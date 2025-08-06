#!/usr/bin/env python3
"""
Reprocess FloPy workflows with poor quality embeddings

This script targets specific workflows that need reprocessing due to:
- Short embedding text (<1000 chars)
- Missing use cases despite having purpose
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

import config
import psycopg2
from src.flopy_workflow_processor import WorkflowProcessor


async def reprocess_flopy_workflows():
    """Reprocess specific FloPy workflows with poor embeddings"""
    
    # List of workflows that need reprocessing (from QA report)
    workflows_to_reprocess = [
        'Notebooks/mf6_data_tutorial04.py',
        'Notebooks/mf6_lgr_tutorial01.py', 
        'Notebooks/vtk_pathlines_example.py',
        'Notebooks/mf6_data_tutorial08.py',
        'Notebooks/mf6_mnw2_tutorial01.py',
        'Notebooks/pest_tutorial01.py',
        'Notebooks/mt3d-usgs_example.py',
        'Notebooks/dis_triangle_example.py'
    ]
    
    print("🔄 REPROCESSING FLOPY WORKFLOWS WITH POOR EMBEDDINGS")
    print("=" * 60)
    print(f"Targeting {len(workflows_to_reprocess)} workflows")
    print()
    
    # Initialize processor
    processor = WorkflowProcessor(
        tutorials_path="/home/danilopezmella/flopy_expert/flopy/.docs/Notebooks",
        neon_conn_string=config.NEON_CONNECTION_STRING,
        gemini_api_key=config.GEMINI_API_KEY,
        openai_api_key=config.OPENAI_API_KEY
    )
    
    # First, delete the existing poor quality records (handle foreign keys)
    print("🗑️  Deleting existing poor quality records...")
    with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
        with conn.cursor() as cur:
            # First get the IDs of workflows to delete
            placeholders = ','.join(['%s'] * len(workflows_to_reprocess))
            cur.execute(f"""
                SELECT id, title FROM flopy_workflows 
                WHERE tutorial_file IN ({placeholders})
            """, workflows_to_reprocess)
            
            workflows_to_delete = cur.fetchall()
            
            if workflows_to_delete:
                # Delete from relationships table first
                workflow_ids = [str(wf_id) for wf_id, _ in workflows_to_delete]
                id_placeholders = ','.join(['%s'] * len(workflow_ids))
                
                cur.execute(f"""
                    DELETE FROM flopy_workflow_relationships 
                    WHERE source_workflow_id IN ({id_placeholders}) 
                    OR target_workflow_id IN ({id_placeholders})
                """, workflow_ids + workflow_ids)
                
                # Delete from steps table
                cur.execute(f"""
                    DELETE FROM flopy_workflow_steps 
                    WHERE workflow_id IN ({id_placeholders})
                """, workflow_ids)
                
                # Finally delete from main table
                cur.execute(f"""
                    DELETE FROM flopy_workflows 
                    WHERE tutorial_file IN ({placeholders})
                """, workflows_to_reprocess)
                
                for wf_id, title in workflows_to_delete:
                    print(f"  ✓ Deleted: {title}")
                
                conn.commit()
                print(f"\nDeleted {len(workflows_to_delete)} workflows")
            else:
                print("No workflows found to delete")
    
    # Now reprocess each workflow
    print("\n🚀 Reprocessing workflows with improved retry logic...")
    print("-" * 60)
    
    successful = 0
    failed = []
    
    for i, workflow_file in enumerate(workflows_to_reprocess, 1):
        print(f"\n[{i}/{len(workflows_to_reprocess)}] Processing: {workflow_file}")
        
        # Extract the workflow (remove 'Notebooks/' prefix for file path)
        filename = workflow_file.replace('Notebooks/', '')
        workflow_path = Path(processor.tutorials_path) / filename
        workflow = processor.extractor.extract_workflow(workflow_path)
        
        if workflow:
            print(f"  ✓ Extracted: {workflow.title}")
            print(f"  Model type: {workflow.model_type}")
            print(f"  Packages: {len(workflow.packages_used)}")
            
            # Process with AI and store
            try:
                success = await processor.process_workflow(workflow)
                if success:
                    print(f"  ✅ Successfully reprocessed!")
                    successful += 1
                    
                    # Verify the new embedding
                    with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
                        with conn.cursor() as cur:
                            cur.execute("""
                                SELECT 
                                    LENGTH(embedding_text) as embed_len,
                                    array_length(best_use_cases, 1) as use_cases_count
                                FROM flopy_workflows
                                WHERE tutorial_file = %s
                            """, (workflow_file,))
                            
                            result = cur.fetchone()
                            if result:
                                embed_len, use_cases = result
                                print(f"  📊 New embedding: {embed_len} chars")
                                print(f"  📋 Use cases: {use_cases or 0} items")
                else:
                    print(f"  ❌ Failed to process")
                    failed.append(workflow_file)
            except Exception as e:
                print(f"  ❌ Error: {e}")
                failed.append(workflow_file)
        else:
            print(f"  ❌ Failed to extract workflow")
            failed.append(workflow_file)
        
        # Small delay between workflows
        await asyncio.sleep(2)
    
    # Final report
    print("\n" + "=" * 60)
    print("📊 REPROCESSING SUMMARY")
    print("=" * 60)
    print(f"✅ Successful: {successful}/{len(workflows_to_reprocess)}")
    
    if failed:
        print(f"❌ Failed: {len(failed)}")
        for f in failed:
            print(f"   - {f}")
    
    # Run quality check on reprocessed items
    print("\n🔍 Verifying new embeddings...")
    with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    tutorial_file,
                    title,
                    LENGTH(embedding_text) as embed_len,
                    array_length(best_use_cases, 1) as use_cases_count
                FROM flopy_workflows
                WHERE tutorial_file = ANY(%s)
                ORDER BY LENGTH(embedding_text)
            """, (workflows_to_reprocess,))
            
            print("\nFinal embedding quality:")
            print("-" * 60)
            all_good = True
            for file, title, embed_len, use_cases in cur.fetchall():
                status = "✅" if embed_len >= 1000 else "⚠️"
                print(f"{status} {file}: {embed_len} chars, {use_cases or 0} use cases")
                if embed_len < 1000:
                    all_good = False
            
            if all_good:
                print("\n🎉 All reprocessed workflows now have good embeddings!")
            else:
                print("\n⚠️  Some workflows still have short embeddings")


async def main():
    """Main entry point"""
    await reprocess_flopy_workflows()


if __name__ == "__main__":
    asyncio.run(main())
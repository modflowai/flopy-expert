#!/usr/bin/env python3
"""
Test script for workflow processing pipeline
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append('/home/danilopezmella/flopy_expert')

import config
from src.flopy_workflow_extractor import JupytextWorkflowExtractor
from src.flopy_workflow_processor import WorkflowProcessor


async def test_single_workflow():
    """Test processing a single workflow"""
    
    print("🧪 Testing workflow processing pipeline...")
    print("=" * 60)
    
    # Initialize processor
    processor = WorkflowProcessor(
        tutorials_path="/home/danilopezmella/flopy_expert/flopy/.docs/Notebooks",
        neon_conn_string=config.NEON_CONNECTION_STRING,
        gemini_api_key=config.GEMINI_API_KEY,
        openai_api_key=config.OPENAI_API_KEY
    )
    
    # Extract a single workflow for testing
    test_file = Path("/home/danilopezmella/flopy_expert/flopy/.docs/Notebooks/mf6_tutorial01.py")
    
    if test_file.exists():
        print(f"\n📄 Testing with: {test_file.name}")
        
        # Extract workflow
        workflow = processor.extractor.extract_workflow(test_file)
        
        if workflow:
            print(f"\n✅ Successfully extracted workflow:")
            print(f"   Title: {workflow.title}")
            print(f"   Model Type: {workflow.model_type}")
            print(f"   Sections: {len(workflow.sections)}")
            print(f"   Packages: {', '.join(workflow.packages_used)}")
            print(f"   Complexity: {workflow.complexity}")
            print(f"   Tags: {', '.join(workflow.tags)}")
            
            # Process with AI and store in database
            print(f"\n🤖 Processing with AI analysis...")
            success = await processor.process_workflow(workflow)
            
            if success:
                print("\n✅ Workflow successfully processed and stored!")
                
                # Query to verify it was stored
                import psycopg2
                with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT 
                                title,
                                workflow_purpose,
                                best_use_cases,
                                prerequisites,
                                common_modifications
                            FROM flopy_workflows
                            WHERE tutorial_file = %s
                        """, (workflow.tutorial_file,))
                        
                        result = cur.fetchone()
                        if result:
                            print("\n📊 Stored Analysis:")
                            print(f"   Purpose: {result[1][:200]}...")
                            print(f"   Use Cases: {result[2][:3]}")
                            print(f"   Prerequisites: {result[3][:3]}")
                            print(f"   Modifications: {result[4][:3]}")
            else:
                print("\n❌ Failed to process workflow")
        else:
            print("\n❌ Failed to extract workflow")
    else:
        print(f"\n❌ Test file not found: {test_file}")


async def test_similarity_search():
    """Test semantic similarity search"""
    
    print("\n\n🔍 Testing similarity search...")
    print("=" * 60)
    
    import psycopg2
    try:
        with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
            with conn.cursor() as cur:
                # Check if we have any workflows
                cur.execute("SELECT COUNT(*) FROM flopy_workflows")
                count = cur.fetchone()[0]
                
                if count > 0:
                    print(f"\nFound {count} workflows in database")
                    
                    # Test semantic search
                    search_query = "how to build a model with wells"
                    print(f"\nSearching for: '{search_query}'")
                    
                    # Create embedding for search query
                    from openai import AsyncOpenAI
                    openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
                    
                    response = await openai_client.embeddings.create(
                        input=search_query,
                        model="text-embedding-3-small"
                    )
                    query_embedding = response.data[0].embedding
                    
                    # Search using cosine similarity
                    cur.execute("""
                        SELECT 
                            title,
                            workflow_purpose,
                            1 - (embedding <=> %s::vector) as similarity
                        FROM flopy_workflows
                        ORDER BY similarity DESC
                        LIMIT 5
                    """, (query_embedding,))
                    
                    results = cur.fetchall()
                    
                    print("\n📋 Top 5 similar workflows:")
                    for i, (title, purpose, similarity) in enumerate(results, 1):
                        print(f"\n{i}. {title} (similarity: {similarity:.3f})")
                        print(f"   Purpose: {purpose[:100]}...")
                else:
                    print("\nNo workflows found in database. Run test_single_workflow() first.")
                    
    except Exception as e:
        print(f"\n❌ Error in similarity search: {e}")


async def main():
    """Run all tests"""
    
    # Test single workflow processing
    await test_single_workflow()
    
    # Test similarity search
    await test_similarity_search()
    
    print("\n\n✅ All tests complete!")


if __name__ == "__main__":
    asyncio.run(main())
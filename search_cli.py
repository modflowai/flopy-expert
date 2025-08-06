#!/usr/bin/env python3
"""
Interactive CLI for testing FloPy and PyEMU semantic searches.
Demonstrates the separate search domains and hierarchical data retrieval.
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import json

# Add project root to path
sys.path.append(str(Path(__file__).parent))

import config
import psycopg2
from openai import AsyncOpenAI


class SemanticSearchCLI:
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        self.connection_string = config.NEON_CONNECTION_STRING
        
    async def create_query_embedding(self, query: str) -> List[float]:
        """Create embedding for user query"""
        response = await self.openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )
        return response.data[0].embedding

    def format_results(self, results: List[Dict[str, Any]], search_type: str) -> str:
        """Format search results for display"""
        if not results:
            return "No results found."
        
        output = f"\n🔍 {search_type} Results:\n"
        output += "=" * 60 + "\n"
        
        for i, result in enumerate(results, 1):
            output += f"\n{i}. "
            
            if 'relative_path' in result:  # Module result
                output += f"📄 {result['relative_path']}\n"
                if result.get('package_code'):
                    output += f"   Package: {result['package_code']}\n"
                if result.get('model_family'):
                    output += f"   Family: {result['model_family']}\n"
            elif 'tutorial_file' in result:  # FloPy workflow
                output += f"📖 {result['tutorial_file']}\n"
                output += f"   Title: {result.get('title', 'N/A')}\n"
                if result.get('packages_used'):
                    packages = result['packages_used'][:3]  # Show first 3
                    output += f"   Packages: {', '.join(packages)}\n"
            elif 'notebook_file' in result:  # PyEMU workflow
                output += f"📓 {result['notebook_file']}\n"
                output += f"   Title: {result.get('title', 'N/A')}\n"
            
            # Show similarity score if available
            if 'similarity' in result:
                output += f"   Similarity: {result['similarity']:.3f}\n"
            
            # Show purpose (truncated)
            purpose_field = result.get('semantic_purpose') or result.get('workflow_purpose', '')
            if purpose_field:
                purpose = purpose_field[:200] + "..." if len(purpose_field) > 200 else purpose_field
                output += f"   Purpose: {purpose}\n"
        
        return output

    async def search_flopy_modules(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search FloPy modules using semantic similarity"""
        try:
            query_embedding = await self.create_query_embedding(query)
            
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    # Try proper vector search first
                    try:
                        # Format embedding as pgvector string literal
                        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
                        
                        # Use L2 distance (<->) which works perfectly in Neon
                        cur.execute("""
                            SELECT 
                                relative_path,
                                package_code,
                                model_family,
                                semantic_purpose,
                                embedding <-> CAST(%s AS vector) as l2_distance
                            FROM flopy_modules
                            WHERE embedding IS NOT NULL
                            ORDER BY embedding <-> CAST(%s AS vector)
                            LIMIT %s
                        """, (embedding_str, embedding_str, limit))
                        
                        columns = [desc[0] for desc in cur.description]
                        results = [dict(zip(columns, row)) for row in cur.fetchall()]
                        
                        if results:
                            # Convert L2 distance to similarity-like score (lower distance = higher similarity)
                            for result in results:
                                result['similarity'] = 1.0 / (1.0 + result['l2_distance'])
                            return results
                            
                    except Exception as vec_error:
                        print(f"Vector search failed: {vec_error}")
                    
                    # Fallback to text search
                    query_pattern = f'%{query}%'
                    cur.execute("""
                        SELECT 
                            relative_path,
                            package_code,
                            model_family,
                            semantic_purpose,
                            0.5 as similarity
                        FROM flopy_modules
                        WHERE semantic_purpose ILIKE %s
                           OR package_code ILIKE %s
                           OR relative_path ILIKE %s
                        ORDER BY 
                            CASE 
                                WHEN package_code ILIKE %s THEN 1
                                WHEN semantic_purpose ILIKE %s THEN 2
                                ELSE 3
                            END,
                            package_code
                        LIMIT %s
                    """, (query_pattern, query_pattern, query_pattern, 
                          query_pattern, query_pattern, limit))
                    
                    columns = [desc[0] for desc in cur.description]
                    results = [dict(zip(columns, row)) for row in cur.fetchall()]
                    
                    return results
        except Exception as e:
            print(f"Error in module search: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def search_flopy_workflows(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search FloPy workflows using semantic similarity"""
        query_embedding = await self.create_query_embedding(query)
        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
        
        with psycopg2.connect(self.connection_string) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        tutorial_file,
                        title,
                        packages_used,
                        complexity,
                        workflow_purpose,
                        embedding <-> CAST(%s AS vector) as l2_distance
                    FROM flopy_workflows
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <-> CAST(%s AS vector)
                    LIMIT %s
                """, (embedding_str, embedding_str, limit))
                
                columns = [desc[0] for desc in cur.description]
                results = [dict(zip(columns, row)) for row in cur.fetchall()]
                
                # Convert L2 distance to similarity
                for result in results:
                    result['similarity'] = 1.0 / (1.0 + result['l2_distance'])
                
                return results

    async def get_flopy_workflow_steps(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get detailed steps for a FloPy workflow"""
        with psycopg2.connect(self.connection_string) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        step_number,
                        description,
                        flopy_classes,
                        key_functions,
                        LEFT(code_snippet, 200) as code_preview
                    FROM flopy_workflow_steps
                    WHERE workflow_id = %s
                    ORDER BY step_number
                """, (workflow_id,))
                
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]

    async def search_pyemu_modules(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search PyEMU modules using semantic similarity"""
        query_embedding = await self.create_query_embedding(query)
        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
        
        with psycopg2.connect(self.connection_string) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        relative_path,
                        module_name,
                        semantic_purpose,
                        use_cases,
                        statistical_concepts,
                        embedding <-> CAST(%s AS vector) as l2_distance
                    FROM pyemu_modules
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <-> CAST(%s AS vector)
                    LIMIT %s
                """, (embedding_str, embedding_str, limit))
                
                columns = [desc[0] for desc in cur.description]
                results = [dict(zip(columns, row)) for row in cur.fetchall()]
                
                # Convert L2 distance to similarity
                for result in results:
                    result['similarity'] = 1.0 / (1.0 + result['l2_distance'])
                
                return results

    async def search_pyemu_workflows(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search PyEMU workflows using semantic similarity"""
        query_embedding = await self.create_query_embedding(query)
        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
        
        with psycopg2.connect(self.connection_string) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        notebook_file,
                        title,
                        workflow_purpose,
                        best_practices,
                        common_applications,
                        embedding <-> CAST(%s AS vector) as l2_distance
                    FROM pyemu_workflows
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <-> CAST(%s AS vector)
                    LIMIT %s
                """, (embedding_str, embedding_str, limit))
                
                columns = [desc[0] for desc in cur.description]
                results = [dict(zip(columns, row)) for row in cur.fetchall()]
                
                # Convert L2 distance to similarity
                for result in results:
                    result['similarity'] = 1.0 / (1.0 + result['l2_distance'])
                
                return results

    async def get_pyemu_workflow_sections(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get detailed sections for a PyEMU workflow"""
        with psycopg2.connect(self.connection_string) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        section_number,
                        title,
                        description,
                        pest_concepts,
                        uncertainty_methods,
                        pyemu_classes
                    FROM pyemu_workflow_sections
                    WHERE workflow_id = %s
                    ORDER BY section_number
                """, (workflow_id,))
                
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]

    async def comprehensive_flopy_search(self, query: str) -> str:
        """Comprehensive FloPy search across modules and workflows"""
        output = f"\n🌊 FLOPY COMPREHENSIVE SEARCH: '{query}'\n"
        output += "=" * 80 + "\n"
        
        # Search modules
        modules = await self.search_flopy_modules(query, 3)
        output += self.format_results(modules, "FloPy Modules")
        
        # Search workflows
        workflows = await self.search_flopy_workflows(query, 3)
        output += self.format_results(workflows, "FloPy Workflows")
        
        # If we found workflows, show one workflow's steps
        if workflows:
            workflow_title = workflows[0]['tutorial_file']
            output += f"\n📋 Detailed Steps for: {workflow_title}\n"
            output += "-" * 60 + "\n"
            
            # Get workflow ID
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM flopy_workflows WHERE tutorial_file = %s", 
                              (workflow_title,))
                    result = cur.fetchone()
                    if result:
                        workflow_id = result[0]
                        steps = await self.get_flopy_workflow_steps(workflow_id)
                        for step in steps[:5]:  # Show first 5 steps
                            output += f"\nStep {step['step_number']}: {step['description']}\n"
                            if step['flopy_classes']:
                                output += f"  Classes: {', '.join(step['flopy_classes'][:3])}\n"
                            if step['code_preview']:
                                output += f"  Code: {step['code_preview']}...\n"
        
        return output

    async def comprehensive_pyemu_search(self, query: str) -> str:
        """Comprehensive PyEMU search across modules and workflows"""
        output = f"\n🎯 PYEMU COMPREHENSIVE SEARCH: '{query}'\n"
        output += "=" * 80 + "\n"
        
        # Search modules
        modules = await self.search_pyemu_modules(query, 3)
        output += self.format_results(modules, "PyEMU Modules")
        
        # Search workflows
        workflows = await self.search_pyemu_workflows(query, 3)
        output += self.format_results(workflows, "PyEMU Workflows")
        
        # If we found workflows, show one workflow's sections
        if workflows:
            workflow_title = workflows[0]['notebook_file']
            output += f"\n📋 Detailed Sections for: {workflow_title}\n"
            output += "-" * 60 + "\n"
            
            # Get workflow ID
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM pyemu_workflows WHERE notebook_file = %s", 
                              (workflow_title,))
                    result = cur.fetchone()
                    if result:
                        workflow_id = result[0]
                        sections = await self.get_pyemu_workflow_sections(workflow_id)
                        for section in sections[:5]:  # Show first 5 sections
                            output += f"\nSection {section['section_number']}: {section['title']}\n"
                            if section['description']:
                                desc = section['description'][:150] + "..." if len(section['description']) > 150 else section['description']
                                output += f"  Description: {desc}\n"
                            if section['pest_concepts']:
                                output += f"  PEST Concepts: {', '.join(section['pest_concepts'][:3])}\n"
                            if section['uncertainty_methods']:
                                output += f"  Methods: {', '.join(section['uncertainty_methods'][:3])}\n"
        
        return output

    def show_help(self):
        """Show help information"""
        help_text = """
🔍 Semantic Search CLI - FloPy Expert Database

COMMANDS:
  help                    - Show this help
  stats                   - Show database statistics
  flopy <query>          - Search FloPy domain (groundwater modeling)
  pyemu <query>          - Search PyEMU domain (uncertainty analysis)
  quit / exit            - Exit the CLI

EXAMPLE QUERIES:

FloPy Domain (Groundwater Modeling):
  flopy sparse matrix solver
  flopy well boundaries
  flopy drain package
  flopy structured grid
  flopy tutorial setup

PyEMU Domain (Uncertainty Analysis):
  pyemu monte carlo
  pyemu pest calibration
  pyemu fosm analysis
  pyemu parameter estimation
  pyemu uncertainty quantification

Each search will show:
- Related modules/packages
- Tutorial workflows
- Detailed steps/sections
- Implementation examples
        """
        print(help_text)

    def show_stats(self):
        """Show database statistics"""
        with psycopg2.connect(self.connection_string) as conn:
            with conn.cursor() as cur:
                # Get counts from all tables
                cur.execute("SELECT COUNT(*) FROM flopy_modules")
                flopy_modules = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM flopy_workflows")
                flopy_workflows = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM flopy_workflow_steps")
                flopy_steps = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM flopy_workflow_relationships")
                flopy_relationships = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM pyemu_modules")
                pyemu_modules = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM pyemu_workflows")
                pyemu_workflows = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM pyemu_workflow_sections")
                pyemu_sections = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM pyemu_workflow_relationships")
                pyemu_relationships = cur.fetchone()[0]
        
        stats = f"""
📊 DATABASE STATISTICS
=====================

FloPy Domain (Groundwater Modeling):
  • Modules:         {flopy_modules:>4} items
  • Workflows:       {flopy_workflows:>4} items  
  • Workflow Steps:  {flopy_steps:>4} items
  • Relationships:   {flopy_relationships:>4} items
  ─────────────────────────
  FloPy Total:       {flopy_modules + flopy_workflows + flopy_steps + flopy_relationships:>4} items

PyEMU Domain (Uncertainty Analysis):
  • Modules:         {pyemu_modules:>4} items
  • Workflows:       {pyemu_workflows:>4} items
  • Sections:        {pyemu_sections:>4} items  
  • Relationships:   {pyemu_relationships:>4} items
  ─────────────────────────
  PyEMU Total:       {pyemu_modules + pyemu_workflows + pyemu_sections + pyemu_relationships:>4} items

GRAND TOTAL:         {flopy_modules + flopy_workflows + flopy_steps + flopy_relationships + pyemu_modules + pyemu_workflows + pyemu_sections + pyemu_relationships:>4} items

Vector Embeddings:   {flopy_modules + flopy_workflows + pyemu_modules + pyemu_workflows:>4} semantic vectors
        """
        print(stats)

    async def run(self):
        """Main CLI loop"""
        print("🔍 FloPy Expert - Semantic Search CLI")
        print("=====================================")
        print("Type 'help' for commands, 'quit' to exit")
        
        while True:
            try:
                user_input = input("\n> ").strip()
                
                if not user_input:
                    continue
                elif user_input.lower() in ['quit', 'exit']:
                    print("Goodbye! 👋")
                    break
                elif user_input.lower() == 'help':
                    self.show_help()
                elif user_input.lower() == 'stats':
                    self.show_stats()
                elif user_input.lower().startswith('flopy '):
                    query = user_input[6:].strip()
                    if query:
                        result = await self.comprehensive_flopy_search(query)
                        print(result)
                    else:
                        print("Please provide a search query after 'flopy'")
                elif user_input.lower().startswith('pyemu '):
                    query = user_input[6:].strip()
                    if query:
                        result = await self.comprehensive_pyemu_search(query)
                        print(result)
                    else:
                        print("Please provide a search query after 'pyemu'")
                else:
                    # Default to FloPy search for any other query
                    print(f"Searching FloPy for: '{user_input}'")
                    result = await self.comprehensive_flopy_search(user_input)
                    print(result)
                    
            except (KeyboardInterrupt, EOFError):
                print("\nGoodbye! 👋")
                break
            except Exception as e:
                print(f"Error: {e}")


async def main():
    cli = SemanticSearchCLI()
    await cli.run()


if __name__ == "__main__":
    asyncio.run(main())
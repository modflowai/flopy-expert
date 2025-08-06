#!/usr/bin/env python3
"""
Demonstration of FloPy Workflow Search System

This script shows how to search for modeling workflows and patterns
using both semantic search (vector embeddings) and keyword search.
"""
import asyncio
import sys
import psycopg2
from openai import AsyncOpenAI

# Add parent directory to path for imports
sys.path.append('/home/danilopezmella/flopy_expert')
import config


class WorkflowSearchDemo:
    """Demonstrate workflow search capabilities"""
    
    def __init__(self):
        self.conn_string = config.NEON_CONNECTION_STRING
        self.openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    
    async def semantic_search(self, query: str, limit: int = 5) -> list:
        """Search workflows using semantic similarity"""
        
        # Create embedding for search query
        response = await self.openai_client.embeddings.create(
            input=query,
            model="text-embedding-3-small"
        )
        query_embedding = response.data[0].embedding
        
        # Search using cosine similarity
        with psycopg2.connect(self.conn_string) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        title,
                        model_type,
                        complexity,
                        packages_used,
                        tags,
                        workflow_purpose,
                        1 - (embedding <=> %s::vector) as similarity
                    FROM flopy_workflows
                    WHERE embedding IS NOT NULL
                    ORDER BY similarity DESC
                    LIMIT %s
                """, (query_embedding, limit))
                
                return cur.fetchall()
    
    def keyword_search(self, query: str, limit: int = 5) -> list:
        """Search workflows using PostgreSQL full-text search"""
        
        with psycopg2.connect(self.conn_string) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        title,
                        model_type,
                        complexity,
                        packages_used,
                        tags,
                        workflow_purpose,
                        ts_rank(search_vector, plainto_tsquery('english', %s)) as rank
                    FROM flopy_workflows
                    WHERE search_vector @@ plainto_tsquery('english', %s)
                    ORDER BY rank DESC
                    LIMIT %s
                """, (query, query, limit))
                
                return cur.fetchall()
    
    def filter_workflows(self, 
                        model_type: str = None, 
                        complexity: str = None,
                        packages: list = None,
                        tags: list = None) -> list:
        """Filter workflows by specific criteria"""
        
        conditions = []
        params = []
        
        if model_type:
            conditions.append("model_type = %s")
            params.append(model_type)
        
        if complexity:
            conditions.append("complexity = %s")
            params.append(complexity)
        
        if packages:
            conditions.append("packages_used && %s")
            params.append(packages)
        
        if tags:
            conditions.append("tags && %s")
            params.append(tags)
        
        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        
        with psycopg2.connect(self.conn_string) as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT 
                        title,
                        model_type,
                        complexity,
                        packages_used,
                        tags,
                        workflow_purpose
                    FROM flopy_workflows
                    WHERE {where_clause}
                    ORDER BY processed_at DESC
                """, params)
                
                return cur.fetchall()
    
    def print_results(self, results: list, search_type: str):
        """Pretty print search results"""
        
        print(f"\n🔍 {search_type} Results:")
        print("=" * 60)
        
        if not results:
            print("No workflows found matching your criteria.")
            return
        
        for i, result in enumerate(results, 1):
            if len(result) == 7:  # With similarity/rank score
                title, model_type, complexity, packages, tags, purpose, score = result
                print(f"\n{i}. {title} (score: {score:.3f})")
            else:  # Without score
                title, model_type, complexity, packages, tags, purpose = result
                print(f"\n{i}. {title}")
            
            print(f"   📊 {model_type.upper()} | {complexity} complexity")
            print(f"   📦 Packages: {', '.join(packages[:5]) if packages else 'None'}")
            print(f"   🏷️  Tags: {', '.join(tags[:5]) if tags else 'None'}")
            
            if purpose:
                print(f"   📝 Purpose: {purpose[:120]}...")
            
            if i < len(results):
                print("-" * 40)


async def main():
    """Run search demonstrations"""
    
    print("🔍 FloPy Workflow Search System Demo")
    print("=" * 50)
    
    search_demo = WorkflowSearchDemo()
    
    # 1. Semantic search examples
    print("\n\n1️⃣ SEMANTIC SEARCH EXAMPLES")
    print("Using AI embeddings to find conceptually similar workflows")
    
    search_queries = [
        "how to build a model with wells and pumping",
        "steady state groundwater flow simulation",
        "transport modeling with contaminants",
        "unstructured grid modeling"
    ]
    
    for query in search_queries:
        print(f"\n🔍 Query: '{query}'")
        results = await search_demo.semantic_search(query, limit=3)
        search_demo.print_results(results, "Semantic Search")
    
    # 2. Keyword search examples
    print("\n\n2️⃣ KEYWORD SEARCH EXAMPLES")
    print("Using PostgreSQL full-text search")
    
    keyword_queries = [
        "drain",
        "steady state",
        "triangular mesh"
    ]
    
    for query in keyword_queries:
        print(f"\n🔍 Keyword: '{query}'")
        results = search_demo.keyword_search(query, limit=3)
        search_demo.print_results(results, "Keyword Search")
    
    # 3. Filter examples
    print("\n\n3️⃣ FILTER EXAMPLES")
    print("Filtering workflows by specific criteria")
    
    filter_examples = [
        {
            "description": "All MODFLOW 6 workflows",
            "model_type": "mf6"
        },
        {
            "description": "Simple complexity workflows",
            "complexity": "simple"
        },
        {
            "description": "Workflows with transport modeling",
            "tags": ["transport"]
        },
        {
            "description": "Workflows using wells (WEL package)",
            "packages": ["WEL"]
        }
    ]
    
    for example in filter_examples:
        print(f"\n🔍 Filter: {example['description']}")
        
        # Extract filter parameters
        filter_params = {k: v for k, v in example.items() if k != 'description'}
        results = search_demo.filter_workflows(**filter_params)
        search_demo.print_results(results, "Filtered Results")
    
    # 4. Database statistics
    print("\n\n4️⃣ DATABASE STATISTICS")
    print("Overview of the workflow database")
    
    with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
        with conn.cursor() as cur:
            # Total count
            cur.execute("SELECT COUNT(*) FROM flopy_workflows")
            total = cur.fetchone()[0]
            
            # By model type
            cur.execute("""
                SELECT model_type, COUNT(*) 
                FROM flopy_workflows 
                GROUP BY model_type 
                ORDER BY COUNT(*) DESC
            """)
            model_counts = cur.fetchall()
            
            # By complexity
            cur.execute("""
                SELECT complexity, COUNT(*) 
                FROM flopy_workflows 
                GROUP BY complexity 
                ORDER BY COUNT(*) DESC
            """)
            complexity_counts = cur.fetchall()
            
            # Most common packages
            cur.execute("""
                SELECT UNNEST(packages_used) as package, COUNT(*) as count
                FROM flopy_workflows
                WHERE packages_used IS NOT NULL
                GROUP BY package
                ORDER BY count DESC
                LIMIT 10
            """)
            package_counts = cur.fetchall()
            
            print(f"\n📊 Total workflows: {total}")
            
            print(f"\n📋 By model type:")
            for model_type, count in model_counts:
                print(f"   {model_type}: {count}")
            
            print(f"\n📋 By complexity:")
            for complexity, count in complexity_counts:
                print(f"   {complexity}: {count}")
            
            print(f"\n📦 Most common packages:")
            for package, count in package_counts:
                print(f"   {package}: {count}")
    
    print(f"\n\n✅ Demo complete! The workflow search system provides:")
    print("   🔍 Semantic search using AI embeddings")
    print("   🔤 Keyword search using full-text search")
    print("   🎯 Advanced filtering by model type, complexity, packages, tags")
    print("   📊 Rich metadata and AI-generated descriptions")
    print("\nThis enables users to quickly find relevant modeling patterns and examples!")


if __name__ == "__main__":
    asyncio.run(main())
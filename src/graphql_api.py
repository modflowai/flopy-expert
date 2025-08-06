import os
import asyncio
import asyncpg
import strawberry
from strawberry.fastapi import GraphQLRouter
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import numpy as np
from fastapi import FastAPI
from dotenv import load_dotenv
from enum import Enum

# Load environment variables
load_dotenv()

# Database connection pool
db_pool = None

async def init_db():
    global db_pool
    db_pool = await asyncpg.create_pool(
        os.getenv('NEON_CONNECTION_STRING'),
        min_size=10,
        max_size=20
    )

async def close_db():
    global db_pool
    if db_pool:
        await db_pool.close()

# GraphQL Types
@strawberry.type
class Package:
    id: str
    name: str
    code: Optional[str]
    model_family: str
    file_path: str
    purpose: str
    docstring: str
    user_scenarios: List[str]
    related_concepts: List[str]
    score: Optional[float] = None

@strawberry.type
class Function:
    id: str
    name: str
    signature: str
    docstring: str
    module_path: str
    class_name: Optional[str]
    what_it_does: Optional[str]
    when_to_use: Optional[str]
    line_number: int
    score: Optional[float] = None

@strawberry.type
class Class:
    id: str
    name: str
    module_path: str
    docstring: str
    base_classes: List[str]
    purpose: Optional[str]
    methods: List[Function]

@strawberry.type
class SearchResult:
    packages: List[Package]
    functions: List[Function]
    classes: List[Class]
    total_results: int

@strawberry.type
class UsagePattern:
    id: str
    pattern_name: str
    description: str
    workflow_steps: str  # JSON string
    example_code: str
    source_file: str

@strawberry.type
class ConceptGraph:
    entity_id: str
    entity_type: str
    entity_name: str
    relationships: List['Relationship']

@strawberry.type
class Relationship:
    target_id: str
    target_name: str
    target_type: str
    relationship_type: str
    strength: float

@strawberry.enum
class SearchMode(Enum):
    EXACT = "exact"
    SEMANTIC = "semantic"
    FULLTEXT = "fulltext"
    HYBRID = "hybrid"

@strawberry.enum
class EntityType(Enum):
    PACKAGE = "package"
    FUNCTION = "function"
    CLASS = "class"
    ALL = "all"

# Query Resolvers
@strawberry.type
class Query:
    @strawberry.field
    async def search(
        self, 
        query: str, 
        mode: SearchMode = SearchMode.HYBRID,
        entity_type: EntityType = EntityType.ALL,
        limit: int = 20
    ) -> SearchResult:
        """Search across the FloPy knowledge base"""
        
        packages = []
        functions = []
        classes = []
        
        async with db_pool.acquire() as conn:
            if mode == SearchMode.EXACT:
                # Exact match on package codes and names
                if entity_type in [EntityType.PACKAGE, EntityType.ALL]:
                    package_rows = await conn.fetch("""
                        SELECT id, relative_path, model_family, package_code,
                               semantic_purpose, module_docstring, user_scenarios, related_concepts
                        FROM modules
                        WHERE package_code = $1 
                           OR relative_path ILIKE '%' || $2 || '%'
                        LIMIT $3
                    """, query.upper(), query, limit)
                    
                    packages = [
                        Package(
                            id=str(row['id']),
                            name=row['package_code'] or os.path.basename(row['relative_path']),
                            code=row['package_code'],
                            model_family=row['model_family'],
                            file_path=row['relative_path'],
                            purpose=row['semantic_purpose'] or '',
                            docstring=row['module_docstring'] or '',
                            user_scenarios=row['user_scenarios'] or [],
                            related_concepts=row['related_concepts'] or []
                        ) for row in package_rows
                    ]
                
                if entity_type in [EntityType.FUNCTION, EntityType.ALL]:
                    function_rows = await conn.fetch("""
                        SELECT f.*, m.relative_path, c.class_name
                        FROM functions f
                        JOIN modules m ON f.module_id = m.id
                        LEFT JOIN classes c ON f.class_id = c.id
                        WHERE f.function_name ILIKE $1
                        LIMIT $2
                    """, f"%{query}%", limit)
                    
                    functions = [
                        Function(
                            id=str(row['id']),
                            name=row['function_name'],
                            signature=row['signature'] or f"{row['function_name']}()",
                            docstring=row['docstring'] or '',
                            module_path=row['relative_path'],
                            class_name=row['class_name'],
                            what_it_does=row['what_it_does'],
                            when_to_use=row['when_to_use'],
                            line_number=row['line_number']
                        ) for row in function_rows
                    ]
            
            elif mode == SearchMode.SEMANTIC:
                # Generate embedding for query
                # For now, we'll use a placeholder - in production, call Gemini
                query_embedding = [0.0] * 1536  # Placeholder
                
                if entity_type in [EntityType.PACKAGE, EntityType.ALL]:
                    package_rows = await conn.fetch("""
                        SELECT id, relative_path, model_family, package_code,
                               semantic_purpose, module_docstring, user_scenarios, related_concepts,
                               1 - (semantic_embedding <=> $1::vector) as similarity
                        FROM modules
                        WHERE semantic_embedding IS NOT NULL
                        ORDER BY semantic_embedding <=> $1::vector
                        LIMIT $2
                    """, query_embedding, limit)
                    
                    packages = [
                        Package(
                            id=str(row['id']),
                            name=row['package_code'] or os.path.basename(row['relative_path']),
                            code=row['package_code'],
                            model_family=row['model_family'],
                            file_path=row['relative_path'],
                            purpose=row['semantic_purpose'] or '',
                            docstring=row['module_docstring'] or '',
                            user_scenarios=row['user_scenarios'] or [],
                            related_concepts=row['related_concepts'] or [],
                            score=row['similarity']
                        ) for row in package_rows
                    ]
            
            elif mode == SearchMode.FULLTEXT:
                # Full-text search
                if entity_type in [EntityType.PACKAGE, EntityType.ALL]:
                    package_rows = await conn.fetch("""
                        SELECT id, relative_path, model_family, package_code,
                               semantic_purpose, module_docstring, user_scenarios, related_concepts,
                               ts_rank(search_content, plainto_tsquery('english', $1)) as rank
                        FROM modules
                        WHERE search_content @@ plainto_tsquery('english', $1)
                        ORDER BY rank DESC
                        LIMIT $2
                    """, query, limit)
                    
                    packages = [
                        Package(
                            id=str(row['id']),
                            name=row['package_code'] or os.path.basename(row['relative_path']),
                            code=row['package_code'],
                            model_family=row['model_family'],
                            file_path=row['relative_path'],
                            purpose=row['semantic_purpose'] or '',
                            docstring=row['module_docstring'] or '',
                            user_scenarios=row['user_scenarios'] or [],
                            related_concepts=row['related_concepts'] or [],
                            score=float(row['rank'])
                        ) for row in package_rows
                    ]
            
            else:  # HYBRID mode
                # Combine all search methods
                # This is a simplified hybrid approach
                # In production, you'd want more sophisticated ranking
                
                # Try exact match first
                exact_packages = await conn.fetch("""
                    SELECT id, relative_path, model_family, package_code,
                           semantic_purpose, module_docstring, user_scenarios, related_concepts
                    FROM modules
                    WHERE package_code = $1
                    LIMIT 5
                """, query.upper())
                
                # Then full-text search
                fulltext_packages = await conn.fetch("""
                    SELECT id, relative_path, model_family, package_code,
                           semantic_purpose, module_docstring, user_scenarios, related_concepts
                    FROM modules
                    WHERE search_content @@ plainto_tsquery('english', $1)
                        AND package_code != $2
                    ORDER BY ts_rank(search_content, plainto_tsquery('english', $1)) DESC
                    LIMIT $3
                """, query, query.upper(), limit - len(exact_packages))
                
                all_packages = list(exact_packages) + list(fulltext_packages)
                
                packages = [
                    Package(
                        id=str(row['id']),
                        name=row['package_code'] or os.path.basename(row['relative_path']),
                        code=row['package_code'],
                        model_family=row['model_family'],
                        file_path=row['relative_path'],
                        purpose=row['semantic_purpose'] or '',
                        docstring=row['module_docstring'] or '',
                        user_scenarios=row['user_scenarios'] or [],
                        related_concepts=row['related_concepts'] or []
                    ) for row in all_packages
                ]
        
        total_results = len(packages) + len(functions) + len(classes)
        
        return SearchResult(
            packages=packages,
            functions=functions,
            classes=classes,
            total_results=total_results
        )
    
    @strawberry.field
    async def get_package(self, package_code: str) -> Optional[Package]:
        """Get a specific package by its code"""
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, relative_path, model_family, package_code,
                       semantic_purpose, module_docstring, user_scenarios, related_concepts
                FROM modules
                WHERE package_code = $1
                LIMIT 1
            """, package_code.upper())
            
            if row:
                return Package(
                    id=str(row['id']),
                    name=row['package_code'] or os.path.basename(row['relative_path']),
                    code=row['package_code'],
                    model_family=row['model_family'],
                    file_path=row['relative_path'],
                    purpose=row['semantic_purpose'] or '',
                    docstring=row['module_docstring'] or '',
                    user_scenarios=row['user_scenarios'] or [],
                    related_concepts=row['related_concepts'] or []
                )
            return None
    
    @strawberry.field
    async def get_function(self, function_name: str, class_name: Optional[str] = None) -> Optional[Function]:
        """Get a specific function by name"""
        async with db_pool.acquire() as conn:
            if class_name:
                row = await conn.fetchrow("""
                    SELECT f.*, m.relative_path, c.class_name
                    FROM functions f
                    JOIN modules m ON f.module_id = m.id
                    JOIN classes c ON f.class_id = c.id
                    WHERE f.function_name = $1 AND c.class_name = $2
                    LIMIT 1
                """, function_name, class_name)
            else:
                row = await conn.fetchrow("""
                    SELECT f.*, m.relative_path
                    FROM functions f
                    JOIN modules m ON f.module_id = m.id
                    WHERE f.function_name = $1 AND f.class_id IS NULL
                    LIMIT 1
                """, function_name)
            
            if row:
                return Function(
                    id=str(row['id']),
                    name=row['function_name'],
                    signature=row['signature'] or f"{row['function_name']}()",
                    docstring=row['docstring'] or '',
                    module_path=row['relative_path'],
                    class_name=row.get('class_name'),
                    what_it_does=row['what_it_does'],
                    when_to_use=row['when_to_use'],
                    line_number=row['line_number']
                )
            return None
    
    @strawberry.field
    async def get_class(self, class_name: str) -> Optional[Class]:
        """Get a specific class by name"""
        async with db_pool.acquire() as conn:
            # Get class info
            class_row = await conn.fetchrow("""
                SELECT c.*, m.relative_path
                FROM classes c
                JOIN modules m ON c.module_id = m.id
                WHERE c.class_name = $1
                LIMIT 1
            """, class_name)
            
            if not class_row:
                return None
            
            # Get methods
            method_rows = await conn.fetch("""
                SELECT f.*
                FROM functions f
                WHERE f.class_id = $1
            """, class_row['id'])
            
            methods = [
                Function(
                    id=str(row['id']),
                    name=row['function_name'],
                    signature=row['signature'] or f"{row['function_name']}()",
                    docstring=row['docstring'] or '',
                    module_path=class_row['relative_path'],
                    class_name=class_name,
                    what_it_does=row['what_it_does'],
                    when_to_use=row['when_to_use'],
                    line_number=row['line_number']
                ) for row in method_rows
            ]
            
            return Class(
                id=str(class_row['id']),
                name=class_row['class_name'],
                module_path=class_row['relative_path'],
                docstring=class_row['docstring'] or '',
                base_classes=class_row['base_classes'] or [],
                purpose=class_row['purpose'],
                methods=methods
            )
    
    @strawberry.field
    async def find_usage_patterns(self, concept: str, limit: int = 10) -> List[UsagePattern]:
        """Find usage patterns for a concept"""
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM usage_patterns
                WHERE description ILIKE '%' || $1 || '%'
                   OR pattern_name ILIKE '%' || $1 || '%'
                LIMIT $2
            """, concept, limit)
            
            return [
                UsagePattern(
                    id=str(row['id']),
                    pattern_name=row['pattern_name'],
                    description=row['description'] or '',
                    workflow_steps=json.loads(row['workflow_steps']) if row['workflow_steps'] else {},
                    example_code=row['example_code'] or '',
                    source_file=row['source_file'] or ''
                ) for row in rows
            ]
    
    @strawberry.field
    async def get_relationships(self, entity_id: str) -> ConceptGraph:
        """Get relationships for an entity"""
        async with db_pool.acquire() as conn:
            # Get entity info
            entity = await conn.fetchrow("""
                SELECT 'module' as type, relative_path as name 
                FROM modules WHERE id = $1
                UNION
                SELECT 'class' as type, class_name as name 
                FROM classes WHERE id = $1
                UNION
                SELECT 'function' as type, function_name as name 
                FROM functions WHERE id = $1
            """, entity_id)
            
            if not entity:
                return None
            
            # Get relationships
            rel_rows = await conn.fetch("""
                SELECT r.*, 
                       CASE 
                           WHEN r.target_type = 'module' THEN m.relative_path
                           WHEN r.target_type = 'class' THEN c.class_name
                           WHEN r.target_type = 'function' THEN f.function_name
                       END as target_name
                FROM relationships r
                LEFT JOIN modules m ON r.target_id = m.id::text AND r.target_type = 'module'
                LEFT JOIN classes c ON r.target_id = c.id::text AND r.target_type = 'class'
                LEFT JOIN functions f ON r.target_id = f.id::text AND r.target_type = 'function'
                WHERE r.source_id = $1
            """, entity_id)
            
            relationships = [
                Relationship(
                    target_id=row['target_id'],
                    target_name=row['target_name'] or 'Unknown',
                    target_type=row['target_type'],
                    relationship_type=row['relationship_type'],
                    strength=row['strength']
                ) for row in rel_rows
            ]
            
            return ConceptGraph(
                entity_id=entity_id,
                entity_type=entity['type'],
                entity_name=entity['name'],
                relationships=relationships
            )

# Create FastAPI app
app = FastAPI(title="FloPy Knowledge Base API")

# Create GraphQL schema
schema = strawberry.Schema(query=Query)

# Add GraphQL route
graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")

# Lifecycle events
@app.on_event("startup")
async def startup():
    await init_db()

@app.on_event("shutdown")
async def shutdown():
    await close_db()

# Health check
@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
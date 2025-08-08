-- FloPy Semantic Database - Clean Schema
-- Based on lessons learned from initial implementation

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Main module information
CREATE TABLE modules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_path TEXT UNIQUE NOT NULL,
    relative_path TEXT NOT NULL,
    
    -- Extracted from path/filename
    model_family TEXT,      -- 'mf6', 'modflow', 'mfusg', 'mt3d', 'utils', etc.
    package_code TEXT,      -- 'WEL', 'SMS', 'UZF', extracted from filename
    
    -- Content
    module_docstring TEXT,
    source_code TEXT,
    
    -- Gemini semantic analysis
    semantic_purpose TEXT NOT NULL,
    user_scenarios TEXT[],
    related_concepts TEXT[],
    typical_errors TEXT[],
    
    -- Single embedding combining code + semantic understanding
    embedding vector(1536) NOT NULL,
    
    -- Full-text search
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english', 
            COALESCE(package_code, '') || ' ' || 
            COALESCE(model_family, '') || ' ' || 
            COALESCE(module_docstring, '') || ' ' || 
            COALESCE(semantic_purpose, '')
        )
    ) STORED,
    
    -- Metadata
    file_hash TEXT NOT NULL,
    last_modified TIMESTAMP,
    processed_at TIMESTAMP DEFAULT NOW(),
    
    -- Indexes
    CONSTRAINT modules_file_path_key UNIQUE (file_path)
);

-- Indexes for modules
CREATE INDEX idx_modules_package_code ON modules(package_code);
CREATE INDEX idx_modules_model_family ON modules(model_family);
CREATE INDEX idx_modules_search_vector ON modules USING GIN(search_vector);
CREATE INDEX idx_modules_embedding ON modules USING hnsw (embedding vector_cosine_ops);

-- Package-level aggregation
CREATE TABLE packages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    package_code TEXT UNIQUE NOT NULL,
    model_families TEXT[],  -- Can span multiple families
    primary_module_id UUID REFERENCES modules(id),
    description TEXT,
    common_parameters JSONB,
    typical_usage TEXT,
    embedding vector(1536),
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english', 
            COALESCE(package_code, '') || ' ' || 
            COALESCE(description, '') || ' ' || 
            COALESCE(typical_usage, '')
        )
    ) STORED
);

-- Indexes for packages
CREATE INDEX idx_packages_search_vector ON packages USING GIN(search_vector);
CREATE INDEX idx_packages_embedding ON packages USING hnsw (embedding vector_cosine_ops);

-- Common workflows from examples/tutorials
CREATE TABLE workflows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    steps JSONB NOT NULL,  -- Array of {step, packages_used, code_snippet}
    involved_packages TEXT[],
    source_files TEXT[],
    difficulty_level TEXT CHECK (difficulty_level IN ('beginner', 'intermediate', 'advanced')),
    embedding vector(1536),
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english', 
            COALESCE(name, '') || ' ' || 
            COALESCE(description, '')
        )
    ) STORED,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for workflows
CREATE INDEX idx_workflows_search_vector ON workflows USING GIN(search_vector);
CREATE INDEX idx_workflows_embedding ON workflows USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_workflows_packages ON workflows USING GIN(involved_packages);

-- Processing log for CI/CD
CREATE TABLE processing_log (
    id SERIAL PRIMARY KEY,
    file_path TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    error_message TEXT,
    attempts INTEGER DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    UNIQUE(file_path)
);

-- Create a view for package search
CREATE VIEW package_search AS
SELECT 
    p.package_code,
    p.description,
    p.model_families,
    COUNT(m.id) as module_count,
    p.embedding
FROM packages p
LEFT JOIN modules m ON m.package_code = p.package_code
GROUP BY p.id, p.package_code, p.description, p.model_families, p.embedding;

-- Create a view for cross-model packages
CREATE VIEW cross_model_packages AS
SELECT 
    package_code,
    array_agg(DISTINCT model_family) as model_families,
    COUNT(*) as implementation_count
FROM modules
WHERE package_code IS NOT NULL
GROUP BY package_code
HAVING COUNT(DISTINCT model_family) > 1;

-- Function to search with different modes
CREATE OR REPLACE FUNCTION search_flopy(
    query_text TEXT,
    search_mode TEXT,
    query_embedding vector DEFAULT NULL,
    limit_count INTEGER DEFAULT 20
)
RETURNS TABLE (
    id UUID,
    name TEXT,
    type TEXT,
    description TEXT,
    model_family TEXT,
    score FLOAT
) AS $$
BEGIN
    IF search_mode = 'EXACT' THEN
        -- Exact package code match
        RETURN QUERY
        SELECT 
            m.id,
            m.package_code::TEXT as name,
            'module'::TEXT as type,
            m.semantic_purpose as description,
            m.model_family,
            1.0::FLOAT as score
        FROM modules m
        WHERE UPPER(m.package_code) = UPPER(query_text)
        LIMIT limit_count;
        
    ELSIF search_mode = 'FULLTEXT' THEN
        -- Full-text search
        RETURN QUERY
        SELECT 
            m.id,
            COALESCE(m.package_code, m.relative_path)::TEXT as name,
            'module'::TEXT as type,
            m.semantic_purpose as description,
            m.model_family,
            ts_rank(m.search_vector, plainto_tsquery('english', query_text))::FLOAT as score
        FROM modules m
        WHERE m.search_vector @@ plainto_tsquery('english', query_text)
        ORDER BY score DESC
        LIMIT limit_count;
        
    ELSIF search_mode = 'SEMANTIC' AND query_embedding IS NOT NULL THEN
        -- Semantic similarity search
        RETURN QUERY
        SELECT 
            m.id,
            COALESCE(m.package_code, m.relative_path)::TEXT as name,
            'module'::TEXT as type,
            m.semantic_purpose as description,
            m.model_family,
            (1 - (m.embedding <=> query_embedding))::FLOAT as score
        FROM modules m
        ORDER BY m.embedding <=> query_embedding
        LIMIT limit_count;
    END IF;
END;
$$ LANGUAGE plpgsql;
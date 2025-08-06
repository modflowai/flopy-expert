# FloPy Semantic Database - Complete Roadmap

## Goal
Create a comprehensive semantic database for FloPy that enables intelligent search and solves package identification issues (like SMS/UZF confusion).

## Core Principles
1. **Documentation structure IS our blueprint** - Follow exactly what ReadTheDocs considers important
2. **Curated coverage** - Process only documented modules, not data files or test artifacts
3. **Single source of truth** - one embedding per entity, clear purpose
4. **Production-ready** - built for CI/CD and continuous updates

## Key Insight: Use Documentation as Guide
The FloPy team has already curated what's important in `.docs/code.rst`. Instead of blindly processing 376+ files (including data files like `.ghb`, `.wel`), we follow their official documentation structure which lists exactly which Python modules matter.

## Phase 1: Database Design

### Core Schema
```sql
-- Main module information
CREATE TABLE modules (
    id UUID PRIMARY KEY,
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
    search_vector tsvector,
    
    -- Metadata
    file_hash TEXT NOT NULL,
    last_modified TIMESTAMP,
    processed_at TIMESTAMP DEFAULT NOW()
);

-- Package-level aggregation
CREATE TABLE packages (
    id UUID PRIMARY KEY,
    package_code TEXT UNIQUE NOT NULL,
    model_families TEXT[],  -- Can span multiple families
    primary_module_id UUID REFERENCES modules(id),
    description TEXT,
    embedding vector(1536)
);

-- Common workflows from examples/tutorials
CREATE TABLE workflows (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    steps JSONB NOT NULL,
    involved_packages TEXT[],
    source_files TEXT[],
    embedding vector(1536)
);
```

### Key Decisions
- **ONE embedding per entity** - combines code structure + semantic meaning
- **Packages table** - aggregates modules by package code (SMS, WEL, etc.)
- **Workflows table** - extracted from notebooks/examples
- **No separate classes/functions tables** - keep it simple, search at module level

## Phase 2: Processing Pipeline

### Step 1: Documentation-Driven Discovery
- Parse `.docs/code.rst` to extract documented module patterns
- Convert patterns to actual file paths (e.g., `flopy.mf6.modflow.mfgwf*` → `flopy/mf6/modflow/mfgwf*.py`)
- Group by model family based on documentation structure
- Create processing queue of ~150-200 curated modules (not 376+ random files)

### Step 2: Batch Processing with Checkpoints
```python
# Process in batches of 10 files
# Save checkpoint after each batch
# Track file hash to detect changes
# Retry failed files up to 3 times
```

### Step 3: For Each Module
1. **Extract Code Info**
   - Module docstring
   - Import statements
   - Package code from filename
   - Model family from path

2. **Gemini Analysis** (Don't skip this!)
   ```
   Analyze this FloPy module:
   - What groundwater modeling purpose does it serve?
   - When would users need this?
   - What concepts does it relate to?
   - Common errors/gotchas?
   ```

3. **Create Combined Embedding**
   ```
   Text = f"{package_code} {model_family} {docstring} {semantic_purpose}"
   Embedding = OpenAI(text)
   ```

4. **Store with Deduplication**
   - Check file hash
   - Update only if changed
   - Maintain processing log

## Phase 3: Package Aggregation

After processing all modules:
1. Group modules by package_code
2. Create package-level descriptions
3. Generate package embeddings from constituent modules
4. Identify cross-model packages (e.g., WEL exists in modflow, mf6, mfusg)

## Phase 4: Workflow Extraction

Process notebooks and examples:
1. Parse example scripts
2. Identify which packages are used together
3. Extract step-by-step workflows
4. Create workflow embeddings

## Phase 5: Search Implementation

### Search Modes
1. **EXACT** - Direct package code match
2. **SEMANTIC** - Vector similarity search
3. **FULLTEXT** - PostgreSQL ts_vector
4. **WORKFLOW** - Find by use case

### GraphQL API
```graphql
type Query {
  # Find packages/modules
  search(query: String!, mode: SearchMode!): SearchResult
  
  # Get specific package across all models
  getPackage(code: String!): Package
  
  # Find workflows/examples
  findWorkflow(useCase: String!): [Workflow]
}
```

## Phase 6: CI/CD Integration

### GitHub Actions Workflow
1. **Daily sync**
   - Pull latest FloPy
   - Check for changed files (hash comparison)
   - Process only changes
   
2. **Quality checks**
   - Ensure all files processed
   - Verify embeddings created
   - Test search accuracy

3. **Monitoring**
   - Track processing failures
   - Alert on missing packages
   - Performance metrics

## Implementation Strategy

### 1. Start Fresh
- Clear database schema
- No legacy columns
- Focus on core functionality

### 2. Process Systematically (Following Documentation Order)
- **MF6 Base Classes**: `flopy.mf6.mf*` modules first
- **MF6 Packages**: All documented `mfgwf*`, `mfgwt*` packages  
- **MODFLOW-2005**: Classic `flopy.modflow.mf*` modules
- **Specialized**: MT3D, MODPATH, SEAWAT modules
- **Utilities**: Utils, plotting, export modules
- **Examples/Workflows**: Process tutorial notebooks last

### 3. Validate Continuously
- Test SMS vs UZF search
- Verify package identification
- Check cross-model packages

### 4. Build for Scale
- Efficient batch processing
- Checkpoint recovery
- Incremental updates only

## Success Metrics

1. **Coverage**: 100% of documented modules processed (~150-200 modules, not 376+ files)
2. **Accuracy**: SMS returns Sparse Matrix Solver, not UZF 
3. **Completeness**: All documented packages have embeddings and descriptions
4. **Performance**: Search returns in <100ms
5. **Quality**: Only process what FloPy team considers documentation-worthy
6. **Maintainability**: CI/CD processes only changed files

## Next Steps

1. Create clean schema
2. Build robust processing pipeline
3. Process entire repository with checkpoints
4. Implement search API
5. Set up automated updates

This roadmap ensures we build a production-ready semantic database that truly understands FloPy's structure and purpose.
# FloPy Semantic Database

A comprehensive semantic search system for the FloPy Python package that enables natural language queries about groundwater modeling components.

## Problem Solved

Traditional keyword search in FloPy documentation often returns irrelevant results. For example, searching for "SMS" (Sparse Matrix Solver) incorrectly returns UZF (Unsaturated Zone Flow) packages due to superficial text similarity, not semantic understanding.

This project creates a semantic database that understands the **actual purpose and context** of each FloPy module, enabling accurate search that distinguishes between:
- **Solvers** (SMS - Sparse Matrix Solver)
- **Physical packages** (UZF - Unsaturated Zone Flow) 
- **Framework components** (BASE - foundational classes)
- **Management objects** (SIM - simulation orchestrator)

## Architecture

### Semantic Processing Pipeline

The system processes 224+ documented FloPy modules using:

1. **Documentation-Driven Discovery**: Uses FloPy's curated `.docs/code.rst` as the authoritative module list
2. **AI-Powered Analysis**: Gemini 2.5 Pro/Flash generates detailed semantic understanding in natural language
3. **High-Quality Embeddings**: OpenAI text-embedding-3-small creates 1536-dimensional vectors
4. **Dual Search Capabilities**: PostgreSQL FTS + vector similarity search

### Database Schema

**Primary Table: `flopy_modules`**
```sql
CREATE TABLE flopy_modules (
    id UUID PRIMARY KEY,
    file_path TEXT UNIQUE NOT NULL,
    relative_path TEXT NOT NULL,
    
    -- Extracted metadata
    model_family TEXT,           -- mf6, modflow, mt3d, utils, etc.
    package_code TEXT,          -- WEL, SMS, CHD, UZF, etc.
    
    -- Content
    module_docstring TEXT,
    source_code TEXT,
    
    -- AI-generated semantic analysis  
    semantic_purpose TEXT NOT NULL,     -- Detailed purpose analysis
    user_scenarios TEXT[],              -- When/how users apply this
    related_concepts TEXT[],            -- Related FloPy concepts
    typical_errors TEXT[],              -- Common mistakes and gotchas
    
    -- Search capabilities
    embedding_text TEXT NOT NULL,      -- Text used for embedding (debugging)
    embedding vector(1536) NOT NULL,   -- OpenAI semantic embedding
    search_vector tsvector,             -- PostgreSQL full-text search
    
    -- Metadata
    file_hash TEXT NOT NULL,           -- Content-based change detection
    last_modified TIMESTAMP,
    processed_at TIMESTAMP DEFAULT NOW(),
    
    -- Git tracking
    git_commit_hash TEXT,          -- Git commit SHA when processed
    git_branch TEXT,               -- Git branch name
    git_commit_date TIMESTAMP      -- Git commit timestamp
);
```

**Secondary Table: `pyemu_modules`** (separate from FloPy)
```sql
CREATE TABLE pyemu_modules (
    -- Similar structure but focused on uncertainty analysis
    -- and PEST integration concepts
);
```

### Semantic Analysis Example

**Input Module**: `flopy/mf6/modflow/mfsms.py`

**AI-Generated Analysis**:
```markdown
## Purpose
The SMS (Sparse Matrix Solver) package provides advanced numerical solution 
methods for MODFLOW 6 models, particularly for unstructured grids and complex 
geometries where standard solvers struggle with convergence.

## User Scenarios  
- Complex unstructured grid models requiring robust solver performance
- Models with extreme heterogeneity or sharp contrasts in hydraulic properties
- Large-scale simulations needing memory-efficient sparse matrix techniques

## Related Concepts
- IMS (Iterative Model Solution) - the standard MODFLOW 6 solver
- DISU/DISV packages - unstructured grids that benefit from SMS
- Numerical convergence and stability analysis

## Typical Errors
- Using SMS with structured grids where IMS would be more appropriate
- Incorrect solver parameter tuning leading to poor convergence
- Memory allocation issues with very large sparse matrices
```

## Features

### 🚀 Modern AI Integration
- **Google Genai SDK**: Latest official Google AI SDK (not deprecated libraries)
- **Markdown-Based Analysis**: Natural language generation instead of forced JSON
- **Context-Aware Processing**: Understands FloPy's groundwater modeling domain

### 🎯 Intelligent Search
- **Semantic Similarity**: Vector search finds conceptually related modules
- **Full-Text Search**: Fast keyword matching with PostgreSQL FTS  
- **Package Classification**: Automatic extraction of package codes (WEL, SMS, CHD, etc.)
- **Model Family Grouping**: Organized by FloPy versions (MF6, MODFLOW-2005, MT3D, etc.)

### 🔄 Robust Processing
- **Checkpoint System**: Resume processing after interruptions
- **Change Detection**: SHA256 file hashing prevents duplicate processing  
- **Batch Processing**: Rate-limited API calls with progress tracking
- **Error Handling**: Graceful fallbacks and retry logic

### 📊 Database Features
- **Neon PostgreSQL**: Cloud-native database with pgvector extension
- **Vector Similarity**: Cosine similarity search over 1536-dimensional embeddings
- **Full-Text Indexing**: GIN indexes for fast text search
- **Content Versioning**: Track file changes and reprocess only modified modules

## Installation & Setup

### Prerequisites
- Python 3.10+
- Neon PostgreSQL database with pgvector extension
- Google AI API key (Gemini)
- OpenAI API key

### Configuration

1. **Clone and setup**:
```bash
git clone <repository>
cd flopy_expert
pip install -r requirements.txt
```

2. **Configure API keys** in `config.py`:
```python
# Database
NEON_CONNECTION_STRING = "postgresql://user:pass@host/db?sslmode=require"

# AI API Keys  
GEMINI_API_KEY = "your_gemini_api_key"
OPENAI_API_KEY = "your_openai_api_key"

# Model Selection
GEMINI_MODEL = "gemini-2.5-flash"  # or "gemini-2.5-pro" for higher quality
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"

# Processing Settings
BATCH_SIZE = 10
```

### Database Setup

The database schema is automatically created on first run, including:
- Required PostgreSQL extensions (vector, uuid-ossp)
- Tables with proper indexes  
- Vector similarity indexes (ivfflat)
- Full-text search indexes (GIN)

## Usage

### Processing FloPy Modules

**Full Processing** (224+ modules, ~3 hours):
```bash
python3 run_processing_flopy.py
```

**Test Batch** (5 modules, ~3 minutes):
```bash
python3 run_test_batch.py
```

### Processing pyEMU Modules

**Full Processing** (28 modules, ~20 minutes):
```bash
python3 run_processing_pyemu.py
```

**Test Batch** (3 modules, ~2 minutes):
```bash
python3 run_test_batch_pyemu.py
```

### Example Processing Output
```
🚀 FloPy Semantic Database Processing
==================================================
Repository: /home/user/flopy_expert
Batch Size: 10
Gemini Model: gemini-2.5-flash

Processing MF6: 89 files
Processing batch 0 (mf6): 10 files
  Processing flopy/mf6/modflow/mfgwfwel.py...
    ✓ Saved WEL
  Processing flopy/mf6/modflow/mfgwfchd.py...
    ✓ Saved CHD
  ...
Batch 0 complete: 10 success, 0 failed

✅ All processing complete: 224 modules processed
```

### Checking Results

```bash
python3 check_database.py
python3 view_analysis.py
```

## Search Capabilities

### Semantic Search Examples

```sql
-- Find modules similar to "sparse matrix solver"
SELECT relative_path, package_code, semantic_purpose,
       1 - (embedding <=> %s::vector) as similarity
FROM flopy_modules
ORDER BY embedding <=> %s::vector  
LIMIT 5;
```

```sql
-- Full-text search for specific terms
SELECT relative_path, package_code, semantic_purpose
FROM flopy_modules
WHERE search_vector @@ to_tsquery('english', 'solver & matrix');
```

```sql  
-- Find all WEL package implementations across FloPy versions
SELECT relative_path, model_family, semantic_purpose
FROM flopy_modules  
WHERE package_code = 'WEL'
ORDER BY model_family;
```

```sql
-- Search by git commit (version-specific queries)
SELECT relative_path, package_code, git_branch, git_commit_date
FROM flopy_modules
WHERE git_commit_hash = 'a9735806...';
```

## Technical Details

### AI Processing Pipeline

1. **Module Discovery**: Parse `.docs/code.rst` for documented modules
2. **Code Analysis**: Extract docstrings, classes, functions using AST parsing
3. **Package Classification**: Regex-based extraction of package codes
4. **Semantic Analysis**: Gemini generates contextual understanding
5. **Embedding Creation**: OpenAI creates semantic vectors
6. **Database Storage**: PostgreSQL with vector similarity indexing

### Quality Assurance

- **Documentation-Driven**: Only processes officially documented modules
- **Content-Based Hashing**: Detects actual file changes, not timestamps
- **Fallback Analysis**: Graceful degradation when AI APIs fail
- **Comprehensive Logging**: Track processing success/failure rates

### Performance Optimizations

- **Batch Processing**: 10 files per batch with checkpoints
- **Rate Limiting**: Prevents API quota exhaustion
- **Vector Indexing**: Fast similarity search with ivfflat
- **Full-Text Indexing**: Optimized keyword search with GIN
- **Resume Capability**: Skip already processed files

## File Structure

```
flopy_expert/
├── src/
│   ├── processing_pipeline.py         # FloPy processing logic
│   ├── pyemu_processing_pipeline.py   # pyEMU processing logic
│   ├── docs_parser.py                 # FloPy documentation parser
│   ├── pyemu_docs_parser.py          # pyEMU documentation parser
│   └── graphql_api.py                # GraphQL API endpoint
├── tests/
│   ├── extract_mf6_modules.py        # Extract MF6 module information
│   └── qa_embedding_quality.py       # Quality assurance testing
├── config.py                         # Configuration settings
├── run_processing_flopy.py          # Process FloPy modules
├── run_processing_pyemu.py          # Process pyEMU modules
├── run_test_batch.py               # Test FloPy processing
├── run_test_batch_pyemu.py         # Test pyEMU processing
├── add_git_columns.py              # Git tracking migration
├── check_database.py               # Database inspection
└── view_analysis.py                # View semantic analysis
```

## Results & Current Status

### ✅ Completed Implementation

- **Interactive CLI**: Working semantic search interface (`search_cli.py`)
- **Vector Search**: Functional L2 distance-based similarity search  
- **Complete Database**: 329 items with comprehensive semantic analysis
- **MFUSG Support**: Added SMS and other MFUSG packages to the database
- **All Processing**: FloPy modules, workflows, PyEMU modules, and workflows complete

### ⚠️ Current Limitations

**Domain Expertise Gaps Identified Through Testing:**

1. **Complexity Ranking Issues**:
   - Search for "simple groundwater flow" returns GHB (General-Head Boundary) as "fundamental"
   - GHB is actually intermediate-to-advanced, not beginner-friendly
   - CHD (Constant Head) should rank higher for simple models

2. **Package Classification Problems**:
   - GWT (Groundwater Transport) appears in results for "simple MODFLOW 6 model"
   - Transport packages are advanced, not basic flow simulation
   - Missing complexity hierarchy understanding

3. **Semantic Search Limitations**:
   - Uses generic OpenAI embeddings, not MODFLOW-domain-specific
   - Lacks understanding of package prerequisites and dependencies
   - No distinction between beginner/intermediate/advanced workflows

### What Works Well

**✅ Content Discovery**: Successfully finds relevant modules and workflows
**✅ SMS Search**: Correctly identifies SMS as sparse matrix solver (top result)
**✅ Vector Search**: L2 distance properly ranks by semantic similarity
**✅ Comprehensive Coverage**: All documented FloPy and PyEMU content processed

### What Needs Improvement

**❌ Domain Intelligence**: Missing MODFLOW expertise in ranking results
**❌ Complexity Awareness**: No understanding of beginner vs advanced concepts  
**❌ Workflow Difficulty**: Cannot distinguish simple tutorials from complex examples

### Processing Statistics

- **233 FloPy modules** processed with semantic analysis (including MFUSG)
- **20 pyEMU modules** with uncertainty/PEST focus
- **72 FloPy workflows** from example notebooks
- **13 pyEMU workflows** from tutorial notebooks
- **1536-dimensional embeddings** for semantic similarity
- **Git tracking** for version-aware search capabilities

### Real-World Testing Results

**Query**: "simple groundwater flow model"
- **Expected**: CHD, DIS, IC packages (beginner-friendly)
- **Actual**: GHB, SFR, GWT packages (intermediate-to-advanced)
- **Issue**: No domain complexity understanding

**Query**: "what is the sms package"  
- **Expected**: SMS sparse matrix solver
- **Actual**: ✅ SMS found as top result
- **Status**: Working correctly

### Architectural Insight

The current system provides **semantic content discovery** but lacks **domain expertise intelligence**. It's essentially a sophisticated search engine rather than a MODFLOW expert system.

## Recent Enhancements

- ✅ **Git Integration**: Tracks processing by specific FloPy commits
- ✅ **pyEMU Support**: Separate semantic database for uncertainty analysis
- ✅ **Table Renaming**: `modules` → `flopy_modules` for clarity
- ✅ **Removed Unused Tables**: Cleaned up packages/workflows tables
- ✅ **Workflow Processing**: Extract workflows from FloPy example notebooks
- ✅ **PyEMU Workflows**: Process PyEMU Jupyter notebook tutorials
- ✅ **Comprehensive QA**: Quality assessment and reprocessing system
- ✅ **Retry Logic**: Robust error handling with exponential backoff
- ✅ **Embedding Quality**: All 4 tables now have high-quality semantic analysis

## Database Status

**All Systems Operational** ✅

- **FloPy Modules**: 224/224 excellent quality embeddings
- **FloPy Workflows**: 72/72 excellent quality embeddings  
- **PyEMU Modules**: 20/20 excellent quality embeddings
- **PyEMU Workflows**: 13/13 excellent quality embeddings

**Total**: 329 processed items with comprehensive semantic analysis

## Quality Metrics

- **Embedding Quality**: All items meet minimum thresholds (500+ chars for modules, 1000+ chars for workflows)
- **AI Analysis Success**: 100% of items have proper semantic purpose descriptions
- **Processing Reliability**: Retry logic with exponential backoff handles API failures
- **Validation Robustness**: Improved validation accepts partial results while maintaining quality

## Processing Commands

### FloPy Processing
```bash
# Full processing (224 modules, ~3 hours) - COMPLETE ✅
python3 run_processing_flopy.py

# Test batch (5 modules, ~3 minutes)
python3 run_test_batch.py

# FloPy workflows (72 workflows, ~1 hour) - COMPLETE ✅  
python3 run_processing_flopy_workflows.py
```

### PyEMU Processing
```bash
# Full processing (20 modules, ~15 minutes) - COMPLETE ✅
python3 run_processing_pyemu.py

# Test batch (3 modules, ~2 minutes)
python3 run_test_batch_pyemu.py

# PyEMU workflows (13 workflows, ~10 minutes) - COMPLETE ✅
python3 run_processing_pyemu_workflows.py
```

### Quality Assurance
```bash
# Comprehensive quality assessment across all tables
python3 tests/qa_embedding_quality.py

# Reprocess any poor quality embeddings (if needed)
python3 scripts/reprocess_poor_embeddings.py
python3 scripts/reprocess_pyemu_mc.py
```

## Future Enhancements

- **Complete GraphQL API**: Finish implementing the search endpoint
- **Cross-Database Search**: Unified search across FloPy and pyEMU
- **Advanced Analytics**: Pattern analysis across workflow types
- **Performance Optimization**: Further indexing and query optimization

## Contributing

This project demonstrates advanced semantic search capabilities for domain-specific technical documentation. The architecture can be adapted for other Python packages or technical documentation systems.

## DSPy Training Data Pipeline

### Stage 2: GitHub Issue Extraction (LangExtract + Claude SDK)

Successfully extracted structured information from 88 FloPy GitHub issues for DSPy training data generation.

#### Approach Comparison

**LangExtract (Pattern Matching)**:
- Extracted everything that looked like a module name
- Average: 7.3 extractions per issue (including duplicates and non-FloPy modules)
- Required extensive manual cleaning (removed 206 modules)

**Claude Code SDK (Intelligent Extraction)**:
- Understands context and extracts only relevant FloPy modules
- Average: 1-3 modules per issue (only actual buggy modules)
- Example: Issue #2150 extracted only `flopy.utils.cvfd_utils.shapefile_to_xcyc` instead of 17 modules

#### Results
- **56 issues processed** with Claude SDK (32 remaining; stopped due to Claude CLI not in PATH)
- **High-quality extractions** with clear problem descriptions and resolutions
- **Ready for Stage 3**: DSPy training data generation with processed issues
- **To Resume**: Add claude to PATH and run `python3 claude_process_all_robust.py`

See `/scripts/dspy_training_pipeline/` for the complete pipeline implementation.

## License

This project is for research and development purposes, built on top of the open-source FloPy package.
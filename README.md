# FloPy & pyEMU Semantic Database with MODFLOW 6 Examples

A comprehensive semantic search system for groundwater modeling that combines:
- **FloPy** Python package modules and workflows (233 modules + 72 workflows)
- **pyEMU** uncertainty analysis and PEST integration (20 modules + 13 workflows) 
- **MODFLOW 6 Examples** with real OpenAI embeddings (73 comprehensive examples)

Enables natural language queries about groundwater modeling with proper semantic search using 1536-dimensional embeddings.

## 🚀 Quick Start

```bash
# 1. Search the database interactively (all 411 items with real embeddings!)
python3 search_cli.py

# 2. Example semantic searches that now work properly:
# - "sparse matrix solver" → correctly returns SMS package
# - "henry problem saltwater" → finds Henry saltwater intrusion examples
# - "uncertainty analysis monte carlo" → finds pyEMU MC modules

# 3. Check database status
python3 -c "
import psycopg2, config
with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
    with conn.cursor() as cur:
        cur.execute('''
            SELECT table_name, count, status FROM (
                SELECT 'FloPy Modules' as table_name, COUNT(*) as count, 
                       'Full source code' as status FROM flopy_modules
                UNION ALL
                SELECT 'MODFLOW 6 Examples', COUNT(*), 
                       'Real OpenAI embeddings' FROM flopy_workflows 
                WHERE source_repository = 'modflow6-examples'
                UNION ALL  
                SELECT 'PyEMU Modules', COUNT(*), 
                       'Complete analysis' FROM pyemu_modules
            ) t ORDER BY count DESC
        ''')
        for row in cur.fetchall():
            print(f'{row[0]}: {row[1]} items - {row[2]}')
"
```

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

## 🎯 Ultra-Discriminative Embeddings

Advanced embedding system that generates hyper-specific technical questions impossible to answer without understanding the exact workflow implementation details.

### Performance Results
- **FloPy Workflows**: 54.4% → 70.7% accuracy (+16.3 percentage points)
- **PyEMU Workflows**: 52.0% → 56.0% accuracy (+4.0 percentage points)

### Key Innovation
Instead of generic descriptions, generates ultra-discriminative questions like:
- *"In this MF6 workflow, how does ModflowGwfdis handle cell2d array construction for DISV?"*
- *"Which pyemu.ParameterEnsemble method updates realizations using the Kalman gain?"*
- *"What specific IMS outer_maximum value does this tutorial use for PCG convergence?"*

### Usage
```bash
# Generate FloPy ultra-discriminative embeddings
python run_embedding_flopy.py --repository flopy
python run_embedding_flopy.py --repository modflow6-examples

# Generate PyEMU ultra-discriminative embeddings  
python run_embedding_pyemu.py
```

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

### Interactive Search CLI

The system includes a user-friendly command-line search interface:

```bash
# Start interactive search (all 411 items available)
python3 search_cli.py
```

**Example Queries:**
```
🔍 FloPy & pyEMU Semantic Search
Search query: what is the sms package
📊 Results:
  1. flopy/mf6/modflow/mfsms.py (SMS) - 0.85 similarity
     Purpose: Sparse Matrix Solver package for MODFLOW 6...

Search query: henry problem saltwater intrusion
📊 Results:
  1. scripts/ex-gwt-henry.py (HENRY) - 0.92 similarity
     Purpose: Classic Henry problem for variable-density flow...
  2. flopy_workflows: henry_density_flow.py - 0.87 similarity

Search query: uncertainty analysis monte carlo
📊 Results:
  1. pyemu.mc.MonteCarlo - 0.91 similarity
     Purpose: Monte Carlo uncertainty analysis framework...
```

### Checking Database Status

```bash
# Comprehensive database overview
python3 check_database.py

# View detailed semantic analysis samples
python3 view_analysis.py

# Quick status check
python3 -c "
import psycopg2, config
with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
    with conn.cursor() as cur:
        for table in ['flopy_modules', 'flopy_workflows', 'pyemu_modules', 'pyemu_workflows']:
            cur.execute(f'SELECT COUNT(*) FROM {table}')
            print(f'{table}: {cur.fetchone()[0]} items')
"
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
- **73 MODFLOW 6 examples** with Claude Code SDK enhanced analysis
- **1536-dimensional embeddings** for semantic similarity
- **Git tracking** for version-aware search capabilities
- **Total: 411 processed items** with comprehensive semantic analysis

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

## 🆕 MODFLOW 6 Examples with Claude Code SDK

### Advanced Multi-Source Processing Pipeline

The MODFLOW 6 examples represent the most sophisticated processing in the system, combining:

1. **LaTeX Documentation Analysis**: Extracts structured content from `/doc/sections/*.tex` files including:
   - Problem descriptions and mathematical formulations
   - Parameter tables and figure references  
   - Citations and theoretical background
   - Scenario breakdowns and subsections

2. **Python Code Analysis**: Comprehensive analysis of `/scripts/*.py` files:
   - Package detection (WEL, SFR, CHD, etc.)
   - FloPy module usage extraction (`flopy.mf6`, `flopy.utils`, etc.)
   - Model type classification (mf6-gwf, mf6-gwt, mf6-gwe, mf6-coupled)
   - Complexity scoring based on functions, classes, and mathematical operations

3. **Claude Code SDK Integration**: Domain-expert analysis generates:
   - **Question-oriented approach**: "When would I use this?", "What will I learn?"
   - **Real-world applications**: Specific consulting and research scenarios
   - **Technical learning objectives**: Key concepts and skills developed
   - **Smart complexity assessment**: Beginner/Intermediate/Advanced based on mathematical complexity, package sophistication, and prerequisites
   - **Rich embedding summaries**: 500-800 character semantic search optimized content

### Example of Enhanced Analysis

**Henry Problem (Saltwater Intrusion)**:
```yaml
Purpose: "Demonstrates mf6-coupled modeling addressing saltwater intrusion 
         with focus on general head boundaries using MODFLOW 6 capabilities"

Key Questions Answered:
  - "How do I simulate contaminant transport in groundwater?"
  - "How do I simulate saltwater intrusion problems?"
  - "What parameters control solute migration in this scenario?"

Use Cases:
  - "Coastal aquifer saltwater intrusion studies"
  - "Density-dependent flow simulation" 
  - "Seawater intrusion vulnerability assessment"

Tags: ['henry-problem', 'saltwater-intrusion', 'density-dependent', 
       'extraction', 'wells', 'transport', 'contamination']

Complexity: intermediate
```

### Processing Features

- **Robust Checkpointing**: Resume processing after interruptions
- **Error Recovery**: Individual example failures don't stop the pipeline  
- **GitHub Integration**: Automatic URL generation for each example
- **Multi-format Analysis**: Combines documentation richness with code intelligence
- **Domain Intelligence**: Claude Code SDK provides groundwater modeling expertise

### Architecture Benefits

This represents a **paradigm shift** from heuristic pattern matching to **true domain expertise**:
- Traditional approach: "This uses WEL package" 
- Claude-enhanced approach: "This demonstrates well injection scenarios for aquifer storage and recovery applications, suitable for practitioners working with municipal water supply optimization"

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
- ✅ **🆕 MODFLOW 6 Examples**: Claude Code SDK integration with multi-source analysis
- ✅ **🆕 Domain Expertise**: Question-oriented, practitioner-focused semantic content

## Database Status

**All Systems Operational** ✅

- **FloPy Modules**: 233/233 excellent quality embeddings
- **FloPy Workflows**: 72/72 excellent quality embeddings  
- **PyEMU Modules**: 20/20 excellent quality embeddings
- **PyEMU Workflows**: 13/13 excellent quality embeddings
- **MODFLOW 6 Examples**: 73/73 with Claude Code SDK enhanced analysis

**Total**: 411 processed items with comprehensive semantic analysis

## Quality Metrics

- **Embedding Quality**: All items meet minimum thresholds (500+ chars for modules, 1000+ chars for workflows)
- **AI Analysis Success**: 100% of items have proper semantic purpose descriptions
- **Processing Reliability**: Retry logic with exponential backoff handles API failures
- **Validation Robustness**: Improved validation accepts partial results while maintaining quality

## Processing Commands

### FloPy Processing
```bash
# Full processing (233 modules, ~3 hours) - COMPLETE ✅
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

### 🆕 MODFLOW 6 Examples Processing (Claude Code SDK Enhanced)
```bash
# Process all 73 MODFLOW 6 examples with robust checkpointing - COMPLETE ✅
python3 scripts/process_modflow6_all_robust.py

# Test with single example
python3 scripts/test_modflow6_single.py

# Test with batch of 5 examples  
python3 scripts/test_modflow6_batch5.py

# Check processing status
python3 scripts/process_modflow6_all_robust.py --summary

# View failed examples (if any)
python3 scripts/process_modflow6_all_robust.py --show-failed

# Retry failed examples only
python3 scripts/process_modflow6_all_robust.py --retry-failed
```

### Quality Assurance
```bash
# Comprehensive quality assessment across all tables
python3 tests/qa_embedding_quality.py

# Reprocess any poor quality embeddings (if needed)
python3 scripts/reprocess_poor_embeddings.py
python3 scripts/reprocess_pyemu_mc.py

# Enhance all MODFLOW 6 examples with Claude analysis (reprocess with better analysis)
python3 scripts/reprocess_with_claude.py
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
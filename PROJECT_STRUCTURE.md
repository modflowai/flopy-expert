# FloPy Expert Project Structure

## Overview
A comprehensive semantic database and analysis system for FloPy and pyEMU groundwater modeling packages.

## Directory Organization

### 📁 Core Directories

#### `/src/`
Production source code for the semantic database system:
- `flopy_processing_pipeline.py` - Main FloPy processing
- `pyemu_processing_pipeline.py` - PyEMU processing
- `flopy_embedding_pipeline.py` - FloPy ultra-discriminative embeddings
- `pyemu_embedding_pipeline.py` - PyEMU ultra-discriminative embeddings
- `flopy_workflow_extractor.py` - Workflow extraction
- `graphql_api.py` - GraphQL API implementation

#### `/tools/`
Organized utility scripts:
- **`/database/`** - Database management tools
  - `create_clean_schema.sql` - Database schema
- **`/test_processing/`** - Test model processing utilities
  - `check_*.py` - Various checking scripts
  - `fix_*.py` - Fixing and batch processing
  - `update_progress.py` - Progress tracking
- **`/search/`** - Search and query tools
  - `search_cli.py` - Interactive search CLI
  - `demo_searches.py` - Example searches
  - `test_search.py` - Search testing

#### `/scripts/`
Additional processing and analysis scripts:
- `add_modules_to_workflows.py` - Module tracking
- `batch_process_tests.py` - Batch test processing
- `claude_analyzer.py` - Claude AI integration
- **`/dspy_training_pipeline/`** - DSPy training system
- **`/github_flopy_extractor_issues/`** - GitHub issue extraction

#### `/test_review/`
Processed test models and results:
- **`/models/`** - All processed test models
- **`/scripts/`** - Test review utilities
- **`/utilities/`** - Configuration files
- **`/results/`** - Test results JSON files
- See `test_review/README_STRUCTURE.md` for details

#### `/tests/`
Test suites and quality assurance:
- `qa_embedding_quality.py` - Embedding QA
- `test_workflow_extraction.py` - Workflow tests
- `extract_mf6_modules.py` - MF6 extraction

#### `/utils/`
General utilities:
- `basic_mf6_model.py` - Basic model examples
- `check_database.py` - Database validation
- `demo_workflow_search.py` - Workflow search demos

#### `/docs/`
Documentation:
- `ROADMAP.md` - Project roadmap
- `CLEAN_START.md` - Setup instructions
- Various technical documentation

#### `/archive/`
Archived and deprecated files:
- **`/old_scripts/`** - Deprecated scripts
- **`/processing_checkpoints/`** - Old checkpoints
- **`/pyemu_checkpoints/`** - PyEMU checkpoints

### 📁 External Dependencies

#### `/flopy/`
FloPy repository (submodule or clone)

#### `/pyemu/`
pyEMU repository for uncertainty analysis

#### `/modflow6-examples/`
MODFLOW 6 example models

#### `/bin/`
MODFLOW executables

### 📁 DSPy Training System

#### `/dspy/`
DSPy integration for intelligent routing:
- **`/docs/`** - DSPy documentation

### 📁 Configuration

#### Root Configuration Files
- `config.py` - Main configuration
- `config.example.py` - Configuration template
- `requirements.txt` - Python dependencies
- `CLAUDE.md` - Claude AI memory/context
- `ARCHITECTURE.md` - System architecture

## Usage Workflow

### 1. Database Setup
```bash
# Create database schema
psql -f tools/database/create_clean_schema.sql

# Check database status
python utils/check_database.py
```

### 2. Processing Pipelines
```bash
# Process FloPy modules
python src/flopy_processing_pipeline.py

# Process pyEMU modules
python src/pyemu_processing_pipeline.py
```

### 3. Ultra-Discriminative Embeddings
```bash
# Generate FloPy workflow embeddings
python run_embedding_flopy.py --repository flopy
python run_embedding_flopy.py --repository modflow6-examples

# Generate PyEMU workflow embeddings
python run_embedding_pyemu.py
```

### 4. Test Model Processing
```bash
# Check all test models
python tools/test_processing/check_all_models.py

# Fix model issues
python tools/test_processing/fix_all_models.py
```

### 5. Search and Query
```bash
# Interactive search
python tools/search/search_cli.py

# Demo searches
python tools/search/demo_searches.py
```

## Key Features

### Semantic Database
- 233 FloPy modules processed
- 72 FloPy workflows analyzed
- 20 pyEMU modules indexed
- 73 MODFLOW 6 examples embedded

### Test Review System
- 56 test models converted to demonstrations
- 7-phase conceptual model for each test
- Comprehensive metadata and validation

### Ultra-Discriminative Embeddings
- Advanced v02 embedding system for workflows
- FloPy: 54.4% → 70.7% accuracy improvement
- PyEMU: 52.0% → 56.0% accuracy improvement  
- Hyper-specific technical question generation
- Domain-aware prompting for MODFLOW vs PEST++

### AI Integration
- OpenAI embeddings (text-embedding-3-small)
- Gemini 2.0 Flash for ultra-discriminative analysis
- Claude integration for assistance
- DSPy for intelligent routing

## Recent Improvements
- ✅ Organized file structure
- ✅ Separated tools from source code
- ✅ Archived deprecated scripts
- ✅ Created clear directory hierarchy
- ✅ Comprehensive documentation
- ✅ Ultra-discriminative embedding pipelines
- ✅ Professional v02 system integration

## Development Status
- **Production Ready**: Semantic database system
- **Active Development**: DSPy training pipeline
- **Testing Phase**: Test model demonstrations
- **Planning**: GraphQL API deployment

---
*Last updated: December 2024*
*FloPy Expert - Semantic Intelligence for Groundwater Modeling*
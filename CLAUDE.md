# FloPy & pyEMU Semantic Database Project - Claude Memory

## Project Overview

This project creates comprehensive semantic search systems for two major groundwater modeling packages:
- **FloPy**: Python interface for MODFLOW groundwater flow models (224 modules processed)
- **pyEMU**: Python framework for uncertainty analysis and PEST integration (28 modules ready)

**Core Problem Solved**: Traditional keyword search for "SMS" (Sparse Matrix Solver) incorrectly returns UZF (Unsaturated Zone Flow) packages due to superficial text similarity. Our semantic approach understands actual purpose and context.

## Current Architecture

### Modern AI Stack
- **Gemini 2.5 Pro/Flash**: Markdown-based semantic analysis (not JSON - better quality)
- **OpenAI text-embedding-3-small**: 1536-dimensional semantic vectors
- **Google Genai SDK**: Latest official SDK (not deprecated google-generativeai)
- **Neon PostgreSQL**: Cloud database with pgvector extension
- **Git Integration**: Track processing by commit hash, branch, and date

### Dual Database Design
1. **`flopy_modules`**: Groundwater modeling concepts (224 modules completed)
2. **`pyemu_modules`**: Uncertainty/PEST concepts (28 modules ready to process)

### Processing Pipeline
1. **Documentation-Driven Discovery**: 
   - FloPy: Uses `.docs/code.rst` as authoritative module list
   - pyEMU: Parses Sphinx autodoc format from docs
2. **AST Code Analysis**: Extract docstrings, classes, functions, package codes
3. **AI Semantic Analysis**: Gemini generates purpose, scenarios, concepts, errors
4. **Embedding Creation**: OpenAI creates semantic vectors
5. **Dual Search**: PostgreSQL FTS (keyword) + pgvector (semantic similarity)

## Database Schema

### FloPy Modules Table
```sql
CREATE TABLE flopy_modules (
    id UUID PRIMARY KEY,
    file_path TEXT UNIQUE NOT NULL,
    relative_path TEXT NOT NULL,
    
    -- Extracted metadata
    model_family TEXT,           -- mf6, modflow, mt3d, utils, etc.
    package_code TEXT,          -- WEL, SMS, CHD, UZF, etc.
    
    -- AI-generated semantic analysis  
    semantic_purpose TEXT NOT NULL,
    user_scenarios TEXT[],
    related_concepts TEXT[],
    typical_errors TEXT[],
    
    -- Search capabilities
    embedding_text TEXT NOT NULL,      -- For debugging
    embedding vector(1536) NOT NULL,
    search_vector tsvector,
    
    -- Metadata with Git tracking
    file_hash TEXT NOT NULL,
    last_modified TIMESTAMP,
    processed_at TIMESTAMP DEFAULT NOW(),
    git_commit_hash TEXT,
    git_branch TEXT,
    git_commit_date TIMESTAMP
);
```

### pyEMU Modules Table
```sql
CREATE TABLE pyemu_modules (
    -- Similar structure but different semantic fields:
    use_cases TEXT[],              -- When to use this method
    pest_integration TEXT[],       -- PEST/PEST++ workflow integration  
    statistical_concepts TEXT[],   -- Key statistical concepts
    common_pitfalls TEXT[]        -- Common usage mistakes
);
```

## Key Technical Decisions

### 1. Separate Tables for FloPy and pyEMU
- Different semantic focus (groundwater vs uncertainty)
- Different AI prompts and analysis
- Cleaner data organization
- Independent processing pipelines

### 2. Markdown Over JSON
- Gemini 2.5 excellent at natural language, poor at JSON
- Regex parsing of markdown sections works reliably
- Much higher quality semantic analysis

### 3. Git Tracking Implementation
- Capture commit hash, branch, date for each processed module
- Enable version-specific queries
- Track FloPy evolution over time

### 4. Table Renaming
- `modules` → `flopy_modules` for clarity
- Removed unused `packages` and `workflows` tables
- Cleaner, more focused schema

## Module Usage Tracking Enhancement ✨

### New Capabilities Added
We've enhanced the semantic database with precise FloPy module usage tracking for all 72 workflows:

**What's New:**
- **Source Code Analysis**: Intelligent extraction of FloPy imports and usage patterns
- **Precise Module Mapping**: Links workflow code to specific FloPy module files
- **Enhanced Schema**: New `modules_used` column and `workflow_module_usage` relationship table

### Database Schema Updates

#### Enhanced FloPy Workflows Table
```sql
ALTER TABLE flopy_workflows 
ADD COLUMN modules_used TEXT[] DEFAULT '{}';  -- Array of module file paths
```

#### New Workflow-Module Relationship Table  
```sql
CREATE TABLE workflow_module_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id UUID NOT NULL REFERENCES flopy_workflows(id) ON DELETE CASCADE,
    module_id UUID NOT NULL REFERENCES flopy_modules(id) ON DELETE CASCADE,
    import_type TEXT,  -- 'direct', 'from_import', 'class_import'
    confidence FLOAT DEFAULT 1.0,  -- Confidence score for the match
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(workflow_id, module_id)
);
```

### Extraction Process

The module extraction intelligently identifies FloPy usage patterns:

1. **Direct Imports**: `import flopy.utils.binaryfile`
2. **From Imports**: `from flopy.mf6.modflow import mfgwfchd`  
3. **Class Usage**: `flopy.mf6.ModflowGwf(...)`
4. **Nested Patterns**: `flopy.mf6.modflow.mfgwfdis.ModflowGwfdis`

### Results Summary

**Statistics:**
- **All 72 workflows** now have identified FloPy modules
- **125 unique modules** used across workflows (vs 233 total available)
- **Average 34 modules per workflow** (realistic, focused usage)
- **2,181 total relationships** with confidence scores

**Example Results:**
```sql
-- mf6_simple_model_example.py uses these key modules:
-- flopy/mf6/modflow/mfgwfchd.py (CHD package)
-- flopy/mf6/modflow/mfgwfdis.py (DIS package)  
-- flopy/mf6/modflow/mfgwfnpf.py (NPF package)
-- flopy/mf6/modflow/mfims.py (IMS solver)
-- flopy/utils/binaryfile.py (output processing)
```

### Usage Examples

**Find workflows using specific modules:**
```sql
SELECT fw.tutorial_file, fw.title
FROM flopy_workflows fw
WHERE 'flopy/mf6/modflow/mfgwfwel.py' = ANY(fw.modules_used);
```

**Analyze module popularity:**
```sql
SELECT fm.relative_path, fm.package_code, COUNT(*) as usage_count
FROM workflow_module_usage wmu 
JOIN flopy_modules fm ON wmu.module_id = fm.id
GROUP BY fm.id, fm.relative_path, fm.package_code
ORDER BY usage_count DESC;
```

**Compare package codes vs specific modules:**
```sql
-- Now you can distinguish between:
-- Package level: "WEL" (Well package)
-- Module level: "flopy/mf6/modflow/mfgwfwel.py" vs "flopy/modflow/mfwel.py"
```

This enhancement bridges the gap between high-level package concepts and specific implementation details, providing much more granular insight into FloPy usage patterns across the tutorial ecosystem.

## File Structure
```
flopy_expert/
├── src/
│   ├── processing_pipeline.py         # FloPy processing logic
│   ├── pyemu_processing_pipeline.py   # pyEMU processing logic
│   ├── docs_parser.py                 # FloPy documentation parser
│   ├── pyemu_docs_parser.py          # pyEMU documentation parser
│   └── graphql_api.py                # GraphQL API (partial)
├── scripts/
│   ├── add_modules_to_workflows_v2.py # ✨ NEW: Module usage extraction
│   └── check_simple_example.py       # ✨ NEW: Module usage verification
├── config.py                         # API keys and settings
├── run_processing_flopy.py          # Process FloPy (3+ hours)
├── run_processing_pyemu.py          # Process pyEMU (~20 min)
├── run_test_batch.py               # Test FloPy (5 modules)
├── run_test_batch_pyemu.py         # Test pyEMU (3 modules)
├── add_git_columns.py              # Git tracking migration
└── cleanup_packages_table.py        # Remove unused tables
```

## Processing Commands

### FloPy Processing
```bash
# Full processing (224 modules, ~3 hours) - ALREADY COMPLETE
python3 run_processing_flopy.py

# Test batch (5 modules, ~3 minutes)
python3 run_test_batch.py
```

### pyEMU Processing
```bash
# Full processing (28 modules, ~20 minutes) - READY TO RUN
python3 run_processing_pyemu.py

# Test batch (3 modules, ~2 minutes)
python3 run_test_batch_pyemu.py
```

## Search Examples

### Semantic Search
```sql
-- Find modules similar to "sparse matrix solver"
SELECT relative_path, package_code, semantic_purpose,
       1 - (embedding <=> query_embedding::vector) as similarity
FROM flopy_modules
ORDER BY embedding <=> query_embedding::vector
LIMIT 5;
```

### Git-Aware Search
```sql
-- Find modules from specific commit
SELECT * FROM flopy_modules 
WHERE git_commit_hash = 'a9735806...';

-- Find modules by branch
SELECT * FROM flopy_modules 
WHERE git_branch = 'develop';
```

### Package Search
```sql
-- Find all WEL implementations across versions
SELECT relative_path, model_family, git_branch
FROM flopy_modules
WHERE package_code = 'WEL'
ORDER BY model_family, git_commit_date;
```

## Current Status

### ✅ Completed - All Systems Operational
- **FloPy Modules**: All 233 modules with high-quality semantic analysis (including MFUSG with full source code)
- **FloPy Workflows**: All 72 workflows from example notebooks processed
- **PyEMU Modules**: All 20 modules with comprehensive semantic analysis
- **PyEMU Workflows**: All 13 workflows from Jupyter notebooks processed
- **MODFLOW 6 Examples**: All 73 examples with real OpenAI embeddings (text-embedding-3-small)
- **Interactive CLI**: Working semantic search interface (`search_cli.py`)
- **Vector Search**: Functional L2 distance-based similarity search in Neon PostgreSQL
- **MFUSG Integration**: Added SMS and other MFUSG packages with complete source code (fixed truncation bug)
- **Git Integration**: Tracking commit/branch/date for all modules
- **Table Architecture**: 8 related tables with foreign key relationships
- **Quality Assurance**: Comprehensive QA system with reprocessing capabilities
- **Retry Logic**: Robust error handling with exponential backoff across all processors
- **Module Usage Tracking**: Precise FloPy module usage extracted from workflow source code

### 📊 Database Statistics
- **Total Processed Items**: 411 (233 FloPy modules + 72 FloPy workflows + 73 MODFLOW 6 examples + 20 PyEMU modules + 13 PyEMU workflows)
- **Vector Search**: Working with L2 distance (`<->`) operator
- **Embedding Quality**: 100% have real OpenAI embeddings (no more dummy vectors)
- **AI Analysis Success**: 100% have proper semantic purpose descriptions
- **Processing Time**: ~5-6 hours total for all processing
- **Storage**: ~1536 × 411 = 631,296 dimensional vectors in pgvector
- **Workflow-Module Relationships**: 2,181 precise relationships across 125 unique modules
- **Source Code**: All modules have complete source code (MFUSG truncation bug fixed)

### ⚠️ Domain Expertise Limitations Discovered

**Real-World Testing Revealed Critical Issues:**

1. **Complexity Ranking Problems**:
   - Query: "simple groundwater flow model"
   - **Issue**: Returns GHB (General-Head Boundary) as "fundamental"
   - **Reality**: GHB is intermediate-to-advanced, not beginner-friendly
   - **Should Return**: CHD (Constant Head), DIS, IC for simple models

2. **Package Classification Errors**:
   - Query: "how can i build a simple modflow 6 model"
   - **Issue**: GWT (Groundwater Transport) appears as top result
   - **Reality**: Transport is advanced, not basic flow simulation
   - **Should Return**: Basic flow packages (GWF, DIS, CHD, IC)

3. **Missing Domain Hierarchy**:
   - **Beginner**: CHD, WEL, DIS, IC, NPF
   - **Intermediate**: GHB, DRN, RIV, MAW
   - **Advanced**: SFR, UZF, LAK, GWT, UZT

### 🔧 Vector Search Technical Resolution

**Problem Solved**: Cosine distance (`<=>`) operator returned 0 results in Neon PostgreSQL
**Solution**: Switched to L2 distance (`<->`) operator which works perfectly
**Result**: SMS (Sparse Matrix Solver) now correctly appears as top result for "sparse matrix solver"

**Technical Details**:
```sql
-- Broken: Cosine distance returns 0 results
SELECT package_code FROM flopy_modules 
ORDER BY embedding <=> '[0.1,0.2,...]'::vector

-- Working: L2 distance returns proper results  
SELECT package_code FROM flopy_modules
ORDER BY embedding <-> '[0.1,0.2,...]'::vector
```

### 🎯 What Works vs What Needs Work

**✅ Excellent for Content Discovery**:
- Finding relevant modules: SMS correctly identified for "sparse matrix solver"
- Comprehensive coverage: All FloPy/PyEMU documentation processed
- Technical search: Vector similarity finds semantically related content

**❌ Poor for Domain Expertise**:
- No complexity awareness: Can't distinguish beginner vs advanced
- Missing prerequisites: Doesn't understand package dependencies
- Generic embeddings: Uses general-purpose vectors, not MODFLOW-specific

### 🔄 Architecture Insight

**Current State**: Sophisticated semantic search engine
**Missing**: Domain expertise and complexity intelligence
**Gap**: Difference between "finding content" vs "understanding MODFLOW expertise"

The system excels at **semantic content discovery** but lacks **hydrogeological domain intelligence**. It's essentially a very good librarian, not a MODFLOW expert.

## Key Insights & Lessons

### Architecture Decisions That Worked
1. **Documentation-Driven**: Using official docs as source of truth
2. **Separate Databases**: FloPy and pyEMU have different focuses
3. **Git Tracking**: Version awareness from the start
4. **Markdown Analysis**: Natural language beats forced JSON

### Technical Gotchas Solved
1. **Package Code Extraction**: Complex regex patterns for different naming conventions
2. **Embedding Text**: Store what was embedded for debugging
3. **Safe Schema Updates**: Never drop tables, only add/enhance
4. **Checkpoint System**: Essential for long-running processes

### Processing Insights
- **FloPy Modules**: 233 modules in ~3.5 hours (about 54 seconds per module, including MFUSG)
- **FloPy Workflows**: 72 workflows in ~1 hour (about 50 seconds per workflow)  
- **PyEMU Modules**: 20 modules in ~15 minutes (about 45 seconds per module)
- **PyEMU Workflows**: 13 workflows in ~10 minutes (about 46 seconds per workflow)
- **Batch Processing**: Size of 10 with 2-second delays optimal
- **Consistency**: ~45-54 seconds per item across all processors
- **Reliability**: File hash deduplication prevents reprocessing
- **Efficiency**: Git info extraction adds minimal overhead
- **Vector Search**: L2 distance works in Neon, cosine distance has issues

### Domain Intelligence Lessons
- **Generic Embeddings Limitation**: OpenAI embeddings lack MODFLOW domain expertise
- **Complexity Hierarchy Missing**: No understanding of beginner vs advanced packages
- **Expert Knowledge Required**: Need domain-specific ranking beyond semantic similarity
- **User Testing Critical**: Academic correctness ≠ practical usability

## Safety Notes

### Database Operations
- Processing pipeline uses `CREATE TABLE IF NOT EXISTS` (never drops)
- Updates use `ON CONFLICT ... DO UPDATE` (safe upserts)
- File hash checking skips unchanged files
- All operations are non-destructive

### When Running Processing  
- **All Processing COMPLETE** - no need to rerun any full processing
- **Quality Verified** - all 338 items have excellent embeddings
- **Interactive CLI Available** - run `python3 search_cli.py` to test
- **Test batches available** for development/testing
- **Reprocessing tools** available for fixing individual items
- **Checkpoints enable resume** if interrupted during development

### Using the Interactive CLI
```bash
# Start the interactive search interface
python3 search_cli.py

# Example queries that work well:
# - "what is the sms package" → finds SMS (Sparse Matrix Solver) 
# - "sparse matrix solver" → SMS appears as top result
# - "pyemu monte carlo" → finds PyEMU uncertainty analysis

# Example queries that show limitations:
# - "simple groundwater flow" → returns advanced packages incorrectly
# - "basic modflow 6 model" → GWT (transport) appears instead of basic flow packages
```

## Quick Reference

### Check Database Status
```bash
python3 -c "
import psycopg2
import config
with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
    with conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM flopy_modules')
        flopy_modules = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM flopy_workflows')  
        flopy_workflows = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM pyemu_modules')
        pyemu_modules = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM pyemu_workflows')
        pyemu_workflows = cur.fetchone()[0]
        total = flopy_modules + flopy_workflows + pyemu_modules + pyemu_workflows
        print(f'📊 Database Status:')
        print(f'  FloPy modules: {flopy_modules}')
        print(f'  FloPy workflows: {flopy_workflows}')  
        print(f'  PyEMU modules: {pyemu_modules}')
        print(f'  PyEMU workflows: {pyemu_workflows}')
        print(f'  Total items: {total}')
"
```

### Quality Assessment
```bash
# Run comprehensive quality check across all tables
python3 tests/qa_embedding_quality.py
```

### Project Details
- **Neon Project**: autumn-math-76166931 (modflow_ai)
- **Database**: neondb
- **Region**: aws-us-east-2
- **FloPy Commit**: a9735806 (develop branch, 2025-07-09)

This semantic database demonstrates how AI can understand domain-specific technical documentation, enabling accurate search that goes beyond keywords to actual concepts and purposes.

## 🎯 NEW TASK: FloPy Test Processing Initiative (December 2024)

### Current Mission
Converting FloPy autotest files into educational, runnable demonstrations with rich metadata for database ingestion.

### Progress Status
- **Total Tests Identified**: 74+ test files in flopy/autotest/
- **Tests Processed**: 54 (as of December 2024)
- **Success Rate**: 100% - All processed tests run without errors
- **Time per Test**: ~15-30 minutes including debugging and documentation

### Test Processing Structure
Each test is transformed into:
```
test_review/models/test_[name]/basic/
├── model.py           # Runnable educational demonstration
├── metadata.json      # Rich metadata with 7-phase conceptual model
└── test_results.json  # Comprehensive test results and analysis
```

### Key Achievements
1. **Created Comprehensive Roadmap**: `test_review/PROCESSING_ROADMAP.md` with detailed phases and patterns
2. **Established Patterns**: Consistent structure for all test transformations
3. **Fixed Common Issues**: Array broadcasting, empty stress periods, MODPATH particle data
4. **7-Phase Conceptual Model**: Standardized metadata structure for all tests

### ⚠️ CRITICAL REQUIREMENT: Model Testing
**THE MOST IMPORTANT PART of test processing is to ACTUALLY TEST THE MODELS**
- All model.py files MUST be runnable and working
- Each model MUST be tested with `python3 model.py` before considering it complete
- Fix all errors immediately - no broken models allowed
- The goal is educational demonstrations that users can run and learn from
- A non-working model defeats the entire purpose of the transformation

### Recent Tests Processed (Latest Session)
- test_lgr.py - Local Grid Refinement
- test_swr_binaryread.py - SWR binary file utilities  
- test_util_2d_and_3d.py - Array utilities
- test_shapefile_utils.py - GIS integration
- test_str.py - Stream routing
- test_modflowoc.py - Output control
- test_modpathfile.py - MODPATH file utilities
- test_mp5.py - MODPATH-5
- test_mp6.py - MODPATH-6 with MNW2
- test_mp7.py - MODPATH-7 with MF6
- test_swi2.py - Salt Water Intrusion
- test_wel.py - Advanced Well package
- test_mp7_cases.py - MODPATH-7 test cases

### Metadata.json Structure (7-Phase Model)
1. **Grid Generation** - DIS, BAS packages
2. **Model Setup** - LPF, UPW, NPF packages
3. **Initial Conditions** - IC, Starting heads
4. **Boundary Conditions** - WEL, RCH, RIV, etc.
5. **Solver** - PCG, NWT, SMS, IMS
6. **Visualization** - OC, OBS
7. **Post-processing** - MODPATH, MT3D, ZoneBudget

### Common Fixes Applied
- **Array Broadcasting**: Convert lists to numpy arrays before operations
- **Empty Stress Periods**: Remove empty periods from stress_period_data
- **MODPATH Issues**: Use NodeParticleData for MP7+MF6, fix LRCParticleData
- **SWI2 Parameters**: Use solver2params dictionary format
- **MF6 Patterns**: Always create simulation container first

### Next Steps
- Continue processing remaining ~20 test files
- Maintain quality and consistency
- Update roadmap with new patterns discovered
- Commit progress regularly to GitHub

### Philosophy
"We are checking one by one manually all the metadata jsons and test results. It's worth it to do it one time and we won't have to work in the future."

## DSPy Training Pipeline Progress

### Stage 1: GitHub Issue Collection ✅
- Collected 88 high-quality closed issues from FloPy repository (2023-2025)
- Implemented date range filtering (DD-MM-YYYY format) and quality checks
- Created heuristic matching to link issues with flopy_modules database (50% match rate)

### Stage 1.5: Heuristic Enrichment ✅
- Built matching system using package codes, class names, and semantic descriptions
- Extracted class names from file paths (e.g., `mfgwfmaw.py` → `ModflowGwfmaw`)
- Created confidence scores and match reasons for DSPy routing

### Stage 2: Intelligent Extraction (In Progress)
Successfully compared two extraction approaches:

**LangExtract (Automated Pattern Matching):**
- Processed all 88 issues with 100% success rate
- Average 7.3 extractions per issue (high noise)
- Extracted non-FloPy modules (numpy, AlgoMesh, etc.)
- Required manual cleaning: removed 206 modules (52% reduction)

**Claude Code SDK (AI Understanding):**
- Uses Claude to actually understand each issue context
- Extracts only relevant FloPy modules with bugs
- Example: Issue #2150
  - LangExtract: 17 modules (including duplicates and non-FloPy)
  - Claude SDK: 1 module (`flopy.utils.cvfd_utils.shapefile_to_xcyc`)
- **56/88 issues processed** (stopped at issue #2086 due to Claude CLI not in PATH)
- Average: 1-3 modules per issue (only buggy modules)

The Claude SDK approach provides **true intelligent extraction** - understanding context rather than pattern matching. Each extraction includes:
- Specific FloPy modules/functions with bugs (full paths)
- Clear problem descriptions with error messages
- Resolutions with implementation details

### Key Results
- LangExtract required extensive post-processing to clean noise
- Claude SDK extracts are immediately usable for DSPy training
- Quality difference: LangExtract 4.6 modules/issue → Claude 1-3 modules/issue

### Stage 3: DSPy Training Data (Next)
Will use the high-quality Claude extractions to generate DSPy training examples for evidence-based routing to the correct FloPy modules.
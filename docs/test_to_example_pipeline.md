# FloPy Test-to-Example Pipeline Roadmap

## Overview

Convert FloPy autotest files into searchable, minimal working examples with semantic documentation. This pipeline extracts BOTH metadata for semantic search AND generates standalone runnable models, with automatic validation to ensure all examples work correctly.

## Architecture

### Directory Structure
```
test_review/
  prompts/
    test_binaryfile_reverse.md      # Claude prompt template (one per test)
    test_modflowdis.md              
    ...
  results/
    test_binaryfile_reverse.json    # Metadata + model code from Claude
    test_modflowdis.json
    ...
  models/                            # Generated standalone models
    test_binaryfile_reverse/
      dis/
        model.py                     # Runnable FloPy model
        metadata.json                # Classification & purpose
        test_results.json            # Validation results
      disv/                          # Only if test uses multiple discretizations
        model.py
        metadata.json
        test_results.json
    test_modflowdis/
      model.py                       # Single model for most tests
      metadata.json
      test_results.json
  status.json                        # Progress tracking
  validation_report.json             # Summary of all model tests
```

## Interactive CLI Workflow

### Main Interface
```bash
$ python review_tests.py

FloPy Test Review CLI
======================
[1/75] test_binaryfile_reverse.py

Found 3 model functions:
  - dis_sim: Phases [1, 3, 4, 5]
  - disv_sim: Phases [1, 3, 4, 5]
  - disu_sim: Phases [1, 3, 4, 5]

Options:
1. Generate standalone models with Claude
2. Create models manually
3. Skip (not useful for examples)
4. View test code
5. Test current model (if exists)
6. Validate ALL models
7. Next test
8. Previous test
9. Jump to test #
10. Show progress
0. Exit

Choice: _
```

### Key Features

1. **Dual Output**: Generates both metadata (for search) and runnable models
2. **Automatic Validation**: Tests every generated model to ensure it works
3. **Phase Detection**: Automatically identifies which of the 7 phases are used
4. **Smart Variants**: Only creates multiple models if test actually uses different discretizations
5. **Progress Tracking**: Saves state between sessions
6. **Quality Assurance**: Validates convergence, output files, and results

## Prompt Template Structure

### Updated Template: `prompts/test_[name].md`

The prompt now requests BOTH metadata extraction AND model generation:

```markdown
# Analyze FloPy Test: test_binaryfile_reverse.py

## Task: Extract Metadata AND Generate Standalone Model

### Part 1: METADATA EXTRACTION
Extract for semantic search database:
- Test purpose and usefulness as example
- Documentation (purpose, concepts, questions answered)
- Classification by 7 phases (primary and secondary)
- Search metadata (keywords, embedding string)

### Part 2: STANDALONE MODEL GENERATION
Create runnable FloPy model(s):
- Only create variants if test uses different discretizations
- Structure code following 7-phase organization
- Remove test assertions, add clear comments
- Must be executable and produce results

Return JSON with both metadata and model code.
```

## Result JSON Structure

### Complete Format: `results/test_binaryfile_reverse.json`

```json
{
  "test_name": "test_binaryfile_reverse.py",
  
  "metadata": {
    "true_purpose": "Tests HeadFile.reverse() and CellBudgetFile.reverse() methods",
    "is_useful_example": true,
    "example_demonstrates": "Binary file time reversal for post-processing",
    
    "documentation": {
      "purpose": "Demonstrates reversing time order in MODFLOW binary outputs",
      "key_concepts": ["Binary file manipulation", "Time reversal", "Post-processing"],
      "questions_answered": [
        "How do I reverse time order in binary files?",
        "What is HeadFile.reverse() method?",
        "Why are budget values negated when reversed?"
      ],
      "common_use_cases": [
        "Analyzing aquifer recovery after pumping",
        "Creating reverse-time animations",
        "Debugging from steady state"
      ]
    },
    
    "classification": {
      "primary_phase": 7,
      "phase_name": "Post-processing",
      "secondary_phases": [1, 2, 3, 4, 5],
      "modflow_version": "mf6",
      "packages_used": [
        "flopy.utils.HeadFile",
        "flopy.utils.CellBudgetFile",
        "flopy.mf6.ModflowGwfdis",
        "flopy.mf6.ModflowGwfdisv"
      ]
    },
    
    "search_metadata": {
      "keywords": ["binary file", "reverse time", "HeadFile", "post-processing"],
      "embedding_string": "Reverse time order in MODFLOW 6 binary output files..."
    }
  },
  
  "models": [
    {
      "variant": "dis",
      "description": "Structured grid version",
      "code": "#!/usr/bin/env python3\n# Complete runnable model code..."
    },
    {
      "variant": "disv",
      "description": "Vertex grid version",
      "code": "#!/usr/bin/env python3\n# Complete runnable model code..."
    }
  ]
}
```

## CLI Implementation

### Core Functions

```python
class TestReviewCLI:
    def __init__(self):
        # Initialize paths and load test files
        
    def extract_model_code(self, test_file):
        """Extract FloPy model building code from test"""
        
    def analyze_packages_in_code(self, code):
        """Categorize packages by 7 conceptual phases"""
        
    def create_standalone_model(self, test_file, model_func, variant):
        """Generate runnable model with phase organization"""
        
    def test_model(self, model_file, work_dir):
        """Run model and validate results"""
        # - Execute with Python
        # - Check convergence
        # - Verify output files
        # - Extract results
        
    def validate_all_models(self):
        """Test all generated models and create report"""
        
    def analyze_with_claude(self, test_file):
        """Send to Claude for metadata + model generation"""
```

## Progress Tracking

### `status.json` Structure

```json
{
  "current_index": 23,
  "total_tests": 75,
  "completed": [
    "test_binaryfile_reverse.py",
    "test_modflowdis.py"
  ],
  "skipped": [
    "test_conftest.py"
  ],
  "useful": [
    "test_modflowdis.py"
  ],
  "session_history": [
    {
      "date": "2024-01-15",
      "tests_reviewed": 10,
      "useful_found": 6
    }
  ]
}
```

## Model Validation

### Automatic Testing
Each generated model is automatically tested for:

```python
{
  "runs": true,           # Python executes without errors
  "converges": true,       # MODFLOW converges successfully
  "output_exists": true,   # Creates .hds/.bud/.cbb files
  "outputs": ["model.hds", "model.bud"],
  "error": null
}
```

### Validation Report
```json
{
  "test_binaryfile_reverse": {
    "dis": {"runs": true, "converges": true, "output_exists": true},
    "disv": {"runs": true, "converges": true, "output_exists": true},
    "disu": {"runs": false, "error": "Missing DISU data"}
  },
  "test_modflowdis": {
    "model": {"runs": true, "converges": true, "output_exists": true}
  }
}
```

## Pipeline Stages

### Stage 1: Interactive Review
- Review each test with Claude
- Extract metadata for search
- Generate standalone models
- Validate models run correctly

### Stage 2: Database Integration
- Load metadata into flopy_examples table
- Generate embeddings for semantic search
- Link models to metadata

### Stage 3: Quality Assurance
- Verify all models execute
- Check search functionality
- Test example discoverability

## Database Integration

### New Table: `flopy_examples`

```sql
CREATE TABLE flopy_examples (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT UNIQUE NOT NULL,
    source_test TEXT NOT NULL,
    version TEXT NOT NULL, -- mf6, mf2005, etc
    
    -- Code
    minimal_code TEXT NOT NULL,
    
    -- Classification  
    phase_primary INTEGER NOT NULL,
    phase_name TEXT NOT NULL,
    phase_secondary INTEGER[],
    
    -- Documentation
    purpose TEXT NOT NULL,
    questions_answered TEXT[],
    use_cases TEXT[],
    
    -- Search
    keywords TEXT[],
    embedding_string TEXT NOT NULL,
    embedding vector(1536),
    
    -- Metadata
    modules_primary TEXT[],
    modules_secondary TEXT[],
    is_runnable BOOLEAN DEFAULT true,
    
    created_at TIMESTAMP DEFAULT NOW(),
    reviewed_by TEXT,
    review_notes TEXT
);
```

## Claude Code SDK Integration

### Option 1: Manual Copy/Paste
1. CLI generates prompt file
2. User copies to Claude Code
3. User pastes result back
4. CLI validates and saves

### Option 2: Direct API Integration
```python
async def analyze_with_claude_api(prompt_text):
    """Direct Claude API call"""
    # Implementation depends on Claude Code SDK setup
    pass
```

## Success Metrics

- **Coverage**: Review all 75 test files
- **Useful Examples**: Extract 30-40 working examples with metadata
- **Model Quality**: 100% of generated models run and converge
- **Dual Output**: Each example has both searchable metadata AND runnable code
- **Classification**: All examples categorized by 7-phase structure
- **Validation**: Automatic testing ensures all models work

## Implementation Status

### ✅ Completed
- Interactive CLI (`review_tests.py`)
- Metadata extraction structure
- Standalone model generation
- Automatic validation system
- 7-phase organization
- Example model for test_binaryfile_reverse

### 🔄 Next Steps
1. **Process Tests**: Use CLI to review all 75 tests
2. **Generate Models**: Create standalone examples with Claude
3. **Validate All**: Run validation to ensure 100% work
4. **Database Load**: Add metadata to flopy_examples table
5. **Create Embeddings**: Generate vectors for semantic search
6. **Test Search**: Verify examples are discoverable
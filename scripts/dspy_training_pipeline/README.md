# DSPy Training Pipeline for FloPy

A three-stage pipeline to extract high-quality training data from FloPy GitHub issues for optimizing DSPy tool inputs.

## Overview

This pipeline transforms GitHub issues into structured training data through:
1. **Collection** - Fetch high-quality resolved issues from GitHub
2. **Extraction** - Use LangExtract to identify module references and patterns
3. **Generation** - Create DSPy training data with evidence-based routing

## Quick Start

```bash
# Stage 1: Collect GitHub issues
cd stage1_github_collector
python collect_issues.py --from-date 01-01-2022 --to-date 31-12-2024 --min-comments 2

# Stage 2: Extract structured data
cd ../stage2_langextract_processor
python extract_modules.py --input ../data/raw/flopy_issues_quality_*.json

# Stage 3: Generate DSPy training data
cd ../stage3_dspy_generator
python generate_training_data.py --input ../data/extracted/aggregated_evidence_*.json
```

## Pipeline Architecture

```
GitHub Issues → [Collector] → Raw JSON → [LangExtract] → Evidence → [Generator] → DSPy Training
```

Each stage is independent and cacheable, allowing iterative refinement without re-running expensive operations.

## Directory Structure

```
dspy_training_pipeline/
├── config/                       # Configuration files
│   ├── pipeline_config.yaml      # Pipeline settings
│   └── extraction_prompts.yaml   # LangExtract prompts
│
├── stage1_github_collector/      # GitHub data collection
│   ├── collect_issues.py         # Main collector
│   ├── github_client.py         # API wrapper
│   └── quality_filters.py       # Issue filtering
│
├── stage2_langextract_processor/ # Evidence extraction
│   ├── extract_modules.py        # Module references
│   ├── extract_patterns.py       # Error patterns
│   ├── extract_relationships.py  # Module relationships
│   └── aggregate_evidence.py     # Evidence merger
│
├── stage3_dspy_generator/        # Training generation
│   ├── generate_training_data.py # Main generator
│   ├── validate_routing.py       # Quality checks
│   └── export_formats.py         # Export utilities
│
├── data/                         # Data outputs (gitignored)
│   ├── raw/                      # GitHub issues
│   ├── extracted/                # LangExtract results
│   └── training/                 # DSPy datasets
│
└── utils/                        # Shared utilities
    ├── logging_config.py         # Logging setup
    ├── data_validators.py        # Validation
    └── visualization.py          # Result viewer
```

## Data Flow

### Stage 1 Output: Raw Issues
```json
{
  "issue_number": 1234,
  "title": "MAW package budget flux reversal",
  "body": "When using variable density flow...",
  "labels": ["bug", "mf6"],
  "comments": [...],
  "resolution": "Fixed in PR #5678"
}
```

### Stage 2 Output: Extracted Evidence
```json
{
  "issue_1234": {
    "module_references": [
      {
        "text": "MAW package",
        "module": "mfgwfmaw",
        "confidence": "high"
      }
    ],
    "error_patterns": [
      {
        "text": "budget flux reversal",
        "type": "numerical_error",
        "component": "budget"
      }
    ],
    "relationships": [
      {
        "modules": ["mfgwfmaw", "mfgwfbuy"],
        "type": "conflict",
        "condition": "variable_density"
      }
    ]
  }
}
```

### Stage 3 Output: DSPy Training Data
```json
{
  "question": "MAW package budget flux reversal with variable density",
  "structured_input": {
    "target_modules": ["mfgwfmaw", "mfgwfbuy"],
    "search_terms": ["budget", "flux", "reversal"],
    "search_type": "semantic",
    "confidence": "high"
  }
}
```

## Configuration

Edit `config/pipeline_config.yaml`:

```yaml
github:
  since_date: "2022-01-01"
  min_comments: 2
  max_issues: 200

langextract:
  model: "gemini-2.5-flash"
  extraction_passes: 3
  max_workers: 10

dspy:
  min_evidence_pieces: 2
  confidence_threshold: 0.7
```

## Development Status

- ✅ Stage 1: Basic implementation exists (needs refactoring)
- ❌ Stage 2: To be implemented
- ❌ Stage 3: To be implemented

## Contributing

1. Each stage should be independently runnable
2. Use timestamps for all output files
3. Add comprehensive logging
4. Write unit tests for filters and validators
5. Document prompt engineering decisions

## License

Part of the FloPy Expert project.
# GitHub FloPy Issues Extraction Pipeline - Roadmap

## Overview

A three-stage pipeline to extract high-quality training data from FloPy GitHub issues for DSPy optimization. Each stage is independent, cacheable, and iteratively refinable.

## Architecture Principles

1. **Decouple Data Collection from Processing** - Collect once, process many times
2. **Evidence-Based Extraction** - Extract structured evidence, not just labels
3. **Iterative Refinement** - Each stage can be improved without re-running previous stages
4. **Clean Codebase** - Organized scripts with clear separation of concerns

## File Structure

```
flopy_expert/
├── docs/
│   └── github_flopy_extractor/
│       ├── ROADMAP.md                    # This document
│       ├── conversation.md               # Original conversation
│       └── github_flopy_ext_ref.py       # Reference implementation
│
├── scripts/
│   └── dspy_training_pipeline/
│       ├── README.md                     # Pipeline documentation
│       ├── config/
│       │   ├── pipeline_config.yaml      # Configuration settings
│       │   └── extraction_prompts.yaml   # LangExtract prompts
│       │
│       ├── stage1_github_collector/
│       │   ├── collect_issues.py         # Main collector script
│       │   ├── github_client.py         # GitHub API wrapper
│       │   └── quality_filters.py       # Issue quality filtering
│       │
│       ├── stage2_langextract_processor/
│       │   ├── extract_modules.py        # Module reference extractor
│       │   ├── extract_patterns.py       # Error pattern extractor
│       │   ├── extract_relationships.py  # Module relationship extractor
│       │   └── aggregate_evidence.py     # Evidence aggregator
│       │
│       ├── stage3_dspy_generator/
│       │   ├── generate_training_data.py # DSPy training generator
│       │   ├── validate_routing.py       # Routing validation
│       │   └── export_formats.py         # Export utilities
│       │
│       ├── data/                         # Data directory (gitignored)
│       │   ├── raw/                      # Stage 1 outputs
│       │   ├── extracted/                # Stage 2 outputs
│       │   └── training/                 # Stage 3 outputs
│       │
│       └── utils/
│           ├── logging_config.py         # Logging setup
│           ├── data_validators.py        # Data validation
│           └── visualization.py          # Result visualization
```

## Stage 1: GitHub Collector

### Purpose
Collect high-quality closed issues from FloPy repository with rich discussion and resolution.

### Inputs
- GitHub API credentials
- Quality filter parameters (min_comments, since_date, etc.)

### Outputs
- `data/raw/flopy_issues_quality_[timestamp].json` - Raw issue data
- `data/raw/collection_stats_[timestamp].json` - Collection statistics

### Key Features
- Rate limit handling
- Quality filtering (closed, commented, recent)
- Full conversation capture (issue + comments)
- Metadata preservation

### Implementation Status
✅ Basic implementation exists (needs refactoring)

## Stage 2: LangExtract Processor

### Purpose
Extract structured evidence from raw issues using LangExtract's precise source grounding.

### Inputs
- Raw issues from Stage 1
- Extraction prompts (module references, error patterns, relationships)

### Outputs
- `data/extracted/module_references_[timestamp].jsonl`
- `data/extracted/error_patterns_[timestamp].jsonl`
- `data/extracted/relationships_[timestamp].jsonl`
- `data/extracted/aggregated_evidence_[timestamp].json`

### Extraction Types

#### 2.1 Module References
```python
examples = [
    {
        "text": "The WEL package throws an error",
        "extractions": [{
            "extraction_class": "module_reference",
            "extraction_text": "WEL package",
            "attributes": {
                "module_name": "mfgwfwel",
                "reference_type": "explicit",
                "confidence": "high"
            }
        }]
    }
]
```

#### 2.2 Error Patterns
```python
examples = [
    {
        "text": "budget flux reversal when using variable density",
        "extractions": [{
            "extraction_class": "error_pattern",
            "extraction_text": "budget flux reversal",
            "attributes": {
                "error_type": "numerical",
                "component": "budget",
                "severity": "data_corruption"
            }
        }]
    }
]
```

#### 2.3 Module Relationships
```python
examples = [
    {
        "text": "MAW package conflicts with BUY when density varies",
        "extractions": [{
            "extraction_class": "module_relationship",
            "extraction_text": "MAW package conflicts with BUY",
            "attributes": {
                "module_1": "mfgwfmaw",
                "module_2": "mfgwfbuy",
                "relationship": "conflict",
                "condition": "variable_density"
            }
        }]
    }
]
```

### Implementation Status
❌ To be implemented

## Stage 3: DSPy Training Generator

### Purpose
Convert extracted evidence into structured training data for DSPy tool input optimization.

### Inputs
- Aggregated evidence from Stage 2
- Module mapping configuration

### Outputs
- `data/training/dspy_training_data.json` - Final training dataset
- `data/training/validation_report.html` - Visual validation report

### Training Data Format
```json
{
  "training_examples": [
    {
      "question": "MAW package budget flux reversal with variable density",
      "evidence": {
        "module_mentions": ["MAW package", "budget calculations"],
        "error_patterns": ["flux reversal", "mass balance"],
        "related_modules": ["BUY package"]
      },
      "structured_input": {
        "target_modules": ["mfgwfmaw", "mfgwfbuy"],
        "search_terms": ["budget", "flux", "reversal", "density"],
        "search_type": "semantic",
        "confidence": "high",
        "focus_area": "budget_analysis"
      }
    }
  ]
}
```

### Implementation Status
❌ To be implemented

## Development Phases

### Phase 1: Foundation (Week 1)
- [ ] Refactor existing GitHub collector into clean structure
- [ ] Set up configuration management
- [ ] Create data directory structure
- [ ] Add comprehensive logging

### Phase 2: LangExtract Integration (Week 2)
- [ ] Implement module reference extractor
- [ ] Implement error pattern extractor
- [ ] Implement relationship extractor
- [ ] Create evidence aggregator

### Phase 3: DSPy Generation (Week 3)
- [ ] Design training data schema
- [ ] Implement evidence-to-training converter
- [ ] Add validation and quality checks
- [ ] Create visualization tools

### Phase 4: Optimization (Week 4)
- [ ] Iterate on extraction prompts
- [ ] Refine quality filters
- [ ] A/B test different approaches
- [ ] Documentation and examples

## Success Metrics

1. **Coverage**: Extract module references from >80% of quality issues
2. **Precision**: >90% accuracy in module identification
3. **Evidence Quality**: Average 3+ evidence pieces per routing decision
4. **Training Quality**: DSPy achieves >85% routing accuracy

## Next Steps

1. Review and approve this roadmap
2. Set up the directory structure
3. Begin Phase 1 implementation
4. Weekly progress reviews

## Notes

- Each stage should be runnable independently
- All data outputs should be versioned with timestamps
- Configuration should be external (YAML/JSON)
- Comprehensive logging at each stage
- Focus on evidence quality over quantity
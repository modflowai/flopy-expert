# Stage 1.5: Heuristic Module Matcher

This intermediate stage enriches GitHub issues with module references from the flopy_modules database using heuristic matching.

## Purpose

Bridge the gap between informal GitHub language and formal FloPy module structure by:
- Matching package codes (WEL, MAW, CHD)
- Extracting class names from file paths (ModflowGwfmaw, ModflowWel)
- Identifying module mentions in natural language
- Parsing error messages and stack traces

## Usage

```bash
# Enrich issues with module matches
python enrich_with_modules.py \
    --input ../data/raw/flopy_issues_quality_*.json \
    --output ../data/enriched/
```

## Output Format

Each issue is enriched with matched modules:

```json
{
  "issue_number": 1234,
  "title": "MAW package budget error",
  "matched_modules": [
    {
      "class_name": "ModflowGwfmaw",
      "package_code": "MAW",
      "file_path": "flopy/mf6/modflow/mfgwfmaw.py",
      "model_family": "mf6",
      "confidence": "high",
      "match_type": "package_code_in_title",
      "match_context": "MAW package"
    }
  ],
  "original_issue": {...}
}
```

## Confidence Levels

- **high**: Direct match (class name, file path, package code)
- **medium**: Pattern match (partial names, descriptions)
- **low**: Fuzzy match (related terms, semantic similarity)

## Match Types

- `class_name_exact`: Exact class name found
- `package_code_exact`: Package code match (WEL, MAW)
- `file_path_exact`: File path mentioned
- `error_trace`: Found in stack trace
- `import_statement`: Found in import
- `natural_language`: Matched description
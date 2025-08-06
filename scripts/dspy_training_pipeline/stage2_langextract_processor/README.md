# Stage 2: LangExtract Comprehensive Issue Analysis

This stage uses Google's LangExtract to perform deep analysis of GitHub issues, extracting all relevant information in a single pass to avoid reprocessing.

## Purpose

Extract comprehensive structured data from FloPy GitHub issues including:
- Complete problem descriptions with error patterns
- All module references (primary, secondary, imports, file paths)
- Code snippets (reproducers, workarounds, solutions)
- Environment and version information
- Full comment thread analysis
- Resolution details and patterns

## Usage

```bash
# Process enriched issues with LangExtract
python extract_comprehensive.py \
    --input ../data/enriched/enriched_*.json \
    --output ../data/extracted/
    
# Optional: Use Gemini 2.5 Pro for more complex extraction
python extract_comprehensive.py \
    --input ../data/enriched/enriched_*.json \
    --output ../data/extracted/ \
    --model gemini-2.5-pro
```

## Extraction Schema

The comprehensive extraction captures:

### 1. Problem Analysis
- Main issue description
- Error messages and stack traces
- Symptoms and user observations
- Problem category (compatibility, regression, feature gap)

### 2. Module Identification
- **Primary modules**: Directly mentioned in issue
- **Secondary modules**: Found in code examples
- **Stack trace modules**: Extracted from error traces
- **Import chains**: Module dependencies

### 3. Code Context
- **Reproducer code**: Minimal example to reproduce
- **Workaround code**: Temporary fixes
- **Solution code**: Final implementation
- **Test cases**: Validation code

### 4. Environment Details
- FloPy version
- MODFLOW version
- Python version and OS
- Dependency versions
- Configuration settings

### 5. Discussion Analysis
- Developer insights and explanations
- User feedback and confirmations
- Related issue references
- Pull request links

### 6. Resolution Patterns
- Resolution type (code fix, workaround, version constraint)
- Fixed version or branch
- Time to resolution
- Commit references

## Output Format

```json
{
  "issue_2497": {
    "problem": {
      "description": "Mf6Splitter does not work when ATS is active",
      "error_messages": ["'ModflowUtlats' object has no attribute 'parent_package'"],
      "symptoms": ["model splitting fails with ATS"]
    },
    "modules": {
      "primary": ["Mf6Splitter", "ModflowUtlats"],
      "secondary": ["ModflowTdis", "ModflowIms"],
      "imports": ["flopy.mf6.utils.Mf6Splitter"],
      "file_paths": ["flopy/mf6/utils/mfsplitter.py"]
    },
    "code_snippets": {
      "reproducer": "sim = flopy.mf6.MFSimulation(...)",
      "workaround": "prepare input files by hand",
      "solution": "ATS support implemented"
    },
    "environment": {
      "flopy_version": "3.9.2",
      "modflow_version": "6.6.1",
      "os": "Windows 11"
    },
    "resolution": {
      "type": "code_fix",
      "fixed_in": "develop",
      "resolver": "jlarsen-usgs",
      "time_to_fix_days": 10
    }
  }
}
```

## Benefits

1. **Single Pass Processing**: Extract everything at once
2. **Complete Context**: Full problem-solution pairs
3. **Rich Relationships**: Module interactions and dependencies
4. **Pattern Learning**: Common problem categories and solutions
5. **Version Awareness**: Track version-specific issues

This comprehensive extraction provides high-quality training data for DSPy to learn complex routing patterns based on real-world FloPy usage.
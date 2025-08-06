# Stage 1: GitHub Issue Collector

This stage collects high-quality issues from the FloPy GitHub repository for DSPy training data generation.

## Quick Start

### 1. Count Issues First (Recommended)

Before collecting, check how many issues exist in your date range:

```bash
# Count all issues from 2022-2024
python count_issues.py --from-date 01-01-2022 --to-date 31-12-2024

# Show monthly breakdown
python count_issues.py --from-date 01-01-2022 --to-date 31-12-2024 --by-month

# Show label distribution
python count_issues.py --from-date 01-01-2022 --to-date 31-12-2024 --by-label
```

### 2. Collect Issues

Based on the counts, collect issues in manageable batches:

```bash
# Collect closed issues from 2023
python collect_issues.py --from-date 01-01-2023 --to-date 31-12-2023

# Collect with specific criteria
python collect_issues.py \
    --from-date 01-01-2022 \
    --to-date 31-12-2022 \
    --min-comments 3 \
    --max-issues 100
```

## Scripts

### `count_issues.py`
Quick issue counter without downloading full data. Use this to:
- Check issue volume in date ranges
- See monthly/label distributions
- Estimate quality metrics
- Plan collection batches

### `collect_issues.py`
Main collector that downloads issues with:
- Quality filtering (comments, labels, content)
- Comment enrichment
- Module mention detection
- Statistics generation

### `quality_filters.py`
Filtering logic to identify high-quality issues suitable for training.

## Output Files

Data is saved to `../data/raw/`:

- `flopy_issues_quality_YYYYMMDD_HHMMSS.json` - Main issue data
- `collection_stats_YYYYMMDD_HHMMSS.json` - Collection statistics

## Quality Criteria

Issues must meet these criteria:
- **State**: Closed (resolved issues have validated solutions)
- **Comments**: Minimum 2 (indicates discussion/resolution)
- **Date Range**: Within specified from/to dates
- **Content**: Minimum 50 characters in body
- **Relevance**: Contains FloPy-specific terms

## Date Range Strategy

For optimal results:
1. Use `count_issues.py` to analyze distribution
2. Split large ranges into ~50-100 issues each
3. Focus on recent years (2022+) for current module structure

Example workflow:
```bash
# 1. Count total
python count_issues.py --from-date 01-01-2022 --to-date 31-12-2024

# 2. Check monthly distribution
python count_issues.py --from-date 01-01-2022 --to-date 31-12-2024 --by-month

# 3. Collect in batches based on distribution
python collect_issues.py --from-date 01-01-2023 --to-date 30-06-2023
python collect_issues.py --from-date 01-07-2023 --to-date 31-12-2023
```

## Environment Variables

Set GitHub token for higher API limits:
```bash
export GITHUB_TOKEN="your_github_token"
```

Without token: 60 requests/hour
With token: 5000 requests/hour
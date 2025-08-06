#!/usr/bin/env python3
"""
Quick Issue Counter for FloPy Repository

A lightweight script to count issues by date ranges and other criteria
without downloading all the data.

Usage:
    python count_issues.py --from-date 2022-01-01 --to-date 2023-12-31
    python count_issues.py --from-date 2022-01-01 --to-date 2023-12-31 --by-month
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
from typing import Dict, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent.parent / '.env'
load_dotenv(env_path)

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from docs.github_flopy_extractor.github_flopy_ext_ref import (
    GitHubFloPyExtractor, GitHubConfig
)


def parse_date(date_str: str) -> datetime:
    """Parse date in DD-MM-YYYY format"""
    return datetime.strptime(date_str, "%d-%m-%Y")


def count_issues_by_criteria(from_date: str, to_date: str, state: str = "all", 
                           by_month: bool = False, by_label: bool = False):
    """Count issues within date range with various groupings"""
    
    # Set up GitHub client
    github_token = os.getenv("GITHUB_TOKEN")
    config = GitHubConfig(token=github_token)
    extractor = GitHubFloPyExtractor(config)
    
    print(f"Counting {state} issues from {from_date} to {to_date}...")
    print(f"Repository: {config.owner}/{config.repo}\n")
    
    # Convert dates
    start_date = parse_date(from_date)
    end_date = parse_date(to_date)
    
    # Fetch issues
    print("Fetching issues from GitHub API...")
    all_issues = extractor.get_issues(state=state)
    
    # Filter by date range
    filtered_issues = []
    for issue in all_issues:
        issue_date = issue.created_at.replace(tzinfo=None)
        if start_date <= issue_date <= end_date:
            filtered_issues.append(issue)
    
    if len(all_issues) >= 1000:
        print("\n⚠️  WARNING: GitHub API limit reached (1000 issues)")
        print("   Some issues may not be included in the count.")
        print("   Consider using more specific filters or date ranges.\n")
    
    # Basic counts
    total_count = len(filtered_issues)
    open_count = sum(1 for i in filtered_issues if i.state == "open")
    closed_count = sum(1 for i in filtered_issues if i.state == "closed")
    
    print(f"Total issues in range: {total_count}")
    print(f"  Open: {open_count}")
    print(f"  Closed: {closed_count}")
    
    # Count by month if requested
    if by_month:
        print("\nBy Month:")
        monthly_counts = defaultdict(int)
        for issue in filtered_issues:
            month_key = issue.created_at.strftime("%Y-%m")
            monthly_counts[month_key] += 1
        
        for month in sorted(monthly_counts.keys()):
            print(f"  {month}: {monthly_counts[month]}")
    
    # Count by label if requested
    if by_label:
        print("\nTop 20 Labels:")
        label_counts = defaultdict(int)
        for issue in filtered_issues:
            for label in issue.labels:
                label_counts[label] += 1
        
        sorted_labels = sorted(label_counts.items(), key=lambda x: x[1], reverse=True)
        for label, count in sorted_labels[:20]:
            print(f"  {label}: {count}")
    
    # Quality metrics
    print("\nQuality Metrics:")
    with_comments = sum(1 for i in filtered_issues if i.comments_count > 0)
    high_engagement = sum(1 for i in filtered_issues if i.comments_count >= 5)
    avg_comments = sum(i.comments_count for i in filtered_issues) / total_count if total_count > 0 else 0
    
    print(f"  Issues with comments: {with_comments} ({with_comments/total_count*100:.1f}%)")
    print(f"  High engagement (5+ comments): {high_engagement} ({high_engagement/total_count*100:.1f}%)")
    print(f"  Average comments per issue: {avg_comments:.1f}")
    
    # Module mention estimation
    module_keywords = ['mf6', 'wel', 'chd', 'drn', 'riv', 'ghb', 'maw', 'sfr', 'lak', 'uzf']
    with_modules = 0
    for issue in filtered_issues:
        text = f"{issue.title} {issue.body or ''}".lower()
        if any(keyword in text for keyword in module_keywords):
            with_modules += 1
    
    print(f"  Likely module-specific issues: {with_modules} ({with_modules/total_count*100:.1f}%)")
    
    return filtered_issues


def suggest_date_ranges(total_issues: int, target_per_range: int = 50):
    """Suggest date ranges to get approximately target number of issues"""
    print(f"\nSuggested date ranges for ~{target_per_range} issues each:")
    
    suggested_ranges = []
    num_ranges = max(1, total_issues // target_per_range)
    
    # This is a simple suggestion - in practice you'd analyze actual distribution
    print(f"  Consider splitting into {num_ranges} ranges")
    print(f"  Use --by-month flag to see distribution and pick ranges accordingly")


def main():
    parser = argparse.ArgumentParser(description="Count FloPy GitHub issues by date range")
    parser.add_argument("--from-date", required=True, help="Start date (DD-MM-YYYY)")
    parser.add_argument("--to-date", required=True, help="End date (DD-MM-YYYY)")
    parser.add_argument("--state", default="all", choices=["open", "closed", "all"],
                       help="Issue state to count")
    parser.add_argument("--by-month", action="store_true", help="Show monthly breakdown")
    parser.add_argument("--by-label", action="store_true", help="Show label breakdown")
    parser.add_argument("--suggest-ranges", action="store_true", 
                       help="Suggest date ranges for batching")
    
    args = parser.parse_args()
    
    # Validate dates
    try:
        parse_date(args.from_date)
        parse_date(args.to_date)
    except ValueError:
        print("Error: Dates must be in DD-MM-YYYY format")
        sys.exit(1)
    
    # Count issues
    issues = count_issues_by_criteria(
        args.from_date, 
        args.to_date, 
        args.state,
        args.by_month,
        args.by_label
    )
    
    # Suggest ranges if requested
    if args.suggest_ranges and issues:
        suggest_date_ranges(len(issues))


if __name__ == "__main__":
    main()
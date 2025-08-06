#!/usr/bin/env python3
"""
Stage 1: GitHub Issues Collector for FloPy

This script collects high-quality issues from the FloPy GitHub repository
and saves them as JSON files for further processing.

Usage:
    python collect_issues.py --since-date 2022-01-01 --min-comments 2
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent.parent / '.env'
load_dotenv(env_path)

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from docs.github_flopy_extractor.github_flopy_ext_ref import (
    GitHubFloPyExtractor, GitHubConfig, Issue
)

from quality_filters import IssueQualityFilter
sys.path.append(str(Path(__file__).parent.parent))
from utils.logging_config import setup_logging


class FloPyIssueCollector:
    """Collects and filters GitHub issues from FloPy repository"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize collector with configuration"""
        self.config = config or {}
        self.logger = setup_logging("issue_collector")
        
        # Set up GitHub client
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            self.logger.warning("GITHUB_TOKEN not set. API rate limits will be lower.")
            
        self.github_config = GitHubConfig(token=github_token)
        self.extractor = GitHubFloPyExtractor(self.github_config)
        
        # Set up quality filter
        date_range = self.config.get("date_range", {})
        self.quality_filter = IssueQualityFilter(
            min_comments=self.config.get("min_comments", 2),
            from_date=date_range.get("from_date", "01-01-2022"),
            to_date=date_range.get("to_date", None),
            required_labels=self.config.get("required_labels", []),
            excluded_labels=self.config.get("excluded_labels", ["duplicate", "wontfix"])
        )
        
        # Set up output directory
        self.output_dir = Path(__file__).parent.parent / "data" / "raw"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def collect_issues(self, state: str = "closed", max_issues: Optional[int] = None) -> List[Issue]:
        """Collect issues from GitHub with quality filtering"""
        self.logger.info(f"Collecting {state} issues from {self.github_config.owner}/{self.github_config.repo}")
        
        # Fetch all issues
        all_issues = self.extractor.get_issues(state=state)
        self.logger.info(f"Fetched {len(all_issues)} total {state} issues")
        
        # Apply quality filters
        quality_issues = []
        for issue in all_issues:
            if self.quality_filter.is_quality_issue(issue):
                quality_issues.append(issue)
                
            if max_issues and len(quality_issues) >= max_issues:
                break
                
        self.logger.info(f"Filtered to {len(quality_issues)} quality issues")
        return quality_issues
        
    def enrich_issue_with_comments(self, issue: Issue) -> Dict[str, Any]:
        """Enrich issue data with comments for better context"""
        issue_dict = self._issue_to_dict(issue)
        
        # Fetch comments if issue has them
        if issue.comments_count > 0:
            try:
                comments = self._fetch_issue_comments(issue.number)
                issue_dict["comments"] = comments
                self.logger.debug(f"Added {len(comments)} comments to issue #{issue.number}")
            except Exception as e:
                self.logger.warning(f"Failed to fetch comments for issue #{issue.number}: {e}")
                issue_dict["comments"] = []
        else:
            issue_dict["comments"] = []
            
        return issue_dict
        
    def _fetch_issue_comments(self, issue_number: int) -> List[Dict[str, Any]]:
        """Fetch comments for a specific issue"""
        endpoint = f"repos/{self.github_config.owner}/{self.github_config.repo}/issues/{issue_number}/comments"
        comments_data = self.extractor._paginate(endpoint)
        
        comments = []
        for comment in comments_data:
            comments.append({
                "id": comment["id"],
                "author": comment["user"]["login"],
                "created_at": comment["created_at"],
                "updated_at": comment["updated_at"],
                "body": comment["body"]
            })
            
        return comments
        
    def _issue_to_dict(self, issue: Issue) -> Dict[str, Any]:
        """Convert Issue dataclass to dictionary"""
        return {
            "number": issue.number,
            "title": issue.title,
            "state": issue.state,
            "labels": issue.labels,
            "created_at": issue.created_at.isoformat(),
            "updated_at": issue.updated_at.isoformat(),
            "closed_at": issue.closed_at.isoformat() if issue.closed_at else None,
            "author": issue.author,
            "assignees": issue.assignees,
            "milestone": issue.milestone,
            "body": issue.body,
            "comments_count": issue.comments_count,
            "reactions": issue.reactions,
            "is_pull_request": issue.is_pull_request
        }
        
    def save_issues(self, issues: List[Dict[str, Any]], filename_prefix: str = "flopy_issues_quality"):
        """Save collected issues to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_prefix}_{timestamp}.json"
        filepath = self.output_dir / filename
        
        # Create metadata
        metadata = {
            "collection_timestamp": datetime.now().isoformat(),
            "repository": f"{self.github_config.owner}/{self.github_config.repo}",
            "total_issues": len(issues),
            "filters_applied": {
                "state": "closed",
                "min_comments": self.quality_filter.min_comments,
                "from_date": self.quality_filter.from_date.isoformat(),
                "to_date": self.quality_filter.to_date.isoformat(),
                "excluded_labels": self.quality_filter.excluded_labels
            }
        }
        
        # Combine metadata and issues
        output_data = {
            "metadata": metadata,
            "issues": issues
        }
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
            
        self.logger.info(f"Saved {len(issues)} issues to {filepath}")
        
        # Also save statistics
        self._save_statistics(issues, timestamp)
        
        return filepath
        
    def _save_statistics(self, issues: List[Dict[str, Any]], timestamp: str):
        """Save collection statistics"""
        stats = {
            "total_issues": len(issues),
            "by_year": {},
            "by_label": {},
            "avg_comments": 0,
            "high_engagement": 0,
            "has_module_mentions": 0
        }
        
        total_comments = 0
        for issue in issues:
            # Year statistics
            year = issue["created_at"][:4]
            stats["by_year"][year] = stats["by_year"].get(year, 0) + 1
            
            # Label statistics
            for label in issue["labels"]:
                stats["by_label"][label] = stats["by_label"].get(label, 0) + 1
                
            # Comment statistics
            total_comments += issue["comments_count"]
            if issue["comments_count"] >= 5:
                stats["high_engagement"] += 1
                
            # Check for module mentions
            if self._has_module_mentions(issue):
                stats["has_module_mentions"] += 1
                
        stats["avg_comments"] = total_comments / len(issues) if issues else 0
        
        # Save statistics
        stats_file = self.output_dir / f"collection_stats_{timestamp}.json"
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
            
        self.logger.info(f"Saved statistics to {stats_file}")
        
    def _has_module_mentions(self, issue: Dict[str, Any]) -> bool:
        """Check if issue mentions FloPy modules"""
        text = f"{issue['title']} {issue['body'] or ''}"
        module_keywords = [
            'mf6', 'modflow', 'mfgwf', 'mfsim', 'wel', 'chd', 'drn', 
            'riv', 'ghb', 'rch', 'evt', 'maw', 'uzf', 'sfr', 'lak',
            'dis', 'ic', 'npf', 'sto', 'buy', 'gnc', 'hfb', 'csub'
        ]
        return any(keyword in text.lower() for keyword in module_keywords)
        
    def run(self, state: str = "closed", max_issues: Optional[int] = None):
        """Main collection pipeline"""
        self.logger.info("Starting GitHub issue collection pipeline")
        
        # Collect issues
        quality_issues = self.collect_issues(state=state, max_issues=max_issues)
        
        # Enrich with comments
        self.logger.info("Enriching issues with comments...")
        enriched_issues = []
        for i, issue in enumerate(quality_issues):
            if (i + 1) % 10 == 0:
                self.logger.info(f"Processed {i + 1}/{len(quality_issues)} issues")
                
            enriched_issue = self.enrich_issue_with_comments(issue)
            enriched_issues.append(enriched_issue)
            
        # Save results
        output_file = self.save_issues(enriched_issues)
        
        self.logger.info(f"Collection complete! Output saved to {output_file}")
        
        # Print summary statistics
        self._print_summary(enriched_issues)
        
    def _print_summary(self, issues: List[Dict[str, Any]]):
        """Print collection summary"""
        print("\n" + "="*60)
        print("COLLECTION SUMMARY")
        print("="*60)
        print(f"Total quality issues collected: {len(issues)}")
        
        # Label distribution
        label_counts = {}
        for issue in issues:
            for label in issue["labels"]:
                label_counts[label] = label_counts.get(label, 0) + 1
                
        print("\nTop 10 labels:")
        for label, count in sorted(label_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {label}: {count}")
            
        # Engagement metrics
        high_engagement = sum(1 for i in issues if i["comments_count"] >= 5)
        avg_comments = sum(i["comments_count"] for i in issues) / len(issues) if issues else 0
        
        print(f"\nEngagement metrics:")
        print(f"  Average comments per issue: {avg_comments:.1f}")
        print(f"  High engagement issues (5+ comments): {high_engagement}")
        
        # Module mentions
        module_mentions = sum(1 for i in issues if self._has_module_mentions(i))
        print(f"\nIssues with module mentions: {module_mentions} ({module_mentions/len(issues)*100:.1f}%)")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Collect quality GitHub issues from FloPy repository")
    parser.add_argument("--state", default="closed", choices=["open", "closed", "all"],
                       help="Issue state to collect (default: closed)")
    parser.add_argument("--from-date", default="01-01-2022",
                       help="Start date for issue collection (DD-MM-YYYY)")
    parser.add_argument("--to-date", default=None,
                       help="End date for issue collection (DD-MM-YYYY, default: today)")
    parser.add_argument("--min-comments", type=int, default=2,
                       help="Minimum number of comments required")
    parser.add_argument("--max-issues", type=int, default=None,
                       help="Maximum number of issues to collect")
    parser.add_argument("--required-labels", nargs="+", default=[],
                       help="Labels that must be present")
    parser.add_argument("--excluded-labels", nargs="+", default=["duplicate", "wontfix"],
                       help="Labels to exclude")
    
    args = parser.parse_args()
    
    # Build configuration
    config = {
        "date_range": {
            "from_date": args.from_date,
            "to_date": args.to_date
        },
        "min_comments": args.min_comments,
        "required_labels": args.required_labels,
        "excluded_labels": args.excluded_labels
    }
    
    # Run collector
    collector = FloPyIssueCollector(config)
    collector.run(state=args.state, max_issues=args.max_issues)


if __name__ == "__main__":
    main()
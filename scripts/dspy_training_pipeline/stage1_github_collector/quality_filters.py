#!/usr/bin/env python3
"""
Quality filters for GitHub issues

This module contains filters to identify high-quality issues
suitable for DSPy training data generation.
"""

from datetime import datetime
from typing import List, Optional
import re


def parse_date(date_str: str) -> datetime:
    """Parse date in DD-MM-YYYY format"""
    return datetime.strptime(date_str, "%d-%m-%Y")


class IssueQualityFilter:
    """Filter GitHub issues based on quality criteria"""
    
    def __init__(self, 
                 min_comments: int = 2,
                 from_date: str = "01-01-2022",
                 to_date: Optional[str] = None,
                 min_body_length: int = 50,
                 required_labels: Optional[List[str]] = None,
                 excluded_labels: Optional[List[str]] = None):
        """
        Initialize quality filter
        
        Args:
            min_comments: Minimum number of comments
            from_date: Only include issues created after this date (DD-MM-YYYY)
            to_date: Only include issues created before this date (DD-MM-YYYY)
            min_body_length: Minimum character length for issue body
            required_labels: Labels that must be present
            excluded_labels: Labels that disqualify an issue
        """
        self.min_comments = min_comments
        self.from_date = parse_date(from_date)
        self.to_date = parse_date(to_date) if to_date else datetime.now()
        self.min_body_length = min_body_length
        self.required_labels = required_labels or []
        self.excluded_labels = excluded_labels or ["duplicate", "wontfix", "invalid"]
        
        # FloPy-specific terms to identify relevant issues
        self.flopy_terms = [
            'flopy', 'modflow', 'mf6', 'mf2005', 'mfnwt', 'mt3d', 'seawat',
            'modpath', 'zone budget', 'pest', 'gwf', 'gwt', 'gwe'
        ]
        
        # Module/package indicators
        self.module_patterns = [
            r'\bmf\w+\b',           # mfgwf, mfsim, etc.
            r'\b[A-Z]{3}\b',        # WEL, CHD, DRN, etc.
            r'package',             # package mentions
            r'\.py\b',              # Python file references
            r'flopy\.\w+',          # flopy.modflow, flopy.mf6, etc.
        ]
        
    def is_quality_issue(self, issue) -> bool:
        """
        Check if an issue meets quality criteria
        
        Args:
            issue: GitHub Issue object
            
        Returns:
            bool: True if issue meets quality criteria
        """
        # Check basic criteria
        if not self._meets_basic_criteria(issue):
            return False
            
        # Check content quality
        if not self._has_quality_content(issue):
            return False
            
        # Check FloPy relevance
        if not self._is_flopy_relevant(issue):
            return False
            
        return True
        
    def _meets_basic_criteria(self, issue) -> bool:
        """Check basic quality criteria"""
        # Check date range
        issue_date = issue.created_at.replace(tzinfo=None)
        if issue_date < self.from_date or issue_date > self.to_date:
            return False
            
        # Check comment count
        if issue.comments_count < self.min_comments:
            return False
            
        # Check excluded labels
        if any(label in self.excluded_labels for label in issue.labels):
            return False
            
        # Check required labels
        if self.required_labels:
            if not any(label in self.required_labels for label in issue.labels):
                return False
                
        # Skip pull requests
        if issue.is_pull_request:
            return False
            
        return True
        
    def _has_quality_content(self, issue) -> bool:
        """Check content quality"""
        # Check body length
        if not issue.body or len(issue.body.strip()) < self.min_body_length:
            return False
            
        # Skip issues with only questions marks or very short titles
        if len(issue.title.strip()) < 10:
            return False
            
        # Skip generic help requests
        generic_patterns = [
            r'^help\s*$',
            r'^question\s*$',
            r'^error\s*$',
            r'^problem\s*$'
        ]
        
        title_lower = issue.title.lower().strip()
        if any(re.match(pattern, title_lower) for pattern in generic_patterns):
            return False
            
        return True
        
    def _is_flopy_relevant(self, issue) -> bool:
        """Check if issue is FloPy-specific"""
        # Combine title and body for checking
        text = f"{issue.title} {issue.body or ''}".lower()
        
        # Must contain at least one FloPy term
        has_flopy_term = any(term in text for term in self.flopy_terms)
        if not has_flopy_term:
            return False
            
        # Bonus: Check for module/package references
        has_module_ref = any(re.search(pattern, text, re.IGNORECASE) 
                            for pattern in self.module_patterns)
        
        # If no module reference, check for other indicators
        if not has_module_ref:
            # Must have substantive technical content
            technical_indicators = [
                'error', 'exception', 'traceback', 'bug', 'issue',
                'feature', 'implement', 'support', 'add',
                'model', 'simulation', 'grid', 'cell', 'layer',
                'stress period', 'time step', 'boundary', 'package'
            ]
            
            has_technical = any(indicator in text for indicator in technical_indicators)
            if not has_technical:
                return False
                
        return True
        
    def get_issue_quality_score(self, issue) -> float:
        """
        Calculate a quality score for ranking issues
        
        Args:
            issue: GitHub Issue object
            
        Returns:
            float: Quality score (0.0 - 1.0)
        """
        score = 0.0
        
        # Comment engagement (up to 0.3)
        comment_score = min(issue.comments_count / 10, 0.3)
        score += comment_score
        
        # Body length (up to 0.2)
        if issue.body:
            body_score = min(len(issue.body) / 1000, 0.2)
            score += body_score
            
        # Label quality (up to 0.2)
        quality_labels = ['bug', 'enhancement', 'documentation', 'discussion']
        label_score = sum(0.05 for label in issue.labels if label in quality_labels)
        score += min(label_score, 0.2)
        
        # Module references (up to 0.2)
        text = f"{issue.title} {issue.body or ''}"
        module_count = sum(1 for pattern in self.module_patterns 
                          if re.search(pattern, text, re.IGNORECASE))
        module_score = min(module_count * 0.05, 0.2)
        score += module_score
        
        # Recency (up to 0.1)
        days_old = (datetime.now() - issue.created_at.replace(tzinfo=None)).days
        recency_score = max(0, 0.1 - (days_old / 3650))  # Decay over 10 years
        score += recency_score
        
        return min(score, 1.0)
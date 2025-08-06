#!/usr/bin/env python3
"""
GitHub FloPy Issues Extractor

This script extracts issues from the FloPy GitHub repository and stores them
in a PostgreSQL database for semantic analysis. It includes:
- Issue metadata (title, state, labels, etc.)
- Issue content and body
- Comments and reactions
- Related pull requests
- Semantic embeddings for search

The extracted issues can be used to:
- Analyze common problems and questions
- Identify feature requests and enhancements
- Track bug patterns
- Understand user needs and pain points
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import psycopg2
from psycopg2.extras import execute_values
import uuid

# Add parent directory to path to import from docs
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from docs.github_flopy_extractor.github_flopy_ext_ref import (
    GitHubFloPyExtractor, GitHubConfig, Issue
)

# Import configuration and AI tools
try:
    import config
    from src.ai_analysis import generate_semantic_analysis, create_embedding
except ImportError:
    print("Error: Could not import config or AI analysis modules")
    print("Make sure config.py exists and contains necessary API keys")
    sys.exit(1)


class GitHubIssuesProcessor:
    """Process GitHub issues and store them in PostgreSQL with semantic analysis"""
    
    def __init__(self, connection_string: str, github_token: Optional[str] = None):
        """Initialize processor with database connection and GitHub config"""
        self.conn = psycopg2.connect(connection_string)
        self.github_config = GitHubConfig(token=github_token)
        self.extractor = GitHubFloPyExtractor(self.github_config)
        self._create_tables()
        
    def _create_tables(self):
        """Create tables for storing GitHub issues data"""
        with self.conn.cursor() as cur:
            # Main issues table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS github_issues (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    issue_number INTEGER UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    state TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    closed_at TIMESTAMP,
                    author TEXT NOT NULL,
                    assignees TEXT[],
                    labels TEXT[],
                    milestone TEXT,
                    
                    -- Content
                    body TEXT,
                    body_html TEXT,
                    
                    -- Metadata
                    comments_count INTEGER DEFAULT 0,
                    reactions JSONB,
                    is_pull_request BOOLEAN DEFAULT FALSE,
                    
                    -- Semantic analysis
                    issue_type TEXT,  -- bug, feature, question, discussion
                    affected_components TEXT[],
                    problem_summary TEXT,
                    proposed_solution TEXT,
                    related_issues INTEGER[],
                    
                    -- Search capabilities
                    embedding_text TEXT NOT NULL,
                    embedding vector(1536),
                    search_vector tsvector,
                    
                    -- Processing metadata
                    processed_at TIMESTAMP DEFAULT NOW(),
                    last_synced_at TIMESTAMP DEFAULT NOW()
                );
                
                CREATE INDEX IF NOT EXISTS idx_issues_number ON github_issues(issue_number);
                CREATE INDEX IF NOT EXISTS idx_issues_state ON github_issues(state);
                CREATE INDEX IF NOT EXISTS idx_issues_created ON github_issues(created_at);
                CREATE INDEX IF NOT EXISTS idx_issues_labels ON github_issues USING GIN(labels);
                CREATE INDEX IF NOT EXISTS idx_issues_search ON github_issues USING GIN(search_vector);
                CREATE INDEX IF NOT EXISTS idx_issues_embedding ON github_issues USING ivfflat (embedding vector_l2_ops);
            """)
            
            # Issue comments table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS github_issue_comments (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    issue_number INTEGER NOT NULL REFERENCES github_issues(issue_number),
                    comment_id INTEGER UNIQUE NOT NULL,
                    author TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    body TEXT,
                    reactions JSONB,
                    
                    FOREIGN KEY (issue_number) REFERENCES github_issues(issue_number) ON DELETE CASCADE
                );
                
                CREATE INDEX IF NOT EXISTS idx_comments_issue ON github_issue_comments(issue_number);
                CREATE INDEX IF NOT EXISTS idx_comments_created ON github_issue_comments(created_at);
            """)
            
            # Issue events table (for tracking state changes)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS github_issue_events (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    issue_number INTEGER NOT NULL REFERENCES github_issues(issue_number),
                    event_type TEXT NOT NULL,  -- closed, reopened, labeled, etc.
                    actor TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    details JSONB,
                    
                    FOREIGN KEY (issue_number) REFERENCES github_issues(issue_number) ON DELETE CASCADE
                );
                
                CREATE INDEX IF NOT EXISTS idx_events_issue ON github_issue_events(issue_number);
                CREATE INDEX IF NOT EXISTS idx_events_type ON github_issue_events(event_type);
            """)
            
            self.conn.commit()
            
    def process_issue(self, issue: Issue) -> Dict[str, Any]:
        """Process a single issue with semantic analysis"""
        print(f"  Processing issue #{issue.number}: {issue.title}")
        
        # Prepare text for embedding
        embedding_text = f"""
Issue #{issue.number}: {issue.title}
State: {issue.state}
Labels: {', '.join(issue.labels)}
Created: {issue.created_at}
Author: {issue.author}

{issue.body or 'No description provided.'}
        """.strip()
        
        # Generate semantic analysis
        analysis_prompt = f"""
Analyze this GitHub issue from the FloPy groundwater modeling package:

Issue #{issue.number}: {issue.title}
Labels: {', '.join(issue.labels)}
State: {issue.state}

Body:
{issue.body or 'No description provided.'}

Provide analysis in the following sections:

## Issue Type
Classify as one of: bug, feature_request, question, discussion, documentation

## Affected Components
List the FloPy components/packages this issue relates to (e.g., mf6, modflow, specific packages like WEL, CHD, etc.)

## Problem Summary
Summarize the core problem or request in 2-3 sentences

## Proposed Solution
If mentioned, summarize any proposed solutions or workarounds
"""
        
        try:
            analysis = generate_semantic_analysis(analysis_prompt)
            
            # Parse analysis sections
            issue_type = self._extract_section(analysis, "Issue Type").lower().replace(" ", "_")
            affected_components = [c.strip() for c in self._extract_section(analysis, "Affected Components").split(",")]
            problem_summary = self._extract_section(analysis, "Problem Summary")
            proposed_solution = self._extract_section(analysis, "Proposed Solution")
            
        except Exception as e:
            print(f"    Warning: Semantic analysis failed: {e}")
            issue_type = self._guess_issue_type(issue)
            affected_components = self._extract_components_from_labels(issue.labels)
            problem_summary = issue.title
            proposed_solution = None
            
        # Create embedding
        try:
            embedding = create_embedding(embedding_text)
        except Exception as e:
            print(f"    Warning: Embedding creation failed: {e}")
            embedding = None
            
        # Find related issues (simple approach based on labels)
        related_issues = self._find_related_issues(issue)
        
        return {
            "issue_number": issue.number,
            "title": issue.title,
            "state": issue.state,
            "created_at": issue.created_at,
            "updated_at": issue.updated_at,
            "closed_at": issue.closed_at,
            "author": issue.author,
            "assignees": issue.assignees,
            "labels": issue.labels,
            "milestone": issue.milestone,
            "body": issue.body,
            "comments_count": issue.comments_count,
            "reactions": json.dumps(issue.reactions),
            "is_pull_request": issue.is_pull_request,
            "issue_type": issue_type,
            "affected_components": affected_components,
            "problem_summary": problem_summary,
            "proposed_solution": proposed_solution,
            "related_issues": related_issues,
            "embedding_text": embedding_text,
            "embedding": embedding,
            "search_vector": self._create_search_vector(issue)
        }
        
    def _extract_section(self, text: str, section: str) -> str:
        """Extract a section from markdown-formatted text"""
        import re
        pattern = rf"##\s*{section}\s*\n(.*?)(?:\n##|$)"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else ""
        
    def _guess_issue_type(self, issue: Issue) -> str:
        """Guess issue type from labels and title"""
        labels_lower = [label.lower() for label in issue.labels]
        title_lower = issue.title.lower()
        
        if any(label in labels_lower for label in ["bug", "defect", "error"]):
            return "bug"
        elif any(label in labels_lower for label in ["enhancement", "feature"]):
            return "feature_request"
        elif any(label in labels_lower for label in ["question", "help wanted"]):
            return "question"
        elif any(label in labels_lower for label in ["documentation", "docs"]):
            return "documentation"
        elif "?" in issue.title:
            return "question"
        elif any(word in title_lower for word in ["add", "implement", "support", "feature"]):
            return "feature_request"
        elif any(word in title_lower for word in ["error", "bug", "fix", "crash", "fail"]):
            return "bug"
        else:
            return "discussion"
            
    def _extract_components_from_labels(self, labels: List[str]) -> List[str]:
        """Extract FloPy components from issue labels"""
        components = []
        for label in labels:
            label_lower = label.lower()
            if "mf6" in label_lower:
                components.append("mf6")
            elif "modflow" in label_lower:
                components.append("modflow")
            elif "mt3d" in label_lower:
                components.append("mt3d")
            elif any(pkg in label_lower for pkg in ["wel", "chd", "drn", "riv", "ghb"]):
                components.append(label_lower)
        return components if components else ["general"]
        
    def _find_related_issues(self, issue: Issue) -> List[int]:
        """Find potentially related issues based on labels"""
        if not issue.labels:
            return []
            
        with self.conn.cursor() as cur:
            # Find issues with overlapping labels
            cur.execute("""
                SELECT issue_number 
                FROM github_issues 
                WHERE issue_number != %s 
                AND labels && %s
                ORDER BY created_at DESC
                LIMIT 5
            """, (issue.number, issue.labels))
            
            return [row[0] for row in cur.fetchall()]
            
    def _create_search_vector(self, issue: Issue) -> str:
        """Create PostgreSQL search vector from issue data"""
        search_text = f"{issue.title} {' '.join(issue.labels)} {issue.body or ''}"
        return search_text
        
    def save_issue(self, issue_data: Dict[str, Any]):
        """Save processed issue to database"""
        with self.conn.cursor() as cur:
            # Prepare data for insertion
            columns = list(issue_data.keys())
            values = [issue_data[col] for col in columns]
            
            # Create placeholders for SQL
            placeholders = ", ".join(["%s"] * len(columns))
            update_clause = ", ".join([f"{col} = EXCLUDED.{col}" for col in columns if col != "issue_number"])
            
            # Upsert issue
            query = f"""
                INSERT INTO github_issues ({", ".join(columns)})
                VALUES ({placeholders})
                ON CONFLICT (issue_number) DO UPDATE SET
                {update_clause},
                last_synced_at = NOW()
            """
            
            cur.execute(query, values)
            
            # Update search vector
            cur.execute("""
                UPDATE github_issues 
                SET search_vector = to_tsvector('english', %s)
                WHERE issue_number = %s
            """, (issue_data["search_vector"], issue_data["issue_number"]))
            
        self.conn.commit()
        
    def process_all_issues(self, state: str = "all", labels: Optional[List[str]] = None):
        """Process all issues from the repository"""
        print(f"\nExtracting issues from FloPy repository (state={state})...")
        issues = self.extractor.get_issues(state=state, labels=labels)
        print(f"Found {len(issues)} issues to process\n")
        
        success_count = 0
        error_count = 0
        
        for i, issue in enumerate(issues):
            try:
                issue_data = self.process_issue(issue)
                self.save_issue(issue_data)
                success_count += 1
                
                # Rate limiting
                if (i + 1) % 10 == 0:
                    print(f"\nProcessed {i + 1}/{len(issues)} issues...")
                    time.sleep(2)  # Pause to avoid rate limits
                    
            except Exception as e:
                print(f"  Error processing issue #{issue.number}: {e}")
                error_count += 1
                continue
                
        print(f"\n✅ Processing complete!")
        print(f"  Success: {success_count}")
        print(f"  Errors: {error_count}")
        
    def get_issue_statistics(self):
        """Get statistics about processed issues"""
        with self.conn.cursor() as cur:
            # Total issues
            cur.execute("SELECT COUNT(*) FROM github_issues")
            total = cur.fetchone()[0]
            
            # Issues by state
            cur.execute("""
                SELECT state, COUNT(*) 
                FROM github_issues 
                GROUP BY state
            """)
            by_state = dict(cur.fetchall())
            
            # Issues by type
            cur.execute("""
                SELECT issue_type, COUNT(*) 
                FROM github_issues 
                GROUP BY issue_type
            """)
            by_type = dict(cur.fetchall())
            
            # Most common labels
            cur.execute("""
                SELECT label, COUNT(*) as count
                FROM github_issues, UNNEST(labels) AS label
                GROUP BY label
                ORDER BY count DESC
                LIMIT 10
            """)
            top_labels = cur.fetchall()
            
            # Most affected components
            cur.execute("""
                SELECT component, COUNT(*) as count
                FROM github_issues, UNNEST(affected_components) AS component
                GROUP BY component
                ORDER BY count DESC
                LIMIT 10
            """)
            top_components = cur.fetchall()
            
        return {
            "total": total,
            "by_state": by_state,
            "by_type": by_type,
            "top_labels": top_labels,
            "top_components": top_components
        }
        
    def search_issues(self, query: str, limit: int = 10) -> List[Dict]:
        """Search issues using semantic similarity"""
        # Create embedding for query
        query_embedding = create_embedding(query)
        
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    issue_number,
                    title,
                    state,
                    labels,
                    problem_summary,
                    1 - (embedding <-> %s::vector) as similarity
                FROM github_issues
                WHERE embedding IS NOT NULL
                ORDER BY embedding <-> %s::vector
                LIMIT %s
            """, (query_embedding, query_embedding, limit))
            
            results = []
            for row in cur.fetchall():
                results.append({
                    "issue_number": row[0],
                    "title": row[1],
                    "state": row[2],
                    "labels": row[3],
                    "problem_summary": row[4],
                    "similarity": row[5]
                })
                
        return results
        
    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    """Main function to run the issues processor"""
    # Get GitHub token from environment
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("Warning: GITHUB_TOKEN not set. API rate limits will be lower.")
        
    # Create processor
    processor = GitHubIssuesProcessor(
        connection_string=config.NEON_CONNECTION_STRING,
        github_token=github_token
    )
    
    try:
        # Process all open issues
        processor.process_all_issues(state="open")
        
        # Show statistics
        print("\n=== Issue Statistics ===")
        stats = processor.get_issue_statistics()
        print(f"Total issues: {stats['total']}")
        print(f"\nBy state:")
        for state, count in stats['by_state'].items():
            print(f"  {state}: {count}")
        print(f"\nBy type:")
        for issue_type, count in stats['by_type'].items():
            print(f"  {issue_type}: {count}")
        print(f"\nTop labels:")
        for label, count in stats['top_labels']:
            print(f"  {label}: {count}")
        print(f"\nTop affected components:")
        for component, count in stats['top_components']:
            print(f"  {component}: {count}")
            
        # Example search
        print("\n=== Example Search ===")
        print("Query: 'error when running mf6 model'")
        results = processor.search_issues("error when running mf6 model", limit=5)
        for result in results:
            print(f"\n#{result['issue_number']}: {result['title']}")
            print(f"  State: {result['state']}")
            print(f"  Labels: {', '.join(result['labels'])}")
            print(f"  Similarity: {result['similarity']:.3f}")
            
    finally:
        processor.close()


if __name__ == "__main__":
    main()
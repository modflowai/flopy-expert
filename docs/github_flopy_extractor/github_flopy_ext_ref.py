#!/usr/bin/env python3
"""
GitHub FloPy Data Extractor - Reference Implementation

This module provides a comprehensive reference for extracting data from the FloPy
GitHub repository, including:
- Repository metadata and statistics
- Code structure and documentation
- Issues and discussions
- Pull requests and commits
- Release information
- Contributors and community data

This serves as a reference implementation for building semantic databases
from GitHub repositories, particularly for scientific computing projects.
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


@dataclass
class GitHubConfig:
    """Configuration for GitHub API access"""
    token: Optional[str] = None
    owner: str = "modflowpy"
    repo: str = "flopy"
    api_base: str = "https://api.github.com"
    per_page: int = 100
    max_retries: int = 3
    backoff_factor: float = 0.3
    

@dataclass
class RepositoryInfo:
    """Repository metadata and statistics"""
    name: str
    full_name: str
    description: str
    homepage: Optional[str]
    language: str
    created_at: datetime
    updated_at: datetime
    pushed_at: datetime
    size: int
    stargazers_count: int
    watchers_count: int
    forks_count: int
    open_issues_count: int
    topics: List[str]
    default_branch: str
    license: Optional[Dict[str, str]]


@dataclass
class Issue:
    """GitHub issue representation"""
    number: int
    title: str
    state: str
    labels: List[str]
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime]
    author: str
    assignees: List[str]
    milestone: Optional[str]
    body: Optional[str]
    comments_count: int
    reactions: Dict[str, int]
    is_pull_request: bool


@dataclass
class PullRequest:
    """Pull request representation"""
    number: int
    title: str
    state: str
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime]
    merged_at: Optional[datetime]
    author: str
    reviewers: List[str]
    labels: List[str]
    base_branch: str
    head_branch: str
    commits: int
    additions: int
    deletions: int
    changed_files: int
    body: Optional[str]


@dataclass
class Release:
    """GitHub release information"""
    tag_name: str
    name: str
    draft: bool
    prerelease: bool
    created_at: datetime
    published_at: datetime
    author: str
    body: Optional[str]
    assets: List[Dict[str, Any]]
    download_count: int


class GitHubFloPyExtractor:
    """
    Main extractor class for FloPy GitHub repository data.
    
    This class provides methods to extract various types of data
    from the FloPy GitHub repository for semantic analysis.
    """
    
    def __init__(self, config: Optional[GitHubConfig] = None):
        """Initialize the extractor with configuration"""
        self.config = config or GitHubConfig()
        self.session = self._create_session()
        self._setup_headers()
        
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry logic"""
        session = requests.Session()
        retry = Retry(
            total=self.config.max_retries,
            backoff_factor=self.config.backoff_factor,
            status_forcelist=[403, 429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
        
    def _setup_headers(self):
        """Setup authentication headers if token is provided"""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "FloPy-Semantic-Extractor/1.0"
        }
        if self.config.token:
            headers["Authorization"] = f"token {self.config.token}"
        self.session.headers.update(headers)
        
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make a GET request to GitHub API with rate limit handling"""
        url = f"{self.config.api_base}/{endpoint}"
        response = self.session.get(url, params=params)
        
        # Check rate limits
        if response.status_code == 403:
            reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
            if reset_time:
                sleep_time = reset_time - int(time.time()) + 1
                if sleep_time > 0:
                    print(f"Rate limited. Sleeping for {sleep_time} seconds...")
                    time.sleep(sleep_time)
                    return self._make_request(endpoint, params)
                    
        response.raise_for_status()
        return response.json()
        
    def _paginate(self, endpoint: str, params: Optional[Dict] = None) -> List[Dict]:
        """Handle pagination for GitHub API endpoints"""
        if params is None:
            params = {}
        params["per_page"] = self.config.per_page
        params["page"] = 1
        
        all_items = []
        while True:
            try:
                items = self._make_request(endpoint, params)
            except requests.exceptions.HTTPError as e:
                # GitHub API returns 422 when trying to paginate beyond 1000 results
                if e.response.status_code == 422 and params["page"] > 10:
                    print(f"Reached GitHub API pagination limit (1000 items). Returning {len(all_items)} items.")
                    break
                else:
                    raise
            
            if not items:
                break
            all_items.extend(items)
            if len(items) < self.config.per_page:
                break
            params["page"] += 1
            
        return all_items
        
    def get_repository_info(self) -> RepositoryInfo:
        """Get repository metadata and statistics"""
        data = self._make_request(f"repos/{self.config.owner}/{self.config.repo}")
        
        return RepositoryInfo(
            name=data["name"],
            full_name=data["full_name"],
            description=data["description"] or "",
            homepage=data["homepage"],
            language=data["language"],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
            pushed_at=datetime.fromisoformat(data["pushed_at"].replace("Z", "+00:00")),
            size=data["size"],
            stargazers_count=data["stargazers_count"],
            watchers_count=data["watchers_count"],
            forks_count=data["forks_count"],
            open_issues_count=data["open_issues_count"],
            topics=data.get("topics", []),
            default_branch=data["default_branch"],
            license=data.get("license")
        )
        
    def get_issues(self, state: str = "all", labels: Optional[List[str]] = None) -> List[Issue]:
        """Get issues from the repository"""
        params = {"state": state}
        if labels:
            params["labels"] = ",".join(labels)
            
        issues_data = self._paginate(
            f"repos/{self.config.owner}/{self.config.repo}/issues",
            params
        )
        
        issues = []
        for item in issues_data:
            # Skip pull requests (they appear in issues endpoint too)
            if "pull_request" in item:
                continue
                
            issue = Issue(
                number=item["number"],
                title=item["title"],
                state=item["state"],
                labels=[label["name"] for label in item["labels"]],
                created_at=datetime.fromisoformat(item["created_at"].replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(item["updated_at"].replace("Z", "+00:00")),
                closed_at=datetime.fromisoformat(item["closed_at"].replace("Z", "+00:00")) 
                          if item["closed_at"] else None,
                author=item["user"]["login"],
                assignees=[a["login"] for a in item["assignees"]],
                milestone=item["milestone"]["title"] if item["milestone"] else None,
                body=item["body"],
                comments_count=item["comments"],
                reactions={
                    "+1": item["reactions"]["+1"],
                    "-1": item["reactions"]["-1"],
                    "laugh": item["reactions"]["laugh"],
                    "hooray": item["reactions"]["hooray"],
                    "confused": item["reactions"]["confused"],
                    "heart": item["reactions"]["heart"],
                    "rocket": item["reactions"]["rocket"],
                    "eyes": item["reactions"]["eyes"]
                },
                is_pull_request=False
            )
            issues.append(issue)
            
        return issues
        
    def get_pull_requests(self, state: str = "all") -> List[PullRequest]:
        """Get pull requests from the repository"""
        params = {"state": state}
        prs_data = self._paginate(
            f"repos/{self.config.owner}/{self.config.repo}/pulls",
            params
        )
        
        pull_requests = []
        for item in prs_data:
            # Get detailed PR info for merge status and stats
            pr_detail = self._make_request(
                f"repos/{self.config.owner}/{self.config.repo}/pulls/{item['number']}"
            )
            
            pr = PullRequest(
                number=item["number"],
                title=item["title"],
                state=item["state"],
                created_at=datetime.fromisoformat(item["created_at"].replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(item["updated_at"].replace("Z", "+00:00")),
                closed_at=datetime.fromisoformat(item["closed_at"].replace("Z", "+00:00")) 
                          if item["closed_at"] else None,
                merged_at=datetime.fromisoformat(pr_detail["merged_at"].replace("Z", "+00:00")) 
                          if pr_detail["merged_at"] else None,
                author=item["user"]["login"],
                reviewers=[r["login"] for r in item.get("requested_reviewers", [])],
                labels=[label["name"] for label in item["labels"]],
                base_branch=item["base"]["ref"],
                head_branch=item["head"]["ref"],
                commits=pr_detail["commits"],
                additions=pr_detail["additions"],
                deletions=pr_detail["deletions"],
                changed_files=pr_detail["changed_files"],
                body=item["body"]
            )
            pull_requests.append(pr)
            
        return pull_requests
        
    def get_releases(self) -> List[Release]:
        """Get releases from the repository"""
        releases_data = self._paginate(
            f"repos/{self.config.owner}/{self.config.repo}/releases"
        )
        
        releases = []
        for item in releases_data:
            # Calculate total download count
            download_count = sum(asset["download_count"] for asset in item["assets"])
            
            release = Release(
                tag_name=item["tag_name"],
                name=item["name"] or item["tag_name"],
                draft=item["draft"],
                prerelease=item["prerelease"],
                created_at=datetime.fromisoformat(item["created_at"].replace("Z", "+00:00")),
                published_at=datetime.fromisoformat(item["published_at"].replace("Z", "+00:00")),
                author=item["author"]["login"],
                body=item["body"],
                assets=[{
                    "name": asset["name"],
                    "size": asset["size"],
                    "download_count": asset["download_count"],
                    "content_type": asset["content_type"]
                } for asset in item["assets"]],
                download_count=download_count
            )
            releases.append(release)
            
        return releases
        
    def get_code_frequency(self) -> List[Dict[str, Any]]:
        """Get code frequency statistics (additions/deletions over time)"""
        data = self._make_request(
            f"repos/{self.config.owner}/{self.config.repo}/stats/code_frequency"
        )
        
        if not data:
            return []
            
        frequency = []
        for week_data in data:
            frequency.append({
                "week": datetime.fromtimestamp(week_data[0]),
                "additions": week_data[1],
                "deletions": abs(week_data[2])
            })
            
        return frequency
        
    def get_contributors(self) -> List[Dict[str, Any]]:
        """Get contributor statistics"""
        data = self._paginate(
            f"repos/{self.config.owner}/{self.config.repo}/contributors"
        )
        
        contributors = []
        for item in data:
            contributors.append({
                "login": item["login"],
                "contributions": item["contributions"],
                "avatar_url": item["avatar_url"],
                "html_url": item["html_url"]
            })
            
        return contributors
        
    def get_topics(self) -> List[str]:
        """Get repository topics"""
        data = self._make_request(
            f"repos/{self.config.owner}/{self.config.repo}/topics",
            params={"accept": "application/vnd.github.mercy-preview+json"}
        )
        return data.get("names", [])
        
    def extract_all(self, output_dir: str = "github_data"):
        """Extract all available data and save to JSON files"""
        os.makedirs(output_dir, exist_ok=True)
        
        print("Extracting repository info...")
        repo_info = self.get_repository_info()
        self._save_json(repo_info, os.path.join(output_dir, "repository_info.json"))
        
        print("Extracting issues...")
        issues = self.get_issues()
        self._save_json(issues, os.path.join(output_dir, "issues.json"))
        print(f"  Found {len(issues)} issues")
        
        print("Extracting pull requests...")
        prs = self.get_pull_requests()
        self._save_json(prs, os.path.join(output_dir, "pull_requests.json"))
        print(f"  Found {len(prs)} pull requests")
        
        print("Extracting releases...")
        releases = self.get_releases()
        self._save_json(releases, os.path.join(output_dir, "releases.json"))
        print(f"  Found {len(releases)} releases")
        
        print("Extracting contributors...")
        contributors = self.get_contributors()
        self._save_json({"contributors": contributors}, 
                       os.path.join(output_dir, "contributors.json"))
        print(f"  Found {len(contributors)} contributors")
        
        print("Extracting code frequency...")
        code_freq = self.get_code_frequency()
        self._save_json({"code_frequency": code_freq}, 
                       os.path.join(output_dir, "code_frequency.json"))
        
        print("\nExtraction complete!")
        
    def _save_json(self, data: Any, filepath: str):
        """Save data to JSON file"""
        if hasattr(data, "__iter__") and not isinstance(data, dict):
            # Convert list of dataclasses to dictionaries
            data = [asdict(item) if hasattr(item, "__dataclass_fields__") else item 
                   for item in data]
        elif hasattr(data, "__dataclass_fields__"):
            data = asdict(data)
            
        # Convert datetime objects to ISO format strings
        def datetime_handler(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return obj
            
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=datetime_handler)
            

def main():
    """Main function demonstrating usage"""
    # Configure with GitHub token if available
    token = os.getenv("GITHUB_TOKEN")
    config = GitHubConfig(token=token)
    
    # Create extractor
    extractor = GitHubFloPyExtractor(config)
    
    # Extract all data
    extractor.extract_all("flopy_github_data")
    
    # Or extract specific data
    print("\n=== Repository Info ===")
    repo_info = extractor.get_repository_info()
    print(f"Repository: {repo_info.full_name}")
    print(f"Stars: {repo_info.stargazers_count}")
    print(f"Forks: {repo_info.forks_count}")
    print(f"Open Issues: {repo_info.open_issues_count}")
    
    print("\n=== Recent Issues ===")
    recent_issues = extractor.get_issues(state="open")[:5]
    for issue in recent_issues:
        print(f"#{issue.number}: {issue.title}")
        print(f"  Labels: {', '.join(issue.labels)}")
        print(f"  Created: {issue.created_at.strftime('%Y-%m-%d')}")
        

if __name__ == "__main__":
    main()
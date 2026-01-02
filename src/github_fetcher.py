"""Fetch commit data from GitHub API"""

import os
from pathlib import Path
from datetime import datetime
import json
from github import Github
import argparse
from dotenv import load_dotenv

load_dotenv()


class GitHubFetcher:
    """Fetches commit data from GitHub for a specified user"""

    def __init__(self, token: str, username: str):
        """
        Initialize GitHub API client

        Args:
            token: GitHub personal access token
            username: GitHub username to analyze
        """
        self.client = Github(token)
        self.username = username
        self.cache_dir = Path("data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch_all_commits(self, use_cache: bool = True) -> list:
        """
        Fetch all commits from user's repositories

        Args:
            use_cache: Whether to use cached data

        Returns:
            List of commit dictionaries with metadata
        """
        user = self.client.get_user(self.username)
        commits = []

        for repo in user.get_repos():
            cache_file = self.cache_dir / f"{repo.name}_commits.json"

            if use_cache and cache_file.exists():
                with open(cache_file) as f:
                    commits.extend(json.load(f))
            else:
                repo_commits = self._fetch_repo_commits(repo)
                commits.extend(repo_commits)

                with open(cache_file, 'w') as f:
                    json.dump(repo_commits, f)

        return commits

    def _fetch_repo_commits(self, repo) -> list:
        """Fetch commits from a single repository"""
        commits = []

        try:
            for commit in repo.get_commits(author=self.username):
                commits.append({
                    "sha": commit.sha,
                    "repository": repo.name,
                    "author": commit.author.login if commit.author else "unknown",
                    "date": commit.commit.author.date.isoformat(),
                    "message": commit.commit.message,
                    "additions": commit.stats.additions,
                    "deletions": commit.stats.deletions,
                    "files_changed": commit.stats.total
                })
        except Exception as e:
            print(f"Error fetching commits from {repo.name}: {e}")

        return commits


def main():
    parser = argparse.ArgumentParser(description="Fetch GitHub commits")
    parser.add_argument("--repo", help="Specific repository to fetch (optional)")
    parser.add_argument("--no-cache", action="store_true", help="Don't use cached data")
    args = parser.parse_args()

    token = os.getenv("GITHUB_TOKEN")
    username = os.getenv("GITHUB_USERNAME", "jasonmotylinski")

    if not token:
        raise ValueError("GITHUB_TOKEN environment variable not set")

    fetcher = GitHubFetcher(token, username)
    commits = fetcher.fetch_all_commits(use_cache=not args.no_cache)

    print(f"Fetched {len(commits)} commits for {username}")


if __name__ == "__main__":
    main()

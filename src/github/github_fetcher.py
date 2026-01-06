"""Fetch commit data from GitHub GraphQL API"""

import os
from pathlib import Path
from datetime import datetime
import json
import requests
import argparse
from dotenv import load_dotenv

load_dotenv()

CONFIG_PATH = Path("config/users.json")
ORG_CACHE_DIR = Path("data/cache/_orgs")
COMMITS_SINCE = datetime(2023, 1, 1)  # Only fetch commits since this date
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

# GraphQL query to fetch commits with stats in one request
COMMITS_QUERY = """
query($owner: String!, $name: String!, $since: GitTimestamp!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    defaultBranchRef {
      target {
        ... on Commit {
          history(first: 100, since: $since, after: $cursor) {
            nodes {
              oid
              message
              additions
              deletions
              changedFilesIfAvailable
              committedDate
              author {
                user {
                  login
                }
                name
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
      }
    }
  }
}
"""

# GraphQL query to list repos in an organization
ORG_REPOS_QUERY = """
query($org: String!, $cursor: String) {
  organization(login: $org) {
    repositories(first: 100, after: $cursor) {
      nodes {
        name
        owner {
          login
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
"""


def load_users_config() -> list:
    """Load list of users from config file"""
    if not CONFIG_PATH.exists():
        return []
    with open(CONFIG_PATH) as f:
        config = json.load(f)
    return config.get("users", [])


def load_organizations_config() -> list:
    """Load list of organizations from config file"""
    if not CONFIG_PATH.exists():
        return []
    with open(CONFIG_PATH) as f:
        config = json.load(f)
    return config.get("organizations", [])


class GraphQLClient:
    """Simple GitHub GraphQL client"""

    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def execute(self, query: str, variables: dict) -> dict:
        """Execute a GraphQL query"""
        response = requests.post(
            GITHUB_GRAPHQL_URL,
            headers=self.headers,
            json={"query": query, "variables": variables}
        )
        response.raise_for_status()
        result = response.json()

        if "errors" in result:
            raise Exception(f"GraphQL errors: {result['errors']}")

        return result["data"]


class OrgCommitCache:
    """Shared cache for organization commits - fetched once, filtered per user"""

    def __init__(self, client: GraphQLClient):
        self.client = client
        self.cache_dir = ORG_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._org_commits = {}  # In-memory cache: {org_name: {repo_name: [commits]}}

    def fetch_org_commits(self, org_name: str, use_cache: bool = True) -> dict:
        """
        Fetch all commits from an organization's repos (once, not per-user)

        Returns:
            Dictionary mapping repo_name to list of all commits
        """
        if org_name in self._org_commits:
            return self._org_commits[org_name]

        org_cache_dir = self.cache_dir / org_name
        org_cache_dir.mkdir(parents=True, exist_ok=True)

        org_commits = {}
        print(f"  Fetching commits from {org_name} organization...")

        try:
            # Get list of repos in the organization
            repos = self._get_org_repos(org_name)
            print(f"    Found {len(repos)} repositories")

            for repo in repos:
                repo_name = repo["name"]
                print(f"    Processing repository: {repo_name}")
                cache_file = org_cache_dir / f"{repo_name}_commits.json"

                if use_cache and cache_file.exists():
                    print(f"      Loading commits from cache")
                    with open(cache_file) as f:
                        org_commits[repo_name] = json.load(f)
                else:
                    print(f"      Fetching commits via GraphQL...")
                    repo_commits = self._fetch_repo_commits_graphql(org_name, repo_name)
                    org_commits[repo_name] = repo_commits

                    # Cache the commits
                    with open(cache_file, 'w') as f:
                        json.dump(repo_commits, f)
                    print(f"      Cached {len(repo_commits)} commits")

        except Exception as e:
            print(f"  Error accessing organization {org_name}: {e}")

        self._org_commits[org_name] = org_commits
        return org_commits

    def _get_org_repos(self, org_name: str) -> list:
        """Get all repositories in an organization using GraphQL"""
        repos = []
        cursor = None

        while True:
            variables = {"org": org_name, "cursor": cursor}
            data = self.client.execute(ORG_REPOS_QUERY, variables)

            org_data = data.get("organization")
            if not org_data:
                break

            repos_data = org_data.get("repositories", {})
            nodes = repos_data.get("nodes", [])
            repos.extend(nodes)

            page_info = repos_data.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")

        return repos

    def _fetch_repo_commits_graphql(self, owner: str, repo_name: str) -> list:
        """Fetch commits from a repository using GraphQL (with stats in same query)"""
        commits = []
        cursor = None
        since_iso = COMMITS_SINCE.isoformat()

        while True:
            variables = {
                "owner": owner,
                "name": repo_name,
                "since": since_iso,
                "cursor": cursor
            }

            try:
                data = self.client.execute(COMMITS_QUERY, variables)
            except Exception as e:
                print(f"        Error fetching commits: {e}")
                break

            repo_data = data.get("repository")
            if not repo_data:
                break

            default_branch = repo_data.get("defaultBranchRef")
            if not default_branch:
                break

            target = default_branch.get("target")
            if not target:
                break

            history = target.get("history", {})
            nodes = history.get("nodes", [])

            for node in nodes:
                # Extract author login
                author_login = "unknown"
                author_data = node.get("author", {})
                if author_data:
                    user = author_data.get("user")
                    if user and user.get("login"):
                        author_login = user["login"]
                    elif author_data.get("name"):
                        author_login = author_data["name"]

                commits.append({
                    "sha": node["oid"],
                    "repository": f"{owner}/{repo_name}",
                    "author": author_login,
                    "date": node["committedDate"],
                    "message": node["message"],
                    "additions": node.get("additions", 0),
                    "deletions": node.get("deletions", 0),
                    "files_changed": node.get("changedFilesIfAvailable") or 0
                })

            page_info = history.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")

        return commits

    def get_user_commits(self, org_name: str, username: str, use_cache: bool = True) -> list:
        """Get commits for a specific user from the org cache"""
        org_commits = self.fetch_org_commits(org_name, use_cache)

        user_commits = []
        for repo_name, commits in org_commits.items():
            for commit in commits:
                if commit["author"].lower() == username.lower():
                    user_commits.append(commit)

        return user_commits


class GitHubFetcher:
    """Fetches commit data from GitHub for a specified user"""

    _org_cache = None  # Shared across all instances

    def __init__(self, token: str, username: str):
        """
        Initialize GitHub GraphQL client

        Args:
            token: GitHub personal access token
            username: GitHub username to analyze
        """
        self.client = GraphQLClient(token)
        self.token = token
        self.username = username
        self.cache_dir = Path("data/cache") / username
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize shared org cache
        if GitHubFetcher._org_cache is None:
            GitHubFetcher._org_cache = OrgCommitCache(self.client)

    def fetch_all_commits(self, use_cache: bool = True) -> list:
        """
        Fetch all commits for this user from organization repositories

        Args:
            use_cache: Whether to use cached data

        Returns:
            List of commit dictionaries with metadata
        """
        commits = []
        seen_shas = set()

        # Fetch from organization repositories (shared cache, filtered by user)
        organizations = load_organizations_config()
        for org_name in organizations:
            user_commits = GitHubFetcher._org_cache.get_user_commits(
                org_name, self.username, use_cache
            )
            for commit in user_commits:
                if commit["sha"] not in seen_shas:
                    commits.append(commit)
                    seen_shas.add(commit["sha"])

        return commits


def fetch_all_users(token: str, use_cache: bool = True) -> dict:
    """
    Fetch commits for all configured users

    Args:
        token: GitHub personal access token
        use_cache: Whether to use cached data

    Returns:
        Dictionary mapping username to list of commits
    """
    users = load_users_config()
    all_commits = {}

    for username in users:
        print(f"Fetching commits for {username}...")
        fetcher = GitHubFetcher(token, username)
        all_commits[username] = fetcher.fetch_all_commits(use_cache=use_cache)
        print(f"  Found {len(all_commits[username])} commits for {username}")

    return all_commits


def main():
    parser = argparse.ArgumentParser(description="Fetch GitHub commits")
    parser.add_argument("--repo", help="Specific repository to fetch (optional)")
    parser.add_argument("--no-cache", action="store_true", help="Don't use cached data")
    parser.add_argument("--user", help="Specific user to fetch (optional, defaults to all users in config)")
    args = parser.parse_args()

    token = os.getenv("GITHUB_TOKEN")

    if not token:
        raise ValueError("GITHUB_TOKEN environment variable not set")

    if args.user:
        # Fetch for specific user
        fetcher = GitHubFetcher(token, args.user)
        commits = fetcher.fetch_all_commits(use_cache=not args.no_cache)
        print(f"Fetched {len(commits)} commits for {args.user}")
    else:
        # Fetch for all configured users
        all_commits = fetch_all_users(token, use_cache=not args.no_cache)
        total = sum(len(c) for c in all_commits.values())
        print(f"\nFetched {total} total commits across {len(all_commits)} users")

    # Rebuild dashboard cache after fetching
    from src.github.github_processor import build_dashboard_cache
    print("\nRebuilding dashboard cache...")
    build_dashboard_cache()


if __name__ == "__main__":
    main()

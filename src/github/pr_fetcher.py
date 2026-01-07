"""Fetch Pull Request data from GitHub GraphQL API"""

import os
import json
import argparse
import requests
from datetime import datetime
from dotenv import load_dotenv

from src.config import (
    GITHUB_ORGANIZATIONS,
    GITHUB_GRAPHQL_URL,
    GITHUB_DATA_SINCE,
    GITHUB_PRS_RAW_DIR,
)

load_dotenv()


# GraphQL query to fetch PRs with reviews
PRS_QUERY = """
query($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequests(first: 100, after: $cursor, orderBy: {field: CREATED_AT, direction: ASC}) {
      nodes {
        number
        title
        state
        createdAt
        closedAt
        mergedAt
        additions
        deletions
        changedFiles
        author {
          login
        }
        reviews(first: 20) {
          nodes {
            author {
              login
            }
            submittedAt
            state
          }
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


class OrgPRCache:
    """Cache for organization Pull Requests"""

    def __init__(self, client: GraphQLClient):
        self.client = client
        self.cache_dir = GITHUB_PRS_RAW_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._org_prs = {}  # In-memory cache: {org_name: {repo_name: [prs]}}

    def fetch_org_prs(self, org_name: str, use_cache: bool = True) -> dict:
        """
        Fetch all PRs from an organization's repos

        Returns:
            Dictionary mapping repo_name to list of all PRs
        """
        if org_name in self._org_prs:
            return self._org_prs[org_name]

        org_cache_dir = self.cache_dir / org_name
        org_cache_dir.mkdir(parents=True, exist_ok=True)

        org_prs = {}
        print(f"  Fetching PRs from {org_name} organization...")

        try:
            # Get list of repos in the organization
            repos = self._get_org_repos(org_name)
            print(f"    Found {len(repos)} repositories")

            for repo in repos:
                repo_name = repo["name"]
                print(f"    Processing repository: {repo_name}")
                cache_file = org_cache_dir / f"{repo_name}_prs.json"

                if use_cache and cache_file.exists():
                    print(f"      Loading PRs from cache")
                    with open(cache_file) as f:
                        org_prs[repo_name] = json.load(f)
                else:
                    print(f"      Fetching PRs via GraphQL...")
                    repo_prs = self._fetch_repo_prs_graphql(org_name, repo_name)
                    org_prs[repo_name] = repo_prs

                    # Cache the PRs
                    with open(cache_file, 'w') as f:
                        json.dump(repo_prs, f)
                    print(f"      Cached {len(repo_prs)} PRs")

        except Exception as e:
            print(f"  Error accessing organization {org_name}: {e}")

        self._org_prs[org_name] = org_prs
        return org_prs

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

    def _fetch_repo_prs_graphql(self, owner: str, repo_name: str) -> list:
        """Fetch PRs from a repository using GraphQL"""
        prs = []
        cursor = None
        since_date = GITHUB_DATA_SINCE

        while True:
            variables = {
                "owner": owner,
                "name": repo_name,
                "cursor": cursor
            }

            try:
                data = self.client.execute(PRS_QUERY, variables)
            except Exception as e:
                print(f"        Error fetching PRs: {e}")
                break

            repo_data = data.get("repository")
            if not repo_data:
                break

            pr_data = repo_data.get("pullRequests", {})
            nodes = pr_data.get("nodes", [])

            for node in nodes:
                # Skip PRs created before our cutoff date
                created_at = node.get("createdAt")
                if created_at:
                    created_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    if created_date.replace(tzinfo=None) < since_date:
                        continue

                # Extract author login
                author_login = "unknown"
                author_data = node.get("author")
                if author_data and author_data.get("login"):
                    author_login = author_data["login"]

                # Extract reviews
                reviews = []
                reviews_data = node.get("reviews", {}).get("nodes", [])
                for review in reviews_data:
                    reviewer_login = "unknown"
                    reviewer_data = review.get("author")
                    if reviewer_data and reviewer_data.get("login"):
                        reviewer_login = reviewer_data["login"]

                    reviews.append({
                        "author": reviewer_login,
                        "submitted_at": review.get("submittedAt"),
                        "state": review.get("state")
                    })

                prs.append({
                    "number": node["number"],
                    "repository": f"{owner}/{repo_name}",
                    "title": node.get("title", ""),
                    "author": author_login,
                    "state": node.get("state"),
                    "created_at": node.get("createdAt"),
                    "closed_at": node.get("closedAt"),
                    "merged_at": node.get("mergedAt"),
                    "additions": node.get("additions", 0),
                    "deletions": node.get("deletions", 0),
                    "changed_files": node.get("changedFiles", 0),
                    "reviews": reviews
                })

            page_info = pr_data.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")

        return prs


def fetch_all_org_prs(token: str, use_cache: bool = True) -> dict:
    """
    Fetch PRs for all configured organizations

    Args:
        token: GitHub personal access token
        use_cache: Whether to use cached data

    Returns:
        Dictionary mapping org/repo to list of PRs
    """
    client = GraphQLClient(token)
    pr_cache = OrgPRCache(client)

    all_prs = {}

    for org_name in GITHUB_ORGANIZATIONS:
        print(f"Fetching PRs for organization: {org_name}")
        org_prs = pr_cache.fetch_org_prs(org_name, use_cache)

        for repo_name, prs in org_prs.items():
            full_repo_name = f"{org_name}/{repo_name}"
            all_prs[full_repo_name] = prs
            print(f"  {full_repo_name}: {len(prs)} PRs")

    return all_prs


def main():
    parser = argparse.ArgumentParser(description="Fetch GitHub Pull Requests")
    parser.add_argument("--no-cache", action="store_true", help="Don't use cached data")
    args = parser.parse_args()

    token = os.getenv("GITHUB_TOKEN")

    if not token:
        raise ValueError("GITHUB_TOKEN environment variable not set")

    all_prs = fetch_all_org_prs(token, use_cache=not args.no_cache)
    total = sum(len(prs) for prs in all_prs.values())
    print(f"\nFetched {total} total PRs across {len(all_prs)} repositories")

    # Build PR export after fetching
    from src.github.pr_processor import build_pr_export
    print("\nBuilding PR export...")
    build_pr_export()


if __name__ == "__main__":
    main()

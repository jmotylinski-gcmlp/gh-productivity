"""Fetch issue data with changelog from JIRA REST API"""

import os
import json
import argparse
import requests
from dotenv import load_dotenv

from src.config import (
    JIRA_BASE_URL,
    JIRA_DATA_SINCE,
    JIRA_RAW_DIR,
)

load_dotenv()


class JiraClient:
    """JIRA REST API client with Basic Auth"""

    def __init__(self, base_url: str, email: str, api_token: str):
        """
        Initialize JIRA client

        Args:
            base_url: JIRA instance URL (e.g., https://your-domain.atlassian.net)
            email: JIRA account email
            api_token: JIRA API token
        """
        self.base_url = base_url.rstrip("/")
        self.auth = (email, api_token)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def get(self, endpoint: str, params: dict = None) -> dict:
        """
        Make a GET request to JIRA API

        Args:
            endpoint: API endpoint (e.g., /rest/api/3/search)
            params: Query parameters

        Returns:
            JSON response as dictionary
        """
        url = f"{self.base_url}{endpoint}"
        response = requests.get(
            url,
            auth=self.auth,
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        return response.json()

    def search_issues(self, jql: str, max_results: int = 100,
                      expand: list = None, fields: list = None,
                      next_page_token: str = None) -> dict:
        """
        Search for issues using JQL (using new /search/jql endpoint)

        The old /rest/api/3/search endpoint is deprecated per CHANGE-2046.
        This uses the new /rest/api/3/search/jql endpoint with nextPageToken pagination.

        Args:
            jql: JQL query string
            max_results: Maximum results per page
            expand: List of fields to expand (e.g., ["changelog"])
            fields: List of fields to return
            next_page_token: Token for fetching next page (None for first page)

        Returns:
            Search results with issues and pagination info (includes nextPageToken)
        """
        params = {
            "jql": jql,
            "maxResults": max_results
        }

        # Only include nextPageToken if we have one (not for first request)
        if next_page_token:
            params["nextPageToken"] = next_page_token

        if expand:
            params["expand"] = ",".join(expand)
        if fields:
            params["fields"] = ",".join(fields)

        return self.get("/rest/api/3/search/jql", params)

    def get_all_projects(self) -> list:
        """
        Fetch all projects the user has access to

        Uses /rest/api/3/project/search with pagination (50 per page)

        Returns:
            List of project dictionaries with key, name, id
        """
        projects = []
        start_at = 0
        max_results = 50

        while True:
            params = {
                "startAt": start_at,
                "maxResults": max_results
            }

            result = self.get("/rest/api/3/project/search", params)

            batch = result.get("values", [])
            if not batch:
                break

            for proj in batch:
                projects.append({
                    "key": proj.get("key"),
                    "name": proj.get("name"),
                    "id": proj.get("id")
                })

            # Check if there are more pages
            if result.get("isLast", True):
                break

            start_at += len(batch)

        return projects


class JiraFetcher:
    """Fetches issue data with changelog from JIRA"""

    def __init__(self, client: JiraClient, project_key: str):
        """
        Initialize JIRA fetcher

        Args:
            client: JiraClient instance
            project_key: JIRA project key to fetch issues from
        """
        self.client = client
        self.project_key = project_key
        self.cache_dir = JIRA_RAW_DIR / project_key
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch_all_issues(self, use_cache: bool = True) -> list:
        """
        Fetch all issues with changelog for the project

        Args:
            use_cache: Whether to use cached data

        Returns:
            List of issue dictionaries with changelog data
        """
        cache_file = self.cache_dir / "issues.json"

        if use_cache and cache_file.exists():
            print(f"  Loading {self.project_key} issues from cache...")
            with open(cache_file) as f:
                return json.load(f)

        print(f"  Fetching {self.project_key} issues from JIRA API...")
        issues = self._fetch_issues_paginated()

        # Cache the raw data
        with open(cache_file, 'w') as f:
            json.dump(issues, f, indent=2)
        print(f"  Cached {len(issues)} issues to {cache_file}")

        return issues

    def _fetch_issues_paginated(self) -> list:
        """Fetch all issues with pagination using nextPageToken"""
        issues = []
        next_page_token = None
        max_results = 100
        page_num = 1

        # Build JQL query for issues updated since cutoff date
        since_str = JIRA_DATA_SINCE.strftime("%Y-%m-%d")
        jql = f'project = "{self.project_key}" AND updated >= "{since_str}" ORDER BY updated DESC'

        while True:
            print(f"    Fetching page {page_num} (max {max_results} issues)...")

            try:
                result = self.client.search_issues(
                    jql=jql,
                    max_results=max_results,
                    expand=["changelog"],
                    fields=["summary", "assignee", "status", "created", "updated", "issuetype"],
                    next_page_token=next_page_token
                )
            except requests.exceptions.HTTPError as e:
                print(f"    Error fetching issues: {e}")
                break

            batch_issues = result.get("issues", [])
            if not batch_issues:
                break

            # Transform issues to simplified format
            for issue in batch_issues:
                transformed = self._transform_issue(issue)
                issues.append(transformed)

            print(f"      Retrieved {len(batch_issues)} issues (total so far: {len(issues)})")

            # Check for next page using nextPageToken
            next_page_token = result.get("nextPageToken")
            if not next_page_token:
                break

            page_num += 1

        print(f"    Fetched {len(issues)} total issues")
        return issues

    def _transform_issue(self, issue: dict) -> dict:
        """
        Transform raw JIRA issue to simplified format

        Args:
            issue: Raw issue from JIRA API

        Returns:
            Simplified issue dictionary
        """
        fields = issue.get("fields", {})
        changelog = issue.get("changelog", {})

        # Extract assignee
        assignee = None
        assignee_data = fields.get("assignee")
        if assignee_data:
            assignee = {
                "account_id": assignee_data.get("accountId"),
                "display_name": assignee_data.get("displayName"),
                "email": assignee_data.get("emailAddress")
            }

        # Extract status transitions from changelog
        status_transitions = []
        for history in changelog.get("histories", []):
            created = history.get("created")
            for item in history.get("items", []):
                if item.get("field") == "status":
                    status_transitions.append({
                        "timestamp": created,
                        "from_status": item.get("fromString"),
                        "to_status": item.get("toString")
                    })

        return {
            "key": issue.get("key"),
            "summary": fields.get("summary"),
            "issue_type": fields.get("issuetype", {}).get("name"),
            "status": fields.get("status", {}).get("name"),
            "assignee": assignee,
            "created": fields.get("created"),
            "updated": fields.get("updated"),
            "status_transitions": status_transitions
        }


def fetch_all_projects(use_cache: bool = True) -> dict:
    """
    Fetch issues for all JIRA projects the user has access to

    Discovers projects via the JIRA API rather than config.

    Args:
        use_cache: Whether to use cached data

    Returns:
        Dictionary mapping project_key to list of issues
    """
    email = os.getenv("JIRA_EMAIL")
    api_token = os.getenv("JIRA_API_TOKEN")

    if not email or not api_token:
        raise ValueError("JIRA_EMAIL and JIRA_API_TOKEN environment variables must be set")

    if not JIRA_BASE_URL:
        raise ValueError("JIRA_BASE_URL not configured")

    client = JiraClient(JIRA_BASE_URL, email, api_token)

    # Fetch all projects from JIRA API
    print("Discovering projects from JIRA API...")
    projects = client.get_all_projects()
    print(f"Found {len(projects)} projects")

    all_issues = {}

    for project in projects:
        project_key = project["key"]
        project_name = project["name"]
        print(f"Processing project: {project_key} ({project_name})")
        fetcher = JiraFetcher(client, project_key)
        all_issues[project_key] = fetcher.fetch_all_issues(use_cache=use_cache)

    return all_issues


def main():
    parser = argparse.ArgumentParser(description="Fetch JIRA issues with changelog")
    parser.add_argument("--project", help="Specific project key to fetch (optional)")
    parser.add_argument("--no-cache", action="store_true", help="Don't use cached data")
    args = parser.parse_args()

    email = os.getenv("JIRA_EMAIL")
    api_token = os.getenv("JIRA_API_TOKEN")

    if not email or not api_token:
        raise ValueError("JIRA_EMAIL and JIRA_API_TOKEN environment variables must be set")

    if not JIRA_BASE_URL:
        raise ValueError("JIRA_BASE_URL not configured")

    client = JiraClient(JIRA_BASE_URL, email, api_token)

    if args.project:
        # Fetch for specific project
        fetcher = JiraFetcher(client, args.project)
        issues = fetcher.fetch_all_issues(use_cache=not args.no_cache)
        print(f"Fetched {len(issues)} issues for {args.project}")
    else:
        # Fetch for all configured projects
        all_issues = fetch_all_projects(use_cache=not args.no_cache)
        total = sum(len(issues) for issues in all_issues.values())
        print(f"\nFetched {total} total issues across {len(all_issues)} projects")


if __name__ == "__main__":
    main()

"""Build pre-processed dashboard cache from raw commit data"""

import csv
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from src.data_processor import DataProcessor

CONFIG_PATH = Path("config/users.json")
ORG_CACHE_DIR = Path("data/cache/_orgs")
DASHBOARD_CACHE_PATH = Path("data/cache/dashboard_cache.csv")


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


def load_all_org_commits() -> dict:
    """
    Load all commits from org cache files.

    Returns:
        Dictionary mapping org_name -> repo_name -> list of commits
    """
    all_commits = {}
    organizations = load_organizations_config()

    for org_name in organizations:
        org_dir = ORG_CACHE_DIR / org_name
        if not org_dir.exists():
            continue

        all_commits[org_name] = {}
        for cache_file in org_dir.glob("*_commits.json"):
            repo_name = cache_file.stem.replace("_commits", "")
            with open(cache_file) as f:
                all_commits[org_name][repo_name] = json.load(f)

    return all_commits


def filter_commits_by_user(all_org_commits: dict, username: str) -> list:
    """Filter commits for a specific user across all orgs/repos"""
    user_commits = []
    seen_shas = set()

    for org_name, repos in all_org_commits.items():
        for repo_name, commits in repos.items():
            for commit in commits:
                if commit["author"].lower() == username.lower():
                    if commit["sha"] not in seen_shas:
                        user_commits.append(commit)
                        seen_shas.add(commit["sha"])

    return user_commits


def get_all_users_from_commits(all_org_commits: dict) -> list:
    """Extract all unique usernames from commit data"""
    users = set()
    for org_name, repos in all_org_commits.items():
        for repo_name, commits in repos.items():
            for commit in commits:
                author = commit.get("author", "unknown")
                if author and author.lower() != "unknown":
                    users.add(author)
    return sorted(users)


def build_dashboard_cache() -> dict:
    """
    Build pre-processed dashboard cache as CSV from raw commit data.
    Includes ALL users found in commits, not just configured users.

    Returns:
        Dictionary with all users' processed stats (also writes CSV)
    """
    print("Building dashboard cache...")

    all_org_commits = load_all_org_commits()

    # Get all users from commit data instead of config
    users = get_all_users_from_commits(all_org_commits)
    print(f"Found {len(users)} unique users in commit data")

    processor = DataProcessor()

    # Collect all rows for CSV
    csv_rows = []
    cache_data = {
        "generated_at": datetime.now().isoformat(),
        "users": {}
    }

    for username in users:
        print(f"  Processing {username}...")
        user_commits = filter_commits_by_user(all_org_commits, username)

        daily_stats = processor.process_commits(user_commits, username)
        summary = processor.calculate_summary(daily_stats, username)

        cache_data["users"][username] = {
            "daily_stats": daily_stats,
            "summary": summary,
            "commit_count": len(user_commits)
        }

        # Add rows to CSV
        for date_str, stats in daily_stats.items():
            csv_rows.append({
                "username": username,
                "date": date_str,
                "commits": stats["commits"],
                "additions": stats["additions"],
                "deletions": stats["deletions"],
                "net_lines": stats["net_lines"],
                "repositories": ";".join(stats["repositories"])
            })

        print(f"    {len(user_commits)} commits, {len(daily_stats)} active days")

    # Write CSV file
    DASHBOARD_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DASHBOARD_CACHE_PATH, 'w', newline='') as f:
        fieldnames = ["username", "date", "commits", "additions", "deletions", "net_lines", "repositories"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"Dashboard cache written to {DASHBOARD_CACHE_PATH} ({len(csv_rows)} rows)")
    return cache_data


def load_dashboard_cache() -> dict:
    """
    Load pre-processed dashboard cache from CSV.

    Returns:
        Dictionary with all users' processed stats, or None if not found
    """
    if not DASHBOARD_CACHE_PATH.exists():
        return None

    # Read CSV and reconstruct the data structure
    users_data = defaultdict(lambda: {"daily_stats": {}, "commits": []})

    with open(DASHBOARD_CACHE_PATH, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            username = row["username"]
            date_str = row["date"]

            users_data[username]["daily_stats"][date_str] = {
                "commits": int(row["commits"]),
                "additions": int(row["additions"]),
                "deletions": int(row["deletions"]),
                "net_lines": int(row["net_lines"]),
                "repositories": row["repositories"].split(";") if row["repositories"] else [],
                "username": username
            }

    # Calculate summaries from the daily stats
    result = {
        "generated_at": datetime.fromtimestamp(DASHBOARD_CACHE_PATH.stat().st_mtime).isoformat(),
        "users": {}
    }

    processor = DataProcessor()
    for username, data in users_data.items():
        daily_stats = dict(sorted(data["daily_stats"].items()))
        summary = processor.calculate_summary(daily_stats, username)
        result["users"][username] = {
            "daily_stats": daily_stats,
            "summary": summary,
            "commit_count": sum(s["commits"] for s in daily_stats.values())
        }

    return result


if __name__ == "__main__":
    build_dashboard_cache()

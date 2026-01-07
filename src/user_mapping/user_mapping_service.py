"""Service for loading and querying user mappings from CSV"""

import csv
from typing import Optional

from src.config import USER_MAPPING_CSV

# In-memory cache for user mappings
_mappings_cache = None
_mappings_cache_mtime = None


def get_user_mappings() -> list:
    """
    Load user mappings from CSV export with caching.

    Returns:
        List of dicts with 'github' and 'jira' keys, or empty list if not found
    """
    global _mappings_cache, _mappings_cache_mtime

    if not USER_MAPPING_CSV.exists():
        return []

    # Check if cache is still valid
    current_mtime = USER_MAPPING_CSV.stat().st_mtime
    if _mappings_cache is not None and _mappings_cache_mtime == current_mtime:
        return _mappings_cache

    mappings = []
    with open(USER_MAPPING_CSV, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            mappings.append({
                "github": row.get("github", ""),
                "jira": row.get("jira", "")
            })

    # Update cache
    _mappings_cache = mappings
    _mappings_cache_mtime = current_mtime

    return mappings


def get_jira_email_for_github_user(github_username: str) -> Optional[str]:
    """
    Look up JIRA email for a GitHub username.

    Args:
        github_username: GitHub username to look up

    Returns:
        JIRA email address, or None if not found
    """
    mappings = get_user_mappings()

    for mapping in mappings:
        if mapping["github"].lower() == github_username.lower():
            return mapping["jira"]

    return None


def get_github_user_for_jira_email(jira_email: str) -> Optional[str]:
    """
    Look up GitHub username for a JIRA email.

    Args:
        jira_email: JIRA email address to look up

    Returns:
        GitHub username, or None if not found
    """
    mappings = get_user_mappings()

    for mapping in mappings:
        if mapping["jira"].lower() == jira_email.lower():
            return mapping["github"]

    return None


def clear_cache() -> None:
    """Clear the in-memory cache (useful for testing or after regenerating mappings)."""
    global _mappings_cache, _mappings_cache_mtime
    _mappings_cache = None
    _mappings_cache_mtime = None

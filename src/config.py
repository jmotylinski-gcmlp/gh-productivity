"""Centralized configuration for the productivity tracker"""

from datetime import datetime
from pathlib import Path


# =============================================================================
# Base Paths
# =============================================================================

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
EXPORTS_DIR = DATA_DIR / "exports"


# =============================================================================
# GitHub Configuration
# =============================================================================

# Organizations to track
GITHUB_ORGANIZATIONS = [
    "GCMGrosvenor"
]

# API
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

# Data fetch cutoff date
GITHUB_DATA_SINCE = datetime(2023, 1, 1)

# Cache paths
GITHUB_COMMITS_RAW_DIR = RAW_DIR / "_orgs"
GITHUB_PRS_RAW_DIR = RAW_DIR / "github" / "prs"

# Export paths
GITHUB_EXPORTS_DIR = EXPORTS_DIR / "github"
GITHUB_USER_COMMITS_CSV = GITHUB_EXPORTS_DIR / "user_commits.csv"
GITHUB_PRS_CSV = GITHUB_EXPORTS_DIR / "prs.csv"


# =============================================================================
# JIRA Configuration
# =============================================================================

# JIRA instance URL
JIRA_BASE_URL = "https://gcmlp1.atlassian.net/"

# Data fetch cutoff date
JIRA_DATA_SINCE = datetime(2023, 1, 1)

# Cache paths
JIRA_RAW_DIR = RAW_DIR / "jira"

# Export paths
JIRA_EXPORTS_DIR = EXPORTS_DIR / "jira"
JIRA_USER_ISSUES_CSV = JIRA_EXPORTS_DIR / "user_issues.csv"


# =============================================================================
# User Mapping Configuration
# =============================================================================

# Export paths
USER_MAPPING_EXPORTS_DIR = EXPORTS_DIR / "user_mapping"
USER_MAPPING_CSV = USER_MAPPING_EXPORTS_DIR / "mapping.csv"


# =============================================================================
# Dashboard Configuration
# =============================================================================

DASHBOARD_DIR = BASE_DIR / "dashboard"

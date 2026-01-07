# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Productivity Tracker is a tool that analyzes developer productivity metrics from both GitHub and JIRA. It provides:
1. **GitHub Commit Metrics**: Daily lines of code (additions/deletions) per user from commit data
2. **GitHub PR Metrics**: Pull request time open, time to first review, reviewer counts by repository
3. **JIRA Metrics**: Cycle time analysis (time issues spend "In Progress" before moving to next state)
4. **Data Exports**: CSV files saved to `data/exports/github/` and `data/exports/jira/` for external analysis
5. **Web Dashboard**: A Flask backend with charts showing GitHub lines changed, PR metrics, and JIRA cycle times by month

## Architecture

### Core Components

**Configuration (`src/config.py`)**
- Centralized Python configuration file containing all constants and settings
- GitHub organizations to track
- JIRA base URL
- All file paths (raw data, exports)

**GitHub Module (`src/github/`)**
- `commit_fetcher.py` - Uses GraphQL API to fetch commits from GitHub, caches in `data/raw/_orgs/`
- `commit_processor.py` - Aggregates commits into daily stats, builds dashboard cache CSV
- `pr_fetcher.py` - Fetches Pull Request data from GitHub GraphQL API
- `pr_processor.py` - Calculates PR metrics (time open, time to review, etc.)

**JIRA Module (`src/jira/`)**
- `jira_fetcher.py` - Fetches issues with changelog from JIRA REST API v3
- `jira_processor.py` - Extracts "In Progress" cycle times, outputs to CSV

**User Mapping Module (`src/user_mapping/`)**
- `user_mapping_processor.py` - Fuzzy matches GitHub usernames to JIRA email addresses
  - Reads from `data/exports/github/user_commits.csv` and `data/exports/jira/user_issues.csv`
  - Outputs mappings to `data/exports/user_mapping/mapping.csv`
- `user_mapping_service.py` - Service layer for loading user mappings
  - Loads mappings from CSV with in-memory caching
  - Provides `get_user_mappings()`, `get_jira_email_for_github_user()`, `get_github_user_for_jira_email()`

**Web Backend (`src/app.py` + `src/api/` + `src/routes.py`)**
- Flask application using Blueprints for modular route organization
- `src/app.py` - Main app factory, registers blueprints
- `src/api/github.py` - GitHub commit API endpoints
- `src/api/jira.py` - JIRA API endpoints
- `src/api/pr.py` - Pull Request API endpoints
- `src/routes.py` - Website routes (serves dashboard HTML)

**API Endpoints:**
- GitHub endpoints (`src/api/github.py`):
  - `GET /api/users` - list configured users
  - `GET /api/user-mappings` - GitHub to JIRA user mappings
  - `GET /api/users/all/stats` - all users' GitHub commit data
  - `GET /api/daily-stats?user={username}` - single user stats
  - `GET /api/summary?user={username}` - summary statistics
  - `GET /api/timeline?user={username}` - timeline format data
  - `GET /api/cache-info` - dashboard cache information
  - `POST /api/refresh` - refresh all users' data
- JIRA endpoints (`src/api/jira.py`):
  - `GET /api/jira/cycles?email={email}` - cycle time data for a user
  - `GET /api/jira/stats?email={email}` - overall statistics
  - `GET /api/jira/stats/monthly?email={email}` - monthly cycle time stats
  - `GET /api/jira/stats/by-user` - stats grouped by user
- PR endpoints (`src/api/pr.py`):
  - `GET /api/pr/repositories` - list repositories with PR data
  - `GET /api/pr/stats?repo={repo}` - overall PR stats for a repository
  - `GET /api/pr/stats/monthly?repo={repo}` - monthly PR metrics breakdown

**Web Dashboard (`dashboard/`)**
- Organized into domain-specific subdirectories, each with `index.html` and corresponding JS
- Main `index.html` redirects to single-user dashboard
- Navigation links in header allow switching between dashboards
- **Single User** (`single-user/`): Default landing page
  - Single GitHub username input (JIRA email auto-looked up from mappings)
  - Date range selector
  - GitHub lines changed chart with trend line and tool enablement markers
  - JIRA cycle time chart with trend line and tool enablement markers
  - Collapsible data tables for both metrics
  - Annotation markers: GitHub Copilot (2023-07), Cursor (2025-02)
- **PR Metrics** (`prs/`): Pull request metrics by repository
  - Repository dropdown selector
  - Date range selector
  - Average PR time open by month chart with trend line
  - Average time to first review by month chart with trend line
  - Summary stats (total PRs, avg time open, avg reviewers)
  - Collapsible data table with monthly breakdown
- **User Comparison** (`compare/`): Side-by-side comparison of two users
- **Individual User Stats** (`user/`): Detailed view for a single user
- **JIRA Stats** (`jira/`): JIRA cycle time statistics by user

### Directory Structure

```
gh-productivity/
├── src/
│   ├── __init__.py
│   ├── config.py               # Centralized configuration (orgs, paths)
│   ├── app.py                  # Flask app factory, registers blueprints
│   ├── routes.py               # Website routes (serves dashboard HTML)
│   ├── api/                    # API route blueprints
│   │   ├── __init__.py
│   │   ├── github.py           # GitHub commit API endpoints
│   │   ├── jira.py             # JIRA API endpoints
│   │   └── pr.py               # Pull Request API endpoints
│   ├── github/
│   │   ├── __init__.py
│   │   ├── commit_fetcher.py   # GitHub commits API integration
│   │   ├── commit_processor.py # Commit data aggregation and cache building
│   │   ├── pr_fetcher.py       # GitHub PR API integration
│   │   └── pr_processor.py     # PR metrics calculation
│   ├── jira/
│   │   ├── __init__.py
│   │   ├── jira_fetcher.py     # JIRA API integration
│   │   └── jira_processor.py   # Cycle time extraction
│   └── user_mapping/
│       ├── __init__.py
│       ├── user_mapping_processor.py  # GitHub to JIRA fuzzy matching
│       └── user_mapping_service.py    # Service for loading mappings
├── dashboard/
│   ├── index.html              # Main redirect to single-user/
│   ├── style.css               # Shared styles
│   ├── single-user/            # Single-user dashboard (default)
│   │   ├── index.html
│   │   └── single-user.js
│   ├── prs/                    # PR metrics dashboard
│   │   ├── index.html
│   │   └── prs.js
│   ├── compare/                # Multi-user comparison
│   │   ├── index.html
│   │   └── compare.js
│   ├── user/                   # Individual user stats
│   │   ├── index.html
│   │   └── user.js
│   └── jira/                   # JIRA cycle time stats
│       ├── index.html
│       └── jira.js
├── data/
│   ├── raw/
│   │   ├── _orgs/              # Raw GitHub commits by organization
│   │   │   └── {org}/
│   │   │       └── {repo}_commits.json
│   │   └── github/prs/         # Raw GitHub PRs by organization
│   │       └── {org}/
│   │           └── {repo}_prs.json
│   └── exports/
│       ├── github/
│       │   ├── user_commits.csv    # Aggregated GitHub commit data
│       │   └── prs.csv             # PR data with calculated metrics
│       ├── jira/
│       │   └── user_issues.csv     # JIRA cycle time data
│       └── user_mapping/
│           └── mapping.csv         # GitHub to JIRA user mappings
├── tests/                      # Unit tests
├── .env                        # Environment variables (not in git)
├── requirements.txt            # Python dependencies
├── startup.sh                  # Local production server startup (gunicorn)
├── create.sh                   # Azure infrastructure provisioning
├── deploy.sh                   # Azure deployment script
├── README.md
└── CLAUDE.md
```

## Common Commands

### Development Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with tokens
echo "GITHUB_TOKEN=your_github_token" > .env
echo "JIRA_EMAIL=your_email@company.com" >> .env
echo "JIRA_API_TOKEN=your_jira_token" >> .env

# Configuration is in src/config.py (organizations, JIRA URL, user mappings)
```

### Running the Application

```bash
# Fetch GitHub commit data for all configured organizations
python3 -m src.github.commit_fetcher

# Fetch GitHub PR data for all configured organizations
python3 -m src.github.pr_fetcher

# Process PR data to CSV (outputs to data/exports/github/prs.csv)
python3 -m src.github.pr_processor

# Fetch JIRA data for all projects
python3 -m src.jira.jira_fetcher

# Process JIRA issues to CSV
python3 -m src.jira.jira_processor

# Generate GitHub to JIRA user mappings (outputs to data/exports/user_mapping/mapping.csv)
python3 -m src.user_mapping.user_mapping_processor

# Start web server - Development (runs on http://localhost:5000)
python3 -m src.app

# Start web server - Production with gunicorn (runs on http://localhost:8000)
./startup.sh
```

### Single User Tasks

```bash
# Fetch commits for a specific user only
python3 -m src.github.commit_fetcher --user "username"

# Clear cache and re-fetch from GitHub
python3 -m src.github.commit_fetcher --no-cache
python3 -m src.github.pr_fetcher --no-cache
```

### Testing

```bash
# Run all tests
python3 -m pytest

# Run specific test file
python3 -m pytest tests/test_data_processor.py

# Run with coverage
python3 -m pytest --cov=src
```

### Azure Deployment

```bash
# First time: Create Azure infrastructure (resource group, app service plan, web app)
./create.sh

# Deploy the application to Azure
./deploy.sh
```

**`create.sh`** - Infrastructure provisioning (run once)
- Creates resource group `jmotylinski-sandbox` in `eastus`
- Creates App Service plan with F1 (free) tier on Linux
- Creates web app `gh-productivity` with Python 3.11 runtime

**`deploy.sh`** - Application deployment
- Configures gunicorn startup command for the web app
- Sets app settings (`SCM_DO_BUILD_DURING_DEPLOYMENT`, `PYTHONPATH`)
- Creates zip package excluding venv, cache, .env, and shell scripts
- Deploys via `az webapp deployment source config-zip`
- App URL: https://gh-productivity.azurewebsites.net

**Note**: If you encounter SSL certificate errors behind a corporate proxy, set:
```bash
export AZURE_CLI_DISABLE_CONNECTION_VERIFICATION=1
```

## Key Implementation Details

### Configuration

All configuration is centralized in `src/config.py`:
```python
# GitHub organizations to track
GITHUB_ORGANIZATIONS = ["GCMGrosvenor"]

# JIRA instance URL
JIRA_BASE_URL = "https://gcmlp1.atlassian.net/"

# Data fetch cutoff date (only fetch data since this date)
GITHUB_DATA_SINCE = datetime(2023, 1, 1)
JIRA_DATA_SINCE = datetime(2023, 1, 1)

# File paths for raw data and exports
GITHUB_COMMITS_RAW_DIR = RAW_DIR / "_orgs"
USER_MAPPING_CSV = EXPORTS_DIR / "user_mapping" / "mapping.csv"
```

### User Mapping

The `src/user_mapping/` module handles GitHub to JIRA user mappings:

**Processor (`user_mapping_processor.py`)**:
- Extracts unique GitHub usernames from `data/exports/github/user_commits.csv`
- Extracts unique JIRA emails from `data/exports/jira/user_issues.csv`
- Normalizes names (removes `-gcmlp`, `-gcm` suffixes)
- Uses fuzzy matching (SequenceMatcher) with 0.7 threshold
- Outputs mappings to `data/exports/user_mapping/mapping.csv`

**Service (`user_mapping_service.py`)**:
- Loads mappings from CSV with in-memory caching (cache invalidated when file changes)
- `get_user_mappings()` - Returns list of all mappings
- `get_jira_email_for_github_user(username)` - Look up JIRA email for GitHub user
- `get_github_user_for_jira_email(email)` - Look up GitHub user for JIRA email

### GitHub API Rate Limiting

- GitHub API has rate limits (~5000 requests/hour for authenticated users)
- Caching is critical: cache API responses in `data/raw/_orgs/{org}/` with timestamps
- Implement exponential backoff for rate limit handling
- Check `X-RateLimit-Remaining` headers before making requests

### JIRA API Integration

- Uses JIRA REST API v3 with `/rest/api/3/search/jql` endpoint
- Pagination via `nextPageToken` (not deprecated `startAt`)
- Fetches issues with `changelog` expansion to get status transitions
- Extracts "In Progress" cycles (time from entering to leaving "In Progress" status)
- Caches issues per project in `data/raw/jira/{project}/`

### Data Exports

- **GitHub Commits**: `data/exports/github/user_commits.csv`
  - Columns: username, date, commits, additions, deletions, net_lines, repositories
- **GitHub PRs**: `data/exports/github/prs.csv`
  - Columns: repository, pr_number, title, author, state, created_at, closed_at, merged_at, time_open_hours, time_to_first_review_hours, reviewer_count, additions, deletions, changed_files
- **JIRA**: `data/exports/jira/user_issues.csv`
  - Columns: key, assignee_email, in_progress_at, out_of_progress_at
- **User Mapping**: `data/exports/user_mapping/mapping.csv`
  - Columns: github, jira

### Web Dashboard Data Flow

**Single User View (`/single-user/`)**
1. Page loads and fetches `/api/user-mappings` to get GitHub→JIRA mappings
2. User enters GitHub username and date range, clicks Search
3. Frontend looks up corresponding JIRA email from mappings
4. Fetches `/api/users/all/stats` (GitHub) and `/api/jira/stats/monthly?email=...` (JIRA) in parallel
5. Renders JIRA cycle time chart and GitHub lines changed chart with trend lines
6. Data tables are collapsible (collapsed by default)

**User Comparison (`/compare/`)**
1. Dashboard loads and requests `/api/users/all/stats`
2. Backend fetches/returns data for all configured users
3. Frontend renders side-by-side user cards with charts and tables
4. "Refresh All" triggers `POST /api/refresh` to update all users

**PR Metrics (`/prs/`)**
1. Page loads and fetches `/api/pr/repositories` to populate dropdown
2. User selects repository and date range, clicks Search
3. Fetches `/api/pr/stats?repo=...` and `/api/pr/stats/monthly?repo=...` in parallel
4. Renders PR time open chart and time to first review chart with trend lines
5. Data table shows monthly breakdown with all metrics

**JIRA Stats (`/jira/`)**
1. Page loads and fetches `/api/jira/stats/by-user` for all users
2. Displays overall statistics summary and cycle time chart
3. User table shows cycle time breakdown by user

## Development Notes

- **Environment Variables**: Always use `.env` file; load with `python-dotenv` if needed
- **API Authentication**: Use GitHub token and JIRA token from environment, never hardcode
- **Error Handling**: API requests can fail; implement retry logic with backoff
- **Data Privacy**: Don't commit API tokens or real user data; gitignore sensitive files
- **Testing**: Mock API responses in unit tests to avoid hitting rate limits

## External Dependencies

### Python
- **PyGithub**: GitHub API client library
- **Flask**: Web framework for backend API
- **gunicorn**: Production WSGI server
- **pandas**: Data manipulation and export to CSV
- **requests**: HTTP client for JIRA API calls

### Frontend (CDN)
- **Chart.js**: Bar charts and line charts for data visualization
- **chartjs-plugin-annotation**: Vertical line annotations for tool enablement dates

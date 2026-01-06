# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Productivity Tracker is a tool that analyzes developer productivity metrics from both GitHub and JIRA. It provides:
1. **GitHub Metrics**: Daily lines of code (additions/deletions) per user from commit data
2. **JIRA Metrics**: Cycle time analysis (time issues spend "In Progress" before moving to next state)
3. **Data Exports**: CSV files saved to `data/exports/github/` and `data/exports/jira/` for external analysis
4. **Web Dashboard**: A Flask backend with charts showing GitHub lines changed and JIRA cycle times by month

## Architecture

### Core Components

**User Configuration (`config.json`)**
- JSON file containing GitHub usernames, organizations to track, and user mappings
- `user_mappings` array maps GitHub usernames to JIRA email addresses for unified dashboard

**GitHub Module (`src/github/`)**
- `github_fetcher.py` - Uses PyGithub to fetch commits from GitHub API, caches in `data/cache/_orgs/`
- `github_processor.py` - Aggregates commits into daily stats, builds dashboard cache CSV
- `exporter.py` - Exports processed data to JSON/CSV formats

**JIRA Module (`src/jira/`)**
- `jira_fetcher.py` - Fetches issues with changelog from JIRA REST API v3
- `jira_processor.py` - Extracts "In Progress" cycle times, outputs to CSV

**User Mapping (`src/user_mapper.py`)**
- Fuzzy matches GitHub usernames to JIRA email addresses
- Reads from `data/exports/github/user_commits.csv` and `data/exports/jira/user_issues.csv`
- Writes mappings to `config.json` under `user_mappings` key

**Web Backend (`src/app.py`)**
- Flask application serving JSON data endpoints
- GitHub endpoints:
  - `GET /api/users` - list configured users
  - `GET /api/user-mappings` - GitHub to JIRA user mappings
  - `GET /api/users/all/stats` - all users' GitHub data
  - `GET /api/daily-stats?user={username}` - single user stats
  - `POST /api/refresh` - refresh all users' data
- JIRA endpoints:
  - `GET /api/jira/cycles?email={email}` - cycle time data for a user
  - `GET /api/jira/stats?email={email}` - overall statistics
  - `GET /api/jira/stats/monthly?email={email}` - monthly cycle time stats
  - `GET /api/jira/stats/by-user` - stats grouped by user
- Serves static dashboard files from `dashboard/`

**Web Dashboard (`dashboard/`)**
- **Single User View** (`index.html` + `single-user.js`): Default landing page
  - Single GitHub username input (JIRA email auto-looked up from mappings)
  - Date range selector
  - JIRA cycle time chart with trend line and tool enablement markers
  - GitHub lines changed chart with trend line and tool enablement markers
  - Collapsible data tables for both metrics
  - Annotation markers: GitHub Copilot (2023-07), Cursor (2025-02)
- **User Comparison** (`compare.html` + `script.js`): Side-by-side comparison of two users
- **Individual User Stats** (`user.html` + `user.js`): Detailed view for a single user

### Directory Structure

```
gh-productivity/
├── config.json                 # Users, orgs, JIRA config, and user mappings
├── src/
│   ├── __init__.py
│   ├── app.py                  # Flask web backend
│   ├── user_mapper.py          # GitHub to JIRA user fuzzy matching
│   ├── github/
│   │   ├── __init__.py
│   │   ├── github_fetcher.py   # GitHub API integration
│   │   ├── github_processor.py # Data aggregation and cache building
│   │   └── exporter.py         # JSON/CSV export logic
│   └── jira/
│       ├── __init__.py
│       ├── jira_fetcher.py     # JIRA API integration
│       └── jira_processor.py   # Cycle time extraction
├── dashboard/
│   ├── index.html              # Single-user dashboard (default landing page)
│   ├── single-user.js          # JavaScript for single-user view
│   ├── compare.html            # Multi-user comparison
│   ├── script.js               # JavaScript for comparison view
│   ├── user.html               # Individual user stats page
│   ├── user.js                 # JavaScript for user stats page
│   └── style.css               # Shared styles
├── data/
│   ├── cache/
│   │   └── _orgs/              # Cached GitHub commits by organization
│   │       └── {org}/
│   │           └── {repo}_commits.json
│   └── exports/
│       ├── github/
│       │   └── user_commits.csv    # Aggregated GitHub commit data
│       └── jira/
│           └── user_issues.csv     # JIRA cycle time data
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

# Configure users to track in config.json
```

### Running the Application

```bash
# Fetch GitHub data for all configured organizations
python3 -m src.github.github_fetcher

# Fetch JIRA data for all projects
python3 -m src.jira.jira_fetcher

# Process JIRA issues to CSV
python3 -m src.jira.jira_processor

# Generate GitHub to JIRA user mappings
python3 -m src.user_mapper

# Start web server - Development (runs on http://localhost:5000)
python3 -m src.app

# Start web server - Production with gunicorn (runs on http://localhost:8000)
./startup.sh
```

### Single User Tasks

```bash
# Fetch commits for a specific user only
python3 -m src.github.github_fetcher --user "username"

# Export to specific format for a specific user
python3 -m src.github.exporter --user "username" --format json

# Clear cache and re-fetch from GitHub
python3 -m src.github.github_fetcher --no-cache
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

### User Configuration

Users are configured in `config.json`:
```json
{
  "users": ["user1-gcmlp", "user2-gcm"],
  "organizations": ["GCMGrosvenor"],
  "jira": {
    "base_url": "https://company.atlassian.net/"
  },
  "user_mappings": [
    { "github": "user1-gcmlp", "jira": "user1@company.com" },
    { "github": "user2-gcm", "jira": "user2@company.com" }
  ]
}
```

- `organizations` - GitHub organizations to fetch commits from
- `user_mappings` - Maps GitHub usernames to JIRA emails for unified dashboard view
- Run `python3 -m src.user_mapper` to auto-generate mappings using fuzzy matching

### User Mapping

The `src/user_mapper.py` script automatically maps GitHub usernames to JIRA emails:
- Extracts unique GitHub usernames from `data/exports/github/user_commits.csv`
- Extracts unique JIRA emails from `data/exports/jira/user_issues.csv`
- Normalizes names (removes `-gcmlp`, `-gcm` suffixes)
- Uses fuzzy matching (SequenceMatcher) with 0.7 threshold
- Writes matches to `config.json` under `user_mappings`

### GitHub API Rate Limiting

- GitHub API has rate limits (~5000 requests/hour for authenticated users)
- Caching is critical: cache API responses in `data/cache/_orgs/{org}/` with timestamps
- Implement exponential backoff for rate limit handling
- Check `X-RateLimit-Remaining` headers before making requests

### JIRA API Integration

- Uses JIRA REST API v3 with `/rest/api/3/search/jql` endpoint
- Pagination via `nextPageToken` (not deprecated `startAt`)
- Fetches issues with `changelog` expansion to get status transitions
- Extracts "In Progress" cycles (time from entering to leaving "In Progress" status)
- Caches issues per project in `data/cache/jira/{project}/`

### Data Exports

- **GitHub**: `data/exports/github/user_commits.csv`
  - Columns: username, date, commits, additions, deletions, net_lines, repositories
- **JIRA**: `data/exports/jira/user_issues.csv`
  - Columns: key, assignee_email, in_progress_at, out_of_progress_at

### Web Dashboard Data Flow

**Single User View (index.html)**
1. Page loads and fetches `/api/user-mappings` to get GitHub→JIRA mappings
2. User enters GitHub username and date range, clicks Search
3. Frontend looks up corresponding JIRA email from mappings
4. Fetches `/api/users/all/stats` (GitHub) and `/api/jira/stats/monthly?email=...` (JIRA) in parallel
5. Renders JIRA cycle time chart and GitHub lines changed chart with trend lines
6. Data tables are collapsible (collapsed by default)

**User Comparison (compare.html)**
1. Dashboard loads and requests `/api/users/all/stats`
2. Backend fetches/returns data for all configured users
3. Frontend renders side-by-side user cards with charts and tables
4. "Refresh All" triggers `POST /api/refresh` to update all users

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

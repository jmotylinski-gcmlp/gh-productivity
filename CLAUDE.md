# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GitHub Productivity Tracker is a tool that analyzes daily lines of code written by multiple GitHub users. It fetches commit data from the GitHub API, calculates daily line changes (additions/deletions), and provides two main outputs:
1. **Data Exports**: JSON and CSV files saved to `data/exports/{username}/` for external analysis
2. **Web Dashboard**: A Flask backend with a side-by-side comparison dashboard for multiple users

## Architecture

### Core Components

**User Configuration (`config/users.json`)**
- JSON file containing list of GitHub usernames to track
- Edit this file to add/remove users from tracking

**Data Fetching (`src/github_fetcher.py`)**
- Uses PyGithub library to authenticate with GitHub API
- Fetches all commits for all configured users across their repositories
- Caches API responses in `data/cache/{username}/` to avoid rate limiting
- Extracts commit metadata: timestamp, added lines, deleted lines, files changed

**Data Processing (`src/data_processor.py`)**
- Aggregates commits into daily statistics per user
- Calculates net lines of code (added - deleted)
- Supports processing all users via `process_all_users()`
- Handles multiple repositories and branches

**Data Export (`src/exporter.py`)**
- Exports processed data to JSON and CSV formats per user
- Creates timestamped files in `data/exports/{username}/`
- Includes summary statistics and username in output

**Web Backend (`src/app.py`)**
- Flask application serving JSON data endpoints
- Multi-user endpoints:
  - `GET /api/users` - list configured users
  - `GET /api/users/all/stats` - all users' data for comparison
  - `GET /api/daily-stats?user={username}` - single user stats
  - `GET /api/summary?user={username}` - single user summary
  - `POST /api/refresh` - refresh all users' data
- Serves static dashboard files from `dashboard/`

**Web Dashboard (`dashboard/`)**
- **Single User View** (`index.html` + `single-user.js`): Default landing page for viewing one user's statistics
  - Username input with date range selector
  - Bar chart showing lines changed by month with trend line
  - Annotation markers for tool enablement dates (GitHub Copilot: 2023-07, Cursor: 2025-02)
  - Table showing monthly breakdown: Lines Changed, Additions, Deletions, Commits
- **User Comparison** (`compare.html` + `script.js`): Hidden page for side-by-side comparison of multiple users
  - Accessible at `/compare.html` directly
  - Each user card displays: summary stats, daily chart, breakdown table
  - Single "Refresh All" button to update all users' data
- **Individual User Stats** (`user.html` + `user.js`): Detailed view for a single user (linked from compare page)

### Directory Structure

```
gh-productivity/
├── config/
│   └── users.json              # List of GitHub usernames to track
├── src/
│   ├── __init__.py
│   ├── github_fetcher.py       # GitHub API integration
│   ├── data_processor.py       # Data aggregation and processing
│   ├── exporter.py             # JSON/CSV export logic
│   └── app.py                  # Flask web backend
├── dashboard/
│   ├── index.html              # Single-user dashboard (default landing page)
│   ├── single-user.js          # JavaScript for single-user view
│   ├── compare.html            # Multi-user comparison (hidden)
│   ├── script.js               # JavaScript for comparison view
│   ├── user.html               # Individual user stats page
│   ├── user.js                 # JavaScript for user stats page
│   └── style.css               # Shared styles
├── data/
│   ├── cache/
│   │   ├── {username}/         # Per-user cache directories
│   │   │   └── {repo}_commits.json
│   └── exports/
│       ├── {username}/         # Per-user export directories
│       │   └── stats_{date}.json
├── tests/                      # Unit tests
├── .env                        # Environment variables (not in git)
├── requirements.txt            # Python dependencies
├── startup.sh                  # Production server startup (gunicorn)
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

# Create .env file with GitHub token
echo "GITHUB_TOKEN=your_token" > .env

# Configure users to track in config/users.json
```

### Running the Application

```bash
# Fetch data for all configured users
python3 -m src.github_fetcher

# Export data for all users
python3 -m src.exporter

# Start web server - Development (runs on http://localhost:5000)
python3 -m src.app

# Start web server - Production with gunicorn (runs on http://localhost:8000)
./startup.sh
```

### Single User Tasks

```bash
# Fetch commits for a specific user only
python3 -m src.github_fetcher --user "username"

# Export to specific format for a specific user
python3 -m src.exporter --user "username" --format json

# Clear cache and re-fetch from GitHub
python3 -m src.github_fetcher --no-cache
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

## Key Implementation Details

### User Configuration

- Users are configured in `config/users.json`:
  ```json
  {
    "users": ["user1", "user2", "user3"]
  }
  ```
- Add or remove users by editing this file
- The main dashboard (`index.html`) allows searching for any configured user
- The comparison page (`compare.html`) displays all configured users side-by-side

### GitHub API Rate Limiting

- GitHub API has rate limits (~5000 requests/hour for authenticated users)
- Caching is critical: always cache API responses in `data/cache/{username}/` with timestamps
- Implement exponential backoff for rate limit handling
- Check `X-RateLimit-Remaining` headers before making requests

### Line Count Calculation

- Use commit diff statistics: `additions` and `deletions` fields from the GitHub API
- Handle edge cases:
  - Binary files may not have line counts
  - Rename-only commits show 0 additions/deletions
  - Large refactors might have inflated numbers due to formatting changes
- Consider filtering out generated code, vendored dependencies, or automated commits if relevant

### Data Persistence

- Cache GitHub API responses per user with date stamps to allow incremental updates
- Export files are per-user and timestamped: `{username}/stats_2026-01-01.json`
- Each user's data is isolated in their own subdirectory

### Web Dashboard Data Flow

**Single User View (index.html)**
1. User enters username and date range, clicks Search
2. Frontend requests `/api/users/all/stats`
3. Filters data for the specified user and date range
4. Renders bar chart with trend line and monthly data table

**User Comparison (compare.html)**
1. Dashboard loads and requests `/api/users/all/stats`
2. Backend fetches/returns data for all configured users
3. Frontend renders side-by-side user cards with charts and tables
4. "Refresh All" triggers `POST /api/refresh` to update all users

## Development Notes

- **Environment Variables**: Always use `.env` file; load with `python-dotenv` if needed
- **API Authentication**: Use GitHub token from environment, never hardcode
- **Error Handling**: GitHub API requests can fail; implement retry logic with backoff
- **Data Privacy**: Don't commit API tokens or real user data; gitignore sensitive files
- **Testing**: Mock GitHub API responses in unit tests to avoid hitting rate limits

## External Dependencies

### Python
- **PyGithub**: GitHub API client library
- **Flask**: Web framework for backend API
- **gunicorn**: Production WSGI server
- **pandas**: Data manipulation and export to CSV
- **requests**: HTTP client for API calls

### Frontend (CDN)
- **Chart.js**: Bar charts and line charts for data visualization
- **chartjs-plugin-annotation**: Vertical line annotations for tool enablement dates

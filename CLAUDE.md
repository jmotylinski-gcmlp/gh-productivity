# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GitHub Productivity Tracker is a tool that analyzes daily lines of code written by a GitHub user. It fetches commit data from the GitHub API, calculates daily line changes (additions/deletions), and provides two main outputs:
1. **Data Exports**: JSON and CSV files saved to `data/exports/` for external analysis
2. **Web Dashboard**: A Flask backend with a frontend for interactive visualization of productivity trends

## Architecture

### Core Components

**Data Fetching (`src/github_fetcher.py`)**
- Uses PyGithub library to authenticate with GitHub API
- Fetches all commits for specified user across all repositories
- Caches API responses in `data/cache/` to avoid rate limiting
- Extracts commit metadata: timestamp, added lines, deleted lines, files changed

**Data Processing (`src/data_processor.py`)**
- Aggregates commits into daily statistics
- Calculates net lines of code (added - deleted)
- Filters out merge commits and bot commits if needed
- Handles multiple repositories and branches

**Data Export (`src/exporter.py`)**
- Exports processed data to JSON and CSV formats
- Creates timestamped files in `data/exports/`
- Includes summary statistics (daily, weekly, monthly totals)

**Web Backend (`src/app.py`)**
- Flask application serving JSON data endpoints
- Routes: `/api/daily-stats`, `/api/summary`, `/api/timeline`
- Serves static dashboard files from `dashboard/dist/`

**Web Dashboard (`dashboard/`)**
- Single-page application (built with HTML/CSS/JS or a framework)
- Visualizes daily stats as charts/graphs
- Allows filtering by date range
- Displays trends and productivity metrics

### Directory Structure

```
gh-productivity/
├── src/
│   ├── __init__.py
│   ├── github_fetcher.py      # GitHub API integration
│   ├── data_processor.py       # Data aggregation and processing
│   ├── exporter.py             # JSON/CSV export logic
│   └── app.py                  # Flask web backend
├── dashboard/                  # Web frontend (HTML/CSS/JS or framework)
│   ├── index.html
│   ├── style.css
│   └── script.js
├── data/
│   ├── cache/                  # GitHub API response cache
│   └── exports/                # Generated JSON/CSV files
├── tests/                      # Unit tests
├── .env                        # Environment variables (not in git)
├── requirements.txt            # Python dependencies
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

# Create .env file with GitHub token and username
echo "GITHUB_TOKEN=your_token" > .env
echo "GITHUB_USERNAME=jasonmotylinski" >> .env
```

### Running the Application

```bash
# Fetch data from GitHub and generate exports
python3 -m src.github_fetcher

# Process and export data
python3 -m src.exporter

# Start web server (runs on http://localhost:5000)
python3 -m src.app
```

### Single Tasks

```bash
# Fetch commits from a specific repository only
python3 -m src.github_fetcher --repo "repo-name"

# Export to specific format
python3 -m src.exporter --format json  # or csv

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

### GitHub API Rate Limiting

- GitHub API has rate limits (~5000 requests/hour for authenticated users)
- Caching is critical: always cache API responses in `data/cache/` with timestamps
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

- Cache GitHub API responses with date stamps to allow incremental updates
- Export files should be timestamped: `stats_2026-01-01.json`
- Maintain a manifest of available data files for dashboard consumption

### Web Dashboard Data Flow

1. Frontend requests `/api/daily-stats` endpoint
2. Backend reads cached/exported data from `data/exports/`
3. Returns JSON with daily metrics and optional filtering
4. Frontend renders charts with libraries like Chart.js or D3.js

## Development Notes

- **Environment Variables**: Always use `.env` file; load with `python-dotenv` if needed
- **API Authentication**: Use GitHub token from environment, never hardcode
- **Error Handling**: GitHub API requests can fail; implement retry logic with backoff
- **Data Privacy**: Don't commit API tokens or real user data; gitignore sensitive files
- **Testing**: Mock GitHub API responses in unit tests to avoid hitting rate limits

## External Dependencies

- **PyGithub**: GitHub API client library
- **Flask**: Web framework for backend API
- **pandas**: Data manipulation and export to CSV
- **requests**: HTTP client for API calls

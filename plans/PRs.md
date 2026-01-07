# PRs

## Requirements
- I want to measure the typical amount of time a PR stays open by repository.
- I want to save the raw data from github into the data/cache/github/prs directory
- A process should exist which converts the raw data from Github into a CSV file in the exports/github directory. The CSV file should consist of: repository, pr id, opened datetime, closed datetime, and submitter. 
- I don't actually know what is available from the github API. If there is other relevant data I would love to see it.
- I want a dashboard that allows me to select a repository and see the average PR time opened over time by month.

## Plan

### Overview
Add Pull Request metrics tracking with:
- Fetch and cache PR data from all repositories in configured GitHub organizations
- Calculate metrics: time open, time to first review, reviewer count, PR size
- Dashboard with repository dropdown to view PR metrics by month

### 1. Create PR Fetcher Module
**File**: `src/github/pr_fetcher.py`

- GraphQL API to fetch PRs with review data
- Cache to `data/cache/github/prs/{org}/{repo}_prs.json`
- Fields: number, title, state, createdAt, closedAt, mergedAt, author, additions, deletions, changedFiles, reviews
- CLI: `python3 -m src.github.pr_fetcher` (with `--no-cache` option)

### 2. Create PR Processor Module
**File**: `src/github/pr_processor.py`

- Calculate per-PR metrics: time_open_hours, time_to_first_review_hours, reviewer_count, size
- Aggregate by month with avg/median calculations
- Export CSV to `data/exports/github/prs.csv`
- Columns: repository, pr_number, title, author, state, created_at, closed_at, merged_at, time_open_hours, time_to_first_review_hours, reviewer_count, additions, deletions, changed_files

### 3. Add API Endpoints
**File**: `src/app.py`

| Endpoint | Description |
|----------|-------------|
| `GET /api/pr/repositories` | List all repositories with PR data |
| `GET /api/pr/stats?repo={repo}` | Overall PR statistics for a repository |
| `GET /api/pr/stats/monthly?repo={repo}` | Monthly breakdown of PR metrics |

### 4. Create PR Dashboard
**Files**: `dashboard/prs.html`, `dashboard/prs.js`

- Repository dropdown selector
- Date range filter (month pickers)
- Chart 1: Average PR Time Open by Month (bar + trend line)
- Chart 2: Time to First Review by Month (bar + trend line)
- Summary stats and collapsible data table

### 5. Update Navigation
- Add nav links between main dashboard and PR dashboard

### Files Summary
| File | Action |
|------|--------|
| `src/github/pr_fetcher.py` | Create |
| `src/github/pr_processor.py` | Create |
| `src/app.py` | Add 3 endpoints |
| `dashboard/prs.html` | Create |
| `dashboard/prs.js` | Create |
| `dashboard/index.html` | Add nav link |
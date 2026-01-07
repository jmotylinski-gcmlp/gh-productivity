# JIRA

## Overview
Develop per user statistic on which calculates mean time a JIRA issue is move into IN Progress and then to the next state.

## Requirements
 - Store data down into flat files so the data processing can be done later.
 - Pull data back to 1/1/2023.

## Plan

### 1. Configuration

**Add JIRA settings to `config.json`**
```json
{
  "users": ["user1", "user2"],
  "organizations": ["GCMGrosvenor"],
  "jira": {
    "base_url": "https://your-domain.atlassian.net",
    "project_keys": ["PROJ1", "PROJ2"],
    "user_mappings": {
      "github-username": "jira-account-id"
    }
  }
}
```

**Add to `.env`**
```
JIRA_EMAIL=your-email@domain.com
JIRA_API_TOKEN=your-api-token
```

### 2. JIRA Data Fetcher (`src/jira_fetcher.py`)

Create a new module following the `commit_fetcher.py` pattern:

- **JiraClient class**: Handles authentication and API requests to JIRA REST API
- **JiraFetcher class**: Fetches issue data with changelog (status transitions)
- **Cache storage**: Save raw issue data to `data/cache/jira/{project_key}/issues.json`
- **Date filter**: Only fetch issues updated since 1/1/2023
- **Pagination**: Handle JIRA's paginated API responses (maxResults, startAt)

**Key API endpoint**: `GET /rest/api/3/search` with JQL query and `expand=changelog`

**Data to capture per issue**:
- Issue key, summary, assignee
- Full changelog with timestamps for status transitions
- Filter transitions where `field == "status"` and `toString == "In Progress"`

### 3. JIRA Data Processor (`src/jira_processor.py`)

Create processing module following `data_processor.py` pattern:

**JiraProcessor class** with methods:
- `extract_status_transitions(issue)`: Parse changelog to find "In Progress" → next state transitions
- `calculate_cycle_time(transition)`: Calculate time delta between In Progress and next state
- `process_user_issues(issues, username)`: Aggregate per-user statistics
- `calculate_mean_time(transitions)`: Compute mean cycle time

**Output structure per user**:
```json
{
  "username": "user1",
  "total_issues": 45,
  "mean_cycle_time_hours": 24.5,
  "transitions": [
    {
      "issue_key": "PROJ-123",
      "in_progress_at": "2024-01-15T10:00:00Z",
      "completed_at": "2024-01-16T14:30:00Z",
      "cycle_time_hours": 28.5,
      "next_status": "In Review"
    }
  ]
}
```

### 4. Data Export (`src/jira_exporter.py`)

Export processed data to flat files:

- **JSON export**: `data/exports/{username}/jira_stats_{date}.json`
- **CSV export**: `data/exports/{username}/jira_transitions_{date}.csv`
- Include summary statistics and raw transition data

### 5. API Endpoints (add to `src/app.py`)

New endpoints following existing patterns:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/jira/users/all/stats` | GET | All users' JIRA statistics |
| `/api/jira/stats?user={username}` | GET | Single user's cycle time stats |
| `/api/jira/transitions?user={username}` | GET | Detailed transition history |
| `/api/jira/refresh` | POST | Re-fetch and process JIRA data |

### 6. Cache Builder Integration

Update `src/cache_builder.py` to include JIRA data in the dashboard cache:
- Add `build_jira_cache()` function
- Include JIRA stats in combined dashboard cache file

### 7. Directory Structure (additions)

```
gh-productivity/
├── config/
│   └── users.json              # Add jira config section
├── src/
│   ├── jira_fetcher.py         # NEW: JIRA API integration
│   ├── jira_processor.py       # NEW: Cycle time calculations
│   └── jira_exporter.py        # NEW: Flat file exports
├── data/
│   ├── cache/
│   │   └── jira/
│   │       └── {project_key}/
│   │           └── issues.json # Raw issue data with changelogs
│   └── exports/
│       └── {username}/
│           ├── jira_stats_{date}.json
│           └── jira_transitions_{date}.csv
```

### 8. Implementation Order

1. ~~Add JIRA configuration to `config.json` and `.env`~~ ✓
2. ~~Create `src/jira_fetcher.py` with JiraClient and JiraFetcher classes~~ ✓
3. ~~Create `src/jira_processor.py` with transition extraction and mean time calculation~~ ✓
4. ~~Create `src/jira_exporter.py` for flat file exports~~ (skipped)
5. ~~Add JIRA API endpoints to `src/app.py`~~ ✓
6. Update `src/cache_builder.py` to include JIRA data
7. Add CLI commands for manual JIRA fetch/export
8. ~~(Optional) Add JIRA metrics to dashboard UI~~ ✓

### 9. Dependencies

Add to `requirements.txt`:
```
requests>=2.28.0  # Already present, used for JIRA REST API
```

No additional dependencies required - JIRA REST API uses standard HTTP requests with Basic Auth.
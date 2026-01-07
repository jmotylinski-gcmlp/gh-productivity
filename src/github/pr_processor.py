"""Process and aggregate Pull Request data into statistics"""

import csv
import json
from datetime import datetime
from collections import defaultdict
from statistics import mean, median

from src.config import (
    GITHUB_ORGANIZATIONS,
    GITHUB_PRS_RAW_DIR,
    GITHUB_PRS_CSV,
)

# In-memory cache for CSV data
_pr_cache = None
_pr_cache_mtime = None


def load_all_pr_data() -> dict:
    """
    Load all PRs from cache files.

    Returns:
        Dictionary mapping org/repo -> list of PRs
    """
    all_prs = {}

    for org_name in GITHUB_ORGANIZATIONS:
        org_dir = GITHUB_PRS_RAW_DIR / org_name
        if not org_dir.exists():
            continue

        for cache_file in org_dir.glob("*_prs.json"):
            repo_name = cache_file.stem.replace("_prs", "")
            full_repo_name = f"{org_name}/{repo_name}"
            with open(cache_file) as f:
                all_prs[full_repo_name] = json.load(f)

    return all_prs


def calculate_pr_metrics(pr: dict) -> dict:
    """
    Calculate metrics for a single PR.

    Args:
        pr: PR dictionary from cache

    Returns:
        PR with calculated metrics added
    """
    result = pr.copy()

    # Calculate time open (in hours)
    created_at = pr.get("created_at")
    closed_at = pr.get("closed_at")
    merged_at = pr.get("merged_at")

    time_open_hours = None
    if created_at:
        created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

        # Use merged_at if available, otherwise closed_at, otherwise now
        end_dt = None
        if merged_at:
            end_dt = datetime.fromisoformat(merged_at.replace("Z", "+00:00"))
        elif closed_at:
            end_dt = datetime.fromisoformat(closed_at.replace("Z", "+00:00"))
        else:
            end_dt = datetime.now(created_dt.tzinfo)

        time_open_hours = (end_dt - created_dt).total_seconds() / 3600

    result["time_open_hours"] = time_open_hours

    # Calculate time to first review (in hours)
    reviews = pr.get("reviews", [])
    time_to_first_review_hours = None
    if reviews and created_at:
        # Sort reviews by submitted_at to find the first one
        valid_reviews = [r for r in reviews if r.get("submitted_at")]
        if valid_reviews:
            valid_reviews.sort(key=lambda r: r["submitted_at"])
            first_review = valid_reviews[0]
            first_review_dt = datetime.fromisoformat(
                first_review["submitted_at"].replace("Z", "+00:00")
            )
            created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            time_to_first_review_hours = (first_review_dt - created_dt).total_seconds() / 3600

    result["time_to_first_review_hours"] = time_to_first_review_hours

    # Count unique reviewers
    reviewer_count = len(set(r.get("author", "unknown") for r in reviews if r.get("author")))
    result["reviewer_count"] = reviewer_count

    # Calculate size
    additions = pr.get("additions", 0)
    deletions = pr.get("deletions", 0)
    result["size"] = additions + deletions

    return result


def aggregate_prs_by_month(prs: list) -> dict:
    """
    Aggregate PRs by month.

    Args:
        prs: List of PR dictionaries with calculated metrics

    Returns:
        Dictionary mapping month (YYYY-MM) to aggregated stats
    """
    monthly_data = defaultdict(list)

    for pr in prs:
        created_at = pr.get("created_at")
        if not created_at:
            continue

        # Extract month from created_at
        month = created_at[:7]  # YYYY-MM
        monthly_data[month].append(pr)

    # Calculate aggregations for each month
    result = {}
    for month, month_prs in sorted(monthly_data.items()):
        time_open_values = [p["time_open_hours"] for p in month_prs if p.get("time_open_hours") is not None]
        time_to_review_values = [p["time_to_first_review_hours"] for p in month_prs if p.get("time_to_first_review_hours") is not None]
        reviewer_counts = [p["reviewer_count"] for p in month_prs]
        additions = [p.get("additions", 0) for p in month_prs]
        deletions = [p.get("deletions", 0) for p in month_prs]

        result[month] = {
            "month": month,
            "pr_count": len(month_prs),
            "avg_time_open_hours": mean(time_open_values) if time_open_values else None,
            "median_time_open_hours": median(time_open_values) if time_open_values else None,
            "avg_time_to_first_review_hours": mean(time_to_review_values) if time_to_review_values else None,
            "avg_reviewer_count": mean(reviewer_counts) if reviewer_counts else 0,
            "avg_additions": mean(additions) if additions else 0,
            "avg_deletions": mean(deletions) if deletions else 0
        }

    return result


def get_all_repositories() -> list:
    """Get list of all repositories with PR data (from CSV export)"""
    prs = load_pr_export()
    repos = set(pr["repository"] for pr in prs)
    return sorted(repos)


def get_repository_prs(repository: str) -> list:
    """Get all PRs for a specific repository (from CSV export, metrics pre-calculated)"""
    prs = load_pr_export()
    return [pr for pr in prs if pr["repository"] == repository]


def get_repository_monthly_stats(repository: str) -> dict:
    """Get monthly aggregated stats for a repository (from CSV export)"""
    prs = get_repository_prs(repository)
    return {
        "repository": repository,
        "months": list(aggregate_prs_by_month(prs).values())
    }


def get_repository_summary(repository: str) -> dict:
    """Get overall summary stats for a repository (from CSV export)"""
    prs = get_repository_prs(repository)

    if not prs:
        return {
            "repository": repository,
            "total_prs": 0
        }

    # Filter for closed/merged PRs for time calculations
    closed_prs = [p for p in prs if p.get("state") in ("CLOSED", "MERGED")]

    time_open_values = [p["time_open_hours"] for p in closed_prs if p.get("time_open_hours") is not None]
    time_to_review_values = [p["time_to_first_review_hours"] for p in closed_prs if p.get("time_to_first_review_hours") is not None]

    return {
        "repository": repository,
        "total_prs": len(prs),
        "open_prs": len([p for p in prs if p.get("state") == "OPEN"]),
        "merged_prs": len([p for p in prs if p.get("state") == "MERGED"]),
        "closed_prs": len([p for p in prs if p.get("state") == "CLOSED"]),
        "avg_time_open_hours": mean(time_open_values) if time_open_values else None,
        "median_time_open_hours": median(time_open_values) if time_open_values else None,
        "avg_time_to_first_review_hours": mean(time_to_review_values) if time_to_review_values else None
    }


def build_pr_export() -> None:
    """
    Build CSV export of all PR data with calculated metrics.
    """
    print("Building PR export...")

    all_prs = load_all_pr_data()

    csv_rows = []
    for repository, prs in all_prs.items():
        for pr in prs:
            pr_with_metrics = calculate_pr_metrics(pr)
            csv_rows.append({
                "repository": repository,
                "pr_number": pr_with_metrics.get("number"),
                "title": pr_with_metrics.get("title", "")[:200],  # Truncate long titles
                "author": pr_with_metrics.get("author"),
                "state": pr_with_metrics.get("state"),
                "created_at": pr_with_metrics.get("created_at"),
                "closed_at": pr_with_metrics.get("closed_at"),
                "merged_at": pr_with_metrics.get("merged_at"),
                "time_open_hours": pr_with_metrics.get("time_open_hours"),
                "time_to_first_review_hours": pr_with_metrics.get("time_to_first_review_hours"),
                "reviewer_count": pr_with_metrics.get("reviewer_count"),
                "additions": pr_with_metrics.get("additions"),
                "deletions": pr_with_metrics.get("deletions"),
                "changed_files": pr_with_metrics.get("changed_files")
            })

    # Write CSV file
    GITHUB_PRS_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(GITHUB_PRS_CSV, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            "repository", "pr_number", "title", "author", "state",
            "created_at", "closed_at", "merged_at",
            "time_open_hours", "time_to_first_review_hours", "reviewer_count",
            "additions", "deletions", "changed_files"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"PR data written to {GITHUB_PRS_CSV} ({len(csv_rows)} rows)")


def load_pr_export() -> list:
    """
    Load PR data from CSV export with caching.

    Returns:
        List of PR dictionaries, or empty list if not found
    """
    global _pr_cache, _pr_cache_mtime

    if not GITHUB_PRS_CSV.exists():
        return []

    # Check if cache is still valid
    current_mtime = GITHUB_PRS_CSV.stat().st_mtime
    if _pr_cache is not None and _pr_cache_mtime == current_mtime:
        return _pr_cache

    prs = []
    with open(GITHUB_PRS_CSV, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert numeric fields
            pr = {
                "repository": row["repository"],
                "pr_number": int(row["pr_number"]) if row["pr_number"] else None,
                "title": row["title"],
                "author": row["author"],
                "state": row["state"],
                "created_at": row["created_at"],
                "closed_at": row["closed_at"] if row["closed_at"] else None,
                "merged_at": row["merged_at"] if row["merged_at"] else None,
                "time_open_hours": float(row["time_open_hours"]) if row["time_open_hours"] else None,
                "time_to_first_review_hours": float(row["time_to_first_review_hours"]) if row["time_to_first_review_hours"] else None,
                "reviewer_count": int(row["reviewer_count"]) if row["reviewer_count"] else 0,
                "additions": int(row["additions"]) if row["additions"] else 0,
                "deletions": int(row["deletions"]) if row["deletions"] else 0,
                "changed_files": int(row["changed_files"]) if row["changed_files"] else 0
            }
            prs.append(pr)

    # Update cache
    _pr_cache = prs
    _pr_cache_mtime = current_mtime

    return prs


if __name__ == "__main__":
    build_pr_export()

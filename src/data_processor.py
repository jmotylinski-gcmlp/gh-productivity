"""Process and aggregate commit data into daily statistics"""

from datetime import datetime
from collections import defaultdict
from pathlib import Path
import json


class DataProcessor:
    """Aggregates commit data into daily statistics"""

    def __init__(self):
        self.cache_dir = Path("data/cache")

    def process_commits(self, commits: list) -> dict:
        """
        Aggregate commits into daily statistics

        Args:
            commits: List of commit dictionaries from github_fetcher

        Returns:
            Dictionary with daily statistics
        """
        daily_stats = defaultdict(lambda: {
            "additions": 0,
            "deletions": 0,
            "net_lines": 0,
            "commits": 0,
            "repositories": set()
        })

        for commit in commits:
            date_str = commit["date"].split("T")[0]  # Extract YYYY-MM-DD

            daily_stats[date_str]["additions"] += commit["additions"]
            daily_stats[date_str]["deletions"] += commit["deletions"]
            daily_stats[date_str]["commits"] += 1
            daily_stats[date_str]["repositories"].add(commit["repository"])

        # Calculate net lines and convert sets to lists
        for date_str in daily_stats:
            daily_stats[date_str]["net_lines"] = (
                daily_stats[date_str]["additions"] - daily_stats[date_str]["deletions"]
            )
            daily_stats[date_str]["repositories"] = list(daily_stats[date_str]["repositories"])

        return dict(sorted(daily_stats.items()))

    def calculate_summary(self, daily_stats: dict) -> dict:
        """Calculate summary statistics across all days"""
        if not daily_stats:
            return {}

        total_additions = sum(s["additions"] for s in daily_stats.values())
        total_deletions = sum(s["deletions"] for s in daily_stats.values())
        total_commits = sum(s["commits"] for s in daily_stats.values())
        total_days = len(daily_stats)

        return {
            "total_additions": total_additions,
            "total_deletions": total_deletions,
            "net_lines": total_additions - total_deletions,
            "total_commits": total_commits,
            "total_days": total_days,
            "avg_daily_lines": (total_additions - total_deletions) / total_days if total_days > 0 else 0,
            "avg_commits_per_day": total_commits / total_days if total_days > 0 else 0
        }

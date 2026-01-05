"""Export processed data to JSON and CSV formats"""

import json
import csv
from datetime import datetime
from pathlib import Path
import argparse
import os
from dotenv import load_dotenv

load_dotenv()

from src.github_fetcher import GitHubFetcher, fetch_all_users, load_users_config
from src.data_processor import DataProcessor


class DataExporter:
    """Exports daily statistics to JSON and CSV files"""

    def __init__(self, output_dir: str = "data/exports", username: str = None):
        self.base_output_dir = Path(output_dir)
        if username:
            self.output_dir = self.base_output_dir / username
        else:
            self.output_dir = self.base_output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.username = username

    def export_json(self, daily_stats: dict, summary: dict) -> str:
        """
        Export data to JSON format

        Args:
            daily_stats: Dictionary of daily statistics
            summary: Summary statistics dictionary

        Returns:
            Path to exported file
        """
        timestamp = datetime.now().strftime("%Y-%m-%d")
        filename = self.output_dir / f"stats_{timestamp}.json"

        data = {
            "exported_at": datetime.now().isoformat(),
            "username": self.username,
            "summary": summary,
            "daily_stats": daily_stats
        }

        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"Exported JSON to {filename}")
        return str(filename)

    def export_csv(self, daily_stats: dict) -> str:
        """
        Export daily stats to CSV format

        Args:
            daily_stats: Dictionary of daily statistics

        Returns:
            Path to exported file
        """
        timestamp = datetime.now().strftime("%Y-%m-%d")
        filename = self.output_dir / f"stats_{timestamp}.csv"

        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Date", "Username", "Commits", "Additions", "Deletions",
                "Net Lines", "Repositories"
            ])

            for date_str, stats in daily_stats.items():
                writer.writerow([
                    date_str,
                    self.username or "",
                    stats["commits"],
                    stats["additions"],
                    stats["deletions"],
                    stats["net_lines"],
                    ";".join(stats["repositories"])
                ])

        print(f"Exported CSV to {filename}")
        return str(filename)


def export_all_users(format: str = "both") -> dict:
    """
    Export data for all configured users

    Args:
        format: Export format ('json', 'csv', or 'both')

    Returns:
        Dictionary mapping username to list of exported file paths
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable not set")

    users = load_users_config()
    processor = DataProcessor()
    exported_files = {}

    for username in users:
        print(f"\nExporting data for {username}...")
        fetcher = GitHubFetcher(token, username)
        commits = fetcher.fetch_all_commits(use_cache=True)

        daily_stats = processor.process_commits(commits, username)
        summary = processor.calculate_summary(daily_stats, username)

        exporter = DataExporter(username=username)
        exported_files[username] = []

        if format in ["json", "both"]:
            json_file = exporter.export_json(daily_stats, summary)
            exported_files[username].append(json_file)
        if format in ["csv", "both"]:
            csv_file = exporter.export_csv(daily_stats)
            exported_files[username].append(csv_file)

    return exported_files


def main():
    parser = argparse.ArgumentParser(description="Export GitHub stats")
    parser.add_argument("--format", choices=["json", "csv", "both"], default="both",
                        help="Export format")
    parser.add_argument("--user", help="Specific user to export (optional, defaults to all users)")
    args = parser.parse_args()

    token = os.getenv("GITHUB_TOKEN")

    if not token:
        raise ValueError("GITHUB_TOKEN environment variable not set")

    if args.user:
        # Export for specific user
        fetcher = GitHubFetcher(token, args.user)
        commits = fetcher.fetch_all_commits(use_cache=True)

        processor = DataProcessor()
        daily_stats = processor.process_commits(commits, args.user)
        summary = processor.calculate_summary(daily_stats, args.user)

        exporter = DataExporter(username=args.user)
        if args.format in ["json", "both"]:
            exporter.export_json(daily_stats, summary)
        if args.format in ["csv", "both"]:
            exporter.export_csv(daily_stats)
    else:
        # Export for all configured users
        exported = export_all_users(args.format)
        print(f"\nExported data for {len(exported)} users")


if __name__ == "__main__":
    main()

"""Export processed data to JSON and CSV formats"""

import json
import csv
from datetime import datetime
from pathlib import Path
import argparse
import os
from dotenv import load_dotenv

load_dotenv()

from src.github_fetcher import GitHubFetcher
from src.data_processor import DataProcessor


class DataExporter:
    """Exports daily statistics to JSON and CSV files"""

    def __init__(self, output_dir: str = "data/exports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

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
                "Date", "Commits", "Additions", "Deletions",
                "Net Lines", "Repositories"
            ])

            for date_str, stats in daily_stats.items():
                writer.writerow([
                    date_str,
                    stats["commits"],
                    stats["additions"],
                    stats["deletions"],
                    stats["net_lines"],
                    ";".join(stats["repositories"])
                ])

        print(f"Exported CSV to {filename}")
        return str(filename)


def main():
    parser = argparse.ArgumentParser(description="Export GitHub stats")
    parser.add_argument("--format", choices=["json", "csv", "both"], default="both",
                        help="Export format")
    args = parser.parse_args()

    token = os.getenv("GITHUB_TOKEN")
    username = os.getenv("GITHUB_USERNAME", "jasonmotylinski")

    if not token:
        raise ValueError("GITHUB_TOKEN environment variable not set")

    # Fetch and process data
    fetcher = GitHubFetcher(token, username)
    commits = fetcher.fetch_all_commits(use_cache=True)

    processor = DataProcessor()
    daily_stats = processor.process_commits(commits)
    summary = processor.calculate_summary(daily_stats)

    # Export
    exporter = DataExporter()
    if args.format in ["json", "both"]:
        exporter.export_json(daily_stats, summary)
    if args.format in ["csv", "both"]:
        exporter.export_csv(daily_stats)


if __name__ == "__main__":
    main()

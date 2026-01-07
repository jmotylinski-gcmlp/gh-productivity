"""Process JIRA issue data to extract In Progress cycle times"""

import csv
import json
import argparse
from pathlib import Path

from src.config import JIRA_RAW_DIR, JIRA_EXPORTS_DIR, JIRA_USER_ISSUES_CSV


def extract_in_progress_cycles(issue: dict) -> list:
    """
    Extract all In Progress -> next state cycles from an issue

    Args:
        issue: Issue dictionary with status_transitions

    Returns:
        List of tuples: (key, assignee_email, in_progress_timestamp, out_of_progress_timestamp)
    """
    transitions = issue.get("status_transitions", [])
    if not transitions:
        return []

    # Sort transitions by timestamp
    sorted_transitions = sorted(transitions, key=lambda t: t.get("timestamp", ""))

    # Get assignee email
    assignee = issue.get("assignee")
    assignee_email = assignee.get("email") if assignee else None

    cycles = []
    in_progress_start = None

    for transition in sorted_transitions:
        to_status = transition.get("to_status", "")
        timestamp = transition.get("timestamp")

        if to_status == "In Progress":
            in_progress_start = timestamp
        elif in_progress_start and to_status != "In Progress":
            cycles.append((
                issue.get("key"),
                assignee_email,
                in_progress_start,
                timestamp
            ))
            in_progress_start = None

    return cycles


def process_issues_to_csv(all_issues: dict, output_file: Path = None) -> Path:
    """
    Process all issues and write cycles to CSV

    Args:
        all_issues: Dictionary mapping project_key to list of issues
        output_file: Optional output path (defaults to data/exports/jira/user_issues.csv)

    Returns:
        Path to the output CSV file
    """
    if output_file is None:
        JIRA_EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        output_file = JIRA_USER_ISSUES_CSV

    all_cycles = []

    for project_key, issues in all_issues.items():
        for issue in issues:
            cycles = extract_in_progress_cycles(issue)
            all_cycles.extend(cycles)

    # Write to CSV
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["key", "assignee_email", "in_progress_at", "out_of_progress_at"])
        writer.writerows(all_cycles)

    print(f"Wrote {len(all_cycles)} cycles to {output_file}")
    return output_file


def load_cached_issues() -> dict:
    """
    Load all cached JIRA issues from disk

    Returns:
        Dictionary mapping project_key to list of issues
    """
    all_issues = {}

    if not JIRA_RAW_DIR.exists():
        return all_issues

    for project_dir in JIRA_RAW_DIR.iterdir():
        if project_dir.is_dir():
            issues_file = project_dir / "issues.json"
            if issues_file.exists():
                with open(issues_file) as f:
                    all_issues[project_dir.name] = json.load(f)

    return all_issues


def main():
    parser = argparse.ArgumentParser(description="Process JIRA issues to CSV")
    parser.add_argument("--output", "-o", help="Output CSV file path")
    args = parser.parse_args()

    print("Loading cached JIRA issues...")
    all_issues = load_cached_issues()

    if not all_issues:
        print("No cached JIRA data found. Run jira_fetcher first.")
        return

    total_issues = sum(len(issues) for issues in all_issues.values())
    print(f"Loaded {total_issues} issues from {len(all_issues)} projects")

    output_file = Path(args.output) if args.output else None
    process_issues_to_csv(all_issues, output_file)


if __name__ == "__main__":
    main()

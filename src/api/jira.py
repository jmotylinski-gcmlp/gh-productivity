"""JIRA API endpoints"""

import csv
from datetime import datetime
from flask import Blueprint, jsonify, request

from src.config import JIRA_USER_ISSUES_CSV

jira_bp = Blueprint('jira', __name__, url_prefix='/api/jira')


def get_jira_cycles() -> list:
    """Load all JIRA cycles from CSV export file"""
    all_cycles = []

    if not JIRA_USER_ISSUES_CSV.exists():
        return all_cycles

    with open(JIRA_USER_ISSUES_CSV, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            all_cycles.append({
                "key": row.get("key"),
                "assignee_email": row.get("assignee_email"),
                "in_progress_at": row.get("in_progress_at"),
                "out_of_progress_at": row.get("out_of_progress_at")
            })

    return all_cycles


def calculate_cycle_hours(in_progress_at: str, out_of_progress_at: str) -> float:
    """Calculate cycle time in hours between two timestamps"""
    try:
        # Parse ISO timestamps
        formats = [
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
        ]

        start = end = None
        for fmt in formats:
            try:
                start = datetime.strptime(in_progress_at, fmt)
                break
            except ValueError:
                continue

        for fmt in formats:
            try:
                end = datetime.strptime(out_of_progress_at, fmt)
                break
            except ValueError:
                continue

        if start and end:
            # Remove timezone info for calculation if present
            if start.tzinfo:
                start = start.replace(tzinfo=None)
            if end.tzinfo:
                end = end.replace(tzinfo=None)
            delta = end - start
            return round(delta.total_seconds() / 3600, 2)
    except Exception:
        pass
    return 0.0


@jira_bp.route("/cycles")
def get_jira_cycles_api():
    """Get all JIRA In Progress cycles"""
    email = request.args.get("email")

    try:
        cycles = get_jira_cycles()

        if email:
            cycles = [c for c in cycles if c["assignee_email"] == email]

        return jsonify(cycles)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@jira_bp.route("/stats")
def get_jira_stats():
    """Get JIRA cycle time statistics, optionally filtered by email"""
    email = request.args.get("email")

    try:
        cycles = get_jira_cycles()

        if email:
            cycles = [c for c in cycles if c["assignee_email"] == email]

        # Calculate cycle times
        cycle_times = []
        for c in cycles:
            hours = calculate_cycle_hours(c["in_progress_at"], c["out_of_progress_at"])
            if hours > 0:
                cycle_times.append(hours)

        if not cycle_times:
            return jsonify({
                "total_cycles": 0,
                "mean_hours": 0,
                "median_hours": 0,
                "min_hours": 0,
                "max_hours": 0
            })

        sorted_times = sorted(cycle_times)
        n = len(sorted_times)
        median = sorted_times[n // 2] if n % 2 == 1 else (sorted_times[n // 2 - 1] + sorted_times[n // 2]) / 2

        return jsonify({
            "total_cycles": len(cycle_times),
            "mean_hours": round(sum(cycle_times) / len(cycle_times), 2),
            "median_hours": round(median, 2),
            "min_hours": round(min(cycle_times), 2),
            "max_hours": round(max(cycle_times), 2)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@jira_bp.route("/stats/by-user")
def get_jira_stats_by_user():
    """Get JIRA cycle time statistics grouped by user"""
    try:
        cycles = get_jira_cycles()

        # Group by email
        by_user = {}
        for c in cycles:
            email = c["assignee_email"] or "unassigned"
            if email not in by_user:
                by_user[email] = []
            hours = calculate_cycle_hours(c["in_progress_at"], c["out_of_progress_at"])
            if hours > 0:
                by_user[email].append(hours)

        # Calculate stats per user
        results = {}
        for email, times in by_user.items():
            if not times:
                continue
            sorted_times = sorted(times)
            n = len(sorted_times)
            median = sorted_times[n // 2] if n % 2 == 1 else (sorted_times[n // 2 - 1] + sorted_times[n // 2]) / 2

            results[email] = {
                "total_cycles": len(times),
                "mean_hours": round(sum(times) / len(times), 2),
                "median_hours": round(median, 2),
                "min_hours": round(min(times), 2),
                "max_hours": round(max(times), 2)
            }

        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@jira_bp.route("/stats/monthly")
def get_jira_stats_monthly():
    """Get JIRA cycle time statistics by month for a specific user"""
    email = request.args.get("email")

    try:
        cycles = get_jira_cycles()

        if email:
            cycles = [c for c in cycles if c["assignee_email"] == email]

        # Group by month (using out_of_progress_at as the completion date)
        by_month = {}
        for c in cycles:
            hours = calculate_cycle_hours(c["in_progress_at"], c["out_of_progress_at"])
            if hours <= 0:
                continue

            # Extract month from out_of_progress_at timestamp
            timestamp = c["out_of_progress_at"]
            if timestamp:
                month = timestamp[:7]  # YYYY-MM
                if month not in by_month:
                    by_month[month] = []
                by_month[month].append(hours)

        # Calculate stats per month
        results = {}
        for month, times in sorted(by_month.items()):
            if not times:
                continue
            sorted_times = sorted(times)
            n = len(sorted_times)
            median = sorted_times[n // 2] if n % 2 == 1 else (sorted_times[n // 2 - 1] + sorted_times[n // 2]) / 2

            results[month] = {
                "cycles": len(times),
                "mean_hours": round(sum(times) / len(times), 2),
                "median_hours": round(median, 2),
                "min_hours": round(min(times), 2),
                "max_hours": round(max(times), 2)
            }

        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

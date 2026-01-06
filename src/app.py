"""Flask web backend for productivity dashboard"""

import json
import os
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from src.github.github_fetcher import load_users_config
from src.github.github_processor import load_dashboard_cache, build_dashboard_cache
from src.jira.jira_processor import load_cached_issues, extract_in_progress_cycles

# Get absolute paths relative to this file's location
BASE_DIR = Path(__file__).parent.parent
DASHBOARD_DIR = BASE_DIR / "dashboard"

# Ensure data directories exist (required for Azure deployment)
(BASE_DIR / "data" / "cache").mkdir(parents=True, exist_ok=True)
(BASE_DIR / "data" / "exports").mkdir(parents=True, exist_ok=True)

app = Flask(__name__, static_folder=str(DASHBOARD_DIR), static_url_path="")

# In-memory cache (loaded from pre-processed file)
_dashboard_data = None
_loaded_at = None


def get_dashboard_data(force_refresh: bool = False) -> dict:
    """
    Load dashboard data from pre-processed cache file.
    Much faster than reading individual repo cache files.
    """
    global _dashboard_data, _loaded_at

    if _dashboard_data and not force_refresh:
        return _dashboard_data

    # Try to load from pre-processed cache
    cache_data = load_dashboard_cache()

    if cache_data:
        _dashboard_data = cache_data
        _loaded_at = datetime.now().isoformat()
        return _dashboard_data

    # Cache doesn't exist - build it
    print("Dashboard cache not found, building...")
    _dashboard_data = build_dashboard_cache()
    _loaded_at = datetime.now().isoformat()
    return _dashboard_data


def get_all_users_data() -> dict:
    """Get all users' data formatted for API response"""
    data = get_dashboard_data()
    users_data = data.get("users", {})

    result = {}
    for username, user_data in users_data.items():
        result[username] = {
            "daily_stats": user_data.get("daily_stats", {}),
            "summary": user_data.get("summary", {}),
            "updated_at": data.get("generated_at")
        }

    return result


@app.route("/api/users")
def get_users():
    """Get list of configured users"""
    users = load_users_config()
    return jsonify(users)


@app.route("/api/users/all/stats")
def get_all_users_stats():
    """Get stats for all configured users"""
    try:
        all_data = get_all_users_data()
        return jsonify(all_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/daily-stats")
def get_daily_stats():
    """Get daily statistics for a specific user"""
    username = request.args.get("user")

    try:
        all_data = get_all_users_data()

        if not username:
            return jsonify({u: d["daily_stats"] for u, d in all_data.items()})

        if username in all_data:
            return jsonify(all_data[username]["daily_stats"])
        else:
            return jsonify({"error": f"User {username} not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/summary")
def get_summary():
    """Get summary statistics for a specific user"""
    username = request.args.get("user")

    try:
        all_data = get_all_users_data()

        if not username:
            return jsonify({u: {"summary": d["summary"], "updated_at": d.get("updated_at")} for u, d in all_data.items()})

        if username in all_data:
            return jsonify({
                "summary": all_data[username]["summary"],
                "updated_at": all_data[username].get("updated_at")
            })
        else:
            return jsonify({"error": f"User {username} not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/timeline")
def get_timeline():
    """Get timeline data for a specific user"""
    username = request.args.get("user")

    try:
        all_data = get_all_users_data()

        if not username:
            users = list(all_data.keys())
            if users:
                username = users[0]
            else:
                return jsonify({"error": "No users configured"}), 400

        if username not in all_data:
            return jsonify({"error": f"User {username} not found"}), 404

        daily_stats = all_data[username]["daily_stats"]
        summary = all_data[username]["summary"]

        # Convert to timeline format
        timeline = []
        for date_str, stats in daily_stats.items():
            timeline.append({
                "date": date_str,
                **stats
            })

        return jsonify({
            "timeline": timeline,
            "summary": summary,
            "username": username
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/refresh", methods=["POST"])
def refresh_data():
    """Rebuild the dashboard cache"""
    global _dashboard_data, _loaded_at

    try:
        # Rebuild the dashboard cache from raw data
        _dashboard_data = build_dashboard_cache()
        _loaded_at = datetime.now().isoformat()

        all_data = get_all_users_data()
        return jsonify({
            "success": True,
            "users": list(all_data.keys()),
            "generated_at": _dashboard_data.get("generated_at")
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/cache-info")
def cache_info():
    """Get information about the dashboard cache"""
    data = get_dashboard_data()
    return jsonify({
        "generated_at": data.get("generated_at"),
        "loaded_at": _loaded_at,
        "users": list(data.get("users", {}).keys())
    })


@app.route("/")
def index():
    """Serve dashboard HTML"""
    try:
        with open(DASHBOARD_DIR / "index.html", 'r') as f:
            return f.read()
    except Exception as e:
        return jsonify({"error": f"Failed to load dashboard: {str(e)}"}), 500


# ============ JIRA API Endpoints ============

def get_jira_cycles() -> list:
    """Load all JIRA cycles from cached issues"""
    all_issues = load_cached_issues()
    all_cycles = []

    for project_key, issues in all_issues.items():
        for issue in issues:
            cycles = extract_in_progress_cycles(issue)
            for cycle in cycles:
                all_cycles.append({
                    "key": cycle[0],
                    "assignee_email": cycle[1],
                    "in_progress_at": cycle[2],
                    "out_of_progress_at": cycle[3]
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


@app.route("/api/jira/cycles")
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


@app.route("/api/jira/stats")
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


@app.route("/api/jira/stats/by-user")
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


@app.route("/api/jira/stats/monthly")
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


if __name__ == "__main__":
    app.run(debug=True, port=5000)

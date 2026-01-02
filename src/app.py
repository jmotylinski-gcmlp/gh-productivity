"""Flask web backend for productivity dashboard"""

import json
import os
from pathlib import Path
from flask import Flask, jsonify, send_from_directory, render_template_string
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

from src.github_fetcher import GitHubFetcher
from src.data_processor import DataProcessor

# Get absolute paths relative to this file's location
BASE_DIR = Path(__file__).parent.parent
DASHBOARD_DIR = BASE_DIR / "dashboard"

app = Flask(__name__, static_folder=str(DASHBOARD_DIR), static_url_path="")

# Cache processed data
_cache = {"daily_stats": None, "summary": None, "updated_at": None}


def load_data(force_refresh: bool = False):
    """Load commit data from cache or GitHub"""
    global _cache

    if _cache["daily_stats"] and not force_refresh:
        return _cache["daily_stats"], _cache["summary"]

    token = os.getenv("GITHUB_TOKEN")
    username = os.getenv("GITHUB_USERNAME", "jasonmotylinski")

    if not token:
        raise ValueError("GITHUB_TOKEN not configured")

    fetcher = GitHubFetcher(token, username)
    commits = fetcher.fetch_all_commits(use_cache=True)

    processor = DataProcessor()
    daily_stats = processor.process_commits(commits)
    summary = processor.calculate_summary(daily_stats)

    _cache["daily_stats"] = daily_stats
    _cache["summary"] = summary
    _cache["updated_at"] = datetime.now().isoformat()

    return daily_stats, summary


@app.route("/api/daily-stats")
def get_daily_stats():
    """Get daily statistics"""
    try:
        daily_stats, _ = load_data()
        return jsonify(daily_stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/summary")
def get_summary():
    """Get summary statistics"""
    try:
        _, summary = load_data()
        return jsonify({
            "summary": summary,
            "updated_at": _cache["updated_at"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/timeline")
def get_timeline():
    """Get timeline data with optional date range filtering"""
    try:
        daily_stats, summary = load_data()

        # Convert to timeline format
        timeline = []
        for date_str, stats in daily_stats.items():
            timeline.append({
                "date": date_str,
                **stats
            })

        return jsonify({
            "timeline": timeline,
            "summary": summary
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/refresh", methods=["POST"])
def refresh_data():
    """Manually trigger data refresh from GitHub"""
    try:
        daily_stats, summary = load_data(force_refresh=True)
        return jsonify({
            "success": True,
            "summary": summary,
            "updated_at": _cache["updated_at"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/")
def index():
    """Serve dashboard HTML"""
    try:
        with open(DASHBOARD_DIR / "index.html", 'r') as f:
            return f.read()
    except Exception as e:
        return jsonify({"error": f"Failed to load dashboard: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)

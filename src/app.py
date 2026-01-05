"""Flask web backend for productivity dashboard"""

import json
import os
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from src.github_fetcher import load_users_config
from src.cache_builder import load_dashboard_cache, build_dashboard_cache

# Get absolute paths relative to this file's location
BASE_DIR = Path(__file__).parent.parent
DASHBOARD_DIR = BASE_DIR / "dashboard"

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


if __name__ == "__main__":
    app.run(debug=True, port=5000)

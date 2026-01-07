"""GitHub API endpoints"""

from datetime import datetime
from flask import Blueprint, jsonify, request

from src.user_mapping import get_user_mappings
from src.github.commit_processor import load_dashboard_cache, build_dashboard_cache

github_bp = Blueprint('github', __name__, url_prefix='/api')

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


@github_bp.route("/users")
def get_users():
    """Get list of users from commit data"""
    data = get_dashboard_data()
    users = list(data.get("users", {}).keys())
    return jsonify(users)


@github_bp.route("/user-mappings")
def get_user_mappings_api():
    """Get GitHub to JIRA user mappings"""
    return jsonify(get_user_mappings())


@github_bp.route("/users/all/stats")
def get_all_users_stats():
    """Get stats for all configured users"""
    try:
        all_data = get_all_users_data()
        return jsonify(all_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@github_bp.route("/daily-stats")
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


@github_bp.route("/summary")
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


@github_bp.route("/timeline")
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


@github_bp.route("/refresh", methods=["POST"])
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


@github_bp.route("/cache-info")
def cache_info():
    """Get information about the dashboard cache"""
    data = get_dashboard_data()
    return jsonify({
        "generated_at": data.get("generated_at"),
        "loaded_at": _loaded_at,
        "users": list(data.get("users", {}).keys())
    })

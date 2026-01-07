"""Admin API endpoints for scheduled tasks"""

import os
import subprocess
import sys
from datetime import datetime
from functools import wraps
from flask import Blueprint, jsonify, request

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


def require_api_key(f):
    """Decorator to require API key for protected endpoints."""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = os.environ.get("ADMIN_API_KEY")
        if not api_key:
            # No key configured = endpoint disabled
            return jsonify({"error": "Endpoint not configured"}), 503

        provided_key = request.headers.get("X-API-Key") or request.args.get("api_key")
        if provided_key != api_key:
            return jsonify({"error": "Unauthorized"}), 401

        return f(*args, **kwargs)
    return decorated


def run_module(module: str) -> dict:
    """Run a Python module and return result."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", module],
            capture_output=True,
            text=True,
            timeout=1800  # 30 minute timeout
        )
        return {
            "module": module,
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout[-2000:] if result.stdout else None,  # Last 2000 chars
            "stderr": result.stderr[-2000:] if result.stderr else None,
        }
    except subprocess.TimeoutExpired:
        return {"module": module, "success": False, "error": "Timeout"}
    except Exception as e:
        return {"module": module, "success": False, "error": str(e)}


@admin_bp.route("/fetch", methods=["POST"])
@require_api_key
def fetch_all_data():
    """
    Fetch fresh data from GitHub and JIRA.

    Runs all fetcher and processor modules in sequence.
    Protected by API key (set ADMIN_API_KEY environment variable).

    Usage:
        curl -X POST https://gh-productivity.azurewebsites.net/api/admin/fetch \
             -H "X-API-Key: your-secret-key"
    """
    started_at = datetime.utcnow().isoformat()

    modules = [
        "src.github.commit_fetcher",
        "src.github.pr_fetcher",
        "src.github.pr_processor",
        "src.jira.jira_fetcher",
        "src.jira.jira_processor",
        "src.user_mapping.user_mapping_processor",
    ]

    results = []
    for module in modules:
        result = run_module(module)
        results.append(result)
        # Stop on failure to avoid cascading errors
        if not result["success"]:
            break

    completed_at = datetime.utcnow().isoformat()
    all_success = all(r["success"] for r in results)

    return jsonify({
        "success": all_success,
        "started_at": started_at,
        "completed_at": completed_at,
        "results": results
    }), 200 if all_success else 500


@admin_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint (no auth required)."""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "fetch_endpoint_configured": bool(os.environ.get("ADMIN_API_KEY"))
    })

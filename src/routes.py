"""Website routes for serving the dashboard"""

from pathlib import Path
from flask import Blueprint, jsonify

website_bp = Blueprint('website', __name__)

# Get absolute paths
BASE_DIR = Path(__file__).parent.parent
DASHBOARD_DIR = BASE_DIR / "dashboard"


def serve_html(filepath: Path):
    """Helper to serve an HTML file"""
    try:
        with open(filepath, 'r') as f:
            return f.read()
    except Exception as e:
        return jsonify({"error": f"Failed to load page: {str(e)}"}), 500


@website_bp.route("/")
def index():
    """Serve main dashboard HTML (redirects to single-user)"""
    return serve_html(DASHBOARD_DIR / "index.html")


@website_bp.route("/single-user/")
def single_user():
    """Serve single-user dashboard"""
    return serve_html(DASHBOARD_DIR / "single-user" / "index.html")


@website_bp.route("/prs/")
def prs():
    """Serve PR metrics dashboard"""
    return serve_html(DASHBOARD_DIR / "prs" / "index.html")


@website_bp.route("/compare/")
def compare():
    """Serve user comparison dashboard"""
    return serve_html(DASHBOARD_DIR / "compare" / "index.html")


@website_bp.route("/user/")
def user():
    """Serve individual user stats dashboard"""
    return serve_html(DASHBOARD_DIR / "user" / "index.html")


@website_bp.route("/jira/")
def jira():
    """Serve JIRA stats dashboard"""
    return serve_html(DASHBOARD_DIR / "jira" / "index.html")

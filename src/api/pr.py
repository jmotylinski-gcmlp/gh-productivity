"""Pull Request API endpoints"""

from flask import Blueprint, jsonify, request

from src.github.pr_processor import (
    get_all_repositories,
    get_repository_summary,
    get_repository_monthly_stats
)

pr_bp = Blueprint('pr', __name__, url_prefix='/api/pr')


@pr_bp.route("/repositories")
def get_pr_repos():
    """Get list of all repositories with PR data"""
    try:
        repos = get_all_repositories()
        return jsonify(repos)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@pr_bp.route("/stats")
def get_pr_stats():
    """Get overall PR statistics for a repository"""
    repo = request.args.get("repo")

    if not repo:
        return jsonify({"error": "repo parameter required"}), 400

    try:
        stats = get_repository_summary(repo)
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@pr_bp.route("/stats/monthly")
def get_pr_stats_monthly():
    """Get monthly PR statistics for a repository"""
    repo = request.args.get("repo")

    if not repo:
        return jsonify({"error": "repo parameter required"}), 400

    try:
        stats = get_repository_monthly_stats(repo)
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

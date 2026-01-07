"""API blueprints for the productivity dashboard"""

from src.api.github import github_bp
from src.api.jira import jira_bp
from src.api.pr import pr_bp

__all__ = ['github_bp', 'jira_bp', 'pr_bp']

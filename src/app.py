"""Flask web backend for productivity dashboard"""

from pathlib import Path
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

# Get absolute paths relative to this file's location
BASE_DIR = Path(__file__).parent.parent
DASHBOARD_DIR = BASE_DIR / "dashboard"

# Ensure data directories exist (required for Azure deployment)
(BASE_DIR / "data" / "cache").mkdir(parents=True, exist_ok=True)
(BASE_DIR / "data" / "exports").mkdir(parents=True, exist_ok=True)


def create_app():
    """Application factory for Flask app"""
    app = Flask(__name__, static_folder=str(DASHBOARD_DIR), static_url_path="")

    # Register API blueprints
    from src.api.github import github_bp
    from src.api.jira import jira_bp
    from src.api.pr import pr_bp
    from src.api.admin import admin_bp
    from src.routes import website_bp

    app.register_blueprint(github_bp)
    app.register_blueprint(jira_bp)
    app.register_blueprint(pr_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(website_bp)

    return app


# Create app instance for direct running and gunicorn
app = create_app()


if __name__ == "__main__":
    app.run(debug=True, port=5000)

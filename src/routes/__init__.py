"""
Flask Blueprints — modular route registration.

Each Blueprint handles a single domain concern:
    - auth: Login, logout, JWT lifecycle
    - transfer: Fund transfers with idempotency and outbox
    - health: Health checks, metrics, home
    - upload: CSV dataset ingestion
    - admin: User/account lookups, test reset
"""
from __future__ import annotations

from flask import Flask

from routes.admin_routes import admin_bp
from routes.auth_routes import auth_bp
from routes.health_routes import health_bp
from routes.transfer_routes import transfer_bp
from routes.upload_routes import upload_bp
from routes.dashboard_routes import dashboard_bp


def register_blueprints(app: Flask) -> None:
    """Register all API Blueprints with the Flask application."""
    app.register_blueprint(auth_bp)
    app.register_blueprint(transfer_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(dashboard_bp)

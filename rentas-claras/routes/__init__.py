"""
Routes Package - Flask Blueprints for RentasClaras
===================================================

This package organizes routes into logical blueprints:
- auth: Login/logout (PIN protection)
- pagos: Main payment tracking page and APIs
- contratos: Contract renewal management
- whatsapp: WhatsApp API endpoints
- admin: Admin/scheduler test endpoints
- backups: Backup management APIs
"""

from flask import Flask


def register_blueprints(app: Flask) -> None:
    """Register all blueprints with the Flask app."""
    from routes.auth import auth_bp
    from routes.pagos import pagos_bp
    from routes.contratos import contratos_bp
    from routes.whatsapp import whatsapp_bp
    from routes.admin import admin_bp
    from routes.backups import backups_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(pagos_bp)
    app.register_blueprint(contratos_bp)
    app.register_blueprint(whatsapp_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(backups_bp)

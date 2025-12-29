"""
RentasClaras MVP - Simple Bulk Sender
======================================

A minimal web interface for:
1. Display list of tenants with checkboxes
2. Uncheck those who already paid
3. Click "Send" to message all checked tenants

Tech Stack: Flask + Simple HTML (no frameworks)
WhatsApp: WhatsApp Web click-to-chat links (manual but legal)
Database: SQLite for persistence + historical records

Author: RentasClaras Engineering
Date: December 2024
"""

import atexit
import locale
import logging
import os
import sys

# Load environment variables from .env file BEFORE any other imports
from dotenv import load_dotenv

load_dotenv()

# Import database module
from database import init_database, seed_tenants, startup_health_check
from flask import Flask

# Import blueprint registration
from routes import register_blueprints

# Import scheduler functions
from src.scheduler import (
    get_scheduler_status,
    start_scheduler,
    stop_scheduler,
    TIMEZONE as MX_TZ,
)


# =============================================================================
# SET SPANISH LOCALE
# =============================================================================
try:
    locale.setlocale(locale.LC_TIME, "es_ES.UTF-8")
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, "es_MX.UTF-8")
    except locale.Error:
        pass  # Fall back to default if Spanish locale not available


# =============================================================================
# CREATE FLASK APP
# =============================================================================
app = Flask(__name__)

# Security: Secret key and PIN protection
# CRITICAL: Both SECRET_KEY and RENTASCLARAS_PIN must be set in environment
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError(
        "SECRET_KEY environment variable is required for session security. "
        'Generate with: python -c "import secrets; print(secrets.token_hex(32))"'
    )
app.secret_key = SECRET_KEY

RENTASCLARAS_PIN = os.environ.get("RENTASCLARAS_PIN")
if not RENTASCLARAS_PIN:
    raise ValueError(
        "RENTASCLARAS_PIN environment variable is required. See .env.example"
    )


# =============================================================================
# FEATURE FLAGS - For gradual template migration
# =============================================================================
FEATURE_FLAGS = {
    "use_external_templates": os.environ.get("USE_EXTERNAL_TEMPLATES", "false").lower()
    == "true",
}


def get_feature_flag(flag_name: str) -> bool:
    """Check if a feature flag is enabled."""
    return FEATURE_FLAGS.get(flag_name, False)


# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================
startup_health_check()  # Run health checks first
init_database()
seed_tenants()


# =============================================================================
# REGISTER BLUEPRINTS
# =============================================================================
register_blueprints(app)


# =============================================================================
# SCHEDULER SETUP (Using consolidated scheduler from src/scheduler.py)
# =============================================================================
logging.basicConfig(level=logging.INFO)
scheduler_logger = logging.getLogger("apscheduler")
scheduler_logger.setLevel(logging.INFO)

# Start the scheduler only if not in reloader process
# This prevents double-start in Flask debug mode which forks a reloader process
_is_reloader = os.environ.get("WERKZEUG_RUN_MAIN") != "true" and "flask" in sys.modules
if not _is_reloader:
    start_scheduler()
    scheduler_logger.info("✅ Scheduler started via src/scheduler.py module")
else:
    scheduler_logger.info("⏭️ In reloader process - skipping scheduler start")

# Store scheduler status function in app config for access by admin blueprint
app.config["get_scheduler_status"] = get_scheduler_status

# Register scheduler shutdown on app exit
atexit.register(stop_scheduler)


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    # Note: Scheduler is already started above at module level.
    # Don't call start_scheduler() again to avoid duplicate initialization.

    print(
        """
╔══════════════════════════════════════════════════════════════════╗
║                    🏠 RentasClaras MVP                            ║
║                Simple Bulk WhatsApp Sender                        ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  Abre tu navegador en: http://localhost:5001                     ║
║                                                                   ║
║  Instrucciones:                                                   ║
║  1. Desmarca los inquilinos que YA PAGARON                       ║
║  2. Click en "Generar Enlaces de WhatsApp"                       ║
║  3. Click en cada enlace para enviar el mensaje                  ║
║                                                                   ║
║  🤖 SCHEDULER ACTIVO: Recordatorios automáticos                   ║
║     - 8:00 AM: Recordatorio de mañana (Día 1)                    ║
║     - 5:00 PM: Recordatorio de tarde (Día 1)                     ║
║                                                                   ║
╚══════════════════════════════════════════════════════════════════╝
"""
    )
    app.run(debug=False, port=5001)

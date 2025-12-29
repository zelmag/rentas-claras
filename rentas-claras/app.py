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

# Load environment variables from .env file BEFORE any other imports
from dotenv import load_dotenv
load_dotenv()

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from flask import Flask
from pytz import timezone

# Import database module
from database import init_database, seed_tenants, startup_health_check

# Import scheduler functions
from src.scheduler import start_scheduler, stop_scheduler

# Import blueprint registration
from routes import register_blueprints


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
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
RENTASCLARAS_PIN = os.environ.get("RENTASCLARAS_PIN")
if not RENTASCLARAS_PIN:
    raise ValueError(
        "RENTASCLARAS_PIN environment variable is required. See .env.example"
    )


# =============================================================================
# FEATURE FLAGS - For gradual template migration
# =============================================================================
FEATURE_FLAGS = {
    "use_external_templates": os.environ.get("USE_EXTERNAL_TEMPLATES", "false").lower() == "true",
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
# SCHEDULER SETUP (APScheduler for automated rent reminders)
# =============================================================================
logging.basicConfig(level=logging.INFO)
scheduler_logger = logging.getLogger("apscheduler")
scheduler_logger.setLevel(logging.INFO)

# Mexico City timezone (permanent UTC-6 since 2022 - no more DST)
MX_TZ = timezone("America/Mexico_City")


def run_rent_automation(task_name: str):
    """
    Wrapper to run rent automation within Flask app context.

    This ensures database connections work properly from background thread.
    """
    with app.app_context():
        from src.tasks import send_rent_reminders
        scheduler_logger.info(f"🔔 Triggering: {task_name}")
        result = send_rent_reminders()
        scheduler_logger.info(f"📊 Result: {result}")
        return result


def run_backup():
    """Run backup within Flask app context."""
    with app.app_context():
        from src.backup import scheduled_backup
        scheduler_logger.info("🔄 Starting daily database backup...")
        success = scheduled_backup()
        if success:
            scheduler_logger.info("✅ Daily backup completed successfully")
        else:
            scheduler_logger.error("❌ Daily backup FAILED - check logs")
        return success


# Initialize the background scheduler
scheduler = BackgroundScheduler(timezone=MX_TZ)

# Job 1: Day 1 - Monthly rent reminder at 9 AM
scheduler.add_job(
    func=run_rent_automation,
    trigger=CronTrigger(day=1, hour=9, minute=0, timezone=MX_TZ),
    args=["Day 1 - Monthly Reminder"],
    id="rent_reminder_day_1",
    replace_existing=True,
)

# Job 2: Days 2, 3, 5, 7, 8 - Late payment escalations at 9 AM
scheduler.add_job(
    func=run_rent_automation,
    trigger=CronTrigger(day="2,3,5,7,8", hour=9, minute=0, timezone=MX_TZ),
    args=["Late Payment Escalation"],
    id="late_escalation",
    replace_existing=True,
)

# Job 3: Daily database backup at 6 AM Mexico City time
scheduler.add_job(
    func=run_backup,
    trigger=CronTrigger(hour=6, minute=0, timezone=MX_TZ),
    id="daily_backup",
    name="Daily Database Backup",
    replace_existing=True,
)

# Start the scheduler
scheduler.start()
scheduler_logger.info("✅ APScheduler started - rent reminders scheduled")

# Store scheduler in app config for access by admin blueprint
app.config['scheduler'] = scheduler

# Register scheduler shutdown on app exit
atexit.register(stop_scheduler)


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    # Start the automated reminder scheduler
    start_scheduler()

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

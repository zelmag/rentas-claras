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
import os

# Load environment variables from .env file BEFORE any other imports
from dotenv import load_dotenv
load_dotenv()
import urllib.parse
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from functools import wraps
from typing import Optional

# Import scheduler for automated reminders
from src.scheduler import start_scheduler, stop_scheduler, get_scheduler_status

# Import database module
from database import (
    get_all_tenants,
    get_available_months,
    get_expiring_contracts,
    get_last_sync_time,
    get_message_counts_for_month,
    get_monthly_status,
    get_tenant_by_id,
    get_tenants_by_property,
    init_database,
    seed_tenants,
    startup_health_check,
    Tenant,
    update_payment_status,
    update_renewal_status,
    update_tenant_phone,
)
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    render_template_string,
    request,
    session,
    url_for,
)

# Set Spanish locale for date formatting
try:
    locale.setlocale(locale.LC_TIME, "es_ES.UTF-8")
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, "es_MX.UTF-8")
    except locale.Error:
        pass  # Fall back to default if Spanish locale not available

app = Flask(__name__)

# =============================================================================
# SECURITY: Secret key and PIN protection
# =============================================================================
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
RENTASCLARAS_PIN = os.environ.get("RENTASCLARAS_PIN")
if not RENTASCLARAS_PIN:
    raise ValueError(
        "RENTASCLARAS_PIN environment variable is required. See .env.example"
    )


def login_required(f):
    """Decorator to require PIN authentication."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


# =============================================================================
# FEATURE FLAGS - For gradual template migration
# =============================================================================
FEATURE_FLAGS = {
    "use_external_templates": os.environ.get("USE_EXTERNAL_TEMPLATES", "false").lower() == "true",
}


def get_feature_flag(flag_name: str) -> bool:
    """Check if a feature flag is enabled."""
    return FEATURE_FLAGS.get(flag_name, False)


# Initialize database on startup with health check
startup_health_check()  # Run health checks first
init_database()
seed_tenants()

# =============================================================================
# SCHEDULER SETUP (APScheduler for automated rent reminders)
# =============================================================================
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone

# Setup logging for scheduler
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

# For testing, use your own number
TEST_MODE = True
TEST_PHONE = os.environ.get("WHATSAPP_TEST_PHONE", "")


# =============================================================================
# MESSAGE GENERATION
# =============================================================================

# Common name abbreviations in Mexican Spanish
NAME_ABBREVIATIONS = {
    "J": "Juan",
    "Ma": "María",
    "Ma.": "María",
    "Mª": "María",
    "Fco": "Francisco",
    "Fco.": "Francisco",
    "Gpe": "Guadalupe",
    "Gpe.": "Guadalupe",
    "Jse": "José",
    "Jse.": "José",
}

# Common second parts of compound first names in Mexican culture
# These should be preserved when they appear as the second word
COMPOUND_SECOND_NAMES = {
    "Carlos",
    "María",
    "Luis",
    "José",
    "Antonio",
    "Francisco",
    "Elena",
    "Isabel",
    "Teresa",
    "Carmen",
    "Cristina",
    "Fernanda",
    "Alejandro",
    "Manuel",
    "Miguel",
    "Angel",
    "Guadalupe",
    "Vanessa",  # Like "Gpe Vanessa" -> "Guadalupe Vanessa"
    # Note: "Pablo" excluded - "José Pablo" should become "José"
}

# Well-known compound first names that should always be preserved as-is
COMPOUND_FIRST_NAMES = {
    "Juan Carlos",
    "José Luis",
    "María Elena",
    "Ana María",
    "María José",
    "Luis Miguel",
    "María Fernanda",
    "María Guadalupe",
    "José Antonio",
    "María Isabel",
    "Juan Manuel",
    "José María",
    "Ana Sofía",
    "Guadalupe Vanessa",
}


def expand_abbreviated_name(name: str) -> str:
    """
    Expand common Mexican name abbreviations.

    Examples:
        "J Carlos" -> "Juan Carlos"
        "Ma Elena" -> "María Elena"
        "Gpe Vanessa" -> "Guadalupe Vanessa"
        "Juan Carlos" -> "Juan Carlos" (preserves well-known compound first name)
        "José Pablo" -> "José" (Pablo treated as middle/last name)
    """
    parts = name.split()
    if not parts:
        return name

    first_part = parts[0]

    # Check if first part is an abbreviation (single letter or known abbreviation)
    if first_part in NAME_ABBREVIATIONS:
        expanded = NAME_ABBREVIATIONS[first_part]
        # If there are more parts, include the second part as compound first name
        if len(parts) > 1:
            return f"{expanded} {parts[1]}"
        return expanded

    # If first part is a single letter followed by more name parts, it's likely abbreviated
    if len(first_part) == 1 and len(parts) > 1:
        # Try to find in abbreviations, otherwise just use what we have
        if first_part.upper() in NAME_ABBREVIATIONS:
            return f"{NAME_ABBREVIATIONS[first_part.upper()]} {parts[1]}"

    # Check if the full name (first two parts) is a well-known compound first name
    if len(parts) >= 2:
        potential_compound = f"{parts[0]} {parts[1]}"
        if potential_compound in COMPOUND_FIRST_NAMES:
            return potential_compound

    # Check if we have a compound first name (e.g., "Juan Carlos")
    # If exactly 2 parts and second part is a known compound name component
    if len(parts) == 2 and parts[1] in COMPOUND_SECOND_NAMES:
        return f"{parts[0]} {parts[1]}"

    return parts[0]


def extract_display_name(full_name: str) -> str:
    """
    Extract the display name for greeting a tenant.

    Handles:
    - Simple names: "María González" -> "María"
    - Abbreviated names: "J Carlos y Raul" -> "Juan Carlos"
    - Compound names: "Gpe Vanessa" -> "Guadalupe Vanessa"
    - Multiple tenants: "Samantha Y Cecilia" -> "Samantha" (first person)

    Note: For shared units (like "J Carlos y Raul"), only Matehuala B
    requires messaging both tenants. The rest communicate with 1 person.
    """
    if not full_name:
        return "Inquilino"

    # Check for "y" or "Y" indicating multiple tenants - take first person only
    # (except for Matehuala B which is handled separately)
    name_lower = full_name.lower()
    if " y " in name_lower:
        # Split by " y " and take the first person
        first_person = full_name.split(" y ")[0].split(" Y ")[0].strip()
        return expand_abbreviated_name(first_person)

    return expand_abbreviated_name(full_name)


def generate_rent_reminder(tenant: Tenant, month_name: str) -> str:
    """
    Generate a rent reminder message in professional Regio Spanish.
    Tone: amable, profesional, firme y directo. No harsh language.
    Simple monthly reminder - no late fees.
    """
    # Extract proper display name
    display_name = extract_display_name(tenant.name)

    # Simple message without penalties
    message = f"Buenos días {display_name}. Espero esté bien. Para recordarle por favor del pago de la renta de {month_name}. Total: ${tenant.rent:,.0f} MXN."

    return message


def create_whatsapp_link(phone: str, message: str) -> str:
    """
    Create a WhatsApp click-to-chat URL.
    This opens WhatsApp with the message pre-filled.
    """
    # Remove + and spaces from phone
    clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")

    # URL encode the message
    encoded_message = urllib.parse.quote(message)

    return f"https://wa.me/{clean_phone}?text={encoded_message}"


# =============================================================================
# HTML TEMPLATE
# =============================================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RentasClaras - Envío de Recordatorios</title>
    <link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
    <link rel="apple-touch-icon" href="/static/icon-192.png">
    <link rel="manifest" href="/static/manifest.json">
    <meta name="theme-color" content="#0A7A0A">
    <!-- SheetJS library for Excel export -->
    <script src="https://cdn.sheetjs.com/xlsx-0.20.1/package/dist/xlsx.full.min.js"></script>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        /* ===========================================
           MOBILE-FIRST CSS: Base styles for mobile (320px+)
           Breakpoints: 768px (tablet), 1024px (desktop)
           =========================================== */
        :root {
            /* Color system */
            --color-primary: #0A7A0A;
            --color-primary-dark: #085A08;
            --color-danger: #CC0000;
            --color-danger-dark: #990000;
            --color-neutral: #333333;
            --color-neutral-light: #F5F5F5;
            --color-border: #CCCCCC;
            --color-white: #FFFFFF;
            --color-black: #000000;
            
            /* Typography - Mobile first (16px minimum for accessibility) */
            --font-size-xs: 0.875rem;   /* 14px */
            --font-size-sm: 1rem;       /* 16px - minimum for body */
            --font-size-base: 1.125rem; /* 18px */
            --font-size-lg: 1.25rem;    /* 20px */
            --font-size-xl: 1.5rem;     /* 24px */
            --font-size-2xl: 1.875rem;  /* 30px */
            --font-size-3xl: 2.25rem;   /* 36px */
            
            /* Spacing */
            --space-xs: 4px;
            --space-sm: 8px;
            --space-md: 16px;
            --space-lg: 24px;
            --space-xl: 32px;
            
            /* Touch targets - 48px minimum for accessibility */
            --touch-target-min: 48px;
            --touch-target-lg: 56px;
            --touch-target-xl: 72px;
            
            /* Border radius */
            --radius-sm: 8px;
            --radius-md: 12px;
            --radius-lg: 16px;
            --radius-full: 9999px;
            
            /* Safe areas for notched phones */
            --safe-area-top: env(safe-area-inset-top, 0px);
            --safe-area-bottom: env(safe-area-inset-bottom, 0px);
            --safe-area-left: env(safe-area-inset-left, 0px);
            --safe-area-right: env(safe-area-inset-right, 0px);
        }
        
        /* ===========================================
           UNIFIED STATUS PILL COMPONENT
           Single source of truth for all status buttons/pills
           Used by: pagos (tenant-status), contratos (renewal-btn)
           =========================================== */
        .status-pill {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: var(--space-sm);
            padding: var(--space-md) var(--space-lg);
            border: 4px solid var(--color-border);
            border-radius: var(--radius-md);
            background: var(--color-white);
            cursor: pointer;
            font-size: var(--font-size-base);
            font-weight: 800;
            transition: all 0.2s;
            min-height: var(--touch-target-lg);
            user-select: none;
        }
        
        @media (min-width: 768px) {
            .status-pill {
                min-height: var(--touch-target-xl);
                font-size: var(--font-size-lg);
            }
        }
        
        .status-pill:hover {
            background: var(--color-neutral-light);
        }
        
        /* Paid / Success / Renovará state (green) */
        .status-pill.status-success,
        .status-pill.paid,
        .status-pill.active-green {
            background: var(--color-white);
            border-color: var(--color-primary);
            color: var(--color-primary);
        }
        
        .status-pill.status-success:hover,
        .status-pill.paid:hover,
        .status-pill.active-green:hover {
            background: var(--color-primary);
            color: var(--color-white);
        }
        
        /* Unpaid / Danger / No renovará state (red) */
        .status-pill.status-danger,
        .status-pill.unpaid,
        .status-pill.active-red {
            background: var(--color-white);
            border-color: var(--color-danger);
            color: var(--color-danger);
        }
        
        .status-pill.status-danger:hover,
        .status-pill.unpaid:hover,
        .status-pill.active-red:hover {
            background: var(--color-danger);
            color: var(--color-white);
        }
        
        /* Pending / Neutral / Pendiente state (gray) */
        .status-pill.status-neutral,
        .status-pill.pending,
        .status-pill.active-yellow {
            background: var(--color-neutral-light);
            border-color: var(--color-neutral);
            color: var(--color-neutral);
        }
        
        /* ===========================================
           UNIFIED SEARCH BAR STYLES
           Shared between Pagos and Contratos tabs
           =========================================== */
        .search-wrapper {
            position: relative;
            width: 100%;
        }
        
        .search-input-styled {
            width: 100%;
            padding: 16px 48px 16px 48px; /* Right padding for X button */
            font-size: 1.1rem;
            border: 3px solid var(--color-border);
            border-radius: var(--radius-md);
            background: var(--color-white);
            color: var(--color-black);
            box-sizing: border-box;
        }
        
        .search-input-styled:focus {
            outline: none;
            border-color: var(--color-primary);
        }
        
        .search-icon {
            position: absolute;
            left: 16px;
            top: 50%;
            transform: translateY(-50%);
            width: 20px;
            height: 20px;
            color: #999;
            pointer-events: none;
        }
        
        .search-clear-btn {
            position: absolute;
            right: 0;
            top: 0;
            bottom: 0;
            width: 48px;
            display: none;
            align-items: center;
            justify-content: center;
            background: none;
            border: none;
            font-size: 1.3rem;
            cursor: pointer;
            color: #666;
            padding: 0;
        }
        
        .search-clear-btn:hover {
            color: var(--color-danger);
        }
        
        .search-clear-btn.visible {
            display: flex;
        }
        
        /* ===========================================
           PROMINENT SEARCH SECTION STYLES
           Used for both Pagos and Contratos tabs
           =========================================== */
        .prominent-search-section {
            margin-bottom: 20px;
            position: sticky;
            top: 0;
            z-index: 100;
            background: var(--color-primary);
            padding: 16px;
            margin-left: -16px;
            margin-right: -16px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }
        
        .prominent-search-label {
            color: white;
            font-size: 1.1rem;
            font-weight: 800;
            margin-bottom: 10px;
            text-align: center;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .prominent-search-input {
            font-size: 1.4rem;
            padding: 20px 56px 20px 20px;
            border: 4px solid #065F06;
            border-radius: 16px;
            box-shadow: inset 0 2px 8px rgba(0,0,0,0.1);
            font-weight: 600;
            background: white;
        }
        
        .prominent-search-clear {
            font-size: 2rem;
            width: 56px;
            color: var(--color-danger);
            font-weight: bold;
        }
        
        .prominent-search-results {
            margin-top: 12px;
            color: white;
            font-size: 1.2rem;
            font-weight: 700;
            display: none;
            text-align: center;
        }
        
        .status-pill.status-neutral:hover,
        .status-pill.pending:hover,
        .status-pill.active-yellow:hover {
            background: var(--color-neutral);
            color: var(--color-white);
        }
        
        /* Touch device adjustments - prevent hover on touch */
        @media (hover: none) {
            .status-pill.status-success:hover,
            .status-pill.paid:hover,
            .status-pill.active-green:hover {
                background: var(--color-white);
                color: var(--color-primary);
            }
            .status-pill.status-success:active,
            .status-pill.paid:active,
            .status-pill.active-green:active {
                background: var(--color-primary);
                color: var(--color-white);
            }
            
            .status-pill.status-danger:hover,
            .status-pill.unpaid:hover,
            .status-pill.active-red:hover {
                background: var(--color-white);
                color: var(--color-danger);
            }
            .status-pill.status-danger:active,
            .status-pill.unpaid:active,
            .status-pill.active-red:active {
                background: var(--color-danger);
                color: var(--color-white);
            }
            
            .status-pill.status-neutral:hover,
            .status-pill.pending:hover,
            .status-pill.active-yellow:hover {
                background: var(--color-neutral-light);
                color: var(--color-neutral);
            }
            .status-pill.status-neutral:active,
            .status-pill.pending:active,
            .status-pill.active-yellow:active {
                background: var(--color-neutral);
                color: var(--color-white);
            }
        }
        
        /* Full width variant for mobile */
        .status-pill.status-pill--full-width {
            width: 100%;
        }
        
        @media (min-width: 768px) {
            .status-pill.status-pill--full-width {
                width: auto;
                min-width: 160px;
            }
        }
        
        /* Small variant for table views */
        .status-pill.status-pill--small {
            padding: var(--space-sm) var(--space-md);
            min-height: var(--touch-target-lg);
            font-size: var(--font-size-sm);
        }
        
        /* ===========================================
           Mobile keyboard scroll fix
           =========================================== */
        @media (max-width: 768px) {
            input:focus,
            textarea:focus,
            select:focus {
                scroll-margin-bottom: 200px;
            }
        }
        
        /* Prevent zoom on input focus (iOS) */
        @supports (-webkit-touch-callout: none) {
            input, select, textarea {
                font-size: 16px !important;
            }
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--color-white);
            min-height: 100vh;
            min-height: -webkit-fill-available;
            color: var(--color-black);
            /* Mobile: tighter padding, account for bottom nav */
            padding: var(--space-md);
            padding-top: calc(var(--space-md) + var(--safe-area-top));
            padding-bottom: calc(80px + var(--safe-area-bottom)); /* Space for bottom nav */
            font-size: var(--font-size-base);
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }
        
        /* Tablet+ (768px): More padding, no bottom nav needed */
        @media (min-width: 768px) {
            body {
                padding: var(--space-lg);
                padding-bottom: var(--space-lg);
            }
        }
        
        /* Desktop (1024px): Even more spacious */
        @media (min-width: 1024px) {
            body {
                padding: var(--space-xl);
                font-size: 20px;
            }
        }
        
        .container {
            max-width: 100%;
            margin: 0 auto;
        }
        
        @media (min-width: 768px) {
            .container {
                max-width: 720px;
            }
        }
        
        @media (min-width: 1024px) {
            .container {
                max-width: 900px;
            }
        }
        
        /* Header - mobile first */
        header {
            text-align: center;
            margin-bottom: var(--space-lg);
            background: var(--color-white);
            padding: var(--space-md);
            border-radius: var(--radius-lg);
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        
        @media (min-width: 768px) {
            header {
                padding: var(--space-lg);
                margin-bottom: var(--space-xl);
            }
        }
        
        h1 {
            font-size: var(--font-size-2xl);
            margin-bottom: var(--space-sm);
            color: var(--color-black);
            font-weight: 800;
        }
        
        @media (min-width: 768px) {
            h1 {
                font-size: var(--font-size-3xl);
            }
        }
        
        /* ===========================================
           BOTTOM NAVIGATION - Mobile only
           =========================================== */
        .bottom-nav {
            display: flex;
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: var(--color-white);
            border-top: 2px solid var(--color-border);
            padding: var(--space-sm);
            padding-bottom: calc(var(--space-sm) + var(--safe-area-bottom));
            z-index: 1000;
            justify-content: space-around;
            gap: var(--space-sm);
            box-shadow: 0 -4px 12px rgba(0,0,0,0.1);
        }
        
        .bottom-nav-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-decoration: none;
            color: var(--color-neutral);
            font-size: var(--font-size-xs);
            font-weight: 700;
            padding: var(--space-sm);
            border-radius: var(--radius-sm);
            min-width: 64px;
            min-height: var(--touch-target-min);
            transition: all 0.2s;
        }
        
        .bottom-nav-item.active {
            color: var(--color-primary);
            background: rgba(10, 122, 10, 0.1);
        }
        
        .bottom-nav-item:hover {
            background: var(--color-neutral-light);
        }
        
        .bottom-nav-icon {
            font-size: 1.5rem;
            margin-bottom: 2px;
        }
        
        /* Hide bottom nav on tablet+ (use sidebar or top nav instead) */
        @media (min-width: 768px) {
            .bottom-nav {
                display: none;
            }
        }
        
        /* ===========================================
           TOP NAVBAR - Always visible, replaces big buttons
           =========================================== */
        .top-navbar {
            display: flex;
            gap: var(--space-sm);
            justify-content: center;
            margin: var(--space-md) 0;
            padding: var(--space-sm);
            background: var(--color-neutral-light);
            border-radius: var(--radius-lg);
        }
        
        .top-navbar-item {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: var(--space-sm);
            flex: 1;
            padding: var(--space-md) var(--space-lg);
            border-radius: var(--radius-md);
            text-decoration: none;
            font-size: var(--font-size-base);
            font-weight: 800;
            transition: all 0.2s;
            min-height: var(--touch-target-min);
            border: none;
            cursor: pointer;
        }
        
        .top-navbar-item.active {
            background: var(--color-primary);
            color: var(--color-white);
            box-shadow: 0 2px 8px rgba(10, 122, 10, 0.3);
        }

        .top-navbar-item:not(.active) {
            background: var(--color-white);
            color: var(--color-neutral);
        }
        
        .top-navbar-item:not(.active):hover {
            background: var(--color-white);
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .top-navbar-icon {
            font-size: 1.3rem;
        }
        
@media (min-width: 768px) {
            .top-navbar {
                max-width: 500px;
                margin: var(--space-lg) auto;
            }
            
            .top-navbar-item {
                font-size: var(--font-size-lg);
                padding: var(--space-lg) var(--space-xl);
            }
            
            .top-navbar-icon {
                font-size: 1.5rem;
            }
        }
        
        /* ===========================================
           SYNC INDICATOR - Shows last save time
           =========================================== */
        .sync-indicator {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            padding: 8px 16px;
            font-size: 0.85rem;
            color: #666;
            background: #f5f5f5;
            border-radius: 20px;
            margin: 0 auto 16px auto;
            max-width: fit-content;
            transition: all 0.3s ease;
        }
        
        .sync-indicator.syncing {
            color: #0A7A0A;
            background: #e8f5e9;
        }
        
        .sync-indicator.synced {
            color: #0A7A0A;
            background: #e8f5e9;
        }
        
        .sync-indicator.error {
            color: #CC0000;
            background: #ffebee;
        }
        
        .sync-icon {
            font-size: 1rem;
        }
        
        .sync-icon.spinning {
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        
        /* Top Navigation (visible on tablet+) - LEGACY, can remove */
        .nav-tabs {
            display: none; /* Hidden on mobile - using bottom nav */
            gap: var(--space-md);
            justify-content: center;
            margin-bottom: var(--space-lg);
        }
        
        @media (min-width: 768px) {
            .nav-tabs {
                display: flex;
            }
        }
        
        .nav-tab {
            display: inline-flex;
            align-items: center;
            gap: var(--space-sm);
            padding: var(--space-md) var(--space-lg);
            border-radius: var(--radius-md);
            text-decoration: none;
            font-size: var(--font-size-lg);
            font-weight: 800;
            transition: all 0.2s;
            min-height: var(--touch-target-xl);
            border: 4px solid;
        }
        
        .nav-tab.active {
            background: var(--color-neutral);
            color: var(--color-white);
            border-color: var(--color-neutral);
        }

        .nav-tab:not(.active) {
            background: var(--color-white);
            color: var(--color-neutral);
            border-color: var(--color-neutral);
        }

        .nav-tab:not(.active):hover {
            background: var(--color-neutral-light);
        }
        
        /* Subtitle - responsive */
        .subtitle {
            color: #4a4a4a;
            font-size: var(--font-size-sm);
        }
        
        @media (min-width: 768px) {
            .subtitle {
                font-size: var(--font-size-base);
            }
        }
        
        .date-badge {
            display: inline-block;
            background: var(--color-neutral);
            color: var(--color-white);
            padding: var(--space-md) var(--space-lg);
            border-radius: var(--radius-full);
            font-size: var(--font-size-base);
            margin-top: var(--space-md);
            font-weight: 700;
        }
            
        .date-display {
            margin-top: var(--space-lg);
        }
            
        .date-month-year {
            font-size: var(--font-size-xl);
            font-weight: 700;
            color: var(--color-neutral);
            text-transform: capitalize;
            margin-top: var(--space-xs);
        }
        
        @media (min-width: 768px) {
            .date-month-year {
                font-size: var(--font-size-2xl);
            }
        }
        
        .controls {
            display: flex;
            flex-direction: column; /* Stack on mobile */
            gap: var(--space-md);
            margin-bottom: var(--space-lg);
        }
        
        @media (min-width: 768px) {
            .controls {
                flex-direction: row;
                flex-wrap: wrap;
            }
        }
        
        /* Buttons - Mobile first with proper touch targets */
        button {
            padding: var(--space-md) var(--space-lg);
            border: none;
            border-radius: var(--radius-md);
            font-size: var(--font-size-base);
            cursor: pointer;
            transition: all 0.2s;
            min-height: var(--touch-target-lg);
            font-weight: 700;
            width: 100%; /* Full width on mobile */
        }
        
        @media (min-width: 768px) {
            button {
                width: auto;
                min-height: var(--touch-target-xl);
                padding: var(--space-lg) var(--space-xl);
                font-size: var(--font-size-lg);
            }
        }
        
        .btn-primary {
            background: var(--color-primary);
            color: var(--color-white);
        }

        .btn-primary:hover {
            background: var(--color-primary-dark);
            transform: translateY(-2px);
        }
        
        /* Prevent transform on touch devices (causes issues) */
        @media (hover: none) {
            .btn-primary:hover {
                transform: none;
            }
        }
        
        .btn-secondary {
            background: var(--color-neutral-light);
            color: var(--color-black);
            border: 3px solid var(--color-border);
        }

        .btn-secondary:hover {
            background: var(--color-border);
            color: var(--color-black);
        }
        
        /* Property sections - responsive */
        .property-section {
            margin-bottom: 40px;
            background: var(--color-white);
            border-radius: var(--radius-lg);
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            overflow: hidden;
        }
        
        .property-header {
            background: var(--color-neutral);
            color: var(--color-white);
            padding: var(--space-md);
            font-weight: 800;
            font-size: var(--font-size-base);
            display: flex;
            flex-direction: column; /* Stack on mobile */
            gap: var(--space-sm);
            text-align: center;
        }
        
        @media (min-width: 768px) {
            .property-header {
                flex-direction: row;
                justify-content: space-between;
                align-items: center;
                padding: var(--space-lg) var(--space-xl);
                font-size: var(--font-size-lg);
                text-align: left;
            }
        }
        
        .property-stats {
            display: flex;
            gap: var(--space-sm);
            flex-wrap: wrap;
            justify-content: center;
        }
        
        @media (min-width: 768px) {
            .property-stats {
                justify-content: flex-end;
            }
        }
        
        .property-count {
            background: rgba(255,255,255,0.25);
            padding: var(--space-sm) var(--space-md);
            border-radius: var(--radius-full);
            font-size: var(--font-size-xs);
        }
        
        @media (min-width: 768px) {
            .property-count {
                font-size: var(--font-size-sm);
            }
        }
        
        .property-paid-count {
            background: var(--color-primary);
            padding: var(--space-sm) var(--space-md);
            border-radius: var(--radius-full);
            font-size: var(--font-size-xs);
            font-weight: 800;
        }
        
        @media (min-width: 768px) {
            .property-paid-count {
                font-size: var(--font-size-sm);
            }
        }

        .property-pending-count {
            background: var(--color-danger);
            padding: var(--space-sm) var(--space-md);
            border-radius: var(--radius-full);
            font-size: var(--font-size-xs);
            font-weight: 800;
        }
        
        @media (min-width: 768px) {
            .property-pending-count {
                font-size: var(--font-size-sm);
            }
        }
        
        .tenant-list {
            background: var(--color-white);
        }
        
        /* Tenant cards - Mobile first (card layout) */
        .tenant-item {
            display: flex;
            flex-direction: column; /* Stack vertically on mobile */
            align-items: stretch;
            padding: var(--space-md);
            border-bottom: 2px solid var(--color-border);
            transition: all 0.3s;
            background: var(--color-white);
            border-left: 6px solid var(--color-danger);
            gap: var(--space-md);
        }
        
        @media (min-width: 768px) {
            .tenant-item {
                flex-direction: row;
                flex-wrap: wrap;
                align-items: center;
                padding: var(--space-lg) var(--space-xl);
                border-left-width: 10px;
            }
        }

        .tenant-item.paid {
            background: var(--color-white);
            border-left-color: var(--color-primary);
        }
        
        .tenant-item:hover {
            background: #F5F5F5;  /* Light gray hover (same for both paid/unpaid) */
        }

        .tenant-item.paid:hover {
            background: #F5F5F5;  /* Light gray hover (no color-coded hovers) */
        }
        
        .tenant-item:last-child {
            border-bottom: none;
        }
        
        .tenant-checkbox {
            display: none;
        }
        
        /* Status + Amount row - horizontally aligned */
        .status-amount-row {
            display: flex;
            flex-direction: row;
            align-items: center;
            justify-content: space-between;
            gap: var(--space-md);
            width: 100%;
            order: 2;
        }
        
        .status-amount-row .tenant-status-btn {
            flex: 1;
            order: unset;
        }
        
        .status-amount-row .tenant-amount {
            flex-shrink: 0;
            order: unset;
            text-align: right;
        }
        
        @media (min-width: 768px) {
            .status-amount-row {
                order: 0;
                width: auto;
                flex: 0 0 auto;
            }
        }
        
        /* Tenant status button - Mobile first with full width on mobile */
        .tenant-status-btn {
            width: 100%; /* Full width on mobile */
            min-height: var(--touch-target-lg);
            padding: var(--space-md);
            border-radius: var(--radius-md);
            cursor: pointer;
            font-size: var(--font-size-base);
            font-weight: 800;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: var(--space-sm);
            border: 4px solid;
            transition: all 0.2s;
            user-select: none;
            pointer-events: auto;
            z-index: 10;
            order: 2; /* After name on mobile */
        }
        
        @media (min-width: 768px) {
            .tenant-status-btn {
                width: auto;
                min-width: 160px;
                min-height: var(--touch-target-xl);
                padding: var(--space-md) var(--space-lg);
                font-size: var(--font-size-lg);
                order: 0;
            }
        }
        
        .tenant-status-btn.unpaid {
            background: var(--color-white);
            border-color: var(--color-danger);
            color: var(--color-danger);
        }

        .tenant-status-btn.unpaid:hover {
            background: var(--color-danger);
            color: var(--color-white);
        }
        
        /* Prevent hover effects on touch devices */
        @media (hover: none) {
            .tenant-status-btn.unpaid:hover {
                background: var(--color-white);
                color: var(--color-danger);
            }
            .tenant-status-btn.unpaid:active {
                background: var(--color-danger);
                color: var(--color-white);
            }
        }

        .tenant-status-btn.paid {
            background: var(--color-white);
            border-color: var(--color-primary);
            color: var(--color-primary);
        }

        .tenant-status-btn.paid:hover {
            background: var(--color-primary);
            color: var(--color-white);
        }
        
        @media (hover: none) {
            .tenant-status-btn.paid:hover {
                background: var(--color-white);
                color: var(--color-primary);
            }
            .tenant-status-btn.paid:active {
                background: var(--color-primary);
                color: var(--color-white);
            }
        }
        
        .tenant-status-btn .icon {
            font-size: 1.4rem;
        }
        
        .tenant-main-info {
            flex: 1;
            min-width: 100%;
            order: 1; /* First on mobile */
        }
        
        @media (min-width: 768px) {
            .tenant-main-info {
                min-width: 200px;
                order: 0;
            }
        }
        
        /* Tenant name - responsive */
        .tenant-name {
            font-weight: 800;
            font-size: var(--font-size-lg);
            margin-bottom: var(--space-sm);
            color: var(--color-black);
            text-align: center;
            width: 100%;
        }
        
        @media (min-width: 768px) {
            .tenant-name {
                font-size: var(--font-size-xl);
                text-align: left;
            }
        }
        
        /* Phone number - responsive */
        .tenant-phone-inline {
            font-size: var(--font-size-sm);
            color: #4a4a4a;
            margin-bottom: var(--space-xs);
            text-align: center;
        }
        
        @media (min-width: 768px) {
            .tenant-phone-inline {
                text-align: left;
            }
        }
        
        .tenant-phone-inline a {
            color: #2563eb;
            text-decoration: none;
        }
        
        .tenant-phone-inline a:hover {
            text-decoration: underline;
        }
        
        /* Missing phone warning - mobile first */
        .no-phone-warning {
            display: block;
            background: var(--color-danger);
            color: var(--color-white);
            padding: var(--space-md);
            border-radius: var(--radius-sm);
            font-weight: 800;
            font-size: var(--font-size-sm);
        }
        
        @media (min-width: 768px) {
            .no-phone-warning {
                font-size: var(--font-size-base);
            }
        }
        
        .no-phone-row {
            background: #FEE2E2 !important;
            border-left: 10px solid var(--color-danger) !important;
        }
        
        .add-phone-btn {
            background: var(--color-danger) !important;
            color: var(--color-white) !important;
            padding: var(--space-md) var(--space-lg) !important;
            font-size: var(--font-size-sm) !important;
            min-height: var(--touch-target-min) !important;
            border-radius: var(--radius-md) !important;
        }
        
        .add-phone-btn:hover {
            background: #990000 !important;
        }
        
        .edit-phone-btn, .add-phone-btn {
            background: #333333;
            color: white;
            border: none;
            padding: 14px 20px;  /* P2.5: Increased padding */
            border-radius: 8px;
            font-size: 1.1rem;  /* P2.5: Larger font */
            font-weight: 700;
            cursor: pointer;
            margin-left: 8px;
            min-height: 56px;  /* P2.5: Increased from 44px for 60+ users */
        }
        
        .edit-phone-btn:hover {
            background: #555555;
        }
          
        /* Phone edit modal - Mobile first (bottom sheet on mobile) */
        .phone-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            z-index: 2000;
            align-items: flex-end; /* Bottom sheet on mobile */
            justify-content: center;
        }
        
        @media (min-width: 768px) {
            .phone-modal {
                align-items: center; /* Centered on tablet+ */
            }
        }
          
        .phone-modal.show {
            display: flex;
        }
          
        .phone-modal-content {
            background: var(--color-white);
            padding: var(--space-lg);
            padding-bottom: calc(var(--space-lg) + var(--safe-area-bottom));
            border-radius: var(--radius-lg) var(--radius-lg) 0 0;
            width: 100%;
            max-width: 100%;
            box-shadow: 0 -8px 32px rgba(0,0,0,0.3);
            animation: slideUp 0.3s ease-out;
        }
        
        @keyframes slideUp {
            from {
                transform: translateY(100%);
            }
            to {
                transform: translateY(0);
            }
        }
        
        @media (min-width: 768px) {
            .phone-modal-content {
                max-width: 400px;
                border-radius: var(--radius-lg);
                padding-bottom: var(--space-lg);
                animation: none;
            }
        }
          
        .phone-modal h3 {
            font-size: var(--font-size-xl);
            margin-bottom: var(--space-md);
            text-align: center;
        }
          
        .phone-modal input {
            width: 100%;
            padding: var(--space-md);
            font-size: var(--font-size-lg);
            border: 3px solid var(--color-neutral);
            border-radius: var(--radius-md);
            margin-bottom: var(--space-md);
        }
        
        .phone-modal input:focus {
            outline: none;
            border-color: var(--color-primary);
        }
          
        .phone-modal-buttons {
            display: flex;
            flex-direction: column; /* Stacked on mobile */
            gap: var(--space-md);
        }
        
        @media (min-width: 768px) {
            .phone-modal-buttons {
                flex-direction: row;
            }
        }
          
        .phone-modal-buttons button {
            flex: 1;
            padding: var(--space-md);
            font-size: var(--font-size-base);
            min-height: var(--touch-target-lg);
        }
        
        /* Inline WhatsApp button */
        .whatsapp-inline-btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 12px 20px;
            background: #0A7A0A;  /* P3.12: Standardized to system green */
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 1rem;
            font-weight: 700;
            text-decoration: none;
            cursor: pointer;
            transition: all 0.2s;
            min-height: 48px;
        }
        
        .whatsapp-inline-btn:hover {
            background: #085A08;  /* Darker green on hover */
            transform: translateY(-2px);
        }
        
        .whatsapp-inline-btn.disabled {
            background: #9ca3af;
            cursor: not-allowed;
            pointer-events: none;
        }
        
        .tenant-unit {
            color: #333333;  /* Changed from blue to black/gray - 3-color system */
            font-weight: 700;
        }
        
        /* ISSUE #2: Larger rent amount */
        .tenant-amount {
            text-align: right;
        }
        
        /* Phase 1 Fix: VERY large rent amount - easy to see at arm's length */
        .tenant-rent {
            font-weight: 800;  /* Bolder from 700 */
            font-size: 1.6rem;  /* Increased from 1.4rem */
            color: #0A7A0A;  /* Dark green - better contrast than #16a34a */
        }
        
        .tenant-details {
            display: none;
            width: 100%;
            padding: 16px 20px;
            background: #f9fafb;
            border-top: 2px solid #e5e5e5;
            font-size: 1rem;
            line-height: 1.6;
            color: #374151;
        }
        
        .tenant-details.show {
            display: block;
        }
        
        .tenant-details p {
            margin-bottom: 8px;
        }
        
        .tenant-details strong {
            color: #1a1a1a;
        }
        
        /* Payment method - hidden by default, shown in details */
        .payment-method-row {
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid #e5e5e5;
        }
        
        .payment-method {
            padding: 12px 16px;
            border-radius: 8px;
            border: 2px solid #d4d4d4;
            background: white;
            color: #1a1a1a;
            font-size: 1rem;
            cursor: pointer;
            min-width: 180px;
        }
        
        .payment-method:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            background: #e5e5e5;
        }
        
        .payment-method:enabled {
            border-color: #0A7A0A;  /* System green */
            background: #f0fdf4;
        }
        
        .send-section {
            margin-top: 32px;
            padding: 28px;
            background: white;
            border-radius: 16px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            position: relative;
            z-index: 100;
        }
        
        /* ISSUE #2: Larger send count text */
        .send-count {
            font-size: 1.3rem;
            margin-bottom: 20px;
            color: #1a1a1a;
        }
        
        .send-count strong {
            color: #0A7A0A;  /* System green */
            font-size: 1.5rem;
        }
        
        .whatsapp-links {
            display: none;
            flex-direction: column;
            gap: 12px;
            margin-top: 24px;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .whatsapp-link {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: #f0fdf4;
            border: 2px solid #0A7A0A;  /* System green */
            padding: 16px 20px;
            border-radius: 12px;
            text-decoration: none;
            color: #1a1a1a;
            transition: all 0.2s;
            font-size: 1.1rem;
        }
        
        .whatsapp-link:hover {
            background: #0A7A0A;  /* System green */
            color: white;
        }
        
        .link-name {
            font-weight: 600;
        }
        
        .link-icon {
            font-size: 1.2rem;
            font-weight: 700;
        }
        
        .test-mode-banner {
            background: #F5F5F5;  /* P3.8: Changed from yellow to gray - 3-color system */
            color: #333333;
            padding: 16px 20px;
            text-align: center;
            border-radius: 12px;
            margin-bottom: 24px;
            font-weight: 700;
            font-size: 1.1rem;
            border: 3px solid #333333;
        }
        
        /* =========================================== 
           DEPRECATED: Summary cards removed - using top banner instead
           Keeping CSS for backwards compatibility
           =========================================== */
        .summary {
            display: none;  /* P2.4: Hidden - deprecated */
        }
            
        .summary-card {
            display: none;  /* P2.4: Hidden - deprecated */
        }
            
        .summary-value {
            font-size: 2.5rem;
            font-weight: 800;
            color: #0A7A0A;  /* Changed from #16a34a */
        }
            
        /* ISSUE #2: Larger summary label */
        .summary-label {
            color: #333333;  /* Changed from #4a4a4a */
            font-size: 1rem;
            margin-top: 8px;
            font-weight: 600;
        }
            
        /* =========================================== 
           TOTALS SECTION
           =========================================== */
        .totals-section {
            background: white;
            border-radius: 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            padding: 24px;
            margin-bottom: 32px;
        }
            
        .totals-header {
            font-size: 1.4rem;
            font-weight: 700;
            color: #1a1a1a;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
            
        .property-subtotals {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
            
        .property-subtotal-card {
            background: #f9fafb;
            border-radius: 12px;
            padding: 16px;
            border-left: 4px solid #333333;  /* Changed from blue to black/gray */
        }
            
        .property-subtotal-name {
            font-weight: 700;
            font-size: 1.1rem;
            color: #333333;  /* Changed from blue to black/gray */
            margin-bottom: 12px;
        }
            
        .property-subtotal-stats {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            margin-bottom: 12px;
        }
            
        .property-subtotal-stat {
            font-size: 0.9rem;
            padding: 4px 10px;
            border-radius: 8px;
            background: white;
        }
            
        .property-subtotal-stat.paid {
            background: #dcfce7;
            color: #0A7A0A;  /* Changed from #166534 to system green */
        }
            
        .property-subtotal-stat.pending {
            background: #FEE2E2;  /* Light red background */
            color: #CC0000;  /* System red */
        }
            
        .property-subtotal-amount {
            font-size: 1.3rem;
            font-weight: 700;
            color: #0A7A0A;  /* Changed from #16a34a to system green */
        }
            
        .grand-total {
            background: #0A7A0A;  /* Solid dark green (no gradient) */
            color: white;
            padding: 28px;  /* Increased padding */
            border-radius: 12px;
            text-align: center;
        }
            
        .grand-total-label {
            font-size: 1.1rem;
            margin-bottom: 8px;
            opacity: 0.9;
        }
            
        .grand-total-amount {
            font-size: 2.5rem;
            font-weight: 800;
        }
        
        /* Grand total breakdown */
        .grand-total-breakdown {
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin-bottom: 16px;
        }
        
        .breakdown-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 16px;
            border-radius: 8px;
            background: rgba(255,255,255,0.1);
        }
        
        .breakdown-item.highlight-pending {
            background: rgba(245, 158, 11, 0.3);
            font-weight: 700;
        }
        
        .breakdown-item.highlight-paid {
            background: rgba(34, 197, 94, 0.3);
        }
        
        .breakdown-label {
            font-size: 1rem;
        }
        
        .breakdown-value {
            font-size: 1.3rem;
            font-weight: 800;
        }
        
        /* Offline banner */
        .offline-banner {
            background: #fef2f2;
            color: #dc2626;
            padding: 16px 20px;
            text-align: center;
            border-radius: 12px;
            margin-bottom: 24px;
            font-weight: 700;
            font-size: 1.1rem;
            border: 3px solid #dc2626;
        }
        
        /* Undo toast - #1 PERSISTENT CONFIRMATION */
        .undo-toast {
            position: fixed;
            bottom: 24px;
            left: 50%;
            transform: translateX(-50%);
            background: #0A7A0A;
            color: white;
            padding: 20px 32px;
            border-radius: 16px;
            font-size: 1.3rem;
            font-weight: 800;
            display: none;
            z-index: 1000;
            box-shadow: 0 8px 24px rgba(0,0,0,0.3);
            gap: 20px;
            align-items: center;
            border: 4px solid white;
        }
        
        .undo-toast.show {
            display: flex;
        }
        
        .undo-toast button {
            background: white;
            color: #0A7A0A;
            border: none;
            padding: 12px 20px;
            border-radius: 12px;
            cursor: pointer;
            font-weight: 800;
            min-height: 56px;
            font-size: 1.1rem;
        }
        
        .undo-toast button:hover {
            background: #E5E5E5;
        }
        
        /* #11 CONFETTI CELEBRATION at 100% */
        .confetti-container {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 9999;
            overflow: hidden;
        }
        
        .confetti {
            position: absolute;
            width: 12px;
            height: 12px;
            opacity: 0;
        }
        
        .celebration-banner {
            display: none;
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: #0A7A0A;
            color: white;
            padding: 40px 60px;
            border-radius: 24px;
            font-size: 2rem;
            font-weight: 800;
            z-index: 10000;
            box-shadow: 0 12px 48px rgba(0,0,0,0.4);
            text-align: center;
            border: 6px solid white;
        }
        
        .celebration-banner.show {
            display: block;
            animation: celebrationPop 0.5s ease-out;
        }
        
        @keyframes celebrationPop {
            0% { transform: translate(-50%, -50%) scale(0.5); opacity: 0; }
            50% { transform: translate(-50%, -50%) scale(1.1); }
            100% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
        }
            
        .grand-total-stats {
            display: flex;
            justify-content: center;
            gap: 24px;
            margin-top: 16px;
            flex-wrap: wrap;
        }
            
        .grand-total-stat {
            background: rgba(255,255,255,0.2);
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.95rem;
        }
        
        /* Progress bar for collection rate - NOW AT TOP */
        .progress-bar-container {
            width: 100%;
            max-width: 100%;
            margin: 0 0 20px 0;
            padding: 0 4px;
        }
        
        .progress-bar-label {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
            font-size: 1.1rem;
            font-weight: 700;
        }
        
        .progress-bar-track {
            width: 100%;
            height: 32px;
            background: rgba(255,255,255,0.3);
            border-radius: 16px;
            overflow: hidden;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .progress-bar-fill {
            height: 100%;
            background: #0A7A0A;  /* Solid dark green (no gradient) */
            border-radius: 12px;
            transition: width 0.5s ease-out;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            padding-right: 8px;
            min-width: 0;
        }

        .progress-bar-fill.complete {
            background: #0A7A0A;  /* Same solid dark green */
        }
        
        .progress-bar-text {
            font-size: 0.9rem;
            font-weight: 800;
            color: white;
            text-shadow: 0 1px 2px rgba(0,0,0,0.3);
            white-space: nowrap;
        }
        
        .message-preview {
            background: #f9fafb;
            padding: 20px;
            border-radius: 12px;
            margin-top: 24px;
            text-align: left;
            white-space: pre-wrap;
            font-size: 1rem;
            max-height: 200px;
            overflow-y: auto;
            border-left: 4px solid #0A7A0A;  /* Changed from #16a34a to system green */
            color: #1a1a1a;
        }

        /* ===========================================
           Phase 1 Fix: Excel-like TABLE VIEW for familiar interface
           =========================================== */
        .view-toggle {
            display: flex;
            gap: 12px;
            justify-content: center;
            margin: 24px 0;
        }

        .view-toggle-btn {
            padding: 16px 32px;
            border-radius: 12px;
            border: 4px solid #333333;  /* Changed from blue to black/gray */
            background: white;
            color: #333333;
            font-size: 1.2rem;
            font-weight: 800;
            cursor: pointer;
            transition: all 0.2s;
            min-height: 72px;
        }

        .view-toggle-btn.active {
            background: #333333;  /* Changed from blue to black/gray */
            color: white;
        }

        .view-toggle-btn:hover {
            transform: translateY(-2px);
        }

        /* Excel-style table */
        .excel-view {
            display: none;
            background: white;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            margin-bottom: 32px;
        }

        .excel-view.active {
            display: block;
        }

        .excel-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 1.1rem;
        }

        .excel-table th {
            background: #E5E5E5;
            color: #000000;
            padding: 16px;
            text-align: left;
            font-weight: 800;
            border: 2px solid #CCCCCC;
            font-size: 1.2rem;
        }

        .excel-table td {
            padding: 16px;
            border: 2px solid #CCCCCC;
            background: white;
            color: #000000;
            font-size: 1.1rem;
        }

        .excel-table tr:hover td {
            background: #F5F5F5;
        }

        .excel-table .status-cell {
            text-align: center;
            font-weight: 800;
            font-size: 1.4rem;
        }

        .excel-table .status-cell.unpaid {
            color: #CC0000;
        }

        .excel-table .status-cell.paid {
            color: #0A7A0A;
        }

        .excel-table .rent-cell {
            text-align: right;
            font-weight: 800;
            font-size: 1.3rem;
            color: #0A7A0A;
        }

        .excel-table .action-cell {
            text-align: center;
        }

        .excel-table .action-cell button,
        .tenant-status-btn-table {
            min-height: 56px;
            font-size: 1rem;
            border: 4px solid;  /* P2.7: Added 4px border for consistency */
        }

        .tenant-status-btn-table.paid {
            background: white;
            border-color: #0A7A0A;
            color: #0A7A0A;
            border-width: 4px;  /* P2.7: Thicker border */
        }

        .tenant-status-btn-table.paid:hover {
            background: #0A7A0A;
            color: white;
        }

        .tenant-status-btn-table.unpaid {
            background: white;
            border-color: #CC0000;
            color: #CC0000;
            border-width: 4px;  /* P2.7: Thicker border */
        }

        .tenant-status-btn-table.unpaid:hover {
            background: #CC0000;
            color: white;
        }

        /* P1.3: WhatsApp button in table view */
        .whatsapp-table-btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 10px 16px;
            background: #0A7A0A;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 700;
            text-decoration: none;
            cursor: pointer;
            min-height: 48px;
        }

        .whatsapp-table-btn:hover {
            background: #085A08;
        }

        .whatsapp-table-btn.disabled {
            background: #CCCCCC;
            color: #666666;
            cursor: not-allowed;
            pointer-events: none;
        }

        /* Hide card view when table is active */
        .card-view.hidden {
            display: none;
        }

        /* Hide excel view when card view is active */
        .excel-view.hidden {
            display: none;
        }

        /* ===========================================
           MOBILE EXCEL TABLE OPTIMIZATION
           Compact styles for small screens
           =========================================== */
        @media (max-width: 600px) {
            .excel-table {
                font-size: 0.85rem;
            }
            
            .excel-table th,
            .excel-table td {
                padding: 8px 6px;
                font-size: 0.85rem;
            }
            
            .excel-table th {
                font-size: 0.8rem;
            }
            
            /* Reduce button size in table */
            .tenant-status-btn-table {
                min-height: 44px;
                padding: 6px 10px;
                font-size: 0.9rem;
            }
            
            /* Hide MULTA column on very small screens to fit */
            .excel-table th:nth-child(4),
            .excel-table td:nth-child(4) {
                display: none;
            }
            
            /* Adjust property header on mobile */
            .excel-table th[colspan] {
                font-size: 1.1rem !important;
                padding: 6px 10px !important;
            }
        }

        /* ===========================================
           LEGACY MOBILE OVERRIDES REMOVED
           Now using mobile-first approach - base styles ARE mobile
           Only tablet/desktop use @media (min-width: ...)
           =========================================== */
        
        /* Tenant rent amount - responsive */
        .tenant-rent {
            font-size: var(--font-size-2xl);
            background: #f0fdf4;
            padding: var(--space-md) var(--space-lg);
            border-radius: var(--radius-md);
            display: inline-block;
            border: 3px solid var(--color-primary);
            text-align: center;
            width: 100%;
        }
        
        @media (min-width: 768px) {
            .tenant-rent {
                width: auto;
                font-size: var(--font-size-xl);
            }
        }
        
        .tenant-amount {
            text-align: center;
            order: 3;
        }
        
        @media (min-width: 768px) {
            .tenant-amount {
                text-align: right;
                order: 0;
            }
        }
        
        .whatsapp-inline-btn {
            width: 100%;
            order: 4;
        }
        
        @media (min-width: 768px) {
            .whatsapp-inline-btn {
                width: auto;
                order: 0;
            }
        }
        
        .tenant-details {
            order: 6;
        }
        
        /* Summary cards - mobile first (stacked) */
        .summary {
            display: grid;
            grid-template-columns: 1fr;
            gap: var(--space-md);
            margin-bottom: var(--space-xl);
        }
        
        @media (min-width: 768px) {
            .summary {
                grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            }
        }
        
        .summary-value {
            font-size: var(--font-size-2xl);
            font-weight: 800;
        }
        
        @media (min-width: 768px) {
            .summary-value {
                font-size: var(--font-size-3xl);
            }
        }
        
        /* Grand total - responsive */
        .grand-total-amount {
            font-size: var(--font-size-2xl);
        }
        
        @media (min-width: 768px) {
            .grand-total-amount {
                font-size: var(--font-size-3xl);
            }
        }
        
        .grand-total-stats {
            display: flex;
            flex-direction: column;
            gap: var(--space-sm);
            justify-content: center;
            margin-top: var(--space-md);
        }
        
        @media (min-width: 768px) {
            .grand-total-stats {
                flex-direction: row;
                gap: var(--space-lg);
                flex-wrap: wrap;
            }
        }
        
        /* ===========================================
           Contract Renewal Tracking Styles
           =========================================== */
        .renewal-section {
            margin-top: 16px;
            padding-top: 16px;
            border-top: 2px solid #e5e5e5;
        }
        
        .renewal-buttons,
        .payment-buttons {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin: 12px 0;
        }
        
        /* ===========================================
           Payment Toggle Switch Styles
           =========================================== */
        .payment-toggle-container {
            display: flex;
            align-items: center;
            gap: 12px;
            margin: 8px 0;
        }
        
        .payment-toggle {
            position: relative;
            width: 60px;
            height: 32px;
            flex-shrink: 0;
        }
        
        .payment-toggle input {
            opacity: 0;
            width: 0;
            height: 0;
        }
        
        .payment-toggle .slider {
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: #CC0000;
            transition: 0.3s;
            border-radius: 32px;
        }
        
        .payment-toggle .slider:before {
            position: absolute;
            content: "";
            height: 24px;
            width: 24px;
            left: 4px;
            bottom: 4px;
            background-color: white;
            transition: 0.3s;
            border-radius: 50%;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        
        .payment-toggle input:checked + .slider {
            background-color: #0A7A0A;
        }
        
        .payment-toggle input:checked + .slider:before {
            transform: translateX(28px);
        }
        
        .payment-toggle-label {
            font-size: 1rem;
            font-weight: 700;
            min-width: 100px;
        }
        
        .payment-toggle-label.paid {
            color: #0A7A0A;
        }
        
        .payment-toggle-label.unpaid {
            color: #CC0000;
        }
        
        /* Mobile: Larger toggle for better touch targets (44px+ recommended) */
        @media (max-width: 768px) {
            .payment-toggle {
                width: 72px;
                height: 40px;
            }
            
            .payment-toggle .slider {
                border-radius: 40px;
            }
            
            .payment-toggle .slider:before {
                height: 32px;
                width: 32px;
            }
            
            .payment-toggle input:checked + .slider:before {
                transform: translateX(32px);
            }
            
            .payment-toggle-label {
                font-size: 1.1rem;
            }
        }
        
        /* UNIFIED BUTTON STYLES - payment-btn (Pagos) and renewal-btn (Contratos)
           Both use identical styling for consistency across pages */
        .status-pill.payment-btn,
        .status-pill.renewal-btn {
            display: flex;
            flex: 1;
            padding: 14px 20px;
            border: 3px solid #d4d4d4;
            border-radius: 12px;
            background: white;
            cursor: pointer;
            font-size: 1.1rem;
            font-weight: 700;
            transition: all 0.2s;
            min-height: 56px;
            text-align: center;
            justify-content: center;
            align-items: center;
        }
        
        .status-pill.payment-btn:hover,
        .status-pill.renewal-btn:hover {
            background: #f5f5f5;
        }
        
        .status-pill.payment-btn.active-green,
        .status-pill.renewal-btn.active-green {
            background: #dcfce7;
            border-color: #0A7A0A;
            color: #0A7A0A;
        }
        
        .status-pill.payment-btn.active-red,
        .status-pill.renewal-btn.active-red {
            background: #fee2e2;
            border-color: #CC0000;
            color: #CC0000;
        }
        
        .status-pill.renewal-btn.active-yellow {
            background: #F5F5F5;
            border-color: #333333;
            color: #333333;
        }
        
        .contract-tracking {
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin: 12px 0;
        }
        
        .tracking-checkbox {
            display: flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
            font-size: 1rem;
        }
        
        .tracking-checkbox input[type="checkbox"] {
            width: 20px;
            height: 20px;
            cursor: pointer;
        }
        
        .replacement-section {
            margin-top: 12px;
            padding: 12px;
            background: #fef2f2;
            border-radius: 8px;
            border: 2px solid #fca5a5;
        }
        
        .replacement-input {
            width: 100%;
            padding: 10px 12px;
            border: 2px solid #d4d4d4;
            border-radius: 8px;
            font-size: 1rem;
            margin-top: 8px;
        }
        
        .replacement-input:focus {
            outline: none;
            border-color: #333333;
        }
        
        /* ===========================================
           CONFIRMATION MODAL (UX Improvement #1)
           =========================================== */
        .confirm-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.6);
            z-index: 3000;
            align-items: center;
            justify-content: center;
        }
        
        .confirm-modal.show {
            display: flex;
        }
        
        .confirm-modal-content {
            background: var(--color-white);
            padding: var(--space-xl);
            border-radius: var(--radius-lg);
            width: 90%;
            max-width: 400px;
            text-align: center;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            animation: modalPop 0.2s ease-out;
        }
        
        @keyframes modalPop {
            from { transform: scale(0.9); opacity: 0; }
            to { transform: scale(1); opacity: 1; }
        }
        
        .confirm-modal-icon {
            font-size: 4rem;
            margin-bottom: var(--space-md);
        }
        
        .confirm-modal h3 {
            font-size: var(--font-size-xl);
            margin-bottom: var(--space-sm);
            color: var(--color-black);
        }
        
        .confirm-modal p {
            font-size: var(--font-size-base);
            color: var(--color-neutral);
            margin-bottom: var(--space-lg);
        }
        
        .confirm-modal-buttons {
            display: flex;
            gap: var(--space-md);
        }
        
        .confirm-modal-buttons button {
            flex: 1;
            min-height: var(--touch-target-lg);
            font-size: var(--font-size-base);
            font-weight: 700;
            border-radius: var(--radius-md);
            cursor: pointer;
            border: 3px solid;
        }
        
        .confirm-modal .btn-cancel {
            background: var(--color-white);
            color: var(--color-neutral);
            border-color: var(--color-border);
        }
        
        .confirm-modal .btn-confirm-paid {
            background: var(--color-primary);
            color: var(--color-white);
            border-color: var(--color-primary);
        }
        
        .confirm-modal .btn-confirm-unpaid {
            background: var(--color-danger);
            color: var(--color-white);
            border-color: var(--color-danger);
        }
        
        /* ===========================================
           PROPERTY FILTER TABS (UX Improvement #3)
           =========================================== */
        .property-filter-tabs {
            display: flex;
            gap: 8px;
            margin-bottom: var(--space-lg);
            overflow-x: auto;
            padding: 4px;
            -webkit-overflow-scrolling: touch;
            position: relative;
            z-index: 100;
            background: #F5F5F5;
            border-radius: 12px;
        }
        
        .property-filter-tab {
            flex-shrink: 0;
            padding: 12px 20px;
            border-radius: 8px;
            border: none;
            background: transparent;
            color: var(--color-neutral);
            font-size: 0.9rem;
            font-weight: 700;
            cursor: pointer !important;
            transition: all 0.2s;
            min-height: var(--touch-target-min);
            white-space: nowrap;
            position: relative;
            z-index: 101;
            pointer-events: auto !important;
        }
        
        .property-filter-tab:hover {
            background: rgba(0, 0, 0, 0.05);
        }
        
        .property-filter-tab.active {
            background: var(--color-primary);
            color: var(--color-white);
        }
        
        .property-filter-tab .tab-count {
            display: inline-block;
            margin-left: var(--space-xs);
            padding: 2px 8px;
            border-radius: var(--radius-full);
            font-size: var(--font-size-xs);
            background: rgba(255,255,255,0.3);
        }
        
        .property-filter-tab.active .tab-count {
            background: rgba(255,255,255,0.3);
        }
        
        .property-filter-tab:not(.active) .tab-count {
            background: rgba(0, 0, 0, 0.1);
        }
        
        /* ===========================================
           PHONE VALIDATION PREVIEW (UX Improvement #5)
           =========================================== */
        .phone-preview {
            margin-top: var(--space-sm);
            padding: var(--space-md);
            border-radius: var(--radius-sm);
            font-size: var(--font-size-sm);
            display: none;
        }
        
        .phone-preview.valid {
            display: block;
            background: #dcfce7;
            color: var(--color-primary);
            border: 2px solid var(--color-primary);
        }
        
        .phone-preview.invalid {
            display: block;
            background: #fee2e2;
            color: var(--color-danger);
            border: 2px solid var(--color-danger);
        }
        
        .phone-preview .preview-label {
            font-weight: 700;
            margin-bottom: 4px;
        }
        
        .phone-preview .preview-number {
            font-size: var(--font-size-lg);
            font-weight: 800;
            font-family: monospace;
        }
        
        /* ===========================================
           LOADING SPINNER (UX Improvement #2)
           =========================================== */
        .loading-spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top-color: white;
            animation: spin 0.8s linear infinite;
            margin-right: 8px;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .btn-loading {
            opacity: 0.8;
            pointer-events: none;
        }
        
        /* Enhanced toast with types */
        .undo-toast.success {
            background: var(--color-primary);
        }
        
        .undo-toast.error {
            background: var(--color-danger);
        }
        
        .undo-toast.warning {
            background: #f59e0b;
        }
        
        /* ===========================================
           PRINT STYLES (UX Improvement #13) - Enhanced with page headers
           =========================================== */
        @media print {
            /* Hide non-essential elements */
            .bottom-nav,
            .top-navbar,
            .nav-tabs,
            .search-section,
            .send-section,
            .view-toggle,
            .view-toggle-btn,
            .view-segmented-control,
            .controls,
            .btn-primary,
            .btn-secondary,
            .whatsapp-inline-btn,
            .tenant-status-btn,
            .tenant-status-btn-table,
            .add-phone-btn,
            .edit-phone-btn,
            .test-mode-banner,
            .offline-banner,
            .undo-toast,
            .confetti-container,
            .celebration-banner,
            .phone-modal,
            .confirm-modal,
            .property-filter-tabs,
            #scrollIndicatorRight,
            details,
            #lastSaved {
                display: none !important;
            }
            
            /* Reset body styles */
            body {
                background: white !important;
                padding: 0 !important;
                font-size: 12pt !important;
                color: black !important;
            }
            
            /* Make header simpler */
            header {
                box-shadow: none !important;
                border-bottom: 2px solid #333 !important;
                margin-bottom: 20pt !important;
                padding: 10pt !important;
            }
            
            h1 {
                font-size: 18pt !important;
                margin-bottom: 5pt !important;
            }
            
            .subtitle {
                font-size: 12pt !important;
            }
            
            /* Month display */
            .date-month-year {
                font-size: 14pt !important;
            }
            
            /* Property sections */
            .property-section {
                page-break-inside: avoid;
                box-shadow: none !important;
                border: 2px solid #333 !important;
                margin-bottom: 15pt !important;
            }
            
            .property-header {
                background: #f0f0f0 !important;
                color: black !important;
                padding: 8pt !important;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }
            
            /* Tenant items */
            .tenant-item {
                padding: 8pt !important;
                border-bottom: 1px solid #ccc !important;
                border-left: 4px solid !important;
                page-break-inside: avoid;
            }
            
            .tenant-item.paid {
                border-left-color: #0A7A0A !important;
            }
            
            .tenant-item:not(.paid) {
                border-left-color: #CC0000 !important;
            }
            
            .tenant-name {
                font-size: 11pt !important;
            }
            
            .tenant-rent {
                font-size: 12pt !important;
                border: none !important;
                background: none !important;
                padding: 0 !important;
            }
            
            /* Status indicator for print */
            .tenant-item::after {
                content: "PENDIENTE";
                font-weight: bold;
                color: #CC0000;
                float: right;
            }
            
            .tenant-item.paid::after {
                content: "PAGADO";
                color: #0A7A0A;
            }
            
            /* Progress bar */
            .progress-bar-container {
                background: #f0f0f0 !important;
                padding: 10pt !important;
                border: 2px solid #333 !important;
            }
            
            /* Grand totals */
            .grand-total {
                background: #f0f0f0 !important;
                color: black !important;
                border: 2px solid #333 !important;
            }
            
            /* Falta cobrar banner */
            #faltaCobrarTop,
            [style*="background: #CC0000"] {
                background: white !important;
                color: black !important;
                border: 3px solid #CC0000 !important;
            }
            
            /* Excel view - preferred for printing */
            .excel-view {
                display: block !important;
            }
            
            .card-view {
                display: none !important;
            }
            
            .excel-table {
                width: 100% !important;
                border-collapse: collapse !important;
            }
            
            .excel-table th,
            .excel-table td {
                border: 1px solid #333 !important;
                padding: 6pt !important;
                font-size: 10pt !important;
            }
            
            .excel-table th {
                background: #e0e0e0 !important;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }
            
            /* Excel property section headers */
            .excel-property-section {
                page-break-inside: avoid;
            }
            
            /* Print header and footer */
            @page {
                margin: 1.5cm;
                @top-center {
                    content: "RentasClaras - Reporte de Cobranza";
                    font-size: 10pt;
                    color: #666;
                }
                @bottom-right {
                    content: "Página " counter(page) " de " counter(pages);
                    font-size: 9pt;
                    color: #666;
                }
            }
            
            /* Print title header */
            .container::before {
                content: "";
                display: block;
            }
            
            /* Print footer with date */
            .container::after {
                content: "Impreso el " attr(data-print-date) " | RentasClaras";
                display: block;
                text-align: center;
                font-size: 9pt;
                color: #666;
                margin-top: 20pt;
                padding-top: 10pt;
                border-top: 1px solid #ccc;
            }
        }
    </style>
</head>
<body>
    <div class="container">
    <header>
            <h1>RentasClaras</h1>
              
            <!-- NAVBAR - Pagos y Contratos -->
            <nav class="top-navbar">
                <a href="/" class="top-navbar-item active">
                    <span>Pagos</span>
                </a>
                <a href="/contratos" class="top-navbar-item">
                    <span>Contratos</span>
                </a>
            </nav>
              
<p class="subtitle" style="font-size: 1.3rem; font-weight: 700; color: #000;">¿Quién ya pagó este mes?</p>
            
            <!-- Sync Indicator - Shows last save time -->
            <div id="sync-indicator" class="sync-indicator synced">
                <span class="sync-icon">✓</span>
                <span id="sync-text">{% if last_sync %}Guardado {{ last_sync_relative }}{% else %}Sin cambios aún{% endif %}</span>
            </div>
            
            <!-- Month Selector with SVG arrows and integrated Hoy button -->
            <div style="display: flex; flex-direction: column; align-items: center; gap: 12px; margin: 24px 0;">
                <div style="display: flex; align-items: center; justify-content: center; gap: 20px;">
                    {% if can_go_prev %}
                    <a href="/?year={{ prev_year }}&month={{ prev_month }}" 
                       style="background: #333333; color: white; width: 72px; height: 72px; border-radius: 50%; display: flex; align-items: center; justify-content: center; text-decoration: none; box-shadow: 0 4px 12px rgba(0,0,0,0.2); transition: all 0.2s;"
                       onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="15 18 9 12 15 6"></polyline>
                        </svg>
                    </a>
                    {% else %}
                    <div style="background: #E5E5E5; color: #999999; width: 72px; height: 72px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: not-allowed;">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="15 18 9 12 15 6"></polyline>
                        </svg>
                    </div>
                    {% endif %}
                    <div style="text-align: center; min-width: 180px;">
                        <div style="font-size: 2.2rem; font-weight: 800; color: #000; text-transform: capitalize; line-height: 1.2;">{{ month_name }}</div>
                        <div style="font-size: 1.3rem; font-weight: 700; color: #333333;">{{ year }}</div>
                    </div>
                    <a href="/?year={{ next_year }}&month={{ next_month }}" 
                       style="background: #333333; color: white; width: 72px; height: 72px; border-radius: 50%; display: flex; align-items: center; justify-content: center; text-decoration: none; box-shadow: 0 4px 12px rgba(0,0,0,0.2); transition: all 0.2s;"
                       onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="9 18 15 12 9 6"></polyline>
                        </svg>
                    </a>
                </div>
                <!-- Integrated Hoy button - only shown when not in current month -->
                {% if not is_current_month %}
                <a href="/" style="display: inline-flex; align-items: center; gap: 8px; padding: 12px 28px; background: #0A7A0A; color: white; border-radius: 24px; font-size: 1.1rem; font-weight: 700; text-decoration: none; box-shadow: 0 2px 8px rgba(10, 122, 10, 0.3); transition: all 0.2s;"
                   onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='translateY(0)'">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                        <line x1="16" y1="2" x2="16" y2="6"></line>
                        <line x1="8" y1="2" x2="8" y2="6"></line>
                        <line x1="3" y1="10" x2="21" y2="10"></line>
                    </svg>
                    Ir a Hoy
                </a>
                {% endif %}
            </div>
        </header>
        
        <!-- CONTRACT EXPIRY ALERT BANNER - Proactive reminder for landlord -->
        {% if expiring_contracts|length > 0 %}
        <div style="background: white; border-radius: 16px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); overflow: hidden;">
            <!-- Banner header with count -->
            <a href="/contratos" style="display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; text-decoration: none;
                       {% if expiring_expired|length > 0 or expiring_critical|length > 0 %}
                       background: linear-gradient(135deg, #CC0000 0%, #990000 100%); color: white;
                       {% elif expiring_warning|length > 0 %}
                       background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%); color: white;
                       {% else %}
                       background: #F5F5F5; color: #333;
                       {% endif %}
                       ">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                        <line x1="16" y1="2" x2="16" y2="6"></line>
                        <line x1="8" y1="2" x2="8" y2="6"></line>
                        <line x1="3" y1="10" x2="21" y2="10"></line>
                        <circle cx="12" cy="16" r="2" fill="currentColor"/>
                    </svg>
                    <div>
                        <div style="font-size: 1.1rem; font-weight: 800;">
                            {% if expiring_expired|length > 0 %}
                            {{ expiring_expired|length }} contrato(s) VENCIDO(S)
                            {% elif expiring_critical|length > 0 %}
                            {{ expiring_critical|length }} contrato(s) vence(n) en menos de 2 semanas
                            {% elif expiring_warning|length > 0 %}
                            {{ expiring_warning|length }} contrato(s) vence(n) este mes
                            {% else %}
                            {{ expiring_contracts|length }} contrato(s) próximo(s) a vencer
                            {% endif %}
                        </div>
                        <div style="font-size: 0.9rem; opacity: 0.9; margin-top: 2px;">Toca para ver detalles en Contratos</div>
                    </div>
                </div>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="9 18 15 12 9 6"></polyline>
                </svg>
            </a>
            
            <!-- Quick preview of most urgent contracts (max 3) -->
            <div style="padding: 0 16px 16px 16px;">
                {% for contract in expiring_contracts[:3] %}
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; margin-top: 8px; border-radius: 10px;
                            {% if contract.urgency == 'expired' %}
                            background: #FEE2E2; border-left: 4px solid #CC0000;
                            {% elif contract.urgency == 'critical' %}
                            background: #FEF3C7; border-left: 4px solid #F59E0B;
                            {% elif contract.urgency == 'warning' %}
                            background: #FEF9C3; border-left: 4px solid #EAB308;
                            {% else %}
                            background: #F5F5F5; border-left: 4px solid #666;
                            {% endif %}
                            ">
                    <div>
                        <div style="font-weight: 700; font-size: 1rem; color: #333;">{{ contract.name }}</div>
                        <div style="font-size: 0.9rem; color: #666;">{{ contract.property_name }} ({{ contract.unit }})</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-weight: 800; font-size: 1rem;
                                    {% if contract.urgency == 'expired' %}color: #CC0000;
                                    {% elif contract.urgency == 'critical' %}color: #B45309;
                                    {% elif contract.urgency == 'warning' %}color: #A16207;
                                    {% else %}color: #666;{% endif %}">
                            {% if contract.days_until_expiry < 0 %}
                            ¡Venció hace {{ -contract.days_until_expiry }} día(s)!
                            {% elif contract.days_until_expiry == 0 %}
                            ¡Vence HOY!
                            {% elif contract.days_until_expiry == 1 %}
                            Vence mañana
                            {% else %}
                            {{ contract.days_until_expiry }} días
                            {% endif %}
                        </div>
                        <div style="font-size: 0.85rem; color: #888;">{{ contract.contract_end_formatted }}</div>
                    </div>
                </div>
                {% endfor %}
                {% set displayed_count = [expiring_contracts[:3]|length, 3]|min %}
                {% if expiring_expired|length > 0 %}
                    {% set banner_total = expiring_expired|length %}
                {% elif expiring_critical|length > 0 %}
                    {% set banner_total = expiring_critical|length %}
                {% elif expiring_warning|length > 0 %}
                    {% set banner_total = expiring_warning|length %}
                {% else %}
                    {% set banner_total = expiring_contracts|length %}
                {% endif %}
                {% set remaining = banner_total - displayed_count %}
                {% if remaining > 0 %}
                <div style="text-align: center; padding: 12px; margin-top: 8px;">
                    <a href="/contratos" style="color: #0A7A0A; font-weight: 700; text-decoration: none;">
                        Ver {{ remaining }} más →
                    </a>
                </div>
                {% endif %}
            </div>
        </div>
        {% endif %}
        
        <!-- #8: FALTA COBRAR moved to TOP - Shows RENT total + multas -->
        <div style="background: white; border: 4px solid #CC0000; padding: 20px; border-radius: 16px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                <div style="font-size: 0.9rem; font-weight: 600; color: #666;">Rentas por cobrar:</div>
                <div style="font-size: 1.8rem; font-weight: 800; color: #CC0000;" id="faltaCobrarTop">${{ "{:,.0f}".format(total_owed - total_late_fees) }} MXN</div>
            </div>
            {% if total_late_fees > 0 %}
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-top: 8px; padding-top: 8px; border-top: 1px dashed #ddd;">
                <div style="font-size: 0.9rem; font-weight: 600; color: #666;">Multas acumuladas:</div>
                <div style="font-size: 1.4rem; font-weight: 700; color: #E65100;" id="multasTop">${{ "{:,.0f}".format(total_late_fees) }} MXN</div>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-top: 8px; padding-top: 8px; border-top: 1px solid #CC0000;">
                <div style="font-size: 0.9rem; font-weight: 700; color: #333;">TOTAL A COBRAR:</div>
                <div style="font-size: 1.6rem; font-weight: 800; color: #CC0000;">${{ "{:,.0f}".format(total_owed) }} MXN</div>
            </div>
            {% endif %}
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px;">
                <div style="font-size: 0.9rem; color: #666;" id="faltaPersonasTop">{{ unpaid_count }} inquilino{% if unpaid_count != 1 %}s{% endif %} pendiente{% if unpaid_count != 1 %}s{% endif %}</div>
                <div style="font-size: 0.75rem; color: #999;">{{ now.strftime('%d %b, %H:%M') }}</div>
            </div>
        </div>
        
        {% if test_mode %}
        <div class="test-mode-banner">
            MODO PRUEBA — Los mensajes irán a tu número {{ test_phone }}, no a los inquilinos.
        </div>
        {% endif %}
        
        <!-- Hidden counters for JavaScript updates (summary cards removed per UX feedback - info redundant with top banner) -->
        <div style="display: none;">
            <span id="totalTenants">{{ total_tenants }}</span>
            <span id="pendingCount">{{ total_tenants }}</span>
            <span id="paidCount">0</span>
            <span id="grandTotalExpected">${{ "{:,.0f}".format(total_rent) }} MXN</span>
            <span id="grandTotalPending">${{ "{:,.0f}".format(total_rent) }} MXN</span>
            <span id="grandTotalPaid">$0 MXN</span>
            <span id="collectionRate">0% cobrado</span>
            {% for property_name, tenants in tenants_by_property.items() %}
            <span data-subtotal-paid="{{ property_name }}">0 pagados</span>
            <span data-subtotal-pending="{{ property_name }}">{{ tenants|length }} pendientes</span>
            {% endfor %}
        </div>
        
        <!-- Progress Bar - NOW AT TOP for visibility, #11 CONFETTI ADDED -->
        <div class="progress-bar-container" style="background: #0A7A0A; padding: 20px; border-radius: 16px; margin-bottom: 24px;">
            <div class="progress-bar-label" style="color: white;">
                <span style="font-size: 1.2rem;">Cobrado este mes</span>
                <span id="collectionPercentage" style="font-size: 1.4rem; font-weight: 800;">0%</span>
            </div>
            <div class="progress-bar-track">
                <div class="progress-bar-fill" id="collectionProgressBar" style="width: 0%;">
                    <span class="progress-bar-text" id="collectionProgressText"></span>
                </div>
            </div>
        </div>

        <!-- PROMINENT SEARCH BAR - Big, colorful, impossible to miss on small phones -->
        <div class="prominent-search-section" id="stickySearch">
            <!-- Label above search -->
            <div class="prominent-search-label">
                ¿Quién pagó? Escribe su nombre:
            </div>
            <div class="search-wrapper">
                <input type="text" 
                       id="tenantSearch" 
                       class="search-input-styled prominent-search-input" 
                       placeholder="Ej: Claudia, Juan, María...">
                <button type="button" 
                        id="clearSearch" 
                        class="search-clear-btn prominent-search-clear"
                        onclick="clearSearchStandalone()">
                    ✕
                </button>
            </div>
            <div id="searchResults" class="prominent-search-results"></div>
        </div>
        
        <!-- STANDALONE SEARCH SCRIPT - Independent of main script -->
        <script>
        (function() {
            var searchInput = document.getElementById('tenantSearch');
            var clearBtn = document.getElementById('clearSearch');
            var resultsDiv = document.getElementById('searchResults');
            
            if (searchInput) {
                searchInput.addEventListener('input', function(e) {
                    var term = (e.target.value || '').toLowerCase().trim();
                    
                    // Show/hide clear button using class toggle
                    if (clearBtn) {
                        if (term) {
                            clearBtn.classList.add('visible');
                        } else {
                            clearBtn.classList.remove('visible');
                        }
                    }
                    
                    // Get all tenant items (card view)
                    var allItems = document.querySelectorAll('.tenant-item');
                    var allSections = document.querySelectorAll('.property-section');
                    
                    // Get all excel rows
                    var allRows = document.querySelectorAll('.excel-table tbody tr');
                    
                    if (!term) {
                        // Show all
                        allItems.forEach(function(item) { item.style.display = 'flex'; });
                        allSections.forEach(function(section) { section.style.display = 'block'; });
                        allRows.forEach(function(row) { row.style.display = ''; });
                        var excelSections = document.querySelectorAll('.excel-property-section');
                        excelSections.forEach(function(section) { section.style.display = 'block'; });
                        if (resultsDiv) resultsDiv.style.display = 'none';
                        return;
                    }
                    
                    var matchCount = 0;
                    var propertyVisibility = {};
                    
                    // Filter card view
                    allItems.forEach(function(item) {
                        var checkbox = item.querySelector('.tenant-checkbox');
                        if (!checkbox) return;
                        var name = (checkbox.dataset.name || '').toLowerCase();
                        var property = checkbox.dataset.property;
                        
                        if (name.indexOf(term) !== -1) {
                            item.style.display = 'flex';
                            matchCount++;
                            propertyVisibility[property] = true;
                        } else {
                            item.style.display = 'none';
                        }
                    });
                    
                    // Filter excel view
                    allRows.forEach(function(row) {
                        var nameCell = row.querySelector('td:nth-child(2)');
                        if (!nameCell) return;
                        var name = nameCell.textContent.toLowerCase();
                        
                        if (name.indexOf(term) !== -1) {
                            row.style.display = '';
                        } else {
                            row.style.display = 'none';
                        }
                    });
                    
                    // Hide empty property sections (card view)
                    allSections.forEach(function(section) {
                        var propertyName = section.dataset.property;
                        section.style.display = propertyVisibility[propertyName] ? 'block' : 'none';
                    });
                    
                    // Hide empty Excel sections
                    var excelPropertySections = document.querySelectorAll('.excel-property-section');
                    excelPropertySections.forEach(function(section) {
                        var visibleRows = section.querySelectorAll('tr[data-tenant-id]');
                        var hasVisible = false;
                        visibleRows.forEach(function(row) {
                            if (row.style.display !== 'none') {
                                hasVisible = true;
                            }
                        });
                        section.style.display = hasVisible ? 'block' : 'none';
                    });
                    
                    // Show results count
                    if (resultsDiv) {
                        resultsDiv.style.display = 'block';
                        if (matchCount === 0) {
                            resultsDiv.innerHTML = 'No se encontró "' + e.target.value + '"';
                        } else if (matchCount === 1) {
                            resultsDiv.innerHTML = '1 inquilino encontrado';
                        } else {
                            resultsDiv.innerHTML = matchCount + ' inquilinos encontrados';
                        }
                    }
                });
            }
            
            // Clear search function
            window.clearSearchStandalone = function() {
                if (searchInput) {
                    searchInput.value = '';
                    searchInput.dispatchEvent(new Event('input'));
                    searchInput.focus();
                }
            };
        })();
        </script>
        
        <!-- Property Filter Tabs with scroll indicator -->
        <div style="position: relative; margin-bottom: 24px;">
            <div class="property-filter-tabs" id="propertyFilterTabs" style="display: flex; gap: 8px; overflow-x: auto; padding: 4px; -webkit-overflow-scrolling: touch; position: relative; z-index: 10; background: #F5F5F5; border-radius: 12px; scroll-behavior: smooth;">
                <button type="button" class="property-filter-tab active" data-filter="all" onclick="filterByProperty('all', this)" style="flex-shrink: 0; padding: 12px 20px; border-radius: 8px; border: none; background: #0A7A0A; color: white; font-size: 0.9rem; font-weight: 700; cursor: pointer; transition: all 0.2s; min-height: 48px; white-space: nowrap; position: relative; z-index: 11;">
                    Todas <span class="tab-count" id="tabCountAll" style="background: rgba(255,255,255,0.3); padding: 2px 10px; border-radius: 12px; margin-left: 6px;">{{ total_tenants }}</span>
                </button>
                {% for property_name, tenants in tenants_by_property.items() %}
                <button type="button" class="property-filter-tab" data-filter="{{ property_name }}" onclick="filterByProperty('{{ property_name }}', this)" style="flex-shrink: 0; padding: 12px 20px; border-radius: 8px; border: none; background: transparent; color: #333333; font-size: 0.9rem; font-weight: 700; cursor: pointer; transition: all 0.2s; min-height: 48px; white-space: nowrap; position: relative; z-index: 11;">
                    {{ property_name }} <span class="tab-count" data-tab-count="{{ property_name }}" style="background: rgba(0,0,0,0.1); padding: 2px 10px; border-radius: 12px; margin-left: 6px;">{{ tenants|length }}</span>
                </button>
                {% endfor %}
            </div>
            <!-- Scroll indicator arrow (visible when content overflows) -->
            <div id="scrollIndicatorRight" class="scroll-indicator-arrow" style="position: absolute; right: 0; top: 0; bottom: 0; width: 48px; background: linear-gradient(90deg, transparent, rgba(245,245,245,0.95)); display: flex; align-items: center; justify-content: center; pointer-events: none; border-radius: 0 12px 12px 0;">
                <span style="font-size: 1.5rem; color: #666; animation: pulseArrow 1.5s infinite;">›</span>
            </div>
            <!-- First-time "Desliza" tooltip -->
            <div id="deslizaTooltipPagos" class="desliza-tooltip" style="display: none; position: absolute; right: 8px; top: -32px; background: #333; color: white; padding: 6px 12px; border-radius: 8px; font-size: 0.8rem; font-weight: 600; white-space: nowrap; box-shadow: 0 2px 8px rgba(0,0,0,0.2); z-index: 1000;">
                Desliza para ver mas
                <div style="position: absolute; bottom: -6px; right: 16px; width: 0; height: 0; border-left: 6px solid transparent; border-right: 6px solid transparent; border-top: 6px solid #333;"></div>
            </div>
            <style>
                @keyframes pulseArrow {
                    0%, 100% { opacity: 0.5; transform: translateX(0); }
                    50% { opacity: 1; transform: translateX(4px); }
                }
            </style>
            <script>
                // Hide scroll indicator if tabs don't overflow + show desliza tooltip
                (function() {
                    var tabs = document.getElementById('propertyFilterTabs');
                    var indicator = document.getElementById('scrollIndicatorRight');
                    var tooltip = document.getElementById('deslizaTooltipPagos');
                    var tooltipKey = 'rentasclaras_desliza_shown_pagos';
                    
                    if (tabs && indicator) {
                        function checkScroll() {
                            var isOverflowing = tabs.scrollWidth > tabs.clientWidth;
                            var isScrolledToEnd = tabs.scrollLeft + tabs.clientWidth >= tabs.scrollWidth - 10;
                            indicator.style.display = (isOverflowing && !isScrolledToEnd) ? 'flex' : 'none';
                            
                            // Show tooltip only once if overflowing and not seen before
                            if (isOverflowing && tooltip && !localStorage.getItem(tooltipKey)) {
                                tooltip.style.display = 'block';
                                setTimeout(function() {
                                    tooltip.style.display = 'none';
                                    localStorage.setItem(tooltipKey, 'true');
                                }, 4000);
                            }
                            
                            // Hide tooltip once user scrolls
                            if (tabs.scrollLeft > 20 && tooltip) {
                                tooltip.style.display = 'none';
                                localStorage.setItem(tooltipKey, 'true');
                            }
                        }
                        checkScroll();
                        tabs.addEventListener('scroll', checkScroll);
                        window.addEventListener('resize', checkScroll);
                    }
                })();
            </script>
        </div>
        
        <!-- Bulk actions - visible buttons with clear warning styling -->
        <div style="margin-bottom: 24px; padding: 20px; background: #FAFAFA; border-radius: 16px; border: 2px solid #E5E5E5;">
            <div style="font-weight: 700; color: #666; font-size: 1rem; margin-bottom: 12px; text-align: center;">
                Acciones para los {{ total_tenants }} inquilinos
            </div>
            <div style="display: flex; gap: 12px; flex-wrap: wrap; justify-content: center;">
                <button type="button" onclick="confirmMarkAllUnpaid()" 
                        style="flex: 1; min-width: 180px; max-width: 280px; padding: 16px 24px; background: white; color: #CC0000; border: 3px solid #CC0000; border-radius: 12px; font-size: 1.1rem; font-weight: 700; cursor: pointer; min-height: 56px; display: flex; align-items: center; justify-content: center; gap: 8px;">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 6L6 18M6 6l12 12"/></svg>
                    Todos pendientes
                </button>
                <button type="button" onclick="confirmMarkAllPaid()" 
                        style="flex: 1; min-width: 180px; max-width: 280px; padding: 16px 24px; background: white; color: #0A7A0A; border: 3px solid #0A7A0A; border-radius: 12px; font-size: 1.1rem; font-weight: 700; cursor: pointer; min-height: 56px; display: flex; align-items: center; justify-content: center; gap: 8px;">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                    Todos pagados
                </button>
            </div>
        </div>
        
          
        <!-- Offline Banner -->
        <div class="offline-banner" id="offlineBanner" style="display:none;">
            Sin conexión a internet. Los cambios se guardarán cuando regrese.
        </div>
        
        <!-- Toast -->
        <div class="undo-toast" id="undoToast">
            <span id="undoMessage">Guardado</span>
        </div>

        <!-- VIEW TOGGLE - Clear segmented buttons (better for 60+ users than toggle switch) -->
        <div class="view-segmented-control" style="display: flex; justify-content: center; margin-bottom: 20px;">
            <div style="display: inline-flex; background: #F5F5F5; border-radius: 12px; padding: 4px; gap: 4px;">
                <button type="button" id="cardViewBtn" onclick="switchToCardView()" 
                        style="padding: 14px 28px; border-radius: 10px; border: none; font-size: 1.1rem; font-weight: 700; cursor: pointer; min-height: 52px; transition: all 0.2s; background: transparent; color: #666;">
                    Tarjetas
                </button>
                <button type="button" id="tableViewBtn" onclick="switchToTableView()" 
                        style="padding: 14px 28px; border-radius: 10px; border: none; font-size: 1.1rem; font-weight: 700; cursor: pointer; min-height: 52px; transition: all 0.2s; background: #0A7A0A; color: white; box-shadow: 0 2px 8px rgba(10, 122, 10, 0.3);">
                    Tabla
                </button>
            </div>
        </div>
        <!-- Hidden checkbox for backwards compatibility -->
        <input type="checkbox" id="viewToggle" style="display: none;" checked>

        <!-- CARD VIEW (hidden by default - TABLE is default for Excel users) -->
        <div class="card-view" id="cardView" style="display: none;">
        {% for property_name, tenants in tenants_by_property.items() %}
        {% set property_total = tenants|sum(attribute='rent') %}
        <div class="property-section" data-property="{{ property_name }}" data-property-total="{{ property_total }}">
            <div class="property-header">
                <span>{{ property_name }}</span>
                <div class="property-stats">
                    <span class="property-pending-count" data-property-pending="{{ property_name }}">{{ tenants|length }} pendientes</span>
                    <span class="property-paid-count" data-property-paid="{{ property_name }}">0 pagaron</span>
                </div>
            </div>
            <!-- Property Subtotal Row -->
            <div class="property-subtotal-row" style="background: #f5f5f5; padding: 12px 16px; border-radius: 8px; margin: 8px 0 12px 0; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; border: 2px solid #e0e0e0;">
                <div style="display: flex; gap: 16px; flex-wrap: wrap; align-items: center;">
                    <span style="font-weight: 700; color: #333;">Subtotal:</span>
                    <span class="property-subtotal-expected" data-subtotal-expected="{{ property_name }}" style="font-weight: 600; color: #333;">${{ "{:,.0f}".format(property_total) }} esperados</span>
                </div>
                <div style="display: flex; gap: 16px; flex-wrap: wrap; align-items: center;">
                    <span class="property-subtotal-paid" data-subtotal-amount-paid="{{ property_name }}" style="font-weight: 700; color: #0A7A0A; background: #dcfce7; padding: 4px 12px; border-radius: 6px;">$0 cobrados</span>
                    <span class="property-subtotal-pending" data-subtotal-amount-pending="{{ property_name }}" style="font-weight: 700; color: #CC0000; background: #FEE2E2; padding: 4px 12px; border-radius: 6px;">${{ "{:,.0f}".format(property_total) }} pendientes</span>
                </div>
            </div>
            <div class="tenant-list">
                {% for tenant in tenants %}
                <div class="tenant-item {% if tenant.paid %}paid{% endif %}" data-property="{{ property_name }}" data-tenant-id="{{ tenant.id }}">
                    <input type="checkbox" class="tenant-checkbox" 
                           id="tenant-{{ tenant.id }}" 
                           data-id="{{ tenant.id }}"
                           data-name="{{ tenant.name }}"
                           data-phone="{{ tenant.phone }}"
                           data-property="{{ property_name }}"
                           {% if not tenant.paid %}checked{% endif %}>
                    
                    <div class="tenant-main-info">
                        <!-- 1. NAME at the top -->
                        <div class="tenant-name">
                            <span class="tenant-unit">({{ tenant.unit }})</span> {{ tenant.name }}
                        </div>
                        
                        <!-- 2. PHONE NUMBER -->
                        <div class="tenant-phone-inline">
                            {% if tenant.phone %}
                            <a href="tel:{{ tenant.phone }}" style="color: #000; text-decoration: none;">{{ tenant.phone }}</a>
                            <button type="button" class="edit-phone-btn" onclick="editPhone('{{ tenant.id }}', '{{ tenant.phone }}')">Editar</button>
                            {% else %}
                            <div style="background: #CC0000; color: white; padding: 12px 16px; border-radius: 8px; font-weight: 700; font-size: 1rem; display: flex; align-items: center; gap: 12px; flex-wrap: wrap; position: relative; z-index: 10;">
                                <span>SIN TELÉFONO</span>
                                <button type="button" class="add-phone-btn" onclick="editPhone('{{ tenant.id }}', '')" style="background: white !important; color: #CC0000 !important; border: none; padding: 10px 20px; border-radius: 8px; font-weight: 700; cursor: pointer; min-height: 48px; position: relative; z-index: 11;">
                                    Agregar
                                </button>
                            </div>
                            {% endif %}
                        </div>
                        
                        <!-- 3. LATE FEE BANNER - Only shown for unpaid tenants with fees, hidden after day 7 -->
                        {% if not tenant.paid and tenant.days_late >= 1 and tenant.days_late <= 7 %}
                        <div style="{% if tenant.days_late >= 7 %}background: #FEE2E2; border: 2px solid #CC0000;{% else %}background: #FEF3C7; border: 2px solid #F59E0B;{% endif %} border-radius: 12px; padding: 14px 16px; margin-top: 12px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                                <div style="display: flex; align-items: center; gap: 8px;">
                                    <span style="font-size: 1.4rem;">{% if tenant.days_late >= 7 %}🚨{% else %}⏰{% endif %}</span>
                                    <span style="font-weight: 700; {% if tenant.days_late >= 7 %}color: #CC0000;{% else %}color: #92400E;{% endif %} font-size: 1rem;">{{ tenant.days_late }} día{% if tenant.days_late > 1 %}s{% endif %} de atraso{% if tenant.days_late >= 7 %} — CRÍTICO{% endif %}</span>
                                </div>
                                <div style="text-align: right;">
                                    <div style="font-size: 0.9rem; {% if tenant.days_late >= 7 %}color: #991B1B;{% else %}color: #92400E;{% endif %}">
                                        Multa: $500{% if tenant.days_late > 1 %} + {{ tenant.days_late - 1 }}×$100{% endif %} = <strong>+${{ "{:,.0f}".format(tenant.late_fee) }}</strong>
                                    </div>
                                </div>
                            </div>
                        </div>
                        {% endif %}
                    </div>
                    
                    <!-- 4. STATUS TOGGLE + 5. TOTAL AMOUNT - aligned horizontally -->
                    <div class="status-amount-row">
                        <div class="payment-toggle-container">
                            <label class="payment-toggle" data-tenant-id="{{ tenant.id }}">
                                <input type="checkbox" 
                                       {% if tenant.paid %}checked{% endif %}
                                       onchange="togglePaymentStatus(this, '{{ tenant.id }}')">
                                <span class="slider"></span>
                            </label>
                            <span class="payment-toggle-label {% if tenant.paid %}paid{% else %}unpaid{% endif %}">
                                {% if tenant.paid %}Ya pagó{% else %}No ha pagado{% endif %}
                            </span>
                        </div>
                        <div class="tenant-amount" data-base-rent="{{ tenant.rent }}">
                            <!-- Show TOTAL with late fees for unpaid, or just rent for paid -->
                            {% if not tenant.paid and tenant.late_fee > 0 %}
                            <div class="tenant-rent" style="color: #CC0000; border-color: #CC0000; background: #FEE2E2;">${{ "{:,.0f}".format(tenant.total_owed) }}</div>
                            {% else %}
                            <div class="tenant-rent">${{ "{:,.0f}".format(tenant.rent) }}</div>
                            {% endif %}
                        </div>
                    </div>
                      
                    <!-- Inline WhatsApp button with SVG icon -->
                    {% if tenant.phone and not tenant.paid %}
                    <a href="#" class="whatsapp-inline-btn" 
                       data-tenant-id="{{ tenant.id }}"
                       onclick="sendWhatsApp(event, this)"
                       style="display: inline-flex; align-items: center; gap: 10px;">
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
                        </svg>
                        Enviar WhatsApp
                    </a>
                    {% endif %}
                    
                    <!-- Simplified details section -->
                    <div class="tenant-details" data-details-for="{{ tenant.id }}">
                        {% if tenant.emergency_contact %}
                        <p><strong>Aval:</strong> {{ tenant.emergency_contact }} {% if tenant.emergency_phone %}({{ tenant.emergency_phone }}){% endif %}</p>
                        {% endif %}
                        {% if tenant.contract_start_formatted and tenant.contract_end_formatted %}
                        <p><strong>Contrato:</strong> {{ tenant.contract_start_formatted }} → {{ tenant.contract_end_formatted }}</p>
                        {% endif %}
                          
                        <div class="payment-method-row">
                            <label><strong>¿Cómo pagó?</strong></label><br>
                            <select class="payment-method" onchange="updatePaymentMethod(this)" {% if not tenant.paid %}disabled{% endif %}>
                                <option value="">— Seleccionar método —</option>
                                <option value="transferencia" {% if tenant.payment_method == 'transferencia' %}selected{% endif %}>Transferencia</option>
                                <option value="envio" {% if tenant.payment_method == 'envio' %}selected{% endif %}>Envío sin tarjeta</option>
                                <option value="deposito" {% if tenant.payment_method == 'deposito' %}selected{% endif %}>Depósito</option>
                                <option value="efectivo" {% if tenant.payment_method == 'efectivo' %}selected{% endif %}>Efectivo</option>
                            </select>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endfor %}
        </div>
        <!-- END CARD VIEW -->

        <!-- EXCEL TABLE VIEW (DEFAULT for 60+ users familiar with Excel) -->
        <div class="excel-view" id="excelView" style="display: block; overflow-x: auto;">
            {% for property_name, tenants in tenants_by_property.items() %}
            <div class="excel-property-section" style="margin-bottom: 32px;">
                <!-- Property Header - Excel style -->
                <table class="excel-table" style="margin-bottom: 0;">
                    <thead>
                        <tr>
                            <th colspan="4" style="background: white; border: none; font-size: 1.4rem; text-align: left; padding: 8px 16px;">
                                {{ property_name }}
                            </th>
                            <th colspan="4" style="background: white; border: none; font-style: italic; text-align: right;">{{ month_name }}</th>
                        </tr>
                        <tr>
                            <th style="width: 40px; text-align: center;"></th>
                            <th style="min-width: 120px;">Nombre</th>
                            <th style="text-align: right; min-width: 70px;">Renta</th>
                            <th style="text-align: right; min-width: 70px; background: #FFF3CD; color: #856404;">MULTA</th>
                            <th style="text-align: right; min-width: 80px; font-weight: 800;">TOTAL</th>
                            <th style="text-align: right; min-width: 70px;">Pagado</th>
                            <th style="text-align: center; width: 70px;">Estado</th>
                            <th style="text-align: center; width: 40px;" title="Mensajes enviados este mes">📨</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for tenant in tenants %}
                        <tr data-tenant-id="{{ tenant.id }}" data-property="{{ property_name }}" class="excel-row {% if tenant.paid %}paid-row{% else %}unpaid-row{% endif %}">
                            <td style="text-align: center; font-weight: bold;">{{ loop.index if property_name == 'Ensenada' else ['A','B','C','D','E','F','G','H','I','J'][loop.index0] if loop.index0 < 10 else loop.index }}</td>
                            <td>
                                <strong>{{ tenant.name }}</strong>
                                {% if not tenant.phone %}<span style="color: #CC0000; font-size: 0.8rem;"> ⚠️</span>{% endif %}
                            </td>
                            <td class="rent-cell" style="{% if not tenant.paid %}color: #CC0000;{% endif %}">${{ "{:,.0f}".format(tenant.rent) }}</td>
                            <!-- MULTA column -->
                            <td style="text-align: right; font-weight: 700; {% if tenant.late_fee > 0 %}color: #CC0000;{% else %}color: #666;{% endif %}">
                                {% if tenant.paid %}—{% elif tenant.late_fee > 0 %}+${{ "{:,.0f}".format(tenant.late_fee) }}{% else %}$0{% endif %}
                            </td>
                            <!-- TOTAL A COBRAR column -->
                            <td style="text-align: right; font-weight: 800; {% if not tenant.paid %}background: #FEE2E2; color: #CC0000;{% else %}color: #0A7A0A;{% endif %}">
                                {% if tenant.paid %}${{ "{:,.0f}".format(tenant.rent) }}{% else %}${{ "{:,.0f}".format(tenant.total_owed) }}{% endif %}
                            </td>
                            <td class="pagado-cell" data-tenant-id="{{ tenant.id }}" style="text-align: right; font-weight: 700; color: #0A7A0A;">
                                {% if tenant.paid %}${{ "{:,.0f}".format(tenant.rent) }}{% endif %}
                            </td>
                            <td style="text-align: center;">
                                <button type="button" class="status-pill status-pill--small tenant-status-btn-table {% if tenant.paid %}paid{% else %}unpaid{% endif %}"
                                        onclick="togglePaidTable(this, '{{ tenant.id }}')">
                                    {% if tenant.paid %}✓{% else %}{% endif %}
                                </button>
                            </td>
                            <!-- MESSAGE INDICATOR COLUMN -->
                            <td style="text-align: center; font-size: 0.85rem;">
                                {% if tenant.paid %}
                                    <span style="color: #9CA3AF;">—</span>
                                {% elif not tenant.phone %}
                                    <span style="color: #DC2626;" title="Sin teléfono">⚠️</span>
                                {% elif tenant.msg_count > 0 %}
                                    <span style="color: #059669;" title="{{ tenant.msg_count }} mensaje(s) enviado(s)">✉️{{ tenant.msg_count }}</span>
                                {% else %}
                                    <span style="color: #9CA3AF;">—</span>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                        <!-- Property Total Row -->
                        <tr style="background: #F9F9F9; font-weight: bold;">
                            <td></td>
                            <td>{{ property_name }}</td>
                            <td class="rent-cell" style="border-top: 2px solid #333;">${{ "{:,.0f}".format(tenants|sum(attribute='rent')) }}</td>
                            <td style="border-top: 2px solid #333; text-align: right; color: #CC0000;">+${{ "{:,.0f}".format(tenants|rejectattr('paid')|sum(attribute='late_fee')) }}</td>
                            <td style="border-top: 2px solid #333; text-align: right; font-weight: 800; color: #CC0000;">${{ "{:,.0f}".format(tenants|rejectattr('paid')|sum(attribute='total_owed')) }}</td>
                            <td class="property-total-paid" data-property="{{ property_name }}" style="text-align: right; color: #0A7A0A; border-top: 2px solid #333;">${{ "{:,.0f}".format(tenants|selectattr('paid')|sum(attribute='rent')) }}</td>
                            <td></td>
                            <td style="border-top: 2px solid #333;"></td>
                        </tr>
                    </tbody>
                </table>
            </div>
            {% endfor %}
            
            <!-- Grand Total Summary Section -->
            <div class="excel-property-section" style="margin-top: 24px; padding: 16px; background: #F5F5F5; border-radius: 8px;">
                <table class="excel-table" style="max-width: 500px;">
                    <tbody>
                        {% for property_name, tenants in tenants_by_property.items() %}
                        <tr>
                            <td style="padding: 8px 16px; border: none;">{{ property_name }}</td>
                            <td style="padding: 8px 16px; border: none; text-align: right;">${{ "{:,.0f}".format(tenants|sum(attribute='rent')) }}</td>
                            <td style="padding: 8px 16px; border: none; text-align: right; color: #CC0000; font-size: 0.9rem;">
                                {% if tenants|rejectattr('paid')|sum(attribute='late_fee') > 0 %}+${{ "{:,.0f}".format(tenants|rejectattr('paid')|sum(attribute='late_fee')) }}{% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                        <tr style="border-top: 3px solid #333; background: #FEE2E2;">
                            <td style="padding: 12px 16px; border: none; font-weight: 800; font-size: 1.2rem; color: #991B1B;">GRAN TOTAL:</td>
                            <td colspan="2" style="padding: 12px 16px; border: none; text-align: right; font-weight: 800; font-size: 1.3rem; color: #CC0000;">
                                ${{ "{:,.0f}".format(total_rent) }}{% if total_late_fees > 0 %} <span style="font-size: 0.85rem; font-weight: 600; color: #991B1B;">+ ${{ "{:,.0f}".format(total_late_fees) }} multas</span>{% endif %}
                            </td>
                        </tr>
                    </tbody>
            </table>
            </div>
            
            <!-- EXCEL DOWNLOAD BUTTON -->
            <div style="text-align: center; margin-top: 24px;">
                <button onclick="downloadExcel()" 
                        style="background: #217346; color: white; border: none; padding: 20px 40px; border-radius: 12px; font-size: 1.3rem; font-weight: 700; cursor: pointer; min-height: 64px; box-shadow: 0 4px 12px rgba(0,0,0,0.2); display: inline-flex; align-items: center; gap: 12px;">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M14.5 2H6C4.9 2 4 2.9 4 4V20C4 21.1 4.9 22 6 22H18C19.1 22 20 21.1 20 20V7.5L14.5 2ZM18 20H6V4H13V8H18V20ZM12.9 14.5L15.2 19H13.4L12 16.5L10.6 19H8.8L11.1 14.5L9 10H10.8L12 12.3L13.2 10H15L12.9 14.5Z"/></svg>
                    Descargar Excel
                </button>
                <p style="color: #666; font-size: 0.95rem; margin-top: 12px;">Descarga el archivo con una hoja por cada propiedad</p>
            </div>
        </div>
        <!-- END EXCEL VIEW -->

        <!-- SIMPLIFIED SEND SECTION - Single button -->
        <div class="send-section" style="background: white; padding: 32px; border-radius: 16px; text-align: center; margin-top: 32px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); position: relative; z-index: 100;">
            <div style="font-size: 1.2rem; margin-bottom: 24px; color: #000; font-weight: 700;">
                Enviar recordatorio a <strong id="selectedCount" style="color: #CC0000; font-size: 1.6rem;">{{ total_tenants }}</strong> inquilino(s) pendientes
            </div>
            
            <!-- ONE BIG BUTTON -->
            <button id="sendAllApiBtn" onclick="sendAllViaApi()" 
                    style="width: 100%; max-width: 600px; padding: 24px 32px; font-size: 1.4rem; font-weight: 700; background: #0A7A0A; color: white; border: none; border-radius: 12px; cursor: pointer; min-height: 72px; box-shadow: 0 4px 12px rgba(0,0,0,0.2); position: relative; z-index: 101;">
                Enviar a todos los pendientes
            </button>
            
            <div id="apiStatus" style="margin: 24px 0; padding: 20px; border-radius: 12px; display: none; font-size: 1.1rem;"></div>
            
            <p style="color: #666666; font-size: 1rem; margin-top: 16px;">
                Un clic = mensaje automático a cada inquilino pendiente
            </p>
            
        </div>
        
        <!-- Celebration banner at 100% -->
        <div class="confetti-container" id="confettiContainer"></div>
        <div class="celebration-banner" id="celebrationBanner">
            ¡TODOS PAGARON!
        </div>
    </div>
    
    <!-- MOBILE BOTTOM NAVIGATION - Only visible on mobile, consistent 2 items -->
    <nav class="bottom-nav">
        <a href="/" class="bottom-nav-item active">
            <span class="bottom-nav-icon" style="font-size: 1.3rem; font-weight: 700;">$</span>
            <span>Pagos</span>
        </a>
        <a href="/contratos" class="bottom-nav-item">
            <svg class="bottom-nav-icon" style="width: 24px; height: 24px;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
            <span>Contratos</span>
        </a>
    </nav>
    
    <!-- Phone Edit Modal -->
    <div class="phone-modal" id="phoneModal">
        <div class="phone-modal-content">
            <h3>Editar Teléfono</h3>
            <input type="tel" id="phoneInput" placeholder="+52 81 1234 5678" inputmode="tel" oninput="validatePhonePreview(this.value)">
            <!-- UX #5: Phone validation preview -->
            <div class="phone-preview" id="phonePreview">
                <div class="preview-label">Se guardará como:</div>
                <div class="preview-number" id="phonePreviewNumber"></div>
            </div>
            <div id="phoneError" style="display: none; color: #CC0000; font-size: 0.95rem; margin-top: 8px;"></div>
            <div class="phone-modal-buttons">
                <button class="btn-secondary" onclick="closePhoneModal()">Cancelar</button>
                <button class="btn-primary" id="savePhoneBtn" onclick="savePhone()">Guardar</button>
            </div>
        </div>
    </div>
    
    <!-- Confirmation Modal for status changes - with enhanced context -->
    <div class="confirm-modal" id="confirmModal">
        <div class="confirm-modal-content">
            <div class="confirm-modal-icon" id="confirmIcon" style="font-size: 3rem;"></div>
            <h3 id="confirmTitle">¿Confirmar cambio?</h3>
            <!-- Enhanced context section -->
            <div id="confirmContext" style="background: #F5F5F5; border-radius: 12px; padding: 16px; margin: 16px 0; text-align: left;">
                <div style="font-size: 1.2rem; font-weight: 800; color: #333; margin-bottom: 8px;" id="confirmTenantName"></div>
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                    <span style="font-size: 1.1rem; color: #666;" id="confirmMonthYear"></span>
                    <span style="font-size: 1.3rem; font-weight: 800; color: #0A7A0A;" id="confirmAmount"></span>
                </div>
            </div>
            <p id="confirmMessage" style="font-size: 1rem; color: #666;">¿Está seguro de realizar esta acción?</p>
            <div class="confirm-modal-buttons">
                <button class="btn-cancel" onclick="closeConfirmModal()">Cancelar</button>
                <button class="btn-confirm-paid" id="confirmBtn" onclick="executeConfirmedAction()">Confirmar</button>
            </div>
        </div>
    </div>
    
    <script>
        console.log('Main script starting...');
        const dayOfMonth = {{ day_of_month }};
        const currentYear = {{ year }};
        const currentMonth = {{ month }};
        const testMode = {{ 'true' if test_mode else 'false' }};
        const testPhone = "{{ test_phone }}";
        console.log('Variables initialized:', { dayOfMonth, currentYear, currentMonth, testMode });

        // #4: VIEW SWITCHING FUNCTIONS - Segmented control buttons
        function toggleView() {
            const toggle = document.getElementById('viewToggle');
            if (toggle.checked) {
                switchToTableView();
            } else {
                switchToCardView();
            }
        }

        function switchToCardView() {
            console.log('switchToCardView called');
            const cardView = document.getElementById('cardView');
            const excelView = document.getElementById('excelView');
            
            if (!cardView || !excelView) {
                console.error('View elements not found:', { cardView, excelView });
                return;
            }
            
            // Direct style manipulation - guaranteed to work
            cardView.style.display = 'block';
            excelView.style.display = 'none';
            
            // Update segmented control button states
            const cardBtn = document.getElementById('cardViewBtn');
            const tableBtn = document.getElementById('tableViewBtn');
            
            if (cardBtn) {
                cardBtn.style.background = '#0A7A0A';
                cardBtn.style.color = 'white';
                cardBtn.style.boxShadow = '0 2px 8px rgba(10, 122, 10, 0.3)';
            }
            if (tableBtn) {
                tableBtn.style.background = 'transparent';
                tableBtn.style.color = '#666';
                tableBtn.style.boxShadow = 'none';
            }
            
            // Update hidden checkbox for compatibility
            const toggle = document.getElementById('viewToggle');
            if (toggle) toggle.checked = false;
            
            localStorage.setItem('preferredView', 'card');
            console.log('Switched to card view');
        }

        function switchToTableView() {
            console.log('switchToTableView called');
            const cardView = document.getElementById('cardView');
            const excelView = document.getElementById('excelView');
            
            if (!cardView || !excelView) {
                console.error('View elements not found:', { cardView, excelView });
                return;
            }
            
            // Direct style manipulation - guaranteed to work
            cardView.style.display = 'none';
            excelView.style.display = 'block';
            
            // Update segmented control button states
            const cardBtn = document.getElementById('cardViewBtn');
            const tableBtn = document.getElementById('tableViewBtn');
            
            if (tableBtn) {
                tableBtn.style.background = '#0A7A0A';
                tableBtn.style.color = 'white';
                tableBtn.style.boxShadow = '0 2px 8px rgba(10, 122, 10, 0.3)';
            }
            if (cardBtn) {
                cardBtn.style.background = 'transparent';
                cardBtn.style.color = '#666';
                cardBtn.style.boxShadow = 'none';
            }
            
            // Update hidden checkbox for compatibility
            const toggle = document.getElementById('viewToggle');
            if (toggle) toggle.checked = true;
            
            localStorage.setItem('preferredView', 'table');
            console.log('Switched to table view');
        }

        // #4: Restore user's preferred view on page load - DEFAULT is now TABLE
        window.addEventListener('DOMContentLoaded', () => {
            const preferredView = localStorage.getItem('preferredView') || 'table';
            if (preferredView === 'card') {
                switchToCardView();
            } else {
                switchToTableView();
            }
            
            // Initialize counts and subtotals on page load
            updateCounts();
            
            // Set up search functionality
            const searchInput = document.getElementById('tenantSearch');
            if (searchInput) {
                searchInput.addEventListener('input', function(e) {
                    filterTenants(e.target.value);
                });
            }
        });

        // Toggle paid status from Excel table view
        function togglePaidTable(btn, tenantId) {
            // Find the corresponding tenant in card view
            const cardViewItem = document.querySelector(`.tenant-item[data-tenant-id="${tenantId}"]`);
            if (!cardViewItem) {
                console.error('Could not find card view item for tenant:', tenantId);
                return;
            }
            
            // Determine current state and toggle it
            const row = btn.closest('tr');
            const currentlyPaid = btn.classList.contains('paid');
            const newPaidStatus = !currentlyPaid;
            
            // Find the payment buttons in card view and trigger the appropriate one
            const paymentBtnPaid = cardViewItem.querySelector('.payment-btn[onclick*="true"]');
            const paymentBtnUnpaid = cardViewItem.querySelector('.payment-btn[onclick*="false"]');
            
            if (newPaidStatus && paymentBtnPaid) {
                // Trigger the "Ya pagó" button
                setPaymentStatus(paymentBtnPaid, tenantId, true);
            } else if (!newPaidStatus && paymentBtnUnpaid) {
                // Trigger the "No ha pagado" button
                setPaymentStatus(paymentBtnUnpaid, tenantId, false);
            } else {
                // Fallback: directly update via API
                updatePaymentDirectly(tenantId, newPaidStatus);
            }

            // Update table row appearance
            const pagadoCell = row.querySelector('.pagado-cell');
            const rentCell = row.querySelector('.rent-cell');
            const rentAmount = rentCell ? rentCell.textContent.trim() : '$0';

            if (newPaidStatus) {
                row.classList.add('paid-row');
                row.classList.remove('unpaid-row');
                btn.className = 'status-pill status-pill--small tenant-status-btn-table paid';
                btn.textContent = '✓';
                if (pagadoCell) {
                    pagadoCell.textContent = rentAmount;
                }
                if (rentCell) {
                    rentCell.style.color = '';
                }
            } else {
                row.classList.add('unpaid-row');
                row.classList.remove('paid-row');
                btn.className = 'status-pill status-pill--small tenant-status-btn-table unpaid';
                btn.textContent = '';
                if (pagadoCell) {
                    pagadoCell.textContent = '';
                }
                if (rentCell) {
                    rentCell.style.color = '#CC0000';
                }
            }
            
            // Update property totals
            updatePropertyTotals();
        }
        
        // Fallback function for direct API update when card view buttons not found
        function updatePaymentDirectly(tenantId, isPaid) {
            fetch('/api/payment', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tenant_id: tenantId, paid: isPaid })
            }).then(response => {
                if (response.ok) {
                    updateCounts();
                }
            }).catch(err => console.error('Payment update failed:', err));
        }
        
        // Update property totals when payment status changes
        function updatePropertyTotals() {
            const propertySections = document.querySelectorAll('.excel-property-section');
            propertySections.forEach(section => {
                let totalPaid = 0;
                const rows = section.querySelectorAll('tr[data-tenant-id]');
                rows.forEach(row => {
                    if (row.classList.contains('paid-row')) {
                        const rentCell = row.querySelector('.rent-cell');
                        if (rentCell) {
                            const rentText = rentCell.textContent.replace(/[$,]/g, '');
                            totalPaid += parseFloat(rentText) || 0;
                        }
                    }
                });
                const totalCell = section.querySelector('.property-total-paid');
                if (totalCell) {
                    totalCell.textContent = '$' + totalPaid.toLocaleString('en-US', {maximumFractionDigits: 0});
                }
            });
        }

        // PDF Receipt Download Function - Creates a professional PDF receipt for each tenant
        function downloadReceipt(btn) {
            const tenantId = btn.getAttribute('data-tenant-id');
            const tenantName = btn.getAttribute('data-tenant-name');
            const tenantUnit = btn.getAttribute('data-tenant-unit');
            const property = btn.getAttribute('data-property');
            const rent = btn.getAttribute('data-rent');
            const isPaid = btn.getAttribute('data-paid') === 'true';
            
            // Generate folio number (unique identifier)
            const now = new Date();
            const folio = `RC-${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}-${tenantId}`;
            
            // Format date in Spanish
            const months = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
            const dateStr = `${now.getDate()} de ${months[now.getMonth()]} de ${now.getFullYear()}`;
            const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
            
            // Current month/year for billing period
            const billingMonth = months[currentMonth - 1] + ' ' + currentYear;
            
            // Status text and color
            const statusText = isPaid ? 'PAGADO' : 'PENDIENTE';
            const statusColor = isPaid ? '#0A7A0A' : '#CC0000';
            const statusBg = isPaid ? '#DCFCE7' : '#FEE2E2';
            
            // Format rent amount
            const rentFormatted = parseFloat(rent).toLocaleString('es-MX', { style: 'currency', currency: 'MXN' });
            
            // Create PDF content using HTML and print dialog
            const pdfContent = `
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Recibo de Renta - ${tenantName}</title>
                <style>
                    * { margin: 0; padding: 0; box-sizing: border-box; }
                    body { 
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                        padding: 40px; 
                        color: #333;
                        max-width: 800px;
                        margin: 0 auto;
                    }
                    .header { 
                        text-align: center; 
                        margin-bottom: 40px;
                        border-bottom: 3px solid #0A7A0A;
                        padding-bottom: 20px;
                    }
                    .logo { 
                        font-size: 28px; 
                        font-weight: 800; 
                        color: #0A7A0A;
                        margin-bottom: 8px;
                    }
                    .subtitle { color: #666; font-size: 14px; }
                    .folio { 
                        background: #F5F5F5; 
                        padding: 12px 24px; 
                        border-radius: 8px; 
                        display: inline-block;
                        margin-top: 16px;
                        font-weight: 700;
                        font-size: 14px;
                    }
                    .status-badge {
                        display: inline-block;
                        padding: 12px 32px;
                        border-radius: 8px;
                        font-weight: 800;
                        font-size: 18px;
                        margin: 24px 0;
                        background: ${statusBg};
                        color: ${statusColor};
                        border: 3px solid ${statusColor};
                    }
                    .section { margin: 32px 0; }
                    .section-title { 
                        font-size: 14px; 
                        color: #666; 
                        text-transform: uppercase;
                        letter-spacing: 1px;
                        margin-bottom: 12px;
                    }
                    .info-grid { 
                        display: grid; 
                        grid-template-columns: 1fr 1fr; 
                        gap: 16px;
                    }
                    .info-item { 
                        background: #FAFAFA; 
                        padding: 16px; 
                        border-radius: 8px;
                        border: 1px solid #E5E5E5;
                    }
                    .info-label { font-size: 12px; color: #666; margin-bottom: 4px; }
                    .info-value { font-size: 16px; font-weight: 700; }
                    .amount-section {
                        background: #F5F5F5;
                        padding: 32px;
                        border-radius: 12px;
                        text-align: center;
                        margin: 32px 0;
                    }
                    .amount-label { font-size: 14px; color: #666; margin-bottom: 8px; }
                    .amount-value { 
                        font-size: 48px; 
                        font-weight: 800; 
                        color: ${isPaid ? '#0A7A0A' : '#CC0000'};
                    }
                    .footer {
                        margin-top: 48px;
                        padding-top: 24px;
                        border-top: 2px solid #E5E5E5;
                        text-align: center;
                        color: #999;
                        font-size: 12px;
                    }
                    .timestamp { margin-top: 8px; }
                    @media print {
                        body { padding: 20px; }
                        .no-print { display: none; }
                    }
                </style>
            </head>
            <body>
                <div class="header">
                    <div class="logo">RentasClaras</div>
                    <div class="subtitle">Sistema de Administración de Rentas</div>
                    <div class="folio">Folio: ${folio}</div>
                </div>
                
                <div style="text-align: center;">
                    <div class="status-badge">${statusText}</div>
                </div>
                
                <div class="section">
                    <div class="section-title">Datos del Inquilino</div>
                    <div class="info-grid">
                        <div class="info-item">
                            <div class="info-label">Nombre</div>
                            <div class="info-value">${tenantName}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Unidad</div>
                            <div class="info-value">${tenantUnit}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Propiedad</div>
                            <div class="info-value">${property}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Periodo</div>
                            <div class="info-value">${billingMonth}</div>
                        </div>
                    </div>
                </div>
                
                <div class="amount-section">
                    <div class="amount-label">Monto de Renta</div>
                    <div class="amount-value">${rentFormatted}</div>
                </div>
                
                <div class="footer">
                    <div>Este documento es un comprobante oficial de RentasClaras</div>
                    <div class="timestamp">Generado el ${dateStr} a las ${timeStr}</div>
                    <div style="margin-top: 16px; color: #0A7A0A; font-weight: 700;">
                        Conserve este recibo para su registro
                    </div>
                </div>
                
                <div class="no-print" style="text-align: center; margin-top: 32px;">
                    <button onclick="window.print()" style="background: #0A7A0A; color: white; border: none; padding: 16px 32px; border-radius: 8px; font-size: 16px; font-weight: 700; cursor: pointer;">
                        Imprimir / Guardar PDF
                    </button>
                </div>
            </body>
            </html>
            `;
            
            // Open in new window for printing/saving as PDF
            const printWindow = window.open('', '_blank');
            printWindow.document.write(pdfContent);
            printWindow.document.close();
        }

        // Excel Download Function - Creates multi-sheet Excel file matching user's format
        function downloadExcel() {
            // Get all tenant data from the page
            const tenantsData = {};
            const propertySections = document.querySelectorAll('.excel-property-section');
            
            // Get month/year from page
            const months = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
            const monthName = months[currentMonth - 1];
            
            propertySections.forEach(section => {
                const table = section.querySelector('.excel-table');
                if (!table) return;
                
                // Get property name from first header
                const headerRow = table.querySelector('thead tr:first-child th');
                if (!headerRow) return;
                const propertyName = headerRow.textContent.trim();
                
                // Skip the summary section
                if (propertyName === '') return;
                
                const rows = table.querySelectorAll('tbody tr[data-tenant-id]');
                if (rows.length === 0) return;
                
                tenantsData[propertyName] = [];
                
                rows.forEach((row, index) => {
                    const cells = row.querySelectorAll('td');
                    if (cells.length < 6) return;
                    
                    const name = cells[1].textContent.trim().replace('⚠️', '').trim();
                    const inicia = cells[2].textContent.trim();
                    const termina = cells[3].textContent.trim();
                    const rentText = cells[4].textContent.replace(/[$,]/g, '').trim();
                    const rent = parseFloat(rentText) || 0;
                    const pagadoText = cells[5].textContent.replace(/[$,]/g, '').trim();
                    const pagado = parseFloat(pagadoText) || 0;
                    
                    // Row label: A, B, C... for some properties, 1, 2, 3... for Ensenada
                    const rowLabel = cells[0].textContent.trim();
                    
                    tenantsData[propertyName].push({
                        label: rowLabel,
                        name: name,
                        inicia: inicia,
                        termina: termina,
                        rent: rent,
                        pagado: pagado
                    });
                });
            });
            
            // Create workbook with SheetJS
            const wb = XLSX.utils.book_new();
            let grandTotals = [];
            
            // Create a sheet for each property
            Object.keys(tenantsData).forEach(propertyName => {
                const tenants = tenantsData[propertyName];
                if (!tenants || tenants.length === 0) return;
                
                // Build sheet data matching the user's Excel format
                const sheetData = [];
                
                // Row 1: RENTAS + Year
                sheetData.push(['', 'RENTAS ' + currentYear, '', '', '', 'Por', '']);
                
                // Row 2: Property name
                sheetData.push(['', propertyName, '', '', '', 'Pagar', '']);
                
                // Row 3: Month header (right side)
                sheetData.push(['', '', '', '', '', 'Renta', 'Pagado', monthName]);
                
                // Row 4: Column headers
                sheetData.push(['', '', 'INICIA', 'TERMINA', 'Bco', 'Renta', 'Pagado', 'AVISO']);
                
                // Tenant rows
                let totalRent = 0;
                let totalPagado = 0;
                
                tenants.forEach(tenant => {
                    sheetData.push([
                        tenant.label,
                        tenant.name,
                        tenant.inicia,
                        tenant.termina,
                        '',  // Bco (bank) - empty for now
                        tenant.rent,
                        tenant.pagado || '',
                        ''  // AVISO - empty for now
                    ]);
                    totalRent += tenant.rent;
                    totalPagado += tenant.pagado || 0;
                });
                
                // Empty row
                sheetData.push([]);
                
                // Totals row
                sheetData.push(['', propertyName, '', '', '', totalRent, totalPagado]);
                
                // Store for summary sheet
                grandTotals.push({ name: propertyName, total: totalRent, pagado: totalPagado });
                
                // Create worksheet
                const ws = XLSX.utils.aoa_to_sheet(sheetData);
                
                // Set column widths
                ws['!cols'] = [
                    { wch: 4 },   // A - row label
                    { wch: 25 },  // B - name
                    { wch: 12 },  // C - inicia
                    { wch: 12 },  // D - termina
                    { wch: 6 },   // E - bco
                    { wch: 10 },  // F - renta
                    { wch: 10 },  // G - pagado
                    { wch: 20 }   // H - aviso
                ];
                
                // Add sheet to workbook (limit sheet name to 31 chars)
                const sheetName = propertyName.substring(0, 31);
                XLSX.utils.book_append_sheet(wb, ws, sheetName);
            });
            
            // Create summary sheet (like Hoja2 in user's Excel)
            const summaryData = [[], []];  // Empty rows at top
            
            grandTotals.forEach(item => {
                summaryData.push(['', item.total]);
            });
            
            // Empty rows
            summaryData.push([]);
            summaryData.push([]);
            
            // Add property breakdown
            grandTotals.forEach(item => {
                summaryData.push(['', item.name, '', '', '', item.total]);
            });
            
            // Grand total
            const grandTotal = grandTotals.reduce((sum, item) => sum + item.total, 0);
            summaryData.push([]);
            summaryData.push(['', 'G total', '', '', '', grandTotal]);
            
            const summaryWs = XLSX.utils.aoa_to_sheet(summaryData);
            summaryWs['!cols'] = [
                { wch: 4 },
                { wch: 15 },
                { wch: 10 },
                { wch: 10 },
                { wch: 10 },
                { wch: 12 }
            ];
            XLSX.utils.book_append_sheet(wb, summaryWs, 'Resumen');
            
            // Generate filename with month and year
            const filename = 'Rentas_' + monthName + '_' + currentYear + '.xlsx';
            
            // Download the file
            XLSX.writeFile(wb, filename);
        }

        // UX #1: Confirmation Modal State
        let pendingConfirmAction = null;
        let pendingConfirmBtn = null;
        
        // Get tenant info for modal context
        function getTenantInfoFromBtn(btn) {
            const item = btn.closest('.tenant-item') || btn.closest('tr[data-tenant-id]');
            if (!item) return { name: '', amount: '', month: '' };
            
            const tenantId = item.dataset.tenantId;
            
            // Try to get name
            let name = '';
            const nameEl = item.querySelector('.tenant-name');
            if (nameEl) {
                name = nameEl.textContent.trim();
            } else {
                // From table view
                const nameCell = item.querySelector('td:nth-child(2)');
                if (nameCell) name = nameCell.textContent.trim();
            }
            
            // Try to get amount
            let amount = '';
            const rentEl = item.querySelector('.tenant-rent');
            if (rentEl) {
                amount = rentEl.textContent.trim();
            } else {
                const rentCell = item.querySelector('.rent-cell');
                if (rentCell) amount = rentCell.textContent.trim();
            }
            
            // Get current month from page
            const monthEl = document.querySelector('[style*="text-transform: capitalize"]');
            const month = monthEl ? monthEl.textContent.trim() : '';
            
            return { name, amount, month };
        }
        
        function showConfirmModal(title, message, icon, actionType, btn) {
            const modal = document.getElementById('confirmModal');
            const titleEl = document.getElementById('confirmTitle');
            const messageEl = document.getElementById('confirmMessage');
            const iconEl = document.getElementById('confirmIcon');
            const confirmBtn = document.getElementById('confirmBtn');
            
            // Get tenant context
            const tenantInfo = getTenantInfoFromBtn(btn);
            const tenantNameEl = document.getElementById('confirmTenantName');
            const monthYearEl = document.getElementById('confirmMonthYear');
            const amountEl = document.getElementById('confirmAmount');
            const contextEl = document.getElementById('confirmContext');
            
            titleEl.textContent = title;
            messageEl.textContent = message;
            iconEl.textContent = icon;
            
            // Populate context if we have tenant info
            if (tenantInfo.name && tenantNameEl) {
                tenantNameEl.textContent = tenantInfo.name;
                monthYearEl.textContent = tenantInfo.month;
                amountEl.textContent = tenantInfo.amount;
                if (contextEl) contextEl.style.display = 'block';
            } else if (contextEl) {
                contextEl.style.display = 'none';
            }
            
            // Update button style based on action type
            confirmBtn.className = actionType === 'paid' ? 'btn-confirm-paid' : 'btn-confirm-unpaid';
            confirmBtn.textContent = actionType === 'paid' ? 'Sí, pagó' : 'Marcar pendiente';
            
            pendingConfirmBtn = btn;
            pendingConfirmAction = actionType;
            
            modal.classList.add('show');
        }
        
        function closeConfirmModal() {
            const modal = document.getElementById('confirmModal');
            modal.classList.remove('show');
            pendingConfirmAction = null;
            pendingConfirmBtn = null;
        }
        
        function executeConfirmedAction() {
            if (pendingConfirmBtn) {
                executeTogglePaid(pendingConfirmBtn);
            }
            closeConfirmModal();
        }
        
        // #1 & #3: Toggle paid status - DIRECT toggle like contratos (no modal)
        function togglePaid(btn) {
            // Execute toggle directly - no confirmation needed
            executeTogglePaid(btn);
        }
        
        // NEW: Two-button payment status system (like Contratos renewal buttons)
        function setPaymentStatus(btn, tenantId, isPaid) {
            const item = btn.closest('.tenant-item');
            if (!item) {
                console.error('Could not find tenant-item for button');
                return;
            }
            
            const container = btn.closest('.payment-buttons');
            const checkbox = item.querySelector('.tenant-checkbox');
            const paymentSelect = item.querySelector('.payment-method');
            const tenantName = item.querySelector('.tenant-name')?.textContent?.trim() || 'Inquilino';
            const rentText = item.querySelector('.tenant-rent')?.textContent || '$0';
            
            // Update button states
            container.querySelectorAll('.payment-btn').forEach(b => {
                b.classList.remove('active-green', 'active-red');
            });
            
            // Set active state
            if (isPaid) {
                btn.classList.add('active-green');
                item.classList.add('paid');
                if (checkbox) checkbox.checked = false;
                if (paymentSelect) paymentSelect.disabled = false;
                updateWhatsAppButton(item, true);
                showPersistentConfirmation(`¡${tenantName} PAGÓ! ${rentText}`, 'paid');
                
                // Auto-show details to show payment method selector
                const details = item.querySelector('.tenant-details');
                if (details && !details.classList.contains('show')) {
                    details.classList.add('show');
                    if (paymentSelect) {
                        setTimeout(() => {
                            paymentSelect.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            paymentSelect.focus();
                        }, 200);
                    }
                }
            } else {
                btn.classList.add('active-red');
                item.classList.remove('paid');
                if (checkbox) checkbox.checked = true;
                if (paymentSelect) {
                    paymentSelect.disabled = true;
                    paymentSelect.value = '';
                }
                updateWhatsAppButton(item, false);
                showPersistentConfirmation(`${tenantName} marcado como PENDIENTE`, 'unpaid');
            }
            
            // Update last saved immediately for instant user feedback
            updateLastSaved();
            
            // Save to database
            fetch('/api/payment', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tenant_id: tenantId,
                    paid: isPaid,
                    payment_method: paymentSelect?.value || null
                })
            }).then(response => {
                if (response.ok) {
                    console.log(`Guardado: ${tenantId} = ${isPaid ? 'pagado' : 'pendiente'}`);
                }
            }).catch(err => {
                console.error('Error guardando, guardando localmente:', err);
                const queue = JSON.parse(localStorage.getItem('pendingPayments') || '[]');
                queue.push({ tenantId: tenantId, paid: isPaid, timestamp: Date.now() });
                localStorage.setItem('pendingPayments', JSON.stringify(queue));
                showPersistentConfirmation('Guardado localmente (sin conexión)', 'warning');
            });
            
            updateCounts();
        }
        
        // NEW: Toggle switch payment status handler
        function togglePaymentStatus(toggle, tenantId) {
            const isPaid = toggle.checked;
            const item = toggle.closest('.tenant-item');
            if (!item) {
                console.error('Could not find tenant-item for toggle');
                return;
            }
            
            const checkbox = item.querySelector('.tenant-checkbox');
            const paymentSelect = item.querySelector('.payment-method');
            const tenantName = item.querySelector('.tenant-name')?.textContent?.trim() || 'Inquilino';
            const rentText = item.querySelector('.tenant-rent')?.textContent || '$0';
            const toggleLabel = item.querySelector('.payment-toggle-label');
            
            // Update toggle label
            if (toggleLabel) {
                toggleLabel.textContent = isPaid ? 'Ya pagó' : 'No ha pagado';
                toggleLabel.classList.toggle('paid', isPaid);
                toggleLabel.classList.toggle('unpaid', !isPaid);
            }
            
            // Update item state
            if (isPaid) {
                item.classList.add('paid');
                if (checkbox) checkbox.checked = false;
                if (paymentSelect) paymentSelect.disabled = false;
                updateWhatsAppButton(item, true);
                showPersistentConfirmation(`¡${tenantName} PAGÓ! ${rentText}`, 'paid');
                
                // Auto-show details to show payment method selector
                const details = item.querySelector('.tenant-details');
                if (details && !details.classList.contains('show')) {
                    details.classList.add('show');
                    if (paymentSelect) {
                        setTimeout(() => {
                            paymentSelect.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            paymentSelect.focus();
                        }, 200);
                    }
                }
            } else {
                item.classList.remove('paid');
                if (checkbox) checkbox.checked = true;
                if (paymentSelect) {
                    paymentSelect.disabled = true;
                    paymentSelect.value = '';
                }
                updateWhatsAppButton(item, false);
                showPersistentConfirmation(`${tenantName} marcado como PENDIENTE`, 'unpaid');
            }
            
            // Update last saved immediately for instant user feedback
            updateLastSaved();
            
            // Save to database
            fetch('/api/payment', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tenant_id: tenantId,
                    paid: isPaid,
                    payment_method: paymentSelect?.value || null
                })
            }).then(response => {
                if (response.ok) {
                    console.log(`Guardado: ${tenantId} = ${isPaid ? 'pagado' : 'pendiente'}`);
                }
            }).catch(err => {
                console.error('Error guardando, guardando localmente:', err);
                const queue = JSON.parse(localStorage.getItem('pendingPayments') || '[]');
                queue.push({ tenantId: tenantId, paid: isPaid, timestamp: Date.now() });
                localStorage.setItem('pendingPayments', JSON.stringify(queue));
                showPersistentConfirmation('Guardado localmente (sin conexión)', 'warning');
            });
            
            updateCounts();
        }
        
        // Execute the actual toggle after confirmation
        function executeTogglePaid(btn) {
            const item = btn.closest('.tenant-item');
            if (!item) {
                console.error('Could not find tenant-item for button');
                return;
            }
            
            const checkbox = item.querySelector('.tenant-checkbox');
            if (!checkbox) {
                console.error('Could not find checkbox for tenant');
                return;
            }
            
            const paymentSelect = item.querySelector('.payment-method');
            const tenantId = btn.dataset.tenantId;
            const tenantName = item.querySelector('.tenant-name')?.textContent?.trim() || 'Inquilino';
            const rentText = item.querySelector('.tenant-rent')?.textContent || '$0';
            
            // Show loading state on button
            const originalHtml = btn.innerHTML;
            btn.innerHTML = '<span class="loading-spinner"></span> Guardando...';
            btn.classList.add('btn-loading');
            
            // Toggle the hidden checkbox
            checkbox.checked = !checkbox.checked;
            
            // Determine new paid status (checked = NOT paid, needs reminder)
            const isPaid = !checkbox.checked;
            
            // Update the button appearance
            if (checkbox.checked) {
                // Now UNPAID (will receive reminder)
                btn.className = 'status-pill status-pill--full-width tenant-status-btn unpaid';
                btn.innerHTML = '<span class="icon"></span><span class="label">No ha pagado</span>';
                item.classList.remove('paid');
                if (paymentSelect) {
                    paymentSelect.disabled = true;
                    paymentSelect.value = '';
                }
                updateWhatsAppButton(item, false);
                // #1: Show PERSISTENT confirmation (no blinking)
                showPersistentConfirmation(`${tenantName} marcado como PENDIENTE`, 'unpaid');
            } else {
                // Now PAID (won't receive reminder)
                btn.className = 'status-pill status-pill--full-width tenant-status-btn paid';
                btn.innerHTML = '<span class="icon"></span><span class="label">Ya pagó</span>';
                item.classList.add('paid');
                if (paymentSelect) {
                    paymentSelect.disabled = false;
                }
                updateWhatsAppButton(item, true);
                // #1: Show PERSISTENT confirmation (no blinking)
                showPersistentConfirmation(`¡${tenantName} PAGÓ! ${rentText}`, 'paid');
                
                // #9: Auto-show details to show payment method selector
                const details = item.querySelector('.tenant-details');
                if (details && !details.classList.contains('show')) {
                    details.classList.add('show');
                    // Scroll to the payment method selector
                    if (paymentSelect) {
                        setTimeout(() => {
                            paymentSelect.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            paymentSelect.focus();
                        }, 200);
                    }
                }
            }
            
            // Update last saved immediately for instant user feedback
            updateLastSaved();
            
            // Save to database with loading state
            fetch('/api/payment', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tenant_id: tenantId,
                    paid: isPaid,
                    payment_method: paymentSelect.value || null
                })
            }).then(response => {
                if (response.ok) {
                    console.log(`Guardado: ${tenantId} = ${isPaid ? 'pagado' : 'pendiente'}`);
                }
            }).catch(err => {
                console.error('Error guardando, guardando localmente:', err);
                // OFFLINE QUEUE: Save to LocalStorage for later sync
                const queue = JSON.parse(localStorage.getItem('pendingPayments') || '[]');
                queue.push({ tenantId: tenantId, paid: isPaid, timestamp: Date.now() });
                localStorage.setItem('pendingPayments', JSON.stringify(queue));
                showPersistentConfirmation('Guardado localmente (sin conexión)', 'warning');
            });
            
            updateCounts();
        }
        
        function updateCounts() {
            const checkboxes = document.querySelectorAll('.tenant-checkbox');
            let pending = 0;
            let paid = 0;
            let paidAmount = 0;
            let totalAmount = 0;
            let pendingBaseRent = 0;  // Track base rent only (without late fees) for top banner
            
            // Track per-property counts and amounts
            const propertyPaidCounts = {};
            const propertyPendingCounts = {};
            const propertyPaidAmounts = {};
            
            checkboxes.forEach(cb => {
                const propertyName = cb.dataset.property;
                const item = cb.closest('.tenant-item');
                const rentText = item.querySelector('.tenant-rent')?.textContent || '$0';
                const rent = parseFloat(rentText.replace(/[$,]/g, '')) || 0;
                
                // Get base rent from data attribute (without late fees)
                const tenantAmountEl = item.querySelector('.tenant-amount');
                const baseRent = parseFloat(tenantAmountEl?.dataset.baseRent) || rent;
                
                totalAmount += rent;
                
                if (!propertyPaidCounts[propertyName]) {
                    propertyPaidCounts[propertyName] = 0;
                    propertyPaidAmounts[propertyName] = 0;
                }
                if (!propertyPendingCounts[propertyName]) {
                    propertyPendingCounts[propertyName] = 0;
                }
                
                if (cb.checked) {
                    pending++;
                    propertyPendingCounts[propertyName]++;
                    pendingBaseRent += baseRent;  // Add base rent only for pending tenants
                } else {
                    paid++;
                    paidAmount += rent;
                    propertyPaidCounts[propertyName]++;
                    propertyPaidAmounts[propertyName] += rent;
                }
            });
            
            // Update property paid counters
            Object.keys(propertyPaidCounts).forEach(propName => {
                const paidCounter = document.querySelector(`[data-property-paid="${propName}"]`);
                if (paidCounter) {
                    paidCounter.textContent = `${propertyPaidCounts[propName]} pagaron`;
                }
                
                const pendingCounter = document.querySelector(`[data-property-pending="${propName}"]`);
                if (pendingCounter) {
                    pendingCounter.textContent = `${propertyPendingCounts[propName]} pendientes`;
                }
                
                // Get property total from data attribute
                const propertySection = document.querySelector(`.property-section[data-property="${propName}"]`);
                const propertyTotal = propertySection ? parseFloat(propertySection.dataset.propertyTotal) || 0 : 0;
                const propertyPaidAmount = propertyPaidAmounts[propName] || 0;
                const propertyPendingAmount = propertyTotal - propertyPaidAmount;
                
                // Update subtotal amounts (with peso values)
                const subtotalAmountPaid = document.querySelector(`[data-subtotal-amount-paid="${propName}"]`);
                if (subtotalAmountPaid) {
                    subtotalAmountPaid.textContent = `$${propertyPaidAmount.toLocaleString()} cobrados`;
                }
                
                const subtotalAmountPending = document.querySelector(`[data-subtotal-amount-pending="${propName}"]`);
                if (subtotalAmountPending) {
                    subtotalAmountPending.textContent = `$${propertyPendingAmount.toLocaleString()} pendientes`;
                }
                
                // Update old subtotal counters (for hidden elements)
                const subtotalPaid = document.querySelector(`[data-subtotal-paid="${propName}"]`);
                if (subtotalPaid) {
                    subtotalPaid.textContent = `${propertyPaidCounts[propName]} pagados`;
                }
                
                const subtotalPending = document.querySelector(`[data-subtotal-pending="${propName}"]`);
                if (subtotalPending) {
                    subtotalPending.textContent = `${propertyPendingCounts[propName]} pendientes`;
                }
            });
            
            document.getElementById('pendingCount').textContent = pending;
            document.getElementById('paidCount').textContent = paid;
            document.getElementById('selectedCount').textContent = pending;
            
            // Update grand total breakdown (pending/paid amounts)
            const pendingAmount = totalAmount - paidAmount;
            
            const grandTotalPending = document.getElementById('grandTotalPending');
            const grandTotalPaid = document.getElementById('grandTotalPaid');
            const collectionRateStat = document.getElementById('collectionRate');
            
            if (grandTotalPending) {
                grandTotalPending.textContent = `$${pendingAmount.toLocaleString()} MXN`;
            }
            if (grandTotalPaid) {
                grandTotalPaid.textContent = `$${paidAmount.toLocaleString()} MXN`;
            }
            
            // Update collection rate progress bar
            const progressBar = document.getElementById('collectionProgressBar');
            const progressText = document.getElementById('collectionProgressText');
            const percentageLabel = document.getElementById('collectionPercentage');
            
            if (progressBar && totalAmount > 0) {
                const percentage = Math.round((paidAmount / totalAmount) * 100);
                progressBar.style.width = `${percentage}%`;
                
                // Update percentage label
                if (percentageLabel) {
                    percentageLabel.textContent = `${percentage}%`;
                }
                
                // Update collection rate stat in grand total
                if (collectionRateStat) {
                    collectionRateStat.textContent = `${percentage}% cobrado`;
                }
                
                // Show text inside bar only if there's enough space (>15%)
                if (progressText) {
                    if (percentage >= 15) {
                        progressText.textContent = `$${paidAmount.toLocaleString()}`;
                    } else {
                        progressText.textContent = '';
                    }
                }
                
                // Add 'complete' class when 100%
                if (percentage === 100) {
                    progressBar.classList.add('complete');
                    // #11: CELEBRATION at 100%!
                    triggerCelebration();
                } else {
                    progressBar.classList.remove('complete');
                }
            }
            
            // #8: Update TOP "Falta Cobrar" section (base rent only, without late fees)
            const faltaCobrarTop = document.getElementById('faltaCobrarTop');
            const faltaPersonasTop = document.getElementById('faltaPersonasTop');
            if (faltaCobrarTop) {
                faltaCobrarTop.textContent = `$${pendingBaseRent.toLocaleString()} MXN`;
            }
            if (faltaPersonasTop) {
                faltaPersonasTop.textContent = `de ${pending} personas`;
            }
            
            // UX #3: Update property filter tab counts
            updatePropertyFilterCounts();
        }
        
        // #1: PERSISTENT CONFIRMATION function (no blinking, solid green/red)
        function showPersistentConfirmation(message, type) {
            const toast = document.getElementById('undoToast');
            const messageEl = document.getElementById('undoMessage');
            
            if (!toast || !messageEl) return;
            
            messageEl.textContent = message;
            
            // Color based on type
            if (type === 'paid') {
                toast.style.background = '#0A7A0A';
            } else if (type === 'unpaid') {
                toast.style.background = '#CC0000';
            } else {
                toast.style.background = '#333333';
            }
            
            toast.classList.add('show');
            
            // Hide after 3 seconds
            setTimeout(() => {
                toast.classList.remove('show');
            }, 3000);
        }
        
        // #11: CELEBRATION with confetti when 100% collected
        let celebrationShown = false;
        function triggerCelebration() {
            if (celebrationShown) return;
            celebrationShown = true;
            
            // Show celebration banner
            const banner = document.getElementById('celebrationBanner');
            if (banner) {
                banner.classList.add('show');
                setTimeout(() => {
                    banner.classList.remove('show');
                }, 4000);
            }
            
            // Create confetti
            const container = document.getElementById('confettiContainer');
            if (!container) return;
            
            const colors = ['#0A7A0A', '#CC0000', '#FFD700', '#FF6B6B', '#4ECDC4'];
            
            for (let i = 0; i < 50; i++) {
                setTimeout(() => {
                    const confetti = document.createElement('div');
                    confetti.className = 'confetti';
                    confetti.style.left = Math.random() * 100 + '%';
                    confetti.style.top = '-20px';
                    confetti.style.background = colors[Math.floor(Math.random() * colors.length)];
                    confetti.style.borderRadius = Math.random() > 0.5 ? '50%' : '0';
                    confetti.style.opacity = '1';
                    container.appendChild(confetti);
                    
                    // Animate falling
                    const duration = 2000 + Math.random() * 2000;
                    const endX = (Math.random() - 0.5) * 200;
                    confetti.animate([
                        { transform: 'translateY(0) rotate(0deg)', opacity: 1 },
                        { transform: `translateY(100vh) translateX(${endX}px) rotate(720deg)`, opacity: 0 }
                    ], {
                        duration: duration,
                        easing: 'ease-out'
                    });
                    
                    // Remove after animation
                    setTimeout(() => confetti.remove(), duration);
                }, i * 50);
            }
            
            // Reset after 10 seconds so it can trigger again if user changes things
            setTimeout(() => {
                celebrationShown = false;
            }, 10000);
        }
        
        // =============================================
        // UX #3: Property Filter Tabs
        // =============================================
        
        let activePropertyFilter = 'all';
        
        function filterByProperty(propertyName, btn) {
            console.log('filterByProperty called with:', propertyName);
            activePropertyFilter = propertyName;
            
            // Update tab active states and styles (green active, same as contratos)
            const allTabs = document.querySelectorAll('.property-filter-tab');
            allTabs.forEach(tab => {
                tab.classList.remove('active');
                tab.style.background = 'transparent';
                tab.style.color = '#333333';
            });
            btn.classList.add('active');
            btn.style.background = '#0A7A0A';
            btn.style.color = 'white';
            
            // Clear any search filter first
            const searchInput = document.getElementById('tenantSearch');
            if (searchInput && searchInput.value) {
                searchInput.value = '';
                document.getElementById('clearSearch').classList.remove('visible');
                document.getElementById('searchResults').style.display = 'none';
            }
            
            // Filter card view
            const allItems = document.querySelectorAll('.tenant-item');
            const allSections = document.querySelectorAll('.property-section');
            
            // Filter excel view
            const excelSections = document.querySelectorAll('.excel-property-section');
            
            if (propertyName === 'all') {
                // Show all
                allItems.forEach(item => item.style.display = 'flex');
                allSections.forEach(section => section.style.display = 'block');
                excelSections.forEach(section => section.style.display = 'block');
            } else {
                // Filter by property (use includes for partial matching like Contratos)
                allItems.forEach(item => {
                    const itemProperty = item.dataset.property || '';
                    item.style.display = itemProperty.includes(propertyName) ? 'flex' : 'none';
                });
                
                allSections.forEach(section => {
                    const sectionProperty = section.dataset.property || '';
                    section.style.display = sectionProperty.includes(propertyName) ? 'block' : 'none';
                });
                
                // For Excel view, hide non-matching sections
                excelSections.forEach(section => {
                    const sectionTable = section.querySelector('.excel-table');
                    if (sectionTable) {
                        const headerRow = sectionTable.querySelector('thead tr:first-child th');
                        if (headerRow) {
                            const headerText = headerRow.textContent.trim();
                            section.style.display = headerText.includes(propertyName) ? 'block' : 'none';
                        }
                    }
                });
            }
            
            // Update counts display
            updatePropertyFilterCounts();
        }
        
        function updatePropertyFilterCounts() {
            // Get counts per property
            const allItems = document.querySelectorAll('.tenant-item');
            const propertyCounts = {};
            let totalPending = 0;
            
            allItems.forEach(item => {
                const property = item.dataset.property;
                const isPaid = item.classList.contains('paid');
                
                if (!propertyCounts[property]) {
                    propertyCounts[property] = { total: 0, pending: 0 };
                }
                
                propertyCounts[property].total++;
                if (!isPaid) {
                    propertyCounts[property].pending++;
                    totalPending++;
                }
            });
            
            // Update tab badges
            const allTabCount = document.getElementById('tabCountAll');
            if (allTabCount) {
                allTabCount.textContent = totalPending > 0 ? `${totalPending} pendientes` : '✓ Todos pagaron';
            }
            
            Object.keys(propertyCounts).forEach(propName => {
                const tabCount = document.querySelector(`[data-tab-count="${propName}"]`);
                if (tabCount) {
                    const pending = propertyCounts[propName].pending;
                    tabCount.textContent = pending > 0 ? `${pending} pendientes` : '✓';
                }
            });
        }
        
        // =============================================
        // Search/Filter Tenants
        // =============================================
        
        function filterTenants(searchTerm) {
            const clearBtn = document.getElementById('clearSearch');
            const resultsDiv = document.getElementById('searchResults');
            const term = (searchTerm || '').toLowerCase().trim();
            
            // Show/hide clear button
            if (clearBtn) {
                clearBtn.style.display = term ? 'block' : 'none';
            }
            
            // Filter card view
            const allItems = document.querySelectorAll('.tenant-item');
            const allSections = document.querySelectorAll('.property-section');
            
            // Filter excel view rows
            const allRows = document.querySelectorAll('.excel-table tbody tr');
            
            if (!term) {
                // Show all tenants and sections
                allItems.forEach(item => item.style.display = 'flex');
                allSections.forEach(section => section.style.display = 'block');
                allRows.forEach(row => row.style.display = '');
                // Also show all Excel property sections
                const excelSections = document.querySelectorAll('.excel-property-section');
                excelSections.forEach(section => section.style.display = 'block');
                if (resultsDiv) resultsDiv.style.display = 'none';
                return;
            }
            
            let matchCount = 0;
            const propertyVisibility = {};
            
            // Filter card view
            allItems.forEach(item => {
                const checkbox = item.querySelector('.tenant-checkbox');
                if (!checkbox) return;
                const name = (checkbox.dataset.name || '').toLowerCase();
                const property = checkbox.dataset.property;
                
                if (name.includes(term)) {
                    item.style.display = 'flex';
                    matchCount++;
                    propertyVisibility[property] = true;
                } else {
                    item.style.display = 'none';
                }
            });
            
            // Filter excel view
            allRows.forEach(row => {
                const nameCell = row.querySelector('td:nth-child(2)');
                if (!nameCell) return;
                const name = nameCell.textContent.toLowerCase();
                
                if (name.includes(term)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
            
            // Hide property sections with no visible tenants (card view)
            allSections.forEach(section => {
                const propertyName = section.dataset.property;
                section.style.display = propertyVisibility[propertyName] ? 'block' : 'none';
            });
            
            // Hide Excel property sections with no visible tenants
            const excelPropertySections = document.querySelectorAll('.excel-property-section');
            excelPropertySections.forEach(section => {
                const visibleRows = section.querySelectorAll('tr[data-tenant-id]');
                let hasVisible = false;
                visibleRows.forEach(row => {
                    if (row.style.display !== 'none') {
                        hasVisible = true;
                    }
                });
                section.style.display = hasVisible ? 'block' : 'none';
            });
            
            // Show results count
            resultsDiv.style.display = 'block';
            if (matchCount === 0) {
                resultsDiv.innerHTML = `No se encontró "<strong>${searchTerm}</strong>"`;
            } else if (matchCount === 1) {
                resultsDiv.innerHTML = `1 inquilino encontrado`;
            } else {
                resultsDiv.innerHTML = `${matchCount} inquilinos encontrados`;
            }
        }
        
        function clearSearch() {
            const searchInput = document.getElementById('tenantSearch');
            searchInput.value = '';
            filterTenants('');
            searchInput.focus();
        }
        
        function updatePaymentMethod(select) {
            const item = select.closest('.tenant-item');
            const tenantId = item.dataset.tenantId;
            const method = select.value;
            
            if (method && tenantId) {
                fetch('/api/payment', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        tenant_id: tenantId,
                        paid: true,
                        payment_method: method
                    })
                }).then(response => {
                    if (response.ok) {
                        console.log(`Método guardado: ${tenantId} = ${method}`);
                    }
                });
            }
        }
        
        function markAllUnpaid() {
            // Get all tenant IDs from both card and table views
            const allTenantIds = new Set();
            
            // Collect from card view
            document.querySelectorAll('.tenant-item').forEach(item => {
                if (item.dataset.tenantId) allTenantIds.add(item.dataset.tenantId);
            });
            
            // Collect from table view
            document.querySelectorAll('tr[data-tenant-id]').forEach(row => {
                if (row.dataset.tenantId) allTenantIds.add(row.dataset.tenantId);
            });
            
            allTenantIds.forEach(tenantId => {
                // Update card view if exists
                const item = document.querySelector(`.tenant-item[data-tenant-id="${tenantId}"]`);
                if (item) {
                    const checkbox = item.querySelector('.tenant-checkbox');
                    const btn = item.querySelector('.tenant-status-btn');
                    const paymentSelect = item.querySelector('.payment-method');
                    
                    if (checkbox) checkbox.checked = true;
                    if (btn) {
                        btn.className = 'status-pill status-pill--full-width tenant-status-btn unpaid';
                        btn.innerHTML = '<span class="icon"></span><span class="label">No ha pagado</span>';
                    }
                    item.classList.remove('paid');
                    if (paymentSelect) {
                        paymentSelect.disabled = true;
                        paymentSelect.value = '';
                    }
                    
                    // Update WhatsApp button visibility
                    updateWhatsAppButton(item, false);
                }
                
                // Update table view if exists
                const tableRow = document.querySelector(`tr[data-tenant-id="${tenantId}"]`);
                if (tableRow) {
                    tableRow.classList.remove('paid-row');
                    tableRow.classList.add('unpaid-row');
                    
                    // Update the status button in table
                    const tableBtn = tableRow.querySelector('.tenant-status-btn-table');
                    if (tableBtn) {
                        tableBtn.className = 'status-pill status-pill--small tenant-status-btn-table unpaid';
                        tableBtn.textContent = '';
                    }
                    
                    // Update the "Pagado" cell (clear the amount)
                    const pagadoCell = tableRow.querySelector('.pagado-cell');
                    if (pagadoCell) {
                        pagadoCell.textContent = '';
                    }
                    
                    // Update the rent cell color to red (pending)
                    const rentCell = tableRow.querySelector('.rent-cell');
                    if (rentCell) {
                        rentCell.style.color = '#CC0000';
                    }
                }
                
                // Save to database
                fetch('/api/payment', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ tenant_id: tenantId, paid: false })
                });
            });
            
            // Update property totals in table view
            updatePropertyTotals();
            updateCounts();
        }
        
        function markAllPaid() {
            // Get all tenant IDs from both card and table views
            const allTenantIds = new Set();
            
            // Collect from card view
            document.querySelectorAll('.tenant-item').forEach(item => {
                if (item.dataset.tenantId) allTenantIds.add(item.dataset.tenantId);
            });
            
            // Collect from table view
            document.querySelectorAll('tr[data-tenant-id]').forEach(row => {
                if (row.dataset.tenantId) allTenantIds.add(row.dataset.tenantId);
            });
            
            allTenantIds.forEach(tenantId => {
                // Update card view if exists
                const item = document.querySelector(`.tenant-item[data-tenant-id="${tenantId}"]`);
                if (item) {
                    const checkbox = item.querySelector('.tenant-checkbox');
                    const btn = item.querySelector('.tenant-status-btn');
                    const paymentSelect = item.querySelector('.payment-method');
                    
                    if (checkbox) checkbox.checked = false;
                    if (btn) {
                        btn.className = 'status-pill status-pill--full-width tenant-status-btn paid';
                        btn.innerHTML = '<span class="icon"></span><span class="label">Ya pagó</span>';
                    }
                    item.classList.add('paid');
                    if (paymentSelect) {
                        paymentSelect.disabled = false;
                    }
                    
                    // Update WhatsApp button visibility
                    updateWhatsAppButton(item, true);
                }
                
                // Update table view if exists
                const tableRow = document.querySelector(`tr[data-tenant-id="${tenantId}"]`);
                if (tableRow) {
                    tableRow.classList.remove('unpaid-row');
                    tableRow.classList.add('paid-row');
                    
                    // Update the status button in table
                    const tableBtn = tableRow.querySelector('.tenant-status-btn-table');
                    if (tableBtn) {
                        tableBtn.className = 'status-pill status-pill--small tenant-status-btn-table paid';
                        tableBtn.textContent = '✓';
                    }
                    
                    // Get the rent amount from the rent cell and update the "Pagado" cell
                    const rentCell = tableRow.querySelector('.rent-cell');
                    const pagadoCell = tableRow.querySelector('.pagado-cell');
                    if (rentCell && pagadoCell) {
                        pagadoCell.textContent = rentCell.textContent;
                        // Remove red color from rent cell (no longer pending)
                        rentCell.style.color = '';
                    }
                }
                
                // Save to database
                fetch('/api/payment', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ tenant_id: tenantId, paid: true })
                });
            });
            
            // Update property totals in table view
            updatePropertyTotals();
            updateCounts();
        }
        
        function generateLinks() {
            const checkboxes = document.querySelectorAll('.tenant-checkbox:checked');
            const linksContainer = document.getElementById('whatsappLinks');
            const previewContainer = document.getElementById('messagePreview');
            
            if (checkboxes.length === 0) {
                alert('¡Todos han pagado! No hay inquilinos pendientes.');
                return;
            }
            
            // Clear previous links
            linksContainer.innerHTML = '';
            
            // Generate links for each selected tenant
            checkboxes.forEach((cb, index) => {
                const name = cb.dataset.name;
                const phone = testMode ? testPhone : cb.dataset.phone;
                
                // Fetch the message from server
                fetch(`/api/message?tenant_id=${cb.dataset.id}&day=${dayOfMonth}`)
                    .then(response => response.json())
                    .then(data => {
                        const link = document.createElement('a');
                        link.href = data.whatsapp_url;
                        link.target = '_blank';
                        link.className = 'whatsapp-link';
                        link.innerHTML = `
                            <span class="link-name">${index + 1}. ${name}</span>
                            <span class="link-icon">Enviar</span>
                        `;
                        linksContainer.appendChild(link);
                        
                        // Show preview of first message
                        if (index === 0) {
                            previewContainer.textContent = data.message;
                            previewContainer.style.display = 'block';
                        }
                    });
            });
            
            linksContainer.style.display = 'flex';
        }
        
        // =============================================
        // WhatsApp Cloud API - Send All Function
        // =============================================
        
        async function sendAllViaApi() {
            const btn = document.getElementById('sendAllApiBtn');
            const statusDiv = document.getElementById('apiStatus');
            const pendingCount = parseInt(document.getElementById('selectedCount').textContent);
            
            if (pendingCount === 0) {
                alert('¡Todos han pagado! No hay inquilinos pendientes.');
                return;
            }
            
            // Confirm before sending
            if (!confirm(`¿Enviar recordatorio de renta a ${pendingCount} inquilino(s) pendientes vía WhatsApp? Esto enviará mensajes automáticamente.`)) {
                return;
            }
            
            // Show loading state
            btn.disabled = true;
            btn.innerHTML = 'Enviando...';
            statusDiv.style.display = 'block';
            statusDiv.style.background = '#fef3c7';
            statusDiv.style.color = '#92400e';
            statusDiv.innerHTML = 'Enviando mensajes a inquilinos pendientes...';
            
            try {
                const response = await fetch('/api/whatsapp/send-all', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Show success
                    statusDiv.style.background = '#dcfce7';
                    statusDiv.style.color = '#166534';
                    statusDiv.innerHTML = `
                        <strong>¡Enviado!</strong><br>
                        ${data.summary.sent} mensajes enviados<br>
                        ${data.summary.skipped_paid > 0 ? `${data.summary.skipped_paid} ya pagaron (no se les envió)<br>` : ''}
                        ${data.summary.skipped_no_phone > 0 ? `${data.summary.skipped_no_phone} sin teléfono<br>` : ''}
                        ${data.summary.failed > 0 ? `${data.summary.failed} fallaron<br>` : ''}
                    `;
                    
                    // Show toast
                    showUndoToast(`${data.summary.sent} mensajes enviados`, null);
                } else {
                    // Show error
                    statusDiv.style.background = '#fee2e2';
                    statusDiv.style.color = '#dc2626';
                    statusDiv.innerHTML = `
                        <strong>Error</strong><br>
                        ${data.error || 'Error desconocido'}<br>
                        <small>Revisa la configuración en docs/SETUP_WHATSAPP_API.md</small>
                    `;
                }
            } catch (err) {
                statusDiv.style.background = '#fee2e2';
                statusDiv.style.color = '#dc2626';
                statusDiv.innerHTML = `
                    <strong>Error de conexión</strong><br>
                    ${err.message}<br>
                    <small>Verifica tu conexión a internet</small>
                `;
            } finally {
                btn.disabled = false;
                btn.innerHTML = '📤 Enviar TODOS via WhatsApp API';
            }
        }
        
        // Check WhatsApp API status on page load
        async function checkWhatsAppStatus() {
            try {
                const response = await fetch('/api/whatsapp/status');
                const data = await response.json();
                
                const btn = document.getElementById('sendAllApiBtn');
                if (!data.configured) {
                    btn.style.background = '#9ca3af';
                    btn.innerHTML = 'Configurar WhatsApp API';
                    btn.onclick = () => {
                        alert('WhatsApp API no está configurado.\\n\\nPasos:\\n1. Ve a docs/SETUP_WHATSAPP_API.md\\n2. Sigue los pasos para obtener credenciales\\n3. Agrega las credenciales al archivo .env');
                    };
                }
            } catch (err) {
                console.log('WhatsApp API check failed:', err);
            }
        }
        
        // Run on page load
        window.addEventListener('DOMContentLoaded', () => {
            checkWhatsAppStatus();
        });
        
        // =============================================
        // Confirmation dialogs for bulk actions
        // =============================================
        
        function confirmMarkAllUnpaid() {
            if (confirm('¿Marcar TODOS los inquilinos como pendientes de pago? Esta acción se puede deshacer.')) {
                markAllUnpaid();
                showUndoToast('Todos marcados como pendientes', 'markAllPaid');
            }
        }
        
        function confirmMarkAllPaid() {
            if (confirm('¿Marcar TODOS los inquilinos como pagados? Esta acción se puede deshacer.')) {
                markAllPaid();
                showUndoToast('Todos marcados como pagados', 'markAllUnpaid');
            }
        }
        
        // =============================================
        // Undo Toast Functionality
        // =============================================
        
        let lastAction = null;
        let undoTimeout = null;
        
        function showUndoToast(message, undoActionName) {
            const toast = document.getElementById('undoToast');
            const messageEl = document.getElementById('undoMessage');
            const undoBtn = document.getElementById('undoBtn');
            
            messageEl.textContent = message;
            lastAction = undoActionName;
            
            toast.classList.add('show');
            
            // Clear previous timeout
            if (undoTimeout) {
                clearTimeout(undoTimeout);
            }
            
            // Hide after 5 seconds
            undoTimeout = setTimeout(() => {
                toast.classList.remove('show');
                lastAction = null;
            }, 5000);
        }
        
        function undoLastAction() {
            const toast = document.getElementById('undoToast');
            
            if (lastAction === 'markAllPaid') {
                markAllPaid();
            } else if (lastAction === 'markAllUnpaid') {
                markAllUnpaid();
            }
            
            toast.classList.remove('show');
            if (undoTimeout) {
                clearTimeout(undoTimeout);
            }
            lastAction = null;
        }
        
        // =============================================
        // Offline Detection
        // =============================================
        
        function updateOnlineStatus() {
            const banner = document.getElementById('offlineBanner');
            if (navigator.onLine) {
                banner.style.display = 'none';
            } else {
                banner.style.display = 'block';
            }
        }
        
        // Initialize counts on page load
        document.addEventListener('DOMContentLoaded', function() {
            // Update checkbox state based on paid status (loaded from DB)
            document.querySelectorAll('.tenant-item').forEach(item => {
                const btn = item.querySelector('.tenant-status-btn');
                const checkbox = item.querySelector('.tenant-checkbox');
                
                // If button shows paid, uncheck the checkbox (paid = won't receive reminder)
                if (btn.classList.contains('paid')) {
                    checkbox.checked = false;
                    item.classList.add('paid');
                } else {
                    checkbox.checked = true;
                    item.classList.remove('paid');
                }
            });
            
            updateCounts();
            
            // Setup offline detection
            updateOnlineStatus();
            window.addEventListener('online', function() {
                updateOnlineStatus();
                syncPendingPayments();  // Sync when back online
            });
            window.addEventListener('offline', updateOnlineStatus);
        });
        
        // =============================================
        // Sync pending payments when back online
        // =============================================
        
        function syncPendingPayments() {
            const queue = JSON.parse(localStorage.getItem('pendingPayments') || '[]');
            if (queue.length === 0) return;
            
            console.log(`🔄 Syncing ${queue.length} pending payments...`);
            
            queue.forEach((item, index) => {
                fetch('/api/payment', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        tenant_id: item.tenantId,
                        paid: item.paid
                    })
                }).then(response => {
                    if (response.ok) {
                        console.log(`Synced payment for ${item.tenantId}`);
                    }
                });
            });
            
            // Clear the queue after syncing
            localStorage.removeItem('pendingPayments');
            showUndoToast(`${queue.length} cambios sincronizados`, null);
            updateLastSaved();
        }
        
// =============================================
        // Last Saved Timestamp - Updates sync indicator
        // =============================================
        
        function updateLastSaved() {
            const syncIndicator = document.getElementById('sync-indicator');
            const syncText = document.getElementById('sync-text');
            const now = new Date();
            
            // Save timestamp to localStorage for persistence across page reloads
            localStorage.setItem('lastSavedTime', now.getTime().toString());
            
            // Update the sync indicator
            if (syncIndicator && syncText) {
                syncIndicator.classList.remove('error');
                syncIndicator.classList.add('synced');
                syncText.textContent = 'Guardado hace unos segundos';
                
                // Show brief "syncing" animation
                const syncIcon = syncIndicator.querySelector('.sync-icon');
                if (syncIcon) {
                    syncIcon.textContent = '↻';
                    syncIcon.classList.add('spinning');
                    setTimeout(() => {
                        syncIcon.textContent = '✓';
                        syncIcon.classList.remove('spinning');
                    }, 500);
                }
            }
        }
        
        // Update sync indicator on errors
        function showSyncError() {
            const syncIndicator = document.getElementById('sync-indicator');
            const syncText = document.getElementById('sync-text');
            if (syncIndicator && syncText) {
                syncIndicator.classList.remove('synced');
                syncIndicator.classList.add('error');
                syncText.textContent = 'Error al guardar - reintentando...';
            }
        }
        
        // =============================================
        // Phone Number Editing
        // =============================================
        
        let currentEditingTenantId = null;
        
        function editPhone(tenantId, currentPhone) {
            currentEditingTenantId = tenantId;
            const modal = document.getElementById('phoneModal');
            const input = document.getElementById('phoneInput');
            const preview = document.getElementById('phonePreview');
            const saveBtn = document.getElementById('savePhoneBtn');
            
            input.value = currentPhone || '+52';
            preview.className = 'phone-preview'; // Reset preview state
            preview.style.display = 'none';
            saveBtn.disabled = false;
            saveBtn.textContent = 'Guardar';
            
            modal.classList.add('show');
            input.focus();
            input.select();
            
            // Validate initial value
            if (currentPhone) {
                validatePhonePreview(currentPhone);
            }
        }
        
        // UX #5: Phone validation with preview
        function validatePhonePreview(value) {
            const preview = document.getElementById('phonePreview');
            const previewNumber = document.getElementById('phonePreviewNumber');
            const saveBtn = document.getElementById('savePhoneBtn');
            
            // Remove all non-digits
            const digits = value.replace(/[^\d]/g, '');
            
            // Format the number for display
            let formattedNumber = '';
            let isValid = false;
            
            if (digits.length === 0) {
                preview.style.display = 'none';
                saveBtn.disabled = true;
                return;
            }
            
            // Check if it's a valid Mexican phone number
            if (digits.startsWith('52')) {
                // Already has country code
                if (digits.length === 12) {
                    // Full Mexican number: 52 + 10 digits
                    formattedNumber = `+${digits.slice(0,2)} ${digits.slice(2,4)} ${digits.slice(4,8)} ${digits.slice(8,12)}`;
                    isValid = true;
                } else if (digits.length === 13 && digits.startsWith('521')) {
                    // Old Mexican mobile format: 52 + 1 + 10 digits
                    formattedNumber = `+52 ${digits.slice(3,5)} ${digits.slice(5,9)} ${digits.slice(9,13)}`;
                    isValid = true;
                } else {
                    formattedNumber = `+${digits} (incompleto - necesita 12 dígitos)`;
                    isValid = false;
                }
            } else if (digits.length === 10) {
                // Just 10 digit Mexican local number - add country code
                formattedNumber = `+52 ${digits.slice(0,2)} ${digits.slice(2,6)} ${digits.slice(6,10)}`;
                isValid = true;
            } else if (digits.length > 10 && digits.length < 12) {
                formattedNumber = `${digits} (verificar formato)`;
                isValid = false;
            } else if (digits.length > 12) {
                formattedNumber = `${digits.slice(0,12)}... (muy largo)`;
                isValid = false;
            } else {
                formattedNumber = `${digits} (necesita 10+ dígitos)`;
                isValid = false;
            }
            
            // Update preview display
            preview.style.display = 'block';
            previewNumber.textContent = formattedNumber;
            
            if (isValid) {
                preview.className = 'phone-preview valid';
                preview.querySelector('.preview-label').textContent = 'Se guardará como:';
                saveBtn.disabled = false;
            } else {
                preview.className = 'phone-preview invalid';
                preview.querySelector('.preview-label').textContent = 'Formato incorrecto:';
                saveBtn.disabled = true;
            }
        }
        
        function closePhoneModal() {
            const modal = document.getElementById('phoneModal');
            modal.classList.remove('show');
            currentEditingTenantId = null;
        }
        
        // #9: Phone save with FEEDBACK MESSAGE
        function savePhone() {
            const input = document.getElementById('phoneInput');
            const phone = input.value.trim();
            
            if (!phone || !currentEditingTenantId) {
                closePhoneModal();
                return;
            }
            
            // Show saving state
            const saveBtn = document.querySelector('#phoneModal .btn-primary');
            if (saveBtn) {
                saveBtn.textContent = 'Guardando...';
                saveBtn.disabled = true;
            }
            
            fetch('/api/phone', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tenant_id: currentEditingTenantId,
                    phone: phone
                })
            }).then(response => {
                if (response.ok) {
                    // #9: Show success feedback message BEFORE reload
                    showPersistentConfirmation('¡Teléfono guardado! Ahora puedes enviar WhatsApp.', 'paid');
                    updateLastSaved();
                    // Reload page to show updated phone after short delay
                    setTimeout(() => location.reload(), 1500);
                }
            }).catch(err => {
                showPersistentConfirmation('Error guardando teléfono. Revise su conexión.', 'unpaid');
            });
            
            closePhoneModal();
        }
        
        // =============================================
        // Inline WhatsApp Function
        // =============================================
        
        function sendWhatsApp(event, btn) {
            event.preventDefault();
            const tenantId = btn.dataset.tenantId;
            
            // Show loading state
            const originalText = btn.innerHTML;
            btn.innerHTML = 'Cargando...';
            
            // Fetch message and open WhatsApp
            fetch(`/api/message?tenant_id=${tenantId}&day=${dayOfMonth}`)
                .then(response => response.json())
                .then(data => {
                    btn.innerHTML = originalText;
                    window.open(data.whatsapp_url, '_blank');
                })
                .catch(err => {
                    btn.innerHTML = originalText;
                    alert('Error al generar mensaje. Revise su conexión.');
                });
        }
        
        // Update WhatsApp button state when payment status changes
        function updateWhatsAppButton(item, isPaid) {
            const waBtn = item.querySelector('.whatsapp-inline-btn');
            if (waBtn && !waBtn.classList.contains('disabled')) {
                if (isPaid) {
                    waBtn.classList.add('disabled');
                    waBtn.innerHTML = 'Pagado';
                    waBtn.onclick = null;
                } else {
                    waBtn.classList.remove('disabled');
                    waBtn.innerHTML = 'WhatsApp';
                }
            }
        }
    </script>
</body>
</html>
"""


# =============================================================================
# ROUTES
# =============================================================================


@app.route("/login", methods=["GET", "POST"])
def login():
    """Simple PIN login for password protection."""
    if request.method == "POST":
        pin = request.form.get("pin", "")
        if pin == RENTASCLARAS_PIN:
            session["authenticated"] = True
            return redirect(url_for("index"))
        else:
            return render_template_string(
                LOGIN_TEMPLATE, error="PIN incorrecto. Intente de nuevo."
            )
    return render_template_string(LOGIN_TEMPLATE, error=None)


@app.route("/logout")
def logout():
    """Clear the session and log out."""
    session.clear()
    return redirect(url_for("login"))


LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="default">
    <title>RentasClaras - Iniciar Sesión</title>
    <link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
    <link rel="apple-touch-icon" href="/static/icon-192.png">
    <link rel="manifest" href="/static/manifest.json">
    <meta name="theme-color" content="#0A7A0A">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        :root {
            --safe-area-top: env(safe-area-inset-top, 0px);
            --safe-area-bottom: env(safe-area-inset-bottom, 0px);
            --color-primary: #0A7A0A;
            --color-primary-dark: #085A08;
            --color-danger: #CC0000;
            --color-neutral: #333333;
        }
        
        html {
            height: 100%;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #FFFFFF;
            min-height: 100%;
            min-height: 100dvh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 16px;
            padding-top: calc(16px + var(--safe-area-top));
            padding-bottom: calc(16px + var(--safe-area-bottom));
        }
        
        .login-card {
            background: white;
            padding: 24px;
            border-radius: 24px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.12);
            text-align: center;
            max-width: 100%;
            width: 100%;
        }
        
        @media (min-width: 768px) {
            .login-card {
                padding: 48px;
                max-width: 500px;
            }
        }
        
        h1 {
            font-size: 3rem;
            margin-bottom: 12px;
        }
        
        @media (min-width: 768px) {
            h1 {
                font-size: 4rem;
                margin-bottom: 16px;
            }
        }
        
        .subtitle {
            font-size: 1.4rem;
            color: #000;
            margin-bottom: 16px;
            font-weight: 800;
        }
        
        @media (min-width: 768px) {
            .subtitle {
                font-size: 1.6rem;
                margin-bottom: 20px;
            }
        }
        
        /* Welcome message */
        .welcome-message {
            font-size: 1.2rem;
            color: var(--color-primary);
            margin-bottom: 32px;
            font-weight: 600;
        }
        
        @media (min-width: 768px) {
            .welcome-message {
                font-size: 1.4rem;
                margin-bottom: 40px;
            }
        }
        
        /* PIN instruction text */
        .pin-instruction {
            font-size: 1.8rem;
            font-weight: 700;
            color: #333;
            margin-bottom: 20px;
            text-align: center;
        }
        
        @media (min-width: 768px) {
            .pin-instruction {
                font-size: 2.2rem;
                margin-bottom: 24px;
            }
        }
        
        /* PIN INPUT - Mobile first */
        .pin-container {
            display: flex;
            gap: 10px;
            justify-content: center;
            margin-bottom: 24px;
        }
        
        @media (min-width: 768px) {
            .pin-container {
                gap: 16px;
                margin-bottom: 32px;
            }
        }
        
        .pin-digit {
            width: 60px;
            height: 60px;
            font-size: 1.75rem;
            text-align: center;
            border: 4px solid var(--color-neutral);
            border-radius: 12px;
            font-weight: 800;
            background: white;
        }
        
        @media (min-width: 768px) {
            .pin-digit {
                width: 80px;
                height: 80px;
                font-size: 2.5rem;
                border-radius: 16px;
            }
        }
        
        .pin-digit:focus {
            outline: none;
            border-color: var(--color-primary);
            background: #F0FDF4;
        }
        
        /* Hidden actual input */
        .pin-input-hidden {
            position: absolute;
            opacity: 0;
            pointer-events: none;
        }
        
        .error {
            background: var(--color-danger);
            color: white;
            padding: 16px;
            border-radius: 12px;
            margin-bottom: 20px;
            font-weight: 800;
            font-size: 1rem;
        }
        
        @media (min-width: 768px) {
            .error {
                padding: 20px;
                margin-bottom: 24px;
                font-size: 1.2rem;
            }
        }
        
    </style>
</head>
<body>
    <div class="login-card">
        <h1>RentasClaras</h1>
        <div class="welcome-message">¡Bienvenidos papis! 💚</div>
        
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
        
        <form method="POST" action="/login" id="loginForm">
            <!-- Instruction above PIN boxes -->
            <div class="pin-instruction">Ingrese su PIN</div>
            
            <!-- #12: Large digit boxes for visual PIN entry -->
            <div class="pin-container" onclick="document.getElementById('pinInput').focus()">
                <input type="text" class="pin-digit" id="pin1" maxlength="1" readonly placeholder="●">
                <input type="text" class="pin-digit" id="pin2" maxlength="1" readonly placeholder="●">
                <input type="text" class="pin-digit" id="pin3" maxlength="1" readonly placeholder="●">
                <input type="text" class="pin-digit" id="pin4" maxlength="1" readonly placeholder="●">
            </div>
            
            <!-- Hidden actual input that receives the PIN -->
            <input type="password" 
                   name="pin" 
                   id="pinInput"
                   class="pin-input-hidden" 
                   maxlength="4"
                   inputmode="numeric"
                   pattern="[0-9]*"
                   autofocus
                   required>
            
        </form>
    </div>
    
    <script>
        // #12: PIN box visual feedback
        const pinInput = document.getElementById('pinInput');
        const digits = [
            document.getElementById('pin1'),
            document.getElementById('pin2'),
            document.getElementById('pin3'),
            document.getElementById('pin4')
        ];
        
        pinInput.addEventListener('input', function() {
            const value = this.value;
            
            digits.forEach((digit, index) => {
                if (value[index]) {
                    digit.value = '●';
                    digit.style.borderColor = '#0A7A0A';
                    digit.style.background = '#F0FDF4';
                } else {
                    digit.value = '';
                    digit.style.borderColor = '#333333';
                    digit.style.background = 'white';
                }
            });
            
            // Auto-submit when 4 digits entered
            if (value.length === 4) {
                setTimeout(() => {
                    document.getElementById('loginForm').submit();
                }, 300);
            }
        });
        
        // Focus the hidden input when clicking anywhere in the PIN container
        document.querySelector('.pin-container').addEventListener('click', function() {
            pinInput.focus();
        });
        
        // Mobile keyboard scroll fix - scroll PIN container into view when focused
        pinInput.addEventListener('focus', function() {
            // Small delay to wait for keyboard to appear
            setTimeout(() => {
                const pinContainer = document.querySelector('.pin-container');
                if (pinContainer) {
                    pinContainer.scrollIntoView({ 
                        behavior: 'smooth', 
                        block: 'center' 
                    });
                }
            }, 300);
        });
        
        // Also handle visual viewport resize (when keyboard appears)
        if (window.visualViewport) {
            window.visualViewport.addEventListener('resize', function() {
                if (document.activeElement === pinInput) {
                    const pinContainer = document.querySelector('.pin-container');
                    if (pinContainer) {
                        pinContainer.scrollIntoView({ 
                            behavior: 'smooth', 
                            block: 'center' 
                        });
                    }
                }
            });
        }
        
        // Focus on page load
        pinInput.focus();
    </script>
</body>
</html>
"""


@app.route("/")
@login_required
def index():
    # Get year/month from query params or use current
    today = datetime.now()
    
    # AUTO-SWITCH: After day 7, default to next month (rent collection is done)
    # This helps landlord focus on preparing for next month's collection
    if today.day > 7:
        if today.month == 12:
            default_year = today.year + 1
            default_month = 1
        else:
            default_year = today.year
            default_month = today.month + 1
    else:
        default_year = today.year
        default_month = today.month
    
    year = request.args.get("year", default_year, type=int)
    month = request.args.get("month", default_month, type=int)

    # #5: Calculate prev/next month for month selector arrows
    # MINIMUM DATE: January 2026 (no data before this)
    MIN_YEAR = 2026
    MIN_MONTH = 1

    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year

    # Check if we can go back (not before December 2025)
    can_go_prev = (prev_year > MIN_YEAR) or (
        prev_year == MIN_YEAR and prev_month >= MIN_MONTH
    )

    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year

    # #10: Check if we're viewing the current month (for HOY button)
    is_current_month = year == today.year and month == today.month

    # Check if we're viewing a future month (no late fees for future months)
    is_future_month = (year > today.year) or (
        year == today.year and month > today.month
    )

    # Get payment status for this month
    monthly_status = get_monthly_status(year, month)
    
    # Get message counts for this month
    message_counts = get_message_counts_for_month(year, month)

    # Get tenants grouped by property with payment status
    all_tenants = get_all_tenants()
    tenants_by_property = {}

    for tenant in all_tenants:
        # Merge payment status into tenant
        status = monthly_status.get(tenant.id, {})
        tenant.paid = bool(status.get("paid", 0))
        tenant.payment_method = status.get("payment_method")
        
        # Add message count for this tenant
        msg_info = message_counts.get(tenant.id, {"sent": 0, "failed": 0})
        tenant.msg_count = msg_info["sent"]
        tenant.msg_failed = msg_info["failed"]

        if tenant.property_name not in tenants_by_property:
            tenants_by_property[tenant.property_name] = []
        tenants_by_property[tenant.property_name].append(tenant)

    # Sort tenants: UNPAID FIRST (so mom doesn't have to scroll past paid ones)
    # Within each group, sort by unit number for consistency
    for property_name in tenants_by_property:
        tenants_by_property[property_name].sort(
            key=lambda t: (t.paid, t.unit)  # False (unpaid) comes before True (paid)
        )

    # Get Spanish month name
    spanish_months = [
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    ]
    month_name = spanish_months[month - 1]

    # Get available months for selector
    available_months = get_available_months()

    # Calculate total rent for grand total
    total_rent = sum(tenant.rent for tenant in all_tenants)

    # Helper function to format dates in Spanish
    spanish_months_lower = [
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    ]

    def format_date_spanish(date_str):
        if not date_str:
            return None
        try:
            parsed = datetime.strptime(date_str, "%Y-%m-%d")
        except:
            try:
                parsed = datetime.strptime(date_str, "%d/%m/%Y")
            except:
                return date_str
        return f"{parsed.day} de {spanish_months_lower[parsed.month - 1]} {parsed.year}"

    def format_date_excel(date_str):
        """Format date as M/D/YYYY for Excel-style display"""
        if not date_str:
            return None
        try:
            parsed = datetime.strptime(date_str, "%Y-%m-%d")
        except:
            try:
                parsed = datetime.strptime(date_str, "%d/%m/%Y")
            except:
                return date_str
        return f"{parsed.month}/{parsed.day}/{parsed.year}"

    # Format contract dates for each tenant and calculate late fees
    # Calculate days late based on which month we're viewing
    for tenant in all_tenants:
        tenant.contract_start_formatted = format_date_excel(tenant.contract_start)
        tenant.contract_end_formatted = format_date_excel(tenant.contract_end)

        # Calculate days late and late fees for unpaid tenants
        if not tenant.paid:
            # Future months: no late fees yet (month hasn't happened)
            if is_future_month:
                tenant.days_late = 0
                tenant.late_fee = 0
                tenant.total_owed = float(tenant.rent)
            # If viewing current month, use today's day
            elif is_current_month:
                day_of_calculation = today.day
                # Days late = day - 1 (Day 1 is not late, Day 2 = 1 day late)
                tenant.days_late = max(0, day_of_calculation - 1)

                # Calculate late fees: $500 initial (after day 1) + $100/day (after day 2, max 5 days)
                if tenant.days_late >= 1:
                    initial_penalty = 500
                    # Daily penalty: starts day 3 (days_late >= 2), max 5 days
                    daily_penalty_days = min(max(0, tenant.days_late - 1), 5)
                    daily_penalty = daily_penalty_days * 100
                    tenant.late_fee = initial_penalty + daily_penalty
                    tenant.total_owed = float(tenant.rent) + tenant.late_fee
                else:
                    tenant.late_fee = 0
                    tenant.total_owed = float(tenant.rent)
            else:
                # For past months, assume they're fully late (end of month)
                import calendar

                day_of_calculation = calendar.monthrange(year, month)[1]
                # Days late = day - 1 (Day 1 is not late, Day 2 = 1 day late)
                tenant.days_late = max(0, day_of_calculation - 1)

                # Calculate late fees: $500 initial (after day 1) + $100/day (after day 2, max 5 days)
                if tenant.days_late >= 1:
                    initial_penalty = 500
                    # Daily penalty: starts day 3 (days_late >= 2), max 5 days
                    daily_penalty_days = min(max(0, tenant.days_late - 1), 5)
                    daily_penalty = daily_penalty_days * 100
                    tenant.late_fee = initial_penalty + daily_penalty
                    tenant.total_owed = float(tenant.rent) + tenant.late_fee
                else:
                    tenant.late_fee = 0
                    tenant.total_owed = float(tenant.rent)
        else:
            tenant.days_late = 0
            tenant.late_fee = 0
            tenant.total_owed = float(tenant.rent)

    # Get expiring contracts for the alert banner (60 days ahead)
    expiring_contracts = get_expiring_contracts(days_ahead=60)
    # Count by urgency for the banner
    expiring_critical = [c for c in expiring_contracts if c["urgency"] == "critical"]
    expiring_warning = [c for c in expiring_contracts if c["urgency"] == "warning"]
    expiring_expired = [c for c in expiring_contracts if c["urgency"] == "expired"]

# Calculate total late fees and total owed (for top banner)
    total_late_fees = sum(t.late_fee for t in all_tenants if not t.paid)
    total_owed = sum(t.total_owed for t in all_tenants if not t.paid)
    unpaid_count = sum(1 for t in all_tenants if not t.paid)

    # Get last sync time for the indicator
    last_sync = get_last_sync_time()
    last_sync_relative = None
    if last_sync:
        try:
            sync_dt = datetime.fromisoformat(last_sync.replace('Z', '+00:00'))
            diff = datetime.now() - sync_dt.replace(tzinfo=None)
            seconds = diff.total_seconds()
            if seconds < 60:
                last_sync_relative = "hace unos segundos"
            elif seconds < 3600:
                minutes = int(seconds / 60)
                last_sync_relative = f"hace {minutes} minuto{'s' if minutes != 1 else ''}"
            elif seconds < 86400:
                hours = int(seconds / 3600)
                last_sync_relative = f"hace {hours} hora{'s' if hours != 1 else ''}"
            else:
                days = int(seconds / 86400)
                last_sync_relative = f"hace {days} día{'s' if days != 1 else ''}"
        except:
            last_sync_relative = last_sync[:16] if last_sync else None

    return render_template_string(
        HTML_TEMPLATE,
        tenants=all_tenants,
        tenants_by_property=tenants_by_property,
        total_tenants=len(all_tenants),
        total_rent=total_rent,
        total_late_fees=total_late_fees,
        total_owed=total_owed,
        unpaid_count=unpaid_count,
        current_date=today.strftime("%d de %B, %Y"),
        day_of_month=today.day,
        month_name=month_name,
        year=year,
        month=month,
        prev_month=prev_month,
        prev_year=prev_year,
        next_month=next_month,
        next_year=next_year,
        available_months=available_months,
        test_mode=TEST_MODE,
        test_phone=TEST_PHONE,
        is_current_month=is_current_month,
        can_go_prev=can_go_prev,
expiring_contracts=expiring_contracts,
        expiring_critical=expiring_critical,
        expiring_warning=expiring_warning,
        expiring_expired=expiring_expired,
        last_sync=last_sync,
        last_sync_relative=last_sync_relative,
        now=datetime.now(),
    )


@app.route("/api/message")
def get_message():
    tenant_id = request.args.get("tenant_id")

    # Find tenant from database
    all_tenants = get_all_tenants()
    tenant = next((t for t in all_tenants if t.id == tenant_id), None)
    if not tenant:
        return jsonify({"error": "Tenant not found"}), 404

    # Get current month name
    today = datetime.now()
    spanish_months = [
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    ]
    month_name = spanish_months[today.month - 1]

    # Generate message
    message = generate_rent_reminder(tenant, month_name)

    # Create WhatsApp link
    phone = TEST_PHONE if TEST_MODE else tenant.phone
    whatsapp_url = create_whatsapp_link(phone, message)

    return jsonify(
        {
            "tenant_id": tenant_id,
            "tenant_name": tenant.name,
            "message": message,
            "whatsapp_url": whatsapp_url,
        }
    )


@app.route("/api/tenants")
def list_tenants():
    all_tenants = get_all_tenants()
    return jsonify(
        [
            {
                "id": t.id,
                "name": t.name,
                "phone": t.phone,
                "property": t.property_name,
                "unit": t.unit,
                "rent": float(t.rent),
                "paid": t.paid,
            }
            for t in all_tenants
        ]
    )


@app.route("/api/payment", methods=["POST"])
def update_payment():
    """Update payment status for a tenant and sync to Excel"""
    data = request.json
    tenant_id = data.get("tenant_id")
    paid = data.get("paid", False)
    payment_method = data.get("payment_method")

    today = datetime.now()

    # Update local SQLite database
    update_payment_status(
        tenant_id=tenant_id,
        year=today.year,
        month=today.month,
        paid=paid,
        payment_method=payment_method,
    )

    # Sync to Excel if payment is marked as paid
    if paid:
        try:
            from src.excel_client import (
                ExcelClient,
                ExcelConfig,
                generate_payment_id,
                PaymentRow,
            )

            # Get tenant info to populate Excel record
            tenant = get_tenant_by_id(tenant_id)
            if tenant:
                config = ExcelConfig.from_env()
                client = ExcelClient(config)
                client.authenticate()

                # Create payment record for Excel
                spanish_months = [
                    "Enero",
                    "Febrero",
                    "Marzo",
                    "Abril",
                    "Mayo",
                    "Junio",
                    "Julio",
                    "Agosto",
                    "Septiembre",
                    "Octubre",
                    "Noviembre",
                    "Diciembre",
                ]
                month_name = spanish_months[today.month - 1]

                payment = PaymentRow(
                    payment_id=generate_payment_id(),
                    tenant_id=tenant_id,
                    payment_date=today.strftime("%Y-%m-%d"),
                    amount=tenant.rent,
                    method=payment_method or "Web UI",
                    withdrawal_code=None,
                    bank=tenant.bank,
                    concept=f"Renta {month_name} {today.year}",
                    folio=f"RC-{today.strftime('%Y%m%d')}-{tenant_id}",
                    confirmed=True,
                    notes="Marcado pagado desde la vista de tarjetas",
                )
                client.add_payment(payment)
                print(f"✅ Synced payment for {tenant.name} to Excel")
        except ImportError as e:
            print(f"⚠️ Excel sync skipped - missing dependencies: {e}")
        except Exception as e:
            print(f"⚠️ Excel sync failed (payment saved locally): {e}")

    return jsonify({"success": True})


@app.route("/api/phone", methods=["POST"])
def update_phone():
    """Update phone number for a tenant"""
    data = request.json
    tenant_id = data.get("tenant_id")
    phone = data.get("phone", "")

    update_tenant_phone(tenant_id, phone)

    return jsonify({"success": True})


@app.route("/api/renewal", methods=["POST"])
def update_renewal():
    """Update contract renewal status for a tenant"""
    data = request.json
    tenant_id = data.get("tenant_id")

    update_renewal_status(
        tenant_id=tenant_id,
        renewal_status=data.get("renewal_status"),
        contract_delivered=data.get("contract_delivered"),
        contract_picked_up=data.get("contract_picked_up"),
        leaving_date=data.get("leaving_date"),
        replacement_name=data.get("replacement_name"),
        replacement_phone=data.get("replacement_phone"),
        replacement_contract_start=data.get("replacement_contract_start"),
        replacement_contract_end=data.get("replacement_contract_end"),
        replacement_aval_name=data.get("replacement_aval_name"),
        replacement_aval_phone=data.get("replacement_aval_phone"),
    )

    return jsonify({"success": True})


# =============================================================================
# BACKUP API ENDPOINTS
# =============================================================================


@app.route("/api/backups", methods=["GET"])
@login_required
def api_list_backups():
    """List all database backups."""
    try:
        from src.backup import list_backups, get_backup_stats
        
        backups = list_backups()
        stats = get_backup_stats()
        
        return jsonify({
            "success": True,
            "backups": backups,
            "stats": stats
        })
    except ImportError:
        return jsonify({
            "success": False,
            "error": "Backup module not available"
        }), 500


@app.route("/api/backups", methods=["POST"])
@login_required
def api_create_backup():
    """Create a new backup now."""
    try:
        from src.backup import create_backup
        
        result = create_backup(verify_first=True)
        
        return jsonify({
            "success": result["success"],
            "message": result["message"],
            "backup_path": result.get("backup_path"),
            "size_mb": result.get("size_mb")
        })
    except ImportError:
        return jsonify({
            "success": False,
            "error": "Backup module not available"
        }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/backups/restore/<filename>", methods=["POST"])
@login_required
def api_restore_backup(filename):
    """
    Restore database from a backup file.
    
    DANGEROUS OPERATION - requires explicit confirmation.
    Request body must include: {"confirm": "YES_RESTORE"}
    """
    try:
        from src.backup import restore_backup
        
        data = request.json or {}
        confirm = data.get("confirm")
        
        if confirm != "YES_RESTORE":
            return jsonify({
                "success": False,
                "error": "Must confirm with 'YES_RESTORE' in request body"
            }), 400
        
        result = restore_backup(filename, create_safety_backup=True)
        
        if result["success"]:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except ImportError:
        return jsonify({
            "success": False,
            "error": "Backup module not available"
        }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/sync-status", methods=["GET"])
def api_sync_status():
    """Get the last sync time and database health."""
    last_sync = get_last_sync_time()
    
    # Calculate relative time
    last_sync_relative = None
    if last_sync:
        try:
            sync_dt = datetime.fromisoformat(last_sync.replace('Z', '+00:00'))
            diff = datetime.now() - sync_dt.replace(tzinfo=None)
            seconds = diff.total_seconds()
            if seconds < 60:
                last_sync_relative = "hace unos segundos"
            elif seconds < 3600:
                minutes = int(seconds / 60)
                last_sync_relative = f"hace {minutes} minuto{'s' if minutes != 1 else ''}"
            elif seconds < 86400:
                hours = int(seconds / 3600)
                last_sync_relative = f"hace {hours} hora{'s' if hours != 1 else ''}"
            else:
                days = int(seconds / 86400)
                last_sync_relative = f"hace {days} día{'s' if days != 1 else ''}"
        except:
            last_sync_relative = last_sync[:16] if last_sync else None
    
    return jsonify({
        "success": True,
        "last_sync": last_sync,
        "last_sync_relative": last_sync_relative
    })


@app.route("/api/whatsapp/status")
def whatsapp_status():
    """Check if WhatsApp API is configured"""
    try:
        from src.whatsapp_client import check_credentials

        return jsonify(check_credentials())
    except ImportError:
        return jsonify({"configured": False, "error": "whatsapp_client not found"})


@app.route("/api/whatsapp/send-all", methods=["POST"])
def send_all_whatsapp():
    """
    Send WhatsApp reminders to all unpaid tenants via Meta Cloud API.

    This is the main automation endpoint that:
    1. Gets all tenants who haven't paid this month
    2. Sends each a personalized rent reminder
    3. Returns a summary of what was sent
    """
    try:
        from src.whatsapp_client import check_credentials, send_rent_reminder
    except ImportError:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "WhatsApp client not installed. Check src/whatsapp_client.py",
                }
            ),
            500,
        )

    # Check if credentials are configured
    creds = check_credentials()
    if not creds["configured"]:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "WhatsApp API not configured. See docs/SETUP_WHATSAPP_API.md",
                    "credentials": creds,
                }
            ),
            400,
        )

    # Get current month info
    today = datetime.now()
    spanish_months = [
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    ]
    month_name = spanish_months[today.month - 1]

    # Get payment status for this month
    monthly_status = get_monthly_status(today.year, today.month)

    # Get all tenants
    all_tenants = get_all_tenants()

    # Filter to unpaid tenants with phone numbers
    results = {"sent": [], "failed": [], "skipped_paid": [], "skipped_no_phone": []}

    for tenant in all_tenants:
        # Check if paid
        status = monthly_status.get(tenant.id, {})
        is_paid = bool(status.get("paid", 0))

        if is_paid:
            results["skipped_paid"].append(
                {"id": tenant.id, "name": tenant.name, "reason": "Already paid"}
            )
            continue

        # Check if has phone
        if not tenant.phone:
            results["skipped_no_phone"].append(
                {"id": tenant.id, "name": tenant.name, "reason": "No phone number"}
            )
            continue

        # Extract display name
        display_name = extract_display_name(tenant.name)

        # Format amount with commas
        amount_str = f"{tenant.rent:,.0f}"

        # Send WhatsApp message
        response = send_rent_reminder(
            to_phone=tenant.phone,
            tenant_name=display_name,
            month=month_name,
            amount=amount_str,
        )

        if response.success:
            results["sent"].append(
                {
                    "id": tenant.id,
                    "name": tenant.name,
                    "phone": tenant.phone,
                    "message_id": response.message_id,
                }
            )
        else:
            results["failed"].append(
                {
                    "id": tenant.id,
                    "name": tenant.name,
                    "phone": tenant.phone,
                    "error": response.error,
                }
            )

    return jsonify(
        {
            "success": True,
            "summary": {
                "total_tenants": len(all_tenants),
                "sent": len(results["sent"]),
                "failed": len(results["failed"]),
                "skipped_paid": len(results["skipped_paid"]),
                "skipped_no_phone": len(results["skipped_no_phone"]),
            },
            "details": results,
        }
    )


@app.route("/api/whatsapp/send-one", methods=["POST"])
def send_one_whatsapp():
    """Send WhatsApp reminder to a single tenant"""
    try:
        from src.whatsapp_client import check_credentials, send_rent_reminder
    except ImportError:
        return jsonify({"success": False, "error": "WhatsApp client not found"}), 500

    creds = check_credentials()
    if not creds["configured"]:
        return jsonify({"success": False, "error": "WhatsApp API not configured"}), 400

    data = request.json
    tenant_id = data.get("tenant_id")

    if not tenant_id:
        return jsonify({"success": False, "error": "tenant_id required"}), 400

    # Find tenant
    all_tenants = get_all_tenants()
    tenant = next((t for t in all_tenants if t.id == tenant_id), None)

    if not tenant:
        return jsonify({"success": False, "error": "Tenant not found"}), 404

    if not tenant.phone:
        return jsonify({"success": False, "error": "Tenant has no phone number"}), 400

    # Get month name
    today = datetime.now()
    spanish_months = [
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    ]
    month_name = spanish_months[today.month - 1]

    # Send message
    display_name = extract_display_name(tenant.name)
    amount_str = f"{tenant.rent:,.0f}"

    response = send_rent_reminder(
        to_phone=tenant.phone,
        tenant_name=display_name,
        month=month_name,
        amount=amount_str,
    )

    if response.success:
        return jsonify(
            {"success": True, "message_id": response.message_id, "tenant": tenant.name}
        )
    else:
        return jsonify({"success": False, "error": response.error}), 500


@app.route("/api/database/health", methods=["GET"])
@login_required
def api_database_health():
    """Check database health and integrity."""
    from src.backup import verify_database_integrity, get_db_path, get_backup_stats
    
    db_path = get_db_path()
    
    if not db_path.exists():
        return jsonify({
            "healthy": False,
            "message": "Database file not found",
            "path": str(db_path)
        }), 500
    
    is_ok, message = verify_database_integrity(db_path)
    stats = get_backup_stats()
    
    return jsonify({
        "healthy": is_ok,
        "message": message,
        "database_path": str(db_path),
        "database_size_mb": stats.get("database_size_mb", 0),
        "total_backups": stats.get("total_backups", 0),
        "newest_backup": stats.get("newest_backup"),
        "backup_dir_exists": stats.get("backup_dir_exists", False)
    })

CONTRACTS_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <title>RentasClaras - Contratos</title>
    <link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
    <link rel="apple-touch-icon" href="/static/icon-192.png">
    <link rel="manifest" href="/static/manifest.json">
    <meta name="theme-color" content="#0A7A0A">
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        :root {
            --safe-area-top: env(safe-area-inset-top, 0px);
            --safe-area-bottom: env(safe-area-inset-bottom, 0px);
            --color-primary: #0A7A0A;
            --color-danger: #CC0000;
            --color-neutral: #333333;
            --color-neutral-light: #F5F5F5;
            --color-white: #FFFFFF;
            --color-border: #CCCCCC;
            --color-black: #000000;
            --color-accent: #7c3aed;
            --space-sm: 8px;
            --space-md: 16px;
            --space-lg: 24px;
            --space-xl: 32px;
            --radius-md: 12px;
            --radius-lg: 16px;
            --touch-target-min: 48px;
            --touch-target-lg: 56px;
        }
        
        /* ===========================================
           UNIFIED SEARCH BAR STYLES
           Shared between Pagos and Contratos tabs
           =========================================== */
        .search-wrapper {
            position: relative;
            width: 100%;
        }
        
        .search-input-styled {
            width: 100%;
            padding: 16px 48px 16px 48px;
            font-size: 1.1rem;
            border: 3px solid var(--color-border);
            border-radius: var(--radius-md);
            background: var(--color-white);
            color: var(--color-black);
            box-sizing: border-box;
        }
        
        .search-input-styled:focus {
            outline: none;
            border-color: var(--color-primary);
        }
        
        .search-icon {
            position: absolute;
            left: 16px;
            top: 50%;
            transform: translateY(-50%);
            width: 20px;
            height: 20px;
            color: #999;
            pointer-events: none;
        }
        
        .search-clear-btn {
            position: absolute;
            right: 0;
            top: 0;
            bottom: 0;
            width: 48px;
            display: none;
            align-items: center;
            justify-content: center;
            background: none;
            border: none;
            font-size: 1.3rem;
            cursor: pointer;
            color: #666;
            padding: 0;
        }
        
        .search-clear-btn:hover {
            color: var(--color-danger);
        }
        
        .search-clear-btn.visible {
            display: flex;
        }
        
        /* ===========================================
           PROMINENT SEARCH SECTION STYLES
           Used for both Pagos and Contratos tabs
           =========================================== */
        .prominent-search-section {
            margin-bottom: 20px;
            position: sticky;
            top: 0;
            z-index: 100;
            background: var(--color-primary);
            padding: 16px;
            margin-left: -16px;
            margin-right: -16px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }
        
        .prominent-search-label {
            color: white;
            font-size: 1.1rem;
            font-weight: 800;
            margin-bottom: 10px;
            text-align: center;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .prominent-search-input {
            font-size: 1.4rem;
            padding: 20px 56px 20px 20px;
            border: 4px solid #065F06;
            border-radius: 16px;
            box-shadow: inset 0 2px 8px rgba(0,0,0,0.1);
            font-weight: 600;
            background: white;
        }
        
        .prominent-search-clear {
            font-size: 2rem;
            width: 56px;
            color: var(--color-danger);
            font-weight: bold;
        }
        
        .prominent-search-results {
            margin-top: 12px;
            color: white;
            font-size: 1.2rem;
            font-weight: 700;
            display: none;
            text-align: center;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f0;
            min-height: 100vh;
            min-height: -webkit-fill-available;
            color: #1a1a1a;
            padding: var(--space-md);
            padding-top: calc(var(--space-md) + var(--safe-area-top));
            padding-bottom: calc(80px + var(--safe-area-bottom)); /* Space for bottom nav */
            font-size: 1rem;
            line-height: 1.5;
        }
        
        @media (min-width: 768px) {
            body {
                padding: var(--space-lg);
                padding-bottom: var(--space-lg);
                font-size: 18px;
            }
        }
        
        .container {
            max-width: 100%;
            margin: 0 auto;
        }
        
        @media (min-width: 768px) {
            .container {
                max-width: 900px;
            }
        }
        
        header {
            text-align: center;
            margin-bottom: var(--space-lg);
            background: var(--color-white);
            padding: var(--space-md);
            border-radius: var(--radius-lg);
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        
        @media (min-width: 768px) {
            header {
                padding: var(--space-lg);
                margin-bottom: var(--space-xl);
            }
        }
        
        h1 {
            font-size: 1.75rem;
            margin-bottom: var(--space-sm);
            color: #000000;
            font-weight: 800;
        }
        
        @media (min-width: 768px) {
            h1 {
                font-size: 2.2rem;
            }
        }
        
        .subtitle {
            color: #4a4a4a;
            font-size: 1rem;
        }
        
        @media (min-width: 768px) {
            .subtitle {
                font-size: 1.1rem;
            }
        }
        
        /* Navigation Tabs - hidden on mobile (use bottom nav) */
        .nav-tabs {
            display: none;
            gap: var(--space-md);
            justify-content: center;
            margin-bottom: var(--space-lg);
        }
        
        @media (min-width: 768px) {
            .nav-tabs {
                display: flex;
            }
        }
        
        .nav-tab {
            display: inline-flex;
            align-items: center;
            gap: var(--space-sm);
            padding: var(--space-md) var(--space-lg);
            border-radius: var(--radius-md);
            text-decoration: none;
            font-size: 1.1rem;
            font-weight: 800;
            transition: all 0.2s;
            min-height: var(--touch-target-lg);
            border: 4px solid;
        }
        
        .nav-tab.active {
            background: var(--color-accent);
            color: var(--color-white);
            border-color: var(--color-accent);
        }
        
        .nav-tab:not(.active) {
            background: var(--color-white);
            color: var(--color-accent);
            border-color: var(--color-accent);
        }
        
        .nav-tab:not(.active):hover {
            background: #f3e8ff;
        }
        
        /* ===========================================
           TOP NAVBAR - Always visible (UNIFIED with Pagos)
           =========================================== */
        .top-navbar {
            display: flex;
            gap: var(--space-sm);
            justify-content: center;
            margin: var(--space-md) 0;
            padding: var(--space-sm);
            background: var(--color-neutral-light);
            border-radius: var(--radius-lg);
        }
        
        .top-navbar-item {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: var(--space-sm);
            flex: 1;
            padding: var(--space-md) var(--space-lg);
            border-radius: var(--radius-md);
            text-decoration: none;
            font-size: var(--font-size-base);
            font-weight: 800;
            transition: all 0.2s;
            min-height: var(--touch-target-min);
            border: none;
            cursor: pointer;
        }
        
        .top-navbar-item.active {
            background: var(--color-primary);
            color: var(--color-white);
            box-shadow: 0 2px 8px rgba(10, 122, 10, 0.3);
        }

        .top-navbar-item:not(.active) {
            background: var(--color-white);
            color: var(--color-neutral);
        }
        
        .top-navbar-item:not(.active):hover {
            background: var(--color-white);
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .top-navbar-icon {
            font-size: 1.3rem;
        }
        
        @media (min-width: 768px) {
            .top-navbar {
                max-width: 500px;
                margin: var(--space-lg) auto;
            }
            
            .top-navbar-item {
                font-size: var(--font-size-lg);
                padding: var(--space-lg) var(--space-xl);
            }
            
            .top-navbar-icon {
                font-size: 1.5rem;
            }
        }
        
        /* Bottom Navigation */
        .bottom-nav {
            display: flex;
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: var(--color-white);
            border-top: 2px solid #CCCCCC;
            padding: var(--space-sm);
            padding-bottom: calc(var(--space-sm) + var(--safe-area-bottom));
            z-index: 1000;
            justify-content: space-around;
            gap: var(--space-sm);
            box-shadow: 0 -4px 12px rgba(0,0,0,0.1);
        }
        
        @media (min-width: 768px) {
            .bottom-nav {
                display: none;
            }
        }
        
        .bottom-nav-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-decoration: none;
            color: var(--color-neutral);
            font-size: 0.75rem;
            font-weight: 700;
            padding: var(--space-sm);
            border-radius: var(--radius-md);
            min-width: 64px;
            min-height: var(--touch-target-min);
            transition: all 0.2s;
            background: none;
            border: none;
            cursor: pointer;
        }
        
        .bottom-nav-item.active {
            color: var(--color-accent);
            background: rgba(124, 58, 237, 0.1);
        }
        
        .bottom-nav-icon {
            font-size: 1.5rem;
            margin-bottom: 2px;
        }
        
        /* Summary cards - mobile first (stacked) */
        .summary {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: var(--space-sm);
            margin-bottom: var(--space-lg);
        }
        
        @media (min-width: 768px) {
            .summary {
                grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
                gap: var(--space-md);
                margin-bottom: var(--space-xl);
            }
        }
        
        .summary-card {
            background: var(--color-white);
            padding: var(--space-md);
            border-radius: var(--radius-lg);
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        
        @media (min-width: 768px) {
            .summary-card {
                padding: var(--space-lg);
            }
        }
        
        .summary-value {
            font-size: 1.75rem;
            font-weight: 800;
        }
        
        @media (min-width: 768px) {
            .summary-value {
                font-size: 2.2rem;
            }
        }
        
        .summary-value.green { color: var(--color-primary); }
        .summary-value.red { color: var(--color-danger); }
        .summary-value.yellow { color: var(--color-neutral); }
        
        .summary-label {
            color: var(--color-neutral);
            font-size: 0.875rem;
            margin-top: var(--space-sm);
            font-weight: 600;
        }
        
        @media (min-width: 768px) {
            .summary-label {
                font-size: 0.95rem;
            }
        }
        
        /* Upcoming renewals */
        .upcoming-section {
            background: var(--color-white);
            border-radius: var(--radius-lg);
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            margin-bottom: var(--space-lg);
            overflow: hidden;
        }
        
        .upcoming-header {
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
            color: var(--color-white);
            padding: var(--space-md);
            font-weight: 700;
            font-size: 1rem;
        }
        
        @media (min-width: 768px) {
            .upcoming-header {
                padding: var(--space-md) var(--space-lg);
                font-size: 1.2rem;
            }
        }
        
        .upcoming-list {
            padding: 0;
        }
        
        /* Month section header */
        .month-section {
            border-bottom: 3px solid #e5e5e5;
        }
        
        .month-section:last-child {
            border-bottom: none;
        }
        
        .month-header {
            background: #f3f4f6;
            padding: 14px 24px;
            font-size: 1.2rem;
            font-weight: 800;
            color: #1a1a1a;
            border-bottom: 2px solid #e5e5e5;
        }
        
        .upcoming-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 24px;
            border-bottom: 2px solid #e5e5e5;
            gap: 16px;
            flex-wrap: wrap;
        }
        
        .upcoming-item:last-child {
            border-bottom: none;
        }
        
        .upcoming-item.renewing {
            background: #f0fdf4;
            border-left: 6px solid #0A7A0A;  /* System green */
        }
        
        .upcoming-item.not-renewing {
            background: #fef2f2;
            border-left: 6px solid #CC0000;  /* System red */
        }
        
        .upcoming-item.pending {
            background: #F5F5F5;  /* Changed to gray - 3-color system */
            border-left: 6px solid #333333;
        }
          
        /* URGENT: Contracts expiring in <30 days */
        .upcoming-item.expiring-soon {
            background: #fef2f2;
            border-left: 6px solid #CC0000;  /* System red */
        }
          
        .expiring-soon-badge {
            display: inline-block;
            background: #dc2626;
            color: white;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.85rem;
            font-weight: 700;
            margin-left: 8px;
        }
        
        .upcoming-info {
            display: flex;
            align-items: center;
            gap: 16px;
            flex: 1;
            flex-wrap: wrap;
        }
        
        .upcoming-name {
            font-size: 1.15rem;
            color: #1a1a1a;
            font-weight: 600;
        }
        
        .upcoming-date {
            font-size: 1.15rem;
            color: #1a1a1a;
            font-weight: 700;
        }
        
        .upcoming-status {
            flex-shrink: 0;
        }
        
        .status-badge {
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.95rem;
            font-weight: 700;
        }
        
        .status-badge.green {
            background: #dcfce7;
            color: #166534;
        }
        
        .status-badge.red {
            background: #fee2e2;
            color: #dc2626;
        }
        
        .status-badge.yellow {
            background: #fef3c7;
            color: #92400e;
        }
        
        /* Property section */
        .property-section {
            margin-bottom: 40px;
            background: white;
            border-radius: 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            overflow: hidden;
        }
        
        .property-header {
            background: #7c3aed;
            color: white;
            padding: 16px 24px;
            font-weight: 700;
            font-size: 1.2rem;
        }
        
        /* Contract card */
        .contract-card {
            padding: 20px;
            border-bottom: 2px solid #e5e5e5;
            background: white;
        }
        
        .contract-card:last-child {
            border-bottom: none;
        }
        
        .contract-card.renewing {
            background: #f0fdf4;
            border-left: 6px solid #0A7A0A;  /* System green */
        }
        
        .contract-card.not-renewing {
            background: #fef2f2;
            border-left: 6px solid #CC0000;  /* System red */
        }
        
        .contract-card.pending {
            background: #F5F5F5;  /* Changed to gray - 3-color system */
            border-left: 6px solid #333333;
        }
        
        .tenant-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            flex-wrap: wrap;
            gap: 12px;
        }
        
        .tenant-name {
            font-size: 1.3rem;
            font-weight: 700;
            color: #1a1a1a;
            text-align: center;  /* Center tenant name horizontally */
        }
        
        .tenant-unit {
            color: #7c3aed;
            font-weight: 700;
        }
        
        .contract-dates {
            font-size: 1rem;
            color: #4a4a4a;
            background: #f3f4f6;
            padding: 8px 16px;
            border-radius: 8px;
        }
        
        /* Renewal buttons */
        .renewal-buttons {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-bottom: 16px;
        }
        
        /* UNIFIED BUTTON STYLES (Contratos page) - matches Pagos for consistency */
        .status-pill.renewal-btn {
            display: flex;
            flex: 1;
            padding: 14px 20px;
            border: 3px solid #d4d4d4;
            border-radius: 12px;
            background: white;
            cursor: pointer;
            font-size: 1.1rem;
            font-weight: 700;
            transition: all 0.2s;
            min-height: 56px;
            text-align: center;
            justify-content: center;
            align-items: center;
        }
        
        .status-pill.renewal-btn:hover {
            background: #f5f5f5;
        }
        
        .status-pill.renewal-btn.active-green {
            background: #dcfce7;
            border-color: #0A7A0A;
            color: #0A7A0A;
        }
        
        .status-pill.renewal-btn.active-red {
            background: #fee2e2;
            border-color: #CC0000;
            color: #CC0000;
        }
        
        .status-pill.renewal-btn.active-yellow {
            background: #F5F5F5;
            border-color: #333333;
            color: #333333;
        }
        
        /* Contract tracking */
        .contract-tracking {
            display: flex;
            flex-direction: column;
            gap: 12px;
            margin: 16px 0;
            padding: 16px;
            background: #f9fafb;
            border-radius: 12px;
        }
        
        .tracking-checkbox {
            display: flex;
            align-items: center;
            gap: 12px;
            cursor: pointer;
            font-size: 1.1rem;
        }
        
        .tracking-checkbox input[type="checkbox"] {
            width: 24px;
            height: 24px;
            cursor: pointer;
        }
        
        /* Replacement section */
        .replacement-section {
            margin-top: 16px;
            padding: 16px;
            background: #fef2f2;
            border-radius: 12px;
            border: 2px solid #fca5a5;
        }
        
        .replacement-title {
            font-weight: 700;
            font-size: 1.1rem;
            margin-bottom: 12px;
            color: #dc2626;
        }
        
        .replacement-input {
            width: 100%;
            padding: 14px 16px;
            border: 2px solid #d4d4d4;
            border-radius: 8px;
            font-size: 1.1rem;
            margin-top: 8px;
        }
        
        .replacement-input:focus {
            outline: none;
            border-color: #7c3aed;
        }
        
        /* Available apartments section - Need to show! */
        .available-section {
            background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
            border-radius: 16px;
            box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3);
            margin-bottom: 32px;
            overflow: hidden;
        }
        
        .available-header {
            color: white;
            padding: 20px 24px;
            font-weight: 800;
            font-size: 1.3rem;
        }
        
        .available-list {
            background: white;
        }
        
        .available-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 24px;
            border-bottom: 2px solid #fee2e2;
            gap: 16px;
            flex-wrap: wrap;
        }
        
        .available-item:last-child {
            border-bottom: none;
        }
        
        .available-info {
            flex: 1;
        }
        
        .available-property {
            font-size: 1.2rem;
            color: #1a1a1a;
            margin-bottom: 6px;
        }
        
        .available-tenant {
            font-size: 1rem;
            color: #4a4a4a;
            margin-bottom: 4px;
        }
        
        .available-date {
            font-size: 1.1rem;
            font-weight: 700;
            color: #dc2626;
        }
        
        .available-actions {
            flex-shrink: 0;
        }
        
        .call-btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 12px 20px;
            background: #2563eb;
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 1rem;
            font-weight: 700;
            text-decoration: none;
            min-height: 48px;
        }
        
        .call-btn:hover {
            background: #1d4ed8;
        }
        
        .available-footer {
            background: #fef2f2;
            color: #991b1b;
            padding: 16px 24px;
            font-size: 1rem;
            font-weight: 600;
            text-align: center;
        }
        
        /* Replacement badge in bird's eye view */
        .replacement-badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 16px;
            font-size: 0.9rem;
            font-weight: 700;
            margin-left: 8px;
            background: #dbeafe;
            color: #1d4ed8;
        }
        
        .replacement-badge.needs-candidate {
            background: #fef3c7;
            color: #92400e;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }
        
        /* Expandable upcoming items - inline editing from bird's eye view */
        .upcoming-item {
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .upcoming-item:hover {
            background: rgba(0,0,0,0.02);
        }
        
        .upcoming-item-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 16px;
            flex-wrap: wrap;
        }
        
        .upcoming-expand-form {
            display: none;
            padding: 16px 0 8px 0;
            border-top: 2px dashed #e5e5e5;
            margin-top: 16px;
        }
        
        .upcoming-item.expanded .upcoming-expand-form {
            display: block;
        }
        
        .upcoming-item.expanded {
            background: #fefefe;
            box-shadow: inset 0 0 0 3px #7c3aed;
        }
        
        .expand-icon {
            font-size: 1.2rem;
            transition: transform 0.2s;
            color: #7c3aed;
            font-weight: bold;
        }
        
        .upcoming-item.expanded .expand-icon {
            transform: rotate(180deg);
        }
        
        /* Tenant ID badge - prominent for disambiguation */
        .tenant-id-badge {
            display: inline-block;
            background: #7c3aed;
            color: white;
            padding: 4px 10px;
            border-radius: 8px;
            font-size: 0.9rem;
            font-weight: 800;
            font-family: monospace;
            margin-right: 8px;
        }
        
        /* Inline form styling for bird's eye view */
        .inline-renewal-buttons {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 12px;
        }
        
        .inline-renewal-btn {
            flex: 1;
            min-width: 100px;
            padding: 10px 16px;
            border: 2px solid #d4d4d4;
            border-radius: 8px;
            background: white;
            cursor: pointer;
            font-size: 0.95rem;
            font-weight: 600;
            transition: all 0.2s;
            text-align: center;
        }
        
        .inline-renewal-btn:hover {
            background: #f5f5f5;
        }
        
        .inline-renewal-btn.active-green {
            background: #dcfce7;
            border-color: #0A7A0A;
            color: #0A7A0A;
        }
        
        .inline-renewal-btn.active-red {
            background: #fee2e2;
            border-color: #CC0000;
            color: #CC0000;
        }
        
        .inline-renewal-btn.active-yellow {
            background: #F5F5F5;
            border-color: #333333;
            color: #333333;
        }
        
        .inline-replacement-section {
            padding: 12px;
            background: #fef2f2;
            border-radius: 8px;
            border: 2px solid #fca5a5;
            margin-top: 12px;
        }
        
        .inline-replacement-section.hidden {
            display: none;
        }
        
        .inline-replacement-title {
            font-weight: 700;
            font-size: 1rem;
            margin-bottom: 10px;
            color: #dc2626;
        }
        
        .inline-form-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        
        @media (max-width: 600px) {
            .inline-form-grid {
                grid-template-columns: 1fr;
            }
        }
        
        .inline-form-input {
            width: 100%;
            padding: 10px 12px;
            border: 2px solid #d4d4d4;
            border-radius: 6px;
            font-size: 0.95rem;
        }
        
        .inline-form-input:focus {
            outline: none;
            border-color: #7c3aed;
        }
        
        .inline-form-label {
            font-size: 0.85rem;
            font-weight: 600;
            color: #666;
            margin-bottom: 4px;
            display: block;
        }
        
        .inline-form-group {
            margin-bottom: 8px;
        }
        
        .inline-form-group.full-width {
            grid-column: 1 / -1;
        }
        
        /* Toast notification */
        .toast {
            position: fixed;
            bottom: 24px;
            left: 50%;
            transform: translateX(-50%);
            background: #1a1a1a;
            color: white;
            padding: 16px 24px;
            border-radius: 12px;
            font-size: 1.1rem;
            font-weight: 600;
            display: none;
            z-index: 1000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        
        .toast.show {
            display: block;
            animation: fadeIn 0.3s ease;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateX(-50%) translateY(20px); }
            to { opacity: 1; transform: translateX(-50%) translateY(0); }
        }
        
        /* Mobile styles */
        @media (max-width: 600px) {
            body {
                padding: 12px;
                font-size: 20px;
            }
            
            .tenant-header {
                flex-direction: column;
                align-items: flex-start;
            }
            
            .renewal-buttons {
                flex-direction: column;
            }
            
            .renewal-btn {
                width: 100%;
                text-align: center;
            }
            
            .summary {
                grid-template-columns: repeat(2, 1fr);
            }
            
            .summary-value {
                font-size: 2rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>RentasClaras</h1>
            
            <!-- NAVBAR - Pagos y Contratos -->
            <nav class="top-navbar">
                <a href="/" class="top-navbar-item">
                    <span>Pagos</span>
                </a>
                <a href="/contratos" class="top-navbar-item active">
                    <span>Contratos</span>
                </a>
            </nav>
            
            <p class="subtitle">¿Quién renovará su contrato?</p>
        </header>
        
        <div class="summary">
            <div class="summary-card">
                <div class="summary-value green" id="renewingCount">{{ renewing_count }}</div>
                <div class="summary-label">Renovarán (próx. 30 días)</div>
            </div>
            <div class="summary-card">
                <div class="summary-value red" id="notRenewingCount">{{ not_renewing_count }}</div>
                <div class="summary-label">No renovarán (próx. 30 días)</div>
            </div>
            <div class="summary-card">
                <div class="summary-value yellow" id="pendingCount">{{ pending_count }}</div>
                <div class="summary-label">Pendientes (próx. 30 días)</div>
            </div>
        </div>
        
        <!-- Search Bar for Contratos - Prominent style matching Pagos -->
        <div class="prominent-search-section" id="stickyContractSearch">
            <!-- Label above search -->
            <div class="prominent-search-label">
                ¿Cuál contrato buscas? Escribe su nombre:
            </div>
            <div class="search-wrapper">
                <input type="text" 
                       id="contractSearch" 
                       class="search-input-styled prominent-search-input"
                       placeholder="Ej: Claudia, Juan, María..." 
                       oninput="filterContracts(this.value)">
                <button type="button" 
                        id="clearContractSearch" 
                        class="search-clear-btn prominent-search-clear"
                        onclick="clearContractSearch()">
                    ✕
                </button>
            </div>
            <div id="contractSearchResults" class="prominent-search-results"></div>
        </div>
        
        <!-- Property Filter Tabs for Contratos with scroll indicator -->
        <div style="position: relative; margin-bottom: 24px;">
            <div class="property-filter-tabs" id="propertyFilterTabsContratos" style="display: flex; gap: 8px; overflow-x: auto; padding: 4px; -webkit-overflow-scrolling: touch; position: relative; z-index: 10; background: #F5F5F5; border-radius: 12px; scroll-behavior: smooth;">
                <button type="button" class="property-filter-tab active" data-filter="all" onclick="filterContractsByProperty('all', this)" style="flex-shrink: 0; padding: 12px 20px; border-radius: 8px; border: none; background: #0A7A0A; color: white; font-size: 0.9rem; font-weight: 700; cursor: pointer; transition: all 0.2s; min-height: 48px; white-space: nowrap; position: relative; z-index: 11;">
                    Todas <span class="tab-count" id="tabCountAllContratos" style="background: rgba(255,255,255,0.3); padding: 2px 10px; border-radius: 12px; margin-left: 6px;">{{ total_tenants }}</span>
                </button>
                {% for property_name, tenants in tenants_by_property.items() %}
                <button type="button" class="property-filter-tab" data-filter="{{ property_name }}" onclick="filterContractsByProperty('{{ property_name }}', this)" style="flex-shrink: 0; padding: 12px 20px; border-radius: 8px; border: none; background: transparent; color: #333333; font-size: 0.9rem; font-weight: 700; cursor: pointer; transition: all 0.2s; min-height: 48px; white-space: nowrap; position: relative; z-index: 11;">
                    {{ property_name }} <span class="tab-count" data-tab-count="{{ property_name }}" style="background: rgba(0,0,0,0.1); padding: 2px 10px; border-radius: 12px; margin-left: 6px;">{{ tenants|length }}</span>
                </button>
                {% endfor %}
            </div>
            <!-- Scroll indicator arrow (visible when content overflows) -->
            <div id="scrollIndicatorRightContratos" class="scroll-indicator-arrow" style="position: absolute; right: 0; top: 0; bottom: 0; width: 48px; background: linear-gradient(90deg, transparent, rgba(245,245,245,0.95)); display: flex; align-items: center; justify-content: center; pointer-events: none; border-radius: 0 12px 12px 0;">
                <span style="font-size: 1.5rem; color: #666; animation: pulseArrow 1.5s infinite;">›</span>
            </div>
            <!-- First-time "Desliza" tooltip -->
            <div id="deslizaTooltipContratos" class="desliza-tooltip" style="display: none; position: absolute; right: 8px; top: -32px; background: #333; color: white; padding: 6px 12px; border-radius: 8px; font-size: 0.8rem; font-weight: 600; white-space: nowrap; box-shadow: 0 2px 8px rgba(0,0,0,0.2); z-index: 1000;">
                Desliza para ver mas
                <div style="position: absolute; bottom: -6px; right: 16px; width: 0; height: 0; border-left: 6px solid transparent; border-right: 6px solid transparent; border-top: 6px solid #333;"></div>
            </div>
            <script>
                // Hide scroll indicator if tabs don't overflow + show desliza tooltip
                (function() {
                    var tabs = document.getElementById('propertyFilterTabsContratos');
                    var indicator = document.getElementById('scrollIndicatorRightContratos');
                    var tooltip = document.getElementById('deslizaTooltipContratos');
                    var tooltipKey = 'rentasclaras_desliza_shown_contratos';
                    
                    if (tabs && indicator) {
                        function checkScroll() {
                            var isOverflowing = tabs.scrollWidth > tabs.clientWidth;
                            var isScrolledToEnd = tabs.scrollLeft + tabs.clientWidth >= tabs.scrollWidth - 10;
                            indicator.style.display = (isOverflowing && !isScrolledToEnd) ? 'flex' : 'none';
                            
                            // Show tooltip only once if overflowing and not seen before
                            if (isOverflowing && tooltip && !localStorage.getItem(tooltipKey)) {
                                tooltip.style.display = 'block';
                                setTimeout(function() {
                                    tooltip.style.display = 'none';
                                    localStorage.setItem(tooltipKey, 'true');
                                }, 4000);
                            }
                            
                            // Hide tooltip once user scrolls
                            if (tabs.scrollLeft > 20 && tooltip) {
                                tooltip.style.display = 'none';
                                localStorage.setItem(tooltipKey, 'true');
                            }
                        }
                        checkScroll();
                        tabs.addEventListener('scroll', checkScroll);
                        window.addEventListener('resize', checkScroll);
                    }
                })();
            </script>
        </div>
        
        <!-- APARTMENTS AVAILABLE - Need to show to new tenants -->
        {% if available_apartments %}
        <div class="available-section" style="background: #CC0000; border-radius: 16px; box-shadow: 0 4px 12px rgba(204, 0, 0, 0.3); margin-bottom: 32px; overflow: hidden;">
            <div class="available-header" style="background: #CC0000; color: white; padding: 20px 24px; font-weight: 700; font-size: 1.2rem;">
                Departamentos Disponibles
            </div>
            <div class="available-list">
                {% for apt in available_apartments %}
                <div class="available-item">
                    <div class="available-info">
                        <div class="available-property">
                            <strong>{{ apt.property_name }}</strong> — Unidad {{ apt.unit }}
                        </div>
                        <div class="available-tenant">
                            Sale: {{ apt.name }}
                        </div>
                        <div class="available-date">
                            Disponible: {{ apt.contract_end_formatted }}
                        </div>
                    </div>
                    <div class="available-actions">
                        <a href="tel:{{ apt.phone }}" class="call-btn" style="background: #0A7A0A;">Llamar</a>
                    </div>
                </div>
                {% endfor %}
            </div>
            <div class="available-footer" style="background: #FEE2E2; color: #991b1b; padding: 16px 24px; font-size: 1rem; font-weight: 600; text-align: center;">
                Estos departamentos no tienen candidato aún.
            </div>
        </div>
        {% endif %}
        
        <!-- Bird's Eye View: Upcoming Renewals Grouped by Month - NOW EXPANDABLE -->
        {% if upcoming_renewals_by_month %}
        <div class="upcoming-section" style="background: white; border-radius: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 24px; overflow: hidden;">
            <div class="upcoming-header" style="background: #CC0000; color: white; padding: 16px; font-weight: 700; font-size: 1rem;">
                ⚠️ {{ action_needed_count }} contrato{{ 's' if action_needed_count != 1 else '' }} necesita{{ 'n' if action_needed_count != 1 else '' }} atención <span style="font-weight: 400; opacity: 0.9; font-size: 0.85rem;">(pendientes o sin candidato)</span>
            </div>
            <div class="upcoming-list">
                {% for month_group in upcoming_renewals_by_month %}
                <div class="month-section">
                    <div class="month-header" style="background: #f3f4f6; padding: 14px 24px; font-size: 1.1rem; font-weight: 700; color: #1a1a1a; border-bottom: 2px solid #e5e5e5;">{{ month_group.month }}</div>
                    {% for tenant in month_group.tenants %}
                    <div class="upcoming-item {{ 'renewing' if tenant.renewal_status == 'renovará' else 'not-renewing' if tenant.renewal_status == 'no_renovará' else 'pending' }} {{ 'expiring-soon' if tenant.days_until_expiry is defined and tenant.days_until_expiry <= 30 else '' }}"
                         id="upcoming-{{ tenant.id }}"
                         data-tenant-id="{{ tenant.id }}"
                         onclick="toggleUpcomingExpand(this, event)">
                        
                        <!-- Clickable header row -->
                        <div class="upcoming-item-header">
                            <div class="upcoming-info">
                                <span class="tenant-id-badge">{{ tenant.id }}</span>
                                <span class="upcoming-name">
                                    <strong>{{ tenant.property_name }}</strong> ({{ tenant.unit }}) — {{ tenant.name }}
                                </span>
                                <span class="upcoming-date">{{ tenant.contract_end_formatted }}</span>
                                {% if tenant.days_until_expiry is defined and tenant.days_until_expiry <= 30 %}
                                <span class="expiring-soon-badge" style="background: #CC0000; color: white; padding: 4px 10px; border-radius: 12px; font-size: 0.85rem; font-weight: 700; margin-left: 8px;">{{ tenant.days_until_expiry }} días</span>
                                {% endif %}
                            </div>
                            <div class="upcoming-status" style="display: flex; align-items: center; gap: 8px;">
                                {% if tenant.renewal_status == 'renovará' %}
                                <span class="status-badge green">Renovará</span>
                                {% elif tenant.renewal_status == 'no_renovará' %}
                                <span class="status-badge red">No renovará</span>
                                {% if tenant.replacement_name %}
                                <span class="replacement-badge">{{ tenant.replacement_name }}</span>
                                {% else %}
                                <span class="replacement-badge needs-candidate" style="background: #FEE2E2; color: #CC0000;">Sin candidato</span>
                                {% endif %}
                                {% else %}
                                <span class="status-badge yellow" style="background: #F5F5F5; color: #333333;">Pendiente</span>
                                {% endif %}
                                <span class="expand-icon">▼</span>
                            </div>
                        </div>
                        
                        <!-- Expandable inline edit form -->
                        <div class="upcoming-expand-form" onclick="event.stopPropagation()">
                            <div style="margin-bottom: 12px; padding: 8px 12px; background: #7c3aed; color: white; border-radius: 8px; font-weight: 700;">
                                ✏️ Editando: <span class="tenant-id-badge" style="background: white; color: #7c3aed;">{{ tenant.id }}</span> {{ tenant.name }} — {{ tenant.property_name }} ({{ tenant.unit }})
                            </div>
                            
                            <!-- Renewal status buttons -->
                            <div class="inline-renewal-buttons">
                                <button type="button" 
                                        class="inline-renewal-btn {% if tenant.renewal_status == 'renovará' %}active-green{% endif %}" 
                                        onclick="setInlineRenewalStatus('{{ tenant.id }}', 'renovará', this)">
                                    ✓ Sí Renovará
                                </button>
                                <button type="button" 
                                        class="inline-renewal-btn {% if tenant.renewal_status == 'no_renovará' %}active-red{% endif %}" 
                                        onclick="setInlineRenewalStatus('{{ tenant.id }}', 'no_renovará', this)">
                                    ✗ No Renovará
                                </button>
                                <button type="button" 
                                        class="inline-renewal-btn {% if tenant.renewal_status == 'pendiente' %}active-yellow{% endif %}" 
                                        onclick="setInlineRenewalStatus('{{ tenant.id }}', 'pendiente', this)">
                                    ? Pendiente
                                </button>
                            </div>
                            
                            <!-- Replacement section - shown when "No Renovará" -->
                            <div class="inline-replacement-section {% if tenant.renewal_status != 'no_renovará' %}hidden{% endif %}" 
                                 id="inline-replacement-{{ tenant.id }}">
                                <div class="inline-replacement-title">🔄 Datos del Nuevo Inquilino</div>
                                
                                <div class="inline-form-grid">
                                    <div class="inline-form-group">
                                        <label class="inline-form-label">Nombre</label>
                                        <input type="text" class="inline-form-input" 
                                               placeholder="Nombre del nuevo inquilino"
                                               value="{{ tenant.replacement_name or '' }}"
                                               onchange="updateInlineReplacement('{{ tenant.id }}', 'replacement_name', this.value)">
                                    </div>
                                    <div class="inline-form-group">
                                        <label class="inline-form-label">Teléfono</label>
                                        <input type="tel" class="inline-form-input" 
                                               placeholder="Teléfono"
                                               value="{{ tenant.replacement_phone or '' }}"
                                               onchange="updateInlineReplacement('{{ tenant.id }}', 'replacement_phone', this.value)">
                                    </div>
                                    <div class="inline-form-group">
                                        <label class="inline-form-label">Inicio Contrato</label>
                                        <input type="date" class="inline-form-input" 
                                               value="{{ tenant.replacement_contract_start or '' }}"
                                               onchange="updateInlineReplacement('{{ tenant.id }}', 'replacement_contract_start', this.value)">
                                    </div>
                                    <div class="inline-form-group">
                                        <label class="inline-form-label">Fin Contrato</label>
                                        <input type="date" class="inline-form-input" 
                                               value="{{ tenant.replacement_contract_end or '' }}"
                                               onchange="updateInlineReplacement('{{ tenant.id }}', 'replacement_contract_end', this.value)">
                                    </div>
                                    <div class="inline-form-group">
                                        <label class="inline-form-label">Nombre del Aval</label>
                                        <input type="text" class="inline-form-input" 
                                               placeholder="Nombre del aval/fiador"
                                               value="{{ tenant.replacement_aval_name or '' }}"
                                               onchange="updateInlineReplacement('{{ tenant.id }}', 'replacement_aval_name', this.value)">
                                    </div>
                                    <div class="inline-form-group">
                                        <label class="inline-form-label">Teléfono del Aval</label>
                                        <input type="tel" class="inline-form-input" 
                                               placeholder="Teléfono del aval"
                                               value="{{ tenant.replacement_aval_phone or '' }}"
                                               onchange="updateInlineReplacement('{{ tenant.id }}', 'replacement_aval_phone', this.value)">
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}
        
        {% for property_name, tenants in tenants_by_property.items() %}
        <div class="property-section">
            <div class="property-header">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                    <span>🏢 {{ property_name }} ({{ tenants|length }} unidades)</span>
                    {% if property_stats[property_name].expiring_soon > 0 %}
                    <span style="font-size: 0.85rem; font-weight: 600; opacity: 0.95;">
                        Próx. 30 días: 
                        <span style="color: #86efac;">✓{{ property_stats[property_name].renewing }}</span> |
                        <span style="color: #fca5a5;">✗{{ property_stats[property_name].not_renewing }}</span> |
                        <span style="color: #fde047;">?{{ property_stats[property_name].pending }}</span>
                    </span>
                    {% endif %}
                </div>
            </div>
            
            {% for tenant in tenants %}
            <div class="contract-card {{ 'renewing' if tenant.renewal_status == 'renovará' else 'not-renewing' if tenant.renewal_status == 'no_renovará' else 'pending' }}" 
                 data-tenant-id="{{ tenant.id }}">
                
                <div class="tenant-header">
                    <div class="tenant-name">
                        <span class="tenant-id-badge">{{ tenant.id }}</span>
                        <span class="tenant-unit">({{ tenant.unit }})</span> {{ tenant.name }}
                    </div>
                    {% if tenant.contract_start_formatted and tenant.contract_end_formatted %}
                    <div class="contract-dates">
                        📄 {{ tenant.contract_start_formatted }} → {{ tenant.contract_end_formatted }}
                    </div>
                    {% endif %}
                </div>
                
                <div class="renewal-buttons">
                    <button type="button" class="status-pill renewal-btn {% if tenant.renewal_status == 'renovará' %}active-green{% endif %}" 
                            onclick="setRenewalStatus(this, '{{ tenant.id }}', 'renovará')">
                        Sí Renovará
                    </button>
                    <button type="button" class="status-pill renewal-btn {% if tenant.renewal_status == 'no_renovará' %}active-red{% endif %}" 
                            onclick="setRenewalStatus(this, '{{ tenant.id }}', 'no_renovará')">
                        No Renovará
                    </button>
                    <button type="button" class="status-pill renewal-btn {% if tenant.renewal_status == 'pendiente' %}active-yellow{% endif %}" 
                            onclick="setRenewalStatus(this, '{{ tenant.id }}', 'pendiente')">
                        Pendiente
                    </button>
                </div>
                
                <div class="contract-tracking">
                    <label class="tracking-checkbox">
                        <input type="checkbox" {% if tenant.contract_delivered %}checked{% endif %} 
                               onchange="updateContractDelivery(this, '{{ tenant.id }}', 'delivered')">
                        <span>📨 Contrato nuevo entregado</span>
                    </label>
                    <label class="tracking-checkbox">
                        <input type="checkbox" {% if tenant.contract_picked_up %}checked{% endif %} 
                               onchange="updateContractDelivery(this, '{{ tenant.id }}', 'picked_up')">
                        <span>✍️ Contrato firmado/recogido</span>
                    </label>
                </div>
                
                <div class="replacement-section" id="replacement-{{ tenant.id }}" 
                     style="{% if tenant.renewal_status != 'no_renovará' %}display:none;{% endif %}">
                    <div class="replacement-title">🔄 Datos del Nuevo Inquilino</div>
                    
                    <div class="inline-form-grid" style="margin-bottom: 12px;">
                        <div class="inline-form-group">
                            <label class="inline-form-label">Nombre</label>
                            <input type="text" class="replacement-input" 
                                   placeholder="Nombre del nuevo inquilino" 
                                   value="{{ tenant.replacement_name or '' }}"
                                   onchange="updateReplacementField(this, '{{ tenant.id }}', 'replacement_name')">
                        </div>
                        <div class="inline-form-group">
                            <label class="inline-form-label">Teléfono</label>
                            <input type="tel" class="replacement-input" 
                                   placeholder="Teléfono" 
                                   value="{{ tenant.replacement_phone or '' }}"
                                   onchange="updateReplacementField(this, '{{ tenant.id }}', 'replacement_phone')">
                        </div>
                        <div class="inline-form-group">
                            <label class="inline-form-label">Inicio Contrato</label>
                            <input type="date" class="replacement-input" 
                                   value="{{ tenant.replacement_contract_start or '' }}"
                                   onchange="updateReplacementField(this, '{{ tenant.id }}', 'replacement_contract_start')">
                        </div>
                        <div class="inline-form-group">
                            <label class="inline-form-label">Fin Contrato</label>
                            <input type="date" class="replacement-input" 
                                   value="{{ tenant.replacement_contract_end or '' }}"
                                   onchange="updateReplacementField(this, '{{ tenant.id }}', 'replacement_contract_end')">
                        </div>
                        <div class="inline-form-group">
                            <label class="inline-form-label">Nombre del Aval</label>
                            <input type="text" class="replacement-input" 
                                   placeholder="Nombre del aval/fiador" 
                                   value="{{ tenant.replacement_aval_name or '' }}"
                                   onchange="updateReplacementField(this, '{{ tenant.id }}', 'replacement_aval_name')">
                        </div>
                        <div class="inline-form-group">
                            <label class="inline-form-label">Teléfono del Aval</label>
                            <input type="tel" class="replacement-input" 
                                   placeholder="Teléfono del aval" 
                                   value="{{ tenant.replacement_aval_phone or '' }}"
                                   onchange="updateReplacementField(this, '{{ tenant.id }}', 'replacement_aval_phone')">
                        </div>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
        {% endfor %}
    </div>
    
    <!-- MOBILE BOTTOM NAVIGATION -->
    <nav class="bottom-nav">
        <a href="/" class="bottom-nav-item">
            <span class="bottom-nav-icon" style="font-size: 1.3rem; font-weight: 700;">$</span>
            <span>Pagos</span>
        </a>
        <a href="/contratos" class="bottom-nav-item active">
            <svg class="bottom-nav-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
            <span>Contratos</span>
        </a>
    </nav>
    
    <div class="toast" id="toast">Guardado</div>
    
    
    <script>
        function showToast(message) {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.classList.add('show');
            setTimeout(() => {
                toast.classList.remove('show');
            }, 2000);
        }
        
        function updateCounts() {
            let renewing = 0;
            let notRenewing = 0;
            let pending = 0;
            
            document.querySelectorAll('.contract-card').forEach(card => {
                if (card.classList.contains('renewing')) renewing++;
                else if (card.classList.contains('not-renewing')) notRenewing++;
                else pending++;
            });
            
            document.getElementById('renewingCount').textContent = renewing;
            document.getElementById('notRenewingCount').textContent = notRenewing;
            document.getElementById('pendingCount').textContent = pending;
        }
        
        function setRenewalStatus(btn, tenantId, status) {
            const card = btn.closest('.contract-card');
            const container = btn.closest('.renewal-buttons');
            
            // Update button states
            container.querySelectorAll('.renewal-btn').forEach(b => {
                b.classList.remove('active-green', 'active-red', 'active-yellow');
            });
            
            // Set active state and card style
            card.classList.remove('renewing', 'not-renewing', 'pending');
            
            if (status === 'renovará') {
                btn.classList.add('active-green');
                card.classList.add('renewing');
            } else if (status === 'no_renovará') {
                btn.classList.add('active-red');
                card.classList.add('not-renewing');
            } else {
                btn.classList.add('active-yellow');
                card.classList.add('pending');
            }
            
            // Show/hide replacement section
            const replacementSection = document.getElementById(`replacement-${tenantId}`);
            if (replacementSection) {
                replacementSection.style.display = status === 'no_renovará' ? 'block' : 'none';
            }
            
            // Save to database
            fetch('/api/renewal', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tenant_id: tenantId,
                    renewal_status: status
                })
            }).then(response => {
                if (response.ok) {
                    showToast('Guardado');
                    updateCounts();
                }
            });
        }
        
        function updateContractDelivery(checkbox, tenantId, type) {
            const isChecked = checkbox.checked;
            const data = { tenant_id: tenantId };
            
            if (type === 'delivered') {
                data.contract_delivered = isChecked;
            } else if (type === 'picked_up') {
                data.contract_picked_up = isChecked;
            }
            
            fetch('/api/renewal', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            }).then(response => {
                if (response.ok) {
                    showToast(isChecked ? 'Marcado' : 'Desmarcado');
                }
            });
        }
        
        function updateReplacement(input, tenantId, field) {
            const value = input.value;
            const data = { tenant_id: tenantId };
            
            if (field === 'name') {
                data.replacement_name = value;
            } else if (field === 'phone') {
                data.replacement_phone = value;
            }
            
            fetch('/api/renewal', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            }).then(response => {
                if (response.ok) {
                    showToast('Guardado');
                }
            });
        }
        
        // Generic field update function for replacement fields
        function updateReplacementField(input, tenantId, field) {
            const value = input.value;
            const data = { tenant_id: tenantId };
            data[field] = value;
            
            fetch('/api/renewal', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            }).then(response => {
                if (response.ok) {
                    showToast('Guardado');
                }
            });
        }
        
        // =============================================
        // INLINE EDITING from Bird's Eye View
        // =============================================
        
        function toggleUpcomingExpand(item, event) {
            // Don't toggle if clicking on form elements inside
            if (event.target.closest('.upcoming-expand-form')) {
                return;
            }
            
            // Close other expanded items
            document.querySelectorAll('.upcoming-item.expanded').forEach(other => {
                if (other !== item) {
                    other.classList.remove('expanded');
                }
            });
            
            // Toggle this item
            item.classList.toggle('expanded');
        }
        
        function setInlineRenewalStatus(tenantId, status, btn) {
            const item = btn.closest('.upcoming-item');
            const container = btn.closest('.inline-renewal-buttons');
            
            // Update button states in the inline form
            container.querySelectorAll('.inline-renewal-btn').forEach(b => {
                b.classList.remove('active-green', 'active-red', 'active-yellow');
            });
            
            // Set active state
            if (status === 'renovará') {
                btn.classList.add('active-green');
            } else if (status === 'no_renovará') {
                btn.classList.add('active-red');
            } else {
                btn.classList.add('active-yellow');
            }
            
            // Update the item's visual state
            item.classList.remove('renewing', 'not-renewing', 'pending');
            if (status === 'renovará') {
                item.classList.add('renewing');
            } else if (status === 'no_renovará') {
                item.classList.add('not-renewing');
            } else {
                item.classList.add('pending');
            }
            
            // Show/hide inline replacement section
            const inlineReplacementSection = document.getElementById(`inline-replacement-${tenantId}`);
            if (inlineReplacementSection) {
                if (status === 'no_renovará') {
                    inlineReplacementSection.classList.remove('hidden');
                } else {
                    inlineReplacementSection.classList.add('hidden');
                }
            }
            
            // Update the status badge in the header
            const statusContainer = item.querySelector('.upcoming-status');
            const statusBadge = statusContainer.querySelector('.status-badge');
            if (statusBadge) {
                statusBadge.className = 'status-badge';
                if (status === 'renovará') {
                    statusBadge.classList.add('green');
                    statusBadge.textContent = 'Renovará';
                } else if (status === 'no_renovará') {
                    statusBadge.classList.add('red');
                    statusBadge.textContent = 'No renovará';
                } else {
                    statusBadge.classList.add('yellow');
                    statusBadge.style.background = '#F5F5F5';
                    statusBadge.style.color = '#333333';
                    statusBadge.textContent = 'Pendiente';
                }
            }
            
            // Also update the corresponding contract card below (if visible)
            const contractCard = document.querySelector(`.contract-card[data-tenant-id="${tenantId}"]`);
            if (contractCard) {
                contractCard.classList.remove('renewing', 'not-renewing', 'pending');
                if (status === 'renovará') {
                    contractCard.classList.add('renewing');
                } else if (status === 'no_renovará') {
                    contractCard.classList.add('not-renewing');
                } else {
                    contractCard.classList.add('pending');
                }
                
                // Update buttons in the card
                const cardButtons = contractCard.querySelectorAll('.renewal-btn');
                cardButtons.forEach(b => {
                    b.classList.remove('active-green', 'active-red', 'active-yellow');
                    if (b.textContent.includes('Sí') && status === 'renovará') {
                        b.classList.add('active-green');
                    } else if (b.textContent.includes('No') && status === 'no_renovará') {
                        b.classList.add('active-red');
                    } else if (b.textContent.includes('Pendiente') && status === 'pendiente') {
                        b.classList.add('active-yellow');
                    }
                });
                
                // Show/hide replacement section in card
                const cardReplacementSection = document.getElementById(`replacement-${tenantId}`);
                if (cardReplacementSection) {
                    cardReplacementSection.style.display = status === 'no_renovará' ? 'block' : 'none';
                }
            }
            
            // Save to database
            fetch('/api/renewal', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tenant_id: tenantId,
                    renewal_status: status
                })
            }).then(response => {
                if (response.ok) {
                    showToast('Guardado');
                    updateCounts();
                }
            });
        }
        
        function updateInlineReplacement(tenantId, field, value) {
            const data = { tenant_id: tenantId };
            data[field] = value;
            
            // Also update the corresponding input in the contract card below
            const contractCard = document.querySelector(`.contract-card[data-tenant-id="${tenantId}"]`);
            if (contractCard) {
                const correspondingInput = contractCard.querySelector(`input[onchange*="${field}"]`);
                if (correspondingInput) {
                    correspondingInput.value = value;
                }
            }
            
            // Update replacement badge if it's the name field
            if (field === 'replacement_name') {
                const upcomingItem = document.getElementById(`upcoming-${tenantId}`);
                if (upcomingItem) {
                    const replacementBadge = upcomingItem.querySelector('.replacement-badge');
                    if (replacementBadge && value) {
                        replacementBadge.textContent = value;
                        replacementBadge.classList.remove('needs-candidate');
                        replacementBadge.style.background = '#dbeafe';
                        replacementBadge.style.color = '#1d4ed8';
                    } else if (replacementBadge && !value) {
                        replacementBadge.textContent = 'Sin candidato';
                        replacementBadge.classList.add('needs-candidate');
                        replacementBadge.style.background = '#FEE2E2';
                        replacementBadge.style.color = '#CC0000';
                    }
                }
            }
            
            fetch('/api/renewal', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            }).then(response => {
                if (response.ok) {
                    showToast('Guardado');
                }
            });
        }
        
        // =============================================
        // Search/Filter Contracts
        // =============================================
        
        function filterContracts(searchTerm) {
            const searchInput = document.getElementById('contractSearch');
            const clearBtn = document.getElementById('clearContractSearch');
            const resultsDiv = document.getElementById('contractSearchResults');
            const term = searchTerm.toLowerCase().trim();
            
            // Show/hide clear button using class toggle
            if (term) {
                clearBtn.classList.add('visible');
            } else {
                clearBtn.classList.remove('visible');
            }
            
            // Get all contract cards and property sections
            const allCards = document.querySelectorAll('.contract-card');
            const allPropertySections = document.querySelectorAll('.property-section');
            const allUpcomingItems = document.querySelectorAll('.upcoming-item');
            
            if (!term) {
                // Show all
                allCards.forEach(card => card.style.display = 'block');
                allPropertySections.forEach(section => section.style.display = 'block');
                allUpcomingItems.forEach(item => item.style.display = 'flex');
                resultsDiv.style.display = 'none';
                return;
            }
            
            let matchCount = 0;
            const propertyVisibility = {};
            
            // Filter contract cards
            allCards.forEach(card => {
                const nameEl = card.querySelector('.tenant-name');
                if (!nameEl) return;
                const name = nameEl.textContent.toLowerCase();
                const propertySection = card.closest('.property-section');
                const propertyHeader = propertySection ? propertySection.querySelector('.property-header') : null;
                const propertyName = propertyHeader ? propertyHeader.textContent.trim() : '';
                
                if (name.includes(term)) {
                    card.style.display = 'block';
                    matchCount++;
                    propertyVisibility[propertyName] = true;
                } else {
                    card.style.display = 'none';
                }
            });
            
            // Filter upcoming items
            allUpcomingItems.forEach(item => {
                const nameEl = item.querySelector('.upcoming-name');
                if (!nameEl) return;
                const name = nameEl.textContent.toLowerCase();
                
                if (name.includes(term)) {
                    item.style.display = 'flex';
                } else {
                    item.style.display = 'none';
                }
            });
            
            // Hide property sections with no visible cards
            allPropertySections.forEach(section => {
                const header = section.querySelector('.property-header');
                const propName = header ? header.textContent.trim() : '';
                section.style.display = propertyVisibility[propName] ? 'block' : 'none';
            });
            
            // Show results count
            resultsDiv.style.display = 'block';
            if (matchCount === 0) {
                resultsDiv.innerHTML = `No se encontró "<strong>${searchTerm}</strong>"`;
            } else if (matchCount === 1) {
                resultsDiv.innerHTML = `1 inquilino encontrado`;
            } else {
            resultsDiv.innerHTML = `${matchCount} inquilinos encontrados`;
            }
        }
        
        // =============================================
        // Property Filter Tabs for Contratos
        // =============================================
        
        let activeContractPropertyFilter = 'all';
        
        function filterContractsByProperty(propertyName, btn) {
            activeContractPropertyFilter = propertyName;
            
            // Update tab active states and styles (green active, consistent with Pagos)
            const allTabs = document.querySelectorAll('#propertyFilterTabsContratos .property-filter-tab');
            allTabs.forEach(tab => {
                tab.classList.remove('active');
                tab.style.background = 'transparent';
                tab.style.color = '#333333';
            });
            btn.classList.add('active');
            btn.style.background = '#0A7A0A';
            btn.style.color = 'white';
            
            // Clear any search filter first
            const searchInput = document.getElementById('contractSearch');
            if (searchInput && searchInput.value) {
                searchInput.value = '';
                document.getElementById('clearContractSearch').classList.remove('visible');
                document.getElementById('contractSearchResults').style.display = 'none';
            }
            
            // Filter contract cards
            const allCards = document.querySelectorAll('.contract-card');
            const allPropertySections = document.querySelectorAll('.property-section');
            const allUpcomingItems = document.querySelectorAll('.upcoming-item');
            const availableSection = document.querySelector('.available-section');
            const upcomingSection = document.querySelector('.upcoming-section');
            
            if (propertyName === 'all') {
                // Show all
                allCards.forEach(card => card.style.display = 'block');
                allPropertySections.forEach(section => section.style.display = 'block');
                allUpcomingItems.forEach(item => item.style.display = 'flex');
                if (availableSection) availableSection.style.display = 'block';
                if (upcomingSection) upcomingSection.style.display = 'block';
            } else {
                // Filter by property
                allCards.forEach(card => {
                    const propertySection = card.closest('.property-section');
                    const propertyHeader = propertySection ? propertySection.querySelector('.property-header') : null;
                    const propName = propertyHeader ? propertyHeader.textContent.trim() : '';
                    
                    if (propName.includes(propertyName)) {
                        card.style.display = 'block';
                    } else {
                        card.style.display = 'none';
                    }
                });
                
                allPropertySections.forEach(section => {
                    const header = section.querySelector('.property-header');
                    const propName = header ? header.textContent.trim() : '';
                    section.style.display = propName.includes(propertyName) ? 'block' : 'none';
                });
                
                // Filter upcoming items by property name in the text
                allUpcomingItems.forEach(item => {
                    const nameEl = item.querySelector('.upcoming-name');
                    if (!nameEl) return;
                    const name = nameEl.textContent;
                    item.style.display = name.includes(propertyName) ? 'flex' : 'none';
                });
                
                // Hide available apartments section when filtering
                if (availableSection) {
                    const hasMatchingApartments = Array.from(availableSection.querySelectorAll('.available-property')).some(el => 
                        el.textContent.includes(propertyName)
                    );
                    availableSection.style.display = hasMatchingApartments ? 'block' : 'none';
                }
            }
        }
        
        function clearContractSearch() {
            const searchInput = document.getElementById('contractSearch');
            searchInput.value = '';
            filterContracts('');
            searchInput.focus();
        }
    </script>
</body>
</html>
"""


@app.route("/contratos")
def contracts():
    """Separate page focused on contract renewal management"""
    from collections import defaultdict
    from datetime import datetime

    all_tenants = get_all_tenants()
    tenants_by_property = {}

    # Calculate today's date for comparisons
    today = datetime.now()
    
    # Count by renewal status (limited to next month for actionable items)
    renewing_count = 0
    not_renewing_count = 0  # Only contracts expiring within next month
    pending_count = 0  # Only contracts expiring within next month
    
    # Calculate the date range for "next month" (contracts expiring in next 30 days)
    from datetime import timedelta
    next_month_cutoff = today + timedelta(days=30)

    # Spanish month names
    spanish_months = [
        "Enero",
        "Febrero",
        "Marzo",
        "Abril",
        "Mayo",
        "Junio",
        "Julio",
        "Agosto",
        "Septiembre",
        "Octubre",
        "Noviembre",
        "Diciembre",
    ]

    # Spanish month names lowercase for date formatting
    spanish_months_lower = [
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    ]

    def parse_date(date_str):
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except:
            try:
                return datetime.strptime(date_str, "%d/%m/%Y")
            except:
                return None

    # Add days_until_expiry for urgency highlighting
    for tenant in all_tenants:
        if tenant.contract_end:
            parsed = parse_date(tenant.contract_end)
            if parsed:
                tenant.days_until_expiry = (parsed - today).days

    # Track upcoming renewals for bird's eye view, grouped by month
    upcoming_by_month = defaultdict(list)

    def format_date_spanish(date_str):
        """Format date as '12 de diciembre 2025'"""
        parsed = parse_date(date_str)
        if parsed:
            return f"{parsed.day} de {spanish_months_lower[parsed.month - 1]} {parsed.year}"
        return date_str  # Return original if can't parse

    for tenant in all_tenants:
        # Format contract dates for display
        if tenant.contract_start:
            tenant.contract_start_formatted = format_date_spanish(tenant.contract_start)
        else:
            tenant.contract_start_formatted = None
        if tenant.contract_end:
            tenant.contract_end_formatted = format_date_spanish(tenant.contract_end)
        else:
            tenant.contract_end_formatted = None

        if tenant.property_name not in tenants_by_property:
            tenants_by_property[tenant.property_name] = []
        tenants_by_property[tenant.property_name].append(tenant)

        # Count statuses only for contracts expiring within next 30 days
        contract_expires_soon = False
        if tenant.contract_end:
            parsed_end = parse_date(tenant.contract_end)
            if parsed_end and parsed_end <= next_month_cutoff:
                contract_expires_soon = True
        
        # Only count contracts expiring within next 30 days for ALL statuses
        if contract_expires_soon:
            if tenant.renewal_status == "renovará":
                renewing_count += 1
            elif tenant.renewal_status == "no_renovará":
                not_renewing_count += 1
            else:  # pendiente
                pending_count += 1

        # Add to upcoming renewals grouped by month
        if tenant.contract_end:
            parsed = parse_date(tenant.contract_end)
            if parsed:
                month_key = f"{spanish_months[parsed.month - 1]} {parsed.year}"
                upcoming_by_month[month_key].append(
                    {"tenant": tenant, "parsed_date": parsed}
                )

    # Sort tenants within each month by date
    for month_key in upcoming_by_month:
        upcoming_by_month[month_key].sort(key=lambda x: x["parsed_date"])

    # Sort months chronologically using Spanish month names
    def parse_spanish_month_year(month_str):
        """Parse 'Enero 2025' to datetime for sorting."""
        spanish_to_num = {
            "enero": 1,
            "febrero": 2,
            "marzo": 3,
            "abril": 4,
            "mayo": 5,
            "junio": 6,
            "julio": 7,
            "agosto": 8,
            "septiembre": 9,
            "octubre": 10,
            "noviembre": 11,
            "diciembre": 12,
        }
        try:
            parts = month_str.split()
            month_num = spanish_to_num.get(parts[0].lower(), 1)
            year = int(parts[1])
            return datetime(year, month_num, 1)
        except:
            return datetime.max

    sorted_months = sorted(upcoming_by_month.keys(), key=parse_spanish_month_year)

    # Build ordered dict of month -> tenants
    upcoming_renewals_by_month = []
    for month_key in sorted_months:
        upcoming_renewals_by_month.append(
            {
                "month": month_key,
                "tenants": [item["tenant"] for item in upcoming_by_month[month_key]],
            }
        )

    # Sort tenants within each property by contract end date too
    for prop_name in tenants_by_property:
        tenants_by_property[prop_name].sort(
            key=lambda t: (
                parse_date(t.contract_end)
                if t.contract_end and parse_date(t.contract_end)
                else datetime.max
            )
        )

    # Compute property-level stats for contracts expiring in next 30 days
    property_stats = {}
    for prop_name, tenants in tenants_by_property.items():
        prop_renewing = 0
        prop_not_renewing = 0
        prop_pending = 0
        prop_expiring_soon = 0
        
        for tenant in tenants:
            # Check if contract expires within 30 days
            expires_soon = False
            if tenant.contract_end:
                parsed_end = parse_date(tenant.contract_end)
                if parsed_end and parsed_end <= next_month_cutoff:
                    expires_soon = True
                    prop_expiring_soon += 1
            
            # Only count if expiring soon
            if expires_soon:
                if tenant.renewal_status == "renovará":
                    prop_renewing += 1
                elif tenant.renewal_status == "no_renovará":
                    prop_not_renewing += 1
                else:  # pendiente
                    prop_pending += 1
        
        property_stats[prop_name] = {
            'renewing': prop_renewing,
            'not_renewing': prop_not_renewing,
            'pending': prop_pending,
            'expiring_soon': prop_expiring_soon,
            'total': len(tenants)
        }

    # Build list of available apartments (no renovará + no replacement candidate)
    available_apartments = []
    for tenant in all_tenants:
        if tenant.renewal_status == "no_renovará" and not tenant.replacement_name:
            available_apartments.append(tenant)

    # Sort by contract end date (soonest first)
    available_apartments.sort(
        key=lambda t: (
            parse_date(t.contract_end)
            if t.contract_end and parse_date(t.contract_end)
            else datetime.max
        )
    )

    # Filter upcoming renewals to only show "action needed" items:
    # - no_renovará WITHOUT a candidate (needs attention)
    # - pendiente (needs decision)
    # Exclude renovará (already handled, no action needed)
    action_needed_renewals_by_month = []
    action_needed_count = 0
    for month_group in upcoming_renewals_by_month:
        filtered_tenants = []
        for tenant in month_group["tenants"]:
            needs_action = False
            if tenant.renewal_status == "pendiente":
                needs_action = True
            elif tenant.renewal_status == "no_renovará" and not tenant.replacement_name:
                needs_action = True
            
            if needs_action:
                filtered_tenants.append(tenant)
                action_needed_count += 1
        
        if filtered_tenants:
            action_needed_renewals_by_month.append({
                "month": month_group["month"],
                "tenants": filtered_tenants
            })

    return render_template_string(
        CONTRACTS_TEMPLATE,
        tenants_by_property=tenants_by_property,
        property_stats=property_stats,
        total_tenants=len(all_tenants),
        renewing_count=renewing_count,
        not_renewing_count=not_renewing_count,
        pending_count=pending_count,
        upcoming_renewals_by_month=action_needed_renewals_by_month,
        action_needed_count=action_needed_count,
        available_apartments=available_apartments,
    )


# =============================================================================
# ADMIN ROUTES (Manual Testing / Scheduler Trigger)
# =============================================================================


@app.route("/admin/test-scheduler/<secret_key>")
def admin_test_scheduler(secret_key):
    """
    Manually trigger the rent reminder scheduler for testing.
    
    Usage: https://your-app.fly.dev/admin/test-scheduler/your-secret-password
    
    This lets you test the scheduler without waiting for the actual day/time.
    Check fly logs to see the output.
    """
    # Use the RENTASCLARAS_PIN as the secret key for simplicity
    if secret_key != RENTASCLARAS_PIN:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        result = run_rent_automation("MANUAL TEST")
        return jsonify({
            "status": "triggered",
            "result": result,
            "message": "Check fly logs for details"
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/admin/test-single/<secret_key>/<tenant_id>")
def admin_test_single(secret_key, tenant_id):
    """
    Send a test reminder to a single tenant.
    
    Usage: https://your-app.fly.dev/admin/test-single/your-secret-password/MAT-A
    """
    if secret_key != RENTASCLARAS_PIN:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        from src.tasks import send_test_reminder
        result = send_test_reminder(tenant_id, force=True)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/admin/scheduler-status/<secret_key>")
def admin_scheduler_status(secret_key):
    """
    Check the status of scheduled jobs.
    
    Usage: https://your-app.fly.dev/admin/scheduler-status/your-secret-password
    """
    if secret_key != RENTASCLARAS_PIN:
        return jsonify({"error": "Unauthorized"}), 403
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": str(job.next_run_time) if job.next_run_time else None,
            "trigger": str(job.trigger),
        })
    
    return jsonify({
        "scheduler_running": scheduler.running,
        "jobs": jobs,
        "timezone": str(MX_TZ)
    })


# =============================================================================
# MAIN
# =============================================================================

# Register scheduler shutdown on app exit
atexit.register(stop_scheduler)

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

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
# ROUTES
# =============================================================================


@app.route("/login", methods=["GET", "POST"])
def login():
    """Simple PIN login for password protection."""
    error = None
    
    if request.method == "POST":
        pin = request.form.get("pin", "")
        if pin == RENTASCLARAS_PIN:
            session["authenticated"] = True
            return redirect(url_for("index"))
        else:
            error = "PIN incorrecto. Intente de nuevo."
    
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    """Clear the session and log out."""
    session.clear()
    return redirect(url_for("login"))


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

    # Use external template if feature flag is enabled
    template_vars = dict(
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
        active_tab="pagos",
    )
    
    return render_template("pagos.html", **template_vars)


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
    # - ONLY contracts expiring within the next 30 days
    # Exclude renovará (already handled, no action needed)
    action_needed_renewals_by_month = []
    action_needed_count = 0
    for month_group in upcoming_renewals_by_month:
        filtered_tenants = []
        for tenant in month_group["tenants"]:
            # Only include contracts expiring within next 30 days
            if not hasattr(tenant, 'days_until_expiry') or tenant.days_until_expiry > 30:
                continue
            
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

    template_vars = dict(
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
    
    return render_template("contratos.html", **template_vars)


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

"""
Pagos Blueprint - Payment Tracking Routes
==========================================

Main payment tracking page and related API endpoints.
"""

import logging
import os
from datetime import datetime

from database import (
    get_all_tenants,
    get_available_months,
    get_expiring_contracts,
    get_last_sync_time,
    get_message_counts_for_month,
    get_monthly_status,
    get_tenant_by_id,
    get_tenants_by_property,
    update_payment_status,
    update_tenant_phone,
)

from flask import Blueprint, jsonify, render_template, request
from routes.auth import login_required
from services.dates import (
    calculate_relative_time,
    format_date_excel,
    get_billing_month,
    MIN_BILLING_MONTH,
    MIN_BILLING_YEAR,
    parse_date,
    SPANISH_MONTHS,
    SPANISH_MONTHS_CAPITALIZED,
)
from services.late_fees import calculate_tenant_late_fee
from services.messages import create_whatsapp_link, generate_rent_reminder
from services.names import extract_display_name
from services.responses import error_response, not_found_response, success_response
from services.validation import (
    validate_payment_update,
    validate_phone,
    validate_tenant_id,
)


logger = logging.getLogger(__name__)
pagos_bp = Blueprint("pagos", __name__)

# Test mode configuration - controlled via environment variable
TEST_MODE = os.environ.get("TEST_MODE", "false").lower() == "true"
TEST_PHONE = os.environ.get("WHATSAPP_TEST_PHONE", "")


# =============================================================================
# ROUTES
# =============================================================================


@pagos_bp.route("/")
@login_required
def index():
    """Main payment tracking page."""
    today = datetime.now()

    # Use shared billing month function (Single Source of Truth)
    default_year, default_month, _ = get_billing_month(today)

    year = request.args.get("year", default_year, type=int)
    month = request.args.get("month", default_month, type=int)

    # Calculate prev/next month for navigation
    MIN_YEAR = 2025
    MIN_MONTH = 1

    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year

    can_go_prev = (prev_year > MIN_YEAR) or (
        prev_year == MIN_YEAR and prev_month >= MIN_MONTH
    )

    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year

    is_current_month = year == today.year and month == today.month
    is_future_month = (year > today.year) or (
        year == today.year and month > today.month
    )

    # Get payment status and message counts
    monthly_status = get_monthly_status(year, month)
    message_counts = get_message_counts_for_month(year, month)

    # Get tenants grouped by property
    all_tenants = get_all_tenants()
    tenants_by_property = {}

    # Filter out tenants whose contract starts in the current billing month
    # (they don't owe rent for their first month if they start on the 1st)
    filtered_tenants = []
    for tenant in all_tenants:
        if tenant.contract_start:
            start_date = parse_date(tenant.contract_start)
            if start_date and start_date.year == year and start_date.month == month:
                continue  # Skip tenants starting this month
        filtered_tenants.append(tenant)

    all_tenants = filtered_tenants

    for tenant in all_tenants:
        status = monthly_status.get(tenant.id, {})
        tenant.paid = bool(status.get("paid", 0))
        tenant.payment_method = status.get("payment_method")
        tenant.visits = status.get("visits", 0)
        tenant.visit_charge = status.get("visit_charge", 0)

        msg_info = message_counts.get(tenant.id, {"sent": 0, "failed": 0})
        tenant.msg_count = msg_info["sent"]
        tenant.msg_failed = msg_info["failed"]

        if tenant.property_name not in tenants_by_property:
            tenants_by_property[tenant.property_name] = []
        tenants_by_property[tenant.property_name].append(tenant)

    # Sort tenants: UNPAID FIRST
    for property_name in tenants_by_property:
        tenants_by_property[property_name].sort(key=lambda t: (t.paid, t.unit))

    month_name = SPANISH_MONTHS[month - 1]
    available_months = get_available_months()
    total_rent = sum(tenant.rent for tenant in all_tenants)

    # Format contract dates and calculate late fees
    for tenant in all_tenants:
        tenant.contract_start_formatted = format_date_excel(tenant.contract_start)
        tenant.contract_end_formatted = format_date_excel(tenant.contract_end)

        # Calculate late fees using the service
        fee_result = calculate_tenant_late_fee(
            rent=float(tenant.rent),
            year=year,
            month=month,
            is_paid=tenant.paid,
            is_current_month=is_current_month,
            is_future_month=is_future_month,
        )
        tenant.days_late = fee_result.days_late
        tenant.late_fee = float(fee_result.total_penalties)  # Renamed in new version
        tenant.total_owed = float(fee_result.total_due)  # Renamed in new version

    # Get expiring contracts
    expiring_contracts = get_expiring_contracts(days_ahead=60)
    expiring_critical = [c for c in expiring_contracts if c["urgency"] == "critical"]
    expiring_warning = [c for c in expiring_contracts if c["urgency"] == "warning"]
    expiring_expired = [c for c in expiring_contracts if c["urgency"] == "expired"]

    # Calculate totals
    total_late_fees = sum(t.late_fee for t in all_tenants if not t.paid)
    total_owed = sum(t.total_owed for t in all_tenants if not t.paid)
    unpaid_count = sum(1 for t in all_tenants if not t.paid)
    paid_count = sum(1 for t in all_tenants if t.paid)

    # Get last sync time
    last_sync = get_last_sync_time()
    last_sync_relative = calculate_relative_time(last_sync)

    template_vars = dict(
        tenants=all_tenants,
        tenants_by_property=tenants_by_property,
        total_tenants=len(all_tenants),
        total_rent=total_rent,
        total_late_fees=total_late_fees,
        total_owed=total_owed,
        unpaid_count=unpaid_count,
        paid_count=paid_count,
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


@pagos_bp.route("/api/message")
@login_required
def get_message():
    """Get rent reminder message for a tenant."""
    tenant_id = request.args.get("tenant_id")

    all_tenants = get_all_tenants()
    tenant = next((t for t in all_tenants if t.id == tenant_id), None)
    if not tenant:
        return jsonify({"error": "Tenant not found"}), 404

    today = datetime.now()
    month_name = SPANISH_MONTHS[today.month - 1]

    display_name = extract_display_name(tenant.name)
    message = generate_rent_reminder(display_name, month_name, tenant.rent)
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


@pagos_bp.route("/api/tenants")
@login_required
def list_tenants():
    """List all tenants."""
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


@pagos_bp.route("/api/payment", methods=["POST"])
@login_required
def update_payment():
    """Update payment status for a tenant and sync to Excel."""
    data = request.json
    if not data:
        return jsonify({"success": False, "error": "Request body is required"}), 400

    # Validate input data
    is_valid, error, validated = validate_payment_update(data)
    if not is_valid:
        logger.warning(f"Payment validation failed: {error}")
        return jsonify({"success": False, "error": error}), 400

    tenant_id = validated["tenant_id"]
    paid = validated["paid"]
    payment_method = validated.get("payment_method")
    visits = validated.get("visits", 0)
    visit_charge = validated.get("visit_charge", 0.0)
    year = validated["year"]
    month = validated["month"]

    today = datetime.now()

    update_payment_status(
        tenant_id=tenant_id,
        year=year,
        month=month,
        paid=paid,
        payment_method=payment_method,
        visits=visits,
        visit_charge=visit_charge,
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

            tenant = get_tenant_by_id(tenant_id)
            if tenant:
                config = ExcelConfig.from_env()
                client = ExcelClient(config)
                client.authenticate()

                spanish_months_cap = [
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
                month_name = spanish_months_cap[
                    month - 1
                ]  # Use request month, not today

                # Calculate total amount including visit charges
                total_amount = tenant.rent + visit_charge
                concept = f"Renta {month_name} {today.year}"
                if visits > 0:
                    concept += f" + {visits} visita{'s' if visits > 1 else ''}"

                payment = PaymentRow(
                    payment_id=generate_payment_id(),
                    tenant_id=tenant_id,
                    payment_date=today.strftime("%Y-%m-%d"),
                    amount=total_amount,
                    method=payment_method or "Web UI",
                    withdrawal_code=None,
                    bank=tenant.bank,
                    concept=concept,
                    folio=f"RC-{today.strftime('%Y%m%d')}-{tenant_id}",
                    confirmed=True,
                    notes=f"Marcado pagado desde la vista de tarjetas{' (incluye ' + str(visits) + ' visitas)' if visits > 0 else ''}",
                )
                client.add_payment(payment)
                logger.info(
                    f"Synced payment for {tenant.name} to Excel (${total_amount})"
                )
        except ImportError as e:
            # Excel client module not available - this is expected in some deployments
            logger.debug(f"Excel sync skipped - missing dependencies: {e}")
        except Exception as e:
            # Log but don't fail - payment was saved locally
            logger.warning(f"Excel sync failed (payment saved locally): {e}")

    return jsonify({"success": True})


@pagos_bp.route("/api/phone", methods=["POST"])
@login_required
def update_phone():
    """Update phone number for a tenant."""
    data = request.json
    if not data:
        return jsonify({"success": False, "error": "Request body is required"}), 400

    tenant_id = data.get("tenant_id")
    phone = data.get("phone", "")

    # Validate tenant_id
    is_valid, error = validate_tenant_id(tenant_id)
    if not is_valid:
        return jsonify({"success": False, "error": error}), 400

    # Validate phone format
    is_valid, error = validate_phone(phone)
    if not is_valid:
        return jsonify({"success": False, "error": error}), 400

    update_tenant_phone(tenant_id, phone)

    return jsonify({"success": True})


@pagos_bp.route("/api/sync-status", methods=["GET"])
@login_required
def api_sync_status():
    """Get the last sync time and database health."""
    last_sync = get_last_sync_time()
    last_sync_relative = calculate_relative_time(last_sync)

    return jsonify(
        {
            "success": True,
            "last_sync": last_sync,
            "last_sync_relative": last_sync_relative,
        }
    )

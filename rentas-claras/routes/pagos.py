"""
Pagos Blueprint - Payment Tracking Routes
==========================================

Main payment tracking page and related API endpoints.
"""

import os
from datetime import datetime

from flask import Blueprint, jsonify, render_template, request

from database import (
    get_all_tenants,
    get_available_months,
    get_expiring_contracts,
    get_last_sync_time,
    get_message_counts_for_month,
    get_monthly_status,
    get_tenant_by_id,
    Tenant,
    update_payment_status,
    update_tenant_phone,
)
from routes.auth import login_required
from services.dates import (
    calculate_relative_time,
    format_date_excel,
    format_date_spanish,
    get_month_name,
    SPANISH_MONTHS,
)
from services.late_fees import calculate_tenant_late_fee
from services.messages import create_whatsapp_link, generate_rent_reminder
from services.names import extract_display_name


pagos_bp = Blueprint("pagos", __name__)

# Test mode configuration
TEST_MODE = True
TEST_PHONE = os.environ.get("WHATSAPP_TEST_PHONE", "")


# =============================================================================
# ROUTES
# =============================================================================

@pagos_bp.route("/")
@login_required
def index():
    """Main payment tracking page."""
    today = datetime.now()

    # AUTO-SWITCH: After day 7, default to next month
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

    # Calculate prev/next month for navigation
    MIN_YEAR = 2026
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
        tenants_by_property[property_name].sort(
            key=lambda t: (t.paid, t.unit)
        )

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
        tenant.total_owed = float(fee_result.total_due)      # Renamed in new version

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
def update_payment():
    """Update payment status for a tenant and sync to Excel."""
    data = request.json
    tenant_id = data.get("tenant_id")
    paid = data.get("paid", False)
    payment_method = data.get("payment_method")
    visits = data.get("visits", 0)
    visit_charge = data.get("visit_charge", 0.0)

    today = datetime.now()
    
    # BUG FIX: Use year/month from request if provided, otherwise default to current
    # This ensures payments for historical/future months are saved correctly
    year = data.get("year", today.year)
    month = data.get("month", today.month)

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
                    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
                ]
                month_name = spanish_months_cap[today.month - 1]

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
                print(f"✅ Synced payment for {tenant.name} to Excel (${total_amount})")
        except ImportError as e:
            print(f"⚠️ Excel sync skipped - missing dependencies: {e}")
        except Exception as e:
            print(f"⚠️ Excel sync failed (payment saved locally): {e}")

    return jsonify({"success": True})


@pagos_bp.route("/api/phone", methods=["POST"])
def update_phone():
    """Update phone number for a tenant."""
    data = request.json
    tenant_id = data.get("tenant_id")
    phone = data.get("phone", "")

    update_tenant_phone(tenant_id, phone)

    return jsonify({"success": True})


@pagos_bp.route("/api/sync-status", methods=["GET"])
def api_sync_status():
    """Get the last sync time and database health."""
    last_sync = get_last_sync_time()
    last_sync_relative = calculate_relative_time(last_sync)

    return jsonify({
        "success": True,
        "last_sync": last_sync,
        "last_sync_relative": last_sync_relative
    })

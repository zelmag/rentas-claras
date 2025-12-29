"""
WhatsApp Blueprint - WhatsApp API Endpoints
============================================

WhatsApp Cloud API integration for sending rent reminders.
"""

from datetime import datetime

from database import get_all_tenants, get_monthly_status

from flask import Blueprint, jsonify, request
from routes.auth import login_required
from services.dates import SPANISH_MONTHS
from services.names import extract_display_name


whatsapp_bp = Blueprint("whatsapp", __name__)


# =============================================================================
# ROUTES
# =============================================================================


@whatsapp_bp.route("/api/whatsapp/status")
@login_required
def whatsapp_status():
    """Check if WhatsApp API is configured."""
    try:
        from src.whatsapp_client import check_credentials

        return jsonify(check_credentials())
    except ImportError:
        return jsonify({"configured": False, "error": "whatsapp_client not found"})


@whatsapp_bp.route("/api/whatsapp/send-all", methods=["POST"])
@login_required
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
    month_name = SPANISH_MONTHS[today.month - 1]

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


@whatsapp_bp.route("/api/whatsapp/send-one", methods=["POST"])
@login_required
def send_one_whatsapp():
    """Send WhatsApp reminder to a single tenant."""
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
    month_name = SPANISH_MONTHS[today.month - 1]

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

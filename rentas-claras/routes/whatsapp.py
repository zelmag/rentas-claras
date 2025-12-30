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
    ⚠️ DEPRECATED: Use /api/reminders/send instead.
    
    This endpoint is deprecated because:
    - It does NOT log messages to message_logs table
    - It uses outdated function signatures  
    - It does not support template selection
    
    Keeping for backward compatibility but redirecting to new endpoint.
    """
    import warnings
    warnings.warn(
        "/api/whatsapp/send-all is deprecated. Use /api/reminders/send instead.",
        DeprecationWarning
    )
    
    # Return a deprecation notice
    return (
        jsonify(
            {
                "success": False,
                "error": "Este endpoint está obsoleto. Usa /api/reminders/send en su lugar.",
                "deprecated": True,
                "redirect_to": "/api/reminders/send",
            }
        ),
        410,  # HTTP 410 Gone
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

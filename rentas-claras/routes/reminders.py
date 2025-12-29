"""
Reminders Blueprint - Rent Reminder Approval System
=====================================================

Zero-Mistake rent reminder system:
- Preview all pending reminders before sending
- Human approval required (no auto-send)
- Full audit trail
- Idempotency protection

Author: RentasClaras Engineering
Date: December 2024
"""

from datetime import datetime
from decimal import Decimal

from database import (
    get_all_tenants,
    get_db_connection,
    get_message_counts_for_month,
    get_monthly_status,
    log_message_sent,
    was_message_sent_today,
)

from flask import Blueprint, jsonify, render_template, request
from routes.auth import login_required
from services.dates import get_billing_month, SPANISH_MONTHS
from services.names import extract_display_name


reminders_bp = Blueprint("reminders", __name__)


# =============================================================================
# PAGE ROUTES
# =============================================================================


@reminders_bp.route("/recordatorios")
@login_required
def recordatorios_page():
    """
    Recordatorios approval page.

    Shows all unpaid tenants with preview of messages to be sent.
    Dad reviews and clicks "Enviar" to approve.
    """
    today = datetime.now()
    year, month, month_name = get_billing_month(today)

    # Get all tenants and their payment status
    all_tenants = get_all_tenants()
    monthly_status = get_monthly_status(year, month)
    message_counts = get_message_counts_for_month(year, month)

    # Fetch message statuses and replies for "Ya enviados hoy" section
    message_status_map = _get_today_message_statuses()
    reply_map = _get_tenant_replies()

    # Build list of unpaid tenants
    unpaid_tenants = []
    skipped_no_phone = []
    already_messaged_today = []

    for tenant in all_tenants:
        status = monthly_status.get(tenant.id, {})
        is_paid = bool(status.get("paid", 0))

        if is_paid:
            continue  # Skip paid tenants

        # Check if already messaged today
        already_sent = was_message_sent_today(tenant.id, "morning_reminder")

        # Get message history for this tenant
        msg_count = message_counts.get(tenant.id, {"sent": 0, "failed": 0})

        tenant_data = {
            "id": tenant.id,
            "name": tenant.name,
            "display_name": extract_display_name(tenant.name),
            "phone": tenant.phone or "",
            "property_name": tenant.property_name,
            "unit": tenant.unit,
            "rent": float(tenant.rent),
            "rent_formatted": f"${tenant.rent:,.0f}",
            "has_phone": bool(tenant.phone and tenant.phone.strip()),
            "messages_sent_this_month": msg_count["sent"],
            "already_sent_today": already_sent,
        }

        if already_sent:
            # Enrich with status data from message_logs
            msg_status = message_status_map.get(tenant.id, {})
            tenant_data["status"] = msg_status.get("status", "sent")
            tenant_data["last_message_time"] = msg_status.get("sent_time", "Hoy")
            tenant_data["last_template"] = msg_status.get("template", "Recordatorio")
            
            # Check for replies
            reply_info = reply_map.get(tenant.id)
            if reply_info:
                tenant_data["has_reply"] = True
                tenant_data["reply_preview"] = reply_info.get("preview", "")
            else:
                tenant_data["has_reply"] = False
                tenant_data["reply_preview"] = ""
            
            already_messaged_today.append(tenant_data)
        elif not tenant_data["has_phone"]:
            skipped_no_phone.append(tenant_data)
        else:
            unpaid_tenants.append(tenant_data)

    # Calculate totals
    total_pending = (
        len(unpaid_tenants) + len(skipped_no_phone) + len(already_messaged_today)
    )
    total_amount = sum(t["rent"] for t in unpaid_tenants)
    ready_to_send = len(unpaid_tenants)

    # Get last send time (most recent message)
    last_send_time = _get_last_send_time()

    return render_template(
        "recordatorios.html",
        month_name=month_name,
        year=year,
        unpaid_tenants=unpaid_tenants,
        skipped_no_phone=skipped_no_phone,
        already_messaged_today=already_messaged_today,
        total_pending=total_pending,
        total_amount=total_amount,
        total_amount_formatted=f"${total_amount:,.0f}",
        ready_to_send=ready_to_send,
        last_send_time=last_send_time,
        active_tab="recordatorios",
        now=today,  # Pass current datetime for template logic
    )


# =============================================================================
# API ROUTES
# =============================================================================


@reminders_bp.route("/api/reminders/preview")
@login_required
def get_reminders_preview():
    """
    API: Get preview of all pending reminders.

    Returns list of unpaid tenants with their reminder details.
    Used by dashboard widget and approval screen.
    """
    today = datetime.now()
    year, month, month_name = get_billing_month(today)

    all_tenants = get_all_tenants()
    monthly_status = get_monthly_status(year, month)

    unpaid = []
    no_phone = []
    already_sent = []

    for tenant in all_tenants:
        status = monthly_status.get(tenant.id, {})
        is_paid = bool(status.get("paid", 0))

        if is_paid:
            continue

        sent_today = was_message_sent_today(tenant.id, "morning_reminder")
        has_phone = bool(tenant.phone and tenant.phone.strip())

        tenant_info = {
            "id": tenant.id,
            "name": tenant.name,
            "display_name": extract_display_name(tenant.name),
            "phone": tenant.phone or "",
            "property_name": tenant.property_name,
            "unit": tenant.unit,
            "rent": float(tenant.rent),
            "rent_formatted": f"${tenant.rent:,.0f}",
            "has_phone": has_phone,
        }

        if sent_today:
            already_sent.append(tenant_info)
        elif not has_phone:
            no_phone.append(tenant_info)
        else:
            unpaid.append(tenant_info)

    total_amount = sum(t["rent"] for t in unpaid)

    return jsonify(
        {
            "success": True,
            "month_name": month_name,
            "ready_to_send": unpaid,
            "no_phone": no_phone,
            "already_sent_today": already_sent,
            "summary": {
                "ready_count": len(unpaid),
                "no_phone_count": len(no_phone),
                "already_sent_count": len(already_sent),
                "total_amount": total_amount,
                "total_amount_formatted": f"${total_amount:,.0f}",
            },
        }
    )


@reminders_bp.route("/api/reminders/send", methods=["POST"])
@login_required
def send_approved_reminders():
    """
    API: Send reminders to approved tenants.

    Request body:
    {
        "tenant_ids": ["MAT-A", "MUZ-B", ...],  // List of tenant IDs to send to
        "template": "recordatorio_renta"        // Template to use
    }

    Returns summary of sent/failed messages.
    """
    try:
        from src.whatsapp_client import check_credentials, WhatsAppClient
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

    # Check credentials
    creds = check_credentials()
    if not creds["configured"]:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "WhatsApp API no configurado. Revisa las credenciales.",
                    "credentials": creds,
                }
            ),
            400,
        )

    data = request.get_json() or {}
    tenant_ids = data.get("tenant_ids", [])
    template = data.get("template", "recordatorio_renta")

    # Validate template - now includes hello_world for testing
    valid_templates = ["hello_world", "recordatorio_renta", "recordatorio_tarde", "aviso_recargo"]
    if template not in valid_templates:
        template = "recordatorio_renta"

    if not tenant_ids:
        return (
            jsonify({"success": False, "error": "No se seleccionaron inquilinos"}),
            400,
        )

    # Get tenant data
    all_tenants = get_all_tenants()
    tenant_map = {t.id: t for t in all_tenants}

    # Initialize WhatsApp client
    client = WhatsAppClient()

    results = {
        "sent": [],
        "failed": [],
        "skipped": [],
    }

    for tenant_id in tenant_ids:
        tenant = tenant_map.get(tenant_id)

        if not tenant:
            results["skipped"].append(
                {"id": tenant_id, "reason": "Inquilino no encontrado"}
            )
            continue

        if not tenant.phone:
            results["skipped"].append(
                {
                    "id": tenant_id,
                    "name": tenant.name,
                    "reason": "Sin número de teléfono",
                }
            )
            continue

        # Check idempotency - don't send twice
        if was_message_sent_today(tenant_id, "morning_reminder"):
            results["skipped"].append(
                {
                    "id": tenant_id,
                    "name": tenant.name,
                    "reason": "Ya se envió mensaje hoy",
                }
            )
            continue

        # Send the reminder based on selected template
        display_name = extract_display_name(tenant.name)

        if template == "hello_world":
            # Use the pre-approved hello_world template for testing
            response = client.send_template_message(
                to_phone=tenant.phone,
                template_name="hello_world",
                parameters=[],
                language_code="en_US",
            )
        elif template == "recordatorio_renta":
            response = client.send_rent_reminder(
                to_phone=tenant.phone,
                tenant_name=display_name,
                amount=float(tenant.rent),
            )
        elif template == "recordatorio_tarde":
            response = client.send_afternoon_reminder(
                to_phone=tenant.phone,
                tenant_name=display_name,
                amount=float(tenant.rent),
            )
        elif template == "aviso_recargo":
            response = client.send_late_fee_notice(
                to_phone=tenant.phone,
                tenant_name=display_name,
                base_rent=float(tenant.rent),
                total_with_fees=float(tenant.rent),  # TODO: calculate actual late fee
            )
        else:
            # Fallback to morning reminder
            response = client.send_rent_reminder(
                to_phone=tenant.phone,
                tenant_name=display_name,
                amount=float(tenant.rent),
            )

        if response.success:
            # Log successful send
            log_message_sent(
                tenant_id=tenant_id,
                message_type="morning_reminder",
                message_id=response.message_id,
                status="sent",
            )
            results["sent"].append(
                {
                    "id": tenant_id,
                    "name": tenant.name,
                    "phone": tenant.phone,
                    "message_id": response.message_id,
                }
            )
        else:
            # Log failed attempt
            log_message_sent(
                tenant_id=tenant_id,
                message_type="morning_reminder",
                status="failed",
                error_message=response.error,
            )
            results["failed"].append(
                {
                    "id": tenant_id,
                    "name": tenant.name,
                    "phone": tenant.phone,
                    "error": response.error,
                }
            )

    return jsonify(
        {
            "success": True,
            "summary": {
                "sent": len(results["sent"]),
                "failed": len(results["failed"]),
                "skipped": len(results["skipped"]),
            },
            "details": results,
            "template_used": template,
        }
    )


@reminders_bp.route("/api/reminders/test", methods=["POST"])
@login_required
def send_test_reminder():
    """
    API: Send a test message using the pre-approved 'hello_world' template.
    
    This is for testing the WhatsApp API connection while your custom
    templates are still pending approval.
    
    Request body:
    {
        "phone": "+52 81 1234 5678"  // Your phone number
    }
    """
    try:
        from src.whatsapp_client import WhatsAppClient
    except ImportError:
        return (
            jsonify({
                "success": False,
                "error": "WhatsApp client not installed. Check src/whatsapp_client.py",
            }),
            500,
        )
    
    data = request.get_json() or {}
    phone = data.get("phone", "").strip()
    
    if not phone:
        return (
            jsonify({
                "success": False,
                "error": "Se requiere número de teléfono",
            }),
            400,
        )
    
    client = WhatsAppClient()
    
    # Check credentials first
    creds = client.check_credentials()
    if not creds["configured"]:
        return (
            jsonify({
                "success": False,
                "error": "WhatsApp API no configurado. Revisa las credenciales en .env",
                "credentials": creds,
            }),
            400,
        )
    
    # Send using the pre-approved hello_world template
    response = client.send_template_message(
        to_phone=phone,
        template_name="hello_world",
        parameters=[],  # hello_world has no parameters
        language_code="en_US",  # hello_world is in English
    )
    
    if response.success:
        # Log the test message so "Último envío" updates
        log_message_sent(
            tenant_id="TEST",
            message_type="test_hello_world",
            message_id=response.message_id,
            status="sent",
        )
        return jsonify({
            "success": True,
            "message": "¡Mensaje de prueba enviado!",
            "message_id": response.message_id,
            "phone": phone,
        })
    else:
        return jsonify({
            "success": False,
            "error": response.error,
            "error_code": response.error_code,
        }), 400


@reminders_bp.route("/api/reminders/retry", methods=["POST"])
@login_required
def retry_failed_reminder():
    """
    API: Retry sending a failed reminder to a specific tenant.
    
    Request body:
    {
        "tenant_id": "MAT-A",
        "template": "hello_world"  // Optional, defaults to recordatorio_renta
    }
    
    This bypasses the idempotency check (was_message_sent_today) since
    the previous attempt failed.
    """
    try:
        from src.whatsapp_client import check_credentials, WhatsAppClient
    except ImportError:
        return (
            jsonify({
                "success": False,
                "error": "WhatsApp client not installed. Check src/whatsapp_client.py",
            }),
            500,
        )

    # Check credentials
    creds = check_credentials()
    if not creds["configured"]:
        return (
            jsonify({
                "success": False,
                "error": "WhatsApp API no configurado. Revisa las credenciales.",
                "credentials": creds,
            }),
            400,
        )

    data = request.get_json() or {}
    tenant_id = data.get("tenant_id")
    template = data.get("template", "recordatorio_renta")

    if not tenant_id:
        return (
            jsonify({"success": False, "error": "Se requiere tenant_id"}),
            400,
        )

    # Validate template
    valid_templates = ["hello_world", "recordatorio_renta", "recordatorio_tarde", "aviso_recargo"]
    if template not in valid_templates:
        template = "recordatorio_renta"

    # Get tenant data
    all_tenants = get_all_tenants()
    tenant = next((t for t in all_tenants if t.id == tenant_id), None)

    if not tenant:
        return (
            jsonify({"success": False, "error": "Inquilino no encontrado"}),
            404,
        )

    if not tenant.phone:
        return (
            jsonify({"success": False, "error": "El inquilino no tiene teléfono registrado"}),
            400,
        )

    # Initialize WhatsApp client
    client = WhatsAppClient()
    display_name = extract_display_name(tenant.name)

    # Send the reminder based on selected template
    if template == "hello_world":
        response = client.send_template_message(
            to_phone=tenant.phone,
            template_name="hello_world",
            parameters=[],
            language_code="en_US",
        )
    elif template == "recordatorio_renta":
        response = client.send_rent_reminder(
            to_phone=tenant.phone,
            tenant_name=display_name,
            amount=float(tenant.rent),
        )
    elif template == "recordatorio_tarde":
        response = client.send_afternoon_reminder(
            to_phone=tenant.phone,
            tenant_name=display_name,
            amount=float(tenant.rent),
        )
    elif template == "aviso_recargo":
        response = client.send_late_fee_notice(
            to_phone=tenant.phone,
            tenant_name=display_name,
            base_rent=float(tenant.rent),
            total_with_fees=float(tenant.rent),
        )
    else:
        response = client.send_rent_reminder(
            to_phone=tenant.phone,
            tenant_name=display_name,
            amount=float(tenant.rent),
        )

    if response.success:
        # Update the existing failed message to 'sent' status
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # First, try to update the most recent failed message
        cursor.execute(
            """
            UPDATE message_logs 
            SET status = 'sent', 
                message_id = ?, 
                sent_at = ?,
                error_message = NULL
            WHERE tenant_id = ? 
              AND status = 'failed'
              AND date(sent_at) = date('now')
            """,
            (response.message_id, datetime.now().isoformat(), tenant_id)
        )
        
        if cursor.rowcount == 0:
            # No failed message found, create a new log entry
            log_message_sent(
                tenant_id=tenant_id,
                message_type="morning_reminder",
                message_id=response.message_id,
                status="sent",
            )
        
        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "message": f"¡Mensaje reenviado a {display_name}!",
            "message_id": response.message_id,
            "tenant_id": tenant_id,
        })
    else:
        return jsonify({
            "success": False,
            "error": response.error,
            "error_code": response.error_code,
        }), 400


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _get_last_send_time() -> str:
    """Get formatted string of last message send time."""
    from database import get_db_connection

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT sent_at FROM message_logs
        WHERE status = 'sent'
        ORDER BY sent_at DESC
        LIMIT 1
    """
    )

    row = cursor.fetchone()
    conn.close()

    if row and row["sent_at"]:
        try:
            dt = datetime.fromisoformat(row["sent_at"])
            # Format: "1 Dic, 8:03 AM"
            day = dt.day
            month_abbr = SPANISH_MONTHS[dt.month - 1][:3].capitalize()
            hour = dt.strftime("%I:%M %p").lstrip("0")
            return f"{day} {month_abbr}, {hour}"
        except (ValueError, IndexError):
            return "Fecha desconocida"

    return "Nunca"


def _get_today_message_statuses() -> dict:
    """
    Get message statuses for all messages sent today.
    
    Returns a dict mapping tenant_id to:
    {
        "status": "sent" | "delivered" | "read" | "failed",
        "sent_time": "8:32 AM",
        "template": "Recordatorio"
    }
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    cursor.execute(
        """
        SELECT tenant_id, status, sent_at, message_type, delivered_at, read_at
        FROM message_logs
        WHERE sent_at >= ?
        ORDER BY sent_at DESC
        """,
        (today_start.isoformat(),)
    )
    
    result = {}
    for row in cursor.fetchall():
        tenant_id = row["tenant_id"]
        
        # Only keep the most recent message per tenant
        if tenant_id in result:
            continue
        
        # Format sent time
        sent_time = "Hoy"
        if row["sent_at"]:
            try:
                dt = datetime.fromisoformat(row["sent_at"])
                sent_time = dt.strftime("%I:%M %p").lstrip("0")
            except (ValueError, TypeError):
                pass
        
        # Map message_type to friendly template name
        template_map = {
            "morning_reminder": "Recordatorio",
            "afternoon_reminder": "Recordatorio Tarde",
            "late_fee_notice": "Aviso Recargo",
            "test_hello_world": "Hello World (Prueba)",
        }
        template_name = template_map.get(row["message_type"], "Recordatorio")
        
        result[tenant_id] = {
            "status": row["status"] or "sent",
            "sent_time": sent_time,
            "template": template_name,
        }
    
    conn.close()
    return result


def _get_tenant_replies() -> dict:
    """
    Get the most recent reply from each tenant (within last 24 hours).
    
    Returns a dict mapping tenant_id to:
    {
        "preview": "Ya pagué, gracias!",
        "received_at": datetime
    }
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if incoming_messages table exists
    cursor.execute(
        """
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='incoming_messages'
        """
    )
    if not cursor.fetchone():
        conn.close()
        return {}
    
    # Get replies from last 24 hours
    yesterday = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    cursor.execute(
        """
        SELECT tenant_id, message_body, received_at
        FROM incoming_messages
        WHERE tenant_id IS NOT NULL
          AND received_at >= ?
        ORDER BY received_at DESC
        """,
        (yesterday.isoformat(),)
    )
    
    result = {}
    for row in cursor.fetchall():
        tenant_id = row["tenant_id"]
        
        # Only keep the most recent reply per tenant
        if tenant_id in result:
            continue
        
        # Truncate preview to ~40 chars
        message_body = row["message_body"] or ""
        if len(message_body) > 40:
            preview = message_body[:37] + "..."
        else:
            preview = message_body
        
        result[tenant_id] = {
            "preview": preview,
            "received_at": row["received_at"],
        }
    
    conn.close()
    return result

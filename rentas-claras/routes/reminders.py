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

import json
import logging
import traceback
from datetime import datetime

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
from services.late_fees import calculate_late_fee
from services.names import extract_display_name


reminders_bp = Blueprint("reminders", __name__)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("Reminders")


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
    # KEY CHANGE: Show ALL unpaid tenants in the main list, regardless of whether
    # they've been messaged today. We keep sending until they PAY.
    unpaid_tenants = []
    skipped_no_phone = []

    for tenant in all_tenants:
        status = monthly_status.get(tenant.id, {})
        is_paid = bool(status.get("paid", 0))

        if is_paid:
            continue  # Skip ONLY paid tenants - this is the only filter now

        # Check if already messaged today
        already_sent = was_message_sent_today(tenant.id, "morning_reminder")

        # Get message history for this tenant
        msg_count = message_counts.get(tenant.id, {"sent": 0, "failed": 0})

        # Enrich with status data from message_logs (if messaged today)
        msg_status = message_status_map.get(tenant.id, {})
        
        # Check for replies
        reply_info = reply_map.get(tenant.id)

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
            # Message status info (if messaged today)
            "status": msg_status.get("status", "sent") if already_sent else None,
            "last_message_time": msg_status.get("sent_time", "Hoy") if already_sent else None,
            "last_template": msg_status.get("template", "Recordatorio") if already_sent else None,
            # Reply info
            "has_reply": bool(reply_info) if already_sent else False,
            "reply_preview": reply_info.get("preview", "") if reply_info else "",
        }

        if not tenant_data["has_phone"]:
            skipped_no_phone.append(tenant_data)
        else:
            # ALL unpaid tenants with phone go in the main list
            unpaid_tenants.append(tenant_data)

    # Calculate totals
    total_pending = len(unpaid_tenants) + len(skipped_no_phone)
    total_amount = sum(t["rent"] for t in unpaid_tenants)
    ready_to_send = len(unpaid_tenants)
    
    # Count how many were already messaged today (for the summary card)
    already_messaged_count = sum(1 for t in unpaid_tenants if t.get("already_sent_today"))

    # Get last send time (most recent message)
    last_send_time = _get_last_send_time()

    return render_template(
        "recordatorios.html",
        month_name=month_name,
        year=year,
        unpaid_tenants=unpaid_tenants,
        skipped_no_phone=skipped_no_phone,
        already_messaged_count=already_messaged_count,
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
    logger.info("="*60)
    logger.info("📤 /api/reminders/send called")
    logger.info("="*60)
    
    try:
        from src.whatsapp_client import check_credentials, WhatsAppClient
        logger.debug("WhatsApp client imported successfully")
    except ImportError as e:
        logger.error(f"Failed to import WhatsApp client: {e}")
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
    logger.debug(f"Credentials check: {creds}")
    
    if not creds["configured"]:
        logger.error("WhatsApp credentials not configured")
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
    # Note: force_resend parameter removed in Bug #7 fix - idempotency check was already removed
    
    logger.info(f"Request data: tenant_ids={tenant_ids}, template={template}")

    # Validate template
    valid_templates = [
        "recordatorio_renta",
        "recordatorio_tarde",
        "aviso_recargo",
    ]
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
        logger.debug(f"Processing tenant: {tenant_id}")

        if not tenant:
            logger.warning(f"Tenant {tenant_id} not found")
            results["skipped"].append(
                {"id": tenant_id, "reason": "Inquilino no encontrado"}
            )
            continue

        if not tenant.phone:
            logger.warning(f"Tenant {tenant_id} has no phone")
            results["skipped"].append(
                {
                    "id": tenant_id,
                    "name": tenant.name,
                    "reason": "Sin número de teléfono",
                }
            )
            continue

        # NOTE: No idempotency check here - we can send multiple messages to unpaid tenants
        # The only filter is: skip if they're already PAID (handled in the page, not here)
        logger.info(f"Tenant {tenant_id}: proceeding to send message")

        # Send the reminder based on selected template
        display_name = extract_display_name(tenant.name)
        logger.info(f"Sending {template} to {display_name} ({tenant.phone})")

        try:
            if template == "recordatorio_renta":
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
                # Calculate late fee - 10% penalty starting Day 2
                day_of_month = datetime.now().day
                days_late = max(0, day_of_month - 1)  # Day 2 = 1 day late
                late_fee = calculate_late_fee(days_late)
                total_with_fees = float(tenant.rent) + late_fee
                
                response = client.send_late_fee_notice(
                    to_phone=tenant.phone,
                    tenant_name=display_name,
                    base_rent=float(tenant.rent),
                    total_with_fees=total_with_fees,
                )
            else:
                # Fallback to morning reminder
                response = client.send_rent_reminder(
                    to_phone=tenant.phone,
                    tenant_name=display_name,
                    amount=float(tenant.rent),
                )
            
            logger.info(f"WhatsApp API response: success={response.success}, message_id={response.message_id}, error={response.error}")

            if response.success:
                # Bug #5 fix: Log correct message_type based on template
                message_type_map = {
                    "recordatorio_renta": "morning_reminder",
                    "recordatorio_tarde": "afternoon_reminder",
                    "aviso_recargo": "late_fee_notice",
                }
                message_type = message_type_map.get(template, "morning_reminder")
                
                log_message_sent(
                    tenant_id=tenant_id,
                    message_type=message_type,
                    message_id=response.message_id,
                    status="sent",
                )
                logger.info(f"✅ Message sent successfully to {tenant.name}")
                results["sent"].append(
                    {
                        "id": tenant_id,
                        "name": tenant.name,
                        "phone": tenant.phone,
                        "message_id": response.message_id,
                    }
                )
            else:
                # Bug #5 fix: Log correct message_type on failure too
                message_type_map = {
                    "recordatorio_renta": "morning_reminder",
                    "recordatorio_tarde": "afternoon_reminder",
                    "aviso_recargo": "late_fee_notice",
                }
                message_type = message_type_map.get(template, "morning_reminder")
                
                log_message_sent(
                    tenant_id=tenant_id,
                    message_type=message_type,
                    status="failed",
                    error_message=response.error,
                )
                logger.error(f"❌ Message failed for {tenant.name}: {response.error}")
                results["failed"].append(
                    {
                        "id": tenant_id,
                        "name": tenant.name,
                        "phone": tenant.phone,
                        "error": response.error,
                    }
                )
        except Exception as e:
            logger.error(f"Exception sending to {tenant.name}: {e}")
            logger.error(traceback.format_exc())
            results["failed"].append(
                {
                    "id": tenant_id,
                    "name": tenant.name,
                    "phone": tenant.phone,
                    "error": str(e),
                }
            )

    response_data = {
        "success": True,
        "summary": {
            "sent": len(results["sent"]),
            "failed": len(results["failed"]),
            "skipped": len(results["skipped"]),
        },
        "details": results,
        "template_used": template,
    }
    
    logger.info(f"Final response: {json.dumps(response_data, indent=2)}")
    return jsonify(response_data)


@reminders_bp.route("/api/reminders/test", methods=["POST"])
@login_required
def send_test_reminder():
    """
    API: Send a test message using the 'recordatorio_renta' template.

    Request body (optional):
    {
        "phone": "+52 81 1234 5678"  // Optional - defaults to WHATSAPP_TEST_PHONE env var
    }
    """
    import os
    
    try:
        from src.whatsapp_client import WhatsAppClient
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

    data = request.get_json() or {}
    phone = data.get("phone", "").strip()
    
    # Bug #9 fix: If no phone provided, use WHATSAPP_TEST_PHONE from .env
    if not phone:
        phone = os.getenv("WHATSAPP_TEST_PHONE", "").strip()

    if not phone:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Se requiere número de teléfono. Configura WHATSAPP_TEST_PHONE en .env o proporciona un número.",
                }
            ),
            400,
        )

    client = WhatsAppClient()

    # Check credentials first
    creds = client.check_credentials()
    if not creds["configured"]:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "WhatsApp API no configurado. Revisa las credenciales en .env",
                    "credentials": creds,
                }
            ),
            400,
        )

    # Send test using recordatorio_renta template
    response = client.send_rent_reminder(
        to_phone=phone,
        tenant_name="Prueba",
        amount=1000.00,
    )

    if response.success:
        # Log the test message so "Último envío" updates
        log_message_sent(
            tenant_id="TEST",
            message_type="test_reminder",
            message_id=response.message_id,
            status="sent",
        )
        return jsonify(
            {
                "success": True,
                "message": "¡Mensaje de prueba enviado!",
                "message_id": response.message_id,
                "phone": phone,
            }
        )
    else:
        return (
            jsonify(
                {
                    "success": False,
                    "error": response.error,
                    "error_code": response.error_code,
                }
            ),
            400,
        )


@reminders_bp.route("/api/reminders/retry", methods=["POST"])
@login_required
def retry_failed_reminder():
    """
    API: Retry sending a failed reminder to a specific tenant.

    Request body:
    {
        "tenant_id": "MAT-A",
        "template": "recordatorio_renta"  // Optional, defaults to recordatorio_renta
    }

    This bypasses the idempotency check (was_message_sent_today) since
    the previous attempt failed.
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
    tenant_id = data.get("tenant_id")
    template = data.get("template", "recordatorio_renta")

    if not tenant_id:
        return (
            jsonify({"success": False, "error": "Se requiere tenant_id"}),
            400,
        )

    # Validate template
    valid_templates = [
        "recordatorio_renta",
        "recordatorio_tarde",
        "aviso_recargo",
    ]
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
            jsonify(
                {"success": False, "error": "El inquilino no tiene teléfono registrado"}
            ),
            400,
        )

    # Initialize WhatsApp client
    client = WhatsAppClient()
    display_name = extract_display_name(tenant.name)

    # Send the reminder based on selected template
    if template == "recordatorio_renta":
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
            (response.message_id, datetime.now().isoformat(), tenant_id),
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

        return jsonify(
            {
                "success": True,
                "message": f"¡Mensaje reenviado a {display_name}!",
                "message_id": response.message_id,
                "tenant_id": tenant_id,
            }
        )
    else:
        return (
            jsonify(
                {
                    "success": False,
                    "error": response.error,
                    "error_code": response.error_code,
                }
            ),
            400,
        )


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
            # Format: "1 Dic, 8:03 p.m."
            day = dt.day
            month_abbr = SPANISH_MONTHS[dt.month - 1][:3].capitalize()
            # Manual AM/PM formatting to avoid locale-dependent "p. m." with spaces
            hour_12 = dt.hour % 12 or 12
            minute = dt.minute
            am_pm = "a.m." if dt.hour < 12 else "p.m."
            return f"{day} {month_abbr}, {hour_12}:{minute:02d} {am_pm}"
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
        (today_start.isoformat(),),
    )

    result = {}
    for row in cursor.fetchall():
        tenant_id = row["tenant_id"]

        # Only keep the most recent message per tenant
        if tenant_id in result:
            continue

        # Format sent time - manual AM/PM to avoid locale issues
        sent_time = "Hoy"
        if row["sent_at"]:
            try:
                dt = datetime.fromisoformat(row["sent_at"])
                hour_12 = dt.hour % 12 or 12
                am_pm = "a.m." if dt.hour < 12 else "p.m."
                sent_time = f"{hour_12}:{dt.minute:02d} {am_pm}"
            except (ValueError, TypeError):
                pass

        # Map message_type to friendly template name
        template_map = {
            "morning_reminder": "Recordatorio",
            "afternoon_reminder": "Recordatorio Tarde",
            "late_fee_notice": "Aviso Recargo",
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
        (yesterday.isoformat(),),
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

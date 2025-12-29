"""
WhatsApp Webhook Blueprint
===========================

Handles incoming webhooks from Meta's WhatsApp Cloud API:
- Message delivery status updates (sent → delivered → read)
- Incoming messages from tenants (replies)

Setup:
1. Deploy to Fly.io (needs public URL)
2. Configure webhook URL in Meta Developer Portal:
   URL: https://your-app.fly.dev/webhook/whatsapp
   Verify Token: Set WHATSAPP_WEBHOOK_VERIFY_TOKEN in .env

Author: RentasClaras Engineering
Date: December 2024
"""

import hashlib
import hmac
import logging
import os
import re
from datetime import datetime

from flask import Blueprint, request, jsonify

from database import get_db_connection, get_all_tenants


webhook_bp = Blueprint("webhook", __name__)
logger = logging.getLogger("WhatsAppWebhook")


# =============================================================================
# WEBHOOK VERIFICATION (GET request from Meta)
# =============================================================================


@webhook_bp.route("/webhook/whatsapp", methods=["GET"])
def verify_webhook():
    """
    Webhook verification endpoint.
    
    Meta sends a GET request with these query parameters:
    - hub.mode: Should be "subscribe"
    - hub.verify_token: Must match your WHATSAPP_WEBHOOK_VERIFY_TOKEN
    - hub.challenge: A random string you must echo back
    
    If verification succeeds, return the challenge.
    """
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    
    verify_token = os.getenv("WHATSAPP_WEBHOOK_VERIFY_TOKEN", "")
    
    if not verify_token:
        logger.error("WHATSAPP_WEBHOOK_VERIFY_TOKEN not configured in .env")
        return "Webhook verify token not configured", 500
    
    if mode == "subscribe" and token == verify_token:
        logger.info("Webhook verified successfully!")
        return challenge, 200
    else:
        logger.warning(f"Webhook verification failed. Mode: {mode}, Token match: {token == verify_token}")
        return "Verification failed", 403


# =============================================================================
# WEBHOOK EVENTS (POST request from Meta)
# =============================================================================


@webhook_bp.route("/webhook/whatsapp", methods=["POST"])
def receive_webhook():
    """
    Receive webhook events from WhatsApp.
    
    Event types:
    1. Status updates: sent → delivered → read → failed
    2. Incoming messages: text, image, audio, etc.
    
    Always return 200 OK quickly to acknowledge receipt,
    otherwise Meta will retry and potentially rate-limit you.
    """
    # Verify signature (optional but recommended for security)
    if not _verify_signature(request):
        logger.warning("Invalid webhook signature")
        return "Invalid signature", 401
    
    try:
        data = request.get_json()
        
        if not data:
            return "OK", 200
        
        # Process each entry
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                if change.get("field") == "messages":
                    value = change.get("value", {})
                    
                    # Handle status updates (delivery receipts)
                    statuses = value.get("statuses", [])
                    for status in statuses:
                        _handle_status_update(status)
                    
                    # Handle incoming messages
                    messages = value.get("messages", [])
                    for message in messages:
                        _handle_incoming_message(message, value.get("contacts", []))
        
        return "OK", 200
        
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        # Still return 200 to prevent Meta from retrying
        return "OK", 200


# =============================================================================
# STATUS UPDATE HANDLER
# =============================================================================


def _handle_status_update(status: dict):
    """
    Handle message status updates.
    
    Status flow: sent → delivered → read
    
    Example status object:
    {
        "id": "wamid.xxx",
        "status": "delivered",
        "timestamp": "1703875200",
        "recipient_id": "521234567890"
    }
    """
    message_id = status.get("id")
    status_value = status.get("status")  # sent, delivered, read, failed
    timestamp = status.get("timestamp")
    
    if not message_id or not status_value:
        return
    
    logger.info(f"Status update: {message_id} → {status_value}")
    
    # Convert Unix timestamp to ISO format
    if timestamp:
        try:
            dt = datetime.fromtimestamp(int(timestamp))
            timestamp_iso = dt.isoformat()
        except (ValueError, TypeError):
            timestamp_iso = datetime.now().isoformat()
    else:
        timestamp_iso = datetime.now().isoformat()
    
    # Update the message log
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if status_value == "delivered":
            cursor.execute(
                """
                UPDATE message_logs 
                SET status = 'delivered', delivered_at = ?
                WHERE message_id = ? AND status = 'sent'
                """,
                (timestamp_iso, message_id)
            )
        elif status_value == "read":
            cursor.execute(
                """
                UPDATE message_logs 
                SET status = 'read', read_at = ?
                WHERE message_id = ? AND status IN ('sent', 'delivered')
                """,
                (timestamp_iso, message_id)
            )
        elif status_value == "failed":
            # Get error details if available
            error_info = status.get("errors", [{}])[0]
            error_msg = error_info.get("title", "Unknown error")
            
            cursor.execute(
                """
                UPDATE message_logs 
                SET status = 'failed', error_message = ?
                WHERE message_id = ?
                """,
                (error_msg, message_id)
            )
        
        conn.commit()
    except Exception as e:
        logger.error(f"Error updating message status: {e}")
    finally:
        conn.close()


# =============================================================================
# INCOMING MESSAGE HANDLER
# =============================================================================


def _handle_incoming_message(message: dict, contacts: list):
    """
    Handle an incoming message from a tenant.
    
    Example message object:
    {
        "from": "521234567890",
        "id": "wamid.xxx",
        "timestamp": "1703875200",
        "type": "text",
        "text": {"body": "Ya pagué"}
    }
    """
    wa_message_id = message.get("id")
    from_phone = message.get("from")
    timestamp = message.get("timestamp")
    msg_type = message.get("type", "unknown")
    
    if not wa_message_id or not from_phone:
        return
    
    logger.info(f"Incoming message from {from_phone}: type={msg_type}")
    
    # Extract message body based on type
    message_body = None
    media_id = None
    
    if msg_type == "text":
        message_body = message.get("text", {}).get("body", "")
    elif msg_type == "image":
        media_id = message.get("image", {}).get("id")
        message_body = message.get("image", {}).get("caption", "[Imagen]")
    elif msg_type == "audio":
        media_id = message.get("audio", {}).get("id")
        message_body = "[Audio]"
    elif msg_type == "document":
        media_id = message.get("document", {}).get("id")
        message_body = message.get("document", {}).get("filename", "[Documento]")
    elif msg_type == "video":
        media_id = message.get("video", {}).get("id")
        message_body = "[Video]"
    elif msg_type == "sticker":
        message_body = "[Sticker]"
    elif msg_type == "location":
        loc = message.get("location", {})
        message_body = f"[Ubicación: {loc.get('latitude')}, {loc.get('longitude')}]"
    elif msg_type == "button":
        message_body = message.get("button", {}).get("text", "[Botón]")
    elif msg_type == "interactive":
        interactive = message.get("interactive", {})
        if interactive.get("type") == "button_reply":
            message_body = interactive.get("button_reply", {}).get("title", "[Respuesta]")
        elif interactive.get("type") == "list_reply":
            message_body = interactive.get("list_reply", {}).get("title", "[Selección]")
    else:
        message_body = f"[{msg_type}]"
    
    # Convert Unix timestamp to ISO format
    if timestamp:
        try:
            dt = datetime.fromtimestamp(int(timestamp))
            timestamp_iso = dt.isoformat()
        except (ValueError, TypeError):
            timestamp_iso = datetime.now().isoformat()
    else:
        timestamp_iso = datetime.now().isoformat()
    
    # Try to match phone to a tenant
    tenant_id = _match_phone_to_tenant(from_phone)
    
    # Get contact name if available
    contact_name = None
    if contacts:
        contact_name = contacts[0].get("profile", {}).get("name")
    
    # Store the incoming message
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """
            INSERT INTO incoming_messages 
            (wa_message_id, from_phone, tenant_id, message_type, message_body, 
             media_id, timestamp, received_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(wa_message_id) DO NOTHING
            """,
            (
                wa_message_id,
                from_phone,
                tenant_id,
                msg_type,
                message_body,
                media_id,
                timestamp_iso,
                datetime.now().isoformat(),
            )
        )
        conn.commit()
        
        if tenant_id:
            logger.info(f"Message stored from tenant {tenant_id}: {message_body[:50] if message_body else '[empty]'}")
        else:
            logger.info(f"Message stored from unknown phone {from_phone}: {message_body[:50] if message_body else '[empty]'}")
            
    except Exception as e:
        logger.error(f"Error storing incoming message: {e}")
    finally:
        conn.close()


def _match_phone_to_tenant(phone: str) -> str | None:
    """
    Try to match an incoming phone number to a tenant.
    
    Phone numbers can come in various formats:
    - 521234567890 (no +)
    - +521234567890 (with +)
    - WhatsApp may strip the + sign
    
    Returns tenant_id if found, None otherwise.
    """
    # Normalize phone: remove all non-digits
    normalized = re.sub(r"\D", "", phone)
    
    tenants = get_all_tenants()
    
    for tenant in tenants:
        if not tenant.phone:
            continue
        
        tenant_phone = re.sub(r"\D", "", tenant.phone)
        
        # Check if they match (could be with or without country code)
        if normalized == tenant_phone:
            return tenant.id
        
        # Also try matching last 10 digits (local number)
        if len(normalized) >= 10 and len(tenant_phone) >= 10:
            if normalized[-10:] == tenant_phone[-10:]:
                return tenant.id
    
    return None


# =============================================================================
# SIGNATURE VERIFICATION
# =============================================================================


def _verify_signature(req) -> bool:
    """
    Verify the X-Hub-Signature-256 header from Meta.
    
    This ensures the request actually came from Meta and wasn't spoofed.
    
    Set WHATSAPP_APP_SECRET in your .env file.
    """
    app_secret = os.getenv("WHATSAPP_APP_SECRET", "")
    
    if not app_secret:
        # If no secret configured, skip verification (not recommended for production)
        logger.warning("WHATSAPP_APP_SECRET not configured - skipping signature verification")
        return True
    
    signature = req.headers.get("X-Hub-Signature-256", "")
    
    if not signature:
        return False
    
    # Signature format: "sha256=xxxxx"
    if not signature.startswith("sha256="):
        return False
    
    expected_signature = signature[7:]  # Remove "sha256=" prefix
    
    # Calculate expected signature
    payload = req.get_data()
    calculated = hmac.new(
        app_secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, calculated)


# =============================================================================
# API ENDPOINTS FOR UI
# =============================================================================


@webhook_bp.route("/api/messages/incoming")
def get_incoming_messages():
    """
    API: Get incoming messages (tenant replies).
    
    Query params:
    - unread_only: If "true", only return unread messages
    - tenant_id: Filter by specific tenant
    - limit: Max number of messages (default 50)
    """
    unread_only = request.args.get("unread_only", "false").lower() == "true"
    tenant_id = request.args.get("tenant_id")
    limit = min(int(request.args.get("limit", 50)), 100)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT im.*, t.name as tenant_name, t.property_name, t.unit
        FROM incoming_messages im
        LEFT JOIN tenants t ON im.tenant_id = t.id
        WHERE 1=1
    """
    params = []
    
    if unread_only:
        query += " AND im.read_by_user = 0"
    
    if tenant_id:
        query += " AND im.tenant_id = ?"
        params.append(tenant_id)
    
    query += " ORDER BY im.received_at DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    
    messages = []
    for row in cursor.fetchall():
        messages.append({
            "id": row["id"],
            "wa_message_id": row["wa_message_id"],
            "from_phone": row["from_phone"],
            "tenant_id": row["tenant_id"],
            "tenant_name": row["tenant_name"],
            "property_name": row["property_name"],
            "unit": row["unit"],
            "message_type": row["message_type"],
            "message_body": row["message_body"],
            "timestamp": row["timestamp"],
            "received_at": row["received_at"],
            "read_by_user": bool(row["read_by_user"]),
        })
    
    # Get unread count
    cursor.execute("SELECT COUNT(*) FROM incoming_messages WHERE read_by_user = 0")
    unread_count = cursor.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        "success": True,
        "messages": messages,
        "unread_count": unread_count,
    })


@webhook_bp.route("/api/messages/incoming/<int:message_id>/read", methods=["POST"])
def mark_message_read(message_id: int):
    """Mark an incoming message as read."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE incoming_messages SET read_by_user = 1 WHERE id = ?",
        (message_id,)
    )
    
    conn.commit()
    conn.close()
    
    return jsonify({"success": True})


@webhook_bp.route("/api/messages/status/<message_id>")
def get_message_status(message_id: str):
    """Get the delivery status of a specific message."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """
        SELECT tenant_id, message_type, status, sent_at, delivered_at, read_at, error_message
        FROM message_logs
        WHERE message_id = ?
        """,
        (message_id,)
    )
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return jsonify({"success": False, "error": "Message not found"}), 404
    
    return jsonify({
        "success": True,
        "status": {
            "tenant_id": row["tenant_id"],
            "message_type": row["message_type"],
            "status": row["status"],
            "sent_at": row["sent_at"],
            "delivered_at": row["delivered_at"],
            "read_at": row["read_at"],
            "error_message": row["error_message"],
        }
    })

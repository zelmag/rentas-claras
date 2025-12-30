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
import json
import logging
import os
import re
import traceback
from datetime import datetime

from database import get_all_tenants, get_db_connection

from flask import Blueprint, jsonify, request

# Configure logging with more detail
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


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
        logger.warning(
            f"Webhook verification failed. Mode: {mode}, Token match: {token == verify_token}"
        )
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
    logger.info("\n" + "#"*60)
    logger.info("# WEBHOOK POST REQUEST RECEIVED")
    logger.info("#"*60)
    
    # Verify signature (optional but recommended for security)
    if not _verify_signature(request):
        logger.warning("Invalid webhook signature")
        return "Invalid signature", 401

    try:
        data = request.get_json()
        
        # Log the raw payload for debugging
        logger.debug(f"Raw webhook payload: {json.dumps(data, indent=2)}")

        if not data:
            logger.info("Empty webhook payload - ignoring")
            return "OK", 200

        # Process each entry
        entries = data.get("entry", [])
        logger.info(f"Processing {len(entries)} entries")
        
        for entry in entries:
            changes = entry.get("changes", [])
            logger.info(f"Entry has {len(changes)} changes")
            
            for change in changes:
                field = change.get("field")
                logger.info(f"Change field: {field}")
                
                if field == "messages":
                    value = change.get("value", {})

                    # Handle status updates (delivery receipts)
                    statuses = value.get("statuses", [])
                    if statuses:
                        logger.info(f"Found {len(statuses)} status updates")
                    for status in statuses:
                        _handle_status_update(status)

                    # Handle incoming messages
                    messages = value.get("messages", [])
                    if messages:
                        logger.info(f"Found {len(messages)} incoming messages")
                    for message in messages:
                        _handle_incoming_message(message, value.get("contacts", []))
                else:
                    logger.info(f"Ignoring non-messages field: {field}")

        logger.info("Webhook processing complete - returning 200 OK")
        return "OK", 200

    except Exception as e:
        logger.error(f"❌ Webhook processing error: {str(e)}")
        logger.error(traceback.format_exc())
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
    recipient_id = status.get("recipient_id")

    # Enhanced logging for debugging
    logger.info("="*60)
    logger.info(f"📬 STATUS UPDATE RECEIVED")
    logger.info(f"   Message ID: {message_id}")
    logger.info(f"   Status: {status_value}")
    logger.info(f"   Recipient: {recipient_id}")
    logger.info(f"   Timestamp: {timestamp}")
    logger.info(f"   Full status object: {json.dumps(status, indent=2)}")
    logger.info("="*60)

    if not message_id or not status_value:
        logger.warning(f"Missing message_id or status_value - skipping")
        return

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
        rows_affected = 0
        
        if status_value == "delivered":
            cursor.execute(
                """
                UPDATE message_logs 
                SET status = 'delivered', delivered_at = ?
                WHERE message_id = ? AND status = 'sent'
                """,
                (timestamp_iso, message_id),
            )
            rows_affected = cursor.rowcount
            logger.info(f"✓ DELIVERED update: {rows_affected} rows affected for message_id={message_id}")
            
        elif status_value == "read":
            cursor.execute(
                """
                UPDATE message_logs 
                SET status = 'read', read_at = ?
                WHERE message_id = ? AND status IN ('sent', 'delivered')
                """,
                (timestamp_iso, message_id),
            )
            rows_affected = cursor.rowcount
            logger.info(f"👁️ READ update: {rows_affected} rows affected for message_id={message_id}")
            
        elif status_value == "failed":
            error_info = status.get("errors", [{}])[0]
            error_msg = error_info.get("title", "Unknown error")
            error_code = error_info.get("code")
            error_details = error_info.get("error_data", {})

            logger.error(f"❌ MESSAGE FAILED: {error_msg}")
            logger.error(f"   Error code: {error_code}")
            logger.error(f"   Error details: {json.dumps(error_details, indent=2)}")

            cursor.execute(
                """
                UPDATE message_logs 
                SET status = 'failed', error_message = ?
                WHERE message_id = ?
                """,
                (error_msg, message_id),
            )
            rows_affected = cursor.rowcount
            
        elif status_value == "sent":
            logger.info(f"✓ Message confirmed SENT by WhatsApp")
            rows_affected = 0  # No DB update needed for 'sent' (already logged)

        conn.commit()
        
        # Bug #4 fix: If no rows were updated, try matching by recipient phone as fallback
        if rows_affected == 0 and status_value in ["delivered", "read"] and recipient_id:
            logger.warning(f"⚠️ No rows updated for message_id={message_id}. Attempting fallback by recipient phone...")
            
            # Determine which statuses to look for based on the status update we're applying
            # For "delivered" status: look for "sent" records
            # For "read" status: look for "sent" OR "delivered" records (it might have been updated already)
            if status_value == "delivered":
                status_filter = "ml.status = 'sent'"
            else:  # read
                status_filter = "ml.status IN ('sent', 'delivered')"
            
            # Try to find the most recent message to this phone number that can be updated
            cursor.execute(
                f"""
                SELECT ml.id, ml.message_id, ml.tenant_id, ml.status, t.phone
                FROM message_logs ml
                LEFT JOIN tenants t ON ml.tenant_id = t.id
                WHERE (t.phone LIKE ? OR t.phone LIKE ?)
                  AND {status_filter}
                  AND date(ml.sent_at) = date('now')
                ORDER BY ml.sent_at DESC
                LIMIT 1
                """,
                (f"%{recipient_id[-10:]}", f"%{recipient_id}"),
            )
            fallback_row = cursor.fetchone()
            
            if fallback_row:
                logger.info(f"   Found fallback match: log_id={fallback_row['id']}, tenant={fallback_row['tenant_id']}, current_status={fallback_row['status']}")
                
                # Update this record with the message_id and new status
                if status_value == "delivered":
                    cursor.execute(
                        """
                        UPDATE message_logs 
                        SET status = 'delivered', delivered_at = ?, message_id = ?
                        WHERE id = ?
                        """,
                        (timestamp_iso, message_id, fallback_row['id']),
                    )
                elif status_value == "read":
                    cursor.execute(
                        """
                        UPDATE message_logs 
                        SET status = 'read', read_at = ?, message_id = ?
                        WHERE id = ?
                        """,
                        (timestamp_iso, message_id, fallback_row['id']),
                    )
                
                conn.commit()
                logger.info(f"   ✓ Fallback update successful! Updated from {fallback_row['status']} to {status_value}")
            else:
                logger.warning(f"   No fallback match found for recipient {recipient_id}")
                # Log what's in the database for debugging
                cursor.execute("SELECT message_id, status, tenant_id FROM message_logs ORDER BY sent_at DESC LIMIT 5")
                recent = cursor.fetchall()
                logger.info(f"   Recent messages in DB: {[dict(r) for r in recent]}")
                
    except Exception as e:
        logger.error(f"Error updating message status: {e}")
        logger.error(traceback.format_exc())
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

    # Enhanced logging for incoming messages
    logger.info("="*60)
    logger.info(f"💬 INCOMING MESSAGE RECEIVED")
    logger.info(f"   From: {from_phone}")
    logger.info(f"   Message ID: {wa_message_id}")
    logger.info(f"   Type: {msg_type}")
    logger.info(f"   Contacts: {json.dumps(contacts, indent=2)}")
    logger.info(f"   Full message: {json.dumps(message, indent=2)}")
    logger.info("="*60)

    if not wa_message_id or not from_phone:
        logger.warning(f"Missing wa_message_id or from_phone - skipping")
        return

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
            message_body = interactive.get("button_reply", {}).get(
                "title", "[Respuesta]"
            )
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
        # Bug #10 fix: Validate that incoming_messages table exists and has correct schema
        cursor.execute(
            """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='incoming_messages'
            """
        )
        if not cursor.fetchone():
            logger.warning("📋 incoming_messages table doesn't exist - creating it now")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS incoming_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wa_message_id TEXT UNIQUE,
                    from_phone TEXT NOT NULL,
                    tenant_id TEXT,
                    message_type TEXT,
                    message_body TEXT,
                    media_id TEXT,
                    timestamp TEXT,
                    received_at TEXT NOT NULL,
                    read_by_user INTEGER DEFAULT 0,
                    FOREIGN KEY (tenant_id) REFERENCES tenants(id)
                )
                """
            )
            conn.commit()
            logger.info("✅ incoming_messages table created")

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
            ),
        )
        conn.commit()

        if tenant_id:
            logger.info(f"✅ Message stored successfully!")
            logger.info(f"   Tenant ID: {tenant_id}")
            logger.info(f"   Message: {message_body[:100] if message_body else '[empty]'}")
        else:
            logger.info(f"✅ Message stored (unknown sender)")
            logger.info(f"   Phone: {from_phone}")
            logger.info(f"   Message: {message_body[:100] if message_body else '[empty]'}")
            logger.info(f"   ℹ️ Could not match phone to any tenant. Check tenant phone numbers.")

    except Exception as e:
        logger.error(f"❌ Error storing incoming message: {e}")
        logger.error(traceback.format_exc())
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
        logger.warning(
            "WHATSAPP_APP_SECRET not configured - skipping signature verification"
        )
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
    calculated = hmac.new(app_secret.encode(), payload, hashlib.sha256).hexdigest()

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
        messages.append(
            {
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
            }
        )

    # Get unread count
    cursor.execute("SELECT COUNT(*) FROM incoming_messages WHERE read_by_user = 0")
    unread_count = cursor.fetchone()[0]

    conn.close()

    return jsonify(
        {
            "success": True,
            "messages": messages,
            "unread_count": unread_count,
        }
    )


@webhook_bp.route("/api/messages/incoming/<int:message_id>/read", methods=["POST"])
def mark_message_read(message_id: int):
    """Mark an incoming message as read."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE incoming_messages SET read_by_user = 1 WHERE id = ?", (message_id,)
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
        (message_id,),
    )

    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({"success": False, "error": "Message not found"}), 404

    return jsonify(
        {
            "success": True,
            "status": {
                "tenant_id": row["tenant_id"],
                "message_type": row["message_type"],
                "status": row["status"],
                "sent_at": row["sent_at"],
                "delivered_at": row["delivered_at"],
                "read_at": row["read_at"],
                "error_message": row["error_message"],
            },
        }
    )

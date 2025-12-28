"""
WhatsApp Cloud API Client for RentasClaras
===========================================

Sends rent reminders via Meta's WhatsApp Cloud API.
FREE for first 1,000 messages/month.

Setup: See docs/SETUP_WHATSAPP_API.md

Author: RentasClaras Engineering
Date: December 2024
"""

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import requests


# =============================================================================
# CONFIGURATION
# =============================================================================

WHATSAPP_API_VERSION = "v18.0"
WHATSAPP_API_BASE = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}"

# Load from environment variables
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")

# Template names (must match what you create in Meta Business)
TEMPLATE_RENT_REMINDER = "rent_reminder"
TEMPLATE_RENT_REMINDER_LATE = "rent_reminder_late"


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class WhatsAppResponse:
    """Response from WhatsApp API"""

    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    raw_response: Optional[dict] = None


# =============================================================================
# CORE API FUNCTIONS
# =============================================================================


def _get_headers() -> dict:
    """Get authorization headers for WhatsApp API"""
    return {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }


def _clean_phone_number(phone: str) -> str:
    """
    Clean phone number for WhatsApp API.

    Input formats accepted:
    - +52 81 1234 5678
    - +521234567890
    - 52 81 1234 5678
    - 811234567890

    Output: 521234567890 (country code + number, no + or spaces)
    """
    # Remove all non-digits
    digits = "".join(filter(str.isdigit, phone))

    # If it starts with 52 (Mexico), use as-is
    if digits.startswith("52"):
        return digits

    # If 10 digits (Mexican local), add country code
    if len(digits) == 10:
        return f"52{digits}"

    # If 11 digits starting with 1 (old Mexican mobile format), convert
    if len(digits) == 11 and digits.startswith("1"):
        return f"52{digits}"

    # Return as-is for other countries
    return digits


def send_template_message(
    to_phone: str,
    template_name: str,
    language_code: str = "es_MX",
    parameters: list[str] = None,
) -> WhatsAppResponse:
    """
    Send a template message via WhatsApp Cloud API.

    Args:
        to_phone: Recipient phone number (any format)
        template_name: Name of approved template (e.g., "rent_reminder")
        language_code: Template language (default: Spanish Mexico)
        parameters: List of strings to fill template variables {{1}}, {{2}}, etc.

    Returns:
        WhatsAppResponse with success status and message ID
    """
    if not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        return WhatsAppResponse(
            success=False,
            error="WhatsApp credentials not configured. Set WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID in .env",
        )

    url = f"{WHATSAPP_API_BASE}/{WHATSAPP_PHONE_NUMBER_ID}/messages"

    # Build template components
    components = []
    if parameters:
        body_params = [{"type": "text", "text": str(p)} for p in parameters]
        components.append({"type": "body", "parameters": body_params})

    payload = {
        "messaging_product": "whatsapp",
        "to": _clean_phone_number(to_phone),
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language_code},
        },
    }

    if components:
        payload["template"]["components"] = components

    try:
        response = requests.post(url, headers=_get_headers(), json=payload, timeout=30)
        data = response.json()

        if response.status_code == 200 and "messages" in data:
            return WhatsAppResponse(
                success=True,
                message_id=data["messages"][0].get("id"),
                raw_response=data,
            )
        else:
            error_msg = data.get("error", {}).get("message", "Unknown error")
            return WhatsAppResponse(success=False, error=error_msg, raw_response=data)

    except requests.exceptions.RequestException as e:
        return WhatsAppResponse(success=False, error=f"Network error: {str(e)}")


def send_text_message(to_phone: str, message: str) -> WhatsAppResponse:
    """
    Send a plain text message via WhatsApp Cloud API.

    NOTE: This only works within the 24-hour conversation window.
    For outbound messages to users who haven't messaged you recently,
    use send_template_message() instead.

    Args:
        to_phone: Recipient phone number
        message: Message text (max 4096 characters)

    Returns:
        WhatsAppResponse with success status
    """
    if not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        return WhatsAppResponse(
            success=False, error="WhatsApp credentials not configured"
        )

    url = f"{WHATSAPP_API_BASE}/{WHATSAPP_PHONE_NUMBER_ID}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "to": _clean_phone_number(to_phone),
        "type": "text",
        "text": {"preview_url": False, "body": message[:4096]},  # Max message length
    }

    try:
        response = requests.post(url, headers=_get_headers(), json=payload, timeout=30)
        data = response.json()

        if response.status_code == 200 and "messages" in data:
            return WhatsAppResponse(
                success=True,
                message_id=data["messages"][0].get("id"),
                raw_response=data,
            )
        else:
            error_msg = data.get("error", {}).get("message", "Unknown error")
            return WhatsAppResponse(success=False, error=error_msg, raw_response=data)

    except requests.exceptions.RequestException as e:
        return WhatsAppResponse(success=False, error=f"Network error: {str(e)}")


# =============================================================================
# RENT-SPECIFIC FUNCTIONS
# =============================================================================


def send_rent_reminder(
    to_phone: str, tenant_name: str, month: str, amount: str
) -> WhatsAppResponse:
    """
    Send a rent reminder using the 'rent_reminder' template.

    Template format:
    "Buenos días {{1}}. Espero esté bien. Para recordarle por favor
     del pago de la renta de {{2}}. Total: ${{3}} MXN. Gracias."

    Args:
        to_phone: Tenant's phone number
        tenant_name: Tenant's first name (e.g., "María")
        month: Month name in Spanish (e.g., "enero")
        amount: Rent amount as string (e.g., "3,200")

    Returns:
        WhatsAppResponse
    """
    return send_template_message(
        to_phone=to_phone,
        template_name=TEMPLATE_RENT_REMINDER,
        parameters=[tenant_name, month, amount],
    )


def send_late_reminder(
    to_phone: str, tenant_name: str, month: str, amount: str
) -> WhatsAppResponse:
    """
    Send a late payment reminder using the 'rent_reminder_late' template.

    Template format:
    "Buenas tardes {{1}}. Le recordamos que el pago de renta de {{2}}
     por ${{3}} MXN sigue pendiente. Por favor regularice su situación. Gracias."

    Args:
        to_phone: Tenant's phone number
        tenant_name: Tenant's first name
        month: Month name in Spanish
        amount: Rent amount as string

    Returns:
        WhatsAppResponse
    """
    return send_template_message(
        to_phone=to_phone,
        template_name=TEMPLATE_RENT_REMINDER_LATE,
        parameters=[tenant_name, month, amount],
    )


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def check_credentials() -> dict:
    """
    Check if WhatsApp API credentials are configured.

    Returns:
        Dict with configuration status
    """
    return {
        "configured": bool(WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID),
        "has_token": bool(WHATSAPP_ACCESS_TOKEN),
        "has_phone_id": bool(WHATSAPP_PHONE_NUMBER_ID),
        "token_preview": (
            WHATSAPP_ACCESS_TOKEN[:20] + "..." if WHATSAPP_ACCESS_TOKEN else None
        ),
        "phone_number_id": WHATSAPP_PHONE_NUMBER_ID or None,
    }


def send_test_message(to_phone: str = None) -> WhatsAppResponse:
    """
    Send a test message to verify API configuration.

    Args:
        to_phone: Phone number to send test to (optional, uses env var if not provided)

    Returns:
        WhatsAppResponse
    """
    test_phone = to_phone or os.getenv("WHATSAPP_TEST_PHONE", "")

    if not test_phone:
        return WhatsAppResponse(
            success=False,
            error="No test phone number provided. Set WHATSAPP_TEST_PHONE in .env or pass to_phone parameter.",
        )

    return send_rent_reminder(
        to_phone=test_phone, tenant_name="Prueba", month="enero", amount="1,000"
    )


# =============================================================================
# CLI TEST
# =============================================================================

if __name__ == "__main__":
    print("🔧 WhatsApp API Configuration Check")
    print("=" * 50)

    config = check_credentials()

    if config["configured"]:
        print("✅ Credentials configured")
        print(f"   Token: {config['token_preview']}")
        print(f"   Phone Number ID: {config['phone_number_id']}")

        # Optionally send test message
        test_phone = os.getenv("WHATSAPP_TEST_PHONE")
        if test_phone:
            print(f"\n📤 Sending test message to {test_phone}...")
            result = send_test_message(test_phone)
            if result.success:
                print(f"✅ Message sent! ID: {result.message_id}")
            else:
                print(f"❌ Failed: {result.error}")
        else:
            print("\n⚠️  Set WHATSAPP_TEST_PHONE in .env to send a test message")
    else:
        print("❌ Credentials not configured")
        print("   Set WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID in .env")
        print("   See docs/SETUP_WHATSAPP_API.md for instructions")

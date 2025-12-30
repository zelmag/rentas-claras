"""
WhatsApp Cloud API Client for RentasClaras
===========================================

Sends rent reminders via Meta's WhatsApp Cloud API.
FREE for first 1,000 messages/month.

Setup: See docs/SETUP_WHATSAPP_API.md

Author: RentasClaras Engineering
Date: December 2024
"""

import logging
import os
import re
from dataclasses import dataclass
from typing import Optional

import requests

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("WhatsAppClient")


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class WhatsAppResponse:
    """Response from WhatsApp API"""

    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[int] = None
    raw_response: Optional[dict] = None


# =============================================================================
# TEMPLATE CONFIGURATION
# =============================================================================

# Template names (must match what you created in Meta Business)
TEMPLATE_CONFIG = {
    "recordatorio_renta": {
        "param_count": 2,
        "description": "Morning reminder - Day 1",
        "params": ["tenant_name", "amount"],
    },
    "recordatorio_tarde": {
        "param_count": 2,
        "description": "Afternoon reminder - Day 1 (5 PM)",
        "params": ["tenant_name", "amount"],
    },
    "aviso_recargo": {
        "param_count": 3,
        "description": "Late fee notice - Day 2+",
        "params": ["tenant_name", "base_rent", "total_with_fees"],
    },
}


# =============================================================================
# WHATSAPP CLIENT CLASS
# =============================================================================


class WhatsAppClient:
    """
    WhatsApp Cloud API Client for sending rent reminders.

    Usage:
        client = WhatsAppClient()
        response = client.send_rent_reminder(
            to_phone="+52 81 1234 5678",
            tenant_name="María García",
            amount=3200.00
        )
        if response.success:
            print(f"Message sent! ID: {response.message_id}")
        else:
            print(f"Error: {response.error}")
    """

    API_VERSION = "v22.0"
    API_BASE_URL = "https://graph.facebook.com"

    def __init__(
        self,
        access_token: Optional[str] = None,
        phone_number_id: Optional[str] = None,
    ):
        """
        Initialize the WhatsApp client.

        Args:
            access_token: WhatsApp API access token (or set WHATSAPP_ACCESS_TOKEN env var)
            phone_number_id: WhatsApp phone number ID (or set WHATSAPP_PHONE_NUMBER_ID env var)
        """
        self.access_token = access_token or os.getenv("WHATSAPP_ACCESS_TOKEN", "")
        self.phone_number_id = phone_number_id or os.getenv(
            "WHATSAPP_PHONE_NUMBER_ID", ""
        )

        if not self.access_token or not self.phone_number_id:
            logger.warning(
                "WhatsApp credentials not configured. "
                "Set WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID in .env"
            )

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _get_headers(self) -> dict:
        """Get authorization headers for WhatsApp API."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _get_messages_url(self) -> str:
        """Get the messages API endpoint URL."""
        return f"{self.API_BASE_URL}/{self.API_VERSION}/{self.phone_number_id}/messages"

    @staticmethod
    def sanitize_phone_number(phone: str) -> str:
        """
        Sanitize phone number for WhatsApp API.

        Meta requires phone numbers in format: country code + number, no + or spaces.
        Example: 521234567890 (Mexico) or 447811782597 (UK)

        Args:
            phone: Phone number in any format

        Returns:
            Cleaned phone number (digits only, with country code)

        Examples:
            >>> WhatsAppClient.sanitize_phone_number("+52 81 1234 5678")
            "528112345678"
            >>> WhatsAppClient.sanitize_phone_number("+44 7811 782597")
            "447811782597"
        """
        # Remove all non-digits
        digits = re.sub(r"\D", "", phone)

        # Handle Mexican numbers
        if digits.startswith("52"):
            return digits
        # Handle UK numbers
        elif digits.startswith("44"):
            return digits
        # If 10 digits (Mexican local), add country code
        elif len(digits) == 10:
            return f"52{digits}"
        # If 11 digits starting with 1 (old Mexican mobile format)
        elif len(digits) == 11 and digits.startswith("1"):
            return f"52{digits}"

        # Return as-is for other countries
        return digits

    @staticmethod
    def format_currency(amount: float, currency: str = "MXN") -> str:
        """
        Format amount as Mexican Peso currency string.

        Args:
            amount: Numeric amount (int or float)
            currency: Currency code (default: MXN)

        Returns:
            Formatted string like "$3,200.00"

        Examples:
            >>> WhatsAppClient.format_currency(3200)
            "$3,200.00"
            >>> WhatsAppClient.format_currency(1500.50)
            "$1,500.50"
        """
        return f"${amount:,.2f}"

    # =========================================================================
    # CORE API METHOD
    # =========================================================================

    def send_template_message(
        self,
        to_phone: str,
        template_name: str,
        parameters: list[str],
        language_code: str = "es_MX",
    ) -> WhatsAppResponse:
        """
        Send a template message via WhatsApp Cloud API.

        Args:
            to_phone: Recipient phone number (any format)
            template_name: Name of approved template (e.g., "recordatorio_renta")
            parameters: List of strings to fill template variables {{1}}, {{2}}, etc.
            language_code: Template language (default: Spanish Mexico)

        Returns:
            WhatsAppResponse with success status, message_id, and error details
        """
        # Validate credentials
        if not self.access_token or not self.phone_number_id:
            error_msg = (
                "WhatsApp credentials not configured. "
                "Set WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID in .env"
            )
            logger.error(error_msg)
            return WhatsAppResponse(success=False, error=error_msg)

        # Validate template exists in our config
        if template_name not in TEMPLATE_CONFIG:
            logger.warning(
                f"Template '{template_name}' not in TEMPLATE_CONFIG. "
                "Proceeding anyway, but verify it exists in Meta Business."
            )

        # Validate parameter count
        expected_count = TEMPLATE_CONFIG.get(template_name, {}).get("param_count", 0)
        if expected_count and len(parameters) != expected_count:
            logger.warning(
                f"Template '{template_name}' expects {expected_count} parameters, "
                f"but got {len(parameters)}."
            )

        # Build request
        url = self._get_messages_url()
        clean_phone = self.sanitize_phone_number(to_phone)

        # Build template components (body parameters)
        components = []
        if parameters:
            body_params = [{"type": "text", "text": str(p)} for p in parameters]
            components.append({"type": "body", "parameters": body_params})

        payload = {
            "messaging_product": "whatsapp",
            "to": clean_phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
            },
        }

        if components:
            payload["template"]["components"] = components

        # Log the request (without sensitive token)
        logger.info(
            f"Sending WhatsApp message: template={template_name}, to={clean_phone}"
        )
        logger.debug(f"Payload: {payload}")

        # Make API request
        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=30,
            )
            data = response.json()

            # Handle success
            if response.status_code == 200 and "messages" in data:
                message_id = data["messages"][0].get("id")
                logger.info(f"Message sent successfully! ID: {message_id}")
                return WhatsAppResponse(
                    success=True,
                    message_id=message_id,
                    raw_response=data,
                )

            # Handle API errors (400, 401, etc.)
            error_data = data.get("error", {})
            error_message = error_data.get("message", "Unknown error")
            error_code = error_data.get("code")
            error_subcode = error_data.get("error_subcode")

            # Log detailed error for debugging
            logger.error(
                f"WhatsApp API Error: {error_message} "
                f"(code={error_code}, subcode={error_subcode})"
            )
            logger.error(f"Full response: {data}")

            return WhatsAppResponse(
                success=False,
                error=error_message,
                error_code=error_code,
                raw_response=data,
            )

        except requests.exceptions.Timeout:
            error_msg = "Request timed out after 30 seconds"
            logger.error(error_msg)
            return WhatsAppResponse(success=False, error=error_msg)

        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error: {str(e)}"
            logger.error(error_msg)
            return WhatsAppResponse(success=False, error=error_msg)

        except requests.exceptions.RequestException as e:
            error_msg = f"Network error: {str(e)}"
            logger.error(error_msg)
            return WhatsAppResponse(success=False, error=error_msg)

        except ValueError as e:
            error_msg = f"Invalid JSON response: {str(e)}"
            logger.error(error_msg)
            return WhatsAppResponse(success=False, error=error_msg)

    # =========================================================================
    # RENT-SPECIFIC CONVENIENCE METHODS
    # =========================================================================

    def send_rent_reminder(
        self,
        to_phone: str,
        tenant_name: str,
        amount: float,
    ) -> WhatsAppResponse:
        """
        Send morning rent reminder using 'recordatorio_renta' template.

        Template: "Buenos días {{1}}. Espero esté bien. Le recordamos
                  amablemente el pago de su renta. Monto pendiente: {{2}}.
                  Agradecemos su atención."

        Args:
            to_phone: Tenant's phone number
            tenant_name: Tenant's name (e.g., "María García")
            amount: Rent amount as number (e.g., 3200.00)

        Returns:
            WhatsAppResponse
        """
        formatted_amount = self.format_currency(amount)
        return self.send_template_message(
            to_phone=to_phone,
            template_name="recordatorio_renta",
            parameters=[tenant_name, formatted_amount],
        )

    def send_afternoon_reminder(
        self,
        to_phone: str,
        tenant_name: str,
        amount: float,
    ) -> WhatsAppResponse:
        """
        Send afternoon rent reminder using 'recordatorio_tarde' template.

        Template: "Buenas tardes {{1}}. Le recordamos que el pago de su
                  renta por {{2}} sigue pendiente. Le pedimos realizar
                  el pago hoy de ser posible. Gracias por su atención."

        Args:
            to_phone: Tenant's phone number
            tenant_name: Tenant's name
            amount: Rent amount as number

        Returns:
            WhatsAppResponse
        """
        formatted_amount = self.format_currency(amount)
        return self.send_template_message(
            to_phone=to_phone,
            template_name="recordatorio_tarde",
            parameters=[tenant_name, formatted_amount],
        )

    def send_late_fee_notice(
        self,
        to_phone: str,
        tenant_name: str,
        base_rent: float,
        total_with_fees: float,
    ) -> WhatsAppResponse:
        """
        Send late fee notice using 'aviso_recargo' template.

        Template: "Buen día {{1}}. Le informamos que su renta de {{2}}
                  continúa pendiente y a partir de hoy aplica un recargo.
                  Total a pagar: {{3}}. Le pedimos regularizar su situación
                  lo antes posible. Gracias."

        Args:
            to_phone: Tenant's phone number
            tenant_name: Tenant's name
            base_rent: Original rent amount
            total_with_fees: Total including late fees

        Returns:
            WhatsAppResponse
        """
        formatted_base = self.format_currency(base_rent)
        formatted_total = self.format_currency(total_with_fees)
        return self.send_template_message(
            to_phone=to_phone,
            template_name="aviso_recargo",
            parameters=[tenant_name, formatted_base, formatted_total],
        )

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def check_credentials(self) -> dict:
        """
        Check if WhatsApp API credentials are configured.

        Returns:
            Dict with configuration status
        """
        return {
            "configured": bool(self.access_token and self.phone_number_id),
            "has_token": bool(self.access_token),
            "has_phone_id": bool(self.phone_number_id),
            "token_preview": (
                self.access_token[:20] + "..." if self.access_token else None
            ),
            "phone_number_id": self.phone_number_id or None,
            "api_version": self.API_VERSION,
        }

    def get_template_status(self, business_account_id: Optional[str] = None) -> dict:
        """
        Get the status of all message templates.

        Args:
            business_account_id: WhatsApp Business Account ID
                (or set WHATSAPP_BUSINESS_ACCOUNT_ID env var)

        Returns:
            Dict with templates and their statuses

        Status values:
            - APPROVED: Ready to use
            - PENDING: Under review (usually 24-48 hours)
            - REJECTED: Rejected, check rejection reason
        """
        waba_id = business_account_id or os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID", "")

        if not waba_id:
            return {
                "success": False,
                "error": "WHATSAPP_BUSINESS_ACCOUNT_ID not configured in .env",
            }

        if not self.access_token:
            return {
                "success": False,
                "error": "WHATSAPP_ACCESS_TOKEN not configured in .env",
            }

        url = f"{self.API_BASE_URL}/{self.API_VERSION}/{waba_id}/message_templates"

        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=30,
            )
            data = response.json()

            if response.status_code == 200 and "data" in data:
                templates = []
                for t in data["data"]:
                    templates.append(
                        {
                            "name": t.get("name"),
                            "status": t.get("status"),
                            "category": t.get("category"),
                            "language": t.get("language"),
                            "rejected_reason": t.get("rejected_reason"),
                        }
                    )

                logger.info(f"Retrieved {len(templates)} templates")
                return {
                    "success": True,
                    "templates": templates,
                }

            error_data = data.get("error", {})
            return {
                "success": False,
                "error": error_data.get("message", "Unknown error"),
                "raw_response": data,
            }

        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e),
            }

    def send_test_message(self, to_phone: str) -> WhatsAppResponse:
        """
        Send a test rent reminder to verify API configuration.

        Args:
            to_phone: Phone number to send test to

        Returns:
            WhatsAppResponse
        """
        return self.send_rent_reminder(
            to_phone=to_phone,
            tenant_name="Prueba",
            amount=1000.00,
        )


# =============================================================================
# STANDALONE FUNCTIONS (for backward compatibility)
# =============================================================================

# Create a default client instance
_default_client = None


def _get_default_client() -> WhatsAppClient:
    """Get or create the default WhatsApp client."""
    global _default_client
    if _default_client is None:
        _default_client = WhatsAppClient()
    return _default_client


def send_template_message(
    to_phone: str,
    template_name: str,
    language_code: str = "es_MX",
    parameters: list[str] = None,
) -> WhatsAppResponse:
    """
    Send a template message via WhatsApp Cloud API.
    (Backward compatible function - uses default client)
    """
    return _get_default_client().send_template_message(
        to_phone=to_phone,
        template_name=template_name,
        parameters=parameters or [],
        language_code=language_code,
    )


def send_rent_reminder(
    to_phone: str, tenant_name: str, month: str, amount: str
) -> WhatsAppResponse:
    """
    Send a rent reminder. (Backward compatible function)
    Note: 'month' parameter is ignored in new templates.
    """
    # Convert amount string to float if needed
    try:
        amount_float = float(amount.replace(",", "").replace("$", ""))
    except (ValueError, AttributeError):
        amount_float = 0.0

    return _get_default_client().send_rent_reminder(
        to_phone=to_phone,
        tenant_name=tenant_name,
        amount=amount_float,
    )


def send_late_reminder(
    to_phone: str, tenant_name: str, month: str, amount: str
) -> WhatsAppResponse:
    """
    Send a late payment reminder using 'aviso_recargo' template.
    (Backward compatible function for scheduler)

    Note: 'month' parameter is ignored in new templates.
    Uses the same amount for base_rent and total since the amount
    passed already includes late fees.
    """
    # Convert amount string to float if needed
    try:
        amount_float = float(amount.replace(",", "").replace("$", ""))
    except (ValueError, AttributeError):
        amount_float = 0.0

    return _get_default_client().send_late_fee_notice(
        to_phone=to_phone,
        tenant_name=tenant_name,
        base_rent=amount_float,
        total_with_fees=amount_float,
    )


def check_credentials() -> dict:
    """Check if WhatsApp API credentials are configured."""
    return _get_default_client().check_credentials()


def send_test_message(to_phone: str = None) -> WhatsAppResponse:
    """Send a test message to verify API configuration."""
    test_phone = to_phone or os.getenv("WHATSAPP_TEST_PHONE", "")
    if not test_phone:
        return WhatsAppResponse(
            success=False,
            error="No test phone number provided. Set WHATSAPP_TEST_PHONE in .env",
        )
    return _get_default_client().send_test_message(to_phone=test_phone)


# =============================================================================
# CLI TEST
# =============================================================================

if __name__ == "__main__":
    print("🔧 WhatsApp API Configuration Check")
    print("=" * 50)

    client = WhatsAppClient()
    config = client.check_credentials()

    if config["configured"]:
        print("✅ Credentials configured")
        print(f"   API Version: {config['api_version']}")
        print(f"   Token: {config['token_preview']}")
        print(f"   Phone Number ID: {config['phone_number_id']}")

        # List available templates
        print("\n📋 Available Templates:")
        for name, info in TEMPLATE_CONFIG.items():
            print(f"   • {name}: {info['description']} ({info['param_count']} params)")

        # Optionally send test message
        test_phone = os.getenv("WHATSAPP_TEST_PHONE")
        if test_phone:
            print(f"\n📤 Sending test message to {test_phone}...")
            result = client.send_test_message(test_phone)
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

"""
Message Generation Services
============================

Utilities for generating rent reminder messages and WhatsApp links.
"""

import urllib.parse
from typing import Protocol


# =============================================================================
# TYPES
# =============================================================================

class TenantLike(Protocol):
    """Protocol for tenant-like objects with name and rent."""
    name: str
    rent: float


# =============================================================================
# MESSAGE GENERATION
# =============================================================================

def generate_rent_reminder(
    display_name: str,
    month_name: str,
    amount: float,
) -> str:
    """
    Generate a rent reminder message in professional Regio Spanish.

    Args:
        display_name: The tenant's display name (already processed)
        month_name: Spanish month name (e.g., "enero", "febrero")
        amount: Rent amount in MXN

    Returns:
        Formatted rent reminder message
    """
    message = (
        f"Buenos días {display_name}. Espero esté bien. "
        f"Para recordarle por favor del pago de la renta de {month_name}. "
        f"Total: ${amount:,.0f} MXN."
    )
    return message


def generate_late_payment_reminder(
    display_name: str,
    month_name: str,
    amount: float,
    late_fee: float,
    days_late: int,
) -> str:
    """
    Generate a late payment reminder with fee information.

    Args:
        display_name: The tenant's display name
        month_name: Spanish month name
        amount: Original rent amount in MXN
        late_fee: Late fee amount in MXN
        days_late: Number of days late

    Returns:
        Formatted late payment reminder message
    """
    total = amount + late_fee
    message = (
        f"Buenos días {display_name}. Espero esté bien. "
        f"Le recordamos que el pago de la renta de {month_name} está pendiente. "
        f"Renta: ${amount:,.0f} MXN + Recargo: ${late_fee:,.0f} MXN = "
        f"Total: ${total:,.0f} MXN. "
        f"({days_late} días de retraso)"
    )
    return message


# =============================================================================
# WHATSAPP UTILITIES
# =============================================================================

def create_whatsapp_link(phone: str, message: str) -> str:
    """
    Create a WhatsApp click-to-chat URL.

    Args:
        phone: Phone number (can include +, spaces, dashes)
        message: Message text to pre-fill

    Returns:
        WhatsApp wa.me URL with encoded message
    """
    # Clean phone number - remove common formatting characters
    clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")
    encoded_message = urllib.parse.quote(message)
    return f"https://wa.me/{clean_phone}?text={encoded_message}"


def format_phone_for_display(phone: str) -> str:
    """
    Format phone number for display (e.g., +52 81 1234 5678).

    Args:
        phone: Raw phone number

    Returns:
        Formatted phone number for display
    """
    clean = phone.replace("+", "").replace(" ", "").replace("-", "")

    # Mexican mobile format: +52 followed by 10 digits
    if len(clean) == 12 and clean.startswith("52"):
        return f"+52 {clean[2:4]} {clean[4:8]} {clean[8:]}"
    elif len(clean) == 10:
        return f"+52 {clean[:2]} {clean[2:6]} {clean[6:]}"

    # Return as-is if format is unknown
    return phone

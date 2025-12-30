"""
Date Formatting Services
========================

Utilities for parsing and formatting dates in Spanish.
Used by pagos and contratos routes.

This is the SINGLE SOURCE OF TRUTH for:
- Spanish month names
- Spanish days of week
- Billing month calculation
"""

from datetime import datetime
from typing import Optional


# =============================================================================
# CONSTANTS - Single Source of Truth for Spanish date names
# =============================================================================

SPANISH_MONTHS = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]

SPANISH_MONTHS_CAPITALIZED = [
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
]

SPANISH_DAYS_OF_WEEK = [
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
    "sábado",
    "domingo",
]

SPANISH_MONTH_TO_NUM = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


# =============================================================================
# BILLING MONTH CONSTANTS (Single Source of Truth)
# =============================================================================

# Minimum supported date (when our data starts)
# IMPORTANT: This is the single source of truth - import from here in all modules
MIN_BILLING_YEAR = 2025
MIN_BILLING_MONTH = 1


# =============================================================================
# PARSING FUNCTIONS
# =============================================================================


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parse date string in various formats.

    Supports:
    - ISO format: "2025-12-31"
    - European format: "31/12/2025"

    Args:
        date_str: Date string to parse

    Returns:
        datetime object or None if parsing fails
    """
    if not date_str:
        return None

    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        try:
            return datetime.strptime(date_str, "%d/%m/%Y")
        except (ValueError, TypeError):
            return None


def parse_spanish_month_year(month_str: str) -> datetime:
    """
    Parse 'Enero 2025' or 'enero 2025' to datetime for sorting.

    Args:
        month_str: Spanish month and year string (e.g., "Enero 2025")

    Returns:
        datetime object (first day of that month), or datetime.max if parsing fails
    """
    try:
        parts = month_str.split()
        month_num = SPANISH_MONTH_TO_NUM.get(parts[0].lower(), 1)
        year = int(parts[1])
        return datetime(year, month_num, 1)
    except (IndexError, ValueError):
        return datetime.max


# =============================================================================
# FORMATTING FUNCTIONS
# =============================================================================


def format_date_spanish(date_str: Optional[str]) -> Optional[str]:
    """
    Format date as '12 de enero 2025'.

    Args:
        date_str: Date string in ISO or European format

    Returns:
        Spanish formatted date string, or original if parsing fails
    """
    parsed = parse_date(date_str)
    if parsed:
        return f"{parsed.day} de {SPANISH_MONTHS[parsed.month - 1]} {parsed.year}"
    return date_str


def format_date_excel(date_str: Optional[str]) -> Optional[str]:
    """
    Format date as M/D/YYYY for Excel-style display.

    Args:
        date_str: Date string in ISO or European format

    Returns:
        Excel formatted date string, or original if parsing fails
    """
    parsed = parse_date(date_str)
    if parsed:
        return f"{parsed.month}/{parsed.day}/{parsed.year}"
    return date_str


def get_month_name(month: int, capitalize: bool = False) -> str:
    """
    Get Spanish month name by number (1-12).

    Args:
        month: Month number (1-12)
        capitalize: If True, return capitalized version

    Returns:
        Spanish month name
    """
    if 1 <= month <= 12:
        if capitalize:
            return SPANISH_MONTHS_CAPITALIZED[month - 1]
        return SPANISH_MONTHS[month - 1]
    return ""


# =============================================================================
# BILLING MONTH (Single Source of Truth for "current month" across all pages)
# =============================================================================


def get_billing_month(
    reference_date: Optional[datetime] = None,
) -> tuple[int, int, str]:
    """
    Get the current billing month/year for payment tracking.

    This is the SINGLE SOURCE OF TRUTH for determining which month
    payments should be tracked for. All pages (pagos, dashboard, contratos,
    state API) should use this function.

    Rules:
    - After day 7 of any month, auto-switch to NEXT month
    - Minimum supported date is January 2025 (when our data starts)

    Args:
        reference_date: Optional datetime to use instead of now (for testing)

    Returns:
        Tuple of (year, month, month_name_spanish)

    Examples:
        - Dec 29, 2025 → (2026, 1, "enero") [after day 7, switches to Jan 2026]
        - Jan 5, 2026 → (2026, 1, "enero") [before day 7, stays on Jan]
        - Jan 10, 2026 → (2026, 2, "febrero") [after day 7, switches to Feb]
    """
    today = reference_date or datetime.now()

    # Start with current date
    year = today.year
    month = today.month

    # AUTO-SWITCH: After day 7, move to next month
    if today.day > 7:
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1

    # CLAMP: Ensure we don't go below minimum supported date
    if year < MIN_BILLING_YEAR:
        year = MIN_BILLING_YEAR
        month = MIN_BILLING_MONTH
    elif year == MIN_BILLING_YEAR and month < MIN_BILLING_MONTH:
        month = MIN_BILLING_MONTH

    month_name = SPANISH_MONTHS[month - 1]

    return (year, month, month_name)


def calculate_relative_time(timestamp: Optional[str]) -> Optional[str]:
    """
    Calculate relative time string from ISO timestamp.

    Args:
        timestamp: ISO format timestamp string

    Returns:
        Spanish relative time string (e.g., "hace 5 minutos")
    """
    if not timestamp:
        return None

    try:
        sync_dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        diff = datetime.now() - sync_dt.replace(tzinfo=None)
        seconds = diff.total_seconds()

        if seconds < 60:
            return "hace unos segundos"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"hace {minutes} minuto{'s' if minutes != 1 else ''}"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"hace {hours} hora{'s' if hours != 1 else ''}"
        else:
            days = int(seconds / 86400)
            return f"hace {days} día{'s' if days != 1 else ''}"
    except Exception:
        return timestamp[:16] if timestamp else None

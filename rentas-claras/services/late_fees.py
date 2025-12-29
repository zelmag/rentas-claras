"""
Late Fee Calculation Services
==============================

This module re-exports from src/late_fees.py (the comprehensive version)
and provides backward-compatible wrapper functions.

Source of truth: src/late_fees.py
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

# =============================================================================
# RE-EXPORTS FROM src/late_fees.py (comprehensive version)
# =============================================================================

from src.late_fees import (
    # Constants
    INITIAL_PENALTY_MXN,
    DAILY_PENALTY_MXN,
    MAX_DAILY_PENALTY_DAYS,
    TERMINATION_WARNING_DAY,
    # Enums
    PaymentStatus,
    PropertyType,
    # Dataclasses
    LateFeeResult,
    PropertyConfig,
    PropertySubtotal,
    GrandTotal,
    # Property configurations
    PROPERTIES,
    # Core functions
    calculate_rentas_claras_balance,
    calculate_tenant_utilities,
    calculate_property_subtotal,
    calculate_grand_total,
    # Formatting functions
    format_property_subtotal,
    format_grand_total,
    # Message generation
    generate_payment_request_message,
    generate_reminder_message,
)

# =============================================================================
# BACKWARD-COMPATIBLE CONSTANTS (for any code using the old names)
# =============================================================================

INITIAL_PENALTY = int(INITIAL_PENALTY_MXN)  # 500
DAILY_PENALTY = int(DAILY_PENALTY_MXN)      # 100


# =============================================================================
# BACKWARD-COMPATIBLE WRAPPER FUNCTIONS
# =============================================================================

def calculate_late_fee(days_late: int) -> float:
    """
    Calculate the late fee based on days late.
    
    BACKWARD COMPATIBILITY WRAPPER.
    Prefer using calculate_rentas_claras_balance() for new code.

    Args:
        days_late: Number of days past the due date (day 1)

    Returns:
        Late fee amount in MXN (float)

    Examples:
        days_late=0: $0 (on time)
        days_late=1: $500 (day 2)
        days_late=2: $600 (day 3)
        days_late=5: $900 (day 6)
        days_late=6+: $1,000 (capped)
    """
    if days_late < 1:
        return 0.0

    # Initial penalty on first day late
    initial = INITIAL_PENALTY

    # Daily penalty for days 2+ (capped at 5 days)
    daily_penalty_days = min(max(0, days_late - 1), MAX_DAILY_PENALTY_DAYS)
    daily = daily_penalty_days * DAILY_PENALTY

    return float(initial + daily)


def calculate_days_late(
    year: int,
    month: int,
    is_current_month: bool,
    is_future_month: bool,
    current_day: Optional[int] = None,
) -> int:
    """
    Calculate the number of days late for a given month.
    
    BACKWARD COMPATIBILITY WRAPPER.
    Prefer using calculate_rentas_claras_balance() for new code.

    Args:
        year: The year of the payment
        month: The month of the payment (1-12)
        is_current_month: True if this is the current calendar month
        is_future_month: True if this is a future month
        current_day: Override for current day (for testing)

    Returns:
        Number of days late (0 if not late)
    """
    import calendar
    
    if is_future_month:
        return 0

    if is_current_month:
        day = current_day or datetime.now().day
        return max(0, day - 1)

    # Past month - use last day of that month
    last_day = calendar.monthrange(year, month)[1]
    return max(0, last_day - 1)


def calculate_tenant_late_fee(
    rent: float,
    year: int,
    month: int,
    is_paid: bool,
    is_current_month: bool,
    is_future_month: bool,
    current_day: Optional[int] = None,
) -> LateFeeResult:
    """
    Calculate late fee for a specific tenant.
    
    BACKWARD COMPATIBILITY WRAPPER.
    This function wraps calculate_rentas_claras_balance() to maintain
    the original interface used by routes/pagos.py.

    Args:
        rent: Monthly rent amount in MXN
        year: Payment year
        month: Payment month (1-12)
        is_paid: True if already paid
        is_current_month: True if current calendar month
        is_future_month: True if future month
        current_day: Override for current day (for testing)

    Returns:
        LateFeeResult with full details
    """
    # Determine the effective day for calculation
    if is_future_month:
        effective_day = 1  # No late fees for future months
    elif is_current_month:
        effective_day = current_day or datetime.now().day
    else:
        # Past month - use a high day to get full late fees
        import calendar
        effective_day = calendar.monthrange(year, month)[1]

    # If paid, return early with zero fees
    if is_paid:
        return LateFeeResult(
            base_rent=Decimal(str(rent)),
            utilities=Decimal("0"),
            days_late=0,
            initial_penalty=Decimal("0"),
            daily_penalties=Decimal("0"),
            total_penalties=Decimal("0"),
            total_due=Decimal(str(rent)),
            status=PaymentStatus.PAID,
            warning_message=None,
            breakdown="",
        )

    # Use the comprehensive calculator
    result = calculate_rentas_claras_balance(
        base_rent=rent,
        utilities=0,  # Routes/pagos.py doesn't track utilities separately
        current_day=effective_day,
        already_paid=rent if is_paid else 0,
    )

    return result


# =============================================================================
# CONVENIENCE PROPERTIES FOR BACKWARD COMPATIBILITY
# =============================================================================

# Expose commonly needed attributes at module level
__all__ = [
    # Constants (old names)
    "INITIAL_PENALTY",
    "DAILY_PENALTY",
    # Constants (new names)
    "INITIAL_PENALTY_MXN",
    "DAILY_PENALTY_MXN",
    "MAX_DAILY_PENALTY_DAYS",
    "TERMINATION_WARNING_DAY",
    # Enums
    "PaymentStatus",
    "PropertyType",
    # Dataclasses
    "LateFeeResult",
    "PropertyConfig",
    "PropertySubtotal",
    "GrandTotal",
    # Property configurations
    "PROPERTIES",
    # Backward-compatible functions
    "calculate_late_fee",
    "calculate_days_late",
    "calculate_tenant_late_fee",
    # Core functions from src/late_fees.py
    "calculate_rentas_claras_balance",
    "calculate_tenant_utilities",
    "calculate_property_subtotal",
    "calculate_grand_total",
    # Formatting
    "format_property_subtotal",
    "format_grand_total",
    # Message generation
    "generate_payment_request_message",
    "generate_reminder_message",
]

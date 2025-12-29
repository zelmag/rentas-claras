"""
Late Fee Calculation Services
==============================

Business logic for calculating late fees on rent payments.
Based on the contract terms for RentasClaras properties.

Fee Structure:
- Day 1: No fee (rent is due)
- Day 2: $500 MXN initial penalty
- Days 3-7: +$100 MXN per day (up to $500 max daily fees)
- Day 8+: Capped at $500 + $500 = $1,000 MXN maximum

Formula: late_fee = 500 + min(days_late - 1, 5) * 100
"""

import calendar
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


# =============================================================================
# CONSTANTS
# =============================================================================

# Late fee configuration
INITIAL_PENALTY = 500  # $500 MXN on day 2
DAILY_PENALTY = 100  # $100 MXN per day after day 2
MAX_DAILY_PENALTY_DAYS = 5  # Cap daily penalty at 5 days ($500 max)

# Derived: Maximum late fee = 500 + (5 * 100) = $1,000 MXN


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class LateFeeResult:
    """Result of late fee calculation."""
    days_late: int
    late_fee: float
    total_owed: float
    breakdown: Optional[str] = None


# =============================================================================
# FUNCTIONS
# =============================================================================

def calculate_late_fee(days_late: int) -> float:
    """
    Calculate the late fee based on days late.

    Args:
        days_late: Number of days past the due date (day 1)

    Returns:
        Late fee amount in MXN

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

    Args:
        year: The year of the payment
        month: The month of the payment (1-12)
        is_current_month: True if this is the current calendar month
        is_future_month: True if this is a future month
        current_day: Override for current day (for testing)

    Returns:
        Number of days late (0 if not late)
    """
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

    Args:
        rent: Monthly rent amount in MXN
        year: Payment year
        month: Payment month (1-12)
        is_paid: True if already paid
        is_current_month: True if current calendar month
        is_future_month: True if future month
        current_day: Override for current day (for testing)

    Returns:
        LateFeeResult with days_late, late_fee, and total_owed
    """
    if is_paid:
        return LateFeeResult(
            days_late=0,
            late_fee=0.0,
            total_owed=float(rent),
        )

    days_late = calculate_days_late(
        year=year,
        month=month,
        is_current_month=is_current_month,
        is_future_month=is_future_month,
        current_day=current_day,
    )

    late_fee = calculate_late_fee(days_late)
    total_owed = float(rent) + late_fee

    # Generate breakdown for display
    breakdown = None
    if late_fee > 0:
        daily_portion = late_fee - INITIAL_PENALTY
        if daily_portion > 0:
            breakdown = f"${INITIAL_PENALTY:,.0f} + ${daily_portion:,.0f}"
        else:
            breakdown = f"${INITIAL_PENALTY:,.0f}"

    return LateFeeResult(
        days_late=days_late,
        late_fee=late_fee,
        total_owed=total_owed,
        breakdown=breakdown,
    )

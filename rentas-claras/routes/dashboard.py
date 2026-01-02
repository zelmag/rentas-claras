"""
Dashboard Blueprint - Home/Summary Screen
==========================================

Dashboard page showing overall status at a glance.
"""

from datetime import datetime

from database import (
    get_billable_tenants,
    get_db_connection,
    get_expiring_contracts,
    get_monthly_status,
)

from flask import Blueprint, render_template
from routes.auth import login_required
from services.dates import get_billing_month, SPANISH_DAYS_OF_WEEK, SPANISH_MONTHS


dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/resumen")
@login_required
def index():
    """Dashboard home page with overall status."""
    today = datetime.now()
    hour = today.hour

    # Time-based greeting in Spanish
    if hour < 12:
        greeting = "Buenos días"
    elif hour < 19:
        greeting = "Buenas tardes"
    else:
        greeting = "Buenas noches"

    # Format today's date in Spanish using centralized constants
    dia_semana = SPANISH_DAYS_OF_WEEK[today.weekday()]
    dia = today.day
    mes = SPANISH_MONTHS[today.month - 1]
    today_formatted = f"{dia_semana.capitalize()} {dia} de {mes}"

    # Get billing month from SINGLE SOURCE OF TRUTH
    # This ensures all pages (dashboard, pagos, state API) use the same month
    year, month, month_name = get_billing_month(today)

    # Get billable tenants using SINGLE SOURCE OF TRUTH
    # This filters out tenants whose contract starts in the billing month
    all_tenants = get_billable_tenants(year, month)
    monthly_status = get_monthly_status(year, month)

    # Calculate totals
    total_tenants = len(all_tenants)
    total_expected = sum(t.rent for t in all_tenants)

    # Get paid/pending counts
    total_collected = 0
    pending_payments = 0
    pending_amount = 0

    for tenant in all_tenants:
        status = monthly_status.get(tenant.id, {})
        if status.get("paid", 0):
            total_collected += tenant.rent
        else:
            pending_payments += 1
            pending_amount += tenant.rent

    # Collection percentage
    collection_percent = (
        round((total_collected / total_expected * 100)) if total_expected > 0 else 0
    )

    # Get unique properties
    properties = set(t.property_name for t in all_tenants)
    total_properties = len(properties)

    # Get expiring contracts
    expiring = get_expiring_contracts(days_ahead=30)
    expiring_contracts = len(expiring)

    # Property pending breakdown with colors
    PROPERTY_COLORS = ["#2D6A4F", "#9B2C2C", "#B7791F", "#5B21B6", "#0891B2", "#DB2777"]
    property_pending = []
    property_names = sorted(list(properties))
    for i, prop_name in enumerate(property_names):
        pending_for_prop = sum(
            1
            for t in all_tenants
            if t.property_name == prop_name
            and not monthly_status.get(t.id, {}).get("paid", 0)
        )
        if pending_for_prop > 0:
            property_pending.append(
                {
                    "name": prop_name[:10],  # Truncate long names
                    "pending": pending_for_prop,
                    "color": PROPERTY_COLORS[i % len(PROPERTY_COLORS)],
                }
            )

    # Get message status stats for today
    message_stats = _get_today_message_stats()

    return render_template(
        "dashboard.html",
        greeting=greeting,
        today_formatted=today_formatted,
        month_name=month_name,
        total_collected=total_collected,
        total_expected=total_expected,
        collection_percent=collection_percent,
        pending_payments=pending_payments,
        pending_amount=pending_amount,
        expiring_contracts=expiring_contracts,
        total_tenants=total_tenants,
        total_properties=total_properties,
        property_pending=property_pending,
        message_stats=message_stats,
        active_tab="resumen",
    )


def _get_today_message_stats() -> dict:
    """
    Get message statistics for today.

    Returns:
    {
        "sent": 5,
        "delivered": 4,
        "read": 3,
        "failed": 0,
        "replies": 1,
        "has_activity": True
    }
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Get message status counts
    cursor.execute(
        """
        SELECT status, COUNT(*) as count
        FROM message_logs
        WHERE sent_at >= ?
        GROUP BY status
        """,
        (today_start.isoformat(),),
    )

    status_counts = {
        "sent": 0,
        "delivered": 0,
        "read": 0,
        "failed": 0,
    }

    for row in cursor.fetchall():
        status = row["status"]
        count = row["count"]
        if status in status_counts:
            status_counts[status] = count

    # Get reply count
    # Check if incoming_messages table exists
    cursor.execute(
        """
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='incoming_messages'
        """
    )

    replies = 0
    if cursor.fetchone():
        cursor.execute(
            """
            SELECT COUNT(*) as count
            FROM incoming_messages
            WHERE received_at >= ?
            """,
            (today_start.isoformat(),),
        )
        row = cursor.fetchone()
        if row:
            replies = row["count"]

    conn.close()

    # Total sent includes all statuses (they all started as sent)
    total_sent = (
        status_counts["sent"]
        + status_counts["delivered"]
        + status_counts["read"]
        + status_counts["failed"]
    )

    return {
        "sent": total_sent,
        "delivered": status_counts["delivered"]
        + status_counts["read"],  # delivered + read = all delivered
        "read": status_counts["read"],
        "failed": status_counts["failed"],
        "replies": replies,
        "has_activity": total_sent > 0 or replies > 0,
    }

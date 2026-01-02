"""
Depósitos Blueprint - Security Deposit Tracking
================================================

View all security deposits received from tenants.
Features:
- Track when deposit was paid (received)
- Editable deposit amount (defaults to first month rent)
- Track when deposit was returned
"""

import logging
from decimal import Decimal

from database import get_all_tenants, get_db_connection, get_last_sync_time

from flask import Blueprint, jsonify, render_template, request
from routes.auth import login_required
from services.dates import calculate_relative_time, format_date_spanish, parse_date
from services.validation import validate_deposit_update


logger = logging.getLogger(__name__)
depositos_bp = Blueprint("depositos", __name__)


# =============================================================================
# DATABASE HELPERS
# =============================================================================


def update_deposit_info(
    tenant_id: str,
    deposit_amount: float = None,
    deposit_paid: bool = None,
    deposit_paid_date: str = None,
    deposit_returned: bool = None,
    deposit_returned_date: str = None,
    deposit_returned_notes: str = None,
):
    """Update deposit info for a tenant."""
    conn = get_db_connection()
    cursor = conn.cursor()

    updates = []
    params = []

    if deposit_amount is not None:
        updates.append("deposit_amount = ?")
        params.append(deposit_amount)
    if deposit_paid is not None:
        updates.append("deposit_paid = ?")
        params.append(1 if deposit_paid else 0)
    if deposit_paid_date is not None:
        updates.append("deposit_paid_date = ?")
        params.append(deposit_paid_date if deposit_paid_date else None)
    if deposit_returned is not None:
        updates.append("deposit_returned = ?")
        params.append(1 if deposit_returned else 0)
    if deposit_returned_date is not None:
        updates.append("deposit_returned_date = ?")
        params.append(deposit_returned_date if deposit_returned_date else None)
    if deposit_returned_notes is not None:
        updates.append("deposit_returned_notes = ?")
        params.append(deposit_returned_notes if deposit_returned_notes else None)

    if updates:
        updates.append("updated_at = datetime('now')")
        params.append(tenant_id)

        cursor.execute(
            f"""
            UPDATE tenants SET {', '.join(updates)}
            WHERE id = ?
            """,
            params,
        )

        conn.commit()

    conn.close()


# =============================================================================
# ROUTES
# =============================================================================


@depositos_bp.route("/depositos")
@login_required
def depositos():
    """Deposits overview page - shows all security deposits by property."""
    all_tenants = get_all_tenants()

    # Get deposit info for all tenants
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, rent, deposit_amount, deposit_paid, deposit_paid_date,
               deposit_returned, deposit_returned_date, deposit_returned_notes
        FROM tenants WHERE active = 1
        """
    )
    deposit_info = {row["id"]: dict(row) for row in cursor.fetchall()}
    conn.close()

    # Group tenants by property and calculate totals
    tenants_by_property = {}
    property_totals = {}
    grand_total = Decimal("0")
    paid_total = Decimal("0")
    pending_total = Decimal("0")
    returned_total = Decimal("0")
    active_count = 0
    returned_count = 0

    for tenant in all_tenants:
        prop = tenant.property_name

        # Initialize property group if needed
        if prop not in tenants_by_property:
            tenants_by_property[prop] = []
            property_totals[prop] = {
                "total": Decimal("0"),
                "paid": Decimal("0"),
                "pending": Decimal("0"),
            }

        # Format contract start date for display
        if tenant.contract_start:
            tenant.contract_start_formatted = format_date_spanish(tenant.contract_start)
        else:
            tenant.contract_start_formatted = "Sin fecha"

        # Get deposit info
        info = deposit_info.get(tenant.id, {})

        # Deposit amount: use custom amount if set, otherwise default to rent
        raw_amount = info.get("deposit_amount")
        if raw_amount is not None and raw_amount > 0:
            tenant.deposit_amount = Decimal(str(raw_amount))
        else:
            tenant.deposit_amount = tenant.rent

        # Payment status
        tenant.deposit_paid = bool(info.get("deposit_paid", 0))
        tenant.deposit_paid_date = info.get("deposit_paid_date")
        if tenant.deposit_paid_date:
            tenant.deposit_paid_date_formatted = format_date_spanish(
                tenant.deposit_paid_date
            )
        else:
            tenant.deposit_paid_date_formatted = None

        # Return status
        tenant.deposit_returned = bool(info.get("deposit_returned", 0))
        tenant.deposit_returned_date = info.get("deposit_returned_date")
        tenant.deposit_returned_notes = info.get("deposit_returned_notes")
        if tenant.deposit_returned_date:
            tenant.deposit_returned_date_formatted = format_date_spanish(
                tenant.deposit_returned_date
            )
        else:
            tenant.deposit_returned_date_formatted = None

        tenants_by_property[prop].append(tenant)

        # Track returned vs active deposits separately
        if tenant.deposit_returned:
            returned_total += tenant.deposit_amount
            returned_count += 1
        else:
            grand_total += tenant.deposit_amount
            active_count += 1
            property_totals[prop]["total"] += tenant.deposit_amount

            if tenant.deposit_paid:
                property_totals[prop]["paid"] += tenant.deposit_amount
                paid_total += tenant.deposit_amount
            else:
                property_totals[prop]["pending"] += tenant.deposit_amount
                pending_total += tenant.deposit_amount

    # Sort tenants within each property by contract_start date (most recent first)
    def get_contract_start_sort_key(tenant):
        """Return sort key for contract_start - most recent first, None values last."""
        if tenant.contract_start:
            parsed = parse_date(tenant.contract_start)
            if parsed:
                # Negative timestamp for descending order (most recent first)
                return (0, -parsed.timestamp())
        # Tenants without contract_start go last
        return (1, 0)

    for prop in tenants_by_property:
        tenants_by_property[prop].sort(key=get_contract_start_sort_key)

    # Property colors (matching contratos.html)
    property_colors = ["blue", "brown", "green", "purple", "gold"]

    # Get last sync time for sync indicator
    last_sync = get_last_sync_time()
    last_sync_relative = calculate_relative_time(last_sync)

    return render_template(
        "depositos.html",
        tenants_by_property=tenants_by_property,
        property_totals=property_totals,
        property_colors=property_colors,
        grand_total=grand_total,
        paid_total=paid_total,
        pending_total=pending_total,
        returned_total=returned_total,
        total_tenants=len(all_tenants),
        active_count=active_count,
        returned_count=returned_count,
        last_sync=last_sync,
        last_sync_relative=last_sync_relative,
        active_tab="depositos",
    )


@depositos_bp.route("/api/deposit", methods=["POST"])
@login_required
def update_deposit():
    """Update deposit info for a tenant."""
    data = request.json
    if not data:
        return jsonify({"success": False, "error": "Request body is required"}), 400

    # Validate input data
    is_valid, error, validated = validate_deposit_update(data)
    if not is_valid:
        logger.warning(f"Deposit validation failed: {error}")
        return jsonify({"success": False, "error": error}), 400

    try:
        update_deposit_info(
            tenant_id=validated["tenant_id"],
            deposit_amount=validated.get("deposit_amount"),
            deposit_paid=validated.get("deposit_paid"),
            deposit_paid_date=validated.get("deposit_paid_date"),
            deposit_returned=validated.get("deposit_returned"),
            deposit_returned_date=validated.get("deposit_returned_date"),
            deposit_returned_notes=validated.get("deposit_returned_notes"),
        )

        return jsonify({"success": True})
    except Exception as e:
        logger.exception(f"Error updating deposit: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

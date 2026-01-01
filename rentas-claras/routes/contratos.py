"""
Contratos Blueprint - Contract Renewal Management
==================================================

Contract renewal tracking page and related API endpoints.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta

from database import auto_renew_contract, get_all_tenants, get_last_sync_time, update_renewal_status

from flask import Blueprint, jsonify, render_template, request
from routes.auth import login_required
from services.dates import (
    calculate_relative_time,
    format_date_spanish,
    parse_date,
    parse_spanish_month_year,
    SPANISH_MONTHS_CAPITALIZED as SPANISH_MONTHS,
)
from services.validation import validate_renewal_update


logger = logging.getLogger(__name__)
contratos_bp = Blueprint("contratos", __name__)


# =============================================================================
# ROUTES
# =============================================================================


@contratos_bp.route("/contratos")
@login_required
def contracts():
    """Contract renewal management page."""
    all_tenants = get_all_tenants()
    tenants_by_property = {}

    today = datetime.now()
    today_date = today.date()  # Use date object for consistent comparison

    # Count by renewal status (limited to next month for actionable items)
    renewing_count = 0
    not_renewing_count = 0
    pending_count = 0

    # Calculate the date range for "next month" (contracts expiring in next 31 days)
    next_month_cutoff = today + timedelta(days=31)

    # Add days_until_expiry for urgency highlighting
    for tenant in all_tenants:
        if tenant.contract_end:
            parsed = parse_date(tenant.contract_end)
            if parsed:
                tenant.days_until_expiry = (parsed.date() - today_date).days
            else:
                tenant.days_until_expiry = None
        else:
            tenant.days_until_expiry = None

    # Track upcoming renewals for bird's eye view, grouped by month
    upcoming_by_month = defaultdict(list)

    for tenant in all_tenants:
        # Format contract dates for display
        if tenant.contract_start:
            tenant.contract_start_formatted = format_date_spanish(tenant.contract_start)
        else:
            tenant.contract_start_formatted = None
        if tenant.contract_end:
            tenant.contract_end_formatted = format_date_spanish(tenant.contract_end)
        else:
            tenant.contract_end_formatted = None

        if tenant.property_name not in tenants_by_property:
            tenants_by_property[tenant.property_name] = []
        tenants_by_property[tenant.property_name].append(tenant)

        # Count statuses only for contracts expiring within next 30 days
        contract_expires_soon = False
        if tenant.contract_end:
            parsed_end = parse_date(tenant.contract_end)
            if parsed_end and parsed_end.date() <= next_month_cutoff.date():
                contract_expires_soon = True

        # Only count contracts expiring within next 30 days for ALL statuses
        if contract_expires_soon:
            if tenant.renewal_status == "renovará":
                renewing_count += 1
            elif tenant.renewal_status == "no_renovará":
                not_renewing_count += 1
            else:  # pendiente
                pending_count += 1

        # Add to upcoming renewals grouped by month
        if tenant.contract_end:
            parsed = parse_date(tenant.contract_end)
            if parsed:
                month_key = f"{SPANISH_MONTHS[parsed.month - 1]} {parsed.year}"
                upcoming_by_month[month_key].append(
                    {"tenant": tenant, "parsed_date": parsed}
                )

    # Sort tenants within each month by date
    for month_key in upcoming_by_month:
        upcoming_by_month[month_key].sort(key=lambda x: x["parsed_date"])

    # Sort months chronologically
    sorted_months = sorted(upcoming_by_month.keys(), key=parse_spanish_month_year)

    # Build ordered dict of month -> tenants
    upcoming_renewals_by_month = []
    for month_key in sorted_months:
        upcoming_renewals_by_month.append(
            {
                "month": month_key,
                "tenants": [item["tenant"] for item in upcoming_by_month[month_key]],
            }
        )

    # Sort tenants within each property by contract end date
    for prop_name in tenants_by_property:
        tenants_by_property[prop_name].sort(
            key=lambda t: (
                parse_date(t.contract_end)
                if t.contract_end and parse_date(t.contract_end)
                else datetime.max
            )
        )

    # Compute property-level stats for contracts expiring in next 30 days
    property_stats = {}
    for prop_name, tenants in tenants_by_property.items():
        prop_renewing = 0
        prop_not_renewing = 0
        prop_pending = 0
        prop_expiring_soon = 0

        for tenant in tenants:
            expires_soon = False
            if tenant.contract_end:
                parsed_end = parse_date(tenant.contract_end)
                if parsed_end and parsed_end <= next_month_cutoff:
                    expires_soon = True
                    prop_expiring_soon += 1

            if expires_soon:
                if tenant.renewal_status == "renovará":
                    prop_renewing += 1
                elif tenant.renewal_status == "no_renovará":
                    prop_not_renewing += 1
                else:
                    prop_pending += 1

        property_stats[prop_name] = {
            "renewing": prop_renewing,
            "not_renewing": prop_not_renewing,
            "pending": prop_pending,
            "expiring_soon": prop_expiring_soon,
            "total": len(tenants),
        }

    # Build list of available apartments (no renovará + no replacement candidate)
    available_apartments = []
    for tenant in all_tenants:
        if tenant.renewal_status == "no_renovará" and not tenant.replacement_name:
            available_apartments.append(tenant)

        # Sort by contract end date (soonest first)
        available_apartments.sort(
            key=lambda t: (
                parse_date(t.contract_end)
                if t.contract_end and parse_date(t.contract_end)
                else datetime.max
            )
        )

    # Filter upcoming renewals to only show "action needed" items
    action_needed_renewals_by_month = []
    action_needed_count = 0
    for month_group in upcoming_renewals_by_month:
        filtered_tenants = []
        for tenant in month_group["tenants"]:
            if (
                not hasattr(tenant, "days_until_expiry")
                or tenant.days_until_expiry > 31
            ):
                continue

            needs_action = False
            if tenant.renewal_status == "pendiente":
                needs_action = True
            elif tenant.renewal_status == "no_renovará" and not tenant.replacement_name:
                needs_action = True

            if needs_action:
                filtered_tenants.append(tenant)
                action_needed_count += 1

        if filtered_tenants:
            action_needed_renewals_by_month.append(
                {"month": month_group["month"], "tenants": filtered_tenants}
            )

    # Get last sync time for sync indicator
    last_sync = get_last_sync_time()
    last_sync_relative = calculate_relative_time(last_sync)

    template_vars = dict(
        tenants_by_property=tenants_by_property,
        property_stats=property_stats,
        total_tenants=len(all_tenants),
        renewing_count=renewing_count,
        not_renewing_count=not_renewing_count,
        pending_count=pending_count,
        upcoming_renewals_by_month=action_needed_renewals_by_month,
        action_needed_count=action_needed_count,
        available_apartments=available_apartments,
        last_sync=last_sync,
        last_sync_relative=last_sync_relative,
        active_tab="contratos",
    )

    return render_template("contratos.html", **template_vars)


@contratos_bp.route("/api/renewal", methods=["POST"])
@login_required
def update_renewal():
    """Update contract renewal status for a tenant."""
    data = request.json
    if not data:
        return jsonify({"success": False, "error": "Request body is required"}), 400

    # Validate input data
    is_valid, error, validated = validate_renewal_update(data)
    if not is_valid:
        logger.warning(f"Renewal validation failed: {error}")
        return jsonify({"success": False, "error": error}), 400

    try:
        update_renewal_status(
            tenant_id=validated["tenant_id"],
            renewal_status=validated.get("renewal_status"),
            contract_delivered=validated.get("contract_delivered"),
            contract_picked_up=validated.get("contract_picked_up"),
            leaving_date=validated.get("leaving_date"),
            replacement_name=validated.get("replacement_name"),
            replacement_phone=validated.get("replacement_phone"),
            replacement_contract_start=validated.get("replacement_contract_start"),
            replacement_contract_end=validated.get("replacement_contract_end"),
            replacement_aval_name=validated.get("replacement_aval_name"),
            replacement_aval_phone=validated.get("replacement_aval_phone"),
        )

        # Auto-renew contract when status is set to "renovará"
        new_contract_end = None
        if validated.get("renewal_status") == "renovará":
            new_contract_end = auto_renew_contract(validated["tenant_id"])
            if new_contract_end:
                logger.info(f"Auto-renewed contract for tenant {validated['tenant_id']} to {new_contract_end}")

        return jsonify({
            "success": True,
            "new_contract_end": new_contract_end
        })
    except Exception as e:
        logger.exception(f"Error updating renewal: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

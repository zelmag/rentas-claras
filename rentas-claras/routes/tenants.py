"""
Tenant Management Blueprint - Add/Edit Tenants & Properties
============================================================

Admin page for managing tenants and properties.
"""

import logging

from database import (
    add_tenant,
    deactivate_tenant,
    get_all_properties,
    get_all_tenants,
    get_last_sync_time,
    get_tenant_by_id,
    reactivate_tenant,
    update_tenant,
)

from flask import Blueprint, jsonify, render_template, request
from routes.auth import login_required
from services.dates import calculate_relative_time
from services.validation import (
    sanitize_string,
    validate_date_string,
    validate_phone,
    validate_rent,
    validate_tenant_create,
    validate_tenant_id,
)


logger = logging.getLogger(__name__)
tenants_bp = Blueprint("tenants", __name__)


# =============================================================================
# ROUTES
# =============================================================================


@tenants_bp.route("/inquilinos")
@login_required
def tenants_page():
    """Tenant management page."""
    tenants = get_all_tenants()
    properties = get_all_properties()

    # Group tenants by property
    tenants_by_property = {}
    for tenant in tenants:
        if tenant.property_name not in tenants_by_property:
            tenants_by_property[tenant.property_name] = []
        tenants_by_property[tenant.property_name].append(tenant)

    # Get last sync time for sync indicator
    last_sync = get_last_sync_time()
    last_sync_relative = calculate_relative_time(last_sync)

    return render_template(
        "inquilinos.html",
        tenants=tenants,
        tenants_by_property=tenants_by_property,
        properties=properties,
        total_tenants=len(tenants),
        last_sync=last_sync,
        last_sync_relative=last_sync_relative,
        active_tab="inquilinos",
    )


@tenants_bp.route("/api/tenant", methods=["POST"])
@login_required
def api_add_tenant():
    """Add a new tenant."""
    data = request.json
    if not data:
        return jsonify({"success": False, "error": "Request body is required"}), 400

    # Validate input data
    is_valid, error, validated = validate_tenant_create(data)
    if not is_valid:
        logger.warning(f"Tenant creation validation failed: {error}")
        return jsonify({"success": False, "error": error}), 400

    try:
        tenant_id = add_tenant(
            name=validated["name"],
            property_name=validated["property_name"],
            unit=validated["unit"],
            rent=validated["rent"],
            phone=validated.get("phone", ""),
            contract_start=validated.get("contract_start"),
            contract_end=validated.get("contract_end"),
            emergency_contact=validated.get("emergency_contact"),
            emergency_phone=validated.get("emergency_phone"),
            bank=validated.get("bank"),
            aval_name=validated.get("aval_name"),
            aval_phone=validated.get("aval_phone"),
            prorated_first_month=validated.get("prorated_first_month", False),
            prorated_amount=validated.get("prorated_amount"),
            prorated_month=validated.get("prorated_month"),
            prorated_year=validated.get("prorated_year"),
        )

        return jsonify({"success": True, "tenant_id": tenant_id})
    except Exception as e:
        logger.exception(f"Error adding tenant: {e}")
        return jsonify({"success": False, "error": str(e)}), 400


@tenants_bp.route("/api/tenant/<tenant_id>", methods=["PUT"])
@login_required
def api_update_tenant(tenant_id):
    """Update an existing tenant."""
    data = request.json
    if not data:
        return jsonify({"success": False, "error": "Request body is required"}), 400

    # Validate tenant_id
    is_valid, error = validate_tenant_id(tenant_id)
    if not is_valid:
        return jsonify({"success": False, "error": error}), 400

    # Validate individual fields if provided
    errors = []

    if "name" in data:
        name = sanitize_string(data.get("name"), max_length=200)
        if not name:
            errors.append("name cannot be empty")

    if "phone" in data:
        is_valid, error = validate_phone(data.get("phone"))
        if not is_valid:
            errors.append(error)

    if "rent" in data:
        is_valid, error = validate_rent(data.get("rent"))
        if not is_valid:
            errors.append(error)

    for date_field in ["contract_start", "contract_end"]:
        if date_field in data:
            is_valid, error = validate_date_string(data.get(date_field), date_field)
            if not is_valid:
                errors.append(error)

    if errors:
        return jsonify({"success": False, "error": "; ".join(errors)}), 400

    try:
        update_tenant(
            tenant_id=tenant_id,
            name=sanitize_string(data.get("name")),
            phone=sanitize_string(data.get("phone")),
            property_name=sanitize_string(data.get("property_name")),
            unit=sanitize_string(data.get("unit"), max_length=20),
            rent=(
                float(data["rent"])
                if "rent" in data and data["rent"] is not None
                else None
            ),
            contract_start=data.get("contract_start"),
            contract_end=data.get("contract_end"),
            emergency_contact=sanitize_string(data.get("emergency_contact")),
            emergency_phone=sanitize_string(data.get("emergency_phone")),
            bank=sanitize_string(data.get("bank"), max_length=50),
            aval_name=sanitize_string(data.get("aval_name")),
            aval_phone=sanitize_string(data.get("aval_phone")),
        )

        return jsonify({"success": True})
    except Exception as e:
        logger.exception(f"Error updating tenant: {e}")
        return jsonify({"success": False, "error": str(e)}), 400


@tenants_bp.route("/api/tenant/<tenant_id>", methods=["DELETE"])
@login_required
def api_deactivate_tenant(tenant_id):
    """Deactivate (soft-delete) a tenant."""
    # Validate tenant_id
    is_valid, error = validate_tenant_id(tenant_id)
    if not is_valid:
        return jsonify({"success": False, "error": error}), 400

    try:
        deactivate_tenant(tenant_id)
        return jsonify({"success": True})
    except Exception as e:
        logger.exception(f"Error deactivating tenant: {e}")
        return jsonify({"success": False, "error": str(e)}), 400


@tenants_bp.route("/api/tenant/<tenant_id>/reactivate", methods=["POST"])
@login_required
def api_reactivate_tenant(tenant_id):
    """Reactivate a previously deactivated tenant."""
    # Validate tenant_id
    is_valid, error = validate_tenant_id(tenant_id)
    if not is_valid:
        return jsonify({"success": False, "error": error}), 400

    try:
        reactivate_tenant(tenant_id)
        return jsonify({"success": True})
    except Exception as e:
        logger.exception(f"Error reactivating tenant: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

"""
Tenant Management Blueprint - Add/Edit Tenants & Properties
============================================================

Admin page for managing tenants and properties.
"""

from flask import Blueprint, jsonify, render_template, request

from database import (
    add_tenant,
    deactivate_tenant,
    get_all_properties,
    get_all_tenants,
    get_tenant_by_id,
    reactivate_tenant,
    update_tenant,
)
from routes.auth import login_required


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
    
    return render_template(
        "inquilinos.html",
        tenants=tenants,
        tenants_by_property=tenants_by_property,
        properties=properties,
        total_tenants=len(tenants),
        active_tab="inquilinos",
    )


@tenants_bp.route("/api/tenant", methods=["POST"])
@login_required
def api_add_tenant():
    """Add a new tenant."""
    data = request.json
    
    try:
        tenant_id = add_tenant(
            name=data.get("name", "").strip(),
            property_name=data.get("property_name", "").strip(),
            unit=data.get("unit", "").strip(),
            rent=float(data.get("rent", 0)),
            phone=data.get("phone", "").strip(),
            contract_start=data.get("contract_start"),
            contract_end=data.get("contract_end"),
            emergency_contact=data.get("emergency_contact"),
            emergency_phone=data.get("emergency_phone"),
            bank=data.get("bank"),
        )
        
        return jsonify({"success": True, "tenant_id": tenant_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@tenants_bp.route("/api/tenant/<tenant_id>", methods=["PUT"])
@login_required
def api_update_tenant(tenant_id):
    """Update an existing tenant."""
    data = request.json
    
    try:
        update_tenant(
            tenant_id=tenant_id,
            name=data.get("name"),
            phone=data.get("phone"),
            property_name=data.get("property_name"),
            unit=data.get("unit"),
            rent=float(data["rent"]) if "rent" in data else None,
            contract_start=data.get("contract_start"),
            contract_end=data.get("contract_end"),
            emergency_contact=data.get("emergency_contact"),
            emergency_phone=data.get("emergency_phone"),
            bank=data.get("bank"),
        )
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@tenants_bp.route("/api/tenant/<tenant_id>", methods=["DELETE"])
@login_required
def api_deactivate_tenant(tenant_id):
    """Deactivate (soft-delete) a tenant."""
    try:
        deactivate_tenant(tenant_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@tenants_bp.route("/api/tenant/<tenant_id>/reactivate", methods=["POST"])
@login_required
def api_reactivate_tenant(tenant_id):
    """Reactivate a previously deactivated tenant."""
    try:
        reactivate_tenant(tenant_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

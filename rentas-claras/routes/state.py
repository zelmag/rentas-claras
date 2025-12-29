"""
State Blueprint - Central State API (Single Source of Truth)
============================================================

Provides a unified API endpoint for fetching current app state.
All pages can poll this endpoint to stay in sync with the database.

This is the SERVER-SIDE SOT that feeds the client-side state.js module.
"""

from datetime import datetime

from flask import Blueprint, jsonify

from database import (
    get_all_tenants,
    get_expiring_contracts,
    get_last_sync_time,
    get_monthly_status,
)
from routes.auth import login_required
from services.dates import SPANISH_MONTHS, calculate_relative_time


state_bp = Blueprint("state", __name__)


@state_bp.route("/api/state/summary")
@login_required
def get_state_summary():
    """
    Get comprehensive state summary for all pages.
    
    This is the single source of truth API that all pages poll.
    Returns current month payment status, tenant counts, and key metrics.
    
    Response:
    {
        "success": true,
        "summary": {
            "total_collected": 50000,
            "total_expected": 80000,
            "collection_percent": 63,
            "pending_payments": 10,
            "pending_amount": 30000,
            "paid_count": 22,
            "unpaid_count": 10,
            "total_tenants": 32,
            "total_properties": 5,
            "expiring_contracts": 3,
            "month_name": "Enero",
            "year": 2025,
            "month": 1,
            "last_sync": "2025-01-01T10:30:00",
            "last_sync_relative": "hace 5 min",
            "payments": {
                "tenant_id_year_month": {
                    "paid": true,
                    "payment_method": "Efectivo",
                    "visits": 0,
                    "visit_charge": 0
                }
            },
            "tenants_summary": [
                {
                    "id": "MAT-A",
                    "name": "Juan Pérez",
                    "property_name": "Matehuala",
                    "unit": "A",
                    "rent": 8000,
                    "paid": true
                }
            ]
        }
    }
    """
    today = datetime.now()
    year = today.year
    month = today.month
    
    # Auto-switch: After day 7, use next month as default
    if today.day > 7:
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
    
    month_name = SPANISH_MONTHS[month - 1]
    
    # Get all tenants and payment status
    all_tenants = get_all_tenants()
    monthly_status = get_monthly_status(year, month)
    
    # Calculate totals
    total_tenants = len(all_tenants)
    total_expected = sum(float(t.rent) for t in all_tenants)
    
    # Track payments
    total_collected = 0
    pending_payments = 0
    pending_amount = 0
    paid_count = 0
    unpaid_count = 0
    
    # Build payments dict and tenant summaries
    payments = {}
    tenants_summary = []
    
    for tenant in all_tenants:
        status = monthly_status.get(tenant.id, {})
        is_paid = bool(status.get("paid", 0))
        
        if is_paid:
            total_collected += float(tenant.rent)
            paid_count += 1
        else:
            pending_payments += 1
            pending_amount += float(tenant.rent)
            unpaid_count += 1
        
        # Payment record keyed by tenant_id_year_month
        payments[f"{tenant.id}_{year}_{month}"] = {
            "paid": is_paid,
            "payment_method": status.get("payment_method"),
            "visits": status.get("visits", 0),
            "visit_charge": status.get("visit_charge", 0),
        }
        
        # Tenant summary for list views
        tenants_summary.append({
            "id": tenant.id,
            "name": tenant.name,
            "property_name": tenant.property_name,
            "unit": tenant.unit,
            "rent": float(tenant.rent),
            "phone": tenant.phone or "",
            "paid": is_paid,
            "payment_method": status.get("payment_method"),
            "contract_end": tenant.contract_end,
        })
    
    # Collection percentage
    collection_percent = round((total_collected / total_expected * 100)) if total_expected > 0 else 0
    
    # Get unique properties
    properties = set(t.property_name for t in all_tenants)
    total_properties = len(properties)
    
    # Get expiring contracts count
    expiring = get_expiring_contracts(days_ahead=30)
    expiring_contracts = len(expiring)
    
    # Get last sync time
    last_sync = get_last_sync_time()
    last_sync_relative = calculate_relative_time(last_sync)
    
    summary = {
        "total_collected": total_collected,
        "total_expected": total_expected,
        "collection_percent": collection_percent,
        "pending_payments": pending_payments,
        "pending_amount": pending_amount,
        "paid_count": paid_count,
        "unpaid_count": unpaid_count,
        "total_tenants": total_tenants,
        "total_properties": total_properties,
        "expiring_contracts": expiring_contracts,
        "month_name": month_name,
        "year": year,
        "month": month,
        "last_sync": last_sync,
        "last_sync_relative": last_sync_relative,
        "timestamp": datetime.now().isoformat(),
        "payments": payments,
        "tenants_summary": tenants_summary,
    }
    
    return jsonify({
        "success": True,
        "summary": summary
    })


@state_bp.route("/api/state/payments/<int:year>/<int:month>")
@login_required
def get_payments_for_month(year: int, month: int):
    """
    Get payment status for a specific month.
    
    Used when navigating to historical months.
    """
    all_tenants = get_all_tenants()
    monthly_status = get_monthly_status(year, month)
    month_name = SPANISH_MONTHS[month - 1]
    
    payments = {}
    total_collected = 0
    pending_amount = 0
    
    for tenant in all_tenants:
        status = monthly_status.get(tenant.id, {})
        is_paid = bool(status.get("paid", 0))
        
        if is_paid:
            total_collected += float(tenant.rent)
        else:
            pending_amount += float(tenant.rent)
        
        payments[tenant.id] = {
            "paid": is_paid,
            "payment_method": status.get("payment_method"),
            "visits": status.get("visits", 0),
            "visit_charge": status.get("visit_charge", 0),
        }
    
    total_expected = sum(float(t.rent) for t in all_tenants)
    collection_percent = round((total_collected / total_expected * 100)) if total_expected > 0 else 0
    
    return jsonify({
        "success": True,
        "year": year,
        "month": month,
        "month_name": month_name,
        "total_collected": total_collected,
        "pending_amount": pending_amount,
        "collection_percent": collection_percent,
        "payments": payments
    })

"""
Dashboard Blueprint - Home/Summary Screen
==========================================

Dashboard page showing overall status at a glance.
"""

from datetime import datetime

from flask import Blueprint, render_template

from database import (
    get_all_tenants,
    get_expiring_contracts,
    get_monthly_status,
)
from routes.auth import login_required
from services.dates import get_billing_month, SPANISH_MONTHS


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
    
    # Format today's date in Spanish (full format for clarity)
    DIAS_SEMANA = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
    MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 
             'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    
    dia_semana = DIAS_SEMANA[today.weekday()]
    dia = today.day
    mes = MESES[today.month - 1]
    today_formatted = f"{dia_semana.capitalize()} {dia} de {mes}"
    
    # Get billing month from SINGLE SOURCE OF TRUTH
    # This ensures all pages (dashboard, pagos, state API) use the same month
    year, month, month_name = get_billing_month(today)
    
    # Get tenants and payment status
    all_tenants = get_all_tenants()
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
    collection_percent = round((total_collected / total_expected * 100)) if total_expected > 0 else 0
    
    # Get unique properties
    properties = set(t.property_name for t in all_tenants)
    total_properties = len(properties)
    
    # Get expiring contracts
    expiring = get_expiring_contracts(days_ahead=30)
    expiring_contracts = len(expiring)
    
    # Property pending breakdown with colors
    PROPERTY_COLORS = ['#2D6A4F', '#9B2C2C', '#B7791F', '#5B21B6', '#0891B2', '#DB2777']
    property_pending = []
    property_names = sorted(list(properties))
    for i, prop_name in enumerate(property_names):
        pending_for_prop = sum(1 for t in all_tenants 
                               if t.property_name == prop_name 
                               and not monthly_status.get(t.id, {}).get("paid", 0))
        if pending_for_prop > 0:
            property_pending.append({
                'name': prop_name[:10],  # Truncate long names
                'pending': pending_for_prop,
                'color': PROPERTY_COLORS[i % len(PROPERTY_COLORS)]
            })
    
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
        active_tab="resumen",
    )

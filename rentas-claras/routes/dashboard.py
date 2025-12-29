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
from services.dates import SPANISH_MONTHS


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
    
    # Format today's date in Spanish
    DIAS_SEMANA = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
    MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 
             'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    
    dia_semana = DIAS_SEMANA[today.weekday()]
    dia = today.day
    mes = MESES[today.month - 1]
    año = today.year
    today_formatted = f"{dia_semana.capitalize()}, {dia} de {mes} de {año}"
    
    # Current month
    year = today.year
    month = today.month
    month_name = SPANISH_MONTHS[month - 1]
    
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
        active_tab="resumen",
    )

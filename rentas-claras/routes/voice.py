"""
Voice Agent API Routes
======================
Handles voice queries from the frontend.
Queries the database and returns natural Spanish responses.

INTENTS SUPPORTED:
- payment_status: "¿Ya pagó Claudia?"
- unpaid_list: "¿Quiénes no han pagado?"
- paid_list: "¿Quiénes ya pagaron?"
- contract_info: "¿Cuándo vence el contrato de María?"
- deposit_owed: "¿Cuánto depósito debemos a Juan?"
"""

import unicodedata
from datetime import datetime

from flask import Blueprint, jsonify, request

from database import get_all_tenants, get_monthly_status

voice_bp = Blueprint("voice", __name__)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def normalize_name(name: str) -> str:
    """
    Normalize name for fuzzy matching.
    
    Converts to lowercase and removes accents:
    - "María" → "maria"
    - "José" → "jose"
    - "Claudia García" → "claudia garcia"
    
    WHY? Speech recognition may or may not include accents,
    and we want "maria" to match "María García López".
    """
    if not name:
        return ""
    # NFD splits characters: é → e + ́ (combining accent)
    # Then we filter out the combining marks (category 'Mn')
    normalized = unicodedata.normalize("NFD", name.lower())
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn")


def find_tenant_by_name(name: str, tenants_status: dict) -> dict | None:
    """
    Find a tenant by fuzzy name match.
    
    Searches through all tenants and returns the first one whose name
    contains the search term (after normalization).
    
    Examples:
    - "claudia" matches "Claudia García López"
    - "garcia" matches "María García"
    - "juan" matches "Juan Carlos Pérez"
    
    Returns:
        Tenant dict with 'id' key added, or None if not found.
    """
    if not name:
        return None

    search_name = normalize_name(name)

    for tenant_id, tenant in tenants_status.items():
        tenant_name = normalize_name(tenant.get("name", ""))
        # Check if search term appears anywhere in the tenant's name
        if search_name in tenant_name:
            return {**tenant, "id": tenant_id}

    return None


def find_tenant_in_list(name: str, tenants: list) -> object | None:
    """
    Find a tenant by name in a list of Tenant objects.
    
    Similar to find_tenant_by_name but works with Tenant dataclass objects
    instead of dicts. Used for contract_info and deposit_owed which need
    the full Tenant object (not just monthly_status).
    """
    if not name:
        return None

    search_name = normalize_name(name)

    for tenant in tenants:
        if search_name in normalize_name(tenant.name):
            return tenant

    return None


def format_currency(amount: float) -> str:
    """Format a number as Mexican pesos: $7,800"""
    return f"${amount:,.0f}"


# =============================================================================
# API ENDPOINT
# =============================================================================


@voice_bp.route("/api/voice/query", methods=["POST"])
def voice_query():
    """
    Handle voice agent queries.
    
    This is the main endpoint that the frontend JavaScript calls.
    It receives an intent (detected by pattern matching in JS) and
    returns a natural Spanish response with real data.
    
    Request body:
    {
        "type": "payment_status" | "unpaid_list" | "paid_list" | ...,
        "name": "claudia" (optional, for name-based queries),
        "originalTranscript": "ya pagó claudia" (for debugging)
    }
    
    Response:
    {
        "response": "Sí, Claudia García ya pagó $7,800 por transferencia."
    }
    """
    data = request.json or {}
    intent_type = data.get("type", "unknown")
    name = data.get("name")

    # Get current month's payment status for all tenants
    now = datetime.now()
    tenants_status = get_monthly_status(now.year, now.month)

    response = ""

    # -------------------------------------------------------------------------
    # INTENT: payment_status - "¿Ya pagó Claudia?"
    # -------------------------------------------------------------------------
    if intent_type == "payment_status":
        if not name:
            response = "No capté el nombre. ¿De quién quieres saber?"
        else:
            tenant = find_tenant_by_name(name, tenants_status)
            if tenant:
                tenant_name = tenant.get("name", name)
                rent = tenant.get("rent", 0)
                paid = tenant.get("paid", False)

                if paid:
                    method = tenant.get("payment_method", "")
                    method_text = f" por {method}" if method else ""
                    response = f"Sí, {tenant_name} ya pagó {format_currency(rent)}{method_text}."
                else:
                    response = f"No, {tenant_name} no ha pagado. Debe {format_currency(rent)}."
            else:
                response = f"No encontré a nadie que se llame '{name}'."

    # -------------------------------------------------------------------------
    # INTENT: unpaid_list - "¿Quiénes no han pagado?"
    # -------------------------------------------------------------------------
    elif intent_type == "unpaid_list":
        unpaid = [t for t in tenants_status.values() if not t.get("paid")]
        count = len(unpaid)
        total = sum(t.get("rent", 0) for t in unpaid)

        if count == 0:
            response = "¡Todos han pagado este mes! 🎉"
        elif count <= 5:
            # List names if 5 or fewer (easy to read aloud)
            names = [t.get("name", "?").split()[0] for t in unpaid]  # First name only
            response = f"Faltan {count}: {', '.join(names)}. Total pendiente: {format_currency(total)}."
        else:
            # Too many to list, just summarize
            response = f"Faltan {count} inquilinos por pagar. Total pendiente: {format_currency(total)}."

    # -------------------------------------------------------------------------
    # INTENT: paid_list - "¿Quiénes ya pagaron?"
    # -------------------------------------------------------------------------
    elif intent_type == "paid_list":
        paid = [t for t in tenants_status.values() if t.get("paid")]
        count = len(paid)
        total = sum(t.get("rent", 0) for t in paid)

        if count == 0:
            response = "Nadie ha pagado todavía este mes."
        elif count <= 5:
            names = [t.get("name", "?").split()[0] for t in paid]  # First name only
            response = f"Ya pagaron {count}: {', '.join(names)}. Total cobrado: {format_currency(total)}."
        else:
            response = f"Ya pagaron {count} inquilinos. Total cobrado: {format_currency(total)}."

    # -------------------------------------------------------------------------
    # INTENT: contract_info - "¿Cuándo vence el contrato de María?"
    # -------------------------------------------------------------------------
    elif intent_type == "contract_info":
        if not name:
            response = "No capté el nombre. ¿De quién quieres saber el contrato?"
        else:
            # Need full tenant objects for contract dates (not in monthly_status)
            tenants = get_all_tenants()
            tenant = find_tenant_in_list(name, tenants)

            if tenant:
                # Format dates nicely if they exist
                start = tenant.contract_start or "no registrada"
                end = tenant.contract_end or "no registrada"
                
                # Calculate days until expiry if we have an end date
                days_msg = ""
                if tenant.contract_end:
                    try:
                        end_date = datetime.strptime(tenant.contract_end, "%Y-%m-%d")
                        days_until = (end_date - datetime.now()).days
                        if days_until < 0:
                            days_msg = f" (venció hace {-days_until} días)"
                        elif days_until == 0:
                            days_msg = " (¡vence hoy!)"
                        elif days_until <= 30:
                            days_msg = f" (vence en {days_until} días)"
                    except ValueError:
                        pass  # Invalid date format, skip days calculation
                
                response = f"{tenant.name}: Contrato del {start} al {end}{days_msg}."
            else:
                response = f"No encontré a nadie que se llame '{name}'."

    # -------------------------------------------------------------------------
    # INTENT: deposit_owed - "¿Cuánto depósito debemos a Juan?"
    # -------------------------------------------------------------------------
    elif intent_type == "deposit_owed":
        if not name:
            response = "No capté el nombre. ¿De quién quieres saber el depósito?"
        else:
            tenants = get_all_tenants()
            tenant = find_tenant_in_list(name, tenants)

            if tenant:
                # Deposit is typically stored or equals one month's rent
                # Check if there's a deposit_amount field, otherwise use rent
                deposit = getattr(tenant, "deposit_amount", None) or tenant.rent
                response = f"El depósito de {tenant.name} es {format_currency(float(deposit))}."
            else:
                response = f"No encontré a nadie que se llame '{name}'."

    # -------------------------------------------------------------------------
    # INTENT: help - "¿Qué puedes hacer?"
    # -------------------------------------------------------------------------
    elif intent_type == "help":
        response = (
            "Puedo decirte quién ha pagado, quién falta, "
            "fechas de contratos y depósitos. "
            "Pregunta lo que quieras."
        )

    # -------------------------------------------------------------------------
    # INTENT: unknown - Fallback
    # -------------------------------------------------------------------------
    else:
        response = (
            "No entendí. Puedes preguntar: "
            "¿Quiénes no han pagado? o ¿Ya pagó [nombre]?"
        )

    return jsonify({"response": response})

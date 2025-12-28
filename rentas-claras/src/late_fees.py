"""
RentasClaras: Late Fee Calculator
=================================

Implements the Mexican landlord late fee structure:
- Day 1: Rent due (grace period)
- Day 2: Initial penalty of $500 MXN
- Days 3-7: Additional $100 MXN per day
- Day 8+: Contract termination warning territory

Author: RentasClaras Engineering
Date: December 2024
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Optional


class PaymentStatus(Enum):
    """Status of a tenant's payment for the month."""
    PAID = "paid"
    ON_TIME = "on_time"  # Day 1, no penalty yet
    LATE_INITIAL = "late_initial"  # Day 2, $500 penalty
    LATE_ACCUMULATING = "late_accumulating"  # Days 3-7, +$100/day
    CRITICAL = "critical"  # Day 8+, termination warning


class PropertyType(Enum):
    """Types of properties with different billing rules."""
    SHARED_METER = "shared_meter"  # Ensenada, Huichapan
    LANDLORD_SPLIT = "landlord_split"  # Matehuala A (50% landlord)
    INDIVIDUAL = "individual"  # Muzquiz


@dataclass
class LateFeeResult:
    """Result of late fee calculation."""
    base_rent: Decimal
    utilities: Decimal
    days_late: int
    initial_penalty: Decimal
    daily_penalties: Decimal
    total_penalties: Decimal
    total_due: Decimal
    status: PaymentStatus
    warning_message: Optional[str]
    breakdown: str


# =============================================================================
# CONFIGURATION
# =============================================================================

INITIAL_PENALTY_MXN = Decimal("500.00")
DAILY_PENALTY_MXN = Decimal("100.00")
MAX_DAILY_PENALTY_DAYS = 5  # Days 3-7 (5 days of $100)
TERMINATION_WARNING_DAY = 8


# =============================================================================
# CORE CALCULATION
# =============================================================================

def calculate_rentas_claras_balance(
    base_rent: float | Decimal,
    utilities: float | Decimal,
    current_day: int,
    already_paid: float | Decimal = 0
) -> LateFeeResult:
    """
    Calculate the total balance due including late fees.
    
    Business Rules:
    - Day 1: Rent is due (no penalty)
    - Day 2: $500 MXN initial penalty applied
    - Days 3-7: Additional $100 MXN per day delay fee
    - Day 8+: Contract termination warning activated
    
    Args:
        base_rent: Monthly rent amount in MXN
        utilities: Utility charges (luz, agua, etc.) in MXN
        current_day: Day of the month (1-31)
        already_paid: Amount already paid this month
    
    Returns:
        LateFeeResult with complete breakdown
    
    Example:
        >>> result = calculate_rentas_claras_balance(4500, 350, 5)
        >>> print(result.total_due)  # 4500 + 350 + 500 + 300 = 5650
    """
    # Convert to Decimal for precision
    base_rent = Decimal(str(base_rent))
    utilities = Decimal(str(utilities))
    already_paid = Decimal(str(already_paid))
    
    # Initialize penalties
    initial_penalty = Decimal("0.00")
    daily_penalties = Decimal("0.00")
    warning_message = None
    
    # Calculate days late (Day 1 = not late, Day 2+ = late)
    days_late = max(0, current_day - 1)
    
    # Determine status and calculate penalties
    if already_paid >= (base_rent + utilities):
        status = PaymentStatus.PAID
        days_late = 0
    elif current_day == 1:
        status = PaymentStatus.ON_TIME
    elif current_day == 2:
        # Day 2: Initial penalty only
        status = PaymentStatus.LATE_INITIAL
        initial_penalty = INITIAL_PENALTY_MXN
    elif 3 <= current_day <= 7:
        # Days 3-7: Initial + daily accumulation
        status = PaymentStatus.LATE_ACCUMULATING
        initial_penalty = INITIAL_PENALTY_MXN
        daily_penalty_days = current_day - 2  # Days 3=1 day, 4=2 days, etc.
        daily_penalties = DAILY_PENALTY_MXN * daily_penalty_days
    else:
        # Day 8+: Critical - termination warning
        # Daily penalties continue accumulating (Day 3 onwards = current_day - 2)
        status = PaymentStatus.CRITICAL
        initial_penalty = INITIAL_PENALTY_MXN
        daily_penalty_days = current_day - 2  # Days 3+ each add $100
        daily_penalties = DAILY_PENALTY_MXN * daily_penalty_days
        warning_message = (
            "⚠️ AVISO: De acuerdo con su contrato de arrendamiento, "
            "el retraso de más de 7 días en el pago constituye causa de rescisión. "
            "Le solicitamos regularizar su situación de manera inmediata."
        )
    
    # Calculate totals
    total_penalties = initial_penalty + daily_penalties
    subtotal = base_rent + utilities + total_penalties
    total_due = max(Decimal("0.00"), subtotal - already_paid)
    
    # Build breakdown string
    breakdown = _build_breakdown(
        base_rent=base_rent,
        utilities=utilities,
        initial_penalty=initial_penalty,
        daily_penalties=daily_penalties,
        days_late=days_late,
        already_paid=already_paid,
        total_due=total_due,
        current_day=current_day
    )
    
    return LateFeeResult(
        base_rent=base_rent,
        utilities=utilities,
        days_late=days_late,
        initial_penalty=initial_penalty,
        daily_penalties=daily_penalties,
        total_penalties=total_penalties,
        total_due=total_due.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        status=status,
        warning_message=warning_message,
        breakdown=breakdown
    )


def _build_breakdown(
    base_rent: Decimal,
    utilities: Decimal,
    initial_penalty: Decimal,
    daily_penalties: Decimal,
    days_late: int,
    already_paid: Decimal,
    total_due: Decimal,
    current_day: int
) -> str:
    """Build a human-readable breakdown of the charges."""
    lines = [
        f"📋 *Desglose de Adeudo (Día {current_day})*",
        "",
        f"🏠 Renta mensual: ${base_rent:,.2f}",
        f"💡 Servicios: ${utilities:,.2f}",
    ]
    
    if initial_penalty > 0:
        lines.append(f"⚠️ Penalización inicial (Día 2): ${initial_penalty:,.2f}")
    
    if daily_penalties > 0:
        daily_days = int(daily_penalties / DAILY_PENALTY_MXN)
        lines.append(f"📈 Recargo diario ({daily_days} días × $100): ${daily_penalties:,.2f}")
    
    if already_paid > 0:
        lines.append(f"✅ Abonado: -${already_paid:,.2f}")
    
    lines.extend([
        "",
        f"💰 *TOTAL A PAGAR: ${total_due:,.2f} MXN*"
    ])
    
    return "\n".join(lines)


# =============================================================================
# PROPERTY-SPECIFIC CALCULATIONS
# =============================================================================

@dataclass
class PropertyConfig:
    """Configuration for a specific property."""
    property_id: str
    name: str
    property_type: PropertyType
    landlord_utility_share: Decimal = Decimal("0.00")  # For Matehuala A: 0.50


# Property configurations
PROPERTIES = {
    "ensenada": PropertyConfig(
        property_id="ENSENADA",
        name="Ensenada",
        property_type=PropertyType.SHARED_METER,
    ),
    "huichapan": PropertyConfig(
        property_id="HUICHAPAN",
        name="Huichapan",
        property_type=PropertyType.SHARED_METER,
    ),
    "matehuala_a": PropertyConfig(
        property_id="MATEHUALA_A",
        name="Matehuala A",
        property_type=PropertyType.LANDLORD_SPLIT,
        landlord_utility_share=Decimal("0.50"),  # 50% landlord
    ),
    "muzquiz": PropertyConfig(
        property_id="MUZQUIZ",
        name="Múzquiz",
        property_type=PropertyType.INDIVIDUAL,
    ),
}


def calculate_tenant_utilities(
    total_utility_bill: Decimal,
    property_config: PropertyConfig,
    tenants_on_meter: int = 1,
    tenant_days: int = 30,
    period_days: int = 30
) -> Decimal:
    """
    Calculate a tenant's share of utilities based on property type.
    
    Args:
        total_utility_bill: Total CFE/water bill in MXN
        property_config: Property configuration
        tenants_on_meter: Number of tenants sharing the meter
        tenant_days: Days the tenant occupied during period
        period_days: Total days in billing period
    
    Returns:
        Tenant's utility share in MXN
    """
    # Start with base calculation
    base_share = total_utility_bill
    
    # Apply landlord split if applicable (Matehuala A)
    if property_config.property_type == PropertyType.LANDLORD_SPLIT:
        landlord_portion = total_utility_bill * property_config.landlord_utility_share
        base_share = total_utility_bill - landlord_portion
    
    # Pro-rate by days if needed
    if tenant_days < period_days:
        daily_rate = base_share / Decimal(period_days)
        base_share = daily_rate * Decimal(tenant_days)
    
    # Split among tenants on meter (for shared meters)
    if property_config.property_type == PropertyType.SHARED_METER and tenants_on_meter > 1:
        base_share = base_share / Decimal(tenants_on_meter)
    
    return base_share.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# =============================================================================
# MESSAGE GENERATION
# =============================================================================

def generate_payment_request_message(
    tenant_name: str,
    unit: str,
    result: LateFeeResult,
    property_name: str,
    month: str,
    folio: str
) -> str:
    """
    Generate a WhatsApp payment request in Northern Mexican Spanish.
    
    Uses formal "usted" and professional Regio tone.
    """
    # Greeting based on time of day
    hour = datetime.now().hour
    if hour < 12:
        greeting = "Buenos días"
    elif hour < 19:
        greeting = "Buenas tardes"
    else:
        greeting = "Buenas noches"
    
    # Build message
    message = f"""{greeting}, estimado/a inquilino/a de {property_name} {unit}.

Le compartimos el estado de cuenta correspondiente al mes de {month}.

{result.breakdown}

📅 *Fecha de corte:* Día 1 de cada mes

Puede realizar su pago por:
• SPEI a la cuenta registrada
• Retiro sin tarjeta: Envíe el código y monto aquí

"""
    
    # Add warning if in critical status
    if result.warning_message:
        message += f"\n{result.warning_message}\n"
    
    message += f"""
Cualquier duda, con gusto le atendemos.

_Folio: {folio}_"""
    
    return message.strip()


def generate_reminder_message(
    tenant_name: str,
    result: LateFeeResult,
    reminder_type: str = "morning"  # "morning" or "afternoon"
) -> str:
    """
    Generate a reminder message for the 1st of the month.
    
    Args:
        tenant_name: Tenant's name
        result: Late fee calculation result
        reminder_type: "morning" (9 AM) or "afternoon" (4 PM)
    """
    if reminder_type == "morning":
        message = f"""Buenos días.

Le recordamos que hoy es día de pago de renta.

{result.breakdown}

Puede enviar su comprobante de pago o código de retiro por este medio.

Gracias por su puntualidad. 🙏"""
    else:
        message = f"""Buenas tardes.

Solo un recordatorio amable: el pago de renta del mes vence hoy.

💰 *Total a pagar: ${result.total_due:,.2f} MXN*

Si ya realizó su pago, envíenos su comprobante y con gusto actualizamos su estado.

Gracias."""
    
    return message


# =============================================================================
# SUBTOTALS AND TOTALS
# =============================================================================

@dataclass
class PropertySubtotal:
    """Subtotal for a single property across all tenants."""
    property_id: str
    property_name: str
    total_base_rent: Decimal
    total_utilities: Decimal
    total_penalties: Decimal
    total_due: Decimal
    tenant_count: int
    paid_count: int
    late_count: int
    critical_count: int


@dataclass
class GrandTotal:
    """Grand total across all properties."""
    total_base_rent: Decimal
    total_utilities: Decimal
    total_penalties: Decimal
    total_due: Decimal
    property_count: int
    tenant_count: int
    paid_count: int
    late_count: int
    critical_count: int
    subtotals_by_property: dict[str, PropertySubtotal]


def calculate_property_subtotal(
    property_config: PropertyConfig,
    tenant_results: list[LateFeeResult]
) -> PropertySubtotal:
    """
    Calculate subtotal for a single property across all its tenants.
    
    Args:
        property_config: The property configuration
        tenant_results: List of LateFeeResult for each tenant in the property
    
    Returns:
        PropertySubtotal with aggregated values
    """
    total_base_rent = Decimal("0.00")
    total_utilities = Decimal("0.00")
    total_penalties = Decimal("0.00")
    total_due = Decimal("0.00")
    paid_count = 0
    late_count = 0
    critical_count = 0
    
    for result in tenant_results:
        total_base_rent += result.base_rent
        total_utilities += result.utilities
        total_penalties += result.total_penalties
        total_due += result.total_due
        
        if result.status == PaymentStatus.PAID:
            paid_count += 1
        elif result.status == PaymentStatus.CRITICAL:
            critical_count += 1
        elif result.status in (PaymentStatus.LATE_INITIAL, PaymentStatus.LATE_ACCUMULATING):
            late_count += 1
    
    return PropertySubtotal(
        property_id=property_config.property_id,
        property_name=property_config.name,
        total_base_rent=total_base_rent,
        total_utilities=total_utilities,
        total_penalties=total_penalties,
        total_due=total_due,
        tenant_count=len(tenant_results),
        paid_count=paid_count,
        late_count=late_count,
        critical_count=critical_count,
    )


def calculate_grand_total(
    property_subtotals: list[PropertySubtotal]
) -> GrandTotal:
    """
    Calculate grand total across all properties.
    
    Args:
        property_subtotals: List of PropertySubtotal for each property
    
    Returns:
        GrandTotal with aggregated values across all properties
    """
    total_base_rent = Decimal("0.00")
    total_utilities = Decimal("0.00")
    total_penalties = Decimal("0.00")
    total_due = Decimal("0.00")
    tenant_count = 0
    paid_count = 0
    late_count = 0
    critical_count = 0
    subtotals_by_property: dict[str, PropertySubtotal] = {}
    
    for subtotal in property_subtotals:
        total_base_rent += subtotal.total_base_rent
        total_utilities += subtotal.total_utilities
        total_penalties += subtotal.total_penalties
        total_due += subtotal.total_due
        tenant_count += subtotal.tenant_count
        paid_count += subtotal.paid_count
        late_count += subtotal.late_count
        critical_count += subtotal.critical_count
        subtotals_by_property[subtotal.property_id] = subtotal
    
    return GrandTotal(
        total_base_rent=total_base_rent,
        total_utilities=total_utilities,
        total_penalties=total_penalties,
        total_due=total_due,
        property_count=len(property_subtotals),
        tenant_count=tenant_count,
        paid_count=paid_count,
        late_count=late_count,
        critical_count=critical_count,
        subtotals_by_property=subtotals_by_property,
    )


def format_property_subtotal(subtotal: PropertySubtotal) -> str:
    """
    Format a property subtotal for display.
    
    Args:
        subtotal: PropertySubtotal to format
    
    Returns:
        Formatted string for display
    """
    lines = [
        f"🏠 *{subtotal.property_name}*",
        f"   📊 Inquilinos: {subtotal.tenant_count}",
        f"   ✅ Pagados: {subtotal.paid_count}",
        f"   ⏳ Con retraso: {subtotal.late_count}",
    ]
    
    if subtotal.critical_count > 0:
        lines.append(f"   ⚠️ Críticos: {subtotal.critical_count}")
    
    lines.extend([
        "",
        f"   💵 Renta base: ${subtotal.total_base_rent:,.2f}",
        f"   💡 Servicios: ${subtotal.total_utilities:,.2f}",
        f"   📈 Penalizaciones: ${subtotal.total_penalties:,.2f}",
        f"   💰 *Subtotal: ${subtotal.total_due:,.2f} MXN*",
    ])
    
    return "\n".join(lines)


def format_grand_total(grand_total: GrandTotal) -> str:
    """
    Format the grand total for display.
    
    Args:
        grand_total: GrandTotal to format
    
    Returns:
        Formatted string with property subtotals and grand total
    """
    lines = [
        "=" * 50,
        "📊 *RESUMEN DE COBRANZA*",
        "=" * 50,
        "",
    ]
    
    # Add each property subtotal
    for subtotal in grand_total.subtotals_by_property.values():
        lines.append(format_property_subtotal(subtotal))
        lines.append("")
    
    # Add grand total
    collection_rate = (
        (grand_total.paid_count / grand_total.tenant_count * 100)
        if grand_total.tenant_count > 0
        else 0
    )
    
    lines.extend([
        "=" * 50,
        "🏦 *TOTAL GENERAL*",
        "=" * 50,
        "",
        f"🏠 Propiedades: {grand_total.property_count}",
        f"👥 Total inquilinos: {grand_total.tenant_count}",
        f"✅ Pagados: {grand_total.paid_count} ({collection_rate:.1f}%)",
        f"⏳ Con retraso: {grand_total.late_count}",
        f"⚠️ Críticos: {grand_total.critical_count}",
        "",
        f"💵 Total renta base: ${grand_total.total_base_rent:,.2f}",
        f"💡 Total servicios: ${grand_total.total_utilities:,.2f}",
        f"📈 Total penalizaciones: ${grand_total.total_penalties:,.2f}",
        "",
        f"💰 *GRAN TOTAL A COBRAR: ${grand_total.total_due:,.2f} MXN*",
    ])
    
    return "\n".join(lines)


# =============================================================================
# DEMO
# =============================================================================

def run_late_fee_demo():
    """Demonstrate the late fee calculator with various scenarios."""
    print("=" * 70)
    print("🏠 RENTASCLARAS - Late Fee Calculator Demo")
    print("=" * 70)
    print()
    
    base_rent = 4500.00
    utilities = 350.00
    
    test_cases = [
        (1, "Day 1 - On time (no penalty)"),
        (2, "Day 2 - Initial penalty ($500)"),
        (3, "Day 3 - Initial + 1 day ($500 + $100)"),
        (5, "Day 5 - Initial + 3 days ($500 + $300)"),
        (7, "Day 7 - Initial + 5 days ($500 + $500)"),
        (8, "Day 8 - CRITICAL (termination warning)"),
        (15, "Day 15 - CRITICAL (penalties capped)"),
    ]
    
    for day, description in test_cases:
        result = calculate_rentas_claras_balance(base_rent, utilities, day)
        
        print(f"📅 {description}")
        print(f"   Status: {result.status.value}")
        print(f"   Base: ${result.base_rent:,.2f} + Utilities: ${result.utilities:,.2f}")
        print(f"   Penalties: ${result.total_penalties:,.2f}")
        print(f"   → TOTAL: ${result.total_due:,.2f} MXN")
        if result.warning_message:
            print(f"   ⚠️  {result.warning_message[:60]}...")
        print()
    
    # Demo with partial payment
    print("=" * 70)
    print("💳 PARTIAL PAYMENT SCENARIO")
    print("=" * 70)
    print()
    
    result = calculate_rentas_claras_balance(base_rent, utilities, 5, already_paid=2000)
    print(f"Day 5, with $2,000 already paid:")
    print(f"   Full amount would be: ${Decimal(str(base_rent)) + Decimal(str(utilities)) + result.total_penalties:,.2f}")
    print(f"   Already paid: $2,000.00")
    print(f"   → REMAINING: ${result.total_due:,.2f} MXN")
    print()
    
    # Demo Matehuala A (50% landlord split)
    print("=" * 70)
    print("🏠 MATEHUALA A - 50% Landlord Split Demo")
    print("=" * 70)
    print()
    
    matehuala_config = PROPERTIES["matehuala_a"]
    total_bill = Decimal("1200.00")
    tenant_share = calculate_tenant_utilities(
        total_utility_bill=total_bill,
        property_config=matehuala_config
    )
    
    print(f"Total CFE Bill: ${total_bill:,.2f}")
    print(f"Landlord pays 50%: ${total_bill * Decimal('0.50'):,.2f}")
    print(f"Tenant pays 50%: ${tenant_share:,.2f}")
    print()
    
    # Generate sample WhatsApp message
    print("=" * 70)
    print("📱 SAMPLE WHATSAPP MESSAGE")
    print("=" * 70)
    print()
    
    result = calculate_rentas_claras_balance(4500, 350, 5)
    message = generate_payment_request_message(
        tenant_name="María González",
        unit="Unidad 3",
        result=result,
        property_name="Ensenada",
        month="Enero 2025",
        folio="RC-20250105-00001"
    )
    print(message)


def run_subtotals_demo():
    """Demonstrate the subtotals and grand total functionality."""
    print()
    print("=" * 70)
    print("📊 SUBTOTALS & GRAND TOTAL DEMO")
    print("=" * 70)
    print()
    
    # Simulate tenant results for Ensenada
    ensenada_results = [
        calculate_rentas_claras_balance(4500, 350, 1),   # On time
        calculate_rentas_claras_balance(4500, 350, 5),   # Late
        calculate_rentas_claras_balance(4500, 350, 1, already_paid=4850),  # Paid
    ]
    
    # Simulate tenant results for Huichapan
    huichapan_results = [
        calculate_rentas_claras_balance(3800, 280, 2),   # Initial penalty
        calculate_rentas_claras_balance(3800, 280, 10),  # Critical
    ]
    
    # Simulate tenant results for Matehuala A
    matehuala_results = [
        calculate_rentas_claras_balance(5200, 400, 1, already_paid=5600),  # Paid
        calculate_rentas_claras_balance(5200, 400, 3),   # Late accumulating
    ]
    
    # Calculate subtotals for each property
    ensenada_subtotal = calculate_property_subtotal(
        PROPERTIES["ensenada"],
        ensenada_results
    )
    huichapan_subtotal = calculate_property_subtotal(
        PROPERTIES["huichapan"],
        huichapan_results
    )
    matehuala_subtotal = calculate_property_subtotal(
        PROPERTIES["matehuala_a"],
        matehuala_results
    )
    
    # Calculate grand total
    grand_total = calculate_grand_total([
        ensenada_subtotal,
        huichapan_subtotal,
        matehuala_subtotal
    ])
    
    # Display formatted summary
    print(format_grand_total(grand_total))


if __name__ == "__main__":
    run_late_fee_demo()
    run_subtotals_demo()

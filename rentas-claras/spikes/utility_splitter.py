"""
RentasClaras Technical Spike: Utility Splitter Module
======================================================

This spike models the Ensenada property (9 units, 7 meters) and implements
the pro-rata utility splitting logic for CFE bills.

Key Features:
- Pro-rating by exact days of occupancy
- Handles mid-cycle move-ins and move-outs
- Generates WhatsApp-ready messages in Northern Mexican Spanish
- Flexible meter-to-unit mapping

Author: RentasClaras Engineering
Date: December 2024
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional
from decimal import Decimal, ROUND_HALF_UP


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class Tenant:
    """Represents a tenant in the property."""
    tenant_id: str
    name: str
    unit_id: str
    phone: str  # WhatsApp number
    move_in_date: date
    move_out_date: Optional[date] = None  # None = still residing
    
    @property
    def is_active(self) -> bool:
        """Check if tenant is currently active (not moved out)."""
        return self.move_out_date is None or self.move_out_date >= date.today()


@dataclass
class Meter:
    """Represents a CFE electricity meter."""
    meter_id: str
    cfe_number: str
    unit_ids: list[str]  # Units connected to this meter


@dataclass
class Property:
    """Represents a rental property with multiple units and meters."""
    property_id: str
    name: str
    meters: list[Meter]
    
    def get_meter_for_unit(self, unit_id: str) -> Optional[Meter]:
        """Find which meter a unit is connected to."""
        for meter in self.meters:
            if unit_id in meter.unit_ids:
                return meter
        return None


@dataclass
class BillPhotoData:
    """
    Represents extracted data from a CFE bill photo.
    In production, this would come from Vision OCR (GPT-4V).
    """
    meter_cfe_number: str
    total_amount: Decimal
    period_start: date
    period_end: date
    kwh_consumed: int
    extraction_confidence: float = 1.0  # OCR confidence score


@dataclass
class TenantSplit:
    """Result of splitting a bill for one tenant."""
    tenant: Tenant
    days_in_period: int
    days_occupied: int
    tenants_sharing_meter: int
    amount_owed: Decimal
    calculation_breakdown: str


# =============================================================================
# ENSENADA PROPERTY MODEL (9 units, 7 meters)
# =============================================================================

def create_ensenada_property() -> Property:
    """
    Creates the Ensenada property model.
    
    Configuration:
    - 9 units total
    - 7 meters (some meters serve multiple units)
    
    Meter mapping:
    - ENS-M1: Units 1, 2 (shared)
    - ENS-M2: Unit 3 (individual)
    - ENS-M3: Units 4, 5 (shared)
    - ENS-M4: Unit 6 (individual)
    - ENS-M5: Unit 7 (individual)
    - ENS-M6: Unit 8 (individual)
    - ENS-M7: Unit 9 (individual)
    """
    meters = [
        Meter(meter_id="ENS-M1", cfe_number="CFE-001-MTY-2024", unit_ids=["ENS-1", "ENS-2"]),
        Meter(meter_id="ENS-M2", cfe_number="CFE-002-MTY-2024", unit_ids=["ENS-3"]),
        Meter(meter_id="ENS-M3", cfe_number="CFE-003-MTY-2024", unit_ids=["ENS-4", "ENS-5"]),
        Meter(meter_id="ENS-M4", cfe_number="CFE-004-MTY-2024", unit_ids=["ENS-6"]),
        Meter(meter_id="ENS-M5", cfe_number="CFE-005-MTY-2024", unit_ids=["ENS-7"]),
        Meter(meter_id="ENS-M6", cfe_number="CFE-006-MTY-2024", unit_ids=["ENS-8"]),
        Meter(meter_id="ENS-M7", cfe_number="CFE-007-MTY-2024", unit_ids=["ENS-9"]),
    ]
    
    return Property(
        property_id="ENSENADA",
        name="Ensenada",
        meters=meters
    )


def create_dummy_tenant_registry() -> dict[str, Tenant]:
    """
    Creates dummy tenant data for the Ensenada property.
    
    Scenarios covered:
    - Full period occupancy (most tenants)
    - Mid-cycle move-in (Tenant in ENS-2)
    - Mid-cycle move-out (Tenant in ENS-5)
    - Empty unit (ENS-9 - no tenant)
    """
    tenants = [
        # ENS-M1: Shared meter (Units 1, 2)
        Tenant(
            tenant_id="T-001",
            name="María González Rodríguez",
            unit_id="ENS-1",
            phone="+528112345001",
            move_in_date=date(2024, 1, 15),  # Full period
        ),
        Tenant(
            tenant_id="T-002",
            name="Dr. Carlos Mendoza Leyva",
            unit_id="ENS-2",
            phone="+528112345002",
            move_in_date=date(2024, 11, 20),  # Mid-cycle move-in (day 20 of 60)
        ),
        
        # ENS-M2: Individual meter (Unit 3)
        Tenant(
            tenant_id="T-003",
            name="Ana Sofía Treviño",
            unit_id="ENS-3",
            phone="+528112345003",
            move_in_date=date(2024, 6, 1),  # Full period
        ),
        
        # ENS-M3: Shared meter (Units 4, 5)
        Tenant(
            tenant_id="T-004",
            name="Roberto Garza Elizondo",
            unit_id="ENS-4",
            phone="+528112345004",
            move_in_date=date(2024, 3, 10),  # Full period
        ),
        Tenant(
            tenant_id="T-005",
            name="Lic. Patricia Salinas",
            unit_id="ENS-5",
            phone="+528112345005",
            move_in_date=date(2024, 2, 1),
            move_out_date=date(2024, 11, 15),  # Mid-cycle move-out (day 15 of 60)
        ),
        
        # ENS-M4: Individual meter (Unit 6)
        Tenant(
            tenant_id="T-006",
            name="Fernando Villarreal",
            unit_id="ENS-6",
            phone="+528112345006",
            move_in_date=date(2024, 8, 1),  # Full period
        ),
        
        # ENS-M5: Individual meter (Unit 7)
        Tenant(
            tenant_id="T-007",
            name="Dra. Lucía Cantú Reyes",
            unit_id="ENS-7",
            phone="+528112345007",
            move_in_date=date(2024, 5, 15),  # Full period
        ),
        
        # ENS-M6: Individual meter (Unit 8)
        Tenant(
            tenant_id="T-008",
            name="Ing. Miguel Ángel Flores",
            unit_id="ENS-8",
            phone="+528112345008",
            move_in_date=date(2024, 4, 1),  # Full period
        ),
        
        # ENS-M9: Individual meter (Unit 9) - VACANT
        # No tenant registered
    ]
    
    return {t.tenant_id: t for t in tenants}


# =============================================================================
# CORE CALCULATION LOGIC
# =============================================================================

def calculate_days_occupied(
    tenant: Tenant,
    period_start: date,
    period_end: date
) -> int:
    """
    Calculate how many days a tenant occupied their unit during the billing period.
    
    Handles:
    - Tenant moved in before period: full period or until move-out
    - Tenant moved in during period: from move-in to period end or move-out
    - Tenant moved out during period: from period start or move-in to move-out
    - Tenant not in period: 0 days
    """
    # Determine effective occupancy window within the billing period
    effective_start = max(period_start, tenant.move_in_date)
    
    if tenant.move_out_date:
        effective_end = min(period_end, tenant.move_out_date)
    else:
        effective_end = period_end
    
    # If tenant wasn't present during this period
    if effective_start > effective_end:
        return 0
    
    # +1 because both start and end days are inclusive
    return (effective_end - effective_start).days + 1


def calculate_tenant_share(
    bill_total: Decimal,
    period_days: int,
    days_occupied: int,
    tenants_on_meter: int
) -> Decimal:
    """
    Calculate a tenant's share of the utility bill.
    
    Formula: (Bill Total / Period Days) × Days Occupied / Tenants on Meter
    
    Uses Decimal for precise currency calculations.
    """
    if period_days == 0 or tenants_on_meter == 0:
        return Decimal("0.00")
    
    daily_rate = bill_total / Decimal(period_days)
    tenant_share = (daily_rate * Decimal(days_occupied)) / Decimal(tenants_on_meter)
    
    # Round to 2 decimal places (centavos)
    return tenant_share.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def generate_payment_message(
    tenant: Tenant,
    split: TenantSplit,
    period_start: date,
    period_end: date,
    property_name: str,
    folio: str,
    clabe: str = "012180001234567890"  # Dummy CLABE
) -> str:
    """
    Generate a WhatsApp payment request message in Northern Mexican Spanish.
    
    Uses formal "usted" tone as specified in the PRD.
    """
    # Format dates in Spanish
    period_str = f"{period_start.strftime('%d %b')} - {period_end.strftime('%d %b, %Y')}"
    
    # Calculate payment deadline (7 days from today)
    deadline = date.today().replace(day=min(date.today().day + 7, 28))
    deadline_str = deadline.strftime("%d de %B, %Y").replace("January", "enero").replace(
        "February", "febrero").replace("March", "marzo").replace("April", "abril").replace(
        "May", "mayo").replace("June", "junio").replace("July", "julio").replace(
        "August", "agosto").replace("September", "septiembre").replace("October", "octubre").replace(
        "November", "noviembre").replace("December", "diciembre")
    
    # Build message
    message = f"""Buenos días, estimado/a inquilino/a de {property_name} Unidad {tenant.unit_id.split('-')[1]}.

Le compartimos el desglose de su parte proporcional del recibo de luz (CFE) correspondiente al periodo {period_str}.

📊 *Desglose:*
• Días del periodo: {split.days_in_period}
• Sus días de ocupación: {split.days_occupied}
• Inquilinos en su medidor: {split.tenants_sharing_meter}

{split.calculation_breakdown}

💰 *Su parte proporcional: ${split.amount_owed:,.2f} MXN*

📅 Fecha límite de pago: {deadline_str}

Puede realizar su pago por:
• SPEI: {clabe}
• Retiro sin tarjeta: Envíe el código aquí

Cualquier duda, con gusto le atendemos.

_Folio: {folio}_"""
    
    return message


# =============================================================================
# MAIN CALCULATION FUNCTION
# =============================================================================

def calculate_splits(
    bill_photo_data: BillPhotoData,
    tenant_registry: dict[str, Tenant],
    property_config: Property
) -> dict[str, str]:
    """
    Main function to split a utility bill among tenants.
    
    Args:
        bill_photo_data: Extracted data from CFE bill (from Vision OCR)
        tenant_registry: Dictionary of tenant_id -> Tenant
        property_config: Property configuration with meter mappings
    
    Returns:
        Dictionary of {tenant_name: whatsapp_message}
    """
    results: dict[str, str] = {}
    
    # Find which meter this bill is for
    target_meter = None
    for meter in property_config.meters:
        if meter.cfe_number == bill_photo_data.meter_cfe_number:
            target_meter = meter
            break
    
    if not target_meter:
        raise ValueError(f"No meter found for CFE number: {bill_photo_data.meter_cfe_number}")
    
    # Calculate period days
    period_days = (bill_photo_data.period_end - bill_photo_data.period_start).days + 1
    
    # Find all tenants on this meter
    tenants_on_meter = [
        tenant for tenant in tenant_registry.values()
        if tenant.unit_id in target_meter.unit_ids
    ]
    
    # Filter to only tenants who were present during the billing period
    active_tenants = [
        tenant for tenant in tenants_on_meter
        if calculate_days_occupied(tenant, bill_photo_data.period_start, bill_photo_data.period_end) > 0
    ]
    
    if not active_tenants:
        print(f"⚠️  No active tenants found for meter {target_meter.meter_id}")
        return results
    
    # Calculate splits for each tenant
    folio_counter = 1
    for tenant in active_tenants:
        days_occupied = calculate_days_occupied(
            tenant,
            bill_photo_data.period_start,
            bill_photo_data.period_end
        )
        
        amount_owed = calculate_tenant_share(
            bill_total=bill_photo_data.total_amount,
            period_days=period_days,
            days_occupied=days_occupied,
            tenants_on_meter=len(active_tenants)
        )
        
        # Build calculation breakdown for transparency
        daily_rate = bill_photo_data.total_amount / Decimal(period_days)
        breakdown = f"""📐 *Cálculo:*
• Total del recibo: ${bill_photo_data.total_amount:,.2f}
• Tarifa diaria: ${daily_rate:,.2f}
• ({days_occupied} días × ${daily_rate:,.2f}) ÷ {len(active_tenants)} inquilinos"""
        
        split = TenantSplit(
            tenant=tenant,
            days_in_period=period_days,
            days_occupied=days_occupied,
            tenants_sharing_meter=len(active_tenants),
            amount_owed=amount_owed,
            calculation_breakdown=breakdown
        )
        
        # Generate folio
        folio = f"RC-{datetime.now().strftime('%Y%m%d')}-{folio_counter:05d}"
        folio_counter += 1
        
        # Generate WhatsApp message
        message = generate_payment_message(
            tenant=tenant,
            split=split,
            period_start=bill_photo_data.period_start,
            period_end=bill_photo_data.period_end,
            property_name=property_config.name,
            folio=folio
        )
        
        results[tenant.name] = message
    
    return results


# =============================================================================
# DEMO / TESTING
# =============================================================================

def run_spike_demo():
    """
    Demonstrates the utility splitter with sample data.
    
    Simulates a 60-day billing cycle (Nov 1 - Dec 30, 2024) for meter ENS-M1
    which serves Units 1 and 2.
    
    Scenarios tested:
    - Tenant 1 (María): Full 60-day occupancy
    - Tenant 2 (Dr. Carlos): Mid-cycle move-in on Nov 20 (40 days)
    """
    print("=" * 70)
    print("🏠 RENTASCLARAS - Utility Splitter Technical Spike")
    print("=" * 70)
    print()
    
    # Setup
    property_config = create_ensenada_property()
    tenant_registry = create_dummy_tenant_registry()
    
    # Simulate a 60-day bill for meter ENS-M1 (Units 1 & 2)
    bill_data = BillPhotoData(
        meter_cfe_number="CFE-001-MTY-2024",
        total_amount=Decimal("3600.00"),  # $3,600 MXN for 60 days
        period_start=date(2024, 11, 1),
        period_end=date(2024, 12, 30),
        kwh_consumed=720,
        extraction_confidence=0.98
    )
    
    print(f"📋 Bill Data (from OCR):")
    print(f"   Meter: {bill_data.meter_cfe_number}")
    print(f"   Total: ${bill_data.total_amount:,.2f} MXN")
    print(f"   Period: {bill_data.period_start} to {bill_data.period_end}")
    print(f"   kWh: {bill_data.kwh_consumed}")
    print(f"   OCR Confidence: {bill_data.extraction_confidence:.0%}")
    print()
    
    # Calculate splits
    print("⚡ Calculating splits...")
    print()
    
    results = calculate_splits(bill_data, tenant_registry, property_config)
    
    # Display results
    print("=" * 70)
    print("📤 GENERATED WHATSAPP MESSAGES")
    print("=" * 70)
    
    for tenant_name, message in results.items():
        print()
        print(f"👤 {tenant_name}")
        print("-" * 50)
        print(message)
        print()
    
    # Summary
    print("=" * 70)
    print("📊 SPLIT SUMMARY")
    print("=" * 70)
    
    # Quick verification
    print()
    print("Expected behavior for ENS-M1 (60-day cycle, $3,600 bill):")
    print()
    print("  • María (ENS-1): 60 days → ($60/day × 60) ÷ 2 = $1,800.00")
    print("  • Dr. Carlos (ENS-2): 40 days (moved in Nov 20)")
    print("    → ($60/day × 40) ÷ 2 = $1,200.00")
    print()
    print("  Total collected: $3,000.00")
    print("  Unoccupied days cost (absorbed by landlord): $600.00")
    print()
    
    # Test another meter with mid-cycle move-out
    print("=" * 70)
    print("🧪 TEST CASE: Mid-cycle Move-Out (Meter ENS-M3)")
    print("=" * 70)
    print()
    
    bill_data_m3 = BillPhotoData(
        meter_cfe_number="CFE-003-MTY-2024",
        total_amount=Decimal("2400.00"),
        period_start=date(2024, 11, 1),
        period_end=date(2024, 12, 30),
        kwh_consumed=480,
        extraction_confidence=0.95
    )
    
    results_m3 = calculate_splits(bill_data_m3, tenant_registry, property_config)
    
    for tenant_name, message in results_m3.items():
        print(f"👤 {tenant_name}")
        print("-" * 50)
        print(message)
        print()
    
    print("Expected behavior for ENS-M3 (60-day cycle, $2,400 bill):")
    print()
    print("  • Roberto (ENS-4): 60 days → ($40/day × 60) ÷ 2 = $1,200.00")
    print("  • Patricia (ENS-5): 15 days (moved out Nov 15)")
    print("    → ($40/day × 15) ÷ 2 = $300.00")
    print()


if __name__ == "__main__":
    run_spike_demo()

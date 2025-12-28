"""
RentasClaras: Payment Reminder Scheduler
=========================================

Handles scheduled reminders for rent collection:
- Morning reminder (9 AM CST) on the 1st of each month
- Afternoon reminder (4 PM CST) on the 1st of each month
- Late payment escalation (Days 2-8+)

Designed to work with:
- Cron jobs (simple deployment)
- APScheduler (Python-native)
- AWS Lambda + EventBridge (serverless)
- Cloud Functions + Cloud Scheduler (GCP)

Author: RentasClaras Engineering
Date: December 2024
"""

from dataclasses import dataclass
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional, Callable
from zoneinfo import ZoneInfo

# Mexico Central Time
MEXICO_TZ = ZoneInfo("America/Mexico_City")


class ReminderType(Enum):
    """Types of automated reminders."""
    MORNING_DAY_1 = "morning_day_1"  # 9 AM on 1st
    AFTERNOON_DAY_1 = "afternoon_day_1"  # 4 PM on 1st
    LATE_DAY_2 = "late_day_2"  # Day 2: Initial penalty applied
    LATE_DAY_3 = "late_day_3"  # Day 3: First daily penalty
    LATE_DAY_5 = "late_day_5"  # Day 5: Midweek reminder
    LATE_DAY_7 = "late_day_7"  # Day 7: Final warning before termination
    CRITICAL_DAY_8 = "critical_day_8"  # Day 8: Termination notice
    CODE_EXPIRY = "code_expiry"  # 2 hours before withdrawal code expires


@dataclass
class ScheduledReminder:
    """Represents a scheduled reminder to be sent."""
    reminder_type: ReminderType
    scheduled_time: datetime
    tenant_id: str
    tenant_name: str
    tenant_phone: str
    property_name: str
    unit: str
    amount_due: Decimal
    message: Optional[str] = None
    sent: bool = False
    sent_at: Optional[datetime] = None


@dataclass
class ReminderConfig:
    """Configuration for the reminder scheduler."""
    morning_hour: int = 9  # 9 AM
    morning_minute: int = 0
    afternoon_hour: int = 16  # 4 PM
    afternoon_minute: int = 0
    timezone: ZoneInfo = MEXICO_TZ
    
    # Late payment reminder schedule
    late_reminder_days: list[int] = None
    
    def __post_init__(self):
        if self.late_reminder_days is None:
            self.late_reminder_days = [2, 3, 5, 7, 8]


# =============================================================================
# SCHEDULE CALCULATION
# =============================================================================

def get_next_first_of_month(from_date: Optional[date] = None) -> date:
    """Get the next 1st of the month."""
    if from_date is None:
        from_date = date.today()
    
    if from_date.day == 1:
        return from_date
    
    # Move to next month
    if from_date.month == 12:
        return date(from_date.year + 1, 1, 1)
    else:
        return date(from_date.year, from_date.month + 1, 1)


def get_morning_reminder_time(
    target_date: date,
    config: ReminderConfig = None
) -> datetime:
    """Get the morning reminder datetime for a specific date."""
    if config is None:
        config = ReminderConfig()
    
    return datetime(
        target_date.year,
        target_date.month,
        target_date.day,
        config.morning_hour,
        config.morning_minute,
        tzinfo=config.timezone
    )


def get_afternoon_reminder_time(
    target_date: date,
    config: ReminderConfig = None
) -> datetime:
    """Get the afternoon reminder datetime for a specific date."""
    if config is None:
        config = ReminderConfig()
    
    return datetime(
        target_date.year,
        target_date.month,
        target_date.day,
        config.afternoon_hour,
        config.afternoon_minute,
        tzinfo=config.timezone
    )


def get_late_reminder_times(
    first_of_month: date,
    config: ReminderConfig = None
) -> dict[int, datetime]:
    """
    Get reminder times for late payment days.
    
    Returns dict of {day_number: reminder_datetime}
    """
    if config is None:
        config = ReminderConfig()
    
    reminders = {}
    for day in config.late_reminder_days:
        reminder_date = first_of_month + timedelta(days=day - 1)
        reminders[day] = datetime(
            reminder_date.year,
            reminder_date.month,
            reminder_date.day,
            config.morning_hour,
            config.morning_minute,
            tzinfo=config.timezone
        )
    
    return reminders


# =============================================================================
# CRON EXPRESSIONS
# =============================================================================

def get_cron_expressions() -> dict[str, str]:
    """
    Get cron expressions for all reminder types.
    
    For use with system cron, APScheduler, or cloud schedulers.
    
    Format: minute hour day month weekday
    """
    return {
        "morning_day_1": "0 9 1 * *",  # 9:00 AM on 1st of every month
        "afternoon_day_1": "0 16 1 * *",  # 4:00 PM on 1st of every month
        "late_day_2": "0 9 2 * *",  # 9:00 AM on 2nd
        "late_day_3": "0 9 3 * *",  # 9:00 AM on 3rd
        "late_day_5": "0 9 5 * *",  # 9:00 AM on 5th
        "late_day_7": "0 9 7 * *",  # 9:00 AM on 7th
        "critical_day_8": "0 9 8 * *",  # 9:00 AM on 8th
        "code_expiry_check": "*/30 * * * *",  # Every 30 minutes (for code expiry)
    }


def generate_crontab() -> str:
    """
    Generate a crontab file content for the reminder system.
    
    Usage:
        crontab -e
        # paste output
    """
    crons = get_cron_expressions()
    
    crontab = """# RentasClaras Payment Reminder Scheduler
# Generated: {timestamp}
# Timezone: America/Mexico_City (CST/CDT)

# Set timezone
TZ=America/Mexico_City

# Morning reminder - 1st of month at 9 AM
{morning_day_1} /usr/bin/python3 /path/to/rentas-claras/src/scheduler.py --trigger morning_day_1

# Afternoon reminder - 1st of month at 4 PM
{afternoon_day_1} /usr/bin/python3 /path/to/rentas-claras/src/scheduler.py --trigger afternoon_day_1

# Late payment reminders
{late_day_2} /usr/bin/python3 /path/to/rentas-claras/src/scheduler.py --trigger late_day_2
{late_day_3} /usr/bin/python3 /path/to/rentas-claras/src/scheduler.py --trigger late_day_3
{late_day_5} /usr/bin/python3 /path/to/rentas-claras/src/scheduler.py --trigger late_day_5
{late_day_7} /usr/bin/python3 /path/to/rentas-claras/src/scheduler.py --trigger late_day_7
{critical_day_8} /usr/bin/python3 /path/to/rentas-claras/src/scheduler.py --trigger critical_day_8

# Code expiry check - every 30 minutes
{code_expiry_check} /usr/bin/python3 /path/to/rentas-claras/src/scheduler.py --trigger code_expiry_check
""".format(
        timestamp=datetime.now(MEXICO_TZ).isoformat(),
        **crons
    )
    
    return crontab


# =============================================================================
# MESSAGE TEMPLATES
# =============================================================================

def get_reminder_message(
    reminder_type: ReminderType,
    tenant_name: str,
    amount_due: Decimal,
    property_name: str,
    unit: str,
    month: str
) -> str:
    """
    Get the appropriate message for a reminder type.
    
    All messages use formal "usted" and professional Regio tone.
    """
    messages = {
        ReminderType.MORNING_DAY_1: f"""Buenos días.

Le recordamos que hoy es día de pago de renta correspondiente al mes de {month}.

🏠 Propiedad: {property_name} {unit}
💰 Total a pagar: ${amount_due:,.2f} MXN

Puede realizar su pago por:
• SPEI a la cuenta registrada
• Retiro sin tarjeta: Envíe el código aquí

Gracias por su puntualidad. 🙏""",

        ReminderType.AFTERNOON_DAY_1: f"""Buenas tardes.

Solo un recordatorio amable: el pago de renta del mes de {month} vence hoy.

💰 Total a pagar: ${amount_due:,.2f} MXN

Si ya realizó su pago, envíenos su comprobante y con gusto actualizamos su estado.

Gracias.""",

        ReminderType.LATE_DAY_2: f"""Buenos días.

Le informamos que el pago de renta correspondiente a {month} no ha sido registrado.

A partir de hoy se ha aplicado una penalización inicial de $500.00 MXN de acuerdo con su contrato.

💰 Nuevo total: ${amount_due:,.2f} MXN

Le sugerimos regularizar su situación lo antes posible para evitar cargos adicionales.

Gracias.""",

        ReminderType.LATE_DAY_3: f"""Buenos días.

Continuamos sin recibir su pago de renta de {month}.

⚠️ Recargo adicional de $100.00 MXN aplicado hoy.

💰 Total acumulado: ${amount_due:,.2f} MXN

Recuerde que se aplica un recargo de $100.00 diarios hasta el día 7.

Quedamos a sus órdenes para cualquier aclaración.""",

        ReminderType.LATE_DAY_5: f"""Buenos días.

Este es un recordatorio sobre su adeudo pendiente de {month}.

💰 Total acumulado: ${amount_due:,.2f} MXN
📅 Días de retraso: 4

Le recordamos que el día 8 se activa el aviso formal de rescisión de contrato.

Agradecemos su pronta atención a este asunto.""",

        ReminderType.LATE_DAY_7: f"""Buenos días.

⚠️ *AVISO IMPORTANTE*

Mañana se cumple el plazo establecido en su contrato para el pago de renta.

💰 Total acumulado: ${amount_due:,.2f} MXN
📅 Días de retraso: 6

De no recibir su pago el día de hoy, mañana se emitirá un aviso formal que podría derivar en la rescisión de su contrato de arrendamiento.

Le solicitamos regularizar su situación de manera inmediata.

Quedamos a sus órdenes.""",

        ReminderType.CRITICAL_DAY_8: f"""Estimado/a inquilino/a:

📋 *AVISO FORMAL DE ADEUDO*

De acuerdo con las cláusulas de su contrato de arrendamiento, le informamos formalmente que su adeudo ha excedido el plazo máximo de tolerancia.

🏠 Propiedad: {property_name} {unit}
💰 Monto adeudado: ${amount_due:,.2f} MXN
📅 Días de retraso: 7+

Este documento constituye un aviso formal que forma parte de su expediente de arrendamiento.

De acuerdo con la legislación vigente en Nuevo León, este retraso constituye causa de rescisión contractual.

Le solicitamos comunicarse con la administración de manera inmediata para acordar la regularización de su situación.

Atentamente,
Administración {property_name}""",
    }
    
    return messages.get(reminder_type, "")


def get_code_expiry_alert(
    code: str,
    amount: Decimal,
    bank: str,
    tenant_name: str,
    unit: str,
    expires_at: datetime
) -> str:
    """Generate an expiry alert for landlord."""
    time_remaining = expires_at - datetime.now(MEXICO_TZ)
    hours = int(time_remaining.total_seconds() // 3600)
    minutes = int((time_remaining.total_seconds() % 3600) // 60)
    
    return f"""⏰ *CÓDIGO POR VENCER*

👤 Inquilino: {tenant_name} ({unit})
🏦 Banco: {bank}
🔢 Código: {code}
💰 Monto: ${amount:,.2f} MXN
⏰ Vence en: {hours}h {minutes}m

¡Cobra este código antes de que expire!

Responde "Retiré {code[:6]}" cuando lo cobres."""


# =============================================================================
# SCHEDULER LOGIC
# =============================================================================

class ReminderScheduler:
    """
    Main scheduler class for payment reminders.
    
    Can be used with:
    - Direct execution (cron-based)
    - APScheduler (for Python-native scheduling)
    - Cloud Functions (serverless)
    """
    
    def __init__(
        self,
        config: ReminderConfig = None,
        send_message_fn: Callable[[str, str], bool] = None,
        get_tenants_fn: Callable[[], list] = None,
        get_pending_codes_fn: Callable[[], list] = None
    ):
        """
        Initialize the scheduler.
        
        Args:
            config: Reminder configuration
            send_message_fn: Function to send WhatsApp message (phone, message) -> success
            get_tenants_fn: Function to get list of tenants from Excel
            get_pending_codes_fn: Function to get pending withdrawal codes
        """
        self.config = config or ReminderConfig()
        self.send_message = send_message_fn or self._dummy_send
        self.get_tenants = get_tenants_fn or self._dummy_get_tenants
        self.get_pending_codes = get_pending_codes_fn or self._dummy_get_codes
    
    def _dummy_send(self, phone: str, message: str) -> bool:
        """Dummy send function for testing."""
        print(f"📤 [SPIKE] Would send to {phone}:")
        print(message[:100] + "..." if len(message) > 100 else message)
        return True
    
    def _dummy_get_tenants(self) -> list:
        """Dummy tenant fetch for testing."""
        return [
            {
                "tenant_id": "T-001",
                "name": "María González",
                "phone": "+528112345001",
                "property": "Ensenada",
                "unit": "3",
                "rent": Decimal("4500"),
                "paid": False
            }
        ]
    
    def _dummy_get_codes(self) -> list:
        """Dummy pending codes fetch for testing."""
        return []
    
    def trigger(self, reminder_type: ReminderType) -> int:
        """
        Trigger a specific reminder type.
        
        Returns number of messages sent.
        """
        now = datetime.now(MEXICO_TZ)
        current_day = now.day
        month = now.strftime("%B %Y")
        
        print(f"🔔 Triggering: {reminder_type.value} at {now.isoformat()}")
        
        # Get unpaid tenants
        tenants = [t for t in self.get_tenants() if not t.get("paid", False)]
        
        if not tenants:
            print("✓ All tenants have paid!")
            return 0
        
        sent_count = 0
        
        for tenant in tenants:
            # Calculate amount due based on day
            base_rent = tenant["rent"]
            utilities = Decimal("350")  # Placeholder
            
            # Import late fee calculator
            from late_fees import calculate_rentas_claras_balance
            
            result = calculate_rentas_claras_balance(
                base_rent=base_rent,
                utilities=utilities,
                current_day=current_day
            )
            
            message = get_reminder_message(
                reminder_type=reminder_type,
                tenant_name=tenant["name"],
                amount_due=result.total_due,
                property_name=tenant["property"],
                unit=tenant["unit"],
                month=month
            )
            
            if message and self.send_message(tenant["phone"], message):
                sent_count += 1
        
        print(f"✓ Sent {sent_count} reminders")
        return sent_count
    
    def check_code_expiry(self, hours_threshold: int = 2) -> int:
        """
        Check for withdrawal codes expiring soon and alert landlord.
        
        Returns number of alerts sent.
        """
        now = datetime.now(MEXICO_TZ)
        threshold = now + timedelta(hours=hours_threshold)
        
        pending_codes = self.get_pending_codes()
        expiring = [c for c in pending_codes if c.get("expires_at") and c["expires_at"] <= threshold]
        
        alert_count = 0
        landlord_phone = "+528112340000"  # Placeholder
        
        for code in expiring:
            alert = get_code_expiry_alert(
                code=code["code"],
                amount=code["amount"],
                bank=code["bank"],
                tenant_name=code["tenant_name"],
                unit=code["unit"],
                expires_at=code["expires_at"]
            )
            
            if self.send_message(landlord_phone, alert):
                alert_count += 1
        
        return alert_count


# =============================================================================
# APSCHEDULER INTEGRATION
# =============================================================================

def setup_apscheduler(scheduler: ReminderScheduler):
    """
    Set up APScheduler for Python-native scheduling.
    
    Usage:
    ```python
    from apscheduler.schedulers.background import BackgroundScheduler
    
    scheduler = ReminderScheduler()
    aps = setup_apscheduler(scheduler)
    aps.start()
    ```
    """
    # This is the integration code - would need apscheduler installed
    print("""
# APScheduler Setup
# =================
# Install: pip install apscheduler

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

aps = BackgroundScheduler(timezone='America/Mexico_City')

# Morning reminder - 1st of month at 9 AM
aps.add_job(
    scheduler.trigger,
    CronTrigger(day=1, hour=9, minute=0),
    args=[ReminderType.MORNING_DAY_1],
    id='morning_day_1'
)

# Afternoon reminder - 1st of month at 4 PM
aps.add_job(
    scheduler.trigger,
    CronTrigger(day=1, hour=16, minute=0),
    args=[ReminderType.AFTERNOON_DAY_1],
    id='afternoon_day_1'
)

# Late payment reminders
for day in [2, 3, 5, 7, 8]:
    reminder_type = getattr(ReminderType, f'LATE_DAY_{day}', ReminderType.LATE_DAY_2)
    if day == 8:
        reminder_type = ReminderType.CRITICAL_DAY_8
    
    aps.add_job(
        scheduler.trigger,
        CronTrigger(day=day, hour=9, minute=0),
        args=[reminder_type],
        id=f'late_day_{day}'
    )

# Code expiry check - every 30 minutes
aps.add_job(
    scheduler.check_code_expiry,
    CronTrigger(minute='*/30'),
    id='code_expiry_check'
)

aps.start()
""")


# =============================================================================
# CLI INTERFACE
# =============================================================================

def main():
    """CLI entry point for cron-based triggering."""
    import argparse
    
    parser = argparse.ArgumentParser(description="RentasClaras Reminder Scheduler")
    parser.add_argument(
        "--trigger",
        choices=[
            "morning_day_1", "afternoon_day_1",
            "late_day_2", "late_day_3", "late_day_5", "late_day_7",
            "critical_day_8", "code_expiry_check"
        ],
        help="Trigger type to execute"
    )
    parser.add_argument(
        "--generate-crontab",
        action="store_true",
        help="Generate crontab configuration"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run demo mode"
    )
    
    args = parser.parse_args()
    
    if args.generate_crontab:
        print(generate_crontab())
        return
    
    if args.demo:
        run_scheduler_demo()
        return
    
    if args.trigger:
        scheduler = ReminderScheduler()
        
        if args.trigger == "code_expiry_check":
            scheduler.check_code_expiry()
        else:
            reminder_type = ReminderType(args.trigger)
            scheduler.trigger(reminder_type)


# =============================================================================
# DEMO
# =============================================================================

def run_scheduler_demo():
    """Demonstrate the scheduler functionality."""
    print("=" * 70)
    print("🏠 RENTASCLARAS - Scheduler Demo")
    print("=" * 70)
    print()
    
    now = datetime.now(MEXICO_TZ)
    print(f"📅 Current time (Mexico City): {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print()
    
    # Show cron expressions
    print("=" * 70)
    print("⏰ CRON EXPRESSIONS")
    print("=" * 70)
    print()
    
    for name, cron in get_cron_expressions().items():
        print(f"  {name}: {cron}")
    print()
    
    # Show next 1st of month
    print("=" * 70)
    print("📆 SCHEDULE CALCULATION")
    print("=" * 70)
    print()
    
    next_first = get_next_first_of_month()
    config = ReminderConfig()
    
    print(f"Next 1st of month: {next_first}")
    print(f"Morning reminder: {get_morning_reminder_time(next_first, config)}")
    print(f"Afternoon reminder: {get_afternoon_reminder_time(next_first, config)}")
    print()
    
    print("Late payment reminders:")
    for day, dt in get_late_reminder_times(next_first, config).items():
        print(f"  Day {day}: {dt}")
    print()
    
    # Show sample messages
    print("=" * 70)
    print("📱 SAMPLE MESSAGES")
    print("=" * 70)
    print()
    
    sample_types = [
        ReminderType.MORNING_DAY_1,
        ReminderType.LATE_DAY_2,
        ReminderType.CRITICAL_DAY_8,
    ]
    
    for reminder_type in sample_types:
        print(f"--- {reminder_type.value.upper()} ---")
        message = get_reminder_message(
            reminder_type=reminder_type,
            tenant_name="María González",
            amount_due=Decimal("5350.00"),
            property_name="Ensenada",
            unit="Unidad 3",
            month="Enero 2025"
        )
        print(message)
        print()
    
    # Simulate trigger
    print("=" * 70)
    print("🔔 SIMULATED TRIGGER")
    print("=" * 70)
    print()
    
    scheduler = ReminderScheduler()
    scheduler.trigger(ReminderType.MORNING_DAY_1)


if __name__ == "__main__":
    main()

"""
RentasClaras Database Module
============================

SQLite database for persistent tenant and payment record storage.
Supports historical monthly records.

Tables:
- tenants: Master list of tenants
- monthly_records: Monthly rent status per tenant
"""

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

# Database file path
# On Fly.io, use /data volume for persistence. Locally, use current directory.
if os.path.exists("/data"):
    DB_PATH = Path("/data/rentas_claras.db")
else:
    DB_PATH = Path(__file__).parent / "rentas_claras.db"


@dataclass
class Tenant:
    id: str
    name: str
    phone: str  # WhatsApp number with country code (+52...)
    property_name: str
    unit: str
    rent: Decimal
    paid: bool = False
    last_payment_date: Optional[str] = None
    payment_method: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    contract_start: Optional[str] = None
    contract_end: Optional[str] = None
    bank: Optional[str] = None  # Bank abbreviation from Excel
    # Contract renewal tracking
    renewal_status: str = "pendiente"  # 'renovará', 'no_renovará', 'pendiente'
    contract_delivered: bool = False  # Has new contract been delivered?
    contract_picked_up: bool = False  # Has tenant picked up the contract?
    leaving_date: Optional[str] = None  # Date tenant is leaving
    replacement_name: Optional[str] = None  # Name of replacement tenant
    replacement_phone: Optional[str] = None  # Phone of replacement tenant


def get_db_connection():
    """Get a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialize the database schema."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Tenants table - master list
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tenants (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT DEFAULT '',
            property_name TEXT NOT NULL,
            unit TEXT NOT NULL,
            rent REAL NOT NULL,
            emergency_contact TEXT,
            emergency_phone TEXT,
            contract_start TEXT,
            contract_end TEXT,
            bank TEXT,
            active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            -- Contract renewal tracking
            renewal_status TEXT DEFAULT 'pendiente',  -- 'renovará', 'no_renovará', 'pendiente'
            contract_delivered INTEGER DEFAULT 0,      -- Has new contract been delivered?
            contract_picked_up INTEGER DEFAULT 0,      -- Has tenant picked up the contract?
            leaving_date TEXT,                         -- Date tenant is leaving (if not renewing)
            replacement_name TEXT,                     -- Name of replacement tenant
            replacement_phone TEXT                     -- Phone of replacement tenant
        )
    """
    )

    # Add new columns if they don't exist (for existing databases)
    try:
        cursor.execute(
            "ALTER TABLE tenants ADD COLUMN renewal_status TEXT DEFAULT 'pendiente'"
        )
    except:
        pass
    try:
        cursor.execute(
            "ALTER TABLE tenants ADD COLUMN contract_delivered INTEGER DEFAULT 0"
        )
    except:
        pass
    try:
        cursor.execute(
            "ALTER TABLE tenants ADD COLUMN contract_picked_up INTEGER DEFAULT 0"
        )
    except:
        pass
    try:
        cursor.execute("ALTER TABLE tenants ADD COLUMN leaving_date TEXT")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE tenants ADD COLUMN replacement_name TEXT")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE tenants ADD COLUMN replacement_phone TEXT")
    except:
        pass

    # Message logs table - prevents double-sending (idempotency)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS message_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            message_type TEXT NOT NULL,  -- 'rent_reminder', 'late_day_2', 'late_day_5', etc.
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            day INTEGER NOT NULL,
            sent_at TEXT NOT NULL,
            message_id TEXT,  -- WhatsApp message ID from Meta API
            status TEXT DEFAULT 'sent',  -- 'sent', 'failed', 'delivered', 'read'
            error_message TEXT,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id),
            UNIQUE(tenant_id, message_type, year, month, day)  -- Prevent double-send same day
        )
    """
    )

    # Monthly records table - tracks payments per month
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS monthly_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            paid INTEGER DEFAULT 0,
            payment_date TEXT,
            payment_method TEXT,
            amount_paid REAL,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id),
            UNIQUE(tenant_id, year, month)
        )
    """
    )

    conn.commit()
    conn.close()


def seed_tenants():
    """
    Seed the database with tenant data from Excel screenshots.

    Properties:
    - Matehuala: 7 tenants (units A-G)
    - Múzquiz: 7 tenants (units A-G)
    - Ensenada: 9 tenants (units 1-9)
    - Huichapan: 8 tenants (units A-H)
    - Puerta Del Sol: 1 tenant (unit 1)

    Total: 32 tenants

    NOTE: Phone numbers are missing from Excel - placeholders used.
    User needs to provide real phone numbers.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if already seeded
    cursor.execute("SELECT COUNT(*) FROM tenants")
    if cursor.fetchone()[0] > 0:
        print("Database already seeded. Skipping.")
        conn.close()
        return

    tenants = [
        # MATEHUALA - 7 tenants (from Excel screenshot)
        # Units: A, B, C, D, E, F, G
        (
            "MAT-A",
            "Fatima",
            "",
            "Matehuala",
            "A",
            9600,
            None,
            None,
            "2024-07-01",
            "2025-12-31",
            "BT",
        ),
        (
            "MAT-B",
            "J Carlos y Raul",
            "",
            "Matehuala",
            "B",
            8400,
            None,
            None,
            "2024-04-06",
            "2026-04-30",
            "HSBC",
        ),
        (
            "MAT-C",
            "Enrique -Hector",
            "",
            "Matehuala",
            "C",
            7200,
            None,
            None,
            "2024-06-14",
            "2025-12-31",
            None,
        ),
        (
            "MAT-D",
            "Alejandro",
            "",
            "Matehuala",
            "D",
            7200,
            None,
            None,
            "2025-06-03",
            "2026-05-31",
            None,
        ),
        (
            "MAT-E",
            "José Pablo",
            "",
            "Matehuala",
            "E",
            7800,
            None,
            None,
            "2024-07-01",
            "2025-12-31",
            "Stdr",
        ),
        (
            "MAT-F",
            "Ali",
            "",
            "Matehuala",
            "F",
            6700,
            None,
            None,
            "2024-11-01",
            "2026-04-30",
            None,
        ),
        (
            "MAT-G",
            "Andrea",
            "",
            "Matehuala",
            "G",
            7300,
            None,
            None,
            "2025-04-01",
            "2026-03-31",
            None,
        ),
        # MÚZQUIZ 287 - 7 tenants (from Excel screenshot)
        # Units: A, B, C, D, E, F, G
        (
            "MUZ-A",
            "Antonio",
            "",
            "Múzquiz",
            "A",
            8400,
            None,
            None,
            "2025-07-01",
            "2025-12-31",
            "Bmx",
        ),
        (
            "MUZ-B",
            "Karen y Yolitzin",
            "",
            "Múzquiz",
            "B",
            9600,
            None,
            None,
            "2025-12-01",
            "2026-05-31",
            None,
        ),
        (
            "MUZ-C",
            "Alfredo",
            "",
            "Múzquiz",
            "C",
            7500,
            None,
            None,
            "2024-06-01",
            "2026-04-30",
            "ST",
        ),
        (
            "MUZ-D",
            "Gpe Vanessa",
            "",
            "Múzquiz",
            "D",
            7900,
            None,
            None,
            "2025-07-06",
            "2026-01-31",
            None,
        ),
        (
            "MUZ-E",
            "Isaac",
            "",
            "Múzquiz",
            "E",
            8100,
            None,
            None,
            "2023-08-01",
            "2026-01-31",
            None,
        ),
        (
            "MUZ-F",
            "Jorge de Jesús",
            "",
            "Múzquiz",
            "F",
            8100,
            None,
            None,
            "2025-03-15",
            "2026-03-31",
            None,
        ),
        (
            "MUZ-G",
            "Fernanda",
            "",
            "Múzquiz",
            "G",
            8100,
            None,
            None,
            "2024-12-26",
            "2025-12-31",
            None,
        ),
        # ENSENADA 114 - 9 tenants (from Excel screenshot)
        # Units: 1-9
        (
            "ENS-1",
            "Claudia",
            "",
            "Ensenada",
            "1",
            7500,
            None,
            None,
            "2025-11-16",
            "2026-05-31",
            None,
        ),
        (
            "ENS-2",
            "Samantha Y Cecilia",
            "",
            "Ensenada",
            "2",
            9500,
            None,
            None,
            "2024-12-15",
            "2025-12-31",
            None,
        ),
        (
            "ENS-3",
            "Regina",
            "",
            "Ensenada",
            "3",
            7800,
            None,
            None,
            "2025-01-07",
            "2025-12-31",
            None,
        ),
        (
            "ENS-4",
            "David Alonso",
            "",
            "Ensenada",
            "4",
            7800,
            None,
            None,
            "2024-05-31",
            "2026-05-31",
            None,
        ),
        (
            "ENS-5",
            "Aranza",
            "",
            "Ensenada",
            "5",
            8300,
            None,
            None,
            "2025-04-14",
            "2026-04-30",
            None,
        ),
        (
            "ENS-6",
            "Ericka",
            "",
            "Ensenada",
            "6",
            8300,
            None,
            None,
            "2025-02-01",
            "2026-01-31",
            None,
        ),
        (
            "ENS-7",
            "Fatima",
            "",
            "Ensenada",
            "7",
            7800,
            None,
            None,
            "2025-02-01",
            "2026-01-31",
            None,
        ),
        (
            "ENS-8",
            "Jhosvan",
            "",
            "Ensenada",
            "8",
            8100,
            None,
            None,
            "2024-03-25",
            "2026-03-31",
            None,
        ),
        (
            "ENS-9",
            "Cruz",
            "",
            "Ensenada",
            "9",
            7600,
            None,
            None,
            "2024-12-20",
            "2025-12-31",
            None,
        ),
        # HUICHAPAN - 8 tenants (from Excel screenshot)
        # Units: A, B, C, D, E, F, G, H
        (
            "HUI-A",
            "Hanna",
            "",
            "Huichapan",
            "A",
            7500,
            None,
            None,
            "2024-09-25",
            "2026-03-31",
            "BBVA",
        ),
        (
            "HUI-B",
            "Irene",
            "",
            "Huichapan",
            "B",
            6900,
            None,
            None,
            "2025-10-15",
            "2026-03-31",
            None,
        ),
        (
            "HUI-C",
            "Adrian",
            "",
            "Huichapan",
            "C",
            7200,
            None,
            None,
            "2025-03-22",
            "2026-03-31",
            None,
        ),
        (
            "HUI-D",
            "Raul",
            "",
            "Huichapan",
            "D",
            7200,
            None,
            None,
            "2025-02-03",
            "2026-02-28",
            None,
        ),
        (
            "HUI-E",
            "Jocelyn",
            "",
            "Huichapan",
            "E",
            6400,
            None,
            None,
            "2025-04-30",
            "2026-04-30",
            None,
        ),
        (
            "HUI-F",
            "Juan de Dios",
            "",
            "Huichapan",
            "F",
            7900,
            None,
            None,
            "2025-11-05",
            "2026-04-30",
            None,
        ),
        (
            "HUI-G",
            "Kevin",
            "",
            "Huichapan",
            "G",
            7300,
            None,
            None,
            "2025-04-05",
            "2026-03-31",
            None,
        ),
        (
            "HUI-H",
            "Daniela",
            "",
            "Huichapan",
            "H",
            6400,
            None,
            None,
            "2024-09-16",
            "2026-03-31",
            "BBVA",
        ),
        # PUERTA DEL SOL - 1 tenant
        # Units: 1
        (
            "PDS-1",
            "Inguva",
            "",
            "Puerta Del Sol",
            "1",
            15900,
            None,
            None,
            "2025-03-01",
            "2026-02-28",
            None,
        ),
    ]

    cursor.executemany(
        """
        INSERT INTO tenants (id, name, phone, property_name, unit, rent, 
                            emergency_contact, emergency_phone, contract_start, contract_end, bank)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        tenants,
    )

    conn.commit()
    conn.close()
    print(f"✅ Seeded {len(tenants)} tenants into database")


def get_all_tenants() -> List[Tenant]:
    """Get all active tenants."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, name, phone, property_name, unit, rent,
               emergency_contact, emergency_phone, contract_start, contract_end, bank,
               renewal_status, contract_delivered, contract_picked_up,
               leaving_date, replacement_name, replacement_phone
        FROM tenants 
        WHERE active = 1
        ORDER BY property_name, unit
    """
    )

    tenants = []
    for row in cursor.fetchall():
        tenants.append(
            Tenant(
                id=row["id"],
                name=row["name"],
                phone=row["phone"] or "",
                property_name=row["property_name"],
                unit=row["unit"],
                rent=Decimal(str(row["rent"])),
                emergency_contact=row["emergency_contact"],
                emergency_phone=row["emergency_phone"],
                contract_start=row["contract_start"],
                contract_end=row["contract_end"],
                bank=row["bank"],
                renewal_status=row["renewal_status"] or "pendiente",
                contract_delivered=bool(row["contract_delivered"]),
                contract_picked_up=bool(row["contract_picked_up"]),
                leaving_date=row["leaving_date"],
                replacement_name=row["replacement_name"],
                replacement_phone=row["replacement_phone"],
            )
        )

    conn.close()
    return tenants


def get_tenants_by_property() -> Dict[str, List[Tenant]]:
    """Get all tenants grouped by property."""
    tenants = get_all_tenants()
    grouped = {}
    for tenant in tenants:
        if tenant.property_name not in grouped:
            grouped[tenant.property_name] = []
        grouped[tenant.property_name].append(tenant)
    return grouped


def get_tenant_by_id(tenant_id: str) -> Optional[Tenant]:
    """Get a single tenant by their ID."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, name, phone, property_name, unit, rent,
               emergency_contact, emergency_phone, contract_start, contract_end, bank,
               renewal_status, contract_delivered, contract_picked_up,
               leaving_date, replacement_name, replacement_phone
        FROM tenants
        WHERE id = ? AND active = 1
    """,
        (tenant_id,),
    )

    row = cursor.fetchone()
    conn.close()

    if row:
        return Tenant(
            id=row["id"],
            name=row["name"],
            phone=row["phone"] or "",
            property_name=row["property_name"],
            unit=row["unit"],
            rent=Decimal(str(row["rent"])),
            emergency_contact=row["emergency_contact"],
            emergency_phone=row["emergency_phone"],
            contract_start=row["contract_start"],
            contract_end=row["contract_end"],
            bank=row["bank"],
            renewal_status=row["renewal_status"] or "pendiente",
            contract_delivered=bool(row["contract_delivered"]),
            contract_picked_up=bool(row["contract_picked_up"]),
            leaving_date=row["leaving_date"],
            replacement_name=row["replacement_name"],
            replacement_phone=row["replacement_phone"],
        )
    return None


def get_monthly_record(tenant_id: str, year: int, month: int) -> Optional[Dict]:
    """Get the monthly payment record for a tenant."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT * FROM monthly_records
        WHERE tenant_id = ? AND year = ? AND month = ?
    """,
        (tenant_id, year, month),
    )

    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def update_payment_status(
    tenant_id: str,
    year: int,
    month: int,
    paid: bool,
    payment_method: Optional[str] = None,
    amount_paid: Optional[float] = None,
    notes: Optional[str] = None,
):
    """Update or create a monthly payment record."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO monthly_records (tenant_id, year, month, paid, payment_method, amount_paid, notes, payment_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(tenant_id, year, month) DO UPDATE SET
            paid = excluded.paid,
            payment_method = COALESCE(excluded.payment_method, payment_method),
            amount_paid = COALESCE(excluded.amount_paid, amount_paid),
            notes = COALESCE(excluded.notes, notes),
            payment_date = CASE WHEN excluded.paid = 1 THEN COALESCE(payment_date, datetime('now')) ELSE NULL END,
            updated_at = datetime('now')
    """,
        (
            tenant_id,
            year,
            month,
            1 if paid else 0,
            payment_method,
            amount_paid,
            notes,
            datetime.now().isoformat() if paid else None,
        ),
    )

    conn.commit()
    conn.close()


def get_monthly_status(year: int, month: int) -> Dict[str, Dict]:
    """Get payment status for all tenants for a specific month."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get all tenants with their monthly status
    cursor.execute(
        """
        SELECT t.id, t.name, t.phone, t.property_name, t.unit, t.rent,
               t.emergency_contact, t.emergency_phone, t.contract_start, t.contract_end,
               COALESCE(m.paid, 0) as paid,
               m.payment_method, m.payment_date, m.amount_paid, m.notes
        FROM tenants t
        LEFT JOIN monthly_records m ON t.id = m.tenant_id AND m.year = ? AND m.month = ?
        WHERE t.active = 1
        ORDER BY t.property_name, t.unit
    """,
        (year, month),
    )

    result = {}
    for row in cursor.fetchall():
        result[row["id"]] = dict(row)

    conn.close()
    return result


def update_tenant_phone(tenant_id: str, phone: str):
    """Update a tenant's phone number."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE tenants SET phone = ?, updated_at = datetime('now')
        WHERE id = ?
    """,
        (phone, tenant_id),
    )

    conn.commit()
    conn.close()


def update_renewal_status(
    tenant_id: str,
    renewal_status: Optional[str] = None,
    contract_delivered: Optional[bool] = None,
    contract_picked_up: Optional[bool] = None,
    leaving_date: Optional[str] = None,
    replacement_name: Optional[str] = None,
    replacement_phone: Optional[str] = None,
):
    """Update contract renewal tracking for a tenant."""
    conn = get_db_connection()
    cursor = conn.cursor()

    updates = []
    params = []

    if renewal_status is not None:
        updates.append("renewal_status = ?")
        params.append(renewal_status)
    if contract_delivered is not None:
        updates.append("contract_delivered = ?")
        params.append(1 if contract_delivered else 0)
    if contract_picked_up is not None:
        updates.append("contract_picked_up = ?")
        params.append(1 if contract_picked_up else 0)
    if leaving_date is not None:
        updates.append("leaving_date = ?")
        params.append(leaving_date)
    if replacement_name is not None:
        updates.append("replacement_name = ?")
        params.append(replacement_name)
    if replacement_phone is not None:
        updates.append("replacement_phone = ?")
        params.append(replacement_phone)

    if updates:
        updates.append("updated_at = datetime('now')")
        params.append(tenant_id)

        cursor.execute(
            f"""
            UPDATE tenants SET {', '.join(updates)}
            WHERE id = ?
        """,
            params,
        )

        conn.commit()

    conn.close()


def get_available_months() -> List[Dict[str, int]]:
    """Get list of months that have payment records."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT DISTINCT year, month
        FROM monthly_records
        ORDER BY year DESC, month DESC
    """
    )

    months = [{"year": row["year"], "month": row["month"]} for row in cursor.fetchall()]
    conn.close()

    # Always include current month
    now = datetime.now()
    current = {"year": now.year, "month": now.month}
    if current not in months:
        months.insert(0, current)

    return months


def get_expiring_contracts(days_ahead: int = 60) -> List[Dict[str, Any]]:
    """
    Get contracts expiring within the specified number of days.
    
    Returns list of dicts with tenant info and days until expiration.
    Sorted by expiration date (soonest first).
    
    Args:
        days_ahead: Number of days to look ahead (default 60)
    
    Returns:
        List of dicts with: tenant_id, name, property_name, unit, contract_end,
                           days_until_expiry, urgency ('critical', 'warning', 'info')
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    today = datetime.now().date()
    
    cursor.execute(
        """
        SELECT id, name, property_name, unit, contract_end, renewal_status
        FROM tenants
        WHERE active = 1 AND contract_end IS NOT NULL AND contract_end != ''
        ORDER BY contract_end ASC
    """
    )
    
    expiring = []
    for row in cursor.fetchall():
        try:
            contract_end = datetime.strptime(row["contract_end"], "%Y-%m-%d").date()
            days_until = (contract_end - today).days
            
            # Only include contracts expiring within the specified window
            # Also include recently expired (up to 30 days ago) for follow-up
            if -30 <= days_until <= days_ahead:
                # Determine urgency level
                if days_until < 0:
                    urgency = "expired"
                elif days_until <= 14:
                    urgency = "critical"
                elif days_until <= 30:
                    urgency = "warning"
                else:
                    urgency = "info"
                
                expiring.append({
                    "tenant_id": row["id"],
                    "name": row["name"],
                    "property_name": row["property_name"],
                    "unit": row["unit"],
                    "contract_end": row["contract_end"],
                    "contract_end_formatted": contract_end.strftime("%d %b %Y"),
                    "days_until_expiry": days_until,
                    "urgency": urgency,
                    "renewal_status": row["renewal_status"] or "pendiente",
                })
        except (ValueError, TypeError):
            # Skip invalid dates
            continue
    
    conn.close()
    return expiring


# =============================================================================
# MESSAGE LOGGING (Idempotency / Anti-Spam)
# =============================================================================


def was_message_sent_today(tenant_id: str, message_type: str) -> bool:
    """
    Check if a message of this type was already sent to this tenant today.
    
    This prevents double-sending if the scheduler restarts or runs twice.
    
    Args:
        tenant_id: The tenant's ID
        message_type: Type of message ('rent_reminder', 'late_day_2', etc.)
    
    Returns:
        True if message was already sent today, False otherwise
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    now = datetime.now()
    
    cursor.execute(
        """
        SELECT id FROM message_logs
        WHERE tenant_id = ? AND message_type = ? 
        AND year = ? AND month = ? AND day = ?
        """,
        (tenant_id, message_type, now.year, now.month, now.day)
    )
    
    result = cursor.fetchone()
    conn.close()
    
    return result is not None


def log_message_sent(
    tenant_id: str,
    message_type: str,
    message_id: Optional[str] = None,
    status: str = "sent",
    error_message: Optional[str] = None
) -> bool:
    """
    Log that a message was sent (or attempted) to a tenant.
    
    Args:
        tenant_id: The tenant's ID
        message_type: Type of message ('rent_reminder', 'late_day_2', etc.)
        message_id: WhatsApp message ID from Meta API (optional)
        status: 'sent', 'failed', 'delivered', 'read'
        error_message: Error message if failed
    
    Returns:
        True if logged successfully, False if duplicate (already sent today)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    now = datetime.now()
    
    try:
        cursor.execute(
            """
            INSERT INTO message_logs 
            (tenant_id, message_type, year, month, day, sent_at, message_id, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tenant_id,
                message_type,
                now.year,
                now.month,
                now.day,
                now.isoformat(),
                message_id,
                status,
                error_message
            )
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        # Duplicate - message already sent today
        conn.close()
        return False


def get_unpaid_tenants_for_reminder(year: int, month: int, message_type: str) -> List[Dict]:
    """
    Get tenants who haven't paid AND haven't received this message type today.
    
    This is the main query for the scheduler - it handles both payment status
    AND idempotency in one query.
    
    Args:
        year: Current year
        month: Current month
        message_type: Type of reminder to check
    
    Returns:
        List of tenant dicts ready for messaging
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    today = datetime.now()
    
    cursor.execute(
        """
        SELECT t.id, t.name, t.phone, t.property_name, t.unit, t.rent,
               t.contract_start, t.contract_end
        FROM tenants t
        LEFT JOIN monthly_records m 
            ON t.id = m.tenant_id AND m.year = ? AND m.month = ?
        LEFT JOIN message_logs ml 
            ON t.id = ml.tenant_id 
            AND ml.message_type = ?
            AND ml.year = ? AND ml.month = ? AND ml.day = ?
        WHERE t.active = 1
        AND t.phone IS NOT NULL AND t.phone != ''
        AND COALESCE(m.paid, 0) = 0  -- Not paid
        AND ml.id IS NULL  -- No message sent today
        ORDER BY t.property_name, t.unit
        """,
        (year, month, message_type, today.year, today.month, today.day)
    )
    
    tenants = []
    for row in cursor.fetchall():
        tenants.append({
            "id": row["id"],
            "name": row["name"],
            "phone": row["phone"],
            "property_name": row["property_name"],
            "unit": row["unit"],
            "rent": Decimal(str(row["rent"])),
            "contract_start": row["contract_start"],
            "contract_end": row["contract_end"],
        })
    
    conn.close()
    return tenants


def get_message_history(tenant_id: str, limit: int = 10) -> List[Dict]:
    """Get recent message history for a tenant."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """
        SELECT message_type, year, month, day, sent_at, status, error_message
        FROM message_logs
        WHERE tenant_id = ?
        ORDER BY sent_at DESC
        LIMIT ?
        """,
        (tenant_id, limit)
    )
    
    history = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return history


# Initialize database when module is imported
if __name__ == "__main__":
    init_database()
    seed_tenants()

    # Show summary
    tenants = get_all_tenants()
    print(f"\n📊 Database Summary:")
    print(f"   Total tenants: {len(tenants)}")

    by_property = get_tenants_by_property()
    for prop, prop_tenants in by_property.items():
        print(f"   - {prop}: {len(prop_tenants)} unidades")

    # Check for missing phone numbers
    missing_phones = [t for t in tenants if not t.phone]
    if missing_phones:
        print(f"\n⚠️  WARNING: {len(missing_phones)} tenants have no phone number!")
        print("   Phone numbers must be added to send WhatsApp messages.")

"""
RentasClaras Database Module
============================

SQLite database for persistent tenant and payment record storage.
Supports historical monthly records.

Tables:
- tenants: Master list of tenants
- monthly_records: Monthly rent status per tenant
"""

import logging
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Database file path
# On Fly.io, use /data volume for persistence. Locally, use current directory.
if os.path.exists("/data"):
    DB_PATH = Path("/data/rentas_claras.db")
else:
    DB_PATH = Path(__file__).parent / "rentas_claras.db"


# =============================================================================
# SQL INJECTION PREVENTION - Column Name Whitelists
# =============================================================================

TENANT_SAFE_COLUMNS = frozenset(
    {
        "name",
        "phone",
        "property_name",
        "unit",
        "rent",
        "emergency_contact",
        "emergency_phone",
        "contract_start",
        "contract_end",
        "bank",
        "active",
        "renewal_status",
        "contract_delivered",
        "contract_picked_up",
        "leaving_date",
        "replacement_name",
        "replacement_phone",
        "replacement_contract_start",
        "replacement_contract_end",
        "replacement_aval_name",
        "replacement_aval_phone",
        "aval_name",
        "aval_phone",
        "prorated_first_month",
        "prorated_amount",
        "prorated_month",
        "prorated_year",
        "deposit_amount",
        "deposit_paid",
        "deposit_paid_date",
        "deposit_returned",
        "deposit_returned_date",
        "deposit_returned_notes",
        "updated_at",
    }
)


def _validate_column_names(columns: list, allowed: frozenset) -> None:
    """
    Validate that all column names are in the allowed whitelist.

    Raises ValueError if an invalid column name is detected.
    This prevents SQL injection through dynamic column names.
    """
    for col in columns:
        # Extract column name from "column = ?" format
        col_name = col.split(" = ")[0].strip() if " = " in col else col.strip()
        if col_name not in allowed:
            logger.error(f"SECURITY: Attempted SQL injection with column: {col_name}")
            raise ValueError(f"Invalid column name: {col_name}")


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
    # Guarantor (Aval) information
    aval_name: Optional[str] = None  # Tenant's guarantor name
    aval_phone: Optional[str] = None  # Tenant's guarantor phone
    # Contract renewal tracking
    renewal_status: str = "pendiente"  # 'renovará', 'no_renovará', 'pendiente'
    contract_delivered: bool = False  # Has new contract been delivered?
    contract_picked_up: bool = False  # Has tenant picked up the contract?
    leaving_date: Optional[str] = None  # Date tenant is leaving
    replacement_name: Optional[str] = None  # Name of replacement tenant
    replacement_phone: Optional[str] = None  # Phone of replacement tenant
    # New replacement candidate fields
    replacement_contract_start: Optional[str] = (
        None  # Start date of new tenant's contract
    )
    replacement_contract_end: Optional[str] = None  # End date of new tenant's contract
    replacement_aval_name: Optional[str] = None  # Guarantor name
    replacement_aval_phone: Optional[str] = None  # Guarantor phone
    # Prorated first month rent
    prorated_first_month: bool = False  # Is first month prorated?
    prorated_amount: Optional[Decimal] = None  # Prorated amount for first month
    prorated_month: Optional[int] = None  # Month the proration applies to (1-12)
    prorated_year: Optional[int] = None  # Year the proration applies to


def get_db_connection():
    """Get a connection to the SQLite database with ROCK SOLID durability."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row

    # CRITICAL: These settings ensure data is written to disk
    cursor = conn.cursor()

    # Use WAL mode for better concurrency + crash safety
    cursor.execute("PRAGMA journal_mode=WAL")

    # FULL sync means every transaction waits for disk write confirmation
    # This is slower but GUARANTEES data isn't lost
    cursor.execute("PRAGMA synchronous=FULL")

    # Checkpoint WAL file after every 1000 pages
    cursor.execute("PRAGMA wal_autocheckpoint=1000")

    # Enable foreign keys for data integrity
    cursor.execute("PRAGMA foreign_keys=ON")

    return conn


class DatabaseConnection:
    """
    Context manager for database connections.

    Ensures proper cleanup and commit/rollback handling.

    Usage:
        with DatabaseConnection() as (conn, cursor):
            cursor.execute(...)
            # Auto-commits on success, rollbacks on exception

        # For read-only operations (no commit):
        with DatabaseConnection(readonly=True) as (conn, cursor):
            cursor.execute("SELECT ...")
    """

    def __init__(self, readonly: bool = False):
        self.conn = None
        self.readonly = readonly

    def __enter__(self):
        self.conn = get_db_connection()
        cursor = self.conn.cursor()
        return self.conn, cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            if exc_type is not None:
                # Exception occurred - rollback
                self.conn.rollback()
            elif not self.readonly:
                # No exception - commit
                self.conn.commit()
            self.conn.close()
        return False  # Don't suppress exceptions


# =============================================================================
# MIGRATION HELPER
# =============================================================================


def _add_column_if_not_exists(cursor, table: str, column: str, column_def: str) -> bool:
    """
    Add a column to a table if it doesn't already exist.

    This reduces repetitive try/except blocks for schema migrations.

    Args:
        cursor: Database cursor
        table: Table name
        column: Column name
        column_def: Column definition (e.g., "TEXT", "INTEGER DEFAULT 0")

    Returns:
        True if column was added, False if it already exists
    """
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_def}")
        return True
    except sqlite3.OperationalError:
        return False  # Column already exists


def verify_database_integrity() -> tuple[bool, str]:
    """
    Check database integrity on startup.

    Returns:
        (is_ok, message) - True if database is healthy
    """
    if not DB_PATH.exists():
        return True, "Database does not exist yet (will be created)"

    try:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        cursor = conn.cursor()

        # Run integrity check
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]

        conn.close()

        if result == "ok":
            return True, "Database integrity check passed ✅"
        else:
            return False, f"Database integrity check failed: {result}"

    except Exception as e:
        return False, f"Database integrity check error: {str(e)}"


def startup_health_check():
    """
    Run comprehensive health checks on startup.
    Logs warnings but doesn't prevent startup.
    """
    import logging

    logger = logging.getLogger(__name__)

    print("🔍 Running database health checks...")

    # 1. Check integrity
    is_ok, message = verify_database_integrity()
    if is_ok:
        print(f"   {message}")
    else:
        print(f"   ⚠️  WARNING: {message}")
        logger.warning(f"Database integrity issue: {message}")

    # 2. Check if volume is mounted (production only)
    if os.path.exists("/data"):
        # Check if it's actually a mount point with sufficient space
        try:
            stat = os.statvfs("/data")
            free_mb = (stat.f_frsize * stat.f_bavail) / (1024 * 1024)
            total_mb = (stat.f_frsize * stat.f_blocks) / (1024 * 1024)
            print(
                f"   📁 Volume /data mounted: {free_mb:.0f}MB free of {total_mb:.0f}MB"
            )

            if free_mb < 50:
                print(f"   ⚠️  WARNING: Low disk space on volume!")
                logger.warning(f"Low disk space on /data volume: {free_mb:.0f}MB free")
        except Exception as e:
            print(f"   ⚠️  Could not check volume: {e}")
    else:
        print("   📁 Running locally (no /data volume)")

    # 3. Check if database exists
    if DB_PATH.exists():
        size_mb = DB_PATH.stat().st_size / (1024 * 1024)
        print(f"   📊 Database: {DB_PATH} ({size_mb:.2f}MB)")
    else:
        print(f"   📊 Database will be created at: {DB_PATH}")

    print("✅ Health check complete")


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
    except sqlite3.OperationalError:
        pass  # Column already exists
    try:
        cursor.execute(
            "ALTER TABLE tenants ADD COLUMN contract_delivered INTEGER DEFAULT 0"
        )
    except sqlite3.OperationalError:
        pass  # Column already exists
    try:
        cursor.execute(
            "ALTER TABLE tenants ADD COLUMN contract_picked_up INTEGER DEFAULT 0"
        )
    except sqlite3.OperationalError:
        pass  # Column already exists
    try:
        cursor.execute("ALTER TABLE tenants ADD COLUMN leaving_date TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    try:
        cursor.execute("ALTER TABLE tenants ADD COLUMN replacement_name TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    try:
        cursor.execute("ALTER TABLE tenants ADD COLUMN replacement_phone TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    # New replacement candidate fields
    try:
        cursor.execute("ALTER TABLE tenants ADD COLUMN replacement_contract_start TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    try:
        cursor.execute("ALTER TABLE tenants ADD COLUMN replacement_contract_end TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    try:
        cursor.execute("ALTER TABLE tenants ADD COLUMN replacement_aval_name TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    try:
        cursor.execute("ALTER TABLE tenants ADD COLUMN replacement_aval_phone TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    # Tenant's own aval (guarantor) fields
    try:
        cursor.execute("ALTER TABLE tenants ADD COLUMN aval_name TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    try:
        cursor.execute("ALTER TABLE tenants ADD COLUMN aval_phone TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    # Prorated rent fields
    try:
        cursor.execute(
            "ALTER TABLE tenants ADD COLUMN prorated_first_month INTEGER DEFAULT 0"
        )
    except sqlite3.OperationalError:
        pass  # Column already exists
    try:
        cursor.execute("ALTER TABLE tenants ADD COLUMN prorated_amount REAL")
    except sqlite3.OperationalError:
        pass  # Column already exists
    try:
        cursor.execute("ALTER TABLE tenants ADD COLUMN prorated_month INTEGER")
    except sqlite3.OperationalError:
        pass  # Column already exists
    try:
        cursor.execute("ALTER TABLE tenants ADD COLUMN prorated_year INTEGER")
    except sqlite3.OperationalError:
        pass  # Column already exists
    # Deposit tracking
    try:
        cursor.execute(
            "ALTER TABLE tenants ADD COLUMN deposit_returned INTEGER DEFAULT 0"
        )
    except sqlite3.OperationalError:
        pass  # Column already exists
    try:
        cursor.execute("ALTER TABLE tenants ADD COLUMN deposit_returned_date TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    try:
        cursor.execute("ALTER TABLE tenants ADD COLUMN deposit_returned_notes TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    # Deposit payment tracking (when deposit was received)
    try:
        cursor.execute("ALTER TABLE tenants ADD COLUMN deposit_amount REAL")
    except sqlite3.OperationalError:
        pass  # Column already exists
    try:
        cursor.execute("ALTER TABLE tenants ADD COLUMN deposit_paid INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # Column already exists
    try:
        cursor.execute("ALTER TABLE tenants ADD COLUMN deposit_paid_date TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Message logs table - tracks ALL message history (no unique constraint!)
    # We want to keep full history: 8 AM reminder, 5 PM reminder, retries, etc.
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
            delivered_at TEXT,  -- Timestamp when delivered
            read_at TEXT,  -- Timestamp when read
            error_message TEXT,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id)
        )
    """
    )

    # Migration: Remove unique constraint from old databases
    # SQLite doesn't support dropping constraints, so we need to recreate the table
    # Check if the unique constraint exists by trying to insert duplicates
    try:
        cursor.execute(
            """
            SELECT sql FROM sqlite_master 
            WHERE type='table' AND name='message_logs'
            """
        )
        row = cursor.fetchone()
        if row and "UNIQUE" in row[0]:
            logger.info("Migrating message_logs table to remove unique constraint...")
            # Rename old table
            cursor.execute("ALTER TABLE message_logs RENAME TO message_logs_old")
            # Create new table without unique constraint
            cursor.execute(
                """
                CREATE TABLE message_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    month INTEGER NOT NULL,
                    day INTEGER NOT NULL,
                    sent_at TEXT NOT NULL,
                    message_id TEXT,
                    status TEXT DEFAULT 'sent',
                    delivered_at TEXT,
                    read_at TEXT,
                    error_message TEXT,
                    FOREIGN KEY (tenant_id) REFERENCES tenants(id)
                )
                """
            )
            # Copy data
            cursor.execute(
                """
                INSERT INTO message_logs 
                SELECT * FROM message_logs_old
                """
            )
            # Drop old table
            cursor.execute("DROP TABLE message_logs_old")
            logger.info("Migration complete: message_logs unique constraint removed")
    except Exception as e:
        logger.warning(f"Could not check/migrate message_logs: {e}")

    # Add new columns for delivery tracking (for existing databases)
    _add_column_if_not_exists(cursor, "message_logs", "delivered_at", "TEXT")
    _add_column_if_not_exists(cursor, "message_logs", "read_at", "TEXT")

    # Incoming messages table - stores replies from tenants
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS incoming_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wa_message_id TEXT UNIQUE,  -- WhatsApp message ID
            from_phone TEXT NOT NULL,  -- Phone number of sender
            tenant_id TEXT,  -- Matched tenant ID (if found)
            message_type TEXT NOT NULL,  -- 'text', 'image', 'audio', 'document', etc.
            message_body TEXT,  -- Text content (for text messages)
            media_id TEXT,  -- Media ID for non-text messages
            timestamp TEXT NOT NULL,  -- When the message was sent
            received_at TEXT NOT NULL,  -- When we received it
            read_by_user INTEGER DEFAULT 0,  -- Has the landlord seen this?
            FOREIGN KEY (tenant_id) REFERENCES tenants(id)
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
            visits INTEGER DEFAULT 0,
            visit_charge REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id),
            UNIQUE(tenant_id, year, month)
        )
    """
    )

    # Add visits columns if they don't exist (for existing databases)
    try:
        cursor.execute(
            "ALTER TABLE monthly_records ADD COLUMN visits INTEGER DEFAULT 0"
        )
    except sqlite3.OperationalError:
        pass  # Column already exists
    try:
        cursor.execute(
            "ALTER TABLE monthly_records ADD COLUMN visit_charge REAL DEFAULT 0"
        )
    except sqlite3.OperationalError:
        pass  # Column already exists

    conn.commit()
    conn.close()


def seed_tenants():
    """
    Seed the database with tenant data from JSON file.

    Data source: data/seed_tenants.json

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
    import json

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if already seeded
    cursor.execute("SELECT COUNT(*) FROM tenants")
    if cursor.fetchone()[0] > 0:
        print("Database already seeded. Skipping.")
        conn.close()
        return

    # Load seed data from JSON file
    seed_file = Path(__file__).parent / "data" / "seed_tenants.json"

    if not seed_file.exists():
        print(f"⚠️  Seed file not found: {seed_file}")
        print("   Database will start empty. Add tenants via the UI.")
        conn.close()
        return

    with open(seed_file, "r", encoding="utf-8") as f:
        seed_data = json.load(f)

    # Convert JSON records to tuples for INSERT
    tenants = []
    for t in seed_data.get("tenants", []):
        tenants.append(
            (
                t["id"],
                t["name"],
                t.get("phone", ""),
                t["property_name"],
                t["unit"],
                t["rent"],
                t.get("emergency_contact"),
                t.get("emergency_phone"),
                t.get("contract_start"),
                t.get("contract_end"),
                t.get("bank"),
            )
        )

    if not tenants:
        print("⚠️  No tenants found in seed file.")
        conn.close()
        return

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
    print(f"✅ Seeded {len(tenants)} tenants from {seed_file.name}")


def get_all_tenants() -> List[Tenant]:
    """Get all active tenants."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, name, phone, property_name, unit, rent,
               emergency_contact, emergency_phone, contract_start, contract_end, bank,
               aval_name, aval_phone,
               renewal_status, contract_delivered, contract_picked_up,
               leaving_date, replacement_name, replacement_phone,
               replacement_contract_start, replacement_contract_end,
               replacement_aval_name, replacement_aval_phone,
               prorated_first_month, prorated_amount, prorated_month, prorated_year
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
                aval_name=row["aval_name"],
                aval_phone=row["aval_phone"],
                renewal_status=row["renewal_status"] or "pendiente",
                contract_delivered=bool(row["contract_delivered"]),
                contract_picked_up=bool(row["contract_picked_up"]),
                leaving_date=row["leaving_date"],
                replacement_name=row["replacement_name"],
                replacement_phone=row["replacement_phone"],
                replacement_contract_start=row["replacement_contract_start"],
                replacement_contract_end=row["replacement_contract_end"],
                replacement_aval_name=row["replacement_aval_name"],
                replacement_aval_phone=row["replacement_aval_phone"],
                prorated_first_month=bool(row["prorated_first_month"]),
                prorated_amount=(
                    Decimal(str(row["prorated_amount"]))
                    if row["prorated_amount"]
                    else None
                ),
                prorated_month=row["prorated_month"],
                prorated_year=row["prorated_year"],
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


def get_billable_tenants(year: int, month: int) -> List[Tenant]:
    """
    Get tenants who owe rent for a specific billing month.

    This is the SINGLE SOURCE OF TRUTH for determining which tenants
    should appear in payment tracking and dashboard pending counts.

    Excludes:
    - Inactive tenants (already filtered by get_all_tenants)
    - Tenants whose contract_start is in the billing month (they don't
      owe rent for their first month if they start on the 1st)

    Args:
        year: The billing year (e.g., 2026)
        month: The billing month (1-12)

    Returns:
        List of Tenant objects who owe rent for this month
    """
    from services.dates import parse_date

    all_tenants = get_all_tenants()
    billable = []

    for tenant in all_tenants:
        if tenant.contract_start:
            start_date = parse_date(tenant.contract_start)
            if start_date and start_date.year == year and start_date.month == month:
                continue  # Skip tenants starting this month
        billable.append(tenant)

    return billable


def get_tenant_by_id(tenant_id: str) -> Optional[Tenant]:
    """Get a single tenant by their ID."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, name, phone, property_name, unit, rent,
               emergency_contact, emergency_phone, contract_start, contract_end, bank,
               aval_name, aval_phone,
               renewal_status, contract_delivered, contract_picked_up,
               leaving_date, replacement_name, replacement_phone,
               replacement_contract_start, replacement_contract_end,
               replacement_aval_name, replacement_aval_phone,
               prorated_first_month, prorated_amount, prorated_month, prorated_year
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
            aval_name=row["aval_name"],
            aval_phone=row["aval_phone"],
            renewal_status=row["renewal_status"] or "pendiente",
            contract_delivered=bool(row["contract_delivered"]),
            contract_picked_up=bool(row["contract_picked_up"]),
            leaving_date=row["leaving_date"],
            replacement_name=row["replacement_name"],
            replacement_phone=row["replacement_phone"],
            replacement_contract_start=row["replacement_contract_start"],
            replacement_contract_end=row["replacement_contract_end"],
            replacement_aval_name=row["replacement_aval_name"],
            replacement_aval_phone=row["replacement_aval_phone"],
            prorated_first_month=bool(row["prorated_first_month"]),
            prorated_amount=(
                Decimal(str(row["prorated_amount"])) if row["prorated_amount"] else None
            ),
            prorated_month=row["prorated_month"],
            prorated_year=row["prorated_year"],
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
    visits: int = 0,
    visit_charge: float = 0.0,
):
    """Update or create a monthly payment record."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO monthly_records (tenant_id, year, month, paid, payment_method, amount_paid, notes, payment_date, visits, visit_charge)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(tenant_id, year, month) DO UPDATE SET
            paid = excluded.paid,
            payment_method = COALESCE(excluded.payment_method, payment_method),
            amount_paid = COALESCE(excluded.amount_paid, amount_paid),
            notes = COALESCE(excluded.notes, notes),
            visits = excluded.visits,
            visit_charge = excluded.visit_charge,
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
            visits if paid else 0,
            visit_charge if paid else 0.0,
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
               m.payment_method, m.payment_date, m.amount_paid, m.notes,
               COALESCE(m.visits, 0) as visits,
               COALESCE(m.visit_charge, 0) as visit_charge
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


def auto_renew_contract(tenant_id: str, months: int = 6) -> Optional[str]:
    """
    Automatically extend a tenant's contract by the specified number of months.
    
    This is called when a tenant confirms they will renew (status = 'renovará').
    It extends the contract_end date by the specified number of months.
    
    Args:
        tenant_id: The tenant's ID
        months: Number of months to extend the contract (default 6)
        
    Returns:
        The new contract_end date as a string (YYYY-MM-DD), or None if failed
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get current contract end date
        cursor.execute(
            "SELECT contract_end FROM tenants WHERE id = ? AND active = 1",
            (tenant_id,)
        )
        row = cursor.fetchone()
        
        if not row or not row["contract_end"]:
            logger.warning(f"Cannot auto-renew: tenant {tenant_id} has no contract_end date")
            conn.close()
            return None
        
        # Parse the current end date
        try:
            current_end = datetime.strptime(row["contract_end"], "%Y-%m-%d")
        except ValueError:
            logger.error(f"Invalid contract_end date format for tenant {tenant_id}: {row['contract_end']}")
            conn.close()
            return None
        
        # Calculate new end date (add months)
        new_month = current_end.month + months
        new_year = current_end.year + (new_month - 1) // 12
        new_month = ((new_month - 1) % 12) + 1
        
        # Handle day overflow (e.g., Jan 31 + 1 month -> Feb 28)
        import calendar
        max_day = calendar.monthrange(new_year, new_month)[1]
        new_day = min(current_end.day, max_day)
        
        new_end = current_end.replace(year=new_year, month=new_month, day=new_day)
        new_end_str = new_end.strftime("%Y-%m-%d")
        
        # Update the contract_end date and reset tracking flags for new contract cycle
        cursor.execute(
            """
            UPDATE tenants 
            SET contract_end = ?,
                contract_delivered = 0,
                contract_picked_up = 0,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (new_end_str, tenant_id)
        )
        
        conn.commit()
        logger.info(f"Auto-renewed contract for tenant {tenant_id}: {row['contract_end']} -> {new_end_str}")
        return new_end_str
        
    except Exception as e:
        logger.error(f"Error auto-renewing contract for tenant {tenant_id}: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()


def update_renewal_status(
    tenant_id: str,
    renewal_status: Optional[str] = None,
    contract_delivered: Optional[bool] = None,
    contract_picked_up: Optional[bool] = None,
    leaving_date: Optional[str] = None,
    replacement_name: Optional[str] = None,
    replacement_phone: Optional[str] = None,
    replacement_contract_start: Optional[str] = None,
    replacement_contract_end: Optional[str] = None,
    replacement_aval_name: Optional[str] = None,
    replacement_aval_phone: Optional[str] = None,
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
    if replacement_contract_start is not None:
        updates.append("replacement_contract_start = ?")
        params.append(replacement_contract_start)
    if replacement_contract_end is not None:
        updates.append("replacement_contract_end = ?")
        params.append(replacement_contract_end)
    if replacement_aval_name is not None:
        updates.append("replacement_aval_name = ?")
        params.append(replacement_aval_name)
    if replacement_aval_phone is not None:
        updates.append("replacement_aval_phone = ?")
        params.append(replacement_aval_phone)

    if updates:
        # Validate all column names against whitelist (SQL injection prevention)
        _validate_column_names(updates, TENANT_SAFE_COLUMNS)

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

                expiring.append(
                    {
                        "tenant_id": row["id"],
                        "name": row["name"],
                        "property_name": row["property_name"],
                        "unit": row["unit"],
                        "contract_end": row["contract_end"],
                        "contract_end_formatted": contract_end.strftime("%d %b %Y"),
                        "days_until_expiry": days_until,
                        "urgency": urgency,
                        "renewal_status": row["renewal_status"] or "pendiente",
                    }
                )
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
    Check if a SUCCESSFUL message of this type was already sent to this tenant today.

    This prevents double-sending if the scheduler restarts or runs twice.
    Failed messages do NOT count - we allow retries after failures.

    Args:
        tenant_id: The tenant's ID
        message_type: Type of message ('rent_reminder', 'late_day_2', etc.)

    Returns:
        True if a successful message was already sent today, False otherwise
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    now = datetime.now()

    # Only count successful sends (sent, delivered, read) - NOT failed
    cursor.execute(
        """
        SELECT id FROM message_logs
        WHERE tenant_id = ? AND message_type = ? 
        AND year = ? AND month = ? AND day = ?
        AND status IN ('sent', 'delivered', 'read')
        """,
        (tenant_id, message_type, now.year, now.month, now.day),
    )

    result = cursor.fetchone()
    conn.close()

    return result is not None


def log_message_sent(
    tenant_id: str,
    message_type: str,
    message_id: Optional[str] = None,
    status: str = "sent",
    error_message: Optional[str] = None,
) -> bool:
    """
    Log that a message was sent (or attempted) to a tenant.

    Always creates a NEW record - we want full history of all messages
    (8 AM reminder, 5 PM reminder, retries, failures, etc.)

    Args:
        tenant_id: The tenant's ID
        message_type: Type of message ('morning_reminder', 'afternoon_reminder', etc.)
        message_id: WhatsApp message ID from Meta API (optional)
        status: 'sent', 'failed', 'delivered', 'read'
        error_message: Error message if failed

    Returns:
        True if logged successfully
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    now = datetime.now()

    try:
        # Always INSERT a new record - keep full message history
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
                error_message,
            ),
        )
        conn.commit()
        logger.info(f"Message logged: tenant={tenant_id}, status={status}, message_id={message_id}")
        return True
    except sqlite3.IntegrityError as e:
        # Handle unique constraint if it still exists in old databases
        # Try to update existing record as fallback
        logger.warning(f"IntegrityError (old schema?), trying update: {e}")
        try:
            cursor.execute(
                """
                UPDATE message_logs 
                SET sent_at = ?, message_id = ?, status = ?, error_message = ?,
                    delivered_at = NULL, read_at = NULL
                WHERE tenant_id = ? AND message_type = ? 
                AND year = ? AND month = ? AND day = ?
                """,
                (
                    now.isoformat(),
                    message_id,
                    status,
                    error_message,
                    tenant_id,
                    message_type,
                    now.year,
                    now.month,
                    now.day,
                ),
            )
            conn.commit()
            return True
        except Exception as e2:
            logger.error(f"Error updating message log: {e2}")
            return False
    except Exception as e:
        logger.error(f"Error logging message: {e}")
        return False
    finally:
        conn.close()


def get_unpaid_tenants_for_reminder(
    year: int, month: int, message_type: str
) -> List[Dict]:
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
        (year, month, message_type, today.year, today.month, today.day),
    )

    tenants = []
    for row in cursor.fetchall():
        tenants.append(
            {
                "id": row["id"],
                "name": row["name"],
                "phone": row["phone"],
                "property_name": row["property_name"],
                "unit": row["unit"],
                "rent": Decimal(str(row["rent"])),
                "contract_start": row["contract_start"],
                "contract_end": row["contract_end"],
            }
        )

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
        (tenant_id, limit),
    )

    history = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return history


def get_message_counts_for_month(year: int, month: int) -> dict:
    """
    Get message counts for all tenants for a specific month.

    Returns dict: {tenant_id: {"sent": count, "failed": count, "has_phone": bool}}
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get message counts grouped by tenant and status
    cursor.execute(
        """
        SELECT 
            tenant_id,
            status,
            COUNT(*) as count
        FROM message_logs
        WHERE year = ? AND month = ?
        GROUP BY tenant_id, status
        """,
        (year, month),
    )

    # Build result dict
    result = {}
    for row in cursor.fetchall():
        tenant_id = row["tenant_id"]
        status = row["status"]
        count = row["count"]

        if tenant_id not in result:
            result[tenant_id] = {"sent": 0, "failed": 0}

        if status == "sent" or status == "delivered" or status == "read":
            result[tenant_id]["sent"] += count
        elif status == "failed":
            result[tenant_id]["failed"] += count

    conn.close()
    return result


def get_all_properties() -> List[str]:
    """Get list of all unique property names."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT DISTINCT property_name FROM tenants
        WHERE active = 1
        ORDER BY property_name
        """
    )

    properties = [row["property_name"] for row in cursor.fetchall()]
    conn.close()
    return properties


def add_tenant(
    name: str,
    property_name: str,
    unit: str,
    rent: float,
    phone: str = "",
    contract_start: Optional[str] = None,
    contract_end: Optional[str] = None,
    emergency_contact: Optional[str] = None,
    emergency_phone: Optional[str] = None,
    bank: Optional[str] = None,
    aval_name: Optional[str] = None,
    aval_phone: Optional[str] = None,
    prorated_first_month: bool = False,
    prorated_amount: Optional[float] = None,
    prorated_month: Optional[int] = None,
    prorated_year: Optional[int] = None,
) -> str:
    """Add a new tenant. Returns the new tenant ID."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Generate ID from property name prefix and unit
    # E.g., "Matehuala" + "H" = "MAT-H"
    prefix = property_name[:3].upper()
    tenant_id = f"{prefix}-{unit}"

    # Check if ID already exists, add number if needed
    cursor.execute("SELECT id FROM tenants WHERE id = ?", (tenant_id,))
    if cursor.fetchone():
        # Find next available number
        cursor.execute(
            "SELECT id FROM tenants WHERE id LIKE ? ORDER BY id", (f"{prefix}-%",)
        )
        existing = [row["id"] for row in cursor.fetchall()]
        counter = 2
        while f"{prefix}-{unit}{counter}" in existing:
            counter += 1
        tenant_id = f"{prefix}-{unit}{counter}"

    cursor.execute(
        """
        INSERT INTO tenants (id, name, phone, property_name, unit, rent,
                            emergency_contact, emergency_phone, contract_start, contract_end, bank,
                            aval_name, aval_phone,
                            prorated_first_month, prorated_amount, prorated_month, prorated_year)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            tenant_id,
            name,
            phone,
            property_name,
            unit,
            rent,
            emergency_contact,
            emergency_phone,
            contract_start,
            contract_end,
            bank,
            aval_name,
            aval_phone,
            1 if prorated_first_month else 0,
            prorated_amount,
            prorated_month,
            prorated_year,
        ),
    )

    conn.commit()
    conn.close()

    return tenant_id


def update_tenant(
    tenant_id: str,
    name: Optional[str] = None,
    phone: Optional[str] = None,
    property_name: Optional[str] = None,
    unit: Optional[str] = None,
    rent: Optional[float] = None,
    contract_start: Optional[str] = None,
    contract_end: Optional[str] = None,
    emergency_contact: Optional[str] = None,
    emergency_phone: Optional[str] = None,
    bank: Optional[str] = None,
    aval_name: Optional[str] = None,
    aval_phone: Optional[str] = None,
):
    """Update an existing tenant's information."""
    conn = get_db_connection()
    cursor = conn.cursor()

    updates = []
    params = []

    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if phone is not None:
        updates.append("phone = ?")
        params.append(phone)
    if property_name is not None:
        updates.append("property_name = ?")
        params.append(property_name)
    if unit is not None:
        updates.append("unit = ?")
        params.append(unit)
    if rent is not None:
        updates.append("rent = ?")
        params.append(rent)
    if contract_start is not None:
        updates.append("contract_start = ?")
        params.append(contract_start)
    if contract_end is not None:
        updates.append("contract_end = ?")
        params.append(contract_end)
    if emergency_contact is not None:
        updates.append("emergency_contact = ?")
        params.append(emergency_contact)
    if emergency_phone is not None:
        updates.append("emergency_phone = ?")
        params.append(emergency_phone)
    if bank is not None:
        updates.append("bank = ?")
        params.append(bank)
    if aval_name is not None:
        updates.append("aval_name = ?")
        params.append(aval_name)
    if aval_phone is not None:
        updates.append("aval_phone = ?")
        params.append(aval_phone)

    if updates:
        # Validate all column names against whitelist (SQL injection prevention)
        _validate_column_names(updates, TENANT_SAFE_COLUMNS)

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


def deactivate_tenant(tenant_id: str):
    """Soft-delete a tenant by marking as inactive."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE tenants SET active = 0, updated_at = datetime('now')
        WHERE id = ?
        """,
        (tenant_id,),
    )

    conn.commit()
    conn.close()


def reactivate_tenant(tenant_id: str):
    """Reactivate a previously deactivated tenant."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE tenants SET active = 1, updated_at = datetime('now')
        WHERE id = ?
        """,
        (tenant_id,),
    )

    conn.commit()
    conn.close()


def get_last_sync_time(table: str = None) -> Optional[str]:
    """
    Get the timestamp of the most recent database update.

    Args:
        table: Optional table name to check. If None, checks all relevant tables
               and returns the most recent update across all of them.
               Valid values: 'monthly_records', 'tenants', 'message_logs'

    Returns:
        ISO timestamp string of last update, or None if no records exist
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    if table:
        # Check specific table
        cursor.execute(
            f"""
            SELECT MAX(updated_at) as last_update 
            FROM {table}
            """
        )
        row = cursor.fetchone()
        conn.close()
        return row["last_update"] if row and row["last_update"] else None

    # Check all relevant tables and return the most recent
    cursor.execute(
        """
        SELECT MAX(last_update) as last_update FROM (
            SELECT MAX(updated_at) as last_update FROM monthly_records
            UNION ALL
            SELECT MAX(updated_at) as last_update FROM tenants
        )
        """
    )

    row = cursor.fetchone()
    conn.close()

    if row and row["last_update"]:
        return row["last_update"]

    return None


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

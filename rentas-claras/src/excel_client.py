"""
RentasClaras: Excel Online Integration
=======================================

Connects to Excel workbooks hosted on OneDrive/SharePoint via Microsoft Graph API.
Reads tenant data, writes payments, and updates ATM codes.

Architecture:
    WhatsApp → Webhook → Python → Microsoft Graph API → Excel Online
    
Prerequisites:
    1. Azure AD App Registration with delegated permissions:
       - Files.ReadWrite (for OneDrive)
       - Sites.ReadWrite.All (for SharePoint)
    2. OAuth 2.0 token (user or application flow)

Author: RentasClaras Engineering
Date: December 2024
"""

import os
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from enum import Enum

# Note: In production, install with: pip install msal requests
# For this spike, we define the interface


class ExcelProvider(Enum):
    """Supported Excel storage providers."""
    ONEDRIVE_PERSONAL = "onedrive_personal"  # Personal OneDrive
    ONEDRIVE_BUSINESS = "onedrive_business"  # OneDrive for Business
    SHAREPOINT = "sharepoint"  # SharePoint Online


@dataclass
class ExcelConfig:
    """Configuration for Excel Online connection."""
    provider: ExcelProvider
    client_id: str  # Azure AD App Client ID
    client_secret: str  # Azure AD App Secret (for app-only flow)
    tenant_id: str  # Azure AD Tenant ID
    workbook_path: str  # Path to workbook (e.g., "/RentasClaras/Inquilinos.xlsx")
    site_id: Optional[str] = None  # Required for SharePoint
    
    @classmethod
    def from_env(cls) -> "ExcelConfig":
        """Load configuration from environment variables."""
        return cls(
            provider=ExcelProvider(os.getenv("EXCEL_PROVIDER", "onedrive_personal")),
            client_id=os.getenv("AZURE_CLIENT_ID", ""),
            client_secret=os.getenv("AZURE_CLIENT_SECRET", ""),
            tenant_id=os.getenv("AZURE_TENANT_ID", ""),
            workbook_path=os.getenv("EXCEL_WORKBOOK_PATH", "/RentasClaras/Inquilinos.xlsx"),
            site_id=os.getenv("SHAREPOINT_SITE_ID"),
        )


# =============================================================================
# EXCEL SCHEMA DEFINITION
# =============================================================================

@dataclass
class TenantRow:
    """
    Represents a row in the "Inquilinos" (Tenants) sheet.
    
    Expected Excel columns:
    A: ID_Inquilino (e.g., "T-001")
    B: Nombre (e.g., "María González")
    C: WhatsApp (e.g., "+528112345001")
    D: Propiedad (e.g., "Ensenada")
    E: Unidad (e.g., "3")
    F: Renta_Mensual (e.g., 4500)
    G: Fecha_Ingreso (e.g., "2024-01-15")
    H: Fecha_Salida (empty if active)
    I: Email (optional)
    """
    tenant_id: str
    name: str
    whatsapp: str
    property_name: str
    unit: str
    monthly_rent: Decimal
    move_in_date: str
    move_out_date: Optional[str]
    email: Optional[str] = None
    
    @classmethod
    def from_row(cls, row: list[Any]) -> "TenantRow":
        """Parse a row from Excel into a TenantRow."""
        return cls(
            tenant_id=str(row[0]) if row[0] else "",
            name=str(row[1]) if row[1] else "",
            whatsapp=str(row[2]) if row[2] else "",
            property_name=str(row[3]) if row[3] else "",
            unit=str(row[4]) if row[4] else "",
            monthly_rent=Decimal(str(row[5])) if row[5] else Decimal("0"),
            move_in_date=str(row[6]) if row[6] else "",
            move_out_date=str(row[7]) if row[7] else None,
            email=str(row[8]) if len(row) > 8 and row[8] else None,
        )


@dataclass
class PaymentRow:
    """
    Represents a row in the "Pagos" (Payments) sheet.
    
    Expected Excel columns:
    A: ID_Pago (auto-generated, e.g., "P-2025-01-001")
    B: ID_Inquilino (e.g., "T-001")
    C: Fecha_Pago (e.g., "2025-01-05")
    D: Monto (e.g., 4850.00)
    E: Metodo (e.g., "Retiro sin tarjeta", "SPEI", "Efectivo")
    F: Codigo_Retiro (if applicable, e.g., "847293")
    G: Banco (if applicable, e.g., "BBVA")
    H: Concepto (e.g., "Renta Enero + Luz")
    I: Folio (e.g., "RC-20250105-00001")
    J: Confirmado (TRUE/FALSE)
    K: Notas (optional)
    """
    payment_id: str
    tenant_id: str
    payment_date: str
    amount: Decimal
    method: str
    withdrawal_code: Optional[str]
    bank: Optional[str]
    concept: str
    folio: str
    confirmed: bool
    notes: Optional[str] = None
    
    def to_row(self) -> list[Any]:
        """Convert to Excel row format."""
        return [
            self.payment_id,
            self.tenant_id,
            self.payment_date,
            float(self.amount),
            self.method,
            self.withdrawal_code or "",
            self.bank or "",
            self.concept,
            self.folio,
            self.confirmed,
            self.notes or "",
        ]


# =============================================================================
# MICROSOFT GRAPH API CLIENT (INTERFACE)
# =============================================================================

class ExcelClient:
    """
    Client for reading/writing Excel Online via Microsoft Graph API.
    
    This is a skeleton implementation. In production:
    1. Use MSAL library for authentication
    2. Handle token refresh
    3. Add proper error handling and retries
    """
    
    BASE_URL = "https://graph.microsoft.com/v1.0"
    
    def __init__(self, config: ExcelConfig):
        self.config = config
        self._access_token: Optional[str] = None
        
    # -------------------------------------------------------------------------
    # Authentication
    # -------------------------------------------------------------------------
    
    def authenticate(self) -> str:
        """
        Authenticate with Microsoft Graph API.
        
        In production, use MSAL:
        ```python
        from msal import ConfidentialClientApplication
        
        app = ConfidentialClientApplication(
            client_id=self.config.client_id,
            client_credential=self.config.client_secret,
            authority=f"https://login.microsoftonline.com/{self.config.tenant_id}"
        )
        
        result = app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )
        
        if "access_token" in result:
            self._access_token = result["access_token"]
            return self._access_token
        else:
            raise AuthenticationError(result.get("error_description"))
        ```
        """
        # Placeholder for spike
        print("🔐 [SPIKE] Would authenticate with Microsoft Graph API")
        self._access_token = "spike_token_placeholder"
        return self._access_token
    
    def _get_workbook_url(self) -> str:
        """Build the Graph API URL for the workbook."""
        if self.config.provider == ExcelProvider.SHAREPOINT:
            return f"{self.BASE_URL}/sites/{self.config.site_id}/drive/root:{self.config.workbook_path}:/workbook"
        else:
            return f"{self.BASE_URL}/me/drive/root:{self.config.workbook_path}:/workbook"
    
    # -------------------------------------------------------------------------
    # Read Operations
    # -------------------------------------------------------------------------
    
    def get_tenants(self, sheet_name: str = "Inquilinos") -> list[TenantRow]:
        """
        Read all tenants from the Inquilinos sheet.
        
        Graph API endpoint:
        GET /me/drive/root:/path/to/file.xlsx:/workbook/worksheets/{sheet}/usedRange
        
        Returns:
            List of TenantRow objects
        """
        url = f"{self._get_workbook_url()}/worksheets/{sheet_name}/usedRange"
        
        # In production:
        # response = requests.get(url, headers={"Authorization": f"Bearer {self._access_token}"})
        # data = response.json()
        # rows = data["values"][1:]  # Skip header row
        # return [TenantRow.from_row(row) for row in rows]
        
        print(f"📊 [SPIKE] Would fetch tenants from: {url}")
        
        # Return dummy data for spike
        return [
            TenantRow(
                tenant_id="T-001",
                name="María González",
                whatsapp="+528112345001",
                property_name="Ensenada",
                unit="3",
                monthly_rent=Decimal("4500"),
                move_in_date="2024-01-15",
                move_out_date=None,
            ),
            TenantRow(
                tenant_id="T-002",
                name="Dr. Carlos Mendoza",
                whatsapp="+528112345002",
                property_name="Ensenada",
                unit="5",
                monthly_rent=Decimal("5200"),
                move_in_date="2024-06-01",
                move_out_date=None,
            ),
        ]
    
    def get_tenant_by_phone(self, phone: str, sheet_name: str = "Inquilinos") -> Optional[TenantRow]:
        """Find a tenant by their WhatsApp number."""
        tenants = self.get_tenants(sheet_name)
        for tenant in tenants:
            # Normalize phone comparison
            if tenant.whatsapp.replace("+", "").replace(" ", "") == phone.replace("+", "").replace(" ", ""):
                return tenant
        return None
    
    
    # -------------------------------------------------------------------------
    # Write Operations
    # -------------------------------------------------------------------------
    
    def add_payment(self, payment: PaymentRow, sheet_name: str = "Pagos") -> bool:
        """
        Add a new payment record to the Pagos sheet.
        
        Graph API endpoint:
        POST /me/drive/root:/path/to/file.xlsx:/workbook/worksheets/{sheet}/tables/{table}/rows/add
        
        Or append to range:
        PATCH /me/drive/root:/path/to/file.xlsx:/workbook/worksheets/{sheet}/range(address='A:K')
        """
        url = f"{self._get_workbook_url()}/worksheets/{sheet_name}/tables/TablaPagos/rows/add"
        
        payload = {
            "values": [payment.to_row()]
        }
        
        # In production:
        # response = requests.post(
        #     url,
        #     headers={
        #         "Authorization": f"Bearer {self._access_token}",
        #         "Content-Type": "application/json"
        #     },
        #     json=payload
        # )
        # return response.status_code == 201
        
        print(f"💾 [SPIKE] Would add payment to: {url}")
        print(f"   Payload: {json.dumps(payload, indent=2, default=str)}")
        return True
    


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def generate_payment_id() -> str:
    """Generate a unique payment ID."""
    now = datetime.now()
    # In production: query Excel to get last ID and increment
    return f"P-{now.strftime('%Y-%m')}-{now.strftime('%H%M%S')}"




# =============================================================================
# WEBHOOK INTEGRATION EXAMPLE
# =============================================================================

def handle_whatsapp_payment(
    sender_phone: str,
    message_text: str,
    attachment_data: Optional[bytes] = None
) -> dict:
    """
    Handle an incoming WhatsApp message about payment.
    
    This would be called by your WhatsApp webhook (Twilio, Meta API, etc.)
    
    Args:
        sender_phone: WhatsApp number of sender
        message_text: Message text
        attachment_data: Image data if screenshot was sent
    
    Returns:
        Response to send back to user
    """
    config = ExcelConfig.from_env()
    client = ExcelClient(config)
    client.authenticate()
    
    # Find tenant
    tenant = client.get_tenant_by_phone(sender_phone)
    if not tenant:
        return {
            "success": False,
            "message": "No encontramos su número registrado. Por favor contacte al administrador."
        }
    
    # If image attached, process with Vision OCR
    if attachment_data:
        # See vision_ocr.py for extraction
        pass
    
    return {
        "success": True,
        "tenant": tenant,
        "message": f"Hola {tenant.name}, recibimos su mensaje."
    }


# =============================================================================
# EXCEL TEMPLATE STRUCTURE
# =============================================================================

EXCEL_TEMPLATE_INFO = """
📊 EXCEL WORKBOOK STRUCTURE
============================

Create an Excel workbook with 3 sheets and tables:

1. SHEET: "Inquilinos" (TABLE: "TablaInquilinos")
   Columns:
   A: ID_Inquilino     | Text    | Primary key (e.g., "T-001")
   B: Nombre           | Text    | Full name
   C: WhatsApp         | Text    | Phone with country code (+52...)
   D: Propiedad        | Text    | Property name (Ensenada, Huichapan, etc.)
   E: Unidad           | Text    | Unit number
   F: Renta_Mensual    | Number  | Monthly rent in MXN
   G: Fecha_Ingreso    | Date    | Move-in date
   H: Fecha_Salida     | Date    | Move-out date (empty if active)
   I: Email            | Text    | Optional email

2. SHEET: "Pagos" (TABLE: "TablaPagos")
   Columns:
   A: ID_Pago          | Text    | Auto-generated ID
   B: ID_Inquilino     | Text    | Foreign key to Inquilinos
   C: Fecha_Pago       | Date    | Payment date
   D: Monto            | Number  | Amount in MXN
   E: Metodo           | Text    | "Retiro sin tarjeta", "SPEI", "Efectivo"
   F: Codigo_Retiro    | Text    | Withdrawal code (if applicable)
   G: Banco            | Text    | Bank name (if applicable)
   H: Concepto         | Text    | Payment description
   I: Folio            | Text    | RentasClaras folio number
   J: Confirmado       | Boolean | TRUE if landlord confirmed
   K: Notas            | Text    | Optional notes

🔧 SETUP INSTRUCTIONS:
1. Create workbook in OneDrive/SharePoint
2. Format each sheet as a Table (Ctrl+T)
3. Name tables as shown above
4. Register Azure AD app with Files.ReadWrite permission
5. Set environment variables (AZURE_CLIENT_ID, etc.)
"""


# =============================================================================
# DEMO
# =============================================================================

def run_excel_demo():
    """Demonstrate Excel integration (spike mode)."""
    print("=" * 70)
    print("🏠 RENTASCLARAS - Excel Online Integration Demo")
    print("=" * 70)
    print()
    
    # Show template info
    print(EXCEL_TEMPLATE_INFO)
    print()
    
    # Simulate operations
    print("=" * 70)
    print("🔄 SIMULATED OPERATIONS")
    print("=" * 70)
    print()
    
    config = ExcelConfig(
        provider=ExcelProvider.ONEDRIVE_PERSONAL,
        client_id="demo-client-id",
        client_secret="demo-secret",
        tenant_id="demo-tenant",
        workbook_path="/RentasClaras/Inquilinos.xlsx"
    )
    
    client = ExcelClient(config)
    client.authenticate()
    
    # Read tenants
    print("\n📋 Reading tenants...")
    tenants = client.get_tenants()
    for t in tenants:
        print(f"   • {t.tenant_id}: {t.name} ({t.property_name} {t.unit}) - ${t.monthly_rent}/mes")
    
    # Add a payment
    print("\n💰 Adding payment...")
    payment = PaymentRow(
        payment_id=generate_payment_id(),
        tenant_id="T-001",
        payment_date=datetime.now().strftime("%Y-%m-%d"),
        amount=Decimal("4850.00"),
        method="Retiro sin tarjeta",
        withdrawal_code="847293102934",
        bank="BBVA",
        concept="Renta Enero 2025 + Luz",
        folio="RC-20250105-00001",
        confirmed=False,
        notes="Código recibido por WhatsApp"
    )
    client.add_payment(payment)
    
    print("\n✅ Demo complete!")


if __name__ == "__main__":
    run_excel_demo()

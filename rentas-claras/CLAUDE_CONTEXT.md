# Rentas Claras - AI Context Document

> **Purpose**: This document provides comprehensive context for AI assistants (Claude, etc.) to understand and contribute to the Rentas Claras project effectively.

---

## 🏠 What is Rentas Claras?

**Rentas Claras** is a Spanish-language **rental property management web app** designed specifically for a 60-year-old Mexican landlord who manages ~32 rental units across 5 properties in Mexico. The app runs as a **Progressive Web App (PWA)** optimized for small-screen iPhones.

### Target User Profile
- **Age**: 60+ years old
- **Tech Comfort**: Prefers pen, paper, and Excel
- **Device**: Small-screen iPhone (SE, Mini)
- **Language**: Spanish (Mexico)
- **Vision**: May need larger text and touch targets
- **Workflow**: Wants simple, clear actions without hidden menus

### Core Problem Solved
Before Rentas Claras, the landlord tracked rent payments in Excel spreadsheets and sent WhatsApp reminders manually to each tenant. This app consolidates:
1. **Rent tracking** - Who paid, who hasn't
2. **WhatsApp reminders** - Bulk messaging via WhatsApp Business API
3. **Contract management** - Track expiring leases
4. **Deposit tracking** - Security deposit status
5. **Automated reminders** - Scheduled payment reminders

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend** | Python 3.11 + Flask |
| **Database** | SQLite with WAL mode (persistent volume on Fly.io) |
| **Frontend** | Vanilla HTML/CSS/JS + Jinja2 templates |
| **Styling** | CSS custom properties (no frameworks) |
| **Fonts** | Inter (Google Fonts) |
| **Hosting** | Fly.io (single machine + persistent volume) |
| **Messaging** | WhatsApp Business Cloud API |
| **Scheduler** | APScheduler for automated reminders |
| **PWA** | Service worker for offline support |

### Key Files
```
rentas-claras/
├── app.py                    # Flask app entry point
├── database.py               # SQLite database module (~1600 lines)
├── fly.toml                  # Fly.io deployment config (CRITICAL: has [mounts])
├── routes/                   # Flask blueprints
│   ├── pagos.py              # Main rent tracking page
│   ├── contratos.py          # Contract management
│   ├── depositos.py          # Security deposits
│   ├── reminders.py          # WhatsApp reminder page
│   └── tenants.py            # Tenant CRUD API
├── services/                 # Business logic modules
│   ├── dates.py              # Spanish date formatting (SINGLE SOURCE OF TRUTH)
│   ├── late_fees.py          # Late fee calculation
│   ├── messages.py           # WhatsApp message templates
│   └── validation.py         # Input validation
├── templates/                # Jinja2 HTML templates
│   ├── pagos.html            # "Rentas" - main payment tracking (~2600 lines)
│   ├── contratos.html        # Contract expiry tracking
│   ├── depositos.html        # Deposit management
│   ├── recordatorios.html    # WhatsApp reminder sender
│   ├── dashboard.html        # Home/summary page
│   └── partials/             # Reusable components
│       ├── bottom_nav.html   # Mobile bottom navigation
│       └── search_box.html   # Tenant search component
├── src/
│   ├── scheduler.py          # APScheduler for automated reminders
│   └── whatsapp_client.py    # WhatsApp Business API client
└── scripts/
    └── pre-deploy-check.sh   # Validates fly.toml before deploy
```

---

## 📱 App Pages & Features

### 1. **Rentas** (Main Page - `/`)
The primary page landlord uses daily.
- Lists all tenants grouped by property
- Shows paid ✅ vs unpaid ❌ status with visual cards
- Tap tenant card to mark as paid (with payment method selection)
- Shows late fees calculated automatically (day 6+)
- Search by tenant name, property, or unit
- Month navigation to view historical data
- Collapsible "Pagados" section to focus on unpaid

**Key Logic:**
- Tenants starting a contract in the current billing month are EXCLUDED (they don't owe rent yet)
- After day 7 of month, billing auto-switches to next month
- Late fees: 10% after day 5, +5% per week thereafter

### 2. **Contratos** (`/contratos`)
Contract expiry management.
- Shows tenants with contracts expiring in next 60 days
- Urgency levels with color coding:
  - 🔴 **Urgent** (≤7 days) - Red
  - 🟠 **Soon** (8-14 days) - Orange
  - 🔵 **OK** (15-21 days) - Blue
  - ⚪ **Later** (22-31 days) - Gray
- Track renewal status: "Renovará" / "No renovará" / "Pendiente"
- Replacement tenant info for those leaving

### 3. **Depósitos** (`/depositos`)
Security deposit tracking.
- Track deposit paid/returned status per tenant
- Editable deposit amounts
- Export to Excel

### 4. **Recordatorios** (`/recordatorios`)
WhatsApp reminder sender.
- Select multiple tenants with checkboxes
- Preview message before sending
- Sends via WhatsApp Business API
- Tracks message delivery status

### 5. **Inicio/Dashboard** (`/resumen`)
Summary home page.
- Quick stats: total collected, pending, collection rate
- Links to other sections
- Contract expiry warnings

---

## 🎨 Design Philosophy

### Accessibility-First for Elderly Users
- **Large touch targets**: 56px+ buttons (exceeds WCAG's 44px minimum)
- **High contrast**: Green (#2D6A4F) on white
- **16px+ base font**: `var(--text-base)` = 17px
- **No hidden menus**: All navigation visible in bottom nav
- **Spanish language**: Fully localized ("Pagos", "Contratos", etc.)
- **Familiar patterns**: Excel export, print-friendly layouts

### Visual Design
- **Color palette**:
  - Primary: `--green: #2D6A4F` (dark green)
  - Success: `--green-light: #D1FAE5`
  - Error: `--red: #9B2C2C`
  - Warning: `--yellow: #FEFCBF`
  - Text: `--gray-dark: #1a1a1a`
- **Typography**: Inter font family
- **Cards**: White background with subtle shadows
- **Property sections**: Color-coded left borders (green, blue, purple, orange, pink)

### Mobile-First
- Bottom navigation bar (5 tabs)
- Sticky search box
- Collapsible sections to reduce scrolling
- Safe area handling for iPhone notch

---

## 🗄️ Database Schema

### Main Tables

**`tenants`** - Master tenant list
```sql
- id (TEXT PRIMARY KEY)           -- e.g., "MAT-A", "ENS-1"
- name (TEXT)                     -- "Sergio y Kenner"
- phone (TEXT)                    -- "+52 123 456 7890"
- property_name (TEXT)            -- "Matehuala", "Ensenada"
- unit (TEXT)                     -- "A", "1"
- rent (REAL)                     -- 9800.00
- contract_start (TEXT)           -- "2026-01-01"
- contract_end (TEXT)             -- "2026-06-30"
- active (INTEGER DEFAULT 1)
- renewal_status (TEXT)           -- "renovará", "no_renovará", "pendiente"
- aval_name, aval_phone           -- Guarantor info
- deposit_amount, deposit_paid    -- Security deposit tracking
```

**`monthly_records`** - Payment status per month
```sql
- tenant_id (TEXT)
- year (INTEGER)
- month (INTEGER)
- paid (INTEGER)                  -- 0 or 1
- payment_method (TEXT)           -- "Efectivo", "Transferencia"
- payment_date (TEXT)
- visits, visit_charge            -- Extra charges
```

**`message_log`** - WhatsApp message tracking
```sql
- tenant_id, year, month
- message_type (TEXT)             -- "reminder", "late_notice"
- sent_at (TEXT)
- status (TEXT)                   -- "sent", "delivered", "failed"
- whatsapp_message_id (TEXT)
```

---

## 🔐 Security & Privacy

### Authentication
- PIN-based login (4-digit code stored in `RENTASCLARAS_PIN` env var)
- Session-based authentication via Flask

### Data Privacy
- **Database** (`*.db`) is gitignored - contains real tenant PII
- **Tenant seed files** are gitignored
- Production database on Fly.io persistent volume (not in container)
- All API endpoints protected with `@login_required` decorator

### Sensitive Environment Variables
```bash
SECRET_KEY              # Flask session encryption
RENTASCLARAS_PIN        # Login PIN
WHATSAPP_ACCESS_TOKEN   # Meta WhatsApp API token
WHATSAPP_PHONE_NUMBER_ID
WHATSAPP_WEBHOOK_VERIFY_TOKEN
```

---

## 🚀 Deployment

### Fly.io Setup
- Single machine deployment
- **Persistent volume**: `clara_data` mounted at `/data`
- Database path: `/data/rentas_claras.db`

### Deployment Command
```bash
./scripts/pre-deploy-check.sh && git push origin main && fly deploy
```

### ⚠️ CRITICAL: Data Loss Prevention
A 2025-12-29 incident caused data loss when the `[mounts]` section was accidentally deleted from `fly.toml`.

**Rules:**
1. NEVER use `write_to_file` on `fly.toml` - use `str_replace_edit`
2. ALWAYS run `pre-deploy-check.sh` before deploy
3. The `[mounts]` section is CRITICAL - without it, database is ephemeral

---

## 🎯 Feature Ideas for Future Development

### High-Value Features for Target User

1. **Monthly PDF Reports**
   - Generate printable monthly summary
   - Include: total collected, pending, late fees, occupancy rate
   - Email to landlord automatically

2. **WhatsApp Quick Replies**
   - "Pagué" auto-marks tenant as paid
   - Confirmation number in response

3. **Expense Tracking**
   - Record property maintenance expenses
   - Calculate net income per property

4. **Vacancy Alerts**
   - Notify when contract expires without renewal
   - Track days vacant per unit

5. **Payment History Timeline**
   - Show payment patterns per tenant
   - Flag consistently late payers

6. **Bank Reconciliation**
   - Import bank statements
   - Match transfers to tenants

7. **Multi-Language**
   - English for properties in US (some landlords have both)

8. **Tenant Portal**
   - Tenants can see their payment history
   - Submit maintenance requests

9. **Voice Commands**
   - "Marca a Juan como pagado" via Siri
   - Accessibility for elderly

10. **Offline-First Enhancements**
    - Queue payments when offline
    - Sync when back online

### Technical Improvements

1. **Full-Text Search**
   - SQLite FTS5 for tenant search

2. **Data Backup Automation**
   - Daily backup to cloud storage
   - One-click restore

3. **Analytics Dashboard**
   - Collection rate trends
   - Property performance comparison

4. **API for Integrations**
   - Zapier/Make webhooks
   - Accounting software sync

---

## 📋 Known Quirks & Conventions

1. **Billing Month Logic**
   - After day 7, the app shows NEXT month as current billing period
   - This matches when rent is typically due (1st-5th of month)

2. **Tenant IDs**
   - Format: `{PROPERTY_CODE}-{UNIT}` (e.g., "MAT-A", "ENS-1")
   - Property codes: MAT (Matehuala), MUZ (Múzquiz), ENS (Ensenada), HUI (Huichapan), PDS (Puerta Del Sol)

3. **Split Tenants**
   - When roommates pay separately, they get separate tenant records
   - e.g., "MAT-B" (J Carlos, $4200) and "MAT-B2" (Raul, $4200)

4. **Contract Start Filter**
   - Tenants whose `contract_start` is in the current billing month don't appear in rent tracking
   - They don't owe rent for their first month if starting on the 1st

5. **Spanish Date Formatting**
   - "12 de enero 2025" format
   - All month names lowercase: "enero", "febrero", etc.

---

## 🐛 Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Database empty after deploy | Check `fly.toml` has `[mounts]` section |
| WhatsApp messages not sending | Verify `WHATSAPP_ACCESS_TOKEN` is valid |
| CSS not updating | Clear browser cache or hard refresh |
| Port 5001 in use | Kill existing process: `lsof -ti:5001 \| xargs kill` |
| Jinja2 linter errors | Ignore - VS Code JS linter doesn't understand `{{ }}` |

---

## 📞 Support Info

- **Live URL**: https://rentas-claras.fly.dev/
- **Repo**: GitHub (private)
- **Owner**: Zelma
- **Target User**: 60-year-old landlord in Mexico

---

*Last updated: January 2026*

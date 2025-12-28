# RentasClaras Product Roadmap
## ROI-Prioritized Milestones

**Last Updated:** December 28, 2024
**Current State:** MVP with 3 substantial features, 2 not started, 1 spike-level

---

## Executive Summary

| Priority | Feature | Current State | ROI Impact | Effort |
|----------|---------|---------------|------------|--------|
| 🥇 P0 | Cobranza Automática | 85% done | 💰💰💰💰💰 | 🔧 Low |
| 🥈 P1 | Sincronización Excel | 40% spike | 💰💰💰💰 | 🔧🔧🔧 High |
| 🥉 P2 | Cálculo de Luz | 80% done | 💰💰💰 | 🔧🔧 Medium |
| 4️⃣ P3 | Gestión de Contratos | 75% done | 💰💰💰 | 🔧 Low |
| 5️⃣ P4 | Control de Depósitos | 0% | 💰💰 | 🔧🔧 Medium |
| 6️⃣ P5 | Fugas por Visitas | 0% | 💰 | 🔧🔧 Medium |

---

## 🥇 MILESTONE 1: Cobranza Completa (Week 1-2)
### *"Que el sistema cobre solo, sin intervención"*

**Business Value:** Elimina ~4 horas/semana de trabajo manual + elimina la carga emocional de cobrar

### What's Built ✅
- Late fee engine: $500 inicial + $100/día (max 5 días)
- WhatsApp Cloud API integration
- Manual "Enviar recordatorio" button
- Payment tracking in SQLite

### What's Missing ❌

| Task | Description | Files to Modify | Effort |
|------|-------------|-----------------|--------|
| **Wire scheduler** | Connect APScheduler to Flask app | `app.py`, `requirements.txt` | 2hrs |
| **Auto-trigger Day 2** | Send late notice automatically at 9am on día 2 | `src/scheduler.py` | 3hrs |
| **Auto-trigger Day 8** | Send critical notice on día 8 | `src/scheduler.py` | 1hr |
| **Escalation templates** | Adjust message tone for Day 2 vs Day 8 | `src/whatsapp_client.py` | 2hrs |

### Deliverables
```
✓ Automated rent reminder on Day 1 (or last day before due)
✓ Automated late notice on Day 2 ($500 penalty warning)
✓ Automated escalation on Day 8 (critical + contract clause)
✓ Zero manual intervention required
```

### Dependencies
```bash
pip install apscheduler
```

### Success Metric
> **Before:** Manual button clicks daily for 32 tenants
> **After:** 0 clicks, system runs autonomously

---

## 🥈 MILESTONE 2: Sincronización con Excel (Week 3-5)
### *"WhatsApp → OCR → Excel automático"*

**Business Value:** Elimina ~2 horas/semana de transcripción manual de códigos de pago

### What's Built ✅
- `ExcelClient` class structure (spike)
- `VisionOCR` class structure (spike)
- Payment endpoint `/api/payment`
- `PaymentRow` dataclass

### What's Missing ❌

| Task | Description | Files to Modify | Effort |
|------|-------------|-----------------|--------|
| **Add real dependencies** | `msal`, `openai` in requirements | `requirements.txt` | 30min |
| **Azure AD App Registration** | Create app in Azure Portal for Graph API | External | 1hr |
| **Implement Microsoft Graph** | Real `add_payment()` → Excel Online | `src/excel_client.py` | 6hrs |
| **Implement OpenAI Vision** | Real `extract_withdrawal_code()` | `src/vision_ocr.py` | 4hrs |
| **WhatsApp media webhook** | Endpoint to receive photos from tenants | `app.py` | 6hrs |
| **Confirmation flow** | Bot asks "¿Es correcto este código: XXXX?" | `src/whatsapp_client.py` | 4hrs |

### Architecture
```
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│ Tenant sends    │───►│ WhatsApp     │───►│ Flask       │
│ payment photo   │    │ Cloud API   │    │ /webhook    │
└─────────────────┘    └──────────────┘    └─────────────┘
                                                  │
                                                  ▼
                                          ┌─────────────┐
                                          │ GPT-4V OCR  │
                                          │ Extract:    │
                                          │ - Code      │
                                          │ - Amount    │
                                          │ - Bank      │
                                          └─────────────┘
                                                  │
                                                  ▼
                                          ┌─────────────┐
                                          │ Confirm via │
                                          │ WhatsApp    │
                                          └─────────────┘
                                                  │
                                                  ▼
                                          ┌─────────────┐
                                          │ Excel Online│
                                          │ Graph API   │
                                          │ + SQLite    │
                                          └─────────────┘
```

### Dependencies
```bash
pip install msal openai
```

### Environment Variables Needed
```
AZURE_CLIENT_ID=xxx
AZURE_CLIENT_SECRET=xxx
AZURE_TENANT_ID=xxx
EXCEL_FILE_ID=xxx
OPENAI_API_KEY=xxx
```

### Success Metric
> **Before:** Tenant sends screenshot → you manually copy code to Excel
> **After:** Tenant sends screenshot → auto-confirmed → auto-synced

---

## 🥉 MILESTONE 3: Cálculo de Luz Completo (Week 6-7)
### *"Subir foto de recibo CFE → prorrateo automático"*

**Business Value:** Elimina ~1 hora/mes de cálculo manual + elimina errores de prorrateo

### What's Built ✅
- `calculate_tenant_utilities()` with property configs
- Matehuala A 50% subsidy configured
- Shared meter splitting logic
- Pro-rating by occupancy days

### What's Missing ❌

| Task | Description | Files to Modify | Effort |
|------|-------------|-----------------|--------|
| **Bill upload endpoint** | `/api/upload/bill` receives CFE photo | `app.py` | 3hrs |
| **CFE OCR prompt** | Extract kWh, amount, billing period | `src/vision_ocr.py` | 4hrs |
| **Bill storage** | Save bill photos with metadata | `database.py` | 2hrs |
| **Utility breakdown UI** | Show per-tenant calculation on dashboard | `app.py` (template) | 4hrs |
| **Integration with rent** | Add utility amount to monthly total | `src/late_fees.py` | 2hrs |

### Formula Reference (Already Implemented)
```python
# Shared meter (Ensenada, Huichapan)
tenant_share = total_bill / num_tenants

# Landlord split (Matehuala A - 50% subsidy)
tenant_share = (total_bill * 0.50) / num_tenants

# Pro-rated by occupancy
tenant_share = (tenant_share * days_occupied) / days_in_period
```

### Success Metric
> **Before:** Manual CFE bill calculation with calculator + Excel
> **After:** Upload photo → system calculates → adds to rent total

---

## 4️⃣ MILESTONE 4: Alertas de Contratos (Week 8)
### *"Notificación automática 60 días antes de vencimiento"*

**Business Value:** Previene vacantes sorpresa + da tiempo para buscar reemplazos

### What's Built ✅
- `contract_end` dates in database
- `get_expiring_contracts(days_ahead=60)` query
- `/contratos` page with renewal status
- Urgency highlighting (critical/warning/info)

### What's Missing ❌

| Task | Description | Files to Modify | Effort |
|------|-------------|-----------------|--------|
| **Scheduled check** | Daily job to find expiring contracts | `src/scheduler.py` | 2hrs |
| **Admin WhatsApp alerts** | Send to landlord when contract expires in 60/30/7 days | `src/whatsapp_client.py` | 3hrs |
| **Tenant reminder** | "Tu contrato vence en X días" message | `src/whatsapp_client.py` | 2hrs |

### Alert Schedule
```
60 días: "Contrato de [Tenant] vence el [Date]. Confirmar renovación."
30 días: "Quedan 30 días. Status: [Pendiente/Renovará/No renovará]"
 7 días: "URGENTE: Contrato vence en 7 días."
```

### Success Metric
> **Before:** Check contracts manually, sometimes forget
> **After:** Automatic WhatsApp reminders at 60/30/7 days

---

## 5️⃣ MILESTONE 5: Control de Depósitos (Week 9-10)
### *"Trackear estado de cada depósito para la finiquito"*

**Business Value:** Facilita decisiones de finiquito + evita disputas

### What's Built ✅
- Nothing (0%)

### What Needs to Be Built ❌

| Task | Description | Files to Modify | Effort |
|------|-------------|-----------------|--------|
| **Database schema** | `deposits` table | `database.py` | 2hrs |
| **CRUD functions** | `add_deposit()`, `update_deposit_status()`, `get_deposit()` | `database.py` | 3hrs |
| **Deposits UI** | View/edit deposits per tenant | `app.py` (new page) | 6hrs |
| **Finiquito calculation** | Auto-calculate: deposit - damages - unpaid rent | `src/finiquito.py` (new) | 4hrs |
| **Finiquito report** | Generate PDF/printable finiquito document | `src/finiquito.py` | 4hrs |

### Database Schema
```sql
CREATE TABLE deposits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    amount REAL NOT NULL,
    deposit_date TEXT NOT NULL,
    status TEXT DEFAULT 'held',  -- 'held', 'applied', 'refunded', 'partial'
    applied_amount REAL DEFAULT 0,
    refund_amount REAL DEFAULT 0,
    refund_date TEXT,
    notes TEXT,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);
```

### Status Flow
```
held ──► applied (deducted for damages/unpaid rent)
  │
  └──► refunded (returned to tenant)
  │
  └──► partial (some applied, some refunded)
```

### Success Metric
> **Before:** Track deposits in mental notes or separate Excel
> **After:** All deposits visible with clear status + auto-calculated finiquito

---

## 6️⃣ MILESTONE 6: Cobro por Visitas Extra (Week 11-12)
### *"Registrar fugas/daños y cobrar automáticamente"*

**Business Value:** Recupera ingresos perdidos por no dar seguimiento

### What's Built ✅
- Nothing (0%)

### What Needs to Be Built ❌

| Task | Description | Files to Modify | Effort |
|------|-------------|-----------------|--------|
| **Database schema** | `extra_charges` table | `database.py` | 2hrs |
| **CRUD functions** | `add_charge()`, `get_charges_for_tenant()` | `database.py` | 2hrs |
| **Charges UI** | Log extra charges per tenant | `app.py` (new section) | 5hrs |
| **Integration with rent** | Auto-add charges to monthly total | `src/late_fees.py` | 3hrs |
| **Photo evidence** | Upload damage photos | `app.py`, storage | 4hrs |

### Database Schema
```sql
CREATE TABLE extra_charges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    charge_date TEXT NOT NULL,
    charge_type TEXT NOT NULL,  -- 'fuga', 'daño', 'visita_extra', 'limpieza'
    description TEXT,
    amount REAL NOT NULL,
    applied_to_month TEXT,  -- '2024-12' = charged in Dec rent
    photo_path TEXT,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);
```

### Charge Types
| Type | Example | Typical Amount |
|------|---------|----------------|
| `fuga` | Water leak repair | $200-500 |
| `daño` | Broken window | Varies |
| `visita_extra` | 3rd maintenance visit | $150 |
| `limpieza` | Deep cleaning | $300 |

### Success Metric
> **Before:** Forget to charge for extra visits, lose that income
> **After:** Log charge → auto-added to next rent → nothing gets lost

---

## 📅 Complete Timeline

```
Week 1-2   │ ████████████████████████ │ M1: Cobranza Automática
Week 3-5   │ ████████████████████████████████████ │ M2: Sync Excel + OCR
Week 6-7   │ ████████████████████████ │ M3: Cálculo de Luz
Week 8     │ ████████████ │ M4: Alertas Contratos
Week 9-10  │ ████████████████████████ │ M5: Control Depósitos
Week 11-12 │ ████████████████████████ │ M6: Cobro Visitas Extra
```

**Total:** ~12 weeks to complete product

---

## 💰 ROI Analysis

### Time Saved Per Month
| Feature | Hours/Month Before | Hours/Month After | Savings |
|---------|-------------------|-------------------|---------|
| Cobranza manual | 16 hrs | 0 hrs | **16 hrs** |
| Transcribir Excel | 8 hrs | 0 hrs | **8 hrs** |
| Calcular luz | 2 hrs | 0.5 hrs | **1.5 hrs** |
| Revisar contratos | 2 hrs | 0 hrs | **2 hrs** |
| Control depósitos | 1 hr | 0.5 hrs | **0.5 hrs** |
| Seguimiento visitas | 2 hrs | 0.5 hrs | **1.5 hrs** |
| **TOTAL** | **31 hrs** | **1.5 hrs** | **29.5 hrs** |

### Money Recovered
| Feature | Lost Before | Recovered After |
|---------|-------------|-----------------|
| Late fees not applied | ~$2,000/mo | $2,000/mo |
| Extra charges not followed up | ~$500/mo | $500/mo |
| **TOTAL** | **$2,500/mo** | **$2,500/mo recovered** |

---

## 🔧 Technical Prerequisites

### Dependencies to Add
```txt
# requirements.txt additions
apscheduler>=3.10.0
msal>=1.24.0
openai>=1.0.0
```

### Environment Variables to Configure
```bash
# .env additions
AZURE_CLIENT_ID=your-azure-app-id
AZURE_CLIENT_SECRET=your-azure-secret
AZURE_TENANT_ID=your-azure-tenant
EXCEL_FILE_ID=your-excel-file-id
OPENAI_API_KEY=your-openai-key
```

### External Setup Required
1. **Azure AD App Registration** - For Microsoft Graph API (Excel Online)
2. **WhatsApp Business API** - Already configured ✅
3. **OpenAI API Account** - For Vision OCR

---

## 🎯 Quick Wins (Can Do Today)

1. **Add APScheduler** - `pip install apscheduler` + wire to Flask
2. **Create deposits table** - 10 lines of SQL in `database.py`
3. **Create extra_charges table** - 10 lines of SQL in `database.py`
4. **Connect scheduler to existing WhatsApp code** - Functions exist, just need trigger

---

## Next Step Recommendation

**Start with Milestone 1 (Cobranza Automática)** because:
- ✅ 85% already built
- ✅ Highest time savings (16 hrs/month)
- ✅ Lowest effort to complete (~8 hrs)
- ✅ Immediate emotional relief (no more manual cobrar)
- ✅ Foundation for other automated features

Would you like me to start implementing Milestone 1?

# RentasClaras MVP
## Product Requirements Document

**Version:** 1.0
**Date:** December 27, 2024
**Author:** Product & AI Architecture Team
**Status:** Draft

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [User Personas](#2-user-personas)
3. [Functional Requirements](#3-functional-requirements)
4. [Technical Constraints](#4-technical-constraints)
5. [User Stories](#5-user-stories)
6. [Core Logic & Formulas](#6-core-logic--formulas)
7. [Agent Personality & Tone](#7-agent-personality--tone)
8. [Success Metrics](#8-success-metrics)
9. [Appendix: Sample Agent Messages](#9-appendix-sample-agent-messages)

---

## 1. Executive Summary

### The "Why" Behind RentasClaras

**RentasClaras** (lit. "Clear Rents") is a WhatsApp-based AI agent designed to eliminate the operational chaos of managing rental properties in Monterrey, Mexico.

#### The Problem

Traditional landlording in Nuevo León is a fragmented, manual, and increasingly legally risky endeavor:

| Pain Point | Current Reality | Impact |
|------------|-----------------|--------|
| **Utility Chaos** | 32 tenants share various electricity meters across 4 properties. Calculations are done by hand, pro-rated by days of occupancy. | Hours of error-prone math each billing cycle. Disputes. Unpaid balances. |
| **Shadow Economy** | Payments arrive via "Retiros sin Tarjeta" (cardless ATM withdrawals) or SPEI transfers. Landlords physically visit ATMs to retrieve expiring codes. | Full days lost at ATMs. Missed codes = lost rent. |
| **Legal Shift (2025)** | Nuevo León's new tenant protection laws make traditional enforcement (cutting power, lockouts) illegal. Formal, timestamped proof of payment requests is now mandatory. | Risk of lawsuits. Inability to evict non-paying tenants without paper trail. |
| **Data Silos** | Maintenance records, receipts, and tenant history live in physical paper folders. | No lifecycle view. Lost warranties. Repeated issues undiagnosed. |

#### The Solution

RentasClaras is a **"Lightweight AI Socio"** that handles the "Dirty Work" of landlording through a familiar WhatsApp interface:

- 📸 **Snap a CFE bill** → AI splits it fairly across tenants.
- 🤖 **Automated "Bad Cop"** → Polite, persistent, legally-compliant payment reminders.
- 🏧 **ATM Ledger** → Extracts withdrawal codes from chat, tracks redemptions.
- 🔧 **Maintenance Digitizer** → Photo of paper receipt → searchable digital record.

#### Target Users

- **Primary:** The Garza family (operators of 32 units across Matehuala, Músquiz, Ensenada, and Huichapan properties).
- **Secondary:** Small-scale landlords in Nuevo León facing similar operational burdens.

#### Business Value

| Metric | Before RentasClaras | After RentasClaras |
|--------|---------------------|---------------------|
| Time spent on CFE calculations | 4-6 hours/month | 15 minutes/month |
| ATM trips for code redemptions | 8-12/month | Tracked remotely, batch trips |
| Payment collection rate | ~78% on-time | Target: 92% on-time |
| Legal compliance (2025) | Manual, inconsistent | 100% automated receipts |

---

## 2. User Personas

### 2.1 The Traditional Landlord — "El Operador"

**Name:** Don Raúl (composite of real users)
**Age:** 58
**Tech Comfort:** WhatsApp, basic smartphone, no apps beyond banking
**Properties:** 32 units across 4 buildings

#### Goals
- Collect rent on time without confrontation
- Split CFE bills fairly (and defensibly)
- Stay compliant with 2025 laws without becoming a lawyer
- Know when the boiler in Unit 7 was last serviced

#### Frustrations
- "I spend entire Saturdays at the ATM waiting for codes to arrive."
- "Every month I do the same division by hand. One mistake and tenants call me a thief."
- "The new laws scare me. How do I prove I asked for payment?"
- "I know we fixed the leak in 4B... but when? And who did the work?"

#### Behavior Patterns
- Communicates almost exclusively via WhatsApp text messages and photos
- Trusts paper over digital (but paper gets lost)
- Prefers "trato directo" (personal dealings) but needs to scale

#### RentasClaras Value Proposition
> "Tu socio digital que hace las cuentas, cobra a los morosos, y guarda los recibos — todo por WhatsApp."

---

### 2.2 The Medical Resident / Student — "El Inquilino"

**Name:** Dra. Fernanda (composite)
**Age:** 27
**Tech Comfort:** Digital native, uses apps for everything
**Situation:** Renting a small unit near Hospital Universitario; 36-hour shifts common

#### Goals
- Pay bills quickly and forget about them
- Clear, itemized breakdown (no surprises)
- Flexible payment options (SPEI, card, Oxxo)
- Minimal landlord interaction unless necessary

#### Frustrations
- "I get a WhatsApp at 11pm saying I owe $847.32 for luz. Where does that number come from?"
- "The landlord wants me to go to Oxxo and read him a code over the phone. It's 2024."
- "I requested a receipt once. I'm still waiting."

#### Behavior Patterns
- Checks messages between patients; needs scannable information
- Trusts automation; distrusts handwritten math
- Will pay immediately if given a one-tap payment link

#### RentasClaras Value Proposition
> "Recibe tu desglose de luz en un mensaje claro, paga con un clic, y olvídate."

---

## 3. Functional Requirements

### 3.1 Module 1: The AI Utility Splitter

**Purpose:** Transform a photograph of a CFE electricity bill into individualized, fair, and defensible payment requests for each tenant.

#### Inputs
| Input | Source | Format |
|-------|--------|--------|
| CFE Bill Photo | Landlord via WhatsApp | JPEG/PNG image |
| Property Identifier | Landlord confirmation | Text (e.g., "Ensenada") |
| Tenant Occupancy Data | System database | Structured (tenant_id, unit, move_in, move_out, meter_id) |

#### Processing Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                     UTILITY SPLITTER FLOW                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  📸 Photo of CFE Bill                                           │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────────┐                                            │
│  │   Vision OCR    │  Extract: total, period, meter number      │
│  │   (GPT-4V)      │                                            │
│  └────────┬────────┘                                            │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │  Human Review   │  "¿Es correcto? Total: $5,234.00           │
│  │  (Landlord)     │   Periodo: Nov 15 - Dic 14"                │
│  └────────┬────────┘                                            │
│           │ ✓ Confirmed                                          │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │  Pro-Rate       │  Apply formula per tenant                  │
│  │  Calculation    │  (see Section 6.1)                         │
│  └────────┬────────┘                                            │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │  Generate       │  Create individual messages                │
│  │  Messages       │  with payment links                        │
│  └────────┬────────┘                                            │
│           │                                                      │
│           ▼                                                      │
│  📤 Send to each tenant via WhatsApp                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Outputs
| Output | Recipient | Format |
|--------|-----------|--------|
| Extraction Confirmation | Landlord | WhatsApp message with parsed data |
| Individual Payment Request | Each Tenant | WhatsApp message with breakdown + payment link |
| Calculation Log | System | JSON record for auditing |

#### Edge Cases
| Scenario | Handling |
|----------|----------|
| Partial month occupancy | Pro-rate by exact days (move-in date to period end or move-out) |
| Mid-cycle tenant change | Both tenants charged for their respective days |
| Unreadable bill photo | Request re-photo with guidance ("toma la foto de frente, con buena luz") |
| Multiple meters, one bill | Map meter number to tenant subset; split only among relevant units |

---

### 3.2 Module 2: The "Bad Cop" Collector

**Purpose:** Automate payment follow-ups in a tone that is firm but respectful, generating legally-compliant PDF receipts at every touchpoint.

#### Collection Sequence

```
┌──────────────────────────────────────────────────────────────────────────┐
│                      "BAD COP" COLLECTION TIMELINE                        │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  Day 0 (Bill Sent)                                                       │
│  ├─ Initial payment request (friendly)                                   │
│  └─ PDF: "Solicitud de Pago #001"                                        │
│                                                                           │
│  Day 3 (No Payment)                                                       │
│  ├─ First reminder (still friendly)                                       │
│  └─ "Solo un recordatorio amable..."                                      │
│                                                                           │
│  Day 7 (No Payment)                                                       │
│  ├─ Second reminder (firmer)                                              │
│  └─ "Notamos que el pago sigue pendiente..."                              │
│                                                                           │
│  Day 10 (No Payment)                                                      │
│  ├─ Final notice (formal)                                                 │
│  └─ PDF: "Aviso Formal de Adeudo"                                         │
│  └─ "De acuerdo con su contrato, este es un aviso formal..."              │
│                                                                           │
│  Day 14+ (Escalation)                                                     │
│  ├─ Landlord notified for manual intervention                             │
│  └─ Full PDF trail available for legal proceedings                        │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

#### PDF Receipt Generation (2025 Compliance)

Every payment request generates a timestamped PDF containing:

| Field | Example |
|-------|---------|
| Fecha de Emisión | 2024-12-27 14:32:05 CST |
| Nombre del Arrendador | Raúl Garza Martínez |
| Nombre del Inquilino | Fernanda López Reyes |
| Concepto | Prorrateo de energía eléctrica (CFE) |
| Periodo | Nov 15 - Dic 14, 2024 |
| Monto | $847.32 MXN |
| Fecha Límite de Pago | Dic 20, 2024 |
| Folio Único | RC-2024-1227-00047 |
| Estado | Pendiente / Pagado |

#### Payment Detection

The system monitors for:
1. **SPEI confirmation screenshots** sent by tenant
2. **Cardless withdrawal confirmations** (see Module 3)
3. **Manual landlord confirmation** via chat command

Upon detection → status updates to "Pagado" → confirmation sent to tenant.

---

### 3.3 Module 3: The ATM Ledger

**Purpose:** Extract cardless withdrawal codes from tenant messages, track their expiration, and reconcile with actual ATM redemptions.

#### "Retiro sin Tarjeta" Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    ATM LEDGER WORKFLOW                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Tenant sends code via WhatsApp:                                │
│  "Ahí le dejo el retiro:                                        │
│   Código: 847293                                                 │
│   Monto: $3,200                                                  │
│   Vence: 27 dic 8pm"                                            │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────────┐                                            │
│  │   NLP Parser    │  Extract: code, amount, expiry             │
│  │                 │  Map to: tenant_id, pending_balance        │
│  └────────┬────────┘                                            │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │  Confirmation   │  "✓ Registrado. Código 847293              │
│  │  to Tenant      │   por $3,200 vence hoy 8pm."               │
│  └────────┬────────┘                                            │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │  Landlord       │  "Nuevo código de María (4B):              │
│  │  Notification   │   847293 - $3,200 - Vence 8pm"             │
│  └────────┬────────┘                                            │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │  Expiry         │  2 hours before: Alert landlord            │
│  │  Monitoring     │  On expiry: Mark as expired if unredeemed  │
│  └────────┬────────┘                                            │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │  Redemption     │  Landlord confirms: "Retiré 847293"        │
│  │  Confirmation   │  → Tenant notified, balance updated         │
│  └─────────────────┘                                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Ledger Schema

```json
{
  "withdrawal_id": "WD-2024-1227-003",
  "tenant_id": "T-ENS-4B",
  "tenant_name": "María González",
  "code": "847293",
  "amount_mxn": 3200.00,
  "sent_at": "2024-12-27T14:15:00-06:00",
  "expires_at": "2024-12-27T20:00:00-06:00",
  "status": "pending|redeemed|expired",
  "redeemed_at": null,
  "notes": ""
}
```

---

### 3.4 Module 4: Maintenance Digitizer (Phase 2)

**Purpose:** Convert photos of physical maintenance receipts into searchable, structured digital records.

#### Lifecycle Log Entry

| Field | Source |
|-------|--------|
| Fecha | OCR from receipt |
| Proveedor | OCR + landlord confirmation |
| Concepto | OCR + AI categorization |
| Unidad/Área | Landlord input |
| Monto | OCR from receipt |
| Garantía | Landlord input (optional) |
| Foto del Recibo | Attached image |

#### Future Capabilities (v2+)
- Warranty expiration alerts
- Recurring issue detection ("Third plumber visit to 7A this year")
- Vendor performance tracking

---

## 4. Technical Constraints

### 4.1 WhatsApp as Primary UI

| Constraint | Implication |
|------------|-------------|
| No custom UI | All interactions via chat bubbles, buttons (limited), and media |
| Message limits | Max 4096 characters per message; longer content must be split or sent as PDF |
| Media processing | Images processed via Cloud API; must handle compression artifacts |
| Session window | 24-hour messaging window; templates required for outbound beyond window |

#### WhatsApp Business API Requirements
- Verified Business Account
- Approved message templates for:
  - Payment requests
  - Payment reminders (D+3, D+7, D+10)
  - Formal notices
  - Payment confirmations

### 4.2 LLM-Driven Vision OCR

| Component | Technology | Purpose |
|-----------|------------|---------|
| OCR Engine | GPT-4 Vision | Extract text from CFE bills, receipts |
| Entity Extraction | GPT-4 | Parse dates, amounts, meter numbers |
| Fallback | Google Cloud Vision | Secondary OCR if GPT-4V fails |

#### OCR Accuracy Targets
| Field | Target Accuracy | Verification |
|-------|-----------------|--------------|
| Total Amount | 99.5% | Human-in-the-loop confirmation |
| Billing Period | 98% | Landlord confirmation |
| Meter Number | 97% | Cross-reference with property DB |

### 4.3 Human-in-the-Loop (HITL) Verification

**Critical Rule:** No money-related action is taken without explicit landlord confirmation.

| Action | HITL Checkpoint |
|--------|-----------------|
| Send payment request | Landlord confirms extracted amount and period |
| Mark payment received | Landlord confirms via chat command or screenshot review |
| Escalate to formal notice | Landlord approves escalation |

### 4.4 Data Storage & Security

| Requirement | Implementation |
|-------------|----------------|
| Tenant PII | Encrypted at rest (AES-256) |
| Payment data | Tokenized; no full card numbers stored |
| Message logs | Retained 7 years (legal requirement) |
| PDF receipts | Immutable storage with hash verification |

---

## 5. User Stories

### 5.1 Utility Splitting

#### US-001: Split a CFE Bill
> **As a landlord**, I want to take a photo of a $5,000 MXN CFE bill and have RentasClaras send individual WhatsApp payment links to 9 tenants based on their specific stay dates, **so that** I don't spend 4 hours doing manual math.

**Acceptance Criteria:**
- [ ] Photo is processed within 60 seconds
- [ ] Landlord receives confirmation message with extracted total, period, and meter
- [ ] Landlord confirms or corrects extraction
- [ ] System calculates per-tenant amounts using pro-rata formula
- [ ] Each tenant receives personalized message with their amount and payment link
- [ ] Calculation log is stored for audit

#### US-002: Handle Partial Month Tenant
> **As a landlord**, when a tenant moved in on the 20th of a 30-day billing period, I want them charged only for 10 days of electricity, **so that** charges are fair and defensible.

**Acceptance Criteria:**
- [ ] System reads tenant move-in date from database
- [ ] Pro-rata calculation applies: (Total / 30 days) × 10 days / tenants_on_meter
- [ ] Tenant message shows: "Tu parte proporcional (10 días de 30): $XXX.XX"

---

### 5.2 Payment Collection

#### US-003: Automated Payment Reminders
> **As a landlord**, I want the system to automatically send polite reminders at Day 3, 7, and 10 after a payment request, **so that** I don't have to manually chase tenants.

**Acceptance Criteria:**
- [ ] D+3: Friendly reminder sent if no payment detected
- [ ] D+7: Firmer reminder with explicit deadline
- [ ] D+10: Formal notice with PDF attachment
- [ ] All messages logged with timestamps

#### US-004: 2025-Compliant PDF Receipt
> **As a landlord**, every payment request must generate a PDF receipt with a unique folio, timestamp, and breakdown, **so that** I have legal proof of payment requests for potential eviction proceedings.

**Acceptance Criteria:**
- [ ] PDF generated on every payment request
- [ ] Contains: folio, date, landlord name, tenant name, amount, concept, deadline
- [ ] PDF stored in immutable storage
- [ ] Accessible via landlord command: "Ver recibo [folio]"

---

### 5.3 ATM Ledger

#### US-005: Capture Withdrawal Code
> **As a landlord**, when a tenant sends me a cardless withdrawal code via WhatsApp, I want RentasClaras to automatically extract and log the code, amount, and expiry, **so that** I don't lose track of pending withdrawals.

**Acceptance Criteria:**
- [ ] System detects withdrawal code pattern in tenant message
- [ ] Extracts: code (6 digits), amount, expiry datetime
- [ ] Sends confirmation to tenant
- [ ] Sends notification to landlord with code details
- [ ] Adds to ATM Ledger with "pending" status

#### US-006: Expiry Alert
> **As a landlord**, I want to receive an alert 2 hours before a withdrawal code expires, **so that** I can redeem it in time.

**Acceptance Criteria:**
- [ ] Alert sent to landlord 2 hours before expiry
- [ ] Alert includes: tenant name, code, amount, time remaining
- [ ] If unredeemed by expiry: status changes to "expired", landlord notified

---

### 5.4 Tenant Experience

#### US-007: Clear Payment Breakdown
> **As a tenant**, when I receive a payment request, I want to see a clear breakdown showing the total bill, the billing period, my days of occupancy, and how my amount was calculated, **so that** I trust the landlord isn't overcharging me.

**Acceptance Criteria:**
- [ ] Message includes: total bill, period, days billed, calculation formula, final amount
- [ ] Payment link is one-tap actionable
- [ ] Option to request full PDF breakdown

#### US-008: Instant Payment Confirmation
> **As a tenant**, after I send proof of payment, I want immediate confirmation that my payment was received, **so that** I have peace of mind.

**Acceptance Criteria:**
- [ ] System detects payment proof (screenshot or SPEI reference)
- [ ] Pending: Landlord confirmation triggers confirmation message
- [ ] Tenant receives: "✓ Pago recibido. Gracias."
- [ ] Updated PDF receipt with "PAGADO" status available on request

---

## 6. Core Logic & Formulas

### 6.1 Pro-Rata Utility Calculation

#### Base Formula

```
Tenant Amount = (Bill Total ÷ Days in Period) × Days Stayed ÷ Tenants on Meter
```

#### Detailed Breakdown

```python
def calculate_tenant_share(
    bill_total: float,
    period_start: date,
    period_end: date,
    tenant_move_in: date,
    tenant_move_out: date | None,
    tenants_on_meter: int
) -> float:
    """
    Calculate a tenant's share of a utility bill.

    Args:
        bill_total: Total CFE bill amount in MXN
        period_start: First day of billing period
        period_end: Last day of billing period
        tenant_move_in: Tenant's move-in date
        tenant_move_out: Tenant's move-out date (None if still residing)
        tenants_on_meter: Number of tenants sharing this meter

    Returns:
        Tenant's share in MXN, rounded to 2 decimal places
    """
    # Calculate billing period days
    period_days = (period_end - period_start).days + 1

    # Calculate tenant's occupancy within period
    effective_start = max(period_start, tenant_move_in)
    effective_end = min(period_end, tenant_move_out) if tenant_move_out else period_end

    # Handle tenant not in this period
    if effective_start > effective_end:
        return 0.00

    days_stayed = (effective_end - effective_start).days + 1

    # Daily rate
    daily_rate = bill_total / period_days

    # Tenant's share
    tenant_share = (daily_rate * days_stayed) / tenants_on_meter

    return round(tenant_share, 2)
```

#### Example Calculation

**Scenario:** Ensenada property, November CFE bill

| Parameter | Value |
|-----------|-------|
| Bill Total | $5,000.00 MXN |
| Billing Period | Nov 15 - Dec 14 (30 days) |
| Meter | Covers Units 1, 2, 3 |
| Tenant A (Unit 1) | Full period (30 days) |
| Tenant B (Unit 2) | Moved in Nov 25 (20 days) |
| Tenant C (Unit 3) | Full period (30 days) |

**Calculation:**

```
Daily Rate = $5,000 / 30 = $166.67/day

Tenant A: ($166.67 × 30) / 3 = $1,666.70
Tenant B: ($166.67 × 20) / 3 = $1,111.13
Tenant C: ($166.67 × 30) / 3 = $1,666.70

Total: $4,444.53 (remaining $555.47 is Tenant B's unoccupied portion,
       absorbed by landlord or carried forward)
```

**Note:** For fairness, the "empty days" cost can be:
1. Absorbed by landlord (current approach)
2. Split among all tenants
3. Charged to outgoing tenant if applicable

### 6.2 Property-Meter Mapping

```json
{
  "properties": {
    "ensenada": {
      "name": "Ensenada",
      "units": 9,
      "meters": [
        {
          "meter_id": "ENS-M1",
          "cfe_number": "123456789",
          "units": ["ENS-1", "ENS-2", "ENS-3"]
        },
        {
          "meter_id": "ENS-M2",
          "cfe_number": "234567890",
          "units": ["ENS-4", "ENS-5"]
        },
        {
          "meter_id": "ENS-M3",
          "cfe_number": "345678901",
          "units": ["ENS-6", "ENS-7", "ENS-8", "ENS-9"]
        }
      ]
    },
    "matehuala": { ... },
    "musquiz": { ... },
    "huichapan": { ... }
  }
}
```

---

## 7. Agent Personality & Tone

### 7.1 Core Personality

**RentasClaras** is:

| Trait | Description | NOT This |
|-------|-------------|----------|
| **Profesional** | Business-like, clear, efficient | Robotic, cold |
| **Regio** | Northern Mexican directness, trustworthy | Chilango slang, overly casual |
| **Respetuoso** | Polite, uses "usted" with tenants | Confrontational, threatening |
| **Claro** | Unambiguous, shows the math | Vague, bureaucratic |

### 7.2 Language Guidelines

| Context | Style |
|---------|-------|
| Landlord communication | Can be informal ("tú"), direct, concise |
| Tenant communication | Formal ("usted"), polite, complete information |
| Payment requests | Clear amount, clear deadline, clear payment method |
| Reminders | Escalating formality, never threatening |

### 7.3 Forbidden Phrases

| ❌ Never Say | ✅ Say Instead |
|-------------|---------------|
| "Págame o te corto la luz" | "Le recordamos que el pago sigue pendiente" |
| "Ya me debes" | "Su saldo actual es de..." |
| "Último aviso" (unless D+10) | "Este es un recordatorio amable" |
| Any threat of lockout | Reference to contract terms only |

---

## 8. Success Metrics

### 8.1 MVP Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| OCR Accuracy (amounts) | ≥99% | Landlord corrections / total extractions |
| Payment collection rate | ≥90% within 10 days | Payments received / requests sent |
| Time saved per billing cycle | ≥3 hours | User survey |
| PDF receipt generation | 100% | Requests sent with PDFs / total requests |
| Withdrawal code capture rate | ≥95% | Codes parsed / codes sent by tenants |

### 8.2 User Satisfaction

| Metric | Target | Measurement |
|--------|--------|-------------|
| Landlord NPS | ≥50 | Monthly survey |
| Tenant complaint rate | ≤5% | Complaints / messages sent |
| System trust (landlord) | "Would you trust RentasClaras with a $10k bill?" | Yes/No survey |

---

## 9. Appendix: Sample Agent Messages

### 9.1 To Landlord (OCR Confirmation)

```
📋 Recibo de CFE procesado

Propiedad: Ensenada
Medidor: ENS-M1 (Unidades 1, 2, 3)

💡 Total: $5,000.00 MXN
📅 Periodo: Nov 15 - Dic 14, 2024
⚡ kWh: 1,247

¿Es correcto?
[✓ Sí, enviar] [✏️ Corregir]
```

### 9.2 To Tenant (Initial Payment Request)

```
Buenos días, estimado/a inquilino/a de Ensenada Unidad 2.

Le compartimos el desglose de su parte proporcional del recibo de luz (CFE) correspondiente al periodo Nov 15 - Dic 14, 2024.

📊 Desglose:
• Total del recibo: $5,000.00
• Días del periodo: 30
• Sus días de ocupación: 20 (desde Nov 25)
• Inquilinos en su medidor: 3

💰 Su parte proporcional: $1,111.13 MXN

📅 Fecha límite de pago: Dic 20, 2024

Puede realizar su pago por:
• SPEI: [Número CLABE]
• Retiro sin tarjeta: Envíe el código aquí

Cualquier duda, con gusto le atendemos.

Folio: RC-2024-1227-00047
```

### 9.3 To Tenant (Day 7 Reminder)

```
Buenas tardes.

Notamos que el pago correspondiente a luz (Folio RC-2024-1227-00047) por $1,111.13 MXN sigue pendiente.

Le recordamos que la fecha límite de pago fue el Dic 20.

Por favor, realice su pago a la brevedad para evitar que este adeudo se acumule con el siguiente periodo.

Si ya realizó el pago, envíenos su comprobante y con gusto actualizamos su estado.

Gracias por su atención.
```

### 9.4 To Tenant (Day 10 Formal Notice)

```
Estimado/a inquilino/a:

De acuerdo con las cláusulas de su contrato de arrendamiento, le informamos formalmente que cuenta con un adeudo pendiente:

📄 Concepto: Prorrateo de luz (CFE)
💰 Monto: $1,111.13 MXN
📅 Fecha de vencimiento original: Dic 20, 2024
⚠️ Días de retraso: 10

Adjuntamos el Aviso Formal de Adeudo (PDF) para su referencia.

Este documento forma parte del expediente de su arrendamiento.

Le solicitamos atentamente regularizar su situación en las próximas 48 horas.

Atentamente,
Administración Ensenada
```

### 9.5 Withdrawal Code Confirmation (To Tenant)

```
✓ Recibido

Registramos su retiro sin tarjeta:
• Código: 847293
• Monto: $3,200.00
• Vence: Hoy, 8:00 PM

Le confirmaremos una vez que el retiro sea realizado.

Gracias.
```

### 9.6 Withdrawal Code Alert (To Landlord)

```
🏧 Nuevo código de retiro

Inquilino: María González (Ensenada 4B)
Código: 847293
Monto: $3,200.00
Vence: Hoy 8:00 PM (en 5 horas)

Responde "Retiré 847293" cuando lo cobres.
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2024-12-27 | Product & AI Architecture | Initial PRD |

---

*RentasClaras: Tu socio digital para rentas claras.* 🏠

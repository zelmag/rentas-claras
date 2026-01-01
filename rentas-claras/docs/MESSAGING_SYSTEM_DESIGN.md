# RentasClaras Messaging System Design

> **Status:** Design Document
> **Created:** 2025-12-30
> **Author:** AI Assistant (Audit & Fix Session)

---

## Overview

This document defines how the WhatsApp messaging and webhook system should work for rent reminders.

---

## 1. Message Flow Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  Recordatorios  │────▶│   /api/reminders │────▶│   WhatsApp Cloud    │
│     UI Page     │     │      /send       │     │        API          │
└─────────────────┘     └──────────────────┘     └─────────────────────┘
                                │                          │
                                │                          │
                                ▼                          ▼
                        ┌──────────────────┐     ┌─────────────────────┐
                        │   message_logs   │◀────│   /webhook/whatsapp │
                        │     (SQLite)     │     │   (status updates)  │
                        └──────────────────┘     └─────────────────────┘
```

---

## 2. Message Types & Templates

### 2.1 Template Configuration

| Template Name       | Message Type (DB)      | When to Use                    | Parameters                          |
|---------------------|------------------------|--------------------------------|-------------------------------------|
| `recordatorio_renta`| `morning_reminder`     | Day 1, morning (before 5 PM)   | `[tenant_name, amount]`             |
| `recordatorio_tarde`| `afternoon_reminder`   | Day 1, after 5 PM              | `[tenant_name, amount]`             |
| `aviso_recargo`     | `late_fee_notice`      | Day 2+, with late fee          | `[tenant_name, base_rent, total]`   |

### 2.2 Template Selection Logic (Auto)

```python
def get_recommended_template(day_of_month: int, hour: int) -> str:
    if day_of_month >= 2:
        return "aviso_recargo"      # Late fee applies
    elif hour >= 17:
        return "recordatorio_tarde" # Afternoon reminder
    else:
        return "recordatorio_renta" # Morning reminder
```

---

## 3. Late Fee Calculation

### 3.1 Business Rules

- **Grace Period:** Day 1 of each month (no late fee)
- **Late Fee Rate:** 10% starting Day 2
- **Calculation:** `total = base_rent * 1.10`

### 3.2 Implementation

```python
def calculate_late_fee(base_rent: float, day_of_month: int) -> tuple[float, float]:
    """
    Calculate late fee based on day of month.

    Returns:
        (base_rent, total_with_fees) tuple
    """
    LATE_FEE_RATE = 0.10  # 10%

    if day_of_month >= 2:
        late_fee = base_rent * LATE_FEE_RATE
        total = base_rent + late_fee
        return (base_rent, total)
    else:
        return (base_rent, base_rent)  # No late fee on Day 1
```

---

## 4. Message Logging

### 4.1 `message_logs` Table Schema

```sql
CREATE TABLE message_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    message_type TEXT NOT NULL,      -- 'morning_reminder', 'afternoon_reminder', 'late_fee_notice'
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    sent_at TEXT NOT NULL,           -- ISO 8601 timestamp
    message_id TEXT,                 -- WhatsApp message ID (wamid.xxx)
    status TEXT DEFAULT 'sent',      -- 'sent', 'delivered', 'read', 'failed'
    delivered_at TEXT,
    read_at TEXT,
    error_message TEXT
);
```

### 4.2 Status Flow

```
sent ──▶ delivered ──▶ read
  │
  └──▶ failed
```

### 4.3 Logging Rules

1. **Always INSERT new records** - keep full message history
2. **Log correct message_type** - match the template used, not always "morning_reminder"
3. **Store WhatsApp message_id** - needed for webhook status matching

---

## 5. Webhook Processing

### 5.1 Incoming Webhook Types

1. **Status Updates** (`statuses` array)
   - `sent` - Message accepted by WhatsApp
   - `delivered` - Message delivered to device
   - `read` - Message read by recipient
   - `failed` - Message failed (with error details)

2. **Incoming Messages** (`messages` array)
   - Text replies from tenants
   - Media (images, audio, etc.)

### 5.2 Status Update Processing

```python
def handle_status_update(status: dict):
    message_id = status["id"]      # wamid.xxx format
    status_value = status["status"] # sent/delivered/read/failed

    # Update message_logs table
    if status_value == "delivered":
        UPDATE message_logs SET status='delivered', delivered_at=?
        WHERE message_id=? AND status='sent'
    elif status_value == "read":
        UPDATE message_logs SET status='read', read_at=?
        WHERE message_id=? AND status IN ('sent', 'delivered')
    elif status_value == "failed":
        UPDATE message_logs SET status='failed', error_message=?
        WHERE message_id=?
```

### 5.3 Signature Verification

All webhook requests should be verified using HMAC-SHA256:
```python
expected = hmac.new(app_secret.encode(), payload, hashlib.sha256).hexdigest()
return hmac.compare_digest(signature, expected)
```

---

## 6. API Endpoints (Consolidated)

### 6.1 Primary Endpoint: `/api/reminders/send` (POST)

**Request:**
```json
{
  "tenant_ids": ["MAT-A", "MUZ-B"],
  "template": "recordatorio_renta"
}
```

**Response:**
```json
{
  "success": true,
  "summary": {"sent": 2, "failed": 0, "skipped": 0},
  "details": {
    "sent": [{"id": "MAT-A", "name": "...", "message_id": "wamid.xxx"}],
    "failed": [],
    "skipped": []
  }
}
```

### 6.2 Deprecated: `/api/whatsapp/send-all`

> ⚠️ **DEPRECATED** - Use `/api/reminders/send` instead.
>
> This endpoint does not log messages and uses outdated function signatures.

---

## 7. Error Handling

### 7.1 API Errors

| Error Code | Meaning | Action |
|------------|---------|--------|
| 131047 | Template not approved | Check Meta Business portal |
| 131049 | Phone number invalid | Verify phone format |
| 131030 | Rate limit exceeded | Wait and retry |
| 100 | Parameter missing | Check template params |

### 7.2 Retry Logic

- Failed messages can be retried via `/api/reminders/retry`
- Retries bypass the idempotency check
- Original failed log entry is updated on success

---

## 8. Security Considerations

### 8.1 XSS Prevention

Always escape user input in JavaScript:
```html
<!-- BAD -->
onclick="sendTo('{{ tenant.name }}')"

<!-- GOOD -->
onclick="sendTo({{ tenant.name|tojson }})"
```

### 8.2 Environment Variables

Required in `.env`:
```
WHATSAPP_ACCESS_TOKEN=xxx
WHATSAPP_PHONE_NUMBER_ID=xxx
WHATSAPP_WEBHOOK_VERIFY_TOKEN=xxx
WHATSAPP_APP_SECRET=xxx  # For signature verification
```

---

## 9. Testing

### 9.1 Test Phone Configuration

```env
WHATSAPP_TEST_PHONE=+52xxxxxxxxxx  # Your test phone
```

### 9.2 Test Endpoint

`POST /api/reminders/test` - Sends test message using configured test phone from `.env`

---

## 10. Bug Fixes Applied (2025-12-30)

| Bug # | Issue | Fix |
|-------|-------|-----|
| 1 | Late fee not calculated | Calculate 10% fee for Day 2+ |
| 2 | Missing DOM elements | Add badge elements to HTML |
| 3 | Race condition in modal | Save values before closing |
| 4 | Webhook status mismatch | Improve matching logic |
| 5 | Wrong message_type logged | Log correct type per template |
| 6 | Duplicate endpoints | Deprecate `/api/whatsapp/send-all` |
| 7 | Unused force_resend | Remove parameter |
| 8 | XSS vulnerability | Use `|tojson` filter |
| 9 | Hardcoded test phone | Use env variable |
| 10 | Missing table validation | Add schema check |

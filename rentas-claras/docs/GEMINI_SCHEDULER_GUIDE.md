# Gemini's Guide: Implementing Scheduled WhatsApp Messages
## "Single-Machine Persistent" Strategy

*Source: Gemini responses, December 2024*

---

## Key Insights

### 🎯 Strategy: Single-Machine "Always On"
- **Platform:** Fly.io (Machine: `shared-cpu-1x`, RAM: `256MB`)
- **Database:** SQLite on **Fly Volume** (survives restarts/deploys)
- **Scheduler:** APScheduler inside Flask process
- No need for Redis, Celery, or external services
- Perfect for your scale (32 tenants)

### 🇲🇽 Mexico Timezone Simplification
> **Big win:** Mexico (CDMX/Monterrey) **abolished Daylight Saving Time in 2022**.  
> You're now on **permanent UTC-6**, so no DST headaches!

### 💰 Updated Cost Estimate (Dec 2024)
| Item | Cost |
|------|------|
| WhatsApp messages (Utility) | ~$0.01 USD per message |
| 160 messages/month | **~$1.60 USD/month** |
| Fly.io (shared-cpu-1x) | **FREE** (within free tier) |

> **Pro Tip:** If a tenant replies (e.g., "Ya pagué!"), any follow-up you send within 24 hours is **FREE**!

---

## Implementation Steps

### Step 0: Create Fly Volume (Persistent Storage)

⚠️ **CRITICAL:** By default, Fly.io files disappear on deploy. You need a "hard drive" for your database.

```bash
# Run this ONCE in your terminal
fly volumes create clara_data --size 1 --region dfw
```

---

### Step 1: Update `fly.toml` - Volume + Always On

```toml
[mounts]
  source = "clara_data"
  destination = "/data"  # Your DB will live here

[http_service]
  internal_port = 5000
  force_https = true
  auto_stop_machines = false  # ← CRITICAL: Set to false
  auto_start_machines = true
  min_machines_running = 1    # ← CRITICAL: Keep 1 machine alive 24/7
```

---

### Step 2: Wire APScheduler in `app.py`

```python
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import timezone
import logging

# 1. Setup Logging (Check these in 'fly logs')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
MX_TZ = timezone('America/Mexico_City')

def run_automation_logic(task_name):
    """The wrapper that runs inside the 'app context' to access the DB"""
    with app.app_context():
        # Import your existing logic here to avoid circular imports
        from src.tasks import process_rent_reminders
        logger.info(f"Starting {task_name} at 9:00 AM CST")
        process_rent_reminders()

# 2. Initialize Scheduler
scheduler = BackgroundScheduler(timezone=MX_TZ)

# Job 1: Rent Reminders (1st of the month)
scheduler.add_job(
    func=run_automation_logic,
    trigger='cron',
    day=1, hour=9, minute=0,
    args=['Monthly Reminder'],
    id='rent_reminder'
)

# Job 2: Late Escalations (Days 2, 3, 5, 7, 8)
scheduler.add_job(
    func=run_automation_logic,
    trigger='cron',
    day='2,3,5,7,8', hour=9, minute=0,
    args=['Late Escalation'],
    id='late_escalation'
)

scheduler.start()

@app.route('/')
def home():
    return "Rentas-Claras is running and scheduled."
```

---

### Step 3: Create `src/tasks.py` - The Actual Logic

```python
import sqlite3
from src.whatsapp_client import WhatsAppClient

def process_rent_reminders():
    # 1. Connect to DB (Use absolute path to your Fly Volume)
    conn = sqlite3.connect('/data/rentas.db') 
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 2. Get only unpaid tenants
    tenants = cursor.execute("SELECT * FROM tenants WHERE paid = 0").fetchall()

    client = WhatsAppClient()
    
    for tenant in tenants:
        try:
            # Your existing logic to calculate late fees and send
            client.send_rent_reminder(
                phone=tenant['phone'], 
                amount=tenant['rent_amount'],
                name=tenant['name']
            )
            # Log success in DB so you don't double-send if the script restarts
            cursor.execute("INSERT INTO logs (tenant_id, status) VALUES (?, 'sent')", (tenant['id'],))
        except Exception as e:
            print(f"Failed for {tenant['name']}: {e}")
    
    conn.commit()
    conn.close()
```

---

### Step 4: Add Testing Route (Manual Trigger)

```python
@app.route('/admin/force-test-messages/<secret_key>')
def force_test(secret_key):
    if secret_key != "your-very-secret-password":
        return "Unauthorized", 403
    
    # Manually trigger the task
    run_automation_logic("MANUAL TEST")
    return "Test messages initiated! Check fly logs."
```

**Usage:** Visit `https://your-app.fly.dev/admin/force-test-messages/your-very-secret-password`

---

## Reliability Checklist

| Item | Action |
|------|--------|
| **Persistent DB** | Use Fly Volume (`/data/rentas.db`), not local filesystem |
| **Graceful Restarts** | Jobs are in memory; `add_job` in `app.py` re-registers on every startup |
| **Logging** | Use `fly logs` to monitor; save `message_id` from Meta API |
| **Timezone** | `America/Mexico_City` = permanent UTC-6 (no DST since 2022) |

---

## Dependencies to Add

```bash
pip install apscheduler pytz
```

Or add to `requirements.txt`:
```
apscheduler>=3.10.0
pytz>=2024.1
```

---

## Next Steps

1. [ ] Update `fly.toml` with always-on settings
2. [ ] Add APScheduler to `requirements.txt`
3. [ ] Wire scheduler in `app.py`
4. [ ] Create `src/tasks.py` with rent reminder logic
5. [ ] Set up Fly Volume for SQLite persistence
6. [ ] Deploy and test with admin route
7. [ ] Monitor with `fly logs`

---

*Guide saved from Gemini response, December 2024*

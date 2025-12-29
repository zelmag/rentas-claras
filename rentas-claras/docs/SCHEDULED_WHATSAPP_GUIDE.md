# Scheduled WhatsApp Messages for Rentas-Claras
## A Beginner's Guide 🚀

---

## 🎯 Benefits of Automating WhatsApp Reminders

### Time Savings
- ✅ **Saves 16+ hours/month** - No more manually messaging 32 tenants
- ✅ **Zero daily effort** - Messages go out automatically at 9 AM
- ✅ **No forgotten reminders** - System never forgets, never gets sick, never takes vacation

### Emotional Benefits
- ✅ **Removes awkwardness of asking for money** - The system does the "uncomfortable" part
- ✅ **Professional distance** - Tenants see it as "the system" not personal pressure
- ✅ **Consistent tone** - Messages are always professional, never emotional

### Financial Benefits
- ✅ **Better collection rate** - Automated escalation (Day 2, 5, 7, 8) means fewer late payments
- ✅ **Automatic late fee calculation** - System adds $500 + $100/day automatically
- ✅ **Recovers ~$2,000-2,500/month** in late fees that used to slip through

### Why Meta's WhatsApp Cloud API Specifically?
- ✅ **Service conversations are FREE (unlimited)** - As of Nov 2024, when tenants message YOU first, it's free
- ✅ **Official & reliable** - It's Meta's own API, not a sketchy third party
- ✅ **Templates ensure delivery** - Pre-approved templates bypass spam filters
- ✅ **Already integrated** - You have the code ready in `whatsapp_client.py`

> ⚠️ **IMPORTANT PRICING UPDATE (2024-2025):**
> - **Service conversations** (tenant messages you first) = **FREE, unlimited**
> - **Marketing/Utility conversations** (you message tenant first) = **PAID per message** (as of April 2025)
> - For rent reminders where YOU initiate, you'll pay per message (~$0.02-0.05 USD per message in Mexico)
> - At 160 messages/month = ~$3-8 USD/month (still very cheap!)

---

## 📋 Step-by-Step Guide (For Beginners)

### Phase 1: Understand What You Have ✅

You already have these pieces built:

| Component | File | Status |
|-----------|------|--------|
| WhatsApp API client | `src/whatsapp_client.py` | ✅ Done |
| Message templates | `src/scheduler.py` | ✅ Done |
| Late fee calculator | `src/late_fees.py` | ✅ Done |
| Scheduler logic | `src/scheduler.py` | ✅ Done |
| Database | `database.py` | ✅ Done |

**What's missing:** Connecting the scheduler to actually RUN automatically.

---

### Phase 2: Set Up WhatsApp Business API (One-time, ~2 hours)

#### Step 1: Create Meta Business Account
```
1. Go to: https://business.facebook.com
2. Click "Create Account"
3. Use your dad's business info (or create one for the rental business)
4. Verify with phone number
```

#### Step 2: Set Up WhatsApp in Meta Developer Portal
```
1. Go to: https://developers.facebook.com
2. Create a new App → Select "Business" type
3. Add "WhatsApp" product to your app
4. Get your:
   - WHATSAPP_ACCESS_TOKEN (temporary, lasts 24 hours initially)
   - WHATSAPP_PHONE_NUMBER_ID
```

#### Step 3: Create Message Templates
In Meta Business Suite → WhatsApp Manager → Message Templates:

**Template 1: `rent_reminder`**
```
Buenos días {{1}}. Espero esté bien. Para recordarle por favor 
del pago de la renta de {{2}}. Total: ${{3}} MXN. Gracias.
```

**Template 2: `rent_reminder_late`**
```
Buenas tardes {{1}}. Le recordamos que el pago de renta de {{2}} 
por ${{3}} MXN sigue pendiente. Por favor regularice su situación. Gracias.
```

⏳ Wait 24-48 hours for template approval.

#### Step 4: Add Credentials to Your App
Create/update `/rentas-claras/.env`:
```bash
WHATSAPP_ACCESS_TOKEN=your_long_token_here
WHATSAPP_PHONE_NUMBER_ID=your_phone_id_here
WHATSAPP_TEST_PHONE=+521234567890  # Your phone for testing
```

#### Step 5: Test It Works
```bash
cd /Users/zelma/Desktop/ZelmaHelps_Agent/rentas-claras
python src/whatsapp_client.py
```

You should see: `✅ Message sent!`

---

### Phase 3: Wire Up the Scheduler (The Key Part)

This is where the magic happens. You need to make the scheduler run automatically.

#### Option A: Simple Cron Job (Easiest for Beginners) ⭐

**What is cron?** A built-in system that runs commands on a schedule.

**Step 1:** Open your terminal and type:
```bash
crontab -e
```

**Step 2:** Add these lines:
```bash
# RentasClaras WhatsApp Reminders
# Timezone: Mexico City (CST)
TZ=America/Mexico_City

# Day 1 - Morning reminder at 9 AM
0 9 1 * * cd /Users/zelma/Desktop/ZelmaHelps_Agent/rentas-claras && python -c "from src.scheduler import ReminderScheduler, ReminderType; ReminderScheduler().trigger(ReminderType.MORNING_DAY_1)"

# Day 2 - Late notice at 9 AM
0 9 2 * * cd /Users/zelma/Desktop/ZelmaHelps_Agent/rentas-claras && python -c "from src.scheduler import ReminderScheduler, ReminderType; ReminderScheduler().trigger(ReminderType.LATE_DAY_2)"

# Day 5 - Mid-week reminder at 9 AM
0 9 5 * * cd /Users/zelma/Desktop/ZelmaHelps_Agent/rentas-claras && python -c "from src.scheduler import ReminderScheduler, ReminderType; ReminderScheduler().trigger(ReminderType.LATE_DAY_5)"

# Day 7 - Final warning at 9 AM
0 9 7 * * cd /Users/zelma/Desktop/ZelmaHelps_Agent/rentas-claras && python -c "from src.scheduler import ReminderScheduler, ReminderType; ReminderScheduler().trigger(ReminderType.LATE_DAY_7)"

# Day 8 - Critical notice at 9 AM
0 9 8 * * cd /Users/zelma/Desktop/ZelmaHelps_Agent/rentas-claras && python -c "from src.scheduler import ReminderScheduler, ReminderType; ReminderScheduler().trigger(ReminderType.CRITICAL_DAY_8)"
```

**Step 3:** Save and exit (`:wq` in vim or Ctrl+X in nano)

**Problem:** This only works if your Mac is ON at 9 AM Mexico time. Not ideal.

---

#### Option B: Deploy to Fly.io with Scheduled Jobs (Better for Production) ⭐⭐

**What is Fly.io?** A cloud platform where your app runs 24/7.

**Step 1:** Install Fly CLI
```bash
brew install flyctl
```

**Step 2:** Login to Fly
```bash
fly auth login
```

**Step 3:** Update `fly.toml` to add scheduled machines:
```toml
# Already in your fly.toml:
app = "rentas-claras"
primary_region = "dfw"  # Dallas (close to Mexico)

[http_service]
  internal_port = 5000
  force_https = true

# ADD THIS for scheduled jobs:
[[machines]]
  [machines.schedule]
    cron = "0 15 1 * *"  # 9 AM Mexico = 15:00 UTC
    command = ["python", "-c", "from src.scheduler import ReminderScheduler, ReminderType; ReminderScheduler().trigger(ReminderType.MORNING_DAY_1)"]
```

**Step 4:** Deploy
```bash
cd /Users/zelma/Desktop/ZelmaHelps_Agent/rentas-claras
fly deploy
```

---

#### Option C: Use APScheduler Inside Flask (Most Elegant) ⭐⭐⭐

This runs the scheduler as part of your Flask app.

**Step 1:** Install APScheduler
```bash
pip install apscheduler
```

**Step 2:** Add to `app.py`:
```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from src.scheduler import ReminderScheduler, ReminderType

# Create scheduler
reminder_scheduler = ReminderScheduler()
aps = BackgroundScheduler(timezone='America/Mexico_City')

# Morning reminder - 1st of month at 9 AM
aps.add_job(
    reminder_scheduler.trigger,
    CronTrigger(day=1, hour=9, minute=0),
    args=[ReminderType.MORNING_DAY_1],
    id='morning_day_1'
)

# Late Day 2 - 9 AM
aps.add_job(
    reminder_scheduler.trigger,
    CronTrigger(day=2, hour=9, minute=0),
    args=[ReminderType.LATE_DAY_2],
    id='late_day_2'
)

# Add more days as needed...

# Start scheduler when app starts
aps.start()
```

**Caveat:** On Fly.io, if your app has multiple instances or sleeps, APScheduler might not fire reliably. For production, Option B is more robust.

---

### Phase 4: Test Without Waiting for the 1st of the Month

#### Manual Trigger (Test Anytime)
```bash
cd /Users/zelma/Desktop/ZelmaHelps_Agent/rentas-claras
python src/scheduler.py --demo
```

This shows you what messages WOULD be sent without actually sending them.

#### Force Send to Yourself
```python
# Quick test script
from src.whatsapp_client import send_rent_reminder

result = send_rent_reminder(
    to_phone="+52YOUR_PHONE",
    tenant_name="Test",
    month="enero",
    amount="4,500"
)
print(result)
```

---

## 🎯 Summary: Your Action Items

| Step | What | Time | Priority |
|------|------|------|----------|
| 1 | Set up Meta Business account | 30 min | 🔴 Do First |
| 2 | Create WhatsApp templates | 15 min | 🔴 Do First |
| 3 | Wait for template approval | 24-48 hrs | ⏳ Wait |
| 4 | Add credentials to `.env` | 5 min | 🟡 After approval |
| 5 | Test with `python src/whatsapp_client.py` | 5 min | 🟡 |
| 6 | Choose scheduling method (A, B, or C) | 1 hr | 🟢 Last |
| 7 | Deploy and let it run | 30 min | 🟢 Last |

---

## ❓ FAQ

**Q: What if a message fails to send?**
A: The current code logs failures. You should add retry logic and maybe a Telegram/email alert to yourself.

**Q: What if a tenant already paid but still gets a reminder?**
A: The scheduler checks `paid` status in the database. Make sure to mark payments promptly!

**Q: Is this legal in Mexico?**
A: Yes, for business communications with customers who have given consent (they signed a rental contract with their phone number).

**Q: What about GDPR/privacy?**
A: Store phone numbers securely (✅ SQLite is local), don't share with third parties, and allow tenants to opt out.

---

## 🚀 Next Steps After This Works

1. **OCR for payment screenshots** - Tenant sends photo → system extracts code → auto-updates Excel
2. **Two-way WhatsApp bot** - Tenants can reply "Ya pagué" and system responds
3. **Dashboard notifications** - See who got messages, who opened them

---

*Created: December 2024 | RentasClaras Engineering*

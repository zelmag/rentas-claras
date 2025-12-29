"""
RentasClaras Scheduler
======================

Automated rent reminder system using APScheduler.

Schedule (Day 1 of each month only):
- 8:00 AM: Morning reminder (recordatorio_renta)
- 5:00 PM: Afternoon reminder (recordatorio_tarde)

Day 2+: Dad takes over manually (calls aval)

Author: RentasClaras Engineering
Date: December 2024
"""

import logging
import os
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone

# =============================================================================
# LOGGING
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("RentasScheduler")

# =============================================================================
# CONFIGURATION
# =============================================================================

# Timezone for Mexico
TIMEZONE = timezone(os.getenv("SCHEDULER_TIMEZONE", "America/Mexico_City"))

# Enable/disable scheduler (useful for testing)
SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"

# Global scheduler instance
_scheduler: Optional[BackgroundScheduler] = None


# =============================================================================
# REMINDER JOBS
# =============================================================================


def run_morning_reminder():
    """
    8:00 AM reminder job - runs on Day 1 only.
    
    Sends 'recordatorio_renta' to all unpaid tenants.
    """
    now = datetime.now(TIMEZONE)
    
    # Only run on Day 1 of the month
    if now.day != 1:
        logger.info(f"Morning reminder skipped - today is day {now.day}, not day 1")
        return
    
    logger.info("=" * 60)
    logger.info("🌅 Running MORNING reminder job (8:00 AM)")
    logger.info("=" * 60)
    
    _send_reminders(
        message_type="morning_reminder",
        template_name="recordatorio_renta",
        is_morning=True
    )


def run_afternoon_reminder():
    """
    5:00 PM reminder job - runs on Day 1 only.
    
    Sends 'recordatorio_tarde' to all unpaid tenants.
    """
    now = datetime.now(TIMEZONE)
    
    # Only run on Day 1 of the month
    if now.day != 1:
        logger.info(f"Afternoon reminder skipped - today is day {now.day}, not day 1")
        return
    
    logger.info("=" * 60)
    logger.info("🌆 Running AFTERNOON reminder job (5:00 PM)")
    logger.info("=" * 60)
    
    _send_reminders(
        message_type="afternoon_reminder",
        template_name="recordatorio_tarde",
        is_morning=False
    )


def run_daily_backup():
    """
    6:00 AM backup job - runs every day.
    
    Creates a backup of the SQLite database.
    """
    logger.info("=" * 60)
    logger.info("💾 Running DAILY BACKUP job (6:00 AM)")
    logger.info("=" * 60)
    
    try:
        from src.backup import create_backup, get_backup_stats
        
        # Create backup
        result = create_backup(verify_first=True)
        
        if result["success"]:
            logger.info(f"✅ Backup created: {result['backup_path']}")
            logger.info(f"   Size: {result['size_mb']} MB")
            
            # Log backup stats
            stats = get_backup_stats()
            logger.info(f"   Total backups: {stats['total_backups']}")
            logger.info(f"   Total size: {stats['total_size_mb']} MB")
        else:
            logger.error(f"❌ Backup failed: {result['message']}")
            
    except ImportError as e:
        logger.error(f"❌ Backup module not found: {e}")
    except Exception as e:
        logger.error(f"❌ Backup error: {e}")


def _send_reminders(message_type: str, template_name: str, is_morning: bool):
    """
    Core logic to send reminders to all unpaid tenants.
    
    Args:
        message_type: Type for message_logs ('morning_reminder' or 'afternoon_reminder')
        template_name: WhatsApp template name
        is_morning: True for 8 AM, False for 5 PM
    """
    # Import here to avoid circular imports
    from database import (
        get_unpaid_tenants_for_reminder,
        log_message_sent,
    )
    from src.whatsapp_client import WhatsAppClient
    
    now = datetime.now(TIMEZONE)
    year = now.year
    month = now.month
    
    # Get unpaid tenants who haven't received this message type today
    tenants = get_unpaid_tenants_for_reminder(year, month, message_type)
    
    if not tenants:
        logger.info("✅ No unpaid tenants to remind (all paid or already messaged)")
        return
    
    logger.info(f"📋 Found {len(tenants)} unpaid tenants to remind")
    
    # Initialize WhatsApp client
    client = WhatsAppClient()
    
    # Check credentials
    config = client.check_credentials()
    if not config["configured"]:
        logger.error("❌ WhatsApp credentials not configured. Skipping reminders.")
        return
    
    # Send reminders
    success_count = 0
    fail_count = 0
    
    for tenant in tenants:
        tenant_id = tenant["id"]
        tenant_name = tenant["name"]
        phone = tenant["phone"]
        rent = float(tenant["rent"])
        
        logger.info(f"📤 Sending to {tenant_name} ({phone})...")
        
        # Send appropriate reminder
        if is_morning:
            response = client.send_rent_reminder(
                to_phone=phone,
                tenant_name=tenant_name,
                amount=rent
            )
        else:
            response = client.send_afternoon_reminder(
                to_phone=phone,
                tenant_name=tenant_name,
                amount=rent
            )
        
        # Log result
        if response.success:
            success_count += 1
            log_message_sent(
                tenant_id=tenant_id,
                message_type=message_type,
                message_id=response.message_id,
                status="sent"
            )
            logger.info(f"   ✅ Sent! Message ID: {response.message_id}")
        else:
            fail_count += 1
            log_message_sent(
                tenant_id=tenant_id,
                message_type=message_type,
                status="failed",
                error_message=response.error
            )
            logger.error(f"   ❌ Failed: {response.error}")
    
    # Summary
    logger.info("=" * 60)
    logger.info(f"📊 Summary: {success_count} sent, {fail_count} failed")
    logger.info("=" * 60)


# =============================================================================
# SCHEDULER MANAGEMENT
# =============================================================================


def start_scheduler():
    """
    Start the background scheduler with rent reminder jobs.
    
    Call this when the Flask app starts.
    """
    global _scheduler
    
    if not SCHEDULER_ENABLED:
        logger.info("⏸️  Scheduler is DISABLED (SCHEDULER_ENABLED=false)")
        return
    
    if _scheduler is not None:
        logger.warning("Scheduler already running")
        return
    
    logger.info("🚀 Starting RentasClaras Scheduler...")
    
    _scheduler = BackgroundScheduler(timezone=TIMEZONE)
    
    # Job 1: Morning reminder at 8:00 AM Mexico time
    _scheduler.add_job(
        run_morning_reminder,
        trigger=CronTrigger(hour=8, minute=0, timezone=TIMEZONE),
        id="morning_reminder",
        name="8:00 AM Rent Reminder",
        replace_existing=True,
    )
    
    # Job 2: Afternoon reminder at 5:00 PM Mexico time
    _scheduler.add_job(
        run_afternoon_reminder,
        trigger=CronTrigger(hour=17, minute=0, timezone=TIMEZONE),
        id="afternoon_reminder",
        name="5:00 PM Rent Reminder",
        replace_existing=True,
    )
    
    # Job 3: Daily database backup at 6:00 AM Mexico time
    _scheduler.add_job(
        run_daily_backup,
        trigger=CronTrigger(hour=6, minute=0, timezone=TIMEZONE),
        id="daily_backup",
        name="6:00 AM Daily Backup",
        replace_existing=True,
    )
    
    _scheduler.start()
    
    logger.info("✅ Scheduler started successfully!")
    logger.info("   📅 Morning reminder: 8:00 AM (Day 1 only)")
    logger.info("   📅 Afternoon reminder: 5:00 PM (Day 1 only)")
    logger.info("   💾 Daily backup: 6:00 AM")
    logger.info(f"   🌎 Timezone: {TIMEZONE}")
    
    # List all jobs
    jobs = _scheduler.get_jobs()
    for job in jobs:
        logger.info(f"   📋 Job: {job.name} → Next run: {job.next_run_time}")


def stop_scheduler():
    """
    Stop the scheduler gracefully.
    
    Call this when the Flask app shuts down.
    """
    global _scheduler
    
    if _scheduler is None:
        return
    
    logger.info("🛑 Stopping scheduler...")
    _scheduler.shutdown(wait=False)
    _scheduler = None
    logger.info("✅ Scheduler stopped")


def get_scheduler_status() -> dict:
    """
    Get current scheduler status.
    
    Returns:
        Dict with scheduler info and job statuses
    """
    if _scheduler is None:
        return {
            "running": False,
            "enabled": SCHEDULER_ENABLED,
            "timezone": str(TIMEZONE),
            "jobs": []
        }
    
    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
        })
    
    return {
        "running": _scheduler.running,
        "enabled": SCHEDULER_ENABLED,
        "timezone": str(TIMEZONE),
        "jobs": jobs
    }


# =============================================================================
# MANUAL TRIGGERS (for testing)
# =============================================================================


def trigger_morning_reminder_now():
    """
    Manually trigger morning reminder (for testing).
    Ignores the day-of-month check.
    """
    logger.info("⚡ MANUAL TRIGGER: Morning reminder")
    
    from database import (
        get_unpaid_tenants_for_reminder,
        log_message_sent,
    )
    from src.whatsapp_client import WhatsAppClient
    
    now = datetime.now(TIMEZONE)
    
    _send_reminders(
        message_type="morning_reminder",
        template_name="recordatorio_renta",
        is_morning=True
    )


def trigger_afternoon_reminder_now():
    """
    Manually trigger afternoon reminder (for testing).
    Ignores the day-of-month check.
    """
    logger.info("⚡ MANUAL TRIGGER: Afternoon reminder")
    
    _send_reminders(
        message_type="afternoon_reminder",
        template_name="recordatorio_tarde",
        is_morning=False
    )


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys
    
    print("🗓️  RentasClaras Scheduler")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "test-morning":
            print("Testing morning reminder...")
            trigger_morning_reminder_now()
        elif command == "test-afternoon":
            print("Testing afternoon reminder...")
            trigger_afternoon_reminder_now()
        elif command == "status":
            status = get_scheduler_status()
            print(f"Running: {status['running']}")
            print(f"Enabled: {status['enabled']}")
            print(f"Timezone: {status['timezone']}")
            print(f"Jobs: {len(status['jobs'])}")
            for job in status['jobs']:
                print(f"  - {job['name']}: Next run {job['next_run']}")
        else:
            print(f"Unknown command: {command}")
            print("Usage: python scheduler.py [test-morning|test-afternoon|status]")
    else:
        print("Starting scheduler in foreground (Ctrl+C to stop)...")
        start_scheduler()
        
        try:
            # Keep running
            import time
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            stop_scheduler()
            print("\nScheduler stopped.")

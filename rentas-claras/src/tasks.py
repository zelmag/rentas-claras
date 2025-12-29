"""
RentasClaras: Automated Rent Reminder Tasks
============================================

This module contains the automation logic for sending scheduled WhatsApp
reminders to tenants. It's designed to be called by APScheduler.

Key Features:
- Idempotent: Won't double-send messages (checks message_logs table)
- Day-aware: Sends appropriate message based on day of month
- Error handling: Logs failures for retry/review

Author: RentasClaras Engineering
Date: December 2024
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pytz import timezone

# Local imports
from database import (
    get_unpaid_tenants_for_reminder,
    log_message_sent,
    was_message_sent_today,
)
from src.late_fees import calculate_rentas_claras_balance, PaymentStatus
from src.whatsapp_client import send_template_message, send_rent_reminder, send_late_reminder

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mexico City timezone (permanent UTC-6 since 2022)
MX_TZ = timezone("America/Mexico_City")

# Message type constants
MSG_TYPE_DAY_1 = "rent_reminder_day_1"
MSG_TYPE_DAY_2 = "late_day_2"
MSG_TYPE_DAY_3 = "late_day_3"
MSG_TYPE_DAY_5 = "late_day_5"
MSG_TYPE_DAY_7 = "late_day_7"
MSG_TYPE_DAY_8 = "critical_day_8"


def get_message_type_for_day(day: int) -> Optional[str]:
    """
    Get the message type based on current day of month.
    
    Args:
        day: Day of month (1-31)
    
    Returns:
        Message type string or None if no message should be sent
    """
    message_types = {
        1: MSG_TYPE_DAY_1,
        2: MSG_TYPE_DAY_2,
        3: MSG_TYPE_DAY_3,
        5: MSG_TYPE_DAY_5,
        7: MSG_TYPE_DAY_7,
        8: MSG_TYPE_DAY_8,
    }
    return message_types.get(day)


def calculate_total_with_late_fees(rent: Decimal, utilities: Decimal, day: int) -> dict:
    """
    Calculate the total amount due including late fees.
    
    Late fee rules:
    - Day 1: No penalty (grace day)
    - Day 2: $500 MXN initial penalty
    - Days 3-7: $500 + $100/day additional
    - Day 8+: Same calculation, but with termination warning
    
    Args:
        rent: Base rent amount
        utilities: Utility charges (can be 0)
        day: Current day of month
    
    Returns:
        Dict with total_due, breakdown, and status
    """
    result = calculate_rentas_claras_balance(
        base_rent=rent,
        utilities=utilities,
        current_day=day
    )
    
    return {
        "total_due": result.total_due,
        "breakdown": result.breakdown,
        "status": result.status,
        "penalties": result.total_penalties,
        "warning_message": result.warning_message,
    }


def send_rent_reminders():
    """
    Main function to send rent reminders to unpaid tenants.
    
    This is called by APScheduler at 9 AM on configured days.
    It handles:
    1. Determining which message type to send based on day
    2. Querying unpaid tenants who haven't been messaged today
    3. Calculating late fees
    4. Sending WhatsApp messages via Meta API
    5. Logging results for idempotency
    
    Returns:
        Dict with summary of actions taken
    """
    now = datetime.now(MX_TZ)
    current_day = now.day
    current_year = now.year
    current_month = now.month
    
    # Get Spanish month name
    month_names = {
        1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
        5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
        9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
    }
    month_name = month_names.get(current_month, str(current_month))
    
    logger.info(f"🔔 Starting rent reminders for {month_name} {current_year}, day {current_day}")
    
    # Determine message type for today
    message_type = get_message_type_for_day(current_day)
    if not message_type:
        logger.info(f"ℹ️ No scheduled reminders for day {current_day}")
        return {"status": "skipped", "reason": f"Day {current_day} is not a reminder day"}
    
    logger.info(f"📝 Message type for today: {message_type}")
    
    # Get unpaid tenants who haven't been messaged today
    tenants = get_unpaid_tenants_for_reminder(current_year, current_month, message_type)
    
    if not tenants:
        logger.info("✅ All tenants either paid or already messaged today")
        return {"status": "completed", "sent": 0, "reason": "No tenants to message"}
    
    logger.info(f"📤 Found {len(tenants)} tenants to message")
    
    # Track results
    results = {
        "status": "completed",
        "sent": 0,
        "failed": 0,
        "details": []
    }
    
    # Send messages to each tenant
    for tenant in tenants:
        tenant_id = tenant["id"]
        tenant_name = tenant["name"]
        phone = tenant["phone"]
        rent = tenant["rent"]
        
        # Calculate total with late fees
        # For now, assume no utilities tracked (can be enhanced later)
        utilities = Decimal("0")
        fee_info = calculate_total_with_late_fees(rent, utilities, current_day)
        
        # Format amount for message
        amount_str = f"{fee_info['total_due']:,.0f}"
        
        logger.info(f"📱 Sending to {tenant_name} ({tenant_id}): ${amount_str}")
        
        try:
            # Choose appropriate sender based on day
            if current_day == 1:
                response = send_rent_reminder(
                    to_phone=phone,
                    tenant_name=tenant_name.split()[0],  # First name only
                    month=month_name,
                    amount=amount_str
                )
            else:
                response = send_late_reminder(
                    to_phone=phone,
                    tenant_name=tenant_name.split()[0],
                    month=month_name,
                    amount=amount_str
                )
            
            if response.success:
                # Log successful send
                log_message_sent(
                    tenant_id=tenant_id,
                    message_type=message_type,
                    message_id=response.message_id,
                    status="sent"
                )
                results["sent"] += 1
                results["details"].append({
                    "tenant_id": tenant_id,
                    "name": tenant_name,
                    "status": "sent",
                    "message_id": response.message_id
                })
                logger.info(f"✅ Sent to {tenant_name}: {response.message_id}")
            else:
                # Log failed send
                log_message_sent(
                    tenant_id=tenant_id,
                    message_type=message_type,
                    status="failed",
                    error_message=response.error
                )
                results["failed"] += 1
                results["details"].append({
                    "tenant_id": tenant_id,
                    "name": tenant_name,
                    "status": "failed",
                    "error": response.error
                })
                logger.error(f"❌ Failed for {tenant_name}: {response.error}")
                
        except Exception as e:
            # Log exception
            error_msg = str(e)
            log_message_sent(
                tenant_id=tenant_id,
                message_type=message_type,
                status="failed",
                error_message=error_msg
            )
            results["failed"] += 1
            results["details"].append({
                "tenant_id": tenant_id,
                "name": tenant_name,
                "status": "error",
                "error": error_msg
            })
            logger.exception(f"💥 Exception for {tenant_name}: {e}")
    
    logger.info(f"📊 Summary: {results['sent']} sent, {results['failed']} failed")
    return results


def send_test_reminder(tenant_id: str, force: bool = False) -> dict:
    """
    Send a test reminder to a specific tenant.
    
    Args:
        tenant_id: The tenant's ID to message
        force: If True, send even if already messaged today
    
    Returns:
        Dict with result
    """
    from database import get_tenant_by_id
    
    tenant = get_tenant_by_id(tenant_id)
    if not tenant:
        return {"status": "error", "error": f"Tenant {tenant_id} not found"}
    
    if not tenant.phone:
        return {"status": "error", "error": "Tenant has no phone number"}
    
    now = datetime.now(MX_TZ)
    day = now.day
    
    # Check if already sent today
    message_type = get_message_type_for_day(day) or MSG_TYPE_DAY_1
    if not force and was_message_sent_today(tenant_id, message_type):
        return {"status": "skipped", "reason": "Already messaged today (use force=True to override)"}
    
    # Calculate fees
    fee_info = calculate_total_with_late_fees(tenant.rent, Decimal("0"), day)
    amount_str = f"{fee_info['total_due']:,.0f}"
    
    # Get month name
    month_names = {
        1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
        5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
        9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
    }
    month_name = month_names.get(now.month, str(now.month))
    
    try:
        response = send_rent_reminder(
            to_phone=tenant.phone,
            tenant_name=tenant.name.split()[0],
            month=month_name,
            amount=amount_str
        )
        
        if response.success:
            if not force:
                log_message_sent(tenant_id, message_type, response.message_id, "sent")
            return {
                "status": "sent",
                "message_id": response.message_id,
                "tenant": tenant.name,
                "amount": amount_str
            }
        else:
            return {"status": "failed", "error": response.error}
            
    except Exception as e:
        return {"status": "error", "error": str(e)}


# =============================================================================
# CLI Testing
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="RentasClaras Rent Reminder Tasks")
    parser.add_argument("--run", action="store_true", help="Run the reminder task now")
    parser.add_argument("--test", metavar="TENANT_ID", help="Send test to specific tenant")
    parser.add_argument("--force", action="store_true", help="Force send even if already sent today")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be sent without sending")
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("🔍 DRY RUN: Showing what would be sent...")
        now = datetime.now(MX_TZ)
        message_type = get_message_type_for_day(now.day) or MSG_TYPE_DAY_1
        tenants = get_unpaid_tenants_for_reminder(now.year, now.month, message_type)
        
        print(f"\n📅 Day {now.day} of {now.month}/{now.year}")
        print(f"📝 Message type: {message_type}")
        print(f"\n👥 Tenants to message ({len(tenants)}):")
        
        for t in tenants:
            fee_info = calculate_total_with_late_fees(t["rent"], Decimal("0"), now.day)
            print(f"   - {t['name']} ({t['id']}): ${fee_info['total_due']:,.2f}")
        
    elif args.test:
        print(f"📱 Sending test to {args.test}...")
        result = send_test_reminder(args.test, force=args.force)
        print(f"Result: {result}")
        
    elif args.run:
        print("🚀 Running rent reminders...")
        result = send_rent_reminders()
        print(f"Result: {result}")
        
    else:
        parser.print_help()

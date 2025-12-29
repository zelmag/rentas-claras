"""
Admin Blueprint - Admin/Scheduler Test Endpoints
=================================================

Protected endpoints for testing scheduler and manual triggers.
"""

import os

from flask import Blueprint, current_app, jsonify


admin_bp = Blueprint("admin", __name__)

# PIN from environment for authorization
RENTASCLARAS_PIN = os.environ.get("RENTASCLARAS_PIN")


# =============================================================================
# ROUTES
# =============================================================================

@admin_bp.route("/admin/test-scheduler/<secret_key>")
def admin_test_scheduler(secret_key):
    """
    Manually trigger the rent reminder scheduler for testing.

    Usage: https://your-app.fly.dev/admin/test-scheduler/your-secret-password

    This lets you test the scheduler without waiting for the actual day/time.
    Check fly logs to see the output.
    """
    if secret_key != RENTASCLARAS_PIN:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        # Import the run_rent_automation function from app context
        from src.tasks import send_rent_reminders

        with current_app.app_context():
            result = send_rent_reminders()
            return jsonify({
                "status": "triggered",
                "result": result,
                "message": "Check fly logs for details"
            })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@admin_bp.route("/admin/test-single/<secret_key>/<tenant_id>")
def admin_test_single(secret_key, tenant_id):
    """
    Send a test reminder to a single tenant.

    Usage: https://your-app.fly.dev/admin/test-single/your-secret-password/MAT-A
    """
    if secret_key != RENTASCLARAS_PIN:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        from src.tasks import send_test_reminder
        result = send_test_reminder(tenant_id, force=True)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@admin_bp.route("/admin/scheduler-status/<secret_key>")
def admin_scheduler_status(secret_key):
    """
    Check the status of scheduled jobs.

    Usage: https://your-app.fly.dev/admin/scheduler-status/your-secret-password
    """
    if secret_key != RENTASCLARAS_PIN:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        # Access scheduler from app config
        scheduler = current_app.config.get('scheduler')
        if not scheduler:
            return jsonify({
                "scheduler_running": False,
                "error": "Scheduler not found in app config"
            })

        from pytz import timezone
        MX_TZ = timezone("America/Mexico_City")

        jobs = []
        for job in scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": str(job.next_run_time) if job.next_run_time else None,
                "trigger": str(job.trigger),
            })

        return jsonify({
            "scheduler_running": scheduler.running,
            "jobs": jobs,
            "timezone": str(MX_TZ)
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

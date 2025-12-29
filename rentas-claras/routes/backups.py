"""
Backups Blueprint - Backup Management API
==========================================

Database backup and restore endpoints.
"""

from flask import Blueprint, jsonify, request

from routes.auth import login_required


backups_bp = Blueprint("backups", __name__)


# =============================================================================
# ROUTES
# =============================================================================

@backups_bp.route("/api/backups", methods=["GET"])
@login_required
def api_list_backups():
    """List all database backups."""
    try:
        from src.backup import list_backups, get_backup_stats

        backups = list_backups()
        stats = get_backup_stats()

        return jsonify({
            "success": True,
            "backups": backups,
            "stats": stats
        })
    except ImportError:
        return jsonify({
            "success": False,
            "error": "Backup module not available"
        }), 500


@backups_bp.route("/api/backups", methods=["POST"])
@login_required
def api_create_backup():
    """Create a new backup now."""
    try:
        from src.backup import create_backup

        result = create_backup(verify_first=True)

        return jsonify({
            "success": result["success"],
            "message": result["message"],
            "backup_path": result.get("backup_path"),
            "size_mb": result.get("size_mb")
        })
    except ImportError:
        return jsonify({
            "success": False,
            "error": "Backup module not available"
        }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@backups_bp.route("/api/backups/restore/<filename>", methods=["POST"])
@login_required
def api_restore_backup(filename):
    """
    Restore database from a backup file.

    DANGEROUS OPERATION - requires explicit confirmation.
    Request body must include: {"confirm": "YES_RESTORE"}
    """
    try:
        from src.backup import restore_backup

        data = request.json or {}
        confirm = data.get("confirm")

        if confirm != "YES_RESTORE":
            return jsonify({
                "success": False,
                "error": "Must confirm with 'YES_RESTORE' in request body"
            }), 400

        result = restore_backup(filename, create_safety_backup=True)

        if result["success"]:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except ImportError:
        return jsonify({
            "success": False,
            "error": "Backup module not available"
        }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@backups_bp.route("/api/database/health", methods=["GET"])
@login_required
def api_database_health():
    """Check database health and integrity."""
    try:
        from src.backup import verify_database_integrity, get_db_path, get_backup_stats

        db_path = get_db_path()

        if not db_path.exists():
            return jsonify({
                "healthy": False,
                "message": "Database file not found",
                "path": str(db_path)
            }), 500

        is_ok, message = verify_database_integrity(db_path)
        stats = get_backup_stats()

        return jsonify({
            "healthy": is_ok,
            "message": message,
            "database_path": str(db_path),
            "database_size_mb": stats.get("database_size_mb", 0),
            "total_backups": stats.get("total_backups", 0),
            "newest_backup": stats.get("newest_backup"),
            "backup_dir_exists": stats.get("backup_dir_exists", False)
        })
    except ImportError:
        return jsonify({
            "healthy": False,
            "error": "Backup module not available"
        }), 500
    except Exception as e:
        return jsonify({
            "healthy": False,
            "error": str(e)
        }), 500

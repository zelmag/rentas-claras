"""
RentasClaras Backup System
===========================

Automated backup system for the SQLite database.

Features:
- Timestamped local backups
- Automatic rotation (keeps last N backups)
- Pre-restore safety backup
- Integrity verification before backup
- WAL checkpoint before backup (ensures all data is written)

Backup Location: /data/backups/ (on Fly.io volume)
                 ./backups/ (local development)
"""

import logging
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Setup logging
logger = logging.getLogger(__name__)

# Backup configuration
MAX_BACKUPS = 30  # Keep last 30 backups (1 month of daily backups)
BACKUP_DIR_NAME = "backups"


def get_backup_dir() -> Path:
    """Get the backup directory path based on environment."""
    if os.path.exists("/data"):
        return Path("/data") / BACKUP_DIR_NAME
    else:
        return Path(__file__).parent.parent / BACKUP_DIR_NAME


def get_db_path() -> Path:
    """Get the database path (avoid circular import)."""
    if os.path.exists("/data"):
        return Path("/data/rentas_claras.db")
    else:
        return Path(__file__).parent.parent / "rentas_claras.db"


def verify_database_integrity(db_path: Path) -> tuple[bool, str]:
    """
    Run SQLite integrity check on the database.
    
    Returns:
        (is_ok, message) - True if database is healthy
    """
    try:
        conn = sqlite3.connect(str(db_path), timeout=30)
        cursor = conn.cursor()
        
        # Run integrity check
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]
        
        conn.close()
        
        if result == "ok":
            return True, "Database integrity check passed"
        else:
            return False, f"Database integrity check failed: {result}"
            
    except Exception as e:
        return False, f"Database integrity check error: {str(e)}"


def checkpoint_wal(db_path: Path) -> bool:
    """
    Force WAL checkpoint to ensure all data is written to main DB file.
    
    This is CRITICAL before backup to ensure we capture all data.
    """
    try:
        conn = sqlite3.connect(str(db_path), timeout=30)
        cursor = conn.cursor()
        
        # Force full checkpoint - writes all WAL content to main DB
        cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        result = cursor.fetchone()
        
        conn.close()
        
        logger.info(f"WAL checkpoint completed: {result}")
        return True
        
    except Exception as e:
        logger.error(f"WAL checkpoint failed: {e}")
        return False


def create_backup(verify_first: bool = True) -> Dict:
    """
    Create a timestamped backup of the database.
    
    Args:
        verify_first: If True, verify database integrity before backup
    
    Returns:
        Dict with backup result:
        {
            "success": bool,
            "backup_path": str or None,
            "message": str,
            "size_mb": float,
            "timestamp": str
        }
    """
    db_path = get_db_path()
    backup_dir = get_backup_dir()
    
    # Ensure backup directory exists
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if database exists
    if not db_path.exists():
        return {
            "success": False,
            "backup_path": None,
            "message": f"Database not found at {db_path}",
            "size_mb": 0,
            "timestamp": datetime.now().isoformat()
        }
    
    # Optional: Verify integrity before backup
    if verify_first:
        is_ok, message = verify_database_integrity(db_path)
        if not is_ok:
            logger.warning(f"Backup proceeding despite integrity issue: {message}")
    
    # Checkpoint WAL to ensure all data is in main DB file
    checkpoint_wal(db_path)
    
    # Create timestamped backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"rentas_claras_{timestamp}.db"
    backup_path = backup_dir / backup_filename
    
    try:
        # Use SQLite's backup API for safe copy (handles locking properly)
        source_conn = sqlite3.connect(str(db_path), timeout=30)
        dest_conn = sqlite3.connect(str(backup_path))
        
        source_conn.backup(dest_conn)
        
        source_conn.close()
        dest_conn.close()
        
        # Calculate backup size
        size_mb = backup_path.stat().st_size / (1024 * 1024)
        
        # Rotate old backups
        _rotate_backups()
        
        logger.info(f"Backup created: {backup_path} ({size_mb:.2f} MB)")
        
        return {
            "success": True,
            "backup_path": str(backup_path),
            "message": f"Backup created successfully",
            "size_mb": round(size_mb, 2),
            "timestamp": timestamp
        }
        
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        # Clean up partial backup if exists
        if backup_path.exists():
            backup_path.unlink()
        
        return {
            "success": False,
            "backup_path": None,
            "message": f"Backup failed: {str(e)}",
            "size_mb": 0,
            "timestamp": timestamp
        }


def _rotate_backups():
    """Keep only the last MAX_BACKUPS backups, delete older ones."""
    backup_dir = get_backup_dir()
    
    if not backup_dir.exists():
        return
    
    # Get all backup files sorted by name (which includes timestamp)
    backups = sorted(
        backup_dir.glob("rentas_claras_*.db"),
        key=lambda p: p.name,
        reverse=True  # Newest first
    )
    
    # Delete old backups beyond MAX_BACKUPS
    for old_backup in backups[MAX_BACKUPS:]:
        try:
            old_backup.unlink()
            logger.info(f"Rotated out old backup: {old_backup.name}")
        except Exception as e:
            logger.error(f"Failed to delete old backup {old_backup}: {e}")


def list_backups() -> List[Dict]:
    """
    List all available backups with metadata.
    
    Returns:
        List of dicts with backup info, newest first
    """
    backup_dir = get_backup_dir()
    
    if not backup_dir.exists():
        return []
    
    backups = []
    for backup_file in sorted(backup_dir.glob("rentas_claras_*.db"), reverse=True):
        try:
            stat = backup_file.stat()
            size_mb = stat.st_size / (1024 * 1024)
            
            # Parse timestamp from filename
            # Format: rentas_claras_YYYYMMDD_HHMMSS.db
            timestamp_str = backup_file.stem.replace("rentas_claras_", "")
            try:
                created = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                created_formatted = created.strftime("%Y-%m-%d %H:%M:%S")
            except:
                created_formatted = "Unknown"
            
            backups.append({
                "filename": backup_file.name,
                "path": str(backup_file),
                "size_mb": round(size_mb, 2),
                "created": created_formatted,
                "created_timestamp": stat.st_mtime
            })
        except Exception as e:
            logger.error(f"Error reading backup {backup_file}: {e}")
    
    return backups


def restore_backup(backup_filename: str, create_safety_backup: bool = True) -> Dict:
    """
    Restore database from a backup file.
    
    DANGEROUS OPERATION - creates a safety backup of current DB first.
    
    Args:
        backup_filename: Name of the backup file to restore
        create_safety_backup: If True, backup current DB before restoring
    
    Returns:
        Dict with restore result
    """
    backup_dir = get_backup_dir()
    db_path = get_db_path()
    backup_path = backup_dir / backup_filename
    
    # Validate backup exists
    if not backup_path.exists():
        return {
            "success": False,
            "message": f"Backup file not found: {backup_filename}",
            "safety_backup": None
        }
    
    # Verify backup integrity before restoring
    is_ok, message = verify_database_integrity(backup_path)
    if not is_ok:
        return {
            "success": False,
            "message": f"Backup file is corrupted: {message}",
            "safety_backup": None
        }
    
    safety_backup_path = None
    
    # Create safety backup of current database
    if create_safety_backup and db_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safety_backup_path = backup_dir / f"pre_restore_{timestamp}.db"
        
        try:
            shutil.copy2(db_path, safety_backup_path)
            logger.info(f"Safety backup created: {safety_backup_path}")
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to create safety backup: {str(e)}",
                "safety_backup": None
            }
    
    # Restore the backup
    try:
        # Use SQLite backup API for safe restore
        source_conn = sqlite3.connect(str(backup_path), timeout=30)
        dest_conn = sqlite3.connect(str(db_path))
        
        source_conn.backup(dest_conn)
        
        source_conn.close()
        dest_conn.close()
        
        logger.info(f"Database restored from: {backup_filename}")
        
        return {
            "success": True,
            "message": f"Database restored successfully from {backup_filename}",
            "safety_backup": str(safety_backup_path) if safety_backup_path else None
        }
        
    except Exception as e:
        logger.error(f"Restore failed: {e}")
        return {
            "success": False,
            "message": f"Restore failed: {str(e)}",
            "safety_backup": str(safety_backup_path) if safety_backup_path else None
        }


def get_backup_stats() -> Dict:
    """
    Get statistics about the backup system.
    
    Returns:
        Dict with backup stats
    """
    backup_dir = get_backup_dir()
    backups = list_backups()
    
    total_size_mb = sum(b["size_mb"] for b in backups)
    
    stats = {
        "backup_dir": str(backup_dir),
        "backup_dir_exists": backup_dir.exists(),
        "total_backups": len(backups),
        "total_size_mb": round(total_size_mb, 2),
        "max_backups": MAX_BACKUPS,
        "oldest_backup": backups[-1]["created"] if backups else None,
        "newest_backup": backups[0]["created"] if backups else None,
    }
    
    # Check database health
    db_path = get_db_path()
    if db_path.exists():
        is_ok, message = verify_database_integrity(db_path)
        stats["database_healthy"] = is_ok
        stats["database_message"] = message
        stats["database_size_mb"] = round(db_path.stat().st_size / (1024 * 1024), 2)
    else:
        stats["database_healthy"] = False
        stats["database_message"] = "Database not found"
        stats["database_size_mb"] = 0
    
    return stats


# Convenience function for scheduler
def scheduled_backup():
    """
    Entry point for scheduled backups.
    Logs result and returns success status.
    """
    logger.info("Starting scheduled backup...")
    result = create_backup(verify_first=True)
    
    if result["success"]:
        logger.info(f"Scheduled backup completed: {result['backup_path']}")
    else:
        logger.error(f"Scheduled backup failed: {result['message']}")
    
    return result["success"]


if __name__ == "__main__":
    # Test backup system
    logging.basicConfig(level=logging.INFO)
    
    print("Testing backup system...")
    
    # Get stats
    stats = get_backup_stats()
    print(f"\nBackup Stats: {stats}")
    
    # Create a backup
    result = create_backup()
    print(f"\nBackup Result: {result}")
    
    # List backups
    backups = list_backups()
    print(f"\nAvailable Backups: {len(backups)}")
    for b in backups[:5]:
        print(f"  - {b['filename']} ({b['size_mb']} MB) - {b['created']}")

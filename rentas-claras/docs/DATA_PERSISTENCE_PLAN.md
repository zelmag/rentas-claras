# 🔒 ROCK SOLID Data Persistence Plan

## 📋 Executive Summary

Your `rentas-claras` app uses SQLite on a Fly.io volume for data persistence. While this setup CAN work, there are **critical vulnerabilities** that may be causing data loss. This plan addresses each issue.

---

## 🔍 Current Architecture Analysis

### What You Have:
```
[Fly.io Machine] ---> [Volume: clara_data] ---> /data/rentas_claras.db
                                                     └── SQLite file
```

### Configuration:
- ✅ Volume mount configured (`clara_data` → `/data`)
- ✅ DB path checks for `/data` directory
- ✅ `auto_stop_machines = 'off'` (good!)
- ✅ `min_machines_running = 1` (good!)

---

## 🚨 IDENTIFIED PROBLEMS (Why Data Gets Lost)

### Problem 1: Volume Not Created
**Symptom:** App writes to `/data` but there's no volume attached
**Cause:** Volume must be explicitly created BEFORE the app deploys

**Check if volume exists:**
```bash
fly volumes list -a rentas-claras
```

If empty, this is your problem! The app is writing to an ephemeral directory.

**Fix:**
```bash
# Create the persistent volume
fly volumes create clara_data --region dfw --size 1 -a rentas-claras

# Redeploy to attach it
fly deploy
```

### Problem 2: Multiple Machines, One Volume
**Symptom:** Data appears/disappears randomly
**Cause:** Fly.io volumes can only attach to ONE machine. If you have >1 machine, only one sees the data.

**Check:**
```bash
fly machines list -a rentas-claras
```

**Fix:** Ensure only 1 machine or use a different database.

### Problem 3: SQLite WAL Mode Corruption on Volume
**Symptom:** Occasional data loss after writes
**Cause:** SQLite WAL files may not sync properly on network-attached volumes

**Fix:** Add explicit WAL mode with sync settings (see implementation below)

### Problem 4: No Backup Strategy
**Symptom:** Volume corruption = total data loss
**Cause:** Single point of failure

**Fix:** Implement automatic backups (see implementation below)

---

## ✅ IMPLEMENTATION PLAN

### Phase 1: Verify Volume Exists (TODAY - 5 minutes)

```bash
# Check volume
fly volumes list -a rentas-claras

# If no volumes, create one:
fly volumes create clara_data --region dfw --size 1 -a rentas-claras

# Check machines
fly machines list -a rentas-claras

# Redeploy
fly deploy
```

### Phase 2: Add SQLite Durability Settings (15 minutes)

Update `/Users/zelma/Desktop/ZelmaHelps_Agent/rentas-claras/database.py`:

```python
def get_db_connection():
    """Get a connection to the SQLite database with ROCK SOLID durability."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row

    # CRITICAL: These settings ensure data is written to disk
    cursor = conn.cursor()

    # Use WAL mode for better concurrency + crash safety
    cursor.execute("PRAGMA journal_mode=WAL")

    # FULL sync means every transaction waits for disk write confirmation
    # This is slower but GUARANTEES data isn't lost
    cursor.execute("PRAGMA synchronous=FULL")

    # Checkpoint WAL file after every 1000 pages
    cursor.execute("PRAGMA wal_autocheckpoint=1000")

    return conn
```

### Phase 3: Add Backup System (30 minutes)

Create `/Users/zelma/Desktop/ZelmaHelps_Agent/rentas-claras/src/backup.py`:

```python
"""
Automated backup system for RentasClaras.

Backs up SQLite database to:
1. Local timestamped file
2. (Optional) Cloud storage (Cloudflare R2, S3, etc.)
"""

import shutil
from datetime import datetime
from pathlib import Path
import os

# Backup location
BACKUP_DIR = Path("/data/backups")
MAX_BACKUPS = 30  # Keep last 30 backups

def create_backup() -> str:
    """Create a timestamped backup of the database."""
    from database import DB_PATH

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"rentas_claras_{timestamp}.db"

    # Copy database file
    shutil.copy2(DB_PATH, backup_path)

    # Also copy WAL file if exists
    wal_path = Path(str(DB_PATH) + "-wal")
    if wal_path.exists():
        shutil.copy2(wal_path, str(backup_path) + "-wal")

    # Rotate old backups
    _rotate_backups()

    return str(backup_path)

def _rotate_backups():
    """Keep only the last MAX_BACKUPS backups."""
    if not BACKUP_DIR.exists():
        return

    backups = sorted(BACKUP_DIR.glob("rentas_claras_*.db"), reverse=True)

    # Delete old backups
    for old_backup in backups[MAX_BACKUPS:]:
        old_backup.unlink()
        # Also delete WAL file
        wal = Path(str(old_backup) + "-wal")
        if wal.exists():
            wal.unlink()

def list_backups() -> list:
    """List all available backups."""
    if not BACKUP_DIR.exists():
        return []

    backups = []
    for backup_file in sorted(BACKUP_DIR.glob("rentas_claras_*.db"), reverse=True):
        size_mb = backup_file.stat().st_size / (1024 * 1024)
        backups.append({
            "filename": backup_file.name,
            "path": str(backup_file),
            "size_mb": round(size_mb, 2),
            "created": backup_file.stat().st_mtime
        })

    return backups

def restore_backup(backup_filename: str) -> bool:
    """Restore database from a backup file."""
    from database import DB_PATH

    backup_path = BACKUP_DIR / backup_filename
    if not backup_path.exists():
        return False

    # Create backup of current DB before restoring
    current_backup = BACKUP_DIR / f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy2(DB_PATH, current_backup)

    # Restore
    shutil.copy2(backup_path, DB_PATH)

    return True
```

### Phase 4: Schedule Automatic Backups (15 minutes)

Add to `/Users/zelma/Desktop/ZelmaHelps_Agent/rentas-claras/src/scheduler.py`:

```python
# Add this job in the scheduler setup:

from src.backup import create_backup

# Daily backup at 6 AM Mexico City time
scheduler.add_job(
    create_backup,
    trigger='cron',
    hour=6,
    minute=0,
    id='daily_backup',
    name='Daily Database Backup',
    replace_existing=True
)
```

### Phase 5: Add Backup API Endpoints (Optional - 20 minutes)

Add to `app.py`:

```python
from src.backup import create_backup, list_backups, restore_backup

@app.route('/api/backups', methods=['GET'])
def api_list_backups():
    """List all database backups."""
    return jsonify(list_backups())

@app.route('/api/backups', methods=['POST'])
def api_create_backup():
    """Create a new backup now."""
    backup_path = create_backup()
    return jsonify({"success": True, "path": backup_path})

@app.route('/api/backups/restore/<filename>', methods=['POST'])
def api_restore_backup(filename):
    """Restore from a backup (DANGEROUS - requires confirmation)."""
    confirm = request.json.get('confirm')
    if confirm != 'YES_RESTORE':
        return jsonify({"error": "Must confirm with 'YES_RESTORE'"}), 400

    success = restore_backup(filename)
    return jsonify({"success": success})
```

---

## 🎯 Priority Order

| Priority | Task | Time | Impact |
|----------|------|------|--------|
| 🔴 P0 | Verify/create Fly.io volume | 5 min | **Critical** |
| 🔴 P0 | Check for multiple machines | 2 min | **Critical** |
| 🟠 P1 | Add SQLite PRAGMA settings | 10 min | High |
| 🟡 P2 | Create backup system | 30 min | High |
| 🟡 P2 | Schedule automatic backups | 15 min | High |
| 🟢 P3 | Add backup API | 20 min | Medium |

---

## 🧪 Verification Steps

After implementing, verify with:

```bash
# 1. SSH into the machine and check
fly ssh console -a rentas-claras

# Inside the machine:
ls -la /data
# Should show: rentas_claras.db

# Check volume is mounted
df -h /data
# Should show the volume

# Check DB integrity
sqlite3 /data/rentas_claras.db "PRAGMA integrity_check;"
# Should return: ok

# Check WAL mode is active
sqlite3 /data/rentas_claras.db "PRAGMA journal_mode;"
# Should return: wal

# Exit
exit
```

---

## 🚀 Future Upgrades (When Scaling)

When you need even more reliability:

1. **Migrate to LiteFS** (Fly.io's distributed SQLite)
   - Multi-region replication
   - Automatic failover
   - https://fly.io/docs/litefs/

2. **Use Turso** (Managed SQLite)
   - Hosted SQLite with replication
   - Edge locations
   - https://turso.tech/

3. **Use PostgreSQL**
   - If you need multiple machines
   - Fly Postgres is well-supported
   - `fly postgres create`

---

## ⚡ Quick Commands Reference

```bash
# Check everything
fly volumes list -a rentas-claras
fly machines list -a rentas-claras
fly status -a rentas-claras

# SSH and check DB
fly ssh console -a rentas-claras
ls -la /data
sqlite3 /data/rentas_claras.db "SELECT COUNT(*) FROM tenants;"

# Create backup manually
fly ssh console -a rentas-claras -C "python -c 'from src.backup import create_backup; print(create_backup())'"

# View logs for issues
fly logs -a rentas-claras
```

---

## 📞 Emergency Recovery

If data is lost:

1. **Check if backup exists:**
   ```bash
   fly ssh console -a rentas-claras -C "ls -la /data/backups/"
   ```

2. **Restore from backup:**
   ```bash
   fly ssh console -a rentas-claras
   cp /data/backups/rentas_claras_YYYYMMDD_HHMMSS.db /data/rentas_claras.db
   ```

3. **If no backups, reseed:**
   ```bash
   fly ssh console -a rentas-claras
   python -c "from database import init_database, seed_tenants; init_database(); seed_tenants()"
   ```

---

## ✅ Checklist

- [ ] Verified Fly.io volume exists (`fly volumes list`)
- [ ] Confirmed only 1 machine running
- [ ] Added SQLite PRAGMA settings to `database.py`
- [ ] Created `src/backup.py`
- [ ] Added backup job to scheduler
- [ ] Tested backup/restore works
- [ ] Set up alerts for backup failures
- [ ] Documented recovery procedure

---

*Last updated: 2024-12-29*
*Author: DevMate*

# 🔒 Data Persistence Risk Analysis & Mitigations

## Summary: What We Implemented

| Implementation | File | Purpose |
|----------------|------|---------|
| SQLite durability settings | `database.py` | WAL mode + FULL sync = crash-safe writes |
| Startup health checks | `database.py` | Detect issues before they cause problems |
| Context manager for connections | `database.py` | Auto-commit/rollback prevents partial writes |
| Automated daily backups | `app.py` | 6 AM Mexico City time, 30-day retention |
| Backup system | `src/backup.py` | Create, list, restore, rotate backups |
| Backup API endpoints | `app.py` | Manual backup/restore via API |
| Database health API | `app.py` | Check integrity on demand |

---

## Risk Matrix

| Risk | Severity | Likelihood | Mitigation | Residual Risk |
|------|----------|------------|------------|---------------|
| **Volume not attached** | 🔴 CRITICAL | Medium | Startup health check warns | User must verify with `fly volumes list` |
| **SQLite corruption** | 🔴 CRITICAL | Low | WAL mode + integrity checks | Backup restores available |
| **Data loss from code deploy** | 🟢 LOW | Very Low | DB is on volume, not in code | Already protected |
| **Accidental data deletion** | 🟠 HIGH | Low | Pre-restore safety backups | User error still possible |
| **Volume failure** | 🔴 CRITICAL | Very Low | Daily backups on same volume | **See HOLE #1** |
| **Schema migration breaks data** | 🟡 MEDIUM | Low | Additive migrations only | Test before deploy |
| **Concurrent write corruption** | 🟡 MEDIUM | Low | WAL + FULL sync + foreign keys | SQLite handles this |
| **Scheduler runs twice** | 🟢 LOW | Medium | Message idempotency table | Already protected |

---

## ✅ What's Protected

### 1. Code Changes Won't Wipe Data
```
Code Repository         Fly.io Volume
     │                       │
     ▼                       ▼
┌─────────────┐        ┌─────────────┐
│   app.py    │        │  /data/     │
│ database.py │◄──────►│  ├── rentas_claras.db
│   etc...    │        │  └── backups/
└─────────────┘        └─────────────┘
     │                       │
     ▼                       │
 fly deploy             PERSISTS
   (new code)           (data stays)
```

### 2. Crash Recovery
```python
# WAL mode = Write-Ahead Logging
# If app crashes mid-write, WAL file contains the partial write
# On restart, SQLite automatically recovers from WAL
cursor.execute("PRAGMA journal_mode=WAL")
cursor.execute("PRAGMA synchronous=FULL")  # Wait for disk confirmation
```

### 3. Automatic Backups
```
Every day at 6 AM Mexico City:
1. Verify database integrity
2. Checkpoint WAL (flush to main DB)
3. Use SQLite backup API (handles locking)
4. Rotate old backups (keep last 30)
```

### 4. Safe Restores
```
Before any restore:
1. Verify backup file integrity
2. Create safety backup of current DB
3. Use SQLite backup API (atomic)
```

---

## 🕳️ HOLES IN THE LOGIC (Self-Critique)

### HOLE #1: Backups Are on the Same Volume
**Problem:** If the Fly.io volume fails completely, BOTH the database AND backups are lost.

**Current State:**
```
/data/
├── rentas_claras.db      ← Main database
└── backups/
    ├── rentas_claras_20241229_060000.db  ← Backup
    └── ...                                ← All on SAME volume!
```

**Why This Is Bad:** A volume failure (hardware, Fly.io outage, accidental deletion) wipes everything.

**Solution (NOT YET IMPLEMENTED):**
- Export backups to external storage (Cloudflare R2, S3, Google Drive)
- Cost: ~$0.015/GB/month for R2
- Complexity: Medium (add boto3 or r2 client)

**Recommendation:** Add off-site backup for **true** disaster recovery. Priority: P1

---

### HOLE #2: No Backup Verification After Creation
**Problem:** We create backups but don't verify they're restorable.

**Current State:** We check integrity BEFORE backup, but not AFTER.

**Why This Matters:** A corrupted backup file is useless.

**Solution (EASY FIX):**
```python
# After creating backup:
is_ok, msg = verify_database_integrity(backup_path)
if not is_ok:
    logger.error(f"Backup verification FAILED: {msg}")
    backup_path.unlink()  # Delete corrupted backup
```

**Recommendation:** Add post-backup verification. Priority: P2

---

### HOLE #3: No Alerting on Backup Failures
**Problem:** If backups fail silently for 30 days, you won't know until disaster strikes.

**Current State:** Logs are written, but no notifications.

**Solution:**
- Send WhatsApp/email alert on backup failure
- Add health check endpoint for monitoring services

**Recommendation:** Add backup failure alerts. Priority: P2

---

### HOLE #4: Single Machine Assumption
**Problem:** If you scale to 2+ machines, SQLite won't work properly.

**Current State:** Works fine with 1 machine.

**Why This Matters:** Fly.io might auto-scale under load, or you might manually add machines.

**Solution:**
- Keep `min_machines_running = 1` and `max = 1`
- Or migrate to PostgreSQL/LiteFS for multi-machine

**Recommendation:** Document clearly that this is single-machine only. Priority: P3

---

### HOLE #5: Restore Requires App Restart
**Problem:** After restoring a backup, the app might have cached connections.

**Current State:** We restore the file, but existing connections might see old data.

**Solution:**
- Add restart command to restore endpoint
- Or force new connections on restore

**Recommendation:** Add app restart after restore. Priority: P3

---

### HOLE #6: No Point-in-Time Recovery
**Problem:** Daily backups mean you could lose up to 24 hours of data.

**Current State:** Backup at 6 AM. Crash at 5:59 AM next day = 23h59m of data loss.

**Solution:**
- More frequent backups (every 4 hours)
- Or use SQLite continuous backup / WAL shipping

**Recommendation:** For a 32-tenant app, daily is probably fine. Priority: P4

---

### HOLE #7: Startup Health Check Doesn't Block
**Problem:** We warn about issues but start the app anyway.

**Current State:**
```python
def startup_health_check():
    # ... checks ...
    print("⚠️  WARNING: Low disk space!")  # But app still starts
```

**Why This Might Be OK:** Blocking startup could cause more problems (can't access to fix).

**Recommendation:** Keep non-blocking, but add critical alerts. Priority: P3

---

## 🎯 Recommended Priority Actions

### TODAY (5 minutes)
```bash
# Verify volume exists and is attached
fly volumes list -a rentas-claras
fly machines list -a rentas-claras

# SSH and verify
fly ssh console -a rentas-claras
ls -la /data
sqlite3 /data/rentas_claras.db "PRAGMA integrity_check;"
exit
```

### THIS WEEK
1. Deploy updated code with all mitigations
2. Manually trigger a backup: `POST /api/backups`
3. Verify backup was created: `GET /api/backups`

### NEXT WEEK
1. Add off-site backup (R2/S3) - Fixes HOLE #1
2. Add post-backup verification - Fixes HOLE #2
3. Add backup failure alerts - Fixes HOLE #3

---

## 📊 Final Risk Assessment

| Scenario | Before Mitigations | After Mitigations |
|----------|-------------------|-------------------|
| App crashes mid-write | 🔴 Possible data loss | 🟢 WAL recovery |
| Server restarts | 🟠 Uncertain state | 🟢 Health check + WAL |
| Code deploy | 🟢 Already safe | 🟢 Already safe |
| Accidental deletion via UI | 🔴 Permanent loss | 🟡 Restore from backup |
| Volume hardware failure | 🔴 Total loss | 🔴 Total loss (HOLE #1) |
| Schema migration bug | 🔴 Possible corruption | 🟡 Additive only + backup |

---

## API Reference

### Check Database Health
```bash
curl -X GET https://rentas-claras.fly.dev/api/database/health \
  -H "Cookie: session=..."
```

### Create Manual Backup
```bash
curl -X POST https://rentas-claras.fly.dev/api/backups \
  -H "Cookie: session=..."
```

### List All Backups
```bash
curl -X GET https://rentas-claras.fly.dev/api/backups \
  -H "Cookie: session=..."
```

### Restore from Backup (DANGEROUS)
```bash
curl -X POST https://rentas-claras.fly.dev/api/backups/restore/rentas_claras_20241229_060000.db \
  -H "Cookie: session=..." \
  -H "Content-Type: application/json" \
  -d '{"confirm": "YES_RESTORE"}'
```

---

## Conclusion

**Data is now MUCH safer** with these mitigations:
- ✅ Crash recovery (WAL + FULL sync)
- ✅ Daily automated backups
- ✅ Manual backup/restore capability
- ✅ Integrity checks on startup and before operations
- ✅ Safe connection handling

**But complete protection requires:**
- 🔴 Off-site backups (external storage)
- 🟡 Backup failure alerts
- 🟡 Post-backup verification

**Bottom line:** For a 32-tenant rental app, this level of protection is **very good**. The remaining HOLE #1 (same-volume backups) is the only critical gap, and it's a P1 priority to fix.

---

*Last updated: 2024-12-29*
*Risk analysis by: DevMate*

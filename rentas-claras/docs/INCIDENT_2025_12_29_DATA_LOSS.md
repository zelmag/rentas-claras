# 🚨 INCIDENT POSTMORTEM: Production Data Loss

**Date:** December 29, 2025
**Severity:** HIGH - Production data loss
**Duration:** ~2 hours (until detected and fixed)
**Author:** AI Assistant (Devmate)

---

## Summary

Production database was lost due to accidental deletion of the `[mounts]` section in `fly.toml` during a routine file update. This caused the Fly.io app to write to ephemeral container storage instead of the persistent volume, resulting in data loss on the next deploy.

---

## Timeline

| Time | Event |
|------|-------|
| Dec 28, 18:09 | `[mounts]` section added correctly in commit `1c32811` |
| Dec 29, 15:40 | Commit `64c30c0` rewrote `fly.toml` for webhook docs - **accidentally deleted `[mounts]` section** |
| Dec 29, ~16:00 | `fly deploy` executed - volume no longer mounted |
| Dec 29, ~16:00 | App created fresh empty database in `/app/rentas_claras.db` (ephemeral) |
| Dec 29, ~22:00 | User reported "0 Inquilinos" on production site |
| Dec 29, ~22:30 | Root cause identified - mount section missing |
| Dec 29, ~22:45 | Fixed by restoring `[mounts]` section and uploading local database |

---

## Root Cause

When the AI assistant (me) edited `fly.toml` to add documentation about webhooks and secrets, I used `write_to_file` to rewrite the entire file. In doing so, I **failed to preserve the critical `[mounts]` section**.

### The deleted section:
```toml
# Persistent storage for SQLite database
[mounts]
  source = "clara_data"
  destination = "/data"
```

### Why this matters:
- `database.py` checks if `/data` exists to determine production vs local environment
- Without the mount, `/data` doesn't exist
- App falls back to writing database in container filesystem (`/app/rentas_claras.db`)
- Container filesystem is **ephemeral** - wiped on every deploy
- All production data lost

---

## Impact

- **Data lost:** All tenant payment records from production
- **User impact:** Owner had to re-sync local database to production
- **Data pollution:** Local test data (payments marked as "Cobrado") was pushed to production

---

## Resolution

1. Restored `[mounts]` section in `fly.toml`
2. Redeployed to Fly.io
3. Uploaded local database to `/data/rentas_claras.db` on Fly.io volume
4. Restarted app

---

## Lessons Learned

1. **NEVER use `write_to_file` on infrastructure config files** - always use `str_replace_edit` to make targeted changes
2. **Critical sections in config files should have warning comments**
3. **Pre-deploy validation should check for required config sections**
4. **AI assistants need explicit rules about infrastructure files**

---

## Prevention Measures Implemented

### 1. Critical Section Markers in `fly.toml`
Added highly visible warning comments that AI and humans will notice.

### 2. Pre-Deploy Validation Script
Created `scripts/pre-deploy-check.sh` that validates critical config before deploying.

### 3. AI Assistant Rules
Created `.llms/rules/deployment-safety.md` with explicit rules for AI assistants.

### 4. This Postmortem
Documented for future reference and learning.

---

## Action Items

- [x] Fix `fly.toml` to restore `[mounts]` section
- [x] Upload database to production
- [x] Create postmortem document
- [ ] Add critical section markers to `fly.toml`
- [ ] Create pre-deploy validation script
- [ ] Create AI assistant rules file
- [ ] Consider adding backup strategy for production database

---

## Related Files

- `/rentas-claras/fly.toml` - Deployment configuration
- `/rentas-claras/database.py` - Database path logic
- `/rentas-claras/scripts/pre-deploy-check.sh` - Validation script (to be created)
- `/rentas-claras/.llms/rules/deployment-safety.md` - AI rules (to be created)

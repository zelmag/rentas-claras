# 🚨 Deployment Safety Rules for AI Assistants

> **CRITICAL**: These rules exist because of a data loss incident on 2025-12-29.
> See: `docs/INCIDENT_2025_12_29_DATA_LOSS.md`

## Rule 1: NEVER Overwrite Infrastructure Config Files

**Files that must NEVER be overwritten with `write_to_file`:**
- `fly.toml`
- `Dockerfile`
- `docker-compose.yml`
- `.env` files
- Any file in `scripts/`

**Instead:** Always use `str_replace_edit` to make targeted changes to these files.

### Why?
On 2025-12-29, an AI assistant used `write_to_file` on `fly.toml` to add documentation comments. In doing so, the critical `[mounts]` section was accidentally deleted. This caused all production data to be lost because the SQLite database was no longer stored on a persistent volume.

---

## Rule 2: Preserve Critical Sections

When editing `fly.toml`, the following sections are **CRITICAL** and must NEVER be removed:

```toml
# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  🚨🚨🚨 CRITICAL SECTION - DO NOT DELETE OR MODIFY WITHOUT CARE 🚨🚨🚨   ║
# ╚═══════════════════════════════════════════════════════════════════════════╝
[mounts]
  source = "clara_data"
  destination = "/data"
```

If you see a comment box like the above, **DO NOT DELETE IT**.

---

## Rule 3: Always Run Pre-Deploy Check

Before running `fly deploy`, always run the validation script:

```bash
./scripts/pre-deploy-check.sh && fly deploy
```

This script validates that critical config sections exist.

---

## Rule 4: Database Path Awareness

The app uses SQLite with this logic in `database.py`:

```python
if os.path.exists("/data"):
    DB_PATH = Path("/data/rentas_claras.db")  # Production (Fly.io)
else:
    DB_PATH = Path(__file__).parent / "rentas_claras.db"  # Local
```

**Key insight:** If `/data` doesn't exist on Fly.io (because mount is missing), the app creates a database in the container filesystem which is **ephemeral** and gets wiped on every deploy.

---

## Rule 5: When Editing fly.toml

Before making any changes to `fly.toml`:

1. **Read the current file first**
2. **Identify all sections** (especially `[mounts]`)
3. **Use `str_replace_edit`** for targeted changes only
4. **Verify the `[mounts]` section still exists** after changes
5. **Run `./scripts/pre-deploy-check.sh`** to validate

---

## Rule 6: Syncing Databases

- **Local** and **Production** databases are SEPARATE
- Local: `rentas_claras.db` in project folder
- Prod: `/data/rentas_claras.db` on Fly.io volume

**To upload local to prod** (use with caution - overwrites prod!):
```bash
echo "put rentas_claras.db /data/rentas_claras.db" | fly ssh sftp shell
fly apps restart rentas-claras
```

**To download prod backup:**
```bash
fly ssh sftp shell
# then: get /data/rentas_claras.db prod_backup.db
```

---

## Quick Reference

| Action | Safe Method |
|--------|-------------|
| Edit fly.toml | `str_replace_edit` (targeted changes only) |
| Add comments to fly.toml | `str_replace_edit` (targeted changes only) |
| Deploy | `./scripts/pre-deploy-check.sh && fly deploy` |
| Check mount exists | `grep -q "^\[mounts\]" fly.toml` |

# Ship & Deploy to Fly.io - Rentas Claras

## Quick Commands

```bash
# Full deploy workflow
cd /Users/zelma/Desktop/ZelmaHelps_Agent/rentas-claras
git add -A && git commit -m "Your commit message"
git push origin main
fly deploy
```

## Pre-Deploy Checklist

### ✅ Dockerfile Must Include ALL Directories

**CRITICAL**: Ensure your Dockerfile copies all necessary Python packages/directories:

```dockerfile
# Copy application code - DON'T FORGET ANY DIRECTORIES!
COPY app.py .
COPY database.py .
COPY src/ ./src/
COPY routes/ ./routes/       # ← REQUIRED for Flask blueprints
COPY services/ ./services/   # ← REQUIRED for service modules
COPY templates/ ./templates/
COPY static/ ./static/
```

**Common 502 Error Cause**: Missing `COPY` statements for Python modules = `ModuleNotFoundError` at startup.

### ✅ Test Locally Before Deploying

```bash
# Build and run Docker locally to catch missing files
docker build -t rentas-claras-test .
docker run -p 8080:8080 rentas-claras-test
# Visit http://localhost:8080 to verify
```

### ✅ Verify Git Remote

```bash
# Check current remote
git remote -v

# Should show:
# origin  https://github.com/zelmag/rentas-claras.git (fetch)
# origin  https://github.com/zelmag/rentas-claras.git (push)

# Fix if wrong:
git remote set-url origin https://github.com/zelmag/rentas-claras.git
```

---

## Debugging 502 Errors

### Check Fly.io Logs Immediately After Deploy

```bash
fly logs --app rentas-claras --no-tail | head -100
```

### Common Error Patterns

| Error | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: No module named 'X'` | Missing COPY in Dockerfile | Add `COPY X/ ./X/` to Dockerfile |
| `Worker failed to boot` | App crashes on startup | Check logs for traceback |
| `Connection refused` | Wrong port | Ensure `--bind 0.0.0.0:8080` |

### Verify Deployment

```bash
# Check HTTP status (302 = redirect to login = working)
curl -s -o /dev/null -w "%{http_code}" https://rentas-claras.fly.dev/
```

---

## Fly.io Useful Commands

```bash
# Deploy
fly deploy

# Check logs (live tail)
fly logs --app rentas-claras

# Check logs (recent, no tail)
fly logs --app rentas-claras --no-tail | head -50

# SSH into running machine
fly ssh console --app rentas-claras

# Check app status
fly status --app rentas-claras

# Restart app
fly apps restart rentas-claras

# Scale to 0 (stop paying)
fly scale count 0 --app rentas-claras

# Scale back up
fly scale count 1 --app rentas-claras
```

---

## Database Persistence

The SQLite database is stored on a Fly.io volume at `/data/rentas_claras.db`.

```bash
# Check volume
fly volumes list --app rentas-claras

# Backup database (download)
fly ssh sftp get /data/rentas_claras.db ./backup_rentas_claras.db --app rentas-claras
```

---

## Preventing Future Deployment Failures

1. **Always test Docker build locally first**
2. **Check logs immediately after `fly deploy`**
3. **Add new Python directories to Dockerfile immediately when creating them**
4. **Keep a mental checklist**: new route file? → update `routes/__init__.py` AND Dockerfile

---

## App URLs

- **Production**: https://rentas-claras.fly.dev/
- **Fly Dashboard**: https://fly.io/apps/rentas-claras
- **Monitoring**: https://fly.io/apps/rentas-claras/monitoring

---

## GitHub Repository

```bash
# Create repo if it doesn't exist (run once)
gh repo create rentas-claras --public --source=. --remote=origin --push

# Or manually create at https://github.com/new then:
git remote set-url origin https://github.com/zelmag/rentas-claras.git
git push -u origin main
```

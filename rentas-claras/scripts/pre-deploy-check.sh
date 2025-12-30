#!/bin/bash
# ============================================================================
# PRE-DEPLOY VALIDATION SCRIPT
# ============================================================================
# Run this BEFORE every `fly deploy` to prevent data loss incidents.
#
# Usage:
#   ./scripts/pre-deploy-check.sh
#
# Or integrate into your workflow:
#   ./scripts/pre-deploy-check.sh && fly deploy
#
# See: docs/INCIDENT_2025_12_29_DATA_LOSS.md for why this exists
# ============================================================================

set -e  # Exit on any error

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "============================================"
echo "🔍 PRE-DEPLOY VALIDATION CHECK"
echo "============================================"
echo ""

ERRORS=0

# ----------------------------------------------------------------------------
# CHECK 1: fly.toml exists
# ----------------------------------------------------------------------------
if [ ! -f "fly.toml" ]; then
    echo -e "${RED}❌ FAIL: fly.toml not found!${NC}"
    echo "   You must be in the project root directory."
    exit 1
fi
echo -e "${GREEN}✓${NC} fly.toml exists"

# ----------------------------------------------------------------------------
# CHECK 2: [mounts] section exists
# ----------------------------------------------------------------------------
if ! grep -q "^\[mounts\]" fly.toml; then
    echo -e "${RED}❌ CRITICAL FAIL: [mounts] section missing from fly.toml!${NC}"
    echo ""
    echo "   Without this section, your database will be stored in ephemeral"
    echo "   container storage and ALL DATA WILL BE LOST on every deploy!"
    echo ""
    echo "   Add this to fly.toml:"
    echo ""
    echo '   [mounts]'
    echo '     source = "clara_data"'
    echo '     destination = "/data"'
    echo ""
    echo "   See: docs/INCIDENT_2025_12_29_DATA_LOSS.md"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}✓${NC} [mounts] section exists"
fi

# ----------------------------------------------------------------------------
# CHECK 3: Mount destination is /data (not /app/data or anything else)
# ----------------------------------------------------------------------------
MOUNT_DEST=$(grep -A2 "^\[mounts\]" fly.toml | grep "destination" | sed 's/.*= *"//' | sed 's/".*//' | tr -d ' "')
if [ "$MOUNT_DEST" != "/data" ]; then
    echo -e "${RED}❌ CRITICAL FAIL: Mount destination is '$MOUNT_DEST' but should be '/data'${NC}"
    echo ""
    echo "   database.py expects the database at /data/rentas_claras.db"
    echo "   Current mount destination does not match!"
    echo ""
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}✓${NC} Mount destination is correct (/data)"
fi

# ----------------------------------------------------------------------------
# CHECK 4: Volume source name matches
# ----------------------------------------------------------------------------
MOUNT_SOURCE=$(grep -A2 "^\[mounts\]" fly.toml | grep "source" | sed 's/.*= *"//' | sed 's/".*//' | tr -d ' "')
if [ -z "$MOUNT_SOURCE" ]; then
    echo -e "${RED}❌ FAIL: No volume source defined in [mounts]${NC}"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}✓${NC} Volume source defined: $MOUNT_SOURCE"
fi

# ----------------------------------------------------------------------------
# CHECK 5: Dockerfile exists
# ----------------------------------------------------------------------------
if [ ! -f "Dockerfile" ]; then
    echo -e "${RED}❌ FAIL: Dockerfile not found!${NC}"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}✓${NC} Dockerfile exists"
fi

# ----------------------------------------------------------------------------
# CHECK 6: Required secrets reminder
# ----------------------------------------------------------------------------
echo ""
echo -e "${YELLOW}📋 REMINDER: Ensure these secrets are set on Fly.io:${NC}"
echo "   - SECRET_KEY"
echo "   - RENTASCLARAS_PIN"
echo "   - WHATSAPP_ACCESS_TOKEN"
echo "   - WHATSAPP_PHONE_NUMBER_ID"
echo "   - WHATSAPP_WEBHOOK_VERIFY_TOKEN"
echo ""
echo "   Check with: fly secrets list"
echo ""

# ----------------------------------------------------------------------------
# FINAL RESULT
# ----------------------------------------------------------------------------
echo "============================================"
if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}🚨 DEPLOY BLOCKED: $ERRORS critical error(s) found!${NC}"
    echo "============================================"
    echo ""
    echo "Fix the errors above before deploying."
    exit 1
else
    echo -e "${GREEN}✅ ALL CHECKS PASSED - Safe to deploy!${NC}"
    echo "============================================"
    echo ""
    echo "Run: fly deploy"
    exit 0
fi

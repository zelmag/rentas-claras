#!/bin/bash
# Quick start script for rentas-claras

cd "$(dirname "$0")"

# Kill any existing instance
pkill -f "python.*app.py" 2>/dev/null || true
sleep 1

# Load environment variables from .env
set -a
source .env
set +a

# Run the app
python app.py

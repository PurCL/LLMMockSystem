#!/bin/bash
# Driver: Initializes Aim repository and starts the web UI.
set -e

cd /app

# Initialize aim repo if not already done
if [ ! -d ".aim" ]; then
    aim init
    python create_run.py
fi

# Start aim web UI
exec aim up --host 0.0.0.0 --port 8080

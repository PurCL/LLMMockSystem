#!/bin/bash
# start_server.sh - Starts the vulnerable Aim server

set -e

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Store PID for cleanup
AIM_PID=""
AIM_DIR_CREATED=false

# =====================================================================
# 🧹 Cleanup Function
# =====================================================================
cleanup() {
    echo ""
    echo "[⚙️ Teardown] Initiating cleanup..."

    # Kill the Aim server if running
    if [ -n "$AIM_PID" ] && kill -0 $AIM_PID 2>/dev/null; then
        echo "[⚙️ Teardown] Shutting down Aim server (PID: $AIM_PID)..."
        kill -9 $AIM_PID 2>/dev/null || true
    fi

    # Clean up any remaining processes on port 9090
    echo "[⚙️ Teardown] Checking for remaining processes on port 9090..."
    lsof -ti:9090 2>/dev/null | xargs -r kill -9 2>/dev/null || true

    # Clean up any remaining aim processes
    pkill -9 -f "aim up" 2>/dev/null || true

    # Remove .aim directory if it was created by this script
    if [ "$AIM_DIR_CREATED" = true ] && [ -d "$SCRIPT_DIR/.aim" ]; then
        echo "[⚙️ Teardown] Removing .aim directory created by this script..."
        rm -rf "$SCRIPT_DIR/.aim"
    fi

    echo "[✓] Cleanup complete. Goodbye!"
}

# Register trap to execute cleanup on EXIT, SIGINT (Ctrl+C), or SIGTERM
trap cleanup EXIT INT TERM

# Check if .aim directory exists, if not initialize
if [ ! -d ".aim" ]; then
    echo "[*] Initializing Aim repository..."
    AIM_DIR_CREATED=true
    aim init

    # Create a dummy run so the search endpoint has data to query
    echo "[*] Creating dummy run..."
    python3 << 'EOF'
from aim import Run
run = Run()
run["dummy"] = 1
run.track(1.0, name="metric")
run.close()
print("Dummy run created successfully.")
EOF
fi

# Start the vulnerable Aim server on port 9090
echo "[*] Starting Aim server on http://localhost:9090..."
echo "[*] Press Ctrl+C to stop the server"

# Run in background to capture PID
aim up --host 0.0.0.0 --port 9090 &
AIM_PID=$!

# Wait for the process
wait $AIM_PID

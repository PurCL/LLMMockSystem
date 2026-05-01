#!/bin/bash

echo "=================================================="
echo "   [Server] CVE-2023-0297 Mock Target Server Startup     "
echo "=================================================="

# Store PID for cleanup
PYLOAD_PID=""

# =====================================================================
# 🧹 Cleanup Function
# =====================================================================
cleanup() {
    echo ""
    echo "[⚙️ Teardown] Initiating cleanup..."

    # Kill pyLoad server if running
    if [ -n "$PYLOAD_PID" ] && kill -0 $PYLOAD_PID 2>/dev/null; then
        echo "[⚙️ Teardown] Shutting down pyLoad server (PID: $PYLOAD_PID)..."
        kill -9 $PYLOAD_PID 2>/dev/null || true
    fi

    # Clean up any remaining pyload processes
    pkill -9 -f "python3 -m pyload" 2>/dev/null || true

    # Remove test script and success indicator
    if [ -f "/tmp/pwn" ]; then
        echo "[⚙️ Teardown] Removing /tmp/pwn test script..."
        rm -f /tmp/pwn
    fi

    if [ -f "/tmp/pwn_success" ]; then
        echo "[⚙️ Teardown] Removing /tmp/pwn_success indicator..."
        rm -f /tmp/pwn_success
    fi

    # Remove pyLoad generated files/directories if they exist
    if [ -d "$HOME/.pyload" ]; then
        echo "[⚙️ Teardown] Removing ~/.pyload directory..."
        rm -rf "$HOME/.pyload"
    fi

    echo "[✓] Cleanup complete. Goodbye!"
}

# Register trap to execute cleanup on EXIT, SIGINT (Ctrl+C), or SIGTERM
trap cleanup EXIT INT TERM

echo "[*] 1. Creating test script for RCE verification (/tmp/pwn)..."
cat << 'EOF' > /tmp/pwn
#!/bin/bash
touch /tmp/pwn_success
echo "Vulnerability Confirmed (Mock Environment)" > /tmp/pwn_success
EOF
chmod +x /tmp/pwn
rm -f /tmp/pwn_success

echo "[*] 2. Starting pyLoad server in Mock environment..."
# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH=$SCRIPT_DIR/project/src:$PYTHONPATH

echo "=================================================="
echo " 🚦 Server will run in foreground, observe LLM interception logs in this terminal "
echo " 👉 Please open another terminal to run trigger_exploit.sh       "
echo " 🛑 Press Ctrl+C to terminate the server anytime                "
echo "=================================================="

# Run in background to capture PID
python3 -m pyload &
PYLOAD_PID=$!

# Wait for the process
wait $PYLOAD_PID
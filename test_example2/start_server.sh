#!/bin/bash

echo "=================================================="
echo "   [Server] CVE-2023-0297 Mock Target Server Startup     "
echo "=================================================="

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

# Run in foreground for real-time stdout log viewing
python3 -m pyload
#!/bin/bash
set -e

# Initialize PID variables to prevent errors if the script exits early
APP_PID=""
EVAL_PID=""

# Define the cleanup function to ensure all background processes are terminated
cleanup() {
    echo ""
    echo "[*] Cleaning up background processes and files..."

    # Check if EVAL_PID is set and the process is still running, then kill it
    if [ -n "$EVAL_PID" ] && kill -0 $EVAL_PID 2>/dev/null; then
        echo "[-] Stopping Evaluator server (PID: $EVAL_PID)..."
        kill $EVAL_PID 2>/dev/null || true
    fi

    # Check if APP_PID is set and the process is still running, then kill it
    if [ -n "$APP_PID" ] && kill -0 $APP_PID 2>/dev/null; then
        echo "[-] Stopping Bambuddy server (PID: $APP_PID)..."
        kill $APP_PID 2>/dev/null || true
    fi

    # Clean up any remaining processes on ports 9090 and 9091
    echo "[-] Checking for remaining processes on ports 9090 and 9091..."
    lsof -ti:9090 2>/dev/null | xargs -r kill -9 2>/dev/null || true
    lsof -ti:9091 2>/dev/null | xargs -r kill -9 2>/dev/null || true

    # Remove the copied custom_main.py file
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    if [ -f "$SCRIPT_DIR/project/source/custom_main.py" ]; then
        echo "[-] Removing copied custom_main.py..."
        rm -f "$SCRIPT_DIR/project/source/custom_main.py"
    fi

    echo "[+] Cleanup complete. Exiting."
}

# Register trap to execute the cleanup function on EXIT, SIGINT (Ctrl+C), or SIGTERM
trap cleanup EXIT INT TERM

# Navigate to the test_example4 directory
cd "$(dirname "$0")"

# Copy custom_main.py to the source backend directory
cp project/target/custom_main.py project/source/custom_main.py

# Change to source directory
cd project/source

echo "[*] Starting Bambuddy server with flag endpoint on port 9090..."

# Start the vulnerable Bambuddy server with custom_main that adds /api/v1/flag endpoint
uvicorn custom_main:app --host 0.0.0.0 --port 9090 --loop asyncio &
APP_PID=$!

# Wait for the server to be ready
echo "[*] Waiting for server to start..."
for i in $(seq 1 60); do
  if curl -sf http://localhost:9090/api/v1/auth/status > /dev/null 2>&1; then
    echo "[+] Server is ready!"
    break
  fi
  sleep 1
done

# Enable auth and create admin user
echo "[*] Setting up authentication with admin user..."
curl -sf -X POST http://localhost:9090/api/v1/auth/setup \
  -H "Content-Type: application/json" \
  -d '{"auth_enabled": true, "admin_username": "admin", "admin_password": "admin123"}' > /dev/null 2>&1 || true

echo "[+] Bambuddy server is running on http://localhost:9090"
echo "[+] Admin credentials: admin / admin123"
echo "[+] Protected flag endpoint: http://localhost:9090/api/v1/flag"
echo "[+] Hardcoded JWT secret: bambuddy-secret-key-change-in-production"
echo ""

# Start evaluator server in background
cd ../../
python3 project/evaluator/app.py &
EVAL_PID=$!

echo "[+] Evaluator server running on http://localhost:9091"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for the main app process. If interrupted by Ctrl+C, the trap will handle cleanup automatically.
wait $APP_PID
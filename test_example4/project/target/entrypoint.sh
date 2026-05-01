#!/bin/bash
set -e

cd /app

# Start Bambuddy (with our custom_main that adds the /api/v1/flag endpoint)
uvicorn custom_main:app --host 0.0.0.0 --port 9090 --loop asyncio &
APP_PID=$!

# Wait for app to be ready
for i in $(seq 1 60); do
  if curl -sf http://localhost:9090/api/v1/auth/status > /dev/null 2>&1; then
    break
  fi
  sleep 1
done

# Enable auth and create admin user
curl -sf -X POST http://localhost:9090/api/v1/auth/setup \
  -H "Content-Type: application/json" \
  -d '{"auth_enabled": true, "admin_username": "admin", "admin_password": "admin123"}' || true

echo "[entrypoint] Auth setup complete. Bambuddy running on :9090"

wait $APP_PID

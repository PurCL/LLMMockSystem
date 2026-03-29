#!/bin/bash
set -e

echo "=== DocuServe Backend Starting ==="

# Wait for database to be ready
echo "Waiting for database to be ready..."
max_attempts=30
attempt=1

while ! nc -z db 5432; do
  if [ $attempt -eq $max_attempts ]; then
    echo "❌ Database connection timeout after $max_attempts attempts"
    exit 1
  fi
  echo "Attempt $attempt/$max_attempts: Database not ready, waiting..."
  sleep 2
  attempt=$((attempt + 1))
done

echo "✅ Database is ready!"

# Always run initialization
echo "Running database initialization..."
# Default to scripts.seed_public if INIT_SCRIPT is not set
INIT_SCRIPT=${INIT_SCRIPT:-scripts.seed_public}
python -m "$INIT_SCRIPT"

# Check if initialization was successful
if [ $? -eq 0 ]; then
    echo "✅ Database initialization completed!"
else
    echo "❌ Database initialization failed!"
    exit 1
fi

# Start the main application
# Default to port 8000 and host 0.0.0.0 if not set
APP_PORT=${PORT:-8000}
APP_HOST=${HOST:-0.0.0.0}

echo "🚀 Starting FastAPI application on $APP_HOST:$APP_PORT..."
exec uvicorn app.main:app --host "$APP_HOST" --port "$APP_PORT" --reload

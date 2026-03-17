#!/bin/bash

echo "🧹 1. Destroying the old environment..."
rm -rf .venv

echo "🌱 2. Rebuilding the virtual environment at lightning speed using uv..."
uv venv

echo "📦 3. Installing core testing tools, Agent dependencies, database drivers, and application skeleton..."
uv pip install claude-agent-sdk pytest-playwright psycopg2-binary fastapi sqlmodel "uvicorn[standard]" email-validator sniffio

echo "🌐 4. Downloading browser binaries..."
# The environment must be activated first to use the playwright command
source .venv/bin/activate
playwright install chromium

echo "🪝 5. Remounting the LLM dependency auto-healing interceptor..."
python install_hook.py

echo "===================================================="
echo "✨ Golden baseline environment reset complete! You can now start the next round of clean testing."
echo "Please run manually: source .venv/bin/activate && python -m uvicorn app.main:app"
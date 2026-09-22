#!/bin/bash

# CVE Results Web Server Startup Script

echo "========================================"
echo "🛡️  CVE Results Web Server"
echo "========================================"
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python3 is not installed"
    exit 1
fi

echo "✅ Python3 found: $(python3 --version)"
echo ""

# Check and install dependencies
echo "📦 Checking dependencies..."
if ! python3 -c "import flask" 2>/dev/null; then
    echo "⚠️  Flask not installed, installing dependencies..."
    pip3 install -r requirements.txt --user
else
    echo "✅ Dependencies installed"
fi
echo ""

# Start server
echo "🚀 Starting web server..."
echo ""
python3 server.py

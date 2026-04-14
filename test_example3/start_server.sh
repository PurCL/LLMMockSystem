#!/bin/bash
# Start the vulnerable lollms-webui server (CVE-2024-2624)
# This script starts the server on port 9090

set -e

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/project"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Starting lollms-webui Server (CVE-2024-2624)${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if project directory exists
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}Error: Project directory not found at $PROJECT_DIR${NC}"
    exit 1
fi

# Navigate to project directory
cd "$PROJECT_DIR"

# Create necessary directories
echo -e "${YELLOW}Creating necessary directories...${NC}"
mkdir -p web/dist
mkdir -p databases
mkdir -p configs

# Create a minimal index.html for static files if not exists
if [ ! -f "web/dist/index.html" ]; then
    echo -e "${YELLOW}Creating minimal web interface...${NC}"
    mkdir -p web/dist
    cat > web/dist/index.html <<'EOF'
<!DOCTYPE html>
<html>
<head><title>LoLLMS WebUI</title></head>
<body><h1>LoLLMS WebUI Running</h1><p>Server is active on port 9090</p></body>
</html>
EOF
fi

# Create the secret file for the exploit
echo -e "${YELLOW}Creating secret file at /tmp/uploads/secret...${NC}"
mkdir -p /tmp/uploads
echo "This is a secret file for CVE-2024-2624 demonstration" | tee /tmp/uploads/secret > /dev/null
chmod 644 /tmp/uploads/secret
echo -e "${GREEN}Secret file created successfully${NC}"

# Export environment variables
export PYTHONPATH="$PROJECT_DIR:$PROJECT_DIR/lollms_core:$PYTHONPATH"

# Start the server on port 9090
echo -e "${GREEN}Starting server on http://0.0.0.0:9090${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

# Run the application
python3 app.py --host 0.0.0.0 --port 9090

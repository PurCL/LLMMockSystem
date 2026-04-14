#!/bin/bash

# =====================================================================
# Configuration & Styling
# =====================================================================
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

BACKEND_DIR="$HOME/data3/LLMMockSystem/test_example1/project/src/backend"
PORT_FILE="/tmp/llm_mock_server_port.txt"
DB_ENV_FILE="/tmp/llm_mock_db_env.sh"

SERVER_PID=""

# =====================================================================
# 🧹 Teardown Sequence (Server)
# =====================================================================
cleanup_server() {
    echo -e "\n${YELLOW}[⚙️ Teardown] Initiating server cleanup...${NC}"

    if [ -n "$SERVER_PID" ] && kill -0 $SERVER_PID 2>/dev/null; then
        echo -e "${YELLOW}[⚙️ Teardown] Shutting down FastAPI server (PID: $SERVER_PID)...${NC}"
        kill -9 $SERVER_PID 2>/dev/null
    fi

    # Clean up port file
    if [ -f "$PORT_FILE" ]; then
        echo -e "${YELLOW}[⚙️ Teardown] Removing port file ${PORT_FILE}...${NC}"
        rm -f "$PORT_FILE"
    fi

    echo -e "${GREEN}[⚙️ Teardown] Server cleanup complete. Goodbye!${NC}"
}

trap cleanup_server EXIT

# =====================================================================
# 🚀 Phase 2: Start Backend Server
# =====================================================================
get_free_port() {
    # Adding -S prevents Python from loading site modules (often bypassing hooks entirely)
    # Using grep -Eo '^[0-9]+$' guarantees we only capture the actual number
    python3 -S -c 'import socket; s=socket.socket(); s.bind(("", 0)); print(s.getsockname()[1]); s.close()' 2>/dev/null | grep -Eo '^[0-9]+$' | head -n 1
}

start_server() {
    echo -e "\n${YELLOW}[🚀 Phase 2] Initializing FastAPI server startup sequence...${NC}"

    # 检查数据库环境变量文件是否存在并加载
    if [ ! -f "$DB_ENV_FILE" ]; then
        echo -e "${RED}[🚀 Phase 2] ❌ Error: Database environment file not found at ${DB_ENV_FILE}${NC}"
        echo -e "${RED}Please ensure start_database.sh is running in another terminal.${NC}"
        exit 1
    fi

    echo -e "${YELLOW}[🚀 Phase 2] Loading database environment variables from ${DB_ENV_FILE}...${NC}"
    source "$DB_ENV_FILE"

    if [ ! -d "$BACKEND_DIR" ]; then
        echo -e "${RED}[🚀 Phase 2] ❌ Error: Directory not found at ${BACKEND_DIR}${NC}"
        exit 1
    fi

    cd "$BACKEND_DIR" || exit 1
    
    SERVER_PORT=$(get_free_port)
    echo -e "${YELLOW}[🚀 Phase 2] 🎯 Dynamic Server Port ${SERVER_PORT} acquired...${NC}"

    # Save port to temporary file for run_exploit.sh to read
    echo "$SERVER_PORT" > "$PORT_FILE"
    echo -e "${GREEN}[🚀 Phase 2] ✅ Port ${SERVER_PORT} saved to ${PORT_FILE}${NC}"

    # 启动服务器并放入后台以便记录 PID
    python -m uvicorn app.main:app --host 127.0.0.1 --port $SERVER_PORT &
    SERVER_PID=$!
    
    echo -e "${GREEN}[🚀 Phase 2] ✅ Server is running on PID $SERVER_PID${NC}"
    echo -e "${YELLOW}Press [CTRL+C] to stop the server.${NC}"
    
    # 等待服务器进程
    wait $SERVER_PID
}

# =====================================================================
# Main Execution Flow
# =====================================================================
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  LLM Mock System - Backend Server${NC}"
echo -e "${GREEN}========================================${NC}"

start_server
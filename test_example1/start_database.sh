#!/bin/bash

# =====================================================================
# Configuration & Styling
# =====================================================================
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

CONTAINER_NAME=""
DB_ENV_FILE="/tmp/llm_mock_db_env.sh"

# =====================================================================
# 🧹 Teardown Sequence (Database)
# =====================================================================
cleanup_db() {
    echo -e "\n${YELLOW}[⚙️ Teardown] Initiating database cleanup...${NC}"

    if [ -n "$CONTAINER_NAME" ]; then
        echo -e "${YELLOW}[⚙️ Teardown] Stopping database container ${CONTAINER_NAME}...${NC}"
        docker stop "$CONTAINER_NAME" > /dev/null 2>&1
    fi

    if [ -f "$DB_ENV_FILE" ]; then
        echo -e "${YELLOW}[⚙️ Teardown] Removing env file ${DB_ENV_FILE}...${NC}"
        rm -f "$DB_ENV_FILE"
    fi

    echo -e "${GREEN}[⚙️ Teardown] Database cleanup complete. Goodbye!${NC}"
}

trap cleanup_db EXIT

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
        
        # 将环境变量写入临时文件供 server 脚本读取
        cat <<EOF > "$DB_ENV_FILE"
export POSTGRES_SERVER="localhost"
export POSTGRES_PORT="${DB_PORT}"
export POSTGRES_USER="postgres"
export POSTGRES_PASSWORD="changethis"
export POSTGRES_DB="app"
export SQLALCHEMY_DATABASE_URI="postgresql+psycopg2://postgres:changethis@localhost:${DB_PORT}/app"
export DATABASE_URL="postgresql+psycopg2://postgres:changethis@localhost:${DB_PORT}/app"
EOF
        echo -e "${GREEN}[🐳 Phase 1] ✅ Database environment variables saved to ${DB_ENV_FILE}${NC}"
    else
        echo -e "${RED}[🐳 Phase 1] ❌ Database startup timeout!${NC}"
        exit 1
    fi
}

# =====================================================================
# Main Execution Flow
# =====================================================================
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  LLM Mock System - Database Service${NC}"
echo -e "${GREEN}========================================${NC}"

setup_database

echo -e "\n${YELLOW}==================================================================${NC}"
echo -e "${GREEN}Database is running in the background.${NC}"
echo -e "${YELLOW}Please open a NEW terminal to run start_server.sh${NC}"
echo -e "${YELLOW}Press [CTRL+C] in this terminal to stop the DB and clean up.${NC}"
echo -e "${YELLOW}==================================================================${NC}"

# 保持脚本运行，直到用户按下 Ctrl+C
tail -f /dev/null
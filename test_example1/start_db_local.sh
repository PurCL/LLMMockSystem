#!/bin/bash

# =====================================================================
# Configuration & Styling
# =====================================================================
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

DB_ENV_FILE="/tmp/llm_mock_db_env.sh"
# Create a temporary data directory with a random PID suffix
PG_DATA_DIR="/tmp/llm_mock_pgdata_$$"
INIT_LOG="/tmp/llm_mock_init_$$.log"
PG_LOG="/tmp/llm_mock_pg_$$.log"
DB_PORT=""

# =====================================================================
# Auto-detect PostgreSQL path for Debian/Ubuntu
# =====================================================================
if [ -d "/usr/lib/postgresql" ]; then
    PG_BIN_DIR=$(ls -d /usr/lib/postgresql/*/bin 2>/dev/null | sort -V | tail -n 1)
    if [ -n "$PG_BIN_DIR" ]; then
        export PATH="$PATH:$PG_BIN_DIR"
    fi
fi

# =====================================================================
# 🧹 Teardown Sequence
# =====================================================================
cleanup_db() {
    echo -e "\n${YELLOW}[⚙️ Teardown] Initiating local database cleanup...${NC}"

    if command -v pg_ctl > /dev/null 2>&1 && [ -f "$PG_DATA_DIR/postmaster.pid" ]; then
        echo -e "${YELLOW}[⚙️ Teardown] Stopping local PostgreSQL instance...${NC}"
        if [ "$(id -u)" -eq 0 ]; then
            su postgres -c "pg_ctl -D '$PG_DATA_DIR' stop -m fast > /dev/null 2>&1"
        else
            pg_ctl -D "$PG_DATA_DIR" stop -m fast > /dev/null 2>&1
        fi
    fi

    if [ -d "$PG_DATA_DIR" ]; then
        echo -e "${YELLOW}[⚙️ Teardown] Removing temporary database files at ${PG_DATA_DIR}...${NC}"
        rm -rf "$PG_DATA_DIR"
    fi

    # Clean up external log files
    rm -f "$INIT_LOG" "$PG_LOG" > /dev/null 2>&1

    if [ -f "$DB_ENV_FILE" ]; then
        echo -e "${YELLOW}[⚙️ Teardown] Removing env file ${DB_ENV_FILE}...${NC}"
        rm -f "$DB_ENV_FILE"
    fi

    echo -e "${GREEN}[⚙️ Teardown] Database cleanup complete. Goodbye!${NC}"
}

trap cleanup_db EXIT

# =====================================================================
# 🐘 Phase 1: Dynamic Infrastructure (Local PostgreSQL)
# =====================================================================
get_free_port() {
    python3 -c 'import socket; s=socket.socket(); s.bind(("", 0)); print(s.getsockname()[1]); s.close()' 2>/dev/null | tail -1
}

check_dependencies() {
    for cmd in initdb pg_ctl pg_isready psql createdb; do
        if ! command -v "$cmd" > /dev/null 2>&1; then
            echo -e "${RED}❌ Error: '$cmd' is not installed or not in PATH.${NC}"
            exit 1
        fi
    done
}

wait_for_db_ready() {
    local port=$1
    local timeout=15
    local start_time=$(date +%s)
    
    while true; do
        if pg_isready -h localhost -p "$port" -U postgres > /dev/null 2>&1; then
            return 0
        fi
        
        local current_time=$(date +%s)
        if [ $((current_time - start_time)) -ge $timeout ]; then
            return 1
        fi
        sleep 1
    done
}

# Core helper: Automatically determine if we need to switch to the 'postgres' user for execution
run_pg_cmd() {
    if [ "$(id -u)" -eq 0 ]; then
        su postgres -c "export PATH=\"$PATH\"; $1"
    else
        eval "$1"
    fi
}

setup_database() {
    echo -e "${YELLOW}[🐘 Phase 1] Checking local PostgreSQL dependencies...${NC}"
    check_dependencies
    
    DB_PORT=$(get_free_port)
    echo -e "${YELLOW}[🐘 Phase 1] 🎯 Free port ${DB_PORT} locked, initializing local cluster...${NC}"
    
    # Create data directory and grant ownership to postgres user if running as root
    mkdir -p "$PG_DATA_DIR"
    if [ "$(id -u)" -eq 0 ]; then
        chown postgres:postgres "$PG_DATA_DIR"
    fi
    
    # 1. Initialize the database cluster (logs routing to an external file now!)
    run_pg_cmd "initdb -U postgres -D '$PG_DATA_DIR' --auth=trust > '$INIT_LOG' 2>&1"
    if [ $? -ne 0 ]; then
        echo -e "${RED}[🐘 Phase 1] ❌ initdb failed! Log output:${NC}"
        cat "$INIT_LOG"
        exit 1
    fi
    
    # 2. Start the local database instance
    echo -e "${YELLOW}[🐘 Phase 1] Starting PostgreSQL on port ${DB_PORT}...${NC}"
    run_pg_cmd "pg_ctl -D '$PG_DATA_DIR' -o '-p ${DB_PORT} -h localhost' -l '$PG_LOG' start > /dev/null 2>&1"
    
    if wait_for_db_ready "$DB_PORT"; then
        # 3. Set the superuser password and create the application database
        run_pg_cmd "psql -h localhost -p '$DB_PORT' -U postgres -c \"ALTER USER postgres WITH PASSWORD 'changethis';\" > /dev/null 2>&1"
        run_pg_cmd "createdb -h localhost -p '$DB_PORT' -U postgres app > /dev/null 2>&1"

        echo -e "${GREEN}[🐘 Phase 1] ✅ Database ready! (Port: ${DB_PORT})${NC}"
        
        # 4. Write environment variables to a temporary file for the server script to read
        cat <<EOF > "$DB_ENV_FILE"
export POSTGRES_SERVER="localhost"
export POSTGRES_PORT="${DB_PORT}"
export POSTGRES_USER="postgres"
export POSTGRES_PASSWORD="changethis"
export POSTGRES_DB="app"
export SQLALCHEMY_DATABASE_URI="postgresql+psycopg2://postgres:changethis@localhost:${DB_PORT}/app"
export DATABASE_URL="postgresql+psycopg2://postgres:changethis@localhost:${DB_PORT}/app"
EOF
        echo -e "${GREEN}[🐘 Phase 1] ✅ Database environment variables saved to ${DB_ENV_FILE}${NC}"
    else
        echo -e "${RED}[🐘 Phase 1] ❌ Database startup timeout! Check log output below:${NC}"
        cat "$PG_LOG"
        exit 1
    fi
}

# =====================================================================
# Main Execution Flow
# =====================================================================
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  LLM Mock System - Local DB Service${NC}"
echo -e "${GREEN}========================================${NC}"

setup_database

echo -e "\n${YELLOW}==================================================================${NC}"
echo -e "${GREEN}Local PostgreSQL is running in the background.${NC}"
echo -e "${YELLOW}Please open a NEW terminal to run start_server.sh${NC}"
echo -e "${YELLOW}Press [CTRL+C] in this terminal to stop the DB and clean up.${NC}"
echo -e "${YELLOW}==================================================================${NC}"

# Keep the script running in the foreground to maintain the trap/lifecycle
tail -f /dev/null
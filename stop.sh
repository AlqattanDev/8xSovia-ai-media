#!/bin/bash

# 8xSovia Media Gallery Stop Script
# Stops the backend server and optionally stops PostgreSQL and Redis

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}=== Stopping 8xSovia Media Gallery ===${NC}\n"

# Stop backend server
if [ -f "$PROJECT_DIR/.backend.pid" ]; then
    BACKEND_PID=$(cat "$PROJECT_DIR/.backend.pid")
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        echo -e "${YELLOW}Stopping backend server (PID: $BACKEND_PID)...${NC}"
        kill $BACKEND_PID
        rm "$PROJECT_DIR/.backend.pid"
        echo -e "${GREEN}✓${NC} Backend server stopped"
    else
        echo -e "${YELLOW}⚠${NC} Backend server not running"
        rm "$PROJECT_DIR/.backend.pid"
    fi
else
    echo -e "${YELLOW}⚠${NC} No backend PID file found"
fi

# Ask about stopping services
echo
read -p "Stop PostgreSQL and Redis services? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if command -v brew >/dev/null 2>&1; then
        echo -e "${YELLOW}Stopping PostgreSQL...${NC}"
        brew services stop postgresql@14 2>/dev/null || brew services stop postgresql
        echo -e "${GREEN}✓${NC} PostgreSQL stopped"

        echo -e "${YELLOW}Stopping Redis...${NC}"
        brew services stop redis
        echo -e "${GREEN}✓${NC} Redis stopped"
    else
        echo -e "${YELLOW}⚠${NC} Homebrew not found. Stop services manually"
    fi
fi

# Clean up log files
if [ -f "$PROJECT_DIR/backend.log" ]; then
    read -p "Remove log files? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm "$PROJECT_DIR/backend.log"
        echo -e "${GREEN}✓${NC} Log files removed"
    fi
fi

echo -e "\n${GREEN}Done!${NC}\n"

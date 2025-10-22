#!/bin/bash

# 8xSovia Setup Verification Script
# Checks if all prerequisites are met before running start.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== 8xSovia Setup Verification ===${NC}\n"

ERRORS=0
WARNINGS=0

# Check Python
echo -e "${BLUE}Checking Python...${NC}"
if command -v python3 >/dev/null 2>&1; then
    VERSION=$(python3 --version | cut -d' ' -f2)
    MAJOR=$(echo $VERSION | cut -d'.' -f1)
    MINOR=$(echo $VERSION | cut -d'.' -f2)

    if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 9 ]; then
        echo -e "${GREEN}✓${NC} Python $VERSION (>= 3.9 required)"
    else
        echo -e "${RED}✗${NC} Python $VERSION found, but 3.9+ required"
        ERRORS=$((ERRORS+1))
    fi
else
    echo -e "${RED}✗${NC} Python 3 not found"
    echo "  Install: brew install python3"
    ERRORS=$((ERRORS+1))
fi

# Check PostgreSQL
echo -e "\n${BLUE}Checking PostgreSQL...${NC}"
if command -v psql >/dev/null 2>&1; then
    VERSION=$(psql --version | cut -d' ' -f3)
    echo -e "${GREEN}✓${NC} PostgreSQL $VERSION installed"

    # Check if running
    if pg_isready >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} PostgreSQL is running"
    else
        echo -e "${YELLOW}⚠${NC} PostgreSQL is not running"
        echo "  Start: brew services start postgresql@14"
        WARNINGS=$((WARNINGS+1))
    fi
else
    echo -e "${RED}✗${NC} PostgreSQL not found"
    echo "  Install: brew install postgresql@14"
    ERRORS=$((ERRORS+1))
fi

# Check Redis
echo -e "\n${BLUE}Checking Redis...${NC}"
if command -v redis-cli >/dev/null 2>&1; then
    VERSION=$(redis-cli --version | cut -d' ' -f2)
    echo -e "${GREEN}✓${NC} Redis $VERSION installed"

    # Check if running
    if redis-cli ping >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Redis is running"
    else
        echo -e "${YELLOW}⚠${NC} Redis is not running"
        echo "  Start: brew services start redis"
        WARNINGS=$((WARNINGS+1))
    fi
else
    echo -e "${RED}✗${NC} Redis not found"
    echo "  Install: brew install redis"
    ERRORS=$((ERRORS+1))
fi

# Check .env file
echo -e "\n${BLUE}Checking configuration...${NC}"
if [ -f ".env" ]; then
    echo -e "${GREEN}✓${NC} .env file exists"
else
    echo -e "${YELLOW}⚠${NC} .env file not found"
    echo "  Copy: cp .env.example .env"
    WARNINGS=$((WARNINGS+1))
fi

# Check backend directory
echo -e "\n${BLUE}Checking project structure...${NC}"
if [ -d "backend" ]; then
    echo -e "${GREEN}✓${NC} Backend directory exists"

    if [ -f "backend/requirements.txt" ]; then
        echo -e "${GREEN}✓${NC} requirements.txt found"
    else
        echo -e "${RED}✗${NC} requirements.txt not found"
        ERRORS=$((ERRORS+1))
    fi

    if [ -d "backend/venv" ]; then
        echo -e "${GREEN}✓${NC} Virtual environment exists"
    else
        echo -e "${YELLOW}⚠${NC} Virtual environment not found (will be created by start.sh)"
        WARNINGS=$((WARNINGS+1))
    fi
else
    echo -e "${RED}✗${NC} Backend directory not found"
    ERRORS=$((ERRORS+1))
fi

# Check frontend
if [ -f "index.html" ]; then
    echo -e "${GREEN}✓${NC} Frontend (index.html) exists"
else
    echo -e "${RED}✗${NC} Frontend not found"
    ERRORS=$((ERRORS+1))
fi

# Check port availability
echo -e "\n${BLUE}Checking port availability...${NC}"
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠${NC} Port 8000 is in use"
    echo "  Process: $(lsof -Pi :8000 -sTCP:LISTEN | tail -1 | awk '{print $1}')"
    WARNINGS=$((WARNINGS+1))
else
    echo -e "${GREEN}✓${NC} Port 8000 is available"
fi

# Summary
echo -e "\n${BLUE}=== Summary ===${NC}"
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed! You're ready to run ./start.sh${NC}\n"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ $WARNINGS warning(s) found. You can still run ./start.sh${NC}\n"
    exit 0
else
    echo -e "${RED}✗ $ERRORS error(s) and $WARNINGS warning(s) found.${NC}"
    echo -e "${RED}Please fix the errors above before running ./start.sh${NC}\n"
    exit 1
fi

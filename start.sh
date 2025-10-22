#!/bin/bash

# 8xSovia Media Gallery Startup Script
# This script checks for prerequisites and starts all required services

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"

echo -e "${BLUE}=== 8xSovia Media Gallery Startup ===${NC}\n"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a service is running
check_service() {
    local service=$1
    local port=$2

    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $service is running on port $port"
        return 0
    else
        echo -e "${YELLOW}✗${NC} $service is not running on port $port"
        return 1
    fi
}

# Function to start PostgreSQL
start_postgresql() {
    echo -e "\n${BLUE}Starting PostgreSQL...${NC}"

    if command_exists brew; then
        # Check if PostgreSQL is installed via Homebrew
        if brew list postgresql@14 >/dev/null 2>&1 || brew list postgresql >/dev/null 2>&1; then
            brew services start postgresql@14 2>/dev/null || brew services start postgresql
            sleep 2
            echo -e "${GREEN}✓${NC} PostgreSQL started via Homebrew"
        else
            echo -e "${YELLOW}⚠${NC} PostgreSQL not found. Install it with:"
            echo "    brew install postgresql@14"
            return 1
        fi
    else
        echo -e "${YELLOW}⚠${NC} Homebrew not found. Please start PostgreSQL manually"
        return 1
    fi
}

# Function to start Redis
start_redis() {
    echo -e "\n${BLUE}Starting Redis...${NC}"

    if command_exists brew; then
        # Check if Redis is installed via Homebrew
        if brew list redis >/dev/null 2>&1; then
            brew services start redis
            sleep 1
            echo -e "${GREEN}✓${NC} Redis started via Homebrew"
        else
            echo -e "${YELLOW}⚠${NC} Redis not found. Install it with:"
            echo "    brew install redis"
            return 1
        fi
    else
        echo -e "${YELLOW}⚠${NC} Homebrew not found. Please start Redis manually"
        return 1
    fi
}

# Function to setup database
setup_database() {
    echo -e "\n${BLUE}Setting up database...${NC}"

    # Check if database exists
    if psql -lqt | cut -d \| -f 1 | grep -qw media_gallery; then
        echo -e "${GREEN}✓${NC} Database 'media_gallery' already exists"
    else
        echo -e "${YELLOW}Creating database...${NC}"
        createdb media_gallery 2>/dev/null || true

        # Create user if doesn't exist
        psql postgres -c "CREATE USER gallery_user WITH PASSWORD 'password';" 2>/dev/null || true
        psql postgres -c "GRANT ALL PRIVILEGES ON DATABASE media_gallery TO gallery_user;" 2>/dev/null || true
        psql media_gallery -c "GRANT ALL ON SCHEMA public TO gallery_user;" 2>/dev/null || true

        echo -e "${GREEN}✓${NC} Database created"
    fi

    # Run migrations
    cd "$BACKEND_DIR"
    if [ -d "alembic" ]; then
        echo -e "${BLUE}Running database migrations...${NC}"
        alembic upgrade head
        echo -e "${GREEN}✓${NC} Migrations complete"
    fi
}

# Function to install Python dependencies
install_dependencies() {
    echo -e "\n${BLUE}Installing Python dependencies...${NC}"

    cd "$BACKEND_DIR"

    if [ ! -f "requirements.txt" ]; then
        echo -e "${RED}✗${NC} requirements.txt not found in backend/"
        return 1
    fi

    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        python3 -m venv venv
    fi

    source venv/bin/activate
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    echo -e "${GREEN}✓${NC} Dependencies installed"
}

# Function to start backend server
start_backend() {
    echo -e "\n${BLUE}Starting backend server...${NC}"

    cd "$BACKEND_DIR"

    # Activate virtual environment
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi

    # Start server in background
    python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > "$PROJECT_DIR/backend.log" 2>&1 &
    BACKEND_PID=$!

    # Wait for server to start
    echo -e "${YELLOW}Waiting for backend to start...${NC}"
    for i in {1..10}; do
        if curl -s http://localhost:8000/api/health >/dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} Backend server started (PID: $BACKEND_PID)"
            echo $BACKEND_PID > "$PROJECT_DIR/.backend.pid"
            return 0
        fi
        sleep 1
    done

    echo -e "${RED}✗${NC} Backend failed to start. Check backend.log for errors"
    return 1
}

# Main execution
echo -e "${BLUE}Step 1: Checking prerequisites...${NC}"

# Check Python
if command_exists python3; then
    echo -e "${GREEN}✓${NC} Python 3 installed ($(python3 --version))"
else
    echo -e "${RED}✗${NC} Python 3 is required but not installed"
    exit 1
fi

# Check PostgreSQL
if command_exists psql; then
    echo -e "${GREEN}✓${NC} PostgreSQL installed"
    POSTGRES_OK=true
else
    echo -e "${YELLOW}⚠${NC} PostgreSQL not found"
    POSTGRES_OK=false
fi

# Check Redis
if command_exists redis-cli; then
    echo -e "${GREEN}✓${NC} Redis installed"
    REDIS_OK=true
else
    echo -e "${YELLOW}⚠${NC} Redis not found"
    REDIS_OK=false
fi

echo -e "\n${BLUE}Step 2: Starting services...${NC}"

# Start PostgreSQL if not running
if [ "$POSTGRES_OK" = true ]; then
    if ! check_service "PostgreSQL" 5432; then
        start_postgresql
    fi
else
    echo -e "${YELLOW}⚠${NC} Install PostgreSQL: brew install postgresql@14"
    exit 1
fi

# Start Redis if not running
if [ "$REDIS_OK" = true ]; then
    if ! check_service "Redis" 6379; then
        start_redis
    fi
else
    echo -e "${YELLOW}⚠${NC} Install Redis: brew install redis"
    exit 1
fi

# Setup database
setup_database

echo -e "\n${BLUE}Step 3: Installing dependencies...${NC}"
install_dependencies

echo -e "\n${BLUE}Step 4: Starting backend server...${NC}"
start_backend

# Display success message
echo -e "\n${GREEN}=== 🚀 Application Started Successfully! ===${NC}\n"
echo -e "Application:  ${BLUE}http://localhost:8000${NC}"
echo -e "API Docs:     ${BLUE}http://localhost:8000/docs${NC}"
echo -e "\nBackend logs: ${BLUE}tail -f $PROJECT_DIR/backend.log${NC}"
echo -e "\nTo stop the backend:"
echo -e "  ${YELLOW}kill \$(cat $PROJECT_DIR/.backend.pid)${NC}"
echo -e "\nTo stop services:"
echo -e "  ${YELLOW}brew services stop postgresql@14${NC}"
echo -e "  ${YELLOW}brew services stop redis${NC}\n"

# Open frontend in browser (optional)
read -p "Open application in browser? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    open "http://localhost:8000"
fi

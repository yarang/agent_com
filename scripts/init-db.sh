#!/bin/bash
#
# Database Initialization Script for AI Agent Communication System
#
# This script initializes the PostgreSQL database for the application.
#
# Usage:
#   ./scripts/init-db.sh              # Initialize database (interactive)
#   ./scripts/init-db.sh --yes        # Auto-confirm all prompts
#   ./scripts/init-db.sh --reset      # Drop and recreate all tables
#   ./scripts/init-db.sh --check      # Check database status only
#   ./scripts/init-db.sh --create     # Create database if needed
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuration
DB_NAME="${DB_NAME:-agent_comm}"
DB_USER="${DB_USER:-agent}"
DB_PASSWORD="${DB_PASSWORD:-password}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
ADMIN_USER="${ADMIN_USER:-postgres}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-password}"

# Parse arguments
AUTO_CONFIRM=""
RESET_MODE=""
CHECK_ONLY=""
CREATE_DB=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --yes|-y)
            AUTO_CONFIRM="yes"
            shift
            ;;
        --reset|-r)
            RESET_MODE="--reset"
            shift
            ;;
        --check|-c)
            CHECK_ONLY="--check"
            shift
            ;;
        --create)
            CREATE_DB="--create-db"
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Usage: $0 [--yes] [--reset] [--check] [--create]"
            exit 1
            ;;
    esac
done

# Functions
print_header() {
    local text="$1"
    local padding=$(( (60 - ${#text}) / 2 ))
    printf "\n${CYAN}${BOLD}============================================================${NC}\n"
    printf "${CYAN}${BOLD}%*s%s%*s${NC}\n" $padding "" "$text" $padding ""
    printf "${CYAN}${BOLD}============================================================${NC}\n\n"
}

print_step() {
    local step="$1"
    local total="$2"
    local text="$3"
    echo -e "${CYAN}[${step}/${total}] ${BOLD}${text}${NC}"
}

print_success() {
    echo -e "  ${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "  ${RED}✗${NC} $1"
}

print_warning() {
    echo -e "  ${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "  ${BLUE}ℹ${NC} $1"
}

# Check if PostgreSQL is running
check_postgres() {
    print_step 1 4 "Checking PostgreSQL connection"

    if command -v pg_isadmin &> /dev/null; then
        if pg_isadmin -h "$DB_HOST" -p "$DB_PORT" -U "$ADMIN_USER" &> /dev/null; then
            print_success "PostgreSQL is running"
            return 0
        fi
    fi

    if command -v psql &> /dev/null; then
        if PGPASSWORD="$ADMIN_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$ADMIN_USER" -d postgres -c '\q' &> /dev/null; then
            print_success "PostgreSQL is running"
            return 0
        fi
    fi

    print_error "Cannot connect to PostgreSQL"
    print_info "Make sure PostgreSQL is running on ${DB_HOST}:${DB_PORT}"
    print_info "You can start it with: docker-compose up -d postgres"
    return 1
}

# Create database if it doesn't exist
create_database() {
    print_step 2 4 "Creating database (if needed)"

    # Check if database exists
    if PGPASSWORD="$ADMIN_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$ADMIN_USER" -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
        print_success "Database '$DB_NAME' already exists"
        return 0
    fi

    # Create database
    print_info "Creating database '$DB_NAME'..."
    if PGPASSWORD="$ADMIN_PASSWORD" createdb -h "$DB_HOST" -p "$DB_PORT" -U "$ADMIN_USER" "$DB_NAME"; then
        print_success "Created database '$DB_NAME'"
    else
        print_error "Failed to create database"
        return 1
    fi
}

# Run Python initialization script
run_init_script() {
    local step_num=3
    local total_steps=4

    print_step $step_num $total_steps "Running database initialization"

    local python_cmd="python"
    if command -v python3 &> /dev/null; then
        python_cmd="python3"
    fi

    local script_args=""
    if [[ -n "$RESET_MODE" ]]; then
        script_args="$script_args $RESET_MODE"
    fi

    if [[ -n "$CHECK_ONLY" ]]; then
        script_args="$script_args $CHECK_ONLY"
    fi

    # Set DATABASE_URL for Python script
    export DATABASE_URL="postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"

    # Run the initialization script
    if $python_cmd scripts/init_db.py $script_args; then
        print_success "Database initialization completed"
        return 0
    else
        print_error "Database initialization failed"
        return 1
    fi
}

# Verify database
verify_database() {
    local step_num=4
    local total_steps=4

    print_step $step_num $total_steps "Verifying database"

    local python_cmd="python"
    if command -v python3 &> /dev/null; then
        python_cmd="python3"
    fi

    export DATABASE_URL="postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"

    if $python_cmd scripts/init_db.py --check; then
        print_success "Database verification passed"
        return 0
    else
        print_error "Database verification failed"
        return 1
    fi
}

# Main execution
main() {
    print_header "AI Agent Communication System - Database Initialization"

    if [[ -n "$CHECK_ONLY" ]]; then
        # Check mode only
        verify_database
        exit $?
    fi

    # Check PostgreSQL
    if ! check_postgres; then
        exit 1
    fi

    # Create database
    if [[ -n "$CREATE_DB" ]]; then
        if ! create_database; then
            exit 1
        fi
    fi

    # Run initialization
    if ! run_init_script; then
        exit 1
    fi

    # Summary
    print_header "Initialization Complete"

    print_success "Database is ready for use!"
    echo ""
    print_info "Database: ${DB_NAME}"
    print_info "Host: ${DB_HOST}:${DB_PORT}"
    print_info "User: ${DB_USER}"
    echo ""
    print_info "Default credentials:"
    print_info "  Admin username: admin"
    print_info "  Admin password: admin (CHANGE THIS IMMEDIATELY!)"
    echo ""
    print_info "Next steps:"
    print_info "  1. Start the communication server:"
    print_info "     python src/communication_server/main.py"
    echo ""
    print_info "  2. Or start with Docker Compose:"
    print_info "     docker-compose up -d"
    echo ""
    print_info "  3. Access the dashboard at:"
    print_info "     http://localhost:8000"
}

# Run main function
main

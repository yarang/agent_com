#!/bin/bash
# AI Agent Communication System - Development Script
# Run services in development mode with hot reload enabled

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"
CERT_DIR="./certificates"

# Print colored message
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Print section header
print_header() {
    echo ""
    print_message "${BLUE}" "========================================"
    print_message "${BLUE}" "$1"
    print_message "${BLUE}" "========================================"
    echo ""
}

# Check if .env file exists
check_env_file() {
    if [ ! -f "${ENV_FILE}" ]; then
        print_message "${YELLOW}" "Warning: ${ENV_FILE} not found. Creating from .env.example..."
        if [ -f ".env.example" ]; then
            cp .env.example "${ENV_FILE}"
            print_message "${GREEN}" "Created ${ENV_FILE} from .env.example"
            print_message "${YELLOW}" "Please update ${ENV_FILE} with your settings"
        else
            print_message "${RED}" "Error: .env.example not found. Please create ${ENV_FILE} manually"
            exit 1
        fi
    fi
}

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_message "${RED}" "Error: Docker is not running. Please start Docker and try again."
        exit 1
    fi
}

# Generate SSL certificates if enabled and missing
check_certificates() {
    # Check if SSL is enabled in .env
    if grep -q "^SSL_ENABLED=true" "${ENV_FILE}" 2>/dev/null; then
        print_header "Checking SSL Certificates"

        if [ ! -f "${CERT_DIR}/cert.pem" ] || [ ! -f "${CERT_DIR}/key.pem" ]; then
            print_message "${YELLOW}" "SSL is enabled but certificates not found."
            print_message "${YELLOW}" "Generating self-signed certificates..."

            # Generate certificates
            if [ -x "./scripts/generate-certificates.sh" ]; then
                ./scripts/generate-certificates.sh
            else
                print_message "${YELLOW}" "Making certificate generation script executable..."
                chmod +x ./scripts/generate-certificates.sh
                ./scripts/generate-certificates.sh
            fi

            print_message "${GREEN}" "Certificates generated successfully!"
        else
            print_message "${GREEN}" "SSL certificates found."
            print_message "${BLUE}" "  Certificate: ${CERT_DIR}/cert.pem"
            print_message "${BLUE}" "  Private Key: ${CERT_DIR}/key.pem"
        fi
        echo ""
    fi
}

# Start development environment
start_dev() {
    print_header "Starting Development Environment"

    check_env_file
    check_docker
    check_certificates

    print_message "${YELLOW}" "Starting services with hot reload enabled..."
    docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up --build

    # Note: The --build flag ensures images are rebuilt on code changes
    # For true hot reload, you may want to mount volumes in docker-compose.yml
}

# Start services in detached mode
start_dev_detached() {
    print_header "Starting Development Environment (Detached)"

    check_env_file
    check_docker
    check_certificates

    print_message "${YELLOW}" "Starting services in background..."
    docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d --build

    print_message "${GREEN}" "Services started in background!"
    echo ""

    # Check if SSL is enabled
    local ssl_enabled=false
    if grep -q "^SSL_ENABLED=true" "${ENV_FILE}" 2>/dev/null; then
        ssl_enabled=true
    fi

    print_message "${BLUE}" "View logs with: ./scripts/dev.sh logs"
    print_message "${BLUE}" "Stop services with: ./scripts/dev.sh stop"
    print_message "${BLUE}" "Service URLs:"

    if [ "$ssl_enabled" = true ]; then
        echo "  - Communication Server (HTTPS): https://localhost:8443"
        echo "  - Communication Server (HTTP):  http://localhost:8001"
        echo "  - MCP Broker:                   http://localhost:8000"
        echo "  - API Documentation (HTTPS):    https://localhost:8443/docs"
    else
        echo "  - Communication Server: http://localhost:8001"
        echo "  - MCP Broker:            http://localhost:8000"
        echo "  - API Documentation:     http://localhost:8001/docs"
    fi
}

# Stop development environment
stop_dev() {
    print_header "Stopping Development Environment"

    check_docker

    print_message "${YELLOW}" "Stopping services..."
    docker-compose -f "${COMPOSE_FILE}" down

    print_message "${GREEN}" "Services stopped!"
}

# Show logs
show_logs() {
    check_docker

    if [ -z "$1" ]; then
        print_header "All Service Logs"
        docker-compose -f "${COMPOSE_FILE}" logs -f --tail=100
    else
        print_header "$1 Logs"
        docker-compose -f "${COMPOSE_FILE}" logs -f --tail=100 "$1"
    fi
}

# Run tests
run_tests() {
    print_header "Running Tests"

    check_docker

    print_message "${YELLOW}" "Running tests in Docker container..."

    docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" run --rm \
        "${SERVICE_COMM_SERVER}" python -m pytest tests/ -v --cov=src

    print_message "${GREEN}" "Tests completed!"
}

# Format code
format_code() {
    print_header "Formatting Code"

    print_message "${YELLOW}" "Running ruff formatter and linter..."

    # Check if uv is available
    if command -v uv &> /dev/null; then
        # Format with ruff using uv
        uv run ruff check --fix src/ tests/
        uv run ruff format src/ tests/
    else
        # Fallback to direct ruff command
        ruff check --fix src/ tests/
        ruff format src/ tests/
    fi

    print_message "${GREEN}" "Code formatted!"
}

# Type check
type_check() {
    print_header "Type Checking"

    print_message "${YELLOW}" "Running mypy..."

    # Check if uv is available
    if command -v uv &> /dev/null; then
        uv run mypy src/
    else
        mypy src/
    fi

    print_message "${GREEN}" "Type check completed!"
}

# Rebuild services
rebuild() {
    print_header "Rebuilding Services"

    check_docker

    print_message "${YELLOW}" "Rebuilding Docker images..."
    docker-compose -f "${COMPOSE_FILE}" build --no-cache

    print_message "${GREEN}" "Services rebuilt!"
}

# Generate SSL certificates
generate_certs() {
    print_header "Generating SSL Certificates"

    if [ -x "./scripts/generate-certificates.sh" ]; then
        ./scripts/generate-certificates.sh
    else
        print_message "${YELLOW}" "Making certificate generation script executable..."
        chmod +x ./scripts/generate-certificates.sh
        ./scripts/generate-certificates.sh
    fi
}

# Enable SSL
enable_ssl() {
    print_header "Enabling SSL/TLS"

    check_env_file

    # Check if SSL_ENABLED is already true
    if grep -q "^SSL_ENABLED=true" "${ENV_FILE}"; then
        print_message "${YELLOW}" "SSL is already enabled in .env"
    else
        # Update or add SSL_ENABLED=true
        if grep -q "^SSL_ENABLED=" "${ENV_FILE}"; then
            sed -i.bak 's/^SSL_ENABLED=.*/SSL_ENABLED=true/' "${ENV_FILE}"
            rm -f "${ENV_FILE}.bak"
        else
            echo "" >> "${ENV_FILE}"
            echo "# SSL/TLS enabled via dev.sh" >> "${ENV_FILE}"
            echo "SSL_ENABLED=true" >> "${ENV_FILE}"
        fi
        print_message "${GREEN}" "SSL enabled in .env"
    fi

    # Generate certificates if needed
    check_certificates

    print_message "${GREEN}" "SSL/TLS is now enabled!"
    echo ""
    print_message "${BLUE}" "Next steps:"
    echo "  1. Restart services: ./scripts/dev.sh restart"
    echo "  2. Access via HTTPS: https://localhost:8443"
}

# Disable SSL
disable_ssl() {
    print_header "Disabling SSL/TLS"

    check_env_file

    # Update SSL_ENABLED to false
    if grep -q "^SSL_ENABLED=" "${ENV_FILE}"; then
        sed -i.bak 's/^SSL_ENABLED=.*/SSL_ENABLED=false/' "${ENV_FILE}"
        rm -f "${ENV_FILE}.bak"
    fi

    print_message "${GREEN}" "SSL/TLS is now disabled!"
    echo ""
    print_message "${BLUE}" "Next steps:"
    echo "  1. Restart services: ./scripts/dev.sh restart"
    echo "  2. Access via HTTP: http://localhost:8001"
}

# Clean up
cleanup() {
    print_header "Cleaning Up"

    check_docker

    print_message "${YELLOW}" "Stopping and removing containers..."
    docker-compose -f "${COMPOSE_FILE}" down -v

    print_message "${YELLOW}" "Removing dangling images..."
    docker image prune -f

    print_message "${GREEN}" "Cleanup completed!"
}

# Show usage
show_usage() {
    cat << EOF
AI Agent Communication System - Development Script

Usage: $0 <command> [options]

Commands:
    up              Start all services (attached)
    start           Start all services (detached)
    stop            Stop all services
    logs [service]  Show logs for all services or specific service
    test            Run tests
    format          Format code with ruff and black
    typecheck       Run mypy type checking
    rebuild         Rebuild Docker images
    cleanup         Stop services and remove volumes

SSL/TLS Commands:
    certs           Generate self-signed SSL certificates
    ssl-enable      Enable SSL/TLS (generates certificates if needed)
    ssl-disable     Disable SSL/TLS

Services:
    postgres            PostgreSQL database
    redis               Redis cache (optional)
    communication-server Communication API server
    mcp-broker          MCP broker server

Examples:
    $0 up                       # Start all services with logs
    $0 start                    # Start all services in background
    $0 logs mcp-broker          # Show MCP broker logs
    $0 ssl-enable               # Enable SSL/TLS
    $0 test                     # Run tests
    $0 format                   # Format code

Environment:
    Requires .env file (will create from .env.example if missing)

Note:
    This script is for development use only.
    For production deployment, use scripts/deploy.sh

EOF
}

# Main script logic
main() {
    local command=$1
    shift || true

    case "${command}" in
        up)
            start_dev
            ;;
        start)
            start_dev_detached
            ;;
        stop)
            stop_dev
            ;;
        restart)
            stop_dev
            start_dev_detached
            ;;
        logs)
            show_logs "$1"
            ;;
        test)
            run_tests
            ;;
        format)
            format_code
            ;;
        typecheck)
            type_check
            ;;
        rebuild)
            rebuild
            ;;
        cleanup)
            cleanup
            ;;
        certs)
            generate_certs
            ;;
        ssl-enable)
            enable_ssl
            ;;
        ssl-disable)
            disable_ssl
            ;;
        *)
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"

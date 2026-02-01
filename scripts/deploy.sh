#!/bin/bash
# AI Agent Communication System - Deployment Script
# Supports start, stop, restart, status, logs, and health check commands

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="agent-comm"
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"
CERT_DIR="./certificates"

# Service names
SERVICE_POSTGRES="postgres"
SERVICE_REDIS="redis"
SERVICE_COMM_SERVER="communication-server"
SERVICE_MCP_BROKER="mcp-broker"

# Health check endpoints
HEALTH_COMM_SERVER="http://localhost:8001/health"
HEALTH_COMM_SERVER_SSL="https://localhost:8443/health"
HEALTH_MCP_BROKER="http://localhost:8000/health"

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

# Check SSL certificates if SSL is enabled
check_certificates() {
    if grep -q "^SSL_ENABLED=true" "${ENV_FILE}" 2>/dev/null; then
        if [ ! -f "${CERT_DIR}/cert.pem" ] || [ ! -f "${CERT_DIR}/key.pem" ]; then
            print_message "${YELLOW}" "SSL is enabled but certificates not found."
            print_message "${YELLOW}" "Generating self-signed certificates..."

            if [ -x "./scripts/generate-certificates.sh" ]; then
                ./scripts/generate-certificates.sh
            else
                chmod +x ./scripts/generate-certificates.sh
                ./scripts/generate-certificates.sh
            fi

            print_message "${GREEN}" "Certificates generated successfully!"
        fi
    fi
}

# Get health check URL based on SSL configuration
get_health_check_url() {
    if grep -q "^SSL_ENABLED=true" "${ENV_FILE}" 2>/dev/null; then
        # For now, use HTTP for health checks even with SSL enabled
        # Change to SSL endpoint when SSL is fully configured
        echo "${HEALTH_COMM_SERVER}"
    else
        echo "${HEALTH_COMM_SERVER}"
    fi
}

# Wait for service to be healthy
wait_for_service() {
    local service_name=$1
    local health_url=$2
    local max_attempts=30
    local attempt=1

    print_message "${YELLOW}" "Waiting for ${service_name} to be healthy..."

    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "${health_url}" > /dev/null 2>&1; then
            print_message "${GREEN}" "${service_name} is healthy!"
            return 0
        fi
        sleep 2
        attempt=$((attempt + 1))
        echo -n "."
    done

    echo ""
    print_message "${RED}" "Timeout waiting for ${service_name} to be healthy"
    return 1
}

# Start services
start_services() {
    print_header "Starting Services"

    check_env_file
    check_docker
    check_certificates

    print_message "${YELLOW}" "Building and starting Docker containers..."
    docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d

    print_message "${GREEN}" "Services started successfully!"
    echo ""

    # Determine health check URL
    local health_url=$(get_health_check_url)

    # Wait for services to be healthy
    wait_for_service "Communication Server" "${health_url}"
    wait_for_service "MCP Broker" "${HEALTH_MCP_BROKER}"

    print_message "${GREEN}" "All services are healthy!"
    echo ""

    # Print service URLs
    print_service_urls
}

# Print service URLs
print_service_urls() {
    print_message "${BLUE}" "Service URLs:"

    # Check if SSL is enabled
    if grep -q "^SSL_ENABLED=true" "${ENV_FILE}" 2>/dev/null; then
        echo "  - Communication Server (HTTPS): https://localhost:8443"
        echo "  - Communication Server (HTTP):  http://localhost:8001"
        echo "  - MCP Broker:                   http://localhost:8000"
        echo "  - API Documentation (HTTPS):    https://localhost:8443/docs"
        echo ""
        print_message "${YELLOW}" "Note: Self-signed certificate warning is expected in development."
        print_message "${YELLOW}" "      Trust the certificate to remove browser warnings."
    else
        echo "  - Communication Server: http://localhost:8001"
        echo "  - MCP Broker:            http://localhost:8000"
        echo "  - API Documentation:     http://localhost:8001/docs"
    fi
}

# Stop services
stop_services() {
    print_header "Stopping Services"

    check_docker

    print_message "${YELLOW}" "Stopping Docker containers..."
    docker-compose -f "${COMPOSE_FILE}" down

    print_message "${GREEN}" "Services stopped successfully!"
}

# Restart services
restart_services() {
    print_header "Restarting Services"

    stop_services
    sleep 2
    start_services
}

# Show service status
show_status() {
    print_header "Service Status"

    check_docker

    docker-compose -f "${COMPOSE_FILE}" ps

    echo ""
    print_message "${BLUE}" "Health Checks:"
    echo ""

    # Check Communication Server
    local health_url=$(get_health_check_url)
    if curl -f -s "${health_url}" > /dev/null 2>&1; then
        print_message "${GREEN}" "Communication Server: Healthy"
    else
        print_message "${RED}" "Communication Server: Unhealthy"
    fi

    # Check MCP Broker
    if curl -f -s "${HEALTH_MCP_BROKER}" > /dev/null 2>&1; then
        print_message "${GREEN}" "MCP Broker: Healthy"
    else
        print_message "${RED}" "MCP Broker: Unhealthy"
    fi
}

# Show service logs
show_logs() {
    local service=$1

    check_docker

    if [ -z "${service}" ]; then
        print_header "All Service Logs"
        docker-compose -f "${COMPOSE_FILE}" logs -f --tail=100
    else
        print_header "${service} Logs"
        docker-compose -f "${COMPOSE_FILE}" logs -f --tail=100 "${service}"
    fi
}

# Run database migrations
run_migrations() {
    print_header "Running Database Migrations"

    check_env_file
    check_docker

    print_message "${YELLOW}" "Running migrations on Communication Server..."
    docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" exec -T "${SERVICE_COMM_SERVER}" \
        python3 -c "
import asyncio
from agent_comm_core.db.database import init_db
from communication_server.dependencies import get_database_url

async def run_migrations():
    database_url = get_database_url()
    await init_db(database_url=database_url, drop_all=False)
    print('Migrations completed successfully!')

asyncio.run(run_migrations())
"

    print_message "${GREEN}" "Migrations completed!"
}

# Health check for all services
health_check() {
    print_header "Health Check"

    local all_healthy=true

    # Check Communication Server
    print_message "${YELLOW}" "Checking Communication Server..."
    local health_url=$(get_health_check_url)
    if curl -f -s "${health_url}" > /dev/null 2>&1; then
        response=$(curl -s "${health_url}")
        print_message "${GREEN}" "Communication Server: Healthy"
        echo "  Response: ${response}"
    else
        print_message "${RED}" "Communication Server: Unhealthy"
        all_healthy=false
    fi

    echo ""

    # Check MCP Broker
    print_message "${YELLOW}" "Checking MCP Broker..."
    if curl -f -s "${HEALTH_MCP_BROKER}" > /dev/null 2>&1; then
        response=$(curl -s "${HEALTH_MCP_BROKER}")
        print_message "${GREEN}" "MCP Broker: Healthy"
        echo "  Response: ${response}"
    else
        print_message "${RED}" "MCP Broker: Unhealthy"
        all_healthy=false
    fi

    echo ""

    if [ "${all_healthy}" = true ]; then
        print_message "${GREEN}" "All services are healthy!"
        return 0
    else
        print_message "${RED}" "Some services are unhealthy!"
        return 1
    fi
}

# Build images
build_images() {
    print_header "Building Docker Images"

    check_docker

    print_message "${YELLOW}" "Building Docker images..."
    docker-compose -f "${COMPOSE_FILE}" build

    print_message "${GREEN}" "Docker images built successfully!"
}

# Clean up containers and volumes
cleanup() {
    print_header "Cleaning Up"

    check_docker

    print_message "${YELLOW}" "Stopping and removing containers..."
    docker-compose -f "${COMPOSE_FILE}" down -v

    print_message "${YELLOW}" "Removing dangling images..."
    docker image prune -f

    print_message "${GREEN}" "Cleanup completed!"
}

# Generate SSL certificates
generate_certs() {
    print_header "Generating SSL Certificates"

    if [ -x "./scripts/generate-certificates.sh" ]; then
        ./scripts/generate-certificates.sh
    else
        chmod +x ./scripts/generate-certificates.sh
        ./scripts/generate-certificates.sh
    fi
}

# Enable SSL
enable_ssl() {
    print_header "Enabling SSL/TLS for Production"

    check_env_file

    print_message "${YELLOW}" "For production, use a valid SSL certificate from Let's Encrypt or a commercial CA."
    print_message "${YELLOW}" "Self-signed certificates are for development only."
    echo ""

    # Update .env file
    if grep -q "^SSL_ENABLED=" "${ENV_FILE}"; then
        sed -i.bak 's/^SSL_ENABLED=.*/SSL_ENABLED=true/' "${ENV_FILE}"
        rm -f "${ENV_FILE}.bak"
    else
        echo "" >> "${ENV_FILE}"
        echo "SSL_ENABLED=true" >> "${ENV_FILE}"
    fi

    print_message "${GREEN}" "SSL enabled in configuration."
    echo ""
    print_message "${BLUE}" "To use self-signed certificates for development:"
    echo "  $0 certs"
    echo "  $0 restart"
    echo ""
    print_message "${BLUE}" "To use production certificates:"
    echo "  1. Place certificates at ${CERT_DIR}/cert.pem and ${CERT_DIR}/key.pem"
    echo "  2. Update SSL_CERT_PATH and SSL_KEY_PATH in .env"
    echo "  3. Run: $0 restart"
}

# Show usage
show_usage() {
    cat << EOF
AI Agent Communication System - Deployment Script

Usage: $0 <command> [options]

Commands:
    start           Start all services
    stop            Stop all services
    restart         Restart all services
    status          Show service status
    logs [service]  Show logs for all services or specific service
    health          Run health check on all services
    migrate         Run database migrations
    build           Build Docker images
    cleanup         Stop services and remove volumes

SSL/TLS Commands:
    certs           Generate self-signed SSL certificates
    ssl-enable      Enable SSL/TLS configuration

Services:
    postgres            PostgreSQL database
    redis               Redis cache (optional)
    communication-server Communication API server
    mcp-broker          MCP broker server

Examples:
    $0 start                    # Start all services
    $0 logs mcp-broker          # Show MCP broker logs
    $0 health                   # Check service health
    $0 migrate                  # Run database migrations
    $0 ssl-enable               # Enable SSL/TLS

Environment:
    Requires .env file (will create from .env.example if missing)

EOF
}

# Main script logic
main() {
    local command=$1
    shift || true

    case "${command}" in
        start)
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "$1"
            ;;
        health)
            health_check
            ;;
        migrate)
            run_migrations
            ;;
        build)
            build_images
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
        *)
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"

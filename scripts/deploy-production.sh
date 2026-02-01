#!/bin/bash
# Production Deployment Script for Communication Server on OCI
# Deploys Communication Server on port 8000 at oci-ajou-ec2.fcoinfup.com

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVICE_NAME="agent-comm"
SERVICE_PORT=8000
DOMAIN="oci-ajou-ec2.fcoinfup.com"
APP_DIR="/home/ubuntu/agent_com"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
LOG_DIR="/var/log/agent-comm"
CONFIG_FILE="config.production.json"

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

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_message "${RED}" "Error: This script must be run as root (use sudo)"
        exit 1
    fi
}

# Check if application directory exists
check_app_dir() {
    if [ ! -d "${APP_DIR}" ]; then
        print_message "${RED}" "Error: Application directory not found: ${APP_DIR}"
        exit 1
    fi
}

# Create log directory
create_log_dir() {
    print_header "Creating Log Directory"

    if [ ! -d "${LOG_DIR}" ]; then
        mkdir -p "${LOG_DIR}"
        chown ubuntu:ubuntu "${LOG_DIR}"
        print_message "${GREEN}" "Log directory created: ${LOG_DIR}"
    else
        print_message "${YELLOW}" "Log directory already exists: ${LOG_DIR}"
    fi
}

# Generate production secrets
generate_secrets() {
    print_header "Generating Production Secrets"

    # Generate JWT secret
    JWT_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')

    # Generate API token secret
    API_TOKEN_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')

    print_message "${GREEN}" "Secrets generated successfully!"
    print_message "${YELLOW}" "JWT_SECRET=${JWT_SECRET:0:16}..."
    print_message "${YELLOW}" "API_TOKEN_SECRET=${API_TOKEN_SECRET:0:16}..."

    # Update config file with secrets
    cd "${APP_DIR}"
    sed -i.bak "s/CHANGE_ME_IN_PRODUCTION_USE_32_CHAR_MIN/${JWT_SECRET}/g" "${CONFIG_FILE}"
    sed -i.bak "s/CHANGE_ME_IN_PRODUCTION_USE_32_CHAR_MIN/${API_TOKEN_SECRET}/g" "${CONFIG_FILE}"
    rm -f "${CONFIG_FILE}.bak"

    print_message "${GREEN}" "Production config updated with secrets"
}

# Install systemd service
install_service() {
    print_header "Installing Systemd Service"

    # Copy service file
    cp "${APP_DIR}/scripts/agent-comm-port8000.service" "${SERVICE_FILE}"

    # Reload systemd
    systemctl daemon-reload

    print_message "${GREEN}" "Service file installed: ${SERVICE_FILE}"
}

# Enable and start service
start_service() {
    print_header "Starting Service"

    # Enable service to start on boot
    systemctl enable "${SERVICE_NAME}"

    # Start service
    systemctl start "${SERVICE_NAME}"

    # Wait a moment for service to start
    sleep 3

    # Check service status
    if systemctl is-active --quiet "${SERVICE_NAME}"; then
        print_message "${GREEN}" "Service started successfully!"
    else
        print_message "${RED}" "Service failed to start!"
        print_message "${YELLOW}" "Check status with: sudo systemctl status ${SERVICE_NAME}"
        print_message "${YELLOW}" "Check logs with: sudo journalctl -u ${SERVICE_NAME} -n 50"
        exit 1
    fi
}

# Verify deployment
verify_deployment() {
    print_header "Verifying Deployment"

    # Check service status
    print_message "${YELLOW}" "Service status:"
    systemctl status "${SERVICE_NAME}" --no-pager -l

    echo ""

    # Check health endpoint
    print_message "${YELLOW}" "Checking health endpoint..."
    if curl -f -s "http://localhost:${SERVICE_PORT}/health" > /dev/null; then
        print_message "${GREEN}" "Health check passed!"
        curl -s "http://localhost:${SERVICE_PORT}/health" | jq .
    else
        print_message "${RED}" "Health check failed!"
        exit 1
    fi
}

# Configure firewall
configure_firewall() {
    print_header "Configuring Firewall"

    # Check if ufw is installed
    if command -v ufw &> /dev/null; then
        print_message "${YELLOW}" "Configuring ufw..."
        ufw allow "${SERVICE_PORT}/tcp" || true
        print_message "${GREEN}" "Firewall configured for port ${SERVICE_PORT}"
    elif command -v firewall-cmd &> /dev/null; then
        print_message "${YELLOW}" "Configuring firewalld..."
        firewall-cmd --permanent --add-port="${SERVICE_PORT}/tcp" || true
        firewall-cmd --reload || true
        print_message "${GREEN}" "Firewall configured for port ${SERVICE_PORT}"
    else
        print_message "${YELLOW}" "No firewall detected, skipping..."
    fi
}

# Print deployment summary
print_summary() {
    print_header "Deployment Summary"

    print_message "${GREEN}" "Communication Server deployed successfully!"
    echo ""
    print_message "${BLUE}" "Service Details:"
    echo "  - Service Name: ${SERVICE_NAME}"
    echo "  - Port: ${SERVICE_PORT}"
    echo "  - Domain: ${DOMAIN}"
    echo "  - Health URL: http://${DOMAIN}:${SERVICE_PORT}/health"
    echo ""
    print_message "${BLUE}" "Management Commands:"
    echo "  - Start service:   sudo systemctl start ${SERVICE_NAME}"
    echo "  - Stop service:    sudo systemctl stop ${SERVICE_NAME}"
    echo "  - Restart service: sudo systemctl restart ${SERVICE_NAME}"
    echo "  - Check status:    sudo systemctl status ${SERVICE_NAME}"
    echo "  - View logs:       sudo journalctl -u ${SERVICE_NAME} -f"
    echo "  - View app logs:   tail -f ${LOG_DIR}/output.log"
    echo ""
    print_message "${BLUE}" "Application Logs:"
    echo "  - Output:  ${LOG_DIR}/output.log"
    echo "  - Error:   ${LOG_DIR}/error.log"
    echo ""
}

# Main deployment flow
main() {
    print_header "Communication Server Production Deployment"
    print_message "${YELLOW}" "Deploying to ${DOMAIN}:${SERVICE_PORT}"

    # Pre-flight checks
    check_root
    check_app_dir

    # Deployment steps
    create_log_dir
    generate_secrets
    install_service
    configure_firewall
    start_service
    verify_deployment

    # Print summary
    print_summary
}

# Run main function
main "$@"

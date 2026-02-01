#!/bin/bash
# Remote Deployment Script for Communication Server
# Run this from your local machine to deploy to the OCI server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVER_USER="ubuntu"
SERVER_HOST="oci-ajou-ec2"
SERVER_PORT="22"
APP_DIR="/home/ubuntu/works/agent_com"
SERVICE_NAME="agent-comm"
SERVICE_PORT=8000

# SSH command wrapper
ssh_cmd() {
    ssh -p "${SERVER_PORT}" "${SERVER_USER}@${SERVER_HOST}" "$1"
}

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

# Check SSH connectivity
check_ssh() {
    print_header "Checking SSH Connectivity"

    if ssh_cmd "echo 'SSH connection successful'" > /dev/null 2>&1; then
        print_message "${GREEN}" "SSH connection to ${SERVER_HOST} successful"
    else
        print_message "${RED}" "Cannot connect to ${SERVER_HOST}"
        print_message "${YELLOW}" "Please check:"
        echo "  - Server is running"
        echo "  - SSH key is configured"
        echo "  - Network connectivity"
        exit 1
    fi
}

# Check prerequisites on remote server
check_prerequisites() {
    print_header "Checking Prerequisites"

    print_message "${YELLOW}" "Checking Python 3..."
    if ssh_cmd "python3 --version" > /dev/null 2>&1; then
        print_message "${GREEN}" "Python 3 is installed"
    else
        print_message "${RED}" "Python 3 is not installed"
        exit 1
    fi

    print_message "${YELLOW}" "Checking uv package manager..."
    if ssh_cmd "uv --version" > /dev/null 2>&1; then
        print_message "${GREEN}" "uv is installed"
    else
        print_message "${RED}" "uv is not installed"
        print_message "${YELLOW}" "Install uv with: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi

    print_message "${YELLOW}" "Checking PostgreSQL..."
    if ssh_cmd "systemctl is-active postgresql" > /dev/null 2>&1; then
        print_message "${GREEN}" "PostgreSQL is running"
    else
        print_message "${YELLOW}" "PostgreSQL is not running (will start during deployment)"
    fi
}

# Deploy to remote server
deploy_remote() {
    print_header "Deploying to Remote Server"

    print_message "${YELLOW}" "Running production deployment script on remote server..."

    ssh_cmd "cd ${APP_DIR} && sudo ./scripts/deploy-production.sh"

    if [ $? -eq 0 ]; then
        print_message "${GREEN}" "Deployment completed successfully!"
    else
        print_message "${RED}" "Deployment failed!"
        exit 1
    fi
}

# Verify deployment
verify_deployment() {
    print_header "Verifying Deployment"

    print_message "${YELLOW}" "Running verification script on remote server..."

    ssh_cmd "cd ${APP_DIR} && sudo ./scripts/verify-deployment.sh"

    if [ $? -eq 0 ]; then
        print_message "${GREEN}" "Verification passed!"
    else
        print_message "${YELLOW}" "Verification found some issues (see output above)"
    fi
}

# Test health endpoint from local machine
test_health() {
    print_header "Testing Health Endpoint from Local Machine"

    print_message "${YELLOW}" "Testing: http://${SERVER_HOST}:${SERVICE_PORT}/health"

    if curl -f -s "http://${SERVER_HOST}:${SERVICE_PORT}/health" > /dev/null; then
        local health_response=$(curl -s "http://${SERVER_HOST}:${SERVICE_PORT}/health")
        print_message "${GREEN}" "Health check successful!"
        print_message "${BLUE}" "Response: ${health_response}"
    else
        print_message "${RED}" "Health check failed from local machine"
        print_message "${YELLOW}" "The service may be running but not accessible from external network"
        print_message "${YELLOW}" "Check OCI Security List settings"
    fi
}

# Print deployment summary
print_summary() {
    print_header "Deployment Summary"

    print_message "${GREEN}" "Communication Server deployed to ${SERVER_HOST}:${SERVICE_PORT}"
    echo ""
    print_message "${BLUE}" "Service Details:"
    echo "  - Server: ${SERVER_HOST}"
    echo "  - Port: ${SERVICE_PORT}"
    echo "  - Service: ${SERVICE_NAME}"
    echo ""
    print_message "${BLUE}" "URLs:"
    echo "  - Health:  http://${SERVER_HOST}:${SERVICE_PORT}/health"
    echo "  - API:     http://${SERVER_HOST}:${SERVICE_PORT}/api/v1"
    echo "  - Docs:    http://${SERVER_HOST}:${SERVICE_PORT}/docs"
    echo ""
    print_message "${BLUE}" "Remote Commands:"
    echo "  - SSH:        ssh ${SERVER_USER}@${SERVER_HOST}"
    echo "  - Status:     ssh ${SERVER_USER}@${SERVER_HOST} 'sudo systemctl status ${SERVICE_NAME}'"
    echo "  - Logs:       ssh ${SERVER_USER}@${SERVER_HOST} 'sudo journalctl -u ${SERVICE_NAME} -f'"
    echo "  - Restart:    ssh ${SERVER_USER}@${SERVER_HOST} 'sudo systemctl restart ${SERVICE_NAME}'"
    echo ""
}

# Main deployment flow
main() {
    print_header "Remote Deployment: Communication Server"
    print_message "${YELLOW}" "Target: ${SERVER_USER}@${SERVER_HOST}"

    # Check local connectivity
    check_ssh

    # Check prerequisites on remote
    check_prerequisites

    # Deploy to remote
    deploy_remote

    # Verify deployment
    verify_deployment

    # Test from local machine
    test_health

    # Print summary
    print_summary
}

# Handle command line arguments
case "${1:-deploy}" in
    deploy)
        main
        ;;
    verify)
        verify_deployment
        ;;
    health)
        test_health
        ;;
    *)
        echo "Usage: $0 [deploy|verify|health]"
        echo "  deploy  - Full deployment (default)"
        echo "  verify  - Run verification on remote server"
        echo "  health  - Test health endpoint from local machine"
        exit 1
        ;;
esac

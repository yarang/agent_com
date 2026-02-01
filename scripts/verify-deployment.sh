#!/bin/bash
# Verification script for Communication Server deployment
# Checks service health, connectivity, and configuration

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
LOG_DIR="/var/log/agent-comm"

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

# Check function
check() {
    local description=$1
    local command=$2
    local expected=$3

    print_message "${YELLOW}" "Checking: ${description}"

    if eval "${command}" > /dev/null 2>&1; then
        print_message "${GREEN}" "  PASS: ${description}"
        return 0
    else
        print_message "${RED}" "  FAIL: ${description}"
        return 1
    fi
}

# Main verification
main() {
    print_header "Communication Server Deployment Verification"
    print_message "${YELLOW}" "Target: ${DOMAIN}:${SERVICE_PORT}"

    local all_passed=true

    # Check systemd service
    print_header "1. Systemd Service Status"

    if systemctl is-active --quiet "${SERVICE_NAME}"; then
        print_message "${GREEN}" "Service is running"
    else
        print_message "${RED}" "Service is NOT running"
        all_passed=false
    fi

    if systemctl is-enabled --quiet "${SERVICE_NAME}"; then
        print_message "${GREEN}" "Service is enabled for auto-start"
    else
        print_message "${RED}" "Service is NOT enabled for auto-start"
        all_passed=false
    fi

    # Check port binding
    print_header "2. Network Configuration"

    if check "Port ${SERVICE_PORT} is listening" "ss -tuln | grep -q ':${SERVICE_PORT}'"; then
        : # pass
    else
        all_passed=false
    fi

    # Check local health endpoint
    print_header "3. Health Endpoints"

    if check "Local health endpoint" "curl -f -s http://localhost:${SERVICE_PORT}/health"; then
        local health_response=$(curl -s "http://localhost:${SERVICE_PORT}/health")
        print_message "${GREEN}" "  Response: ${health_response}"
    else
        all_passed=false
    fi

    # Check API docs endpoint
    if check "API docs endpoint" "curl -f -s http://localhost:${SERVICE_PORT}/docs"; then
        : # pass
    else
        all_passed=false
    fi

    # Check log directory
    print_header "4. Logging"

    if [ -d "${LOG_DIR}" ]; then
        print_message "${GREEN}" "Log directory exists: ${LOG_DIR}"

        if [ -f "${LOG_DIR}/output.log" ]; then
            print_message "${GREEN}" "Output log file exists"
        else
            print_message "${YELLOW}" "Output log file not found yet"
        fi

        if [ -f "${LOG_DIR}/error.log" ]; then
            print_message "${GREEN}" "Error log file exists"
        else
            print_message "${YELLOW}" "Error log file not found yet"
        fi
    else
        print_message "${RED}" "Log directory not found: ${LOG_DIR}"
        all_passed=false
    fi

    # Check firewall
    print_header "5. Firewall Configuration"

    if command -v ufw &> /dev/null; then
        if ufw status | grep -q "${SERVICE_PORT}/tcp.*ALLOW"; then
            print_message "${GREEN}" "UFW rule exists for port ${SERVICE_PORT}"
        else
            print_message "${YELLOW}" "UFW rule not found for port ${SERVICE_PORT}"
        fi
    elif command -v firewall-cmd &> /dev/null; then
        if firewall-cmd --list-ports | grep -q "${SERVICE_PORT}/tcp"; then
            print_message "${GREEN}" "Firewalld rule exists for port ${SERVICE_PORT}"
        else
            print_message "${YELLOW}" "Firewalld rule not found for port ${SERVICE_PORT}"
        fi
    else
        print_message "${YELLOW}" "No firewall detected"
    fi

    # Summary
    print_header "Verification Summary"

    if [ "${all_passed}" = true ]; then
        print_message "${GREEN}" "All critical checks passed!"
        echo ""
        print_message "${BLUE}" "Service URL: http://${DOMAIN}:${SERVICE_PORT}"
        print_message "${BLUE}" "Health URL: http://${DOMAIN}:${SERVICE_PORT}/health"
        print_message "${BLUE}" "API Docs:  http://${DOMAIN}:${SERVICE_PORT}/docs"
        echo ""
        return 0
    else
        print_message "${RED}" "Some checks failed. Please review the output above."
        echo ""
        print_message "${YELLOW}" "Troubleshooting commands:"
        echo "  - Check status:    sudo systemctl status ${SERVICE_NAME}"
        echo "  - View logs:       sudo journalctl -u ${SERVICE_NAME} -n 50"
        echo "  - View app logs:   tail -f ${LOG_DIR}/error.log"
        echo "  - Restart service: sudo systemctl restart ${SERVICE_NAME}"
        echo ""
        return 1
    fi
}

# Run main function
main "$@"

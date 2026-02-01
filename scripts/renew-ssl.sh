#!/bin/bash
# Auto-renewal script for SSL certificates
#
# This script renews Let's Encrypt SSL certificates and restarts services.
# It is typically called by cron twice daily.
#
# Usage:
#   ./scripts/renew-ssl.sh
#
# Environment Variables:
#   DOMAIN              - Domain name (required)
#   CERT_DIR            - Certificate directory (default: ./certificates)
#   RESTART_DOCKER      - Set to "true" to restart docker services
#   RESTART_SYSTEMD     - Set to "true" to restart systemd service
#
# Example:
#   DOMAIN=example.com RESTART_DOCKER=true ./scripts/renew-ssl.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
DOMAIN="${DOMAIN:-}"
CERT_DIR="${CERT_DIR:-${PROJECT_ROOT}/certificates}"
RESTART_DOCKER="${RESTART_DOCKER:-false}"
RESTART_SYSTEMD="${RESTART_SYSTEMD:-false}"
DRY_RUN="${DRY_RUN:-false}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN="true"
            shift
            ;;
        --domain)
            DOMAIN="$2"
            shift 2
            ;;
        --docker)
            RESTART_DOCKER="true"
            shift
            ;;
        --systemd)
            RESTART_SYSTEMD="true"
            shift
            ;;
        -h|--help)
            cat << EOF
SSL Certificate Renewal Script

Usage: $0 [OPTIONS]

OPTIONS:
    --dry-run           Test renewal without making changes
    --domain DOMAIN     Domain name for certificates
    --docker            Restart docker services after renewal
    --systemd           Restart systemd service after renewal
    -h, --help          Show this help

ENVIRONMENT VARIABLES:
    DOMAIN              Domain name
    CERT_DIR            Certificate directory (default: ./certificates)
    RESTART_DOCKER      Restart docker services (true/false)
    RESTART_SYSTEMD     Restart systemd service (true/false)
    DRY_RUN             Test renewal without changes (true/false)

EXAMPLES:
    # Test renewal
    $0 --dry-run

    # Renew with docker restart
    DOMAIN=example.com RESTART_DOCKER=true $0

    # Renew with systemd restart
    DOMAIN=example.com RESTART_SYSTEMD=true $0

EOF
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Log function
log() {
    local level=$1
    shift
    local message="$@"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $message"
}

# Renew certificates
renew_certificates() {
    log "INFO" "Starting certificate renewal..."

    local certbot_cmd="sudo certbot renew"

    if [ "$DRY_RUN" = "true" ]; then
        certbot_cmd="$certbot_cmd --dry-run"
        log "INFO" "Running in dry-run mode (no changes will be made)"
    fi

    # Run certbot renew
    $certbot_cmd

    if [ $? -eq 0 ]; then
        log "INFO" "Certificate renewal completed successfully"
    else
        log "ERROR" "Certificate renewal failed"
        exit 1
    fi
}

# Copy certificates to project directory
copy_certificates() {
    if [ -z "$DOMAIN" ]; then
        log "WARN" "DOMAIN not set, skipping certificate copy"
        return 0
    fi

    log "INFO" "Copying certificates to $CERT_DIR..."

    # Create directory if it doesn't exist
    sudo mkdir -p "$CERT_DIR"

    # Copy certificates
    sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem "$CERT_DIR/cert.pem"
    sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem "$CERT_DIR/key.pem"

    # Set permissions
    sudo chown -R $(whoami):$(whoami) "$CERT_DIR"
    chmod 644 "$CERT_DIR/cert.pem"
    chmod 600 "$CERT_DIR/key.pem"

    log "INFO" "Certificates copied successfully"
}

# Restart docker services
restart_docker_services() {
    if [ "$RESTART_DOCKER" != "true" ]; then
        return 0
    fi

    log "INFO" "Restarting docker services..."

    cd "$PROJECT_ROOT"

    # Restart nginx and communication-server
    docker-compose restart nginx communication-server 2>/dev/null || {
        log "WARN" "Docker services not running or docker-compose not available"
    }

    log "INFO" "Docker services restarted"
}

# Restart systemd service
restart_systemd_service() {
    if [ "$RESTART_SYSTEMD" != "true" ]; then
        return 0
    fi

    log "INFO" "Restarting systemd service..."

    # Try to restart the agent-comm-server service
    if systemctl is-active --quiet agent-comm-server; then
        sudo systemctl restart agent-comm-server
        log "INFO" "Systemd service restarted"
    else
        log "WARN" "agent-comm-server service not running"
    fi
}

# Main execution
main() {
    echo -e "${GREEN}=== SSL Certificate Renewal ===${NC}"
    echo ""

    # Check if certbot is installed
    if ! command -v certbot &> /dev/null; then
        log "ERROR" "Certbot is not installed"
        exit 1
    fi

    # Renew certificates
    renew_certificates

    # Copy certificates if not in dry-run mode
    if [ "$DRY_RUN" != "true" ]; then
        copy_certificates
    fi

    # Restart services
    restart_docker_services
    restart_systemd_service

    echo ""
    echo -e "${GREEN}=== Renewal Complete ===${NC}"
}

# Run main function
main "$@"

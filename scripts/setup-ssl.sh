#!/bin/bash
set -e

# SSL Setup with Let's Encrypt using Certbot
# This script configures SSL certificates for production use

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
DOMAIN=""
EMAIL=""
STAGING="false"
PRODUCTION="false"
DOCKER="false"
NGINX="false"

# Help function
show_help() {
    cat << EOF
SSL Setup with Let's Encrypt (Certbot)

Usage: $0 [OPTIONS]

OPTIONS:
    -d, --domain DOMAIN        Domain name (required for production)
    -e, --email EMAIL          Email for Let's Encrypt notifications (required)
    -s, --staging              Use Let's Encrypt staging environment (for testing)
    -p, --production           Enable production mode
    --docker                   Setup for Docker/Docker Compose
    -n, --nginx                Setup with Nginx reverse proxy
    -h, --help                 Show this help

EXAMPLES:
    # Staging test (no rate limits)
    $0 --staging --domain example.com --email admin@example.com

    # Production with Docker
    $0 --production --docker --domain example.com --email admin@example.com

    # Production with Nginx
    $0 --production --nginx --domain example.com --email admin@example.com

NOTES:
    - Domain must have DNS pointing to this server
    - Port 80 must be open for HTTP-01 challenge
    - Staging mode is recommended for initial testing

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--domain)
            DOMAIN="$2"
            shift 2
            ;;
        -e|--email)
            EMAIL="$2"
            shift 2
            ;;
        -s|--staging)
            STAGING="true"
            shift
            ;;
        -p|--production)
            PRODUCTION="true"
            shift
            ;;
        --docker)
            DOCKER="true"
            shift
            ;;
        -n|--nginx)
            NGINX="true"
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Validation
if [ "$PRODUCTION" = "true" ]; then
    if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
        echo -e "${RED}Error: --domain and --email are required for production${NC}"
        show_help
        exit 1
    fi
fi

# Certificate directory
CERT_DIR="${PROJECT_ROOT}/certificates"
mkdir -p "$CERT_DIR"

echo -e "${GREEN}=== SSL Certificate Setup ===${NC}"

if [ "$PRODUCTION" = "true" ]; then
    echo "Domain: $DOMAIN"
    echo "Email: $EMAIL"
    echo "Mode: Production"
    echo ""

    # Check if certbot is installed
    if ! command -v certbot &> /dev/null; then
        echo -e "${YELLOW}Certbot not found. Installing...${NC}"
        sudo apt update
        sudo apt install -y certbot
    fi

    # Build certbot command
    CERTBOT_CMD="sudo certbot certonly"

    if [ "$STAGING" = "true" ]; then
        CERTBOT_CMD="$CERTBOT_CMD --staging"
        echo -e "${YELLOW}Using staging environment (no rate limits)${NC}"
    fi

    if [ "$NGINX" = "true" ]; then
        # For nginx, we'll use webroot after nginx is started
        CERTBOT_CMD="$CERTBOT_CMD --webroot -w /var/www/html"
    elif [ "$DOCKER" = "true" ]; then
        # For Docker, we'll use the certbot container
        echo -e "${GREEN}Setting up SSL for Docker environment...${NC}"

        # Update docker-compose.yml
        cat > "$PROJECT_ROOT/docker-compose.ssl.yml" << EOF
# SSL configuration for production
# Usage: docker-compose -f docker-compose.yml -f docker-compose.ssl.yml up

services:
  certbot:
    image: certbot/certbot:latest
    container_name: agent-comm-certbot
    volumes:
      - ./certificates:/etc/letsencrypt/live/${DOMAIN}
      - ./certbot-webroot:/var/www/html
    entrypoint: >
      sh -c "certonly --webroot
      --webroot-path=/var/www/html
      --email ${EMAIL}
      --agree-tos
      --no-eff-email
      -d ${DOMAIN}
      $( [ "$STAGING" = "true" ] && echo "--staging" || echo "--force-renewal" )
      && cp /etc/letsencrypt/live/${DOMAIN}/fullchain.pem /etc/letsencrypt/live/${DOMAIN}/cert.pem
      && cp /etc/letsencrypt/live/${DOMAIN}/privkey.pem /etc/letsencrypt/live/${DOMAIN}/key.pem"
    networks:
      - agent-comm-network
    profiles:
      - ssl

  nginx:
    image: nginx:alpine
    container_name: agent-comm-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certificates:/etc/letsencrypt/live/${DOMAIN}:ro
      - ./certbot-webroot:/var/www/html:ro
    depends_on:
      - communication-server
    networks:
      - agent-comm-network
    profiles:
      - ssl

networks:
  agent-comm-network:
    external: true

volumes:
  certbot-webroot:
EOF

        echo -e "${GREEN}Created docker-compose.ssl.yml${NC}"
        echo -e "${YELLOW}Run: docker-compose -f docker-compose.yml -f docker-compose.ssl.yml --profile ssl up${NC}"
        exit 0
    else
        # Standalone mode
        CERTBOT_CMD="$CERTBOT_CMD --standalone"
    fi

    # Add email and agreement
    CERTBOT_CMD="$CERTBOT_CMD --email $EMAIL --agree-tos --no-eff-email -d $DOMAIN"

    echo -e "${GREEN}Running certbot...${NC}"
    echo "Command: $CERTBOT_CMD"
    echo ""

    # Stop any service on port 80/443 if needed
    if lsof -Pi :80 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}Port 80 is in use. Attempting to free it...${NC}"
        sudo lsof -ti :80 | xargs sudo kill -9 2>/dev/null || true
    fi

    # Run certbot
    eval $CERTBOT_CMD

    # Copy certificates to project directory
    echo -e "${GREEN}Copying certificates to project...${NC}"
    sudo mkdir -p "$CERT_DIR"
    sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem "$CERT_DIR/cert.pem"
    sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem "$CERT_DIR/key.pem"
    sudo chown -R $USER:$USER "$CERT_DIR"
    chmod 644 "$CERT_DIR/cert.pem"
    chmod 600 "$CERT_DIR/key.pem"

    echo -e "${GREEN}Certificates installed to $CERT_DIR${NC}"

    # Setup auto-renewal
    echo -e "${GREEN}Setting up auto-renewal...${NC}"

    # Create renewal script
    cat > "$SCRIPT_DIR/renew-ssl.sh" << EOF
#!/bin/bash
# Auto-renewal script for SSL certificates

# Renew certificates
sudo certbot renew --quiet --deploy-hook "
    cp /etc/letsencrypt/live/${DOMAIN}/fullchain.pem ${CERT_DIR}/cert.pem
    cp /etc/letsencrypt/live/${DOMAIN}/privkey.pem ${CERT_DIR}/key.pem
    chown \$(whoami):\$(whoami) ${CERT_DIR}/*.pem
    chmod 644 ${CERT_DIR}/cert.pem
    chmod 600 ${CERT_DIR}/key.pem

    # Restart communication server
    # Uncomment if using systemd:
    # sudo systemctl restart agent-comm-server

    # Or restart docker:
    # docker-compose restart communication-server
"
EOF

    chmod +x "$SCRIPT_DIR/renew-ssl.sh"

    # Add to crontab
    (crontab -l 2>/dev/null | grep -v "renew-ssl.sh"; echo "0 0,12 * * * $SCRIPT_DIR/renew-ssl.sh >> /var/log/ssl-renewal.log 2>&1") | crontab -

    echo -e "${GREEN}Auto-renewal configured (runs at 00:00 and 12:00 daily)${NC}"

else
    echo -e "${YELLOW}Production mode not enabled. Usage:${NC}"
    show_help
    echo ""
    echo -e "${YELLOW}Quick start:${NC}"
    echo "  1. Test with staging: $0 --staging --domain yourdomain.com --email you@example.com"
    echo "  2. Production run: $0 --production --domain yourdomain.com --email you@example.com"
fi

echo ""
echo -e "${GREEN}=== Setup Complete ===${NC}"

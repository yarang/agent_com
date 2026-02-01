#!/bin/bash
# Generate self-signed SSL certificates for development
#
# Usage:
#   ./scripts/generate-certificates.sh [DOMAIN]
#
# Environment Variables:
#   CERT_DIR     - Certificate output directory (default: ./certificates)
#   DAYS_VALID   - Certificate validity period in days (default: 365)
#   DOMAIN       - Domain name for certificate (default: localhost)
#
# Examples:
#   ./scripts/generate-certificates.sh                    # Generate for localhost
#   ./scripts/generate-certificates.sh example.com        # Generate for example.com
#   CERT_DIR=/etc/ssl ./scripts/generate-certificates.sh  # Custom output directory

set -e

# Configuration with defaults
CERT_DIR="${CERT_DIR:-./certificates}"
DAYS_VALID="${DAYS_VALID:-365}"
DOMAIN="${1:-${DOMAIN:-localhost}}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored message
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Print header
print_header() {
    echo ""
    print_message "${BLUE}" "========================================"
    print_message "${BLUE}" "$1"
    print_message "${BLUE}" "========================================"
    echo ""
}

# Check if OpenSSL is installed
check_openssl() {
    if ! command -v openssl &> /dev/null; then
        print_message "${RED}" "Error: OpenSSL is not installed."
        print_message "${YELLOW}" "Install OpenSSL:"
        print_message "${YELLOW}" "  macOS:   brew install openssl"
        print_message "${YELLOW}" "  Ubuntu:  sudo apt-get install openssl"
        print_message "${YELLOW}" "  CentOS:  sudo yum install openssl"
        exit 1
    fi
}

# Create certificate directory
create_cert_directory() {
    if [ ! -d "$CERT_DIR" ]; then
        mkdir -p "$CERT_DIR"
        print_message "${GREEN}" "Created certificate directory: $CERT_DIR"
    fi
}

# Generate self-signed certificate
generate_certificate() {
    print_header "Generating Self-Signed SSL Certificate"

    print_message "${YELLOW}" "Certificate details:"
    echo "  Domain:         $DOMAIN"
    echo "  Validity:       $DAYS_VALID days"
    echo "  Output:         $CERT_DIR"
    echo ""

    # Generate certificate and private key
    openssl req -x509 -newkey rsa:4096 \
        -keyout "$CERT_DIR/key.pem" \
        -out "$CERT_DIR/cert.pem" \
        -days "$DAYS_VALID" \
        -nodes \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=$DOMAIN" \
        -addext "subjectAltName=DNS:$DOMAIN,DNS:localhost,IP:127.0.0.1"

    print_message "${GREEN}" "Certificate generated successfully!"
    echo ""
    print_message "${BLUE}" "Generated files:"
    echo "  Certificate: $CERT_DIR/cert.pem"
    echo "  Private Key: $CERT_DIR/key.pem"
    echo ""
}

# Set appropriate permissions
set_permissions() {
    print_header "Setting File Permissions"

    chmod 600 "$CERT_DIR/key.pem"
    chmod 644 "$CERT_DIR/cert.pem"

    print_message "${GREEN}" "Permissions set:"
    echo "  Private Key:  600 (read/write for owner only)"
    echo "  Certificate:  644 (readable by all)"
    echo ""
}

# Display trust instructions
show_trust_instructions() {
    print_header "Certificate Trust Instructions"

    print_message "${YELLOW}" "This is a self-signed certificate for development use only."
    print_message "${YELLOW}" "Browsers will show security warnings until you trust it."
    echo ""

    # Detect OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        print_message "${BLUE}" "To trust this certificate on macOS:"
        echo "  sudo security add-trusted-cert -d -r trustRoot \\"
        echo "    -k /Library/Keychains/System.keychain $CERT_DIR/cert.pem"
        echo ""
        print_message "${YELLOW}" "Or double-click the certificate and:"
        echo "  1. Open 'Keychain Access'"
        echo "  2. Find 'localhost' or your domain"
        echo "  3. Double-click and set 'Trust: Always Trust'"
        echo ""
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        print_message "${BLUE}" "To trust this certificate on Linux:"
        echo "  sudo cp $CERT_DIR/cert.pem /usr/local/share/ca-certificates/agent-comm.crt"
        echo "  sudo update-ca-certificates"
        echo ""
    fi

    print_message "${BLUE}" "To trust in browser:"
    echo "  1. Open https://$DOMAIN:8443 in your browser"
    echo "  2. Proceed past the security warning"
    echo "  3. The browser will prompt to trust the certificate"
    echo ""

    print_message "${BLUE}" "For Docker/remote access:"
    echo "  1. Copy $CERT_DIR/cert.pem to client machine"
    echo "  2. Import into browser/OS certificate store"
    echo ""
}

# Display certificate information
display_certificate_info() {
    print_header "Certificate Information"

    openssl x509 -in "$CERT_DIR/cert.pem" -text -noout | grep -A 2 "Validity\|Subject:\|Subject Alternative Name"
    echo ""
}

# Display usage instructions
show_usage() {
    cat << EOF
Generate Self-Signed SSL Certificates

Usage: $0 [DOMAIN] [OPTIONS]

Arguments:
    DOMAIN          Domain name for certificate (default: localhost)

Environment Variables:
    CERT_DIR        Output directory for certificates (default: ./certificates)
    DAYS_VALID      Certificate validity in days (default: 365)

Examples:
    $0                                    # Generate for localhost
    $0 example.com                        # Generate for example.com
    CERT_DIR=/etc/ssl $0 dashboard.local  # Custom directory and domain

Output Files:
    cert.pem    SSL/TLS certificate (public key)
    key.pem     Private key (keep secret!)

Note:
    Self-signed certificates are for development only.
    Use Let's Encrypt or a commercial CA for production.

EOF
}

# Main execution
main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                DOMAIN="$1"
                ;;
        esac
        shift
    done

    check_openssl
    create_cert_directory
    generate_certificate
    set_permissions
    display_certificate_info
    show_trust_instructions

    print_message "${GREEN}" "Certificate generation complete!"
    echo ""
    print_message "${BLUE}" "Next steps:"
    echo "  1. Update .env with SSL_ENABLED=true"
    echo "  2. Set SSL_CERT_PATH=$CERT_DIR/cert.pem"
    echo "  3. Set SSL_KEY_PATH=$CERT_DIR/key.pem"
    echo "  4. Restart services with ./scripts/dev.sh restart"
    echo ""
}

# Run main function
main "$@"

#!/bin/bash
set -e

# Ubuntu 24.04.3 Quick Installation Script for Agent Communication System
# This script installs system-level dependencies for Ubuntu

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

print_header() {
    echo ""
    print_message "${BLUE}" "========================================"
    print_message "${BLUE}" "$1"
    print_message "${BLUE}" "========================================"
    echo ""
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_message "${RED}" "This script should not be run as root. Use sudo instead."
    exit 1
fi

print_header "Agent Communication System - Ubuntu 24.04.3 Installation"

# Detect Ubuntu version
UBUNTU_VERSION=$(lsb_release -rs)
print_message "${GREEN}" "Detected Ubuntu version: $UBUNTU_VERSION"

if [[ ! "$UBUNTU_VERSION" =~ ^24\.04 ]]; then
    print_message "${YELLOW}" "Warning: This script is designed for Ubuntu 24.04.x"
    print_message "${YELLOW}" "Your version is $UBUNTU_VERSION. Continue at your own risk."
    read -p "Continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Step 1: Update system
print_header "Step 1: Updating System"
print_message "${YELLOW}" "Updating package list and upgrading packages..."
sudo apt update && sudo apt upgrade -y

# Step 2: Install prerequisites
print_header "Step 2: Installing Prerequisites"
print_message "${YELLOW}" "Installing essential tools..."
sudo apt install -y curl git wget software-properties-common \
    build-essential ca-certificates gnupg lsb-release \
    htop tmux vim net-tools

# Step 3: Install Python 3.13
print_header "Step 3: Installing Python 3.13"
if command -v python3.13 &> /dev/null; then
    print_message "${GREEN}" "Python 3.13 is already installed: $(python3.13 --version)"
else
    print_message "${YELLOW}" "Adding deadsnakes PPA..."
    sudo add-apt-repository ppa:deadsnakes/ppa -y
    sudo apt update -y

    print_message "${YELLOW}" "Installing Python 3.13 and development tools..."
    sudo apt install -y python3.13 python3.13-venv python3.13-dev python3-pip

    print_message "${YELLOW}" "Setting Python 3.13 as default..."
    sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.13 1

    print_message "${GREEN}" "Python 3.13 installed: $(python3 --version)"
fi

# Step 4: Install uv
print_header "Step 4: Installing uv Package Manager"
if command -v uv &> /dev/null; then
    print_message "${GREEN}" "uv is already installed: $(uv --version)"
else
    print_message "${YELLOW}" "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"

    # Add to .bashrc if not already present
    if ! grep -q 'PATH="$HOME/.local/bin:$PATH"' ~/.bashrc; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
    fi

    print_message "${GREEN}" "uv installed: $(uv --version)"
fi

# Step 5: Install system dependencies
print_header "Step 5: Installing System Dependencies"

# PostgreSQL client
print_message "${YELLOW}" "Installing PostgreSQL client..."
sudo apt install -y postgresql-client

# Certbot
print_message "${YELLOW}" "Installing certbot..."
sudo apt install -y certbot

# Nginx
print_message "${YELLOW}" "Installing nginx..."
sudo apt install -y nginx

# Step 6: Configure Firewall
print_header "Step 6: Configuring Firewall"
print_message "${YELLOW}" "Setting up UFW firewall rules..."

# Enable UFW
sudo ufw --force enable

# Allow SSH
sudo ufw allow 22/tcp
sudo ufw allow OpenSSH

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow application port (if not using reverse proxy)
read -p "Allow direct access to port 8001 (not recommended with reverse proxy)? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo ufw allow 8001/tcp
fi

print_message "${GREEN}" "Firewall configured:"
sudo ufw status

# Step 7: Docker (optional)
print_header "Step 7: Docker Installation (Optional)"
read -p "Install Docker and Docker Compose? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if ! command -v docker &> /dev/null; then
        print_message "${YELLOW}" "Installing Docker..."
        curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
        sudo sh /tmp/get-docker.sh
        sudo usermod -aG docker $USER
        rm /tmp/get-docker.sh
        print_message "${GREEN}" "Docker installed: $(docker --version)"
    else
        print_message "${GREEN}" "Docker is already installed: $(docker --version)"
    fi

    if ! command -v docker-compose &> /dev/null; then
        print_message "${YELLOW}" "Installing Docker Compose..."
        sudo apt install -y docker-compose
        print_message "${GREEN}" "Docker Compose installed: $(docker-compose --version)"
    else
        print_message "${GREEN}" "Docker Compose is already installed: $(docker-compose --version)"
    fi
fi

# Step 8: Create application directory
print_header "Step 8: Creating Application Directory"
if [ ! -d "/opt/agent-comm" ]; then
    print_message "${YELLOW}" "Creating /opt/agent-comm directory..."
    sudo mkdir -p /opt/agent-comm
    sudo chown $USER:$USER /opt/agent-comm
    print_message "${GREEN}" "Directory created: /opt/agent-comm"
else
    print_message "${GREEN}" "Directory already exists: /opt/agent-comm"
fi

# Step 9: Summary
print_header "Installation Summary"
print_message "${GREEN}" "System-level dependencies installed successfully!"
echo ""
print_message "${BLUE}" "Installed Components:"
echo "  - Python 3.13: $(python3 --version)"
echo "  - uv: $(uv --version)"
echo "  - PostgreSQL client: $(psql --version | head -1)"
echo "  - Certbot: $(certbot --version | head -1)"
echo "  - Nginx: $(nginx -v 2>&1 | head -1)"
if command -v docker &> /dev/null; then
    echo "  - Docker: $(docker --version | head -1)"
fi
echo ""

print_message "${BLUE}" "Next Steps:"
echo "  1. Navigate to application directory: cd /opt/agent-comm"
echo "  2. Clone repository: git clone <your-repo-url> ."
echo "  3. Install Python dependencies: ./scripts/install.sh"
echo "  4. Configure environment: nano .env"
echo "  5. Setup SSL: ./scripts/setup-ssl.sh --production --domain yourdomain.com --email admin@example.com"
echo "  6. Start service: sudo systemctl start agent-comm"
echo ""

print_message "${YELLOW}" "Important Notes:"
echo "  - Log out and back in for Docker group changes to take effect"
echo "  - Configure your domain DNS to point to this server"
echo "  - Update .env with secure passwords and your domain"
echo ""

print_header "Installation Complete!"

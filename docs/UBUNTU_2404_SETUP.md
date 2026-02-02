# Ubuntu 24.04.3 Deployment Guide

Complete deployment guide for AI Agent Communication System on Ubuntu 24.04.3 LTS.

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [System Update](#2-system-update)
3. [Python 3.13 Installation](#3-python-313-installation)
4. [uv Package Manager](#4-uv-package-manager)
5. [System Dependencies](#5-system-dependencies)
6. [Firewall Configuration](#6-firewall-configuration)
7. [Project Deployment](#7-project-deployment)
8. [SSL Certificate Setup](#8-ssl-certificate-setup)
9. [Systemd Service Configuration](#9-systemd-service-configuration)
10. [Nginx Reverse Proxy](#10-nginx-reverse-proxy)
11. [Verification](#11-verification)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. Prerequisites

- Ubuntu 24.04.3 LTS
- At least 2GB RAM, 1 CPU (4GB RAM, 2 CPU recommended)
- Root or sudo access
- Public IP with ports 80, 443 open

---

## 2. System Update

```bash
# Update package list and upgrade packages
sudo apt update && sudo apt upgrade -y

# Install essential tools
sudo apt install -y curl git wget software-properties-common \
    build-essential ca-certificates gnupg lsb-release

# Verify Ubuntu version
lsb_release -a
# Expected: Ubuntu 24.04.3 LTS
```

---

## 3. Python 3.13 Installation

Ubuntu 24.04.3 includes Python 3.12 by default. Install Python 3.13 from the deadsnakes PPA:

```bash
# Add deadsnakes PPA
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update

# Install Python 3.13 and development tools
sudo apt install -y python3.13 python3.13-venv python3.13-dev python3-pip

# Set Python 3.13 as default (optional)
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.13 1

# Verify installation
python3 --version
# Expected: Python 3.13.x
```

---

## 4. uv Package Manager

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Verify installation
uv --version
```

---

## 5. System Dependencies

```bash
# PostgreSQL client
sudo apt install -y postgresql-client

# Certbot for Let's Encrypt
sudo apt install -y certbot

# Nginx for reverse proxy
sudo apt install -y nginx

# Additional useful tools
sudo apt install -y htop tmux vim net-tools

# Docker (optional, for containerized database)
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker ubuntu
    rm get-docker.sh
fi

# Docker Compose (optional)
if ! command -v docker-compose &> /dev/null; then
    sudo apt install -y docker-compose
fi
```

---

## 6. Firewall Configuration

Ubuntu uses **ufw** (Uncomplicated Firewall) by default.

```bash
# Enable UFW
sudo ufw --force enable

# Allow SSH (to prevent lockout)
sudo ufw allow 22/tcp
sudo ufw allow OpenSSH

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow Communication Server (optional, if not using reverse proxy)
sudo ufw allow 8001/tcp

# Allow MCP Broker (internal only, typically not needed externally)
# sudo ufw allow 8000/tcp

# Check status
sudo ufw status verbose

# Expected output:
# Status: active
#
# To                         Action      From
# --                         ------      ----
# 22/tcp                     ALLOW       Anywhere
# 80/tcp                     ALLOW       Anywhere
# 443/tcp                    ALLOW       Anywhere
# 8001/tcp                   ALLOW       Anywhere
```

### Restrict SSH Access (Production Recommended)

```bash
# Replace with your IP address
YOUR_IP="203.0.113.0"

# Remove general SSH access
sudo ufw delete allow 22/tcp

# Allow SSH from your IP only
sudo ufw allow from $YOUR_IP to any port 22
```

---

## 7. Project Deployment

### Create Application Directory

```bash
# Create application directory
sudo mkdir -p /opt/agent-comm
sudo chown ubuntu:ubuntu /opt/agent-comm
cd /opt/agent-comm
```

### Clone Repository

```bash
# Clone repository (replace with your repo URL)
git clone git@github.com:yarang/agent_com.git .

# Or using SSH
# git clone git@github.com:yarang/agent_com.git .

# Checkout specific branch if needed
# git checkout main
```

### Install Dependencies

```bash
# Ensure uv is available
export PATH="$HOME/.local/bin:$PATH"

# Create virtual environment
uv venv

# Install dependencies (with dev tools for development)
uv pip install -e ".[dev,redis]"

# Or for production (without dev dependencies)
# uv pip install -e ".[redis]"
```

### Configure Environment Variables

```bash
# Create .env file from example
cp .env.example .env

# Edit environment variables
nano .env
```

**Critical settings to update in `.env`:**

```bash
# Generate secure keys
python3 -c 'import secrets; print("JWT_SECRET_KEY=" + secrets.token_urlsafe(32))'
python3 -c 'import secrets; print("API_TOKEN_SECRET=" + secrets.token_urlsafe(32))'

# Database configuration (use external PostgreSQL or Docker)
DATABASE_URL=postgresql+asyncpg://agent:secure_password@localhost:5432/agent_comm

# Server configuration
PORT=8001
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com

# SSL configuration (for production)
SSL_ENABLED=true
SSL_CERT_PATH=/etc/letsencrypt/live/your-domain.com/fullchain.pem
SSL_KEY_PATH=/etc/letsencrypt/live/your-domain.com/privkey.pem
```

---

## 8. SSL Certificate Setup

### Option A: Let's Encrypt (Production)

```bash
# Make script executable
chmod +x scripts/setup-ssl.sh

# Setup SSL (replace domain and email)
./scripts/setup-ssl.sh --production \
    --domain your-domain.com \
    --email admin@example.com

# Or with staging first (no rate limits)
./scripts/setup-ssl.sh --staging \
    --domain your-domain.com \
    --email admin@example.com
```

### Option B: Self-Signed (Development)

```bash
# Use project script for development
./scripts/generate-certificates.sh

# Or manually generate
mkdir -p certificates
openssl req -x509 -newkey rsa:4096 \
    -keyout certificates/key.pem \
    -out certificates/cert.pem \
    -days 365 \
    -nodes \
    -subj "/CN=localhost"
```

### Setup Auto-Renewal

```bash
# Test renewal
sudo certbot renew --dry-run

# Setup cron job for auto-renewal
(crontab -l 2>/dev/null | grep -v "certbot renew"; echo "0 0,12 * * * certbot renew --quiet --post-hook 'systemctl reload nginx'") | sudo crontab -
```

---

## 9. Systemd Service Configuration

### Create Systemd Service File

```bash
# Create service file
sudo tee /etc/systemd/system/agent-comm.service > /dev/null << 'EOF'
[Unit]
Description=Agent Communication Server
Documentation=https://github.com/yarang/agent_com
After=network.target postgresql.service docker.service
Wants=postgresql.service

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/agent-comm

# Environment
Environment="PATH=/opt/agent-comm/.venv/bin:/usr/bin:/bin"
Environment="PYTHONUNBUFFERED=1"

# Service management
Restart=always
RestartSec=10
StartLimitInterval=60
StartLimitBurst=3

# Process management
ExecStart=/opt/agent-comm/.venv/bin/uvicorn communication_server.main:app \
    --host 0.0.0.0 \
    --port 8001 \
    --workers 2 \
    --loop uvloop

# Resource limits (adjust based on your VM size)
MemoryMax=2G
CPUQuota=200%

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/agent-comm /var/log/agent-comm

# Logging
StandardOutput=append:/var/log/agent-comm/agent-comm.log
StandardError=append:/var/log/agent-comm/agent-comm-error.log
SyslogIdentifier=agent-comm

[Install]
WantedBy=multi-user.target
EOF
```

### Create Log Directory

```bash
# Create log directory
sudo mkdir -p /var/log/agent-comm
sudo chown ubuntu:ubuntu /var/log/agent-comm
```

### Enable and Start Service

```bash
# Reload systemd daemon
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable agent-comm

# Start service
sudo systemctl start agent-comm

# Check status
sudo systemctl status agent-comm

# View logs
sudo journalctl -u agent-comm -f
```

---

## 10. Nginx Reverse Proxy

### Create Nginx Configuration

```bash
# Remove default site
sudo rm -f /etc/nginx/sites-enabled/default

# Create site configuration
sudo tee /etc/nginx/sites-available/agent-comm > /dev/null << 'EOF'
# Upstream configuration
upstream agent_comm_backend {
    server 127.0.0.1:8001;
    keepalive 32;
}

# Rate limiting zone
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_conn_zone $binary_remote_addr zone=conn_limit:10m;

# HTTP to HTTPS redirect
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    # Let's Encrypt ACME challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # Redirect all HTTP traffic to HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # SSL session cache
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Logging
    access_log /var/log/nginx/agent-comm-access.log;
    error_log /var/log/nginx/agent-comm-error.log;

    # Client body size limit
    client_max_body_size 10M;

    # Communication server API proxy
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        limit_conn conn_limit 10;

        proxy_pass http://agent_comm_backend;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # WebSocket proxy for meetings
    location /ws/meetings/ {
        proxy_pass http://agent_comm_backend;
        proxy_http_version 1.1;

        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }

    # WebSocket proxy for status
    location /ws/status {
        proxy_pass http://agent_comm_backend;
        proxy_http_version 1.1;

        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }

    # Health endpoint (no rate limiting)
    location /health {
        proxy_pass http://agent_comm_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        access_log off;
    }

    # Root location
    location / {
        proxy_pass http://agent_comm_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF
```

### Enable Nginx Site

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/agent-comm /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Enable and start Nginx
sudo systemctl enable nginx
sudo systemctl start nginx

# Check status
sudo systemctl status nginx
```

---

## 11. Verification

### Check Service Status

```bash
# Check agent-comm service
sudo systemctl status agent-comm

# Check nginx service
sudo systemctl status nginx

# Check PostgreSQL (if running locally)
sudo systemctl status postgresql
```

### Test Endpoints

```bash
# Test health endpoint directly
curl http://localhost:8001/health

# Test through Nginx
curl https://localhost/health

# Test from external
curl https://your-domain.com/health

# Expected response:
# {"status":"healthy","service":"communication-server","version":"1.0.0"}
```

### View Logs

```bash
# Application logs
sudo journalctl -u agent-comm -f

# Nginx logs
sudo tail -f /var/log/nginx/agent-comm-access.log
sudo tail -f /var/log/nginx/agent-comm-error.log

# Application file logs
tail -f /var/log/agent-comm/agent-comm.log
```

---

## 12. Troubleshooting

### Service Not Starting

```bash
# Check service status
sudo systemctl status agent-comm

# View detailed logs
sudo journalctl -u agent-comm -n 100 --no-pager

# Test manually
cd /opt/agent-comm
source .venv/bin/activate
uvicorn communication_server.main:app --host 0.0.0.0 --port 8001
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test connection
psql -U agent -h localhost -d agent_comm

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-*.log
```

### Nginx 502 Bad Gateway

```bash
# Check if backend is running
curl http://localhost:8001/health

# Check Nginx error logs
sudo tail -f /var/log/nginx/agent-comm-error.log

# Restart both services
sudo systemctl restart agent-comm
sudo systemctl restart nginx
```

### Firewall Issues

```bash
# Check UFW status
sudo ufw status verbose

# Open required ports
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Reload firewall
sudo ufw reload
```

### Permission Issues

```bash
# Fix log directory permissions
sudo chown -R ubuntu:ubuntu /var/log/agent-comm

# Fix application directory permissions
sudo chown -R ubuntu:ubuntu /opt/agent-comm
```

---

## Quick Start Script

For automated installation, use the provided Ubuntu installation script:

```bash
# Download and run the installation script
chmod +x scripts/install-ubuntu.sh
sudo ./scripts/install-ubuntu.sh
```

---

## Support and Resources

- [Ubuntu Documentation](https://ubuntu.com/server/docs)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [Project Repository](https://github.com/yarang/agent_com)

---

**Document Version**: 1.0.0
**Last Updated**: 2026-02-01
**Platform**: Ubuntu 24.04.3 LTS

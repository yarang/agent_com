# Oracle Cloud Infrastructure (OCI) Deployment Guide

Complete deployment guide for AI Agent Communication System on Oracle Cloud Infrastructure VM instances.

> **Ubuntu 24.04.3 users**: See [UBUNTU_2404_SETUP.md](UBUNTU_2404_SETUP.md) for Ubuntu-specific deployment guide.

## Table of Contents

1. [OCI VM Instance Creation](#1-oci-vm-instance-creation)
2. [Network Configuration (Security Lists)](#2-network-configuration-security-lists)
3. [Initial Server Setup](#3-initial-server-setup)
4. [Firewall Configuration](#4-firewall-configuration)
5. [Project Deployment](#5-project-deployment)
6. [Systemd Service Configuration](#6-systemd-service-configuration)
7. [Nginx Reverse Proxy](#7-nginx-reverse-proxy)
8. [Auto-Start Configuration](#8-auto-start-configuration)
9. [OCI-Specific Considerations](#9-oci-specific-considerations)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. OCI VM Instance Creation

### Step 1: Access OCI Console

1. Log in to [Oracle Cloud Console](https://console.oraclecloud.com/)
2. Navigate to **Compute** > **Instances**
3. Click **Create Instance**

### Step 2: Configure Instance Basics

| Setting | Recommended Value |
|---------|------------------|
| Name | `agent-comm-server` |
| Compartment | Select your compartment |
| Availability Domain | Select closest to your users |

### Step 3: Choose Shape

For **Free Tier** (Always Free):

- Shape: `VM.Standard.E4.Flex`
- OCPU: `1` (up to 4 OCPU available)
- Memory: `6 GB` (up to 24 GB available)

For **Production**:

- Shape: `VM.Standard.E4.Flex` or higher
- OCPU: `2-4` (based on load)
- Memory: `8-16 GB` (recommended)

### Step 4: Choose Image

Recommended images:

1. **Ubuntu 24.04.3 LTS** (Recommended)
   - Ubuntu 24.04.3 LTS
   - Familiar package management (apt)
   - Python 3.13 easily available via PPA
   - See [UBUNTU_2404_SETUP.md](UBUNTU_2404_SETUP.md) for detailed guide

2. **Oracle Linux**
   - Oracle Linux 8/9
   - Optimized for OCI platform
   - Better OCI tool integration
   - Uses dnf/yum package manager

### Step 5: Configure SSH Keys

1. **Generate SSH Key Pair** (if you don't have one):

```bash
# On your local machine
ssh-keygen -t rsa -b 4096 -C "oci-agent-comm" -f ~/.ssh/oci_agent_comm
```

2. **Add Public Key to OCI**:
   - Paste contents of `~/.ssh/oci_agent_comm.pub` into SSH Keys field
   - Or upload the public key file

### Step 6: Configure Networking

| Setting | Value |
|---------|-------|
| Virtual Cloud Network | Create new VCN or use existing |
| Subnet | Public Subnet (for internet access) |
| Assign Public IP | Yes (for external access) |

### Step 7: Boot Volume

| Setting | Value |
|---------|-------|
| Boot Volume Size | 50 GB (minimum) |
| Encryption | Oracle-managed key |

### Step 8: Advanced Options

- **Hostname**: `agent-comm-oci`
- **Cloud-init**: Leave disabled (will configure manually)

### Step 9: Create Instance

Review all settings and click **Create**. Wait 2-5 minutes for instance provisioning.

### Step 10: Access Your Instance

```bash
# Ubuntu instances
ssh -i ~/.ssh/oci_agent_comm ubuntu@<YOUR_PUBLIC_IP>

# Oracle Linux instances
ssh -i ~/.ssh/oci_agent_comm opc@<YOUR_PUBLIC_IP>

# Or using DNS if configured
ssh -i ~/.ssh/oci_agent_comm ubuntu@<YOUR_DOMAIN>
```

**Note**: Default user is `ubuntu` for Ubuntu, `opc` for Oracle Linux.

**Ubuntu 24.04.3 Quick Start**: After connecting, run the automated installer:
```bash
# Clone repository and run Ubuntu installer
git clone <your-repo-url> /home/ubuntu/agent_com
cd /home/ubuntu/agent_com
./scripts/install-ubuntu.sh
```

---

## 2. Network Configuration (Security Lists)

OCI uses Security Lists (or Network Security Groups) to control inbound/outbound traffic.

### Option A: Security List Configuration

1. Navigate to **Networking** > **Virtual Cloud Networks**
2. Select your VCN > **Security Lists** > **Default Security List**
3. Add **Ingress Rules**:

| Rule | Protocol | Source Port | Destination Port | Type |
|------|----------|-------------|------------------|------|
| SSH | TCP | Any | 22 | IPv4 |
| HTTP | TCP | Any | 80 | IPv4 |
| HTTPS | TCP | Any | 443 | IPv4 |
| Comm Server | TCP | Any | 8001 | IPv4 |
| MCP Broker | TCP | Any | 8000 | IPv4 |

### Option B: Network Security Group (Recommended for Production)

1. Create **Network Security Group** (NSG)
2. Add **Ingress Rules** to NSG:

```bash
# Security Rules for Agent Communication System
# Port 22: SSH (restrict to your IP in production)
# Port 80: HTTP (redirect to HTTPS)
# Port 443: HTTPS (primary access)
# Port 8001: Communication Server (optional, can use proxy)
# Port 8000: MCP Broker (internal only, use VPN)
```

3. **Associate NSG with Instance VNIC**

### Example: OCI CLI Commands

```bash
# Add ingress rule using OCI CLI
oci network security-list update \
  --seclist-id <SECURITY_LIST_OCID> \
  --ingress-security-rules '[{"protocol": "6", "tcp-options": {"destination-port-range": {"max": 22, "min": 22}}, "source": "0.0.0.0/0", "is-stateless": false}]'

oci network security-list update \
  --seclist-id <SECURITY_LIST_OCID> \
  --ingress-security-rules '[{"protocol": "6", "tcp-options": {"destination-port-range": {"max": 443, "min": 443}}, "source": "0.0.0.0/0", "is-stateless": false}]'
```

---

## 3. Initial Server Setup

### Ubuntu 24.04.3 Setup (Recommended)

For Ubuntu 24.04.3, use the automated installer or follow [UBUNTU_2404_SETUP.md](UBUNTU_2404_SETUP.md):

```bash
# Quick automated installation
git clone <your-repo-url> /home/ubuntu/agent_com
cd /home/ubuntu/agent_com
./scripts/install-ubuntu.sh
```

Or manually:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.13 from deadsnakes PPA
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update -y
sudo apt install -y python3.13 python3.13-venv python3.13-dev git curl wget

# Install development tools
sudo apt install -y build-essential

# Verify Python installation
python3.13 --version
```

### Oracle Linux Setup

If you chose Oracle Linux image:

```bash
# Update system
sudo dnf update -y

# Install development tools
sudo dnf groupinstall -y "Development Tools"

# Install Python 3.13 and development dependencies
sudo dnf install -y python3.13 python3.13-pip python3.13-devel git curl wget

# Verify Python installation
python3.13 --version
```

### Install Docker

```bash
# Install Docker using official script
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group (logout/login required)
sudo usermod -aG docker $USER

# Enable Docker service
sudo systemctl enable docker
sudo systemctl start docker

# Verify Docker installation
docker --version
docker ps
```

### Install Certbot (for SSL)

```bash
# Ubuntu
sudo apt install -y certbot

# Oracle Linux
# sudo dnf install -y certbot

# Verify installation
certbot --version
```

### Install Additional Dependencies

```bash
# Ubuntu
sudo apt install -y postgresql-client nginx htop tmux vim

# Oracle Linux
# sudo dnf install -y postgresql-client nginx htop tmux vim
```

### Set Timezone

```bash
# Set to your timezone
sudo timedatectl set-timezone Asia/Seoul
# sudo timedatectl set-timezone America/New_York

# Verify
timedatectl
```

### Create Application Directory

```bash
# Create application directory
sudo mkdir -p /opt/agent-comm
sudo chown $USER:$USER /opt/agent-comm
cd /opt/agent-comm
```

---

## 4. Firewall Configuration

Ubuntu uses **ufw** by default. Oracle Linux uses **firewalld**.

### Ubuntu (ufw)

```bash
# Enable ufw
sudo ufw --force enable

# Allow SSH first (to prevent lockout)
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow application ports
sudo ufw allow 8001/tcp
sudo ufw allow 8000/tcp

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
# 8000/tcp                   ALLOW       Anywhere
```

### Oracle Linux (firewalld)

```bash
# Start and enable firewalld
sudo systemctl start firewalld
sudo systemctl enable firewalld

# Check status
sudo firewall-cmd --state

# Add services
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --add-service=ssh

# Add custom ports for Communication Server
sudo firewall-cmd --permanent --add-port=8001/tcp  # Communication Server
sudo firewall-cmd --permanent --add-port=8000/tcp  # MCP Broker (internal)

# For SSL
sudo firewall-cmd --permanent --add-port=443/tcp

# Reload to apply changes
sudo firewall-cmd --reload

# List all rules
sudo firewall-cmd --list-all
```

### Restrict SSH Access (Recommended for Production)

```bash
# Ubuntu - Restrict SSH to your IP only
sudo ufw delete allow 22/tcp
sudo ufw allow from YOUR_IP to any port 22

# Oracle Linux - Restrict SSH
sudo firewall-cmd --permanent --remove-service=ssh
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="YOUR_IP/32" port protocol="tcp" port="22" accept'
sudo firewall-cmd --reload
```

---

## 5. Project Deployment

### Clone Repository

```bash
# Navigate to application directory
cd /opt/agent-comm

# Clone repository (replace with your repo URL)
git clone https://github.com/your-username/agent_com.git .

# Or if using a specific branch
git clone -b main https://github.com/your-username/agent_com.git .
```

### Install uv Package Manager

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH (add to .bashrc for persistence)
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Verify installation
uv --version
```

### Install Dependencies

```bash
# Create virtual environment
uv venv

# Install dependencies
uv pip install -e ".[dev,redis]"

# Or for production (without dev dependencies)
uv pip install -e ".[redis]"
```

### Configure Environment Variables

```bash
# Create .env file from example
cp .env.example .env

# Edit environment variables
vim .env
```

**Critical settings to update in `.env`:**

```bash
# Generate secure keys
python3.13 -c 'import secrets; print("JWT_SECRET_KEY=" + secrets.token_urlsafe(32))'
python3.13 -c 'import secrets; print("API_TOKEN_SECRET=" + secrets.token_urlsafe(32))'

# Database configuration (use external PostgreSQL or Docker)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/agent_comm

# Server configuration
PORT=8001
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com

# SSL configuration (for production)
SSL_ENABLED=true
SSL_CERT_PATH=/etc/letsencrypt/live/your-domain.com/fullchain.pem
SSL_KEY_PATH=/etc/letsencrypt/live/your-domain.com/privkey.pem
SSL_PORT=8443
```

### Setup SSL Certificates

#### Option A: Let's Encrypt (Production)

```bash
# Ensure DNS is configured for your domain
# Run certbot to get certificates
sudo certbot certonly --standalone \
  -d your-domain.com \
  -d www.your-domain.com \
  --email admin@example.com \
  --agree-tos \
  --non-interactive

# Certificates will be stored at:
# /etc/letsencrypt/live/your-domain.com/fullchain.pem
# /etc/letsencrypt/live/your-domain.com/privkey.pem

# Setup auto-renewal
sudo crontab -e

# Add this line for daily renewal check:
0 0,12 * * * certbot renew --quiet --post-hook "systemctl reload nginx"
```

#### Option B: Self-Signed (Development)

```bash
# Use project script for development
./scripts/generate-certificates.sh

# Or manually generate
openssl req -x509 -newkey rsa:4096 \
  -keyout certificates/key.pem \
  -out certificates/cert.pem \
  -days 365 \
  -nodes \
  -subj "/CN=localhost"
```

### Database Setup

#### Option A: PostgreSQL on OCI VM

```bash
# Install PostgreSQL
sudo dnf install -y postgresql postgresql-server postgresql-contrib  # Oracle Linux
# sudo apt install -y postgresql postgresql-contrib  # Ubuntu

# Initialize database
sudo postgresql-setup --initdb  # Oracle Linux
# sudo pg_ctlcluster 15 main start  # Ubuntu

# Start and enable PostgreSQL
sudo systemctl enable postgresql
sudo systemctl start postgresql

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE agent_comm;
CREATE USER agent WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE agent_comm TO agent;
ALTER DATABASE agent_comm OWNER TO agent;
\c agent_comm
GRANT ALL ON SCHEMA public TO agent;
EOF

# Update pg_hba.conf for password authentication
sudo vim /var/lib/pgsql/data/pg_hba.conf  # Oracle Linux
# sudo vim /etc/postgresql/15/main/pg_hba.conf  # Ubuntu

# Change auth method to scram-sha-256 or md5
# host    all             all             127.0.0.1/32            scram-sha-256

# Restart PostgreSQL
sudo systemctl restart postgresql
```

#### Option B: Docker Compose with PostgreSQL

```bash
# Use project docker-compose.yml
# Create production override file
cat > docker-compose.prod.yml << EOF
version: "3.8"

services:
  postgres:
    image: postgres:15-alpine
    container_name: agent-comm-postgres
    environment:
      POSTGRES_DB: agent_comm
      POSTGRES_USER: agent
      POSTGRES_PASSWORD: \${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: always
    networks:
      - agent-comm-network

  redis:
    image: redis:7-alpine
    container_name: agent-comm-redis
    command: redis-server --appendonly yes --requirepass \${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    restart: always
    networks:
      - agent-comm-network

volumes:
  postgres_data:
  redis_data:

networks:
  agent-comm-network:
    external: true
EOF

# Create network
docker network create agent-comm-network

# Start services
docker-compose -f docker-compose.prod.yml up -d
```

### Run Database Migrations

```bash
# Activate virtual environment
source .venv/bin/activate

# Run migrations
uv run python -c "
import asyncio
from agent_comm_core.db.database import init_db
import os

async def main():
    db_url = os.getenv('DATABASE_URL')
    await init_db(database_url=db_url, drop_all=False)
    print('Database initialized successfully!')

asyncio.run(main())
"
```

### Test Application

```bash
# Test Communication Server
uv run uvicorn communication_server.main:app --host 0.0.0.0 --port 8001

# In another terminal, test health endpoint
curl http://localhost:8001/health

# Expected response:
# {"status":"healthy","service":"communication-server","version":"1.0.0","ssl_enabled":false}
```

---

## 6. Systemd Service Configuration

Create systemd service for automatic startup and management.

### Create Systemd Service File

```bash
# Create service file
sudo vim /etc/systemd/system/agent-comm.service
```

### Service Configuration

Paste the following content:

```ini
[Unit]
Description=Agent Communication Server
Documentation=https://github.com/your-username/agent_com
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
    --loop uvloop \
    --log-config /opt/agent-comm/logging.conf

# Resource limits (adjust based on OCI shape)
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
```

**Note**: For Oracle Linux instances, change `User=ubuntu` to `User=opc`.

### Create Logging Configuration

```bash
# Create log directory
sudo mkdir -p /var/log/agent-comm
sudo chown ubuntu:ubuntu /var/log/agent-comm

# For Oracle Linux, use:
# sudo chown opc:opc /var/log/agent-comm
```

# Create logging configuration
vim /opt/agent-comm/logging.conf
```

```ini
[loggers]
keys=root,uvicorn.error,uvicorn.access

[handlers]
keys=default

[formatters]
keys=default

[logger_root]
level=INFO
handlers=default

[logger_uvicorn.error]
level=INFO
handlers=default
propagate=0
qualname=uvicorn.error

[logger_uvicorn.access]
level=INFO
handlers=default
propagate=0
qualname=uvicorn.access

[handler_default]
class=StreamHandler
formatter=default
args=(sys.stdout,)

[formatter_default]
format=%(asctime)s - %(name)s - %(levelname)s - %(message)s
datefmt=%Y-%m-%d %H:%M:%S
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

# View application logs
tail -f /var/log/agent-comm/agent-comm.log
```

### Service Management Commands

```bash
# Start service
sudo systemctl start agent-comm

# Stop service
sudo systemctl stop agent-comm

# Restart service
sudo systemctl restart agent-comm

# Reload service (graceful restart)
sudo systemctl reload agent-comm

# Check status
sudo systemctl status agent-comm

# View recent logs
sudo journalctl -u agent-comm -n 100

# Follow logs
sudo journalctl -u agent-comm -f

# Check service health
curl http://localhost:8001/health
```

---

## 7. Nginx Reverse Proxy

Configure Nginx as a reverse proxy with SSL termination.

### Create Nginx Configuration

```bash
# Create site configuration
sudo vim /etc/nginx/conf.d/agent-comm.conf
```

```nginx
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

    # OCSP stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;

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
        proxy_set_header X-Request-ID $request_id;

        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    # WebSocket proxy for meetings
    location /ws/meetings/ {
        proxy_pass http://agent_comm_backend;
        proxy_http_version 1.1;

        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

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
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

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

    # Dashboard static files
    location /static/ {
        alias /opt/agent-comm/src/communication_server/static/;
        expires 7d;
        add_header Cache-Control "public, immutable";
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
```

### Configure Main Nginx Settings

```bash
# Edit main nginx.conf
sudo vim /etc/nginx/nginx.conf
```

Update/add the following in http block:

```nginx
http {
    # ... existing config ...

    # Rate limiting zones
    limit_req_zone $binary_remote_addr zone=general_limit:10m rate=30r/s;

    # Keepalive connections
    upstream_keepalive_connections 64;
    upstream_keepalive_timeout 60s;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss application/rss+xml font/truetype font/opentype application/vnd.ms-fontobject image/svg+xml;

    # Security headers (global)
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options SAMEORIGIN always;

    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for" '
                    'rt=$request_time uct="$upstream_connect_time" '
                    'uht="$upstream_header_time" urt="$upstream_response_time"';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log warn;

    # Include site configurations
    include /etc/nginx/conf.d/*.conf;
}
```

### Test and Enable Nginx

```bash
# Test configuration
sudo nginx -t

# Expected output:
# nginx: configuration file /etc/nginx/nginx.conf syntax is ok
# nginx: configuration file /etc/nginx/nginx.conf test is successful

# Enable and start Nginx
sudo systemctl enable nginx
sudo systemctl start nginx

# Check status
sudo systemctl status nginx

# Check if listening
sudo netstat -tlnp | grep nginx

# Expected output:
# tcp        0      0 0.0.0.0:80              0.0.0.0:*               LISTEN      1234/nginx: master
# tcp        0      0 0.0.0.0:443             0.0.0.0:*               LISTEN      1234/nginx: master
```

### Configure Firewall for Nginx

```bash
# Oracle Linux
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload

# Ubuntu
sudo ufw allow 'Nginx Full'
```

### Setup Log Rotation

```bash
# Create logrotate config
sudo vim /etc/logrotate.d/agent-comm
```

```
/var/log/agent-comm/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 ubuntu ubuntu
    sharedscripts
    postrotate
        systemctl reload agent-comm > /dev/null 2>&1 || true
    endscript
}
```

**Note**: For Oracle Linux instances, change `ubuntu ubuntu` to `opc opc`.

---

## 8. Auto-Start Configuration

Ensure all services start automatically on boot.

### Enable Services

```bash
# Enable PostgreSQL
sudo systemctl enable postgresql

# Enable Docker (if using containerized services)
sudo systemctl enable docker

# Enable Agent Communication service
sudo systemctl enable agent-comm

# Enable Nginx
sudo systemctl enable nginx

# Verify enabled services
systemctl list-unit-files | grep enabled
```

### Configure Docker Auto-Start (Optional)

If using Docker for PostgreSQL/Redis:

```bash
# Create systemd service for docker-compose
sudo vim /etc/systemd/system/agent-comm-docker.service
```

```ini
[Unit]
Description=Agent Communication Docker Services
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/agent-comm
ExecStart=/usr/local/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.prod.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

```bash
# Enable docker service
sudo systemctl enable agent-comm-docker
```

### Test Auto-Start

```bash
# Reboot instance
sudo reboot

# After reboot, connect and verify services
ssh -i ~/.ssh/oci_agent_comm opc@<YOUR_IP>

# Check all services
sudo systemctl status postgresql
sudo systemctl status agent-comm
sudo systemctl status nginx
sudo systemctl status agent-comm-docker  # if enabled

# Check health endpoints
curl http://localhost:8001/health
curl https://localhost/health
```

### Configure Cron Jobs

```bash
# Open crontab
crontab -e

# Add periodic tasks
# Database backup at 2 AM daily
0 2 * * * /opt/agent-comm/scripts/backup-db.sh

# Log rotation at 3 AM daily
0 3 * * * /usr/sbin/logrotate /etc/logrotate.d/agent-comm

# SSL renewal check at 00:00 and 12:00
0 0,12 * * * certbot renew --quiet --post-hook "systemctl reload nginx"

# Cleanup old logs weekly
0 4 * * 0 find /var/log/agent-comm -name "*.log.*" -mtime +30 -delete
```

### Create Backup Script

```bash
# Create backup script
sudo vim /opt/agent-comm/scripts/backup-db.sh
```

```bash
#!/bin/bash
# Database Backup Script for Agent Communication System

set -e

BACKUP_DIR="/opt/backups/agent-comm"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/db_backup_$DATE.sql.gz"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Dump database
pg_dump -U agent -h localhost agent_comm | gzip > "$BACKUP_FILE"

# Keep only last 7 days of backups
find "$BACKUP_DIR" -name "db_backup_*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_FILE"
```

```bash
# Make script executable
chmod +x /opt/agent-comm/scripts/backup-db.sh

# Create backup directory
sudo mkdir -p /opt/backups/agent-comm
sudo chown ubuntu:ubuntu /opt/backups/agent-comm

# For Oracle Linux instances:
# sudo chown opc:opc /opt/backups/agent-comm
```

---

## 9. OCI-Specific Considerations

### Oracle Cloud Free Tier

The Oracle Cloud Free Tier includes:

| Resource | Free Tier Limit |
|----------|----------------|
| VM Instances | 2 x VM.Standard.E4.Flex (up to 4 OCPU, 24 GB RAM each) |
| Public IPs | 2 reserved |
| Outbound Data | 10 TB/month |
| Inbound Data | Unlimited |
| Load Balancer | 1 (optional for HA) |

### Ubuntu 24.04.3 Specifics

**Package Manager**: Ubuntu uses `apt`

```bash
# Install packages
sudo apt install <package>

# Update system
sudo apt update && sudo apt upgrade -y

# Search for packages
apt search <keyword>
```

**Default User**: `ubuntu`

```bash
# Default user is ubuntu
ssh ubuntu@<your-ip>

# Ubuntu user is in sudo group
sudo -  # requires password
```

**Firewall**: Uses `ufw`

```bash
# Check firewall status
sudo ufw status

# Allow ports
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

### Oracle Linux Specifics

**Package Manager**: Oracle Linux uses `dnf` (or `yum`)

```bash
# Install packages
sudo dnf install <package>

# Update system
sudo dnf update -y

# Search for packages
sudo dnf search <keyword>
```

**Default User**: `opc` instead of `ubuntu`

```bash
# Default user is opc
ssh opc@<your-ip>

# Oracle Linux user is in wheel group (sudoers)
sudo -  # works without password
```

**Firewall**: Uses `firewalld`

```bash
# Check firewall status
sudo firewall-cmd --state

# List all zones
sudo firewall-cmd --list-all-zones

# Get active zone
sudo firewall-cmd --get-active-zones
```

### Static Public IP

By default, OCI instances get ephemeral public IPs. For production, create a reserved IP:

1. Navigate to **Networking** > **Public IPs**
2. Click **Create Reserved Public IP**
3. Select compartment and region
4. Click **Create**
5. Associate with instance VNIC

```bash
# Using OCI CLI
oci network public-ip create \
  --compartment-id <COMPARTMENT_OCID> \
  --lifetime "RESERVED" \
  --name "agent-comm-ip"
```

### OCI DNS Configuration

1. Navigate to **Networking** > **DNS Zones**
2. Create zone for your domain
3. Add A record pointing to reserved public IP
4. Update your domain's nameservers to OCI DNS

### Monitoring and Logging

OCI provides built-in monitoring:

```bash
# Ubuntu - Install OCI CLI
sudo apt install -y python3-oci-cli

# Oracle Linux - Install OCI CLI
# sudo dnf install -y python3-oci-cli

# Configure CLI
oci setup config

# View instance metrics
oci monitoring metric-data summarize \
  --compartment-id <COMPARTMENT_OCID> \
  --namespace "oci_compute" \
  --query-text "CPUUtilization[1m].mean()"
```

### OCI Object Storage (Optional)

For storing backups and large files:

```bash
# Create bucket using OCI CLI
oci os bucket create \
  --compartment-id <COMPARTMENT_OCID> \
  --name "agent-comm-backups"

# Upload backup
oci os object put \
  --bucket-name "agent-comm-backups" \
  --name "db_backup_$(date +%Y%m%d).sql.gz" \
  --file "/opt/backups/agent-comm/db_backup_$(date +%Y%m%d)_*.sql.gz"
```

### Security Best Practices for OCI

1. **Use IAM Policies**: Restrict access to OCI console
2. **Enable Security Zones**: Apply security best practices automatically
3. **Use Vault**: Store secrets in OCI Vault instead of .env files
4. **Network Security Groups**: Use NSGs instead of security lists
5. **Bastion Service**: Use OCI Bastion for secure SSH access

```bash
# Create bastion session
oci bastion session create \
  --bastion-id <BASTION_OCID> \
  --target-resource-id <INSTANCE_OCID> \
  --session-ttl 1800 \
  --key-type PUBSSH
```

### OCI Load Balancer (High Availability)

For production deployment with multiple instances:

```bash
# Create load balancer
oci lb load-balancer create \
  --compartment-id <COMPARTMENT_OCID> \
  --name "agent-comm-lb" \
  --shape "flexible" \
  --subnet-ids <SUBNET_OCID> \
  --is-private false

# Create backend set
oci lb backend-set create \
  --load-balancer-id <LB_OCID> \
  --name "agent-comm-backend" \
  --policy "ROUND_ROBIN" \
  --health-checker-protocol "HTTP" \
  --health-checker-url-path "/health"
```

---

## 10. Troubleshooting

### Common Issues and Solutions

#### Issue 1: Cannot Connect to Instance

**Symptoms**: SSH connection times out or refused

**Solutions**:

```bash
# 1. Check security list rules
oci network security-list list --compartment-id <COMPARTMENT_OCID>

# 2. Verify instance is running
oci compute instance get --instance-id <INSTANCE_OCID>

# 3. Check local firewall
sudo firewall-cmd --list-all

# 4. Verify SSH service
sudo systemctl status sshd

# 5. Check SSH logs
sudo tail -f /var/log/secure
```

#### Issue 2: Service Not Starting

**Symptoms**: Systemd service fails to start

**Solutions**:

```bash
# 1. Check service status
sudo systemctl status agent-comm

# 2. View detailed logs
sudo journalctl -u agent-comm -n 100 --no-pager

# 3. Check application logs
tail -f /var/log/agent-comm/agent-comm-error.log

# 4. Test manually
cd /opt/agent-comm
source .venv/bin/activate
uvicorn communication_server.main:app --host 0.0.0.0 --port 8001

# 5. Verify environment variables
systemctl show agent-comm --property=Environment
```

#### Issue 3: Database Connection Errors

**Symptoms**: Application cannot connect to PostgreSQL

**Solutions**:

```bash
# 1. Check PostgreSQL is running
sudo systemctl status postgresql

# 2. Test connection
psql -U agent -h localhost -d agent_comm

# 3. Check pg_hba.conf
sudo cat /var/lib/pgsql/data/pg_hba.conf | grep -v '^#' | grep -v '^$'

# 4. Check PostgreSQL logs
sudo tail -f /var/lib/pgsql/data/log/postgresql-*.log

# 5. Verify DATABASE_URL in .env
grep DATABASE_URL .env
```

#### Issue 4: SSL Certificate Issues

**Symptoms**: HTTPS not working, certificate warnings

**Solutions**:

```bash
# 1. Check certificate files
ls -la /etc/letsencrypt/live/your-domain.com/

# 2. Verify certificate expiry
sudo certbot certificates

# 3. Test certificate renewal
sudo certbot renew --dry-run

# 4. Check Nginx SSL configuration
sudo nginx -t

# 5. Reload Nginx after certificate update
sudo systemctl reload nginx

# 6. If using self-signed, trust certificate locally
sudo cp certificates/cert.pem /etc/pki/ca-trust/source/anchors/
sudo update-ca-trust
```

#### Issue 5: Nginx 502 Bad Gateway

**Symptoms**: Nginx returns 502 error

**Solutions**:

```bash
# 1. Check if backend service is running
curl http://localhost:8001/health

# 2. Check Nginx error logs
sudo tail -f /var/log/nginx/agent-comm-error.log

# 3. Verify upstream configuration
sudo nginx -t | grep upstream

# 4. Check SELinux (Oracle Linux)
sudo getenforce
sudo setsebool -P httpd_can_network_connect 1

# 5. Restart both services
sudo systemctl restart agent-comm
sudo systemctl restart nginx
```

#### Issue 6: Firewall Blocking Connections

**Symptoms**: External connections blocked

**Solutions**:

```bash
# 1. Check OCI security list ingress rules
oci network security-list get --sec-list-id <SEC_LIST_OCID>

# 2. Check local firewall
sudo firewall-cmd --list-all

# 3. Test local connection
curl http://localhost:8001/health

# 4. Test from external
curl http://<YOUR_PUBLIC_IP>:8001/health

# 5. Add missing rules
sudo firewall-cmd --permanent --add-port=8001/tcp
sudo firewall-cmd --reload
```

#### Issue 7: SELinux Blocking Services

**Symptoms**: Services fail with permission denied

**Solutions**:

```bash
# 1. Check SELinux status
sudo getenforce

# 2. Check audit logs for denials
sudo ausearch -m avc -ts recent

# 3. Allow HTTP network connections
sudo setsebool -P httpd_can_network_connect 1

# 4. If needed, set to permissive mode for testing
sudo setenforce 0

# 5. Create custom policy (for production)
sudo audit2allow -a -M agent_comm
sudo semodule -i agent_comm.pp

# 6. Re-enable enforcing
sudo setenforce 1
```

#### Issue 8: DNS Propagation Issues

**Symptoms**: Domain not resolving to OCI IP

**Solutions**:

```bash
# 1. Check DNS propagation
dig your-domain.com +short
nslookup your-domain.com

# 2. Check OCI DNS zone
oci dns record get \
  --zone-name-or-id <ZONE_OCID> \
  --domain "your-domain.com" \
  --rtype A

# 3. Verify nameservers at registrar
whois your-domain.com | grep "Name Server"

# 4. Test from multiple locations
# Use online tool: https://www.whatsmydns.net/

# 5. Clear local DNS cache
sudo systemctl restart systemd-resolved  # Oracle Linux
# sudo systemd-resolve --flush-caches  # Ubuntu
```

#### Issue 9: Performance Issues

**Symptoms**: Slow response times, high CPU/memory

**Solutions**:

```bash
# 1. Check system resources
htop

# 2. Check service status
sudo systemctl status agent-comm
sudo systemctl status postgresql

# 3. Check PostgreSQL connections
psql -U agent -d agent_comm -c "SELECT count(*) FROM pg_stat_activity;"

# 4. Analyze slow queries
psql -U agent -d agent_comm -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"

# 5. Check Nginx access logs for slow requests
sudo awk '{print $NF}' /var/log/nginx/agent-comm-access.log | sort -n | tail -20

# 6. Review application logs
sudo tail -f /var/log/agent-comm/agent-comm.log

# 7. Consider scaling up OCI shape if needed
```

#### Issue 10: Memory Issues (OOM)

**Symptoms**: Service killed, out of memory errors

**Solutions**:

```bash
# 1. Check memory usage
free -h
cat /proc/meminfo

# 2. Check OOM killer logs
sudo dmesg | grep -i "out of memory"
sudo journalctl -k | grep -i oom

# 3. Adjust service memory limits
sudo vim /etc/systemd/system/agent-comm.service
# Update MemoryMax=2G to appropriate value

# 4. Configure PostgreSQL memory
sudo vim /var/lib/pgsql/data/postgresql.conf
# Set shared_buffers, effective_cache_size, etc.

# 5. Add swap space if needed
sudo dd if=/dev/zero of=/swapfile bs=1G count=4
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Diagnostic Commands

```bash
# System overview
neofetch  # or screenfetch
uname -a
cat /etc/os-release

# Service status
sudo systemctl list-units --type=service --state=running
sudo systemctl list-units --type=service --state=failed

# Network status
ss -tulpn
netstat -tulpn
ip addr show

# Disk usage
df -h
du -sh /opt/agent-comm

# Process information
ps aux | grep python
ps aux | grep postgres
top

# Recent logs
sudo journalctl -xe
sudo dmesg | tail

# Application health
curl http://localhost:8001/health
curl http://localhost:8000/health
```

### Recovery Procedures

**Full Service Recovery**:

```bash
#!/bin/bash
# Emergency Recovery Script

echo "Starting emergency recovery..."

# 1. Check and restart PostgreSQL
if ! systemctl is-active --quiet postgresql; then
    echo "PostgreSQL not running, starting..."
    sudo systemctl start postgresql
fi

# 2. Check database connectivity
if ! psql -U agent -h localhost -d agent_comm -c "SELECT 1;" &>/dev/null; then
    echo "Database connection failed, restarting PostgreSQL..."
    sudo systemctl restart postgresql
    sleep 5
fi

# 3. Check and restart agent-comm service
if ! systemctl is-active --quiet agent-comm; then
    echo "Agent Communication service not running, starting..."
    sudo systemctl start agent-comm
fi

# 4. Check health endpoint
if ! curl -f http://localhost:8001/health &>/dev/null; then
    echo "Health check failed, restarting service..."
    sudo systemctl restart agent-comm
    sleep 10
fi

# 5. Check Nginx
if ! systemctl is-active --quiet nginx; then
    echo "Nginx not running, starting..."
    sudo systemctl start nginx
fi

echo "Recovery complete. Checking status..."
sudo systemctl status postgresql --no-pager
sudo systemctl status agent-comm --no-pager
sudo systemctl status nginx --no-pager
curl -f http://localhost:8001/health
```

---

## Support and Resources

### Documentation Links

- [OCI Documentation](https://docs.oracle.com/en-us/iaas/)
- [Oracle Linux Documentation](https://docs.oracle.com/en-us/operating-systems/oracle-linux/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [Project Repository](https://github.com/your-username/agent_com)

### Useful OCI CLI Commands

```bash
# List instances
oci compute instance list --compartment-id <COMPARTMENT_OCID>

# Get instance details
oci compute instance get --instance-id <INSTANCE_OCID>

# Start/Stop instance
oci compute instance action --action START --instance-id <INSTANCE_OCID>
oci compute instance action --action STOP --instance-id <INSTANCE_OCID>

# List security lists
oci network security-list list --compartment-id <COMPARTMENT_OCID>

# Create console connection
oci compute instance-console-connection create --instance-id <INSTANCE_OCID>
```

### Monitoring

```bash
# Application health check
watch -n 5 'curl -s http://localhost:8001/health | jq'

# System resource monitoring
htop

# Log monitoring
sudo journalctl -u agent-comm -f

# Network monitoring
sudo tcpdump -i any port 8001 -n
```

---

## Appendix

### Quick Reference: Ports

| Port | Service | External Access |
|------|---------|-----------------|
| 22 | SSH | Yes (restrict IP) |
| 80 | HTTP | Yes (redirects to 443) |
| 443 | HTTPS | Yes (primary) |
| 8000 | MCP Broker | No (internal only) |
| 8001 | Communication Server | No (via Nginx) |
| 5432 | PostgreSQL | No (local only) |
| 6379 | Redis | No (local only) |

### Systemd Service Locations

| File | Location |
|------|----------|
| Service file | `/etc/systemd/system/agent-comm.service` |
| Application logs | `/var/log/agent-comm/` |
| Nginx config | `/etc/nginx/conf.d/agent-comm.conf` |
| PostgreSQL data (Ubuntu) | `/var/lib/postgresql/15/main/` |
| PostgreSQL data (Oracle Linux) | `/var/lib/pgsql/data/` |
| Application | `/opt/agent-comm/` |

### Default Credentials

| Service | Default User | Notes |
|---------|--------------|-------|
| OCI VM (Ubuntu) | `ubuntu` | sudo access |
| OCI VM (Oracle Linux) | `opc` | sudo access |
| PostgreSQL | `agent` | Change password |
| Application Admin | `admin` | Change on first login |

---

**Document Version**: 1.1.0
**Last Updated**: 2026-02-01
**OCI Region**: All regions
**Supported Images**: Ubuntu 24.04.3 LTS (Recommended), Oracle Linux 8/9

**Ubuntu Users**: For detailed Ubuntu-specific deployment instructions, see [UBUNTU_2404_SETUP.md](UBUNTU_2404_SETUP.md).

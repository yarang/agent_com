# Communication Server Deployment Quick Start

Deploy Communication Server to `oci-ajou-ec2.fcoinfup.com:8000` with systemd auto-start and auto-restart.

## Prerequisites

1. SSH access to the OCI instance
2. Python 3.12+ installed
3. PostgreSQL database running
4. `uv` package manager installed

## Deployment Steps

### 1. SSH into the Server

```bash
ssh ubuntu@oci-ajou-ec2.fcoinfup.com
```

### 2. Navigate to Application Directory

```bash
cd /home/ubuntu/agent_com
```

### 3. Update Configuration

The production configuration is already set up in `config.production.json` with:
- Port 8000
- CORS origins for `oci-ajou-ec2.fcoinfup.com`
- Production-ready settings

### 4. Generate Production Secrets

Generate secure secrets for JWT and API tokens:

```bash
# Generate JWT secret
python3 -c 'import secrets; print("JWT_SECRET=" + secrets.token_urlsafe(32))'

# Generate API token secret
python3 -c 'import secrets; print("API_TOKEN_SECRET=" + secrets.token_urlsafe(32))'
```

Update `config.production.json` with these secrets.

### 5. Deploy Using the Deployment Script

```bash
sudo ./scripts/deploy-production.sh
```

This script will:
- Create log directory at `/var/log/agent-comm`
- Install systemd service file
- Configure firewall for port 8000
- Start the service with auto-restart enabled
- Verify deployment with health check

### 6. Verify Deployment

```bash
# Check service status
sudo systemctl status agent-comm

# Check health endpoint
curl http://localhost:8000/health

# Check from external
curl http://oci-ajou-ec2.fcoinfup.com:8000/health
```

## Service Management

### Start/Stop/Restart

```bash
# Start service
sudo systemctl start agent-comm

# Stop service
sudo systemctl stop agent-comm

# Restart service
sudo systemctl restart agent-comm

# Reload service (graceful restart)
sudo systemctl reload agent-comm
```

### View Logs

```bash
# View service logs (systemd journal)
sudo journalctl -u agent-comm -f

# View application output logs
tail -f /var/log/agent-comm/output.log

# View application error logs
tail -f /var/log/agent-comm/error.log

# View recent logs
sudo journalctl -u agent-comm -n 100
```

### Check Status

```bash
# Detailed status
sudo systemctl status agent-comm

# Check if running
sudo systemctl is-active agent-comm

# Check if enabled for auto-start
sudo systemctl is-enabled agent-comm
```

## Service Configuration

The systemd service is configured with:

- **Auto-start**: Enabled (starts on boot)
- **Auto-restart**: Always restarts on failure
- **Restart delay**: 10 seconds
- **Memory limit**: 2GB
- **Log location**: `/var/log/agent-comm/`
- **Config file**: `/home/ubuntu/agent_com/config.production.json`

## Firewall Configuration

Ensure port 8000 is open in the firewall:

```bash
# Ubuntu (ufw)
sudo ufw allow 8000/tcp
sudo ufw status

# Oracle Linux (firewalld)
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
sudo firewall-cmd --list-ports
```

## OCI Security List

Ensure the OCI Security List allows inbound traffic on port 8000:

1. Go to OCI Console > Networking > Virtual Cloud Networks
2. Select your VCN > Security Lists > Default Security List
3. Add Ingress Rule:
   - Protocol: TCP
   - Source: 0.0.0.0/0
   - Destination Port: 8000

## Troubleshooting

### Service Not Starting

```bash
# Check detailed status
sudo systemctl status agent-comm

# View recent logs
sudo journalctl -u agent-comm -n 50 --no-pager

# Check application logs
tail -n 50 /var/log/agent-comm/error.log
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test database connection
psql -U agent -h localhost -d agent_comm -c "SELECT 1;"
```

### Port Already in Use

```bash
# Check what's using port 8000
sudo lsof -i :8000
sudo netstat -tulpn | grep 8000
```

### Firewall Blocking

```bash
# Test locally
curl http://localhost:8000/health

# Test from external
curl http://oci-ajou-ec2.fcoinfup.com:8000/health
```

## Health Check Endpoints

- **Health**: `http://oci-ajou-ec2.fcoinfup.com:8000/health`
- **API Docs**: `http://oci-ajou-ec2.fcoinfup.com:8000/docs`
- **Root**: `http://oci-ajou-ec2.fcoinfup.com:8000/`

## Updating the Application

```bash
cd /home/ubuntu/agent_com

# Pull latest changes
git pull

# Restart service to apply changes
sudo systemctl restart agent-comm

# Verify deployment
curl http://localhost:8000/health
```

## Database Migrations

```bash
cd /home/ubuntu/agent_com

# Run database migrations
uv run python -c "
import asyncio
from agent_comm_core.db.database import init_db
import os

async def main():
    db_url = os.getenv('DATABASE_URL', 'postgresql+asyncpg://agent:agent_password@localhost:5432/agent_comm')
    await init_db(database_url=db_url, drop_all=False)
    print('Database initialized successfully!')

asyncio.run(main())
"
```

## Monitoring

### Set up log monitoring

```bash
# Watch logs in real-time
sudo journalctl -u agent-comm -f
```

### Set up health monitoring

```bash
# Add to crontab for periodic health checks
crontab -e

# Add this line for health check every 5 minutes
*/5 * * * * curl -f http://localhost:8000/health || echo "Health check failed" | mail -s "Agent Comm Alert" admin@example.com
```

## Production Considerations

1. **Secrets Management**: Use a secrets manager (OCI Vault, HashiCorp Vault) instead of storing secrets in config files
2. **SSL/TLS**: Consider using Nginx as a reverse proxy with SSL termination for HTTPS
3. **Database Backups**: Set up automated PostgreSQL backups
4. **Monitoring**: Set up application monitoring (Prometheus, Grafana, or OCI Monitoring)
5. **Log Aggregation**: Consider centralized logging (OCI Logging, ELK stack)

## Additional Resources

- Full OCI deployment guide: [OCI_DEPLOYMENT.md](OCI_DEPLOYMENT.md)
- Development setup: [README.md](../README.md)
- API documentation: `http://oci-ajou-ec2.fcoinfup.com:8000/docs`

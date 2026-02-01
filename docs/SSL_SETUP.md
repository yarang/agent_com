# SSL Certificate Setup with Let's Encrypt

This guide explains how to set up SSL certificates using Let's Encrypt and certbot for production deployments of the AI Agent Communication System.

## Overview

The system supports two SSL certificate providers:

1. **Self-signed certificates** (default) - For development only
2. **Let's Encrypt certificates** (production) - Free, trusted SSL certificates

## Prerequisites

Before setting up Let's Encrypt SSL certificates, ensure you have:

- Domain name with DNS pointing to your server
- Port 80 and 443 open on your firewall
- Root or sudo access on the server
- Docker and Docker Compose installed (for containerized deployment)

## Quick Start

### Step 1: Initial Setup (Staging Test)

First, test with the Let's Encrypt staging environment to verify your configuration:

```bash
# For Docker deployment
./scripts/setup-ssl.sh --staging --docker --domain example.com --email admin@example.com

# For Nginx standalone deployment
./scripts/setup-ssl.sh --staging --nginx --domain example.com --email admin@example.com
```

**Why use staging?** The staging environment has no rate limits, allowing you to test your configuration without hitting Let's Encrypt's strict rate limits (5 certificates per domain per 7 days).

### Step 2: Production Deployment

Once staging is successful, obtain production certificates:

```bash
# For Docker deployment
./scripts/setup-ssl.sh --production --docker --domain example.com --email admin@example.com

# For Nginx standalone deployment
./scripts/setup-ssl.sh --production --nginx --domain example.com --email admin@example.com
```

### Step 3: Update Configuration

Edit your `config.json` to enable SSL:

```json
{
  "server": {
    "ssl": {
      "enabled": true,
      "provider": "letsencrypt",
      "cert_path": "./certificates/cert.pem",
      "key_path": "./certificates/key.pem",
      "letsencrypt": {
        "email": "admin@example.com",
        "domain": "example.com",
        "staging": false
      }
    }
  }
}
```

### Step 4: Start Services

For Docker deployment:

```bash
# Start with SSL profile
docker-compose --profile ssl up -d

# Verify certificates
docker-compose logs certbot
```

For standalone deployment:

```bash
# Restart the communication server
systemctl restart agent-comm-server
# or
./scripts/dev.sh restart
```

## Docker Deployment

### Architecture

The Docker deployment uses three services:

1. **certbot** - Obtains and renews SSL certificates
2. **nginx** - Reverse proxy with SSL termination
3. **communication-server** - Application server (behind nginx)

### Environment Variables

Create a `.env` file with the following:

```env
# Domain configuration
DOMAIN=example.com
EMAIL=admin@example.com

# SSL configuration
SSL_ENABLED=true
SSL_CERT_PATH=./certificates/cert.pem
SSL_KEY_PATH=./certificates/key.pem

# CORS configuration (update with your frontend URL)
CORS_ORIGINS=https://app.example.com
```

### Docker Compose Commands

```bash
# Start all services with SSL
docker-compose --profile ssl up -d

# Start only core services (development)
docker-compose up -d

# View logs
docker-compose logs -f nginx
docker-compose logs -f certbot

# Restart SSL services
docker-compose restart nginx certbot

# Stop SSL services
docker-compose --profile ssl down
```

## Nginx Configuration

The Nginx configuration (`nginx/nginx.conf`) provides:

- HTTP to HTTPS redirect
- Let's Encrypt ACME challenge support
- SSL termination with modern TLS settings
- WebSocket support for real-time communication
- Rate limiting for API endpoints
- Security headers (HSTS, X-Frame-Options, etc.)

### Customizing Nginx

To customize the Nginx configuration:

1. Edit `nginx/nginx.conf`
2. Replace `DOMAIN_PLACEHOLDER` with your actual domain
3. Restart the nginx container:

```bash
docker-compose restart nginx
```

## Certificate Auto-Renewal

Let's Encrypt certificates are valid for 90 days. The system includes automatic renewal:

### Docker Deployment

The certbot container runs a continuous process that:

1. Checks for certificate renewal every 12 hours
2. Renews certificates when they are within 30 days of expiry
3. Copies renewed certificates to the shared volume
4. Nginx automatically picks up the new certificates

### Standalone Deployment

A cron job is automatically configured:

```bash
# View cron job
crontab -l | grep renew-ssl

# Manual renewal test
sudo certbot renew --dry-run

# Force immediate renewal
sudo certbot renew --force-renewal
```

## Troubleshooting

### Port 80 Already in Use

```bash
# Find process using port 80
sudo lsof -ti :80

# Kill the process
sudo lsof -ti :80 | xargs sudo kill -9
```

### Certificate Fails to Obtain

1. **Check DNS propagation:**

```bash
dig +short yourdomain.com
nslookup yourdomain.com
```

2. **Check firewall:**

```bash
# Ubuntu/Debian
sudo ufw status
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# CentOS/RHEL
sudo firewall-cmd --list-all
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

3. **Check for existing services on port 80:**

```bash
sudo netstat -tulpn | grep :80
```

### Certificate Not Trusted by Browser

1. Verify you're using production (not staging) certificates:

```bash
sudo certbot certificates
```

2. Check the certificate chain:

```bash
openssl s_client -connect yourdomain.com:443 -showcerts
```

### Nginx 502 Bad Gateway

This usually means the communication-server is not accessible:

```bash
# Check communication-server status
docker-compose ps
docker-compose logs communication-server

# Check nginx configuration
docker-compose exec nginx nginx -t

# Restart nginx
docker-compose restart nginx
```

### Docker Permission Issues

```bash
# Fix certificate permissions
sudo chown -R $USER:$USER ./certificates
chmod 644 ./certificates/cert.pem
chmod 600 ./certificates/key.pem
```

## Certificate Management

### View Certificates

```bash
sudo certbot certificates
```

### Revoke Certificate

```bash
sudo certbot revoke --cert-path /etc/letsencrypt/live/example.com/cert.pem
```

### Delete Certificate

```bash
sudo certbot delete --cert-name example.com
```

## Security Best Practices

1. **Use Strong SSL Configuration** - The Nginx config uses TLS 1.2+ and secure ciphers

2. **Enable HSTS** - Already enabled in nginx.conf with 1-year max-age

3. **Implement Rate Limiting** - API rate limiting is configured at 10 requests/second

4. **Keep Certificates Updated** - Auto-renewal is enabled by default

5. **Monitor Expiry** - Set up alerts for certificate expiry:

```bash
# Add to crontab for expiry alerts (30 days before)
0 0 * * * certbot certificates | grep -q "EXPIRING" && echo "SSL certificate expiring soon" | mail -s "SSL Alert" admin@example.com
```

## Migrating from Self-Signed Certificates

If you're currently using self-signed certificates:

1. Stop all services
2. Backup existing certificates:

```bash
cp -r certificates certificates.backup
```

3. Follow the Quick Start guide above
4. Update configuration to use `letsencrypt` provider
5. Restart services

## Production Checklist

Before going live:

- [ ] DNS is correctly pointing to your server
- [ ] Ports 80 and 443 are open
- [ ] Test with staging environment first
- [ ] Update `config.json` with production values
- [ ] Set correct CORS origins
- [ ] Enable SSL in environment variables
- [ ] Test certificate auto-renewal with `--dry-run`
- [ ] Configure monitoring for certificate expiry
- [ ] Set up backup strategy for certificates
- [ ] Review and test security headers

## Additional Resources

- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [Certbot Documentation](https://certbot.eff.org/docs/)
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

## Support

For issues specific to this project, please refer to the main README.md or open an issue in the project repository.

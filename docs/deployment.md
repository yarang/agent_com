# AI Agent Communication System - Deployment Guide

This guide covers deployment of the AI Agent Communication System using Docker and Docker Compose.

## Architecture Overview

The system consists of four main services:

| Service | Port | Description |
|---------|------|-------------|
| **Communication Server** | 8001 | REST API and WebSocket server for agent communication |
| **MCP Broker** | 8000 | MCP protocol broker for inter-agent communication |
| **PostgreSQL** | 5432 | Persistent data storage |
| **Redis** (optional) | 6379 | Caching and session management |

## Quick Start

### 1. Configure Environment

Copy the example environment file and update with your settings:

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 2. Start Services

**Development mode:**

```bash
./scripts/dev.sh start
```

**Production deployment:**

```bash
./scripts/deploy.sh start
```

### 3. Verify Deployment

Check service health:

```bash
./scripts/deploy.sh health
```

## Service Endpoints

### Communication Server

- **Health Check**: http://localhost:8001/health
- **API Documentation**: http://localhost:8001/docs
- **WebSocket Meetings**: ws://localhost:8001/ws/meetings/{meeting_id}
- **WebSocket Status**: ws://localhost:8001/ws/status

### MCP Broker

- **Health Check**: http://localhost:8000/health
- **Sessions API**: http://localhost:8000/sessions
- **Protocols API**: http://localhost:8000/protocols
- **Security Status**: http://localhost:8000/security/status

## Docker Images

### Dedicated Dockerfiles

The system uses dedicated Dockerfiles for each service:

- **Dockerfile.mcp**: MCP Broker Server (port 8000)
- **Dockerfile.communication**: Communication Server (port 8001)
- **Dockerfile**: Legacy single-service Dockerfile (backward compatibility)

### Build Images

```bash
# Build specific service image
docker build -f Dockerfile.mcp -t agent-comm:mcp-broker .
docker build -f Dockerfile.communication -t agent-comm:communication-server .

# Build all images
docker-compose build
```

## Environment Variables

### Required Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://agent:password@postgres:5432/agent_comm

# Communication Server
COMMUNICATION_SERVER_URL=http://localhost:8001
PORT=8001

# MCP Broker
MCP_BROKER_HOST=0.0.0.0
MCP_BROKER_PORT=8000
COMMUNICATION_SERVER_URL=http://communication-server:8001
```

### Optional Variables

```bash
# Logging
LOG_LEVEL=INFO
MCP_BROKER_LOG_FORMAT=json

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Security
MCP_BROKER_ENABLE_AUTH=true
MCP_BROKER_AUTH_SECRET=change-me-in-production
```

## Deployment Scripts

### Development Script (scripts/dev.sh)

```bash
# Start services in background
./scripts/dev.sh start

# Start services with logs
./scripts/dev.sh up

# View logs
./scripts/dev.sh logs [service]

# Stop services
./scripts/dev.sh stop

# Run tests
./scripts/dev.sh test

# Format code
./scripts/dev.sh format

# Type check
./scripts/dev.sh typecheck

# Rebuild images
./scripts/dev.sh rebuild

# Clean up
./scripts/dev.sh cleanup
```

### Production Script (scripts/deploy.sh)

```bash
# Start all services
./scripts/deploy.sh start

# Stop all services
./scripts/deploy.sh stop

# Restart services
./scripts/deploy.sh restart

# Show status
./scripts/deploy.sh status

# View logs
./scripts/deploy.sh logs [service]

# Health check
./scripts/deploy.sh health

# Run migrations
./scripts/deploy.sh migrate

# Build images
./scripts/deploy.sh build

# Clean up
./scripts/deploy.sh cleanup
```

## Health Checks

### Manual Health Check

```bash
# Communication Server
curl http://localhost:8001/health

# MCP Broker
curl http://localhost:8000/health

# All services
./scripts/deploy.sh health
```

### Automated Health Checks

Both services include Docker health checks:

- **Interval**: 30 seconds
- **Timeout**: 10 seconds
- **Retries**: 3
- **Start period**: 10 seconds

## Networking

Services communicate via internal Docker network `agent-comm-network`:

- Communication Server accessible internally at `http://communication-server:8001`
- MCP Broker accessible internally at `http://mcp-broker:8000`

## Volumes

Persistent data is stored in named volumes:

- **postgres_data**: PostgreSQL database files
- **redis_data**: Redis persistence files (if enabled)

## Troubleshooting

### Service Not Starting

1. Check Docker is running: `docker info`
2. Check port availability: `lsof -i :8000 -i :8001`
3. View service logs: `./scripts/deploy.sh logs [service]`

### Database Connection Issues

1. Verify PostgreSQL is healthy: `docker-compose ps postgres`
2. Check DATABASE_URL in .env file
3. Run migrations: `./scripts/deploy.sh migrate`

### Health Check Failing

1. Check service logs: `docker-compose logs [service]`
2. Verify service is responding: `curl http://localhost:PORT/health`
3. Restart service: `docker-compose restart [service]`

## Production Deployment

### Security Checklist

- [ ] Change default passwords in .env
- [ ] Generate secure SECRET_KEY with `openssl rand -hex 32`
- [ ] Set MCP_BROKER_ENABLE_AUTH=true
- [ ] Restrict CORS_ORIGINS to specific domains
- [ ] Enable HTTPS/TLS for external connections
- [ ] Configure firewall rules
- [ ] Set up log aggregation
- [ ] Configure backup strategy for database

### Scaling

To scale services:

```bash
# Scale MCP Broker
docker-compose up -d --scale mcp-broker=3

# Scale Communication Server
docker-compose up -d --scale communication-server=2
```

### Monitoring

Enable monitoring and observability:

- Configure external log aggregation (ELK, CloudWatch, etc.)
- Set up metrics collection (Prometheus, Datadog, etc.)
- Configure alerting for service health
- Monitor resource usage (CPU, memory, disk)

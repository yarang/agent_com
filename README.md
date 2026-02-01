# MCP Broker Server

**Inter-Claude Code communication system using the Model Context Protocol (MCP)**

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)
[![Development Status](https://img.shields.io/badge/status-alpha-orange.svg)](https://github.com/moai/mcp-broker-server)

---

## Overview

The MCP Broker Server is a centralized communication middleware that enables multiple Claude Code instances to discover each other, negotiate communication capabilities, and exchange messages. The server implements the Model Context Protocol (MCP) standard to provide tools that Claude Code instances can invoke.

### Key Features

- **Protocol Registry** - Register and discover communication protocols with JSON Schema validation and version tracking
- **Session Manager** - Track connected sessions with automatic heartbeat monitoring and stale session detection
- **Capability Negotiator** - Automatic capability handshake with compatibility matrix computation
- **Message Router** - Point-to-point (1:1) and broadcast (1:N) message delivery with queuing
- **MCP Tools Interface** - Six standard MCP tools for all broker operations
- **Storage Layer** - In-memory storage with optional Redis support for distributed deployments
- **Security Module** - Authentication middleware with token validation and CORS support
- **Multi-Language Support** - Dashboard UI internationalization with Korean/English language toggle
- **Project Filtering UI** - Chat-like sidebar for organizing agents by project with real-time filtering
- **Message History View** - Dedicated message browser with project filtering and detail modal

---

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [MCP Tools](#mcp-tools)
- [Development](#development)
- [Testing](#testing)
- [Security](#security)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Installation

### Requirements

- Python 3.13 or higher
- uv package manager (recommended)

### Basic Installation

```bash
# Clone the repository
git clone https://github.com/moai/mcp-broker-server.git
cd mcp-broker-server

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
./scripts/install.sh

# Or manually:
# uv venv
# uv pip install -e ".[dev,redis]"

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Optional Dependencies

```bash
# Install with Redis support for distributed deployments
pip install -e ".[redis]"

# Install all dependencies
pip install -e ".[dev,redis]"
```

### Verify Installation

```bash
# Check if the server starts
python -m mcp_broker.main --help
```

---

## Quick Start

### 1. Basic Configuration

Create a `.env` file in the project root:

```bash
# Copy the example configuration
cp .env.example .env

# Edit the configuration as needed
nano .env
```

### 2. Start the Server

```bash
# Run the server directly
python -m mcp_broker.main

# Or with uvicorn for development
uvicorn mcp_broker.main:app --reload --host 0.0.0.0 --port 8000
```

The server will start on `http://localhost:8000` by default.

### 3. Verify Server Status

```bash
# Check health endpoint
curl http://localhost:8000/health

# View API documentation
open http://localhost:8000/docs
```

### 4. Using with Claude Code

Configure Claude Code to connect to the MCP Broker:

```json
{
  "mcpServers": {
    "mcp-broker": {
      "command": "python",
      "args": ["-m", "mcp_broker.main"],
      "env": {
        "MCP_BROKER_HOST": "127.0.0.1",
        "MCP_BROKER_PORT": "8000"
      }
    }
  }
}
```

---

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `MCP_BROKER_HOST` | Server host address | `0.0.0.0` | No |
| `MCP_BROKER_PORT` | Server port | `8000` | No |
| `MCP_BROKER_LOG_LEVEL` | Logging level | `INFO` | No |
| `MCP_BROKER_LOG_FORMAT` | Log format (json/text) | `json` | No |
| `MCP_BROKER_STORAGE` | Storage backend | `memory` | No |
| `MCP_BROKER_REDIS_URL` | Redis connection URL | - | Yes (for Redis) |
| `MCP_BROKER_QUEUE_CAPACITY` | Max messages per queue | `100` | No |
| `MCP_BROKER_QUEUE_WARNING` | Queue warning threshold (0-1) | `0.9` | No |
| `MCP_BROKER_HEARTBEAT_INTERVAL` | Heartbeat interval (seconds) | `30` | No |
| `MCP_BROKER_STALE_THRESHOLD` | Stale session threshold (seconds) | `30` | No |
| `MCP_BROKER_DISCONNECT_THRESHOLD` | Disconnect threshold (seconds) | `60` | No |
| `MCP_BROKER_MAX_PAYLOAD_MB` | Max payload size (MB) | `10` | No |
| `MCP_BROKER_ENABLE_AUTH` | Enable authentication | `false` | No |
| `MCP_BROKER_AUTH_SECRET` | Authentication secret | - | Yes (if auth enabled) |
| `MCP_BROKER_CORS_ORIGINS` | Allowed CORS origins (comma-separated) | `*` | No |

### Example Configuration Files

**Development (.env.dev):**
```bash
MCP_BROKER_HOST=127.0.0.1
MCP_BROKER_PORT=8000
MCP_BROKER_LOG_LEVEL=DEBUG
MCP_BROKER_STORAGE=memory
MCP_BROKER_ENABLE_AUTH=false
MCP_BROKER_CORS_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
```

**Production (.env.prod):**
```bash
MCP_BROKER_HOST=0.0.0.0
MCP_BROKER_PORT=8000
MCP_BROKER_LOG_LEVEL=INFO
MCP_BROKER_LOG_FORMAT=json
MCP_BROKER_STORAGE=redis
MCP_BROKER_REDIS_URL=redis://redis:6379/0
MCP_BROKER_ENABLE_AUTH=true
MCP_BROKER_AUTH_SECRET=<generate-secure-secret>
MCP_BROKER_CORS_ORIGINS=https://your-domain.com
```

### Generating a Secure Authentication Secret

```bash
# Generate a cryptographically secure secret
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## API Reference

### HTTP Endpoints

#### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "storage_backend": "memory",
  "active_sessions": 0,
  "authentication_enabled": false
}
```

#### List Sessions

```http
GET /sessions?status=active&include_capabilities=true
```

**Query Parameters:**
- `status` (optional): Filter by status (`active`, `stale`, `all`)
- `include_capabilities` (optional): Include full capability details

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "uuid",
      "connection_time": "2025-01-31T00:00:00Z",
      "last_heartbeat": "2025-01-31T00:00:30Z",
      "status": "active",
      "queue_size": 0,
      "capabilities": {...}
    }
  ],
  "count": 1
}
```

#### List Protocols

```http
GET /protocols?name=chat&version=1.0.0
```

**Query Parameters:**
- `name` (optional): Filter by protocol name
- `version` (optional): Filter by version

**Response:**
```json
{
  "protocols": [
    {
      "name": "chat",
      "version": "1.0.0",
      "capabilities": ["point_to_point", "broadcast"],
      "metadata": {...},
      "registered_at": "2025-01-31T00:00:00Z"
    }
  ],
  "count": 1
}
```

#### Security Status

```http
GET /security/status
```

**Response:**
```json
{
  "authentication_enabled": false,
  "cors_origins": ["*"],
  "recommendations": [
    "Enable authentication for production use",
    "Restrict CORS origins to specific domains"
  ]
}
```

#### Root Endpoint

```http
GET /
```

**Response:**
```json
{
  "name": "MCP Broker Server",
  "version": "1.0.0",
  "description": "Inter-Claude Code communication system",
  "docs": "/docs",
  "health": "/health",
  "security": "/security/status"
}
```

---

## MCP Tools

The broker exposes six MCP tools that can be invoked by Claude Code instances:

### 1. register_protocol

Register a new communication protocol with JSON Schema validation.

**Input:**
```json
{
  "name": "chat",
  "version": "1.0.0",
  "schema": {
    "type": "object",
    "properties": {
      "message": {"type": "string"},
      "sender": {"type": "string"}
    },
    "required": ["message"]
  },
  "capabilities": ["point_to_point", "broadcast"],
  "author": "Your Name",
  "description": "Chat message protocol",
  "tags": ["chat", "messaging"]
}
```

**Response:**
```json
{
  "success": true,
  "protocol": {
    "name": "chat",
    "version": "1.0.0",
    "registered_at": "2025-01-31T00:00:00Z",
    "capabilities": ["point_to_point", "broadcast"]
  }
}
```

### 2. discover_protocols

Query available protocols with optional filtering.

**Input:**
```json
{
  "name": "chat",
  "version_range": ">=1.0.0,<2.0.0",
  "tags": ["messaging"]
}
```

**Response:**
```json
{
  "protocols": [
    {
      "name": "chat",
      "version": "1.0.0",
      "capabilities": ["point_to_point", "broadcast"],
      "metadata": {...}
    }
  ],
  "count": 1
}
```

### 3. negotiate_capabilities

Perform capability negotiation handshake with a target session.

**Input:**
```json
{
  "target_session_id": "uuid",
  "required_protocols": [
    {"name": "chat", "version": "1.0.0"}
  ]
}
```

**Response:**
```json
{
  "compatible": true,
  "supported_protocols": {"chat": "1.0.0"},
  "feature_intersections": ["point_to_point"],
  "unsupported_features": [],
  "incompatibilities": [],
  "suggestion": null
}
```

### 4. send_message

Send a point-to-point message to a specific session.

**Input:**
```json
{
  "recipient_id": "uuid",
  "protocol_name": "chat",
  "protocol_version": "1.0.0",
  "payload": {
    "message": "Hello!",
    "sender": "Session A"
  },
  "priority": "normal",
  "ttl": 3600
}
```

**Response:**
```json
{
  "success": true,
  "message_id": "uuid",
  "delivered_at": "2025-01-31T00:00:00Z"
}
```

### 5. broadcast_message

Broadcast a message to all compatible sessions.

**Input:**
```json
{
  "protocol_name": "chat",
  "protocol_version": "1.0.0",
  "payload": {
    "message": "Broadcast announcement",
    "sender": "System"
  },
  "capability_filter": {"supports_broadcast": true},
  "priority": "normal"
}
```

**Response:**
```json
{
  "success": true,
  "delivery_count": 3,
  "recipients": {
    "delivered": ["uuid1", "uuid2", "uuid3"],
    "failed": [],
    "skipped": []
  },
  "reason": null
}
```

### 6. list_sessions

List all active sessions with their capabilities.

**Input:**
```json
{
  "status_filter": "active",
  "include_capabilities": true
}
```

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "uuid",
      "connection_time": "2025-01-31T00:00:00Z",
      "last_heartbeat": "2025-01-31T00:00:30Z",
      "status": "active",
      "queue_size": 0,
      "capabilities": {...}
    }
  ],
  "count": 1
}
```

---

## Multi-Project Support

The MCP Broker Server supports multi-project deployments, enabling complete isolation of protocols, sessions, and messages between different projects.

### Enabling Multi-Project Mode

Set the environment variable to enable multi-project support:

```bash
MCP_BROKER_ENABLE_MULTI_PROJECT=true
```

### Project Identification

Projects are identified using one of the following methods (in priority order):

1. **X-Project-ID Header** (recommended)
   ```bash
   curl -H "X-Project-ID: myproject" http://localhost:8000/protocols
   ```

2. **API Key Prefix**
   ```bash
   # API key format: {project_id}_{key_id}_{secret}
   curl -H "X-API-Key: myproject_admin_abc123def..." http://localhost:8000/protocols
   ```

### Project MCP Tools

In addition to the six core MCP tools, the broker provides four project management tools when multi-project mode is enabled:

#### 7. create_project

Create a new project with generated API keys.

**Input:**
```json
{
  "project_id": "myproject",
  "name": "My Project",
  "description": "Project description",
  "max_sessions": 50,
  "allow_cross_project": false,
  "discoverable": true
}
```

**Response:**
```json
{
  "success": true,
  "project": {
    "project_id": "myproject",
    "name": "My Project",
    "status": "active"
  },
  "credentials": {
    "project_id": "myproject",
    "api_key": "myproject_key_xxx..."
  }
}
```

#### 8. list_projects

List discoverable projects with public metadata.

**Input:**
```json
{
  "name_filter": "test",
  "include_inactive": false,
  "include_stats": false
}
```

#### 9. get_project_info

Get detailed project information.

**Input:**
```json
{
  "project_id": "myproject",
  "include_config": true,
  "include_permissions": true
}
```

#### 10. rotate_project_keys

Rotate project API keys (admin only).

**Input:**
```json
{
  "project_id": "myproject",
  "grace_period_seconds": 300
}
```

### Project Isolation

- **Protocol Isolation**: Each project has its own protocol registry
- **Session Isolation**: Sessions belong to specific projects and can only interact within their project
- **Message Isolation**: Messages are routed only within the originating project
- **Storage Isolation**: All project data is stored in separate namespaces

### Cross-Project Communication

Cross-project communication is opt-in and requires explicit configuration:

```python
# In project configuration
config = ProjectConfig(
    allow_cross_project=True,  # Enable cross-project
    cross_project_permissions=[
        CrossProjectPermission(
            target_project_id="other-project",
            allowed_protocols=["chat", "file"],
            message_rate_limit=100
        )
    ]
)
```

### Backward Compatibility

Single-project deployments are fully supported through:
- Default project creation ("default") with auto-generated API key
- All operations work without `project_id` parameter (defaults to "default")
- Existing data automatically migrates to default project namespace

---

## Dashboard Features

The Communication Server dashboard provides a web-based interface for monitoring and managing agents in real-time.

### Multi-Language Support

The dashboard supports internationalization (i18n) with Korean and English languages.

#### Language Toggle

- Language selector in the dashboard header (Korean/English)
- Persistent language preference in browser localStorage
- Automatic browser language detection
- Real-time UI translation without page refresh

#### Language API

**Get Supported Languages:**
```http
GET /api/v1/i18n/languages
```

**Response:**
```json
{
  "languages": [
    {"code": "ko", "name": "Korean", "native_name": "한국어"},
    {"code": "en", "name": "English", "native_name": "English"}
  ],
  "default": "ko"
}
```

**Get Translations:**
```http
GET /api/v1/i18n/{language}
```

**Parameters:**
- `language` (path): Language code (ko, en)

**Response:**
```json
{
  "language": "ko",
  "translations": {
    "dashboard": {
      "title": "AI Agent Communication",
      "subtitle": "Real-time Status Board"
    },
    "stats": {
      "totalAgents": "전체 에이전트",
      "activeAgents": "활성화 에이전트"
    }
  },
  "version": "1.0.0"
}
```

#### JavaScript Integration

```javascript
// Get translation
const text = i18n.t('stats.totalAgents');

// Set language
await i18n.setLanguage('en');

// Get current language
const currentLang = i18n.getCurrentLanguage();
```

### Project Filtering UI

The dashboard provides a chat-like sidebar for organizing and filtering agents by project.

#### Sidebar Features

- **Project Channels**: Visual list of projects as selectable channels
- **Agent Counts**: Real-time count of agents per project
- **Online Indicators**: Visual status indicators for active projects
- **Keyboard Shortcuts**: Cmd/Ctrl + 1-9 for quick project switching
- **Collapsible Sidebar**: Toggle to maximize content area
- **Persistent Selection**: Last selected project saved in localStorage

#### Projects API

**List Projects:**
```http
GET /api/v1/projects
```

**Response:**
```json
{
  "projects": [
    {
      "project_id": "myproject",
      "name": "My Project",
      "agent_count": 5,
      "active_count": 3,
      "is_online": true
    },
    {
      "project_id": null,
      "name": "All Agents",
      "agent_count": 10,
      "active_count": 5,
      "is_online": true
    }
  ]
}
```

**Get Project Agents:**
```http
GET /api/v1/projects/{project_id}/agents
```

**Parameters:**
- `project_id` (path): Project ID or "_none" for agents without a project

**Response:**
```json
{
  "project_id": "myproject",
  "agents": [
    {
      "agent_id": "uuid",
      "full_id": "FrontendExpert",
      "nickname": "FrontendExpert",
      "status": "online",
      "capabilities": ["code", "review"],
      "last_seen": "2026-02-01T12:00:00Z",
      "current_meeting": null,
      "project_id": "myproject"
    }
  ]
}
```

### Message History View

The dashboard includes a dedicated message browser for viewing and filtering communication history.

#### Message List Features

- **Reverse Chronological Order**: Newest messages displayed first
- **Project Filtering**: Filter messages by project
- **Infinite Scroll**: Automatically load older messages as you scroll
- **Message Detail Modal**: View full message content and metadata
- **Real-time Updates**: New messages appear automatically via WebSocket
- **Empty/Error States**: Helpful messages when no messages exist

#### Messages API

**List Messages:**
```http
GET /api/v1/messages?project_id={project_id}&limit=50&offset=0
```

**Query Parameters:**
- `project_id` (optional): Filter by project ID
- `from_agent` (optional): Filter by sender agent
- `to_agent` (optional): Filter by recipient agent
- `limit` (optional): Messages per page (default: 50, max: 200)
- `offset` (optional): Pagination offset (default: 0)

**Response:**
```json
[
  {
    "message_id": "uuid",
    "from_agent": "FrontendExpert",
    "to_agent": "BackendDev",
    "timestamp": "2026-02-01T12:00:00Z",
    "content_preview": "Here is the API payload...",
    "project_id": "myproject",
    "message_type": "direct"
  }
]
```

**Get Message Detail:**
```http
GET /api/v1/messages/{message_id}
```

**Response:**
```json
{
  "message_id": "uuid",
  "from_agent": "FrontendExpert",
  "to_agent": "BackendDev",
  "timestamp": "2026-02-01T12:00:00Z",
  "content": "Full message content here...",
  "content_type": "text/plain",
  "project_id": "myproject",
  "message_type": "direct",
  "direction": "outbound",
  "correlation_id": null,
  "metadata": {}
}
```

---

## Development

### Project Structure

```
mcp-broker-server/
├── src/mcp_broker/
│   ├── core/           # Configuration, logging, security
│   ├── models/         # Pydantic data models
│   ├── protocol/       # Protocol registry
│   ├── session/        # Session management
│   ├── negotiation/    # Capability negotiation
│   ├── routing/        # Message routing
│   ├── storage/        # Storage abstraction
│   ├── mcp/            # MCP server and tools
│   └── main.py         # FastAPI application
├── tests/              # Unit and integration tests
├── docs/               # Documentation
└── pyproject.toml      # Project configuration
```

### Code Quality Tools

```bash
# Format code with ruff
uv run ruff format src/ tests/

# Lint with ruff
uv run ruff check src/ tests/

# Auto-fix linting issues
uv run ruff check --fix src/ tests/

# Type check with mypy
uv run mypy src/

# Run all quality checks
uv run ruff format src/ tests/ && uv run ruff check src/ tests/ && uv run mypy src/
```

### Development Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes and run tests**
   ```bash
   pytest
   ```

3. **Ensure quality gates pass**
   ```bash
   black src/ tests/ && ruff check src/ tests/ && mypy src/
   ```

4. **Commit with conventional commit message**
   ```bash
   git commit -m "feat: add new protocol versioning support"
   ```

5. **Push and create pull request**
   ```bash
   git push origin feature/your-feature-name
   ```

---

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src/mcp_broker --cov-report=html

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m slow          # Slow tests only

# Run specific test file
pytest tests/unit/test_protocol_registry.py

# Run with verbose output
pytest -v
```

### Test Coverage

```bash
# Generate coverage report
pytest --cov=src/mcp_broker --cov-report=term-missing

# Open HTML coverage report
open htmlcov/index.html
```

**Target Coverage:** >= 85%

### Writing Tests

```python
# tests/unit/test_example.py
import pytest
from mcp_broker.protocol.registry import ProtocolRegistry

@pytest.mark.asyncio
async def test_register_protocol():
    registry = ProtocolRegistry()
    protocol = ProtocolDefinition(
        name="test",
        version="1.0.0",
        schema={"type": "object"},
        capabilities=["point_to_point"]
    )
    result = await registry.register(protocol)
    assert result.name == "test"
```

---

## Security

### Authentication

The broker supports token-based authentication. Enable it in production:

```bash
# Enable authentication
MCP_BROKER_ENABLE_AUTH=true
MCP_BROKER_AUTH_SECRET=<your-secure-secret>
```

### Making Authenticated Requests

```bash
# Using header
curl -H "X-API-Key: your-secret" http://localhost:8000/sessions

# Using cookie
curl --cookie "api_key=your-secret" http://localhost:8000/sessions
```

### CORS Configuration

Restrict CORS origins in production:

```bash
MCP_BROKER_CORS_ORIGINS=https://your-domain.com,https://app.your-domain.com
```

### Security Best Practices

1. **Always enable authentication in production**
2. **Use strong, randomly generated secrets**
3. **Restrict CORS origins to specific domains**
4. **Use HTTPS in production**
5. **Keep dependencies updated**
6. **Review security logs regularly**

---

## Deployment

### Cloud Platform Guides

- [Oracle Cloud Infrastructure (OCI) Deployment Guide](docs/OCI_DEPLOYMENT.md) - Complete guide for deploying on OCI VM instances with Oracle Linux
- [General Deployment Guide](docs/deployment.md) - Platform-agnostic deployment instructions
- [SSL/TLS Setup Guide](docs/SSL_SETUP.md) - SSL certificate configuration for production

### Docker Deployment

```bash
# Build the image
docker build -t mcp-broker-server .

# Run the container
docker run -d \
  --name mcp-broker \
  -p 8000:8000 \
  --env-file .env.prod \
  mcp-broker-server
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'
services:
  broker:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MCP_BROKER_STORAGE=redis
      - MCP_BROKER_REDIS_URL=redis://redis:6379/0
      - MCP_BROKER_ENABLE_AUTH=true
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

```bash
# Start with Docker Compose
docker-compose up -d
```

### Production Checklist

- [ ] Enable authentication with strong secret
- [ ] Configure Redis for persistence
- [ ] Set appropriate CORS origins
- [ ] Use HTTPS with reverse proxy
- [ ] Configure log aggregation
- [ ] Set up monitoring and alerts
- [ ] Review queue capacity settings
- [ ] Test failover scenarios

---

## Troubleshooting

### Common Issues

**Server won't start**
```bash
# Check if port is already in use
lsof -i :8000

# Use a different port
MCP_BROKER_PORT=8001 python -m mcp_broker.main
```

**Redis connection fails**
```bash
# Check Redis is running
redis-cli ping

# Verify connection string
MCP_BROKER_REDIS_URL=redis://localhost:6379/0
```

**Authentication failures**
```bash
# Verify auth is enabled
curl http://localhost:8000/security/status

# Check secret is set
echo $MCP_BROKER_AUTH_SECRET
```

**Sessions going stale**
```bash
# Increase heartbeat thresholds
MCP_BROKER_STALE_THRESHOLD=60
MCP_BROKER_DISCONNECT_THRESHOLD=120
```

### Debug Mode

```bash
# Enable debug logging
MCP_BROKER_LOG_LEVEL=DEBUG python -m mcp_broker.main

# Check logs for errors
tail -f logs/mcp-broker.log
```

### Getting Help

- Check the [API documentation](docs/api.md)
- Review [architecture docs](docs/architecture.md)
- Open an issue on [GitHub](https://github.com/moai/mcp-broker-server/issues)

---

## Contributing

We welcome contributions! Please follow these guidelines:

1. **Code Style**
   - Follow PEP 8
   - Use Black for formatting
   - Add type hints
   - Write docstrings

2. **Testing**
   - Add tests for new features
   - Ensure coverage >= 85%
   - All tests must pass

3. **Commit Messages**
   - Use conventional commits
   - Examples: `feat:`, `fix:`, `docs:`, `test:`

4. **Pull Requests**
   - Describe your changes
   - Link related issues
   - Ensure CI passes

---

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

---

## Links

- [Documentation](docs/)
- [API Reference](docs/api.md)
- [Architecture](docs/architecture.md)
- [GitHub Repository](https://github.com/moai/mcp-broker-server)
- [Issue Tracker](https://github.com/moai/mcp-broker-server/issues)
- [MCP Specification](https://modelcontextprotocol.io/)

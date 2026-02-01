# Project Structure

MCP Broker Server - Code organization and layout

---

## Directory Structure

```
mcp-broker-server/
├── .claude/                    # Claude Code configuration
│   ├── agents/                 # Agent definitions
│   ├── commands/               # Slash commands
│   ├── skills/                 # Skills library
│   └── rules/                  # Execution rules
├── .github/                    # GitHub configuration
│   └── workflows/              # CI/CD workflows
├── .moai/                      # MoAI configuration
│   ├── config/                 # Project configuration
│   │   └── sections/           # Configuration sections
│   ├── project/                # Project documentation
│   │   ├── product.md          # Product overview
│   │   ├── structure.md        # This file
│   │   └── tech.md             # Technical stack
│   └── specs/                  # Specification documents
│       └── SPEC-MCP-BROKER-001/
│           ├── spec.md         # Requirements specification
│           ├── plan.md         # Implementation plan
│           └── acceptance.md   # Acceptance criteria
├── docs/                       # User documentation
│   ├── api.md                  # API reference
│   └── architecture.md         # Architecture documentation
├── src/mcp_broker/             # Source code
│   ├── __init__.py
│   ├── __main__.py             # Entry point for python -m
│   ├── main.py                 # FastAPI application
│   ├── core/                   # Core components
│   │   ├── __init__.py
│   │   ├── config.py           # Configuration management
│   │   ├── logging.py          # Structured logging
│   │   └── security.py         # Authentication middleware
│   ├── models/                 # Pydantic data models
│   │   ├── __init__.py
│   │   ├── protocol.py         # Protocol models
│   │   ├── session.py          # Session models
│   │   └── message.py          # Message models
│   ├── protocol/               # Protocol registry
│   │   ├── __init__.py
│   │   └── registry.py         # ProtocolRegistry implementation
│   ├── session/                # Session management
│   │   ├── __init__.py
│   │   └── manager.py          # SessionManager implementation
│   ├── negotiation/            # Capability negotiation
│   │   ├── __init__.py
│   │   └── negotiator.py       # CapabilityNegotiator implementation
│   ├── routing/                # Message routing
│   │   ├── __init__.py
│   │   └── router.py           # MessageRouter implementation
│   ├── storage/                # Storage abstraction
│   │   ├── __init__.py
│   │   ├── interface.py        # Storage interface
│   │   ├── memory.py           # In-memory storage
│   │   └── redis.py            # Redis storage (optional)
│   └── mcp/                    # MCP server and tools
│       ├── __init__.py
│       ├── server.py           # MCPServer implementation
│       └── tools.py            # MCP tool definitions
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── conftest.py             # Pytest fixtures
│   ├── unit/                   # Unit tests
│   │   ├── test_protocol_registry.py
│   │   ├── test_session_manager.py
│   │   ├── test_capability_negotiator.py
│   │   ├── test_message_router.py
│   │   └── test_security.py
│   ├── integration/            # Integration tests
│   │   ├── test_mcp_tools.py
│   │   ├── test_http_endpoints.py
│   │   └── test_end_to_end.py
│   └── load/                   # Load tests
│       └── test_concurrent_sessions.py
├── .env                        # Environment configuration (local)
├── .env.example                # Environment template
├── .gitignore                  # Git ignore rules
├── .mcp.json                   # MCP configuration
├── .python-version             # Python version pin
├── CHANGELOG.md                # Version history
├── CLAUDE.md                   # Claude Code instructions
├── Dockerfile                  # Container image definition
├── docker-compose.yml          # Development environment
├── pyproject.toml              # Project configuration
├── README.md                   # Project documentation
└── uv.lock                     # Dependency lock file
```

---

## Component Overview

### Core Components (`src/mcp_broker/core/`)

**config.py** - Configuration management
- Environment-based configuration
- Pydantic settings model
- Validation and defaults

**logging.py** - Structured logging
- JSON and text formatters
- Log level configuration
- Sensitive data redaction

**security.py** - Authentication and security
- Token validation middleware
- CORS handling
- Security context management

### Data Models (`src/mcp_broker/models/`)

Pydantic models for type-safe data structures:

- **protocol.py** - ProtocolDefinition, ProtocolInfo, ProtocolMetadata
- **session.py** - Session, SessionCapabilities, SessionStatus
- **message.py** - Message, MessageHeaders, DeliveryResult

### Business Logic Components

**Protocol Registry** (`src/mcp_broker/protocol/`)
- Protocol registration and discovery
- JSON Schema validation
- Version management

**Session Manager** (`src/mcp_broker/session/`)
- Session lifecycle management
- Heartbeat monitoring
- Message queuing

**Capability Negotiator** (`src/mcp_broker/negotiation/`)
- Compatibility checking
- Feature intersection
- Incompatibility reporting

**Message Router** (`src/mcp_broker/routing/`)
- Point-to-point routing
- Broadcast routing
- Delivery management

### Storage Layer (`src/mcp_broker/storage/`)

Abstracted storage with pluggable backends:

- **interface.py** - StorageBackend protocol
- **memory.py** - In-memory implementation
- **redis.py** - Redis implementation

### MCP Integration (`src/mcp_broker/mcp/`)

- **server.py** - MCPServer implementation and lifecycle
- **tools.py** - Six MCP tools for broker operations

### API Layer (`src/mcp_broker/main.py`)

FastAPI application with HTTP endpoints:
- Health check
- Session listing
- Protocol listing
- Security status

---

## File Organization Principles

### 1. Domain-Driven Structure

Components are organized by domain boundaries:
- `protocol/` - Protocol-related logic
- `session/` - Session-related logic
- `negotiation/` - Negotiation logic
- `routing/` - Routing logic

### 2. Layered Architecture

```
┌─────────────────────────────────────┐
│         API Layer (FastAPI)         │  ← HTTP endpoints
├─────────────────────────────────────┤
│       MCP Layer (MCP Tools)         │  ← MCP interface
├─────────────────────────────────────┤
│      Business Logic Layer           │  ← Core components
│  (Protocol, Session, Routing, etc)  │
├─────────────────────────────────────┤
│         Data Models Layer           │  ← Pydantic models
├─────────────────────────────────────┤
│        Storage Layer                │  ← Persistence
└─────────────────────────────────────┘
```

### 3. Dependency Flow

Dependencies flow inward:
- API depends on MCP layer
- MCP layer depends on business logic
- Business logic depends on models and storage

### 4. Testing Structure

Tests mirror source structure:
- `tests/unit/` - Component tests
- `tests/integration/` - Cross-component tests
- `tests/load/` - Performance tests

---

## Import Patterns

### Absolute Imports

Use absolute imports for clarity:

```python
# Correct
from mcp_broker.core.config import get_config
from mcp_broker.protocol.registry import ProtocolRegistry
from mcp_broker.models.protocol import ProtocolDefinition

# Avoid relative imports
from ..core.config import get_config
```

### Type Hints

All public functions have type hints:

```python
async def register(
    self,
    protocol: ProtocolDefinition,
) -> ProtocolInfo:
    ...
```

### Docstrings

Google-style docstrings for documentation:

```python
async def register(
    self,
    protocol: ProtocolDefinition,
) -> ProtocolInfo:
    """Register a new protocol.

    Args:
        protocol: Protocol definition to register

    Returns:
        ProtocolInfo with registration details

    Raises:
        ProtocolAlreadyExists: If protocol already registered
    """
```

---

## Configuration Files

### pyproject.toml

Project metadata, dependencies, and tool configuration:
- Build system (setuptools)
- Project information (name, version, authors)
- Dependencies (core, dev, optional)
- Tool configuration (black, ruff, mypy, pytest)

### .env / .env.example

Environment variables for configuration:
- Server settings (host, port)
- Logging (level, format)
- Storage (backend, Redis URL)
- Security (auth, CORS)
- Session settings (heartbeat, thresholds)

### .mcp.json

MCP server configuration for Claude Code integration.

### .gitignore

Files excluded from version control:
- Python cache (__pycache__, *.pyc)
- Virtual environments (.venv, venv)
- IDE files (.vscode, .idea)
- Local configuration (.env)
- Build artifacts (dist, build, *.egg-info)
- Test coverage (htmlcov, .coverage)

---

## Related Documentation

- [Product Overview](product.md) - Product description and features
- [Technical Stack](tech.md) - Technologies and dependencies
- [README.md](../../README.md) - Project overview
- [Architecture](../../docs/architecture.md) - System architecture

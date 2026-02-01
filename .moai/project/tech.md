# Technical Stack

MCP Broker Server - Technologies and dependencies

---

## Overview

The MCP Broker Server is built with Python 3.11+ using modern async frameworks and libraries. The project follows a modular architecture with clear separation of concerns.

---

## Core Technologies

### Python Runtime

**Version:** 3.11, 3.12, 3.13

**Key Features Used:**
- Async/await for non-blocking I/O
- Type hints for static analysis
- Dataclasses for configuration
- Context managers for resource management

**Why Python:**
- Native MCP SDK support
- Excellent async ecosystem
- Strong type checking with mypy
- Wide library ecosystem

### Web Framework

**FastAPI** (>= 0.115.0)

**Purpose:** HTTP API and server endpoints

**Key Features:**
- Automatic OpenAPI documentation
- Pydantic integration for validation
- Async request handling
- CORS middleware
- Dependency injection

**Usage:**
- Health check endpoint
- Session listing API
- Protocol discovery API
- Security status endpoint
- Interactive documentation (/docs)

### ASGI Server

**Uvicorn** (>= 0.32.0)

**Purpose:** ASGI server for FastAPI

**Key Features:**
- High performance (uvloop)
- HTTP/1.1 and WebSocket support
- Hot reload in development
- Process management

**Usage:**
- Development server with auto-reload
- Production server with proper configuration

---

## MCP Integration

### MCP SDK

**mcp** (>= 1.0.0)

**Purpose:** Official Model Context Protocol Python SDK

**Key Features:**
- Server implementation patterns
- Tool definition interface
- Message handling
- JSON-RPC protocol

**Usage:**
- MCPServer base class
- Tool registration
- Message routing
- Lifecycle management

---

## Data Validation

### Pydantic

**pydantic** (>= 2.9.0)

**Purpose:** Data validation and settings management

**Key Features:**
- Runtime type checking
- JSON Schema generation
- Settings management
- Fast serialization

**Usage:**
- All data models (Protocol, Session, Message)
- Configuration validation
- Request/response validation
- JSON Schema export

### JSON Schema

**jsonschema** (>= 4.0.0)

**Purpose:** JSON Schema validation for protocol definitions

**Key Features:**
- Draft 7 support
- Detailed validation errors
- Schema composition

**Usage:**
- Protocol schema validation
- Message payload validation
- Error reporting

---

## Version Management

### Semver

**semver** (>= 3.0.0)

**Purpose:** Semantic versioning parsing and comparison

**Key Features:**
- Version parsing
- Range matching
- Comparison operations

**Usage:**
- Protocol version validation
- Version range queries
- Compatibility checking

---

## Storage

### In-Memory (Default)

**Built-in Python collections**

**Purpose:** Development and single-server deployments

**Components:**
- `dict` for protocol and session storage
- `collections.deque` for message queues

**Benefits:**
- Fast access (no network I/O)
- No external dependencies
- Simple debugging

**Limitations:**
- Not persistent
- Not scalable
- Lost on restart

### Redis (Optional)

**redis** (>= 5.0.0)

**Purpose:** Distributed storage backend

**Key Features:**
- Persistent storage
- Distributed locking
- Pub/sub support
- Automatic expiration

**Usage:**
- Multi-server deployments
- Message persistence
- Shared state

**Configuration:**
```python
MCP_BROKER_STORAGE=redis
MCP_BROKER_REDIS_URL=redis://localhost:6379/0
```

---

## Logging

### Structured Logging

**Built-in logging module with custom formatters**

**Purpose:** Structured logging for observability

**Features:**
- JSON format for production
- Text format for development
- Log level filtering (DEBUG, INFO, WARNING, ERROR)
- Sensitive data redaction
- Request ID tracking

**Configuration:**
```python
MCP_BROKER_LOG_LEVEL=INFO
MCP_BROKER_LOG_FORMAT=json
```

---

## Security

### Authentication

**Built-in secrets module**

**Purpose:** Token-based authentication

**Features:**
- Constant-time comparison (timing-attack safe)
- API key validation via header or cookie
- Configurable authentication enable/disable

**Configuration:**
```python
MCP_BROKER_ENABLE_AUTH=true
MCP_BROKER_AUTH_SECRET=<secure-secret>
```

### CORS

**FastAPI CORSMiddleware**

**Purpose:** Cross-origin resource sharing

**Features:**
- Configurable allowed origins
- Credentials support
- Pre-flight handling

**Configuration:**
```python
MCP_BROKER_CORS_ORIGINS=http://localhost:8000,https://your-domain.com
```

---

## Development Tools

### Code Formatting

**Black** (>= 24.0.0)

**Purpose:** Code formatting

**Configuration:**
- Line length: 100 characters
- Target Python: 3.11
- Exclude: tests, build artifacts

**Usage:**
```bash
black src/ tests/
```

### Linting

**Ruff** (>= 0.8.0)

**Purpose:** Fast Python linter

**Rules Enabled:**
- pycodestyle (E, W)
- Pyflakes (F)
- isort (I)
- flake8-bugbear (B)
- flake8-comprehensions (C4)
- pyupgrade (UP)
- flake8-unused-arguments (ARG)
- flake8-simplify (SIM)

**Usage:**
```bash
ruff check src/ tests/
```

### Type Checking

**mypy** (>= 1.0.0)

**Purpose:** Static type checking

**Configuration:**
- Python 3.11+ target
- Strict mode enabled
- Disallow untyped definitions
- Warn on redundant casts

**Usage:**
```bash
mypy src/
```

---

## Testing

### Test Framework

**pytest** (>= 8.0.0)

**Purpose:** Testing framework

**Features:**
- Async test support (pytest-asyncio)
- Coverage reporting (pytest-cov)
- Fixture system
- Marker support (unit, integration, load)

**Usage:**
```bash
pytest                    # Run all tests
pytest -m unit            # Unit tests only
pytest -m integration     # Integration tests only
pytest --cov              # With coverage
```

### Test Coverage

**pytest-cov** (>= 6.0.0)

**Purpose:** Coverage reporting

**Target:** 85% coverage

**Usage:**
```bash
pytest --cov=src/mcp_broker --cov-report=html
```

### HTTP Testing

**httpx** (>= 0.28.0)

**Purpose:** Async HTTP client for testing

**Features:**
- Async request support
- Timeout handling
- Exception classes

---

## Packaging

### Build System

**setuptools** (>= 61.0)

**Purpose:** Package building and distribution

**Configuration:** pyproject.toml

**Usage:**
```bash
python -m build
```

### Package Manager

**uv** (recommended) or **pip**

**Purpose:** Dependency management

**Benefits of uv:**
- Fast installation
- Lock file support
- Dependency resolution

---

## Containerization

### Docker

**Purpose:** Container image for deployment

**Base Image:** python:3.13-slim

**Features:**
- Multi-stage build
- Minimal image size
- Non-root user
- Health check

**Usage:**
```bash
docker build -t mcp-broker-server .
docker run -p 8000:8000 mcp-broker-server
```

### Docker Compose

**Purpose:** Development environment

**Services:**
- broker - MCP Broker Server
- redis - Redis storage

**Usage:**
```bash
docker-compose up -d
```

---

## Documentation

### Markdown

**Purpose:** Project documentation

**Files:**
- README.md - Project overview
- CHANGELOG.md - Version history
- docs/api.md - API reference
- docs/architecture.md - System architecture
- .moai/project/*.md - Project docs

### Mermaid Diagrams

**Purpose:** Architecture diagrams

**Usage:**
- System architecture
- Component interactions
- Data flows
- State diagrams

---

## CI/CD

### GitHub Actions

**Purpose:** Automated testing and deployment

**Workflows:**
- Test suite on push/PR
- Coverage reporting
- Linting and type checking
- Docker image build

---

## Dependencies Summary

### Production Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| mcp | >= 1.0.0 | MCP SDK |
| fastapi | >= 0.115.0 | Web framework |
| pydantic | >= 2.9.0 | Validation |
| jsonschema | >= 4.0.0 | Schema validation |
| uvicorn | >= 0.32.0 | ASGI server |
| semver | >= 3.0.0 | Versioning |
| python-dotenv | >= 1.0.0 | Configuration |

### Optional Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| redis | >= 5.0.0 | Distributed storage |

### Development Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| pytest | >= 8.0.0 | Test framework |
| pytest-asyncio | >= 0.24.0 | Async tests |
| pytest-cov | >= 6.0.0 | Coverage |
| httpx | >= 0.28.0 | HTTP testing |
| ruff | >= 0.8.0 | Linting |
| black | >= 24.0.0 | Formatting |
| mypy | >= 1.0.0 | Type checking |
| pytest-mock | >= 3.14.0 | Mocking |

---

## Technology Choices Rationale

### Why FastAPI?

1. **Async-native** - Built on Starlette for async I/O
2. **Type-safe** - Pydantic integration for validation
3. **Auto-docs** - OpenAPI/Swagger out of the box
4. **Modern** - Active development and community

### Why Pydantic?

1. **Runtime validation** - Catch errors early
2. **Type safety** - Full type hint support
3. **JSON Schema** - Automatic schema generation
4. **Performance** - Rust-based validation core

### Why Redis (optional)?

1. **Persistence** - Survive server restarts
2. **Scalability** - Support distributed deployments
3. **Maturity** - Battle-tested and reliable
4. **Features** - Pub/sub, expiration, locking

### Why pytest?

1. **Async support** - pytest-asyncio for async tests
2. **Fixtures** - Powerful fixture system
3. **Plugins** - Coverage, mocking, profiling
4. **Community** - Large ecosystem and support

---

## Related Documentation

- [Product Overview](product.md) - Product description
- [Project Structure](structure.md) - Code organization
- [README.md](../../README.md) - Quick start guide
- [Architecture](../../docs/architecture.md) - System design

# Changelog

All notable changes to the MCP Broker Server project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2025-01-31

### Added

#### Core Components
- **Protocol Registry** - Register and discover communication protocols with JSON Schema validation
  - Semantic versioning support
  - Protocol discovery with filtering by name, version range, and tags
  - Duplicate registration prevention

- **Session Manager** - Track connected Claude Code instances
  - Unique session ID assignment (UUID)
  - Session state tracking (active, stale, disconnected)
  - Automatic heartbeat monitoring (30s stale threshold, 60s disconnect)
  - Message queuing for offline recipients (configurable capacity)
  - Graceful session disconnection

- **Capability Negotiator** - Automatic compatibility checking
  - Handshake between sessions
  - Compatibility matrix computation
  - Feature intersection identification
  - Incompatibility reporting with upgrade suggestions

- **Message Router** - Message delivery between sessions
  - Point-to-point (1:1) messaging
  - Broadcast (1:N) messaging to compatible sessions
  - Message queuing for offline recipients
  - Priority levels (low, normal, high, urgent)
  - Time-to-live (TTL) support

#### MCP Tools Interface
Six standard MCP tools for broker operations:
1. `register_protocol` - Register communication protocols
2. `discover_protocols` - Query available protocols
3. `negotiate_capabilities` - Perform capability handshake
4. `send_message` - Send point-to-point messages
5. `broadcast_message` - Broadcast to compatible sessions
6. `list_sessions` - List active sessions

#### HTTP API
- `GET /health` - Health check endpoint
- `GET /sessions` - List sessions via HTTP
- `GET /protocols` - List protocols via HTTP
- `GET /security/status` - Security configuration and recommendations
- `GET /` - Root endpoint with server information
- `GET /docs` - Interactive API documentation (FastAPI auto-docs)

#### Storage Layer
- **In-Memory Storage** - Default storage backend for development
- **Redis Storage** - Optional distributed storage backend
- **Storage Abstraction** - Unified interface for pluggable backends

#### Security Module
- **Authentication Middleware** - Token-based API authentication
  - API key validation via header or cookie
  - Constant-time comparison for timing-attack prevention
  - Configurable authentication enable/disable

- **CORS Support** - Cross-origin resource sharing configuration
  - Configurable allowed origins
  - Credentials support
  - Pre-flight request handling

- **Security Status Endpoint** - Configuration validation and recommendations

#### Configuration Management
- Environment-based configuration via `.env` file
- Sensible defaults for development
- Production-ready configuration options
- Runtime configuration validation

#### Logging
- Structured logging with JSON and text formats
- Configurable log levels (DEBUG, INFO, WARNING, ERROR)
- Sensitive data redaction (auth tokens, passwords)

#### Testing
- **Unit Tests** - Component-level testing
  - Protocol registry tests
  - Session manager tests
  - Capability negotiator tests
  - Message router tests
  - Security module tests

- **Integration Tests** - End-to-end workflow testing
  - MCP tool invocation tests
  - HTTP endpoint tests
  - Cross-component integration

- **Test Coverage** - 55.24% coverage (91/98 tests passing)

#### Developer Experience
- **Type Hints** - Full type annotation coverage
- **Docstrings** - Google-style documentation
- **Code Quality** - Ruff linting, Black formatting, mypy type checking
- **Development Scripts** - Quick start, testing, quality checks

#### Documentation
- **README.md** - Comprehensive project documentation
  - Installation instructions
  - Quick start guide
  - Configuration reference
  - API overview
  - Development setup
  - Security best practices
  - Deployment guide
  - Troubleshooting section

- **API Documentation** (`docs/api.md`)
  - Complete HTTP endpoint reference
  - MCP tools reference
  - Error codes documentation
  - Authentication guide

- **Architecture Documentation** (`docs/architecture.md`)
  - System overview with diagrams
  - Component architecture
  - Data models
  - Message flow diagrams
  - Storage layer design
  - Security architecture
  - Deployment patterns

- **Project Documentation** (`.moai/project/`)
  - Product overview
  - Project structure
  - Technical stack

### Dependencies

#### Core Dependencies
- `mcp>=1.0.0` - Model Context Protocol SDK
- `fastapi>=0.115.0` - Web framework
- `pydantic>=2.9.0` - Data validation
- `jsonschema>=4.0.0` - JSON Schema validation
- `uvicorn[standard]>=0.32.0` - ASGI server
- `semver>=3.0.0` - Semantic versioning
- `python-dotenv>=1.0.0` - Environment configuration

#### Optional Dependencies
- `redis>=5.0.0` - Distributed storage backend

#### Development Dependencies
- `pytest>=8.0.0` - Testing framework
- `pytest-asyncio>=0.24.0` - Async test support
- `pytest-cov>=6.0.0` - Coverage reporting
- `httpx>=0.28.0` - Async HTTP client
- `ruff>=0.8.0` - Linter
- `black>=24.0.0` - Formatter
- `mypy>=1.0.0` - Type checker
- `pytest-mock>=3.14.0` - Mocking utilities

### Python Support
- Python 3.11
- Python 3.12
- Python 3.13

### Known Issues

- 7 failing tests in router module (addressed in future releases)
- Test coverage at 55.24% (target: 85%)
- Redis connection pool tuning needs optimization

### Security Considerations

- Authentication disabled by default (enable for production)
- CORS origins set to wildcard `*` by default (restrict in production)
- No rate limiting implemented (add at reverse proxy level)
- Message payload size limit: 10MB (configurable)

---

## [Unreleased]

### Added

#### Dashboard Features
- **Multi-Language Support (SPEC-UI-I18N-001)** - Dashboard UI internationalization
  - Language toggle component in dashboard header (Korean/English)
  - localStorage persistence for language preference
  - I18n API endpoints for translation resources
  - Translation JSON files for Korean and English
  - Automatic browser language detection
  - Real-time DOM update on language change
  - Translation key fallback system
  - Language change event dispatching

- **Project Filtering UI (SPEC-UI-PROJECTS-001)** - Chat-like project sidebar
  - Project sidebar with channel-style project listing
  - Agent filtering by selected project
  - Real-time agent count per project
  - Online/offline status indicators for projects
  - Keyboard shortcuts (Cmd/Ctrl + 1-9) for project switching
  - Collapsible sidebar with localStorage persistence
  - "All Agents" channel for viewing all agents
  - Project selection synchronization across components

- **Message History View (SPEC-UI-MESSAGES-001)** - Message browser with filtering
  - Message list section in dashboard
  - Project-based message filtering
  - Message detail modal with full content
  - Infinite scroll for pagination
  - Real-time message updates via WebSocket
  - Empty and error state handling
  - Message preview with truncation
  - Timestamp formatting and display

#### New API Endpoints
- `GET /api/v1/i18n/languages` - List supported languages
- `GET /api/v1/i18n/{language}` - Get translation resources
- `GET /api/v1/projects` - List projects with agent counts
- `GET /api/v1/projects/{project_id}/agents` - Get agents by project
- `GET /api/v1/messages` - List messages with filtering
- `GET /api/v1/messages/{message_id}` - Get message details

#### New JavaScript Modules
- `static/js/i18n.js` - I18n manager for language handling
- `static/js/projects.js` - Project sidebar component
- `static/js/messages.js` - Message history component

#### New Data Models
- `TranslationResource` - I18n translation model
- `LanguageInfo` - Language metadata model
- `MessageListItem` - Message list view model
- `MessageDetail` - Full message detail model

#### Translation Files
- `i18n/ko.json` - Korean translations
- `i18n/en.json` - English translations

### Changed

#### Core Models
- `AgentInfo` model now includes `project_id` field for project association
- `AgentRegistry` service extended with project-related methods

#### API Integration
- Status API supports optional `project_id` query parameter for filtering

### Changed
- **Multi-Project Support** - Project isolation and cross-project communication
  - Project identification via X-Project-ID header or API key prefix
  - Project-scoped sessions, protocols, and messages
  - Cross-project communication with explicit permission model
  - Four new project management MCP tools
  - Backward compatible with existing single-project deployments
  - API key format: {project_id}_{key_id}_{secret}
  - Namespace-based resource isolation in storage layer
  - Project discovery and filtering capabilities

### Changed
- Session model now includes project_id field (defaults to "default")
- SessionManager methods now support project_id parameter for scoping
- ProtocolRegistry methods now support project_id parameter for isolation
- MessageRouter validates project boundaries and prevents unauthorized cross-project messaging
- Storage backend interface extended with project_id parameter support

### Planned Features
- [ ] Protocol transformation adapters for version compatibility
- [ ] Dead-letter queue for failed messages
- [ ] Rate limiting on API endpoints
- [ ] Metrics and observability (Prometheus)
- [ ] Admin dashboard for monitoring
- [ ] WebSocket support for real-time message push
- [ ] Message replay capabilities

---

## Version Reference

| Version | Release Date | Status |
|---------|--------------|--------|
| 1.0.0 | 2025-01-31 | Current |
| Unreleased | - | In Development |

---

## Links

- [GitHub Repository](https://github.com/yarang/agent_com)
- [Issue Tracker](https://github.com/yarang/agent_com/issues)
- [MCP Specification](https://modelcontextprotocol.io/)

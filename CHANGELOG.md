# Changelog

All notable changes to the MCP Broker Server project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

#### Agent and Task Persistence System (SPEC-AGENT-PERSISTENCE-001)
- **AgentDB Model** - Complete database persistence for AI agents
  - Agents table with UUID primary key and project association
  - Status tracking (online, offline, busy, error)
  - Capabilities management (JSON array)
  - Flexible configuration (JSON object)
  - Active state flag for authentication control
  - Unique constraint on (project_id, name)
  - Cascade delete to API keys and chat participants

- **TaskDB Model** - Complete database persistence for agent tasks
  - Tasks table with UUID primary key and project association
  - Optional chat room association
  - Status tracking (pending, in_progress, review, completed, blocked, cancelled)
  - Priority levels (low, medium, high, critical)
  - Task assignment to agents or users
  - Dependency management with JSON array
  - Automatic timestamp management (started_at, completed_at)
  - Due date tracking and result storage (JSON)

- **Agent API Endpoints** (`/api/v1/agents`)
  - `POST /api/v1/agents` - Create new agent
  - `GET /api/v1/agents` - List agents with pagination and filtering
  - `GET /api/v1/agents/{id}` - Get agent by ID
  - `PATCH /api/v1/agents/{id}` - Update agent (partial updates)
  - `DELETE /api/v1/agents/{id}` - Delete agent (CASCADE)

- **Task API Endpoints** (`/api/v1/tasks`)
  - `POST /api/v1/tasks` - Create new task
  - `GET /api/v1/tasks` - List tasks with pagination and filtering
  - `GET /api/v1/tasks/{id}` - Get task by ID
  - `PATCH /api/v1/tasks/{id}` - Update task (partial updates)
  - `DELETE /api/v1/tasks/{id}` - Delete task
  - `POST /api/v1/tasks/{id}/assign` - Assign task to agent/user

- **Foreign Key Constraint Fixes** - Referential integrity for agent_id references
  - FK constraint on `chat_participants.agent_id` -> `agents.id` (CASCADE)
  - FK constraint on `agent_api_keys.agent_id` -> `agents.id` (CASCADE)
  - Relationship definitions for AgentDB -> AgentApiKeyDB, ChatParticipantDB

- **Database Migration** - Alembic migration `003_create_agent_and_task_tables`
  - Creates agents and tasks tables with proper indexes
  - Handles orphaned agent_id values by creating placeholder agents
  - Applies foreign key constraints to existing tables
  - Verified upgrade and downgrade paths

#### Database Schema
- **agents table** - Stores AI agent entities with project association
- **tasks table** - Stores agent tasks with dependency tracking
- **Foreign keys** - Enforces referential integrity across agent-related tables

#### Documentation
- [Agent and Task API Documentation](docs/AGENT_TASK_API.md) - Complete API reference
- [Agent and Task Architecture](docs/AGENT_TASK_ARCHITECTURE.md) - System architecture and design

### Changed

#### Data Persistence
- **Agent data** now persists across application restarts (previously in-memory only)
- **Task data** now persists across application restarts (previously in-memory only)
- **No data loss** on page refresh or server restart

#### Testing
- **Integration Tests** - 30+ tests covering all Agent and Task API endpoints
- **E2E Tests** - 11 tests verifying data persistence across refresh
- **Test Coverage** - 85%+ target achieved for new models and endpoints

---

## [Unreleased]

### Added

#### Agent User Ownership Model (SPEC-AGENT-002)
- **Foreign Key Constraint** - Added referential integrity between `agent_api_keys.created_by_id` and `users.id`
  - `ForeignKey("users.id", ondelete="SET NULL")` constraint on `AgentApiKeyDB.created_by_id`
  - ON DELETE SET NULL behavior preserves agent keys when users are deleted
  - Migration script `002_add_agent_api_key_user_fk.sql` with data validation
  - Alembic migration `002_add_agent_api_key_user_fk.py` for future use

#### Database Schema
- **Foreign Key** on `agent_api_keys.created_by_id` referencing `users.id`
  - Validates all agent API keys are created by valid users
  - Sets `created_by_id` to NULL when referenced user is deleted
  - Index `idx_agent_api_keys_created_by_id` for query performance

#### Testing
- **Characterization Tests** - `test_agent_api_key_fk.py`
  - Documents current FK behavior before refactoring
  - Tests for FK field definition, valid/invalid user IDs, NULL handling
  - Repository FK behavior characterization

- **Unit Tests** - `test_agent_api_key_fk_behavior.py`
  - Tests for FK constraint validation and behavior
  - ON DELETE SET NULL behavior verification
  - Query and filtering by `created_by_id`
  - JOIN queries with users table
  - Edge cases: multiple keys same creator, NULL values, updates

#### Documentation
- Migration notes for `agent_api_keys` foreign key constraint
- API documentation updates for agent ownership model
- Test coverage for foreign key constraint behavior

### Changed

#### Agent API Key Repository
- **Removed uuid4() Fallback** - Repository now requires explicit `created_by_id`
  - Previous behavior: `created_by_id=created_by_id or uuid4()` fallback
  - New behavior: `created_by_id` must be provided explicitly
  - NULL values allowed for system-created keys

#### Agent API Key Services
- **AuthServiceDB.create_agent_token()** - Now uses `ProjectDB.owner_id` as creator
  - Queries project owner to use as `created_by_id`
  - Falls back to admin user if project not found
  - Ensures all agent keys have valid user ownership

#### Data Consistency
- **Ownership Chain Alignment** - All agent-related resources now reference users
  - `ProjectDB.owner_id` → users.id
  - `MediatorDB.created_by` → users.id
  - `MediatorPromptDB.created_by` → users.id
  - `AgentApiKeyDB.created_by_id` → users.id ✅ NOW FIXED

### Security
- **Database-Level Referential Integrity** - FK constraint enforced at database level
- **No Orphaned Records** - Migration validates and fixes orphaned `created_by_id` values
- **Audit Trail** - All agent API keys traceable to creating user

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

#### User Management System (SPEC-FULL-001)
- **Database-Persistent User Authentication**
  - Public user signup endpoint with database persistence
  - Argon2 password hashing for secure storage
  - JWT token generation and validation
  - Token refresh mechanism with automatic handling
  - Email uniqueness validation
  - Username validation (min 3 characters)
  - Password strength requirements (min 12 characters)

- **Project Management with Database Persistence**
  - Complete CRUD operations for projects
  - Owner-based access control
  - Project archival functionality
  - Cascade delete for related data
  - Agent assignment to projects
  - Project-based agent filtering

- **Agent Management System**
  - Agent API key generation and storage
  - Database-backed agent authentication
  - Token rotation functionality
  - Token revocation support
  - Agent-to-project association
  - Capability tracking per agent

- **Chat Room System**
  - Real-time messaging with WebSocket support
  - Multi-participant chat rooms
  - Message history with pagination
  - Agent and user message support
  - Project-based chat room organization
  - Participant management

#### Mediator System (SPEC-MEDIATOR-001)
- **LLM Model Management**
  - Support for OpenAI models (GPT-4, GPT-4 Turbo, GPT-3.5 Turbo)
  - Support for Anthropic models (Claude 3 Opus, Sonnet, Haiku)
  - Model provider abstraction layer
  - API endpoint configuration per model
  - Streaming support indicators
  - Cost tracking per 1K tokens

- **Mediator Prompt Management**
  - Prompt library with categories (moderator, summarizer, facilitator, translator)
  - System prompt editor with variable support
  - Few-shot examples storage
  - Public/private prompt visibility
  - Prompt duplication functionality
  - Category-based filtering

- **Chat Room Mediator Assignment**
  - One-to-many mediator-to-room assignments
  - Per-mediator prompt override
  - Auto-trigger and keyword-based triggering
  - Manual trigger via API
  - Active/inactive mediator states
  - Configuration temperature and max_tokens settings

- **LLM Provider Integration**
  - OpenAI API integration
  - Anthropic API integration
  - Extensible provider interface
  - Error handling and retry logic

#### Complete UI System (SPEC-UI-001)
- **Login Page**
  - Clean, modern login interface
  - User signup with validation
  - Secure password input
  - Error message display
  - Responsive design
  - Auto-redirect after login

- **Mediator Management UI**
  - Models section with provider badges
  - Prompts section with category filtering
  - Active mediators section
  - Create/Edit mediator modals
  - Prompt editor with syntax highlighting
  - Configuration JSON editor
  - Real-time status updates

- **Settings Page**
  - User profile management
  - Password change functionality
  - Project management interface
  - Agent key management
  - Preference settings
  - Account deletion

- **Foundation JavaScript Modules**
  - `router.js` - SPA routing with hash-based navigation
  - `auth.js` - Authentication manager with token refresh
  - `websocket.js` - WebSocket connection management with auto-reconnect
  - `api.js` - Complete API client with error handling
  - `login.js` - Login page logic
  - `settings.js` - Settings page management
  - `mediators.js` - Mediator management interface

- **CSS Styling System**
  - `mediators.css` - 767 lines of mediator-specific styles
  - `settings.css` - 963 lines of settings-specific styles
  - Design token system with CSS variables
  - Responsive layout utilities
  - Modal component styles
  - Form validation styles

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

**Authentication:**
- `POST /api/v1/auth/signup` - Public user registration
- `POST /api/v1/auth/login` - User login with JWT tokens
- `POST /api/v1/auth/logout` - Token revocation
- `POST /api/v1/auth/refresh` - Token refresh
- `GET /api/v1/auth/me` - Current user info
- `PUT /api/v1/auth/me` - Update profile
- `POST /api/v1/auth/change-password` - Password change

**Projects:**
- `GET /api/v1/projects` - List user's projects
- `POST /api/v1/projects` - Create new project
- `GET /api/v1/projects/{id}` - Get project details
- `PUT /api/v1/projects/{id}` - Update project
- `DELETE /api/v1/projects/{id}` - Delete project
- `POST /api/v1/projects/{id}/archive` - Archive project

**Agents:**
- `GET /api/v1/agents` - List user's agents
- `POST /api/v1/agents` - Create new agent
- `GET /api/v1/agents/{id}` - Get agent details
- `PUT /api/v1/agents/{id}` - Update agent
- `DELETE /api/v1/agents/{id}` - Delete agent
- `POST /api/v1/agents/{id}/revoke` - Revoke agent token
- `POST /api/v1/agents/{id}/rotate` - Rotate agent token

**Chat Rooms:**
- `GET /api/v1/chat/rooms` - List chat rooms
- `POST /api/v1/chat/rooms` - Create chat room
- `GET /api/v1/chat/rooms/{id}` - Get room details
- `PUT /api/v1/chat/rooms/{id}` - Update room
- `DELETE /api/v1/chat/rooms/{id}` - Delete room
- `GET /api/v1/chat/rooms/{id}/messages` - Get messages
- `POST /api/v1/chat/rooms/{id}/messages` - Send message
- `POST /api/v1/chat/rooms/{id}/participants` - Add participant
- `DELETE /api/v1/chat/rooms/{id}/participants/{id}` - Remove participant

**Mediators:**
- `GET /api/v1/mediator-models` - List available models
- `GET /api/v1/mediator-models/{id}` - Get model details
- `POST /api/v1/mediator-models` - Create custom model (admin)
- `GET /api/v1/mediator-prompts` - List prompts
- `POST /api/v1/mediator-prompts` - Create prompt
- `GET /api/v1/mediator-prompts/{id}` - Get prompt details
- `PUT /api/v1/mediator-prompts/{id}` - Update prompt
- `DELETE /api/v1/mediator-prompts/{id}` - Delete prompt
- `GET /api/v1/mediator-prompts/categories` - List prompt categories
- `POST /api/v1/mediator-prompts/{id}/duplicate` - Duplicate prompt
- `GET /api/v1/mediators` - List mediators
- `POST /api/v1/mediators` - Create mediator
- `GET /api/v1/mediators/{id}` - Get mediator details
- `PUT /api/v1/mediators/{id}` - Update mediator
- `DELETE /api/v1/mediators/{id}` - Delete mediator

**Chat Room Mediators:**
- `GET /api/v1/chat/rooms/{id}/mediators` - List room mediators
- `POST /api/v1/chat/rooms/{id}/mediators` - Add mediator to room
- `PUT /api/v1/chat/rooms/{id}/mediators/{mid}` - Update room mediator config
- `DELETE /api/v1/chat/rooms/{id}/mediators/{mid}` - Remove mediator from room
- `POST /api/v1/chat/rooms/{id}/mediators/{mid}/trigger` - Manually trigger mediator

**I18n:**
- `GET /api/v1/i18n/languages` - List supported languages
- `GET /api/v1/i18n/{language}` - Get translation resources

**Projects:**
- `GET /api/v1/projects` - List projects with agent counts
- `GET /api/v1/projects/{project_id}/agents` - Get agents by project

**Messages:**
- `GET /api/v1/messages` - List messages with filtering
- `GET /api/v1/messages/{message_id}` - Get message details

#### Database Schema
- **users** table with email uniqueness and password hashing
- **projects** table with owner foreign key and timestamps
- **agent_api_keys** table with project association
- **chat_rooms** table with project association
- **chat_participants** table for room membership
- **chat_messages** table for message storage
- **mediators** table for mediator configuration
- **mediator_models** table for LLM model definitions
- **mediator_prompts** table for prompt templates
- **chat_room_mediators** junction table for assignments

#### New JavaScript Modules (15 files total)
- `static/js/router.js` - SPA routing system (384 lines)
- `static/js/auth.js` - Authentication manager (482 lines)
- `static/js/websocket.js` - WebSocket manager (628 lines)
- `static/js/api.js` - Complete API client (437 lines)
- `static/js/login.js` - Login page logic (474 lines)
- `static/js/settings.js` - Settings page (762 lines)
- `static/js/mediators.js` - Mediator management (1056 lines)
- `static/js/i18n.js` - I18n manager
- `static/js/projects.js` - Project sidebar
- `static/js/messages.js` - Message history
- `static/js/dashboard.js` - Main dashboard
- `static/js/project-chat.js` - Chat functionality
- `static/js/project-management.js` - Project management
- `static/js/charts.js` - Data visualization
- `static/js/timeline.js` - Timeline display

#### New HTML Pages
- `login.html` - User authentication page (571 lines)
- `mediators.html` - Mediator management interface (339 lines)
- `settings.html` - User settings page (592 lines)
- `mission-control.html` - Enhanced mission control
- `index.html` - Updated dashboard

#### New CSS Files (4 files)
- `css/mediators.css` - Mediator-specific styles (767 lines)
- `css/settings.css` - Settings-specific styles (963 lines)
- `css/styles.css` - Updated with design tokens (27 new lines)
- Foundation styles for modals, forms, and layouts

#### New Data Models
- `UserDB`, `UserCreate`, `UserUpdate` - User management
- `ProjectDB`, `ProjectCreate`, `ProjectUpdate` - Project management
- `AgentApiKeyDB`, `AgentCreate` - Agent authentication
- `ChatRoomDB`, `ChatRoomCreate` - Chat room management
- `ChatMessageDB`, `ChatMessageCreate` - Message storage
- `MediatorDB`, `MediatorCreate` - Mediator configuration
- `MediatorModelDB`, `MediatorModelCreate` - LLM models
- `MediatorPromptDB`, `MediatorPromptCreate` - Prompt templates
- `ChatRoomMediatorDB` - Room-mediator relationships

#### Translation Files
- `i18n/ko.json` - Korean translations (81 entries)
- `i18n/en.json` - English translations (81 entries)

#### WebSocket Events
- `chat.message` - New message broadcast
- `chat.participant_joined` - Participant joined notification
- `chat.participant_left` - Participant left notification
- `chat.typing` - Typing indicator
- `agent.status_update` - Agent status changes
- `project.update` - Project data updates

### Changed

#### Core Models
- `AgentInfo` model now includes `project_id` field for project association
- `AgentRegistry` service extended with project-related methods
- User authentication migrated from in-memory to database
- Agent authentication migrated from in-memory to database

#### API Integration
- Status API supports optional `project_id` query parameter for filtering
- All CRUD operations now use database persistence
- WebSocket manager with auto-reconnect and error handling

#### Security
- Argon2 password hashing for user passwords
- JWT token validation with refresh mechanism
- SHA-256 hashing for API tokens
- Owner-based access control for projects
- Participant-based access control for chat rooms

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

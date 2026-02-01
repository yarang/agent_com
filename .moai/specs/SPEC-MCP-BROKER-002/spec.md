# SPEC-MCP-BROKER-002: Multi-Project Support for MCP Broker Server

## TAG BLOCK

```yaml
SPEC_ID: SPEC-MCP-BROKER-002
TITLE: Multi-Project Support - Project Isolation and Authentication
STATUS: Planned
PRIORITY: High
DOMAIN: MCP-BROKER
VERSION: 1.0.0
CREATED: 2026-01-31
ASSIGNED: manager-ddd
RELATED_SPECS:
  - SPEC-MCP-BROKER-001 (base MCP Broker Server)
TRACEABILITY:
  - PLAN: .moai/specs/SPEC-MCP-BROKER-002/plan.md
  - ACCEPTANCE: .moai/specs/SPEC-MCP-BROKER-002/acceptance.md
```

---

## Environment

### System Context

The MCP Broker Server currently operates in single-project mode where all connected Claude Code instances share a global namespace. SPEC-MCP-BROKER-002 extends the broker to support multiple independent projects with complete isolation of protocols, sessions, messages, and authentication.

Multi-project scenarios include:
- Multiple development teams using the same broker instance
- Different projects with their own protocol definitions
- Isolated testing and production environments on the same broker
- Multi-tenant deployments where each tenant requires separate namespace

### Technical Environment

- **Base System**: MCP Broker Server v1.0 (SPEC-MCP-BROKER-001)
- **Language**: Python 3.13+
- **MCP SDK**: `mcp` (official Python SDK)
- **Project Identification**: API key prefix, HTTP header, or connection context
- **Storage**: Project-scoped data isolation (in-memory or Redis)
- **Authentication**: Project-specific API keys with optional user authentication

### Deployment Environment

- **Development**: Multiple local projects connecting to single broker
- **Production**: Multi-tenant broker serving multiple teams/organizations
- **Network**: HTTP/HTTPS with Server-Sent Events (SSE) for real-time updates

---

## Assumptions

### Technical Assumptions

| Assumption | Confidence | Evidence Basis | Risk if Wrong | Validation Method |
|------------|------------|----------------|---------------|-------------------|
| API key prefix format can uniquely identify projects | High | Standard API key pattern (projID_key) | Medium - May conflict with existing keys | Prototype prefix-based routing |
| Storage layer can be extended with project namespace | High | Current storage abstraction supports key prefixing | Low - Abstracted storage interface | Unit test storage namespacing |
| Session isolation can be implemented without breaking existing API | Medium | Session IDs are UUIDs independent of project | High - May require API changes | Integration test with mixed projects |
| Protocol registry can be sharded by project | High | ProtocolRegistry uses dict-based storage | Low - Add project_id to dict key | Test protocol isolation across projects |
| Existing MCP tools can be extended with project context | Medium | MCP SDK supports parameterized tools | Medium - Tool signature changes required | Test tool invocation with project_id |

### Business Assumptions

| Assumption | Confidence | Evidence Basis | Risk if Wrong | Validation Method |
|------------|------------|----------------|---------------|-------------------|
| Multiple teams need isolated environments on shared broker | High | User request indicates multi-project scenarios | Low - Core use case | User survey/interview |
| Project owners should manage their own API keys | High | Self-service model is industry standard | Low - Standard admin pattern | Admin UX testing |
| Cross-project communication should be opt-in | Medium | Security consideration suggests isolation default | Medium - May limit collaboration | Design cross-project communication API |
| Projects can share protocols in read-only mode | Medium | Protocol reuse reduces duplication | Medium - May complicate protocol versioning | Test protocol sharing scenarios |

### Root Cause Analysis (Five Whys)

1. **Surface Problem**: Cannot isolate protocols, sessions, and messages by project
2. **First Why**: Current broker has single global namespace for all resources
3. **Second Why**: No project identification mechanism in requests
4. **Third Why**: Session model lacks project association
5. **Root Cause**: Original architecture assumed single-project deployment

**Solution Approach**: Introduce project as first-class entity with scoped namespaces for all resources, project-specific authentication, and optional cross-project communication.

---

## Requirements (EARS Format)

### 1. Project Identification Requirements

**UBIQUITOUS**: The system SHALL identify the project for every incoming request using API key prefix, HTTP header, or connection parameter.

**WHEN** a request arrives, **THEN** the system SHALL extract project identifier from the first available source in priority order: X-Project-ID header, API key prefix (format: {project_id}_{key}), or connection parameter.

**IF** no project identifier can be determined, **THEN** the system SHALL reject the request with HTTP 401 Unauthorized and error message indicating missing project credentials.

**WHILE** processing a request, **THEN** the system SHALL scope all resource access (protocols, sessions, messages) to the identified project.

**WHERE** API key prefix is used for identification, **THEN** the system SHALL validate the prefix against registered projects and return 403 if project is unknown.

**THE SYSTEM SHALL NOT** allow requests to access or modify resources from a different project.

### 2. Project Registry Requirements

**UBIQUITOUS**: The system SHALL maintain a registry of all registered projects with metadata, API keys, and configuration.

**WHEN** a new project is registered, **THEN** the system SHALL assign a unique project ID, generate initial API keys, and create project-scoped storage namespace.

**IF** a project with the same name already exists, **THEN** the system SHALL reject registration with error indicating available alternative names.

**WHILE** a project is active, **THEN** the system SHALL track project metrics including session count, message volume, protocol count, and last activity timestamp.

**WHEN** a project is deactivated, **THEN** the system SHALL preserve historical data, disconnect all active sessions, and reject new connections with clear deactivation notice.

**WHERE** project configuration includes storage quotas, **THEN** the system SHALL enforce quota limits and alert when thresholds are exceeded.

**THE SYSTEM SHALL NOT** allow project deletion if active sessions or pending messages exist.

### 3. Project Authentication Requirements

**UBIQUITOUS**: The system SHALL authenticate each request using project-specific API keys with optional user-level authentication.

**WHEN** a project API key is validated, **THEN** the system SHALL verify the key belongs to the identified project, check key expiration status, and log authentication events.

**IF** an expired or invalid API key is presented, **THEN** the system SHALL return 401 Unauthorized without revealing whether the project exists or the key is invalid.

**WHILE** user-level authentication is enabled for a project, **THEN** the system SHALL require both valid project API key and user credentials (token or certificate).

**WHERE** projects share the same broker, **THEN** the system SHALL ensure API keys from one project cannot authenticate requests for another project.

**THE SYSTEM SHALL NOT** allow authentication bypass even for project owner operations; all administrative actions require proper authentication.

### 4. Session Isolation Requirements

**UBIQUITOUS**: The system SHALL isolate sessions by project such that sessions can only interact with resources within their project scope.

**WHEN** a session connects, **THEN** the system SHALL associate the session with the authenticated project, assign project-scoped session ID, and record project in session metadata.

**IF** a session attempts to access resources from another project, **THEN** the system SHALL reject the operation with 403 Forbidden error indicating project boundary violation.

**WHILE** listing sessions, **THEN** the system SHALL only return sessions belonging to the requesting project unless the request has cross-project admin privileges.

**WHERE** session heartbeats are processed, **THEN** the system SHALL maintain project-specific heartbeat intervals and stale session thresholds.

**THE SYSTEM SHALL NOT** allow messages to be routed between sessions from different projects unless explicitly authorized via cross-project communication configuration.

### 5. Protocol Isolation Requirements

**UBIQUITOUS**: The system SHALL maintain separate protocol registries per project with optional read-only protocol sharing.

**WHEN** a protocol is registered, **THEN** the system SHALL store the protocol in the project-scoped namespace, validate against project-specific naming rules, and record project ownership.

**IF** a protocol name conflict occurs within a project, **THEN** the system SHALL reject registration and suggest version increment or name modification.

**WHILE** protocol discovery is performed, **THEN** the system SHALL only return protocols registered within the requesting project unless cross-project sharing is enabled.

**WHERE** protocol sharing is configured, **THEN** the system SHALL allow projects to import protocols from other projects in read-only mode with clear provenance metadata.

**THE SYSTEM SHALL NOT** allow protocol modification through shared references; modifications require direct project ownership.

### 6. Message Isolation Requirements

**UBIQUITOUS**: The system SHALL ensure messages are routed only within the originating project unless cross-project routing is explicitly configured.

**WHEN** a message is sent, **THEN** the system SHALL validate that both sender and recipient sessions belong to the same project, verify protocol is registered in the project, and scope message queue to project namespace.

**IF** a message attempts to cross project boundaries without authorization, **THEN** the system SHALL reject delivery with error indicating cross-project communication is disabled.

**WHILE** broadcasting messages, **THEN** the system SHALL deliver only to sessions within the same project unless broadcast explicitly targets multiple projects.

**WHERE** message queuing is used for offline recipients, **THEN** the system SHALL maintain project-specific queue limits and message expiration policies.

**THE SYSTEM SHALL NOT** allow message inspection or modification by sessions from different projects, including administrative sessions without explicit authorization.

### 7. Project Discovery Requirements

**UBIQUITOUS**: The system SHALL provide mechanisms for discovering active projects, project capabilities, and project metadata.

**WHEN** a project lists other projects, **THEN** the system SHALL return only projects that have opted into discovery, include only public metadata (name, description, capabilities), and hide sensitive information (API keys, session details).

**IF** a project has disabled discovery, **THEN** the system SHALL exclude it from project listing results while still allowing direct access by project ID.

**WHILE** querying project capabilities, **THEN** the system SHALL return supported protocol versions, enabled features, and communication patterns without exposing implementation details.

**WHERE** cross-project communication is requested, **THEN** the system SHALL provide compatibility matrix showing which protocol versions are compatible between projects.

**THE SYSTEM SHALL NOT** expose project configuration, API keys, or internal metrics through discovery endpoints.

### 8. MCP Tools Extension Requirements

**UBIQUITOUS**: The system SHALL extend all existing MCP tools with project scoping while maintaining backward compatibility for single-project deployments.

**register_protocol Tool Extension**:
- **WHEN** invoked, **THEN** the system SHALL accept optional project_id parameter, validate project exists and caller has registration permission, and register protocol in project namespace
- **IF** project_id is omitted in single-project mode, **THEN** the system SHALL register in default project namespace

**discover_protocols Tool Extension**:
- **WHEN** invoked, **THEN** the system SHALL return protocols from the calling project's namespace, support include_shared parameter to include shared protocols, and filter results based on project access permissions

**list_sessions Tool Extension**:
- **WHEN** invoked, **THEN** the system SHALL return only sessions within the calling project, support project_id parameter for admin cross-project queries, and require elevated permissions for cross-project access

**send_message Tool Extension**:
- **WHEN** invoked, **THEN** the system SHALL validate recipient session is within the same project, support target_project_id parameter for authorized cross-project messaging, and return delivery status with project context

**Project Management Tools (NEW)**:

**create_project Tool**:
- **WHEN** invoked with project name and metadata, **THEN** the system SHALL create new project with unique ID, generate initial API keys, and return project credentials

**list_projects Tool**:
- **WHEN** invoked, **THEN** the system SHALL return discoverable projects with public metadata, filter based on caller permissions, and support name/description filtering

**get_project_info Tool**:
- **WHEN** invoked with project_id, **THEN** the system SHALL return project metadata, capabilities, and statistics if caller has access permission

**rotate_project_keys Tool**:
- **WHEN** invoked by project admin, **THEN** the system SHALL generate new API keys, invalidate old keys after grace period, and return updated credentials

**THE SYSTEM SHALL NOT** allow project management operations without proper authentication and authorization.

### 9. Storage Isolation Requirements

**UBIQUITOUS**: The system SHALL maintain complete isolation of project data in the storage layer using namespace prefixing or separate databases.

**WHEN** storing project resources, **THEN** the system SHALL prefix all storage keys with project namespace (format: project_id:resource_type:resource_id), enforce namespace boundaries on all storage operations, and prevent cross-project data access.

**IF** storage layer detects namespace boundary violation, **THEN** the system SHALL reject operation with error indicating cross-project access attempt.

**WHILE** using Redis backend, **THEN** the system SHALL use separate database indices per project or key prefixing with consistent pattern.

**WHERE** in-memory storage is used, **THEN** the system SHALL maintain separate dict instances per project for each resource type.

**THE SYSTEM SHALL NOT** allow storage operations to bypass namespace isolation even for internal system operations.

### 10. Cross-Project Communication Requirements

**UBIQUITOUS**: The system SHALL support optional, explicitly configured cross-project communication with strict authorization controls.

**WHEN** cross-project communication is configured, **THEN** the system SHALL require explicit mutual consent from both projects, document communication permissions in project metadata, and log all cross-project message attempts.

**IF** a cross-project message is sent without authorization, **THEN** the system SHALL reject delivery with error indicating cross-project communication is not configured between the projects.

**WHILE** routing cross-project messages, **THEN** the system SHALL validate protocol compatibility between projects, apply protocol transformation if configured, and track cross-project message statistics separately.

**WHERE** cross-project communication is established, **THEN** the system SHALL support communication policies including rate limits, message size limits, and allowed protocol whitelists.

**THE SYSTEM SHALL NOT** enable cross-project communication by default; all cross-project communication requires explicit opt-in configuration.

---

## Specifications

### Component Architecture

```
                              MCP Broker Server (Multi-Project)
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                    Project Identification Middleware                     │    │
│  │                                                                          │    │
│  │  • API Key Prefix Parser    • Header Extraction    • Context Resolver   │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                    │                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                        Project Registry (NEW)                           │    │
│  │                                                                          │    │
│  │  • Project Metadata         • API Key Management    • Permission Store  │    │
│  │  • Project Configuration    • Cross-Project Rules   • Quota Tracking    │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                    │                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                     Project-Scoped Component Layer                      │    │
│  │                                                                          │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │    │
│  │  │ Protocol     │  │ Session      │  │ Message      │  │ Capability   │  │    │
│  │  │ Registry     │  │ Manager      │  │ Router       │  │ Negotiator   │  │    │
│  │  │              │  │              │  │              │  │              │  │    │
│  │  │ • Namespaced │  │ • Project    │  │ • Isolated   │  │ • Project-   │  │    │
│  │  │   Storage   │  │   Association │  │   Queues     │  │   Specific   │  │    │
│  │  │ • Shared     │  │ • Isolated   │  │ • Cross-     │  │   Handshakes │  │    │
│  │  │   Protocols │  │   Sessions   │  │   Project    │  │              │  │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                    │                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                  Namespace-Isolated Storage Layer                       │    │
│  │                                                                          │    │
│  │  Project A:                   Project B:                   Project C:     │    │
│  │  ┌─────────────┐              ┌─────────────┐              ┌───────────┐  │    │
│  │  │ Protocols   │              │ Protocols   │              │ Protocols │  │    │
│  │  │ Sessions    │              │ Sessions    │              │ Sessions  │  │    │
│  │  │ Messages    │              │ Messages    │              │ Messages  │  │    │
│  │  └─────────────┘              └─────────────┘              └───────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                    │                                           │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
┌───────▼────────┐         ┌────────▼────────┐         ┌────────▼────────┐
│ Project A      │         │ Project B       │         │ Project C       │
│ Claude Code    │         │ Claude Code     │         │ Claude Code     │
│ Instance(s)    │         │ Instance(s)     │         │ Instance(s)     │
└────────────────┘         └─────────────────┘         └─────────────────┘
```

### Data Model Specifications

#### Project Definition Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Project Definition",
  "type": "object",
  "required": ["project_id", "name", "api_keys", "created_at"],
  "properties": {
    "project_id": {
      "type": "string",
      "pattern": "^[a-z][a-z0-9_]*[a-z0-9]$",
      "description": "Unique project identifier (snake_case)"
    },
    "name": {
      "type": "string",
      "minLength": 1,
      "maxLength": 100,
      "description": "Human-readable project name"
    },
    "description": {
      "type": "string",
      "maxLength": 500,
      "description": "Project description"
    },
    "api_keys": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "key_id": {"type": "string"},
          "api_key": {"type": "string"},
          "created_at": {"type": "string", "format": "date-time"},
          "expires_at": {"type": "string", "format": "date-time"},
          "is_active": {"type": "boolean"}
        }
      },
      "description": "Project API keys"
    },
    "config": {
      "type": "object",
      "properties": {
        "max_sessions": {"type": "integer", "minimum": 1},
        "max_protocols": {"type": "integer", "minimum": 1},
        "max_message_queue_size": {"type": "integer", "minimum": 1},
        "allow_cross_project": {"type": "boolean"},
        "discoverable": {"type": "boolean"},
        "shared_protocols": {
          "type": "array",
          "items": {"type": "string"}
        }
      }
    },
    "cross_project_permissions": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "target_project_id": {"type": "string"},
          "allowed_protocols": {
            "type": "array",
            "items": {"type": "string"}
          },
          "message_rate_limit": {"type": "integer"}
        }
      }
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "last_activity": {
      "type": "string",
      "format": "date-time"
    },
    "status": {
      "type": "string",
      "enum": ["active", "inactive", "suspended"]
    }
  }
}
```

#### Project-Scoped Session Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Project-Scoped Session",
  "type": "object",
  "required": ["session_id", "project_id", "connection_time", "status"],
  "properties": {
    "session_id": {
      "type": "string",
      "format": "uuid",
      "description": "Unique session identifier"
    },
    "project_id": {
      "type": "string",
      "description": "Project this session belongs to"
    },
    "connection_time": {
      "type": "string",
      "format": "date-time"
    },
    "last_heartbeat": {
      "type": "string",
      "format": "date-time"
    },
    "status": {
      "type": "string",
      "enum": ["active", "stale", "disconnected"]
    },
    "capabilities": {
      "type": "object",
      "properties": {
        "supported_protocols": {
          "type": "object",
          "additionalProperties": {
            "type": "array",
            "items": {"type": "string"}
          }
        }
      }
    },
    "metadata": {
      "type": "object",
      "properties": {
        "user_agent": {"type": "string"},
        "connection_type": {"type": "string"}
      }
    }
  }
}
```

### API Key Format Specification

**API Key Structure**: `{project_id}_{key_id}_{secret}`

**Format Rules**:
- `project_id`: Valid project identifier (lowercase, alphanumeric, underscore)
- `key_id`: Key identifier (e.g., `default`, `admin`, `service`)
- `secret`: Cryptographically random string (minimum 32 characters)

**Example**: `myproject_admin_k8j3m9x2p4v7n1q5`

**Parsing**: Split on first underscore to extract project_id, validate remainder against project's registered keys.

### New MCP Tool Definitions

#### Tool: create_project

```python
{
    "name": "create_project",
    "description": "Create a new project with generated API keys",
    "inputSchema": {
        "type": "object",
        "required": ["project_id", "name"],
        "properties": {
            "project_id": {
                "type": "string",
                "pattern": "^[a-z][a-z0-9_]*[a-z0-9]$",
                "description": "Unique project identifier"
            },
            "name": {
                "type": "string",
                "minLength": 1,
                "maxLength": 100,
                "description": "Human-readable project name"
            },
            "description": {
                "type": "string",
                "maxLength": 500,
                "description": "Project description"
            },
            "config": {
                "type": "object",
                "properties": {
                    "max_sessions": {"type": "integer"},
                    "max_protocols": {"type": "integer"},
                    "allow_cross_project": {"type": "boolean"},
                    "discoverable": {"type": "boolean"}
                }
            }
        }
    }
}
```

#### Tool: list_projects

```python
{
    "name": "list_projects",
    "description": "List discoverable projects with public metadata",
    "inputSchema": {
        "type": "object",
        "properties": {
            "name_filter": {
                "type": "string",
                "description": "Filter by project name (partial match)"
            },
            "include_inactive": {
                "type": "boolean",
                "default": false,
                "description": "Include inactive projects"
            },
            "include_stats": {
                "type": "boolean",
                "default": false,
                "description": "Include project statistics"
            }
        }
    }
}
```

#### Tool: get_project_info

```python
{
    "name": "get_project_info",
    "description": "Get detailed project information",
    "inputSchema": {
        "type": "object",
        "required": ["project_id"],
        "properties": {
            "project_id": {
                "type": "string",
                "description": "Project identifier"
            },
            "include_config": {
                "type": "boolean",
                "default": false,
                "description": "Include project configuration"
            },
            "include_permissions": {
                "type": "boolean",
                "default": false,
                "description": "Include cross-project permissions"
            }
        }
    }
}
```

#### Tool: rotate_project_keys

```python
{
    "name": "rotate_project_keys",
    "description": "Rotate project API keys (admin only)",
    "inputSchema": {
        "type": "object",
        "required": ["project_id"],
        "properties": {
            "project_id": {
                "type": "string",
                "description": "Project identifier"
            },
            "key_id": {
                "type": "string",
                "description": "Specific key to rotate (optional, rotates all if omitted)"
            },
            "grace_period_seconds": {
                "type": "integer",
                "default": 300,
                "description": "Grace period before old keys are invalidated"
            }
        }
    }
}
```

---

## Traceability

### Requirement to Component Mapping

| Requirement Category | Component | Traceability ID |
|---------------------|-----------|-----------------|
| Project Identification | ProjectIdentificationMiddleware | REQ-PROJ-ID-001 |
| Project Registry | ProjectRegistry | REQ-PROJ-REG-001 |
| Project Authentication | ProjectAuth | REQ-PROJ-AUTH-001 |
| Session Isolation | SessionManager (enhanced) | REQ-SESS-ISO-001 |
| Protocol Isolation | ProtocolRegistry (enhanced) | REQ-PROTO-ISO-001 |
| Message Isolation | MessageRouter (enhanced) | REQ-MSG-ISO-001 |
| Project Discovery | ProjectDiscovery | REQ-PROJ-DISC-001 |
| MCP Tools Extension | MCPToolsInterface (enhanced) | REQ-MCP-EXT-001 |
| Storage Isolation | StorageBackend (enhanced) | REQ-STOR-ISO-001 |
| Cross-Project Communication | CrossProjectRouter | REQ-CROSS-PROJ-001 |

### Acceptance Criteria Reference

See `.moai/specs/SPEC-MCP-BROKER-002/acceptance.md` for detailed acceptance criteria in Given-When-Then format.

### Implementation Plan Reference

See `.moai/specs/SPEC-MCP-BROKER-002/plan.md` for implementation milestones and technical approach.

---

## Dependencies

### External Dependencies

All dependencies from SPEC-MCP-BROKER-001, plus:
- **cryptography** >= 41.0.0 - API key generation and validation
- **python-dateutil** >= 2.8.0 - Date/time handling for expiration

### Internal Dependencies

- SPEC-MCP-BROKER-001 (base MCP Broker Server) - Core broker functionality
- All existing components (ProtocolRegistry, SessionManager, etc.) - Require enhancement

### System Dependencies

- Python 3.13+
- Redis (optional, for distributed deployments)
- Container runtime (Docker/Podman) for production deployments

---

## Constraints

### Technical Constraints

- MUST maintain backward compatibility with single-project deployments
- MUST NOT break existing MCP tool signatures (extend only)
- MUST support migration from single-project to multi-project configuration
- MUST ensure zero cross-project data leakage
- MUST support graceful fallback to single-project mode

### Business Constraints

- Existing deployments MUST be able to migrate without data loss
- API key format MUST be parseable without database lookup (prefix-based)
- Cross-project communication MUST be opt-in, not default
- Project isolation MUST be enforced at all layers

### Security Constraints

- API key rotation MUST NOT cause service disruption
- Project metadata MUST NOT expose sensitive information
- Cross-project communication MUST require explicit authorization
- Storage isolation MUST be enforced even for privileged operations

---

## Quality Attributes

### TRUST 5 Framework Compliance

**Tested**:
- Unit test coverage >= 85% for all new components
- Integration tests for project isolation
- Cross-project communication tests
- Migration tests from single to multi-project

**Readable**:
- Type hints on all public functions
- Docstrings following Google style
- Clear separation between project-scoped and global operations

**Unified**:
- Consistent namespace prefix pattern across storage
- Pydantic models for all project-related data structures
- Structured logging with project context

**Secured**:
- Project-scoped authentication at all entry points
- Namespace validation on all storage operations
- Audit logging for all cross-project operations

**Trackable**:
- All project creations logged with metadata
- Cross-project message tracking with source/destination
- API key rotation events logged with timestamps

---

## Appendix

### Glossary

- **Project**: Isolated namespace for protocols, sessions, and messages
- **Project ID**: Unique identifier for a project (snake_case format)
- **API Key Prefix**: Project identifier embedded in API key for routing
- **Namespace Isolation**: Separation of data by project ID in storage
- **Cross-Project Communication**: Explicitly authorized message routing between projects
- **Shared Protocol**: Protocol registered in one project and visible in another (read-only)
- **Project Discovery**: Mechanism for projects to find other projects on the broker

### Migration Strategy from Single-Project

**Phase 1: Default Project Creation**
- Create default project with ID "default"
- Migrate all existing protocols, sessions to default project
- Update storage keys with namespace prefix

**Phase 2: Identification Layer**
- Add project identification middleware
- Support backward-compatible mode (default to "default" project)
- Log missing project identifiers for transition period

**Phase 3: Multi-Project Activation**
- Enable project creation API
- Add cross-project communication controls
- Update documentation with multi-project setup

### References

- [SPEC-MCP-BROKER-001](./SPEC-MCP-BROKER-001/spec.md) - Base MCP Broker Server
- [Multi-Tenancy Patterns](https://martinfowler.com/articles/multi-tenancy.html)
- [API Key Best Practices](https://owasp.org/www-community/vulnerabilities/Insufficient_Authorization)

---

**END OF SPEC-MCP-BROKER-002**

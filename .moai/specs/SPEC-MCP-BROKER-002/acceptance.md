# Acceptance Criteria: SPEC-MCP-BROKER-002

## TAG BLOCK

```yaml
SPEC_ID: SPEC-MCP-BROKER-002
RELATED_DOCUMENTS:
  - SPEC: .moai/specs/SPEC-MCP-BROKER-002/spec.md
  - PLAN: .moai/specs/SPEC-MCP-BROKER-002/plan.md
VERSION: 1.0.0
LAST_UPDATED: 2026-01-31
```

---

## Acceptance Criteria Overview

This document defines detailed acceptance criteria for multi-project support in the MCP Broker Server. All criteria are written in the Given-When-Then format for clarity and testability.

### Quality Gate Criteria

Before considering this SPEC complete, the following must be achieved:

- [ ] All acceptance criteria scenarios pass
- [ ] 85%+ test coverage achieved
- [ ] Zero critical security vulnerabilities
- [ ] All TRUST 5 quality gates passed
- [ ] Performance targets met (<5% overhead)
- [ ] Documentation complete and accurate

---

## 1. Project Identification

### AC-1.1: API Key Prefix Identification

**Given** a project with ID "myproject" and API key "myproject_admin_k8j3m9x2p4v7n1q5"
**When** a request is made with the API key in the Authorization header
**Then** the system SHALL identify the project as "myproject"
**And** the request SHALL be scoped to "myproject" namespace
**And** authentication SHALL succeed

### AC-1.2: Header-Based Identification

**Given** a request with X-Project-ID header set to "team-alpha"
**When** the request is processed by the identification middleware
**Then** the system SHALL extract "team-alpha" as the project ID
**And** the request SHALL be scoped to "team-alpha" namespace
**And** the project SHALL be validated as existing

### AC-1.3: Missing Project Identification

**Given** a request without API key prefix or X-Project-ID header
**When** the request is processed
**Then** the system SHALL return HTTP 401 Unauthorized
**And** the error message SHALL indicate missing project credentials
**And** the event SHALL be logged as authentication failure

### AC-1.4: Invalid Project in API Key

**Given** an API key with prefix "nonexistent_project"
**When** the request is processed
**Then** the system SHALL return HTTP 403 Forbidden
**And** the error message SHALL indicate project not found
**And** no information about existing projects SHALL be leaked

### AC-1.5: Identification Priority Order

**Given** a request with both X-Project-ID header and API key prefix
**When** the header contains "project-a" and the key prefix is "project-b"
**Then** the system SHALL use the X-Project-ID header value ("project-a")
**And** the API key SHALL be validated against "project-a"
**And** the priority order SHALL be documented

---

## 2. Project Registry

### AC-2.1: Project Creation

**Given** an authenticated admin user
**When** they invoke create_project with project_id="new-project", name="New Project"
**Then** the system SHALL create a new project with ID "new-project"
**And** generate initial API keys
**And** return project credentials including API keys
**And** log the project creation event

### AC-2.2: Duplicate Project Name Prevention

**Given** a project with name "My Project" already exists
**When** a user attempts to create another project with name "My Project"
**Then** the system SHALL reject the creation
**And** return HTTP 409 Conflict
**And** the error message SHALL indicate the name conflict
**And** suggest alternative names

### AC-2.3: Project Listing

**Given** three projects exist: "project-a" (active), "project-b" (active), "project-c" (inactive)
**When** list_projects is invoked with include_inactive=false
**Then** the system SHALL return only "project-a" and "project-b"
**And** each project SHALL include name, description, and status
**And** sensitive information (API keys) SHALL NOT be included

### AC-2.4: Project Discovery Filtering

**Given** five projects exist with various names
**When** list_projects is invoked with name_filter="test"
**Then** the system SHALL return only projects with "test" in their name
**And** the search SHALL be case-insensitive
**And** partial matches SHALL be included

### AC-2.5: Non-Discoverable Projects

**Given** a project with discoverable=false
**When** list_projects is invoked
**Then** the system SHALL exclude the project from results
**And** the project SHALL still be accessible via direct project_id lookup
**And** the project's sessions and protocols SHALL remain functional

### AC-2.6: Project Deactivation

**Given** an active project with connected sessions
**When** the project is deactivated
**Then** the system SHALL preserve all historical data
**And** disconnect all active sessions with graceful shutdown
**And** reject new connection attempts
**And** return clear deactivation notice

---

## 3. Project Authentication

### AC-3.1: Valid API Key Authentication

**Given** a project with active API key "myproject_admin_validkey"
**When** a request includes this API key
**Then** the system SHALL validate the key
**And** authenticate the request for project "myproject"
**And** log the authentication event with timestamp

### AC-3.2: Expired API Key Rejection

**Given** an API key that expired yesterday
**When** a request includes the expired API key
**Then** the system SHALL reject the request with HTTP 401 Unauthorized
**And** the error message SHALL not reveal whether the project exists
**And** the event SHALL be logged as authentication failure

### AC-3.3: Project Key Isolation

**Given** project "project-a" with API key "project-a_key1"
**And** project "project-b" with API key "project-b_key2"
**When** a request uses "project-a_key1" but attempts to access "project-b" resources
**Then** the system SHALL return HTTP 403 Forbidden
**And** the error SHALL indicate project boundary violation
**And** the attempt SHALL be logged

### AC-3.4: User-Level Authentication (Optional)

**Given** a project with user authentication enabled
**When** a request includes valid project API key but invalid user credentials
**Then** the system SHALL return HTTP 401 Unauthorized
**And** the error SHALL indicate user authentication failure
**And** project authentication SHALL remain independent

### AC-3.5: Admin Bypass Prevention

**Given** a project owner attempting administrative operation
**When** the request lacks proper authentication
**Then** the system SHALL reject the operation
**And** admin privileges SHALL NOT bypass authentication
**And** the event SHALL be logged as unauthorized access attempt

---

## 4. Session Isolation

### AC-4.1: Project-Scoped Session Creation

**Given** a request authenticated for project "team-alpha"
**When** a new session is created
**Then** the session SHALL be associated with project "team-alpha"
**And** the session metadata SHALL include project_id="team-alpha"
**And** the session SHALL only access "team-alpha" resources

### AC-4.2: Cross-Project Session Access Prevention

**Given** session A belongs to project "project-a"
**And** session B belongs to project "project-b"
**When** session A attempts to list sessions from "project-b"
**Then** the system SHALL return only sessions from "project-a"
**And** session B SHALL NOT be visible to session A
**And** the attempt SHALL be logged if session A has admin privileges

### AC-4.3: Project-Scoped Session Listing

**Given** project "prod" has 5 active sessions
**And** project "dev" has 3 active sessions
**When** list_sessions is invoked with project="prod"
**Then** the system SHALL return exactly 5 sessions
**And** all returned sessions SHALL belong to "prod"
**And** no "dev" sessions SHALL be included

### AC-4.4: Admin Cross-Project Session Query

**Given** an admin user from project "admin"
**When** list_sessions is invoked with project_id="other-project" and admin credentials
**Then** the system SHALL return sessions from "other-project"
**And** the admin SHALL have elevated privileges verified
**And** the cross-project access SHALL be logged

### AC-4.5: Heartbeat Isolation

**Given** sessions from multiple projects with different heartbeat intervals
**When** heartbeat monitoring runs
**Then** each session SHALL be evaluated according to its project's interval
**And** stale session detection SHALL be project-specific
**And** session status SHALL be maintained per project

---

## 5. Protocol Isolation

### AC-5.1: Project-Scoped Protocol Registration

**Given** a request authenticated for project "mobile-app"
**When** register_protocol is invoked with protocol name "chat-protocol"
**Then** the protocol SHALL be registered in "mobile-app" namespace
**And** the protocol SHALL only be visible to "mobile-app" sessions
**And** the registration SHALL be logged with project context

### AC-5.2: Protocol Name Conflict Within Project

**Given** project "api" has protocol "data-model" registered
**When** another registration attempt for "data-model" is made in project "api"
**Then** the system SHALL reject the registration
**And** return HTTP 409 Conflict
**And** suggest version increment (e.g., "data-model-v2")

### AC-5.3: Protocol Discovery Isolation

**Given** project "frontend" with protocols "ui-events" and "state-sync"
**And** project "backend" with protocols "api-calls" and "data-streams"
**When** discover_protocols is invoked by "frontend" project
**Then** only "ui-events" and "state-sync" SHALL be returned
**And** "backend" protocols SHALL NOT be visible
**And** the result SHALL indicate total protocol count

### AC-5.4: Protocol Sharing (Read-Only)

**Given** project "shared" with protocol "common-types"
**And** project "app" has configured to import from "shared"
**When** discover_protocols is invoked by "app" with include_shared=true
**Then** "common-types" from "shared" SHALL be included in results
**And** the protocol SHALL be marked as shared with provenance
**And** "app" SHALL NOT be able to modify "common-types"

### AC-5.5: Cross-Project Protocol Modification Prevention

**Given** project "consumer" importing protocol "base-format" from project "provider"
**When** "consumer" attempts to modify "base-format"
**Then** the system SHALL return HTTP 403 Forbidden
**And** the error SHALL indicate protocol is not owned
**And** the attempt SHALL be logged

---

## 6. Message Isolation

### AC-6.1: Intra-Project Message Delivery

**Given** session A in project "sales" sends message to session B in project "sales"
**When** send_message is invoked
**Then** the message SHALL be delivered successfully
**And** the message SHALL be queued in "sales" namespace
**And** delivery confirmation SHALL be sent to session A

### AC-6.2: Cross-Project Message Rejection

**Given** session A in project "team-a" attempts to send message to session B in project "team-b"
**When** cross-project communication is not configured
**Then** the system SHALL reject the message delivery
**And** return error indicating cross-project communication disabled
**And** the rejection SHALL be logged

### AC-6.3: Broadcast Project Isolation

**Given** project "marketing" has 10 active sessions
**And** project "engineering" has 15 active sessions
**When** broadcast_message is invoked by "marketing"
**Then** the message SHALL be delivered to all 10 "marketing" sessions
**And** no "engineering" sessions SHALL receive the message
**And** delivery summary SHALL indicate 10 recipients

### AC-6.4: Project-Scoped Message Queuing

**Given** session in project "orders" is offline
**When** message is sent to this session
**Then** the message SHALL be queued in "orders" namespace
**And** queue limits SHALL be enforced per project
**And** message SHALL be delivered when session reconnects

### AC-6.5: Cross-Project Message Inspection Prevention

**Given** messages in project "finance" namespace
**When** an admin from project "operations" attempts to inspect "finance" messages
**Then** the system SHALL return HTTP 403 Forbidden
**And** no message content SHALL be exposed
**And** the attempt SHALL be logged

---

## 7. Project Discovery

### AC-7.1: Discoverable Projects Listing

**Given** projects "alpha" (discoverable=true), "beta" (discoverable=true), "gamma" (discoverable=false)
**When** list_projects is invoked
**Then** "alpha" and "beta" SHALL be included
**And** "gamma" SHALL be excluded
**And** each included project SHALL show name, description, status only

### AC-7.2: Public Metadata Only

**Given** project "public-project" with discoverable=true
**When** list_projects returns project information
**Then** the result SHALL NOT include API keys
**And** the result SHALL NOT include session details
**And** the result SHALL NOT include internal metrics
**And** only public metadata SHALL be exposed

### AC-7.3: Project Capabilities Query

**Given** project "service-a" with capabilities ["grpc", "protobuf"]
**When** get_project_info is invoked with include_capabilities=true
**Then** the result SHALL include supported capabilities
**And** capability details SHALL include protocol versions
**And** implementation details SHALL NOT be exposed

### AC-7.4: Cross-Project Compatibility Matrix

**Given** project "x" using protocol v1.0
**And** project "y" using protocol v1.2
**When** cross-project compatibility is queried
**Then** the system SHALL return compatibility matrix
**And** indicate whether v1.0 and v1.2 are compatible
**And** suggest transformation if available

---

## 8. MCP Tools Extension

### AC-8.1: Backward Compatible Tool Invocation

**Given** an existing client using single-project mode
**When** register_protocol is invoked without project_id parameter
**Then** the protocol SHALL be registered in "default" project
**And** the operation SHALL succeed without modification
**And** backward compatibility SHALL be maintained

### AC-8.2: Project-Scoped Protocol Registration

**Given** a request with project_id="iot-project"
**When** register_protocol is invoked with protocol definition
**Then** the protocol SHALL be registered in "iot-project" namespace
**And** caller permissions SHALL be verified for "iot-project"
**And** registration SHALL be logged with project context

### AC-8.3: Shared Protocol Discovery

**Given** project "core" with shared protocols
**When** discover_protocols is invoked with include_shared=true
**Then** local project protocols SHALL be returned
**And** shared protocols from other projects SHALL be included
**And** each shared protocol SHALL indicate source project

### AC-8.4: Admin Cross-Project Session Listing

**Given** an admin user
**When** list_sessions is invoked with project_id="other-project"
**Then** sessions from "other-project" SHALL be returned
**And** admin permissions SHALL be verified
**And** the cross-project query SHALL be logged

### AC-8.5: Project Creation Tool

**Given** an authenticated admin user
**When** create_project is invoked with valid project parameters
**Then** a new project SHALL be created
**And** initial API keys SHALL be generated
**And** project credentials SHALL be returned
**And** the event SHALL be logged

### AC-8.6: Project Key Rotation

**Given** a project with existing API keys
**When** rotate_project_keys is invoked by project admin
**Then** new API keys SHALL be generated
**And** old keys SHALL remain valid for grace period
**And** after grace period, old keys SHALL be invalidated
**And** the rotation SHALL be logged

---

## 9. Storage Isolation

### AC-9.1: Namespace Key Prefixing

**Given** a protocol with ID "chat-proto" in project "messaging"
**When** the protocol is stored
**Then** the storage key SHALL be prefixed as "messaging:protocol:chat-proto"
**And** retrieval SHALL only find the key with correct prefix
**And** cross-project access SHALL be prevented by key isolation

### AC-9.2: Cross-Project Storage Access Rejection

**Given** storage operation attempted for project "a" resource from project "b" context
**When** the storage layer detects namespace mismatch
**Then** the operation SHALL be rejected
**And** an error SHALL indicate cross-project access attempt
**And** the event SHALL be logged

### AC-9.3: In-Memory Storage Isolation

**Given** in-memory storage backend
**When** resources are stored for multiple projects
**Then** each project SHALL have separate dict instances
**And** no cross-project reference SHALL exist
**And** isolation SHALL be verifiable through tests

### AC-9.4: Redis Storage Isolation

**Given** Redis storage backend
**When** resources are stored for multiple projects
**Then** each key SHALL include project prefix
**And** KEY pattern matching SHALL only return same-project keys
**And** Redis database separation option SHALL work correctly

---

## 10. Cross-Project Communication

### AC-10.1: Mutual Consent Requirement

**Given** project "sender" wants to send messages to project "receiver"
**When** cross-project communication is not configured
**Then** messages SHALL be rejected
**And** both projects SHALL explicitly consent before enabling
**And** consent SHALL be documented in project metadata

### AC-10.2: Authorized Cross-Project Message Delivery

**Given** projects "x" and "y" have mutually consented to communication
**When** send_message is invoked from project "x" to project "y"
**Then** the message SHALL be delivered successfully
**And** delivery SHALL be logged with source and destination projects
**And** cross-project statistics SHALL be updated

### AC-10.3: Protocol Compatibility Check

**Given** project "a" using protocol v1.0
**And** project "b" using protocol v2.0 (incompatible)
**When** cross-project message is attempted
**Then** the system SHALL check protocol compatibility
**And** reject delivery if incompatible
**And** suggest protocol transformation or version upgrade

### AC-10.4: Cross-Project Rate Limiting

**Given** cross-project communication configured with rate limit of 100 msg/min
**When** message rate exceeds 100 msg/min
**Then** additional messages SHALL be rejected
**And** rate limit error SHALL be returned
**And** the rejection SHALL be logged

### AC-10.5: Opt-In Cross-Project Communication

**Given** a newly created project
**When** no cross-project permissions are configured
**Then** the project SHALL NOT receive messages from other projects
**And** the project SHALL NOT send messages to other projects
**And** cross-project communication SHALL be disabled by default

---

## 11. Migration from Single-Project

### AC-11.1: Default Project Creation

**Given** an existing single-project deployment
**When** the migration script is run
**Then** a "default" project SHALL be created
**And** all existing protocols SHALL be migrated to "default"
**And** all existing sessions SHALL be migrated to "default"
**And** data integrity SHALL be verified

### AC-11.2: Backward Compatibility

**Given** an existing client application
**When** the client connects to the upgraded multi-project broker
**Then** the client SHALL continue working without modification
**And** all operations SHALL be scoped to "default" project
**And** no breaking changes SHALL be experienced

### AC-11.3: Migration Rollback

**Given** a migration that needs to be rolled back
**When** the rollback script is executed
**Then** the "default" project SHALL be removed
**And** pre-migration state SHALL be restored
**And** all existing functionality SHALL work

---

## 12. Performance Requirements

### AC-12.1: Namespace Overhead

**Given** operations with project namespace isolation
**When** performance is measured
**Then** storage overhead SHALL be <5%
**And** identification latency SHALL be <10ms per request
**And** overall performance impact SHALL be minimal

### AC-12.2: Project Listing Performance

**Given** 100 projects in the registry
**When** list_projects is invoked
**Then** the response time SHALL be <100ms
**And** pagination SHALL be supported for larger result sets
**And** performance SHALL not degrade linearly

### AC-12.3: Cross-Project Message Latency

**Given** authorized cross-project communication
**When** a message is sent between projects
**Then** delivery latency SHALL be <150ms
**And** compatibility checking SHALL not significantly impact latency
**And** rate limiting SHALL not add excessive overhead

---

## 13. Security Requirements

### AC-13.1: No Cross-Project Data Leakage

**Given** multiple projects with sensitive data
**When** any project operation is performed
**Then** no data SHALL leak between projects
**And** storage isolation SHALL be enforced at all layers
**And** security audit SHALL confirm zero leakage

### AC-13.2: API Key Format Enforcement

**Given** API key validation
**When** a malformed API key is presented
**Then** authentication SHALL fail
**And** the error message SHALL not reveal format details
**And** the attempt SHALL be logged

### AC-13.3: Audit Logging

**Given** any cross-project or administrative operation
**When** the operation is performed
**Then** the event SHALL be logged with timestamp
**And** source and destination projects SHALL be recorded
**And** user identity SHALL be captured

### AC-13.4: Authorization Verification

**Given** an operation requiring project access
**When** the request is processed
**Then** project ownership SHALL be verified
**And** operation permissions SHALL be checked
**And** unauthorized access SHALL be prevented

---

## Definition of Done

A feature is considered complete when:

- [ ] All acceptance criteria for the feature pass
- [ ] Unit tests achieve 85%+ coverage
- [ ] Integration tests cover all scenarios
- [ ] Security review is completed
- [ ] Documentation is updated
- [ ] Performance benchmarks are met
- [ ] Code review is approved
- [ ] TRUST 5 quality gates are passed

---

## Test Scenarios Summary

| Category | Test Count | Priority |
|----------|------------|----------|
| Project Identification | 5 | High |
| Project Registry | 6 | High |
| Project Authentication | 5 | High |
| Session Isolation | 5 | High |
| Protocol Isolation | 5 | High |
| Message Isolation | 5 | High |
| Project Discovery | 4 | Medium |
| MCP Tools Extension | 6 | High |
| Storage Isolation | 4 | High |
| Cross-Project Communication | 5 | Medium |
| Migration | 3 | High |
| Performance | 3 | Medium |
| Security | 4 | High |
| **Total** | **60** | - |

---

**END OF ACCEPTANCE CRITERIA - SPEC-MCP-BROKER-002**

# Comprehensive Implementation Plan: MCP Broker Server

**Created Date**: 2026-01-31
**SPEC Coverage**: SPEC-MCP-BROKER-001 + SPEC-MCP-BROKER-002
**Agent**: manager-strategy
**Language**: ko (Korean)

---

## Executive Summary

### Current Status

| SPEC | Progress | Status | Remaining Tasks |
|------|----------|--------|-----------------|
| SPEC-MCP-BROKER-001 | ~90% | nearing completion | Redis storage, SSE endpoints, integration tests |
| SPEC-MCP-BROKER-002 | ~40% | in progress | Project identification, MCP tools, cross-project communication |

### Already Implemented

**SPEC-MCP-BROKER-001 Components:**
- Protocol Registry (src/mcp_broker/protocol/registry.py)
- Session Manager (src/mcp_broker/session/manager.py)
- Capability Negotiator (src/mcp_broker/negotiation/negotiator.py)
- Message Router (src/mcp_broker/routing/router.py)
- 6 MCP Tools (src/mcp_broker/mcp/tools.py)
- MCP Server (src/mcp_broker/mcp/server.py)
- In-Memory Storage (src/mcp_broker/storage/memory.py)
- Security Middleware (src/mcp_broker/core/security.py)

**SPEC-MCP-BROKER-002 Components:**
- Project Models (src/mcp_broker/models/project.py)
- Project Registry (src/mcp_broker/project/registry.py)
- Storage Interface with project_id parameter (src/mcp_broker/storage/interface.py)
- In-Memory Storage with project namespace (src/mcp_broker/storage/memory.py)

---

## 1. Remaining Work Summary

### SPEC-MCP-BROKER-001 Remaining (~10%)

| Component | Status | Complexity | Estimated Time |
|-----------|--------|------------|----------------|
| Redis Storage Backend | Not Started | Medium | 4-6 hours |
| SSE Endpoints | Not Started | Medium | 3-4 hours |
| Integration Tests | Partial | Medium | 6-8 hours |
| Load Testing | Not Started | Simple | 2-3 hours |

### SPEC-MCP-BROKER-002 Remaining (~60%)

| Component | Status | Complexity | Estimated Time |
|-----------|--------|------------|----------------|
| Project Identification Middleware | Not Started | Medium | 4-5 hours |
| Project MCP Tools (4 tools) | Not Started | Medium | 5-6 hours |
| Enhanced Protocol Registry | Not Started | Medium | 3-4 hours |
| Enhanced Session Manager | Not Started | Medium | 3-4 hours |
| Enhanced Message Router | Not Started | Medium | 3-4 hours |
| Cross-Project Communication | Not Started | Complex | 8-10 hours |
| Project Discovery | Not Started | Simple | 2-3 hours |
| Integration Tests | Not Started | Medium | 6-8 hours |
| Migration Tests | Not Started | Medium | 4-5 hours |

**Total Estimated Time**: ~60-70 hours

---

## 2. Task Breakdown

### Phase 1: SPEC-MCP-BROKER-001 Completion (Priority: HIGH)

#### Task 001: Redis Storage Backend
- **ID**: TASK-001-REDIS
- **Description**: Implement Redis storage backend for distributed deployments
- **Complexity**: Medium
- **Dependencies**: None
- **Files to Create**:
  - `src/mcp_broker/storage/redis.py`
- **Files to Modify**: None
- **Requirements**:
  - Implement StorageBackend protocol
  - Support connection pooling with retry logic
  - Use key pattern `{project_id}:{resource_type}:{resource_id}`
  - Implement automatic failover to in-memory storage
- **Acceptance Criteria**:
  - All StorageBackend methods implemented
  - Connection pooling configured
  - Automatic failover tested
  - 85%+ test coverage

#### Task 002: SSE Endpoints for Real-time Updates
- **ID**: TASK-002-SSE
- **Description**: Implement Server-Sent Events endpoints for real-time message delivery
- **Complexity**: Medium
- **Dependencies**: TASK-001-REDIS
- **Files to Create**:
  - `src/mcp_broker/core/sse.py`
- **Files to Modify**:
  - `src/mcp_broker/main.py`
- **Requirements**:
  - SSE endpoint for session message streaming
  - Automatic reconnection handling
  - Heartbeat mechanism for connection monitoring
  - Support for multiple concurrent SSE connections
- **Acceptance Criteria**:
  - SSE endpoint functional with curl client
  - Automatic reconnection tested
  - Heartbeat every 30 seconds
  - 50+ concurrent connections supported

#### Task 003: Integration Tests for SPEC-MCP-BROKER-001
- **ID**: TASK-003-INT-001
- **Description**: Complete integration test coverage for base broker functionality
- **Complexity**: Medium
- **Dependencies**: TASK-001-REDIS, TASK-002-SSE
- **Files to Create**:
  - `tests/integration/test_mcp_tools.py`
  - `tests/integration/test_end_to_end.py`
- **Files to Modify**: None
- **Requirements**:
  - Test all 6 MCP tools end-to-end
  - Test protocol registration and discovery
  - Test session lifecycle
  - Test message routing (1:1 and 1:N)
  - Test SSE message delivery
- **Acceptance Criteria**:
  - All MCP tools tested
  - 85%+ coverage achieved
  - All tests passing

#### Task 004: Load Testing
- **ID**: TASK-004-LOAD
- **Description**: Verify performance under load (50+ concurrent sessions)
- **Complexity**: Simple
- **Dependencies**: TASK-003-INT-001
- **Files to Create**:
  - `tests/load/test_concurrent_sessions.py`
- **Files to Modify**: None
- **Requirements**:
  - 50 concurrent sessions
  - 100 messages/second throughput
  - P95 latency < 100ms
  - P99 latency < 500ms
- **Acceptance Criteria**:
  - Load test passing
  - Performance targets met
  - No message loss

---

### Phase 2: Multi-Project Foundation (Priority: HIGH)

#### Task 101: Project Identification Middleware
- **ID**: TASK-101-IDENT
- **Description**: Implement middleware to extract project ID from requests
- **Complexity**: Medium
- **Dependencies**: None
- **Files to Create**:
  - `src/mcp_broker/core/identification.py`
  - `src/mcp_broker/core/context.py`
- **Files to Modify**:
  - `src/mcp_broker/main.py`
  - `src/mcp_broker/mcp/server.py`
- **Requirements**:
  - API key prefix parsing ({project_id}_{key_id}_{secret})
  - X-Project-ID header extraction
  - Connection parameter resolution
  - Project context injection into request
  - Priority order: Header > API Key prefix > Connection parameter
- **Acceptance Criteria**:
  - All three identification methods working
  - Missing identification returns 401
  - Invalid project returns 403
  - Audit logging for all identification events

#### Task 102: Project Management MCP Tools
- **ID**: TASK-102-TOOLS
- **Description**: Implement 4 project management MCP tools
- **Complexity**: Medium
- **Dependencies**: TASK-101-IDENT
- **Files to Create**:
  - `src/mcp_broker/mcp/project_tools.py`
- **Files to Modify**:
  - `src/mcp_broker/mcp/tools.py` (extend with project tools)
- **Requirements**:
  - `create_project` tool
  - `list_projects` tool
  - `get_project_info` tool
  - `rotate_project_keys` tool
  - Admin permission verification
- **Acceptance Criteria**:
  - All 4 tools functional
  - Admin permissions enforced
  - Tool documentation complete
  - Integration tests passing

#### Task 103: Enhanced Protocol Registry
- **ID**: TASK-103-PROTO
- **Description**: Extend protocol registry with project scoping
- **Complexity**: Medium
- **Dependencies**: TASK-101-IDENT
- **Files to Create**: None
- **Files to Modify**:
  - `src/mcp_broker/protocol/registry.py`
  - `src/mcp_broker/mcp/tools.py`
- **Requirements**:
  - Add project_id parameter to all methods
  - Protocol isolation per project
  - Protocol sharing support (read-only)
  - Update register_protocol tool handler
  - Update discover_protocols tool handler
- **Acceptance Criteria**:
  - Protocols isolated by project
  - Protocol sharing functional
  - Backward compatible (defaults to "default" project)
  - Isolation tests passing

#### Task 104: Enhanced Session Manager
- **ID**: TASK-104-SESS
- **Description**: Extend session manager with project scoping
- **Complexity**: Medium
- **Dependencies**: TASK-101-IDENT
- **Files to Create**: None
- **Files to Modify**:
  - `src/mcp_broker/session/manager.py`
  - `src/mcp_broker/mcp/tools.py`
- **Requirements**:
  - Add project_id to session metadata
  - Project-scoped session listing
  - Isolated heartbeat monitoring
  - Cross-project session query for admins
  - Update list_sessions tool handler
- **Acceptance Criteria**:
  - Sessions isolated by project
  - Admin cross-project query working
  - Heartbeat isolation verified
  - Backward compatible

#### Task 105: Enhanced Message Router
- **ID**: TASK-105-ROUTE
- **Description**: Extend message router with project scoping
- **Complexity**: Medium
- **Dependencies**: TASK-101-IDENT, TASK-104-SESS
- **Files to Create**: None
- **Files to Modify**:
  - `src/mcp_broker/routing/router.py`
  - `src/mcp_broker/mcp/tools.py`
- **Requirements**:
  - Project-scoped message queues
  - Cross-project message rejection (default)
  - Message statistics per project
  - Update send_message tool handler
  - Update broadcast_message tool handler
- **Acceptance Criteria**:
  - Messages isolated by project
  - Cross-project rejected by default
  - Statistics tracked per project
  - Backward compatible

---

### Phase 3: Cross-Project Communication (Priority: MEDIUM)

#### Task 201: Cross-Project Router
- **ID**: TASK-201-CROSS
- **Description**: Implement optional cross-project communication
- **Complexity**: Complex
- **Dependencies**: TASK-105-ROUTE
- **Files to Create**:
  - `src/mcp_broker/routing/cross_project.py`
  - `src/mcp_broker/project/cross_project_config.py`
- **Files to Modify**:
  - `src/mcp_broker/routing/router.py`
- **Requirements**:
  - Permission validation for cross-project messages
  - Protocol compatibility checking
  - Rate limiting per cross-project relationship
  - Mutual consent verification
  - Opt-in only (disabled by default)
- **Acceptance Criteria**:
  - Cross-project communication opt-in only
  - Mutual consent required and verified
  - Protocol compatibility checked
  - Rate limits enforced
  - Audit logging for all cross-project messages

#### Task 202: Project Discovery
- **ID**: TASK-202-DISC
- **Description**: Implement project discovery mechanism
- **Complexity**: Simple
- **Dependencies**: TASK-102-TOOLS
- **Files to Create**: None
- **Files to Modify**:
  - `src/mcp_broker/project/registry.py`
- **Requirements**:
  - List discoverable projects
  - Filter by name/description
  - Include only public metadata
  - Support discoverable flag
  - Cross-project compatibility matrix
- **Acceptance Criteria**:
  - Discovery API functional
  - Public metadata only exposed
  - Discoverable flag respected
  - Compatibility matrix computed

---

### Phase 4: Testing and Quality (Priority: HIGH)

#### Task 301: Integration Tests for Multi-Project
- **ID**: TASK-301-INT-002
- **Description**: Complete integration test coverage for multi-project features
- **Complexity**: Medium
- **Dependencies**: TASK-105-ROUTE, TASK-202-DISC
- **Files to Create**:
  - `tests/integration/test_project_tools.py`
  - `tests/integration/test_cross_project.py`
  - `tests/integration/test_isolation.py`
- **Files to Modify**: None
- **Requirements**:
  - Test project lifecycle (create, list, update, delete)
  - Test API key rotation
  - Test session isolation
  - Test protocol isolation
  - Test message isolation
  - Test cross-project communication
  - Test project discovery
- **Acceptance Criteria**:
  - All scenarios tested
  - 85%+ coverage achieved
  - All tests passing

#### Task 302: Migration Tests
- **ID**: TASK-302-MIG
- **Description**: Test migration from single-project to multi-project
- **Complexity**: Medium
- **Dependencies**: TASK-301-INT-002
- **Files to Create**:
  - `tests/integration/test_migration.py`
- **Files to Modify**: None
- **Requirements**:
  - Test default project creation
  - Test data migration from single to multi-project
  - Test backward compatibility
  - Test rollback procedure
- **Acceptance Criteria**:
  - Migration script functional
  - Data integrity verified
  - Backward compatibility maintained
  - Rollback tested

#### Task 303: Documentation Updates
- **ID**: TASK-303-DOCS
- **Description**: Update documentation with multi-project features
- **Complexity**: Simple
- **Dependencies**: TASK-302-MIG
- **Files to Create**:
  - `docs/multi-project-setup.md`
  - `docs/migration-guide.md`
  - `docs/cross-project-communication.md`
- **Files to Modify**:
  - `README.md`
- **Requirements**:
  - Multi-project setup guide
  - Migration guide from single-project
  - Cross-project communication guide
  - API documentation with project parameters
  - Example configurations
- **Acceptance Criteria**:
  - All documentation complete
  - Examples tested
  - API docs accurate

---

## 3. Implementation Phases

### Phase 1: Base SPEC Completion (Week 1)

**Goal**: Complete SPEC-MCP-BROKER-001 to 100%

**Tasks**:
- TASK-001-REDIS (Redis Storage)
- TASK-002-SSE (SSE Endpoints)
- TASK-003-INT-001 (Integration Tests)
- TASK-004-LOAD (Load Testing)

**Success Criteria**:
- All SPEC-MCP-BROKER-001 requirements implemented
- 85%+ test coverage
- Load tests passing
- Documentation updated

### Phase 2: Multi-Project Foundation (Week 2)

**Goal**: Establish project isolation infrastructure

**Tasks**:
- TASK-101-IDENT (Identification Middleware)
- TASK-102-TOOLS (Project Management Tools)
- TASK-103-PROTO (Enhanced Protocol Registry)
- TASK-104-SESS (Enhanced Session Manager)
- TASK-105-ROUTE (Enhanced Message Router)

**Success Criteria**:
- Project identification functional
- Project management tools working
- Component isolation verified
- Backward compatibility maintained

### Phase 3: Cross-Project Features (Week 3)

**Goal**: Implement optional cross-project communication

**Tasks**:
- TASK-201-CROSS (Cross-Project Router)
- TASK-202-DISC (Project Discovery)

**Success Criteria**:
- Cross-project communication opt-in only
- Mutual consent verified
- Discovery API functional

### Phase 4: Quality and Documentation (Week 4)

**Goal**: Comprehensive testing and documentation

**Tasks**:
- TASK-301-INT-002 (Multi-Project Integration Tests)
- TASK-302-MIG (Migration Tests)
- TASK-303-DOCS (Documentation Updates)

**Success Criteria**:
- 85%+ test coverage
- All TRUST 5 quality gates passed
- Documentation complete
- Migration path validated

---

## 4. Risk Assessment

### Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Redis connection instability | High | Low | Retry logic with exponential backoff, fallback to in-memory |
| Cross-project data leakage | Critical | Medium | Namespace validation at storage layer, security audit |
| Performance degradation | Medium | Medium | Benchmark at each milestone, optimize hot paths |
| Breaking existing deployments | High | Low | Comprehensive backward compatibility tests |
| API key format conflicts | Medium | Low | Validation on creation, clear error messages |

### Operational Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Migration data loss | Critical | Low | Backup before migration, verification tests |
| Session state inconsistency | High | Low | Periodic state persistence, recovery procedures |
| Message delivery failure | High | Medium | Dead-letter queue, retry logic |

---

## 5. Acceptance Criteria

### Phase 1 Acceptance

- [ ] Redis storage backend functional with connection pooling
- [ ] SSE endpoints supporting 50+ concurrent connections
- [ ] All 6 MCP tools tested end-to-end
- [ ] Load test passing (50 sessions, 100 msg/s)
- [ ] P95 latency < 100ms, P99 < 500ms

### Phase 2 Acceptance

- [ ] Project identification working via API key, header, and connection parameter
- [ ] All 4 project management tools functional
- [ ] Component isolation verified (protocols, sessions, messages)
- [ ] Backward compatibility maintained (single-project mode works)

### Phase 3 Acceptance

- [ ] Cross-project communication opt-in only
- [ ] Mutual consent required and verified
- [ ] Protocol compatibility checked
- [ ] Rate limits enforced

### Phase 4 Acceptance

- [ ] 85%+ test coverage achieved
- [ ] All TRUST 5 quality gates passed
- [ ] Migration script tested and verified
- [ ] Documentation complete and accurate

---

## 6. Next Steps

### Immediate Actions (This Week)

1. **Start Phase 1**: Implement Redis storage backend (TASK-001-REDIS)
2. **Set up load testing environment**: Prepare Locust or custom pytest-asyncio setup
3. **Create integration test structure**: Set up test fixtures and helpers

### First Milestone (End of Week 1)

- Complete SPEC-MCP-BROKER-001 to 100%
- All integration tests passing
- Load test targets met

### Second Milestone (End of Week 2)

- Project identification middleware deployed
- Project management tools functional
- Component isolation verified

### Third Milestone (End of Week 3)

- Cross-project communication implemented
- Project discovery functional

### Final Milestone (End of Week 4)

- All tests passing (85%+ coverage)
- TRUST 5 quality gates passed
- Documentation complete
- Ready for production deployment

---

**END OF IMPLEMENTATION PLAN**

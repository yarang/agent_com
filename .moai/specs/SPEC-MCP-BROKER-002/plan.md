# Implementation Plan: SPEC-MCP-BROKER-002

## TAG BLOCK

```yaml
SPEC_ID: SPEC-MCP-BROKER-002
RELATED_DOCUMENTS:
  - SPEC: .moai/specs/SPEC-MCP-BROKER-002/spec.md
  - ACCEPTANCE: .moai/specs/SPEC-MCP-BROKER-002/acceptance.md
IMPLEMENTATION_STATUS: Planned
LAST_UPDATED: 2026-01-31
```

---

## Implementation Strategy

### Development Approach

This SPEC follows the **DDD (Domain-Driven Development)** approach:

1. **ANALYZE**: Understand existing SPEC-MCP-BROKER-001 implementation and identify extension points
2. **PRESERVE**: Write characterization tests for existing single-project behavior
3. **IMPROVE**: Incrementally add multi-project support with test validation

### Migration Strategy

**Phase 1 - Default Project (Non-Breaking)**
- Create "default" project and migrate existing resources
- Maintain backward compatibility for single-project deployments
- All existing operations continue working without modification

**Phase 2 - Identification Layer**
- Add project identification middleware
- Extend existing components with project scoping
- Add logging for missing project identifiers

**Phase 3 - Multi-Project Features**
- Enable project creation and management
- Implement cross-project communication
- Add project discovery capabilities

---

## Milestones

### Milestone 1: Foundation (Primary Goal)

**Objective**: Establish project infrastructure without breaking existing functionality

**Deliverables**:

1. **Project Data Models** (`src/mcp_broker/models/project.py`)
   - `ProjectDefinition` - Project metadata and configuration
   - `ProjectAPIKey` - API key model with project association
   - `ProjectConfig` - Project-specific settings
   - `ProjectPermissions` - Cross-project permissions

2. **Project Registry** (`src/mcp_broker/project/registry.py`)
   - `ProjectRegistry` class with CRUD operations
   - In-memory project storage
   - Project validation (name uniqueness, ID format)
   - API key generation and management

3. **Storage Namespace Extension** (`src/mcp_broker/storage/interface.py`)
   - Add `project_id` parameter to all storage methods
   - Implement namespace prefixing for keys
   - Add namespace isolation validation

4. **Default Project Migration**
   - Migration script to create "default" project
   - Data migration for existing protocols and sessions
   - Verification tests for data integrity

**Acceptance Criteria**:
- All existing tests pass without modification
- Default project created with all existing resources
- Storage operations properly namespace resources
- Zero breaking changes to existing API

---

### Milestone 2: Project Identification (Primary Goal)

**Objective**: Implement project identification mechanism for all incoming requests

**Deliverables**:

1. **Identification Middleware** (`src/mcp_broker/core/identification.py`)
   - `ProjectIdentificationMiddleware` class
   - API key prefix parsing
   - Header extraction (`X-Project-ID`)
   - Connection parameter resolution
   - Project context injection

2. **Enhanced Security Module** (`src/mcp_broker/core/security.py`)
   - Project-scoped authentication
   - API key validation with project association
   - Authorization checks for project boundaries
   - Audit logging for cross-project access attempts

3. **Request Context Enhancement** (`src/mcp_broker/core/context.py`)
   - `RequestContext` with project_id field
   - Context propagation through request lifecycle
   - Thread-safe context storage

4. **Identification Tests** (`tests/unit/test_identification.py`)
   - API key prefix parsing tests
   - Header extraction tests
   - Fallback behavior tests
   - Security boundary violation tests

**Acceptance Criteria**:
- All requests include project identification
- Missing identification returns 401 Unauthorized
- Cross-project access attempts are blocked
- Audit logs capture all identification events

---

### Milestone 3: Component Enhancement (Primary Goal)

**Objective**: Extend existing components with project scoping

**Deliverables**:

1. **Enhanced Protocol Registry** (`src/mcp_broker/protocol/registry.py`)
   - Add `project_id` parameter to all methods
   - Protocol isolation per project
   - Protocol sharing support (read-only cross-project references)
   - Update MCP tool handlers

2. **Enhanced Session Manager** (`src/mcp_broker/session/manager.py`)
   - Add `project_id` to session metadata
   - Project-scoped session listing
   - Isolated heartbeat monitoring
   - Cross-project session query for admins

3. **Enhanced Message Router** (`src/mcp_broker/routing/router.py`)
   - Project-scoped message queues
   - Cross-project message rejection (default)
   - Message statistics per project
   - Delivery confirmation with project context

4. **Enhanced Capability Negotiator** (`src/mcp_broker/negotiation/negotiator.py`)
   - Project-scoped negotiation
   - Protocol compatibility check within project
   - Cross-project compatibility reporting

**Acceptance Criteria**:
- All components support project scoping
- Isolation tests verify no cross-project data leakage
- Existing MCP tools work with project context
- Performance impact is minimal (<10% overhead)

---

### Milestone 4: Project Management APIs (Secondary Goal)

**Objective**: Expose project management functionality through MCP tools

**Deliverables**:

1. **Project Management Tools** (`src/mcp_broker/mcp/project_tools.py`)
   - `create_project` tool implementation
   - `list_projects` tool implementation
   - `get_project_info` tool implementation
   - `rotate_project_keys` tool implementation
   - `delete_project` tool implementation (soft delete)

2. **Enhanced Existing Tools** (`src/mcp_broker/mcp/tools.py`)
   - Add `project_id` parameter to `register_protocol`
   - Add `include_shared` parameter to `discover_protocols`
   - Add project filter to `list_sessions`
   - Add `target_project_id` parameter to `send_message` (admin only)

3. **Admin Permission System** (`src/mcp_broker/core/admin.py`)
   - Admin role detection
   - Cross-project access authorization
   - Permission caching for performance

4. **Tool Integration Tests** (`tests/integration/test_project_tools.py`)
   - Project lifecycle tests
   - Permission verification tests
   - API key rotation tests
   - Cross-project tool access tests

**Acceptance Criteria**:
- All project management tools functional
- Admin permissions properly enforced
- Tool documentation updated
- Integration tests pass for all scenarios

---

### Milestone 5: Cross-Project Communication (Secondary Goal)

**Objective**: Implement optional, explicitly configured cross-project communication

**Deliverables**:

1. **Cross-Project Router** (`src/mcp_broker/routing/cross_project.py`)
   - `CrossProjectRouter` class
   - Permission validation for cross-project messages
   - Protocol compatibility checking across projects
   - Rate limiting per cross-project relationship

2. **Cross-Project Configuration** (`src/mcp_broker/project/cross_project_config.py`)
   - `CrossProjectConfig` model
   - Mutual consent tracking
   - Permission rules storage
   - Configuration validation

3. **Enhanced Message Router** (`src/mcp_broker/routing/router.py`)
   - Integrate cross-project router
   - Fallback to isolated routing if not configured
   - Cross-project delivery confirmation

4. **Cross-Project Tests** (`tests/integration/test_cross_project.py`)
   - Permission validation tests
   - Message delivery tests
   - Protocol transformation tests
   - Rate limiting tests

**Acceptance Criteria**:
- Cross-project communication is opt-in only
- Mutual consent is required and verified
- Protocol compatibility is checked before delivery
- Rate limits are enforced

---

### Milestone 6: Storage Isolation (Secondary Goal)

**Objective**: Ensure complete storage isolation with efficient namespace handling

**Deliverables**:

1. **Enhanced Storage Interface** (`src/mcp_broker/storage/interface.py`)
   - `project_id` parameter required for all operations
   - Namespace prefix validation
   - Cross-project access detection and rejection

2. **In-Memory Storage Enhancement** (`src/mcp_broker/storage/memory.py`)
   - Project-scoped dict instances
   - Namespace-aware key generation
   - Isolation verification tests

3. **Redis Storage Enhancement** (`src/mcp_broker/storage/redis.py`)
   - Key prefix pattern: `{project_id}:{resource_type}:{resource_id}`
   - Separate Redis database option per project
   - Connection pooling with project context

4. **Storage Isolation Tests** (`tests/unit/test_storage_isolation.py`)
   - Namespace boundary tests
   - Cross-project access rejection tests
   - Data migration verification tests

**Acceptance Criteria**:
- Complete storage isolation verified
- No cross-project data access possible
- Performance impact minimal (<5% overhead)
- Redis and in-memory implementations consistent

---

### Milestone 7: Testing and Documentation (Final Goal)

**Objective**: Comprehensive test coverage and documentation

**Deliverables**:

1. **Test Suite Completion**
   - Unit tests for all new components (85%+ coverage)
   - Integration tests for multi-project scenarios
   - Migration tests from single to multi-project
   - Load tests for project isolation overhead

2. **Documentation Updates**
   - Multi-project setup guide
   - API documentation with project parameters
   - Migration guide from single-project
   - Cross-project communication guide
   - Security considerations document

3. **Example Configurations**
   - Single-project mode (backward compatible)
   - Multi-project setup
   - Cross-project communication example
   - Docker Compose with multiple projects

4. **Changelog Update**
   - Document breaking changes (none planned)
   - Document new features
   - Document deprecations

**Acceptance Criteria**:
- 85%+ test coverage achieved
- All integration tests pass
- Documentation is complete and accurate
- Example configurations are tested

---

## Technical Approach

### Architecture Decisions

**Decision 1: API Key Prefix Format**

*Choice*: `{project_id}_{key_id}_{secret}` format

*Reasoning*:
- Allows project identification without database lookup
- Maintains human-readable project association
- Supports multiple keys per project
- Compatible with existing API key patterns

*Alternatives Considered*:
- Separate header for project ID: Requires additional client configuration
- JWT tokens with project claim: Overhead for token validation
- Database lookup for all requests: Performance impact

**Decision 2: Storage Namespace Pattern**

*Choice*: Key prefix pattern `{project_id}:{resource_type}:{resource_id}`

*Reasoning*:
- Works with both in-memory and Redis storage
- Simple prefix filtering for project queries
- Maintains existing storage interface
- Easy to implement and verify

*Alternatives Considered*:
- Separate database per project: Increased operational complexity
- Separate Redis database per project: Limited to 16 databases
- Namespace column in relational model: Requires schema migration

**Decision 3: Backward Compatibility Strategy**

*Choice*: Default project with automatic migration

*Reasoning*:
- Zero breaking changes for existing deployments
- Gradual migration path to multi-project
- Single configuration mode for simple deployments
- Clear upgrade path

*Alternatives Considered*:
- Breaking change with migration guide: User friction
- Separate deployment mode: Code duplication
- Feature flag for multi-project: Additional complexity

### Implementation Order

**Phase 1: Core Infrastructure**
1. Project models and registry
2. Storage namespace extension
3. Identification middleware
4. Default project migration

**Phase 2: Component Enhancement**
5. Protocol Registry enhancement
6. Session Manager enhancement
7. Message Router enhancement
8. Capability Negotiator enhancement

**Phase 3: API Layer**
9. Project management MCP tools
10. Enhanced existing MCP tools
11. Admin permission system
12. Cross-project communication

**Phase 4: Quality Assurance**
13. Test suite completion
14. Documentation updates
15. Performance testing
16. Security audit

### Risk Mitigation

**Risk 1: Performance Degradation**
- Mitigation: Namespace prefix caching
- Mitigation: Connection pooling for Redis
- Mitigation: Performance benchmarking at each milestone

**Risk 2: Data Migration Issues**
- Mitigation: Comprehensive migration tests
- Mitigation: Rollback plan for migration failures
- Mitigation: Data verification scripts

**Risk 3: Cross-Project Data Leakage**
- Mitigation: Namespace validation at storage layer
- Mitigation: Security audit of isolation implementation
- Mitigation: Penetration testing for cross-project access

**Risk 4: Breaking Existing Deployments**
- Mitigation: Backward compatibility tests
- Mitigation: Default project automatic migration
- Mitigation: Feature flag for gradual rollout

---

## Dependencies and Integration

### External Dependencies

```python
# New dependencies for multi-project support
cryptography >= 41.0.0  # API key generation
python-dateutil >= 2.8.0  # Date/time handling
```

### Component Dependencies

```
ProjectIdentificationMiddleware
    ↓
ProjectRegistry (project validation)
    ↓
Enhanced Components (ProtocolRegistry, SessionManager, etc.)
    ↓
Storage Layer (namespace isolation)
    ↓
MCP Tools (project-scoped operations)
```

### Integration Points

1. **FastAPI App** (`main.py`)
   - Add identification middleware
   - Add project management endpoints (admin only)

2. **MCPServer** (`mcp/server.py`)
   - Pass project context to tool handlers
   - Enhanced tool registration

3. **Storage Backend** (`storage/interface.py`)
   - All methods require project_id parameter
   - Namespace validation on all operations

---

## Quality Gates

### TRUST 5 Validation

**Tested**:
- 85%+ unit test coverage for new code
- Integration tests for multi-project scenarios
- Migration tests for single to multi-project
- Load tests for isolation overhead

**Readable**:
- Type hints on all new functions
- Docstrings with project context
- Clear naming for project-scoped operations

**Unified**:
- Consistent namespace prefix pattern
- Pydantic models for all project data
- Structured logging with project_id

**Secured**:
- Namespace validation at storage layer
- Project authentication at all entry points
- Audit logging for cross-project operations

**Trackable**:
- Project creation events logged
- Cross-project message tracking
- API key rotation events logged

### Performance Targets

- Namespace overhead: <5% for storage operations
- Identification latency: <10ms per request
- Cross-project message latency: <150ms
- Project listing: <100ms for 100 projects

### Security Validation

- No cross-project data access possible
- API key format enforced and validated
- Audit trail for all administrative operations
- Penetration testing for isolation bypass

---

## Migration Path from SPEC-MCP-BROKER-001

### Step 1: Characterization Tests

Create tests capturing existing single-project behavior:
- Protocol registration and discovery
- Session lifecycle
- Message routing patterns
- Authentication flow

### Step 2: Default Project Creation

Run migration script:
1. Stop broker server
2. Create "default" project in registry
3. Migrate existing protocols to default project
4. Migrate existing sessions to default project
5. Verify data integrity
6. Start broker server

### Step 3: Feature Rollout

Enable multi-project features:
1. Update configuration to enable project identification
2. Test with existing single-project setup
3. Create additional test projects
4. Verify isolation between projects
5. Enable cross-project communication (optional)

### Step 4: Client Updates

Update client applications:
1. Include project identification in requests
2. Update API keys to new format
3. Test with both single and multi-project modes

---

## Rollback Plan

If issues occur during rollout:

**Phase 1 Rollback** (Foundation):
- Remove "default" project
- Restore pre-migration storage state
- All existing functionality restored

**Phase 2 Rollback** (Identification):
- Disable identification middleware
- Default to "default" project for all requests
- Maintain multi-project capability but not enforced

**Phase 3 Rollback** (Multi-Project Features):
- Disable project creation API
- Existing projects remain but no new projects
- Cross-project communication disabled

---

## Success Metrics

### Functional Metrics
- All existing tests pass without modification
- New multi-project tests achieve 85%+ coverage
- Zero cross-project data leakage verified
- Migration from single to multi-project succeeds

### Performance Metrics
- <5% overhead for namespace operations
- <10ms latency for project identification
- <100ms latency for project listing (100 projects)

### Quality Metrics
- Zero critical security vulnerabilities
- All TRUST 5 quality gates passed
- Documentation complete and accurate

### Adoption Metrics
- Single-project deployments continue working
- Multi-project setups can be created easily
- Migration path is clear and documented

---

## Next Steps

After completion of SPEC-MCP-BROKER-002:

1. **Run /moai:2-run SPEC-MCP-BROKER-002** to begin implementation
2. **Execute migration script** on existing deployments
3. **Update documentation** with multi-project examples
4. **Create training materials** for multi-project setup
5. **Monitor metrics** for performance and security

---

**END OF IMPLEMENTATION PLAN - SPEC-MCP-BROKER-002**

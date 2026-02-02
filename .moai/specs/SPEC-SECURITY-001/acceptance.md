# SPEC-SECURITY-001: Acceptance Criteria

**Version:** 1.0.0
**Created:** 2026-02-02
**Status:** Planned

---

## TAG BLOCK

```yaml
tags:
  - acceptance
  - testing
  - quality-gates

traceability:
  spec: SPEC-SECURITY-001
  plan: SPEC-SECURITY-001/plan.md
```

---

## 1. Definition of Done

A requirement is considered **Done** when:

1. **Code Complete:** Implementation is complete and committed
2. **Test Coverage:** Unit tests with 85%+ coverage
3. **Integration Tests:** All integration test scenarios pass
4. **Documentation:** API documentation updated
5. **Code Review:** Approved by at least one reviewer
6. **Security Review:** No critical vulnerabilities identified

---

## 2. Acceptance Criteria (Given-When-Then Format)

### 2.1 Authentication

#### AC-AUTH-001: User Login with OAuth

**Given:** a registered user with valid credentials
**When:** the user submits login request with username and password
**Then:** the system returns JWT access and refresh tokens
**And:** the tokens have valid expiration times
**And:** the login event is logged to audit_logs

```gherkin
Feature: User Login
  Scenario: Successful login with valid credentials
    Given a user exists with username "testuser" and active status
    And the user has password "securepassword123"
    When the user POSTs to "/api/v1/auth/login" with:
      | username | testuser |
      | password | securepassword123 |
    Then the response status is 200
    And the response contains "access_token"
    And the response contains "refresh_token"
    And the response contains "expires_in" of 900
    And an audit log entry is created with action="login"

  Scenario: Login fails with invalid credentials
    Given a user exists with username "testuser"
    When the user POSTs to "/api/v1/auth/login" with:
      | username | testuser |
      | password | wrongpassword |
    Then the response status is 401
    And the response contains error detail
    And a failed login event is logged to audit_logs

  Scenario: Login fails for inactive user
    Given a user exists with username "testuser" and is_active=false
    When the user POSTs to "/api/v1/auth/login" with:
      | username | testuser |
      | password | anypassword |
    Then the response status is 403
    And the response contains "User account is inactive"
```

#### AC-AUTH-002: Token Refresh

**Given:** a user with a valid refresh token
**When:** the user submits refresh token request
**Then:** the system returns a new access token
**And:** the new access token has valid expiration

```gherkin
Feature: Token Refresh
  Scenario: Successful token refresh
    Given a user has a valid refresh token
    When the user POSTs to "/api/v1/auth/refresh" with refresh token
    Then the response status is 200
    And the response contains a new "access_token"
    And the new access token expires in 15 minutes

  Scenario: Refresh fails with invalid token
    Given a user has an invalid refresh token
    When the user POSTs to "/api/v1/auth/refresh" with invalid token
    Then the response status is 401
    And the response contains error detail
```

#### AC-AUTH-003: Agent Authentication with API Key

**Given:** an agent with a valid project-bound API key
**When:** the agent makes an API request with the key
**Then:** the system validates the key and grants access
**And:** the request context includes project_id
**And:** RLS policies filter data by project_id

```gherkin
Feature: Agent Authentication
  Scenario: Agent authenticates with valid API key
    Given an agent exists with API key "sk_agent_v1_550e8400_agent123_a1b2c3d4"
    And the agent is bound to project "test-project"
    When the agent sends a GET request to "/api/v1/communications"
    And the request includes "Authorization: Bearer sk_agent_v1_550e8400_agent123_a1b2c3d4"
    Then the response status is 200
    And the response only contains data from project "test-project"

  Scenario: Agent authentication fails with invalid key
    Given an agent exists
    When the agent sends a request with invalid API key
    Then the response status is 401
    And the response contains "Invalid agent token"

  Scenario: Agent cannot access other projects
    Given an agent is bound to project "project-a"
    When the agent attempts to access data from project "project-b"
    Then the response status is 403
    Or the response returns empty results (RLS enforcement)
```

### 2.2 Project Management

#### AC-PROJ-001: Create Project

**Given:** an authenticated human user
**When:** the user creates a new project
**Then:** the system creates the project with user as owner
**And:** the project has unique project_id
**And:** the creation is logged to audit_logs

```gherkin
Feature: Create Project
  Scenario: Successful project creation
    Given a user is authenticated with JWT token
    And the user has username "projectowner"
    When the user POSTs to "/api/v1/projects" with:
      | project_id | my-new-project |
      | name | My New Project |
      | description | A test project |
    Then the response status is 201
    And the response contains project "id"
    And the response contains "owner_id" matching the user
    And an audit log entry is created with action="project_create"

  Scenario: Project creation fails with duplicate project_id
    Given a project exists with project_id "existing-project"
    When the user POSTs to "/api/v1/projects" with:
      | project_id | existing-project |
      | name | Duplicate Project |
    Then the response status is 409
    And the response contains "Project ID already exists"
```

#### AC-PROJ-002: List Projects

**Given:** an authenticated user
**When:** the user requests their projects
**Then:** the system returns only projects owned by the user
**And:** each project includes owner_id

```gherkin
Feature: List Projects
  Scenario: User sees only their projects
    Given user "alice" owns projects "project-a" and "project-b"
    And user "bob" owns projects "project-c"
    When user "alice" GETs "/api/v1/projects"
    Then the response contains 2 projects
    And the response includes "project-a"
    And the response includes "project-b"
    And the response does NOT include "project-c"

  Scenario: Superuser sees all projects
    Given a superuser exists
    And multiple projects exist owned by different users
    When the superuser GETs "/api/v1/projects"
    Then the response contains all projects
```

#### AC-PROJ-003: Delete Project

**Given:** a project owner
**When:** the owner deletes their project
**Then:** the system deletes the project
**And:** all associated data is cascade deleted
**And:** the deletion is logged to audit_logs

```gherkin
Feature: Delete Project
  Scenario: Owner can delete their project
    Given a user owns a project "test-project"
    When the user DELETEs "/api/v1/projects/{project_id}"
    Then the response status is 200
    And the project no longer exists
    And all project communications are deleted
    And all project meetings are deleted
    And an audit log entry is created with action="project_delete"

  Scenario: Non-owner cannot delete project
    Given a user "alice" owns a project
    And a different user "bob" exists
    When user "bob" attempts to DELETE "/api/v1/projects/{project_id}"
    Then the response status is 403
    And the project still exists
```

### 2.3 Row-Level Security

#### AC-RLS-001: Project Data Isolation

**Given:** two projects with data
**When:** a user from project A queries data
**Then:** the system returns only project A data
**And:** no data from project B is accessible

```gherkin
Feature: Row-Level Security
  Scenario: Agents can only access their project data
    Given "project-a" has 10 communications
    And "project-b" has 20 communications
    And an agent is bound to "project-a"
    When the agent queries for all communications
    Then exactly 10 communications are returned
    And all 10 communications have project_id matching "project-a"
    And no communications from "project-b" are returned

  Scenario: SQL injection cannot bypass RLS
    Given an agent is bound to "project-a"
    When the agent attempts to inject SQL to access other projects
    Then the injection attempt is blocked by ORM
    Or the RLS policy filters out non-project data
    And the response contains only project-a data or error
```

#### AC-RLS-002: RLS Policy Validation

**Given:** RLS policies are enabled on all tables
**When:** a query is executed with project context
**Then:** the RLS policy filters by project_id
**And:** the filter uses app.current_project_id setting

```gherkin
Feature: RLS Policy Enforcement
  Scenario: RLS policy filters communications
    Given RLS is enabled on communications table
    And app.current_project_id is set to "project-a-id"
    When a query executes "SELECT * FROM communications"
    Then only communications with project_id = "project-a-id" are returned

  Scenario: RLS prevents cross-project access
    Given RLS is enabled on decisions table
    And app.current_project_id is set to "project-a-id"
    When a query attempts to access decisions from "project-b-id"
    Then no decisions are returned
    Or an access denied error occurs
```

### 2.4 Audit Logging

#### AC-AUDIT-001: Critical Actions Logged

**Given:** a critical action occurs (create, update, delete, login)
**When:** the action is executed
**Then:** the system logs the action to audit_logs
**And:** the log includes action, entity_type, entity_id, actor
**And:** the log includes timestamp and IP address

```gherkin
Feature: Audit Logging
  Scenario: Login is logged
    Given a user with username "testuser"
    When the user logs in successfully
    Then an audit log entry exists with:
      | action | login |
      | entity_type | user |
      | actor_type | human |
    And the log includes the user's ID
    And the log includes a timestamp
    And the log includes IP address

  Scenario: Project creation is logged
    Given a user creates a project
    Then an audit log entry exists with:
      | action | project_create |
      | entity_type | project |
      | actor_type | human |
    And the log includes the project ID
    And the log includes action_details

  Scenario: Communication creation is logged
    Given an agent creates a communication
    Then an audit log entry exists with:
      | action | create |
      | entity_type | communication |
      | actor_type | agent |
    And the log includes the communication ID
```

#### AC-AUDIT-002: Audit Log Immutability

**Given:** an audit log entry exists
**When:** an update or delete is attempted on the entry
**Then:** the system rejects the modification
**And:** returns an error

```gherkin
Feature: Audit Log Immutability
  Scenario: Audit log cannot be updated
    Given an audit log entry exists
    When a user attempts to UPDATE the audit log entry
    Then the update is rejected
    And an error is raised: "Cannot modify immutable audit log"

  Scenario: Audit log cannot be deleted
    Given an audit log entry exists
    When a user attempts to DELETE the audit log entry
    Then the delete is rejected
    And an error is raised: "Cannot modify immutable audit log"
```

### 2.5 Security Measures

#### AC-SEC-001: Rate Limiting

**Given:** an agent with valid API key
**When:** the agent exceeds rate limit
**Then:** the system returns 429 Too Many Requests
**And:** includes Retry-After header

```gherkin
Feature: Rate Limiting
  Scenario: Agent is rate limited
    Given an agent has a rate limit of 60 requests per minute
    And the agent has made 60 requests in the last minute
    When the agent makes another request
    Then the response status is 429
    And the response includes "Retry-After" header
    And the error message mentions rate limit

  Scenario: Rate limit resets after window
    Given an agent has been rate limited
    And 60 seconds have passed since the first request
    When the agent makes a new request
    Then the response status is 200
    And the request is processed
```

#### AC-SEC-002: Kill Switch (Panic)

**Given:** a superuser
**When:** the superuser triggers panic endpoint
**Then:** all agent API keys are revoked
**And:** all active sessions are terminated
**And:** the action is logged to audit_logs

```gherkin
Feature: Emergency Kill Switch
  Scenario: Superuser can trigger panic
    Given a superuser is authenticated
    And 100 active agent API keys exist
    When the superuser POSTs to "/api/v1/security/panic" with reason="Security incident"
    Then all 100 agent API keys are marked as "revoked"
    And an audit log entry is created with action="panic"
    And all active agent sessions are terminated
    And the response confirms the number of keys revoked

  Scenario: Non-superuser cannot trigger panic
    Given a regular user is authenticated
    When the user POSTs to "/api/v1/security/panic"
    Then the response status is 403
    And no API keys are revoked
```

#### AC-SEC-003: Password Security

**Given:** a user account
**When:** the password is stored
**Then:** the password is hashed with bcrypt
**And:** the hash uses cost factor of 12
**And:** plaintext password is never stored

```gherkin
Feature: Password Security
  Scenario: Password is hashed with bcrypt
    Given a user is created with password "plaintext123"
    When the user record is saved to database
    Then the password_hash column contains a bcrypt hash
    And the hash starts with "$2b$12$" (bcrypt cost 12)
    And the plaintext password is NOT stored anywhere

  Scenario: Password cannot be retrieved
    Given a user exists with password
    When a database query selects the user
    Then the response contains password_hash
    And the response does NOT contain the plaintext password
```

### 2.6 Cross-Project Permissions

#### AC-CROSS-001: Cross-Project Access Blocked by Default

**Given:** two projects A and B
**When:** an agent from project A attempts to access project B
**Then:** the system denies access
**And:** returns 403 Forbidden

```gherkin
Feature: Cross-Project Access Control
  Scenario: Cross-project access denied by default
    Given project "alpha" exists with allow_cross_project=false
    And project "beta" exists
    And an agent is bound to project "alpha"
    When the agent attempts to access project "beta" data
    Then the response status is 403
    And the error message mentions cross-project access

  Scenario: Cross-project access allowed with permission
    Given project "alpha" exists with allow_cross_project=true
    And project "alpha" has permission for project "beta"
    And an agent is bound to project "alpha"
    When the agent attempts to access project "beta" data
    Then the response status is 200
    And the agent can access project "beta" data
```

---

## 3. Quality Gates

### 3.1 TRUST 5 Validation

| Pillar | Criteria | Status |
|--------|----------|--------|
| **Tested** | 85%+ code coverage, all integration tests pass | Pending |
| **Readable** | Clear naming, English comments, formatted code | Pending |
| **Unified** | Consistent style, passes linter (ruff/black) | Pending |
| **Secured** | OWASP compliance, no critical vulnerabilities | Pending |
| **Trackable** | Commits follow conventional format, SPEC referenced | Pending |

### 3.2 LSP Quality Gates

| Phase | Max Errors | Max Type Errors | Max Lint Errors |
|-------|------------|-----------------|-----------------|
| Plan | N/A | N/A | N/A |
| Run | 0 | 0 | 0 |
| Sync | 0 | 0 | 10 (warnings allowed) |

### 3.3 Security Validation

| Check | Status |
|-------|--------|
| No SQL injection vulnerabilities | Pending |
| No stored XSS vulnerabilities | Pending |
| Passwords hashed with bcrypt (cost 12) | Pending |
| API keys hashed with SHA-256 | Pending |
| JWT secret is 32+ characters | Pending |
| HTTPS enforced in production | Pending |
| CORS properly configured | Pending |
| Security headers present | Pending |

---

## 4. Test Scenarios Summary

### 4.1 Unit Tests

| Component | Test Cases | Target |
|-----------|------------|--------|
| JWT Service | 15 | 100% |
| API Key Service | 12 | 100% |
| Repository Base | 20 | 90% |
| Auth Service | 18 | 90% |
| Project Service | 15 | 85% |
| Audit Service | 10 | 85% |

### 4.2 Integration Tests

| Scenario | Endpoints | Status |
|----------|-----------|--------|
| OAuth Flow | /auth/login, /auth/refresh, /auth/logout | Pending |
| Agent Auth | All endpoints with agent token | Pending |
| Project CRUD | /projects/* | Pending |
| RLS Isolation | All data endpoints | Pending |
| Audit Logging | All write operations | Pending |
| Rate Limiting | All endpoints | Pending |
| Kill Switch | /security/panic | Pending |

### 4.3 Security Tests

| Test Type | Tool | Status |
|-----------|------|--------|
| SQL Injection | Manual + automated | Pending |
| XSS | Manual + automated | Pending |
| CSRF | Manual review | Pending |
| Authentication Bypass | Penetration testing | Pending |
| Authorization Bypass | Penetration testing | Pending |

---

## 5. Verification Methods

### 5.1 Automated Testing

```bash
# Unit tests
pytest tests/unit/ -v --cov=src --cov-report=html

# Integration tests
pytest tests/integration/ -v

# Security tests
bandit -r src/
pylint src/ --enable=security

# Linting
ruff check src/
black --check src/
mypy src/
```

### 5.2 Manual Testing

**Authentication:**
- [ ] Login with valid credentials succeeds
- [ ] Login with invalid credentials fails
- [ ] Token refresh works
- [ ] Logout invalidates refresh token

**Project Management:**
- [ ] Create project succeeds
- [ ] List projects shows only owned projects
- [ ] Update project requires ownership
- [ ] Delete project cascades to all data

**RLS Verification:**
```sql
-- Test RLS policy
SET app.current_project_id = 'project-a-id';
SELECT * FROM communications;  -- Should only return project-a

SET app.current_project_id = 'project-b-id';
SELECT * FROM communications;  -- Should only return project-b
```

**Audit Log Verification:**
```sql
-- Check audit log for event
SELECT * FROM audit_logs
WHERE action = 'login'
  AND actor_id = 'user-id'
ORDER BY occurred_at DESC
LIMIT 1;
```

### 5.3 Performance Testing

| Metric | Target | Status |
|--------|--------|--------|
| Login latency | < 200ms | Pending |
| API key validation | < 50ms | Pending |
| RLS query overhead | < 10% | Pending |
| Audit log write | < 20ms | Pending |
| Rate limit check | < 5ms | Pending |

---

## 6. Sign-Off

### 6.1 Approval Checklist

- [ ] All acceptance criteria met
- [ ] Unit tests passing (85%+ coverage)
- [ ] Integration tests passing
- [ ] Security review completed
- [ ] Performance benchmarks met
- [ ] Documentation updated
- [ ] Code review approved

### 6.2 Stakeholder Approval

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Security Lead | | | |
| Backend Lead | | | |
| QA Lead | | | |
| Product Owner | | | |

---

**Document Owner:** QA Team
**Last Updated:** 2026-02-02
**Next Review:** Upon completion of each milestone

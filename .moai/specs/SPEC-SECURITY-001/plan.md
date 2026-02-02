# SPEC-SECURITY-001: Implementation Plan

**Version:** 1.0.0
**Created:** 2026-02-02
**Status:** Planned

---

## TAG BLOCK

```yaml
tags:
  - security
  - implementation
  - migration

traceability:
  spec: SPEC-SECURITY-001
  requirements:
    - REQ-SEC-001 through REQ-SEC-405
```

---

## 1. Milestones (Priority-Based)

### Milestone 1: Foundation (Primary Goal)

**Objective:** Establish database schema and core authentication infrastructure

**Deliverables:**
- Database schema with all security tables
- User and Project ORM models
- JWT authentication service
- API key generation and validation
- Base repository with project context injection

**Dependencies:** None

---

### Milestone 2: Row-Level Security (Primary Goal)

**Objective:** Implement database-level access control

**Deliverables:**
- RLS policies on all project-bound tables
- Project context middleware
- Security middleware for request processing
- Integration tests for RLS enforcement

**Dependencies:** Milestone 1

---

### Milestone 3: Audit Logging (Primary Goal)

**Objective:** Implement immutable audit trail

**Deliverables:**
- Audit log table and triggers
- Audit log query endpoints
- Audit event service
- Immutable audit log enforcement

**Dependencies:** Milestone 1

---

### Milestone 4: API Layer (Secondary Goal)

**Objective:** Implement authentication and project management APIs

**Deliverables:**
- Authentication endpoints (login, refresh, logout)
- Project CRUD endpoints
- Agent key management endpoints
- API documentation

**Dependencies:** Milestone 1, Milestone 2

---

### Milestone 5: Security Features (Secondary Goal)

**Objective:** Implement advanced security features

**Deliverables:**
- Rate limiting middleware
- Kill switch (panic endpoint)
- Cross-project permission validation
- Security status endpoint

**Dependencies:** Milestone 4

---

### Milestone 6: Testing & Documentation (Final Goal)

**Objective:** Complete testing and documentation

**Deliverables:**
- Unit tests (85%+ coverage)
- Integration tests
- Security audit
- API documentation
- Deployment guide

**Dependencies:** All previous milestones

---

## 2. Technical Approach

### 2.1 Architecture Design

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Security Architecture                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         API Layer (FastAPI)                          │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │   Auth API   │  │ Project API  │  │ Security API │              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   │                                         │
│                                   ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      Security Middleware                             │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │    Auth      │  │     RLS      │  │ Rate Limit   │              │   │
│  │  │  Validation  │  │   Context    │  │   Check      │              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   │                                         │
│                                   ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       Service Layer                                  │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │ Auth Service │  │ Project Svc  │  │  Audit Svc   │              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   │                                         │
│                                   ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Repository Layer (SQLAlchemy)                      │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │ User Repo    │  │Project Repo  │  │  Audit Repo  │              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  │  ┌──────────────────────────────────────────────────────┐          │   │
│  │  │         Base Repository (with RLS context)            │          │   │
│  │  └──────────────────────────────────────────────────────┘          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   │                                         │
│                                   ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      Database (PostgreSQL)                            │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │   │
│  │  │  users   │  │projects  │  │api_keys  │  │audit_logs│           │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │   │
│  │  ┌────────────────────────────────────────────────────────────┐     │   │
│  │  │           Row-Level Security Policies                       │     │   │
│  │  └────────────────────────────────────────────────────────────┘     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Database | PostgreSQL | 16+ |
| ORM | SQLAlchemy | 2.0+ |
| Migrations | Alembic | 1.13+ |
| JWT | python-jose | 3.3+ |
| Password Hashing | bcrypt | 4.0+ |
| API Framework | FastAPI | 0.115+ |
| Testing | pytest | 8.0+ |

### 2.3 Database Migration Strategy

**Migration Order:**

1. **Migration 001:** Create core tables (users, projects, agent_api_keys)
2. **Migration 002:** Add mandatory fields to existing tables
3. **Migration 003:** Enable Row-Level Security
4. **Migration 004:** Create audit infrastructure
5. **Migration 005:** Create cross-project permissions (optional)

**Rollback Plan:**
- Each migration has a corresponding downgrade function
- Rollback order is reverse of migration order
- Test rollback in development environment before production

### 2.4 Security Implementation Details

#### 2.4.1 JWT Token Generation

```python
# File: src/agent_comm_core/auth/jwt.py

from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from pydantic import BaseModel

class TokenPayload(BaseModel):
    sub: str  # user_id
    exp: datetime
    iat: datetime
    type: Literal["access", "refresh"]

class JWTService:
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_expire_minutes: int = 15,
        refresh_expire_days: int = 7
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_expire_minutes = access_expire_minutes
        self.refresh_expire_days = refresh_expire_days

    def create_access_token(self, user_id: str) -> str:
        """Create JWT access token."""
        now = datetime.utcnow()
        payload = TokenPayload(
            sub=user_id,
            exp=now + timedelta(minutes=self.access_expire_minutes),
            iat=now,
            type="access"
        )
        return jwt.encode(payload.model_dump(), self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user_id: str) -> str:
        """Create JWT refresh token."""
        now = datetime.utcnow()
        payload = TokenPayload(
            sub=user_id,
            exp=now + timedelta(days=self.refresh_expire_days),
            iat=now,
            type="refresh"
        )
        return jwt.encode(payload.model_dump(), self.secret_key, algorithm=self.algorithm)

    def validate_token(self, token: str) -> Optional[TokenPayload]:
        """Validate and decode JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return TokenPayload(**payload)
        except JWTError:
            return None
```

#### 2.4.2 API Key Generation

```python
# File: src/agent_comm_core/auth/api_key.py

import hashlib
import secrets
from typing import Tuple
from uuid import UUID

class APIKeyService:
    def __init__(self, prefix: str = "sk_agent"):
        self.prefix = prefix
        self.version = "v1"

    def generate_key(
        self,
        project_id: UUID,
        agent_id: UUID
    ) -> Tuple[str, str]:
        """
        Generate structured API key and hash.

        Returns:
            Tuple of (api_key, api_key_hash)
        """
        # Generate random hash component
        random_hash = secrets.token_hex(4)  # 8 characters

        # Format: sk_agent_v1_{project_id_8chars}_{agent_id}_{hash}
        project_prefix = str(project_id)[:8]
        api_key = f"{self.prefix}_{self.version}_{project_prefix}_{agent_id}_{random_hash}"

        # Generate SHA-256 hash for storage
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        return api_key, api_key_hash

    def validate_key(
        self,
        provided_key: str,
        stored_hash: str
    ) -> bool:
        """
        Validate API key against stored hash.

        Uses constant-time comparison to prevent timing attacks.
        """
        provided_hash = hashlib.sha256(provided_key.encode()).hexdigest()
        return secrets.compare_digest(provided_hash, stored_hash)

    def parse_key(self, api_key: str) -> dict:
        """
        Parse API key to extract components.
        """
        parts = api_key.split("_")

        if len(parts) < 6 or parts[0] != "sk" or parts[1] != "agent":
            raise ValueError("Invalid API key format")

        return {
            "prefix": f"{parts[0]}_{parts[1]}",
            "version": parts[2],
            "project_id_prefix": parts[3],
            "agent_id": parts[4],
            "hash": parts[5]
        }
```

#### 2.4.3 Base Repository with Project Context

```python
# File: src/agent_comm_core/db/repository.py

from typing import Generic, TypeVar, Type, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from agent_comm_core.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):
    """Base repository with automatic project_id injection for RLS."""

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    def _set_project_context(self, project_id: UUID) -> None:
        """Set PostgreSQL session variable for RLS."""
        self.session.execute(
            text("SET LOCAL app.current_project_id = :project_id"),
            {"project_id": str(project_id)}
        )

    def _set_actor_context(self, actor_type: str, actor_id: UUID) -> None:
        """Set actor context for audit logging."""
        self.session.execute(
            text("SET LOCAL app.actor_type = :actor_type"),
            {"actor_type": actor_type}
        )
        self.session.execute(
            text("SET LOCAL app.actor_id = :actor_id"),
            {"actor_id": str(actor_id)}
        )

    async def get_by_id(
        self,
        id: UUID,
        project_id: UUID
    ) -> Optional[ModelType]:
        """Get entity by ID with project_id filtering."""
        self._set_project_context(project_id)

        stmt = select(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        project_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> list[ModelType]:
        """List entities with project_id filtering."""
        self._set_project_context(project_id)

        stmt = select(self.model).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self,
        obj: ModelType,
        project_id: UUID,
        actor_type: str = "agent",
        actor_id: Optional[UUID] = None
    ) -> ModelType:
        """Create entity with audit context."""
        self._set_project_context(project_id)
        self._set_actor_context(
            actor_type,
            actor_id or getattr(obj, "created_by_id", None)
        )

        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)

        return obj
```

### 2.5 API Endpoint Examples

#### 2.5.1 Authentication Endpoints

```python
# File: src/communication_server/api/v1/auth.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from agent_comm_core.auth.service import AuthService
from communication_server.security.dependencies import get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    auth_service: AuthService = Depends()
):
    """
    Authenticate user and return JWT tokens.

    - **username**: User's username
    - **password**: User's password
    """
    user = await auth_service.authenticate_user(request.username, request.password)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is inactive")

    tokens = await auth_service.create_tokens(user)

    # Log to audit
    await auth_service.log_audit_event(
        action="login",
        entity_type="user",
        entity_id=user.id,
        actor_type="human",
        actor_id=user.id
    )

    return tokens

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str,
    auth_service: AuthService = Depends()
):
    """Refresh access token using refresh token."""
    tokens = await auth_service.refresh_tokens(refresh_token)
    return tokens

@router.post("/logout")
async def logout(
    refresh_token: str,
    user: User = Depends(get_current_user),
    auth_service: AuthService = Depends()
):
    """Invalidate refresh token."""
    await auth_service.revoke_refresh_token(refresh_token)

    # Log to audit
    await auth_service.log_audit_event(
        action="logout",
        entity_type="user",
        entity_id=user.id,
        actor_type="human",
        actor_id=user.id
    )

    return {"message": "Logged out successfully"}
```

#### 2.5.2 Project Management Endpoints

```python
# File: src/communication_server/api/v1/projects.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from agent_comm_core.auth.service import AuthService
from agent_comm_core.db.repository import ProjectRepository
from agent_comm_core.db.models.project import ProjectDB
from communication_server.security.dependencies import get_current_user

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

class ProjectCreate(BaseModel):
    project_id: str  # Human-readable slug
    name: str
    description: Optional[str] = None
    max_agents: int = 100
    allow_cross_project: bool = False

class ProjectResponse(BaseModel):
    id: UUID
    project_id: str
    name: str
    description: Optional[str]
    owner_id: UUID
    status: str
    created_at: datetime

@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    user: User = Depends(get_current_user),
    project_repo: ProjectRepository = Depends()
):
    """List all projects owned by current user."""
    projects = await project_repo.list_by_owner(user.id)
    return projects

@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    data: ProjectCreate,
    user: User = Depends(get_current_user),
    project_repo: ProjectRepository = Depends()
):
    """Create a new project owned by current user."""
    # Check if project_id already exists
    existing = await project_repo.get_by_project_id(data.project_id)
    if existing:
        raise HTTPException(status_code=409, detail="Project ID already exists")

    project = ProjectDB(
        project_id=data.project_id,
        name=data.name,
        description=data.description,
        owner_id=user.id,
        max_agents=data.max_agents,
        allow_cross_project=data.allow_cross_project
    )

    created = await project_repo.create(
        project,
        project_id=project.id,
        actor_type="human",
        actor_id=user.id
    )

    # Log to audit
    await project_repo.log_audit_event(
        action="project_create",
        entity_type="project",
        entity_id=created.id,
        project_id=created.id,
        actor_type="human",
        actor_id=user.id
    )

    return created
```

---

## 3. Risk Assessment

### 3.1 Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| RLS policy bypass causes data leak | Critical | Low | Comprehensive RLS testing, code review |
| Migration fails in production | High | Medium | Test migration in staging, have rollback plan |
| JWT secret compromise | Critical | Low | Use environment variables, rotate keys |
| Audit log performance degradation | Medium | Medium | Implement partitioning, indexing |
| Cross-project permission confusion | Medium | High | Clear documentation, explicit opt-in |

### 3.2 Operational Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Existing agents broken after migration | High | Medium | Backward compatibility mode |
| Users locked out after auth changes | High | Low | Superuser bypass, emergency access |
| Performance regression with RLS | Medium | Low | Performance testing, optimization |

---

## 4. Testing Strategy

### 4.1 Unit Tests

**Coverage Target:** 85%+

**Key Areas:**
- JWT token generation and validation
- API key generation and validation
- Repository methods with project context
- RLS policy enforcement (mock database)
- Audit logging functions

### 4.2 Integration Tests

**Scenarios:**
1. Complete OAuth flow (login, refresh, logout)
2. Agent authentication with API key
3. Project CRUD operations
4. Cross-project access blocking
5. Audit log creation and querying
6. Rate limiting enforcement

### 4.3 Security Tests

**OWASP Top 10 Coverage:**
- SQL injection (prevented by ORM + RLS)
- Broken authentication (JWT + API key validation)
- Sensitive data exposure (audit log redaction)
- Broken access control (RLS + permission checks)
- Security misconfiguration (CORS, headers)

---

## 5. Deployment Plan

### 5.1 Pre-Deployment Checklist

- [ ] All migrations tested in development
- [ ] RLS policies verified
- [ ] Audit logging functional
- [ ] Unit tests passing (85%+)
- [ ] Integration tests passing
- [ ] Security review completed
- [ ] Performance benchmarks met
- [ ] Rollback procedure tested

### 5.2 Deployment Steps

1. **Database Backup**
   ```bash
   pg_dump -U user -h host database_name > backup_$(date +%Y%m%d).sql
   ```

2. **Run Migrations**
   ```bash
   alembic upgrade head
   ```

3. **Verify Schema**
   ```bash
   psql -c "\d users"
   psql -c "\d projects"
   psql -c "\d agent_api_keys"
   psql -c "\d audit_logs"
   ```

4. **Test RLS Policies**
   ```sql
   SET app.current_project_id = 'test-project-id';
   SELECT * FROM communications;  -- Should only return project data
   ```

5. **Deploy Application**
   ```bash
   # Update code
   git pull origin main

   # Install dependencies
   pip install -r requirements.txt

   # Restart services
   systemctl restart communication-server
   ```

6. **Smoke Tests**
   ```bash
   curl -X POST https://api.example.com/api/v1/auth/login
   curl https://api.example.com/health
   ```

### 5.3 Rollback Plan

If deployment fails:

1. **Application Rollback**
   ```bash
   git checkout previous_stable_tag
   systemctl restart communication-server
   ```

2. **Database Rollback**
   ```bash
   alembic downgrade -1  # Rollback last migration
   ```

3. **Verify**
   ```bash
   curl https://api.example.com/health
   ```

---

## 6. Post-Implementation Tasks

### 6.1 Monitoring

- Set up alerts for failed authentication attempts
- Monitor audit log volume
- Track RLS policy violations
- Monitor rate limiting triggers

### 6.2 Documentation

- Update API documentation
- Create security guide for users
- Document audit log queries
- Create troubleshooting guide

### 6.3 Training

- Train support team on new authentication
- Document common issues and resolutions
- Create runbooks for emergency scenarios

---

**Document Owner:** Implementation Team
**Last Updated:** 2026-02-02
**Next Review:** After Milestone 3 completion

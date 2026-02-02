# Standalone Mode Configuration Guide

## Introduction

The Communication Server can run in **standalone mode** without external dependencies like PostgreSQL or Redis. This mode is ideal for:

- Local development and testing
- Single-machine deployments
- Quick prototyping and proof-of-concept projects
- Resource-constrained environments

**Note:** Standalone mode uses SQLite for data storage and in-memory session management. For production deployments with high availability requirements, consider using PostgreSQL and Redis instead.

---

## Table of Contents

1. [Dependencies](#dependencies)
2. [Configuration](#configuration)
3. [Environment Variables](#environment-variables)
4. [Startup Instructions](#startup-instructions)
5. [Verification Steps](#verification-steps)
6. [Limitations](#limitations)
7. [Migration to Production](#migration-to-production)

---

## Dependencies

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Python | 3.11+ | 3.13+ |
| RAM | 512MB | 1GB+ |
| Disk | 50MB | 100MB+ |

### Python Packages

Standalone mode requires only core dependencies. Install with:

```bash
# Clone repository
git clone https://github.com/yarang/agent_com.git
cd agent_com

# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies (without extras)
uv venv
source .venv/bin/activate
uv pip install -e .
```

**No external database or cache services required!**

---

## Configuration

### Quick Setup

1. **Copy the standalone configuration:**

```bash
cp config.standalone.example.json config.json
```

2. **Or specify config path via environment variable:**

```bash
export CONFIG_PATH=/path/to/config.standalone.example.json
```

### Configuration File Structure

The standalone configuration file (`config.standalone.example.json`) contains:

```json
{
  "version": "1.0.0",
  "server": {
    "host": "0.0.0.0",
    "port": 8001,
    "ssl": {
      "enabled": false,
      "cert_path": "./certificates/cert.pem",
      "key_path": "./certificates/key.pem"
    },
    "cors": {
      "origins": ["*"],
      "allow_credentials": true
    }
  },
  "database": {
    "url": "sqlite+aiosqlite:///./agent_comm.db",
    "pool_size": 5,
    "max_overflow": 10
  },
  "authentication": {
    "jwt": {
      "secret_key": "dev-secret-key-32-chars-long-min",
      "algorithm": "HS256",
      "access_token_expire_minutes": 15,
      "refresh_token_expire_days": 7
    },
    "api_token": {
      "prefix": "agent_",
      "secret": "dev-api-token-secret-32-chars-min"
    }
  },
  "security": {
    "rate_limiting": {
      "enabled": true,
      "requests_per_minute": 60
    },
    "headers": {
      "enabled": true
    }
  },
  "logging": {
    "level": "INFO",
    "format": "json"
  },
  "agent": {
    "nickname": "StandaloneAgent",
    "project_id": "standalone",
    "capabilities": []
  },
  "communication_server": {
    "url": "http://localhost:8001",
    "timeout": 30
  }
}
```

### Key Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `database.url` | SQLite database path (file-based) | `./agent_comm.db` |
| `server.host` | Server bind address | `0.0.0.0` |
| `server.port` | Server port | `8001` |
| `authentication.jwt.secret_key` | JWT signing secret | Auto-generated |
| `security.rate_limiting.enabled` | Enable rate limiting | `true` |

---

## Environment Variables

### Optional Environment Variables

```bash
# Override config file location
export CONFIG_PATH=/path/to/custom/config.json

# Override server settings
export HOST=0.0.0.0
export PORT=8001

# Override database location
export DATABASE_URL=sqlite+aiosqlite:///./custom_agent_comm.db

# Override JWT secret (recommended for production)
export JWT_SECRET_KEY=your-secure-secret-key-min-32-chars

# Override API token secret
export API_TOKEN_SECRET=your-api-token-secret-min-32-chars

# CORS settings
export CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

# Logging
export LOG_LEVEL=INFO
export LOG_FORMAT=json
```

### Generating Secure Secrets

For standalone deployments requiring security:

```bash
# Generate JWT secret
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate API token secret
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Startup Instructions

### Method 1: Direct Python Execution

```bash
# Activate virtual environment
source .venv/bin/activate

# Start the server
python -m communication_server.main
```

### Method 2: Using Entry Point Script

```bash
# Activate virtual environment
source .venv/bin/activate

# Start using the agent-comm-server command
agent-comm-server
```

### Method 3: Uvicorn (Development with Hot Reload)

```bash
# Activate virtual environment
source .venv/bin/activate

# Start with uvicorn
uvicorn communication_server.main:app --reload --host 0.0.0.0 --port 8001
```

### Method 4: systemd Service (Linux)

Create `/etc/systemd/system/agent-comm-standalone.service`:

```ini
[Unit]
Description=Agent Communication Server (Standalone)
After=network.target

[Service]
Type=simple
User=agentcomm
Group=agentcomm
WorkingDirectory=/opt/agent-comm
Environment="PATH=/opt/agent-comm/.venv/bin"
Environment="CONFIG_PATH=/opt/agent-comm/config.json"
ExecStart=/opt/agent-comm/.venv/bin/python -m communication_server.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable agent-comm-standalone
sudo systemctl start agent-comm-standalone
sudo systemctl status agent-comm-standalone
```

### Expected Startup Output

```
============================================================
SSL/TLS is DISABLED
HTTP endpoint: http://0.0.0.0:8001
WebSocket: ws://0.0.0.0:8001/ws/status
============================================================
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8001
```

---

## Verification Steps

### 1. Health Check

```bash
curl http://localhost:8001/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "service": "communication-server",
  "version": "1.0.0",
  "ssl_enabled": false
}
```

### 2. API Root Endpoint

```bash
curl http://localhost:8001/
```

**Expected Response:**
```json
{
  "name": "Communication Server",
  "version": "1.0.0",
  "description": "REST API and WebSocket server for AI Agent Communication System",
  "ssl_enabled": false,
  "endpoints": {
    "api": "/api/v1",
    "health": "/health",
    "websocket": "/ws/meetings/{meeting_id}",
    "status_websocket": "/ws/status",
    "chat_websocket": "/ws/chat/{room_id}",
    "docs": "/docs",
    "dashboard": "/static/index.html"
  }
}
```

### 3. Database File Creation

Verify SQLite database was created:

```bash
ls -la agent_comm.db
```

### 4. WebSocket Connection Test

```bash
# Using websocat (install: go install github.com/gorilla/websocket@latest)
websocat ws://localhost:8001/ws/status
```

### 5. API Documentation Access

Open browser: http://localhost:8001/docs

---

## Limitations

### Standalone Mode Constraints

| Feature | Standalone | Production |
|---------|------------|------------|
| Database | SQLite (file-based) | PostgreSQL |
| Concurrency | Limited by SQLite locks | High concurrency |
| Scalability | Single instance | Multi-instance |
| Session Storage | In-memory | Redis |
| Persistence | Local file only | Distributed |
| Backup | File copy | Database dump |

### Known Limitations

1. **SQLite Concurrency**: SQLite handles concurrent writes, but may have performance limitations under heavy write loads.

2. **Single Instance**: Only one server instance can access the SQLite database file safely. Use PostgreSQL for multi-instance deployments.

3. **In-Memory Sessions**: Session data is lost on server restart. Use Redis for persistent session storage.

4. **No Horizontal Scaling**: Standalone mode does not support multiple server instances behind a load balancer.

5. **File-Based Backup**: Database backup requires file-level operations. Consider automated backup strategies.

### When to Use Standalone Mode

**Use standalone mode for:**
- Local development and testing
- Prototyping and proof-of-concepts
- Single-user applications
- Resource-constrained edge devices
- CI/CD testing environments

**Use production mode (PostgreSQL + Redis) for:**
- Multi-user production deployments
- High availability requirements
- Horizontal scaling needs
- Distributed deployments
- Production workloads

---

## Migration to Production

### From Standalone to PostgreSQL

1. **Export SQLite data:**

```bash
# Install sqlite3
sudo apt-get install sqlite3  # Linux
brew install sqlite3           # macOS

# Export data to SQL
sqlite3 agent_comm.db .dump > backup.sql
```

2. **Set up PostgreSQL:**

```bash
# Install PostgreSQL
sudo apt-get install postgresql postgresql-contrib  # Linux
brew install postgresql@16                          # macOS

# Create database
sudo -u postgres psql
CREATE DATABASE agent_comm;
CREATE USER agent WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE agent_comm TO agent;
\q
```

3. **Update configuration:**

```json
{
  "database": {
    "url": "postgresql+asyncpg://agent:secure_password@localhost/agent_comm",
    "pool_size": 10,
    "max_overflow": 20
  }
}
```

4. **Run migrations:**

```bash
alembic upgrade head
```

5. **Import data (if needed):**

This requires manual data migration or using a migration tool. Consider exporting API data and re-importing via API calls.

### Backup and Restore

**Standalone Mode Backup:**

```bash
# Simple file copy
cp agent_comm.db agent_comm.db.backup.$(date +%Y%m%d)

# Or automated backup script
#!/bin/bash
BACKUP_DIR="/backups/agent-comm"
mkdir -p "$BACKUP_DIR"
cp agent_comm.db "$BACKUP_DIR/agent_comm.db.$(date +%Y%m%d_%H%M%S)"
# Keep last 7 days
find "$BACKUP_DIR" -name "agent_comm.db.*" -mtime +7 -delete
```

**Standalone Mode Restore:**

```bash
# Stop server first
sudo systemctl stop agent-comm-standalone

# Restore from backup
cp agent_comm.db.backup.20260203 agent_comm.db

# Start server
sudo systemctl start agent-comm-standalone
```

---

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 8001
lsof -i :8001

# Kill the process
kill -9 <PID>

# Or use different port
PORT=8002 python -m communication_server.main
```

### Database Locked Error

```bash
# Check for other running instances
ps aux | grep communication_server

# Stop all instances before starting new one
```

### Permission Denied on Database File

```bash
# Check file permissions
ls -la agent_comm.db

# Fix permissions
chmod 644 agent_comm.db
chown $USER:$USER agent_comm.db
```

### Import Errors

```bash
# Reinstall dependencies
uv pip install --upgrade -e .

# Verify Python version
python --version  # Should be 3.11+
```

---

# 독립 실행형 모드 구성 가이드

## 소개

통신 서버는 PostgreSQL이나 Redis와 같은 외부 종속성 없이 **독립 실행형 모드(standalone mode)** 로 실행할 수 있습니다. 이 모드는 다음과 같은 경우에 적합합니다:

- 로컬 개발 및 테스트
- 단일 머신 배포
- 빠른 프로토타이핑 및 개념 증명 프로젝트
- 리소스가 제한된 환경

**참고:** 독립 실행형 모드는 데이터 저장을 위해 SQLite를 사용하고 세션 관리를 위해 메모리 내 저장을 사용합니다. 고가용성이 필요한 프로덕션 배포의 경우 PostgreSQL과 Redis를 사용하는 것이 좋습니다.

---

## 목차

1. [종속성](#종속성)
2. [구성](#구성-1)
3. [환경 변수](#환경-변수-1)
4. [시작 지침](#시작-지침)
5. [검증 단계](#검증-단계)
6. [제한 사항](#제한-사항)
7. [프로덕션으로 마이그레이션](#프로덕션으로-마이그레이션)

---

## 종속성

### 시스템 요구사항

| 구성요소 | 최소 사양 | 권장 사양 |
|----------|-----------|-----------|
| Python | 3.11+ | 3.13+ |
| RAM | 512MB | 1GB+ |
| 디스크 | 50MB | 100MB+ |

### Python 패키지

독립 실행형 모드는 핵심 종속성만 필요합니다. 다음과 같이 설치하세요:

```bash
# 저장소 복제
git clone https://github.com/yarang/agent_com.git
cd agent_com

# uv 패키지 관리자 설치
curl -LsSf https://astral.sh/uv/install.sh | sh

# 종속성 설치 (추가 기능 없이)
uv venv
source .venv/bin/activate
uv pip install -e .
```

**외부 데이터베이스나 캐시 서비스가 필요하지 않습니다!**

---

## 구성

### 빠른 설정

1. **독립 실행형 구성 복사:**

```bash
cp config.standalone.example.json config.json
```

2. **또는 환경 변수를 통해 구성 경로 지정:**

```bash
export CONFIG_PATH=/path/to/config.standalone.example.json
```

### 구성 파일 구조

독립 실행형 구성 파일(`config.standalone.example.json`)은 다음을 포함합니다:

```json
{
  "version": "1.0.0",
  "server": {
    "host": "0.0.0.0",
    "port": 8001,
    "ssl": {
      "enabled": false,
      "cert_path": "./certificates/cert.pem",
      "key_path": "./certificates/key.pem"
    },
    "cors": {
      "origins": ["*"],
      "allow_credentials": true
    }
  },
  "database": {
    "url": "sqlite+aiosqlite:///./agent_comm.db",
    "pool_size": 5,
    "max_overflow": 10
  },
  "authentication": {
    "jwt": {
      "secret_key": "dev-secret-key-32-chars-long-min",
      "algorithm": "HS256",
      "access_token_expire_minutes": 15,
      "refresh_token_expire_days": 7
    },
    "api_token": {
      "prefix": "agent_",
      "secret": "dev-api-token-secret-32-chars-min"
    }
  },
  "security": {
    "rate_limiting": {
      "enabled": true,
      "requests_per_minute": 60
    },
    "headers": {
      "enabled": true
    }
  },
  "logging": {
    "level": "INFO",
    "format": "json"
  },
  "agent": {
    "nickname": "StandaloneAgent",
    "project_id": "standalone",
    "capabilities": []
  },
  "communication_server": {
    "url": "http://localhost:8001",
    "timeout": 30
  }
}
```

### 주요 구성 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `database.url` | SQLite 데이터베이스 경로 (파일 기반) | `./agent_comm.db` |
| `server.host` | 서버 바인드 주소 | `0.0.0.0` |
| `server.port` | 서버 포트 | `8001` |
| `authentication.jwt.secret_key` | JWT 서명 시크릿 | 자동 생성 |
| `security.rate_limiting.enabled` | 속도 제한 활성화 | `true` |

---

## 환경 변수

### 선택적 환경 변수

```bash
# 구성 파일 위치 재정의
export CONFIG_PATH=/path/to/custom/config.json

# 서버 설정 재정의
export HOST=0.0.0.0
export PORT=8001

# 데이터베이스 위치 재정의
export DATABASE_URL=sqlite+aiosqlite:///./custom_agent_comm.db

# JWT 시크릿 재정의 (프로덕션 권장)
export JWT_SECRET_KEY=your-secure-secret-key-min-32-chars

# API 토큰 시크릿 재정의
export API_TOKEN_SECRET=your-api-token-secret-min-32-chars

# CORS 설정
export CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

# 로깅
export LOG_LEVEL=INFO
export LOG_FORMAT=json
```

### 보안 시크릿 생성

보안이 필요한 독립 실행형 배포의 경우:

```bash
# JWT 시크릿 생성
python -c "import secrets; print(secrets.token_urlsafe(32))"

# API 토큰 시크릿 생성
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 시작 지침

### 방법 1: 직접 Python 실행

```bash
# 가상 환경 활성화
source .venv/bin/activate

# 서버 시작
python -m communication_server.main
```

### 방법 2: 진입점 스크립트 사용

```bash
# 가상 환경 활성화
source .venv/bin/activate

# agent-comm-server 명령어로 시작
agent-comm-server
```

### 방법 3: Uvicorn (핫 리로드 개발)

```bash
# 가상 환경 활성화
source .venv/bin/activate

# uvicorn으로 시작
uvicorn communication_server.main:app --reload --host 0.0.0.0 --port 8001
```

### 방법 4: systemd 서비스 (Linux)

`/etc/systemd/system/agent-comm-standalone.service` 생성:

```ini
[Unit]
Description=Agent Communication Server (Standalone)
After=network.target

[Service]
Type=simple
User=agentcomm
Group=agentcomm
WorkingDirectory=/opt/agent-comm
Environment="PATH=/opt/agent-comm/.venv/bin"
Environment="CONFIG_PATH=/opt/agent-comm/config.json"
ExecStart=/opt/agent-comm/.venv/bin/python -m communication_server.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

활성화 및 시작:

```bash
sudo systemctl daemon-reload
sudo systemctl enable agent-comm-standalone
sudo systemctl start agent-comm-standalone
sudo systemctl status agent-comm-standalone
```

### 예상 시작 출력

```
============================================================
SSL/TLS is DISABLED
HTTP endpoint: http://0.0.0.0:8001
WebSocket: ws://0.0.0.0:8001/ws/status
============================================================
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8001
```

---

## 검증 단계

### 1. 헬스 체크

```bash
curl http://localhost:8001/health
```

**예상 응답:**
```json
{
  "status": "healthy",
  "service": "communication-server",
  "version": "1.0.0",
  "ssl_enabled": false
}
```

### 2. API 루트 엔드포인트

```bash
curl http://localhost:8001/
```

### 3. 데이터베이스 파일 생성 확인

```bash
ls -la agent_comm.db
```

### 4. WebSocket 연결 테스트

```bash
# websocat 사용 (설치: go install github.com/gorilla/websocket@latest)
websocat ws://localhost:8001/ws/status
```

### 5. API 문서 액세스

브라우저 열기: http://localhost:8001/docs

---

## 제한 사항

### 독립 실행형 모드 제약

| 기능 | 독립 실행형 | 프로덕션 |
|------|------------|----------|
| 데이터베이스 | SQLite (파일 기반) | PostgreSQL |
| 동시성 | SQLite 잠금으로 제한됨 | 높은 동시성 |
| 확장성 | 단일 인스턴스 | 멀티 인스턴스 |
| 세션 저장소 | 메모리 내 | Redis |
| 지속성 | 로컬 파일만 | 분산 |
| 백업 | 파일 복사 | 데이터베이스 덤프 |

### 알려진 제한 사항

1. **SQLite 동시성**: SQLite는 동시 쓰기를 처리하지만, 무거운 쓰기 부하 하에서는 성능 제한이 있을 수 있습니다.

2. **단일 인스턴스**: SQLite 데이터베이스 파일은 안전하게 단 하나의 서버 인스턴스에서만 액세스할 수 있습니다. 멀티 인스턴스 배포에는 PostgreSQL을 사용하세요.

3. **메모리 내 세션**: 세션 데이터는 서버 재시작 시 손실됩니다. 지속적인 세션 저장에는 Redis를 사용하세요.

4. **수평 확장 불가**: 독립 실행형 모드는 로드 밸런서 뒤에 여러 서버 인스턴스를 지원하지 않습니다.

5. **파일 기반 백업**: 데이터베이스 백업에는 파일 수준 작업이 필요합니다. 자동화된 백업 전략을 고려하세요.

### 독립 실행형 모드 사용 시기

**독립 실행형 모드 사용:**
- 로컬 개발 및 테스트
- 프로토타이핑 및 개념 증명
- 단일 사용자 애플리케이션
- 리소스가 제한된 엣지 디바이스
- CI/CD 테스트 환경

**프로덕션 모드 사용 (PostgreSQL + Redis):**
- 다중 사용자 프로덕션 배포
- 높은 가용성 요구사항
- 수평 확장 요구
- 분산 배포
- 프로덕션 워크로드

---

## 프로덕션으로 마이그레이션

### 독립 실행형에서 PostgreSQL로

1. **SQLite 데이터 내보내기:**

```bash
# sqlite3 설치
sudo apt-get install sqlite3  # Linux
brew install sqlite3           # macOS

# 데이터를 SQL로 내보내기
sqlite3 agent_comm.db .dump > backup.sql
```

2. **PostgreSQL 설정:**

```bash
# PostgreSQL 설치
sudo apt-get install postgresql postgresql-contrib  # Linux
brew install postgresql@16                          # macOS

# 데이터베이스 생성
sudo -u postgres psql
CREATE DATABASE agent_comm;
CREATE USER agent WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE agent_comm TO agent;
\q
```

3. **구성 업데이트:**

```json
{
  "database": {
    "url": "postgresql+asyncpg://agent:secure_password@localhost/agent_comm",
    "pool_size": 10,
    "max_overflow": 20
  }
}
```

4. **마이그레이션 실행:**

```bash
alembic upgrade head
```

---

## 문제 해결

### 포트 이미 사용 중

```bash
# 포트 8001을 사용하는 프로세스 찾기
lsof -i :8001

# 프로세스 종료
kill -9 <PID>

# 또는 다른 포트 사용
PORT=8002 python -m communication_server.main
```

### 데이터베이스 잠금 오류

```bash
# 실행 중인 다른 인스턴스 확인
ps aux | grep communication_server

# 새 인스턴스 시작 전 모든 인스턴스 중지
```

### 데이터베이스 파일 권한 거부

```bash
# 파일 권한 확인
ls -la agent_comm.db

# 권한 수정
chmod 644 agent_comm.db
chown $USER:$USER agent_comm.db
```

---

## 관련 문서

- [README.md](../README.md) - 프로젝트 개요
- [docs/deployment.md](deployment.md) - 배포 가이드
- [docs/INSTALLATION.md](INSTALLATION.md) - 설치 가이드
- [docs/SECURITY.md](SECURITY.md) - 보안 가이드

---

**버전:** 1.0.0
**최종 업데이트:** 2026-02-03
**문서 관리자:** MCP Broker Server 팀

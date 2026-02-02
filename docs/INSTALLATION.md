# 설치 가이드

**버전:** 1.0.0
**최종 업데이트:** 2026-02-02
**플랫폼:** MCP Broker Server

---

## 목차

1. [시스템 요구사항](#시스템-요구사항)
2. [개발 환경 설정](#개발-환경-설정)
3. [데이터베이스 설정](#데이터베이스-설정)
4. [서버 시작](#서버-시작)
5. [Docker 배포](#docker-배포)
6. [문제 해결](#문제-해결)

---

## 시스템 요구사항

### 필수 구성요소

| 구성요소 | 최소 사양 | 권장 사양 |
|----------|-----------|-----------|
| 운영체제 | Linux/macOS/Windows | Linux (Ubuntu 22.04+, Oracle Linux 8+) |
| Python | 3.11+ | 3.13+ |
| RAM | 2GB | 4GB+ |
| 디스크 | 10GB 여유 공간 | 20GB+ SSD |
| PostgreSQL | 16+ | 16+ |
| Redis | 6+ | 7+ |

### 선택적 구성요소

| 구성요소 | 용도 | 권장 버전 |
|----------|------|-------------|
| Docker | 컨테이너화 배포 | 24.0+ |
| Nginx | 리버스 프록시 | 1.24+ |

---

## 개발 환경 설정

### 1. Python 설치

#### Linux/macOS

```bash
# Python 3.13 설치 (Ubuntu/Debian)
sudo apt update
sudo apt install -y python3.13 python3.13-venv python3-pip

# Python 3.13 설치 (macOS - Homebrew)
brew install python@3.13

# 또는 pyenv 사용 (권장)
curl https://pyenv.run | bash
pyenv install 3.13.0
pyenv global 3.13.0
```

#### Windows

```powershell
# Python 3.13 다운로드 및 설치
# https://www.python.org/downloads/

# 또는 winget 사용
winget install Python.Python.3.13
```

### 2. 패키지 관리자 설정 (uv 사용 권장)

```bash
# uv 설치
curl -LsSf https://astral.sh/uv/install.sh | sh

# 또는
pip install uv

# 프로젝트 디렉토리 이동
cd /path/to/mcp-broker-server

# 가상환 환경 생성 및 의존성 설치
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e ".[dev,redis]"
```

### 3. 환경 변수 설정

`.env` 파일 생성:

```bash
cp .env.example .env
nano .env
```

**필수 환경 변수:**

```bash
# 서버 설정
MCP_BROKER_HOST=0.0.0.0
MCP_BROKER_PORT=8000
MCP_BROKER_LOG_LEVEL=INFO

# 스토리지 설정
MCP_BROKER_STORAGE=memory

# Redis 설정 (선택사항)
# MCP_BROKER_REDIS_URL=redis://localhost:6379/0

# 보안 설정
MCP_BROKER_ENABLE_AUTH=false
# MCP_BROKER_AUTH_SECRET=<generate-secure-secret>

# CORS 설정
MCP_BROKER_CORS_ORIGINS=*
```

---

## 데이터베이스 설정

### PostgreSQL 설치

#### Linux (Ubuntu/Debian)

```bash
# PostgreSQL 저장소 추가
sudo apt install -y postgresql postgresql-contrib

# PostgreSQL 시작
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 데이터베이스 사용자 및 데이터베이스 생성
sudo -u postgres psql
```

```sql
-- 데이터베이스 생성
CREATE DATABASE mcp_broker;

-- 사용자 생성
CREATE USER mcp_user WITH PASSWORD 'secure_password_here';

-- 권한 부여
GRANT ALL PRIVILEGES ON DATABASE mcp_broker TO mcp_user;

-- 종료
\q
```

#### macOS

```bash
# Homebrew로 설치
brew install postgresql@16
brew services start postgresql@16

# 데이터베이스 설정
createdb mcp_broker
psql -d mcp_broker
```

```sql
-- 사용자 생성
CREATE USER mcp_user WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE mcp_broker TO mcp_user;
```

#### Windows

```powershell
# PostgreSQL 설치 다운로드
# https://www.postgresql.org/download/windows/

# 설치过程中 설정:
# - 포트: 5432
# - 비밀번호: (기억하기 쉬움)
# - 서비스 시작: 자동

# 데이터베이스 생성
createdb mcproker
```

### Alembic 마이그레이션

```bash
# Alembic 초기화
cd /path/to/mcp-broker-server

# 마이그레이션 생성
alembic revision --autogenerate -m "Initial migration"

# 마이그레이션 실행
alembic upgrade head

# 롤백 (필요한 경우)
alembic downgrade -1
```

### 데이터베이스 연결 설정

`src/agent_comm_core/db/database.py`:

```python
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://mcp_user:password@localhost/mcp_broker"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

async_session_maker = sessionmaker(
    expire_on_commit=False,
    autocommit=False,
    bind=engine
)
```

### Row-Level Security (RLS) 활성화

```sql
-- RLS 활성화
ALTER TABLE communications ENABLE ROW LEVEL SECURITY;
ALTER TABLE meetings ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE decisions ENABLE ROW LEVEL SECURITY;

-- 프로젝트 격리 정책
CREATE POLICY communications_project_isolation
ON communications
FOR ALL
USING (project_id = current_setting('app.current_project_id')::uuid);

CREATE POLICY communications_select
ON communications
FOR SELECT
USING (project_id = current_setting('app.current_project_id')::uuid);

CREATE POLICY communications_insert
ON communications
FOR INSERT
WITH CHECK (project_id = current_setting('app.current_project_id')::uuid);
```

---

## 서버 시작

### 개발 모드

```bash
# 가상환 환경 활성화
source .venv/bin/activate

# 개발 서버 시작 (hot reload)
uvicorn communication_server.main:app --reload --host 0.0.0.0 --port 8001

# 또는 Python 직접 실행
python -m communication_server.main
```

### 프로덕션 모드

```bash
# gunicorn 사용 (권장)
pip install gunicorn[uvloop]

# 시작
gunicorn communication_server.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8001 \
  --access-logfile - \
  --error-logfile - \
  --log-level info
```

### systemd 서비스 설정 (Linux)

`/etc/systemd/system/mcp-broker.service`:

```ini
[Unit]
Description=MCP Broker Server
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=mcpbroker
Group=mcpbroker
WorkingDirectory=/opt/mcp-broker-server
Environment="PATH=/opt/mcp-broker-server/.venv/bin"
ExecStart=/opt/mcp-broker-server/.venv/bin/gunicorn communication_server.main:app
ExecReload=/bin/kill -HUP $MAINPID
KillMode=mixed
TimeoutSec=30
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# 서비스 등록 및 시작
sudo systemctl daemon-reload
sudo systemctl enable mcp-broker
sudo systemctl start mcp-broker
sudo systemctl status mcp-broker
```

---

## Docker 배포

### Dockerfile 작성

```dockerfile
FROM python:3.13-slim

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 파일 복사
COPY pyproject.toml README.md ./
COPY .claude/ .claude/
COPY src/ src/

# uv 설치 및 의존성 설치
RUN pip install uv
RUN uv venv
RUN uv pip install -e ".[dev]"

# 비-root 사용자 생성
RUN useradd -m -u 1000 mcpbroker && \
    chown -R mcpbroker:mcpbroker /app
USER mcpbroker

# 포트 노출
EXPOSE 8001

# 서버 시작
CMD ["python", "-m", "communication_server.main"]
```

### docker-compose.yml 작성

```yaml
version: '3.8'

services:
  broker:
    build: .
    ports:
      - "8001:8001"
    environment:
      - DATABASE_URL=postgresql://mcp_user:password@postgres:5432/mcp_broker
      - REDIS_URL=redis://redis:6379/0
      - JWT_SECRET_KEY=your-super-secret-key-min-32-chars
      - API_TOKEN_SECRET=your-api-token-secret
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    restart: unless-stopped
    volumes:
      - ./src:/app/src
      - ./logs:/app/logs

  postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=mcp_broker
      - POSTGRES_USER=mcp_user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: always
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mcp_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: always
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
           "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - broker
    restart: always

volumes:
  postgres_data:
  redis_data:
```

### Docker 실행

```bash
# 빌드 및 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f broker

# 서비스 중지
docker-compose down

# 전체 재시작
docker-compose restart
```

---

## 문제 해결

### 서버가 시작하지 않음

```bash
# 포트 사용 중인지 확인
lsof -i :8001

# 다른 포트 사용
MCP_BROKER_PORT=8002 python -m communication_server.main

# 로그 확인
tail -f logs/mcp-broker.log
```

### 데이터베이스 연결 실패

```bash
# PostgreSQL 상태 확인
sudo systemctl status postgresql

# 연결 테스트
psql -U mcp_user -d mcp_broker -h localhost

# 환경 변수 확인
echo $DATABASE_URL
```

### Redis 연결 실패

```bash
# Redis 상태 확인
redis-cli ping

# 연결 테스트
redis-cli -h localhost -p 6379 INFO server
```

### 인증 실패

```bash
# 보안 상태 확인
curl http://localhost:8001/api/v1/security/status

# 시크릿 확인
echo $JWT_SECRET_KEY
echo $API_TOKEN_SECRET
```

### 마이그레이션 오류

```bash
# 마이그레이션 상태 확인
alembic current

# 최신 마이그레이션으로 리셋트
alembic upgrade head

# 롤백 후 재시작
alembic downgrade base
alembic upgrade head
```

---

## 검증

### 서버 상태 확인

```bash
# 헬스 체크
curl http://localhost:8001/health

# API 루트 확인
curl http://localhost:8001/

# WebSocket 연결 확인
wscat -c ws://localhost:8001/api/v1/ws/dashboard
```

### 데이터베이스 연결 확인

```sql
-- PostgreSQL 연결 테스트
\c mcp_broker
SELECT COUNT(*) FROM agents;
SELECT COUNT(*) FROM communications;
SELECT COUNT(*) FROM meetings;
```

---

## 업그레이드

### 의존성 업그레이드

```bash
# 최신 버전으로 업데이트
git pull origin main

# 새로운 의존성 설치
uv pip install --upgrade -e ".[dev,redis]"

# 마이그레이션 실행
alembic upgrade head
```

---

## 롤백

### 변경 사항 되돌리기

```bash
# git reset
git reset --hard HEAD

# 데이터베이스 스키마 롤백
alembic downgrade base

# 미사용 데이터 삭제
sudo rm -rf logs/*
```

---

## 관련 문서

- [README.md](README.md) - 프로젝트 개요
- [ARCHITECTURE.md](ARCHITECTURE.md) - 시스템 아키텍처
- [API.md](API.md) - API 레퍼런스
- [SECURITY.md](SECURITY.md) - 보안 가이드

---

**문서 관리자:** MCP Broker Server 팀
**마지막 검토:** 2026-02-02
**다음 검토:** 2026-05-02

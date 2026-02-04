# Chat Service - Multi-Agent Orchestration Platform

## 프로젝트 개요

**목적**: AI Agent 간 협업을 조율하는 프로젝트 기반 실시간 채팅 시스템  
**상태**: 신규 프로젝트 - 구현 시작 전  
**우선순위**: Phase별 점진적 구현 (Phase 0 → Phase 7)

## 핵심 목표

1. ✅ **프로젝트 기반 컨텍스트 관리**: 모든 Chat Room은 Project에 속하며 공유 컨텍스트 유지
2. ✅ **Orchestrator 중재 시스템**: Agent 간 메시지 라우팅, 작업 할당, 충돌 해결
3. ✅ **실시간 WebSocket 통신**: 양방향 실시간 메시징
4. ✅ **지능형 Task 관리**: 자동 작업 분배 및 의존성 관리

## 기술 스택

### Backend
- **언어**: Python 3.11+
- **프레임워크**: FastAPI 0.104+
- **ORM**: SQLAlchemy 2.0+ (Async)
- **데이터베이스**: PostgreSQL 15+
- **캐싱**: Redis 6+
- **실시간**: WebSocket (FastAPI built-in)

### 인증 & 보안
- **JWT**: python-jose
- **비밀번호**: passlib[bcrypt]

### 개발 도구
- **마이그레이션**: Alembic
- **테스트**: pytest, pytest-asyncio
- **코드 품질**: black, flake8, mypy

## 프로젝트 구조

```
chat-service/
├── app/
│   ├── main.py                 # FastAPI 앱 진입점
│   ├── config.py               # 환경 설정
│   ├── database.py             # DB 연결 설정
│   │
│   ├── models/                 # SQLAlchemy 모델
│   │   ├── project.py          # Project, ProjectContext
│   │   ├── member.py           # ProjectMember
│   │   ├── room.py             # ChatRoom
│   │   ├── message.py          # ChatMessage
│   │   └── task.py             # Task
│   │
│   ├── schemas/                # Pydantic 스키마
│   │   ├── project.py
│   │   ├── room.py
│   │   ├── message.py
│   │   └── task.py
│   │
│   ├── api/                    # API 엔드포인트
│   │   ├── projects.py         # Project CRUD
│   │   ├── rooms.py            # Room 관리
│   │   ├── messages.py         # Message 처리
│   │   ├── tasks.py            # Task 관리
│   │   └── websocket.py        # WebSocket 엔드포인트
│   │
│   ├── services/               # 비즈니스 로직
│   │   ├── project_service.py
│   │   ├── room_service.py
│   │   ├── message_service.py
│   │   ├── task_service.py
│   │   └── orchestrator_service.py
│   │
│   ├── orchestrator/           # Orchestrator 시스템
│   │   ├── base.py             # OrchestratorAgent 클래스
│   │   ├── intent_analyzer.py  # 메시지 의도 분석
│   │   ├── scorer.py           # Agent 평가 엔진
│   │   └── router.py           # 메시지 라우팅
│   │
│   ├── websocket/              # WebSocket 관리
│   │   ├── manager.py          # ConnectionManager
│   │   └── handlers.py         # 이벤트 핸들러
│   │
│   └── utils/                  # 유틸리티
│       ├── auth.py             # JWT 인증
│       └── helpers.py
│
├── alembic/                    # DB 마이그레이션
├── tests/                      # 테스트
│   ├── unit/
│   └── integration/
│
├── .env.example
├── requirements.txt
├── CLAUDE.md                   # 이 파일
├── TASKS.md                    # 상세 작업 지침
└── README.md
```

## 아키텍처 계층

```
┌──────────────────────────────────────────┐
│         Project Context Layer            │  ← 공유 컨텍스트, 파일, 목표
├──────────────────────────────────────────┤
│      Orchestrator (Moderator) Layer      │  ← 메시지 라우팅, Task 할당
├──────────────────────────────────────────┤
│           Chat Room Layer                │  ← 실시간 메시징, WebSocket
├──────────────────────────────────────────┤
│         Service Layer                    │  ← 비즈니스 로직
├──────────────────────────────────────────┤
│         Data Layer (SQLAlchemy)          │  ← 데이터 영속화
└──────────────────────────────────────────┘
```

## 개발 규칙

### 코딩 스타일
- **PEP 8 준수**: Black 자동 포맷팅 사용
- **타입 힌트 필수**: 모든 함수에 타입 힌트 추가
- **Docstrings**: Google 스타일 docstring
- **네이밍**:
  - 함수/변수: `snake_case`
  - 클래스: `PascalCase`
  - 상수: `UPPER_SNAKE_CASE`
  - Private: `_leading_underscore`

### 비동기 처리
- **SQLAlchemy**: 모든 DB 작업은 async/await
- **Service 메서드**: `async def` 필수
- **API 핸들러**: `async def` 필수
- **WebSocket**: async 처리

### 에러 처리
- **HTTPException**: FastAPI 표준 예외 사용
- **명확한 상태 코드**: 400, 401, 403, 404, 409, 500
- **에러 메시지**: 사용자 친화적이고 구체적으로
- **로깅**: 모든 에러는 로그 기록

### 데이터베이스
- **마이그레이션**: 모든 스키마 변경은 Alembic 사용
- **관계**: ForeignKey, relationship 명확히 정의
- **인덱스**: 자주 쿼리되는 필드에 인덱스 추가
- **UUID**: 모든 Primary Key는 UUID 사용

### 테스트
- **커버리지 목표**: 80% 이상
- **단위 테스트**: 모든 service 메서드
- **통합 테스트**: API 엔드포인트, WebSocket
- **Fixtures**: pytest fixture 적극 활용

## 현재 상태

### ✅ 완료
- 프로젝트 구조 설계 완료
- 아키텍처 정의 완료
- 작업 지침 문서화 완료

### 🚧 진행 중
- Phase 0: 환경 설정 (다음 단계)

### 📋 예정
- Phase 1-7: 순차적 구현

## 다음 단계

**현재 Phase**: Phase 0 - 환경 설정

### Phase 0 작업 순서
1. **Task 0.1**: requirements.txt 생성
2. **Task 0.2**: .env.example 및 .env 생성
3. **Task 0.3**: app/main.py 생성 (FastAPI 앱)
4. **Task 0.4**: app/database.py 생성 (DB 설정)
5. **Task 0.5**: Alembic 초기화

각 Task의 상세 지침은 `TASKS.md` 참조

## 중요 참고사항

### Orchestrator 동작 방식
1. **메시지 수신** → IntentAnalyzer가 의도 파악
2. **라우팅 결정**:
   - Question → 전문성 있는 Agent에게
   - Task Request → Task 생성 후 최적 Agent 할당
   - Agent Mention → 언급된 Agent에게 직접 전달
   - General → 전체 브로드캐스트

### WebSocket 프로토콜
- **Client → Server**: `{"type": "message", "content": "..."}`
- **Server → Client**: `{"type": "message", "message": {...}}`
- **Heartbeat**: 30초마다 ping/pong

### Task 생애주기
```
pending → in_progress → review → completed
         ↓
      blocked (의존성 미완료)
         ↓
      cancelled (취소)
```

## 환경 변수

필수 환경 변수 (`.env` 파일):
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/chatdb
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
CORS_ORIGINS=http://localhost:3000
```

## 빠른 시작

```bash
# 1. 가상환경 생성
python -m venv venv
source venv/bin/activate

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 환경 설정
cp .env.example .env
# .env 파일 수정

# 4. 데이터베이스 설정
createdb chatdb
alembic upgrade head

# 5. 서버 실행
python app/main.py
```

## API 엔드포인트 (예정)

- `POST /api/v1/projects` - 프로젝트 생성
- `GET /api/v1/projects/{id}` - 프로젝트 조회
- `POST /api/v1/rooms` - 채팅방 생성
- `WS /api/v1/rooms/{id}/ws` - WebSocket 연결
- `POST /api/v1/tasks` - Task 생성
- `PATCH /api/v1/tasks/{id}/assign` - Task 할당

전체 API 문서는 실행 후 `/docs` 참조

## 문제 해결

**일반적인 문제:**
1. **DB 연결 실패** → DATABASE_URL 확인
2. **마이그레이션 오류** → `alembic downgrade -1` 후 재시도
3. **WebSocket 끊김** → Heartbeat 구현 확인 (Task 5.3)
4. **Redis 연결 실패** → `redis-cli ping` 확인

## 추가 문서

- `TASKS.md` - 상세 작업 지침 (Phase별 Task)
- `ARCHITECTURE.md` - 아키텍처 상세 설계
- `README.md` - 프로젝트 소개 및 사용법

## 연락처

프로젝트 관련 질문이나 이슈는 GitHub Issues 활용
# Communication Server 배포 보고서

## 배포 개요

Communication Server를 OCI 인스턴스 `oci-ajou-ec2.fcoinfup.com:8000`에 배포하는 설정이 완료되었습니다.

### 배포 대상

- **서버**: oci-ajou-ec2.fcoinfup.com
- **포트**: 8000
- **서비스**: Communication Server (FastAPI)
- **시작 모드**: systemd 서비스 (부팅 시 자동 시작)
- **재시작 정책**: 실패 시 자동 재시작

---

## 생성된 파일

### 1. 프로덕션 설정 파일

**파일**: `/Users/yarang/works/agent_dev/agent_com/config.production.json`

- 포트: 8000
- CORS origins: `oci-ajou-ec2.fcoinfup.com`, `localhost:3000`
- 데이터베이스: PostgreSQL 로컬 연결
- 로깅: JSON 형식, INFO 레벨

### 2. systemd 서비스 파일

**파일**: `/Users/yarang/works/agent_dev/agent_com/scripts/agent-comm-port8000.service`

- 사용자: ubuntu
- 작업 디렉토리: `/home/ubuntu/agent_com`
- 설정 파일: `config.production.json`
- 로그 위치: `/var/log/agent-comm/`

### 3. 배포 스크립트

**서버 배포 스크립트**: `/Users/yarang/works/agent_dev/agent_com/scripts/deploy-production.sh`
- 로그 디렉토리 생성
- 비밀 키 생성
- systemd 서비스 설치
- 방화벽 설정
- 서비스 시작 및 검증

**원격 배포 스크립트**: `/Users/yarang/works/agent_dev/agent_com/scripts/deploy-remote.sh`
- 로컬 머신에서 실행하여 원격 서버에 배포
- SSH 연결 확인
- 원격 서버 검증

**검증 스크립트**: `/Users/yarang/works/agent_dev/agent_com/scripts/verify-deployment.sh`
- 서비스 상태 확인
- 네트워크 구성 확인
- 헬스 엔드포인트 테스트
- 로그 디렉토리 확인

### 4. 환경 변수 템플릿

**파일**: `/Users/yarang/works/agent_dev/agent_com/.env.production`

프로덕션 환경 변수 템플릿입니다. 실제 배포 전에 비밀 키 값을 변경해야 합니다.

---

## 배포 단계

### 방법 1: 서버에서 직접 배포

```bash
# 1. SSH로 서버 접속
ssh ubuntu@oci-ajou-ec2.fcoinfup.com

# 2. 애플리케이션 디렉토리로 이동
cd /home/ubuntu/agent_com

# 3. 배포 스크립트 실행
sudo ./scripts/deploy-production.sh
```

### 방법 2: 로컬에서 원격 배포

```bash
# 로컬 머신에서 실행
./scripts/deploy-remote.sh deploy
```

---

## 배포 후 검증

### 1. 서비스 상태 확인

```bash
# 서비스 상태
sudo systemctl status agent-comm

# 활성 상태 확인
sudo systemctl is-active agent-comm

# 자동 시작 활성화 확인
sudo systemctl is-enabled agent-comm
```

### 2. 헬스 엔드포인트 테스트

```bash
# 로컬에서 테스트
curl http://localhost:8000/health

# 외부에서 테스트
curl http://oci-ajou-ec2.fcoinfup.com:8000/health
```

### 3. 검증 스크립트 실행

```bash
sudo ./scripts/verify-deployment.sh
```

---

## 서비스 관리

### 시작/중지/재시작

```bash
# 시작
sudo systemctl start agent-comm

# 중지
sudo systemctl stop agent-comm

# 재시작
sudo systemctl restart agent-comm

# Graceful 재시작
sudo systemctl reload agent-comm
```

### 로그 확인

```bash
# 서비스 로그 (systemd 저널)
sudo journalctl -u agent-comm -f

# 애플리케이션 출력 로그
tail -f /var/log/agent-comm/output.log

# 애플리케이션 에러 로그
tail -f /var/log/agent-comm/error.log

# 최근 로그
sudo journalctl -u agent-comm -n 100
```

---

## 방화벽 설정

### Ubuntu (ufw)

```bash
sudo ufw allow 8000/tcp
sudo ufw status
```

### Oracle Linux (firewalld)

```bash
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
sudo firewall-cmd --list-ports
```

### OCI Security List

OCI 콘솔에서 다음 인그레스 규칙을 추가해야 합니다:

- 프로토콜: TCP
- 소스: 0.0.0.0/0
- 대상 포트: 8000

---

## 엔드포인트

| 엔드포인트 | URL |
|----------|-----|
| 헬스 체크 | http://oci-ajou-ec2.fcoinfup.com:8000/health |
| API 루트 | http://oci-ajou-ec2.fcoinfup.com:8000/api/v1 |
| API 문서 | http://oci-ajou-ec2.fcoinfup.com:8000/docs |
| 루트 | http://oci-ajou-ec2.fcoinfup.com:8000/ |

---

## 문제 해결

### 서비스가 시작되지 않음

```bash
# 상세 상태 확인
sudo systemctl status agent-comm

# 최근 로그 확인
sudo journalctl -u agent-comm -n 50 --no-pager

# 애플리케이션 로그 확인
tail -n 50 /var/log/agent-comm/error.log
```

### 데이터베이스 연결 문제

```bash
# PostgreSQL 상태 확인
sudo systemctl status postgresql

# 데이터베이스 연결 테스트
psql -U agent -h localhost -d agent_comm -c "SELECT 1;"
```

### 포트 이미 사용 중

```bash
# 포트 8000 사용 중인 프로세스 확인
sudo lsof -i :8000
sudo netstat -tulpn | grep 8000
```

### 방화벽 차단

```bash
# 로컬에서 테스트
curl http://localhost:8000/health

# 외부에서 테스트
curl http://oci-ajou-ec2.fcoinfup.com:8000/health
```

---

## systemd 서비스 구성

서비스는 다음과 같이 구성되어 있습니다:

```ini
[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/agent_com
Restart=always          # 항상 재시작
RestartSec=10          # 10초 후 재시작
MemoryMax=2G           # 메모리 제한 2GB
```

### 자동 재시작 정책

- **재시art 모드**: always (항상 재시작)
- **재시art 지연**: 10초
- **최대 재시art**: 무제한
- **시작 제한**: 500초 내 5회

---

## 보안 고려사항

### 프로덕션 배포 전 필수 변경사항

1. **비밀 키 변경**: `config.production.json`의 `jwt.secret_key`와 `api_token.secret`을 안전한 값으로 변경

2. **데이터베이스 비밀번호**: 강력한 비밀번호 사용

3. **SSL/TLS**: Nginx 리버스 프록시와 함께 SSL 종단 사용 고려

4. **방화벽**: SSH 포트(22)를 신뢰할 수 있는 IP로 제한

5. **OCI Security List**: 불필요한 포트 닫기

---

## 업데이트 절차

```bash
# 1. 애플리케이션 디렉토리로 이동
cd /home/ubuntu/agent_com

# 2. 최신 변경사항 가져오기
git pull

# 3. 서비스 재시art (변경사항 적용)
sudo systemctl restart agent-comm

# 4. 배포 검증
curl http://localhost:8000/health
```

---

## 모니터링

### 건강 상태 모니터링

```bash
# 실시간 로그 모니터링
sudo journalctl -u agent-comm -f
```

### 크론작업을 이용한 주기적 헬스 체크

```bash
# 크론탭 편집
crontab -e

# 5분마다 헬스 체크 추가
*/5 * * * * curl -f http://localhost:8000/health || echo "Health check failed"
```

---

## 추가 리소스

- 전체 OCI 배포 가이드: [OCI_DEPLOYMENT.md](OCI_DEPLOYMENT.md)
- 개발 설정: [README.md](../README.md)
- API 문서: `http://oci-ajou-ec2.fcoinfup.com:8000/docs`

---

**배포 보고서 버전**: 1.0.0
**생성일**: 2026-02-01
**대상 서버**: oci-ajou-ec2.fcoinfup.com:8000

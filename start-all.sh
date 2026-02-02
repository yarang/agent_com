#!/bin/bash
# 두 서버를 동시에 시작하는 스크립트

# 스크립트 위치 기준으로 프로젝트 디렉토리 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
cd "$PROJECT_DIR"

# 패키지 설치 확인
echo "패키지 의존성 확인 중..."
if ! uv run python -c "import agent_comm_core" 2>/dev/null; then
    echo "패키지가 설치되지 않았습니다. uv sync 실행 중..."
    uv sync
    echo "패키지 설치 완료"
fi
echo ""

# 서버 IP 주소 감지
echo "서버 네트워크 정보 확인 중..."
# 로컬이 아닌 외부 연결 가능한 IP 주소 찾기
SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
if [ -z "$SERVER_IP" ] || [ "$SERVER_IP" = "127.0.0.1" ]; then
    # Linux에서 외부 IP 찾기
    SERVER_IP=$(ip route get 1 2>/dev/null | awk '{print $7}' | head -1)
fi
if [ -z "$SERVER_IP" ] || [ "$SERVER_IP" = "127.0.0.1" ]; then
    # macOS에서 외부 IP 찾기
    SERVER_IP=$(ifconfig 2>/dev/null | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -1)
fi
# 기본값 설정
if [ -z "$SERVER_IP" ]; then
    SERVER_IP="0.0.0.0"
fi
echo "   감지된 IP: $SERVER_IP"
echo ""

# 기존 프로세스 정리
echo "기존 프로세스 확인 중..."
pkill -f "communication_server.main" 2>/dev/null && echo "  기존 Communication Server 중지됨" || true
pkill -f "mcp_broker.main" 2>/dev/null && echo "  기존 MCP Broker Server 중지됨" || true
sleep 2

echo ""
echo "=========================================="
echo "AI Agent Communication System 시작"
echo "=========================================="
echo ""

# 1. Communication Server (포트 8000)
echo "1️⃣ Communication Server 시작 (포트 8000)..."
export CONFIG_PATH="$PROJECT_DIR/config.comm.json"
uv run -m communication_server.main > /tmp/comm_server.log 2>&1 &
COMM_PID=$!
echo "   PID: $COMM_PID"
sleep 3

# 2. MCP Broker Server (포트 8001)
echo ""
echo "2️⃣ MCP Broker Server 시작 (포트 8001)..."
uv run -m mcp_broker.main > /tmp/mcp_broker.log 2>&1 &
BROKER_PID=$!
echo "   PID: $BROKER_PID"

echo ""
echo "=========================================="
echo "✅ 모든 서버가 시작되었습니다"
echo "=========================================="
echo ""
echo "Communication Server:"
echo "  - Local: http://localhost:8000"
echo "  - External: http://$SERVER_IP:8000"
echo "  - Dashboard: http://$SERVER_IP:8000/"
echo "  - API Docs: http://$SERVER_IP:8000/docs"
echo "  - WebSocket: ws://$SERVER_IP:8000/ws"
echo ""
echo "MCP Broker Server:"
echo "  - Local: http://localhost:8001"
echo "  - External: http://$SERVER_IP:8001"
echo "  - Health: http://$SERVER_IP:8001/health"
echo "  - API Docs: http://$SERVER_IP:8001/docs"
echo ""
echo "로그 파일:"
echo "  - Communication Server: /tmp/comm_server.log"
echo "  - MCP Broker: /tmp/mcp_broker.log"
echo ""
echo "서버를 중지하려면: Ctrl+C 또는 ./stop-all.sh"
echo ""

# PID 파일 저장
echo $COMM_PID > /tmp/comm_server.pid
echo $BROKER_PID > /tmp/mcp_broker.pid

# 신호 핸들러 - SIGINT/SIGTERM을 받으면 모든 프로세스 종료
cleanup() {
    echo ""
    echo "서버 중지 중..."
    kill $COMM_PID 2>/dev/null || true
    kill $BROKER_PID 2>/dev/null || true
    rm -f /tmp/comm_server.pid /tmp/mcp_broker.pid
    echo "모든 서버가 중지되었습니다."
    exit 0
}

trap cleanup SIGINT SIGTERM

# 모든 백그라운드 프로세스가 종료될 때까지 대기
wait

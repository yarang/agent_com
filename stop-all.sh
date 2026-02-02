#!/bin/bash
# 두 서버를 중지하는 스크립트

echo "=========================================="
echo "AI Agent Communication System 중지"
echo "=========================================="
echo ""

# PID 파일에서 PID 읽기
if [ -f /tmp/comm_server.pid ]; then
    COMM_PID=$(cat /tmp/comm_server.pid)
    echo "Communication Server (PID: $COMM_PID) 중지 중..."
    kill $COMM_PID 2>/dev/null && echo "  ✅ 중지됨" || echo "  ⚠️  이미 종료됨"
    rm -f /tmp/comm_server.pid
else
    echo "Communication Server: PID 파일 없음, 프로세스 검색 중..."
    pkill -f "communication_server.main" && echo "  ✅ 프로세스 중지됨" || echo "  ⚠️  실행 중인 프로세스 없음"
fi

echo ""

if [ -f /tmp/mcp_broker.pid ]; then
    BROKER_PID=$(cat /tmp/mcp_broker.pid)
    echo "MCP Broker Server (PID: $BROKER_PID) 중지 중..."
    kill $BROKER_PID 2>/dev/null && echo "  ✅ 중지됨" || echo "  ⚠️  이미 종료됨"
    rm -f /tmp/mcp_broker.pid
else
    echo "MCP Broker Server: PID 파일 없음, 프로세스 검색 중..."
    pkill -f "mcp_broker.main" && echo "  ✅ 프로세스 중지됨" || echo "  ⚠️  실행 중인 프로세스 없음"
fi

echo ""
echo "=========================================="
echo "✅ 모든 서버가 중지되었습니다"
echo "=========================================="

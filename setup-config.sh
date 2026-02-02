#!/bin/bash
# 설정 파일 생성 스크립트
# 보안을 위해 실제 비밀번호는 입력받도록 함

set -e

echo "=========================================="
echo "AI Agent Communication System 설정"
echo "=========================================="
echo ""

# 보안 키 생성 안내
echo "보안 키 생성 중..."
JWT_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
API_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')

echo ""
echo "1️⃣ MCP Broker 설정 (config.json)"
cat > config.json << EOF
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
      "origins": [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://localhost:3000",
        "https://localhost:8000"
      ],
      "allow_credentials": true
    }
  },
  "database": {
    "url": "postgresql+asyncpg://agent:changeme@localhost/agent_comm",
    "pool_size": 10,
    "max_overflow": 20
  },
  "authentication": {
    "jwt": {
      "secret_key": "$JWT_SECRET",
      "algorithm": "HS256",
      "access_token_expire_minutes": 15,
      "refresh_token_expire_days": 7
    },
    "api_token": {
      "prefix": "agent_",
      "secret": "$API_SECRET"
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
    "nickname": "DevAgent",
    "project_id": "agent-comm",
    "capabilities": []
  },
  "communication_server": {
    "url": "http://0.0.0.0:8000",
    "timeout": 30
  }
}
EOF

echo ""
echo "2️⃣ Communication Server 설정 (config.comm.json)"
cat > config.comm.json << EOF
{
  "version": "1.0.0",
  "server": {
    "host": "0.0.0.0",
    "port": 8000,
    "ssl": {
      "enabled": false,
      "cert_path": "./certificates/cert.pem",
      "key_path": "./certificates/key.pem"
    },
    "cors": {
      "origins": [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8001",
        "https://localhost:3000",
        "https://localhost:8000",
        "https://localhost:8001"
      ],
      "allow_credentials": true
    }
  },
  "database": {
    "url": "postgresql+asyncpg://agent:changeme@localhost/agent_comm",
    "pool_size": 10,
    "max_overflow": 20
  },
  "authentication": {
    "jwt": {
      "secret_key": "$JWT_SECRET",
      "algorithm": "HS256",
      "access_token_expire_minutes": 15,
      "refresh_token_expire_days": 7
    },
    "api_token": {
      "prefix": "agent_",
      "secret": "$API_SECRET"
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
    "nickname": "DevAgent",
    "project_id": "agent-comm",
    "capabilities": []
  },
  "communication_server": {
    "url": "http://0.0.0.0:8000",
    "timeout": 30
  }
}
EOF

echo ""
echo "=========================================="
echo "✅ 설정 파일이 생성되었습니다"
echo "=========================================="
echo ""
echo "⚠️  중요: 데이터베이스 비밀번호를 변경하세요:"
echo "   config.json 및 config.comm.json에서 'changeme'를 실제 비밀번호로 변경"
echo ""
echo "생성된 보안 키:"
echo "  JWT Secret: $JWT_SECRET"
echo "  API Secret: $API_SECRET"
echo ""
echo "이 키들은 안전한 곳에 보관하세요!"

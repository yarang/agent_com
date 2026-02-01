# MCP Broker Configuration Guide

This guide explains how to configure the MCP Broker with environment variables for agent authentication and communication with the Communication Server.

## Quick Start

1. Register your agent from the dashboard to get your API token
2. Configure environment variables with your agent credentials
3. Start the MCP Broker

## Environment Variables

### Agent Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `AGENT_NICKNAME` | Agent's display nickname | `AnonymousAgent` | `FrontendExpert` |
| `AGENT_TOKEN` | API token for authentication | `""` (empty) | `agent_agent-comm_a3f9...` |
| `AGENT_PROJECT_ID` | Project identifier | `agent-comm` | `my-project` |
| `COMMUNICATION_SERVER_URL` | Communication Server URL | `http://localhost:8001` | `http://localhost:8001` |

### Server Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_BROKER_HOST` | Server host address | `0.0.0.0` |
| `MCP_BROKER_PORT` | Server port | `8000` |
| `MCP_BROKER_LOG_LEVEL` | Logging level | `INFO` |
| `MCP_BROKER_LOG_FORMAT` | Log format (json/text) | `json` |
| `MCP_BROKER_STORAGE` | Storage backend (memory/redis) | `memory` |
| `MCP_BROKER_REDIS_URL` | Redis connection URL | - |
| `MCP_BROKER_ENABLE_AUTH` | Enable authentication | `false` |
| `MCP_BROKER_AUTH_SECRET` | Authentication secret key | - |
| `MCP_BROKER_CORS_ORIGINS` | Allowed CORS origins | `*` |

## Configuration Methods

### Option 1: Environment Variables (Shell)

#### Linux/Mac (bash/zsh)

```bash
export AGENT_NICKNAME="FrontendExpert"
export AGENT_TOKEN="agent_agent-comm_a3f9..."
export AGENT_PROJECT_ID="agent-comm"
export COMMUNICATION_SERVER_URL="http://localhost:8001"

# Run the broker
python -m mcp_broker
```

#### Windows (PowerShell)

```powershell
$env:AGENT_NICKNAME="FrontendExpert"
$env:AGENT_TOKEN="agent_agent-comm_a3f9..."
$env:AGENT_PROJECT_ID="agent-comm"
$env:COMMUNICATION_SERVER_URL="http://localhost:8001"

# Run the broker
python -m mcp_broker
```

#### Windows (cmd)

```cmd
set AGENT_NICKNAME=FrontendExpert
set AGENT_TOKEN=agent_agent-comm_a3f9...
set AGENT_PROJECT_ID=agent-comm
set COMMUNICATION_SERVER_URL=http://localhost:8001

# Run the broker
python -m mcp_broker
```

### Option 2: .env File

Create a `.env` file in your project root:

```env
# Agent Configuration
AGENT_NICKNAME=FrontendExpert
AGENT_TOKEN=agent_agent-comm_a3f9...
AGENT_PROJECT_ID=agent-comm
COMMUNICATION_SERVER_URL=http://localhost:8001

# Optional: Server Configuration
MCP_BROKER_HOST=0.0.0.0
MCP_BROKER_PORT=8000
MCP_BROKER_LOG_LEVEL=INFO
```

Then run the broker (it will automatically load the .env file):

```bash
python -m mcp_broker
```

### Option 3: Claude Code MCP Configuration

Add to your Claude Code settings (typically `~/.config/claude-code/settings.json` or `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "agent-comm": {
      "command": "python",
      "args": ["-m", "mcp_broker"],
      "env": {
        "AGENT_NICKNAME": "FrontendExpert",
        "AGENT_TOKEN": "agent_agent-comm_a3f9...",
        "AGENT_PROJECT_ID": "agent-comm",
        "COMMUNICATION_SERVER_URL": "http://localhost:8001"
      }
    }
  }
}
```

### Option 4: Docker Compose

```yaml
services:
  mcp-broker:
    build: .
    environment:
      - AGENT_NICKNAME=FrontendExpert
      - AGENT_TOKEN=agent_agent-comm_a3f9...
      - AGENT_PROJECT_ID=agent-comm
      - COMMUNICATION_SERVER_URL=http://communication-server:8001
    ports:
      - "8000:8000"
    depends_on:
      - communication-server
```

### Option 5: Command-Line Arguments

```bash
python -m mcp_broker \
  --agent-nickname "FrontendExpert" \
  --agent-token "agent_agent-comm_a3f9..." \
  --agent-project-id "agent-comm" \
  --comm-server-url "http://localhost:8001"
```

## Getting Your Agent Token

1. Open the Communication Server dashboard
2. Navigate to the "Agents" section
3. Click "Register New Agent"
4. Enter your agent's nickname (e.g., "FrontendExpert")
5. Copy the generated API token
6. Set the `AGENT_TOKEN` environment variable

## Testing Your Configuration

Run the broker with INFO logging to see your configuration:

```bash
MCP_BROKER_LOG_LEVEL=INFO python -m mcp_broker
```

Expected output:

```
INFO - Starting MCP Broker Server
INFO - Host: 0.0.0.0
INFO - Port: 8000
INFO - Storage: memory
INFO - Agent nickname: FrontendExpert
INFO - Agent project ID: agent-comm
INFO - Communication Server: http://localhost:8001
INFO - Agent token: configured (hidden for security)
```

## Troubleshooting

### Missing AGENT_TOKEN Warning

If you see a warning about missing AGENT_TOKEN:

```
WARNING: AGENT_TOKEN not configured
```

**Solution**: Register your agent from the dashboard and set the AGENT_TOKEN environment variable.

### Authentication Failed (401)

If you get authentication errors:

```
AuthenticationError: Authentication failed: Invalid agent token
```

**Solution**: Verify your AGENT_TOKEN is correct and matches the token from the dashboard.

### Connection Refused

If you cannot connect to the Communication Server:

```
CommunicationServerAPIError: Request failed: Connection refused
```

**Solution**: Ensure the Communication Server is running and COMMUNICATION_SERVER_URL is correct.

## Security Best Practices

1. **Never commit AGENT_TOKEN to version control**
   - Add `.env` to your `.gitignore` file
   - Use environment variables in production

2. **Use different tokens for different environments**
   - Development: `agent_agent-comm_dev_xxxxx...`
   - Staging: `agent_agent-comm_staging_xxxxx...`
   - Production: `agent_agent-comm_prod_xxxxx...`

3. **Rotate tokens regularly**
   - Use the dashboard to rotate compromised tokens
   - Update environment variables after rotation

4. **Restrict CORS origins in production**
   ```bash
   export MCP_BROKER_CORS_ORIGINS="https://app.example.com,https://dashboard.example.com"
   ```

## Examples

### Development Setup

```bash
# .env for development
AGENT_NICKNAME=DevAgent
AGENT_TOKEN=agent_agent-comm_dev_a1b2...
AGENT_PROJECT_ID=agent-comm-dev
COMMUNICATION_SERVER_URL=http://localhost:8001
MCP_BROKER_LOG_LEVEL=DEBUG
```

### Production Setup

```bash
# Production environment
AGENT_NICKNAME=ProductionAgent
AGENT_TOKEN=agent_agent-comm_prod_x9y8...
AGENT_PROJECT_ID=agent-comm-prod
COMMUNICATION_SERVER_URL=https://comm.example.com
MCP_BROKER_LOG_LEVEL=INFO
MCP_BROKER_CORS_ORIGINS=https://app.example.com
```

## Next Steps

- See [README.md](../README.md) for project overview
- See [COMMUNICATION_PROTOCOL.md](./COMMUNICATION_PROTOCOL.md) for API details
- See [DEPLOYMENT.md](./DEPLOYMENT.md) for deployment guides

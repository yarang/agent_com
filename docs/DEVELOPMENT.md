# Development Setup with uv

## Prerequisites

- Python 3.13+
- uv package manager

## Installation

### 1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or using pip:

```bash
pip install uv
```

### 2. Install Dependencies

```bash
# Using the installation script
./scripts/install.sh

# Or manually
uv venv
uv pip install -e ".[dev,redis]"
```

### 3. Activate Virtual Environment

```bash
source .venv/bin/activate
```

## Development Commands

### Running Services

```bash
# MCP Broker Server
uv run python -m mcp_broker.main

# Communication Server
uv run python -m communication_server.main

# With uvicorn for development (hot reload)
uv run uvicorn mcp_broker.main:app --reload --host 0.0.0.0 --port 8000
uv run uvicorn communication_server.main:app --reload --host 0.0.0.0 --port 8001
```

### Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/mcp_broker --cov-report=html

# Run specific test categories
uv run pytest -m unit          # Unit tests only
uv run pytest -m integration   # Integration tests only
uv run pytest -m slow          # Slow tests only

# Run specific test file
uv run pytest tests/unit/test_protocol_registry.py
```

### Code Quality

```bash
# Format code with ruff
uv run ruff format src/ tests/

# Lint code
uv run ruff check src/ tests/

# Auto-fix linting issues
uv run ruff check --fix src/ tests/

# Type check with mypy
uv run mypy src/

# Run all quality checks
uv run ruff format src/ tests/ && uv run ruff check src/ tests/ && uv run mypy src/
```

### Docker Development

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild images
docker-compose build --no-cache
```

## Project Structure

```
agent-comm/
├── src/
│   ├── mcp_broker/           # MCP Broker Server
│   ├── communication_server/ # Communication Server
│   └── agent_comm_core/      # Shared core library
├── tests/                    # Test files
├── scripts/                  # Utility scripts
├── docs/                     # Documentation
├── pyproject.toml            # Project configuration
├── .python-version           # Python version for uv
├── .uvrc                     # uv configuration
└── docker-compose.yml        # Docker services
```

## Environment Variables

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Key environment variables:

- `MCP_BROKER_HOST`: Server host (default: `0.0.0.0`)
- `MCP_BROKER_PORT`: Server port (default: `8000`)
- `MCP_BROKER_LOG_LEVEL`: Logging level (default: `INFO`)
- `MCP_BROKER_STORAGE`: Storage backend (`memory` or `redis`)
- `DATABASE_URL`: PostgreSQL connection URL
- `REDIS_URL`: Redis connection URL

## Troubleshooting

### uv not found

```bash
# Add uv to PATH
export PATH="$HOME/.cargo/bin:$PATH"

# Or install globally
pip install uv
```

### Virtual environment issues

```bash
# Remove and recreate
rm -rf .venv
uv venv
uv pip install -e ".[dev]"
```

### Import errors

```bash
# Reinstall in editable mode
uv pip install -e .
```

## Useful Links

- [uv documentation](https://github.com/astral-sh/uv)
- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [MCP specification](https://modelcontextprotocol.io/)

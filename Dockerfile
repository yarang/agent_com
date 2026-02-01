# AI Agent Communication System - Dockerfile with uv
# NOTE: This Dockerfile is maintained for backward compatibility.
# For new deployments, use the dedicated Dockerfiles:
#   - Dockerfile.mcp for MCP Broker Server
#   - Dockerfile.communication for Communication Server

FROM python:3.13-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy pyproject.toml
COPY pyproject.toml ./

# Install dependencies using uv
RUN uv pip install --system -e .

# Copy source
COPY src/ ./src/

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENV MCP_BROKER_HOST=0.0.0.0 \
    MCP_BROKER_PORT=8000

# Run the MCP broker server
CMD ["python3", "-m", "uvicorn", "mcp_broker.main:app", "--host", "0.0.0.0", "--port", "8000"]

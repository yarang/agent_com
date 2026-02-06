"""
API package for Agent Communication Core.

This package provides REST API endpoints for managing agents and tasks.
"""

from agent_comm_core.api.v1 import router as v1_router

__all__ = [
    "v1_router",
]

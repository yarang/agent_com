"""
API v1 endpoints for Communication Server.

This package contains version 1 API endpoints.
"""

from communication_server.api.v1.agents import router as agents_router
from communication_server.api.v1.projects import router as projects_v1_router

__all__ = [
    "agents_router",
    "projects_v1_router",
]

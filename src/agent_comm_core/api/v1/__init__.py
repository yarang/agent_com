"""
API v1 endpoints for Agent Communication Core.

This package contains version 1 API endpoints for Agent and Task management.
"""

from fastapi import APIRouter

from agent_comm_core.api.v1.agents import router as agents_router
from agent_comm_core.api.v1.tasks import router as tasks_router

# Create the main v1 router
router = APIRouter(prefix="/v1", tags=["v1"])

# Register sub-routers
router.include_router(agents_router)
router.include_router(tasks_router)

__all__ = [
    "router",
    "agents_router",
    "tasks_router",
]

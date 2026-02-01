"""
REST API endpoints for Communication Server.

Provides API routes for communications, meetings, decisions, status, authentication, i18n, and projects.
"""

from communication_server.api.auth import router as auth_router
from communication_server.api.communications import router as communications_router
from communication_server.api.decisions import router as decisions_router
from communication_server.api.i18n import router as i18n_router
from communication_server.api.meetings import router as meetings_router
from communication_server.api.messages import router as messages_router
from communication_server.api.projects import router as projects_router
from communication_server.api.status import router as status_router

__all__ = [
    "communications_router",
    "meetings_router",
    "decisions_router",
    "status_router",
    "auth_router",
    "i18n_router",
    "projects_router",
    "messages_router",
]

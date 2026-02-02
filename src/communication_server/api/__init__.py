"""
REST API endpoints for Communication Server.

Provides API routes for communications, meetings, decisions, status, authentication, i18n, projects, agents, security, and chat.
"""

from communication_server.api.auth import router as auth_router
from communication_server.api.chat import router as chat_router
from communication_server.api.communications import router as communications_router
from communication_server.api.decisions import router as decisions_router
from communication_server.api.i18n import router as i18n_router
from communication_server.api.mediators import router as mediators_router
from communication_server.api.meetings import router as meetings_router
from communication_server.api.messages import router as messages_router
from communication_server.api.projects import router as projects_router
from communication_server.api.projects_db import router as projects_db_router
from communication_server.api.security import router as security_router
from communication_server.api.status import router as status_router
from communication_server.api.v1.agents import router as agents_router

__all__ = [
    "communications_router",
    "meetings_router",
    "decisions_router",
    "status_router",
    "auth_router",
    "i18n_router",
    "projects_router",
    "projects_db_router",
    "messages_router",
    "security_router",
    "agents_router",
    "mediators_router",
    "chat_router",
]

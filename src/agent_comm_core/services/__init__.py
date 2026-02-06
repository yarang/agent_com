"""
Business logic services for Agent Communication System.

Services provide high-level operations that coordinate
between repositories and implement business rules.

Includes base classes for service implementation.
"""

# Import concrete service implementations
from agent_comm_core.services.agent_api_key import (
    AgentApiKeyService,
    get_agent_api_key_service,
)
from agent_comm_core.services.agent_service import AgentService, get_agent_service
from agent_comm_core.services.audit_log import AuditLogService, get_audit_log_service
from agent_comm_core.services.base import ServiceBase, SessionServiceBase
from agent_comm_core.services.communication import CommunicationService
from agent_comm_core.services.discussion import DiscussionService
from agent_comm_core.services.meeting import MeetingService
from agent_comm_core.services.task_service import TaskService, get_task_service

__all__ = [
    # Base classes (new)
    "ServiceBase",
    "SessionServiceBase",
    # Service implementations
    "CommunicationService",
    "MeetingService",
    "DiscussionService",
    "AuditLogService",
    "AgentApiKeyService",
    "AgentService",
    "TaskService",
    # Service factory functions
    "get_audit_log_service",
    "get_agent_api_key_service",
    "get_agent_service",
    "get_task_service",
]

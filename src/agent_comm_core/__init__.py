"""
Agent Communication Core Library

Shared core library for the AI Agent Communication System.
Provides models, repositories, services, and database utilities
used by both MCP Broker Server and Communication Server.
"""

__version__ = "1.0.0"

# Re-export main components
# Configuration
from agent_comm_core.config import Config, ConfigLoader, get_config
from agent_comm_core.db import Base, get_db_session, init_db
from agent_comm_core.models import (
    Communication,
    CommunicationCreate,
    Decision,
    Meeting,
    MeetingMessage,
    MeetingParticipant,
)
from agent_comm_core.repositories import (
    BaseRepository,
    CommunicationRepository,
    MeetingRepository,
)
from agent_comm_core.services import (
    CommunicationService,
    DiscussionService,
    MeetingService,
)

__all__ = [
    # Models
    "Communication",
    "CommunicationCreate",
    "Meeting",
    "MeetingMessage",
    "MeetingParticipant",
    "Decision",
    # Repositories
    "BaseRepository",
    "CommunicationRepository",
    "MeetingRepository",
    # Services
    "CommunicationService",
    "MeetingService",
    "DiscussionService",
    # Database
    "Base",
    "get_db_session",
    "init_db",
    # Configuration
    "Config",
    "ConfigLoader",
    "get_config",
]

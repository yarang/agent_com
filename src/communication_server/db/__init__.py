"""
Database models for Communication Server.

SQLAlchemy ORM models that map to the Pydantic models in agent_comm_core.

Includes:
- Existing models (CommunicationDB, MeetingDB, etc.) for other specifications
- AgentCommunicationDB, AgentMeetingDB, etc. for SPEC-AGENT-COMM-001
"""

from communication_server.db.agent_comm import (
    AgentCommunicationDB,
    AgentDecisionDB,
    AgentMeetingDB,
    AgentMeetingMessageDB,
    AgentMeetingParticipantDB,
    MeetingStatus,
    MeetingType,
    MessageType,
)
from communication_server.db.communication import CommunicationDB
from communication_server.db.meeting import (
    DecisionDB,
    MeetingDB,
    MeetingMessageDB,
    MeetingParticipantDB,
)

__all__ = [
    # Existing models
    "CommunicationDB",
    "MeetingDB",
    "MeetingParticipantDB",
    "MeetingMessageDB",
    "DecisionDB",
    # SPEC-AGENT-COMM-001 models
    "AgentCommunicationDB",
    "AgentMeetingDB",
    "AgentMeetingParticipantDB",
    "AgentMeetingMessageDB",
    "AgentDecisionDB",
    "MeetingStatus",
    "MeetingType",
    "MessageType",
]

"""
Meeting-related MCP Tools for Claude Code integration.

This module defines MCP tools for:
- Creating meetings
- Joining meetings
- Getting meeting decisions
- Proposing topics for discussion
"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from mcp_broker.client.http_client import HTTPClient


# Tool input schemas


class SendMessageInput(BaseModel):
    """Input schema for send_message tool."""

    to_agent: str = Field(description="Target agent ID")
    message_type: str = Field(
        description="Type of message",
        pattern="^(proposal|question|answer|notification)$",
    )
    content: str = Field(description="Message content")
    topic: str | None = Field(default=None, description="Optional topic")


class CreateMeetingInput(BaseModel):
    """Input schema for create_meeting tool."""

    topic: str = Field(description="Meeting topic")
    participants: list[str] = Field(description="Agent IDs of participants")
    meeting_type: str = Field(
        default="user_specified",
        description="Meeting type",
        pattern="^(user_specified|auto_generated)$",
    )
    description: str | None = Field(default=None, description="Optional description")
    max_duration_seconds: int | None = Field(
        default=None, description="Maximum meeting duration in seconds"
    )


class JoinMeetingInput(BaseModel):
    """Input schema for join_meeting tool."""

    meeting_id: str = Field(description="Meeting UUID")
    agent_id: str = Field(description="Your agent ID")
    role: str = Field(default="participant", description="Participant role")


class GetDecisionsInput(BaseModel):
    """Input schema for get_decisions tool."""

    meeting_id: str | None = Field(default=None, description="Meeting UUID (optional)")
    status: str | None = Field(
        default=None,
        description="Filter by decision status",
        pattern="^(pending|approved|rejected|deferred)$",
    )
    limit: int = Field(default=100, description="Maximum results")


class ProposeTopicInput(BaseModel):
    """Input schema for propose_topic tool."""

    topic: str = Field(description="Topic to propose")
    priority: str = Field(
        default="medium",
        description="Topic priority",
        pattern="^(low|medium|high)$",
    )
    context: str | None = Field(default=None, description="Additional context for the topic")


class MeetingMCPTools:
    """
    Collection of Meeting-related MCP tools for Claude Code integration.

    This class defines the following tools:
    1. send_message - Send a message to another agent
    2. create_meeting - Create a new meeting
    3. join_meeting - Join an existing meeting
    4. get_decisions - Get meeting decisions
    5. propose_topic - Propose a topic for discussion
    """

    def __init__(
        self,
        http_client: HTTPClient,
        agent_id: str | None = None,
        agent_token: str = "",
        agent_nickname: str = "",
    ) -> None:
        """Initialize meeting MCP tools.

        Args:
            http_client: HTTP client for Communication Server
            agent_id: This agent's ID (deprecated, use agent_nickname)
            agent_token: API token for authentication
            agent_nickname: Agent's display nickname
        """
        self._http_client = http_client
        self._agent_id = agent_id or agent_nickname or http_client.agent_nickname
        self._agent_token = agent_token or http_client.agent_token
        self._agent_nickname = agent_nickname or http_client.agent_nickname

    async def send_message(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Send a message to another agent.

        Args:
            input_data: Tool input with to_agent, message_type, content

        Returns:
            Message delivery result
        """
        from agent_comm_core.models.communication import CommunicationCreate, CommunicationDirection

        parsed = SendMessageInput(**input_data)

        # Get current agent ID
        from_agent = self._agent_id or "claude-code-agent"

        # Log communication via Communication Server
        communication = CommunicationCreate(
            from_agent=from_agent,
            to_agent=parsed.to_agent,
            message_type=parsed.message_type,
            content=parsed.content,
            direction=CommunicationDirection.OUTBOUND,
            metadata={"topic": parsed.topic} if parsed.topic else {},
        )

        try:
            result = await self._http_client.log_communication(communication)

            return {
                "success": True,
                "message_id": str(result.id),
                "from_agent": from_agent,
                "to_agent": parsed.to_agent,
                "message_type": parsed.message_type,
                "created_at": result.created_at.isoformat(),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    async def create_meeting(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new meeting.

        Args:
            input_data: Tool input with topic, participants, meeting_type

        Returns:
            Meeting creation result
        """
        from agent_comm_core.models.meeting import MeetingCreate

        parsed = CreateMeetingInput(**input_data)

        # Create meeting
        meeting_data = MeetingCreate(
            title=parsed.topic,
            participant_ids=parsed.participants,
            description=parsed.description or f"Meeting about {parsed.topic}",
            max_duration_seconds=parsed.max_duration_seconds,
        )

        try:
            meeting = await self._http_client.create_meeting(meeting_data)

            return {
                "success": True,
                "meeting_id": str(meeting.id),
                "title": meeting.title,
                "status": meeting.status.value,
                "participant_ids": parsed.participants,
                "created_at": meeting.created_at.isoformat(),
                "websocket_url": f"/ws/meetings/{meeting.id}",
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    async def join_meeting(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Join an existing meeting via WebSocket.

        Args:
            input_data: Tool input with meeting_id, agent_id

        Returns:
            Meeting join result with WebSocket connection info
        """
        parsed = JoinMeetingInput(**input_data)

        try:
            # Verify meeting exists
            meeting_uuid = UUID(parsed.meeting_id)
            meeting = await self._http_client.get_meeting(meeting_uuid)

            if not meeting:
                return {
                    "success": False,
                    "error": f"Meeting {parsed.meeting_id} not found",
                }

            # Add participant to meeting
            try:
                participant = await self._http_client.add_meeting_participant(
                    meeting_uuid, parsed.agent_id, parsed.role
                )
            except Exception as e:
                # Participant might already exist, continue
                participant = {"agent_id": parsed.agent_id, "role": parsed.role}

            return {
                "success": True,
                "meeting_id": str(meeting.id),
                "title": meeting.title,
                "status": meeting.status.value,
                "participant": {
                    "agent_id": parsed.agent_id,
                    "role": parsed.role,
                },
                "websocket_url": f"/ws/meetings/{meeting.id}",
                "message": "Connect to WebSocket endpoint to join the meeting",
            }

        except ValueError as e:
            return {
                "success": False,
                "error": f"Invalid meeting ID: {e}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    async def get_decisions(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Get meeting decisions.

        Args:
            input_data: Tool input with optional meeting_id, status filters

        Returns:
            Decisions query result
        """
        parsed = GetDecisionsInput(**input_data)

        try:
            meeting_id = UUID(parsed.meeting_id) if parsed.meeting_id else None

            decisions = await self._http_client.list_decisions(
                meeting_id=meeting_id,
                status=parsed.status,
                limit=parsed.limit,
            )

            return {
                "success": True,
                "decisions": [
                    {
                        "id": str(d.id),
                        "title": d.title,
                        "description": d.description,
                        "status": d.status.value,
                        "proposed_by": d.proposed_by,
                        "meeting_id": str(d.meeting_id) if d.meeting_id else None,
                        "selected_option": d.selected_option,
                        "created_at": d.created_at.isoformat(),
                        "decided_at": d.decided_at.isoformat() if d.decided_at else None,
                    }
                    for d in decisions
                ],
                "count": len(decisions),
            }

        except ValueError as e:
            return {
                "success": False,
                "error": f"Invalid meeting ID: {e}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    async def propose_topic(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Propose a topic for discussion to other agents.

        This sends a broadcast message proposing a topic for discussion.
        The topic will be visible to all agents in the project.

        Args:
            input_data: Tool input with topic, priority, context

        Returns:
            Topic proposal result
        """
        from agent_comm_core.models.communication import CommunicationCreate, CommunicationDirection

        parsed = ProposeTopicInput(**input_data)

        # Get current agent ID
        from_agent = self._agent_id or "claude-code-agent"

        # Create topic proposal as a communication
        communication = CommunicationCreate(
            from_agent=from_agent,
            to_agent="broadcast",  # Broadcast to all agents
            message_type="proposal",
            content=f"Topic proposal: {parsed.topic}",
            direction=CommunicationDirection.OUTBOUND,
            metadata={
                "proposal_type": "topic",
                "priority": parsed.priority,
                "topic": parsed.topic,
                "context": parsed.context,
            },
        )

        try:
            result = await self._http_client.log_communication(communication)

            return {
                "success": True,
                "proposal_id": str(result.id),
                "topic": parsed.topic,
                "priority": parsed.priority,
                "proposed_by": from_agent,
                "created_at": result.created_at.isoformat(),
                "message": "Topic proposal has been broadcast to all agents",
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Get all tool definitions for MCP registration.

        Returns:
            List of tool definitions with input schemas
        """
        return [
            {
                "name": "send_message",
                "description": "Send a message to another Claude Code agent in the same project",
                "inputSchema": SendMessageInput.model_json_schema(),
            },
            {
                "name": "create_meeting",
                "description": "Create a new AI meeting with specified participants",
                "inputSchema": CreateMeetingInput.model_json_schema(),
            },
            {
                "name": "join_meeting",
                "description": "Join an existing meeting via WebSocket",
                "inputSchema": JoinMeetingInput.model_json_schema(),
            },
            {
                "name": "get_decisions",
                "description": "Get meeting decisions, optionally filtered by meeting or status",
                "inputSchema": GetDecisionsInput.model_json_schema(),
            },
            {
                "name": "propose_topic",
                "description": "Propose a topic for discussion to other agents",
                "inputSchema": ProposeTopicInput.model_json_schema(),
            },
        ]

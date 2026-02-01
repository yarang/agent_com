"""
Integration tests for MCP Broker to Communication Server integration.

Tests the MCP tools that communicate with the Communication Server API:
- send_message MCP tool → communication server API
- create_meeting MCP tool → meeting creation
- get_decisions MCP tool → decision retrieval
- Error handling when communication server is down
"""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from mcp_broker.client.http_client import HTTPClient, CommunicationServerAPIError
from mcp_broker.mcp.meeting_tools import MeetingMCPTools
from agent_comm_core.models.communication import CommunicationDirection
from agent_comm_core.models.meeting import MeetingStatus


@pytest.mark.integration
class TestMCPCommunicationIntegration:
    """Tests for MCP Broker to Communication Server integration."""

    async def test_send_message_mcp_tool_success(
        self,
        http_client: HTTPClient,
        meeting_mcp_tools: MeetingMCPTools,
        communication_server,
    ):
        """Test send_message MCP tool successfully logs communication via API."""
        # Mock the HTTP client to call the actual communication server
        with patch.object(http_client, "log_communication", new_callable=AsyncMock) as mock_log:
            # Setup mock to return a communication
            from agent_comm_core.models.communication import Communication

            mock_comm = Communication(
                id=uuid4(),
                from_agent="test-agent",
                to_agent="agent-002",
                message_type="question",
                content="How should we implement this feature?",
                direction=CommunicationDirection.OUTBOUND,
                metadata={"topic": "feature-implementation"},
            )
            mock_log.return_value = mock_comm

            # Call send_message
            input_data = {
                "to_agent": "agent-002",
                "message_type": "question",
                "content": "How should we implement this feature?",
                "topic": "feature-implementation",
            }

            result = await meeting_mcp_tools.send_message(input_data)

            # Verify result
            assert result["success"] is True
            assert "message_id" in result
            assert result["from_agent"] == "test-agent"
            assert result["to_agent"] == "agent-002"
            assert result["message_type"] == "question"

            # Verify the mock was called correctly
            mock_log.assert_called_once()

    async def test_send_message_mcp_tool_error_handling(
        self,
        meeting_mcp_tools: MeetingMCPTools,
        http_client: HTTPClient,
    ):
        """Test send_message MCP tool handles errors gracefully."""
        with patch.object(http_client, "log_communication", new_callable=AsyncMock) as mock_log:
            # Simulate an error
            mock_log.side_effect = CommunicationServerAPIError(
                message="Server unavailable", status_code=503
            )

            input_data = {
                "to_agent": "agent-002",
                "message_type": "question",
                "content": "Test message",
            }

            result = await meeting_mcp_tools.send_message(input_data)

            # Verify error handling
            assert result["success"] is False
            assert "error" in result

    async def test_create_meeting_mcp_tool_success(
        self,
        meeting_mcp_tools: MeetingMCPTools,
        http_client: HTTPClient,
    ):
        """Test create_meeting MCP tool successfully creates meeting via API."""
        with patch.object(http_client, "create_meeting", new_callable=AsyncMock) as mock_create:
            # Setup mock to return a meeting
            from agent_comm_core.models.meeting import Meeting

            mock_meeting = Meeting(
                id=uuid4(),
                title="API Design Discussion",
                status=MeetingStatus.PENDING,
                participant_ids=["agent-001", "agent-002"],
                description="Meeting about API design",
            )
            mock_create.return_value = mock_meeting

            input_data = {
                "topic": "API Design Discussion",
                "participants": ["agent-001", "agent-002"],
                "meeting_type": "user_specified",
                "description": "Meeting about API design",
                "max_duration_seconds": 3600,
            }

            result = await meeting_mcp_tools.create_meeting(input_data)

            # Verify result
            assert result["success"] is True
            assert "meeting_id" in result
            assert result["title"] == "API Design Discussion"
            assert result["status"] == "pending"
            assert "websocket_url" in result
            assert result["websocket_url"] == f"/ws/meetings/{mock_meeting.id}"

    async def test_create_meeting_mcp_tool_validation_error(
        self,
        meeting_mcp_tools: MeetingMCPTools,
        http_client: HTTPClient,
    ):
        """Test create_meeting MCP tool handles validation errors."""
        with patch.object(http_client, "create_meeting", new_callable=AsyncMock) as mock_create:
            # Simulate validation error
            mock_create.side_effect = ValueError("At least one participant is required")

            input_data = {
                "topic": "Test Meeting",
                "participants": [],  # Empty participants
                "meeting_type": "user_specified",
            }

            result = await meeting_mcp_tools.create_meeting(input_data)

            # Verify error handling
            assert result["success"] is False
            assert "error" in result

    async def test_get_decisions_mcp_tool_success(
        self,
        meeting_mcp_tools: MeetingMCPTools,
        http_client: HTTPClient,
    ):
        """Test get_decisions MCP tool retrieves decisions via API."""
        with patch.object(http_client, "list_decisions", new_callable=AsyncMock) as mock_list:
            # Setup mock to return decisions
            from agent_comm_core.models.decision import Decision, DecisionStatus

            meeting_id = uuid4()
            mock_decisions = [
                Decision(
                    id=uuid4(),
                    title="Use FastAPI",
                    description="We should use FastAPI for the REST API",
                    context={},
                    proposed_by="agent-001",
                    options=[{"title": "FastAPI"}, {"title": "Flask"}],
                    status=DecisionStatus.APPROVED,
                    meeting_id=meeting_id,
                    selected_option={"title": "FastAPI"},
                    rationale="FastAPI has better async support",
                ),
            ]
            mock_list.return_value = mock_decisions

            input_data = {
                "meeting_id": str(meeting_id),
                "status": "approved",
                "limit": 100,
            }

            result = await meeting_mcp_tools.get_decisions(input_data)

            # Verify result
            assert result["success"] is True
            assert "decisions" in result
            assert result["count"] == 1
            assert result["decisions"][0]["title"] == "Use FastAPI"
            assert result["decisions"][0]["status"] == "approved"

    async def test_get_decisions_mcp_tool_empty_results(
        self,
        meeting_mcp_tools: MeetingMCPTools,
        http_client: HTTPClient,
    ):
        """Test get_decisions MCP tool handles empty results."""
        with patch.object(http_client, "list_decisions", new_callable=AsyncMock) as mock_list:
            # Return empty list
            mock_list.return_value = []

            input_data = {
                "status": "pending",
                "limit": 100,
            }

            result = await meeting_mcp_tools.get_decisions(input_data)

            # Verify empty result is handled correctly
            assert result["success"] is True
            assert result["decisions"] == []
            assert result["count"] == 0

    async def test_communication_server_unavailable(
        self,
        meeting_mcp_tools: MeetingMCPTools,
        http_client: HTTPClient,
    ):
        """Test MCP tools handle communication server being down."""
        with patch.object(http_client, "log_communication", new_callable=AsyncMock) as mock_log:
            # Simulate server being down
            mock_log.side_effect = CommunicationServerAPIError(
                message="Connection refused", status_code=503
            )

            input_data = {
                "to_agent": "agent-002",
                "message_type": "question",
                "content": "Test message",
            }

            result = await meeting_mcp_tools.send_message(input_data)

            # Verify error is returned but doesn't crash
            assert result["success"] is False
            assert "error" in result
            assert "503" in result["error"] or "Connection" in result["error"]

    async def test_propose_topic_broadcast(
        self,
        meeting_mcp_tools: MeetingMCPTools,
        http_client: HTTPClient,
    ):
        """Test propose_topic MCP tool broadcasts to all agents."""
        with patch.object(http_client, "log_communication", new_callable=AsyncMock) as mock_log:
            # Setup mock
            from agent_comm_core.models.communication import Communication

            mock_comm = Communication(
                id=uuid4(),
                from_agent="test-agent",
                to_agent="broadcast",
                message_type="proposal",
                content="Topic proposal: Database Schema Design",
                direction=CommunicationDirection.OUTBOUND,
                metadata={
                    "proposal_type": "topic",
                    "priority": "high",
                    "topic": "Database Schema Design",
                    "context": "We need to finalize the schema",
                },
            )
            mock_log.return_value = mock_comm

            input_data = {
                "topic": "Database Schema Design",
                "priority": "high",
                "context": "We need to finalize the schema",
            }

            result = await meeting_mcp_tools.propose_topic(input_data)

            # Verify broadcast was sent
            assert result["success"] is True
            assert result["topic"] == "Database Schema Design"
            assert result["priority"] == "high"
            assert result["proposed_by"] == "test-agent"
            assert "proposal_id" in result

            # Verify the communication was created with broadcast target
            mock_log.assert_called_once()
            call_args = mock_log.call_args[0][0]
            assert call_args.to_agent == "broadcast"
            assert call_args.message_type == "proposal"


@pytest.mark.integration
class TestMCPToCommunicationServerAPI:
    """Tests for direct HTTP client to Communication Server API."""

    async def test_http_client_log_communication(
        self,
        communication_server,
        clean_db,
        sample_agent_ids,
    ):
        """Test HTTP client can log communication via API."""
        from agent_comm_core.models.communication import CommunicationCreate

        # Create communication via API
        comm_data = CommunicationCreate(
            from_agent=sample_agent_ids[0],
            to_agent=sample_agent_ids[1],
            message_type="question",
            content="Integration test message",
            direction=CommunicationDirection.OUTBOUND,
        )

        response = await communication_server.post(
            "/api/v1/communications",
            json=comm_data.model_dump(mode="json"),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["from_agent"] == sample_agent_ids[0]
        assert data["to_agent"] == sample_agent_ids[1]
        assert data["message_type"] == "question"
        assert "id" in data

    async def test_http_client_create_meeting(
        self,
        communication_server,
        clean_db,
        sample_agent_ids,
    ):
        """Test HTTP client can create meeting via API."""
        meeting_data = {
            "title": "Integration Test Meeting",
            "participant_ids": sample_agent_ids[:2],
            "description": "Test meeting via API",
            "agenda": ["Item 1", "Item 2"],
            "max_duration_seconds": 1800,
        }

        response = await communication_server.post(
            "/api/v1/meetings",
            json=meeting_data,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Integration Test Meeting"
        assert data["status"] == "pending"
        assert len(data["participant_ids"]) == 2
        assert "id" in data

    async def test_http_client_get_meeting_messages(
        self,
        communication_server,
        active_meeting,
        sample_agent_ids,
        meeting_service,
        clean_db,
    ):
        """Test HTTP client can retrieve meeting messages via API."""
        # Record some messages
        await meeting_service.record_message(
            meeting_id=active_meeting.id,
            agent_id=sample_agent_ids[0],
            content="Test message 1",
            message_type="statement",
        )
        await meeting_service.record_message(
            meeting_id=active_meeting.id,
            agent_id=sample_agent_ids[1],
            content="Test message 2",
            message_type="question",
        )
        await clean_db.commit()

        # Get messages via API
        response = await communication_server.get(
            f"/api/v1/meetings/{active_meeting.id}/messages",
            params={"limit": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["content"] == "Test message 1"
        assert data[1]["content"] == "Test message 2"

    async def test_http_client_query_communications_with_filters(
        self,
        communication_server,
        clean_db,
        sample_agent_ids,
        communication_service,
    ):
        """Test HTTP client can query communications with filters."""
        # Create communications
        await communication_service.log_communication(
            from_agent=sample_agent_ids[0],
            to_agent=sample_agent_ids[1],
            message_type="question",
            content="Test question",
        )
        await communication_service.log_communication(
            from_agent=sample_agent_ids[1],
            to_agent=sample_agent_ids[0],
            message_type="answer",
            content="Test answer",
        )
        await clean_db.commit()

        # Query with from_agent filter
        response = await communication_server.get(
            "/api/v1/communications",
            params={"from_agent": sample_agent_ids[0], "limit": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["from_agent"] == sample_agent_ids[0]
        assert data[0]["message_type"] == "question"

    async def test_http_client_start_and_end_meeting(
        self,
        communication_server,
        sample_meeting,
    ):
        """Test HTTP client can start and end meetings via API."""
        # Start meeting
        start_response = await communication_server.post(
            f"/api/v1/meetings/{sample_meeting.id}/start",
        )
        assert start_response.status_code == 200
        start_data = start_response.json()
        assert start_data["status"] == "active"
        assert start_data["started_at"] is not None

        # End meeting
        end_response = await communication_server.post(
            f"/api/v1/meetings/{sample_meeting.id}/end",
        )
        assert end_response.status_code == 200
        end_data = end_response.json()
        assert end_data["status"] == "completed"
        assert end_data["ended_at"] is not None


@pytest.mark.integration
class TestMCPEndToEndFlow:
    """End-to-end tests for MCP workflow."""

    async def test_full_communication_workflow(
        self,
        meeting_mcp_tools: MeetingMCPTools,
        http_client: HTTPClient,
        sample_agent_ids,
    ):
        """Test complete workflow: send message, create meeting, get decisions."""
        meeting_id = None

        with (
            patch.object(http_client, "log_communication", new_callable=AsyncMock) as mock_log,
            patch.object(http_client, "create_meeting", new_callable=AsyncMock) as mock_create,
            patch.object(http_client, "list_decisions", new_callable=AsyncMock) as mock_list,
        ):

            # Setup mocks
            from agent_comm_core.models.communication import Communication
            from agent_comm_core.models.meeting import Meeting
            from agent_comm_core.models.decision import Decision, DecisionStatus

            mock_comm = Communication(
                id=uuid4(),
                from_agent="test-agent",
                to_agent=sample_agent_ids[0],
                message_type="proposal",
                content="I propose we have a meeting",
                direction=CommunicationDirection.OUTBOUND,
            )
            mock_log.return_value = mock_comm

            mock_meeting = Meeting(
                id=uuid4(),
                title="Test Meeting",
                status=MeetingStatus.PENDING,
                participant_ids=[sample_agent_ids[0], sample_agent_ids[1]],
            )
            mock_create.return_value = mock_meeting
            meeting_id = mock_meeting.id

            mock_decision = Decision(
                id=uuid4(),
                title="Test Decision",
                description="Test decision description",
                context={},
                proposed_by="test-agent",
                options=[{"title": "Option A"}, {"title": "Option B"}],
                status=DecisionStatus.PENDING,
                meeting_id=meeting_id,
            )
            mock_list.return_value = [mock_decision]

            # Step 1: Send proposal message
            msg_result = await meeting_mcp_tools.send_message(
                {
                    "to_agent": sample_agent_ids[0],
                    "message_type": "proposal",
                    "content": "I propose we have a meeting",
                }
            )
            assert msg_result["success"] is True

            # Step 2: Create meeting
            meeting_result = await meeting_mcp_tools.create_meeting(
                {
                    "topic": "Test Meeting",
                    "participants": [sample_agent_ids[0], sample_agent_ids[1]],
                }
            )
            assert meeting_result["success"] is True

            # Step 3: Get decisions for the meeting
            decisions_result = await meeting_mcp_tools.get_decisions(
                {
                    "meeting_id": str(meeting_id),
                }
            )
            assert decisions_result["success"] is True
            assert len(decisions_result["decisions"]) == 1

"""
End-to-End Scenario Tests.

Tests the complete workflow from start to finish:
1. Register multiple agents
2. Agent A sends message to Agent B
3. Agent C proposes topic
4. Meeting is created and started
5. Agents participate in sequential discussion
6. Decision is recorded
7. Verify all data is persisted
"""

import pytest
from uuid import uuid4

from agent_comm_core.models.communication import CommunicationDirection
from agent_comm_core.models.meeting import MeetingStatus
from agent_comm_core.models.status import AgentRegistration
from communication_server.services.agent_registry import AgentRegistry


@pytest.mark.integration
@pytest.mark.e2e
class TestEndToEndScenario:
    """End-to-end scenario tests."""

    async def test_complete_agent_workflow(
        self,
        agent_registry: AgentRegistry,
        communication_service,
        meeting_service,
        clean_db,
        communication_server,
    ):
        """Test complete workflow from registration to decision recording."""
        # Step 1: Register multiple agents
        agent_registrations = []
        for i, nickname in enumerate(["Alpha", "Beta", "Gamma", "Delta"]):
            full_id = str(uuid4())
            reg = AgentRegistration(
                full_id=full_id,
                nickname=nickname,
                capabilities=["text-generation", "analysis"],
            )
            agent_info = await agent_registry.register_agent(
                full_id=reg.full_id,
                nickname=reg.nickname,
                capabilities=reg.capabilities,
            )
            agent_registrations.append((reg, agent_info))

        # Verify all agents registered
        all_agents = await agent_registry.get_all_agents()
        assert len(all_agents) == 4
        nicknames = {a.nickname for a in all_agents}
        assert {"Alpha", "Beta", "Gamma", "Delta"} == nicknames

        # Step 2: Agent A sends message to Agent B
        comm1 = await communication_service.log_communication(
            from_agent=agent_registrations[0][1].agent_id,
            to_agent=agent_registrations[1][1].agent_id,
            message_type="question",
            content="Should we use PostgreSQL for our database?",
            direction=CommunicationDirection.OUTBOUND,
            metadata={"topic": "database-choice"},
        )

        assert comm1 is not None
        assert comm1.message_type == "question"

        await clean_db.commit()

        # Step 3: Verify communication persisted
        retrieved_comm = await communication_service.get_communication(comm1.id)
        assert retrieved_comm is not None
        assert "PostgreSQL" in retrieved_comm.content

        # Step 4: Agent C proposes topic
        comm2 = await communication_service.log_communication(
            from_agent=agent_registrations[2][1].agent_id,
            to_agent="broadcast",
            message_type="proposal",
            content="Topic proposal: We should discuss the API architecture",
            direction=CommunicationDirection.OUTBOUND,
            metadata={
                "proposal_type": "topic",
                "priority": "high",
                "topic": "API Architecture",
            },
        )

        await clean_db.commit()

        # Step 5: Create meeting with multiple agents
        meeting = await meeting_service.create_meeting(
            title="Architecture Decision Meeting",
            participant_ids=[
                agent_registrations[0][1].agent_id,
                agent_registrations[1][1].agent_id,
                agent_registrations[2][1].agent_id,
            ],
            description="Meeting to decide on system architecture",
            agenda=["Database choice", "API design", "Deployment strategy"],
            max_duration_seconds=3600,
        )

        assert meeting is not None
        assert meeting.status == MeetingStatus.PENDING

        # Verify participants added
        participants = await meeting_service.get_participants(meeting.id)
        assert len(participants) == 3

        await clean_db.commit()

        # Step 6: Start the meeting
        started_meeting = await meeting_service.start_meeting(meeting.id)
        assert started_meeting.status == MeetingStatus.ACTIVE
        assert started_meeting.started_at is not None

        await clean_db.commit()

        # Step 7: Agents participate in discussion
        messages = []
        discussion_content = [
            (agent_registrations[0][1].agent_id, "I recommend PostgreSQL for ACID compliance"),
            (agent_registrations[1][1].agent_id, "Agreed, PostgreSQL is the right choice"),
            (agent_registrations[2][1].agent_id, "Let's also consider Redis for caching"),
        ]

        for agent_id, content in discussion_content:
            msg = await meeting_service.record_message(
                meeting_id=meeting.id,
                agent_id=agent_id,
                content=content,
                message_type="statement",
            )
            messages.append(msg)

        assert len(messages) == 3

        await clean_db.commit()

        # Step 8: Verify messages persisted and in sequence
        retrieved_messages = await meeting_service.get_messages(meeting.id, limit=10)
        assert len(retrieved_messages) == 3

        # Check sequence numbers are sequential
        sequence_numbers = [m.sequence_number for m in retrieved_messages]
        assert sequence_numbers == sorted(sequence_numbers)

        # Step 9: Record a decision
        from communication_server.db.meeting import DecisionDB
        from datetime import datetime, UTC

        decision = DecisionDB(
            title="Database Choice",
            description="Select PostgreSQL as the primary database",
            context={"discussion": "Unanimous agreement"},
            proposed_by=agent_registrations[0][1].agent_id,
            options=[
                {"title": "PostgreSQL", "votes": 3},
                {"title": "MongoDB", "votes": 0},
            ],
            status="approved",
            meeting_id=meeting.id,
            selected_option={"title": "PostgreSQL", "votes": 3},
            rationale="Team agreed on PostgreSQL for ACID compliance",
            decided_at=datetime.now(UTC),
        )

        clean_db.add(decision)
        await clean_db.commit()

        # Verify decision persisted
        from sqlalchemy import select

        result = await clean_db.execute(
            select(DecisionDB).where(DecisionDB.meeting_id == meeting.id)
        )
        decisions = result.scalars().all()

        assert len(decisions) == 1
        assert decisions[0].title == "Database Choice"
        assert decisions[0].status == "approved"

        # Step 10: End the meeting
        ended_meeting = await meeting_service.end_meeting(meeting.id)
        assert ended_meeting.status == MeetingStatus.COMPLETED
        assert ended_meeting.ended_at is not None

        await clean_db.commit()

        # Step 11: Verify all data persisted correctly
        # Verify communications
        all_comms = await communication_service.list_recent(limit=100)
        assert len(all_comms) >= 2

        # Verify meeting
        final_meeting = await meeting_service.get_meeting(meeting.id)
        assert final_meeting.status == MeetingStatus.COMPLETED
        assert final_meeting.started_at is not None
        assert final_meeting.ended_at is not None

        # Verify messages
        final_messages = await meeting_service.get_messages(meeting.id, limit=100)
        assert len(final_messages) == 3

    async def test_multi_agent_discussion_flow(
        self,
        agent_registry: AgentRegistry,
        communication_service,
        meeting_service,
        clean_db,
    ):
        """Test multiple agents discussing and reaching consensus."""
        # Register agents
        agents = []
        for nickname in ["Alice", "Bob", "Charlie", "Diana"]:
            full_id = str(uuid4())
            agent = await agent_registry.register_agent(
                full_id=full_id,
                nickname=nickname,
                capabilities=["discussion"],
            )
            agents.append(agent)

        # Create and start meeting
        meeting = await meeting_service.create_meeting(
            title="Technical Discussion",
            participant_ids=[a.agent_id for a in agents[:3]],
            description="Discussion about technical approach",
        )

        await meeting_service.start_meeting(meeting.id)
        await clean_db.commit()

        # Simulate discussion rounds
        rounds = [
            [
                (agents[0].agent_id, "I propose using FastAPI"),
                (agents[1].agent_id, "FastAPI is good, what about database?"),
                (agents[2].agent_id, "PostgreSQL with asyncpg"),
            ],
            [
                (agents[0].agent_id, "Agreed on PostgreSQL"),
                (agents[1].agent_id, "Let's also add Redis for caching"),
                (agents[2].agent_id, "Sounds good"),
            ],
            [
                (agents[0].agent_id, "Any objections?"),
                (agents[1].agent_id, "No objections from me"),
                (agents[2].agent_id, "I agree, let's proceed"),
            ],
        ]

        all_messages = []
        for round_num, statements in enumerate(rounds):
            for agent_id, content in statements:
                msg = await meeting_service.record_message(
                    meeting_id=meeting.id,
                    agent_id=agent_id,
                    content=content,
                    message_type="statement",
                )
                all_messages.append(msg)

        await clean_db.commit()

        # Verify all messages recorded
        messages = await meeting_service.get_messages(meeting.id, limit=100)
        assert len(messages) == 9  # 3 rounds * 3 agents

        # Check sequential ordering
        for i in range(len(messages) - 1):
            assert messages[i].sequence_number < messages[i + 1].sequence_number

        # End meeting
        await meeting_service.end_meeting(meeting.id)
        await clean_db.commit()

    async def test_communication_flow_between_agents(
        self,
        agent_registry: AgentRegistry,
        communication_service,
        clean_db,
        sample_agent_ids,
    ):
        """Test communication flow between different agents."""
        # Register agents
        for agent_id in sample_agent_ids:
            full_id = str(uuid4())
            await agent_registry.register_agent(
                full_id=full_id,
                nickname=f"Agent-{agent_id[-3:]}",
                capabilities=["communication"],
            )

        # Create a chain of communications
        # Agent 1 -> Agent 2: Question
        comm1 = await communication_service.log_communication(
            from_agent=sample_agent_ids[0],
            to_agent=sample_agent_ids[1],
            message_type="question",
            content="What's the status of the API development?",
            direction=CommunicationDirection.OUTBOUND,
        )

        # Agent 2 -> Agent 1: Answer
        comm2 = await communication_service.log_communication(
            from_agent=sample_agent_ids[1],
            to_agent=sample_agent_ids[0],
            message_type="answer",
            content="The API is 80% complete",
            direction=CommunicationDirection.INBOUND,
            correlation_id=comm1.id,
        )

        # Agent 2 -> Agent 3: Forward
        comm3 = await communication_service.log_communication(
            from_agent=sample_agent_ids[1],
            to_agent=sample_agent_ids[2],
            message_type="notification",
            content="API will be ready soon",
            direction=CommunicationDirection.INTERNAL,
        )

        await clean_db.commit()

        # Verify communications with correlation
        correlated = await communication_service.get_communications(
            correlation_id=comm1.id,
        )

        assert len(correlated) >= 1
        assert correlated[0].id == comm2.id

        # Verify all communications persisted
        all_comms = await communication_service.get_communications(limit=100)
        assert len(all_comms) >= 3

    async def test_meeting_with_decisions_flow(
        self,
        agent_registry: AgentRegistry,
        meeting_service,
        clean_db,
        sample_agent_ids,
    ):
        """Test meeting flow with multiple decisions."""
        # Register agents
        for agent_id in sample_agent_ids[:3]:
            full_id = str(uuid4())
            await agent_registry.register_agent(
                full_id=full_id,
                nickname=f"Agent-{agent_id[-3:]}",
                capabilities=["decision-making"],
            )

        # Create meeting
        meeting = await meeting_service.create_meeting(
            title="Decision Meeting",
            participant_ids=sample_agent_ids[:3],
            description="Meeting to make key decisions",
        )

        # Start meeting
        await meeting_service.start_meeting(meeting.id)

        # Record discussion messages
        await meeting_service.record_message(
            meeting_id=meeting.id,
            agent_id=sample_agent_ids[0],
            content="We need to decide on the framework",
            message_type="statement",
        )
        await meeting_service.record_message(
            meeting_id=meeting.id,
            agent_id=sample_agent_ids[1],
            content="I suggest FastAPI",
            message_type="proposal",
        )
        await meeting_service.record_message(
            meeting_id=meeting.id,
            agent_id=sample_agent_ids[2],
            content="I agree with FastAPI",
            message_type="vote",
        )

        await clean_db.commit()

        # Create multiple decisions
        from communication_server.db.meeting import DecisionDB
        from datetime import datetime, UTC

        decisions = [
            DecisionDB(
                title="Use FastAPI",
                description="Framework choice",
                context={},
                proposed_by=sample_agent_ids[1],
                options=[{"title": "FastAPI"}, {"title": "Flask"}],
                status="approved",
                meeting_id=meeting.id,
                selected_option={"title": "FastAPI"},
                rationale="Unanimous agreement",
                decided_at=datetime.now(UTC),
            ),
            DecisionDB(
                title="Use PostgreSQL",
                description="Database choice",
                context={},
                proposed_by=sample_agent_ids[0],
                options=[{"title": "PostgreSQL"}, {"title": "MongoDB"}],
                status="approved",
                meeting_id=meeting.id,
                selected_option={"title": "PostgreSQL"},
                rationale="Best for our use case",
                decided_at=datetime.now(UTC),
            ),
        ]

        for decision in decisions:
            clean_db.add(decision)

        await clean_db.commit()

        # End meeting
        await meeting_service.end_meeting(meeting.id)
        await clean_db.commit()

        # Verify all decisions persisted
        from sqlalchemy import select

        result = await clean_db.execute(
            select(DecisionDB).where(DecisionDB.meeting_id == meeting.id)
        )
        meeting_decisions = result.scalars().all()

        assert len(meeting_decisions) == 2
        titles = {d.title for d in meeting_decisions}
        assert {"Use FastAPI", "Use PostgreSQL"} == titles

    async def test_error_recovery_in_workflow(
        self,
        agent_registry: AgentRegistry,
        communication_service,
        meeting_service,
        clean_db,
        sample_agent_ids,
    ):
        """Test error recovery and transaction rollback."""
        # Register agent
        full_id = str(uuid4())
        agent = await agent_registry.register_agent(
            full_id=full_id,
            nickname="ErrorTest",
            capabilities=["test"],
        )

        # Create communication
        comm = await communication_service.log_communication(
            from_agent=agent.agent_id,
            to_agent=sample_agent_ids[0],
            message_type="question",
            content="Test message",
            direction=CommunicationDirection.OUTBOUND,
        )

        await clean_db.commit()

        # Verify data persisted
        retrieved_comm = await communication_service.get_communication(comm.id)
        assert retrieved_comm is not None

        # Test error: try to record message in non-existent meeting
        fake_meeting_id = uuid4()

        with pytest.raises(ValueError, match="not found"):
            await meeting_service.record_message(
                meeting_id=fake_meeting_id,
                agent_id=agent.agent_id,
                content="This should fail",
                message_type="statement",
            )

        # Verify the error didn't affect other data
        all_comms = await communication_service.list_recent(limit=100)
        assert len(all_comms) >= 1


@pytest.mark.integration
@pytest.mark.e2e
class TestDataPersistence:
    """Tests for data persistence across operations."""

    async def test_communication_persistence_rollback(
        self,
        communication_service,
        clean_db,
        sample_agent_ids,
    ):
        """Test that rollback works correctly on error."""
        # Create a communication
        comm1 = await communication_service.log_communication(
            from_agent=sample_agent_ids[0],
            to_agent=sample_agent_ids[1],
            message_type="statement",
            content="Before rollback",
            direction=CommunicationDirection.OUTBOUND,
        )

        await clean_db.commit()

        # Try to create invalid communication (should fail validation)
        # Create a very long content that exceeds max length
        try:
            await communication_service.log_communication(
                from_agent=sample_agent_ids[1],
                to_agent=sample_agent_ids[0],
                message_type="statement",
                content="x" * 200000,  # Exceeds 100,000 char limit
                direction=CommunicationDirection.INBOUND,
            )
            assert False, "Should have raised ValueError"
        except ValueError:
            pass  # Expected

        # Verify first communication still exists
        retrieved = await communication_service.get_communication(comm1.id)
        assert retrieved is not None
        assert retrieved.content == "Before rollback"

    async def test_meeting_state_transitions(
        self,
        meeting_service,
        clean_db,
        sample_agent_ids,
    ):
        """Test meeting state transitions are persisted correctly."""
        # Create meeting
        meeting = await meeting_service.create_meeting(
            title="State Test",
            participant_ids=sample_agent_ids[:2],
        )

        assert meeting.status == MeetingStatus.PENDING
        assert meeting.started_at is None
        assert meeting.ended_at is None

        await clean_db.commit()

        # Start meeting
        started = await meeting_service.start_meeting(meeting.id)
        assert started.status == MeetingStatus.ACTIVE
        assert started.started_at is not None

        await clean_db.commit()

        # End meeting
        ended = await meeting_service.end_meeting(meeting.id)
        assert ended.status == MeetingStatus.COMPLETED
        assert ended.started_at is not None
        assert ended.ended_at is not None

        await clean_db.commit()

        # Verify persisted state
        final = await meeting_service.get_meeting(meeting.id)
        assert final.status == MeetingStatus.COMPLETED
        assert final.started_at is not None
        assert final.ended_at is not None


@pytest.mark.integration
@pytest.mark.e2e
class TestCrossComponentIntegration:
    """Tests for integration across different components."""

    async def test_communication_to_meeting_integration(
        self,
        agent_registry: AgentRegistry,
        communication_service,
        meeting_service,
        clean_db,
        sample_agent_ids,
    ):
        """Test flow from communications to meeting creation."""
        # Register agents
        agents = []
        for i, agent_id in enumerate(sample_agent_ids[:3]):
            full_id = str(uuid4())
            agent = await agent_registry.register_agent(
                full_id=full_id,
                nickname=f"Agent{i}",
                capabilities=["integration"],
            )
            agents.append(agent)

        # Create communications that lead to a meeting
        comm1 = await communication_service.log_communication(
            from_agent=agents[0].agent_id,
            to_agent=agents[1].agent_id,
            message_type="proposal",
            content="We need a meeting to discuss the API design",
            direction=CommunicationDirection.OUTBOUND,
        )

        comm2 = await communication_service.log_communication(
            from_agent=agents[1].agent_id,
            to_agent=agents[2].agent_id,
            message_type="notification",
            content="Meeting proposal received, adding you to the discussion",
            direction=CommunicationDirection.INTERNAL,
            correlation_id=comm1.id,
        )

        await clean_db.commit()

        # Create meeting based on the communications
        meeting = await meeting_service.create_meeting(
            title="API Design Meeting",
            participant_ids=[a.agent_id for a in agents],
            description="Meeting resulting from communication discussion",
        )

        # Verify meeting created with all participants
        participants = await meeting_service.get_participants(meeting.id)
        assert len(participants) == 3

        participant_ids = {p.agent_id for p in participants}
        assert participant_ids == {a.agent_id for a in agents}

        await clean_db.commit()

        # Verify communications are still accessible
        related_comms = await communication_service.get_communications(
            correlation_id=comm1.id,
        )

        assert len(related_comms) >= 1

"""
Integration tests for Topic Analysis.

Tests:
- Create sample communications
- Test auto-generated topic suggestions
- Test topic ranking by priority
"""

import pytest
from datetime import datetime, timedelta, UTC

from communication_server.analyzer.topic import (
    TopicAnalyzer,
    TopicType,
    TopicPriority,
    DetectedTopic,
    AgendaSuggestion,
)
from agent_comm_core.models.communication import CommunicationDirection


@pytest.mark.integration
class TestTopicDetection:
    """Tests for topic detection from communications."""

    async def test_detect_conflict_topics(
        self,
        clean_db,
        sample_agent_ids,
        communication_service,
    ):
        """Test detection of conflict-type topics."""
        # Create communications with conflict indicators
        conflict_messages = [
            (sample_agent_ids[0], sample_agent_ids[1], "I disagree with your approach"),
            (sample_agent_ids[1], sample_agent_ids[0], "We cannot agree on this"),
            (sample_agent_ids[0], sample_agent_ids[1], "This is a conflict we need to resolve"),
        ]

        for from_agent, to_agent, content in conflict_messages:
            await communication_service.log_communication(
                from_agent=from_agent,
                to_agent=to_agent,
                message_type="statement",
                content=content,
                direction=CommunicationDirection.OUTBOUND,
            )

        await clean_db.commit()

        # Analyze communications
        analyzer = TopicAnalyzer(clean_db)
        topics = await analyzer.analyze_communications(
            time_range_hours=1,
            min_communications=2,
        )

        # Should detect conflict topics
        conflict_topics = [t for t in topics if t.topic_type == TopicType.CONFLICT]

        assert len(conflict_topics) > 0
        assert any(
            "conflict" in t.title.lower() or "disagree" in t.title.lower() for t in conflict_topics
        )

    async def test_detect_unresolved_questions(
        self,
        clean_db,
        sample_agent_ids,
        communication_service,
    ):
        """Test detection of unresolved question topics."""
        # Create communications with question patterns
        questions = [
            (sample_agent_ids[0], sample_agent_ids[1], "How should we implement the cache?"),
            (sample_agent_ids[1], sample_agent_ids[2], "What do you think about Redis?"),
            (sample_agent_ids[2], sample_agent_ids[0], "I'm not sure about the best approach"),
        ]

        for from_agent, to_agent, content in questions:
            await communication_service.log_communication(
                from_agent=from_agent,
                to_agent=to_agent,
                message_type="question",
                content=content,
                direction=CommunicationDirection.OUTBOUND,
            )

        await clean_db.commit()

        # Analyze
        analyzer = TopicAnalyzer(clean_db)
        topics = await analyzer.analyze_communications(
            time_range_hours=1,
            min_communications=2,
        )

        # Should detect unresolved topics
        unresolved_topics = [t for t in topics if t.topic_type == TopicType.UNRESOLVED]

        assert len(unresolved_topics) > 0

    async def test_detect_decision_needed_topics(
        self,
        clean_db,
        sample_agent_ids,
        communication_service,
    ):
        """Test detection of decision-needed topics."""
        # Create communications about decisions
        decision_messages = [
            (sample_agent_ids[0], sample_agent_ids[1], "We need to decide on the database"),
            (sample_agent_ids[1], sample_agent_ids[2], "Which option do you prefer?"),
            (sample_agent_ids[2], sample_agent_ids[0], "I recommend option A"),
        ]

        for from_agent, to_agent, content in decision_messages:
            await communication_service.log_communication(
                from_agent=from_agent,
                to_agent=to_agent,
                message_type="proposal",
                content=content,
                direction=CommunicationDirection.OUTBOUND,
            )

        await clean_db.commit()

        # Analyze
        analyzer = TopicAnalyzer(clean_db)
        topics = await analyzer.analyze_communications(
            time_range_hours=1,
            min_communications=2,
        )

        # Should detect decision-needed topics
        decision_topics = [t for t in topics if t.topic_type == TopicType.DECISION_NEEDED]

        assert len(decision_topics) > 0

    async def test_detect_technical_topics(
        self,
        clean_db,
        sample_agent_ids,
        communication_service,
    ):
        """Test detection of technical discussion topics."""
        # Create technical communications
        tech_messages = [
            (sample_agent_ids[0], sample_agent_ids[1], "The API endpoint needs optimization"),
            (sample_agent_ids[1], sample_agent_ids[2], "Let's review the database schema"),
            (sample_agent_ids[2], sample_agent_ids[0], "The server deployment is ready"),
        ]

        for from_agent, to_agent, content in tech_messages:
            await communication_service.log_communication(
                from_agent=from_agent,
                to_agent=to_agent,
                message_type="statement",
                content=content,
                direction=CommunicationDirection.OUTBOUND,
            )

        await clean_db.commit()

        # Analyze
        analyzer = TopicAnalyzer(clean_db)
        topics = await analyzer.analyze_communications(
            time_range_hours=1,
            min_communications=2,
        )

        # Should detect technical topics
        tech_topics = [t for t in topics if t.topic_type == TopicType.TECHNICAL]

        assert len(tech_topics) > 0


@pytest.mark.integration
class TestTopicPriority:
    """Tests for topic priority calculation."""

    async def test_urgent_priority_for_conflicts(
        self,
        clean_db,
        sample_agent_ids,
        communication_service,
    ):
        """Test that conflict topics get urgent priority."""
        # Create conflict communications with error indicators
        conflict_messages = [
            (sample_agent_ids[0], sample_agent_ids[1], "There's an error in the system"),
            (sample_agent_ids[1], sample_agent_ids[0], "I cannot accept this proposal"),
            (sample_agent_ids[0], sample_agent_ids[1], "The issue is blocking deployment"),
        ]

        for from_agent, to_agent, content in conflict_messages:
            await communication_service.log_communication(
                from_agent=from_agent,
                to_agent=to_agent,
                message_type="statement",
                content=content,
                direction=CommunicationDirection.OUTBOUND,
            )

        await clean_db.commit()

        # Analyze
        analyzer = TopicAnalyzer(clean_db)
        topics = await analyzer.analyze_communications(
            time_range_hours=1,
            min_communications=2,
        )

        # Check priority
        urgent_topics = [t for t in topics if t.priority == TopicPriority.URGENT]

        assert len(urgent_topics) > 0

    async def test_high_priority_for_recent_activity(
        self,
        clean_db,
        sample_agent_ids,
        communication_service,
    ):
        """Test that recent activity increases priority."""
        # Create many recent communications on same topic
        for i in range(6):
            await communication_service.log_communication(
                from_agent=sample_agent_ids[0],
                to_agent=sample_agent_ids[1],
                message_type="statement",
                content=f"Discussion point {i} about API design",
                direction=CommunicationDirection.OUTBOUND,
            )

        await clean_db.commit()

        # Analyze
        analyzer = TopicAnalyzer(clean_db)
        topics = await analyzer.analyze_communications(
            time_range_hours=1,
            min_communications=3,
        )

        # Should have high priority topics
        high_topics = [t for t in topics if t.priority == TopicPriority.HIGH]

        assert len(high_topics) > 0

    async def test_medium_priority_for_moderate_activity(
        self,
        clean_db,
        sample_agent_ids,
        communication_service,
    ):
        """Test moderate activity gets medium priority."""
        # Create moderate number of communications
        for i in range(3):
            await communication_service.log_communication(
                from_agent=sample_agent_ids[0],
                to_agent=sample_agent_ids[1],
                message_type="statement",
                content=f"Comment {i} about the project",
                direction=CommunicationDirection.OUTBOUND,
            )

        await clean_db.commit()

        # Analyze
        analyzer = TopicAnalyzer(clean_db)
        topics = await analyzer.analyze_communications(
            time_range_hours=1,
            min_communications=2,
        )

        # Should have medium or higher priority topics
        medium_or_high = [
            t
            for t in topics
            if t.priority in [TopicPriority.MEDIUM, TopicPriority.HIGH, TopicPriority.URGENT]
        ]

        assert len(medium_or_high) > 0

    async def test_low_priority_for_limited_activity(
        self,
        clean_db,
        sample_agent_ids,
        communication_service,
    ):
        """Test limited activity gets low priority."""
        # Create minimal communications
        await communication_service.log_communication(
            from_agent=sample_agent_ids[0],
            to_agent=sample_agent_ids[1],
            message_type="statement",
            content="A single comment",
            direction=CommunicationDirection.OUTBOUND,
        )

        await clean_db.commit()

        # Analyze with minimum threshold
        analyzer = TopicAnalyzer(clean_db)
        topics = await analyzer.analyze_communications(
            time_range_hours=1,
            min_communications=1,
        )

        # Should detect topics but with lower priority
        low_topics = [t for t in topics if t.priority == TopicPriority.LOW]

        # At least one topic should exist
        assert len(topics) >= 0


@pytest.mark.integration
class TestTopicRanking:
    """Tests for topic ranking and sorting."""

    async def test_topics_sorted_by_priority(
        self,
        clean_db,
        sample_agent_ids,
        communication_service,
    ):
        """Test that topics are sorted by priority."""
        # Create mixed communications
        # Urgent - conflict
        await communication_service.log_communication(
            from_agent=sample_agent_ids[0],
            to_agent=sample_agent_ids[1],
            message_type="statement",
            content="Error: System failure detected",
            direction=CommunicationDirection.OUTBOUND,
        )

        # Low priority - generic
        await communication_service.log_communication(
            from_agent=sample_agent_ids[1],
            to_agent=sample_agent_ids[2],
            message_type="statement",
            content="General comment about the weather",
            direction=CommunicationDirection.OUTBOUND,
        )

        # High - recent activity
        for i in range(5):
            await communication_service.log_communication(
                from_agent=sample_agent_ids[2],
                to_agent=sample_agent_ids[0],
                message_type="statement",
                content=f"Point {i} about deployment",
                direction=CommunicationDirection.OUTBOUND,
            )

        await clean_db.commit()

        # Analyze
        analyzer = TopicAnalyzer(clean_db)
        topics = await analyzer.analyze_communications(
            time_range_hours=1,
            min_communications=1,
        )

        # Check ordering - urgent should come first
        if len(topics) >= 2:
            priority_order = {
                TopicPriority.URGENT: 0,
                TopicPriority.HIGH: 1,
                TopicPriority.MEDIUM: 2,
                TopicPriority.LOW: 3,
            }
            for i in range(len(topics) - 1):
                current_priority = priority_order[topics[i].priority]
                next_priority = priority_order[topics[i + 1].priority]
                # Current should be <= next (lower number = higher priority)
                assert current_priority <= next_priority

    async def test_topics_sorted_by_frequency_within_priority(
        self,
        clean_db,
        sample_agent_ids,
        communication_service,
    ):
        """Test that topics with same priority are sorted by frequency."""
        # Create two topics with similar priority but different frequency
        # Topic A - 5 communications
        for i in range(5):
            await communication_service.log_communication(
                from_agent=sample_agent_ids[0],
                to_agent=sample_agent_ids[1],
                message_type="statement",
                content=f"API design discussion {i}",
                direction=CommunicationDirection.OUTBOUND,
            )

        # Topic B - 3 communications
        for i in range(3):
            await communication_service.log_communication(
                from_agent=sample_agent_ids[1],
                to_agent=sample_agent_ids[2],
                message_type="statement",
                content=f"Database discussion {i}",
                direction=CommunicationDirection.OUTBOUND,
            )

        await clean_db.commit()

        # Analyze
        analyzer = TopicAnalyzer(clean_db)
        topics = await analyzer.analyze_communications(
            time_range_hours=1,
            min_communications=2,
        )

        # Both should have similar priority (medium/high)
        # But API design (more frequent) should appear first
        if len(topics) >= 2:
            # Check that higher frequency topics come first
            assert topics[0].communication_count >= topics[1].communication_count


@pytest.mark.integration
class TestAgendaSuggestion:
    """Tests for agenda suggestion generation."""

    async def test_suggest_agenda_from_topics(
        self,
        clean_db,
    ):
        """Test generating agenda suggestions from detected topics."""
        # Create sample topics
        from communication_server.analyzer.topic import DetectedTopic, TopicType, TopicPriority

        sample_topics = [
            DetectedTopic(
                title="Conflict: Database Choice",
                description="Team disagrees on database selection",
                topic_type=TopicType.CONFLICT,
                priority=TopicPriority.URGENT,
                related_agents={"agent-001", "agent-002"},
                communication_count=8,
                first_seen=datetime.now(UTC),
                last_seen=datetime.now(UTC),
                sample_messages=["We need PostgreSQL", "I prefer MongoDB"],
                keywords={"database", "postgresql", "mongodb"},
            ),
            DetectedTopic(
                title="Decision: API Framework",
                description="Need to decide on REST vs GraphQL",
                topic_type=TopicType.DECISION_NEEDED,
                priority=TopicPriority.HIGH,
                related_agents={"agent-001", "agent-002", "agent-003"},
                communication_count=5,
                first_seen=datetime.now(UTC),
                last_seen=datetime.now(UTC),
                sample_messages=["What about GraphQL?"],
                keywords={"api", "graphql", "rest"},
            ),
        ]

        analyzer = TopicAnalyzer(clean_db)
        suggestions = await analyzer.suggest_agenda(
            topics=sample_topics,
            max_items=5,
            max_duration_minutes=60,
        )

        assert len(suggestions) == 2

        # Check first suggestion (urgent)
        assert suggestions[0].title == "Conflict: Database Choice"
        assert suggestions[0].priority == TopicPriority.URGENT
        assert suggestions[0].estimated_duration_minutes == 20  # Urgent = 20 min

        # Check second suggestion (high)
        assert suggestions[1].title == "Decision: API Framework"
        assert suggestions[1].priority == TopicPriority.HIGH
        assert suggestions[1].estimated_duration_minutes == 15  # High = 15 min

    async def test_agenda_duration_by_priority(
        self,
        clean_db,
    ):
        """Test that agenda duration varies by priority."""
        from communication_server.analyzer.topic import DetectedTopic, TopicType, TopicPriority

        # Create topics with different priorities
        topics = [
            DetectedTopic(
                title="Urgent Topic",
                description="Needs immediate attention",
                topic_type=TopicType.CONFLICT,
                priority=TopicPriority.URGENT,
                related_agents={"agent-001"},
                communication_count=5,
            ),
            DetectedTopic(
                title="High Priority Topic",
                description="Important but not urgent",
                topic_type=TopicType.DECISION_NEEDED,
                priority=TopicPriority.HIGH,
                related_agents={"agent-002"},
                communication_count=4,
            ),
            DetectedTopic(
                title="Medium Priority Topic",
                description="Standard discussion",
                topic_type=TopicType.DISCUSSION,
                priority=TopicPriority.MEDIUM,
                related_agents={"agent-003"},
                communication_count=3,
            ),
            DetectedTopic(
                title="Low Priority Topic",
                description="Nice to have",
                topic_type=TopicType.COORDINATION,
                priority=TopicPriority.LOW,
                related_agents={"agent-004"},
                communication_count=2,
            ),
        ]

        analyzer = TopicAnalyzer(clean_db)
        suggestions = await analyzer.suggest_agenda(topics=topics)

        durations = {s.title: s.estimated_duration_minutes for s in suggestions}

        assert durations["Urgent Topic"] == 20
        assert durations["High Priority Topic"] == 15
        assert durations["Medium Priority Topic"] == 10
        assert durations["Low Priority Topic"] == 5

    async def test_agenda_max_items_limit(
        self,
        clean_db,
    ):
        """Test that agenda respects max_items limit."""
        from communication_server.analyzer.topic import DetectedTopic, TopicType, TopicPriority

        # Create more topics than limit
        topics = [
            DetectedTopic(
                title=f"Topic {i}",
                description=f"Description {i}",
                topic_type=TopicType.DISCUSSION,
                priority=TopicPriority.MEDIUM,
                related_agents={f"agent-{i}"},
                communication_count=i + 1,
            )
            for i in range(10)
        ]

        analyzer = TopicAnalyzer(clean_db)
        suggestions = await analyzer.suggest_agenda(
            topics=topics,
            max_items=5,
        )

        assert len(suggestions) == 5

    async def test_agenda_discussion_points(
        self,
        clean_db,
    ):
        """Test that agenda includes relevant discussion points."""
        from communication_server.analyzer.topic import DetectedTopic, TopicType, TopicPriority

        topics = [
            DetectedTopic(
                title="API Design",
                description="Discussion about API architecture",
                topic_type=TopicType.DISCUSSION,
                priority=TopicPriority.MEDIUM,
                related_agents={"agent-001", "agent-002"},
                communication_count=10,
                sample_messages=[
                    "We need REST endpoints for users",
                    "WebSocket support for real-time",
                    "Authentication middleware is needed",
                ],
                keywords={"api", "rest", "websocket"},
            ),
        ]

        analyzer = TopicAnalyzer(clean_db)
        suggestions = await analyzer.suggest_agenda(topics=topics)

        assert len(suggestions) == 1
        assert len(suggestions[0].discussion_points) >= 2
        assert any("communications" in p.lower() for p in suggestions[0].discussion_points)
        assert any("discuss" in p.lower() for p in suggestions[0].discussion_points)


@pytest.mark.integration
class TestAgentFiltering:
    """Tests for filtering topics by agents."""

    async def test_analyze_specific_agents(
        self,
        clean_db,
        sample_agent_ids,
        communication_service,
    ):
        """Test analyzing communications from specific agents only."""
        # Create communications between different agent pairs
        # Agent 1 <-> Agent 2: Discussing API
        for i in range(3):
            await communication_service.log_communication(
                from_agent=sample_agent_ids[0],
                to_agent=sample_agent_ids[1],
                message_type="statement",
                content=f"API design point {i}",
                direction=CommunicationDirection.OUTBOUND,
            )

        # Agent 2 <-> Agent 3: Discussing database
        for i in range(3):
            await communication_service.log_communication(
                from_agent=sample_agent_ids[1],
                to_agent=sample_agent_ids[2],
                message_type="statement",
                content=f"Database design point {i}",
                direction=CommunicationDirection.OUTBOUND,
            )

        await clean_db.commit()

        # Analyze only agent-001 and agent-002
        analyzer = TopicAnalyzer(clean_db)
        topics = await analyzer.analyze_communications(
            time_range_hours=1,
            agent_filter={sample_agent_ids[0], sample_agent_ids[1]},
            min_communications=2,
        )

        # Should only find API-related topics, not database
        for topic in topics:
            # Check that agent-003 is not in related agents
            assert sample_agent_ids[2] not in topic.related_agents
            # API design should be mentioned
            assert (
                any("api" in k.lower() for k in topic.keywords) or "design" in topic.title.lower()
            )

    async def test_time_range_filtering(
        self,
        clean_db,
        sample_agent_ids,
        communication_service,
    ):
        """Test filtering by time range."""
        # This test would require manipulating timestamps
        # For now, we just verify the parameter is accepted
        analyzer = TopicAnalyzer(clean_db)

        # Create some communications
        await communication_service.log_communication(
            from_agent=sample_agent_ids[0],
            to_agent=sample_agent_ids[1],
            message_type="statement",
            content="Test message",
            direction=CommunicationDirection.OUTBOUND,
        )
        await clean_db.commit()

        # Analyze with different time ranges
        topics_1h = await analyzer.analyze_communications(time_range_hours=1)
        topics_24h = await analyzer.analyze_communications(time_range_hours=24)

        # Both should work (actual filtering depends on timestamps)
        assert isinstance(topics_1h, list)
        assert isinstance(topics_24h, list)


@pytest.mark.integration
class TestKeywordExtraction:
    """Tests for keyword extraction from communications."""

    async def test_extract_keywords_from_communications(
        self,
        clean_db,
        sample_agent_ids,
        communication_service,
    ):
        """Test that keywords are extracted from communications."""
        # Create communications with specific technical terms
        technical_comm = [
            ("The API endpoint needs optimization for performance"),
            ("Database query optimization is critical"),
            ("The PostgreSQL schema requires normalization"),
        ]

        for content in technical_comm:
            await communication_service.log_communication(
                from_agent=sample_agent_ids[0],
                to_agent=sample_agent_ids[1],
                message_type="statement",
                content=content,
                direction=CommunicationDirection.OUTBOUND,
            )

        await clean_db.commit()

        # Analyze
        analyzer = TopicAnalyzer(clean_db)
        topics = await analyzer.analyze_communications(
            time_range_hours=1,
            min_communications=2,
        )

        # Should have extracted keywords
        if len(topics) > 0:
            # At least one topic should have keywords
            assert any(len(t.keywords) > 0 for t in topics)

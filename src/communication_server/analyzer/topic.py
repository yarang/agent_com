"""
Topic analyzer for auto-generated meeting agendas.

Analyzes communication logs to detect conflicts, unresolved questions,
and ranks topics by priority for meeting agenda suggestions.
"""

import asyncio
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_comm_core.models.communication import CommunicationDirection
from communication_server.db.communication import CommunicationDB


class TopicType(str, Enum):
    """Type of topic detected."""

    CONFLICT = "conflict"
    UNRESOLVED = "unresolved"
    DECISION_NEEDED = "decision_needed"
    DISCUSSION = "discussion"
    TECHNICAL = "technical"
    COORDINATION = "coordination"


class TopicPriority(str, Enum):
    """Priority level for a topic."""

    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class DetectedTopic:
    """A topic detected from communication analysis."""

    title: str
    description: str
    topic_type: TopicType
    priority: TopicPriority
    related_agents: set[str] = field(default_factory=set)
    communication_count: int = 0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    sample_messages: list[str] = field(default_factory=list)
    keywords: set[str] = field(default_factory=set)


@dataclass
class AgendaSuggestion:
    """A suggested agenda item for a meeting."""

    title: str
    description: str
    estimated_duration_minutes: int
    priority: TopicPriority
    discussion_points: list[str]
    participants: list[str]


class TopicAnalyzer:
    """
    Analyzer for detecting topics from communication logs.

    Analyzes patterns in communications to:
    - Detect conflicts and disagreements
    - Identify unresolved questions
    - Find topics requiring decisions
    - Rank topics by frequency and urgency
    - Generate meeting agenda suggestions
    """

    # Patterns for detecting different topic types
    CONFLICT_PATTERNS = [
        r"disagree|disagreement|conflict|dispute|cannot agree",
        r"reject|refuse|won't|will not|cannot",
        r"\bno\b.*\baccept\b|\bno\b.*\bagree\b",
        r"issue|problem|error|failure",
    ]

    UNRESOLVED_PATTERNS = [
        r"\?$",
        r"how to|how do|how should|what do|what should",
        r"need help|need advice|stuck|blocked",
        r"unclear|unsure|don't know|not sure",
        r"todo|fixme|hack|temporary",
    ]

    DECISION_PATTERNS = [
        r"decide|decision|choose|option|alternative",
        r"should we|which one|prefer|recommendation",
        r"proposal|suggest|recommend|advise",
        r"approve|deny|reject|accept",
    ]

    TECHNICAL_PATTERNS = [
        r"\bapi\b|\bendpoint\b|\bservice\b|\bserver\b",
        r"\bdatabase\b|\bquery\b|\bschema\b",
        r"\bbug\b|\bfix\b|\bpatch\b",
        r"\bdeploy\b|\brelease\b|\bversion\b",
    ]

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the topic analyzer.

        Args:
            session: Database async session
        """
        self._session = session
        self._compiled_patterns = {
            TopicType.CONFLICT: [re.compile(p, re.IGNORECASE) for p in self.CONFLICT_PATTERNS],
            TopicType.UNRESOLVED: [re.compile(p, re.IGNORECASE) for p in self.UNRESOLVED_PATTERNS],
            TopicType.DECISION_NEEDED: [
                re.compile(p, re.IGNORECASE) for p in self.DECISION_PATTERNS
            ],
            TopicType.TECHNICAL: [re.compile(p, re.IGNORECASE) for p in self.TECHNICAL_PATTERNS],
        }

    async def analyze_communications(
        self,
        time_range_hours: int = 24,
        agent_filter: Optional[set[str]] = None,
        min_communications: int = 3,
    ) -> list[DetectedTopic]:
        """
        Analyze recent communications to detect topics.

        Args:
            time_range_hours: Time range to analyze (default: 24 hours)
            agent_filter: Optional set of agent IDs to filter by
            min_communications: Minimum communications to consider a topic

        Returns:
            List of detected topics sorted by priority
        """
        # Get communications in time range
        since = datetime.utcnow() - timedelta(hours=time_range_hours)

        query = select(CommunicationDB).where(CommunicationDB.created_at >= since)

        if agent_filter:
            # Filter by agent IDs
            from sqlalchemy import or_

            agent_conditions = [
                (CommunicationDB.from_agent == agent_id) | (CommunicationDB.to_agent == agent_id)
                for agent_id in agent_filter
            ]
            query = query.where(or_(*agent_conditions))

        query = query.order_by(CommunicationDB.created_at.desc())

        result = await self._session.execute(query)
        communications = result.scalars().all()

        # Analyze communications for topics
        topic_groups: dict[str, list[CommunicationDB]] = {}

        for comm in communications:
            # Detect topic type and extract keywords
            topic_type = self._detect_topic_type(comm.content)
            keywords = self._extract_keywords(comm.content)

            # Create a topic key from keywords
            if keywords:
                topic_key = "-".join(sorted(keywords)[:3])  # Use top 3 keywords
            else:
                topic_key = topic_type.value

            if topic_key not in topic_groups:
                topic_groups[topic_key] = []
            topic_groups[topic_key].append(comm)

        # Convert to detected topics
        detected_topics = []

        for topic_key, comms in topic_groups.items():
            if len(comms) < min_communications:
                continue

            # Determine topic type from most common
            first_comm = comms[0]
            topic_type = self._detect_topic_type(first_comm.content)

            # Calculate priority
            priority = self._calculate_priority(comms)

            # Get related agents
            related_agents = set()
            for comm in comms:
                related_agents.add(comm.from_agent)
                related_agents.add(comm.to_agent)

            # Get sample messages
            sample_messages = [comm.content[:200] for comm in comms[:3]]

            # Extract keywords from first communication
            keywords = set(self._extract_keywords(first_comm.content))

            detected_topics.append(
                DetectedTopic(
                    title=self._generate_title(topic_key, topic_type),
                    description=self._generate_description(comms),
                    topic_type=topic_type,
                    priority=priority,
                    related_agents=related_agents,
                    communication_count=len(comms),
                    first_seen=min(comm.created_at for comm in comms),
                    last_seen=max(comm.created_at for comm in comms),
                    sample_messages=sample_messages,
                    keywords=keywords,
                )
            )

        # Sort by priority and frequency
        priority_order = {
            TopicPriority.URGENT: 0,
            TopicPriority.HIGH: 1,
            TopicPriority.MEDIUM: 2,
            TopicPriority.LOW: 3,
        }

        detected_topics.sort(key=lambda t: (priority_order[t.priority], -t.communication_count))

        return detected_topics

    def _detect_topic_type(self, content: str) -> TopicType:
        """
        Detect the type of topic from content.

        Args:
            content: Communication content

        Returns:
            Detected topic type
        """
        content_lower = content.lower()

        # Check conflict patterns first (highest priority)
        for pattern in self._compiled_patterns[TopicType.CONFLICT]:
            if pattern.search(content):
                return TopicType.CONFLICT

        # Check decision patterns
        for pattern in self._compiled_patterns[TopicType.DECISION_NEEDED]:
            if pattern.search(content):
                return TopicType.DECISION_NEEDED

        # Check unresolved patterns
        for pattern in self._compiled_patterns[TopicType.UNRESOLVED]:
            if pattern.search(content):
                return TopicType.UNRESOLVED

        # Check technical patterns
        for pattern in self._compiled_patterns[TopicType.TECHNICAL]:
            if pattern.search(content):
                return TopicType.TECHNICAL

        # Default to discussion
        return TopicType.DISCUSSION

    def _extract_keywords(self, content: str) -> list[str]:
        """
        Extract important keywords from content.

        Args:
            content: Communication content

        Returns:
            List of keywords
        """
        # Simple keyword extraction: find words that are capitalized
        # or appear to be technical terms
        words = re.findall(r"\b[a-zA-Z]{4,}\b", content)

        # Filter out common words
        stop_words = {
            "that",
            "this",
            "with",
            "from",
            "have",
            "been",
            "were",
            "they",
            "their",
            "what",
            "when",
            "where",
            "will",
            "would",
            "could",
            "should",
            "about",
            "after",
            "before",
            "because",
            "through",
        }

        keywords = [w.lower() for w in words if w.lower() not in stop_words and len(w) >= 4]

        # Get most common
        word_counts = Counter(keywords)
        return [w for w, _ in word_counts.most_common(5)]

    def _calculate_priority(self, communications: list[CommunicationDB]) -> TopicPriority:
        """
        Calculate priority based on communication patterns.

        Args:
            communications: List of related communications

        Returns:
            Calculated priority
        """
        now = datetime.utcnow()
        recent_count = sum(1 for c in communications if (now - c.created_at).total_seconds() < 3600)
        total_count = len(communications)

        # Check for conflict indicators
        has_conflict = any(
            self._detect_topic_type(c.content) == TopicType.CONFLICT for c in communications
        )

        # Check for error indicators
        has_errors = any("error" in c.content.lower() for c in communications)

        # Calculate priority
        if has_conflict or has_errors:
            return TopicPriority.URGENT
        elif recent_count >= 5:
            return TopicPriority.HIGH
        elif total_count >= 10 or recent_count >= 2:
            return TopicPriority.MEDIUM
        else:
            return TopicPriority.LOW

    def _generate_title(self, topic_key: str, topic_type: TopicType) -> str:
        """
        Generate a title for a topic.

        Args:
            topic_key: Topic key
            topic_type: Topic type

        Returns:
            Generated title
        """
        prefix = topic_type.value.replace("_", " ").title()
        words = topic_key.replace("-", " ").split()

        if words:
            return f"{prefix}: {' '.join(words[:3]).title()}"
        return f"{prefix} Discussion"

    def _generate_description(self, communications: list[CommunicationDB]) -> str:
        """
        Generate a description for a topic.

        Args:
            communications: Related communications

        Returns:
            Generated description
        """
        # Get a summary from the most recent communication
        if not communications:
            return "No details available."

        latest = communications[0]
        return latest.content[:200] + ("..." if len(latest.content) > 200 else "")

    async def suggest_agenda(
        self,
        topics: Optional[list[DetectedTopic]] = None,
        max_items: int = 5,
        max_duration_minutes: int = 60,
    ) -> list[AgendaSuggestion]:
        """
        Generate meeting agenda suggestions from detected topics.

        Args:
            topics: Optional list of topics (will analyze if not provided)
            max_items: Maximum number of agenda items
            max_duration_minutes: Maximum meeting duration

        Returns:
            List of agenda suggestions
        """
        if topics is None:
            topics = await self.analyze_communications()

        agenda_items = []

        for topic in topics[:max_items]:
            # Calculate duration based on priority and complexity
            base_duration = {
                TopicPriority.URGENT: 20,
                TopicPriority.HIGH: 15,
                TopicPriority.MEDIUM: 10,
                TopicPriority.LOW: 5,
            }
            duration = base_duration.get(topic.priority, 10)

            # Generate discussion points
            discussion_points = [
                f"Review {topic.communication_count} related communications",
                f"Address {topic.topic_type.value.replace('_', ' ')}",
            ]

            if topic.sample_messages:
                discussion_points.append(f"Discuss: {topic.sample_messages[0][:100]}...")

            agenda_items.append(
                AgendaSuggestion(
                    title=topic.title,
                    description=topic.description,
                    estimated_duration_minutes=duration,
                    priority=topic.priority,
                    discussion_points=discussion_points,
                    participants=list(topic.related_agents),
                )
            )

        return agenda_items

"""
Statistics Service for agent and system-wide metrics.

Calculates and aggregates statistics from communications,
meetings, and decisions.
"""

from collections import Counter
from datetime import datetime, timedelta
from typing import Optional

from agent_comm_core.models.status import (
    ActivityPatterns,
    AgentStats,
    MessageEvent,
    SystemStats,
)
from agent_comm_core.repositories.base import CommunicationRepository, MeetingRepository


class StatisticsService:
    """
    Service for calculating agent and system statistics.

    Aggregates data from communications and meetings to provide
    insights into agent activity and system usage patterns.
    """

    def __init__(
        self,
        communication_repo: CommunicationRepository,
        meeting_repo: MeetingRepository,
    ) -> None:
        """
        Initialize the statistics service.

        Args:
            communication_repo: Repository for communication data
            meeting_repo: Repository for meeting data
        """
        self._communication_repo = communication_repo
        self._meeting_repo = meeting_repo

    async def get_agent_stats(self, agent_full_id: str) -> AgentStats:
        """
        Get statistics for a specific agent.

        Args:
            agent_full_id: Full UUID of the agent

        Returns:
            Agent statistics
        """
        from agent_comm_core.models.status import format_agent_display_id

        display_id = format_agent_display_id(agent_full_id, "Agent")

        # Get messages sent by agent
        sent_messages = await self._communication_repo.get_by_agents(
            from_agent=agent_full_id, limit=10000
        )

        # Get messages received by agent
        received_messages = await self._communication_repo.get_by_agents(
            to_agent=agent_full_id, limit=10000
        )

        # Get meetings where agent participated
        all_meetings = await self._meeting_repo.list_all(limit=10000)
        meetings_created = 0
        meetings_participated = 0

        for meeting in all_meetings:
            participants = await self._meeting_repo.get_participants(meeting.id)
            agent_participant = any(p.agent_id == agent_full_id for p in participants)

            if agent_participant:
                meetings_participated += 1
                # Check if agent created the meeting (first participant)
                if participants and participants[0].agent_id == agent_full_id:
                    meetings_created += 1

        # Calculate last activity
        last_activity = None
        all_activity = sent_messages + received_messages
        if all_activity:
            last_activity = max(msg.created_at for msg in all_activity)

        return AgentStats(
            agent_id=display_id,
            messages_sent=len(sent_messages),
            messages_received=len(received_messages),
            meetings_created=meetings_created,
            meetings_participated=meetings_participated,
            decisions_proposed=0,  # TODO: Implement when decision tracking is ready
            last_activity=last_activity,
        )

    async def get_system_stats(self) -> SystemStats:
        """
        Get system-wide statistics.

        Returns:
            System statistics
        """
        from communication_server.services.agent_registry import get_agent_registry

        registry = get_agent_registry()
        agents = await registry.get_all_agents()
        agent_counts = await registry.get_agent_count()

        # Count total messages
        all_messages = await self._communication_repo.list_all(limit=100000)
        total_messages = len(all_messages)

        # Count meetings by status
        all_meetings = await self._meeting_repo.list_all(limit=10000)
        total_meetings = len(all_meetings)
        active_meetings = sum(1 for m in all_meetings if m.status == "active")

        # Count decisions
        decisions_made = 0
        pending_decisions = 0
        for meeting in all_meetings:
            # TODO: Implement when decision tracking is ready
            pass

        return SystemStats(
            total_agents=agent_counts.get("total", 0),
            active_agents=agent_counts.get("online", 0) + agent_counts.get("active", 0),
            total_messages=total_messages,
            total_meetings=total_meetings,
            active_meetings=active_meetings,
            decisions_made=decisions_made,
            pending_decisions=pending_decisions,
        )

    async def get_activity_patterns(self, agent_full_id: Optional[str] = None) -> ActivityPatterns:
        """
        Get activity patterns by hour and day.

        Args:
            agent_full_id: Optional agent ID to filter by

        Returns:
            Activity patterns
        """
        # Get recent communications
        if agent_full_id:
            communications = await self._communication_repo.get_by_agents(
                from_agent=agent_full_id, limit=1000
            )
        else:
            communications = await self._communication_repo.list_all(limit=1000)

        # Initialize activity counters
        activity_by_hour = [0] * 24
        activity_by_day = {
            "Monday": 0,
            "Tuesday": 0,
            "Wednesday": 0,
            "Thursday": 0,
            "Friday": 0,
            "Saturday": 0,
            "Sunday": 0,
        }

        day_names = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]

        for comm in communications:
            # Count by hour
            activity_by_hour[comm.created_at.hour] += 1

            # Count by day
            day_name = day_names[comm.created_at.weekday()]
            activity_by_day[day_name] += 1

        # Get top agents by message count
        all_communications = await self._communication_repo.list_all(limit=10000)
        agent_message_counts = Counter(comm.from_agent for comm in all_communications)
        top_agents = [
            {"agent_id": agent_id, "message_count": count}
            for agent_id, count in agent_message_counts.most_common(10)
        ]

        # Get recent events
        recent_events = await self.get_message_timeline(limit=20)

        return ActivityPatterns(
            activity_by_hour=activity_by_hour,
            activity_by_day=activity_by_day,
            top_agents=top_agents,
            recent_events=recent_events,
        )

    async def get_message_timeline(self, limit: int = 100) -> list[MessageEvent]:
        """
        Get recent message events for timeline view.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of message events
        """
        # Get recent communications
        communications = await self._communication_repo.list_all(limit=limit)

        # Get recent meetings
        meetings = await self._meeting_repo.list_all(limit=limit)

        # Create events from communications
        events = []
        for comm in communications:
            event = MessageEvent(
                timestamp=comm.created_at,
                from_agent=comm.from_agent,
                to_agent=comm.to_agent,
                event_type="message",
                description=f"{comm.message_type}: {comm.content[:100]}...",
                metadata={"direction": comm.direction, "message_type": comm.message_type},
            )
            events.append(event)

        # Create events from meetings
        for meeting in meetings:
            event = MessageEvent(
                timestamp=meeting.created_at,
                from_agent="system",
                event_type="meeting",
                description=f"Meeting '{meeting.title}' - {meeting.status}",
                metadata={
                    "meeting_id": str(meeting.id),
                    "status": meeting.status,
                    "title": meeting.title,
                },
            )
            events.append(event)

        # Sort by timestamp descending
        events.sort(key=lambda e: e.timestamp, reverse=True)

        return events[:limit]

    async def get_agent_activity_summary(self, agent_full_id: str, days: int = 7) -> dict:
        """
        Get activity summary for an agent over a period.

        Args:
            agent_full_id: Full UUID of the agent
            days: Number of days to look back

        Returns:
            Activity summary with daily breakdown
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Get all agent communications
        sent_messages = await self._communication_repo.get_by_agents(
            from_agent=agent_full_id, limit=10000
        )
        received_messages = await self._communication_repo.get_by_agents(
            to_agent=agent_full_id, limit=10000
        )

        # Filter by date
        recent_sent = [m for m in sent_messages if m.created_at >= cutoff_date]
        recent_received = [m for m in received_messages if m.created_at >= cutoff_date]

        # Group by day
        daily_breakdown = {}
        for msg in recent_sent + recent_received:
            day_key = msg.created_at.strftime("%Y-%m-%d")
            if day_key not in daily_breakdown:
                daily_breakdown[day_key] = {"sent": 0, "received": 0}

            if msg.from_agent == agent_full_id:
                daily_breakdown[day_key]["sent"] += 1
            else:
                daily_breakdown[day_key]["received"] += 1

        return {
            "agent_id": agent_full_id,
            "period_days": days,
            "total_sent": len(recent_sent),
            "total_received": len(recent_received),
            "daily_breakdown": daily_breakdown,
        }


# Global service instance
_statistics_service: Optional[StatisticsService] = None


def get_statistics_service(
    communication_repo: CommunicationRepository,
    meeting_repo: MeetingRepository,
) -> StatisticsService:
    """
    Get or create the statistics service instance.

    Args:
        communication_repo: Repository for communication data
        meeting_repo: Repository for meeting data

    Returns:
        The StatisticsService instance
    """
    global _statistics_service
    if _statistics_service is None:
        _statistics_service = StatisticsService(communication_repo, meeting_repo)
    return _statistics_service

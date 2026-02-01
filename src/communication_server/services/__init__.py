"""
Services for Communication Server.

Provides business logic services for agent registry,
statistics, and other functionality.
"""

from communication_server.services.agent_registry import (
    AgentRegistry,
    get_agent_registry,
)
from communication_server.services.statistics import (
    StatisticsService,
    get_statistics_service,
)

__all__ = [
    "AgentRegistry",
    "get_agent_registry",
    "StatisticsService",
    "get_statistics_service",
]

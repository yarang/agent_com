"""
WebSocket support for real-time meeting communication.

Provides connection management and message handling for
agent meetings and discussions.
"""

from communication_server.websocket.handler import WebSocketHandler
from communication_server.websocket.manager import ConnectionManager

__all__ = ["ConnectionManager", "WebSocketHandler"]

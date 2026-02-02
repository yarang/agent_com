"""
HTTP Client for Communication Server integration.

This module provides an async HTTP client for communicating with
the Communication Server REST API.
"""

from typing import Any
from uuid import UUID

import httpx
from pydantic import BaseModel

from agent_comm_core.models.communication import Communication, CommunicationCreate
from agent_comm_core.models.decision import Decision
from agent_comm_core.models.meeting import Meeting, MeetingCreate
from mcp_broker.core.config import get_config
from mcp_broker.core.logging import get_logger

logger = get_logger(__name__)


class CommunicationServerAPIError(Exception):
    """Base exception for Communication Server API errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_data: dict[str, Any] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(self.message)


class AuthenticationError(CommunicationServerAPIError):
    """Exception raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed: Invalid agent token"):
        super().__init__(message, status_code=401)


class HTTPClient:
    """
    Async HTTP client for Communication Server.

    Provides methods to interact with the Communication Server REST API
    for logging communications, managing meetings, and retrieving decisions.

    Attributes:
        base_url: Base URL of the Communication Server
        agent_token: API token for authentication
        agent_nickname: Agent's display nickname
        client: httpx async client instance
        timeout: Request timeout in seconds
    """

    def __init__(
        self,
        base_url: str | None = None,
        agent_token: str = "",
        agent_nickname: str = "AnonymousAgent",
        timeout: float = 30.0,
    ) -> None:
        """Initialize the HTTP client.

        Args:
            base_url: Base URL of the Communication Server
                      (defaults to COMMUNICATION_SERVER_URL env var or http://localhost:8000)
            agent_token: API token for authentication (defaults to AGENT_TOKEN env var)
            agent_nickname: Agent's display nickname (defaults to AGENT_NICKNAME env var)
            timeout: Request timeout in seconds
        """
        import os

        config = get_config()

        # Get base URL from parameter, env var, or default
        if base_url is None:
            base_url = os.getenv("COMMUNICATION_SERVER_URL", "http://localhost:8000")

        # Get agent token from parameter, env var, or config
        if not agent_token:
            agent_token = config.authentication.api_token.value or os.getenv("AGENT_TOKEN", "")

        # Get agent nickname from parameter, env var, or config
        if agent_nickname == "AnonymousAgent":
            agent_nickname = config.agent.nickname or os.getenv("AGENT_NICKNAME", "AnonymousAgent")

        # Ensure base_url doesn't have trailing slash
        self.base_url = base_url.rstrip("/")

        self.agent_token = agent_token
        self.agent_nickname = agent_nickname
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

        logger.info(
            "HTTPClient initialized",
            extra={
                "context": {
                    "base_url": self.base_url,
                    "agent_nickname": agent_nickname,
                    "timeout": timeout,
                }
            },
        )

    async def __aenter__(self) -> "HTTPClient":
        """Enter context manager and initialize client.

        Returns:
            The HTTPClient instance
        """
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager and close client.

        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Exception traceback
        """
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        """Get the HTTP client, initializing if necessary.

        Returns:
            The httpx AsyncClient instance

        Raises:
            RuntimeError: If client is not initialized (use async context manager)
        """
        if self._client is None:
            raise RuntimeError(
                "HTTPClient not initialized. Use 'async with HTTPClient()' or "
                "call 'ensure_client()' first."
            )
        return self._client

    async def ensure_client(self) -> httpx.AsyncClient:
        """Ensure the HTTP client is initialized.

        Returns:
            The httpx AsyncClient instance
        """
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            )
        return self._client

    def _handle_error(self, response: httpx.Response) -> None:
        """Handle HTTP error response.

        Args:
            response: The HTTP response

        Raises:
            CommunicationServerAPIError: If response indicates an error
            AuthenticationError: If response is 401 Unauthorized
        """
        try:
            error_data = response.json()
        except Exception:
            error_data = {}

        if response.status_code == 401:
            raise AuthenticationError(
                message=error_data.get("detail", "Authentication failed: Invalid agent token")
            )

        raise CommunicationServerAPIError(
            message=f"Communication Server error: {response.status_code}",
            status_code=response.status_code,
            response_data=error_data,
        )

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a GET request.

        Args:
            path: API path (without base URL)
            params: Query parameters

        Returns:
            Response JSON as dictionary

        Raises:
            CommunicationServerAPIError: If request fails
            AuthenticationError: If authentication fails
        """
        client = await self.ensure_client()
        url = f"{self.base_url}{path}"

        # Build headers with agent token
        headers = {"Content-Type": "application/json"}
        if self.agent_token:
            headers["X-Agent-Token"] = self.agent_token

        logger.debug(f"GET request to {url}", extra={"context": {"params": params}})

        try:
            response = await client.get(path, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            self._handle_error(e.response)
        except httpx.RequestError as e:
            raise CommunicationServerAPIError(f"Request failed: {e}")

    async def _post(self, path: str, data: dict[str, Any] | BaseModel) -> dict[str, Any]:
        """Make a POST request.

        Args:
            path: API path (without base URL)
            data: Request body (dict or Pydantic model)

        Returns:
            Response JSON as dictionary

        Raises:
            CommunicationServerAPIError: If request fails
            AuthenticationError: If authentication fails
        """
        client = await self.ensure_client()

        # Convert Pydantic model to dict if necessary
        if isinstance(data, BaseModel):
            json_data = data.model_dump(mode="json")
        else:
            json_data = data

        # Build headers with agent token
        headers = {"Content-Type": "application/json"}
        if self.agent_token:
            headers["X-Agent-Token"] = self.agent_token

        logger.debug(f"POST request to {path}", extra={"context": {"data": json_data}})

        try:
            response = await client.post(path, json=json_data, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            self._handle_error(e.response)
        except httpx.RequestError as e:
            raise CommunicationServerAPIError(f"Request failed: {e}")

    # Communication methods

    async def log_communication(self, communication: CommunicationCreate) -> Communication:
        """Log a communication between agents.

        Args:
            communication: Communication data to log

        Returns:
            The created Communication record

        Raises:
            CommunicationServerAPIError: If request fails
        """
        result = await self._post("/api/v1/communications", communication)
        return Communication(**result)

    async def get_communications(
        self,
        from_agent: str | None = None,
        to_agent: str | None = None,
        correlation_id: UUID | None = None,
        limit: int = 100,
    ) -> list[Communication]:
        """Query communications with optional filters.

        Args:
            from_agent: Optional source agent filter
            to_agent: Optional target agent filter
            correlation_id: Optional correlation ID filter
            limit: Maximum number of results

        Returns:
            List of Communication records

        Raises:
            CommunicationServerAPIError: If request fails
        """
        params: dict[str, Any] = {"limit": limit}
        if from_agent:
            params["from_agent"] = from_agent
        if to_agent:
            params["to_agent"] = to_agent
        if correlation_id:
            params["correlation_id"] = str(correlation_id)

        result = await self._get("/api/v1/communications", params=params)
        return [Communication(**c) for c in result]

    # Meeting methods

    async def create_meeting(self, meeting: MeetingCreate) -> Meeting:
        """Create a new meeting.

        Args:
            meeting: Meeting creation data

        Returns:
            The created Meeting record

        Raises:
            CommunicationServerAPIError: If request fails
        """
        result = await self._post("/api/v1/meetings", meeting)
        return Meeting(**result)

    async def get_meeting(self, meeting_id: UUID) -> Meeting | None:
        """Get a meeting by ID.

        Args:
            meeting_id: Meeting UUID

        Returns:
            The Meeting record or None if not found

        Raises:
            CommunicationServerAPIError: If request fails
        """
        try:
            result = await self._get(f"/api/v1/meetings/{meeting_id}")
            return Meeting(**result)
        except CommunicationServerAPIError as e:
            if e.status_code == 404:
                return None
            raise

    async def list_meetings(
        self,
        status: str | None = None,
        limit: int = 100,
    ) -> list[Meeting]:
        """List meetings with optional filters.

        Args:
            status: Optional status filter
            limit: Maximum number of results

        Returns:
            List of Meeting records

        Raises:
            CommunicationServerAPIError: If request fails
        """
        params: dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status

        result = await self._get("/api/v1/meetings", params=params)
        return [Meeting(**m) for m in result]

    async def start_meeting(self, meeting_id: UUID) -> Meeting | None:
        """Start a meeting.

        Args:
            meeting_id: Meeting UUID

        Returns:
            The updated Meeting record

        Raises:
            CommunicationServerAPIError: If request fails
        """
        result = await self._post(f"/api/v1/meetings/{meeting_id}/start", {})
        return Meeting(**result)

    async def end_meeting(self, meeting_id: UUID) -> Meeting | None:
        """End a meeting.

        Args:
            meeting_id: Meeting UUID

        Returns:
            The updated Meeting record

        Raises:
            CommunicationServerAPIError: If request fails
        """
        result = await self._post(f"/api/v1/meetings/{meeting_id}/end", {})
        return Meeting(**result)

    async def add_meeting_participant(
        self,
        meeting_id: UUID,
        agent_id: str,
        role: str = "participant",
    ) -> dict[str, Any]:
        """Add a participant to a meeting.

        Args:
            meeting_id: Meeting UUID
            agent_id: Agent identifier
            role: Participant role

        Returns:
            The created participant record

        Raises:
            CommunicationServerAPIError: If request fails
        """
        params = {"agent_id": agent_id, "role": role}
        result = await self._post(f"/api/v1/meetings/{meeting_id}/participants", params)
        return result

    async def get_meeting_messages(
        self,
        meeting_id: UUID,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get messages from a meeting.

        Args:
            meeting_id: Meeting UUID
            limit: Maximum number of results

        Returns:
            List of meeting messages

        Raises:
            CommunicationServerAPIError: If request fails
        """
        params = {"limit": limit}
        result = await self._get(f"/api/v1/meetings/{meeting_id}/messages", params=params)
        return result

    async def record_meeting_message(
        self,
        meeting_id: UUID,
        agent_id: str,
        content: str,
        message_type: str = "statement",
    ) -> dict[str, Any]:
        """Record a message in a meeting.

        Args:
            meeting_id: Meeting UUID
            agent_id: Agent identifier
            content: Message content
            message_type: Type of message

        Returns:
            The created message record

        Raises:
            CommunicationServerAPIError: If request fails
        """
        data = {
            "agent_id": agent_id,
            "content": content,
            "message_type": message_type,
        }
        result = await self._post(f"/api/v1/meetings/{meeting_id}/messages", data)
        return result

    # Decision methods

    async def list_decisions(
        self,
        meeting_id: UUID | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[Decision]:
        """List decisions with optional filters.

        Args:
            meeting_id: Optional meeting ID filter
            status: Optional status filter
            limit: Maximum number of results

        Returns:
            List of Decision records

        Raises:
            CommunicationServerAPIError: If request fails
        """
        params: dict[str, Any] = {"limit": limit}
        if meeting_id:
            params["meeting_id"] = str(meeting_id)
        if status:
            params["status"] = status

        result = await self._get("/api/v1/decisions", params=params)
        return [Decision(**d) for d in result]

    async def get_decision(self, decision_id: UUID) -> Decision | None:
        """Get a decision by ID.

        Args:
            decision_id: Decision UUID

        Returns:
            The Decision record or None if not found

        Raises:
            CommunicationServerAPIError: If request fails
        """
        try:
            result = await self._get(f"/api/v1/decisions/{decision_id}")
            return Decision(**result)
        except CommunicationServerAPIError as e:
            if e.status_code == 404:
                return None
            raise

    # Health check

    async def health_check(self) -> dict[str, Any]:
        """Check if the Communication Server is healthy.

        Returns:
            Health check response

        Raises:
            CommunicationServerAPIError: If request fails
        """
        return await self._get("/health")

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

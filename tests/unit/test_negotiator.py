"""
Unit tests for Capability Negotiator component.

Tests capability negotiation, compatibility checking,
and compatibility matrix computation.
"""

import pytest
from uuid import uuid4

from mcp_broker.models.session import Session, SessionCapabilities
from mcp_broker.negotiation.negotiator import (
    CapabilityNegotiator,
    NegotiationResult,
    ProtocolRequirement,
)


class TestCapabilityNegotiator:
    """Tests for CapabilityNegotiator class."""

    async def test_negotiate_compatible_sessions(
        self, session_a: Session, session_b: Session
    ) -> None:
        """Test negotiation between compatible sessions."""
        negotiator = CapabilityNegotiator()

        result = await negotiator.negotiate(session_a, session_b)

        assert result.compatible is True
        assert "chat_message" in result.supported_protocols
        assert "point_to_point" in result.feature_intersections

    async def test_negotiate_incompatible_protocols(
        self, session_a: Session
    ) -> None:
        """Test negotiation with incompatible protocol versions."""
        negotiator = CapabilityNegotiator()

        # Create session with different protocol versions
        other_caps = SessionCapabilities(
            supported_protocols={"video_chat": ["1.0.0"]}
        )
        session_d = Session(
            session_id=uuid4(), capabilities=other_caps
        )

        result = await negotiator.negotiate(session_a, session_d)

        assert result.compatible is True  # No required protocols, so compatible
        assert len(result.supported_protocols) == 0

    async def test_negotiate_with_required_protocols(
        self, session_a: Session, session_b: Session
    ) -> None:
        """Test negotiation with required protocols."""
        negotiator = CapabilityNegotiator()

        required = [
            ProtocolRequirement(name="chat_message", version="1.0.0")
        ]

        result = await negotiator.negotiate(session_a, session_b, required)

        assert result.compatible is True
        assert "chat_message" in result.supported_protocols

    async def test_negotiate_unmet_requirements(
        self, session_a: Session
    ) -> None:
        """Test negotiation with unmet requirements."""
        negotiator = CapabilityNegotiator()

        # Create session that supports different version of required protocol
        # This ensures suggestion is generated (session_b has versions)
        other_caps = SessionCapabilities(
            supported_protocols={"chat_message": ["1.0.0"], "file_transfer": ["1.0.0"]}
        )
        session_d = Session(
            session_id=uuid4(), capabilities=other_caps
        )

        required = [
            ProtocolRequirement(name="file_transfer", version="2.0.0")
        ]

        result = await negotiator.negotiate(session_a, session_d, required)

        assert result.compatible is False
        assert len(result.incompatibilities) > 0
        # Suggestion should be generated since session_d has file_transfer (different version)
        assert result.suggestion is not None

    async def test_check_compatibility(
        self, session_a: Session
    ) -> None:
        """Test checking individual protocol compatibility."""
        negotiator = CapabilityNegotiator()

        result = await negotiator.check_compatibility(
            session_a, "chat_message", "1.0.0"
        )

        assert result is True

    async def test_check_compatibility_unsupported(
        self, session_a: Session
    ) -> None:
        """Test checking unsupported protocol version."""
        negotiator = CapabilityNegotiator()

        result = await negotiator.check_compatibility(
            session_a, "chat_message", "2.0.0"
        )

        assert result is False

    def test_compute_compatibility_matrix(
        self, session_a: Session, session_b: Session, session_c: Session
    ) -> None:
        """Test computing compatibility matrix."""
        negotiator = CapabilityNegotiator()

        sessions = [session_a, session_b, session_c]
        matrix = negotiator.compute_compatibility_matrix(sessions)

        assert len(matrix.session_ids) == 3
        assert len(matrix.pairs) == 3  # 3 choose 2 = 3 pairs

        # Check specific pair
        pair_key = "0-1"  # First pair
        if pair_key in matrix.pairs:
            pair = matrix.pairs[pair_key]
            assert pair.compatible is True

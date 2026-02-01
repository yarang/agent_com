"""
Capability Negotiator for MCP Broker Server.

This module provides the CapabilityNegotiator class responsible for
performing capability negotiation between sessions.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import UUID

from mcp_broker.core.logging import get_logger
from mcp_broker.models.session import Session

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class NegotiationResult:
    """Result of capability negotiation between two sessions.

    Attributes:
        compatible: Whether the sessions are compatible
        supported_protocols: Dict of protocol name -> common version
        feature_intersections: List of common features
        unsupported_features: Dict of session -> unsupported features
        incompatibilities: List of incompatibility details
        suggestion: Suggested remediation if incompatible
    """

    compatible: bool
    supported_protocols: dict[str, str] = field(default_factory=dict)
    feature_intersections: list[str] = field(default_factory=list)
    unsupported_features: dict[str, list[str]] = field(
        default_factory=lambda: {"session_a": [], "session_b": []}
    )
    incompatibilities: list[str] = field(default_factory=list)
    suggestion: str | None = None


@dataclass
class ProtocolRequirement:
    """Required protocol for negotiation.

    Attributes:
        name: Protocol name
        version: Required version
    """

    name: str
    version: str


@dataclass
class CompatibilityMatrix:
    """Compatibility matrix for multiple sessions.

    Attributes:
        pairs: Dict of pair_key -> compatibility info
        session_ids: List of session IDs in matrix
    """

    pairs: dict[str, "PairCompatibility"] = field(default_factory=dict)
    session_ids: list[UUID] = field(default_factory=list)


@dataclass
class PairCompatibility:
    """Compatibility info for a session pair.

    Attributes:
        session_a_id: First session ID
        session_b_id: Second session ID
        compatible: Whether sessions are compatible
        common_protocols: Dict of protocol -> version
        common_features: List of common features
        reason: Reason if not compatible
    """

    session_a_id: UUID
    session_b_id: UUID
    compatible: bool
    common_protocols: dict[str, str] = field(default_factory=dict)
    common_features: list[str] = field(default_factory=list)
    reason: str | None = None


class CapabilityNegotiator:
    """
    Negotiator for session capability handshake.

    The CapabilityNegotiator handles:
    - Protocol version compatibility checking
    - Feature intersection detection
    - Incompatibility reporting
    - Compatibility matrix computation for multiple sessions

    Attributes:
        None (stateless service)
    """

    def __init__(self) -> None:
        """Initialize the capability negotiator."""
        logger = get_logger(__name__)
        logger.info("CapabilityNegotiator initialized")

    async def negotiate(
        self,
        session_a: Session,
        session_b: Session,
        required_protocols: list[ProtocolRequirement] | None = None,
    ) -> NegotiationResult:
        """Perform capability negotiation between two sessions.

        Args:
            session_a: First session
            session_b: Second session
            required_protocols: Optional required protocol versions

        Returns:
            NegotiationResult with compatibility details
        """
        logger = get_logger(__name__)

        # Find common protocols
        common_protocols = session_a.find_common_protocols(session_b)

        # Check required protocols
        incompatibilities: list[str] = []
        suggestion: str | None = None

        if required_protocols:
            for req in required_protocols:
                if req.name not in common_protocols:
                    session_a_versions = session_a.capabilities.supported_protocols.get(
                        req.name, []
                    )
                    session_b_versions = session_b.capabilities.supported_protocols.get(
                        req.name, []
                    )

                    incompatibilities.append(
                        f"Protocol '{req.name}' version '{req.version}' not supported by both sessions. "
                        f"Session A: {session_a_versions}, Session B: {session_b_versions}"
                    )

                    if session_b_versions:
                        suggestion = (
                            f"Session A should add support for {req.name} {session_b_versions[0]} "
                            f"or Session B should upgrade to {req.name} {req.version}"
                        )

        # Check feature intersection
        features_a = set(session_a.capabilities.supported_features)
        features_b = set(session_b.capabilities.supported_features)
        common_features = list(features_a & features_b)
        unsupported_a = list(features_b - features_a)
        unsupported_b = list(features_a - features_b)

        # Determine compatibility
        compatible = (
            len(common_protocols) > 0 or not required_protocols
        ) and len(incompatibilities) == 0

        result = NegotiationResult(
            compatible=compatible,
            supported_protocols=common_protocols,
            feature_intersections=common_features,
            unsupported_features={"session_a": unsupported_a, "session_b": unsupported_b},
            incompatibilities=incompatibilities,
            suggestion=suggestion,
        )

        logger.info(
            f"Negotiation between {session_a.session_id} and {session_b.session_id}: {compatible}",
            extra={
                "context": {
                    "session_a": str(session_a.session_id),
                    "session_b": str(session_b.session_id),
                    "compatible": compatible,
                    "common_protocols": common_protocols,
                }
            },
        )

        return result

    async def check_compatibility(
        self,
        session: Session,
        protocol_name: str,
        protocol_version: str,
    ) -> bool:
        """Check if a session supports a specific protocol version.

        Args:
            session: Session to check
            protocol_name: Protocol name
            protocol_version: Required version

        Returns:
            True if session supports the protocol version
        """
        return session.supports_protocol(protocol_name, protocol_version)

    def compute_compatibility_matrix(
        self,
        sessions: list[Session],
    ) -> CompatibilityMatrix:
        """Compute compatibility matrix for multiple sessions.

        Args:
            sessions: List of sessions to analyze

        Returns:
            CompatibilityMatrix with pairwise compatibility
        """
        logger = get_logger(__name__)
        matrix = CompatibilityMatrix()
        matrix.session_ids = [s.session_id for s in sessions]

        # Compare each pair
        for i, session_a in enumerate(sessions):
            for j, session_b in enumerate(sessions):
                if i >= j:
                    continue  # Skip duplicates and self-comparison

                # Find common protocols and features
                common_protocols = session_a.find_common_protocols(session_b)

                features_a = set(session_a.capabilities.supported_features)
                features_b = set(session_b.capabilities.supported_features)
                common_features = list(features_a & features_b)

                # Determine compatibility
                compatible = len(common_protocols) > 0

                pair_key = f"{i}-{j}"
                matrix.pairs[pair_key] = PairCompatibility(
                    session_a_id=session_a.session_id,
                    session_b_id=session_b.session_id,
                    compatible=compatible,
                    common_protocols=common_protocols,
                    common_features=common_features,
                    reason=None if compatible else "No common protocols",
                )

        logger.debug(
            f"Computed compatibility matrix for {len(sessions)} sessions",
            extra={
                "context": {
                    "session_count": len(sessions),
                    "pair_count": len(matrix.pairs),
                }
            },
        )

        return matrix

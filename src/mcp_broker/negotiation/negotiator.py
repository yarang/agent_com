"""
Capability Negotiator for MCP Broker Server.

This module provides the CapabilityNegotiator class responsible for
performing capability negotiation between sessions with project-scoped
compatibility checking.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import UUID

from mcp_broker.core.logging import get_logger
from mcp_broker.models.session import Session

if TYPE_CHECKING:
    pass


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
        cross_project: Whether this is a cross-project negotiation
    """

    compatible: bool
    supported_protocols: dict[str, str] = field(default_factory=dict)
    feature_intersections: list[str] = field(default_factory=list)
    unsupported_features: dict[str, list[str]] = field(
        default_factory=lambda: {"session_a": [], "session_b": []}
    )
    incompatibilities: list[str] = field(default_factory=list)
    suggestion: str | None = None
    cross_project: bool = False


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
        project_groups: Dict of project_id -> list of session indices
    """

    pairs: dict[str, "PairCompatibility"] = field(default_factory=dict)
    session_ids: list[UUID] = field(default_factory=list)
    project_groups: dict[str, list[int]] = field(default_factory=dict)


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
        cross_project: Whether sessions are from different projects
    """

    session_a_id: UUID
    session_b_id: UUID
    compatible: bool
    common_protocols: dict[str, str] = field(default_factory=dict)
    common_features: list[str] = field(default_factory=list)
    reason: str | None = None
    cross_project: bool = False


class CapabilityNegotiator:
    """
    Negotiator for session capability handshake.

    The CapabilityNegotiator handles:
    - Protocol version compatibility checking
    - Feature intersection detection
    - Incompatibility reporting
    - Compatibility matrix computation for multiple sessions
    - Project-scoped negotiation with cross-project detection

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
        allow_cross_project: bool = False,
    ) -> NegotiationResult:
        """Perform capability negotiation between two sessions.

        Args:
            session_a: First session
            session_b: Second session
            required_protocols: Optional required protocol versions
            allow_cross_project: Whether to allow cross-project negotiation

        Returns:
            NegotiationResult with compatibility details
        """
        logger = get_logger(__name__)

        # Check if sessions are from different projects
        cross_project = session_a.project_id != session_b.project_id

        # If cross-project and not allowed, return incompatible
        if cross_project and not allow_cross_project:
            logger.info(
                f"Cross-project negotiation blocked: {session_a.project_id} != {session_b.project_id}",
                extra={
                    "context": {
                        "session_a": str(session_a.session_id),
                        "session_b": str(session_b.session_id),
                        "project_a": session_a.project_id,
                        "project_b": session_b.project_id,
                    }
                },
            )
            return NegotiationResult(
                compatible=False,
                cross_project=True,
                incompatibilities=[
                    f"Cross-project negotiation not allowed: "
                    f"session from '{session_a.project_id}' cannot negotiate with "
                    f"session from '{session_b.project_id}'"
                ],
                suggestion="Enable cross-project communication or ensure sessions are in the same project",
            )

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
        compatible = (len(common_protocols) > 0 or not required_protocols) and len(
            incompatibilities
        ) == 0

        result = NegotiationResult(
            compatible=compatible,
            supported_protocols=common_protocols,
            feature_intersections=common_features,
            unsupported_features={"session_a": unsupported_a, "session_b": unsupported_b},
            incompatibilities=incompatibilities,
            suggestion=suggestion,
            cross_project=cross_project,
        )

        logger.info(
            f"Negotiation between {session_a.session_id} and {session_b.session_id}: {compatible}",
            extra={
                "context": {
                    "session_a": str(session_a.session_id),
                    "session_b": str(session_b.session_id),
                    "project_a": session_a.project_id,
                    "project_b": session_b.project_id,
                    "compatible": compatible,
                    "cross_project": cross_project,
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
        allow_cross_project: bool = False,
    ) -> CompatibilityMatrix:
        """Compute compatibility matrix for multiple sessions.

        Args:
            sessions: List of sessions to analyze
            allow_cross_project: Whether to allow cross-project compatibility

        Returns:
            CompatibilityMatrix with pairwise compatibility
        """
        logger = get_logger(__name__)
        matrix = CompatibilityMatrix()
        matrix.session_ids = [s.session_id for s in sessions]

        # Group sessions by project
        for idx, session in enumerate(sessions):
            if session.project_id not in matrix.project_groups:
                matrix.project_groups[session.project_id] = []
            matrix.project_groups[session.project_id].append(idx)

        # Compare each pair
        for i, session_a in enumerate(sessions):
            for j, session_b in enumerate(sessions):
                if i >= j:
                    continue  # Skip duplicates and self-comparison

                # Check if cross-project
                cross_project = session_a.project_id != session_b.project_id

                # Skip cross-project if not allowed
                if cross_project and not allow_cross_project:
                    pair_key = f"{i}-{j}"
                    matrix.pairs[pair_key] = PairCompatibility(
                        session_a_id=session_a.session_id,
                        session_b_id=session_b.session_id,
                        compatible=False,
                        common_protocols={},
                        common_features=[],
                        reason=f"Cross-project compatibility not allowed: {session_a.project_id} != {session_b.project_id}",
                        cross_project=True,
                    )
                    continue

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
                    cross_project=cross_project,
                )

        logger.debug(
            f"Computed compatibility matrix for {len(sessions)} sessions",
            extra={
                "context": {
                    "session_count": len(sessions),
                    "pair_count": len(matrix.pairs),
                    "project_groups": len(matrix.project_groups),
                }
            },
        )

        return matrix

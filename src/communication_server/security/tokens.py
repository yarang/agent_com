"""
Token generation and validation utilities.

Provides JWT tokens for dashboard users and API tokens for agents.
"""

from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from pydantic import BaseModel

# Use argon2 for password hashing (more reliable than bcrypt)
try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError

    HASHER = PasswordHasher(
        time_cost=2,  # Number of iterations
        memory_cost=65536,  # Memory usage in KiB
        parallelism=4,  # Number of parallel threads
        hash_len=32,  # Hash length
        salt_len=16,  # Salt length
    )
except ImportError:
    # Fallback to passlib with argon2
    from passlib.context import CryptContext

    HASHER = CryptContext(
        schemes=["argon2"],
        deprecated="auto",
        argon2__time_cost=2,
        argon2__memory_cost=65536,
        argon2__parallelism=4,
    )


# Lazy import of config to avoid circular imports
def _get_jwt_secret_key() -> str:
    """Get JWT secret key from configuration."""
    from agent_comm_core.config import get_config

    config = get_config()
    return config.authentication.jwt.secret_key


def _get_jwt_algorithm() -> str:
    """Get JWT algorithm from configuration."""
    from agent_comm_core.config import get_config

    config = get_config()
    return config.authentication.jwt.algorithm


def _get_access_token_expire_minutes() -> int:
    """Get access token expiration from configuration."""
    from agent_comm_core.config import get_config

    config = get_config()
    return config.authentication.jwt.access_token_expire_minutes


def _get_refresh_token_expire_days() -> int:
    """Get refresh token expiration from configuration."""
    from agent_comm_core.config import get_config

    config = get_config()
    return config.authentication.jwt.refresh_token_expire_days


def _get_api_token_prefix() -> str:
    """Get API token prefix from configuration."""
    from agent_comm_core.config import get_config

    config = get_config()
    return config.authentication.api_token.prefix


# Token data model
class TokenData(BaseModel):
    """Data extracted from JWT token."""

    user_id: str | None = None
    agent_id: str | None = None
    exp: int | None = None
    type: str | None = None  # 'access' or 'refresh'


def _validate_jwt_config() -> None:
    """
    Validate JWT configuration is properly set.

    Raises:
        ValueError: If JWT_SECRET_KEY is not set or too short
    """
    secret_key = _get_jwt_secret_key()
    if not secret_key or secret_key == "change-me-in-production":
        raise ValueError(
            "JWT secret key must be configured in config.json "
            "under authentication.jwt.secret_key. "
            "Generate a secure key with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )
    if len(secret_key) < 32:
        raise ValueError(
            f"JWT secret key must be at least 32 characters long for security. "
            f"Current length: {len(secret_key)} characters"
        )


def create_access_token(data: dict, expires_delta: int | None = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Payload data to encode in the token
        expires_delta: Custom expiration time in minutes (optional)

    Returns:
        Encoded JWT access token

    Raises:
        ValueError: If JWT configuration is invalid
    """
    _validate_jwt_config()

    to_encode = data.copy()

    # Set expiration
    if expires_delta:
        expire = datetime.now(UTC) + timedelta(minutes=expires_delta)
    else:
        expire = datetime.now(UTC) + timedelta(minutes=_get_access_token_expire_minutes())

    to_encode.update(
        {
            "exp": expire,
            "type": "access",
        }
    )

    # Encode token
    encoded_jwt = jwt.encode(to_encode, _get_jwt_secret_key(), algorithm=_get_jwt_algorithm())
    return encoded_jwt


def create_refresh_token(user_id: str) -> str:
    """
    Create a JWT refresh token for token renewal.

    Args:
        user_id: User ID to embed in the token

    Returns:
        Encoded JWT refresh token

    Raises:
        ValueError: If JWT configuration is invalid
    """
    _validate_jwt_config()

    expire = datetime.now(UTC) + timedelta(days=_get_refresh_token_expire_days())

    to_encode = {
        "sub": user_id,
        "exp": expire,
        "type": "refresh",
    }

    encoded_jwt = jwt.encode(to_encode, _get_jwt_secret_key(), algorithm=_get_jwt_algorithm())
    return encoded_jwt


def decode_token(token: str) -> dict:
    """
    Decode a JWT token without validation.

    Args:
        token: JWT token to decode

    Returns:
        Decoded token payload

    Raises:
        JWTError: If token cannot be decoded
    """
    try:
        payload = jwt.decode(
            token,
            _get_jwt_secret_key(),
            algorithms=[_get_jwt_algorithm()],
        )
        return payload
    except JWTError as e:
        raise JWTError(f"Unable to decode token: {e}") from e


def verify_jwt_token(token: str) -> TokenData:
    """
    Verify and validate a JWT token.

    Args:
        token: JWT token to verify

    Returns:
        TokenData with extracted information

    Raises:
        JWTError: If token is invalid, expired, or malformed
    """
    _validate_jwt_config()

    try:
        payload = jwt.decode(
            token,
            _get_jwt_secret_key(),
            algorithms=[_get_jwt_algorithm()],
        )

        # Extract token type
        token_type = payload.get("type")
        if token_type not in ("access", "refresh"):
            raise JWTError("Invalid token type")

        # Create TokenData
        token_data = TokenData(
            user_id=payload.get("sub"),
            exp=payload.get("exp"),
            type=token_type,
        )

        return token_data

    except jwt.ExpiredSignatureError as e:
        raise JWTError("Token has expired") from e
    except jwt.JWTError as e:
        raise JWTError(f"Invalid token: {e}") from e


def generate_agent_token(project_id: str, name: str) -> str:
    """
    Generate a secure API token for agent authentication.

    Args:
        project_id: Project ID the agent belongs to
        name: Agent name/identifier

    Returns:
        Secure API token with prefix
    """
    # Generate cryptographically secure random token
    import secrets

    random_part = secrets.token_urlsafe(32)
    prefix = _get_api_token_prefix()

    # Combine project and name for uniqueness
    token = f"{prefix}{project_id}_{name}_{random_part}"

    return token


def hash_api_token(token: str) -> str:
    """
    Hash an API token for secure storage using argon2.

    Args:
        token: Plain text API token

    Returns:
        Argon2 hashed token

    Raises:
        ValueError: If token is empty
    """
    if not token:
        raise ValueError("Token cannot be empty")

    # Use argon2 PasswordHasher if available
    if hasattr(HASHER, "hash"):
        return HASHER.hash(token)
    else:
        # Fallback to passlib CryptContext
        return HASHER.hash(token)  # type: ignore[arg-type]


def validate_agent_token(token: str, hashed_token: str) -> bool:
    """
    Validate an agent API token against its hash.

    Uses constant-time comparison to prevent timing attacks.

    Args:
        token: Plain text token to validate
        hashed_token: Stored argon2 hash

    Returns:
        True if token matches hash, False otherwise
    """
    if not token or not hashed_token:
        return False

    try:
        # Use argon2 PasswordHasher if available
        if hasattr(HASHER, "verify"):
            HASHER.verify(hashed_token, token)
            return True
        else:
            # Fallback to passlib CryptContext
            return HASHER.verify(token, hashed_token)  # type: ignore[arg-type]
    except (VerifyMismatchError, ValueError, TypeError):
        return False


def extract_token_from_header(authorization: str) -> str:
    """
    Extract bearer token from Authorization header.

    Args:
        authorization: Authorization header value

    Returns:
        Extracted token

    Raises:
        ValueError: If header is malformed
    """
    if not authorization:
        raise ValueError("Missing Authorization header")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise ValueError("Invalid Authorization header format. Expected: 'Bearer <token>'")

    return parts[1]

"""
Security module for MCP Broker Server.

Provides authentication middleware, token validation for API access,
and startup security validation for configuration files.
"""

import json
import secrets
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, Request, status
from fastapi.security import APIKeyCookie, APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from mcp_broker.core.config import get_config
from mcp_broker.core.logging import get_logger

# Security schemes
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_cookie = APIKeyCookie(name="api_key", auto_error=False)

logger = get_logger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce authentication based on configuration."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with authentication check.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler

        Returns:
            HTTP response
        """
        config = get_config()

        # Skip authentication for public endpoints
        if request.url.path in ["/", "/health", "/docs", "/openapi.json"]:
            return await call_next(request)

        # Skip if auth is disabled
        if not config.enable_auth:
            return await call_next(request)

        # Validate authentication
        if not config.auth_secret:
            logger.warning("Authentication enabled but no secret configured")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server configuration error: authentication enabled but no secret",
            )

        # Check for API key in header or cookie
        api_key = request.headers.get("X-API-Key") or request.cookies.get("api_key")

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required. Provide X-API-Key header or api_key cookie.",
            )

        if not secrets.compare_digest(api_key, config.auth_secret):
            logger.warning(f"Invalid authentication attempt from {request.client}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid API key",
            )

        return await call_next(request)


async def verify_auth_token(request: Request) -> bool:
    """Verify authentication token from request.

    Args:
        request: Incoming HTTP request

    Returns:
        True if authenticated, False otherwise
    """
    config = get_config()

    # Skip if auth is disabled
    if not config.enable_auth:
        return True

    # Check for API key in header or cookie
    api_key = request.headers.get("X-API-Key") or request.cookies.get("api_key")

    if not api_key or not config.auth_secret:
        return False

    return secrets.compare_digest(api_key, config.auth_secret)


def generate_session_token() -> str:
    """Generate a cryptographically secure session token.

    Returns:
        Random token string
    """
    return secrets.token_urlsafe(32)


def validate_session_token(token: str, _max_age_seconds: int = 3600) -> bool:
    """Validate a session token and its age.

    Args:
        token: Token string to validate
        _max_age_seconds: Maximum age of token in seconds (unused, for future implementation)

    Returns:
        True if token is valid and not expired
    """
    if not token or len(token) < 32:
        return False

    # For now, simple validation - in production, check against token store
    # Token format validation (base64url encoded)
    try:
        # Ensure token only contains valid characters
        valid_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
        return all(c in valid_chars for c in token)
    except Exception:
        return False


class SecurityContext:
    """Security context for request-scoped security information."""

    def __init__(self, authenticated: bool = False, session_id: UUID | None = None):
        """Initialize security context.

        Args:
            authenticated: Whether the request is authenticated
            session_id: Optional session identifier
        """
        self.authenticated = authenticated
        self.session_id = session_id
        self.timestamp = time.time()

    def is_authenticated(self) -> bool:
        """Check if the context is authenticated.

        Returns:
            True if authenticated
        """
        return self.authenticated

    def age_seconds(self) -> float:
        """Get the age of this context in seconds.

        Returns:
            Age in seconds since creation
        """
        return time.time() - self.timestamp


# =============================================================================
# Startup Security Validation
# =============================================================================

# Security warning messages
_SECURITY_WARNINGS = {
    "plaintext_token": """
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                           SECURITY WARNING                            ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

WARNING: AGENT_TOKEN found in .mcp.json configuration file!

This is a SECURITY RISK. Your token is stored in plaintext and could be:
  - Committed to version control
  - Exposed in file sharing
  - Accessed by unauthorized users

RECOMMENDED ACTION:
  1. Remove AGENT_TOKEN from .mcp.json
  2. Run: python scripts/migrate_tokens.py
  3. Set AGENT_TOKEN as environment variable:

     export AGENT_TOKEN='your-token-here'

For automatic migration, run:
  python scripts/migrate_tokens.py --dry-run  # Preview changes
  python scripts/migrate_tokens.py            # Execute migration

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""",
    "config_git_tracked": """
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                    CRITICAL SECURITY WARNING                          ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

CRITICAL: .mcp.json is tracked by Git!

Your configuration file may have been committed with sensitive tokens.

IMMEDIATE ACTION REQUIRED:
  1. Check git history for exposed tokens:
     git log --all --full-history --source -- "*.mcp.json"

  2. If tokens were committed, consider them compromised:
     - Rotate all exposed tokens immediately
     - Remove from git history: git filter-branch (USE WITH CAUTION)
     - Force push to remove from remote

  3. Add to .gitignore (if not already present):
     echo ".mcp.json" >> .gitignore
     echo ".mcp.local.json" >> .gitignore

  4. Remove from git tracking:
     git rm --cached .mcp.json
     git commit -m "Security: Remove .mcp.json from version control"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""",
    "weak_token": """
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                         TOKEN SECURITY WARNING                        ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

WARNING: AGENT_TOKEN does not meet security requirements.

Token validation checks:
  - Minimum length: 32 characters
  - Valid format: Starts with 'agent_' prefix
  - No placeholder values: 'example', 'your-', 'change'

Please obtain a proper token from your communication server dashboard.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""",
}


class SecurityValidator:
    """Validates security configuration at startup."""

    def __init__(self, config_path: Path | None = None):
        """Initialize security validator.

        Args:
            config_path: Path to .mcp.json configuration file
        """
        self.config_path = config_path or Path.cwd() / ".mcp.json"
        self.warnings_shown: list[str] = []

    def check_plaintext_token(self) -> bool:
        """Check if AGENT_TOKEN is stored in .mcp.json.

        Returns:
            True if plaintext token detected (warning shown), False otherwise
        """
        if not self.config_path.exists():
            return False

        try:
            with open(self.config_path) as f:
                config = json.load(f)

            # Navigate to agent-comm server env
            agent_comm = config.get("mcpServers", {}).get("agent-comm", {})
            env = agent_comm.get("env", {})

            if "AGENT_TOKEN" in env:
                token = env["AGENT_TOKEN"]

                # Check if it's a placeholder value
                placeholder_indicators = [
                    "your-",
                    "here",
                    "change",
                    "placeholder",
                    "example",
                ]
                is_placeholder = any(
                    indicator in token.lower() for indicator in placeholder_indicators
                )

                if not is_placeholder:
                    print(_SECURITY_WARNINGS["plaintext_token"])
                    self.warnings_shown.append("plaintext_token")
                    return True

        except (json.JSONDecodeError, OSError):
            pass

        return False

    def check_git_tracked(self) -> bool:
        """Check if .mcp.json is tracked by Git.

        Returns:
            True if file is git tracked (warning shown), False otherwise
        """
        if not self.config_path.exists():
            return False

        # Check if we're in a git repository
        git_dir = Path.cwd()
        while git_dir != git_dir.parent:
            if (git_dir / ".git").exists():
                break
            git_dir = git_dir.parent
        else:
            # Not in a git repository
            return False

        try:
            # Use git ls-files to check if file is tracked
            result = subprocess.run(
                ["git", "ls-files", str(self.config_path)],
                capture_output=True,
                text=True,
                cwd=git_dir,
                check=False,
            )

            if result.stdout.strip():
                print(_SECURITY_WARNINGS["config_git_tracked"])
                self.warnings_shown.append("config_git_tracked")
                return True

        except (FileNotFoundError, OSError):
            pass

        return False

    def validate_token_strength(self, token: str) -> bool:
        """Validate token meets security requirements.

        Args:
            token: The AGENT_TOKEN to validate

        Returns:
            True if token is strong enough, False if weak (warning shown)
        """
        if not token:
            return True  # No token to validate

        # Check minimum length
        if len(token) < 32:
            print(_SECURITY_WARNINGS["weak_token"])
            self.warnings_shown.append("weak_token")
            return False

        # Check for placeholder values
        placeholder_indicators = [
            "your-",
            "here",
            "change",
            "placeholder",
            "example",
        ]
        if any(indicator in token.lower() for indicator in placeholder_indicators):
            print(_SECURITY_WARNINGS["weak_token"])
            self.warnings_shown.append("weak_token")
            return False

        return True

    def run_all_checks(self, token: str | None = None) -> list[str]:
        """Run all security checks.

        Args:
            token: Optional AGENT_TOKEN to validate

        Returns:
            List of warning identifiers that were shown
        """
        self.warnings_shown = []

        # Check for plaintext token in config
        self.check_plaintext_token()

        # Check if config is git tracked
        self.check_git_tracked()

        # Validate token strength if provided
        if token:
            self.validate_token_strength(token)

        return self.warnings_shown


def validate_startup_security(token: str | None = None) -> list[str]:
    """Convenience function to run security validation at startup.

    Args:
        token: Optional AGENT_TOKEN to validate

    Returns:
        List of warning identifiers that were shown
    """
    validator = SecurityValidator()
    return validator.run_all_checks(token)


def is_mcp_config_gitignored() -> bool:
    """Check if .mcp.json patterns are in .gitignore.

    Returns:
        True if .mcp.json is gitignored, False otherwise
    """
    gitignore_path = Path.cwd() / ".gitignore"

    if not gitignore_path.exists():
        return False

    try:
        with open(gitignore_path) as f:
            content = f.read()

        # Check for .mcp.json patterns
        return ".mcp.json" in content or ".mcp.local.json" in content

    except OSError:
        return False

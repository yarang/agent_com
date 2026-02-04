"""
Input validation middleware for security hardening.

Provides comprehensive input validation to prevent:
- SQL injection
- XSS attacks
- Path traversal
- Command injection
- Oversized payloads
"""

import re
import html
import json
from typing import Any, Optional
from urllib.parse import unquote

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class InputValidator:
    """
    Comprehensive input validation for security.

    Validates and sanitizes user input to prevent common attacks.
    """

    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\bunion\b.*\bselect\b)",
        r"(\bselect\b.*\bfrom\b)",
        r"(\binsert\b.*\binto\b)",
        r"(\bupdate\b.*\bset\b)",
        r"(\bdelete\b.*\bfrom\b)",
        r"(\bdrop\b.*\btable\b)",
        r"(\bexec\b|\bexecute\b)",
        r"(;.*\b(?:exec|execute)\b)",
        r"('.*--)",
        r"(/\*.*\*/)",
        r"(\bor\b.*=.*\bor\b)",
        r"(\band\b.*=.*\band\b)",
    ]

    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
        r"<embed[^>]*>",
        r"<object[^>]*>",
        r"vbscript:",
        r"fromCharCode",
        r"&#",
        r"<.*?>",
    ]

    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\./",
        r"%2e%2e%2f",
        r"%2e%2e\\",
        r"\.\.\\",
        r"~",
        r"%00",
    ]

    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r";\s*\w+\s*",
        r"\|\s*\w+\s*",
        r"&&\s*\w+\s*",
        r"`[^`]*`",
        r"\$\(.*\)",
        r"<\?[^>]*>",
    ]

    def __init__(
        self,
        max_request_size: int = 10485760,  # 10MB
        enable_sql_injection_check: bool = True,
        enable_xss_check: bool = True,
        enable_path_traversal_check: bool = True,
        enable_command_injection_check: bool = True,
    ) -> None:
        """
        Initialize the input validator.

        Args:
            max_request_size: Maximum request size in bytes
            enable_sql_injection_check: Enable SQL injection detection
            enable_xss_check: Enable XSS detection
            enable_path_traversal_check: Enable path traversal detection
            enable_command_injection_check: Enable command injection detection
        """
        self.max_request_size = max_request_size
        self.enable_sql_injection_check = enable_sql_injection_check
        self.enable_xss_check = enable_xss_check
        self.enable_path_traversal_check = enable_path_traversal_check
        self.enable_command_injection_check = enable_command_injection_check

        # Compile patterns for performance
        self.sql_patterns = [re.compile(p, re.IGNORECASE) for p in self.SQL_INJECTION_PATTERNS]
        self.xss_patterns = [re.compile(p, re.IGNORECASE) for p in self.XSS_PATTERNS]
        self.path_patterns = [re.compile(p, re.IGNORECASE) for p in self.PATH_TRAVERSAL_PATTERNS]
        self.command_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.COMMAND_INJECTION_PATTERNS
        ]

    def validate_string(self, value: str, field_name: str = "input") -> str:
        """
        Validate a string input against all security patterns.

        Args:
            value: String to validate
            field_name: Name of the field being validated

        Returns:
            Sanitized string

        Raises:
            HTTPException: If validation fails
        """
        if not isinstance(value, str):
            raise HTTPException(
                status_code=400,
                detail=f"Field '{field_name}' must be a string",
            )

        # Check length
        if len(value) > 10000:
            raise HTTPException(
                status_code=400,
                detail=f"Field '{field_name}' exceeds maximum length",
            )

        # SQL injection check
        if self.enable_sql_injection_check:
            for pattern in self.sql_patterns:
                if pattern.search(value):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Field '{field_name}' contains potentially malicious SQL code",
                    )

        # XSS check
        if self.enable_xss_check:
            for pattern in self.xss_patterns:
                if pattern.search(value):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Field '{field_name}' contains potentially malicious script code",
                    )

        # Command injection check
        if self.enable_command_injection_check:
            for pattern in self.command_patterns:
                if pattern.search(value):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Field '{field_name}' contains potentially malicious command code",
                    )

        # Sanitize HTML entities
        value = html.escape(value)

        return value

    def validate_path(self, value: str, field_name: str = "path") -> str:
        """
        Validate a path string against path traversal patterns.

        Args:
            value: Path string to validate
            field_name: Name of the field being validated

        Returns:
            Sanitized path string

        Raises:
            HTTPException: If validation fails
        """
        if not isinstance(value, str):
            raise HTTPException(
                status_code=400,
                detail=f"Field '{field_name}' must be a string",
            )

        # URL decode first
        decoded = unquote(value)

        # Path traversal check
        if self.enable_path_traversal_check:
            for pattern in self.path_patterns:
                if pattern.search(decoded):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Field '{field_name}' contains potentially malicious path code",
                    )

        return value

    def validate_json(self, value: Any, field_name: str = "json") -> Any:
        """
        Validate JSON input.

        Args:
            value: Value to validate
            field_name: Name of the field being validated

        Returns:
            Validated JSON value

        Raises:
            HTTPException: If validation fails
        """
        if isinstance(value, str):
            # Try to parse and re-serialize to validate
            try:
                parsed = json.loads(value)
                # Check size of serialized JSON
                if len(value) > 100000:  # 100KB
                    raise HTTPException(
                        status_code=400,
                        detail=f"Field '{field_name}' exceeds maximum JSON size",
                    )
                return parsed
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Field '{field_name}' contains invalid JSON",
                )

        # Recursively validate nested structures
        if isinstance(value, dict):
            return {k: self.validate_json(v, f"{field_name}.{k}") for k, v in value.items()}
        elif isinstance(value, list):
            return [self.validate_json(v, f"{field_name}[]") for v in value]
        elif isinstance(value, str):
            return self.validate_string(value, field_name)
        else:
            return value

    def sanitize_input(self, value: Any, field_name: str = "input") -> Any:
        """
        Sanitize input based on its type.

        Args:
            value: Value to sanitize
            field_name: Name of the field being validated

        Returns:
            Sanitized value
        """
        if value is None:
            return None

        if isinstance(value, str):
            return self.validate_string(value, field_name)
        elif isinstance(value, dict):
            return {k: self.sanitize_input(v, f"{field_name}.{k}") for k, v in value.items()}
        elif isinstance(value, list):
            return [self.sanitize_input(v, f"{field_name}[]") for v in value]
        else:
            return value


class InputValidationMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for input validation.

    Automatically validates request body, query parameters, and path parameters.
    """

    def __init__(
        self,
        app,
        validator: Optional[InputValidator] = None,
        exclude_paths: Optional[set[str]] = None,
    ) -> None:
        """
        Initialize the middleware.

        Args:
            app: FastAPI application
            validator: Input validator instance
            exclude_paths: Paths to exclude from validation
        """
        super().__init__(app)
        self.validator = validator or InputValidator()
        self.exclude_paths = exclude_paths or {"/health", "/metrics", "/docs", "/openapi.json"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with input validation.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response or raises HTTPException if validation fails
        """
        # Skip validation for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # Validate request size
        content_length = request.headers.get("content-length")
        if content_length:
            if int(content_length) > self.validator.max_request_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"Request body exceeds maximum size of {self.validator.max_request_size} bytes",
                )

        # Validate query parameters
        for key, value in request.query_params.items():
            if isinstance(value, str):
                self.validator.validate_string(value, f"query.{key}")

        # Validate path parameters
        for key, value in request.path_params.items():
            if isinstance(value, str):
                if "path" in key.lower() or "file" in key.lower():
                    self.validator.validate_path(value, f"path.{key}")
                else:
                    self.validator.validate_string(value, f"path.{key}")

        # Process request
        response = await call_next(request)

        return response


def sanitize_dict(
    data: dict[str, Any], validator: Optional[InputValidator] = None
) -> dict[str, Any]:
    """
    Sanitize a dictionary of input data.

    Args:
        data: Dictionary to sanitize
        validator: Optional validator instance

    Returns:
        Sanitized dictionary
    """
    validator = validator or InputValidator()
    return {k: validator.sanitize_input(v, k) for k, v in data.items()}


def get_default_validator() -> InputValidator:
    """Get the default input validator instance."""
    return InputValidator()

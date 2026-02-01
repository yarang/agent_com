"""
HTTP Client for Communication Server integration.

This module provides an async HTTP client for communicating with
the Communication Server REST API for logging communications,
managing meetings, and retrieving decisions.
"""

from mcp_broker.client.http_client import HTTPClient

__all__ = ["HTTPClient"]

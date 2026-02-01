"""
Communication Server for AI Agent Communication System.

Provides REST API and WebSocket endpoints for agent communication,
meeting management, and sequential discussion coordination.
"""

__version__ = "1.0.0"

# Import main app for package entry point
try:
    from .main import app

    __all__ = ["app"]
except ImportError:
    # During development, the app may not be importable
    __all__ = []

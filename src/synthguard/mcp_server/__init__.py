"""Safe local MCP interface for SynthGuard."""

from .paths import McpServerError, PathPolicy
from .server import create_server, mcp

__all__ = ["McpServerError", "PathPolicy", "create_server", "mcp"]

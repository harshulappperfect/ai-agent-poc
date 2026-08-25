"""Re-export database query helpers for the MCP server module."""

from __future__ import annotations

from app.database import execute_query, execute_single_query

__all__ = ["execute_query", "execute_single_query"]

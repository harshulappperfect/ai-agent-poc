"""PostgreSQL database client for Finance Agent Plugin.

Provides database connection management, parameterized query execution,
type serialization, and robust read-only SQL safety checks for 9 relational tables.
"""

from __future__ import annotations

import logging
import os
import re
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Generator

from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)

# Regex pattern matching forbidden DML/DDL/DCL write keywords with word boundaries
FORBIDDEN_SQL_PATTERNS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE|GRANT|REVOKE|COPY|EXECUTE|CALL|VACUUM|REINDEX)\b",
    re.IGNORECASE,
)

# Maximum allowed rows returned by any query to prevent context window overflow
MAX_QUERY_ROW_LIMIT = 100

# Load environment variables
load_dotenv(override=True)


def get_db_config() -> dict[str, Any]:
    """Retrieve database connection parameters from environment variables."""
    return {
        "host": os.getenv("DATABASE_HOST", "localhost"),
        "port": int(os.getenv("DATABASE_PORT", "5432")),
        "dbname": os.getenv("DATABASE_NAME", "mydatabase"),
        "user": os.getenv("DATABASE_USER", "agent_readonly"),
        "password": os.getenv("DATABASE_PASSWORD", "Harshul01"),
    }


def _serialize_value(val: Any) -> Any:
    """Convert database types (Decimal, date) into JSON-compatible Python types."""
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, (date, datetime)):
        return val.isoformat()
    return val


def _serialize_row(row: dict[str, Any] | None) -> dict[str, Any] | None:
    """Serialize all values in a single row dict."""
    if row is None:
        return None
    return {k: _serialize_value(v) for k, v in row.items()}


@contextmanager
def get_connection() -> Generator[psycopg.Connection, None, None]:
    """Context manager for PostgreSQL database connections.
    
    Yields:
        psycopg.Connection: Active database connection.
    """
    config = get_db_config()
    conn = None
    try:
        conn = psycopg.connect(
            host=config["host"],
            port=config["port"],
            dbname=config["dbname"],
            user=config["user"],
            password=config["password"],
            row_factory=dict_row,
            autocommit=True,
            connect_timeout=3,
        )
        yield conn
    except psycopg.Error as e:
        raise ConnectionError(
            f"Plugin failed to connect to PostgreSQL '{config['dbname']}' on {config['host']}:{config['port']} as user '{config['user']}'. "
            f"Ensure PostgreSQL container 'finance-postgres' is running. (Details: {e})"
        ) from e
    finally:
        if conn is not None and not conn.closed:
            conn.close()


def _validate_query_safety(query: str) -> None:
    """Ensure query strictly begins with SELECT or WITH and contains no write operations."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Query must be a non-empty string.")

    clean_query = query.strip()

    # 1. Enforce that query starts with SELECT or WITH (Common Table Expressions)
    if not re.match(r"^(SELECT|WITH)\b", clean_query, re.IGNORECASE):
        raise ValueError("Security Error: Only SELECT and WITH (CTE) queries are permitted.")

    # 2. Block forbidden DML/DDL/DCL keywords
    if FORBIDDEN_SQL_PATTERNS.search(clean_query):
        match = FORBIDDEN_SQL_PATTERNS.search(clean_query)
        raise ValueError(f"Security Error: Forbidden operation '{match.group(0)}' is not permitted.")

    # 3. Disallow multi-statement execution (semicolon followed by non-whitespace text)
    stripped_semicolon = clean_query.rstrip(";").strip()
    if ";" in stripped_semicolon:
        raise ValueError("Security Error: Multi-statement SQL execution is not allowed.")


def execute_query(query: str, params: tuple | list | dict | None = None) -> list[dict[str, Any]]:
    """Execute a parameterized or dynamic SELECT query and return rows as dicts (max 100 rows)."""
    _validate_query_safety(query)
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchmany(MAX_QUERY_ROW_LIMIT)
                return [_serialize_row(row) for row in rows]
    except Exception as e:
        logger.error("Query execution failed: %r", e)
        raise


def execute_single_query(query: str, params: tuple | list | dict | None = None) -> dict[str, Any] | None:
    """Execute a SELECT query and return a single row as a dict."""
    _validate_query_safety(query)
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                row = cur.fetchone()
                return _serialize_row(row)
    except Exception as e:
        logger.error("Query execution failed: %r", e)
        raise

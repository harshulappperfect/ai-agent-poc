"""PostgreSQL database client using psycopg (v3).

Provides connection management and parameterized query execution
for financial forecasts and actuals data.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Generator

from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

# Load environment variables from .env
load_dotenv()


def get_db_config() -> dict[str, Any]:
    """Retrieve database connection parameters from environment variables."""
    return {
        "host": os.getenv("DATABASE_HOST", "localhost"),
        "port": int(os.getenv("DATABASE_PORT", "5432")),
        "dbname": os.getenv("DATABASE_NAME", "mydatabase"),
        "user": os.getenv("DATABASE_USER", "postgres"),
        "password": os.getenv("DATABASE_PASSWORD", "MyStrongPassword123!"),
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
        # Avoid leaking credentials in logs
        raise ConnectionError(
            f"Failed to connect to PostgreSQL database '{config['dbname']}' on {config['host']}:{config['port']}. Please check if the Docker container 'finance-postgres' is running. (Details: {e})"
        ) from e
    finally:
        if conn is not None and not conn.closed:
            conn.close()


def execute_query(query: str, params: tuple | list | dict | None = None) -> list[dict[str, Any]]:
    """Execute a parameterized SELECT query and return all rows as dicts.
    
    Args:
        query: Parameterized SQL query string.
        params: Parameters to substitute into the query.
        
    Returns:
        List of row dictionaries with serialized data.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
                print("[PostgreSQL] Query executed successfully")
                return [_serialize_row(row) for row in rows]
    except Exception as e:
        print(f"[PostgreSQL] Query execution failed: {e}")
        raise


def execute_single_query(query: str, params: tuple | list | dict | None = None) -> dict[str, Any] | None:
    """Execute a parameterized SELECT query and return a single row as a dict.
    
    Args:
        query: Parameterized SQL query string.
        params: Parameters to substitute into the query.
        
    Returns:
        Single row dictionary with serialized data, or None if no result.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                row = cur.fetchone()
                print("[PostgreSQL] Query executed successfully")
                return _serialize_row(row)
    except Exception as e:
        print(f"[PostgreSQL] Query execution failed: {e}")
        raise

"""
MCP Database Server - Using FastMCP (Standalone Package)
=========================================================

This server exposes database query capabilities as MCP tools using
the FastMCP framework - the fast, Pythonic way to build MCP servers.

Key Features:
- @mcp.tool() decorator for tool definition
- Automatic JSON Schema generation from type hints
- Built-in HTTP transport with host/port configuration
- Clean, minimal API

Learning Points:
- FastMCP simplifies server creation with decorators
- Type hints are used to generate JSON Schema automatically
- The run() method handles all transport details
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("MCP Database Server")

# Database connection parameters from environment
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "postgres"),
    "database": os.environ.get("DB_NAME", "mcp"),
    "user": os.environ.get("DB_USER", "mcp"),
    "password": os.environ.get("DB_PASSWORD", "mcp"),
}


def get_db_connection():
    """Create and return a database connection."""
    return psycopg2.connect(**DB_CONFIG)


@mcp.tool()
def query_db(sql: str) -> list[dict]:
    """
    Execute a SQL query against the database.

    Available tables:
    - users (id SERIAL PRIMARY KEY, username VARCHAR(50), email VARCHAR(100))
    - notes (id SERIAL PRIMARY KEY, user_id INTEGER REFERENCES users(id),
             title VARCHAR(255), content TEXT, created_at TIMESTAMP)

    Args:
        sql: SQL query to execute (SELECT, INSERT, UPDATE, DELETE)

    Returns:
        For SELECT queries: List of dictionaries with query results
        For other queries: Status and rows affected

    Examples:
        - SELECT * FROM users
        - SELECT n.*, u.username FROM notes n JOIN users u ON n.user_id = u.id
        - SELECT * FROM notes WHERE title ILIKE '%shopping%'
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(sql)

        # Check if query returns rows (SELECT) or is a mutation (INSERT/UPDATE/DELETE)
        if cur.description:
            rows = cur.fetchall()
            result = [dict(row) for row in rows]
        else:
            conn.commit()
            result = [{"status": "success", "rows_affected": cur.rowcount}]

        cur.close()
        return result

    except Exception as e:
        conn.rollback()
        raise ValueError(f"Query error: {str(e)}")

    finally:
        conn.close()


@mcp.tool()
def list_tables() -> list[str]:
    """
    List all tables in the database.

    Returns:
        List of table names in the public schema
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)
        tables = [row[0] for row in cur.fetchall()]
        cur.close()
        return tables

    finally:
        conn.close()


@mcp.tool()
def describe_table(table_name: str) -> list[dict]:
    """
    Get the schema/columns of a specific table.

    Args:
        table_name: Name of the table to describe

    Returns:
        List of column definitions with name, type, and nullable info
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
        """, (table_name,))
        columns = [dict(row) for row in cur.fetchall()]
        cur.close()

        if not columns:
            raise ValueError(f"Table '{table_name}' not found")

        return columns

    finally:
        conn.close()


if __name__ == "__main__":
    print(f"Starting MCP DB Server on port 3334... DB_HOST={DB_CONFIG['host']}")
    # Run with HTTP transport - clean API!
    mcp.run(transport="http", host="0.0.0.0", port=3334)

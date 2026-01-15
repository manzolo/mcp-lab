"""
MCP File Server - Using Official MCP Python SDK
================================================

This server exposes file system operations as MCP tools using
the official FastMCP framework.

Key Changes from Custom FastAPI Implementation:
- Uses @mcp.tool() decorator instead of manual /tools and /call endpoints
- Schema is auto-generated from Python type hints and docstrings
- Transport layer is handled by the SDK (streamable-http)

Learning Points:
- FastMCP simplifies server creation with decorators
- Type hints are used to generate JSON Schema automatically
- The SDK handles all MCP protocol details
"""

from pathlib import Path
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

# Configure transport security to allow container hostnames
# This is necessary for Docker container communication
transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=[
        "localhost:*",
        "127.0.0.1:*",
        "mcp-file:*",      # Docker container name
        "0.0.0.0:*",
    ],
)

# Initialize the MCP server with security settings
mcp = FastMCP("MCP File Server", transport_security=transport_security)

# Data directory for file access
DATA_DIR = Path("/data")


@mcp.tool()
def read_file(path: str) -> str:
    """
    Read content of a text file from the data directory.

    This tool provides secure file reading with path traversal protection.
    All paths are relative to the /data directory.

    Args:
        path: Relative path to file (e.g., 'notes.txt', 'subdir/file.txt')

    Returns:
        The content of the file as a string

    Raises:
        ValueError: If path attempts directory traversal
        FileNotFoundError: If file doesn't exist
    """
    # Resolve the full path
    requested_path = (DATA_DIR / path).resolve()

    # Security: Prevent path traversal attacks
    if not requested_path.is_relative_to(DATA_DIR):
        raise ValueError("Access denied: Path traversal attempt")

    # Check file exists
    if not requested_path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    # Check it's actually a file
    if not requested_path.is_file():
        raise ValueError(f"Path is not a file: {path}")

    # Read and return content
    return requested_path.read_text(encoding="utf-8")


@mcp.tool()
def list_files(directory: str = "") -> list[str]:
    """
    List files in the data directory or a subdirectory.

    Args:
        directory: Relative path to directory (empty string for root /data)

    Returns:
        List of file and directory names in the specified directory
    """
    target_dir = (DATA_DIR / directory).resolve()

    # Security: Prevent path traversal
    if not target_dir.is_relative_to(DATA_DIR):
        raise ValueError("Access denied: Path traversal attempt")

    if not target_dir.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    if not target_dir.is_dir():
        raise ValueError(f"Path is not a directory: {directory}")

    # List directory contents
    return [item.name for item in target_dir.iterdir()]


if __name__ == "__main__":
    import uvicorn

    print("Starting MCP File Server on port 3333...")

    # Get the ASGI app from FastMCP and run with uvicorn
    # This provides control over host and port
    app = mcp.streamable_http_app()

    uvicorn.run(app, host="0.0.0.0", port=3333)

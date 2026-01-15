"""
MCP Server Integration Tests - Using Official MCP Python SDK
============================================================

This test script verifies that MCP servers are working correctly
using the official MCP Python SDK client.

Key Changes from Custom HTTP Tests:
- Uses official mcp.ClientSession instead of raw HTTP requests
- Supports the streamable-http transport
- Tests the full MCP protocol (initialize, list_tools, call_tool)
"""

import asyncio
import json
import time
import sys
import os

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# Default to localhost for local testing, can be overridden by env vars for container
MCP_FILE_URL = os.environ.get("MCP_FILE_URL", "http://localhost:3333")
MCP_DB_URL = os.environ.get("MCP_DB_URL", "http://localhost:3334")


async def test_server_async(name: str, base_url: str):
    """
    Test an MCP server using the official SDK.

    Args:
        name: Display name of the server
        base_url: Base URL of the server (without /mcp suffix)
    """
    print(f"\n--- Testing {name} Server ({base_url}) ---")

    # Ensure URL has /mcp endpoint
    url = base_url.rstrip('/')
    if not url.endswith('/mcp'):
        url = f"{url}/mcp"

    try:
        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                # 1. Initialize session (required handshake)
                print("Initializing session...")
                await session.initialize()
                print("Session initialized")

                # 2. List tools
                print("Fetching tools...")
                result = await session.list_tools()
                tools = result.tools

                print(f"Found {len(tools)} tools:")
                for tool in tools:
                    print(f"  - {tool.name}: {tool.description[:50]}...")

                # 3. Call a tool based on server type
                if name == "MCP File":
                    tool_name = "read_file"
                    arguments = {"path": "hello.txt"}
                elif name == "MCP DB":
                    tool_name = "query_db"
                    arguments = {"sql": "SELECT * FROM notes LIMIT 3;"}
                else:
                    print(f"Unknown server type: {name}")
                    return

                print(f"\nCalling tool: {tool_name}")
                print(f"Arguments: {json.dumps(arguments)}")

                call_result = await session.call_tool(tool_name, arguments)

                print("Tool call successful!")
                if call_result.content:
                    for item in call_result.content:
                        if hasattr(item, 'text'):
                            # Truncate long results
                            text = item.text
                            if len(text) > 500:
                                text = text[:500] + "..."
                            print(f"Result: {text}")
                        else:
                            print(f"Result: {item}")

    except Exception as e:
        print(f"Error testing {name}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def test_server(name: str, url: str):
    """
    Synchronous wrapper for test_server_async.
    """
    asyncio.run(test_server_async(name, url))


def main():
    print("MCP Server Integration Tests (using official SDK)")
    print("=" * 50)
    print("Waiting for servers to be ready...")
    time.sleep(3)  # Give servers time to start

    args = sys.argv[1:]
    run_all = not args

    if run_all or "file" in args:
        test_server("MCP File", MCP_FILE_URL)
        print("\nMCP File Server: PASSED")

    if run_all or "db" in args:
        test_server("MCP DB", MCP_DB_URL)
        print("\nMCP DB Server: PASSED")

    print("\n" + "=" * 50)
    print("All tests passed!")


if __name__ == "__main__":
    main()

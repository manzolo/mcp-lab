"""
MCP Client - Using Official MCP Python SDK
==========================================

This module handles communication with MCP servers using the official
Model Context Protocol Python SDK.

Key Changes from Custom HTTP Implementation:
- Uses official mcp.ClientSession instead of raw HTTP requests
- Supports multiple transports (streamable-http, sse, stdio)
- Proper async/await pattern for I/O operations
- Built-in protocol handling and error management

Why this exists:
- Provides a standardized interface for tool discovery and execution
- Decouples the agent from specific tool implementations
- Enables dynamic tool registration and discovery
- Makes the system extensible (easy to add new tools)

The MCP Protocol Flow (unchanged):
1. Agent asks: "What tools do you have?" → list_tools()
2. Server responds: "Here's my menu..." → List of tool definitions
3. Agent orders: "Please run this tool" → call_tool()
4. Server delivers: "Here's the result" → Tool result

Learning Points:
- The SDK handles JSON-RPC protocol details internally
- Async programming is essential for efficient I/O
- Transport abstraction allows flexibility (HTTP, stdio, etc.)
- Type safety is improved through Pydantic models

Example:
    client = MCPClient("http://mcp-file:3333")
    tools = await client.get_tools()
    result = await client.call_tool("read_file", {"path": "hello.txt"})
"""

import asyncio
from typing import List, Dict, Any, Optional
from lib.ui import print_success, print_error, print_info
from lib.config import get_config

# Import MCP SDK components
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


class MCPClient:
    """
    Client for communicating with MCP servers using the official SDK.

    This class uses the official MCP Python SDK for communication,
    supporting streamable HTTP transport for HTTP-based MCP servers.

    Attributes:
        server_url: Base URL of the MCP server
        timeout: Request timeout in seconds

    Learning Point:
        The SDK provides ClientSession which handles:
        - Protocol handshake (initialize)
        - Tool discovery (list_tools)
        - Tool execution (call_tool)
        - Proper error handling and types
    """

    def __init__(self, server_url: str, timeout: int = 30):
        """
        Initialize MCP client.

        Args:
            server_url: Base URL of the MCP server (e.g., "http://mcp-file:3333")
            timeout: Request timeout in seconds (default: 30)

        Learning Point:
            The SDK uses async context managers for session management,
            ensuring proper cleanup of resources.
        """
        # Ensure URL ends with /mcp for streamable HTTP endpoint
        self.server_url = server_url.rstrip('/')
        if not self.server_url.endswith('/mcp'):
            self.server_url = f"{self.server_url}/mcp"
        self.timeout = timeout
        self._tools_cache: Optional[List[Dict[str, Any]]] = None

    async def get_tools(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Discover available tools from the MCP server.

        This implements the "discovery" phase of the agent loop using
        the official SDK's list_tools() method.

        Args:
            use_cache: If True, return cached tools (avoids repeated requests)

        Returns:
            List of tool definitions, each containing:
            - name: Tool identifier (e.g., "read_file")
            - description: What the tool does
            - inputSchema: JSON Schema describing required inputs

        Learning Point:
            The SDK returns typed objects (Tool) which we convert to
            dictionaries for compatibility with the rest of the agent.
        """
        if use_cache and self._tools_cache is not None:
            return self._tools_cache

        try:
            print_info(f"Discovering tools from {self.server_url}...")

            async with streamablehttp_client(self.server_url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    # Initialize the session (required handshake)
                    await session.initialize()

                    # List available tools
                    result = await session.list_tools()

                    # Convert SDK Tool objects to dictionaries
                    tools = []
                    for tool in result.tools:
                        tool_dict = {
                            "name": tool.name,
                            "description": tool.description or "",
                            "inputSchema": tool.inputSchema if tool.inputSchema else {
                                "type": "object",
                                "properties": {}
                            }
                        }
                        tools.append(tool_dict)

                    self._tools_cache = tools
                    print_success(f"Loaded {len(tools)} tools from {self.server_url}")
                    return tools

        except Exception as e:
            print_error(f"Failed to discover tools from {self.server_url}: {e}")
            raise ConnectionError(
                f"Cannot connect to MCP server at {self.server_url}\n"
                f"Make sure the server is running: docker compose ps\n"
                f"Technical details: {e}"
            )

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute a tool on the MCP server.

        Args:
            name: Name of the tool to execute
            arguments: Dictionary of arguments to pass to the tool

        Returns:
            Tool execution result (format depends on the tool)

        Learning Point:
            The SDK's call_tool returns a CallToolResult with typed content.
            We extract the content for our agent's use.
        """
        try:
            async with streamablehttp_client(self.server_url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    # Call the tool
                    result = await session.call_tool(name, arguments)

                    # Extract content from result
                    if result.content:
                        # Handle different content types
                        contents = []
                        for item in result.content:
                            if hasattr(item, 'text'):
                                contents.append(item.text)
                            elif hasattr(item, 'data'):
                                contents.append(item.data)
                            else:
                                contents.append(str(item))

                        # Return single item or list
                        if len(contents) == 1:
                            return contents[0]
                        return contents

                    return None

        except Exception as e:
            print_error(f"Failed to call tool {name}: {e}")
            raise

    def clear_cache(self):
        """
        Clear the cached tools.

        Useful when you want to force a refresh of available tools
        (e.g., after restarting a server or adding new tools dynamically).
        """
        self._tools_cache = None


def mcp_to_ollama_tool(mcp_tool: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert MCP tool format to Ollama/OpenAI function calling format.

    MCP and Ollama use slightly different JSON structures for tool definitions.
    This function translates between them.

    MCP Format:
        {
            "name": "read_file",
            "description": "Read a file",
            "inputSchema": {"type": "object", "properties": {...}}
        }

    Ollama Format:
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file",
                "parameters": {"type": "object", "properties": {...}}
            }
        }

    Args:
        mcp_tool: Tool definition in MCP format

    Returns:
        Tool definition in Ollama/OpenAI format

    Learning Point:
        When integrating systems, you often need "adapter" functions that
        translate between different data formats. This is a common pattern
        in software engineering called the "Adapter Pattern".
    """
    return {
        "type": "function",
        "function": {
            "name": mcp_tool["name"],
            "description": mcp_tool["description"],
            "parameters": mcp_tool.get("inputSchema", {"type": "object", "properties": {}})
        }
    }


async def _discover_all_tools_async() -> tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Async implementation of tool discovery from all configured MCP servers.

    Returns:
        Tuple of:
        - List of tools in Ollama format
        - Dict mapping tool names to server URLs (for routing)
    """
    config = get_config()

    all_mcp_tools = []
    server_map = {}

    # Query file server
    try:
        file_client = MCPClient(config.mcp_file_url, timeout=30)
        file_tools = await file_client.get_tools()
        all_mcp_tools.extend(file_tools)

        # Add to server map (use the client's adjusted URL)
        for tool in file_tools:
            server_map[tool["name"]] = file_client.server_url

    except Exception as e:
        print_error(f"Failed to load tools from file server: {e}")
        # Continue anyway - maybe DB server works

    # Query database server
    try:
        db_client = MCPClient(config.mcp_db_url, timeout=30)
        db_tools = await db_client.get_tools()
        all_mcp_tools.extend(db_tools)

        # Add to server map (use the client's adjusted URL)
        for tool in db_tools:
            server_map[tool["name"]] = db_client.server_url

    except Exception as e:
        print_error(f"Failed to load tools from database server: {e}")
        # Continue anyway

    # Convert to Ollama format
    ollama_tools = [mcp_to_ollama_tool(tool) for tool in all_mcp_tools]

    print_info(f"Total tools available: {len(ollama_tools)}")

    return ollama_tools, server_map


def discover_all_tools() -> tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Discover tools from all configured MCP servers.

    This is a convenience function that wraps the async implementation
    for use in synchronous code.

    Returns:
        Tuple of:
        - List of tools in Ollama format
        - Dict mapping tool names to server URLs (for routing)

    Learning Point:
        The MCP SDK uses async/await for I/O operations, but our agent
        is synchronous. We bridge this gap with asyncio.run().
    """
    return asyncio.run(_discover_all_tools_async())

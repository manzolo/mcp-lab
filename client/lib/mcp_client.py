"""
MCP Client - Model Context Protocol Implementation
==================================================

The Model Context Protocol (MCP) is a standard way for AI agents
to discover and use external tools.

Why this exists:
- Provides a standardized interface for tool discovery and execution
- Decouples the agent from specific tool implementations
- Enables dynamic tool registration and discovery
- Makes the system extensible (easy to add new tools)

Key Concepts:
- **Protocol**: A standardized way for systems to communicate
- **Tool Discovery**: Finding out what capabilities are available
- **Schema**: A structured description of data (JSON Schema for tools)
- **Client-Server Pattern**: MCP client (agent) talks to MCP servers (tools)

The MCP Protocol Flow:
1. Agent asks: "What tools do you have?" → GET /tools
2. Server responds: "Here's my menu..." → JSON list of tools
3. Agent orders: "Please run this tool" → POST /call
4. Server delivers: "Here's the result" → JSON response

Think of it like a restaurant:
- Menu (GET /tools): List of available dishes with descriptions
- Order (POST /call): Requesting a specific dish with customizations
- Delivery (Response): Getting the prepared dish

Learning Points:
- MCP is similar to OpenAPI/Swagger for REST APIs
- The protocol is simple by design (2 endpoints!)
- JSON Schema describes inputs, making tools self-documenting
- This pattern enables tool marketplaces (like an "app store" for AI tools)

Example:
    client = MCPClient("http://mcp-file:3333")
    tools = client.get_tools()
    # Returns: [{"name": "read_file", "description": "...", ...}]
"""

import requests
from typing import List, Dict, Any, Optional
from lib.ui import print_success, print_error, print_info
from lib.config import get_config


class MCPClient:
    """
    Client for communicating with MCP (Model Context Protocol) servers.

    An MCP server exposes tools that an AI agent can use. This client
    handles the communication: discovering tools and executing them.

    Attributes:
        server_url: Base URL of the MCP server
        timeout: Request timeout in seconds

    Learning Point:
        Using a class (instead of functions) allows us to:
        - Store state (URL, timeout, cache)
        - Group related operations
        - Create multiple clients for different servers
        - Easily mock for testing
    """

    def __init__(self, server_url: str, timeout: int = 5):
        """
        Initialize MCP client.

        Args:
            server_url: Base URL of the MCP server (e.g., "http://mcp-file:3333")
            timeout: Request timeout in seconds (default: 5)

        Learning Point:
            Timeouts are crucial! Without them, a slow/dead server can hang
            your entire application. Always set reasonable timeouts.
        """
        self.server_url = server_url.rstrip('/')  # Remove trailing slash
        self.timeout = timeout
        self._tools_cache: Optional[List[Dict[str, Any]]] = None

    def get_tools(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Discover available tools from the MCP server.

        This implements the "discovery" phase of the agent loop.
        The server returns a list of tools with their schemas.

        Args:
            use_cache: If True, return cached tools (avoids repeated requests)

        Returns:
            List of tool definitions, each containing:
            - name: Tool identifier (e.g., "read_file")
            - description: What the tool does
            - inputSchema: JSON Schema describing required inputs

        Raises:
            ConnectionError: If cannot connect to server
            ValueError: If server returns invalid response

        Learning Point:
            Tool discovery happens ONCE at agent startup, not every time
            the agent thinks. This is more efficient and reduces latency.

        Example:
            >>> client = MCPClient("http://mcp-file:3333")
            >>> tools = client.get_tools()
            >>> print(tools[0]["name"])
            'read_file'
        """
        # Return cached tools if available
        if use_cache and self._tools_cache is not None:
            return self._tools_cache

        try:
            print_info(f"Discovering tools from {self.server_url}...")
            response = requests.get(
                f"{self.server_url}/tools",
                timeout=self.timeout
            )
            response.raise_for_status()

            tools = response.json()

            # Validate response format
            if not isinstance(tools, list):
                raise ValueError(f"Expected list of tools, got {type(tools)}")

            # Cache the tools
            self._tools_cache = tools

            print_success(f"Loaded {len(tools)} tools from {self.server_url}")
            return tools

        except requests.exceptions.Timeout:
            print_error(f"Timeout connecting to {self.server_url}")
            raise ConnectionError(
                f"MCP server at {self.server_url} did not respond in {self.timeout}s\n"
                f"The server might be down or too slow."
            )

        except requests.exceptions.ConnectionError as e:
            print_error(f"Cannot connect to {self.server_url}")
            raise ConnectionError(
                f"Cannot connect to MCP server at {self.server_url}\n"
                f"Make sure the server is running: docker compose ps\n"
                f"Technical details: {e}"
            )

        except requests.exceptions.HTTPError as e:
            print_error(f"HTTP error from {self.server_url}: {e}")
            raise ValueError(f"MCP server returned error: {e}")

        except Exception as e:
            print_error(f"Unexpected error from {self.server_url}: {e}")
            raise

    def clear_cache(self):
        """
        Clear the cached tools.

        Useful when you want to force a refresh of available tools
        (e.g., after restarting a server or adding new tools dynamically).

        Learning Point:
            Caching improves performance but can cause stale data issues.
            Always provide a way to invalidate the cache!
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

    Example:
        >>> mcp_tool = {"name": "read_file", "description": "...", "inputSchema": {...}}
        >>> ollama_tool = mcp_to_ollama_tool(mcp_tool)
        >>> ollama_tool["type"]
        'function'
    """
    return {
        "type": "function",
        "function": {
            "name": mcp_tool["name"],
            "description": mcp_tool["description"],
            "parameters": mcp_tool["inputSchema"]
        }
    }


def discover_all_tools() -> tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Discover tools from all configured MCP servers.

    This is a convenience function that:
    1. Gets the list of MCP server URLs from config
    2. Queries each server for its tools
    3. Converts tools to Ollama format
    4. Returns both the tool list and a routing map

    Returns:
        Tuple of:
        - List of tools in Ollama format
        - Dict mapping tool names to server URLs (for routing)

    Learning Point:
        "Convenience functions" wrap common multi-step operations.
        They make the calling code cleaner and more readable.

    Example:
        >>> tools, server_map = discover_all_tools()
        >>> print(f"Found {len(tools)} tools total")
        >>> print(server_map["read_file"])
        'http://mcp-file:3333'
    """
    config = get_config()

    all_mcp_tools = []
    server_map = {}

    # Query file server
    try:
        file_client = MCPClient(config.mcp_file_url, timeout=5)
        file_tools = file_client.get_tools()
        all_mcp_tools.extend(file_tools)

        # Add to server map
        for tool in file_tools:
            server_map[tool["name"]] = config.mcp_file_url

    except Exception as e:
        print_error(f"Failed to load tools from file server: {e}")
        # Continue anyway - maybe DB server works

    # Query database server
    try:
        db_client = MCPClient(config.mcp_db_url, timeout=5)
        db_tools = db_client.get_tools()
        all_mcp_tools.extend(db_tools)

        # Add to server map
        for tool in db_tools:
            server_map[tool["name"]] = config.mcp_db_url

    except Exception as e:
        print_error(f"Failed to load tools from database server: {e}")
        # Continue anyway

    # Convert to Ollama format
    ollama_tools = [mcp_to_ollama_tool(tool) for tool in all_mcp_tools]

    print_info(f"Total tools available: {len(ollama_tools)}")

    return ollama_tools, server_map

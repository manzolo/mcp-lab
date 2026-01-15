"""
Tool Router - Using Official MCP Python SDK
============================================

The Tool Router directs tool calls to the appropriate MCP server
using the official MCP Python SDK.

Key Changes from Custom HTTP Implementation:
- Uses MCPClient.call_tool() instead of raw HTTP POST requests
- Async/await pattern for efficient I/O
- SDK handles JSON-RPC protocol details

Why this exists:
- Multiple MCP servers offer different tools
- Each tool lives on a specific server (URL)
- The agent needs a directory: "read_file → http://mcp-file:3333/mcp"
- Routing logic should be separate from execution logic

Design Pattern: Command Router
- Input: Tool name + Arguments
- Logic: Look up server URL in registry
- Action: Use MCP SDK to call tool
- Output: Return result or error

Learning Points:
- This pattern is common in microservices architecture
- The SDK provides proper protocol handling
- Error handling is crucial - tools can fail for many reasons
"""

import asyncio
import json
from typing import Dict, Any, List
from lib.ui import print_tool_exec, print_error, print_success
from lib.sanitizers import fix_sql_args, validate_tool_arguments, sanitize_output
from lib.mcp_client import MCPClient


class ToolRouter:
    """
    Routes and executes tool calls to appropriate MCP servers using the SDK.

    This class maintains a registry of tools and their server URLs,
    and uses the MCP SDK for actual tool execution.

    Attributes:
        server_map: Dict mapping tool names to server URLs
        timeout: Request timeout in seconds
        _clients: Cache of MCPClient instances per server

    Learning Point:
        Using the SDK provides:
        - Proper protocol handling
        - Type-safe communication
        - Better error messages
    """

    def __init__(self, server_map: Dict[str, str], timeout: int = 30):
        """
        Initialize the tool router.

        Args:
            server_map: Dictionary mapping tool names to server URLs
                Example: {"read_file": "http://mcp-file:3333/mcp", ...}
            timeout: Request timeout in seconds (default: 30)

        Learning Point:
            We cache MCPClient instances to avoid recreating them
            for each tool call, though the SDK handles connection pooling.
        """
        self.server_map = server_map
        self.timeout = timeout
        self._clients: Dict[str, MCPClient] = {}

    def _get_client(self, server_url: str) -> MCPClient:
        """
        Get or create an MCPClient for a server URL.

        Args:
            server_url: URL of the MCP server

        Returns:
            MCPClient instance for the server
        """
        if server_url not in self._clients:
            self._clients[server_url] = MCPClient(server_url, timeout=self.timeout)
        return self._clients[server_url]

    def route(self, tool_name: str) -> str:
        """
        Find the server URL for a given tool name.

        Args:
            tool_name: Name of the tool (e.g., "read_file")

        Returns:
            Server URL that handles this tool

        Raises:
            KeyError: If tool is not registered
        """
        if tool_name not in self.server_map:
            raise KeyError(
                f"Tool '{tool_name}' not found in registry.\n"
                f"Available tools: {', '.join(self.server_map.keys())}"
            )

        return self.server_map[tool_name]

    async def _execute_tool_async(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Async implementation of tool execution.

        Args:
            tool_name: Name of the tool to execute
            arguments: Dictionary of arguments to pass to the tool

        Returns:
            Tool execution result
        """
        print_tool_exec(f"Calling: {tool_name}")
        print(f"      Args: {json.dumps(arguments)}")

        try:
            # Step 1: Validate arguments (security)
            validate_tool_arguments(tool_name, arguments)

            # Step 2: Sanitize arguments (fix LLM quirks)
            if tool_name == "query_db":
                arguments = fix_sql_args(arguments)

            # Step 3: Route to correct server
            server_url = self.route(tool_name)

            # Step 4: Get client and call tool
            client = self._get_client(server_url)
            result = await client.call_tool(tool_name, arguments)

            # Step 5: Format and sanitize result
            # Convert to dict format for consistency
            if isinstance(result, str):
                result = {"content": result}
            elif isinstance(result, list):
                result = {"data": result}
            elif result is None:
                result = {"status": "success"}

            result = sanitize_output(result)

            # Show truncated result for logging
            result_str = json.dumps(result)
            truncated = result_str[:150] + "..." if len(result_str) > 150 else result_str
            print_success(f"Result: {truncated}")

            return result

        except KeyError as e:
            print_error(str(e))
            raise

        except Exception as e:
            error_msg = f"Tool '{tool_name}' failed: {e}"
            print_error(error_msg)
            raise ValueError(error_msg)

    def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a single tool call.

        This wraps the async implementation for synchronous use.

        Args:
            tool_name: Name of the tool to execute
            arguments: Dictionary of arguments to pass to the tool

        Returns:
            Tool execution result (format depends on the tool)

        Raises:
            KeyError: If tool not found in registry
            ValueError: If tool execution fails
        """
        return asyncio.run(self._execute_tool_async(tool_name, arguments))

    def execute_tools(
        self,
        tool_calls: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple tool calls sequentially.

        This handles the case where the LLM requests multiple tools
        in a single response. Tools are executed in order.

        Args:
            tool_calls: List of tool call objects, each containing:
                - function.name: Tool name
                - function.arguments: Tool arguments

        Returns:
            List of results in same order as tool_calls

        Learning Point:
            Sequential execution is simple but can be slow.
            In production, you might execute tools in parallel
            using asyncio.gather().
        """
        results = []

        for tool_call in tool_calls:
            func_name = tool_call["function"]["name"]
            raw_args = tool_call["function"]["arguments"]

            # Normalize arguments (handle Ollama quirks)
            # Sometimes Ollama wraps values in {"value": actual_value}
            normalized_args = {}
            for key, value in raw_args.items():
                if isinstance(value, dict) and "value" in value:
                    normalized_args[key] = value["value"]
                else:
                    normalized_args[key] = value

            # Execute tool
            try:
                result = self.execute_tool(func_name, normalized_args)
                results.append(result)
            except Exception as e:
                # Return error as a result (don't crash the whole loop)
                error_result = {
                    "error": str(e),
                    "tool": func_name
                }
                results.append(error_result)

        return results

    def format_tool_results_for_llm(
        self,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """
        Format tool results as messages for the LLM.

        The LLM needs tool results in a specific format to understand them.
        This converts raw tool results into LLM messages.

        Args:
            results: List of tool execution results

        Returns:
            List of message objects with role="tool"
        """
        messages = []

        for result in results:
            # Convert result to string (JSON format)
            content_str = json.dumps(result)

            # Create tool result message
            messages.append({
                "role": "tool",
                "content": content_str
            })

        return messages

    def register_tool(self, tool_name: str, server_url: str):
        """
        Register a new tool dynamically.

        Args:
            tool_name: Name of the tool
            server_url: URL of the server that hosts this tool
        """
        self.server_map[tool_name] = server_url
        print_success(f"Registered tool '{tool_name}' at {server_url}")

    def unregister_tool(self, tool_name: str):
        """
        Remove a tool from the registry.

        Args:
            tool_name: Name of the tool to remove
        """
        if tool_name in self.server_map:
            del self.server_map[tool_name]
            print_success(f"Unregistered tool '{tool_name}'")
        else:
            print_error(f"Tool '{tool_name}' not found in registry")

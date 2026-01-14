"""
Tool Router - Directing Traffic to the Right Server
===================================================

The Tool Router is like a post office: it knows which server handles
which tools and delivers requests to the right place.

Why this exists:
- Multiple MCP servers offer different tools
- Each tool lives on a specific server (URL)
- The agent needs a directory: "read_file → http://mcp-file:3333"
- Routing logic should be separate from execution logic

Key Concepts:
- **Routing**: Directing requests to the correct destination
- **Service Registry**: A map of services and their locations
- **Command Pattern**: Encapsulating tool calls as objects
- **Error Handling**: What to do when a tool fails

Design Pattern: Command Router
- Input: Tool name + Arguments
- Logic: Look up server URL in registry
- Action: Send HTTP request to server
- Output: Return result or error

Learning Points:
- This pattern is common in microservices architecture
- Routing can be static (hardcoded) or dynamic (service discovery)
- In production, you might use a service mesh (Istio, Linkerd)
- Error handling is crucial - tools can fail for many reasons

Real-World Example:
    When you order from Uber Eats, the app routes your request to:
    - Restaurant service (to place the order)
    - Payment service (to process payment)
    - Delivery service (to assign a driver)

    The app is a "router" that knows where each request should go!
"""

import requests
import json
from typing import Dict, Any, List
from lib.ui import print_tool_exec, print_error, print_success
from lib.sanitizers import fix_sql_args, validate_tool_arguments, sanitize_output


class ToolRouter:
    """
    Routes and executes tool calls to appropriate MCP servers.

    This class maintains a registry of tools and their server URLs,
    and handles the actual HTTP communication when executing tools.

    Attributes:
        server_map: Dict mapping tool names to server URLs
        timeout: Request timeout in seconds

    Learning Point:
        Separating routing logic from business logic makes the code:
        - Easier to test (mock the router)
        - Easier to modify (change routing without touching agent logic)
        - More flexible (add new tools without changing core code)
    """

    def __init__(self, server_map: Dict[str, str], timeout: int = 10):
        """
        Initialize the tool router.

        Args:
            server_map: Dictionary mapping tool names to server URLs
                Example: {"read_file": "http://mcp-file:3333", ...}
            timeout: Request timeout in seconds (default: 10)

        Learning Point:
            Tool execution can take longer than tool discovery, so we
            use a longer timeout (10s vs 5s for discovery).
        """
        self.server_map = server_map
        self.timeout = timeout

    def route(self, tool_name: str) -> str:
        """
        Find the server URL for a given tool name.

        Args:
            tool_name: Name of the tool (e.g., "read_file")

        Returns:
            Server URL that handles this tool

        Raises:
            KeyError: If tool is not registered

        Learning Point:
            This is a simple routing strategy (dictionary lookup).
            More advanced routing might consider:
            - Load balancing (multiple servers for same tool)
            - Health checks (route to healthy servers only)
            - Geographic proximity (route to nearest server)
        """
        if tool_name not in self.server_map:
            raise KeyError(
                f"Tool '{tool_name}' not found in registry.\n"
                f"Available tools: {', '.join(self.server_map.keys())}"
            )

        return self.server_map[tool_name]

    def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a single tool call.

        This is the core of the "Execution" phase in the agent loop.
        It takes a tool call from the LLM and actually runs it.

        Process:
        1. Validate arguments (security check)
        2. Sanitize arguments (fix common LLM mistakes)
        3. Route to correct server
        4. Make HTTP POST request
        5. Handle errors gracefully
        6. Return sanitized result

        Args:
            tool_name: Name of the tool to execute
            arguments: Dictionary of arguments to pass to the tool

        Returns:
            Tool execution result (format depends on the tool)

        Raises:
            KeyError: If tool not found in registry
            ConnectionError: If cannot connect to server
            ValueError: If server returns error

        Learning Point:
            Tool execution is the most error-prone part of the agent loop:
            - Network can fail
            - Server can be down
            - Arguments can be invalid
            - Tool can timeout
            Good error handling is essential!

        Example:
            >>> router = ToolRouter({"read_file": "http://mcp-file:3333"})
            >>> result = router.execute_tool("read_file", {"path": "hello.txt"})
            >>> print(result["content"])
            'Hello from MCP File Server!'
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

            # Step 4: Make HTTP request
            response = requests.post(
                f"{server_url}/call",
                json={
                    "name": tool_name,
                    "arguments": arguments
                },
                timeout=self.timeout
            )

            # Step 5: Handle HTTP errors
            if response.status_code != 200:
                error_msg = response.text
                print_error(f"Tool execution failed: {error_msg}")
                raise ValueError(f"Tool '{tool_name}' failed: {error_msg}")

            # Step 6: Parse and sanitize result
            result = response.json()
            result = sanitize_output(result)

            # Show truncated result for logging
            result_str = json.dumps(result)
            truncated = result_str[:150] + "..." if len(result_str) > 150 else result_str
            print_success(f"Result: {truncated}")

            return result

        except requests.exceptions.Timeout:
            error_msg = f"Tool '{tool_name}' timed out after {self.timeout}s"
            print_error(error_msg)
            raise ConnectionError(error_msg)

        except requests.exceptions.ConnectionError as e:
            error_msg = f"Cannot connect to server for tool '{tool_name}'"
            print_error(error_msg)
            raise ConnectionError(f"{error_msg}: {e}")

        except KeyError as e:
            print_error(str(e))
            raise

        except Exception as e:
            print_error(f"Unexpected error executing '{tool_name}': {e}")
            raise

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
            In production, you might:
            - Execute tools in parallel (concurrent HTTP requests)
            - Use async/await for better performance
            - Implement a dependency graph (some tools depend on others)

        Example:
            >>> tool_calls = [
            ...     {"function": {"name": "read_file", "arguments": {"path": "a.txt"}}},
            ...     {"function": {"name": "read_file", "arguments": {"path": "b.txt"}}}
            ... ]
            >>> results = router.execute_tools(tool_calls)
            >>> len(results)
            2
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

        Learning Point:
            Different LLMs expect tool results in different formats:
            - OpenAI: {"role": "tool", "content": "...", "tool_call_id": "..."}
            - Anthropic: {"role": "user", "content": [{"type": "tool_result", ...}]}
            - Ollama: {"role": "tool", "content": "..."}

            This is why abstraction layers (like LangChain) exist!

        Example:
            >>> results = [{"content": "Hello"}]
            >>> messages = router.format_tool_results_for_llm(results)
            >>> messages[0]["role"]
            'tool'
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

        This allows adding tools at runtime without restarting the agent.

        Args:
            tool_name: Name of the tool
            server_url: URL of the server that hosts this tool

        Learning Point:
            Dynamic registration enables:
            - Hot-reloading (add tools without restart)
            - Plugin systems (third-party tools)
            - A/B testing (route some traffic to new versions)

        Example:
            >>> router.register_tool("weather", "http://mcp-weather:3335")
            >>> router.route("weather")
            'http://mcp-weather:3335'
        """
        self.server_map[tool_name] = server_url
        print_success(f"Registered tool '{tool_name}' at {server_url}")

    def unregister_tool(self, tool_name: str):
        """
        Remove a tool from the registry.

        Args:
            tool_name: Name of the tool to remove

        Learning Point:
            Graceful shutdown requires cleaning up registrations.
            Otherwise, the agent might try to call a tool that no longer exists!
        """
        if tool_name in self.server_map:
            del self.server_map[tool_name]
            print_success(f"Unregistered tool '{tool_name}'")
        else:
            print_error(f"Tool '{tool_name}' not found in registry")

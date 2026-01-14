"""
Error Handling - Making Failures Educational
============================================

This module defines custom exceptions with educational error messages.

Why this exists:
- Error messages are learning opportunities
- Good errors explain WHAT, WHY, and HOW TO FIX
- Custom exceptions provide context-specific guidance
- Educational errors reduce frustration for learners

Key Concepts:
- **Exception Hierarchy**: Base class → Specific exceptions
- **Error Context**: Include what went wrong and how to fix it
- **Fail Fast**: Detect errors early with clear messages
- **User-Friendly**: Technical details available but not overwhelming

Learning Points:
- In production, errors should be:
  * Actionable (tell user what to do)
  * Specific (not generic "Error occurred")
  * Logged (for debugging)
  * User-appropriate (hide internals from end users)

Error Message Template:
    [Error Type]: [What went wrong]

    📚 What does this mean?
       [Plain-language explanation]

    🔧 How to fix:
       Option 1: [Command or action]
       Option 2: [Alternative]

    🔍 Technical details:
       [For advanced users]

    📖 Learn more: [Link to documentation]

Real-World Example:
    Instead of: "Connection refused"
    We show: "Could not connect to Ollama at http://localhost:11434

             📚 What does this mean?
                The agent needs Ollama (the LLM) to be running, but
                it couldn't find it at the configured address.

             🔧 How to fix:
                Option 1: Start Ollama locally
                  → Run: ollama serve

                Option 2: Use containerized Ollama
                  → Run: make up-local

                Option 3: Check your configuration
                  → Verify OLLAMA_URL in .env file

             📖 Learn more: README.md section 'Ollama Configuration'"
"""


class MCPError(Exception):
    """
    Base exception for all MCP Lab errors.

    All custom exceptions inherit from this class, making it easy to
    catch all MCP-specific errors with a single except clause.

    Learning Point:
        Exception hierarchies allow catching errors at different levels:
        - Catch MCPError: Handle all MCP errors
        - Catch specific errors: Handle only certain types

    Example:
        try:
            agent.run()
        except MCPError as e:
            print(f"MCP error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
    """
    pass


class ConfigurationError(MCPError):
    """
    Raised when configuration is invalid or incomplete.

    This error appears early (during startup) when the system detects
    missing or invalid configuration.

    Learning Point:
        Validating configuration at startup (fail fast) is better than
        failing deep in the application with a confusing error.
    """

    def __init__(self, missing_var: str, current_value: str = None):
        """
        Create a configuration error with helpful guidance.

        Args:
            missing_var: Name of the missing/invalid configuration variable
            current_value: Current value (if any) that's invalid
        """
        message = f"Configuration Error: {missing_var} is not set correctly"

        if current_value:
            message += f"\nCurrent value: {current_value}"

        message += f"""

📚 What does this mean?
   The agent needs configuration to know where to find services.
   Configuration is stored in environment variables (from .env file).

🔧 How to fix:
   Option 1 (Recommended): Run the setup wizard
     → make wizard

   Option 2: Manually create/edit .env file
     → Copy .env.dist to .env
     → Set {missing_var} to the correct value

   Option 3: Set environment variable directly
     → export {missing_var}=<your_value>

📖 Learn more: README.md section 'Configuration Guide'
"""
        super().__init__(message)


class LLMConnectionError(MCPError):
    """
    Raised when cannot connect to Ollama (the LLM).

    This is one of the most common errors for new users, so we provide
    extensive troubleshooting guidance.
    """

    def __init__(self, url: str, details: str = ""):
        """
        Create an LLM connection error with troubleshooting steps.

        Args:
            url: The Ollama URL that failed to connect
            details: Optional technical details about the error
        """
        message = f"Cannot connect to Ollama at {url}"

        message += """

📚 What is Ollama?
   Ollama is the 'brain' - the LLM (Large Language Model) that powers
   the agent. Without it, the agent cannot reason or make decisions.

🔧 How to fix:

   Option 1 (Recommended for beginners):
     Start Ollama in a Docker container
     → make up-local

   Option 2 (If you have Ollama installed locally):
     Start Ollama on your host machine
     → ollama serve
     Then make sure OLLAMA_URL in .env points to: http://host.docker.internal:11434

   Option 3 (Using a remote Ollama):
     Update OLLAMA_URL in .env to point to your Ollama instance
     → OLLAMA_URL=http://your-server:11434

   Check if Ollama is running:
     → docker compose ps  (for containerized)
     → curl http://localhost:11434/api/version  (for local)
"""

        if details:
            message += f"""
🔍 Technical details:
   {details}
"""

        message += """
📖 Learn more: README.md section 'Troubleshooting'
"""
        super().__init__(message)


class MCPServerError(MCPError):
    """
    Raised when an MCP server (tool server) has problems.

    MCP servers provide the "tools" (file access, database, etc.).
    If they're down, the agent can't perform actions.
    """

    def __init__(self, server_name: str, server_url: str, details: str = ""):
        """
        Create an MCP server error with troubleshooting.

        Args:
            server_name: Friendly name (e.g., "File Server")
            server_url: URL that failed
            details: Optional technical details
        """
        message = f"Cannot connect to {server_name} at {server_url}"

        message += f"""

📚 What does this mean?
   MCP servers provide "tools" that the agent uses to take actions.
   The {server_name} is needed for certain operations but isn't responding.

🔧 How to fix:

   1. Check if services are running:
      → docker compose ps

   2. If services are stopped, start them:
      → make up

   3. If services are running but unhealthy, restart them:
      → make down
      → make up

   4. Check server logs for errors:
      → docker compose logs {server_name.lower().replace(' ', '-')}

   5. Verify network connectivity:
      → docker compose exec mcp-agent ping {server_name.lower().replace(' ', '-')}
"""

        if details:
            message += f"""
🔍 Technical details:
   {details}
"""

        message += """
📖 Learn more: README.md section 'Troubleshooting'
"""
        super().__init__(message)


class ToolExecutionError(MCPError):
    """
    Raised when a tool fails to execute properly.

    Tools can fail for many reasons: invalid arguments, permission issues,
    resource not found, etc. This error provides context about what went wrong.
    """

    def __init__(self, tool_name: str, reason: str, arguments: dict = None):
        """
        Create a tool execution error.

        Args:
            tool_name: Name of the tool that failed
            reason: Why it failed
            arguments: Arguments that were passed (optional)
        """
        message = f"Tool '{tool_name}' failed to execute"

        message += f"""

📚 What happened?
   The agent tried to use the '{tool_name}' tool, but it failed:
   {reason}
"""

        if arguments:
            message += f"""
   Arguments provided:
   {arguments}
"""

        message += f"""
🔧 How to fix:

   Common issues with {tool_name}:
"""

        # Tool-specific guidance
        if tool_name == "read_file":
            message += """
      • File doesn't exist: Check the file path
        → ls mcp-file/data/

      • Path traversal blocked: Use relative paths only
        → Good: "notes.txt"
        → Bad: "../../etc/passwd"

      • File too large: Current limit is 10MB
        → Check file size: ls -lh mcp-file/data/
"""

        elif tool_name == "query_db":
            message += """
      • SQL syntax error: Check your query syntax
        → PostgreSQL docs: https://www.postgresql.org/docs/

      • Missing quotes: String literals need quotes
        → Good: WHERE title = 'Shopping'
        → Bad: WHERE title = Shopping

      • Table doesn't exist: Check available tables
        → Run: make agent MSG="What tables are in the database?"

      • Permission denied: Query might be blocked by security rules
        → Check if using DROP, DELETE, or ALTER
"""

        else:
            message += f"""
      • Check that the tool server is running: docker compose ps
      • Check server logs: docker compose logs
      • Verify arguments match the tool's schema
"""

        message += """
📖 Learn more: README.md section 'Adding Tools'
"""
        super().__init__(message)


class ModelNotFoundError(MCPError):
    """
    Raised when the specified model doesn't exist in Ollama.

    Users might configure a model name that hasn't been downloaded yet.
    """

    def __init__(self, model_name: str):
        """
        Create a model not found error.

        Args:
            model_name: Name of the model that wasn't found
        """
        message = f"Model '{model_name}' not found in Ollama"

        message += f"""

📚 What does this mean?
   Ollama needs to download models before they can be used.
   The model '{model_name}' hasn't been downloaded yet.

🔧 How to fix:

   Option 1: Pull the model
     → docker compose exec ollama ollama pull {model_name}

   Option 2: Use a different model
     Update MODEL_NAME in .env to one you have:
     → ollama list  (see available models)

   Option 3: Use recommended model for learning
     → export MODEL_NAME=llama3.2:3b
     → docker compose exec ollama ollama pull llama3.2:3b

   Popular models:
     • llama3.2:3b  - Fast, good for learning (2GB)
     • llama3.2:7b  - Better quality (4GB)
     • llama3:70b   - Production quality (40GB)

📖 Learn more: README.md section 'Model Selection'
"""
        super().__init__(message)


def handle_error(error: Exception) -> str:
    """
    Convert any exception into a user-friendly error message.

    This function is the "last resort" error handler. It catches any
    exception and tries to provide helpful guidance.

    Args:
        error: The exception that was raised

    Returns:
        User-friendly error message

    Learning Point:
        Centralized error handling ensures consistent error messages
        across the application. Users get the same quality of help
        regardless of where the error occurred.

    Example:
        try:
            agent.run()
        except Exception as e:
            print(handle_error(e))
    """
    # If it's already one of our custom exceptions, just return its message
    if isinstance(error, MCPError):
        return str(error)

    # Otherwise, wrap it in a generic but helpful message
    return f"""
Unexpected Error: {type(error).__name__}

📚 What happened?
   An unexpected error occurred: {str(error)}

🔧 What to try:

   1. Check if all services are running:
      → make test-servers

   2. Review recent changes:
      → What did you change before this error?

   3. Check logs:
      → docker compose logs

   4. Restart everything:
      → make down
      → make up

   5. If the error persists, it might be a bug:
      → Check GitHub issues: https://github.com/yourname/mcp-lab/issues
      → Include this error message and steps to reproduce

🔍 Technical details:
   Error type: {type(error).__name__}
   Error message: {str(error)}

   Stack trace (for debugging):
   {error}

📖 Learn more: README.md section 'Troubleshooting'
"""

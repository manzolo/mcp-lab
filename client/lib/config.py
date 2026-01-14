"""
Configuration Management for MCP Agent
======================================

This module centralizes all configuration for the MCP Agent.

Why this exists:
- Configuration should be separate from code for security and flexibility
- Environment variables allow same code to run in different environments
- Validation catches configuration errors early, before they cause problems
- Centralized config makes it easy to understand what settings exist

Key Concepts:
- Environment Variables: OS-level key-value pairs (e.g., OLLAMA_URL=http://localhost:11434)
- Configuration as Code: Using Python classes to represent and validate config
- Fail Fast: Validate configuration at startup, not during operation
- Sensible Defaults: Provide reasonable defaults for common cases

Learning Points:
- In production systems, never hardcode URLs, credentials, or environment-specific values
- The 12-Factor App methodology recommends storing config in environment variables
- Configuration validation prevents "works on my machine" problems

Example:
    from lib.config import get_config

    config = get_config()
    print(config.ollama_url)  # http://localhost:11434
    print(config.model_name)  # llama3.2:3b
"""

import os
from typing import Dict


class AppConfig:
    """
    Application Configuration

    This class loads and validates all configuration from environment variables.
    It provides sensible defaults for common development scenarios.

    Attributes:
        ollama_url: URL of the Ollama server (the LLM "brain")
        model_name: Name of the model to use (e.g., llama3.2:3b)
        mcp_file_url: URL of the file MCP server
        mcp_db_url: URL of the database MCP server
        server_map: Mapping of tool names to their server URLs

    Learning Point:
        Using a class for configuration (instead of global variables) makes
        testing easier and allows multiple configurations in one program.
    """

    def __init__(self):
        """
        Initialize configuration from environment variables.

        Loads all required settings and provides defaults for common cases.
        Validates that critical settings are present.

        Raises:
            ValueError: If required configuration is missing
        """
        # Ollama Configuration
        # The "brain" that powers the agent - where the LLM runs
        self.ollama_url = os.environ.get("OLLAMA_URL", "https://myollama.my.address.it")

        # Model selection - smaller models are faster but less capable
        # llama3.2:3b is a good balance for learning (2GB RAM, fast responses)
        self.model_name = os.environ.get("MODEL_NAME", "llama3")

        # MCP Server URLs
        # These are the "tools" that the agent can use
        # Default to Docker Compose service names for containerized setup
        self.mcp_file_url = os.environ.get("MCP_FILE_URL", "http://mcp-file:3333")
        self.mcp_db_url = os.environ.get("MCP_DB_URL", "http://mcp-db:3334")

        # Server Map: Tool Name → Server URL
        # This tells the agent which server to call for each tool
        # In a dynamic system, this might be discovered automatically
        self.server_map: Dict[str, str] = {
            "read_file": self.mcp_file_url,
            "query_db": self.mcp_db_url
        }

    def validate(self) -> bool:
        """
        Validate that critical configuration is present and reasonable.

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If configuration is invalid

        Learning Point:
            Validating configuration at startup prevents cryptic errors later.
            It's better to fail fast with a clear message than to fail deep
            in the application with a confusing error.
        """
        if not self.ollama_url:
            raise ValueError(
                "OLLAMA_URL not set. Please configure the Ollama endpoint.\n"
                "Example: export OLLAMA_URL=http://localhost:11434"
            )

        if not self.model_name:
            raise ValueError(
                "MODEL_NAME not set. Please specify which model to use.\n"
                "Example: export MODEL_NAME=llama3.2:3b"
            )

        # Basic URL format validation
        if not self.ollama_url.startswith(("http://", "https://")):
            raise ValueError(
                f"Invalid OLLAMA_URL: {self.ollama_url}\n"
                "URL must start with http:// or https://"
            )

        return True

    def summary(self) -> str:
        """
        Get a human-readable summary of the current configuration.

        Returns:
            String describing the configuration

        Learning Point:
            Configuration summaries are helpful for debugging and logging.
            Users can quickly see what settings are active.
        """
        return (
            "MCP Agent Configuration:\n"
            f"  Ollama URL: {self.ollama_url}\n"
            f"  Model: {self.model_name}\n"
            f"  File Server: {self.mcp_file_url}\n"
            f"  DB Server: {self.mcp_db_url}\n"
            f"  Tools: {len(self.server_map)} registered"
        )


# Singleton instance
# This ensures we only load configuration once
_config_instance = None


def get_config() -> AppConfig:
    """
    Get the application configuration (singleton pattern).

    This function ensures we only create one configuration instance,
    which is efficient and prevents inconsistencies.

    Returns:
        AppConfig: The validated configuration

    Learning Point:
        The Singleton pattern ensures only one instance of a class exists.
        This is useful for configuration, database connections, and other
        resources that should be shared across the application.

    Example:
        config = get_config()
        print(config.ollama_url)
    """
    global _config_instance

    if _config_instance is None:
        _config_instance = AppConfig()
        _config_instance.validate()

    return _config_instance


def reset_config():
    """
    Reset the configuration singleton (useful for testing).

    In tests, you might want to change environment variables and reload
    the configuration. This function allows that.

    Learning Point:
        Testability is important. Even singletons should have a way to
        reset for testing purposes.
    """
    global _config_instance
    _config_instance = None

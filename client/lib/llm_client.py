"""
LLM Client - Communicating with the "Brain"
===========================================

This module handles all communication with Ollama (the LLM).

Why this exists:
- Separates LLM interaction from agent orchestration logic
- Provides a clean abstraction over the Ollama API
- Manages conversation history and context
- Handles tool calling protocol

Key Concepts:
- **Chat Completion API**: Modern way to interact with LLMs
- **Tool Calling/Function Calling**: LLMs can request external tools
- **Message History**: LLMs need context (previous messages) to respond coherently
- **System Prompts**: Instructions that guide the LLM's behavior
- **Streaming vs Non-Streaming**: Getting responses all-at-once vs chunk-by-chunk

The Conversation Flow:
1. System Prompt: "You are a helpful assistant with these rules..."
2. User Message: "Who wrote the groceries note?"
3. Assistant (LLM): "I need to query the database" → Tool Call Request
4. Tool Result: [{"username": "alice"}]
5. Assistant (LLM): "Alice wrote the groceries note." → Final Answer

Learning Points:
- Each message has a role: 'system', 'user', 'assistant', or 'tool'
- Message history grows with each turn (can hit context limits!)
- Tool calling is a structured way for LLMs to request actions
- System prompts are powerful - they shape the LLM's behavior

Real-World Example:
    ChatGPT, Claude, and other chat apps all use this pattern:
    - Your messages = "user" role
    - AI responses = "assistant" role
    - Instructions = "system" role
    - When ChatGPT uses plugins = "tool" role
"""

import requests
import json
import time
import re
from typing import List, Dict, Any, Optional, Tuple
from lib.ui import print_success, print_error, print_info, print_llm_thought
from lib.config import get_config
from lib.sanitizers import clean_json_text


class LLMClient:
    """
    Client for communicating with Ollama (or OpenAI-compatible LLM APIs).

    This class abstracts away the details of the Ollama API and provides
    a clean interface for the agent to interact with the LLM.

    Attributes:
        ollama_url: Base URL of Ollama server
        model_name: Name of the model to use
        timeout: Request timeout in seconds

    Learning Point:
        Using a class allows us to:
        - Maintain conversation state (message history)
        - Configure the LLM once and reuse it
        - Mock the LLM for testing
        - Swap out Ollama for other LLM providers easily
    """

    def __init__(
        self,
        ollama_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: int = 120
    ):
        """
        Initialize LLM client.

        Args:
            ollama_url: Base URL of Ollama server (defaults to config)
            model_name: Model to use (defaults to config)
            timeout: Request timeout in seconds (default: 120)

        Learning Point:
            LLM requests can be slow (especially for complex queries),
            so we use a long timeout (120s vs 10s for tools).
        """
        config = get_config()
        self.ollama_url = (ollama_url or config.ollama_url).rstrip('/')
        self.model_name = model_name or config.model_name
        self.timeout = timeout

    def build_system_prompt(self) -> str:
        """
        Build the system prompt that guides the LLM's behavior.

        The system prompt is like "instructions" for the LLM. It tells
        the LLM what role to play and how to behave.

        Returns:
            System prompt string

        Learning Point:
            System prompts are incredibly powerful! They can:
            - Define the LLM's personality
            - Set rules and constraints
            - Provide domain knowledge
            - Guide tool usage

            Good prompting is an art (and increasingly a science!)

        Example:
            "You are a helpful SQL assistant. Always use ILIKE for
             case-insensitive searches. Never use SELECT *."
        """
        return """You are a smart assistant with access to a database and a file system.

WHEN USING THE DATABASE:
1. The schema has 'users' (id, username, email) and 'notes' (id, user_id, title, content).
2. To find who wrote a note, you MUST JOIN tables: `SELECT u.username FROM users u JOIN notes n ON u.id = n.user_id ...`
3. Use ILIKE for case-insensitive search (e.g. `title ILIKE '%shopping%'`).
4. ALWAYS put single quotes around string values! (Correct: `'%shopping%'`, Wrong: `%shopping%`)
5. DO NOT use `+` to concatenate strings. Use standard SQL syntax.
6. Example of a correct query:
   `SELECT u.username FROM users u JOIN notes n ON u.id = n.user_id WHERE n.title ILIKE '%deployment%'`
"""

    def chat(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Send a chat request to the LLM.

        This is the core method for LLM interaction. It sends a conversation
        history + available tools to the LLM and gets a response.

        Args:
            messages: List of message objects with 'role' and 'content'
            tools: List of available tools in Ollama format
            stream: Whether to stream the response (default: False)

        Returns:
            Response from Ollama containing the LLM's message

        Raises:
            ConnectionError: If cannot connect to Ollama
            ValueError: If Ollama returns an error

        Learning Point:
            The Ollama API is compatible with OpenAI's API format, which
            means code written for Ollama can often work with OpenAI, Azure,
            or other OpenAI-compatible services with minimal changes!

        Example:
            >>> client = LLMClient()
            >>> messages = [{"role": "user", "content": "Hello!"}]
            >>> response = client.chat(messages, tools=[])
            >>> print(response["message"]["content"])
            'Hi! How can I help you today?'
        """
        print_info(f"Sending request to Ollama ({self.model_name})...")

        payload = {
            "model": self.model_name,
            "messages": messages,
            "tools": tools,
            "stream": stream
        }

        try:
            start_time = time.time()

            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json=payload,
                timeout=self.timeout
            )

            duration = time.time() - start_time

            response.raise_for_status()

            print_success(f"Ollama responded in {duration:.2f}s")

            return response.json()

        except requests.exceptions.Timeout:
            raise ConnectionError(
                f"Ollama did not respond within {self.timeout}s.\n"
                f"The query might be too complex, or the server is overloaded."
            )

        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.ollama_url}\n"
                f"Make sure Ollama is running: docker compose ps\n"
                f"Technical details: {e}"
            )

        except requests.exceptions.HTTPError as e:
            raise ValueError(f"Ollama returned error: {e}")

    def parse_tool_calls(
        self,
        message: Dict[str, Any]
    ) -> Tuple[Optional[List[Dict[str, Any]]], bool]:
        """
        Parse tool calls from LLM response.

        The LLM can respond in two ways:
        1. Direct text answer (no tools needed)
        2. Tool call request (needs external data)

        This function detects which type of response it is and parses
        any tool calls.

        Args:
            message: The LLM's response message

        Returns:
            Tuple of:
            - List of tool calls (or None if no tools)
            - Boolean indicating if this is a direct answer

        Learning Point:
            LLMs don't always follow the protocol perfectly! Sometimes:
            - They include tool calls in the "content" field as JSON
            - They format JSON incorrectly
            - They hallucinate tool calls that don't exist

            Robust parsing handles these edge cases gracefully.

        Example:
            >>> message = {"tool_calls": [{"function": {"name": "read_file", ...}}]}
            >>> tool_calls, is_direct = client.parse_tool_calls(message)
            >>> is_direct
            False
            >>> len(tool_calls)
            1
        """
        # Check for standard tool_calls field
        tool_calls = message.get("tool_calls", [])

        if tool_calls:
            print_llm_thought("The model decided it needs more information.")
            return tool_calls, False

        # Fallback: Check if LLM sent JSON in content (Llama quirk)
        content = message.get("content", "").strip()

        if not content:
            return None, False

        # Try to find JSON in content
        json_match = re.search(r"(\{.*\})", content, re.DOTALL)

        if json_match or (content.startswith("{") and content.endswith("}")):
            json_str = json_match.group(1) if json_match else content

            # Clean up invalid escapes
            json_str = clean_json_text(json_str)

            try:
                print_info("Attempting to parse raw JSON from content (fallback)...")
                fake_tool = json.loads(json_str)

                # Check if it looks like a tool call
                if "name" in fake_tool and ("parameters" in fake_tool or "arguments" in fake_tool):
                    print_llm_thought("The model sent a direct JSON response. Converting to tool call.")

                    # Normalize between "parameters" and "arguments"
                    args = fake_tool.get("parameters") or fake_tool.get("arguments")

                    tool_calls = [{
                        "function": {
                            "name": fake_tool["name"],
                            "arguments": args
                        }
                    }]

                    return tool_calls, False

            except json.JSONDecodeError as e:
                print_error(f"JSON parse failed even after cleanup: {e}")
                # Not a tool call, treat as direct answer
                pass

        # No tool calls found - this is a direct answer
        print_llm_thought("The model decided to answer directly without tools.")
        return None, True

    def create_conversation(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Create initial conversation with system and user messages.

        Args:
            user_prompt: The user's question/request
            system_prompt: Optional system prompt (uses default if not provided)

        Returns:
            List of message objects ready for the LLM

        Learning Point:
            Message order matters! The system message should come first,
            followed by the conversation history. This gives the LLM
            the best context for responding.

        Example:
            >>> messages = client.create_conversation("Hello!")
            >>> messages[0]["role"]
            'system'
            >>> messages[1]["role"]
            'user'
        """
        if system_prompt is None:
            system_prompt = self.build_system_prompt()

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    def add_tool_results(
        self,
        messages: List[Dict[str, str]],
        assistant_message: Dict[str, Any],
        tool_results: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """
        Add tool results to conversation history.

        After executing tools, we need to tell the LLM what happened.
        This function adds both the assistant's tool call request and
        the tool results to the conversation.

        Args:
            messages: Current conversation history
            assistant_message: The LLM's message requesting tools
            tool_results: Results from executing the tools

        Returns:
            Updated conversation history

        Learning Point:
            The LLM needs to see its own tool call request in the history,
            followed by the results. This is how it knows what context
            to use for its final answer.

            Conversation structure:
            1. System: "You are a helpful assistant..."
            2. User: "Who wrote the groceries note?"
            3. Assistant: [tool_call: query_db]
            4. Tool: [result: {"username": "alice"}]
            5. Assistant: "Alice wrote it!"

        Example:
            >>> messages = [{"role": "user", "content": "Hello"}]
            >>> assistant_msg = {"role": "assistant", "tool_calls": [...]}
            >>> results = [{"role": "tool", "content": "..."}]
            >>> updated = client.add_tool_results(messages, assistant_msg, results)
            >>> len(updated)
            3
        """
        # Add assistant's tool call request
        messages.append(assistant_message)

        # Add tool results
        messages.extend(tool_results)

        return messages

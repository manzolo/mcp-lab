"""
MCP Agent - The Orchestrator
============================

This is the MAIN FILE that ties everything together.

Think of it as a conductor of an orchestra:
- It doesn't play instruments (that's the modules in lib/)
- It coordinates when each section plays (the agent loop)
- It ensures everything works in harmony

The Agent Loop (5 Steps):
1. **Discovery**: Find available tools from MCP servers
2. **Reasoning**: Send user prompt + tools to LLM
3. **Decision**: LLM decides to use tools or answer directly
4. **Execution**: Execute requested tools
5. **Synthesis**: Send tool results back to LLM for final answer

Each step is handled by a specialized module, keeping this file
clean and easy to understand.

Architecture Note:
    This module provides two interfaces:
    - MCPAgent class: A generator-based interface for GUIs and programmatic use
    - chat() function: The original CLI interface with rich terminal output

Learning Points:
- Orchestration code should be high-level and readable
- Details are hidden in modules (separation of concerns)
- This file is the "entry point" - it's what users run
- Good orchestration makes the system easy to understand and modify

Usage:
    # CLI usage
    python agent.py "Your question here"

    # Programmatic usage (for GUIs)
    agent = MCPAgent()
    for event in agent.run("Your question"):
        print(event)

Example:
    python agent.py "Read hello.txt and tell me what it says"
"""

import sys
from typing import List, Dict, Any, Generator
from dataclasses import dataclass
from enum import Enum

# Import our modules
from lib.config import get_config
from lib.ui import print_step, print_info, print_success, print_llm_thought, print_error, Colors
from lib.mcp_client import discover_all_tools
from lib.llm_client import LLMClient
from lib.tool_router import ToolRouter
from lib.errors import (
    MCPError, LLMConnectionError, MCPServerError,
    ToolExecutionError, handle_error
)


# =============================================================================
# Event Types for the MCPAgent Generator Interface
# =============================================================================

class EventType(Enum):
    """Types of events yielded by MCPAgent.run()"""
    STEP_START = "step_start"      # A step is beginning
    INFO = "info"                   # Informational message
    SUCCESS = "success"             # Something succeeded
    TOOL_CALL = "tool_call"        # A tool is being called
    TOOL_RESULT = "tool_result"    # A tool returned a result
    FINAL_ANSWER = "final_answer"  # The final answer
    ERROR = "error"                 # An error occurred


@dataclass
class AgentEvent:
    """
    Event yielded by MCPAgent during execution.

    This provides a structured way for GUIs to receive updates
    about the agent's progress through the loop.

    Attributes:
        type: The type of event (see EventType enum)
        step: Which step of the agent loop (1-6, or 0 for errors)
        message: Human-readable description
        data: Optional additional data (tool calls, results, etc.)
    """
    type: EventType
    step: int
    message: str
    data: Any = None


# =============================================================================
# MCPAgent Class - Generator-based Interface for GUIs
# =============================================================================

class MCPAgent:
    """
    MCP Agent with a generator-based interface.

    This class wraps the agent loop in a generator that yields events,
    making it easy to integrate with GUIs like Streamlit or web frontends.

    Example:
        agent = MCPAgent()
        for event in agent.run("Who wrote the groceries note?"):
            if event.type == EventType.STEP_START:
                print(f"Starting step {event.step}: {event.message}")
            elif event.type == EventType.FINAL_ANSWER:
                print(f"Answer: {event.message}")

    Learning Point:
        Using a generator pattern allows the UI to update in real-time
        as the agent progresses, rather than waiting for the entire
        operation to complete.
    """

    def __init__(self):
        """Initialize the agent with configuration."""
        self.config = get_config()
        self.llm_client = LLMClient()
        self.tools = []
        self.server_map = {}

    def run(self, prompt: str) -> Generator[AgentEvent, None, None]:
        """
        Run the agent loop, yielding events for each step.

        Args:
            prompt: The user's question or request

        Yields:
            AgentEvent objects describing the agent's progress

        Learning Point:
            This generator implements the same 5-step loop as chat(),
            but yields events instead of printing directly. This
            separation of concerns allows any UI to consume these events.
        """
        try:
            # =================================================================
            # STEP 1: DISCOVERY & CONTEXT PREPARATION
            # =================================================================
            yield AgentEvent(EventType.STEP_START, 1, "Discovery & Assembly")

            self.tools, self.server_map = discover_all_tools()

            if not self.tools:
                yield AgentEvent(EventType.ERROR, 1,
                    "No tools available! Make sure MCP servers are running.")
                return

            yield AgentEvent(EventType.SUCCESS, 1,
                f"Loaded {len(self.tools)} tools",
                data={"tool_count": len(self.tools)})

            # =================================================================
            # STEP 2: REASONING (The "Brain")
            # =================================================================
            yield AgentEvent(EventType.STEP_START, 2, "Reasoning")
            yield AgentEvent(EventType.INFO, 2,
                f"Sending to {self.config.model_name}...")

            messages = self.llm_client.create_conversation(prompt)

            try:
                response_data = self.llm_client.chat(messages, self.tools)
            except ConnectionError as e:
                raise LLMConnectionError(self.llm_client.ollama_url, str(e))

            message = response_data.get("message", {})
            yield AgentEvent(EventType.SUCCESS, 2, "LLM responded")

            # =================================================================
            # STEP 3: DECISION EVALUATION
            # =================================================================
            yield AgentEvent(EventType.STEP_START, 3, "Decision Evaluation")

            tool_calls, is_direct_answer = self.llm_client.parse_tool_calls(message)

            if tool_calls:
                yield AgentEvent(EventType.INFO, 3,
                    f"LLM decided to use {len(tool_calls)} tool(s)",
                    data={"tool_calls": tool_calls})

                # =============================================================
                # STEP 4: EXECUTION LOOP
                # =============================================================
                yield AgentEvent(EventType.STEP_START, 4, "Tool Execution")

                router = ToolRouter(self.server_map, timeout=10)

                # Yield info about each tool call
                for tc in tool_calls:
                    tool_name = tc.get("function", {}).get("name", "unknown")
                    tool_args = tc.get("function", {}).get("arguments", {})
                    yield AgentEvent(EventType.TOOL_CALL, 4,
                        f"Calling {tool_name}",
                        data={"name": tool_name, "arguments": tool_args})

                try:
                    results = router.execute_tools(tool_calls)
                except ConnectionError as e:
                    raise MCPServerError("MCP Server", "unknown", str(e))
                except Exception as e:
                    raise ToolExecutionError("unknown", str(e))

                # Yield results
                for result in results:
                    yield AgentEvent(EventType.TOOL_RESULT, 4,
                        f"Got result from {result.get('tool', 'unknown')}",
                        data=result)

                tool_result_messages = router.format_tool_results_for_llm(results)

                # =============================================================
                # STEP 5: SYNTHESIS
                # =============================================================
                yield AgentEvent(EventType.STEP_START, 5, "Synthesis")
                yield AgentEvent(EventType.INFO, 5,
                    "Sending tool outputs back to LLM...")

                messages = self.llm_client.add_tool_results(
                    messages, message, tool_result_messages
                )

                try:
                    final_data = self.llm_client.chat(messages, self.tools)
                except ConnectionError as e:
                    raise LLMConnectionError(self.llm_client.ollama_url, str(e))

                final_content = final_data["message"]["content"]

                # =============================================================
                # STEP 6: FINAL ANSWER
                # =============================================================
                yield AgentEvent(EventType.FINAL_ANSWER, 6, final_content)

            else:
                # LLM answered directly without tools
                yield AgentEvent(EventType.INFO, 3, "LLM answered directly (no tools needed)")
                yield AgentEvent(EventType.FINAL_ANSWER, 6, message.get("content", ""))

        except MCPError as e:
            yield AgentEvent(EventType.ERROR, 0, str(e))
        except Exception as e:
            yield AgentEvent(EventType.ERROR, 0, handle_error(e))


# =============================================================================
# CLI Interface - The Original chat() Function
# =============================================================================

def chat(prompt: str):
    """
    Main agent function - orchestrates the agent loop with CLI output.

    This is the heart of the agent. It implements the 5-step loop:
    Discovery → Reasoning → Decision → Execution → Synthesis

    Args:
        prompt: The user's question or request

    Learning Point:
        Notice how clean this function is! All the complex logic is
        in the modules. This function just orchestrates the flow.

    Example:
        >>> chat("Who wrote the groceries note?")
        # Agent discovers tools, queries LLM, executes query_db, returns answer
    """
    print(f"{Colors.BOLD}🤖 AGENT STARTING...{Colors.ENDC}")
    print(f'Goal: "{prompt}"\n')

    try:
        # =================================================================
        # STEP 1: DISCOVERY & CONTEXT PREPARATION
        # Gather all capabilities (tools) our agent has access to.
        # =================================================================
        print_step(1, "Discovery & Assembly")

        # Discover tools from all MCP servers
        tools, server_map = discover_all_tools()

        if not tools:
            print_error("No tools available! Cannot proceed.")
            print_info("Make sure MCP servers are running: docker compose ps")
            return

        # =================================================================
        # STEP 2: REASONING (The "Brain")
        # We send the Prompt + Tool Definitions to the LLM.
        # The LLM decides if it can answer directly or needs tools.
        # =================================================================
        print_step(2, "Reasoning (Sending to LLM)")

        # Initialize LLM client
        llm_client = LLMClient()

        # Create conversation with system prompt
        messages = llm_client.create_conversation(prompt)

        # Send to LLM
        try:
            response_data = llm_client.chat(messages, tools)
        except ConnectionError as e:
            raise LLMConnectionError(llm_client.ollama_url, str(e))

        message = response_data.get("message", {})

        # =================================================================
        # STEP 3: DECISION EVALUATION
        # Did the LLM give us text or a request to run tools?
        # =================================================================
        print_step(3, "Decision Evaluation")

        # Parse tool calls from LLM response
        tool_calls, is_direct_answer = llm_client.parse_tool_calls(message)

        if tool_calls:
            # LLM wants to use tools
            # =============================================================
            # STEP 4: EXECUTION LOOP
            # For each tool requested, we run it and capture the output.
            # =============================================================
            print_step(4, "Tool Execution")

            # Initialize tool router
            router = ToolRouter(server_map, timeout=10)

            # Execute all requested tools
            try:
                results = router.execute_tools(tool_calls)
            except ConnectionError as e:
                raise MCPServerError("MCP Server", "unknown", str(e))
            except Exception as e:
                raise ToolExecutionError("unknown", str(e))

            # Format results for LLM
            tool_result_messages = router.format_tool_results_for_llm(results)

            # =============================================================
            # STEP 5: SYNTHESIS
            # We send the Tool Results back to the LLM to get the final answer.
            # =============================================================
            print_step(5, "Synthesis (Feeding back results)")
            print_info("Sending tool outputs back to Ollama...")

            # Add tool call and results to conversation
            messages = llm_client.add_tool_results(
                messages,
                message,
                tool_result_messages
            )

            # Get final answer from LLM
            try:
                final_data = llm_client.chat(messages, tools)
            except ConnectionError as e:
                raise LLMConnectionError(llm_client.ollama_url, str(e))

            final_content = final_data["message"]["content"]

            # =============================================================
            # STEP 6: FINAL ANSWER
            # =============================================================
            print_step(6, "Final Answer")
            print(f"\n{Colors.BOLD}{final_content}{Colors.ENDC}\n")

        else:
            # LLM answered directly without tools
            print_step(6, "Direct Answer")
            print(f"\n{Colors.BOLD}{message['content']}{Colors.ENDC}\n")

    except MCPError as e:
        # Our custom errors already have helpful messages
        print(f"\n{Colors.FAIL}❌ ERROR:{Colors.ENDC}")
        print(str(e))
        sys.exit(1)

    except Exception as e:
        # Unexpected errors - provide helpful message
        print(f"\n{Colors.FAIL}❌ UNEXPECTED ERROR:{Colors.ENDC}")
        print(handle_error(e))
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python agent.py 'Your question here'")
        print("Example: python agent.py 'Read hello.txt and tell me what it says'")
        sys.exit(1)

    prompt = sys.argv[1]
    chat(prompt)

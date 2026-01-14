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

Learning Points:
- Orchestration code should be high-level and readable
- Details are hidden in modules (separation of concerns)
- This file is the "entry point" - it's what users run
- Good orchestration makes the system easy to understand and modify

Usage:
    python agent.py "Your question here"

Example:
    python agent.py "Read hello.txt and tell me what it says"
"""

import sys
from typing import List, Dict, Any

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


def chat(prompt: str):
    """
    Main agent function - orchestrates the agent loop.

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
    """
    Entry point when running the script directly.

    Parses command line arguments and starts the agent.

    Usage:
        python agent.py "Your prompt here"
        python agent.py  # Uses default prompt
    """
    if len(sys.argv) > 1:
        # User provided a prompt
        prompt = " ".join(sys.argv[1:])
    else:
        # Default didactic prompt
        prompt = "Hello! Check the database for any notes and tell me what they are about."

    # Run the agent!
    chat(prompt)

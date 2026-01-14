"""
User Interface Module - Making Terminal Output Beautiful
========================================================

This module handles all console output formatting using ANSI color codes.

Why this exists:
- Separates presentation (UI) from logic (business operations)
- Makes the codebase more maintainable and testable
- Allows easy swapping of UI implementations (terminal, web, etc.)

Key Concepts:
- ANSI Escape Codes: Special character sequences that terminals understand
  to display colors and formatting. Example: '\033[95m' means "show purple text"
- Separation of Concerns: UI logic should be separate from business logic
  so you can change one without affecting the other

Learning Points:
- In production applications, UI is often a separate module or even a separate service
- This makes it easier to create multiple interfaces (CLI, web, mobile) for the same logic
- Screen readers and accessibility tools can work better when UI is well-separated

Example:
    from lib.ui import print_step, print_success

    print_step(1, "Discovery")
    print_success("Found 5 tools")
"""


class Colors:
    """
    ANSI Color Codes for Terminal Output

    These are special escape sequences that terminals understand.
    They tell the terminal to change text color or style.

    Example: '\033[95m' means "start purple text"
             '\033[0m' means "reset to default"
    """
    HEADER = '\033[95m'   # Purple - Used for section headers
    OKBLUE = '\033[94m'   # Blue - Used for information
    OKCYAN = '\033[96m'   # Cyan - Used for LLM thoughts
    OKGREEN = '\033[92m'  # Green - Used for success messages
    WARNING = '\033[93m'  # Yellow - Used for warnings and tool execution
    FAIL = '\033[91m'     # Red - Used for errors
    ENDC = '\033[0m'      # Reset - Returns to default color
    BOLD = '\033[1m'      # Bold text


def print_step(step_num: int, title: str):
    """
    Print a numbered step header in the agent loop.

    This creates visual separation between different phases of the agent loop:
    Discovery → Reasoning → Decision → Execution → Synthesis → Final Answer

    Args:
        step_num: The step number (1-6)
        title: The step description (e.g., "Discovery & Assembly")

    Example:
        print_step(1, "Discovery")
        # Output: "➤ STEP 1: Discovery" (in purple and bold)

    Learning Point:
        Visual feedback is crucial for educational tools. Users need to see
        what's happening at each stage to understand the agent loop.
    """
    print(f"\n{Colors.HEADER}{Colors.BOLD}➤ STEP {step_num}: {title}{Colors.ENDC}")


def print_info(msg: str):
    """
    Print an informational message.

    Used for neutral information that the user should know but isn't
    success or error.

    Args:
        msg: The message to display

    Example:
        print_info("Loading configuration from .env file")
        # Output: "ℹ Loading configuration..." (in blue)
    """
    print(f"{Colors.OKBLUE}  ℹ {msg}{Colors.ENDC}")


def print_success(msg: str):
    """
    Print a success message.

    Used to indicate that an operation completed successfully.

    Args:
        msg: The success message

    Example:
        print_success("All servers are ready!")
        # Output: "✓ All servers are ready!" (in green)

    Learning Point:
        Positive reinforcement through visual feedback helps users feel
        confident that things are working correctly.
    """
    print(f"{Colors.OKGREEN}  ✓ {msg}{Colors.ENDC}")


def print_llm_thought(msg: str):
    """
    Print a message representing LLM reasoning.

    Used to show what the AI "brain" (Ollama) is thinking or deciding.

    Args:
        msg: The thought or decision message

    Example:
        print_llm_thought("The model decided it needs more information")
        # Output: "🧠 The model decided..." (in cyan)

    Learning Point:
        Making AI reasoning visible demystifies how agents work. Users can
        see the decision-making process, not just the final result.
    """
    print(f"{Colors.OKCYAN}  🧠 {msg}{Colors.ENDC}")


def print_tool_exec(msg: str):
    """
    Print a tool execution message.

    Used to show when the agent is executing a tool (calling an MCP server).

    Args:
        msg: The execution message

    Example:
        print_tool_exec("Calling: read_file")
        # Output: "🛠️  Calling: read_file" (in yellow)

    Learning Point:
        Tool execution is a critical step in the agent loop. Highlighting it
        helps users understand when the agent is taking action in the real world.
    """
    print(f"{Colors.WARNING}  🛠️  {msg}{Colors.ENDC}")


def print_error(msg: str):
    """
    Print an error message.

    Used for errors and failures that the user needs to address.

    Args:
        msg: The error message

    Example:
        print_error("Failed to connect to Ollama")
        # Output: "❌ Failed to connect..." (in red)

    Learning Point:
        Clear error messages are essential for learning. Users need to know
        not just that something failed, but what went wrong and how to fix it.
    """
    print(f"{Colors.FAIL}  ❌ {msg}{Colors.ENDC}")

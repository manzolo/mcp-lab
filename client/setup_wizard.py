#!/usr/bin/env python3
"""
Setup Wizard for MCP Lab
========================

This interactive wizard guides users through setting up their MCP Lab environment.

What it does:
1. Checks prerequisites (Docker, Docker Compose)
2. Helps configure Ollama (local or external)
3. Generates .env configuration file
4. Starts services and verifies connectivity
5. Shows next steps and example commands

This makes the setup process beginner-friendly and reduces configuration errors.
"""

import os
import sys
import subprocess
import time
from typing import Optional, Tuple

# Import our UI module for consistent styling
sys.path.insert(0, os.path.dirname(__file__))
from lib.ui import Colors, print_success, print_error, print_info


def print_header(text: str):
    """Print a styled header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}  {text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.ENDC}\n")


def print_box(text: str):
    """Print text in a box."""
    lines = text.split('\n')
    max_len = max(len(line) for line in lines)
    print(f"\n{Colors.OKCYAN}┌─{'─' * max_len}─┐{Colors.ENDC}")
    for line in lines:
        padding = ' ' * (max_len - len(line))
        print(f"{Colors.OKCYAN}│ {line}{padding} │{Colors.ENDC}")
    print(f"{Colors.OKCYAN}└─{'─' * max_len}─┘{Colors.ENDC}\n")


def run_command(cmd: str, check: bool = True, capture: bool = True) -> Tuple[int, str]:
    """
    Run a shell command and return exit code and output.

    Args:
        cmd: Command to run
        check: Whether to check return code
        capture: Whether to capture output

    Returns:
        Tuple of (exit_code, output)
    """
    try:
        if capture:
            result = subprocess.run(
                cmd,
                shell=True,
                check=check,
                capture_output=True,
                text=True
            )
            return result.returncode, result.stdout + result.stderr
        else:
            result = subprocess.run(cmd, shell=True, check=check)
            return result.returncode, ""
    except subprocess.CalledProcessError as e:
        return e.returncode, str(e)


def check_docker() -> bool:
    """Check if Docker is installed and running."""
    print_info("Checking Docker installation...")

    # Check if docker command exists
    code, output = run_command("docker --version", check=False)
    if code != 0:
        print_error("Docker is not installed")
        print("\n  Please install Docker from: https://docs.docker.com/get-docker/")
        return False

    print_success(f"Docker found: {output.strip()}")

    # Check if Docker daemon is running
    code, _ = run_command("docker ps", check=False)
    if code != 0:
        print_error("Docker is installed but not running")
        print("\n  Please start Docker and try again")
        return False

    print_success("Docker daemon is running")
    return True


def check_docker_compose() -> bool:
    """Check if Docker Compose is installed."""
    print_info("Checking Docker Compose installation...")

    code, output = run_command("docker compose version", check=False)
    if code != 0:
        print_error("Docker Compose is not installed")
        print("\n  Please install Docker Compose (usually included with Docker Desktop)")
        return False

    print_success(f"Docker Compose found: {output.strip()}")
    return True


def ask_yes_no(question: str, default: bool = True) -> bool:
    """
    Ask a yes/no question.

    Args:
        question: Question to ask
        default: Default answer if user just presses Enter

    Returns:
        True for yes, False for no
    """
    default_str = "Y/n" if default else "y/N"
    while True:
        answer = input(f"{question} [{default_str}]: ").strip().lower()

        if not answer:
            return default

        if answer in ['y', 'yes']:
            return True
        elif answer in ['n', 'no']:
            return False
        else:
            print_error("Please answer 'yes' or 'no'")


def ask_choice(question: str, choices: list, default: int = 0) -> int:
    """
    Ask user to choose from a list of options.

    Args:
        question: Question to ask
        choices: List of choice strings
        default: Default choice index

    Returns:
        Index of chosen option
    """
    print(f"\n{question}")
    for i, choice in enumerate(choices, 1):
        marker = "→" if i == default + 1 else " "
        print(f"  {marker} [{i}] {choice}")

    while True:
        answer = input(f"\nChoice [1-{len(choices)}] (default: {default + 1}): ").strip()

        if not answer:
            return default

        try:
            choice = int(answer) - 1
            if 0 <= choice < len(choices):
                return choice
            else:
                print_error(f"Please enter a number between 1 and {len(choices)}")
        except ValueError:
            print_error("Please enter a valid number")


def configure_ollama() -> Tuple[str, str]:
    """
    Configure Ollama settings.

    Returns:
        Tuple of (ollama_url, model_name)
    """
    print_header("STEP 2/5: Ollama Configuration")

    print("""
Ollama is the "brain" - the LLM that powers the agent.
You have two options:

  Option 1: Use Local Ollama Container (Recommended for beginners)
    • Self-contained, no external dependencies
    • Easier to set up
    • Requires ~4GB RAM for llama3.2:3b model

  Option 2: Use External Ollama Instance
    • Use Ollama running on your host machine
    • Or connect to a remote Ollama server
    • More flexible for advanced users
""")

    choice = ask_choice(
        "How would you like to run Ollama?",
        [
            "Local Container (Recommended) - Docker will manage everything",
            "External Instance - I have Ollama running elsewhere"
        ],
        default=0
    )

    if choice == 0:
        # Local container
        ollama_url = "http://ollama:11434"
        print_success("Will use local Ollama container")

        # Ask about model
        print("\nWhich model would you like to use?")
        print("  • llama3.2:3b - Fast, good for learning (2GB RAM, ~1-2s response)")
        print("  • llama3.2:7b - Better quality (8GB RAM, ~3-5s response)")

        model_choice = ask_choice(
            "Select a model:",
            [
                "llama3.2:3b (Recommended for learning)",
                "llama3.2:7b (Better quality, needs more RAM)"
            ],
            default=0
        )

        model_name = "llama3.2:3b" if model_choice == 0 else "llama3.2:7b"
        print_success(f"Will use model: {model_name}")

    else:
        # External instance
        print("\nPlease enter your Ollama URL:")
        print("  Examples:")
        print("    • http://localhost:11434 (local Ollama on host)")
        print("    • http://host.docker.internal:11434 (host from container)")
        print("    • http://your-server:11434 (remote server)")

        ollama_url = input("\nOllama URL [http://localhost:11434]: ").strip()
        if not ollama_url:
            ollama_url = "http://localhost:11434"

        print_success(f"Will use Ollama at: {ollama_url}")

        # Ask about model
        model_name = input("\nModel name [llama3.2:3b]: ").strip()
        if not model_name:
            model_name = "llama3.2:3b"

        print_success(f"Will use model: {model_name}")

    return ollama_url, model_name


def generate_env_file(ollama_url: str, model_name: str) -> bool:
    """
    Generate .env configuration file.

    Args:
        ollama_url: Ollama URL
        model_name: Model name

    Returns:
        True if successful
    """
    print_header("STEP 3/5: Generate Configuration")

    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')

    if os.path.exists(env_path):
        if not ask_yes_no(f"\n.env file already exists. Overwrite?", default=False):
            print_info("Keeping existing .env file")
            return True

    env_content = f"""# MCP Lab Configuration
# Generated by setup wizard

# Database Configuration
POSTGRES_DB=mcp
POSTGRES_USER=mcp
POSTGRES_PASSWORD=mcp

# Ollama Configuration
OLLAMA_URL={ollama_url}
MODEL_NAME={model_name}
"""

    try:
        with open(env_path, 'w') as f:
            f.write(env_content)

        print_success("Created .env file")
        print(f"\n{Colors.OKBLUE}Configuration:{Colors.ENDC}")
        print(f"  OLLAMA_URL={ollama_url}")
        print(f"  MODEL_NAME={model_name}")
        return True

    except Exception as e:
        print_error(f"Failed to create .env file: {e}")
        return False


def start_services(use_local_ollama: bool) -> bool:
    """
    Start Docker Compose services.

    Args:
        use_local_ollama: Whether to start local Ollama container

    Returns:
        True if successful
    """
    print_header("STEP 4/5: Start Services")

    # Change to project root directory
    project_root = os.path.dirname(os.path.dirname(__file__))
    os.chdir(project_root)

    print_info("Stopping any existing services...")
    run_command("docker compose down", check=False, capture=False)

    if use_local_ollama:
        print_info("\nStarting services with local Ollama...")
        print("  (This will download the Ollama image if needed - may take a few minutes)")
        code, output = run_command("make up-local", check=False, capture=False)
    else:
        print_info("\nStarting MCP servers...")
        code, output = run_command("make up", check=False, capture=False)

    if code != 0:
        print_error("Failed to start services")
        return False

    print_success("Services started successfully!")

    # Wait for services to be ready
    print_info("Waiting for services to initialize...")
    time.sleep(5)

    return True


def verify_setup() -> bool:
    """
    Verify that everything is working.

    Returns:
        True if all checks pass
    """
    print_header("STEP 5/5: Verify Setup")

    print_info("Running connectivity tests...")

    code, output = run_command("make test-servers", check=False, capture=True)

    if code == 0 and "✅" in output:
        print_success("All connectivity tests passed!")
        return True
    else:
        print_error("Some tests failed")
        print("\nTest output:")
        print(output)
        return False


def show_next_steps():
    """Show what to do next."""
    print_box("""
🎉 Setup Complete! Your MCP Lab is ready!
""")

    print(f"{Colors.BOLD}Try these commands to get started:{Colors.ENDC}\n")

    print(f"{Colors.OKGREEN}1. Read a file:{Colors.ENDC}")
    print(f'   make agent MSG="Read hello.txt and tell me what it says"\n')

    print(f"{Colors.OKGREEN}2. Query the database:{Colors.ENDC}")
    print(f'   make agent MSG="Who wrote the groceries note?"\n')

    print(f"{Colors.OKGREEN}3. Complex query:{Colors.ENDC}")
    print(f'   make agent MSG="List all notes about deployment"\n')

    print(f"{Colors.BOLD}Useful commands:{Colors.ENDC}\n")
    print(f"  make test        - Run all tests")
    print(f"  make logs        - View service logs")
    print(f"  make down        - Stop all services")
    print(f"  make up          - Restart services\n")

    print(f"{Colors.BOLD}Learn more:{Colors.ENDC}\n")
    print(f"  README.md        - Full documentation")
    print(f"  TUTORIAL.md      - Step-by-step tutorials")
    print(f"  CLAUDE.md        - Architecture details\n")


def main():
    """Main wizard flow."""
    print_box("""
🧪 Welcome to MCP Lab Setup Wizard

This wizard will help you set up your AI agent playground
in just a few minutes!
""")

    # Step 1: Check prerequisites
    print_header("STEP 1/5: Check Prerequisites")

    if not check_docker():
        sys.exit(1)

    if not check_docker_compose():
        sys.exit(1)

    print_success("All prerequisites met!")

    # Step 2: Configure Ollama
    ollama_url, model_name = configure_ollama()
    use_local_ollama = "ollama:" in ollama_url

    # Step 3: Generate .env
    if not generate_env_file(ollama_url, model_name):
        sys.exit(1)

    # Step 4: Start services
    if not start_services(use_local_ollama):
        print_error("\nSetup incomplete. Please check the error messages above.")
        sys.exit(1)

    # Step 5: Verify
    if not verify_setup():
        print_error("\nSetup completed but verification failed.")
        print("You can try running the tests manually: make test-servers")
        sys.exit(1)

    # Show next steps
    show_next_steps()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Setup cancelled by user{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.FAIL}Unexpected error: {e}{Colors.ENDC}")
        sys.exit(1)

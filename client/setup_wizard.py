#!/usr/bin/env python3
"""
Setup Wizard for MCP Lab
========================

Educational tool to guide users through the setup process.
"""

import os
import sys
import subprocess
import time
import re
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
    lines = text.strip().split('\n')
    max_len = max(len(line) for line in lines)
    print(f"\n{Colors.OKCYAN}┌─{'─' * max_len}─┐{Colors.ENDC}")
    for line in lines:
        padding = ' ' * (max_len - len(line))
        print(f"{Colors.OKCYAN}│ {line}{padding} │{Colors.ENDC}")
    print(f"{Colors.OKCYAN}└─{'─' * max_len}─┘{Colors.ENDC}\n")


def run_command(cmd: str, check: bool = True, capture: bool = True) -> Tuple[int, str]:
    """Run a shell command."""
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


def ask_yes_no(question: str, default: bool = True) -> bool:
    """Ask a yes/no question."""
    default_str = "Y/n" if default else "y/N"
    while True:
        answer = input(f"{question} [{default_str}]: ").strip().lower()
        if not answer: return default
        if answer in ['y', 'yes']: return True
        if answer in ['n', 'no']: return False
        print_error("Please answer 'yes' or 'no'")


def ask_choice(question: str, choices: list, default: int = 0) -> int:
    """Ask user to choose from a list."""
    print(f"\n{question}")
    for i, choice in enumerate(choices, 1):
        marker = "→" if i == default + 1 else " "
        print(f"  {marker} [{i}] {choice}")

    while True:
        answer = input(f"\nChoice [1-{len(choices)}] (default: {default + 1}): ").strip()
        if not answer: return default
        try:
            choice = int(answer) - 1
            if 0 <= choice < len(choices): return choice
        except ValueError: pass
        print_error(f"Please enter a number between 1 and {len(choices)}")


def check_prerequisites() -> bool:
    """General info about the environment."""
    print_info("Checking environment...")
    
    # Check if we are in the container
    in_container = os.path.exists('/.dockerenv')
    if in_container:
        print_success("Running inside Setup Container")
        print_info("I will generate configuration files for your host machine.")
    else:
        print_info("Running on Host Machine")

    return True


def configure_ollama() -> Tuple[str, str]:
    """Configure Ollama settings."""
    print_header("STEP 2/5: Ollama Configuration")

    print(f"""
Ollama is the {Colors.BOLD}"brain"{Colors.ENDC} - the LLM that powers the agent.

{Colors.OKBLUE}Option 1: Use Local Ollama Container (Recommended){Colors.ENDC}
  • Setup handles everything. Best if you don't have Ollama yet.

{Colors.OKBLUE}Option 2: Use External Ollama Instance{Colors.ENDC}
  • Use Ollama running on your machine (host).
""")

    choice = ask_choice(
        "How would you like to run Ollama?",
        [
            "Local Container (Managed by Docker Compose)",
            "External Instance (Running on host)"
        ],
        default=0
    )

    if choice == 0:
        ollama_url = "http://ollama:11434"
        print_success("Selected: Local Ollama container")
    else:
        print("\nPlease enter your Ollama URL:")
        print(f"  {Colors.WARNING}Tip:{Colors.ENDC} Usually it's {Colors.BOLD}http://localhost:11434{Colors.ENDC}")
        
        ollama_url = input(f"\nOllama URL [http://localhost:11434]: ").strip()
        if not ollama_url:
            ollama_url = "http://localhost:11434"
        print_success(f"Selected: {ollama_url}")

    # Model selection
    print("\nWhich model would you like to use?")
    print("  • llama3.2:3b - Fast, good for learning")

    model_choice = ask_choice(
        "Select a model:",
        ["llama3.2:3b", "llama3.2:7b"],
        default=0
    )
    model_name = "llama3.2:3b" if model_choice == 0 else "llama3.2:7b"
    print_success(f"Selected model: {model_name}")

    return ollama_url, model_name


def generate_env_file(ollama_url: str, model_name: str) -> bool:
    """Generate .env configuration file."""
    print_header("STEP 3/5: Configuration")

    # The wizard container mounts the project root to /workspace
    env_path = "/workspace/.env"
    
    if os.path.exists(env_path):
        if not ask_yes_no(f"\n.env file already exists. Overwrite?", default=False):
            print_info("Keeping existing .env file")
            return True

    env_content = f"""# MCP Lab Configuration
# Generated by Setup Wizard

# Database
POSTGRES_DB=mcp
POSTGRES_USER=mcp
POSTGRES_PASSWORD=mcp

# Ollama
OLLAMA_URL={ollama_url}
MODEL_NAME={model_name}
"""
    try:
        with open(env_path, 'w') as f:
            f.write(env_content)
        print_success("Configuration saved to .env")
        return True
    except Exception as e:
        print_error(f"Failed to create .env file: {e}")
        return False


def start_services(ollama_url: str) -> bool:
    """Show commands to start the lab."""
    print_header("STEP 4/5: Launch Instructions")

    print_info("Configuration is ready. Please run these commands on your HOST machine:")
    
    local_ollama = "ollama:" in ollama_url
    if local_ollama:
        print(f"\n  {Colors.BOLD}make up-local{Colors.ENDC}")
    else:
        print(f"\n  {Colors.BOLD}make up{Colors.ENDC}")
        
    print("\nThis will start the database, MCP servers, and the agent.")
    return True


def verify_setup() -> bool:
    """Verification instructions."""
    print_header("STEP 5/5: Next Steps")
    print_info("Once services are running, test your agent with:")
    print(f"\n  {Colors.BOLD}make agent-db{Colors.ENDC}")
    print("\nOr ask a custom question:")
    print(f"  {Colors.BOLD}make agent MSG=\"Who wrote the groceries note?\"{Colors.ENDC}")
    return True


def main():
    """Main wizard flow."""
    print_box(f"""
🧪 MCP LAB SETUP WIZARD

I will help you configure your AI Agent playground.
I'll generate the .env file and show you how to start.
""")

    # Step 1: Check
    check_prerequisites()

    # Step 2: Configure Ollama
    ollama_url, model_name = configure_ollama()

    # Step 3: Generate .env
    if not generate_env_file(ollama_url, model_name):
        sys.exit(1)

    # Step 4: Instructions
    start_services(ollama_url)

    # Step 5: Verification
    verify_setup()

    print_box("""
🎉 Wizard Finished!
Follow the instructions above to start your lab.
""")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Setup cancelled{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.FAIL}Error: {e}{Colors.ENDC}")
        sys.exit(1)

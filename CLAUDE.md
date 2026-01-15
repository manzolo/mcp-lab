# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP Lab is a fully containerized, educational Model Context Protocol (MCP) playground demonstrating how to connect an LLM (Ollama) to local tools using a microservice architecture. The system follows an **Agent Loop** pattern where the agent acts as a bridge between the LLM "brain" and MCP server "tools".

**Key Achievement**: Through refactoring, the main agent.py was reduced from 348 lines to ~200 lines by extracting focused modules with comprehensive educational documentation.

## Architecture

The system consists of three main components orchestrated by Docker Compose:

1. **The Brain (External)**: Ollama instance providing LLM intelligence
2. **The Body (Agent)**: `mcp-agent` container (`client/agent.py`) that bridges the LLM and tools
3. **The Tools (MCP Servers)**:
   - `mcp-file` (port 3333): File system operations with secure path access
   - `mcp-db` (port 3334): SQL queries against PostgreSQL database

### The Agent Loop

Understanding the flow is critical to working with this codebase:

1. **Discovery**: Agent fetches available tools from MCP servers via SDK's `list_tools()`
2. **Reasoning**: Agent sends user prompt + tool definitions to Ollama
3. **Decision**: Ollama responds with either text or structured tool call requests
4. **Execution**: Agent routes tool calls to appropriate MCP server via SDK's `call_tool()`
5. **Synthesis**: Agent feeds tool results back to Ollama for final response

### MCP Protocol

This project uses the **official MCP Python SDK** with streamable-http transport:
- Servers use `FastMCP` with `@mcp.tool()` decorators
- Client uses `ClientSession` with `streamablehttp_client`
- Communication via JSON-RPC protocol at `/mcp` endpoint
- Transport security configured to allow Docker container hostnames

## Common Commands

### First-Time Setup

```bash
# Interactive setup wizard (recommended for beginners)
make wizard

# Or quick setup (for experienced users)
make setup && make up
```

### Starting the Environment

```bash
# Using external Ollama (default)
make up

# Using local Ollama container (self-contained)
make up-local

# Stop all services
make down

# Clean everything (including volumes)
make clean
```

### Testing

```bash
# Run all tests (server connectivity + agent integration)
make test

# Test only MCP servers (no LLM required)
make test-servers

# Test individual servers
make test-file    # File server only
make test-db      # Database server only
```

### Running the Agent

```bash
# Custom prompt
make agent MSG="Your prompt here"

# Pre-defined file test
make agent-file

# Pre-defined database test
make agent-db
```

### Development

```bash
# View all available commands
make help

# View logs
make logs

# Rebuild all images
make build
```

## Key Files and Responsibilities

### `client/agent.py` (~200 lines, was 348)
The main orchestrator that ties everything together. Clean, high-level code that delegates to modules:
- `chat()`: Main function implementing the 5-step agent loop
- Minimal logic - just orchestration and error handling
- **Educational note**: Compare with git history to see before/after refactoring

### `client/setup_wizard.py` (~300 lines)
Interactive setup wizard for beginner-friendly configuration:
- Checks prerequisites (Docker, Docker Compose)
- Configures Ollama (local container or external)
- Generates .env configuration file
- Starts services and runs verification tests
- Shows next steps with example commands

### `client/lib/` - Modular Components

#### `client/lib/config.py` (~160 lines)
Configuration management with validation:
- `AppConfig` class: Centralizes all environment variables
- `get_config()`: Singleton pattern for accessing configuration
- Validates URLs and required settings on startup
- Maps tool names to server URLs (server_map)

#### `client/lib/ui.py` (~150 lines)
Console UI with ANSI color codes:
- `Colors` class: ANSI escape sequences for terminal colors
- `print_step()`, `print_info()`, `print_success()`, etc.: Styled output functions
- Separates presentation from business logic

#### `client/lib/mcp_client.py` (~310 lines)
MCP protocol implementation using official SDK:
- `MCPClient` class: Uses `ClientSession` with `streamablehttp_client`
- `get_tools()`: Async discovery via SDK's `list_tools()` method
- `call_tool()`: Async tool execution via SDK's `call_tool()` method
- `mcp_to_ollama_tool()`: Converts MCP format to Ollama format
- `discover_all_tools()`: Sync wrapper using `asyncio.run()`
- Implements caching for efficiency

#### `client/lib/llm_client.py` (~290 lines)
Ollama/LLM communication:
- `LLMClient` class: Abstracts LLM API communication
- `build_system_prompt()`: Creates the system prompt with SQL guidance
- `chat()`: Sends messages + tools to LLM, returns response
- `parse_tool_calls()`: Extracts tool calls from LLM response (handles quirks)
- `create_conversation()`: Initializes message history
- `add_tool_results()`: Appends tool results to conversation

#### `client/lib/tool_router.py` (~300 lines)
Tool routing and execution using official SDK:
- `ToolRouter` class: Routes tool calls to appropriate servers via `MCPClient`
- `execute_tool()`: Sync wrapper around async `_execute_tool_async()`
- `execute_tools()`: Executes multiple tools sequentially
- `format_tool_results_for_llm()`: Formats results for LLM consumption
- Uses `MCPClient.call_tool()` for SDK-based execution

#### `client/lib/sanitizers.py` (~240 lines)
Input sanitization and LLM quirk fixes:
- `clean_json_text()`: Fixes malformed JSON from LLM output
- `fix_sql_args()`: Sanitizes SQL (URL decoding, quote wrapping for ILIKE)
- `validate_tool_arguments()`: Security checks on tool inputs
- `sanitize_output()`: Truncates large outputs to fit context windows
- Comprehensive comments explaining each LLM quirk

#### `client/lib/errors.py` (~320 lines)
Educational error messages:
- `MCPError`: Base exception class
- `ConfigurationError`: Configuration issues with fix instructions
- `LLMConnectionError`: Ollama connection problems with troubleshooting
- `MCPServerError`: MCP server connectivity issues
- `ToolExecutionError`: Tool execution failures with context
- `handle_error()`: Converts any exception to user-friendly message
- Each error includes: what happened, why, and how to fix

### `mcp-file/server.py` (~95 lines)
FastMCP server exposing file system operations using standalone FastMCP package:
- Uses `@mcp.tool()` decorator for tool definition
- `read_file()`: Reads files with path traversal protection
- `list_files()`: Lists directory contents
- Clean `mcp.run(transport="http", host="...", port="...")` API

### `mcp-db/server.py` (~145 lines)
FastMCP server exposing database query capabilities using standalone FastMCP package:
- Uses `@mcp.tool()` decorator for tool definition
- `query_db()`: Executes SQL queries with `RealDictCursor`
- `list_tables()`: Lists available database tables
- `describe_table()`: Returns table schema
- Clean `mcp.run(transport="http", host="...", port="...")` API

### `mcp-db/init.sql`
Database schema and seed data:
- **users** table: `id`, `username`, `email`
- **notes** table: `id`, `user_id`, `title`, `content`, `created_at`
- Seed data includes users (alice, bob, charlie) and their notes

## Configuration

Configuration is managed via `.env` file (created from `.env.dist`):
- `OLLAMA_URL`: Ollama endpoint (default: `http://ollama:11434`)
- `MODEL_NAME`: Model to use (default: `llama3.2:3b`)
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`: Database credentials

## Docker Compose Profiles

- **default**: Runs only MCP servers and PostgreSQL
- **agent**: Includes the agent container
- **test**: Includes the test-runner container
- **local-llm**: Includes Ollama container for self-contained setup

## Adding New MCP Tools

To extend the system with a new tool:

1. Create a new directory (e.g., `mcp-weather/`)
2. Create `server.py` using FastMCP:
```python
from fastmcp import FastMCP

mcp = FastMCP("Weather Server")

@mcp.tool()
def get_weather(city: str) -> dict:
    """Get current weather for a city."""
    return {"temperature": 72, "conditions": "sunny"}

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=3335)
```
3. Create `requirements.txt`:
```
fastmcp>=2.0.0
```
4. Create `Dockerfile` (follow pattern from mcp-file or mcp-db)
5. Add service to `docker-compose.yml` with appropriate port and network
6. Update `client/lib/config.py`:
   - Add URL to `__init__` method
   - Add tool mapping to `server_map`
7. Optionally add integration tests in `tests/test_mcp.py`
8. Test: `make down && make up`, then `make agent MSG="test your tool"`

## Important Implementation Notes

### Agent SQL Handling
The agent includes robust middleware (`fix_sql_args()`) to handle common LLM SQL generation issues:
- URL-encoded characters (e.g., `%27` → `'`)
- Unquoted ILIKE patterns (wraps them in quotes)
- Invalid escape sequences in SQL strings

### LLM Response Parsing
The agent includes fallback logic to handle non-standard tool call formats:
- Checks both `tool_calls` field and raw JSON in content
- Cleans invalid escape sequences (`\%`, `\/`)
- Normalizes between `parameters` and `arguments` keys

### System Prompt for Database Queries
The agent includes a detailed system prompt (`client/agent.py:174-184`) that instructs the LLM on proper SQL query construction:
- Use JOINs to relate users and notes
- Use ILIKE for case-insensitive search
- Always quote string values
- Example queries are provided

## Project Structure Summary

```
mcp-lab/
├── client/                    # The Agent
│   ├── agent.py              # Main orchestrator (~200 lines, was 348)
│   ├── setup_wizard.py       # Interactive setup (~300 lines)
│   ├── requirements.txt      # Pinned dependencies
│   └── lib/                  # Modular components (7 modules, ~1700 lines total)
│       ├── __init__.py
│       ├── config.py         # Configuration (160 lines)
│       ├── ui.py             # Console UI (150 lines)
│       ├── mcp_client.py     # MCP protocol (270 lines)
│       ├── llm_client.py     # Ollama communication (290 lines)
│       ├── tool_router.py    # Tool routing (260 lines)
│       ├── sanitizers.py     # Input sanitization (240 lines)
│       └── errors.py         # Error handling (320 lines)
│
├── mcp-file/                  # File Tool Server
│   ├── server.py             # FastMCP server (~115 lines)
│   ├── data/                 # Accessible files
│   ├── requirements.txt      # MCP SDK + uvicorn
│   └── Dockerfile
│
├── mcp-db/                    # Database Tool Server
│   ├── server.py             # FastMCP server (~165 lines)
│   ├── init.sql              # Schema & seed data
│   ├── requirements.txt      # MCP SDK + psycopg2
│   └── Dockerfile
│
├── tests/                     # Integration tests
│   ├── test_mcp.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── docker-compose.yml         # Service orchestration
├── Makefile                  # Command shortcuts (with wizard!)
├── README.md                 # Beginner-friendly guide (~580 lines)
├── TUTORIAL.md               # Extended learning (~400 lines)
└── CLAUDE.md                 # This file
```

## Code Quality Metrics

**Before Refactoring**:
- agent.py: 348 lines (monolithic)
- No module structure
- Limited documentation
- Mixed concerns

**After Refactoring**:
- agent.py: ~200 lines (orchestration only)
- 7 focused modules (~1700 lines with extensive docs)
- ~1500 lines of educational docstrings
- Clear separation of concerns
- Each module < 300 lines

## Network Architecture

All services communicate via the `mcp-net` Docker bridge network. Internal service URLs:
- File server: `http://mcp-file:3333`
- DB server: `http://mcp-db:3334`
- PostgreSQL: `postgres:5432`
- Ollama (when using local-llm): `http://ollama:11434`

## Development Workflow

### Making Changes to the Agent

1. **Identify the module**: Which module handles the concern?
   - UI changes → `lib/ui.py`
   - Configuration → `lib/config.py`
   - LLM behavior → `lib/llm_client.py`
   - Tool execution → `lib/tool_router.py`

2. **Make changes**: Edit the specific module

3. **Rebuild**: `make down && make up`

4. **Test**: `make test`

### Common Modifications

**Change system prompt**:
- File: `client/lib/llm_client.py`
- Method: `build_system_prompt()`

**Add new tool server**:
- Files: `docker-compose.yml`, `client/lib/config.py`
- See "Adding New MCP Tools" section

**Change error messages**:
- File: `client/lib/errors.py`
- Modify exception classes

**Modify UI colors/styling**:
- File: `client/lib/ui.py`
- Update `Colors` class or print functions

## CI/CD Pipeline

The project includes a comprehensive GitHub Actions workflow (`.github/workflows/ci.yml`) that runs on every push and pull request to main/master branches.

### Workflow Structure

The CI pipeline consists of 6 parallel jobs with a final success reporting job:

#### Job 1: Build Docker Images
- Builds all Docker images (mcp-file, mcp-db, mcp-agent, wizard, test-runner)
- Verifies image sizes
- Uses Docker Buildx for efficient caching
- **Duration**: ~2-3 minutes

#### Job 2: Test MCP Servers
- Tests server connectivity without LLM
- Runs `make test-servers`, `make test-file`, `make test-db`
- Fast tests that verify MCP protocol implementation
- Logs shown on failure for debugging
- **Duration**: ~1 minute
- **No LLM required** - runs quickly

#### Job 3: Test Agent Integration
- Full end-to-end testing with local Ollama
- Runs `make up-local` to start all services
- Tests agent file reading and database queries
- Uses 120-second timeout per test
- Shows logs on failure
- **Duration**: ~8-10 minutes (includes model download)
- **Most comprehensive** - validates the entire agent loop

#### Job 4: Test Setup Wizard
- Verifies wizard Docker image builds correctly
- Tests wizard can access Docker daemon
- Ensures containerized wizard functionality
- **Duration**: ~1 minute

#### Job 5: Code Quality Checks
- Python syntax validation using `py_compile`
- Verifies modular structure (all 7 modules present)
- Checks requirements.txt files exist
- Ensures all Python files compile without errors
- **Duration**: <1 minute
- **Fast feedback** for syntax errors

#### Job 6: Documentation Validation
- Verifies all documentation files present
- Checks Makefile has required targets
- Validates mermaid diagrams in README
- Ensures project completeness
- **Duration**: <1 minute

#### Job 7: CI Success (requires all previous jobs)
- Reports overall success
- Only runs if all 6 jobs pass
- Provides clear success indicator

### Triggering the Workflow

**Automatic triggers**:
```bash
git push origin main          # Triggers on push to main
gh pr create                  # Triggers on pull request
```

**Manual trigger**:
```bash
gh workflow run "MCP Lab CI"  # Manual workflow dispatch
```

Or via GitHub UI: Actions → MCP Lab CI → Run workflow

### Understanding Test Results

**Green checks mean**:
- ✅ All Docker images build successfully
- ✅ MCP servers respond to protocol requests
- ✅ Agent can discover tools and execute them
- ✅ Wizard container has Docker access
- ✅ All Python code compiles
- ✅ Documentation is complete

**Common failure scenarios**:

1. **Build job fails**: Dockerfile syntax error or missing dependencies
   - Check: `docker compose build` locally
   - Fix: Update Dockerfile or requirements.txt

2. **Test-servers fails**: MCP server not responding or returning errors
   - Check: `make test-servers` locally
   - Fix: Verify server.py logic in mcp-file or mcp-db

3. **Test-agent fails**: Agent can't communicate with Ollama or tools
   - Check: `make up-local && make test` locally
   - Fix: Check agent.py orchestration or module integration

4. **Code-quality fails**: Python syntax error in a module
   - Check: `python -m py_compile client/agent.py`
   - Fix: Syntax errors in Python files

5. **Docs fails**: Missing file or Makefile target
   - Check: File existence and Makefile contents
   - Fix: Add missing files or targets

### Local Testing Before Push

Always run these before pushing:

```bash
# Quick checks (< 2 minutes)
make test-servers              # Verify servers work

# Full validation (~ 10 minutes)
make down && make up-local     # Fresh environment
make test                      # Run all tests

# Code quality
python -m py_compile client/agent.py client/lib/*.py
```

### Workflow Optimizations

The workflow is optimized for educational clarity and speed:
- **Parallel execution**: Independent jobs run concurrently
- **Early failure detection**: Code quality checks run first
- **Efficient caching**: Docker layer caching reduces build time
- **Isolated tests**: Each job uses fresh environment
- **Clear naming**: Job names indicate what's being tested

### Adding New Tests

To extend the CI pipeline:

1. **Add a new job** in `.github/workflows/ci.yml`:
   ```yaml
   test-new-feature:
     name: Test New Feature
     runs-on: ubuntu-latest
     needs: build
     steps:
       - uses: actions/checkout@v4
       - run: make test-new-feature
   ```

2. **Update ci-success job** to include new job:
   ```yaml
   needs: [build, test-servers, ..., test-new-feature]
   ```

3. **Test locally first**:
   ```bash
   make test-new-feature  # Should pass
   git push               # Triggers CI
   ```

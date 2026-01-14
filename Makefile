.PHONY: up down build logs test clean setup wizard agent help

# Show help
help:
	@echo "MCP Lab - Make Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make wizard      - Interactive setup wizard (recommended for beginners)"
	@echo "  make setup       - Quick setup (copy .env.dist to .env)"
	@echo "  make up          - Start services with external Ollama"
	@echo "  make up-local    - Start services with local Ollama container"
	@echo ""
	@echo "Testing:"
	@echo "  make test        - Run all tests (servers + agent)"
	@echo "  make test-servers - Test MCP servers only"
	@echo "  make test-file   - Test file server only"
	@echo "  make test-db     - Test database server only"
	@echo ""
	@echo "Agent:"
	@echo "  make agent MSG='your prompt' - Run agent with custom prompt"
	@echo "  make agent-file  - Run agent with file test"
	@echo "  make agent-db    - Run agent with database test"
	@echo ""
	@echo "Management:"
	@echo "  make logs        - View service logs"
	@echo "  make down        - Stop all services"
	@echo "  make clean       - Stop and remove everything (including volumes)"
	@echo "  make build       - Rebuild all images"
	@echo ""

# Interactive setup wizard (recommended for first-time users)
wizard:
	@echo "Starting MCP Lab Setup Wizard..."
	@docker compose run --rm wizard

# Create .env from .env.dist if not exists (quick setup)
setup:
	@if [ ! -f .env ]; then \
		cp .env.dist .env; \
		echo "Created .env from .env.dist"; \
	else \
		echo ".env already exists"; \
	fi

# Default: Build and start services (Uses external Ollama by default)
up: setup
	docker compose up --build -d mcp-file mcp-db postgres

# Start WITH Local Ollama (Self-Contained)
up-local: setup
	@echo "Starting with Local Ollama..."
	OLLAMA_URL=http://ollama:11434 docker compose --profile local-llm up --build -d mcp-file mcp-db postgres ollama
	@echo "Waiting for Ollama to be ready..."
	@sleep 5
	@echo "Pulling model llama3.2:3b (this may take a while)..."
	docker compose exec ollama ollama pull llama3.2:3b
	@echo "Environment ready! Use 'make agent' (it will auto-connect to local ollama if you set OLLAMA_URL=http://localhost:11434 in your shell, OR rely on the compose networking if you run the agent inside compose)"
	
# Stop services
down:
	docker compose down

# Build images
build:
	docker compose --profile agent --profile test --profile wizard build --no-cache

# Follow logs
logs:
	docker compose logs -f

# Run ALL tests (Servers + Agent)
test: test-servers agent-file agent-db

# Run only Server Connectivity Tests (No LLM required)
test-servers:
	docker compose run --rm test-runner

# Run only File Server tests
test-file:
	docker compose run --rm test-runner python test_mcp.py file
	docker compose run --rm test-runner python test_mcp.py file

# Run only DB Server tests
test-db:
	docker compose run --rm test-runner python test_mcp.py db

# Run Interactive Agent (Requires arg: MSG="Your prompt")
agent:
	@if [ -z "$(MSG)" ]; then \
		echo "Usage: make agent MSG='your prompt'"; \
		exit 1; \
	fi
	docker compose run --rm mcp-agent "$(MSG)"

# Run Agent with File Test Query
agent-file:
	docker compose run --rm mcp-agent "Read the file hello.txt and tell me its content"

# Run Agent with DB Test Query
agent-db:
	docker compose run --rm mcp-agent "List all notes in the database and tell me who wrote them"

# Remove volumes and orphans
clean:
	docker compose down --volumes --remove-orphans

# One-shot command to get everything running and tested
verify: up
	@echo "Waiting for services to be ready..."
	@sleep 5
	make test

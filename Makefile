.PHONY: up down build logs test clean setup agent

# Create .env from .env.dist if not exists
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
	docker compose build --no-cache

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
	docker compose run --rm mcp-agent "List all notes in the database"

# Remove volumes and orphans
clean:
	docker compose down --volumes --remove-orphans

# One-shot command to get everything running and tested
verify: up
	@echo "Waiting for services to be ready..."
	@sleep 5
	make test

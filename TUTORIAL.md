# MCP Lab Extended Tutorial 🎓

Welcome to the extended learning guide for MCP Lab! This tutorial provides hands-on exercises, detailed explanations, and practical challenges to help you master AI agent development.

## Table of Contents

1. [Introduction to AI Agents](#introduction-to-ai-agents)
2. [Understanding the Agent Loop](#understanding-the-agent-loop)
3. [Using the Web Interface](#using-the-web-interface)
4. [MCP Protocol Deep Dive](#mcp-protocol-deep-dive)
5. [Reading and Modifying Code](#reading-and-modifying-code)
6. [Building Your First Tool](#building-your-first-tool)
7. [Advanced Patterns](#advanced-patterns)
8. [Debugging Techniques](#debugging-techniques)
9. [Challenges and Exercises](#challenges-and-exercises)

---

## Introduction to AI Agents

### What is an AI Agent?

An **AI Agent** is a system that:
1. **Perceives** its environment (receives input)
2. **Reasons** about what to do (uses an LLM)
3. **Acts** on the environment (executes tools)
4. **Learns** from results (improves over time)

**Think of it like a human assistant**:
- You ask: "What's the weather?" (input)
- They think: "I need to check a weather service" (reasoning)
- They act: Opens weather app, checks forecast (tool use)
- They respond: "It's 72°F and sunny" (output)

### Why Agents Matter

Traditional LLMs are limited to their training data:
- **Without agents**: "I don't have real-time weather data"
- **With agents**: *Checks weather API* "It's currently 72°F in your location"

Agents give LLMs "arms and legs" to interact with the real world!

---

## Understanding the Agent Loop

### Exercise 1: Observe the Agent Loop

**Goal**: Watch the agent loop in action with detailed output.

```bash
# Run this command and observe each step
make agent MSG="Who wrote the note about groceries?"
```

**What you'll see**:

```
➤ STEP 1: Discovery & Assembly
  ✓ Loaded 1 tools from http://mcp-file:3333
  ✓ Loaded 1 tools from http://mcp-db:3334
  ℹ Total tools available: 2

➤ STEP 2: Reasoning (Sending to LLM)
  ℹ Sending request to Ollama (llama3.2:3b)...
  ✓ Ollama responded in 0.52s

➤ STEP 3: Decision Evaluation
  🧠 The model decided it needs more information.

➤ STEP 4: Tool Execution
  🛠️  Calling: query_db
      Args: {"sql": "SELECT u.username FROM users u JOIN notes n ..."}
      ✓ Result: [{"username": "alice"}]

➤ STEP 5: Synthesis (Feeding back results)
  ℹ Sending tool outputs back to Ollama...

➤ STEP 6: Final Answer
Alice wrote the note about groceries.
```

**Analysis Questions**:
1. What tools were discovered in Step 1?
2. How long did Ollama take to respond?
3. What SQL query did the LLM generate?
4. How many round trips to Ollama occurred? (Hint: Steps 2 and 5)

---

## Using the Web Interface

MCP Lab includes a Streamlit-based web interface that makes it easier to visualize the agent loop in action.

### Exercise 1.5: Explore with the GUI

**Goal**: Use the web interface to see the agent loop visually.

**Steps**:

1. Start the services and GUI:
   ```bash
   # If using external Ollama
   make up && make gui

   # Or with local Ollama
   make up-local && make gui
   ```

2. Open http://localhost:8501 in your browser

3. Try these queries:
   - "Read hello.txt"
   - "Who wrote the groceries note?"
   - "List all users in the database"

**What to observe**:

- **Progress indicator**: Watch as the agent moves through each step
- **Step labels**: See Discovery, Reasoning, Decision, Execution, Synthesis in real-time
- **Tool calls**: See which tools are called and with what arguments
- **Results**: See the raw results from each tool
- **History**: Click "View Agent Loop Details" on past messages to review what happened

**Learning Point**:

The GUI uses the same `MCPAgent` class as the CLI, but instead of printing to terminal,
it consumes events from a generator. This pattern (separating logic from presentation)
is called **separation of concerns** and makes code more flexible.

Check `client/gui.py` to see how the Streamlit UI consumes events from `MCPAgent.run()`.

---

## MCP Protocol Deep Dive

### Exercise 2: Observe the Protocol via Logs

**Goal**: Understand the MCP protocol by observing the communication between the agent and servers.

With the upgrade to **FastMCP**, our servers now use the full Model Context Protocol, which involves session management (initialization, handshakes, and session IDs). Therefore, manual testing is best performed using the built-in test runner or the agent itself.

#### Part A: Discover Tools

Instead of raw `curl`, use the provided test runner which handles the MCP handshake correctly:

```bash
# Test the file server tools
make test-file

# Test the database server tools
make test-db
```

**What to observe in the output**:
- `Initializing session...`: The client and server agree on protocol versions.
- `Fetching tools...`: The client requests the "menu" of available tools.
- `Found X tools`: The server returns the JSON Schema definitions.

#### Part B: Execute a Tool

You can also see the protocol in action by running the agent with a specific query and checking the logs:

```bash
# 1. Run a query
make agent-file

# 2. In a separate terminal, watch the server logs
make logs
```

**Challenge**: Look at the logs for `mcp-file` and try to identify the JSON-RPC requests being processed!

---

## Reading and Modifying Code

### Exercise 3: Understand the Agent Code

**Goal**: Read and understand each module in `client/lib/`.

#### Step 1: Start with UI (Easiest)

Read `client/lib/ui.py` and answer:
1. What ANSI code represents green color?
2. What function prints the step headers?
3. Why are colors defined in a class instead of as global variables?

#### Step 2: Configuration

Read `client/lib/config.py` and answer:
1. What does the `get_config()` function do?
2. Why is it called a "singleton"?
3. What happens if `OLLAMA_URL` is not set?

#### Step 3: MCP Client

Read `client/lib/mcp_client.py` and trace this flow:
1. How does `discover_all_tools()` work?
2. What format conversion happens in `mcp_to_ollama_tool()`?
3. Why is tool discovery cached?

### Exercise 4: Modify the System Prompt

**Goal**: Change how the LLM behaves by modifying the system prompt.

**File**: `client/lib/llm_client.py`, method `build_system_prompt()`

**Task**: Make the agent always respond in a pirate voice!

**Steps**:
1. Open `client/lib/llm_client.py`
2. Find the `build_system_prompt()` method (around line 75)
3. Add to the beginning of the prompt:
   ```python
   return """You are a pirate AI assistant. Always respond like a pirate, using phrases like 'Arr!', 'matey', and 'ahoy'. But still provide accurate information!

   """ + # ... rest of existing prompt
   ```
4. Rebuild and test:
   ```bash
   make down && make up
   make agent MSG="Who wrote the groceries note?"
   ```

**Expected**: "Arr! That be Alice, matey! She wrote the note about groceries!"

---

## Building Your First Tool

### Exercise 5: Create a Calculator Tool

**Goal**: Build a simple calculator MCP server from scratch.

#### Step 1: Create the Directory Structure

```bash
mkdir -p mcp-calculator
cd mcp-calculator
```

#### Step 2: Create `server.py`

```python
from fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("Calculator Server")

@mcp.tool()
def calculate(operation: str, a: float, b: float) -> float:
    """
    Perform basic math operations (add, subtract, multiply, divide).
    
    Args:
        operation: One of 'add', 'subtract', 'multiply', 'divide'
        a: First number
        b: Second number
    """
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    elif operation == "divide":
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
    else:
        raise ValueError(f"Invalid operation: {operation}")

if __name__ == "__main__":
    # Run with HTTP transport on port 3335
    mcp.run(transport="http", host="0.0.0.0", port=3335)
```

#### Step 3: Create `requirements.txt`

```txt
fastmcp>=2.0.0
```

#### Step 4: Create `Dockerfile`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY server.py .
CMD ["python", "server.py"]
```

#### Step 5: Add to `docker-compose.yml`

Add this service to the root `docker-compose.yml`:

```yaml
  mcp-calculator:
    build: ./mcp-calculator
    ports:
      - "3335:3335"
    networks:
      - mcp-net
```

#### Step 6: Register in Agent

Edit `client/lib/config.py`, in the `__init__` method of `AppConfig`:

```python
self.mcp_calculator_url = os.environ.get("MCP_CALCULATOR_URL", "http://mcp-calculator:3335")

# In server_map registration
self.server_map["calculate"] = self.mcp_calculator_url
```

#### Step 7: Test It!

```bash
# Restart services
make down && make up

# Test the calculator
make agent MSG="What is 42 multiplied by 17?"
```

**Expected**: "The result is 714."

---

## Advanced Patterns

### Exercise 6: Tool Chaining

**Goal**: Make the agent use multiple tools in sequence.

**Challenge**: Create a file that contains a math expression, then ask the agent to read it and calculate the result.

**Steps**:

1. Create a file with a math problem:
   ```bash
   echo "25 + 17" > mcp-file/data/math_problem.txt
   ```

2. Ask the agent to solve it:
   ```bash
   make agent MSG="Read math_problem.txt and calculate the result"
   ```

**What should happen**:
1. Agent reads the file: `read_file("math_problem.txt")` → "25 + 17"
2. Agent calculates: `calculate("add", 25, 17)` → 42
3. Agent responds: "The result is 42"

### Exercise 7: Error Handling

**Goal**: See how the agent handles errors.

**Test invalid file path**:
```bash
make agent MSG="Read the file ../../etc/passwd"
```

**Expected**: The file server blocks the path traversal attempt.

**Test invalid SQL**:
```bash
make agent MSG="Run this query: DROP TABLE users;"
```

**Observe**: How does the sanitizer handle this?

---

## Debugging Techniques

### Technique 1: Check Service Logs

```bash
# View all logs in real-time
make logs

# View specific service
docker compose logs mcp-file
docker compose logs ollama
```

### Technique 2: Test Services Individually

```bash
# Test MCP servers without the agent
make test-servers

# Test file server only
curl http://localhost:3333/tools
```

### Technique 3: Inspect the Database

```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U mcp -d mcp

# Run SQL queries directly
SELECT * FROM users;
SELECT * FROM notes;
\q  # quit
```

### Technique 4: Add Debug Prints

Edit `client/agent.py` to add more logging:

```python
# In the chat() function, after getting tool results
print(f"\n[DEBUG] Tool results: {results}\n")
```

---

## Challenges and Exercises

### Challenge 1: Weather Tool (Beginner)

**Task**: Create a mock weather tool that returns fake weather data.

**Hints**:
- Similar structure to the calculator tool
- Return temperature, conditions, humidity
- Use a dictionary of cities with mock data

### Challenge 2: Multi-Step Planning (Intermediate)

**Task**: Make the agent handle a complex multi-step query.

**Example Query**:
```
"Find all notes written by alice, read any files mentioned in those notes,
and summarize the content."
```

**Hints**:
- The agent needs to:
  1. Query database for Alice's notes
  2. Extract file names from note content
  3. Read those files
  4. Summarize everything

### Challenge 3: Tool with External API (Advanced)

**Task**: Create a real weather tool using a weather API.

**Requirements**:
- Use OpenWeatherMap API (free tier)
- Handle API errors gracefully
- Cache responses to avoid rate limits
- Add proper error messages

**File**: `mcp-weather/server.py`

<details>
<summary>Starter code</summary>

```python
import os
import requests
from fastmcp import FastMCP

mcp = FastMCP("Weather Server")
API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")

@mcp.tool()
def get_weather(city: str) -> dict:
    """
    Get current weather for a city.
    
    Args:
        city: Name of the city (e.g., 'London', 'Rome')
    """
    url = f"http://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": API_KEY, "units": "metric"}

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()

        return {
            "city": city,
            "temperature": data["main"]["temp"],
            "conditions": data["weather"][0]["description"],
            "humidity": data["main"]["humidity"]
        }
    except Exception as e:
        raise ValueError(f"Weather API error: {str(e)}")

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=3335)
```
</details>

### Challenge 4: Conversation Memory (Advanced)

**Task**: Add conversation history so the agent remembers previous queries.

**Requirements**:
- Store message history in a file or database
- Load history on agent startup
- Append new messages
- Limit history to last N messages (avoid context overflow)

**Hints**:
- Modify `client/lib/llm_client.py`
- Add `load_history()` and `save_history()` methods
- Update `create_conversation()` to include history

---

## Learning Path Summary

**Week 1**: Run examples, understand the agent loop
- ✅ Complete Exercises 1-2
- ✅ Read README thoroughly
- ✅ Understand MCP protocol

**Week 2**: Read code, understand modules
- ✅ Complete Exercise 3
- ✅ Read all files in `client/lib/`
- ✅ Understand separation of concerns

**Week 3**: Modify existing code
- ✅ Complete Exercise 4
- ✅ Try different system prompts
- ✅ Modify tool behavior

**Week 4**: Build new tools
- ✅ Complete Exercise 5 (Calculator)
- ✅ Try Challenge 1 (Weather)
- ✅ Understand MCP server structure

**Week 5**: Advanced patterns
- ✅ Complete Exercises 6-7
- ✅ Try Challenges 2-3
- ✅ Build your own custom agent

---

## Additional Resources

### Concepts to Learn

- **LLM Function Calling**: How LLMs request tools
- **JSON Schema**: How to describe tool inputs
- **FastAPI**: Building HTTP APIs in Python
- **Docker Compose**: Orchestrating microservices
- **PostgreSQL**: Relational databases

### Recommended Reading

- [MCP Specification](https://github.com/anthropics/mcp)
- [OpenAI Function Calling Guide](https://platform.openai.com/docs/guides/function-calling)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Ollama Documentation](https://ollama.ai/docs)

### Next Projects

After mastering this lab, try building:
- **Personal Assistant Agent**: Email, calendar, todos
- **Research Agent**: Web search, summarization
- **Code Agent**: Run tests, fix bugs, generate code
- **Data Analysis Agent**: SQL queries, charts, insights

---

## Troubleshooting Common Learning Issues

### "I don't understand why we need tools"

**Answer**: LLMs are trained on static data. They can't:
- Read your current files
- Check today's weather
- Query your database
- Make API calls

Tools give them these abilities!

### "Why use MCP instead of hardcoding tools?"

**Answer**: MCP is a *standard*. With MCP:
- Tools are discoverable (agent doesn't need to know them upfront)
- Tools are portable (same tool works with any MCP agent)
- Schema is self-documenting (tools describe themselves)

### "This seems complicated for a simple query"

**Answer**: Yes! For simple tasks, calling an API directly is easier. But agents shine when:
- You don't know which tool to use upfront
- You need to chain multiple tools
- The task requires reasoning about results

---

## Congratulations! 🎉

You've completed the MCP Lab tutorial! You now understand:
- ✅ How AI agents work (the agent loop)
- ✅ The Model Context Protocol
- ✅ How to read and modify agent code
- ✅ How to build your own MCP tools
- ✅ Debugging and troubleshooting techniques

**Keep building and learning!** The best way to master agents is to build your own.

---

**Questions or feedback?** Open an issue on GitHub or contribute improvements to this tutorial!

**Happy building!** 🚀

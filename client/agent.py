import os
import requests
import json
import sys

# Configuration
OLLAMA_URL = os.environ.get("OLLAMA_URL", "https://myollama.my.address.it")
MODEL_NAME = os.environ.get("MODEL_NAME", "llama3") # Default model
MCP_FILE_URL = os.environ.get("MCP_FILE_URL", "http://mcp-file:3333")
MCP_DB_URL = os.environ.get("MCP_DB_URL", "http://mcp-db:3334")

SERVER_MAP = {
    "read_file": MCP_FILE_URL,
    "query_db": MCP_DB_URL
}

def get_tools_from_server(url):
    try:
        resp = requests.get(f"{url}/tools", timeout=2)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Warning: Could not fetch tools from {url}: {e}", file=sys.stderr)
        return []

def mcp_to_ollama_tool(mcp_tool):
    """Adapt MCP tool definition to Ollama/OpenAI format."""
    return {
        "type": "function",
        "function": {
            "name": mcp_tool["name"],
            "description": mcp_tool["description"],
            "parameters": mcp_tool["inputSchema"]
        }
    }

def chat(prompt):
    # 1. Gather tools
    tools = []
    file_tools = get_tools_from_server(MCP_FILE_URL)
    db_tools = get_tools_from_server(MCP_DB_URL)
    
    all_mcp_tools = file_tools + db_tools
    ollama_tools = [mcp_to_ollama_tool(t) for t in all_mcp_tools]

    messages = [{"role": "user", "content": prompt}]
    
    print(f"🤖 Sending request to Ollama ({OLLAMA_URL}) with {len(ollama_tools)} tools...")
    
    # 2. First call to Ollama
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "tools": ollama_tools,
        "stream": False 
    }
    
    try:
        # User confirmed valid certificate, enabling verification
        resp = requests.post(f"{OLLAMA_URL}/api/chat", json=payload) 
        
        if resp.status_code != 200:
             print(f"❌ Ollama API Error ({resp.status_code}):")
             print(resp.text)
             resp.raise_for_status()
             
        response_data = resp.json()
        message = response_data.get("message", {})
        
        # 3. Check for tool calls
        if message.get("tool_calls"):
            print("🛠️  Model requested tool execution:")
            messages.append(message) # Add assistant's response history
            
            for tool_call in message["tool_calls"]:
                func_name = tool_call["function"]["name"]
                args = tool_call["function"]["arguments"]
                
                print(f"   -> Executing {func_name} with {json.dumps(args)}")
                
                # Execute against appropriate MCP server
                server_url = SERVER_MAP.get(func_name)
                if server_url:
                    tool_resp = requests.post(f"{server_url}/call", json={
                        "name": func_name,
                        "arguments": args
                    })
                    if tool_resp.status_code == 200:
                        tool_result = tool_resp.json()
                        # MCP servers return raw result, typically dict.
                        # We need to serialize for chat history
                        content_str = json.dumps(tool_result)
                    else:
                        content_str = f"Error: {tool_resp.text}"
                else:
                    content_str = "Error: Tool unknown to client routing map."

                print(f"   <- Result: {content_str[:100]}...")

                # Add tool result to history
                messages.append({
                    "role": "tool",
                    "content": content_str,
                })
            
            # 4. Follow-up call to Ollama with results
            print("🤖 Sending results back to Ollama...")
            payload["messages"] = messages
            
            resp = requests.post(f"{OLLAMA_URL}/api/chat", json=payload)
            if resp.status_code != 200:
                 print(f"❌ Ollama API Error (Follow-up) ({resp.status_code}):")
                 print(resp.text)
                 resp.raise_for_status()

            final_data = resp.json()
            print("\n📝 Final Answer:")
            print(final_data["message"]["content"])
            
        else:
            print("\n📝 Answer:")
            print(message["content"])

    except Exception as e:
        print(f"❌ Error communicating with Ollama or Tools: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = "Hello! what tools do you have?"
    
    chat(prompt)

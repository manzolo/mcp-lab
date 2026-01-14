import requests
import json
import time
import sys
import os

# Default to localhost for local testing, can be overridden by env vars for container
MCP_FILE_URL = os.environ.get("MCP_FILE_URL", "http://localhost:3333")
MCP_DB_URL = os.environ.get("MCP_DB_URL", "http://localhost:3334")

def test_server(name, url):
    print(f"\n--- Testing {name} Server ({url}) ---")
    
    # 1. Get Tools
    try:
        resp = requests.get(f"{url}/tools")
        resp.raise_for_status()
        tools = resp.json()
        print(f"✅ /tools: Found {len(tools)} tools")
        print(json.dumps(tools, indent=2))
        
        # 2. Call Tool
        if name == "MCP File":
            payload = {
                "name": "read_file",
                "arguments": {"path": "hello.txt"}
            }
        elif name == "MCP DB":
            payload = {
                "name": "query_db",
                "arguments": {"sql": "SELECT * FROM notes;"}
            }
            
        print(f"Testing /call with: {json.dumps(payload)}")
        resp = requests.post(f"{url}/call", json=payload)
        
        if resp.status_code == 200:
            print("✅ /call: Success")
            print(json.dumps(resp.json(), indent=2))
        else:
            print(f"❌ /call: Failed ({resp.status_code})")
            print(resp.text)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        # Fail the script if major errors occur, useful for CI/CD
        sys.exit(1)

def main():
    print("Waiting for servers to be up...")
    time.sleep(2) 
    
    args = sys.argv[1:]
    run_all = not args

    if run_all or "file" in args:
        test_server("MCP File", MCP_FILE_URL)
    
    if run_all or "db" in args:
        test_server("MCP DB", MCP_DB_URL)

if __name__ == "__main__":
    main()

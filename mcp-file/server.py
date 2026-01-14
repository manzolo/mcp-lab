import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()
DATA_DIR = Path("/data")

class CallRequest(BaseModel):
    name: str
    arguments: dict

@app.get("/tools")
async def list_tools():
    return [
        {
            "name": "read_file",
            "description": "Read content of a text file from the data directory",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to file (e.g., 'notes.txt')"
                    }
                },
                "required": ["path"]
            }
        }
    ]

@app.post("/call")
async def call_tool(request: CallRequest):
    if request.name != "read_file":
        raise HTTPException(status_code=404, detail="Tool not found")
    
    path_str = request.arguments.get("path")
    if not path_str:
        raise HTTPException(status_code=400, detail="Missing path argument")

    # Prevent path traversal
    try:
        requested_path = (DATA_DIR / path_str).resolve()
        if not requested_path.is_relative_to(DATA_DIR):
             raise HTTPException(status_code=403, detail="Access denied: Path traversal attempt")
        
        if not requested_path.exists():
             raise HTTPException(status_code=404, detail="File not found")
             
        if not requested_path.is_file():
             raise HTTPException(status_code=400, detail="Path is not a file")

        return {"content": requested_path.read_text(encoding="utf-8")}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    print("Starting MCP File Server on port 3333...")
    uvicorn.run(app, host="0.0.0.0", port=3333)

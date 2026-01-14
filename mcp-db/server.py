import os
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# Database connection parameters from environment
DB_HOST = os.environ.get("DB_HOST", "postgres")
DB_NAME = os.environ.get("DB_NAME", "mcp")
DB_USER = os.environ.get("DB_USER", "mcp")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "mcp")

class CallRequest(BaseModel):
    name: str
    arguments: dict

def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")

@app.get("/tools")
async def list_tools():
    return [
        {
            "name": "query_db",
            "description": "Execute a SQL query against the database. Available tables:\n"
                           "CREATE TABLE users (id SERIAL PRIMARY KEY, username VARCHAR(50), email VARCHAR(100));\n"
                           "CREATE TABLE notes (id SERIAL PRIMARY KEY, user_id INTEGER REFERENCES users(id), title VARCHAR(255), content TEXT, created_at TIMESTAMP);",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "SQL query to execute"
                    }
                },
                "required": ["sql"]
            }
        }
    ]

@app.post("/call")
async def call_tool(request: CallRequest):
    if request.name != "query_db":
        raise HTTPException(status_code=404, detail="Tool not found")
    
    sql = request.arguments.get("sql")
    if not sql:
        raise HTTPException(status_code=400, detail="Missing sql argument")

    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(sql)
        
        # Check if query returns rows
        if cur.description:
            rows = cur.fetchall()
            result = [dict(row) for row in rows]
        else:
            conn.commit()
            result = [{"status": "success", "rows_affected": cur.rowcount}]
            
        cur.close()
        conn.close()
        return result

    except Exception as e:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=500, detail=f"Query error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print(f"Starting MCP DB Server on port 3334... DB_HOST={DB_HOST}")
    uvicorn.run(app, host="0.0.0.0", port=3334)

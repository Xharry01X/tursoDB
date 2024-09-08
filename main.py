import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import libsql_experimental as libsql

# Load environment variables
load_dotenv()

# Database connection details
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")

# Pydantic model for user data
class User(BaseModel):
    name: str
    email: str

# Initialize FastAPI app
app = FastAPI()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to database
    app.state.conn = libsql.connect("hello.db", sync_url=TURSO_DATABASE_URL, auth_token=TURSO_AUTH_TOKEN)
    app.state.conn.sync()
    print("Connected to Turso database.")
    
    yield
    
    # Shutdown: The libsql_experimental Connection object doesn't have a close() method
    # Resources might be automatically managed by the library
    print("Application shutting down.")

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def read_root():
    try:
        result = app.state.conn.execute("SELECT 'Connected to Turso!' as message")
        return {"message": result.fetchone()[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tables")
async def get_tables():
    try:
        result = app.state.conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in result.fetchall()]
        return {"tables": tables}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/query")
async def execute_query(query: str):
    try:
        result = app.state.conn.execute(query)
        return {"result": [dict(row) for row in result.fetchall()]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/create_table")
async def create_table():
    try:
        app.state.conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL
            )
        """)
        return {"message": "Table 'users' created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/add_user")
async def add_user(user: User):
    try:
        app.state.conn.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)",
            (user.name, user.email)
        )
        return {"message": f"User {user.name} added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users")
async def get_users():
    try:
        result = app.state.conn.execute("SELECT * FROM users")
        users = [dict(row) for row in result.fetchall()]
        return {"users": users}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
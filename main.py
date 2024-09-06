import os
from dotenv import load_dotenv
import libsql_experimental as libsql
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List

# Load environment variables from .env file
load_dotenv()

# Retrieve database credentials from environment variables
TURSO_DATABASE_URL = os.getenv('TURSO_DATABASE_URL')
TURSO_AUTH_TOKEN = os.getenv('TURSO_AUTH_TOKEN')

# Check if environment variables are set
if not TURSO_DATABASE_URL:
    raise ValueError("TURSO_DATABASE_URL is not set in the environment variables")
if not TURSO_AUTH_TOKEN:
    raise ValueError("TURSO_AUTH_TOKEN is not set in the environment variables")

# Local SQLite database file
LOCAL_DB_FILE = "local.db"

# Initialize FastAPI app
app = FastAPI()

# Pydantic model for User
class User(BaseModel):
    id: int
    name: str

class UserCreate(BaseModel):
    name: str

# Function to create a connection to the database
def get_db():
    try:
        conn = libsql.connect(
            LOCAL_DB_FILE,
            sync_url=TURSO_DATABASE_URL,
            auth_token=TURSO_AUTH_TOKEN
        )
        yield conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        print(f"TURSO_DATABASE_URL: {TURSO_DATABASE_URL}")
        print(f"TURSO_AUTH_TOKEN: {'*' * len(TURSO_AUTH_TOKEN) if TURSO_AUTH_TOKEN else 'Not set'}")
        raise
    finally:
        # Note: libsql_experimental doesn't have a close() method as of now
        # If it's added in the future, you would close the connection here
        pass

# Create tables on startup (only in local database)
@app.on_event("startup")
async def startup_event():
    try:
        conn = libsql.connect(LOCAL_DB_FILE)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)
        conn.commit()
        print("Local database initialized successfully")
    except Exception as e:
        print(f"Error during startup: {e}")
        raise

# Routes
@app.post("/users/", response_model=User)
def create_user(user: UserCreate, db: libsql.Connection = Depends(get_db)):
    cursor = db.execute("INSERT INTO users (name) VALUES (?) RETURNING id, name", (user.name,))
    new_user = cursor.fetchone()
    db.commit()
    return User(id=new_user[0], name=new_user[1])

@app.get("/users/", response_model=List[User])
def read_users(db: libsql.Connection = Depends(get_db)):
    cursor = db.execute("SELECT id, name FROM users")
    users = cursor.fetchall()
    return [User(id=user[0], name=user[1]) for user in users]

@app.get("/users/{user_id}", response_model=User)
def read_user(user_id: int, db: libsql.Connection = Depends(get_db)):
    cursor = db.execute("SELECT id, name FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return User(id=user[0], name=user[1])

@app.post("/sync/", response_model=dict)
def sync_database(db: libsql.Connection = Depends(get_db)):
    try:
        db.sync()
        return {"message": "Database synced successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
import os
from fastapi import FastAPI, Depends
from sqlalchemy import create_engine, Column, Integer, String, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection details
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")

# Construct the DSN (Data Source Name)
DSN = f"{TURSO_DATABASE_URL}?authToken={TURSO_AUTH_TOKEN}"

# Create SQLAlchemy engine
engine = create_engine(f"sqlite+{DSN}", connect_args={"check_same_thread": False})

# Create declarative base
Base = declarative_base()

# Define User model
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Initialize FastAPI app
app = FastAPI()

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create schema
def create_schema():
    Base.metadata.create_all(bind=engine)

# Initialize database
@app.on_event("startup")
async def startup_event():
    create_schema()
    print("Database initialized and schema created.")

# Root endpoint
@app.get("/")
def read_root(db: Session = Depends(get_db)):
    return {"message": "Connected to Turso database"}

# Example endpoint to create a user
@app.post("/users/")
def create_user(username: str, password: str, db: Session = Depends(get_db)):
    new_user = User(username=username, password=password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"id": new_user.id, "username": new_user.username}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
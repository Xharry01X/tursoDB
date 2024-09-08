import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv
import libsql_experimental as libsql



load_dotenv()


db_url = os.getenv("TURSO_DATABASE_URL")
auth_token = os.getenv("TURSO_AUTH_TOKEN")


@asynccontextmanager
async def lifespan(app: FastAPI):
    
    app.state.pool = libsql.create_pool(
        url = db_url,
        auth_token = auth_token
    )
    
    print("Connected to Turso Database")
    yield
    
    await app.state.pool.close()
    print("Disconnected from Turso Database")
    
app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    async with app.state.pool.connection() as conn:
        result = await conn.execute("SELECT 'Hello, Turso!' as message")
        row = await result.fetchone()
        return {"message": row[0]}
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
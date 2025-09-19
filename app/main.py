import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from .db import init_db, close_db
from .routes import tasks, chat

# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    await init_db()
    print("Database initialized")
    yield
    # Shutdown
    await close_db()
    print("Database connections closed")


# Create FastAPI app
app = FastAPI(
    title="Task Management API",
    description="A FastAPI backend with AI-powered task management using LangGraph and Gemini",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tasks.router, prefix="/api")
app.include_router(chat.router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Task Management API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }




@app.get("/api/info")
async def api_info():
    """API information endpoint"""
    return {
        "endpoints": {
            "tasks": "/api/tasks",
            "chat": "/api/chat",
            "websockets": {
                "chat": "/api/chat/ws",
                "task_updates": "/api/chat/ws/tasks"
            }
        },
        "features": [
            "CRUD operations for tasks",
            "AI-powered task management with Gemini",
            "Real-time WebSocket communication",
            "Task filtering and search",
            "Async database operations with PostgreSQL"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    debug = os.getenv("DEBUG", "True").lower() == "true"
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )
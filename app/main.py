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
    try:
        await init_db()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Warning: Database connection failed: {e}")
        print("Application will start but database features may not work")
    yield
    # Shutdown
    try:
        await close_db()
        print("Database connections closed")
    except Exception as e:
        print(f"Warning during database cleanup: {e}")


# Create FastAPI app
app = FastAPI(
    title="Task Management API",
    description="A FastAPI backend with AI-powered task management using LangGraph and Gemini",
    version="1.0.0",
    lifespan=lifespan
)

# Print startup info
print("=" * 50)
print("FASTAPI APP CONFIGURATION")
print(f"Title: {app.title}")
print(f"Version: {app.version}")
print(f"PORT env var: {os.getenv('PORT', 'NOT SET')}")
print(f"Railway ENV: {os.getenv('RAILWAY_ENVIRONMENT', 'NOT SET')}")
print("=" * 50)

# CORS configuration
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
print(f"CORS origins: {allowed_origins}")

# Handle different formats
if allowed_origins == "*":
    cors_origins = ["*"]
else:
    cors_origins = allowed_origins.split(",")

print(f"Processed CORS origins: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request, call_next):
    print(f"=== INCOMING REQUEST ===")
    print(f"Method: {request.method}")
    print(f"URL: {request.url}")
    print(f"Headers: {dict(request.headers)}")
    print(f"Client: {request.client}")
    response = await call_next(request)
    print(f"=== RESPONSE ===")
    print(f"Status: {response.status_code}")
    print(f"========================")
    return response

# Include routers
try:
    app.include_router(tasks.router, prefix="/api")
    print("Tasks router included successfully")
except Exception as e:
    print(f"Error including tasks router: {e}")

try:
    app.include_router(chat.router, prefix="/api")
    print("Chat router included successfully")
except Exception as e:
    print(f"Error including chat router: {e}")


@app.get("/")
async def root():
    """Root endpoint"""
    print("Root endpoint accessed")
    return {
        "message": "Task Management API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "timestamp": "2025-09-19"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "task-management-api",
        "version": "1.0.0"
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
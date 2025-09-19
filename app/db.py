import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from .models import Base

# Load environment variables
load_dotenv()

# Database URL from environment with debugging
DATABASE_URL = os.getenv("DATABASE_URL")
print(f"Database URL loaded: {DATABASE_URL is not None}")

if not DATABASE_URL:
    print("Warning: DATABASE_URL not found, using default")
    DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/taskdb"
else:
    # Ensure the URL has the correct async driver
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
        print("Fixed DATABASE_URL to use asyncpg driver")

print(f"Final DATABASE_URL: {DATABASE_URL[:50]}...")

# Create async engine with better error handling
try:
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,  # Reduce logging in production
        future=True,
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=300,    # Recycle connections every 5 minutes
        connect_args={
            "server_settings": {
                "application_name": "railway_taskmanager",
            }
        }
    )
    print("Database engine created successfully")
except Exception as e:
    print(f"Error creating database engine: {e}")
    # Create a dummy engine to prevent import errors
    engine = None

# Create async session factory
if engine:
    AsyncSessionLocal = sessionmaker(
        engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
else:
    AsyncSessionLocal = None

async def init_db():
    """Initialize the database by creating all tables"""
    if not engine:
        print("Skipping database initialization - no engine available")
        return
    
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Database tables created successfully")
    except Exception as e:
        print(f"Failed to initialize database: {e}")
        raise

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session"""
    if not AsyncSessionLocal:
        raise RuntimeError("Database not available")
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def close_db():
    """Close database connections"""
    if engine:
        await engine.dispose()
        print("Database connections closed")
import os
import asyncio
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

# Create async engine with better error handling and Railway compatibility
try:
    # Connection arguments for better Railway <-> Supabase connectivity
    connect_args = {
        "server_settings": {
            "application_name": "railway_taskmanager",
        },
        # Add SSL configuration for Supabase
        "ssl": "require",
        # Connection timeout settings
        "command_timeout": 30,
        "connect_timeout": 10,
    }
    
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,  # Reduce logging in production
        future=True,
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=300,    # Recycle connections every 5 minutes
        pool_timeout=20,     # Wait time for getting connection from pool
        max_overflow=10,     # Additional connections beyond pool size
        connect_args=connect_args
    )
    print("Database engine created successfully with Railway optimizations")
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
    
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            print(f"Database connection attempt {attempt + 1}/{max_retries}")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("Database tables created successfully")
            return
        except Exception as e:
            print(f"Database connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            else:
                print("All database connection attempts failed")
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
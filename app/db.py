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
    
    # Railway PostgreSQL typically doesn't need SSL enforcement
    # but we'll detect Railway environment and adjust accordingly
    is_railway = os.getenv("RAILWAY_ENVIRONMENT") is not None
    
    if is_railway:
        print("Railway environment detected - using Railway PostgreSQL optimizations")
        # Railway's internal PostgreSQL doesn't need SSL mode for internal connections
        if "sslmode=" not in DATABASE_URL:
            if "?" in DATABASE_URL:
                DATABASE_URL += "&sslmode=prefer"
            else:
                DATABASE_URL += "?sslmode=prefer"
    else:
        # For external databases like Supabase, require SSL
        if "sslmode=" not in DATABASE_URL:
            if "?" in DATABASE_URL:
                DATABASE_URL += "&sslmode=require"
            else:
                DATABASE_URL += "?sslmode=require"
            print("Added SSL mode requirement for external database")

print(f"Final DATABASE_URL: {DATABASE_URL[:50]}...")

# Create async engine optimized for Railway PostgreSQL
try:
    # Connection arguments optimized for Railway
    connect_args = {
        "server_settings": {
            "application_name": "railway_taskmanager",
        }
    }
    
    # Adjust pool settings based on environment
    if is_railway:
        # Railway PostgreSQL can handle more connections
        pool_settings = {
            "pool_size": 10,
            "max_overflow": 20,
            "pool_timeout": 30,
            "pool_recycle": 3600,  # 1 hour
        }
        print("Using Railway PostgreSQL pool settings")
    else:
        # Conservative settings for external databases
        pool_settings = {
            "pool_size": 5,
            "max_overflow": 10,
            "pool_timeout": 20,
            "pool_recycle": 300,  # 5 minutes
        }
        print("Using external database pool settings")
    
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,  # Reduce logging in production
        future=True,
        pool_pre_ping=True,  # Verify connections before use
        connect_args=connect_args,
        **pool_settings
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
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

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Reduce logging in production
    future=True,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=300,    # Recycle connections every 5 minutes
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

async def init_db():
    """Initialize the database by creating all tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def close_db():
    """Close database connections"""
    await engine.dispose()
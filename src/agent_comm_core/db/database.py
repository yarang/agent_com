"""
Database session management and engine configuration.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Global engine and session maker
_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


def get_engine(
    database_url: str | None = None,
    pool_size: int = 10,
    max_overflow: int = 20,
    echo: bool = False,
) -> AsyncEngine:
    """
    Get or create the database engine.

    Args:
        database_url: Database connection URL (uses env var if not provided)
        pool_size: Connection pool size (not used for SQLite)
        max_overflow: Maximum overflow connections (not used for SQLite)
        echo: Echo SQL statements for debugging

    Returns:
        Async SQLAlchemy engine
    """
    global _engine

    if _engine is None:
        if database_url is None:
            from os import getenv

            database_url = getenv(
                "DATABASE_URL",
                "sqlite+aiosqlite:///./agent_comm.db",
            )

        # Check if using SQLite
        is_sqlite = database_url.startswith("sqlite+")

        if is_sqlite:
            # SQLite doesn't support connection pooling features
            _engine = create_async_engine(
                database_url,
                echo=echo,
            )
        else:
            # PostgreSQL and other databases support pooling
            _engine = create_async_engine(
                database_url,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_pre_ping=True,  # Verify connections before using
                echo=echo,
            )

    return _engine


async def init_db(
    database_url: str | None = None,
    drop_all: bool = False,
) -> None:
    """
    Initialize the database.

    Creates all tables. Use drop_all=True to reset the database.

    Args:
        database_url: Database connection URL
        drop_all: Drop all existing tables before creating
    """
    from agent_comm_core.db.base import Base

    engine = get_engine(database_url)

    if drop_all:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_session_maker(
    database_url: str | None = None,
) -> async_sessionmaker[AsyncSession]:
    """
    Get or create the session maker.

    Args:
        database_url: Database connection URL

    Returns:
        Async session maker
    """
    global _session_maker

    if _session_maker is None:
        engine = get_engine(database_url)
        _session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Prevent detached instance errors
        )

    return _session_maker


async def get_db_session(
    database_url: str | None = None,
) -> AsyncGenerator[AsyncSession]:
    """
    Get a database session for use in async contexts.

    Usage:
        async for session in get_db_session():
            await session.execute(...)

    Args:
        database_url: Database connection URL

    Yields:
        Async database session
    """
    session_maker = get_session_maker(database_url)

    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def db_session(
    database_url: str | None = None,
) -> AsyncGenerator[AsyncSession]:
    """
    Context manager for database sessions.

    Usage:
        async with db_session() as session:
            result = await session.execute(...)

    Args:
        database_url: Database connection URL

    Yields:
        Async database session
    """
    session_maker = get_session_maker(database_url)

    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db() -> None:
    """
    Close the database engine and all connections.

    Should be called on application shutdown.
    """
    global _engine, _session_maker

    if _engine:
        await _engine.dispose()
        _engine = None
        _session_maker = None

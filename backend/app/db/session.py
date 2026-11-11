"""
Async Database Engine, Session Management, and Non-Destructive Schema Migration.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from app.core.config import settings

connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    connect_args=connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

Base = declarative_base()


def _sqlite_type_sql(col) -> str:
    type_name = col.type.__class__.__name__.upper()
    if "INT" in type_name:
        return "INTEGER"
    if "FLOAT" in type_name or "NUMERIC" in type_name:
        return "REAL"
    if "BOOL" in type_name:
        return "BOOLEAN"
    if "DATETIME" in type_name:
        return "DATETIME"
    if "TEXT" in type_name:
        return "TEXT"
    return "VARCHAR(255)"


def _sync_sqlite_migrate(sync_engine) -> None:
    """
    Creates missing tables and safely adds missing columns to existing SQLite tables
    without losing existing data.
    """
    import app.models  # noqa: F401 - Ensure all ORM models are registered on Base.metadata

    Base.metadata.create_all(sync_engine)

    with sync_engine.begin() as conn:
        for table_name, table in Base.metadata.tables.items():
            existing_rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
            existing_cols = {row[1] for row in existing_rows}

            for col in table.columns:
                if col.name not in existing_cols:
                    sql_type = _sqlite_type_sql(col)
                    default_clause = ""
                    if col.default is not None and isinstance(col.default.arg, (bool, int, float, str)):
                        val = col.default.arg
                        if isinstance(val, bool):
                            default_clause = f" DEFAULT {1 if val else 0}"
                        elif isinstance(val, (int, float)):
                            default_clause = f" DEFAULT {val}"
                        elif isinstance(val, str):
                            escaped = val.replace("'", "''")
                            default_clause = f" DEFAULT '{escaped}'"
                    elif col.nullable:
                        default_clause = " DEFAULT NULL"

                    # SQLite ADD COLUMN requires NULL or a constant DEFAULT
                    null_clause = "" if col.nullable else (default_clause or " DEFAULT ''")
                    stmt = f"ALTER TABLE {table_name} ADD COLUMN {col.name} {sql_type}{null_clause}"
                    conn.execute(text(stmt))

                    if col.unique or col.index:
                        unique_kw = "UNIQUE " if col.unique else ""
                        idx_name = f"ix_{table_name}_{col.name}"
                        conn.execute(text(f"CREATE {unique_kw}INDEX IF NOT EXISTS {idx_name} ON {table_name} ({col.name})"))


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides an asynchronous database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Creates and migrates database tables on application startup."""
    import app.models  # noqa: F401

    if "sqlite" in settings.DATABASE_URL:
        from sqlalchemy import create_engine
        sync_url = settings.DATABASE_URL.replace("+aiosqlite", "")
        sync_engine = create_engine(sync_url, connect_args={"check_same_thread": False})
        _sync_sqlite_migrate(sync_engine)
        sync_engine.dispose()
    else:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

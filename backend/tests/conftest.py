"""Pytest fixtures.

Pure unit tests (pricing, lifecycle, signatures) need nothing here. Integration
tests use a real PostgreSQL (spin it up with `docker compose up db redis`) and the
schema in ../db/schema.sql. Set TEST_DATABASE_URL to point at a disposable database.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
import pytest_asyncio

TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://luxe:luxe@localhost:5432/luxe_test",
)
_SCHEMA = Path(__file__).resolve().parents[2] / "db" / "schema.sql"
_SEED = Path(__file__).resolve().parents[2] / "db" / "seed.sql"


@pytest_asyncio.fixture(scope="session")
async def _engine():
    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine(TEST_DB_URL, echo=False)
    # (Re)create the schema for a clean run.
    async with engine.begin() as conn:
        await conn.exec_driver_sql("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        await conn.exec_driver_sql(_SCHEMA.read_text())
        await conn.exec_driver_sql(_SEED.read_text())
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db(_engine):
    """A session wrapped in a transaction that is rolled back after each test."""
    from sqlalchemy.ext.asyncio import AsyncSession
    conn = await _engine.connect()
    txn = await conn.begin()
    session = AsyncSession(bind=conn, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await txn.rollback()
        await conn.close()


@pytest_asyncio.fixture
async def client(_engine):
    """HTTPX client bound to the ASGI app, with get_db overridden to the test DB."""
    import httpx
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.db.session import get_db
    from app.main import app

    factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

    async def _override():
        async with factory() as s:
            yield s
            await s.commit()

    app.dependency_overrides[get_db] = _override
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test/api/v1") as c:
        yield c
    app.dependency_overrides.clear()

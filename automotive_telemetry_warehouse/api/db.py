"""SQLAlchemy Core async engine/session — Settings read DATABASE_URL from env."""

from __future__ import annotations

from collections.abc import AsyncIterator

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://telemetry:telemetry@localhost:5432/telemetry"


settings = Settings()

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    pool_size=5,
    max_overflow=15,  # min_size=5, max_size=20 per the design spec
    pool_pre_ping=True,
)

async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session() as session:
        yield session

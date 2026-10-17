import os
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv
from pathlib import Path
from migraciones import aplicar_migraciones

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Database URL - support both PostgreSQL and SQLite for development
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    # PostgreSQL async URL
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql+asyncpg://', 1)
    elif DATABASE_URL.startswith('postgresql://'):
        DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://', 1)
else:
    # Default to SQLite for local development
    DATABASE_URL = "sqlite+aiosqlite:///./ethercloud.db"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    """Crea las tablas que falten. En una base nueva, además registra las migraciones como aplicadas:
    las tablas recién creadas desde los modelos ya tienen esos cambios (ver migraciones.py)."""
    async with engine.begin() as conn:
        base_nueva = not await conn.run_sync(lambda c: inspect(c).has_table("productos"))
        await conn.run_sync(Base.metadata.create_all)
    if base_nueva:
        await aplicar_migraciones(engine, base_nueva=True)

import os
from contextlib import asynccontextmanager
from enum import Enum
from typing import AsyncGenerator
from dotenv import dotenv_values, load_dotenv
from pydantic import PostgresDsn
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool
from sqlalchemy import create_engine

load_dotenv()
DB_POOL_SIZE = 83
WEB_CONCURRENCY = 9
# POOL_SIZE = max(DB_POOL_SIZE // WEB_CONCURRENCY, 5)
POOL_SIZE = 15
POOL_TIMEOUT = 5

connect_args = {"check_same_thread": False}

config = dotenv_values(".env")


class ModeEnum(str, Enum):
    development = "development"
    production = "production"
    testing = "testing"


username = config["DATABASE_USER"] or os.environ["DATABASE_USER"]
password = config["DATABASE_PASSWORD"] or os.environ["DATABASE_PASSWORD"]
host = config["DATABASE_HOST"] or os.environ["DATABASE_HOST"]
port = config["DATABASE_PORT"] or os.environ["DATABASE_PORT"]
path = config["DATABASE_NAME"] or os.environ["DATABASE_NAME"]

postgresUrl = str(
    PostgresDsn.build(
        scheme="postgresql+asyncpg",
        username=username,
        password=password,
        host=host,
        port=int(port),
        path=path,
    )
)

# in production, do not use NullPool
engine = create_async_engine(
    postgresUrl,
    echo=False,
    poolclass=
    # NullPool if ModeEnum.development == ModeEnum.testing else 
    AsyncAdaptedQueuePool,  # Asincio pytest works with NullPool
    pool_size=POOL_SIZE,
    max_overflow=15,
    pool_timeout=POOL_TIMEOUT,
    future=True
)


def async_session_generator():
    return sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@asynccontextmanager
async def create_async_session() -> AsyncGenerator[AsyncSession, None]:
    # to handle error above
    # session = SessionLocal()
    async_session = async_session_generator()
    async with async_session() as session:
        async with session.begin():
            try:
                yield session
            except Exception as e:
                await session.rollback()
                raise e
            finally:
                await session.close()


connection_string = f"postgresql://{username}:{password}@{host}:{port}/{path}"
engine_sqlalchemy = create_engine(
    connection_string,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=3600,
    pool_use_lifo=True,
    pool_pre_ping=True,
)

"""Shared pytest fixtures: a real, disposable MongoDB test database and Redis client."""

from collections.abc import Iterator

import pytest
import redis
from fastapi.testclient import TestClient
from pymongo import MongoClient
from pymongo.database import Database

from math_job_operator.api.main import create_app
from math_job_operator.config import Settings


@pytest.fixture
def settings() -> Settings:
    """Settings pointed at a disposable test database, distinct from the dev one."""
    return Settings(
        MONGO_URL="127.0.0.1",
        MONGO_PORT=27017,
        MONGO_ACCOUNT_DB="mathematics_test",
        MONGO_VARIABLES_COLLECTION="variables",
        MONGO_JOBS_COLLECTION="jobs",
        REDIS_URL="redis://localhost:6379/1",
        TIME_ZONE="UTC",
    )


@pytest.fixture
def test_db(settings: Settings) -> Iterator[Database[dict[str, object]]]:
    """A real MongoDB database, dropped before and after each test for isolation."""
    client: MongoClient[dict[str, object]] = MongoClient(
        host=settings.MONGO_URL, port=settings.MONGO_PORT
    )
    client.drop_database(settings.MONGO_ACCOUNT_DB)
    try:
        yield client[settings.MONGO_ACCOUNT_DB]
    finally:
        client.drop_database(settings.MONGO_ACCOUNT_DB)
        client.close()


@pytest.fixture
def redis_client(settings: Settings) -> Iterator[redis.Redis]:
    """A real Redis client on a disposable test DB index, flushed before/after each test."""
    client: redis.Redis = redis.Redis.from_url(settings.REDIS_URL)
    client.flushdb()
    try:
        yield client
    finally:
        client.flushdb()
        client.close()


@pytest.fixture
def client(
    settings: Settings,
    test_db: Database[dict[str, object]],
    redis_client: redis.Redis,
) -> Iterator[TestClient]:
    """A TestClient wired to a disposable test MongoDB + Redis (both fixtures clean up)."""
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client

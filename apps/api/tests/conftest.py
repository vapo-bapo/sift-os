import os
from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import Session

API_ROOT = Path(__file__).parents[1]
TEST_DATABASE_ERROR = (
    "TEST_DATABASE_URL must use a PostgreSQL database whose name ends in _test"
)


def validate_test_database_url(database_url: str) -> str:
    try:
        url = make_url(database_url)
    except ArgumentError:
        pytest.fail(TEST_DATABASE_ERROR)

    if url.get_backend_name() != "postgresql":
        pytest.fail(TEST_DATABASE_ERROR)
    if url.database is None or not url.database.endswith("_test"):
        pytest.fail(TEST_DATABASE_ERROR)
    return database_url


@pytest.fixture(scope="session")
def test_database_url() -> str:
    database_url = os.environ.get("TEST_DATABASE_URL")
    if database_url is None:
        pytest.fail("TEST_DATABASE_URL must point to the isolated PostgreSQL test database")
    return validate_test_database_url(database_url)


def alembic_config(database_url: str) -> Config:
    database_url = validate_test_database_url(database_url)
    config = Config(API_ROOT / "alembic.ini")
    config.set_main_option("script_location", str(API_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def run_alembic(database_url: str, action: str, revision: str) -> None:
    operation = getattr(command, action)
    operation(alembic_config(database_url), revision)


@pytest.fixture
def migrated_engine(test_database_url: str) -> Generator[Engine]:
    run_alembic(test_database_url, "downgrade", "base")
    run_alembic(test_database_url, "upgrade", "head")
    engine = create_engine(test_database_url)
    try:
        yield engine
    finally:
        engine.dispose()
        run_alembic(test_database_url, "downgrade", "base")


@pytest.fixture
def db_session(migrated_engine: Engine) -> Generator[Session]:
    with Session(migrated_engine) as session:
        yield session

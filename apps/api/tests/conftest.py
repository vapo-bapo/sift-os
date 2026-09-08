import os
from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

API_ROOT = Path(__file__).parents[1]


@pytest.fixture(scope="session")
def test_database_url() -> str:
    database_url = os.environ.get("TEST_DATABASE_URL")
    if database_url is None:
        pytest.fail("TEST_DATABASE_URL must point to the isolated PostgreSQL test database")
    if not database_url.rsplit("/", maxsplit=1)[-1].startswith("sift_os_test"):
        pytest.fail("TEST_DATABASE_URL must use a database whose name starts with sift_os_test")
    return database_url


def alembic_config(database_url: str) -> Config:
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

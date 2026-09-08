import pytest
from alembic import command
from sqlalchemy import create_engine, inspect

from tests.conftest import alembic_config, run_alembic

IDENTITY_TABLES = {"staff_members", "staff_member_roles", "user_sessions", "audit_logs"}


def table_names(database_url: str) -> set[str]:
    engine = create_engine(database_url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


@pytest.mark.integration
def test_upgrade_head_creates_identity_tables(test_database_url: str) -> None:
    run_alembic(test_database_url, "downgrade", "base")

    run_alembic(test_database_url, "upgrade", "head")

    assert table_names(test_database_url) >= IDENTITY_TABLES


@pytest.mark.integration
def test_identity_migration_can_downgrade_and_upgrade(test_database_url: str) -> None:
    run_alembic(test_database_url, "upgrade", "head")

    run_alembic(test_database_url, "downgrade", "base")
    assert IDENTITY_TABLES.isdisjoint(table_names(test_database_url))

    run_alembic(test_database_url, "upgrade", "head")
    assert table_names(test_database_url) >= IDENTITY_TABLES


@pytest.mark.integration
def test_identity_migration_matches_model_metadata(test_database_url: str) -> None:
    run_alembic(test_database_url, "downgrade", "base")
    run_alembic(test_database_url, "upgrade", "head")

    command.check(alembic_config(test_database_url))

import pytest

from tests.conftest import test_database_url


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql+psycopg://sift_os:sift_os@localhost:5433/sift_os_test",
        "postgresql://sift_os:sift_os@localhost/sift_os_integration_test?sslmode=require",
    ],
)
def test_test_database_url_accepts_postgresql_test_databases(
    monkeypatch: pytest.MonkeyPatch, database_url: str
) -> None:
    monkeypatch.setenv("TEST_DATABASE_URL", database_url)

    assert test_database_url.__wrapped__() == database_url


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql+psycopg://sift_os:sift_os@localhost:5433/sift_os_test_production",
        "postgresql+psycopg://sift_os:sift_os@localhost:5433/test_sift_os",
        "sqlite:///sift_os_test",
    ],
)
def test_test_database_url_rejects_unsafe_bindings(
    monkeypatch: pytest.MonkeyPatch, database_url: str
) -> None:
    monkeypatch.setenv("TEST_DATABASE_URL", database_url)

    with pytest.raises(pytest.fail.Exception, match=r"PostgreSQL database.*_test"):
        test_database_url.__wrapped__()

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_http_and_short_secrets() -> None:
    with pytest.raises(ValidationError):
        Settings(
            APP_ENV="production",
            SIFT_OS_PUBLIC_URL="http://os.example",
            SESSION_SECRET="x",
        )


def test_production_rejects_development_session_secret() -> None:
    with pytest.raises(
        ValidationError, match="SESSION_SECRET must not use the development default"
    ):
        Settings(
            APP_ENV="production",
            SIFT_OS_PUBLIC_URL="https://os.example",
            CSRF_SECRET="c" * 32,
        )


@pytest.mark.parametrize("csrf_secret", [None, "x" * 31])
def test_production_rejects_default_or_short_csrf_secret(csrf_secret: str | None) -> None:
    values = {
        "APP_ENV": "production",
        "SIFT_OS_PUBLIC_URL": "https://os.example",
        "SESSION_SECRET": "s" * 32,
    }
    if csrf_secret is not None:
        values["CSRF_SECRET"] = csrf_secret

    with pytest.raises(ValidationError, match="CSRF_SECRET"):
        Settings(**values)


def test_production_rejects_wildcard_cors_origin() -> None:
    with pytest.raises(ValidationError, match="CORS_ALLOWED_ORIGINS must not include a wildcard"):
        Settings(
            APP_ENV="production",
            SIFT_OS_PUBLIC_URL="https://os.example",
            SESSION_SECRET="s" * 32,
            CSRF_SECRET="c" * 32,
            CORS_ALLOWED_ORIGINS="*",
        )


def test_settings_parse_environment_style_cors_origins() -> None:
    settings = Settings(CORS_ALLOWED_ORIGINS="http://localhost:5173,https://os.example")

    assert [str(origin) for origin in settings.cors_allowed_origins] == [
        "http://localhost:5173/",
        "https://os.example/",
    ]

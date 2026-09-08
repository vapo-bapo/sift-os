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


def test_settings_parse_environment_style_cors_origins() -> None:
    settings = Settings(CORS_ALLOWED_ORIGINS="http://localhost:5173,https://os.example")

    assert [str(origin) for origin in settings.cors_allowed_origins] == [
        "http://localhost:5173/",
        "https://os.example/",
    ]

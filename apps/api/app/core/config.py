from functools import lru_cache
from typing import Any, Literal

from pydantic import AnyHttpUrl, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated runtime settings loaded from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        enable_decoding=False,
        extra="ignore",
    )

    app_env: Literal["development", "test", "staging", "production"] = "development"
    database_url: str = "postgresql+psycopg://sift_os:sift_os@localhost:5433/sift_os"
    sift_os_public_url: AnyHttpUrl = AnyHttpUrl("http://localhost:5173")
    sift_platform_public_url: AnyHttpUrl = AnyHttpUrl("http://localhost:8000")
    sift_platform_sso_audience: str = "sift-os"
    sift_platform_sso_issuer: AnyHttpUrl = AnyHttpUrl("http://localhost:8000")
    sift_platform_jwks_url: AnyHttpUrl = AnyHttpUrl("http://localhost:8000/.well-known/jwks.json")
    session_secret: SecretStr = SecretStr("local-development-session-secret-change-me")
    csrf_secret: SecretStr = SecretStr("local-development-csrf-secret-change-me")
    cors_allowed_origins: tuple[AnyHttpUrl, ...] = (AnyHttpUrl("http://localhost:5173"),)
    session_cookie_name: str = "sift_os_session"
    csrf_cookie_name: str = "sift_os_csrf"
    session_ttl_hours: int = 12
    cookie_domain: str | None = None
    log_level: str = "INFO"

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def parse_cors_allowed_origins(cls, value: Any) -> Any:
        if isinstance(value, str):
            return tuple(origin.strip() for origin in value.split(",") if origin.strip())
        return value

    @model_validator(mode="after")
    def secure_deployment(self) -> "Settings":
        if self.app_env in {"staging", "production"}:
            if self.sift_os_public_url.scheme != "https":
                raise ValueError("SIFT_OS_PUBLIC_URL must use HTTPS")
            if len(self.session_secret.get_secret_value()) < 32:
                raise ValueError("SESSION_SECRET must contain at least 32 characters")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""
    return Settings()

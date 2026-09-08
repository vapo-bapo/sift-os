from functools import lru_cache
from typing import Any, Literal

from pydantic import AnyHttpUrl, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SESSION_SECRET = "local-development-session-secret-change-me"
DEFAULT_CSRF_SECRET = "local-development-csrf-secret-change-me"
CorsAllowedOrigin = AnyHttpUrl | Literal["*"]


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
    session_secret: SecretStr = SecretStr(DEFAULT_SESSION_SECRET)
    csrf_secret: SecretStr = SecretStr(DEFAULT_CSRF_SECRET)
    cors_allowed_origins: tuple[CorsAllowedOrigin, ...] = (AnyHttpUrl("http://localhost:5173"),)
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
            session_secret = self.session_secret.get_secret_value()
            csrf_secret = self.csrf_secret.get_secret_value()
            if session_secret == DEFAULT_SESSION_SECRET:
                raise ValueError("SESSION_SECRET must not use the development default")
            if len(session_secret) < 32:
                raise ValueError("SESSION_SECRET must contain at least 32 characters")
            if csrf_secret == DEFAULT_CSRF_SECRET:
                raise ValueError("CSRF_SECRET must not use the development default")
            if len(csrf_secret) < 32:
                raise ValueError("CSRF_SECRET must contain at least 32 characters")
            if "*" in self.cors_allowed_origins:
                raise ValueError("CORS_ALLOWED_ORIGINS must not include a wildcard")
        return self

    @property
    def normalized_cors_allowed_origins(self) -> tuple[str, ...]:
        """Return exact browser origins without URL-only trailing slashes."""
        return tuple(str(origin).rstrip("/") for origin in self.cors_allowed_origins)


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""
    return Settings()

from collections.abc import Callable

from fastapi import FastAPI

from app import __version__
from app.api.health import router as health_router
from app.core.config import Settings, get_settings
from app.core.errors import ApiError, api_error_handler
from app.core.middleware import RequestIdMiddleware


def _always_ready() -> bool:
    return True


def create_app(
    settings: Settings | None = None,
    readiness_probe: Callable[[], bool] = _always_ready,
) -> FastAPI:
    """Compose the modular FastAPI application."""
    app = FastAPI(title="SIFT OS API", version=__version__)
    app.state.settings = settings or get_settings()
    app.state.readiness_probe = readiness_probe
    app.add_middleware(RequestIdMiddleware)
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(health_router)
    return app


app = create_app()

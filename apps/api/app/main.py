from collections.abc import Callable

from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.cors import CORSMiddleware

from app import __version__
from app.admin.routes import router as admin_router
from app.api.health import router as health_router
from app.auth.routes import router as auth_router
from app.auth.sso import platform_jwks
from app.company.routes import router as company_router
from app.core.config import Settings, get_settings
from app.core.errors import ApiError, api_error_handler, unexpected_error_handler
from app.core.middleware import RequestIdMiddleware
from app.crm.routes import router as crm_router
from app.dashboard.routes import router as dashboard_router
from app.db.session import engine
from app.finance.routes import router as finance_router
from app.integrations.routes import router as integrations_router
from app.partners.routes import router as partners_router
from app.products.routes import router as products_router
from app.search.routes import router as search_router
from app.staff.routes import router as staff_router


def _database_ready() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False


def create_app(
    settings: Settings | None = None,
    readiness_probe: Callable[[], bool] = _database_ready,
) -> FastAPI:
    """Compose the modular FastAPI application."""
    app = FastAPI(title="SIFT OS API", version=__version__)
    app_settings = settings or get_settings()
    app.state.settings = app_settings
    app.state.readiness_probe = readiness_probe
    app.state.platform_jwks = platform_jwks(app_settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(app_settings.normalized_cors_allowed_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIdMiddleware)
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(staff_router)
    app.include_router(dashboard_router)
    app.include_router(crm_router)
    app.include_router(partners_router)
    app.include_router(products_router)
    app.include_router(company_router)
    app.include_router(finance_router)
    app.include_router(integrations_router)
    app.include_router(search_router)
    app.include_router(admin_router)
    return app


app = create_app()

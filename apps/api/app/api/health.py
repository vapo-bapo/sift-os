from fastapi import APIRouter, Request

from app.core.errors import ApiError

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Return process liveness without checking external dependencies."""
    return {"status": "ok"}


@router.get("/ready")
def ready(request: Request) -> dict[str, str]:
    """Return readiness after required dependencies have been checked."""
    if not request.app.state.readiness_probe():
        raise ApiError(
            status_code=503,
            code="service_not_ready",
            message="Required dependencies are unavailable.",
        )
    return {"status": "ready"}

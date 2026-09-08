from typing import Any
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    """A client-safe API exception with a stable response shape."""

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: Any = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


async def api_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Serialize expected API errors without exposing implementation details."""
    if not isinstance(exc, ApiError):
        raise TypeError("api_error_handler received a non-ApiError exception")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
            "request_id": request.state.request_id,
        },
    )


async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a safe 500 envelope while preserving the request correlation ID."""
    request_id = getattr(request.state, "request_id", None)
    if not isinstance(request_id, str):
        request_id = str(uuid4())
    headers = {"X-Request-ID": request_id}
    origin = request.headers.get("origin")
    allowed_origins = getattr(
        getattr(request.app.state, "settings", None), "normalized_cors_allowed_origins", ()
    )
    if isinstance(origin, str) and origin in allowed_origins:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
        headers["Vary"] = "Origin"

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_server_error",
                "message": "An unexpected error occurred.",
                "details": None,
            },
            "request_id": request_id,
        },
        headers=headers,
    )

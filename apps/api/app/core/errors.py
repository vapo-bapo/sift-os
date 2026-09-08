from typing import Any

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

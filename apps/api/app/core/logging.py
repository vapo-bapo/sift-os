from typing import Any

import structlog


def log_request(
    *,
    method: str,
    route: str,
    status: int,
    duration_ms: float,
    request_id: str,
    environment: str,
    platform_user_id: str | None,
) -> None:
    """Emit the minimal structured request audit record without request contents."""
    event: dict[str, Any] = {
        "method": method,
        "route": route,
        "status": status,
        "duration_ms": duration_ms,
        "request_id": request_id,
        "environment": environment,
    }
    if platform_user_id is not None:
        event["platform_user_id"] = platform_user_id

    structlog.get_logger("sift_os.request").info("request.completed", **event)

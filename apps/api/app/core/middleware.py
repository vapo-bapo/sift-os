from time import perf_counter
from uuid import UUID, uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import log_request


class RequestIdMiddleware:
    """Attach a trusted request identifier and log only safe access metadata."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _request_id(scope)
        scope.setdefault("state", {})["request_id"] = request_id
        started_at = perf_counter()
        status_code = 500

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("ascii")))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            route = scope.get("route")
            route_template = str(getattr(route, "path", "unmatched"))
            settings = getattr(scope["app"].state, "settings", None)
            environment = getattr(settings, "app_env", "unknown")
            platform_user_id = scope.get("state", {}).get("platform_user_id")
            log_request(
                method=scope["method"],
                route=route_template,
                status=status_code,
                duration_ms=(perf_counter() - started_at) * 1000,
                request_id=request_id,
                environment=environment,
                platform_user_id=str(platform_user_id) if platform_user_id is not None else None,
            )


def _request_id(scope: Scope) -> str:
    """Return a valid caller-provided UUID or a newly generated UUID."""
    inbound_request_id = next(
        (
            value.decode("ascii")
            for name, value in scope["headers"]
            if name.lower() == b"x-request-id"
        ),
        None,
    )
    if isinstance(inbound_request_id, str):
        try:
            UUID(inbound_request_id)
        except ValueError:
            pass
        else:
            return inbound_request_id
    return str(uuid4())

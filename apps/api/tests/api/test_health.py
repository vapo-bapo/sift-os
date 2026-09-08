import httpx
import pytest

from app.core.config import Settings
from app.core.errors import ApiError
from app.main import create_app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_health_and_ready_are_distinct() -> None:
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        health_response = await client.get("/health")
        ready_response = await client.get("/ready")

    assert health_response.json() == {"status": "ok"}
    assert ready_response.json() == {"status": "ready"}


@pytest.mark.anyio
async def test_ready_returns_service_unavailable_when_dependency_probe_fails() -> None:
    transport = httpx.ASGITransport(app=create_app(readiness_probe=lambda: False))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ready")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_not_ready"


@pytest.mark.anyio
async def test_request_id_is_echoed_when_valid_and_replaced_when_invalid() -> None:
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/health", headers={"X-Request-ID": "a2e310f9-eef3-42bc-b6c7-665e8b1a7a1d"}
        )
        invalid_response = await client.get("/health", headers={"X-Request-ID": "not-a-uuid"})

    assert response.headers["X-Request-ID"] == "a2e310f9-eef3-42bc-b6c7-665e8b1a7a1d"
    assert invalid_response.headers["X-Request-ID"] != "not-a-uuid"


@pytest.mark.anyio
async def test_api_error_has_stable_envelope_with_request_id() -> None:
    app = create_app()

    @app.get("/error")
    def error() -> None:
        raise ApiError(
            status_code=422,
            code="invalid_input",
            message="The submitted value is invalid.",
            details={"field": "name"},
        )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/error", headers={"X-Request-ID": "a2e310f9-eef3-42bc-b6c7-665e8b1a7a1d"}
        )

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "invalid_input",
            "message": "The submitted value is invalid.",
            "details": {"field": "name"},
        },
        "request_id": "a2e310f9-eef3-42bc-b6c7-665e8b1a7a1d",
    }


@pytest.mark.anyio
async def test_unhandled_error_returns_request_id() -> None:
    app = create_app()

    @app.get("/unexpected-error")
    def unexpected_error() -> None:
        raise RuntimeError("unexpected")

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/unexpected-error", headers={"X-Request-ID": "a2e310f9-eef3-42bc-b6c7-665e8b1a7a1d"}
        )

    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == "a2e310f9-eef3-42bc-b6c7-665e8b1a7a1d"


@pytest.mark.anyio
async def test_unhandled_error_returns_cors_header_for_allowed_origin() -> None:
    app = create_app(Settings(CORS_ALLOWED_ORIGINS="https://os.example"))

    @app.get("/unexpected-cors-error")
    def unexpected_cors_error() -> None:
        raise RuntimeError("unexpected")

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/unexpected-cors-error",
            headers={"Origin": "https://os.example"},
        )

    assert response.status_code == 500
    assert response.headers["Access-Control-Allow-Origin"] == "https://os.example"


@pytest.mark.anyio
async def test_cors_uses_configured_normalized_origin() -> None:
    app = create_app(Settings(CORS_ALLOWED_ORIGINS="https://os.example"))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/health",
            headers={
                "Origin": "https://os.example",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "https://os.example"

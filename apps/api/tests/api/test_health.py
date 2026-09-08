from fastapi.testclient import TestClient

from app.core.errors import ApiError
from app.main import create_app


def test_health_and_ready_are_distinct() -> None:
    client = TestClient(create_app())

    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/ready").json() == {"status": "ready"}


def test_ready_returns_service_unavailable_when_dependency_probe_fails() -> None:
    client = TestClient(create_app(readiness_probe=lambda: False))

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_not_ready"


def test_request_id_is_echoed_when_valid_and_replaced_when_invalid() -> None:
    client = TestClient(create_app())

    response = client.get(
        "/health", headers={"X-Request-ID": "a2e310f9-eef3-42bc-b6c7-665e8b1a7a1d"}
    )
    invalid_response = client.get("/health", headers={"X-Request-ID": "not-a-uuid"})

    assert response.headers["X-Request-ID"] == "a2e310f9-eef3-42bc-b6c7-665e8b1a7a1d"
    assert invalid_response.headers["X-Request-ID"] != "not-a-uuid"


def test_api_error_has_stable_envelope_with_request_id() -> None:
    app = create_app()

    @app.get("/error")
    def error() -> None:
        raise ApiError(
            status_code=422,
            code="invalid_input",
            message="The submitted value is invalid.",
            details={"field": "name"},
        )

    response = TestClient(app).get(
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

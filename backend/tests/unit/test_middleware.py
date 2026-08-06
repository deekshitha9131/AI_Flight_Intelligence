"""Tests for app/presentation/middleware/request_id.py and CORS configuration
in app/main.py's create_app().
"""

from fastapi.testclient import TestClient

from app.core.constants import REQUEST_ID_HEADER


def test_custom_request_id_is_echoed_back(unit_client: TestClient) -> None:
    response = unit_client.get("/health", headers={REQUEST_ID_HEADER: "caller-supplied-id"})

    assert response.headers[REQUEST_ID_HEADER] == "caller-supplied-id"


def test_request_id_is_generated_when_not_supplied(unit_client: TestClient) -> None:
    response = unit_client.get("/health")

    generated_id = response.headers.get(REQUEST_ID_HEADER)
    assert generated_id is not None
    assert len(generated_id) > 0


def test_two_requests_without_custom_ids_get_different_ids(unit_client: TestClient) -> None:
    first = unit_client.get("/health").headers[REQUEST_ID_HEADER]
    second = unit_client.get("/health").headers[REQUEST_ID_HEADER]

    assert first != second


def test_cors_header_present_for_allowed_origin(unit_client: TestClient) -> None:
    # Matches CORS_ORIGINS in backend/.env.example — if this test starts
    # failing after an env change, update both together.
    response = unit_client.get("/health", headers={"Origin": "http://localhost:5173"})

    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_header_absent_for_disallowed_origin(unit_client: TestClient) -> None:
    response = unit_client.get(
        "/health", headers={"Origin": "https://not-an-allowed-origin.example"}
    )

    assert "access-control-allow-origin" not in response.headers

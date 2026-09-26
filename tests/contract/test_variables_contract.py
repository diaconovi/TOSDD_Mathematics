"""Contract test: `PUT /api/v1/variables` and `GET /api/v1/jobs/variables` shapes."""

from fastapi.testclient import TestClient


def test_put_variables_response_shape(client: TestClient) -> None:
    response = client.put(
        "/api/v1/variables", json=[{"name": "x", "value": 1}]
    )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    for entry in body:
        assert set(entry.keys()) == {"name", "value"}


def test_get_jobs_variables_response_shape(client: TestClient) -> None:
    response = client.get("/api/v1/jobs/variables")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    for entry in body:
        assert set(entry.keys()) == {"name", "value"}

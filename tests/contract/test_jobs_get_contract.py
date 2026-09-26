"""Contract test: `GET /api/v1/jobs` and `GET /api/v1/jobs/dependencies` shapes."""

from fastapi.testclient import TestClient


def test_get_jobs_matches_job_summary_shape(client: TestClient) -> None:
    response = client.get("/api/v1/jobs")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    for entry in body:
        assert set(entry.keys()) == {"name", "description", "job_type", "return_type"}
        assert entry["job_type"] in {"mutable", "immutable"}


def test_get_dependencies_is_a_list_of_strings(client: TestClient) -> None:
    response = client.get("/api/v1/jobs/dependencies")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert all(isinstance(item, str) for item in body)

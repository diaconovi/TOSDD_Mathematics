"""Contract test: `PUT /api/v1/jobs` response shapes (200 / 409 / 422)."""

import io

from fastapi.testclient import TestClient

VALID_SOURCE = b"def run(arg: str) -> list:\n    return []\n"
INVALID_SOURCE = b"not valid python (((\n"


def test_put_jobs_success_shape(client: TestClient) -> None:
    response = client.put(
        "/api/v1/jobs",
        files={"file": ("contract_job.py", io.BytesIO(VALID_SOURCE), "text/x-python")},
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"name", "description", "job_type", "return_type"}
    assert body["job_type"] == "mutable"


def test_put_jobs_immutable_conflict_is_problem_detail(client: TestClient) -> None:
    response = client.put(
        "/api/v1/jobs",
        files={
            "file": ("awxsg_example.py", io.BytesIO(VALID_SOURCE), "text/x-python")
        },
    )

    assert response.status_code == 409
    body = response.json()
    assert body["status"] == 409
    assert "title" in body and "detail" in body


def test_put_jobs_invalid_script_is_problem_detail(client: TestClient) -> None:
    response = client.put(
        "/api/v1/jobs",
        files={"file": ("broken_job.py", io.BytesIO(INVALID_SOURCE), "text/x-python")},
    )

    assert response.status_code == 422
    body = response.json()
    assert "detail" in body

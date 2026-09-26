"""Contract test: `POST /api/v1/jobs` request/response shape (contracts/jobs.md)."""

from fastapi.testclient import TestClient
from pymongo.database import Database

JOB_SOURCE = "def run(arg: str) -> list:\n    return [1, 2, 3]\n"


def test_post_jobs_response_matches_contract_shape(
    client: TestClient, test_db: Database[dict[str, object]]
) -> None:
    test_db.get_collection("jobs").update_one(
        {"_id": "job_a"}, {"$set": {"source": JOB_SOURCE}}, upsert=True
    )

    response = client.post(
        "/api/v1/jobs", json=[{"name": "job_a", "args": [{"epic": "AWXSG"}]}]
    )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    (result,) = body
    assert set(result.keys()) == {"name", "finished_at", "duration", "status", "output"}
    assert isinstance(result["name"], str)
    assert isinstance(result["finished_at"], str)  # ISO 8601 datetime
    assert isinstance(result["duration"], (int, float))
    assert result["status"] in {"completed", "error"}

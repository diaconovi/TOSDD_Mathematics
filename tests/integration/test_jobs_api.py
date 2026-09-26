"""Integration tests for `/api/v1/jobs*`: run (US1), catalog/dependencies (US2), upload (US3)."""

import io

from fastapi.testclient import TestClient
from pymongo.database import Database

JOB_RETURNS_VALUE = "def run(arg: str) -> list:\n    return [{'value': 1}]\n"
JOB_READS_UPSTREAM = "def run(arg: str) -> list:\n    return [upstream]\n"
JOB_RAISES = "def run(arg: str) -> list:\n    raise ValueError('boom')\n"
JOB_NO_RETURN = "def run(arg: str) -> list:\n    return None\n"
JOB_NON_SERIALIZABLE_OUTPUT = "def run(arg: str) -> list:\n    return [{1, 2, 3}]\n"


def _insert_job(db: Database[dict[str, object]], name: str, source: str) -> None:
    db.get_collection("jobs").update_one(
        {"_id": name}, {"$set": {"source": source}}, upsert=True
    )


def test_run_single_job(client: TestClient, test_db: Database[dict[str, object]]) -> None:
    _insert_job(test_db, "job_a", JOB_RETURNS_VALUE)

    response = client.post("/api/v1/jobs", json=[{"name": "job_a", "args": []}])

    assert response.status_code == 200
    (result,) = response.json()
    assert result["name"] == "job_a"
    assert result["status"] == "completed"
    assert result["output"] == [{"value": 1}]
    assert result["duration"] >= 0
    assert result["finished_at"]


def test_run_dependent_job(client: TestClient, test_db: Database[dict[str, object]]) -> None:
    _insert_job(test_db, "job_a", JOB_RETURNS_VALUE)
    _insert_job(test_db, "job_b", JOB_READS_UPSTREAM)

    response = client.post(
        "/api/v1/jobs",
        json=[
            {"name": "job_a", "args": []},
            {"name": "job_b", "args": [], "depends_on": "job_a"},
        ],
    )

    assert response.status_code == 200
    results = {r["name"]: r for r in response.json()}
    assert results["job_a"]["status"] == "completed"
    assert results["job_b"]["status"] == "completed"
    assert results["job_b"]["output"] == [[{"value": 1}]]


def test_job_raising_is_reported_as_error(
    client: TestClient, test_db: Database[dict[str, object]]
) -> None:
    _insert_job(test_db, "job_error", JOB_RAISES)

    response = client.post("/api/v1/jobs", json=[{"name": "job_error", "args": []}])

    (result,) = response.json()
    assert result["status"] == "error"
    assert "boom" in result["output"]


def test_job_with_no_return_value(
    client: TestClient, test_db: Database[dict[str, object]]
) -> None:
    _insert_job(test_db, "job_none", JOB_NO_RETURN)

    response = client.post("/api/v1/jobs", json=[{"name": "job_none", "args": []}])

    (result,) = response.json()
    assert result["status"] == "completed"
    assert result["output"] is None


def test_unknown_job_name(client: TestClient) -> None:
    response = client.post("/api/v1/jobs", json=[{"name": "does_not_exist", "args": []}])

    (result,) = response.json()
    assert result["status"] == "error"
    assert "not found" in result["output"]


def test_upstream_failure_propagation(
    client: TestClient, test_db: Database[dict[str, object]]
) -> None:
    _insert_job(test_db, "job_error", JOB_RAISES)
    _insert_job(test_db, "job_b", JOB_READS_UPSTREAM)

    response = client.post(
        "/api/v1/jobs",
        json=[
            {"name": "job_error", "args": []},
            {"name": "job_b", "args": [], "depends_on": "job_error"},
        ],
    )

    results = {r["name"]: r for r in response.json()}
    assert results["job_error"]["status"] == "error"
    assert results["job_b"]["status"] == "error"
    assert "upstream" in results["job_b"]["output"]
    assert "failed" in results["job_b"]["output"]


def test_dangling_dependency(client: TestClient, test_db: Database[dict[str, object]]) -> None:
    _insert_job(test_db, "job_b", JOB_READS_UPSTREAM)

    response = client.post(
        "/api/v1/jobs",
        json=[{"name": "job_b", "args": [], "depends_on": "job_missing"}],
    )

    (result,) = response.json()
    assert result["status"] == "error"
    assert "job_missing" in result["output"]


def test_non_serializable_output(
    client: TestClient, test_db: Database[dict[str, object]]
) -> None:
    _insert_job(test_db, "job_bad_output", JOB_NON_SERIALIZABLE_OUTPUT)

    response = client.post("/api/v1/jobs", json=[{"name": "job_bad_output", "args": []}])

    (result,) = response.json()
    assert result["status"] == "error"


def test_list_jobs(client: TestClient, test_db: Database[dict[str, object]]) -> None:
    _insert_job(test_db, "job_a", JOB_RETURNS_VALUE)

    response = client.get("/api/v1/jobs")

    assert response.status_code == 200
    names_and_types = {j["name"]: j["job_type"] for j in response.json()}
    assert names_and_types.get("job_a") == "mutable"
    assert "awxsg_example" in names_and_types
    assert names_and_types["awxsg_example"] == "immutable"


def test_list_dependencies(client: TestClient) -> None:
    response = client.get("/api/v1/jobs/dependencies")

    assert response.status_code == 200
    packages = response.json()
    assert "requests" in packages
    assert "pymongo" in packages
    assert "to_collector_client" in packages
    assert "to_session_manager" in packages
    assert "fastapi" not in packages
    assert "uvicorn" not in packages
    assert "pydantic" not in packages


# --- User Story 3: Upload/Replace a Mutable Job ---

VALID_JOB_SOURCE = b"def run(arg: str) -> list:\n    return [1, 2, 3]\n"
INVALID_ENTRY_POINT_SOURCE = b"def run(value: int) -> list:\n    return []\n"


def test_upload_new_job(client: TestClient) -> None:
    response = client.put(
        "/api/v1/jobs",
        files={"file": ("my_new_job.py", io.BytesIO(VALID_JOB_SOURCE), "text/x-python")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "my_new_job"
    assert body["job_type"] == "mutable"

    catalog = client.get("/api/v1/jobs").json()
    assert any(j["name"] == "my_new_job" and j["job_type"] == "mutable" for j in catalog)

    run_response = client.post("/api/v1/jobs", json=[{"name": "my_new_job", "args": []}])
    (result,) = run_response.json()
    assert result["status"] == "completed"
    assert result["output"] == [1, 2, 3]


def test_upload_rejects_immutable_overwrite(
    client: TestClient, test_db: Database[dict[str, object]]
) -> None:
    response = client.put(
        "/api/v1/jobs",
        files={
            "file": ("awxsg_example.py", io.BytesIO(VALID_JOB_SOURCE), "text/x-python")
        },
    )

    assert response.status_code == 409
    assert test_db.get_collection("jobs").find_one({"_id": "awxsg_example"}) is None


def test_upload_rejects_invalid_entry_point(client: TestClient) -> None:
    response = client.put(
        "/api/v1/jobs",
        files={
            "file": (
                "bad_job.py",
                io.BytesIO(INVALID_ENTRY_POINT_SOURCE),
                "text/x-python",
            )
        },
    )

    assert response.status_code == 422


def test_upload_replaces_existing_mutable_job(client: TestClient) -> None:
    client.put(
        "/api/v1/jobs",
        files={"file": ("job_x.py", io.BytesIO(VALID_JOB_SOURCE), "text/x-python")},
    )
    replacement = b"def run(arg: str) -> list:\n    return ['replaced']\n"

    client.put(
        "/api/v1/jobs",
        files={"file": ("job_x.py", io.BytesIO(replacement), "text/x-python")},
    )

    run_response = client.post("/api/v1/jobs", json=[{"name": "job_x", "args": []}])
    (result,) = run_response.json()
    assert result["output"] == ["replaced"]


def test_upload_name_derivation_is_case_insensitive(client: TestClient) -> None:
    response = client.put(
        "/api/v1/jobs",
        files={"file": ("AWXSG.PY", io.BytesIO(VALID_JOB_SOURCE), "text/x-python")},
    )

    # AWXSG.PY normalizes to "awxsg", which collides with the immutable "awxsg_example"
    # only if names matched; here it's a distinct name, so this should succeed as mutable.
    assert response.status_code == 200
    assert response.json()["name"] == "awxsg"

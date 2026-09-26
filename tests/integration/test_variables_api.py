"""Integration tests for `PUT /api/v1/variables` and `GET /api/v1/jobs/variables` (US4)."""

from fastapi.testclient import TestClient


def test_set_and_list_variable(client: TestClient) -> None:
    put_response = client.put(
        "/api/v1/variables", json=[{"name": "base_url", "value": "https://example.test"}]
    )
    assert put_response.status_code == 200
    assert put_response.json() == [{"name": "BASE_URL", "value": "https://example.test"}]

    list_response = client.get("/api/v1/jobs/variables")
    stored = {v["name"]: v["value"] for v in list_response.json()}
    assert stored["BASE_URL"] == "https://example.test"


def test_overwrite_variable(client: TestClient) -> None:
    client.put("/api/v1/variables", json=[{"name": "FLAG", "value": False}])

    client.put("/api/v1/variables", json=[{"name": "flag", "value": True}])

    stored = {v["name"]: v["value"] for v in client.get("/api/v1/jobs/variables").json()}
    assert stored["FLAG"] is True


def test_variable_arbitrary_json_types(client: TestClient) -> None:
    payload = [
        {"name": "A_STRING", "value": "hello"},
        {"name": "A_NUMBER", "value": 42},
        {"name": "A_BOOL", "value": True},
        {"name": "AN_OBJECT", "value": {"nested": [1, 2, 3]}},
        {"name": "AN_ARRAY", "value": [1, "two", False]},
    ]

    client.put("/api/v1/variables", json=payload)

    stored = {v["name"]: v["value"] for v in client.get("/api/v1/jobs/variables").json()}
    assert stored["A_STRING"] == "hello"
    assert stored["A_NUMBER"] == 42
    assert stored["A_BOOL"] is True
    assert stored["AN_OBJECT"] == {"nested": [1, 2, 3]}
    assert stored["AN_ARRAY"] == [1, "two", False]


def test_duplicate_name_last_write_wins(client: TestClient) -> None:
    response = client.put(
        "/api/v1/variables",
        json=[{"name": "name", "value": "first"}, {"name": "NAME", "value": "second"}],
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0] == {"name": "NAME", "value": "second"}

    stored = {v["name"]: v["value"] for v in client.get("/api/v1/jobs/variables").json()}
    assert stored["NAME"] == "second"


def test_variables_are_available_inside_a_job_run(
    client: TestClient, test_db: object
) -> None:
    client.put("/api/v1/variables", json=[{"name": "GREETING", "value": "hi"}])
    test_db.get_collection("jobs").update_one(  # type: ignore[attr-defined]
        {"_id": "reads_var"},
        {"$set": {"source": "def run(arg: str) -> list:\n    return [GREETING]\n"}},
        upsert=True,
    )

    response = client.post("/api/v1/jobs", json=[{"name": "reads_var", "args": []}])

    (result,) = response.json()
    assert result["status"] == "completed"
    assert result["output"] == ["hi"]

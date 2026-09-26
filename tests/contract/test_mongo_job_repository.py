"""Contract tests for MongoJobRepository against a real MongoDB instance."""

from pymongo.database import Database

from math_job_operator.infrastructure.mongo.job_repository import MongoJobRepository


def test_get_by_name_returns_none_when_absent(test_db: Database[dict[str, object]]) -> None:
    repo = MongoJobRepository(test_db, "jobs")
    assert repo.get_by_name("missing") is None


def test_upsert_then_get_by_name_round_trips(test_db: Database[dict[str, object]]) -> None:
    repo = MongoJobRepository(test_db, "jobs")
    source = "def run(arg: str) -> list:\n    return []\n"

    repo.upsert("my_job", source)
    record = repo.get_by_name("my_job")

    assert record is not None
    assert record.name == "my_job"
    assert record.source == source


def test_upsert_replaces_existing_source(test_db: Database[dict[str, object]]) -> None:
    repo = MongoJobRepository(test_db, "jobs")
    repo.upsert("my_job", "def run(arg: str) -> list:\n    return [1]\n")
    repo.upsert("my_job", "def run(arg: str) -> list:\n    return [2]\n")

    record = repo.get_by_name("my_job")

    assert record is not None
    assert record.source == "def run(arg: str) -> list:\n    return [2]\n"


def test_list_all_returns_every_stored_job(test_db: Database[dict[str, object]]) -> None:
    repo = MongoJobRepository(test_db, "jobs")
    repo.upsert("job_a", "def run(arg: str) -> list:\n    return []\n")
    repo.upsert("job_b", "def run(arg: str) -> list:\n    return []\n")

    names = sorted(record.name for record in repo.list_all())

    assert names == ["job_a", "job_b"]

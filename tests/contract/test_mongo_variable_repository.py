"""Contract tests for MongoVariableRepository against a real MongoDB instance."""

from pymongo.database import Database

from math_job_operator.infrastructure.mongo.variable_repository import (
    MongoVariableRepository,
)


def test_get_all_is_empty_initially(test_db: Database[dict[str, object]]) -> None:
    repo = MongoVariableRepository(test_db, "variables")
    assert repo.get_all() == []


def test_upsert_many_creates_and_uppercases_names(
    test_db: Database[dict[str, object]],
) -> None:
    repo = MongoVariableRepository(test_db, "variables")

    result = repo.upsert_many([("base_url", "https://example.test"), ("max_days", 30)])

    assert {v.name: v.value for v in result} == {
        "BASE_URL": "https://example.test",
        "MAX_DAYS": 30,
    }
    assert {v.name: v.value for v in repo.get_all()} == {
        "BASE_URL": "https://example.test",
        "MAX_DAYS": 30,
    }


def test_upsert_many_overwrites_existing_value(
    test_db: Database[dict[str, object]],
) -> None:
    repo = MongoVariableRepository(test_db, "variables")
    repo.upsert_many([("FLAG", False)])

    repo.upsert_many([("flag", True)])

    stored = {v.name: v.value for v in repo.get_all()}
    assert stored == {"FLAG": True}


def test_upsert_many_last_write_wins_for_duplicate_names_in_one_call(
    test_db: Database[dict[str, object]],
) -> None:
    repo = MongoVariableRepository(test_db, "variables")

    result = repo.upsert_many([("name", "first"), ("NAME", "second")])

    assert len(result) == 1
    assert result[0].name == "NAME"
    assert result[0].value == "second"
    assert repo.get_all() == [result[0]]


def test_upsert_many_accepts_arbitrary_json_types(
    test_db: Database[dict[str, object]],
) -> None:
    repo = MongoVariableRepository(test_db, "variables")

    repo.upsert_many(
        [
            ("A_STRING", "hello"),
            ("A_NUMBER", 42),
            ("A_BOOL", True),
            ("AN_OBJECT", {"nested": [1, 2, 3]}),
            ("AN_ARRAY", [1, "two", False]),
        ]
    )

    stored = {v.name: v.value for v in repo.get_all()}
    assert stored["A_STRING"] == "hello"
    assert stored["A_NUMBER"] == 42
    assert stored["A_BOOL"] is True
    assert stored["AN_OBJECT"] == {"nested": [1, 2, 3]}
    assert stored["AN_ARRAY"] == [1, "two", False]

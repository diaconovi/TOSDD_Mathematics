"""MongoDB-backed `VariableRepository` implementation."""

from typing import cast

from pymongo import UpdateOne
from pymongo.database import Database

from math_job_operator.domain.entities import JSONValue, SharedVariable
from math_job_operator.domain.repositories import VariableRepository


class MongoVariableRepository(VariableRepository):
    """Stores `{name: <UPPER_STR>, value: <JSONValue>}` documents in Mongo.

    Example:
        >>> repo = MongoVariableRepository(db, "variables")  # doctest: +SKIP
        >>> repo.upsert_many([("base_url", "https://example.test")])  # doctest: +SKIP
    """

    def __init__(self, database: Database[dict[str, object]], collection_name: str) -> None:
        self._collection = database.get_collection(collection_name)

    def get_all(self) -> list[SharedVariable]:
        return [
            SharedVariable(
                name=str(document["_id"]), value=cast(JSONValue, document["value"])
            )
            for document in self._collection.find()
        ]

    def upsert_many(self, variables: list[tuple[str, JSONValue]]) -> list[SharedVariable]:
        if not variables:
            return []

        last_value_by_name: dict[str, JSONValue] = {}
        order: list[str] = []
        for name, value in variables:
            upper_name = name.upper()
            if upper_name not in last_value_by_name:
                order.append(upper_name)
            last_value_by_name[upper_name] = value

        operations = [
            UpdateOne({"_id": name}, {"$set": {"value": value}}, upsert=True)
            for name, value in last_value_by_name.items()
        ]
        self._collection.bulk_write(operations)

        return [SharedVariable(name=name, value=last_value_by_name[name]) for name in order]

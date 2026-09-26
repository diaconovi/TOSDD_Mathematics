"""MongoDB-backed `JobRepository` implementation (mutable job source storage)."""

from pymongo.database import Database

from math_job_operator.domain.repositories import JobRepository, MutableJobRecord


class MongoJobRepository(JobRepository):
    """Stores mutable job source text, keyed by the normalized (lowercase, no-extension) name.

    Example:
        >>> from math_job_operator.infrastructure.mongo.client import build_database
        >>> repo = MongoJobRepository(db, "jobs")  # doctest: +SKIP
        >>> repo.upsert("my_job", "def run(arg: str) -> list:\\n    return []")  # doctest: +SKIP
    """

    def __init__(self, database: Database[dict[str, object]], collection_name: str) -> None:
        self._collection = database.get_collection(collection_name)

    def get_by_name(self, name: str) -> MutableJobRecord | None:
        document = self._collection.find_one({"_id": name})
        if document is None:
            return None
        return MutableJobRecord(name=name, source=str(document["source"]))

    def list_all(self) -> list[MutableJobRecord]:
        return [
            MutableJobRecord(name=str(document["_id"]), source=str(document["source"]))
            for document in self._collection.find()
        ]

    def upsert(self, name: str, source: str) -> None:
        self._collection.update_one(
            {"_id": name}, {"$set": {"source": source}}, upsert=True
        )

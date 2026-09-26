"""pymongo connection/database factory."""

from pymongo import MongoClient
from pymongo.database import Database

from math_job_operator.config import Settings


def build_database(settings: Settings) -> Database[dict[str, object]]:
    """Open a MongoDB connection and return the configured account database.

    Example:
        >>> from math_job_operator.config import Settings
        >>> s = Settings(_env_file=None, MONGO_URL="127.0.0.1", MONGO_PORT=27017,
        ...               MONGO_ACCOUNT_DB="mathematics", TIME_ZONE="UTC")
        >>> db = build_database(s)
        >>> db.name
        'mathematics'
    """
    client: MongoClient[dict[str, object]] = MongoClient(
        host=settings.MONGO_URL, port=settings.MONGO_PORT
    )
    return client[settings.MONGO_ACCOUNT_DB]

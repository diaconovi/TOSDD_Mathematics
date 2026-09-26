"""One-time default-variable seeding, run at application startup."""

from math_job_operator.domain.entities import JSONValue
from math_job_operator.domain.repositories import VariableRepository

DEFAULT_VARIABLES: list[tuple[str, JSONValue]] = [
    ("BASE_ENDPOINT_URL", "https://api-capital.backend-capital.com"),
    ("DEMO_ENDPOINT_URL", "https://demo-api-capital.backend-capital.com"),
    ("SESSION_MANAGER_URL", "http://localhost:8000"),
    ("SESSION_MANAGER_INSECURE", False),
    ("REDIS_URL", "redis://localhost:6379/0"),
    # Not part of the original seed list, but required for the example job (and any other
    # job) to reach the Collector service without hardcoding its address in job source —
    # mirrors the SESSION_MANAGER_URL/SESSION_MANAGER_INSECURE pattern above.
    ("COLLECTOR_URL", "http://localhost:8001"),
    ("COLLECTOR_INSECURE", False),
]


def seed_default_variables(repository: VariableRepository) -> None:
    """Insert each default variable only if its (uppercase) name doesn't already exist.

    Example:
        >>> seed_default_variables(repository)  # doctest: +SKIP
    """
    existing_names = {variable.name for variable in repository.get_all()}
    missing = [
        (name, value) for name, value in DEFAULT_VARIABLES if name not in existing_names
    ]
    if missing:
        repository.upsert_many(missing)

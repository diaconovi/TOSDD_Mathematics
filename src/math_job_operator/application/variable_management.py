"""List/upsert shared-variables use case (FR-011 through FR-014, FR-013a)."""

from math_job_operator.domain.entities import JSONValue, SharedVariable
from math_job_operator.domain.repositories import VariableRepository


def list_variables(repository: VariableRepository) -> list[SharedVariable]:
    """Return every stored shared variable (FR-011)."""
    return repository.get_all()


def set_variables(
    repository: VariableRepository, variables: list[tuple[str, JSONValue]]
) -> list[SharedVariable]:
    """Create or overwrite each `(name, value)` pair, uppercasing every name (FR-012, FR-013).

    Accepts any JSON type as a value, unchanged (FR-013a). When the same normalized name
    appears more than once, the last occurrence in list order wins.

    Example:
        >>> set_variables(repository, [("base_url", "https://example.test")])  # doctest: +SKIP
    """
    return repository.upsert_many(variables)

"""Abstract repository interfaces.

Application-layer use cases depend only on these interfaces, never on a concrete
infrastructure implementation (Constitution Principle VII — Dependency Inversion).
"""

from abc import ABC, abstractmethod

from math_job_operator.domain.entities import JSONValue, SharedVariable


class MutableJobRecord:
    """A mutable job's persisted source, as read from/written to storage."""

    __slots__ = ("name", "source")

    def __init__(self, name: str, source: str) -> None:
        self.name = name
        self.source = source


class JobRepository(ABC):
    """Persists and retrieves mutable job source code, keyed by normalized name."""

    @abstractmethod
    def get_by_name(self, name: str) -> MutableJobRecord | None:
        """Return the mutable job record for `name`, or `None` if it doesn't exist.

        Example:
            >>> class _Fake(JobRepository):
            ...     def get_by_name(self, name): return None
            ...     def list_all(self): return []
            ...     def upsert(self, name, source): pass
            >>> _Fake().get_by_name("missing")
        """
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[MutableJobRecord]:
        """Return every stored mutable job record."""
        raise NotImplementedError

    @abstractmethod
    def upsert(self, name: str, source: str) -> None:
        """Create the job record for `name` if absent, else replace its source."""
        raise NotImplementedError


class VariableRepository(ABC):
    """Persists and retrieves shared variables, keyed by their uppercase name."""

    @abstractmethod
    def get_all(self) -> list[SharedVariable]:
        """Return every stored shared variable."""
        raise NotImplementedError

    @abstractmethod
    def upsert_many(self, variables: list[tuple[str, JSONValue]]) -> list[SharedVariable]:
        """Create or overwrite each `(uppercase_name, value)` pair.

        When the same normalized name appears more than once in `variables`, the last
        occurrence in list order determines the stored value (FR-012).

        Returns:
            The now-current `SharedVariable` for each name given, in the same order as
            their first appearance in `variables`.
        """
        raise NotImplementedError

"""Unit tests for the variable list/set use case."""

from unittest.mock import MagicMock

from math_job_operator.application.variable_management import list_variables, set_variables
from math_job_operator.domain.entities import SharedVariable
from math_job_operator.domain.repositories import VariableRepository


def test_list_variables_delegates_to_repository() -> None:
    repository = MagicMock(spec=VariableRepository)
    repository.get_all.return_value = [SharedVariable(name="X", value=1)]

    result = list_variables(repository)

    assert result == [SharedVariable(name="X", value=1)]
    repository.get_all.assert_called_once()


def test_set_variables_delegates_to_repository_upsert_many() -> None:
    repository = MagicMock(spec=VariableRepository)
    repository.upsert_many.return_value = [SharedVariable(name="BASE_URL", value="x")]

    result = set_variables(repository, [("base_url", "x")])

    assert result == [SharedVariable(name="BASE_URL", value="x")]
    repository.upsert_many.assert_called_once_with([("base_url", "x")])

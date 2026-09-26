"""`/api/v1/variables` endpoint."""

from fastapi import APIRouter, Depends

from math_job_operator.api.deps import get_variable_repository
from math_job_operator.api.schemas.variable_schemas import VariableIn, VariableOut
from math_job_operator.application.variable_management import set_variables
from math_job_operator.domain.repositories import VariableRepository

router = APIRouter(prefix="/api/v1/variables", tags=["variables"])


@router.put("", response_model=list[VariableOut])
async def put_variables(
    variables: list[VariableIn],
    variable_repository: VariableRepository = Depends(get_variable_repository),
) -> list[VariableOut]:
    """Create or update shared variables (FR-012 through FR-014, FR-013a)."""
    updated = set_variables(
        variable_repository, [(v.name, v.value) for v in variables]
    )
    return [VariableOut(name=v.name, value=v.value) for v in updated]

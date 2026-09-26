"""Pydantic request/response schemas for shared-variable endpoints."""

from pydantic import BaseModel

from math_job_operator.domain.entities import JSONValue


class VariableIn(BaseModel):
    """One `{name, value}` pair submitted to `PUT /api/v1/variables`."""

    name: str
    value: JSONValue


class VariableOut(BaseModel):
    """One stored variable, as returned by any variable-listing endpoint."""

    name: str
    value: JSONValue

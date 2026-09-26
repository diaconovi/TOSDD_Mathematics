"""RFC 7807 Problem Details error model and shared FastAPI exception handlers."""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ProblemDetail(BaseModel):
    """An RFC 7807 "Problem Details for HTTP APIs" payload.

    Example:
        >>> ProblemDetail(
        ...     type="about:blank", title="Conflict", status=409,
        ...     detail="job already exists", instance="/api/v1/jobs",
        ... ).status
        409
    """

    type: str = "about:blank"
    title: str
    status: int
    detail: str
    instance: str


class ProblemDetailError(Exception):
    """Raise from application code to produce a Problem Details response."""

    def __init__(self, *, status_code: int, title: str, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.title = title
        self.detail = detail


def _problem_response(request: Request, *, status_code: int, title: str, detail: str) -> JSONResponse:
    problem = ProblemDetail(
        title=title, status=status_code, detail=detail, instance=str(request.url.path)
    )
    return JSONResponse(
        status_code=status_code,
        content=problem.model_dump(),
        media_type="application/problem+json",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register RFC 7807 handlers for application and validation errors.

    Example:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> register_exception_handlers(app)
    """

    @app.exception_handler(ProblemDetailError)
    async def _handle_problem_detail_error(
        request: Request, exc: ProblemDetailError
    ) -> JSONResponse:
        return _problem_response(
            request, status_code=exc.status_code, title=exc.title, detail=exc.detail
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Validation Error",
            detail=str(exc.errors()),
        )

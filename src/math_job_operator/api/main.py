"""FastAPI app factory. The process entrypoint lives in math_job_operator.server."""

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from fastapi import FastAPI

from math_job_operator.api.schemas.errors import register_exception_handlers
from math_job_operator.api.v1.jobs import router as jobs_router
from math_job_operator.api.v1.variables import router as variables_router
from math_job_operator.config import Settings, get_settings
from math_job_operator.infrastructure.filesystem.immutable_job_loader import (
    load_immutable_jobs,
)
from math_job_operator.infrastructure.mongo.client import build_database
from math_job_operator.infrastructure.mongo.job_repository import MongoJobRepository
from math_job_operator.infrastructure.mongo.variable_repository import (
    MongoVariableRepository,
)
from math_job_operator.infrastructure.mongo.variable_seed import seed_default_variables
from math_job_operator.infrastructure.signaling.redis_signal_bus import RedisSignalBus
from math_job_operator.logging_setup import configure_logging


def _build_app_state(app: FastAPI, settings: Settings) -> None:
    configure_logging(settings.LOGGING)

    database = build_database(settings)
    job_repository = MongoJobRepository(database, settings.MONGO_JOBS_COLLECTION)
    variable_repository = MongoVariableRepository(
        database, settings.MONGO_VARIABLES_COLLECTION
    )
    seed_default_variables(variable_repository)

    app.state.settings = settings
    app.state.job_repository = job_repository
    app.state.variable_repository = variable_repository
    app.state.immutable_jobs = load_immutable_jobs(settings.IMMUTABLE_JOBS_DIR)
    app.state.signal_bus = RedisSignalBus(settings.REDIS_URL)


def _make_lifespan(
    settings: Settings,
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        _build_app_state(app, settings)
        yield
        await app.state.signal_bus.close()

    return lifespan


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI application, wiring config, storage, and routers.

    `settings` defaults to `get_settings()` (the process's `.env`-derived config); tests
    pass an explicit `Settings` pointed at a disposable database instead.

    Example:
        >>> app = create_app()
        >>> app.title
        'Math Job Operator API'
    """
    resolved_settings = settings if settings is not None else get_settings()
    app = FastAPI(title="Math Job Operator API", lifespan=_make_lifespan(resolved_settings))
    register_exception_handlers(app)
    app.include_router(jobs_router)
    app.include_router(variables_router)
    return app


app = create_app()

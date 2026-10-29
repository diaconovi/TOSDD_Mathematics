"""Process entrypoint: resolve host/port from Settings and start uvicorn."""

import argparse
import sys
from collections.abc import Sequence
from typing import TypedDict

import uvicorn
from pydantic import ValidationError

from math_job_operator.config import Settings

APP_IMPORT_PATH = "math_job_operator.api.main:app"


class _BindOverrides(TypedDict, total=False):
    HOST: str
    PORT: int


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse the optional start-command flags.

    Example:
        >>> parse_args(["--port", "9191", "--reload"]).port
        9191
    """
    parser = argparse.ArgumentParser(
        prog="math-job-operator", description="Start the Math Job Operator API."
    )
    parser.add_argument("--host", type=str, default=None, help="override HOST for this run")
    parser.add_argument("--port", type=int, default=None, help="override PORT for this run")
    parser.add_argument("--reload", action="store_true", help="development auto-reload mode")
    return parser.parse_args(argv)


def load_settings(args: argparse.Namespace) -> Settings:
    """Build `Settings`, letting explicit flags win over the environment and `.env`.

    Flags are passed as init kwargs, which pydantic-settings ranks above every other
    source, so they go through the same validation as `.env` values.
    """
    overrides: _BindOverrides = {}
    if args.host is not None:
        overrides["HOST"] = args.host
    if args.port is not None:
        overrides["PORT"] = args.port
    return Settings(**overrides)


def _report_invalid_configuration(exc: ValidationError) -> None:
    for err in exc.errors():
        name = ".".join(str(part) for part in err["loc"])
        value = "<missing>" if isinstance(err["input"], dict) else err["input"]
        print(f"Invalid configuration: {name}={value}: {err['msg']}", file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> None:
    """Start the API on the host/port resolved from flags, environment, `.env`, or defaults.

    Example:
        $ uv run math-job-operator --reload
    """
    args = parse_args(argv)
    try:
        settings = load_settings(args)
    except ValidationError as exc:
        _report_invalid_configuration(exc)
        raise SystemExit(2) from None

    reload_flag = "true" if args.reload else "false"
    print(
        f"Starting Math Job Operator API on {settings.HOST}:{settings.PORT} "
        f"(reload={reload_flag})",
        flush=True,
    )
    uvicorn.run(APP_IMPORT_PATH, host=settings.HOST, port=settings.PORT, reload=args.reload)

"""Structured logging configuration for the Math Job Operator API."""

import logging
import sys
from typing import Literal

LogLevel = Literal["INFO", "DEBUG", "WARNING"]


def configure_logging(level: LogLevel) -> None:
    """Configure the root logger with a structured, single-line format.

    Example:
        >>> configure_logging("DEBUG")
    """
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
        force=True,
    )

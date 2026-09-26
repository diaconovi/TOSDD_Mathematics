"""Unit tests for the AST-based import guard."""

import pytest

from math_job_operator.infrastructure.job_runtime.import_guard import (
    DisallowedImportError,
    check_source_imports,
)

APPROVED_SOURCES = [
    "import requests\n",
    "import pymongo\nfrom pymongo import MongoClient\n",
    "from to_collector_client import CollectorClient\n",
    "import json\nimport os\n",
]

DISALLOWED_SOURCES = [
    "import fastapi\n",
    "from fastapi import FastAPI\n",
    "import uvicorn\n",
    "from uvicorn.config import Config\n",
    "import pydantic\n",
    "from pydantic import BaseModel\n",
]


@pytest.mark.parametrize("source", APPROVED_SOURCES)
def test_approved_imports_pass(source: str) -> None:
    check_source_imports(source)  # must not raise


@pytest.mark.parametrize("source", DISALLOWED_SOURCES)
def test_disallowed_imports_are_rejected(source: str) -> None:
    with pytest.raises(DisallowedImportError):
        check_source_imports(source)

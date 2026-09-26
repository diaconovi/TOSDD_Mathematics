# Quickstart: Math Job Operator API

Validates that the feature works end-to-end. See `contracts/jobs.md` and
`contracts/variables.md` for full request/response shapes, and `data-model.md` for entity
definitions.

## Prerequisites

- Python 3.14 installed and managed via `uv` (Constitution Principle II).
- A running MongoDB instance reachable at `MONGO_URL:MONGO_PORT` (defaults:
  `127.0.0.1:27017`), with database `MONGO_ACCOUNT_DB` (default `mathematics`).
- A running Redis instance reachable at `REDIS_URL` (default `redis://localhost:6379/0`).
- The Session Manager dev instance running at `http://localhost:8000` and the Collector dev
  instance at `http://localhost:8001` (per the feature's Dev/Test Environment).
- A `.env` file in the project root populated per the Configuration section of the feature
  spec/plan (`LOGGING`, `PORT`, `TIME_ZONE`, `MONGO_*`).

## Setup

```bash
uv python pin 3.14
uv sync
uv run uvicorn math_job_operator.api.main:app --reload --port "${PORT:-8000}"
```

On first run, the seed default variables (`BASE_ENDPOINT_URL`, `DEMO_ENDPOINT_URL`,
`SESSION_MANAGER_URL`, `SESSION_MANAGER_INSECURE`, `REDIS_URL`) are inserted into
`MONGO_VARIABLES_COLLECTION` if not already present.

## Validation Scenario 1 — Discover the catalog (User Story 2)

```bash
curl -s http://localhost:8000/api/v1/jobs | jq
curl -s http://localhost:8000/api/v1/jobs/dependencies | jq
curl -s http://localhost:8000/api/v1/jobs/variables | jq
```

**Expected**: the example immutable job (`awxsg_example`, or whatever name its file resolves
to per FR-007) appears with `job_type: "immutable"`; the dependency list includes `requests`
and `pymongo`; the variable list includes the five seeded defaults.

## Validation Scenario 2 — Run the example job (User Story 1)

```bash
curl -s -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '[{"name": "awxsg_example", "args": [{"epic": "AWXSG"}], "depends_on": null}]' | jq
```

**Expected**: a single `JobRunResult` with `status: "completed"`, a non-null `output`
containing collector data for epic "AWXSG", and `finished_at` rendered in the configured
`TIME_ZONE`.

## Validation Scenario 3 — Dependent jobs (User Story 1)

```bash
curl -s -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '[
        {"name": "awxsg_example", "args": [{"epic": "AWXSG"}], "depends_on": null},
        {"name": "compute_stats", "args": [{"window": 5}], "depends_on": "awxsg_example"}
      ]' | jq
```

**Expected**: both results are returned; `compute_stats` finishes after `awxsg_example` and
its logic had access to `awxsg_example`'s return value via the `upstream` variable.

## Validation Scenario 4 — Upload a mutable job (User Story 3)

```bash
curl -s -X PUT http://localhost:8000/api/v1/jobs \
  -F "file=@my_new_job.py" | jq
curl -s http://localhost:8000/api/v1/jobs | jq '.[] | select(.name=="my_new_job")'
```

**Expected**: `200 OK` with `job_type: "mutable"`; the job now appears in the catalog and is
runnable via Scenario 2's request shape.

**Rejection check** — attempt to overwrite the immutable example job:

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X PUT http://localhost:8000/api/v1/jobs \
  -F "file=@awxsg_example.py"
```

**Expected**: `409` and the immutable job's source is unchanged.

## Validation Scenario 5 — Shared variables (User Story 4)

```bash
curl -s -X PUT http://localhost:8000/api/v1/variables \
  -H "Content-Type: application/json" \
  -d '[{"name": "max_lookback_days", "value": 30}]' | jq
curl -s http://localhost:8000/api/v1/jobs/variables | jq '.[] | select(.name=="MAX_LOOKBACK_DAYS")'
```

**Expected**: the variable is listed under its uppercased name `MAX_LOOKBACK_DAYS` with value
`30`, and is available to any job run afterward.

## Automated equivalent

The scenarios above are encoded as integration tests in `tests/integration/test_jobs_api.py`
and `tests/integration/test_variables_api.py`; running `uv run pytest tests/integration` is
the automated equivalent of this quickstart.

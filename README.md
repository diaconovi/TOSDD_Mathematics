# Math Job Operator API

A FastAPI microservice that runs Python "jobs" (data-processing scripts) against Capital.com
market/instrument data on demand, via an HTTP API. See
[`specs/001-job-operator-api/spec.md`](specs/001-job-operator-api/spec.md) for the full
feature specification.

## Setup

Requires [`uv`](https://docs.astral.sh/uv/) and Python 3.14 (managed by `uv`), plus a
reachable MongoDB and Redis instance.

```bash
uv python pin 3.14
uv sync
cp .env.example .env   # then edit .env for your environment
uv run uvicorn math_job_operator.api.main:app --reload --port "${PORT:-8000}"
```

On first run, five default shared variables are seeded into MongoDB if not already present
(see **Configuration** below).

## Configuration (`.env`)

| Variable | Description | Default |
|---|---|---|
| `LOGGING` | Log level: `INFO`, `DEBUG`, or `WARNING` | `INFO` |
| `PORT` | HTTP listen port | `8000` |
| `TIME_ZONE` | IANA timezone used to render every reported timestamp | `UTC` |
| `MONGO_URL` | MongoDB host | — (required) |
| `MONGO_PORT` | MongoDB port | — (required) |
| `MONGO_ACCOUNT_DB` | MongoDB database name | — (required) |
| `MONGO_VARIABLES_COLLECTION` | Collection storing shared variables | `variables` |
| `MONGO_JOBS_COLLECTION` | Collection storing mutable job source | `jobs` |
| `REDIS_URL` | Redis connection string (cross-worker job-dependency signaling) | `redis://localhost:6379/0` |
| `IMMUTABLE_JOBS_DIR` | Directory holding immutable job scripts | `jobs/immutable` |

Adding a new **approved job dependency** (a package job scripts may import) is a
project-level change: edit `APPROVED_JOB_PACKAGES` in
`src/math_job_operator/application/job_catalog.py` and restart the service — it cannot be
done at request time.

## Job authoring contract

Every job script (immutable, under `jobs/immutable/`, or mutable, uploaded via `PUT
/api/v1/jobs`) must expose exactly:

```python
def run(arg: str) -> list:
    ...
```

- **`arg`**: the run request's full `args` list, JSON-encoded into a single string. Decode
  it yourself, e.g. `decoded = json.loads(arg)`.
- **Shared variables** and, for a dependent job, the upstream job's return value (as
  `upstream`) are injected as module-level names available inside `run()` — reference them
  as bare identifiers (e.g. `BASE_ENDPOINT_URL`), not via an import or parameter.
- Optional `DESCRIPTION` (str) and `RETURN_TYPE` (str) module-level constants customize
  what `GET /api/v1/jobs` reports; `RETURN_TYPE` defaults to `"list"`.
- Only packages listed by `GET /api/v1/jobs/dependencies` may be imported; `fastapi`,
  `uvicorn`, and `pydantic` are always rejected, even though they're installed in the
  service's own environment.

See `jobs/immutable/awxsg_example.py` for a complete example that decodes `arg`, calls
`to_collector_client` for epic `"AWXSG"`, and reads the `COLLECTOR_URL`/`COLLECTOR_INSECURE`
default variables.

## Endpoints

Full request/response contracts: [`specs/001-job-operator-api/contracts/jobs.md`](specs/001-job-operator-api/contracts/jobs.md)
and [`contracts/variables.md`](specs/001-job-operator-api/contracts/variables.md).

### `GET /api/v1/jobs`

List every available job (immutable and mutable).

```bash
curl http://localhost:8000/api/v1/jobs
```

```json
[{"name": "awxsg_example", "description": "...", "job_type": "immutable", "return_type": "list[dict]"}]
```

### `POST /api/v1/jobs`

Run a batch of jobs, optionally chaining one job to depend on another in the same batch.

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '[{"name": "awxsg_example", "args": [{"epic": "AWXSG"}]}]'
```

A dependent job:

```json
[
  {"name": "fetch_prices", "args": [{"epic": "AWXSG"}]},
  {"name": "compute_stats", "args": [{"window": 20}], "depends_on": "fetch_prices"}
]
```

Each result reports `name`, `finished_at`, `duration`, `status` (`"completed"`/`"error"`),
and `output`. A job whose declared upstream fails, or whose name/dependency isn't found, is
reported with `status: "error"` without running.

### `PUT /api/v1/jobs`

Upload or replace a mutable job (file upload; the job name is derived from the filename).

```bash
curl -X PUT http://localhost:8000/api/v1/jobs -F "file=@my_job.py"
```

Returns `409` if the derived name matches an existing **immutable** job, or `422` if the
script doesn't expose a valid `run(arg: str) -> list` entry point.

### `GET /api/v1/jobs/dependencies`

List the third-party packages approved for job scripts to import.

```bash
curl http://localhost:8000/api/v1/jobs/dependencies
```

### `GET /api/v1/jobs/variables`

List the current set of shared variables available to every job.

```bash
curl http://localhost:8000/api/v1/jobs/variables
```

### `PUT /api/v1/variables`

Create or update shared variables. Names are always stored uppercase; values may be any
JSON type.

```bash
curl -X PUT http://localhost:8000/api/v1/variables \
  -H "Content-Type: application/json" \
  -d '[{"name": "max_lookback_days", "value": 30}]'
```

## Testing

```bash
uv run pytest                                    # full suite (needs Mongo + Redis reachable)
uv run pytest --cov=src/math_job_operator/domain --cov=src/math_job_operator/application
uv run mypy --strict src/
```

Contract tests run against real MongoDB/Redis instances (no mocks), per this project's
[constitution](.specify/memory/constitution.md).

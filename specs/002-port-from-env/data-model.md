# Data Model: Listening Port & Host from Environment Configuration

This feature adds no persisted data. Its only "entities" are two fields on the existing
`Settings` configuration model (`src/math_job_operator/config.py`).

## Settings (existing model, extended)

| Field | Type / constraint | Default | Status | Spec ref |
|---|---|---|---|---|
| `PORT` | `int`, from 1 to 65535 inclusive | `8000` | existing field; constraint added | FR-003, FR-005 |
| `HOST` | `str`, surrounding whitespace stripped, at least 1 character after stripping | `"127.0.0.1"` | **new** | FR-010 |

All other `Settings` fields are unchanged.

### Value sources and precedence

Highest priority first. This applies to both fields (FR-004, FR-010):

1. An explicit start-command flag (`--port` / `--host`), passed as a `Settings(...)` init argument.
2. A process environment variable (`PORT` / `HOST`).
3. The `.env` file in the working directory.
4. The field default.

### Validation rules

| Input | Outcome |
|---|---|
| `PORT` is a whole number from 1 to 65535 (surrounding whitespace allowed) | accepted |
| `PORT` is empty, non-numeric, or outside 1–65535 | startup refused, exit status 2, message names `PORT` and the value |
| `HOST` is non-empty after trimming | accepted as-is; whether the address can be bound is checked when binding |
| `HOST` is empty or whitespace-only | startup refused, exit status 2, message names `HOST` |
| `HOST`/`PORT` valid but binding fails (port in use, or an address the machine doesn't have) | process exits non-zero; the error names the host and port; there is no fallback |

### State / lifecycle

The values are resolved once per process start, before the server binds. In reload mode the
supervisor resolves them once, and every reloaded worker inherits the same host and port. Values
don't change at runtime.

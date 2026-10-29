# Contract: Service Start Command

The operator-facing interface this feature exposes is the command that starts the service. No HTTP
endpoints change.

## Invocation

```text
uv run math-job-operator [--host HOST] [--port PORT] [--reload]
```

| Argument | Type | Required | Meaning |
|---|---|---|---|
| `--host HOST` | string | no | Overrides `HOST` from the environment and `.env` for this run only. |
| `--port PORT` | integer | no | Overrides `PORT` from the environment and `.env` for this run only. |
| `--reload` | flag | no | Development auto-reload mode. The resolved host and port apply to every reload. |

With no arguments, the host and port come from the configuration sources in the precedence order
defined in [data-model.md](../data-model.md#value-sources-and-precedence).

## Configuration inputs

Read from the process environment or `.env`:

| Name | Default | Constraint |
|---|---|---|
| `PORT` | `8000` | whole number from 1 to 65535 |
| `HOST` | `127.0.0.1` | non-empty after trimming |

## Observable behavior

| Situation | stdout/stderr | Exit status |
|---|---|---|
| Valid configuration, bind succeeds | `Starting Math Job Operator API on <host>:<port> (reload=<true\|false>)`, then uvicorn's `Uvicorn running on http://<host>:<port>` | process keeps running; `0` on graceful shutdown |
| Invalid `PORT`/`HOST` (empty, non-numeric, out of range) | stderr: `Invalid configuration: <NAME>=<value>: <reason>` (one line per invalid setting); no server starts | `2` |
| `--port` value isn't an integer | argparse usage error on stderr | `2` |
| Bind fails (port in use, or an address the machine doesn't have) | uvicorn error naming `('<host>', <port>)` and the OS reason | non-zero (uvicorn 0.53 exits with `3`) |

## Compatibility

- The previous documented command,
  `uv run uvicorn math_job_operator.api.main:app --port "${PORT:-8000}"`, still runs. It doesn't
  read `.env` for the port, and it is no longer documented.
- The `app` import path `math_job_operator.api.main:app` is unchanged, so containers or process
  managers that invoke uvicorn directly with explicit flags keep working.

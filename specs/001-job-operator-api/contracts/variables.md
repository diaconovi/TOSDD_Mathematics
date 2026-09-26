# Contract: `/api/v1/variables` endpoint

Errors use RFC 7807 Problem Details (`application/problem+json`), per Constitution Principle
VIII.

## `PUT /api/v1/variables`

Create or update one or more shared variables (FR-012–FR-014, FR-013a).

**Request** — `list[VariableIn]`

```jsonc
[
  { "name": "session_manager_url", "value": "http://localhost:8000" },
  { "name": "MAX_LOOKBACK_DAYS", "value": 30 },
  { "name": "feature_flags", "value": {"beta_stats": true} }
]
```

- `name`: any letter case accepted; normalized to uppercase before storage/matching (FR-013).
  Submitting the same normalized name twice within one request is an implementation-time edge
  case (last-write-in-request-order wins), not a request-level validation error.
- `value`: any JSON type — string, number, boolean, object, or array (FR-013a); stored and
  later returned without coercion.

**Response** `200 OK` — `list[VariableOut]` reflecting the full, now-current set of variables
named in the request (upserted), each with its normalized uppercase `name`:

```jsonc
[
  { "name": "SESSION_MANAGER_URL", "value": "http://localhost:8000" },
  { "name": "MAX_LOOKBACK_DAYS", "value": 30 },
  { "name": "FEATURE_FLAGS", "value": {"beta_stats": true} }
]
```

**Effect**: every variable set here becomes immediately available (by its uppercase name)
inside every subsequent job execution's context (FR-014), alongside any previously stored
variables not touched by this request.

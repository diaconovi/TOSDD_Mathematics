# Quickstart: Listening Port & Host from `.env`

These steps confirm the feature works end to end. Exact command behavior and messages are in
[contracts/start-command.md](contracts/start-command.md), and validation rules are in
[data-model.md](data-model.md).

## Prerequisites

- `uv sync` has been run, which installs the `math-job-operator` console script.
- MongoDB and Redis are reachable as configured in `.env`. These are the same prerequisites as
  feature 001.
- No `PORT` or `HOST` variables are exported in the shell (`unset PORT HOST`).

## Scenario 1: Port from `.env` (User Story 1, SC-001)

```bash
sed -i 's/^PORT=.*/PORT=8081/' .env
uv run math-job-operator
# other terminal:
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8081/api/v1/jobs   # → 200
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/api/v1/jobs   # → 000 (nothing there)
```

**Expected**: the startup output includes `on 127.0.0.1:8081`.

**Coexistence (SC-004)**: start the local Session Manager (port 8000) and Collector (port 8001) dev instances first. The service still starts cleanly on 8081, and all three answer at the same time:

```bash
for p in 8000 8001 8081; do curl -s -o /dev/null -w "$p → %{http_code}\n" http://127.0.0.1:$p/; done   # no "000" for any port
```

## Scenario 2: Auto-reload keeps the port (FR-008)

```bash
uv run math-job-operator --reload
touch src/math_job_operator/api/main.py     # triggers a reload
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8081/api/v1/jobs   # → 200
```

## Scenario 3: Host from `.env` (User Story 1, scenario 4)

```bash
echo 'HOST=0.0.0.0' >> .env
uv run math-job-operator
curl -s -o /dev/null -w '%{http_code}\n' http://$(hostname -I | awk '{print $1}'):8081/api/v1/jobs  # → 200
```

Afterwards, remove the `HOST` line. The service is then reachable only via `127.0.0.1`.

## Scenario 4: Default port (User Story 2, SC-005)

```bash
sed -i '/^PORT=/d' .env
uv run math-job-operator      # startup output: on 127.0.0.1:8000
```

Then restore `PORT=8081`.

## Scenario 5: One-off overrides (User Story 3)

```bash
PORT=9090 uv run math-job-operator          # → listens on 9090
PORT=9090 uv run math-job-operator --port 9191   # → listens on 9191 (the flag beats the environment)
```

## Scenario 6: Invalid values are rejected (FR-005, SC-003)

```bash
PORT=abc   uv run math-job-operator; echo "exit=$?"   # Invalid configuration: PORT=abc: ... / exit=2
PORT=70000 uv run math-job-operator; echo "exit=$?"   # ... less than or equal to 65535 / exit=2
HOST=      uv run math-job-operator; echo "exit=$?"   # Invalid configuration: HOST=: ... / exit=2
```

## Scenario 7: Port already in use (FR-006)

```bash
uv run math-job-operator &        # first instance on 8081
uv run math-job-operator; echo "exit=$?"   # error naming ('127.0.0.1', 8081) / exit≠0
kill %1
```

## Automated checks

```bash
uv run pytest tests/unit/test_server.py tests/integration/test_server_startup.py
uv run mypy src tests/unit/test_server.py tests/integration/test_server_startup.py
```

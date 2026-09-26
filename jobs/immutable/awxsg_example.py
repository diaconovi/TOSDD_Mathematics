"""Example job: queries the Collector for epic "AWXSG" and reads a default variable.

Deliverable job demonstrating the job-authoring contract: decode the JSON-encoded `arg`
string (FR-002a), call an approved third-party client package (`to_collector_client`,
FR-015), and read a shared default variable from context (FR-014).
"""

import json

from to_collector_client import CollectorClient

DESCRIPTION = "Queries the Collector's market endpoint for epic 'AWXSG' and reads a default variable."
RETURN_TYPE = "list[dict]"


def run(arg: str) -> list:
    """Fetch the AWXSG market from the Collector and return it wrapped in a list.

    `arg` is the JSON-encoded `args` list from the run request; an optional `epic`
    override may be given as `[{"epic": "..."}]`, defaulting to `"AWXSG"`.
    """
    decoded = json.loads(arg) if arg else []
    epic = decoded[0].get("epic", "AWXSG") if decoded else "AWXSG"
    times = decoded[0].get("times") if decoded else 1

    # COLLECTOR_URL / COLLECTOR_INSECURE are shared default variables injected into this
    # job's execution context (FR-014) — they are not defined anywhere in this file.
    collector_url = COLLECTOR_URL  # noqa: F821
    insecure = bool(COLLECTOR_INSECURE)  # noqa: F821

    scheme = "https" if collector_url.startswith("https") else "http"
    host_and_port = collector_url.removeprefix("https://").removeprefix("http://")
    host, _, port_str = host_and_port.partition(":")
    port = int(port_str) if port_str else (443 if scheme == "https" else 80)

    all_markets = []
    for i in range(times):

        with CollectorClient(host=host, port=port, scheme=scheme, insecure=insecure) as client:
            market = client.get_market_by_epic(epic)
            all_markets.append(market)

    return [all_markets]

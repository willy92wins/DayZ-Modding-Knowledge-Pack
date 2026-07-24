# Authority publication and authenticated loopback

Use this reference for lease queues, local daemons, brokers, launchers and any
localhost control plane. Authentication is necessary but does not establish
process provenance.

## Authority is a publication boundary

[EXACT][CLAIM-R21-RDA-AUTHORITY-PUBLICATION] Do not expose an owner, token or
generation until the authoritative WAL transition is durably complete and
re-verified.

Audit every sibling grant path, not only the canonical one. Every failure after
side effects begin needs compensation plus startup recovery. Contradictory WAL
or state must fence new authority fail-closed. Fault every
write/flush/re-read/rename/clear boundary.

## Authenticated localhost is still a network boundary

[EXACT][CLAIM-R21-RDA-AUTHENTICATED-LOOPBACK] Validate both pinned host
configurations and distinguish the launcher image from the native daemon image.
Connect first, bind the connected socket to its exact PID, and verify executable,
argv, cwd and a stable process snapshot before constructing, reading or
transmitting the secret.

A healthy response, expected body, status code, port number, keyfile existence
or loopback address is not process provenance.

## Productive transitive closure

[EXACT][CLAIM-R21-RDA-PRODUCTIVE-CLOSURE] A secret-flow audit must cover the
productive transitive closure rather than a hand-maintained file list: direct
and aliased HTTP transports, request bodies, query-key construction,
re-exports, closures, branches, comprehensions and nominal exceptions.
Exceptions need a closed grammar and exact evidence; unresolved carriers fail
closed. Include positive and negative fixtures with exact
path/function/line/kind.

## Evidence

The mechanism was verified during the DayZ MCP authority and loopback audit on
2026-07-22. Current lifecycle tooling separately registers an approved native
launcher; that later operational state does not weaken these invariants.

Verification anchors:

- `DayZ_MCP_dev/server.py:802-807,915-995`
- `DayZ_MCP_dev/dayz_test_tool.py:477-516,528-553`
- `DayZ_MCP_dev/native_launcher_transaction.py:115-151,176-207`
- `DayZ_MCP_dev/tools/approved-launchers.json:4-13`

# Crash-safe evidence indexes and multi-root bundle publication

Use this reference when an audit covers a long-running evidence campaign,
generated final index, or a release that publishes into more than one physical
root. These are audit invariants; they do not by themselves prove a particular
runtime has passed them.

## Authoritative evidence index

[EXACT][CLAIM-R21-RDA-CRASH-EVIDENCE] A crash-sensitive runtime MUST NOT append
directly to its authoritative final index.

Audit for this sequence:

1. Give each logical event a stable logical identity and each physical write a
   distinct attempt ID.
2. Materialize a create-only temporary event file, durably write it, re-read
   and verify it, then atomically rename it to an absent final path.
3. Aggregate event files order-independently and fail closed when duplicate
   logical identities disagree.
4. Publish the final JSONL/index create-only once, after a quiescent close. It
   must represent `FAIL` and `INCOMPLETE`, not only successful completion.
5. Fault both sides of every write, flush, re-read and rename boundary.

An append-only final file without a verifiable event set can be truncated,
duplicated or left internally plausible after termination.

## Publication across physical roots

[EXACT][CLAIM-R21-RDA-MULTIROOT-PUBLISH] A bundle spanning client, server,
profiles, persistence or config roots is not one atomic filesystem update.

Require:

- exact PRE and POST manifests;
- same-volume staging and archive capacity for every root;
- an append-only `PENDING` / `COMMIT` / `ABORT` journal;
- launch refusal while a transaction is `PENDING`;
- `COMMIT` only after every POST hash matches;
- `ABORT` only after every PRE hash, or first-install absence, is restored;
- termination injection at each materialize, archive, publish, verify and
  receipt boundary, in both forward and rollback directions.

If the product contract fixes canonical launch paths, generation directories
are staging/archive only; they must not silently replace the active arguments.

## Evidence

- `Utopia_PC_Suite/plans/2026-07-22-phase-0a-foundation-plan.md:262-289,375-378`
- `Utopia_PC_Suite/plans/2026-07-22-phase-0b-dedicated-persistence-plan.md:383-439`

Verification level: mechanism/source contract cross-check, 2026-07-22.

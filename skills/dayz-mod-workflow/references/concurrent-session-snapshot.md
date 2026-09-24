# Concurrent session snapshot

Load this reference when a session uses `dayz-mod-workflow` while governed
skills may be authored or promoted in parallel, or when the session must
survive a later live-target promote. The contribution authority is
`CONTRIBUTING.md` §Concurrent governed-skill maintenance; this file is only
the consumer procedure.

Authorship, `packctl validate` / `gate`, `promote --check` before `--apply`,
receipt/byte checks, full-map version rollback versus `--recover`, and the
Pack-versus-non-governed split are not restated here.

## What a session pin is

At session start, copy the **entire** artifact tree (`SKILL.md` and every
file under `references/`) from an **immutable** snapshot of the commit in
use. Prefer the vault tree
`<obsidian_snapshots>/<artifact_id>/<commit>/` when that promote exists;
otherwise add a detached worktree at that verified commit
(`git worktree add --detach <path> <commit-ish>`, from `git worktree -h`)
and copy the whole `skills/dayz-mod-workflow/` tree from it. Hash each
copied file (`sha256`) and read those copies for the rest of the session.

If a later step needs a reference not opened at start, take it from **that
same V1 snapshot**. Do not read the live target after a later promote.

Dependencies outside this artifact are not resolved by this procedure. If
any exist, choose a version (commit or digest) and record it.

A hash or a directory copy does not make an agent load those bytes. A later
live promote does not freeze in-memory context.

A **new** session reads V2 only when the host is configured **and verified**
to load the current target or that snapshot. A file-level V1/V2 copy is
not that verification.

## How to capture

1. Identify the commit.
2. Copy the whole `skills/dayz-mod-workflow/` tree from that commit's
   immutable snapshot (vault projection, or a detached worktree added at
   that commit as above).
3. Hash every copied file. Re-hash before trusting the copy.
4. Do not edit the snapshot in place.

## Limits

This pin is a file-level closure. It does not configure Cursor, Claude Code,
Codex, or any other agent host. Wiring each runtime needs separate evidence.

`--recover` restores a broken promote transaction to its recorded preimage.
Selecting an older Pack commit after a later apply is a full-map `--check`
then `--apply` of that commit: inspect every destination in the plan;
destinations that must not change must keep their digest. That is not
`--recover`.

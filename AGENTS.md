# AGENTS.md

Instructions for any AI agent working **with** this repository or **from** it.
This is the canonical agent file; `CLAUDE.md`, `GEMINI.md`, `.cursorrules` and
`.github/copilot-instructions.md` all point here.

## What this repository is

A knowledge pack for **DayZ (Enfusion) modding**: 16 domain playbooks, five
Python tools, and verified reference notes, assembled from shipped mods. It is
written to be handed to a coding agent, not read cover to cover by a human.

Two different jobs bring an agent here, and they have different rules:

- **Using the pack** to help someone mod DayZ → read §Routing and §The four rules.
- **Changing the pack** itself → also read §Contributing changes.

## Routing: load on demand, never wholesale

The pack is ~4 MB. Loading it all buries the answer you need under everything
you don't.

1. Read every `skills/*/SKILL.md` **front-matter only** (`name` + `description`).
   The `description` is written as trigger conditions — read it as "invoke me
   when…". Concatenated, they are your routing table.
2. When the task matches one, load **that whole `SKILL.md`** and follow it.
3. Open a file under that skill's `references/` **only when the procedure names
   it**. They are large and deliberately not loaded up front.
4. `skills/_shared/` holds conventions several skills cite. Keep it alongside
   them wherever you install them.

`knowledge/` is consulted, not routed: open a note when a skill points at it or
when you need a fact the skill assumes.

## The four rules

These are the whole point. Keep them even if you adapt everything else.

1. **Never invent an API.** DayZ punishes confabulation with *silent* failures —
   a class that never binds, an action that never appears, a model that loads
   white. Before writing any Enforce Script call, config class, `.p3d` selection
   or memory point: grep the vanilla source (`P:\scripts\` → `1_core`, `3_game`,
   `4_world`) or a reference here, and cite `path:line`. Semantic search and
   memory are *hints*; open the file.
2. **Respect the client/server split.** Decide which side owns each value before
   writing the feature. Most "it doesn't work" bugs are a read on the wrong side.
3. **In-game tests cost 3–10 minutes each.** Exhaust offline analysis, batch
   every pending change into one test, and have a plan B before asking for a
   rebuild. Two rebuilds with no progress means the strategy is wrong, not the
   fix.
4. **Be honest about verification.** Say *what* you checked, *how* (grep /
   checksum / repro / in-game), and what you did **not**. "It compiles" is not
   "it works". An error of exactly 0.000 is a tautology, not a triumph — and a
   catastrophic result indicts the instrument just as loudly as a perfect one.

Rules 2–4 in longer form, plus invariant tracing and end-to-end walks, are in
`README.md` §7.

## Layout

| Path | What it is |
|---|---|
| `skills/` | 16 playbooks + `_shared/`. The primary content. |
| `tools/` | Five Python tools. See [`TOOLS.md`](TOOLS.md). |
| `knowledge/` | Verified reference notes: engine facts, infra, topic syntheses. |
| `sources/` | Provenance: every distributed file's origin, licence and hash. |
| `evals/` | Regression cases for the claims the skills make. |
| `packctl/` | The validation, gating and packaging CLI. |
| `tests/` | Suite for `packctl` and the tools. |
| `promotions/` | Routing contract for promoting pack content into installed skills. |

## Installing the skills for your agent

**Claude Code** — copy `skills/*` into `~/.claude/skills/` (user-scoped) or
`<project>/.claude/skills/` (project-scoped). Discovery is by front-matter;
`/dayz-vehicles` also invokes one explicitly.

**Any other agent** — there is nothing Claude-specific in the content. Use the
routing procedure above. Some hosts read `AGENTS.md` from a project root; this
file is safe to copy next to the skills.

The pack does **not** vendor its dependencies. `README.md` §4 lists what has to
be installed separately and where it comes from.

## Contributing changes

Full rules in [`CONTRIBUTING.md`](CONTRIBUTING.md). The three that get changes
rejected most often:

- **Every executable claim carries evidence.** A new API, signature or figure
  needs a build/commit and a `path:line`. Unverified material is marked as such
  or does not ship.
- **No private paths, credentials, vanilla or third-party assets.** The privacy
  check is part of the gate, not a review courtesy.
- **Licences are load-bearing.** The pack is MIT; GPL, DPL-ND and CC-NC material
  does not enter it. Third-party attributions live in `THIRD_PARTY_NOTICES.md`.

### Gates

Run from the repository root. All are offline and deterministic.

```bash
python -m packctl validate --root . --report reports/validate.json
```

```bash
python -m packctl gate --root . --report-dir reports
```

```bash
python -m pytest -q
```

`validate` checks provenance, privacy, links and claim ranges. `gate` adds
skill validation, Python compilation, the layout corpus and a reproducible
build; it is the one that must be green before publishing. `build` produces the
release archive and refuses to run from a dirty tree — a release is built from
a committed state or it is not a release.

## What this file is not

It carries no session state, no roadmap and no task list. Those are the
author's and are not published. If you need to know what is currently true
about the repository, measure it: run the gates.

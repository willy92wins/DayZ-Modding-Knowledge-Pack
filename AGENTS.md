# AGENTS.md

Instructions for any AI agent working **with** this repository or **from** it.
This is the canonical agent file; `CLAUDE.md`, `GEMINI.md`, `.cursorrules` and
`.github/copilot-instructions.md` all point here.

## What this repository is

A knowledge pack for **DayZ (Enfusion) modding**: 17 domain playbooks, six
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

## Reaching for a tool

The skills say how to build something; the tools say whether it survived. They
are the part an agent forgets exists, so it reasons about a symptom it could
have measured, or writes a one-off parser for a format that already has a
reader. **Name the tool to the user when the work reaches one of these rows** —
including when the answer is "install it first". Full descriptions, invocations
and limits: [`TOOLS.md`](TOOLS.md).

### By symptom — reach for this before theorising

| What is observed | First instrument | What it settles |
|---|---|---|
| Model loads white, untextured or invisible | `python -m dayz_model_preflight check <p3d> --contract <json>` | Whether the selections, scale and winding the export needed are actually in the file |
| `binarize` refuses the model | same, plus `py3d.validate()` | Which LOD breaks a budget, instead of bisecting by rebuild |
| Animation never plays | `python -m dayz_animation_formats inspect <rtm> --output anatomy.json` | Whether the signature and bone track are what the engine expects |
| Layout renders empty, or a widget is missing | `python tools/dayz-ui-lab/dayz_ui_lab/parse.py <layout> --check` | Broken references and structure, offline, with no build |
| Need a 3D preview of an MLOD `.p3d` without launching DayZ | `python -m dayz_3d_viewer build-viewer <p3d>` | Whether the visual LOD, textures and materials survived the export |
| Two builds differ and nobody knows where | `python -m dayz_odol_strict diff <ref.json> <cand.json>` | The field that changed, not a visual impression |
| A change looks right in Blender but wrong in game | the in-game bridge — `knowledge/dayz-mcp-bridge-protocol.md` | The engine's opinion, which is the only one that counts |
| You are about to parse or emit a `.p3d` by hand | `py3d` | Do not write a bespoke codec; this one fails closed and verifies its own writes |

### By task — what is in play before you start

| Task | Tools | Note |
|---|---|---|
| Importing or authoring a model | `py3d` → `dayz-model-preflight` | Preflight is a gate, not a repair: it never guesses a mapping and never edits the model |
| Comparing against a shipped asset | `dayz-odol-strict` | Read-only, and its backend is **not** redistributed — external and hash-pinned, so a consumer installs it separately |
| Animation, RTM or SEAnim work | `dayz-animation-formats` | BMTR and `.anm` conversion are deliberately out of scope |
| UI and `.layout` work | `dayz-ui-lab` | The offline render is a semantic model, not the engine; DayZDiag stays the golden reference |
| Preview an MLOD `.p3d` / PAA / RVMAT | `dayz-3d-viewer` | HTML loads three.js 0.160.0 from a CDN; SWIZ, proxies and ViewPilot 1100 are documented gaps |
| Verifying anything in-game | the MCP bridge | Wiring example in `.mcp.example.json`, deliberately not auto-started |

Two habits make the difference. Propose the tool **before** the expensive step,
not after it fails — that is the whole point of a preflight. And when a tool
reports clean, say which check ran clean; "preflight passed" without naming the
contract is rule 4 with extra steps.

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

Rules 2–4 in longer form, plus invariant tracing, end-to-end walks and the
durable-memory practice this pack came out of, are in `README.md` §7.

That last one is worth naming here because it is the one an agent can act on
directly: **your context dies at the end of the session, so write what you
learned somewhere that does not.** A plain Markdown vault in version control —
the author uses [Obsidian](https://obsidian.md) — holds the verified APIs with
their `path:line`, the assumptions that turned out false, the decisions and what
they rejected. Without it every session re-derives the same facts and
re-proposes hypotheses that were already refuted. `knowledge/vault-notes/` is
what that layer looks like once it is grown; its `[[wikilink]]` syntax is
Obsidian's.

## Layout

| Path | What it is |
|---|---|
| `skills/` | 17 playbooks + `_shared/`. The primary content. |
| `tools/` | Six Python tools. See [`TOOLS.md`](TOOLS.md). |
| `examples/` | Worked examples that chain the tools on synthetic inputs. |
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

Install the CLI once. Without it `python -m packctl` resolves only while the
shell happens to be standing in the repository root, which is a precondition
nothing states and nothing enforces:

```bash
pip install -e .
```

It is stdlib-only, so the install adds no dependency — it adds an importable
module and a `packctl` entry point. The rest are offline and deterministic.

```bash
python -m packctl validate --root . --report reports/validate.json
```

```bash
python -m packctl gate --root . --report-dir ../pack-gate-reports
```

```bash
python -m pytest -q
```

The gate's report directory must sit **outside** the repository. `gate` builds
the release twice to prove reproducibility, so writing reports into the tree
would contaminate the input it is measuring; it refuses with
`GATE-REPORT-IN-ROOT` — and refuses before writing a report, so the only symptom
is a silent exit 1.

It also needs the external Agent Skills validator, pinned through
`PACK_SKILLS_REF_ROOT` (a checkout or the executable itself). It ships on PyPI
as `skills-ref`; the console script is named `agentskills`. Without it the
`skills_ref` check fails closed rather than being skipped.

`validate` checks provenance, privacy, links and claim ranges. `gate` adds
skill validation, Python compilation, the layout corpus and a reproducible
build; it is the one that must be green before publishing. `build` produces the
release archive and refuses to run from a dirty tree — a release is built from
a committed state or it is not a release.

## What this file is not

It carries no session state, no roadmap and no task list. Those are the
author's and are not published. If you need to know what is currently true
about the repository, measure it: run the gates.

# Changelog

All notable changes to the DayZ Modding Knowledge Pack are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.1.0] - 2026-08-15

The first release shipped the author's project-management layer along with the
product. This one separates them, and gives agents other than Claude Code a way in.

### Added

- `AGENTS.md` — the canonical agent file, in English, covering routing, the four
  rules, layout, installation and the gates. `CLAUDE.md`, `GEMINI.md`,
  `.cursorrules` and `.github/copilot-instructions.md` are entry points that
  point at it, so the pack is discoverable from more than one host.
- `TOOLS.md` — an index of all five bundled tools with what each one does, how to
  run it and, deliberately, **what it refuses to do**. `tools/dayz-ui-lab` was
  absent from the README entirely and is now documented.
- `knowledge/dayz-mcp-bridge-protocol.md` — the in-game verification bridge that
  `dayz-mcp-verify` drives, previously present only as a one-line caveat saying
  it was not public. The note carries the tool surface, the design invariants
  worth copying, and the engine facts the bridge cost in-game cycles to learn:
  a server-side seat is not client ownership, `SetThrottle` sets *future* input
  that `CarScript.OnInput` then overwrites, `DEVELOPER` is not defined in
  DayZDiag while `DIAG_DEVELOPER` is, and freecam freezes the simulation you are
  trying to measure. Each cited to vanilla `path:line`.
- `.mcp.example.json` — example client wiring. Named `.example` on purpose:
  agents auto-start servers declared in `.mcp.json`, and a failed launch on every
  session is worse than no config.
- README §7 rule 7, **keep a durable memory outside the agent**, recommending a
  plain-Markdown vault (Obsidian) and saying what earns a note. The practice that
  produced this entire pack appeared nowhere in it: Obsidian was named only as an
  internal promotion target, and the `[[wikilink]]` syntax in `vault-notes/` was
  explained as a formatting quirk rather than as the mechanism it is.

### Removed

- `plans/`, `specs/`, `promotions/receipts/`, `promotions/adjudications.json`,
  `HANDOFF.md` and the old Spanish `CLAUDE.md`. These were the internal process
  layer: phase roadmaps, session state and promotion bookkeeping. They described
  how the work was run, not what the pack is, and one of them published a private
  workflow instruction and a set of gotchas that had been stale for weeks.

### Fixed

- The README structure diagram was missing two skills (`dayz-clothing`,
  `dayz-persistence`) and one whole tool (`dayz-ui-lab`), and still quoted py3d
  at `1.4.0` after the 1.5.0 sync.

## [1.0.0] - 2026-08-15

First public release. Everything below was accumulated across r21 phases 01-04
and is published together.

### Added

- `knowledge/vault-notes/dayz-world-arena-optimization.md`: what the Enforce
  compiler actually charges per script module, and why almost nothing that looks
  like a size proxy is one — a million source bytes removed bought 0 kB of arena.
  Includes the vanilla early-facade pattern that moves method bodies out of the
  World arena, with its four pieces re-verified in `P:\scripts` on 1.29.
- `rip-vehicle-import` cookbooks (`family-b/`), archived runbooks (`history/`) and the
  classify viewer, which reviews a Blender sitting without opening Blender. Its
  three Three.js libraries are **not** bundled; the viewer README says where to
  fetch them, matching the pack's existing policy on third-party tools.
- `dayz-vehicles` archived gate ladders (`history/`).
- `skills/_shared/pack_skill.py`: packages a skill folder into an installable
  `.skill` zip on Windows, where the upstream packager reads `SKILL.md` without
  an explicit encoding and dies on any em-dash or accent under cp1252.
- `dayz-clothing` skill: the worn-clothing pipeline verified in-game on DayZ
  1.29, covering the three silent failure modes that make a custom
  `ClothingTypes` item load as nothing, float, or come apart. Its helper
  scripts ship with placeholder paths and must be re-pointed before use.
- Compatibility-matrix rows for `dayz-clothing` and `dayz-persistence`. The
  latter closes a gap: the skill shipped without a row, so the matrix covered
  14 of 16 skills while claiming to cover all of them.
- py3d `KNOWN-ISSUES.md`: the published blind spots of the library, including
  three checks that cannot fail for the reason you would rely on them for —
  `save(verify=True)` compares no coordinates, `python -m py3d diff` calls
  materially different models equal, and `audit_p3d.py` can print `ALL PASSED`
  having checked nothing.
- py3d absolute winding check (`_check_winding_absolute` with normal-agreement
  and edge-coherence measures) and its council regression tests.
- In-game verified skill knowledge written between 2026-07-30 and 2026-08-13:
  worn clothing binds through `DayzTemporarySkeleton` rather than
  `OFP2_ManSkeleton`; starting CF on a mission whose persistence was written
  without it crashes the server hard while naming an unrelated vanilla entity;
  the diag RPT buffers about 52 KB.
- r21 Phase 04 strict 3D tooling: SEAnim v1 / `RTM_MDAT` / `RTM_0101`
  reader-writer-inspector, contract-driven MLOD pre-export validation and a
  read-only ODOL v53-v55 anatomy/diff adapter with authorized fixtures.
- py3d 1.4.0 proxy lifecycle with explicit raw/engine frames, strict anatomy,
  atomic align/remove operations and reproducible wheel manifest.
- Rollout projections for model preflight, animation formats, strict ODOL
  parity and proxy lifecycle, including an explicit-root, backup-preserving
  no-write/apply script.
- r21 Phase 01 evidence contracts: source map, executable-claim registry and
  local-root templates.
- Root MIT license, third-party notices, contribution policy and per-skill
  compatibility matrix.
- Source-verified guidance for injected-object Forward Contracts, historical
  PBO recovery, crash-safe evidence, authority and loopback boundaries,
  incremental rebuilds, vehicle get-in/action contracts, winding lineage and
  material overrides.

### Fixed

- **Two skill descriptions were not valid YAML** and no gate had said so.
  `dayz-clothing` carried `Use for: mod de ropa` and `dayz-persistence` carried
  `auditing DayZ persistence: OnStoreSave/...`; an unquoted `: ` inside a YAML
  scalar parses as a nested mapping. Found by re-pinning the external reference
  validator, which is the entire reason criterion A3 asks for a second
  implementation — the pack's own validator checks the caps and the field names
  and had passed both files.

### Changed

- **Agent Skills reference validator re-pinned to `skills-ref==0.1.1` from PyPI**,
  whose console script is `agentskills`. The previous pin was a git commit that is
  no longer reachable in `anthropics/skills`, and whose directory is gone from
  HEAD. `packctl gate` now looks for either command name, so an existing checkout
  keeps working. 16 of 16 skills validate.
- **py3d 1.4.0 → 1.5.0, distribution renamed `py3d` → `py3d-dayz`.** The pack
  now takes its py3d bytes from the published fork
  `willy92wins/py3d-dayz@c50321c`, which was ahead of the pack and already
  carried the release text. The importable module stays `py3d`; only the
  distribution name changes, because `py3d` on PyPI is an unrelated library.
  The version moved rather than being re-sealed again because `1.4.0` had come
  to designate three different contents distinguished only by a manifest seal.
  New reproducible wheel: `py3d_dayz-1.5.0-py3-none-any.whl`, SHA-256
  `16eac9218cddb02b52b533540c0259c33d5e5b2d6ad2cd28444ef049d608a73b`.
- `audit_p3d.py` moves from `tools/py3d/rollout/` to `tools/py3d/tools/`,
  matching the published layout.
- Distinguish fail-closed ODOL parity inspection from partial MLOD recovery;
  the compatible unknown-license backend remains external and SHA-256 pinned.
- Normalized all 14 skill descriptions to the official 1024-character limit.
- Coupled `dayz-test-ingame` and `dayz-mcp-verify` to the managed
  `dayz_test_run` / `dayz_test_stop` lifecycle.
- Hardened generated test launchers so credentials are scoped to child
  processes and no VPP password is packaged by default.
- Promoted the validated Phase 01 snapshot from commit
  `7a25432febc112a957a7c1ef7a7d2c16c221b24f` to Obsidian and all configured
  skill targets with create-only receipt `c7b5366cc761a8038e52f6a2`.

### Fixed

- Make the py3d wheel builder and rollout work under Windows PowerShell 5.1,
  including deferred `$PSScriptRoot` defaults and explicit native
  `git apply` exit-code capture.
- Replace a fabricated `py3d.read_p3d` reference with the verified
  `py3d.P3D(stream)` API in the animation projection.
- Promotion now durably synchronizes and safely removes verified Windows
  sidecars containing read-only files while preserving fail-closed behavior
  for unrelated permission errors.

### Security

- Explicitly exclude secrets, personal identities, private absolute paths,
  proprietary game data and incompatible third-party payloads from releases.

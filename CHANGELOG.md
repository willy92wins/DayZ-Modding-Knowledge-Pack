# Changelog

All notable changes to the DayZ Modding Knowledge Pack are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.3.0] - 2026-08-25

### Removed

- The ODOL→MLOD conversion skill and its scripts are no longer distributed
  with the pack. Reading-side tooling stays; every consumer that needs an
  ODOL→MLOD step now takes an external, locally supplied backend, following
  the pattern `tools/dayz-odol-strict` already used (`--odol-backend` /
  `DAYZ_ODOL_BACKEND_ROOT`). References across skills, notes and tooling now
  point at that external converter.

## [1.2.0] - 2026-08-24

The pack's own gates went looking at themselves. A winding rule that had been
corrected at its source but not at its call-sites, a face flag prescribed in
the same file that measures it inert, a far-LOD target its own census reads as
the failure, and a privacy check that passed over six physical roots because
they were spelled with dashes instead of separators. Contradictions were
adjudicated by which side carried a measurement; where neither did, the entry
says so rather than picking one.

### Added

- Three tools that reached the tree without a changelog line:
  `tools/dayz-script-validator` (pre-PBO linter for Enforce Script,
  `config.cpp`, `.layout` and `.rvmat` — the boot-time failures an editor's
  compile check does not see), `tools/dayz-layout-viewer` (one `.layout`
  rendered at four viewports in a single self-contained HTML, which is where
  exact-pixel-versus-proportional bugs become visible without a build) and
  `tools/dayz-vehicle-proxy-contract` (offline gate for proxy reachability,
  source-OBJ fit and required engine properties). The pack ships nine tools.
- Four more author-owned skills from the live store: `dayz-ai-patterns`,
  `dayz-realistic-animation-director`, `uv-clean-atlas`, `3d-generation-harness`.
  Image-to-3D generators named by the harness (`hunyuan3d-local` and kin) are
  optional/external and are not shipped. PartUV weights and Expansion eAI
  source are cited, not redistributed.
- Eight author-owned 3D/pipeline skills that the pack already cited but did not
  ship: `dayz-model-pipeline`, `dayz-p3d-audit`,
  `dayz-p3d-inspector`, `dayz-proxy-align`, `dayz-animation-pipeline`,
  `mixamo-retarget`, `blender-assembly`, `blender-visual-review`. The vendored
  py3d 1.4.0 wheel those p3d skills used to carry is not included; use
  pack `tools/py3d` 1.5.0 (`pip install -e tools/py3d`). Mixamo/Adobe assets
  are not redistributed.
- Ten author-owned skills that the pack already cited but did not ship:
  `enforce-script-reference`, `dayz-mod-workflow`, `dayz-texture-pipeline`,
  `dayz-particles`, `dayz-sound-system`, `dayz-ui-development`, `dayz-doors`
  (including the author's three worked-example `.p3d`s), `dayz-physics-engine`,
  `dayz-preflight`, `dayz-pbo-build`. The vendored py3d 1.4.0 wheel that
  `dayz-pbo-build` used to carry is not included; use pack `tools/py3d` 1.5.0.
- Routing instruction (AGENTS.md step 0 and README §0): before real
  multi-session work, ask which durable memory the human will use; recommend
  Obsidian or an equivalent plain-Markdown folder and do not proceed silently
  without one.
- `tools/dayz-3d-viewer` — sixth pack tool. Converts an MLOD `.p3d` (and
  optional PAA / RVMAT) to a deterministic `.glb` and a Three.js HTML
  viewer (`python -m dayz_3d_viewer`). Pillow and LZO are optional extras;
  three.js 0.160.0 is loaded from a CDN, not bundled.
- `skills/dayz-3d-viewer` — playbook for the viewer tool. Scripts and the
  old py3d 1.4.0 wheel stay out of the skill; invocations are
  `python -m dayz_3d_viewer`.
- `examples/end-to-end` — synthetic MLOD walked through py3d, model
  preflight and the 3D viewer. `run.py` executes steps 1–3. ODOL,
  animation and UI tools are named and skipped: they do not fit this
  asset.

### Changed

- Renamed the ripped-vehicle import skill from its previous directory to
  `skills/rip-vehicle-import/` and the companion reference
  `skills/dayz-vehicles/references/rip-import.md`. Public prose now uses
  neutral import terminology; measured geometry, hashes, LODs and gates are
  unchanged.
- Synced author working-copy updates into `dayz-feature-spec` (CHK017/CHK018),
  `dayz-vehicles` (extracted references plus day-0 viewer/signoff doctrine) and
  `rip-vehicle-import` (`B7_VISUAL_SIGNOFF`). Brand tokens stay neutralized.
- The DayZ-MCP bridge that `dayz-mcp-verify` drives is now public at
  https://github.com/willy92wins/dayz-mcp (MIT). The README, the bridge
  protocol note and `.mcp.example.json` point at it with the install one-liner
  instead of describing the skill as methodology for a private tool.

### Fixed

- README §4 said those ten skills (and the 3D playbooks still arriving) were
  first-party Anthropic content, not redistributable, and told readers to
  install the `anthropic-skills` plugin. That was false: they are the author's;
  `anthropic-skills` is only the local plugin folder name.
- `AGENTS.md` counted six tools while `TOOLS.md` counted nine, and the README's
  `tools/` row and structure diagram both named six of the nine. The canonical
  agent file was the one that was wrong.
- Eighteen tracked files had been edited without refreshing their `output_hash`
  in `sources/source-map.json`. The cost was not cosmetic: `gate` only runs the
  double build when no finding carries error severity, so the stale hashes made
  `build_reproducible` report `SKIPPED` — with no reason printed — and the
  pack's headline property went unmeasured. Gate is back to 7/7 with two
  byte-identical builds.
- The pack taught, in six places, that the Blender Z-up to DayZ Y-up rotation
  flips face handedness and that every face in every LOD must therefore be
  reversed. It does not. That rotation (`x'=x, y'=z, z'=-y`) has determinant
  +1, so it preserves winding; reversing anyway yields 100% flipped faces — a
  model visible only from inside. Only a reflection (determinant < 0, such as
  the pure swap a glTF import uses) requires the reversal. Rule 12 of
  `dayz-model-pipeline` already said so; the correction had not reached three
  stale cross-references inside that same file, two further files, or
  `references/py3d-direct-generation.md`, where the checklist at line 228 went
  as far as declaring `UNIFORM_FLIPPED` the correct post-fix state and
  `UNIFORM_NON_FLIPPED` the mark of a skipped step — the exact opposite of what
  line 263 of the same file says a correct assembly reports.
- `check_dayz_winding.py` printed its outward-normal fraction and then ignored
  it, so a model with inward normals still exited 0. The measurement is now the
  verdict, with a threshold placed where the metric can actually discriminate,
  and an unreadable model exits 2 instead of passing.
- `rip-import.md` prescribed the MLOD face flag `0x20000` for two-sided
  rendering in the same file that records, twenty lines later, the in-game test
  showing it does nothing. The prescription is withdrawn in the four places it
  appeared. What is established is bounded to what was measured: setting
  `0x20000` did not work, and double-siding the geometry does. Whether DayZ
  ignores a "both sides" face flag in general is still open, because
  `dayz-custom-infected.md` disputes the bit itself (`0x20000` against the
  Bohemia wiki's `0x00000020`) and the wiki value has never been tested.
- Invariant 13 of `dayz-vehicles` prescribed flipping a far LOD to 100%
  cross-outward, four lines above the census that measures ~98% cross-outward
  as the inverted state and lands the fix at ~2%, confirmed in-game on SUB_BRZ.
  Following the prescription delivered you into the state the measurement
  calls broken. The target is retired; the distinction the two draw — black is
  stored normals, transparent is vertex order — is kept, since it is the
  measurement's own.
- `killers-detail.md` explained that an inverted collision LOD hides behind a
  correct-looking model because "the renderer draws both sides". DayZ renders
  single-sided with backface culling, which the pack knows from two independent
  in-game cases. The same file also prescribed an absolute
  "cross-product must point AWAY from mesh center" detection fifteen lines
  above the block recording that this heuristic false-positived on every
  Blender export and was disabled — the disablement that let an inverted
  collision sphere pass a full audit as ALL PASSED. Both now name the relative
  comparison against the Visual LOD that `audit_p3d.py` actually runs.
- Six published files carried a physical system root, which `validate_privacy`
  is meant to prevent and reported zero findings on. Its two patterns require
  path separators and correctly exempt the `<you>` placeholder; neither can
  reach the same path flattened into one dash-joined name component sitting
  further along the very same line. Whoever scrubbed those files replaced the
  one occurrence the gate inspects, and the gate inspects only there. The
  roots are gone and a third pattern covers the flattened shape, with a test
  written to fail first — and which did.

### Removed

- `skills/grok-handoff-template`, `skills/qwen-handoff-template` and
  `skills/zcode-handoff-template`. They arrived under version control on
  2026-08-22 and are the process layer 1.1.0 deliberately stopped publishing:
  how to drive a paid CLI, a local Ollama model and a vendor app, not how to
  mod DayZ. They were also the only Spanish files left under `skills/`, they
  referenced a `codex-handoff-template` this pack does not ship, and one
  reference published a single machine's tool paths. They were never in
  `promotions/promotion-map.json` either, so they were never governed content.

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

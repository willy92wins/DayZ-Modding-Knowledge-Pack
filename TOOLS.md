# Tools

Six Python tools ship in this pack. All are stdlib-first, offline and
deterministic; none of them phone home, and none of them guess.

They exist because the DayZ asset pipeline fails *silently*: a `.p3d` written
with a stale selection loads white, a mistyped RTM signature produces an
animation that never plays, a `.layout` typo yields an empty screen with no
error. Each tool turns one of those silent failures into an early, actionable
one.

| Tool | What it does | Writes files? |
|---|---|---|
| [`py3d`](#tools-py3d) | Read and write MLOD `.p3d` models | **Yes** — with atomic write + verify |
| [`dayz-animation-formats`](#tools-dayz-animation-formats) | Read/write/inspect RTM and SEAnim v1 | Yes |
| [`dayz-model-preflight`](#tools-dayz-model-preflight) | Gate a `.p3d` against a contract before export | No — read-only |
| [`dayz-odol-strict`](#tools-dayz-odol-strict) | Inspect and diff binarized ODOL models | No — read-only |
| [`dayz-ui-lab`](#tools-dayz-ui-lab) | Parse, compose, render and diff `.layout` UIs offline | Reports only |
| [`dayz-3d-viewer`](#tools-dayz-3d-viewer) | Convert MLOD `.p3d`, PAA and RVMAT to glTF + HTML | **Yes** — `.glb`, PNG, HTML |
| [`dayz-script-validator`](#tools-dayz-script-validator) | Lint Enforce, `config.cpp`, `.layout` and `.rvmat` before packing | Reports only |

---

## `tools/py3d`

A DayZ-specific fork of [KoffeinFlummi/py3d](https://github.com/KoffeinFlummi/py3d)
(MIT) — a pure-Python reader/writer for the **MLOD `.p3d`** format, the editable
non-binarized model format. Most asset scripts in these skills import it.

Upstream is an unmaintained minimal codec. This fork adds the anti-corruption
guards: the paths that used to silently produce a broken `.p3d` now fail early
with an actionable message.

- `lod.new_selection(name)` — get-or-create a selection that binds and registers.
- `lod.set_memory_point(name, xyz)` / `get_memory_points()` — idempotent upsert.
- `lod.faces_by_material()` / `faces_for_material(n)` — case-insensitive match.
- `p3d.save(path, verify=True, backup_dir=...)` — atomic write with reopen,
  re-parse and invariant check; on failure the original stays byte-intact.
- `p3d.validate()` → `list[Finding]` (stale selection, weight range, normals
  budget, …).
- A complete fail-closed proxy lifecycle: raw/engine frame conversion,
  `add_proxy`, strict enumeration, in-place align, index-safe remove.

```bash
pip install -e tools/py3d
```

The distribution is named **`py3d-dayz`**; the import name stays `py3d`. A
different, unrelated library is published on PyPI as `py3d`, so assert you got
this one:

```bash
python -c "import py3d; assert py3d.IS_DAYZ_FORK; print(py3d.__version__)"
```

Current version **1.5.0**. Upstream for this fork:
[willy92wins/py3d-dayz](https://github.com/willy92wins/py3d-dayz). Known
limitations are listed in `tools/py3d/KNOWN-ISSUES.md` — read it before
assuming a bug is yours. **Licence:** MIT, `tools/py3d/LICENSE` (© 2017 Felix
Wiegand); keep that file with any redistribution.

## `tools/dayz-animation-formats`

Strict reader/writer for **SEAnim v1** and **DayZ RTM** (`RTM_MDAT` and
`RTM_0101`), plus deterministic JSON inspection.

```bash
python -m dayz_animation_formats inspect input.rtm --output anatomy.json
```

Unsupported signatures fail closed rather than being parsed on a guess. The
frozen first-party fixtures are independently decoded by Arma3ObjectBuilder
during validation, so the reader is checked against a second implementation and
not only against itself.

**Out of scope, deliberately:** BMTR, and `.anm` conversion.

## `tools/dayz-model-preflight`

A read-only gate that answers "will this `.p3d` survive export?" *before* you
spend a build on finding out. Driven by a versioned JSON contract, it composes
`py3d.validate()` with the intended scale, the bone selections that must exist
and be non-empty, and determinant-aware face-lineage and winding checks.

```bash
python -m dayz_model_preflight check target.p3d \
  --contract preflight.json --json preflight-result.json
```

Requires the py3d fork `>=1.4.0`. Missing or ambiguous one-to-one lineage is
reported `INVALID`: the tool never guesses a mapping and never repairs a model.

## `tools/dayz-script-validator`

The **offline gate**: a pre-PBO linter for Enforce Script, `config.cpp`,
`.layout` and `.rvmat`. It catches the family of mistakes that compile-check
clean in an editor and only surface when the script module compiles at boot —
where the symptom is a dead module, a frozen loading screen or a ghost class,
and the diagnosis costs a full in-game cycle.

```bash
python tools/dayz-script-validator/scripts/script_validator.py <addon_root>
python tools/dayz-script-validator/scripts/ui_reconcile.py <addon_root>
```

Exit `0` PASS / `1` FAIL / `2` WARN, findings as JSON on stdout. Under a second
over a full addon, so it belongs in every pass rather than at the end.

`--terse` swaps the JSON report for a verdict on the **first line** and one line
per finding. The exit code is the machine channel; this is the one a human or an
agent actually reads, and it is what the editor hook surfaces.

```
PASS
WARN - 1 warning
  ES-EMPTY-IFDEF-UNSUPPORTED-PATTERN  [WARN] scripts/4_World/Foo.c line 239: ...
```

Rules are one module per defect under `scripts/detectors/`, over a source
stripped of comments and string literals by `scripts/stripper.py` so a pattern
mentioned inside a literal never fires. Coverage today spans refcount misuse
(`delete`), preprocessor traps (empty `#ifdef`), method-scope locals, unchecked
`ctx.Read`, the `SetSynchDirty` contract, `RegisterRecipies` (the vanilla hook
really is spelled with the typo), config classes declared under the wrong
`CfgXxx`, missing `.layout` files and `$PBOPREFIX$` mismatches.

`ui_reconcile.py` is the companion cross-check: `FindAnyWidget`/`FindWidget`
literals against the widgets a `.layout` actually declares, and `#STR_` keys
against the stringtable. Both classes of bug compile fine and only appear when
the menu opens.

**Known coverage limit, stated up front.** Four detectors read curated tables in
`scripts/shared/vanilla_reference.py` that are deliberately small, because the
linter does not parse the vanilla script tree at runtime. That trades false
negatives for a guarantee of no false positives from that path. **A green run is
not proof of absence**, and it predicts that the module compiles and the asset
loads — never that the engine behaves. Behaviour is the online layer's job.

## `tools/dayz-odol-strict`

Fail-closed, read-only anatomy inspection and deterministic diff for **ODOL
v53–v55** — the binarized model format the engine actually ships.

```bash
python -m dayz_odol_strict inspect input.p3d \
  --backend-root <external-backend> --json anatomy.json
python -m dayz_odol_strict diff reference.json candidate.json
```

The adapter, the schemas and three user-authorized first-party fixtures are
redistributable and included. The compatible BisDLL-derived backend is **not**:
it has no redistribution licence, so it stays external, hash-pinned, and is
loaded only inside an isolated subprocess.

**There is no ODOL writer and no partial-success mode**, and neither is planned.
Inspecting a binarized model is a diagnostic; producing one is the engine's job.

## `tools/dayz-ui-lab`

An offline lab for DayZ `.layout` UIs: parse a layout into a JSON IR, compose
scenarios from shells and subviews, emit a deterministic semantic render at a
given viewport, and diff two renders into actionable defects.

```bash
python tools/dayz-ui-lab/dayz_ui_lab/parse.py <layout> --check
python tools/dayz-ui-lab/dayz_ui_lab/scenario.py --scenario s.json --viewport 1920x1080
python tools/dayz-ui-lab/dayz_ui_lab/render.py --scenario s.json --viewport 1920x1080 --out render.json
python tools/dayz-ui-lab/dayz_ui_lab/diff.py --observed render.json --expected ref.json --report diff.json
python tools/dayz-ui-lab/dayz_ui_lab/corpus.py --root .
```

`diff.py` reports broken references, clipping, overlap and missing states per
widget and scenario. `corpus.py` is the regression gate: it parses the pinned
public corpora (VPP, Expansion, TraderPlus, TraderX) plus a first-party negative
set — **376/376 layouts, zero diagnostics** — and audits that no third-party
layout is redistributed with the pack.

**The offline render is not the engine.** It is a semantic model good enough to
catch structural mistakes before a build; DayZDiag remains the golden reference
for anything that depends on real rasterization, fonts or the live widget tree.

## `tools/dayz-3d-viewer`

Convert an MLOD `.p3d` plus optional `.paa` / `.rvmat` into a `.glb` and a
standalone Three.js HTML viewer. Two HTML modes: `embedded` (typed arrays
and base64 textures, no `fetch`) and `web` (external `.glb` via
`GLTFLoader`).

```bash
python -m dayz_3d_viewer p3d-to-glb model.p3d model.glb
python -m dayz_3d_viewer paa-to-png base_co.paa base_co.png
python -m dayz_3d_viewer parse-rvmat housing.rvmat
python -m dayz_3d_viewer build-viewer model.p3d --textures ./tex --mode embedded
```

Requires the pack py3d fork `>=1.5.0`. Pillow and LZO are optional extras
(`[paa]`, `[lzo]`); a missing extra exits 2 with a one-line message.
Generated HTML loads **three.js 0.160.0 from jsDelivr** — it is not
bundled, so a render needs a network. Known converter gaps (SWIZ, proxy
triangles, ViewPilot at resolution 1100) are listed in
`tools/dayz-3d-viewer/KNOWN-ISSUES.md` and are not repaired here.

---

## What is deliberately absent

The DayZ 3D pipeline still needs more than this — Blender→`.p3d` assembly,
PNG→PAA encoding, PBO packing. Those live in tooling that is not the
author's to redistribute; `README.md` §4 lists what to install and where
it comes from. PAA *decoding* is now in `tools/dayz-3d-viewer`.

The offline in-game verification bridge is described in
[`knowledge/dayz-mcp-bridge-protocol.md`](knowledge/dayz-mcp-bridge-protocol.md).

# Tools

Nine Python tools ship in this pack. They are offline and deterministic;
none of them phone home, and none of them guess. Most are stdlib-only;
[`dayz-vehicle-proxy-contract`](#tools-dayz-vehicle-proxy-contract) also
needs numpy, scipy, matplotlib and the pack py3d fork.

**Install before invoking.** The `python -m <tool>` forms below resolve only
once that tool is installed — `python -m pip install -e tools/<name>` from the
repository root. On a fresh clone they fail with `No module named`, which
reads like a broken tool and is a missing install. Tools that also ship a
script path (`dayz-script-validator`, `dayz-ui-lab`) can be run from the tree
without installing; each tool's section says which.

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
| [`dayz-layout-viewer`](#tools-dayz-layout-viewer) | Preview a `.layout` as HTML at four viewports | **Yes** — one `.preview.html` |
| [`dayz-3d-viewer`](#tools-dayz-3d-viewer) | Convert MLOD `.p3d`, PAA and RVMAT to glTF + HTML | **Yes** — `.glb`, PNG, HTML |
| [`dayz-script-validator`](#tools-dayz-script-validator) | Lint Enforce, `config.cpp`, `.layout` and `.rvmat` before packing | Reports only |
| [`dayz-vehicle-proxy-contract`](#tools-dayz-vehicle-proxy-contract) | Audit vehicle proxy graph, fit, engine properties and PBO closure | Reports only; `repair` stages copies outside the addon |

---

## Two `.layout` parsers

There are two readers. Neither is a superset of the other. Pick by the
question you are asking, not by which file you already have open.

Measured on 2026-08-19 over the 819 `.layout` files of the working tree:

| | `layout_ast.py` (DayZ_Tooling) | `dayz-ui-lab` (this pack) |
|---|---|---|
| Job | GEOMETRY | FORMAT |
| Keeps | 11 geometry and flag keys | all keys |
| Exceptions over 819 | 0 | 57 (45 are copies of ONE first-party HUD, 12 are XML files) |
| Continuation `\` + newline | does not reconstruct it | one LF — matches what was measured in DayZDiag |
| Serves | rectangles, click centres, reachability | render, scenarios, and anything that reads text/color/image |

Choice rule, in one line: **if you need where a widget IS, the geometry parser; if you need what it SAYS, the format parser. Neither is a superset of the other.**

A third, historical parser exists (`renderer/parse.py` from the DayZ_UI_Research
project). It is **superseded**. On Windows paths it **silently strips the
backslash** (`gui\layouts\foo.edds` → `guilayoutsfoo.edds`). Do not revive it.

Inline-format collapse into `position` was a measured defect of the format
parser: grouping by physical line in `Parser.parse_values` turned
`ImageWidgetClass Bg { position 0 0 size 1 1 stretch 1 ignorepointer 1 { } }`
into a single `position` attribute holding the whole list. Fixed in commit
df64e5f **for the vocabulary the parser knows**: `parse_values`
consumes by measured key arity, and that input now yields four attributes. The
bound is the point. An attribute missing from `ATTRIBUTE_ARITY` still falls back
to line grouping, so two unknown keys written inline still collapse into one —
measured, `{ zzz_custom 0 0 yyy_other 1 1 }` yields one attribute, while
`{ position 0 0 zzz_custom 7 }` splits correctly because the known key's arity
ends its run. Adding an attribute to the table is what extends the fix. The
geometry parser splits by arity throughout.

A screen-rectangle predictor (`ui_rects.py`: `predict` / `lint` / `centers`)
sits on the geometry parser. It is **not published in this pack** — it lives
in the unpublished DayZ_Tooling workbench, and this pack ships the format lab,
not a second, partial geometry model. Unmodelled anchors (`halign left_ref` /
`valign top_ref`, `hexactpos 1`) are refused, not guessed. Route:
[`GETTING-STARTED.md`](GETTING-STARTED.md) §3.

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

**Vanilla control — linter authors only, not a mod-cycle step.** Before
committing a change under `tools/dayz-script-validator/` (a new rule, a
touched detector, a touched parser), compare the linter's findings on
Bohemia's vanilla tree against the pinned baseline:

```bash
python tools/dayz-script-validator/scripts/vanilla_control.py
```

A full run takes about 85 seconds (`tools/dayz-script-validator/README.md`;
not re-timed here). Without a local vanilla tree the control SKIPs with
exit 2. A green control only proves the linter is silent on that tree; it
does not prove the new rule catches anything. Optional flags from
`--help`: `--vanilla-root`, `--baseline`, `--update`, `--json`.

## `tools/dayz-vehicle-proxy-contract`

The **offline vehicle-proxy gate**: it checks that every declared proxy on a
vehicle host is reachable, that the source OBJ still fits the assembled P3D
within the manifest thresholds, that required engine properties such as
`autocenter=0` are present, that animated selections do not steal a proxy
triangle unless the manifest names that exact host/LOD/selection triple, and
that the deployed PBO still hashes to the source bytes.

```bash
python tools/dayz-vehicle-proxy-contract/scripts/vehicle_proxy_contract.py audit \
  --manifest <manifest.json> --out <outdir>
python tools/dayz-vehicle-proxy-contract/scripts/vehicle_proxy_contract.py preview \
  --manifest <manifest.json> --out <outdir>
python tools/dayz-vehicle-proxy-contract/scripts/vehicle_proxy_contract.py repair \
  --manifest <manifest.json> --staging <abs-staging-dir> \
  --operation set-autocenter-zero|yaw180|affine-fit
python tools/dayz-vehicle-proxy-contract/scripts/vehicle_proxy_contract.py self-test
```

Exit `0` PASS / `1` FAIL / `2` self-test control miss / `3` self-test broken /
`4` input or internal error / `64` usage. `audit` publishes
`report.json`, `summary.txt` and `lod-overview.json` into a new `--out`
directory, or nothing at all on exit `4`. `preview` adds sampled point-cloud
PNGs. `repair` stages copies under a new absolute directory outside the addon
root; it does not rewrite the source tree and it does not pack a PBO.

The manifest is the only place paths live. Every stored path
(`addon_root`, `host_p3d`, `cfgconvert`, source scene, piece OBJ, deployed
PBO) must already be absolute. The tool has no default `C:\...` converter
or addon root.

Needs the pack py3d fork, numpy, scipy and matplotlib. `CfgConvert` is an
external adapter named by the manifest, not a bundled binary.

**A green run is not proof the vehicle plays.** It predicts that the declared
proxy graph, the source-to-assembly fit, the required properties and the
deployed bytes match the contract. It does not predict look, animation, IK,
damage zones, get-in points or physics. Deferred host-axis warnings
(`P3D-AXIS-SELECTION-DEFERRED`) are explicit about that: steering and damper
motion remain an online gate. Behaviour is the online layer's job.

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
given viewport, and diff two renders into actionable defects. This is the
**format** parser in [Two `.layout` parsers](#two-layout-parsers). Geometry
(rectangles, click centres) is a different reader, outside this pack.

```bash
python tools/dayz-ui-lab/dayz_ui_lab/parse.py <layout>
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

## `tools/dayz-layout-viewer`

Emits one self-contained `*.preview.html` for a `.layout`, with the same tree
drawn at **four viewports** (1080p, 1440p, ultrawide 21:9, 720p) plus the
parser's diagnostics. Switching between them is the whole point: exact-pixel
widgets keep their pixels while proportional ones scale, which is the "looked
right in the mockup, wrong in game" failure made visible without a build.

```bash
python tools/dayz-layout-viewer/build_viewer.py <layout> [-o out.html]
```

It reads through `dayz-ui-lab`'s format parser, so it inherits that contract —
including the continuation and fail-closed escape behaviour — rather than
carrying a second lexer. It is **not** `dayz-ui-lab/render.py`, which emits
semantic scenario JSON and no HTML.

**A structural approximation, not the rasterizer.** Its README enumerates what
it does not do, and the list is the useful part: no font atlas, no `.paa` /
`.edds` decode, no script-side `SetColor` / `SetText`, no spacer re-flow (the
authored `position`/`size` are drawn, and the engine overwrites those), no
`.styles`, and no claim about the `right_ref` / `bottom_ref` offset sign, which
is still unverified. Trust it for structure and anchoring; for pixels, colour
and fonts, DayZDiag.

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

The screen-rectangle predictor (`ui_rects.py`) is also absent on purpose:
it belongs to the unpublished DayZ_Tooling workbench, not this pack. See
[Two `.layout` parsers](#two-layout-parsers).

The offline in-game verification bridge is described in
[`knowledge/dayz-mcp-bridge-protocol.md`](knowledge/dayz-mcp-bridge-protocol.md).

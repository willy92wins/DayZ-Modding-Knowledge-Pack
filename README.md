# DayZ Modding Knowledge Pack

A distilled, battle-tested knowledge base for **DayZ (Enfusion) modding**, assembled by a
working DayZ modder and their AI assistant across dozens of shipped mods — vehicles, aircraft,
weapons, characters, base-building, persistence systems, and full Blender→`.p3d` asset pipelines.

It is meant to be **handed to an AI coding assistant** (Claude Code, or any capable LLM agent)
so it can help you mod DayZ with the same playbooks, tools, and hard-won gotchas that produced
those mods.

It contains three things:

| Part | What it is |
|---|---|
| `skills/` | 14 structured **playbooks** ("skills") — one Markdown procedure per domain, with on-demand `references/`. |
| `tools/` | The **py3d DayZ fork** plus strict RTM/SEAnim inspection, MLOD pre-export and ODOL parity tools. |
| `knowledge/` | **Verified reference notes** — technical facts, infra, and cross-project pattern syntheses. |

---

## 0. TL;DR for the assistant reading this

If you are an AI assistant tasked with helping the user mod DayZ, internalize this first:

1. **A "skill" is a playbook you load on demand.** Each `skills/<name>/SKILL.md` starts with a
   `description:` that lists its trigger conditions. When the user's task matches, open that
   `SKILL.md`, follow it, and pull files from its `references/` folder only when the procedure
   points you there (progressive disclosure — don't read everything up front).

2. **The one rule that makes DayZ modding work: never invent an API.** DayZ punishes
   confabulation with *silent* failures — a class that never binds, an action that never shows,
   a model that loads white. Before you write any Enforce Script function, config class, `.p3d`
   selection name, or memory point, **grep the vanilla source** (`P:\scripts\` — see
   `knowledge/DAYZ_INFRA.md`) or a reference in this pack, and cite `path:line`. Then use it.
   This discipline is baked into every skill here; keep it.

3. **The client/server split is not optional knowledge.** Most "it doesn't work" bugs are a
   value read on the wrong side. Map which side owns each piece of state *before* writing a
   feature. `enforce-script-reference` (see §4) and `knowledge/` cover this.

4. **In-game testing is expensive (3–10 min per cycle).** Do all offline analysis first, batch
   every pending change into one test, and have a plan B/C ready before you ask for a rebuild.

---

## 1. What's inside

```
DayZ-Modding-Knowledge-Pack/
├── README.md                     ← you are here
├── compatibility-matrix.md       ← per-skill build/evidence status
├── CONTRIBUTING.md               ← evidence, privacy and contribution rules
├── THIRD_PARTY_NOTICES.md        ← included and research-only attributions
├── sources/                      ← provenance and executable-claim contracts
├── skills/
│   ├── _shared/                  ← conventions referenced by several skills
│   │   ├── dayz-conventions.md
│   │   └── enscript-style.md
│   ├── dayz-vehicles/            ← cars, trucks, quads, bikes, boats (CarScript)
│   ├── dayz-aviation/            ← planes, seaplanes, helicopters
│   ├── dayz-weapons/             ← custom firearms (entity side)
│   ├── dayz-characters/          ← infected, survivors, NPCs (rig to OFP2_ManSkeleton)
│   ├── dayz-basebuilding/        ← buildable structures (BaseBuildingBase)
│   ├── dayz-test-ingame/         ← build + deploy + launch with DayZDiag + filepatching
│   ├── dayz-mcp-verify/          ← auto-test a mod by driving it (see caveat §8)
│   ├── dayz-pbo-reverse-engineering/  ← learn from another author's PBO
│   ├── dayz-feature-spec/        ← spec + consistency gate before coding
│   ├── rip-vehicle-import/            ← convert a ripped racing-game car into a drivable DayZ vehicle
│   ├── rigorous-data-audit/      ← audit persistence/state-machine code before release
│   ├── blender-animation/        ← author animations in Blender (via MCP) → DayZ
│   ├── ai-3d-to-dayz/            ← AI-generated 3D (Hunyuan/Tripo/TRELLIS) → DayZ
│   └── ardy-motion-generation/   ← motion generation → DayZ integration
├── tools/
│   ├── py3d/                     ← DayZ fork of py3d (MLOD .p3d codec), MIT
│   ├── dayz-animation-formats/   ← strict RTM/SEAnim v1 reader/writer/inspect
│   ├── dayz-model-preflight/     ← contract-driven MLOD export gate
│   └── dayz-odol-strict/         ← read-only ODOL v53-v55 anatomy/diff adapter
└── knowledge/
    ├── DAYZ_TECHNICAL_NOTES.md   ← py3d MLOD facts, LODs, winding, config, runtime
    ├── DAYZ_INFRA.md             ← drives, AddonBuilder, serverDZ.cfg, RPT triage, terrain
    └── vault-notes/              ← 16 topic notes (see §6)
```

---

## 2. How to use the skills

### What a skill is
A skill is a folder with a `SKILL.md` (the procedure, with YAML front-matter: `name`,
`description`) and usually a `references/` folder of deeper material the procedure links to.
The `description` is written as **trigger conditions** — read it as "invoke me when…".

### If your assistant is Claude Code
Copy the skill folders into a skills directory Claude Code reads:

- **Project-scoped:** `<your-project>/.claude/skills/`
- **User-scoped (all projects):** `~/.claude/skills/` (Windows: `%USERPROFILE%\.claude\skills\`)

Copy the contents of `skills/` into one of those (keep `_shared/` alongside them — several
skills reference `_shared/dayz-conventions.md` and `_shared/enscript-style.md`). Claude Code
auto-discovers them by their front-matter and invokes them by trigger; you can also call one
explicitly, e.g. `/dayz-vehicles`.

### If your assistant is a different LLM / agent
There is nothing Claude-specific about the content. Use them as **retrieval-and-follow**
playbooks:
1. Match the user's task against the `description:` blocks (a cheap way: concatenate all
   `SKILL.md` front-matters into your context as a routing table).
2. When one matches, load that whole `SKILL.md` into context and follow it step by step.
3. Load a file from `references/` only when the procedure names it.

Do **not** dump the entire pack into context at once — it is large by design. Route, then load.

---

## 3. Skill index

**Vehicles & aircraft**
| Skill | Use when |
|---|---|
| `dayz-vehicles` | Authoring, importing or debugging a **drivable ground/water vehicle** (car, truck, quad/ATV, motorbike, boat) on the CarScript/Boat base. Owns the full `config.cpp` + `model.cfg` contract (SimulationModule drivetrain, Axles/Wheels, Crew, AnimationSources, `wheel_1_1..2_2`), structural parity vs a vanilla vehicle, and the packaging failures that pass local filepatching but break on a dedicated server (white/untextured, reversed wheel spin). **Invoke before writing any ground-vehicle entity/config.** |
| `dayz-aviation` | **Planes, seaplanes, and helicopters** via the CarScript-as-aviation pattern. Real aerodynamics in Enforce Script (lift/drag/stall, ISA atmosphere), NaN-safe physics, PID auto-stabilization, flight-control AnimationSources, aviation memory points, script-driven dials, Buoyancy for seaplanes, retractable gear, RPM-band sound. Documents 5 flight-model implementations across 4 authors. |
| `rip-vehicle-import` | Converting a **racing-game rip** (source-game 'Grub': `.modelbin`/`.carbin`) into a drivable, textured DayZ CarScript car. A 12-step pipeline + day-1 checklist + winding/glass/interior/material rules distilled from ~30 sessions on the first car. Pairs with `dayz-vehicles`. |

**Weapons, characters & animation**
| Skill | Use when |
|---|---|
| `dayz-weapons` | Custom **firearm** (entity side): the `.p3d` contract (bolt/trigger/magazine selections + memory points), weapon-selection→player-bone remap (`AddItemBoneRemap`), the `CfgWeapons`/`config.cpp` contract, inheritance base choice (Rifle_Base / BoltActionRifle_Base / Pistol_Base…), fire modes, dispersion, recoil, jam config, attachment/optics slots, muzzle-flash + ejection points. |
| `dayz-characters` | **Humanoid characters** (custom infected/zombies, survivors, NPCs): mesh → retopo → rig to `OFP2_ManSkeleton` → UV + normal bake → character LODs → `config.cpp` inheritance (ZombieMaleBase / SurvivorBase…) → PBO. Owns baked scaling (runtime `SetScale` is broken), the one-anim-mod-at-a-time wall, canonical bind pose. |
| `blender-animation` | Authoring or modifying **animations in Blender** (via the Blender MCP) and handing them off to DayZ (RTM / `.anm` / `.txa` / SEAnim). Includes physics-sim driven motion. |
| `ardy-motion-generation` | **Motion generation** for characters/creatures and the plan to integrate generated motion into DayZ. |

**Base building**
| Skill | Use when |
|---|---|
| `dayz-basebuilding` | **Buildable player structures** on `BaseBuildingBase` (fences, watchtowers, gates, tents, shelters, flag poles). The `Construction{}` block field-by-field, the four-class runtime quartet (BaseBuildingBase / Construction / ConstructionPart / ConstructionActionData), synced-bitmask persistence (part id caps at 93, `OnStoreSave/Load` ordering), hologram deploy, `RecipeBase` craft, upgrade/dismantle. |

**3D / AI asset pipeline**
| Skill | Use when |
|---|---|
| `ai-3d-to-dayz` | Index/pointer skill for taking **AI-generated 3D** (Hunyuan, Tripo, TRELLIS) into DayZ: geometry-first, normal-bake into `_nohq`, and why AI-retopo output needs a manifold cleanup pass. |

**Process, QA & tooling** (domain-agnostic — use them across all of the above)
| Skill | Use when |
|---|---|
| `dayz-feature-spec` | **Before coding a non-trivial feature.** Writes a lightweight spec with measurable success criteria and Given/When/Then acceptance scenarios (incl. in-game repro), plus a **Forward Contract** — every classname / `model.cfg` selection / `.p3d` proxy / stringtable key the next phase will consume — and a read-only cross-artifact consistency gate. Adapted from github/spec-kit. |
| `dayz-mod-workflow` *(not included — see §4)* | The implement/debug protocol these skills assume you follow. |
| `dayz-pbo-reverse-engineering` | **Learning from another author's PBO**: Mikero ExtractPbo, source-vs-deployable classification, the sweep order (config.cpp → model.cfg → scripts → rvmats → p3d), and citation discipline so you don't confabulate what their code does. |
| `rigorous-data-audit` | **Before releasing data-critical code** (persistence, state machines, admin commands, async multi-tick queues) — anything where a bug means lost player progression. A multi-angle parallel audit + adversarial verification for invariant violations, races, path inconsistencies, and recovery-path defects. |
| `dayz-test-ingame` | **Building, deploying and launching a mod locally** with `DayZDiag_x64.exe` + filepatching (server+client on one box, or single-exe offline). Generates a parametrized test orchestrator. *Assumes a specific Windows/DayZ tooling layout — see §8.* |
| `dayz-mcp-verify` | **Auto-testing a mod in-game** by driving it with MCP tools (spawn a classname, orbit the camera, screenshot, raycast, read telemetry) and the drivable-car acceptance ladder. *Requires the author's custom `dayz-mcp` bridge, which is not public — included as methodology, see §8.* |

---

## 4. Dependencies NOT included (install these separately)

Several skills above **delegate generic steps** to a set of first-party DayZ skills published by
Anthropic as the **`anthropic-skills` plugin** for Claude Code. Those are not the author's to
redistribute, so they are not copied here — but the pack assumes they exist, and the single most
important one (`enforce-script-reference`) is referenced constantly.

Install the `anthropic-skills` plugin from the Claude Code plugin marketplace (run `/plugin` in
an interactive Claude Code session and add the Anthropic marketplace). The relevant skills:

| Skill | Role |
|---|---|
| **`enforce-script-reference`** | **The** Enforce Script reference — memory (`ref`/`autoptr`/Managed/GC), networking (ScriptRPC, SyncVars, `OnStoreSave/Load`), timers (the `CallLater` 4.5 h bug), type system, config.cpp, the action system, side checks. Load it for *any* Enforce Script or config work. |
| `dayz-mod-workflow` | Implementation & debugging protocol (client/server mapping, anti-confabulation, top-down debug hierarchy). |
| `dayz-model-pipeline` | Blender-headless → `.p3d` assembly, LODs, memory points, procedural textures, `model.cfg`, PBO. |
| `dayz-texture-pipeline` | `.paa` / `.rvmat` / native PBR materials, the `_co/_nohq/_smdi/_as` map suffixes. |
| `dayz-p3d-audit`, `dayz-p3d-debinarizer`, `dayz-p3d-inspector` | Collision/action/path audit; ODOL→MLOD de-binarize; model inspection. |
| `dayz-particles`, `dayz-sound-system`, `dayz-ui-development`, `dayz-doors` | Particles, sound, UI/layouts, door class. |
| `dayz-pbo-build`, `dayz-preflight`, `dayz-proxy-align`, `dayz-physics-engine`, `dayz-3d-viewer`, `dayz-animation-pipeline`, `mixamo-retarget`, `blender-assembly`, `blender-visual-review` | Packaging, preflight checks, proxy alignment, physics, viewing, animation, retarget, Blender assembly/review. |

If you see a cross-reference like *"delegates generic steps to `dayz-model-pipeline`"* inside an
included skill, that is one of these. Installing the plugin makes those references resolve.

---

## 5. 3D tooling

### `tools/py3d`

`tools/py3d/` is a **DayZ-specific fork of** [KoffeinFlummi/py3d](https://github.com/KoffeinFlummi/py3d)
(MIT) — a pure-Python reader/writer for the **MLOD `.p3d`** format (the editable, non-binarized
model format). Most asset scripts in these skills import it. Upstream is an unmaintained minimal
codec; this fork (`__version__ = "1.4.0"`, `IS_DAYZ_FORK = True`) adds anti-corruption guards so
the paths that used to silently corrupt a `.p3d` now fail *early* with an actionable message.

Highlights (see `tools/py3d/README.md` for the full list):
- `lod.new_selection(name)` — get-or-create a named selection that binds and registers correctly.
- `lod.set_memory_point(name, xyz)` / `lod.get_memory_points()` — idempotent memory-point upsert.
- `lod.faces_by_material()` / `faces_for_material(n)` — case-insensitive material match.
- `p3d.save(path, verify=True, backup_dir=...)` — atomic write with reopen+parse+invariant verify;
  on failure the original stays byte-intact.
- `p3d.validate()` → `list[Finding]` with codes (stale selection, weight range, normals budget…).
- Complete fail-closed proxy lifecycle: raw/engine frame conversion,
  `add_proxy`, strict enumeration, in-place align and index-safe remove.

**Install:** it targets Python 3. From the pack root:
```
pip install -e tools/py3d        # editable install
# then, in scripts, assert you got the fork (PyPI 'py3d' is a DIFFERENT library):
python -c "import py3d; assert getattr(py3d,'IS_DAYZ_FORK',False); print(py3d.__version__)"
```
Or just add `tools/py3d/` to `PYTHONPATH`. **License:** MIT — `tools/py3d/LICENSE` (© 2017 Felix
Wiegand, upstream author); keep that file with any redistribution.

### `tools/dayz-animation-formats`

Strict stdlib reader/writer for SEAnim v1 and DayZ RTM (`RTM_MDAT` and
`RTM_0101`) plus deterministic JSON inspection:

```text
python -m dayz_animation_formats inspect input.rtm --output anatomy.json
```

Frozen first-party fixtures are independently decoded by
Arma3ObjectBuilder during validation. BMTR and `.anm` conversion remain
explicitly out of scope; unsupported signatures fail closed.

### `tools/dayz-model-preflight`

Read-only MLOD gate driven by a versioned JSON contract. It composes
`py3d.validate()` with intended scale, required non-empty bone selections and
determinant-aware face-lineage/winding checks:

```text
python -m dayz_model_preflight check target.p3d \
  --contract preflight.json --json preflight-result.json
```

The DayZ py3d fork `>=1.4.0` is required. Missing or ambiguous one-to-one
lineage is `INVALID`; the tool never guesses a mapping or repairs a model.

### `tools/dayz-odol-strict`

Fail-closed, read-only ODOL v53-v55 anatomy inspection and deterministic diff:

```text
python -m dayz_odol_strict inspect input.p3d \
  --backend-root <external-backend> --json anatomy.json
python -m dayz_odol_strict diff reference.json candidate.json
```

The adapter, schemas and three user-authorized first-party fixtures are
redistributable. The compatible BisDLL-derived backend has no redistribution
license and is therefore external, hash-pinned and loaded only in an isolated
subprocess. No ODOL writer or partial-success mode is included.

---

## 6. Knowledge notes

`knowledge/` is verified reference material — facts to consult, but still **cite-then-verify**
against the vanilla source for your game version (the engine moves).

- **`DAYZ_TECHNICAL_NOTES.md`** — py3d MLOD reader facts, the canonical LOD resolutions
  (Geometry / Memory / LandContact / ViewGeometry / FireGeometry), winding handedness
  Blender→DayZ and the canonical fix, debris/selection centroids, single- vs double-sided faces,
  Container base requirements, magazine ammo, JSON schema migration, loot resolution cascade.
- **`DAYZ_INFRA.md`** — the environment: drive layout and the `P:\` work-drive convention,
  AddonBuilder / DayZDiag commands, `serverDZ.cfg` `allowFilePatching`, mission templates, texture
  suffixes, `.p3d` named properties, Central Economy file layout, BattlEye codes, RPT triage,
  terrain pipeline.
- **`vault-notes/`** — 16 topic notes, including: `dayz-animations-creatures-weapons`,
  `dayz-custom-infected`, `dayz-enforce-script-reference`, `dayz-mod-implementation-checklists`,
  `dayz-modded-class-server-stub-pattern`, `dayz-objectbuilder-lod-conventions`,
  `dayz-wiki-systems-reference`, `dayz-wrp-roadgraph-extraction`, `uv-mapping-dayz`, and
  cross-project syntheses for vehicles and weapon configs.

> The vault notes use Obsidian **`[[wikilink]]`** syntax. Some links point to the author's own
> process notes that are *not* included in this pack — treat those as contextual pointers; the
> substantive knowledge is inline. Links between notes that *are* here still resolve.

---

## 7. Working conventions that make AI-assisted DayZ modding reliable

These are the process rules — distilled from many painful cycles — that the skills enforce. They
are the real value; keep them even if you adapt everything else.

1. **Verify every API before you use it.** Grep the vanilla scripts (`P:\scripts\` → `1_core`,
   `3_game`, `4_world`) or a reference here, and cite `path:line`. Memory and semantic search are
   *hints*, not facts — open the file.
2. **Trace an invariant to every call-site.** When a change alters a system invariant (not just a
   local bug), grep *all* sites that assumed the old one and propagate the fix. The classic bug is
   "fixed it here, forgot the adjacent site."
3. **Walk it end-to-end before declaring it done.** Compiling ≠ correct. Mentally run the happy
   path, then kill the process between each I/O pair (crash recovery), then re-check admin/reset
   flows. For data-critical code, run `rigorous-data-audit`.
4. **Respect the client/server split.** Decide which side owns each value before coding; most
   "doesn't work" bugs are a read on the wrong side.
5. **Batch in-game tests.** A test cycle is minutes. Exhaust offline analysis (grep logs, simulate
   the fix in Python) and apply all pending fixes before asking for one rebuild; keep a plan B/C.
6. **Be honest about verification.** State *what* you verified, *how* (grep / checksum / repro /
   in-game), and what you did *not*. "It compiles" is not "it works." An error of exactly 0.000 in
   a test is suspicious (a tautology), not perfection.

---

## 8. Caveats & disclaimers

- **Example project names are illustrative.** The skills cite the author's real mods (e.g.
  `LFQuad`, `SUB_BRZ`/`BRZ`, `MercedesAMGLF`, `A6_SR2M`, `LF_VStorage`, `LFPowerGrid`,
  `KT-Roadkill`) as *where a given rule came from*. The rules are general; **the mod source is not
  included**. Treat the names as case-study labels.
- **Two skills assume the author's private infrastructure:**
  - `dayz-test-ingame` generates a Windows PowerShell orchestrator around a specific tooling layout
    (the `P:\` work-drive junction, AddonBuilder, a `<Mod>_dev\tools\` convention). The *ideas*
    transfer; the generated scripts will need to be re-pointed to your setup.
  - `dayz-mcp-verify` drives the game through a **custom `dayz-mcp` bridge to DayZDiag that is not
    public**. Without an equivalent bridge the MCP verbs won't run — read it as methodology
    (spawn → orbit → screenshot → raycast → telemetry → verdict), not a turnkey tool.
- **Placeholders.** Angle-bracket tokens like `<notes>`, `<research-notes>`, `<skills>`,
  `<claude-home>`, `<tmp>`, and `C:\Users\<you>\…` replace the author's private local paths. `P:\`
  is the standard DayZ work-drive convention, left as-is.
- **Provenance & integrity.** Releases are built from the versioned
  [`sources/source-map.json`](sources/source-map.json), scanned for secrets,
  identities and private paths, and checked for broken local links. Physical
  source and promotion roots stay in ignored local configuration.
- **Licensing.** Original pack material is MIT under [`LICENSE`](LICENSE).
  `tools/py3d` retains its own upstream MIT license. Research-only GPL,
  DPL-ND, proprietary and unknown-license material is not release payload; see
  [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
- **Moving target.** DayZ/Enfusion changes across versions. Dates and version-specific facts are
  noted where known; re-verify against your game build and consult the
  [`compatibility-matrix.md`](compatibility-matrix.md).

---

## 9. Updates and releases

Git is the canonical editable source. A release is created only after
`python -m packctl gate --root .` passes from a clean commit and two clean
builds produce the same SHA-256. The resulting payload is then promoted to
Obsidian and configured skill roots with hash readback; installed copies are
never edited as independent sources.

For a DayZ stable update, first pin the exact build and diff the relevant
vanilla contracts, then rerun offline validation and the smallest
representative in-game matrix. Record evidence and unknowns in
[`compatibility-matrix.md`](compatibility-matrix.md) and notable changes in
[`CHANGELOG.md`](CHANGELOG.md). Contribution and privacy requirements are in
[`CONTRIBUTING.md`](CONTRIBUTING.md).

---

## 10. A worked first move (for the assistant)

> **User:** "Help me make this ripped car drivable in DayZ."
>
> 1. `rip-vehicle-import` if it's a racing-game rip (import pipeline), else `dayz-vehicles` (authoring).
> 2. `enforce-script-reference` (install per §4) for any Enforce Script / config work.
> 3. `dayz-feature-spec` first if it's non-trivial — lock the Forward Contract (classnames,
>    `model.cfg` selections, wheel names) before coding.
> 4. `dayz-test-ingame` to build/deploy/launch locally; verify in-game.
> 5. `dayz-mcp-verify` (or manual) to confirm spawn → get-in → drive → correct wheel sense.
>
> Throughout: verify every class/field against vanilla (`P:\scripts\`), respect the client/server
> split, and batch your in-game tests.

Happy modding.

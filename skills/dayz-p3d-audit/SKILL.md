---
name: dayz-p3d-audit
description: >
  Audit and fix DayZ .p3d model files for collision, action targeting, physics, animation,
  path, and structural issues. Runs py3d-based validation against known-working reference
  patterns. Also validates config.cpp and .rvmat files for path and property issues.
  Use this skill whenever: a DayZ mod object has no collision, actions don't appear,
  the player walks through placed objects, CCTObject raycasts miss, Geometry LOD seems
  ignored, a model was exported from Blender and doesn't work in-game, textures are
  missing, animations don't play, or the user says "review the p3d", "check the model",
  "audit collision", "why no actions", "flag/object has no collision", "audit the mod",
  "check paths", "validate the model". Also trigger when debugging any placed
  Inventory_Base item. This is the GO-TO skill for P3D and mod structure debugging.
---

# DayZ P3D Audit — Complete Model & Mod Validator

Validates .p3d model files, config.cpp, model.cfg, and .rvmat materials against
DayZ engine requirements. Built from production debugging where models rendered
correctly but had zero collision, missing animations, or broken textures.

## Preflight gate

Per the L2 rule (`_shared/dayz-conventions.md`), every DayZ skill that does work gates on `/dayz-preflight` first. The audit reads `.p3d` files which can live anywhere, but the moment you point it at `P:\` paths or a built mod, an unmounted P-drive silently produces wrong results. Run `/dayz-preflight` before this skill.

## The three py3d gates cannot go red for geometry (SP-227-py3d-gates-cannot-go-red)

A clean `validate()`, a passing `save(verify=True)`, or a `diff` that reports equal is not evidence that the geometry is correct. Those checks only prove internal count consistency. When declaring a model verified, say whether vertex order was compared against debinarized vanilla or whether it was tested in-game.

1. `validate()` does not detect GLOBAL winding inversion. The winding check is relative to the Visual LOD. If every LOD is inverted (Blender Z-up to Y-up; this skill, PART 5 item 1), `validate()` returns an empty list and exit 0. If only Visual is inverted, it accuses healthy collision LODs (`ERR_WINDING_INVERTED`), and the message of the pinned `py3d_dayz-1.8.0` tells you to run `face.vertices.reverse()` on every face of each one (it warns against a `vertices[1]`/`[2]` swap, which turns a quad into a crossed face); following that instruction still breaks them. [OFFLINE MEASURED 2026-10-02] On `build_multilod_v2_p3d` (py3d tests) after `blender_to_dayz()`, with the Visual LOD turned inside-out, faces and normals together, the finding named the three healthy collision LODs; following it wound all 6 faces of each box outward and traded the finding for `ERR_WINDING_VS_NORMALS` on each, and negating their normals as well left `validate()` empty with every LOD wound outward: the silent-broken state. Read the finding as "Absolute winding check" rule 6 says. *(Corrected 2026-10-02: this item said it "suggests swapping vertices on every face; following that instruction reaches the silent-broken state". The 1.8.0 message names `face.vertices.reverse()` and warns against the swap; on a healthy collision LOD that still breaks the LOD, and `validate()` goes quiet only once the LOD's normals are negated too.)*
2. `save(verify=True)`: _verify_against does not compare geometry. It looks at counts, selection names and mass sum. Points `(0,0,0)` vs `(99,99,99)` still verify OK.
3. `python -m py3d diff`: py3d diff total: 0 does not prove geometric equality. The same pair reports `total: 0`, exit 0.

[DESIGN] Discriminating signal on a vanilla-scale LOD set: edge coherence (neighbors traverse the shared edge in opposite directions) and `cross(e1,e2) . declared_normal` in the same space.

Update 2026-09-07 (corrected the same day by the engine): the fork (1.7.0) ships that absolute signal as `_check_winding_absolute` → `ERR_WINDING_VS_NORMALS`. Calibrated against shipped MLOD it reads 100 % on production models and 0 % on two Blender exports whose STORED NORMALS were inverted, so **0 % means winding and normals disagree, not that the winding is wrong**: the build that reversed every face on that reading rendered both models inside-out in DayZDiag. Item 1 above describes the relative check only. See "Absolute winding check: what 0 % means" under WINDING DIAGNOSTICS for the direction test (signed volume against production) and the fix rule.


## SP-221 — sibling-model frame parity (before copying rotation offsets)

Two `.p3d` of the SAME family can differ 90° in authorship frame. Before copying
rotation offsets from one kit to another, verify frame parity. Compare Memory LOD
(res `1e15`) selections point-to-point between the two models. If the coordinates
correspond by an **axis permutation** — measured here `(x, y, z) → (x, -z, y)` —
the models do NOT share a frame and their config rotation offsets are **not
interchangeable**. The discriminator of "which way it mounts" is the **thin axis
of the Geometry LOD** (`1e13`): that axis must sit perpendicular to the mounting
surface, and pitch comes from there, not from the family or the model name.
**The visual LOD bbox is NOT a signal** — measured counterexample in the same
session: `gate_and.p3d` (Y≈2, Z≈1.16, pitch 90) and `switch_v2.p3d` (Y=1, Z≈2,
pitch 90) have opposite long axes and the SAME pitch. Corollary: "the two kits
are identical except this override" is a hypothesis about CONFIG; measure the
model before acting on it.

Source: 2026-08-10 LFPowerGrid (placement-batch reorientation). `switch_v2.p3d`
vs `switch_v2_remote.p3d`, memory points: `switch_axis` (-0.0407, 0.0288, -0.1472)
→ (-0.0407, 0.1472, 0.0288); `ce_center` (0.0001, 0.0366, -0.1286) → (0.0001,
0.1286, 0.0366); `boundingbox_max` (0.1833, 0.1039, -0.3665) → (0.1833, 0.3665,
0.1039); Geometry LOD 0.293/0.0911/0.4185 → 0.293/0.4185/0.0911. Refutes finding
F1 of `LFPowerGrid_dev\reviews\2026-08-07-placement-audit-grok.md` — applying the
"forgotten" pitch would have PRODUCED the symptom it was meant to cure. MLOD
parser used (memory points + extents per LOD, PowerShell, without py3d) is
reusable. See also `dayz-model-pipeline`.

## Quick Start

```bash
# Single model(s)
python <skill-path>/scripts/audit_p3d.py path/to/model.p3d [more.p3d ...]

# With config.cpp — REQUIRED for the SP-017 wheel-slot wiring check (see below)
python <skill-path>/scripts/audit_p3d.py model.p3d --config path/to/config.cpp

# model.cfg / .rvmat path checks
python <skill-path>/scripts/audit_p3d.py model.p3d --model-cfg path/to/model.cfg
python <skill-path>/scripts/audit_p3d.py model.p3d --rvmat a.rvmat b.rvmat

# Whole-mod scan (recursive; auto-uses the first config.cpp found for SP-017)
python <skill-path>/scripts/audit_p3d.py --scan-dir path/to/mod/
```

Without `--config` (or a `--scan-dir` that finds a config.cpp), the SP-017 check does NOT
run: the audit cannot verify the wheel-slot selection wiring, so a wheeled-vehicle body can
print "ALL PASSED" while its wheels will never simulate. Always pass `--config` when
auditing a vehicle body.

For full mod audit including config and materials, also check sections below manually.

## SP-017 — wheel-slot selection wiring (the silent wheel-sim gate)

The engine resolves the wheel slot→model binding via the selection named by
`config.cpp > CfgSlots > <Slot>.selection`. That selection MUST exist in the body's
**FireGeometry LOD** and contain the wheel-proxy faces. If it exists only in visual LODs,
the slot binds as inventory but the wheel never simulates: `WheelCountPresent()=0` while
`WheelCount()=N`, with NO RPT error — chassis bounces/sinks, wheels mount as items but do
not rotate, RPM climbs while speedo stays ≈0. Fix Y (confirmed in-game on LFQuad,
wheelPresent 0→4): alias the wheel-proxy face ALSO into a selection with the exact name
`CfgSlots.selection` expects — additive, preserving the original selection. Automated:
`check_wheel_slot_firegeo` in `scripts/audit_p3d.py` (runs only with `--config` or a
`--scan-dir` that finds a config.cpp). Source: Bohemia wiki `DayZ:Vehicle_Configuration`.

## Sibling skills

| Input / need | Delegate to |
|---|---|
| ODOL / binarized `.p3d` (audit_p3d.py rejects ODOL — MLOD signature required) | external ODOL→MLOD converter FIRST, then audit the MLOD output |
| Visual inspection / interactive editing of a `.p3d` | `dayz-p3d-inspector` |
| Aligning / orienting proxies | `dayz-proxy-align` |
| Assembling or generating models | `dayz-model-pipeline` |

---

## PART 1: The 13 Silent P3D Killers

These produce ZERO engine errors but break functionality completely. Full body of
each killer (root cause, detection snippet, fix, caveats) →
`references/killers-detail.md`. Index:

1. **Collision LOD Wound Opposite to the Visual LOD** (CRITICAL once confirmed — most common
   from Blender) — a collision component whose cross product points OUTWARD lets raycasts
   through; a correct MLOD winds it INWARD and stores its normals INWARD too
   (`dayz-model-pipeline` Rules 12 and 18). `audit_p3d.py` gets `ERR_WINDING_INVERTED` from py3d
   `P3D.validate()`: a RELATIVE check of each whole collision LOD against the Visual LOD, so a
   trigger, not the verdict. Confirm with Rule 18's per-component check (every face of every
   closed, convex component inward; faces outside any component leave it unresolved), then
   `face.vertices.reverse()` on the faces that read outward — never a `vertices[1]`/`[2]` swap
   (a quad becomes a crossed face), never to match the Visual LOD ("Absolute winding check",
   rule 7). MANDATORY re-run whenever you generate/edit a collision LOD. *(Corrected 2026-10-02:
   titled "Inverted Face Winding", this entry read "Geometry LOD normals point INWARD; raycasts
   pass through" and fixed it with "swap `vertices[1]`/`[2]` per inverted face".)*
2. **No `ComponentNN` Selection in the Collision LODs** (CRITICAL) — measured on a box whose
   Geometry, View and Fire LODs all lacked a `ComponentNN` selection: no ray hit in `geom`, `view`
   or `fire`, no physics-ray hit, the player walked through, and no log line said so. A selection
   missing from only some collision LODs was not measured. `component01` behaved exactly like
   `Component01` (rays, physics ray, walk; unbinarized and binarized, and binarize writes both as
   `component01`), so do not rename it to repair collision; other spellings were not measured
   (`references/killers-detail.md` §2). Fix: select each closed, convex part as its own
   `ComponentNN`, the components together covering the LOD (killer #8). py3d 1.9.0 raises
   `ERR_COMPONENT_NAMING` on each Geometry, View or Fire LOD with faces and no selection named
   `component…` in any case, and only `WARN_COMPONENT_NAMING` when the names are all irregular
   (`Component_01`); up to 1.8.0 (the pinned wheel) it checked the Geometry LOD alone and was a
   false positive on `component01`. *(Corrected 2026-10-02: titled "Component Selection Case
   Sensitivity", this entry read "Geometry component MUST be `Component01` (uppercase C); any
   variation silently loses ALL collision.")*
3. **Missing `autocenter=0` LOD Property** (CRITICAL for Inventory_Base) — items with
   `autocenter=0` in config need it ALSO as a named property on every collision LOD,
   else collision is displaced.
4. **Missing Memory LOD or Geometry LOD** (CRITICAL) — no Memory (~1e15) → no
   animation/bounding (maybe crash); no Geometry (~1e13) → zero collision. Canon LODs:
   Geometry 1e13, Memory 1e15, LandContact 2e15, ViewGeo 6e15, FireGeo 7e15.
5. **Missing `pos center` Memory Point** — without it the engine mis-derives bounding
   center for tall/asymmetric objects, breaking the action-targeting pre-filter.
6. **Missing Animation Selections & Axes** — model.cfg anim needs a Visual-LOD selection
   + a 2-point Memory axis. Caveat: on vehicles the axis↔selection binding lives in
   `model.cfg`, so the NAME heuristic false-positives on a valid decoupled rig (LL-027).
7. **Missing `box_placing_min` / `box_placing_max` Memory Points** — hologram placement
   fallback; fires only for items without a proper Geometry LOD / broken `GetCollisionBox()`.
8. **Incomplete Component Coverage** — every vertex and face of a collision LOD must belong to
   a `ComponentNN` selection with weight=1, one component per closed, convex part, the components
   together covering the LOD, or collision is partial. Never merge separate parts into one
   `Component01` to make it cover everything: that component is no longer convex. py3d
   `WARN_COMPONENT_COVERAGE` counts `Component01` alone and fires on a healthy multi-component LOD
   (`references/killers-detail.md` §8). *(Corrected 2026-10-02: titled "Incomplete Component01
   Coverage", this entry read "`Component01` must include ALL verts AND faces with weight=1, or
   collision is partial.")*
9. **Non-Watertight Collision Mesh** — open Geometry mesh (boundary edges/holes) →
   raycasts pass through gaps.
10. **Missing Surface/Material Assignment on Collision LODs** (CRITICAL) — every collision
    face needs a penetration `.rvmat`→`.bisurf` material, else bullets pass / no footstep /
    action cursor may miss. Persists through binarization.
11. **Wheel Proxy `.p3d` Memory LOD has only `ce_center`** (CRITICAL for wheeled vehicles) —
    vanilla ships 5 mem-points (`ce_center`, `ce_radius`, `boundingbox_min/max`, `invview`);
    missing them → `contact=0` every frame, bounce, speedo diverges to ±inf.
12. **Wheel-vertical-placement** (CRITICAL for wheeled vehicles) — tire bottom below model
    origin / chassis floor below wheel-center line → belly too low, `contact=0` at rest.
    Fix raises wheels AND chassis floor together (ride-height triple).
13. **Vehicle Geometry built as ONE monolithic component** (CRITICAL for wheeled vehicles) —
    a working car's Geometry LOD is many closed convex components each with mass +
    `autocenter=0`; a monolith → low inertia. NOTE the confirmed spawn-launch root cause was
    a spurious `#Mass#` on a non-Geometry LOD (see "Vehicle satellite checks"), NOT the
    monolith — keep multi-component as best-practice, diagnose mass first.

## PART 2: Config.cpp Validation

### Baked-in P:\ Drive Paths (CRITICAL)

Absolute paths like `P:\DZ\gear\consumables\data\rag_co.paa` only exist on the
developer's machine. These MUST be converted to game-relative paths:

```cpp
// WRONG — breaks on any other machine:
hiddenSelectionsTextures[] = {"P:\DZ\gear\consumables\data\rag_co.paa"};

// CORRECT — works everywhere:
hiddenSelectionsTextures[] = {"DZ\gear\consumables\data\rag_co.paa"};
```

**Where to check**: `hiddenSelectionsTextures[]`, `hiddenSelectionsMaterials[]`,
and any texture/material path in config.cpp.

**Exception**: Paths starting with `P:\` are valid ONLY during development on a
workbench with P: drive mounted. They must be stripped for distribution/PBO packing.

### Required Properties for Placed Objects

```cpp
class MyPlacedObject: Inventory_Base
{
    autocenter = 0;        // MANDATORY — prevents visual mesh burial
    model = "\ModName\data\model.p3d";  // Backslash prefix = addon root
    // For kits (handheld items): do NOT set autocenter=0
};
```

### AnimationSources Must Match model.cfg

If model.cfg defines animation `flag_mast` with `source = "flag_mast"`, config.cpp
MUST have a matching AnimationSources entry:

```cpp
class AnimationSources
{
    class flag_mast
    {
        source = "user";    // "user" = script-controlled
        animPeriod = 0.5;
        initPhase = 1;      // 0=up, 1=down for vanilla flag convention
    };
};
```

### hiddenSelections Must Match P3D

Every entry in `hiddenSelections[]` MUST have a matching named selection in the
Visual LOD of the P3D. Missing selections silently fail (no texture swap occurs).

---

## PART 3: Material (.rvmat) Validation

### P:\ Drive Paths in .rvmat Files

Same rule as config.cpp — `P:\` paths break on distribution:

```
// WRONG:
texture="P:\dz\gear\camping\data\flag_generic_nohq.paa";

// CORRECT (vanilla reference):
texture="dz\gear\camping\data\flag_generic_nohq.paa";
```

### Required Texture Stages

Standard DayZ .rvmat needs at minimum:
- Stage 0: Diffuse color texture (`_co.paa`)
- Stage 1: Normal map (`_nohq.paa`)
- Stage 2: Specular/detail map (`_smdi.paa`)

Missing stages produce engine warnings but don't crash.

---

## PART 4: Diagnostic Decision Tree

```
1. Can you SEE the object in-game?
   NO  → Check model path in config.cpp (backslash prefix, case)
   YES ↓

2. Is the object buried/floating?
   BURIED → Missing autocenter=0 in config.cpp AND/OR LOD property
   FLOATING → autocenter=0 on a kit class (only placed objects need it)
   CORRECT ↓

3. Does floating text (item name) appear near it?
   NO  → Entity not spawned. Check CreateObjectEx, server logs
   YES ↓

4. Do debug Print() in ActionCondition appear in script log?
   YES → ActionCondition rejecting. Read prints to find which check fails
   NO  ↓ (P3D Geometry LOD issue — engine can't raycast)

5. Run audit_p3d.py and check:
   a. Collision cross product INWARD on every face of every component (killer #1, Rule 18)?
                                 → If a face reads OUTWARD: face.vertices.reverse() on that face
                                   only (proxy:* faces excluded; prerequisites and unresolved
                                   cases: killer #1), never a verts[1]/verts[2] swap (a quad
                                   crosses); for the normals, see the Check A table in
                                   references/winding-diagnostics.md.
                                   (Corrected 2026-10-02: this line asked for OUTWARD winding and
                                   swapped verts[1]/verts[2] when inward. Aligned the same day
                                   with killer #1: it asked "Collision cross product INWARD per
                                   component" and reversed "the faces of that component only",
                                   which turns the healthy faces of a mostly-outward component
                                   outward.)
   b. Collision faces in a ComponentNN selection (killer #2)?
                                 → If none: select each closed, convex part as ComponentNN.
                                   component01 works like Component01: do not rename it to
                                   repair collision.
                                   (Corrected 2026-10-02: this line read "Component01 uppercase
                                   C?   → If wrong case: rename"; in game component01 collided
                                   exactly like Component01.)
   c. autocenter=0 LOD property? → If missing: add
   d. pos center in Memory?      → If missing: add at (0,0,0)
   e. Components cover every collision face (killer #8)?
                                 → If not: give each uncovered closed, convex part its own
                                   ComponentNN; never merge parts into one component.
                                   (Corrected 2026-10-02: this line read "Component01 covers
                                   all?    → If partial: extend selection", which merges separate
                                   parts into one non-convex component.)
   f. Mesh watertight?           → If open: close gaps
   g. Geometry LOD exists?       → If missing: create one

6. Animations not playing?
   → Check flag_mast selection in Visual LOD
   → Check flag_mast_axis (2 points) in Memory LOD
   → Check AnimationSources in config.cpp matches model.cfg

7. Textures missing/white?
   → Check P:\ paths in config.cpp hiddenSelectionsTextures
   → Check P:\ paths in .rvmat files
   → Verify .paa files exist at referenced paths
```

---

## PART 5: Common Blender Export Pitfalls

1. **Collision and Visual LODs can reach the MLOD wound differently** — Rule 12's map treats
   every LOD alike, but collision built in code, exported with another map or reversed on its
   own does not follow the Visual LOD: check each collision LOD per component (killer #1,
   Rule 18), independently from the Visual LOD. *(Corrected 2026-10-02: this item read "Z-up →
   Y-up flips collision winding but not visual — always verify Geometry LOD normals
   independently from Visual LOD".)*
2. **Blender Geometry LOD may inherit `class=house`** from Object Builder templates
3. **py3d read-write cycles** preserve validity but change file size (~800 bytes per
   property change). This is normal.
4. **Addon Builder binarizes MLOD → ODOL** — mesh defects persist into builds, but the
   winding/cull SIGN does not: on the measured path it inverts in every pair. Audit the
   published ODOL with a predicate calibrated on ODOL, never one ported from the MLOD
   (LL-273, "MLOD to ODOL is a winding-sign boundary", below)
5. **`component01` collides like `Component01`** — the MLOD keeps the name as written and py3d
   looks selections up by exact name (its component check ignores the case from 1.9.0), but in
   game `component01` behaved exactly like `Component01`, and
   binarize writes `Component01` as `component01` (killer #2). Other spellings, other selections
   and names that differ only by case inside one model were not measured. *(Corrected 2026-10-02: this item read "**Named selections are
   case-sensitive** in MLOD format. `Component01` ≠ `component01`".)*
6. **Memory LOD must have zero faces** — only single-vertex points. Faces in Memory LOD
   may confuse the engine.
7. **Animation axis points must be in the SAME named selection** — both points of
   `flag_mast_axis` must be in one selection, not split across two.

---

## PART 6: Script-Side Gotchas

These aren't P3D issues but commonly co-occur during debugging:

- `IsTakeable()` MUST return `true` for `ActionManagerClient` to include the entity
  in the action targeting pipeline. Use `CanPutInCargo()=false` +
  `CanPutIntoHands()=false` + `RemoveAction(ActionTakeItem)` for non-pickup items.
- `SetFullyRaised()` in group creation → flags start at progress=1.0 → only
  `LowerFlag` appears initially, not `RaiseFlag` (checks `< 1.0`).
- SyncVar timing vs RPC cache timing can deadlock ActionConditions.
- `autocenter=0` on FlagKit (handheld) causes it to float when dropped — only set
  on placed objects, not kits.

---



---

## WINDING DIAGNOSTICS — Deep Methodology

Deep winding validation methodology (how NOT to verify — centroid/right-handed heuristics
that false-positive on DayZ left-handed models; Check A winding-vs-averaged-normal, Check B
edge-pair topology, Check C vs-vanilla; minority-group isolation per welded component, then
the group's vertex order flipped with its stored normals read by Check A first — negated in
the same pass only where they turned along with the winding (unless the pipeline recalculates
them afterwards), kept where the winding alone was reversed — and a corner-by-corner check of
the whole LOD to close; full-sphere back-dominance battery
for inverted faces with NO topological minority, judging residue in visible pixels, never face
counts; known lessons learned incl. `flip_winding.py`
idempotency and Crate_Wooden mixed winding tolerated in render) →
`references/winding-diagnostics.md`. Complements killer #1. *(Corrected 2026-10-02: this line
read "the coupled fix — flip vertex order AND negate the stored normals unless the pipeline
recalculates them afterwards", which turns right normals wrong on a group whose winding alone
was reversed: `references/winding-diagnostics.md`, "From Check B to fix", item 3.)*

### MLOD to ODOL is a winding-sign boundary (LL-273)

The measured SUB_BRZ path paired source MLOD and published ODOL triangles by centroid and found opposite orientation in 12,784 of 12,784 pairs. For that Binarize path, a cull/winding predicate calibrated on MLOD must invert its sign when auditing the published ODOL; for a different toolchain or build, recalibrate the boundary instead of assuming the sign.

Qualify the release gate with a known MLOD/ODOL pair and prove it separates a healthy build from an intentionally broken one. An identical zero count across materially different inputs is evidence of an instrument failure, not a clean artifact — measured `0 of 2367` on three distinct builds; with the sign inverted, ODOL and MLOD agreed cell by cell (637 → 0 and 636 → 0). Verify the published ODOL, but never port the MLOD predicate by memory.

### Locating seat-visible see-through: render from the REAL first-person camera (added 2026-09-18, SUB_BRZ s96)

A defect the player reports from the seat must be reproduced from the real first-person camera, not an estimated eye: an eye 23 cm below and behind the real one showed neither windshield-base patch. [EXACT] Recover the camera from the user's own screenshot by PnP over known-position dashboard features (measured reprojection error 2.7 px), then z-buffer-render the LOD flagging every pixel whose nearest opaque face is a backface; the seal is measured, not estimated (2,203 inverted twins added, 0 see-through pixels afterwards). [DESIGN] Show the before/after to the user BEFORE touching geometry. Seal culprits with inverted twins — same points, reversed vertex order and UVs, negated normals — never by flipping; exclude twin candidates that coincide with another piece (< 2 mm) or they will flicker. Winding-vs-hole still goes through the battery above and `dayz-model-pipeline` SP-166.

### Absolute winding check: what 0 % means (added 2026-09-07, corrected the same day with the engine verdict)

py3d fork 1.7.0 implements the absolute signal: `_pct_normal_agreement(lod)` = % of faces with `dot(cross(v1−v0, v2−v0), declared_normal_v0) > 0`, both vectors in raw MLOD space; `_check_winding_absolute` raises `ERR_WINDING_VS_NORMALS` (CRITICAL) near 0 % and `WARN_WINDING_NORMAL_MISMATCH` when mixed. Calibration measured 2026-09-07 with that same function on the visual LOD:

| MLOD | Status | Agreement |
|---|---|---|
| `P:\LFPowerGrid\data\solarpanel\lf_solarpanel.p3d` (2,944 faces) | in production, seen in game | 100.0 % |
| `P:\LFPowerGrid\data\kits\lf_kit_box.p3d` (12 faces) | in production | 100.0 % |
| SUB_BRZ co-driver door MLOD (double-sided glass twins with negated normals) | verified in game | 26 % |
| LFSecure door export (third-party Blender, 11 LODs) | engine verdict 2026-09-07: normals inverted, winding correct | 0 % in every visual and collision LOD |
| LFSecure room export (third-party Blender, 12 LODs) | engine verdict 2026-09-07: normals inverted, winding correct | 0 % in every visual and collision LOD |

Engine verdict (LFSecure I-0, DayZDiag 1.29, 2026-09-07 21:20): the build that followed the first version of this section (`face.vertices.reverse()` on every face of every LOD) rendered BOTH exports inside-out (textures visible only from inside the object; the room's Roadway faces flipped too), and `RaycastRVProxy` (view, fire and geom) from 2 m in front of the door returned no hit while a terrain control hit. The 0 % came from the exports' STORED NORMALS, not from their winding: a second instrument that ignores normals (signed volume by winding of the visual LOD0, divergence sum over fan triangles in raw MLOD space) reads −0.1145 on `lf_kit_box`, −0.0691 on `lf_solarpanel`, −0.1967 on the door export (same sign as production) and +25.19 on the room export (a room seen from inside: faces toward the interior); the reversed builds carried the opposite signs.

Reading rules, corrected:

1. Healthy single-sided MLOD reads ≈ 100 %. **0 % means winding and stored normals DISAGREE; it does not say which side is wrong.** Never derive the fix direction from this number alone. The relative check (item 1 of "The three py3d gates") cannot see a global disagreement; this one can.
2. A **mixed** percentage on a double-sided model is the twins voting, not an inversion: isolate the minority group per welded component (`references/winding-diagnostics.md`) instead of flipping everything. *(Measured 2026-10-02 with Check A on the SUB_BRZ door of the table: there the twins do not explain the mix — coincident twins are 144 of 11,921 faces, and the census without them is unchanged (72.7 % flipped, 25.9 % agreeing). The vote splits by part — exterior paint, black trim and mirror against their normals, cabin trim and glass with them — and no face group is inverted: Check B finds one stray edge, and with it cut every welded component orients as one group. See Check A, `MIXED`, in `references/winding-diagnostics.md`.)*
3. Measure in **raw MLOD coordinates**. A frame that already flips Z (an OBJ export, `parse_obj` helpers) inverts the sign; one session concluded "healthy = cross opposite normal" from such a frame and doubted a true CRITICAL for a round.
4. Decide the direction with the **signed volume by winding**, calibrated on shipped MLOD: a solid seen from outside reads NEGATIVE on production models (a convex box also winds 0 % of its faces "outward" from its centroid); a room meant to be seen from inside reads POSITIVE; Roadway faces walkable from above read `cross_Y < 0` (same side as the kit box's top face). Export sign equal to production → the winding is right and the normals are wrong.
5. Fix the side that is wrong. Normals wrong → keep the winding and negate the normal pool in place (`lod.facenormals[j] = (-x, -y, -z)`; never through the `Vertex.normal` setter, which re-indexes into the pool); the audit then reads ≈ 100 % with every face order identical to the source. Winding wrong (sign opposite to production) → `face.vertices.reverse()` on every face of every LOD, never a `vertices[1]`/`[2]` swap (a quad becomes a crossed face). Either way confirm in the engine (outside render, inside render, raycast, walk the Roadway) BEFORE promoting the rule: the first version of this section was promoted before that check and cost one build. Engine confirmation of the negate-normals build on the LFSecure pair: PASS, 2026-09-07 22:13, DayZDiag 1.29, I-0 with the L4 PBO (door and room render right side out from outside and from inside; `RaycastRVProxy` view/fire hit the door from the front and the back and the room wall from both sides, while the face-reversed L3 build missed every ray; `P:\LFSecure_dev\evidence\i0\i0_result.json`).
6. `ERR_WINDING_INVERTED` does not come from this check. py3d raises it in `_check_winding_vs_visual`, the RELATIVE check (item 1 of "The three py3d gates"), which compares each collision LOD's share of faces whose cross product points away from the centroid of the LOD's points with the Visual LOD's share; the absolute check of this section raises `ERR_WINDING_VS_NORMALS`. On the production `lf_kit_box.p3d` the absolute check stays silent (winding and stored normals agree on every face) and the relative check fires on the Geometry, View and Fire LODs: each holds one `Component01` of 12 triangles, all wound outward (signed volume +0.1145), against an inward Visual LOD (−0.1145). There the finding named LODs that Rule 18's per-component check also reads outward, and in game that collision registers no raycast. Measured 2026-10-02 on DayZDiag 1.29.163709, with the MLOD packed unbinarized as in the deployed PBO: 0 of 27 `scene_raycast` rays hit it (nine per mode in `geom`, `view` and `fire`: from above, from the four sides at mid-height, from one side at two other heights, and two from inside), and a ray built like the cursor ray of vanilla `ActionTargets` (`RaycastRVProxy`, `ObjIntersectView`, as a 0.05 m sphere: the dayz-mcp bridge replaces a requested radius of 0 with its 0.05 m default, and the vanilla ray has radius 0) passes through it to the ground; in the same run `gate_and.p3d` from the same PBO (six components, each wound inward) and a vanilla `WoodenCrate` (the kit's own `item_small` physics layer) took 21 of 21. (claim: CLAIM-P3D-KITBOX-OUTWARD-INGAME) Outward winding is the cause, measured in a paired run the same day (DayZDiag 1.29.163709, three classes with the kit's own config, MLODs packed unbinarized): with only the collision LODs changed, `face.vertices.reverse()` on all 12 faces of each and the Visual and Memory LODs byte-identical, the kit took 27 of 27 rays of the same nine-per-mode battery, whether its collision normals were negated with the winding (the Check A table's "agree / toward the visible side" row) or kept as shipped, and the cursor-like ray stopped on its top; the shipped bytes took 0 of 27 again and a vanilla `WoodenCrate` 27 of 27. (claim: CLAIM-P3D-KITBOX-PAIRED-INGAME) The two fixed variants answered every ray at the same coordinates relative to the kit, so a collision LOD's stored normals do not change these rays, and binarize writes the two to the same ODOL (claim: CLAIM-P3D-BINARIZE-COLLISION-NORMALS); negate them anyway, for Rule 12 and a clean audit (with the shipped normals the absolute check raises `ERR_WINDING_VS_NORMALS` on the fixed LODs). The outward winding did not hide the kit from the server's physics world: `DayZPhysics.RayCastBullet` found the shipped kit's top, east and north faces where it found the fixed kits' (a static query; player contact, standing on the kit and client collision were not measured). The misses were measured on the bridge's `RaycastRVProxy` battery, a 0.05 m sphere taking the nearest contact. Vanilla rays in the same intersection modes are the reason to expect the defect in play, not tested here: the action cursor casts `RaycastRVProxy` with `ObjIntersectView` (`ActionTargets`), and hologram placement casts `RaycastRV` with `ObjIntersectFire` (`Hologram`), both at radius 0 and with their own flags and acceptance checks, and some of the hologram's rays are ground-only and skip every object whatever its winding. A walking player, who went through the 0.49 m `item_small` kit fixed or not, does not tell. Treat the kit box's collision as broken in the shipped model and keep its collision LODs out of any calibration of healthy winding. Read `ERR_WINDING_INVERTED` as a trigger for Rule 18's per-component check, which decides, and fix as killer #1 says (only the faces that read outward, never a whole LOD to match the Visual LOD): the finding also fires on healthy collision LODs under an inverted Visual LOD. *(Corrected 2026-10-02: this item read “`_check_winding_absolute` / `ERR_WINDING_INVERTED` in the fork flags the production `lf_kit_box.p3d`: the fork's absolute sign convention is inverted. Read that finding as "disagreement", never as a direction.” In py3d 1.8.0 `_check_winding_absolute` raises `ERR_WINDING_VS_NORMALS`, which does not fire on the kit box; the finding that fires is the relative one, and on the kit box it named the outward LODs.)* *(Measured 2026-10-02, paired run: this item read “That run did not change the kit's winding alone, so outward winding as the cause stays a hypothesis for this kit: the paired test behind Rule 12 supports it (the same binarized boxes, same points, took every ray with their faces wound inward in the MLOD and none wound outward, but that pair also turned the Visual LOD and every stored normal), and a fixed kit, player collision and bullets were not tested.” The paired run measured the fixed kit; a real bullet, a hologram and player collision are still not measured.)* *(Corrected 2026-10-02: the first run's cursor-like ray read “(`RaycastRVProxy`, `ObjIntersectView`, radius 0)”; radius 0 was requested, and the bridge cast its 0.05 m default, in that run and in the paired one.)*
7. Geometry / Fire / View LODs of shipped models carry mixed signs (kit box +, solar panel −; seven debinarized vanilla models and four LFPG models wind 0 % "outward per component", i.e. the same orientation as the Blender exports): do not "fix" collision LODs to match the visual LOD, keep the export's orientation. *(Measured in game 2026-10-02, rule 6: the kit box's + is its outward collision, which registers no raycast; it is no sign to keep. A collision LOD is still never matched to the visual LOD. Keep the export's orientation only where every face of a closed, convex component reads inward (killer #1, Rule 18); a component that reading cannot score (open, planar or double-sided) is unresolved, not a sign to keep.)*
8. **A sign that matches production does not rule out a MIRRORED export.** The LFSecure exports read 0 % with a production-like winding sign, and the negate-normals build rendered right side out — as a mirror image (door handle and bed on the opposite side to the vendor's own renders; textures read "as in a mirror"). A reflection of positions on export flips the winding, and an exporter that then reverses vertex order hides it behind a correct-looking sign. Before choosing the fix, compare ONE asymmetric feature (handle side, furniture layout, texture lettering) against the vendor's render; measured 2026-09-07, DayZDiag 1.29. Full fix for a mirrored export: reflect x on every point of every LOD (memory points included), reverse the vertex order of every face, and map the normal pool to (nx, -ny, -nz); the audit then reads 100 % with the production sign, collisions still hit (RV convex components follow the winding) and the asymmetric feature lands where the render puts it (LFSecure L7, `P:\LFSecure_dev\reviews\2026-09-07-r2-claude-scripts.md` §Espejo).

---

## Vehicle satellite checks (mass / wheel clearance / crew / vertex ceiling)

Vehicle-specific extensions of the killers, full detail →
`references/vehicle-killers.md`:

- **`#Mass#` must live only in the Geometry LOD** (2026-06-02) — a stray `#Mass#` tagg on a
  non-Geometry LOD makes binarize bake THAT LOD's mass → `CoM=(0,0,0)`, spawn below ground,
  PhysX ejection. MANUAL check (not automated in `audit_p3d.py`); set `point.mass = None`
  (not `0.0`) on non-Geometry LODs. This is the confirmed spawn-launch root cause behind
  killer #13.
- **Wheel-well clearance vs wheel RADIUS, not HUB** (SP-024) — measure chassis-to-wheel-center
  vs the effective wheel radius (cylinder), not the small hub box; `< radius` → PhysX
  self-penetration ejection.
- **Crew check (get-in / co-driver)** (2026-06-05) — Check A: `seat_driver`/`seat_codriver`
  must each live in their own ViewGeo component; Check B: crew proxies must be canonical
  (not 90/45/45 isosceles) or the player sits sideways.
- **Vertex-ceiling flag counts face-indices, not resolved vertices** — FALSE POSITIVE; the
  DX9 16-bit ceiling is on resolved unique vertices (point×normal×uv), not `faces×3`.
  Patched 2026-07-06 (`check_lod0_vertex_budget`).

---

## SP-051 — UV audit step (added 2026-07-06)

UV audit (beyond out-of-range): run
`<dayz-projects>\LFQuad_dev\tools\uv_audit.py`
(verified present 2026-07-06) — checks: zero-uv%, NaN, bounds vs ODOL int16 quantization
(range ≤ ~32 on 2048 tex — min/max over the WHOLE LOD), degenerate faces, mirrored islands
(signed UV area — breaks _nohq), Monte-Carlo overlap per group and cross-group, island count
(union-find) + texel density (px/m; healthy reference ≈ 292 px/m LFQuad wheels; 27 px/m =
measured cause of bake artifacts). Gotchas: whitelist `proxy:*` faces (degenerate by design),
exclude full-frame tris (UV area > 0.2) from cross-group overlap, classic raster misses
subpixel islands. Full symptom→fix catalog:
`<vault>\AI\20_Knowledge\uv-mapping-dayz.md`.


---

## Resolution LOD count -- performance check (added 2026-07-14)

WARN (performance, not a correctness killer): flag any model that ships with only ONE
resolution LOD. With a single LOD the engine loads the full mesh at any distance (no
distance-based decimation), inflating client/server load; it is a documented cause of
stutter and random disconnects when many such models are near the player. Vanilla
reference: the plate carrier ships ~5 resolution LODs.

- Heuristic: `resolution_LOD_count >= 2` for any non-trivial visible model; a genuinely
  low-poly prop (a few hundred faces) may legitimately keep one.
- Manual for now (not automated in `audit_p3d.py`): open in Object Builder / py3d and count
  Resolution LODs; or compare face counts across LODs (identical counts = the ladder is a
  copy, not a decimation -- see dayz-model-pipeline `lods-and-geometry.md`).
- Fix: author decimated LODs (user-gated per the dayz-model-pipeline decimation gate).

Source: community report (YouTube Oqz8-FNQypI, 2026) + BI LOD wiki recommendation of at
least one resolution LOD. Related BI cap: 30+ total LODs can crash the binarizer.

## Rules promoted from lessons corpus (added 2026-07-27)

Promoted from `AI/20_Knowledge/lessons-learned.md` to arrive via trigger instead
of depending on someone remembering to look them up. Each rule cites source `LL-NNN`;
complete entry lives there. Do not remove citation: the index detects promotion by it.

- **LL-068** — Audit convex decomposition and mass distribution separately: regrouping the same points does not change CoM or inertia. Do not turn CoM/Izz into hard gates if they stem from reconstructed uniform masses or are geometrically unachievable.
- **LL-092** — Build crew proxy as scalene triangle with unambiguous frame and calibrate +Y/+Z against referenced submodel. Place anchor vertex at actual seat height; do not copy vertices from another proxy type.
- **LL-364** — Before citing "vanilla equals N" for a field, ask THROUGH WHAT CHANNEL that N arrived. If material is distributed in derived format (ODOL) and the number was produced by a converter, the right question is not what it is worth but whether field survives conversion: `odol_to_mlod.py` writes bare `face.flags = 0`, so any "vanilla uses flags=N" measured there is the instrument answering itself. Measured 2026-08-24 via round-trip: `binarize.exe` DISCARDS MLOD per-face `flags` field — three MLODs differing only in it binarize to a byte-for-byte identical model, while two positive controls (point moved 1 cm, texture cleared on same faces) do change output. And a neighboring field in derived format carrying same bit (`Section.special`, per section) is NOT the same field.


## Vehicle get-in action contract gate (SP-086, added 2026-08-31)

For every vehicle that declares `class Crew`, run a `contract_gate` over the complete action
graph rather than checking each file independently:

- identify the Memory LOD by resolution near `1e15` and require `actionSel`, `proxyPos`,
  `getInPos`, and `getInDir` endpoints to resolve in the `.p3d`;
- close those names through model.cfg `sections[]` and `SkeletonBones[]`, then through the
  matching config.cpp `class Crew` fields;
- require each get-in position/direction pair to be within 1 m of its intended proxy;
- close config.cpp `AnimationSources` to model.cfg `Animations`.

Report every broken edge with both endpoint files and names. Keep `actionSel in sections[]`
as a calibration warning, not a hard failure, until it has passed a representative vanilla
vehicle control. A project-local gate passed one known-good artifact and rejected one known
bad artifact, but that single pair does not settle the membership rule.

## Resolve every face index (SP-142, added 2026-08-31)

Counts, selection names, proxy centroids, and material pairs live in a different space from
face indices. A freshly assembled or surgically edited `.p3d` must have a gate that
dereferences every face corner's `point_index` and `normal_index` against the live pools.
Fail on the first out-of-range value and name the LOD, face, corner, index, and pool length.
Do not treat matching cardinalities as an equivalent check.

Run `binarize` as the authoritative serialization check, with the previous known-good model
as a control in the same run. This separates a product failure from a broken test bench and
makes pre-existing log noise comparable. A binarize pass proves that this index/serialization
gate passed; it still does not replace the in-game spawn gate in SP-216.

### Trusting a FAIL from a new gate on a binarized ODOL: run the control piece first (added 2026-09-28, LFDucati T102b)

[DESIGN] Before trusting a FAIL from a new ODOL gate, run the gate on a piece that already works in game (here `drivewheel`): if the control also fails, the gate is wrong, not the model — two rebuild cycles stopped on a bad gate while the model was fine. [EXACT] In a binarized ODOL the named selections of the VISUAL LODs are stored as faces (also `drivewheel` and `damper_1`, which do move in game); read their vertices through the face corner indices. Memory and Geometry LOD selections list vertices. And write gate expressions against the tool's real output, not its vocabulary: the anatomy dump writes animation types as numbers (0 rotation, 4 translation), so an expression matching the string `rotation` never fires.

## SP-359 — The audit does not check the resolved-vertex budget

A `.p3d` can pass this entire audit with 0 CRITICAL and still be rejected by the engine when it
loads the MLOD with `Too many vertices`, which surfaces in-game as
`PHYSICS (E): Won't simulate, it has no geometry` even when the Geometry LOD is perfect.

Add to the audit: a count of `(point, normal, uv)` triples per LOD, and a warning past 90% of the
measured ceiling for that model.

The ceiling is per-model, not a constant — `RESOLVED_LIMIT = 65535` is a false friend. Measured
cliff on the HH-60G: 46.133 triples load, 46.134 do not (25 in-game verdicts, zero false).

The authoritative gate is `binarize.exe`, not this count, and it has three states: PASS /
CAPACITY_FAIL / OTHER_FAIL. CAPACITY_FAIL means do not go in-game to "fix" Geometry; OTHER_FAIL
means do not touch geometry at all. Evidence and the measured cliff: SP-122 in
`dayz-vehicles/SKILL.md` and `dayz-vehicles/references/binarize-vertex-budget.md`.

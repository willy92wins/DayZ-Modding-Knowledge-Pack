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
| ODOL / binarized `.p3d` (audit_p3d.py rejects ODOL — MLOD signature required) | `dayz-p3d-debinarizer` FIRST, then audit the MLOD output |
| Visual inspection / interactive editing of a `.p3d` | `dayz-p3d-inspector` |
| Aligning / orienting proxies | `dayz-proxy-align` |
| Assembling or generating models | `dayz-model-pipeline` |

---

## PART 1: The 13 Silent P3D Killers

These produce ZERO engine errors but break functionality completely. Full body of
each killer (root cause, detection snippet, fix, caveats) →
`references/killers-detail.md`. Index:

1. **Inverted Face Winding** (CRITICAL — most common from Blender) — Geometry LOD
   normals point INWARD; raycasts pass through. `audit_p3d.py` runs a RELATIVE
   winding check vs the Visual LOD. Fix: swap `vertices[1]`/`[2]` per inverted face.
   MANDATORY re-run whenever you generate/edit a collision LOD.
2. **Component Selection Case Sensitivity** (CRITICAL) — Geometry component MUST be
   `Component01` (uppercase C); any variation silently loses ALL collision.
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
8. **Incomplete Component01 Coverage** — `Component01` must include ALL verts AND faces
   with weight=1, or collision is partial.
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
   a. Face winding outward?      → If inward: swap verts[1]/verts[2]
   b. Component01 uppercase C?   → If wrong case: rename
   c. autocenter=0 LOD property? → If missing: add
   d. pos center in Memory?      → If missing: add at (0,0,0)
   e. Component01 covers all?    → If partial: extend selection
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

1. **Z-up → Y-up flips collision winding but not visual** — always verify Geometry LOD
   normals independently from Visual LOD
2. **Blender Geometry LOD may inherit `class=house`** from Object Builder templates
3. **py3d read-write cycles** preserve validity but change file size (~800 bytes per
   property change). This is normal.
4. **Addon Builder binarizes MLOD → ODOL** — all MLOD issues persist into builds
5. **Named selections are case-sensitive** in MLOD format. `Component01` ≠ `component01`
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
edge-pair topology, Check C vs-vanilla; known lessons learned incl. `flip_winding.py`
idempotency and Crate_Wooden mixed winding tolerated in render) →
`references/winding-diagnostics.md`. Complements killer #1.

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

## Reglas promovidas del corpus de lecciones (added 2026-07-27)

Promovidas desde `AI/20_Knowledge/lessons-learned.md` para que lleguen por trigger en vez
de depender de que alguien recuerde buscarlas. Cada regla cita su `LL-NNN` de origen;
la entrada completa vive allí. No quites la cita: el índice detecta la promoción por ella.

- **LL-068** — Audita por separado descomposición convexa y reparto de masa: reagrupar los mismos puntos no cambia CoM ni inercia. No conviertas CoM/Izz en gates duros si proceden de masas uniformes reconstruidas o son geométricamente inalcanzables.
- **LL-092** — Construye el crew proxy como triángulo escaleno con frame inequívoco y calibra +Y/+Z contra el submodelo referenciado. Coloca el vértice ancla a la altura real del asiento; no copies vértices de otro tipo de proxy.

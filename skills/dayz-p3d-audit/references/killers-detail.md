# The 13 Silent P3D Killers — full detail

> Extracted from dayz-p3d-audit/SKILL.md 2026-07-07 (F3). The core SKILL.md keeps the index/summary and points here.


These produce ZERO engine errors but break functionality completely. The core SKILL.md carries the one-line index of all 13; this file holds the full body of each killer (root cause, detection snippet, fix, caveats).


### 1. Collision LOD Wound Opposite to the Visual LOD (CRITICAL — Most Common from Blender)

A collision component (Geometry, View or Fire Geometry LOD) whose cross product
`cross(v1-v0, v2-v0)` points OUTWARD lets the LOD raycasts (`RaycastRV`, `RaycastRVProxy`)
from outside pass through it, the rays action targeting (`view`) and ballistic hits (`fire`)
rely on (`dayz-model-pipeline` Rule 18 and its symptom triplet). On the boxes measured below
its physics body still stopped a walking player and held one standing on it. A correct MLOD
winds the cross product away from the side meant to be seen and stores its normals the same
way (Rule 12): INWARD on a solid seen from
outside, which every collision component is. Rule 12's in-game probe of 2026-10-01 agrees:
Geometry, View and Fire components converted with its map registered `scene_raycast` hits from
both sides, and after the det=+1 map alone none — a map that also mirrors the model and leaves
its normals outward, so not a winding-only experiment.

**Measured in game** (2026-10-02, DayZDiag 1.29.163709, driven by dayz-mcp): killer #2's 2 m box
(one `Component01` per collision LOD, every face wound inward) against the same bytes with every
face of its Geometry, View and Fire LODs reversed and their normals negated (Rule 18: 6 of 6
faces outward per LOD; `audit_p3d.py`: `ERR_WINDING_INVERTED` on all three; Visual and Memory
LODs byte-identical). Each was packed unbinarized and binarized (binarize does not undo the
outward winding: the binarized outward boxes missed the same rays) and loaded as an
`Inventory_Base` item (`physLayer="item_large"`) and as a `HouseNoDestruct`:

| collision LODs | `scene_raycast` in `geom`, `view`, `fire` | `RayCastBullet` (physics) | player walking into it | player standing on top |
|---|---|---|---|---|
| wound inward | every ray hits | hits the faces | stopped about 0.36 m before the face | stands on the top (MLOD item) |
| wound outward | no ray hits; vertical rays reach the ground | hits the same faces | stopped about 0.36 m before the face | stands on the top (MLOD and binarized items) |

Rays per item and mode: one from above, one from the side, one from inside; on the static copies
one from the side per mode and one from above in `view`. A `view` ray cast like the action
cursor's, from eye height toward the box, stopped on the inward MLOD item and went through the
outward one. The rays and the walk gave the same answer for both packings and both classes; the
standoff is the server's reading (the owner client stopped about 0.33 m before the face). The
stand probe put the player 6-7 cm above the top and moved them for 0.5 s, then read the server:
right after a teleport, standing still, the server kept the teleported height for 3 s even above
open ground. Same-run controls: a vanilla `HescoBox` stopped the player where it did in the
killer #2 run; on open ground the walk covered 7.5 m in 5 s, and a player placed 2.17 m above
the ground and moved for 0.5 s fell to it. On these boxes the outward winding hid the box from
the LOD raycasts and from nothing measured in the physics world. A walk does not diagnose the
winding either way: these outward boxes stopped the player, and a 0.49 m `item_small` kit let
the player through with either winding (`SKILL.md` "Absolute winding check", rule 6).
(claim: CLAIM-P3D-WINDING-PHYSICS-INGAME)

**Root cause**: the collision LOD and the Visual LOD reached the MLOD by different paths.
Rule 12's map treats every LOD alike; the mismatch comes from a LOD that did not go through it
the same way: collision boxes built in code in DayZ space with outward winding (code-built
geometry does not go through the map), a collision LOD exported with another axis map, or a
face reversal applied to some LODs and not to others. The model looks perfect and can still
stop the player (measured above), but the LOD raycasts go through it.

**Detection**: Rule 18's per-component check decides, once its prerequisites hold: every
non-proxy face of the collision LOD belongs to a `ComponentNN` selection (killer #8), and every
component is closed (killer #9) and convex (`dayz-model-pipeline` Rule 1). Then compare each
face's cross product with `face_centroid - component_centroid`; on a convex component this reads
each face exactly. A healthy component has EVERY face pointing toward its centroid (inward), not
most of them: one face pointing away is an inverted face. Faces outside every component, an open
or non-convex component, a component with no face scored, or a face without a reading (its first
three corners collinear, so a zero cross product: py3d `WARN_DEGENERATE_FACES`) leave the check
unresolved — meet the prerequisite or fix that face first, and never read an empty census as
healthy. `audit_p3d.py` does not run
this check; it reports the relative trigger below. The absolute mesh-center comparison is
disabled for false positives.

> **AUTOMATED CHECK (added 2026-05-21; scope corrected 2026-10-02)**: `audit_p3d.py` runs a
> RELATIVE winding check through py3d `P3D.validate()` (`audit_p3d.py:337`): it compares each
> collision LOD's winding orientation, seen from that LOD's centroid, against the **Visual LOD**
> and emits `ERR_WINDING_INVERTED` (printed as CRITICAL) when both are uniform and opposite.
> This replaces the old absolute centroid heuristic, which false-positived on every Blender
> export (left-handed transform) and so was disabled — that disablement is exactly why an
> inverted collision sphere could pass a full audit with "ALL PASSED". The relative check is
> coordinate-system-agnostic, but it judges whole LODs against the Visual LOD, so it is a
> trigger, not the verdict [OFFLINE MEASURED 2026-10-02, py3d 1.8.0, synthetic unit boxes]:
>
> - it fires on a one-box collision LOD wound outward under a Rule 12 Visual LOD, and clears
>   after `face.vertices.reverse()` (for that box's normals, see **Fix**);
> - it also fires on a healthy inward box when the Visual LOD's cross product points outward:
>   an inside-out Visual LOD (`SKILL.md`, item 1 of "The three py3d gates"), or a room meant to
>   be seen from inside (`SKILL.md` "Absolute winding check", rule 4);
> - on a collision LOD of two boxes 4 m apart, one box wound outward raises only
>   `WARN_WINDING_MIXED`, and the same LOD with both boxes inward still reads mixed (16.7 %
>   outward from the LOD's centroid).
>
> **MANDATORY when you GENERATE or EDIT a collision LOD** (procedural sphere, py3d round-trip,
> Blender import, inspector rebuild): re-run `audit_p3d.py` and Rule 18's per-component check
> **before deploying**: with its prerequisites met, every non-proxy face of every component must
> read inward. An `ERR_WINDING_INVERTED` CRITICAL that a complete
> per-component check does not confirm says nothing against the collision: check the Visual LOD
> against the side meant to be seen instead (Check A table in `winding-diagnostics.md`; a room
> seen from inside is right as it is). An unresolved check confirms nothing either way. Run
> these checks even when the object blocks the player: the outward boxes measured above still
> stopped a walking player and held one standing on top, and a body made with
> `dBodyCreateDynamicEx` takes its shape from the geoms passed to it
> (`1_core/proto/enphysics.c:51`), not from the LOD, so neither a walk nor a moving body tells
> the winding. A player walking through the object is not evidence of outward winding either:
> look for a collision LOD with no `ComponentNN` selection (killer #2) and at the body itself
> (its layer, its height, how it was created: `dayz-physics-engine`).

**Fix**: `face.vertices.reverse()` on each face that reads outward, and only on those
(`proxy:*` faces excluded): on a convex, closed component the reading is exact, and a component
wound outward reads outward on every face. Never a `vertices[1]`/`[2]` swap, which inverts a
triangle but turns a quad `[0,1,2,3]` into `[0,2,1,3]`, a crossed face (`tools/py3d/README.md`).
Do not reverse a collision LOD to match the Visual LOD: shipped collision LODs carry mixed
whole-LOD signs, while seven debinarized vanilla models and four LFPG models wind 0 % outward per
component (`SKILL.md` "Absolute winding check", rule 7). Read the stored normals of the faces you
reverse with the Check A table in `winding-diagnostics.md`: negate a face's normals in the same
pass only if they pointed outward along with its winding (otherwise py3d's absolute check then
reports the winding against its own normals, `ERR_WINDING_VS_NORMALS`); keep them if they already
pointed inward. A normal shared with a face you leave alone gets a new pool entry
(`winding-diagnostics.md`, "From Check B to fix", item 3).

**Why the collision failure may not affect the Visual LOD**: Visual and Geometry LODs have independent face data.
One can be correct while the other is inverted. DayZ renders Visual LODs single-sided with backface culling:
inverted faces are see-through / textured on the inside. Check the Visual LOD offline with the absolute check
(`SKILL.md` "Absolute winding check") and Check A (`winding-diagnostics.md`).

*(Corrected 2026-10-02 against `dayz-model-pipeline` Rule 12, measured in game 2026-10-01, and
Rule 18. This killer was titled "Inverted Face Winding" and opened: "Geometry LOD faces have
normals pointing INWARD. Raycasts from outside pass through without detecting collision — no
collision, no action targeting, no physics." Its root cause read: "Blender Z-up → DayZ Y-up axis
conversion flips triangle winding on collision LODs while leaving the Visual LOD correct." Its
detection read: "Compare each collision LOD's winding orientation against the Visual LOD of the
same model." The automated check took the Visual LOD as the reference, "(which renders correctly
in-game and therefore defines this model's correct convention)", and ended: "If the CRITICAL
fires, swap `vertices[1]`/`[2]` on every face of that LOD so it matches the Visual LOD
convention." The Fix line read: "Swap `vertices[1]` and `vertices[2]` of each inverted face."
The last paragraph ended: "Check offline with
`skills/dayz-characters/references/check_dayz_winding.py`." That script then predated Rule 12 and
failed a correct export; since 2026-10-02 it reads Rule 12 (dayz-characters, "OFFLINE GATE").)*

*(Measured in game 2026-10-02, the outward boxes above: the opening said an outward component
"lets raycasts from outside pass through without detecting collision — no collision, no action
targeting, no ballistic hits"; the root cause ended "The model looks perfect but is physically
invisible."; and the MANDATORY note ended "A separately-created dynamic physics body
(`dBodyCreateDynamicEx`) can still make the object move, which masks inverted collision winding
— the object rolls but the player walks through it and no action cursor registers." The outward
boxes stopped a walking player like the inward ones and held one standing on top, and only the
LOD raycasts missed them, the `view` rays the action cursor casts among them: the missing action
fits the measurement, the walk-through does not. The sentence matches the
rolling stone of `dayz-physics-engine/references/fisica-engine-deep-dive.md` §7, a
`dBodyCreateDynamicEx` sphere, and that section puts the stone's walk-through down to a body
created only on the server and its missing action to a missing View Geometry LOD.)*

### 2. No `ComponentNN` Selection in the Collision LODs (CRITICAL)

A box whose Geometry, View and Fire LODs all carried no `ComponentNN` selection had no collision
in any consumer that was measured: no `scene_raycast` hit in `geom`, `view` or `fire`, no
`RayCastBullet` hit, and the player walked through it. No line in the RPT or the script log said
so. `component01` and `Component01` gave the same result as each other.

**Measured in game** (2026-10-02, DayZDiag 1.29.163709, driven by dayz-mcp): one 2 m box written
as three MLODs that are byte-identical except for the selection on the Geometry, View and Fire
LODs: `Component01`, `component01` (those two files differ in exactly three bytes, the `C` of
each name), or none. Each was loaded packed unbinarized and binarized, as an `Inventory_Base` item
(`physLayer="item_large"`) and as a `HouseNoDestruct`, with every face wound inward (Rule 18):

| collision selection | `scene_raycast` (item; geom, view, fire) | `RayCastBullet` (physics) | player walking into it |
|---|---|---|---|
| `Component01` | 6/6 per mode, both packings | hit, both packings | stopped 0.36 m before the face |
| `component01` | 6/6 per mode, both packings | hit, both packings | stopped 0.36 m before the face |
| none | 0/6 per mode, both packings | no hit | walked through |

Rays per item and mode: one from above, one from each of the four sides at mid-height, one from
inside; the two names gave the same faces to the centimetre. The `HouseNoDestruct` copies gave the
same answer on one horizontal ray per mode, the physics ray and the walk. Same-run vanilla
controls (layers from their vanilla configs): `HescoBox` (`item_large`) took every ray and
stopped the player at the same 0.36 m; `WoodenCrate` (`item_small`, inherited from
`Inventory_Base`) took every ray and did not stop the player. The crate is also low, so the run
does not tell whether its layer or its height let the player pass; either way, a walk-through
alone does not show that the collision geometry is missing. A free walk covered the 7.5 m in
about 5 s; a blocked one held for the full 10 s. (claim: CLAIM-P3D-COMPONENT-CASE-INGAME)

**Binarize removes the difference anyway**: from the `Component01` and the `component01` MLOD it
writes the same ODOL, byte for byte, with the name stored as `component01`.

**Detection**: a collision LOD with faces and no `ComponentNN` selection. From py3d 1.9.0,
`P3D.validate()` (`_check_component_naming`) raises `ERR_COMPONENT_NAMING` on each Geometry, View
or Fire LOD that has faces outside its proxy triangles and no selection whose name starts with
`component`, in any case; when there are such names but none is `Component` and a number (only
`Component_01`, say) it raises `WARN_COMPONENT_NAMING` instead. An empty component selection
counts as present there. Up to 1.8.0, the wheel pinned until 2026-10-02, it checked the Geometry LOD
only ("No Component selection found"), and the same code also fired on a lowercase
`component01`, which works, so that reading is a false positive.

**Fix**: select each closed, convex part of the collision LOD as its own `ComponentNN`
(`Component01`, `Component02`, ...) over all of that part's points and faces, the components
together covering the LOD (killer #8). Do not rename `component01` to `Component01` to repair
collision: both gave the same results.

**Not measured**: other spellings (`COMPONENT01`, `Component1`, `Component_01`), names that
differ only by case inside one model, more than one component per LOD, a component in some
collision LODs and none in others, consumers other than the three above (weapon fire, the action
cursor, vehicles hitting it, AI), vehicles.

*(Corrected 2026-10-02: titled "Component Selection Case Sensitivity", this entry read: "Geometry
LOD component MUST be `Component01` (uppercase C). The engine string-matches exactly.
`component01`, `COMPONENT01`, or any variation silently fails — engine finds zero components and
ignores ALL collision geometry." and "**Verified against**: LFPowerGrid production models (fridge,
furnace, battery_adapter) all use `Component01`." Those files show which name LFPowerGrid used,
not that another name fails. An earlier run the same day (the kit-box measurement behind rule 6
of "Absolute winding check") also reported LFPowerGrid's `lf_solarpanel.p3d`, whose collision
component is `component01`, taking 21 of 21 rays.)*

### 3. Missing `autocenter=0` LOD Property (CRITICAL for Inventory_Base)

For items with `autocenter=0` in config.cpp, the Geometry LOD MUST ALSO carry
`autocenter=0` as a named property. Config property controls the visual mesh;
LOD property controls the collision mesh. Without both, collision is displaced.

**Where**: Named property on ALL collision LODs — Geometry (1e13), LandContact (2e15), ViewGeometry (6e15), FireGeometry (7e15), plus Roadway/Hitpoints when present. GeoPhys 2e13 and FireGeo 3e13 are Arma 3 resolutions that DO NOT apply to DayZ — the engine ignores LODs at those values. DayZ canon (matches `audit_p3d.py` and `dayz-model-pipeline`): Geometry 1e13, Memory 1e15, LandContact 2e15, ViewGeo 6e15, FireGeo 7e15.
In py3d: `lod.properties['autocenter'] = '0'`

### 4. Missing Memory LOD or Geometry LOD (CRITICAL)

A P3D without a Memory LOD (res ~1e15) will have no animation, no bounding data, and
potentially crash the engine. A P3D without a Geometry LOD (res ~1e13) will have zero
collision and zero action targeting.

**Required LODs for any interactive DayZ object:**
- LOD 0: Visual (res=0.0) — rendering
- Memory (res ~1e15) — animation axes, bounding, interaction points
- Geometry (res ~1e13) — collision and cursor raycasting

**Recommended additional LODs (DayZ canon — GeoPhys 2e13 / FireGeo 3e13 are Arma 3 values that do NOT apply to DayZ):**
- LandContact (res 2e15) — ground placement contact points
- ViewGeometry (res 6e15) — action cursor + occlusion raycasts
- FireGeometry (res 7e15) — ballistic raycast (bullets)

### 5. Missing `pos center` Memory Point

Without `pos center`, the engine calculates bounding center from vertex distribution.
For tall/asymmetric objects (flagpoles where most vertices are in cloth at top), the
calculated center is far from the base — breaking the action targeting pre-filter.

**Fix**: Add `pos center` at `(0.0, 0.0, 0.0)` in Memory LOD for `autocenter=0` items.

### 6. Missing Animation Selections & Axes

If model.cfg defines an animation (like `flag_mast`), the P3D MUST have:
- **Visual LOD**: Named selection matching the animation selection name (e.g. `flag_mast`)
  covering all vertices/faces that should animate
- **Memory LOD**: Named selection matching the axis name (e.g. `flag_mast_axis`) with
  EXACTLY 2 points defining the animation axis (start and end of translation/rotation)

If either is missing, the animation silently does nothing.

> **Caveat — vehicles: the axis↔selection binding lives in `model.cfg`, so this check
> false-positives on a valid decoupled rig (added 2026-06-05, LL-027).** `audit_p3d.py`
> cross-references Memory↔Visual by a NAME heuristic — it assumes `wheel_X_X_axis` implies
> a visual selection literally named `wheel_X_X`. A clone-Croco / vanilla wheel rig
> legitimately DECOUPLES the names: the selection is `wheelfrontleft` while the rotation
> axis is `wheel_1_1_axis`, and the two are tied in `model.cfg`
> (`class wheel_1_1 { source="wheelfrontleft"; selection="wheelfrontleft"; axis="wheel_1_1_axis"; }`,
> see `dayz-model-pipeline/references/vehicle-config-and-modelcfg.md` §12). The audit then
> reports the selection as "missing" when it exists under a different name. Real LFQuad case:
> 12 spurious CRITICALs on the C.6 body, all false positives. **Rule:** for ANIMATED AXES on a
> vehicle, treat these CRITICALs as WARNING until you cross-check `model.cfg` — read the
> `selection=`/`axis=` of each animation class and confirm BOTH names exist in the `.p3d`
> (axis as a 2-point Memory selection, the named `selection=` in the Visual LOD). A rig that
> decouples axis-name from selection-name is valid (Croco/vanilla pattern). The deep fix
> (parse `model.cfg` in `audit_p3d.py`) is tracked as PB-010.

### 7. Missing `box_placing_min` / `box_placing_max` Memory Points

For deployable objects using the hologram placement system, the Memory LOD needs:
- `box_placing_min` — single point at the minimum corner of the placement bounding box
- `box_placing_max` — single point at the maximum corner

Without these, the hologram collision check may malfunction (permanently block placement
or never detect terrain collision).

**Note (empirical, vanilla 1.x)**: This memory-point pair is a *fallback*. Vanilla
`hologram.c::GetProjectionCollisionBox` first calls `m_Projection.GetCollisionBox(min_max)`,
which returns the bbox derived from the Geometry LOD; only if that fails does it fall
back to `box_placing_*`. Vanilla deployables (`55galdrum`, `wooden_case`, `sea_chest`,
`MilitaryCrate` from a6_base_storage) ship `boundingbox_min/max` as Memory LOD selection
names — NOT `box_placing_*` — and rely on the Geometry LOD bbox. So this rule fires only
for items without a proper Geometry LOD or with broken `GetCollisionBox()` data.

### 8. Incomplete Component Coverage

Every face of a collision LOD (proxy triangles aside), and every point those faces use, must belong
to a `ComponentNN` selection with weight=1: one component per closed, convex part
(`dayz-model-pipeline` Rule 1), the components together covering the LOD. A closed part left out of
every component collides with nothing in the LODs it is left out of, also when they have other
components (measured in game on two such parts, below): a box left out of all three took no
`scene_raycast` hit in `geom`, `view` or `fire` and no `RayCastBullet` hit, and the player walked
through it; a lever left out of Geometry and Fire took no hit in those LODs and no `RayCastBullet`
hit, and its knob did not stop a player walking into it; no log line said so. A part left out only
in part (one face of a box whose other faces are in a component, or faces whose points sit in one)
was not measured. Never merge separate parts into one `Component01` to make it cover everything: a
component that holds two separate parts is not convex.

py3d 1.10.0 (`_check_component_coverage`) reads the union of the `ComponentNN` selections, whatever
the case, on the Geometry, View and Fire LODs, against the faces that no component holds and the
points those faces use that no component holds. Proxy triangles (a `proxy:` selection holding one
triangle and, as its 3 points, that triangle's corners; a whole box under a proxy name counts as
collision geometry) and points that no face uses are not counted. It groups the faces into pieces
that share a corner position and raises `ERR_COMPONENT_COVERAGE`, an ERROR, for the case measured
below: a piece that is a closed solid (each edge used by two of its faces, once each way, around a
volume) with no face and no point in any component. It reads each LOD on its own, while the parts
measured below were left out of all three LODs (the box) or of Geometry and Fire (the lever): its
message says that a part left out of one LOD alone was not measured. A piece thinner than 16 float32
steps at its distance from the model's origin (taken as at least 1 m) counts as flat, so a
double-sided sheet stays the WARN wherever it lies; corners are read as the MLOD stores them
(float32), so a model reads the same in memory and once written. Every other face in no component (a
part left out only in part, an open piece such as a stray triangle, a flat double-sided sheet, a
closed piece too thin for the cutoff at its distance from the origin, which errs toward the WARN),
and every point of a covered face that no component holds, stay `WARN_COMPONENT_COVERAGE`, whose
message says they were not measured. A LOD with no component at all is `ERR_COMPONENT_NAMING`'s
finding (killer #2); one whose component selections are all empty is read like any other, its closed
parts raising the ERROR (an empty selection itself was not measured). On the three door samples of
the `dayz-doors` tutorial it is silent on `Simple_Door` and `Door_w_Button` and raises the ERROR on
the Geometry and Fire LODs of `Expert_Mode`, whose lever (18 faces, one closed piece: selection
`lever` in Geometry, `door1_open` in Fire) is in no component there, though the tutorial's text
lists the lever among the parts that take up space. The 1.10.1 wheel, pinned since 2026-10-03,
runs this check unchanged. The 1.9.0 wheel, the pin from 2026-10-02 to 2026-10-03, raises every face in
no component as `WARN_COMPONENT_COVERAGE`, and its message says that a face left out beside covered
ones was not measured: with that wheel, read a closed part it counts in no component as the
measured case below.

**Measured in game** (2026-10-02, DayZDiag 1.29.163709, driven by dayz-mcp): a pair of 2 m boxes,
A in `Component01` and B either in `Component02` or in no component (the two MLODs byte-identical
apart from the three `Component02` tags; every face wound inward, Rule 18), loaded packed
binarized and unbinarized, as a `HouseNoDestruct` and as an `Inventory_Base` item
(`physLayer="item_large"`):

| box B | rays on B (`geom`, `view`, `fire`, `RayCastBullet`) | player walking into B |
|---|---|---|
| `Component02` | 26/26 | stopped 0.33 m before the face |
| in no component | 0/46; the vertical rays reach the ground | walked through: 7.5 m in about 5 s, as on open ground |

Box A took 40/40 in the same objects. Binarize keeps the left-out faces in the ODOL (it lowercases
the component names); the engine ignores them. The tutorial's `Expert_Mode`, spawned the same way,
gave the lever no Geometry, Fire or physics hit (0/28), and a player walking into the lever's knob
stopped on the block behind it. In its View LOD the lever is `Component09`, one closed piece that
is not convex (an octagonal knob and a bar): only the knob answered (3/3) and the bar took none
(0/9), so that non-convex component collided only in part; each collision LOD answered by its own
components (the lever, a component in View only, was hit in View only). No RPT or script-log line
named any of these models. Not measured: a part left out only in part, weapon fire, the action
cursor, vehicles, DayZ 1.30 Exp.
(claim: CLAIM-P3D-UNCOVERED-FACES-INGAME)

Up to 1.8.0, the wheel pinned until 2026-10-02, the check compared `Component01` alone with the
whole Geometry LOD, so it fired on a healthy multi-component LOD: `gate_and.p3d`'s Geometry LOD
holds six components of 8 points each (48 points, 36 faces) and reads "Component01 covers 8/48
vertices", yet that model took every ray in game (SKILL.md, "Absolute winding check", rule 6).
With that wheel, count the union of the `ComponentNN` selections yourself.

*(Corrected 2026-10-02: titled "Incomplete Component01 Coverage", this entry read "`Component01`
must include ALL vertices AND ALL faces of the Geometry LOD with weight=1." The first correction
that day still opened "Every vertex and face of a collision LOD must belong to a `ComponentNN`
selection" and said "Partial coverage means partial collision — some faces won't register
raycasts.", a consequence measured only for a LOD with no component at all.)*

*(Updated 2026-10-02, after the in-game A/B above: the first paragraph read "A face outside every
component is expected not to collide, but that was measured only for a LOD with no component at
all (killer #2), not for a face left out next to covered ones.", and the py3d paragraph read "A
face outside every component on a LOD that has others was not measured in game, so the finding
stays a WARN." and closed "whether that lever collides in game was not measured.")*

*(Updated 2026-10-03, py3d 1.10.0: the py3d paragraph opened "py3d 1.9.0 `WARN_COMPONENT_COVERAGE`
(`_check_component_coverage`) reads the union", said "one whose component selections are all empty
is reported here, every face counted. py3d 1.9.0 raises it as a WARN, and its message says that a
face left out beside covered ones was not measured: both predate the in-game A/B below, which
measured whole parts left out beside covered ones." and "flags the Geometry and Fire LODs of
`Expert_Mode`".)*

*(Updated 2026-10-03, after the py3d 1.10.0 review: the first paragraph read "A closed part left out
of every component collides with nothing, also when the same LOD has other components: no
`scene_raycast` hit in `geom`, `view` or `fire`, no `RayCastBullet` hit, the player walks through
it, and no log line says so (measured in game on two such parts, below).", which gave both parts the
box's readings: the lever was a component in View and was hit there, and a walk along its arm was
inconclusive.)*

### 9. Non-Watertight Collision Mesh

The Geometry LOD mesh must be closed (watertight) — every edge shared by exactly 2 faces.
Open meshes (with boundary edges/holes) cause unreliable collision where raycasts can
pass through gaps.

### 10. Missing Surface/Material Assignment on Collision LODs (CRITICAL)

Every face in the collision LODs (Geometry / GeoPhys / FireGeometry / ViewGeometry /
HitPoints) MUST have a `material` assigned, pointing to a penetration `.rvmat` that in
turn references a `.bisurf` file. Without this assignment, the engine raycasts hit the
geometry but cannot resolve a surface to consult — bullets pass through, footstep sound
is missing, and action cursor may not register.

Vanilla items always ship this — verifiable via `strings <p3d> | grep penetration`:

| Vanilla object   | Penetration material assigned             |
|------------------|-------------------------------------------|
| `55galdrum`      | `dz\data\data\penetration\metalplate.rvmat` + `metalPlate.bisurf` |
| `wooden_case`    | `dz\data\data\penetration\wood_desk.rvmat` + `wood_desk.bisurf` |
| `sea_chest`      | `dz\data\data\penetration\wood_desk.rvmat` + `wood_desk.bisurf` |
| `MilitaryCrate` (a6_base_storage) | `dz\data\data\penetration\plastic.rvmat` + `plastic.bisurf` |

Detection (py3d):
```python
for lod in p.lods:
    if lod.resolution in collision_lod_ranges:
        for face in lod.faces:
            assert (face.material or '') != '', f"face missing material in {lod_label}"
```

Fix: in Object Builder OR programmatically via py3d, set `face.material =
"dz\\data\\data\\penetration\\<surface>.rvmat"` for every face in every collision LOD
and write back. Visual LOD keeps its complex multi-stage `.rvmat` (e.g. `wooden_case.rvmat`)
unchanged — the penetration `.rvmat` is a SEPARATE simpler material used only by
collision LODs. Symptoms persist after binarization (ODOL preserves the empty
material), so this can be missed until in-game ballistic test.

### 11. Wheel Proxy `.p3d` Memory LOD has only `ce_center` (CRITICAL for wheeled vehicles) (added 2026-05-29)

If you audit a wheel proxy `.p3d` (the separate file referenced by `ProxyVehiclePart`
in `CfgNonAIVehicles`, atached to the body via `inventorySlot`) and its Memory LOD
contains only `ce_center` — the wheel is **anatomically incomplete**. The vanilla
pattern (Croco `quadbike_wheel.p3d` v53, verified 2026-05-29) ships 5 mem-points:
`ce_center`, `ce_radius`, `boundingbox_min`, `boundingbox_max`, `invview`. PhysX uses
those 4 missing ones to construct the wheel collider geometry; without them it falls
back to the Geometry LOD of the proxy (typically a small 8-vertex cube on procedural
wheels generated by `dayz-model-pipeline`).

**Symptom in-game (silent — no RPT error)**: `wheelCount=N wheelPresent=N anyLocked=0`
(attachment / config / FireGeo slot all OK) but `contact=0` permanent on every wheel
every frame. The vehicle spawns, the suspension engages once at frame 0 (penetration
contact via Geometry hub), then the body lifts more than ~10 cm and **the wheel raycast
can no longer reach ground** because the effective collider is the size of the hub cube
(~0.10 m) rather than the wheel diameter (~0.34 m). Body falls free, chassis Geometry
hits terrain, bounce divergente, `speedo` oscillates between large magnitudes, eventually
exceeds finite range and the engine logs `Will delete object with !finite or outside
world coords`. Symptom triplet:

- `wheelPresent` = full count (not the older `wheelPresent=0` blocker)
- `contact` = 0 across all wheels in EVERY frame
- Body Y oscillates with amplitude growing per bounce (energy never dissipates because
  there is no wheel-ground contact to apply friction)

**Detection (py3d)**:

```python
WHEEL_REQUIRED = {"ce_center", "ce_radius", "boundingbox_min",
                  "boundingbox_max", "invview"}
for lod in p.lods:
    if abs(lod.resolution - 1e15) > 1e12: continue  # Memory only
    if not (path.endswith("wheel_front.p3d") or
            path.endswith("wheel_rear.p3d") or
            "wheel" in path.lower()):
        # Heuristic: this proxy is a wheel if its Geometry LOD bbox Y span
        # matches a wheel-shaped aspect (Y span ≈ Z span ≈ 2× radius from config).
        pass
    have = set(lod.selections.keys())
    missing = WHEEL_REQUIRED - have
    if missing:
        flag_critical(f"wheel proxy Memory missing {missing}")
```

**Fix**: bake the 4 missing mem-points using the Croco-vanilla convention (Y vertical,
X axial, Z with intentional min/max inversion). Reference values + scaling rules in
`dayz-model-pipeline/references/vehicle-structural-parity.md` §"Addendum (2026-05-29)
— Wheel proxy `.p3d` Memory anatomy (T1-D)". Bake with py3d 1.0.0 — observe the
6 quirks in `dayz-animation-pipeline/references/py3d-1.0.0-quirks.md` (constructor
with args, weight `int` not `float`, rebind after grow, etc.). The 5 mem-points
do NOT carry weight — each is its own one-vertex Selection.

**Caveat (Visual LOD diameter vs collider size)**: PhysX uses the **Memory mem-points
to construct the wheel collider**, NOT the Geometry LOD of the proxy. A wheel proxy
can have a perfectly sized Visual LOD (Ø0.68) AND a tiny Geometry hub cube (~0.20)
AND `contact=0` because the Memory anatomy is incomplete. Visual size is not what
PhysX measures.

**Why this is silent until 2026-05-29**: `audit_p3d.py` checks Component01, autocenter,
winding, surface materials — but not selection-name presence per proxy class. The
wheel proxy passed ALL PASSED with only `ce_center`, and the bug surfaced 4 sessions
later as a bounce blocker (LL-057 — gap TIER 1 diferido sin gate). Until the audit
script is updated, surface this proactively when the symptom is "vehicle bounces on
spawn / contact=0 / speedo diverges to ±inf / delete-outside-world".

Origin: LFQuad bounce diagnostic 2026-05-29; LL-057 (process); cross-ref
`dayz-model-pipeline` Rule 19.

---

### 12. Wheel-vertical-placement: tire bottom below model origin / chassis floor below wheel-center line (CRITICAL for wheeled vehicles) (added 2026-05-29)

A wheeled vehicle whose wheels sit too LOW relative to the body rides with its belly too close to the ground. **Symptom:** `wheelCount=N wheelPresent=N` OK but `contact=0` permanently on all wheels even at rest; chassis bounces elastically on terrain; vehicle falls unbalanced / rotates. No RPT error -- silent killer.

3 working references (Croco quad, vanilla `offroadhatchback`, `civiliansedan`) all place the **tire bottom ~ at/above the model origin** (never negative) and the **chassis floor ~ at/above the wheel-center line**. Anti-example: LFQuad shipped with tire bottom Y=-0.114, chassis floor Y=0.120 (0.107 BELOW the wheel center 0.227) -- 4+ iterations of geometry fixes never measured this because the invariant lived in the skill only as prose (LL-062).

**Check** (measure, don't eyeball; compare to a debinarized working reference):
```python
geo = next(l for l in p3d.lods if abs(l.resolution - 1e13) < 1e11)
wheel_center_Y = ...   # Memory wheel_X_X centroid Y (or hub damper_land)
radius = ...           # config Axles -> Wheels.radius
tire_bottom   = wheel_center_Y - radius
chassis_floor = component01_bbox_min_Y(geo)
if tire_bottom < -0.02:
    flag_critical(f"tire bottom {tire_bottom:.3f} below model origin (working refs ~+0.01/+0.05)")
if chassis_floor < wheel_center_Y - 0.05:
    flag_critical(f"chassis floor {chassis_floor:.3f} below wheel-center line {wheel_center_Y:.3f}")
```

**Coupling (do not create a new anomaly):** the fix raises BOTH the wheel/hub system AND the chassis floor to the reference triple -- raising only the wheels worsens resting clearance. See `dayz-model-pipeline/references/vehicle-structural-parity.md` "Addendum 2026-05-29 -- ride-height triple" + LL-062. Causal link to `contact=0` is `[verify in-game]` (R31); the parity divergence itself is verified vs 3 references.


### 13. Vehicle Geometry built as ONE monolithic component / mass concentrated / missing per-component `autocenter=0` (CRITICAL for wheeled vehicles) (added 2026-05-30)

A working DayZ car's Geometry LOD is a **compound of several closed convex components**, each with mass and `autocenter=0` — never a single monolithic hull holding all the mass. Building it as one component is the silent root of the classic **launch/bounce at spawn**: the chassis explodes upward the instant it's created, tumbles, gains energy, and the engine deletes it (`Will delete object with !finite or outside world coords`). No RPT error.

Mechanism (documented): PhysX resolves spawn interpenetration in a single step → large separating impulse (NVIDIA PhysX Best Practices, "Overlapping objects explode"); sharp edges of a tight monolithic hull "impart a large moment … sending it up into the air" (Arma Anti-Bounce community). Mass concentrated in one component → low/pathological inertia tensor → the impulse becomes a runaway tumble (LOD wiki: "the Mass distribution is critically important … Inertia/Moment of Inertia"). Anti-example: LFQuad shipped with **1** chassis component (`component01`) holding ~90% of mass, Izz 128.5 vs the Croco reference 350.7 (37%); the working Croco quad has **23 chassis components + 4 hubs**.

Working references converge: Bohemia `DayZ:Vehicle_Configuration` ("convex components. Every component's vertex should have weight assigned. From these weights the total mass of vehicle and its center of mass is computed. Wheel hubs should have their own components"); the Tyson89/Landrover tutorial Object-Builder checklist ("Convex Components / autocenter value 0 / Applied a Mass on **ALL** components / Wheel hubs present / Center of Mass"). See `dayz-model-pipeline/references/vehicle-structural-parity.md` Addendum 2026-05-30 + external refs there.

**Check** (measure, don't eyeball; compare to a debinarized working reference):
```python
geo = next(l for l in p3d.lods if abs(l.resolution - 1e13) < 1e11)   # Geometry LOD
comps = components_in(geo)                          # named selections componentNN (chassis) + hubs
chassis = [c for c in comps if c.name.startswith("component")]
if len(chassis) <= 1:
    flag_critical(f"Geometry chassis is {len(chassis)} component (monolith); working cars use many "
                  f"convex components (Croco ~23). Single hull → spawn-launch + low inertia.")
for c in comps:                                     # mass on ALL components, none ~0, none dominant
    if c.mass <= 0:
        flag_critical(f"component {c.name} has no mass; CoM/inertia will be wrong")
    if c.mass > 0.6 * total_mass:
        flag_critical(f"component {c.name} holds {c.mass/total_mass:.0%} of mass (concentrated → low inertia)")
    if c.named_property("autocenter") != "0":       # extends Killer #3 to per-component on vehicles
        flag_critical(f"component {c.name} missing autocenter=0 (engine may recompute CoM)")
com = center_of_mass(geo)
if abs(com.x) > 0.05:
    flag_critical(f"center of mass X={com.x:.3f} not laterally centered (vehicle will lean/launch)")
```

Note `autocenter=0` is already Killer #3 but only for `Inventory_Base`; on a **vehicle** it must be present on **every** Geometry component (per the Landrover checklist), or the engine recomputes the origin and shifts the CoM relative to the mass you assigned. The fix couples with Killer #12 (ride-height): rebuild the chassis as multiple convex components with distributed mass AND correct vertical placement together — raising one without the other creates a new anomaly (LL-030). Causal link to the launch is `[verify in-game]` (R31); the construction divergence vs 3 references is verified.

> **Correction (2026-06-02, verified in-game):** the `[verify in-game]` above was settled and the causal attribution did NOT hold. The CONFIRMED root cause of the LFQuad spawn-launch/bounce was a spurious `#Mass#` tagg (all zeros) on a non-Geometry LOD (FireGeometry) → AddonBuilder/binarize baked the mass of THAT LOD → deployed ODOL with `CoM=(0,0,0)` and zero inertia → `ECE_PLACE_ON_SURFACE` spawned the vehicle ~0.48 m below ground → PhysX ejection. It was **not** the monolithic Geometry nor the low inertia tensor. Multi-component Geometry with distributed mass remains **best-practice** (ride-height, collision, convex-component correctness per the Landrover/Bohemia checklist), but it is NOT the cause of the spawn-launch — keep this Killer as a recommended construction practice, not as the spawn-launch diagnosis. Fix = strip `#Mass#` from every LOD that is not the Geometry LOD (set `point.mass = None`, not `0.0`). See this skill's **"#Mass# debe vivir solo en Geometry LOD"** section + LL-079/LL-080/LL-081 + the worked example, and the mirrored correction in `dayz-model-pipeline/references/vehicle-structural-parity.md` Addendum (2026-05-30). First diagnose with the mass-only-Geometry check (it catches the real cause in seconds) before suspecting the chassis-component count.

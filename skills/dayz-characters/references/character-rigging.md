# Rigging a custom humanoid mesh to OFP2_ManSkeleton

The expensive, character-specific step. Goal: produce **per-vertex weights** that map your custom mesh's
vertices to the exact `OFP2_ManSkeleton` bone names, with the mesh sitting in the canonical bind A-pose,
then carry those into the `.p3d` as **named selections**. In DayZ there is no shipped armature — the
`model.cfg` defines the skeleton; the `.p3d` carries named selections + weights; the engine pairs them.

Verified end-to-end in Blender against the official BI rig ([LFInfectedBig ✓] 2026-06-24). The Blender
side is fully exercised; the `.p3d` export bridge is flagged `[TBD-verify]` below.

## 0. Get the official rig (one download)

`animation_rig_character.fbx` from `BohemiaInteractive/DayZ-Misc` → "Rig and Animations". Blender-native
FBX: armature `Armature` with **114 bones (exact OFP2_ManSkeleton names)** + a weighted body `Male_body`
in the **canonical bind A-pose**. Units = **cm** (height ~172.5). Helpers (`*_Dummy`, `Weapon_*`,
`EntityPosition`) import as **EMPTIES**, not bones.

```powershell
$dir="C:\path\_rig"; New-Item -ItemType Directory -Force $dir | Out-Null
$enc="Rig%20and%20Animations/animation_rig_character.fbx"
Invoke-WebRequest "https://raw.githubusercontent.com/BohemiaInteractive/DayZ-Misc/master/$enc" `
  -OutFile "$dir\animation_rig_character.fbx" -Headers @{ "User-Agent"="x" }
```

Inspect once: import, list `bpy.data.objects` (armature + `Male_body` + empties), `armature.data.bones`
names, world Z-span (height in cm), and which target bones exist. Confirm names match the bone catalog
(`dayz-animation-pipeline/references/player-skeleton.md`).

## 1. Fit the armature to your mesh — THE SCALE GOTCHA

Keep your mesh at its final size (e.g. baked 1.2× → 2.277 m) and **scale the armature to it**. The
armature's absolute size is irrelevant to the game (the engine uses vanilla `OFP2_ManSkeleton`); it only
generates weights.

**MUST bake the scale into the armature before bone-heat.** Scaling only the object (or a parent) leaves
the bone *data* at native cm scale; bone-heat then runs the 172-unit armature against your 2.3-unit mesh
→ the whole mesh is a dot near `Pelvis` → **every weight collapses to `Pelvis`**, every other bone gets 0
verts. The tell: after binding, posing any limb moves nothing.

```python
# arm = the imported Armature, low = your mesh (feet at z=0, centred)
arm.parent=None; arm.animation_data_clear()
s = mesh_height / armature_world_height
arm.scale=(s,s,s); bpy.context.view_layer.update()
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)   # <-- bake into bone data
# then translate the armature so its bone-bbox feet are at z=0, centred on the mesh, and apply location
```

## 2. Bind with automatic weights

Disable deform on bones you don't want as selections (face, fingers, eyes, tongue) to keep the vgroup
set clean, then parent with automatic weights.

```python
for b in arm.data.bones:
    if b.name.startswith("Face_") or b.name in ("EyeLeft","EyeRight") \
       or any(f in b.name for f in ("Index","Middle","Ring","Pinky","Thumb")) or "Tongue" in b.name:
        b.use_deform=False
bpy.ops.object.select_all(action='DESELECT')
low.select_set(True); arm.select_set(True); bpy.context.view_layer.objects.active=arm
bpy.ops.object.parent_set(type='ARMATURE_AUTO')
```

**Verify the distribution, not just success.** Count weighted verts per major bone — if `LeftUpLeg`,
`Spine1`, `LeftArm` etc. are non-zero and `Pelvis` isn't hoarding everything, the fit was right. (~44
deform bones for a body rig.) Confirm 0 zero-weight verts.

## 3. Bind pose — conform the mesh to canonical

The mesh MUST ship in the rig's canonical A-pose; anims are relative to that rest. Measure each limb's
direction vs its bone; if off, rotate that limb's verts around the joint, **masked by the vertex's
auto-weight in the limb groups** so the shoulder/hip blends smoothly (no crease). Re-bind afterwards for
clean weights on the conformed mesh.

```python
# per side: pivot = armb.head (world); target = bone chain direction; R aligns mesh_arm_dir -> target
from mathutils import Quaternion
for v in low.data.vertices:
    w = sum(g.weight for g in v.groups if vgname(g) in arm_groups)   # 0..1
    if w<=1e-4: continue
    Rw = Quaternion().slerp(R, min(w,1.0))                            # partial rotation = smooth falloff
    v.co = MWi @ (pivot + Rw @ (MW@v.co - pivot))
```

[LFInfectedBig ✓] arms were 28°/34° narrower than canonical; this opened them onto the bones cleanly.

**Angle is NOT enough — match joint POSITIONS too** [✓ in-game LFInfectedBig S7 2026-06-24]. The rotation
above conforms each limb's *direction*, but the engine binds against the canonical bone *positions* (see
SKILL.md → THE CANONICAL-BIND INVARIANT). If the mesh's anatomical joints (elbow/knee/shoulder/wrist) sit at
different *positions* than the canonical bones — which an AI mesh always will; its proportions are its own —
the limbs **overextend / stretch under anims** even though scale, orientation and winding are all correct,
and the rest pose looks perfectly fine. LFInfectedBig shipped with this unfixed (arms ~0.12 m *shorter* than
the armature — length, not angle) → visible arm overextension in-game. Fix = a **proportion conform**: move
the mesh's joint regions onto the canonical bone positions (weight-masked, same idea as the angle conform)
so every bone sits on the anatomy it drives, then re-bind/re-weight. Verify offline with the bone-head →
weighted-vert-centroid distance check (`_export/diag_bind_mismatch.py`); large distances = that limb will
deform. [The position conform is not yet shipped on LFInfectedBig — queued as a fresh-session task.]

## 4. Cleanup

```python
bpy.ops.object.vertex_group_limit_total(limit=4)     # DayZ skinning: <=4 influences/vertex
bpy.ops.object.vertex_group_normalize_all()
```

Target: max 4 influences/vert, 0 zero-weight verts (zero-weight → pinched/spiky verts in-game).

**CRITICAL — kill cross-midline auto-weight bleed (the "totally deformed in-game" bug).** Blender
bone-heat on a narrow torso bleeds weight ACROSS the body centre: verts near spine/neck/chest/shoulders end
up weighted to BOTH a `left*` AND a `right*` bone (e.g. a chest vert → `leftarm` + `rightarm`). It looks
fine at rest and the deform-test passes (it never poses the two arms oppositely), but in-game the opposing
limb anims TEAR those verts apart → grossly deformed mesh (and smeared UVs → "wrong colours"). It does NOT
log a script error. The binarize tell is **`Error: vertices of bone X are shared with bone Y`** (left↔right
pair) — treat that as **BLOCKING**, never cosmetic. Fix per-vertex: keep only the dominant side (+ centre
bones spine/pelvis/neck/head), zero the minority side, renormalize. Verify: 0 verts with both a `left*` and
`right*` weight; binarize reports 0 "shared with bone". (LFInfectedBig S6: 1847 verts bled → totally
deformed in-game; reference impl `clean_cross_side()` in `_export/build_full_p3d.py`.)

## 5. Deform sanity-check (gross motion only — NOT the deform gate)

This Blender pose-test is a FALSE GATE for real deform — the engine skins against the real
`OFP2_ManSkeleton`, not the rig-FBX armature; the deform gate is in-game/Buldozer (see SKILL.md
§"The Blender deform-test is a FALSE GATE").

Pose spine/arms/legs and render several views; bends must be smooth, no exploded verts, joints holding,
and any internal/cavity geometry must follow its parent bone. **Pose the LEFT and RIGHT limbs in OPPOSITE
directions in the SAME pose** (left arm up + right arm down, left leg fwd + right leg back) — this is the
only deform-test that surfaces cross-midline weight bleed (§4); posing one side at a time hides it and ships
a model that explodes in-game.

Headless pitfalls (all hit during [LFInfectedBig]):
- **The FBX may carry an Action.** If posing does nothing, `arm.animation_data_clear()` first — fcurves
  override manual `rotation_euler`. (Set `arm.data.pose_position='POSE'`.)
- **FBX bone tails are auto-generated by the importer** → `tail-head` direction does NOT follow the limb.
  Never detect A/T-pose from bone vectors; use a render or the skinned result.
- **Track deformation by ORIGINAL vertex index.** `evaluated_get(dg).to_mesh().vertices[i].index` is
  invalid after `to_mesh_clear()`. Pick the index from `low.data.vertices`, then read evaluated positions
  at that same `i` across poses; compare max delta over ALL verts (a single foot vert may be on the
  un-posed side).
- Set pose via `pose.bones[n].rotation_euler` (mode `'XYZ'`) + `view_layer.update()`; no mode switch
  needed in background.

```python
arm.data.pose_position='POSE'
pb=arm.pose.bones['LeftUpLeg']; pb.rotation_mode='XYZ'; pb.rotation_euler=(radians(45),0,0)
bpy.context.view_layer.update()
# max vertex delta vs rest > 0 and ~thousands of verts moving == skinning works
```

## 6. Export to `.p3d` (vgroups → named selections) — VERIFIED via py3d ([LFInfectedBig ✓] 2026-06-25)

The Blender vertex groups become **named selections** carrying per-vertex bone weights in the `.p3d`, mesh
in canonical bind pose. **Route that works headless/autonomous: py3d direct write** (no Object Builder /
DayZATool GUI needed). The other two routes (Object Builder import, DayZATool bridge) are GUI-bound and
were not needed. Two-stage pipeline:

**Stage A — Blender headless dump** (`mesh.calc_loop_triangles()` handles quads/ngons): per mesh dump
world-space verts (`matrix_world @ v.co`), triangles (loop-tri vertex indices), per-loop UV, per-corner
normals (`mesh.corner_normals[loop].vector`, transformed by `matrix_world.to_3x3()`), and a dense
`(N_verts × N_bones)` weight matrix from `v.groups`. Save `.npz`. Confirm `weight-sum == 1.0` and
`0 zero-weight verts` before proceeding (Blender already did `limit_total(4)+normalize_all`).

**Stage B — py3d builder.** Critical gotchas, each verified unless labelled otherwise:
- **Coordinate transform `(x, y, z) → (x, z, y)`, det = −1 (dayz-model-pipeline Rule 12)**, applied to
  every point and normal of every LOD and to the bone/memory points. *Corrected 2026-10-01:* this bullet
  used to prescribe `(x, z, −y)` (det = +1) as "`R⁻¹`, the exact space of the bind". That derivation dropped
  a handedness change. What the frames measure:
  - The rig in Blender is a non-mirrored body: front −Y, anatomical left +X, Z up. [OFFLINE MEASURED
    2026-10-01, Blender 5.1.1, both FBX importers] `LeftArm` head x = +0.16; `LeftToeBase` head 0.135 m in −Y
    from `LeftFoot`; `Male_body` vertices weighted to `LeftArm` at x = +0.22, toe vertices at y = −0.10.
  - The armature's `matrix_world` is indeed `R(+90° X)` (same run), and `R⁻¹ = (x, z, −y)` returns to the
    FBX file's own frame: Y up, front +Z, left +X. That frame is RIGHT-handed. Read as DayZ numbers
    (left-handed), it is a mirrored body that faces backwards.
  - The DayZ bind is a non-mirrored body in a left-handed frame: front −Z, left +X (vanilla male `left*` on
    +X, SKILL.md "mesh can be left/right MIRRORED"; worn frame −Z front / +X left, in-game verified,
    SKILL.md "WORN CLOTHING binds via ... DayzTemporarySkeleton").
  - So the FBX frame differs from DayZ by `z → −z`, and Blender → DayZ is `(x, z, −y)` followed by `z → −z`:
    `(x, z, y)`. It sends front −Y to −Z and keeps left on +X. Every det = +1 map lands the body mirrored:
    left and right swapped relative to where it faces.
  - The project history matches this [✓ in-game]: `(x, z, −y)` shipped LFInfectedBig facing and walking
    BACKWARD (S7); `(−x, z, y)` turned it round but left it mirrored, and the limbs flung back/up until the
    L/R selections were swapped (S9). The shipped build (`(−x, z, y)` + reversed faces + L/R swap) is the
    mirror image of the authored mesh.
  - [✓ in-game 2026-10-02, LFInfectedBig] The chiral check at the end of this section ran: the `(x, z, y)`
    build reads its marker correctly and is lit like a vanilla zombie; the shipped recipe reads it mirrored.
- **Winding and normals follow Rule 12; do not reverse the faces.** Under `(x, z, y)` the Blender face order
  lands in the MLOD convention by itself (cross product inward, collision LODs included, as Rule 18 wants);
  the shading normals are negated (MLOD stores them inward). The old "reverse every visual face" was right
  only under the det = +1 map, where it hid the mirror (LFInfectedBig S6: that map without the reversal
  rendered inside-out). With py3d ≥ 1.8.0, build the model from the Blender-space dump and call
  `py3d.blender_to_dayz(model)` once, before adding anything built in DayZ space: it maps every LOD,
  memory points included, keeps the face order and negates the normals. By hand: `P3D.transform(((1, 0, 0),
  (0, 0, 1), (0, 1, 0)))` maps points and normals and reverses every face because det < 0; reverse them
  back and negate the normal pool. `py3d.BLENDER_TO_DAYZ` is the old `(x, z, −y)`, deprecated in 1.8.0 and
  kept as `py3d.ROT_X_NEG90`: not for this export.
- **GATE — `check_dayz_winding.py` predates Rule 12 and fails a correct export.** It expects outward stored
  normals and `cross · normal < 0`, the state of the LFInfectedBig det = +1 build. [OFFLINE MEASURED
  2026-10-01] On the three MLODs of the Rule 12 in-game probe it exits 1 on all three. That includes the one
  that renders solid and reads correctly in game (`cross.normal_positive=1.00`, `normals_outward=0.00`).
  Its fix hints ("reverse every face", "orient normals outward") would turn that model inside-out.
  [✓ in-game 2026-10-02, LFInfectedBig, chiral check below] The state this gate passes, winding in the MLOD
  order with the normals stored OUTWARD, renders solid but lit inverted (dark on the sunlit side; base
  shading on an untextured client), and so
  does the shipped LFInfectedBig; the Rule 12 build it fails renders solid and lit like a vanilla zombie. (claim: CLAIM-CHAR-NORMALS-INWARD-INGAME)
  Binarize gives all of them vanilla's winding; only the inward-normal build keeps vanilla's relation
  between stored normals and winding in the ODOL (agreement 0.2 %, vanilla zombies 0.3-0.4 %, the
  outward-normal builds 99.8 %). So store the normals inward, and until the script is updated, gate the
  export with dayz-p3d-audit "Absolute winding check": normal agreement ≈ 100 % and a negative signed
  volume by winding, the production sign. On the static probe that check passes both solid variants and
  fails the inside-out one; on LFInfectedBig it passes the Rule 12 build (99.3 %, −0.109) and fails both
  inverted ones (0.7-0.8 %). Like every winding gate, it cannot see a mirror. A double-sided
  Blender/Three.js preview never shows DayZ's single-sided culling, so a gate is still needed. Do NOT
  compare to a *debinarized* vanilla model for winding: the ODOL→MLOD converter's winding handling inverts
  the comparison.
- **Selection names LOWERCASE.** Vanilla `.p3d` selections are lowercase (`leftarm`, `pelvis`, `spine3`);
  Blender vgroups are MixedCase → `.lower()` them. (DayZ matching is case-insensitive, but match vanilla.)
- **Identity binding (py3d F1-05).** Alias `points = lod.points` BEFORE creating any `Face(lod.points, …)`
  / `Vertex(...)` and use `lod.new_selection(name)`; selection point/face keys must be the *same objects*
  in `lod.points`/`lod.faces` or their weight is silently dropped (or `write()` raises "foreign key").
- **Fractional weight byte range.** py3d encodes `w∈(0,1)` as `round((1-w)*255)+1` (read: byte 1→1.0,
  2..255→`1-(b-1)/255`). For `w ≲ 0.002` this overflows to 256 → `ValueError: bytes must be in range`.
  Clamp: `w≥0.995 → int 1`, `0.005≤w<0.995 → float`, `w<0.005 → drop` (negligible, ≤4 influences anyway).
- **Drop empty selections.** A twist/helper bone whose every weight fell below the cutoff (e.g.
  `leftwristextra`) yields an empty selection → an orphan. Skip writing any bone selection with 0 members.
- **`point.mass = None`** on the visual LOD (mass only on Geometry LOD).
- Internal decorative geometry (ChestBones) is merged into the **same** visual LOD point/face pool; its
  spine selections merge by name with the body's.
- Add a `camo` hidden-selection (all body points+faces) for `hiddenSelectionsTextures`; an internal mesh
  with its own texture gets a second hidden-selection (`camo_bone`). Non-bone selections (`camo`, proxies)
  are ignored by the skeleton matcher and do NOT explode the mesh.

**Verify offline** by debinarizing a vanilla character (`DZ\characters\zombies\*.p3d` are ODOL → use
an external ODOL→MLOD converter; selection *names* recover even though visual-LOD bone *membership* does not) and
asserting: round-trip read OK; all bone selection names ⊆ the vanilla bone-name set; 0 orphan selections;
0 points with no bone weight (zero-weight → spiky/exploded in-game); ≤4 influences/vertex; bbox Y-up with
vanilla-like proportions; winding ~0% flipped; fractional weights present and round-tripping; `left*`
centroids on +X and the front on −Z (toe and face vertices in −Z from the foot and neck). "Left and right on
opposite X" alone also passes a mirrored export. Facing plus side rule out a det = +1 map only while the L/R
selections were never swapped by hand. The `model.cfg` references `skeletonName = "OFP2_ManSkeleton"`.
The `.p3d` selections present MUST be a subset of `skeletonBones[]` or the mesh explodes; a misnamed bone
logs `Bone X doesn't exist in skeleton OFP2_ManSkeleton`.

Reference scripts (LFInfectedBig): `3dmodel\LFInfectedBig\_export\{bl_export_rig,build_p3d,verify_p3d}.py`
+ `debin_vanilla.py` (the vanilla ground-truth extractor).

**Chiral in-game check for this route [run 2026-10-02, DayZDiag 1.29.163709].** Winding gates, the bbox and
the facing test cannot see a mirror once the L/R selections have been swapped, which is how LFInfectedBig
shipped.
1. Re-export LFInfectedBig with `(x, z, y)`, faces in Blender order, negated normals and no L/R swap. Add
   one marker: an "F" in relief on the chest, weighted 100 % to `spine3`. Build the shipped recipe once
   more with the same marker as the negative control.
2. Spawn both and a vanilla `ZombieMaleBase` with the same yaw; put the camera in front of them.
3. Pass on the new build: it faces the camera like the vanilla one; no limb flings back/up over 30 s of idle
   and one attack; the "F" reads correctly; the off-centre chest hole sits on the anatomical side it has in
   the rig frame in Blender (the character's left is screen-right when it faces you). Expected on the
   control: "F" mirrored, hole on the other side.
4. Lighting: the lit side of the body is bright. (At design time the normal sign rested on Rule 12,
   measured on static models only; the result below covers a character.)

Result. LFInfectedBig was rebuilt three ways from one dump, each with the "F": Rule 12 via
`py3d.blender_to_dayz()`; the same with the normals re-negated OUTWARD; and the shipped recipe as control,
equal to the shipped p3d in every point, normal, face and selection without the marker. References: a
vanilla `ZmbM_SoldierNormal` and the player, sun from the east.
- Rule 12 build: solid, the "F" reads correctly, lit like the vanilla zombie and the player.
  check_dayz_winding.py fails it ("inside-out"); the absolute check passes it.
- Rule 12 with outward normals: solid, the "F" reads correctly, lit inverted.
- Shipped recipe: solid, the "F" MIRRORED, lit inverted.
- An AI-enabled Rule 12 build walked about 18 m with its limbs in place; the attack was not seen (it never
  engaged the player). The chest hole is centred (x ≈ 0), so step 3's hole criterion cannot show chirality
  on this model. The client ran without textures: this covers the base shading of these builds, not
  colour, `_nohq` normal maps or tangents.
- Second run the same day, same PBO, client with textures, sun from the east: an AI-enabled Rule 12 build
  spawned 2.4 m in front of the player attacked it once the player moved (a wind-up with one arm raised
  behind, then swings at the shoulder), with its limbs in place, the same moves a vanilla
  `ZmbM_SoldierNormal` made on that player. A static Rule 12 build kept its limbs in place over about 80 s
  of idle, with the "F" reading correctly; the shipped recipe looked dark, as in the first run. The
  ribcage mesh seen through the hole spans x −0.165 to +0.134 m in the Blender dump (centre −0.016 m),
  consistent with a centred hole. (claim: CLAIM-CHAR-ATTACK-INGAME)

## Failure → cause quick map

| Symptom | Cause |
|---|---|
| Posing moves nothing | armature scale not applied before bone-heat → all weights on `Pelvis`; or a live Action |
| All verts on `Pelvis` | same scale gotcha |
| Spiky / pinched verts in-game | zero-weight verts or a selection with no weight |
| Mesh explodes | selection not in `skeletonBones[]`, or wrong skeleton name in `model.cfg` |
| `Bone X doesn't exist` (RPT) | bone-name casing/underscore mismatch |
| Limbs drift during anims | mesh not in canonical bind, or baked-scale drift (accepted for 1.2×) |
| Faces / walks backward, proportions fine | det = +1 export `(x, z, −y)` sends the rig front (−Y) to +Z → re-export with `(x, z, y)` (Rule 12), not `(−x, z, y)` |
| Limbs fling back/up at idle, sane rest pose; an off-centre detail on the wrong side | mirrored export (any det = +1 map, e.g. `(−x, z, y)`) → re-export with `(x, z, y)`; an L/R selection swap only relabels the mirror |

## DayZ 1.30 Exp — bone indices and infected graphs

(hasta 1.29: `skeletons.anim.xml` listed a numeric `index` per bone; community practice treated 250 as a hard global cap.)

(desde 1.30 Exp: [CHANGELOG] the 250 global bone limit is removed. The global bone index is derived from the bone **name**, not from a value in `skeletons.anim.xml`. Most of that XML is unused; only the `lod` attribute is used, plus adding bones that were missing inside the `.xob`. `work/changelog-1.30-exp-modding.md:31,43`.)

The extracted `hermit_newbindpose.xob` block still *contains* leftover `index = "10"` style attributes (`exp/anims_cfg/DZ/anims/cfg/skeletons.anim.xml:2-16`). Do not copy those numbers into a custom skeleton — they are unused. New 1.30 skeletons name bones only; the sole remaining `index` is `EntityPosition` `index = "0"` (`ovis_gmelini_skeleton.xob` at `:986-989`, `canis_familiaris_dobermann_skeleton.xob` at `:1047-1050`). Those animal skeletons are **not** the zed bind: a custom infected still weights to the 95-bone `hermit_newbindpose.xob` subset.

Infected graph files: `infected.agr` is now an Enfusion `AnimSrcGraph` index over `.agf` subgraphs (`Locomotion.agf`, `Combat.agf`, `Interaction.agf`). See `references/dayz-1-30-characters.md`. Custom infected workspaces: open the 1.29 `.aw` in Workbench 1.30 and re-save ([CHANGELOG] tweet; converter untested).

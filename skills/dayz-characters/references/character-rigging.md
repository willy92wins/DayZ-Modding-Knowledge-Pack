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

**Stage B — py3d builder.** Critical gotchas, each verified:
- **Coordinate transform `(x, z, -y)`** for POSITIONS (det = +1). Derive it, don't guess: the imported
  armature's `matrix_world` is the leftover FBX Y-up→Z-up conversion `R(+90° X)`; the correct Blender→DayZ
  transform is `R⁻¹ = (x, z, -y)`, mapping the mesh into the *exact* space of `OFP2_ManSkeleton`'s bind
  (the rig FBX **is** that skeleton, so `R⁻¹ @ rig_blender == OFP2_dayz_bind`). Verify: bbox Y-up
  (feet≈0, head max Y) and X-width / Y-height / Z-depth proportions match a vanilla character.
  **CAUTION — the bbox check does NOT verify FACING** [✓ in-game LFInfectedBig S7 2026-06-24]: `(x,z,−y)`
  gives the right height & proportions but LFInfectedBig shipped **facing / walking BACKWARD** in-game — the
  mesh (or this transform) was 180° about the vertical axis off from the rig. Fix for that case = **`(−x, z,
  y)`** (`(x,z,−y)` composed with a 180° rotation about DayZ-up; still det +1, no winding change — apply to
  every LOD's points + the bone/memory points consistently). Before shipping, confirm the mesh faces the SAME
  way as the rig's `Male_body` in Blender; the in-game tell is "faces / walks backward". Do NOT assume
  `(x,z,−y)` is universally right — whether the 180° is needed depends on how the mesh was oriented pre-export.
- **WINDING — REVERSE IT (the recurring inside-out bug).** A Rodin/AI/GLB-sourced + Blender-retopo'd mesh
  ships with glTF-CCW winding, which DayZ renders as BACK-facing → exterior is culled, textures show on the
  INTERIOR (a Blender/Three.js preview is double-sided and NEVER shows this — only in-game or the gate below).
  The `(x,z,-y)` transform is det +1 so it does NOT auto-fix this — you MUST `face.vertices.reverse()` on
  EVERY visual face (and collision faces too: dayz-model-pipeline Rule 18 wants the collision cross INWARD).
  Do NOT trust LL-020's "det+1 → no flip" for AI/GLB-sourced character meshes — it caused a shipped
  inside-out build (LFInfectedBig S6). [✓ in-game-confirmed pipeline]
- **GATE (run before every PBO — catches inside-out OFFLINE):**
  `python references/check_dayz_winding.py <source_mlod.p3d>` (exit 1 = will render inside-out). Rule it
  encodes, validated against the in-game-confirmed inside-out build: in the SOURCE MLOD a correct visual LOD
  has `cross(v1-v0,v2-v0) · stored_normal < 0` (cross points INWARD; AddonBuilder reverses winding at
  binarize so this becomes outward/front-facing in the ODOL the engine renders). `cross·normal > 0` ⇒
  inside-out. The detector gates on this crisp sign (the "normals outward" extreme-vertex check is too noisy
  on a humanoid to gate — informational only). Do NOT compare to a *debinarized* vanilla model for winding:
  the debinarizer's winding handling inverts the comparison and will mislead you.
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
`dayz-p3d-debinarizer`; selection *names* recover even though visual-LOD bone *membership* does not) and
asserting: round-trip read OK; all bone selection names ⊆ the vanilla bone-name set; 0 orphan selections;
0 points with no bone weight (zero-weight → spiky/exploded in-game); ≤4 influences/vertex; bbox Y-up with
vanilla-like proportions; winding ~0% flipped; fractional weights present and round-tripping; left/right
bone centroids on opposite X (no mirror). The `model.cfg` references `skeletonName = "OFP2_ManSkeleton"`.
The `.p3d` selections present MUST be a subset of `skeletonBones[]` or the mesh explodes; a misnamed bone
logs `Bone X doesn't exist in skeleton OFP2_ManSkeleton`.

Reference scripts (LFInfectedBig): `3dmodel\LFInfectedBig\_export\{bl_export_rig,build_p3d,verify_p3d}.py`
+ `debin_vanilla.py` (the vanilla ground-truth extractor).

## Failure → cause quick map

| Symptom | Cause |
|---|---|
| Posing moves nothing | armature scale not applied before bone-heat → all weights on `Pelvis`; or a live Action |
| All verts on `Pelvis` | same scale gotcha |
| Spiky / pinched verts in-game | zero-weight verts or a selection with no weight |
| Mesh explodes | selection not in `skeletonBones[]`, or wrong skeleton name in `model.cfg` |
| `Bone X doesn't exist` (RPT) | bone-name casing/underscore mismatch |
| Limbs drift during anims | mesh not in canonical bind, or baked-scale drift (accepted for 1.2×) |

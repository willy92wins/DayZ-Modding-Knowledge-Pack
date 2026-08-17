# Weapon animation authoring viewer (Layer 2, interactive)

An in-sandbox, repeatable pipeline to author **weapon** animations: an
interactive Three.js viewer showing the weapon + the character on the vanilla
`OFP2_ManSkeleton`, where the user poses with IK handles + a keyframe timeline,
Claude produces an offline preview, and exports the open **SEAnim** intermediate
toward `.anm`. Built 2026-06-28. Reference implementation lives in the project
`WeaponAnimPipeline_dev/` (tools + viewer + data + README).

This is the high-value alternative to per-bone keyframing in Workbench for the
"how should the weapon be held / how should this reload look" class of task.
For vehicle-rider seated pose use the sibling `vehicle-rider-ik-pose.md`; this
doc is the general weapon/body authoring viewer.

## The pipeline

```
[1] Viewer (HTML, self-contained Three.js r128 UMD)        Claude/sandbox
      weapon + SkinnedMesh character + skeleton overlay
      IK-drag handles (hands/feet/head/weapon) + 2-bone analytic IK
      direct FK sliders (wrist roll, finger curl, torso lean, head)
      keyframe timeline (add/scrub/play/interpolate) + JSON export
[2] Offline preview (Puppeteer frame capture -> GIF)       Claude/sandbox
[3] seanim_export.py : anim JSON -> .seanim (round-trip gated)  Claude/sandbox
[4] DayZATool --generate-anim X.seanim -> X.anm            user (Windows GUI)
[5] wire in config/anim-graph + sign PBO + IN-GAME TEST    user (the real gate)
```

## Where the rig comes from (and the traps)

Source: the official BI rig FBX (DayZ-Misc) — in this environment
`C:\Users\<you>\3dmodel\LFInfectedBig\_rig\animation_rig_character.fbx`:
`Armature` with 114 `OFP2_ManSkeleton` bones (exact names) + `Male_body` mesh
(7499 v) skinned to it. Read it with Blender headless (`blender --background
--python`), not a Python FBX parser.

### [VERIFIED 2026-06-28] FBX scale/space trap (same bug that bit LFInfectedBig)

The importer leaves the **mesh at object scale `0.01`** and the **armature at
scale `1`** → mesh and armature live in **disjoint spaces** (armature in
T-pose, cm, origin at pelvis; mesh in meters, origin at feet). The armature
bones are NOT spatially coincident with the mesh; the deform "works" in Blender
only via the modifier's relative transform, and naively reading bone world
positions puts the skeleton ~35x off the mesh. Animating the raw rig pivots the
mesh around far-off points → the broken-deform symptom.

**Fix — re-bind in your own consistent space** (do NOT trust the FBX bind):
1. Read bone rest matrices in armature-world (cm) and mesh verts in mesh-world (m).
2. Both are roughly T-pose → align by **uniform scale + translation**. Derive the
   scale from a reliable correspondence: the wrist bone X vs the mesh X half-width
   (`RightHand` X ≈ −58.6 cm ; mesh X edge ≈ ±0.703 m → `s ≈ 0.0101`). Translate
   to align bbox centers; align Z by feet (mins).
3. Apply the DayZ axis fix `(x', y', z') = (x, z, −y)` (Blender Z-up → DayZ Y-up).
4. Build a fresh `THREE.Skeleton`/`SkinnedMesh` in that space; the bind is now
   self-consistent (boneInverses from the aligned rest). Skinning + IK are correct.

Result landmarks (DayZ Y-up, m): Head 1.62, Pelvis 0.99, hands ±0.59 @1.07,
feet Y≈0.09. Weapon anchor `RightHand_Dummy`=`Weapon_Root`=(−0.156, 1.368, 0.207).

Helper "bones" (`RightHand_Dummy`, `Weapon_Root`, `LeftHand_Dummy`, IK helpers)
are **empties** in the FBX, parented to bones; read their world via the
child-of-bone formula `arm_w @ pose_bone.matrix @ T(0,bone_len,0) @
matrix_parent_inverse @ matrix_basis` (plain `matrix_world` returns 0 before a
depsgraph update, and even after for bone-parented empties).

## ⚠️ [VERIFIED 2026-06-28] Bone-frame convention gap — why in-game is the gate

The viewer's exported quaternions are **rig-local** = Blender bone-local (bone
points **+Y**). DayZ's `.anm`/SEAnim bone-local frame points the bone **+X** —
proven from a DayZATool-extracted vanilla SEAnim (`aks74u_reference.seanim`):
finger phalanx local offsets are `(length, 0, 0)`. A global change-of-basis does
NOT reconcile them (tested: best-fit relative error 0.88), so the per-bone frames
differ by per-bone rotations that are **not derivable offline** from a partial
(hands-only) reference. This is the `[TBD-verify]` the skill always flagged:
**there is no offline shortcut; only the in-game test verifies the convention.**

Consequence: a SEAnim emitted straight from the viewer is structurally valid
(round-trips; bone names = `OFP2_ManSkeleton`; fps correct) and geometrically
correct in the rig, but its rotation convention vs DayZ is NOT guaranteed.
Close it the way the skill always prescribed: `DayZATool --extract-anim` a
near-vanilla `.anm` → SEAnim, feed as `--rest-pose` for rebasing, and iterate
in-game. Plan the rest-pose round-trip from day one.

SEAnim local translations are in **cm** (rig meters × 100) — also from the
reference offsets.

## Viewer architecture (for maintenance)

- `THREE.SkinnedMesh` + `THREE.Skeleton` built by hand from the rig JSON (bone
  local pos+quat, hierarchy; mesh verts + 4-weight skinIndex/skinWeight).
- **Analytic 2-bone IK** per limb (law of cosines + pole hint) — same math as
  `ik_pose_to_seanim.py`; ported to JS and applied by *aiming* each bone's rest
  child-direction at the solved child world position (preserves rest roll),
  setting `bone.quaternion = parentWorldQuat⁻¹ · desiredWorld`. The viewer reads
  `bone.quaternion` (local) directly for export — so the
  `positions_to_local_rotations` stub in `ik_pose_to_seanim.py` is NOT needed on
  this path.
- Direct FK as **post-multiply** on the IK result (`bone.quaternion.multiply(
  axisAngle)`) so wrist-roll/finger-curl layer on top of IK instead of resetting
  to rest. The IK helpers do not roll the wrist (skill-verified) → wrist + finger
  control is raw `LeftHand/RightHand` + finger bones.
- Three.js libs are **inlined** (no CDN) → offline + dodges the R1 CDN-404 trap.
- Keyframes store the *authoring state* (target positions + slider values + weapon
  transform); playback/export interpolates state then re-runs IK/FK and bakes
  per-frame per-bone local quats. The IK/FK is the single source of truth.

## Stale-doc corrections (apply on output)

- `seanim_writer.py` **does ship a working `read_seanim`** — the
  `ik_pose_to_seanim.py` `load_rest_pose` docstring that says "SEAnim reader not
  yet implemented" is stale. Use `seanim_writer.read_seanim` to load a rest pose.
- A verified Python SEAnim **reader+writer** exists; `.anm` write still does not
  (DayZATool only).

## Reusable tools (project `WeaponAnimPipeline_dev/tools/`)

`fbx_extract.py` (Blender headless rig dump) → `build_rig_dayz.py` (align +
DayZ-space rig JSON) ; `extract_weapon.py` (py3d weapon mesh+memory points) ;
`build_viewer.py` (generates the self-contained HTML) ; `selftest.js` /
`capture.js` (Puppeteer self-test + preview capture) ; `seanim_export.py`
(anim JSON → SEAnim, round-trip gated). Paths are set at the top of each script.

## The wall (unchanged)

Only one mod modifying player/creature animations can load at a time; a weapon
animation mod conflicts with every other anim-mod on the server. State it on
every plan.

## (added 2026-07-05) Viewer state after the finger/gizmo/hyperext pass + grip authoring

The viewer moved well past the 2026-06-28 v1 above. Current deployed state
(`viewer/weapon_anim_viewer.html`; verified: Codex R22 v1->v4 APPROVE + v5 absolute
sliders; polish-verify 12/12; self-test 47 checks PASS):

- Rig: the JD Master Rig (`_DayZ_Character`, 151 bones, mesh `zMale_body`, scale 1)
  -- NOT the 114-bone FBX above (which had the disjoint-space bug). Data `data/jd_dayz.json`.
- Start pose = the real in-game grip, read off the live skeleton with a bone-dump
  (`GRIP_VARIANT='ingame_exact'`, `data/pose_grip_ingame_exact.json`): hands/fingers
  0-0.4 cm from in-game; the elbow is the IK-resolved in-game elbow (not derivable offline).
- Absolute finger sliders per finger + thumb (0 = open hand, 100 = fist/grip; thumb 100 =
  slerp toward the in-game aim grip). Baked into `basePoseQ`, not a re-applied layer.
- Hyperextension guard live (elbow/knee = signed flexion-plane angle, `HINGE_MAX=178`;
  wrist = quat magnitude) -> red joint dot + `info` warning.
- Editing: universal FK-by-bone (click a joint dot -> gizmo, sized 0.35 for phalanges),
  move-all (root group), undo/redo, mirror L<->R, filterable 151-bone list. Weapon
  rigidly follows the right hand (`weaponRel`).
- Two export routes to `.anm` (both round-trip-verified offline; in-game is the gate):
  - Route A (canonical): `tools/txa/dump_viewer_world.py` + `viewer_to_txa_via_plugin.py`
    -> `.txa` -> Workbench -> `.anm`. Handles root motion. USE THIS FOR THE GRIP.
  - Route C (CLI): `tools/seanim_export.py` -> `.seanim` -> `DayZATool --generate-anim
    <f>.seanim 100` -> `.anm`. Rotations + rest only. The viewer->seanim quat convention
    `(-vy,-vz,vx,vw)` is exact on fingers but `LeftHand` does NOT obey it (separate wrist
    process) -> do not use Route C for the support-hand wrist. Route C is also NOT valid
    for full-body action anims (jam/unjam/melee): the A6_SR2M golpe (2026-06-30) confirmed
    full-body goes Route A (JD plugin -> `.txa` -> Workbench Register&Import -> `.anm`).
    Use Route C only for weapon-bone/partial tracks.

### Authoring a weapon GRIP with the viewer (verified in-game on the SR2M)

The grip is fixed by three levers, NOT by "posing the wrist" (weapon-in-hands :90-140):
(1) firearms behavior + an ikpose; (2) geometric parity -- move the WEAPON to where the
ikpose lands the hand (the SR2M fix was +2.4 cm), via `placeWeaponOnHand` / the "Arma"
gizmo; (3) finger curl (the one hand thing the ikpose drives visibly). The viewer serves
levers 2 and 3; rotating `LeftHand` in the ikpose is near-inert. Step-by-step guide:
`WeaponAnimPipeline_dev/reviews/2026-07-05-flujo-agarre-con-visor.md`.

### A native "ikpose mode" is non-trivial (design spec on file)

A real ikpose keys 8 IK bones the viewer's "No IK Bones" rig lacks --
`{Left,Right}HandIKTarget`, `...HandOrigin`, `...ForeArmDirection`(+`Origin`) -- plus
fingers + `_Dummy` (verified from `sr2m_grip.seanim`, 43 bones). A usable export must
SYNTHESIZE those 8 targets from the viewer FK pose. ROI is dubious (working mods reuse
vanilla ikposes + geometry). Design + open questions:
`WeaponAnimPipeline_dev/reviews/2026-07-05-spec-modo-ikpose.md`.

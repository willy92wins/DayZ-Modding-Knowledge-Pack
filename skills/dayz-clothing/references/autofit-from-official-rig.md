# Auto-fit a garment on the OFFICIAL DayZ rig (joint landmarks + weight donor)

Harvested 2026-09-01 from the Blender 3.6 pack "DayZ Model Tools CZ" 1.16.4 (triage note:
`<vault>\AI\30_Sessions\2026-09-01-DayZ_Tooling-dayz-model-tools-pack-triage.md`).
Scope: headless Blender 5.1 driven through `execute_blender_code`; no panels, no operators of the
pack. Labels: **[EXACT]** measured on this host; **[DESIGN]** logic read from the pack or written
here, not yet run end-to-end on a real garment; **[ASSUMPTION]** stated, unverified;
**[RUN 2026-09-01]** executed on a real jacket (Hunyuan3D shell, 1.35 M tris decimated to 100 k)
in Blender 5.1.1 headless, two Grok rounds; evidence in
`<vault>\AI\30_Sessions\reviews\2026-09-01-dayz-model-tools-pack\jacket-test\`.

**Read this first (result of the run).** Sections 3, 4, 5 and the corridor mask of 6 work as
written and the mechanical gate (7) passes on the exported p3d. What the run REFUTED is the idea
that a garment modelled with hanging sleeves can be put on the A-pose body by fitting alone:
neither the uniform fit (sleeves stay on the torso) nor a rigid per-sleeve rotation (aligns the
sleeve axis to 7 degrees but stretches fabric membranes between sleeve and flank, because on such
garments the inner sleeve is fused to the torso) gives an acceptable mesh, and the gate does not
see either failure. Two ways out, in order: (a) author or obtain the garment ALREADY in A-pose
(sleeves ~50 degrees from vertical, i.e. matching the rig's arm axis); (b) for a hanging-sleeve
garment, do the pose-match skinning of section 6b instead of any rotation. A render review of
the fit is mandatory before the weight transfer; the gate alone is not enough.

**Round 3 (same day): the A-pose route is NOT reachable with SDXL -> Hunyuan.** Nine SDXL
ghost-mannequin concepts (two prompt variants, A-pose stated first, CLIP-safe length) gave
sleeves 15-30 degrees from vertical at best; the one spread garment was a short batwing. Run
through the unchanged round-1 pipeline (no rotation, orchestrator-run, 16 s in Blender): gate
a-g and (i) PASS (sleeve weight 92 % on arm bones, 0 unweighted, 0 bleed, no membranes), (h)
FAIL at 28.8 / 27.2 degrees and cuffs 0.23 m short of the hand: a true positive of the
garment's geometry, so the pipeline is validated end-to-end and (h) discriminates. For a real
A-pose garment use a downloaded/authored one, or use section 6b, which handles any sleeve angle.
The 12-degree / 0.08 m thresholds of (h) are the orchestrator's choice, not an in-game
measurement [ASSUMPTION].

**Round 4 (2026-09-02): section 6b run on the hanging-sleeve jacket, and it ALSO fails on this
mesh.** Posing the rig onto the sleeve axis works (0.02 degrees), the anti-double-transform bind
sequence works, (h) passes (7.4 / 8.2 degrees, cuffs 7 cm), but (i) fails (61 / 59 % of sleeve
weight on arm bones) and the new edge-stretch criterion (j) fails (max edge 6.5x): the same
membranes as round 2, now at the mask boundary. Mechanism, measured by the worker: with the rig
posed arms-down, the donor's arm occupies the same volume as the flank, so a proximity transfer
paints arm weights on the flank too; restricting the posed weights to the sleeve mask moves the
tear to the mask edge. On a closed AI shell where sleeve and flank are one continuous surface
there is no proximity- or mask-based partition that does not tear. Conclusion for the skill: a
garment whose sleeves are fused to the torso needs TOPOLOGICAL separation (a seam, a cut at the
armpit, or separate sleeve parts) before any pose-match; that is authoring, not fitting. What
the four rounds did validate: sections 3-5 and 7 as a pipeline, and (j) as a membrane detector.

## 0. What replaces what

| pack piece (`addon.py`) | why not | replacement |
|---|---|---|
| `_load_local_dayz_player_rig` 3880-3924 + `_real_dayz_rig_landmarks` 3853-3876 | needs the external `DayzAnimationTools.import_xob` and a hard-coded `P:\DZ\characters\bodies\player_testing.xob`; that XOB is a TEST skeleton with `To Be removed` bones (dayz-animation-pipeline/references/player-skeleton.md:88-92) | bone heads of `animation_rig_character.fbx` (section 1, 3) |
| donor `resources\DayzSkeleton.p3d` (`_ensure_builtin_reference` 1649-1673) | single visual LOD, 44 lowercase groups, 1,517 of 10,153 verts with zero weight, sums not normalised; embeds vanilla `m_adam` textures/rvmats (licence); the pack decodes weights with its own table (`weight_decode` 225-231), not the py3d codec | `Male_body` of the same FBX: 0 unweighted verts, <=4 influences (section 1, 5) |
| `to_bl`/`from_bl` = `(x, z, y)` + `rev()` 219-221 | it is the rig-frame convention, NOT our worn-export frame | section 2 |
| `_apply_autofit_armature(..., apply=True)` 3213-3287, run by default in `clothing_prepare` 4454-4457 | destructive bone-heat sleeve warp; the panel says it does not run (4828) and the code runs it | do not port; sleeve detection as a mask only (section 6) |

## 1. The reference rig [EXACT: Blender 5.1.1 / Python 3.13.9, headless, 2026-09-01]

- File: `C:\Users\<you>\3dmodel\LFInfectedBig\_rig\animation_rig_character.fbx` (official,
  `BohemiaInteractive/DayZ-Misc` "Rig and Animations"; download recipe in
  dayz-characters/references/character-rigging.md:12-23).
- Import: `bpy.ops.wm.fbx_import(filepath=FBX)` (5.x native importer; `import_scene.fbx` also
  still exists). Result: object `Armature` (114 bones, object scale 1.0, **bone heads already in
  metres**), object `Male_body` (object scale 0.01, parented to `Armature` with an Armature
  modifier, world dims 1.406 x 0.390 x 1.799 m, feet at z = 0), 38 empties (`*_Dummy`,
  `Weapon_*`, `EntityPosition`: ignore).
- Because the heads come in metres, the "bake the armature scale" step of
  character-rigging.md section 1 (written for the legacy importer, armature at 172 units) is not
  needed for landmarks. It IS still needed if you bone-heat your own mesh against this armature
  at another size.
- **Bone tails are garbage after import** (Pelvis tail 11 m away, arm tails 10 m+). Use
  `bone.head_local` only; never `tail`, `length` or `vector`.
- Frame: Z up; anatomical LEFT = +X (`LeftArm` head x = +0.160, `LeftHand` x = +0.586);
  FRONT = -Y (`LeftToeBase`/`RightToeBase` heads sit 0.135 m in -Y from the `*Foot` heads).
- Arm chain heads, world, metres (Right side = same with x negated):

  | bone | head (x, y, z) |
  |---|---|
  | LeftShoulder | (0.010, -0.020, 1.390) |
  | LeftArm | (0.160, 0.010, 1.430) |
  | LeftArmRoll | (0.309, 0.057, 1.305) |
  | LeftForeArm | (0.376, 0.078, 1.249) |
  | LeftElbowExtra | (0.380, 0.079, 1.246) |
  | LeftForeArmRoll | (0.532, 0.074, 1.117) |
  | LeftWristExtra | (0.579, 0.073, 1.078) |
  | LeftHand | (0.586, 0.073, 1.072) |

  Spine heads z: Pelvis 1.000, Spine 1.030, Spine1 1.060, Spine2 1.137, Spine3 1.235,
  Neck 1.490, Neck1 1.565, Head 1.620. A-pose: the upper arm drops about 40 degrees
  (shoulder to elbow: dx 0.216, dz -0.181).
- Name mapping: the 44 lowercase group names vanilla worn p3ds and the pack use (`leftarm`,
  `leftforearmroll`, `lefthipextra`, ...) map 1:1 onto bones by `bone.name.lower()` (44/44).
- `Male_body`: 7,499 verts, 14,936 faces, 111 vertex groups named like the bones
  (PascalCase: `RightArm`, `Spine3`, `Pelvis`), max 4 influences per vertex, 0 zero-weight
  vertices.

## 2. Axes: the rig frame is NOT the worn-export frame [EXACT + doctrine; lesson LL-413]

- Our worn tooling maps DayZ -> Blender with `(x, -z, y)` (`references/export_clothing_fbx.py:12-13`):
  the body stands Z-up FACING +Y with left at +X (SKILL.md, CANONICAL WORN FRAME: -Z chest,
  +X left, +Y up). The official rig faces -Y with left at +X. The two Blender frames differ by
  the reflection `y -> -y`, not by a rotation. [EXACT] cross-check on a DayZ-frame body (the
  pack's `DayzSkeleton.p3d`, read with py3d 1.5.0): `lefttoebase` centroid sits 0.147 m in -Z
  from `leftfoot`, `head` 0.030 m in -Z from `neck`, `leftfoot` at x = +0.167: front -Z, left +X.
  `(x, -z, y)` puts those toes at +Y; the swap `(x, z, y)` puts them at -Y, i.e. onto the rig.
- Consequence: a garment fitted on `Male_body` returns to DayZ with the pure swap
  `(x, y, z)_blender -> (x, z, y)_dayz` AND face-order reversal in every LOD (the det = -1 rule,
  dayz-model-pipeline/references/lods-and-geometry.md:146-148). That is exactly the pack's
  `from_bl` + `rev()`. Do NOT apply `py3d.BLENDER_TO_DAYZ` = `(x, z, -y)` to it: that is the
  det = +1 route for meshes authored in our +Y-facing frame. dayz-characters hit this on the
  same rig: `(x, z, -y)` shipped LFInfectedBig walking backwards and a residual mirror
  (character-rigging.md:169-175; dayz-characters/SKILL.md:167-192).
- Alternative that keeps every existing clothing script unchanged: mirror the rig into our frame
  first (`y -> -y` on `Armature` and `Male_body`, then reverse `Male_body` face order), fit
  there, export with `BLENDER_TO_DAYZ`.
- [ASSUMPTION] Which of the two is less error-prone in practice. Neither has been run on a real
  garment yet; in both cases run the anatomical facing test of SKILL.md CANONICAL WORN FRAME on
  the exported p3d before packing (killer #2).

## 3. Landmarks: replacing `_real_dayz_rig_landmarks` [RUN 2026-09-01: works; mirrors addon.py:3853-3876]

```python
def arm_landmarks(arm, side):
    """Shoulder joint, elbow, wrist of the official rig; world space, metres."""
    p = "Left" if side == "L" else "Right"
    b = arm.data.bones
    upper = b[p + "Arm"]
    elbow = b.get(p + "ForeArm") or b[p + "ElbowExtra"]
    wrist = b.get(p + "WristExtra") or b[p + "Hand"]
    W = arm.matrix_world
    return W @ upper.head_local, W @ elbow.head_local, W @ wrist.head_local
```

Drops the pack's `scene.dayz.clothing_armature` lookup and its `dayz_real_player_rig` flag;
the centroid fallback `_reference_arm_landmarks` (1844-1875) becomes unnecessary.
`_reference_arm_radius_profile` (1875) samples the reference MESH around that axis: feed it
`Male_body` and its `matrix_world` (the 0.01 object scale lives inside the matrix).
[RUN 2026-09-01] Works as written; heads matched `probe_rig_fbx.json` to 1 mm; arm length
shoulder-elbow-wrist = 0.565 m per side. `WristExtra` vs `Hand` differ by 7 mm: irrelevant.
Blender 5.1 has no `Mesh.calc_normals_split`: read `vertex.normal` and recompute face normals
after the axis swap.

## 4. Region bbox + uniform fit [RUN 2026-09-01: works for the torso, cannot move sleeves; addon.py:21-31, 1629-1638, 1700-1748]

- Region groups per garment type: `CLOTHING_REGION_GROUPS` (JACKET, SHIRT, VEST, PANTS, BOOTS,
  GLOVES, BACKPACK, HEADGEAR, MASK), lowercase names; match `Male_body` groups by `.lower()`.
- `_reference_region_bbox`: world bbox of the `Male_body` vertices weighted > 0.02 in any group
  of the region.
- `_fit_objects_to_reference`: ONE uniform factor for all parts of the garment (multi-part
  OBJ/FBX are measured together): `0.82 * height_ratio + 0.18 * secondary`, where `secondary`
  is whichever of the X or Y ratio is closest to 1 (`argmin |log r|`, addon.py:1721-1722), for
  JACKET/SHIRT/VEST/BACKPACK/PANTS (median of the three ratios otherwise), times `margin`
  (pack UI default 1.06; function default 1.02). Then translate so the garment's top edge sits
  on the region's top edge (bottom edge for BOOTS). No vertex warping at all.
  [RUN 2026-09-01] Works as written. JACKET region bbox of `Male_body`: lo (-0.603, -0.134,
  0.945), hi (0.603, 0.143, 1.611); factor 0.424 with margin 1.04 on the Hunyuan jacket; collar at
  the neck, hem mid-thigh, front offset 0.035 m towards -Y. What it cannot do: a garment with
  hanging sleeves stays 0.69 m wide against a 1.21 m A-pose region, so the sleeves end up beside
  the torso, not on the arms (`02_fit_front.png`).
- Rest forward offset (`_set_clothing_rest_forward_offset` 1608-1621): translate along the body's
  FRONT vector by `offset` (pack default 0.035 m), stored on the object to avoid accumulation on
  repeated fits. On the official rig the front vector is world `(0, -1, 0)`; in our +Y frame it
  is `(0, +1, 0)`.

## 5. Weight transfer from `Male_body` [RUN 2026-09-01: works in Blender 5.1.1 with the three corrections of item 7]

1. Remove foreign deform groups from the garment (`_remove_foreign_deform_groups` 4036-4065):
   anything that is neither a bone name nor a named selection (`camo*`, `zbytek`,
   `hiddenSelection*` stay).
2. Create the destination groups by name (`_copy_reference_vgroup_names` 3781), then a
   `DATA_TRANSFER` modifier on the garment: `object = Male_body`, `use_vert_data = True`,
   `data_types_verts = {'VGROUP_WEIGHTS'}`, `vert_mapping = 'POLYINTERP_NEAREST'`,
   `layers_vgroup_select_src = 'ALL'`, `layers_vgroup_select_dst = 'NAME'` (addon.py:4110-4118).
   Apply with `bpy.ops.object.modifier_apply(modifier=name)` inside
   `bpy.context.temp_override(object=g, active_object=g, selected_objects=[g])`; headless there
   is no active object otherwise.
3. Cleanup (`_cleanup_weights` 4127-4155): per vertex keep the top <= 4 bone groups with
   weight >= 0.005, drop the rest, renormalise to 1.0; touch only bone-named groups so named
   selections survive. Better than Blender's global Clean/Limit Total for that reason.
4. Add what the pack lacks: cross-midline cleanup (`left*` weight on the right half and vice
   versa; character-rigging.md:108-117) and the two counts of section 7.
5. Export with py3d: group names to lowercase (character-rigging.md:192); the byte encoding is
   py3d's `round((1-w)*255)+1` (character-rigging.md:196), never the pack's `weight_encode`
   table (addon.py:233-238).
6. The in-game skeleton is still `DayzTemporarySkeleton` with the 159-pair template (killer #3
   in SKILL.md); the rig only generates weights. The 44-name set is what vanilla worn items
   actually weight (SKILL.md:60-63): more bones is fine, fewer works but articulates coarsely.
7. [RUN 2026-09-01] Steps 2-5 work in Blender 5.1.1 (`modifier_apply` under `temp_override`
   applied first time; 111 groups transferred). Three corrections found by the run:
   - Restrict the "bone-named groups" of step 3 to the deform set of character-rigging.md
     section 2 (no `Face_*`, eyes, tongue, fingers): otherwise a collar ends up weighted to
     `face_jawbone`.
   - py3d's byte encoding quantises weights: sums come back 0.996-1.004 after the p3d
     round-trip, so the gate tolerance is +-0.01, not exact 1.0.
   - The empty Geometry LOD (1e13, `autocenter=0`) makes `python -m py3d validate` raise
     `ERR_COMPONENT_NAMING` unless it carries an empty `Component01` selection (0 points).
     Adding it satisfies the validator; whether vanilla worn p3ds carry it is [ASSUMPTION].
   Result on the test jacket: 49,994 verts, 0 unweighted, max 4 influences, 0 midline bleed,
   34 of the 44 selections populated.

## 6. Sleeve detection: mask only [RUN 2026-09-01: corridor mask works; rigid rotation REFUTED]

`_find_disconnected_sleeve_component` 2245, `_find_sleeve_by_reference_corridor` 2294,
`_auto_source_sleeve` 2358 and `_auto_assign_both_sleeves` 2480 are reusable to tag
`DAYZ_SLEEVE_L/R` vertex groups (corridor = 0.19 x arm length around the section 3 axis) for the
alignment viewer. Do not port the heuristic warp that follows (`_apply_autofit_armature`
3213-3287) as it is: the pack's own README admits wrong-sleeve detection (README_AUTOFIT_1_9.md,
"Kdyz automatika oznaci spatny rukav") and `_filter_plausible_arm_fields` (2927-2955) silently
continues with one arm.

[RUN 2026-09-01] On a closed AI shell the wrist-seed flood found 0/2 sleeves (no open cuffs);
labelling the whole corridor found 2/2 (4,582 / 4,468 verts with the A-pose axis; 12,659 /
12,346 with a corridor around the garment's own hanging-cuff-to-shoulder axis, which also
captures flank vertices). A RIGID rotation of the masked sleeve about the `*Arm` head onto the
rig axis (pack v4 logic, addon.py:2720-2809, blend `smoothstep(0.05, 0.22)` of the arm length at
the root, axial scale 0.75) reached 7.2 / 7.6 degrees and cuffs 4.7 / 4.6 cm from the hand,
but tore the mesh: flank vertices inside the corridor rotated with the sleeve and stretched
into fan-shaped membranes between sleeve and torso (`02b_fit_front.png`, `02b_fit_iso.png`).
Verdict: rigid rotation is unusable on garments whose sleeves are fused to the torso, and the
gate cannot detect the membranes. Do not ship a fit without looking at the render.

## 6b. Hanging-sleeve garments: pose-match skinning instead of rotation [RUN 2026-09-02: mechanics work, still tears on a fused AI shell]

This is the pack's v5 idea (`_apply_autofit_armature`: bind in the garment's pose, then move
the rig to REST) made deterministic with the measured axes, and it is the only route that moves
the sleeve with a proper skinning falloff instead of a cut:

1. Measure the garment's sleeve axes from the corridor mask (shoulder root, PCA axis, cuff).
2. Pose the official `Armature` in Pose Mode so that `LeftArm`/`RightArm` chains follow those
   axes (rotate the arm bones about the shoulder; keep the rest of the rig untouched).
   `Male_body` follows through its Armature modifier, so the donor body is now arms-down too.
3. Transfer weights from the POSED `Male_body` (section 5, evaluated mesh) and clean them.
4. Bind the garment to the armature in that pose (Armature modifier, parent inverse), then
   return the armature to its rest pose: the skinning carries the sleeves to the A-pose with
   weight falloff at the shoulder instead of a rigid seam.
5. Apply the Armature modifier (bake), run the gate (7) including (h) and (i), review renders,
   export via section 2.
Expected failure to watch for: flank vertices weighted to arm bones (the corridor problem in a
different form); the cross-midline and per-bone-share checks of the gate catch part of it,
the render catches the rest. Cheaper alternative: regenerate the garment in A-pose upstream.

[RUN 2026-09-02, worker notes] Rotate the `*Arm` pose bone about its world HEAD with
`pose_bone.matrix` (never `bone.vector`/`tail`: tails are garbage after import); one rotation of
`*Arm` was enough (ForeArm untouched), residual 0.02 degrees. Bind sequence that avoids the
double transform: record the rest world matrices of the 18 arm-chain bones BEFORE posing;
`bpy.ops.pose.armature_apply`; add the Armature modifier + parent inverse; set the chain back to
the recorded matrices parent-first with `view_layer.update()` between bones; apply the modifier.
The posed donor paints arm weights on the flank (hanging arm = flank volume), so the worker
blended posed weights inside `DAYZ_SLEEVE_*` with rest-pose weights outside; the tear then
appears at that boundary (see the round-4 note at the top). On this mesh the route is refuted,
not the mechanics.

## 7. Gate before trusting a fit [DESIGN]

- 0 zero-weight vertices; every vertex weight sum = 1.0 +- 0.01; max 4 influences;
  `left*`/`right*` bleed across the midline = 0.
- Facing: the anatomical test of SKILL.md CANONICAL WORN FRAME on the exported p3d (front
  detail at -Z, `left*` centroids at +X). Measured on the test jacket: `left*` centroid
  x = +0.16 (fit only) / +0.25 (sleeves on arms); spine/pelvis-weighted z = -0.040 / -0.059
  (vanilla -0.04..-0.08); garment y in [0.77, 1.61].
- Sleeves on arms (added after the run): (h) angle between each sleeve's principal axis and the
  rig's `Arm -> Hand` axis <= 12 degrees, and the cuff centroid (10 % of sleeve verts farthest
  from the shoulder) <= 0.08 m from the `Hand` head, both in the DayZ frame; (i) >= 70 % of the
  weight of the sleeve vertices on arm bones (`*arm*`, `*forearm*`, `*hand`, their roll/extra),
  not on `spine*`/`*shoulder`. Implemented in `jacket-test\round2\gate_fit.py`.
- Membranes / torn fabric (added 2026-09-02, criterion j): on the exported visual LOD, edge
  lengths after the fit vs the fitted-but-unposed garment: p99 ratio <= 1.3 and max ratio
  <= 2.0. Calibrated on the round-2 p3d (membranes): p99 1.31 and max 6.15 -> FAIL; the
  pose-match round: max 6.53 -> FAIL. It is the only mechanical check that sees the tears.
- (h)-(j) still do not see a sleeve sitting beside the torso without stretching: look at an
  orthographic front render with `Male_body` overlaid before trusting any of them.
- Then the in-game gate of SKILL.md BUILD step 5 (spawn -> equip -> move). A worn item cannot be
  validated offline-only.

## 8. Provenance

- Pack: `C:\Users\<you>\Downloads\dayz_model_tools.rar` (v1.16.4, MIT code; its `resources\*.p3d`
  reference Bohemia assets). Line numbers above are its `addon.py`.
- Triage note and the three Grok lane reports with verified citations:
  `<vault>\AI\30_Sessions\2026-09-01-DayZ_Tooling-dayz-model-tools-pack-triage.md`
  and `<vault>\AI\30_Sessions\reviews\2026-09-01-dayz-model-tools-pack\`.
- Rig measurements: `probe_rig_fbx.json` and `probe_rig_front.log` in that reviews folder
  (`rig-probes\`), produced by `blender.exe -b --python` on Blender 5.1.1.
- Real-jacket run (two Grok rounds, 2026-09-01): `jacket-test\` in the same reviews folder:
  SDXL concepts and the prepared cutout, Hunyuan GLB check, `round1\` and `round2\` with the
  worker scripts (`autofit_jacket.py`, `build_p3d.py`, `gate_fit.py`), metrics JSON, gate outputs,
  `07_skill_feedback.md` and the fit renders. The p3d files stay in the session scratchpad only.

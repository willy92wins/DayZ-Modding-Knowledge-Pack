# Rig bind-pose check

Why a rig's rest pose has to be the game's, how to extract the game's
bind pose as an SEModel, and how to run `scripts/bind_pose_check.py`
against it. The measured case is a third-party Rigify template with no
author name (none was given): every local but 32 matched, and the rig
was still turned 180 deg about world Z in its roots.

## Why it matters

[EXACT][CLAIM-ANIM-BIND-EXPORT-ABSOLUTE] The DayZ plugin's exporter writes absolute local
transforms and switches every constraint off before sampling
(`references/weapon-anim-blender-complete.md:989`), so the rest pose of the deform armature
is what reaches the game: a rig whose rest locals differ from the bind pose exports
that difference into every animation. The preview mesh deforms from that same Blender
rest pose, not from the game's bind pose, so the preview cannot show a difference between
the two; it shows once the export plays in game (deduced, not measured).

A local check alone can miss a turned rig: the game's root is not
compared, and a bone whose game parent is absent from the rig and
which is a root there is not compared either, so a rig can match every
compared local and still sit turned in armature space. That is why the
tool also compares the three armature roots of a `jd` rig.

## Get the SEModel and run the check

The bind pose model is extracted from the player model as described in
`references/player-skeleton.md`: `DayZATool.exe --extract-mdl
DZ\characters\bodies\player_testing.xob` writes `player_testing.semodel`,
whose header (`magic[7]="SEModel"`, `boneCount` uint32 at 14, names
from offset 29, one 73-byte record per bone) the tool reads.

    blender -b rig.blend --python scripts/bind_pose_check.py -- --semodel player_testing.semodel [--armature _DayZ_Character] [--tol-deg 0.05] [--tol-mm 0.01] [--report out.json]

Exits: 0 pass; 1 fail (a local or a root over tolerance, a parent
mismatch, a non-finite number); 2 input error (a missing file or
armature, an unreadable SEModel, a rig frame that cannot be read, a
`--report` path that is an input); 3 the tool itself crashed. The
report JSON carries `compared`, `max_deg`, `max_mm`, `over`,
`parent_mismatch`, `absent_in_armature`, `not_compared`,
`roots_compared`, `roots_over`, `roots_missing` and `non_finite`.
`--report` never replaces the loaded `.blend` or the SEModel: such a
path is refused with exit 2 and the input is left byte for byte.

The bone-frame map is the one of `scripts/seanim_export.py`
(`seanim_rot`, `seanim_pos_cm`, `detect_rig_frame`), imported, not
copied, and a rig whose frame cannot be read is refused. With a `jd`
rig, `Pelvis`, `EntityPosition` and `Collision` are compared in
armature space with the JD Master Rig constants in the script (the
rotation against `--tol-deg`, the head against `--tol-mm`); a root
over tolerance fails and is listed apart from the locals, a root
missing from the rig is listed and does not fail. With an `fbx` rig
the roots are not compared and the report says so.

[EXACT][CLAIM-ANIM-BIND-DOUBLE-PRECISION] Every angle and distance is
computed in double precision from Python floats copied out of the
inputs. Measured on 2026-11-19: mathutils stores and computes in
float32, where a quaternion dot product cannot resolve turns below
about 0.03 deg (one float32 step below 1.0 is 0.0396 deg), next to the
0.05 deg tolerance; the tool therefore never compares a mathutils
quaternion or dot product, and reads each SEModel record's 17 floats
and each rig matrix entry for finiteness before any comparison.

## The measured case (2026-11-18 and 2026-11-19)

[EXACT][CLAIM-ANIM-BIND-TEMPLATE-32] On the original template the bind
check compared 144 bones and found 32 over tolerance, maximum
36.6195 deg and 0.2996 mm (`RightArm`): `RightArm` 36.6195 deg,
`LeftArm` 14.5557, `RightForeArm` 13.6014, `RightHand` 10.0609,
`RightArmRoll` 9.3650, `RightForeArmRoll` 8.9203, `LeftForeArm`
4.2199, `LeftHand` 4.1867, `LeftArmRoll` 3.7956, `LeftForeArmRoll`
3.7945, `LeftUpLeg` 0.5912, `RightUpLeg` 0.5910, `LeftHandRing2`
0.5063, `RightHandRing2` 0.5062, `RightHandRing3` 0.5014,
`LeftHandRing3` 0.5014, `LeftHipExtra` 0.2958, `RightHipExtra` 0.2954,
`RightHandThumb2` 0.2541, `LeftHandThumb2` 0.2541,
`Face_BrowFrontRight` 0.0626 and `Face_BrowFrontLeft` 0.0587 deg; and
by position `LeftHandIndex3` 0.0732 mm, `RightHandMiddle3` 0.0477,
`LeftHandMiddle3` 0.0430, `RightHandMiddle2` 0.0413,
`LeftHandMiddle2` 0.0350, `RightHandIndex2` 0.0121, `LeftHandIndex2`
0.0113, `RightHandIndex3` 0.0740, `Spine2` 0.2956 and
`RightHandThumb3` 0.0135 mm. `LeftHandIK` and `RightHandIK` were
missing in the rig (listed, out of scope); `Scene_Root` (the game
root) and `Pelvis` (its game parent absent there) were not compared.
The JD rig passed: 146 compared, maximum 0.0347 deg and 0.0004 mm.

[EXACT][CLAIM-ANIM-BIND-ROOT-TURN] Every other local matched, and the
template was still turned 180 deg about world Z against the JD rig:
in the rest pose exported with the plugin, `Pelvis` was 179.9999 deg,
`EntityPosition` 120 deg and `Collision` 120 deg off the JD rig's, and
the preview mesh was the JD rig's mesh turned 180 deg about Z and
about 1 cm off ((+0.8629, +9.8721, 0) mm in Blender axes, residual
0.0084 mm). A rig can therefore match all its compared locals and be
turned in the root; the in-game effect of that turn is deduced, not
measured.

[EXACT][CLAIM-ANIM-BIND-FIX-RESULT] The fix turns the whole template
with `Armature.transform`, because `EditBone.transform` bone by bone
was measured to leave 34 Rigify bones of the metarig up to 1.4 m off
their twins on connected chains and to break a control. On the fixed
copy the bind check compared 144 bones with maximum 0.0313 deg and
0.009 mm; the mesh sat within 0.0084 mm of the JD rig's; and the
plugin's rest export against the JD rig's had 149 common nodes, none
over 0.05 deg or 0.1 mm, `Pelvis`, `EntityPosition` and `Collision`
included. Every local outside the 32 kept within 0.000256 deg and
0.000905 mm, and `Pelvis` matched the turned original within
0.0000022 deg.

[EXACT][CLAIM-ANIM-BIND-VISUAL-KEYING] The template's controls work: a
bake with visual keying replayed the controlled pose to 0.0011 mm, and
its angle check, which reads in float32, showed no turn it could
resolve. Before exporting with a constraint rig, bake with visual
keying: the exporter samples absolute locals with the constraints off,
so the bake is what carries the controlled pose into the export.

[EXACT][CLAIM-ANIM-BIND-RIGIFY-CONTROLS] In the agent runs of
2026-11-25 on the conformed template in Blender 5.3.0 in background,
`upper_arm_parent.R["IK_FK"]` was 0 in the template and in its
conformed copy, as delivered; with 0, turning the FK control
`upper_arm_fk.R` by -60 or +60 deg about its local X, Y or Z left
the direction of `_DayZ_Character`'s `RightArm` unchanged
(0.0 deg); with 1, -60 or +60 deg about its local X or Z turned
that direction 60.0 deg, and about its local Y (the bone's own
axis) 0.0 deg. So, with a Rigify template, measure which value of
the arm's `IK_FK` lets the FK control move the deform rig before
keying it. Reopened with `blender -b`, the saved file read
0.141 deg at frame 20 on `_DayZ_Character` instead of the
59.993 deg of the authoring session, and the same 0.141 deg with
`--enable-autoexec`; with the Copy Transforms constraints of
`_DayZ_Character` muted, its baked action read 59.993 deg again.
In the second run the reopened file, with those constraints muted,
read 60.0 deg. The cause was not established.

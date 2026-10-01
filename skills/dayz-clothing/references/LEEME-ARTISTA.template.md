# ArmorHneck — CORRECTED worn models (delivery for fine-tuning)

Date: 2026-08-03. Worn models of ArmorHneck mod with structural
corrections making the garment work in-game (verified in DayZ
1.29). Fine-tuning fit (arms, legs, abdominal protector) remains
pending: that is the task for this delivery.

## Contenido
- `armorhneck_m.fbx` / `armorhneck_f.fbx` — **for working in Blender/Max/Maya**
  (geometry + UVs + skinning WEIGHTS as vertex groups on an armature)
- `armorhneck_beige_co.png` — diffuse texture (FBX references it)
- `armorhneck_m.p3d` / `armorhneck_f.p3d` — same models in MLOD
  (editable in Object Builder, if that route is preferred)
- `model.cfg` — CORRECT model.cfg for binarizing these models

## The FBX
- **Axes**: standard Blender, Z up, character is STANDING facing -Y (Blender's
  Front view), anatomical left at +X: the same frame as the official DayZ rig.
  Units: meters. Origin at character's feet. (Packages made before 2026-10-01
  faced +Y and were a mirror image; return those the way they were delivered.)
- **The 10-bone armature is a WEIGHT CARRIER, not the game rig**:
  its bones are placed at each region's centroid only so the
  FBX preserves vertex groups. Not for animating. The important part are the
  GROUPS: leftarm, rightarm, leftforearm, rightforearm, leftupleg, rightupleg,
  neck, pelvis, spine, spine3 (in lowercase).
- **Golden rule**: move/rotate/sculpt VERTICES to fit plates to the
  body. Do NOT rename vertex groups, do NOT empty them. Re-weighting is allowed if you
  want to improve deformation (see "optional improvement"), keeping sum 1.0
  per vertex and those same group names.
- If topology is preserved (same vertex number/order),
  reintegration into mod is automatic; if retopo'd, still deliver the
  FBX with groups and we rebuild it.

## What was already corrected (do NOT undo)
1. **Orientation**: original mesh was modeled facing backwards (180
   degrees). These models are already in canonical DayZ clothing frame
   (in .p3d: -Z = front, +X = anatomical left, Y up, origin at
   feet; FBX already translates to Blender axes). If re-exported from an
   old source WITHOUT rotating, the bug returns.
2. **Skeleton**: model.cfg declares `DayzTemporarySkeleton` (159 bones,
   exact vanilla hierarchy). ALL vanilla clothing is compiled this way; with
   `OFP2_ManSkeleton` as name engine does NOT re-bind garment to player
   and it renders rigid/floating. ALWAYS binarize with this model.cfg.
3. Complete and normalized weights (sum 1.0 per vertex).

## The assignment (fine-tuning)
Align plates to body in canonical DayZ A-pose:
- **Arms**: pauldrons and forearms remain separated/sagging relative to character's
  arm (canonical bind has arms more horizontal than this
  model). Perfect reference for "where clothing should fall": vanilla chainmail
  worn (`dz\characters\tops\chainmail_m.p3d`).
- **Legs and abdominal protector**: minor fit.

## Mejora opcional
Current skinning is rigid per plate (62% of vertices to single bone, without
shoulder/roll/extra/spine1/spine2 transition bones). It works, but
joints are crude in motion. Smoothing weights at joints (2-4
influences, like vanilla clothing) would greatly improve deformation.

## Return workflow
Deliver modified FBX (or .blend). We convert it to .p3d
(the same axis map that produced this FBX, which is its own inverse),
rebuild selections with vertex group weights, and binarize with included
model.cfg. Do not mirror the model or flip its normals: the garment is
meant to look in game as it does in Blender, text and logos included.

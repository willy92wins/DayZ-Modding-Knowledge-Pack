# Skeletal animation — RTM route (legacy props and man animations)

RTM is the Real Virtuality animation format. In DayZ it is used for config-driven prop/object animation and legacy man animations (not the Enfusion character path — that is `.anm`, see `skeletal-anm-enfusion.md`). Sources from fase-0 research (2026-05-20), labelled.

## ⚠️ Legal/format caveat, first

The RTM format is **reverse-engineered**. The BI wiki RTM page carries an explicit notice that it describes internal undocumented structures and that use of the information may violate BI's rights. Treat it as community RE, not an official contract — it can differ between engine versions. [VERIFIED: community.bistudio.com/wiki/Rtm_(Animation)_File_Format, notice read directly.]

## Format shape [VERIFIED structure, line offsets TBD-verify]

- Plain (`RTM_0101`): optional `RTM_MDAT` header (frame properties as name/value at float phases), then `RTM_0101`: a motion XYZTriplet, frame count, bone count, 32-byte fixed-length bone names, per-frame bone transforms as 4x3 float matrices.
- Binarised RTM: separate compact format, versions 3/4/5 (Arma 2 / Arma 3). [TBD-verify: page Cloudflare-blocked at fetch; existence confirmed via search index.]

## ⚠️ Writer status — do NOT promise a Python RTM writer

- Reading RTM in Python is feasible (the `4d4a5852/rtm_import` Blender addon parses it; logic is portable). [VERIFIED import-only.]
- **No verified open-source RTM writer in pure Python exists.** Only Blender plugins write RTM. So route RTM *authoring* through Blender or FBXToRTM, not through a hand-rolled Python writer. A Python RTM writer is roadmap, not a current capability — mark it [ASSUMPTION] if you ever propose it.

## The pipeline (Windows/GUI — Layer 3)

```
Blender (keyframes against OFP2_ManSkeleton)
  → .rtm directly        [Arma3ObjectBuilder export]      — OR —
  → FBX → .rtm           [FBXToRTMGui.exe, ships with DayZ Tools]
       → reference in p3d/model.cfg → pack → sign → in-game
```

- **Arma3ObjectBuilder** (MrClock8163, Blender 4.2+) exports `.rtm` directly from a timeline range; phase maps 0.0–1.0 across the render range — a misconfigured range squishes or clips the animation. Only known frame property is `StepSound`. [VERIFIED: mrcmodding.gitbook.io/arma-3-object-builder/properties/rtm.] Arma-3-branded but the RTM format is identical to DayZ's.
- **FBXToRTMGui.exe** (DayZ Tools): set bindpose FBX + modelbox.xml, pick skeleton (`ManSkeleton`), root bone (`Hips`), match FPS to source. [VERIFIED page exists; ran-with-DayZ-Tools detail TBD-verify.]

## Gotchas [VERIFIED unless noted]

- Bone names must match `OFP2_ManSkeleton` exactly (same wall as the `.anm` route).
- FPS must match exactly between the Blender/source file and the converter, or animation speed drifts.
- Scale: Blender meters vs BI space — [TBD-verify exact factor for DayZ].
- MotionBuilder: FBXtoRTM documented working with MB 2009, broken with MB 2015. [TBD-verify modern MB.]
- DayZATool extraction rigs are "always incorrect" per community — do not use DayZATool for RTM authoring round-trips; it is the `.anm` tool.

## When to use RTM vs `.anm`

- RTM: config-driven prop/object animation that needs real skeletal motion beyond `rotation`/`translation` (rare — most props are fine with Layer 1 config animation), or legacy man anims.
- `.anm`: anything character/infected/animal/weapon. See `skeletal-anm-enfusion.md`.

## Source repos (URLs)

- BI RTM spec: community.bistudio.com/wiki/Rtm_(Animation)_File_Format
- Arma3ObjectBuilder: github.com/MrClock8163/Arma3ObjectBuilder
- ArmAToolbox (older): github.com/AlwarrenSidh/ArmAToolbox
- rtm_import (read only): github.com/4d4a5852/rtm_import
- FBX to RTM: community.bistudio.com/wiki/FBX_to_RTM

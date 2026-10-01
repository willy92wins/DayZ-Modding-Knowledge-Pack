# ARDY → DayZ integration plan (UNVERIFIED)

This entire document is `[DESIGN]` — plan/hypothesis, not a tested procedure. No step of
this chain has been executed. Before writing retargeting code, re-read this completely and
decide with user whether each stretch deserves its own gate (R3: changes touching >1 mod/skill
file require prior approval) — do not chain the 4 steps in a single session without checkpoints.

## Why this plan exists without being verified

The use case chosen for ARDY is survivor full-body locomotion (running, jumping,
vaulting). For that to become playable in DayZ a conversion chain is needed that today does not
exist. Documenting the plan now avoids a future session having to re-derive from scratch what
is missing, but **do not advance the verdict that the chain works** — each arrow below is an
unexplored plausible failure point.

## The complete chain

```
ARDY .npz (skeleton "core", world-space joints + rotaciones + root + foot contacts)
  │
  │  [DESIGN] Paso 1 — parseo
  ▼
Import a Blender (script Python custom, numpy → armature)
  │
  │  [DESIGN] Paso 2 — el paso de mayor riesgo
  ▼
Retarget al OFP2_ManSkeleton (skeleton del player DayZ)
  │
  │  [EXACT — pipeline ya existente y verificado, ver dayz-animation-pipeline]
  ▼
Export .txa → Workbench → .anm (SEAnim / DayZATool)
  │
  ▼
Gate in-game
```

Only the final leg (`.txa` → `.anm` → in-game) has a verified pipeline — it is the one already used by
`dayz-animation-pipeline` for any player skeletal animation. Steps 1 and 2 are
new territory.

## Step 1 — Parse the `.npz`

Low technical risk: it is a numpy array with documented structure (`posed_joints [T,J,3]`,
rotations, root, foot contacts). Write a script that loads it and inspects the actual shape
of the first generated output BEFORE assuming the layout — the README does not give the exact
dtype/axis order (XYZ or XZY? Y-up or Z-up?), and DayZ uses Z-up (see Blender→DayZ winding caveats
already documented in `outputs/flip_winding.py` from other projects). Confirm with a real `.npz`, do
not assume the convention of another pipeline.

## Step 2 — Retarget to OFP2_ManSkeleton (the step that can kill the plan)

This is structurally the same problem already solved (partially, EXPERIMENTAL) by the skill
`mixamo-retarget`: mapping a generic external skeleton to the specific bone hierarchy that
DayZ expects. Differences that may make it HARDER than the Mixamo case:

- The ARDY "core" skeleton has no documented official mapping to any video game format
  (neither FBX, nor BVH, nor SMPL) — the bone-by-bone mapping must be derived by hand, comparing names
  and hierarchy against the complete map of `OFP2_ManSkeleton` in
  `<knowledge-notes>/dayz-animations-creatures-weapons.md` §3.10 (Core/spine,
  legs, arms, IK helpers, fingers).
- The exact bone count of "core" against official source is not known (the video said 27, not
  confirmed on research.nvidia.com or GitHub) — count actual joints of the first generated
  `.npz` before attempting to map.
- DayZ expects fingers, `RightHand_Dummy`/`LeftHand_Dummy` (lod=2 helpers), and several IK helpers
  (`*HandOrigin`, `*HandIKTarget`) that a generic "core" skeleton of 27 bones probably does NOT
  cover — leg/torso locomotion may map reasonably well, but hands/fingers
  probably need to remain in their bind pose (unanimated) or inherit from another source.

**Open question to resolve with the first test**: is retargeting only legs+torso+spine
(leaving arms/hands intact or in additive) sufficient for the real goal ("running,
jumping, vaulting")? If yes, retargeting scope is greatly reduced and risk drops. Decide it
BEFORE attempting to map hands/fingers, which is where this type of retarget usually fails most.

## Steps 3-4 — Export and final pipeline

Once an FK pose exists on the Blender armature with correct DayZ bone names, the
rest of the chain (`.txa` → Workbench → `.anm`) is the ALREADY verified pipeline of
`dayz-animation-pipeline` — there is nothing new to design there, only execute the known process
(see that skill for export details).

## Alternatives if direct retargeting does not pay off

If step 2 turns out too costly for the actual benefit:

- Use ARDY only as **visual reference** (playblast) to animate by hand in Blender/Cascadeur,
  instead of attempting an automatic 1:1 retarget. Loses "real time" but avoids the skeleton
  mapping problem.
- Review whether `Cascadeur` (already evaluated in `ai-3d-pipeline/stage-05-animation.md`, conditional
  MED verdict, only one with custom-skeleton + IK/FK + physics support) better covers the same
  locomotion objective without ARDY's non-standard skeleton problem.

## Cross-refs

- `<knowledge-notes>/dayz-animations-creatures-weapons.md` §3.10 — complete bone
  map of DayZ player, needed to design step 2 mapping.
- `<knowledge-notes>/ai-3d-pipeline/stage-05-animation.md` — ARDY applicability
  verdict and comparison with the other 6 evaluated tools.
- skill `mixamo-retarget` — same type of problem (external retarget → DayZ), already EXPERIMENTAL;
  read what failed or remained pending there before repeating the same path.
- skill `dayz-animation-pipeline` — final target `.txa`/Workbench/`.anm` pipeline.

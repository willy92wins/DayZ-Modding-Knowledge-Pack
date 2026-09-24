# Character ragdoll (DayZ 1.30 Exp)

(hasta 1.29: player death/unconscious physics was an opaque native ragdoll; scripts only toggled it via `PhysicsSetRagdoll`.)

(desde 1.30 Exp: survivor death physics is data-driven. `SurvivorBase` points `enfAnimSys.ragdoll` at `DZ/characters/bodies/human.ragdoll`. Workbench ships a ragdoll editor for `.ragdoll` files ([CHANGELOG] `work/changelog-1.30-exp-modding.md:47`).)

**Who this is for:** anyone authoring a custom survivor/human NPC body, or replacing `SurvivorBase` mesh/skeleton. Infected `ZombieBase.enfanimsys` in this build does **not** set a `ragdoll` path (`exp/characters_zombies/DZ/characters/zombies/config.cpp:50-57`). Whether a custom non-human `.ragdoll` is picked up by name/GUID is [UNVERIFIED] (no script `LoadRagdollFile`).

## Binding on SurvivorBase

Re-verified in the extracted config (DeRap header shifts line numbers vs digest `:20`):

- `class SurvivorBase: Man` — `exp/characters_data/DZ/characters/data/config.cpp:97`
- `class enfAnimSys` — same file `:106`
- `ragdoll = "DZ/characters/bodies/human.ragdoll";` — same file `:113`

If you replace a survivor body, keep that `ragdoll` line (or point it at your own `.ragdoll` that matches your `.xob` bone names). [DESIGN] A mesh/skeleton mismatch vs the ragdoll bone set will look like a broken corpse (capsules on the wrong limbs), not a bind-pose deform at idle.

## Format (`RagdollDef`)

`human.ragdoll` is 202 lines of Enfusion config. Root `RagdollDef` binds an Enfusion `.xob`, then nests `RagdollBone` blocks (hierarchy = nesting). Each bone has `Mass`, `Offset`, `Geometries` (`PhysicsCapsuleGeometry` / `PhysicsSphereGeometry`), and joint limits.

```
// [EXACT] exp/characters_bodies/DZ/characters/bodies/human.ragdoll:1
RagdollDef {
 Object "{D470A4E7581CCE23}DZ/anims/workspaces/player/Models/player_m_editorpreview.xob"
 {
  RagdollBone pelvis {
   Mass 17
   Offset -0.008 -0.011 0
   Geometries {
    PhysicsCapsuleGeometry Spine1 {
     SurfaceProperties "DZ/data/data/penetration/flesh.bisurf"
     Offset 0 0.914 0.015
     Orientation 0 0 90
     Radius 0.1
     Height 0.2
    }
    PhysicsCapsuleGeometry Spine2 {
     Offset 0 1.061 0
     Radius 0.1
     Height 0.1
    }
   }
   {
    RagdollBone spine3 {
     Mass 15
```

Head uses a sphere, not a capsule (`PhysicsSphereGeometry Head`, `:42-46`). Surface on flesh capsules is `"DZ/data/data/penetration/flesh.bisurf"`.

## Eleven `RagdollBone` masses (vanilla human)

Cited from `exp/characters_bodies/DZ/characters/bodies/human.ragdoll`:

| Bone | Mass | Line |
|---|---|---|
| pelvis | 17 | `:5` |
| spine3 | 15 | `:23` |
| head | 6.1 | `:39` |
| leftarm | 2.1 | `:54` |
| leftforearm | 1.7 | `:69` |
| rightarm | 2.1 | `:85` |
| rightforearm | 1.7 | `:100` |
| leftupleg | 7.5 | `:118` |
| leftleg | 6.6 | `:134` |
| rightupleg | 7.5 | `:159` |
| rightleg | 6.6 | `:175` |

Joint fields used: `JointMinLimits`, `JointMaxLimits`, `JointStiffness` (e.g. spine3/head `0.8`), `JointDamper` (e.g. `0.3` / `0.4`). Not every bone sets stiffness.

[DESIGN] Do not scale these masses with a baked-oversize character mesh — the ragdoll is a separate physics asset. If you bake a 1.2× body, the capsules will sit wrong unless you author a matching `.ragdoll`.

## Authoring checklist

1. Bone names in `.ragdoll` must exist on the bound `.xob` (vanilla: `player_m_editorpreview.xob` GUID `{D470A4E7581CCE23}`).
2. Keep `ragdoll = ...` on any class that inherits/replaces `SurvivorBase.enfAnimSys`.
3. Edit `.ragdoll` in Workbench's ragdoll editor ([CHANGELOG]); treat this file as the source of truth for corpse capsules, not `model.cfg`.
4. Infected custom characters still use the 95-bone `hermit_newbindpose.xob` bind for animation; that is a different layer from this survivor ragdoll.

<!-- [merged 2026-06-05: standalone predecessor particle reference from .claude\skills user copy. Kept for content the main SKILL.md + refs do not cover: multi-emitter composition (PLANES_EX/IMPACT/BOOM), animated + Mast modulation curves, CfgCloudlets conversion.] -->

---
name: dayz-particles
description: Enfusion-style .ptc particle effect format for DayZ (current engine, post-Reforger) — distinct from the classic class-based Particle.cpp / CfgCloudlets syntax. Covers EffectDef/EmitorDef structure, Material UUID + .emat refs (vanilla smoke/fire/sparks/dust/debris paths), the emitter parameter catalog, animated curves and *Mast modulation overlays, multi-emitter composition (layered explosion/impact), and registration via ParticleList + RegisterParticle. Use when: writing .ptc files for DayZ Enfusion, creating explosion/impact/smoke/dust/debris/spark effects, registering with ParticleList, integrating with EffectParticle scripts, debugging .ptc that won't load, or converting old class-based particles to Enfusion. Triggers: .ptc, particle effect, Enfusion particle, EffectDef, EmitorDef, ParticleList, smoke/fire/explosion effect, RegisterParticle, .emat. Use alongside enforce-script-reference.
---

# DayZ Enfusion Particle Effects (.ptc)

**Format note**: This skill covers the **Enfusion (Reforger-style) .ptc format** used by current DayZ. It is structurally different from the classic class-based `CfgCloudlets` / `Particle.cpp` syntax. Both formats coexist in some legacy mods, but new content should use Enfusion.

Patterns extracted from LM_Planes (3 .ptc files: PLANES_EX bomb explosion, PLANES_IMPACT ground hit, PLANES_BOOM aircraft fireball). Author: Llama+Itspete-Here.

## File structure

```
EffectDef {
 Emitors {
  EmitorDef <named_emitter_1> {
   ShapeType <Box|Ellipse|Cone|Sphere>
   ShapeSize <x> <y> <z>
   ConeAngle <a> <b> <c>
   MaxNum <int>
   BirthRate <float>
   BirthRateRND <float>
   Angles <a> <b> <c>
   Material "{GUID}path/to/material.emat"
   SizeMultiplier <float>
   SizeRND <float>
   RandomRotDir <0|1>
   RotMultiplier <float>
   VelAngle <float>
   RandomAngle <0|1>
   Sort <int>
   Velocity <float>
   VelocityRND <float>
   VelAffect <float>
   Wind <0|1>
   AnimOnce <0|1>
   AnimFPS <int>
   LifetimeByAnim <0|1>
   LifeTime <float>
   LifeTimeRND <float>
   Color { <keyframes...> }
   Alpha { <keyframes...> }
   RotationSpeed { <keyframes...> }
   Size { <keyframes...> }
   EffectTime <float>
   ColorMast { ... }  (optional)
   AlphaMast { ... }  (optional)
  }
  EmitorDef <named_emitter_2> { ... }
  ...
 }
}
```

**Indentation**: space-based (typically 1-2 spaces per level). No braces with `class` keyword. No semicolons. White-space separated key/value pairs.

**No commas in arrays** — `ShapeSize 0.5 0 0.5` is three floats, not `{0.5, 0, 0.5}`.

## Material references (Enfusion .emat)

```
Material "{0BEA27443975BE0B}Graphics/Particles/materials/smoke/smoke_anim_02.emat"
```

The `{UUID}` prefix is the Enfusion asset GUID from Workbench. The path that follows is the canonical asset path.

### Reusable vanilla DayZ/Reforger materials

You almost never need to create your own `.emat`. Re-use these (with their UUIDs):

| Path | Use case |
|---|---|
| `Graphics/Particles/materials/smoke/smoke_anim_02.emat` | Generic smoke (LM_Planes uses for short and long smoke trails) |
| `Graphics/Particles/materials/smoke/smoke_cloud_01_b_trans_landmine_01.emat` | Dust cloud for impact (used in PLANES_IMPACT dust ring) |
| `Graphics/Particles/materials/smoke/smoke_cloud_01_g_heliwreck_01.emat` | Dark red smoke (used in PLANES_BOOM red_smoke for aircraft fireball) |
| `Graphics/Particles/materials/smoke/smoke_dust_01.emat` | Generic dust |
| `Graphics/Particles/materials/smoke/smoke_dust_02.emat` | Dust variant 2 |
| `Graphics/Particles/materials/smoke/smoke_dust_04.emat` | Dust variant 4 |
| `Graphics/Particles/materials/smoke/smoke_dust_05.emat` | Dust variant 5 |
| `Graphics/Particles/materials/smoke/smoke_dust_06.emat` | Dust variant 6 |
| `Graphics/Particles/materials/smoke/smoke_debris_01.emat` | Debris flying chunks |
| `Graphics/Particles/materials/fire/fireball_1.emat` | Animated fireball |
| `Graphics/Particles/materials/fire/fire_medium_camp_04.emat` | Slower fire (campfire-style, used for fire_anim_root in BOOM) |
| `Graphics/Particles/materials/fire/sparks_05.emat` | Quick spark |
| `Graphics/Particles/materials/fire/sparks1.emat` | Generic sparks (BOOM) |
| `Graphics/Particles/materials/fire/sparks_04.emat` | Sparks variant 4 (debris sparks in IMPACT) |
| `Graphics/Particles/materials/weapons/weapon_shot_fnx_02.emat` | Pistol shot flash (used as impact fire 01) |
| `Graphics/Particles/materials/weapons/weapon_shot_fnx_03.emat` | Pistol shot flash variant |

UUIDs are stable across DayZ versions — copy from existing .ptc files in vanilla DayZ Reforger mod directory or another mod.

## EmitorDef parameters reference

### Spawn geometry
- `ShapeType Box | Ellipse | Cone | Sphere` — emitter volume primitive
- `ShapeSize <x> <y> <z>` — dimensions of the volume
- `ConeAngle <a> <b> <c>` — for Cone type, opening angles
- `Offset <x> <y> <z>` — emitter spawn point offset from owner position (use negative Y to lower spawn point)
- `CenterX <float>`, `CenterY <float>` — texture rotation pivot (0-1 normalized)

### Emission rate
- `MaxNum <int>` — particle cap (don't exceed; emitter dies if reached)
- `BirthRate <float>` — particles per second
- `BirthRateRND <float>` — random variation added to birth rate
- `BirthRateVel <0|1>` — link birth rate to owner velocity (smoke trails behind moving objects)

### Lifetime
- `LifeTime <float>` — particle lifetime in seconds
- `LifeTimeRND <float>` — random variation
- `EffectTime <float>` — total effect duration (when does the emitter stop spawning?)
- `LifetimeByAnim <0|1>` — if 1, particle dies when its texture animation completes

### Animation
- `AnimFPS <int>` — texture animation playback speed (use 999 for non-animated materials, single frame)
- `AnimOnce <0|1>` — 1 = play animation once, 0 = loop while particle alive
- `RandomFrame <0|1>` — 1 = start at random frame of animation (visual variation across particles)

### Initial motion
- `Velocity <float>` — initial speed
- `VelocityRND <float>` — random variation
- `VelAffect <float>` — how much owner velocity transfers to particles (0 = none, 1 = full)
- `VelAngle <float>` — initial direction angle
- `RandomAngle <0|1>` — randomize initial direction
- `RandomRotDir <0|1>` — randomize rotation direction
- `RotMultiplier <float>` — rotation speed multiplier

### Physics
- `Wind <0|1>` — affected by wind
- `AirResistance <float>` — air drag coefficient (typical 0.05)
- `AirResistanceRND <float>` — random variation
- `GravityMultiply <float>` — gravity multiplier. **Negative values make particles rise** (used for smoke: `-0.05`)

### Sorting
- `Sort <int>` — render order priority (higher = renders later, on top)

## Animated curves (over particle lifetime)

Properties like `Color`, `Alpha`, `Size`, `RotationSpeed` are interpolated over the particle's lifetime via keyframe lists:

```
Alpha {
 0 0 0.31101 0.24684 1 0
}
```

This means: at lifetime fraction `0` alpha is `0`, at fraction `0.31101` alpha is `0.24684`, at fraction `1` alpha is `0`. So the particle fades in then fades out.

```
Color {
 0 1 1 1   1 0.9187 0.8938 0.8813
}
```

For Color, each keyframe is `<time> <R> <G> <B>` (4 floats). So this is: at time `0` color is `(1,1,1)` (white), at time `1` color is `(0.9187, 0.8938, 0.8813)` (warm white).

For long curves with multiple keyframes:
```
Color {
 0 0.8353 0.3133 0.008
 0.2115 0.1647 0.008 0.008
 0.2159 0 0 0
 0.2925 0.0201 0.0201 0.0201
 ...
}
```

Each line of 4 floats is one keyframe (time + RGB).

### Mast modulation curves (envelope dynamics)

Suffix `Mast` indicates a **modulation curve applied on top of the base curve**. These let you create complex envelope effects:

- `AlphaMast { ... }` — multiplies alpha over effect time
- `SizeMast { ... }` — modulates size
- `RotationSpeedMast { ... }` — modulates rotation
- `BRateMast { ... }` — modulates birth rate (dynamic spawn rate)
- `VelocityMast { ... }` — modulates velocity
- `AirResistanceMast { ... }` — modulates air resistance

Pattern: **base curve defines baseline behavior, Mast adds dynamic envelope**. Example use: smoke that pulses in intensity (`AlphaMast`), explosion that ramps spawn rate up then down (`BRateMast`), debris that initially flies fast then slows (`VelocityMast`).

## Multi-emitter composition pattern

Real effects layer multiple emitters with different timings, sizes, materials. From LM_Planes:

### PLANES_EX (bomb-drop explosion) — 4 emitters

- `short` — short-lived smoke burst (Box shape, smoke_anim_02, LifeTime 0.5)
- `short_spark` — quick sparks (Box, sparks_05, LifeTime 0.1 AnimOnce 1)
- `long_light` — lingering light-color smoke (Ellipse, smoke_anim_02, hemispheric cone 90/-90/90)
- `long_dark` — lingering dark-color smoke (Ellipse, larger size, slower fade)

### PLANES_IMPACT (ground impact) — 12 emitters

Organized in clusters: explo_fire (3), explo_dust (7 including small/big rings, up direction, opposite direction variants), explo_debris (3 with sparks).

### PLANES_BOOM (aircraft fireball) — 7 emitters

fire_anim_small + fire_anim_root + fire_anim + fire_anim_Rot + red_smoke + red_smoke_large + sparks. Uses extensive `Mast` modulation for dynamic feel.

**Design principle**: each emitter is small + focused. Layer by purpose (initial flash, secondary debris, lingering smoke, sparks). Different LifeTimes per layer create natural cascade.

## Useful tricks

| Trick | Use |
|---|---|
| `GravityMultiply -0.05` | Smoke that rises (negative gravity) |
| `AnimFPS 999 + AnimOnce 1` | Non-animated materials (single static frame, no resampling) |
| `RandomFrame 1` | Visual variation across particles from same emitter (each starts at a random texture frame) |
| `ConeAngle 90 -90 90` | Hemispheric emission (shell expansion) |
| `ShapeType Ellipse + ConeAngle` | Spherical/dome shell expansion |
| `Offset 0 -0.83 0` (negative Y) | Lower emitter spawn point (sink the explosion partially into the ground) |
| `BirthRateVel 1` | Birth rate scales with owner velocity (smoke trails) |
| Materials reused across emitters | Same material with different LifeTime/Size/Velocity gives different visual layers cheaply |

## Registration via ParticleList (modded class)

To make a .ptc usable from script, register it in `ParticleList`:

```cpp
// scripts/3_Game/ParticleList.c
modded class ParticleList
{
    static const int PLANES_EX = RegisterParticle("LM_Planes/graphics/", "PLANES_EX");
    static const int PLANES_IMPACT = RegisterParticle("LM_Planes/graphics/", "PLANES_IMPACT");
    static const int PLANES_BOOM = RegisterParticle("LM_Planes/graphics/", "PLANES_BOOM");
}
```

**Pattern**:
- File goes in `3_Game` script module (game-scope registration)
- `modded class ParticleList` — extends vanilla particle registry
- Each particle gets a unique `static const int` ID via `RegisterParticle(folder, name)`
- `folder` parameter is the mod path WITH trailing slash (e.g. `"LM_Planes/graphics/"`)
- `name` is the .ptc filename WITHOUT extension (e.g. `"PLANES_EX"` for `PLANES_EX.ptc`)
- Naming convention observed: folder prefix then UPPERCASE_PARTICLE_NAME

## Triggering particles from script

```cpp
import "EffectParticle";

// In an entity script:
override void EOnContact(IEntity other, Contact extra)
{
    if (m_PlaneMode == PlaneMode.PLANE_MODE_AIR && GetVelocity(this).Length() > 30) {
        // Trigger impact effect at hit position
        Particle p = Particle.PlayInWorld(ParticleList.PLANES_IMPACT, extra.Position);
    }
}

// Attached to entity:
EffectParticle eff = new EffectParticle();
eff.SetParticle(ParticleList.PLANES_BOOM);
eff.SetAutodestroy(true);
SEffectManager.PlayInWorld(eff, GetPosition());

// Custom EffectParticle subclass with per-frame logic (see Seaplanewatereffects.c pattern):
class EffectSeaplaneWaterFront : EffectParticle
{
    void EffectSeaplaneWaterFront()
    {
        SetParticle(ParticleList.PLANES_SEAPLANE_FRONT);
    }
    
    override void Update(float timeSlice = 0)
    {
        float speed = GetPlaneSpeed();
        UpdateSpeedState(GetCurrentParticle(), speed);
    }
    
    protected void UpdateSpeedState(Particle ptc, float speed)
    {
        // Enable/disable specific emitters in the .ptc based on speed
        EnableEmitor(ptc, 0, speed > 5.0);   // slow emitter
        EnableEmitor(ptc, 1, speed > 15.0);  // medium emitter
        EnableEmitor(ptc, 2, speed > 30.0);  // fast emitter
    }
}
```

The dynamic-enable pattern (per-emitter control via `EnableEmitor(ptc, index, enable)`) lets you build adaptive effects that respond to game state.

## Anti-patterns

1. **Don't create custom .emat unless you must.** Reuse vanilla DZ materials with their UUIDs. Custom .emat requires Enfusion Workbench + asset GUID generation. Vanilla coverage is broad enough for 95% of effects.
2. **Don't use AnimFPS for non-animated materials at low values.** Use `999 + AnimOnce 1` so engine doesn't waste cycles cycling frames you don't have.
3. **Don't forget RandomFrame for groups of similar particles.** Without it, all particles spawn synced to the same frame — looks artificial.
4. **Don't put EmitorDefs at the wrong nesting level.** Must be inside `EffectDef { Emitors { ... } }`, not directly under `EffectDef`.

## Cross-references

- [[enforce-script-reference]] — `modded class` pattern, EffectParticle base, SEffectManager
- [[dayz-aviation]] — PLANES_EX / PLANES_IMPACT / PLANES_BOOM usage context, Seaplanewatereffects.c example
- [[dayz-mod-workflow]] — workflow protocol

## Conversion from classic CfgCloudlets format

If migrating from old class-based DayZ particles to Enfusion:

| Old (CfgCloudlets) | New (.ptc Enfusion) |
|---|---|
| `class CloudletShape;` declaration | Implicit via ShapeType |
| `class MyEffect: CloudletShape { ... }` | `EffectDef { Emitors { EmitorDef name { ... } } }` |
| `interval = 0.01;` | `BirthRate = 100;` (1/interval) |
| `cloudletDuration = 2;` | `LifeTime 2` |
| `cloudletShape = "..."` | `Material "{UUID}path.emat"` |
| Animation = arrays per attribute | `Color { ... }` / `Alpha { ... }` keyframe blocks |
| `class Color { ... }` nested | Same data, different syntax (inline keyframes) |

Full migration usually means rewriting; structure is too different for mechanical translation.

<!-- llama-mod-extraction: findings f_060, f_061, f_062, f_063, f_064, f_065 | pbo: LM_Planes | pass: 1 | date: 2026-05-23 | source: workshop 3730564764 graphics/PLANES_EX.ptc + PLANES_IMPACT.ptc + PLANES_BOOM.ptc -->

---
name: dayz-particles
description: >
  DayZ particle effects system for Enforce Script modding. Covers the FULL
  pipeline: .ptc particle files (PLAIN TEXT, creatable programmatically),
  .emat material files (PLAIN TEXT, Particle/ParticleSprite shaders),
  .edds textures (standard DDS renamed), GUID reference system, vanilla material
  library (11 materials with GUIDs). Script API: legacy Particle, ParticleSource
  (native), ParticleManager (10k pool), SEffectManager wrapper, ParticleList
  registration. 276 vanilla effects cataloged (count is version-dependent). Includes .ptc 56-property reference,
  .emat 12-property reference, LFPG integration patterns (OnVarSync toggle,
  cleanup, overload sparks, generator smoke, sprinkler). Use for: creating custom
  particles WITHOUT Workbench, playing particles on objects, device lifecycle,
  SyncVar-driven toggle, EmitorParam tuning, Wiggle API. Consult BEFORE writing
  ANY particle code. Use alongside enforce-script-reference and dayz-model-pipeline.
---

# DayZ Particle Effects — Complete Modding Reference

## CRITICAL: .ptc AND .emat ARE PLAIN TEXT

DayZ particle files (.ptc) and material files (.emat) are plain text configs,
not binary. Custom particles can be created programmatically without Workbench.

| Layer | Format | Creatable? | Purpose |
|---|---|---|---|
| `.ptc` | Plain text config | YES | Particle effect (emitters, physics, curves) |
| `.emat` | Plain text config | YES | Material (texture ref, blend mode, color) |
| `.edds` | Standard DDS renamed | YES | Billboard sprite texture |
| `.meta` | Plain text (GUIDs) | Workbench only | NOT needed for mod runtime |

All particles are CLIENT-ONLY. Server controls state via SyncVars; client
creates/destroys particles in response.

## EFFECT-AREA PREFLIGHT (added 2026-08-31)

For `cfgeffectarea.json`, run **Effect areas: emitter budget and vertical band** plus its correction
below **before** choosing a radius. Compute the exact per-ring upper budget, keep it below 1,000 with
margin, measure the full elevation/underground band, and compare every global `SafePositions` entry
against every area.

---

## .ptc FILE FORMAT (verified from 9 vanilla files)

One EffectDef with one or more EmitorDef blocks. Each emitter is an independent
particle stream. Simplest particle (debug_dot): 1 emitter, 478 bytes. Complex
fire (fire_small_camp_01): 6 emitters (glow + flames + burst + short + sparks + smoke).

```
EffectDef {
 Emitors {
  EmitorDef <name> {
   ShapeType Point
   MaxNum 10
   BirthRate 5
   Material "{GUID}path/to/material.emat"
   SizeMultiplier 0.5
   Velocity 2
   LifeTime 1.5
   Color {
    0 1 0.8 0.3 1 0.7 0.5 0.25
   }
   Alpha {
    0 0 0.2 1 1 0
   }
   Repeat 1
  }
 }
}
```

### Property categories (56 total — full list in references/ptc-format-reference.md)

**Shape & emission:** ShapeType (Point/Box/Ellipse), ShapeSize (x y z),
ConeAngle (yaw pitch roll deg), MaxNum, BirthRate, BirthRateRND, Offset (x y z)

**Visual:** Material ("{GUID}path.emat"), SizeMultiplier, SizeRND,
BillboardingType (Full), CenterY (-1=bottom, 0=center), StretchMultiplier

**Motion:** Velocity, VelocityRND, AirResistance, AirResistanceRND,
GravityMultiply, GravityMultiplyRND, Wind (0-1), Spring, Restitution,
VelAngle (0/1), VelAffect (0-1)

**Lifetime:** LifeTime (seconds), LifeTimeRND, EffectTime (cycle duration),
Repeat (0=one-shot auto-deletes, 1=loop MUST stop manually)

**Animation:** AnimOnce, AnimFPS, LifetimeByAnim, RandomFrame

**Rotation:** RandomRotDir, RotMultiplier, RandomAngle

**Curves (keyframe pairs: time value time value ...):**
Color { t r g b t r g b }, Alpha { t a t a },
Size { t s t s }, RotationSpeed { t s t s }

**Master curves (modulate over EffectTime):**
ColorMast, AlphaMast, SizeMast, BRateMast, VelocityMast, AirResistanceMast

---

## .emat MATERIAL FORMAT (verified from 8 vanilla materials)

### Shader: `Particle` (fire, sparks, water, most particles)
```
Particle {
 AlbedoMap "{GUID}Graphics/Particles/sprites/texture.edds"
 Color 0 0 0 1
 Emissive 1 1 1 0
 BlendMode Additive_AlphaModulate
 Sort translucent
 Softness 2
 TileU 4
 TileV 2
}
```

### Shader: `ParticleSprite` (steam, flares, glow billboards)
```
ParticleSprite {
 AlbedoMap "{GUID}Graphics/Particles/sprites/texture.edds"
 Color 0.95 0.95 0.95 1
 Diffuse 0.95 0.95 0.95 1
 Ambient 0.59 0.59 0.59 1
 Softness 2
}
```

### All .emat properties (12):
AlbedoMap (texture GUID+path), Color (RGBA 0-1), Diffuse (RGBA),
Ambient (RGBA), Emissive (RGBA, self-glow), BlendMode (Additive_AlphaModulate
or numeric), Sort (translucent/overlay/0), Softness (0-2, edge blending),
TileU/TileV (sprite sheet cols/rows), CameraBlendFar (distance fade),
BidirLightScale (bidirectional lighting)

Full reference with examples: `references/emat-format-reference.md`

---

## GUID REFERENCE SYSTEM

Resources reference each other via `{HEXGUID}relative/path.ext`.

- **Vanilla→vanilla**: GUIDs embedded, engine resolves by GUID first
- **Mod .ptc→vanilla .emat**: USE vanilla GUID+path (mandatory, verified)
- **Mod .emat→vanilla .edds**: USE vanilla GUID+path (safe)
- **Mod .ptc→mod .emat**: path-only may work (needs in-game testing)
- **.meta files NOT needed** for mod runtime loading

---

## VANILLA MATERIAL LIBRARY (11 GUIDs mapped)

Reference these in custom .ptc to reuse vanilla visuals:

| GUID | Short name | Visual type |
|---|---|---|
| `{CB7AF4FD8ACBFDFC}` | glow/glow1.emat | Soft glow dot |
| `{009C2EBAACD2D72A}` | fire/sparks1.emat | Bright spark point |
| `{0B829A150C6A13E5}` | fire/sparks_06.emat | Spark strip (8-tile) |
| `{853257EDA4B1E35D}` | fire/fire_flame_01.emat | Fire flame billboard |
| `{3E6CE4D61F8AC71F}` | fire/fire_medium_camp_02.emat | Medium fire anim |
| `{83BCB6516091DB01}` | fire/fire_medium_camp_04.emat | Fire burst anim |
| `{62F13B8B540EBC80}` | fire/fireball_1.emat | Fireball |
| `{00BEA27443975BEB}` | smoke/smoke_anim_02.emat | Animated smoke puff |
| `{008E25684854DAB8}` | smoke/steam_small_cook_01.emat | Steam/vapor cloud |
| `{8FE2383D6913E098}` | enviroment/water_splash_01_NoEm.emat | Water splash |
| `{D29B53088A5A3911}` | smoke/smoke_dust_01_W.emat | White dust/mist |

All paths prefixed with `Graphics/Particles/materials/`.

---

## THREE SCRIPT API LAYERS

### 1. Legacy `Particle` (scripts/3_Game/Particles/Particle.c)
Creates `#particlesourceenf` child entity. EOnFrame lifetime tracking.
Auto-deletes non-looping particles. Used by FireplaceBase, torches, cooking.

### 2. `ParticleSource` extends Particle (ParticleSource.c)
Native C++ backed. No EOnFrame. Auto-destroy flags: ON_END, ON_STOP, ALL, NONE.
StopParticleFlags: `NONE = 0` (no-op; default `StopParticle()` already does gradual fade), IMMEDIATE, PAUSE (freeze visible).

### 3. `ParticleManager` pool (ParticleManager.c)
Global instance via `ParticleManager.GetInstance()` — 10000 pool, client only,
returns null on dedicated server. Pre-allocates+reuses ParticleSource objects.
Mods can also `new ParticleManager(settings)` to instantiate their own pools
(the test framework does this); GetInstance() is the global, not a hard singleton.

### Wrapper: `SEffectManager`
PowerGenerator pattern: `SEffectManager.PlayOnObject(effect, parent, pos, ori)`.
Cleanup: `SEffectManager.DestroyEffect(m_Smoke)`.

Full API signatures: `references/script-api-reference.md`

---

## API QUICK REFERENCE

```
// Static create+play
Particle p = Particle.PlayOnObject(ID, parent, localPos, localOri, forceWorldRot);
Particle p = Particle.PlayInWorld(ID, worldPos);
// ParticleManager.GetInstance() returns null on dedicated server — always guard.
ParticleManager pm = ParticleManager.GetInstance();
ParticleSource ps;
if (pm) ps = pm.PlayOnObject(ID, parent, localPos);

// Instance control
p.PlayParticle(optionalNewId);
p.StopParticle(flags);  // StopParticleFlags: NONE, IMMEDIATE, PAUSE
p.Stop();               // legacy alias
p.IsParticlePlaying();
p.ResetParticle();      // ParticleSource only
p.RestartParticle();    // reset+play
p.DisableAutoDestroy(); // ParticleSource only

// Parameter tuning (-1 = all emitters)
p.SetParameter(emitter, EmitorParam.AIR_RESISTANCE, 3.0);
p.ScaleParticleParamFromOriginal(EmitorParam.SIZE, 0.5);

// Wiggle
p.SetWiggle(randomAngle, randomInterval);
p.StopWiggle();
```

---

## REGISTERING CUSTOM PARTICLES

### Mod file structure
```
LFPowerGrid/
  data/particles/
    lfpg_sprinkler_spray.ptc
    lfpg_overload_sparks.ptc
  data/particles/materials/         ← optional custom materials
    lfpg_blue_water.emat
  scripts/3_Game/
    LFPG_ParticleList.c
```

### Registration (3_Game layer)
```
modded class ParticleList
{
    static const int LFPG_SPRINKLER_SPRAY = RegisterParticle(
        "LFPowerGrid/data/particles/", "lfpg_sprinkler_spray");
    static const int LFPG_OVERLOAD_SPARKS = RegisterParticle(
        "LFPowerGrid/data/particles/", "lfpg_overload_sparks");
};
```

### AddonBuilder filter (include .ptc .emat .edds)
```
*.emat;*.edds;*.meta;*.ptc;*.c;*.imageset;*.layout;*.ogg;*.json;*.xml;*.paa;*.rvmat
```

---

## LFPG INTEGRATION PATTERNS (summary)

Full code: `references/lfpg-integration-patterns.md`

**Pattern A** — FireplaceBase helpers: `LFPG_PlayParticle(out Particle, id, pos)` /
`LFPG_StopParticle(out Particle)` with null-safety and server guard.

**Pattern B** — SyncVar toggle: server sets state→SetSynchDirty, client
creates/destroys in LFPG_OnVarSync.

**Pattern C** — One-shot sparks: non-looping (Repeat 0) particles auto-delete,
no cleanup needed. Use for overload events.

**Pattern D** — SEffectManager wrapper: for combining particle+sound. Cleanup
ONLY via SEffectManager.DestroyEffect().

**Pattern E** — Runtime parameter tuning: SetParameter for AIR_RESISTANCE,
ScaleParticleParamFromOriginal for SIZE.

**Cleanup contract**: EVERY device with looping particles MUST clean up in
EEDelete + LFPG_OnWiresCut + destructor.

---

## PITFALLS AND HARD RULES

1. **Particles are CLIENT-ONLY.** Wrap in `#ifndef SERVER`.
2. **Looping particles (Repeat 1) NEVER end.** MUST Stop() + null ref.
3. **Stop() is gradual.** Use StopParticleFlags.IMMEDIATE for instant removal.
4. **ObjectDelete(particle)** valid for ParticleSource with DisableAutoDestroy().
5. **Render distance ~200m.** Engine limit, no workaround.
6. **Duplicate filenames** across mods: use unique prefixes (`lfpg_`).
7. **ParticleManager.GetInstance()** returns null on server. Always null-check.
   Guards 1 and 7 are complementary, not redundant: `#ifndef SERVER` (pitfall 1) is
   compile-time exclusion for whole client-only blocks; the null-check (this pitfall)
   is runtime safety for code compiled on both sides (a diag/SP client-server build has
   no SERVER define but still runs server-side). Side checks: `enforce-script-reference`
   hard rules 19-20.
8. **SEffectManager.DestroyEffect()** is the ONLY safe Effect cleanup.
9. **AIR_RESISTANCE** controls smoke rise. FireplaceBase adjusts for ceilings.
10. **force_world_rotation=true** for smoke/steam that should always rise up.
11. **.meta files NOT needed** for mod runtime.
12. **GUIDs mandatory** when referencing vanilla .emat/.edds from mod .ptc.
13. **.ptc is PLAIN TEXT.** Can be generated by Python scripts, no Workbench needed.
14. **EffectTime + Repeat** interact: EffectTime is the master curve cycle, Repeat
    loops the entire effect. One-shot (Repeat 0) plays once for EffectTime duration.

---

## VANILLA PARTICLE CATALOG — KEY CATEGORIES

Full catalog: `references/vanilla-particle-catalog.md` (276 entries; version-dependent).

### Electricity
`POWER_GENERATOR_SMOKE` (1 emitter, loop), `BARBED_WIRE_SPARKS` (1 emitter, one-shot)

### Water
`WATER_JET` (2 emitters, loop), `WATER_JET_WEAK` (2 emitters, loop),
`WATER_SPILLING`, `DROWNING_BUBBLES`

### Fire
`CAMP_SMALL_FIRE` (6 emitters), `CAMP_STOVE_FIRE`, `BONFIRE_FIRE`

### Smoke/Steam
`CAMP_SMALL_SMOKE` (1 emitter), `CAMP_STEAM_2END`, `EVAPORATION`, `SPOOKY_MIST`

### Environment
`ENV_SWARMING_FLIES`, `SMOKING_HELI_WRECK`, `HOTPSRING_WATERVAPOR`,
`GEYSER_NORMAL`, `GEYSER_STRONG`, `VOLCANO`

---

## REFERENCE FILES

- `references/standalone-particle-reference.md` — standalone predecessor reference: multi-emitter composition (PLANES_EX/IMPACT/BOOM), animated + Mast curves, CfgCloudlets conversion. [merged 2026-06-05]

- `references/vanilla-particle-catalog.md` — 276 vanilla particles by category (version-dependent)
- `references/lfpg-integration-patterns.md` — 5 LFPG code patterns
- `references/ptc-format-reference.md` — 56-property .ptc reference with vanilla examples
- `references/emat-format-reference.md` — .emat format, both shader types, all 12 properties
- `references/script-api-reference.md` — Particle/ParticleSource/ParticleManager signatures
- `references/answeroverflow-2026-05-17.md` — community snippets verified vs vanilla (PlayOnObject pattern with client guard)

## Effect areas (`cfgeffectarea.json`): emitter budget and vertical band (added 2026-08-31)

Run these gates **before** choosing a large contaminated-area radius.

### Hard particle budget

Each effect area has a hard cap of 1,000 emitters: `const int PARTICLES_MAX = 1000`
(`VANILLA/scripts/4_world/classes/contaminatedarea/effectarea.c:84`), enforced while
`SpawnParticles` fills the area (`:421`). Exceeding it does not shrink the damage radius. The area
can remain lethal beyond the visible particle core and logs
`Not enough particles in pool for EffectArea` (`:440`). A valid JSON and a booting server do not
prove that the perimeter is visible.

For the static `FillWithParticles` route, budget first with:

```text
N = ceil((Radius + OuterOffset - InnerPartDist/2) / InnerPartDist)
emitters ~= 6.283 * N^2 * (VerticalLayers + 1)
```

Vanilla computes `circumference = 2 * Math.PI2 * ringRadius` (`effectarea.c:389`) while
`Math.PI2` is already 6.28318530717958 (`VANILLA/scripts/1_core/proto/enmath.c:13`). That quirk
uses approximately `4*pi*r`, twice the ordinary circumference. Budgeting with `2*pi*r` therefore
under-counts. Increasing `InnerPartDist` lowers the ring count `N`; it does not reduce the emitter
count within an existing ring.

For static areas, only `InnerPartDist` and `OuterOffset` feed this route
(`contaminatedarea.c:70`). `InnerRingCount`, `OuterPartDist`, and `OuterRingToggle` belong to
`PlaceParticles` and are inert here. Do not tune them to solve a static-area density problem.

### Damage and visibility are vertically bounded

The trigger is a finite cylinder, built by
`SetCollisionCylinderTwoWay(radius, -(NegHeight + c), PosHeight - c)` with
`c = (PosHeight - NegHeight) * 0.5` (`effectarea.c:495-497`). Particle placement is culled against
the same band after snapping to terrain (`:413,421`). Choose `PosHeight` and `NegHeight` from the
actual elevation range inside the radius, not from a small vanilla zone. Underground spaces also
count: particles snap to `SurfaceY` and are never spawned below terrain, so a bunker can be lethal
inside the cylinder while showing no gas. That can be deliberate, but it must not be accidental.

### Safe positions and schema

`SafePositions` is global, not attached to one area. `GetClosestSafePos` searches the whole array in
2D (`VANILLA/scripts/4_world/static/miscgameplayfunctions.c:1698,1717`) during the early-presence
rescue path (`:1692`; caller `areaexposure.c:44`). After any radius change, measure every safe
position against every area; a rescue point inside another cylinder can teleport a reconnecting
player from gas to gas.

Treat `JsonDataContaminatedArea` as the schema authority
(`VANILLA/scripts/4_world/classes/contaminatedarea/jsondatacontaminatedarea.c:17-34`). Community
fields named `InnerRingRatio` and `OuterRingRatio` are not in that schema. Large-radius height values
remain `[VERIFY IN GAME]` until the real terrain and underground depth are measured.

## Correction: effect-area budget and pool diagnostics (added 2026-08-31)

This section supersedes the approximate `6.283 * N^2` budget and the RPT claim above. For the normal
large-area branch (`R >= 1.25 * s`), use the same rounded ring spacing and per-ring floors as
`FillWithParticles`:

```text
R = Radius + OuterOffset
s = max(InnerPartDist, 1)
N = ceil((R - s/2) / s)
d = (R - s/2) / N
XZ = 1 + sum(floor(2 * PI2 * d * k / s), k = 1..N)
budget_max = XZ * (VerticalLayers + 1)
```

`PI2` is `2*pi`, so the source's `2 * PI2 * ringRadius` remains the intentional doubled
circumference. The center emitter is the leading `1`. Small areas take separate one-ring/center
branches in `effectarea.c:360-373`; use those branches directly rather than this large-area formula.
As a check, `Radius=500`, `OuterOffset=20`, `InnerPartDist=70`, and `VerticalLayers=1` give
`N=7`, `d=69.286`, `XZ=346`, and `budget_max=692`.

Reaching `PARTICLES_MAX` truncates additional visual emitters in `SpawnParticles`
(`effectarea.c:411-426`) but does **not** itself log `Not enough particles in pool`. That error is in
`InsertParticles` and means `ParticleManager` returned fewer objects than the count requested
(`:429-447`). Do not use the RPT message as the cap gate. Vertical culling can reduce the actual
count, but an approximation that under-counts cannot authorize a radius; calculate the upper budget
and confirm the visible perimeter in game.

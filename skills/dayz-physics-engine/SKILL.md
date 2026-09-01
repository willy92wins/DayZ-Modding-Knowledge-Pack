---
name: dayz-physics-engine
description: "Use when: física DayZ, dBody, collision layers, player walks through my object, action/cursor does not appear, EOnContact, TransportHit, thrown/rolling objects. Not vehicle authoring: dayz-vehicles; not flight: dayz-aviation."
---

# DayZ Engine Physics (Enforce Script)

Engine-truth reference for rigid-body work in DayZ mods. Every API claim below was verified against
the decompiled vanilla v1.24 scripts; citations are `path:line` relative to the script root (treat
line numbers as ±3 — minor drift between builds). When something common-sounding is missing here,
check section "What does NOT exist" before assuming it exists.

## How to use this skill

The body covers the 90% working set. Three bundled references hold the full deep-dives — load them
only when the task needs that depth:

| Reference | Read it when |
|---|---|
| `references/fisica-engine-deep-dive.md` | full dBody/dGeom/dJoint signatures, raycast family tables, surfaces, drop-physics lifecycle details |
| `references/transport-netsync-vehiculos.md` | anything about why/how vehicles replicate, CarScript damage-by-momentum, Pawn/TransportOwnerState, push-action pattern |
| `references/dano-transporthit.md` | damage pipeline (MDF), EEHitBy chain, the complete TransportHit flow line-by-line, hitzones, armor reality |

## The 9 engine truths (prevent the classic bugs)

1. **A body only collides where it exists.** The player capsule (CCT) is simulated client-side
   (`3_game/human.c:1397-1418`). A rigid body created only on the server can never block a player —
   the client's CCT has nothing to collide with. This is architectural; no layer mask fixes it.
2. **The action cursor sees View Geometry, not physics.** Action targeting uses `RaycastRVProxy`
   with default `ObjIntersectView` (`4_world/classes/useractionscomponent/actiontargets.c:214-219`,
   default at `3_game/global/dayzphysics.c:88`). No View Geometry LOD in the .p3d → no action, no
   admin-tool selection, regardless of any physics body.
3. **`dSetInteractionLayer` is GLOBAL.** It edits the world's layer↔layer interaction matrix
   (`1_core/physics/physicsworld.c:14-21`); the first parameter only resolves the world. To stop two
   specific entities from colliding use the surgical pair-block instead:
   `dBlock b = dBodyCollisionBlock(entA, entB); ... dBodyRemoveBlock(world, b);` (`1_core/proto/enphysics.c:116-117`).
4. **Friction/restitution are material strings, not setters.** They come from the physics material
   assigned per-geometry (`PhysicsGeomDef.MaterialName`, e.g. `"material/default"` —
   `1_core/physics/physicsgeomdef.c:18-24`) and surface definitions (.bisurf / CfgSurfaces). There is
   no `dBodySetFriction`-style API (0 matches in all of scripts/). Measured (BenchRE 2026-08-26):
   .bisurf `restitution` does not translate into bounce on the native item path — SmallStone dropped
   from 5 m onto open-field terrain rebounds 0.02-10 mm (apparent e = 0.009-0.046, n=6).
5. **Transport replicates because it is a Pawn.** `Transport extends Pawn` with continuous
   `TransportOwnerState` (world transform + linear + angular velocity) streamed to all proxies
   (`3_game/vehicles/transport.c:13-30,52-53`; `3_game/entities/pawn.c:20-24`). `ItemBase` is not a
   Pawn: clients get only occasional entity snapshots — never velocities. A free dynamic body on an
   ItemBase looks "synced" only at low latency/local tests.
6. **The native throw path runs on server AND owner client.** `HandActionThrow` guards with
   `GetInstanceType() != INSTANCETYPE_REMOTE` before `item.ThrowPhysically(player, force)`
   (`3_game/systems/inventory/hand_actions.c:77-81`). That is why thrown items collide for the
   thrower. Whether REMOTE clients get a local body is not visible in scripts — treat third-party
   collision as unverified until tested in-game.
7. **Drop/throw physics is temporary by design.** It is governed by a lifetime:
   `StopItemDynamicPhysics()` kills it via `SetDynamicPhysicsLifeTime(0.01)`
   (`4_world/entities/itembase.c:4530-4534`). A long-rolling object must renew/extend the lifetime or
   avoid depending on the drop path. Measured (BenchRE 2026-08-26): the default lifetime is exactly
   **15 s** (n=2, `dBodyIsDynamic` polled at 4 Hz flips at t=15.00); `SetDynamicPhysicsLifeTime(3600)`
   is honored (still dynamic past a 300 s watchdog).
8. **A player's EOnContact only reacts to Transport.** `DayZPlayerImplement.EOnContact` casts
   `Transport.Cast(other)` and ignores everything else (`4_world/entities/dayzplayerimplement.c:3814-3829`).
   A custom ItemBase that should hurt players must detect the contact itself and call
   `target.ProcessDirectDamage(...)` from its own `EOnContact`.
9. **Script impulses push corpses, not living players.** Vanilla applies `dBodyApplyImpulse` to the
   victim only when `IsDamageDestroyed()` (ragdoll) — `3_game/entities/entityai.c:4111-4115`. Living
   players are displaced by the contact solver itself (both bodies present + interacting layers), not
   by script.

## API quick map (verified signatures)

### Create / destroy (`1_core/proto/enphysics.c`)

```c
proto bool dBodyCreateStaticEx (notnull IEntity ent, PhysicsGeomDef geoms[]);                        // :38
proto bool dBodyCreateGhostEx  (notnull IEntity ent, PhysicsGeomDef geoms[]);                        // :39
proto bool dBodyCreateDynamicEx(notnull IEntity ent, vector centerOfMass, float mass, PhysicsGeomDef geoms[]); // :51
proto native void dBodyDestroy(notnull IEntity ent);                                                 // :54
proto native bool dBodyIsSet(notnull IEntity ent);                                                   // :57
```
- `PhysicsGeomDef(string name, dGeom geom, string materialName, int layerMask)` + public `Frame[4]`,
  `ParentNode` (`1_core/physics/physicsgeomdef.c:9-26`).
- Geoms: `dGeomCreateBox(size)` :186, `dGeomCreateSphere(radius)` :189, `dGeomCreateCapsule` :192,
  `dGeomCreateCylinder` :195, `dGeomDestroy` :198.
- `dBodyCreateDynamic/Static` (no `Ex`) exist only under `#ifdef GAME_TEMPLATE`
  (`2_gamelib/entities/scriptmodel.c:31,35`) — they do not compile in DayZ. The wrapper
  `Physics.CreateDynamic(ent, mass, layerMask)` builds geometry from the entity's .p3d
  (`1_core/physics/physics.c:189`).
- Recreate pattern: always `if (dBodyIsSet(this)) dBodyDestroy(this);` before re-creating.

### State, damping, sleep, CCD

```c
dBodySetInteractionLayer(ent, mask)            // :59  (per body)   dBodyGetInteractionLayer :60
dBodyActive(ent, ActiveState.X)                // :64  INACTIVE | ACTIVE | ALWAYS_ACTIVE (activestate.c:9-17)
dBodyDynamic(ent, bool)                        // :65
dBodyEnableGravity(ent, bool)                  // :69  bool only — no vector
dBodySetDamping(ent, linear, angular)          // :70
dBodySetSleepingTreshold(body, lin, ang)       // :71
dBodyEnableCCD(body, maxMotion, castRadius)    // :83  (-1 disables) anti-tunneling
dBodySetLinearFactor(body, vector)             // :87  zero an axis => 2D physics
dBodyGetMass / dBodySetMass                    // :122-123
```

### Impulses, forces, velocities

```c
dBodyApplyImpulse(body, impulse)               // :141
dBodyApplyImpulseAt(body, impulse, worldPos)   // :136  off-center => natural torque/roll
dBodyApplyForce / dBodyApplyForceAt            // :146 / :151
dBodyApplyTorque / dBodyApplyTorqueImpulse     // :153 / :125
GetVelocity(ent) / SetVelocity(ent, v)         // :104 / :111  global functions (work on Man too)
dBodyGetAngularVelocity / dBodySetAngularVelocity  // :158 / :165  rad/s per axis, NOT yaw/pitch/roll
dBodyGetVelocityAt(body, worldPos)             // :177
dBodySetTargetMatrix(body, matrix, timeslice)  // :170  kinematic move
dBodyGetKineticEnergy(body)                    // :175
```
Wrapper-only extras: `Physics.ClearForces/GetTotalForce/GetTotalTorque/SetResponseIndex`
(`physics.c:106-115`); constants `Physics.STANDARD_GRAVITY(9.81)/VGravity/KMH2MS` (`physics.c:18-21`).

### Interaction layers (`3_game/global/dayzphysics.c:1-43`)

`PhxInteractionLayers` (bit order): NOCOLLISION, DEFAULT, BUILDING, CHARACTER, VEHICLE, DYNAMICITEM,
DYNAMICITEM_NOCHAR, ROADWAY, VEHICLE_NOTERRAIN, CHARACTER_NO_GRAVITY, RAGDOLL_NO_CHARACTER/FIREGEOM,
DOOR, RAGDOLL, WATERLAYER, TERRAIN, GHOST, WORLDBOUNDS, FENCE, AI, AI_NO_COLLISION, AI_COMPLEX,
TINYCAPSULE, TRIGGER, TRIGGER_NOTERRAIN, ITEM_SMALL, ITEM_LARGE, CAMERA, TEMP.

Runtime query pattern (vanilla, `3_game/vehicles/transport.c:556-557`):
```c
int layer = dBodyGetInteractionLayer(obj);
bool blocksPlayer = dGetInteractionLayer(this, PhxInteractionLayers.CHARACTER, layer);
```
Use the same query to log whether `CHARACTER × DYNAMICITEM` is active when debugging "walks through".

### Raycast / overlap families (`3_game/global/dayzphysics.c:123-230`)

Two separate worlds — pick the right one:

| Family | Sees | Use for |
|---|---|---|
| `RaycastRV` :199 / `RaycastRVProxy` :208 | RV geometries via `ObjIntersect*`: Fire(0), View(1), Geom(2), IFire(3), None(4) (:66-71) | cursor/action targeting, hit surfaces, melee aim |
| `RayCastBullet` :211, `SphereCastBullet` :213, `*OverlapBullet` :216-228 | Bullet physics world, filtered by `PhxInteractionLayers` | physical LOS, ground probes, area queries on bodies |

`CollisionFlags` (FIRSTCONTACT, NEARESTCONTACT, ONLYSTATIC, ONLYDYNAMIC, ONLYWATER, ALLOBJECTS) —
`1_core/proto/endebug.c:140-148`. Overlap callback: `CollisionOverlapCallback.OnContact(IEntity, Contact)`
(`dayzphysics.c:115-121`). Action-cursor ground fallback uses `RayCastBullet` with
`ROADWAY|TERRAIN|WATERLAYER` (`actiontargets.c:329-331`).

### Contacts

`sealed class Contact` (`1_core/physics/contact.c:9-50`): `Impulse` (:21), `Normal`, `Position`,
`PenetrationDepth`, `RelativeVelocityBefore/After`, `GetNormalImpulse()` (:47). Receive it via
`SetEventMask(EntityEvent.CONTACT)` → `override void EOnContact(IEntity other, Contact extra)`
(`1_core/proto/enentity.c:213`). Vanilla measures impact magnitude with
`extra.RelativeVelocityBefore.Length()` (`3_game/entities/inventoryitem.c:200`, threshold 0.3,
throttled 0.33 s) — not with `Impulse`. `Transport.OnContact` warns "Can be called very frequently in
one frame" (`4_world/entities/vehicles/carscript.c:1453`): buffer contacts, process once per tick
(vanilla caches and consumes in `EOnPostSimulate`).

### Native dynamic-item path (drop/throw)

```c
// 3_game/entities/inventoryitem.c
proto native void EnableCollisionsWithCharacter(bool state);   // :21
proto native void ThrowPhysically(DayZPlayer player, vector force, bool collideWithCharacters = true); // :26
// 3_game/entities/object.c
proto native void CreateDynamicPhysics(int interactionLayers); // :462  (never called by vanilla script)
proto native void EnableDynamicCCD(bool state);                // :463
proto native void SetDynamicPhysicsLifeTime(float lifeTime);   // :464
```
Lifecycle: throw (`hand_actions.c:62-88`, server+owner) · inventory dump uses
`ThrowPhysically(null, force, false)` (`4_world/static/miscgameplayfunctions.c:1164-1220`) · admin
spawn-with-gravity uses `item.ThrowPhysically(null, "0 0 0")` server-side
(`4_world/plugins/pluginbase/plugindeveloper.c:381,504`) · re-config hook
`override void OnCreatePhysics()` (`itembase.c:1222-1227`; real overrides in tentbase.c, fireplace.c,
batterycharger.c). The `DYNAMICITEM` / `DYNAMICITEM_NOCHAR` pair maps to `collideWithCharacters`
by naming (inference — internal assignment not script-visible).

### Player CCT (`3_game/human.c`)

`PhysicsIsFalling` :1397, `PhysicsGetFloorEntity` :1400, `PhysicsGetLinkedEntity` :1403,
`PhysicsGetVelocity` :1410, `PhysicsEnableGravity` :1412, `PhysicsSetSolid` :1414-1415,
`PhysicsSetRagdoll` :1418 ("sets and synchronize interaction layers RAGDOLL..."),
`CheckFreeSpace` :1354, `CollisionMoveTest` :1357, `LinkToLocalSpaceOf` :1361.

### Joints

`dJointCreateHinge/Hinge2/Slider/BallSocket/Fixed/ConeTwist/6DOF/6DOFSpring(..., bool block, float breakThreshold)`
+ per-type setters (`enphysics.c:212-270`); break event `EOnJointBreak` (`1_core/proto/enentity.c:207`).

### Surfaces

`SurfaceInfo` (`3_game/surfaceinfo.c:8-51`): GetByName/GetByFile, roughness/dustness/penetrability,
IsLiquid/IsSolid, step/wheel particle ids. Detection: `CGame.GetSurface/SurfaceY/SurfaceGetType/
SurfaceUnderObject/SurfaceGetNormal` (`3_game/global/game.c:1160-1187`). Impact surface:
`DayZPhysics.GetHitSurfaceAndLiquid` (`dayzphysics.c:206`; used `inventoryitem.c:168-176`). No
friction getters — see truth #4.

## Recipes

**A. Custom dynamic sphere body (server-side baseline)**
```c
PhysicsGeomDef geoms[] = {PhysicsGeomDef("", dGeomCreateSphere(0.5), "material/default",
    PhxInteractionLayers.DYNAMICITEM)};
dBodyCreateDynamicEx(this, GetCenterOfMassOffset(), 80.0, geoms);
dBodySetInteractionLayer(this, PhxInteractionLayers.DYNAMICITEM);
dBodyActive(this, ActiveState.ALWAYS_ACTIVE);     // no mid-slope sleep
dBodySetDamping(this, 0.05, 0.2);
dBodyEnableCCD(this, 0.4, 0.45);                  // ~diameter*0.8, inner radius
```
Remember truth #1: created only server-side, players walk through it.

**B. Native path (recommended for items that must block/hit players)**
```c
// run on server AND owner client (replicate the hand_actions.c:77 guard):
item.ThrowPhysically(null, impulse, true);   // true => collides with CHARACTER
item.EnableDynamicCCD(true);
item.SetDynamicPhysicsLifeTime(3600);        // renew for long rolling [validate in-game]
```
Model requirements: Geometry LOD (collision), View Geometry (cursor — truth #2), FireGeometry (bullets).

**C. Contact damage to players (vehicle-parity, from the stone side)**
```c
void MyItem() { SetEventMask(EntityEvent.CONTACT); }
override void EOnContact(IEntity other, Contact extra)
{
    if (!g_Game.IsServer()) return;
    EntityAI target = EntityAI.Cast(other);
    if (target && target.IsAlive())
    {
        float speed = GetVelocity(this).Length();          // m/s
        if (speed > 0.5 && m_CanHit)                        // guard vs multi-contact per tick
        {
            m_CanHit = false;                               // reset via timer or target EEHitBy
            target.ProcessDirectDamage(DT_CUSTOM, this, "", "TransportHit", "0 0 0", speed);
        }
    }
}
```
`damageCoef` IS the velocity: real damage = base damage of ammo `"TransportHit"` × coef
(`entityai.c:4086-4116`). The ammo lives in binary game data, not scripts. Vanilla resets its
one-hit guard in the victim's `EEHitBy` (`dayzplayerimplement.c:1551`). Corpse launch only:
`impulse = 40 * velocity; impulse[1] = 60; dBodyApplyImpulse(victim, impulse);` gated by
`IsDamageDestroyed()` (truth #9). Full pipeline: `references/dano-transporthit.md`.

**D. Push action (vanilla parity)**
`ActionPushCar` applies `dBodyApplyImpulseAt(car, impulse, car.ModelToWorld(car.GetEnginePos()))`
(`4_world/classes/useractionscomponent/actions/continuous/actionpushcar.c:52`). Off-center
application point gives natural roll. Stamina cost is one line: `EStaminaModifiers.PUSH_CAR` already
exists (`3_game/enums/estaminamodifiers.c:13`).

**E. Wake a sleeping body before impulses**
`dBodyActive(ent, ActiveState.ACTIVE); dBodyDynamic(ent, true);` then apply the impulse — impulses
on sleeping bodies are lost.

## Debugging physics

- Visual overlay works in retail builds: `Shape.CreateSphere(0x88FF0000, ShapeFlags.TRANSP|ShapeFlags.NOZBUFFER, pos, r)`
  and `Shape.CreateLines(...)` with `ShapeFlags.ONCE` for per-frame draws (`1_core/proto/endebug.c:114-230`;
  never keep a pointer to a ONCE shape).
- Log the layer matrix at runtime with the `dGetInteractionLayer` query pattern above.
- Count world bodies: `dGetNumDynamicBodies(world)` / `dGetDynamicBody(world, i)` (`enphysics.c:9-10`).
- Fast iteration: DayZDiag_x64 + `-filePatching` reloads scripts without PBO rebuild (no BattlEye, no
  signature checks); see the dayz-mod-workflow skill §6 for the full loop.

## What does NOT exist (verified: 0 matches in scripts/)

| Plausible-sounding API | Reality |
|---|---|
| `dBodySetFriction` / `SetRestitution` / `SetBounciness` | physics material string per geometry + .bisurf only |
| per-body gravity vector (`dBodySetGravity`) | only `dBodyEnableGravity(ent, bool)` and global `dSetGravity(world, g)` (`enphysics.c:17`) |
| `dBodySetVelocity` / `dBodyGetVelocity` | global `SetVelocity/GetVelocity` (`enphysics.c:104,111`) |
| `dBodyApplyAngularImpulse` | `dBodyApplyTorqueImpulse` (`enphysics.c:125`) |
| `AddForce` (Unity-style) | `dBodyApplyForce*` |
| `SetMaxLinearVelocity` clamp | clamp manually per tick |
| `PhxRaycast*` | the physics-world casts are the `*Bullet` family in `DayZPhysics` |
| `EOnSimulate` on CarScript | car physics is 100% native; script only calls Set* controls |
| vanilla script call to `CreateDynamicPhysics` | declared but never called from script — no vanilla usage pattern |
| `Synchronize()` on EntityAI/ItemBase | Transport-only (`transport.c:108-109`) |

## Sleep/active enum

`enum ActiveState { INACTIVE, ACTIVE, ALWAYS_ACTIVE }` (`1_core/physics/activestate.c:9-17`).
`ALWAYS_ACTIVE` prevents mid-slope sleep for objects that must keep simulating.

## Cross-skill pointers

- `enforce-script-reference` — language rules, RPC/SyncVars, config.cpp, action system basics.
- `dayz-p3d-audit` / `dayz-model-pipeline` — building the Geometry/ViewGeo/FireGeo LODs that physics
  and the cursor require.
- `dayz-mod-workflow` — implementation protocol + DayZDiag/filePatching fast loop.
- `dayz-sound-system` — impact/rolling audio driven from contact events (client-only rules).

## PhysicsSetRagdoll sobre un jugador VIVO — evidencia empírica (added 2026-06-11)

Origen: LFSlidingFloor spike B, test in-game 2026-06-10 (script logs con telemetría completa). Actualiza la expectativa previa "sin uso público sobre vivos / probablemente no simula":

- **SERVER-SIDE SÍ SIMULA**: con (1) DisableSimulation(false) antes del toggle (paridad con el flujo de muerte, dayzplayerimplement.c:726), (2) pre-wake `dBodyActive(p, ActiveState.ACTIVE)` + `dBodyDynamic(p, true)`, (3) `dBodyApplyImpulse(p, V*masa)` — dBodyGetMass devolvió masa real del player (87.5 kg) y el impulso prendió a la primera (sin necesidad de SetVelocity). El cuerpo deslizó 77.6 m a 4-6.7 m/s siguiendo el terreno (cuestas arriba incluidas — fricción efectiva bajísima).
- **OWNER CLIENT NO**: el avatar local nunca ragdollea — sigue de pie y controlable (movimiento client-authoritative). Desync total server-owner. Ragdoll-en-vivo solo es viable end-to-end con sync custom de posición (ver LL-138).
- El toggle `PhysicsSetRagdoll(false)` NO rubber-bandea: la entidad queda exactamente donde terminó el cuerpo (pos pre == post, verificado).
- **PELIGRO get-up**: `StartCommand_Unconscious(0)` + `WakeUp` a los 0.5 s dejó al player server-side 40 m BAJO el terreno, con caída al vacío, uncon real y muerte. La protección vanilla anti-wake-early es de 2 s (playerbase.c:3169-3172); no se re-iteró (el desync ya invalidaba el enfoque).

## Cuerpos script sobre items vanilla — evidencia empírica BenchRE (added 2026-08-26)

Corrida DayZDiag 1.29 server+cliente, mod BenchRE build 0004. Evidencia:
`C:\Users\<you>\dayz_re_scratch\bench_results\` (CSVs + logs crudos); síntesis con las 7
preguntas de la matriz en `C:\Users\<you>\dayz_re_scratch\physics_matrix.md` §6.

- **`Physics.CreateDynamic` / `CreateDynamicEx` / `CreateStaticEx` devuelven falsy sobre
  InventoryItem vanilla** (SmallStone/WoodenStick spawneados con `CreateObjectEx`): 7/7 intentos
  server-side. El path NATIVO sobre los mismos items funciona (`ThrowPhysically` +
  `SetDynamicPhysicsLifeTime` + `dBodyIsDynamic` leído 2402 ticks). Los items ya poseen cuerpo
  nativo y la familia `Create*Ex` no se adhiere a ellos — coincide con sus 0 usos gameplay en
  vanilla. Un host viable para cuerpos script debe carecer de física propia (sin validar aún:
  entidad custom estilo `scriptmodel.c`).
- **`DayZPhysics.GetHitSurfaceAndLiquid` no nombra superficies de TERRENO**: `RayCastBullet`
  sobre campo abierto devuelve hit_pos válido, pero la vía exige un Object y el terreno no lo
  es (6/6 sondas sin nombre). Para terreno: `CGame.SurfaceGetType(x, z, out type)`
  (`3_game/global/game.c:1166`) / `SurfaceGetType3D` (`game.c:1168`).
- **Cliente MP: `CreateObjectEx` sin `ECE_LOCAL` devuelve null** (n=2). Para geometría local de
  test en cliente añadir `ECE_LOCAL` (`3_game/ce/centraleconomy.c:24`; patrón cliente:
  `3_game/particles/particle.c:119`).

## Reglas promovidas del corpus de lecciones (added 2026-07-27)

Promovidas desde `AI/20_Knowledge/lessons-learned.md` para que lleguen por trigger en vez
de depender de que alguien recuerde buscarlas. Cada regla cita su `LL-NNN` de origen;
la entrada completa vive allí. No quites la cita: el índice detecta la promoción por ella.

- **LL-014** — Para cuerpos rodantes, usa damping lineal y angular muy bajos pero no nulos y ajusta el sleeping threshold. No minimices la fricción de contacto: vive en `.bisurf`; si desliza sin girar, súbela, y si vibra o no para, sube damping.

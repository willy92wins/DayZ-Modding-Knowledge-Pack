# Deep-dive: Engine-level physics (DayZ / Enfusion / Enforce Script)

> Investigation 2026-06-06 · Source of truth: decompiled vanilla scripts v1.24
> (`<dayz-projects>\scripts\`). All cited paths
> are relative to that folder. Everything cited with `path:line` was verified with Read/Grep.
> What is not verifiable in scripts is marked [UNVERIFIED] or [INFERRED].

---

## 1. Resumen ejecutivo

- The DayZ rigid body API lives in **global functions `dBody*`/`dGeom*`/`dJoint*`** declared in `1_core/proto/enphysics.c` (Bullet-style; ODE-type names). They operate on `IEntity` directly: the body is "attached" to the entity.
- There also exists a **wrapper class `Physics`** (`1_core/physics/physics.c`) with same functionality as methods (`ApplyImpulse`, `CreateDynamicEx`...), plus extras (`ClearForces`, `GetTotalForce`, `SetResponseIndex`, `AddGeom`). Vanilla DayZ gameplay almost exclusively uses global `dBody*` functions; wrapper is Enfusion-style API.
- **Interaction layers** (`PhxInteractionLayers`, `3_game/global/dayzphysics.c:1-43`) are bitmasks; layer↔layer matrix is **global per world** (`dSetInteractionLayer`), and each body/geom carries its mask (`dBodySetInteractionLayer`).
- **Raycasts**: two families. `RaycastRV/RaycastRVProxy` (RV geometries: Fire/View/Geom by `ObjIntersect*`) and `RayCastBullet/SphereCastBullet/...OverlapBullet` (Bullet physics world, filtered by `PhxInteractionLayers`). Action cursor uses **`RaycastRVProxy` with `ObjIntersectView` by default** — confirms cause of "Push does not appear" bug without View Geometry.
- **Contacts**: `sealed Contact` class (`1_core/physics/contact.c`) with `Impulse`, `Normal`, `Position`, velocities before/after. Received via `EOnContact` after `SetEventMask(EntityEvent.CONTACT)`.
- **Dynamic items native path**: `InventoryItem.ThrowPhysically(player, force, collideWithCharacters=true)` + `Object.CreateDynamicPhysics/EnableDynamicCCD/SetDynamicPhysicsLifeTime`. ⚠️RELEVANT: vanilla calls `ThrowPhysically` on **server AND owner client** (not on REMOTE) — body exists on both sides.
- **There do not exist** per-body friction/restitution setters, nor vector gravity per body, nor `dBodySetVelocity` (global `SetVelocity` is used). Friction/restitution come from **physical material** assigned to geometry (string in `PhysicsGeomDef.MaterialName` / .bisurf surface).

---

## 2. API verificada (firmas exactas)

### 2.1 Physics world (global)

```c
proto native int    dGetNumDynamicBodies(notnull IEntity worldEnt);          // enphysics.c:9
proto native IEntity dGetDynamicBody(notnull IEntity worldEnt, int index);   // enphysics.c:10
proto native void   dSetInteractionLayer(notnull IEntity worldEntity, int mask1, int mask2, bool enable); // enphysics.c:11
proto native bool   dGetInteractionLayer(notnull IEntity worldEntity, int mask1, int mask2);              // enphysics.c:12
proto native vector dGetGravity(notnull IEntity worldEntity);                // enphysics.c:15
proto native void   dSetGravity(notnull IEntity worldEntity, vector g);      // enphysics.c:17 (GLOBAL, no por body)
proto native void   dSetTimeSlice(notnull IEntity worldEntity, float timeSlice); // enphysics.c:19 — default 1/40 (sim a 40 fps)
```
Equivalente OO: `PhysicsWorld.SetInteractionLayer/GetGravity/SetGravity/GetTimeSlice/GetUpdateRate/SetUpdateRate(20..1000)` (`1_core/physics/physicsworld.c:21-48`).

### 2.2 Creation / destruction of bodies

```c
proto bool dBodyCreateStaticEx (notnull IEntity ent, PhysicsGeomDef geoms[]);                       // enphysics.c:38
proto bool dBodyCreateGhostEx  (notnull IEntity ent, PhysicsGeomDef geoms[]);                       // enphysics.c:39
proto bool dBodyCreateDynamicEx(notnull IEntity ent, vector centerOfMass, float mass, PhysicsGeomDef geoms[]); // enphysics.c:51
proto native void dBodyDestroy(notnull IEntity ent);   // enphysics.c:54
proto native bool dBodyIsSet(notnull IEntity ent);     // enphysics.c:57
```
- `PhysicsGeomDef(string name, dGeom geom, string materialName, int layerMask)` with `Frame[4]` (local transform) and `ParentNode` (bone) as public fields — `1_core/physics/physicsgeomdef.c:9-26`.
- Official doc example: `PhysicsGeomDef("", dGeomCreateBox(size), "material/default", 0xffffffff)` (`enphysics.c:34`).
- Static wrapper: `Physics.CreateStatic(ent, layerMask)`, `Physics.CreateDynamic(ent, mass, layerMask)` (from VObject/p3d geometry), `Physics.CreateDynamicEx/CreateStaticEx/CreateGhostEx` (`1_core/physics/physics.c:170-210`). ATTENTION: globals `dBodyCreateStatic/dBodyCreateDynamic` (without Ex, with layerMask) only appear used in `2_gamelib/entities/scriptmodel.c:31,35` under `#ifdef GAME_TEMPLATE` and **are not declared** in `enphysics.c` → in DayZ use wrapper `Physics.CreateDynamic` or `*Ex`.

### 2.3 Estado, masa, damping, sleep, CCD

```c
proto native void  dBodySetInteractionLayer(notnull IEntity ent, int mask);          // enphysics.c:59
proto native int   dBodyGetInteractionLayer(notnull IEntity ent);                    // enphysics.c:60
proto native void  dBodySetGeomInteractionLayer(notnull IEntity ent, int index, int mask); // enphysics.c:61
proto native int   dBodyGetGeomInteractionLayer(notnull IEntity ent, int index);     // enphysics.c:62
proto native void  dBodyActive(notnull IEntity ent, ActiveState activeState);        // enphysics.c:64
proto native void  dBodyDynamic(notnull IEntity ent, bool dynamic);                  // enphysics.c:65
proto native bool  dBodyIsDynamic(notnull IEntity ent);                              // enphysics.c:66
proto native bool  dBodyIsActive(notnull IEntity ent);                               // enphysics.c:68
proto native bool  dBodyEnableGravity(notnull IEntity ent, bool enable);             // enphysics.c:69 (bool, NO vector)
proto native void  dBodySetDamping(notnull IEntity ent, float linearDamping, float angularDamping); // enphysics.c:70
proto native void  dBodySetSleepingTreshold(notnull IEntity body, float linearTreshold, float angularTreshold); // enphysics.c:71
proto native bool  dBodyIsSolid(notnull IEntity ent);                                // enphysics.c:73
proto native void  dBodySetSolid(notnull IEntity ent, bool solid);                   // enphysics.c:74
proto native void  dBodyEnableCCD(notnull IEntity body, float maxMotion, float sphereCastRadius); // enphysics.c:83 (-1 para desactivar)
proto native void  dBodySetLinearFactor(notnull IEntity body, vector linearFactor);  // enphysics.c:87 (zero an axis => 2D physics)
proto native float dBodyGetMass(notnull IEntity ent);                                // enphysics.c:122
proto native void  dBodySetMass(notnull IEntity body, float mass);                   // enphysics.c:123
proto native void  dBodySetInertiaTensorV(notnull IEntity body, vector v);           // enphysics.c:119
proto native void  dBodySetInertiaTensorM(notnull IEntity body, vector m[3]);        // enphysics.c:120
proto native vector dBodyGetCenterOfMass(notnull IEntity body);                      // enphysics.c:90
```
- `enum ActiveState { INACTIVE, ACTIVE, ALWAYS_ACTIVE }` — `1_core/physics/activestate.c:9-17`. ⚠️RELEVANT: `ALWAYS_ACTIVE` prevents the rock from falling asleep halfway down a slope.
- `enum SimulationState { NONE, COLLISION, SIMULATION }` — `1_core/physics/simulationstate.c:12-20` (via `Physics.ChangeSimulationState`, `physics.c:51`).

### 2.4 Impulsos, fuerzas, velocidades, transform

```c
proto void  dBodyApplyImpulse(notnull IEntity body, vector impulse);                  // enphysics.c:141
proto void  dBodyApplyImpulseAt(notnull IEntity body, vector impulse, vector pos);    // enphysics.c:136 (pos en WORLD)
proto void  dBodyApplyForce(notnull IEntity body, vector force);                      // enphysics.c:146
proto void  dBodyApplyForceAt(notnull IEntity body, vector pos, vector force);        // enphysics.c:151
proto native void dBodyApplyTorque(notnull IEntity body, vector torque);              // enphysics.c:153
proto native void dBodyApplyTorqueImpulse(notnull IEntity ent, vector torqueImpulse); // enphysics.c:125
proto native vector GetVelocity(notnull IEntity ent);                                 // enphysics.c:104 (global, sirve para player)
proto native void   SetVelocity(notnull IEntity ent, vector vel);                     // enphysics.c:111 (global)
proto vector dBodyGetAngularVelocity(notnull IEntity body);                           // enphysics.c:158
proto void   dBodySetAngularVelocity(notnull IEntity body, vector angvel);            // enphysics.c:165 (rad/s por eje, no yaw/pitch/roll)
proto native vector dBodyGetVelocityAt(notnull IEntity body, vector globalpos);       // enphysics.c:177
proto native void  dBodySetTargetMatrix(notnull IEntity body, vector matrix[4], float timeslice); // enphysics.c:170 (move kinematic)
proto native void  dBodyGetWorldTransform(notnull IEntity body, out vector matrix[4]);       // enphysics.c:172
proto native void  dBodyGetDirectWorldTransform(notnull IEntity body, out vector matrix[4]); // enphysics.c:173
proto native float dBodyGetKineticEnergy(notnull IEntity body);                       // enphysics.c:175
// Pair-to-pair collision blocking:
proto native dBlock dBodyCollisionBlock(notnull IEntity ent1, notnull IEntity ent2);  // enphysics.c:116
proto native void   dBodyRemoveBlock(notnull IEntity worldEntity, dBlock block);      // enphysics.c:117
```
In `Physics` wrapper only: `ClearForces()`, `GetTotalForce()`, `GetTotalTorque()`, `SetResponseIndex(int)` (`physics.c:106-115`), `IsKinematic()` (`physics.c:63`), `GetGeomSurfaces(index, out array<SurfaceProperties>)` (`physics.c:160`).

### 2.5 Geometries and joints

```c
proto native dGeom dGeomCreateBox(vector size);                       // enphysics.c:186
proto native dGeom dGeomCreateSphere(float radius);                   // enphysics.c:189  ⚠️RELEVANTE (piedra)
proto native dGeom dGeomCreateCapsule(float radius, vector extent);   // enphysics.c:192
proto native dGeom dGeomCreateCylinder(float radius, vector extent);  // enphysics.c:195
proto native void  dGeomDestroy(dGeom geom);                          // enphysics.c:198
proto native int   dBodyGetGeom(notnull IEntity ent, string name);    // enphysics.c:202
proto native int   dBodyGetNumGeoms(notnull IEntity ent);             // enphysics.c:204
```
Joints (`enphysics.c:212-270`): `dJointCreateHinge/Hinge2/Slider/BallSocket/Fixed/ConeTwist/6DOF/6DOFSpring(ent1, ent2, ..., bool block, float breakThreshold)` + `dJointDestroy`. Setters por tipo: `dJointHingeSetLimits/SetAxis/SetMotorTargetAngle` (223-225), `dJointConeTwistSetLimits` (241), `dJoint6DOFSetLinearLimits/SetAngularLimits/SetLimit` (250-252), `dJoint6DOFSpringSetSpring` (255, stiffness=-1 && damping=-1 desactiva), slider completo (258-270). Rotura → evento `EOnJointBreak` (`1_core/proto/enentity.c:207`).

### 2.6 Interaction layers

`enum PhxInteractionLayers` — `3_game/global/dayzphysics.c:1-43` (orden = bit index):
`NOCOLLISION, DEFAULT, BUILDING, CHARACTER, VEHICLE, DYNAMICITEM, DYNAMICITEM_NOCHAR, ROADWAY, VEHICLE_NOTERRAIN, CHARACTER_NO_GRAVITY, RAGDOLL_NO_CHARACTER, FIREGEOM (redef. de RAGDOLL_NO_CHARACTER), DOOR, RAGDOLL, WATERLAYER, TERRAIN, GHOST, WORLDBOUNDS, FENCE, AI, AI_NO_COLLISION, AI_COMPLEX, TINYCAPSULE, TRIGGER, TRIGGER_NOTERRAIN, ITEM_SMALL, ITEM_LARGE, CAMERA, TEMP`.

Semantics (verified by usage):
- **Global matrix**: `dSetInteractionLayer(world, mask1, mask2, enable)` activates/deactivates interaction between layers for ENTIRE world (1st parameter = entity to obtain world; `physicsworld.c:14-21` documents it as "Modifies interaction matrix of interaction layers"). Confirms project gotcha.
- **Per body**: `dBodySetInteractionLayer(ent, mask)` assigns which layers that body belongs to; per individual geometry with `dBodySetGeomInteractionLayer`.
- **Matrix query**: vanilla pattern in `3_game/vehicles/transport.c:556-557`:
```c
int layer = dBodyGetInteractionLayer(o);
bool interacts = dGetInteractionLayer(this, PhxInteractionLayers.CHARACTER, layer);
```
(decides if an object blocks vehicle doors according to whether CHARACTER collides with its layer). ⚠️RELEVANT: same query serves to verify at runtime if `CHARACTER×DYNAMICITEM` is active.
- There are no reserved "CUSTOM" layers; `TEMP` is the last named bit. Creating a new layer = using an unused bit and activating pairs with `dSetInteractionLayer` [reasonable INFERENCE; without vanilla example].

### 2.7 Raycasts / shapecasts / overlaps (`DayZPhysics`, `3_game/global/dayzphysics.c:123-230`)

```c
proto static bool RaycastRV(vector begPos, vector endPos, out vector contactPos, out vector contactDir,
    out int contactComponent, set<Object> results = NULL, Object with = NULL, Object ignore = NULL,
    bool sorted = false, bool ground_only = false, int iType = ObjIntersectView, float radius = 0.0,
    CollisionFlags flags = CollisionFlags.NEARESTCONTACT);                                  // :199
proto static bool RaycastRVProxy(notnull RaycastRVParams in, out notnull array<ref RaycastRVResult> results,
    array<Object> excluded = null);                                                         // :208
proto static bool GetHitSurface(Object other, vector begPos, vector endPos, string surface);            // :204
proto static bool GetHitSurfaceAndLiquid(Object other, vector begPos, vector endPos, string surface, out int liquidType); // :206
proto static bool RayCastBullet(vector begPos, vector endPos, PhxInteractionLayers layerMask, Object ignoreObj,
    out Object hitObject, out vector hitPosition, out vector hitNormal, out float hitFraction);          // :211
proto static bool SphereCastBullet(vector begPos, vector endPos, float radius, PhxInteractionLayers layerMask, ...); // :213
proto static bool GeometryOverlapBullet(vector transform[4], dGeom geometry, PhxInteractionLayers layerMask, notnull CollisionOverlapCallback callback); // :216
proto static bool EntityOverlapBullet(...) / EntityOverlapSingleBullet(...) / SphereOverlapBullet(pos, radius, ...)
    / CylinderOverlapBullet(...) / CapsuleOverlapBullet(...) / BoxOverlapBullet(...);       // :218-228
```
- `RaycastRVParams` (`:49-92`): default `type` **`ObjIntersectView`** (`:88`); documented values `ObjIntersectFire(0), View(1), Geom(2), IFire(3), None(4)` (`:66-71`) — constants defined in engine, not in scripts.
- `RaycastRVResult` (`:98-113`): `obj/parent` (proxy if `hierLevel>0`), `pos`, `dir`, `component`, `surface` (SurfaceInfo), `entry/exit`.
- `CollisionFlags` — `1_core/proto/endebug.c:140-148`: `FIRSTCONTACT, NEARESTCONTACT, ONLYSTATIC, ONLYDYNAMIC, ONLYWATER, ALLOBJECTS`.
- `CollisionOverlapCallback.OnContact(IEntity other, Contact contact)` (`dayzphysics.c:115-121`) for overlaps.
- `PhxRaycast*` **does not exist** (grep without matches).

Who uses what (verified):
| Use | API | Geometry/layers | Citation |
|---|---|---|---|
| Action cursor (1st pass) | `RaycastRVProxy` | `ObjIntersectView` (default) + `CollisionFlags.ALLOBJECTS` | `4_world/classes/useractionscomponent/actiontargets.c:214-219` |
| Action cursor (ground fallback) | `RayCastBullet` | `ROADWAY\|TERRAIN\|WATERLAYER` | `actiontargets.c:329-331` |
| Melee aiming/hitzone | `RaycastRV` | `ObjIntersectIFire` | `4_world/entities/dayzplayerimplementmeleecombat.c:623` |
| Melee obstruction | `RayCastBullet` | `BUILDING\|DOOR\|VEHICLE\|ROADWAY\|TERRAIN\|ITEM_SMALL\|ITEM_LARGE\|FENCE` | `dayzplayerimplementmeleecombat.c:671-686` |
| Weapon lift | member mask `hit_mask` with `...\|AI` | — | `4_world/entities/firearms/weapon_base.c:75` |
| Under roof? (Environment) | `RayCastBullet` vertical 25 m | `ITEM_LARGE\|BUILDING\|VEHICLE` | `4_world/classes/environment/environment.c:406-408` |
| Admin spawn on crosshair | `RayCastBullet` | `BUILDING\|DOOR\|VEHICLE\|ROADWAY\|TERRAIN\|CHARACTER\|AI\|RAGDOLL\|RAGDOLL_NO_CHARACTER` | `4_world/plugins/pluginbase/plugindeveloper.c:474-475` |
| Action cursor (1st pass, 1.30 Exp) | `RaycastRVProxy` | `ObjIntersectView` (default) + `CollisionFlags.ALLOBJECTS` | `exp/scripts/scripts/4_World/Classes/UserActionsComponent/ActionTargets.c:255` |
| Action cursor (ground fallback, 1.30 Exp) | `RayCastBullet` | `ROADWAY\|TERRAIN\|WATERLAYER` | `exp/scripts/scripts/4_World/Classes/UserActionsComponent/ActionTargets.c:383-384` |
| Action cursor (liquid surface without object, 1.30 Exp) | scoring | utility 0.01 if `SurfaceInfo.GetLiquidType() != LIQUID_NONE` | `exp/scripts/scripts/4_World/Classes/UserActionsComponent/ActionTargets.c:532-534` |

### 2.8 Contacts and events

`sealed class Contact` — `1_core/physics/contact.c:9-50`:
```c
Physics Physics1; Physics Physics2;
SurfaceProperties Material1; SurfaceProperties Material2;
float  Impulse;            // "Impulse applied to resolve the collision" (:21)
int    ShapeIndex1, ShapeIndex2;
vector Normal;             // collision axis (:27)
vector Position;           // punto de contacto WS (:29)
float  PenetrationDepth;
float  RelativeNormalVelocityBefore / After;
vector RelativeVelocityBefore / After;
vector VelocityBefore1/2, VelocityAfter1/2;
proto native vector GetNormalImpulse();                       // :47
proto native float  GetRelativeVelocityBefore(vector vel);    // :48
proto native float  GetRelativeVelocityAfter(vector vel);     // :49
```
Registro: `SetEventMask(EntityEvent.CONTACT)` → override `event protected void EOnContact(IEntity other, Contact extra)` (`1_core/proto/enentity.c:213`, enum `EntityEvent.CONTACT` en `enentity.c:97`). Constructor no instanciable (privado, `contact.c:11`).

Vanilla patterns:
- Player: `4_world/entities/dayzplayerimplement.c:172` registers; (up to 1.29: `:3814-3830`; since 1.30 Exp: `exp/scripts/scripts/4_World/Entities/DayZPlayerImplement.c:3958-3973`) → if `other` is `Transport` and `g_Game.IsServer()` → `RegisterTransportHit(transport)`.
- Infected/animal: `zombiebase.c:50,1018-1031`; `dayzanimal.c:692,942`.
- `RegisterTransportHit` (up to 1.29: `3_game/entities/entityai.c:4086-4116`; since 1.30 Exp: `exp/scripts/scripts/3_Game/Entities/EntityAI.c:4111` with a new Motorbike branch at `:4143-4160` before Boat): damage `DT_CUSTOM ... "TransportHit"` with magnitude `GetVelocity(transport).Length()` and, if it dies, `dBodyApplyImpulse(this, 40*velocity)` (Motorbike corpse impulse is `5.0 * velocity`, not 40). ⚠️RELEVANT (same damage+impulse pattern used by stone S2).
- ItemBase: `4_world/entities/itembase.c:1194-1220` — uses `extra.RelativeVelocityBefore.Length()` (via `ProcessImpactSoundEx`, `3_game/entities/inventoryitem.c:198-225`) for impact sound; client plays `#ifndef SERVER`, server sets SyncVar. Does **not** use `Impulse` for force.
- Vehicles: high-level callback `Transport.OnContact(string zoneName, vector localPos, IEntity other, Contact data)` (`3_game/vehicles/transport.c:252`, override in `carscript.c:1454-1480` — damage by own **momentum delta**, not by `data.Impulse`; comment `:1453` warns "Can be called very frequently in one frame").
- ItemBase combined trigger+contact style: `easteregg.c:40` (`SetEventMask(CONTACT|TOUCH)`), `fireplace.c:17,55-76` (processes contact in `EOnPostSimulate` with flag, and checks `dBodyIsActive(this)`).

### 2.9 Native path for dynamic items (drop/throw) ⚠️RELEVANT (plan S3)

```c
// 3_game/entities/inventoryitem.c
proto native void EnableCollisionsWithCharacter(bool state);   // :21
proto native bool HasCollisionsWithCharacter();                // :22
proto native void ThrowPhysically(DayZPlayer player, vector force, bool collideWithCharacters = true); // :26
proto native void ForceFarBubble(bool state);                  // :31 (network bubble far)
// 3_game/entities/object.c
proto native void CreateDynamicPhysics(int interactionLayers); // up to 1.29: :462; since 1.30 Exp: exp/scripts/scripts/3_Game/Entities/Object.c:456
proto native void EnableDynamicCCD(bool state);                // up to 1.29: :463; since 1.30 Exp: :457
proto native void SetDynamicPhysicsLifeTime(float lifeTime);   // up to 1.29: :464; since 1.30 Exp: :458
```
Lifecycle observed in vanilla:
1. **Throw from hands**: `HandActionThrow.Action` (`3_game/systems/inventory/hand_actions.c:62-88`) — moves item to GROUND via inventory and then:
```c
if ( player.GetInstanceType() != DayZPlayerInstanceType.INSTANCETYPE_REMOTE )
    item.ThrowPhysically(player, throwEvent.GetForce());
```
→ executes on **server and on owner client** (not on remotes): dynamic simulation exists on both; remotes receive result via network [internal replication mechanism not visible in scripts — NOT VERIFIED].
2. **Emptying inventory/containers**: `MiscGameplayFunctions.ThrowEntityFromInventory` (`4_world/static/miscgameplayfunctions.c:1164-1220`) calls `entityIB.ThrowPhysically(null, force, false)` (without collision against characters) and, for non-ItemBase entities, `dBodyApplyImpulse(entity, force)` (`:1218`).
3. **Admin spawn with physics**: `plugindeveloper.c:381,504` — `item.ThrowPhysically(null, "0 0 0")` server-side to activate falling physics.
4. **Shutdown**: `ItemBase.StopItemDynamicPhysics()` → `SetDynamicPhysicsLifeTime(0.01)` (`4_world/entities/itembase.c:4530-4534`) — drop dynamic physics has a *lifetime* managed by engine; setting it to 0.01 kills it instantly. Flag `m_ItemBeingDroppedPhys` (`itembase.c:71`).
5. `CreateDynamicPhysics(layers)` **is never called from vanilla script** (grep: only declaration) — engine invokes it inside `ThrowPhysically` [INFERENCE]; exposed for mods.
6. Re-configuration hook: `override void OnCreatePhysics()` → `RefreshPhysics()` (`itembase.c:1222-1227`); real implementations in `tentbase.c:160-172`, `fireplace.c`, `hescobox.c`, `kitbase.c`, `batterycharger.c`.

Layers `DYNAMICITEM` vs `DYNAMICITEM_NOCHAR` (`dayzphysics.c:9-10`): the pair corresponds to `collideWithCharacters` parameter of `ThrowPhysically` and to `EnableCollisionsWithCharacter` [INFERENCE by naming and signature; internal assignment NOT VERIFIED].

### 2.10 Player CCT (character controller)

Player controller is NOT a script-visible rigid body; its API lives in `Human` (`3_game/human.c`):
```c
proto native bool    PhysicsIsFalling(bool pValidate);            // :1397
proto native IEntity PhysicsGetFloorEntity();                     // :1400
proto native IEntity PhysicsGetLinkedEntity();                    // :1403
proto native bool    PhysicsWasSlidingOffLinkedEntity();          // :1407 (config 'animPhysDetachSpeed')
proto native void    PhysicsGetVelocity(out vector pVelocity);    // :1410
proto native void    PhysicsEnableGravity(bool pEnable);          // :1412
proto native bool    PhysicsIsSolid();                            // :1414
proto native void    PhysicsSetSolid(bool pSolid);                // :1415
proto native void    PhysicsSetRagdoll(bool pEnable);             // :1418 — "Sets and synchronize interaction layers
                     // 'RAGDOLL' and 'RAGDOLL_NO_CHARACTER' to prevent body stacking and players going through dead creatures" (:1417)
proto native bool    CheckFreeSpace(vector localDir, float distance, bool useHeading, vector posOffset = vector.Zero, float xzScale = 1.0); // :1354
proto       float    CollisionMoveTest(vector dir, vector offset, float xzScale, IEntity ignoreEntity, out IEntity hitEntity, out vector hitPosition, out vector hitNormal); // :1357
proto native void    LinkToLocalSpaceOf(notnull IEntity child, vector pLocalSpaceMatrix[4]); // :1361
```
(since 1.30 Exp: `PhysicsIsFalling` :1428 also true if ragdoll moves > 1 m/s; `PhysicsSetSimpleDeath` :1448-1449 is the "old" death-state system that previously was `PhysicsSetRagdoll`; `PhysicsSetRagdoll` :1451 no longer carries the 1.29 RAGDOLL-layer comment; `PhysicsIsRagdoll()` :1452; `HumanCommandUnconscious.IsRagdoll()` :647. Death branch calls `PhysicsSetSimpleDeath(true)` at `exp/scripts/scripts/4_World/Entities/DayZPlayerImplement.c:745`. CheckFreeSpace :1381, CollisionMoveTest :1387, LinkToLocalSpaceOf :1391.)
- CCT belongs to `CHARACTER` layer [strong INFERENCE: `transport.c:557` queries `dGetInteractionLayer(this, PhxInteractionLayers.CHARACTER, layer)` to determine what blocks player].
- Vanilla manipulates it: `dayzplayerimplement.c:32` (`PhysicsEnableGravity(true)` upon leaving unconscious-fall), `:658` (`PhysicsSetSolid(true)`).
- ⚠️RELEVANT: for player NOT to pass through stone, stone body must (a) exist on the machine simulating CCT (player local client) and (b) be in a layer with active interaction against `CHARACTER` (e.g. `DYNAMICITEM`).

### 2.11 Surfaces

- `SurfaceProperties` opaque (`1_core/physics/surfaceproperties.c:9-15`); useful subclass `SurfaceInfo` (`3_game/surfaceinfo.c:8-51`): `GetByName/GetByFile` (O(n), `:16,:22`), `GetName/GetEntryName/GetSurfaceType`, `GetRoughness/GetDustness/GetBulletPenetrability/GetThickness/GetDeflection/GetTransparency/GetAudability`, `IsLiquid/IsStairs/IsPassthrough/IsSolid`, `GetSoundEnv/GetImpact`, `GetLiquidType`, `GetStepParticleId/GetWheelParticleId`. Comment `:4`: defined in `CfgSurfaces` **or in object's `.bisurf`**; lifetime managed by engine ("don't store handles").
- Detection API in `CGame` (`3_game/global/game.c`): `GetSurface(SurfaceDetectionParameters, SurfaceDetectionResult)` (`:1160`), `SurfaceY` (`:1162`), `SurfaceRoadY/3D` (`:1163-1164`), `SurfaceGetType/3D` (`:1166-1168`), `SurfaceUnderObject/Ex/ByBone` (`:1169-1171`), `SurfaceGetNormal` (`:1173`), sea/waves (`:1174-1187`). Config helpers: `IsSurfaceDigable/IsSurfaceFertile` read `CfgSurfaces <surface> isDigable/isFertile` (`:1229-1243`).
- Item impact: `DayZPhysics.GetHitSurfaceAndLiquid` used in `inventoryitem.c:168-176`.
- **Surface PhysX friction/restitution are NOT exposed to script** — `SurfaceInfo` lacks friction getters; physics material is assigned by string when creating geometry (`PhysicsGeomDef.MaterialName`, e.g. `"material/default"`).

### 2.12 Engine → client synchronization

- `Transport` has `proto native void Synchronize()` — "Synchronizes car's state in case the simulation is not running" (`3_game/vehicles/transport.c:108-109`). With `FEATURE_NETWORK_RECONCILIATION`, `Transport extends Pawn` (`transport.c:53`) with states `TransportOwnerState/TransportMove` (transform + linear/angular velocities, `transport.c:11-50`) — move replication with replay (`3_game/entities/pawn.c:20-24`: "full state synchronization... triggering a replay on the owner").
- `EntityAI`: SyncVars via `RegisterNetSyncVariable{Bool,Int,Float,Object}` + `SetSynchDirty` (`3_game/entities/entityai.c:2843-3068`); position does NOT enter there.
- Thrown ItemBase: physics runs on server + owner client (2.9.1); for final position on remotes inventory flow (`LocationSyncMoveEntity`, `hand_actions.c:74`) and native item replication handle it [internal detail NOT VERIFIED in scripts].
- For ad-hoc `dBodyCreateDynamicEx` bodies on ItemBase there is NO transform sync script code: if client sees it move (project empirical 2026-05-21), it is native entity position replication, not simulation → on client there is no body → player passes through it. Consistent with current bug.

---

## 3. Patrones vanilla (snippets reales)

**Create dynamic body with custom geom** (only complete example, `2_gamelib/entities/scriptmodel.c:35-51`, under `#ifdef GAME_TEMPLATE`!):
```c
PhysicsGeomDef geoms[] = {PhysicsGeomDef("", dGeomCreateBox(size), "material/default", 0xffffffff)};
dBodyCreateDynamicEx(this, center, 1, geoms);
if (dBodyIsSet(this)) {
    dBodySetMass(this, 1.0);
    dBodyActive(this, ActiveState.ACTIVE);
    dBodyDynamic(this, true);
}
// destructor: if (dBodyIsSet(this)) dBodyDestroy(this);   // :57-58
```

**Native throw (server + owner client)** — `hand_actions.c:76-84`:
```c
DayZPlayer player = DayZPlayer.Cast(e.m_Player);
if ( player.GetInstanceType() != DayZPlayerInstanceType.INSTANCETYPE_REMOTE )
    item.ThrowPhysically(player, throwEvent.GetForce());
```

**Damage + impulse upon dying from vehicle contact** — `entityai.c:4098-4116`:
```c
if (car.GetSpeedometerAbsolute() > 2)
    ProcessDirectDamage(DT_CUSTOM, transport, "", "TransportHit", "0 0 0", damage);
if (IsDamageDestroyed() && car.GetSpeedometerAbsolute() > 3) {
    impulse = 40 * m_TransportHitVelocity;
    impulse[1] = 40 * 1.5;
    dBodyApplyImpulse(this, impulse);
}
```

**Action cursor** — `actiontargets.c:214-219` (`RaycastRVProxy` + `CollisionFlags.ALLOBJECTS`, default type `ObjIntersectView`); proxies detected with `res.hierLevel > 0` (`:249`). (since 1.30 Exp: `exp/scripts/scripts/4_World/Classes/UserActionsComponent/ActionTargets.c:255`; fallback `:383-384`; liquid-without-object utility 0.01 at `:532-534`.)

**Layer matrix query** — `transport.c:556-557` (see 2.6).

**Impact velocity for effects** — `inventoryitem.c:200`: `float impactVelocity = extra.RelativeVelocityBefore.Length();` with `< 0.3` threshold ignored and 0.33 s throttle.

---

## 4. Gotchas

1. `dSetInteractionLayer` modifies the **global matrix** of the world (layer↔layer), not a body; the 1st parameter only serves to resolve the world (`physicsworld.c:14-21`). Disabling `CHARACTER×DYNAMICITEM` affects ALL dynamic items on the server.
2. `Contact` is `sealed` with private constructor/destructor (`contact.c:11-12`) — cannot be instantiated or inherited; only received.
3. `EOnContact` only fires with `SetEventMask(EntityEvent.CONTACT)` active and active body; fireplace also checks `dBodyIsActive(this)` (`fireplace.c:62`). On passive receiver (player vs vehicle) it fires player event even if active body is the car.
4. `Transport.OnContact` (per damage-zone) "Can be called very frequently in one frame" (`carscript.c:1453`) — buffer it (vanilla uses `m_ContactCache`).
5. `ObjIntersect*` constants are NOT defined in scripts (engine builtins); reliable values only from comment `dayzphysics.c:66-71`.
6. `dBodyCreateDynamic/dBodyCreateStatic` (without `Ex`) only exist in `GAME_TEMPLATE` code — in DayZ they do not compile; use `Physics.CreateDynamic` (wrapper, `physics.c:189`) or `dBodyCreateDynamicEx`.
7. Cursor (`RaycastRVProxy` with `ObjIntersectView`) sees **View Geometry**: without View Geometry LOD in .p3d there is no action target even if rigid body exists (body lives in Bullet world, which cursor does not query except for ground fallback `RayCastBullet` with `ROADWAY|TERRAIN|WATERLAYER`, `actiontargets.c:329`). ⚠️RELEVANT: explains "Push does not appear" bug. (since 1.30 Exp: `RaycastRVProxy` at `exp/scripts/scripts/4_World/Classes/UserActionsComponent/ActionTargets.c:255`; fallback `:383-384`. Truth still holds.)
8. `dBodySetAngularVelocity` is rotation along x/y/z axes (rad/s), "not yaw/pitch/roll" (`enphysics.c:163`).
9. `SetDynamicPhysicsLifeTime` implies that drop physics is **temporary by design**: engine removes it after lifetime passes; an object that must roll indefinitely needs to prevent/renew that timeout (or not rely on drop path). [Exact semantics of default value NOT VERIFIED.]
10. `GetVelocity/SetVelocity` are global functions (work for Man and bodies); do not look for `dBodyGetVelocity` — it does not exist.
11. `physics.c:18-21` defines `Physics.KMH2MS/MS2KMH/STANDARD_GRAVITY(9.81)/VGravity("0 -9.81 0")` — useful pre-made constants.
12. Default physics timestep is 1/40 s (`enphysics.c:18`); `PhysicsWorld.SetUpdateRate` accepts 20..1000 (`physicsworld.c:46`). Changing it is global.

---

## 5. What does NOT exist (absences verified by grep across all `scripts/`)

| Typical confabulation | Reality |
|---|---|
| `dBodySetFriction` / `SetFriction` / `SetRestitution` / `SetBounciness` / `SetElasticity` / `SetBounce` | 0 matches. Friction/restitution = geometry physics material (string `MaterialName`) / surface; no runtime setter per body. |
| Vector gravity per body (`dBodySetGravity`, `SetGravityDir`, `GravityFactor`) | 0 matches. Only `dBodyEnableGravity(ent, bool)` (on/off) and `dSetGravity(world, g)` global. |
| `dBodySetVelocity` / `dBodyGetVelocity` | Do not exist; use globals `SetVelocity/GetVelocity` (`enphysics.c:104,111`) and `dBodySet/GetAngularVelocity`. |
| `dBodyApplyAngularImpulse` | Does not exist; it is `dBodyApplyTorqueImpulse` (`enphysics.c:125`). |
| `AddForce` (Unity style) | 0 matches; it is `dBodyApplyForce*`. |
| `SetMaxLinearVelocity` / `SetMaxAngularVelocity` | 0 matches; no velocity clamp per body (do it by hand in `EOnSimulate`). |
| `PhxRaycast*` | 0 matches; physics world functions are `*Bullet` in `DayZPhysics`. |
| Script call to `CreateDynamicPhysics` in vanilla | 0 uses (only declaration `object.c:462`) — available for mods, no vanilla reference pattern. (since 1.30 Exp: declaration at `exp/scripts/scripts/3_Game/Entities/Object.c:456`.) |
| Mass setter via config at runtime | `dBodySetMass` exists, but there is no physical "SetWeight"; ItemBase `m_ConfigWeight` is for sound/inventory (`itembase.c:1199`). |

---

## 6. Recipes for mods

**A. Custom dynamic body (sphere) server-side** (what LF_RollingStone does today):
```c
PhysicsGeomDef geoms[] = {PhysicsGeomDef("", dGeomCreateSphere(0.5), "material/default",
    PhxInteractionLayers.DYNAMICITEM)};
dBodyCreateDynamicEx(this, GetCenterOfMassOffset(), 80.0, geoms);
dBodySetInteractionLayer(this, PhxInteractionLayers.DYNAMICITEM);  // collides as dynamic item
dBodyActive(this, ActiveState.ALWAYS_ACTIVE);                      // no se duerme
dBodySetDamping(this, 0.05, 0.2);
dBodyEnableCCD(this, 0.4, 0.45);                                   // ~radio; anti-tunneling
// empuje: dBodyApplyImpulseAt(this, dir * fuerza, contactPosWS);
// limpiar: if (dBodyIsSet(this)) dBodyDestroy(this);
```
Demonstrated limitation: body only exists where created; local client CCT does not see it → passable.

**B. Native path (recommended, plan S3)**: let the item use engine drop/throw physics.
```c
// On server and on owner client (replicate hand_actions.c:77 guard):
item.ThrowPhysically(null, impulso, true);   // true => colisiona con CHARACTER
item.EnableDynamicCCD(true);
item.SetDynamicPhysicsLifeTime(3600);        // renovar/extender para rodadura larga [comportamiento exacto a validar]
```
Requirements for .p3d: Geometry LOD (collision), **View Geometry** (cursor/actions), FireGeometry (bullets) — engine constructs physics geometries from model, no need for `dGeomCreate*`.

**C. Read impact force** (velocity damage, vanilla pattern):
```c
void LFRS_Stone() { SetEventMask(EntityEvent.CONTACT); }
override void EOnContact(IEntity other, Contact extra)
{
    float v = extra.RelativeVelocityBefore.Length();      // velocidad relativa de impacto (m/s)
    // or extra.Impulse (kg·m/s applied by solver) / extra.GetNormalImpulse()
    if (g_Game.IsServer() && v > 4 && other.IsInherited(DayZPlayer)) { /* ProcessDirectDamage + dBodyApplyImpulse al player NO (CCT) → daño */ }
}
```
Note: a living player (CCT) is not pushed with `dBodyApplyImpulse`; vanilla only does so on corpses/ragdoll (`entityai.c:4111-4115`).

**D. Disable the collision between two specific entities**: `dBlock b = dBodyCollisionBlock(entA, entB);` ... `dBodyRemoveBlock(world, b);` (`enphysics.c:116-117`) — more surgical than touching global matrix.

**E. Physics raycast with layer filter**:
```c
Object hit; vector pos, n; float frac;
DayZPhysics.RayCastBullet(from, to, PhxInteractionLayers.DYNAMICITEM|PhxInteractionLayers.TERRAIN, ignorar, hit, pos, n, frac);
```

---

## 7. Relevance for LF_RollingStone

1. **"Passes through stone" bug**: architectural, not layers. Server-only `dBodyCreateDynamicEx` body will never collide with local client CCT (CCT is simulated client-side). Correct fix = body on client too: either call creation on both sides, or (better) native path `ThrowPhysically/CreateDynamicPhysics` which vanilla already executes on server+owner (`hand_actions.c:77-81`).
2. **"Push does not appear" bug**: 100% confirmed — `actiontargets.c:214-219` uses `RaycastRVProxy` with `ObjIntersectView`; without View Geometry LOD there is no target. No physics layer fixes it. (since 1.30 Exp: same API at `exp/scripts/scripts/4_World/Classes/UserActionsComponent/ActionTargets.c:255`.)
3. **S2 damage/impulse**: `EOnContact → IsServer → ProcessDirectDamage("TransportHit")` pattern is exactly vanilla from `dayzplayerimplement.c:3814-3830` + `entityai.c:4086-4116` — but inverted (in vanilla event is processed by victim, not striker). For stone: player `EOnContact` will not recognize stone as `Transport`; better for **stone** to detect contact and damage player, or register custom damage.
4. **Maintain rolling**: `dBodyActive(ALWAYS_ACTIVE)` + low `dBodySetSleepingTreshold` + low `dBodySetDamping`; CCD with `dBodyEnableCCD(maxMotion≈diameter*0.8, inner_radius)`.
5. **Push**: `dBodyApplyImpulseAt(stone, dir*F, contactPos)` generates natural roll (implicit torque) better than `dBodyApplyImpulse` at origin.
6. **Runtime layer verification**: log `dGetInteractionLayer(this, PhxInteractionLayers.CHARACTER, dBodyGetInteractionLayer(this))` after creating body (`transport.c:556-557` pattern).
7. **If migrating to native path**: watch `SetDynamicPhysicsLifeTime` (drop physics expires; `StopItemDynamicPhysics` kills it with 0.01 — `itembase.c:4530-4534`) and `EnableCollisionsWithCharacter(true)`.

---

## 8. Fuentes

Verificadas en repo local (v1.24):
- `1_core/proto/enphysics.c` (API dBody/dGeom/dJoint completa)
- `1_core/physics/{contact.c, physics.c, physicsworld.c, physicsgeomdef.c, activestate.c, simulationstate.c, surfaceproperties.c}`
- `1_core/proto/enentity.c` (EntityEvent, EOn*), `1_core/proto/endebug.c` (CollisionFlags)
- `3_game/global/dayzphysics.c` (PhxInteractionLayers, DayZPhysics), `3_game/global/game.c` (surfaces)
- `3_game/entities/{object.c, inventoryitem.c, entityai.c, pawn.c, dayzanimal.c}`, `3_game/human.c`
- `3_game/vehicles/transport.c`, `3_game/systems/inventory/hand_actions.c`, `3_game/surfaceinfo.c`
- `4_world/entities/{itembase.c, dayzplayerimplement.c, dayzplayerimplementmeleecombat.c}`, `4_world/entities/creatures/infected/zombiebase.c`, `4_world/entities/vehicles/carscript.c`, `4_world/entities/firearms/weapon_base.c`
- `4_world/classes/useractionscomponent/actiontargets.c`, `4_world/classes/environment/environment.c`, `4_world/static/miscgameplayfunctions.c`, `4_world/plugins/pluginbase/plugindeveloper.c`
- `2_gamelib/entities/scriptmodel.c` (GAME_TEMPLATE), `4_world/entities/itembase/{tentbase.c, fireplacebase/fireplace.c, gear/consumables/easteregg.c}`

No web used (0 fetches); all content comes from local vanilla source.

## 9. DayZ 1.30 Exp (build 1.30.164014)

Line-drift and new player-physics APIs above. Full `.ragdoll` / `RagdollDef`, `PhysicsSetSimpleDeath`, unconscious `PhysicsIsFalling` wake guard, and fall-damage `CurveExp` live in `dayz-1-30-ragdoll-and-fall.md`. TransportHit Motorbike branch + fall-damage thresholds: `dano-transporthit.md`.

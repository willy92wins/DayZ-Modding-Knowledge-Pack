# Deep-dive: Física engine-level (DayZ / Enfusion / Enforce Script)

> Investigación 2026-06-06 · Fuente de verdad: scripts vanilla descompilados v1.24
> (`<dayz-projects>\scripts\`). Todas las rutas citadas
> son relativas a esa carpeta. Todo lo citado con `ruta:línea` fue verificado con Read/Grep.
> Lo no verificable en scripts se marca [NO VERIFICADO] o [INFERENCIA].

---

## 1. Resumen ejecutivo

- La API de rigid bodies de DayZ vive en **funciones globales `dBody*`/`dGeom*`/`dJoint*`** declaradas en `1_core/proto/enphysics.c` (Bullet-style; nombres tipo ODE). Operan sobre `IEntity` directamente: el body se "adjunta" a la entidad.
- Existe además una **clase wrapper `Physics`** (`1_core/physics/physics.c`) con la misma funcionalidad como métodos (`ApplyImpulse`, `CreateDynamicEx`...), más extras (`ClearForces`, `GetTotalForce`, `SetResponseIndex`, `AddGeom`). El gameplay vanilla de DayZ usa casi exclusivamente las funciones globales `dBody*`; el wrapper es la API estilo Enfusion.
- Las **capas de interacción** (`PhxInteractionLayers`, `3_game/global/dayzphysics.c:1-43`) son bitmasks; la matriz capa↔capa es **global por mundo** (`dSetInteractionLayer`), y cada body/geom lleva su máscara (`dBodySetInteractionLayer`).
- **Raycasts**: dos familias. `RaycastRV/RaycastRVProxy` (geometrías RV: Fire/View/Geom por `ObjIntersect*`) y `RayCastBullet/SphereCastBullet/...OverlapBullet` (mundo físico Bullet, filtrado por `PhxInteractionLayers`). El cursor de acciones usa **`RaycastRVProxy` con `ObjIntersectView` por defecto** — confirma la causa del bug "Empujar no aparece" sin View Geometry.
- **Contactos**: clase `sealed Contact` (`1_core/physics/contact.c`) con `Impulse`, `Normal`, `Position`, velocidades antes/después. Se recibe vía `EOnContact` tras `SetEventMask(EntityEvent.CONTACT)`.
- **Path nativo de items dinámicos**: `InventoryItem.ThrowPhysically(player, force, collideWithCharacters=true)` + `Object.CreateDynamicPhysics/EnableDynamicCCD/SetDynamicPhysicsLifeTime`. ⚠️RELEVANTE: vanilla llama `ThrowPhysically` en **server Y cliente dueño** (no en REMOTE) — el body existe en ambos lados.
- **No existen** setters por-body de fricción/restitución, ni gravedad vectorial por body, ni `dBodySetVelocity` (se usa `SetVelocity` global). Fricción/restitución vienen del **material físico** asignado a la geometría (string en `PhysicsGeomDef.MaterialName` / superficie .bisurf).

---

## 2. API verificada (firmas exactas)

### 2.1 Mundo físico (global)

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

### 2.2 Creación / destrucción de bodies

```c
proto bool dBodyCreateStaticEx (notnull IEntity ent, PhysicsGeomDef geoms[]);                       // enphysics.c:38
proto bool dBodyCreateGhostEx  (notnull IEntity ent, PhysicsGeomDef geoms[]);                       // enphysics.c:39
proto bool dBodyCreateDynamicEx(notnull IEntity ent, vector centerOfMass, float mass, PhysicsGeomDef geoms[]); // enphysics.c:51
proto native void dBodyDestroy(notnull IEntity ent);   // enphysics.c:54
proto native bool dBodyIsSet(notnull IEntity ent);     // enphysics.c:57
```
- `PhysicsGeomDef(string name, dGeom geom, string materialName, int layerMask)` con `Frame[4]` (transform local) y `ParentNode` (hueso) como campos públicos — `1_core/physics/physicsgeomdef.c:9-26`.
- Ejemplo doc oficial: `PhysicsGeomDef("", dGeomCreateBox(size), "material/default", 0xffffffff)` (`enphysics.c:34`).
- Wrapper estático: `Physics.CreateStatic(ent, layerMask)`, `Physics.CreateDynamic(ent, mass, layerMask)` (desde geometría del VObject/p3d), `Physics.CreateDynamicEx/CreateStaticEx/CreateGhostEx` (`1_core/physics/physics.c:170-210`). OJO: las globales `dBodyCreateStatic/dBodyCreateDynamic` (sin Ex, con layerMask) solo aparecen usadas en `2_gamelib/entities/scriptmodel.c:31,35` bajo `#ifdef GAME_TEMPLATE` y **no están declaradas** en `enphysics.c` → en DayZ usar el wrapper `Physics.CreateDynamic` o las `*Ex`.

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
proto native void  dBodySetLinearFactor(notnull IEntity body, vector linearFactor);  // enphysics.c:87 (cero un eje => física 2D)
proto native float dBodyGetMass(notnull IEntity ent);                                // enphysics.c:122
proto native void  dBodySetMass(notnull IEntity body, float mass);                   // enphysics.c:123
proto native void  dBodySetInertiaTensorV(notnull IEntity body, vector v);           // enphysics.c:119
proto native void  dBodySetInertiaTensorM(notnull IEntity body, vector m[3]);        // enphysics.c:120
proto native vector dBodyGetCenterOfMass(notnull IEntity body);                      // enphysics.c:90
```
- `enum ActiveState { INACTIVE, ACTIVE, ALWAYS_ACTIVE }` — `1_core/physics/activestate.c:9-17`. ⚠️RELEVANTE: `ALWAYS_ACTIVE` evita que la piedra se duerma a mitad de cuesta.
- `enum SimulationState { NONE, COLLISION, SIMULATION }` — `1_core/physics/simulationstate.c:12-20` (vía `Physics.ChangeSimulationState`, `physics.c:51`).

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
proto native void  dBodySetTargetMatrix(notnull IEntity body, vector matrix[4], float timeslice); // enphysics.c:170 (mover kinemático)
proto native void  dBodyGetWorldTransform(notnull IEntity body, out vector matrix[4]);       // enphysics.c:172
proto native void  dBodyGetDirectWorldTransform(notnull IEntity body, out vector matrix[4]); // enphysics.c:173
proto native float dBodyGetKineticEnergy(notnull IEntity body);                       // enphysics.c:175
// Bloqueo de colisión par-a-par:
proto native dBlock dBodyCollisionBlock(notnull IEntity ent1, notnull IEntity ent2);  // enphysics.c:116
proto native void   dBodyRemoveBlock(notnull IEntity worldEntity, dBlock block);      // enphysics.c:117
```
Solo en el wrapper `Physics`: `ClearForces()`, `GetTotalForce()`, `GetTotalTorque()`, `SetResponseIndex(int)` (`physics.c:106-115`), `IsKinematic()` (`physics.c:63`), `GetGeomSurfaces(index, out array<SurfaceProperties>)` (`physics.c:160`).

### 2.5 Geometrías y joints

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

### 2.6 Capas de interacción

`enum PhxInteractionLayers` — `3_game/global/dayzphysics.c:1-43` (orden = bit index):
`NOCOLLISION, DEFAULT, BUILDING, CHARACTER, VEHICLE, DYNAMICITEM, DYNAMICITEM_NOCHAR, ROADWAY, VEHICLE_NOTERRAIN, CHARACTER_NO_GRAVITY, RAGDOLL_NO_CHARACTER, FIREGEOM (redef. de RAGDOLL_NO_CHARACTER), DOOR, RAGDOLL, WATERLAYER, TERRAIN, GHOST, WORLDBOUNDS, FENCE, AI, AI_NO_COLLISION, AI_COMPLEX, TINYCAPSULE, TRIGGER, TRIGGER_NOTERRAIN, ITEM_SMALL, ITEM_LARGE, CAMERA, TEMP`.

Semántica (verificada por uso):
- **Matriz global**: `dSetInteractionLayer(world, mask1, mask2, enable)` activa/desactiva interacción entre capas para TODO el mundo (1er parámetro = entidad para obtener el mundo; `physicsworld.c:14-21` lo documenta como "Modifies interaction matrix of interaction layers"). Confirma el gotcha del proyecto.
- **Por body**: `dBodySetInteractionLayer(ent, mask)` asigna a qué capas pertenece ese body; por geometría individual con `dBodySetGeomInteractionLayer`.
- **Query de matriz**: patrón vanilla en `3_game/vehicles/transport.c:556-557`:
```c
int layer = dBodyGetInteractionLayer(o);
bool interacts = dGetInteractionLayer(this, PhxInteractionLayers.CHARACTER, layer);
```
(decide si un objeto bloquea puertas de vehículo según si CHARACTER colisiona con su capa). ⚠️RELEVANTE: misma query sirve para verificar en runtime si `CHARACTER×DYNAMICITEM` está activo.
- No hay capas "CUSTOM" reservadas; `TEMP` es el último bit nombrado. Crear una capa nueva = usar un bit no usado y activar pares con `dSetInteractionLayer` [INFERENCIA razonable; sin ejemplo vanilla].

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
- `RaycastRVParams` (`:49-92`): `type` default **`ObjIntersectView`** (`:88`); valores documentados `ObjIntersectFire(0), View(1), Geom(2), IFire(3), None(4)` (`:66-71`) — constantes definidas en engine, no en scripts.
- `RaycastRVResult` (`:98-113`): `obj/parent` (proxy si `hierLevel>0`), `pos`, `dir`, `component`, `surface` (SurfaceInfo), `entry/exit`.
- `CollisionFlags` — `1_core/proto/endebug.c:140-148`: `FIRSTCONTACT, NEARESTCONTACT, ONLYSTATIC, ONLYDYNAMIC, ONLYWATER, ALLOBJECTS`.
- `CollisionOverlapCallback.OnContact(IEntity other, Contact contact)` (`dayzphysics.c:115-121`) para overlaps.
- `PhxRaycast*` **no existe** (grep sin matches).

Quién usa qué (verificado):
| Uso | API | Geometría/capas | Cita |
|---|---|---|---|
| Cursor de acciones (1ª pasada) | `RaycastRVProxy` | `ObjIntersectView` (default) + `CollisionFlags.ALLOBJECTS` | `4_world/classes/useractionscomponent/actiontargets.c:214-219` |
| Cursor de acciones (fallback suelo) | `RayCastBullet` | `ROADWAY\|TERRAIN\|WATERLAYER` | `actiontargets.c:329-331` |
| Apuntado melee/hitzone | `RaycastRV` | `ObjIntersectIFire` | `4_world/entities/dayzplayerimplementmeleecombat.c:623` |
| Obstrucción melee | `RayCastBullet` | `BUILDING\|DOOR\|VEHICLE\|ROADWAY\|TERRAIN\|ITEM_SMALL\|ITEM_LARGE\|FENCE` | `dayzplayerimplementmeleecombat.c:671-686` |
| Lift de arma | máscara miembro `hit_mask` con `...\|AI` | — | `4_world/entities/firearms/weapon_base.c:75` |
| ¿Bajo techo? (Environment) | `RayCastBullet` vertical 25 m | `ITEM_LARGE\|BUILDING\|VEHICLE` | `4_world/classes/environment/environment.c:406-408` |
| Spawn admin sobre crosshair | `RayCastBullet` | `BUILDING\|DOOR\|VEHICLE\|ROADWAY\|TERRAIN\|CHARACTER\|AI\|RAGDOLL\|RAGDOLL_NO_CHARACTER` | `4_world/plugins/pluginbase/plugindeveloper.c:474-475` |

### 2.8 Contactos y eventos

`sealed class Contact` — `1_core/physics/contact.c:9-50`:
```c
Physics Physics1; Physics Physics2;
SurfaceProperties Material1; SurfaceProperties Material2;
float  Impulse;            // "Impulse applied to resolve the collision" (:21)
int    ShapeIndex1, ShapeIndex2;
vector Normal;             // eje de colisión (:27)
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

Patrones vanilla:
- Player: `4_world/entities/dayzplayerimplement.c:172` registra; `:3814-3830` → si `other` es `Transport` y `g_Game.IsServer()` → `RegisterTransportHit(transport)`.
- Infectado/animal: `zombiebase.c:50,1018-1031`; `dayzanimal.c:692,942`.
- `RegisterTransportHit` (`3_game/entities/entityai.c:4086-4116`): daño `DT_CUSTOM ... "TransportHit"` con magnitud `GetVelocity(transport).Length()` y, si muere, `dBodyApplyImpulse(this, 40*velocidad)` ⚠️RELEVANTE (mismo patrón daño+empuje que usa S2 de la piedra).
- ItemBase: `4_world/entities/itembase.c:1194-1220` — usa `extra.RelativeVelocityBefore.Length()` (vía `ProcessImpactSoundEx`, `3_game/entities/inventoryitem.c:198-225`) para sonido de impacto; cliente reproduce `#ifndef SERVER`, server marca SyncVar. **No** usa `Impulse` para fuerza.
- Vehículos: callback de alto nivel `Transport.OnContact(string zoneName, vector localPos, IEntity other, Contact data)` (`3_game/vehicles/transport.c:252`, override en `carscript.c:1454-1480` — daño por **delta de momento** propio, no por `data.Impulse`; comentario `:1453` avisa "Can be called very frequently in one frame").
- ItemBase estilo trigger+contact combinados: `easteregg.c:40` (`SetEventMask(CONTACT|TOUCH)`), `fireplace.c:17,55-76` (procesa contacto en `EOnPostSimulate` con flag, y comprueba `dBodyIsActive(this)`).

### 2.9 Path nativo de items dinámicos (drop/throw) ⚠️RELEVANTE (plan S3)

```c
// 3_game/entities/inventoryitem.c
proto native void EnableCollisionsWithCharacter(bool state);   // :21
proto native bool HasCollisionsWithCharacter();                // :22
proto native void ThrowPhysically(DayZPlayer player, vector force, bool collideWithCharacters = true); // :26
proto native void ForceFarBubble(bool state);                  // :31 (network bubble far)
// 3_game/entities/object.c
proto native void CreateDynamicPhysics(int interactionLayers); // :462
proto native void EnableDynamicCCD(bool state);                // :463
proto native void SetDynamicPhysicsLifeTime(float lifeTime);   // :464
```
Ciclo de vida observado en vanilla:
1. **Throw desde manos**: `HandActionThrow.Action` (`3_game/systems/inventory/hand_actions.c:62-88`) — mueve el item a GROUND por inventario y luego:
```c
if ( player.GetInstanceType() != DayZPlayerInstanceType.INSTANCETYPE_REMOTE )
    item.ThrowPhysically(player, throwEvent.GetForce());
```
→ se ejecuta en **server y en el cliente dueño** (no en remotos): la simulación dinámica existe en ambos; los remotos reciben el resultado vía red [mecanismo de replicación interno no visible en scripts — NO VERIFICADO].
2. **Vaciado de inventario/contenedores**: `MiscGameplayFunctions.ThrowEntityFromInventory` (`4_world/static/miscgameplayfunctions.c:1164-1220`) llama `entityIB.ThrowPhysically(null, force, false)` (sin colisión con characters) y, para entidades no-ItemBase, `dBodyApplyImpulse(entity, force)` (`:1218`).
3. **Spawn admin con física**: `plugindeveloper.c:381,504` — `item.ThrowPhysically(null, "0 0 0")` server-side para activar la física de caída.
4. **Apagado**: `ItemBase.StopItemDynamicPhysics()` → `SetDynamicPhysicsLifeTime(0.01)` (`4_world/entities/itembase.c:4530-4534`) — la física dinámica de drop tiene un *lifetime* gestionado por engine; ponerlo a 0.01 la mata al instante. Flag `m_ItemBeingDroppedPhys` (`itembase.c:71`).
5. `CreateDynamicPhysics(layers)` **nunca se llama desde script vanilla** (grep: solo la declaración) — la invoca el engine dentro de `ThrowPhysically` [INFERENCIA]; está expuesta para mods.
6. Hook de re-configuración: `override void OnCreatePhysics()` → `RefreshPhysics()` (`itembase.c:1222-1227`); implementaciones reales en `tentbase.c:160-172`, `fireplace.c`, `hescobox.c`, `kitbase.c`, `batterycharger.c`.

Capas `DYNAMICITEM` vs `DYNAMICITEM_NOCHAR` (`dayzphysics.c:9-10`): el par se corresponde con el parámetro `collideWithCharacters` de `ThrowPhysically` y con `EnableCollisionsWithCharacter` [INFERENCIA por nomenclatura y firma; asignación interna NO VERIFICADA].

### 2.10 CCT del jugador (character controller)

El controller del player NO es un rigid body script-visible; su API vive en `Human` (`3_game/human.c`):
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
- El CCT pertenece a la capa `CHARACTER` [INFERENCIA fuerte: `transport.c:557` consulta `dGetInteractionLayer(this, PhxInteractionLayers.CHARACTER, layer)` para saber qué bloquea al player].
- Vanilla lo manipula: `dayzplayerimplement.c:32` (`PhysicsEnableGravity(true)` al salir de unconscious-fall), `:658` (`PhysicsSetSolid(true)`).
- ⚠️RELEVANTE: para que el player NO atraviese la piedra, el body de la piedra debe (a) existir en la máquina que simula el CCT (cliente local del player) y (b) estar en una capa con interacción activa contra `CHARACTER` (p.ej. `DYNAMICITEM`).

### 2.11 Surfaces

- `SurfaceProperties` opaco (`1_core/physics/surfaceproperties.c:9-15`); subclase útil `SurfaceInfo` (`3_game/surfaceinfo.c:8-51`): `GetByName/GetByFile` (O(n), `:16,:22`), `GetName/GetEntryName/GetSurfaceType`, `GetRoughness/GetDustness/GetBulletPenetrability/GetThickness/GetDeflection/GetTransparency/GetAudability`, `IsLiquid/IsStairs/IsPassthrough/IsSolid`, `GetSoundEnv/GetImpact`, `GetLiquidType`, `GetStepParticleId/GetWheelParticleId`. Comentario `:4`: definidas en `CfgSurfaces` **o en el `.bisurf` del objeto**; lifetime gestionado por engine ("don't store handles").
- API de detección en `CGame` (`3_game/global/game.c`): `GetSurface(SurfaceDetectionParameters, SurfaceDetectionResult)` (`:1160`), `SurfaceY` (`:1162`), `SurfaceRoadY/3D` (`:1163-1164`), `SurfaceGetType/3D` (`:1166-1168`), `SurfaceUnderObject/Ex/ByBone` (`:1169-1171`), `SurfaceGetNormal` (`:1173`), mar/olas (`:1174-1187`). Helpers config: `IsSurfaceDigable/IsSurfaceFertile` leen `CfgSurfaces <surface> isDigable/isFertile` (`:1229-1243`).
- Impacto de item: `DayZPhysics.GetHitSurfaceAndLiquid` usado en `inventoryitem.c:168-176`.
- **Fricción/restitución PhysX por superficie NO están expuestas a script** — `SurfaceInfo` no tiene getters de fricción; el material físico se asigna por string al crear la geometría (`PhysicsGeomDef.MaterialName`, p.ej. `"material/default"`).

### 2.12 Sincronización engine → cliente

- `Transport` tiene `proto native void Synchronize()` — "Synchronizes car's state in case the simulation is not running" (`3_game/vehicles/transport.c:108-109`). Con `FEATURE_NETWORK_RECONCILIATION`, `Transport extends Pawn` (`transport.c:53`) con estados `TransportOwnerState/TransportMove` (transform + velocidades lineal/angular, `transport.c:11-50`) — replicación de moves con replay (`3_game/entities/pawn.c:20-24`: "full state synchronization... triggering a replay on the owner").
- `EntityAI`: SyncVars por `RegisterNetSyncVariable{Bool,Int,Float,Object}` + `SetSynchDirty` (`3_game/entities/entityai.c:2843-3068`); posición NO entra ahí.
- ItemBase lanzado: la física corre en server + cliente dueño (2.9.1); para la posición final en remotos el flujo de inventario (`LocationSyncMoveEntity`, `hand_actions.c:74`) y la replicación nativa del item se encargan [detalle interno NO VERIFICADO en scripts].
- Para bodies `dBodyCreateDynamicEx` ad-hoc sobre ItemBase no hay NINGÚN código script de sync de transform: si el cliente la ve moverse (empírico 2026-05-21 del proyecto), es replicación nativa de posición de la entidad, no de la simulación → en cliente no hay body → el player la atraviesa. Consistente con el bug actual.

---

## 3. Patrones vanilla (snippets reales)

**Crear body dinámico con geom custom** (único ejemplo completo, `2_gamelib/entities/scriptmodel.c:35-51`, ¡bajo `#ifdef GAME_TEMPLATE`!):
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

**Throw nativo (server + cliente dueño)** — `hand_actions.c:76-84`:
```c
DayZPlayer player = DayZPlayer.Cast(e.m_Player);
if ( player.GetInstanceType() != DayZPlayerInstanceType.INSTANCETYPE_REMOTE )
    item.ThrowPhysically(player, throwEvent.GetForce());
```

**Daño + empuje al morir por contacto con vehículo** — `entityai.c:4098-4116`:
```c
if (car.GetSpeedometerAbsolute() > 2)
    ProcessDirectDamage(DT_CUSTOM, transport, "", "TransportHit", "0 0 0", damage);
if (IsDamageDestroyed() && car.GetSpeedometerAbsolute() > 3) {
    impulse = 40 * m_TransportHitVelocity;
    impulse[1] = 40 * 1.5;
    dBodyApplyImpulse(this, impulse);
}
```

**Cursor de acciones** — `actiontargets.c:214-219` (`RaycastRVProxy` + `CollisionFlags.ALLOBJECTS`, type default `ObjIntersectView`); proxies detectados con `res.hierLevel > 0` (`:249`).

**Query de matriz de capas** — `transport.c:556-557` (ver 2.6).

**Velocidad de impacto para efectos** — `inventoryitem.c:200`: `float impactVelocity = extra.RelativeVelocityBefore.Length();` con umbral `< 0.3` ignorado y throttle de 0.33 s.

---

## 4. Gotchas

1. `dSetInteractionLayer` modifica la **matriz global** del mundo (capa↔capa), no un body; el 1er parámetro solo sirve para resolver el mundo (`physicsworld.c:14-21`). Apagar `CHARACTER×DYNAMICITEM` afecta a TODOS los items dinámicos del servidor.
2. `Contact` es `sealed` con constructor/destructor privados (`contact.c:11-12`) — no instanciable ni heredable; solo se recibe.
3. `EOnContact` solo dispara con `SetEventMask(EntityEvent.CONTACT)` activo y body activo; fireplace además comprueba `dBodyIsActive(this)` (`fireplace.c:62`). En el receptor pasivo (player vs vehículo) dispara el evento del player aunque el body activo sea el coche.
4. `Transport.OnContact` (por damage-zone) "Can be called very frequently in one frame" (`carscript.c:1453`) — bufferizar (vanilla usa `m_ContactCache`).
5. Las constantes `ObjIntersect*` NO están definidas en scripts (builtins del engine); valores fiables solo por el comentario `dayzphysics.c:66-71`.
6. `dBodyCreateDynamic/dBodyCreateStatic` (sin `Ex`) solo existen en el código `GAME_TEMPLATE` — en DayZ no compilan; usar `Physics.CreateDynamic` (wrapper, `physics.c:189`) o `dBodyCreateDynamicEx`.
7. El cursor (`RaycastRVProxy` con `ObjIntersectView`) ve **View Geometry**: sin LOD View Geometry en el .p3d no hay target de acción aunque el rigid body exista (el body vive en el mundo Bullet, que el cursor no consulta salvo el fallback de suelo `RayCastBullet` con `ROADWAY|TERRAIN|WATERLAYER`, `actiontargets.c:329`). ⚠️RELEVANTE: explica el bug "Empujar no aparece".
8. `dBodySetAngularVelocity` es rotación por ejes x/y/z (rad/s), "not yaw/pitch/roll" (`enphysics.c:163`).
9. `SetDynamicPhysicsLifeTime` implica que la física de drop es **temporal por diseño**: el engine la retira pasado el lifetime; un objeto que debe rodar indefinidamente necesita evitar/renovar ese timeout (o no depender del path de drop). [Semántica exacta del valor por defecto NO VERIFICADA.]
10. `GetVelocity/SetVelocity` son funciones globales (sirven para Man y bodies); no busques `dBodyGetVelocity` — no existe.
11. `physics.c:18-21` define `Physics.KMH2MS/MS2KMH/STANDARD_GRAVITY(9.81)/VGravity("0 -9.81 0")` — constantes útiles ya hechas.
12. El timestep físico por defecto es 1/40 s (`enphysics.c:18`); `PhysicsWorld.SetUpdateRate` acepta 20..1000 (`physicsworld.c:46`). Cambiarlo es global.

---

## 5. Qué NO existe (ausencias verificadas por grep en todo `scripts/`)

| Confabulación típica | Realidad |
|---|---|
| `dBodySetFriction` / `SetFriction` / `SetRestitution` / `SetBounciness` / `SetElasticity` / `SetBounce` | 0 matches. Fricción/restitución = material físico de la geometría (string `MaterialName`) / superficie; no hay setter runtime por body. |
| Gravedad vectorial por body (`dBodySetGravity`, `SetGravityDir`, `GravityFactor`) | 0 matches. Solo `dBodyEnableGravity(ent, bool)` (on/off) y `dSetGravity(world, g)` global. |
| `dBodySetVelocity` / `dBodyGetVelocity` | No existen; usar globales `SetVelocity/GetVelocity` (`enphysics.c:104,111`) y `dBodySet/GetAngularVelocity`. |
| `dBodyApplyAngularImpulse` | No existe; es `dBodyApplyTorqueImpulse` (`enphysics.c:125`). |
| `AddForce` (estilo Unity) | 0 matches; es `dBodyApplyForce*`. |
| `SetMaxLinearVelocity` / `SetMaxAngularVelocity` | 0 matches; no hay clamp de velocidad por body (hazlo a mano en `EOnSimulate`). |
| `PhxRaycast*` | 0 matches; las funciones de mundo físico son `*Bullet` en `DayZPhysics`. |
| Llamada script a `CreateDynamicPhysics` en vanilla | 0 usos (solo declaración `object.c:462`) — disponible para mods, sin patrón vanilla de referencia. |
| Setter de masa vía config en runtime | `dBodySetMass` existe, pero no hay "SetWeight" físico; `m_ConfigWeight` de ItemBase es para sonido/inventario (`itembase.c:1199`). |

---

## 6. Recetas para mods

**A. Body dinámico custom (esfera) server-side** (lo que hace LF_RollingStone hoy):
```c
PhysicsGeomDef geoms[] = {PhysicsGeomDef("", dGeomCreateSphere(0.5), "material/default",
    PhxInteractionLayers.DYNAMICITEM)};
dBodyCreateDynamicEx(this, GetCenterOfMassOffset(), 80.0, geoms);
dBodySetInteractionLayer(this, PhxInteractionLayers.DYNAMICITEM);  // colisiona como item dinámico
dBodyActive(this, ActiveState.ALWAYS_ACTIVE);                      // no se duerme
dBodySetDamping(this, 0.05, 0.2);
dBodyEnableCCD(this, 0.4, 0.45);                                   // ~radio; anti-tunneling
// empuje: dBodyApplyImpulseAt(this, dir * fuerza, contactPosWS);
// limpiar: if (dBodyIsSet(this)) dBodyDestroy(this);
```
Limitación demostrada: el body solo existe donde se crea; el CCT del cliente local no lo ve → atravesable.

**B. Path nativo (recomendado, plan S3)**: dejar que el item use la física de drop/throw del engine.
```c
// En server y en cliente dueño (replicar guard de hand_actions.c:77):
item.ThrowPhysically(null, impulso, true);   // true => colisiona con CHARACTER
item.EnableDynamicCCD(true);
item.SetDynamicPhysicsLifeTime(3600);        // renovar/extender para rodadura larga [comportamiento exacto a validar]
```
Requisitos del .p3d: Geometry LOD (collision), **View Geometry** (cursor/acciones), FireGeometry (balas) — el engine construye las geometrías físicas desde el modelo, no hace falta `dGeomCreate*`.

**C. Leer fuerza de impacto** (daño por velocidad, patrón vanilla):
```c
void LFRS_Stone() { SetEventMask(EntityEvent.CONTACT); }
override void EOnContact(IEntity other, Contact extra)
{
    float v = extra.RelativeVelocityBefore.Length();      // velocidad relativa de impacto (m/s)
    // o extra.Impulse (kg·m/s aplicado por el solver) / extra.GetNormalImpulse()
    if (g_Game.IsServer() && v > 4 && other.IsInherited(DayZPlayer)) { /* ProcessDirectDamage + dBodyApplyImpulse al player NO (CCT) → daño */ }
}
```
Nota: a un player vivo (CCT) no se le empuja con `dBodyApplyImpulse`; vanilla solo lo hace sobre cadáveres/ragdoll (`entityai.c:4111-4115`).

**D. Desactivar colisión puntual entre dos entidades**: `dBlock b = dBodyCollisionBlock(entA, entB);` ... `dBodyRemoveBlock(world, b);` (`enphysics.c:116-117`) — más quirúrgico que tocar la matriz global.

**E. Raycast físico con filtro de capas**:
```c
Object hit; vector pos, n; float frac;
DayZPhysics.RayCastBullet(from, to, PhxInteractionLayers.DYNAMICITEM|PhxInteractionLayers.TERRAIN, ignorar, hit, pos, n, frac);
```

---

## 7. Relevancia para LF_RollingStone

1. **Bug "atraviesa la piedra"**: arquitectónico, no de capas. El body `dBodyCreateDynamicEx` server-only jamás colisionará con el CCT del cliente local (el CCT se simula client-side). Fix correcto = body en cliente también: o llamar la creación en ambos lados, o (mejor) path nativo `ThrowPhysically/CreateDynamicPhysics` que vanilla ya ejecuta en server+owner (`hand_actions.c:77-81`).
2. **Bug "Empujar no aparece"**: confirmado al 100% — `actiontargets.c:214-219` usa `RaycastRVProxy` con `ObjIntersectView`; sin View Geometry LOD no hay target. Ninguna capa física lo arregla.
3. **Daño/empuje S2**: el patrón `EOnContact → IsServer → ProcessDirectDamage("TransportHit")` es exactamente el vanilla de `dayzplayerimplement.c:3814-3830` + `entityai.c:4086-4116` — pero invertido (en vanilla el evento lo procesa el golpeado, no el golpeador). Para la piedra: el `EOnContact` del player no conocerá la piedra como `Transport`; conviene que la **piedra** detecte el contacto y dañe al player, o registrar daño custom.
4. **Mantener rodadura**: `dBodyActive(ALWAYS_ACTIVE)` + `dBodySetSleepingTreshold` bajos + `dBodySetDamping` bajo; CCD con `dBodyEnableCCD(maxMotion≈diámetro*0.8, radio_interno)`.
5. **Empujar**: `dBodyApplyImpulseAt(stone, dir*F, posContacto)` genera rodadura natural (torque implícito) mejor que `dBodyApplyImpulse` en el origen.
6. **Verificación runtime de capas**: loggear `dGetInteractionLayer(this, PhxInteractionLayers.CHARACTER, dBodyGetInteractionLayer(this))` tras crear el body (patrón `transport.c:556-557`).
7. **Si se migra a path nativo**: vigilar `SetDynamicPhysicsLifeTime` (la física de drop caduca; `StopItemDynamicPhysics` la mata con 0.01 — `itembase.c:4530-4534`) y `EnableCollisionsWithCharacter(true)`.

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

No se usó web (0 fetches); todo el contenido proviene del source vanilla local.

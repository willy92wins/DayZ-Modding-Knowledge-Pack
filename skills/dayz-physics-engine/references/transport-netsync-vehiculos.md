# 04 — Vehículos y Sincronización de Red (Transport / CarScript)
> DayZ Standalone v1.24 · Enforce Script descompilado · 2026-06-06  
> Fuente de verdad: `<dayz-projects>\scripts\`  
> Anti-confabulación: toda clase/firma verificada con Grep/Read + ruta:línea

---

## Resumen Ejecutivo

El sistema de vehículos de DayZ está construido en tres capas:

1. **Transport (nativo + script)** — clase base de todos los vehículos; hereda de `Pawn` (con `FEATURE_NETWORK_RECONCILIATION` activo) o de `EntityAI` en builds sin esa feature. Es el nivel donde ocurre la **magia de red**: Transport registra `TransportOwnerState` / `TransportMove` y usa `NetworkMoveStrategy.NONE` (tick de red propio, totalmente nativo — no el sistema de reconciliación de jugadores).
2. **Car / Boat / Helicopter (nativo)** — clases que heredan de Transport y exponen la API de física (throttle, steering, brake, fluidos, marchas). Toda la simulación es nativa (C++/PhysX); el script sólo llama a setters.
3. **CarScript / BoatScript / HelicopterScript (script puro)** — wrappers script que añaden daño por contacto, fluidos, luces, partículas, sonido, temperatura. Los caches de daño (`m_ContactCache`) sólo corren en server.

La **sincronización de posición/rotación** de un Transport no es "magia de ItemBase" ni usa `SetSynchDirty()`; es una propiedad intrínseca del tipo nativo `Pawn`/Transport que el engine sincroniza de forma continua (posición + velocidades linear/angular) a todos los clientes.

---

## API Verificada

### Jerarquía de herencia

```
EntityAI
└── Pawn  [FEATURE_NETWORK_RECONCILIATION]          pawn.c:191
    └── Transport                                    transport.c:52-56
        ├── Car                                      car.c:98
        │   └── CarScript                            carscript.c:170
        │       ├── OffroadHatchback                 offroadhatchback.c:1
        │       ├── Truck_02                         truck_02.c:1
        │       ├── Sedan_02, Van_01, Hatchback_02…
        │       └── Truck_01_Base → Chassis/Cargo/Covered
        ├── Boat                                     boat.c:31
        │   └── BoatScript                           boatscript.c:41
        │       └── Boat_01_ColorBase                boat_01.c:1
        └── Helicopter → HelicopterAuto              helicopter.c:9-14
            └── HelicopterScript                     helicopterscript.c:4
```

Sin `FEATURE_NETWORK_RECONCILIATION` el árbol es `EntityAI → Transport → …` (sin `Pawn`).  
Define activo en v1.24: `1_core/defines.c:64` (documentación-only; se activa desde C++).

---

### Transport — API clave

| Método | Firma | Nota |
|--------|-------|------|
| `Synchronize()` | `proto native void Synchronize()` | transport.c:109 — fuerza sync de estado cuando la simulación no está corriendo |
| `CrewSize()` | `proto native int CrewSize()` | transport.c:112 |
| `CrewPositionIndex(int componentIdx)` | `proto native int` | transport.c:116 — mapea component index del raycast a seat index |
| `CrewMemberIndex(Human player)` | `proto native int` | transport.c:120 — returns -1 si no está dentro |
| `CrewMember(int posIdx)` | `proto native Human` | transport.c:124 — null si vacío |
| `CrewDriver()` | `proto native Human` | transport.c:128 |
| `CrewGetIn(Human player, int posIdx)` | `proto native void` | transport.c:143 |
| `CrewGetOut(int posIdx)` | `proto native Human` | transport.c:146 |
| `CrewDeath(int posIdx)` | `proto native void` | transport.c:149 |
| `ApplyForce/Torque/Impulse…` | `proto void` | transport.c:197-212 — física determinista |
| `Random/RandomRange/Random01` | `proto native` | transport.c:220-233 — solo usar en EOnSimulate/EOnPostSimulate |
| `OnContact(zoneName, localPos, other, data)` | `void` | transport.c:252 — callback de colisión |
| `OnInput(float dt)` | `void` | transport.c:262 — llamado tras cada paso de input |
| `OnUpdate(float dt)` | `void` | transport.c:268 — cada frame (cliente) / tasa fija (server) |
| `IsTransport()` | `override bool → true` | transport.c:273 |

### Car — API de física por script

```cpp
// car.c — todos proto native, verificados
proto native float GetSpeedometer();          // km/h con signo
proto native float GetSteering();             // <-1,1>
proto native void  SetSteering(float value, bool unused0 = false);
proto native float GetThrottle();             // <0,1>
proto native void  SetThrottle(float value);
proto native float GetBrake();
proto native void  SetBrake(float value, float unused0 = 0, bool unused1 = false);
proto native float GetHandbrake();
proto native void  SetHandbrake(float value);
proto native void  SetBrakesActivateWithoutDriver(bool activate = true);
proto native float EngineGetRPM();
proto native bool  EngineIsOn();
proto native void  EngineStart();
proto native void  EngineStop();
proto native int   GetCurrentGear();          // ver enum CarGear (REVERSE, NEUTRAL, FIRST…SIXTEENTH)
proto native int   GetGear();                 // gear futuro (antes de aplicar)
proto native int   GetNeutralGear();
proto native int   GetGearCount();
proto native void  ShiftUp/ShiftDown/ShiftTo(int gear);
proto native CarGearboxType GearboxGetType(); // MANUAL | AUTOMATIC
proto native float GetFluidFraction(CarFluid fluid);  // <0,1>
proto native float GetFluidCapacity(CarFluid fluid);
proto native void  Fill(CarFluid fluid, float amount);
proto native void  Leak(CarFluid fluid, float amount);
proto native void  LeakAll(CarFluid fluid);
proto native int   WheelCount();              // hubs totales
proto native int   WheelCountPresent();       // ruedas realmente instaladas
proto native bool  WheelHasContact(int idx);
proto native vector WheelGetContactPosition(int idx);
```

**Fluidos (CarFluid enum):** `FUEL, OIL, BRAKE, COOLANT, USER1..USER4` — `car.c:17-29`.  
**Marchas (CarGear enum):** `REVERSE, NEUTRAL, FIRST..SIXTEENTH` — `car.c:43-63`.

### CarController — OBSOLETO

`GetController()` está marcado `[Obsolete("Use methods directly on Car")]` — `car.c:440`.  
`CarController` existe como clase legada compatible hacia atrás: `car.c:464-497`. No usar en mods nuevos.

### EOnPostSimulate — firma y dónde corre

```cpp
// carscript.c:325 — se registra en el constructor:
SetEventMask(EntityEvent.POSTSIMULATE);
SetEventMask(EntityEvent.POSTFRAME);

// carscript.c:948
override void EOnPostSimulate(IEntity other, float timeSlice)
{
    m_Time += timeSlice;
    if (g_Game.IsServer())
    {
        CheckContactCache();         // aplica daño acumulado de colisiones
        m_VelocityPrevTick = GetVelocity(this);
        m_MomentumPrevTick = GetMomentum();
    }
    // fluid checks, FX, brake lights… (server + cliente)
}
```

`EOnPostSimulate` corre en **server y cliente**. La sección de daño (`CheckContactCache`) y drenaje de fluidos está guardada por `g_Game.IsServer()`. Los efectos visuales están en `!g_Game.IsDedicatedServer()`. La función `IsServerOrOwner()` (carscript.c:3222) devuelve `IsServer()` para networking clásico o `IsOwner()` cuando `NetworkMoveStrategy == PHYSICS`.

`EOnSimulate` no está en carscript.c ni en transport.c — la simulación de física es enteramente **nativa**. El script no sobreescribe el loop de física.

### OnInput y OnUpdate

```cpp
// carscript.c:1303
override void OnInput(float dt)  // llamado por el engine para que el script aplique controles
{
    // (en DIAG: modo automático de test)
    SetThrottle(thrustWanted);
    SetSteering(steeringWanted);
    SetBrake(0.0);
    SetHandbrake(0.0);
}

// carscript.c:1385
override void OnUpdate(float dt)
{
    Human driver = CrewDriver();
    if (driver && !driver.IsControllingVehicle())
        if (driver.IsAlive())
            SetBrake(0.5);     // frena si el conductor está inconsciente
}
```

En condiciones normales (sin código de test), `CarScript.OnInput` sólo actúa si el conductor es una IA de prueba. El conductor humano controla el vehículo por su propia entrada (la física nativa lee el input del jugador directamente).

---

## Config CfgVehicles [WEB]

La estructura de config para vehículos usa `SimulationModule` y es completamente declarativa (no existe en los scripts descompilados; está en los archivos `config.cpp` de los addons P3D).  
Referencia: https://community.bistudio.com/wiki/DayZ:Vehicle_Configuration

Clases relevantes confirmadas por convención de naming en scripts (verificadas indirectamente):

- `class SimulationModule` — parámetros de física PhysX del vehículo completo
  - `axles[]` — lista de ejes (front/rear), cada uno con `wheels[]`
  - Dentro de cada rueda: `steerAngle`, `frictionCoef`, `dampingRate`
  - `engine {}` — `torque[][]`, `RPMMin`, `RPMIdle`, `RPMMax`, `RPMRedline`
  - `gearbox {}` — tipo (MANUAL/AUTOMATIC), relaciones de marcha
  - `clutch {}` — `maxRPMDrop`, `engagingSpeed`
  - `brakes {}` — `torqueMax`
  - `aerodynamics {}` — `dragCoef`, `frontalArea`
  - `drive` — `DRIVE_AWD`, `DRIVE_FWD`, `DRIVE_RWD`
- `inventorySlots[]` — slots de ruedas (para attachment de `CarWheel`)
- `attachments[]` — `CarRadiator`, `CarBattery`, `SparkPlug`, `GlowPlug`
- `dmgZones` — zonas de daño (Engine, FuelTank, ruedas, fenders, etc.)

Los enums `CarFluid` (FUEL/OIL/BRAKE/COOLANT) y `CarGear` sí existen en scripts y determinan el comportamiento de los fluidos y la caja de cambios por script.

---

## ⚠️ Netsync de Transport — Por qué Replica y ItemBase No

### La diferencia fundamental

```
Transport extends Pawn extends EntityAI    ← transport.c:52-53
ItemBase extends EntityAI                  ← NO es Pawn
```

**`Pawn`** es el tipo nativo que el engine trata como entidad "poseída" o controlada con movimiento continuo de red. La clase `Pawn` tiene:

- `GetOwnerStateType()` → devuelve `PawnOwnerState` — contiene posición/velocidades en una snapshot comprimida para corrección de desync — `pawn.c:238`
- `GetMoveType()` → devuelve `PawnMove` — el paquete de movimiento enviado cada tick — `pawn.c:246`
- `GetNetworkMoveStrategy()` → devuelve la estrategia activa (`NONE`, `LATEST`, `PHYSICS`) — `pawn.c:218`

**Transport** sobreescribe estos tipos:

```cpp
// transport.c:97-106
protected override event typename GetOwnerStateType() { return TransportOwnerState; }
protected override event typename GetMoveType()        { return TransportMove;       }
```

`TransportOwnerState` tiene `SetWorldTransform/GetWorldTransform`, `SetLinearVelocity/GetLinearVelocity`, `SetAngularVelocity/GetAngularVelocity` — `transport.c:13-30`. Estos campos son los que el engine nativo serializa y envía a clientes proxy en cada tick de red de vehículos.

El comentario en transport.c:52 dice explícitamente:
```
//! Uses NetworkMoveStrategy.NONE
class Transport extends Pawn
```
`NetworkMoveStrategy.NONE` significa que **no usa el sistema de reconciliación de cliente** (el mismo que usa el jugador). En cambio, el engine emplea su propio mecanismo de sincronización de física de vehículos (propietario del servidor, proxy en clientes), que replica posición + velocidades de forma continua a todos los proxies.

### Por qué ItemBase con dBody dinámico NO replica automáticamente

- `ItemBase` hereda de `EntityAI`, no de `Pawn`. El engine no sabe que debe tratar su transform como "estado de red continuo".
- El sistema `SetSynchDirty()` / `RegisterNetSyncVariable*` es un mecanismo de RPC de estado discreto (por cambio de valor), no un stream continuo de posición/velocidad.
- Un `dBody` dinámico sobre `ItemBase` tiene física en el servidor pero el cliente no recibe el transform en tiempo real — sólo lo actualiza cuando el item entra en su área de interés y en eventos de resync periódico.
- **Por eso el comportamiento "PASS provisional"** del proyecto (el cliente vio rodar la piedra en test S1) puede ser un artefacto de latencia baja + frecuencia de resync alta en red local / singleplayer, o de algún mecanismo de replicación de EntityAI que no está documentado en scripts.

### Métodos de red relevantes en Transport

```cpp
// transport.c:108-109
//! Synchronizes car's state in case the simulation is not running.
proto native void Synchronize();
```

Este `Synchronize()` es un "force push" de estado para cuando el vehículo no está en simulación activa (ej: acaba de ser activado, o el driver salió y el coche quedó quieto). Confirma que la sincronización normal es continua por el engine, y esto es un override manual.

```cpp
// transport.c:579-583
void SetEngineZoneReceivedHit(bool pState)
{
    m_EngineZoneReceivedHit = pState;
    SetSynchDirty();  // <- usa el sistema de netSyncVar para estado discreto
}
```

Transport usa AMBOS sistemas: el stream nativo de posición (vía Pawn) Y `SetSynchDirty()` para variables de estado (luces, daño de motor, etc.).

---

## Daño en CarScript

### OnContact + CheckContactCache

```cpp
// carscript.c:1453-1479
override void OnContact(string zoneName, vector localPos, IEntity other, Contact data)
{
    if (g_Game.IsServer())
    {
        if (m_ContactCache.Count() == 0)  // sólo primera zona por frame
        {
            float momentumDelta = GetMomentum() - m_MomentumPrevTick;
            float dot = vector.Dot(m_VelocityPrevTick.Normalized(), GetVelocity(this).Normalized());
            if (dot < 0) momentumDelta = m_MomentumPrevTick;
            ccd.Insert(new CarContactData(localPos, other, momentumDelta));
        }
    }
}
```

`OnContact` sólo corre en server (`g_Game.IsServer()`). Usa la **variación de momento** (delta de momentum = cambio en velocidad × masa) como proxy del impulso de colisión. El `Contact data` struct tiene `data.Impulse` (carscript.c:1462).

El procesamiento real ocurre en `CheckContactCache()` llamado desde `EOnPostSimulate`:

```cpp
// carscript.c:1482-1588
void CheckContactCache()
{
    float dmg = Math.AbsInt(data[0].impulse * m_dmgContactCoef);  // m_dmgContactCoef = 0.058 (carscript.c:198)
    float crewDmgBase = Math.AbsInt((data[0].impulse / dBodyGetMass(this)) * 1000 * m_dmgContactCoef);
    
    if (dmg < GameConstants.CARS_CONTACT_DMG_MIN) continue;    // umbral mínimo
    
    if (dmg < GameConstants.CARS_CONTACT_DMG_THRESHOLD)
        SynchCrashLightSound(true);    // choque leve
    else
    {
        DamageCrew(crewDmgBase);       // daño a tripulantes
        SynchCrashHeavySound(true);    // choque fuerte
    }
    
    ProcessDirectDamage(DamageType.CUSTOM, null, zoneName, "EnviroDmg", "0 0 0", dmg, pddfFlags);
}
```

Las **zonas de daño** (Engine, FuelTank, fenders, front, back) se mapean desde memoria points del modelo (`dmgZone_engine`, `dmgZone_front`, etc.) — carscript.c:393-426.

### Daño a tripulación

`DamageCrew(float dmg)` — carscript.c:1592. Si `dmg > CARS_CONTACT_DMG_KILLCREW` → `player.SetHealth(0.0)`. De lo contrario, calcula shock + HP via `Math.InverseLerp`.

### EEHitBy en Transport

`Transport.EEHitBy` activa `SetEngineZoneReceivedHit(dmgZone == "Engine")` — transport.c:84-89. Este flag se sincroniza vía `SetSynchDirty()`.

---

## Patrones Vanilla

### OnInput: física completamente nativa, script sólo lee/escribe

El patrón estándar para mods que quieran modificar comportamiento de conducción:

```cpp
override void OnInput(float dt)
{
    super.OnInput(dt);         // importante: dejar correr la lógica base
    // leer state: GetThrottle(), GetSteering()
    // modificar: SetThrottle(newVal), SetSteering(newVal)
}
```

### Fluidos por script

```cpp
// Llenar en debug spawn (patrón de offroadhatchback/boat_01):
float amount = GetFluidCapacity(CarFluid.FUEL);
Fill(CarFluid.FUEL, amount);

// Chequeo de nivel:
if (GetFluidFraction(CarFluid.FUEL) <= 0)
    EngineStop();

// Leak progresivo:
if (m_FuelTankHealth < GameConstants.DAMAGE_DAMAGED_VALUE)
    LeakFluid(CarFluid.FUEL);  // wrapper que llama Leak() con tasa
```

### Temperatura de motor (patrón UTSource)

Todos los coches vanilla (OffroadHatchback, Truck_02, Van_01, etc.) instancian `UniversalTemperatureSource` en `EEInit` sólo en server/SP, la actualizan en `EOnPostSimulate` y la activan/desactivan en `OnEngineStart/Stop`. El cliente no toca UTSource.

### Boarding completo

1. Jugador mira el vehículo → raycast llega a componente de modelo.
2. `ActionGetInTransport.ActionCondition` verifica: `trans.CrewPositionIndex(componentIndex)` >= 0 y seat vacío — actiongetintransport.c:50-80.
3. En `Start()`: `player.StartCommand_Vehicle(trans, crew_index, seat)` → crea `HumanCommandVehicle`.
4. En server (`OnStartServer`): actualiza luces.
5. Para salir: `ActionGetOutTransport` + `OnVehicleJumpOutServer` calcula daño por velocidad al desembarcar — carscript.c:1217-1291.

---

## Gotchas

1. **`OnContact` sólo corre en server** — carscript.c:1456. No hay callback de colisión en cliente para coches.
2. **`EOnPostSimulate` corre en ambos** — pero la mayoría de lógica está guardada por `g_Game.IsServer()`.
3. **`Random/RandomRange/Random01` sólo en EOnSimulate/EOnPostSimulate** — transport.c:216-237. Usarlos fuera de esos callbacks rompe el determinismo.
4. **`GetController()` está obsoleto** — usar métodos directos de `Car` (SetThrottle, SetSteering, etc.).
5. **`IsServerOrOwner()`** — carscript.c:3222. Con networking nuevo (`NetworkMoveStrategy.PHYSICS`), el "owner" (cliente que conduce) también ejecuta la simulación. Con networking clásico, sólo el server.
6. **`dBodyApplyImpulseAt` en ActionPushCar** — actionpushcar.c:52. Usa la API dBody global (no la del Transport); el resultado se propaga porque el physics body sí existe en server y Transport lo replica.
7. **`Synchronize()`** — llamar manualmente cuando el vehículo pasa de estado estático a activo, para forzar snapshot.
8. **`CarContactData` usa `momentumDelta` como "impulso"** — no es el `data.Impulse` del Contact struct en el cálculo principal; es `GetMomentum() - m_MomentumPrevTick`.
9. **`FEATURE_NETWORK_RECONCILIATION` está definido** — transport.c:52-56 muestra que si NO está definido, Transport hereda de EntityAI directamente. En v1.24 está activo.
10. **Coches sin conductor**: `SetBrakesActivateWithoutDriver(true)` — car.c:222. Si el conductor pierde control, `OnUpdate` aplica brake=0.5.

---

## Qué NO Existe / Confabulaciones Típicas

- **`CarScript` con `SimulationModule` por script**: FALSO. El `SimulationModule` es estrictamente config (CfgVehicles). No hay forma de crear parámetros de física de ruedas/axles por código Enforce Script.
- **Transport custom sin modelo con sim module**: FALSO. Necesitas un modelo P3D con geometría apropiada (PhysX collision, LODs, memory points) registrado en config.
- **`GetCrewIndex()`**: NO EXISTE con ese nombre. El método correcto es `CrewPositionIndex(int componentIdx)` (transport.c:116) o `CrewMemberIndex(Human player)` (transport.c:120).
- **`EFluidType` enum para vehículos**: NO EXISTE con ese nombre. Es `CarFluid` (car.c:17) y `BoatFluid` (boat.c:13-16). `EFluidType` puede existir para otros sistemas (water, fireplace) pero no para coches.
- **`EOnSimulate` en CarScript**: NO está overrideado en ninguna clase de script de coches. La simulación de física es 100% nativa.
- **`HelicopterScript` con física completa**: `HelicopterScript.EOnPostSimulate` está vacío — helicopterscript.c:11-13. Todo el vuelo es nativo en `HelicopterAuto`.
- **BoatScript hereda de BoatScript**: Confirmar — `BoatScript extends Boat` (boatscript.c:41), y `Boat extends Transport` (boat.c:31). La clase `BoatScript` SÍ existe (al contrario de lo que algunos suponen).

---

## Relevancia para LF_RollingStone

### ⚠️RELEVANTE: Por qué Transport replica y tu ItemBase no

La razón exacta es que `Transport extends Pawn` y el engine trata a todos los Pawn con un stream continuo de `TransportOwnerState` (worldTransform + linearVelocity + angularVelocity) hacia todos los proxies. `ItemBase` no hereda de `Pawn`, por lo que el engine no genera ese stream.

El "PASS provisional" de S1 (el cliente ve la piedra rodar) puede explicarse por:
- En **singleplayer**: no hay red, el mismo proceso ve todo.
- En **MP local / baja latencia**: EntityAI hace resync periódico de posición cuando cambia lo suficiente (mecanismo de `SetSynchDirty` automático del engine al mover entidades). Este resync es infrecuente (posiblemente cada N ms o cuando el server lo decide) y no envía velocidades, por lo que el cliente interpola mal o ve saltos.

### ⚠️RELEVANTE: Opciones reales para LF_RollingStone

1. **Opción A (Plan S3 — ThrowPhysically / DYNAMICITEM)**: Convertir la piedra en un `Transport` o aprovechar alguna entidad "throwable" que el engine sí sincronice. Riesgoso sin mod de sim module completo.
2. **Opción B (RPC manual de posición)**: En cada tick del server, leer `GetPosition()` y `GetVelocity()` del dBody y enviar un RPC al cliente para mover la piedra manualmente (`SetPosition` + `dBodySetVelocity`). Es costoso pero correcto.
3. **Opción C (Heredar de Transport)**: Crear una clase que herede de `Transport` (no de `ItemBase`), registrarlo con un sim module mínimo en config. Tendría netsync automático. El problema es que Transport requiere config de CfgVehicles con SimulationModule + modelo P3D adecuado.
4. **Opción D (Throttle nativo del dBody)**: Confirmar empíricamente si el engine hace resync del EntityAI en un intervalo tolerable para el gameplay. Si la frecuencia es ~100ms, puede ser "suficientemente bueno" para S1.

### ⚠️RELEVANTE: ActionPushCar como referencia para LFRS_ActionPush

`ActionPushCarCB.ApplyForce` usa exactamente el patrón que debería usar `LFRS_ActionPush`:
```cpp
dBodyApplyImpulseAt(car, impulse, car.ModelToWorld(car.GetEnginePos()));
// actionpushcar.c:52
```
Adaptado para la piedra:
```cpp
dBodyApplyImpulseAt(stone, impulse, stone.GetPosition());
```
El impulse se calcula como `bodyMass × fuerza × coef × dirección`. Este código ya está en server (la acción corre en server) y el push físicamente mueve el dBody en servidor. El cliente verá el efecto sólo si hay netsync (problema conocido).

### ⚠️RELEVANTE: OnContact para EOnContact de la piedra

El `OnContact` de Transport (que sólo corre en server) es el mismo patrón que `EOnContact` de ItemBase. La diferencia es que para Transport hay callbacks bien definidos con nombre de zona; para ItemBase el patrón es `EOnContact(IEntity other, Contact data)`. La arquitectura de daño (acumular en cache, procesar en PostSimulate) es reutilizable para la piedra si se quiere daño al jugador por impacto.

---

## Fuentes

| Archivo | Descripción |
|---------|-------------|
| `3_game/vehicles/transport.c` | Clase base Transport: crew, forces, netsync state types |
| `3_game/vehicles/car.c` | Car proto-native API: steering/throttle/brake/gear/fluid |
| `3_game/vehicles/boat.c` | Boat proto-native API (confirma BoatScript existe) |
| `3_game/vehicles/helicopter.c` | Helicopter + HelicopterAuto (auto-hover nativo) |
| `3_game/entities/pawn.c` | Pawn, PawnOwnerState, PawnMove, NetworkMoveStrategy enum |
| `1_core/defines.c` | FEATURE_NETWORK_RECONCILIATION definido en v1.24 |
| `4_world/entities/vehicles/carscript.c` | CarScript completo: contacto, fluidos, luces, EOnPostSimulate |
| `4_world/entities/vehicles/boatscript.c` | BoatScript: confirma existencia y estructura |
| `4_world/entities/vehicles/helicopterscript.c` | HelicopterScript: EOnPostSimulate vacío |
| `4_world/entities/vehicles/inheritedcars/offroadhatchback.c` | Patrón UTSource, GetSeatAnimationType |
| `4_world/entities/vehicles/inheritedcars/truck_02.c` | Patrón truck con temperatura |
| `4_world/entities/vehicles/inheritedboats/boat_01.c` | Boat_01: fluidos, asientos |
| `4_world/classes/useractionscomponent/actions/interact/actiongetintransport.c` | Boarding completo |
| `4_world/classes/useractionscomponent/actions/continuous/actionpushcar.c` | dBodyApplyImpulseAt como patrón |
| [WEB] community.bistudio.com/wiki/DayZ:Vehicle_Configuration | CfgVehicles SimulationModule |

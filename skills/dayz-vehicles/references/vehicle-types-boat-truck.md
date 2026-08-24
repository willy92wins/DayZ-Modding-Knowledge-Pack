# Vehicle types — boats, trucks (and ATV / motorbike gaps)

> Authored 2026-07-07 (F4) from vanilla `P:\scripts` and `DZ\vehicles\` config.
> Every API / class / field below carries a `path:line` citation verified against
> vanilla. `[UNVERIFIED]` marks anything the source does not pin down.

The core skill (`SKILL.md`) is written around the **CarScript** (wheeled) case.
This reference is the delta for the OTHER `Transport` subclasses: boats (a
sibling of Car under `Transport`), trucks (a Car config, not a new class), plus
honest notes on community ATVs and the motorbike gap.

---

## 1. The hierarchy — Car and Boat are SIBLINGS (the central invariant)

```
Pawn (FEATURE_NETWORK_RECONCILIATION) / EntityAI
 └─ Transport            transport.c:53-56
     ├─ Car              car.c:98            → CarScript   carscript.c:1
     └─ Boat             boat.c:31           → BoatScript  boatscript.c:41
```

- `class Transport extends Pawn` (with `FEATURE_NETWORK_RECONCILIATION`) /
  `extends EntityAI` (without) — `scripts\3_game\vehicles\transport.c:53-56`.
- `class Car extends Transport` — `scripts\3_game\vehicles\car.c:98`.
- `class Boat extends Transport` — `scripts\3_game\vehicles\boat.c:31`.
- Scripted layer: `class CarScript` — `scripts\4_world\entities\vehicles\carscript.c:1`.
  `class BoatScript : Boat` — `scripts\4_world\entities\vehicles\boatscript.c:41`.
- Config layer: `class BoatScript: Boat` base at `DZ\vehicles\water\config.cpp:17`;
  concrete `Boat_01_ColorBase: BoatScript` at `:42`. Truck base
  `Truck_01_Base: CarScript` at `DZ\vehicles\wheeled\config.cpp:18382`.

**Key structural fact:** Car and Boat are SIBLINGS, both directly under
`Transport`. They are NOT parent/child. A boat does not inherit anything wheeled,
and a car does not inherit anything buoyant. This governs where each feature
lives:

| Concern | Lives on | Why it matters |
|---|---|---|
| Crew / get-in / flip / fuel plumbing / lights / physics helpers | **Transport** | shared by cars AND boats |
| Wheels / brakes / handbrake / `CarFluid` (OIL/BRAKE/COOLANT) | **Car** | boat has NONE of these |
| Propeller / buoyancy / `BoatFluid` (fuel only) | **Boat** | car has none of these |

A **truck is just a `CarScript` config** with more axles and double wheels — no
new class (see §4).

### 1.1 What Transport OWNS (shared by Car AND Boat)

- Crew system (native): `CrewSize/CrewMemberIndex/CrewMember/CrewDriver/CrewEntry/
  CrewEntryWS/CrewTransform/CrewGetIn/CrewGetOut/CrewDeath` — `transport.c:112-149`.
  `OnDriverEnter/OnDriverExit` hooks — `transport.c:155-161`.
- Lights: `LightIsOn/LightOn/LightOff/LightToggle`, `OnBeforeLightOn`,
  `UpdateLights` — `transport.c:164-192,271`.
- Fuel refill point: `m_fuelPos` from memory point `"refill"`,
  `GetRefillPointPosWS` — `transport.c:75-78,313-326`.
- Flip detection scaffolding: `DetectFlipped` (override per-impl), `IsFlipped`,
  `DetectFlippedUsingSurface` (water-aware, uses `GetWaterDepth`) —
  `transport.c:342-439`.
- Deterministic physics helpers: `ApplyForce/ApplyTorque/ApplyImpulseAt/...` —
  `transport.c:197-212`.
- Get-in door-clearance: `IsAreaAtDoorFree` — `transport.c:634-689`.
- `GetVehicleType()` returns `"VehicleTypeUndefined"` on base —
  `transport.c:308-311` (each subclass overrides).

### 1.2 CAR-only additions (`car.c`)

- Wheels API (native): `WheelCount/WheelCountPresent/WheelGetAngularVelocity/
  WheelHasContact/WheelGetSurface/WheelGetWaterState/WheelGetEntity/
  WheelIsLocked` — `car.c:283-352`. `CarWheelWaterState` enum
  (ON_LAND/IN_WATER/UNDER_WATER) — `car.c:78-83`.
- Brakes + handbrake: `GetBrake/SetBrake/GetHandbrake/SetHandbrake/
  SetBrakesActivateWithoutDriver` — `car.c:211-223`. **Boat has NO brake API.**
- Fluids: `CarFluid` = FUEL/OIL/BRAKE/COOLANT (+USER1-4) — `car.c:18-29`.
  Speedometer `GetSpeedometer` — `car.c:113`.
- Flip via wheels: `DetectFlippedUsingWheels` (all wheels must have contact) —
  `car.c:168-189`.
- Scripted get-in actions: `SetActions()` adds `ActionOpenCarDoorsOutside,
  ActionCloseCarDoorsOutside, ActionGetInTransport, ActionSwitchLights,
  ActionCarHornShort/Long, ActionPushCar` — `carscript.c:2871-2880`.

---

## 2. BOAT — the deltas vs the CarScript contract

A boat is authored like a car up to the `Transport`-shared layer, then diverges.
Do NOT copy a car's `Axles`/brakes/`CarFluid` blocks into a boat.

| Area | Boat | vs Car |
|---|---|---|
| Fluids | `BoatFluid` = **FUEL only** — `boat.c:13-16` | Car has FUEL/OIL/BRAKE/COOLANT |
| Propulsion | **Propeller** native: `PropellerGetPosition()`, `PropellerGetAngularVelocity()` — `boat.c:112-115` | Car has wheels; no propeller |
| Brakes | **none** (no brake/handbrake protos) | Car has full brake API |
| Steering | `GetSteering/SetSteering(float)` — `boat.c:46-49` (Car's `SetSteering` has an extra `bool unused0`, `car.c:196`) | signature differs |
| Sound ctrl | `BoatSoundCtrl` = ENGINE/SPEED/PLAYER — `boat.c:2-10` (no RPM, no DOORS) | Car adds RPM, DOORS |
| Get-in | `CrewCanGetThrough/CanReachSeatFromSeat/...` all return **true** — `boatscript.c:217-235` (no doors, open cockpit) | Car GATES by door state |
| Anim | `GetAnimInstance()` = `VehicleAnimInstances.ZODIAC` — `boatscript.c:207-210` | Car uses its own instance |
| Actions | `SetActions()` = only `ActionGetInTransport` + `ActionPushBoat` — `boatscript.c:748-752` | Car adds doors/lights/horn |
| Type | `GetVehicleType()` = `"VehicleTypeBoat"` — `boatscript.c:187-190` | Car returns its own |

### 2.1 Get-in is ALWAYS free on a boat

This is the single most useful contrast for the core-skill reader. The CarScript
preflight #1 exists because a bare `CarScript` inherits `CrewCanGetThrough()` →
`false`, killing the get-in radial. A boat does NOT have that trap: `BoatScript`
overrides `CrewCanGetThrough` (and `CanReachSeatFromSeat`, etc.) to return
**true** unconditionally — `boatscript.c:217-235` — because it is an open cockpit
with no doors. There is no door-state gating to satisfy.

### 2.2 Water physics (config, not script)

On the config base `BoatScript` there is a `class Buoyancy` in place of a car's
`Axles`/brakes — `DZ\vehicles\water\config.cpp:32-40`:

```cpp
class Buoyancy
{
    linearDampeningCoefficient;
    angularDampeningCoefficient;
    linearDragCoefficient  = 0.2;
    quadraticDragCoefficient = 0.2;
    falloffPower = 0.8;
    sinkRate = 0.05;
};
```

Native buoyancy state lives on the owner: `SetBuoyancySubmerged/
GetBuoyancySubmerged` — `transport.c:22-23` (`TransportOwnerState`).

The boat `SimulationModule` (config `:162` region, block `:119-175`) has **NO
`Axles` block and NO brakes**. Instead it carries a `class Propeller` plus the
usual Engine/Clutch/Gearbox/Throttle/`class Steering`:

```cpp
class Propeller
{
    position; radius; outerRadius; innerRadius;
    efficiency; cavitationThreshold; pitch; width;
    numberOfBlades = 3; mass;
};
```

`DZ\vehicles\water\config.cpp:119-175`. There is no `Axles`/`Wheels`/brake class
anywhere in a boat's `SimulationModule`.

### 2.3 Boat runtime deltas (`boatscript.c`)

- **Auto-stop out of water:** the engine auto-stops if the propeller lifts out of
  the water — `GetWaterDepth(pos) < -0.2 → EngineStop()` in `EOnSimulate` —
  `boatscript.c:385-399`. Also stops on no-fuel — `:353-363`.
- **Decay while unoccupied:** server-side `Timer DecayHealthTick` every 10s, ×4
  if flipped — `boatscript.c:44-47,118-119,526-540`.
- **4 water particle effects** attached to memory points `ptcFxFront/Back/Side1/
  Side2` — `boatscript.c:125-140`. Effect classes `EffectBoatWaterFront/Back/Side`
  in `scripts\4_world\entities\effects\boatwatereffects.c:10,116,199` (speed-gated
  emitters; the Back effect reads `PropellerGetAngularVelocity` for speed
  `boatwatereffects.c:183`).
- **Vital `SparkPlug`** gates engine start — `boatscript.c:270-278`
  (`CheckOperationalRequirements`). (Contrast the car's SparkPlug+GlowPlug double
  default in SKILL.md preflight #8 — the boat only ever demands its SparkPlug.)
- **Flip uses the SURFACE detector** (water-aware), not wheels —
  `boatscript.c:482-487`.

### 2.4 Boat actions (`scripts\4_world\...\actions\`)

- `ActionStartEngineBoat` (continuous) / `ActionStopEngineBoat` (single-use):
  both cast target to `BoatScript`, require `CrewDriver()==player`, and guard
  `GetNetworkMoveStrategy()==PHYSICS` to skip server exec —
  `actionstartengineboat.c:9-70`, `actionstopengineboat.c:1-52`. On execute they
  call `vehicle.OnIgnition()`; on finish, `EngineStart()`.
- `ActionPushBoat extends ActionPushObject` — full-body, syncs `SyncSoundPushBoat`
  on start/end (server) — `actionpushboat.c:17-46`.
- `ActionRepairBoatChassis/Engine extends ActionRepairVehiclePartBase` — repairs
  non-`Engine` zones between WORN and RUINED — `actionrepairboatchassis.c:1-47`.

---

## 3. (reserved — see §4 for the truck deltas)

---

## 4. TRUCK — a Car config with more axles + double wheels (NOT a new class)

A truck (`Truck_01_Base: CarScript` — `DZ\vehicles\wheeled\config.cpp:18382`) is
NOT a new class. It is a plain `CarScript` config; the deltas are pure config.

| Feature | Truck config | Standard car (contrast) |
|---|---|---|
| Axle count | **3 axles**: `class Front`, `class Middle: Rear`, `class Rear: Rear` — `config.cpp:18521-18624` | 2 axles (Front/Rear) |
| Drivetrain | `drive="DRIVE_642"` (6×4) — `config.cpp:18491`; `class CentralDifferential { type="DIFFERENTIAL_LOCKED"; }` — `:18516-18520` | typically DRIVE_4x2/4x4 |
| Wheel slots | 6 driven hubs `Truck_01_Wheel_1_1..2_3` + 2 spares — `config.cpp:18394-18401` | 4 hubs |
| Double wheel | Middle+Rear hubs take **`Truck_01_WheelDouble`** — `config.cpp:18089-18106`; its `inventorySlot[]` = the 4 rear slots `1_2,1_3,2_2,2_3`. `width=0.40` (vs single `0.20`), `weight=50000` (vs 30000), better grip/resistance | single `Truck_01_Wheel` |
| Dual-wheel craft | `Truck_01_Wheel + Truck_01_Wheel → Truck_01_WheelDouble` recipe — `crafttruck01doublewheel.c:27-46`; reverse decraft needs Crowbar/LugWrench → 2 wheels — `decrafttruck01doublewheel.c:36,48-60` | n/a |
| Crew | **4 seats**: Driver + CoDriver + Cargo1 + Cargo2 (`class Crew` w/ `proxyPos="crewCargo1/2"`) — `config.cpp:265-283, 1341-1364` region + truck cargo `crewCargo1/2` | 2-4 depending |
| Cargo | `class Cargo { itemsCargoSize[]={10,40}; }` — `config.cpp:18626-18631` | small/none |
| Fuel | `fuelCapacity=120; fuelConsumption=30` — `config.cpp:18459-18460` | ~50 / lower |

### 4.1 The "double wheel" invariant

**One attachment classname per rear hub covers BOTH physical tyres via the
`Truck_01_WheelDouble.p3d` model** — it is NOT two wheel entities per hub. The
rear axles reference it via `inventorySlot` in the Axles/Wheels blocks
(`config.cpp:18569-18622`). Each Middle/Rear wheel also declares
`wheelHub="wheel_X_Y_damper_land"` plus `animDamper`/`animTurn`/`animRotation`.

So a truck's structural parity is a car's parity (SKILL.md preflight #1-#9) with:
(a) 6 wheel hubs instead of 4, (b) the rear four resolving to one WheelDouble
classname each, (c) 3 axle blocks with a locked central differential, (d) 4-seat
crew. Nothing about get-in, DamageZones, or the vital-igniter chain changes — it
is still `CarScript`.

---

## 5. ATV (quad) — community pattern, one line

Community ATVs are plain `CarScript` with slots hung off `Chassis` instead of
`Body`. (No vanilla ATV in the base game; this is the community convention
observed in the heli/RaG research pass.) Everything else is the standard
`CarScript` contract in the core skill (LFQuad is the worked example throughout
`SKILL.md` — a quad IS a car).

---

## 6. Motorbikes — honest gap

No vanilla motorbike and no community source on disk; the 2-wheel physics pattern
is an open gap (needs a real project or a community PBO to reverse-engineer).
Do not fabricate a `SimulationModule` for two wheels from the car pattern — a
motorbike's lean/balance model is not derivable from the 4-wheel `Axles` blocks
and there is nothing verified to cite. Flag `[UNVERIFIED]` and research first.

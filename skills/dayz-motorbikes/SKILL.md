---
name: dayz-motorbikes
description: >
  Author, import, configure and debug single-track vehicles (motorbikes /
  motorcycles) in DayZ 1.30 Experimental build 1.30.164014. Covers MotorbikeScript,
  simulation = "motorbike", 2-wheel physics (Wheels block without Axles, Brakes
  split Front/Rear, lean/steering/tipover), kickstand, kickstart actions,
  dedicated 3rd person camera (ID 32), and the DayZ 1.30 modular vehicle refactor
  (VehicleLightsComponent, VehicleHornComponent, VehicleVFXComponent). Use when
  creating a new motorbike, porting two-wheel assets (Jawa, dirt bikes, scooters),
  migrating existing vehicle mods from 1.29 to 1.30, or fixing get-in/fall-over bugs.
  Do NOT use for 4-wheel cars, trucks or quads (see dayz-vehicles), aircraft
  (see dayz-aviation), raw 3D mesh processing (see dayz-model-pipeline), or
  custom player animation authoring (see dayz-animation-pipeline).
---

# DayZ Motorbikes (Single-Track Vehicles) & 1.30 Vehicle Refactor

> **Preflight: rider posture (added 2026-09-28, LFDucati T99; B1 measured on the same day) [EXACT except where marked].** Chosen solely by `GetAnimInstance()` -> `SetVehicleType` (`exp\scripts\scripts\4_World\Classes\UserActionsComponent\Actions\Interact\ActionGetInTransport.c:104-107`) -> fixed state and column in `Vehicles.agf` (five nodes require literal `VehicleType == 10 || VehicleType == 11`: `:1429, 1474, 1529, 1570, 2806`). Neither the model nor the config moves the hands: they are fixed by the handlebar pose clip, and there is no foot IK. GP clip-ons with MOTO1/MOTO2 leave the hands ~40 cm above: custom clips are required. Survivor Animations MOTORCYCLE (16) = car driver body (Offroad Hatchback) with IK hands, 1.29 format graph (crashes 1.30). Corrects `references/rider-animation.md:77`: 1.29 graphs are TEXT (`$AnimGraph 7`), not binary. Approach without touching the graph: registered child `.asi` + `SetAnimationInstanceByName`, like surrendering (`PlayerBase.c:2087-2088`, `DayZPlayerCfgBase.c:1532-1537`): **works with the motorbike stopped** on dedicated server and local client (measured 2026-09-28, LFDucati B1, LL-530), **and stopped and moving with custom clips** (LFRider on the H2R, same day, LL-533..535): a DayZATool (`ANIMSET5`) clip is within 0.4 mm of its FK; steering clips are distributed across ±45° of REAL wheel angle on all motorbikes (`Vehicles.agf:50`, `:1466`), not at the limit of each one; transitions are exported as full whole-body posture (as additive differences they collapse the skeleton). With observers and in edge cases, untested. Common mod and toolchain: LFRider (not published). Recipe, pitfalls, and the pose in four pieces: `references/rider-animation.md` §Per-bike pose. Detail: LFDucati research notes (not published).

DayZ 1.30 Experimental (build 1.30.164014) introduces full native engine support for single-track vehicles via the engine simulation type `simulation = "motorbike"` (`exp\bin\bin\config.cpp:1059`, in-game `bin\config.cpp`). At the class architecture level, `class Motorbike: Transport` is a direct sibling of `Car` and `Boat` in native C++ (`exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:30`, in-game `scripts\3_Game\Vehicles\Motorbike.c`), not a child of `Car`. In the game script layer, `MotorbikeScript` inherits directly from `Motorbike` (`exp\scripts\scripts\4_World\Entities\Vehicles\MotorbikeScript.c:53`, in-game `scripts\4_World\Entities\Vehicles\MotorbikeScript.c`), NOT from `CarScript`.

### Three-Layer Inheritance Hierarchy
1. **Engine Config Layer (`bin\config.cpp`)**:
   `Transport` -> `Motorbike` (`exp\bin\bin\config.cpp:1054-1059`, with `simulation = "motorbike"`).
2. **3_Game Script Layer (`scripts\3_Game\Vehicles\`)**:
   - `TransportType` -> `MotorbikeType` (`exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:16-18`).
   - `TransportOwnerState` -> `MotorbikeOwnerState` (`Motorbike.c:20-23`).
   - `TransportMove` -> `MotorbikeMove` (`Motorbike.c:25-27`).
   - `Transport` -> `Motorbike` (`Motorbike.c:30-370`).
3. **4_World Script Layer (`scripts\4_World\Entities\Vehicles\`)**:
   - `MotorbikeOwnerState` -> `MotorbikeScriptOwnerState` (`exp\scripts\scripts\4_World\Entities\Vehicles\MotorbikeScript.c:23-25`).
   - `MotorbikeMove` -> `MotorbikeScriptMove` (`MotorbikeScript.c:27-29`).
   - `Motorbike` -> `MotorbikeScript` (`MotorbikeScript.c:53-1765`).
   - `MotorbikeScript` -> `Motorbike_01_ColorBase` (`exp\scripts\scripts\4_World\Entities\Vehicles\InheritedMotorbikes\Motorbike_01.c:1-166`).
   - `MotorbikeScript` -> `Motorbike_02_ColorBase` (`exp\scripts\scripts\4_World\Entities\Vehicles\InheritedMotorbikes\Motorbike_02.c:1-140`).

A motorcycle in DayZ 1.30 has no relationship to the traditional four-wheel subsystem: it completely lacks the `Axles` hierarchy, does not use doors (`IsAreaAtDoorFree` always returns `true`), does not require a radiator or vital coolant circuit (`IsVitalRadiator()` returns `false`, `MotorbikeScript.c:321-324`), and the two vanilla motorbikes dispense with a battery because they override `NeedElectricitySourceDevice()` to `false` (`Motorbike_01.c:33-36`, `Motorbike_02.c:34-37`); the default in `Transport` is `true` (`Transport.c:821-824`) and `MotorbikeScript` does not change it. In return, the Enfusion engine simulates a dynamic two-wheel balance model with gyroscopic lean (`maxLeanAngle[]`), decoupled lever and pedal brakes, kickstand (`SetKickstand`), fall and destabilization (`FallOver`), and mandatory driver ejection on tipover (`CrewShouldEject`).

All technical evidence in this skill comes from code and configuration extraction (`source_verified`) of Experimental 1.30.164014. No dynamic behavior is declared runtime tested (`runtime_verified`).

## Family Selector

| Use case | Tool and skill path | Key files |
|---|---|---|
| New vanilla-like motorbike (created from scratch or derived from Motorbike_01 / Motorbike_02) | **This skill (`dayz-motorbikes`)** | [references/forward-contract.md](references/forward-contract.md) and [references/config-contract.md](references/config-contract.md) |
| Motorbike imported from another game (ripped / asset store / Blender) | **This skill** + `dayz-model-pipeline` (mesh and LODs) | [references/forward-contract.md](references/forward-contract.md) and `dayz-model-pipeline/SKILL.md` |
| Traditional car, truck, quad, or boat | `dayz-vehicles` (sibling land vehicle skill) | `dayz-vehicles/SKILL.md` |
| Car mod migration from 1.29 to 1.30 (components, lights, horn, VFX) | [references/vehicle-1.30-refactor.md](references/vehicle-1.30-refactor.md) | [references/vehicle-1.30-refactor.md](references/vehicle-1.30-refactor.md) |
| Rider animations, handlebar poses, or .agf graph | [references/rider-animation.md](references/rider-animation.md) + `dayz-animation-pipeline` | [references/rider-animation.md](references/rider-animation.md) and `dayz-animation-pipeline/SKILL.md` |

Architecture recommendation: for a new motorbike, inherit in Enforce Script directly from `MotorbikeScript` and copy the structure of `Motorbike_01_ColorBase` in your `config.cpp` (see [references/config-contract.md](references/config-contract.md)). Do not attempt to inherit from `CarScript` or adapt 4-wheel `Axles` blocks: `simulation = "motorbike"` does not use them (invariant 1; exact failure mode is not measured [UNVERIFIED]). If inheriting directly from `MotorbikeScript`, override `NeedElectricitySourceDevice()`: without override it returns `true` and the motorbike would require a battery (`Transport.c:821-824`).

## Day-0 critical path for a new motorbike

Ordered checklist of minimum mandatory deliverables to have an operational motorbike:

1. [EXACT] **CfgPatches and CfgVehicles declaration**: declare the addon with mandatory dependency on `"DZ_Vehicles_Singletrack"` (`exp\vehicles_singletrack\DZ\vehicles\singletrack\config.cpp:22-31`, in-game `DZ\vehicles\singletrack\config.cpp`). Inherit from `MotorbikeScript` with `simulation = "motorbike"`.
   ```cpp
   class CfgPatches { class MiMoto { units[] = {}; requiredAddons[] = {"DZ_Data", "DZ_Vehicles_Singletrack"}; }; };
   ```
2. [EXACT] **`class Crew` block**: define `class Driver` and `class CoDriver: Driver` pointing to `actionSel = "seat_driver"`, `proxyPos = "crewDriver"`, `getInPos = "pos_driver"`, `getInDir = "pos_driver_dir"`, and both with `isDriver = 1;` (`config.cpp:67-85`).
3. [EXACT] **`class SimulationModule` block**: declare `class Wheels` with `class Front` and `class Rear` (without `Axles`), `class Brakes` with `Front` (`input = 1`) and `Rear` (`input = 0`), and lean curves in `class Steering` (`config.cpp:228-343`).
4. [EXACT] **Animation sources (`AnimationSources`)**: declare shock absorbers `damper_1`, `damper_2` and wheel state `AnimHitWheel_1`, `AnimHitWheel_2` (`config.cpp:112-148, 344-364`). If it has a flip-up seat, add `SeatDriver`.
5. [EXACT] **Damage system (`DamageSystem`)**: define `GlobalHealth` (1000 HP) and the zones from `Motorbike_01`: `Chassis`, `Fender` (transfer target for `Front`), `Engine` (`inventorySlots[] = {"SparkPlug"}`), `Front`, `Reflector_1_1`, `Back`, and `FuelTank`, plus `GUIInventoryAttachmentsProps` (`config.cpp:365-515`).
6. [EXACT] **Wheels and Proxies**: define classes derived from `MotorbikeWheel` for front and rear wheels with their `_Ruined` versions in `CfgVehicles` (`config.cpp:155-214`), and proxies in `CfgNonAIVehicles` (`config.cpp:1061-1083`):
   ```cpp
   class MiMoto_Wheel_1: MotorbikeWheel { scope = 2; radius = 0.29; width = 0.06; tyreLateralFriction = 3.0; };
   ```
7. [EXACT] **High-speed anti-snag geometry**: define `speedGeomActivation = 0.29;` and `speedGeoms[] = {"geotohide"};` (`config.cpp:226-227`).
8. [EXACT] **4_World Script Class**: create class derived from `MotorbikeScript` (`exp\scripts\scripts\4_World\Entities\Vehicles\InheritedMotorbikes\Motorbike_01.c:1-166`). Configure in constructor impact damages (`m_VehicleContactDamageCoef`, `m_CrewContactDamageCoef`), engine and horn SoundSets, and register lights in `m_LightsComponent`:
   ```c
   m_VehicleContactDamageCoef = 0.03;
   m_CrewContactDamageCoef = 0.018;
   ```
9. [EXACT] **Mandatory script overrides**: implement `GetAnimInstance()` returning `VehicleAnimInstances.MOTO1` (10) or `MOTO2` (11), `HasDirectionalInOutAction()` (`true`), `GetSeatAnimationTypeDirectional()`, `GetTransportCameraDistance()`, `GetTransportCameraOffset()`, and `NeedElectricitySourceDevice()` (`false` on magneto/kickstart bikes).
10. [DESIGN] **Geometry and P3D model**: ensure bone `"drivewheel"` on the front fork, light memory points (`light_1_1`, `light_1_2_reverse`), smoke (`ptcExhaust_start/end`, `ptcEnginePos`), fuel cap (`refill`), and damage selections (`dmgZone_*`). Details in [references/forward-contract.md](references/forward-contract.md).
11. [EXACT] **Sounds**: reference engine, exhaust, shock absorber, and horn SoundSets defined in `exp\sounds_hpp\DZ\sounds\hpp\config.cpp` (motorbike SoundSets `:98179-98909`, SoundShaders `:59253-59918`):
    ```c
    m_EngineStartOK = "Motorbike_01_engine_start_SoundSet";
    m_HornComponent.RegisterSound(VehicleHornMode.SHORT, "Motorbike_01_Horn_Short_SoundSet");
    ```
12. [DESIGN] **Economy and Spawn**: register in `types.xml` and `cfgspawnabletypes.xml` with spark plug (`SparkPlug`) and wheels installed.
13. [EXACT] **Decide rider posture BEFORE modeling (added 2026-09-19, LFDucati)**: no runtime hand adjustment exists. Each vanilla motorbike has its own column in the animation set (`"Jawa_05"`, `"Jawa_Bitrak"`: `exp\anims_workspaces\DZ\anims\workspaces\player\player_main\player_main.ast:1114-1121`) with its own clip set (26 and 27 distinct `.anm` clips; e.g. `Vehicle.Jawa_05.DriverSteeringMain` → `…/Jawa_05/p_motorbike_01_driver_steering_pose.anm`, `player_main.asi:5131`; `Vehicle.Jawa_Bitrak.DriverSteeringMain` → `…/Jawa_Bitrak/p_motorbike_02_driver_steering_pose.anm`, `player_main.asi:5179`), and hand IK takes its targets `LHandIKTarget`/`RHandIKTarget` from those clips (`AnimNodeIK2Target0` with child `SteeringBlend`, `Vehicles.agf:17-46`), not from the motorbike P3D. There are no Arma-style config keys (`driverLeftHandAnimName`: 0 occurrences in `vehicles_singletrack`, `vehicles_wheeled`, and `bin` `config.cpp`). Consequence: either you fit the handlebar/footpegs/seat of YOUR model to the contact points of MOTO1 or MOTO2 (measure them in-game on the vanilla bike before touching ergonomics), or you add a column with custom clips, which means modifying `player_main` (the single-animation-mod wall, see [references/rider-animation.md](references/rider-animation.md) §5). (corrected 2026-09-28) There is a third way without touching `player_main`: a child `.asi` with custom clips only on your bike class (preflight above; tested in-game stationary and moving on the H2R). A handlebar of a different width does NOT fix itself.

## The ten invariants that break a motorbike

Each rule must be strictly followed to prevent critical failures in the entity:

### 1. Flat `Wheels` in config, NEVER `Axles` block
- **Symptom** [UNVERIFIED, expected and not measured in-game]: simulation initialization failure when spawning the entity; exact failure mode (RPT error, inert entity, or process crash) has not been measured.
- **Cause**: The `simulation = "motorbike"` engine reads directly `class Wheels { class Front; class Rear; }` (`exp\vehicles_singletrack\DZ\vehicles\singletrack\config.cpp:88-106`). The `class Axles` hierarchy belongs exclusively to `simulation = "car"` / `"carx"`.
- **Citation**: `exp\vehicles_singletrack\DZ\vehicles\singletrack\config.cpp:88-106, 305-342`.
- **Remedy**: Remove any `Axles` block from `SimulationModule`. Declare `Front` and `Rear` directly inside `Wheels: Wheels`:
  ```cpp
  class Wheels: Wheels
  {
      class Front: Front { inventorySlot = "MiMoto_Wheel_1"; animDamper = "damperfront"; };
      class Rear: Rear   { inventorySlot = "MiMoto_Wheel_2"; animDamper = "damperback"; };
  };
  ```

### 2. Brakes Front input=1 / Rear input=0
- **Symptom**: The front brake lever does not respond, or the rear pedal blocks the front wheel unexpectedly.
- **Cause**: On motorbikes, the front brake is bound to the handbrake channel (`input = 1`) and the rear to the regular pedal brake (`input = 0`). The API documents it: `SetBrake` is the rear brake and `SetHandbrake` is the front brake (`exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:129-139`).
- **Citation**: `exp\vehicles_singletrack\DZ\vehicles\singletrack\config.cpp:257, 266`.
- **Remedy**: In `SimulationModule -> Brakes`, define `class Front { input = 1; ... };` and `class Rear { input = 0; ... };`:
  ```cpp
  class Brakes
  {
      class Front { input = 1; pressureBySpeed[] = {0,0.85,10,0.7,40,0.6,60,0.5,80,0.5}; };
      class Rear  { input = 0; pressureBySpeed[] = {0,0.95,10,0.1,20,0.1,40,0.1,50,0.1}; };
  };
  ```
  The rear pressure drops from `0.95` at standstill to `0.1` from point `10` on the curve (`config.cpp:267`); whether this serves to prevent rear axle skids is an interpretation [UNVERIFIED].

### 3. `"drivewheel"` bone in P3D for headlight
- **Symptom**: The headlight light cone remains pointed rigidly forward along the chassis and does not rotate when turning the handlebars.
- **Cause**: `MotorbikeScript.c:1107-1109` looks up the `"drivewheel"` bone in a hardcoded manner via `GetBoneIndex("drivewheel")` to align the light cone with the front fork.
- **Citation**: `exp\scripts\scripts\4_World\Entities\Vehicles\MotorbikeScript.c:1107-1109`.
- **Remedy**: Name the front fork and handlebar selection `"drivewheel"` in the P3D geometry and in `skeletonBones[]` of your `model.cfg`:
  ```c
  int driveWheelIndex = GetBoneIndex("drivewheel");
  m_LightsComponent.AttachLightOnObject("Front", GetMemoryPointPos(m_HeadLightPoint), vector.Zero, VehicleLightMode.SEGREGATED, driveWheelIndex);
  ```

### 4. `SeatDriver` and `CanGetIn` entry condition
- **Symptom**: The player receives no prompt to get on the bike (`CanGetIn()` returns `false`).
- **Cause**: If inheriting from `Motorbike_01_ColorBase`, the script requires `GetAnimationPhase("SeatDriver") == 0.0` (`Motorbike_01.c:97`). If your model lacks the `"SeatDriver"` animation, the condition permanently fails.
- **Citation**: `exp\scripts\scripts\4_World\Entities\Vehicles\InheritedMotorbikes\Motorbike_01.c:92-98`.
- **Remedy**: For motorbikes without a flip-up seat, inherit directly from `MotorbikeScript` or override `CanGetIn()` without evaluating `"SeatDriver"`. If keeping the seat, declare `SeatDriver` in `AnimationSources` with initial phase `0.0`:
  ```cpp
  class AnimationSources: AnimationSources
  {
      class SeatDriver { source = "user"; initPhase = 0.0; animPeriod = 1.0; };
  };
  ```

### 5. Contact damage coefficients and instant death
- **Symptom**: The rider dies instantly upon grazing a minor obstacle at low speed.
- **Cause**: Each contact produces two quantities on the server (`CheckContactCache`, `MotorbikeScript.c:1252-1357`, called inside `if (g_Game.IsServer())` at `:743-758`): vehicle damage `dmg = |impulso × m_VehicleContactDamageCoef|` (`:1263`) and the crew damage base `crewDmgBase = |impulso / masa × 500 × m_CrewContactDamageCoef|` (`:1264`, calculates as if the motorbike weighed 500 kg). Threshold tiers are decided with `dmg`; only the last damages the crew, and there death depends on `crewDmgBase` (`DamageCrew`, `:1360-1412`).
- **Citation**: `exp\scripts\scripts\4_World\Entities\Vehicles\MotorbikeScript.c:1263-1264, 1301-1350, 1369-1383` and `exp\scripts\scripts\3_Game\constants.c:898-901`.
- **Tiers according to vehicle `dmg` (`constants.c:898-901`)**:
  - `dmg < 10` (`MOTORBIKES_CONTACT_DMG_MIN`): ignored (`:1301-1302`).
  - `10 ≤ dmg < 25` (`MOTORBIKES_CONTACT_DMG_THRESHOLD_SMALL`): damage to zone without transfer (`NO_TRANSFER`) and light crash sound (`:1310-1320`).
  - `25 ≤ dmg < 40` (`MOTORBIKES_CONTACT_DMG_THRESHOLD_MID`): `FallOver()` and light sound; crew takes no damage (`:1321-1331`).
  - `dmg ≥ 40`: `DamageCrew(crewDmgBase)`, `FallOver()` and heavy sound (`:1332-1344`).
  - From `dmg ≥ 10`, `ProcessDirectDamage` applies `dmg` to the impacted zone (`:1350`).
- **Inside `DamageCrew`**: if `crewDmgBase > 80` (`MOTORBIKES_CONTACT_DMG_KILLCREW`, strictly greater) it executes `crew.SetHealth(0.0)` (`:1369, 1383`); otherwise, it subtracts shock from 50 to 150 and health from 2 to 100, interpolated between 25 and 80 (`:1387-1409`).
- **Remedy**: `m_VehicleContactDamageCoef` decides when the motorbike falls (`dmg ≥ 25`) and when the crew is damaged (`dmg ≥ 40`); `m_CrewContactDamageCoef` decides if that damage kills (`crewDmgBase > 80`). Vanilla values: `0.03` / `0.018` (`Motorbike_01.c:5-6`) and `0.035` / `0.012` (`Motorbike_02.c:5-6`).

### 6. Lean angles (`maxLeanAngle`) and tipover (`tipoverAngle`)
- **Symptom** [UNVERIFIED, expected and not measured in-game]: the motorbike falls over on its own when accelerating or stays vertical without leaning in turns.
- **Cause**: `Steering` declares lean curves and threshold `tipoverAngle = 50.0`; both are consumed by native simulation (`simulation = "motorbike"`), not script, so their exact effect above the threshold cannot be verified in text [UNVERIFIED].
- **Citation**: `exp\vehicles_singletrack\DZ\vehicles\singletrack\config.cpp:231-243`.
- **Remedy**: Copy the validated table from `Motorbike_01`:
  ```cpp
  class Steering
  {
      tipoverAngle = 50.0;
      maxLeanAngle[] = {1,0,5,8,15,10,30,17,40,22,80,30};
      maxSteeringAngle[] = {1,40,5,40,15,20,30,5,40,3,80,1};
      directControl[] = {0.0,1.0,5.0,1.0,30.0,0.6,60.0,0.2,80.0,0.0};
  };
  ```

### 7. Kickstand (`Kickstand`) in lifecycle
- **Symptom** [UNVERIFIED, expected and not measured in-game]: the motorbike collapses sideways upon spawning on the ground.
- **Cause**: the vanilla constructor deploys the kickstand using native method `SetKickstand(1)`; what native physics specifically does with that value is an assumption (see digest A, SUPOSICIONES 2) [UNVERIFIED].
- **Citation**: `exp\scripts\scripts\4_World\Entities\Vehicles\MotorbikeScript.c:141`.
- **Remedy**: Ensure the constructor maintains `SetKickstand(1);`. No retail script retracts the kickstand: the only `SetKickstand(0.0)` is in `OnInput` within `#ifdef DIAG_DEVELOPER` and only runs with debug mode active (`MotorbikeScript.c:841-843, 915`). If it retracts while riding, native simulation does it [UNVERIFIED].

### 8. Hidden geometry at speed (`speedGeomActivation` / `speedGeoms`)
- **Symptom**: The motorbike collides with invisible terrain micro-bumps or is flung into the air at high speed.
- **Cause**: The support stand geometry collides with ground unevenness if not disabled when moving at high speed. In `Motorbike_01` it activates at `0.29` and in `Motorbike_02` at `0.27`.
- **Citation**: `exp\vehicles_singletrack\DZ\vehicles\singletrack\config.cpp:226-227, 729-730`.
- **Remedy**: Define in config `speedGeomActivation = 0.29;` and `speedGeoms[] = {"geotohide"};`, isolating kickstand geometry into the `"geotohide"` component of LOD Geometry.

### 9. Mandatory modular components (Lights, Horn, VFX)
- **Symptom** [UNVERIFIED, expected and not measured in-game]: failure when accessing an uninstantiated component in the lighting code path, or horn without sound and without noise for infected.
- **Cause**: In DayZ 1.30, lights no longer reside in `m_Headlight` nor the horn in `m_CarHornState`; they operate in independent components.
- **Citation**: `exp\scripts\scripts\4_World\Entities\Vehicles\MotorbikeScript.c:113, 127, 139`.
- **Remedy**: Instantiate `VehicleLightsComponent`, `VehicleHornComponent`, and `VehicleVFXComponent` in the constructor, registering their corresponding profiles and SoundSets:
  ```c
  m_LightsComponent = VehicleLightsComponent(this);
  m_HornComponent = VehicleHornComponent(this);
  InitializeParticles(); // Instancia m_VFXComponent
  ```
- [EXACT] Vehicle lights are toggled with `UAToggleVehicleLights` via `ToggleVehicleLightsActionInput` (`exp\scripts\scripts\4_World\Classes\UserActionsComponent\ActionInput.c:849-855`); `ActionSwitchLights.GetInputType()` returns that class (`ActionSwitchLights.c:16-19`). `UAToggleHeadlight` is the headtorch (`ToggleLightsActionInput`, `ActionInput.c:776-782`). Both names exist in `exp\bin\bin\constants.xml:90-91`. Detail: [references/actions-hud-lights-sounds.md](references/actions-hud-lights-sounds.md) §5.

### 10. Blowtorch-exclusive repair actions in build 1.30.164014
- **Symptom**: The player receives no action to repair engine or chassis when aiming with a wrench or epoxy putty.
- **Cause**: In this Experimental build, motorbike repair actions are assigned only to the blowtorch (`Blowtorch.c`). Additionally, `ActionRepairMotorbikeEngine` was not registered in `ActionConstructor.c`.
- **Citation**: `exp\scripts\scripts\4_World\Entities\ItemBase\Blowtorch.c:109, 111, 113` (the only motorbike repair `AddAction` in all of `scripts`) and `exp\scripts\scripts\4_World\Classes\UserActionsComponent\ActionConstructor.c:252-260` (registration of motorbike actions, without `ActionRepairMotorbikeEngine`).
- **Remedy**: If your mod requires repairing with traditional hand tools, you must bind actions to items via `modded class` and insert them into `ActionConstructor`:
  ```c
  modded class ActionConstructor
  {
      override void RegisterActions(TTypenameArray actions)
      {
          super.RegisterActions(actions);
          actions.Insert(ActionRepairMotorbikeEngine);
      }
  }
  ```

## Measured lessons from LFDucati (1.30.164014, September 2026)

Measured in-game with a 157 kg Desmosedici GP16 inherited from `Motorbike_02_ColorBase` (DayZDiag, dedicated server and client). Each rule cites its lesson from the vault (`AI/20_Knowledge/lessons-learned.md`), which stores the narrative and numbers.

1. **Overall first gear must be short.** [EXACT] With the automatic clutch, first × `driveRatio` between 20 and 26 starts (Motorbike_02: 25.7; LFDucati settled on 20); 6.77, that of a real MotoGP, does not move the bike: 0.05-0.1 km/h wide open and rpm stuck at two values. Decide it with a session A/B using the vanilla drivetrain as control, and measure the ratio applied by the engine (rpm·π/30 ÷ ω of the drive wheel) to confirm config loaded. On 1.30 motorbikes `w0` is the front: distinguish wheels by rolling radius (ω·r = v), not by `WheelGetPositionLS` (LL-506).
2. **Suspension is sized to the load of each wheel.** [INFERRED] The model fitting measurements is F = k (u + travelMaxDown), with the wheel hanging from the modeled axle and u linear in the damper phase (phase 0 = -travelMaxDown, phase 1 = +travelMaxUp). [EXACT] With it, in the variant resting solely on the springs the sum of forces / g yielded 157.1 kg for a 157.0 kg bike; in the product red variant the springs only carried 132.7 kg and the rest rested on the Engine box against the ground. For it to rest on the axle, travelMaxDown = F / k on each wheel (or increase k and scale damping with √(k·m)). A motorbike inheriting suspension from a lighter one inherits its sag; if the sum does not match the mass, look for what else is resting on the ground (LL-512).
3. **No Geometry box can touch the ground at full suspension compression.** [EXACT] Each hit is a contact: damage deciding the tier is `Math.AbsInt(data[0].m_Impulse * m_VehicleContactDamageCoef)` (`MotorbikeScript.c:1263`) and, from 25 upwards, the branches call `FallOver()` (`:1310-1342`), throwing the rider off (invariant 5). Gate before testing: lowest point of each component, minus remaining compression from rest, ≥ 5 mm; and `m_VehicleContactDamageCoef` scaled by mass (× m_vanilla / m_propia) so the same hit counts equally (LL-507).
   - (LL-507 details) [EXACT] If a `..._damper_land` box is lowered to seat the physical wheel,
     shrink it keeping the SAME centre - the physical wheel does not move; and log contacts
     server-side (`Transport.OnContact`: zone, point, impulse change) before tuning coefficients.
     (Measured in game, DayZ 1.30.164014 Exp.)
4. **The rider proxy only positions and yaws around the vertical.** [EXACT] The engine applies the crew proxy frame but keeps the player vertical: a proxy tilted 20 degrees forward resulted in yaw of about 17 degrees and zero lean; a rolled proxy produced a player standing 30 cm off the bike. Crouching or leaning the rider requires animation (preflight above and `references/rider-animation.md`) (LL-511, LL-509).
5. **A hidden selection only changes material if `model.cfg` lists it in `sections[]`.** [EXACT] Config alone is not enough and the failure is silent: check it in the ODOL (sectional selection), not in config. Lights render by index in `hiddenSelections`: headlight 0, brake 1, tail light 2, and dashboard 3 (`MotorbikeScript.c:114-122`), and Motorbike_02 moves brake to 2 of the tail light (`Motorbike_02.c:20-21`); in a custom model those positions might fall onto livery sections (LL-508).

## How to verify

1. **Offline linter before opening the game**:
   Run the offline validator on your addon directory:
   `python <KNOWLEDGE_PACK>/tools/dayz-script-validator/scripts/script_validator.py <addon_root>`
   - Check `errors` and `warnings` keys at the root of output JSON.
   - Return code is 0 (PASS), 1 (FAIL), or 2 (WARN).
   - Always gate by `len(errors) == 0`; a clean tree with minor warnings returns 2 and is valid.
   - Check that no broken references exist in Enforce `.c`, layouts, `config.cpp`, or `.rvmat`.
   - Use delta comparison against the unchanged base tree to isolate errors introduced by your mod.
2. **In-game verification ladder (via DayZ-MCP or local Diag server)**:
   - **Step 1 (Spawn)**: Spawn the bike using the `world_spawn` tool on a local server run with `-filePatching`. Confirm it stays upright on the kickstand without endless oscillations or sinking into the ground.
   - **Step 2 (Render)**: Check that wheels show their correct proxies, rvmat materials respond, and there are no grey panels or invisible meshes due to incorrect selection names.
   - **Step 3 (Get-In)**: Trigger `vehicle_get_in_client` approaching from the left flank and then from the right; verify that `ActionGetInTransport` activates directional animations `GetIn_L` and `GetIn_R`.
   - **Step 4 (Starting and Driving)**: Trigger `ActionStartEngineMotorbike` or the `engine_set` tool. Listen for kickstart lever sound, verify front headlight rotates together with handlebars (`drivewheel`), and check that the 3rd person camera follows steering with spring damping.
   - **Step 5 (Driving Telemetry)**: Monitor RPM, speed, and gear via `vehicle_telemetry` or `telemetry_read` to verify `SimulationModule` response.
   - **Step 6 (Fall and Recovery)**: Cause a side collision or sharp turn to induce a forced tipover. Check that the player is ejected to the ground (`CrewShouldEject`) and that `ActionPickUpMotorbike` allows picking it up via `action_use`.
   > **Measured correction (2026-09-19, LFDucati; citations re-read in `DayZ_MCP_dev` on that date):** this ladder CANNOT be run today with DayZ-MCP on Experimental 1.30.
   > (a) The approved launcher only starts Stable: the executable is hardcoded in `tools\native-launchers\dayz-test-v1\worker-runtime.json` (all 10 projects point to `...\common\DayZ\DayZDiag_x64.exe`) and the daemon
   > only accepts `<DAYZ_GAME_PATH>\DayZDiag_x64.exe`, a global setting (`tools\dayz_mcp\daemon.py:552-557`, `process_lifecycle.py:1782-1793`). (b) The `@DayZ_MCP` addon is unaware of `Motorbike`
   > (0 occurrences in `addon\`): control and telemetry cast to `CarScript` (`addon\scripts\5_Mission\MCPClientBridge.c:1191, 2812-2826`), so `engine_set`, `vehicle_control`, and the engine portion
   > of `vehicle_telemetry` do not see a motorbike, which in 1.30 inherits from `Transport` and not from `CarScript`. (c) There is no verb to read player bones (rider pose).
   > Approach used while 1.30 is Experimental: custom diagnostic addon with scenario in a `modded MissionServer` behind a command line parameter, `LFD_…` output in `script_*.log`,
   > two `.bat` files pointing to `DayZ Exp\DayZDiag_x64.exe` launched via `cmd /c start` and a Python driver awaiting log markers (kit: LFDucati probe kit, not published). Seating the player from the
   > server produces crew without `HumanCommandVehicle` on client (skill `dayz-test-ingame` §SP-295): serves to measure pose on server, not to validate actions or HUD.
3. **What to look for in the RPT file (`server-profiles/` or `client-profiles/`)** [UNVERIFIED: message texts are illustrative, not measured; search by symbol]:
   - `Cannot load surface info` or `Undefined sound shader`: missing SoundSets or particles in `CfgSurfaces`.
   - `AnimationSource ... not found`: missing source registration in config `AnimationSources`.
   - `Bone 'drivewheel' not found`: missing bone in front fork of P3D model.
   - Spawn failure with uninitialized simulation: check if an `Axles` block was configured instead of `Wheels` (exact failure mode not measured).

## Status of this build (WIP Experimental 1.30.164014)

Work-in-progress aspects detected in Bohemia code that could change before Stable:
1. **Provisional unconsciousness ejection**: In `exp\scripts\scripts\4_World\Entities\DayZPlayerImplement.c:2452-2458`, motorbike tipover triggers `eModifiers.MDF_UNCONSCIOUSNESS` because the native ragdoll command was not finished in time. Bohemia is expected to replace this with a dedicated ragdoll command.
2. **Orphaned engine repair action**: `ActionRepairMotorbikeEngine.c` exists on disk, but is not inserted into `ActionConstructor.c:252-260` nor bound to hand tools. Only `ActionRepairMotorbikeEngineWithBlowtorch` operates via blowtorch.
3. **Undefined rvmat material properties**: `MotorbikeScript.c:114-122` registers selections whose material is read with `ConfigGetString` (`VehicleLightsComponent.c:77`) from properties such as `frontReflectorMatOn`, which `vehicles_singletrack\config.cpp` does not declare (cars do, e.g. `vehicles_wheeled\DZ\vehicles\wheeled\config.cpp:895`).
4. **Displaced audio definitions**: `exp\sounds_vehicles\DZ\sounds\vehicles\config.cpp` contains only `CfgPatches`. All motorbike SoundSets reside in `exp\sounds_hpp\DZ\sounds\hpp\config.cpp:98179-98909`, and their SoundShaders in `:59253-59918`.
5. **Alignment with 1.29 community guides**: Many vehicle modding guides assumed methods such as `CreateFrontLight`, `CarPartsHealthCheck`, or variables such as `data[0].impulse`. In 1.30 these signatures have been completely replaced or encapsulated (see [references/vehicle-1.30-refactor.md](references/vehicle-1.30-refactor.md)).
6. **Vehicle lights input vs headtorch**: `ActionSwitchLights` binds `UAToggleVehicleLights`, not `UAToggleHeadlight`. An `inputs.xml` declaring only `UAToggleHeadlight` will not switch off the headlight. See [references/actions-hud-lights-sounds.md](references/actions-hud-lights-sounds.md) §5.

## Cite-then-verify

Every technical claim in this skill includes the source file path and exact line range relative to extraction root `<extract-root>/1.30.164014/`.
- If you need to verify a citation, open the corresponding file at that exact line and check the symbol.
- Last full audit: 2026-09-19. All `file:line` citations, `[EXACT]` blocks (byte-for-byte identical), and `references/sources.md` counts were verified against the extraction; displaced citations and claims regarding contact damage, kickstand (DIAG only), default battery, `Jawa_05` clips, and sound ranges were corrected. Previous copies: `*.bak-20260919-pre-audit`. Still unverified: anything depending on native simulation (curve units, effect of `tipoverAngle`).
- When Bohemia publishes a new Experimental build or Stable version of DayZ 1.30, **DO NOT overwrite** the current extraction directory. Extract the new version into a sibling directory identified by its build number (for example `<extract-root>/1.30.XXXXXX/`), run a textual diff against `1.30.164014`, and update shifted line numbers.

## References Index

- [references/config-contract.md](references/config-contract.md): Open to copy literal [EXACT] `config.cpp` blocks (Crew, SimulationModule, DamageSystem, Wheels, AnimationSources, speedGeoms) and view the complete motorbike parameter table.
- [references/script-api.md](references/script-api.md): Open to view `proto native` signatures from `Motorbike.c`, stability callbacks, `MotorbikeScript` lifecycle, and differences from `CarScript`.
- [references/actions-hud-lights-sounds.md](references/actions-hud-lights-sounds.md): Open to implement or fix kickstart actions, ground pickup, `MotorBikeHud` instrumentation, light/horn components, and exact `sounds_hpp` SoundSets. Includes §5: `UAToggleVehicleLights` vs `UAToggleHeadlight`.
- [references/rider-animation.md](references/rider-animation.md): Open when configuring rider poses, handlebar IK, `Vehicles.agf` graph nodes (`MotorBikeSTM`), directional animations, or 3rd person camera.
- [references/vehicle-1.30-refactor.md](references/vehicle-1.30-refactor.md): Open when migrating a car mod from 1.29 to 1.30; contains deprecated method list, component migration, and 1.29 guide myth table.
- [references/forward-contract.md](references/forward-contract.md): Open for the full production checklist before packaging a new motorbike and to know what to measure on the P3D model.
- [references/sources.md](references/sources.md): Open to audit extracted sources, verify total line count of each cited file, and understand audio PBO layout.
- [references/vanilla-p3d-anatomy.md](references/vanilla-p3d-anatomy.md) (added 2026-09-19): Open for the REAL P3D/model.cfg anatomy of `Motorbike_01` and `Motorbike_02` read from ODOL v56 binaries — mass and center of mass, LODs with resolution and faces, skeleton with parents, all 44/60 animations with their source, angles and axes, LOD Memory points with coordinates, proxies, selections, and named properties. It is the parity benchmark for a new motorbike. `parsed` state: read its header before citing any number.

## WHAT THIS SKILL COULD NOT VERIFY

1. **Binary 3D models (`.p3d`)**: Exact face selections, memory points not cited in script, and collision LODs of `motorbike_01.p3d` and `motorbike_02.p3d` cannot be inspected in text; they must be measured with `dayz-p3d-audit` or P3D analysis tools.
   - (added 2026-09-19, LFDucati) **1.30 P3Ds are ODOL v56 (1.29 = v54) and the external ODOL->MLOD converter only reads v54**: today they CANNOT be measured without patching the reader; see the §Preflight of that skill (an unpublished reader patch is in progress). Verified via binary search in `Motorbike_01.p3d`: `drivewheel`, `damper_1`, `damperfront`, `kickstand`, `geotohide`, `pos_driver`, `light_1_1`, `refill`, and 49 `proxy:` names exist.
   - (added 2026-09-19; corrected 2026-09-19) **Corrected errata**: the Motorbike_02 column in table §6 of [references/config-contract.md](references/config-contract.md) (lines 512-535) had incorrect values (tipover, steering/lean tables, torque curve, idle, redline, ratios); it now matches `exp\vehicles_singletrack\DZ\vehicles\singletrack\config.cpp:736-738, 786, 791, 794, 806`. Motorbike_01 values were correct, but there were shifted line citations in both columns (Steering, torque, ratios, caster, and scripts), also corrected. Previous copy: `references/config-contract.md.bak-20260919`.
2. **Vanilla motorbike model.cfg file**: Not included in plain text inside extracted Bohemia PBOs. Bone names are only known when explicitly referenced in script (`"drivewheel"`).
3. **Internal C++ physics calculations**: The gyroscopic solver, internal stability algorithm, and Enfusion dynamic balance calculation reside compiled in `DayZDiag_x64.exe` and are not accessible via Enforce Script.
4. **In-game tuning of tyre lateral friction**: Wheel friction tables (`tyreLateralFriction`, `tyreLongitudinalFriction`) are verified in config, but grip feel on wet curves or gravel requires dynamic in-game testing.

FIN-SKILL-DRAFT

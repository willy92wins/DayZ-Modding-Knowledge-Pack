# Actions, HUD, Lights, and Sounds in Motorbikes

This document details all user actions specific to motorbikes in DayZ 1.30, the internal structure of `MotorBikeHud`, the lights/horn/VFX components, and the exact acoustic configuration extracted from `exp\sounds_hpp\DZ\sounds\hpp\config.cpp`.

---

## 1. Motorbike User Actions

### `ActionStartEngineMotorbike`
- **File**: `exp\scripts\scripts\4_World\Classes\UserActionsComponent\Actions\Continuous\Vehicles\ActionStartEngineMotorBike.c:9` (in-game `scripts\4_World\...\ActionStartEngineMotorBike.c`).
- **Type**: Continuous action (`ActionContinuousBase`), uses `ActionStartEngineMotorbikeCB` with `CAContinuousTime(UATimeSpent.START_ENGINE)`.
- **Condition (`ActionCondition`)**:
  - Player in `HumanCommandVehicle` (`line 28`).
  - Vehicle is `MotorbikeScript` and its engine is off (`if (!vehicle || vehicle.EngineIsOn())` returns `false`, `line 33`).
  - The player is the driver (`vehicle.CrewDriver() == player`, `line 36`).
- **Execution**:
  - In `OnExecute` (`lines 66-75`): invokes `vehicle.OnIgnition()` (`line 74`), which plays the kickstart sound with `HandleEngineSound(MotorbikeEngineSoundState.STARTING)` (`MotorbikeScript.c:1598-1620`, called at `1619`).
  - In `OnFinishProgress` (`lines 39-64`): invokes `vehicle.EngineStart()` (`line 63`). According to the comment at `line 51`, validation is performed by C++ via the `Motorbike.OnBeforeEngineStart()` callback.
- **Registration**: In `PlayerBase.c:1709` (`AddAction(ActionStartEngineMotorbike, InputActionMap);`) and in `ActionConstructor.c:223`.

### `ActionStopEngineMotorbike`
- **File**: `exp\scripts\scripts\4_World\Classes\UserActionsComponent\Actions\SingleUse\Vehicles\ActionStopEngineMotorBike.c:1`.
- **Type**: Single-use action (`ActionSingleUseBase`).
- **Condition**: Driver on `MotorbikeScript`, engine running (`vehicle.EngineIsOn()`), and absolute speed $\le 8$ km/h (`if (vehicle.GetSpeedometerAbsolute() > 8)` returns `false`, `line 29`). Cannot be manually turned off at high speed.
- **Registration**: In `PlayerBase.c:1712` and in `ActionConstructor.c:76`.

### `ActionPickUpMotorbike`
- **File**: `exp\scripts\scripts\4_World\Classes\UserActionsComponent\Actions\Interact\Vehicles\ActionPickUpMotorBike.c:1`.
- **Type**: Direct interaction (`ActionInteractBase`, `IsInstant() = true`).
- **Condition**: The object is `Motorbike`, player is not carrying a heavy item in hands (`!IsHeavyBehaviour()`), cursor does not point to a seat (`trans.CrewPositionIndex(componentIndex) < 0`), and the bike is fallen over and eligible to be picked up (`trans.CanPickUp()`, `line 64`).
- **Execution**: Invokes `trans.PickUp();` (`line 74`).
- **Registration**: In `MotorbikeScript.c:367`, on the side fairings of `Motorbike_02` (`exp\scripts\scripts\4_World\Entities\Core\Inherited\InventoryItem.c:499, 511, 539, 551`), and in `ActionConstructor.c:348`.

### `ActionAnimateMotorbikeSeat`
- **File**: `exp\scripts\scripts\4_World\Classes\UserActionsComponent\Actions\Interact\Vehicles\ActionAnimateMotorbikeSeat.c:1`.
- **Type**: `ActionAnimateSeats`.
- **Condition**: Seat without driver (`!bike.CrewMember(VEHICLESEAT_DRIVER)`), player closer than 1 meter, and selection belongs to animation source `"SeatDriver"`.
- **Registration**: In `Motorbike_01.c:104` (`AddAction(ActionAnimateMotorbikeSeat);`) and in `ActionConstructor.c:313`.

### Motorbike Repair Actions
| Action | File | Required tool | Target zone | Registration in ActionConstructor |
|---|---|---|---|---|
| `ActionRepairMotorbikeChassisWithBlowtorch` | `ActionRepairMotorbikeChassisWithBlowtorch.c:9` | `Blowtorch` (blowtorch with gas) | Chassis: damaged zone between `WORN` and `RUINED` (inherited condition, `ActionRepairMotorbikeChassis.c:31-47`) | Yes (`ActionConstructor.c:259`) |
| `ActionRepairMotorbikeChassis` | `ActionRepairMotorbikeChassis.c:1` | Base without vanilla tool | Chassis | Yes (`ActionConstructor.c:255`) |
| `ActionRepairMotorbikeEngineWithBlowtorch` | `ActionRepairMotorbikeEngineWithBlowtorch.c:9` | `Blowtorch` | Engine (`"Engine"`) | Yes (`ActionConstructor.c:260`) |
| `ActionRepairMotorbikeEngine` | `ActionRepairMotorbikeEngine.c:1` | Base (orphaned) | Engine | **NO** (vanilla omission in 1.30) |
| `ActionRepairMotorbikePartWithBlowTorch` | `ActionRepairMotorbikePartWithBlowTorch.c:9` | `Blowtorch` | Parts / fairings (`MotorbikePart`) | Yes (`ActionConstructor.c:253`) |
| `ActionRepairMotorbikePart` | `ActionRepairMotorbikePart.c:12` | Base | Parts / fairings | Yes (`ActionConstructor.c:252`) |

---

## 2. Vehicle HUD: `MotorBikeHud`

- **File**: `exp\scripts\scripts\5_Mission\GUI\Vehicles\MotorBikeHud.c:1-248` (in-game `scripts\5_Mission\GUI\Vehicles\MotorBikeHud.c`).
- **Inheritance**: `class MotorbikeHud : VehicleHudBase`.
- **Reused base layout**: `"gui/layouts/day_z_hud_cars.layout"` (`line 36`).
- **Entity binding**: `MotorbikeScript.c:316-319` returns `"VehicleTypeMotorbike"`, registered in `exp\scripts\scripts\5_Mission\GUI\IngameHud.c:183` (`m_VehicleHudMap.Insert("VehicleTypeMotorbike", motorbikeHud)`).
- **Active instrumentation (`RefreshVehicleHud`)**:
  - **RPM and Tachometer**: Reads `EngineGetRPM() / EngineGetRPMMax()` (`line 105`). The needle rotates with `rpm_value * 270 - 130` (`line 109`). Redline is calculated with `EngineGetRPMRedline() / EngineGetRPMMax()` (`line 106`).
  - **Speedometer**: Absolute speed divided by 200 for needle (`speed_value * 260 - 130`, `line 110`) and numeric text via `Math.AbsInt(GetSpeedometer()).ToString()` (`line 111`).
  - **Gears**: `UpdateGear()` queries `GetGear()` (`lines 217-237`). On manual transmission (`CarGearboxType.MANUAL`, `line 229`) it updates `Current`, `Prev`, and `Next` (`lines 231-236`) with the R/N/1-8 table built in `lines 77-88`.
  - **Fuel level**: Reads `GetFluidFraction(MotorbikeFluid.FUEL) * 260 - 130` (`line 204`).
  - **Engine light**: Queries `GetHealthLevel("Engine")`. Blinks if `HasEngineZoneReceivedHit()` is active (`lines 118-137`).
  - **Wheel lock**: Illuminates if `WheelIsAnyLocked()` returns `true` (`line 197`).
- **Visual differences compared to cars**:
  - Handbrake light **hidden**: `m_VehicleHandBrakeLight.Show(false);` (`line 196`).
  - Temperature indicator **hidden**: `m_VehicleTemperatureIndicator.Show(false);` because `IsVitalRadiator()` returns `false` (`lines 191-194`).

---

## 3. Modular Vehicle Components

### `VehicleLightsComponent` (`VehicleLightsComponent.c:1-190`)
- Allows registering rvmat material selections associated with light states:
  ```c
  m_LightsComponent.RegisterSelection("FrontOn", {new VehicleLightSelectionData(0, "frontReflectorMatOn")});
  m_LightsComponent.RegisterSelection("BrakeOn", {new VehicleLightSelectionData(1, "brakeReflectorMatOn")});
  ```
- Supports dedicated light profiles (`VehicleLightProfileBase`):
  - `Motorbike_01LightProfileFront`: brightness 2, radius 30m, angle 50º, RGB color `(0.85, 0.85, 0.68)`.
  - `Motorbike_01LightProfileRear`: brightness 4, radius 6m, angle 120º, RGB color `(0.95, 0.16, 0.05)`.
  - `Motorbike_02LightProfileFront`: brightness 3, radius 65m, angle 65º, RGB color `(0.85, 0.85, 0.68)`.
- Handlebar attachment:
  `int driveWheelIndex = GetBoneIndex("drivewheel");` and `m_LightsComponent.AttachLightOnObject("Front", GetMemoryPointPos(m_HeadLightPoint), vector.Zero, VehicleLightMode.SEGREGATED, driveWheelIndex);` (`MotorbikeScript.c:1107-1109`).

### `VehicleHornComponent` (`VehicleHornComponent.c:1-111`)
- Manages modes `OFF`, `SHORT`, `LONG`.
- On server triggers `GenerateHornAINoise` loading `NoiseCarHorn` from `config.cpp` (`strength = 30.0`).
- Synchronizes integer variable `m_HornComponent.m_Mode` over the network.

### `VehicleVFXComponent` (`VehicleVFXComponent.c:1-588`)
- Registers particles in `MotorbikeScript.c:174-205`:
  - `DUST_BEHIND` (`EffVehicleDust`) at `ConvertMemPointToPosition("engine")`.
  - `ENGINE_SMOKE` (`EffEngineSmoke`) at engine position.
  - `EXHAUST_SMOKE` (`EffExhaustSmoke`) oriented between `ptcExhaust_start` and `ptcExhaust_end`.
  - Wheel groups: `WHEEL_SMOKE` (`EffWheelSmoke`) and `WHEEL_CONTACT` (`EffWheelContact`).

---

## 4. Sound Configuration (`CfgSoundShaders` and `CfgSoundSets`)

Motorbike audio blocks are located in `exp\sounds_hpp\DZ\sounds\hpp\config.cpp` and cataloged in `work\soundsets-motorbike-1.30.txt`:

### Engine Shaders (RPM and Offload)
- `Motorbike_01_Engine_Ext_Rpm0_SoundShader` through `Rpm6_SoundShader` (`exp\sounds_hpp\DZ\sounds\hpp\config.cpp:59253-59324`): acceleration layers based on `rpm` and `thrust`.
- `Motorbike_01_Engine_Offload_Ext_Rpm1_SoundShader` through `Offload_Rpm6_SoundShader` (`config.cpp:59265-59330`): offload overrun layers upon releasing throttle.
- Equivalents in `Motorbike_02`: 8 acceleration layers (`Rpm0` to `Rpm7`) and 7 offload layers (`Offload_Rpm1` to `Offload_Rpm7`) (`config.cpp:59571-59660`).

### Primary SoundSets Registered in Script
- **Starting and stopping**:
  - `Motorbike_01_engine_start_SoundSet` (`config.cpp:98414-98420`) -> sample `\DZ\sounds\vehicles\Motorbike_01\engine_start`.
  - `Motorbike_01_engine_failed_start_fuel_SoundSet` (`config.cpp:98421`) -> `\DZ\sounds\vehicles\Motorbike_01\engine_failed_start_fuel`.
  - `Motorbike_01_engine_stop_SoundSet` (`config.cpp:98428`) -> `\DZ\sounds\vehicles\Motorbike_01\engine_stop`.
  - `Motorbike_01_engine_stop_fuel_SoundSet` (`config.cpp:98434`) -> `\DZ\sounds\vehicles\Motorbike_01\engine_stop_fuel`.
- **Kickstart**:
  - `Motorbike_01_Kickstart_FoldOut_SoundSet` (`config.cpp:98482`) -> lever fold out.
  - `Motorbike_01_Starting_Engine_Off_SoundSet` (`config.cpp:98486`) -> false kick sound.
- **Horn**:
  - `Motorbike_01_Horn_SoundSet` (`config.cpp:98517`): continuous loop (`loop = 1`).
  - `Motorbike_01_Horn_Short_SoundSet` (`config.cpp:98523`): short honk (`volumefactor = 0.8`).
  - `Motorbike_01_Horn_Start_SoundSet` and `Motorbike_01_Horn_End_SoundSet` (`config.cpp:98528-98537`).
- **Flip-up seat (`Motorbike_01`)**:
  - `Motorbike_01_Seat_FlipUp_SoundSet` and `Motorbike_01_Seat_FlipDown_SoundSet` (`Motorbike_01.c:119, 123`).
- **Shock Absorbers and Collision**:
  - `Motorbike_01_damper_front_SoundSet` and `Motorbike_01_damper_rear_SoundSet` (`config.cpp:98350, 98365`), both based on `Motorbike_01_damper_SoundShader` (`config.cpp:59458`), with 10 samples `motorbike_damper_01` through `motorbike_damper_10`.
  - `Motorbike_01_hit_character_SoundSet` and `Motorbike_01_hit_heavy_SoundSet` (`Motorbike_01.c:143, 150`).

## 5. Lights input: `UAToggleVehicleLights` versus `UAToggleHeadlight` (digest F, re-verified 2026-09-17 and 2026-09-19)

`ActionSwitchLights` (common to cars and motorbikes) uses the **vehicle** lights action, not the headtorch:

```c
// [EXACT] exp\scripts\scripts\4_World\Classes\UserActionsComponent\Actions\Interact\Vehicles\ActionSwitchLights.c:16-19
	override typename GetInputType()
	{
		return ToggleVehicleLightsActionInput;
	}
```

```c
// [EXACT] exp\scripts\scripts\4_World\Classes\UserActionsComponent\ActionInput.c:849-855
class ToggleVehicleLightsActionInput : DefaultActionInput
{
	ref ActionTarget targetNew;
	
	void ToggleVehicleLightsActionInput(PlayerBase player)
	{
		SetInput("UAToggleVehicleLights");
```

`ToggleLightsActionInput` still executes `SetInput("UAToggleHeadlight")` (`ActionInput.c:776-782`). Both names exist in `exp\bin\bin\constants.xml:90-91`. A custom `inputs.xml` that only assigns `UAToggleHeadlight` will turn on the headtorch, not the motorbike headlight. Horn aliases `CarHornShortActionInput : VehicleHornShortActionInput {}` (`ActionInput.c:757-758`) are empty compatibility shells with 1.29; register `ActionVehicleHornShort`/`Long` (`ActionConstructor.c:340-341`).

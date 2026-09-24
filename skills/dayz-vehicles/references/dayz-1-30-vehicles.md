# DayZ 1.30 Exp (build 1.30.164014) — vehicle script/config deltas

This atlas `SKILL.md` already carries a 2026-09-16 1.30 matrix (Motorbike sibling + component refactor). This file holds the rest of the 1.30 vehicle contract that does not fit in the 1896-line core: physics/VFX knobs, lights/horn/input migration, get-in gate changes, boats, wrecks, and `speedGeoms`. Every `[EXACT]` block was copied from `exp\` on 2026-09-17. Car/truck authoring that still talks about 1.29 (`CarLightBase`, `CreateFrontLight`, `ForceUpdateLightsStart`) is kept in the core and marked there.

Migration of a 1.29 *car* mod also lives in `dayz-motorbikes/references/vehicle-1.30-refactor.md`. Two-wheel work stays in `dayz-motorbikes`. Aviation that inherits `CarScript` → `dayz-aviation/references/dayz-1-30-aviation.md` in the aviation skill.

## What 1.30 changes (cars / trucks / boats)

| Topic | Until 1.29 | Since 1.30 Exp | Cite |
|---|---|---|---|
| Transport children | `Car` + `Boat` | third sibling `Motorbike` (`simulation = "motorbike"`) | `exp\bin\bin\config.cpp:1054-1059`, `Motorbike.c:30` |
| Headlights | subclass `CarLightBase` + `CreateFrontLight`/`CreateRearLight` | `VehicleLightBase` + `VehicleLightProfileBase` registered on `m_LightsComponent` | `VehicleLightBase.c:1`, `CivilianSedanFrontLight.c:1`, `Offroad_02.c:21-22` |
| Battery vital | `IsVitalCarBattery` / `IsVitalTruckBattery` | `NeedElectricitySourceDevice` / `GetElectricitySourceDevice` / `GetElectricitySourceDeviceType` | `Transport.c:821-833`, `CarScript.c:2811-2817` |
| Horn actions | `ActionCarHornShort`/`Long` | `ActionVehicleHornShort`/`Long`; `CarHorn*ActionInput` are empty aliases | `CarScript.c:2319-2320`, `ActionCarHorn.c:1,69-70,213-214`, `ActionInput.c:757-758` |
| Light toggle input | `UAToggleHeadlight` (`ToggleLightsActionInput`) | vehicle lights use `UAToggleVehicleLights` (`ToggleVehicleLightsActionInput`) | `ActionSwitchLights.c:16-18`, `ActionInput.c:776-782,849-855`, `bin\constants.xml:90-91` |
| Forced light refresh | `ForceUpdateLightsStart`/`End` | `[Obsolete("1.30: no replacement")]` — delete the calls | `CarScript.c:2805-2809` |
| Fluids | `CarFluid` / isolated `BoatFluid` | `enum ETransportFluid`; `BoatFluid : ETransportFluid {}` | `Transport.c:52-63`, `Boat.c:13` |
| Boat speedo | listed as Car-only | `Boat.GetSpeedometer` + `GetSpeedometerAbsolute` | `Boat.c:42-56` |
| Get-in | `IsAreaAtDoorFree` | `CanGetIn()` then `IsAreaAtDoorFreeDiag`; script **does** call `CanReachSeatFromDoors` | `ActionGetInTransport.c:36,54,64`, `Transport.c:672-675` |
| VFX scale | — | `GetWeightCoef()` (default 1.0) | `Transport.c:475-478` |
| Ganged rear bulbs | — | `HasGangedTailAndBrakeLights()` (default false) | `CarScript.c:468-471,2061-2094` |
| High-speed geom | changelog only | config `speedGeomActivation` + `speedGeoms[]` | `vehicles_singletrack\config.cpp:226-227`; changelog MODDING |
| Motorbike 3PP camera | — | `DAYZCAMERA_3RD_VEHICLE_MOTORBIKE = 32` | `DayZPlayerCameras.c:20,63` — detail in `dayz-motorbikes/references/rider-animation.md` |

## 1. Lights: `VehicleLightBase` + profiles (not `CarLightBase`)

(until 1.29: subclass `CarLightBase` / `CarRearLightBase` and override `CreateFrontLight`/`CreateRearLight`.)

(since 1.30 Exp:) `CreateFrontLight`/`CreateRearLight` are `[Obsolete("1.30: use VehicleLightsComponent instead")]` (`CarScript.c:2936-2948`). Vanilla `*FrontLight` classes stay on disk as obsolete wrappers:

```c
// [EXACT] exp\scripts\scripts\4_World\Entities\ScriptedLightBase\SpotLightBase\CarLightBase\CivilianSedanFrontLight.c:1-4
[Obsolete("use VehicleLightBase and VehicleLightProfileBase instead")]
class CivilianSedanFrontLight extends CarLightBase
{
	void CivilianSedanFrontLight()
```

The live light entity is `VehicleLightBase : SpotLightBase` (`VehicleLightBase.c:1`). Parameters live on `VehicleLightProfileBase` (`VehicleLightProfiles\VehicleLightProfileBase.c:1-14`). Register in the vehicle ctor:

```c
// [EXACT] exp\scripts\scripts\4_World\Entities\Vehicles\InheritedCars\Offroad_02.c:21-22
		m_LightsComponent.RegisterLight("Front", new VehicleLightData(new Offroad_02LightProfileFront()));
		m_LightsComponent.RegisterLight("Rear", new VehicleLightData(new Offroad_02LightProfileRear()));
```

`ActionSwitchLights` now uses `ToggleVehicleLightsActionInput` and `transport.LightToggle()`:

```c
// [EXACT] exp\scripts\scripts\4_World\Classes\UserActionsComponent\Actions\Interact\Vehicles\ActionSwitchLights.c:16-18
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

Headgear torches still bind `UAToggleHeadlight` (`ToggleLightsActionInput` at `ActionInput.c:776-782`). A custom car that `SetInput("UAToggleHeadlight")` for vehicle lights will not fire `ActionSwitchLights`.

[DESIGN] LEDs that are not vehicle headlights (bloom vs real light via `PointLightBase`) are unchanged; see `emissive-leds-and-dynamic-lights.md`.

## 2. Electricity: `NeedElectricitySourceDevice` (not `IsVital*Battery`)

```c
// [EXACT] exp\scripts\scripts\3_Game\Vehicles\Transport.c:821-833
	bool NeedElectricitySourceDevice()
	{
		return true;
	}
	
	EntityAI GetElectricitySourceDevice()
	{
		return null;
	}
	
	string GetElectricitySourceDeviceType()
	{
		return "";
	}
```

`ActionSwitchLights.ActionCondition` consults that trio (`ActionSwitchLights.c:38-46`). Vanilla Offroad_02:

```c
// [EXACT] exp\scripts\scripts\4_World\Entities\Vehicles\InheritedCars\Offroad_02.c:73-87
	override bool NeedElectricitySourceDevice()
	{
		return true;
	}
	
	override EntityAI GetElectricitySourceDevice()
	{
		super.GetElectricitySourceDevice();
		
		return GetInventory().FindAttachment(CarBattery.SLOT_ID);
	}
	
	override string GetElectricitySourceDeviceType()
	{
		return "CarBattery";
	}
```

Magneto/kickstart bikes override `NeedElectricitySourceDevice()` to `false` (`Motorbike_02.c:34-37`).

## 3. Horn

`CarScript.SetActions()` registers `ActionVehicleHornShort`/`Long` (`CarScript.c:2313-2321`). `ActionCarHornShort`/`Long` are `[Obsolete("replaced by ActionVehicleHornShort/Long")]` (`ActionCarHorn.c:69-70,213-214`). Empty aliases `CarHornShortActionInput : VehicleHornShortActionInput {}` (`ActionInput.c:757-758`) exist so old typenames still compile; logic lives on the VehicleHorn* parent. Register sounds on `m_HornComponent` in the ctor (`Offroad_02.c:33` pattern; trucks at `Truck_01_Base.c:25-26`).

## 4. `GetWeightCoef` and `HasGangedTailAndBrakeLights`

```c
// [EXACT] exp\scripts\scripts\3_Game\Vehicles\Transport.c:475-478
	float GetWeightCoef()
	{
		return 1.0;
	}
	
```

Vanilla overrides (verified): `Truck_01_Base` → `2.0` (`Truck_01_Base.c:120-123`); `Offroad_02` → `1.5` (`Offroad_02.c:133-136`); `Motorbike_01` → `0.5` (`Motorbike_01.c:87-90`); `Motorbike_02` → `0.75` (`Motorbike_02.c:77-80`). `CarScript` feeds the coef into VFX float modifiers (`CarScript.c:720,793`). Digest M claimed motorbikes return `0.25` from `MotorbikeScript.c:646`; that line *uses* `GetWeightCoef()`, it does not return 0.25.

```c
// [EXACT] exp\scripts\scripts\4_World\Entities\Vehicles\CarScript.c:468-471
	bool HasGangedTailAndBrakeLights()
	{
		return false;
	}
```

When true, reverse/position material swaps do not turn the brake selection off (`CarScript.c:2061-2094`). Offroad_02 and both vanilla bikes override to `true` (`Offroad_02.c:68-71`, `Motorbike_01.c:28` / `Motorbike_02.c:29`).

## 5. Get-in (1.30 condition)

(until 1.29: four gates ending at `IsAreaAtDoorFree` + a claim that script never calls `CanReachSeatFromDoors`.)

(since 1.30 Exp:) `ActionGetInTransport.ActionCondition` also requires `transport.CanGetIn()` (default `true` on `Transport`, `Transport.c:672-675`) and `IsAreaAtDoorFreeDiag(crewIndex)` (`ActionGetInTransport.c:36,54`). Gate 4 **is** invoked from script:

```c
// [EXACT] exp\scripts\scripts\4_World\Classes\UserActionsComponent\Actions\Interact\ActionGetInTransport.c:54-66
		if (!transport.CrewCanGetThrough(crewIndex) || !transport.IsAreaAtDoorFreeDiag(crewIndex))
			return false;
		
		array<string> selections = new array<string>();
		transport.GetActionComponentNameList(componentIndex, selections);
		int selectionCount = selections.Count();
		vector playerPosition = player.GetPosition();
		
		for (int i = 0; i < selectionCount; ++i)
		{
			if (transport.CanReachSeatFromDoors(selections[i], playerPosition, 1.0))
				return true;
		}
```

The 1 m third argument is therefore observable: vanilla script passes `1.0` (`ActionGetInTransport.c:64`). The 2026-09-07 "engine-native only" reading is false on this build. The measured LFQuad2 cost of changing `GetDoorConditionPointFromSelection` still stands as a 1.29 lesson.

## 6. Boats

```c
// [EXACT] exp\scripts\scripts\3_Game\Vehicles\Boat.c:12-13
//!	Type of vehicle's fluid. (native, do not change or extend)
enum BoatFluid : ETransportFluid {}
```

```c
// [EXACT] exp\scripts\scripts\3_Game\Vehicles\Boat.c:42-56
	//!	Returns the current speed of the vehicle in km/h.
	float GetSpeedometer()
	{
		vector transform[4];
		GetTransform(transform);

		float velocity = GetVelocity(this).InvMultiply3(transform)[2];
		return velocity * 3.6;
	}
	
	//! Returns the current speed of the vehicle in km/h. Value is absolute
	float GetSpeedometerAbsolute()
	{
		return Math.AbsFloat(GetSpeedometer());
	}
```

`BoatScript.GetHeatComfortOverride()` at `BoatScript.c:256-259`. Config AI noise `NoiseBoatEngine { strength = 30; }` at `exp\vehicles_water\DZ\vehicles\water\config.cpp:59-63`. `ActionFillFuel` talks to `Transport` via `ETransportFluid.FUEL` (digest M; re-verify that action file if you override fill).

## 7. `speedGeomActivation` / `speedGeoms`

[CHANGELOG] Official MODDING notes: hide named components when travelling at speed to prevent ground snags. Vanilla motorbikes:

```cpp
// [EXACT] exp\vehicles_singletrack\DZ\vehicles\singletrack\config.cpp:226-227
		speedGeomActivation = 0.29;
		speedGeoms[] = {"geotohide"};
```

`Motorbike_02` uses `0.27` (`config.cpp:729-730`). The C++ filter itself is not in Enforce [UNVERIFIED]. Cars/trucks in this extraction were not found declaring the pair [UNVERIFIED] — copy the motorbike pattern only if a high-speed geom snag is measured.

## 8. Wreck cisterns as `Well`

```c
// [EXACT] exp\scripts\scripts\4_World\Entities\Building\Wrecks\Wreck_Truck01_Aban1_Cistern.c:1-2
class Land_Wreck_Truck01_Aban1_Cistern : Well {}
class Land_Wreck_Truck01_Aban1_Cistern_DE : Land_Wreck_Truck01_Aban1_Cistern {}
```

`Land_Wreck_Truck01_Aban2_Cistern` is the same pattern (`Wreck_Truck01_Aban2_Cistern.c`). They drink as wells, not as vehicle wrecks.

Chinook / Mi24 wreck *scripts* exist (`Wreck_Chinook.c:1-24`, `Wreck_Mi24_TK.c:1-11`) with no matching `.p3d` in `structures_wrecks` listings this build — aviation-adjacent; see aviation 1.30 note.

## 9. Motorbike camera (pointer)

`DAYZCAMERA_3RD_VEHICLE_MOTORBIKE = 32` (`DayZPlayerCameras.c:20,63`); class `DayZPlayerCamera3rdPersonVehicleMotorbike` at `DayZPlayerCameraVehicles.c:239` with `CONST_SPRING_SMOOTHTIME_YAW = 0.5`, `CONST_YAW_LAG_REVERSE = 0.3`, `UP_ANGLE_CAP = 10` (`:243-258`). Do not duplicate that contract here — open `dayz-motorbikes/references/rider-animation.md` §2.

## 10. Line-number drift inside this atlas (1.29 cites)

These core SKILL.md cites were true on 1.29 and are displaced in 1.30 Exp (same symbols, new lines). Keep the old numbers as "(until 1.29)" and use:

| Symbol | until 1.29 (atlas) | since 1.30 Exp |
|---|---|---|
| `CarScript` ctor `SetEventMask(POSTSIMULATE/POSTFRAME)` | `carscript.c:325-326` | `CarScript.c:207-208` |
| `CarScript.EOnPostSimulate` | `carscript.c:948` | `CarScript.c:807` |
| `CarScript.OnDriverExit` gear-stop | `carscript.c:1207-1215` | `CarScript.c:940-948` |
| `Transport.OnDriverExit` empty body | `transport.c:161` | `Transport.c:224` |
| `ForceUpdateLightsStart`/`End` | `:535-536`, `:2981/:2990` | `[Obsolete]` at `CarScript.c:2805-2809`; no replacement |

## Migration checklist (1.29 car → 1.30 Exp)

1. Delete overrides of `CreateFrontLight` / `CreateRearLight` / `IsVitalCarBattery` / `IsVitalTruckBattery` / `CarPartsHealthCheck` / `ForceUpdateLightsStart`/`End`.
2. Instantiate / keep `m_LightsComponent`, `m_HornComponent`, `m_VFXComponent` (already constructed on `CarScript` in 1.30).
3. `RegisterLight("Front"|"Rear", new VehicleLightData(new YourProfile()))` and `RegisterSound(VehicleHornMode.SHORT/LONG, "...")`.
4. Override `NeedElectricitySourceDevice` + getters if the vehicle needs a battery; return false for magneto.
5. Bind vehicle light action to `UAToggleVehicleLights`, not `UAToggleHeadlight`.
6. `SetActions` / `AddAction(ActionVehicleHornShort/Long)` — not `ActionCarHorn*`.
7. Override `GetWeightCoef` if dust/exhaust scale is wrong; override `HasGangedTailAndBrakeLights` if brake+tail share a bulb.
8. If get-in vanished, implement `CanGetIn()` and check `IsAreaAtDoorFreeDiag` plus `CanReachSeatFromDoors` from the action.
9. Fluid fill uses `ETransportFluid` / `GetFluidCapacityScript` on `Transport`.
10. Re-verify every `carscript.c:NNNN` cite in this atlas against the 1.30 file before shipping.

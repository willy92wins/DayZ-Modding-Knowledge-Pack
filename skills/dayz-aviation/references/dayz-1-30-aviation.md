# DayZ 1.30 Exp (build 1.30.164014) — CarScript-as-aviation deltas

Digests F and M do not list `dayz-aviation` in SKILL IMPACT. This file is what 1.30 still changes for a plane/heli that **inherits `CarScript`**: the vehicle-light/horn/battery/event-mask contract moved under the aircraft. Native `HelicopterScript` remains a stub. Line numbers cited in the core SKILL.md against `P:\scripts\...\carscript.c` are 1.29; re-open `exp\scripts\scripts\4_World\Entities\Vehicles\CarScript.c` before copying them.

Compose with `dayz-vehicles/references/dayz-1-30-vehicles.md` for the car-side migration table.

## Native aviation class is still a stub

(until 1.29 and since 1.30 Exp: still true.) `HelicopterScript extends HelicopterAuto` registers only `POSTSIMULATE` and has an empty `EOnPostSimulate` plus empty engine hooks.

```c
// [EXACT] exp\scripts\scripts\4_World\Entities\Vehicles\HelicopterScript.c:4-13
class HelicopterScript extends HelicopterAuto
{
	void HelicopterScript()
	{
		SetEventMask(EntityEvent.POSTSIMULATE);
	}

	override void EOnPostSimulate(IEntity other, float timeSlice)
	{
	}
```

Do not inherit it expecting a flight model. CarScript-as-aviation stays the pattern.

## CarScript ctor / per-tick (line drift)

(until 1.29: SKILL.md cites `carscript.c:325-326` for `SetEventMask` and `:948` for `EOnPostSimulate`.)
(desde 1.30 Exp:)

```c
// [EXACT] exp\scripts\scripts\4_World\Entities\Vehicles\CarScript.c:207-208
		SetEventMask(EntityEvent.POSTSIMULATE);
		SetEventMask(EntityEvent.POSTFRAME);
```

`EOnPostSimulate` is at `CarScript.c:807`. `OnDriverExit` gear-stop is `CarScript.c:940-948` (was `:1207-1215`). Empty `Transport.OnDriverExit` is `Transport.c:224` (was `:161`).

## Lights, battery, ForceUpdateLights

A CarScript aircraft that still overrides `CreateFrontLight` / subclasses `CarLightBase` compiles against `[Obsolete]` but the override is not the 1.30 path. Vanilla cars register:

```c
// [EXACT] exp\scripts\scripts\4_World\Entities\Vehicles\InheritedCars\Offroad_02.c:21-22
		m_LightsComponent.RegisterLight("Front", new VehicleLightData(new Offroad_02LightProfileFront()));
		m_LightsComponent.RegisterLight("Rear", new VehicleLightData(new Offroad_02LightProfileRear()));
```

`ForceUpdateLightsStart`/`End` are `[Obsolete("1.30: no replacement")]` (`CarScript.c:2805-2809`). The SKILL.md parked-beam recipe that copies those two calls is a 1.29 pattern; delete the calls on 1.30.

Electricity: `NeedElectricitySourceDevice()` (`Transport.c:821`) replaces `IsVitalCarBattery`. Magneto aircraft can return false (vanilla bikes do: `Motorbike_02.c:34-37`).

Vehicle light toggle input is `UAToggleVehicleLights` (`ToggleVehicleLightsActionInput`, `ActionInput.c:849-855`), not `UAToggleHeadlight` (headgear). Custom flight `UA*` bindings are unchanged.

LM_Planes-style `class LM_TigermothFrontLight extends CarLightBase` in `effects-and-lights.md` is the 1.29 community pattern — keep it for existing mods; new 1.30 work uses `VehicleLightProfileBase` + `VehicleLightBase`.

## Wreck scripts without models

`StaticObj_Wreck_Chinook` (`Wreck_Chinook.c:1-24`) and `StaticObj_Wreck_Mi24_TK` (`Wreck_Mi24_TK.c:1-11`) exist in `scripts.pbo` and spawn a smoking particle when not dedicated. No matching `.p3d` in `work\pbo-listings` for `structures_wrecks` this build [UNVERIFIED] whether a later PBO will ship them. Do not config-depend on those classnames as placeable wrecks until a model listing exists.

## Migration checklist (CarScript aircraft)

1. Re-verify every `carscript.c:NNNN` / `transport.c:NNNN` cite in this skill against `exp\`.
2. Replace `CreateFrontLight`/`CreateRearLight` with `m_LightsComponent.RegisterLight` + a `VehicleLightProfile*` class.
3. Delete `ForceUpdateLightsStart`/`End`.
4. Override `NeedElectricitySourceDevice` (and getters) instead of `IsVitalCarBattery`.
5. Bind cockpit light toggle to `UAToggleVehicleLights` if it should use `ActionSwitchLights`.
6. Keep custom `UA*` flight axes; they are independent of the vehicle-light rename.
7. Do not switch the entity base to `HelicopterScript`.

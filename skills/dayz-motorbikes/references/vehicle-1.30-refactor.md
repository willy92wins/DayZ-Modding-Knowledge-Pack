# Vehicle Refactor in DayZ 1.30 (1.29 -> 1.30 Migration Guide)

This document details the internal restructuring of the vehicle system introduced in DayZ 1.30 Experimental (build 1.30.164014). It covers the modular decomposition of `CarScript`, the escalation of responsibilities to `Transport`, the adoption of specialized components, and the migration guide for existing car mods.

---

## 1. Responsibility Decomposition in CarScript and Transport

In DayZ 1.30, `CarScript.c` (-1155 / +877 lines) ceases to be a self-contained monolith:
- **Moved to `Transport.c` (+438 lines)**:
  - Unified fluids definition: `enum ETransportFluid` (`Transport.c:52-63`), from which `CarFluid`, `BoatFluid`, and `MotorbikeFluid` inherit.
  - Physics collision caching and handling: `m_ContactCache`, `m_MomentumPrevTick`, `m_VelocityPrevTick`, `m_dmgContactCoef`, `m_VehicleContactDamageCoef`, `m_CrewContactDamageCoef` (`Transport.c:90-96`).
  - Impact callback: `OnContact(...)` (`Transport.c:315`).
  - Electrical source detection: `NeedElectricitySourceDevice()`, `GetElectricitySourceDevice()`, `GetElectricitySourceDeviceType()` (`Transport.c:821-834`; default returns `true`, `null`, and `""`).
  - Vital parts check with callback: `CheckVitalItemCallback(...)` and virtual declaration `PartsHealthCheck()` (`Transport.c:420, 437`).
- **Moved to Modular Components (`exp\scripts\scripts\4_World\Entities\Vehicles\Components\`)**:
  - Lights and reflectors -> `VehicleLightsComponent`.
  - Horn and AI acoustic noise -> `VehicleHornComponent`.
  - Exhaust, radiator, and wheel dust particles -> `VehicleVFXComponent`.

---

## 2. Removed and Obsolete-Marked Methods

`CarScript.c` includes an explicit `//! DEPRECATED` section (`exp\scripts\scripts\4_World\Entities\Vehicles\CarScript.c:2760-2981`):

| Obsolete Method in 1.30 | Official Code Annotation | Corrective Action in Mod |
|---|---|---|
| `CreateFrontLight()` | `[Obsolete("1.30: use VehicleLightsComponent instead")]` | Register `VehicleLightProfileFront` in `m_LightsComponent`. |
| `CreateRearLight()` | `[Obsolete("1.30: use VehicleLightsComponent instead")]` | Register `VehicleLightProfileRear` in `m_LightsComponent`. |
| `IsVitalCarBattery()` | `[Obsolete("1.30: use Transport.NeedElectricitySourceDevice")]` | Override `NeedElectricitySourceDevice()` and return `true`. |
| `IsVitalTruckBattery()` | `[Obsolete("1.30: use Transport.NeedElectricitySourceDevice")]` | Override `NeedElectricitySourceDevice()` and return `true`. |
| `IsScriptedLightsOn()` | `[Obsolete("1.30: use Transport.LightIsOn")]` | Invoke `LightIsOn()`. |
| `CarPartsHealthCheck()` | `[Obsolete("1.30: use Transport::PartsHealthCheck instead")]` | Rename signature to `override protected void PartsHealthCheck()`. |
| `CheckVitalItem(bool, int)` | `[Obsolete("1.30: use Transport::CheckVitalItemCallback instead")]` | Use `CheckVitalItemCallback(...)`. |
| `OnBeforeSwitchLights()` | `[Obsolete("1.30: no replacement")]` | Remove prior logic; control is immediate in components. |
| `ForceUpdateLightsStart/End()` | `[Obsolete("1.30: no replacement")]` | Remove manual lights synchronization. |
| `BrakesRearLight()`, etc. | `[Obsolete("1.30: use VehicleLightsComponent instead")]` | Use `m_LightsComponent.SetLightTypeAndMode(...)`. |

---

## 3. New Tyre Physics Parameters in config.cpp

In DayZ 1.30, all car wheel classes (`HatchbackWheel`, `CivSedanWheel`, `Offroad_02_Wheel`, etc.) incorporate four new physical parameters, absent in `stable-1.29` (example in `HatchbackWheel`: `exp\vehicles_wheeled\DZ\vehicles\wheeled\config.cpp:745-751`):
- `tyreType = 0;`: Tyre type identifier.
- `tyreRoughness = 1.0;` (pristine) / `0.2;` (ruined): Ground surface roughness.
- `tyreLongitudinalFriction = 0.85 - 1.5;` (`2.5` in `Truck_01_WheelDouble`, `config.cpp:6152`): longitudinal grip during acceleration and braking. On ruined wheels it drops to `0.25 - 0.35`.
- `tyreLateralFriction = 0.95 - 1.8;` (`2.8` in `Truck_01_WheelDouble`, `config.cpp:6153`): lateral skid resistance. On ruined rims it rises to `4.95` across all wheels; that this mimics metal on asphalt is an interpretation [UNVERIFIED].

> **Cars only.** These ranges come from `vehicles_wheeled`; motorbike wheels (`exp\vehicles_singletrack\DZ\vehicles\singletrack\config.cpp`) do not follow them: `tyreType = 1` (`:165, 195, 542, 571`); pristine `tyreLateralFriction` 3.0-7.0 (`:171, 201, 547, 576`) and ruined 0.5 (`:183, 213, 558, 587`), meaning it drops when ruined rather than rising; pristine `tyreLongitudinalFriction` 0.85-1.8 (`:170, 200, 546, 575`) and ruined 0.5 (`:182, 212, 557, 586`); Motorbike_02 wheels do not declare `tyreRoughness` (`:531-588`). For a bike, start from `:155-214` (Motorbike_01) or `:531-588` (Motorbike_02).

---

## 4. Restructuring of Offroad_02 (Bohemia's Reference Example)

1. **Dual door selection (`hiddenSelections`)**:
   `Offroad_02` doors now differentiate exterior and interior panels:
   `hiddenSelections[] = {"texture_roof_ext","texture_roof_int"};` (`config.cpp:7106-7108`).
   The `Doors` damage zone includes dual `.rvmat` arrays in `RefTexsMats[]` and `healthLevels[]`.
2. **Front impact zone adjustment**:
   In `DamageZones -> Front`, `"dmgZone_bumper_1"` is removed (`work\diffs\configs\vehicles_wheeled.config.diff:319`); whether this is to avoid parasitic damage when hitting the bumper is an interpretation [UNVERIFIED].
3. **New beige variants**:
   `Offroad_02_Beige` and `_BeigeRust` parts are introduced (`config.cpp:7724, 7905`; they do not exist in 1.29).

---

## 5. Migration Checklist for a Car Mod from 1.29 to 1.30

Follow this step-by-step list to update an existing car:

- [EXACT] **Step 1: Remove obsolete light factories**:
  Delete any implementation of `override CarLightBase CreateFrontLight()` and `override CarRearLightBase CreateRearLight()`.
- [EXACT] **Step 2: Register lighting profiles**:
  Create your profile derived from `VehicleLightProfileFront` / `VehicleLightProfileRear` and register it in the vehicle constructor:
  ```c
  m_LightsComponent.RegisterLight("Front", new VehicleLightData(new MiCocheLightProfileFront()));
  m_LightsComponent.RegisterLight("Rear", new VehicleLightData(new MiCocheLightProfileRear()));
  ```
- [EXACT] **Step 3: Register horn in component**:
  In the constructor, replace `m_CarHornShortSoundName` with:
  ```c
  m_HornComponent.RegisterSound(VehicleHornMode.SHORT, "MiCoche_Horn_Short_SoundSet");
  m_HornComponent.RegisterSound(VehicleHornMode.LONG,  "MiCoche_Horn_Long_SoundSet");
  ```
- [EXACT] **Step 4: Update electrical supply**:
  Replace `IsVitalCarBattery()` and `IsVitalTruckBattery()` with the new `Transport` API:
  ```c
  override bool NeedElectricitySourceDevice() { return true; }
  override EntityAI GetElectricitySourceDevice() { return GetInventory().FindAttachment(CarBattery.SLOT_ID); }
  override string GetElectricitySourceDeviceType() { return "CarBattery"; }
  ```
- [EXACT] **Step 5: Rename signatures and collision data access**:
  - If you had `protected void CarPartsHealthCheck()`, change it to `override protected void PartsHealthCheck()`.
  - If you were reading `data[0].impulse`, update it to `data[0].m_Impulse`: it is a public member of `VehicleContactData` (`Transport.c:1144-1148`), and `CarContactData` remains as an empty subclass (`CarScript.c:53`).
- [EXACT] **Step 6: Update horn actions**:
  Verify that your vehicle actions register `ActionVehicleHornShort` and `ActionVehicleHornLong` instead of the legacy `ActionCarHorn*`.
- [DESIGN] **Step 7: Add modern friction in wheel config.cpp**:
  Ensure that your mod's wheels define `tyreRoughness`, `tyreLongitudinalFriction`, and `tyreLateralFriction`.

---

## 6. Claims in 1.29 Guides That Become False in 1.30

| Common claim in 1.29 guides | Reality in DayZ 1.30 Experimental | Evidence citation |
|---|---|---|
| *"To add lights to a car you must override `CreateFrontLight()` and create a `CarLightBase`"* | **FALSE**. Those methods are deprecated (`[Obsolete]`). The engine does not invoke them; you must create a `VehicleLightProfileBase` and register it in `m_LightsComponent`. | `CarScript.c:2937-2945` and `VehicleLightsComponent.c:61-64` |
| *"The horn is scripted with `SetCarHornState(ECarHornState)` and `ActionCarHorn`"* | **FALSE**. The `ActionCarHorn*` classes still exist, but marked `[Obsolete("replaced by ActionVehicleHornBase")]`, and cars now register `ActionVehicleHornShort/Long`. The horn is operated with `m_HornComponent.SetMode(VehicleHornMode)`. | `ActionCarHorn.c:1-2`, `CarScript.c:2319-2320`, and `VehicleHornComponent.c:41-53` |
| *"The battery is validated with `IsVitalCarBattery()`"* | **FALSE**. Obsolete method with no effect on starting. `Transport.NeedElectricitySourceDevice()` is consulted now. | `CarScript.c:2811-2817` and `Transport.c:821` |
| *"Engine parts checking is scripted in `CarPartsHealthCheck()`"* | **FALSE**. The signature was absorbed by `Transport.c` and renamed to `PartsHealthCheck()`. | `Transport.c:437`, `CarScript.c:2121`, and `CarScript.c:2976-2979` |
| *"Collision impulses are read in `data[0].impulse`"* | **FALSE**. The field is now `m_Impulse`, public, in the base class `VehicleContactData`; `CarContactData` is an empty subclass. No `impulse` member exists, so `.impulse` should not compile [UNVERIFIED: not compiled]. | `Transport.c:1144-1148` and `CarScript.c:53` |
| *"Exhaust smoke is controlled directly via `m_exhaustFx`"* | **FALSE**. Manual FX variables are obsolete. The entire particle pipeline is managed in `VehicleVFXComponent`. | `CarScript.c:477-478` (`m_VFXComponent.PlayEffect`) and `CarScript.c:2760, 2779` (`m_exhaustFx` remains in the `//! DEPRECATED` section) |
| *"Vehicle animation graphs are inaccessible `.agr` binary files"* | **FALSE**. In 1.30, `Vehicles.agf` is shipped as editable Enfusion structured text. (corrected 2026-09-28) It was already false in 1.29, so it is not a 1.29 truth that 1.30 broke: 1.29 ships the vehicle sub-graph as the text `Vehicles.agr` in the old `$AnimGraph 7` format, and 1.30 changed the syntax. | `Vehicles.agf:1-3655`; `stable-1.29\anims_workspaces\DZ\anims\workspaces\player\player_main\Vehicles.agr:1` |
| *"Bailing out while moving always uses the unique 8 km/h threshold of cars"* | **FALSE**. Dedicated thresholds exist: 8 km/h for cars, 5 km/h for boats, and 10 km/h for motorbikes (`MOTO_JUMPOUT_THRESHOLD`). | `ActionGetOutTransport.c:34-36` |

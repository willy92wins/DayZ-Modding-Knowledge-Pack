# DayZ Car — Complete config.cpp + model.cfg (verified worked example: Tyson89/Landrover)

> The biggest "build a DayZ car from scratch" gap that `vehicle-structural-parity.md` does NOT cover:
> the full **config.cpp** car class and the matching **model.cfg** (skeleton + animations). This file
> reproduces both end-to-end, anchored to a real working tutorial vehicle, the **Tyson89/Landrover**
> (a from-scratch drivable DayZ car), cross-checked against the official Bohemia DayZ wiki and a second
> real vehicle (Crocodoc QuadBike, debinarized in the vault).
>
> **Read order for a car:** (1) `vehicle-structural-parity.md` (Geometry/mass/CoM/inertia, wheel hubs,
> wheel-proxy Memory anatomy, ride-height — the model-structure invariants); (2) this file (config.cpp +
> model.cfg); (3) `vehicle-structural-parity.md` Addendum 2026-05-30b (per-LOD content + memory-point
> catalog + proxy placement). Mass is NOT set here — see §1.
>
> **Provenance labels** (R2 cite-then-verify): `[Landrover ✓]` = reproduced verbatim from the raw repo
> file, self-verified this session; `[DayZ-wiki ✓]` = verbatim from the official page, self-verified;
> `[Bohemia]` = Bohemia LOD/Oxygen2/Arma3-Cars wiki (sub-agent verbatim, cross-checked); `[QuadBike]` =
> real debinarized Crocodoc QuadBike values from the vault; `[TBD-verify]` = NOT verified, do not trust.
> `[UAZ ✓]` = DayZ-Expansion-Scripts UAZ `config.cpp`, curl-fetched raw + Read-tool verbatim (WebFetch's
> own summarizer paraphrases code even under explicit "verbatim" instruction — do not trust it for code
> quotes); `[vanilla-dump]` = `ravmustang/DayZ_SA_ClassName_Dump`, real extracted DayZ SA classes.
>
> Primary sources:
> - Landrover config.cpp: `https://raw.githubusercontent.com/Tyson89/Landrover/main/config.cpp`
> - Landrover model.cfg: `https://raw.githubusercontent.com/Tyson89/Landrover/main/Landrover.cfg`
> - Landrover wiki (tutorial): `https://github.com/Tyson89/Landrover/wiki` (+ `/config.cpp`, `/Object-Builder`, `/SimulationModule`)
> - Bohemia DayZ vehicle config: `https://community.bistudio.com/wiki/DayZ:Vehicle_Configuration`
> - QuadBike physics cheatsheet (vault): `AI/10_Projects/DayZ_Vehicle_Skill/skill-draft/references/carscript-cheatsheet.md`

## 1. The three files and what each OWNS (and where mass lives)

| File | Owns | Does NOT own |
|---|---|---|
| `.p3d` (Object Builder / py3d) | geometry, LODs, named selections, memory points, proxies, **mass + CoM (Geometry LOD vertex weights)** | physics params, animation values |
| `config.cpp` | the car class, drivetrain/engine/suspension numbers, crew, damage, lights, cargo, attachments, sound bindings, `AnimationSources` | mass, CoM, the animation geometry (axes) |
| `model.cfg` | `CfgSkeletons` (bone hierarchy) + `CfgModels` `Animations` (how each bone moves) | physics, which sources are user-driven |

**Mass is NOT in config.cpp.** `[DayZ-wiki ✓]` "Every component's vertex should have weight assigned.
From these weights the total mass of vehicle and its center of mass is computed." The Landrover and the
QuadBike configs contain **no** `mass`, `centerOfMass`, `sprungMass`, or `geometryClass` field — both
inherit those from `CarScript` and take mass/CoM from the Geometry LOD. See `vehicle-structural-parity.md`
Addendum 2026-05-30 for assigning that mass. `sprungMass` is an **Arma-3** concept ("The sum of sprungMass
values for all Wheels must be equal to the vehicle's weight", `Arma_3_Cars_Config_Guidelines`); it does not
appear in either DayZ config — `[TBD-verify]` whether DayZ CarScript honors it at all.

## 2. The car class skeleton

A drivable DayZ car extends **`CarScript`**. Pattern: a `scope=0` base (`model=""` or the real model) that
holds all physics, then `scope=2` concrete variants. `[Landrover ✓]` ships base + one variant:

```cpp
class Carscript;                       // forward-declare the parent (NOTE casing below)
class Landrover_Base: Carscript
{
    scope = 0;
    displayname = "Landrover Base";
    Model = "\Landrover\Landrover.p3d";
    // ... hiddenSelections, attachments, Crew, SimulationModule, DamageSystem, AnimationSources, Sounds ...
};
class Landrover: Landrover_Base { scope = 2; };
```

**Casing gotcha:** the Landrover repo writes `Carscript` (lowercase s); the QuadBike writes `CarScript`.
DayZ config class-name resolution is **case-insensitive**, so both inherit correctly. Canonical vanilla
name is `CarScript`. The class name does NOT have to match the .p3d filename for a vehicle (unlike a
static `Inventory_Base`); the link is the `Model=` path.

## 3. SimulationModule — the physics core (reproduce, then tune)

`[DayZ-wiki ✓]` "SimulationModule class contains car's controls properties, engine and drivetrain
configuration." Complete, working block, `[Landrover ✓]` (AWD, ~Land-Rover-110 mass class):

```cpp
class SimulationModule
{
    drive = "DRIVE_AWD";                    // DRIVE_RWD | DRIVE_FWD | DRIVE_AWD (case-sensitive, defines feel)
    class Steering
    {
        maxSteeringAngle = 35;              // max wheel turn in degrees
        increaseSpeed[]  = {0,45, 60,25, 100,15};   // {km/h, deg/s} pairs — slower steer at speed
        decreaseSpeed[]  = {0,90, 60,45, 100,15};   // counter-steer speed
        centeringSpeed[] = {0,0, 15,28, 60,45, 100,60};
    };
    class Throttle
    {
        reactionTime = 0.25;               // s to reach wanted thrust
        defaultThrust = 0.8; gentleThrust = 0.6;
        turboCoef = 5; gentleCoef = 0.7;
    };
    class Brake
    {
        pressureBySpeed[] = {0,0.85, 10,0.7, 20,0.5, 40,0.4, 60,0.43, 80,0.46, 100,0.52, 120,0.7};
        reactionTime = 0.25; driverless = 0.1;   // driverless = brake applied with no driver, [0,1]
    };
    class Aerodynamics { frontalArea = 2.18; dragCoefficient = 0.65; };   // drag sets top speed
    class Engine
    {
        torqueCurve[] = {650,0, 850,110, 1200,150, 2500,200, 4350,160, 7300,0};  // {rpm, Nm} pairs
        inertia = 0.5; frictionTorque = 160; rollingFriction = 0.5; viscousFriction = 0.5;
        rpmIdle = 800; rpmMin = 850; rpmClutch = 1450; rpmRedline = 6150;
    };
    class Clutch { maxTorqueTransfer = 440; uncoupleTime = 0.1; coupleTime = 0.1; };
    class Gearbox { type = "GEARBOX_MANUAL"; reverse = 3.91; ratios[] = {3.6,3.0,2.3,1.45,1.0}; };
    class CentralDifferential { ratio = 1.5; type = "DIFFERENTIAL_LOCKED"; };   // only for AWD/642
    class Axles
    {
        class Front
        {
            maxBrakeTorque = 3500; maxHandbrakeTorque = 4000;
            wheelHubMass = 15;          // KG, only used while NO wheel is attached
            wheelHubRadius = 0.284;     // radius of the HUB component (Shift+E on hub, axis Y) — never negative
            class Differential { ratio = 4.0; type = "DIFFERENTIAL_OPEN"; };
            class Suspension { stiffness = 40000; compression = 2100; damping = 5400; travelMaxUp = 0.10; travelMaxDown = 0.06; };
            class Wheels
            {
                class Left  { animTurn="turnfrontleft";  animRotation="wheelfrontleft";  wheelHub="wheel_1_1_damper_land"; animDamper="damper_1_1"; inventorySlot="Landrover_Wheel_1_1"; };
                class Right { animTurn="turnfrontright"; animRotation="wheelfrontright"; wheelHub="wheel_2_1_damper_land"; animDamper="damper_2_1"; inventorySlot="Landrover_Wheel_2_1"; };
            };
        };
        class Rear
        {
            maxBrakeTorque = 1750; maxHandbrakeTorque = 4000;
            wheelHubMass = 15; wheelHubRadius = 0.284;
            class Differential { ratio = 4.0; type = "DIFFERENTIAL_OPEN"; };
            class Suspension { stiffness = 40000; compression = 2100; damping = 5400; travelMaxUp = 0.10; travelMaxDown = 0.06; };
            class Wheels
            {
                class Left  { animTurn="turnbackleft";   animRotation="wheelbackleft";   wheelHub="wheel_1_2_damper_land"; animDamper="damper_1_2"; inventorySlot="Landrover_Wheel_1_2"; };
                class Right { animTurn="turnbacktright";  animRotation="wheelbackright";  wheelHub="wheel_2_2_damper_land"; animDamper="damper_2_2"; inventorySlot="Landrover_Wheel_2_2"; };
            };
        };
    };
};
```
(`animTurn="turnbacktright"` on rear-right is a typo IN the source — `turnbacktright` has an extra `t`.
The QuadBike has the identical typo. Harmless: rear wheels don't steer. Use `turnbackright` in new work.)

### What the wheel fields wire to
- `wheelHub` = the name of the wheel-hub **memory point / land-contact** in the .p3d (`wheel_X_Y_damper_land`).
- `animTurn` / `animRotation` / `animDamper` = **model.cfg animation SOURCE names** (see §11–13). Front
  wheels set `animTurn` (they steer); rear wheels still list it but it does nothing.
- `inventorySlot` = the wheel item slot (see §8).

### Parameter semantics (official) `[DayZ-wiki ✓]`
| class | key fields | meaning (verbatim where quoted) |
|---|---|---|
| `Steering` | `maxSteeringAngle`, `increaseSpeed[]`/`decreaseSpeed[]`/`centeringSpeed[]` | "Every point of the curve determines how fast the steering wheel rotates based on vehicle speed." `{km/h, deg/s}` pairs. |
| `Throttle` | `defaultThrust`,`gentleThrust`,`turboCoef`,`gentleCoef`,`reactionTime` | gentle/default/turbo pedal-pressure modes |
| `Brake` | `pressureBySpeed[]`,`reactionTime`,`driverless` | `reactionTime` = "how long it takes to floor the brake pedal"; `driverless` ∈ [0,1] |
| `Aerodynamics` | `frontalArea`,`dragCoefficient`,(`downforceCoefficient`,`downforceOffset`) | "frontal drag practically determines maximal forward speed". Negative drag forbidden. |
| `Engine` | `torqueCurve[]` `{rpm,Nm}`, `inertia`, `rpmIdle/Min/Clutch/Redline` | "DayZ allows users to manually insert its torque curve". `inertia` is the real field — `engineMomentum` does NOT exist `[QuadBike]`. |
| `Clutch` | `maxTorqueTransfer`,`uncoupleTime`,`coupleTime` | "Maximal torque in Nm that the clutch can transfer before it starts to slip." |
| `Gearbox` | `type` (`GEARBOX_MANUAL`/`GEARBOX_AUTOMATIC`), `reverse`, `ratios[]` | one reverse ratio + N forward ratios |
| `CentralDifferential` | `ratio`, `type` (`DIFFERENTIAL_LOCKED`/`_OPEN`) | "Valid only for AWD and 642 drivetrains." |

### Suspension tuning — calibrate to mass (don't copy blindly)
Formula (starting points, then adjust) `[Landrover SimulationModule wiki]`: `compression = stiffness/10`,
`damping = compression*3`; stiffness sized so it "needs to overcome the Kilogram that is going down by the
force of gravity." Two real reference points for a 4-wheeler:

| | Landrover (AWD) `[Landrover ✓]` | QuadBike (FWD) `[QuadBike]` |
|---|---|---|
| Front stiffness / compression / damping | 40000 / 2100 / 5400 | 41000 / 2100 / 7200 |
| Front travelMaxUp / travelMaxDown | 0.10 / 0.06 | 0.293 / 0.051 |
| Rear stiffness / comp / damp | 40000 / 2100 / 5400 | 40000 / 2000 / 7000 |
| Rear travelMaxUp / travelMaxDown | 0.10 / 0.06 | 0.414 / 0.012 |
| drive / front diff | DRIVE_AWD / OPEN 4.0 | DRIVE_FWD / LOCKED 4.1 |

Trap (documented): mass too LOW + stiffness copied from a heavier vehicle → catapult. Suspension is
**not** the spawn-bounce trigger — but neither is the monolithic Geometry (the 2026-05-30 hypothesis,
refuted twice: `vehicle-structural-parity.md` Correction 2026-06-01 and 2026-06-02). Confirmed
spawn-bounce causes: chassis Geometry overlapping the wheel volume, spawn placement, and a stray `#Mass#`
tag on a non-Geometry LOD (FireGeo) baking CoM=(0,0,0).

## 4. Crew (driver / co-driver / cargo)

`[DayZ-wiki ✓]` property table:

| property | type | description (verbatim) |
|---|---|---|
| `actionSel` | string | "Name of the named selection(s) in view or fire geometry LOD of the model. This selection is used as entry point for user action." |
| `proxyPos` | string | "Name of the named proxy selection in view geometry LOD of the model. This proxy is used as position where to put player inside car. This proxy has to have defined bone inside skeleton config of the car." |
| `getInPos` | string | "Name of the selection point from which player gets in/out the car." |
| `getInDir` | string | "Name of the selection of second point serving as direction from the first one." |
| `isDriver` | boolean | "Indicates if this crew position serves for driver. There can be max. one driver position at the time." |

`[Landrover ✓]` (driver, co-driver + 6 cargo). `proxyPos` names a **proxy object in ViewGeometry** (and
FireGeometry) AND a **bone in `CfgSkeletons`** — both are required or get-in breaks (see
`vehicle-structural-parity.md` "Crew proxies", the #1 post-spawn gotcha):

```cpp
class Crew
{
    class Driver   { actionSel="seat_driver";   proxyPos="CrewDriver";   getInPos="pos_driver";   getInDir="pos_driver_dir";   isDriver=1; };
    class CoDriver { actionSel="seat_codriver"; proxyPos="CrewCoDriver"; getInPos="pos_codriver"; getInDir="pos_codriver_dir"; };
    class Cargo1   { actionSel="seat_cargo1";   proxyPos="CrewCargo1";   getInPos="pos_cargo";    getInDir="pos_cargo_dir"; };
    // Cargo2..Cargo6 identical, incrementing the index; all cargo share pos_cargo/pos_cargo_dir here
};
```
(`isDriver=1` and `isDriver=true` are equivalent.)

**Nailing `crewDriver`/`pos_driver` BEFORE baking (offline fit editor).** Crew memory points are baked into the
Memory LOD — they cannot be nudged in-game without a rebuild, so a wrong seat costs a full build cycle per guess.
LFQuad's cheap fix: a throwaway offline HTML editor (sliders for `crewDriver` X/Y/Z/yaw + `pos_driver` X/Y/Z, a
~1.8 m seated mannequin, the handlebar/wheel grips as fixed markers, a live coord readout) to align pelvis↔seat
and hands↔grips, then copy the final coords into the assemble script's `extra_mem`. Seed its defaults from a
working reference's real points (debinarize the donor's Memory LOD). This is the no-MCP counterpart to the
headless crew-probe (`vehicle-structural-parity.md`): the editor *places* the seat offline; the probe *verifies*
the ViewGeo seat cube is raycast-collidable. (LFQuad 2026-05-23.)

## 5. Lights (selections + reflector material on/off)

Two halves: (a) the glowing headlight **mesh faces** are `hiddenSelections` swapped to a lights `.rvmat`;
(b) named `*ReflectorMatOn/Off` properties tell `CarScript` which material to swap when lights toggle.
The **light beam** itself is placed at Memory points (`light_left`,`light_left_dir`,`light_right`,
`light_right_dir`, `reflector_1_1`, `reflector_2_1`). `[Landrover ✓]`:

```cpp
hiddenSelections[]={ "light_left","light_right","light_brake_1_2","light_brake_2_2",
    "light_reverse_1_2","light_reverse_2_2","light_1_2","light_2_2","light_dashboard","base","special" };
hiddenSelectionsTextures[]={ "","","","","","","","","", "Landrover\data\lr_base_acr_co.paa","Landrover\data\lr_special_acr_co.paa" };
hiddenSelectionsMaterials[]={ "","","","","","","","","", "Landrover\data\lr_base.rvmat","Landrover\data\lr_special.rvmat" };

frontReflectorMatOn  ="Landrover\data\landrover_front_lights_on.rvmat";   frontReflectorMatOff ="Landrover\data\lr_base.rvmat";
brakeReflectorMatOn  ="Landrover\data\landrover_brake_lights_on.rvmat";   brakeReflectorMatOff ="Landrover\data\lr_base.rvmat";
TailReflectorMatOn   ="Landrover\data\landrover110_tail_lights_on.rvmat"; TailReflectorMatOff  ="Landrover\data\lr_base.rvmat";
ReverseReflectorMatOn="Landrover\data\landrover_reverse_lights_on.rvmat"; ReverseReflectorMatOff="Landrover\data\lr_base.rvmat";
dashboardMatOn       ="Landrover\data\landrover_dashboard_lights_on.rvmat"; dashboardMatOff    ="Landrover\data\lr_base.rvmat";
```
The `_on.rvmat` is an **emissive** material (see `config-and-packing.md` emissive section); the `_off` is
the plain body material. Without the selections + memory points + these properties, headlights mount but
never illuminate (`vehicle-structural-parity.md` "Lights").

## 6. DamageSystem / DamageZones

`class DamageSystem { class GlobalHealth { class Health { hitpoints; healthLevels[] } } class DamageZones { ... } }`.
Each zone maps to a `dmgZone_*` selection (in FireGeometry/Hitpoints + Memory) via `componentNames[]`/
`memoryPoints[]`, and can cascade damage to other zones (`transferToZonesNames[]`/`Coefs[]`) or to attached
items (`inventorySlots[]`/`Coefs[]`). `[Landrover ✓]` full zone set: **Chassis, Front, Back, Roof,
Fender_1_1/2_1/1_2/2_2, WindowFront, Engine, FuelTank, Reflector_1_1/2_1** (door/window zones live on the
`CarDoor` item classes, §8). Two zones verbatim; the rest follow the same shape:

```cpp
class DamageSystem
{
    class GlobalHealth { class Health { hitpoints=2500; healthLevels[]={ {1.0,{}},{0.7,{}},{0.5,{}},{0.3,{}},{0.0,{}} }; }; };
    class DamageZones
    {
        class Chassis
        {
            class Health { hitpoints=2500; transferToGlobalCoef=0; };
            displayName="$STR_CfgVehicleDmg_Chassis0";
            memoryPoints[]={"dmgZone_chassis"};  componentNames[]={"dmgZone_chassis"};
            fatalInjuryCoef=-1;  inventorySlots[]={};
        };
        class Front
        {
            class Health { hitpoints=2500; transferToGlobalCoef=0;
                healthLevels[]={ {1.0,{"Landrover\data\lr_base.rvmat","Landrover\data\lr_special.rvmat"}},
                                 {0.7,{...}},{0.5,{"...lr_base_damage.rvmat",...}},{0.3,{...}},{0.0,{"...lr_base_destruct.rvmat",...}} }; };
            displayName="$STR_CfgVehicleDmg_Bumper0";
            transferToZonesNames[]={"Reflector_1_1","Reflector_2_1","Fender_1_1","Fender_2_1","Engine"};
            transferToZonesCoefs[]={0.1,0.1,0.1,0.1,0.15};
            memoryPoints[]={"dmgZone_front"};  componentNames[]={"dmgZone_front"};
            inventorySlots[]={"Landrover_Hood","CarRadiator","Landrover_Wheel_1_1","Landrover_Wheel_2_1"};
            inventorySlotsCoefs[]={0.3,0.25,0.1,0.1};
        };
        // Back, Roof(dmgZone_tarp), Fender_*, WindowFront, Engine(fatalInjuryCoef=0.001), FuelTank, Reflector_* ...
    };
};
```
`healthLevels[]` has 5 thresholds (1.0/0.7/0.5/0.3/0.0); each supplies the `.rvmat` array to swap at that
damage level (empty `{}` = no visual change). `"hidden"` instead of an rvmat array hides the selection at
that level (glass). Every `dmgZone_*` in `componentNames[]` MUST exist as a selection in the model
(FireGeometry component + Hitpoints/Memory). Without DamageZones + FireGeometry components there is no
localized damage.

## 6b. Window / Glass damage (added 2026-07-07, cross-confirmed 3 real configs)

Breakable glass is **not** a separate system — it is the same `DamageZones` + `healthLevels[]` rvmat-swap
mechanism as any body panel (§6 above), applied to a window-named zone. All 3 independent real configs
checked converge on the same shape (intact → intact/no-change → damage rvmat → destruct rvmat → `"hidden"`):

| Source | Zone | hitpoints | final state |
|---|---|---|---|
| `[Landrover ✓]` | `WindowFront` (body) | 200 | `"hidden"` |
| `[UAZ ✓]` | `Window` (per door) | 500 | `"hidden"` |
| `[UAZ ✓]` | `WindowFront` (body) | 800 | `"hidden"` |
| `[vanilla-dump]` OffroadHatchback/Niva | `WindowFront` | 120 (StarDZ tutorial cites 150 for the same zone type — unresolved, `[TBD-verify]`) | `"hidden"` |

`[UAZ ✓]` verbatim:
```cpp
class Window
{
    class Health
    {
        hitpoints=500;
        healthLevels[]=
        {
            {1,   {"dz\vehicles\wheeled\hatchback_02\data\hatchback_02_windows.rvmat"}},
            {0.7, {"dz\vehicles\wheeled\hatchback_02\data\hatchback_02_windows.rvmat"}},
            {0.5, {"dz\vehicles\wheeled\hatchback_02\data\glass_i_damage.rvmat"}},
            {0.3, {"dz\vehicles\wheeled\hatchback_02\data\glass_i_damage.rvmat"}},
            {0,   "hidden"}
        };
    };
    fatalInjuryCoef=-1; transferToGlobalCoef=0;
    componentNames[]={"dmgZone_doorwindowLeft"};
};
```
Reuses the **vanilla Hatchback_02** glass rvmats directly instead of authoring new damage textures — a
legitimate shortcut when the vanilla crack/shatter look is acceptable.

**Naming convention**: English, `dmgZone_*` pattern (e.g. `dmgZone_windowFront`, `dmgZone_doorwindowLeft`)
— NOT the Czech legacy names (`sklo predni L/P`) from 2008-era Arma1/OFP glass tutorials. Those describe a
different, older pipeline (convex glass hull duplicated into Fire Geometry LOD, Hit-points LOD vertex per
opening) that does not apply to DayZ SA's config-driven DamageZones system — do not follow it.

**`[TBD-verify]` — genuinely open, do not guess:**
- The exact "correct" `hitpoints` value varies 120-800 across real sources — calibrate per-vehicle, don't
  treat any single number as canonical.
- The `.p3d`-side authoring process: which LOD the `dmgZone_window*` selection must live in, how to paint
  it in Object Builder / Blender. No DayZ SA-specific source found for this step this session — recommend
  debinarizing a vanilla car with glass (`civiliansedan`) via the parity-first method and inspecting its
  selection directly, rather than guessing from the Arma-era tutorials.
- Whether `"hidden"` at 0 HP also removes FireGeometry/collision or only the visual — an unconfirmed
  Bohemia feedback ticket (T141571, 403'd on fetch) suggests it may not always hide geometry. Test
  in-game: does a "shattered" window still block bullets/vision like solid glass?

Sources: Tyson89/Landrover `config.cpp` (curl-fetch verbatim 2026-07-07); DayZ-Expansion-Scripts UAZ
`config.cpp`, raw.githubusercontent.com (curl-fetch verbatim 2026-07-07); `ravmustang/DayZ_SA_ClassName_Dump`
`vehicles_wheeled/config.cpp`; StarDZ Modding Wiki vehicle-mod tutorial (hitpoints discrepancy source).

## 7. Attachments, Cargo, fuel, GUI groups

`[Landrover ✓]`:

```cpp
fuelCapacity=65; fuelConsumption=15;
attachments[]={ "CarBattery","Reflector_1_1","Reflector_2_1","CarRadiator","SparkPlug",
    "Landrover_Driver_Door","Landrover_CoDriver_Door","Landrover_Hood","Landrover_Trunk",
    "Landrover_Wheel_1_1","Landrover_Wheel_1_2","Landrover_Wheel_2_1","Landrover_Wheel_2_2","Landrover_Sparewheel" };
class Cargo { itemsCargoSize[]={10,50}; allowOwnedCargoManipulation=1; openable=0; };
class GUIInventoryAttachmentsProps
{
    class Engine  { name="$STR_attachment_Engine0";  icon="set:dayz_inventory image:cat_vehicle_engine";  attachmentSlots[]={"CarBattery","CarRadiator","SparkPlug"}; };
    class Body    { name="$STR_attachment_Body0";    icon="set:dayz_inventory image:cat_vehicle_body";    attachmentSlots[]={"Reflector_1_1","Reflector_2_1","Landrover_Driver_Door","Landrover_CoDriver_Door","Landrover_Hood","Landrover_Trunk","Landrover_Sparewheel"}; };
    class Chassis { name="$STR_attachment_Chassis0"; icon="set:dayz_inventory image:cat_vehicle_chassis"; attachmentSlots[]={"Landrover_Wheel_1_1","Landrover_Wheel_1_2","Landrover_Wheel_2_1","Landrover_Wheel_2_2"}; };
};
```
`CarBattery` + `SparkPlug` (+ `CarRadiator`) are vanilla engine-part slots **required for the engine to
start** — see §15. Vanilla leaves BOTH `IsVitalSparkPlug` and `IsVitalGlowPlug` true by default, so a
petrol car must `override IsVitalGlowPlug()→false` (`civiliansedan.c:363`) or it silently also demands a
GlowPlug it has no slot for (the bug that bit SUB_BRZ). `ObstacleGenerator { class Shapes { class Cylindric {...} } }` (in the Landrover) carves
the road-block volume; optional.

## 8. Wheels & doors as ITEMS + slot/proxy wiring

A car's wheels and doors are **separate item entities** attached into slots. Three pieces wire each one:
the item class, the slot, and (for the rendered-while-attached visual) the proxy.

### a) Wheel item — `class <Wheel>: CarWheel` `[Landrover ✓]`
```cpp
class CarWheel;
class Landrover_Wheel: CarWheel
{
    scope=2; displayName="Landrover Wheel"; model="\Landrover\proxy\Landrover_Wheel.p3d"; weight=15000;
    inventorySlot[]={"Landrover_Wheel_1_1","Landrover_Wheel_1_2","Landrover_Wheel_2_1","Landrover_Wheel_2_2","Landrover_Sparewheel"};
    radius=0.451; width=0.142;                          // tire radius/width (drives the visual + ground contact)
    radiusByDamage[]={0,0.451, 0.3,0.3, 0.9998,0.25, 0.9999,0.2};
    tyreOffroadResistance=0.75; tyreGrip=0.8; tyreRollResistance=0.015;
    rotationFlags=8; repairableWithKits[]={6}; repairCosts[]={30};
    class DamageSystem { class GlobalHealth { class Health { hitpoints=400; healthLevels[]={...} }; }; };
};
class Landrover_Wheel_Ruined: CarWheel { /* radius=0.2; width=0.107; tyreGrip=0.2; the destroyed variant */ };
```
`tyreGrip`/`tyreRollResistance` are the "feel" knobs: QuadBike `tyreGrip=2.8`+`tyreRollResistance=0.015`
("glued to ground") vs Landrover `0.8`/`0.015` `[QuadBike]`. **`radius` here must agree with the wheel
proxy .p3d Memory anatomy** (`vehicle-structural-parity.md` Addendum 2026-05-29) or `contact=0`.

### b) Slot registration — `class CfgSlots` `[QuadBike]`
Custom wheel slots are registered once (vanilla slots like `CarBattery` need no registration):
```cpp
class CfgSlots
{
    class Slot_croco_quad_wheel_1_1 { name="croco_quad_wheel_1_1"; displayName="Front Left Wheel"; selection="wheel_1_1"; ghostIcon="wheel"; };
    // _1_2 (rear left), _2_1 (front right), _2_2 (rear right)
};
```
Naming convention `<axle>_<side>`: axle 1=front, 2=rear; side 1=left, 2=right.
`[TBD-verify]` the Landrover repo's config.cpp does NOT contain a `CfgSlots` block for its
`Landrover_Wheel_*` slots — either it relies on slots defined elsewhere in the mod or on engine
auto-registration; confirm the exact mechanism before shipping custom slots without a `CfgSlots` entry.

### c) Proxy-while-attached — `class CfgNonAIVehicles` `[QuadBike]`
For the wheel/part to RENDER on the body while attached (vs only in inventory):
```cpp
class CfgNonAIVehicles
{
    class ProxyAttachment;
    class ProxyVehiclePart: ProxyAttachment { scope=2; simulation="ProxyInventory"; autocenter=0; animated=0; shadow=1; reversed=0; };
    class Proxyquadbike_wheel: ProxyVehiclePart { model="\CrocoVehicles\QuadBike\proxys\quadbike_wheel.p3d"; inventorySlot[]={"croco_quad_wheel_1_1","croco_quad_wheel_2_1"}; };
    // + rear + destroyed variants
};
```
The proxy `.p3d` is the same model referenced by the `CarWheel` item and placed as a proxy face in the
body's Visual + ViewGeometry + FireGeometry LODs (`vehicle-structural-parity.md` Addendum 2026-05-26 — wheel
proxies in FireGeometry; Addendum 2026-05-29 — its Memory anatomy).

### d) Door item — `class <Door>: CarDoor` `[Landrover ✓]`
Doors are items too (`Landrover_Driver_Door`/`CoDriver_Door`/`Hood`/`Trunk`), each a `CarDoor` with its own
`model="\Landrover\proxy\<Door>.p3d"`, `inventorySlot`, `hiddenSelections` and a `DamageZones` with
`Window`+`Doors` zones. The door **opening animation** lives in model.cfg (§12) + `AnimationSources` (§10),
not on the item.

## 9. Sounds — borrow a vanilla engine's SoundSets

The simplest correct pattern: reference an existing vanilla vehicle's SoundSets by name (do NOT redefine
them). `[Landrover ✓]` borrows the whole `offroad_*` set:
```cpp
class Sounds
{
    thrust=0.6; thrustTurbo=1; thrustGentle=0.3; thrustSmoothCoef=0.02; camposSmoothCoef=0.03;
    soundSetsFilter[]={ "offroad_Engine_Offload_Ext_Rpm1_SoundSet", ... "offroad_Engine_Ext_Rpm0..5_SoundSet",
        "offroad_Engine_Ext_Broken_SoundSet", "offroad_Tires_*_SoundSet", "offroad_Rain_Ext_SoundSet",
        "offroad_damper_left_SoundSet","offroad_damper_right_SoundSet" };
    soundSetsInt[]={ "Offroad_Tires_Asphalt_Fast_General_Int_SoundSet","Offroad_Wind_SoundSet" };
};
```
A from-scratch car only needs custom `CfgSoundShaders`/`CfgSoundSets` if you want a unique engine note;
otherwise borrow `offroad_*` (truck/SUV) or `Hatchback_02_*`/`Sedan_02_*` (car). `[QuadBike]` borrows
`Hatchback_02_*` start/horn + defines only its own RPM SoundShaders. The `class Sounds` block lives on the
**scope=2 variant** in the QuadBike (on the base in the Landrover) — both work.

## 10. config.cpp — AnimationSources (the `user`-driven sources)

Dampers and doors are driven by script/simulation as `source="user"`; the engine-driven sources
(`wheelfrontleft`, `turnfrontleft`, `speed`, `rpm`, `fuel`…) are NOT listed here — they are provided by the
car simulation. `[Landrover ✓]`:
```cpp
class AnimationSources
{
    class DoorsDriver  { source="user"; initPhase=0;       animPeriod=0.5; };
    class DoorsCoDriver: DoorsDriver {}; class DoorsHood: DoorsDriver {}; class DoorsTrunk: DoorsDriver {};
    class damper_1_1   { source="user"; initPhase=0.4857;  animPeriod=1; };   // front rest position
    class damper_2_1: damper_1_1 {};
    class damper_1_2   { source="user"; initPhase=0.4002;  animPeriod=1; };   // rear rest position
    class damper_2_2: damper_1_2 {};
};
```
Missing a damper source ⇒ RPT `unknown animation source damper`. `initPhase` fixes the visual rest position
of the damper (front ≈0.486, rear ≈0.400).

## 11. model.cfg — CfgSkeletons (the bone hierarchy)

The **wheel bone chain encodes steering vs rolling vs suspension**: front = `damper → steering → wheel`
(3 levels), rear = `damper → wheel` (no steering bone). `isDiscrete=1` (mechanical). `[Landrover ✓]`,
abridged to the vehicle-critical bones:
```cpp
class cfgSkeletons
{
    class Landrover_skeleton
    {
        skeletonInherit=""; isDiscrete=1;
        SkeletonBones[]=
        {
            "drivewheel","", "mph","", "rpm","", "dial_rpm","", "dial_temp","", "fuel_1","",   // dashboard
            "doors_driver","", "doors_codriver","", "doors_hood","", "doors_trunk","",          // doors
            "crewdriver","", "crewcodriver","", "CrewCargo1","", /* ...CrewCargo6 */              // crew proxy bones
            "engine","", "engine_rotate","engine",
            // FRONT wheels: damper -> steering -> wheel
            "wheel_1_1_damper","",  "wheel_1_1_steering","wheel_1_1_damper",  "wheel_1_1","wheel_1_1_steering",
            "wheel_2_1_damper","",  "wheel_2_1_steering","wheel_2_1_damper",  "wheel_2_1","wheel_2_1_steering",
            // REAR wheels: damper -> wheel  (NO steering bone)
            "wheel_1_2_damper","",  "wheel_1_2","wheel_1_2_damper",
            "wheel_2_2_damper","",  "wheel_2_2","wheel_2_2_damper"
        };
    };
};
```
Each pair is `"bone","parent"` (empty parent = root). `crewdriver`/`crewcodriver`/`CrewCargoN` bones MUST
exist here because `Crew.proxyPos` requires them (§4). Bone names MUST match the .p3d selection names.

## 12. model.cfg — CfgModels Animations

`class <Model>: Default { skeletonName="<skeleton>"; sections[]={hiddenSelections + dmgZones}; class Animations {...} }`.
The four animation families a car needs, `[Landrover ✓]`:

```cpp
class Animations
{
    // ---- wheel ROLLING (continuous spin) — source provided by sim; sourceAddress=loop; maxValue=2*PI ----
    class wheel_1_1 { type="rotation"; source="wheelfrontleft";  selection="wheel_1_1"; axis="wheel_1_1_axis";
                      sourceAddress=loop; minValue=0.0; maxValue=6.2831855; angle0=0.0; angle1=6.2831855; };
    class wheel_2_1 { type="rotation"; source="wheelfrontright"; selection="wheel_2_1"; axis="wheel_2_1_axis";
                      sourceAddress=loop; minValue=0.0; maxValue=6.2831855; angle0=0.0; angle1=-6.2831855; };  // right side negated
    // wheel_1_2 (wheelbackleft), wheel_2_2 (wheelbackright) identical pattern

    // ---- STEERING (front only) — selection is the *_steering bone ----
    class steering_hub_1_1 { type="rotation"; source="turnfrontleft";  selection="wheel_1_1_steering"; axis="wheel_1_1_steering_axis";
                             minValue=-1.5707964; maxValue=1.5707964; angle0=-1.5707964; angle1=1.5707964; };
    class steering_hub_2_1 { type="rotation"; source="turnfrontright"; selection="wheel_2_1_steering"; axis="wheel_2_1_steering_axis";
                             minValue=-1.5707964; maxValue=1.5707964; angle0=-1.5707964; angle1=1.5707964; };

    // ---- SUSPENSION damper (translation) — minValue/maxValue FIXED 0/1, travel via offsets ----
    class suspension_damper_1_1 { type="translation"; source="damper_1_1"; selection="wheel_1_1_damper"; axis="wheel_1_1_damper_axis";
                                  minValue=0.0; maxValue=1.0; offset0=0.05; offset1=-0.35; };
    // _2_1 same; rear _1_2/_2_2 use maxValue=0.6 (visual only), same offsets

    // ---- steering WHEEL + dials + doors ----
    class DrivingWheel { type="rotation"; source="steeringwheel"; selection="drivewheel"; axis="drivewheel_axis";
                         minValue=-1.0; maxValue=1.0; angle0=1.9415927; angle1=-1.9415927; };
    class IndicatorSpeed { type="rotation"; source="speed"; selection="mph"; axis="mph_axis"; minValue=0.0; maxValue=160.0; angle0=0.0; angle1=-4.5361256; };
    class IndicatorRPM   { type="rotationZ"; source="rpm"; selection="rpm"; axis="rpm_axis"; minValue=0.0; maxValue=1.0; angle0=0.0; angle1=-1.5707964; };
    class IndicatorFuel  { type="rotation"; source="fuel"; selection="fuel_1"; axis="fuel_1_axis"; minValue=0.0; maxValue=1.0; angle0=0.0; angle1=-1.5707964; };
    class DoorsDriver { type="rotation"; source="doorsdriver"; selection="doors_driver"; axis="doors_driver_axis"; minValue=0.0; maxValue=1.0; angle0=0.0; angle1=1.3962634; };
    // DoorsCoDriver, DoorsHood, DoorsTrunk same shape
};
```
Key points: **wheel rolling** uses `sourceAddress=loop` and a full-turn range (`maxValue=2π`), right-side
`angle1` negated; **steering** rotates the `*_steering` selection ±90° (±π/2); **damper** is a `translation`
with `minValue=0`/`maxValue=1` and the real travel carried by `offset0`/`offset1` (NOT by min/max — the
recurring confusion; see `vehicle-structural-parity.md` Addendum 2026-05-30). Every animation needs a
matching 2-point `*_axis` selection in the Memory LOD or it silently does nothing (`dayz-p3d-audit` #6).

**Two gotchas that bit LFQuad (LL-103/LL-104), easy to half-remember:**
- **`angle0/angle1="rad N"` — N is the throw in DEGREES, not radians, for the *visible* sweep of a
  source-driven anim.** `rad 0.45` → ~0.5° (looks frozen), `rad 30` → ~30°. Tune handlebar / needle / door
  throw in a degree scale, not a 0–2π scale (the literal `6.2831855` constants above are the full-turn
  wheel-roll case, a different family). (LFQuad LL-104; a contradicting `rad -0.39` example still lives in
  `dayz-animation-pipeline` — see the pending SP for it.)
- **`GetSteering()` is client-only — the server returns 0.** A cosmetic steering / handlebar anim driven by a
  script `source="user"` set from the client gets overwritten by server sync and snaps back in MP. Use the
  **engine-native `source="steeringwheel"`** channel (already synced — the `DrivingWheel` class above) for any
  steering-coupled visual; reserve `source="user"` for what the engine does not already drive (dampers, doors).
  (LFQuad LL-103.)

## 13. The wiring chain (config ⇄ model.cfg ⇄ .p3d)

```
config Axles.Front.Wheels.Left
  animRotation="wheelfrontleft" ─────► model.cfg class wheel_1_1   source="wheelfrontleft"  (sim-driven, loop)
  animTurn    ="turnfrontleft"  ─────► model.cfg class steering_hub_1_1 source="turnfrontleft" (sim-driven)
  animDamper  ="damper_1_1"     ─────► model.cfg class suspension_damper_1_1 source="damper_1_1"
                                              ▲ also ► config AnimationSources class damper_1_1 source="user"
  wheelHub    ="wheel_1_1_damper_land" ─────► .p3d Memory point (land contact) + Geometry hub component
  inventorySlot="Landrover_Wheel_1_1"  ─────► CfgSlots slot + CarWheel item + CfgNonAIVehicles proxy
model.cfg selections (wheel_1_1, wheel_1_1_steering, wheel_1_1_damper, *_axis) ─────► must exist in .p3d
```
A break anywhere in this chain = a silent failure (no roll / no steer / no suspension / `unknown source`).

## 14. Shortcut: reuse a vanilla anim-instance rig

Instead of authoring the whole model.cfg, a mod can reuse a vanilla rig by overriding `GetAnimInstance()`
in its CarScript child (e.g. QuadBike returns `VehicleAnimInstances.V3S` `[QuadBike]`). Then the wheel/
steering/damper animation CLASSES come from the vanilla rig and you only need matching selections/axes in
the .p3d. Caveat `[QuadBike]`: `VehicleAnimInstances` alone is "not proof of a reusable model.cfg" — verify
the vanilla rig's selection names match yours before relying on it. For a truly from-scratch car, author the
full model.cfg (§11–12) — it is self-contained and the Landrover proves it works.

## 15. Troubleshooting — engine / won't-start (+ the in-game Diag tool)

| Symptom | Likely cause | Check / fix |
|---|---|---|
| Engine won't start at all | Missing engine-part slots | `CarBattery` + `SparkPlug` (and often `CarRadiator`) must be in `attachments[]` and physically attached in-game; a car with no battery/plug cranks but won't run |
| Won't start even WITH a SparkPlug attached | Default `IsVitalGlowPlug()=true` demands a GlowPlug too (`carscript.c:2011`); a bare `CarScript` needs BOTH plugs (all `IsVital*` default true, `carscript.c:2734-2762`) | Override the unused igniter — petrol: `IsVitalGlowPlug()→false` (`civiliansedan.c:363`) keep SparkPlug; diesel: `IsVitalSparkPlug()→false` (`offroad_02.c:389`) keep GlowPlug. Declare ONLY the vital plug in `attachments[]` + attach it in `OnDebugSpawn`. `IsVitalGlowPlug→false` is the vanilla petrol pattern, NOT a removed check. Bit SUB_BRZ 2026-06-28 |
| Engine drowns instantly at spawn | Missing `drown_engine` memory point ⇒ it defaults to (0,0,0) | Add `drown_engine` at the engine in the Memory LOD (`vehicle-structural-parity.md` Addendum 2026-05-30 #9) |
| RPT: `unknown animation source damper` | `AnimationSources` damper class missing | Add `class damper_X_Y { source="user"; ... }` for all four (§10) |
| Revs but no torque / stalls weirdly | `torqueCurve[]` starts/ends nonzero or rpm bands wrong | Curve must start at 0 Nm (stall rpm) and return to 0 at redline; keep `rpmIdle<rpmMin<rpmClutch<rpmRedline` |
| Steers but wheels don't spin | `animRotation` source not wired in model.cfg, or no `wheel_X_Y_axis` | §12 wheel class + 2-point axis in Memory |

**Use the in-game Diag binary** `[DayZ-wiki ✓]`: "You can debug all simulation properties directly in game
when using the Diag binary of the game. The debug is accessible through the diag menu (holding ⊞ Win + Alt
keys)… go to Game -> Vehicles -> Simulation." This is the fastest way to see live engine/RPM/wheel-contact/
suspension state instead of guessing — instrument, don't guess (R35).

**`OnDebugSpawn` gotchas (LFQuad).** It must `CreateAttachment` the drivetrain by **CLASS name, not slot name**
(`"LFQuad_Wheel_Front"`, not the slot `"LFQuad_wheel_1_1"`) — in vanilla slot==class so the bug stays masked
until your custom slots differ — plus `Fill(CarFluid.FUEL, GetFluidCapacity(CarFluid.FUEL))` (+ `COOLANT` if
`IsVitalRadiator()`); the base only drops loose parts into cargo. Also: **`OnDebugSpawn` does NOT fire when the
entity is created by the mission server in a headless harness** — attach parts manually in that path (the
MCP / admin spawn), or a "wheels missing / engine won't start" verdict is a false negative, not a real bug.

## 16. [TBD-verify] register (do NOT invent these)

- `simulationclass=` string: NOT present in Landrover or QuadBike configs (both rely on `extends CarScript`).
  Do not add a `simulationclass` field unless found in a real source. The Arma-3 equivalent is `simulation="carx"`.
- `mass`, `centerOfMass`, `sprungMass`, `geometryClass`: NOT in DayZ car config. Mass/CoM = Geometry LOD
  vertex weights. `sprungMass` is Arma-3 (`Arma_3_Cars_Config_Guidelines`); unconfirmed in DayZ.
- `CentralDifferential`: verified fields are `ratio` + `type` (Landrover: 1.5 / DIFFERENTIAL_LOCKED). Any
  property beyond those, and `DRIVE_642`, are `[TBD-verify]` (DayZ wiki truncated there).
- `reflectors[]` array: Arma-3 lights feature; unconfirmed in DayZ CarScript.
- Landrover custom `CfgSlots` registration: not in its config.cpp (§8b) — mechanism `[TBD-verify]`.
- A separate PhysX LOD (4e13): Arma-3 requires it ("a lod (4e13)… just the main body of car… wheels are
  added by engine later", `Arma_3_Cars_Config_Guidelines`); the DayZ references (Landrover, QuadBike, Croco,
  civiliansedan) use **Geometry 1e13 only**. Do NOT add a 4e13 LOD for a DayZ car unless verified in-game.
- `type="GEARBOX_AUTOMATIC"`: the engine natively supports it — `enum CarGearboxType {MANUAL, AUTOMATIC}`
  plus `GearboxGetMode()`/`CarAutomaticGearboxMode` confirmed verbatim in vanilla `car.c:33-38,277-280`
  (2026-07-07) — but **zero real-world configs found using it** (Landrover, UAZ, vanilla-dump all ship
  `GEARBOX_MANUAL`). Treat as native-but-unprecedented: no ratios/tuning reference exists to copy. If
  attempted, verify behavior live via the in-game Diag tool (§15), don't guess.

## Sources
- Landrover config.cpp + model.cfg (verbatim, self-fetched 2026-05-30): `https://raw.githubusercontent.com/Tyson89/Landrover/main/config.cpp`, `https://raw.githubusercontent.com/Tyson89/Landrover/main/Landrover.cfg`
- Landrover wiki tutorial: `https://github.com/Tyson89/Landrover/wiki` (Home, config.cpp, Object-Builder, SimulationModule)
- DayZ vehicle config (verbatim, self-fetched): `https://community.bistudio.com/wiki/DayZ:Vehicle_Configuration`
- Arma 3 cars (drivetrain/sprungMass/PhysX-LOD context): `https://community.bistudio.com/wiki/Arma_3_Cars_Config_Guidelines`
- QuadBike (Crocodoc) real values: `AI/10_Projects/DayZ_Vehicle_Skill/skill-draft/references/carscript-cheatsheet.md`, `.../library/quadbike.notes.md`
- Geometry/mass/CoM/wheel-proxy/ride-height invariants: `vehicle-structural-parity.md` (this skill)

> Origin: LFQuad car-build skill consolidation 2026-05-30. Multi-agent canon extraction (Landrover wiki+repo,
> Bohemia DayZ/LOD/Oxygen2/Validating/Arma3-Cars) reconciled by the orchestrator against self-fetched primary
> sources + verified vault QuadBike reference. Cross-ref `dayz-p3d-audit` Killers #11/#12/#13, `dayz-pbo-build`,
> `dayz-animation-pipeline` (py3d Memory LOD quirks).

## 17. (added 2026-06-05) — Crew get-in resolution + proxy frame (verified in-game, LFQuad)
> (Merged 2026-07-06 from the `dayz-model-pipeline` fork copy -- LL-110 dedup. Newer canonical
> seat rules extend 17.1/17.2: `vehicle-structural-parity.md` Addendum 2026-06-27 + CRITICAL EXTENSION
> 2026-06-28 -- seat ComponentNN cubes must ALSO be inward-wound with point flags `0x02000000` or they
> are not raycast-collidable.)

> Extends §4 (Crew) with the part §4 did not cover: **how the engine actually resolves which seat a
> get-in lands in**, and **how a crew proxy's geometry must be shaped** so the player sits upright at the
> right height facing forward. Verified in-game on LFQuad after ~7 days of churn whose root cause was a
> crew ViewGeometry whose seat selections were spread across many collision components instead of two
> dedicated ones. The CoDriver never appeared until the structure matched the Croco's. `[LFQuad ✓]` =
> verified in-game / by py3d structural diff this session; `[QuadBike]` = Crocodoc reference values.

### 17.1 Get-in is resolved per COLLISION COMPONENT (not per selection, not per memory point)

The engine maps a get-in to a seat through **`Transport.CrewPositionIndex(int componentIndex)`** —
`proto native int CrewPositionIndex(int position)` at `P:\scripts\3_game\vehicles\transport.c:116`
(opaque; no script body). The `componentIndex` is the **collision component** that the cursor's raycast
hits when the player presses "enter". The engine pre-associates each crew slot with the component(s) that
contain that slot's `actionSel` selection (the `seat_driver` / `seat_codriver` named selection from the
`Crew` config, §4) **in the ViewGeometry LOD**.

So the wiring is: cursor raycast → hit component N → `CrewPositionIndex(N)` → driver / co-driver / cargo.
A wheel-hub axis or a `pos_driver` memory point does NOT drive this; **only the geometry of the component
carrying `seat_driver`/`seat_codriver` does.**

### 17.2 RULE: each seat needs its OWN dedicated component in the ViewGeometry

`[QuadBike]` the working reference has exactly **two** crew components in its ViewGeometry:
`component24` = `seat_driver` (8 pts / 6 faces, one clean cube), `component25` = `seat_codriver`
(8 pts / 6 faces). One selection, one component, per seat.

`[LFQuad ✓]` the broken model had the `seat_driver`/`seat_codriver` selections **spread across the whole
multi-component grid** that had been copied from the Geometry LOD into the ViewGeometry — **23 crew
components, 88/112 points sprinkled** instead of 2. The engine then generated 23 overlapping crew
components; the get-in raycast resolved to the first/driver component every time and **never** landed on
the co-driver. Symptom: **co-driver seat unusable, player only ever boards as driver.**

> **Build rule (do this for every car):** in the ViewGeometry LOD, give each seat its **own single
> dedicated component** — one connected cube (8 pts / 6 faces is enough) tagged ONLY with that seat's
> `actionSel` selection (`seat_driver` in one, `seat_codriver` in another, `seat_cargoN` each in its own).
> Do NOT reuse the multi-component Geometry/collision grid as the crew ViewGeo. Verify with py3d:
> `count of components carrying seat_* == number of seats` (Croco: 2). If it is 20+, the get-in is broken.

This is the actionable form of the LFQuad root cause; the diagnosis method (structural py3d diff vs the
Croco rather than theorizing about the opaque native) is `lessons-learned.md` LL-090; the "transplant the
reference structure wholesale instead of patching piece by piece" meta-lesson is LL-089.

### 17.3 The crew PROXY frame = orientation + seated height (and where height actually comes from)

`Crew.proxyPos` (§4) names a **proxy in the ViewGeometry** (a 3-vertex triangle face placed as
`proxy:\...`), and that proxy is what positions the player — **not** the `pos_driver` memory point or the
skeleton bone. The proxy's frame is derived by **angle-sort of its three vertices** (the
`dayz-proxy-align` / `Arma3ObjectBuilder` convention, see `LL-072`):

| vertex | role |
|---|---|
| widest angle | **anchor** = the proxy's position (and thus the seated player's position/height) |
| middle angle | local **+Y** |
| smallest angle | local **+Z** |

For a **crew** proxy the target frame is: **+Y → front of the vehicle, +Z → up.** Then:

- **Anchor = seated height.** Because the anchor vertex is the position, an anchor placed too high puts the
  player in the air. `[LFQuad ✓]` anchors at Y=1.46 / Y=1.70 → player floating above the quad; fix = drop
  the anchor to seat height + the small seat offset. Tune the **anchor Y**, not the memory point.
- **Use a canonical scalene triangle, never isosceles.** A 90/45/45 isosceles triangle (the shape you get
  from a hand-rolled 1 mm proxy) makes the middle and smallest angles **tie** → the +Y/+Z assignment is
  ambiguous → the frame falls differently per proxy → **player seated sideways and spins on entry**. Always
  emit 3 distinct angles (e.g. 90/63.4/26.6) encoding the exact frame. Full statement: `LL-072`; the
  crew-specific addition here is the +Y→front / +Z→up target and anchor=height.
- **Do NOT copy a proxy frame from another sub-model.** The correct frame depends on which crew sub-model
  the proxy references. Vanilla / LFQuad reference `crew_driver` / `crew_cargo`
  (`proxy:\dz\vehicles\wheeled\proxies\crew_driver`), for which **+Y must point to the vehicle front**.
  `[QuadBike]` the Croco references `bus_driver` / `bus_cargo`, and its co-driver derives **+Y → −Z (toward
  the rear)**. Copying the Croco's raw triangle into a vanilla-crew car gives a back-facing / wrong
  orientation. Match the frame to the referenced sub-model, do not transplant the raw vertices across
  sub-models.

### 17.4 Driver's HANDS = the animation rig, not the model

The hands on the wheel/bars come from the player's **animation instance** (the anim-set, e.g. `QUADBIKE`
from @Survivor Animations, selected via `GetAnimInstance()` — §14 / config `class Crew` driver pose), NOT
from IK and NOT from any memory point on the vehicle. `[LFQuad ✓]` + `[QuadBike]`: there are **no hand
memory points** on either vehicle `.p3d`, and hand placement is **not editable from the `.p3d`** — it is a
property of the rig. If the hands sit wrong, fix the anim instance, not the model.

### 17.5 Headless validation loop for crew get-in (and its limits)

You can validate the get-in **without a manual in-game test cycle** with a test mission that spawns the
vehicle plus an auto-connecting client and probes each seat:

1. For `i` in `0..N`, call `Transport.CrewPositionIndex(i)` and tabulate which component maps to which seat
   (driver/co-driver/cargo) — this alone reveals "23 components all → driver".
2. Raycast from outside toward each seat's world position with
   **`DayZPhysics.RaycastRV(vector begin, vector end, out vector contactPos, out vector contactDir, out int contactComponent, set<Object> results, Object ignore, Object source, bool sorted, bool ground, int iType, float radius)`** — signature at `P:\scripts\3_game\global\dayzphysics.c:199` — and check that `contactComponent` is the seat's dedicated component. Compare every result against a **control vehicle that already works** (the Croco).

**Limits (all verified `[LFQuad ✓]`):**
- `RaycastRV` is **server-only-blind without a client**: with no connected client it returns hit=0. The
  mission must actually connect a client.
- A **large `radius`** crosses the boundary between adjacent components and gives a false component id — use
  a **fine radius (~0.05)** so the hit lands inside one component.
- The raycast offset must be expressed in **LOCAL space transformed by `ModelToWorld`**, not a fixed world
  offset — the vehicle spawns with some pitch/roll, so a world-fixed probe misses.
- The **visual posture is NOT measurable headless**: final orientation (sitting upright vs sideways) and
  seated height are only confirmable by eye in-game. The loop proves *which seat the get-in resolves to*;
  it cannot prove *how the player looks once seated* (that is §17.3 + an in-game screenshot).

> Bottom line for a future car's crew: (1) two dedicated seat components in ViewGeo — verify count with
> py3d vs the Croco; (2) crew proxies with canonical scalene triangles, +Y→front, +Z→up, anchor at seat
> height; (3) match the proxy frame to the referenced crew sub-model, never copy it raw from another;
> (4) hands come from the anim rig; (5) gate the get-in with the headless `CrewPositionIndex` +
> `RaycastRV` loop, then confirm posture by eye. Origin: LFQuad get-in resolution, in-game verified
> 2026-06-05; cross-ref `lessons-learned.md` LL-089/LL-090/LL-072, handoff
> `30_Sessions/2026-06-05-LFQuad-causa-copiloto-firegeo-plan-definitivo.md`.

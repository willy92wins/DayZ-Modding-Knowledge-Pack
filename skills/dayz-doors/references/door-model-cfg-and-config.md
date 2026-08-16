# Door model.cfg and config.cpp contract

## Contents

- [Evidence convention](#evidence-convention)
- [Name flow](#name-flow)
- [model.cfg contract](#modelcfg-contract)
- [config.cpp contract](#configcpp-contract)
- [DamageSystem contract](#damagesystem-contract)
- [Verified mappings](#verified-mappings)
- [Unverified or conflicting details](#unverified-or-conflicting-details)
- [Sources](#sources)

## Evidence convention

- **Verified** means the class/property appears in a shipped working file under **assets/**, or the stated behavior is explicitly taught by one of the four local tutorials.
- A leading **?** means the supplied files do not independently confirm the claim, or the sources conflict.
- Code in [worked-examples.md](worked-examples.md) is **[EXACT]**: copied from the real files. This document describes the contract without silently normalizing those examples.

## Name flow

Normal mapping:

**P3D View Geometry interaction selection -> model.cfg source -> config.cpp class Doors component**

Moving geometry mapping:

**P3D moving named selection -> CfgSkeletons bone -> CfgModels animation selection**

The two chains can share a name (**door1**) or diverge (**selection = "door1"**, **source = "door1_open"**). See **WELCOME TO novoGODS Shit Door Tutorial.txt:17-22** and **assets/Door_w_Button/Door_w_Button.cfg:27-38**.

## model.cfg contract

### CfgSkeletons

The shipped files spell the root class **cfgSkeletons**; the tutorial/common convention calls it **CfgSkeletons**. Preserve the working syntax when copying an example.

| Class/property | Contract | Verification |
|---|---|---|
| **class CfgSkeletons / cfgSkeletons** | Root skeleton declaration. | Simple **assets/Door/Simple_Door.cfg:1-14**; button **:1-12**; expert **:1-14**. |
| Custom skeleton class | Referenced by the model's **skeletonName**. | **Simple_DoorSkeleton** at Simple **:3-13**; equivalents in other CFGs. |
| **skeletonInherit** | Parent skeleton; all examples use **""**. | Simple **:5**; button **:5**; expert **:5**. |
| **isDiscrete** | All three real examples use **0**. | Simple **:6**; button **:6**; expert **:6**. |
| **SkeletonBones[]** | Flat (child,parent) string pairs. | Simple **:7-12**; button **:7-10**; expert **:7-12**. |
| Parent **""** | Bone follows no animated parent. | Fundamentals **:11-14**; real **door1** roots and expert **lever**. |
| Parent bone name | Child follows that parent's transform. | Simple **handle,door1** at **:10-11**; expert **:9-11**. |

Prefer a model-unique skeleton name derived from the P3D basename, such as **<p3dname>_skeleton**. Real files use **Simple_DoorSkeleton**, **Door_w_ButtonSkeleton**, and **Expert_ModeSkeleton**; separator/suffix spelling is a convention, not proven as an engine requirement.

? The fundamentals tutorial says duplicate skeleton names can cause server crashes (**WELCOME TO novoGODS Shit Door Tutorial.txt:11**), but the supplied files cannot reproduce that outcome. Treat uniqueness as a preventive convention.

### CfgModels and class Animations

| Class/property | Contract | Verification |
|---|---|---|
| **class CfgModels** | Root model declaration. | Simple **assets/Door/Simple_Door.cfg:15-55**; button **:13-41**; expert **:15-67**. |
| **class Default** | Empty base with sections and skeleton fields. | Simple **:17-22**; button **:15-20**; expert **:17-22**. |
| **sections[]** | Named material sections; empty here. | Simple **:19,26**; button **:17,24**; expert **:19,26**. |
| **sectionsInherit** | Inherited sections; empty here. | Simple **:20**; button **:18**; expert **:20**. |
| **skeletonName** | Exact custom skeleton class name. | Simple **:25**; button **:23**; expert **:25**. |
| Model class | Matches P3D basename in all examples. | **Simple_Door :23**; **Door_w_Button :21**; **Expert_Mode :23**. |
| **class Animations** | One class per animated selection, not per source. | Simple **:27-53**; expert has three at **:27-65**. |
| **type = "rotation"** | Rotates the named selection. | Every real animation class. |
| **selection** | Moving named selection in the LODs where it exists. | Fundamentals **:17**; Simple **:32,44**. |
| **source** | Controller/interaction name; may differ from selection. | Fundamentals **:18**; button **:30-32**; expert **:32-33,44-45,56-57**. |
| **axis** | Named Memory LOD axis selection. | Simple **:34,46**; button **:32**; expert **:34,46,58**. |
| **memory = 1** | All real rotations use Memory axes. | Simple **:35,47**; button **:33**; expert **:35,47,59**. |
| **minValue** | Source phase where motion starts. | Simple door **0.15 :36**; handle **0 :48**. |
| **maxValue** | Source phase where angle1 is reached. | Simple handle **0.15 :49**; expert lever **0.5 :61**. |
| **angle0** | Rotation at minValue; all examples use **0**. | Simple **:38,50**; button **:36**; expert **:38,50,62**. |
| **angle1** | Rotation at maxValue; sign sets direction in these files. | Simple **1.9/-1.4 :39,51**; expert **1.9/-1.7/-0.88 :39,51,63**. |

**Verified: `angle0/angle1` are in RADIANS.** BI Model Config wiki: angle values are specified in radians (= degrees x pi/180); a bare number is radians, or write `"rad 90"` to give degrees. Independently confirmed in the user's `dayz-animation-pipeline/references/config-driven-animation.md:40`. The shipped values fit: Simple Door `angle1 = 1.9` rad ~= 109 deg of swing. (Verified 2026-07-14 vs BI wiki + local skill.)

### Source aggregation

A single source can drive several animation classes:

- Simple Door: **Door1** and **handle** both use **source = "door1"** (**assets/Door/Simple_Door.cfg:29-52**).
- Button: only **Door1** animates, using **source = "door1_open"** (**assets/Door_w_Button/Door_w_Button.cfg:27-38**).
- Expert: **Door1**, **Handle**, and **Lever** all use **source = "door1_open"** (**assets/Expert_Mode/Expert_Mode.cfg:29-64**).

The button is absent from its skeleton because it does not animate (**Door_w_Button Readme.txt:65**).

## config.cpp contract

### Outer classes and object declaration

| Class/property | Contract | Verification |
|---|---|---|
| **class CfgPatches** | Addon patch root. | Every real **config.cpp:1-7**. |
| Patch subclass | Example-specific patch name. | Each real **config.cpp:3**. |
| **requiredAddons[] = {"DZ_Data"}** | Required in all working examples. | Every real **config.cpp:5**; fundamentals **:101-107,228**. |
| **class CfgVehicles** | Entity declaration root. | Every real **config.cpp:9**. |
| **class HouseNoDestruct;** | Base forward declaration. | Every real **config.cpp:11**. |
| **class land_*: HouseNoDestruct** | Entity class pattern used here. | Every real **config.cpp:12**. |
| **scope** | All real examples use **scope = 1**. | Every real **config.cpp:14**. |
| **model** | Addon-relative P3D path. | Every real **config.cpp:15**. |
| **class Doors** | Door subsystem under the entity. | Every real **config.cpp:16**. |

**Verified: `scope` = 0 private / 1 protected / 2 public.** BI CfgVehicles Config Reference. In DayZ practice, 1 = protected (placed via Terrain Builder or inherited, not directly spawnable) and 2 = player/admin-spawnable (user's `enforce-script-reference/references/config-cpp.md:123`). Buildings ship `scope = 1`, matching the tutorial's intent. (Verified 2026-07-14.)

### Per-door entry

| Property | Contract in supplied examples | Verification |
|---|---|---|
| Doors subclass | Corresponds by convention to source/component; **component** is exact binding. | Simple **assets/Door/config.cpp:18-21**; button **assets/Door_w_Button/config.cpp:18-21**. |
| **displayName** | Player-facing door/controller label. | Simple/button/expert main **:20**; expert secondary **:33**. |
| **component** | Exact model.cfg interaction source. | Simple **:21**; button **:21**; expert **:21,34**. |
| **soundPos** | Memory point where door sound originates. | Simple **:22**; button **:22**; expert main **:22**; real Expert Lever omits it. |
| **animPeriod** | Duration in seconds per tutorial. | Simple **1.3 :23**; button/expert main **1.0**; expert secondary **0.50 :35**. |
| **initPhase** | All real entries use **0.0**. | Simple **:24**; button **:24**; expert **:24,36**. |
| **initOpened** | World-spawn behavior per tutorial. | Simple/button **0.0**; expert **0.5/0.0 :25,37**. |
| **soundOpen** | Opening sound name. | Full door entries Simple/button/expert **:26**. |
| **soundClose** | Closing sound name. | Full door entries Simple/button/expert **:27**. |
| **soundLocked** | Locked/rattle sound. | Full door entries Simple/button/expert **:28**. |
| **soundOpenABit** | Partial-opening sound. | Full door entries Simple/button/expert **:29**. |

Tutorial sound list: **DZ\sounds\hpp\config.cpp** (**WELCOME TO novoGODS Shit Door Tutorial.txt:255-256**). Verify a sound there before adding it.

**Verified: `initPhase` is the initial animation phase value (0..1) at spawn, NOT a start delay.** BI Doors_on_buildings wiki ("initial value for the animation"). The tutorial's "time it takes to start" phrasing is WRONG; real files use `0.0` = spawn closed. (Verified 2026-07-14 vs BI wiki.)

**Verified: `initOpened` is a spawn probability.** BI Doors_on_buildings wiki: when `rand < initOpened` the door spawns opened, so `0` never spawns open and `0.5` spawns open ~half the time. The tutorial's description is correct. (Verified 2026-07-14 vs BI wiki.)

### One source to one Doors entry

Preferred starting rule: create one **class Doors** subclass per unique **source**, with **component** equal to that source. Animated selections sharing the source do not get separate normal door entries. Simple and Button follow this.

? Expert contradicts a universal rule: its model has only **source = "door1_open"** (**assets/Expert_Mode/Expert_Mode.cfg:33,45,57**), but config declares **Door1_Open** and **Lever**, both with **component = "door1_open"** (**assets/Expert_Mode/config.cpp:18-38**). Ask before copying the second entry.

## DamageSystem contract

| Class/property | Role in supplied examples | Verification |
|---|---|---|
| **class DamageSystem** | Root damage definition. | Simple/button **config.cpp:32-84**; expert **:40-92**. |
| **GlobalHealth > Health** | Global **hitpoints = 1000**. | Simple/button **:34-40**; expert **:42-48**. |
| **GlobalArmor** | Projectile/Melee Health, Blood, Shock damage all **0**. | Simple/button **:41-55**; expert **:49-63**. |
| **DamageZones** | Per-component zones. | Simple/button **:56-83**; expert **:64-91**. |
| Zone **class Door1** | Zone name used in all examples. | Simple/button **:58**; expert **:66**. |
| Zone **class Health** | **hitpoints = 1000**, **transferToGlobalCoef = 0**. | Simple/button **:60-64**; expert **:68-72**. |
| **componentNames[]** | Moving geometry **{"door1"}**, even when source is **door1_open**. | Simple/button **:65**; expert **:73**. |
| **fatalInjuryCoef** | **-1** in every zone. | Simple/button **:66**; expert **:74**. |
| **class ArmorType** | Projectile Health **2**; Melee Health **2.5**; Blood/Shock **0**. | Simple/button **:67-81**; expert **:75-89**. |

Do not replace **DamageZones.componentNames[]** automatically with the Doors component: Button and Expert prove the two can differ.

## Verified mappings

| Pattern | Bones | Animation selections | Unique source(s) | Real Doors component(s) |
|---|---|---|---|---|
| Simple Door | door1 -> ""; handle -> door1 | door1, handle | door1 | door1 |
| Door with Button | door1 -> "" | door1 | door1_open | door1_open |
| Expert Mode | door1 -> ""; handle -> door1; lever -> "" | door1, handle, lever | door1_open | door1_open twice |

## Unverified or conflicting details

Resolved 2026-07-14 (details in the per-property sections above): `angle0/angle1` = radians, `initPhase` = initial phase not a delay, `initOpened` = spawn probability, `scope` 0/1/2 = private/protected/public. All confirmed against the BI wiki + the user's verified skills.

Remaining:

- ? Duplicate skeleton names causing a server crash: tutorial warning, not independently reproduced. Treat skeleton-name uniqueness as a cheap preventive convention.
- Conflict (resolved by authority, not a ?): the one-source/one-Doors rule is contradicted by Expert -- two Doors entries share component `door1_open`. A real quirk of the shipped example.
- Conflict (resolved by authority): Expert prose has `soundOpen = "switchOpen"` / `soundClose = "switchClose"`, but real `assets/Expert_Mode/config.cpp:31-38` omits both. The real file wins.

## Sources

Local tutorials read in full:

- **WELCOME TO novoGODS Shit Door Tutorial.txt**
- **Simple_Door Readme.txt**
- **Door_w_Button Readme.txt**
- **Welcome to novoGODs Expert_Mode Door mod.txt**

Shipped examples:

- **assets/Door/Simple_Door.cfg** and **assets/Door/config.cpp**
- **assets/Door_w_Button/Door_w_Button.cfg** and **assets/Door_w_Button/config.cpp**
- **assets/Expert_Mode/Expert_Mode.cfg** and **assets/Expert_Mode/config.cpp**

Official references cited by tutorials, not fetched during authoring:

- https://community.bistudio.com/wiki/DayZ:Doors_on_buildings
- https://github.com/BohemiaInteractive/DayZ-Samples
- https://community.bistudio.com/wiki/LOD

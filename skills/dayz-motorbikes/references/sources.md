# Sources and Extraction Evidence (DayZ 1.30 Exp)

This document details the extraction environment, analyzed builds, primary sources, and the exact line count of each file cited in the `dayz-motorbikes` skill and its references.

## Extraction Root and Metadata

- **Workspace root**: the author's local extraction of build 1.30.164014 (`exp/` = 1.30 Exp, `stable-1.29/` = 1.29 stable)
- **Extraction date**: 2026-09-16
- **DayZ version and build analyzed**: DayZ Experimental 1.30, build `1.30.164014`
- **Extraction tool**: Mikero tools; `config.cpp` files are `config.bin` debinarized with DeRap ("Dos Tools Dll version 10.13", header of `exp\vehicles_singletrack\DZ\vehicles\singletrack\config.cpp:1-6`)
- **Stable comparison version**: DayZ 1.29 Stable (`stable-1.29\` folder)
- **Evidence level**: `source_verified` (claims are verified in Enforce Script `.c` source code, `.cpp` configs, and `.agf` graph, except those marked `[UNVERIFIED]`; none is assumed `runtime_verified` until tested on server).

## Critical Note on Vehicle and Motorbike SoundSets

In the DayZ 1.30 Experimental extraction:
- The file `exp\sounds_vehicles\DZ\sounds\vehicles\config.cpp` has only **31 lines** and contains **exclusively** the `CfgPatches` declaration (`DZ_Sounds_Vehicles`). It contains no sound classes.
- Actual definitions of `CfgSoundShaders` and `CfgSoundSets` for motorbikes (`Motorbike_01` and `Motorbike_02`) reside in:
  `exp\sounds_hpp\DZ\sounds\hpp\config.cpp` (183928 total lines):
  - `Motorbike_0*` classes in `CfgSoundShaders` (section `1454-59958`): lines `59253` through `59918` (engine RPM, offload overrun, brake, shock absorbers, tyres on different surfaces, crash).
  - `Motorbike_0*` classes in `CfgSoundSets` (section `59959-98936`): lines `98179` through `98909` (gear shift, kickstart, lights, get in/out, short/long/loop horn, RPM sets).
- These blocks were extracted with their real lines to `work\soundsets-motorbike-1.30.txt` (1913 lines).

## Cited Source Files and Total Lines

Below is each file from the `exp\` extraction and `work\` diffs referenced in this technical documentation with its verified line count (text lines: output of `wc -l`, plus 1 if the last line lacks a trailing newline; recounted on 2026-09-19):

### 1. Engine and Base Scripts (3_Game)
| File in extraction (`exp\`) | In-game internal path | Total lines | Key analyzed symbols |
|---|---|---|---|
| `exp\bin\bin\config.cpp` | `bin\config.cpp` | 6287 | `class Motorbike: Transport`, `simulation = "motorbike"` |
| `exp\scripts\scripts\3_Game\Vehicles\Motorbike.c` | `scripts\3_Game\Vehicles\Motorbike.c` | 370 | Motorbike `proto native` signatures, `MotorbikeOwnerState`, `MotorbikeMove`, sound and stability callbacks |
| `exp\scripts\scripts\3_Game\Vehicles\Transport.c` | `scripts\3_Game\Vehicles\Transport.c` | 1205 | `ETransportFluid`, `NeedElectricitySourceDevice`, `IsAnyCrewPresent`, `OnContact`, `m_ContactCache`, `VehicleContactData` |
| `exp\scripts\scripts\3_Game\Vehicles\Car.c` | `scripts\3_Game\Vehicles\Car.c` | 507 | `enum CarFluid : ETransportFluid` |
| `exp\scripts\scripts\3_Game\Vehicles\Boat.c` | `scripts\3_Game\Vehicles\Boat.c` | 207 | `enum BoatFluid : ETransportFluid` |
| `exp\scripts\scripts\3_Game\constants.c` | `scripts\3_Game\constants.c` | 1168 | `MOTORBIKES_CONTACT_DMG_*`, `ENVIRO_HEATCOMFORT_MOTORBIKE_*` |
| `exp\scripts\scripts\3_Game\human.c` | `scripts\3_Game\human.c` | 1721 | `HumanAnimInterface.IsTag()`, `HumanCommandVehicle.IsTransitioning()` |
| `exp\scripts\scripts\3_Game\dayzplayer.c` | `scripts\3_Game\dayzplayer.c` | 1413 | Player constants |
| `exp\scripts\scripts\3_Game\DustKickupEffects.c` | `scripts\3_Game\DustKickupEffects.c` | 256 | Projectile dust effects singleton |
| `exp\scripts\scripts\3_Game\Enums\EVehicleVFXTypes.c` | `scripts\3_Game\Enums\EVehicleVFXTypes.c` | 17 | `EVehicleVFXEffect`, `EVehicleVFXEffectGroup` |

### 2. Gameplay and Entity Scripts (4_World)
| File in extraction (`exp\`) | In-game internal path | Total lines | Key analyzed symbols |
|---|---|---|---|
| `exp\scripts\scripts\4_World\Entities\Vehicles\MotorbikeScript.c` | `scripts\4_World\Entities\Vehicles\MotorbikeScript.c` | 1765 | Lifecycle, kickstand, starting, "drivewheel" lights, damages, network sync |
| `exp\scripts\scripts\4_World\Entities\Vehicles\CarScript.c` | `scripts\4_World\Entities\Vehicles\CarScript.c` | 2981 | 1.30 refactor, component delegation, deprecated methods marked with `[Obsolete]` |
| `exp\scripts\scripts\4_World\Entities\Vehicles\VehicleAnimInstances.c` | `scripts\4_World\Entities\Vehicles\VehicleAnimInstances.c` | 15 | `MOTO1 = 10`, `MOTO2 = 11` |
| `exp\scripts\scripts\4_World\Entities\Vehicles\InheritedMotorbikes\Motorbike_01.c` | `scripts\4_World\Entities\Vehicles\InheritedMotorbikes\Motorbike_01.c` | 171 | `Motorbike_01_ColorBase`, `SeatDriver`, `ActionAnimateMotorbikeSeat`, SoundSets |
| `exp\scripts\scripts\4_World\Entities\Vehicles\InheritedMotorbikes\Motorbike_02.c` | `scripts\4_World\Entities\Vehicles\InheritedMotorbikes\Motorbike_02.c` | 142 | `Motorbike_02_ColorBase`, `ShieldFront/Left/Right` fairings, thermal comfort |
| `exp\scripts\scripts\4_World\Entities\Vehicles\InheritedCars\CivilianSedan.c` | `scripts\4_World\Entities\Vehicles\InheritedCars\CivilianSedan.c` | 497 | Lights and horn migration to components |
| `exp\scripts\scripts\4_World\Entities\Vehicles\InheritedCars\Offroad_02.c` | `scripts\4_World\Entities\Vehicles\InheritedCars\Offroad_02.c` | 475 | `HasGangedTailAndBrakeLights`, shared lights |
| `exp\scripts\scripts\4_World\Entities\Vehicles\Components\VehicleHornComponent.c` | `scripts\4_World\Entities\Vehicles\Components\VehicleHornComponent.c` | 111 | Horn modes, AI noise, `NoiseCarHorn` integration |
| `exp\scripts\scripts\4_World\Entities\Vehicles\Components\VehicleLightsComponent.c` | `scripts\4_World\Entities\Vehicles\Components\VehicleLightsComponent.c` | 190 | Registration of light selections and profiles |
| `exp\scripts\scripts\4_World\Entities\Vehicles\Components\VehicleVFXComponent.c` | `scripts\4_World\Entities\Vehicles\Components\VehicleVFXComponent.c` | 588 | Unified particles and exhaust/wheel smoke management |
| `exp\scripts\scripts\4_World\Entities\ScriptedLightBase\SpotLightBase\VehicleLightBase.c` | `scripts\4_World\Entities\ScriptedLightBase\SpotLightBase\VehicleLightBase.c` | 86 | Parameterized generic spotlight |
| `exp\scripts\scripts\4_World\Entities\ScriptedLightBase\SpotLightBase\VehicleLightProfiles\VehicleLightProfileBase.c` | `scripts\4_World\Entities\ScriptedLightBase\SpotLightBase\VehicleLightProfiles\VehicleLightProfileBase.c` | 95 | Base aggregated and segregated lighting profile |
| `exp\scripts\scripts\4_World\Entities\ScriptedLightBase\SpotLightBase\VehicleLightProfiles\Motorbike_01.c` | `scripts\4_World\Entities\ScriptedLightBase\SpotLightBase\VehicleLightProfiles\Motorbike_01.c` | 34 | `Motorbike_01LightProfileFront`, `Motorbike_01LightProfileRear` |
| `exp\scripts\scripts\4_World\Entities\ScriptedLightBase\SpotLightBase\VehicleLightProfiles\Motorbike_02.c` | `scripts\4_World\Entities\ScriptedLightBase\SpotLightBase\VehicleLightProfiles\Motorbike_02.c` | 34 | `Motorbike_02LightProfileFront` |
| `exp\scripts\scripts\4_World\Entities\DayZPlayerImplement.c` | `scripts\4_World\Entities\DayZPlayerImplement.c` | 4131 | Crash ejection (`CrewShouldEject` / `eModifiers.MDF_UNCONSCIOUSNESS`), bike death (`FallOver`) |
| `exp\scripts\scripts\4_World\Entities\DayZPlayerImplementFallDamage.c` | `scripts\4_World\Entities\DayZPlayerImplementFallDamage.c` | 378 | `CurveExp` exponential curve and new thresholds |
| `exp\scripts\scripts\4_World\Entities\ManBase\DayZPlayer\DayZPlayerCameras.c` | `scripts\4_World\Entities\ManBase\DayZPlayer\DayZPlayerCameras.c` | 173 | Registration of `DAYZCAMERA_3RD_VEHICLE_MOTORBIKE = 32` |
| `exp\scripts\scripts\4_World\Entities\ManBase\DayZPlayer\DayZPlayerCameraVehicles.c` | `scripts\4_World\Entities\ManBase\DayZPlayer\DayZPlayerCameraVehicles.c` | 470 | Implementation of `DayZPlayerCamera3rdPersonVehicleMotorbike` with spring lag |
| `exp\scripts\scripts\4_World\Entities\ManBase\PlayerBase.c` | `scripts\4_World\Entities\ManBase\PlayerBase.c` | 10144 | Engine start and stop actions registration |
| `exp\scripts\scripts\4_World\Entities\ItemBase\Blowtorch.c` | `scripts\4_World\Entities\ItemBase\Blowtorch.c` | 146 | Exclusive registration of chassis, engine, and bike part repair actions |

### 3. User Actions (4_World / Actions)
| File in extraction (`exp\`) | In-game internal path | Total lines | Key analyzed symbols |
|---|---|---|---|
| `exp\scripts\scripts\4_World\Classes\UserActionsComponent\Actions\Continuous\Vehicles\ActionStartEngineMotorBike.c` | `scripts\4_World\...\ActionStartEngineMotorBike.c` | 100 | Continuous kickstart action, `OnIgnition()` |
| `exp\scripts\scripts\4_World\Classes\UserActionsComponent\Actions\SingleUse\Vehicles\ActionStopEngineMotorBike.c` | `scripts\4_World\...\ActionStopEngineMotorBike.c` | 76 | Engine stop action capped at 8 km/h |
| `exp\scripts\scripts\4_World\Classes\UserActionsComponent\Actions\Interact\Vehicles\ActionPickUpMotorBike.c` | `scripts\4_World\...\ActionPickUpMotorBike.c` | 104 | Picking up fallen bike (`trans.PickUp()`) |
| `exp\scripts\scripts\4_World\Classes\UserActionsComponent\Actions\Interact\Vehicles\ActionAnimateMotorbikeSeat.c` | `scripts\4_World\...\ActionAnimateMotorbikeSeat.c` | 47 | `SeatDriver` tilting |
| `exp\scripts\scripts\4_World\Classes\UserActionsComponent\Actions\Continuous\ActionRepairMotorbikeChassis.c` | `scripts\4_World\...\ActionRepairMotorbikeChassis.c` | 55 | Base chassis repair |
| `exp\scripts\scripts\4_World\Classes\UserActionsComponent\Actions\Continuous\ActionRepairMotorbikeChassisWithBlowtorch.c` | `scripts\4_World\...\ActionRepairMotorbikeChassisWithBlowtorch.c` | 46 | Chassis repair with blowtorch |
| `exp\scripts\scripts\4_World\Classes\UserActionsComponent\Actions\Continuous\ActionRepairMotorbikeEngine.c` | `scripts\4_World\...\ActionRepairMotorbikeEngine.c` | 60 | Base engine repair (orphaned) |
| `exp\scripts\scripts\4_World\Classes\UserActionsComponent\Actions\Continuous\ActionRepairMotorbikeEngineWithBlowtorch.c` | `scripts\4_World\...\ActionRepairMotorbikeEngineWithBlowtorch.c` | 45 | Engine repair with blowtorch |
| `exp\scripts\scripts\4_World\Classes\UserActionsComponent\Actions\Continuous\ActionRepairMotorbikePart.c` | `scripts\4_World\...\ActionRepairMotorbikePart.c` | 160 | Base part/fairing repair |
| `exp\scripts\scripts\4_World\Classes\UserActionsComponent\Actions\Continuous\ActionRepairMotorbikePartWithBlowTorch.c` | `scripts\4_World\...\ActionRepairMotorbikePartWithBlowTorch.c` | 46 | Part repair with blowtorch |
| `exp\scripts\scripts\4_World\Classes\UserActionsComponent\Actions\Continuous\Vehicles\ActionVehicleHorn.c` | `scripts\4_World\...\ActionVehicleHorn.c` | 350 | `ActionVehicleHornShort`, `ActionVehicleHornLong` |
| `exp\scripts\scripts\4_World\Classes\UserActionsComponent\Actions\Interact\ActionGetInTransport.c` | `scripts\4_World\...\ActionGetInTransport.c` | 159 | Directional mounting via lateral dot product |
| `exp\scripts\scripts\4_World\Classes\UserActionsComponent\Actions\Interact\ActionGetOutTransport.c` | `scripts\4_World\...\ActionGetOutTransport.c` | 274 | Jump out while moving at speed > 10 km/h |
| `exp\scripts\scripts\4_World\Classes\UserActionsComponent\ActionConstructor.c` | `scripts\4_World\...\ActionConstructor.c` | 399 | Global action registration in the subsystem |

### 4. Graphical Interface and HUD (5_Mission)
| File in extraction (`exp\`) | In-game internal path | Total lines | Key analyzed symbols |
|---|---|---|---|
| `exp\scripts\scripts\5_Mission\GUI\Vehicles\MotorBikeHud.c` | `scripts\5_Mission\GUI\Vehicles\MotorBikeHud.c` | 248 | Tachometer, speedometer, fuel gauge, disabled warning indicators (handbrake, temperature) |

### 5. Vehicle Configurations and Animations
| File in extraction (`exp\`) | In-game internal path | Total lines | Key analyzed symbols |
|---|---|---|---|
| `exp\vehicles_singletrack\DZ\vehicles\singletrack\config.cpp` | `DZ\vehicles\singletrack\config.cpp` | 1099 | Full vanilla motorbike contract (`MotorbikeScript`, `Motorbike_01`, `Motorbike_02`, wheels, proxies) |
| `exp\vehicles_wheeled\DZ\vehicles\wheeled\config.cpp` | `DZ\vehicles\wheeled\config.cpp` | 8357 | Vanilla car config, new wheel parameters (`tyreRoughness`, `tyreLongitudinalFriction`, `tyreLateralFriction`) |
| `exp\anims_workspaces\DZ\anims\workspaces\player\player_main\Vehicles.agf` | `DZ\anims\workspaces\player\player_main\Vehicles.agf` | 3655 | Enfusion animation graph in plain text, `MotorBikeB` node, `MotorBikeSTM` state machine |
| `exp\anims_workspaces\DZ\anims\workspaces\player\player_main\player_main.ast` | `DZ\anims\workspaces\player\player_main\player_main.ast` | 1268 | `"Jawa_05"` and `"Jawa_Bitrak"` animation columns |
| `exp\anims_workspaces\DZ\anims\workspaces\player\player_main\player_main.asi` | `DZ\anims\workspaces\player\player_main\player_main.asi` | 6679 | `.anm` clip mapping for motorbike riding poses |
| `exp\sounds_hpp\DZ\sounds\hpp\config.cpp` | `DZ\sounds\hpp\config.cpp` | 183928 | Real CfgSoundShaders and CfgSoundSets of motorbikes |
| `exp\sounds_vehicles\DZ\sounds\vehicles\config.cpp` | `DZ\sounds\vehicles\config.cpp` | 31 | Exclusive CfgPatches without audio classes |

### 6. Difference Files (work\diffs)
Diff citations in this technical documentation use the exact path with a single underscore (`_`) separating directories:
- `work\diffs\scripts\3_Game_human.c.diff` (88 lines)
- `work\diffs\scripts\3_Game_Vehicles_Transport.c.diff` (657 lines: +438 / -40)
- `work\diffs\scripts\4_World_Entities_Vehicles_CarScript.c.diff` (2784 lines: +877 / -1155)
- `work\diffs\scripts\4_World_Entities_DayZPlayerImplementFallDamage.c.diff` (165 lines)
- `work\diffs\scripts\4_World_Classes_UserActionsComponent_ActionInput.c.diff` (323 lines)
- `work\diffs\configs\vehicles_wheeled.config.diff` (785 lines)
- There is no diff for `vehicles_singletrack`: `stable-1.29\vehicles_singletrack` contains no files (the PBO is new in 1.30).

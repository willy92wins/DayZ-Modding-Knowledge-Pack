# Sources — dayz-environment-hazards (1.30.164014)

Lane Q01. New skill. Digests: I (sandstorm/environment/medical), M (vehicle VFX / SurfaceInfo). Every digest citation was reopened in `exp\` except those marked UNVERIFIED.

## Ficheros reabiertos (1.30)

| Path under `E:\DayZ-Exp-Extract\1.30.164014\` | Purpose |
|---|---|
| `exp\scripts\scripts\3_Game\Sandstorm.c` | API proto, GetScriptedType |
| `exp\scripts\scripts\3_Game\Weather.c` | GetSandstorm :210, Obsolete noise :407-467 |
| `exp\scripts\scripts\3_Game\WorldData.c` | StartSandstorm, sun effect, dust settings, frequency |
| `exp\scripts\scripts\3_Game\CfgGameplayDataJson.c` | ITEM_SandstormData :433-451 |
| `exp\scripts\scripts\3_Game\CfgGameplayHandler.c` | GetSandstormFrequency :518-521 |
| `exp\scripts\scripts\3_Game\Enums\EAgents.c` | SILICOSIS 512, EYES 1024 |
| `exp\scripts\scripts\3_Game\constants.c` | AGT/DEF dust :545-550, ENVIRO shadow 30 s :760, moto/boat HC :792-798 |
| `exp\scripts\scripts\3_Game\PlayerConstants.c` | THERMAL_BIAS_* :203-210 |
| `exp\scripts\scripts\3_Game\SurfaceInfo.c` | dust protos :49-70 |
| `exp\scripts\scripts\3_Game\DustKickupEffects.c` | kickup |
| `exp\scripts\scripts\3_Game\PPEManager\Requesters\PPERSandstorm.c` | PPE |
| `exp\scripts\scripts\3_Game\Vehicles\Transport.c` | GetWeightCoef :475 |
| `exp\scripts\scripts\4_World\Systems\Sandstorm\ScriptedSandstormController.c` | shelter |
| `exp\scripts\scripts\4_World\Systems\Sandstorm\PlayerSandstormData.c` | per-player state |
| `exp\scripts\scripts\4_World\Classes\PlayerModifiers\eModifiers.c` | new IDs |
| `exp\scripts\scripts\4_World\Classes\PlayerModifiers\ModifiersManager.c` | eyes/heat sync bits |
| `exp\scripts\scripts\4_World\Classes\PlayerModifiers\Modifiers\HeatComfortMdfr.c` | feed bias |
| `exp\scripts\scripts\4_World\Classes\PlayerModifiers\Modifiers\diseases\HeatStroke.c` | 4 phases |
| `exp\scripts\scripts\4_World\Classes\PlayerModifiers\Modifiers\diseases\Silicosis.c` | thresholds |
| `exp\scripts\scripts\4_World\Classes\PlayerModifiers\Modifiers\diseases\IrritatedEyes.c` | widget ≥15 |
| `exp\scripts\scripts\4_World\Classes\PlayerModifiers\Modifiers\conditions\SandstormExposure.c` | transmission |
| `exp\scripts\scripts\4_World\Classes\PlayerModifiers\Modifiers\ImmuneSystem.c` | NTF_SICK |
| `exp\scripts\scripts\4_World\Classes\TransmissionAgents\Agents\SilicosisAgent.c` | die-off |
| `exp\scripts\scripts\4_World\Classes\TransmissionAgents\Agents\EyesIrritation.c` | die-off |
| `exp\scripts\scripts\4_World\Plugins\PluginBase\PluginTransmissionAgents.c` | AGT_AIRBOURNE_SOLID :414 |
| `exp\scripts\scripts\4_World\Classes\ThermalBiasHandler.c` | Add/resist/save |
| `exp\scripts\scripts\4_World\Classes\Environment\Environment.c` | shadow, sun, moto/boat |
| `exp\scripts\scripts\4_World\Classes\Worlds\Nasdara.c` | sand weather, sun table, dust |
| `exp\scripts\scripts\4_World\Classes\Worlds\ChernarusPlus.c` | no sun table, no StartSandstorm |
| `exp\scripts\scripts\4_World\Classes\UserActionsComponent\Actions\Continuous\ActionWashHeadWettingClothesBase.c` | wash |
| `exp\scripts\scripts\4_World\Classes\UserActionsComponent\Actions\Continuous\ActionWashHeadItemContinuous.c` | frozen bottle |
| `exp\scripts\scripts\4_World\Classes\UserActionsComponent\Actions\Continuous\ActionWetClothingInHandsBase.c` | wet clothes |
| `exp\scripts\scripts\4_World\Classes\ContaminatedArea\OilPitArea.c` | delay 3-10 |
| `exp\scripts\scripts\4_World\Classes\ContaminatedArea\EffectArea.c` | OnCEIterate, OIL_PIT=8, SurfaceRoadY |
| `exp\scripts\scripts\4_World\Entities\ScriptedEntities\Triggers\OilPitTrigger.c` | 20 HeatDamage |
| `exp\scripts\scripts\4_World\Classes\Dust\DustEffectCeilingHandler.c` | ceiling |
| `exp\scripts\scripts\4_World\Classes\Dust\DustEffectsManager.c` | manager |
| `exp\scripts\scripts\4_World\Entities\Effects\VehicleDust.c` | override params |
| `exp\scripts\scripts\4_World\Entities\Effects\EffWheelContact.c` | contact |
| `exp\scripts\scripts\4_World\Entities\Effects\WheelSmoke.c` | Obsolete SetSurface |
| `exp\scripts\scripts\4_World\Static\Surface.c` | Obsolete getters |
| `exp\scripts\scripts\4_World\Entities\Vehicles\Components\VehicleVFXComponent.c` | GetSurface |
| `exp\scripts\scripts\4_World\Entities\Vehicles\InheritedCars\Offroad_02.c` | weight 1.5 |
| `exp\scripts\scripts\4_World\Entities\ManBase\PlayerBase.c` | handler ctor :426, HasDisease :1119 |
| `exp\scripts\scripts\4_World\Classes\PlayerSymptoms\States\Secondary\SquintState.c` | eyes PPE |
| `exp\dz\DZ\data\config.cpp` | cfgWorlds Sandstorm :968 |
| `exp\dz\DZ\data\aiconfigs\config.cpp` | AIParams :19-27 |
| `exp\nasdara__data_nasdara\DZ\data_takistan\config.cpp` | CfgMods |
| `exp\nasdara__data_nasdara\DZ\data_takistan\basicDefines.hpp` | skinning |
| `exp\nasdara__data_nasdara\DZ\data_takistan\aiconfigs\config.cpp` | group beh |
| `exp\graphics\graphics\Materials\postprocess\sandstorm.emat` | SnowEffect |
| `work\pbo-listing-diff.txt:487` | 6 files Nasdara |
| `work\changelog-1.30-exp-modding.md` | OnCEIterate, AI native, known issues |

## No reabiertos (UNVERIFIED o skill hermana)

- `BoatScript.GetHeatComfortOverride` body (digest M).
- `Truck_01_Base.GetWeightCoef` / `MotorbikeScript` 0.25 (digest M).
- `PlayerBase.OnStoreSave` handler caller.
- Config of a vanilla mask with numeric `DEF_DUST_PARTICLE_*`.
- `GEWidgetsMetaDataEyeVeins.c` / `GEWidgetsMetaDataSquinting.c` (digest I names).
- `1.29` HeatComfortMdfr heat damage (digest I §1.5 claim; 1.30 no longer has it in high tick).

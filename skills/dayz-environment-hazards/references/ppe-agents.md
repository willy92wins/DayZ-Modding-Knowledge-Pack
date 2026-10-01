# Dust agents, PPE, and symptoms

## Enums

```c
// [EXACT] exp\scripts\scripts\3_Game\Enums\EAgents.c:14
	SILICOSIS 		= 512,
	EYES_IRRITATION	= 1024,
```

```c
// [EXACT] exp\scripts\scripts\3_Game\constants.c:545
const int AGT_AIRBOURNE_SOLID	= 15;

const int DEF_BIOLOGICAL			= 1;
const int DEF_CHEMICAL				= 2;
const int DEF_DUST_PARTICLE_BREATH	= 3;
const int DEF_DUST_PARTICLE_EYES	= 4;
```

Modifiers (`eModifiers.c:62-69`): `MDF_SANDSTORM_EXPOSURE_STATIC`, `_DYNAMIC`, `MDF_PARTICLES_BREATH`, `MDF_PARTICLES_EYES`, `MDF_HEAT_STROKE1..4`. Enum starts at `MDF_TEMPERATURE = 1`; do not use integers 59–66 from digest I (they are shifted: STATIC falls on 60 if counting from 1).

## Transmission

`SandstormExposureMdfrBase.TransmitAgents` uses `AGT_AIRBOURNE_SOLID` and does not transmit if unconscious (`SandstormExposure.c:45-50`). Base dose 1.0 agent/s (`:16-17`). Dynamic: dose × `GetIntensityForPlayer` (`:111-121`). Static (test zone): 1/s without intensity (`:76-80`).

`SandstormExposureDynamicMdfr.ActivateCondition`: storm activo e intensidad > 0 (`:101-104`).

PPE channel (digest I cited `:377`; the real case is `:414`):

```c
// [EXACT] exp\scripts\scripts\4_World\Plugins\PluginBase\PluginTransmissionAgents.c:414
			case AGT_AIRBOURNE_SOLID:
				switch (sourceAgents)
				{
					float protectionLevel = 0.0;
					Man man = Man.Cast(target);

					case eAgents.SILICOSIS:
						protectionLevel = GetProtectionLevelCachedEquipment(
							DEF_DUST_PARTICLE_BREATH,
							ECachedEquipmentItemCategory.MASK,
							man,
						);
						break;				
					case eAgents.EYES_IRRITATION:
						protectionLevel = GetProtectionLevelCachedEquipment(
							DEF_DUST_PARTICLE_EYES,
							ECachedEquipmentItemCategory.EYEWEAR|ECachedEquipmentItemCategory.MASK|ECachedEquipmentItemCategory.NVG,
							man,
						);
						break;
				}
```

`GetProtectionLevelCachedEquipment` (`:577-592`): query ATTACHMENT, `m_MaximumDepth = 2`, **sums** `GetProtectionLevel(type)` of each attachment.

## Agentes

`SilicosisAgent` (`SilicosisAgent.c:5-15`): `m_MaxCount = 1000`, `m_TransferabilityIn = 3.5`, `m_DieOffSpeed = 0.9`. `EyesIrritationAgent` (`EyesIrritation.c:5-15`): max 100, transfer 1.0, die-off 0.30. Ambos `GetDieOffSpeedEx` → 0 si inconsciente (`:18-23`).

## SilicosisMdfr (`MDF_PARTICLES_BREATH`)

Activa con count > 0 (`Silicosis.c:36-38`). Tick 5 s (`:33`).

| Threshold | Effect |
|---|---|
| remap from 200 | `HEAVY_BREATHING` (`:15, 88-106`) |
| ≥ 600 | stamina `DISEASE_PNEUMONIA` (`:3, 112-116`) |
| > 700 and count rising | `AddHealth(-HEALTH_LOSS * remap)` with `HEALTH_LOSS = 2.0` (`:13, 133-136`) |
| > 800 | `SYMPTOM_FAINT` fade + cyclic uncon 60–120 s, shock 25 (`:4, 193-218`) |

`OnActivate` ya encola `SYMPTOM_FAINT` (`:46-70`).

## IrritatedEyesMdfr (`MDF_PARTICLES_EYES`)

Activates with count > 0 (`IrritatedEyes.c:19-21`). Sync `MODIFIER_SYNC_PARTICLE_EYES`. Widget starting at 15 agents (`:79-88`).

## Squint and exposure

`SandstormExposureMdfrBase.OnActivate` encola `SYMPTOM_SQUINT` (`SandstormExposure.c:32-34`). `SquintSymptom.OnUpdateClient` resta protection `DEF_DUST_PARTICLE_EYES` en EYEWEAR|MASK (`SquintState.c:25-39`).

Cough: `HandleCoughing` checks `DEF_DUST_PARTICLE_BREATH` in EYEWEAR|MASK (not NVG) (`SandstormExposure.c:124-158`). Interval 25→3 s. Digest I said "mask cancels cough" — correct if `protectionLevel` covers intensity (`coughIntensity = Clamp(intensity - protection, 0, 1)`).

## Test zone

`SandstormZoneSmall_TESTONLY` activates/deactivates `MDF_SANDSTORM_EXPOSURE_STATIC` on enter/exit (`SandstormExposure.c:1-11`). Do not use this class in production.

## PPE item authoring [DESIGN]

In clothing `config.cpp`, declare `protection` / `Deflectors` equivalent to `DEF_DUST_PARTICLE_BREATH` and/or `_EYES` like the rest of `DEF_*`. The numeric value is consumed by `ItemBase.GetProtectionLevel`. Worn mesh is `dayz-clothing`. Do not copy protection values from digest: a vanilla mask `config.cpp` with those keys was not reopened in this lane.

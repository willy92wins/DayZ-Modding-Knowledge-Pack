# Agentes de polvo, PPE y síntomas

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

Modificadores (`eModifiers.c:62-69`): `MDF_SANDSTORM_EXPOSURE_STATIC`, `_DYNAMIC`, `MDF_PARTICLES_BREATH`, `MDF_PARTICLES_EYES`, `MDF_HEAT_STROKE1..4`. El enum empieza en `MDF_TEMPERATURE = 1`; no uses los enteros 59–66 del digest I (están desplazados: STATIC cae en 60 si se cuenta desde 1).

## Transmisión

`SandstormExposureMdfrBase.TransmitAgents` usa `AGT_AIRBOURNE_SOLID` y no transmite si inconsciente (`SandstormExposure.c:45-50`). Dosis base 1.0 agente/s (`:16-17`). Dinámico: dosis × `GetIntensityForPlayer` (`:111-121`). Estático (zona test): 1/s sin intensidad (`:76-80`).

`SandstormExposureDynamicMdfr.ActivateCondition`: storm activo e intensidad > 0 (`:101-104`).

Canal PPE (digest I citó `:377`; el case real es `:414`):

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

`GetProtectionLevelCachedEquipment` (`:577-592`): query ATTACHMENT, `m_MaximumDepth = 2`, **suma** `GetProtectionLevel(type)` de cada attachment.

## Agentes

`SilicosisAgent` (`SilicosisAgent.c:5-15`): `m_MaxCount = 1000`, `m_TransferabilityIn = 3.5`, `m_DieOffSpeed = 0.9`. `EyesIrritationAgent` (`EyesIrritation.c:5-15`): max 100, transfer 1.0, die-off 0.30. Ambos `GetDieOffSpeedEx` → 0 si inconsciente (`:18-23`).

## SilicosisMdfr (`MDF_PARTICLES_BREATH`)

Activa con count > 0 (`Silicosis.c:36-38`). Tick 5 s (`:33`).

| Umbral | Efecto |
|---|---|
| remap desde 200 | `HEAVY_BREATHING` (`:15, 88-106`) |
| ≥ 600 | stamina `DISEASE_PNEUMONIA` (`:3, 112-116`) |
| > 700 y count subiendo | `AddHealth(-HEALTH_LOSS * remap)` con `HEALTH_LOSS = 2.0` (`:13, 133-136`) |
| > 800 | fade `SYMPTOM_FAINT` + uncon cíclico 60–120 s, shock 25 (`:4, 193-218`) |

`OnActivate` ya encola `SYMPTOM_FAINT` (`:46-70`).

## IrritatedEyesMdfr (`MDF_PARTICLES_EYES`)

Activa con count > 0 (`IrritatedEyes.c:19-21`). Sync `MODIFIER_SYNC_PARTICLE_EYES`. Widget a partir de 15 agentes (`:79-88`).

## Squint y exposición

`SandstormExposureMdfrBase.OnActivate` encola `SYMPTOM_SQUINT` (`SandstormExposure.c:32-34`). `SquintSymptom.OnUpdateClient` resta protection `DEF_DUST_PARTICLE_EYES` en EYEWEAR|MASK (`SquintState.c:25-39`).

Tos: `HandleCoughing` mira `DEF_DUST_PARTICLE_BREATH` en EYEWEAR|MASK (no NVG) (`SandstormExposure.c:124-158`). Intervalo 25→3 s. Digest I dijo "máscara cancela tos" — correcto si `protectionLevel` cubre intensidad (`coughIntensity = Clamp(intensity - protection, 0, 1)`).

## Zona de test

`SandstormZoneSmall_TESTONLY` activa/desactiva `MDF_SANDSTORM_EXPOSURE_STATIC` al entrar/salir (`SandstormExposure.c:1-11`). No uses esta clase en producción.

## Autoría de ítem PPE [DESIGN]

En `config.cpp` del clothing, declara `protection` / `Deflectors` equivalentes a `DEF_DUST_PARTICLE_BREATH` y/o `_EYES` como el resto de `DEF_*`. El valor numérico lo consume `ItemBase.GetProtectionLevel`. La malla worn es `dayz-clothing`. No copies valores de protección de digest: no se reabrió un `config.cpp` de máscara vanilla con esas keys en esta lane.

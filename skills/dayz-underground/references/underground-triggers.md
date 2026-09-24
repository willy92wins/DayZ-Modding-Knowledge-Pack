# Triggers subterráneos: esquema y recetas (DayZ 1.30.164014 Exp)

Citas de `exp\scripts\scripts\…`, abiertas el 2026-09-24. `source_verified` salvo lo que se
marque `[DESIGN]` o sin verificar.

## Esquema de `cfgundergroundtriggers.json`

[EXACT][CLAIM-UG-TRIGGER-JSON-130] Raíz `{ "Triggers": [ … ] }`
(`3_Game\UndergroundAreaLoader.c:1-3`). Cada trigger (`JsonUndergroundAreaTriggerData`,
`:69-99`):

| Campo | Tipo | Para qué |
|---|---|---|
| `Comment` | string | nota libre (nuevo en 1.30) |
| `CustomSpawn` | bool | no se crea al arrancar: lo crea un objeto padre (ver §Triggers ligados a un objeto) |
| `Tag` | string | enlace con una entrada del Object Spawner o con un spawn manual |
| `ParentNetworkId` | int[2] | enlace con un objeto del mapa por su network id |
| `Position`, `Orientation`, `Size` | float[3] | caja del trigger |
| `EyeAccommodation` | float | adaptación de la vista; `1.0` sin breadcrumbs da tipo `OUTER` |
| `InterpolationSpeed` | float | velocidad de la transición |
| `UseLinePointFade` | bool | fundido simple entre los puntos de `Breadcrumbs` |
| `AmbientSoundType` | string | tipo de ambiente para el controlador de sonido |
| `AmbientSoundSet` | string | ambiente manual (Livonia usa `Underground_SoundSet`) |
| `Breadcrumbs` | array | puntos de transición; si hay alguno, el tipo es `TRANSITIONING` (32 como máximo) |

Cada breadcrumb (`JsonUndergroundAreaBreadcrumb`, `:36-51`): `Position` (float[3]),
`EyeAccommodation` (float), `UseRaycast` (bool), `Radius` (float; Livonia usa `-1`),
`LightLerp` (bool, solo con `UseLinePointFade`), `Comment` y `ExternalValueController`
(`Type` + `Params`; por ejemplo `BreadcrumbDoorStateController`, que toma el nombre de
selección de una puerta, `:53-67`).

El tipo del trigger lo decide `UndergroundTrigger.c:97-116`:

- con breadcrumbs, `TRANSITIONING`;
- sin ellos, `EyeAccommodation == 1.0` da `OUTER`;
- cualquier otro valor da `INNER`.

La presencia del jugador sale del tipo (`TranslateTriggerTypeToPresence`, `:190-203`).

## Carga y sincronización

1. **Fichero.** `UndergroundAreaLoader.GetData` busca primero
   `$mission:cfgundergroundtriggers.json`; si no está, avisa en el RPT y prueba
   `dz/worlds/<mundo>/ce/cfgundergroundtriggers.json` (`:105-125`).
2. **Arranque.** El servidor crea un `UndergroundTriggerCarrier` por trigger sin
   `CustomSpawn` (`SpawnAllTriggerCarriers`, `:135-154`, llamado en
   `5_Mission\mission\missionServer.c:91`).
3. **Sincronización.** Al conectar un jugador, el servidor le manda el JSON entero por
   `RPC_UNDERGROUND_SYNC` (`:174-177`; `missionServer.c:342,363`) y el cliente lo guarda
   (`:181-193`). El cliente no necesita tener el fichero.
4. **Local.** En partida local con `DIAG_DEVELOPER`, el cliente carga y crea los triggers
   él mismo (`5_Mission\mission\missionGameplay.c:112-117`).

Tope: `m_TriggerIndex` se sincroniza en `-1..4095` (`UndergroundTrigger.c:10`), así que
un JSON admite hasta 4096 triggers. En 1.29 eran 256.

## Triggers ligados a un objeto

Dos formas, las dos con `CustomSpawn = true`:

- **Objeto del mapa.** `ParentNetworkId` con el network id del objeto; el propio objeto
  llama a `JsonUndergroundTriggers.SpawnParentedTriggers(this)` (`:5-22`). Lo hacen
  `Land_WarheadStorage_Main` (`:72`) y `Land_WarheadStorage_Bunker_Facility` (`:16`).
- **Objeto colocado por el Object Spawner.**
  - La entrada del spawner (`ITEM_SpawnerObject`: `name`, `pos`, `ypr`, `scale`,
    `enableCEPersistency`, `customString`; `3_Game\ObjectSpawner.c:100-108`) lleva
    `"customString": "undergroundTriggerTag=TAG"`.
  - El spawner llama a `object.OnSpawnByObjectSpawner(item)` (`ObjectSpawner.c:63`).
  - La clase recorre los triggers `CustomSpawn` y crea los que tengan ese `Tag`
    (`Land_WarheadStorage_Bunker_Facility.c:62-94`); `customString` admite varias
    parejas separadas por `;`.
  - Esa lógica vive en las clases de Sakhal, no en una base común: una clase de mod
    tiene que escribirla.

Sin verificar: si `Position` de un trigger ligado es de mundo o relativa al padre. El
código crea el carrier en `data.GetPosition()` y después llama a `SetParent(parent)`
(`UndergroundAreaLoader.c:24-33`); cómo transforma eso la posición no está medido.

## Receta [DESIGN]: búnker de mod colocado con el Object Spawner

Sin probar. Sigue el patrón vanilla de Sakhal.

1. **Trigger en el JSON de la misión**, con `"CustomSpawn": true`, un `Tag` único y la
   caja del interior. Para una zona oscura sin transición: sin breadcrumbs y
   `EyeAccommodation` distinto de `1`, que da `INNER`.
2. **Entrada del Object Spawner** con `"customString": "undergroundTriggerTag=<Tag>"`.
3. **Clase script del búnker.** Sobrescribe `OnSpawnByObjectSpawner(ITEM_SpawnerObject item)`
   con el mismo recorrido que `Land_WarheadStorage_Bunker_Facility.c:62-94`, llamando a
   `JsonUndergroundTriggers.SpawnTriggerCarrier(this, index, triggerData)`.
4. **Agujero.** Si el búnker se abre al terreno, hace falta además el agujero
   (`CfgWorlds >> <mundo> >> Holes`, ver `SKILL.md`).

Un mod no puede añadir su propio fichero de triggers sin tocar el cargador: `GetData`
lee un único fichero. Un `modded class UndergroundAreaLoader` que añada los triggers del
mod a `m_JsonData` antes de `SyncDataSend` es la vía obvia; no está probada.

## Presencia y restricciones

Ver `SKILL.md` §Presencia bajo tierra. En resumen: el cliente calcula la presencia, en 1.30
la envía al servidor (`INPUT_UDT_UNDERGROUND_SYNC`) y dentro de un trigger `CanPlaceItem`
bloquea `disallowedTypesInUnderground`.

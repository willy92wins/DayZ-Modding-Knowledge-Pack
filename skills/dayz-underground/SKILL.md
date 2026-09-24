---
name: dayz-underground
description: >
  Use when: terrain holes, terrain hole, SurfaceIsHole, CfgWorlds Holes, tiles[],
  holes.cfg, hole in the terrain, agujero o hueco en el terreno, underground area,
  zona subterránea, bunker, búnker, tunnel, túnel, trench, trinchera, cave,
  irrigation tunnel, cfgundergroundtriggers.json, UndergroundTrigger, breadcrumbs,
  EyeAccommodation, EUndergroundPresence, INPUT_UDT_UNDERGROUND_SYNC, underground
  trigger editor, disallowedTypesInUnderground, bunker broadcast,
  cfgbunkerbroadcast.json, Buldozer MarkUnderground or CopyTileCoord. DayZ 1.30 Exp
  (1.30.164014). Not construction parts, rebuilding or code locks: dayz-basebuilding.
  Not the bunker-broadcast storage file: dayz-persistence. Not sandstorm or heat:
  dayz-environment-hazards.
---

# DayZ Underground (1.30 Exp)

Zonas bajo el terreno en DayZ 1.30 Experimental (build 1.30.164014): el agujero en el
terreno (*terrain holes*, nuevo en 1.30), los triggers subterráneos que oscurecen y
cambian el ambiente, el estado «bajo tierra» del jugador y lo que Badlands monta encima
(búnkeres anunciados por radio, entrada del túnel de riego).

Las citas `exp\scripts\scripts\…` son del `dta\scripts.pbo` de 1.30.164014, comparado
con el de 1.29. Todo lo marcado `source_verified` se abrió en esos ficheros. **Nada de
esta skill se ha probado todavía en el juego**: §Estado de verificación dice qué nivel
tiene cada afirmación y §Antes de diseñar sobre holes, cómo subirlo.

## El modelo: tres piezas

| Pieza | Qué es | Dónde se define | Quién lo usa |
|---|---|---|---|
| Agujero | celdas del heightmap sin terreno | `CfgWorlds >> <mundo> >> Holes` (config del mapa) | el motor, al cargar el mundo |
| Geometría | túnel o búnker colocado bajo la superficie | `.wrp` (Terrain Builder), Object Spawner o script | el motor |
| Triggers | cajas que oscurecen, cambian el sonido y marcan «bajo tierra» | `cfgundergroundtriggers.json` | el servidor las crea, el cliente aplica los efectos |

El agujero solo quita terreno: no crea ningún espacio. Qué ocurre si algo cae por un
agujero sin geometría debajo no está medido; diseña como si no hubiera suelo. Sin
triggers, dentro no oscurece.

## Terrain holes

### Formato

Entre los mapas vanilla legibles de 1.30.164014, solo Livonia tiene holes (Chernarus no;
Sakhal va cifrado): siete celdas en dos grupos, junto a las dos entradas del búnker de
Dambog. El config 1.29 del mismo mapa no los tiene.

```cpp
// [EXACT][CLAIM-UG-HOLES-SCHEMA-130] Addons\worlds_enoch.pbo > config.bin > CfgWorlds > Enoch (1.30.164014, pasado a texto con CfgConvert)
class Holes
{
	class Dambog            // un grupo = una subclase; el nombre es libre
	{
		tiles[]=
		{
			{118,195},{118,196},{118,197},
			{94,180},{95,180},{94,181},{95,181}
		};
	};
};
```

- Cada entrada de `tiles[]` es `{x, z}`: índices de celda del heightmap, no metros.
- El motor valida el rango: el código que lee `tiles` usa los mensajes
  `x (%d) out of range <0, %d)` y `y (%d) …` (cadenas de `DayZDiag_x64.exe` 1.30;
  detalle en `references/terrain-holes-evidence.md`).
- Cada grupo es una subclase, así que un mod podría añadir el suyo sin pisar el de
  Bohemia. **Sin probar**: que un parche de config de un mod sobre
  `CfgWorlds >> ChernarusPlus` abra agujeros es la primera hipótesis que hay que medir.

### Unidad: celda del heightmap

En Livonia la rejilla es de 2048 celdas de 6,25 m (12 800 m). Con ese tamaño, los dos
grupos caen sobre los triggers subterráneos vanilla de Dambog; con 5 m o 10 m no cae
ninguno (cuentas en la referencia):

- `{118, 195–197}` → X 737,5–743,75, Z 1218,75–1237,5: entrada principal.
- `{94–95, 180–181}` → cuadrado de 12,5 m en X 587,5–600, Z 1125–1137,5: segundo acceso.

Es `cross_checked` por ese encaje: no se ha leído el tamaño de celda en la cabecera del
`.wrp` (OPRW v32) y los demás mapas no están medidos. Calcula siempre
`celda = floor(coordenada / tamaño_de_celda)` con el tamaño de tu terreno.

### API de script

```c
// [EXACT][CLAIM-UG-SURFACEISHOLE-130] exp\scripts\scripts\3_Game\Global\Game.c:1203-1204
//! Returns whether tile at provided world coordinates is a hole.
proto native bool		SurfaceIsHole(float x, float z);
```

- Es la única API nueva de holes y es de solo lectura: no hay forma de abrir ni cerrar
  agujeros desde script en tiempo de juego.
- Ningún script vanilla 1.30 la llama.
- Sirve para no colocar nada donde no hay terreno: loot propio, puntos de spawn,
  hologramas propios.

### Dónde viven los datos

- `enoch.wrp` y `chernarusplus.wrp` pasan de OPRW v29 a v32 en 1.30 y crecen un 5 % los
  dos; Chernarus no tiene `Holes`. Ese cambio es de formato, no de agujeros: los holes
  están en el config del mundo (`cross_checked`).
- `exp\scripts\scripts\4_World\Classes\Hologram.c` es idéntico en 1.29 y 1.30: ninguna
  comprobación de colocación de kits sabe de holes.

## Flujo de autoría

- Buldozer 1.30 trae cuatro inputs nuevos: `UABuldLinkCamToTerrain`,
  `UABuldCopyTileCoord`, `UABuldMarkUnderground` y `UABuldRemoveUnderground`
  (`exp\bin\bin\constants.xml:282-285`, citado en `enforce-script-reference`; los dos
  últimos también aparecen en `DayZDiag_x64.exe` 1.30).
- Changelog 1.30, sección Terrain Builder: la cámara de Buldozer se puede desligar de la
  altura del terreno para editar bajo la superficie (tecla 8 por defecto), y cada objeto
  tiene un flag «underground» que evita que un objeto estático bajo el terreno se oculte
  por oclusión cuando debe verse.
- Ese flag es de Terrain Builder. No hay equivalente en script para objetos creados por
  el Object Spawner o por `CreateObject`, y si esos objetos se ocultan bajo el terreno
  está sin medir.
- Una DayZ Tools estable de abril de 2026 no contiene ninguna cadena de holes ni del flag
  (medido el 2026-09-24): hace falta un Terrain Builder posterior.
- Herramienta de terceros: Flynn's Terrain Tools (FTT, publicada el 2026-09-19).
  - Marca celdas y escribe `holes.cfg` junto a `layers.cfg`, donde según su guía lo leen
    Terrain Builder y Buldozer.
  - Añade el `#include` al `config.cpp` del terreno.
  - Buldozer lo relee en cada alt-tab.
  - Encaja con la cadena `\holes.cfg` que el motor usa en su función de carga del mundo,
    pero la ruta exacta y la recarga no están verificadas aquí.

## Triggers subterráneos

- Fichero: `$mission:cfgundergroundtriggers.json`; si no existe,
  `dz/worlds/<mundo>/ce/cfgundergroundtriggers.json`
  (`exp\scripts\scripts\3_Game\UndergroundAreaLoader.c:105-125`).
- El servidor crea las cajas (`UndergroundTriggerCarrier`) al arrancar la misión
  (`5_Mission\mission\missionServer.c:91`) y envía el JSON entero a cada cliente al
  conectar (`UndergroundAreaLoader.c:174-177`; `missionServer.c:342,363`). Un JSON propio
  de la misión funciona sin que el cliente tenga el fichero.
- Tipo de trigger (`4_World\Entities\ScriptedEntities\Triggers\UndergroundTrigger.c:97-116`):
  - con `Breadcrumbs` es `TRANSITIONING` (32 como máximo);
  - sin ellos, `EyeAccommodation == 1.0` da `OUTER`;
  - cualquier otro valor da `INNER`.
- [EXACT][CLAIM-UG-TRIGGER-LIMIT-130] Tope de 4096 triggers por JSON: `m_TriggerIndex` se
  sincroniza en `-1..4095` (`UndergroundTrigger.c:10`); en 1.29 era `-1..255`.
- Triggers ligados a un objeto (`CustomSpawn`): por `ParentNetworkId` para objetos del
  mapa, o por `Tag`.
  - Patrón vanilla para una estructura colocada por el Object Spawner: su entrada del
    spawner lleva `"customString": "undergroundTriggerTag=TAG"`.
  - La clase, en `OnSpawnByObjectSpawner`, crea los triggers cuyo `Tag` coincide
    (`4_World\Entities\Building\Underground\Land_WarheadStorage_Bunker_Facility.c:62-94`;
    `3_Game\ObjectSpawner.c:63,107`).
  - Esa lógica vive en las clases de Sakhal, no en una base común: una clase de mod
    tiene que implementarla.
- Editor in-game, nuevo en 1.30: `LCTRL+/`, solo en DayZDiag y en partida local.
  - Doble clic crea un trigger; edita cajas y breadcrumbs.
  - Exporta a `$mission:cfgundergroundtriggers.json` y deja una copia
    `…json.backup-<fecha>`.
  - Citas: `4_World\Plugins\PluginBase\PluginUndergroundTriggerManager.c:1,360,821,922`;
    `PluginKeyBinding.c:55`. Más detalle en `dayz-mod-workflow`.
- Esquema completo del JSON y receta del trigger con `Tag`: `references/underground-triggers.md`.

## Presencia bajo tierra

- `EUndergroundPresence`: `NONE`, `OUTER`, `TRANSITIONING`, `FULL`
  (`4_World\Classes\UndergroundHandlerClient.c:1-7`). La calcula el cliente según el
  trigger en el que está (`:470-475`).
- [EXACT][CLAIM-UG-PRESENCE-SYNC-130] En 1.30 el cliente la envía al servidor.
  - `SetUnderground` manda `INPUT_UDT_UNDERGROUND_SYNC`
    (`4_World\Entities\ManBase\PlayerBase.c:2853-2865`).
  - El servidor la acepta en `OnInputUserDataProcess` solo con una comprobación de rango
    (`:6531`, `:6557-6563`).
  - En 1.29 el valor solo existía en el cliente.
- Consecuencia: el servidor ya conoce la presencia. Antes, cualquier comprobación de
  servidor que la leyera veía `NONE`.
- Una de esas comprobaciones es `CanPlaceItem` (`PlayerBase.c:2834-2846`, llamado desde
  `Hologram.c:438`): dentro de un trigger bloquea los tipos de
  `disallowedTypesInUnderground`.
  - Por defecto: `FenceKit`, `TerritoryFlagKit` y `WatchtowerKit`
    (`3_Game\CfgGameplayDataJson.c:229-232`).
  - Se configura en `cfggameplay.json` > `BaseBuildingData` > `HologramData`.
- El valor lo decide el cliente: el servidor no lo recalcula.

## Badlands en los scripts de 1.30

- **Búnkeres anunciados por radio.**
  - Clases `Land_Bunker_Basement_*` y `Land_Bunker_Shelter_*`
    (`4_World\Entities\Building\Bunker.c:289-294`), con cerradura de código.
  - La radio emite coordenadas y código en Morse.
  - Se configuran en `cfgbunkerbroadcast.json`, en `$mission:` o en
    `dz/worlds/<mundo>/ce/` (`3_Game\CfgBunkerBroadcastHandler.c:5,23-27`), más
    `bunkerBroadcastEnabled` en `cfggameplay.json` (`CfgGameplayDataJson.c:193`).
  - El fichero de estado lo cubre `dayz-persistence`.
- **Túnel de riego.** `Land_IrrigationTunnel_Entrance_01` está en
  `4_World\Entities\Building\Rebuildable\` (`IrrigationTunnel_Entrance.c:1-11`): la
  entrada es reconstruible, y su spawn de depuración le mete palos y cuerda. La
  reconstrucción la cubre `dayz-basebuilding`.
- Los configs y modelos de Nasdara no vienen en la 1.30 Exp: solo sus scripts (medido el
  2026-09-24 sobre los PBO sin cifrar).
- Bohemia (Dev Blog Recap 2, Steam, 2026-09-22): las instalaciones subterráneas de
  Badlands usan el sistema de terrain holes, que estará disponible para otros mapas y
  para la comunidad de modding.

## Estado de verificación

| Afirmación | Nivel |
|---|---|
| Formato `Holes`/`tiles[]`, `SurfaceIsHole`, sincronización de presencia, tope de triggers, esquema del JSON | `source_verified` |
| Una entrada de `tiles[]` es una celda del heightmap; 6,25 m en Livonia | `cross_checked` (encaje con los triggers) |
| Los holes viven en el config, no en el `.wrp` | `cross_checked` (el `.wrp` crece igual con y sin holes) |
| Cómo se ve y colisiona un agujero, qué pasa al caer por él, IA y navmesh | `unverified` |
| Un mod de solo config abre holes en un mapa vanilla | `unverified` (hipótesis) |
| `holes.cfg` junto a `layers.cfg` y recarga en alt-tab | `unverified` (terceros: FTT) |
| Efecto de `ECE_OBJECT_SPAWNER` | `unverified` |

## Antes de diseñar sobre holes

Cada prueba sube una fila de §Estado de verificación. Juntas caben en una sola sesión de
DayZDiag 1.30 (`dayz-test-ingame`, `dayz-mcp-verify`):

1. **Livonia vanilla.** `g_Game.SurfaceIsHole(740, 1225)` debe dar `true` (celda
   `{118,196}`) y `g_Game.SurfaceIsHole(1000, 1000)` `false`. Una captura desde fuera y
   otra desde dentro del agujero.
2. **Mod de solo config.** Añade un grupo propio en `CfgWorlds >> ChernarusPlus >> Holes`
   y repite la comprobación en su celda.
3. **Geometría del mod.** Coloca un objeto con el Object Spawner bajo ese agujero y
   comprueba que se ve desde dentro y desde fuera, y que colisiona.
4. **Caída.** Suelta un objeto y entra con un personaje en un agujero sin geometría.

## Delegaciones

| Tema | Skill |
|---|---|
| Partes construibles, reconstrucción, cerraduras | `dayz-basebuilding` |
| Fichero de estado del bunker broadcast | `dayz-persistence` |
| Editor de triggers dentro del flujo general del mod | `dayz-mod-workflow` |
| Inputs de Buldozer y API de Enforce 1.30 | `enforce-script-reference` |
| Lanzar el juego y verificar con capturas | `dayz-test-ingame` + `dayz-mcp-verify` |
| Tormenta de arena y calor de Nasdara | `dayz-environment-hazards` |

## Referencias

- `references/terrain-holes-evidence.md`: cadenas nuevas del motor y sus referencias en el
  código, diff del config de Livonia, cuentas del tamaño de celda, `.wrp` v29→v32 y fuentes
  oficiales y de terceros.
- `references/underground-triggers.md`: esquema completo de `cfgundergroundtriggers.json`,
  receta del trigger con `Tag` y presencia bajo tierra.

## LO QUE ESTA SKILL NO PUDO VERIFICAR

- Ningún comportamiento en el juego: render, colisión, oclusión, caída, IA y navmesh.
- El tamaño de celda de cualquier mapa que no sea Livonia, y el de Livonia leído de la
  cabecera del `.wrp`.
- Sakhal: su mundo va en un `.ebo` cifrado y no se pudo leer.
- Dónde busca exactamente el motor `holes.cfg` y si un mod de solo config abre agujeros.
- Qué hace el motor con `ECE_OBJECT_SPAWNER`.

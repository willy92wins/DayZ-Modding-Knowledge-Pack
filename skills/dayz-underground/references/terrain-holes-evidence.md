# Terrain holes: evidencia (DayZ 1.30.164014 Exp)

Todo lo de esta página se midió el 2026-09-24 comparando la instalación 1.30.164.014 Exp
con la 1.29 estable. Nada se ha probado en el juego.

## Cómo reproducirlo

1. Extrae `dta\scripts.pbo`, `Addons\worlds_enoch.pbo` y `Addons\worlds_chernarusplus.pbo`
   de las dos versiones (cualquier extractor de PBO; las entradas no van comprimidas).
2. Pasa cada `config.bin` a texto con `CfgConvert.exe -txt` (DayZ Tools) y compáralos.
3. Busca cadenas en `DayZDiag_x64.exe` de las dos versiones (ASCII y UTF-16) y diferéncialas.
4. Para ver qué código usa cada cadena, busca instrucciones `lea`/`mov r64, [rip+disp32]`
   de `.text` que apunten a su RVA y lista las demás cadenas referenciadas en una ventana
   de ±0x600 bytes. Las RVA son de esta build y cambian con cada una.

## Cadenas nuevas del motor

En `DayZDiag_x64.exe` 1.30.164.014 aparecen cuatro cadenas relacionadas que no están en el
ejecutable 1.29 (el resto de apariciones de «hole» son de Recast, el generador de navmesh,
y ya existían):

| Cadena | Dónde se usa (RVA de la referencia) | Cadenas cercanas en esa función |
|---|---|---|
| `\holes.cfg` | 0x792cb4 | `CfgWorlds` (+1429), `DefaultWorld` (+1474): carga del mundo |
| `tiles` | 0x6655e3 | `Holes` (+1308) |
| `Holes` | 0x665aff | `tiles` (−1308), `y (%d) out of range <0, %d)` (+1349), `x (%d) out of range <0, %d)` (+1374) |
| `Holes` | 0x71b1f2 | `minTreesInForestSquare` (−1358), `minRocksInRockSquare` (−1203): parámetros de `CfgWorlds` |
| `SurfaceIsHole` | 0xc20528 | tabla de nativas de `CGame` (`SurfaceY`, `SurfaceRoadY`, `GetSurfaceInfoOn`…) |

En `.rdata`, `\holes.cfg` va justo antes de los mensajes de pantalla de carga («Preparing
surface materials», «Extruding hills and valleys»…) y justo después de las acciones de
Buldozer `UABuldMarkUnderground` y `UABuldRemoveUnderground`.

Lectura, marcada como inferencia: un código recorre `Holes`, lee `tiles` y valida cada
`x`/`z` contra el tamaño de la rejilla; `Holes` se lee también como parámetro del mundo en
`CfgWorlds`; y existe una ruta que carga un fichero `holes.cfg` al cargar el mundo. No se
ha desensamblado para ver cómo se construye esa ruta.

## Config de Livonia: 1.29 frente a 1.30

`Addons\worlds_enoch.pbo > config.bin`, pasado a texto. Diferencias entre versiones:

- `class Holes` nueva dentro de `CfgWorlds > Enoch`, entre `OutsideTerrain` y `Grid`, con
  un único grupo `Dambog` de siete celdas (el bloque está en el `SKILL.md`).
- `hasOcean=0` nuevo en la misma clase del mundo.

`Addons\worlds_chernarusplus.pbo > config.bin` 1.30 no contiene ni `Holes` ni `tiles`.
El mundo de Sakhal va en `sakhal\Addons\worlds_sakhal.ebo`, cifrado, y no se pudo leer.
`worlds_enoch_ce.pbo > cfgundergroundtriggers.json` es idéntico byte a byte en 1.29 y 1.30:
los agujeros no llegaron con triggers nuevos.

## Tamaño de celda en Livonia: 6,25 m

Livonia mide 12 800 m. Con 2048 celdas, cada una mide 6,25 m. Posición de las celdas de
`Dambog` según el tamaño supuesto, frente a los triggers subterráneos vanilla de Dambog
(`cfgundergroundtriggers.json` de `worlds_enoch_ce.pbo`, 8 triggers en X 584,6–749,7 y
Z 1131,0–1229,1):

| Grupo de celdas | Con 5 m | Con 6,25 m | Con 10 m |
|---|---|---|---|
| `{118, 195–197}` | X 590–595, Z 975–990 | X 737,5–743,75, Z 1218,75–1237,5 | X 1180–1190, Z 1950–1980 |
| `{94–95, 180–181}` | X 470–480, Z 900–910 | X 587,5–600, Z 1125–1137,5 | X 940–960, Z 1800–1820 |

Triggers con los que coincide la columna de 6,25 m:

- Entrada principal: triggers en (749,7; 533,5; 1228,5) y (735,0; 533,7; 1229,1), de
  15 × 5,6 × 10,8 m.
- Segundo acceso: trigger en (593,7; 588,75; 1131,8), de 11 × 22,3 × 11,6 m.

Con 5 m y con 10 m ningún grupo cae dentro del rango de los triggers. El encaje de dos
grupos independientes es lo que sostiene el nivel `cross_checked`. La cabecera del `.wrp`
(OPRW v32) no se interpretó, y el tamaño de celda de otros mapas no está medido.

## El `.wrp` cambia igual con y sin holes

| Mapa | 1.29 | 1.30 | Diferencia | ¿Tiene `Holes`? |
|---|---|---|---|---|
| ChernarusPlus | OPRW v29, 223 653 986 B | OPRW v32, 235 121 528 B | +5,1 % | no |
| Enoch (Livonia) | OPRW v29, 226 053 187 B | OPRW v32, 237 263 513 B | +5,0 % | sí |

Los dos pasan a v32 y crecen lo mismo aunque solo uno tenga agujeros: el cambio del `.wrp`
es de formato. Esto apoya que los holes vivan en el config; no descarta que el `.wrp`
guarde además algo relacionado (por ejemplo, el flag «underground» por objeto).

## Fuentes externas

- **Changelog oficial 1.30.164014.** El post del foro está en
  `forums.dayz.com/topic/266385`, detrás de Cloudflare; se leyó la copia de mydayz.eu.
  - La sección MODDING añade «Terrain holes», sin más detalle.
  - La sección TERRAIN BUILDER añade la cámara de Buldozer desligada del terreno para
    editar bajo la superficie (tecla 8), un input para ligarla y desligarla, que ese
    toggle afecte también a los objetos y el flag «underground» por objeto contra la
    oclusión.
- **Dev Blog Recap 2 (anuncio de Steam, 2026-09-22).** Entre lo que llega con Badlands:
  instalaciones e infraestructura subterránea con el nuevo sistema de terrain holes,
  disponible también para otros mapas y para la comunidad de modding, y señales de radio
  en Morse que llevan a refugios subterráneos.
- **Flynn's Terrain Tools (terceros, `github.com/Naviata/FTT-Releases`, 2026-09-19/20).**
  Solo publica binarios, sin código fuente. Según su guía `guide/holes.md`:
  - su «Hole Generator» marca celdas de la rejilla del heightfield;
  - escribe `holes.cfg` junto a `layers.cfg`, con una clase por grupo;
  - añade el `#include` al `config.cpp` del terreno;
  - Buldozer relee el fichero en cada alt-tab;
  - su guía general avisa de que un Terrain Builder más nuevo pide una columna de flag
    «underground» en las importaciones de objetos.

  Nada de esto se ha verificado aquí. No se ejecutó su binario.

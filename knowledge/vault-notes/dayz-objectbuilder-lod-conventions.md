# DayZ Object Builder — convenciones de LOD, selecciones y named properties (verificado vanilla)

> Verificado 2026-07-06 debinarizando 9 modelos vanilla (ODOL v54) con un
> conversor ODOL→MLOD externo + cross-check con A3OB al importar en Blender. Nace de validar
> el snippet aproximado de la wiki DayZ (`Doors_on_buildings`, `Ladders_on_buildings`,
> `LOD`): los nombres EXACTOS difieren de lo que la wiki transcribe (DZ-R2.1: el wiki es
> hint, no fact). `[EXACT]` = medido en vanilla en esta sesión; `[WIKI]` = wiki-only, no
> observado en los samples (tratar como hipótesis hasta ver un sample que lo use).
>
> Modelos inspeccionados: ladders `residential/misc/ladder.p3d`, `ladder_half.p3d`,
> `furniture/various/ladder_a_wood.p3d`, `Proxy_BuildingParts/ladders/ladder_long_proxy.p3d`,
> `ladder_top_proxy.p3d`, `residential/offices/proxy/ladderlong.p3d`; edificios
> `industrial/garages/garage_small.p3d`, `industrial/farms/barn_wood1.p3d`, `farm_cowsheda.p3d`.

## Tabla de resoluciones de LOD [EXACT]

Fuente autoritativa: `py3d` fork `LOD_RESOLUTIONS` (`__init__.py:68-76`, `classify_lod_resolution()`)
+ observado en los 9 modelos + confirmado por A3OB al leer `Crate_Wooden.p3d` (mismas signatures).

| LOD | resolution | notas |
|---|---|---|
| Visual (Resolution) | `0 .. <1e3` | LOD0 = 0 ó 1; sucesivos 2,3,4… (más alto = más basto) |
| ShadowVolume | `1e4 .. 2e4` | p.ej. 10000, 11000 |
| **Geometry** | `1e13` | colisión; lleva `class=house`, `ComponentXX` |
| **Memory** | `1e15` | puntos: ejes de puerta, acciones, sonido, loot |
| LandContact | `2e15` | |
| **Roadway** | `3e15` | superficie caminable; DEBE existir bajo los memory points de ladder |
| Paths | `4e15` | AI pathfinding: `posXX`/`inXX` |
| HitPoints | `5e15` | |
| **ViewGeometry** | `6e15` | oclusión |
| **FireGeometry** | `7e15` | balística/daño |

Tolerancia de clasificación: `|res - canon| <= 0.05*canon` (`LOD_RELATIVE_TOLERANCE`).

## Named properties [EXACT]

- **Geometry LOD de edificios**: `class=house`, `map=building`, `damage=no`.
- **Visual LODs**: `lodnoshadow=1` (confirma el claim wiki "Resolution LOD default LodNoShadow=1").
- **ViewGeometry**: `canocclude=1`.
- **Props/proxies sueltos**: `autocenter=0`, `drawimportance=N` (p.ej. 0.02).

## Componentes de colisión [EXACT]
Nombrados `component01`, `component02`… (el ODOL los guarda en minúscula; Object Builder
espera `ComponentNN`, case-sensitive al autorar). Presentes en Geometry, ViewGeometry y
FireGeometry. FireGeo puede tener decenas (30–570 según complejidad del modelo).

## Puertas [EXACT] — corrige el genérico "doorX" de la wiki

Esquema real de selecciones de una puerta N (garage_small, barn_wood1, farm_cowsheda):
- `doorsN` — la geometría de la hoja (en TODOS los LODs relevantes: visual, geometry, memory,
  view_geometry, fire_geometry, hitpoints). Confirma wiki "animated in ALL relevant LODs".
- `doorsN_axis` — (Memory LOD) eje de rotación.
- `doorsN_action` — (Memory LOD) punto de acción/interacción.
- Puertas gemelas: `doorstwinN` + `twinN_action` (o `doorstwinN_action`).

Ejemplos medidos: garage_small Memory = `doors1, doors1_axis, doors2, doors2_axis, doorstwin1,
twin1_action`; barn_wood1 Memory = `doorsN, doorsN_axis, doorsN_action` para N=1..6.
Config: `class Doors` en el config ↔ `source` del model.cfg; edificio hereda `HouseNoDestruct`;
clase de config `land_<modelname>` autolinkea modelo↔config; `class=house` en Geometry. La wiki
añade `bounding="selección"` (volumen abierto para que raycast/balística sigan la puerta abierta)
y el estándar "casi todas las puertas DayZ son 120×220 cm" [WIKI — no medido aquí].

## Escaleras [EXACT] — DOS esquemas coexisten (verificado: 6 ladder-props + 3 edificios multi-piso)

La convención depende de si el ladder es un prop suelto o va integrado en un edificio:

- **Ladder-prop suelto climbable** (`ladder.p3d`, `ladderlong.p3d`): Memory = `start`/`end` (o
  `start1`/`end1`), Geometry con `component01` + `class=house`, un **Roadway (3e15)**, subible.
- **Ladder INTEGRADA en edificio** (verificado en `lighthouse.p3d`, `mil_fortified_nest_watchtower.p3d`,
  `cementworks_silobig1a.p3d`): SÍ usa el esquema `ladderN_*` de la wiki — `ladderN` (selección base +
  componente en ViewGeometry), y en Memory LOD `ladderN_bottom_front` (entrada inferior),
  `ladderN_top_front` (salida superior), `ladderN_middle_right`(+`_align`) para entradas laterales de
  pisos intermedios (visto en el silo multi-piso), + `ladderN_con`/`ladderN_con_dir`/`ladderN_dir`
  (conexión/dirección). `N` empieza en 1. Roadway LOD presente.
- **Proxy ladders** (`ladder_long_proxy`, `ladder_top_proxy`): selección con el nombre de la pieza
  (`long`, `top`), Geometry vacío `autocenter=0` (se insertan en el edificio host).

Conclusión: el `ladderN_*` del wiki es CORRECTO para ladders de EDIFICIO; los props sueltos usan
`start`/`end`. (Corregido 2026-07-06: una versión previa de esta nota decía "ladderN_ no observado" —
solo se había mirado props sueltos; los edificios multi-piso sí lo usan.)

## Faces: quads nativos (FaceType 3/4) [EXACT — código py3d]
El MLOD guarda hasta 4 vertex-slots por `LodFace`; py3d `Face.read`/`Face.write` (`__init__.py:1034-1055`)
manejan `num_vertices ∈ {3,4}` nativamente (relleno de 16 bytes solo para triángulos). → py3d
**preserva quads** en el round-trip; la salida quad de un retopo puede escribirse directa sin
re-triangular. Caveat: el viewer/inspector triangula al exportar a glTF (solo visualización), y el
binarize a ODOL (AddonBuilder) preservando quads queda por confirmar con un test de binarizado.

## Paths LOD (AI pathfinding) [EXACT]
`garage_small` paths = `pos1, pos2, in1, in2, actionbegin1, actionend1`. Confirma wiki:
`posXX` = stop-vertices (usables por `buildingpos`), `inXX` = entry/access points. `actionbeginN`/
`actionendN` acotan acciones de AI.

## Memory LOD — extras no documentados en la wiki [EXACT]
Además de door/ladder points: `lootcenter`/`lootaround` (spawn de loot) y `sound_*`
(posición de sonido ambiental, p.ej. `sound_rainobjectinner3metal2_1`).

## Método de verificación (reproducible)
`odol_reader.ODOL.from_file(<p3d>)` → iterar `odol.lods`; por LOD leer `lod.resolution`
(→ `py3d.classify_lod_resolution`), `lod.named_selections[].name`, `lod.named_properties`
(tuplas `(key,value)`). Scripts en el scratchpad de la sesión (`inspect_p3d.py`,
`inspect_doors.py`, `inspect_full.py`). Caveat: usar Object Builder/A3OB si se quiere autorar;
el conversor externo invierte winding y su membresía de selección tiene caveats (SP-001), pero los
NOMBRES de selección y named properties se leen fielmente.

## Cross-ref
- [[dayz-technical-notes]] / `DAYZ_TECHNICAL_NOTES.md` (LODs canónicos).
- Skills `dayz-model-pipeline` (`references/lods-and-geometry.md`, `memory-and-selections.md`),
  `dayz-p3d-audit` (ComponentXX Killer #2), `dayz-animation-pipeline` (class Doors, source).
- [[dayz-wiki-systems-reference]] (sistemas wiki de gameplay/entorno, [TBD-verify]).
- Origen: sesión 2026-07-06 (verificación de los deep-research P3D + Wiki Sweep).

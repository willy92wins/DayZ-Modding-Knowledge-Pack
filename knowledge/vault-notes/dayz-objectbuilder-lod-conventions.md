# DayZ Object Builder — LOD conventions, selections, and named properties (vanilla verified)

> Verified 2026-07-06 debinarizing 9 vanilla models (ODOL v54) with an
> external ODOL→MLOD converter + cross-check with A3OB when importing into Blender. Born from validating
> the approximate snippet from DayZ wiki (`Doors_on_buildings`, `Ladders_on_buildings`,
> `LOD`): EXACT names differ from what the wiki transcribes (DZ-R2.1: wiki is
> hint, not fact). `[EXACT]` = measured in vanilla in this session; `[WIKI]` = wiki-only, not
> observed in samples (treat as hypothesis until seeing a sample using it).
>
> Inspected models: ladders `residential/misc/ladder.p3d`, `ladder_half.p3d`,
> `furniture/various/ladder_a_wood.p3d`, `Proxy_BuildingParts/ladders/ladder_long_proxy.p3d`,
> `ladder_top_proxy.p3d`, `residential/offices/proxy/ladderlong.p3d`; buildings
> `industrial/garages/garage_small.p3d`, `industrial/farms/barn_wood1.p3d`, `farm_cowsheda.p3d`.

## LOD resolution table [EXACT]

Authoritative source: `py3d` fork `LOD_RESOLUTIONS` (`__init__.py:68-76`, `classify_lod_resolution()`)
+ observed in the 9 models + confirmed by A3OB when reading `Crate_Wooden.p3d` (same signatures).

| LOD | resolution | notes |
|---|---|---|
| Visual (Resolution) | `0 .. <1e3` | LOD0 = 0 or 1; successive 2,3,4… (higher = coarser) |
| ShadowVolume | `1e4 .. 2e4` | e.g. 10000, 11000 |
| **Geometry** | `1e13` | collision; carries `class=house`, `ComponentXX` |
| **Memory** | `1e15` | points: door axes, actions, sound, loot |
| LandContact | `2e15` | |
| **Roadway** | `3e15` | walkable surface; MUST exist beneath ladder memory points |
| Paths | `4e15` | AI pathfinding: `posXX`/`inXX` |
| HitPoints | `5e15` | |
| **ViewGeometry** | `6e15` | occlusion |
| **FireGeometry** | `7e15` | ballistics/damage |

Classification tolerance: `|res - canon| <= 0.05*canon` (`LOD_RELATIVE_TOLERANCE`).

## Named properties [EXACT]

- **Geometry LOD de edificios**: `class=house`, `map=building`, `damage=no`.
- **Visual LODs**: `lodnoshadow=1` (confirma el claim wiki "Resolution LOD default LodNoShadow=1").
- **ViewGeometry**: `canocclude=1`.
- **Props/proxies sueltos**: `autocenter=0`, `drawimportance=N` (p.ej. 0.02).

## Collision components [EXACT]
Named `component01`, `component02`… (ODOL stores them lowercase; Object Builder
expects `ComponentNN`, case-sensitive when authoring). Present in Geometry, ViewGeometry, and
FireGeometry. FireGeo can have dozens (30–570 depending on model complexity).

## Doors [EXACT] — corrects generic "doorX" from wiki

Actual selection scheme for door N (garage_small, barn_wood1, farm_cowsheda):
- `doorsN` — leaf geometry (in ALL relevant LODs: visual, geometry, memory,
  view_geometry, fire_geometry, hitpoints). Confirms wiki "animated in ALL relevant LODs".
- `doorsN_axis` — (Memory LOD) rotation axis.
- `doorsN_action` — (Memory LOD) action/interaction point.
- Twin doors: `doorstwinN` + `twinN_action` (or `doorstwinN_action`).

Measured examples: garage_small Memory = `doors1, doors1_axis, doors2, doors2_axis, doorstwin1,
twin1_action`; barn_wood1 Memory = `doorsN, doorsN_axis, doorsN_action` for N=1..6.
Config: `class Doors` in config ↔ `source` in model.cfg; building inherits `HouseNoDestruct`;
config class `land_<modelname>` auto-links model↔config; `class=house` in Geometry. The wiki
adds `bounding="selection"` (opened volume so raycast/ballistics follow the open door)
and the standard "almost all DayZ doors are 120×220 cm" [WIKI — not measured here].

## Escaleras [EXACT] — DOS esquemas coexisten (verificado: 6 ladder-props + 3 edificios multi-piso)

The convention depends on whether the ladder is a loose prop or integrated into a building:

- **Climbable loose ladder-prop** (`ladder.p3d`, `ladderlong.p3d`): Memory = `start`/`end` (or
  `start1`/`end1`), Geometry with `component01` + `class=house`, a **Roadway (3e15)**, climbable.
- **Ladder INTEGRATED into building** (verified in `lighthouse.p3d`, `mil_fortified_nest_watchtower.p3d`,
  `cementworks_silobig1a.p3d`): DOES use the `ladderN_*` scheme from wiki — `ladderN` (base selection +
  component in ViewGeometry), and in Memory LOD `ladderN_bottom_front` (bottom entrance),
  `ladderN_top_front` (top exit), `ladderN_middle_right`(+`_align`) for lateral entrances on
  intermediate floors (seen on multi-story silo), + `ladderN_con`/`ladderN_con_dir`/`ladderN_dir`
  (connection/direction). `N` starts at 1. Roadway LOD present.
- **Proxy ladders** (`ladder_long_proxy`, `ladder_top_proxy`): selection named after the piece
  (`long`, `top`), empty Geometry `autocenter=0` (inserted into host building).

Conclusion: `ladderN_*` from wiki is CORRECT for BUILDING ladders; loose props use
`start`/`end`. (Corrected 2026-07-06: a previous version of this note stated "ladderN_ not observed" —
only loose props had been looked at; multi-story buildings do use it.)

## Faces: native quads (FaceType 3/4) [EXACT — py3d code]
MLOD stores up to 4 vertex-slots per `LodFace`; py3d `Face.read`/`Face.write` (`__init__.py:1034-1055`)
handle `num_vertices ∈ {3,4}` natively (16-byte padding only for triangles). → py3d
**preserves quads** in round-trip; quad output of a retopo can be written directly without
re-triangulating. Caveat: the viewer/inspector triangulates when exporting to glTF (visualization only), and
binarizing to ODOL (AddonBuilder) preserving quads remains to be confirmed with a binarization test.

## Paths LOD (AI pathfinding) [EXACT]
`garage_small` paths = `pos1, pos2, in1, in2, actionbegin1, actionend1`. Confirma wiki:
`posXX` = stop-vertices (usables por `buildingpos`), `inXX` = entry/access points. `actionbeginN`/
`actionendN` acotan acciones de AI.

## Memory LOD — extras not documented in wiki [EXACT]
Besides door/ladder points: `lootcenter`/`lootaround` (loot spawn) and `sound_*`
(ambient sound position, e.g. `sound_rainobjectinner3metal2_1`).

## Verification method (reproducible)
`odol_reader.ODOL.from_file(<p3d>)` → iterate `odol.lods`; per LOD read `lod.resolution`
(→ `py3d.classify_lod_resolution`), `lod.named_selections[].name`, `lod.named_properties`
(tuples `(key,value)`). Scripts in session scratchpad (`inspect_p3d.py`,
`inspect_doors.py`, `inspect_full.py`). Caveat: use Object Builder/A3OB if authoring is desired;
the external converter inverts winding and its selection membership has caveats (SP-001), but selection
NAMES and named properties are read faithfully.

## Cross-ref
- [[dayz-technical-notes]] / `DAYZ_TECHNICAL_NOTES.md` (canonical LODs).
- Skills `dayz-model-pipeline` (`references/lods-and-geometry.md`, `memory-and-selections.md`),
  `dayz-p3d-audit` (ComponentXX Killer #2), `dayz-animation-pipeline` (class Doors, source).
- [[dayz-wiki-systems-reference]] (gameplay/environment wiki systems, [TBD-verify]).
- Origin: session 2026-07-06 (verification of deep-research P3D + Wiki Sweep).

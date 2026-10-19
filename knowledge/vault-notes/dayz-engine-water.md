# DayZ — Engine water over water objects (rivers, streams, the streambed kit)

> What the engine's water queries read over objects that carry their own water: the vanilla
> `river_24_*` and `stream_14_*` pieces, the `dz\water\streambed\` kit, and a roadway `water_ext`
> face of your own. Measured from the DayZDiag server with probe missions of the DayZ_Baltic_12km
> project, 2026-10-03 to 2026-10-14 (pipeline inbox 0303, 2466 and 3f33). They read native queries
> on the server, and do not test a boat, a player drinking or how the water looks.

## Measure the vanilla map first

Before you decide how a map's water or terrain objects are cut into pieces, measure how the vanilla
map does it with a server probe. The 0303 survey walked Chernarus in 103 × 103 cells of 150 m with
`GetObjectsAtPosition` and logged, for every water piece, its pose, `GetDirectionUp` and water
queries along its axes. Query at gameplay heights, the water surface ± 1 m, never from high above:
on a pitched piece the level read moves with the height of the query (see the last section).

## A server with no player reads no object water until the objects are loaded

With no player connected, `GetWaterDepth`, `GetWaterSurfaceHeightNoFakeWave` and `SurfaceRoadY3D`
at points over the streambed kit and over the `stream_14` pieces of Chernarus read sea level and a
depth of 0, while the pond pieces of the project's own map layer read fine. Calling
`GetGame().GetObjectsAtPosition(Vector(x, 0, z), 30, objs, proxies)` in the same frame, and keeping
both arrays alive until the water queries have run, made 371 of 417 points on the kit's axes read
water.

- The kit's water reads only where the terrain lies about 0.10–0.15 m or more below its roadway
  `water_ext` face: 61 % of the points read wet with less than 0.05 m of clearance, 100 % with
  0.15 m or more.
- The water you see on the kit is a separate 14 × 24 m `CalmWater` proxy sheet, which no server
  query sees (claim: CLAIM-WATER-SERVER-PROBE-LOADS-OBJECTS).

## Vanilla rivers and streams are pitched pieces, and `SurfaceIsPond` is false on most of them

A server read of the whole of vanilla Chernarus, 2026-10-03:

| Pieces | Count | Pitched | Pitch: median / p95 / max |
|---|---|---|---|
| Ponds and lakes | 670 | 3 | — |
| `river_24_*` | 660 | 562 | 1.5° / 4.7° / 8.4° |
| `stream_14_*` | 460 | 388 | 2.2° / 9.0° / 39.3° |

- The water surface the engine returns follows the slope of the piece: the median ratio of water
  slope to piece slope is 0.95 on the rivers (n = 172) and 0.94 on the streams (n = 188).
- At the centres of the pieces above 50 m, `SurfaceIsPond` is true for only 75 of 375 river pieces
  and 30 of 384 stream pieces, while the water depth is positive for 365 of 375 and 312 of 384.

So in a vanilla bed `SurfaceIsPond` false is the normal case and does not rule the water out; test
the depth, as `enforce-script-reference` `references/pitfalls-advanced.md` advises. An acceptance
test that demands `SurfaceIsPond` true pushes you to replace pitched beds with flat planes: on the
Baltic map those stepped planes left visible steps and dry strips on the sloped stretches. The
survey's streambed rows mix other surfaces and do not serve for the slope ratio
(claim: CLAIM-WATER-VANILLA-BEDS-PITCHED).

## How the level is read over a roadway water face

Measured in game on the DayZDiag server, run 8392533a of a vanilla-channel pilot on the Baltic map:
the rule below reproduces 1,940 of 1,941 readback rows within 2 mm, and a second query height
agrees with a mean residual of 1 cm or less. Over a roadway water face,
`GetWaterSurfaceHeightNoFakeWave` and `GetWaterDepth` (`3_game/global/game.c:1183-1185`, as the
ticket cites them) read:

1. The candidate faces are those whose bounding box in world xz contains the query point.
2. The query point goes to the object's model space with its own height, through the object's whole
   transform (rotation and uniform scale).
3. A candidate counts only if that model-space point falls inside the face in model xz.
4. The level is the model y of the face's first vertex, horizontal in model space, brought back to
   world as (lx, y_first, lz). Over several objects the highest level wins.

What follows from it:

- On a pitched piece, a query dy above or below the surface reads the level displaced by
  dy·sin(pitch) along the piece: an error of about dy·pitch² (pitch in radians), +6.0 cm at 2° and
  +1.5 cm at 1° when queried from 50 m above the ground, whatever the scale. Near the edges of a
  face the water is lost (false holes). That is why a probe must query at gameplay heights.
- On the vanilla straights (`river_24_*`, `stream_14_*`) the −z skirt reads its bottom (its first
  vertex is at −0.07 m) and the +z skirt reads the flat level (its first vertex, v3, is at
  +0.07 m). Their Roadway LOD (resolution 3e15) has the same vertices as LOD 0, and every roadway
  normal is (0, 1, 0).
- At gameplay heights the flat part matches the mesh within 1 cm in 84–97 % of the samples, with no
  holes; the differences are on the skirts (±0.07 × scale) and at some joints (up to 13 cm).
- Straights laid edge to edge around a bend leave gaps, where the sea shows through if the bed is
  below sea level. When you use only straights, overlap them by one skirt pair (6 m × scale).

Refuted with the run's data: a roadway that differs from the visual LOD; selection by the exact
projected polygon (it fails 137 cases with yawed, overlapping pieces); selection in model space only
(it fails 21 pad rows); proximity to the face boundary; and the nearest face in model units (241
disagreements). One row is unexplained: where two levels overlapped, the engine returned the lower
one (claim: CLAIM-WATER-ROADWAY-FACE-LEVEL).

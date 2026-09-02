# G12 paint photograph (Track A organic)

Photograph, do **not** unwrap. Accepted by Guillermo 2026-09-02 on the Tripo statue (`g12_arm`).

Authority lives here plus `scripts/project_atlas.py` (G9/G10 engine, copy — do not edit the Quad tree) and `scripts/g12_paint_peel.py` (organic peel driver). Canonical Quad method: `LFQuad_dev/tools/shell_classify_20260824/` and the late-August PAINT groups (`grupos_uv_20260827`).

Do **not** run `uv_view_charts.py` + SLIM on a one-shell organic (coat, statue, character). That clustering is vehicle-panel Track A. On the statue it produced 25 charts, dust-merge 5 with density 0.00–3.95, then k=6 / Voronoi / absorb deformations. Track B `smart_project` 215 islands was rejected: not few, not by views.

## What "done" looks like

In priority order:

1. **The user reads the atlas.** Elevations of the asset (alzados), pieces a painter can name, not tetris and not 200 crumbs.
2. **No overlaps between islands.** Exact SAT pair count = 0. Report collapsed/total; non-zero collapse of unwrapped faces is FAIL. Edge-on photo tris (`n·axis ≈ 0`) may be 4/11k and are the photograph, not an unwrap collapse.
3. **Photograph self-overlap (autosolape)** is what the user sees as "sigue habiendo solape". Peel overlapping **pieces** until the ghost is gone. Tube thickness leftover ~0.03 was accepted as "mejor".
4. **One global scale `a`.** CV = 0. Affine `u = a·u_proj + b`, `v = a·v_proj + c`. Rigid translate only for peeled pieces. Do not normalize density per island (that deforms the photo).
5. **Few islands that are pieces of views.** 2 alzados (n+ skin / n− lining). L/R stay in the **same** frame. Peel legs, then occluding limbs. Statue landed at 15 islands. Not 40, not 215. Not graph-coloring L/R into extra frames (that kills the elevation).

## Recipe

1. Sanitize the mesh. Do not remesh as part of UV.
2. Measure the photograph axis (bbox / island area, autosolape). Up = longest bbox axis. Disallow top-down if a side elevation exists. Statue: Up=Z, thin=+Y front. Unsplit closed coat autosolape ≈ 1.0 — **must** split by normal sign.
3. Split by **normal sign**: n+ = skin / outside, n− = lining / inside. These are **two alzados of the same asset**, never stacked in one island.
4. Split **L/R** only if the shell bbox crosses the measured X mid-plane. Keep L and R in the same alzado (archipelago, real projected XY). If SAT collides on the midline, nudge a tiny U gap (`du_each` ~ 0.01 world). Do **not** put L and R in different frames.
5. One photograph rotation so world-up increases with V (head up). Spine at `u_proj = 0`.
6. Pack **cropped frames as rectangles** (G10 maxrects). Two frames side by side (forro | piel). Align pieces within each layer, then layers to each other. No island tetris pack.
7. **Gate SAT=0.** If the user still sees overlap, it is intra-island photograph occlusion. Peel pieces, do not add cameras past ~2 alzados unless they ask.

### Peel overlapping pieces (same alzado)

Repeat until the ghost is gone. Same `a`, rigid translate only. Place the piece so it still reads as that part of the elevation (legs below hem, arms beside, a second occluder above).

**Legs (Guillermo, 2026-09-02):** if the coat overlaps the legs in the photo, make a legs island. Measure: cut near the hem; faces below whose connected component **reaches the floor** are legs. Coat skirt that does not reach the floor stays with the coat. Translate legs **Δv negative** (below hem, feet down, midline kept).

**Limbs / occluders:** on remaining coat islands, raster the photograph. Pixels with coverage ≥ 2. The **front occluder** is the covering face with **larger world depth along the view** and a real Δ (statue: larger world Y, ΔY ≥ 0.02). Connected components of those fronts = limb. If a CC still shares photo pixels, a second piece (`arm2`). Skip grazing CCs of a few faces (n<8). Translate arms beside (Δu), leftover occluders above (Δv+).

Do not Voronoi. Do not `smart_project`. Do not Recreate UV in Modddif.

## Worked example — Tripo statue 2026-09-02

Mesh: `statue_remesh.blend` object `statue`, 5756 faces, 1 shell, identity world.

| run | islands | SAT | autosolape | occupancy | notes |
|---|---:|---:|---:|---:|---|
| `g12_proj` | 4 | 2 | 0.234 | 0.73 | 2 alzados, L/R midline SAT, coat over legs. User: se reconoce, **sin solapes** |
| `g12_legs` | 8 | 0 | 0.166 | 0.54 | legs z=0.32 floor-CC, Δv=−0.194. User: mejor, sigue solape (manga) |
| `g12_arm` | 15 | 0 | 0.033 | 0.19 | peel front occluders; arms Δu ±0.27, arm2 Δv=+0.77. User: **mejor, guardar receta**. Modddif after |

Leftover 0.033 is sleeve tube thickness + n<8 folds, not the arm-over-chest ghost.

Paths: `DayZ Projects\_scratch_tripo2p\statue\retopo\g12_arm\`.

## Do not

- Unwrap (SLIM / angle-based / `smart_project`) on paint organic.
- `uv_view_charts.py` k-means / cone_fallback on a one-shell coat.
- Recreate UV in Modddif. Generate only on this atlas.
- Graph-color L/R into extra elevations to force SAT=0.
- Per-island density normalize (deforms the photograph).
- Hunyuan / 3090 for UV. Enforce / PBO / vault (other agents).

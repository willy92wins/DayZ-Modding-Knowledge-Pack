# Re-unwrapping a model that already ships, with a LOD chain

Measured end to end on 2026-09-01/02 against `LFQuad_body.p3d` (two visual LODs:
38.831 and 15.422 faces, 16 materials, 4 wheel proxies, 29 selections per LOD).

This is a different job from the one the main SKILL.md describes. There the input
is a mesh you are free to treat as raw material. Here the model **already ships**:
its selections carry memory points, damage zones and proxy mounts, its material
assignment is wired into `config.cpp`, and the only thing you are allowed to move
is UV. Everything below is what that constraint costs and how to pay it.

Read this when the ask sounds like *"re-desplegar el modelo que se envía"*,
*"cambiar solo las UV"*, *"que los dos LOD compartan textura"*, or when an atlas
has to serve more than one visual LOD.

---

## 1. Make "UV-only" a measurement, not an intention

Before touching anything, freeze a fingerprint of everything that is **not** UV and
compare against it after. Written in complementary form: not a list of things that
must survive — that list is written by whoever is doing the changing — but a hash of
the whole, with `Vertex.uv` as the single field deliberately left out.

Per LOD, hash: point coordinates, face-to-point topology, the `(texture, material)`
pair of every face, and the selection names. In MLOD the UV lives per face-vertex,
so a legitimate unwrap does not need to touch a single point, and any difference in
those four hashes means the change stopped being a UV change.

Calibrate it by mutation before believing it, four candidates built in the run:

| mutación | esperado | qué mueve |
|---|---|---|
| fichero sin tocar | pasa | — |
| **una UV movida 0,25** | **pasa** | — |
| un punto movido 1 mm | falla | solo `puntos` |
| una selección renombrada | falla | solo `selecciones` |

The bolded row is the one that matters and the one usually skipped. A gate that also
rejects the legitimate change is not strict, it is broken, and that failure is
invisible if you only ever test the bad cases.

---

## 2. You cannot transfer a fragmented layout onto a decimated LOD

Three attempts, three distinct failure modes, all measured on the same pair:

| intento | método | resultado en LOD1 |
|---|---|---|
| v1 | vecino más próximo por esquina, sesgado 12% al centro de la cara | ocupación **25.114%**, una sola cara con el **41% del atlas** |
| v2 | isla fijada por cara, mapa afín de reserva | densidad correcta (ratio LOD1/LOD0 = 0,97) y **8.409 pares** solapados, 349.089 texeles |
| v3 | proyección por isla con punto recortado al triángulo | 4.647 pares, 329.542 texeles, y **167 caras aplastadas** |

The v2 row is the instructive one: **the density came out right and the sheet was
still ruined**. A per-face affine map is locally correct and globally inconsistent,
so adjacent faces overlap each other. Checking density alone would have shipped it.

### The cause is granularity, and it is arithmetic

LOD0 islands had a **median of 2 faces**. LOD0 carries 38.831 faces over 10,76 m²
and LOD1 15.422 over 10,53 m², so the mean LOD1 face is **2,5x** the area of a LOD0
face. One coarse face therefore spans several islands at once. Clamp it into one and
it squashes; spread it across several and its neighbours pile up. There is no third
option, and no amount of care in the transfer changes the arithmetic.

Before attempting any LOD transfer, measure the ratio `median island area / mean
coarse face area`. Below ~1 the transfer cannot work.

---

## 3. And you cannot fix it by cutting fewer seams

The obvious response is to make the islands bigger. Measured on the same mesh,
unwrap only — no fold loop, no packing — with the collapse percentage next to the
island count:

| estrategia de costura | costuras | islas | mediana | mayor | NaN | **colapsadas** |
|---|---:|---:|---:|---:|---:|---:|
| `smart_project` 80° | 49 | 8.515 | 2 | 389 | 0 | **0,0%** |
| material + aristas > 60° | 15.401 | 5.188 | 2 | 1.579 | 0 | **15,3%** |
| material + aristas > 40° | 21.669 | 8.577 | 2 | 819 | 0 | 0,1% |
| material + aristas > 25° | 28.433 | 13.442 | 2 | 620 | 0 | 0,0% |
| **solo costuras de material** | 49 | **695** | **19** | 1.594 | 0 | **100,0%** |

The floor is 495 connected shells in 3D, so 695 islands is nearly optimal — and it
flattens the entire mesh. The only seam family that survives is the projection route,
and that is precisely the one that fragments. The intermediate angle thresholds are
worse than both ends: more seams *and* collapse.

**The trade is not negotiable on this class of mesh.** Legible-atlas advice
("few large semantic islands") assumes a mesh you may retopologise; a shipped
hard-surface body with hundreds of small welded shells does not offer that choice.

### The probe that recommended the disaster

The first version of that seam probe measured island count and NaN — and nothing
else — so it recommended the 695-island strategy. Every counter downstream in the
recipe filters `abs(area) > 1e-14` before measuring, so over the survivors the
collapsed run reported **1.308 px/m and 76% occupancy**: numbers better than the
correct run's. Only the exact SAT oracle over the unfiltered triangles found
**30.032 collapsed of 38.832 — 77%**.

This is LL-371 one level deeper than section 2b of the SKILL.md: it is not only the
shipped gate that inherits the area filter, it is **the probe you write to choose
between strategies**. A probe that cannot see the failure mode the project already
paid for will select for it. Put `collapsed / total` in every comparison table you
build, including the throwaway ones.

---

## 4. The shape that works: one sheet, disjoint regions

Neither LOD carries the other's layout. Each is unwrapped on its own with the
projection recipe, the coarse LOD is scaled to take a declared share, and both are
packed **together as one packing problem** into a single sheet.

One texture still serves both: painting happens once on the fine LOD's region, and
the coarse LOD's region is filled at bake time by baking it directly from the same
high-poly. That is simpler than resampling the fine region and it never meets the
granularity problem, because a bake works per texel.

Setting the share: after per-island density normalisation each island's UV area
equals its 3D area, so the two LODs arrive at roughly 1:1. The packer fits everything
uniformly, so **the ratio going in is the ratio coming out** — scale the coarse LOD
by `sqrt(want / have)` before packing and the split lands exactly.

Measured result at a 75/25 split, 4096 sheet, 4-texel pack margin:

| | LOD0 | LOD1 |
|---|---:|---:|
| caras | 38.831 | 15.422 |
| islas tras converger | 8.708 | 6.287 |
| iteraciones del bucle de pliegues | 4 | 2 |
| colapsadas | **0,00%** | **0,00%** |
| solape SAT exacto | **0 pares** | **0 pares** |
| cuota real de hoja | 75,0% | 25,0% |
| densidad | 349 px/m | 204 px/m |

Cross-LOD overlapping pairs: **0**. Islands all single-material, which comes free if
you seam the material boundaries before unwrapping — 49 edges on this mesh, and worth
doing because a mixed island cannot be painted and breaks any per-material check.

### What sharing costs

Packing both LODs dropped the fine LOD from 528 px/m (alone, 17,9% occupancy) to
349 px/m (shared, 10,4% total). Most of that is not the sharing but the **gutter**:
~15.000 islands of roughly 19 texels a side, each paying a 4-texel margin, is a 42%
linear inflation per island. Levers, in order of honesty:

- fewer islands — not available here, see section 3;
- smaller pack margin — cheap (~+18% at 2 texels) but it invalidates whatever
  no-bleed measurement was made against the bake's own margin, so it costs a re-measure;
- bigger sheet — doubles density at 8192, at 4x the texture memory.

Report the number and let the owner choose. 349 px/m was 2,6x the shipped reference
(section 7), so it was accepted.

---

## 5. Aligning the high-poly: search the frame, never assume it

A high-to-low bake fires rays from the low surface and records the high one. If the
two are not in the same place the map records detail from the wrong spot, and the
error is invisible in every offline check — it shows up in game as relief that does
not match the silhouette.

The handoff for this model said the high-poly rip "could not serve this mesh",
citing p95 = 6,1 mm. That figure had been taken against a different OBJ **and**
without any frame search. The real fit, found by trying all 48 axis permutations
with sign flips, each re-centred on the bounding box:

```
(-x,  z,  y)   p50=  0,47 mm   p95=  1,82 mm   fuera de jaula   2,0%   <- este
( x,  z,  y)   p50=  1,14 mm   p95= 21,35 mm   fuera de jaula   9,0%
identidad      p50=163,71 mm   p95=438,62 mm   fuera de jaula  93,6%
(x, z, -y)     p50=829,14 mm   p95=1210,97 mm  fuera de jaula 100,0%
```

Two things make the search cheap and reliable:

- **Sorted bounding-box dimensions identify the object before anything else.**
  `[0,8848, 0,9478, 1,8736]` against `[0,8848, 0,9463, 1,8732]` says "same object,
  same scale, axes permuted" in one line, and tells you the search is worth running.
- **Re-centre each candidate on the bbox centre before scoring.** A correct
  permutation scores terribly under a pure origin offset and gets discarded; this
  model needed a 144 mm shift in one axis.

**Check the determinant of the 3x3.** Here it came out +1, so the transform is a
rotation and the baked normals keep their handedness. A -1 means the alignment
mirrors, and the map will be chirally wrong in a way that is easy to miss.

Move the LOW into the high-poly's space, not the other way round: a rigid transform
leaves tangent-space normals untouched — they are defined against the surface — and
moving one object beats re-parenting eleven.

### The guard criterion is reach, not deviation

A first guard demanded `p95 < cage/4` and threw the coarse LOD out at p95 = 5,22 mm.
That was wrong: **the coarse LOD is supposed to deviate from the high-poly** —
capturing exactly that deviation is what the bake is for.

The criterion that discriminates is the fraction of the low mesh sitting beyond the
ray's reach: **1,9% and 2,1%** for the two aligned LODs against **93,6% and 95,6%**
for the misaligned frames, with `p50` separating them by two orders of magnitude
(1,7 mm against 164 mm). Fail on `fraction beyond cage > 10%` or `p50 > cage`, and
report p50/p95 without gating on them.

---

## 6. Measure the map where it is sampled

The bake's own quality check rejected a good map at 2,433% non-unit normals against
a 1% bar. Opening the artifact showed **99,08% of those texels were in the packing
gutter**; of the texels a triangle actually covers, only **0,0976%** were short.

The gutter fraction tracks island count, not bake quality — this sheet is 89,6%
empty — so a whole-sheet threshold measures fragmentation and calls it a defect.

Rasterise the UV coverage, erode it by one texel to get the "core" (texels whose
whole 3x3 neighbourhood is covered), and put both tests there:

- non-unit normals inside the core, and
- **texels still holding the seed colour inside the core**.

That second test is the one that earns its place. Over the whole sheet, "under 92%
neutral" was nearly free with 89,6% empty. Inside the core it read **29,55%** — and
that number is what revealed that only the fine LOD had been baked and the coarse
LOD's quarter of the sheet had never received a ray. After baking both: **9,166%**.

Keep the residual honest rather than hiding it: the leftover neutral is the faces
whose ray cannot reach the high-poly (2,30% and 2,67% here), which are deliberately
flattened to neutral because a cage cannot invent a surface that is not there.
Flatten the **triangle** dilated a couple of texels, not its bounding box: bbox+7
wiped 226.663 texels where triangle+2 wiped 86.249 for the same faces.

---

## 7. Calibrate density against what already ships

The main SKILL.md quotes ~292 px/m as the healthy reference measured on the LFQuad
wheels. Re-measured 2026-09-01 by decoding the shipped `.paa`: the wheel `_co` is
**1024²**, with UV density 0,1307–0,1438, so the shipped figure is **134–147 px/m**.
The 292 is that density read against a 2048 texture the asset does not use.

The general form matters more than the number: **derive the floor from shipped and
accepted work, and measure both halves** — the UV density from the model and the
texture side from the file — so nothing is carried in as a constant.

An earlier floor for this work was taken from two previous atlases that each covered
a *subset* of the same body. Packing less surface into the same sheet buys density
for free, so a whole-body atlas "failed" while being denser than anything the mod
ships. A gate calibrated above everything the project ships goes permanently red and
stops being read.

When a floor turns out to be miscalibrated, move the axis and harden something else
rather than lowering the bar. Here the replacement added **uniformity** — no material
below 60% of the body's own median — which a single global floor cannot see: it
cannot distinguish a healthy sheet from one with a single starved group, and a
starved group is exactly what shows up in game as one blurry part.

---

## Checklist

1. Freeze the non-UV fingerprint, and calibrate it by mutation including the
   legitimate change.
2. Measure `median island area / mean coarse face area`. Below ~1, do not transfer.
3. Choose seams with a probe that reports **collapse**, not just island count.
4. Unwrap each LOD separately; seam material boundaries first.
5. Normalise density per island, scale the coarse LOD by `sqrt(want/have)`, pack both
   as one problem.
6. Prove zero overlap within each LOD *and* between them, exactly.
7. Align the high-poly by searching frames; check the determinant; gate on reach.
8. Bake every LOD; measure the map inside the island cores.
9. Compare density against shipped work, and report what sharing cost.

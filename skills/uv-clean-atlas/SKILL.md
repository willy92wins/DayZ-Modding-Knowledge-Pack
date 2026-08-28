---
name: uv-clean-atlas
description: 'Generate clean, human-readable UV atlases (livery-template style — few large semantic islands, zero overlap, moderate stretch) for hard-surface game meshes via a validated Blender-headless pipeline, and audit any UV set with exact SAT overlap + island/density metrics. Use whenever the user wants to unwrap or re-unwrap a vehicle/prop/weapon body for texturing — "generar UVs", "unwrap", "UV wrapping", "atlas legible", "las UVs salen con mil islas", "islas que se pisan", "textura estirada", "plantilla de livery", "UVs limpias", "preparar el modelo para texturizar", auditing UVs ("auditar UVs", "cuántas islas", "hay solape") — and for any rip-to-DayZ or LFQuad-style vehicle import needing UVs. Also covers the PartUV (AI) alternative — when the user asks about AI UV unwrapping, PartUV, PartField, or "IA para UVs", consult this skill''s pilot verdict BEFORE recommending any AI tool.'
---

# uv-clean-atlas — legible UV atlases for hard-surface game meshes

Turn a hard-surface mesh (vehicle body, prop, weapon furniture) into a UV atlas a
human can read like a livery template: each island is a recognizable panel, nothing
overlaps, texel density is uniform, and moderate stretch is accepted as the price of
legibility. Validated 2026-07-16 on the LFQuad Banshee body — both a clean 10.5k-quad
retopo (54 islands / 30 panels, straightened outlines, exact-zero overlap) and a raw
36.9k-tri decimated rip (65 islands, straightening auto-rolled-back, exact-zero
overlap), where 16 previous methods had produced 500–2000 islands.

## The quality gate (what "done" looks like)

Judge the atlas against these criteria, in priority order. The reference bar is a
professional game livery template (whole car side = ONE island, roof, hood, doors).

1. **Islands = semantic panels.** ~15–45 meaningful islands for a full vehicle body.
   A human must identify each island ("that's the left fender") without a legend.
2. **Zero overlap, proven.** Monte-Carlo overlap has a noise floor (~0.06–0.15%);
   "no overlap" may only be claimed from an exact SAT check with **0 pairs**
   (`scripts/sat_gate.py`). Never claim it from MC numbers.
   **A SAT=0 is bounded by the triangles that entered the test - see 2b.**
3. **Moderate stretch is acceptable.** Uniform texel density (p05/p95 within roughly
   0.8–1.5 of median) beats zero distortion. Chasing zero distortion is exactly what
   fragments atlases into confetti — that trade is the root failure this skill fixes.
4. **Organized layout.** Panels axis-aligned in rows, long strips grouped vertically
   at one side, micro-specks clustered in a corner. `pack_islands` optimizes area,
   not legibility — do not use it for the final pack.
5. **The final judge is the user.** Render the layout and show it; "un humano lee el
   atlas" is the acceptance test. Expect 1–2 feedback rounds.

### 2b. A SAT=0 is bounded by what entered the test (measured 2026-08-27, LFQuad material groups)

**LL-371** — Todo gate que filtre parte de su entrada tiene que publicar total / evaluados / filtrados en el veredicto; un filtrado no cero acota el PASS a lo que entro. SAT=0 no es atlas-done si las caras colapsadas fueron saltadas.

`scripts/sat_gate.py:22` skips any triangle whose UV area is `<= 1e-14` before pairing it,
because a degenerate triangle cannot overlap anything. So an unwrap that COLLAPSES faces to
zero UV area does not fail the gate - it vanishes from it, and the worse the collapse the
cleaner the verdict reads.

Measured on the LFQuad material groups: a chrome group was shipped as "done, zero overlap
proven by exact SAT, 17 islands, 14140 px/m" while **31.0% of its faces were collapsed**; the
chassis read "96 islands, 1964 px/m" with **78.0%** collapsed and its px/m averaged over the
surviving 22%. Re-solved honestly, that same chassis gives 1198 islands and **755 px/m** - the
true number is 2.6x worse than the one reported as a win.

**Do this**: report `collapsed / total` next to the SAT pair count, and treat any non-zero
collapse as FAIL, not a footnote. Two cheap tells that it is happening:

- criteria 1 and 3 move the WRONG way - island count DROPS and texel density RISES as the
  defect grows, because both are computed over the survivors only. A gate metric that improves
  while the mesh degrades is the signature.
- a `mirrored%` that is neither 0 nor 100 may be collapse, not mixed handedness. DayZ's
  `uv_audit.py` (`:280-283`) excludes degenerate triangles from the `mirrored` numerator but
  not from its denominator, so a uniformly mirrored mesh with 31% collapsed reports 69%. Check
  whether `non-degenerate` and `mirrored` are the same integer before calling it a chirality
  defect - on three LFQuad groups they matched exactly.

## Preconditions

- Blender 4.3+ headless (`MINIMUM_STRETCH`/SLIM unwrap method required; verified in 5.1).
- Mesh health first: run mesh sanity (weld/degenerate checks) BEFORE unwrapping —
  duplicate verts read as open boundaries and zero-area faces crash naive code
  (every script here guards zero-length normals, but garbage in = specks out).
  For DayZ work the LFQuad tools apply: `mesh_health.py` / `mesh_sanitize.py`
  (adaptive weld ladder) in `LFQuad_dev\tools\`.
- Decimated rips CAN be unwrapped directly with this pipeline (validated), but if the
  mesh has 3D micro-detail on curved surfaces (tire lugs), retopo-then-bake is still
  the better product path — and any retopo/decimation destined for visuals is
  **user-gated**: ask before applying to production.

## The pipeline (one command)

```
blender -b <in.blend> -P scripts/uv_clean_atlas.py -- <out.blend> <out_dir> <tag> \
        <min_faces> <object_name>
# validated: min_faces=30 (10k mesh) / 60 (37k mesh)
```

Stages, and why each exists:

1. **Artist-style charts — per-shell dominant-view clustering** (`uv_view_charts.py`).
   For each connected shell (physical piece), k-means-cluster face normals (k=1–3 by
   normal spread) and cap the result to ≤k charts per shell: only the largest
   component of each cluster is a core; every other patch merges into its
   longest-boundary neighbor. This reproduces how an artist unwraps a body panel —
   one island per "view side" of each piece (fender top, its underside), swallowing
   stretch on wrap edges. Helicoid shells (springs: clustering shatters them) fall
   back to normal-cone region growing at 100°, which unrolls them as strips.
2. **Dust merge.** Charts under `min_faces` merge into the neighbor sharing the
   longest boundary. Kills confetti at the source. Isolated micro-shells with no
   neighbor survive — they become "specks" and are handled by the packer.
3. **SLIM unwrap + fold guard, ONE round.** Unwrap all with `MINIMUM_STRETCH`.
   Detect folded charts two ways — per-TRIANGLE winding mix >5% (bowtie quads hide
   when signed areas are summed per face) and per-chart MC self-overlap >3%
   (a >360° wrap keeps consistent winding while overlapping; winding checks alone
   miss it). Fix by normal-sign bisection (a wrapped cylinder becomes two half
   shells); centroid-PCA median split as fallback. **Never iterate the guard**: a
   second pass chases 1–2% cosmetic folds and cascades island count (measured
   32→84; same cascade documented in the July 2026 LFQuad spike).
4. **SAT finisher, ONE round.** Exact SAT tri-tri over the whole layer; offender
   faces (in practice mm²-scale crease slivers) get all edges seamed → isolated as
   invisible speck islands → global re-unwrap (plain SLIM flags — see traps).
5. **Boundary straightening, panels only, solver-free** (`uv_straighten.py`).
   Walk each panel island's boundary loops with the bmesh radial walk, smooth them
   with Taubin lambda/mu (shrink-free), cap each corner's displacement at 0.35× the
   local boundary spacing (thin hole-rims invert past that), and diffuse the
   displacement a few rings into the interior. No pins, no re-solve, no repack —
   displacement is bounded so it cannot explode the layout. Strips and thin islands
   are skipped (smoothing their two rails independently bowties them). Residual
   offender faces (≤ ~40) are excised as micro-specks; a larger offender set means
   the mesh doesn't tolerate straightening and the stage AUTO-ROLLS-BACK (measured:
   active on the LFQuad retopo, rolled back on the raw rip — both end SAT=0).
6. **Semantic shelf pack** (`uv_shelf_pack.py`). PCA-rotate every island so its major
   axis is horizontal; shelf-pack panels in rows biggest-first; rotate strips
   (aspect>6: springs, rails, trims) vertical, downscale them to the panel-field
   height (strips are near-invisible parts — they pay the texel cost so panels keep
   theirs) and group them right; specks go to a corner grid. Shelf width is iterated
   dry-run until the block is roughly square. Do NOT "improve" this with
   `pack_islands` — it will shuffle rotations and destroy legibility.
7. **Metrics + verdict.** The script prints islands / MC overlap / density spread and
   the SAT verdict, and renders `<tag>_uvlayout.png` + `<tag>_uvgrid.png`. Read the
   layout PNG yourself before showing the user (R1: verify artifacts).

### Reading the output

```
SHELLS: 13                          # connected components = island floor
CHARTS_VIEW: 41                     # after per-shell view clustering
CHARTS_AFTER_DUST: 34
FOLD_GUARD: bisecting 1 charts ...  # >2-3 charts here = mesh very wrap-prone
SAT_PRE_FINISH: pairs=3 faces=6     # mm2-slivers, expected small
STRAIGHTEN: loops=17 corners=1072   # panels whose outlines were smoothed
EXCISE: 9 residual offender faces   # or STRAIGHTEN_ROLLBACK_EARLY on hostile meshes
SHELF_PACK: islands=54 panels=30 strips=9 specks=15
SAT_VERDICT: pairs=0 (ZERO OVERLAP PROVEN)   # the release gate
METRICS[...] islands=54 overlap=0.09% density_p05/p50/p95=0.85/1.00/1.20
```

- `overlap` (MC) at 0.0–0.15% with `SAT_VERDICT: pairs=0` = clean; report the SAT.
- `STRAIGHTEN_ROLLBACK*` lines are the safety valves working, not failures: the
  mesh keeps the (already validated) un-straightened layout.
- `islands` far above `3× SHELLS` → `min_faces` too small, or mesh health junk.

### Iteration knobs (change ONE per rebuild)

| Symptom | Knob |
|---|---|
| Tiny junk islands everywhere | mesh health pass first; `min_faces` up |
| A physical piece split oddly | its normal spread sits near a k threshold — check `_spread` cutoffs (70°/125°) in `uv_view_charts.py` |
| Springs/rails fragmented | `frag_limit`/cone fallback in `uv_view_charts.py` |
| Outlines still wobbly | straightening rolled back (see log); that mesh needs retopo or manual seams for crisp profiles |

## Auditing an existing UV set

- `scripts/sat_gate.py` — exact overlap verdict + offender face diagnostics:
  `blender -b <file.blend> -P sat_gate.py -- <object_name>`
- `scripts/uv_metrics.py` — import and call `score_and_render(obj, out_dir, tag)`
  for islands / MC overlap / density + layout render (headless-safe rasterizer).
- For DayZ `.p3d` files audit with `LFQuad_dev\tools\uv_audit.py` instead (works on
  assembled p3d LODs, knows about proxies and full-frame faces).

## Handing off to texturing / DayZ

- The out blend keeps the original mesh + new active UV layer. Export or feed py3d
  from there. DayZ note: binarization quantizes UVs to int16 over the LOD's min/max —
  one face with huge tiling degrades the whole LOD; this pipeline keeps everything in
  [0,1] so it is safe.
- Texel density reference: ~292 px/m @2048 was the healthy in-game reference measured
  on LFQuad wheels; props ~512 px/m, first-person weapons ~1024 px/m.

## AI alternative — PartUV (piloted, measured; read before recommending any "UV AI")

Verdict 2026-07-16 (RTX 3090, WSL2): PartUV works locally and is the only real
code+weights UV AI, but on vehicle content it LOST to this pipeline on the primary
criterion: 162 islands (t=1.25) / 127 (t=2.0) vs our 43 on the same retopo mesh, and
232 vs our 63 on the same rip — it charts per PartField part with no dust control, so
helicoids/junk shells explode into speck storms. Density spread was comparable; its
GPU cost is fine (~4 s inference @10–37k tris). Use it only when semantic part
separation matters more than island count, or as a chart-source experiment feeding
stages 4–7. Setup quirks, exact numbers and rerun commands: `references/partuv-pilot.md`.

The wider 2026 tool survey (Ministry of Flat, RizomUV, xatlas, Nuvo/SeamGPT etc. and
why each was descartado or shortlisted): `references/tool-research.md`.

## Known traps (all bitten during development)

- `bpy.ops.uv.smart_project` headless ignores face selection and unwraps EVERYTHING.
  This pipeline never uses it; if you script around it, don't rely on selection.
- Never dedupe bmesh loop-UV wrappers by `id()` — wrappers are transient and ids
  recycle, silently skipping loops. Each loop owns its UV; visit each loop once.
  Same for `loop.index`: not guaranteed initialized — key corners by
  `(face.index, vert.index)`.
- Zero-length face normals exist in real meshes; guard every `Vector.angle()`.
- MC overlap has a noise floor; only SAT=0 proves zero overlap (July 2026 lesson).
- One guard round only — fold-guard iteration cascades island count (32→84 measured).
- Boundary smoothing: pure closed-curve Laplacian is curve-shortening flow — it
  collapses boundaries into the island (measured 605k SAT pairs). Use Taubin
  lambda/mu AND cap per-corner displacement by local boundary spacing.
- Pinned SLIM re-solve is a trap chain: `no_flip` defaults to False and 10 default
  iterations don't converge against pins (1302 folded pairs measured), and with
  pins the auto-pack drops UNPINNED islands on top of pinned ones — phantom
  cross-island SAT counts before packing. The shipped pipeline avoids pins
  entirely (local diffusion instead); don't reintroduce them casually.
- `no_flip=True` on a full re-unwrap makes wrap-prone charts spiral-overlap
  instead of flipping (133 residual pairs measured on the rip) — flips are the
  fold guard's signal; don't suppress them globally.
- Judge overlap ONLY on the final packed layout, and prefer rollback over mass
  excision: >~40 offender faces post-straighten means the stage hurt the mesh.
- Windows→WSL scripts: strip CRLF (`tr -d '\r'`) before `bash`; never inline-escape
  quoted python through PowerShell→bash — write a script file.
- OneDrive: don't Write/Edit `.py` in the OneDrive tree (null-byte/truncation risk);
  work in a scratchpad and copy results in with a size check.
- The fold guard's detector must be the gate's instrument. A Monte-Carlo estimate over a
  percentage threshold can never clear an exact zero-tolerance gate: whatever sits below the
  threshold survives every round, forever. Measured 2026-08-27 with exact per-island SAT as the
  detector instead: engine 31481 -> 0 pairs, chassis 5839 -> 0.
- "One guard round only" (above) is a COST rule, not a correctness rule. It bounds island
  growth and it is right whenever one round already leaves the exact gate at zero. When it does
  not, iterate until the gate is clean and pay the islands - measured 200->244, 546->1375, over
  3-7 rounds, with texel density essentially unchanged. A mesh that still folds is not
  shippable no matter how few islands it has. Pair counts are not monotone across rounds
  (4 -> 2 -> 7 -> 10 -> 0 measured); do not stop on the first increase.
- Sparse seams make SLIM fail silently. With a tree-cotree cut graph (133 seam edges for 42
  shells over 45k tris) `MINIMUM_STRETCH` returned **78.3% of triangles collapsed straight out
  of the unwrap**, median per-triangle UV extent exactly zero, and no warning. `ANGLE_BASED` on
  the same seams left 15.8% collapsed and squeezed the whole layout into u in [0, 0.048] - 18
  px/m. On another group both solvers returned an **all-NaN UV layer** (109086 NaN = 6 per
  triangle x 18181): NaN fails an `area > eps` test, so every triangle got filtered out and the
  downstream gate died in `min()` on an empty list. An `except TypeError` around
  `bpy.ops.uv.unwrap` only catches a Blender that does not know the enum - check the returned
  layer for NaN and for collapse instead.
- `smart_project` stays unusable for partial selections (first trap above), but as a
  whole-mesh seam generator it is the honest fallback when the topological cut collapses: on
  four LFQuad groups it gave 0.0% collapsed and SAT 0 where the tree-cotree route gave
  3.6-78.0% collapsed. Follow it with `seams_from_islands` so a later re-unwrap keeps the same
  cuts. The price is island count (17 -> 214, 96 -> 1198); section 2b is why that price is the
  correct one.

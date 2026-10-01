# Winding Diagnostics — Deep Methodology

> Extracted from dayz-p3d-audit/SKILL.md 2026-07-07 (F3). The core SKILL.md keeps the index/summary and points here.



Moved from `DayZ Projects/CLAUDE.md` 2026-05-04. It is the winding validation
detail learned in production with Crate_Wooden and WallLamp. Complements
section 1 ("Inverted Face Winding") with validation methodology, gotchas, and
complete import checklist.

#### How NOT to verify — misleading heuristics

⚠️ **Centroid-based check (`cross(e1, e2) · (face_centroid - LOD_centroid) > 0`):**
- It is **right-handed** (Three.js / OpenGL convention). DayZ is **left-handed**. A CORRECT post-flip model will appear as "winding inward" in that check but with outward declared normals — not incoherence, it is the opposite sign of cross product between systems.
- Assumes **convex geometry** (compares against LOD centroid). For hollow boxes with thick walls, correct interior faces are marked as "inverted".
- **Conclusion: DOES NOT WORK for validating absolute DayZ winding.** The `dayz-p3d-audit` skill had it for months and produced up to 100% false positives on correct models. Only valid for relative consistency before/after SAME operation, or compared against a reference vanilla.

⚠️ **Comparing `face.vertices[i].normal` with cross product directly does NOT work.** Normals in `lod.facenormals` pool are smoothed per-vertex-corner (smoothing groups): on flat faces they match flat normal; on smoothed faces they do not. To use them as "intent" reference one must **average normals of the 3-4 corners of ONE face** and compare against `cross(e1, e2)`. See Check A in `audit_p3d.py`.

⚠️ **Assuming `lod.facenormals[i]` is normal of `lod.faces[i]`.** False. `lod.facenormals` is a global POOL (size = MLOD header `num_facenormals`, **independent** of `len(lod.faces)`); each Vertex points to it via `normal_index`. Confusing them leads to checks that never run (length mismatch) or checks comparing wrong things.

#### How TO verify

1. **Check A — winding-vs-averaged-normal per face (DIAGNOSTIC).** For each face, calculate `n_winding = normalize(cross(v1-v0, v2-v0))` and compare with normalized average of `face.vertices[i].normal` over corners. % of faces with `dot < -0.5` indicates handedness state:
   - **~100% UNIFORM_FLIPPED** → EXPECTED state in DayZ (left-handed) after export from Blender (right-handed Z-up). Handedness shift inverts cross product. **Empirically verified with Crate_Wooden 2026-04-25 in-game: render/bullets/cursor/collision all OK.** No action needed. → severity NOTE.
   - **~0% UNIFORM_NON_FLIPPED** → either no handedness transform or normals realigned post-transform. Verify in-game. → severity NOTE.
   - **5-95% MIXED** → real bug, inconsistent render/collision between faces. → severity CRITICAL.
   Coordinate-system-agnostic.

2. **Check B — edge-pair topology (MOST RELIABLE).** Two manifold faces sharing an edge must traverse it in opposite directions. If `face1` traverses `(A→B)` and `face2` also traverses `(A→B)` ⇒ one of the two is flipped. Coordinate-system-agnostic. Independent of modeler's intent. **Best tool for detecting mixed winding post-flip.**

3. **Check C — comparison vs vanilla.** Match faces between target and equivalent vanilla (e.g. `DZ/gear/camping/wooden_case.p3d`) by centroid proximity, compare winding-derived normals. Only applicable when there is a close vanilla equivalent in geometry.

4. **Direct in-game test.** Rebuild PBO → test server → inspect visual + collision + actions + ballistic. It is the final filter and the only 100% definitive one. When all previous checks say "OK", test in-game anyway.

5. **In-game spawn is non-negotiable (SP-216).** Offline `.p3d` gates (py3d reload, per-LOD digest, normal budget, resolved vs 65,535, winding parity, indices, degenerate faces, Geometry byte-identical to a p3d that does spawn) **do not authorize spawn**. Never declare a p3d "ready for spawn" by those checks; in-game spawn is mandatory gate. Complements point 4: offline "OK" is not "spawns".
   - **Case (LFHeli HH-60G V8, verified 2026-07-20):** passed those gates — normals 24,404<32,768, resolved 46,905<65,535, winding 100%, Geometry LOD byte-identical to a p3d that DOES spawn — and yet `Won't simulate, it has no geometry`. The "normal budget" theory (root-cause of a previous R21) was REFUTED: with normals reduced to 5,506 it still failed. V8 is a negative capacity control, not a refutation of `binarize`.
   - **Measured cause (SP-122, 2026-07-29, same model):** that message is same defect as `Too many vertices` — engine aborts when loading MLOD, before constructing physics; a valid Geometry LOD does not exonerate. HH-60G cliff: **46,133 resolved triples** (46,133 loads, 46,134 does not; 25 in-game verdicts, zero false ones) in `dayz-vehicles/references/binarize-vertex-budget.md` and invariants #24/#27 of `dayz-vehicles/SKILL.md`. The 46,905 of V8 are above that cliff; `RESOLVED_LIMIT = 65535` is a false friend. **Run `binarize` before touching geometry** (three-state verdict: PASS / CAPACITY_FAIL / OTHER_FAIL). CAPACITY_FAIL → do not go in-game to "fix" Geometry; OTHER_FAIL → do not touch geometry. Visual LOD serialization hypothesis (corner order / TAGG / normal pool, "open RCA" on 2026-07-20) was closed as capacity nine days later; do not reopen as primary suspicion or treat count as irrelevant. If `binarize` yields PASS and game still reports no-geometry, other axes remain and in-game spawn is judge.
   - **Reusable bisection:** N test-classnames in 1 PBO, each with a p3d-variant (LODs swapped via py3d). filePatching does NOT reload `.p3d` binaries; one restart tests N variants. Each classname needs its CfgModels entry inheriting skeleton+crew-bones from actual model. 2026-07-20 origin: without that entry, a config with Crew `proxyPos` bones caused `CreateObjectEx` to crash server (minidump in MCPBridge DispatchWorldSpawn) instead of returning spawn_failed. Orthogonal to SP-070/SP-071 (winding/render). Cross-ref: `dayz-vehicles` (get-in/spawn), `dayz-model-pipeline` (`.p3d` export).

#### Trampas conocidas (lessons learned)
- **`flip_winding.py` applied twice** returns to original state (idempotent modulo 2). If you do not remember if applied, check if backup `.p3d.bak_v4_pre_winding_flip` exists — if present, it was applied at least once.
- **`renegate_normals.py` is DEPRECATED** and based on a misunderstanding. If applied, pool normals are erroneously negated; revert by negating again. See "Reusable scripts".
- **Crate_Wooden has mixed winding in Visual LOD** (38.6% bad edges in Check B, 2026-04-25) but **DayZ tolerates it in render** (verified in-game: visual / bullets / cursor / collision OK). Collision LODs (Geometry/LandContact/ViewGeo/FireGeo) are internally consistent. **The skill marks this as CRITICAL in Check B**, which is good as a preventive signal, even if the engine tolerates it in this particular case. Do not re-flip this model unless a concrete in-game symptom appears.
- **Measured:** setting `face.flags |= 0x20000` did not produce two-sided rendering; the faces
  remained see-through in-game. The route confirmed to work is double-sided geometry. The reason is
  now pinned: `binarize.exe` discards the MLOD per-face `flags` field entirely. Three MLODs differing
  ONLY in `face.flags` (`0`, `0x00000020`, `0x00020000`) binarize to a byte-identical model, while a
  moved point and a cleared texture on the same faces each change it (round-trip 2026-08-24). The
  `0x20000` vs `0x00000020` dispute is moot: no face-flag value reaches the game.

#### From Check B to fix: isolate minority group and flip it ENTIRELY (winding + stored normals)

Verified method (GunRacks T1/T2/T3 2026-08-28: 156 inverted faces across 11 parts of three
external artist models, player report "plank normals are inverted"):

1. **Isolate**: weld points by position (5 decimals), split visual LOD into connected
   components (excluding faces from `proxy:*` selections), and within each component run
   orientation flood-fill with Check B rule (two manifold faces traversing
   shared edge in SAME direction are opposite). A healthy component yields ONE group;
   a broken one yields two, and **the minority one is the inverted one** — reference is part's
   own majority, never an absolute sign convention.
2. **Severity by visibility, not by count**: render with id-buffer and screen culling,
   with sign CALIBRATED against population (majority of a model looking good in-game
   must come out front-facing; same lesson as centroid-check above). Minority group
   visible from outside = defect reported by players; interior groups (shelf
   edges) = same fix, lower urgency. Signed volume does NOT decide orientation on open
   sheets. **When discarding "residual", measure in PIXELS of visible backface, not in faces** —
   "few faces" can be a strip of hundreds of pixels (measured: 1 face, 636 px); and
   "identical to shipped" does NOT exonerate: shipped asset can carry defect from origin.
   Real legitimate residual: front-dominant faces with minor slit backfaces
   (healthy pattern measured: 4335 px front / 59 back).
3. **Coupled fix**: invert vertex order (`v[:1] + reversed(v[1:])`) **and negate
   stored normals of those corners in the same pass** — UNLESS pipeline recalculates
   normals in a subsequent step. A fixer that only inverts vertices (e.g. GunRacks
   `fix_winding.py`) is correct ONLY because its pipeline recalculated
   normals afterwards; copying that mechanic to a pipeline without recalculation leaves face visible
   but shaded inside out (second lost cycle). Safe mechanics with global POOL:
   if `normal_index` of faces to flip are exclusive to them, negate in place;
   if any is shared with a face not touched, add negated normal as new pool entry
   (32768 budget) and reindex only those corners.
4. **Artist defect RECURS**: measured identical across three consecutive deliveries of
   same model (16/08, 18/08, 19/08) — lives in working file, re-exporting does not cure it.
   Check is run on EVERY delivery reintegration, not only initial import; and
   fixer is anchored fail-closed (expected component centers + exact face count)
   so a differently re-exported breakdown aborts rather than flipping wrong things.
5. **Inverted faces WITHOUT topological minority** (edges/chamfers not sharing manifold
   edges with their part — point 1 flood-fill cannot see them): operational criterion is
   **back-dominance across a battery of views covering entire sphere** — per face, pixels
   won in z-buffer as backface ≥8 and ≥4× those won as front. Second GunRacks round
   (same day): 17 more faces like this, with strips up to 636 px, which first pass discarded
   as residual. Two measured pitfalls when trying to arbitrate by geometry instead of
   visibility: positional gate ("near ymax ⇒ exterior is +Y") errs on hanging
   faces (soffits, shelf bottoms), and bidirectional raycast cannot resolve ~1 mm sheet
   sandwiches (epsilon hit against twin skin in both directions). And verify the
   battery itself: in typical yaw/pitch projection of these rasterizers positive pitch
   LOWERS camera — a "top view" looking from below leaves roof un-audited
   (measured: sought roof defect did not exist, but original battery could not
   know). Closing loop: complete post-fix re-render with 0 back-dominant faces and
   none new.


#### Render-sign A/B and source-profile limits (SP-070/SP-071, added 2026-08-31)

Edge-pair coherence and cross-product-versus-stored-normal ratios test internal consistency;
they do not by themselves predict which side the engine will render. Normals and winding can
be mutually coherent while both use the wrong sign for the target pipeline.

When the absolute sign remains uncertain, generate an all-flipped variant by reversing every
**visual** face, excluding proxy triangles because their winding encodes the proxy frame.
Binarize the candidate and variant, then run an in-game A/B. Before spending that cycle,
measure both derived outputs with the same census and require the results to differ; equal
results make the A/B a null experiment. Binarization was measured preserving source winding,
not normalizing it.

A pre-binarize dot census can be a cheap predictor only inside a calibrated source profile.
Exclude near-zero dots, do not compare ratios across vanilla ODOL, converted MLOD, and raw
DCC MLOD, and do not generalize a generic-DCC flip rule to a vehicle profile with a different
measured source transform. After adopting a flip, recalibrate every expected fraction in the
assembler's gates. The in-game A/B remains the absolute render verdict.

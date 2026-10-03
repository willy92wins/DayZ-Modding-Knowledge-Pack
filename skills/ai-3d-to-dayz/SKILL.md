---
name: ai-3d-to-dayz
description: >
  Front-end para generar un prop, item o asset 3D de DayZ con IA: image/text-to-3D,
  limpieza y retopología low-poly manifold, UV, normal bake high→low, PBR y handoff
  a .p3d/.paa/.rvmat. Úsala para "generar un objeto/modelo 3D para DayZ", "crear un
  prop desde cero", "image to 3D", "convertir un GLB de IA en .p3d", Hunyuan,
  Tripo o Rodin, y low-poly realista. Decide el generador y los gates del front-end;
  alimenta dayz-model-pipeline, el pipeline de texturas y dayz-pbo-build, no los
  sustituye. Compón con blender-assembly, dayz-3d-viewer y 3d-generation-harness.
  hunyuan3d-local es opcional/externa (no va en este pack). No usar para humanoides ni animación.
---

# ai-3d-to-dayz

AI-assisted generation front-end to produce a 3D asset **game-ready for DayZ** from an
idea. Workflow scaffold: structure and handoffs are verified; specific tool-picks are
claims from @stefan_3d_ai channel marked `❓ validate` until confirmed with own tests.

> **Source and status:** distilled from 33 channel videos. KB with timestamps in
> `<knowledge-notes>\ai-3d-pipeline\` (`index.md` + 6 stages). Tool
> names / versions / settings = creator claims, NOT facts. Verify before trusting (R2).

## WHEN TO USE

- User wants an object/prop/item for a DayZ mod and does not want (or cannot) model by hand.
- Reference image exists, or one can be generated.
- Target = **static props/items or with mechanical parts** (weapons, containers, gear, world props).
- DO NOT use for: humanoid characters, or when primary need is skeletal animation (channel
  pipeline does not cover DayZ config-driven animation — see KB `stage-05-animation`).

## PIPELINE (scaffold idea → .p3d)

1. **Reference.** Clean image: white background, lit from all sides, no extra objects. Tools
   `❓ validate`: Nano Banana / Krea / 3D AI Studio. **ALWAYS remove background** before image-to-3D.
2. **Generate mesh.** Geometry > texture (DayZ remakes texture). Routes verified as available:
   - **Hunyuan 2.1 local** (RTX 3090) → optional external skill `hunyuan3d-local` if installed (not distributed in this pack). Control `target_face_number`.
   - **Tripo / 3D AI Studio** (paid access) → paid route to generate mesh; request low-poly with polygon control. No skill in this pack automates it.
   - Control poly count DURING generation; without limit, every tool produces millions of tris.
3. **Clean + retopo.** Import GLB into Blender (invokes `blender-assembly`). Reduce to low-poly **manifold**:
   Retopoflow (manual) or Quad Remesher; or AI auto-retopo (Tripo/Rodin/Hunyuan) **+ mandatory cleanup**.
4. **UV + normal bake (high→low).** Step generating `_nohq`. Blender Cycles, selected→active
   (low first, then high), Bake Type Normal, Non-Color, margin 8px, tune Extrusion/Max Ray Distance.
   Settings detail: KB `stage-01-mesh-retopo-uv-bake`. DayZ `_nohq` is DirectX-style (Y−):
   invert the green channel on export — verified fixture F7 in blender-assembly (Rule 11).
5. **Texture on UV.** Tool: **Modddif** ❓ (pending validation, backlog #3: UV-respect and map
   usability unverified) (color → `_co`; normal → `_nohq`; does NOT output roughness/metallic).
   `_smdi` is made separately (manual PBR in Blender, or repack Tripo ORM). DO NOT remesh a retopo'd.
6. **DayZ Handoff.** Assemble `.p3d` MLOD — **recommended option: Blender Arma 3 Object Builder add-on**
   (what DayZ community uses; native LODs/proxies/named selections) or py3d. `_smdi`: repack
   rough/metal with **SubstanceToArma preset** (R=white,G=metal,B=rough, invert rough). Convert to `.paa`
   (TexView/ImageToPAA), build `.rvmat`, binarize. → skills `dayz-texture-pipeline`, `dayz-model-pipeline`,
   `dayz-pbo-build`. Preview with `dayz-3d-viewer`. Validate in-game with `dayz-test-ingame`.

## HARD RULES (the pitfalls that break DayZ)

- **AI is only high-poly BLOCKOUT, it does NOT produce game-ready assets for DayZ** (confirmed by
  independent counterfactual, 2026-06-23). The official Bohemia/Enfusion pipeline requires manifold+closed+convex
  geometry and ships a Model Quality Assurance marking non-manifold/ngon/non-convex
  as defects — precisely what AI + auto-retopo generate. AI output ALWAYS goes through manual retopo
  (Retopoflow/Quad Remesher) + UV + bake + Object Builder validation before `.p3d`. "AI auto-retopo
  sufficient" = REFUTED. (links to `dayz-binarize-vertex-limit`; detail in `20_Knowledge/ai-3d-pipeline/counterfactual.md`).
- **NEVER trust placement / orientation / scale of a `.p3d` to AI vision** — it is the documented
  weak link (rotates 90°, does not reposition). Use numerical checks (verify_bounds) + diff against reference
  image. (links to `blender-visual-review`).
- Texture tools **MUST texture over existing UV**, not remesh an already retopo'd model.
  Verify this point on any new tool before putting it into pipeline.
- DayZ vertices = point×normal×uv per LOD. Budget is not "faces"; shared normals reduce count.
- Tool names/versions/settings marked `❓` are **unverified claims from creator** — confirm
  against actual tool before encoding them as truth.

## TOOL SHORTLIST (estado)

| Tool | Role | Status |
|---|---|---|
| Hunyuan 2.1 (local) | generate high-poly **blockout**, poly control | available ✅ (external skill `hunyuan3d-local`, not in this pack) |
| Tripo / 3D AI Studio | generate low-poly mesh, retopo, PBR | access ✅; **#1 in independent low-poly arena (Top3D 71.8%)**; ⚠️ Smart Low-Poly behind paywall |
| Blender + Retopoflow/Quad Remesher (or ZRemesher/InstaLOD) | manifold retopo, UV, bake | core ✅ — **unavoidable** (AI does not replace it) |
| **Arma 3 Object Builder** (Blender add-on, MrClock8163) | native `.p3d` MLOD: LODs, proxies, named selections, RVMAT, RTM | ✅ **DayZ community standard** (Discord + dep. DayZ-LOD-Tools); **substitute/complement for py3d**. Official link below, under "Key external links" |
| **Modddif** (ex-"Modif/Motif") | color (`_co`) + normal (`_nohq`) over existing UV | ✅ free; NO roughness/metallic |
| 3D AI Studio / Meshy Texture | full PBR (albedo+normal+rough+metal) over existing UV | ✅ confirmed; repack to `_smdi` |
| Sloyd (parametric) | templated props (barrels/crates/weapons) quad+UV+LOD out-of-box | ✅ less cleanup than AI for simple props |
| Rodin (Hyper3D) | mesh editing, parts, PBR | access ✅; #3 low-poly arena |
| AI animation (Mixamo/AccuRig/Cascadeur/…) | humanoid rig/anim | LOW for DayZ props |

## VALIDATION BACKLOG (harden this skill after this)

1. ~~A/B generation: same DayZ prop via local Hunyuan 2.1 vs Tripo → geometry + poly control.~~
   RESOLVED by the 2026-06-10 mk47 shootout (hunyuan3d-local §"Hard-surface → fal.ai") + the 2026-06-23
   full-body case: local 2.1 wins as default (free, organic, concept iteration); fal Hunyuan 3.1 Pro for
   fine hard-surface; fal Rodin 2.5 for organic full-body; Tripo 2.5 gave efficient direct low-poly
   (92k tris) but was not the pick.
2. High→low normal bake (Ep.3 workflow) → export → `_nohq.paa` → validate in-game.
3. Modif on prepared UV → does it respect UV? do maps work for `_co`/`_nohq`?
4. LOD batch via Blender-MCP: prompt decimating to N targets + downscale textures → LOD prototype
   (any VISUAL decimation is user-gated — rule 2026-07-02: ask before, default is manual by the user).

Upon confirming each item: replace corresponding `❓` with verified data + citation, here and in KB.

## SOURCES

- KB: `20_Knowledge/ai-3d-pipeline/index.md` (+ stage-00/01/04/05/07/08).
- **Counterfactual + deep dives:** `counterfactual.md`, `arma3-object-builder.md`, `alternatives-deep-dive.md`. These are private research notes and do **not** travel in this pack; what they decided is already summarized above.
- Key external links: [Arma3 Object Builder](https://github.com/MrClock8163/Arma3ObjectBuilder) · [SubstanceToArma (preset `_smdi`)](https://github.com/MoonieFR/SubstanceToArma) · [Top3D low-poly arena](https://www.top3d.ai/leaderboard?type=low-poly).
- Transcripts: `30_Research/youtube/stefan_3d_ai/` (33 videos) + `_counterfactual/` (5 independent).
- Extraction skill: `youtube-research`.

## (added 2026-06-23) Ruta personajes / infected (zombis)

For a humanoid character or creature (zombie / DayZ infected) do NOT author from scratch: reskin of a vanilla.
Verified recipe in `20_Knowledge/dayz-custom-infected.md` -- inheriting `ZombieMaleBase` reuses skeleton
`OFP2_ManSkeleton` + vanilla animations + AI (free by inheritance of the `enfanimsys` block); the actual cost is
rigging the mesh to the vanilla bones. DayZ runtime scaling broken (T140705) -> bake the size into the
mesh. Organic full-body mesh generation goes through fal Rodin (see hunyuan3d-local added 2026-06-23).

## Rules promoted from the lessons corpus (added 2026-07-27)

Promoted from `AI/20_Knowledge/lessons-learned.md` so that they arrive via trigger instead
of relying on someone remembering to look them up. Each rule cites its source `LL-NNN`;
the full entry (symptom, origin, evidence) lives there. Do not remove the citation: the index
`lessons-index.md` detects promotion by searching for that reference inside the skills.

- **LL-154** — Prepare reference with rembg, autocrop, white background, margin, and filled transparent holes; use full body when the output requires it. After generating, validate `trimesh.extents`: a near-zero axis is a planar failure even if the render looks plausible.


## (added 2026-08-31, SP-071) Generic-DCC visual winding at MLOD emission

Every route of this skill reaches the MLOD as geometry authored in Blender: the generator's mesh
(GLB, OBJ or FBX) is imported, retopologized, unwrapped and baked there (steps 3-4). Emit it with
the FBX / Blender-authored bullet of `dayz-model-pipeline` Rule 12, whatever format the generator
wrote (the mesh is Blender-authored by then; the GLB/glTF case does not apply): the det=-1 map
`(x,y,z)->(x,z,y)` on every point and normal of every LOD, faces in their original order, shading
normals negated (py3d >= 1.8.0: `py3d.blender_to_dayz(model)`, called once, before adding anything
built in DayZ space, such as collision boxes made in code, which skip the map). Do not reverse the
faces. Winding gates cannot see a mirror, so check chirality on an asymmetric feature too (Rule 12);
an MLOD written by another exporter, such as the Arma 3 Object Builder add-on, gets the same checks,
winding and normals with `dayz-p3d-audit` included. On this skill's own route, LFInfectedBig (an
AI-generated GLB, retopologized and rigged in Blender) read correctly in game with this map, and
mirrored with its shipped det=+1 recipe of reversed faces (`dayz-characters`
`references/character-rigging.md` §6, 2026-10-02).

Reverse the vertex order of every **visual** face only for a source whose own lineage was measured
to need it: an in-game A/B against the all-visual-faces-flipped variant plus a chirality check.
Proxy triangles are exempt: their winding encodes the proxy frame. SP-071's one calibration does
not qualify: the LFHeli OH-1 (2026-07-19) was an artist's Blender model exported as OBJ and mapped
with the det=+1 rotation `x'=x, y'=z, z'=-y`, the map Rule 12 measured in game as a mirror; the
reversal made it render solid, and nothing in that verdict checked chirality. Do not carry the
reversal to a vehicle or reconstructed source profile either: those keep their own measured
lineage.

A pre-binarize census of `dot(cross(v1-v0, v2-v0), mean_stored_normal)`, excluding
`abs(dot) < 1e-9`, reads whether the stored normals agree with the winding, not which side
renders. Its OH-1 thresholds (at least 95% negative `SOLID`, positive-dominant `INVERTED`) belong
to that pipeline, which stored the normals outward against an inward winding; a Rule 12 export
stores them inward like the winding. [OFFLINE MEASURED 2026-10-03] On the MLODs of the Rule 12
in-game test, rebuilt byte for byte by `tools/py3d/tests/test_s7_blender_to_dayz.py`, the export
that rendered solid and read correctly reads 0% negative, `INVERTED` by those thresholds; the same
export with every face reversed (winding outward: inside-out) and SP-071's own recipe, the det=+1
map with reversed faces and outward normals (a mirror), both read 100% negative, `SOLID`. Normals
stored outward render solid but lit inverted (`character-rigging.md` §6). Read a Rule 12 export
with `dayz-p3d-audit` instead: a healthy single-sided MLOD reads about 100% agreement ("Absolute
winding check", rule 1), and the direction comes from the signed volume by winding of each closed
shell, even at 100% agreement, never from the sum over the LOD: one shell reversed with its normals
negated keeps 100% agreement and a negative sum (Check A in `references/winding-diagnostics.md`).
Open sheets and double-sided parts take the visibility battery of "From Check B to fix"; isolate a
mixed result per part before any bulk fix (rule 2).

This census is a **profile signal, not a universal gate**. Do not compare its ratios across
ODOL, MLOD produced from ODOL by an external ODOL->MLOD converter (not distributed with this
pack), raw DCC MLOD, or vanilla references: stored-normal conventions differ by origin. Only
enforce a threshold after an in-game A/B has calibrated that exact source pipeline. The final
verdict remains the in-game A/B between the candidate and an all-visual-faces-flipped variant.
That A/B cannot see a mirror either, since both variants share the map: check chirality too.

*(Aligned 2026-10-03 with Rule 12, measured in game 2026-10-01. This section read "For a raw
Blender, OBJ, glTF, or FBX import whose measured axis transform preserves winding, reverse the
vertex order of every **visual** face when emitting the authoring MLOD.", "Keep this step in the
generic-DCC profile handed to `dayz-model-pipeline`; do not generalize it to a vehicle or
reconstructed source profile with a different measured lineage." and "A pre-binarize census of
`dot(cross(v1-v0, v2-v0), mean_stored_normal)` can predict the result inside a calibrated source
profile. Exclude `abs(dot) < 1e-9`. At the measured generic-DCC calibration, at least 95% negative
is `SOLID`, positive-dominant is `INVERTED`, and an intermediate result means mixed per-piece
winding that must be isolated before a bulk fix.")*

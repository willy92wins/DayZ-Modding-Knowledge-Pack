---
name: dayz-vehicles
description: >
  Author, import, debug and ship DayZ ground/water vehicles: CarScript cars,
  trucks, quads/ATVs and motorbikes plus Boat-based watercraft. Covers the
  config.cpp/model.cfg contract, drivetrain/engine/suspension, Axles/Wheels,
  Crew/get-in/actions, AnimationSources, structural parity, LODs, wheel/crew
  proxies, View/Fire/Geometry, placement, winding and dedicated-server
  packaging failures. Use for car/truck/quad/ATV/moto/boat, drivable vehicle,
  CarScript, civiliansedan parity, importing Blender/OBJ/ripped racing-game vehicles,
  "get-in broken", wheels missing/not steering/spinning backwards, white or
  untextured vehicle, vehicle build/pack/binarize or proxy pose. Always invoke
  before authoring/debugging a vehicle entity, config.cpp or model.cfg. Use
  dayz-aviation for flight and dayz-model-pipeline for generic assembly.
---

# DayZ Ground Vehicle Modding

## Selector de familia — ruta crítica day-0 (CAMBIO-2)

1. Identifica la familia por el origen y la arquitectura del asset; no por el síntoma.
2. Si el asset es un coche source-game/Grub nuevo, proxy-split y con partes móviles, usa **familia B**.
3. Familia B → abre `../rip-vehicle-import/SKILL.md` y sigue únicamente su adaptador, golden y allowlist.
4. Ese adaptador abre el `asset-contract.json` del asset como tercer y último fichero day-0; schema, export Blender y primitive son inputs de máquina, no documentos adicionales que el agente mantenga.
5. Si ya existe un plan/runbook congelado para el asset, sigue ese contrato en vuelo; no lo migres aquí.
6. Si ninguna fila aplica o falta el adaptador de la familia: **STOP**. No improvises desde este atlas.

| Señal de entrada | Adaptador | Ficheros day-0 |
|---|---|---|
| source-game/Grub, coche nuevo, proxy-split + puertas/partes móviles | Familia B | Este router → `../rip-vehicle-import/SKILL.md` → `<asset>\asset-contract.json` |
| Asset ya en vuelo | Runbook congelado del proyecto | El que cite su plan vigente |
| Otra familia o datos insuficientes | Ninguno | **STOP** |

El resto de este body es atlas de diagnóstico y **no forma parte del camino crítico day-0**. Solo se consulta cuando el adaptador o un síntoma enlaza una sección concreta.

**Preflight antes de re-importar / re-ensamblar cualquier pieza** (SP-193): mide primero la completitud A NIVEL DE CARAS de la pieza de fábrica contra el modelo ya empaquetado. Una malla "podrida" suele estar completa y el defecto estar en otro sitio; ver SP-193 al final de este atlas.

---

Drivable wheeled vehicles in DayZ extend **`CarScript`** — there is no generic "vehicle" base, and
you do not build one from `EntityAI` or `Inventory_Base`. `CarScript` gives wheels, seats, sound
integration and the damage system for free; you configure the rest. This skill is the
vehicle-specific layer on top of `dayz-model-pipeline` (generic geometry / LODs / textures) and is
the ground counterpart to `dayz-aviation` (anything that flies belongs there).

Scope: cars, trucks, quads/ATVs, motorbikes — anything wheeled and drivable, modeled from scratch
or imported (Blender / OBJ) from another game.

> REDIRECT CAMBIO-1: el selector de familia de la cabecera y el adaptador elegido son la única ruta day-0.

**Vehicle type matrix (invariant):** `Car` and `Boat` are SIBLINGS, both directly under `Transport`
(`car.c:98` / `boat.c:31`) — NOT parent/child. `Transport` owns crew/get-in/flip/fuel; `Car` owns
wheels/brakes/`CarFluid`; `Boat` owns propeller/buoyancy/`BoatFluid`(fuel-only). A truck is a plain
`CarScript` config with 3 axles + double wheels, NOT a new class. Boats, truck double-wheels, ATV and
the motorbike gap → `references/vehicle-types-boat-truck.md`.

**Per-tick event asymmetry (invariant, added 2026-07-29, LFHeli OH-1):** `CarScript` has NO
`EOnSimulate` — its ctor registers only `POSTSIMULATE`/`POSTFRAME` (`carscript.c:325-326`) and ALL
its per-tick work (engine, fluids, part health, fuel/engine auto-stop, exhaust and wheel FX, much of
it gated `IsServerOrOwner()` so it is meant to run on the owner client) lives in `EOnPostSimulate`
(`carscript.c:948`). `BoatScript` overrides BOTH (`boatscript.c:347` and `:385`). Consequences on a
car: hook `EOnPostSimulate` for per-tick logic; `super.EOnSimulate` is the empty stub at
`enentity.c:201-203`, so calling or skipping it does nothing either way — treat any comment claiming
it "runs engine/fluids twice" as false. Custom solvers that add `SetEventMask(EntityEvent.SIMULATE)`
and pump it by hand (aviation) → `dayz-aviation` preflight invariants.

**Mirror-vs-rotation invariant (added 2026-08-02, LFHeli HH-60G):** before you declare an
imported model "mirrored" and reach for the `det=-1` import rule, **check all THREE axes**. A table
of memory points cannot tell a reflection from a rotation on its own — points have no handedness, so
only the PATTERN of sign flips does:

**The general test is the SIGNED VOLUME, not counting axes.** Take four LABELLED, non-coplanar
corresponding points (A,B,C,D) and compute `det[B-A, C-A, D-A]` on each side. An individual point has
no handedness, but a labelled tetrahedron does:

- signed volume **keeps its sign** -> proper transform (`det=+1`) -> rotation. The model is FINE and
  `det=-1` would ADD a mirror that is not there.
- signed volume **flips sign** -> improper transform (`det=-1`) -> the reflection is real; apply the
  `det=-1` import rule plus pseudovector (`-S.n`) normals.
- volume ~= 0 -> your four points are coplanar: pick others, the test says nothing.

Counting inverted axes is only the axis-aligned shortcut of that test, and it is easy to misread:

| axes flipped (axis-aligned case only) | what it is |
|---|---|
| ONE inverted, other two intact | reflection |
| TWO inverted, third intact | rotation of 180 deg about the third axis |
| all three inverted | point reflection = 180 deg rotation + mirror; decompose before acting |

Real case, and it nearly cost a full re-emission of 16 `.p3d`: one session measured only X, saw the
sign flipped and concluded "mirrored"; the user authorised de-mirroring. Measuring Z too showed
**38/38 points with X and Z inverted and Y intact** — a 180 deg yaw (det=+1), which is the pipeline's
normal convention, not a defect. Control that settled it: the sister airframe that already flies
in-game has the SAME convention (nose at -Z in the file). Applying `det=-1` would have introduced a
real reflection where none existed and broken a winding policy already verified in-game. The
review that settled it did exactly the tetrahedron test: `+6.076679` in file against `+6.076514`
in runtime, ratio `+0.999973` - same sign, proper transform, argument closed without a game cycle.

**Say what the test does NOT cover.** A proper file->runtime transform does not rule out a mirror
baked in EARLIER (before the `.p3d`, in the source mesh or the exporter) nor a pre-mirrored UV
island, which is a texture defect and shows up as backwards lettering with the geometry perfectly
correct. Those are separate investigations with separate evidence; do not let a clean parity check
close them.

**Corollary worth more than the rule — prefer RELATIVE measurements.** A comparison made *within one
file, through one reader* is robust to whatever axis convention your reader uses; an absolute
file-vs-runtime comparison is not. "The 10 crew proxies carry a frame rotated 180 deg from the 15
piece proxies" is sound even if you never establish which handedness py3d reports, because both sides
went through the same lens. When a diagnosis can be phrased as a relative comparison against a
control inside the same asset, phrase it that way and it survives being wrong about conventions.

**Imported-mesh budget invariant (added 2026-07-29, LFHeli HH-60G):** a **triples/triangle ratio
measured on a DECIMATED mesh does not extrapolate to an authored one.** `Decimate` collapses edges
and breaks normal sharing, so it inflates resolved (point, normal, uv) triples per triangle. Measured
on the same asset: **1.301** on the Decimate-ratio export (0.26-0.6 per group) versus **0.941** on the
source's own Medium LODs — 28 % apart, and enough to change how many sub-`.p3d` you plan for (2.43
projected LODs against 1.75 measured). Rule: measure the ratio on the geometry you will SHIP, not on
whatever export you have lying around. Corollary, and it is the bigger win: **if the source ships an
authored LOD ladder (GTA `.yft` High/Medium/Low, source-game, Sollumz-imported `.blend` datablocks), use it
instead of decimating** — swapping `obj.data` to the `<piece>_medium` datablock is usually better in
triples AND satisfies the "the agent never decimates visual" clause of a product spec. Re-measure per
model; never copy a ratio or a resolved ceiling between assets.

**Packaging invariant — a fix that lives in the generator and not in the binary does not exist
(added 2026-07-29, LFHeli HH-60G):** when the cycle's fix is *adding or changing a PROPERTY* of a
`.p3d` (`autocenter`, `class`, `sbsource`, `lodnoshadow`), a SHA-based manifest cannot see it — it
compares the same wrong file on both sides and reports green. Real case: `autocenter=0` was added to
the hull's visual LOD in both assemblers and the PBO was packed minutes later from `.p3d` built
before; measured afterwards on the **48 extracted** models, the 8 sub-models carried it and **all 40
hulls did not**. The post-`ExtractPbo` gate must READ the property, per LOD, on the extracted files.
Two riders that make the gate survive contact:

- Declare the expectation **in a table with a reason per row, never as "all LODs"**. A healthy pack
  contains **controls that exist in order NOT to change** (an A/B control arm, a byte-frozen
  baseline); a blanket gate rejects them and gets switched off on its first run.
- The producer must satisfy its own gate. Here "all LODs" would have rejected the canonical
  assembler's own output, because the Memory LOD has no geometry to re-centre and therefore never
  carries `autocenter`. Exclusions are declared, not assumed.

**Deployment-identity invariant — the artifact your gate validates must be byte-linked to the
artifact the game loads (added 2026-07-29, SUB_BRZ S42):** a native-contract gate that consumes a
separate ODOL stage says NOTHING about the deployed PBO. `-packonly` copies whatever format sits in
the compilable tree, and pairing MLOD↔ODOL stage files by homonymous path is not closure. Measured
case: the gate validated the ODOL stage doors (~2.1 MB each) while the live PBO carried the source
MLOD (8.7/8.1 MB, byte-identical to the MLOD stage) — nothing in the pipeline linked the two
artifacts, and the mismatch surfaced only during post-crash analysis. Rule, before ANY deploy of a
gated artifact: list the PBO, extract or slice every `.p3d` entry by offset, and require (a) the
expected signature (`ODOL` where the contract is ODOL) and (b) SHA-256 equal to the approved stage —
fail on wrong signature, missing entry, casefold/slash collision, or hash mismatch. Corollary:
record the mounted PBO's SHA-256 contemporaneously at every runtime launch; without that seal, no
post-crash analysis can prove which artifact the process actually loaded.

**Native-crash fingerprint — compare CODE BYTES, not fault addresses (added 2026-07-30, SUB_BRZ
S42):** the RPT's `Fault address` is not an identifier — ASLR moves the module base, so the same
code site prints different addresses across runs and reads as "different bugs". What identifies the
detection site is `Prev. code bytes` + `Fault code bytes` (16 bytes each) plus the engine `Version`.
Measured case: six `C0000374` crashes split across two addresses (`3523D5F9` and `57B5D5F9`) had
**byte-identical** code bytes and identical low 16 bits — one code site, one engine build. Reading
them by address had produced the (false, and formally rejected) claim that the ODOL-era and
MLOD-era crashes were unrelated; the byte comparison also killed the hypothesis that the artifact
FORMAT was the discriminating variable, since the crash appeared in both. Report "same/different
detection signature", never "same/different bug": `C0000374` is detected on free, not where the
out-of-bounds write happened, so an identical signature still does not prove identical cause.

## ITERATION BUDGET — check this BEFORE opening a front (added 2026-07-27)

Measured over one month of vehicle work (125 session handoffs: MercedesAMGLF 46, SUB_BRZ 38,
LFHeli 37): **26 sessions ended in STOP/BLOCKED/FALSIFIED against 24 green**. The three failure
modes below are process gates, not config facts — and each burned dozens of sessions on a
different project before being named. They cost more iterations than any invariant below.

1. **Count the cycles spent on one objective, and make the count block.** `DZ-R5` already says
   "after 2 rebuilds without progress, STOP and change strategy"; it does not bite because nobody
   tracks N. Carry `ciclos_en_este_objetivo: N` in the HANDOFF `LIVE-STATE`, and at N>=3 the
   re-entry gate must pick one of three exits before touching code: change strategy, escalate to a
   human, or drop the objective. Evidence: MercedesAMGLF Task 9 reached **v64 across 29 sessions**,
   and what finally closed it was shifting 28 proxy triangles by -0.240 m in X.

2. **Keep the test harness OUT of the product task.** Task 9 mixed "align the Mercedes proxies"
   (product) with "build an automated live verifier" (daemon, broker, lease, preflight, camera
   contract, JPEG SHA) — the harness silently took the bulk of the time and became the project.
   If a product task is blocked TWICE by the harness, stop the product and decide explicitly: scope
   the harness as its own project, or run that one test by hand and move on.

3. **When the judge is the eye, offline analysis gets ONE round.** Green offline gates do not
   predict the live result. A Task 9 build reported `263/263 global + verifier 35/35 hard PASS` plus
   every SHA, and then: `Visual: FAIL of evidence, client hung`. The LFHeli "seis frentes" night
   spent ~25 Codex sessions to produce refutations only (binding intact, re-bake refuted, clock and
   interpolation refuted) and concluded the discriminator was the user's own screenshot. If the
   discriminator is visual or feel, spend one offline round ruling out cheap causes, then go to the
   game — extra offline rounds postpone the verdict, they do not replace it.

Corollary already paid twice: SUB_BRZ needed 30+ sessions to conclude that a decimated rip mesh
cannot reach game-ready quality (pivot to a human artist), and the LFHeli HH-60G reached the same
verdict independently weeks later. A visual red that survives N rounds is a signal to escalate to a
human, not to run round N+1.

> REDIRECT CAMBIO-1: familia B → `../rip-vehicle-import/cookbooks/family-b/radial-puerta-ausente.md`.

## INV-ALIGN — a faithful import does NOT mean the pieces line up (added 2026-07-27)

**A bit-exact import and correctly-fitting pieces are different properties.** When a model is
assembled by script, each piece is placed at a **procedurally computed anchor** (centroid, bbox
centre, a reference point). If that anchor diverges from the real reference, the pieces sit wrong
while every import check passes. Paid three times (MercedesAMGLF, SUB_BRZ, LFHeli):

- MercedesAMGLF: the 28 wheel proxies sat **-0.240 m in X** from their Memory hubs. Fix: measure
  the offset with py3d and shift only those triangles (max error 0.0 m afterwards).
- LFHeli OH-1: import fidelity 12/12 at max 3.2e-7 m, and the `SEATS` procedural anchor still
  diverged **583 mm** from the source mesh.

**Gate before declaring an assembly good**: for every proxy, measure its anchor against the real
reference (the matching Memory point, or the source mesh position) and assert the delta is ~0.
Import fidelity, digest equality and structural diffs do NOT catch this — they compare the piece
to itself, not to where it belongs.

**Do NOT "fix" it by adjusting the pipeline transform.** That is the intuitive move and it is a
false fix: it displaces everything else that was already correct. Correct the individual anchor.

**False friend — `autocenter=0` is not this bug.** It is a real and separate requirement (the
engine recenters LODs by bbox without it, displacing collision ~20-25 cm from visual; see
`dayz-model-pipeline` and `dayz-p3d-audit`), but it does not cause or cure anchor divergence.
MercedesAMGLF spent a full RCA on that hypothesis and closed it as unproven: adding `autocenter=0`
to all 18 proxy LODs changed nothing geometric, and the protrusions and see-through were already
present in the earlier baseline. Do not re-run that investigation.

## TEXTURE OR MESH? — discriminate BEFORE auditing the texture pipeline (added 2026-07-27)

"The textures look wrong" on an imported vehicle is a symptom with at least three unrelated
causes, and auditing the texture pipeline is the **most expensive** way to find out which. Run
this ladder first; each rung is minutes, the full audit is sessions.

1. **Audit the UVs, not the textures.** Exact SAT overlap + island count + density
   (`uv-clean-atlas`, `uv_audit.py`). Overlap > 0, atomised islands (2-4 faces each) or wildly
   uneven density means the problem is upstream of any `.rvmat` — no material wiring fixes it.
2. **Ask where the mesh came from.** A decimated rip cannot yield game-ready UVs: the cause is
   topology, not the unwrap algorithm or the texture route. The fix is retopo (bake the high-poly
   onto a clean low-poly), and no amount of pipeline correction substitutes for it.
3. **Render the same material on a known-good control.** If a vanilla-derived control looks right
   with the same route, the pipeline is exonerated and the defect is in this asset.
4. **Only now** audit `.rvmat` stages, `_co/_nohq/_smdi` paths, `.paa` conversion and
   `hiddenSelections` — see `dayz-texture-pipeline`, and its
   `references/vehicle-materials-and-color-variants.md` for the vehicle-specific shader choice
   (Super where faces carry a `_co`, NormalMapSpecularMap for constant-colour parts, tiled detail
   for overlapping or un-baked UVs).

**Cost rule**: if two rounds of pipeline auditing come back clean, "the texture is applied wrong"
is REFUTED — change branch instead of running a third. An audit that exonerates the pipeline is
evidence about where the bug is NOT, and repeating it produces no new information.

Evidence for the rule: on LFHeli OH-1, F6 ran a double audit that exculpated the entire offline
chain (UVs identical across blend/MLOD/ODOL, old PAA identical to new, `rvmat uvSource=tex`, zero
`hiddenSelections`, no faces inside the watermark box) — the textures were never the problem. On
SUB_BRZ the documented root cause was the decimated rip's topology, reached after six rounds and
a pivot to a human artist. In both cases the ladder above would have branched away on rung 1 or 2.

### Rip-specific rung 0 — a "paint" material in the source has NO diffuse; never substitute a livery sheet (added 2026-07-27)

Before running the ladder on a **ripped** vehicle (GTA, source-game, any game rip), census which source
material each face carries and what the import mapped it to. Game rips colour the body through the
host game's **paint system**, not through a texture: in GTA those materials are
`vehicle_generic_smallspecmap*` / "primary" and their diffuse is legitimately **absent or a
zero-byte file**. An importer that needs *some* texture per face will silently fall back to whatever
is available — and if what is available is the model's **livery/decal sheet**, the result is signs,
numbers and camo stamped across the whole fuselage. The symptom reads as "the UVs are wrong" or
"textures are crossed", and both readings send you down the expensive branch.

- **Discriminator (minutes)**: count faces per `(source material -> texture)` pair. A single texture
  carrying a large share of the model, especially a decal/livery atlas, is the signature. Cross-check
  the source file size on disk: a **0-byte** or missing DDS proves the fallback fired.
- **Fix direction**: those faces want a **flat colour `_co`** (the host game's paint slot has no DayZ
  equivalent), not the decal sheet and not a re-unwrap. Their UVs were never meant to address a
  texture, so no UV work is involved.
- **Measured evidence.** LFHeli HH-60G (2026-07-27): `hh60g_sign_1_co.paa` — a 22.4 MB livery sheet —
  carried **23,716 / 35,385 faces (67%)**, of which **8,695 (24.6% of the model)** were pure fallback
  (7,568 of the body's `[PRIMARY]` material plus all four doors), with
  `vehicle_generic_smallspecmap3.dds` confirmed **0 bytes** on disk. The user's independent report was
  "things and colours drawn where they don't belong". The OH-1 line hit the same class separately
  (rotor blades wearing camo and a registration number) after the PAA route had been exonerated.
- Status honesty: the diagnosis is measured; the flat-colour fix was **not yet confirmed in-game** at
  the time of writing — treat the fix direction as unverified until a cycle closes it.

## A mesh DRAWN in the wrong place is invisible to every script transform — qualify the probe first (SP-138, added 2026-07-29)

When the user reports that a vehicle **draws** somewhere the entity is not — body on the ground while
the vehicle climbs, a part left behind, a piece floating — the reflex is to instrument the transforms
and compare. **That reflex has already been paid for and it returns nothing.**

Measured on LFHeli OH-1 over a 26 m climb: root position, `GetRenderTransform`, both bones, the
physics body (`dBodyGetWorldTransform`) and the pilot's world position **agreed digit-for-digit**
while the hull was drawn on the ground. Recorded in that project's own code at
`LFHeliCore\scripts\4_world\LFHeli\LFHeli_Base.c:3106-3113`. The consequence is the general rule:

> **Any probe derived from the entity root inherits the root's blind spot.** A drawing-position defect
> lives downstream of every transform Enforce exposes, so no amount of transform logging can see it.

**What does work** — a marker the engine projects from a WORLD point without consulting the entity's
transform, read off a screenshot: `Debug.DrawSphere` at `GetPosition()` plus a ladder of rungs at
fixed spacing below it. The rung spacing is what makes the defect **quantitative** (gap in metres =
rungs × spacing) instead of an eye report. Reference implementation: `LFHeli_Base.c:3114-3128`.

**Probe qualification, mandatory before any number adjudicates:** read the magnitude in the regime
where the drawing is CORRECT (on the ground) and in the regime where it is WRONG (airborne). If it
does not change while the eye sees a difference, that magnitude is **blind** — stop using it. A delta
of exactly `0.000` is a tautology signal, not precision.

**The companion trap, on the inference side.** Over flat ground, "the visual Y is frozen at its
take-off value" and "the transform is computed from a ground-referenced magnitude" produce **the same
two signatures**: gap grows with height, gap returns to zero on landing. Arithmetic, confirmed by
external review. So the flat-ground signature must never be used to EXCLUDE a family of causes — it
identifies nothing. Discriminate by changing the regime, not by reasoning:

- horizontal traverse at constant world Y over terrain ≥15 m lower — ground-referenced tracks the
  terrain, frozen-Y does not;
- descend without touching down and climb again — a replication/state split shows hysteresis, a pure
  function of height does not.

- Status honesty: the blind-spot measurement and the flat-ground ambiguity are **verified**; the two
  discriminant manoeuvres above were designed on 2026-07-29 and **had not been run in-game** at the
  time of writing. Treat them as an untested procedure until a cycle closes it.

> REDIRECT CAMBIO-1: familia B → `../rip-vehicle-import/cookbooks/family-b/get-in-ausente.md`.

## INVARIANTS YOU WILL HIT — preflight checklist (read BEFORE authoring, not after the in-game fail)

These recur on **every** vehicle. They were each won the hard way on one project and then re-derived
from scratch over dozens of iterations on the next (LFQuad → SUB_BRZ → MercedesAMGLF), because they
were not promoted to this checklist in time. Check them up front; full detail behind each pointer.

**BEFORE any numbered gate below — calibrate the gate itself (SP-132, added 2026-07-29; LFHeli HH-60G + OH-1).**
Two rules in this file already cover this — §"Calibration + scope (so a gate is trustworthy, not a false
green)" and §METHOD habit 2 ("never close a phase on a tautological gate"). Both were live and **neither
fired across four gates in one week**, because both read as being about *car render/winding* gates. They
are not: they govern every item below, and capacity, parity, telemetry and policy gates alike. The four
shapes, so they are recognizable on sight:
- **A threshold copied instead of measured.** `hh60g_assemble.py:29` carried `RESOLVED_LIMIT = 65535`;
  the engine's real resolved-vertex ceiling on that model is **46.133** (42% lower), so the gate passed
  models `binarize` rejects with `Too many vertices`. The cap is model-dependent (×1.4205 on HH-60G,
  ×1.46 on OH-1) — never copy it between models, re-measure with binarize.
- **A policy that is a mathematical no-op.** `uniform` and `keepdot` were geometrically inert
  (`dot(-cross,-n) == dot(cross,n)`); four variants were built on them before the identity was checked.
- **A gate that shares the producer's frame.** OH-1 seat parity compared under pure translation — the
  same assumption the sub-model was generated with. `delta 0.000` proved producer and gate agreed, not
  that either was right.
- **A field read selectively.** `attachment_count=2` was signed PASS because that one field matched
  expectation; the regression sat in the same output 20 min before the user hit it in-game.

**One minute, before trusting any gate:** (a) run it against a KNOWN-BAD case — green on a known-bad
means the bug is the gate, not the artifact; (b) name in one line the assumption the artifact was BUILT
with, and confirm the gate does not reuse it. A gate that has only ever been seen green is unmeasured,
not verified.

0. **Gate #0 — mesh + UV health BEFORE anything else (SP-052).** For ANY imported model (source-game or not),
   the FIRST step is a mesh+UV audit, because a broken mesh produces false downstream diagnostics (a
   "double wall" that was mirrored UV on a single wall; a "convexity" issue that was open design-boundary
   edges). (a) audit `mesh_health.py` (boundary / non-manifold / dup-verts / dup-faces / winding per
   piece) + `uv_audit.py` (islands / overlap / density / mirrored); (b) sanitize with an ADAPTIVE weld
   (ladder 0.5→0.01 mm; gates: NM must NOT grow + UVs preserved — a blind 0.5 mm weld FUSES
   legitimately-touching pieces and CREATES non-manifold); (c) unwrap BY SECTIONS per
   `AI/20_Knowledge/uv-mapping-dayz.md` §0.5/§5; (d) gates: overlap ~0% for bake, uniform density, atlas
   legible by a human, checker render with SMOOTH shading (flat shading + grid raster read as a false
   "low-poly/blurry"). Tools in `LFQuad_dev\tools\` (mesh_health.py, mesh_sanitize.py bpy-headless;
   uv_audit.py py3d) — portable to any vehicle. → `AI/20_Knowledge/uv-mapping-dayz.md`, winding #10(f).

0b. **Gate #0b — when LOD1/2 come from DECIMATE instead of an artist, audit the modifier's OUTPUT
   (added 2026-08-06, MercedesAMGLF).** No artist is now the normal case, so per-object COLLAPSE +
   planar DISSOLVE is the default LOD path. The modifier leaves **loose vertices** — vertices no
   triangle indexes. Every count-based gate stays green (triangles, resolved, identity, monotonicity,
   frame parity), and the streams ship broken: a per-vertex extract loop driven by `mesh.loops` never
   reaches a loose vertex, so whatever the array was initialised to is what gets written. Initialised
   to `(0,0,0)` → **zero-length normals in NORMAL.bin**. Measured: source had 0 loose in 224.700 verts;
   after decimation, 786 at LOD1 and 4.024 at LOD2 — plus 16 normals of length down to `3e-6` that a
   `> 0` usability test happily passed. Three checks close the whole class:
   - delete loose verts after every decimate (`bmesh.ops.delete(bm, geom=[v for v in bm.verts if not
     v.link_faces], context="VERTS")`). NOT one of the three forbidden calls — it removes only geometry
     no triangle references. Skip the bmesh round-trip entirely when there is nothing to delete, so
     must-keep pieces never pass through it.
   - assert every emitted normal is unit length and normalise on emission. The real cut is **0.5**, not
     0: a unit normal survives float32 within ~1e-7 of 1.0, so anything shorter is a cancelled sum.
     Substitute from NEIGHBOUR normals, never from `poly.normal` — if the import transform negates an
     axis it is a mirror, and the winding-derived normal points the opposite way (see #10 winding).
   - assert every index falls inside its own piece's vertex range. No count gate sees an out-of-range
     index; it explodes at assembly.

   **Gate corollary — a drift number that mixes classes is not a measurement.** Split survivors into
   INTACT (incident-triangle set identical to LOD0 → drift MUST be ~0; any drift here is a real defect),
   RECOMPUTED (topology changed → drift is legitimate) and DEGENERATE (counted, never averaged in).
   Mixed together, a p99 of `90.00°` hid a real defect AND hid that untouched geometry was clean at
   ≤0.26°. An exact round angle is a fingerprint, not a result: `90.00` is `acos(0)` = a null vector on
   one side. Match survivors on a ~1e-4 m grid, not 1e-6 — positions are written as float32 and a 1e-6
   grid drops about a third of the untouched vertices at random, which is why the samples looked tiny.

1. **"Get in" radial needs a real SCRIPT CLASS, not a bare config class.** A `class <Mod>: CarScript`
   with no `.c` runs as bare `CarScript`, which inherits `Transport.CrewCanGetThrough()` → **`false`**
   (`scripts/3_game/vehicles/transport.c:493`) → the get-in action is filtered out and **never appears,
   no bone/proxy/componentNN fix helps**. Author `<Mod>_Base extends CarScript` overriding
   `CrewCanGetThrough` + `GetAnimInstance` + `GetSeatAnimationType` (+ `CfgMods` worldScriptModule).
   Verified in-game LFQuad D34 + MercedesAMGLF + SUB_BRZ. → `vehicle-structural-parity.md` "Crew get-in".
2. **The script module must actually LOAD or the class never binds — silent.** `CfgMods` `files[]` with
   back-slashes / a `.p3d` path that resolves to `*.p3d.p3d` → module not loaded → no get-in, no error.
   → `SKILL.md` §"Binding del script", `rip-import.md`.
3. **REDIRECT CAMBIO-1 (familia B):** `../rip-vehicle-import/cookbooks/family-b/wheelpresent-0.md`.
4. **Seats and wheel hubs must be `componentNN`-tagged (dual-tag) — AND each seat component must be raycast-collidable.** The engine enumerates collision
   components only by `componentNN`; a seat/hub that is a standalone island (0% componentNN overlap) is
   invisible → spawn blocker / no seat. Tag the SAME faces with a `componentNN` too. **Then the ViewGeo seat cube
   must be INWARD-wound with every point flag = `0x02000000`:** a py3d box left outward + flags 0 passes every
   offline shape/winding/dual-tag check yet `RaycastRV(ObjIntersectView)` does NOT hit it → the get-in cursor
   falls through to component0 → the driver "works" by fallback but the CODRIVER never resolves. The decisive,
   in-game-confirmed copilot blocker on BOTH SUB_BRZ (s9) and MercedesAMGLF (s12) — copy winding+flags from a
   positive control (LFQuad/Croco), never trust py3d's default. → "componentNN DUAL-TAG" + "CRITICAL EXTENSION 2026-06-28" (`vehicle-structural-parity.md`).
5. **Crew/wheel proxies must exist in BOTH ViewGeometry AND FireGeometry**; the proxy triangle uses the
   engine identity frame (`R=((-1,0,0),(0,0,1),(0,1,0))`, model-space), NOT py3d `rotation=None`. → parity + rip-import.
5b. **`wheelHub` names a GEOMETRY/MEMORY selection, not the visual `wheel_X_Y` — and the visual
   `wheel_X_Y` IS the proxy's own triangle under a second name (added 2026-08-07, MercedesAMGLF).**
   `class Wheels { class Left { wheelHub="wheel_1_1_damper_land"; } }` resolves to a selection that
   lives in Geometry `1e13` (a ~0.20 m hub box) and Memory `1e15` (1 point) — vanilla
   `DZ/vehicles/wheeled/config.cpp:297`. It is NOT the `wheel_X_Y` selection on the visual LOD.
   Measured on two independent cars: that visual companion has the SAME centroid and the SAME bbox
   as its `proxy:<path>.NNN` selection, i.e. it is one triangle carrying two names (vanilla shows it
   as 1 face too). Consequences, each of which cost a session:
   - **A gate of the form "proxy anchor -> companion centroid == 0" measures nothing about the wheel.**
     It computes `|anchor - centroid|` of a single triangle, which is a pure function of that
     triangle's SIZE. Measured on the same model: 0.131757 m for a 0.339x0.204 triangle vs
     0.000745 m for py3d's canonical `scale=0.001`. Against the real hub both artifacts read
     **0.000000 m**. Point the gate at `wheel_X_Y_damper_land`.
   - **Proxy triangle size bakes NO scale.** The frame is derived from UNIT vectors
     (`py3d/__init__.py:174-179`, port of `proxy_frame.derive_frame`), and vanilla's binarised proxy
     matrix is orthonormal (`|aside|=|up|=|dir|=1.000000` on `civiliansedan.p3d` ODOL v54). A 1 mm
     canonical triangle and a 0.34 m one place the same wheel; SUB_BRZ shipped on `scale=0.001`.
     Do not "fix" a small triangle.
   - **Vanilla reference, if you need one:** `civiliansedan` puts the hub **0.106334-0.107333 m
     INBOARD** of the wheel proxy, the whole delta in X. Hub coincident with the proxy (0 m) is
     tighter than vanilla, not a defect.
   - **Before matching a magnitude to another open debt, decompose it by AXIS.** 0.1318 m was read
     as "the wheel drawn 13 cm off its simulated position" because it resembled a 0.136 m track
     debt; the 0.1318 lives entirely in Y/Z (`dX = 0.000000` exactly on all four wheels) and the
     track debt lives entirely in X. Orthogonal — the resemblance was numerology.
   - **Read a gate's PRODUCT verdict from a run WITHOUT its negative fixtures**, then repeat it on
     the known-good artifact as a control. Run with `--negative-fixture` and the fixture's
     deliberate reds (yaw-180 families, stripped companions) interleave with the product rows and
     read as product failures.
6. **Wheel `angle1` sign: measure the axle in the `.p3d` BEFORE setting it.** An offline check predicts
   reversed spin without an in-game cycle. → `build-packaging-and-debug.md` §2-3.
7. **Imported-model winding: keep the RAW glTF winding VERBATIM — NEVER orient to a normal oracle
   (authored/`__N`) nor to a radial/centroid heuristic (see #10j).** The pipeline's `__N` was never
   authored (`rip_p2_group.py:110,131` — smooth normals of the pre-mirror winding) and `orient_authored`
   inverted EVERY piece; repair only the ~0.5% source-inconsistent FACES by MAJORITY flood-fill per
   connected component, AFTER de-dup (#10e). Blender backface-cull render = HINT only (its convention
   false-greened once — it shows the +cross side, the engine renders the ANTI-cross side); in-game render
   is the gate. → #10(j) + `SUB_BRZ_dev\reviews\2026-07-02-s20-plan-reimport-unico-v2.md`.
8. **One vital igniter per car — vanilla defaults BOTH SparkPlug AND GlowPlug to vital, so a bare
   `CarScript` car silently demands BOTH.** `CheckOperationalRequirements` sets `NO_IGNITER` if either
   vital plug is missing (`carscript.c:2004` SparkPlug / `:2011` GlowPlug); every `IsVital*` defaults true
   (`carscript.c:2734-2762`, `transport.c:303`). A PETROL car (CivilianSedan) keeps SparkPlug vital and
   overrides `IsVitalGlowPlug()→false` (`civiliansedan.c:363`) + `IsVitalTruckBattery()→false` (`:358`);
   a DIESEL car (Offroad_02) mirrors it — `IsVitalSparkPlug()→false` (`offroad_02.c:389`). `attachments[]`
   must declare ONLY the vital plug and `OnDebugSpawn` must attach THAT part. "Engine won't start" with a
   SparkPlug already attached = the un-overridden GlowPlug, **NOT** a removed requirement — `IsVitalGlowPlug→false`
   IS the vanilla petrol pattern (the car still requires its SparkPlug). Bit SUB_BRZ (petrol car defaulted
   to needing a GlowPlug it had no slot for; a "remove the check" framing got it backwards). → `vehicle-config-and-modelcfg.md` §engine parts.
9. **Engine STARTS then immediately STALLS (eng=1 for one tick → eng=0 rpm=0) with fuel + ALL vital parts
   attached → the car is missing its `Engine` (and `FuelTank`) DamageZone.** `CarScript` stops a running
   engine EVERY tick when `m_EngineHealth <= 0` (`carscript.c:991`), and `m_EngineHealth =
   GetHealthLevelValue(GetHealthLevel("Engine"), "Engine")` (`carscript.c:2572-2573`) — a `DamageSystem.
   DamageZones` with no `class Engine` resolves "Engine" health to RUINED → perpetual `EngineStop()`. A
   missing `class FuelTank` compounds it (`carscript.c:1004` ruins the Engine zone when FuelTank reads
   RUINED). EVERY vanilla car ships BOTH zones; an imported/regen car declaring only body zones
   (chassis/front/back/roof) LOOKS configured but the engine never sustains. Fix: add `class Engine` +
   `class FuelTank` to `DamageZones` — the proven shape (vanilla/SUB_BRZ) points `componentNames[]` at a
   FireGeo `dmgzone_engine`/`dmgzone_fueltank` selection; a config-only health zone (empty `componentNames[]`/
   `memoryPoints[]`) is the minimal variant (verify it registers). DISTINCT from #8: #8 gates whether the
   engine STARTS (vital igniter parts); #9 gates whether a STARTED engine STAYS ON (engine-health zone).
   Bit MercedesAMGLF (stalled with SparkPlug+CarBattery+CarRadiator+fuel+coolant ALL present; SUB_BRZ ran
   only because it carried both zones). Verified vs `carscript.c` source + SUB_BRZ in-game parity.

10. **Imported-car offline VISUAL gates that LIE — the #7 family (offline geometry heuristic != in-game truth).** The per-session changelog of sub-entries #10(a)-#10(o) (steering-axis fit, single-sided see-through, debug fluids, raycast oracle, source-game duplicate faces, per-piece winding uniformity, ViewPilot interior, bright-triangle shading seams, the import-orientation saga, glass occluder twins, foreign-LOD material transfer, gap skirts, hub-lift decoupling, get-in-preserving patches) lives in **`references/visual-gates-and-winding.md`** (s14->s23, SUPERSEDED entries archived there). The single operative winding rule stays here:
   - **THE RULE (import orientation, #10j):** keep the raw glTF winding VERBATIM for ALL pieces (net rip->DayZ = `(-Fx, Fy+Y0, -Fz)`, det=+1, preserves the authored visible side end-to-end); stored MLOD normals = smooth(+cross) of the FINAL winding. NEVER orient winding to a normal oracle or to outward-of-centre. Repair ONLY source-inconsistent components by MAJORITY flood-fill per connected component (never minority-area). `glass*int_a` panes are legitimate cabin-side glass (do not delete as z-fight). Full mechanism, measurements, and the SUPERSEDED (h)/(i) history: `references/visual-gates-and-winding.md` #10(j)/(f).

11. **Vanilla forward convention is nose = −Z (ENGINE-NATIVE), and the "visual side" of an imported car
   is NOT one homogeneous block — measure EVERY body proxy separately before any bulk rotation
   (MERCEDES_AMGLF review 2026-07-03; convention verified offline on native data, the yaw-180 fix's
   in-game gate pending).**
   - Convention measured on the raw vanilla ODOL (NOT a debinarized MLOD, so no converter-flip doubt):
     sedan `light_1_1` Z=−2.387, `dmgzone_front` −2.355, front axle −1.655, exhaust at +Z (tail).
     Nose=−Z is engine data. (Side-finding: the debinarized sedan MLOD is sign-faithful to the ODOL.)
   - Perceived-"forward" chain: the 3PP vehicle camera inherits the SEATED PLAYER's yaw (crew-proxy
     orientation, sim side) + an MS offset — `dayzplayercameravehicles.c:39-49,93-105`
     (`m_fIgnoreParentYaw` commented out at `:194`), defaults `transport.c:452-463`. Headlights and
     hubs play NO role in what the player sees as forward. Traction sign is C++
     (`car.c:199-274` proto native) — inferred −Z from the working sedan; not script-readable.
   - Symptom map: shell visual yaw-180 vs sim ⇒ 1st gear reads as "drives backwards" AND wheel
     proxies sit mirrored (−X,−Z) off their hubs, BOTH at once. Diagnose by comparing
     `dmgZone_front`/hubs (sim) vs headlights/wheel-proxies (visual) against nose=−Z.
   > Historial del texto superado: `history/cambio-1-superseded-family-b-rules.md` §“Invariante 11”.
   - **CORRECTION to THE TRAP (added 2026-08-01, adjudicated from the applied fix's dated backups +
     in-game outcome — supersedes the "interior/dash/steering/occlusion correctly sim-aligned" claim
     above):** on the Mercedes those `mb_` contents were VISUAL-aligned (coherent with the yaw-180
     shell), and the executed fix had to rotate the ENTIRE cabin cluster — all 6 `mb_` contents +
     crew proxies (View/Fire) + `pos_driver/codriver(+_dir)` + `drivewheel(+_axis`, re-authored to
     the vanilla rake) — in a second same-day pass (backups `pre-visual-yaw180-2026-07-07\` vs
     `pre-cabin-align-2026-07-07\`: shell rotated, cabin still old), after a first shell-only pass
     per the 07-03 scope left the cockpit 180° off the body. The sim-aligned claim came from
     content-bbox reading plus validating `mb_steering` against a memory point of the SAME
     misaligned cluster (self-validation — the SP-132 "gate shares the producer's frame" shape).
     Rules that survive: (a) still measure each proxy separately, but adjudicate cabin orientation
     with ANATOMICAL PAIRS (seat↔steering-wheel↔column-rake↔driver side) against untouched sim
     anchors (hubs, dmgZones, engine memory) — never with mixed-content bbox or the cluster's own
     memory points; (b) the correct rotation unit is EVERYTHING that defines the visual+pose
     experience: shell + body proxies + crew proxies + `pos_*`/`drivewheel*` cockpit points.
     Post-fix coherence verified offline (anchors exact on hubs, LHD seat side, wheel 0.34 m ahead
     of seat, rake (0,0.516,0.857) vanilla-parallel) and live (Task 9 v64 PASS + manual drive
     2026-07-23, no inverted-drive or backwards-pose reports). Full adjudication:
     `MERCEDES_AMGLF_dev\reviews\2026-07-02-fable-review-plan-OUTPUT.md`.
     **R22 refinement (2026-08-01, Codex re-measured the same backups — narrows the rule above):**
     the "rotate the entire cabin cluster" adjudication is Mercedes-SPECIFIC; the durable rule is
     two-sided — (1) adjudicate cabin orientation with the anatomical pairs against untouched sim
     anchors, then (2) rotate exactly the adjudicated cluster IN EVERY FILE/LOD THE HOST
     REFERENCES, measuring each file, never presuming: the applied 07-07 fix itself MISSED the 12
     `mb_*_lod1/_lod2.p3d` referenced by the host's visual LODs 1-2 (byte-identical to pre-fix,
     hash-verified by two independent reviewers) — so mid-distance LODs still draw the body
     proxies in the OLD orientation. The original warning to measure every proxy separately
     SURVIVES; what was wrong was its Mercedes factual claim, not its method.

   - Cheap steering-wheel check: if the `drivewheel_axis` memory pair is near-VERTICAL (Y-dominant
     direction), the wheel sweeps left-right like a wiper instead of rotating in its plane. The axis
     must be ~perpendicular to the rim plane (Z-dominant, some Y).
   Evidence + probes: `MERCEDES_AMGLF_dev\reviews\2026-07-03-fable-review-b1b6-plan.md`.
12. **REDIRECT CAMBIO-1 (familia B):** `../rip-vehicle-import/cookbooks/family-b/coche-blanco.md`.
13. **Distance-LOD ladder: a single-visual-LOD import renders its FULL face count at ANY distance —
    > Historial del texto superado: `history/cambio-1-superseded-family-b-rules.md` §“Invariante 13”.
    author the ladder BEFORE fighting LOD0 decimation.** (added 2026-07-07, SUB_BRZ s25 measured)
    Vanilla civiliansedan ships 5 visual LODs (14,636 → 10,364 → 3,717 → 1,713 → 123 faces); SUB_BRZ
    shipped 1 (231k always) and the admin-preview/spawn freeze did NOT move with dedup (−18.5 MiB) or
    shadow (32k→3.5k) fixes — it is render/face-bound. Distance LODs res 2/3/4 are baked FLAT into the
    main (no proxy refs: proxies of res-0 only render while res-0 renders) from the rip's authored LODs
    (planar-dissolve measured ceiling = ÷2-2.6); exclude the cabin from far LODs (vanilla does). Day-1 check: count
    visual LODs vs the control — ≥2 is also the product-spec floor (AC1.4-class). LOD0 decimation stays
    user-gated and becomes a LAST resort, not the first.
    **s26 EXECUTED the ladder (SUB_BRZ deployed, measured) — measured continuation of the contract:**
    (a) **Planar-dissolve (Blender limited-dissolve, shape+UV preserving) tops out at ÷2-2.6, NOT ÷5-8** —
    the rip's authored LODs are mid-detail racing meshes, not impostors. SUB_BRZ body 58.7k → 34.5k@15° /
    27k@30° / 22.4k@45°. It yields ONE good near LOD (res2 ~27k, quality intact, no gate). To reach vanilla
    parity (sedan res3/res4 = 3.7k/1.7k) you need COLLAPSE decimation, which deforms and is user-gated — so
    MEASURE the planar ceiling and ask how far to take the ladder BEFORE promising res3/res4.
    `decimate_blender.py` (planar) preserves material-slot + UV; collapse does not.
    (b) **Bake far-LOD normals OUTWARD by position, not from winding.** The body winding gives +cross
    INWARD (the build negates paint/lamp classes via `negate_classes`); a flat LOD baked with raw +cross
    renders ~60% inside-out (black). Flip each face whose cross·(centroid−carCenter)<0 → 100% outward (a
    distance LOD is only seen from outside). resolved<65535 holds easily (26k for a 27k-face body).
    (c) **The transplant assumes exactly ONE visual LOD** (`p4_transplant_dyn assert len(vis)==1`). A ladder
    needs a multi visual-LOD transplant: replace the deployed visual block with ALL work res<100 LODs
    (sorted), KEEPING every struct LOD. GATE it with a self-test on a COPY: struct LODs
    (Geo/Mem/HP/ViewGeo/FireGeo) must come out BIT-IDENTICAL (get-in), then re-verify real deployed vs
    backup. Flat body source = shell res0 minus proxy faces + the chunk p3ds (cabin already excluded — it
    lives in the intact interior proxy). Render-review the baked LOD before deploy (blender-visual-review).
    (d) **A far-LOD baked WITHOUT the shell's make-consistent/orient pass ships with its WINDING globally
    INVERTED → the body reads TRANSPARENT (see-through) at mid/far distance — a DISTINCT failure from (b)'s
    BLACK.** (added 2026-07-09, SUB_BRZ s29 measured+fixed) Transparent = winding/cull wrong (anti-cross faces
    point INWARD → culled from outside); black = stored normals point inward (shading). Diagnose OFFLINE by
    census: fraction of far-LOD faces with `cross·(centroid−center)>0` vs the LOD0 control that renders fine —
    far-LOD ~98% cross-outward while LOD0 ~17% ⇒ winding inverted. FIX: if stored normals ALREADY point outward
    (`storedN-outward` high, i.e. it reads transparent not black), a GLOBAL vertex-order flip
    (`face.vertices.reverse()` on every face, do NOT touch normals — they ride the vertices) suffices — census
    98%→2%, matching LOD0. Reach for make-consistent+orient (`rip_winding_core.repair_winding_majority`) ONLY
    when the far-LOD is topologically MIXED (low interior-edge consistency), not merely globally inverted (G5
    simple-first). Root cause on SUB_BRZ: the in-line s26 ladder assembler took the dissolve winding VERBATIM +
    raw +cross normals and skipped make-consistent (which the shell's `rip_winding_core` runs) → res=2 shipped
    see-through, `outward=38.9%` was printed and ignored, no offline gate. GATE any baked far-LOD by census-vs-LOD0
    BEFORE deploy — Blender cannot judge DayZ winding (right- vs left-handed cull).
14. **Steering wheel vs hands: measure rim-center delta AND plane tilt vs the control BEFORE moving
    anything — the seat anim is the control's, so hands land on ITS wheel plane.** (added 2026-07-07,
    SUB_BRZ s25 measured) SUB_BRZ: rim-center delta vs crew anchor already in parity (1-1.6 cm) but rim
    tilt 15.8° vs sedan 31.0° → ±r·sin(Δ) = ±2.1 cm at r=0.159 = exactly the user's "top hand 2 cm
    behind, bottom hand 2 cm in front". Fix = rotate the wheel PIECE about its own rim center to the
    control's tilt and re-author `drivewheel`/`drivewheel_axis` memory points parallel to the new rim
    normal (SUB_BRZ's axis was 38° off its own rim; the sedan's is exactly parallel — a misaligned axis
    also wobbles the G5 wheel animation). Do NOT recline the crew proxy when the positional delta is in
    parity. Reusable tool: `C:\Users\<you>\VehicleImport\s25_plan\measure_wheel_vs_crew.py` (fits rim by
    outer-radial PCA; handles debinarized selections whose point-membership is lost via faces, LL-018).
    Same open symptom on MercedesAMGLF — apply there.
15. **Hub level must use the radius of the wheel you actually MOUNT, not the rip's rim.**
    [HYPOTHESIS with numbers → day-1 coherence check; in-game pending] (added 2026-07-07, SUB_BRZ s25)
    SUB_BRZ profile `WHEEL_R=0.3637` (source-game rim) while the mounted wheel is `CivSedanWheel` radius 0.34
    (`DZ\vehicles\wheeled\config.cpp:4755-4772`) → 2.4 cm hub-vs-radius mismatch, same order as the
    observed damper rest −4.3/−5.6 cm ("wheels slightly up"). Day-1 check: `WHEEL_R == mounted-wheel
    radius` or document why not.

16. **Drive-ready TEST KIT: fill ALL fluids + attach the radiator, not just FUEL (RECURRING: LFQuad + SUB_BRZ
    s28).** An admin/harness kit that only `Fill(CarFluid.FUEL,...)` leaves OIL/COOLANT/BRAKE empty → the oil
    gauge goes RED and the engine BREAKS while driving (looks like a physics/drivetrain bug, it is NOT). A
    drive-ready kit must `Fill` FUEL + OIL + COOLANT + BRAKE **and** `CreateAttachment("CarRadiator")` (coolant
    needs the radiator). Vanilla `OnDebugSpawn`'s `FillUpCarFluids()` does all of it; a hand-rolled `KitManual`
    in the mission `init.c` does NOT unless you mirror it. `CarFluid` enum = FUEL/OIL/BRAKE/COOLANT
    (`scripts/3_game/vehicles/car.c:18`); `Fill`/`GetFluidCapacity` at `car.c:376/359`.

17. **Raise tyre grip WITHOUT touching the wheel binding: a `CarWheel` subclass of the vanilla wheel.** To add
    grip to a car that slides, do NOT rewire slots/proxies (risks re-opening the freeze/wheel-bind). Declare
    `class <Mod>_Wheel : CivSedanWheel { scope=2; tyreGrip=0.98; };` — it INHERITS the vanilla `inventorySlot[]`
    (`DZ\vehicles\wheeled\config.cpp:4761` lists CivSedanWheel_1_1.._2_2 + Spare) so it drops into the same
    `CivSedanWheel_*` slots and reuses the sedanwheel proxy; only tyreGrip changes. Then `OnDebugSpawn`/kit
    create `<Mod>_Wheel`. Grip is DECOUPLED from the visual wheel model (custom source-game/rim = separate visual job). SUB_BRZ s28.

18. **Diagnose "the car slides" BY AXIS — longitudinal (accelerating) vs lateral (cornering) need different
    fixes.** Sliding when you FLOOR it (power-oversteer, RWD) → tyreGrip + throttle/torque down. Sliding when
    you TURN (body roll unloads the inside tyre) → tyreGrip + LOW CoM + downforce + roll stiffness. A low CoM
    helps the CORNERING slide (less lateral weight transfer) but NOT the accelerating slide — in RWD a very low
    CoM even transfers LESS weight rearward under throttle (slightly less traction). Never sell "lower the CoM"
    as the fix for wheelspin. SUB_BRZ s28: accel-slide dropped with grip 0.95→0.98 + throttle 0.8→0.72; corner-slide needed CoM/downforce.

19. **Transplanting a donor mod's drivetrain: match (gear x central x final) / wheel-radius, never
    the ratios verbatim.** (added 2026-07-10, SUB_BRZ s31) Wheel force per engine-Nm = total_reduction /
    wheel_radius and per-gear road speed = rpm x radius / reduction, so a donor running a different
    wheel radius shifts EVERY gear by r_donor/r_yours. Compare radii FIRST; the CentralDifferential
    ratio is the compensation lever. Case: SUB_BRZ (CivSedanWheel 0.34) adopting the Gelenvagen
    drivetrain (0.48 wheels, central 1.4) keeps central 1.0 — 0.34/0.48 ~= 1/1.4 cancels the donor's
    central, reproducing its per-gear speeds AND per-Nm force <1% off; copying central 1.4 verbatim
    would run 29% shorter than the donor feel. The failure class burned a full session first (s30: an
    offroad central 1.5 compounded ratios authored for central 1.0 → gears ~50% short, 6th
    unreachable). Corollaries: (a) donor force on half the mass = ~2x the acceleration — scale
    expectations by mass before judging "too much/too little power"; (b) engine `frictionTorque` is
    calibrated to the donor's mass/curve — engine-braking decel scales as fT x reduction / (radius x
    mass), and when the radius/reduction terms cancel (as above) the mass-equivalent value is simply
    fT x m_yours/m_donor; adopt the donor value for its cruise character but pre-compute that fallback
    before the in-game cycle.

Cross-vehicle durable record (which project won each, links to the three): vault note
`AI/20_Knowledge/dayz-vehicles-crossproject.md`.

20. **Config inherits a vanilla car but your SCRIPT class does not extend that car's script = SWEEP every parent script override (SP-059).** If the config says `class X: OffroadHatchback` while the script is `class X extends MyBase` (with `MyBase extends CarScript`), the config->script binding does NOT drag in the parent car's script overrides - those live on the vanilla `inheritedcars\<parent>.c`, which your class never inherits. Every method with a hostile default in the base that ALL vanilla cars override then bites: `CrewCanGetThrough` (false in `Transport`, `transport.c:493` -> get-in impossible; see #1), `IsVitalGlowPlug` (true in `CarScript` -> engine won't start; see #8), `GetAnimInstance` / `GetSeatAnimationType` (`Error()` in `Transport`, `transport.c:465,475`), `Get3rdPersonCameraType` (`Error()`, `transport.c:483`). Procedure: diff method-by-method against the parent config's `.c` (`4_world\entities\vehicles\inheritedcars\<parent>.c`) and replicate EVERY runtime-contract override, not just the two pose ones - this is DZ-R7 (sweep the invariant to all call-sites) in config form. Origin: LFHeli R21-008 - `LFHeli_Placeholder: OffroadHatchback` (config) + `extends LFHeli_Base` (script) had no get-in and no engine start after passing two reviews; the first fix restored only the two pose methods.

21. **REDIRECT CAMBIO-1 (familia B):** `../rip-vehicle-import/cookbooks/family-b/attach-invisible.md`.
22. **An attached item with its OWN radial actions (CarDoor open/close, hood, trunk) needs a raycast-visible ViewGeometry — point flags 0x02000000 — or the action NEVER appears (SUB_BRZ s38).** The action chain resolves the TARGET by raycast: `ActionCarDoorsOutside.ActionCondition` casts `target.GetObject()` to CarDoor and reads the selections of the hit VG COMPONENT of the ITEM (`actioncardoorsoutside.c:34-46`); a VG whose points carry flags 0x0 is not hit by `RaycastRV(ObjIntersectView)` — the same mechanism as the seat-cube blocker (preflight #4, in-game verified SUB_BRZ s9 + MercedesAMGLF s12) — so the item under the cursor never resolves and the radial is silently filtered, with config, script overrides, slots, bones and anim sources all CORRECT. Contract for the item's VG: (a) componentNN dual-tagged with a selection named EXACTLY what the vehicle's `GetAnimSourceFromSelection` expects (e.g. `doors_driver`); (b) every VG point flags 0x02000000; (c) inward winding (copy a fixed seat cube as control). Symptom signature: attachment renders/attaches/damages fine, `GetCarDoorsState` works, but no open/close radial (and hence no get-in-through-door). Diagnose offline in seconds: census the item's VG point flags vs a working control BEFORE touching config or scripts. Origin: SUB_BRZ s38 D4e; the door fix's own in-game gate pending as of 2026-07-17, but the raycast mechanism is the twice-verified #4 one.

23. **`componentNN` dual-tag is the confirmed fix for simultaneous seat/wheel selection failures; ascending LOD order is match-vanilla practice, not a proven cause (LFHeli OH-1 v2, 2026-07-17).** Sorted-without-dual-tag still failed; sorted-plus-dual-tag spawned; dual-tag-without-sort was never isolated. Therefore a py3d/hand-assembled model with `seat_* not found` / `wheel ... no proper selection` must be checked for collision-selection dual-tag first. `model.lods.sort(key=resolution)` may remain as deterministic authoring hygiene, but no gate may report that sorting fixed the defect. `binarize` accepts either order silently.
> Historial del texto superado: `history/cambio-1-superseded-family-b-rules.md` §“Invariante 23”.

24. **`binarize` is the three-state offline load oracle; `RESOLVED_LIMIT = 65535` is a false friend (SP-122, LFHeli HH-60G, 2026-07-29).**
> Historial del texto superado: `history/cambio-1-superseded-family-b-rules.md` §“Invariante 24”.

Everything below is measured on the HH-60G, cross-checked against 25 in-game verdicts.

**1. `Too many vertices` and `Won't simulate, it has no geometry` are the SAME defect.**
The rejection happens while **loading the MLOD**, before conversion, so the engine aborts the
whole model and emits the generic physics message even though the Geometry LOD is perfect.
Chasing it as a collision problem costs days. If a model that passes every offline gate does
not spawn, run binarize on it **before** touching the Geometry LOD.

**2. binarize adjudicates N models per pass, offline, in ~90 s.**
`binarize.exe -always <src under P:\> <out>`, with a `model.cfg` that declares **every**
basename in the source dir (undeclared basenames fall back to Default and change the code
path). Validated on 28 variants against the in-game verdicts of the previous cycle:
**13 PASS/PASS, 12 FAIL/FAIL, zero false greens, zero false reds.** This turns a model
bisection from ~6 min per variant into ~90 s per batch.

**3. The verdict has THREE states. Using two is a bug in your bench.**
- `PASS` - a **new**, non-empty ODOL for the basename under test, in an output dir that did
  not already contain it. Skip the "new" requirement and a residual ODOL gives you a false green.
- `CAPACITY_FAIL` - no new ODOL **and** a `Too many vertices` line attributed to that MLOD.
- `OTHER_FAIL` - any other absence: bad `model.cfg`, undeclared basename, malformed MLOD, I/O,
  aborted tool. **It blocks and does NOT authorize touching geometry.** Without this state you
  decimate a mesh because your bench was misconfigured.

**The verdict is reproducible; the ODOL bytes are NOT.** The same `.p3d` produced 1,725,025 and
1,726,689 bytes with different hashes in two clean consecutive runs. Never gate on the ODOL SHA.

**Noise that does NOT discriminate** (it appears for the known-good control too):
`Material not loaded`, `No entry '.CfgVehicles'`, `Trying to access error value`,
`Error occured: Loading LODShape`, `UV mapping too varied`, `vertices of bone X are shared with
bone Y`, `Too detailed shadow lod`. The word `Error` in the log classifies nothing - attribute
the outcome to a model and a cause, or record `OTHER_FAIL`.

**4. The ceiling in triple units is not 65535, and it is not portable.**
Measured by walking four structurally different bases of the same asset to the cliff:
**46,133 loads, 46,134 does not** - the same integer for all four. The engine's hard cap does
appear to be 65,535 but on **post-split** vertices, and a `(point, normal, uv)` counter
under-counts those by a model-dependent factor: **1.4205** here, **1.46** on the OH-1 (see #24).
An assembler with `RESOLVED_LIMIT = 65535` hardcoded closed its own gate in green, for weeks, on
a model the engine refuses. **Re-measure per model; the hard gate is binarize's verdict.**

**5. Know your headroom, because it can be one edit wide.**
The deployed HH-60G sat at 46,019 of 46,133 - **114 triples of margin**, 99.8 %. Any change that
adds more than 114 resolved vertices kills it: a normal tweak, a UV seam, a texture that forces
another split. Measure resolved before and after **every** visual edit.

**6. When you mint a normal, you are spending budget; when you reverse a corner order, you are not.**
The defect that cost this project a week: a winding-flip block negated the stored normal **per
corner** for the 151 faces (0.43 %) whose source normal disagreed with the source winding. Those
453 corners minted 630 pool entries and +886 resolved. Re-reversing the corner order of those
151 faces reaches **identical** coherence at zero cost. A face's corner order is free; a new
normal is not.

And the identity to have in your head before "fixing" a winding by inverting things:
`dot(-cross, -n) == dot(cross, n)`. Reversing the corners **and** negating the normal is a
no-op for their relationship - it re-parametrizes, it does not flip. A policy that does both
changes nothing.

**7. A perturbation below the consumer's quantum is a null mutation.**
When walking a limit to find where it breaks, the step must survive the consumer's quantization.
Nudging a normal by 1e-4 on one component (~0.006 deg) does not survive DayZ's normal
compression: the estimator counted +120 new triples, the engine saw none, 42 samples "passed",
and the ceiling would have been reported 7 units too high. Use a step that is unambiguously
above the quantum (>= 3 deg for normals) and include a sample past the known-failing value as
a self-check.

Tool: `C:\Users\<you>\VehicleImport\scripts\p3d_vertex_gate.py` - `count` reports resolved per LOD
as `INFORMATIVE_ONLY`; only `binarize` runs the authoritative three-state adjudication.


25. **GTA V rip intake (dlc.rpf) — mod RPFs are usually UNENCRYPTED and fully parseable offline; the vehicle skeleton maps 1:1 to DayZ needs (LFHeli HH-60G, 2026-07-18).** Check the encryption dword at offset 12 of the RPF7 header FIRST: `0x4E45504F` ('OPEN', standard for OpenIV-built mod RPFs) = no GTA V install, no NG/AES keys needed. Verified on-disk layout: 16-byte header (`7FPR` magic, entryCount, namesLength, encryption); 16-byte entries discriminated by dword2 (`0x7FFFFF00` = directory, high bit set = resource, else binary); file offsets in 512-byte sectors; binary entry with fileSize==0 = stored verbatim (nested .rpf — recurse in place). A resource on disk = **16-byte RSC7 header IN THE CLEAR** (magic `RSC7`, version — 162 yft / 13 ytd —, sysFlags, gfxFlags) + raw-deflate payload from +16 (`zlib wbits=-15`); scene-standard standalone `.yft`/`.ytd` files are exactly that byte range copied verbatim, so extraction is a copy, not a re-encode. Skeleton conventions worth knowing before Blender (string-scan of the decompressed payload suffices — no FRAG parsing): rotors ship THREE states `rotor_main`/`_slow`/`_fast` (+ `rotor_rear` same) = direct map to the DayZ static+blur rotor pattern; doors `door_[dp]side_[fr]` + `handle_*`; glass as own bones (`windscreen`, `window_*` — glass census for free); `seat_[dp]side_*`, `wheel_lf/rf/lr`, `gear_*` incl. `gear_door_*`; guns/turrets are separate bones (`turret_*`, `weapon_*`) = clean v1 exclusion. Toolchain [IN-VIVO VERIFIED 2026-07-18]: Sollumz 2.8.3 imports binary `.yft` directly (PyMateria/szio, Windows-only) on Blender 5.1 (4.0-5.1 supported), while CodeWalker demands a GTA V game folder on first run — so for OPEN rips the primary chain is own-extractor → Sollumz binary import, CodeWalker only as fallback. Two verified gotchas: (a) **PyMateria's native `.pyd` fails to load from a long path** ("DLL load failed ... filename too long", MAX_PATH) — install Sollumz into a SHORT isolated Blender profile via `BLENDER_USER_RESOURCES=C:\tmp\blp` (also keeps the user's running Blender untouched); headless install = `bpy.ops.extensions.package_install_files(repo="user_default", enable_on_install=True)` + `<addon>.dependencies.install_dependencies(online_access_override=True, optional_dependencies_to_install={"pymateria"})`. (b) **The `.yft` does NOT carry its textures** (they live in sibling `.ytd`), and Sollumz's high-level `gta5.try_load_asset` returns None for a `.ytd`, and its `.yft` import wires 47 named-but-empty image nodes — the FIX is the RAW PyMateria binding: `pmg8 = szio.gta5.native.provider_gen8.pmg8`; `res = pmg8.TextureDictionary.import_rsc(Path(ytd))`; `td = res.result`; `td.textures` is a Map(name→Texture); `tex.export_dds(path)` writes the decoded DDS (PyMateria does all the RSC7+format). ~generic base-game textures (`vehicle_generic_*`) live in GTA's `vehshare.ytd` (not in the mod) and stay missing = pink in Blender, but IRRELEVANT for DayZ (glass gets a vanilla `.rvmat`; the rest are secondary spec/detail overlays). Origin: LFHeli HH-60G intake (`rpf_extract.py`/`ytd_extract.py`/`bl_install.py` in `LFHeli_dev\model_src\HH60G_intake\work\`; textured artist package verified by render).

26. **A rip's BONE NAMES are not its MESH PIECES, and an exclusion REGEX silently classifies content nobody has looked at (LFHeli HH-60G, 2026-07-28).** Two failures of the same import, both invisible offline and both only surfaced by a full in-game cycle. (a) **Regex exclusion.** The day-1 census marked `exclude_v1` with `^(mod_[a-z0-9]+|turret_|weapon_|siren\d|extra_\d|hbgrip_)` to drop "GTA cruft". That swept in `mod_n` (31.598 tris = the whole nose kit: refuelling probe, rescue hoist, radome, nose pods) and `mod_s` (52.550 tris = the entire interior, seats included). The exporter inherited the classification and the vehicle shipped with no nose and a hollow cabin; **94.084 tris of legitimate content, 38% of the source**, lost for ten days without one warning. Rule: **the exclusion list is LITERAL NAMES, one justifying line each — never a regex.** A regex classifies pieces nobody has looked at yet; a literal list forces you to look. (b) **Bone names != mesh pieces.** The string-scan of the skeleton (item 25 above) lists `handle_*` next to `door_*`, so the routing table cited `handle_dside_f/pside_f/dside_r/pside_r`. Measured against the actual LOD levels: those four names exist in **no** level of the `.yft` and in **no** mesh of the imported `.blend` — the skeleton carries bones with no geometry behind them. **Item 25's skeleton-convention list is a hypothesis about names, not a piece inventory**; intersect it with the per-level mesh list before routing anything. Corollary that decides the fix: "the export LOST a piece" and "the export CITED a piece that never existed" look identical from a silent `if obj_by_name(n)` skip and lead to **opposite** repairs (go find it vs delete the row). Gates that would have caught both on day 1, cheap and offline: **SOURCE = the piece set of the richest LOD level, measured** (here `hh60g.yft/High` = 49, set-identical to `hh60g_hi.yft/VeryHigh`); every source piece appears **exactly once** in a routing group or in the literal exclusion list, partition verified by set equality, not by totals; every routed name is **in SOURCE**; and a missing artefact is an **error, never a `[skip]`**. Origin: LFHeli HH-60G, plan v15 Fase 1.1/1.2; measurement in `LFHeli_dev/plans/2026-07-28-hh60g-v15-censo-y-tabla-normativa.md`.

27. **A model that passes every offline gate and still refuses to spawn is almost always over the RESOLVED-VERTEX ceiling — and `binarize` tells you offline, in 90 seconds (LFHeli HH-60G, 2026-07-29).** `PHYSICS (E): Won't simulate, it has no geometry` is emitted when the engine aborts while **loading the MLOD**, before it ever builds physics — so a perfect Geometry LOD does not exonerate the model, and chasing it as a collision problem costs days. **Do this first, not last**: drop the `.p3d`s into a dir under `P:\` with a `model.cfg` declaring **every** basename, run `binarize.exe -always <src> <out>`, and read the verdict — `Too many vertices` names the culprit by filename. Validated 25/25 against in-game verdicts on 28 variants (zero false greens, zero false reds), which turns model bisection from ~6 min per variant into ~90 s per batch. Three rules that make it a real gate: (a) the verdict is **three-valued** — `PASS` needs a *new* non-empty ODOL (a residual one is a false green), `CAPACITY_FAIL` needs the `Too many vertices` line *attributed to that MLOD*, and anything else is `OTHER_FAIL` which **blocks and does not authorize touching geometry**; (b) the verdict is reproducible but the **ODOL bytes are not** (same input, 1.725.025 and 1.726.689 b in two clean runs) — never gate on the ODOL SHA; (c) the ceiling in `(point, normal, uv)` units is **not 65535 and not portable** — measured 46.133 on the HH-60G across four bases, because the engine's cap is on POST-SPLIT vertices and your counter under-counts by a model-dependent factor (1,4205 here, 1,46 on the OH-1). An assembler with `RESOLVED_LIMIT = 65535` hardcoded closed its own gate in green for weeks on a model the engine refuses. **Re-measure per model, and know your headroom** — the deployed HH-60G sat 114 triples under the cliff, one normal tweak from death. Full detail, including why reversing corner order is free while minting a normal is not: **SP-122** at the bottom of this skill. Tool: `C:\Users\<you>\VehicleImport\scripts\p3d_vertex_gate.py`.

## NEW CAR — DAY-1 (run BEFORE the first in-game cycle; retro 2026-07-03)

Retro of LFQuad→SUB_BRZ→MercedesAMGLF (~90-110 session-equivalents, ~180-220 in-game cycles across
the three): the dominant cost was known-CLASS defects attacked one-per-rebuild AFTER the car was
in-game. Front-load them on day 1, offline, before any PBO exists — promoted knowledge applied up
front is nearly free (the SUB_BRZ spawn-blocker check ran before Mercedes Fase 3 and cost minutes;
the un-promoted get-in cost "decenas de iteraciones" on three cars):

1. **Parity-first** (METHOD #1): debinarize `civiliansedan` ONCE → structural gap checklist.
   Preflight #1-#9 items fall out of this diff instead of error-by-error in-game.
2. **Measure, never assume — on the rip AND on a working control.** Cite-then-verify extends to
   DATA PROVENANCE and empirical constants, not just API names (the BRZ winding saga ran ~15
   sessions on an oracle nobody had verified; the 32768 "ceiling" and the Izz>=300 gate were both
   artifacts): nose=-Z markers sim vs visual (#11), EACH body proxy's anchor + content (#11 trap),
   axis memory-point directions, per-LOD point counts via py3d (Blender estimates read ~x1.24
   optimistic), the rip's own authored-LOD inventory BEFORE building a decimation pipeline
   (decimation is user-gated).
3. **One command wraps the day-1 measurements**: `python C:\Users\<you>\VehicleImport\tools\import_preflight.py
   --car <p3d> [--proxy-dir <dir>]` — parse-health, sim/visual orientation, wheel-proxy yaw-180
   MIRROR signature, body-proxy anchor+content report, steering-axis direction class, LOD point
   counts; prints the follow-up gate-ladder commands (rungs 1/2/4 stay in their dedicated tools).
   CALIBRATED 2026-07-04: FAILs x3 on the pre-fix Mercedes (B1/B2/B3), 0 FAIL on the vanilla sedan.
   Note from that calibration: anchor→hub PROXIMITY is NOT a discriminator (correct sedan = 0.20-0.22 m,
   mirrored Mercedes = 0.147 m — the broken car sat closer); the EXACT (-X,-Z) mirror signature is.
4. **Acceptance spec from the CONSUMER** (R8-extended): list the exact names/frames/values that
   model.cfg + config.cpp + the engine will read and assert each exists in the `.p3d` — producer-side
   self-consistency passed 58 asserts while the forward contract was broken (LL-025), and offline
   suites passed while the car could not spawn.
5. **Headless harness with a vanilla control in the same run** (sedan/Croco): "the control delta does
   the diagnosis" (LFQuad bounce: wc=0000 vs control wc=1111 isolated the bug in one run).
   **The control delta is only valid if BOTH cars get the IDENTICAL kit flow** — kit the mod car via
   its own `OnDebugSpawn()` (or an explicitly declared superset), never a hand-rolled partial kit.
   MercedesAMGLF s16 spent a user drive-test with the mod car on a hand-written `KitManual`
   (FUEL+COOLANT only → OIL=0/BRAKE=0) while the control sedan got full vanilla `OnDebugSpawn`
   (init.c:145-146, found 2026-07-07 AFTER the cycle was spent): non-equivalent kits silently
   poison the mod-vs-control discriminator and add a confounded state variable to every symptom.
6. **Fluids / DamageZones / vitals config from the proven shape** (preflight #8/#9) — copied, never invented.

## LEGACY DIAGNOSTIC GATE LADDER — manual for a post-CAMBIO-0 family B asset

For vehicles already in flight, this preserves the pre-CAMBIO-0 diagnostic order. For a new family B
asset, none of these rungs executes automatically unless its exact contract appears in the B1-B6
allowlist above. The original wording and order are archived byte-for-byte in
`history/pre-cambio-0-gate-ladder.md`; every rung remains invocable by hand during diagnosis.

0. **STRUCTURAL PARITY** (config/model.cfg) — preflight #1-#6 (get-in, geometry `class=vehicle`,
   componentNN dual-tag+collidable, crew/wheel proxies, DamageZones). Gates spawn/drive, not looks.
   Do it via the parity-first vanilla diff.
1. **DEDUP coincident duplicate faces** (z-fight speckle) — `dedup_faces.py` + `position_dedup.py` (#10e).
   FIRST geometry gate: duplicates dirty every later check. A clean car has ~0 coincident.
2. **WINDING UNIFORMITY per piece** — topological, no raycast — `scripts\winding_consistency.py --car <p>`
   -> every visible piece `OK uniform`. THE basic winding gate; faces inverted vs their NEIGHBOURS =
   triangular artifacts in-game (#10f). Cheap; run BEFORE anything raycast.
3. **ORIENTATION vs SOURCE** — verify each piece preserved the raw glTF winding (#10j); use
   `tools\raycast_winding.py` only as the #10d see-through HINT (L-vs-R asymmetry = bug tell), NEVER as
   authority to flip a whole piece — an all-single-sided piece can be legitimate cabin-side geometry
   (`glass*int_a`); that oracle class is what inverted the BRZ rear glass.
4. **SEE-THROUGH vs exterior** — `scripts\gate_car.py --car <p>` (#10d): body `color`/`glass`
   scattered=noise, dense cluster / L-vs-R asymmetry = bug. Catches isolated inverted faces topology
   misses. HINT — the in-game render is the final gate (s13). (First-person INTERIOR is a separate LOD:
   ViewPilot 1100, DOUBLE-SIDE it per #10g, not orient-inward.)
5. **MATERIAL / LOD / PATHS** — each visible piece has a material selection (not `untagged`), lives in
   LOD0, and its textures/rvmats resolve (`dayz-pbo-build`). A piece with NO material renders invisible
   too — same symptom as inverted winding, different cause; rule it out here.

6. **LOD FRAME PARITY — every `_lodN` variant carries the SAME frame as its LOD0** (added 2026-08-01,
   MercedesAMGLF R22F-003). Any post-hoc transform of a proxy-split body (yaw fix, flip, translate)
   must enumerate EVERY file the host references — including the `_lod1`/`_lod2`/`_lodN` variant of
   each proxy — not just the base pieces. A fix that touches only the bases leaves the distant LODs in
   the OLD frame: the car looks perfect up close and draws its cabin/mechanicals rotated at mid
   distance, the moment the engine switches LOD. Why nothing catches it: topology, face counts, vertex
   ceilings and every structural verifier stay green — each variant is internally valid, just wrongly
   oriented — and the in-game test passes too, unless the tester WALKS AWAY far enough to trip the
   switch. Gate — TWO DISTINCT checks; conflating them makes the gate impossible (this correction
   came from the R22 that reviewed the original wording, 2026-08-01): **(a) transform applied** —
   each rewritten file against ITS OWN input: exact rotation, immutable topology, error
   `0.000000000`. That proves the fix ran on that file; it says nothing about LOD-to-LOD agreement.
   **(b) frame parity LODn vs LOD0** — a metric that TOLERATES decimation (principal axes, oriented
   bounding box, centroid + direction of matched anatomical features). Never point-to-point: a
   legitimately simplified LOD has no vertex correspondence with LOD0, so demanding identical
   topology between them would forbid the decimation the ladder exists for. Plus one in-game orbit
   backing off through LOD1 and LOD2.
   Real cost: the MercedesAMGLF yaw-180 fix rotated the 6 base proxies and left 12 `_lod1`/`_lod2`
   files byte-identical to the pre-fix backup — undetected for 25 days across several visual reviews,
   because the generating script's file list enumerated only the bases (`cabin_align.py:18`).
   Corollary for the CONTRACT, not just the gate: if no acceptance criterion demands LOD-to-LOD frame
   parity, this defect is not merely missed — it is *out of scope*, so no reviewer is wrong to pass it.
   Add the criterion (MercedesAMGLF `AC1.4c`) alongside the check. Cross-project: any car with a LOD
   ladder plus body proxies has the identical exposure (SUB_BRZ shares the shape exactly).

**Calibration + scope (so a gate is trustworthy, not a false green):**
- **Every rung must catch at least one KNOWN in-game bug, not just a synthetic self-test.** The
  self-test proves the MECHANICS; a real known-bad case proves COVERAGE. Keep a short per-car list of
  known in-game defects and confirm the ladder catches each: BRZ backlight mixed-winding -> caught by
  rung 2 (`winding_consistency`: glass 18.2% of area); MercedesAMGLF left tail-lamp inverted -> caught
  by rung 4 (`gate_car` see-through, L-vs-R 310/0). (both 2026-07-01)
- **A PASS states its SCOPE — never a bare "clean".** "clean of see-through in `color`/`glass`" is NOT
  "clean of winding". `gate_car` reporting "BRZ limpio" while rung 2 (per-piece uniformity) was
  unchecked was a FALSE GREEN the user caught in-game (2026-07-01). Name what each gate covered and did not.
- **Freshness:** the analysis prints model SHA+mtime and flags changes vs the last run
  (`model_freshness.stamp`) — the deployed `.p3d` can change under you between sessions (SUB_BRZ s16
  de-dup removed 20320 faces mid-analysis; a stale golden then misleads). Owner of a shared artifact
  (a car's `.p3d`, or THIS skill) = the session working it; edit append-only + verify (this skill was
  being edited by two sessions at once, 2026-07-01).

**A rip-imported PANEL is two parallel skins with an OPEN rim; a vanilla panel is a closed volume
(SP-247, added 2026-08-15; SUB_BRZ doors E-1 — CORRECTED the same day, see the refutation below).**
Any door, hood, tailgate or flap coming out of a game rip is a pair of surfaces — outer skin and
inner card — that are never joined at the edge. The source game never shows that edge, so it was
never modelled; every DayZ door OPENS, so every imported door shows it. This is the same finding as
**SP-198**, measured a week earlier on the same car (leading-edge cap 25 cm² against the ~710 cm² a
real cap needs, 77 mm of thickness available) — and the fact that SP-247 was written without
reading it is itself the lesson: **before authoring a fix, grep this file for the defect, not just
for the car.**

- **Count a free edge over ALL faces of the LOD, not within the material.** An edge the skin shares
  with glass or trim is covered, not open; skirting it pokes through the neighbour. Counting
  within-material inflates the census and aims the fix at edges that were never exposed.

- **⚠ REFUTED — do NOT close the rim with an extruded skirt, and do NOT calibrate on the edge-on
  silhouette.** The first version of this entry canonized both, on the strength of an edge-on render
  going 15.0% → 25.4% of frame against a vanilla control at 26.8%. The user's eye falsified it the
  same day: the edge was still see-through in game, plus two new defects. Two mechanisms, both
  measured afterwards, and either one alone is fatal:
  1. **An extrusion is a flange, not a cap.** Welding a band to the rim closes that edge and opens
     a new one at the band's inner boundary. Measured on the shipped door: true free edge went
     **4455 → 5036 mm**. The operation moved the hole inward; it never closed it.
  2. **The extruded vertices inherited the rim vertex's UV, so every quad has 3D area and ZERO UV
     area** — 235 of 235 quads measured at 0.00000 UV/3D against 0.18 for the skin beside them. The
     faces draw (same pixel count cull ON and OFF), which is exactly why a solid-colour offline
     render scored them as closed, while the engine samples a degenerate mapping and the player
     reads smeared garbage. A skirt that lands anywhere near glass reads as an artifact ON the
     glass: 39 quads within 5 cm of a pane, closest 6.1 mm.
  The silhouette percentage was measuring the patch, not the defect — the exact failure the
  corollary below warns about, committed in the bullet above it.

- **The rim has to be AUTHORED as a cap, on the vertical leading and trailing edges only.** Weld
  skin edge to card edge with its own UV strip (or a dedicated opaque edge material); do not sweep
  the whole free perimeter, because most of it is not exposed — measured on SUB_BRZ, only 31.5% of
  an automatic perimeter skirt landed on the two edges that were actually the complaint, while 17.4%
  (663 cm²) landed on the window top and became a new texture defect.

- **RE-IMPORTING DOES NOT FIX THIS — measured twice.** SP-193 found all six visual factory groups
  already present face-for-face in the shipped proxy (100% centroid match ≤1 mm), and the pipeline's
  own `build_detachable_doors` output measures **684 mm** of free leading edge against the live
  door's 743 and vanilla's **0**. The open sandwich is in the source. Re-assembly reproduces it.

- **Gate: a TEXTURED render plus an in-game capture with the panel OPEN, at the angle of the
  complaint.** Never the silhouette percentage, and never a solid-colour render — both are blind to
  the UV failure that decides whether the fix is visible at all.

- **Corollary on gates (same family as SP-202).** "56 of 63 quads face the edge", "cap 25→40 cm²"
  and "silhouette 15.0→25.4%" all improved while the defect was untouched. A metric that improves
  without the symptom moving is measuring the fix, not the defect — go back to the artifact of the
  complaint.

**Building an OFFLINE viewer/render for the user to judge? Two traps that make it lie
(SP-248, added 2026-08-15; SUB_BRZ 1PP).** Both were caught by the user, not by any gate.
- **What 1PP draws is the 1100 of each part PLUS every proxy that 1100 REFERENCES.** "Does this
  chunk file have a 1100?" is the wrong question: a proxy that ships only `res=0` is still instanced
  by the parent's ViewPilot and falls back to its own LOD0. The SUB_BRZ shell's `res=1100` lists
  **11 proxies including all four body chunks**; excluding them hid the roll cage from the very
  viewer built to have the user point at it. Read the parent's 1100 proxy list, then per part pick
  `1100` if present else the finest visual — the same rule the engine uses — and never hardcode the
  resolution, because a part grows a 1100 the moment you cut something from it.
- **DayZ model space is left-handed; Three.js and a naive numpy raycaster are right-handed.** Feed
  raw coordinates and the car renders MIRRORED — driver on the wrong side — which invalidates every
  left/right judgement the user is about to make. Negate display X **and** swap one pair of triangle
  vertices so the winding survives; keep ids, bboxes and any ray metric in true model space, since
  the `.p3d` edit reads those. Gate it with an asymmetric fact that must hold on screen (here: the
  centreline must project to the RIGHT of the driver's eye, `side > 0`, or the build aborts) — per
  the reference-frame rule, an orientation you did not assert is an orientation you got wrong.

**The ViewPilot (res-1100) is a CURATED view — not a copy, not a budget, and never trimmed against a
partial car (SP-249, added 2026-08-15; SUB_BRZ s52, root-caused).** One car shipped both halves of
this hole at once, and the user found both by eye: a roll-cage bar and a headliner crossing the road
view in first person, and 73 faces of body sheet silently absent from 1PP while present in the very
same model's LOD0. Three lessons, each with the measurement that proves it:

- **What the engine draws in 1PP = the main's res-1100 PLUS every proxy that 1100 references**, each
  contributing its own res-1100 when it has one and its finest visual LOD otherwise. "Does this chunk
  file have a 1100?" is the wrong question — SUB_BRZ's shell 1100 lists 11 proxies including all four
  body chunks, which ship only `res=0` and are therefore drawn whole. Corollary for hiding something
  from first person only: give that part its own res-1100 minus the geometry. A part with only a
  visual LOD is drawn entire the moment the parent's ViewPilot references it.
- **A driver-visibility TRIM must run against the complete assembled car — attachments included.**
  The 73 missing faces were deleted by an occlusion classifier whose rule was "drop every face no
  seated eye sees front-facing", run over a scene built from shell + interior only
  (`c2_export_pilot_json.py:11-12`, verified). With the doors absent, the door-aperture sheet was
  reachable from the seat and read as back-facing, so it was trimmed — the exact strip the user later
  reported as "missing where the body should meet the door, same on both sides". That file's own
  comment records the same bug caught once before ("without it the classifier flags rear lights as
  removable") and fixed by adding ONE more occluder. One occluder short is the whole failure mode.
  Same trap bites offline viewers: a 1PP viewer built without the chunks hid the roll cage from the
  very screen built to have the user point at it.
- **Cabin materials inside BODY chunks are an import misclassification, and that is what puts junk in
  front of the driver.** 269 `brz_cab_metal` faces in `brz_chunk_01` and 18 `brz_cab_head` in
  `brz_chunk_02`; the ViewPilot only made them visible. Confine material families to their artifacts
  and check on PRESENCE, not on visibility — a leak outside the driver's cone today is a leak in his
  cone after the next pose change.

**The gate this produced** (`rip_viewpilot_content_gate.py`, schema rip_artifact_gate.v1) runs
three checks — STRUCTURAL (faces of a declared structural selection in the visual LOD but not in the
1100, keyed by rounded coordinates so it survives AddonBuilder reordering), OCCLUSION (driver-eye ray
fan over the truly-drawn 1PP scene against a per-car deny list) and CONTAINMENT (material family →
allowed artifacts, longest prefix wins so one deliberate exception does not weaken its family).
Calibrated red-then-green on the real artifact: FAIL with 73/269/18 on the pre-fix build, PASS on the
shipped one. Two habits it enforced on its own author, both worth copying: the first deny list was
too broad (it banned a material the driver legitimately sees overhead, and the gate said so at
10.9% of sight lines), and the deliberate shell-side console screen had to be DECLARED rather than
have the rule loosened.

**Why nothing caught it for weeks:** every gate in that suite treated the 1100 as a budget or as
presence — perf_budget counts its faces (and already encoded the proxy-LOD rule at
`rip_perf_budget_gate.py:230-243`, used only for counting), coverage is presence-only ("Nothing
here has an opinion about geometry"), lod_semantics classifies the SOURCE, and the one driver-eye ray
gate was scoped to a single defect. No gate compared a model's 1100 against its own LOD0. When a LOD
is hand-edited outside the builder — this one is proxy-only in `rip_p3_structural.py` and was
cloned by hand — it has no owner and no gate, which is exactly where silent cuts live.

## METHOD — three habits that stop the re-derivation (apply BEFORE the per-invariant fixes)

Not invariants but the working method that would have saved most of the LFQuad→SUB_BRZ→MercedesAMGLF
iterations. They are otherwise diffuse across the references; they live here at the front on purpose:

1. **Parity-first.** Debinarize a known-good vanilla vehicle (`civiliansedan`, ODOL v54) ONCE and diff your
   model against it — LODs, named selections, crew proxies, wheel hubs, componentNN, memory points — into a
   single master gap checklist. Fix every gap in one pass instead of discovering them error-by-error in-game.
   → `vehicle-structural-parity.md` "Parity-first method".
2. **In-game is the ONLY gate; offline is a hint.** Offline parity / frame / winding / render checks repeatedly
   passed GREEN while the car still failed in-game (proxy frame, body winding, seat collidability). A metric that
   is `0.000`/`100%` *by construction* (winding-vs-its-own-normals, frame=py3d-identity) proves internal
   consistency, NOT that DayZ renders / spawns / seats correctly. Never close a phase on a tautological gate.
3. **Crew-probe headless FIRST** when a get-in / radial action will not appear for a seat. BEFORE any rebuild
   cycle: spawn the car + a known-good control (LFQuad/Croco) headless, dump `CrewPositionIndex(0..79)`, and run
   `RaycastRV(ObjIntersectView)` per seat anchored at `pos_driver`/`pos_codriver`. This is what caught the
   inward-winding blocker (#4) without eyeballing and broke the blind-rebuild loop. → `vehicle-structural-parity.md` crew-probe.
   - **(added 2026-07-28, LL-219) A probe you INHERIT carries the coordinates of the artifact of THEN —
     re-derive its targets from source before believing a negative.** The probe is not the thing that
     rots; a hardcoded seat centre is. Re-running it verbatim yields a `hit=0` that is **aim, not
     mechanism**, and it is indistinguishable from the real verdict — while being exactly the
     "interesting" answer nobody re-questions. Measured on SUB_BRZ: the s9 mission
     (`brz_crew_probe_init.c:122-123`) aims at engine `(-0.40, 0.72, -0.12)` / `(0.54, 0.72, -0.12)`,
     while today's boxes come from `profiles\<car>.json` → `rip_p3_structural.py` seat params at
     py3d `(±0.357, 0.55, 0.12)` with half-extents `(0.22, 0.25, 0.25)` — the codriver ray passes
     **3.7 cm** from the box face in X. Still inside, zero margin. Procedure: (a) re-derive the aim
     point from the profile + generator that produced TODAY's artifact, never from the handoff that
     described it; (b) compute the ray's margin against the target box — margin below ~one half-extent
     means the negative is not evidence, fix the literal first; (c) log the aim point used next to the
     verdict, so a later reader can tell a real `hit=0` from a miss. Same family as METHOD #2
     (measure, never assume) applied to the instrument instead of the artifact.
4. **Two failed rebuilds on ONE symptom = HARD STOP — build the probe, do not fire cycle #3.** The rule
   predated the failures and still got skipped (retro 2026-07-03: copilot get-in ~7 days of serial wrong
   hypotheses; handlebar ~2 sessions of parameter sweeps settled by ONE GetSteering log; BRZ get-in 3
   bottom-up sessions when the gate was one script override) — while EVERY time the discipline ran
   (both-sides log line, crew-probe, headless harness, LL-100 field-diff vs a working referent) the issue
   closed in a single pass. Before the 3rd in-game cycle on the same symptom: enumerate candidate causes,
   read the actual mechanism (engine source / wiki, not intuition), instrument BOTH client and server
   (verify the hook actually fires — a silent log IS a signal, `OnUpdate` is not an engine callback), then
   ONE directed fix. If two probes also fail, escalate to a multi-agent audit over the REAL files — that
   escalation resolved the LFQuad wheelsim stall (4 sessions serial) in one session.

## PREFLIGHT

Gate real build work on `/dayz-preflight` (P:\ mounted, AddonBuilder present, P:\Mods junction), per
`_shared/dayz-conventions.md`. Authoring config / model.cfg offline does not need it; packing does.

## THE THREE FILES (and what each owns)

| File | Owns | Does NOT own |
|---|---|---|
| `.p3d` | geometry, LODs, named selections, memory points, proxies, **mass + CoM** (Geometry-LOD vertex weights) | physics params, animation values |
| `config.cpp` | the `CarScript` class, drivetrain / engine / suspension, `Crew`, damage, lights, cargo, attachments, sounds, `AnimationSources` | mass, CoM, animation axes |
| `model.cfg` | `CfgSkeletons` (bone hierarchy) + `CfgModels.Animations` (how each bone moves) | physics, which sources are user-driven |

Mass is **not** a config field — it is computed from Geometry-LOD vertex weights. Full detail in the
references.

## REFERENCES (read by task)

- **Author a vehicle from scratch** → `references/vehicle-config-and-modelcfg.md`: the complete,
  source-verified `config.cpp` + `model.cfg` for a drivable car (Tyson89 Landrover + Crocodoc
  QuadBike anchored), every block end-to-end with provenance labels.
- **Make an imported / procedural model actually work** → `references/vehicle-structural-parity.md`:
  the parity-first method — debinarize `civiliansedan` ONCE, diff your model against it, and build
  all missing LODs / selections / crew proxies / wheel hubs in one pass instead of discovering them
  error-by-error in-game. Crew proxies, wheel hubs, lights, ride-height. Derived from the LFQuad
  parity audit. Its **Appendix "REGEN-FROM-glTF + GET-IN RADIAL / LOD ladder"** owns the regen-from-glTF
  proxy-split traps and the proxy-body get-in radial + LOD ladder (sectioned from the core).
- **Imported-car VISUAL gates + winding session changelog** → `references/visual-gates-and-winding.md`:
  the full per-session history of preflight item #10 (sub-entries #10(a)-#10(o), s14->s23), including
  SUPERSEDED entries. The core keeps only #10 as a stub plus THE RULE; this file is the detail behind
  every `#10(x)` cite.
- **Ship it without it breaking on a server** → `references/build-packaging-and-debug.md`:
  binarize dropping config-only textures (white vehicle), ODOL-vs-MLOD `model.cfg`, reversed wheel
  spin, harmless proxy drive paths, and offline PBO verification. The failures that pass
  filepatching and break on a dedicated box. The LFQuad shipping lessons.
- **Boats, trucks, and the ATV / motorbike gaps** → `references/vehicle-types-boat-truck.md`:
  the `Transport`→Car/Boat sibling hierarchy and the per-type deltas — boat propeller/buoyancy/
  BoatFluid + always-free get-in, truck 3-axle DRIVE_642 + single-classname double wheels, ATV
  slots on `Chassis`, and the honest motorbike gap. All source-verified against vanilla `P:\scripts`.
- **Get-in prompt, cursor actions and proxied-sub pose** →
  `references/get-in-actions-and-proxy-pose.md`: the four-link get-in condition
  chain, the `ActionConstructor` + `PlayerBase` registration contract, and the
  measured `Geometry`/`autocenter=0` gate for multi-LOD proxy submodels.
- **Let a rider FIRE their own weapon from a moving vehicle (free-gunner / walk-on-bed)** →
  `references/gunner-shoot-from-vehicle.md`: the SIBNIC "Gunner" pattern reverse-engineered — the one
  trick (`IsInVehicle()`→false unlocks the weapon) plus `LinkToLocalSpaceOf` attach, frozen physics,
  `HumanGunnerCommand` pose, edge-detection raycast walk controller, leash/tether, per-vehicle JSON of up
  to 10 slots, and the client-authoritative weakness to fix. The **handheld free-gunner** family;
  composes with the fixed-turret weapon recipe (vault `vehicle-weapon-system.md`).

### Imported-model pipeline (OBJ → DayZ `.p3d`)

When the body comes from an artist OBJ or another game (the LFQuad is an imported Yamaha Banshee),
these cover the import path end-to-end (recovered here because the plugin `dayz-model-pipeline`
dropped them in the 2026-06-05 migration):

- `references/external-obj-import.md` — end-to-end OBJ → game-ready `.p3d` walkthrough (parse,
  transform, decimate, assemble LODs, encode textures, write config). Start here.
- `references/decimation-libraries.md` — reducing a high-poly import to per-LOD face budgets.
- `references/png-to-paa-encoding.md` — PNG → PAA in pure Python, no external tools.
- `references/emissive-leds-and-dynamic-lights.md` — emissive materials + dynamic lights
  (headlights / brake / dashboard).
- `references/placement-and-autocenter.md` — origin / autocenter / placement gotchas.

> REDIRECT CAMBIO-1: el único índice síntoma→cookbook de familia B está en `../rip-vehicle-import/SKILL.md`.

## CITE-THEN-VERIFY

Vehicle config and model values are easy to half-remember. Before writing a class name, property, or
named selection, grep it in vanilla (`P:\dz\vehicles\`) or in the references' cited sources, and keep
the provenance labels the references already use (`[Landrover ✓]`, `[QuadBike]`, `[LFQuad ✓]`,
`[TBD-verify]`). Anchor any new vehicle lesson to a real mod with `path:line`, never to memory.


## source-game / source-game RIP IMPORT (added 2026-06-23)

Importing a car ripped from a source-game game (source-game Motorsport / Horizon — the "Grub" container:
`.modelbin` / `.swatchbin` / `.carbin`) into a DayZ `CarScript` vehicle is covered in
`references/rip-import.md`. It documents Manifest.xml INCLUDE/EXCLUDE (the `__slod`, `bumperfcustom`,
and stock-vs-widebody traps), RF right-side reconciliation (a LHD rip ships the driver side; passenger
doors/seats/skirt are mirror-gaps generated by X-mirror), data-driven dimensions from the `Locators.xml`
wheel locators (wheelbase cross-checked against the real car validates the transform read), the
GameDB-gated drivetrain/mass that the rip does not carry (mark `[UNVERIFIED]`, never guess-parse the
binary), and the `verify_<mod>.py` parity-verifier pattern (synthetic self-test as the non-vacuity proof).
Origin: the SUB_BRZ (Subaru BRZ FE '22) build, 2026-06-23.


## REGEN-FROM-glTF BODY + PROXY-SPLIT / GET-IN RADIAL + LOD LADDER -> `references/vehicle-structural-parity.md`

Regenerating a high-poly body from glTF/FBX and splitting it into proxies to beat the 65535 resolved-vertex ceiling (glTF->DayZ winding tautology, proxy-placement identity-frame trap, the confirmed model-space + no-`.p3d` + measured-frame convention), and the proxy-body **get-in radial + LOD ladder** (script-module binding, the geometric get-in blocker, the DECISIVE inward-wound seat ComponentNN + point flags `0x02000000`, reversed-wheel `angle1`, shell+proxy LOD ladder) are structural parity and now live in **`references/vehicle-structural-parity.md`** (Appendix "REGEN-FROM-glTF + GET-IN RADIAL / LOD ladder"). That file is their declared source of truth.

## (added 2026-06-28) Ownership de red: seat forzado server-side != ownership del cliente; PHYSICS lo conduce el owner

Invariante verificada (source + in-game, DayZ-MCP Fase 5 S0). PREFLIGHT antes de cualquier intento de
conducir/automatizar un coche desde un peer cliente o de razonar sobre "quien conduce":

- El coche es un **Pawn** (`Transport extends Pawn` bajo `FEATURE_NETWORK_RECONCILIATION`,
  transport.c:53 -> Car car.c:98 -> CarScript carscript.c:170). El `IsOwner()` de `IsServerOrOwner()`
  (carscript.c:3222-3231) es el **ownership de red del COCHE**, no del player (glosario pawn.c:5-8:
  Owner = el cliente que controla el pawn).
- **`IsServerOrOwner()` NO gatea el throttle.** Sus unicos consumidores son teardown/fluidos
  (carscript.c:822/850/986). El throttle->fisica es **proto native** (`SetThrottle` car.c:202, "future
  throttle value") y lo aplica el **simulador del cuerpo = el OWNER**. El unico `SetThrottle` de script
  (carscript.c:1377) esta muerto en produccion (`#ifdef DIAG_DEVELOPER`).
- Un coche **sin cliente-dueno = `IsAuthorityOwner`** (autoridad sin owner, pawn.c:199-200) -> lo
  simula el server -> un `SetThrottle` server-side **SI lo mueve**. Esto es un **artefacto de
  single-box/SP**, NO prueba de que el server conduzca coches que un cliente posee. (DayZ-MCP S0 F2:
  server movio un PHYSICS car pos_delta=2.29 porque ningun cliente lo poseia.)
- Un **`StartCommand_Vehicle` server-side** (p.ej. el `vehicle_enter` del MCP) sienta al player SOLO
  server-side: el cliente **nunca obtiene `GetGame().GetPlayer().GetCommand_Vehicle()` ni el ownership
  del coche** (medido in-game x6, da `not_seated` en el peer cliente). El get-in real
  (`ActionGetInTransport.Start()`, metodo compartido cliente+server, actiongetintransport.c:82-98) corre
  `StartCommand_Vehicle` en el Human **DEL CLIENTE** + reserva asiento por juncture
  (`AddInventoryJunctureEx`/`SetVehicle`, :141-161). La transferencia de ownership es proto-native (no
  existe `SetNetworkOwner` en script).
- **Consecuencia practica:** para conducir/medir **owner-side** desde un cliente, el cliente debe
  **tomar ownership el mismo** (get-in client-side), no depender de un seat forzado server-side. Y un
  test de owner-authority en **single-box** esta **confundido** (el cliente nunca posee de verdad) ->
  el discriminador limpio es un dedicado 2-maquinas con un cliente remoto que hace el get-in.
- Lectura de diagnostico: `IsOwner()` (pawn.c:194), `IsAuthorityOwner()` (pawn.c:199-200),
  `GetOwnerIdentity()` (pawn.c:209), `GetNetworkID()` (object.c:815). Extiende el caso get-in/radial
  (LL-164) a la dimension de red. Origen: DayZ-MCP S0 (2026-06-28).
- **Conducir owner-side desde script (el actuador — verificado in-game 0→39 km/h):** `Car.SetThrottle/SetSteering/
  SetBrake` llamados desde el MISSION (`OnUpdate` / un job) NO mueven el owner-sim PHYSICS — **`super` de
  `CarScript.OnInput(dt)` (`carscript.c:1303`) los PISA cada frame** con el input=0 del driver local. Fix: aplicar
  el throttle DENTRO de un `modded class CarScript.OnInput`, **TRAS `super.OnInput(dt)`** (donde el autopiloto debug
  vanilla `carscript.c:1377` lo hace). NO hay inyección vía `HumanInputController` (el input de vehículo es nativo,
  sin API de override). Síntoma: "el coche es del owner pero `SetThrottle` no lo mueve". Origen: DayZ-MCP Fase 5 (SP-032).

## PHYSICS = prediccion del owner con reconciliacion: escribir pose pelea con ella (SP-180, added 2026-08-06, LFHeli F-01)

Extiende la seccion de ownership de arriba. Invariante verificada (runtime + fichero, LFHeli 2026-08-06).
PREFLIGHT ante CUALQUIER sintoma de "lag de input" / "rubberband" / "el cliente revierte transforms" en un
CarScript server-authoritative:

- **Mide la estrategia ANTES de teorizar** (1 linea, cualquier lado): `Print(GetNetworkMoveStrategy().ToString())`
  — NONE=0, LATEST=1, PHYSICS=2 (`pawn.c:138-148`; getter proto native `pawn.c:218` — SI esta expuesto a script;
  una nota previa que decia lo contrario costo 3 semanas de desvio en LFHeli). En DayZ 1.29 CarScript corre
  **PHYSICS de serie** (medido `str=2 own=true` en el cliente piloto); no existe flag de config que la seleccione
  (verificado vanilla + Expansion): la fija el motor por clase nativa. `FEATURE_NETWORK_RECONCILIATION` es
  incondicional (`defines.c:64`).
- **Bajo PHYSICS el owner YA simula predictivamente** (contrato Pawn completo en vanilla: `pawn.c:256-329`
  ObtainMove/ConsumeMove/ReplayMove/RewindState; `CarScriptMove/OwnerState` `carscript.c:3198-3218`;
  `IsServerOrOwner()` `carscript.c:3222-3231`). Consecuencias:
  1. Un server que escribe pose/velocidad por tick (`SetOrientation`/`SetVelocity`) NO coopera: genera
     correccion continua owner<-authority = **lag estructural de ida-y-vuelta + snap-backs**. El sintoma se
     siente incluso en loopback (el RTT no es la unica latencia: tick server + replicacion + rewind).
  2. Escribir TRANSFORM desde el cliente owner se REVIERTE en ~0,3 s (medido LFHeli D1). No es un bug que
     depurar: es la reconciliacion funcionando. No gastes ciclos ahi.
  3. La via compatible es la de Expansion 1.28+: **fuerzas simetricas owner/server** (`dBodyApplyForce`
     `enphysics.c:146`, world space; commit gated por `dBodyIsActive && dBodyIsDynamic`,
     `ExpansionPhysicsState.c:209-218`) + input dentro del `PawnMove` nativo (su RPC legacy se APAGA bajo
     PHYSICS, `DayZExpansion CarScript.c:1014-1051`) + contrato Move/OwnerState custom con `super` primero
     (`ExpansionHelicopterScript.c:164-213`). El motor integra; nadie escribe pose.
- **Spike barato antes de comprometerse a esa arquitectura** (patron ForceSpike E, LFHeli
  `plans/2026-08-06-forcespike-e.md`): flag de tuning default-off + ventana de 1,5 s en la que ambos lados
  aplican la MISMA fuerza (contra-gravedad + pulso lateral en un eje que nada del modelo toca) y el server
  suspende su actuador cinematico; trazas por tick ambos lados; parser offline dictamina SI/NO/INCONCLUSO
  (`LFHeli_dev/tools/spike_verdict.py`). Trampas del harness ya pagadas: el abort debe ser SIMETRICO
  (motor/asiento/salida del estado de vuelo), la supresion de la tecla secuestrada va AGUAS ARRIBA de todos
  los consumidores del canal, y toda salida del estado de vuelo limpia la ventana.
- Estado de la evidencia: TODO MEDIDO. Vuelo de veredicto 2026-08-06: **SI** — 3 pulsos limpios en el
  owner (pendiente local ~1,6 m/s2 vs 1,5 teorica, ganancia retenida, reversion puntual <=30% por el
  desfase owner->server); el snap-back al EXPIRAR la ventana es el actuador cinematico reabsorbiendo
  (la razon de retirar la escritura de pose en la via completa); un pulso owner-only cerca del suelo
  (server sin armar por AGL) se revirtio 91% = la limitacion F4 en vivo. Percepcion del piloto: nula
  (0,15 g lateral durante un ascenso a 7-11 m/s) — el gate es telemetrico, no de feel.

## Armazon Pawn custom (Move/OwnerState): la escalera de tipos y sus reglas duras (SP-188, added 2026-08-06, LFHeli D3-1)

Continuacion de SP-180: cuando la via es "fuerzas + owner prediction", el PRIMER paso de
construccion es un armazon Pawn INERTE (tipos custom + hooks solo-log, vuelo intacto) — valida el
wiring con el motor antes de migrar ningun solver (orden de menor riesgo verificado contra el
corpus Expansion). Receta verificada por fuente vanilla + compile gate (LFHeli 2026-08-06):

- **Escalera de tipos** (deriva del ultimo peldano, no de Pawn*): `PawnMove -> TransportMove ->
  CarMove -> CarScriptMove` y `PawnOwnerState -> TransportOwnerState -> CarOwnerState ->
  CarScriptOwnerState` (`transport.c:11-50`, `car.c:89-93`, `carscript.c:135-152`).
  `TransportOwnerState/TransportMove` llevan transform + velocidad lineal + angular NATIVOS
  (`transport.c:13-23,:35-42`): **NO los dupliques en el estado custom**.
- **Hooks** (`pawn.c:238-311`, todos `protected event`): `GetMoveType`/`GetOwnerStateType` (el
  motor instancia los tipos EN CONSTRUCCION, `pawn.c:235,:244` — los overrides deben existir en la
  clase, no activarse tarde), `ObtainMove`, `ConsumeMove`, `ReplayMove` (bool: respeta el rechazo
  del super antes de procesar), `ObtainState`, `RewindState(state, move, inout NetworkRewindType)`.
  CarScript ya implementa Get*Type/ObtainState/RewindState (`carscript.c:3198-3218`) — super
  SIEMPRE y exactamente una vez (ObtainState/RewindState del super llevan `m_fTime`).
- **Serializacion**: `Write/Read` con super PRIMERO; NUNCA serializar `vector` (expandir a
  floats); `EstimateMaximumSize()` = super + 4 bytes por escalar (bool cuenta 4, conservador).
  El Move lleva los ejes RAW pre-authority-scale (la atenuacion/FSM se recomputan por tick de
  solve; hornearlas rompe el determinismo del replay). El latch/estado con memoria del solver va
  en el OwnerState (server -> owner), no en el Move.
- **`ReadRawLocal` DENTRO de `ObtainMove`** (R22 que costo una ronda: el orden nativo
  ObtainMove<->EOnSimulate NO esta expuesto a script; fiarse de la ultima lectura del tick puede
  serializar ceros/stale y tus gates de round-trip validan un cableado VACIO). Exige ademas que el
  gate de payload rechace la corrida si todos los samples van en neutro.
- **Instrumentacion del armazon inerte**: match owner<->authority por `GetMoveId()` EXACTO
  (muestreo determinista `id % 64 == 0` en AMBOS lados), nunca por reloj; `rewind` se loguea
  siempre (raro), `replay` solo muestreado (un rewind storm re-corre todos los moves pendientes e
  inunda el log del cliente, truncado a ~255 chars/linea); contadores agregados a 1 Hz.
- **"Inerte" lo es para el VUELO, no para la RED**: los tipos custom anaden payload por
  move/correccion y una asimetria Write/Read desincroniza al owner — el gate de payload existe
  para eso.
- Estado de la evidencia: TODO CONFIRMADO EN RUNTIME (vuelo LFHeli D3-1, 2026-08-06): el motor
  instancia los tipos custom y los transporta (G1), 94 moves muestreados con los 5 ejes exactos en
  ambos lados y 48 con payload no-cero (G2), 477 rewinds + 47 replays visibles en el owner (G3).
  Trampa del receptor: el script log de DayZ envuelve cada Print en comillas simples — un parser
  de logs debe hacer strip de la comilla pegada al ULTIMO token de la linea o el gate de payload
  da un falso FAIL en ese campo.
- CAVEAT medido en el mismo vuelo: la cadena script de CONTACTO no recibio NI UN callback del
  asiento skid-suelo (0 OnContact en todo el vuelo, con touchdown real via AGL) — el override de
  Car.OnContact NO garantiza contactos suaves de asentado. Antes de construir logica sobre
  contactos de un vehiculo, mide primero que el callback dispare para TU caso (un print one-shot);
  la via robusta candidata es EntityEvent.CONTACT + EOnContact, pendiente de validar.

## Auto-retopo of a dense rip = Quadriflow PER-PANEL + ASCENDING target sweep (SP-055, added 2026-07-14)

For retopologizing a dense vehicle rip to get a clean bake->UV low-poly (domain invariant; saves ~3 discovery cycles):
- **Voxel-remesh does NOT work for hard-surface** (melts panels into organic blobs, loses holes/edges - verified on a Banshee body 37k tris). **Quadriflow PER-PANEL does**: split by loose parts -> remesh each with `use_preserve_sharp` + `use_preserve_boundary`, marking sharp by 35 deg angle first. Whole-bucket gives worse flow than per-panel.
- **`bpy.ops.object.quadriflow_remesh` "Remeshing failed" on a CLEAN mesh (boundary=0, non-manifold=0, euler=2) is NOT dirty geometry - it is a TARGET TOO LOW.** The solver aborts when `target_faces` cannot place singularities for the feature density. Fix = ASCENDING target sweep (not descending): try on THROWAWAY copies (QF is destructive), accept the leanest target that gives quads with `faces >= ~0.4 x desired`. Measured: a 8972-tri fender fails at target 100-1800, engages at >=2600. `remove_doubles` / make-manifold / dissolve-degenerate do NOT help if the mesh is already clean.
- **Quadriflow = ISOTROPIC remesh** (uniform grid, does not align loops to edges like manual retopo). Right for bake-source->low-poly->UV (detail carried by the normal map). A vehicle panel does not deform, so the deform caveat does not apply.
- **Pieces < ~200 tris = detail (clips/bolts): leave un-remeshed.** Recalc normals outside on join; watch thin/double-wall panels (a fender modelled with thickness goes dark on the inner face - the game low-poly wants a single face).

Compose with invariant #0 (Gate #0 mesh+UV, SP-052) and `20_Knowledge/uv-mapping-dayz.md`. CAVEAT: the full auto-retopo pipeline is still user-gated (visual) and not in-game validated; the VERIFIED durable fact is the Quadriflow solver behaviour (target-sweep). Origin: LFQuad v2 auto-retopo experiment (2026-07-06), SEAT.001 36899 tris -> 10502 quads (-72%).

## An in-game GEOMETRIC POSE complaint can be a PERSPECTIVE artifact - measure the DEPLOYED ODOL before applying any offset (SP-076, added 2026-07-20)

When the user reports "piece X sits N cm off / tilted" on an imported model (rotor vs its housing ring, wheel vs arch, part vs socket), do NOT author a corrective offset/rotation from the capture:

1. **Measure the DEPLOYED artifact, not the source**: debinarize the deployed ODOL (skill `dayz-p3d-debinarizer`) and measure the piece against its geometric reference in engine frame - circle-fit (least-squares) of the ring/arch rim, plane-fit (PCA) of a blade/wheel disc, bbox of the socket. Compare piece center / disc normal against the fitted reference.
2. **If the measurement says centered (offset ~mm, tilt ~0 deg), the complaint is PERSPECTIVE**: a ring/aperture with depth along its axis projects obliquely, so a geometrically centered piece LOOKS off-center from an angle - and the apparent offset direction changes with camera angle. Confirm by reproducing the illusion: flat-color render (piece magenta / hull grey) from the user's capture angle vs an orthographic front-on render.
3. **Apply an offset ONLY if the deployed-artifact measurement demands it.** An eyeballed offset on an already-centered model is a REGRESSION (it moves what was right) and burns an in-game cycle to discover it.

Measured case (LFHeli OH-1 round 3, AMENDED same day): user reported tail rotor "10 cm low" + interior "10 cm high, pokes through the canopy". First pass measured global bboxes and called it all perspective - WRONG on two counts: (a) "interior inside the glass" by global bbox missed a REAL 7.25 cm LOCAL protrusion through the canopy roof (per-cell interior-maxY vs glass-surface-Y grid found it; the user's eye was right); (b) the ring fit gave 9.7 mm misreported as 0.9 mm (units slip). CAVEAT the rule accordingly: bbox-vs-bbox NEVER proves containment - protrusion is LOCAL, measure per-cell surface-vs-surface before declaring a pose complaint perceptual. Complements the feel rule (subjective feel -> player data; measurable pose -> deployed-artifact measurement). Origin: LFHeli_dev/reviews/2026-07-20-LA-medicion-pose-fina.md.


## Proxy placement convention - measured on a working reference car (SP-091, added 2026-07-26)

Two full build+test cycles were burned on LFHeli OH-1 guessing this from the broken model alone.
The answer was one probe away: read a car that WORKS. Reference used:
`SUB_BRZ_dev\_references\Tyson89-Landrover` (MLOD v257, py3d reads it directly, no debinarize).

MEASURED on Landrover.p3d LOD0 (18 proxies):
- **NOT ONE has its anchor at the origin.** Every anchor sits at the real target position:
  `Landrover_Wheel [0.8746, 0.4513, -1.5638]`, `Landrover_Driver_Door [0.888, 0.6492, -0.8629]`,
  `Landrover_Trunk [0.0021, 1.1487, 2.5139]`.
- **NOT ONE has an identity frame (0 of 18).** The standard frame is `[[-1,0,0],[0,0,1],[0,1,0]]`;
  the opposite side mirrors it as `[[1,0,0],[0,0,-1],[0,1,0]]`; the spare wheel uses its own rotation.
- Sub-models are authored in **proxy-local space**, origin at the attachment point:
  `Landrover_Wheel |center| = 0.000 m`, `Landrover_Trunk 0.000 m`,
  `Landrover_Hood 0.726 m` and `Landrover_Driver_Door 0.821 m` (they pivot on their hinge).

RULES:
1. Proxy anchor = target position in HOST coordinates. Anchor at origin is a defect.
2. Sub-model geometry authored near ITS OWN origin (< ~1 m). A sub-model whose bbox center sits
   2-7 m away is authored in host coordinates - that is the defect, and it is the one worth gating.
3. The frame `[[-1,0,0],[0,0,1],[0,1,0]]` is the NORMAL neutral, not a smell: the crew proxies that
   work carry it too. Numerical identity NEVER appears in a working model - forcing it makes
   placement WORSE (verified in-game on OH-1).
4. A zero-size crew marker proxy (~463 bytes) is immune to any frame rotation because its geometry
   sits at the origin. Do not infer the convention from those - use a geometry-bearing proxy.
5. Doors on a working vehicle are PROXIES with their own .p3d anchored at the hinge, not baked
   geometry driven by a bone. Consider that before designing bone-driven doors.

METHOD RULE (the expensive lesson): calibrate every gate rule against a model that WORKS before
trusting it. Three rules were written from the broken model; two were false positives that would
have red-flagged every correct model. The reference car killed both in one probe.

Gates implementing this: `LFHeli_dev\tools\import_gates\proxy_placement_gate.py` (P1 anchor at
origin, P8 sub-model authored in host space, P9 normal/winding coherence) plus
`texture_binding_gate.py` (one .rvmat must not carry two base textures).

## Rewriting a proxy triangle: regla corregida para proxies y caras visuales (SP-093)
> Historial del texto superado: `history/cambio-1-superseded-family-b-rules.md` §“SP-093 antes de la corrección de alcance”.

Rewriting the 3 points of a proxy triangle to change its ORIENTATION flips the geometric winding
while the stored vertex normals stay as they were. Measured on OH-1: `dot(geometric, stored)` went
from `+1.0` to `-1.0` on all three proxies. A pure TRANSLATION preserves winding.

SP-093 says any parity check of a .p3d edit must assert `dot(geometric, stored) > 0.9` on every
touched face. That is right for proxy triangles and WRONG as a general rule: on a hull authored with
reversed winding on purpose (`FLIP_VISUAL_WINDING = True` in the OH-1 assembler), every visual face
has a negative dot BY DESIGN. Measured on the deployed OH-1: `door_1` = 7227 dots per LOD, **zero**
above 0.9, median `-0.942910`; `door_2` median `-0.939892`. A gate applying SP-093 to migrated
visual faces fails 100% of valid input, and "fixing" it by flipping normals is the regression.

Rule: proxy triangles -> `dot > 0.9`. Migrated/edited visual faces -> equality of the RESOLVED
normal vector against the baseline, corner by corner, within 1e-6.

## Two diagnoses that look solid and are not: identical textures, and server co-move (SP-094, added 2026-07-26)

Both cost real cycles on LFHeli OH-1. Both are one cheap measurement away.

**A. "One .rvmat bound to two base textures" is NOT automatically the cause of a texture defect.**
On OH-1, `oh1_fuselage.rvmat` resolved to `rd_oh1_fuselage_co.paa` (10403 faces) and
`rd_oh1_hs_fuselage_basecolor_co.paa` (6420 faces), UVs perfectly inside [0,1]. It reads like a
smoking gun. **Hashing the files killed it**: all four .paa were byte-identical
(`16B0FD978AAD7552...`, 6822200 bytes) - the same image under two names, so reassigning the faces
would not change a single pixel. Rule: before concluding a texture-binding split explains anything
visible, **hash the referenced textures**. If they are identical, the split is hygiene, not a cause,
and the real defect is elsewhere (runtime/VFS, material stage, UV layout vs atlas content).
This applies directly to the T1 rule of `texture_binding_gate.py` - the gate is right to flag it,
but a FAIL there is not a diagnosis.

**B. Server-authoritative co-movement does NOT prove the client renders it that way.**
The user reported the hull staying behind while rotors and interior climbed. The instrumented
measurement over a 28 m ascent said the opposite: `ratio shell/root = 1.000`, `proxy/root = 1.000`,
separation constant at 0.626 m - hull and proxy co-move exactly. Both statements were true: the
authoritative transform is coherent and the client still renders the part detached. Rule: when a
part "does not follow", measure BOTH sides before designing a fix. A perfect server-side ratio with
a visible mismatch points at render/replication/perception, and it rules out the physics and
cohesion branches - which is worth a lot, because those are the expensive ones to chase.

## `autocenter=0`: alcance corregido por LOD, host y submodelo (SP-097)
> Historial del texto superado: `history/cambio-1-superseded-family-b-rules.md` §“SP-097 antes de separar host, submodelo y prueba runtime”.

Measured control vs OH-1: all five geometry-bearing Landrover sub-models carry `autocenter=0` on
their visual LOD **and** Geometry (5/5); the three OH-1 proxied sub-models carry it only on an empty
Geometry (0/3 on visual). But the HOST of the control has `props={}` on its visual LOD, exactly like
ours - **the host is exculpated, the sub-models are the gap.** SP-097 does not make that split.

Two further measurements bound the claim, so do not sell the property as a fix:
- The canonical symptom (`model_info.bounding_center != 0` after binarize) can be ABSENT while the
  visual-LOD property is missing: the deployed OH-1 shell and sub-models all read `(0,0,0)`, because
  an empty Geometry LOD carrying `autocenter=0` is already enough to stop binarize re-centring.
- An A/B binarize with and without the property on the visual LODs produced identical semantics -
  66/66 `model_info` fields equal, same face counts per LOD; only the property block differs. So the
  property travels to the ODOL and is verifiable there, but any effect is RUNTIME and cannot be
  predicted offline. Adjudicating it needs an isolated in-game A/B: two PBOs differing only in the
  property, with a reproducible camera pose.

## An import gate rule is not deliverable without a negative fixture (SP-096, added 2026-07-27)

SP-091 established the method rule: calibrate every gate rule against a model that WORKS. That is
necessary and NOT sufficient. The LFHeli OH-1 gates were calibrated against a good reference and
still shipped a gate that passed the broken model, failed the good one, and accepted absurd input.
An adversarial review with in-memory mutation took them apart in one pass:

- 12 proxies displaced by 100/200/300 m -> **PASS**. The distance rule existed and fired, but it
  emitted INFO, and the verdict counted only FAIL.
- 30.419 faces repointed to a texture that does not exist -> **PASS**, with zero findings naming it.
  The rule walked the inventory looking for unreferenced files, never the reverse direction.
- The "corrected" reference fixture itself carried `dot(geometric, stored) = -1.0` on 24 of its 48
  proxy vertices - the exact defect SP-093 is about - and the suite asserted it must PASS.
- The suite advertised as "11 tests green" was 7 tests with 4 red, and could not even start from the
  official layout because it pointed at a directory that did not exist there.

RULES for any model-import gate:

1. **Every rule ships with TWO fixtures, both executed by the suite**: a positive (the good
   reference AND the current clean model both pass) and a **negative mutant** built in memory from a
   good model with the exact defect the rule claims to detect, which the rule MUST fail. A rule
   without a mutant that makes it fail is not deliverable - that is the hole every false PASS above
   came through.
2. **No INFO, no WARN inside the verdict.** If it should block, it is a FAIL; if it should not, it
   is a diagnostic print and stays out of the verdict and the exit code. A severity that cannot
   change the outcome is a rule that does not exist.
3. **Regenerate the reference fixture and verify it against the rules it is supposed to certify.**
   A fixture is an artifact like any other; it rots, and a corrupt one converts the whole suite into
   theatre.
4. **Prefer few solid rules to many plausible ones.** The rebuild kept three - proxy-normal
   coherence, referenced-texture existence, finite UVs - each with its mutant, and that suite is
   worth more than the twelve rules it replaced.
5. **A rule whose threshold is a bare literal is a smell.** Derive it from measurement on the good
   case and leave the number and its derivation in the code.
6. **When a gate change makes a previously green tree go red, fix the RULE or accept the finding -
   never re-baseline the expected value to make it pass.** Deciding between the two is the user's
   call, not implementation.

Origin: LFHeli OH-1 2026-07-27, R21 dual (Codex + Claude subagent). The rebuilt gate lives at
`LFHeli_dev\tools\import_gates_v2\`; the retired one at `tools\import_gates_RETIRED_20260726\` as a
negative reference.

## Reglas promovidas del corpus de lecciones (added 2026-07-27)

Promovidas desde `AI/20_Knowledge/lessons-learned.md` para que lleguen por trigger en vez
de depender de que alguien recuerde buscarlas. Cada regla cita su `LL-NNN` de origen;
la entrada completa (síntoma, origen, evidencia) vive allí. No quites la cita: el índice
`lessons-index.md` detecta la promoción buscando esa referencia dentro de las skills.

- **LL-076** — Antes de diferir una feature, clasifica la severidad de su ausencia y valida los mínimos exigidos por el engine. Todo `CarScript` debe incluir al menos `DamageSystem.GlobalHealth`; su ausencia puede matar el proceso aunque el daño sea una feature posterior.
- **LL-172** — Ante paneles negros o see-through, decodifica primero el `_co` desplegado y mide píxeles oscuros. Si la textura está limpia, trata el síntoma como winding y exige captura in-game antes de voltear regiones.


## Detachable parts (doors/hood/trunk): the FOUR-layer contract, and three rules it corrects (SP-098, added 2026-07-28)

Measured on a working control, `SUB_BRZ_dev\_references\Tyson89-Landrover` (MLOD v257, py3d reads it
directly). LFHeli OH-1 spent weeks on "the door does not animate" with the full script+model contract
verified, because the project only ever knew layer 3 below.

### The contract is four layers, not one

1. **`CfgSlots`** (`Tyson89-Landrover\scripts\config.cpp:65-77`)
   ```cpp
   class Slot_Landrover_Driver_Door {
       name = "Landrover_Driver_Door";
       displayName = "...";
       selection = "doors_driver";        // <-- the ANIMATION BONE selection
       ghostIcon = "set:dayz_inventory image:doorfront";
   };
   ```
   `selection` is the binding between "the attachment is mounted" and "the proxy is drawn".

2. **`CfgNonAIVehicles` / `ProxyVehiclePart`** (`Tyson89-Landrover\scripts\config.cpp:80-100`) —
   THE LAYER PEOPLE MISS.
   ```cpp
   class ProxyAttachment;
   class ProxyVehiclePart : ProxyAttachment {
       scope=2; simulation="ProxyInventory"; autocenter=0; animated=0; shadow=1; reversed=0;
   };
   class ProxyLandrover_Driver_Door : ProxyVehiclePart {
       Model = "\Landrover\proxy\Landrover_Driver_Door.p3d";
       inventorySlot = "Landrover_Driver_Door";
   };
   ```
   Without it the engine does not resolve the host's `proxy:\...` as an attachment proxy. Note
   `autocenter=0` appears HERE too: vanilla declares it in THREE places - the sub-model's visual
   LOD, the sub-model's Geometry LOD, and this config class.

3. **Item class** `Landrover_Driver_Door : CarDoor` with `Model`, `inventorySlot`, `hiddenSelections`,
   `weight`, `itemSize[]`, `physLayer`, `DamageSystem` (`Tyson89-Landrover\config.cpp:70-95`).

4. **Vehicle**: the slot name inside `attachments[]`, plus `class Doors` in the vehicle DamageSystem.

**Host proxy triangle: DOUBLE membership.** Measured on `Landrover.p3d` LOD0, the 3 points of
`proxy:\Landrover\proxy\Landrover_Driver_Door.001` belong 3/3 to `doors_driver` (the bone) AND 3/3
to `Landrover_Driver_Door` (the slot name). A proxy wired only to the bone animates but is not
attachment-aware.

**A detachable part is a physical ITEM.** It can be dropped on the ground, so its `.p3d` needs real
special LODs, not an empty Geometry. Measured: `Landrover_Driver_Door.p3d` = visual `463/754`,
Geometry `32/24`, Memory `7/0`, ViewGeo `32/24`, FireGeo `72/56`, with `autocenter=0` on the visual
LOD and on Geometry. Budget the item LODs before promising the feature.

Custom inventory slots are the T148506 family (`enforce-script-reference`): if the slot name and the
`inventorySlot` string diverge, the item never attaches and the proxy never draws.

> REDIRECT CAMBIO-1: la corrección de SP-093 ocupa ahora el sitio original de SP-093.

> REDIRECT CAMBIO-1: la corrección de SP-097 ocupa ahora el sitio original de SP-097.

### `binarize` is NOT deterministic - never gate on ODOL byte identity

Two runs of `binarize.exe -always` over the same source, same flags: the shell came out
`2,886,719 b` / `8C290530214C...` and `2,763,097 b` / `0705207DB7F0...`; the interior `1,062,412 b`
vs `1,062,417 b`. The two small rotor models were byte-identical, so the effect scales with model
size. Semantically the two shells match (66/66 `model_info` fields, same faces/selections/properties
per LOD); the divergence is encoding/compression order.

Rule: gates over ODOL compare SEMANTICS (per-LOD counts, selections, properties, proxies, centres),
never bytes. Hash identity is still valid for MLOD, which the pipeline writes itself. Re-read any
historical "the ODOL came out byte-identical" claim with this in mind.

Origin: LFHeli OH-1 2026-07-28, the session that converted doors to proxied attachments after the
user pointed out that a vanilla car only draws the door proxy when the door is attached.

### Two traps that follow immediately from converting a baked part into an attachment

Both bite the moment the part becomes an attachment, and both look like "my model change
broke the vehicle".

**1. A detachable part is INVISIBLE on every debug/admin spawn until something attaches it.**
`CreateObject`, VPP/admin-tool spawns and MCP-style bridge spawns do not populate attachment
slots - that is why a VPP-spawned vanilla car has no wheels. The moment you move a door from
baked hull geometry to an attachment, a spawned vehicle shows an empty doorway, and it reads as
a regression when it is the contract working.

The hook is `OnDebugSpawn()` (`P:\scripts\3_game\entities\entityai.c:3902-3907`, with
`OnDebugSpawnEx(DebugSpawnParams)` delegating to it). Two source-verified patterns:

- explicit `CreateAttachment` per part - `LFQuad.c:176-189`:
  ```c
  override void OnDebugSpawn()
  {
      EntityAI entity;
      if (Class.CastTo(entity, this))
      {
          entity.GetInventory().CreateAttachment("CarBattery");
          entity.GetInventory().CreateAttachment("SparkPlug");
          entity.GetInventory().CreateAttachment("LFQuad_Wheel_Front");
          // ...
      }
  }
  ```
- vanilla car, `CreateInInventory` per part - `P:\scripts\4_world\entities\vehicles\inheritedcars\civiliansedan.c:407-429`
  (`SpawnUniversalParts(); SpawnAdditionalItems(); FillUpCarFluids();` then one call per door/wheel).

The `EntityAI` base implementation is config-driven instead: it reads the type's `attachments[]`
and scans `CfgVehicles`/`CfgMagazines`/`CfgWeapons` for any class whose `inventorySlot` matches,
then `CreateInInventory`s it (`entityai.c:3907-3958`). Calling `super.OnDebugSpawn()` therefore
attaches per-type from config with no per-airframe code - useful when one script base serves
several models. Note the vanilla cars deliberately do NOT call super; they list parts explicitly.

**2. `attachments[]` depende del límite de PBO; `+=` no es una regla incondicional.**
> Historial del texto superado: `history/cambio-1-superseded-family-b-rules.md` §“attachments[] += como regla incondicional”.
Dentro del mismo árbol de configuración fuente, `+=` puede conservar los slots del padre. Cuando la clase padre procede de otro PBO ya compilado, esa lista no es una base contractual segura: materializa en la clase hija la lista COMPLETA de slots vitales y propios. Esto corrige la regla anterior con el caso verificado en `AI/20_Knowledge/dayz-mod-implementation-checklists.md:234-240` (E28).

El gate no busca un token `+=`: inspecciona la lista efectiva después de compilar/config-dump y comprueba batería, ignición, radiador, ruedas y cada puerta/parte declarada. Un cambio de puertas no puede retirar silenciosamente un slot vital. Mantén además la comprobación independiente de que cada parte declarada aparece en la ruta `OnDebugSpawn`; son contratos distintos.

## (added 2026-07-28) An animation's SIGN is never judged without its AXIS - use the pseudovector against the control

Wheels spinning backwards, doors hinging the wrong way and inverted steering are the same bug,
and reviewing `angle1` alone cannot catch any of them, because **the axis sign is a free
reparametrization**: `R(theta, a) == R(-theta, -a)`, so a mod with axis `(-1,0,0)` and
`angle1 = +6.28` moves *identically* to the control's `(1,0,0)` / `-6.28`. Compare the raw
angle against a control and you will flag a correct artifact and miss a real one. The
falsifiable invariant is the pseudovector `angle1 x unit(axis_dir)`, compared against the
homologous class of the vanilla CONTROL.

**Where the evidence lives after Binarize** (so this is an OFFLINE gate, not an in-game guess):
the compiled ODOL carries the whole rig. `odol_reader.py:82-160` - `animations.classes[i]` has
`anim_name`, `anim_source`, `anim_type` (0=rotation, 4=translation), `angle0/angle1`,
`offset0/offset1`; `animations.anims2bones[lod][i]` indexes the **global** skeleton (it does NOT
go through `lod.sub_skeletons_to_skeleton`); `animations.axis_data[lod][i]` is
**`(position, direction)`, NOT two points** - measured: wheel axes come back as exactly
`(1,0,0)` unit vectors and dampers as `(0, 0.3, 0)` where 0.3 is the travel length.
Binarize also **lowercases `anim_source` while preserving `anim_name` case**, so compare
sources case-insensitively.

**The trap that inverts the verdict: picking the wrong homologue in the control.**
`CivilianSedan` carries TWO classes driven by `turnfrontleft` with identical angles and
**opposite** axes - `steering_swivel_1_1` on `(0,-1,0)` and `steering_arm_steering_1_1` on
`(0,+1,0)`. The homologue of your steering bone is the **swivel** (the knuckle the wheel hangs
from, i.e. the parent of `wheel_X_1` in your skeleton chain), never the tie rod. Read the
control's skeleton chain before choosing; a comment in your own `model.cfg` asserting which one
you matched is not evidence.

**Worked parity check** (SUB_BRZ vs `civiliansedan.p3d` v54, measured 2026-07-28):

| Leg | Mod | Control homologue | Verdict |
|---|---|---|---|
| wheel roll x4 | `-6.283185 x (1,0,0)` | `wheel_1_1..2_2`: same | identical |
| steering x2 | `+pi/2 x (0,1,0)` | `steering_swivel_X_1`: `-pi/2 x (0,-1,0)` | identical |
| door driver / codriver | `+1.396 x (0,1,0)` / `-1.396 x (0,1,0)` | `DoorsDriver_a` / `DoorsCoDriver_a`: same signs | same convention |

**Dampers have no vanilla homologue if you use the single-bone translation rig** (Tyson89
pattern). `CivilianSedan` models suspension as ~20 ROTATION classes on `susp_arm_*` bones.
Gating your `type="translation"` dampers against the sedan fails by construction - their control
is the Land Rover pattern, not the sedan.

**How to gate it**: assert the pseudovector per animation class against the control, on every
LOD that carries an active binding, plus `anim_source` case-insensitive, bone binding, and a
non-degenerate `axis_dir`. Two fixtures, and getting them the right way round is the whole
point:

- **negative (must FAIL)**: invert the axis **or** the angle, one at a time. That is a real
  direction defect.
- **positive (must PASS)**: invert **both** at once. Same rotation, different parametrization -
  a gate that rejects it is over-fitted to one authoring convention and will reject a correct
  mod.

Checking only "the axis is not null" is not a direction check at all:
`rip_native_door_contract_gate.py:665-674` does exactly that, so it would accept a
backwards-hinging door. Translation animations (`anim_type=4`, dampers) need the same treatment
with `unit(axis_dir) * (offset1 - offset0)`.

Origin: SUB_BRZ 2026-07-28, R21 dual on the "complete the car" roadmap. The measurement turned
the wheel-direction question from "spend an in-game cycle to discover it" into "already proven
offline, in-game only confirms" - which is the difference between one cycle and two.
---

> REDIRECT CAMBIO-1: SP-122 ocupa ahora el sitio del invariante #24 que corrige.

## In-vehicle actions need TWO registrations, and a proxied part is your placement oracle (SP-123, added 2026-07-28)

### An action offered to a SEATED occupant must be registered in two places

Measured on LFHeli OH-1, which spent a build cycle on "the close-door action does not appear
when seated" with the action class already correct.

1. The action must opt in: `ActionBase.InitConditionMask` only sets `ACM_IN_VEHICLE` when
   `CanBeUsedInVehicle()` returns true (`actionbase.c:113`), and the base returns false
   (`actionbase.c:335`). Any world action inherited from `ActionInteractBase` is therefore
   MASKED OUT the moment the player boards.
2. A seated player has no cursor target on the vehicle carrying them, so the target contract
   is `CCTNone` plus `HasTarget()` false - the shape vanilla uses in `actioncardoors.c:20-27`.
3. **Both registrations are required, and the second one is the one people miss:**
   - `ActionConstructor.RegisterActions` - builds the instance into the global pool.
   - `PlayerBase.SetActions(out TInputActionMap)` - `AddAction(MyAction, InputActionMap)`.
     Vanilla puts `ActionOpenCarDoors`/`ActionCloseCarDoors` right there
     (`playerbase.c:1669-1670`).
   Registering only in the constructor builds an action the manager never offers, because
   `FindContextualUserActions` walks the player's `InputActionMap` per input, not the pool.

Vanilla splits inside/outside into separate classes (`ActionCloseCarDoors` vs
`ActionCloseCarDoorsOutside`); copy that split rather than trying to make one class serve both.

**Ship the opening half too.** If entry/exit is gated on the door being open, an inside-only
CLOSE action traps the occupant. Pair it with an inside OPEN action, and keep one exemption in
the gate: a door that is NOT MOUNTED must leave the seat escapable, because no action can open
what is not there.

### A proxied part is the first correctly-placed reference on the host - use it as an oracle

When a host renders wrong, there is usually nothing trustworthy to measure it against. Parts
drawn through attachment proxies are placed by the engine from the entity transform, so they
ARE trustworthy, and the disagreement localises the fault:

- proxies agree with each other and disagree with the host -> **the host is the broken one**.
  Do not "correct" the proxy anchors to match: you would deform the correct piece, and the
  error changes with the host's state.
- On LFHeli OH-1 the doors, both rotors and the interior all followed the aircraft into the
  air while the fuselage stayed at ground level. The doors had just been migrated to proxies,
  and became the reference that finally localised a render bug open since 2026-07-20.

Corollary: `scene_raycast` in `rvproxy` mode returns the GEOMETRY LOD, not the visual mesh, so
it cannot adjudicate a visual misalignment. On a coarse collision hull it reports a surface
tens of centimetres inside the visible skin. Use it for collision questions only.

## (added 2026-08-01) A shared vehicle-core source turns "deploy ordering" gates into fiction

When one Enforce core file serves several vehicle lines (LFHeliCore's `LFHeli_Base.c` serves
OH-1 and HH-60G), any patch in it — even gated by `ConfigIsExisting("vehicleProp")` so only one
line executes it — DEPLOYS whenever ANY line rebuilds the core PBO. A sequencing rule like "do
not deploy the core patch until the model ships its matching memory points" does not survive
the sibling line's next rebuild. Case: LFHeli 2026-08-01 — the OH-1 line rebuilt and deployed
the shared core for its own fixes, and the HH-60G get-in patch went live with it, pointing at
ten `lfheli_con_*` memory points the deployed model does not emit (verified by scanning the
deployed PBO bytes for the patch symbols, not by mtime).

1. A core-side patch that requires a model-side contract (memory points, selections, bones)
   must be RUNTIME-TOLERANT: `MemoryPointExists` fallback to the previous mapping, so the
   patch stays inert until the model actually ships the contract. Deploy-order gates across a
   shared source are not enforceable by anyone.
2. Alternatively, land model and core in the same session/build — never leave a
   contract-dependent patch sitting in shared source "waiting" for its model.
3. When auditing what is live, verify the deployed PBO CONTENT (byte scan for the patch's
   symbols). The sibling line's handoff tells you the core changed; only the bytes tell you
   what rode along.


## Phantom vehicle command blocks ALL vanilla get-in after a client crash while seated (added 2026-08-02)

Symptom: the get-in prompt SHOWS but accepting does nothing - both seats, zero RPT/script-log
trace, and it survives rebuilds because nothing in the mod is broken. Mechanism:
'ActionGetInTransport.ActionCondition' runs on BOTH sides; the CLIENT player (clean) shows the
prompt, but the SERVER-side player still carries a non-null 'GetCommand_Vehicle()' restored
from player storage after a client crash while seated. The first server gate
(actiongetintransport.c:45-48) rejects silently, and a null 'StartCommand_Vehicle' in Start()
(actiongetintransport.c:91-92) produces no log either.

Checklist BEFORE suspecting model/proxies/config for a get-in regression:
1. Check the previous run's client profiles for a 'crash_*.log' - a crash while seated is the
   phantom's birth certificate.
2. With dayz-mcp available: 'query_get_in_condition' returning 'first_block=already_in_vehicle'
   with the player standing in the open = phantom confirmed; 'vehicle_get_in_client' (owner-side
   direct, skips the action gates) seating fine = seat contract and model are healthy.
3. The phantom clears on a clean logout cycle. "It fixed itself next session" is the signature
   of THIS bug, not of a flaky model.

Origin: LFHeli OH-1 gate D 2026-08-02 (GD-1): a full regression gate was misattributed to a
model surgery whose Geometry/ViewGeo/FireGeo/Memory LODs were byte-identical pre/post.

## ViewPilot (1100) of a shell+proxy car MUST carry the body geometry, not only proxy tris (SP-189, added 2026-08-06, SUB_BRZ B-3)

Symptom: on entering the vehicle in FIRST person the body goes invisible for
seconds (vanilla never does). Measured root cause: the shell's 1100 LOD held 7
faces = only the proxy triangles (interior/doors/wheels), zero own geometry,
while the vanilla control (civiliansedan MLOD) carries 11,977 REAL faces there
(interior + body + glass) plus its 13 proxies. The engine switches the shell to
the 1100 on mount; with nothing but proxy anchors in it, the body vanishes
until proxies resolve. The generator's "subset lives in the interior file"
design never materialized as a subset (brz_int 1100 = its full visual LOD).

Fix pattern (fix_b3_viewpilot.py, s45): merge the shell LOD0 into the 1100 —
own geometry with remapped point/normal indices, named selections via
get-or-create (camo/light_* keep working in 1PP), plus the LOD0-only chunk
proxies copied VERBATIM (points+face+selection; add_proxy would lose the
frame). Exclude faces AND anchor points of proxies the 1100 already has.
Gates that must pass: original proxy sels intact (1 face/3 pts), proxy set ==
originals + copied, bone companions cardinality unchanged, facenormals <=
32768, resolved-verts printed vs the ~16k design budget. Binarize preserved
the merge exactly (22,849 faces / 11 proxies in the ODOL).

Applies to every car built by this pipeline (MercedesAMGLF has the same
proxy-only 1100 — same latent defect). Day-1 check for car #2: census the
shell 1100 vs civiliansedan BEFORE first in-game (b3_viewpilot_census.py).

## A winding gate must measure the WHOLE piece, ALL render LODs, and twin pairs (SP-190, added 2026-08-06, SUB_BRZ B-1)

Three blind spots, each one bit us in the same door:

1. **Whole piece, not the touched subset.** The U-2 fix flipped only
   `brz_paint` and its gate measured only paint (97.9-99.5% green) while
   `brz_black` (4,460/door) and `brz_mirror` (315/door) stayed inverted. A
   winding gate censuses EVERY material of the piece (b1_door_census.py
   pattern: per-material concord/discord vs stored normals).
2. **All render LODs, including 1100.** The 1100 is a copy of LOD1: fixing
   LOD1 and skipping 1100 leaves first-person still broken (measured: 4,341
   paint flips pending in driver door, almost all in its 1100).
3. **Twin (double-sided) groups have three states.** Healthy pair = BOTH faces
   concordant with their OWN stored normals (each side owns its normals). A
   group where ALL faces are discordant is a pair inverted WHOLESALE by an
   earlier global flip -> flip ALL its faces (preserves opposite parity).
   Mixed group -> skip + WARN (not adjudicable offline). A blanket twin-skip
   leaves all-discord pairs broken and the census that skips twins reports
   green (measured: codriver brz_cab_plastic pair all-discord in LOD1/2/1100).

Post-fix census that re-runs the SAME predicate as the fix is tautological for
the oracle (it can only fail if reverse() did not mutate). Make it
non-tautological at the mechanism level: contrast flipped-per-material counts
against an INDEPENDENT pre-fix census prediction; the oracle itself (stored
normals sane) is only adjudicated in-game.

## Game winding is the INVERSE of MLOD geometric winding; fix winding per CONNECTED COMPONENT, never per face (SP-191, added 2026-08-07, SUB_BRZ D-1; refines SP-190)

Measured twice in-game with a positive control: a face renders in game when
its MLOD geometric winding looks into the BLOCKED side of its shell (the
pipeline transform is a reflection, LL-236; the rasterizer sees mirrored
winding, while stored normals pass through UNCHANGED for lighting). The body
works because its rip normals came out mirrored too and the F5 builder aligned
winding to them - an accidental double compensation. Any part built by a
different path (the doors came from the s42 cut) breaks the compensation and
no per-material / per-stored-normal / per-face flip converges: SUB_BRZ burned
FOUR in-game cycles (U-2 by material, B-1 by stored-normal concordance, C-1
per-face BVH, D-1 per component) before the method below closed it.

The method that converges (tools in VehicleImport\work\s43_fixes\, reusable):
1. `c1_export_meshes_json.py` + `c1_bvh_classify.py` (Blender BVH
   self-occlusion): per face, ray both ways from the centroid against the
   piece's own mesh -> open / blocked / rim / enclosed. A face is RIGHT when
   it looks into the blocked side. Validate the classifier on an
   in-game-correct piece FIRST (positive control).
2. `d1_comp_census.py`: union-find components by shared edges, vote per
   component over ADJUDICATED faces only (open+blocked; rim/enclosed carry no
   signal). A healthy mesh is bimodal (skins ~1.00 vs ~0.00). If a big
   component mixes both, STOP - per-component flipping would swap a good skin.
3. Flip whole components >=60% open (reverse + negate normals via NEW pool
   copies, never in place); leave <=40%; micro-components (<8 adjudicated)
   with 50/50 reads are left untouched; any REAL ambiguity aborts before save.
4. Verdict->p3d integrity asserts (face counts, index ranges) - a stale
   verdict silently flips foreign faces (this bit us).
5. Convergence gate: re-export, re-classify, re-census -> flip candidates
   must be ZERO on every render LOD.

Concave sub-objects (mirror housings) defeat ray classification: restore them
to their last in-game-good state and ASSERT the reverted count against the
recorded count of the pass that broke them (664/666 here).

Bonus lesson (D-2): a grey band over the windshield in 1PP was the interior's
sun-visor edge seen because the seated camera rides high - legitimate
geometry. Adjudicate WHAT the camera sees with a ray fan (d2_band_probe.py)
BEFORE cutting anything; the fix was posture (crew proxy -5mm), not trimming.


## HUD reticle/marker: anchor the ray at the CAMERA, never at the vehicle (SP-189, added 2026-08-07, LFHeli B-4)

A direction reticle drawn by projecting vehicle_origin + GetDirection()*D reads laterally skewed
against the airframe from any 3PP camera sitting off the symmetry plane: at D=300 the world point
projects ~0.2 deg off the vanishing point while the nearby nose projects ~7 deg off (parallax) -
the reticle appears left/right of the hull even though the world point is exactly on axis.
Camera-anchored is the flight-director pattern and kills the parallax for every camera (3PP
orbited, 1PP): nose = GetGame().GetCurrentCameraPosition() + veh.GetDirection() * D, then
GetGame().GetScreenPos(nose), keep the projZ>0 gate. Verified in-game fix path (LFHeli
LFHeliHUD.c 2026-08-07); the previous bone-anchored origin was a no-op built on a misattributed
probe (see next paragraph).

Two measurement traps that produced that dead fix, worth one line each:
- A stable camMS reading across two boots is NOT proof of a systematic engine offset when the
  probe is a one-shot: it can be the fingerprint of WHEN the one-shot fires (same approach walk,
  same inherited camera yaw). Adjudicate camera geometry from the vanilla camera code
  (DayZPlayerCamera3rdPersonVehicle pivots at vehicle origin + GetTransportCameraOffset, default
  0 1.3 0) before hypothesizing an offset.
- Selection membership can be PHANTOM: points in a named selection with zero faces referencing
  them (LFHeli glass carried 357 such points on one side). Any per-side point count over a
  selection must count only face-referenced points or the asymmetry measurement lies.


## Parent-driven selections (hiddenSelections / config anims) do NOT reach a PROXY - host them in the SHELL (SP-192, added 2026-08-07, SUB_BRZ + LFVehicleUI)

Any named selection the CAR's config must drive - hiddenSelections swaps
(SetObjectTexture/SetObjectMaterial), model.cfg Animations declared on the parent,
sections[] entries - must live in the PARENT model, never only inside a proxy sub-p3d.
Evidence, both measured on SUB_BRZ: (a) dashboard needle anims declared over the interior
proxy = needles STATIC in-game (s45 falsification); (b) the selections that DO work
(light_dashboard idx 8; screen_nav idx 9 for the nav screen) are faces hosted in the shell
- light_dashboard ships duplicated shell+proxy with identical coords and works FROM the
shell copy. MercedesAMGLF carries the same latent defect (interior selections in proxy).

Rules for a proxy-split car (day-1 for car #2, surgery for cars in flight):
1. Every hiddenSelections entry needs its faces in the SHELL, in LOD0 AND the ViewPilot
   1100 (SP-189: 1100 mirrors LOD0 content).
2. MOVE the faces out of the proxy instead of duplicating when the selection can carry a
   DIFFERENT material than the base (a swap on the shell copy z-fights the proxy copy).
   A duplicate is only tolerable while both copies always share the same material - the
   light_dashboard duplicate is a latent z-fight for the dashboard-light swap.
3. Copy vertex order and stored normals VERBATIM when moving (SP-190/191): faces that
   render correctly from the proxy keep rendering correctly from the shell (empirical
   control: the instrument cluster).
4. Reference surgery with asserts (component pick by aspect+centre, per-LOD face deltas,
   selection cardinality, proxies/bones untouched):
   VehicleImport/work/lfvui_f2/surgery_screen_nav.py.


## Diagnose before re-authoring, and validate every visual metric on an in-game-verified control (SP-193, added 2026-08-07, SUB_BRZ E-1/E-2)

SUB_BRZ was one session away from re-assembling both doors from the raw rip, on
the premise that the s42-cut mesh was rotten (five winding passes, 74.7% orphan
verts). Measured first: all six visual factory groups were ALREADY present face
for face in the shipped proxy - skin 2043, card 3344, handle 1176, speaker 18,
wing mirror 4721, mirror base 1174, every one at 100% centroid match <=1 mm. The
re-assembly would have reproduced identical geometry and fixed nothing.

Day-0 check before any re-import/re-assembly of a ripped part:

1. **Face-level completeness, matched by CENTROID** (invariant to vertex order
   and to winding, so it measures presence and never orientation). Point-level
   presence is not enough: a cut can keep every vertex and still drop faces.
2. **Gaps: exact point-to-triangle, never centroid-to-centroid.** The "missing"
   door jamb read 17.2 mm median by centroids and 0.7 mm by exact distance
   (p95 7.1 mm, max 16.2 mm, ZERO faces beyond 30 mm). It was not a hole; adding
   it would have z-fought skin that is already there. A large triangle's centroid
   sits far from a small one while the surfaces touch.

**Offline in-game visibility oracle** (this is what pays for itself - the same
question had cost five in-game cycles):

- A face is DRAWN when its MLOD normal points AWAY from the camera. This is
  SP-191's rule stated per-camera; calibrate it, do not assume it.
- Occlusion counts only DRAWN opaque triangles. A culled face cannot occlude, so
  a plain ray test overstates occlusion badly (mirror glass: 0/315 "visible" with
  raw rays, 238/315 once culling is applied to the occluders).
- **Every run re-validates on a piece confirmed visible in game** and declares
  itself VOID otherwise. Two metrics did exactly that in this session and were
  discarded rather than reported. A visual metric with no self-check is not
  evidence.
- **Judge a part only from cameras that can physically see it.** The mirror glass
  scores 0% from abeam and from the front three-quarter - correct, a rear-facing
  mirror is not visible from in front - and 75.6% from the rear three-quarter.
  A badly chosen camera condemns healthy geometry.
- To inspect a seam, raster the view with the culling rule and colour the PART
  apart from the BODY; both are the same material and one colour per material
  hides the very seam under inspection. Blender's viewport culling is a shading
  flag and has misled this project before - use the calibrated rule.

**A symmetric piece cannot vote on a sign or mirror fit.** Fitting the
blend->DayZ transform, the X-sign discrimination test scored 5.5% for BOTH signs
on a body panel and read as green while measuring nothing: the panel is
mirror-symmetric about x=0, so flipping X maps it onto itself. Report each
control's SELF-MIRROR score and make symmetric pieces ABSTAIN explicitly. Here
only the steering wheel could witness (23.6% vs 0.0%), and it settled that the
pipeline transform is a REFLECTION (det=-1), confirming SP-191/LL-236. Corollary:
never take a part's side from its NAME - adjudicate it against an asymmetric
piece whose in-game position is already measured.

**A flat placeholder _co reads in game as a MISSING part.** brz_mirror_co.paa is
a 16x16 DXT1, 307 bytes, whose AVGC and MAXC taggs are the SAME value
(RGB 38,40,44) - proof of a single near-black colour. The glass geometry,
material and winding were all healthy and it still read as "the mirror has no
glass". Check the PAA taggs (AVGC == MAXC means flat) before hypothesising
geometry; an unswatched piece is a texture bug wearing a geometry costume.

**A defect can survive N winding passes by never entering the adjudicated set.**
The mirror was 315/315 ENCLOSED in the BVH verdict - a category the fixer is told
to skip - and separately excluded from the component census by material. When a
defect outlives several passes, first check whether its faces are even in the set
those passes adjudicate; rim/enclosed are blind spots, not clean bills of health.

Toolkit, parametrised and reusable: `VehicleImport\work\s47_doors\` - p12 face
completeness, p18 exact surface gap, p17/p20 self-validating visibility oracle,
p21 culling-correct seam raster, p7/p8 transform fit with abstention.

## An imported door has NO end caps, and a shut door cannot show you (SP-198, added 2026-08-07, SUB_BRZ E-1)

A ripped car door arrives as two open shells - outer skin and inner card - with
NOTHING closing the leading and trailing edges. The source game never shows that
edge, so it was never modelled. Every DayZ door OPENS, so every imported door
shows it. There are no 2D doors: assume the caps are missing until measured.

SUB_BRZ, both doors, measured at the two z extremes of the door-local frame:

| end | faces facing +/-z | cap area | expected (height x thickness) |
|---|---|---|---|
| leading | 125 | 25 cm2 | ~710 cm2 |
| trailing | 62 | 17 cm2 | ~710 cm2 |

3.5% and 2.4% of the area a real cap needs, and what remains is `brz_paint`
fold-over at the skin edge, not a band. Door thickness available at both ends:
77 mm.

**Day-0 check for any vehicle with opening doors** - slice the door at its two
extremes along its long axis, sum the area of faces whose geometric normal runs
along that axis, and compare against `height x thickness`. Under ~30% means the
caps are missing. `VehicleImport\work\s43_fixes\s49_probe_ends.py` is the probe.

**Why this hides for entire sessions, and the general lesson:** with the door
SHUT the body covers that edge, so every closed-door measurement passes. SUB_BRZ
spent five winding passes, a paint-normals fix and a black-normals fix, plus an
offline visibility oracle over 20 cameras, a jamb gap measured point-to-triangle
and a culling-correct seam raster - all on the shut door, all green, while the
defect sat in the open-door configuration nobody measured. Generalise it:
**measure a part in the state where it is EXPOSED, not in its default state.**
A green metric on the hidden configuration is not evidence about the visible one.

Corollary for the in-game checklist: a door verdict is only worth collecting with
the door OPEN, and the screenshot must show it open. Two rounds of SUB_BRZ
captures were taken shut and settled nothing.

Corollary for the fix: the caps are new geometry, not a flip. Normals and winding
passes cannot create a surface that was never there - and if a door edge reads as
"nothing at all" rather than "wrong colour" or "wrong shading", suspect absence
before orientation.


## Cirugia de caras en un .p3d: un criterio por UN eje parte los quads que cruzan ese eje (SP-197, added 2026-08-07, LFHeli V1)

Al borrar caras de una seleccion por lado ("quita el cristal duplicado de babor"), el criterio
natural es clasificar cada CARA por el signo de su centroide en X. Es correcto para caras que viven
enteras a un lado y **silenciosamente destructivo** para cualquier superficie que CRUCE el eje: un
panel plano suele ser un quad de 2 triangulos, y si el quad cruza X=0, el centroide de un triangulo
cae a un lado y el del otro al otro. El criterio se lleva la mitad del panel y deja medio cuadrilatero.

Firma visual exacta que reporto el usuario: "se ven medio a triangulos medio a huecos triangulares".
Medido despues (LFHeli 2026-08-07): 9 paneles del canopy con 2 caras cada uno; en el fichero
desplegado quedaba 1 de cada pareja. El conteo de ISLAS no lo delata (seguian siendo 17); solo el
conteo de CARAS por isla.

Reglas:

1. Antes de borrar por lado, comprueba si la seleccion tiene islas que CRUZAN el plano de simetria
   (min_x < 0 < max_x en la isla). Si las hay, el criterio por centroide de cara NO sirve: decide a
   nivel de ISLA, o excluye explicitamente las islas que cruzan.
2. Un criterio de UNA dimension captura todo lo que comparte esa dimension. La banda Z de las dos
   puertas del OH-1 (+-0,85 m alrededor de cada ancla) cubria z de -3,68 a -0,62, que es donde
   tambien vive el canopy. Anade la segunda dimension que discrimina (altura Y) o compara cara a cara
   contra el sub-p3d que replica esa geometria.
3. Gate que lo caza offline y que ningun conteo agregado sustituye: **cada isla conserva su numero de
   caras**, o si pierde, pierde 0 o TODAS. Una isla que pasa de 2 caras a 1 es la firma del quad
   partido. El area total tampoco lo delata si mides por conjunto unico de puntos.
4. Cuando el criterio geometrico sea dudoso, no lo adivines: **saca un visor y que el usuario
   seleccione**. Coste medido: ~40 min de visor autocontenido (Three.js UMD r147 + islas clicables +
   export de la lista) frente a un ciclo de vuelo perdido y una regresion visible en el modelo.
   Patron reutilizable en `LFHeli_dev/reviews/oh1-glass-picker-v2.html`: dos capas, lo DESPLEGADO
   (clic = borrar) y lo que YA SE BORRO (clic = restaurar), silueta del casco en wireframe (una malla
   de contexto solida oculta justo los paneles que se van a elegir), y el export como dos listas de
   IDs. Self-test obligatorio antes de entregar (DZ-R1): CDN 200, marcador en el DOM que solo se
   escribe al final del script, y screenshot headless LEIDO.

Corolario del mismo caso: **los puntos huerfanos de una seleccion (miembros de la seleccion sin
ninguna cara que los use) son EVIDENCIA, no basura.** Los 357 huerfanos a estribor del OH-1 eran el
rastro exacto de 619 caras que el pipeline habia perdido; un "saneamiento" los borra y con ellos la
unica pista de que faltaba algo. Mide y entiende antes de limpiar.


## Un canto de puerta ausente se mide por LONGITUD DE BORDE LIBRE contra el control vanilla, y tres fixes "obvios" no lo cierran (SP-202, added 2026-08-07, SUB_BRZ E-1; refina SP-198)

> ⚠ SUPERSEDIDO PARCIALMENTE por SP-245 (sección siguiente): el canto trasero SÍ falla, y el
> cierre por script SÍ funciona con fondo medido. La métrica y los 3 fixes descartados siguen
> vigentes.

SP-198 dice que una puerta importada no trae tapas de canto. Falta lo accionable: **con qué se mide
y qué no arregla**. Una sesion entera de sondas en SUB_BRZ, reproducible en cualquier coche del
pipeline con puertas desmontables.

**El control se saca en un comando** (no hace falta el coche entero):

```
python odol_to_mlod.py "DZ\vehicles\wheeled\civiliansedan\proxy\sedandoors_driver.p3d" ctrl.p3d
```

**La metrica correcta es longitud de borde libre por extremo del eje largo**, en una banda del 6%,
en TODOS los LODs render + el 1100. Medido:

| extremo | vanilla | SUB_BRZ | lectura |
|---|---|---|---|
| delantero (pilar A) | **0 mm** | 673 mm | defecto |
| trasero (pilar B) | 612 mm | 627 mm | **normal, no tocar** |

Dos cosas que esto corrige de golpe:

1. **Tener borde libre en el perimetro de una puerta es NORMAL.** El perimetro entero es un ciclo
   cerrado de ~4,4 m (piel exterior + cristal) y vanilla tambien lo tiene. Solo el borde DELANTERO
   es anomalo, porque es el unico que queda a la vista al abrir. Un gate que mida "borde libre
   total" da rojo en una puerta sana.
2. **El gate por area (`cap >= 70% de alto x espesor`) esta mal calibrado** y no debe usarse: asume
   espesor constante en toda la altura y que toda la altura es chapa. En una puerta frameless (BRZ,
   GT86, y cualquier coupe del rip) la mitad alta es cristal, y el "espesor" que reporta una sonda
   de banda es la CURVATURA del doblez, no un hueco. Ese gate pedia ~710 cm2 de tapa donde la
   geometria real admite ~640 y solo en parte de la altura.

**Tres fixes descartados CON MEDIDA — no repetirlos:**

- **Doble-carar la banda frontal**: render con la regla de culling calibrada del pipeline, antes y
  despues, **0 px de diferencia**. El see-through del canto no es un problema de caras de una sola
  cara.
- **Labio doblado (hem) copiando a vanilla**: un borde libre no se cierra desplazandolo; el labio
  mueve el borde, no lo elimina. Ademas la holgura contra la jamba no da: a 2 mm de profundidad ya
  hay vertices de carroceria dentro del volumen (gap puerta-jamba medido en 0,7 mm).
- **Bridge piel exterior <-> panel interior**: los dos bordes NO se corresponden. Solo 6 de 13
  franjas de altura tienen los dos bordes presentes, con huecos de 121 a 218 mm. Un bridge
  automatico produce una pared retorcida.

**La causa estructural, que es lo que hay que mirar en el coche siguiente:** la piel exterior y el
panel interior son **mallas separadas que no se tocan**. En SUB_BRZ el panel interior
(`brz_cab_plastic`, `brz_black`) muere 108 mm antes del borde delantero, donde la piel exterior
(`brz_paint`) si llega. Entre ambos no hay nada. Por eso no existen "dos anillos que puentear":
existen dos bordes de piezas distintas separados 11 cm.

**Consecuencia de planificacion:** cerrar el canto es **modelado a mano** (autorar la pared del
canto en Blender), no una cirugia por script. Presupuestalo como tal desde el principio y pide la
captura del defecto CON LA PUERTA ABIERTA antes de empezar — con la puerta cerrada toda medida da
verde (SP-198) y sin la captura no se distingue "veo a traves" de "el borde queda feo", que llevan
a fixes distintos.

Sondas reutilizables en `VehicleImport\work\s50_doorcaps\`: `s50_probe_freeedge.py` (la metrica del
gate, por LOD), `s50_compare_control.py` (control vs candidato, ejes normalizados),
`s50_probe_bridge.py` (correspondencia de los dos bordes), `s50_render_front.py` (render A/B/C:
actual con culling, sin culling, y el fix simulado).

## El canto de puerta SE CIERRA POR SCRIPT con una banda de fondo MEDIDO — y ambos cantos fallan (SP-245, added 2026-08-15, SUB_BRZ s52; supersede parcialmente SP-202)

Dos correcciones a SP-202, ambas con medida y la primera confirmada in-game por el usuario:

1. **El canto TRASERO también falla.** La adjudicación "vanilla tiene 612 mm libres ahí → normal,
   no tocar" era una inferencia mala: que vanilla tenga borde libre no implica que quede EXPUESTO.
   Con el usuario delante fallan los dos. Y medido a perímetro completo (banda z del 8%, no del
   6%): vanilla delantero **0 mm** / trasero ~502 mm; el rip 743/598 mm — el delta anómalo está en
   AMBOS extremos.
2. **"Cerrar el canto es modelado a mano" queda superseded**: una banda perimetral por script
   alcanza paridad vanilla. El fix de 5 mm de s51 fallaba por PROFUNDIDAD (5 mm en un hueco de
   ~77 mm), no por orientación — sus quads sí se dibujaban (probe cull ON == cull OFF).

**La receta que funciona** (`VehicleImport\work\s52_cantos\s52_close_perimeter.py`, ambas puertas,
LODs visuales + 1100):

- **Filo libre VERDADERO**: contar el uso de cada arista sobre TODAS las caras del LOD y quedarse
  con las de la piel con uso==1. Contar solo dentro del material de la piel (como s51) marca como
  "libres" aristas que en realidad cubre el cristal o el trim, y la banda las atraviesa.
- **Fondo medido por vértice de borde**: raycast hacia dentro por el eje del grosor; fondo = 90%
  del hueco hasta la primera pared, clamp [8, 60] mm; 60 mm donde no hay pared en 150 mm. El hueco
  real varía 10→135 mm — cualquier constante está mal en la mitad del perímetro.
- **Banda estanca**: UN punto extruido por vértice soldado del borde, compartido entre quads
  vecinos (extruir por-arista con fondos distintos deja rendijas).
- **Winding**: normal almacenada apuntando FUERA del filo, winding geométrico opuesto (la
  convención medida al 100% en los LODs render de ambas puertas). "Fuera del filo" = componente
  del (punto_medio − centroide de la piel) perpendicular a la arista, con el eje del grosor a 0.
- **Gates de paridad, siempre contra el control** en el MISMO metric: render de canto (BRZ pasó
  de 15,0% → 25,4% de superficie dibujada vs 26,8% vanilla) y barrido de rayos por el eje largo
  (65,7% de rayos limpios vs 68,8% vanilla — la puerta quedó MÁS cerrada que la control). Un
  umbral absoluto sin control falla puertas sanas: la vanilla da 68,8% de "abierto" en el barrido
  ingenuo porque la mayoría de los rayos pasan por fuera de la silueta legítimamente.
- **Diagnóstico previo que lo desbloqueó**: renderizar el canto en DOS escenas — coche MONTADO y
  CERRADO (¿regresión visible por fuera?) y puerta AISLADA (= puerta abierta, donde vive la
  queja). El defecto solo existe en la segunda; medir solo una responde a otra pregunta.

Pedir la captura del defecto CON LA PUERTA ABIERTA (SP-202) sigue vigente antes de dimensionar.

---

## Desmontables que NO son puertas: capo y maletero (medido sub_wrxsti_04, 2026-08-07)

**Nivel de evidencia: MEDIDO offline. La extension del rig NO esta implementada ni verificada
in-game a fecha de hoy.** Los numeros de abajo son geometria del modelo, no comportamiento del
motor; lo que aqui se promueve es DONDE mirar, no una receta probada.

Un rig de desmontables escrito para puertas hornea dos supuestos que son **falsos** para capo y
maletero, y ninguno de los dos canta: uno aborta con un mensaje que culpa al eje, y el otro ancla
la bisagra a un metro de donde va, en verde.

1. **El borde de bisagra no es siempre el delantero.** Una puerta bisagra en su borde delantero
   (-Z), y de ahi que los rigs banden sobre `z.min()`. Pero un **capo bisagra en su borde TRASERO**
   (el del parabrisas, +Z) y un **maletero en su borde DELANTERO** (-Z). Medido en el WRX: bisagra
   del capo a **12 mm** del maximo Z de su hoja, la del maletero a **4 mm** del minimo. El borde
   delantero del capo, que es donde bandaria un rig de puertas, esta a **1,16 m** de la bisagra
   real. El borde tiene que ser un dato declarado por rol, no una constante.

2. **La inclinacion se mide contra el eje de su CLASE, no siempre contra la vertical.** Capo y
   maletero dan **89,81 grados** y **88,84 grados** respecto de +Y: revientan cualquier presupuesto
   de verticalidad. Su eje es lateral (+X). Un gate de "tilt vs Y" no es un gate de calidad para
   ellos, es una prohibicion.

3. **Trampa de signo, y es silenciosa.** Con eje lateral `axis[1]` vale ~0, asi que la
   normalizacion habitual `if axis[1] < 0: axis = -axis` deja de ser determinista: el signo lo
   decide el ruido del PCA. La direccion de apertura tiene que venir del angulo declarado, y el
   gate offline que caza un signo invertido es **fisico**: el **borde libre** (la banda OPUESTA a
   la bisagra) debe SUBIR al abrir. Un gate de desplazamiento por magnitud (`|delta| > umbral`)
   pasa en verde con el signo invertido — mide que se mueve, no hacia donde.

4. **El gate del eje NO valida el conjunto de piezas del rol, y es facil creer que si.** El eje se
   ajusta sobre UNA pieza (la que declara la bisagra). Meter en el rol una pieza que no toca — una
   jamba, un panel de carroceria, un faro que en realidad va al paragolpes — no mueve el eje ni un
   grado: **el contraste de bisagra sigue en verde y el de apertura tambien**. Hace falta un gate
   aparte sobre la propiedad: distancia maxima de cualquier cara del rol al eje contra un radio
   declarado, mas el recuento de caras contra el censo. Sin el, la agrupacion mala llega al juego.

5. **Antes de escribir una regla de propiedad `+x`/`-x`, mide si hay caras EN el plano x=0.** Una
   regla por centroide las descarta por los dos lados y esas caras desaparecen del coche sin que
   nadie lo note. En el WRX salieron 0 de 18 piezas candidatas, pero eso es un dato medido, no una
   garantia del formato. Y para una pieza entera no hace falta regla especial si el selector cae a
   "todas" por defecto.

6. **Un capo suele traer cristal y un maletero no.** Si el codigo estructural exige cuerpo Y
   cristal para acotar sus cajas, el maletero aborta y el capo pasa — pero clasificando el cristal
   de los faros como "ventana", con su zona de dano y su material de penetracion de vidrio encima.
   La caja de cristal tiene que ser opcional, y la clasificacion cuerpo/cristal un dato, no un
   prefijo de nombre.

7. **La masa del item no se hereda de la puerta.** Un `geometry_mass_kg` global le pone a un capo
   los kilos de una puerta.

Origen: `VehicleImport\plans\2026-08-07-T6-detachables-rig-extension.md` (T6 del piloto CAMBIO-3),
sondas en el scratchpad de la sesion. Los puntos 3 y 4 los levanto una revision R22 ciega sobre el
plan, no la implementacion: son exactamente la clase de defecto que un gate offline no encuentra
porque el gate estaba midiendo otra cosa.


## Borrar caras de un .p3d con py3d: muta `lod.faces` IN PLACE o rompes las selecciones en silencio (SP-203, added 2026-08-07, SUB_BRZ parabrisas; extiende SP-197)

SP-197 cubre QUE caras elegir. Esto es COMO quitarlas sin corromper el modelo, y es el paso donde
un borrado correcto se convierte en un `.p3d` roto.

**El mecanismo, leido del fuente antes de escribir un byte** (`py3d/__init__.py`, clase
`Selection`): `Selection.all_faces` **es una REFERENCIA a la lista `lod.faces`**, no una copia; y
`Selection.write()` valida sus claves **por identidad** contra esa lista y lanza `RuntimeError` si
alguna es "foreign". Consecuencias:

- `lod.faces = [f for f in lod.faces if ...]` crea una lista NUEVA. Toda `Selection` sigue
  bindeada a la vieja. En el mejor caso peta; en el peor, pesos serializados a cero en silencio.
- La forma correcta es mutar **in place** y de indice mayor a menor: `for i in reversed(cut): del
  lod.faces[i]`.
- Antes de eso hay que **sacar esas caras de cada `Selection.faces`** (son dicts con la Face como
  clave), o `write()` aborta por clave foranea.

**Gate obligatorio, y es barato**: re-leer el archivo tras guardar y comprobar el conteo de CADA
seleccion nombrada. Esperado = conteo anterior menos las retiradas de esa seleccion. Medido en el
caso real: `glass` 6022→5910 (−112), `interior` 4458→4383 (−75), `trim` 4072 intacta, con 187
caras borradas. Si una seleccion no cuadra, el borrado se comio algo que no debia.

**Antes de borrar, pregunta a que selecciones pertenecen las caras condenadas.** No es lo mismo
tocar una seleccion decorativa que `glass`, que gobierna la rotura del cristal. Un 2% de una
seleccion es asumible; el 90% la convierte en otra cosa.

**Los puntos huerfanos se dejan.** Borrar los puntos que ya no usa ninguna cara obliga a reindexar
todo el LOD, y este proyecto ya aprendio que los huerfanos son EVIDENCIA, no basura (LFHeli).

**Comprueba cuantos LODs tiene la pieza ANTES de dar el borrado por hecho.** El fix del forro del
techo (s43) hubo que aplicarlo en el LOD visual Y en el ViewPilot 1100, o reaparecia en primera
persona. En el caso de este parabrisas el chunk tenia UN SOLO LOD y no aplicaba — pero eso se
comprueba, no se supone.

### Corolario para el gate de PBO entre builds (refina SP-194)

Al verificar que un build solo cambio lo que debia:

1. **Una clave "order-free" NO puede contener indices de seccion.** Reimplementarla con
   `face_index_start` / `face_index_end` da un gate que declara DISTINTOS 7 de 10 modelos que no
   se tocaron, porque esos indices son exactamente lo que AddonBuilder reordena. La clave valida
   es el multiset de `(material, textura, indices de vertice de la cara, bit de iluminacion)`
   resuelto por las tablas de NOMBRES, con guard VOID si las secciones no cubren todas las caras.
2. **Anadir una textura nueva cambia `texHeaders.bin`** — es el indice de texturas del PBO. Es
   mecanico y esperado; si no esta en la lista de deltas admitidos, el gate da un rojo falso.
3. Separa el delta por tipo de entrada: `.p3d` se compara **semanticamente**, todo lo demas por
   **bytes**. Un gate que parsea toda entrada cambiada como ODOL revienta en cuanto el lote
   incluye una textura.

## DOOR MECHANISM SELECTOR — decide this BEFORE modelling or scripting anything (added 2026-07-27)

DayZ has **three unrelated door mechanisms**. Picking the wrong one costs a full modelling +
config cycle, and they share vocabulary (`source`, `component`, `axis`), so the mistake is not
obvious from the symptom. Doors have now been re-solved from scratch on three projects
(MercedesAMGLF, SUB_BRZ, LFHeli) — pick from this table first.

| You are building | Mechanism | Where the contract lives |
|---|---|---|
| Door/hatch/lid on a **building or static prop** | `class Doors` under `HouseNoDestruct`; animation `source` maps to a Doors `component` | skill **`dayz-doors`** |
| Door on a **vanilla-style car**, as a detachable part | Attachment: `CarDoor` item + `ActionCarDoorsOutside`; the action target is resolved by **raycast against the ITEM's ViewGeometry** | invariants **#21 and #22** below |
| Door that must **stay part of the shell** (no detach, custom radial) | Own actions driving `GetNearestDoorIndex` / `IsDoorOpen` (fail-closed) / `SetDoorOpen`, with the motion in `model.cfg` AnimationSources | LFHeli OH-1 contract v5 |

**`dayz-doors` does NOT cover vehicle doors.** Its scope is buildings and static props. The name
attracts anyone with a door problem; if the door belongs to a car or a helicopter, that skill is
the wrong contract and its `class Doors` pattern will not produce a working radial.

Two traps specific to the vehicle paths:

- **Attachment path**: the radial silently never appears if the item's ViewGeometry points carry
  `flags 0x0` instead of `0x02000000` — config, script overrides, slots, bones and anim sources
  all correct, action still filtered. Census the item's VG point flags against a working control
  BEFORE touching config. Full contract in #22.
- **Scripted path**: enumeration probes must be READ-ONLY. A diagnostic probe that calls
  `SetAnimationPhase` to "look at" a door corrupts live state — the door closes visually while the
  logical state stays open, and the next diagnosis is chasing a bug the probe created.

Status honesty: #21 and #22 are measured offline and their in-game gate was still pending as of
2026-07-18; the OH-1 scripted contract v5 is implemented with its cycle gate pending. Treat all
three as verified-offline, and confirm in-game on first use.

## GET-IN DOESN'T APPEAR — name the guard BEFORE touching the model (SP-141, added 2026-07-29)

Four vehicles in this vault have burned iterations on "the get-in prompt does not appear"
(LFQuad, MercedesAMGLF, LFHeli OH-1 R3, LFHeli HH-60G). The prompt is gated by **five ordered
guards** inside one function, and a *necessary* chain is not a *measured* cause: knowing the
prompt must pass through `CanReachSeatFromDoors` says nothing about which guard is firing.
Name the guard first; the fix follows in minutes.

`ActionGetInTransport.ActionCondition` (`actiongetintransport.c:50-79`) has **exactly one path
to `true`**, and rejects in this order:

1. `CrewPositionIndex(componentIndex) < 0` — the ViewGeometry component under the cursor is not
   dual-tagged `componentNN`, or its selection is not the seat's `actionSel` (preflight #4).
2. `CrewMember(crew_index)` non-null — seat occupied.
3. `!CrewCanGetThrough(crew_index)` — door state / seat-fold gate. ★ Base
   `OffroadHatchback.CrewCanGetThrough` covers only posIdx 0..3 and then **`return false`**
   (`offroadhatchback.c:212-250`), so ANY vehicle with more than four seats must override it or
   seats 4+ are dead. A `true` on posIdx >= 4 is proof your override is running.
4. `!IsAreaAtDoorFree(crew_index)` — engine-side door area.
5. `!CanReachSeatFromDoors(selection, player.GetPosition(), 1.0)` — and this one has three
   sub-conditions, all silent (`carscript.c:2708-2731`):
   - `GetDoorConditionPointFromSelection(sel)` must return a non-empty name. ★ **The trap**:
     base `CarScript` knows only FOUR cases, all lowercase — `seat_driver`, `seat_codriver`,
     `seat_cargo1`, `seat_cargo2` (`carscript.c:2673-2692`) — and `OffroadHatchback` the same
     six lowercase ones (`offroadhatchback.c:351-365`). Any other seat selection name returns
     `""` and the seat can NEVER be boarded, with config, bones, proxies and componentNN all
     correct. A custom seat set REQUIRES overriding this method.
   - `MemoryPointExists(conPointName)` — the point must be in the **Memory LOD** of the
     shipped model.
   - distance **IN PLAN** (height is zeroed) `<= pDistance`, and the action passes **1.0 m**.
     Vanilla places its condition points ~0.26 m OUTSIDE the hull at the door station
     (measured on `offroadhatchback` MLOD: `seat_con_1_1` x=1.1586 against a half-width of
     0.900) and REUSES two points for four seats. On a long fuselage two points cannot cover
     ten seats.

**The instrument** (DayZ-MCP): `query_get_in_condition` with a `component` index returns
`first_block` = exactly one of `componentNN` / `occupied` / `crew_can_get_through` /
`area_blocked` / `unreachable` / `""`, plus per-seat `crew_can_get_through`, `area_free`,
`occupied`, `reachable` — the `reachable` loop being the same `GetActionComponentNameList` ->
`CanReachSeatFromDoors` the action runs. **That names the guard in one call, offline of the
user's eye.** Pass `component=-1` for the whole crew bank (note: `reachable` is hardcoded false
in that mode — only the per-component call measures it).

Measured case, HH-60G 2026-07-29: all ten seats `first_block="unreachable"` with guards 1-4
GREEN on all ten, so the block is guard 5 alone — and that killed two plausible sub-causes at
once, because neither camelCase nor radius can explain a lowercase seat whose point was 1 mm
from the player.

★ **Discipline that this cost**: a plan that declared "measured mechanism" on the strength of
the chain being necessary was rejected by review for exactly that. Measure `first_block` per
seat BEFORE editing the model, the config or the script.

## UV step of any vehicle import: `SAT=0` is the only proof of no-overlap (SP-214, added 2026-07-16)

**[MEASURED]** The validated UV path for hard-surface vehicles is charts by a 100°
normal cone + SLIM + a **single** anti-fold guard round + SAT finisher + semantic
shelf pack. Measured: a 10.5k-tri retopo produced 43 islands at **SAT=0**; a
36.9k-tri rip produced 63 islands at **SAT=0**.

Three rules, each of which cost a measurement to learn:

- **Declare "no overlap" only on an exact `SAT=0`.** The Monte-Carlo estimator has
  a floor around 0.06-0.15%, so a `0%` from it is not evidence.
- **Never iterate the anti-fold guard.** It cascades 32 islands into 84, measured.
- Break the stretch/overlap/legibility trilemma by **relaxing the deformation
  corner**, not by fragmenting: the real bar tolerates moderate stretch and does
  not tolerate fragmentation.

`PartUV` was piloted and **rejected as the default route**: 162 of 232 islands on
the same meshes. Applies to any vehicle import, source-game or not; the implementation
lives in the `uv-clean-atlas` skill, which this pack does not ship. Cross-ref:
`rip-vehicle-import`, same step after geometry.

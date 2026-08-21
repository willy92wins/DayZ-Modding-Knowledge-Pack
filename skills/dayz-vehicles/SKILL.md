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
2. Si el asset es un coche source-game Grub nuevo, proxy-split y con partes móviles, usa **familia B**.
3. Familia B → abre `../rip-vehicle-import/SKILL.md` y sigue únicamente su adaptador, golden y allowlist.
4. Ese adaptador abre el `asset-contract.json` del asset como tercer y último fichero day-0; schema, export Blender y primitive son inputs de máquina, no documentos adicionales que el agente mantenga.
5. Si ya existe un plan/runbook congelado para el asset, sigue ese contrato en vuelo; no lo migres aquí.
6. Si ninguna fila aplica o falta el adaptador de la familia: **STOP**. No improvises desde este atlas.

| Señal de entrada | Adaptador | Ficheros day-0 |
|---|---|---|
| source-game Grub, coche nuevo, proxy-split + puertas/partes móviles | Familia B | Este router → `../rip-vehicle-import/SKILL.md` → `<asset>\asset-contract.json` |
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

**Cockpit screen → live engine map (RTTextureWidget bridge) (invariant, added 2026-08-19, SUB_BRZ RT spike):**
Any hiddenSelections screen can display the ENGINE's map renderer (what LBmaster's GPS uses) instead
of baked tiles: create the RT via `CreateWidget(RTTextureWidgetTypeID, …)` (children render INTO its
texture, `enwidgets.c:28` — they never paint to the viewport, so no HUD witness), hang a `MapWidget`
under it with `CreateWidgets(layout, rt)`, then hook the entity **in this exact order**:
`SetObjectMaterial(idx, "Mod\data\x.rvmat")` FIRST (no leading backslash), `SetObjectTexture(idx,
"$rendertarget")` second, `proto native void SetGUIWidget(IEntity, int idx, RTTextureWidget)`
(`enwidgets.c:637`) LAST. A later SetObjectMaterial rebinds the base texture slot and silently undoes
the hook — a uniform light-grey screen means `$rendertarget` resolved to the white fallback texture.
Zero call-sites exist on disk for SetGUIWidget/RTTextureWidget; verified in-game on 1.29 diag.
MapWidget `GetScale()` defaults to 0.85; at 0.05–0.6 it draws line-work only (contours + roads, no
urban/forest fill) — pick the zoom with the user's eye gate. If the hooked vehicle leaves the client
streaming bubble its `GetPosition()` reads `<0,0,0>` and the map recenters to the map corner:
production code must re-resolve the vehicle every tick, never cache the entity reference. MCP test
flow that actually seats and starts: `vehicle_get_in_client` (ownership get-in; `vehicle_enter`
answers seated:1 without sticking) → `engine_set`. Recipe, captures and gotchas:
`LFVehicleUI_dev\HANDOFF.md` snapshot 2026-08-19.
**Closed 2026-08-19b — RT unusable for a live GPS:** the RT freezes the FIRST composed frame
(later `SetScale`/`SetMapPos`/vehicle movement never recompose it), and a MapWidget child only ever
contributes the vector layers (roads + contours) — the raster fill (land, forest, buildings) never
reaches the RT, even with a 24 s warm-up between widget creation and the entity hook. The bridge
recipe above remains valid for STATIC screen content only. Live vehicle GPS goes through baked
tiles on hiddenSelections instead (next invariant).

**Vehicle screen tiles: terrain satmap, not navigation usermap — and apply server-side (invariant, added 2026-08-19, SUB_BRZ Plan B):**
Two tile sources share the same `s_XXX_YYY_lco.paa` naming and the same 32×32 grid of 480 m tiles
on chernarusplus, but look completely different: `dz\gear\navigation\data\usermap\` is the PAPER
map art (light background, red roads, contour lines — what the ItemMap shows), while
`dz\worlds\chernarusplus\data\layers\` is the colored aerial satmap (the real "GPS look").
A GPS screen wants the layers path; world name must be parameterized per terrain. Second half of
the invariant: `SetObjectTexture`/`SetObjectMaterial` called ONLY client-side is silently reverted
to the config `hiddenSelectionsTextures[]` whenever the server pushes a visual-state resync —
observed reproducibly on GEAR CHANGE. **Applying on the dedicated server does NOT fix it
(refuted in-game 2026-08-19 afternoon): scripted SetObject* state does not replicate
server→client.** The working pattern is the skin-mod one: re-assert the full scripted visual
state client-side on EVERY `OnVariablesSynchronized` (no packed==applied early-out; gate only
the diagnostics). Also force-hide every bank window on the first apply
(`SetAnimationPhaseNow(name, 1.0)` loop): windows spawn with the config-default texture and
their initial hide phase is not guaranteed applied. The force-hide only exists at runtime if
the hide animations actually BAKED — see the skeletonBones invariant below. Satmap-in-bank
verified in-game 2026-08-19 (SUB_BRZ, 1.29 diag, human driver gate).

**Seated-view geometry lives in the View Pilot LOD (invariant, added 2026-08-19, SUB_BRZ v1.2):**
A car with a View Pilot LOD (resolution 1100) renders THAT copy of the geometry for seated
occupants, not LOD0. Any geometry/UV/selection patch that must be visible from the driver seat
(screen UV remaps, marker quads, interior fixes) has to be applied to BOTH res 0 and res 1100 —
patching only LOD0 looks fine from outside and unchanged from the seat, which reads as "the fix
did nothing". Also from the same session: a tiny 8×8 DXT PAA is invalid (mip chain below 4 px →
engine renders the grey fallback); for flat-color config slots use a procedural
`#(argb,8,8,3)color(r,g,b,1,CO)` instead of a file.

**Animations only bake for selections that are skeletonBones (invariant, added 2026-08-19, SUB_BRZ grey-screen root cause):**
AddonBuilder silently DROPS every model.cfg animation whose `selection` is not declared in the
model's `CfgSkeletons` `skeletonBones[]`: the build exits 0, the anim classes stay in the source
model.cfg, the AnimationSources stay in config.cpp, and `SetAnimationPhaseNow` on their sources
becomes a silent no-op. Measured differential (SUB_BRZ): `gps_marker` was a bone → its 4 anims
baked into the ODOL; the 28 `nav_w*` windows were in CfgModels `sections[]` but NOT bones → all
28 `type=hide` anims dropped, so the untextured bank could never be hidden and rendered as an
opaque grey panel 0.5–1.85 mm in front of the real screen — a grey that reads as "my texture
apply fails" while the apply is actually landing fine behind it. Two rules: (1) every animated
selection — hide anims included — must be listed in skeletonBones[]; being in `sections[]` is
NOT enough. (2) Verify the bake OFFLINE before deploying: extract the PBO and string-scan the
binarized .p3d for the animation SOURCE names, which are plaintext in the ODOL (e.g.
`re.findall(rb'nav_w\d\d_h', odol)` must yield all 28 distinct names). Zero hits = the animation
does not exist at runtime, whatever model.cfg says. Debugging corollary: the engine grey
fallback is per-SECTION (`texture_index=-1`); when a screen shows uniform grey, check for
coplanar untextured geometry IN FRONT of the selection being textured before blaming the
texture path or the apply call.

**Verify new geometry by its ODOL SECTION, not by strings (invariant, added 2026-08-19, SUB_BRZ marker hunt):**
Geometry added to a MLOD by tooling can be present in every string table of the binarized
p3d — selection name, material, texture — and still never render, because whether the
engine draws a section is decided by fields the strings do not show. Measured on the
SUB_BRZ dash marker across seven builds:

| Section `special` | Meaning | Renders? |
|---|---|---|
| `0x0002C000` | hidden-selection + opaque pass | yes (all working textured sections) |
| `0x0002C100` | hidden-selection + alpha pass | alpha-dependent, unreliable for tiny quads |
| `0x0000C000` | no hidden-selection bits | **never** |

Two authoring rules follow. (1) A bone-skinned textured selection must ALSO be listed in
`CfgModels.sections[]`, or binarize emits `is_sectional=0 / sections=[]` and there is no
draw call for the bone — being a `skeletonBones` entry is necessary but not sufficient.
(2) The face texture must be a real `.paa` FILE: a procedural `#(argb,...)` face texture
on new geometry produces `0x0000C000`. Procedurals are fine in rvmat stages, not as the
face texture of a section you need drawn.

Gate before every deploy that adds geometry: extract the PBO and parse the ODOL section
table, asserting `is_sectional==1`, non-empty `sections`, and the `0x20000` bit. The LOD
address table is found by chaining (`lod_end[i] == lod_start[i-1]`, max end ≈ file size);
a naive scan for the first plausible table hits a false positive. Reference implementation:
`<vehicle-import>\work\navscreen_planb\gate_sections.py` (built on `dayz-p3d-debinarizer`'s
`odol_reader`). String-only scans pass while the geometry is undrawable — that gate cost
five wasted in-game cycles before it existed.

**PAA files: always encode with ImageToPAA (added 2026-08-19):**
A hand-rolled PAA whose mip chain runs below 4 px is invalid DXT. The failure mode depends
on the pass: an 8x8 DXT1 `_co` renders as the engine grey fallback, while a `_ca` with
2x2/1x1 mips renders as nothing at all on an alpha section. Encode every texture with
`DayZ Tools\Bin\ImageToPAA\ImageToPAA.exe` from a >=64 px source and let it build the mips.

**Recycle existing faces instead of authoring new ones (invariant, added 2026-08-21, SUB_BRZ marker):**
On an imported/ripped vehicle model, faces ADDED by tooling can be perfectly formed and still
never render, while every modification of pre-existing faces shows up reliably. Measured over
ten builds on SUB_BRZ: a static witness quad — no bone, no animation, bright file texture,
section `0x0002C000`, winding/flags/normals identical to neighbouring faces that render, and
nothing occluding it — stayed invisible in-game; a bank-window quad that already existed was
shrunk, retextured and re-UV'd in the same file and rendered immediately. When a model needs a
new visible element, look for geometry already in it that can be repurposed (an unused overlay
quad, a hidden variant, a duplicate panel): you inherit its section, its bone and its proof of
rendering. Reserve authored geometry for models you build from scratch, and if you must add
faces to an imported model, prove one renders before building anything on top of it.

**Translation offsets: make the memory axis exactly 1 m and the ambiguity disappears (added 2026-08-21):**
For `type="translation"` in model.cfg, `offset0`/`offset1` are documented inconsistently: they
behave as metres in some sources and as a fraction of the axis vector in others, and picking
wrong is silent — the selection simply moves somewhere off the model, which reads exactly like
"my geometry does not render". SUB_BRZ lost six build cycles to a marker translated with
`offset1 = 1.0` against a 169 mm axis: under the metre reading each phase step threw it half a
metre out of the cabin. Author the memory axis **1.0 m long** in the travel direction and set
`offset1` to the travel in metres (0.169 for 169 mm of sweep). Both readings then produce the
same displacement, so the question never has to be answered. When a hidden/animated selection
is invisible, disconnect its animations and rebuild before blaming geometry or materials — a
detached control build is one cycle and it splits the two causes cleanly.

**Reading a dark-art dash at night (added 2026-08-19):**
Instrument-cluster art driven by `dashboardMatOff` (emissive 0) is invisible in an in-game
night, which reads exactly like "the texture never applied". Pin server time
(`serverTime="YYYY/M/D/12/0"` in serverDZ.cfg) before judging any interior art gate, and
give the OFF material a faint emissive so the furniture stays readable after dark.

**Crew / engine state on a non-owner occupant (SP-288, origen LFHeli LF-008):**
`Car.EngineIsOn()` on a client that is not the Pawn owner returns **false** even when the
authority has the engine running — no exception, no warning. Measured on the occupant of
seat 1 with a two-component probe in the same frame (`natEng=false syncEng=true`) and the
server log showing no stop. Any client subsystem gated on `EngineIsOn()` shuts itself off
(thermal camera died instantly: LF-008). Remedy: replicate the state
(`RegisterNetSyncVariableBool` written in `OnEngineStart/Stop`) and have **every** client
path read `native OR replicated`; an `m_EngineOnAuthority` (OwnerState) snapshot does NOT
serve passengers. When a client check decides to turn something off, print BOTH sources in
the same frame.

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
authored LOD ladder (GTA `.yft` High/Medium/Low, ripped racing-game, Sollumz-imported `.blend` datablocks), use it
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

Before running the ladder on a **ripped** vehicle (GTA, ripped racing-game, any game rip), census which source
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

**A fifth shape, and it fakes an ABSENCE rather than a green (added 2026-08-19, SUB_WRXSTI): matching
a LOD by its nominal resolution.** LOD resolutions on disk are not the round numbers the docs use —
FireGeometry reads `6999999976046592`, not `7e15`. A bucket keyed on `round(7e15)`, or any `==`
against the nominal, comes back EMPTY, and a gate built on it reports "the selection is absent" about
something that is present. Measured cost: a cross-check of the config's `componentNames[]` against the
`.p3d` reported all six damage zones missing, and they were all there in FireGeo — the report reached
the user as a red before the control against vanilla caught it. Always match with a RELATIVE tolerance
(`abs(res - nominal) <= nominal * 1e-3`), and note the direction of the failure: this one does not
show up as a suspicious green you might question, but as a confident red about missing data, which is
the shape people act on fastest.

**One minute, before trusting any gate:** (a) run it against a KNOWN-BAD case — green on a known-bad
means the bug is the gate, not the artifact; (b) name in one line the assumption the artifact was BUILT
with, and confirm the gate does not reuse it. A gate that has only ever been seen green is unmeasured,
not verified.

0. **Gate #0 — mesh + UV health BEFORE anything else (SP-052).** For ANY imported model (ripped or not),
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
   must be INWARD-wound with every point flag = `0x0000003F`:** a py3d box left outward + flags 0 passes every
   offline shape/winding/dual-tag check yet `RaycastRV(ObjIntersectView)` does NOT hit it → the get-in cursor
   falls through to component0 → the driver "works" by fallback but the CODRIVER never resolves. The decisive,
   in-game-confirmed copilot blocker on BOTH SUB_BRZ (s9) and MercedesAMGLF (s12, headless `hit=1 comp=6 crewIdx=1`). The s9 patch changed winding and flags together and never isolated the flag as cause; the safe rule is to copy the sealed vanilla control's convention, never py3d's default. → "componentNN DUAL-TAG" + "CRITICAL EXTENSION 2026-06-28" (`vehicle-structural-parity.md`).
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

10. **Imported-car offline VISUAL gates that LIE — the #7 family (offline geometry heuristic != in-game truth).** The per-session changelog of sub-entries #10(a)-#10(o) (steering-axis fit, single-sided see-through, debug fluids, raycast oracle, rip duplicate faces, per-piece winding uniformity, ViewPilot interior, bright-triangle shading seams, the import-orientation saga, glass occluder twins, foreign-LOD material transfer, gap skirts, hub-lift decoupling, get-in-preserving patches) lives in **`references/visual-gates-and-winding.md`** (s14->s23, SUPERSEDED entries archived there). The single operative winding rule stays here:
   - **THE RULE (import orientation, #10j):** keep the raw glTF winding VERBATIM for ALL pieces (net rip→DayZ = `(-Fx, Fy+Y0, -Fz)`, det=+1, preserves the authored visible side end-to-end); stored MLOD normals = smooth(+cross) of the FINAL winding. NEVER orient winding to a normal oracle or to outward-of-centre. Repair ONLY source-inconsistent components by MAJORITY flood-fill per connected component (never minority-area). `glass*int_a` panes are legitimate cabin-side glass (do not delete as z-fight). Full mechanism, measurements, and the SUPERSEDED (h)/(i) history: `references/visual-gates-and-winding.md` #10(j)/(f).
   - **Winding is per profile (SP-217).** rip/vehicle with measured transform det=+1: preserve (`#10j`). Generic DCC import with no profile: flip visual by default (SP-071; proxies exempt). The in-game A/B (SP-070) adjudicates correction; a lineage gate adjudicates preservation. Do not apply generic `dayz-model-pipeline` Smart UV / decimation / flip defaults to a vehicle.

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
    parity. Reusable tool: `<vehicle-import>\s25_plan\measure_wheel_vs_crew.py` (fits rim by
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
    needs the radiator). Vanilla `FillUpCarFluids()` does NOT do all of it, and mirroring `OnDebugSpawn` is not
    enough either. It fills exactly FUEL, COOLANT and OIL — **BRAKE is not among them**
    (`scripts/4_world/entities/vehicles/carscript.c:3191-3196`, read 2026-08-20; a single
    definition in the tree, every other hit is a call, so no subclass overrides it). The
    radiator does not come from it either: that is `SpawnUniversalParts()`
    (`carscript.c:3141-3145`), gated on `IsVitalRadiator()`, via `CreateInInventory` — which
    searches `CARGO | ATTACHMENT` and may land in either (`inventory.c:876-893`), so a debug
    spawn does not guarantee an ATTACHED radiator. Fill BRAKE and attach the radiator
    explicitly; a hand-rolled `KitManual` in the mission `init.c` has to do both. `CarFluid` enum = FUEL/OIL/BRAKE/COOLANT
    (`scripts/3_game/vehicles/car.c:18`); `Fill`/`GetFluidCapacity` at `car.c:376/359`.

    **How the gap was found (SUB_WRXSTI, 2026-08-19).** This invariant used to name
    `FillUpCarFluids()` as satisfying it. A mod car whose `OnDebugSpawn` calls it and stops — which is the obvious, vanilla-faithful thing to write, and what both SUB_BRZ and
    SUB_WRXSTI shipped — spawns its test car with the brake reservoir EMPTY. That is the exact state
    this invariant says breaks the engine while driving, reached by following vanilla. Add the fourth
    fill explicitly: `Fill(CarFluid.BRAKE, GetFluidCapacity(CarFluid.BRAKE))` — capacity from the
    declared value, not a copied `200.0`, since `brakeFluidCapacity` is `1` unless the car redeclares
    it (`DZ\vehicles\wheeled\config.cpp:244`, the only declaration in that file, verified
    2026-08-20). Corollary worth more than the fix: an invariant that names the right requirement AND
    names a vanilla call as satisfying it will be read as "call that and you are done". Verify the
    call, not the claim.

17. **Raise tyre grip WITHOUT touching the wheel binding: a `CarWheel` subclass of the vanilla wheel.** To add
    grip to a car that slides, do NOT rewire slots/proxies (risks re-opening the freeze/wheel-bind). Declare
    `class <Mod>_Wheel : CivSedanWheel { scope=2; tyreGrip=0.98; };` — it INHERITS the vanilla `inventorySlot[]`
    (`DZ\vehicles\wheeled\config.cpp:4761` lists CivSedanWheel_1_1.._2_2 + Spare) so it drops into the same
    `CivSedanWheel_*` slots and reuses the sedanwheel proxy; only tyreGrip changes. Then `OnDebugSpawn`/kit
    create `<Mod>_Wheel`. Grip is DECOUPLED from the visual wheel model (custom source-game rim = separate visual job). SUB_BRZ s28.

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
22. **An attached item with its OWN radial actions (CarDoor open/close, hood, trunk) needs a raycast-visible ViewGeometry — point flags 0x0000003F — or the action NEVER appears (SUB_BRZ s38).** The action chain resolves the TARGET by raycast: `ActionCarDoorsOutside.ActionCondition` casts `target.GetObject()` to CarDoor and reads the selections of the hit VG COMPONENT of the ITEM (`actioncardoorsoutside.c:34-46`); a VG whose points carry flags 0x0 is not hit by `RaycastRV(ObjIntersectView)` — the same mechanism as the seat-cube blocker (preflight #4, in-game verified SUB_BRZ s9 + MercedesAMGLF s12) — so the item under the cursor never resolves and the radial is silently filtered, with config, script overrides, slots, bones and anim sources all CORRECT. Contract for the item's VG: (a) componentNN dual-tagged with a selection named EXACTLY what the vehicle's `GetAnimSourceFromSelection` expects (e.g. `doors_driver`); (b) every VG point flags 0x0000003F; (c) inward winding (copy a fixed seat cube as control). Symptom signature: attachment renders/attaches/damages fine, `GetCarDoorsState` works, but no open/close radial (and hence no get-in-through-door). Diagnose offline in seconds: census the item's VG point flags vs a working control BEFORE touching config or scripts. Origin: SUB_BRZ s38 D4e; the door fix's own in-game gate pending as of 2026-07-17, but the raycast mechanism is the twice-verified #4 one.

23. **`componentNN` dual-tag is the confirmed fix for simultaneous seat/wheel selection failures; ascending LOD order is match-vanilla practice, not a proven cause (LFHeli OH-1 v2, 2026-07-17).** Sorted-without-dual-tag still failed; sorted-plus-dual-tag spawned; dual-tag-without-sort was never isolated. Therefore a py3d/hand-assembled model with `seat_* not found` / `wheel ... no proper selection` must be checked for collision-selection dual-tag first. `model.lods.sort(key=resolution)` may remain as deterministic authoring hygiene, but no gate may report that sorting fixed the defect. `binarize` accepts either order silently.
> Historial del texto superado: `history/cambio-1-superseded-family-b-rules.md` §“Invariante 23”.

24. **`binarize` is the three-state offline load oracle; `RESOLVED_LIMIT = 65535` is a false friend (SP-122, LFHeli HH-60G, 2026-07-29).**
> Historial del texto superado: `history/cambio-1-superseded-family-b-rules.md` §“Invariante 24”.

Measured evidence for this invariant — the three verdict states, the real ceiling in triple
units, headroom accounting and what does NOT discriminate — is in
`references/binarize-vertex-budget.md`.

25. **GTA V rip intake (dlc.rpf) — mod RPFs are usually UNENCRYPTED and fully parseable offline; the vehicle skeleton maps 1:1 to DayZ needs (LFHeli HH-60G, 2026-07-18).** Check the encryption dword at offset 12 of the RPF7 header FIRST: `0x4E45504F` ('OPEN', standard for OpenIV-built mod RPFs) = no GTA V install, no NG/AES keys needed. Verified on-disk layout: 16-byte header (`7FPR` magic, entryCount, namesLength, encryption); 16-byte entries discriminated by dword2 (`0x7FFFFF00` = directory, high bit set = resource, else binary); file offsets in 512-byte sectors; binary entry with fileSize==0 = stored verbatim (nested .rpf — recurse in place). A resource on disk = **16-byte RSC7 header IN THE CLEAR** (magic `RSC7`, version — 162 yft / 13 ytd —, sysFlags, gfxFlags) + raw-deflate payload from +16 (`zlib wbits=-15`); scene-standard standalone `.yft`/`.ytd` files are exactly that byte range copied verbatim, so extraction is a copy, not a re-encode. Skeleton conventions worth knowing before Blender (string-scan of the decompressed payload suffices — no FRAG parsing): rotors ship THREE states `rotor_main`/`_slow`/`_fast` (+ `rotor_rear` same) = direct map to the DayZ static+blur rotor pattern; doors `door_[dp]side_[fr]` + `handle_*`; glass as own bones (`windscreen`, `window_*` — glass census for free); `seat_[dp]side_*`, `wheel_lf/rf/lr`, `gear_*` incl. `gear_door_*`; guns/turrets are separate bones (`turret_*`, `weapon_*`) = clean v1 exclusion. Toolchain [IN-VIVO VERIFIED 2026-07-18]: Sollumz 2.8.3 imports binary `.yft` directly (PyMateria/szio, Windows-only) on Blender 5.1 (4.0-5.1 supported), while CodeWalker demands a GTA V game folder on first run — so for OPEN rips the primary chain is own-extractor → Sollumz binary import, CodeWalker only as fallback. Two verified gotchas: (a) **PyMateria's native `.pyd` fails to load from a long path** ("DLL load failed ... filename too long", MAX_PATH) — install Sollumz into a SHORT isolated Blender profile via `BLENDER_USER_RESOURCES=C:\tmp\blp` (also keeps the user's running Blender untouched); headless install = `bpy.ops.extensions.package_install_files(repo="user_default", enable_on_install=True)` + `<addon>.dependencies.install_dependencies(online_access_override=True, optional_dependencies_to_install={"pymateria"})`. (b) **The `.yft` does NOT carry its textures** (they live in sibling `.ytd`), and Sollumz's high-level `gta5.try_load_asset` returns None for a `.ytd`, and its `.yft` import wires 47 named-but-empty image nodes — the FIX is the RAW PyMateria binding: `pmg8 = szio.gta5.native.provider_gen8.pmg8`; `res = pmg8.TextureDictionary.import_rsc(Path(ytd))`; `td = res.result`; `td.textures` is a Map(name→Texture); `tex.export_dds(path)` writes the decoded DDS (PyMateria does all the RSC7+format). ~generic base-game textures (`vehicle_generic_*`) live in GTA's `vehshare.ytd` (not in the mod) and stay missing = pink in Blender, but IRRELEVANT for DayZ (glass gets a vanilla `.rvmat`; the rest are secondary spec/detail overlays). Origin: LFHeli HH-60G intake (`rpf_extract.py`/`ytd_extract.py`/`bl_install.py` in `LFHeli_dev\model_src\HH60G_intake\work\`; textured artist package verified by render).

26. **A rip's BONE NAMES are not its MESH PIECES, and an exclusion REGEX silently classifies content nobody has looked at (LFHeli HH-60G, 2026-07-28).** Two failures of the same import, both invisible offline and both only surfaced by a full in-game cycle. (a) **Regex exclusion.** The day-1 census marked `exclude_v1` with `^(mod_[a-z0-9]+|turret_|weapon_|siren\d|extra_\d|hbgrip_)` to drop "GTA cruft". That swept in `mod_n` (31.598 tris = the whole nose kit: refuelling probe, rescue hoist, radome, nose pods) and `mod_s` (52.550 tris = the entire interior, seats included). The exporter inherited the classification and the vehicle shipped with no nose and a hollow cabin; **94.084 tris of legitimate content, 38% of the source**, lost for ten days without one warning. Rule: **the exclusion list is LITERAL NAMES, one justifying line each — never a regex.** A regex classifies pieces nobody has looked at yet; a literal list forces you to look. (b) **Bone names != mesh pieces.** The string-scan of the skeleton (item 25 above) lists `handle_*` next to `door_*`, so the routing table cited `handle_dside_f/pside_f/dside_r/pside_r`. Measured against the actual LOD levels: those four names exist in **no** level of the `.yft` and in **no** mesh of the imported `.blend` — the skeleton carries bones with no geometry behind them. **Item 25's skeleton-convention list is a hypothesis about names, not a piece inventory**; intersect it with the per-level mesh list before routing anything. Corollary that decides the fix: "the export LOST a piece" and "the export CITED a piece that never existed" look identical from a silent `if obj_by_name(n)` skip and lead to **opposite** repairs (go find it vs delete the row). Gates that would have caught both on day 1, cheap and offline: **SOURCE = the piece set of the richest LOD level, measured** (here `hh60g.yft/High` = 49, set-identical to `hh60g_hi.yft/VeryHigh`); every source piece appears **exactly once** in a routing group or in the literal exclusion list, partition verified by set equality, not by totals; every routed name is **in SOURCE**; and a missing artefact is an **error, never a `[skip]`**. Origin: LFHeli HH-60G, plan v15 Fase 1.1/1.2; measurement in `LFHeli_dev/plans/2026-07-28-hh60g-v15-censo-y-tabla-normativa.md`.

27. **A model that passes every offline gate and still refuses to spawn is almost always over the RESOLVED-VERTEX ceiling — and `binarize` tells you offline, in 90 seconds (LFHeli HH-60G, 2026-07-29).** `PHYSICS (E): Won't simulate, it has no geometry` is emitted when the engine aborts while **loading the MLOD**, before it ever builds physics — so a perfect Geometry LOD does not exonerate the model, and chasing it as a collision problem costs days. **Do this first, not last**: drop the `.p3d`s into a dir under `P:\` with a `model.cfg` declaring **every** basename, run `binarize.exe -always <src> <out>`, and read the verdict — `Too many vertices` names the culprit by filename. Validated 25/25 against in-game verdicts on 28 variants (zero false greens, zero false reds), which turns model bisection from ~6 min per variant into ~90 s per batch. Three rules that make it a real gate: (a) the verdict is **three-valued** — `PASS` needs a *new* non-empty ODOL (a residual one is a false green), `CAPACITY_FAIL` needs the `Too many vertices` line *attributed to that MLOD*, and anything else is `OTHER_FAIL` which **blocks and does not authorize touching geometry**; (b) the verdict is reproducible but the **ODOL bytes are not** (same input, 1.725.025 and 1.726.689 b in two clean runs) — never gate on the ODOL SHA; (c) the ceiling in `(point, normal, uv)` units is **not 65535 and not portable** — measured 46.133 on the HH-60G across four bases, because the engine's cap is on POST-SPLIT vertices and your counter under-counts by a model-dependent factor (1,4205 here, 1,46 on the OH-1). An assembler with `RESOLVED_LIMIT = 65535` hardcoded closed its own gate in green for weeks on a model the engine refuses. **Re-measure per model, and know your headroom** — the deployed HH-60G sat 114 triples under the cliff, one normal tweak from death. Full detail, including why reversing corner order is free while minting a normal is not: **SP-122** at the bottom of this skill. Tool: `<vehicle-import>\scripts\p3d_vertex_gate.py`. **SP-216 rider:** py3d **count** gates (resolved<65535, normal pool, digest, identical Geometry) do not authorize spawn. The first oracle for `Won't simulate, it has no geometry` is `binarize` (invariant 27): `CAPACITY_FAIL` → do not go in-game; `OTHER_FAIL` → do not touch geometry; `PASS` and the game still says no-geometry → then yes, serialization / another axis, and in-game spawn is the judge. The V8 of SP-216 is the negative capacity control (`CTL_CAPACITY`), not a refutation of `binarize`.

28. **A 4-seat car numbers ONE `crew_cargo` model 1/2/3 — the index is the instance suffix, and two rear seats both at index 1 collide (added 2026-08-16, SUB_WRXSTI T8.2).** There is no `crew_cargo1.p3d`: `P:\DZ\vehicles\wheeled\proxies\` ships exactly `crew_cargo.p3d` + `crew_driver.p3d`, and the seat identity comes from the INDEX. The mapping the consumer actually applies is `bone = "crewcodriver" if index == 1 else "crewcargo%d" % (index - 1)`, so `crew_cargo.001→crewcodriver`, `.002→crewcargo1`, `.003→crewcargo2` (`<vehicle-import>\tools\verify_rip_car.py:983-986`; corroborated by the sealed AC02 control inventory, `profiles\contracts\brz_ac02_v1.json:347-364`, and by CivilianSedan's own Crew Cargo1/Cargo2 block at `P:\DZ\vehicles\wheeled\config.cpp:5206-5218`). Consequences: the front pair legitimately BOTH sit at index 1 because their PATHS differ (`crew_driver.001` and `crew_cargo.001`) — that is not the bug; adding two REAR seats at index 1 on the shared `crew_cargo` path is, and it fails as a duplicate-selection `ValueError` at authoring time if your builder checks, or as silently missing rear get-in if it does not. Extending a 2-seat rig: continue the `crew_cargo` index, never restart it, and pin the mapping with a test whose RED case is exactly the duplicate pair.

29. **A rig threshold on a MEASURED axis must have its source declared for EVERY member of a symmetric pair — declaring it on one side leaves the other on raw measurement, and the build refuses months later (added 2026-08-16, SUB_WRXSTI T8.3 blocker).** The detachable-door rig requires `dir_y > 0.999` (`rip_p3_structural.py`), and a rip's placement tilt lands a door hinge just under it. The WRX profile fixed that for ONE door by declaring `hinge.axis_source.declared = assembly.alignment_build.doorRF`, an axis projected to vertical with its XZ midpoint kept — and the other door, declaring no `axis_source`, kept riding its raw PCA axis. Measured when the whole structural build refused: codriver `|dir_y| = 1.0000`, driver `|dir_y| = 0.998575` = **3.059°**, i.e. one door 3 degrees from a threshold the other met exactly. This is `DZ-R7` (trace the invariant to all call-sites) applied to profile DATA rather than code, and it is invisible until the gate fires, because both doors look declared and only one is. Two riders paid the same day: (a) project each side keeping **its own** XZ midpoint, never mirror the other door's — the two sides of a rip are not symmetric, and mirroring here would have moved the hinge 3.7 cm (driver x +0.849278 vs codriver x −0.811827); (b) relaxing the threshold to admit the one bad case is the tempting fix and the wrong one — the threshold exists so a door does not open tilted, and lowering it for one car lowers it for all.

30. **A seat box is a GET-IN VOLUME, not the cushion — vanilla leads it ~0.15 m toward the nose of the crew position, and collapsing the two onto one point makes rear seats unenterable (added 2026-08-16, SUB_WRXSTI).** The engine resolves the get-in cursor by raycast against the ViewGeometry, so the seat box has to sit inside the DOOR APERTURE; the body that occupies the seat sits further back, against the backrest. Vanilla keeps them apart deliberately — measured on the sealed control `civiliansedan_mlod.p3d`: crew proxy z −0.173 vs seat box z −0.358 in front, +0.675 vs +0.531 in the rear, i.e. the box leads the crew proxy by 0.185 and 0.144. A rig that places both at the same declared point looks correct on a 2-seat car — there is open flank ahead of the front seat either way — and puts the box of a 4-seat car inside the C-pillar: the WRX measured **43% reach on BOTH rear seats** (21/49 rays; the 28 blocked were exactly those with z ≥ 0.876, against a pillar occluder starting at +0.881) while the front pair read 100%. Three riders. (a) The pillar occluder is CORRECT — do not carve the body or refine the occlusion grid to make a seat reachable; the tempting diagnosis "residual door skin left in the shell" was refuted by measurement (the rip's `doorhandlelr_a` carries 1970 `carpaint` faces of the rear PANEL — the rip names the skin after the handle — and it was already owned by the rear door roles). (b) Move the BOX, never the crew proxy: the passenger must stay on the cushion. (c) Calibrate the offset against a sealed vanilla 4-seater and cross-check it by sweeping the box along z against the car's own occluder — on the WRX the vanilla-derived 0.740 landed inside the independently swept 100%-clear window [0.700, 0.800], and the sweep reproduced the measured 43% at the shipped z, which is what makes the simulation admissible. The matching detector is invariant 31.

31. **Seat/crew checks written as a literal front pair go blind the day a car grows a rear row, and report `2/2 100%` while doing it (added 2026-08-16, SUB_WRXSTI).** `verify_rip_car.py` listed `("seat_driver", "seat_codriver")` in the reach ray fan, the componentNN overlap targets and the ViewGeo presence check, plus a hardcoded `/2` denominator in two report strings. On a 2-seat car that IS the whole roster, so the blindness never shows; on a 4-seat car it printed green over two seats it never scanned, one of which was 43% reachable. Derive the roster from the **crew bones** (`crewdriver→seat_driver`, `crewcargo1→seat_cargo1`, …), not from the seat boxes present: deriving from the boxes is blind in the other direction — a car that LOSES a seat box simply has one fewer thing to check and stays green. Same derivation for the `pos_*(_dir)` memory points. Calibrate against the sealed vanilla 4-seater (it measures 4/4 at 100%), which is what turns a 43% into a defect rather than a strict gate.

32. **Two halves of a car that a name-existence gate cannot see: the open-door action reads the DOOR PROXY, and vanilla parity is not a behaviour spec (added 2026-08-16, SUB_WRXSTI).** (a) `ActionCarDoorsOutside.ActionCondition` does `CarDoor.Cast(target.GetObject())` and then `carDoor.GetActionComponentNameList(...)` — the selection names come from the **attached door item's own `.p3d`**, not from the shell (`4_world\classes\useractionscomponent\actions\interact\vehicles\actioncardoorsoutside.c:30-58`, re-read 2026-08-16). If the proxy does not carry `doors_<role>`, `GetAnimSourceFromSelection` returns `""` for every one of its components and the open/close action never appears from outside — no error, no log. Measured placement on both the WRX and the shipped BRZ: the name lives in the proxy's **Geometry and ViewGeometry** LODs; FireGeo carries only `Component01/02`, `dmgzone_*` and `glass_<role>`. Every gate in this project measured the SHELL; nobody had ever opened the six door proxies. When verifying "the doors open", the evidence is the proxy — the shell only proves the model references it and that the animation axis exists. (b) Three behaviours are **correct vanilla ports and still wrong for a mod**: `OnDebugSpawn` drops the parts loose in cargo (`civiliansedan.c:408-430`) so a freshly spawned car needs ten manual attachments before it moves; `CarScript.EEOnCECreate` fills `Math.RandomFloat(0.0, capacity*0.35)` (`carscript.c:2967-2974`) so a CE-spawned car can arrive dry; `CanDisplayCargo` opens the cargo on the boot alone (`civiliansedan.c:162-171`). All three ship a car that loads, drives and looks right, and every structural gate passes them by construction because the criterion is "does it match vanilla". Declare behaviour PER CAR in the profile (`vehicle_script_policy {cargo_access, debug_spawn, ce_spawn_fuel}`) and measure the script against that declaration; derive the attachable roster from the config's own `inventorySlot[]` blocks so a renamed class reds by itself. Rider on the silent one: `CrewCanGetThrough` must compare against `DOORS_CLOSED`, because a torn-off door reports `DOORS_MISSING` — writing the same intent as `!= DOORS_OPEN` reads correctly, passes every structural check, and makes a doorless car unenterable. See LL-279.

33. **Un carril de gates que solo mide numeros es ciego al color y a la orientacion de un proxy, y el unico instrumento que los ve es un ojo delante de un render MONTADO (added 2026-08-16, SUB_WRXSTI).** Nombres que existen, caras que se conservan, hashes que cuadran y matrices plaza→puerta→slot completas: todo eso pasa en verde sobre un coche monocromo con las llantas del reves. Medido: el WRX llego al PBO con el 64% de sus caras en UN material y el interior entero en otro (la importacion registro `material_map: null` y mando 37 piezas con nombre — emblemas, espejos, escape, jambas, faldones, bajos, brazos — al cubo de pintura), con los cuatro proxies de rueda escritos con la matriz IDENTIDAD donde vanilla escribe DOS espejadas una por lado, y con la rueda de berlina vanilla de 176 mm en vez de la suya. Los cuatro defectos los encontro el usuario en minutos la primera vez que vio el coche montado; ninguno era visible a ningun gate. Tres riders. (a) El render tiene que ser ENSAMBLADO y con materiales: las piezas sueltas y en gris no enseñan ni un color mal ni una llanta invertida — un `visual_sheet` que dibuja geometria gris por piezas ya existia y no vio nada. (b) El veredicto humano se ata al sha256 de lo que se miro, o se pudre: tras un rebuild nadie puede decir si aprobo ESTE coche o el anterior, y el gate debe ponerse rojo por stale, no seguir en verde. (c) Calibra la quiralidad con TEXTO DE MARCA, no con la intuicion: DayZ es zurdo y los motores de visor suelen ser diestros, asi que pasar coordenadas tal cual es una reflexion, y un coche espejado se ve normal hasta que un emblema se lee al reves. Contrapartida honesta: esto NO sustituye al test in-game, solo mueve mas barato el hallazgo de lo que se ve.

34. **An absent key in a config class is NOT a value — it is a question about the parent (added
    2026-08-21, from a refutation that did not survive).** Reading `config.cpp` by grepping for a
    key and treating "no hit" as "the default" gets the answer backwards whenever the class
    extends another that sets it. Measured case: `CivSedanDoors_BackLeft` declares no
    `rotationFlags` at all — four lines of body (`DZ\vehicles\wheeled\config.cpp:4923-4932`) —
    and extends `CivSedanDoors_Driver`, which sets `8` (`:4798`). A note published on
    2026-08-19 read the absence as `4` and concluded the sedan REFUTES the left-8/right-4 rule;
    it does not, it is the rule's own prediction. The other five do declare `4` (CoDriver
    `:4921`, BackRight `:4942`, Hood `:4957`, Trunk `:5034`), which is exactly what made the
    sixth look like an outlier instead of an inheritance. **Resolve the chain before quoting a
    value, and say which link you read it from.** The same trap applies to every inherited
    config key, not just `rotationFlags`.

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
3. **One command wraps the day-1 measurements**: `python <vehicle-import>\tools\import_preflight.py
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

7. **Reference-frame MARKER pass, before anything is built on top** (added 2026-08-15,
   MercedesAMGLF G1). Two blind spots compound: a face with an empty `texture` renders **WHITE**, and
   white masks every frame/UV defect underneath it; and a mirrored or 180-rotated parametrization is
   **invisible on any surface without legible text**. Together they hid the same defect here from June
   to August, and it was CLOSED ONCE with the wrong diagnosis ("aliasing", measured 172-180 texels/m,
   4 px/cycle) because no one had a surface that could show handedness. Inject the markers on the
   FIRST import and judge them **in the engine** - not the viewer, not the DCC: the engine defines the
   convention.
   - **Texture marker**: one image, asymmetric under every symmetry of the square - an `F`, a labelled
     +U arrow, a labelled +V arrow, four distinctly coloured corners, and a grid for scale. Point
     EVERY visual face at it; this is the same single-field pass that repairs an empty `face.texture`,
     so it costs nothing to build once. **Redirect the `hiddenSelectionsTextures` slots too**, or the
     config stamping paints over the marker on the host and you read a false pass. Delivers in one
     look: mirror, rotation, per-island rotation, tiling and scale.
   - **Geometry marker**: a small tri-axis gizmo, three differently-SHAPED arms on +X/+Y/+Z, welded at
     the origin. Catches axis permutation and a reflected transform with no textures involved. This is
     the one that would have flagged a frozen `(x, y, -z)` on day 0 - and note that compensating a
     reflection by flipping winding fixes lighting and culling but NOT texture handedness.
   - **Caveat that cost a cycle**: the texture marker is USELESS on heavily tiled surfaces. A seat net
     at u in [-14.9, 25.0] repeats ~40x and shows only fragments of the glyph, which reads as a defect
     and is not one. Measure the per-material UV range first and annotate those surfaces before
     looking, or you will chase your own marker.

## LEGACY DIAGNOSTIC GATE LADDER -> `references/legacy-gate-ladder.md`

Superseded diagnostic order, kept for vehicles already in flight; no rung fires automatically
for a new family B asset. Moved out of the body 2026-08-15. The current findings that used to
live under that heading now have their own sections, immediately below.

## Calibration + scope (so a gate is trustworthy, not a false green)

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


## A rip-imported PANEL is two parallel skins with an OPEN rim; a vanilla panel is a closed volume (SP-247, added 2026-08-15; SUB_BRZ doors E-1 — CORRECTED the same day, see the refutation below).

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


## Building an OFFLINE viewer/render for the user to judge? Two traps that make it lie (SP-248, added 2026-08-15; SUB_BRZ 1PP).

Both were caught by the user, not by any gate.
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


## The ViewPilot (res-1100) is a CURATED view — not a copy, not a budget, and never trimmed against a partial car (SP-249, added 2026-08-15; SUB_BRZ s52, root-caused).

One car shipped both halves of
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
- `references/binarize-vertex-budget.md` — evidence behind invariant 24: the three verdict
  states of `binarize`, the real ceiling in triple units, headroom accounting, and the noise
  that does NOT discriminate. Read it when a model passes every offline gate and still will
  not spawn.
- `references/legacy-gate-ladder.md` — superseded pre-CAMBIO-0 diagnostic order, kept for
  vehicles already in flight. Nothing here is current doctrine; the findings that used to sit
  under that heading and still are (SP-247/248/249) now have their own sections above.

> REDIRECT CAMBIO-1: el único índice síntoma→cookbook de familia B está en `../rip-vehicle-import/SKILL.md`.
- `references/rip-geometry-and-winding.md` - geometria del rip: retopo, winding y cirugia de caras.
- `references/proxies-and-get-in.md` - proxies, get-in y partes desmontables: el contrato.
- `references/doors-and-panel-edges.md` - puertas: canto abierto, tapas y desmontables que no son puertas.
- `references/network-physics-ownership.md` - red, fisica y ownership: quien manda sobre la pose.
- `references/visual-metrics-and-viewer.md` - metrica visual: que se puede afirmar desde una captura.
- `references/materials-and-selections.md` - materiales y selecciones: dos diagnosticos que enganan.
- `references/animation-sign-and-axis.md` - el signo de una animacion no se juzga sin su eje.
- `references/process-gates.md` - gates de proceso: fixtures negativas y reglas promovidas.

## CITE-THEN-VERIFY

Vehicle config and model values are easy to half-remember. Before writing a class name, property, or
named selection, grep it in vanilla (`P:\dz\vehicles\`) or in the references' cited sources, and keep
the provenance labels the references already use (`[Landrover ✓]`, `[QuadBike]`, `[LFQuad ✓]`,
`[TBD-verify]`). Anchor any new vehicle lesson to a real mod with `path:line`, never to memory.

## LIGHTS — the five failures that look like "the material is broken" and are not (added 2026-08-17; SUB_BRZ B2-B6, all measured in-game)

A car whose lights "do not work" almost never has a broken `.rvmat`. Five distinct causes were
separated in one session by measurement; each has a cheap discriminator. Run them in this order,
because the first one invalidates every test downstream.

### 1. A leading backslash in a material path is rejected in SILENCE

`SetObjectMaterial` accepts `MOD\data\x.rvmat` and **rejects** `\MOD\data\x.rvmat`. No error, no
log line: the readback simply still shows the old material. Proven with an A/B that held the car,
the selection, the index and the target file fixed and changed only the leading character:

```
asked \SUB_BRZ\data\brz_light_brake_on.rvmat  ->  got \sub_brz\data\brz_light_brake_off.rvmat   REJECTED
asked  SUB_BRZ\data\brz_light_brake_on.rvmat  ->  got  SUB_BRZ\data\brz_light_brake_on.rvmat    APPLIED
```

Vanilla never writes the leading backslash on a material path — `CivilianSedan` has 25 of them,
all starting at `dz\` (`DZ\vehicles\wheeled\config.cpp:5165-5195`). Neither does a working modded
glowing item. **But `model=` paths keep their leading backslash and resolve fine**, which is why
the inconsistency survives review: half the file uses one form, half the other, and only the
material half breaks.

Applies to `hiddenSelectionsMaterials[]` and to every `*MatOn` / `*MatOff` key.
Grep before blaming anything else: `"\\MOD[^"]*\.rvmat"`.

### 2. A lamp whose faces are in NO hiddenSelection can never light

Rip-imported cars arrive with the lamp split in two: a large piece (`tail`, `light_left_static`,
`light_right_static`, `light_dashboard_static`) that is absent from `hiddenSelections[]`, plus a
small switchable insert that is in it. On SUB_BRZ that was **19.310 faces that nothing can ever
switch** against inserts of 42 and 318 faces.

The symptoms read as material bugs and are not:
- "the red piece is always faintly lit and has no glass" -> the big piece wears a crude constant
  emissive that no setter reaches.
- "only one bulb of the two lights up" -> only the insert is in the selection.
- "the position lamps do not light" -> they do; 42 lit faces against 1.555 unlit around them.

Discriminator, before touching any material: count faces per selection and cross them with
membership. A bounding box is NOT enough — `tail` spanned 3.788 mm of a 4.086 mm car and still was
only the two rear clusters plus two corner markers. Plot every face centroid; the distribution
answers what the box cannot.

### 3. Engine-off and lights-off on driver exit are TWO different bugs

**Engine** is script and is fixable. `CarScript.OnDriverExit` calls `EngineStop()` when the gear
is not neutral (`carscript.c:1207-1215`); `Transport.OnDriverExit` is a no-op
(`3_game/vehicles/transport.c:161`), so an override that does not call `super` loses nothing. Add
`ShiftTo(GetNeutralGear())` (`car.c:271`, `:262`) or a running engine plus `Brake.driverless`
makes the car creep. Measured working: `engine=ON` on client and server, at the event and at
+500 ms and +2 s.

**Lights are NOT fixable that way.** The native forces `LightIsOn()` false on the CLIENT as soon
as the driver seat empties, and vanilla's `m_Headlight` is slaved to it
(`carscript.c:2116-2156`), so the beam is always destroyed and **re-asserting server-side cannot
bring it back**. The working pattern decouples the beam from `LightIsOn()`:

1. a synced `bool` intent + an own `CarLightBase` member;
2. `RegisterNetSyncVariableBool` on the intent in the constructor;
3. `ToggleHeadlights` override that records the intent and `SetSynchDirty()` on server — the
   native exit-clear does NOT call `ToggleHeadlights`, which is exactly why the intent survives it;
4. a `ManageExitLight()` that creates/destroys the own beam edge-triggered, attached at the
   midpoint of the two headlight memory points, called from a `UpdateLightsClient` override;
5. `EEDelete` cleanup so the beam cannot outlive the car.

To make the parked beam appear promptly, copy vanilla's own line rather than inventing one:
`ForceUpdateLightsStart(); g_Game.GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(ForceUpdateLightsEnd, 100, false);`
(`carscript.c:535-536`; the pair is defined at `:2981` and `:2990`).

Reference implementation in this tree: `P:\LFQuad\scripts\4_world\entities\vehicles\inherited\LFQuad.c`.

### 4. No bulbs mounted = brake and tail never light, and it reads as a failed fix

`m_HeadlightsState` stays `NONE` without HeadlightH7 in the reflector slots, and the rear beams
are gated on it (`carscript.c:792-813`, `:2177`). Testing brake lights on a car whose bulbs sit in
the cargo produces a confident false FAIL.

Related and cheap: `OnDebugSpawn` must use **`CreateAttachment`**, not `CreateInInventory`.
Vanilla's `SpawnUniversalParts` (`carscript.c:3121-3158`) drops everything into cargo, so every
test cycle starts with manual assembly and one forgotten bulb poisons the run.

### 5. Measure the setter against a VANILLA car spawned alongside

`SetObjectMaterial` / `GetObjectMaterial` are `proto native` (`entityai.c:2896-2900`): whether they
work is not decidable by reading source. Probing only the car under test cannot separate "our model
is wrong" from "this build does not apply overrides at all". Spawn a stock `CivilianSedan` next to
it and run the identical call, into the SAME log:

| vanilla switches | ours switches | conclusion |
|---|---|---|
| yes | yes | no override fault; it was the bake |
| yes | no  | the fault is in OUR model |
| no  | no  | the environment does not apply overrides; the probe never measured the setter |
| no  | yes | incoherent, repeat |

Resolve the selection **by name** with `GetHiddenSelectionIndex` (`entityai.c:2792-2798`) and print
the resolved index; never hardcode an index onto a vanilla car. If the resolve fails, SKIP — do not
fall back to 0, which is the front-left light of the CarScript ABI (`carscript.c:293-301`) and
corrupts both the car and the measurement.

And adjudicate by photo: the `got=` of a readback is the setter's echo, not proof that the engine
drew anything.

### 6. `rotationFlags` is per SIDE, and the wrong one renders an empty preview

Left-hand doors take `8`, right-hand doors take `4`. Vanilla applies this in every family —
`Hatchback_02_Door_1_1`/`1_2` use 8 while `2_1`/`2_2` use 4 (`DZ\vehicles\wheeled\config.cpp:9006`,
`:9130`, `:9141`, `:9265`), and `Truck_01_Door_2_1` overrides its left-hand parent purely to set 4
(`:18301`). A mirrored door that inherits the left-hand value shows a **blank item-inspect preview**
while its opposite renders normally, with everything else identical: same LOD table, same named
properties, same bounding box, same distance to origin, same selections, same winding. Symmetric
config plus symmetric geometry plus one side blank means look at `rotationFlags` before the model.

## Get-out desync: one-shot bilateral OnDriverExit probe (SP-276, origen LFHeli LF-001)

For "invisible/desync on exit" bugs, a one-shot probe in `OnDriverExit` that prints on BOTH
sides `playerPos`, `heliPos`, `crewEntryWS`, `dPH`, `dPC` adjudicates in one flight what
hypotheses do not: good exit = client == server; bad exit = client with the vehicle at the
spawn pose (sunk) and the player underground, server correct. Align client/server clocks by
PAIRS of twin events (the two EXIT lines gave a stable 33,99 s offset) and correlate with
the owner's position series (FRAME p0) to date the divergence. Complements the Pawn ladder
in `references/network-physics-ownership.md` (SP-188).

## ARCHIVO DE LECCIONES — leer por tema, no por fecha

Las lecciones acumuladas viven agrupadas por tema en `references/`. Cada
entrada dice que hay dentro para que se pueda decidir si abrirla sin abrirla.
Todo lo de abajo es doctrina VIGENTE (lo derogado esta en
`references/legacy-gate-ladder.md`, y solo eso).

- **Geometria del rip: retopo, winding y cirugia de caras** -> `references/rip-geometry-and-winding.md` (16,302 ch, 8 lecciones)
  Todo lo que toca la MALLA importada: intake del rip, auto-retopo, winding (gate y
  direccion), `autocenter`, y como borrar/partir caras sin romper las selecciones.
    - RIPPED RACING-GAME IMPORT
    - Auto-retopo of a dense rip = Quadriflow PER-PANEL + ASCENDING target sweep
    - Rewriting a proxy triangle: regla corregida para proxies y caras visuales
    - `autocenter=0`: alcance corregido por LOD, host y submodelo
    - A winding gate must measure the WHOLE piece, ALL render LODs, and twin pairs
    - Game winding is the INVERSE of MLOD geometric winding; fix winding per…
    - Cirugia de caras en un .p3d: un criterio por UN eje parte los quads que…
    - Borrar caras de un .p3d con py3d: muta `lod.faces` IN PLACE o rompes las…

- **Proxies, get-in y partes desmontables: el contrato** -> `references/proxies-and-get-in.md` (17,979 ch, 7 lecciones)
  Colocacion de proxies medida sobre un coche de referencia, el contrato de cuatro capas
  de las partes desmontables, las dos registraciones que necesita una accion en
  vehiculo, y los dos fallos que bloquean el get-in entero.
    - REGEN-FROM-glTF BODY + PROXY-SPLIT / GET-IN RADIAL + LOD LADDER
    - Proxy placement convention - measured on a working reference car
    - Detachable parts (doors/hood/trunk): the FOUR-layer contract, and three rules…
    - In-vehicle actions need TWO registrations, and a proxied part is your…
    - A shared vehicle-core source turns "deploy ordering" gates into fiction
    - Phantom vehicle command blocks ALL vanilla get-in after a client crash while…
    - ViewPilot (1100) of a shell+proxy car MUST carry the body geometry, not only…

- **Puertas: canto abierto, tapas y desmontables que no son puertas** -> `references/doors-and-panel-edges.md` (13,308 ch, 4 lecciones)
  Un panel rippeado no tiene canto. Como se MIDE que falta (longitud de borde libre
  contra el control vanilla), como se cierra por script, y en que se diferencian capo y
  maletero de una puerta.
    - An imported door has NO end caps, and a shut door cannot show you
    - Un canto de puerta ausente se mide por LONGITUD DE BORDE LIBRE contra el…
    - El canto de puerta SE CIERRA POR SCRIPT con una banda de fondo MEDIDO — y…
    - Desmontables que NO son puertas: capo y maletero (medido sub_wrxsti_04,…

- **Red, fisica y ownership: quien manda sobre la pose** -> `references/network-physics-ownership.md` (11,034 ch, 3 lecciones)
  Ownership de red vs asiento forzado server-side, por que escribir pose pelea con la
  reconciliacion del owner, y la escalera de tipos de un armazon Pawn custom con sus
  reglas duras.
    - Ownership de red: seat forzado server-side != ownership del cliente; PHYSICS…
    - PHYSICS = prediccion del owner con reconciliacion: escribir pose pelea con…
    - Armazon Pawn custom (Move/OwnerState): la escalera de tipos y sus reglas duras

- **Metrica visual: que se puede afirmar desde una captura** -> `references/visual-metrics-and-viewer.md` (8,553 ch, 3 lecciones)
  Una queja de pose puede ser artefacto de PERSPECTIVA. Ancla del rayo del HUD. Y la
  regla general: diagnosticar antes de re-autorar, y validar toda metrica visual sobre
  algo visible in-game.
    - An in-game GEOMETRIC POSE complaint can be a PERSPECTIVE artifact - measure…
    - HUD reticle/marker: anchor the ray at the CAMERA, never at the vehicle
    - Diagnose before re-authoring, and validate every visual metric on an…

- **Materiales y selecciones: dos diagnosticos que enganan** -> `references/materials-and-selections.md` (3,959 ch, 2 lecciones)
  Texturas identicas y co-mismatch de servidor parecen diagnosticos solidos y no lo son.
  Y las selecciones dirigidas por el padre (hiddenSelections, anims de config) NO llegan
  a un proxy.
    - Two diagnoses that look solid and are not: identical textures, and server…
    - Parent-driven selections (hiddenSelections / config anims) do NOT reach a…

- **El SIGNO de una animacion no se juzga sin su EJE** -> `references/animation-sign-and-axis.md` (4,368 ch, 1 leccion)
  Como fijar el eje antes de discutir si una animacion va al reves, y por que el signo
  solo significa algo relativo a ese eje.
    - An animation's SIGN is never judged without its AXIS - use the pseudovector…

- **Gates de proceso: fixtures negativas y reglas promovidas** -> `references/process-gates.md` (4,161 ch, 2 lecciones)
  Una regla de gate de import no es entregable sin una fixture NEGATIVA. Mas las reglas
  promovidas del corpus de lecciones.
    - An import gate rule is not deliverable without a negative fixture
    - Reglas promovidas del corpus de lecciones

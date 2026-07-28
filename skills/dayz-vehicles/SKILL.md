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

Drivable wheeled vehicles in DayZ extend **`CarScript`** — there is no generic "vehicle" base, and
you do not build one from `EntityAI` or `Inventory_Base`. `CarScript` gives wheels, seats, sound
integration and the damage system for free; you configure the rest. This skill is the
vehicle-specific layer on top of `dayz-model-pipeline` (generic geometry / LODs / textures) and is
the ground counterpart to `dayz-aviation` (anything that flies belongs there).

Scope: cars, trucks, quads/ATVs, motorbikes — anything wheeled and drivable, modeled from scratch
or imported (Blender / OBJ) from another game.

**Vehicle type matrix (invariant):** `Car` and `Boat` are SIBLINGS, both directly under `Transport`
(`car.c:98` / `boat.c:31`) — NOT parent/child. `Transport` owns crew/get-in/flip/fuel; `Car` owns
wheels/brakes/`CarFluid`; `Boat` owns propeller/buoyancy/`BoatFluid`(fuel-only). A truck is a plain
`CarScript` config with 3 axles + double wheels, NOT a new class. Boats, truck double-wheels, ATV and
the motorbike gap → `references/vehicle-types-boat-truck.md`.

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

## INVARIANTS YOU WILL HIT — preflight checklist (read BEFORE authoring, not after the in-game fail)

These recur on **every** vehicle. They were each won the hard way on one project and then re-derived
from scratch over dozens of iterations on the next (LFQuad → SUB_BRZ → MercedesAMGLF), because they
were not promoted to this checklist in time. Check them up front; full detail behind each pointer.

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

1. **"Get in" radial needs a real SCRIPT CLASS, not a bare config class.** A `class <Mod>: CarScript`
   with no `.c` runs as bare `CarScript`, which inherits `Transport.CrewCanGetThrough()` → **`false`**
   (`scripts/3_game/vehicles/transport.c:493`) → the get-in action is filtered out and **never appears,
   no bone/proxy/componentNN fix helps**. Author `<Mod>_Base extends CarScript` overriding
   `CrewCanGetThrough` + `GetAnimInstance` + `GetSeatAnimationType` (+ `CfgMods` worldScriptModule).
   Verified in-game LFQuad D34 + MercedesAMGLF + SUB_BRZ. → `vehicle-structural-parity.md` "Crew get-in".
2. **The script module must actually LOAD or the class never binds — silent.** `CfgMods` `files[]` with
   back-slashes / a `.p3d` path that resolves to `*.p3d.p3d` → module not loaded → no get-in, no error.
   → `SKILL.md` §"Binding del script", `rip-import.md`.
3. **Geometry LOD carries named property `class=vehicle` — REQUIRED PARITY (6/6 vanilla wheeled
   vehicles have it; cheap to replicate) but REFUTED as the wheel-sim gate:** deploying it alone left
   `wheelPresent=0` (LFQuad in-game 2026-05-27). The actual wheel-sim gate is the `CfgSlots.selection`
   ↔ FireGeometry selection wiring (SP-017 — see the FireGeo wheel-slot rule in
   `vehicle-structural-parity.md` / `dayz-p3d-audit`). Symptom either way: `WheelCountPresent()==0`
   while `WheelCount()==4`, no traction/spin, body sinks/bounces, **no RPT error**. → SP-027 /
   `vehicle-structural-parity.md`.
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
   - THE TRAP: a proxy-split body can have the shell yaw-180 while interior/dash/steering/occlusion
     proxies are correctly sim-aligned (separate build steps → separate transforms). Bulk-rotating
     "the visual side" (shell + all body proxies) breaks the correct ones. Measure each proxy's
     anchor triangle AND content bbox first; rotate ONLY what is actually flipped, and EXCLUDE the
     correct proxies' anchor triangles from the shell rotation (a rotated anchor rotates its
     proxy's content with it).
   - Cheap steering-wheel check: if the `drivewheel_axis` memory pair is near-VERTICAL (Y-dominant
     direction), the wheel sweeps left-right like a wiper instead of rotating in its plane. The axis
     must be ~perpendicular to the rim plane (Z-dominant, some Y).
   Evidence + probes: `MERCEDES_AMGLF_dev\reviews\2026-07-03-fable-review-b1b6-plan.md`.

12. **AddonBuilder `-include` REPLACES its default copy-list — a binarize build with scripts AND
    assets must list `*.paa;*.rvmat` too, or the PBO ships texture-less (white car).**
    (added 2026-07-06, SUB_BRZ binarize experiment) The canonical scripts-only include file
    (`*.c;*.asi;*.anm`) is NOT additive: it becomes the ONLY copy-list, silently dropping every
    `.paa`/`.rvmat` that isn't referenced from config.cpp (SUB_BRZ measured: 47 files dropped —
    28 paa + 19 rvmat, all body swatches — PBO 8.7 MB instead of 11.6 MB, classic white-car on
    dedicated). Use `-include` with `*.c;*.asi;*.anm;*.paa;*.rvmat` for binarize builds, then
    diff the emitted PBO entry list against the source tree BY EXTENSION with explicit allowances
    (config.cpp→config.bin OK, model.cfg baked OK; all `.p3d/.paa/.rvmat/.c` REQUIRED). Wrapper
    with that diff: `C:\Users\<you>\VehicleImport\scripts\rip_binarize_experiment.ps1`.
    Related fact (same experiment, verified against vanilla civiliansedan ODOL): **binarize drops
    the authored ShadowVolume res-1e4 LOD** — an authored shadow LOD only ships via
    MLOD/packonly; if you adopt ODOL, re-check shadows in-game before trusting the budget.

13. **Distance-LOD ladder: a single-visual-LOD import renders its FULL face count at ANY distance —
    author the ladder BEFORE fighting LOD0 decimation.** (added 2026-07-07, SUB_BRZ s25 measured)
    Vanilla civiliansedan ships 5 visual LODs (14,636 → 10,364 → 3,717 → 1,713 → 123 faces); SUB_BRZ
    shipped 1 (231k always) and the admin-preview/spawn freeze did NOT move with dedup (−18.5 MiB) or
    shadow (32k→3.5k) fixes — it is render/face-bound. Distance LODs res 2/3/4 are baked FLAT into the
    main (no proxy refs: proxies of res-0 only render while res-0 renders) from the rip's authored LODs
    (source-game LOD2 = ÷5-8 measured); exclude the cabin from far LODs (vanilla does). Day-1 check: count
    visual LODs vs the control — ≥2 is also the product-spec floor (AC1.4-class). LOD0 decimation stays
    user-gated and becomes a LAST resort, not the first.
    **s26 EXECUTED the ladder (SUB_BRZ deployed, measured) — three corrections to the ÷5-8 estimate above:**
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

21. **Attachment (wheel/door/part) renders FROM the shell's visual-LOD proxy FRAME — an identity frame hides the piece with the sim intact (SUB_BRZ B1, s37).** The engine instances the attached item's model on the proxy of the visual LOD being drawn, oriented by that proxy's frame. py3d `add_proxy(rotation=None)` writes an identity frame: the attached wheel renders rotated ~90 deg, tucked inside the arch — invisible from outside, no raycast hit at the hub, while attach/sim/damage all work (the exact "attached but invisible" signature). Contract, measured against the civiliansedan control (5 wheel proxies in EVERY visual LOD 1/2/3/4/6 + VG + FG): (a) the attachment proxy exists in EVERY visual LOD of the shell, not just the finest; (b) each carries the per-side lateral frame (x>0 `((1,0,0),(0,0,-1),(0,1,0))`, x<0 mirrored) or, for doors, the UNIFORM measured door frame `((-1,0,0),(0,0,1),(0,1,0))`; (c) proxy point flags 63 like the control (identity-frame proxies also had flags 0); (d) `CfgNonAIVehicles` class name must match the proxy file BASENAME case-insensitively (`sub_brz_wheel_ruined.p3d` -> `ProxySUB_BRZ_Wheel_ruined`; a `_destroyed`-named class over a `_ruined` file correlated with a native client CRASH on the damage swap — B5). Mechanical gate: `derive_proxy_frame` of every visual attachment proxy == expected frame, with a negative fixture (identity MUST fail). Diagnosis shortcut: "attached but invisible" is NOT a missing item LOD 0.0 (refuted in-game s37) and NOT a bone/companion issue if anchors+companions match — measure the FRAMES first. RCA: `VehicleImport\work\s37_b1_rca\B1_RCA_findings.md`. Fix verified offline (double-measured); in-game gate pending as of 2026-07-18.

22. **An attached item with its OWN radial actions (CarDoor open/close, hood, trunk) needs a raycast-visible ViewGeometry — point flags 0x02000000 — or the action NEVER appears (SUB_BRZ s38).** The action chain resolves the TARGET by raycast: `ActionCarDoorsOutside.ActionCondition` casts `target.GetObject()` to CarDoor and reads the selections of the hit VG COMPONENT of the ITEM (`actioncardoorsoutside.c:34-46`); a VG whose points carry flags 0x0 is not hit by `RaycastRV(ObjIntersectView)` — the same mechanism as the seat-cube blocker (preflight #4, in-game verified SUB_BRZ s9 + MercedesAMGLF s12) — so the item under the cursor never resolves and the radial is silently filtered, with config, script overrides, slots, bones and anim sources all CORRECT. Contract for the item's VG: (a) componentNN dual-tagged with a selection named EXACTLY what the vehicle's `GetAnimSourceFromSelection` expects (e.g. `doors_driver`); (b) every VG point flags 0x02000000; (c) inward winding (copy a fixed seat cube as control). Symptom signature: attachment renders/attaches/damages fine, `GetCarDoorsState` works, but no open/close radial (and hence no get-in-through-door). Diagnose offline in seconds: census the item's VG point flags vs a working control BEFORE touching config or scripts. Origin: SUB_BRZ s38 D4e; the door fix's own in-game gate pending as of 2026-07-17, but the raycast mechanism is the twice-verified #4 one.

23. **MLOD LODs must be SORTED ascending by resolution once the model carries a multi-visual-LOD ladder — unsorted functional LODs break EVERY special-level lookup at once (LFHeli OH-1 v2, 2026-07-17).** A py3d-assembled MLOD with functional LODs appended out of order (1e13, 6e15, 7e15, 2e15, 1e15) spawned fine with ONE visual LOD, but adding a 0/1/2/3 visual ladder — functional LODs byte-identical, proven by structural diff against the spawning v1 — made the engine fail geometry, view AND fire lookups simultaneously: `Won't simulate, wheel wheel_1_1_damper_land has no proper selection in geometry` + `Action selection 'seat_*' was not found in view or fire geometry level`, with all selections present as strings in the file. That all-levels-at-once signature = broken LOD-table lookup, NOT missing selections; do not chase per-selection fixes. Reference control: RFFS `r22.p3d` (identical config contract: Crew actionSel seat_driver/seat_coDriver, SimulationModule Axles, dampers in Geometry, seats in ViewGeo) ships 4 visual LODs and ALL LODs strictly ascending (0,1,2,3,1e13,1e15,6e15,7e15). Fix authored: `model.lods.sort(key=resolution)` before write, + dump the final file's LOD order (works on ODOL via the debinarizer's `odol_reader`) and assert ascending. **HONEST ATTRIBUTION (in-game 2026-07-17): the confirmed spawn fix was the componentNN dual-tag (preflight #4), NOT the sort.** Sequence measured on the OH-1: sorted-but-seats/hubs-not-dual-tagged STILL failed with the identical "seat_* not found / wheel no proper selection"; adding componentNN dual-tag (with the model also sorted) spawned. dual-tag-WITHOUT-sort was never isolated, so the ascending sort is match-vanilla good-practice (RFFS r22 ships ascending) of UNPROVEN necessity here — do not sell it as the fix. The load-bearing lesson: on a py3d/hand-assembled model, "seat not found / no proper selection in geometry" = the collision selections lack componentNN, full stop (#4). binarize accepts any LOD order silently.

24. **Binarize "Too many vertices" = per-LOD RESOLVED vertex limit counted on EXACT (point, normal, uv) triples — quantize+share normals instead of decimating, and hard-gate the PBO size (LFHeli OH-1 v2, 2026-07-17).** Empirical bounds on one mesh family: LOD0 at 48 170 exact-triple resolved FAILED, 40 399 PASSED (65535 is the ceiling but the engine-side multiplier over your estimator is unknown — keep margin). Near-equal split normals each burn a slot: rounding in your estimator without quantizing the FILE undercounts (a 48k estimate shipped as a fail). Levers in order: (a) quantize normals to 3 decimals + dedupe the vn pool BY VALUE at ingest; (b) merge to ONE averaged normal per position on big smooth pieces (drops each piece to its pos+uv floor; hull went 28 026 → 20 454); (c) only then trim budgets. Attribute first (resolved counted with pos+uv vs pos+nrm tells you which lever pays). Two trap gates: AddonBuilder prints **Build Successful** while packing a ~1.4 KB PBO with the model DROPPED — always fail the build on PBO size < 50% of the previous build; and a fast bisection bench exists without AddonBuilder: run `binarize.exe -always -norecurse <src_dir_with_model.cfg+data> <dst>` directly (Start-Process with -RedirectStandardError to a file; PS 5.1 mangles native 2>&1) and judge by dst-file existence + stderr.

25. **GTA V rip intake (dlc.rpf) — mod RPFs are usually UNENCRYPTED and fully parseable offline; the vehicle skeleton maps 1:1 to DayZ needs (LFHeli HH-60G, 2026-07-18).** Check the encryption dword at offset 12 of the RPF7 header FIRST: `0x4E45504F` ('OPEN', standard for OpenIV-built mod RPFs) = no GTA V install, no NG/AES keys needed. Verified on-disk layout: 16-byte header (`7FPR` magic, entryCount, namesLength, encryption); 16-byte entries discriminated by dword2 (`0x7FFFFF00` = directory, high bit set = resource, else binary); file offsets in 512-byte sectors; binary entry with fileSize==0 = stored verbatim (nested .rpf — recurse in place). A resource on disk = **16-byte RSC7 header IN THE CLEAR** (magic `RSC7`, version — 162 yft / 13 ytd —, sysFlags, gfxFlags) + raw-deflate payload from +16 (`zlib wbits=-15`); scene-standard standalone `.yft`/`.ytd` files are exactly that byte range copied verbatim, so extraction is a copy, not a re-encode. Skeleton conventions worth knowing before Blender (string-scan of the decompressed payload suffices — no FRAG parsing): rotors ship THREE states `rotor_main`/`_slow`/`_fast` (+ `rotor_rear` same) = direct map to the DayZ static+blur rotor pattern; doors `door_[dp]side_[fr]` + `handle_*`; glass as own bones (`windscreen`, `window_*` — glass census for free); `seat_[dp]side_*`, `wheel_lf/rf/lr`, `gear_*` incl. `gear_door_*`; guns/turrets are separate bones (`turret_*`, `weapon_*`) = clean v1 exclusion. Toolchain [IN-VIVO VERIFIED 2026-07-18]: Sollumz 2.8.3 imports binary `.yft` directly (PyMateria/szio, Windows-only) on Blender 5.1 (4.0-5.1 supported), while CodeWalker demands a GTA V game folder on first run — so for OPEN rips the primary chain is own-extractor → Sollumz binary import, CodeWalker only as fallback. Two verified gotchas: (a) **PyMateria's native `.pyd` fails to load from a long path** ("DLL load failed ... filename too long", MAX_PATH) — install Sollumz into a SHORT isolated Blender profile via `BLENDER_USER_RESOURCES=C:\tmp\blp` (also keeps the user's running Blender untouched); headless install = `bpy.ops.extensions.package_install_files(repo="user_default", enable_on_install=True)` + `<addon>.dependencies.install_dependencies(online_access_override=True, optional_dependencies_to_install={"pymateria"})`. (b) **The `.yft` does NOT carry its textures** (they live in sibling `.ytd`), and Sollumz's high-level `gta5.try_load_asset` returns None for a `.ytd`, and its `.yft` import wires 47 named-but-empty image nodes — the FIX is the RAW PyMateria binding: `pmg8 = szio.gta5.native.provider_gen8.pmg8`; `res = pmg8.TextureDictionary.import_rsc(Path(ytd))`; `td = res.result`; `td.textures` is a Map(name→Texture); `tex.export_dds(path)` writes the decoded DDS (PyMateria does all the RSC7+format). ~generic base-game textures (`vehicle_generic_*`) live in GTA's `vehshare.ytd` (not in the mod) and stay missing = pink in Blender, but IRRELEVANT for DayZ (glass gets a vanilla `.rvmat`; the rest are secondary spec/detail overlays). Origin: LFHeli HH-60G intake (`rpf_extract.py`/`ytd_extract.py`/`bl_install.py` in `LFHeli_dev\model_src\HH60G_intake\work\`; textured artist package verified by render).

26. **A rip's BONE NAMES are not its MESH PIECES, and an exclusion REGEX silently classifies content nobody has looked at (LFHeli HH-60G, 2026-07-28).** Two failures of the same import, both invisible offline and both only surfaced by a full in-game cycle. (a) **Regex exclusion.** The day-1 census marked `exclude_v1` with `^(mod_[a-z0-9]+|turret_|weapon_|siren\d|extra_\d|hbgrip_)` to drop "GTA cruft". That swept in `mod_n` (31.598 tris = the whole nose kit: refuelling probe, rescue hoist, radome, nose pods) and `mod_s` (52.550 tris = the entire interior, seats included). The exporter inherited the classification and the vehicle shipped with no nose and a hollow cabin; **94.084 tris of legitimate content, 38% of the source**, lost for ten days without one warning. Rule: **the exclusion list is LITERAL NAMES, one justifying line each — never a regex.** A regex classifies pieces nobody has looked at yet; a literal list forces you to look. (b) **Bone names != mesh pieces.** The string-scan of the skeleton (item 25 above) lists `handle_*` next to `door_*`, so the routing table cited `handle_dside_f/pside_f/dside_r/pside_r`. Measured against the actual LOD levels: those four names exist in **no** level of the `.yft` and in **no** mesh of the imported `.blend` — the skeleton carries bones with no geometry behind them. **Item 25's skeleton-convention list is a hypothesis about names, not a piece inventory**; intersect it with the per-level mesh list before routing anything. Corollary that decides the fix: "the export LOST a piece" and "the export CITED a piece that never existed" look identical from a silent `if obj_by_name(n)` skip and lead to **opposite** repairs (go find it vs delete the row). Gates that would have caught both on day 1, cheap and offline: **SOURCE = the piece set of the richest LOD level, measured** (here `hh60g.yft/High` = 49, set-identical to `hh60g_hi.yft/VeryHigh`); every source piece appears **exactly once** in a routing group or in the literal exclusion list, partition verified by set equality, not by totals; every routed name is **in SOURCE**; and a missing artefact is an **error, never a `[skip]`**. Origin: LFHeli HH-60G, plan v15 Fase 1.1/1.2; measurement in `LFHeli_dev/plans/2026-07-28-hh60g-v15-censo-y-tabla-normativa.md`.

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

## GATE LADDER — imported-model VISUAL correctness (run IN ORDER, cheap -> expensive)

Every imported car (rip->DayZ) passes these gates IN THIS ORDER. Skipping a rung = re-work later:
`gate_car` was built at rung 4 (see-through) while rung 2 (the most BASIC winding check) was missing,
and the user caught the defect in-game (BRZ backlight mixed-winding, 2026-07-01). Rule: before building
a "done" validator, enumerate the failure modes and name which rung covers each — if you can't, don't
code yet. Run cheap topological gates before expensive raycast/in-game ones.

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

## QUICK TRIAGE

| Symptom | Likely cause | Reference |
|---|---|---|
| White / untextured on dedicated, fine in filepatching | binarize left config-only textures out of the PBO | build-packaging-and-debug §1 |
| Wheels spin backwards | `model.cfg` rotation `angle1` sign (re-binarize if ODOL) | build-packaging-and-debug §2-3 |
| Body reads TRANSPARENT / see-through at mid-far distance (NOT black) | a baked distance/far-LOD shipped with its WINDING globally inverted (anti-cross culled from outside) — distinct from black=inverted normals; diagnose by census cross-outward vs the LOD0 control, fix by a global `face.vertices.reverse()` if normals already point outward | preflight #13(d) |
| Wheels roll but don't pivot left/right when steering (only spin, no turn) | roll and steer are TWO separate `model.cfg` animation classes on TWO separate selections — `wheel_X_1` (`sourceAddress=loop`) vs `wheel_X_1_steering` (bounded ±π/2) — front axle only, needs its own `wheel_X_1_steering` bone between the damper and the wheel in `CfgSkeletons`. Declaring `animTurn` in config.cpp alone does nothing without the matching model.cfg class + p3d selection (Landrover itself declares an orphaned `animTurn` on its REAR axle with no matching class — harmless, but proves the point). NOT the same bug/fix as the row below (in-cabin `DrivingWheel` prop). | vehicle-config-and-modelcfg §11-12 |
| Need breakable/cracking glass on gunfire (vanilla-style) | reuse the vehicle's own `DamageZones` + `healthLevels[]` rvmat-swap (same mechanism as body-panel damage), ending in the literal string `"hidden"` at 0 health — NOT a physics/particle shatter system, NOT the 2008-era Arma1/OFP convex-glass-in-FireGeometry pipeline (Czech selection names like `sklo predni L` do not apply to DayZ SA). Cross-confirmed 2026-07-07 in 3 independent real configs (Tyson89/Landrover, DayZ-Expansion UAZ, vanilla-adjacent OffroadHatchback dump). | vehicle-config-and-modelcfg §6b |
| Edited `model.cfg`, behavior unchanged on server | model is ODOL — `model.cfg` is baked, re-binarize | build-packaging-and-debug §2 |
| `Proxy 'crewdriver' not found in view geometry` / get-in broken | crew proxies missing from ViewGeometry LOD | vehicle-structural-parity |
| Player seated sideways / spins >180° on entry / hands off the wheel / wrong rider pose | animation-system, NOT structural — get-in spin, seated pose, rider IK and the `ActionGetInTransport` approach-side yaw belong to **`dayz-animation-pipeline`** (it owns "get-in spin", rider pose). Fix the anim instance / crew-proxy triangle frame there, not the vehicle geometry. | `dayz-animation-pipeline` |
| Wheels / parts missing or misplaced after spawn | LOD / selection / proxy parity gap vs vanilla | vehicle-structural-parity |
| Wheels attached (vanilla preview in inventory) but INVISIBLE in-game while physics work (car drives) | **NOT "remove the proxies" — that lead was FALSE (verified s12).** Vanilla CivilianSedan AND kt_roadkill BOTH carry `sedanwheel` wheel proxies in the **VISUAL LOD** (5 / 4 resp.) + matching `wheel_X_Y` companion selections; the visual-LOD proxy is exactly what RENDERS the attached wheel. The import's were invisible for TWO reasons: (1) py3d `rotation=None` left an **IDENTITY** frame (engine renders the wheel rotated ~90° → out of sight) instead of the vanilla **mirrored-by-side** frame — measure it: x<0 side `((-1,0,0),(0,0,1),(0,1,0))`, x>0 side `((1,0,0),(0,0,-1),(0,1,0))`; and (2) the visual LOD had **NO `wheel_X_Y` companion selections** (only View/Fire did). Fix: reframe each visual-LOD wheel proxy to the vanilla frame **by anchor-x sign** + add a `wheel_X_Y` companion (same 3pts+1face as the proxy, the `fix_wheel_binding.py` pattern, mapped by the SAME centroid rule as View/Fire). Physics-OK ≠ render-OK; the offline `vis.wheel_proxies` count PASS does not prove render. | rip-import §"VISUAL OVERHAUL" / vehicle-structural-parity — SUB_BRZ s12 |
| Engine won't start / can't test driving right after admin/debug spawn | car spawned with **empty fluids** (fuel=0 → engine never starts, looks "broken"). `OnDebugSpawn()` must both `CreateAttachment` the drivetrain (CarBattery/SparkPlug/CarRadiator/wheels) AND `Fill(CarFluid.FUEL, GetFluidCapacity(CarFluid.FUEL))` (+ `CarFluid.COOLANT` if `IsVitalRadiator()`). Base `OnDebugSpawn` only drops loose parts into cargo. Verified pattern: LFQuad `LFQuad.c:176-191`. | vehicle-config-and-modelcfg |
| Engine won't start even WITH fuel + battery + spark plug attached (debug spawn) | a **vital part the car never carries** blocks ignition — vanilla `CheckOperationalRequirements` (`carscript.c:1980`) sets `NO_IGNITER` when a vital GlowPlug is absent (`:2011-2015`), and ALL `IsVital*` default **true** (`:2739-2749`). A petrol car attaching only CarBattery/SparkPlug/CarRadiator (row above) must override `IsVitalTruckBattery`/`IsVitalGlowPlug` → `false` (the vanilla petrol pattern). The un-overridden **GlowPlug** (vital by default) is what blocks — `IsVitalGlowPlug→false` IS the petrol pattern, NOT a "removed requirement"; the car still requires its attached **SparkPlug** as the igniter (`:2004-2008` already satisfied). (`IsVitalEngineBelt→false` is inert — base carscript never checks it.) See preflight #8. Distinct from the empty-fluids row above (a car can have fuel and still not start). Verified: CivilianSedan `civiliansedan.c:358,363` + LFQuad `LFQuad.c:62-80` + SUB_BRZ. | vehicle-config-and-modelcfg |
| Steering wheel **slides/translates toward driver** instead of rotating when steering | `drivewheel_axis` is vertical `[0,1,0]` or on the wrong side — NOT `type=translation` (already rotation). The wheel mesh (often a proxy e.g. `mb_steering`) is skinned 100% to the `drivewheel` bone, so the whole proxy orbits the axis line. Fix: 2 axis mem-points = **at the wheel hub center** + **along the steering-column rake** (Z-dominant, like vanilla CivilianSedan recovered `dir≈(0,±0.515,±0.857)`), never vertical. Offline check: PCA the `drivewheel` rim disc normal / compare to the vanilla rake. | vehicle-config-and-modelcfg |
| `config.cpp, line 0: '.raP'` crash on load (packonly build) | the source `config.cpp` got rapified **in place** (now binary `\0raP`), packonly shipped binary-as-cpp. Cause: running `CfgConvert -bin` directly on the real config.cpp **overwrites the source**. Never CfgConvert the live file — copy to a TEMP first (`CfgConvert -bin -dst tmp.bin tmp.cpp`). Recover: `CfgConvert -txt -dst restored.cpp config.cpp` round-trips the binary back to text. | build-packaging-and-debug |
| Authoring drivetrain / engine / suspension numbers | the full config block | vehicle-config-and-modelcfg |

**Auto-triage in-game (added 2026-06-28):** if the `@DayZ_MCP` bridge is available, the `dayz-mcp-verify` **acceptance ladder** (`references/drive_ladder.py`) drives a car through ordered rungs — spawn → render → get-in → seat → drive → steer — reading ground-truth in-game (raycast solidity, `query_get_in_condition` `first_block`, drive `pos_delta`) and maps each rung's failure to the fixes in THIS table, so a rip→drivable iteration gets a per-rung verdict + named fix instead of eyeballing. Domain invariant worth keeping: **the rungs form a dependency chain — earlier failures MASK later ones, so fix in order** (spawn `componentNN` → winding per-piece → get-in `CrewCanGetThrough` → seat → wheel-sim FireGeo → steer `angle`); never chase a get-in or drive fix while spawn/render is still red. Caveat: get-in diagnosis needs the car adjacent to the player, but a clean drive needs an obstacle-free runway, and `pos_delta≈0` is ambiguous (obstacle vs drivetrain) until re-tested on clear ground. Origin: SUB_BRZ / DayZ-MCP Fase 5.

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

## Rewriting a proxy triangle: translate, never re-orient without fixing normals (SP-093, added 2026-07-26)

Rewriting the 3 points of a proxy triangle to change its ORIENTATION flips the geometric winding
while the stored vertex normals stay as they were. Measured on OH-1: `dot(geometric, stored)` went
from `+1.0` to `-1.0` on all three proxies, and it shipped unnoticed because the parity check only
watched point coordinates. A pure TRANSLATION does not have this problem (winding is preserved;
the same check stayed at `+1.0` across 96 faces).

Rule: any parity/verification of a .p3d edit must assert `dot(geometric_normal, stored_normal) > 0.9`
on every touched face. Byte-level guards are not enough - "only 192 bytes changed, all inside the
authorized coordinate ranges" was TRUE and still shipped inverted normals, because unchanged normals
were exactly the bug.


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

## `autocenter=0` on VISUAL LODs: the misalignment that keeps coming back (SP-097, added 2026-07-27)

This one has now cost cycles on THREE vehicles (LFQuad wheel offset, Mercedes AMG proxies, LFHeli
OH-1 "interior a bit high / tail rotor a bit low"), and every time it was chased as geometry — pose
tweaks, re-centering, transform hunts — when the fix is a PROPERTY.

**The measurement that settles it** (Mercedes, `AI/10_Projects/MercedesAMGLF/research/`
`2026-07-09-proxy-alignment-reusable-codex.md`): the vanilla control proxies
`P:\DZ\vehicles\wheeled\civiliansedan\proxy\prox_int.p3d` and `sedan_engine.p3d` carry
`autocenter=0`; the Mercedes `mb_*` proxies had `lod.properties={}`. With the property absent the
engine re-centres the sub-model on its own bbox, which shows up as a per-piece offset of tens of
centimetres — predicted deltas there were e.g. interior `(0,-0.686,-0.577)`, chassis
`(0,-0.657,-0.011)` m, matching the in-game captures. Sibling case `bug-ledger.md:25` (T9-WHEEL-046):
28 wheel proxies sat at exactly `-0.240 m` in X from their Memory hubs — **FIXED + LIVE PROVEN**,
max proxy→hub error `0.0 m` afterwards.

**The trap is WHICH LOD carries it.** Measured on LFHeli OH-1 (2026-07-27, py3d over the four
deployed p3d): `autocenter=0` was present ONLY on the Geometry LOD (`1e13`) and **absent on every
visual LOD 0/1/2/3**, in the shell and in all three proxied sub-models. A model can therefore look
"correct" in a properties dump and still be re-centred where it matters.

RULES:

1. **Any proxied sub-model, and any host, gets its properties checked PER LOD, not per file.**
   A `autocenter=0` on Geometry says nothing about the visual LODs the player sees.
2. **Calibrate against a vanilla proxy, always.** Debinarize `prox_int.p3d` / `sedan_engine.p3d`
   (`dayz-p3d-debinarizer`) and read which LODs carry the property. Do not infer it from docs.
3. **A misalignment complaint is a PROPERTY hypothesis before it is a geometry hypothesis.** Test
   the cheap one first: adding a property is reversible, moving vertices is not.
4. Related: SP-091 (proxy placement convention, anchors and frames) and SP-093 (rewriting a proxy
   triangle inverts winding). Those cover WHERE the proxy sits; this one covers whether the engine
   moves it afterwards.

Origin: LFHeli OH-1 2026-07-27, promoted the day the cross-project pattern was recognised — the user
pointed at the Mercedes precedent from memory after it had already cost cycles in three projects.

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

### Correction to SP-093 - the `dot > 0.9` rule is for PROXY TRIANGLES ONLY

SP-093 says any parity check of a .p3d edit must assert `dot(geometric, stored) > 0.9` on every
touched face. That is right for proxy triangles and WRONG as a general rule: on a hull authored with
reversed winding on purpose (`FLIP_VISUAL_WINDING = True` in the OH-1 assembler), every visual face
has a negative dot BY DESIGN. Measured on the deployed OH-1: `door_1` = 7227 dots per LOD, **zero**
above 0.9, median `-0.942910`; `door_2` median `-0.939892`. A gate applying SP-093 to migrated
visual faces fails 100% of valid input, and "fixing" it by flipping normals is the regression.

Rule: proxy triangles -> `dot > 0.9`. Migrated/edited visual faces -> equality of the RESOLVED
normal vector against the baseline, corner by corner, within 1e-6.

### Correction to SP-097 - which LODs, and what the property does NOT prove

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

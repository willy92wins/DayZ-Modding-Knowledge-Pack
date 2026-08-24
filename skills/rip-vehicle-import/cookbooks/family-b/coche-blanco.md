# Cookbook B — coche blanco

> Familia B. Los dos bloques se movieron sin reescritura en CAMBIO-1; la separación entre ellos es costura documental.

<!-- MOVED-EXACT source="dayz-vehicles/SKILL.md:554" sha256="B09D90BB657DFDFC4FA85AF17DB0FE6A99DC8A05C8860C9723FF40DDA7700029" -->
12. **AddonBuilder `-include` REPLACES its default copy-list — a binarize build with scripts AND
    assets must list `*.paa;*.rvmat` too, or the PBO ships texture-less (white car).**
    (added 2026-07-06, SUB_BRZ binarize experiment) The canonical scripts-only include file
    (`*.c;*.asi;*.anm`) is NOT additive: it becomes the ONLY copy-list, silently dropping every
    `.paa`/`.rvmat` that isn't referenced from config.cpp (SUB_BRZ measured: 47 files dropped —
    28 paa + 19 rvmat, all body swatches — PBO 8.7 MB instead of 11.6 MB, classic white-car on
    dedicated). Use `-include` with `*.c;*.asi;*.anm;*.paa;*.rvmat` for binarize builds, then
    diff the emitted PBO entry list against the source tree BY EXTENSION with explicit allowances
    (config.cpp→config.bin OK, model.cfg baked OK; all `.p3d/.paa/.rvmat/.c` REQUIRED). Wrapper
    with that diff: `<vehicle-import>\scripts\rip_binarize_experiment.ps1`.
    Related fact (same experiment, verified against vanilla civiliansedan ODOL): **binarize drops
    the authored ShadowVolume res-1e4 LOD** — an authored shadow LOD only ships via
    MLOD/packonly; if you adopt ODOL, re-check shadows in-game before trusting the budget.

<!-- END MOVED-EXACT -->

<!-- MOVED-EXACT source="dayz-vehicles/references/build-packaging-and-debug.md:10" sha256="35A2DC81503DAB1C5FD18B33A10A9C63F095C9C0DF22000DB2BBC31FB3E4BDBE" -->
## 1. Binarize drops config-only assets → white / untextured vehicle on dedicated

**Symptom:** the vehicle renders white / untextured on a dedicated server, but looks correct in
local filepatching. This is the single most common "ships broken" failure for an imported vehicle.
It is **NOT** a `P:\` path problem (see §4).

**Root cause:** AddonBuilder's binarize dependency-tracker only packs the assets that the
**geometry** (`.p3d`) references. Assets declared **only in `config.cpp`** are not tracked and get
left out of the PBO entirely:

- `hiddenSelectionsTextures[]` — the swappable body/color/seat textures. `[LFQuad ✓ config.cpp:290-304]`
- `hiddenSelectionsMaterials[]` — the paint/seat/light `.rvmat`. `[LFQuad ✓ config.cpp:305-319]`
- reflector material-switch props: `frontReflectorMatOn/Off`, `brakeReflectorMatOn/Off`,
  `ReverseReflectorMatOn/Off`, `TailReflectorMatOn/Off`, `dashboardMatOn/Off`. `[LFQuad ✓ config.cpp:320-329]`

The body's paint uses the `color` selection → `B_PAINT.rvmat` + a `*_co.paa`; both are config-only,
so both are missing from the PBO, and the largest visible surface of the vehicle goes **white**.
`[LFQuad ✓: 26 such assets present in the folder were absent from the 5.4 MB binarized PBO; the
18 MB packonly PBO had all of them.]`

**Why filepatching hides it:** filepatching loads the loose files from the mod folder, where every
asset exists. The PBO is only ever exercised on deploy — so the bug is invisible until a real
server loads it.

**Fixes** (either works; pick by whether you need the model protected):

- **packonly** — `AddonBuilder <src> <dst> -prefix=<Mod> -packonly`. Copies the WHOLE folder, no
  binarize. Every asset ships; `.p3d` stays MLOD, `config.cpp` stays text. Bulletproof, simplest,
  zero asset-tracking to get wrong. Cost: the model is debinarizable and the config ships in clear.
- **binarize + `-include`** — pass `-include=<list.lst>` covering `*.paa;*.rvmat` so the loose
  assets are force-copied alongside the binarized geometry. Keeps `.p3d` ODOL (protected) and still
  ships all textures. Cost: you MUST verify the result — a malformed/ignored include list silently
  rescues nothing and you ship the same broken PBO.

**Always verify the PBO before distributing** — §5. A green build log does not mean the assets are in.

<!-- END MOVED-EXACT -->

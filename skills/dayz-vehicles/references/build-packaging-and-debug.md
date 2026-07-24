# Vehicle build, packaging & post-deploy debug

> Packaging and debug lessons from shipping the **LFQuad** (imported Yamaha Banshee quad) to a
> dedicated server. These are the failures that PASS local filepatching and only surface on a
> dedicated box — the worst kind, because the dev loop never sees them.
>
> Provenance: `[LFQuad ✓]` = verified this session against the real mod (config.cpp / model.cfg /
> raw PBO bytes), 2026-06. Line refs are into `P:\LFQuad\config.cpp` and `P:\LFQuad\model.cfg`.

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

## 2. ODOL vs MLOD changes what `model.cfg` MEANS at runtime

This bites whenever animation/skeleton behavior is "fixed in model.cfg" but doesn't change in-game.

- **MLOD** `.p3d` (what packonly ships): the engine reads `model.cfg` from the PBO at runtime.
  Edits to animations/skeleton take effect on the next pack — no re-binarize needed.
- **ODOL** `.p3d` (binarized): `model.cfg` is **BAKED into the model** at binarize time. A loose
  `model.cfg` shipped next to an ODOL is **IGNORED** at runtime. Animation edits require a
  **RE-BINARIZE** to take effect.

**Trap:** a PBO can contain `config.bin` + ODOL `.p3d` **and** a loose `model.cfg` at the same time
(e.g. when you packonly a folder whose `.p3d` files were already binarized). The loose `model.cfg`
is residual and ignored — behavior comes from the ODOL. Do not trust the text file; read the baked
value out of the ODOL (§5). `[LFQuad ✓: shipped PBO had an ODOL body + a loose model.cfg carrying
the corrected angle; the wheel direction the engine used came from the ODOL bake, not the text.]`

## 3. Wheel spin direction lives in `model.cfg` rotation animations

Each wheel rotates via a `class Animations` entry: `type="rotation"`, `source="wheel<pos>"`,
`sourceAddress="loop"`, around the memory axis `wheel_X_X_axis`, mapping `angle0=0 → angle1="rad 360"`.
`[LFQuad ✓ model.cfg:80-92 wheelfrontleft + 3 siblings]`. `config.cpp` only picks WHICH animation each
wheel uses (`Axles → class Wheels → animRotation`), not the direction `[LFQuad ✓ config.cpp:467-519]`.

**Wheels spin backwards → flip the sign on all four:** `angle1 = "rad 360"` → `"rad -360"`.

Before flipping, **read the four `wheel_X_X_axis` memory points** (py3d, Memory LOD): if they are
uniform (e.g. all `(+1,0,0)`), every wheel spins the same way and the fix is symmetric — flip all
four. If one side's axis points the other way, the model is mirror-inconsistent and a blanket flip
will fix one side and break the other. `[LFQuad ✓: 4 axes all (+1,0,0) → uniform → flipped all four.]`

The change only reaches the game after a rebuild — and **re-binarize if the `.p3d` is ODOL** (§2).

## 4. Absolute drive paths in proxies (`P:\`, `Y:\`) are HARMLESS

Imported `.p3d` files routinely carry absolute proxy paths like `y:\lfquad\lfquad_wheel_front` or
`y:\dz\vehicles\wheeled\proxies\crew_driver` (a leftover of whatever drive the model was authored
on). The engine **strips the drive letter** and resolves the proxy by relative name against the
mounted PBOs — they load fine even when that drive does not exist on the machine.

`[LFQuad ✓: the working packonly PBO carried y:\ proxy paths; the Y: drive was not even mounted; the
four wheel proxies and both crew proxies loaded correctly in local test.]`

Do **NOT** chase proxy drive letters when debugging a white/untextured vehicle — that is §1. A drive
letter on a **texture or material** path (not a proxy) is a different story and IS worth fixing.

## 5. Verify a vehicle PBO offline (no game launch)

The PBO format is a flat header — for each entry, an asciiz filename then 5×`uint32`
(packing-method, original-size, reserved, timestamp, data-size) — followed by the concatenated file
data. A ~40-line Python parser gives you full offline verification:

- **Completeness** — list entries, diff against the mod folder. Catches §1 (config-only assets
  missing). `0 missing` is the gate before distribution.
- **Build mode** — `config.bin` + `ODOL` magic on the body `.p3d` = binarized; `config.cpp` + `MLOD`
  = packonly. Tells you which §2 semantics apply.
- **Baked wheel angle** — extract the body `.p3d` entry (raw slice at its data offset) and scan the
  bytes for float32 `±2π` (`rad ±360` = `±6.28319`). `−2π ×4` and `+2π ×0` confirms the wheel-spin
  fix is in the MODEL, not just the loose model.cfg (§2/§3).
- **Stray absolute paths** — scan text/model entries for `[A-Za-z]:\`. Proxy drives are noise (§4);
  a drive letter inside a `.rvmat` texture path or the body's material table is a real defect.

`[LFQuad ✓: this exact offline workflow caught the 26 missing assets, distinguished the 5.4 MB
binarized (broken) PBO from the 18 MB packonly (complete) one, and confirmed the −360 wheel bake —
all without launching DayZ.]`

A reusable parser skeleton lives in the session scratch (`%TEMP%\lfq_*.py` from the LFQuad shipping
session); re-derive it from the format above rather than trusting a stale copy.

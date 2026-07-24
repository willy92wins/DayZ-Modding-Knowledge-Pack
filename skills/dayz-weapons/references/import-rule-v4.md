# REGLA DE IMPORTS v4 + model-path — import & build invariants

Authored 2026-07-07 (F4). `[VERIFIED in-game]` = a real in-game test in a project handoff;
`[VERIFIED-vanilla]` = read off disk; `[UNVERIFIED]` = inferred. Owns the model-path / winding /
serve-binarized invariants that decide whether the build loads and renders. Geometry assembly / LODs /
textures are delegated (`dayz-model-pipeline`, `dayz-texture-pipeline`); packaging to `dayz-pbo-build`.

## REGLA DE IMPORTS v4 `[VERIFIED in-game]` (MK47 v12c)

`A6_MK47_dev\HANDOFF.md:26-32` + `A6_MK47_dev\CLAUDE.md`:

> swap puro (x,y,z)→(x,z,y) det=−1 + normales pseudovector −S·n + `REVERSE_WINDING=False` + **SERVIR
> BINARIZADO**. El binarize invierte el winding (100%) y pasa las normales tal cual; patrón objetivo
> (akm.p3d ODOL): ~70% caras outward, stored·geo ≈ −0.98.

Origin: the Blender weapon frame is X-long (muzzle X−), Z up, Y lateral (right +Y); the swap converts
Z-up Blender to DayZ Y-up. Implemented in `assemble_mk47.py:68-87` (`A6_MK47_dev\CLAUDE.md`).

**Validator:** `C:\Users\<you>\3dmodel\shootout\work\compare_outwardness.py` — PASS band ≥60% outward AND
stored·geo ≤ −0.85. v12c measured 63.2% / −0.88 = PASS. **Do NOT re-iterate winding/normals** — validate
future changes OFFLINE against the AKM ODOL pattern with this validator + the model-path check.

**The swap is RE-DERIVED per weapon, never copied.** SR2M has a DIFFERENT blend frame — long axis = Y,
muzzle Y− (`A6_SR2M\CLAUDE.md` "Decisiones fijas": "Frame del blend: eje largo = Y, muzzle Y−, Z up
(DISTINTO del MK47; el swap de import se re-deriva y se valida con `compare_outwardness.py`)"). Copying
MK47's swap onto SR2M would flip it wrong. Re-derive the frame from the actual blend, re-validate against
the same AKM pattern.

## W-BUILD1 — model-path root cause `[VERIFIED in-game]`

`A6_MK47_dev\HANDOFF.md:9-24` (Hallazgo nº1 — root cause of EVERY v1→v12b failure):

- `config.cpp` `model=` pointed at `\A6_MK47\mk47_body.p3d` (PBO ROOT) but the `.p3d` lives under
  `data\`.
- Builds without `-Clean` dragged a stowaway MLOD `mk47_body.p3d` at the PBO root → THAT was the model
  the engine loaded, invalidating every offline winding/normals measurement (they were reading the raw
  MLOD, not the ODOL). Corollary: the "PackOnly vs binarize" nuance in the empirical winding table
  v6-v11 was spurious — all those builds ran the root MLOD.
- The v12 (`-Clean`) build cleaned the stowaway → `model=` then resolved to nothing → "invisible + crash
  on equip/Tab" (three unrelated hypotheses were refuted with data before the real fix).
- Fix: `model="\A6_MK47\data\mk47_body.p3d"` + `-Clean` rebuild = v12c (first build whose binarized ODOL
  actually rendered). → LL-145.

**W-BUILD1 invariant:** `model=` must point at the real in-PBO path (`data\`), and the build must run
with a clean temp (`-Clean` after structure changes). A check for this was added to `dayz-pbo-build`
(LL-145). It is also codified as an A6_MK47 "invariante cerrada" (`A6_MK47_dev\HANDOFF.md:67-69`): "`model=`
del config apunta a `data\` y se valida contra el contenido del PBO en cada build."

## W-BUILD2 — serve BINARIZED; RETAIL exe for the A6 family `[VERIFIED in-game]`

`A6_MK47_dev\HANDOFF.md:99-105` + `:41`:

- **Serve binarized.** The winding/normals contract above is only correct on the BINARIZED ODOL —
  binarize flips the winding (100%). A diag-pair / MLOD-served build measures the wrong thing. "NO iterar
  winding/normales más; cambios futuros se validan offline contra el patrón AKM."
- **RETAIL exe, not DayZDiag, for A6-family mods.** The A6 weapon pack uses brace-less syntax
  (`override typename GetInputType() return X;` in OpticScripts/WeaponScripts) that the DayZDiag
  strict-compiler REJECTS as an ERROR while retail tolerates it as a FIX-ME warning. LBmaster is also
  diag-incompatible. This is a test-environment note that belongs in `dayz-test-ingame`; it is repeated
  here because it gates whether the weapon can be tested at all. → `dayz-test-ingame`.

The MK47 launcher enforces both: retail exe + `-Clean` + serve the binarized PBO
(`A6_MK47_dev\tools\dayz-test.ps1`).

## Build-order summary (entity-side)

1. Assemble the `.p3d` with the per-weapon swap (re-derived, validated vs AKM ODOL via
   `compare_outwardness.py` — PASS band ≥60% / ≤ −0.85). Geometry assembly / LODs → `dayz-model-pipeline`.
2. `config.cpp` `model="\<Mod>\data\<wpn>.p3d"` — the real in-PBO path (W-BUILD1).
3. Build binarized with a clean temp (`-Clean`) — packaging → `dayz-pbo-build`.
4. Test with the RETAIL exe for A6-family mods (W-BUILD2) → `dayz-test-ingame`.

## Cite-then-verify

The swap direction, the PASS band, and the model-path are all easy to half-remember and each cost the
MK47 project many builds. Re-read the HANDOFF `path:line` and re-run `compare_outwardness.py` before
declaring a winding change good; never trust a swap copied from another weapon.

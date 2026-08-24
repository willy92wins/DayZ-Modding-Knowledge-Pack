# CAMBIO-1 — reglas superadas del carril familia B

> HISTORY ONLY — NO AUTHORITY. Ningún bloque de este fichero se ejecuta ni amplía el allowlist. Cada verdad vigente está en el sitio original de `dayz-vehicles/SKILL.md`; este fichero solo prueba qué texto fue sustituido.

## SP-093 antes de la corrección de alcance

Origen previo a CAMBIO-1: `dayz-vehicles/SKILL.md:1038`. SHA-256 textual LF: `9FBD26B61A888E9BD494AAC1CA99385F7159463D6816832D101548CE2F784D21`.

<!-- SUPERSEDED-EXACT -->
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


<!-- END SUPERSEDED-EXACT -->

## SP-097 antes de separar host, submodelo y prueba runtime

Origen previo a CAMBIO-1: `dayz-vehicles/SKILL.md:1076`. SHA-256 textual LF: `C924E7F4F0816D625A445454F96CE47F59CC70F2696084BCA554579A64D71EFA`.

<!-- SUPERSEDED-EXACT -->
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
   (with an external ODOL→MLOD converter) and read which LODs carry the property. Do not infer it from docs.
3. **A misalignment complaint is a PROPERTY hypothesis before it is a geometry hypothesis.** Test
   the cheap one first: adding a property is reversible, moving vertices is not.
4. Related: SP-091 (proxy placement convention, anchors and frames) and SP-093 (rewriting a proxy
   triangle inverts winding). Those cover WHERE the proxy sits; this one covers whether the engine
   moves it afterwards.

Origin: LFHeli OH-1 2026-07-27, promoted the day the cross-project pattern was recognised — the user
pointed at the Mercedes precedent from memory after it had already cost cycles in three projects.

<!-- END SUPERSEDED-EXACT -->

## Invariante 11 — afirmación factual errónea sobre el cluster Mercedes

Origen previo a CAMBIO-1: `dayz-vehicles/SKILL.md:515`. SHA-256 textual LF: `CF62F532235446D6E8E3C6CA760A737A786CF553D6C713328ED009C44FEA2482`.

<!-- SUPERSEDED-EXACT -->
   - THE TRAP: a proxy-split body can have the shell yaw-180 while interior/dash/steering/occlusion
     proxies are correctly sim-aligned (separate build steps → separate transforms). Bulk-rotating
     "the visual side" (shell + all body proxies) breaks the correct ones. Measure each proxy's
     anchor triangle AND content bbox first; rotate ONLY what is actually flipped, and EXCLUDE the
     correct proxies' anchor triangles from the shell rotation (a rotated anchor rotates its
     proxy's content with it).
<!-- END SUPERSEDED-EXACT -->

## Invariante 13 — estimación ÷5-8 anterior a la medición s26

Origen previo a CAMBIO-1: `dayz-vehicles/SKILL.md:568`. SHA-256 textual LF: `7843FDCBB12F94CF5836AAE90736E93849E2D46AE67880BC419600FABD333053`.

<!-- SUPERSEDED-EXACT -->
13. **Distance-LOD ladder: a single-visual-LOD import renders its FULL face count at ANY distance —
    author the ladder BEFORE fighting LOD0 decimation.** (added 2026-07-07, SUB_BRZ s25 measured)
    Vanilla civiliansedan ships 5 visual LODs (14,636 → 10,364 → 3,717 → 1,713 → 123 faces); SUB_BRZ
    shipped 1 (231k always) and the admin-preview/spawn freeze did NOT move with dedup (−18.5 MiB) or
    shadow (32k→3.5k) fixes — it is render/face-bound. Distance LODs res 2/3/4 are baked FLAT into the
    main (no proxy refs: proxies of res-0 only render while res-0 renders) from the rip's authored LODs
    (source-game LOD2 = ÷5-8 measured); exclude the cabin from far LODs (vanilla does). Day-1 check: count
    visual LODs vs the control — ≥2 is also the product-spec floor (AC1.4-class). LOD0 decimation stays
    user-gated and becomes a LAST resort, not the first.
<!-- END SUPERSEDED-EXACT -->

## Invariante 23 — atribución causal no aislada al orden de LODs

Origen previo a CAMBIO-1: `dayz-vehicles/SKILL.md:673`. SHA-256 textual LF: `2BB6BEC0D6F105C24E6E2E160555EABC5F22072A6356363562B1F12D37D3B3C7`.

<!-- SUPERSEDED-EXACT -->
23. **MLOD LODs must be SORTED ascending by resolution once the model carries a multi-visual-LOD ladder — unsorted functional LODs break EVERY special-level lookup at once (LFHeli OH-1 v2, 2026-07-17).** A py3d-assembled MLOD with functional LODs appended out of order (1e13, 6e15, 7e15, 2e15, 1e15) spawned fine with ONE visual LOD, but adding a 0/1/2/3 visual ladder — functional LODs byte-identical, proven by structural diff against the spawning v1 — made the engine fail geometry, view AND fire lookups simultaneously: `Won't simulate, wheel wheel_1_1_damper_land has no proper selection in geometry` + `Action selection 'seat_*' was not found in view or fire geometry level`, with all selections present as strings in the file. That all-levels-at-once signature = broken LOD-table lookup, NOT missing selections; do not chase per-selection fixes. Reference control: RFFS `r22.p3d` (identical config contract: Crew actionSel seat_driver/seat_coDriver, SimulationModule Axles, dampers in Geometry, seats in ViewGeo) ships 4 visual LODs and ALL LODs strictly ascending (0,1,2,3,1e13,1e15,6e15,7e15). Fix authored: `model.lods.sort(key=resolution)` before write, + dump the final file's LOD order (works on ODOL via the external backend's `odol_reader`) and assert ascending. **HONEST ATTRIBUTION (in-game 2026-07-17): the confirmed spawn fix was the componentNN dual-tag (preflight #4), NOT the sort.** Sequence measured on the OH-1: sorted-but-seats/hubs-not-dual-tagged STILL failed with the identical "seat_* not found / wheel no proper selection"; adding componentNN dual-tag (with the model also sorted) spawned. dual-tag-WITHOUT-sort was never isolated, so the ascending sort is match-vanilla good-practice (RFFS r22 ships ascending) of UNPROVEN necessity here — do not sell it as the fix. The load-bearing lesson: on a py3d/hand-assembled model, "seat not found / no proper selection in geometry" = the collision selections lack componentNN, full stop (#4). binarize accepts any LOD order silently.

<!-- END SUPERSEDED-EXACT -->

## Invariante 24 — techo portable 65535 y veredicto binario

Origen previo a CAMBIO-1: `dayz-vehicles/SKILL.md:675`. SHA-256 textual LF: `665718AC47F3C43380BA0E75923A944F8D138754AA03A2D2D47DDCA0FAD7DE9C`.

<!-- SUPERSEDED-EXACT -->
24. **Binarize "Too many vertices" = per-LOD RESOLVED vertex limit counted on EXACT (point, normal, uv) triples — quantize+share normals instead of decimating, and hard-gate the PBO size (LFHeli OH-1 v2, 2026-07-17).** Empirical bounds on one mesh family: LOD0 at 48 170 exact-triple resolved FAILED, 40 399 PASSED (65535 is the ceiling but the engine-side multiplier over your estimator is unknown — keep margin). Near-equal split normals each burn a slot: rounding in your estimator without quantizing the FILE undercounts (a 48k estimate shipped as a fail). Levers in order: (a) quantize normals to 3 decimals + dedupe the vn pool BY VALUE at ingest; (b) merge to ONE averaged normal per position on big smooth pieces (drops each piece to its pos+uv floor; hull went 28 026 → 20 454); (c) only then trim budgets. Attribute first (resolved counted with pos+uv vs pos+nrm tells you which lever pays). Two trap gates: AddonBuilder prints **Build Successful** while packing a ~1.4 KB PBO with the model DROPPED — always fail the build on PBO size < 50% of the previous build; and a fast bisection bench exists without AddonBuilder: run `binarize.exe -always -norecurse <src_dir_with_model.cfg+data> <dst>` directly (Start-Process with -RedirectStandardError to a file; PS 5.1 mangles native 2>&1) and judge by dst-file existence + stderr.

<!-- END SUPERSEDED-EXACT -->

## attachments[] += como regla incondicional

Origen previo a CAMBIO-1: `dayz-vehicles/SKILL.md:1299`. SHA-256 textual LF: `535A03C3BEE0E5F18C2F04E1C25E02831EB39A93D35F09C62EE0DAE8525954A4`.

<!-- SUPERSEDED-EXACT -->
**2. `attachments[] =` silently removes the inherited vital slots. Use `+=`.**
Config arrays REPLACE on redeclaration. A modded vehicle deriving from a vanilla car inherits
`attachments[]` with `CarBattery`, `SparkPlug`, wheels and so on. Writing

```cpp
attachments[] = {"MyMod_Door_1", "MyMod_Door_2"};      // WRONG
```

drops every inherited slot, so `SpawnUniversalParts()` can no longer attach battery or spark
plug and the vehicle **can never ignite** - `IsVitalCarBattery`/`IsVitalSparkPlug` stay true
forever. The symptom appears far from the cause: you changed doors and the engine stopped
starting. Correct form:

```cpp
attachments[] += {"MyMod_Door_1", "MyMod_Door_2"};     // keeps the inherited slots
```

This is a different failure from T148506 (`enforce-script-reference`), which is about `+=` on a
**string** `inventorySlot` failing silently. Arrays are the case where `+=` is the right tool;
strings are the case where it is not.

Gate both: assert the config uses `+=` for `attachments[]`, and assert every declared part class
appears in the `OnDebugSpawn` path. Origin: LFHeli OH-1 2026-07-28, caught before the in-game
cycle by re-reading the base class the airframe actually inherits from.

<!-- END SUPERSEDED-EXACT -->

## Routing e índice retirados, no archivados como contenido

- Bloque CAMBIO-0 de routing retirado: SHA-256 textual LF `040647625513EEF23726CB36394A0820566D890DF95FB36DE93508EE647D35C7`.
- QUICK TRIAGE retirado: SHA-256 textual LF `97DE93E460BC02CB969895DEB17B4FBCF49BB7C36D90229C031FF36A2FEE9972`.
- Se registran solo los hashes: conservar sus tablas aquí crearía un segundo router/índice y violaría E6.

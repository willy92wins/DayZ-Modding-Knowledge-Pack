# Cookbook B — attachment invisible

> Family B. This body was moved without rewriting in CAMBIO-1; status notes and paths remain exactly as they were in the origin.

<!-- MOVED-EXACT source="dayz-vehicles/SKILL.md:669" sha256="9EAB1E902D741923EDFF9CEDE1469D619DB11CEB5083705BA4D49DAA8727F9D7" -->
21. **Attachment (wheel/door/part) renders FROM the shell's visual-LOD proxy FRAME — an identity frame hides the piece with the sim intact (SUB_BRZ B1, s37).** The engine instances the attached item's model on the proxy of the visual LOD being drawn, oriented by that proxy's frame. py3d `add_proxy(rotation=None)` writes an identity frame: the attached wheel renders rotated ~90 deg, tucked inside the arch — invisible from outside, no raycast hit at the hub, while attach/sim/damage all work (the exact "attached but invisible" signature). Contract, measured against the civiliansedan control (5 wheel proxies in EVERY visual LOD 1/2/3/4/6 + VG + FG): (a) the attachment proxy exists in EVERY visual LOD of the shell, not just the finest; (b) each carries the per-side lateral frame (x>0 `((1,0,0),(0,0,-1),(0,1,0))`, x<0 mirrored) or, for doors, the UNIFORM measured door frame `((-1,0,0),(0,0,1),(0,1,0))`; (c) proxy point flags 63 like the control (identity-frame proxies also had flags 0); (d) `CfgNonAIVehicles` class name must match the proxy file BASENAME case-insensitively (`sub_brz_wheel_ruined.p3d` -> `ProxySUB_BRZ_Wheel_ruined`; a `_destroyed`-named class over a `_ruined` file correlated with a native client CRASH on the damage swap — B5). Mechanical gate: `derive_proxy_frame` of every visual attachment proxy == expected frame, with a negative fixture (identity MUST fail). Diagnosis shortcut: "attached but invisible" is NOT a missing item LOD 0.0 (refuted in-game s37) and NOT a bone/companion issue if anchors+companions match — measure the FRAMES first. RCA: `<vehicle-import>\work\s37_b1_rca\B1_RCA_findings.md`. Fix verified offline (double-measured); in-game gate pending as of 2026-07-18.

<!-- END MOVED-EXACT -->

## The in-game gate above is CLOSED since 2026-08-24

Outside the MOVED-EXACT block, just like the 08-22 note and for the same reason: the
body above was moved without rewriting and its provenance `sha256` certifies
exactly those bytes, status notes included. In-place editing to update a
status breaks the seal, and no check detects it — `packctl validate` does not look inside
`MOVED-EXACT` blocks.

The gate that line 21 leaves "pending as of 2026-07-18" was **closed in game on
2026-08-24**: the attached part renders in its place. Proxy frame correction
is therefore verified in-game, not just offline.

## Per-side frame is tied to ITS control, and the one above is the civiliansedan

Added 2026-08-22, outside the MOVED-EXACT block to avoid breaking its provenance sha.

The constant from (b) —x>0 `((1,0,0),(0,0,-1),(0,1,0))`, mirrored for x<0— **is not universal**:
it was measured on `civiliansedan_mlod`, and holds for geometry derived from that control. The
invariant body itself states this when naming the control, and `dayz-vehicles`
drives it home: "copy the **VANILLA** frame (NOT kt's — its mirror differs because its wheel
geometry differs)" (`references/rip-import.md:684-685`), with general doctrine in
`references/vehicle-structural-parity.md:939`: the frame depends on e1/e2 **and on the
base model orientation**.

Practical consequence, which is where time is lost: **measuring these literals against a
control from another family yields "inverted" without anything being broken.** It happened — a note in the
ledger (SP-156) recorded the constant as measured backwards when comparing it against a
Landrover. Before believing that the constant is wrong:

1. Measure the frame of YOUR control, the one that renders, with `derive_proxy_frame`.
2. Compare against it, not against these literals.
3. If your control has a different geometry, differing is expected, not a bug.

The mechanical fixture accompanying the invariant only requires that the identity frame FAILS.
A fixture that swaps sides and requires failure remains **pending**, and is what
would turn "inverted" into an automatic red rather than a discussion.

## "Attached but invisible" has a SECOND cause, and its check comes BEFORE

Added 2026-09-09, outside the MOVED-EXACT block to avoid breaking its provenance sha.

The case: LFQuad3, attachment proxies to INVENTORY slots (`Shoulder`, `Melee`, `Back`), not
wheels. All three drew NOTHING: neither the item, nor a placeholder, nor a line in the RPT. Six
recipes tested in game touched the slot property, the `hide` animation, `initPhase`, the
proxy index and the LOD; **none touched the class name**. The cause was exactly
rule (d) above. Measured with GunRacks checker: that mod **18/18** conforming, ours
**0/4**; after renaming, **3/3** and the items draw, verified in game.

Two corrections to the block above:

1. **The symptom of (d) is not just the B5 crash.** The same violation also produces
   **silent, total non-render**, a much more expensive failure mode because it leaves no trace to
   investigate: no error, no log, nothing to search for.
2. **The diagnostic shortcut order is reversed for this case.** The block says, when facing
   "attached but invisible", measure FRAMES first. Matching class name with the
   basename of the `.p3d` is a TEXT check on `config.cpp` -- for each class of
   `CfgNonAIVehicles`, `clase.lower() == "proxy" + basename(model).lower()` --, takes seconds
   and has no false positives: **do it before measuring any frame.** Not doing it cost six
   in-game cycles here.

And a third piece of data from the same session: `ProxyVehiclePart` and `ProxyAttachment` are NOT
interchangeable for a slot that needs to display what you attach to it. `ProxyVehiclePart`
(`simulation = "ProxyInventory"`) draws the CLASS model -- measured in game as a
gray placeholder rifle on the rack --; `ProxyAttachment` places the attached ENTITY there.
For a wheel, whose proxy model IS the wheel, the former is correct; for an inventory
slot it is the bug.

## A rack shared by rifles and tools does not align both families (added 2026-09-13)

An attachment proxy draws the item in the local frame of ITS model, with the origin at the point of the
proxy. Vanilla models that fit in `Shoulder`/`Melee` do not share a long axis (census of 120
parts in LFQuad3): **84 of 87 weapons in `CfgWeapons` have it along X; the 3 bows (`Archery_Base`)
and the 33 tools in `CfgVehicles`, along Y**. A rack placed for rifles leaves shovel, pickaxe or
axe crossed 90 degrees, and a viewer painting each model in its frame already shows it: it is not an engine
or viewer bug, it is geometry.

Two solutions, both measured in game:
- **Two proxies on the same slot**, one per family and each on its own bone, with the script hiding
  that of the unattached family (`IsWeapon()`, and `Archery_Base` counts as a tool). Draws: the
  tool rendered in the correct plane. On LFQuad3 it was discarded for aesthetics.
- **Rack for weapons only**: reject in `CanReceiveAttachment` whatever is not `IsWeapon()` or is
  `Archery_Base`. No dedicated slot needed, which would force patching `Rifle_Base` for all
  weapons on the server.

Census trap: debinarized config opens `class cfgWeapons` in lowercase. A parser that
compares root name case-sensitively sees zero weapons and returns "zero exceptions":
require positive controls (three known rifles in X) before trusting the result.

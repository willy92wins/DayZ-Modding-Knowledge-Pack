# The weapon `.p3d` contract — named selections + memory points

Authored 2026-07-07 (F4). Provenance per line: `[VERIFIED in-game]` = confirmed by a real in-game test
recorded in a project handoff; `[VERIFIED-vanilla]` = read directly from vanilla source on disk;
`[UNVERIFIED]` = inferred, not confirmed. This file owns which selections and memory points must EXIST
and cover the right part. Their MOTION is animation → `dayz-animation-pipeline`.

## Named selections — the three that matter for a rifle/SMG

A firearm `.p3d` exposes part **named selections** driven either by the player skeleton (via bone-remap,
→ `bone-remap.md`) or by model.cfg `AnimationSources` locally.

| Selection | Driven by | Provenance |
|---|---|---|
| `bolt` | player bone `Weapon_Bolt` via `AddItemBoneRemap`; motion authored in the weapon-states `.anm` | `[VERIFIED in-game]` SR2M 2026-06-30 |
| `trigger` | player bone `Weapon_Trigger` via `AddItemBoneRemap`; motion from the vanilla player fire/reload anims | `[VERIFIED in-game]` SR2M (bolt moved; trigger remap present) |
| `magazine` | model.cfg `AnimationSources` locally — NOT the player skeleton; avoid double-drive | `[VERIFIED in-game]` SR2M cfg note (`A6_SR2M\...\DayZPlayerCfgBase.c:25` "Magazine still rides model.cfg") |

The names are the wire: `config.cpp` + `model.cfg` reference selections BY NAME, so preserving names
keeps everything wired (R7). Rename a selection and you silently break the remap and the AnimationSource.

## W-SEL1 — verify a selection covers the real part BEFORE trusting it for a bone-remap

`[VERIFIED in-game]` SR2M 2026-06-30 (`A6_SR2M_dev\reviews\2026-06-30-handoff-bolt-trigger-fix.md:8-9`).
The SR2M `bolt` selection was authored onto the **barrel** (X[−0.19,−0.09], in front of the chamber and
the trigger), not the bolt. `AddItemBoneRemap("bolt")` would have slid the barrel — "the bolt didn't
move, not even conceptually." Caught **offline** by comparing the selection centroid against anatomy (a
bolt sits BEHIND the chamber, not in front) with a diagram + a face painter, before burning a test.
After the repaint the reload-verify showed `bolt` at X[−0.07,0.04] (behind the chamber) — right region
(`...bolt-trigger-fix.md:14`).

**The check is cheap and offline:** dump the selection's vertex centroid and bbox from the `.p3d`, and
sanity it against where that part physically sits on the reference weapon. Do this for EVERY selection
that feeds a bone-remap — a mis-authored one passes every syntactic check yet animates the wrong faces.

## Reusable fix flow for a mis-authored selection (SR2M, SP-002-safe) `[VERIFIED in-game]`

`A6_SR2M_dev\reviews\2026-06-30-handoff-bolt-trigger-fix.md:12-17`:

1. **Paint faces → selection** with a face painter HTML (SR2M used `tools/sr2m_selection_painter.html`,
   self-test PASS). The painter + dilation-refiner tooling PATTERN is documented in
   `dayz-animation-pipeline` (`selection-painter-for-actions.md`) — reference it, do not re-derive.
2. **Write selections to the `.p3d` via py3d DIRECTLY, NOT recipe→build.** A recipe→build round-trip
   DROPS selections (SP-002). SR2M wrote 245v `bolt` / 243v `trigger` in `visual_0` this way.
3. **Propagate to the other visual LODs + the shadow buffer by nearest-vertex label** (centroids
   <3.4 mm on SR2M), keep a backup (`...bak_pre_selfix`), and reload-verify the selection moved to the
   right region.
4. **R7:** `config.cpp` + `model.cfg` reference selections BY NAME → preserving names keeps everything
   wired. The `bolt` had NO model.cfg animation on SR2M (it moves via player-anm + remap); `trigger`,
   `magazine` animate via model.cfg AnimationSources.

## Memory points — the vanilla rifle catalog

`[VERIFIED-vanilla, AKM]` from the memory LOD of a debinarized `akm.p3d` (model space, muzzle toward −X,
Y up). **The full catalog table lives in `dayz-animation-pipeline` → `weapon-in-hands.md` — do NOT
duplicate it here.** This file repeats only the entity-side invariants and the parts a memory-point audit
must find:

- `usti hlavne` = muzzle tip (Czech "barrel mouth") — muzzle flash + projectile exit.
- `konec hlavne` = rear of barrel; **must share Y and Z with `usti hlavne`** so the fire line is level.
- `nabojnicestart` / `nabojniceend` = shell ejection path (2 pts, direction up+right+REAR on AKM).
- `bolt_axis` (2 pts) = bolt / charging-handle travel, **parallel to bore**.
- `trigger_axis` (2 pts) = trigger anim axis (lateral ±Z).
- `magazine_axis` / `recoil` (2 pts each) = mag / recoil axes. `[TBD-verify]` exact semantics per the
  anim skill's own note — carry the tag forward.
- `eye` = ironsights / ADS camera anchor (~5 cm above bore on AKM irons; rail height changes the ADS
  camera). The camera anchoring itself is anim; the point's EXISTENCE + rough height is entity.
- `ce_center` / `ce_radius`, `invview`, `boundingbox_min` / `boundingbox_max`.

### W-MEM1 — casing side is weapon-frame-dependent

`[VERIFIED in-game]` SR2M (`...2026-06-30-handoff-bolt-trigger-fix.md:15,53-54`). `nabojnicestart` /
`nabojniceend` set the shell-eject side; the wrong side ejects casings into the receiver. SR2M was on +Z
(wrong), flipped to **−Z**, confirmed correct 2026-06-30. The correct side is frame-dependent — read the
reference weapon's memory LOD, do not assume from another weapon.

### W-MEM2 — a weapon `.p3d` carries NO hand/grip memory points

`[VERIFIED-vanilla]` akm.p3d memory LOD (zero hand selections). Grip is set by the player `.anm` IK pose
+ geometric parity, NOT by points in the weapon. This is the ANIM boundary → `dayz-animation-pipeline`
(`weapon-in-hands.md`). If you find yourself wanting to add a "grip" point to the weapon, stop — the
answer is on the anim side.

## Memory-point sanity invariants (each fired on a real AI-mesh build, MK47 2026-06-11)

All `[VERIFIED-vanilla]`-derived checks against the AKM reference (the anim skill's `weapon-in-hands.md`
carries the measured MK47 failures):

- `usti hlavne` / `konec hlavne` share Y and Z (level bore). MK47 had `konec` 4.6 cm high → 6.3° tilted
  bore.
- `bolt_axis` parallel to bore.
- `magazine_axis` / `recoil` orientation matches the reference family (vertical-ish on AKM; MK47 had
  lateral = 90° off).
- eject direction within ~25° of the reference (MK47: 42° off, no rearward component).
- `eye` height over bore ≈ reference.

The validator that renders + checks these — `scripts/weapon_grip_viewer.py` — lives with the anim skill
(`weapon-in-hands.md`). Reference it for the memory-point audit rather than re-implementing.

## Open / unverified

- `[TBD-verify]` memory-point semantics for `magazine_axis`, `recoil`, `weapon back` carry over from
  `weapon-in-hands.md` — not independently confirmed here.

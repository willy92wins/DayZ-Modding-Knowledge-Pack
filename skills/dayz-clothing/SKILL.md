---
name: dayz-clothing
description: "Use when: clothing mod, worn model, ClothingTypes, chaleco, armadura, la ropa flota/rígida/girada, slot Vest/Body/Armband, NBCHead/NBCTop/NBCPants/NBCBoots/NBCGloves, NBCBag, Waterskin, gas mask filter, headSelectionsToHide, wet clothing. Worn clothing (_m/_f). Not humanoids/rigging: dayz-characters; not proxy triangles: dayz-proxy-align."
---

# DayZ Worn Clothing — the verified pipeline

Distilled from ArmorHneck (2026-08-03): third-party body armor RAR → fully working
worn item, ~6 in-game cycles to isolate three independent SILENT failure modes.
Everything below is in-game verified on DayZ 1.29 diag unless labeled otherwise.
(until 1.29: the worn pipeline below is the 1.29-diag contract.) (since 1.30 Exp: killers #1–#3 and the worn p3d/model.cfg contract still hold. Config-side NBC layering, mask-filter protection, ItemBaseType wet/hide keys, shoe `itemSize`, Waterskin rename, and wash/wet actions: [dayz-1-30-clothing.md](references/dayz-1-30-clothing.md) and ## DayZ 1.30 Exp.)

## THE THREE SILENT KILLERS (check these FIRST, in this order)

A worn item can fail three independent ways, each with ZERO RPT errors. Any one
of them wastes cycles if you chase the others first.

1. **Config must be TEXT in the PBO.** A `config.bin` produced by CfgConvert in
   this environment does NOT register (class absent: `CreateObjectEx` →
   `unknown_type`, invisible to VPP). Pack `config.cpp` as text (packonly);
   every working local mod ships text. Gate: live spawn of the classname —
   never trust static PBO inspection for "it registered".
2. **Worn mesh must be in the canonical clothing frame** (see next section).
   A mesh built facing +Z renders as EXPLODED rigid pieces floating ~1 m above
   the player (each 0/1-weighted plate is transformed by its bone from a
   flipped frame). Fix: rotate 180° about +Y (det=+1 — do NOT touch winding)
   AND swap left*/right* selection pairs in every LOD.
3. **The clothing skeleton must be named `DayzTemporarySkeleton`.** ALL vanilla
   worn clothing compiles with that name (verified via ODOL
   `model_info.skeleton.name` on armbend_dynamic_m + chainmail_m): same 159
   bones and hierarchy as OFP2_ManSkeleton, ONLY the name differs — it is the
   placeholder the engine swaps for the wearer's skeleton at bind time. With
   `skeletonName="OFP2_ManSkeleton"` the engine treats the p3d as having its
   OWN skeleton and never re-binds: the item renders as a rigid block anchored
   above the player, not animating. The community 114-bone OFP2 template fails
   clothing TWICE (bone count and name). Template: `references/model.cfg.template`.

## CANONICAL WORN FRAME (measured on chainmail_m / hoodie_m)

- **-Z = chest/front** · **+X = anatomical LEFT** · **+Y = up** · origin at feet
  (ground Y=0); mesh authored over the vanilla A-pose body.
- Measure orientation with ANATOMICAL COMPONENTS, never a global Z histogram
  (both ±Z masses are ~55/45 on real clothing — the histogram false-negatives a
  180° flip). Reliable signals: front detail components (hoodie drawstrings at
  Z −0.14..−0.07), pelvis/spine weighted centroids (vanilla ≈ Z −0.04..−0.08),
  `left*` selection centroids on +X.
- Torso clothing spans Y ≈ 0.61..1.66 m. Reference garment for overlay checks:
  `dz\characters\tops\chainmail_m.p3d` (body armor, full-body bone set).

## THE CLOTHING CONTRACT (structure of a working wearable)

config.cpp (text!):
- Class inherits a vanilla clothing base for the slot (`Armband_ColorBase`,
  `Chainmail`, vest/top bases...). `model=` the GROUND p3d (`*_g.p3d`).
- `class ClothingTypes { male="..._m.p3d"; female="..._f.p3d"; };`
- `inventorySlot[]` names the worn slots. (until 1.29: NBC pieces listed only the primary slot — `"Headgear"`, `"Body"`, `"Legs"`, `"Feet"`, `"Gloves"`.) (since 1.30 Exp: those NBC bases also list secondary slots `"NBCHead"`, `"NBCTop"`, `"NBCPants"`, `"NBCBoots"`, `"NBCGloves"` so they can coexist with regular clothing.)
- `hiddenSelections[]` per model section; textures/materials arrays aligned.
- (since 1.30 Exp) Type metadata lives on `ItemBaseType`: `headSelectionsToHide[]`, `hideSelectionsByinventorySlot`, `varWetMax`, `temperaturePerQuantityWeight`, `EnvironmentWetnessIncrements`. The config keys existed in 1.29 (parsed on `ItemBase`); 1.30 centralizes them on the type. Dual-slot headgear (bandana/shemag) still uses `hideSelectionsByinventorySlot = 1` plus `simpleHiddenSelections[]`.
- Damage rvmats referenced only from healthLevels must be re-added at pack
  time (AddonBuilder whitelist gap — see dayz-pbo-build SP-155).

Worn p3d (_m/_f):
- Visual LODs skinned by NAMED SELECTIONS in lowercase = bone names
  (leftarm, rightarm, leftforearm, rightforearm, leftupleg, rightupleg,
  neck, pelvis, spine, spine3 — more is better: vanilla also weights
  shoulder/roll/extra transition bones for smooth joints).
- Per-vertex weight sums MUST be 1.0 (vanilla ODOL encodes raw bytes summing
  255). 0/1 plate-rigid weights WORK but articulate coarsely.
- Camo sections: tops/vests use `camoMale` / `camoFemale` alone; ONLY armbands
  carry the 4 complexion variants (camoMale_big_a/b + small_a/b). + `zbytek`.
- Empty Geometry LOD with `autocenter=0` = the vanilla worn pattern (keep it).
- Ground `_g`: normal item p3d (Geometry+mass+Component01, memory points,
  ViewGeo, FireGeo with a penetration rvmat).

model.cfg:
- Copy `references/model.cfg.template` VERBATIM (CfgSkeletons
  DayzTemporarySkeleton, 159 exact pairs, isDiscrete=0) and add one CfgModels
  class per p3d (class name == p3d filename) with
  `skeletonName="DayzTemporarySkeleton"` and its sections.

## BUILD (staged — see ArmorHneck_dev\tools\build.ps1 as template)

1. Stage the mod to %TEMP% (binarize with -addon=P:\ dies on any broken
   third-party config in the tree — "Error 3", names the wrong culprit).
2. Full AddonBuilder pass to binarize the p3d (model.cfg NEXT TO the p3d in
   the staging; ODOL must come out with skeleton name DayzTemporarySkeleton —
   verify with the external ODOL parser, `model_info.skeleton.name`).
3. Assemble pack tree: config.cpp TEXT + model.cfg + ODOL p3d + ALL paa/rvmat
   (including damage/destruct) → AddonBuilder `-packonly` (separate -temp!).
4. Verify PBO entries (classname, NO config.bin, ODOL magic) → deploy by hash.
5. Gate = in-game: spawn (registers?) → equip (worn renders on body?) → move
   (follows animations?). A worn item CANNOT be validated offline-only.

## DIAGNOSIS LADDER (when a worn item misbehaves)

| Symptom | Cause | Verify with |
|---|---|---|
| Item unknown/unspawnable, no RPT error | config.bin in PBO (killer #1) | spawn gate; PBO entry list |
| Worn = rigid block floating ~1 m, rotated, no anim | skeleton name != DayzTemporarySkeleton (killer #3) | ODOL `model_info.skeleton.name` vs vanilla |
| Worn = EXPLODED separate pieces above head | mesh frame flipped 180° (killer #2) | anatomical component Z-signs vs chainmail |
| Fits but plates misaligned (arms/legs) | rip proportions vs canonical bind | alignment viewer (below) or artist pass |
| Body/arms invisible when equipped | expected: torso-slot hide (Body/Vest classes hide skin) | wear it with the intended slot class |
| Coarse joints while moving | 0/1 plate weights, no transition bones | optional weight-smoothing pass |
| Gas mask worn, still takes bio/gas damage | (since 1.30 Exp) GP5/Airborne `Protection` no longer carries biological/dust_particle_breath; those come from attached `GasMask_Filter` | config `class Protection` vs slot `GasMaskFilter` |
| Custom backpack cannot attach NBC pack | (since 1.30 Exp) backpack `attachments[]` missing `"NBCBag"` (not every vanilla bag has it) | compare `TaloonBag_ColorBase` vs `SmershBag` / `ChildBag_ColorBase` |

**Config-vs-p3d bisection (one config-only rebuild, answers "which side is broken"):**
add two test classes — {your slot class + a VANILLA worn p3d (chainmail)} and
{a vanilla clothing class + YOUR p3d}. Vanilla-p3d-OK + custom-p3d-broken in
both classes = the p3d. Both OK = your main class fields. Both broken = pipeline.

**ODOL parity check vs a debinarized vanilla worn** (external ODOL parser):
skeleton name + 159 bones, per-vertex weight sums, sub_skeleton palette (unused
palette entries with 0 weight are normal in vanilla), sections, ModelInfo flags.
SP-034 caveat: vanilla CHARACTER BODY vertex positions decode corrupt, but
clothing worn p3ds decoded fine (armband, chainmail, hoodie all plausible).

## ALIGNMENT VIEWER (fit plates to the body interactively)

`references/alignment_viewer_extract.py` → JSON of mesh + per-region bone
weights + pivots (+ vanilla chainmail ghost as the placement reference);
`references/alignment_viewer_build.py` → self-contained HTML (embedded
three.js UMD): per-region rotation/offset sliders (weight-masked, around the
region pivot), L/R mirroring, front/back/side views, exports an adjustments
JSON. `references/apply_alignment_json.py` applies that JSON to the MLOD
sources with the EXACT same math (three.js Euler XYZ replicated; cross-check
a sample vertex against the live viewer before batch-applying — err ~1e-8).
Works for arbitrary region sets (arm/leg/abdomen masks, combined selections).

## ARTIST HANDOFF (when a human does the fitting — the usual best route)

`references/export_clothing_fbx.py` (Blender headless + py3d): MLOD worn →
FBX with geometry, UVs (V flipped for Blender), the diffuse as PNG
(ImageToPAA paa→png), and the bone weights carried by a 10-bone WEIGHT-CARRIER
armature (FBX drops loose vertex groups — verified: without an armature
deformer the groups vanish on reimport; with it, round-trip keeps all 10
groups at exact weight sums). Axis map DayZ→Blender: `(x, −z, y)` (det=+1;
character stands on Z-up facing +Y; return trip = the fork's standard
`py3d.BLENDER_TO_DAYZ`). ALWAYS verify by reimporting the FBX in a clean
scene (counts + vgroups + weight sums) before shipping.
Package: FBX m/f + PNG + the MLOD p3ds + model.cfg + README from
`references/LEEME-ARTISTA.template.md` (states the three do-not-undo fixes,
the group-preservation rule, and the return flow). Scripts carry the
ArmorHneck paths — adapt per garment.

## PROVENANCE

ArmorHneck case (full trail): `ArmorHneck_dev\CLAUDE.md`, research workspace
`%TEMP%\armorhneck_research_ws\REPORT.md` (Codex dual research: canonical frame
measurement + transform prescription). Cross-refs: dayz-characters §2026-08-03
(same finding, humanoid context), dayz-pbo-build SP-155 (staged build + rvmat
gap), dayz-test-ingame (launch/lifecycle), external ODOL parsing (converter not distributed).

## DayZ 1.30 Exp (build 1.30.164014)

Worn-mesh killers #1–#3, the canonical frame, `DayzTemporarySkeleton`, and the
staged packonly build are unchanged. What 1.30 adds is **config/script contract**
around slots, protection, wetness, and one classname rename. Details and `[EXACT]`
blocks: [dayz-1-30-clothing.md](references/dayz-1-30-clothing.md).

### What changes

- **NBC secondary slots.** Vanilla NBC hood/jacket/pants/boots/gloves list both
  the primary clothing slot and `NBCHead` / `NBCTop` / `NBCPants` / `NBCBoots` /
  `NBCGloves` (`CfgSlots` in `exp\scripts\scripts\config.cpp:3124-3159`).
- **`NBCBag` on some backpacks, not all.** `TaloonBag_ColorBase`, `TortillaBag`,
  `DryBag_ColorBase`, `HuntingBag`, `MountainBag_ColorBase`, `AssaultBag_ColorBase`,
  `Attack2Bag_ColorBase`, `CoyoteBag_ColorBase`, `AliceBag_ColorBase` append
  `"NBCBag"` next to `"Chemlight"`, `"WalkieTalkie"`, `"Backpack_1"`. `SmershBag`
  and `ChildBag_ColorBase` do not. The pack item is scripted as `NBCPack_ColorBase`
  (`Container_Base`); its `CfgVehicles` entry is not in this extract (`[UNVERIFIED]`).
- **GP5 / Airborne protection moved to the filter.** (until 1.29: `class Protection`
  on both masks included `biological = 1` and `dust_particle_breath = 1`.) (since
  1.30 Exp: those two keys are omitted; only `dust_particle_eyes = 1` remains.
  `GetProtectionLevel` reads the attached `GasMask_Filter`. The sealed `GasMask`
  class still has full passive Protection. There is no class named `FilterBase`.)
- **`ItemBaseType`** parses `headSelectionsToHide`, `hideSelectionsByinventorySlot`,
  `varWetMax`, `temperaturePerQuantityWeight`, `EnvironmentWetnessIncrements`.
  `ItemBase.GetHeadHidingSelection` / `HidesSelectionBySlot` / `GetWetMax` read
  the type. Defaults for soaking/drying live on `Inventory_Base`.
- **Shoe `itemSize` width.** Most footwear bases went from width 4 to width 3
  (height also shrank on several boots). `LeatherShoes_ColorBase` stays `{4,2}`.
- **`WaterPouch_*` → `Waterskin_*`** in `CfgVehicles`. Script stub
  `WaterPouch_ColorBase: Bottle_Base{}` remains. Craft: 2 `TannedLeather` +
  `LeatherSewingKit` (−10) → `Waterskin_Natural`. De-craft: empty
  `Waterskin_ColorBase` + blade (−12 HP) → 1 `TannedLeather`.
- **`CraftArmbandFlag.CanDo`** no longer requires `IsEmpty()`; it only rejects a
  flag that is already an attachment. Extra knives (`Jambiya`, `Scimitar`,
  `DonerKnife`, `Akinaka`) are valid tools.
- **Wash head / wet clothing.** New `ActionWashHead*` / `ActionWetClothing*` apply
  per-slot wetness and `GetThermalBiasHandler().Add(-THERMAL_BIAS_WASH_HEAD_DECREMENT)`.
  `[CHANGELOG]` known issue: bottles can still Wash Head while frozen;
  `ActionWashHeadItemContinuous.ActionCondition` does not call `GetIsFrozen()`.
- **Nasdara/Badlands garments** (Kameez, Shalwar, Pakol, DustGoggles, …) have
  scripts under `ItemBase\Clothing\` but no `characters_*` config in this public
  extract (`[UNVERIFIED]` heatIsolation / cargo).

### What breaks for a 1.29 clothing/gear mod

1. NBC clothing that lists only the primary slot cannot layer with regular
   Headgear/Body/Legs/Feet/Gloves.
2. Custom backpacks without `"NBCBag"` cannot take the NBC pack attachment.
3. GP5/Airborne clones with hardcoded `biological` on the mask, or that skip
   `attachments[] = {"GasMaskFilter"}`, will not match 1.30 filter-gated protection.
4. `CreateObject("WaterPouch_Natural")` / recipes naming `WaterPouch_*` fail:
   the config class is `Waterskin_Natural`.
5. Shoe mods still at width 4 occupy more grid than vanilla 1.30 footwear.
6. Dual-slot headgear that omits `headSelectionsToHide[]` /
   `hideSelectionsByinventorySlot` will clip or hide the wrong head selections.

### Migration checklist

- [ ] NBC pieces: `inventorySlot[]` includes the matching `NBC*` slot.
- [ ] Backpacks that should carry the NBC pack: `attachments[]` includes `"NBCBag"`.
- [ ] Filter masks: `attachments[] = {"GasMaskFilter"}`; biological protection
      lives on `GasMask_Filter`, not on the mask `Protection` block.
- [ ] Declare `headSelectionsToHide[]` / `varWetMax` / optional
      `EnvironmentWetnessIncrements` on the clothing class (read via `ItemBaseType`).
- [ ] Replace `WaterPouch_*` with `Waterskin_*` (optional 1.29 alias: empty
      `WaterPouch_Natural: Waterskin_Natural { scope = 1; }` `[DESIGN]`).
- [ ] Recheck shoe `itemSize[]` if you balanced against vanilla width 4.
- [ ] Armband-from-flag: `CanDo` must not assume `IsEmpty()`.
- [ ] Gate remains in-game: spawn → equip → move (killers #1–#3 unchanged).


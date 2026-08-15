---
name: dayz-weapons
description: >
  Author and import the entity side of a DayZ firearm (rifle, SMG or pistol):
  .p3d bolt/trigger/magazine selections and memory points, player-bone remap,
  CfgWeapons/config.cpp inheritance, chamberableFrom, magazines, semi/full-auto
  modes, dispersion/recoil/jam, attachment/optic slots, muzzle/ejection points,
  winding and serve-binarized paths. Use for custom weapon imports,
  CfgWeapons/base selection, bolt or trigger static, deformed mesh, magazine or
  optic not attaching, muzzle/ejection misplaced, chamber/jam, missing fire
  mode, white/invisible weapon or crash on equip; triggers include
  AddItemBoneRemap, Weapon_Bolt, Weapon_Trigger and Mode_*. Grip/hand pose, ADS,
  reload, fire and jam animations belong to dayz-animation-pipeline. Use
  dayz-vehicles/dayz-characters/dayz-model-pipeline for those domains.
---

# DayZ Firearm Modding — the ENTITY side

A custom firearm in DayZ extends the vanilla `Weapon` chain — you do NOT build one from `EntityAI`.
Inheriting the config base of the vanilla/pack weapon whose ammo, mags, recoil, sounds and anims you
want gives all of that for free; you author only the mesh, the `.p3d` part contract, the config deltas,
and the import transform. This skill is the **entity** layer: the `.p3d` selection + memory-point
contract, the bone-remap glue, the CfgWeapons config, and the model-path / winding / serve-binarized
invariants that gate whether the build loads at all.

**FRONTIER — this skill is NOT weapon animation.** Grip / hand pose / ADS line, and the MOTION of the
bolt / trigger / reload / fire / jam-unjam (the `.anm` / `.asi` authoring) belong to
**`dayz-animation-pipeline`** (`weapon-in-hands.md`, `weapon-anim-*`). This skill owns which selections
and points must EXIST and cover the right part, and which selection maps to which bone — not how they
move. The delegation map at the end is the exact split.

Distilled from two closed, in-game-verified projects: **A6_MK47** (AI-mesh 7.62×39 rifle,
`A6_MK47_dev\`, v12c `[VERIFIED in-game]` 2026-06-11) — import + model-path + winding; and **A6_SR2M**
(user-mesh 9×19 SMG, `A6_SR2M\` + `A6_SR2M_dev\`, `[VERIFIED in-game]` 2026-06-30) — bone-remap,
mis-authored-selection detection + repaint, casing side, root-scope `Mode_*`.

## PREFLIGHT — invariants to check BEFORE the first in-game cycle (not after the fail)

Each was won the hard way on one of the two projects. Front-load them offline; full detail behind each
pointer. Firearm test cycles are as expensive as any DayZ rebuild — a preflight pass is nearly free.

1. **W-BUILD1 — `model=` must point at the real in-PBO path (`data\`), built with `-Clean`.**
   `[VERIFIED in-game]` MK47. `config.cpp` `model=` pointed at PBO root while the `.p3d` lived under
   `data\`; a build without `-Clean` dragged a stowaway MLOD at the root → THAT was the model the engine
   loaded, invalidating every offline winding/normals measurement. Fix = `model="\<Mod>\data\<wpn>.p3d"`
   + `-Clean` rebuild. → LL-145, `import-rule-v4.md` §"model-path".
2. **W-BUILD2 — serve BINARIZED; test A6-family mods with the RETAIL exe.** `[VERIFIED in-game]` MK47.
   The winding/normals contract is only correct on the binarized ODOL (binarize flips winding); a
   diag-pair / MLOD-served build measures the wrong thing. Also the A6 weapon pack uses brace-less
   syntax that DayZDiag strict-compile REJECTS → RETAIL exe, not DayZDiag. → `import-rule-v4.md`,
   `dayz-test-ingame`.
3. **W-SEL1 — every bone-remapped selection must SPATIALLY cover its real part before you trust it.**
   `[VERIFIED in-game]` SR2M. The `bolt` selection was authored onto the **barrel** (X[−0.19,−0.09], in
   front of the chamber), not the bolt; `AddItemBoneRemap("bolt")` would have slid the barrel — "the bolt
   didn't move, not even conceptually." Caught OFFLINE by comparing the selection centroid to anatomy (a
   bolt sits BEHIND the chamber). → `p3d-selection-contract.md` §"mis-authored selection".
4. **W-MEM1 — casing eject side is weapon-frame-dependent; read the reference, do not assume.**
   `[VERIFIED in-game]` SR2M. `nabojnicestart`/`nabojniceend` set the shell-eject side; SR2M was on +Z
   (wrong, ejected into the receiver), flipped to −Z, confirmed correct. → `p3d-selection-contract.md`.
5. **W-MEM2 — a weapon `.p3d` carries NO hand/grip memory points.** `[VERIFIED-vanilla]` akm.p3d memory
   LOD. Grip is set by the player `.anm` IK pose + geometric parity, NOT by points in the weapon — that
   is the ANIM boundary. → `p3d-selection-contract.md`, `dayz-animation-pipeline`.
6. **W-CFG1 — `Mode_SemiAuto` / `Mode_FullAuto` must be forward-declared at ROOT config scope, before
   `class CfgWeapons`.** `[VERIFIED in-game]` SR2M. Forward-declaring `Mode_FullAuto` INSIDE `CfgWeapons`
   makes an empty stub without `autoFire=1` → the mode is dropped → weapon stuck in single.
   → `cfgweapons-contract.md` §"root-scope Mode_*".

**Memory-point sanity** (each was a real AI-mesh bug on MK47): `usti hlavne`/`konec hlavne` share Y and
Z (level bore); `bolt_axis` parallel to bore; eject direction within ~25° of the reference; `eye` height
over bore ≈ reference. → `p3d-selection-contract.md` §"memory-point sanity".

## PARITY-FIRST — debinarize the vanilla weapon you inherit, diff against it

The through-line of both projects. Pick the vanilla/pack weapon whose behavior you want (AKM for
AK-pattern, AKS74U/PM73 for an SMG), debinarize it (`dayz-p3d-debinarizer`), read its **memory LOD** and
its **config**, and match: named selections present, memory points shaped the same, config base chosen
for its ammo / mags / recoil / sounds / anims. Every preflight item above falls out of this one diff
instead of error-by-error in-game. → `p3d-selection-contract.md`, `cfgweapons-contract.md`.

## QUICK TRIAGE

| Symptom | Likely cause | Reference |
|---|---|---|
| Invisible / white / crash-on-equip | W-BUILD1 model-path points at root not `data\`, or no `-Clean` (stowaway MLOD) | `import-rule-v4.md` §model-path |
| Edited winding/normals, in-game unchanged | served MLOD / diag not the binarized ODOL (W-BUILD2) | `import-rule-v4.md` |
| Bolt / charging handle doesn't move | selection mis-authored (W-SEL1) OR missing bone-remap OR no `weaponStateAnim` bolt channel | `p3d-selection-contract.md` §mis-authored; `bone-remap.md` |
| Trigger dead on fire | no `trigger`→`Weapon_Trigger` remap (the vanilla fire/reload anims drive that bone) | `bone-remap.md` |
| Casings eject the wrong side | W-MEM1 — flip `nabojnice*` in the memory LOD | `p3d-selection-contract.md` |
| Stuck in single / full-auto missing | W-CFG1 — `Mode_*` declared inside `CfgWeapons` instead of ROOT scope | `cfgweapons-contract.md` §Mode_* |
| Tilted fire line / muzzle flash off-axis | memory-point sanity: `usti`/`konec` not level, or `usti hlavne` misplaced | `p3d-selection-contract.md` §sanity |
| Magazine won't attach / wrong slot | `magazines[]` / `inventorySlot` mismatch vs the mag class | `cfgweapons-contract.md` §attachments |
| Optics / attachment slot won't accept X | `attachments[]` slot name vs the attachment's `inventorySlot`; mount-gated optics | `cfgweapons-contract.md` §attachments |
| **Grip / hands / ADS / rider pose wrong** | NOT this skill — anim | `dayz-animation-pipeline` → `weapon-in-hands.md` |
| **Bolt-slide / reload / fire / jam-unjam MOTION** | NOT this skill — anim (`.anm`/`.asi` authoring) | `dayz-animation-pipeline` → `weapon-anim-*` |

## DELEGATION MAP — ANIM vs ENTITY, and the generic-pipeline hand-offs

| Concern | Owner |
|---|---|
| `.p3d` selection + memory-point CONTRACT (which must EXIST, cover the right part), casing side | **THIS skill** → `p3d-selection-contract.md` |
| `AddItemBoneRemap` — WHICH selection → WHICH bone, selection-covers-part precondition | **THIS skill** → `bone-remap.md` |
| CfgWeapons: inheritance, chamber/mag/muzzle/optics slots, fire modes, recoil, dispersion, jam CONFIG | **THIS skill** → `cfgweapons-contract.md` |
| Model-path / REGLA DE IMPORTS / winding / serve-binarized | **THIS skill** → `import-rule-v4.md` |
| Grip / hand pose / ADS line, `AddItemInHandsProfileIK` semantics, player skeleton bones | `dayz-animation-pipeline` → `weapon-in-hands.md`, `player-skeleton.md` |
| The weapon-states `.anm` (bolt slide, bullet eject), fire/reload/chamber **action anims**, unjam loop | `dayz-animation-pipeline` → `weapon-anim-*`, `weapon-in-hands.md` |
| The memory-point catalog table + the grip viewer `weapon_grip_viewer.py` | `dayz-animation-pipeline` → `weapon-in-hands.md` (referenced, not copied) |
| Geometry assembly / LODs / procedural textures | `dayz-model-pipeline` |
| Texture / rvmat zones | `dayz-texture-pipeline` |
| `.p3d` collision / action / path audit | `dayz-p3d-audit` |
| Enforce Script (`modded class`, config-script side) rules | `enforce-script-reference` |
| PBO packaging / binarize | `dayz-pbo-build` |
| In-game build/deploy/launch + auto-verify | `dayz-test-ingame` (+ `dayz-mcp-verify`) |

## CITE-THEN-VERIFY

Weapon config fields and named selections are easy to half-remember, and the vanilla firearm hierarchy
is NOT a straight line (`RifleBoltFree_Base` extends `Rifle_Base`, but `BoltActionRifle_Base` and
`Pistol_Base` extend `Weapon_Base` DIRECTLY — see `cfgweapons-contract.md`). Before writing a class name,
field, or selection, grep it in vanilla (`P:\scripts\4_world\entities\firearms\`, a debinarized vanilla
`.p3d`) or the cited references, and keep the provenance labels the references use: `[VERIFIED in-game]`
(a real in-game test in a project handoff) vs `[VERIFIED-vanilla]` (read off disk) vs `[UNVERIFIED]`
(inferred, not confirmed). Anchor every new weapon lesson to a real mod with `path:line`, never memory.

## AMMO CLASSIFICATION SERVER-SIDE (added 2026-08-13, LFPowerGrid turret)

Reading a cartridge ROLE (pistol / intermediate / full-power / shell / arrow) at runtime — needed by any
system that must behave differently per ammo class WITHOUT a classname whitelist (turrets, per-class
ballistics, loot logic, scaling that must also work for modded weapons):

- `enum CartridgeType { None=0, Pistol=1, Intermediate=2, FullPower=3, Shell=4, Arrow=5 }` —
  `P:\scripts\4_world\entities\itembase\magazine\magazine.c:3-11` `[VERIFIED-vanilla]`
- The class lives on the MAGAZINE/pile config, not on CfgAmmo:
  `g_Game.ConfigGetInt("CfgMagazines " + pileType + " iconCartridge")` — `magazine.c:32`
  `[VERIFIED-vanilla]`. Guard with `ConfigIsExisting("CfgMagazines " + pileType)` first (`magazine.c:29`);
  a modded pile that omits the key yields 0 (`None`), so choose an explicit fallback band rather than
  trusting that zero.
- **Two paths, and the guard covers only one.** The constructor PRE-loads `Magazine.m_AmmoData` inside
  `if (!g_Game.IsDedicatedServer())` (`magazine.c:45-64`), but the static accessor
  `Magazine.GetAmmoData(classname)` fills the map LAZILY with **no** such guard (`magazine.c:117-132`)
  `[VERIFIED-vanilla]` — so it does work server-side. The real caveat is allocation, not availability: the
  first miss constructs an `AmmoData` (`:123-125`), so never take that path inside a hot loop. Read it once
  on an attachment event and cache it yourself. (Corrects an earlier version of this entry that claimed the
  map is never populated on a dedicated server.)
- **Gate on `IsAmmoPile()` when you mean loose rounds, not magazines.** `Object.IsAmmoPile()` returns false
  by default (`3_game\entities\object.c:577-580`) and `Ammunition_Base` overrides it to true
  (`4_world\entities\itembase\magazine\ammunitionpiles.c:27-30`) `[VERIFIED-vanilla]`. Detachable magazines
  do NOT declare `iconCartridge`, so any per-cartridge-class logic must reject them first or it silently
  classifies every mag as `None`.
- **`iconCartridge` coverage is NOT total in vanilla.** `Ammunition_Base` sets it to 0, and at least five
  concrete `scope=2` ammo classes resolve to 0/`None` (CupidsBolt, RPG7_HE, RPG7_AP, LAW_HE, GrenadeM4).
  Any band table needs an explicit policy for `None`, and must separate "0 declared" from "key absent" —
  what `ConfigGetInt` returns for a missing path is undocumented, so probe with `ConfigIsExisting` first.
- **You can read binarized vanilla configs without a `P:\DZ` tree**: run Mikero/BI `CfgConvert -txt` over
  the installed game's PBOs (`…\Steam\steamapps\common\DayZ\Addons\weapons_ammunition.pbo`,
  `weapon_magazines.pbo`). This is how the coverage numbers above were established on a machine with no
  unpacked vanilla tree — reach for it before declaring a config claim unverifiable.
- Cartridge -> ammo type for the damage system: `AmmoTypesAPI.MagazineTypeToAmmoType(magType, out ammoType)`
  — `P:\scripts\3_game\global\ammotypes.c:14`, used by vanilla in `weapon_base.c:848` `[VERIFIED-vanilla]`.
  Do not hand-roll a `CfgMagazines <t> ammo` lookup.
- A cartridge damage profile is readable BEFORE firing:
  `ConfigGetFloat("CfgAmmo " + ammoType + " DamageApplied Health damage")` (also `Blood damage`,
  `Shock damage`) — `P:\scripts\4_world\entities\dayzplayerimplementfalldamage.c:261-263`
  `[VERIFIED-vanilla]`. This is how a mod caps absurd modded ammo without a whitelist.
- `iconCartridge` is nominally a UI icon field reused as the cartridge class: confirm per-pile coherence
  against a debinarized config before shipping balance that depends on it. `[UNVERIFIED]`

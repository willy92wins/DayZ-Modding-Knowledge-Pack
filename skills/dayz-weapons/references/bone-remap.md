# Bone-remap — weapon selection → player skeleton bone

Authored 2026-07-07 (F4). `[VERIFIED in-game]` = a real in-game test in a project handoff;
`[VERIFIED-vanilla]` = read off disk; `[UNVERIFIED]` = inferred. This file owns WHICH selection maps to
WHICH bone and the precondition that the selection covers the part. The bone's MOTION is animation →
`dayz-animation-pipeline`.

## The API `[VERIFIED-vanilla]`

`scripts\3_game\dayzplayer.c:252`:
```
proto native int AddItemBoneRemap(string pItemClass, array<string> pBoneRemap);
```
The engine comment + example is at `:245-250`:
```
//! add bone remap for item class
//! pBoneRemap has always 2x N members
//! bone in item's P3D first, bone in Character skeleton second
//! array<string> remap = { "bolt", "Weapon_Bolt", "magazine", "Weapon_Magazine", "trigger", "Weapon_Trigger" };
//! AddItemBoneRemap("class", remap);
```
So the array is a FLAT list of `{weaponSelection, playerBone, ...}` pairs — weapon selection first, player
skeleton bone second.

Companion IK-pose binder, `scripts\3_game\dayzplayer.c:243` `[VERIFIED-vanilla]`:
```
proto native int AddItemInHandsProfileIK(string pItemClass, string pAnimInstanceName,
    HumanItemBehaviorCfg pBehaviorCfg, string pIkPoseAnim, string pWeaponStates = "");
```
The 5th arg (`pWeaponStates`) is the weapon-states `.anm` that drives `Weapon_Bolt`. **That anim is
authored on the ANIM side** (`dayz-animation-pipeline` → `weapon-in-hands.md`, `weapon-anim-*`); the
entity side only supplies its path in the registration.

Both are called from a `modded class ModItemRegisterCallbacks` override of a `Register*` method, after
`super`.

## Real remap — SR2M `[VERIFIED in-game]`

`A6_SR2M\scripts\4_World\Entities\ManBase\DayZPlayer\DayZPlayerCfgBase.c:26-27`:
```
array<string> partRemap = { "bolt", "Weapon_Bolt", "trigger", "Weapon_Trigger" };
pType.AddItemBoneRemap("A6_SR2M_Base", partRemap);
```
Registered inside `override void RegisterFireArms(DayZPlayerType pType, DayzPlayerItemBehaviorCfg
pBehavior)` (`:7`), after `super.RegisterFireArms(...)` (`:9`), alongside the
`AddItemInHandsProfileIK("A6_SR2M_Base", ..., "A6_SR2M/animations/w_sr2m_states.anm")` call (`:19`) that
binds the weapon-states anim.

- `Weapon_Bolt` is driven by the weapon-states `.anm` (the 5th `AddItemInHandsProfileIK` arg).
- `Weapon_Trigger` is driven by the vanilla player fire/reload anims (SR2M note `:22-24`: "the vanilla
  player fire/reload anims drive Weapon_Trigger ... verified animated in p_erc_fire_*_ras and
  p_erc_reload_action_pm73_ras. Without the remap the trigger is a dead no-op on fire").
- `magazine` is deliberately absent from the remap — it rides model.cfg AnimationSources (`:25`), to
  avoid double-drive.

Note: the SR2M handoff (`2026-06-30-handoff-bolt-trigger-fix.md:13`) cites the remap at `:22-23`, an
earlier line number; the live file has it at `:26-27`. Cite the live file.

## When a remap is / isn't needed

- **Needed** only when the weapon's bolt/trigger must be animated by the PLAYER skeleton — i.e. you
  inherit vanilla fire/reload/chamber anims that move `Weapon_*`. `[VERIFIED in-game]` SR2M.
- **Not needed** when a part animates purely via model.cfg AnimationSources (that path is used for the
  magazine — avoid double-drive).

**Precondition (learned the hard way, W-SEL1):** the selection must actually COVER the part (→
`p3d-selection-contract.md`) AND the weapon must have a `weaponStateAnim` whose bolt channel exists.
SR2M kept `weaponStateAnim=AKS74U` states (`A6_SR2M\config.cpp:823`) with `onlyIfBoltIsOpen=1` (`:947`,
per the handoff) — the state machine was ready; only the remap + a correct selection were missing
(`...bolt-trigger-fix.md:17`).

## Bone-remap is an established, production-standard pattern `[VERIFIED-vanilla, third-party]`

Not an SR2M invention — the A6 weapon pack and IMPWMOD remap per weapon class:

- `A6_Weapons\WeaponScripts\WeaponScripts\4_world\Entities\ManBase\DayZPlayer\DayZPlayerCfgBase.c:267-271`
  remaps each shotgun class (`A6_Mossberg_590_Base`, `A6_KSG_Base`, `A6_MP153_Base`, `A6_Spas12_Base`,
  `A6_Benelli_Base`) to named remap arrays `ShotgunBoneRemapNew` / `SemiShotgunBoneRemapNew`.
- `IMPWMOD` (`IMPWMODPart2\Scripts\4_World\Pistol\AnimationsPistol.c:60,63`) uses the same shape.

(These third-party `path:line` are from the F4 research spec, `[VERIFIED-vanilla, third-party]` there —
grep the file before quoting the exact remap arrays if you build on them.)

## Boundary reminder

`AddItemBoneRemap` is entity-config GLUE: which selection maps to which bone, and verifying the selection
covers the part. The bone's MOTION — the weapon-states `.anm` for the bolt, the action anims for
fire/reload/chamber/jam-unjam, `AddItemInHandsProfileIK` IK-pose semantics, the player skeleton bones
(`Weapon_Root`, `RightHand_Dummy`, `LeftHandIKTarget`) — all belong to `dayz-animation-pipeline`
(`weapon-in-hands.md`, `player-skeleton.md`, `anim-graph.md`).

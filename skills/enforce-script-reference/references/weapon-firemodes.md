# Weapon fire modes (single / burst / full-auto)

Extracted from `enforce-script-reference/SKILL.md` on 2026-07-07 (F3 sectioning).

Config-side fire-mode inheritance for DayZ weapons: when to inherit vs override `class SemiAuto`/`FullAuto`, and the `Mode_*` root-scope forward-declaration trap (SP-031). Cross-ref: SP-038 troubleshooting row in `dayz-pbo-build`.

---

## (added 2026-06-26) Fire modes on DERIVED weapons: inherit, do not redeclare over a base that already defines them

On a weapon inheriting from ANOTHER weapon that ALREADY defines its modes (`class SemiAuto`/`class FullAuto`), DO NOT redeclare the mode subclasses with an explicit parent (`class FullAuto: Mode_FullAuto`): that re-derives from the abstract base `Mode_*` and the engine may be left with 1 valid mode. In-game symptom: the weapon only fires semi, the mode key (default X) does not cycle, and the mode name does not appear in the HUD. Instead:
- Inherit the modes without touching them (do not declare `modes[]` or the subclasses), or
- Override WITHOUT parent: `class FullAuto { soundSetShot[]=...; reloadTime=...; }` → MODIFIES the inherited one (preserves its autofire), only changes what you specify.

Redeclaring WITH `: Mode_*` is only correct when inheriting from `Rifle_Base` (which does not predefine the modes), as the AKs of the A6 pack do (a6_ak_config.cpp:354-390).

Verified mechanism (vanilla 1.2x, `P:\scripts`):
- Mode count = config `modes[]` + valid subclasses.
- Mode switch = native input `IsFireModeChange()` (default X key) → `GetWeaponManager().SetNextMuzzleMode()` (`4_world\entities\dayzplayerimplement.c:1088`).
- Mode name in HUD = `GetCurrentModeName()` (`4_world\classes\weapons\weaponmanager.c:1335` → `5_mission\gui\itemactionswidget.c:584`); empty string = engine sees 1 mode.
- Player animation profile (`pType.AddItemInHandsProfileIK(class, .asi, behaviorCfg, ik.anm, weaponStates.anm)` in `dayzplayercfgbase.c:408+`) and `behaviorCfg` (`SetFirearms`/`SetPistols`/`SetToolsOneHanded` → `ItemBehaviorType`, def. `dayzplayercfgbase.c:167-239`) DO NOT control mode count; but registering a weapon with `RegisterOneHanded` does make it behave like a one-handed tool (no selector).

Anti-confabulation: a "protected base" whose `config.bin` "cannot be read" must be VERIFIED by de-rapifying with `CfgConvert -txt` before assuming it. A6_PP19 case (2026-06-26): config.bin de-rapifies completely and already had `modes[]={"SemiAuto","FullAuto"}` — the "protected/single-mode" assumption was false.

### `Mode_*` (Mode_SemiAuto/FullAuto/Burst) belong in ROOT scope, NOT inside `class CfgWeapons` (SP-031, added 2026-06-29)

Failure case distinct from the previous one (not redeclaring the subclass, but misdeclaring the base `Mode_*`). Vanilla mode classes (`WeaponMode_Base`{autoFire=0}, `Mode_SemiAuto`, `Mode_Burst`, `Mode_FullAuto: Mode_SemiAuto` with `autoFire=1`) are defined in **ROOT scope** of config (vanilla `bin.pbo` config.cpp:260/273/307/310), BEFORE `class CfgWeapons` (l.347) — they are **siblings** of CfgWeapons, not inside it. Forward-declaring `class Mode_FullAuto;` **inside `class CfgWeapons`** creates an empty `CfgWeapons.Mode_FullAuto` that **shadows** the real one → any `class FullAuto: Mode_FullAuto` inherits that stub **without `autoFire`** → engine discards the mode → single-mode weapon (semi only, no selector or mode name in HUD).

- **How to recognize it**: weapon with correct `modes[]={"SemiAuto","FullAuto"}` that in-game ONLY fires semi, despite byte-identical config to another that does cycle. Deceiving: CfgConvert/binarize DOES NOT complain (a forward-decl is a valid external) and de-rap looks perfect. Truth is in vanilla source (`bin.pbo`), not in comparing mod configs.
- **Fix**: forward-declare `class Mode_SemiAuto;` / `class Mode_FullAuto;` in **ROOT scope** (above `class CfgWeapons`, just like `class OpticsInfoRifle;`). Then `class FullAuto: Mode_FullAuto` resolves to the real one (`autoFire=1`). Diagnostic discriminator: a clone inheriting from an ALREADY-resolved base weapon cycles, while your base referencing `Mode_*` does not → isolates the cause to `Mode_*` resolution (NOT to the model).

Origin: A6_SR2M bug#10, 2026-06-28, confirmed in-game (~12 cycles without the lesson). Cross-ref: SP-038 (troubleshooting row in `dayz-pbo-build`), LL-174, `20_Knowledge/dayz-weapon-config-crossproject.md` INV-W1.

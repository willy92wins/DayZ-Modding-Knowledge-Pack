---
title: DayZ weapon config — cross-project invariants
type: knowledge
domain: dayz-weapons
status: living
created: 2026-06-28
source: A6_SR2M bug#10 (full-auto), A6_MK47, A6 pack RE
---

# DayZ weapon config — cross-project invariants

Reusable gotchas for authoring/​debugging a DayZ firearm's `config.cpp` (CfgWeapons).
Load this before building or fixing any custom weapon. Pairs with
[[dayz-animations-creatures-weapons]] (anim side) and the `enforce-script-reference`,
`dayz-pbo-build`, `dayz-test-ingame` skills.

## INV-W1 — Fire-mode classes `Mode_*` live at ROOT config scope, NOT inside `CfgWeapons`

**The single most expensive weapon gotcha found so far (~12 rebuild cycles, A6_SR2M bug#10).**

The vanilla fire-mode base classes are defined at the **root** of the config, as siblings
of `CfgWeapons`, NOT inside it. Verified in `<DayZ>\dta\bin.pbo` → `config.cpp`:

```
class WeaponMode_Base { autoFire = 0; burst = 1; ... }      // l.260
class Mode_SemiAuto: WeaponMode_Base { ... }                // l.273
class Mode_Burst: Mode_SemiAuto { burst = 3; }              // l.289
class Mode_FullAuto: Mode_SemiAuto { autoFire = 1; ... }    // l.307  <- autoFire=1 lives here
class OpticsInfoDefault { ... }                             // l.317  (also root)
class Muzzle_Base { ... }                                   // l.328  (also root)
class CfgWeapons { ... }                                    // l.347  <- only NOW does CfgWeapons open
```

**The bug**: forward-declaring `class Mode_FullAuto;` **inside** `class CfgWeapons {}` creates a
*new empty* `CfgWeapons.Mode_FullAuto` that **shadows** the real root-scope one. Any
`class FullAuto: Mode_FullAuto` in the weapon then inherits the empty stub → **no `autoFire`**
→ the engine treats FullAuto as invalid and **drops the mode** → the weapon is single-mode:
fires only semi, no mode name in the HUD, the fire-select key does not cycle.

**Why it's a silent trap**: `CfgConvert`/binarize does **NOT** error (a forward-decl is a valid
"external" reference); the de-rapped `.bin` looks perfect; and the weapon's config can be
byte-identical to another weapon that DOES cycle. You cannot find this by diffing mod configs —
the truth is in the vanilla `bin.pbo`.

**The fix**: forward-declare `class Mode_SemiAuto;` / `class Mode_FullAuto;` at **ROOT scope**
(above `class CfgWeapons`, exactly like `class OpticsInfoRifle;` is). Then
`class FullAuto: Mode_FullAuto` resolves to the real vanilla class → `autoFire=1` → full-auto +
selector work.

```cpp
class OpticsInfoRifle;
class Mode_SemiAuto;      // ROOT scope — references the real vanilla class
class Mode_FullAuto;      // ROOT scope
class CfgWeapons
{
    class Rifle_Base;        // weapon bases DO go inside CfgWeapons (that IS their scope)
    class A6_PP19_Base;      // ditto
    class MyWeapon_Base: A6_PP19_Base   // or Rifle_Base
    {
        class SemiAuto: Mode_SemiAuto { soundSetShot[]={...}; };  // now resolves -> works
        class FullAuto: Mode_FullAuto { soundSetShot[]={...}; };  // autoFire=1 inherited
    };
};
```

Corollary: weapon/optics/muzzle bases (`Rifle_Base`, `<Pack>_Base`, `OpticsInfoRifle`) ARE
forward-declared inside `CfgWeapons` correctly — that is their real scope. Only the `Mode_*`
(and `WeaponMode_Base`, `OpticsInfoDefault`, `Muzzle_Base`) are root-scope. Get the scope right
per class.

## Diagnostic method that cracked it (reuse for "weapon won't cycle / acts single-mode")

1. **Isolate in-game with a clone**, don't keep diffing configs. Add a throwaway weapon that
   inherits a KNOWN-WORKING base verbatim (e.g. `class MyTest: A6_PP19_Base { scope=2; model=<yours>; }`)
   and one that mirrors your suspect structure. Spawn both + the real weapon, press X on each.
   - Clone of working base cycles, yours doesn't → it's YOUR config, not the model/engine.
   - This is what proved the model was innocent (user's instinct was right) and pointed at
     `Mode_*` resolution rather than any visible field.
2. **When mod-vs-mod config diff comes up identical, go to the vanilla source** (`ExtractPbo -P`
   on `dta\bin.pbo`) — the asymmetry was scope, invisible in any mod's de-rap.
3. A throwaway weapon inheriting a `scope=0` base with **no `model=`** crashes on spawn — give
   every test weapon an explicit `model=`.

## INV-W2 — Test path for a weapon whose deps are a script-sloppy third-party pack

If the weapon depends on a separate `@<pack>_deps` (base classes in a deployed PBO), and that
pack's scripts warn on retail but are fatal on DayZDiag:
- **DayZDiag** server dies before binding (strict compile of the sloppy pack).
- **Retail client + `-filePatching`** crashes on connect (`CDPInitServer`/`CDPCreateClient`,
  null read at 0x0).
- **Use `-Retail -NoFilePatching`** — the PBO already carries your change, filePatching is
  unneeded, and dropping it avoids both. This is also the production-like config.

```
dayz-test.ps1 -Mod <Mod> -Mode all -Retail -NoFilePatching -BaseMods "@CF;@Dabs Framework;@VPPAdminTools;@<pack>_deps"
```
(Also captured in `dayz-test-ingame` SKILL.md, added 2026-06-28.)

## INV-W3 — Inheriting from another concrete weapon vs a vanilla base

Inheriting `MyWeapon_Base: SomePack_Weapon_Base` (another mod's weapon) DOES work and inherits
its already-resolved modes/slots/FSM — but you must forward-declare that base inside CfgWeapons
AND it must be in `requiredAddons`. Pure inheritance (no `Mode_*` reference of your own) sidesteps
INV-W1 entirely (that's why A6_SR2M's `ModeTest` cycled). The moment you re-declare the fire
subclasses to customize (e.g. sounds), INV-W1 applies — so fix the `Mode_*` scope first.

## Related
- [[skill-patches-pending]] — SP-031 (this Mode_* scope lesson, destined for `enforce-script-reference` + `dayz-pbo-build`).
- [[dayz-animations-creatures-weapons]] — weapon animation side (RTM/asi, fire/chamber/reload anims).
- A6_SR2M HANDOFF (LIVE-STATE) — `...\A6_SR2M_dev\HANDOFF.md`.

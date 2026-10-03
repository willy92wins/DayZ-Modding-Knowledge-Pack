# Deep-dive verified additions

Extracted from `enforce-script-reference/SKILL.md` on 2026-07-07 (F3 sectioning).

Source-verified vs vanilla v1.24 + real mods: recipes/crafting (PluginRecipesManager), ComponentEnergyManager, action-system additions, damage pipeline, player internals/sync.

---

## Deep-dive verified additions (added 2026-06-06)

> Source-verified vs vanilla v1.24 + real mods (digests in
> `LF_RollingStone_dev/research/deep-dive-2026-06-06/`). Line refs +-3.

### Recipes / crafting (PluginRecipesManager)
- `MAX_NUMBER_OF_INGREDIENTS = 2` (`recipebase.c:1`) — recipes are physically limited to 2
  ingredients; `MAXIMUM_RESULTS = 10`.
- Real API: `InsertIngredient(index, classname)` — **`AddIngredient` does not exist**.
- The official typo is `RegisterRecipies()` (double i). Mod pattern verified in production:
  `modded class PluginRecipesManagerBase { override void RegisterRecipies() { super.RegisterRecipies(); RegisterRecipe(new MyRecipe); } }`.
- Base `CanDo()` rejects ingredients with attachments — override required for recipes with
  weapons/items with attachments. An override copies `ingredients[0]` and `[1]` to locals first
  and does not call `super.CanDo`: measured in game, the array read back after that call held the
  same item in both slots and the craft cancelled itself (`SKILL.md`, Override Rules, rule 42).
- `m_ResultToInventory`: only `-1` (to inventory) works; the swap branch `>= 0` is commented out in
  `SpawnItems`. `SetIsCacheable` does not exist.
- (through 1.29: `TransferItemProperties` on a result with `m_ResultReplacesIngredient` could overwrite health from `m_ResultInheritsHealth`). (since 1.30 Exp: `TransferItemProperties(ingr, res, true, true, false, false)` is called — `transfer_health = false` — `RecipeBase.c:353`. Signature: `MiscGameplayFunctions.c:269`. New: `PluginRecipesManager.GetRecipeClassName(int recipe_id)` at `:84`, not at `:54`.)

### ComponentEnergyManager (quick facts)
- `MAX_SOCKETS_COUNT = 4` hardcoded (`componentenergymanager.c:77`).
- `energyStorageMax` is optional: if you only define `energyAtSpawn`, that value acts as maximum.
- The energy chain is recursive: `ConsumeEnergy()`/`CanWork()` traverse sources upwards
  (safety limit 500 cycles).
- `OnSwitchOn/Off` fires on BOTH sides; `OnWorkStart/OnWork/OnWorkStop` server/SP only — real
  synchronization goes through `SetSynchDirty`.
- `compatiblePlugTypes` absent in config => the socket accepts all plugs.

### Action system (additions)
- `AddAction(typename)` in `SetActions()` registers a **global singleton per input type** — there are no
  per-instance actions nor dynamic runtime registration.
- `CCTCursor` measures from the hit-pos of the `ObjIntersectView` raycast (requires View Geometry LOD);
  `CCTObject` measures from target's `GetPosition()`. If an action does not appear and the model lacks
  ViewGeo, check the LOD first (skill `dayz-physics-engine`, truth #2).
- (through 1.29: CCT distance from hit-pos / `GetPosition()`, often via Head bone). (since 1.30 Exp: `CCTCursor` and `CCTCursorInherited` also measure `MiscGameplayFunctions.GetPlayerHeadPosition` — stance height, not Head bone — `CCTCursor.c:27-28`, `CCTCursorInherited.c:28-32`, `MiscGameplayFunctions.c:748`. New `CCTLiquid` (ctor `:37`) replaces vanilla use of `CCTWaterSurfaceEx` in fill/drink/wash. `Can()` of a custom CCT does not change signature.)

### Damage pipeline (quick facts)
- `ProcessDirectDamage(damageType, source, componentName, ammoName, modelPos, damageCoef, flags)`
  (`object.c:1134`) — `componentName` is the name of the **DamageZone**, not the model component.
- `damageCoef` multiplies the base damage of CfgAmmo. In vanilla TransportHit, coef = speed in m/s
  (`entityai.c:4086-4116`).
- `EEHitBy` is server-only; `EEHitByRemote` runs on the client that hit. `DecreaseHealth` bypasses
  the pipeline (no EEHitBy/animation/bleeding).
- `ProcessIndirectDamage` DOES NOT exist in script; radius damage =
  `DamageSystem.ExplosionDamage(source, null, ammo, pos, DamageType.EXPLOSION)` (`damagesystem.c:25`).
- `GetProtectionLevel` covers only DEF_BIOLOGICAL/DEF_CHEMICAL (hazmat) — ballistic absorption of
  clothing is C++/config, with no script API.
- Full TransportHit flow line by line: skill `dayz-physics-engine`,
  `references/dano-transporthit.md`.

### Player internals — sync (quick facts)
- Stamina syncs via **SyncJuncture** (`SJ_STAMINA`), not via `SetSynchDirty`
  (`staminahandler.c:797-805`). `EStaminaModifiers.PUSH_CAR` and `EStaminaConsumers.PUSH` already exist
  (`estaminamodifiers.c:13`) -> `DepleteStaminaEx` for custom costs.
- `eModifierSyncIDs`: only 7 bits used — `0x80..0x80000000` free for custom synchronized
  modifiers (`emodifiers.c:3-17`).
- `PlayerStatsPCO` uses POSITIONAL indices: a custom stat via `modded PlayerStatsPCO_current`
  needs index > 10 or it corrupts serialization (`playerstatspco.c:312`).
- Custom modifiers: `ModifiersManager` `Init()` hardcodes the list -> pattern
  `modded class ModifiersManager`. `CfgAgents` DOES NOT exist: agents are script classes registered
  in `PluginTransmissionAgents`.

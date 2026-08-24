# Deep-dive verified additions

Extracted from `enforce-script-reference/SKILL.md` on 2026-07-07 (F3 sectioning).

Source-verified vs vanilla v1.24 + real mods: recipes/crafting (PluginRecipesManager), ComponentEnergyManager, action-system additions, damage pipeline, player internals/sync.

---

## Deep-dive verified additions (added 2026-06-06)

> Source-verified vs vanilla v1.24 + real mods (digests in
> `LF_RollingStone_dev/research/deep-dive-2026-06-06/`). Line refs +-3.

### Recipes / crafting (PluginRecipesManager)
- `MAX_NUMBER_OF_INGREDIENTS = 2` (`recipebase.c:1`) — las recetas se limitan fisicamente a 2
  ingredientes; `MAXIMUM_RESULTS = 10`.
- API real: `InsertIngredient(index, classname)` — **`AddIngredient` no existe**.
- El typo oficial es `RegisterRecipies()` (doble i). Patron mod verificado en produccion:
  `modded class PluginRecipesManagerBase { override void RegisterRecipies() { super.RegisterRecipies(); RegisterRecipe(new MyRecipe); } }`.
- `CanDo()` base rechaza ingredientes con attachments — override necesario para recetas con
  armas/items con accesorios.
- `m_ResultToInventory`: solo `-1` (a inventario) funciona; la rama swap `>= 0` esta comentada en
  `SpawnItems`. `SetIsCacheable` no existe.

### ComponentEnergyManager (quick facts)
- `MAX_SOCKETS_COUNT = 4` hardcodeado (`componentenergymanager.c:77`).
- `energyStorageMax` es opcional: si solo defines `energyAtSpawn`, ese valor actua como maximo.
- La cadena de energia es recursiva: `ConsumeEnergy()`/`CanWork()` recorren las fuentes hacia arriba
  (limite de seguridad 500 ciclos).
- `OnSwitchOn/Off` dispara en AMBOS lados; `OnWorkStart/OnWork/OnWorkStop` solo server/SP — la
  sincronizacion real va por `SetSynchDirty`.
- `compatiblePlugTypes` ausente en config => el socket acepta todos los plugs.

### Action system (additions)
- `AddAction(typename)` en `SetActions()` registra un **singleton global por tipo de input** — no hay
  acciones por instancia ni registro dinamico en runtime.
- `CCTCursor` mide desde el hit-pos del raycast `ObjIntersectView` (exige View Geometry LOD);
  `CCTObject` mide desde `GetPosition()` del target. Si una accion no aparece y el modelo no tiene
  ViewGeo, revisa el LOD primero (skill `dayz-physics-engine`, truth #2).

### Damage pipeline (quick facts)
- `ProcessDirectDamage(damageType, source, componentName, ammoName, modelPos, damageCoef, flags)`
  (`object.c:1134`) — `componentName` es el nombre de la **DamageZone**, no el componente del modelo.
- `damageCoef` multiplica el danio base del CfgAmmo. En TransportHit vanilla, coef = velocidad en m/s
  (`entityai.c:4086-4116`).
- `EEHitBy` es server-only; `EEHitByRemote` corre en el cliente que golpeo. `DecreaseHealth` bypasea
  el pipeline (sin EEHitBy/animacion/bleeding).
- `ProcessIndirectDamage` NO existe en script; danio en radio =
  `DamageSystem.ExplosionDamage(source, null, ammo, pos, DamageType.EXPLOSION)` (`damagesystem.c:25`).
- `GetProtectionLevel` cubre solo DEF_BIOLOGICAL/DEF_CHEMICAL (hazmat) — la absorcion balistica de la
  ropa es C++/config, sin API script.
- Flujo TransportHit completo linea a linea: skill `dayz-physics-engine`,
  `references/dano-transporthit.md`.

### Player internals — sync (quick facts)
- La stamina sincroniza por **SyncJuncture** (`SJ_STAMINA`), no por `SetSynchDirty`
  (`staminahandler.c:797-805`). `EStaminaModifiers.PUSH_CAR` y `EStaminaConsumers.PUSH` ya existen
  (`estaminamodifiers.c:13`) -> `DepleteStaminaEx` para costes custom.
- `eModifierSyncIDs`: solo 7 bits usados — `0x80..0x80000000` libres para modifiers custom
  sincronizados (`emodifiers.c:3-17`).
- `PlayerStatsPCO` usa indices POSICIONALES: un stat custom via `modded PlayerStatsPCO_current`
  necesita indice > 10 o corrompe la serializacion (`playerstatspco.c:312`).
- Modifiers custom: el `Init()` de `ModifiersManager` hardcodea la lista -> patron
  `modded class ModifiersManager`. `CfgAgents` NO existe: los agentes son clases script registradas
  en `PluginTransmissionAgents`.

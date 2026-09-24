# DayZ 1.30 Exp — clothing / gear contract (build 1.30.164014)

Companion to `SKILL.md` § DayZ 1.30 Exp. Worn-mesh killers, canonical frame, and
`DayzTemporarySkeleton` are unchanged; this file is the config/script delta.

Line numbers are from the files opened under `exp\` (and `stable-1.29\` where a
1.29 contrast is stated). Digest L/E/F line numbers were **not** copied.

## NBC secondary slots

(until 1.29: `NBCHoodBase.inventorySlot[] = {"Headgear"}` only —
`stable-1.29\characters_headgear\DZ\characters\headgear\config.cpp:3968`.)
(since 1.30 Exp: each NBC clothing base lists the primary slot **and** a dedicated
NBC slot. Gloves follow the same pattern; digest L omitted them.)

```cpp
// [EXACT] exp\characters_headgear\DZ\characters\headgear\config.cpp:3961
	class NBCHoodBase: Clothing
	{
		scope = 0;
		displayName = "$STR_CfgVehicles_NBCHoodBase0";
		descriptionShort = "$STR_CfgVehicles_NBCHoodBase1";
		model = "\DZ\characters\headgear\NBC_Hood_g.p3d";
		inventorySlot[] = {"Headgear","NBCHead"};
```

```cpp
// [EXACT] exp\characters_tops\DZ\characters\tops\config.cpp:4054
	class NBCJacketBase: Clothing
	{
		scope = 0;
		displayName = "$STR_CfgVehicles_NBCJacketBase0";
		descriptionShort = "$STR_CfgVehicles_NBCJacketBase1";
		model = "\DZ\characters\tops\NBC_Jacket_g.p3d";
		inventorySlot[] = {"Body","NBCTop"};
```

```cpp
// [EXACT] exp\characters_pants\DZ\characters\pants\config.cpp:2460
	class NBCPantsBase: Clothing
	{
		scope = 0;
		displayName = "$STR_CfgVehicles_NBCPantsBase0";
		descriptionShort = "$STR_CfgVehicles_NBCPantsBase1";
		model = "\DZ\characters\pants\NBC_Pants_g.p3d";
		ContinuouActions[] = {"AT_WRING_CLOTHES"};
		inventorySlot[] = {"Legs","NBCPants"};
```

```cpp
// [EXACT] exp\characters_shoes\DZ\characters\shoes\config.cpp:1717
	class NBCBootsBase: Clothing
	{
		scope = 0;
		displayName = "$STR_CfgVehicles_NBCBootsBase0";
		descriptionShort = "$STR_CfgVehicles_NBCBootsBase1";
		model = "\DZ\characters\shoes\NBC_Boots_g.p3d";
		inventorySlot[] = {"Feet","NBCBoots"};
```

```cpp
// [EXACT] exp\characters_gloves\DZ\characters\gloves\config.cpp:605
	class NBCGloves_ColorBase: Clothing
	{
		scope = 0;
		displayName = "$STR_cfgvehicles_nbcglovesbase0";
		descriptionShort = "$STR_cfgvehicles_nbcglovesbase1";
		inventorySlot[] = {"Gloves","NBCGloves"};
```

`CfgSlots` names (ghost icons + display strings):

```cpp
// [EXACT] exp\scripts\scripts\config.cpp:3124
	class Slot_NBCBag
	{
		name = "NBCBag";
		displayName = "#STR_CfgVehicles_NBCPack_Colorbase0";
		ghostIcon = "set:dayz_inventory image:back";
	};
	class Slot_NBCHead
	{
		name = "NBCHead";
		displayName = "#STR_CfgVehicles_nbchoodbase0";
		ghostIcon = "set:dayz_inventory image:headgear";
	};
	class Slot_NBCTop
	{
		name = "NBCTop";
		displayName = "#STR_CfgVehicles_nbcjacketbase0";
		ghostIcon = "set:dayz_inventory image:body";
	};
	class Slot_NBCGloves
	{
		name = "NBCGloves";
		displayName = "#STR_CfgVehicles_nbcglovesbase0";
		ghostIcon = "set:dayz_inventory image:gloves";
	};
```

`Slot_NBCPants` (`:3148-3153`) and `Slot_NBCBoots` (`:3154-3159`) follow the same four-field shape.

## NBCBag on backpacks — not universal

(until 1.29: `TaloonBag_ColorBase.attachments[] = {"Chemlight","WalkieTalkie","Backpack_1"}`
— `stable-1.29\characters_backpacks\DZ\characters\backpacks\config.cpp:43`.)
(since 1.30 Exp: nine backpack bases append `"NBCBag"`. Digest L claimed every
vanilla backpack; that is false.)

**Have `"NBCBag"`:** `TaloonBag_ColorBase:43`, `TortillaBag:125`, `DryBag_ColorBase:440`,
`HuntingBag:535`, `MountainBag_ColorBase:620`, `AssaultBag_ColorBase:1239`,
`Attack2Bag_ColorBase:1323`, `CoyoteBag_ColorBase:1407`, `AliceBag_ColorBase:1484`
(all in `exp\characters_backpacks\DZ\characters\backpacks\config.cpp`).

**Do not:** `SmershBag:703` (`{"Chemlight","WalkieTalkie"}`), `ChildBag_ColorBase:764`
(`{"Chemlight","WalkieTalkie","Backpack_1"}`), plus courier/improvised/leather/sling/drysack
bases that never gained the slot.

```cpp
// [EXACT] exp\characters_backpacks\DZ\characters\backpacks\config.cpp:36
	class TaloonBag_ColorBase: Clothing
	{
		displayName = "$STR_cfgVehicles_TaloonBag_ColorBase0";
		descriptionShort = "$STR_cfgVehicles_TaloonBag_ColorBase1";
		model = "\dz\characters\backpacks\taloon_g.p3d";
		debug_ItemCategory = 9;
		inventorySlot[] = {"Back"};
		attachments[] = {"Chemlight","WalkieTalkie","Backpack_1","NBCBag"};
```

The attachable pack is scripted as `NBCPack_ColorBase : Container_Base` with
`CanDisplayAttachmentCargo` forced false
(`exp\scripts\scripts\4_World\Entities\ItemBase\Gear\Containers\containers.c:83-92`).
No `class NBCPack` appears in extracted `exp\**\config.cpp`. `[UNVERIFIED]`:
inventorySlot of the pack item (expected `"NBCBag"`), cargo size, model path.

## Gas masks and `GasMask_Filter`

There is **no** class `FilterBase`. Protection for cartridge masks is
`GasMask_Filter` (`exp\gear_consumables\DZ\gear\consumables\config.cpp:1943`) plus
script `GasMask_Filter : ItemBase`.

(until 1.29: GP5 `Protection` was `biological = 1; dust_particle_breath = 1; dust_particle_eyes = 1;`
at `stable-1.29\characters_masks\DZ\characters\masks\config.cpp:451-456`. Airborne
matched at `:517-522`. Digest L's "1.29 was biological = 0.25" is false.)

(since 1.30 Exp: GP5 and Airborne **omit** `biological` and `dust_particle_breath`;
they keep `dust_particle_eyes = 1`. They do not write `= 0`.)

```cpp
// [EXACT] exp\characters_masks\DZ\characters\masks\config.cpp:452
		class Protection
		{
			dust_particle_eyes = 1;
		};
```

Same four-line `Protection` block on `AirborneMask` at `:516-519`. Both classes
declare `attachments[] = {"GasMaskFilter"}` (`GP5GasMask:418`, `AirborneMask:482`).

The sealed `GasMask` (no filter slot) still has full passive protection:

```cpp
// [EXACT] exp\characters_masks\DZ\characters\masks\config.cpp:83
		class Protection
		{
			biological = 1;
			chemical = 1;
			dust_particle_breath = 1;
			dust_particle_eyes = 1;
		};
```

Filter item:

```cpp
// [EXACT] exp\gear_consumables\DZ\gear\consumables\config.cpp:1963
		class Protection
		{
			biological = 1;
			chemical = 1;
			dust_particle_breath = 1;
		};
```

Runtime: with a filter attached, `GetProtectionLevel` returns the filter's level
except `DEF_DUST_PARTICLE_EYES` which stays 1.0 on the mask. Without a filter it
falls through to `super` (config Protection on the mask).

```c
// [EXACT] exp\scripts\scripts\4_World\Entities\ItemBase\Clothing\GP5GasMask.c:13
	override float GetProtectionLevel(int type, bool consider_filter = false, int system = 0)
	{
		if (IsDamageDestroyed())
			return 0.0;

		ItemBase filter = ItemBase.Cast(FindAttachmentBySlotName("GasMaskFilter"));
		if (filter)
		{
			if (type == DEF_DUST_PARTICLE_EYES)
				return 1.0;

			return filter.GetProtectionLevel(type, false, system);
		}

		return super.GetProtectionLevel(type, consider_filter, system);
	}
```

`AirborneMask.c:18-33` is the same override. `[DESIGN]`: a custom cartridge mask
must attach `GasMaskFilter` and must not rely on mask-level `biological`.

## ItemBaseType — hide selections and wetness

`ItemBaseType` is new in 1.30 (no `ItemBaseType.c` under `stable-1.29`). The
**config keys** `headSelectionsToHide` and `hideSelectionsByinventorySlot` already
existed in 1.29 (`ItemBase.c:178-187` parsed them on the instance). 1.30 moves
the parse onto the type:

```c
// [EXACT] exp\scripts\scripts\4_World\Entities\ItemBaseType.c:105
		if (ConfigIsExisting("headSelectionsToHide"))
		{
			m_HeadHidingSelections = new TStringArray();
			ConfigGetTextArray("headSelectionsToHide", m_HeadHidingSelections);
		}
		
		m_HideSelectionsBySlot = false;
		if (ConfigIsExisting("hideSelectionsByinventorySlot"))
			m_HideSelectionsBySlot = ConfigGetBool("hideSelectionsByinventorySlot");
```

`varWetMax` is read at `ItemBaseType.c:71`. `temperaturePerQuantityWeight` at
`:117-119`. `EnvironmentWetnessIncrements` Soaking/Drying maps at `:121-137`.

Instance accessors:

```c
// [EXACT] exp\scripts\scripts\4_World\Entities\ItemBase.c:4518
	array<string> GetHeadHidingSelection()
	{
		return ItemBaseType.Cast(GetEntityType()).m_HeadHidingSelections;
	}
	
	bool HidesSelectionBySlot()
	{
		return ItemBaseType.Cast(GetEntityType()).m_HideSelectionsBySlot;
	}
```

`InitItemVariables` now copies `m_VarWet` from `itemBaseType.m_VarWetInit`
(`ItemBase.c:162-166`). Dual-slot vanilla example (`Bandana_ColorBase`):

```cpp
// [EXACT] exp\characters_headgear\DZ\characters\headgear\config.cpp:1599
		inventorySlot[] = {"Headgear","Mask"};
		rotationFlags = 16;
		weight = 120;
		itemSize[] = {3,1};
		ragQuantity = 1;
		varWetMax = 1.0;
		heatIsolation = 0.4;
		repairableWithKits[] = {5,2};
		repairCosts[] = {30.0,25.0};
		headSelectionsToHide[] = {"Clipping_BandanaHead","Clipping_BandanaFace"};
		hideSelectionsByinventorySlot = 1;
		hiddenSelections[] = {"camoGround","camoMale_H","camoMale_M","camoFemale_H","camoFemale_M"};
		simpleHiddenSelections[] = {"hide_headgear","hide_mask"};
```

`Shemag_ColorBase` uses the same hide-by-slot pattern at `:1695-1707`.
`NBCHoodBase` sets `headSelectionsToHide[] = {"Clipping_NBC_Hood"}` (`:3978`)
without `hideSelectionsByinventorySlot`.

Default soaking/drying increments (inherited unless a class overrides
`class EnvironmentWetnessIncrements`) sit on `Inventory_Base`:

```cpp
// [EXACT] exp\dz\DZ\data\config.cpp:2533
		class EnvironmentWetnessIncrements
		{
			class Soaking
			{
				parentWithLiquid = 1.0;
				wetParent = 0.005;
			};
			class Drying
			{
				player = 0.00029;
				ground = 0.00011;
				playerHeatSource = 0.0035;
				groundHeatSource = 0.0018;
			};
		};
```

## Shoe `itemSize` (width 3, with exceptions)

Digest L: "all shoes and boots rescaled to width 3". **False as a universal.**
`LeatherShoes_ColorBase` is still `{4,2}`
(`exp\characters_shoes\DZ\characters\shoes\config.cpp:1489`).
`NBCBootsBase` is `{2,2}` (`:1726`); `FeetCover_Improvised` is `{2,2}` (`:1853`).

Measured 1.29 width-4 → 1.30 width-3 on the same line of `shoes\config.cpp`
(height often shrank too):

| Class | 1.29 | 1.30 | line (both trees) |
|---|---|---|---|
| `AthleticShoes_ColorBase` | `{4,2}` | `{3,2}` | 389 |
| `HikingBoots_ColorBase` | `{4,4}` | `{3,3}` | 498 |
| `HikingBootsLow_ColorBase` | `{4,3}` | `{3,2}` | 595 |
| `Wellies_ColorBase` | `{4,4}` | `{3,4}` | 702 |
| `WorkingBoots_ColorBase` | `{4,3}` | `{3,3}` | 813 |
| `JungleBoots_ColorBase` | `{4,4}` | `{3,3}` | 925 |
| `DressShoes_ColorBase` | `{4,2}` | `{3,2}` | 1039 |
| `MilitaryBoots_ColorBase` | `{4,4}` | `{3,3}` | 1151 |
| `CombatBoots_ColorBase` | `{4,4}` | `{3,3}` | 1265 |
| `JoggingShoes_ColorBase` | `{4,2}` | `{3,2}` | 1379 |
| `Sneakers_ColorBase` | `{4,2}` | `{3,2}` | 1646 |
| `Ballerinas_ColorBase` | `{4,2}` | `{3,2}` | 1780 |
| `TTSKOBoots` | `{4,4}` | `{3,3}` | 1905 |
| `MedievalBoots` | `{4,3}` | `{3,4}` | 1940 |
| `TraditionalBoots_ColorBase` | `{4,4}` | `{3,4}` | 2026 |
| `ColdOperationBoots_ColorBase` | `{4,4}` | `{3,4}` | 2122 |

```cpp
// [EXACT] exp\characters_shoes\DZ\characters\shoes\config.cpp:389
		itemSize[] = {3,2};
```

```cpp
// [EXACT] exp\characters_shoes\DZ\characters\shoes\config.cpp:1489
		itemSize[] = {4,2};
```

(The `{4,2}` cite is `LeatherShoes_ColorBase`.)

## Waterskin (was WaterPouch)

(until 1.29: `class WaterPouch_ColorBase: Bottle_Base` /
`class WaterPouch_Natural: WaterPouch_ColorBase` in
`stable-1.29\gear_drinks\DZ\gear\drinks\config.cpp:347,421`.)
(since 1.30 Exp: those config classnames are `Waterskin_ColorBase` /
`Waterskin_Natural`. AnimEvents still use `WaterPouch_*_SoundSet` names.)

Script: `exp\scripts\scripts\4_World\Entities\ItemBase\Gear\Drinks\WaterPouch_ColorBase.c`
is now the empty stub `class WaterPouch_ColorBase: Bottle_Base{};`. Behaviour
lives on `Waterskin_ColorBase.c`.

```cpp
// [EXACT] exp\gear_drinks\DZ\gear\drinks\config.cpp:347
	class Waterskin_ColorBase: Bottle_Base
	{
		displayName = "$STR_CfgVehicles_Waterskin_ColorBase0";
		descriptionShort = "$STR_CfgVehicles_Waterskin_ColorBase1";
		model = "\dz\gear\drinks\waterskin.p3d";
		lootCategory = "Crafted";
		hiddenSelections[] = {"camoground"};
		weight = 250;
		itemSize[] = {2,4};
		repairableWithKits[] = {3};
		repairCosts[] = {25.0};
		destroyOnEmpty = 0;
		varQuantityDestroyOnMin = 0;
		varLiquidTypeInit = 512;
		liquidContainerType = "1 + 2 + 4 + 8 + 16 + 32 + 64 + 128 + 256 + 512 + 1024 + 2048 + 4096 + 8192 + 16384 + 32768 + 65536  + 131072 + 262144 + 524288 + 2097152 + 4194304 - (1 + 2 + 4 + 8 + 16 + 32 + 64 + 128 + 256) - 32768";
		varTemperatureFreezePoint = -200;
		varTemperatureThawPoint = -200;
		varTemperatureMax = 120;
		varQuantityInit = 0.0;
		varQuantityMin = 0.0;
		varQuantityMax = 1250.0;
		temperaturePerQuantityWeight = 4;
```

Craft (`CraftWaterskin.c:26-44`): ingredient 0 `TannedLeather` with
`m_IngredientAddQuantity[0] = -2`; ingredient 1 `LeatherSewingKit` with
`m_IngredientAddQuantity[1] = -10`; result `Waterskin_Natural`.

De-craft (`DeCraftWaterskin.c:26-90`): ingredient 0 `Waterskin_ColorBase`
destroyed; ingredient 1 a long knife/axe list including `Jambiya`, `Scimitar`,
`DonerKnife`, `BrickTrowel`, `Akinaka`; `m_IngredientAddHealth[1] = -12`; result
1 `TannedLeather`. `CanDo` is `return ingredients[0].IsEmpty();`.

`[DESIGN]` persistence alias if a 1.29 world still stores `WaterPouch_Natural`:

```cpp
class Waterskin_Natural;
class WaterPouch_Natural: Waterskin_Natural { scope = 1; };
```

That alias is not in vanilla 1.30.

## CraftArmbandFlag

(until 1.29: `CanDo` was `return ingredients[0].IsEmpty();` —
`stable-1.29\scripts\scripts\4_World\Classes\Recipes\Recipes\CraftArmbandFlag.c:101`.)
(since 1.30 Exp: only rejects a flag that is already attached. Tool list gained
`Jambiya`, `Scimitar`, `DonerKnife`, `Akinaka`.)

```c
// [EXACT] exp\scripts\scripts\4_World\Classes\Recipes\Recipes\CraftArmbandFlag.c:103
	override bool CanDo(ItemBase ingredients[], PlayerBase player)
	{
		return !ingredients[0].GetInventory().IsAttachment();
	}
```

## Wash head / wet clothing / thermal bias

New continuous actions (digest F). Wetness is applied per clothing slot from
maps in `ActionWashHeadWettingClothesBase.GetWetnessMap`
(`:13-22` container vs `:31-40` surface). Wash-head also reduces
`eAgents.EYES_IRRITATION` and calls `GetThermalBiasHandler()`.

Constants (digest F marked these unverified; they are in this extract):

```c
// [EXACT] exp\scripts\scripts\3_Game\PlayerConstants.c:203
	static const float THERMAL_BIAS_WASH_HEAD_DECREMENT = 0.175;
	static const float THERMAL_BIAS_WASH_HEAD_TEMPORARY_RESISTANCE_TIME = 30.0;
```

`ActionWetClothingInHandsWater.ActionCondition` requires `item.IsClothing()` and
`item.GetWet() < item.GetWetMax()` (`ActionWetClothingInHandsWater.c:20-25`) and
uses `CCTLiquid`.

`[CHANGELOG]` `work\changelog-1.30-exp-modding.md:83`: "Bottles can still be used
to Wash Head while Frozen". Confirmed in script:
`ActionWashHeadItemContinuous.ActionCondition` (`:32-38`) only rejects
`LIQUID_GASOLINE`; it does not call `GetIsFrozen()`.

Heat-stroke coupling beyond these two constants is out of scope here (medical
lane). `[DESIGN]`: do not treat wash-head as a full heat-stroke API.

## Nasdara / Badlands clothing scripts without configs

Scripts exist under `exp\scripts\scripts\4_World\Entities\ItemBase\Clothing\`
for `DustGoggles_ColorBase`, `FNOJacket` / `FNOPants`, `Kameez_ColorBase`,
`LeatherHipPack_ColorBase`, `LinenVest_ColorBase`, `PakolHat_ColorBase`,
`PoliceShortSleeveShirt_ColorBase`, `RobeVest_ColorBase`, `Sandals_ColorBase`,
`Shalwar_ColorBase`, `ShortSleeveShirt_ColorBase`, `TurbanHat_ColorBase`.
No matching `class` entries were found in this extract's `characters_tops` /
`pants` / `headgear` / `shoes` / `vests` configs. `[UNVERIFIED]`: Isolation,
cargo, `ClothingTypes` paths, and whether the p3ds shipped in another PBO.

`LeatherHipPack_ColorBase` inherits `Belt_Base` and blocks `CanPutInCargo` unless
empty; `CanReceiveAttachment` refuses non-`Man` parents. `[DESIGN]`: treat as
DLC/regional content until a `characters_*` config appears.

## What 1.30 does **not** change (still the SKILL.md contract)

- `config.cpp` packed as text; `ClothingTypes` male/female; camo `hiddenSelections`.
- Canonical worn frame (−Z chest, +X anatomical left, +Y up).
- Skeleton name `DayzTemporarySkeleton`, 159-pair `model.cfg.template`.
- In-game gate: spawn → equip → move.

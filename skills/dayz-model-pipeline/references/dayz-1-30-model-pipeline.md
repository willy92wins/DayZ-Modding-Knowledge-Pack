# DayZ 1.30 Exp — model pipeline deltas (build 1.30.164014)

Companion to `SKILL.md` § DayZ 1.30 Exp. The LOD resolution table, py3d assembly
path, winding rules, and artist-return preflight (SP-246) still hold. This file
is the 1.30 engine/config delta for meshes, proxies, houses, and cache.

Line numbers are from files opened under `exp\` (and the official changelog
transcription). Digest O/F/H line numbers were **not** copied.

## Inventory-attachment proxy position on dedicated server

(until 1.29: if the proxy triangle was missing from the **final** visual LOD, a
dedicated server could report the attachment at the parent origin / mesh
center.) (since 1.30 Exp [CHANGELOG]: the server falls back to the **View
Geometry LOD** to read the inventory-attachment proxy position.)

Official changelog (`work\changelog-1.30-exp-modding.md:39`):

> Fixed: Getting the position of an inventory attachment proxy on the server
> will now use the view geometry LOD to prevent getting the center of the
> parent object if the proxy was not defined in the final lod

[DESIGN] Duplicate the proxy triangle + `proxy:…p3d.NNN` selection in
ViewGeometry (6.0e15), not only in Resolution LODs. The visual-LOD requirement
in `memory-and-selections.md` remains; ViewGeometry is now the server-side
fallback, not a substitute for visual proxies.

There is no Enforce Script call-site in this extract that names the LOD
fallback — it is engine C++. Do not invent an API for it.

## `-cacheP3D=0/1` and `.p3dcache` next to unbinarized meshes

(since 1.30 Exp [CHANGELOG], `work\changelog-1.30-exp-modding.md:11`):

> Added: '-cacheP3D=0/1' command line launch option, creates .p3dcache files
> next to .p3d files to allow for quicker subsequent launches of the
> Game/Buldozer when working with unbinarized assets

[DESIGN] Use it on DayZDiag / Buldozer loops that iterate **MLOD** `.p3d` (not
yet AddonBuilder-binarized). The cache files are siblings of the `.p3d`; they
are not packed into a shipping PBO. Binary `.p3d` / `.p3dcache` are not in
`exp\`; existence of the flag is changelog-only.

Cross-ref launch argv: `dayz-test-ingame` § DayZ 1.30 Exp and
`dayz-test-ingame/references/dayz-1-30-test-ingame.md`.

## `disableSimulation` on house-based entities

(since 1.30 Exp [CHANGELOG], `work\changelog-1.30-exp-modding.md:13`):

> Added: 'disableSimulation' config parameter to house-based entities to
> eliminate unnecessary entity ticking impacting client/server performance

Script API on `Entity` (verified):

```
// [EXACT] exp\scripts\scripts\3_Game\Entities\Entity.c:1-6
class Entity extends ObjectTyped
{
	proto native void DisableSimulation(bool disable);

	//! Returns whether simulation is disabled
	proto native bool GetIsSimulationDisabled();
```

[UNVERIFIED] No extracted `config.cpp` under `exp\` in this build contains a
vanilla `disableSimulation = 1;` assignment (Digest O §6.3 / Digest H §6.3). The
config key is engine-side; the script natives are exact. Prefer the config
parameter on static `House` / house-based classes that never need per-tick
simulation; use `DisableSimulation(true)` only when toggling at runtime.

## Selection `liquid_source` (wells / liquid interactables)

(since 1.30 Exp) Liquid actions that target a **well object** (not a pond
surface) look up ViewGeometry components named `liquid_source`:

```
// [EXACT] exp\scripts\scripts\4_World\Classes\UserActionsComponent\Actions\ActionConstants.c:175-181
class UAMisc
{
	const float FLAG_STEP_INCREMENT = 0.2; //0..1
	const float CONSUMPTION_SLOWDOWN_COEF_HOT = 5.0;
	
	const string LIQUID_SOURCE_SELECTION = "liquid_source";
};

```

Call-sites (same string, ViewGeometry level): `ActionWashHandsWell.c:38`,
`ActionDrinkWellContinuous.c:54`, `ActionWashHeadWell.c:38`,
`CCTLiquid.c:89` (`GetActionComponentsForSelectionName(…GetViewGeometryLevel(),
UAMisc.LIQUID_SOURCE_SELECTION, …)`).

[DESIGN] A custom well / pump `.p3d` that should accept wash/drink/fill must
carry a named selection `liquid_source` on **ViewGeometry**, not only a memory
point. Pond/sea surfaces go through `CCTLiquid` without this selection.

## `StaticObjectType` + `CfgNonAIVehicles` `VegetationSounds`

(since 1.30 Exp) New type class. Absent from `stable-1.29`. Loads optional
per-object vegetation step sounds from config:

```
// [EXACT] exp\scripts\scripts\3_Game\Entities\StaticObjectType.c:1-15
class StaticObjectType : EntityType
{
	//may not contain every soundset info, defaults from DayZPlayerType used in that case
	protected ref map<int, ref SoundObjectBuilder> m_CustomVegetationSoundsMap; //<stepEventID, SoundObjectBuilder>
	
	void StaticObjectType()
	{
		LoadCustomStepSounds();
	}
	
	protected void LoadCustomStepSounds()
	{
		string pathBase = "CfgNonAIVehicles " + GetName() + " VegetationSounds";
		if (!g_Game.ConfigIsExisting(pathBase))
			return;
```

Vanilla **player** vegetation macros live on `SurvivorBase` (not
CfgNonAIVehicles) — example:

```
// [EXACT] exp\characters_data\DZ\characters\data\config.cpp:258-264
		class VegetationSounds
		{
			class bush_walkErc
			{
				soundSet = "bush_walkErc_SoundSet";
				animEventIds[] = {1,2,23,24,51,52};
			};
```

[UNVERIFIED] This extract has **no** `class VegetationSounds` under a
`CfgNonAIVehicles` config.cpp (only the SurvivorBase block above). The loader
path is exact; a shipping bush/tree example is not in the public PBOs here.
Sound-set authoring belongs to `dayz-sound-system`.

## Animation graphs `.agr` → Enfusion `.agf` (out of scope for model.cfg)

Digest O attributed `.agr` / 250-bone / `skeletons.anim.xml` claims to
`references/animations.md`. That file is **model.cfg object animation**
(CfgSkeletons / CfgModels). It never mentioned `.agr`, a 250-bone cap, or
`skeletons.anim.xml`. Those are the **player/infected Enfusion animation
graph** (skill `dayz-animation-pipeline`).

(since 1.30 Exp [CHANGELOG], `work\changelog-1.30-exp-modding.md:24, 30-31, 43`):
animation-graph files use Enfusion config format; the 250 global bone limit is
removed; most of `skeletons.anim.xml` is unused except the `lod` attribute.

**This skill's model.cfg contract does not change.** Do not convert object
`model.cfg` to `.agf`. Character/infected graph ports belong to
`dayz-animation-pipeline`.

## Unpacked-mod / named filesystem (packaging implication)

(since 1.30 Exp [CHANGELOG]: `-mod` may point at a physical folder; RV configs
read unpacked; mods get a named filesystem —
`work\changelog-1.30-exp-modding.md:25-28`.) Iteration of **config.cpp** no
longer always requires AddonBuilder. Unbinarized `.p3d` still benefit from
`-cacheP3D`. Shipping / Workshop still packs a PBO. Operational launch:
`dayz-test-ingame`.

## Migration checklist (model / config)

1. Inventory attachments: proxy triangle in visual LODs **and** ViewGeometry.
2. Custom wells: ViewGeometry selection `liquid_source`.
3. Static houses with no tick: consider `disableSimulation` (config key
   [CHANGELOG]; script toggle `Entity.DisableSimulation`).
4. Unbinarized mesh loop: `-cacheP3D=1` on Diag/Buldozer.
5. Duplicate **members** inside one config class now fail binarize — see
   `dayz-pbo-build`.
6. Custom character/infected **graphs**: `.agf` via Workbench, not this skill.

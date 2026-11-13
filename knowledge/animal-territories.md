# Animal territories and ambient life (`cfgenvironment.xml`, `env/*_territories.xml`)

This note records the mission XML surface that registers animal and
ambient-life territories in the vanilla ChernarusPlus mission: the
`cfgenvironment.xml` contract, the `env/*_territories.xml` zone files it
points at, the exact group-behavior names the vanilla file uses, and the
Central Economy (`types.xml`) precondition for the spawned classnames.
It documents only what the vanilla XML shows. Runtime spawn rates, group
AI decisions and navmesh behaviour are not claimed here; the behavior
contract itself belongs to [dayz-ai-patterns](../skills/dayz-ai-patterns/SKILL.md).

Primary sources, all in the vanilla mission `dayzOffline.chernarusplus`
(DayZServer `appmanifest_223350.acf`, buildid `26220720`):

- `dayzOffline.chernarusplus/cfgenvironment.xml`, 115 lines,
  SHA-256 `3f73c9f3abe7ed3811811a147ecfcc596af6170552e372c5eaff27dd92fbf135`.
- `dayzOffline.chernarusplus/env/wolf_territories.xml`, 327 lines,
  SHA-256 `36738538717e378a13e0566b9888e58d06a80193506d8bd5a12bf57949aad935`.
- `dayzOffline.chernarusplus/env/bear_territories.xml`, 100 lines,
  SHA-256 `9aa16e734d49d70e835ebe8161f59f0d2386602f9cfc026b42471a1826a9bbf8`.

Only short XML fragments are quoted below, each with its `path:line`
locator; no whole vanilla file is copied into the Pack.

## 1. The `cfgenvironment.xml` contract

The document root is `<env>` and its only child shown in the vanilla
file is `<territories>`, closed at the end of the file:
`<env>` at `dayzOffline.chernarusplus/cfgenvironment.xml:2`,
`<territories>` at `dayzOffline.chernarusplus/cfgenvironment.xml:5`,
`</territories>` at `dayzOffline.chernarusplus/cfgenvironment.xml:114`
and `</env>` at `dayzOffline.chernarusplus/cfgenvironment.xml:115`.
[EXACT][CLAIM-ANIMAL-TERR-ENV-ROOT]

Inside `<territories>`, zone files are registered first with empty
`<file path="env/..."/>` elements, one per territory file:
`env/cattle_territories.xml` at `cfgenvironment.xml:7`,
`env/sheep_goat_territories.xml` at `cfgenvironment.xml:8`,
`env/red_deer_territories.xml` at `cfgenvironment.xml:9`,
`env/roe_deer_territories.xml` at `cfgenvironment.xml:10`,
`env/wild_boar_territories.xml` at `cfgenvironment.xml:11`,
`env/pig_territories.xml` at `cfgenvironment.xml:12`,
`env/hen_territories.xml` at `cfgenvironment.xml:13`,
`env/wolf_territories.xml` at `cfgenvironment.xml:14`,
`env/hare_territories.xml` at `cfgenvironment.xml:15`,
`env/zombie_territories.xml` at `cfgenvironment.xml:16`,
`env/bear_territories.xml` at `cfgenvironment.xml:17` and
`env/fox_territories.xml` at `cfgenvironment.xml:19`.
[EXACT][CLAIM-ANIMAL-TERR-FILE-REGISTRATION]

A territory binding then names a group kind, a display name and a
behavior class, and points at one registered zone file by stem:
`<territory type="Herd" name="Deer" behavior="DZDeerGroupBeh">` at
`cfgenvironment.xml:21` with `<file usable="red_deer_territories" />`
at `cfgenvironment.xml:22`, closed at `cfgenvironment.xml:23`.
The `usable` value is the file stem (`red_deer_territories`), not the
full `env/red_deer_territories.xml` path used at registration.
[EXACT][CLAIM-ANIMAL-TERR-TERRITORY-BINDING]

Exact quirk, recorded as written and with no runtime meaning inferred:
`env/hare_territories.xml` is registered twice, at
`cfgenvironment.xml:15` and again at `cfgenvironment.xml:18`.
[EXACT][CLAIM-ANIMAL-TERR-DUPLICATE-HARE]

## 2. `Herd` versus `Ambient`, and the `ZombieTest` exception

In this vanilla file the animal `Herd` block, `cfgenvironment.xml:21-47`,
declares nine territories (Deer, Cow, Goat, Sheep, RoeDeer, Wolf,
WildBoar, Pig and Bear) and none of them declares an `<agent>`, a
`<spawn>` or an `<item>` child: each holds only its
`<file usable="..."/>` line, as in the Deer example above.
[EXACT][CLAIM-ANIMAL-TERR-HERD-ANIMAL-BLOCK]

The three `Ambient` territories that follow it do declare agents.
`AmbientHen` at `cfgenvironment.xml:50-67`, `AmbientHare` at
`cfgenvironment.xml:70-80` and `AmbientFox` at
`cfgenvironment.xml:83-93` each carry `<agent>` children with
`<spawn>` classnames and territory-level `<item>` values (section 3).
Read the contrast narrowly: it is a fact about the animal `Herd`
block at `:21-47` and the `Ambient` entries at `:50-93` of this file,
not a rule that `Herd` territories never declare agents.
[EXACT][CLAIM-ANIMAL-TERR-HERD-VS-AMBIENT]

`ZombieTest` is the counterexample inside the same file. It is a
`Herd` territory at `cfgenvironment.xml:96-112`
(`<territory type="Herd" name="ZombieTest" behavior="DZdomesticGroupBeh">`
at `cfgenvironment.xml:96`, `<file usable="zombie_territories" />` at
`cfgenvironment.xml:97`) and it does declare agents: `<agent type="Male">`
at `cfgenvironment.xml:99` and `<agent type="Female">` at
`cfgenvironment.xml:104`, neither with a `chance` attribute.
[EXACT][CLAIM-ANIMAL-TERR-ZOMBIE-EXCEPTION]

The vanilla `zombie_territories.xml` registration at
`cfgenvironment.xml:16` is the infected counterpart of the animal
zone files; infected behaviour and classes belong to
[dayz-characters](../skills/dayz-characters/SKILL.md), not to this note.

## 3. `<agent>`, `<spawn>` and `<item>` fields

An `Ambient` agent groups the classnames that one agent type can
spawn. In `AmbientHen`, `<agent type="Male" chance="1">` at
`cfgenvironment.xml:53` holds
`<spawn configName="Animal_GallusGallusDomesticus" chance="1" />` at
`cfgenvironment.xml:54`, and `<agent type="Female" chance="3">` at
`cfgenvironment.xml:56` holds three spawns at
`cfgenvironment.xml:57-59`
(`Animal_GallusGallusDomesticusF_Brown` chance `1`,
`Animal_GallusGallusDomesticusF_Spotted` chance `10`,
`Animal_GallusGallusDomesticusF_White` chance `20`).
`AmbientHare` repeats the shape with `Animal_LepusEuropaeus` at
`cfgenvironment.xml:73-78`, and `AmbientFox` with
`Animal_VulpesVulpes` at `cfgenvironment.xml:86-91`.
[EXACT][CLAIM-ANIMAL-TERR-AGENT-SPAWN]

Territory-level `<item name="..." val="..."/>` values tune the
`Ambient` entries. `AmbientHen` declares `globalCountMax` val `50`
at `cfgenvironment.xml:62`, `zoneCountMin` val `1` at
`cfgenvironment.xml:63`, `zoneCountMax` val `1` at
`cfgenvironment.xml:64`, `playerSpawnRadiusNear` val `25` at
`cfgenvironment.xml:65` and `playerSpawnRadiusFar` val `75` at
`cfgenvironment.xml:66`. `AmbientHare` declares only
`zoneTouchDisableEditPeriodSec` val `300` at `cfgenvironment.xml:79`,
and `AmbientFox` only `zoneTouchDisableEditPeriodSec` val `450` at
`cfgenvironment.xml:92`.
[EXACT][CLAIM-ANIMAL-TERR-AMBIENT-ITEMS]

`ZombieTest` uses a different `<item>` placement. Inside each agent,
`<item name="countMin" val="0" />` and
`<item name="countMax" val="0" />` sit at
`cfgenvironment.xml:101-102` (Male) and
`cfgenvironment.xml:106-107` (Female), under spawns with no `chance`
attribute (`ZombieMale3_NewAI` at `cfgenvironment.xml:100`,
`ZombieFemale3_NewAI` at `cfgenvironment.xml:105`). At territory
level it declares `<item name="herdsCount" val="0" />` at
`cfgenvironment.xml:111`, under the source comment
`<!-- count of herds of this type in the map -->` at
`cfgenvironment.xml:110`. Those agent-level `countMin`/`countMax`
items and the territory-level `herdsCount` are the `ZombieTest`
shape; the `Ambient` entries above show no such items.
[EXACT][CLAIM-ANIMAL-TERR-ZOMBIE-ITEMS]

## 4. Zone files: `env/*_territories.xml`

A zone file has root `<territory-type>`, one `<territory color="...">`
element per territory, and one self-closing
`<zone name="..." smin="..." smax="..." dmin="..." dmax="..." x="..." z="..." r="..."/>`
element per zone. In `wolf_territories.xml` the root opens at
`env/wolf_territories.xml:2`, the first
`<territory color="4291611852">` opens at `env/wolf_territories.xml:3`,
its first zone is
`<zone name="Water" smin="0" smax="0" dmin="0" dmax="0" x="10597.5" z="13432.5" r="60"/>`
at `env/wolf_territories.xml:4`, and the root closes at
`env/wolf_territories.xml:327`; the file holds 24 territories across
`env/wolf_territories.xml:2-327`.
[EXACT][CLAIM-ANIMAL-TERR-ZONE-STRUCTURE]

Wolf zone names, exact and scoped to this file, are `Water`, `Rest`
and `HuntingGround`: `Water` at `env/wolf_territories.xml:4`,
`Rest` at `env/wolf_territories.xml:5` and `HuntingGround` at
`env/wolf_territories.xml:9`, repeated across
`env/wolf_territories.xml:4-326`. Every wolf zone read carries
`smin="0" smax="0" dmin="0" dmax="0"` with its own
`x`, `z` and `r`, as at `env/wolf_territories.xml:4-18`.
[EXACT][CLAIM-ANIMAL-TERR-ZONE-WOLF]

Bear zones use a different name. `bear_territories.xml` opens its
root at `env/bear_territories.xml:2`, its first
`<territory color="4294923520">` at `env/bear_territories.xml:3` and
its first `<zone name="Graze" .../>` at
`env/bear_territories.xml:4`. The file is
`env/bear_territories.xml:2-100`, closes at
`env/bear_territories.xml:100`, and holds 13 territories, not only
the first block at `env/bear_territories.xml:1-10`; every zone in
the file is a `Graze` zone, as at `env/bear_territories.xml:12`,
`env/bear_territories.xml:55` and `env/bear_territories.xml:92`.
Do not generalise zone names across species: wolf uses
`Water`/`Rest`/`HuntingGround` and bear uses `Graze` in the files
read here.
[EXACT][CLAIM-ANIMAL-TERR-ZONE-BEAR]

## 5. Behavior class names (exact)

The `behavior="..."` values in the vanilla file, spelled exactly as
written there, are:

- `DZDeerGroupBeh`: Deer at `cfgenvironment.xml:21`, RoeDeer at
  `cfgenvironment.xml:33`, WildBoar at `cfgenvironment.xml:39`.
- `DZdomesticGroupBeh`: Cow at `cfgenvironment.xml:24`, `ZombieTest`
  at `cfgenvironment.xml:96`.
- `DZSheepGroupBeh`: Goat at `cfgenvironment.xml:27`, Sheep at
  `cfgenvironment.xml:30`, Pig at `cfgenvironment.xml:42`.
- `DZWolfGroupBeh`: Wolf at `cfgenvironment.xml:36`.
- `BlissBearGroupBeh`: Bear at `cfgenvironment.xml:45`. The vanilla
  spelling is `BlissBearGroupBeh`, not `DZBearGroupBeh`.
- `DZAmbientLifeGroupBeh`: `AmbientHen` at `cfgenvironment.xml:50`,
  `AmbientHare` at `cfgenvironment.xml:70`, `AmbientFox` at
  `cfgenvironment.xml:83`.

[EXACT][CLAIM-ANIMAL-TERR-BEHAVIORS]

This note records only that XML wiring. What each behavior class
does at runtime (graze/rest/hunt cycles, group templates such as
`DZMouflonGroupBeh` and `DZDogGroupBeh`) is owned by
[dayz-ai-patterns](../skills/dayz-ai-patterns/SKILL.md); do not infer
a behavior contract from the territory name alone.

## 6. Central Economy precondition

A `<spawn configName="Animal_...">` names a classname; the territory
XML does not itself show a CE dependency. The Pack records
`db/types.xml` as the CE file holding spawn rates, lifetimes and
locations at [DAYZ_INFRA.md](DAYZ_INFRA.md) (`knowledge/DAYZ_INFRA.md:218`).
The territory XML registers where animals can live and which
classnames an agent can pick, as at `cfgenvironment.xml:54` and
`cfgenvironment.xml:57-59`. Treat the `types.xml` entry as the Pack's
CE reference for that classname, not as a condition proved by
`cfgenvironment.xml`.
[EXACT][CLAIM-ANIMAL-TERR-CE-TYPES]

## 7. Custom-map recipe

To add an animal territory to a custom mission, following the
vanilla shape above and claiming no runtime ordering beyond it:

1. Add a zone file, for example `env/my_animal_territories.xml`,
   with root `<territory-type>`, one `<territory color="...">` per
   territory and `<zone name="..." smin="..." smax="..." dmin="..." dmax="..." x="..." z="..." r="..."/>`
   entries whose `name` values match the names the chosen behavior
   expects (section 4; do not copy wolf or bear names blindly).
2. Register the file inside `<territories>` in
   `cfgenvironment.xml` with
   `<file path="env/my_animal_territories.xml"/>`, as at
   `cfgenvironment.xml:7-19`.
3. Add a `<territory type="Herd|Ambient" name="..." behavior="...">`
   binding whose animal `Herd` examples carry only
   `<file usable="my_animal_territories"/>` (the file stem, not the
   full path), as at `cfgenvironment.xml:21-23`; `ZombieTest` shows a
   `Herd` can also carry agents (section 2). For an `Ambient`
   binding, add the `<agent>`/`<spawn>` and `<item>` children shown
   in section 3.
4. Check that every `<spawn configName="Animal_...">` classname has
   a CE entry in the mission `db/types.xml`; the Pack records that
   file as the CE source (section 6), while the territory XML only
   names the class.
5. Restart the server and check the RPT for territory or CE errors
   naming the new file, territory or classname.

No step above claims a load or spawn ordering guarantee; the note
records only the registration shape the vanilla file uses.

## Limits

- Vanilla ChernarusPlus only, DayZServer buildid `26220720`, files
  hashed in the header. Line numbers are those files'; re-verify
  before citing them on another build or mission.
- No runtime verification: nothing here was measured in game, and
  the duplicate `hare_territories.xml` registration at
  `cfgenvironment.xml:15` and `cfgenvironment.xml:18` is recorded
  as an exact textual quirk, not as a claim about what the engine
  does with a duplicate registration.
- Zone counts (24 wolf territories, 13 bear territories) and the
  bear `Graze`-only reading cover the two zone files hashed above;
  other `env/*_territories.xml` files were not read for this note.
- No vanilla file is copied; only the short fragments quoted with
  their locators are reproduced.



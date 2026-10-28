---
name: dayz-sound-system
description: "Use when: sonido DayZ, CfgSoundShaders, SoundSet, sound not playing, no sound on dedicated server, PlaySoundSet, NoiseSystem, bunker radio, HEAVY_BREATHING, GetEnvironmentNoiseReduction, IsHeadlessOrDedicatedServer, sandstorm noise, VegetationSounds. Audio is client-only. Not particles: dayz-particles; not UI: dayz-ui-development."
---

# DayZ Sound System (Enforce Script + config)

Verified reference for mod audio. Citations are `path:line` against the vanilla 1.30.164200 scripts
(first verified on v1.24, re-checked on 2026-10-28; a cite labelled 1.29 is the 1.29 line; ±3 drift) and two real mods used as prior art (IMPWMODPart2 weapons, DoorLockSystem). The full
deep-dive with every signature lives in `references/sonido-deep-dive.md` — load it for AbstractWave
events, DynamicMusicPlayer internals, or PlayerSoundManager handlers. 1.30 Exp cites:
`references/dayz-1-30-sound.md`.

## The one rule that explains most bugs

**Audio is client-only.** `SEffectManager.Init()` runs only on clients (`3_game/effectmanager.c:507-521`)
and `Object.PlaySoundSet` is guarded by `if (g_Game && !g_Game.IsDedicatedServer())`
(`3_game/entities/object.c:1249`). Any `Play*` call on a dedicated server is a silent no-op.
To make a sound happen "from the server", you synchronize a state change and let each client play it:
the official vehicle for that is `StartItemSoundServer` (below), or your own SyncVar +
`OnVariablesSynchronized`.
(hasta 1.29 / still on `Object.PlaySoundSet` in 1.30: the guard is `object.c:1249` —
`if ( g_Game && !g_Game.IsDedicatedServer() )`.)
(desde 1.30: item/player sound **handlers** use `g_Game.IsHeadlessOrDedicatedServer()` so headless
clients are skipped too — `ItemSoundHandler.c:121`, `PlayerSoundManager.c:105`,
`DayZPlayerCfgSounds.c:335`. Proto: `Game.c:1132-1136`. `[EXACT]`: `references/dayz-1-30-sound.md`.)

## Decision table — which API when

| Situation | Use |
|---|---|
| One-shot 3D sound at a position (client code) | `SEffectManager.PlaySound("Set", pos)` (`effectmanager.c:178+`) |
| Sound that follows an object (client code) | `SEffectManager.PlaySoundOnObject("Set", obj)` or `obj.PlaySoundSet(snd, "Set", fadeIn, fadeOut, loop)` (`object.c:1247-1325`) |
| Server-driven item sound, synced to all clients | `StartItemSoundServer(id)` / `StopItemSoundServer(id)` (`4_world/entities/itembase.c:4440-4507`) |
| Sound at a memory point of the model | `PlaySoundSetAtMemoryPoint(...)` (`object.c:1294+`) |
| Animation-bound audio (footsteps, gestures) | AnimEvents in the anim config — engine plays them client-side automatically |
| Building door/alarm | `building.PlaySound/PlaySoundLoop` (native on Building; prior art DoorLockSystem `ActionUnlockDLSDoor.c:63,73`) |
| Make AI/infected hear something | `g_Game.GetNoiseSystem().AddNoise/AddNoisePos/AddNoiseTarget` (`3_game/noise.c:1-26`) — server side |
| Ambient music zone | `DynamicMusicPlayer.RegisterDynamicLocation` (`dynamicmusicplayer.c:289`) |
| (since 1.30) Per-world static music boxes | Subclass `DynamicMusicPlayerRegistry` and `RegisterTrackLocationStaticMultiRectangle` (`DynamicMusicPlayerRegistryNasdara.c:39-67`, wired `missionBase.c:143-145`) |
| (since 1.30) Radio tuned to bunker frequency | Set `SOUND_BUNKER_STATIC_NOISE` on the transmitter; `IsTunedToBunkerFrequency()` (`TransmitterBase.c:6,135-137`, proto on `ItemTransmitter` in `InventoryItem.c:25`) |
| (since 1.30) Per-bush / static vegetation footsteps | `CfgNonAIVehicles <class> VegetationSounds` via `StaticObjectType` (`StaticObjectType.c:13-47`); macro `CUSTOM_PLAYER_MOVEMENT_SOUNDSETS` (`basicDefines.hpp:310-338`) |

Cleanup matters: every `SEffectManager.Play*` registers a ref; call `SEffectManager.DestroyEffect(eff)`
or set autodestroy, or you leak (`effectmanager.c:41-44`).

## Config: CfgSoundShaders + CfgSoundSets

Files: `.ogg` (universal in mods) or `.wav`; referenced **without extension**, path relative to the
mod root (real example: `samples[] = {{"IMPWMODPart2\Weapons\Automatic\Sounds\Rifle1Mid", 1}}`).

```cpp
// config.cpp — minimal working pair (pattern from real mod, IMPWMODPart2 ...\Sounds\config.cpp:27-36)
class CfgSoundShaders
{
    class MyMod_Roll_SoundShader
    {
        samples[]    = {{"MyMod\Sounds\roll_loop", 1}};   // {path-no-extension, random weight}
        volume       = 1.0;
        range        = 40;                                 // meters
        rangeCurve[] = {{0, 1}, {20, 0.8}, {40, 0}};       // inline attenuation curve
        // or: rangeCurve = "closeShotCurve";              // reference a vanilla CfgSoundCurves name
    };
};
class CfgSoundSets
{
    class MyMod_Roll_SoundSet
    {
        soundShaders[] = {"MyMod_Roll_SoundShader"};
    };
};
```

Cleaner for variants: inherit a vanilla base via forward declaration (real example,
`IMPWMODPart2\Weapons\Automatic\F2000\Sounds\config.cpp:22-45`):
```cpp
class base_closeShot_SoundShader;                      // forward-declare vanilla base
class My_closeShot_SoundShader : base_closeShot_SoundShader
{
    samples[] = {{"MyMod\Sounds\my_close", 1}};
    volume    = 0.8;
};
class CfgSoundSets
{
    class Rifle_Shot_Base_SoundSet;                    // forward-declare vanilla base
    class My_Shot_SoundSet : Rifle_Shot_Base_SoundSet
    {
        soundShaders[] = {"My_closeShot_SoundShader", "My_midShot_SoundShader", "My_distShot_SoundShader"};
    };
};
```
Extra SoundSet properties (`sound3DProcessingType`, `volumeCurve`, `spatial`) exist on vanilla bases
but were not verifiable in local source — inherit a vanilla set rather than hand-rolling them.

## Script API core (`3_game/sound.c`, `3_game/effects/effectsound.c`)

- `SoundParams("SetName")` → validates/loads a SoundSet (:137-144).
- `SoundObjectBuilder(params)` → `AddEnvSoundVariables(pos)` / `AddVariable(name, val)` →
  `BuildSoundObject()` (:82-108).
- `SoundObject.SetParent(entity)` / `SetPosition(pos)` / `SetKind(WaveKind.X)` (:111-134). With a
  parent, `SetPosition` is in the parent's model space: set it before `Play3D` (recipe A2).
- Play: `g_Game.GetSoundScene().Play3D(so, sob)` / `Play2D(...)` (:53-79; access `game.c:735`).
- `AbstractWave` handle: `Play/Stop/Loop(bool)/SetVolumeRelative(0..1)/SetFadeInFactor/
  SetFadeOutFactor/SetDoppler/GetLength/GetCurrPosition` + `GetEvents()` ScriptInvokers
  (Started/Stopped/Loaded/HeaderLoaded/Ended) (:146-230). `SetFrequency` takes a pitch factor,
  not Hz (recipe A2).
- `EffectSound` (high-level wrapper): `SetSoundSet/SetSoundLoop/SetSoundFadeIn/Out/SetSoundVolume/
  SoundPlay/SoundStop/IsSoundPlaying` + its own invokers — what `PlaySoundSet` returns.
  (desde 1.30: if `m_SoundFadeInDuration > 0`, `Event_OnSoundWaveStarted` calls `SetSoundVolume(0)`
  so the first frame is silent — `EffectSound.c:549-555`. `[EXACT]`: `references/dayz-1-30-sound.md`.)
- `WaveKind` enum: WAVEEFFECT, WAVEEFFECTEX, WAVESPEECH, WAVEMUSIC, WAVEENVIRONMENT, WAVEWEAPONS,
  WAVEATTALWAYS, WAVEUI... (:1-14) — controls mixer category (and thus user volume sliders).
- Global category volumes only: `AbstractSoundScene.SetSoundVolume(vol, time)/SetMusicVolume/...`
  (:64-75) — there is no per-instance "master volume" beyond `SetVolumeRelative`.

## Server→client item sound (the official pattern)

1. Register sets in `InitItemSounds()` (`itembase.c:4420-4437`):
```c
override void InitItemSounds()
{
    super.InitItemSounds();
    ItemSoundHandler handler = GetItemSoundHandler();
    handler.AddSound(SoundConstants.ITEM_DEPLOY, "MyMod_Deploy_SoundSet");
    SoundParameters params = new SoundParameters();
    params.m_Loop = true;
    handler.AddSound(SoundConstants.ITEM_DEPLOY_LOOP, "MyMod_Loop_SoundSet", params);
}
```
2. Fire from server: `StartItemSoundServer(SoundConstants.ITEM_DEPLOY)` /
   `StopItemSoundServer(SoundConstants.ITEM_DEPLOY_LOOP)` (`itembase.c:4440-4507`).
3. Client side is automatic. On 1.30 the server queues every sound started in a frame and sends them
   in one `RPC_ITEM_SOUND_PLAY` (`itembase.c:4440-4484`), a stop goes as `RPC_ITEM_SOUND_STOP`
   (`:4499-4507`), and `ItemBase.OnRPC` plays them on the client (`:2800-2829`). On 1.29
   `OnVariablesSynchronized` dispatched `m_SoundSyncPlay/m_SoundSyncStop` to
   `PlayItemSoundClient/StopItemSoundClient` (1.29 `itembase.c:3319-3332`); on 1.30 that path runs only
   in a class whose `OnVariablesSynchronized` calls `LegacyItemSoundSync()` (`:3297-3314`).

Limits: int IDs up to `ITEM_SOUNDS_MAX = 63` (`3_game/constants.c:415-435`). On 1.29 only ONE play + ONE
stop could be in flight per sync tick (`4_world/classes/soundhandlers/itemsoundhandler.c:19-20`), and the
sync vars were cleared ~100 ms later via CallLater; on 1.30 the queue sends several sounds in one RPC, and
the handler's comment, unchanged, describes only the legacy path.

For non-item state sounds, the generic pattern is the same: server sets a SyncVar → client plays in
`OnVariablesSynchronized` (remote clients never see one-frame server states otherwise).

## NoiseSystem (AI hearing)

```c
// 3_game/noise.c:1-26 — server side
g_Game.GetNoiseSystem().AddNoise(entity, noiseParams, multiplier);      // at entity
g_Game.GetNoiseSystem().AddNoisePos(entity, pos, noiseParams, mult);    // at position
g_Game.GetNoiseSystem().AddNoiseTarget(pos, lifetimeSec, noiseParams);  // positional DECOY with duration
NoiseParams np = new NoiseParams();  np.Load("name_in_CfgNoises");      // or LoadFromPath
```
(hasta 1.29: Rain/wind reduce effective noise via `NoiseAIEvaluate.GetNoiseReduction(g_Game.GetWeather())`
(used by player steps, `4_world/entities/dayzplayerimplement.c:3250-3254`).)
(desde 1.30: climate is native. Query `GetGame().GetNoiseSystem().GetEnvironmentNoiseReduction(pos)`
— `exp\scripts\scripts\3_Game\Noise.c:13`. `GetNoiseReduction` / `GetNoiseReductionByWeather` are
`[Obsolete]` (`SensesAIEvaluate.c:92`, `Weather.c:454`). Player steps pass only
`NoiseAIEvaluate.GetNoiseMultiplier(this)` (`DayZPlayerImplement.c:3472-3474`). Infected
`AddNoise(this, sound_event.m_NoiseParams)` has no weather multiplier (`ZombieBase.c:597-600`).
Tune rain/snow/fog/wind/sandstorm in `class AIParams` (`exp\dz\DZ\data\aiconfigs\config.cpp:19-27`).
Do not also multiply `AddNoise` by a script weather factor — native attenuation would double-dampen.)
Weapon shots define
`class NoiseShoot { strength = 82; type = "shot"; }` in the weapon config (real example
`IMPWMODPart2\Weapons\Automatic\MCXSpear\config.cpp:73-77`). `AddNoiseTarget` is the tool for
distraction devices: infected investigate a position that has no entity.

## Environment sound controllers

`SetSoundControllerOverride(name, value, action)` / `MuteAllSoundControllers()` /
`ResetAllSoundControllers()` (`3_game/sound.c:38-48`). Controller names (from the proto docs): rain,
night, meadow, trees, hills, houses, windy, deadBody, sea, forest, altitudeGround, altitudeSea,
daytime, shooting, coast, waterDepth, overcast, fog, snowfall, caveSmall, caveBig.

## What does NOT exist / classic confabulations

| Confabulation | Reality |
|---|---|
| `SEffectManager` works on server | Client-only; `InitServer()` exists for particles, not sound (`effectmanager.c:507-521`) |
| `PlaySoundSet` audible on dedicated server | Guarded no-op (`object.c:1249`) — sync state instead |
| `GetGame().CreateSoundOnObject(...)` returns EffectSound | Returns `SoundOnVehicle` entity (`game.c:692`; class `3_game/entities/soundonvehicle.c:1-4`) — legacy, prefer SEffectManager |
| `DynamicMusicPlayer.PlayTrack("...")` | Private; public API is `SetCategory(...)` + `RegisterDynamicLocation` (`dynamicmusicplayer.c:511,289`) |
| `OnSoundEvent` override on ItemBase | Does not exist — use ItemSoundHandler or PlaySoundSet manually |
| Several simultaneous synced sounds via StartItemSoundServer | One play + one stop per sync by protocol (`itemsoundhandler.c:19-20`) |
| Per-sound master volume API | Only `SetVolumeRelative(0..1)` per wave; shader `volume` is fixed config |
| samples[] with file extension | Engine infers `.ogg` — paths go extension-less (all prior-art configs) |

(desde 1.30: the `PlaySoundSet` row above is still true for `Object.PlaySoundSet`. Item/player
**handlers** additionally skip headless via `IsHeadlessOrDedicatedServer()`. Do not write
`GetNoiseReductionByWeather()` into new mods — `[Obsolete]`; use `GetEnvironmentNoiseReduction(pos)`
or `AIParams`.)

## Recipes

**A. Local loop tied to movement (e.g. rolling object) — pure client**
```c
EffectSound m_RollSound;
void UpdateRollAudio()                          // call from client-side update
{
    bool moving = GetVelocity(this).Length() > 0.5;
    if (moving && !m_RollSound)
        PlaySoundSet(m_RollSound, "MyMod_Roll_SoundSet", 0.1, 0.5, true);   // loop
    else if (!moving && m_RollSound)
        StopSoundSet(m_RollSound);              // respects fade-out
}
```
Position is already replicated to clients, so no server involvement is needed for the audio itself.

**A2. The same loop built by hand, to set its pitch** (measured in game, DayZ 1.30.164014 Exp,
LFSkateboard R1e, 2026-10-07) [EXACT][CLAIM-SOUND-HANDBUILT-LOOP-POSITION-130]. `EffectSound` holds
its wave in the protected `m_SoundWaveObject` (`3_game/effects/effectsound.c:23`), so to call
`AbstractWave.SetFrequency` on a roll loop the project built the loop itself: `SoundParams`, then
`SoundObjectBuilder` with `AddEnvSoundVariables`, `BuildSoundObject`,
`SetKind(WaveKind.WAVEEFFECTEX)`, `SetParent` on the player and `g_Game.GetSoundScene().Play3D`. The
loop played (its header loaded, and the script logged it) but was barely audible, while one-shots of
the same character sound bases played through `PlaySoundSet` were loud. With a parent, the position
of a `SoundObject` is in the parent's model space, and `EffectSound` always sets it right before its
own `Play3D`: it calls `SetCurrentLocalPosition` at `:172`, just before `Play3D` at `:173`, and its
override of `SetCurrentLocalPosition` passes the position to `m_SoundObject.SetPosition`
(`:750-757`). The hand-built loop set no position, and sat far from the rider. What fixed it:
`SetPosition` on the sound object after `SetParent` and before `Play3D`, with a small offset in the
parent's model space (the project used 0.1 m up). Lines of 1.30.164.200; 1.29 has the same code, the
override at `:746-753`.

[EXACT][CLAIM-SOUND-WAVE-FREQUENCY-FACTOR-130] `GetFrequency()` of that wave, a playing OGG loop,
returned 1.0: `SetFrequency` takes a factor, a pitch multiplier, not a frequency in Hz. Set it
relative to `GetFrequency()` once `IsHeaderLoaded()` is true. The run called both; their lines in
`3_game/sound.c` were not read for this note.

**B. Server-triggered impact sound** — register a set in `InitItemSounds()`, call
`StartItemSoundServer(id)` from the server event (e.g. `EOnContact`), done.

**C. Distraction noise (server)**
```c
NoiseParams np = new NoiseParams();
np.Load("FlareLight");                          // any CfgNoises entry; verify name in config dump
g_Game.GetNoiseSystem().AddNoiseTarget(pos, 30, np, 2.0);
```
(desde 1.30: do not multiply that `2.0` by a weather reduction you computed in script.)

**D. Music zone** — `RegisterDynamicLocation(this, locationType, radius)` on spawn,
`UnregisterDynamicLocation(this)` on delete; track = SoundSet with `WaveKind.WAVEMUSIC`.
(desde 1.30: a custom world should also subclass `DynamicMusicPlayerRegistry` like
`DynamicMusicPlayerRegistryNasdara` and construct it from `missionBase` world switch.)

## Cross-skill pointers

- `enforce-script-reference` — SyncVars/OnVariablesSynchronized mechanics, CfgSoundSets params table
  (Llama extraction section), config.cpp rules.
- `dayz-physics-engine` — contact events that typically drive impact sounds.
- `dayz-particles` — SEffectManager also owns particles; same lifecycle/leak rules.
- `dayz-ai-patterns` — how the eAI/infected consume NoiseSystem events.

## DayZ 1.30

What changes, what breaks, and the migration checklist. `[EXACT]` blocks: `references/dayz-1-30-sound.md`.
Deep-dive updates: `references/sonido-deep-dive.md`. Shared AI noise: skill `dayz-ai-patterns` (its 1.30 noise section).

**What changes**

- Native noise attenuation + `GetEnvironmentNoiseReduction(pos)`; `AIParams` adds snow/fog/wind/sandstorm multipliers.
- `IsHeadlessOrDedicatedServer()` on item/player sound paths. `Object.PlaySoundSet` still uses `IsDedicatedServer()`.
- `EffectSound` zeros volume at wave start when fade-in is set.
- `EPlayerSoundEventID.HEAVY_BREATHING` / `HeavyBreathEvent1` (anim 907); silicosis requests it.
- Per-world `DynamicMusicPlayerRegistry*` + `DynamicMusicPlayerTimeOfDay.Translate` (MORNING/NOON/AFTERNOON→DAY, EVENING→NIGHT).
- Transmitters: `SOUND_BUNKER_STATIC_NOISE` / `IsTunedToBunkerFrequency()`.
- `StaticObjectType` + `CUSTOM_PLAYER_MOVEMENT_SOUNDSETS` for vegetation step sounds (digest H).
- `[CHANGELOG]` `SoundHitType` / `GetSoundHitType()` (T189758): **not** present in Enforce `SurfaceInfo.c` on this build (digest K). Do not call them.

**What breaks for a 1.29 audio / stealth mod**

1. `[Obsolete]` on `GetNoiseReductionByWeather` / `NoiseAIEvaluate.GetNoiseReduction`.
2. Double-damp if you still pass a weather multiplier into `AddNoise`.
3. Custom radios that ignore bunker frequency never play `bunkerbroadcast_staticnoise_SoundSet`.
4. Subclassing `~InfectedSoundEventBase` to `Stop()` without `if (g_Game)` can crash on shutdown (`SoundEvents.c:12-16`).
5. Looped sounds with fade-in now start at volume 0 — if you relied on the 1.29 first-frame peak, levels will differ.

**Migration checklist**

- [ ] AI-heard factor: `GetEnvironmentNoiseReduction(pos)`; balance via `AIParams`, not script weather math.
- [ ] New client play/stop: `IsHeadlessOrDedicatedServer()`.
- [ ] Custom transmitter: set `SOUND_BUNKER_STATIC_NOISE` and `SetSynchDirty()` on frequency change (vanilla `SetNextFrequency` already does).
- [ ] Custom world music: subclass `DynamicMusicPlayerRegistry`, register boxes with `RegisterTrackLocationStaticMultiRectangle`.
- [ ] Custom bushes: `VegetationSounds` on the `CfgNonAIVehicles` class, or the `CUSTOM_PLAYER_MOVEMENT_SOUNDSETS` macro.
- [ ] Do not call `SurfaceInfo.GetSoundHitType` — not in this Enforce dump.
- [ ] Load `references/sonido-deep-dive.md` for player-event and NoiseSystem signature tables.

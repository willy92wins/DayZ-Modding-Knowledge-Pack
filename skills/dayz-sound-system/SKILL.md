---
name: dayz-sound-system
description: >
  DayZ audio end-to-end for Enforce Script modding: CfgSoundShaders/CfgSoundSets config with real
  working mod examples, the client-only script API (EffectSound, SEffectManager, AbstractWave),
  the official server-to-client sync pattern (StartItemSoundServer + OnVariablesSynchronized),
  DynamicMusicPlayer, and NoiseSystem (AI hearing, noise decoys). Use whenever a task involves
  adding any sound to a mod, .ogg files, "sound not playing", "no sound on dedicated server",
  looping sounds, weapon/alarm/door/ambient audio, music zones, making infected hear something,
  or any PlaySoundSet/SEffectManager/CreateSoundOnObject call. Consult BEFORE writing sound code —
  the #1 failure (silent on dedicated server) and several confabulated APIs are documented here,
  verified against vanilla v1.24 and two real community mods with path:line citations. Triggers:
  sonido DayZ, CfgSoundShaders, SoundSet, sonido no suena, audio del mod, música.
---

# DayZ Sound System (Enforce Script + config)

Verified reference for mod audio. Citations are `path:line` against vanilla v1.24 decompiled scripts
(±3 drift) and two real mods used as prior art (IMPWMODPart2 weapons, DoorLockSystem). The full
deep-dive with every signature lives in `references/sonido-deep-dive.md` — load it for AbstractWave
events, DynamicMusicPlayer internals, or PlayerSoundManager handlers.

## The one rule that explains most bugs

**Audio is client-only.** `SEffectManager.Init()` runs only on clients (`3_game/effectmanager.c:498-512`)
and `Object.PlaySoundSet` is guarded by `if (g_Game && !g_Game.IsDedicatedServer())`
(`3_game/entities/object.c:1245`). Any `Play*` call on a dedicated server is a silent no-op.
To make a sound happen "from the server", you synchronize a state change and let each client play it:
the official vehicle for that is `StartItemSoundServer` (below), or your own SyncVar +
`OnVariablesSynchronized`.

## Decision table — which API when

| Situation | Use |
|---|---|
| One-shot 3D sound at a position (client code) | `SEffectManager.PlaySound("Set", pos)` (`effectmanager.c:169+`) |
| Sound that follows an object (client code) | `SEffectManager.PlaySoundOnObject("Set", obj)` or `obj.PlaySoundSet(snd, "Set", fadeIn, fadeOut, loop)` (`object.c:1243-1321`) |
| Server-driven item sound, synced to all clients | `StartItemSoundServer(id)` / `StopItemSoundServer(id)` (`4_world/entities/itembase.c:4468-4508`) |
| Sound at a memory point of the model | `PlaySoundSetAtMemoryPoint(...)` (`object.c:1293+`) |
| Animation-bound audio (footsteps, gestures) | AnimEvents in the anim config — engine plays them client-side automatically |
| Building door/alarm | `building.PlaySound/PlaySoundLoop` (native on Building; prior art DoorLockSystem `ActionUnlockDLSDoor.c:63,73`) |
| Make AI/infected hear something | `g_Game.GetNoiseSystem().AddNoise/AddNoisePos/AddNoiseTarget` (`3_game/noise.c:1-23`) — server side |
| Ambient music zone | `DynamicMusicPlayer.RegisterDynamicLocation` (`3_game/systems/dynamicmusicplayer/dynamicmusicplayer.c:289`) |

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
- `SoundObject.SetParent(entity)` / `SetPosition(pos)` / `SetKind(WaveKind.X)` (:111-134).
- Play: `g_Game.GetSoundScene().Play3D(so, sob)` / `Play2D(...)` (:53-79; access `game.c:734`).
- `AbstractWave` handle: `Play/Stop/Loop(bool)/SetVolumeRelative(0..1)/SetFadeInFactor/
  SetFadeOutFactor/SetDoppler/GetLength/GetCurrPosition` + `GetEvents()` ScriptInvokers
  (Started/Stopped/Loaded/HeaderLoaded/Ended) (:146-230).
- `EffectSound` (high-level wrapper): `SetSoundSet/SetSoundLoop/SetSoundFadeIn/Out/SetSoundVolume/
  SoundPlay/SoundStop/IsSoundPlaying` + its own invokers — what `PlaySoundSet` returns.
- `WaveKind` enum: WAVEEFFECT, WAVEEFFECTEX, WAVESPEECH, WAVEMUSIC, WAVEENVIRONMENT, WAVEWEAPONS,
  WAVEATTALWAYS, WAVEUI... (:1-14) — controls mixer category (and thus user volume sliders).
- Global category volumes only: `AbstractSoundScene.SetSoundVolume(vol, time)/SetMusicVolume/...`
  (:64-75) — there is no per-instance "master volume" beyond `SetVolumeRelative`.

## Server→client item sound (the official pattern)

1. Register sets in `InitItemSounds()` (`itembase.c:4448-4465`):
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
   `StopItemSoundServer(SoundConstants.ITEM_DEPLOY_LOOP)` (`itembase.c:4468-4508`).
3. Client side is automatic: `OnVariablesSynchronized` dispatches `m_SoundSyncPlay/m_SoundSyncStop`
   to `PlayItemSoundClient/StopItemSoundClient` (`itembase.c:3319-3332`).

Limits: int IDs up to `ITEM_SOUNDS_MAX = 63` (`3_game/constants.c:415-435`); only ONE play + ONE stop
can be in flight per sync tick by design (`4_world/classes/soundhandlers/itemsoundhandler.c:19-20`) —
sync vars are cleared ~100 ms later via CallLater.

For non-item state sounds, the generic pattern is the same: server sets a SyncVar → client plays in
`OnVariablesSynchronized` (remote clients never see one-frame server states otherwise).

## NoiseSystem (AI hearing)

```c
// 3_game/noise.c:1-23 — server side
g_Game.GetNoiseSystem().AddNoise(entity, noiseParams, multiplier);      // at entity
g_Game.GetNoiseSystem().AddNoisePos(entity, pos, noiseParams, mult);    // at position
g_Game.GetNoiseSystem().AddNoiseTarget(pos, lifetimeSec, noiseParams);  // positional DECOY with duration
NoiseParams np = new NoiseParams();  np.Load("name_in_CfgNoises");      // or LoadFromPath
```
Rain/wind reduce effective noise via `NoiseAIEvaluate.GetNoiseReduction(g_Game.GetWeather())`
(used by player steps, `4_world/entities/dayzplayerimplement.c:3204-3208`). Weapon shots define
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
| `SEffectManager` works on server | Client-only; `InitServer()` exists for particles, not sound (`effectmanager.c:498-512`) |
| `PlaySoundSet` audible on dedicated server | Guarded no-op (`object.c:1245`) — sync state instead |
| `GetGame().CreateSoundOnObject(...)` returns EffectSound | Returns `SoundOnVehicle` entity (`game.c:691`; class `3_game/entities/soundonvehicle.c:1-4`) — legacy, prefer SEffectManager |
| `DynamicMusicPlayer.PlayTrack("...")` | Private; public API is `SetCategory(...)` + `RegisterDynamicLocation` (`dynamicmusicplayer.c:511,289`) |
| `OnSoundEvent` override on ItemBase | Does not exist — use ItemSoundHandler or PlaySoundSet manually |
| Several simultaneous synced sounds via StartItemSoundServer | One play + one stop per sync by protocol (`itemsoundhandler.c:19-20`) |
| Per-sound master volume API | Only `SetVolumeRelative(0..1)` per wave; shader `volume` is fixed config |
| samples[] with file extension | Engine infers `.ogg` — paths go extension-less (all prior-art configs) |

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

**B. Server-triggered impact sound** — register a set in `InitItemSounds()`, call
`StartItemSoundServer(id)` from the server event (e.g. `EOnContact`), done.

**C. Distraction noise (server)**
```c
NoiseParams np = new NoiseParams();
np.Load("FlareLight");                          // any CfgNoises entry; verify name in config dump
g_Game.GetNoiseSystem().AddNoiseTarget(pos, 30, np, 2.0);
```

**D. Music zone** — `RegisterDynamicLocation(this, locationType, radius)` on spawn,
`UnregisterDynamicLocation(this)` on delete; track = SoundSet with `WaveKind.WAVEMUSIC`.

## Cross-skill pointers

- `enforce-script-reference` — SyncVars/OnVariablesSynchronized mechanics, CfgSoundSets params table
  (Llama extraction section), config.cpp rules.
- `dayz-physics-engine` — contact events that typically drive impact sounds.
- `dayz-particles` — SEffectManager also owns particles; same lifecycle/leak rules.
- `dayz-ai-patterns` — how the eAI/infected consume NoiseSystem events.

# 02 — DayZ sound system (Enfusion/Enforce Script)
> Deep-dive verificado contra vanilla v1.24 scripts + prior art real. 2026-06-06.

---

## Resumen ejecutivo

DayZ Enfusion sound system has two cleanly separated layers:

1. **Config (no-script):** `CfgSoundShaders` + `CfgSoundSets` in `config.cpp`. Defines which audio file plays, at what volume, and how it attenuates with distance. Engine resolves everything automatically in 3D.
2. **Script API:** `EffectSound` / `SEffectManager` (client-only). Server CANNOT play sounds directly; network variables + `OnVariablesSynchronized` are used to synchronize audio in multiplayer.

For a rolling stone (LF_RollingStone): simplest approach is defining a SoundSet in config, and triggering it from client (`PlaySoundSet` / `SEffectManager.PlaySoundOnObject`) within already synchronized events (for example `OnVariablesSynchronized`, or upon receiving local contact).

---

## 1. Audio pipeline

### Formatos
- **Supported format:** `.ogg` (Vorbis) and `.wav`. In practice **all mods use `.ogg`**; IMP and armory files go as `.ogg` without extension in config paths (engine infers it).
- **WSS:** proprietary Bohemia compressed sound format; in DayZ Standalone mods use `.ogg` directly.
- Samples are referenced **without extension** in `CfgSoundShaders`, e.g.: `"IMPWMODPart2\Weapons\Automatic\F2000\Sounds\F2000_close"` — [IMPWMODPart2\Weapons\Automatic\F2000\Sounds\config.cpp:24].

### Where files live in a mod
```
MiMod/
├── Sounds/           ← archivos .ogg
├── config.cpp        ← CfgSoundShaders, CfgSoundSets
└── scripts/          ← lógica Enforce Script
```
Paths in `samples[]` are relative to mod root (same as model paths).

---

## 2. Config verificada

### CfgSoundShaders

Defines a sound "shader": which audio file(s), volume, range, and attenuation curve.

**Propiedades verificadas** [IMPWMODPart2\Weapons\Automatic\Sounds\config.cpp]:

| Property | Type | Description |
|---|---|---|
| `samples[]` | array of `{path, weight}` pairs | List of samples with randomization weight |
| `volume` | float | Base volume (0–1 or more) |
| `range` | float | Maximum distance in meters where audible |
| `rangeCurve[]` | array of `{distance, factor}` pairs | Distance attenuation curve |
| `rangeCurve` | string | Predefined curve name (e.g. `"closeShotCurve"`) |

**Real example** (shader without inheritance, with inline curve):
```cpp
class IMP_SoundShaderMid
{
    samples[] = {{"IMPWMODPart2\Weapons\Automatic\Sounds\Rifle1Mid", 1}};
    volume = 0.56234133;
    range = 1500;
    rangeCurve[] =
    {
        {0,   0.2},
        {50,  1},
        {300, 0},
        {1500,0}
    };
};
```
[IMPWMODPart2\Weapons\Automatic\Sounds\config.cpp:27-36]

**Example with vanilla base inheritance** (cleanest way for mods):
```cpp
class base_closeShot_SoundShader;   // forward-declare la base vanilla
class IMP_F2000_closeShot_SoundShader: base_closeShot_SoundShader
{
    samples[] = {{"IMPWMODPart2\Weapons\Automatic\F2000\Sounds\F2000_close", 1}};
    volume = 0.8;
};
```
[IMPWMODPart2\Weapons\Automatic\F2000\Sounds\config.cpp:22-26]

### CfgSoundSets

Groups shaders into a "set" that script references by string name.

**Minimum verified properties:**

| Property | Description |
|---|---|
| `soundShaders[]` | Array of CfgSoundShaders names to combine |

**Additional properties** (inherited from base, [UNVERIFIED in decompiled mod vanilla — see Bistudio]): `sound3DProcessingType`, `volumeCurve`, `spatial`.

**Ejemplo real** (heredando de base vanilla):
```cpp
class CfgSoundSets
{
    class Rifle_Shot_Base_SoundSet;   // forward-declare base vanilla
    class IMP_F2000_Shot_SoundSet: Rifle_Shot_Base_SoundSet
    {
        soundShaders[] = {
            "IMP_F2000_closeShot_SoundShader",
            "IMP_F2000_midShot_SoundShader",
            "IMP_F2000_distShot_SoundShader"
        };
    };
};
```
[IMPWMODPart2\Weapons\Automatic\F2000\Sounds\config.cpp:39-45]

**Simple SoundSet without inheritance** (for items, alarms, etc.):
```cpp
class CfgSoundSets
{
    class LFRS_Roll_SoundSet
    {
        soundShaders[] = {"LFRS_Roll_SoundShader"};
    };
};
```
[UNVERIFIED — pattern deduced from prior art; one shader suffices for simple effects]

### CfgSoundCurves / CfgSound3DProcessingTypes

- `CfgSoundCurves`: defines volume curves by name (e.g. `"closeShotCurve"`). Vanilla bases exist; mods reference them. [UNVERIFIED in decompiled scripts — only references by name in prior art config].
- `CfgSound3DProcessingTypes`: configures HRTF processing, occlusion, reverb. [UNVERIFIED — not found in studied prior art].

---

## 3. Script API verificada

### Tipos core (scripts/3_game/sound.c)

```
enum WaveKind
{
    WAVEEFFECT, WAVEEFFECTEX, WAVESPEECH, WAVEMUSIC,
    WAVESPEECHEX, WAVEENVIRONMENT, WAVEENVIRONMENTEX,
    WAVEWEAPONS, WAVEWEAPONSEX, WAVEATTALWAYS, WAVEUI
}
```
[scripts\3_game\sound.c:1-14]

**`SoundParams`** — loads and validates a SoundSet by name:
```
class SoundParams
{
    void SoundParams(string name);
    proto native bool Load(string name);
    proto native bool IsValid();
    proto string GetName();
}
```
[scripts\3_game\sound.c:137-144]

**`SoundObjectBuilder`** — builds a SoundObject with environment variables:
```
class SoundObjectBuilder
{
    void SoundObjectBuilder(SoundParams soundParams);
    SoundObject BuildSoundObject();                        // llama g_Game.GetSoundScene().BuildSoundObject
    proto native void AddEnvSoundVariables(vector position);
    proto native void AddVariable(string name, float value);
}
```
[scripts\3_game\sound.c:82-108]

**`SoundObject`** — representa la fuente 3D:
```
class SoundObject
{
    proto native void SetParent(IEntity parent, int pivot = -1);
    proto native void SetPosition(vector position);
    proto native void SetKind(WaveKind kind);
    proto native void SetOcclusionObstruction(float occlusion, float obstruction);
}
```
[scripts\3_game\sound.c:111-134]

**`AbstractWave`** — handle to playing sound:
```
class AbstractWave
{
    proto void Play();
    proto void Stop();
    proto void Loop(bool setLoop);
    proto void SetVolumeRelative(float value);    // 0.0–1.0 relative to shader max
    proto void SetFadeInFactor(float volume);
    proto void SetFadeOutFactor(float volume);
    proto void SetDoppler(bool setDoppler);
    proto float GetLength();
    proto float GetCurrPosition();
    proto bool IsHeaderLoaded();
    AbstractWaveEvents GetEvents();               // accede a ScriptInvokers de eventos
}
```
[scripts\3_game\sound.c:155-230]

**`AbstractWaveEvents`** — lifecycle ScriptInvokers:
```
class AbstractWaveEvents
{
    ref ScriptInvoker Event_OnSoundWaveStarted;
    ref ScriptInvoker Event_OnSoundWaveStopped;
    ref ScriptInvoker Event_OnSoundWaveLoaded;
    ref ScriptInvoker Event_OnSoundWaveHeaderLoaded;
    ref ScriptInvoker Event_OnSoundWaveEnded;
}
```
[scripts\3_game\sound.c:146-153]

**`AbstractSoundScene`** — global sound engine access:
```
proto native AbstractWave Play2D(SoundObject soundObject, SoundObjectBuilder soundBuilder);
proto native AbstractWave Play3D(SoundObject soundObject, SoundObjectBuilder soundBuilder);
proto native float GetSoundVolume();
proto native void SetSoundVolume(float vol, float time);    // controla volumen GLOBAL
proto native float GetMusicVolume();
proto native void SetMusicVolume(float vol, float time);
// also: GetRadioVolume/SetRadioVolume, GetSpeechExVolume/SetSpeechExVolume
```
[scripts\3_game\sound.c:53-79]
Acceso: `g_Game.GetSoundScene()` [scripts\3_game\global\game.c:734]

### SEffectManager (scripts/3_game/effectmanager.c)

Static manager of Effects (sounds + particles). **Only exists on client** — on server `Init()` does not create sound maps.

**Verified sound methods:**

```
// Create + play at position
static EffectSound PlaySound(string sound_set, vector position,
    float play_fade_in = 0, float stop_fade_out = 0, bool loop = false);

// Create + play parented to an Object (follows object)
static EffectSound PlaySoundOnObject(string sound_set, Object parent_object,
    float play_fade_in = 0, float stop_fade_out = 0, bool loop = false);

// Create + play with pre-built SoundParams (more efficient if reused)
static EffectSound PlaySoundParams(notnull SoundParams params, vector position,
    float play_fade_in = 0, float stop_fade_out = 0, bool loop = false);

// With SoundParams cache (avoids recreating SoundParams object on each call)
static EffectSound PlaySoundCachedParams(string sound_set, vector position, ...);

// With environment variables (reverb, etc.)
static EffectSound PlaySoundEnviroment(string sound_set, vector position, ...);

// Cleanup seguro (respeta fade-out en curso)
static void DestroyEffect(Effect effect);
static bool DestroySound(EffectSound sound_effect);   // legacy alias
```
[scripts\3_game\effectmanager.c:169-256]

**WARNING:** All `Play*` methods register Effect in SEffectManager (retains `ref`). If `DestroyEffect` or `SetAutodestroy(true)` is not called, a memory leak occurs. [scripts\3_game\effectmanager.c:41-44]

### EffectSound (scripts/3_game/effects/effectsound.c)

High-level wrapper over AbstractWave:

```
class EffectSound : Effect
{
    void SetSoundSet(string snd);
    void SetSoundLoop(bool loop);
    void SetSoundFadeIn(float fade_in);
    void SetSoundFadeOut(float fade_out);
    void SetSoundVolume(float volume);         // relativo 0-1
    void SetSoundMaxVolume(float volume);      // max para fade-in
    void SetSoundWaveKind(WaveKind wave_kind);
    void SetDoppler(bool setDoppler);
    void SetEnviromentVariables(bool setEnvVariables);
    bool SoundPlay();
    void SoundStop();                          // respects fade-out if configured
    bool IsSoundPlaying();
    float GetSoundWaveLength();

    // ScriptInvokers para eventos propios:
    ref ScriptInvoker Event_OnSoundWaveStarted;
    ref ScriptInvoker Event_OnSoundWaveEnded;
    ref ScriptInvoker Event_OnSoundFadeInStopped;
    ref ScriptInvoker Event_OnSoundFadeOutStarted;
}
```
[scripts\3_game\effects\effectsound.c — completo]

(since 1.30 Exp: if `m_SoundFadeInDuration > 0`, `Event_OnSoundWaveStarted` calls `SetSoundVolume(0)` to prevent a one-frame spike at full volume — `exp\scripts\scripts\3_Game\Effects\EffectSound.c:549-555`. `[EXACT]` in `references/dayz-1-30-sound.md`.)

### Object.PlaySoundSet (scripts/3_game/entities/object.c)

Convenience method on any Object to play parented:

```
bool PlaySoundSet(out EffectSound sound, string sound_set, float fade_in, float fade_out, bool loop = false);
bool PlaySoundSetLoop(out EffectSound sound, string sound_set, float fade_in, float fade_out);
bool PlaySoundSetAtMemoryPoint(out EffectSound sound, string soundSet, string memoryPoint,
    bool looped = false, float play_fade_in = 0, float stop_fade_out = 0);
bool StopSoundSet(out EffectSound sound);
```
[scripts\3_game\entities\object.c:1243-1321]

**IMPORTANT:** All have guard `if (g_Game && !g_Game.IsDedicatedServer())` — **play only on client**. [scripts\3_game\entities\object.c:1245]

(until 1.29 / continues in 1.30 for `Object.PlaySoundSet`: actual guard is in `object.c:1249`.)
(since 1.30 Exp: item/player handlers use `!g_Game.IsHeadlessOrDedicatedServer()` — `ItemSoundHandler.c:121`, `PlayerSoundManager.c:105`, `DayZPlayerCfgSounds.c:335`. New proto: `Game.c:1132-1136`. `PlaySoundSet` on `Object` did **not** migrate.)

### g_Game.CreateSoundOnObject

```
proto native SoundOnVehicle CreateSoundOnObject(Object source, string sound_name, float distance, bool looped, bool create_local = false);
proto native SoundWaveOnVehicle CreateSoundWaveOnObject(Object source, SoundObject soundObject, AbstractWave soundWave);
```
[scripts\3_game\global\game.c:691-692]

`SoundOnVehicle` is an Entity class (not EffectSound):
```
class SoundOnVehicle extends Entity
{
    proto native float GetSoundLength();
};
```
[scripts\3_game\entities\soundonvehicle.c:1-4]

This method exists and differs from SEffectManager — used internally for vehicles. For item mods, `SEffectManager.PlaySoundOnObject` is preferred.

### Script category volume control

`AbstractSoundScene` exposes setters for global volume by category (Sound, Music, Radio, SpeechEx, VOIP). **There is NO per-sound-instance API beyond `SetVolumeRelative` on AbstractWave or `SetSoundVolume` on EffectSound.** [scripts\3_game\sound.c:64-75]

---

## 4. Sounds on Items (ItemBase)

### ItemSoundHandler — server→client pattern

Official mechanism for triggering sounds from server and synchronizing them to clients:

1. **Declare IDs** in `SoundConstants` (or custom added ones):
   ```
   class SoundConstants
   {
       const int ITEM_PLACE        = 1;
       const int ITEM_DEPLOY_LOOP  = 2;
       const int ITEM_DEPLOY       = 3;
       const int ITEM_FOLD_LOOP    = 4;
       const int ITEM_FOLD         = 5;
       const int ITEM_ATTACH       = 6;
       const int ITEM_DETACH       = 7;
       // ... hasta ITEM_SOUNDS_MAX = 63
   }
   ```
   [scripts\3_game\constants.c:415-435] [scripts\4_world\entities\itembase.c:137]

2. **Registrar soundsets** en `InitItemSounds()`:
   ```
   override void InitItemSounds()
   {
       super.InitItemSounds();
       ItemSoundHandler handler = GetItemSoundHandler();
       handler.AddSound(SoundConstants.ITEM_DEPLOY, "MiMod_Deploy_SoundSet");
       // para loop:
       SoundParameters params = new SoundParameters();
       params.m_Loop = true;
       handler.AddSound(SoundConstants.ITEM_DEPLOY_LOOP, "MiMod_DeployLoop_SoundSet", params);
   }
   ```
   [scripts\4_world\entities\itembase.c:4448-4465]

3. **Disparar desde servidor** (o SP):
   ```
   StartItemSoundServer(SoundConstants.ITEM_DEPLOY);           // one-shot
   StopItemSoundServer(SoundConstants.ITEM_DEPLOY_LOOP);       // para loop
   ```
   [scripts\4_world\entities\itembase.c:4468-4498]

4. **Client reception** via `OnVariablesSynchronized`:
   ```
   // In ItemBase.OnVariablesSynchronized (automatic if using handler):
   if (m_SoundSyncPlay != 0)
       m_ItemSoundHandler.PlayItemSoundClient(m_SoundSyncPlay, m_SoundSyncSlotID);
   if (m_SoundSyncStop != 0)
       m_ItemSoundHandler.StopItemSoundClient(m_SoundSyncStop);
   ```
   [scripts\4_world\entities\itembase.c:3319-3332]

**Used network variables:** `m_SoundSyncPlay` (int), `m_SoundSyncStop` (int), `m_SoundSyncSlotID` (int). Cleared 100ms later via `CallLater`. [scripts\4_world\entities\itembase.c:4468-4508]

**Documented limitation:** Can only synchronize one sound play and one stop at a time (a single int). For two simultaneous sounds, a second sync variable would be needed. [scripts\4_world\classes\soundhandlers\itemsoundhandler.c:19-20]

### PlaySoundSet directly on client

For objects already on client (e.g. local action feedback):
```
EffectSound m_RollSound;
PlaySoundSet(m_RollSound, "LFRS_Roll_SoundSet", 0, 0.5, true);  // loop con fade-out 0.5s
// ...
StopSoundSet(m_RollSound);
```
[scripts\3_game\entities\object.c:1243-1321]

---

## 5. Synchronization patterns (Multiplayer Gotcha)

**Audio IS client-only.** Server does not have `SEffectManager` or `Play*`. Patterns to synchronize:

| Pattern | Mechanism | Typical usage |
|---|---|---|
| `StartItemSoundServer` | Network variable + OnVariablesSynchronized | Items: deploy, place, looped deploy |
| `PlaySoundSet` in `OnVariablesSynchronized` | Existing network variable | Sound upon item state change |
| AnimEvent (bind in anim config) | Engine processes automatically on client | Footsteps, player actions |
| Direct `SEffectManager.PlaySound*` | Only in `#ifndef SERVER` or explicit guard | Local effects, impacts |

**For LF_RollingStone:** rolling sound can be triggered on client upon detecting object motion (speed > threshold), as `OnVariablesSynchronized` already receives synchronized position. No server needed for audio.

---

## 6. Player sounds

### PlayerSoundManagerBase

```
const float SOUNDS_HEARING_DISTANCE = 50;    // constante global

enum eSoundHandlers { STAMINA, HUNGER, INJURY, THIRST, COUNT }

class PlayerSoundManagerBase
{
    ref SoundHandlerBase m_Handlers[MAX_HANDLERS_COUNT];
    void RegisterHandler(SoundHandlerBase handler);
    SoundHandlerBase GetHandler(eSoundHandlers id);
}
```
[scripts\4_world\classes\soundhandlers\playersoundmanager.c:2-55]

Handlers separados: `StaminaSoundHandler`, `HungerSoundHandler`, `InjurySoundHandler`, `ThirstSoundHandler`, `FreezingSoundHandler`. Cada uno extiende `SoundHandlerBase`.

### Player footsteps

Handled in `DayZPlayerImplement.OnStepEvent`:
- Reads `DayZPlayerType.GetStepSoundLookupTable()` → surface table → soundset
- Builds `SoundObjectBuilder` with environment variables
- Calls `g_Game.GetSoundScene().Play3D(so, sob)` directly
- **Executes only on client** (`#ifndef SERVER`) [scripts\4_world\entities\dayzplayerimplement.c:3215-3230+]

### Archivos relevantes
- `scripts/4_world/entities/manbase/dayzplayer/dayzplayercfgsounds.c` — [UNVERIFIED exact existence, path deduced from vanilla structure]
- Voice/VON sounds: `AbstractSoundScene.SetSpeechExVolume` + WaveKind.WAVESPEECHEX
- (since 1.30 Exp: path exists as `exp\scripts\scripts\4_World\Entities\ManBase\DayZPlayer\DayZPlayerCfgSounds.c`. Attachment/particle sound registration uses `IsHeadlessOrDedicatedServer()` at `:335`.)
- (since 1.30 Exp: path exists as `exp\scripts\scripts\4_World\Entities\ManBase\DayZPlayer\DayZPlayerCfgSounds.c`. Attachment/particle sound registration uses `IsHeadlessOrDedicatedServer()` at `:335`.)

### HEAVY_BREATHING (since 1.30 Exp)

New `EPlayerSoundEventID.HEAVY_BREATHING` (`PlayerSoundEventHandler.c:38`), registered with `RegisterState(new HeavyBreathEvent1())` (`:99`). Class `HeavyBreathEvent1` in `HeavyBreathEvents.c:21-27` with `m_SoundVoiceAnimEventClassID = 907`. Vanilla fires it from silicosis (`Silicosis.c:105`). `[EXACT]`: `references/dayz-1-30-sound.md`.

---

## 7. Music: DynamicMusicPlayer

Complete ambient/contextual music system on client:

```
class DynamicMusicPlayer
{
    void SetCategory(DynamicMusicPlayerCategoryPlaybackData playbackData);
    void RegisterDynamicLocation(notnull Entity caller, int locationType, float locationSize);
    void UnregisterDynamicLocation(notnull Entity caller);
}

enum EDynamicMusicPlayerCategory
{
    NONE, MENU, CREDITS, TIME,
    LOCATION_STATIC, LOCATION_STATIC_PRIORITY, LOCATION_DYNAMIC
}
```
[scripts\3_game\systems\dynamicmusicplayer\dynamicmusicplayer.c:81-303]

**Playback interno:** usa `SoundObjectBuilder` + `g_Game.GetSoundScene().Play2D(soundObject, soundBuilder)` con `WaveKind.WAVEMUSIC`. [scripts\3_game\systems\dynamicmusicplayer\dynamicmusicplayer.c:511-538]

**Fade-out:** implemented via `AbstractWave.SetFadeOutFactor(volume)` on 0.2s tick. [scripts\3_game\systems\dynamicmusicplayer\dynamicmusicplayer.c:574-580]

**For mods:** a dynamic location can be registered (e.g. event zone) with `RegisterDynamicLocation`, playing `LOCATION_DYNAMIC` tracks when player enters. Track is a normal SoundSet with `WaveKind.WAVEMUSIC`.

(since 1.30 Exp: `RegisterDynamicLocation` remains in `DynamicMusicPlayer.c:289`. Each world instantiates its `DynamicMusicPlayerRegistry*` — Nasdara in `missionBase.c:130-132`. Static rectangular zones: `RegisterTrackLocationStaticMultiRectangle` (`DynamicMusicPlayerRegistry.c:224`, calls in `DynamicMusicPlayerRegistryNasdara.c:39-67`). 15 DAY/DUSK/DAWN/NIGHT time tracks, not hourly (`:71-93`). `DynamicMusicPlayerTimeOfDay.Translate` maps MORNING/NOON/AFTERNOON→DAY and EVENING→NIGHT (`DynamicMusicPlayer.c:1053-1070`).)

---

## 8. NoiseSystem

```
class NoiseSystem
{
    proto void AddNoise(EntityAI source_entity, NoiseParams noise_params,
        float external_strenght_multiplier = 1.0);
    proto void AddNoisePos(EntityAI source_entity, vector pos, NoiseParams noise_params,
        float external_strenght_multiplier = 1.0);
    proto void AddNoiseTarget(vector pos, float lifetime, NoiseParams noise_params,
        float external_strength_multiplier = 1.0);
    proto native float GetEnvironmentNoiseReduction(vector pos); // desde 1.30 Exp; Noise.c:13
}

class NoiseParams
{
    proto native void Load(string noise_name);        // loads from CfgNoises by name
    proto native void LoadFromPath(string noise_path); // path completo
}
```
[scripts\3_game\noise.c:1-23]

Acceso: `g_Game.GetNoiseSystem()` [scripts\3_game\global\game.c:737]

### How it feeds AI

En `DayZPlayerImplement.AddNoise`:
```
void AddNoise(NoiseParams noisePar, float noiseMultiplier = 1.0)
{
    if (noisePar != null)
        g_Game.GetNoiseSystem().AddNoise(this, noisePar, noiseMultiplier);
}
```
[scripts\4_world\entities\dayzplayerimplement.c:3204-3208]

(until 1.29: Multiplier is reduced with rain/wind via `NoiseAIEvaluate.GetNoiseReduction(g_Game.GetWeather())`.)
(since 1.30 Exp: obsolete. `GetEnvironmentNoiseReduction(pos)` is AI source of truth (`Noise.c:13`). `GetNoiseReduction` / `GetNoiseReductionByWeather` are `[Obsolete]` (`SensesAIEvaluate.c:92`, `Weather.c:454`). Footsteps no longer pass weather multiplier: `GetNoiseMultiplier(this)` (`DayZPlayerImplement.c:3472-3474`). Infected `AddNoise` carries no weather (`ZombieBase.c:597-600`). `class AIParams` adds snow/fog/wind/sandstorm (`exp\dz\DZ\data\aiconfigs\config.cpp:19-27`). Do not pass a multiplier that already includes weather: engine attenuates natively and you would duplicate reduction.)
Footsteps use noise types loaded from `DayZPlayerType.GetNoiseParamsLandLight()/LandHeavy()`. Gunfire uses `class NoiseShoot { strength = 82; type = "shot"; }` in weapon config [IMPWMODPart2\Weapons\Automatic\MCXSpear\config.cpp:73-77].

`AddNoiseTarget` allows creating a noise "decoy" at a fixed position with duration — useful for stun grenades or decoys.

**For LF_RollingStone:** if infected should react upon rolling, call `g_Game.GetNoiseSystem().AddNoise(this, noiseParams)` from item script (server) with a `NoiseParams` loaded from config.

---

## 9. Environment control (SoundControllerOverride)

```
proto native void SetSoundControllerOverride(string controllerName, float value, SoundControllerAction action);
proto native void MuteAllSoundControllers();
proto native void ResetAllSoundControllers();
```
[scripts\3_game\sound.c:38-48]

Available controllers (documented in proto comment):
`rain, night, meadow, trees, hills, houses, windy, deadBody, sea, forest, altitudeGround, altitudeSea, altitudeSurface, daytime, shooting, coast, waterDepth, overcast, fog, snowfall, caveSmall, caveBig`

---

## 10. What DOES NOT exist / typical confabulations

| Common confabulation | Verified reality |
|---|---|
| `GetGame().CreateSoundOnObject(obj, "MiSoundSet", ...)` for everything | Exists but returns `SoundOnVehicle`, NOT `EffectSound`. Name is soundset string, not file path. Prefer `SEffectManager.PlaySoundOnObject`. [game.c:691] |
| `SEffectManager` on server | **DOES NOT exist** — `Init()` is only called on client [effectmanager.c:498-506]. On server only `InitServer()` exists for particles. |
| Global script volume of a specific sound | No `SetMasterVolume`-type API for individual instances beyond `SetVolumeRelative(0-1)` in `AbstractWave`. Shader "volume" is fixed in config. |
| `OnSoundEvent` or automatic callback in ItemBase | NO such override exists. Item sounds are activated manually via `StartItemSoundServer` or `PlaySoundSet`. |
| `PlaySoundSet` working on server | Has guard `!g_Game.IsDedicatedServer()` — **silent on DS**. [object.c:1245] |

(since 1.30 Exp: that row remains true for `Object.PlaySoundSet`. Handlers also use `IsHeadlessOrDedicatedServer()`. Do not use `GetNoiseReductionByWeather()` in new code.)

| Public `DynamicMusicPlayer.PlayTrack(string)` | The `PlayTrack` method is **private**. Public API is `SetCategory`. [dynamicmusicplayer.c:511] |
| Multiple simultaneous sounds with `StartItemSoundServer` | Only 1 play + 1 stop synchronizable at a time by network protocol design. [itemsoundhandler.c:19-20] |

---

## 11. Mod recipes

### A. Simple sound on an item (without server synchronization)
```cpp
// config.cpp
class CfgSoundShaders
{
    class LFRS_Roll_SoundShader
    {
        samples[] = {{"MiMod\Sounds\roll_loop", 1}};
        volume = 1.0;
        range = 40;
        rangeCurve[] = {{0,1},{20,0.8},{40,0}};
    };
};
class CfgSoundSets
{
    class LFRS_Roll_SoundSet
    {
        soundShaders[] = {"LFRS_Roll_SoundShader"};
    };
};
```
```c
// Script: on item (client only)
EffectSound m_RollSound;

void StartRolling()
{
    if (!g_Game.IsDedicatedServer())
        PlaySoundSet(m_RollSound, "LFRS_Roll_SoundSet", 0.1, 0.5, true);
}

void StopRolling()
{
    if (!g_Game.IsDedicatedServer())
        StopSoundSet(m_RollSound);
}
```

### B. Synchronized sound server→client (ItemSoundHandler pattern)
```c
// Add custom ID in subclass or reuse SoundConstants

override void InitItemSounds()
{
    super.InitItemSounds();
    GetItemSoundHandler().AddSound(SoundConstants.ITEM_PLACE, "LFRS_Impact_SoundSet");
}

// From server upon detecting impact:
StartItemSoundServer(SoundConstants.ITEM_PLACE);
// Client plays it in OnVariablesSynchronized automatically.
```

### C. Dynamic contextual music
```c
// Register music zone when item enters game (from client/server):
DynamicMusicPlayer dmp = GetGame().GetMission().GetDynamicMusicPlayer(); // [NO VERIFICADO - acceso exacto]
dmp.RegisterDynamicLocation(this, DynamicMusicLocationTypes.CONTAMINATED_ZONE, 100.0);
// Al destruirse:
dmp.UnregisterDynamicLocation(this);
```

### D. Noise for infected AI
```c
// On server, upon rolling / impacting:
NoiseParams np = new NoiseParams();
np.Load("Footstep_Heavy");    // nombre de CfgNoises vanilla o custom
g_Game.GetNoiseSystem().AddNoise(this, np, 2.0);  // multiplicador x2
```

(since 1.30 Exp: do not multiply that `2.0` by a script-calculated weather reduction; the engine already attenuates natively at the coordinate.)

---

## 12. DayZ 1.30 Exp — radios, vegetation, destructor

Detalle `[EXACT]` en `references/dayz-1-30-sound.md`.

- **Radio / bunker:** `TransmitterBase.SOUND_BUNKER_STATIC_NOISE`; `UseBunkerStaticNoise()` = `IsTunedToBunkerFrequency() && SOUND_BUNKER_STATIC_NOISE != ""` (`TransmitterBase.c:4-6,135-137`). Proto in `ItemTransmitter` (`InventoryItem.c:25`). `PersonalRadio` / `BaseRadio` assign `"bunkerbroadcast_staticnoise_SoundSet"`.
- **Static vegetation:** `StaticObjectType` reads `CfgNonAIVehicles <Name> VegetationSounds` (`StaticObjectType.c:13-47`). Macro `CUSTOM_PLAYER_MOVEMENT_SOUNDSETS` in `basicDefines.hpp:310-338` (not in `:68-96`).
- **Event destructor:** `~SoundEventBase` does `if (g_Game) Stop();` (`SoundEvents.c:12-16`). Do not reimplement a 1.29 destructor in `InfectedSoundEventBase` subclasses.

---

## Fuentes

| Path | Content |
|---|---|
| `scripts\3_game\sound.c` | SoundParams, SoundObjectBuilder, SoundObject, AbstractWave, AbstractSoundScene, WaveKind |
| `scripts\3_game\effectmanager.c` | Full SEffectManager |
| `scripts\3_game\effects\effectsound.c` | Full EffectSound |
| `scripts\3_game\entities\object.c:1243` | PlaySoundSet, PlaySoundSetAtMemoryPoint |
| `scripts\3_game\entities\soundonvehicle.c` | SoundOnVehicle, SoundWaveOnVehicle |
| `scripts\3_game\global\game.c:691,734,737` | CreateSoundOnObject, GetSoundScene, GetNoiseSystem |
| `scripts\3_game\noise.c` | NoiseSystem, NoiseParams |
| `scripts\3_game\constants.c:415` | SoundConstants |
| `scripts\3_game\systems\dynamicmusicplayer\dynamicmusicplayer.c` | DynamicMusicPlayer |
| `scripts\4_world\entities\itembase.c:4448-4508` | InitItemSounds, StartItemSoundServer, StopItemSoundServer |
| `scripts\4_world\entities\itembase.c:3319` | OnVariablesSynchronized sound dispatch |
| `scripts\4_world\classes\soundhandlers\itemsoundhandler.c` | ItemSoundHandler |
| `scripts\4_world\classes\soundhandlers\playersoundmanager.c` | PlayerSoundManagerBase |
| `scripts\4_world\entities\dayzplayerimplement.c:3204,2486` | AddNoise, OnStepEvent |
| `IMPWMODPart2\Weapons\Automatic\Sounds\config.cpp` | Prior art: CfgSoundShaders with inline rangeCurve |
| `IMPWMODPart2\Weapons\Automatic\F2000\Sounds\config.cpp` | Prior art: vanilla base inheritance |
| `IMPWMODPart2\Weapons\Automatic\MCXSpear\config.cpp:59` | Prior art: soundSetShot in weapon mode + NoiseShoot |
| `DoorLockSystem\Scripts\...\ActionUnlockDLSDoor.c:63` | Prior art: building.PlaySound / PlaySoundLoop |
| `scripts\3_game\entities\staticobjecttype.c` | StaticObjectType / VegetationSounds (1.30) |
| `scripts\4_world\entities\itembase\transmitterbase.c` | SOUND_BUNKER_STATIC_NOISE |
| `scripts\3_game\systems\dynamicmusicplayer\dynamicmusicplayerregistrynasdara.c` | Nasdara music registry |
| `references/dayz-1-30-sound.md` | `[EXACT]` 1.30 blocks |

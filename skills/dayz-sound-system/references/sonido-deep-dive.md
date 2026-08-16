# 02 — Sistema de sonido DayZ (Enfusion/Enforce Script)
> Deep-dive verificado contra vanilla v1.24 scripts + prior art real. 2026-06-06.

---

## Resumen ejecutivo

El sistema de sonido de DayZ Enfusion tiene dos capas bien separadas:

1. **Config (no-script):** `CfgSoundShaders` + `CfgSoundSets` en `config.cpp`. Define qué archivo de audio suena, a qué volumen, y cómo atenúa con la distancia. Todo el motor lo resuelve automáticamente en 3D.
2. **Script API:** `EffectSound` / `SEffectManager` (cliente-only). El servidor NO puede reproducir sonidos directamente; para sincronizar audio en multiplayer se usan variables de red + `OnVariablesSynchronized`.

Para una piedra rodante (LF_RollingStone): lo más sencillo es definir un SoundSet en config, y dispararlo desde cliente (`PlaySoundSet` / `SEffectManager.PlaySoundOnObject`) dentro de eventos ya sincronizados (por ejemplo `OnVariablesSynchronized`, o al recibir el contacto local).

---

## 1. Pipeline de audio

### Formatos
- **Formato soportado:** `.ogg` (Vorbis) y `.wav`. En la práctica **todos los mods usan `.ogg`**; los archivos de IMP y armería van como `.ogg` sin extensión en las rutas del config (el engine la infiere).
- **WSS:** formato propietario Bohemia de sonido comprimido; en DayZ Standalone los mods usan directamente `.ogg`.
- Los samples se referencian **sin extensión** en `CfgSoundShaders`, p.ej.: `"IMPWMODPart2\Weapons\Automatic\F2000\Sounds\F2000_close"` — [IMPWMODPart2\Weapons\Automatic\F2000\Sounds\config.cpp:24].

### Dónde viven los archivos en un mod
```
MiMod/
├── Sounds/           ← archivos .ogg
├── config.cpp        ← CfgSoundShaders, CfgSoundSets
└── scripts/          ← lógica Enforce Script
```
Los paths en `samples[]` son relativos a la raíz del mod (igual que los paths de modelos).

---

## 2. Config verificada

### CfgSoundShaders

Define un "shader" de sonido: qué archivo(s) de audio, volumen, rango y curva de atenuación.

**Propiedades verificadas** [IMPWMODPart2\Weapons\Automatic\Sounds\config.cpp]:

| Propiedad | Tipo | Descripción |
|---|---|---|
| `samples[]` | array de pares `{ruta, peso}` | Lista de muestras con peso de aleatorización |
| `volume` | float | Volumen base (0–1 o más) |
| `range` | float | Distancia máxima en metros donde se escucha |
| `rangeCurve[]` | array de pares `{distancia, factor}` | Curva de atenuación por distancia |
| `rangeCurve` | string | Nombre de curva predefinida (p.ej. `"closeShotCurve"`) |

**Ejemplo real** (shader sin herencia, con curva inline):
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

**Ejemplo con herencia de base vanilla** (forma más limpia para mods):
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

Agrupa shaders en un "set" que el script referencia por nombre de cadena.

**Propiedades mínimas verificadas:**

| Propiedad | Descripción |
|---|---|
| `soundShaders[]` | Array de nombres de CfgSoundShaders a combinar |

**Propiedades adicionales** (heredadas de base, [NO VERIFICADO en vanilla descompilado de mods — ver Bistuido]): `sound3DProcessingType`, `volumeCurve`, `spatial`.

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

**SoundSet simple sin herencia** (para items, alarmas, etc.):
```cpp
class CfgSoundSets
{
    class LFRS_Roll_SoundSet
    {
        soundShaders[] = {"LFRS_Roll_SoundShader"};
    };
};
```
[NO VERIFICADO — patrón deducido de prior art; basta un shader para efectos simples]

### CfgSoundCurves / CfgSound3DProcessingTypes

- `CfgSoundCurves`: define curvas de volumen por nombre (p.ej. `"closeShotCurve"`). Las base vanilla existen; mods las referencian. [NO VERIFICADO en scripts descompilados — solo referencias por nombre en config prior art].
- `CfgSound3DProcessingTypes`: configura procesamiento HRTF, oclusión, reverb. [NO VERIFICADO — no encontrado en prior art estudiado].

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

**`SoundParams`** — carga y valida un SoundSet por nombre:
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

**`SoundObjectBuilder`** — construye un SoundObject con variables de entorno:
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

**`AbstractWave`** — handle al sonido en reproducción:
```
class AbstractWave
{
    proto void Play();
    proto void Stop();
    proto void Loop(bool setLoop);
    proto void SetVolumeRelative(float value);    // 0.0–1.0 relativo al max del shader
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

**`AbstractWaveEvents`** — ScriptInvokers del ciclo de vida:
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

**`AbstractSoundScene`** — acceso al motor de sonido global:
```
proto native AbstractWave Play2D(SoundObject soundObject, SoundObjectBuilder soundBuilder);
proto native AbstractWave Play3D(SoundObject soundObject, SoundObjectBuilder soundBuilder);
proto native float GetSoundVolume();
proto native void SetSoundVolume(float vol, float time);    // controla volumen GLOBAL
proto native float GetMusicVolume();
proto native void SetMusicVolume(float vol, float time);
// también: GetRadioVolume/SetRadioVolume, GetSpeechExVolume/SetSpeechExVolume
```
[scripts\3_game\sound.c:53-79]
Acceso: `g_Game.GetSoundScene()` [scripts\3_game\global\game.c:734]

### SEffectManager (scripts/3_game/effectmanager.c)

Gestor estático de Effects (sonidos + partículas). **Solo existe en cliente** — en servidor `Init()` no crea los mapas de sonido.

**Métodos de sonido verificados:**

```
// Crear + reproducir en posición
static EffectSound PlaySound(string sound_set, vector position,
    float play_fade_in = 0, float stop_fade_out = 0, bool loop = false);

// Crear + reproducir parented a un Object (sigue al objeto)
static EffectSound PlaySoundOnObject(string sound_set, Object parent_object,
    float play_fade_in = 0, float stop_fade_out = 0, bool loop = false);

// Crear + reproducir con SoundParams pre-construido (más eficiente si se reutiliza)
static EffectSound PlaySoundParams(notnull SoundParams params, vector position,
    float play_fade_in = 0, float stop_fade_out = 0, bool loop = false);

// Con caché de SoundParams (evita re-crear el objeto SoundParams cada llamada)
static EffectSound PlaySoundCachedParams(string sound_set, vector position, ...);

// Con variables de entorno (reverb, etc.)
static EffectSound PlaySoundEnviroment(string sound_set, vector position, ...);

// Cleanup seguro (respeta fade-out en curso)
static void DestroyEffect(Effect effect);
static bool DestroySound(EffectSound sound_effect);   // legacy alias
```
[scripts\3_game\effectmanager.c:169-256]

**ADVERTENCIA:** Todos los métodos `Play*` registran el Effect en SEffectManager (mantiene `ref`). Si no se llama `DestroyEffect` o `SetAutodestroy(true)`, hay memory leak. [scripts\3_game\effectmanager.c:41-44]

### EffectSound (scripts/3_game/effects/effectsound.c)

Wrapper de alto nivel sobre AbstractWave:

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
    void SoundStop();                          // respeta fade-out si está configurado
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

### Object.PlaySoundSet (scripts/3_game/entities/object.c)

Método de conveniencia en cualquier Object para reproducir parented:

```
bool PlaySoundSet(out EffectSound sound, string sound_set, float fade_in, float fade_out, bool loop = false);
bool PlaySoundSetLoop(out EffectSound sound, string sound_set, float fade_in, float fade_out);
bool PlaySoundSetAtMemoryPoint(out EffectSound sound, string soundSet, string memoryPoint,
    bool looped = false, float play_fade_in = 0, float stop_fade_out = 0);
bool StopSoundSet(out EffectSound sound);
```
[scripts\3_game\entities\object.c:1243-1321]

**IMPORTANTE:** Todos tienen guard `if (g_Game && !g_Game.IsDedicatedServer())` — **solo reproducen en cliente**. [scripts\3_game\entities\object.c:1245]

### g_Game.CreateSoundOnObject

```
proto native SoundOnVehicle CreateSoundOnObject(Object source, string sound_name, float distance, bool looped, bool create_local = false);
proto native SoundWaveOnVehicle CreateSoundWaveOnObject(Object source, SoundObject soundObject, AbstractWave soundWave);
```
[scripts\3_game\global\game.c:691-692]

`SoundOnVehicle` es una clase Entity (no EffectSound):
```
class SoundOnVehicle extends Entity
{
    proto native float GetSoundLength();
};
```
[scripts\3_game\entities\soundonvehicle.c:1-4]

Este método existe y es diferente de SEffectManager — se usa internamente para vehículos. Para mods de items, `SEffectManager.PlaySoundOnObject` es preferible.

### Control de volumen de categoría por script

`AbstractSoundScene` expone setters para volumen global por categoría (Sound, Music, Radio, SpeechEx, VOIP). **NO hay API por instancia de sonido más allá de `SetVolumeRelative` en AbstractWave o `SetSoundVolume` en EffectSound.** [scripts\3_game\sound.c:64-75]

---

## 4. Sonidos en Items (ItemBase)

### ItemSoundHandler — patrón server→client

El mecanismo oficial para disparar sonidos desde servidor y sincronizarlos a clientes:

1. **Declarar IDs** en `SoundConstants` (o propios añadidos):
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

4. **Recepción en cliente** vía `OnVariablesSynchronized`:
   ```
   // En ItemBase.OnVariablesSynchronized (automático si usas el handler):
   if (m_SoundSyncPlay != 0)
       m_ItemSoundHandler.PlayItemSoundClient(m_SoundSyncPlay, m_SoundSyncSlotID);
   if (m_SoundSyncStop != 0)
       m_ItemSoundHandler.StopItemSoundClient(m_SoundSyncStop);
   ```
   [scripts\4_world\entities\itembase.c:3319-3332]

**Variables de red usadas:** `m_SoundSyncPlay` (int), `m_SoundSyncStop` (int), `m_SoundSyncSlotID` (int). Se limpian 100ms después vía `CallLater`. [scripts\4_world\entities\itembase.c:4468-4508]

**Limitación documentada:** Solo puede sincronizar un sonido play y un stop a la vez (un único int). Para dos sonidos simultáneos, necesitarías una segunda variable de sync. [scripts\4_world\classes\soundhandlers\itemsoundhandler.c:19-20]

### PlaySoundSet directamente en cliente

Para objetos que ya están en cliente (p.ej. feedback de acción local):
```
EffectSound m_RollSound;
PlaySoundSet(m_RollSound, "LFRS_Roll_SoundSet", 0, 0.5, true);  // loop con fade-out 0.5s
// ...
StopSoundSet(m_RollSound);
```
[scripts\3_game\entities\object.c:1243-1321]

---

## 5. Patrones de sincronización (Multiplayer Gotcha)

**El audio ES solo cliente.** El servidor no tiene `SEffectManager` ni `Play*`. Los patrones para sincronizar:

| Patrón | Mecanismo | Uso típico |
|---|---|---|
| `StartItemSoundServer` | Variable de red + OnVariablesSynchronized | Items: deploy, place, looped deploy |
| `PlaySoundSet` en `OnVariablesSynchronized` | Variable de red existente | Sonido al cambiar estado del item |
| AnimEvent (bind en config anim) | Motor lo procesa en cliente automáticamente | Pasos, acciones de jugador |
| `SEffectManager.PlaySound*` directo | Solo en `#ifndef SERVER` o guard explícito | Efectos locales, impactos |

**Para LF_RollingStone:** el sonido de rodadura se puede disparar en cliente al detectar que el objeto se mueve (velocidad > umbral), ya que `OnVariablesSynchronized` ya recibe la posición sincronizada. No se necesita servidor para el audio.

---

## 6. Sonidos de jugador

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

### Pasos del jugador

Gestionados en `DayZPlayerImplement.OnStepEvent`:
- Lee `DayZPlayerType.GetStepSoundLookupTable()` → tabla superficie → soundset
- Construye `SoundObjectBuilder` con variables de entorno
- Llama `g_Game.GetSoundScene().Play3D(so, sob)` directamente
- **Solo ejecuta en cliente** (`#ifndef SERVER`) [scripts\4_world\entities\dayzplayerimplement.c:3215-3230+]

### Archivos relevantes
- `scripts/4_world/entities/manbase/dayzplayer/dayzplayercfgsounds.c` — [NO VERIFICADO existencia exacta, path deducido por estructura vanilla]
- Sonidos de voz/VON: `AbstractSoundScene.SetSpeechExVolume` + WaveKind.WAVESPEECHEX

---

## 7. Música: DynamicMusicPlayer

Sistema completo de música ambient/contextual en cliente:

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

**Fade-out:** implementado via `AbstractWave.SetFadeOutFactor(volume)` en tick de 0.2s. [scripts\3_game\systems\dynamicmusicplayer\dynamicmusicplayer.c:574-580]

**Para mods:** se puede registrar una ubicación dinámica (p.ej. zona de evento) con `RegisterDynamicLocation`, que reproduce tracks de `LOCATION_DYNAMIC` cuando el jugador entra. El track es un SoundSet normal con `WaveKind.WAVEMUSIC`.

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
}

class NoiseParams
{
    proto native void Load(string noise_name);        // carga desde CfgNoises por nombre
    proto native void LoadFromPath(string noise_path); // path completo
}
```
[scripts\3_game\noise.c:1-23]

Acceso: `g_Game.GetNoiseSystem()` [scripts\3_game\global\game.c:737]

### Cómo alimenta a la AI

En `DayZPlayerImplement.AddNoise`:
```
void AddNoise(NoiseParams noisePar, float noiseMultiplier = 1.0)
{
    if (noisePar != null)
        g_Game.GetNoiseSystem().AddNoise(this, noisePar, noiseMultiplier);
}
```
[scripts\4_world\entities\dayzplayerimplement.c:3204-3208]

El multiplicador se reduce con lluvia/viento mediante `NoiseAIEvaluate.GetNoiseReduction(g_Game.GetWeather())`. Los pasos usan tipos de ruido cargados de `DayZPlayerType.GetNoiseParamsLandLight()/LandHeavy()`. Los disparos usan `class NoiseShoot { strength = 82; type = "shot"; }` en config de arma [IMPWMODPart2\Weapons\Automatic\MCXSpear\config.cpp:73-77].

`AddNoiseTarget` permite crear un "decoy" de ruido en posición fija con duración — útil para granadas aturdidoras o señuelos.

**Para LF_RollingStone:** si se quiere que los infectados reaccionen al rodar, llamar `g_Game.GetNoiseSystem().AddNoise(this, noiseParams)` desde el script del item (servidor) con un `NoiseParams` cargado desde config.

---

## 9. Control de entorno (SoundControllerOverride)

```
proto native void SetSoundControllerOverride(string controllerName, float value, SoundControllerAction action);
proto native void MuteAllSoundControllers();
proto native void ResetAllSoundControllers();
```
[scripts\3_game\sound.c:38-48]

Controladores disponibles (documentados en el comment del proto):
`rain, night, meadow, trees, hills, houses, windy, deadBody, sea, forest, altitudeGround, altitudeSea, altitudeSurface, daytime, shooting, coast, waterDepth, overcast, fog, snowfall, caveSmall, caveBig`

---

## 10. Qué NO existe / confabulaciones típicas

| Confabulación común | Realidad verificada |
|---|---|
| `GetGame().CreateSoundOnObject(obj, "MiSoundSet", ...)` para todo | Existe pero devuelve `SoundOnVehicle`, NO `EffectSound`. El nombre es string de soundset, no de archivo. Preferir `SEffectManager.PlaySoundOnObject`. [game.c:691] |
| `SEffectManager` en servidor | **NO existe** — `Init()` solo se llama en cliente [effectmanager.c:498-506]. En servidor solo existe `InitServer()` para partículas. |
| Volumen global por script de un sonido específico | No hay API tipo `SetMasterVolume` para instancias individuales más allá de `SetVolumeRelative(0-1)` en `AbstractWave`. El "volumen" del shader es fijo en config. |
| `OnSoundEvent` o callback automático en ItemBase | NO existe tal override. Los sonidos de items se activan manualmente vía `StartItemSoundServer` o `PlaySoundSet`. |
| `PlaySoundSet` funcionando en servidor | Tiene guard `!g_Game.IsDedicatedServer()` — **silencioso en DS**. [object.c:1245] |
| `DynamicMusicPlayer.PlayTrack(string)` público | El método `PlayTrack` es **privado**. La API pública es `SetCategory`. [dynamicmusicplayer.c:511] |
| Múltiples sonidos simultáneos con `StartItemSoundServer` | Solo 1 play + 1 stop sincronizables a la vez por diseño del protocolo de red. [itemsoundhandler.c:19-20] |

---

## 11. Recetas para mods

### A. Sonido simple en un item (sin sincronización server)
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
// Script: en el item (solo cliente)
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

### B. Sonido sincronizado server→client (patrón ItemSoundHandler)
```c
// Añadir ID propio en subclase o reusar SoundConstants

override void InitItemSounds()
{
    super.InitItemSounds();
    GetItemSoundHandler().AddSound(SoundConstants.ITEM_PLACE, "LFRS_Impact_SoundSet");
}

// Desde servidor al detectar impacto:
StartItemSoundServer(SoundConstants.ITEM_PLACE);
// El client lo reproduce en OnVariablesSynchronized automáticamente.
```

### C. Música contextual dinámica
```c
// Registrar zona musical cuando el item entra en juego (desde cliente/servidor):
DynamicMusicPlayer dmp = GetGame().GetMission().GetDynamicMusicPlayer(); // [NO VERIFICADO - acceso exacto]
dmp.RegisterDynamicLocation(this, DynamicMusicLocationTypes.CONTAMINATED_ZONE, 100.0);
// Al destruirse:
dmp.UnregisterDynamicLocation(this);
```

### D. Ruido para AI infectados
```c
// En servidor, al rodar / impactar:
NoiseParams np = new NoiseParams();
np.Load("Footstep_Heavy");    // nombre de CfgNoises vanilla o custom
g_Game.GetNoiseSystem().AddNoise(this, np, 2.0);  // multiplicador x2
```

---

## Fuentes

| Ruta | Contenido |
|---|---|
| `scripts\3_game\sound.c` | SoundParams, SoundObjectBuilder, SoundObject, AbstractWave, AbstractSoundScene, WaveKind |
| `scripts\3_game\effectmanager.c` | SEffectManager completo |
| `scripts\3_game\effects\effectsound.c` | EffectSound completo |
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
| `IMPWMODPart2\Weapons\Automatic\Sounds\config.cpp` | Prior art: CfgSoundShaders con rangeCurve inline |
| `IMPWMODPart2\Weapons\Automatic\F2000\Sounds\config.cpp` | Prior art: herencia de base vanilla |
| `IMPWMODPart2\Weapons\Automatic\MCXSpear\config.cpp:59` | Prior art: soundSetShot en weapon mode + NoiseShoot |
| `DoorLockSystem\Scripts\...\ActionUnlockDLSDoor.c:63` | Prior art: building.PlaySound / PlaySoundLoop |

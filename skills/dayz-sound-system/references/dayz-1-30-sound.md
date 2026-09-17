# DayZ 1.30 Exp — sound, NoiseSystem, music, radios

Citations re-opened under `exp\` (build 1.30.164014). Do not copy digest `[EXACT]` blocks; line numbers below are from the files opened here.

## Server / headless guards

`Object.PlaySoundSet` is **still** `!g_Game.IsDedicatedServer()` in 1.30:

```c
// [EXACT] exp\scripts\scripts\3_Game\Entities\Object.c:1247
	bool PlaySoundSet( out EffectSound sound, string sound_set, float fade_in, float fade_out, bool loop = false )
	{
		if ( g_Game && !g_Game.IsDedicatedServer() )
		{
```

(hasta 1.29: that was the only documented guard.)

(desde 1.30 Exp: handlers that must not run on headless clients use the new proto.)

```c
// [EXACT] exp\scripts\scripts\3_Game\Global\Game.c:1132
	/**
	 \brief Check whether the application is headless or a dedicated server (it combines IsDedicatedServer and IsHeadless)
		\note This includes servers with a head as well (-headlessMode=0)
	*/
	proto native bool		IsHeadlessOrDedicatedServer();
```

```c
// [EXACT] exp\scripts\scripts\4_World\Classes\SoundHandlers\ItemSoundHandler.c:121
		if (g_Game.IsHeadlessOrDedicatedServer())
			return;
```

```c
// [EXACT] exp\scripts\scripts\4_World\Classes\SoundHandlers\PlayerSoundManager.c:105
		if( !g_Game.IsHeadlessOrDedicatedServer() ) 
		{
			m_ClientCharacterDistanceCheck.Run(2, this, "CheckAllowUpdate", null, true);
		}
```

```c
// [EXACT] exp\scripts\scripts\4_World\Entities\ManBase\DayZPlayer\DayZPlayerCfgSounds.c:335
	if(!g_Game.IsHeadlessOrDedicatedServer())//sounds are unnecessary on server
	{
```

`SEffectManager.Cleanup` warns if sound maps exist on that side (`EffectManager.c:536-542`). `IsHeadlessOrDedicatedServer` is **not** in 1.29 `Game.c`.

`[DESIGN]` New synced item sounds: prefer `IsHeadlessOrDedicatedServer()` in client play/stop paths. `PlaySoundSet` on `Object` still uses `IsDedicatedServer()` — a headless client with a head (`-headlessMode=0` is still dedicated+head per the proto note) is a different case; do not assume `PlaySoundSet` migrated.

## EffectSound fade-in peak

```c
// [EXACT] exp\scripts\scripts\3_Game\Effects\EffectSound.c:549
	void Event_OnSoundWaveStarted()
	{
		m_SoundWaveIsPlaying = true;
		if (m_SoundFadeInDuration > 0)
		{
			SetSoundVolume(0);
		}
```

(hasta 1.29: `Event_OnSoundWaveStarted` set `m_SoundWaveIsPlaying` and invoked invokers with no volume zeroing.) `[DESIGN]` Looped item sounds with `SetSoundFadeIn` > 0 no longer start at full volume for one frame.

## `HEAVY_BREATHING` (anim event 907)

```c
// [EXACT] exp\scripts\scripts\4_World\Classes\SoundEvents\PlayerSoundEvents\PlayerSoundEventHandler.c:38
	HEAVY_BREATHING,
```

```c
// [EXACT] exp\scripts\scripts\4_World\Classes\SoundEvents\PlayerSoundEvents\Events\HeavyBreathEvents.c:21
class HeavyBreathEvent1 : HeavyBreathSoundEventBase
{
	void HeavyBreathEvent1()
	{
		m_ID = EPlayerSoundEventID.HEAVY_BREATHING;
		m_SoundVoiceAnimEventClassID = 907;
	}
```

Registered in `PlayerSoundEventHandler.c:99`. Vanilla trigger from silicosis: `Silicosis.c:105` `RequestSoundEventEx(EPlayerSoundEventID.HEAVY_BREATHING, true, EPlayerSoundEventParam.HIGHEST_PRIORITY)`.

## Dynamic music per world

`RegisterDynamicLocation` is **still** on `DynamicMusicPlayer.c:289` (the 1.24 cite in the skill is not stale for that method).

(desde 1.30 Exp: each world constructs its own registry.)

```c
// [EXACT] exp\scripts\scripts\5_Mission\mission\missionBase.c:130
			case "nasdara":
				m_WorldData = new NasdaraData();
				m_DynamicMusicPlayerRegistry = new DynamicMusicPlayerRegistryNasdara();
				break;
```

Nasdara static boxes use `RegisterTrackLocationStaticMultiRectangle` (`DynamicMusicPlayerRegistry.c:224-244`, calls at `DynamicMusicPlayerRegistryNasdara.c:39-67`). 15 time-of-day tracks (DAY/DUSK/DAWN/NIGHT), not hourly (`:71-93`).

```c
// [EXACT] exp\scripts\scripts\3_Game\Systems\DynamicMusicPlayer\DynamicMusicPlayer.c:1053
class DynamicMusicPlayerTimeOfDay : WorldDataDaytime
{
	//! translates WorldDataDaytime -> DynamicMusicPlayerTimeOfDay
	static int Translate(int value)
	{
		switch (value)
		{
			case MORNING:
				return DAY;
			case NOON:
				return DAY;
			case AFTERNOON:
				return DAY;
			case EVENING:
				return NIGHT;
```

## Transmitter bunker static

```c
// [EXACT] exp\scripts\scripts\4_World\Entities\ItemBase\TransmitterBase.c:4
	string SOUND_RADIO_TURNED_ON 		= "";
	string SOUND_BUNKER_STATIC_NOISE 	= "";
```

```c
// [EXACT] exp\scripts\scripts\4_World\Entities\ItemBase\TransmitterBase.c:135
	protected bool UseBunkerStaticNoise()
	{
		return IsTunedToBunkerFrequency()  &&  SOUND_BUNKER_STATIC_NOISE != "";
	}
```

Proto lives on `ItemTransmitter` (file `InventoryItem.c`), not a method of class `InventoryItem`:

```c
// [EXACT] exp\scripts\scripts\4_World\Entities\Core\Inherited\InventoryItem.c:25
	proto native bool IsTunedToBunkerFrequency();
```

```c
// [EXACT] exp\scripts\scripts\4_World\Entities\ItemBase\TransmitterBase\PersonalRadio.c:6
		SOUND_BUNKER_STATIC_NOISE = "bunkerbroadcast_staticnoise_SoundSet";
```

Same assignment on `BaseRadio.c:6`. `SetNextFrequency` already calls `SetSynchDirty()` (`TransmitterBase.c:49`). `[UNVERIFIED]` native MHz that `IsTunedToBunkerFrequency` matches.

## Vegetation step sounds on static objects

```c
// [EXACT] exp\scripts\scripts\3_Game\Entities\StaticObjectType.c:13
		string pathBase = "CfgNonAIVehicles " + GetName() + " VegetationSounds";
		if (!g_Game.ConfigIsExisting(pathBase))
			return;
```

```c
// [EXACT] exp\scripts\scripts\3_Game\Entities\StaticObjectType.c:44
	SoundObjectBuilder GetVegetationSoundBuilderFromEventID(int stepEventID)
	{
		if (m_CustomVegetationSoundsMap)
			return m_CustomVegetationSoundsMap.Get(stepEventID);
```

Macro `CUSTOM_PLAYER_MOVEMENT_SOUNDSETS` — `exp\dz\DZ\data\basicDefines.hpp:310-338` (digest H cited `:68-96`; those lines are wetness/energy `#define`s). Anim event IDs: walk 1,2,23,24,51,52; crouch 21,22,31…; run 3,4,17…; sprint 5,6,35…; scuff 7,8.

## Infected sound-event destructor

```c
// [EXACT] exp\scripts\scripts\4_World\Classes\SoundEvents\SoundEvents.c:12
	void ~SoundEventBase()
	{
		if (g_Game) 
			Stop();
	}
```

`[DESIGN]` Do not re-add a 1.29-style `~InfectedSoundEventBase` that calls `m_SoundSetCallback.Stop()` after `g_Game` is gone.

## NoiseSystem (shared with `dayz-ai-patterns`)

See `dayz-ai-patterns/references/dayz-1-30-ai.md`. In this extract: `Noise.c:12-13`, `DayZPlayerImplement.c:3472-3474`, `ZombieBase.c:597-600`, `AIParams` at `exp\dz\DZ\data\aiconfigs\config.cpp:19-27`.

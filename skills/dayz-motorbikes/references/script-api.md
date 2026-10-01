# Motorbike Script API (`Motorbike.c` and `MotorbikeScript.c`)

This document compiles the complete native interface (`proto native`) of `Motorbike.c`, simulation callbacks, the `MotorbikeScript.c` lifecycle, network synchronization variables, and the differences table relative to `CarScript.c`.

---

## 1. Proto native Signatures of Motorbike.c

All native functions declared in `exp\scripts\scripts\3_Game\Vehicles\Motorbike.c` (in-game `scripts\3_Game\Vehicles\Motorbike.c`):

```c
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:100
proto native float GetSteering();
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:103
proto native void SetSteering(float value);

// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:106
proto native bool CanPickUp();
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:109
proto native void PickUp();

// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:112
proto native bool IsFallen();
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:115
proto native bool FallOver();

// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:118
proto native float GetThrottle();
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:121
proto native void SetThrottle(float value);

// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:124
proto native int GetClutch();
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:127
proto native void SetClutch(float value);

// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:130
proto native float GetBrake();
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:133
proto native void SetBrake(float value);

// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:136
proto native float GetHandbrake();
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:139
proto native void SetHandbrake(float value);

// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:142
proto native float GetKickstand();
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:145
proto native void SetKickstand(float value);

// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:148
proto native float EngineGetRPMMin();
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:151
proto native float EngineGetRPMIdle();
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:154
proto native float EngineGetRPMMax();
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:157
proto native float EngineGetRPMRedline();
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:160
proto native float EngineGetRPM();
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:163
proto native bool EngineIsOn();
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:166
proto native void EngineStart();
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:169
proto native void EngineStop();

// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:172
proto native vector GetEnginePos();
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:175
proto native void SetEnginePos(vector pos);

// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:178
proto native int GetCurrentGear();
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:181
proto native int GetGear();
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:184
proto native int GetNeutralGear();
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:187
proto native int GetGearCount();
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:190
proto native void ShiftUp();
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:193
proto native void ShiftTo(int gear);
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:196
proto native void ShiftDown();

// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:199
proto native CarGearboxType GearboxGetType();
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:202
proto native CarAutomaticGearboxMode GearboxGetMode();

// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:205
proto native bool WheelIsAnyLocked();
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:212
proto native float WheelGetAngularVelocity(int wheelIdx);
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:219
proto native bool WheelHasContact(int wheelIdx);
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:226
proto native vector WheelGetContactPosition(int wheelIdx);
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:233
proto native vector WheelGetPositionLS(int wheelIdx);
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:240
proto native vector WheelGetContactNormal(int wheelIdx);
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:247
proto native vector WheelGetDirection(int wheelIdx);
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:254
proto native SurfaceInfo WheelGetSurface(int wheelIdx);
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:261
proto native CarWheelWaterState WheelGetWaterState(int wheelIdx);
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:268
proto native EntityAI WheelGetEntity(int wheelIdx);
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:275
proto native bool WheelIsLocked(int wheelIdx);
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:278
proto native int WheelCount();
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:281
proto native int WheelCountPresent();

// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:288
proto native float GetFluidCapacity(MotorbikeFluid fluid);
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:296
proto native float GetFluidFraction(MotorbikeFluid fluid);
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:299
proto native void Leak(MotorbikeFluid fluid, float amount);
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:302
proto native void LeakAll(MotorbikeFluid fluid);
// exp\scripts\scripts\3_Game\Vehicles\Motorbike.c:305
proto native void Fill(MotorbikeFluid fluid, float amount);
```

---

## 2. Engine-Script Events and Callbacks in Motorbike.c

- `protected override event typename GetOwnerStateType()` (`Motorbike.c:33-36`): Returns `MotorbikeOwnerState`.
- `protected override event typename GetMoveType()` (`Motorbike.c:39-42`): Returns `MotorbikeMove`.
- `float GetSpeedometer()` (`Motorbike.c:45-52`): Returns longitudinal speed by multiplying projection by 3.6 (km/h).
- `float GetSpeedometerAbsolute()` (`Motorbike.c:55-58`): `Math.AbsFloat(GetSpeedometer())`.
- `override bool IsAreaAtDoorFree(...)` (`Motorbike.c:60-68`): Unconditionally returns `true` (motorbikes have no doors).
- `bool OnBeforeEngineStart()` (`Motorbike.c:312-316`): Callback evaluated before allowing engine start. `MotorbikeScript.c:1558-1564` checks that operational state is `EMotorbikeOperationalState.OK`.
- `void OnEngineStart()` (`Motorbike.c:321`, empty): invoked upon starting. The override in `MotorbikeScript.c:1003-1024` updates headlights and plays `START_OK`.
- `void OnEngineStop()` (`Motorbike.c:326`): Invoked upon engine stopping.
- `void OnGearChanged(int newGear, int oldGear)` (`Motorbike.c:334`): Invoked upon changing gear.
- `void OnFluidChanged(MotorbikeFluid fluid, float newValue, float oldValue)` (`Motorbike.c:344`): Invoked on the owner upon fluid changes.
- `float OnSound(MotorbikeSoundCtrl ctrl, float oldValue)` (`Motorbike.c:354-358`): Modulates sound controllers (`ENGINE`, `RPM`, `SPEED`, `PLAYER`).
- `void OnStabilityStart()` (`Motorbike.c:363`): Invoked when the motorbike regains balance.
- `void OnStabilityStop()` (`Motorbike.c:368`): Invoked when the motorbike falls to the ground.

---

## 3. Lifecycle and Synchronization in MotorbikeScript.c

### Constructor (`MotorbikeScript.c:105-148`)
1. Activates event mask: `SetEventMask(EntityEvent.POSTSIMULATE | EntityEvent.POSTFRAME);` (`line 111`).
2. Instantiates `m_LightsComponent = VehicleLightsComponent(this);` and registers selections:
   - `"FrontOn"`, `"FrontOff"`, `"BrakeOn"`, `"BrakeOff"`, `"TailOn"`, `"TailOff"`, `"DashboardOn"`, `"DashboardOff"`.
   - Registers base profiles: `VehicleLightProfileFront` and `VehicleLightProfileRear`.
3. Instantiates `m_HornComponent = VehicleHornComponent(this);` in `OFF` mode.
4. Initializes particles via `InitializeParticles()` (`lines 174-205`).
5. Deploys kickstand: `SetKickstand(1);` (`line 141`).
6. Registers network synchronization:
   ```c
   RegisterNetSyncVariableBool("m_BrakesArePressed");
   RegisterNetSyncVariableBoolSignal("m_PlayCrashSoundLight");
   RegisterNetSyncVariableBoolSignal("m_PlayCrashSoundHeavy");
   RegisterNetSyncVariableInt("m_HornComponent.m_Mode", VehicleHornMode.OFF, VehicleHornMode.COUNT);
   ```

### Central Economy and Persistence
- `override void EEOnCECreate()` (`MotorbikeScript.c:440-447`): Assigns random initial fuel between 0.0 and 35% of capacity:
  `float maxVolume = GetFluidCapacity( MotorbikeFluid.FUEL );`, `float amount = Math.RandomFloat(0.0, maxVolume * 0.35 );` and `Fill( MotorbikeFluid.FUEL, amount );` (`lines 443-446`).
- **Persistence (`OnStoreSave`/`OnStoreLoad`)**: `MotorbikeScript.c` does **NOT** implement these methods; it delegates directly to standard serialization of `Transport` and `EntityAI`.

---

## 4. Relevant Global Constants (`constants.c`)

Located in `exp\scripts\scripts\3_Game\constants.c`:
- `ENVIRO_HEATCOMFORT_MOTORBIKE_SPEED_MIN = 20.0;` (`line 792`)
- `ENVIRO_HEATCOMFORT_MOTORBIKE_SPEED_MAX = 100.0;` (`line 793`)
- `ENVIRO_HEATCOMFORT_MOTORBIKE_TARGET_MAX = 0.8;` (`line 794`)
- `MOTORBIKES_CONTACT_DMG_THRESHOLD_SMALL = 25.0;` (`line 898`)
- `MOTORBIKES_CONTACT_DMG_THRESHOLD_MID = 40.0;` (`line 899`)
- `MOTORBIKES_CONTACT_DMG_MIN = 10.0;` (`line 900`)
- `MOTORBIKES_CONTACT_DMG_KILLCREW = 80.0;` (`line 901`)

---

## 5. Table of What Does NOT Exist in Motorbikes vs CarScript

| Car Subsystem | Status in Motorbike (`MotorbikeScript`) | Alternative or Behavior |
|---|---|---|
| `class Axles` | **Nonexistent** | Flat `class Wheels { class Front; class Rear; }` |
| Doors (`CarDoor`) | **Nonexistent** | No doors; `IsAreaAtDoorFree` always returns `true` (`Motorbike.c:60-68`) |
| Radiator / Coolant circuit | **Nonexistent / Non-vital** | `IsVitalRadiator()` returns `false` (`MotorbikeScript.c:321-324`). No temperature gauge in HUD (`MotorBikeHud.c:191-194`) |
| Oil / Brake fluid circuit | Declared in config, unused in script | `MotorbikeScript` declares capacities (`config.cpp:45-48`), but `MotorbikeScript.c` only uses `MotorbikeFluid.FUEL` |
| Battery mandatory for ignition | **Depends on override** | `Transport.NeedElectricitySourceDevice()` returns `true` (`Transport.c:821-824`) and `MotorbikeScript` does not change it; `Motorbike_01`/`_02` override it to `false` (`Motorbike_01.c:33-36`, `Motorbike_02.c:34-37`). A bike inheriting from `MotorbikeScript` must override it |
| Door actions (`ActionOpenCarDoors`) | **Nonexistent** | In `Motorbike_01` flip-up seat `SeatDriver` exists |
| Parking handbrake | **Nonexistent** | Handbrake channel actuates front brake (`SetHandbrake`, `Motorbike.c:135-139`; `Brakes.Front.input = 1`, `config.cpp:257`); handbrake indicator light is hidden in HUD (`MotorBikeHud.c:196`) |
| Symmetrical 4-wheel steering | **Nonexistent** | Simulation with dynamic lean (`maxLeanAngle[]`) and `tipoverAngle` |
| Dismount in gear without stalling | **Nonexistent** | If driver exits in gear, engine stops (`OnDriverExit` → `EngineStop()`, `MotorbikeScript.c:217-222`) |

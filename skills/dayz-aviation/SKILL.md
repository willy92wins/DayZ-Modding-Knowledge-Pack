---
name: dayz-aviation
description: >
  DayZ aviation modding for planes, seaplanes and helicopters. Covers the
  source-verified CarScript-as-aviation patterns, custom flight physics
  (lift/drag/stall, atmosphere, NaN guards), controls and input bindings,
  PID stabilization, rotors/propellers, AnimationSources, aviation memory
  points, dials, buoyancy, retractable gear, sounds and damage zones. Use for
  helicopter, plane, aircraft, flight model, rotor, propeller, elevator,
  aileron, rudder, throttle, autopilot, seaplane/flying boat, axis_thruster,
  dial_horizon/dial_altitude, stall warning, Cessna, Spitfire, Catalina,
  Tigermoth or biplane. Always invoke before authoring/debugging aviation
  entity code or config; compose with enforce-script-reference and
  dayz-model-pipeline.
---

# DayZ Aviation Modding

**DayZ has no built-in aviation class.** The proven pattern (validated in LM_Planes by Llama + Itspete-Here): hack `CarScript` as the aviation base, override its physics inside scripts, and use `class Buoyancy` for seaplane behavior. Don't try to make planes work from `EntityAI` or `Inventory_Base` — `CarScript` gives you wheels, seats, sound integration, and damage system for free.

This skill compiles patterns extracted from LM_Planes (Workshop ID `3730564764`) — the only real deployable aviation mod in Llama's catalog, with 8 aircraft + 1 amphibious car (Patty_Wagon) sharing one base class `LlamaPlaneScript`.

## Preflight invariants (check before first boot) (added 2026-07-10, LFHeli phase-1)

- **`EOnSimulate` does NOT fire on a CarScript child by default.** Vanilla `CarScript` registers only
  `POSTSIMULATE`/`POSTFRAME` (`P:\scripts\4_world\entities\vehicles\carscript.c:325-326`, verified
  2026-07-10). Any aviation flight loop living in `EOnSimulate` must add
  `SetEventMask(EntityEvent.SIMULATE)` in the class ctor — RFFS does exactly this (`RFFSHeli_Core.c:180-181`).
  Symptom if missed: mod compiles, spawns, idles normally — and the flight model silently never runs.
- **Native `Helicopter`/`HelicopterScript` is a STUB** — empty `EOnPostSimulate` + empty engine hooks
  (`P:\scripts\4_world\entities\vehicles\helicopterscript.c:1-35`, verified 2026-07-10). Do not inherit
  from it expecting flight behavior; use CarScript-as-aviation (below).
- **Custom flight inputs are silent-fail wiring** (added 2026-07-12, LFHeli W4). A `UA*` action name
  typo'd anywhere in the chain (`inputs.xml` declaration ↔ `SyncedValue("...")` call ↔ stringtable
  `loc=` key) compiles clean and reads 0 forever — the channel is dead with zero errors. Verify the
  names 1:1 character-by-character across the three files BEFORE the first boot. `SyncedValue` returns
  `<0,1>` per action (`P:\scripts\3_game\inputapi\uainput.c:106-110`); opposing actions compose to one
  [-1,1] channel, read server-side via `CrewMember(0).GetInputInterface()` (`man.c:19` — the
  SIB/RFFS/MH6 pattern). Register via `CfgMods.<Mod>.inputs = "<Mod>/inputs.xml"`; `loc=` keys resolve
  from the mod-root `stringtable.csv`.
- **Expansion heli preset = the muscle-memory default** for new heli bindings (verified from
  `DayZExpansion\Vehicles\Scripts\Data\Inputs.xml` preset block): cyclic `kW/kS/kA/kD`, collective
  up/down `kLShift`/`kZ`, anti-torque `kQ`/`kE`, auto-hover `kX` (+ gamepad: thumbstick cyclic,
  triggers collective, shoulders anti-torque).
- **Strict-equality gates in a sealed solver want the deadzone UPSTREAM.** If the flight model gates
  on an exact input value (LFHeli weathervane: `pedal == 0.0`), put the analog deadzone
  (snap-to-zero + rescale `(|v|-dz)/(1-dz)`, LFHeli uses 0.10) in the INPUT READER, not the solver —
  the sealed solver and its offline twin stay byte-identical, and keyboard 0/1 input passes through
  unchanged.
- **Custom vehicle inputs need CLIENT-side `SyncedValue` priming — and NO input `<context>`** (added
  2026-07-12, LFHeli W4H — the fix that actually worked, after a context-membership hypothesis was
  refuted). Reading server-side is NOT enough by itself: the owner-DRIVER client must call
  `player.GetInputInterface().SyncedValue("UA...")` for EACH custom action every tick (return value
  discarded) — that call is what enrolls the action in the synced input stream the server reads.
  Priming with `UAInput.LocalValue()` (via a persistent wrapper) does NOT — `LocalValue` is gated by
  the vehicle's active input group and never reaches the synced stream, so the server's `SyncedValue`
  stays 0 in the seat. Symptom: custom keys dead ONLY while seated, vanilla car inputs still work.
  You do NOT need `<context name="car">`: RFFS (a shipped CarScript heli that works) declares none and
  calls no `ActivateContext`/`ActivateExclude` — its `modded_Inputs.xml` is only
  `<actions>`+`<sorting>`+`<preset>` (client prime `RFFSHeli_Core.c:491-501,1145`; server read
  `:547-554`). Meta-lesson: when diagnosing "custom vehicle inputs read 0 in the seat", extract and
  read the `modded_Inputs.xml` of the CLOSEST-architecture shipped mod (RFFS for CarScript+SyncedValue),
  not the ones that run their own Pawn (MH6/Expansion) — those don't answer the context/priming question.
- **Kinematic `SetVelocity` DOES fly a CarScript — a rubberband is client smoothing fighting native
  replication, NOT the mode** (added 2026-07-13, LFHeli, CORRECTED — an earlier draft here wrongly
  concluded "pivot to force-based"; kinematic works). RFFS (shipped, time-tested) flies with RAW
  `SetVelocity` in the vertical: its `SetVelocityAdjusted` (`RFFSHeli_Core.c:2481`, in the PBO — the
  japm-recovered source is truncated before it) only scales X/Z, the Y passes raw to `SetVelocity`.
  And RFFS has NO client-side pose smoothing — it syncs only instruments (`:189-208`), trusts the
  CarScript's NATIVE replication for the pose, and calls `dBodyActive(this, ActiveState.ACTIVE)` while
  flying (`EOnFrame:1005-1006`). So if a CarScript heli RUBBERBANDS when piloted, the culprit is almost
  always a CUSTOM client smoother (dead-reckoning + client-side `SetPosition`) fighting native
  replication — remove it and let native replication carry the pose, like RFFS. Do NOT pivot to
  force-based on a rubberband alone. GATE LESSON: an offline kinematic gate (a scripted-trajectory
  spike with SetPosition-airborne + SetVelocity) flies OFFLINE and can even show a microstutter that
  tempts you to ADD a client smoother — but real PILOTED flight (only testable once custom inputs work)
  behaves differently. Validate the flight mode in-game with real inputs before adding smoothing or
  sealing the mode.
- **Kinematic CarScript flight — the fixes that make it actually fly, verified IN-GAME piloted
  (added 2026-07-14, LFHeli)**:
  (1) **Double-gravity: the body applies gravity AFTER your `SetVelocity`.** If the solver already
  subtracts gravity (`accelY = lift - GRAVITY`), the dynamic body subtracts it AGAIN and the climb is
  cancelled — measured `realVy = tgtVy - g*dt` (a constant -0.21 m/s/tick). **`dBodyEnableGravity(false)`
  is a NO-OP on CarScript** (measured, did not change the term). Fix = counter-gravity like RFFS: add
  `GRAVITY * dt` back to the velocity Y each flight tick (`RFFSHeli_Core.c:1854`).
  (2) **Kill residual body spin after `SetOrientation`** with `dBodySetAngularVelocity(this, vector.Zero)`
  (`enphysics.c:165`) — else the body's own angular velocity fights your per-tick `SetOrientation` and
  the rotation (and the seat camera) judders. RFFS does this (`:1892`). NOTE: this smooths ROTATION only;
  jittery POSITION replication is a separate problem (native pose replication frequency / client
  interpolation).
  (3) **Car-wheel suspension re-anchors the vertical `SetVelocity` whenever wheels touch the ground** —
  a wheeled placeholder cannot lift off (`realVy` re-clamped to ~0 near AGL 0). Condition the test heli
  WITHOUT wheels (`OnDebugSpawn` minus the wheel `CreateInInventory`); the real model has skids.
  (4) **An idle CarScript body sleeps -> no `EOnSimulate` -> the state machine stalls** (collective does
  nothing until the pilot drives to wake it). `dBodyActive(ALWAYS_ACTIVE)` from EEInit helps but was NOT
  fully sufficient in one run (still needed drive-to-wake) — PENDING; confirm the body stays awake with a
  pilot seated + engine on, or wake in the get-in / engine-start hook.
  Tooling note: the MCP `vehicle_prepare_fixture` conditioning is hardcoded to one car (`MCPBridge.c:835`),
  so a custom test vehicle should self-condition via `EEInit -> CallLater(OnDebugSpawn)`.

- **CarScript-as-aviation runs under `NetworkMoveStrategy.PHYSICS` in 1.29 — client fluidity needs the
  full Pawn pipeline, NOT a mirror** (added 2026-07-14, LFHeli, verified in-game). A CarScript child in
  1.29 (`FEATURE_NETWORK_RECONCILIATION` on) reports `GetNetworkMoveStrategy()==PHYSICS` on the owner
  (probe measured `strat=2`) — the engine expects the OWNER to predict + reconcile. A client mirror
  (pump `EOnSimulate`+`EOnPostSimulate` off `EOnFrame`, RFFS-style) does NOT advance the pose:
  `super.EOnSimulate` is an empty stub (`enentity.c:201`) and pumping `EOnPostSimulate` runs CarScript
  engine/fluids logic on the owner (harmful, `m_Time` ~5x). Partial owner-prediction (run the solver
  gated `IsServerOrOwner` WITHOUT the Pawn hooks) still snaps on corrections and desyncs (hard TP on a
  CRASHED). Fix = full Pawn pipeline: `LFHeliMove`/`LFHeliOwnerState` (both call `super` + implement
  `EstimateMaximumSize`), `ObtainMove`/`ConsumeMove`/`ReplayMove` carrying RAW inputs (not the attenuated
  buffer or FSM-mutated state), `RewindState` (`super` first + ADDITIVE guard), solver ONCE in
  `EOnSimulate` gated `IsServerOrOwner`, tuning to the owner via a guaranteed RPC handshake (values +
  ACK + `ForceCorrection`). SIB/RFFS mirror and hookless owner-prediction are dead ends under PHYSICS.
  Probe `GetNetworkMoveStrategy()` client-side before choosing the network model. (LFHeli 2026-07-14;
  Codex research + R22, plan `2026-07-14-lfheli-physics-pawn-final.md`.)
## Helicopters

A **real rotary-wing flight model is documented from FOUR author/teams across five aircraft** (plus
LM_Planes fixed-wing), which confirms the pattern generalizes AND that monolithic (both kinematic and
force-based) and modular-aerofoil flight are all buildable (see `references/helicopters.md` for the full
pattern + `path:line` citations, the SIB-vs-RFFS-vs-MH6-vs-Expansion-vs-LM_Planes comparison, and the
monolithic-vs-modular architectural synthesis + decision framework):

1. **RFFS — RedFalcon Flight System** [VERIFIED-source, clean] — the **kinematic** reference. Non-obfuscated,
   de-rapified by Mikero, complete on disk. `RFFSHeli_S76 : RFFSHeli_base : CarScript`. Source in
   `<research-notes>\redfalcon-rffs-heli\`. Build from this for an arcade /
   minimal-code / predictable heli — clean, DRM-free, full integrator legible.
2. **MH6 — Llama** [RECOVERED, clean] — the **force-based** reference (same author as LM_Planes; particle
   paths `LM_LLAMA/LM_Vehicles/MH6/`). `class MH6 extends CarScript` with `MH6OwnerState`/`MH6Move` Pawn
   replication; a real PD flight controller applying `dBodyApplyForce`/`dBodyApplyTorque` every tick. Source
   in `<research-notes>\mh6-heli\`. Build from this for realism / momentum /
   autohover.
3. **SIB — lfbanov / sibnic** [RECOVERED, corroborating] — the recovered case with DRM. Workshop
   `3485438937`; JAPM-deobfuscated 2026-07-07 with `japm-pbo-recovery`. `HeliTest_SIB : Heli_sib_cript :
   CarScript`. Source in `<research-notes>\lfbanov-sibnic-heli\`. Its simple
   (kinematic) model is legible; its advanced **force-based** model is license-locked and its core
   integrator did not survive recovery.
4. **Expansion — DayZ Expansion Team** [VERIFIED-source, clean, open-source] — the **modular / framework**
   reference. A data-driven vehicle-physics framework, not a bespoke flight loop: the airframe is a bag of
   auto-configured modules (aerofoils + a rotor module) each adding force+torque at its own position to an
   `ExpansionPhysicsState` accumulator committed via `dBodyApplyForce`/`dBodyApplyTorque`. Entity
   `ExpansionHelicopterScript : CarScript`; rotor is a dedicated module `ExpansionVehicleHelicopter`
   (rotor-disc / blade-element model with autorotation, VRS, RBS, ETL, ground effect). One base flies the
   Gyrocopter/Merlin/MH-6/etc. Source in
   `<research-notes>\expansion-vehicles-heli\`. Build from this for a
   multi-aircraft framework with realistic, config-tunable physics.

All are the **same CarScript-as-aviation hack** used for planes, but as a heli: a full ground
`SimulationModule` as a taxi fallback, and the flight loop entirely in script overriding it. **Both
integration styles are buildable**: kinematic (`SetVelocity`/`SetOrientation` — RFFS, SIB-simple) OR
force-based (`dBodyApplyForce`/`dBodyApplyTorque` — MH6). The earlier "buildable = kinematic only"
impression came solely from SIB's DRM-locked advanced variant; MH6 disproves it with a clean, complete
force-based integrator on disk.

- [VERIFIED-RFFS] **RFFS flight model** (`RFFSHeli_Core.c:1767` `FlightSimulation()`, server-side under
  `EOnSimulate`): far more physically grounded than SIB while still kinematic — collective is a
  **discrete 0-20 detent** (`m_collective_level` × `c_thrust_rate`) rotated into a world lift vector by
  the heli's own pitch/roll/yaw, plus ground effect, effective translational lift, speed + climb
  governors, aerodynamic drag, and weathervaning. Cyclic/pedals feed a carried-forward
  `m_angular_moment`; a `UARFFSRecover` mode auto-levels. **This is the recommended buildable pattern.**
- [RECOVERED-SIB] **SIB simple flight model** (`unknown_16894.c`, corroborating): `KeyboardPilot +
  Simulate`, also `SetVelocity`/`SetOrientation`. Simpler — pitch attitude → scalar forward speed;
  bank → yaw; passive `+0.25` m/s hover baseline; attitude auto-recenter as the only stabilization.
- [RECOVERED-MH6] **MH6 force-based flight model** (`MH6_flightmodel.c`, Llama): a real PD flight
  controller in `ApplyHelicopterPhysics(dt)` — rotor-RPM authority gates (`cyclicAuth =
  Ramp01(m_RotorSpeed,0.18,0.50)`, `:990`), collective→lift force along body-up (`mass·g·1.65 ·
  collective · rotorSpeed² · densityRatio · transLift · groundEffect`, `:1004-1011`), cyclic/tail torques,
  proportional attitude stability + derivative angular-rate damping (`PITCH_STABILITY`/`PITCH_DAMPING`,
  `:1092`/`:1112`), per-axis quadratic drag with ISA `densityRatio`, overspeed + climb limiters, all
  committed via `dBodyApplyForce`+`dBodyApplyTorque` (`:1165-1166`). Uses **custom Pawn replication**
  (`MH6OwnerState`/`MH6Move`, prediction+rewind — like LM_Planes) and hybrid kinematic `SetVelocity`
  autohover/autoland state machines on top. Constants are hard-coded literals (`:141-176`); config.bin
  [UNVERIFIED] (not recovered).
- **Inputs** are custom UA actions read via `GetInputInterface().SyncedValue(...)` / `GetUApi()` in all:
  RFFS `UARFFSCyclic*/Pedal*/Collective*` (`RFFSHeli_Core.c:549-583`), SIB `UASIBHeli*`, MH6 `UAKTHeli*`
  (`MH6_flightmodel.c:1434-1450`). Engine start/stop is action-driven — RFFS/SIB add custom start actions;
  MH6 reuses the vanilla `ActionStartEngine`/`ActionStopEngine` (only relabeled) and gates on `EngineIsOn()`.
- **Config framework**: RFFS uses a **typed named JSON** framework (server-wide `MasterConfig` + per-heli
  `HeliConfig`, `get*` accessors, `JsonFileLoader<T>` with auto-create + version-migrate) — the safest
  reusable pattern. SIB uses a **positional** `map<string,float>` from `$profile` JSON read back
  index-by-index. MH6 uses **hard-coded const literals** in the class (`:141-176`) — no external config on
  disk (its config.bin, which might override, was not recovered).
- **Rotors** are baked geometry with a static/blur mesh cross-faded by health/RPM-gated `SetAnimationPhase`
  in all three (RFFS `rotorN_speed`/`rotorN_blur_hide`; SIB `rot_h_start`/`rot_h_blur_end`; MH6 `rotor_1_1`
  spun by phase-accumulation + `rotor_1_1_hide`/`rotor_1_1_rotate_hide` swap at 70% RPM,
  `MH6_flightmodel.c:1169-1200`) — not attachable items (contrast the other community heli below).
- **Per-component DamageZones**: RFFS `Chassis/Avionics/Engine/Hydraulics/FuelTank/MainRotor/TailRotor`
  with cross-transfer coefs + a `modded IngameHud` flight HUD (`headsUpDisplay.c`); SIB
  `Body/Chassis/Engine/Fuel/Rotor1/Rotor2/Proj` (config dials, no widget HUD). MH6's DamageZones live in
  the unrecovered config.bin ([UNVERIFIED]).
- [UNVERIFIED] **NOT on disk — do not fabricate**: for all three, the `.p3d` models + `model.cfg` skeleton/
  bone graph and the exact `.p3d` memory-point set; the `modded_Inputs.xml` bindings (input *names* are
  confirmed from script). For SIB additionally the advanced force-based integrator `hkdxkhzidmpsib`
  (license-locked, missing) and `config.bin`. For MH6 the entire `CfgVehicles`/`config.bin`
  (AnimationSources/DamageZones/Crew/memory points). See `references/helicopters.md` §7-8 (SIB), RFFS §7,
  MH6 §7. For Expansion the full rotor module (3234 lines — core read, remainder [UNVERIFIED]),
  `Expansion_GetDensity`, the `SimulationModule` config, and concrete Merlin/MH-6 classes.
- **Expansion — modular aerofoil framework** [VERIFIED-source]: the aerofoil (`ExpansionVehicleAerofoil.c`)
  auto-configures from `CfgVehicles <veh> SimulationModule Aerofoils <name>` (area from memory points,
  `type`=Wing/Rudder/Elevator by config), computes AoA/stall/drag in `PreSimulate` (`:152-203`), and adds
  `force = up·q·Cl + airflowNormal·q·Cd` plus **torque `= position × force`** to the accumulator
  (`:229-230`) — so control moments **emerge from the surface's geometry**, no hand-tuned lever arms. The
  heli's rotor is a separate module (§3 of the ref); one core serves car/boat/plane/heli.
- **Decision framework** (which to build from): **one heli, ship now, arcade + code you can read end-to-end
  → monolithic** — kinematic **RFFS** (predictable `SetVelocity`) or force **MH6** (`dBodyApplyForce` with
  momentum + PD stability). **A multi-aircraft framework with realistic, config-tunable physics →
  Expansion** (modular aerofoil + rotor-disc, at the cost of its scaffolding + tuning curve). **Fixed-wing
  with real aero → LM_Planes (monolithic) or Expansion (modular).** Do **not** build from SIB (minimal
  kinematic hack + DRM-locked advanced). Full trade-off analysis in `references/helicopters.md`
  §"Monolithic flight loop vs modular aerofoil system".

> Earlier community-surface note (kept, different mod): `HelicopterSIB_Hommade_LF` (a reskin of
> `HelicopterModhommade`) confirmed a [INFERRED] CarScript-derived base with **attachable** rotor
> blades (`hommade_blade1/2`, tail `hommade_bladem1/2`) and a `c_rotorSound/c_engineSound/
> c_warningSound/c_crashSound` hook contract — but its flight model lived in the (absent) base addon.
> The SIB mod above supersedes it as the documented flight pattern.

## PREFLIGHT

Gate real build work on `/dayz-preflight` (P:\ mounted, AddonBuilder present, P:\Mods junction), per
`<skills>\_shared\dayz-conventions.md`. Authoring config / model.cfg / flight-model
scripts offline does not need it; packing does.

## Architecture: CarScript-as-Aviation

### The fundamental hack

Aviation inherits from `CarScript` (the ground vehicle base). DayZ has no flight class, so:

```cpp
// config.cpp per-aircraft
class LM_Tigermoth: CarScript
{
    scope = 2;
    model = "LM_Planes\LM_Tigermoth\LM_Tigermoth.p3d";
    weight = 1000000;             // Very high for plane stability
    fuelCapacity = 60;
    fuelConsumption = 15;
    animPhysDetachSpeed = 250;
    attachments[] = {"CarBattery","Reflector_1_1","Reflector_2_1","CarRadiator","SparkPlug",...wheels...};
    class SimulationModule: SimulationModule { /* full ground vehicle physics — overridden by scripts */ };
    // ... AnimationSources, DamageSystem, GUIInventoryAttachmentsProps, Sounds
};
```

The plane has 4 wheels (front/back left/right) for ground taxiing AND a `SimulationModule` with full ground-vehicle physics — but actual flight physics is applied in scripts on top of the engine, not via config. See `ApplyFlightPhysics(dt)` in the script section.

### Vestigial config values

When reusing `CarScript`, `Engine` block values that don't affect flight (because scripts take over) can be left as stubs:
- `rpmRedline = 80000` (real engines: 6000-8000) — irrelevant for flight, kept to satisfy config validator
- `torqueCurve[] = {600,0,990,65,...}` — only matters for ground mode

This is acceptable: a script-driven plane doesn't read these at runtime. Don't waste time tuning them.

### requiredAddons combo

```cpp
class CfgPatches {
    class LM_Tigermoth {
        requiredAddons[] = {"DZ_Vehicles_Parts","DZ_Data","DZ_Vehicles_Wheeled","DZ_Vehicles_Water","LM_Planes"};
    };
};
```

Critical: **both `DZ_Vehicles_Wheeled` AND `DZ_Vehicles_Water`** are required. Wheeled gives landing gear behavior; Water gives flying-boat/seaplane buoyancy behavior. Sub-aircraft mods also require their parent (`LM_Planes`).

### `class defs` wrapper for sub-mods

Root mod loads `gameScriptModule`/`worldScriptModule` directly under `CfgMods.<Mod>`:

```cpp
class CfgMods {
    class LM_Planes {
        ...
        class gameScriptModule { files[] = {"LM_Planes/scripts/3_Game"}; };
        class worldScriptModule { files[] = {"LM_Planes/scripts/4_World"}; };
    };
};
```

Per-aircraft sub-mods wrap them under `class defs`:

```cpp
class CfgMods {
    class LM_Tigermoth {
        ...
        class defs {
            class gameScriptModule { ...; files[] = {"LM_Planes/scripts/3_Game"}; };
            class worldScriptModule { ...; files[] = {"LM_Planes/scripts/4_World"}; };
        };
    };
};
```

Some sub-mods only load `worldScriptModule` (Cessna180, Spitfire). The wrapper is required when the mod is a child of another mod's namespace.

### Base script class (data-driven config-in-script)

```cpp
class LlamaPlaneScript extends CarScript
{
    // ~60 protected Get* methods for ALL tunable parameters
    protected float GetWingArea()              { return 22.0; }
    protected float GetWingSpan()              { return 8.9; }
    protected float GetWingAR()                { return 5.2; }
    protected float GetEngineMaxPower()        { return 3000.0; }
    protected float GetClCoef3()               { return -0.00038; }
    // ... etc, 60+ methods covering aerodynamics, control, stall, dampening, sound, lights
};

class LM_Tigermoth extends LlamaPlaneScript
{
    // ONLY override Get* methods — zero new logic per aircraft
    override protected float GetWingArea()     { return 22.0; }
    override protected float GetEngineMaxPower() { return 3100.0; }
    override protected float GetStallBaseSpeedKmph() { return 62.0; }
    // ... 50+ overrides
}
```

Per-aircraft files are essentially configs-as-code: parameter sets, not new logic. This makes adding aircraft trivial: copy the override block, tune values.

### Custom Pawn replication

DayZ networking for player-controlled entities uses Pawn classes. Aviation needs custom state:

```cpp
class PlaneOwnerState extends CarScriptOwnerState
{
    int m_iFlightMode;             // 0=ground, 1=air
    float m_fThrottleSmooth;
    float m_fPitchSmooth;
    float m_fRollSmooth;
    float m_fRudderSmooth;
    float m_fStallFactor;
    
    protected override event void Write(PawnStateWriter ctx) { /* serialize */ }
    protected override event void Read(PawnStateReader ctx) { /* deserialize */ }
};

class PlaneMove extends CarScriptMove
{
    float m_fPitch;
    float m_fRoll;
    float m_fRudder;
    float m_fThrottle;
    int m_iToggleFlightMode;
    
    protected override event void Write(PawnMoveWriter ctx, PawnMove prev) {}
    protected override event void Read(PawnMoveReader ctx, PawnMove prev) {}
};

// In LlamaPlaneScript:
protected override event typename GetOwnerStateType() { return PlaneOwnerState; }
protected override event typename GetMoveType()       { return PlaneMove; }
protected override event void ObtainMove(PawnMove pMove)  { /* client captures inputs */ }
protected override event void ConsumeMove(PawnMove pMove) { /* server applies inputs */ }
protected override event bool ReplayMove(PawnMove pMove)  { /* client-side prediction replay */ }
protected override event void SimulateMove(PawnMove pMove) { /* apply forces */ }
protected override event void ObtainState(PawnOwnerState pState)    { /* snapshot */ }
protected override event void RewindState(PawnOwnerState pState, PawnMove pMove, inout NetworkRewindType pRewindType) { /* rollback */ }
```

This gives you client-side prediction with server reconciliation — essential for fly-able aviation that doesn't feel laggy.

### Two flight modes

```cpp
protected int m_PlaneMode = 0;  // 0=GROUND, 1=AIR
protected float m_PlaneModeSwapCooldown;

protected void Server_ToggleMode()
{
    // Cooldown prevents spam
    if (m_PlaneModeSwapCooldown > 0) return;
    m_PlaneMode = 1 - m_PlaneMode;
    m_PlaneModeSwapCooldown = 1.0;
}
```

`PLANE_MODE_AIR` enables `ApplyFlightPhysics()`. `PLANE_MODE_GROUND` lets `CarScript` handle taxiing normally. Pilot toggles with a bound action (default G). Critical for proper landing/takeoff transitions.

### `driverless` design pattern

```cpp
class SimulationModule {
    class Brake {
        driverless = 0.1;  // Sport aircraft: rolls when pilot exits
        // OR
        driverless = 1.0;  // Heavy aircraft: locks fully (no rolling)
    };
};
```

Llama splits: `0.1` for Cessna180, Spitfire, StuntPlane (sport feel). `1.0` for Catalina, DC-3, Patty_Wagon, Tigermoth, Z37_Bumblebee (utility/heavy feel). Pick based on aircraft character.

## Aerodynamics, Physics, Buoyancy & Aircraft Presets

> Moved to `references/aerodynamics-and-flight-physics.md` — lift/drag/stall, ISA atmosphere,
> PID auto-stab, NaN-safe forces, seaplane Buoyancy + active water physics, runtime optimization,
> and the concrete Cessna/Spitfire/Catalina/Tigermoth parameter presets.

## Memory Points (for the model artist)

Aircraft p3d must contain these memory points; scripts will read them via `GetMemoryPointSafe(name, fallback)`:

| Memory point | Purpose |
|---|---|
| `axis_back`, `axis_front`, `axis_left`, `axis_right`, `axis_floor`, `axis_roof` | Aircraft orientation reference vectors |
| `axis_elevator_left`, `axis_elevator_right` | Elevator hinge axes for moment-arm calc |
| `axis_flap_left`, `axis_flap_right` | Aileron hinge axes |
| `axis_rudder` | Rudder hinge axis |
| `axis_thruster` | **THRUST APPLICATION POINT** — engine force is applied here |
| `wing_left`, `wing_right` | Wing tip positions (for wing span calc + nav lights fallback) |
| `light_wing_left`, `light_wing_right`, `light_wing_tail` | Navigation light spawn positions (red/green/white) |
| `pos_driver`, `pos_codriver`, `pos_cargo1-3` + `_dir` variants | Crew entry positions + facing direction |
| `dmgZone_*` | Damage zone hit centers (matches DamageSystem in config) |

Catalina expands with `light_left`, `light_right`, `light_1_1`, `light_2_1`, `light_dashboard`, `light_reverse` for flying-boat exterior lights.

`GetMemoryPointSafe(name, fallbackVec)` returns the position or `fallbackVec` if not found — keeps script robust against missing memory points.

## Selection Names (skeleton bones in model.cfg)

Top-level bones registered in `CfgSkeletons.<Aircraft>_skeleton.SkeletonBones[]` (no parent unless wheel chain):

**Flight controls** (script-driven via `SetAnimationPhase`):
- `elevator_1_1`, `elevator_2_1` (paired elevators)
- `aileron_1_1`, `aileron_2_1`
- `rudder_1_1`
- `gear_1_1` (landing gear retract)

**Rotors** (propeller animation):
- `rotor_1_1`, `rotor_center` (main prop)
- `rotor_1_1_blur` (visual blur when spinning)
- `rotor_1_2`, `rotor_center2` (DC-3 second engine) OR `rotor_2_1`, `rotor_center_2` (Catalina) — naming inconsistent
- Single-engine planes: only `rotor_1_1` + `rotor_center`

**Instruments**:
- `dial_compass`, `dial_horizon_bank`, `dial_horizon_pitch`
- `dial_altitude`, `dial_volt`
- `dial_rpm`, `dial_fuel`, `dial_temp`, `dial_speed` (vanilla-driven)

**Other**:
- `engine`, `radiator`, `refill`
- `drivewheel`, `drivewheel_1`, `drivewheel_2` (cockpit yokes)
- `crewdriver`, `crewcodriver`, `seat_driver`, `seat_codriver`, `seat_cargo1-3`
- `propeller` (selection, not the rotor bone)

**Wheel chain** (parented):
- `damper_susp_X_Y` (top, no parent) → `damper_X_Y` (parent: damper_susp) → `wheel_X_Y` (parent: damper) → `wheel_X_Y_steering` (parent: wheel)
- Rear/tail wheel: `damper_2_2` has no `damper_susp` parent (simpler chain)

## Control-Surface AnimationSources, model.cfg & Damage Zones

> Moved to `references/animation-and-modelcfg.md` — AnimationSources (surfaces/dials/dampers),
> model.cfg Animation classes, propeller-spin hack, damage zones, VehicleAnimInstances catalog.

## Input Bindings

> Moved to `references/inputs-and-bindings.md` — Inputs.xml registration, keyboard/Xbox scheme,
> stringtable tie-in, multi-aircraft config variants.

## Sounds

> Moved to `references/sounds.md` — CfgSoundShaders/CfgSoundSets two-tier, RPM-band crossfade,
> volume modulation, offload variants, per-aircraft sound ownership.

## Visuals & Materials

### Toggle rvmat pattern (dashboard on/off)

```
Controls.rvmat (lights off)        Controls_on.rvmat (lights on)
forcedDiffuse = {0,0,0,1}     →   forcedDiffuse = {0.1,0.1,0.1,1}
Stage5 SMDI = controls_SMDI       Stage5 SMDI = controls_on_SMDI
Everything else identical.
```

Only 2 things differ between off/on. Cross-aircraft material sharing (Catalina referencing `LM_Tigermoth/data/Controls.rvmat`) — DRY across aircraft (verified in p3d binary string references).

## Effects & Lights

> Moved to `references/effects-and-lights.md` — seaplane water spray effects, custom nav lights,
> per-aircraft headlights.

## Combat Aviation (optional)

> Moved to `references/combat.md` — zero-physics tracer, hitscan + tracer, full Spitfire fire
> pipeline (RPC/ammo/damage-zone), camera shake.

## Reference loading guide

Load a topic reference on-demand when the task touches it (all under `references/`):

| Reference | Load when working on |
|---|---|
| `helicopters.md` | Any rotary-wing (helicopter) work — THREE documented heli flight models + a 4-way cross-author comparison (kinematic vs force-based axis). **RFFS (RedFalcon), clean kinematic reference**: `RFFSHeli_S76 : RFFSHeli_base : CarScript`, `FlightSimulation()` (discrete 0-20 collective → attitude-rotated lift vector, ground effect/ETL/speed+climb governors/drag/weathervaning, kinematic via `SetVelocity`), typed `MasterConfig`+`HeliConfig` JSON, `modded IngameHud` HUD, per-component DamageZones. **MH6 (Llama), clean FORCE-BASED reference**: `MH6 : CarScript` + `MH6OwnerState`/`MH6Move` Pawn replication, PD flight controller (`ApplyHelicopterPhysics` — RPM-authority gates, ISA-density lift force, cyclic/tail torques, P+D attitude control, quadratic drag, `dBodyApplyForce`+`dBodyApplyTorque`), hybrid kinematic autohover/autoland FSMs, `StandardAtmosphere` helper. **SIB (recovered, corroborating)**: `HeliTest_SIB : Heli_sib_cript : CarScript`, simpler kinematic loop, positional JSON coeff store; advanced force-based model license-locked + missing. All use baked-blur rotor `SetAnimationPhase` and server-authoritative sync |
| `aerodynamics-and-flight-physics.md` | Lift/drag/stall, ISA atmosphere, PID auto-stab, NaN-safe forces, seaplane Buoyancy + active water physics, runtime optimization, per-aircraft (Cessna/Spitfire/Catalina/Tigermoth) presets |
| `sounds.md` | Engine sound: CfgSoundShaders/CfgSoundSets, RPM-band crossfade, volume modulation, per-aircraft sound ownership |
| `combat.md` | Weaponizing an aircraft: tracer projectile, hitscan, the full Spitfire fire pipeline (RPC/ammo/damage-zone), camera shake |
| `inputs-and-bindings.md` | Flight-control input bindings: Inputs.xml, keyboard/Xbox scheme, stringtable tie-in |
| `animation-and-modelcfg.md` | Control-surface AnimationSources, model.cfg Animation classes, propeller-spin hack, damage zones, VehicleAnimInstances |
| `effects-and-lights.md` | Seaplane water spray effects, custom navigation lights, per-aircraft headlights |

## Cross-references

- [[dayz-vehicles]] — CarScript packaging/deploy failures that pass filepatching but break on dedicated (binarize dropping config-only textures, ODOL-vs-MLOD model.cfg semantics) live in `dayz-vehicles/references/build-packaging-and-debug.md` and apply to CarScript aircraft too. Amphibians boundary: hull/car base in `dayz-vehicles`; Buoyancy/flight layer here.
- [[enforce-script-reference]] — general Enforce Script patterns (config.cpp, CfgMods, modded class, RPC, persistence)
- [[dayz-model-pipeline]] — rvmat patterns, .p3d Object Builder workflow, materials
- [[dayz-mod-workflow]] — workflow protocol (use ALONGSIDE this skill)
- [[dayz-particles]] — Enfusion .ptc format (used for crash/impact effects)

## Anti-patterns observed

1. **Inventory slot case inconsistency** (`LM_Tigermoth_Wheel_1_1` capital W defined, but referenced as `LM_Tigermoth_wheel_1_1` lowercase w in `class Wheels`). Engine resolves it but bug-magnet. Be consistent.
2. **Rotor source = wheelfrontright** — visual prop tied to wheel, not engine RPM. Works as a hack but doesn't reflect actual engine behavior. Script-overriding it is the proper fix.
3. **rpmRedline=80000** in Engine — vestigial CarScript values left because they don't matter when scripts control physics. Don't bother tuning these for aviation.
4. **i18n placeholders** — Stringtable.csv with 13 locales all identical English. Pragmatic shortcut, not bad practice per se, but worth knowing if you fork the mod.

<!-- llama-mod-extraction: findings f_001, f_003, f_008-f_013, f_016, f_017, f_019, f_023-f_029, f_031-f_036, f_037-f_043, f_048, f_049, f_052, f_053, f_066-f_070, f_073-f_075, f_078, f_085 | pbo: LM_Planes | pass: 1 | date: 2026-05-23 | author: Llama+Itspete-Here | source: workshop 3730564764 | count: 45 -->

## Pass 2: Per-Aircraft Deep Dive Patterns

Patterns extracted from per-aircraft `.c` scripts after full pass-2 coverage of all 8 aircraft + Patty_Wagon. Adds combat aviation, water physics templates, anim instance catalog, and ammo handling.

## Pass 2 patterns (distributed)

> The per-aircraft deep-dive patterns (Pass 2) were distributed into the topic references:
> seaplane water physics + presets + composition override -> `aerodynamics-and-flight-physics.md`;
> the full Spitfire combat pipeline + ResolveDamageZone + camera shake -> `combat.md`;
> VehicleAnimInstances catalog -> `animation-and-modelcfg.md`;
> sound ownership -> `sounds.md`. Sub-mod architecture, cosmetic proxies and family wheel
> sharing (config-level) remain below.

### Sub-mod parent/child architecture

Root mod (`LM_Planes`) has `CfgPatches.units[] = {}` (EMPTY — no entities directly). Only registers `Inputs.xml` + script modules. Per-aircraft sub-mods (`LM_Tigermoth`, `LM_Catalina`, etc.) declare their own `units[]` and require `LM_Planes` parent.

**One-way dependency**: child requires parent, parent doesn't require children. Lets you enable/disable per-aircraft sub-mods independently without breaking root. Critical pattern for large modular mods.

### Cosmetic-only proxies (no script logic needed)

DC-3 has `proxy/LM_DC_3_Rear_seats.p3d` (165 KB) — purely decorative cockpit seats visible in proxy LOD. NO memory points `pos_cargo*`, NO selections `seat_cargo*`. `CfgVehicles.LM_DC_3.class Crew` declares only Driver + CoDriver (no cargo).

Z37_Bumblebee has `proxy/LM_Z37_Bumblebee_door_1_1.p3d` + `door_2_1.p3d` — handled by **vanilla DayZ door attachment system** (CarDoor base + attachments[] in config + class DamageZones.Doors). No script logic for doors. Engine handles visibility on attach/detach.

**Pattern**: use vanilla DayZ systems when possible. Don't write scripts for doors/seats if config + proxies suffice.

### Family wheel sharing (variant reuse)

Tigermoth family (`LM_Tigermoth` + `LM_Tigermoth_MK2` + `LM_Tigermoth_MK3`) all use the SAME wheel inventory class:

```cpp
// LM_Tigermoth_MK2.c OnDebugSpawn:
GetInventory().CreateInInventory("LM_Tigermoth_wheel_front");  // NOT MK2_wheel_*
GetInventory().CreateInInventory("LM_Tigermoth_wheel_back");
```

Only the variant aircraft body changes; wheels are shared. Reduces config + asset duplication. Pattern for vehicle families.


<!-- llama-mod-extraction: findings f_087-f_091, f_096, f_097, f_101, f_103, f_105-f_107, f_110-f_116, f_120, f_123-f_125 | pbo: LM_Planes | pass: 2 | date: 2026-05-23 | source: workshop 3730564764 per-aircraft .c files | count: 23 -->

## Reglas promovidas del corpus de lecciones (added 2026-07-27)

Promovidas desde `AI/20_Knowledge/lessons-learned.md` para que lleguen por trigger en vez
de depender de que alguien recuerde buscarlas. Cada regla cita su `LL-NNN` de origen;
la entrada completa (síntoma, origen, evidencia) vive allí. No quites la cita: el índice
`lessons-index.md` detecta la promoción buscando esa referencia dentro de las skills.

- **LL-194** — Enumera cada campo leído por solver/FSM durante replay y clasifícalo como restaurado, recomputado tras handshake o inicializado incondicionalmente. Nunca inicialices K-values o tablas derivadas solo dentro de `IsServer`.
- **LL-195** — No uses un handshake one-shot si depende de crew/possession/spawn aún asíncronos. Reintenta desde el cliente hasta ACK o empuja desde el servidor cuando el estado esté listo; compara identidades por ID estable, no por instancia.
- **LL-201** — Diagnostica reconciliación con series alineadas: dientes de sierra indican correcciones seguidas de re-divergencia; crecimiento monótono o plateau sin resets indica que el transform no se corrige. Busca el evento que dispara la convergencia antes de retocar el solver.

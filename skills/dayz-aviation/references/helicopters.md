# Helicopters — recovered flight-model pattern (SIB heli mod)

**Load when:** authoring or debugging a rotary-wing (helicopter) DayZ entity — collective/cyclic/
anti-torque, rotor animation, engine start/stop, altitude ceiling, heli damage zones.

## Provenance

[RECOVERED] from the **lfbanov / sibnic SIB helicopter mod** (Workshop **3485438937**, "La Frontera"
/ Fortune Mods; author `SIBNIC`, internal `ver=8.041`). Two PBOs
(`HelicopterMod_lfbanov_SERVER_v8.041.pbo` + `HelicopterSIB_Scripts_lfbanov.pbo`) were JAPM-obfuscated
and recovered on 2026-07-07 with `japm-pbo-recovery`. Source copies live in
`<research-notes>\lfbanov-sibnic-heli\recovered\{SERVER,CLIENT}\` — see
`..\INDEX.md` for the full file→class map. Citations below are `path:line` into those recovered
copies.

**Unlike LM_Planes, this is a REAL rotary-wing flight model on disk, not a community guess.** But note
the caveats in the last section — the *advanced* variant's core integrator did not survive recovery,
and the whole thing is a homegrown kinematic hack, not a physically-modeled rotor.

---

## 1. Architecture — `HeliTest_SIB : Heli_sib_cript : CarScript`

[RECOVERED] Same CarScript-as-aviation hack this skill documents for planes, but three layers deep
(`CLIENT\unknown_15761.c`):

| Layer | Adds | Cite |
|---|---|---|
| `CarScript` (vanilla) | wheels, seats, fuel, damage, sound | — |
| `Heli_sib_cript : CarScript` | full `SimulationModule` (Axles/Wheels — 4 wheels for a ground-taxi fallback), `Crew{Driver,CoDriver}`, car-style `AnimationSources` (`DoorsDriver`, `HideDestroyed_*`, `AnimHitWheel_*`), electrical/fuel stubs (`fuelCapacity=50`, `electricConsumptionIgnition=3001`) | `:117-287` |
| `HeliTest_SIB : Heli_sib_cript` | rotor + flight `AnimationSources` (`hide_rotor`, `hide_start`, `rot_h_start/blur_end`, `rot2_h_*`, `toplivo`, dial detectors), `Crew` expands to Driver+CoDriver+Cargo1+Cargo2, heli `DamageZones` (Body/Chassis/Engine/Fuel/Rotor1/Rotor2/Proj), `Cargo`, `ObstacleGenerator` | `:288-710` |

**Key point:** the flight model is entirely in **script overriding a ground vehicle** — the config
still declares wheels, axles, steering, gearbox (`drive="DRIVE_AWD"`, `class Engine{torqueMax=114;…}`,
`:315-420`). Those are the CarScript ground fallback; the heli overrides `EOnSimulate` and drives
itself with `SetVelocity` / `SetOrientation` (simple model) or `dBodyApplyForce/Torque` (advanced).

Size variants are pure `Cargo`-size subclasses of `HeliTest_SIB`:
`HeliSIB_big/middle/little/minimal/none` (`:711-755`).

---

## 2. Flight model — the two variants

The mod ships **two flight models under the same class name**. Document both; **build from the
simple one** (the advanced one is license-gated and its core did not survive recovery).

### 2a. SIMPLE model — kinematic, `SetVelocity`-based [RECOVERED, fully legible]

File `SERVER\unknown_16894.c` (client copy `CLIENT\unknown_16894.c` is identical through the class
body). Not license-gated. This is the teachable pattern.

**Coefficients** (defaults in the class body; overwritten at runtime from JSON via `go_conf()`):

| Field | Default | Role | Cite |
|---|---|---|---|
| `c_startDurationInv` | `0.05` | engine spin-up inverse duration | `:26` |
| `c_liftForceCoef` | `3.0` | lift/collective strength | `:27` |
| `c_altNoForce` | `500.0` | altitude (m) at which lift → 0 (hard ceiling) | `:28` |
| `c_altFullForce` | `450.0` | altitude (m) below which lift is full | `:29` |
| `c_cyclicAsideForceCoef` | `1.3` | sideways (roll→translate) strength | `:30` |
| `c_cyclicForwardForceCoef` | `1.0` | forward (pitch→translate) strength | `:31` |
| `c_bodyFrictionCoef` | `0.3` | body friction | `:32` |
| `c_heliMass` | `1500.81` | mass | `:33` |

> Note: in the *simple* model these `c_cyclic*` / `c_altFullForce` / `c_bodyFrictionCoef` /
> `c_heliMass` fields are **loaded but the simple `Simulate()` does not actually read most of them**
> — the simple integrator is hand-tuned with literals (see below). They are the config *contract*
> the advanced model consumes. [INFERRED] from reading `Simulate()`.

**Control loop** — `EOnSimulate` (server only) reads two animation phases as the state gate, then
runs input + integration (`:425-452`):

```c
// EOnSimulate: gate on engine (hide_start) AND rotor (hide_rotor) both == 1.0
anim_rotor  = GetAnimationPhase("hide_rotor");
anim_engine = GetAnimationPhase("hide_start");
KeyboardPilot(dt, anim_engine, anim_rotor);   // read inputs -> m_RollKey/m_PitchKey/m_Yaw/m_rotorTurn
Simulate(dt, anim_engine, anim_rotor);         // integrate
```

[RECOVERED] **Inputs** (`KeyboardPilot`, `:124-201`) read via
`playerObj.GetInputInterface().SyncedValue("UASIBHeli<X>")`, each a boolean `>=0.5`:

| Input | Effect on state | Meaning |
|---|---|---|
| `UASIBHeliCyclicRight` / `…Left` | `m_RollKey ∓ 0.6` | roll (cyclic aside) |
| `UASIBHeliBack` / `…Forward` | `m_PitchKey ∓ 0.6` | pitch (cyclic fore/aft) |
| `UASIBHeliLeft` / `…Right` | `m_Yaw ± 0.6` | yaw (anti-torque / pedals) |
| `UASIBHeliUp` / `…Down` | `m_rotorTurn = ±2.8` | collective (climb/descend) |

[RECOVERED] **Integration** (`Simulate`, `:298-391`):

1. **Ground/ceiling probe**: `m_height = Distance(GetPosition, SurfaceY-projected pos)` (`:300-303`).
   Above `1500` m it force-hides rotor/engine (kill switch, `:319`). At `5..6` m it zeroes angular
   velocity (`dBodySetAngularVelocity(this,"0 0 0")`, landing settle, `:326-329`).
2. **Death**: if `GetHealth("","") <= 0` → hide rotor/engine, `m_isDead=true`, `SetSynchDirty()`,
   error-anim the rotors (`:306-315`).
3. **Attitude → forward speed** (`HeliPitch`, `:204-221`): reads `GetOrientation()[1]` (pitch);
   nose-down (`< -5`) accelerates `m_heliSpeed` (cap `60`), nose-up (`> 5`) decelerates (floor `-10`).
   **Forward motion is a side effect of pitch attitude, not a direct thrust vector.**
4. **Bank → yaw** (`HeliRoll`, `:224-258`): reads `GetOrientation()[2]` (roll); banking turns the heli
   (`m_Yaw`), harder bank (>59°) triggers an auto-descend (`m_rotorTurn=-3.0`). Applies the yaw to
   orientation directly with `SetOrientation`.
5. **Auto-leveling** (`AutoAlignment`, `:262-292`): if the pilot isn't actively rolling/pitching
   (`m_RollKey==0`/`m_PitchKey==0`), nudge attitude back toward level (±0.1 per tick past a ±3° dead
   zone). **This is the mod's "auto-stabilization" — a simple attitude-recenter, not a PID.**
6. **Apply attitude**: rotate `GetOrientation()` by `Math.RAD2DEG * m_{Roll,Pitch,Yaw}Key * dt`, then
   `SetOrientation` (`:349-353`).
7. **Apply velocity** (`:360-387`): build a world velocity vector —
   - Forward: `sin/cos(heading) * m_heliSpeed` into X/Z (`:365-371`).
   - Vertical: `m_rotorTurn` (collective) into Y; **with no collective input a constant
     `+0.25` m/s up is applied** (`:384`) — this is the passive hover-lift term, the closest thing to
     "lift(collective)" in the simple model.
   - `SetVelocity(this, m_Velocity)` (`:387`). **Velocity is set, not force-applied** → arcade feel,
     no momentum/inertia carryover between ticks.

[INFERRED] **There is no true collective→lift force curve in the simple model.** "Lift" = a fixed
`+0.25` m/s baseline plus `m_rotorTurn` (±2.8) when climbing/descending. The `c_altNoForce=500` /
`c_altFullForce=450` ceiling coefficients are declared but **the height clamp is a hard literal
`1500` in `Simulate`**, not those coefficients — so in the simple model the documented altitude
ceiling is effectively unused. [UNVERIFIED] whether the advanced model wires the 450/500 band.

### 2b. ADVANCED model — force/torque, autopilot, license-gated [RECOVERED but incomplete]

Files `SERVER\unknown_16458.c` / `CLIENT\unknown_18705.c` + `SERVER\unknown_10783.c`. Every method is
identifier-mangled and every entry point is guarded by `license_active_helisib` (a runtime license
check that GETs `sibnic.info/sib/mod13.php`, `SERVER\unknown_10783.c:319-395`).

What is recoverable:

- **Force-based physics**: the only recovered `dBodyApplyForce` / `dBodyApplyTorque` calls are in the
  helper `qmdkldkpqpmlsib(...)` (`SERVER\unknown_10783.c:454-455`): it computes a target-velocity
  delta × `dBodyGetMass(...)` and applies it as a body force, plus a torque term — i.e. proper rigid-
  body forcing, unlike the simple model's `SetVelocity`. It uses model-space transforms
  (`Transform_SIB`, `unknown_18705.c:4-28` matrix helpers) to convert local up/forward into world.
- **Autopilot state machine**: enum `AutopilotState_SIB { Far, Brake, Near, Align, Reached }` +
  `StopMode_SIB { SMNone, SMLand, SMGetIn, SMGetOut }` (`CLIENT\unknown_18705.c:33-51`) with
  `m_state`/`m_stopMode` fields and a large `get_botmap_*`/`set_botmap_*` accessor surface
  (`:232-270`). This is a genuine autohover/auto-navigate ("bot map") system.
- **Contact-cache damage** (`vlgvxpruyfuxogsib` / `hymidyeqrrwulesib`): per-zone impulse accumulation
  → `ProcessDirectDamage(DT_CUSTOM,…)` with per-zone coefficients + crew-injury lerp
  (`unknown_16458.c:244-333`, `unknown_18705.c:313-402`).

What is **NOT recoverable** — do NOT fabricate: the central integrator **`hkdxkhzidmpsib(dt,this)`**
(dispatched from `EOnSimulate`, `unknown_16458.c:216`; client twin `zcggxjtfzrsib`,
`unknown_18705.c:285`) has **no definition in any recovered file**. The lift-vs-altitude curve, the
collective→force mapping, and how `c_altFullForce`/`c_altNoForce` gate lift all live inside that
missing function. [UNVERIFIED]. **This was confirmed exhaustively** (2026-07-07, 2nd pass): every
non-junk block of both PBOs was decompressed with a relaxed extractor (9,546 server + 13,968 client
entries) — `hkdxkhzidmpsib` appears **only** as the license-gated call, never as a definition. Its
body is not shipped in plaintext in these two PBOs (it is the most heavily protected part of the paid
mod). The recoverable force anchor is the low-level applicator `qmdkldkpqpmlsib` (§below), not the
integrator that feeds it.

---

## 3. Config store — JSON-in-`$profile`, positional coeff map

[RECOVERED] The flight coefficients are **not in config.cpp**. They live in a per-class JSON file
loaded at mission init into a global `map<string,float>`:

- Store: `ref map<string,float> ssaBWDQnlAkkAQpglobal = new map<string,float>;`
  (`CLIENT\unknown_1929.c:4`; referenced everywhere as `ssaBWDQnlAkkAQp`).
- File: `$profile:\Heli_sib\<classname>_config.json`, auto-created from defaults if missing, then
  loaded, via `JsonFileLoaderVert<T>` (`CLIENT\unknown_6344.c:66-97`).
- Default struct: `class Json_Heli_MH6` (`CLIENT\unknown_6344.c:2-53`) with **legible field names +
  defaults**: `Lift_power=3.3`, `No_power=1200`, `Full_power=1250`, `side_strength=1.3`,
  `power_before=1.0`, `friction=0.3`, `Mass=1400.81`, `incline/front_tilt=0.9`, `m_povorot=0.4`,
  per-zone damage bools, `maxFuel=70`, `gasoline_costs=0.0004`, sound volumes, `coef_damage_weapon`,
  `auto_off_autopilot`, `auto_engine_shutdown`, etc.
- Load is **positional**: `vert_conf_MH6` does `ssaBWDQnlAkkAQp.Insert(child_name+"_"+num_mass, …)`
  incrementing `num_mass` (`unknown_6344.c:105-154`); the class reads them back in the **exact same
  order** in `go_conf()` (`unknown_16894.c:475-515`) / `pxmcpzlfyvhxsib()`
  (`unknown_16458.c:337-393`). So the JSON→coeff mapping is index-by-index:

| JSON field (`Json_Heli_MH6`) | Simple-model field (`go_conf`) |
|---|---|
| `duration` | `c_startDurationInv` |
| `Lift_power` | `c_liftForceCoef` |
| `No_power` | `c_altNoForce` |
| `Full_power` | `c_altFullForce` |
| `side_strength` | `c_cyclicAsideForceCoef` |
| `power_before` | `c_cyclicForwardForceCoef` |
| `friction` | `c_bodyFrictionCoef` |
| `Mass` | `c_heliMass` |
| `incline`/`front_tilt`/`inclineMouse`/`front_tiltMouse`/`m_povorot` | `m_naklon`/`m_nabor`/`m_naklonMouse`/`m_naborMouse`/`m_povorot` |
| `Chassis`/`Body`/`Engine`/`Fuel`/`Rotor1`/`Rotor2` | `b_Chassis`/`b_Body`/`b_Engine`/`b_Fuel`/`b_Rotor1`/`b_Rotor2` (damage-zone enable bools) |

[INFERRED] The `MH6` suffix (`Json_Heli_MH6`, `vert_conf_MH6`) suggests a per-model config family
(an MH-6 Little Bird variant); `vert_conf` dispatches by `child_name.Contains("HeliMH6_SIB")`
(`unknown_6344.c:57-64`) — other models would provide their own `Json_Heli_*` + `vert_conf_*`.

---

## 4. Inputs & actions

[RECOVERED]

- **Flight inputs** are custom `UASIBHeli*` UA actions (see §2a table) declared in `modded_Inputs.xml`
  (`inputs = "HelicopterModScripts/modded_Inputs.xml"`, `unknown_15761.c:21`) and registered
  client-side via `GetUApi().GetInputByName("UASIBHeliEngine_new" / "UASIBHeliAutopilot" /
  "UASIBHeliHide")` (`CLIENT\unknown_18863.c:121,188,255`). [UNVERIFIED] the `.xml` itself — not
  recovered (binary XML in the PBO); the input *names* are confirmed from the script reads.
- **In-vehicle continuous actions**: `DefaultActionInputHelicopterEngine` → `UASIBHeliEngine_new`,
  `DefaultActionInputHelicopterHide` → `UASIBHeliHide` (`SERVER\unknown_294.c` / `unknown_286.c`;
  both `ContinuousDefaultActionInput`, `m_DetectFromTarget=false`).
- **Engine start/stop** actions: `ActionHeliStartEngineSIB` / `ActionHeliStopEngineSIB` (simple,
  `unknown_16894.c:609/645`) and mouse/keyboard variants `Action_Helicopter_Start_Engine_*` /
  `Stop_Engine_*` (advanced, `unknown_10783.c:39-228`). Start sets `hide_start=1.0` +
  `heli.OnEngineStart()`; stop sets `hide_start=0`/`hide_rotor=0`, zeroes rotor-speed-wanted,
  error-stops the blur anims, `heli.OnEngineStop()`.
- **Autopilot / cockpit-button actions** raycast a memory point: `GetMemoryPointPos("avtopilot")` /
  `("button_beam")` then `ModelToWorld` + distance-gate the player
  (`CLIENT\unknown_2491.c`, `unknown_2306.c`). Pattern: cockpit buttons are memory points you must
  be within range of.

---

## 5. Rotor animation & engine start sequence

[RECOVERED] Rotors are driven by **`SetAnimationPhase` on paired anim sources**, not by RPM:

- Anim sources (config `unknown_15761.c:455-514`): `hide_rotor`, `hide_start`, `rot_h_start` /
  `rot_h_blur_end` (rotor 1), `rot2_h_start` / `rot2_h_blur_end` (rotor 2), plus `toplivo` (fuel) and
  a bank of dial detectors (`HorizonBankdetect`, `visotadetect`, `rpmdetect`, `speed`, …).
- **Blur swap**: a static (`rot_h_start`) and a spinning-blur (`rot_h_blur_end`) mesh are cross-faded
  by health-gated helpers `animatezzstart` (spinning: start=1, blur=0) / `animatezzstop` (stopped:
  start=0, blur=1) — only if `GetHealth01("Rotor1"/"Rotor2") > 0.15`
  (`unknown_16894.c:526-595`). Dead rotors get `animatezzerror1/2` (freeze).
- **Engine-start sequence** (`SERVER\unknown_12270.c:7-25`, RPC `HelicopterStartSimulate`): when
  `hide_start==1.0` → `SetAnimationPhase("hide_rotor",1)`, `animatezzstart(heli)`, `rot_start(heli)`,
  `mainRotor(heli)`. `rot_start` (`unknown_5972.c:258`) sets the rotor-speed-wanted field (spin-up).
- **Fuel**: anim source `toplivo` doubles as the fuel gauge; `ConsumeFuel()` decrements it every 5 s
  by `z_zatrat + (fuel-damage/4)` (`unknown_16894.c:454-472`).

[INFERRED] Rotors are baked geometry with a blur variant here (not attachable items) — contrast with
the *other* community heli (`HelicopterSIB_Hommade_LF`) documented in the SKILL where blades were
inventory attachments. Different mod, different choice.

---

## 6. Engine start/stop, fuel, damage zones

[RECOVERED]

- **Damage zones** (`unknown_15761.c:580-684`): `Body`, `Chassis`, `Engine`, `Fuel`, `Rotor1`,
  `Rotor2`, `Proj` — each with `memoryPoints[]={"dmgzone_*"}`, own hitpoints (Body 6000, Chassis/
  Engine 3000, Rotor1/2 2000, Fuel/Proj 700), `transferToGlobalCoef` near-0 (zones don't bleed into
  global health except Body's 0.001). Global `hitpoints=1000`.
- **Per-zone enable bools** `b_Chassis/b_Body/b_Engine/b_Fuel/b_Rotor1/b_Rotor2` come from the JSON;
  **if all six are 0 → `SetAllowDamage(false)`** (invulnerable heli, `unknown_16894.c:500-503`).
- **Contact damage** (simple `OnContact`, `unknown_16894.c:400-421`): `dmg = Impulse *
  m_dmgContactCoef`; a hard hit (`vel>10 || angVel>5 || Impulse>1000`) also subtracts the whole zone
  health (destroys the zone).
- **Weapon damage** gate (`SERVER\unknown_3380.c`): `EEOnDamageCalculated` returns false (no damage)
  when `coef_damage_weapon==0`; `EEHitBy` scales incoming damage by `coef_damage_weapon`
  (add-back if `<1`, extra if `>1`). Blades (`SIB_blade`) and doors (`Sib_heliDoor`) proxy to their
  parent heli's coefficient.
- **Transport-hit impulse** (`unknown_10783.c:118-146`): overrides `DayZPlayerImplement.
  RegisterTransportHit` — a destroyed heli hitting the player applies `dBodyApplyImpulse`.

---

## 7. Client/server split & the license gate

[RECOVERED]

- Both flight models are `modded class HeliTest_SIB` present in **both** `SERVER\` and `CLIENT\`
  (`unknown_16894.c` on both; advanced `unknown_16458.c` server / `unknown_18705.c` client). The
  physics run **server-authoritative**: `EOnSimulate` bodies are gated `if (GetGame().IsServer())`
  (`unknown_16894.c:428`; advanced additionally `&& license_active_helisib`,
  `unknown_16458.c:214`).
- The advanced model's `license_active_helisib` flag is set true only after a successful HTTP GET to
  `sibnic.info` returning a signed config (`unknown_10783.c:319-395`). **When authoring your own heli,
  drop the whole license layer** — it is DRM specific to this author, not part of the flight pattern.

---

## 8. NOT recovered / [UNVERIFIED] — do not fabricate

- **`config.bin`** was not decompiled; the config used here is the *script* config
  (`unknown_15761.c`). A real deployed heli would also have a binarized `config.bin`; assume the
  script config is authoritative for classes/inheritance but **verify any exact numeric against the
  live mod** before shipping.
- **`model.cfg`** (skeleton bones, the real rotor/wheel animation `class Animation` sources bound to
  the `.p3d` selections) — not recovered. The AnimationSources *names* are known (from config); the
  model.cfg bone graph is [UNVERIFIED].
- **The `.p3d` memory points** — inferred from script reads (`dmgzone_body/chassis/engine/fuel/
  rotor1/rotor2/proj`, `avtopilot`, `button_beam`, crew `pos_*` / proxy `crew*`) but the actual model
  is not present. [UNVERIFIED] the full memory-point set.
- **The advanced integrator `hkdxkhzidmpsib`** (the true lift/collective/altitude curve) — referenced,
  definition missing. The lift-vs-altitude force law is [UNVERIFIED]. A 2nd exhaustive pass (all
  23,514 non-junk blocks across both PBOs re-decompressed with a patched extractor) confirmed the
  body is not present in plaintext — search driver preserved at
  `<research-notes>/lfbanov-sibnic-heli/exhaustive_integrator_search.py`.
- **`modded_Inputs.xml`** — input names confirmed from script; the XML bindings/defaults not
  recovered.

## Takeaway for building your own heli

Buildable today from RECOVERED material: the class chain (`HeliTest_SIB : Heli_sib_cript :
CarScript`), the `AnimationSources`/`DamageZones`/`Crew` config, the input set + engine-start/stop
actions, the rotor blur-swap animation, and the **simple kinematic flight loop** (`KeyboardPilot` +
`Simulate` with `SetVelocity`/`SetOrientation`). That is a complete, self-contained flyable heli.

Do NOT reach for the advanced force-based model — its core is missing and it's license-locked. If you
want true `dBodyApplyForce` rotor physics, treat `qmdkldkpqpmlsib` (`unknown_10783.c:454`) as the only
recovered anchor and design the lift curve yourself (mark it `[DESIGN]`).

---

# RFFS (RedFalcon) — clean reference implementation

[VERIFIED-RFFS] Source: **RedFalcon Flight System "RFFS"** heli framework (author `RedFalcon`,
authorID `76561198100307085`, credits `GumbyMN`; `RFFSHeli_Core` version 1.0). De-rapified by Mikero
(clean, non-obfuscated — every claim below is read straight from disk). Source copies live in
`<research-notes>\redfalcon-rffs-heli\`:
`Core_config.cpp`, `S76_config.cpp`, `Core_scripts\{3_Game,4_World,5_Mission}\...`,
`S76_scripts\4_world\RFFSHeli_S76.c`. Citations are `path:line` into those copies (paths abbreviated:
`Core.c` = `Core_scripts\4_World\RFFSHeli_Core.c`).

**This is the recommended buildable reference.** Unlike SIB, nothing here is DRM-gated or missing —
the full flight integrator is on disk and legible. It is a *far* more physically-grounded flight model
than SIB's (real thrust-vector rotation by attitude, ground effect, translational lift, speed/climb
governors, aerodynamic drag, weathervaning), while still being **kinematic** (`SetVelocity`-based, no
`dBodyApplyForce`) — confirming SIB's core lesson across a second independent author.

## 1. Architecture — `RFFSHeli_S76 : RFFSHeli_base : CarScript`

[VERIFIED-RFFS] Two layers (vs SIB's three):

| Layer | Adds | Cite |
|---|---|---|
| `CarScript` (vanilla) | wheels, seats, fuel, damage, sound | — |
| `RFFSHeli_base : CarScript` | the **entire flight model** + all tunables + sync vars + CarScript ground fallback (4 `NivaWheel` wheels, axles, steering, gearbox), aviation attachment slots, rotor/gauge `AnimationSources` | `Core.c:2`, config `Core_config.cpp:517-873` |
| `RFFSHeli_S76 : RFFSHeli_base` | per-heli config values (fuel/airspeed/altitude/etc.), door/seat/crew wiring, per-model gauge needle logic, wreck class | `RFFSHeli_S76.c:1`, config `S76_config.cpp:116-734` |

Same **CarScript-as-aviation** hack as SIB and LM_Planes: `class RFFSHeli_base: CarScript`
(`Core_config.cpp:517`) declares a full ground `SimulationModule` (`drive="DRIVE_AWD"`, torque curve,
gearbox, 4 axles/wheels — `Core_config.cpp:525-664`) that exists only as the taxi fallback. The heli
sets `SetEventMask(EntityEvent.SIMULATE)` + `SetEventMask(EntityEvent.FRAME)` (`Core.c:180-181`) and
overrides **`EOnSimulate`** (`Core.c:1027`) to fly itself with `SetVelocity`/`SetOrientation`.
`vehicleClass = "Expansion_Helicopter"` (`Core_config.cpp:523`).

## 2. Flight model — `FlightSimulation()`, kinematic but physically grounded

[VERIFIED-RFFS] The whole flight model is `FlightSimulation()` (`Core.c:1767-2129`), called from
`EOnSimulate` **server-side only** when the engine is running and `m_heli_state == 2`
(`Core.c:1149-1156`). The client re-runs `EOnSimulate` off `EOnFrame` for smoothing every >5 ms
(`Core.c:1008-1016`) but the authoritative integration is server-side.

### 2a. Controls → state (per tick)

Inputs are read server-side in `KeyboardInput()` (`Core.c:510-544`) from pilot `CrewMember(0)` and/or
copilot `CrewMember(1)`, each via `player.GetInputInterface().SyncedValue("UARFFS...")`. The client
also *reads* the same synced values in `KeyboardInputClient()` (`Core.c:475-507`) purely to keep them
network-synced (it discards the result). Custom UA inputs (declared in
`inputs="RFFSHeli_Core/modded_Inputs.xml"`, `Core_config.cpp:30`; XML not in the research copy but the
names are confirmed from the script reads):

| Input | State written | Meaning | Cite |
|---|---|---|---|
| `UARFFSCyclicForward` / `…Back` | `r_cyclic_ForwardBack ∓= v * c_tilt_rate` | cyclic pitch (fore/aft) | `Core.c:549-550` |
| `UARFFSCyclicLeft` / `…Right` | `r_cyclic_LeftRight ∓= v * c_lateral_tilt_rate` | cyclic roll | `Core.c:551-552` |
| `UARFFSPedalLeft` / `…Right` | `r_pedal_LeftRight ∓= v * c_rotation_rate` | anti-torque / yaw (tail rotor) | `Core.c:553-554` |
| `UARFFSCollectiveUp` / `…Down` | `m_collective_level = Clamp(±1, 0, 20)` | **collective, discrete 0-20 detent** | `Core.c:563-583` |
| `UARFFSToggleHUD` | toggles `m_show_hud_*` (3-tick debounce) | HUD on/off | `Core.c:661-668` |
| `UARFFSToggleCommand` | toggles `m_pilot_in_command` | hand control pilot↔copilot | `Core.c:683-690` |
| `UARFFSRecover` | `m_flight_recovery_*` | flight-recovery / auto-level mode | `Core.c:637-657` |

[VERIFIED-RFFS] **The collective is a discrete 0-20 lever (each = 5% → 0-100%)**, not analog
(`m_collective_level` comment `Core.c:105`). The up/down keys step it with a 5-frame repeat gate
(`Core.c:565-583`), and each tick the applied thrust is
`r_collective_power = ((m_collective_level)/20) * c_thrust_rate` (`Core.c:543`). This is RFFS's
signature control and the cleanest difference from SIB (which had no collective detent). Two arcade
fallbacks exist: `c_simple_collective` (server master-config global) and `c_heli_simple_collective`
(per-heli), which replace the detent with a momentary `r_collective_power = ±(0.85 * c_thrust_rate)`
while a key is held (`Core.c:585-592`).

### 2b. Integration — `FlightSimulation()` (`Core.c:1767-2129`)

The realistic (non-recovery) branch runs `Core.c:1895-2126`:

1. **Ceiling clamp**: if `GetPosition()[1] > c_max_altitude_m`, hard-clamp Y via `SetPosition`
   (`Core.c:1774-1780`). Default `c_max_altitude_m = 1219.2` (`Core.c:38`), overridden per-heli
   (S76 = 1250 m, `RFFSHeli_S76.c:45`).
2. **Damage-driven yaw/power loss**: a damaged/ruined `TailRotor` injects escalating uncommanded
   `r_pedal_LeftRight` spin (`Core.c:1783-1801`); a damaged `Engine` or `MainRotor` cuts
   `r_collective_power *= 0.85` (`Core.c:1804-1817`).
3. **Angular-moment model**: cyclic/pedal inputs feed `m_angular_moment` (a carried-forward angular
   momentum vector), which is drag-decayed each tick by `c_tilt_drag_rate * m_cyclic_modifier`, clamped
   to `±c_angular_moment_limit`, and snapped to 0 near zero (`Core.c:1898-1931`). Attitude is then
   rotated by building `YawPitchRollMatrix` from current orientation and from `m_angular_moment` and
   `Math3D.MatrixMultiply3`-ing them (`Core.c:1954-1961`) — a proper 3D orientation compose, not
   SIB's per-axis literal nudges. Cyclic self-centers via `c_cyclic_retard` when input is released
   (`Core.c:1947-1952`).
4. **Collective → world lift vector** (`Core.c:1993-1996`): the scalar `r_collective_power` is rotated
   into world space by the heli's own pitch/roll/yaw:
   ```
   vector_x = r_collective_power * (-sin(roll)*cos(yaw) - cos(roll)*sin(pitch)*sin(yaw))
   vector_y = r_collective_power * ( sin(roll)*sin(yaw) - cos(roll)*sin(pitch)*cos(yaw))
   vector_z = r_collective_power * ( cos(roll)*cos(pitch))
   ```
   So tilting the disc (via cyclic) redirects lift into horizontal translation — the physically
   correct helicopter behaviour, and a real step up from SIB's "pitch attitude → scalar forward speed".
5. **Ground effect**: near the ground on descent, `vector_z` is boosted by a
   `c_rotor_diameter_m`-scaled term (`Core.c:1998-2000`).
6. **Effective translational lift (ETL)**: extra `vector_z` added as a function of horizontal speed
   `~(translational_speed*0.00007)^2 * c_thrust_rate` (`Core.c:2002-2004`).
7. **Speed governor**: as horizontal speed approaches `c_max_airspeed_kph`, a `translational_speed^4 /
   ((max+40)*0.277778)^4` term is subtracted from the horizontal thrust components — but only when the
   thrust would *increase* speed, not brake (`Core.c:2006-2027`).
8. **Climb governor**: as `heli_velocity[1]` approaches `c_max_climb_rate`, `vector_z` is scaled down
   by a 5th-power term (`Core.c:2029-2030`).
9. **Merge + drag**: thrust vectors add onto current velocity (`Core.c:2032-2035`); aerodynamic drag
   `c_aero_drag_rate` is split proportionally across X/Z and subtracted (`Core.c:2037-2048`).
10. **Weathervaning**: the nose is yawed toward the velocity vector by
    `(angle_diff/360) * log2(speed*0.1) * c_bank_turn_coeff` (`Core.c:2069-2087`) — banked turns
    naturally rotate the heading. Wind terms exist but are **commented out** (`Core.c:2050-2067`).
11. **Trainer mode**: optional pitch/roll clamp to ±35° and descent clamp to −7.5 m/s
    (`Core.c:2089-2106`).
12. **Extensibility hook**: `AdditionalThrustVectors(velocity, orient, out, out)` (`Core.c:2132-2136`,
    empty base) lets a concrete heli add thrust (e.g. tilt-rotor) by override.
13. **Apply**: `SetOrientation(heli_orient)` then `SetVelocityAdjusted(heli_velocity)`
    (`Core.c:2116-2119`); the four `r_*` input accumulators reset to 0 (`Core.c:2122-2125`);
    `ConsumeFuel()` at the end (`Core.c:2128`).

[VERIFIED-RFFS] **`SetVelocityAdjusted`/`GetVelocityAdjusted`** (`Core.c:2465-2487`) wrap
`SetVelocity`/`GetVelocity(this)` with a per-heli horizontal scale
(`c_speed_adjustement_factor` / `c_speed_factor`) — a DayZ-1.21/1.28 speed-compensation fudge
(`Core.c:82-84`, S76 sets `SpeedFactor=195`, `RFFSHeli_S76.c:49`). **`dBodyApplyImpulse` is present
only as a commented-out line** (`Core.c:272`) — like SIB, the buildable model is kinematic, never
force-based.

### 2c. Recovery / auto-stabilization mode

[VERIFIED-RFFS] If `UARFFSRecover` is held and `c_allow_recovery`, the recovery branch
(`Core.c:1819-1894`) zeroes all control inputs, sets collective to 50% (`m_collective_level = 10`),
counters gravity (`heli_velocity[1] += 0.245`), bleeds vertical/horizontal speed, and eases the heli
back to a level attitude derived from its current velocity vector. This is RFFS's genuine
auto-stabilization — richer than SIB's simple attitude-recenter, but still not a PID. There is **no
autohover/auto-navigate** system (unlike SIB's license-gated `AutopilotState` bot-map).

## 3. Config framework — `MasterConfig` + per-heli `HeliConfig` (typed JSON, data-driven)

[VERIFIED-RFFS] Two-tier JSON config under `$profile:\RFFSHeli\`, loaded via `JsonFileLoader<T>` with
auto-create-from-defaults + version-bump-migrate:

- **`RFFSHeli_MasterConfig`** → `$profile:\RFFSHeli\MasterConfig.json` (`RFFSHeli_MasterConfig.c:193-268`,
  `ConfigVersion=12`): server-wide policy — HUD units/allow-1PP/3PP/helmet, control flags
  (`AllowTakeCommand`, `SimpleCollective`, `AllowRecoveryMode`, `Grounded`), sound volume, damage
  toggles + collision coef, storage flags, and a full crash-site model (create-on-ruin, scatter/damage
  inventory, spawn zombies with a default class list, distances/counts, loot damage). Read once in
  `EEInit()` server-side (`Core.c:287-352`).
- **`RFFSHeli_HeliConfig`** → `$profile:\RFFSHeli\<classname>_Config.json`
  (`RFFSHeli_HeliConfig.c:136-188`, `ConfigVersion=7`): per-model flight tuning — fuel capacity/rate,
  trainer mode, has-hydraulics, simple-collective, max airspeed/altitude/climb-rate, aero drag, bank-turn
  coeff, speed factor, and the four control rates (anti-torque / cyclic / collective / cyclic-dampening).
  The concrete heli seeds the defaults in its own `EEInit()` and calls `ApplyHeliConfig()`
  (S76: `RFFSHeli_S76.c:38-62`).

[VERIFIED-RFFS] **This is a genuinely typed, named config framework** — a class
`RFFSHeli_HeliConfigData` with named `protected` fields + `get*` accessors (`RFFSHeli_HeliConfig.c:3-133`),
consumed field-by-name in `ApplyHeliConfig()` (`Core.c:232-265`, e.g.
`c_thrust_rate = getControlsCollectiveThrustRate()*0.01*0.47`). Contrast SIB's **positional/index-by-index**
`map<string,float>` store — RFFS's is safer and self-documenting. Notable reusable pattern:
config values are stored as **percentages** (100.0 = baseline) that scale a hard-coded engineering
constant, so servers tune "±X %" without knowing the raw physics coefficient.

[VERIFIED-RFFS] **Config-boolean sync trick**: server packs ~12 config booleans into a single
`RegisterNetSyncVariableInt("c_encoded_config_bool")` bitfield (`Core.c:334-345`) and the client
un-bit-shifts it in `EOnSimulate` (`Core.c:1030-1081`). Reusable when you have many small client-visible
config flags and don't want a sync var per flag. (SIB used the same idea; independent reinvention.)

## 4. AnimationSources, rotors, memory points, Crew, DamageZones (config)

[VERIFIED-RFFS] **AnimationSources** (`Core_config.cpp:665-838`, S76 extends at `S76_config.cpp:318-545`),
all `source="user"` driven by `SetAnimationPhase`:
- **Rotors** — paired main+tail, each with 4 sources: `rotorN_speed` (spin phase), `rotorN_blur_hide`
  (static↔blur swap), `rotorN_blades_hide`, `rotorN_bent_hide` (damage states). Rotors are **baked
  geometry with a blur variant**, health-gated — same choice as SIB, opposite of the attachable-blade
  community heli.
- **Engine/state** — `engine_rpm`, `engine_running`, `engine_running_fast`, `rotor_spinning`.
- **Gauges** — `airspeed_kts`, `altitude_ft`, `agl_ft` (+ `_sm/_lg_hide` or per-model `_low/_med/_high_hide`
  multi-needle bands), `compass`, `pitch_orientation`, `roll_orientation`, `vs_ft` (+ up/down hide).
  Driven from `UpdateCockpitGauges()` (`Core.c:428-441`); the S76 adds 4-band airspeed / 3-band AGL /
  3-needle VS logic (`RFFSHeli_S76.c:85-158`).
- **Wheels/doors** — vanilla CarScript `damper_*`, `AnimHitWheel_*`, plus per-model `DoorsDriver`/
  `DoorsCoDriver`/`DoorsCargo1/2` (`S76_config.cpp:347-370`).

[VERIFIED-RFFS] **Engine-start / rotor-spin state machine** — `m_heli_state`
(0=off, 1=startup, 2=running, 3=shutdown, +11/13 mid-transition; `Core.c:100`). `ExecuteAnimations()`
(`Core.c:1323-1368`) dispatches per state; `StartUpAnimation()` ramps `rotor1_speed` and cross-fades
to blur at 80% of `c_startup_sound_length` (`Core.c:1481-1502`). `EvaluateDamageStates()`
(`Core.c:1371-1468`) is the failure brain: a missing/ruined wiring harness, ruined engine/main-rotor,
bingo fuel, or (if `c_has_hydraulics`) low hydraulic fluid all force `m_heli_state = 3` (auto-shutdown);
low hydraulics also degrade cyclic authority via `m_cyclic_modifier` (`Core.c:1407-1414`).

[VERIFIED-RFFS] **Memory points** (from config `memoryPoints[]` + script reads):
`dmgZone_chassis/avionics/engine/hydraulics/fuelTank/rotor1/rotor2/lights_1_1`
(`S76_config.cpp:561-665`), `ptcExhaust_start` (engine smoke, `Core.c:1332/1343`), crew
`crewDriver/crewCoDriver/crewCargo1-4` + `pos_*`/`pos_*_dir` (`S76_config.cpp:125-171`), headlight
points via CarScript. **The `.p3d` itself is not in the research copy** — memory points are
[VERIFIED-RFFS] from config/script text, [UNVERIFIED] as actual model selections.

[VERIFIED-RFFS] **Crew** (`S76_config.cpp:125-171`): Driver + CoDriver + Cargo1-4 (6 seats), each with
`actionSel`/`proxyPos`/`getInPos`/`getInDir`. Both front seats have `isDriver=0` (control is arbitrated
in script via `m_pilot_in_command`, not the vanilla driver flag) — this is how RFFS gives pilot AND
copilot flight control with a hand-off toggle.

[VERIFIED-RFFS] **Per-component DamageZones** (`S76_config.cpp:546-677`) — a real aviation damage model:
`Chassis`, `Avionics`, `Engine`, `Hydraulics`, `FuelTank`, `MainRotor`, `TailRotor`, `Reflector_1_1`
(landing light). Each has own hitpoints + `transferToZonesNames`/`Coefs` cross-links (e.g. Engine→Hydraulics
0.5, TailRotor→Chassis 0.75+Engine 0.2) and `inventorySlots`/`Coefs` tying part health to attachment
health. Global `hitpoints=8000`. Contact/collision damage flows through `m_ContactCache` +
`ChassisImpactDamage()` (hard skid landing >1500 fpm → `DecreaseHealth("Chassis")`, `Core.c:752-768`).

## 5. Inputs, actions, aviation attachments, HUD

[VERIFIED-RFFS] **Start/Stop actions** replace the vanilla car ones:
- `ActionStartHelicopter` (`ActionStartHelicopter.c:9-205`) — in-vehicle, driver/copilot-in-command
  only, blocked if `c_grounded` or engine ruined; on start it verifies battery(>5 energy)+igniter+
  (hydraulic hoses if applicable)+wiring+fuel, sets `m_heli_state=1`, and calls `OnBeforeEngineStart`.
  `ActionStopHelicopter` (`ActionStopHelicopter.c:1-101`) requires airspeed <8 kph → sets `m_heli_state=3`.
  Both vanilla `ActionStartEngine`/`ActionStopEngine` are `modded` to return false on an `RFFSHeli_base`
  (`ActionStartHelicopter.c:209-232`, `ActionStopHelicopter.c:104-127`), and `SetActions()` removes the
  car horn + start-engine actions (`Core.c:2456-2463`).
- **Component repair actions** — `ActionRepairHelicopter{MainRotor,TailRotor,Engine,Chassis,Hydraulics,
  Avionics,FuelTank,...}` + `ActionReplaceHelicopterAvionics`: each steps one damage zone up a health
  level with a repair item, driven off a per-player `RepairHelicopterActionData` zone selector
  (`ActionRepairHelicopterMainRotor.c`). This is the per-component maintenance loop that pairs with the
  DamageZones above.

[VERIFIED-RFFS] **Aviation attachments** replace the car vitals: `AviationBattery`, `AviationIgniterPlug`,
`AviationHydraulicHoses`, `AviationWiringHarness` (custom `CfgSlots` + inventory items in
`Core_config.cpp:159-505,875-908`). The heli overrides `IsVitalCarBattery/SparkPlug/...` → false and
`IsVitalAviationBattery` → true (`Core.c:2227-2260`); `GetBattery()` returns the aviation battery
(`Core.c:2268-2271`). Fuel = `CarFluid.FUEL`; hydraulic fluid = `CarFluid.OIL` (`Core.c:1135-1136`).

[VERIFIED-RFFS] **HUD** — `modded class IngameHud` (`headsUpDisplay.c:1`) creates
`RFFSHeli_Core/GUI/RFFSHelicopterGUI.layout` under the vanilla `LeftHUDPanel` (`:66-71`). Per-frame it
gets the player's `GetCommand_Vehicle().GetTransport()`, casts to `RFFSHeli_base`, and shows the panel
only for the in-command pilot/copilot with HUD enabled and (optionally) a pilot helmet (`:150-165`). It
reads telemetry straight off the synced heli fields (`RFFSHeli.m_airspeed_kph`, `m_altitude_m`,
`m_fuel_level`, `m_hydraulic_level`, `m_collective_level`) and `GetHealthLevel(...)` for warning lights
(`:202-490`). A **badly-damaged/ruined Avionics zone distorts or blanks the HUD** (`:167-187`) — a nice
touch tying the instrument panel to the avionics damage zone. Metric/imperial switch honoured throughout.

## 6. Multiplayer / sync

[VERIFIED-RFFS] Server-authoritative: `FlightSimulation()` only runs under `g_Game.IsServer()`
(`Core.c:1151`). State is pushed to clients via a bank of `RegisterNetSyncVariable*` in the ctor
(`Core.c:189-208`): telemetry floats (`m_altitude_m`, `m_agl_altitude_m`, `m_airspeed_kph`), the
`m_heli_state` int, `m_collective_level`, `m_rotor_spin`, fuel/hydraulic levels, klaxon/engine-damaged/
bullet-strike sound flags, `m_pilot_in_command`, and the packed `c_encoded_config_bool`. Every state
mutation calls `SetSynchDirty()`. The client mirrors the physics off `EOnFrame`→`EOnSimulate`
(`Core.c:1008-1016`) for smooth interpolation but never owns the authoritative velocity.

## 7. NOT in the research copy / [UNVERIFIED]

- **`modded_Inputs.xml`** — referenced (`Core_config.cpp:30`); the `UARFFS*` input *names* are confirmed
  from script reads (`Core.c:491-501,549-554,563-583`), but the XML bindings/defaults are not on disk.
- **`.p3d` models + `model.cfg`** — not in the copy. Memory points, rotor/gauge selections, and the
  skeleton bone graph are [VERIFIED-RFFS] as *names* (config/script), [UNVERIFIED] as actual model data.
- **`RFFSHelicopterGUI.layout`** and the sound `.p3d`/wave assets — referenced, not present.
- **`config.bin`** — the copies are Mikero-de-rapified `config.cpp`; treat as authoritative for
  classes/inheritance but verify exact numerics against the live PBO before shipping.

---

# MH6 — force-based reference implementation [RECOVERED, clean]

[RECOVERED] Source: the **MH6 Little Bird** helicopter by **Llama** — the *same author* as LM_Planes
(the fixed-wing reference this skill is built on). Authorship is nailed by the particle paths
`LM_LLAMA/LM_Vehicles/MH6/graphics/` (`MH6_scripts\b_off152027_o355.c:3-5`). The flight-model script was
recovered from `MH6_scripts.pbo` (JAPM brute-force recovery, 2026-07-07) and is **fully legible Enforce**
— unlike SIB's advanced model, nothing here is DRM-locked. Source copies live in
`<research-notes>\mh6-heli\`: `MH6_flightmodel.c` (the flight model,
identical twin `MH6_scripts\b_off175614_o48037.c`), `MH6_scripts\b_*.c` (actions/particles), and the
shared framework `Heli_Core\b_*.c`. Citations are `path:line` into `MH6_flightmodel.c` unless noted.

**This is the third independent heli on disk and the first buildable FORCE-BASED one.** Where SIB and
RFFS both fly kinematically (`SetVelocity`) and only SIB's *unrecoverable, DRM-locked* advanced variant
was force-based, MH6 applies real rigid-body forces every tick — `dBodyApplyForce(this, totalForce)` +
`dBodyApplyTorque(this, totalTorque)` (`:1165-1166`) — and its whole integrator is present in plaintext.
It proves the force-based model that SIB made look permanently gated is in fact viable and shippable.

## 1. Architecture — `MH6 : CarScript` + Pawn OwnerState/Move replication

[RECOVERED] Same **CarScript-as-aviation** hack as the other two helis and LM_Planes: `class MH6 extends
CarScript` (`:112`). But MH6's networking is the most advanced of the three helis — it uses the **custom
Pawn OwnerState/Move pipeline** (the same family LM_Planes uses for fixed-wing), not SIB's `SetSynchDirty`
polling or RFFS's `RegisterNetSyncVariable*` bank:

| Layer | Role | Cite |
|---|---|---|
| `MH6OwnerState extends CarScriptOwnerState` | replicated flight state: `m_bAutoHoverEnabled`, `m_fHoverTargetAltitude`, `m_fRotorSpeed`, `m_iAutoLandState`, landing target XYZ, and the 4 smoothed control channels (`m_fCollectiveSmooth`/`CyclicPitch`/`CyclicRoll`/`Pedal`). `Write`→`PawnStateWriter`, `Read`←`PawnStateReader` | `:17-62` |
| `MH6Move extends CarScriptMove` | per-tick pilot input: `m_fCyclicPitch`, `m_fCyclicRoll`, `m_fPedal`, `m_fThrottle`, plus `m_iToggleAutoHover`/`m_iAutoLand` command ints + autoland target XYZ. `Write`→`PawnMoveWriter`, `EstimateMaximumSize += 9*4` | `:64-110` |
| `MH6 : CarScript` | the flight model itself + rotor animation + autohover/autoland state machines + lights | `:112-1624` |

The Pawn wiring: `GetOwnerStateType()`→`MH6OwnerState`, `GetMoveType()`→`MH6Move` (`:286-294`);
`ObtainMove` (client packs inputs into the move, `:296-324`), `ConsumeMove` (server applies them +
dispatches autohover/autoland commands, `:326-351`), `ReplayMove` (client-prediction replay, `:353-368`),
`ObtainState`/`RewindState` (snapshot + rollback with client-interp targets, `:370-424`). This is
**client-side prediction + server reconciliation** — the same reason LM_Planes feels non-laggy, now on a
heli. It still keeps the vestigial CarScript ground drivetrain (gearbox forced to `CarGear.FIRST` every
tick in `OnInput`/`OnGearChanged`, `:1209-1211`/`:1244-1254`) as the taxi fallback.

Two `RegisterNetSyncVariable*` remain for the two discrete states that must survive to all observers:
`RegisterNetSyncVariableBool("m_AutoHoverEnabled")` + `RegisterNetSyncVariableInt("m_AutoLandState",0,4)`
(`:243-244`) — the continuous physics rides the Pawn state, the toggles ride sync vars.

## 2. The simulate loop — `EOnSimulate` / `EOnPostSimulate`

[RECOVERED] Physics run **server-or-owner** (`IsServerOrOwner()`), i.e. server-authoritative with owner
client-prediction. `EOnSimulate` (`:1276-1343`):

1. **Non-owner clients** just `Synchronize()`, interpolate the smoothed channels toward their synced
   targets (`UpdateClientInterpolation`, lerp rate `CLIENT_INTERP_RATE=8`, `:449-461`), animate rotors,
   and return (`:1280-1286`).
2. **Server/owner**: `CachePhysicsState()` (`:507-536`) snapshots velocity, angular velocity, position,
   speed, height-AGL, and the three body basis vectors `m_CachedFwd/Right/Up` (from `ModelToWorld` of the
   local axes) — everything the force model reads, sampled once per tick.
3. **Engine off** → spool rotor down (`SmoothApproach` toward 0 at `1/(ENGINE_SPOOL_DOWN*ROTOR_INERTIA)`),
   force `PHASE_GROUNDED`, `ClearNativeDamping()`, return (no forces) (`:1293-1301`).
4. **Engine on** → `SetupNativeDamping()`, spool rotor up toward `m_RotorSpeedTarget=1.0`, run
   `UpdateFlightPhase`, then (if enabled) `UpdateAutoHover` / `UpdateAutoLand`, smooth the 4 control
   channels toward their net inputs (`SmoothApproach` at `INPUT_SMOOTHING=4`), and — **only if autoland is
   OFF** — call `ApplyHelicopterPhysics(dt)` (`:1303-1325`). Autoland drives the heli kinematically
   instead (see §5).
5. **Adaptive sync** (`:1327-1342`): accumulate dt, and every `GetCurrentSyncInterval()` (0.033 s when
   `m_RotorSpeed>0.3`, else 0.1 s idle) call `SetSynchDirty()` if state changed or the rotor is spinning.

`EOnPostSimulate` (`:1345-1500`) runs the **owner-client input read**: it polls the `UAKTHeli*` inputs
(§6), integrates the collective throttle, handles the autohover/autoland key presses + auto-cancel on
manual override, and updates the landing marker object. It also updates a `UniversalTemperatureSource`
(engine heat) server-side (`:1495-1499`).

Native rigid-body damping is set once via `dBodySetDamping(this, BASE_LINEAR_DAMPING=0.05,
BASE_ANGULAR_DAMPING=0.15)` while the engine runs and cleared on stop (`:463-484`). The script's own drag
and PD torques ride on top of that baseline.

## 3. The PD flight controller — `ApplyHelicopterPhysics(dt)` (`:980-1167`)

[RECOVERED] This is the core and the reason MH6 is the force-based reference. It accumulates a single
`totalForce` + `totalTorque` and applies both at the end. All constants below are `protected const`
literals in the class body (`:141-176`) — **there is no JSON config** (contrast SIB/RFFS; the config.bin
that might override was not recovered, see §7).

### 3a. Rotor-RPM authority gates (realism: no control without RPM)

Three `Ramp01(m_RotorSpeed, a, b)` smoothstep gates scale every control channel by how spun-up the rotor
is (`:988-990`):
- `liftAuth = Ramp01(m_RotorSpeed, 0.05, 0.35)` — lift comes online first
- `tailAuth = Ramp01(m_RotorSpeed, 0.12, 0.40)` — anti-torque next
- `cyclicAuth = Ramp01(m_RotorSpeed, 0.18, 0.50)` — cyclic last (needs the most RPM)

`m_RotorSpeed` is a normalized 0..1 spool value, `SmoothApproach`-ed toward 1.0 while the engine runs at
rate `1/(ENGINE_SPOOL_UP=3 * ROTOR_INERTIA=2)` (`:1305-1307`). `Ramp01` is `SmoothStep01((x-a)/(b-a))`
(`:492-499`). **The cyclic does not respond until the rotor has real RPM** — a genuinely realistic
authority curve, not present in SIB or RFFS.

### 3b. Collective → lift force (with atmosphere, translational lift, ground effect)

When `liftAuth>0` (`:1001-1012`):
```
weightForce   = VEHICLE_MASS(1400) * 9.81
baseThrust    = weightForce * 1.65          // maxThrustRatio: 65% thrust margin over hover
rotorEfficiency = m_RotorSpeed * m_RotorSpeed
thrustMag     = baseThrust * m_CollectiveSmooth * rotorEfficiency
thrustMag    *= densityRatio * transLift * liftAuth * groundEffect
totalForce   += m_CachedUp * thrustMag       // lift along the body up-axis
```
- `densityRatio = StandardAtmosphere.GetDensityRatio(altitude)` (`:986`) — real ISA air-density falloff
  (see §4); lift drops with altitude, giving a soft service ceiling.
- `transLift = CalculateTranslationalLift(forwardSpeed)` — effective translational lift: 1.0 below 2 m/s,
  ramping to `TRANS_LIFT_MAX=1.12` at `TRANS_LIFT_SPEED=12` m/s (`:599-605`).
- `groundEffect = CalculateGroundEffect(heightAGL)` — up to `GROUND_EFFECT_BONUS=1.15` within
  `GROUND_EFFECT_HEIGHT=4` m, quadratic falloff (`:607-615`).

Lift is applied along the **body up-vector `m_CachedUp`**, so tilting the airframe (via cyclic torque)
redirects lift into horizontal translation — the physically-correct helicopter behaviour, achieved here
through real torque + force rather than RFFS's explicit sin/cos lift-vector rotation.

### 3c. Cyclic + tail torques (attitude authority)

- **Cyclic** (`cyclicAuth>0`, `:1038-1053`): `rotorAuthority = m_RotorSpeed² * cyclicAuth`; pitch torque
  `= m_CyclicPitchSmooth * CYCLIC_PITCH_RATE(65) * rotorAuthority * 80` about `m_CachedRight`; roll torque
  `= m_CyclicRollSmooth * CYCLIC_ROLL_RATE(70) * rotorAuthority * 70` about `m_CachedFwd`.
- **Tail rotor / yaw** (`tailAuth>0`, `:1055-1065`): models main-rotor reaction torque
  (`mainRotorTorque = m_CollectiveSmooth * m_RotorSpeed * 35`) + a fixed counter-torque (`-0.9×`) + pilot
  pedal yaw (`m_PedalSmooth * PEDAL_YAW_RATE(75) * tailAuthority * 120`), all about `m_CachedUp`. So more
  collective induces more anti-torque demand — a real coupling.

### 3d. Attitude stability (the "P" term) — only when hands-off

When **not** in autohover (`:1067-1101`): read the airframe tilt from memory-point geometry
(`GetTiltFromAxisPoints`, §4), and if the pilot isn't commanding that axis (`|cyclicSmooth|<0.05`) and the
tilt is in `(3°,70°)`, apply a restoring torque proportional to angle:
```
pitchCorrection = -pitchDeg * PITCH_STABILITY(0.85) * m_RotorSpeed * 12 * pitchScale  // about Right
rollCorrection  = -rollDeg  * ROLL_STABILITY(0.90)  * m_RotorSpeed * 12 * rollScale   // about Fwd
```
`pitchScale`/`rollScale` fade the correction in with airspeed (weaker near hover, halved below 1.2 m AGL)
so it doesn't fight low-speed manoeuvring. **This is the proportional term of a PD attitude controller.**

### 3e. Angular-rate damping (the "D" term) — always on

`:1103-1116`: project angular velocity onto each body axis and apply opposing torque:
```
totalTorque += Right * (-pitchRate * PITCH_DAMPING(5.0) * 800 * dampingScale)
totalTorque += Fwd   * (-rollRate  * ROLL_DAMPING(5.5)  * 700 * dampingScale)
totalTorque += Up    * (-yawRate   * YAW_DAMPING(4.5)   * 600 * dampingScale)
```
`dampingScale = 0.6` in autohover, else 1.0. **P (3d) + D (3e) = a full PD flight-stability controller**,
the defining feature of MH6's model.

### 3f. Quadratic drag + overspeed + climb limiter (force domain)

- **Per-axis quadratic drag** scaled by `densityRatio` (`:1118-1126`): `-Fwd * fwdSpeed*|fwdSpeed| *
  DRAG_FORWARD(0.4) * densityRatio` and likewise for side (`DRAG_SIDE=7.0`) and vertical
  (`DRAG_VERTICAL=3.5`). Side drag ≫ forward drag → the heli resists sideways slip strongly (realistic).
- **Overspeed limiting** (`:1128-1132`): above `MAX_FORWARD_SPEED=70` m/s, subtract a quadratic
  `overspeed² * 4` term along the velocity direction (hard soft-cap).
- **Near-ground climb limit** (`:1135-1147`): between 0.5–3 m AGL (outside liftoff), clamp vertical speed
  to `Lerp(4,6, heightAGL/2)` m/s by subtracting `excess * VEHICLE_MASS * 2` — controlled takeoff, no
  rocket-jump off the pad.

`dBodyApplyForce(this, totalForce)` + `dBodyApplyTorque(this, totalTorque)` (`:1165-1166`) commit it all.

## 4. Shared framework — `Heli_Core` + memory-point geometry

[RECOVERED] MH6 depends on `Heli_Core.pbo`. The only **legible, sizeable** class recovered from it is
`class StandardAtmosphere` (`Heli_Core\b_off89829_o1538.c:2-43`) — a static ISA atmosphere helper the
flight model calls for `densityRatio`:
- `GetDensity(altitude_m)` uses the real barometric law:
  `SEA_LEVEL_DENSITY(1.225) * (temp/288.15)^(-(g/(L*R))-1)` with `L=-0.0065`, `R=287.05`, `g=9.80665`,
  clamped to `MAX_ALTITUDE=2000` m (`:12-21`).
- `GetDensityRatio` = density/sea-level (`:22-25`); plus `GetPerformanceFactor` (1.0 below 1200 m, lerp to
  0.6 at 2000 m), `IsApproachingCeiling` (>1800 m), `GetCeilingWarningLevel` (`:26-42`). **This is the same
  ISA-atmosphere idea LM_Planes uses for fixed-wing**, reused for the heli — another Llama through-line.
- [UNVERIFIED] the *rest* of `Heli_Core\b_*.c` — the remaining 25 blocks recovered as **JAPM anti-tamper
  shells** (obfuscated commented `static float ...Hash()...` lines) or byte-fragment junk, not real logic.
  Whether Heli_Core defines any shared heli base beyond `StandardAtmosphere` is [UNVERIFIED].

**Attitude sensing from memory points** (`GetTiltFromAxisPoints`, `:566-587`): rather than read
`GetOrientation()` Euler angles (SIB's approach), MH6 computes pitch/roll from the world-space height delta
between `axis_front`/`axis_back` and `axis_left`/`axis_right` memory points via `Atan2`. Rotor positions
read `rotor_main` / `rotor_tail` memory points with sane fallbacks (`GetMemoryPointSafe`, `:549-564`).
[UNVERIFIED] the actual `.p3d` memory-point set (config.bin/model not recovered) — but the *names*
(`axis_front/back/left/right`, `rotor_main/tail`) and animation selections (`rotor_1_1`, `rotor_2_1`,
`rotor_1_1_hide`, `rotor_1_1_rotate_hide`, `seat_driver/codriver/cargo1/cargo2`, `seat_con_1..4`) are
confirmed from script reads.

## 5. Autohover & autoland — kinematic state machines on top of force flight

[RECOVERED] MH6 is a **hybrid**: real force-based free flight, but the assist modes switch to kinematic
`SetVelocity` for scripted precision.

- **AutoHover** (`UpdateAutoHover`, `:663-698`): a PD altitude+attitude hold that writes *into the control
  channels* (not `SetVelocity`) — throttle `= 0.68 hover + altErr*0.06 - vertVel*0.22` (clamped 0.30..0.95),
  cyclic corrections from `GetTiltFromAxisPoints` to null tilt, and pedal yaw-rate damping. Toggled by
  `Server_ToggleAutoHover` (`:1268-1274`); auto-cancels on manual cyclic/collective input (`:1462-1469`).
  It also adds an extra horizontal-velocity damping *force* in `ApplyHelicopterPhysics` when hovering
  (`dampStr=500`, `:1149-1163`) — this is how it "parks" in the air.
- **AutoLand** (`MH6AutoLandState` FSM: `OFF→WARMUP→APPROACH→DESCEND→TOUCHDOWN`, enum `:1-8`; driver
  `UpdateAutoLand`, `:799-898`): a scripted approach that uses **`SetVelocity` + `dBodySetAngularVelocity`**
  each phase — WARMUP brakes to a stop, APPROACH flies horizontally toward the target at `Clamp(dist*0.4,
  0.3, 5)` m/s, DESCEND steps the descent rate down by height band (−2→−0.5 m/s), TOUCHDOWN settles and
  disarms (180 s cooldown). Preconditions gate it: engine on, speed `<AUTOLAND_MAX_SPEED(10)`, altitude
  `>AUTOLAND_MIN_ALTITUDE(25)`, tilt `<AUTOLAND_MAX_TILT(30°)`, target within `AUTOLAND_MAX_RANGE(65 m)`
  (`Server_InitiateAutoLand`, `:732-768`). While autoland is active, `ApplyHelicopterPhysics` is skipped
  (`:1322-1323`) — the FSM owns the body. The landing target is picked by a camera raycast
  (`FindLandingTarget` → `DayZPhysics.RaycastRV`, `:717-730`) and shown with an `MH6_landing_zone` marker
  object (`:909-978`).

**`MH6FlightPhase` FSM** (`GROUNDED→LIFTOFF→FLIGHT`, enum `:10-15`; `UpdateFlightPhase`, `:617-661`) gates
a **liftoff-assist blend**: during LIFTOFF below `LIFTOFF_BLEND_HEIGHT=3` m it adds a velocity-authority
lift force toward a desired climb rate + strong horizontal damping (`:1014-1036`), then eases out
(`EaseOutQuad`) into pure force flight — so takeoff is stable, cruise is fully dynamic.

## 6. Inputs, actions, particles, lights

[RECOVERED]
- **Flight inputs** are custom `UAKTHeli*` UA actions, read owner-side in `EOnPostSimulate` via
  `GetUApi().GetInputByName(...).LocalHold()` (`:1431-1450`): `UAKTHeliForward`/`Back` → cyclic pitch,
  `UAKTHeliRight`/`Left` → cyclic roll, `UAKTHeliLeanLeft`/`LeanRight` → pedal/yaw, `UAKTHeliTurbo`/
  `Handbrake` → collective up/down (integrated into `m_ThrottleTarget` at `THROTTLE_INCREMENT_RATE=0.80`).
  Toggles `UAKTHeliAutoHover` / `UAKTHeliAutoLand` via `input.LocalPress` (`:1374-1379`). [UNVERIFIED] the
  `modded_Inputs.xml` bindings (config.bin not recovered; names confirmed from script).
- **Engine start/stop**: MH6 reuses the **vanilla CarScript engine actions** — `ActionStartEngine` /
  `ActionStopEngine` are `modded` only to relabel the prompt to "Start/Stop MH6 Helicopter" when the
  transport `IsKindOf("MH6")` (`MH6_scripts\b_off212633_o856.c:1-41`). No custom start action class — the
  flight loop simply gates on `EngineIsOn()`. `OnEngineStart`/`OnEngineStop` (`:1220-1242`) seed collective
  to throttle, reset the flight phase, and set/clear native damping.
- **Particles**: `modded class ParticleList` registers rocket VFX `ROCKET_TAIL2`/`ROCKET_IMPACT`/
  `ROCKET_TAIL` under `LM_LLAMA/LM_Vehicles/MH6/graphics/` (`b_off152027_o355.c:1-6`) — MH6 is an *armed*
  Little Bird (matches LM_Planes' combat-aviation lineage; the fire pipeline itself was not recovered).
- **Lights**: `MH6FrontLight : CarLightBase` + `MH6RearLight : CarRearLightBase` (`:1626-1667`), standard
  CarScript segregated/aggregated light pattern.
- **Sound**: `OnSound` scales the `CarSoundCtrl.RPM` channel by `m_RotorSpeed` (`:1256-1261`) so engine
  audio tracks rotor spool, not wheel RPM.

## 7. NOT recovered / [UNVERIFIED] — do not fabricate

- **`config.bin`** (the MH6 CfgVehicles entry) was **ofuscated and not recovered** — so the exact
  `CfgVehicles MH6` class, `AnimationSources`, `DamageZones`, `Crew`, memory-point declarations, wheel
  slots, and any config values that would *override* the script constants are all [UNVERIFIED]. The script
  is authoritative for the flight *logic*; the config contract around it is inferred from script reads
  (crew seats 0=Driver/1=CoDriver/2+=passengers via `GetSeatAnimationType`, `:1607-1616`; door state
  `DOORS_MISSING`, `:1567-1570`).
- **`model.cfg` + the `.p3d`** — not recovered. Memory points (`axis_*`, `rotor_main/tail`) and animation
  selections (`rotor_1_1`, `rotor_2_1`, `rotor_1_1_hide`, `rotor_1_1_rotate_hide`, `seat_*`) are confirmed
  as *names* from script, [UNVERIFIED] as actual model data.
- **`modded_Inputs.xml`** — the `UAKTHeli*` input names are confirmed from script; bindings not recovered.
- **`Heli_Core` beyond `StandardAtmosphere`** — the remaining blocks are JAPM shells / byte-fragment junk;
  any additional shared logic is [UNVERIFIED].
- **The combat/fire pipeline** — only the `ParticleList` rocket registrations survived; the projectile /
  RPC / damage code was not recovered.

## Takeaway for building your own force-based heli

MH6 is the buildable **force-based** reference (all flight logic in one legible script). The teachable
skeleton: `MH6 : CarScript` with `MH6OwnerState`/`MH6Move` Pawn replication; per-tick `CachePhysicsState`
→ RPM-authority gates → collective lift force (× ISA density × translational lift × ground effect) along
body-up → cyclic/tail torques → **PD attitude control** (P from memory-point tilt, D from angular rate) →
quadratic per-axis drag → `dBodyApplyForce`+`dBodyApplyTorque`. Layer autohover/autoland as kinematic
`SetVelocity` state machines that *replace* the force call while active. Constants are hard-coded literals
(`:141-176`) — you can lift them as a starting tune. What you must author yourself (not on disk): the
`.p3d`, `model.cfg`, and the `CfgVehicles` config contract (crew/damage/animsources/memory points).

---

# Cross-author generalization — SIB vs RFFS vs MH6 vs LM_Planes

**Four independent flight-model implementations from three independent authors** now sit on disk:
**SIB** (SIBNIC) heli, **RFFS** (RedFalcon) heli, **MH6** (Llama) heli, and **LM_Planes** (Llama +
Itspete-Here) fixed-wing. All four use the **CarScript-as-aviation** hack, which pins that down as **the**
way to do aviation in DayZ today. (Note on authorship: Llama accounts for two of the four — the LM_Planes
fixed-wing *and* the MH6 heli — nailed by the `LM_LLAMA/LM_Vehicles/MH6/` particle paths,
`MH6_scripts\b_off152027_o355.c:3-5`. So it is three authors, four aircraft, two of them force-based and
both Llama's.)

## What is COMMON to all four

- **`CarScript` is the aviation base.** DayZ has no flight class; all four inherit `CarScript`, keep a full
  ground `SimulationModule` (wheels/axles/gearbox) as a taxi fallback, and override the physics in script.
  [VERIFIED-RFFS `Core_config.cpp:517`] · [RECOVERED-SIB `HeliTest_SIB:Heli_sib_cript:CarScript`] ·
  [RECOVERED-MH6 `class MH6 extends CarScript`, `MH6_flightmodel.c:112`] ·
  [LM_Planes `LlamaPlaneScript extends CarScript`].
- **Custom `UA*` inputs** drive flight, read via `GetInputInterface().SyncedValue(...)` / `GetUApi()`
  (SIB `UASIBHeli*`, RFFS `UARFFS*`, MH6 `UAKTHeli*`) or the Pawn move pipeline (LM_Planes), declared in a
  modded `Inputs.xml`.
- **Rotor/prop animation via `SetAnimationPhase`** — a static↔blur mesh swap driven by rotor state, not
  RPM-bound geometry (SIB `rot_h_start`/`rot_h_blur_end`; RFFS `rotorN_speed`/`rotorN_blur_hide`; MH6
  `rotor_1_1`/`rotor_1_1_hide`/`rotor_1_1_rotate_hide`); LM_Planes animates control surfaces the same way.
- **Per-component DamageZones** with cross-transfer coefficients (engine/rotor(s)/fuel/etc.) and
  attachment-tied part health.
- **Server-authoritative physics** gated on `IsServer()` / `IsServerOrOwner()`; state pushed to clients;
  the client re-runs the integrator only for smoothing/interpolation.

## Cross-author synthesis, extended — now FIVE aircraft, FOUR authors

With Expansion added, the corpus is **five flight-model implementations from four independent authors**:
**SIB** (SIBNIC), **RFFS** (RedFalcon), **MH6** + **LM_Planes** (Llama), and **Expansion** (DayZ Expansion
Team). All five use **CarScript-as-aviation** (Expansion's modern path does; its *legacy* `Transport`-based
`ExpansionVehicleBase` is the one exception, and it was superseded). Two orthogonal axes now organise them.

### Monolithic flight loop vs modular aerofoil system

This is a **different axis** from kinematic-vs-force (§"The NEW axis" below) — it is about *how the
per-tick calculation is organised*, not how it is integrated.

- **Monolithic** (SIB, RFFS, MH6, LM_Planes): one large flight method computes the whole aircraft's motion
  inline — `Simulate()`/`FlightSimulation()`/`ApplyHelicopterPhysics()` — with **hard-coded constants**,
  reading orientation/velocity, computing lift/drag/attitude in one pass, and applying **one result at the
  end** (`SetVelocity` or a single `dBodyApplyForce`/`Torque`).
- **Modular** (Expansion): the aircraft is a **bag of auto-configured physics modules** (aerofoils + a
  rotor module + wheels/axles/engines). Each module, in `PreSimulate`/`Simulate`, computes **its own force
  at its own position** and adds it to a shared `ExpansionPhysicsState` accumulator
  (`pState.m_Force += ...`, `pState.m_Torque += (position × force)...`,
  `ExpansionVehicleAerofoil.c:229-230`); the framework commits the sum once via
  `dBodyApplyForce`/`dBodyApplyTorque` (`ExpansionPhysicsState.c:216-217`).

**Advantages of MODULAR:**
- **(a) Data-driven.** A new aircraft is a config block + a thin subclass, not new code — that is exactly
  why one Expansion base flies the Gyrocopter, Merlin, MH-6, etc. (`ExpansionGyrocopter.c:25,256`). The
  monolithic mods each hand-write (or copy-paste) a flight method per model.
- **(b) Moments emerge from geometry.** Torque is `r × F` at the module's real airframe position
  (`ExpansionVehicleAerofoil.c:230`): a tail rudder yaws *because it sits at the tail*. The monolithic
  models fake the lever arm with tuned constants (SIB nudges Euler angles by literals; MH6 multiplies by
  `CYCLIC_PITCH_RATE·80`).
- **(c) Real physics that generalises.** Stall, per-altitude air density (`Expansion_GetDensity`), ground
  effect, ETL, VRS, RBS, autorotation all fall out of one model — where SIB fakes "lift" with a constant
  `+0.25 m/s` and a hard 1500 m ceiling.
- **(d) One core, every vehicle type.** The same module system + accumulator serves car, boat, plane and
  heli; the aerofoil is literally reused by the heli (`ExpansionVehicleHelicopterAerofoil` is an empty
  subclass).
- **(e) Live introspection.** Each module has a `CF_OnDebugUpdate` debug window
  (`ExpansionVehicleAerofoil.c:137-149`) — per-surface AoA/Cl/Cd on screen. Monolithic models debug by
  Print.

**Advantages of MONOLITHIC / costs of modular:**
- **(a) Weight and coupling.** Using the aerofoil means swallowing the whole scaffold — the module base +
  event dispatcher + `ExpansionPhysicsState` + Expansion's `modded CarScript`
  (`CarScript.c` alone is 3815 lines; the rotor module 3234). MH6 is a competent, complete force-based heli
  self-contained in one ~48 KB script. If you want *one* aircraft, the framework is mostly overhead.
- **(b) Debuggability.** A monolithic loop reads top-to-bottom — one method is the whole truth. The modular
  path scatters the physics across N modules × 3 hooks + an accumulator + the CarScript integration; to
  follow one force you trace it from config → `PreSimulate` → `Simulate` → accumulator → apply.
- **(c) Config surface = silent-failure surface.** A wrong memory-point name for an aerofoil's `min`/`max`
  yields a wrong area and a subtly wrong flight model with **no compile error**
  (`ExpansionVehicleAerofoil.c:80-111`) — the price of data-driven. A hard-coded constant can't be
  mis-wired.
- **(d) Realism is less forgiving.** Real Cl/Cd/stall/VRS/RBS make the aircraft twitchy, stallable, and
  spinnable — great for a sim, worse for a pick-up-and-fly server. The kinematic arcade feel (RFFS) is more
  accessible; sometimes that is the *desired* design, not a deficiency.
- **(e) Per-frame cost.** N modules each doing trig + a matrix multiply every tick > one inlined loop.
- **(f) Intuitive tuning.** Turning one `thrust_rate` knob (RFFS's %-of-baseline JSON) is easier than
  reasoning about lift coefficients, blade pitch `theta0`, and advance-ratio thresholds.

**Honest caveat — Expansion does NOT model every blade as an aerofoil.** That would be prohibitively
expensive. The **rotor is its own dedicated module** (`ExpansionVehicleHelicopter`, a rotor-disc /
blade-element-*sampling* model over 8 azimuth sectors, `ExpansionVehicleHelicopter.c:2300-2320`), not a
swarm of per-blade aerofoils. The aerofoil system shines on **fixed wings and control surfaces**; on a heli
it is **rotor-module + body aerofoils**, not aerofoils-all-the-way-down.

### Decision framework — which model to build from (skill default)

The two axes give a clean picking rule. **Default recommendation:**

1. **Custom heli, ship it now, arcade feel, code you can read end-to-end → monolithic.**
   - Predictable kinematic handling → **build from RFFS** (clean, DRM-free, physically-grounded but
     `SetVelocity`; discrete 0-20 collective; typed JSON config; flight HUD).
   - Real momentum/inertia + PD stability + autohover, still one legible script → **build from MH6**
     (force-based `dBodyApplyForce`/`Torque`, ISA density, rotor-RPM authority).
2. **A multi-aircraft vehicle *framework* with realistic, config-tunable physics → Expansion**
   (modular aerofoil + rotor-disc). You pay its architecture and a steeper tuning curve (memory-point
   config, blade-element coefficients) but you get data-driven aircraft, geometry-derived moments, the most
   complete rotor model (VRS/RBS/ETL/autorotation), and one core across car/boat/plane/heli.
3. **Fixed-wing with real aerodynamics → LM_Planes** (monolithic, custom Pawn) **or Expansion** (modular
   aerofoil — this is where the aerofoil system is strongest).
4. **Do NOT build from SIB.** Its simple model is a minimal kinematic hack (fake `+0.25 m/s` lift, hard
   1500 m ceiling) and its advanced/force model is **DRM-locked with the core integrator missing**. Use SIB
   only as a corroborating third data point.

Rule of thumb: **one aircraft, want it flying and hackable → monolithic (RFFS kinematic / MH6 force).
A fleet, want config-tunable real physics → Expansion modular.** The other axis (kinematic vs force) is
now a *sub*-choice inside "monolithic".

---

## The NEW axis that matters most: kinematic vs force-based

The previous 3-way write-up concluded "a buildable DayZ aircraft is kinematic". **MH6 refutes that** — it
is force-based, legible, and buildable. The real split is:

| Implementation | Integration | Source state | So the takeaway is… |
|---|---|---|---|
| **SIB — simple** (SIBNIC) | **Kinematic** — `SetVelocity`/`SetOrientation`, `dBodyApplyImpulse` commented out | Recovered, legible (buildable) | Arcade heli, minimal code — the simplest teachable loop |
| **SIB — advanced** (SIBNIC) | **Force** — `dBodyApplyForce`/`Torque` in the applicator `qmdkldkpqpmlsib` | **DRM-locked + core integrator MISSING** | Proof force was *used*, but unbuildable (lost + license-gated) |
| **RFFS** (RedFalcon) | **Kinematic** — `SetVelocity`/`SetOrientation`, `dBodyApplyImpulse` only as a commented line (`Core.c:272`) | Clean, complete, DRM-free | The clean **kinematic** reference: physically-grounded (attitude-rotated lift vector, ground effect, ETL, governors, drag, weathervaning), discrete 0-20 collective, typed JSON config, flight HUD |
| **MH6** (Llama) | **Force** — real `dBodyApplyForce(this, totalForce)` + `dBodyApplyTorque(this, totalTorque)` every tick (`MH6_flightmodel.c:1165-1166`) | **RECOVERED, clean, complete** | The **force-based** reference: full PD flight controller, ISA air density, rotor-RPM authority, autohover/autoland — buildable today |
| **LM_Planes** (Llama) | **Force** — real aerodynamic lift/drag/stall forces applied at `axis_thruster` | Clean (public workshop) | The fixed-wing reference (real aerodynamics + custom Pawn) |

**Conclusion, corrected:** a buildable-from-source DayZ *helicopter* can be **either** kinematic (RFFS) or
force-based (MH6) — both are clean and complete on disk. The impression the SIB mod gave — that the
force-based model is always license-gated and out of reach — was an artifact of *that one author's DRM*,
not a property of DayZ. MH6 shows real `dBodyApplyForce`/`Torque` rotor physics is fully viable in
plaintext Enforce. (And it is no coincidence the force-based heli is by the same author as the force-based
fixed-wing: LM_Planes already applied real forces; MH6 is that muscle carried onto a rotor.)

## What DIFFERS (all four)

| Axis | RFFS (RedFalcon) | SIB (SIBNIC) | MH6 (Llama) | LM_Planes (Llama) |
|---|---|---|---|---|
| Aircraft type | Helicopter | Helicopter | Helicopter | Fixed-wing (+ 1 amphib car) |
| Integration | **Kinematic** (`SetVelocity`) | **Kinematic** (simple); force (advanced, lost) | **Force** (`dBodyApplyForce`/`Torque`) | **Force** (aerodynamic) |
| Source state | **Clean, complete** | Obfuscated; simple recovered, **advanced DRM-gated + integrator missing** | **Recovered clean & complete** (config.bin missing) | Clean (public workshop) |
| Flight model | High-kinematic: attitude-rotated lift vector, ground effect, ETL, speed+climb governors, aero drag, weathervaning | Low-kinematic: pitch attitude → scalar forward speed; bank → yaw; passive +0.25 m/s hover | **PD controller**: RPM-gated authority, ISA-density lift, translational lift, ground effect, per-axis quadratic drag, overspeed + climb limiters | Real aerodynamics: lift/drag/stall, ISA atmosphere, PID auto-stab, NaN-safe forces |
| Collective / thrust | **Discrete 0-20 detent** × `c_thrust_rate` | `m_rotorTurn` ±2.8 momentary + passive baseline | Analog `m_ThrottleTarget` 0-1 → lift force `= mass·g·1.65 · collective · rotorSpeed² · density · …` | Throttle smoothed via Pawn move |
| Attitude stability | Recovery mode (level-to-velocity) | Attitude auto-recenter | **PD**: proportional (memory-point tilt) + derivative (angular-rate damping) | PID auto-stabilization |
| Autohover / autoland | none | Autohover **yes** (license-gated `AutopilotState` bot-map, DRM only) | **Autohover + autoland FSM** (kinematic `SetVelocity` assist on top of force flight) | n/a |
| Config store | **Typed named JSON** (`MasterConfig` + `HeliConfig`, `get*` accessors, %-of-baseline) | Positional `map<string,float>` from `$profile` JSON | **Hard-coded const literals** (`:141-176`); config.bin not recovered | ~60 `Get*` methods per aircraft (config-as-code) |
| Replication | Sync vars + `EOnFrame` mirror | Sync vars + `EOnSimulate` mirror | **Custom Pawn** (`MH6OwnerState`/`MH6Move`, prediction + rewind) + 2 sync vars for toggles | **Custom Pawn** (`PlaneOwnerState`/`PlaneMove`, prediction + rewind) |
| Atmosphere | none (fixed ceiling clamp) | none (hard 1500 m literal) | **ISA `StandardAtmosphere`** density falloff (shared `Heli_Core` helper) | ISA atmosphere |
| HUD | **Full flight HUD** (airspeed/altimeter/collective/fuel/hydraulics/warning lights) | Config dials only | [UNVERIFIED] (config/model not recovered) | Cockpit dials |
| Openness | Fully open | DRM (HTTP license check to `sibnic.info`) | Recovered clean (JAPM, no live DRM in the flight script) | Open |

## Recommendation — pick by feel, not by "what's possible"

Both are now buildable; the choice is a design decision:

- **Want arcade / minimal code / predictable handling → kinematic. Build from RFFS.** It is clean,
  complete, DRM-free, and physically-grounded while staying kinematic (attitude-rotated lift, ground
  effect, ETL, governors, drag, weathervaning), with a discrete collective, typed JSON config, and a flight
  HUD. `SetVelocity` means no momentum surprises — the heli goes where the model says each tick.
- **Want realism / momentum / inertia / autohover → force-based. Build from MH6.** Real
  `dBodyApplyForce`/`Torque` gives genuine momentum and inertia (the heli carries its velocity, pendulums
  under the rotor, needs anticipation), a full PD stability controller, ISA-density performance falloff,
  rotor-RPM authority (no control until spun up), and hybrid kinematic autohover/autoland on top. More
  physically alive, more to tune.
- Use **SIB** only as a corroborating third data point (it independently confirms CarScript-as-aviation +
  baked-blur rotors + per-component damage, and its config-bitfield sync idea is worth mining) — do **not**
  build from its advanced model; that core is missing and license-locked.
- For **fixed-wing**, **LM_Planes** remains the reference (real aerodynamics + custom Pawn). For
  **rotary-wing**, you now have both a kinematic reference (RFFS) and a force-based one (MH6).

## Player-reported feel (empirical — secondhand, subjective)

Feel feedback relayed by a mod operator running these on a live server (2026-07-07). **NOT measured** —
treat as subjective player impression, not a benchmark. It is the "feel" axis the code cannot show, and
it maps cleanly onto the verified mechanisms above:

| Mod | Player-reported feel | Most likely cause (code-verified) |
|---|---|---|
| **RFFS** | Strongest stabilization; most arcade; **best/easiest handling** | Heaviest assist stack on a kinematic base — speed + climb governors, trainer clamps, `UARFFSRecover` auto-level. Forgiving → easy to fly, but feels "managed"/on-rails. |
| **SIB** | **Most fluid** handling | Continuous collective (`m_rotorTurn`) vs RFFS's *discrete* 0-20 steps; weak ±0.1/tick recenter; direct `SetVelocity`, no governors → smooth and free, nothing fights the stick. Less forgiving. |
| **MH6** | **Lackluster — not fluid AND poor recovery** ("worst of both") | Force-based momentum removes the direct/fluid feel, but its PD stabilizer (`PITCH_STABILITY 0.85`) + FSM autoland are not tuned strong enough for RFFS-grade recovery → the drag of force without the payoff of assistance. |
| **Expansion** | **Complex** for some players | Force-based + real rotor-disk aero (momentum, VRS/RBS, air-density falloff) + least arcade hand-holding → highest skill floor. |

**Design insight (the gap none of the five fill):** *fluidity* and *recoverability* are in tension because
both come from the stabilization system — strong constant stabilization (RFFS) is recoverable but not
fluid; weak stabilization (SIB) is fluid but not recoverable; force-based (MH6), under-tuned, loses
fluidity up front and gains no recovery. **No implementation decouples them.** The open improvement: a
fluid kinematic base (SIB-style continuous, direct response) + an *envelope-protection* stabilizer that
stays soft in normal flight (preserves fluidity) and firms up only near loss-of-control (provides
recovery) — fly-by-wire "normal law" instead of always-on correction. That is the one thing that would
feel better than all five, and it is a tuning problem, not new physics. Also confirmed from feel: strong
stabilization is NOT strictly "better" — RFFS wins controllability for the average player but that same
assist is what costs it the fluidity players praise in SIB. Pick by target audience, not by "strongest".

---

# DayZ-Expansion — modular aerofoil physics framework [clean, open-source]

[VERIFIED-EXP] Source: **DayZ-Expansion** vehicle framework (the professional multi-vehicle mod;
`© DayZ Expansion Mod Team`, CC BY-NC-ND). Non-obfuscated — every claim below is read straight from the
research copies in `<research-notes>\expansion-vehicles-heli\`. Citations are
`path:line` into those copies (`ExpansionVehicleHelicopter.c` = the rotor module; `CarScript.c` =
Expansion's `modded class CarScript`; `ExpansionHelicopterScript.c` = the heli entity; the rest by
filename). **This is the fifth aircraft implementation and the first that is a general vehicle-physics
*framework* rather than one bespoke flight loop.**

Where SIB/RFFS/MH6 are each a single hand-written flight method bolted onto one heli, Expansion is a
**data-driven module system**: the airframe is composed of auto-configured physics objects (wheels,
axles, engines, gearboxes, **aerofoils**, and — for helis — a **rotor module**), each of which computes
its own force at its own position every tick and adds it to a shared accumulator that is committed once
via `dBodyApplyForce`/`dBodyApplyTorque`. One core serves cars, boats, planes and helicopters.

## 1. Architecture — entity `: CarScript` + module system + physics-state accumulator

[VERIFIED-EXP] Same **CarScript-as-aviation** hack as the other four, but organised as a framework:

| Layer | Role | Cite |
|---|---|---|
| `modded class CarScript` (Expansion's) | hosts the module system: `m_Modules`/`m_Aerofoils`/`m_Wheels`/`m_Axles`/`m_Engines`/`m_Gearboxes` arrays, the `m_State` (`ExpansionPhysicsState`) accumulator, the `m_Event_*` dispatchers, and `EOnSimulate` which drives the whole per-tick pipeline | `CarScript.c:19,28`, `EOnSimulate` `:2282-2447` |
| `ExpansionHelicopterScript : CarScript` | the heli **entity**: owns an `ExpansionVehicleHelicopter m_Simulation` (the rotor module), heli tunables, autohover/landing state, warning sounds, wreck class | `ExpansionHelicopterScript.c:17-19` |
| `ExpansionVehicleHelicopter : ExpansionVehicleModule` | the **rotor module** itself — collective/cyclic/anti-torque → rotor thrust + torque; a *special module*, NOT one-aerofoil-per-blade | `ExpansionVehicleHelicopter.c:223` |
| `ExpansionGyrocopter : ExpansionHelicopterScript`, `ExpansionBigGyrocopter : ExpansionGyrocopter` | concrete inherited aircraft — pure config/subclass on the shared base | `ExpansionGyrocopter.c:25,256` |

[VERIFIED-EXP] **Pawn replication** (client-prediction + server reconciliation, same family as MH6 and
LM_Planes): `ExpansionHelicopterScriptMove : CarScriptMove` + `ExpansionHelicopterScriptOwnerState :
CarScriptOwnerState` carry the flight state (`m_RotorSpeed`, `m_Collective`, `m_AntiTorque`,
`m_CyclicForward`, `m_CyclicSide` + their targets; `ExpansionVehicleHelicopter.c:3-110`).

### 1a. The per-tick pipeline (`CarScript.c EOnSimulate`, `:2282-2447`)

[VERIFIED-EXP] Server-authoritative / physics-host-gated (`m_IsPhysicsHost = IsOwner()` on client,
always true on server, `:2300-2344`). When active and simulating (`:2403-2418`):

```
m_State.SetupSimulation(dt);        // snapshot transform, mass, world+model-space velocities, zero m_Force/m_Torque
m_State.CalculateAltitudeLimiter(); // altitude-based lift falloff (soft ceiling)
m_Event_PreSimulate.PreSimulate(m_State);  // every module computes its coefficients
OnSimulation(m_State);                     // per-entity hook (heli overrides -> runs rotor module)
m_Event_Simulate.Simulate(m_State);        // every module adds its force+torque to the accumulator
...
m_State.ApplySimulation_CarScript(dt, ...) // -> ApplySimulation -> dBodyApplyForce/Torque
```

The module dispatchers are **singly-linked-list walkers** (`ExpansionVehicleModuleEvent`, whole file):
`PreSimulate`/`Simulate`/`Control`/`PostSimulate`/`Animate` each iterate the chain and call the matching
hook on every module (`ExpansionVehicleModuleEvent.c:83-125`). Base module lifecycle (all no-op
overridables) is `ExpansionVehicleModule` (`ExpansionVehicleModule.c:94-112`) — plus Pawn hooks
`ObtainMove`/`ConsumeMove`/`ReplayMove`/`ObtainState`/`RewindState` (`:70-89`).

### 1b. The accumulator — `ExpansionPhysicsState`

[VERIFIED-EXP] This is the shared force/torque sink every module writes into:
- `SetupSimulation(pDt)` (`ExpansionPhysicsState.c:178-207`): caches `m_Transform`, `m_Mass =
  dBodyGetMass`, world **and** model-space linear/angular velocity + acceleration; **zeroes `m_Force` and
  `m_Torque`** (`:188-189`).
- `GetModelVelocityAt(relPos)` (`:473-475`) = `m_LinearVelocityMS + m_AngularVelocityMS * relPos` — the
  local airflow at any module's position (this is what the aerofoil reads).
- `ApplySimulation(pDt)` (`:209-217`) commits the whole tick in one place:
  `dBodyApplyForce(m_Entity, m_Force); dBodyApplyTorque(m_Entity, m_Torque);` (`:216-217`).

**So the entire fleet is force-based** — unlike RFFS's kinematic `SetVelocity`, Expansion always goes
through `dBody*` forces, like MH6. The `dBodyApplyForce` at `CarScript.c:883` is unrelated — it is the
explosion pop when a vehicle is destroyed, not the flight applicator.

## 2. The aerofoil module — real aerodynamics, config-driven, geometry-placed

[VERIFIED-EXP] `ExpansionVehicleAerofoil : ExpansionVehicleModule` (`ExpansionVehicleAerofoil.c:17`) is
the base of the whole aerodynamic system — a self-contained lifting surface. This is what makes the
framework *data-driven*: an aerofoil auto-configures itself from config and needs no code.

**Config-driven construction** (ctor `:50-135`): reads
`CfgVehicles <veh> SimulationModule Aerofoils <name>`:
- `type` — Fixed/Wing/Rudder/Elevator, string-or-int (`:59-73`).
- `up` — the surface's up-vector, `ConfigGetTextOut(...).ToVector()` (`:77-78`).
- `min`/`max` — **memory-point names**; area is derived from the world extent between them (projected
  perpendicular to `up`), `m_Position = midpoint` (`:80-111`). **The surface's size and location come
  from the model's memory points**, not from magic numbers.
- `camber`, `maxControlAngle`, `stallAngle`, optional `animation` (`:113-124`).

**Aerodynamics in `PreSimulate`** (`:152-203`):
- Local airflow = `-pState.GetModelVelocityAt(m_Position)`, normalized; `m_AirflowMagnitudeSq = v²`
  (`:154-156`).
- Control input mapped by type: Rudder←`-m_Controller.m_Yaw`, Elevator←`m_Controller.m_Pitch`,
  Wing←±`m_Controller.m_Roll` (sign by which side, `m_Position[0]<0`), so **one aerofoil class becomes an
  aileron/elevator/rudder purely by config `type`** (`:158-178`).
- Angle of attack `= Asin(dot(m_Up, airflowNormal)) · RAD2DEG` (`:183`).
- Dynamic pressure `m_PressureCoef = area · 0.5 · Expansion_GetDensity(altitude) · v²` (`:187`) — real
  air-density falloff by altitude (`Expansion_GetDensity` is external to this copy, [UNVERIFIED] body but
  named/called here).
- Lift coefficient with stall: `sin(liftAngle · π/2 / stallAngle) · 2`, forced to 0 once
  `|liftAngle| > 2·stallAngle` — a real stall curve (`:191-193`).
- Drag coefficient parabolic: `0.05 + ((dragAngle+angle)/(stallAngle+|angle|))²` (`:195-202`).

**Force + torque in `Simulate`** (`:205-231`) — the crux of the modular idea:
```
force  = (m_Up · q · Cl) + (airflowNormal · q · Cd)      // lift along up, drag along airflow
force *= m_DeltaTime
pState.m_Force  += force.Multiply3(pState.m_Transform)            // local force -> world, accumulate
pState.m_Torque += (position * force).Multiply3(pState.m_Transform)  // r x F -> world torque, accumulate
```
[VERIFIED-EXP] **The pitching/rolling/yawing moment falls out of the geometry**: torque is `position ×
force` where `position` is the module's own location on the airframe (`:230`). A rudder placed at the
tail produces yaw *because it is at the tail* — no hand-tuned lever-arm constant. `Animate`
(`:233-236`) drives the control-surface animation phase off `m_Input`. `ExpansionVehicleHelicopterAerofoil
: ExpansionVehicleAerofoil` (`ExpansionVehicleHelicopterAerofoil.c:1-5`) is an **empty stub** — helis
reuse the fixed-wing aerofoil unchanged for any body lifting surfaces.

## 3. The rotor module — collective / cyclic / anti-torque / autorotation

[VERIFIED-EXP] The rotor is **its own module** (`ExpansionVehicleHelicopter : ExpansionVehicleModule`,
`ExpansionVehicleHelicopter.c:223`), NOT an aerofoil-per-blade (that would be far too expensive). It is a
large, physically-sophisticated model — 3234 lines total; the parts below are read directly, the
remainder is [UNVERIFIED] (see §6). Confirmed structure:

- **Two simulation modes** (`m_SimulationMode`, default `RotorDisk`): `Simulate_RotorDisk` (the A3
  RotorLib-style blade-element model, `:2237+`) and a `DIAG_DEVELOPER`-only `Simulate_Legacy`
  (`:1746+`), dispatched at `:1722-1735`, then a shared `Simulate_Common` (`:1819+`). It applies forces
  the framework way: `pState.m_Force += force; pState.m_Torque += torque;` at the end of `Simulate`
  (`:1742-1743`).
- **Control channels** (`:66-72,301-333`): `m_Collective`, `m_AntiTorque`, `m_CyclicForward`,
  `m_CyclicSide`, each with a `*Target` (from `m_Controller`), rate limits, trims, and hydraulic-fluid
  authority (`CarFluid.OIL` = hydraulics, `:1693`). Collective/cyclic response is **gated by
  `m_RotorSpeed`** (`m_CollectiveDelta = (target-current)·m_RotorSpeed²`, `:1676`; cyclic only moves if
  `m_RotorSpeed != 0`, `:1705-1711`) — no control authority without RPM, like MH6.
- **Rotor thrust (RotorDisk model, `:2237-2320+`)**: real momentum-theory hover induced velocity
  `viHover = sqrt(mass·g / (2·ρ·π·r²))` (`:2265-2267`), advance ratio `mu = horiSpeed/omegaR`
  (`:2246-2250`), **8-azimuth-sector blade-element sampling** (`:2300-2320`), effective translational
  lift by iterating induced velocity (`:2275-2280`), **ground effect** (`:2252-2263`), **Vortex Ring
  State** thrust loss (`ComputeVRSSeverity`, `:2287-2292`), **Retreating Blade Stall** above `mu=0.35`
  (`:2313-2318`), atmosphere via `pState.m_AltitudeLimiter` (`:2305`). Thrust is applied up the body axis;
  cyclic tilts the disc so lift redirects into translation. (Legacy model is coarser: thrust `∝ collective
  · rotorSpeed² · liftForceCoef · mass · liftFactor`, `:1806-1815`.)
- **Anti-torque / tail rotor** (`Simulate_Common`, `:1932-1960`): tail-rotor force `= m_AntiTorque ·
  m_TailForceCoef · m_RotorSpeed²`, minus the **main-rotor reaction torque** it must cancel
  (`m_MainRotorTorque · m_RotorSpeed² · torqueSpeedFactor`, `:1957-1959`). **Explicitly handles
  tandem/coaxial rotors**: if `m_TranslatingTendencyCoef == 0` (no tail rotor) the main-rotor torque
  cancellation is skipped (`:1947-1949`). Tail-rotor damage injects malfunction torque (`:1934-1944`) —
  the classic loss-of-tail-rotor spin.
- **Autorotation** (`:1662-1667`): if the heli is descending and the rotor is off
  (`goingDown > 0 && m_RotorSpeedTarget < 0.1`), `m_RotorSpeed` is driven *up* from the falling airflow
  (`change = (min(goingDown,1) - m_RotorSpeed)·0.08·pDt`) — the descending air spins the freewheeling
  rotor, exactly the real autorotation energy source (comment cites the Wikipedia autorotation diagram,
  `:1662`).
- **Translating tendency** (`Simulate_Common`, `:1823-1830`): the lateral hover drift a real tail rotor
  induces (pushes right for a CCW main rotor), full at hover, gone by ETL.

**This is the most physically-complete rotary model of the five** — more so than MH6's PD controller,
because it models the rotor *disc* (induced velocity, blade elements, VRS, RBS, ETL, ground effect,
autorotation) rather than a lumped lift force. The trade-off is size and coupling (§synthesis).

## 4. The legacy era — `ExpansionVehicleBase : ExpansionVehicleBaseBase : Transport` (its own physics)

[VERIFIED-EXP] Before Expansion re-based its vehicles on `CarScript`, it had a **parallel physics stack
that inherited `Transport` directly**, bypassing CarScript entirely:
`ExpansionVehicleBase : ExpansionVehicleBaseBase` (`ExpansionVehicleBase.c:13`) and
`ExpansionVehicleBaseBase : Transport` (`ExpansionVehicleBase_Towing.c:1`). It carries its **own**
`m_Controller`, `m_State` (`ExpansionPhysicsStateT<ExpansionVehicleBase>`) and `m_ExpansionVehicle`
(`ExpansionVehicleBase.c:19-28`) — the same module/accumulator idea, but on a `Transport` base rather
than reusing DayZ's `CarScript` crew/fuel/damage contract. The module system (`ExpansionVehicleModule`
ctor, `ExpansionVehicleModule.c:36-42`) still binds to *either* base: it casts the vehicle to
`ExpansionVehicleBase` **or** `CarScript` to find the controller. **The modern path is the `CarScript`
one** (`ExpansionHelicopterScript : CarScript`); the `Transport`-based `ExpansionVehicleBase` is the
legacy era, kept for towing/compatibility.

## 5. Clean inheritance — one base, many aircraft

[VERIFIED-EXP] Concrete aircraft are thin subclasses of `ExpansionHelicopterScript` carrying almost only
config: `ExpansionGyrocopter : ExpansionHelicopterScript` and `ExpansionBigGyrocopter : ExpansionGyrocopter`
(`ExpansionGyrocopter.c:25,256`) are the two present in the research copy. Expansion ships more helis on
the same base (the Merlin and an MH-6 are referenced in comments — big-heli ground-clip handling
`ExpansionVehicleHelicopter.c:2433`, rocket-damage thresholds `ExpansionHelicopterScript.c:450`), and the
`REFERENCE_MASS = 1700 //! MH6` tuning anchor (`ExpansionVehicleHelicopter.c:228`) confirms the framework
is authored against an MH-6-class reference and scaled per-heli by mass/bounding-radius. **This is the
payoff of the modular design: a new aircraft is a config + a subclass, not a new flight loop.** [UNVERIFIED]
the concrete `CfgVehicles` classes of Merlin/UH1H/HatchBird — not in the research copy.

## 6. NOT read / [UNVERIFIED] — do not fabricate

- **`ExpansionVehicleHelicopter.c` in full** — 3234 lines. The architecture, control-channel integration
  (`:1655-1743`), autorotation (`:1662-1667`), rotor-disk thrust core (`:2237-2320`), anti-torque/tail
  (`:1900-1960`), and legacy thrust (`:1800-1816`) were read directly. The **remaining bulk** — the full
  blade-element azimuth loop body past `:2320`, the complete `Simulate_Common` torque assembly, autohover
  (`UpdateAutoHover`-family around `:1440-1600`), auto-trim, RBS/VRS coefficient derivations, the collision
  `ExpansionHelicopterScriptRotor` callback (`:117`), and networking — are **[UNVERIFIED]** (not read line
  by line).
- **`Expansion_GetDensity(altitude)`** — called by the aerofoil (`ExpansionVehicleAerofoil.c:187`) and the
  ISA/altitude atmosphere generally; its definition is outside these copies. [UNVERIFIED] body.
- **`config.cpp` / `SimulationModule` blocks** — the `Aerofoils`/rotor/wheel config the modules read
  (`CfgVehicles <veh> SimulationModule ...`) is [UNVERIFIED] as on-disk config; confirmed only as the
  config *paths* the script reads.
- **`.p3d` + `model.cfg`** — memory points (aerofoil `min`/`max`, rotor selections) confirmed as *names*
  the script reads; [UNVERIFIED] as actual model data.
- **Concrete non-Gyrocopter aircraft classes** (Merlin/MH-6/UH1H) — referenced, not in the copy.

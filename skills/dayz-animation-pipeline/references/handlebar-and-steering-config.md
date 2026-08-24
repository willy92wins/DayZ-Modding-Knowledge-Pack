# Handlebar and steering-wheel rotation (Layer 1, pure config)

Pure Layer 1 pattern for any vehicle part that rotates with the steering input: a motorcycle/quad handlebar, a car steering wheel, the rudder of a boat. Driven by the engine's `steeringwheel` controller (NO `drivingWheel`: ese es el nombre de CLASE de la animacion) — no script, no SEAnim, no Workbench.

This is the cosmetic half of the steering loop. If the rider's hands also track the grips via IK, also read `references/vehicle-rider-ik-pose.md` and respect the shared-angle contract (LL-handlebar-rotation-sync).

## Files touched

- The vehicle's `model.cfg` — declare the bone in `CfgSkeletons` and add a `class Animations` entry in `CfgModels`.
- The vehicle's `.p3d` — add the named selection that gets rotated, plus the axis (two memory points).

That is it. No `config.cpp` `AnimationSources` entry is needed because `steeringwheel` is an engine-provided source (requiere skeleton de direccion estandar; ver correcciones abajo).

## Skeleton declaration

In `model.cfg`:

```cpp
class CfgSkeletons {
    class MyVehicle_Skeleton {
        isDiscrete = 0;                    // smooth interpolation; a switch this is not
        skeletonInherit = "";
        skeletonBones[] = {
            "handlebar", "",               // or "steering_wheel", ""
            // ... other bones (wheels, doors, ...)
        };
    };
};
```

Parent is empty (root) — the steering geometry rotates relative to the vehicle body, no inheritance chain needed.

## Animation block

```cpp
class CfgModels {
    class MyVehicle {
        skeletonName = "MyVehicle_Skeleton";
        sectionsInherit = "";
        sections[] = { /* hidden selections if any */ };
        class Animations {
            class handlebar {
                type      = "rotation";
                source    = "steeringwheel";  // engine source -1..+1. NO "drivingWheel" (eso es nombre de CLASE). EXIGE skeleton de direccion ESTANDAR (wheel_X_X_damper->wheel_X_X_steering->wheel_X_X) o el engine NO lo alimenta.
                selection = "handlebar";      // named selection in .p3d (puede ser "drivewheel", etc.)
                axis      = "handlebar_axis"; // memory axis: two points
                memory    = 1;                // axis lives in Memory LOD
                minValue  = -1;
                maxValue  =  1;
                angle0    = "rad -30";        // escala GRADOS (~25-35), NO 0.39 (throw invisible). Afinar in-game.
                angle1    = "rad  30";
            };
        };
    };
};
```

Key properties:

- `source = "steeringwheel"` — engine drives this from -1 (full left) to +1 (full right). **NO `drivingWheel`** (es el nombre de CLASE de la animacion, no el source). No `AnimationSources` entry required; pero EXIGE el skeleton de direccion estandar (ver correccion 2026-06-06 abajo). `wheel` (looping wheel rotation) and `damper_*` (suspension travel) work the same way for related parts.
- `selection = "handlebar"` — the named selection in the `.p3d` that holds the geometry to rotate (the entire handlebar assembly, all grips, levers, mirrors).
- `axis = "handlebar_axis"` — a named selection that the engine reads as **the line between two memory points** (`<axis>_begin` and `<axis>_end`). Those two points must exist in the Memory LOD.
- `memory = 1` — tells the engine the axis is in the Memory LOD. The default is `1`; include it explicitly so a reader knows where to look.
- `angle0` / `angle1` — angle at `source = minValue` / `maxValue`. **Escala empirica: el numero se comporta como GRADOS para el throw visible** (`rad 0.39` -> casi invisible; `rad 30` -> ~30 grados). Usar ~25-35 y afinar in-game; NO escala de radianes decimal (ver correccion 2026-06-07 abajo).

## Axis geometry — the two memory points

`handlebar_axis_begin` and `handlebar_axis_end` are two memory points in the `.p3d`. The line between them is the rotation axis (right-hand rule from begin to end). Place them so the axis matches the physical steering stem of the bike or the steering column of the car.

LFQuad reference values (Yamaha Banshee, `LFQuad_dev/handoff_2026-05-28.md`):

```
handlebar_axis_begin = (0, 0.748, -0.298)
handlebar_axis_end   = (0, 1.139, -0.384)
```

Direction `end - begin = (0, +0.391, -0.086)` → normalized roughly `(0, +0.977, -0.214)`. The axis tilts slightly backward, matching a quad's stem. Symmetric (`x=0`) keeps the steering centered.

Tooling: add the two memory points and the named selection with `dayz-p3d-inspector` (extract → Recipe JSON → edit memory points + add selection → rebuild) or `dayz-model-pipeline` (py3d). Don't send the user to Object Builder for this.

## Source choices for related parts

| Source | What it represents | Range | Typical use |
|---|---|---|---|
| `steeringwheel` | steering input | -1 .. +1 | handlebar, steering wheel, rudder (NO `drivingWheel`: es nombre de clase) |
| `wheel` | wheel rotation (looped) | 0 .. 1 looping | wheel spin (`sourceAddress = "loop"`) |
| `damper_<corner>` | suspension travel | 0 .. 1 | shock absorbers per wheel |
| `direction` | yaw of vehicle | 0 .. 1 | compass needles |
| `speed` | scaled velocity | 0 .. 1 | speedometers (use `min/maxValue` to scale) |

For wheels, you almost always want `type = "rotationY"` (or X/Z depending on your wheel axis convention) with `sourceAddress = "loop"` so it spins continuously instead of snapping back at phase 1.

## Cross-contract with rider IK — LL-handlebar-rotation-sync

When the rider's hands track the grips via `vehicle-rider-ik-pose.md`, the angular range of the steering rotation **MUST be equal** to the solver's `steerMax`:

```
model.cfg:   angle0 = "rad -30"; angle1 = "rad 30";   // escala grados (ver correccion 2026-06-07)
solver:      T.steerMax = <angulo real que produce angle1, MISMA escala>
```

If they drift, at full lock the engine rotates the geometry to `±angle1` while the solver only rotated the hands to `±T.steerMax`, leaving a gap between the hands and the grips. Visible immediately in-game.

Make this a single constant in your project (a `#define` in a shared header, or a documented entry in `verified-apis.md` / `assumptions.md`) so a later edit to one side cascades to the other. R7 (propagate invariants to every call-site) applied to physics-cosmetic coupling.

## Validation

Offline:

- Confirm the bone exists in `skeletonBones[]` and matches the `selection` string 

## Multiplayer source discipline (LL-103)

**`GetSteering()` is client-only -- the dedicated server returns 0.** A cosmetic steering-wheel/handlebar animation driven by a script-set `source="user"` from the CLIENT gets overwritten by server sync and snaps back to 0 in MP. For any visual coupled to steering, use the engine-native `source="steeringwheel"` channel (already synchronized; the `DrivingWheel` class); reserve `source="user"` for what the engine does not drive (dampers, doors). (LFQuad LL-103.)

# Config-driven animation (Layer 1)

The text-based animation system: `model.cfg` + `config.cpp` + script. This is the part Claude produces fully in-sandbox. No RTM, no `.anm`, no Workbench — just config and Enforce Script driving named selections in the `.p3d`.

Primary source for the [VERIFIED] items below: PMC Editing Wiki mirror of BI's model.cfg page (`pmc.editing.wiki/doku.php?id=arma:modeling:model_config`, read in full 2026-05-20) plus working mods in this vault. Items marked [TBD-verify] were reported by a single secondary source — confirm against the user's vanilla `P:\` config before relying on them.

## Mental model

A controller (the `source`) outputs a value. An `Animations` entry maps that value to a phase (0..1) and applies a transform (rotate/translate/hide) to a named `selection` in the model, optionally around an `axis`. For script-driven motion the source is `"user"` and you set the phase yourself with `SetAnimationPhase`.

Three files, names must match exactly across all three:
- `model.cfg` — skeleton (bones) + the `class Animations` transforms.
- `config.cpp` — `class AnimationSources` (only for `user` / custom sources).
- script `.c` — `SetAnimationPhase("<animClassName>", phase)`.

## Animation types — `class Animations` member `type` [VERIFIED unless noted]

| type | effect |
|---|---|
| `rotation` | rotate around an arbitrary axis (defined by axis selection or begin/end points) |
| `rotationX` / `rotationY` / `rotationZ` | rotate locked to model X/Y/Z axis |
| `translation` | linear motion along an axis |
| `translationX` / `translationY` / `translationZ` | translation locked to X/Y/Z |
| `hide` | hide/show the selection at a phase threshold | [VERIFIED against working mod kt_roadkill_scum `config_main.cpp:862-885`; uses `hideValue`. Confirm against a vanilla door/container config for the exact threshold semantics — not in the PMC wiki type table.] |
| `translationModelX/Y/Z`, `direct` | [TBD-verify: referenced in some community contexts, not confirmed in any primary source. Do not emit unless verified against vanilla.] |

## Properties of an `Animations` entry [VERIFIED]

- `source` — which controller drives it (engine source name, or a name you defined in `AnimationSources`).
- `selection` — the named selection (bone) in the `.p3d` that moves. Must be listed in the skeleton's `skeletonBones[]`.
- `axis` — named selection (two memory points) defining the rotation/translation axis.
- `begin` / `end` — alternative to `axis`: two named points giving an oriented axis.
- `memory` — bool, default `true`; whether the axis lives in the Memory LOD.

> The `.p3d` side here — adding the `selection` you animate, or the two memory points that define the `axis`/`begin`+`end` — is sandbox work, not Object Builder-only. Use `dayz-p3d-inspector` (extract → Recipe → edit points/selections → rebuild) or `dayz-model-pipeline` (py3d), `dayz-p3d-debinarizer` first if the `.p3d` is binarized, `dayz-p3d-audit` to verify. Don't tell the user to open Object Builder for a memory point or a selection — offer to do it.
- `minValue` / `maxValue` — controller input range mapped to phase 0 and phase 1.
- `minPhase` / `maxPhase` — inverse mapping (phase at controller min/max).
- `sourceAddress` — `"clamp"` (default), `"loop"`, or `"mirror"` — what happens past the range.
- `animPeriod` — seconds for one cycle; used by custom (`user`) sources, not engine sources.
- `angle0` / `angle1` — start/end angle in radians (rotation types).
- `offset0` / `offset1` — start/end offset (translation types).
- `hideValue` — phase threshold at/under which the selection is hidden (`hide` type). [VERIFIED via working mod; confirm exact comparison direction against vanilla.]

## `class AnimationSources` (in `config.cpp`, under your CfgVehicles class) [VERIFIED]

Defines/overrides controllers. Needed only for `user` and custom sources — engine sources work without it.

```cpp
class AnimationSources
{
    class Door1
    {
        source = "user";   // script-controlled phase
        animPeriod = 1;    // seconds for a full 0->1 transition
        initPhase = 0;     // phase at spawn
    };
};
```

- `source = "user"` — script controls the phase via `SetAnimationPhase`.
- `animPeriod` — transition speed in seconds (engine interpolates between phases).
- `initPhase` — starting phase at spawn. [TBD-verify: the 0=closed/1=open convention is per-object, decided by your `angle0/angle1` or `hideValue`, not a global rule. In kt_roadkill, hide uses `initPhase=1` to start hidden. Verify your own mapping.]
- The class name (`Door1`) MUST equal the `source` string in the matching `class Animations` entry, and is the name you pass to `SetAnimationPhase`.

## Engine-provided `source` values [VERIFIED list from PMC wiki]

These need no `AnimationSources` entry — the engine drives them:

`wheel`, `drivingWheel`, `speed`, `fuel`, `rpm`, `direction`, `time`, `clockHour`, `clockMinute`, `clockSecond`, `gear`, `altBaro`, `altRadar`, `horizonBank`, `horizonDive`, `vertSpeed`, `aileron`, `aileronB`, `aileronT`, `aoa`, `elevator`, `flap`, `rotor`, `rudder`, `speedBrake`, `damper`, `mainGun`, `mainTurret`, `rotorH`, `rotorV`, `rotorHDive`, `rotorVDive`, `hatchCommander`, `hatchDriver`, `hatchGunner`, `obsGun`, `obsTurret`, `turretDir`, `wheelL`, `wheelR`, `reload`, `revolving`, `compassArrow`, `compassCover`, `compassPointer`, `pedals`, `support`, `gmeter`.

For DayZ static props/containers most are irrelevant. The practical ones: `user` (script), `wheel`/`drivingWheel`/`damper` (vehicles), `reload`/`revolving` (weapons). [TBD-verify: DayZ-specific sources like `doors`, `damage` are cited in community guides but not in the PMC wiki list — confirm against a vanilla DayZ config (e.g. a vanilla car or `Land_*` door) before using.]

## Skeleton declaration — `CfgSkeletons` in `model.cfg` [VERIFIED]

```cpp
class CfgSkeletons
{
    class MySkeleton : ParentSkeleton
    {
        skeletonInherit = "ParentSkeleton";   // "" if none
        skeletonBones[] =
        {
            "bone1", "",        // bone1 has no parent
            "bone2", "bone1"    // bone2 is a child of bone1
        };
    };
};
```

Bones listed here must match the named selections in the `.p3d` used as `selection` in `class Animations`. `CfgModels` references the skeleton with `skeletonName = "MySkeleton"` and contains the `class Animations` block.

```cpp
class CfgModels
{
    class MyModel   // MUST match the .p3d filename (MyModel.p3d)
    {
        skeletonName = "MySkeleton";
        sectionsInherit = "";
        sections[] = {};
        class Animations
        {
            class Door1 { type="rotation"; source="Door1"; selection="door"; axis="door_axis"; minValue=0; maxValue=1; angle0=0; angle1="rad 90"; };
        };
    };
}
```

## Script interface [VERIFIED via community samples; signature TBD-verify line-read]

- `SetAnimationPhase(string animName, float phase)` — set the phase (0..1). `animName` is the `class Animations` entry name.
- `GetAnimationPhase(string animName)` — read current phase.
- For `user` sources the engine interpolates over `animPeriod` toward the phase you set.
- Side discipline: drive state on the side that owns it (server for authoritative state) and let it replicate; for a purely cosmetic local toggle, client is fine. See `enforce-script-reference` for the IsDedicatedServer guards and the EEItemAttached/Detached lifecycle (used by hide-on-attach in `item-ik-and-hide.md`).

[TBD-verify: exact method signatures against `object.c` in the user's script module or DayZ Explorer — the source page was too large to line-read. Confirm before shipping if the p
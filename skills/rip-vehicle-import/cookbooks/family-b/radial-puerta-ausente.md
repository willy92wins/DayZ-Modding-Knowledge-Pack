# Cookbook B — radial de puerta ausente

> Familia B. Este cuerpo se movió sin reescritura en CAMBIO-1; las notas de estado y las rutas permanecen tal como estaban en el origen.

<!-- MOVED-EXACT source="dayz-vehicles/SKILL.md:191" sha256="3E3511B1F6C0480BFDA27046E54A28287A946D315A03F84DED4FF709B31672E8" -->
## DOOR MECHANISM SELECTOR — decide this BEFORE modelling or scripting anything (added 2026-07-27)

DayZ has **three unrelated door mechanisms**. Picking the wrong one costs a full modelling +
config cycle, and they share vocabulary (`source`, `component`, `axis`), so the mistake is not
obvious from the symptom. Doors have now been re-solved from scratch on three projects
(MercedesAMGLF, SUB_BRZ, LFHeli) — pick from this table first.

| You are building | Mechanism | Where the contract lives |
|---|---|---|
| Door/hatch/lid on a **building or static prop** | `class Doors` under `HouseNoDestruct`; animation `source` maps to a Doors `component` | skill **`dayz-doors`** |
| Door on a **vanilla-style car**, as a detachable part | Attachment: `CarDoor` item + `ActionCarDoorsOutside`; the action target is resolved by **raycast against the ITEM's ViewGeometry** | invariants **#21 and #22** below |
| Door that must **stay part of the shell** (no detach, custom radial) | Own actions driving `GetNearestDoorIndex` / `IsDoorOpen` (fail-closed) / `SetDoorOpen`, with the motion in `model.cfg` AnimationSources | LFHeli OH-1 contract v5 |

**`dayz-doors` does NOT cover vehicle doors.** Its scope is buildings and static props. The name
attracts anyone with a door problem; if the door belongs to a car or a helicopter, that skill is
the wrong contract and its `class Doors` pattern will not produce a working radial.

Two traps specific to the vehicle paths:

- **Attachment path**: the radial silently never appears if the item's ViewGeometry points carry
  `flags 0x0` instead of `0x02000000` — config, script overrides, slots, bones and anim sources
  all correct, action still filtered. Census the item's VG point flags against a working control
  BEFORE touching config. Full contract in #22.
- **Scripted path**: enumeration probes must be READ-ONLY. A diagnostic probe that calls
  `SetAnimationPhase` to "look at" a door corrupts live state — the door closes visually while the
  logical state stays open, and the next diagnosis is chasing a bug the probe created.

Status honesty: #21 and #22 are measured offline and their in-game gate was still pending as of
2026-07-18; the OH-1 scripted contract v5 is implemented with its cycle gate pending. Treat all
three as verified-offline, and confirm in-game on first use.

<!-- END MOVED-EXACT -->

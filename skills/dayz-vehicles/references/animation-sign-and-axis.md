# El SIGNO de una animacion no se juzga sin su EJE

Extraido de `SKILL.md` (corte 3, 2026-08-15). Aqui vive el DETALLE; el enunciado
corto y cuando leer esto estan en el indice `## ARCHIVO DE LECCIONES` del SKILL.md.
Nada de este fichero esta derogado: son lecciones vigentes, ordenadas por tema en
vez de por fecha.

---

## (added 2026-07-28) An animation's SIGN is never judged without its AXIS - use the pseudovector against the control

Wheels spinning backwards, doors hinging the wrong way and inverted steering are the same bug,
and reviewing `angle1` alone cannot catch any of them, because **the axis sign is a free
reparametrization**: `R(theta, a) == R(-theta, -a)`, so a mod with axis `(-1,0,0)` and
`angle1 = +6.28` moves *identically* to the control's `(1,0,0)` / `-6.28`. Compare the raw
angle against a control and you will flag a correct artifact and miss a real one. The
falsifiable invariant is the pseudovector `angle1 x unit(axis_dir)`, compared against the
homologous class of the vanilla CONTROL.

**Where the evidence lives after Binarize** (so this is an OFFLINE gate, not an in-game guess):
the compiled ODOL carries the whole rig. `odol_reader.py:82-160` - `animations.classes[i]` has
`anim_name`, `anim_source`, `anim_type` (0=rotation, 4=translation), `angle0/angle1`,
`offset0/offset1`; `animations.anims2bones[lod][i]` indexes the **global** skeleton (it does NOT
go through `lod.sub_skeletons_to_skeleton`); `animations.axis_data[lod][i]` is
**`(position, direction)`, NOT two points** - measured: wheel axes come back as exactly
`(1,0,0)` unit vectors and dampers as `(0, 0.3, 0)` where 0.3 is the travel length.
Binarize also **lowercases `anim_source` while preserving `anim_name` case**, so compare
sources case-insensitively.

**The trap that inverts the verdict: picking the wrong homologue in the control.**
`CivilianSedan` carries TWO classes driven by `turnfrontleft` with identical angles and
**opposite** axes - `steering_swivel_1_1` on `(0,-1,0)` and `steering_arm_steering_1_1` on
`(0,+1,0)`. The homologue of your steering bone is the **swivel** (the knuckle the wheel hangs
from, i.e. the parent of `wheel_X_1` in your skeleton chain), never the tie rod. Read the
control's skeleton chain before choosing; a comment in your own `model.cfg` asserting which one
you matched is not evidence.

**Worked parity check** (SUB_BRZ vs `civiliansedan.p3d` v54, measured 2026-07-28):

| Leg | Mod | Control homologue | Verdict |
|---|---|---|---|
| wheel roll x4 | `-6.283185 x (1,0,0)` | `wheel_1_1..2_2`: same | identical |
| steering x2 | `+pi/2 x (0,1,0)` | `steering_swivel_X_1`: `-pi/2 x (0,-1,0)` | identical |
| door driver / codriver | `+1.396 x (0,1,0)` / `-1.396 x (0,1,0)` | `DoorsDriver_a` / `DoorsCoDriver_a`: same signs | same convention |

**Dampers have no vanilla homologue if you use the single-bone translation rig** (Tyson89
pattern). `CivilianSedan` models suspension as ~20 ROTATION classes on `susp_arm_*` bones.
Gating your `type="translation"` dampers against the sedan fails by construction - their control
is the Land Rover pattern, not the sedan.

**How to gate it**: assert the pseudovector per animation class against the control, on every
LOD that carries an active binding, plus `anim_source` case-insensitive, bone binding, and a
non-degenerate `axis_dir`. Two fixtures, and getting them the right way round is the whole
point:

- **negative (must FAIL)**: invert the axis **or** the angle, one at a time. That is a real
  direction defect.
- **positive (must PASS)**: invert **both** at once. Same rotation, different parametrization -
  a gate that rejects it is over-fitted to one authoring convention and will reject a correct
  mod.

Checking only "the axis is not null" is not a direction check at all:
`rip_native_door_contract_gate.py:665-674` does exactly that, so it would accept a
backwards-hinging door. Translation animations (`anim_type=4`, dampers) need the same treatment
with `unit(axis_dir) * (offset1 - offset0)`.

Origin: SUB_BRZ 2026-07-28, R21 dual on the "complete the car" roadmap. The measurement turned
the wheel-direction question from "spend an in-game cycle to discover it" into "already proven
offline, in-game only confirms" - which is the difference between one cycle and two.
---

> REDIRECT CAMBIO-1: SP-122 ocupa ahora el sitio del invariante #24 que corrige.

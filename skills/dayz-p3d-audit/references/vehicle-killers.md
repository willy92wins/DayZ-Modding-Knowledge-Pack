# Vehicle-specific killer detail (mass / wheel clearance / crew / vertex ceiling)

> Extracted from dayz-p3d-audit/SKILL.md 2026-07-07 (F3). The core SKILL.md keeps the index/summary and points here.


Satellite checks that extend the 13 killers for wheeled vehicles. The core SKILL.md lists them under "Vehicle satellite checks" with a pointer here.


## #Mass# debe vivir solo en Geometry LOD (added 2026-06-02)

**Origen**: LFQuad N1.5 cerrado 2026-06-02 (handoff `30_Sessions/2026-06-02-LFQuad-placement-fix-firegeo-mass-CLOSED.md`). Un `#Mass#` espurio (todos los valores en 0) en el FireGeo LOD del LFQuad hizo que AddonBuilder/binarize horneara la masa de ESE LOD → ODOL desplegado con `CoM=(0,0,0)` e inercia 0. `ECE_PLACE_ON_SURFACE` colocó el vehículo a la altura del CoM = 0 → spawn 0.48 m bajo tierra → eyección.

### MANUAL check (mass-only-geometry) — NOT automated in audit_p3d.py

(Verified 2026-07-06: no mass-related check codes in `audit_p3d.py` nor in py3d `validate()` — the only `mass` hits in the fork are the `#Mass#` tagg reader/writer and the round-trip verify. Run the reference snippet below manually.)

Per-LOD validation: iterar TODOS los LODs del `.p3d` (Visual <1000, Geometry 1e13, Memory 1e15, LandContact 2e15, ViewGeo 6e15, FireGeo 7e15, Shadow) y comprobar:

- `Geometry LOD` (res 1e13): DEBE tener tagg `#Mass#` con valores no-cero y `lod.mass != None`.
- **TODOS los demás LODs**: NO deben tener tagg `#Mass#`. Si lo tienen (aunque sea con todos 0s), severidad **CRITICAL**.

Mensaje del check al fallar (FireGeo):
> *`FireGeometry LOD (res 7e15) contains a `#Mass#` tagg with N points. AddonBuilder/binarize will bake the mass of THIS LOD (not the Geometry LOD), producing CoM=(0,0,0) and inv_inertia=0 in the deployed ODOL → ECE_PLACE_ON_SURFACE will spawn the vehicle below ground. FIX: clear the mass from this LOD (set `point.mass = None` in the assemble, not `0.0`). py3d emits `#Mass#` if ANY point.mass is not None.*`

### Trampa de py3d (sutil)

py3d **emite el tagg `#Mass#` si ALGUNA `point.mass` del LOD es ≠ None**, aunque sea exactamente `0.0`. Por eso `point.mass = 0.0` deja el tagg con ceros → binarize lo usa → CoM=0. La forma correcta en los LODs no-Geometry es `point.mass = None` (Python None, no `0.0`).

### Detección headless (sin tocar el modelo)

```python
import py3d  # fork DayZ >= 1.5.0 (py3d.read_p3d NO existe: API confabulada)
with open(path, "rb") as f:
    m = py3d.P3D(f)
for lod in m.lods:
    if lod.resolution != 1e13:  # Anything but Geometry
        has_mass_tagg = any(
            p.mass is not None for p in (lod.points if hasattr(lod, "points") else [])
        )
        if has_mass_tagg:
            print(f"CRITICAL: LOD res={lod.resolution:.0e} has #Mass# tagg (must be Geometry-only)")
```

### Tool de fix headless

Para .p3d ya ensamblados con el bug, ver `LFQuad_dev/tools/fix_firegeo_mass.py` (LFQuad-specific pero el patrón generaliza: cargar p3d, iterar LOD ≠ Geometry, setear `point.mass = None`, reescribir). Verificación post-fix: `binarize.exe -always -addon=<dir> <src> <dst> <wildcard>` y leer `ModelInfo CoM` del ODOL (debe ser ≠ (0,0,0)).

### Cross-ref
LL-079 (bisección de LODs aisló el bug), LL-080 (la lección durable), R26 (criterios verificables), R35.1 (bisección antes de ensayo-error).

---

## Wheel-well clearance: medir contra RADIO de rueda, no contra HUB (added 2026-06-02, SP-024)

**Origen**: LFQuad sesión 2026-06-01 (handoff `30_Sessions/2026-06-01-LFQuad-spawn-launch-rootcause.md`, FASE 2). El R21 AC-7 del bake ROUND-2 validó "hubs fuera del hull" usando cajas de hub de 8 puntos. Pero la rueda real (radio 0.34) penetraba el chasis: mín 0.16-0.19 m del centro de rueda al chasis. PhysX-depenetración eyectó al vehículo; el Croco con despeje 0.43-0.46 m asienta limpio.

### Check añadido (wheel-well radius-aware)

Para cada rueda del modelo (proxy `wheel_*_*`):

1. Leer el radio efectivo del config: `wheel_radius` del `class Wheels { ... }` o el del `.p3d` de la rueda (cilindro BoundingBox.Y/2).
2. Computar `min_distance(chassis_geometry_hull, wheel_proxy_center)` con py3d (proyectar el centro del proxy sobre el hull del Geometry LOD del chasis).
3. Si `min_distance < wheel_radius` → **CRITICAL**: collider de rueda penetra chasis → PhysX-depenetración eyectará el vehículo al spawn.
4. Si `min_distance < wheel_radius * 1.20` → **WARNING**: margen mínimo (vibración / contacto intermitente). Croco-equivalent es ratio ~1.27.

Mensaje del check al fallar:
> *`Wheel '<wheel_proxy_name>': chassis-to-wheel-center distance = X.XX m < wheel_radius (Y.YY m). PhysX will treat this as self-penetration on spawn and eject the vehicle. FIX: reshape the chassis Geometry LOD to open wheel-wells (target clearance ≥ wheel_radius * 1.25-1.30, Croco-parity). NOT a hub-vs-hull check — must measure against the wheel volume (cylinder of `wheel_radius`).*`

### Anti-patrón cazado

El audit "hubs fuera del hull" mide contra la **caja del hub** (8 vértices pequeños), que pasa aun cuando la **rueda completa** (cilindro de radio efectivo) penetre. Es un falso PASS reproducible en cualquier vehículo donde el hub esté centrado pero el wheel-well sea estrecho.

### Cross-ref
LL-082 (la lección durable), `vehicle-structural-parity.md` Addendum 2026-05-26/29, `dayz-model-pipeline` sección wheel rigging.

---

## Crew check (get-in / copiloto) (added 2026-06-05)

Two new checks for any vehicle that declares a `Crew` (driver + co-driver / passengers).
Both are silent in-game (no RPT error) and cost days of churn when missed. Origin:
LFQuad 2026-06-05 (~7 days of churn diagnosing exactly these two).

### Check A — `seat_driver` / `seat_codriver` spread across the collision grid

Flag (probable broken get-in / co-driver never appears) if, in the **ViewGeo LOD**, the
selections `seat_driver` / `seat_codriver` are **spread over more than 1-2 components**.
Each seat should live in its **own dedicated component** (the Croco pattern). The engine
resolves which seat a get-in raycast hit via `CrewPositionIndex(component)`
(`transport.c:116`) on the component the raycast strikes. If seats are smeared over the
collision grid, the crew components are chaotic and the co-driver position never resolves.

### Check B — crew proxies are 90/45/45 isosceles triangles

Flag (player sits sideways / rotates on get-in) if the `crewdriver` / `crewcodriver`
proxies are isosceles 90/45/45 triangles → ambiguous angle-sort frame. They must be
**canonical** (three distinct angles). Cross-ref **dayz-proxy-align** "Crew proxies de
vehículos" for the frame convention (+Y → vehicle forward) and the canonical-triangle fix.

---

## Vertex-ceiling flag counts face-indices, not resolved vertices — FALSE POSITIVE (added 2026-06-24)

The DX9 16-bit ceiling flag (`Visual LOD0 over the … vertex ceiling (points=…, face-indices=… > 65536)`)
compares the **face-index count** (`faces × 3`) against 65536. That is NOT the real limit. The DX9 ceiling
is on the number of **resolved unique vertices** (distinct `point_index × normal_index × uv`) per LOD —
indices may far exceed 65536 as long as the unique vertex set does not. A dense visual LOD routinely has
> 65536 face-indices while resolving to far fewer unique vertices, so this fires a **false CRITICAL** on
models that load and render fine.

VERIFIED 2026-06-24 (SUB_BRZ): the audit flagged Visual LOD0 (face-indices 96585 > 65536) as over the
ceiling, but the resolved unique vertices = **22143**, well under 65535 — the body loaded and rendered. The
error it was investigated under (vehicle won't spawn) was UNRELATED (crew/wheel geometry rejection).

**Correct check** (resolved-vertex count, not face-index count):
```python
res = set()
for f in lod.faces:
    for v in f.vertices:
        res.add((v.point_index, v.normal_index, v.uv))
if len(res) > 65535:
    flag_critical(f"LOD resolves to {len(res)} unique vertices > 65535 (DX9 16-bit ceiling)")
```
Cross-ref the project memory `dayz-binarize-vertex-limit` ("límite de vértices resueltos punto×normal×uv por
LOD"). **Patched 2026-07-06**: `check_lod0_vertex_budget` in `audit_p3d.py` now computes the resolved-vertex
count directly — CRITICAL only when resolved unique vertices > 65535; raw point/face-index counts over 65536
emit a WARNING that includes the resolved count.

> Origen: SUB_BRZ Fase 4 in-game debug 2026-06-24 (false-positive surfaced while diagnosing a non-spawning
> vehicle). The real blocker was crew/wheel geometry rejection — root cause OPEN, see
> `dayz-vehicles/references/rip-import.md` addendum "FIRST IN-GAME SPAWN RESULT".

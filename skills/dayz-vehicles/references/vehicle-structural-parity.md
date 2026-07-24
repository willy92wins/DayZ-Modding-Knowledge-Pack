# DayZ Vehicle Structural Parity Checklist

> Generating a wheeled vehicle from scratch (procedural / Blender-to-DayZ) reveals the structural
> pieces a real DayZ vehicle has of stock ONE ERROR AT A TIME in-game. To avoid that whack-a-mole,
> debinarize a vanilla vehicle ONCE and diff against it BEFORE baking.
> Reference: civiliansedan (`DZ/vehicles/wheeled/civiliansedan/civiliansedan.p3d`, ODOL v54, debinarizable).
> Derived from the LFQuad F2 parity audit (2026-05-24). Cross-ref LL-030 (parity-first), LL-031 (gate by RPT).

## Parity-first method (do this BEFORE baking a vehicle)

1. Debinarize the civiliansedan (v54) with `dayz-p3d-debinarizer` (its ODOL reader handles v54).
2. Enumerate every LOD (resolution + `named_selections` + `proxies`) with the ODOL reader.
3. Diff against your model's read-back (py3d) and your `config.cpp`.
4. Build ALL missing pieces in one pass — do not discover them error-by-error in-game.

## Required LOD set for a functional wheeled vehicle

The civiliansedan ships 10 LODs: 6 visual + the special LODs below. A from-scratch vehicle needs at
minimum Geometry + Memory + ViewGeometry (if it has crew) + FireGeometry (if it takes damage).

| LOD | resolution | carries | needed when |
|---|---|---|---|
| Geometry | 1.0e13 | collision hull as `componentNN` + `wheel_X_X_damper_land` (wheel hubs as FACES, not only memory) + `seat_driver`/`seat_codriver` + door selections | always |
| Memory | 1.0e15 | crew/pos points, wheel axes, light points, particle points, `seat_con_*` | always |
| ViewGeometry | 6.0e15 | CREW PROXIES (`crewdriver`/`crewcodriver`/`crewcargoN`) as proxy objects + occlusion components + seats + wheels | if config declares `class Crew` |
| FireGeometry | 7.0e15 | damage-zone components + crew proxies + wheels (ballistic + damage) | if vehicle takes localized damage |
| LandContact | 2.0e15 | ground contact points | OPTIONAL — the civiliansedan has NO LandContact LOD. Do not add unless ground-settling demands it. |

## Crew proxies (the #1 post-spawn gotcha)

`config.cpp` `class Crew` → `Driver.proxyPos="crewdriver"`, `CoDriver.proxyPos="crewcodriver"`. The
engine then looks for crew PROXY OBJECTS named crewdriver/crewcodriver in the **ViewGeometry LOD** (and
FireGeometry). Memory points named crewdriver are NOT sufficient.

Symptom if missing: `PHYSICS (E): Proxy with bone name 'crewdriver' was not found in view geometry level
of model` (the vehicle still spawns, but get-in/crew is broken).

Vanilla proxy models: `\dz\vehicles\wheeled\proxies\crew_driver.p3d` (-> crewdriver) and
`\dz\vehicles\wheeled\proxies\crew_cargo.p3d` (-> crewcodriver, crewcargo1, crewcargo2). Place them at the
crew memory points (`crewdriver`/`crewcodriver` / `pos_driver`/`pos_codriver`).

## Lights

- Model visual LODs: selections `light_1_1`, `light_1_2`, `light_2_1`, `light_2_2`, `light_brake`,
  `light_brake_1_2`, `light_brake_2_2`, `light_reverse_1_2`, `light_reverse_2_2`, `light_dashboard`, `light_rear`.
- Model Memory LOD: `light_left`, `light_left_dir`, `light_right`, `light_right_dir`, `light_reverse`,
  `reflector_1_1`, `reflector_2_1`.
- Config (CarScript): `hiddenSelections[]` with the light_* selections; `hiddenSelectionsMaterials[]` ->
  a lights `.rvmat`; material-switch properties `frontReflectorMatOn/Off`, `brakeReflectorMatOn/Off`,
  `ReverseReflectorMatOn/Off`, `TailReflectorMatOn/Off`, `dashboardMatOn/Off`.

Without the selections + memory points + config, headlights mount but never illuminate.

## Damage

- Config: `class DamageSystem { class GlobalHealth { healthLevels[] } }` + `class DamageZones`
  (chassis, front, back, roof, engine, fueltank, fender_1_1/1_2/2_1/2_2, windowfront, windowback).
- Model: each zone maps to a component in FireGeometry + `dmgzone_*` selections across visual/ViewGeo/FireGeo/Memory.
- Wreck (DayZ cars): handled via destruction effects / material swap rather than a dedicated Wreck class
  in `wheeled/config.cpp` — verify the exact mechanism against the reference before relying on it.

Without DamageZones + FireGeometry components there is no localized damage and no wreck.

## AnimationSources (wheel / damper / steering)

The dampers need user animation sources: config `class AnimationSources` with `damper_1_1/2_1/1_2/2_2`
as `source="user"` (`initPhase` + `animPeriod`). Without this block: `unknown animation source damper`.
Wheel rotation (`source "wheel"`) and steering (`source "direction"`) are driven by the car simulation
when `Axles -> Wheels` (`animRotation`/`animTurn`/`wheelHub`) are correct AND the wheel hubs exist as
faces in the Geometry LOD (`wheel_X_X_damper_land`). `model.cfg` defines the animation classes; the
config wires them.

## Cross-reference

- LFQuad F2 parity audit: `AI/10_Projects/LFQuad/research/2026-05-24-parity-audit-civiliansedan-claude.md`.
- LL-030 (parity-first), LL-031 (gate by RPT post-deploy).
- Skills: `dayz-p3d-debinarizer` (debinarize the reference), `enforce-script-reference` (config blocks),
  `dayz-animation-pipeline` (model.cfg / AnimationSources), `dayz-particles` (damage effects).

---

## Addendum (2026-05-26) — Lecciones de la depuración "el quad no conduce" (LFQuad)

> Verificado contra civiliansedan v54 (full), hatchback_02/offroadhatchback/offroad_02 (FireGeo) y
> Croco quadbike v53 (solo cabecera). Marcado [VERIFICADO] vs [HIPOTESIS] (regla R31: una divergencia
> con el referente es candidato, no veredicto; no afirmar causa sin leer el mecanismo).

### Vehiculo que NO rueda / se hunde / bota, con TODO el checklist presente

Si el vehiculo se crea, dirige y suena pero NO RUEDA, se HUNDE y BOTA, sin error en el RPT, la
simulacion PhysX de rueda no engancha. Discriminador clave [VERIFICADO]: "dirige (steering anima) pero
no rueda" = rueda reconocida por config/anim pero su fisica (contacto/suspension/rotacion) bloqueada.

- El hub de rueda NO puede estar dentro del convex hull del chasis [HIPOTESIS fuerte]. La rueda raycast
  lanza un rayo hacia abajo desde el hub; si nace dentro de la colision del chasis, auto-colisiona -> sin
  contacto suelo -> sin suspension (hunde) + sin traccion (no rueda). Un unico convex hull del cuerpo
  entero es INCORRECTO: engloba el espacio de las ruedas. El chasis necesita wheel-wells (colision ausente
  donde van las ruedas): hull mas estrecho que la via, o multi-componente con huecos. Comprobar offline
  que cada hub queda FUERA del hull y que el neumatico no lo penetra.
- Fallo silencioso (sin error RPT) -> instrumentar, no adivinar [PROCESO, R35]. Script debug temporal en
  el .c del vehiculo que loguee GetWheelCount(), velocidad de rueda vs EngineGetRPM(), server vs cliente,
  contacto. Observar el fallo. Prohibido el bucle "una hipotesis -> un cambio -> un test".
- Que NO es la causa si se clono de un vehiculo funcional [VERIFICADO]: drivetrain (motor/par/embrague/
  caja/diferencial), scripts (CarScript hijo; diferencias cosmeticas), model.cfg. El fallo de "no rueda"
  suele ser de modelo/geometria o binding nativo, no del config/script clonado.

### Wheel-proxies en FireGeometry [VERIFICADO 4/4 vanilla]

TODOS los coches vanilla revisados llevan proxies de rueda en su FireGeometry LOD, identicos a los del
Visual LOD (sedan sedanwheel.001-005, hatchback_02, niva, offroad_02). Replicar: copiar los wheel-proxies
del Visual a la FireGeo (cara-proxy de 3 vertices + seleccion proxy:path.NNN, mass 0). Nota: la tabla de
memory-and-selections.md ("proxies NO en FireGeo") es para attachments tipo item, NO para ruedas.

### Tamano del hub wheel_X_X_damper_land en Geometry [VERIFICADO vs sedan]

Componente convexo PEQUENO (~0.20x0.18x0.18, sedan), NO una caja grande. Un from-scratch con cajas de
~0.40 es 2x demasiado grande y baja casi al suelo.

### Masa, COM y suspension escalan con el vehiculo [VERIFICADO vs Croco]

- La masa se computa de los pesos de vertice de la Geometry LOD. Un quad real pesa ~1000 kg (Croco
  ModelInfo: mass 1061.5, COM (0, 0.474, -0.011)), NO el ~250 por defecto de un hull procedural. Masa
  demasiado baja -> fisica inestable (bote).
- La suspension (stiffness/compression/damping) escala con la masa: NO clonar la de un crawler pesado
  sobre un quad ligero (muelles brutalmente duros -> bote). Clonar de masa comparable.
- wheelHubRadius = radio del COMPONENTE DE HUB (pequeno ~0.11-0.15), NO el radio del neumatico (doc BI).
  Croco 0.11 (neumatico 0.367); sedan 0.15.
- Radio de rueda vs holgura de bajos: contacto de rueda ~Y=0 y fondo del chasis bien por encima (sedan
  belly clearance 0.428 m). Ruedas pequenas -> el cuerpo monta demasiado bajo.

### Wreck [VERIFICADO sedan]

El sedan ship 3 .p3d de wreck dedicados direccionales (wreck/_wreckedfront/back/both.p3d) + spawn
script-side (no hay wreck= ni class Wrecked* en wheeled/config.cpp). healthLevels {} vacios es valido.

### Herramientas / parity de referencias [VERIFICADO]

- Croco quadbike v53: NO full-debinarizable (desync en EmbeddedMaterial v53), pero la cabecera/ModelInfo
  SI (mass, COM, geometry_center, resoluciones de LOD) monkeypatcheando LOD.read para saltar el parse de
  geometria. Para su geometria real -> Object Builder (maneja v53).
- El debinarizer INVIERTE el winding (ODOL->MLOD) -> un MLOD debinarizado NO es referencia de winding
  fiable. Para winding de colision usar Check C (cross vs centroide del componente).
- LOD set de un quad que funciona (Croco): visual 0-6, shadow 1100, Geometry 1e13, Memory 1e15, ViewGeo
  6e15, FireGeo 7e15 (sin LandContact).

> Origen: LFQuad bug-ledger P1 2026-05-26 (UPDATE 1-6); handoff 30_Sessions/2026-05-26-LFQuad-wheelsim-debug-handoff.md; LL-039/040/041; R31, R35.

---

## Addendum (2026-05-29) — Wheel proxy `.p3d` Memory anatomy (T1-D) [VERIFICADO vs Croco]

> Esta sección cubre el `.p3d` del **wheel attachment** (el archivo separado que se referencia
> desde `CfgNonAIVehicles` `ProxyVehiclePart` y se ata al body por `inventorySlot`), no el
> body. Es donde estaba el bug que pasó desapercibido entre 2026-05-26 y 2026-05-29 (4
> sesiones), origen de `contact=0` permanente y bounce divergente. Ver LL-057 para la
> lección de proceso, este addendum para la anatomía técnica.

### El wheel proxy `.p3d` NO es "una rueda con LODs visuales". PhysX usa su Memory LOD para construir el wheel collider.

Sin las 5 selecciones canónicas en el Memory LOD del wheel proxy, **PhysX no sabe el tamaño
del wheel collider** y por defecto usa el Geometry LOD del proxy (típicamente un cubo
proxy 8v de 0.20³ generado por `dayz-model-pipeline` cuando lo creas de cero). El collider
efectivo de la rueda termina siendo del tamaño de un cubito en lugar de una rueda Ø(2×radius).
Síntoma: `wheelCount=N wheelPresent=N` (ruedas atachadas OK) pero `contact=0` siempre tras
el primer frame in-game (el raycast wheel→ground solo alcanza ±0.10 m bajo el hub anchor en
lugar de ±radius). Resultado: el body cae libre hasta que el chasis Geometry colisiona,
bounce divergente acumulativo, eventualmente `speedo` excede el rango finito y la engine
hace `Will delete object with !finite or outside world coords`.

### Las 5 mem-points canónicas (extraídas de Croco `quadbike_wheel.p3d` v53, debinarizado 2026-05-27)

Cada una es una `Selection` de 1 punto único en el Memory LOD (resolution 1e15). Todas siguen
la convención Croco-vanilla (Y vertical/radial, X axial/width, Z radial con inversión
intencional entre min y max).

| Selection | Cita Croco (front wheel) | Significado | Escalado a un wheel custom |
|---|---|---|---|
| `ce_center` | `(−1e-05, 0.0, 0.0)` ≈ (0,0,0) | centro del collider | siempre origen |
| `ce_radius` | `(3e-05, 0.37679, 0.40015)` | marker de radio (Y) + width-marker (Z) | `(0, wheel_radius, ce_radius_Z)` — preservar la relación Z/Y de Croco (~1.062×Y) |
| `boundingbox_min` | `(−0.19095, −0.3816, +0.38558)` | esquina min con **Z positivo** | `(−width/2, −wheel_radius, +wheel_radius)` |
| `boundingbox_max` | `(+0.20446, +0.39014, −0.38393)` | esquina max con **Z negativo** | `(+width/2, +wheel_radius, −wheel_radius)` |
| `invview` | `(−0.23026, −1e-05, 0.0)` | offset X negativo (probablemente para inversión de view) | preservar offset relativo al width axial |

**Quirk no-estándar**: `boundingbox_min.Z > boundingbox_max.Z` (Z invertido entre min y max).
NO normalizar — es convención BI/PhysX para wheel proxies. Copiar literal escalando Y/Z
con `factor_radial = wheel_radius / 0.38587` y X con `factor_axial = width / 0.39541`.

### Cómo construirlas con py3d 1.0.0 (cross-ref a `dayz-animation-pipeline` anchor 6)

Los 6 quirks de py3d 1.0.0 aplican (constructor con args, weight int, rebind tras grow,
matname lowercase, overwrite-in-place para `ce_center` si ya existe, frame +Z/-Z si el
wheel viene de Blender). Ver `references/py3d-1.0.0-quirks.md` de la skill
`dayz-animation-pipeline`. NO duplicar el patrón aquí — la skill de pipeline de animación
es la fuente canónica para escribir Memory LODs vía py3d.

### Criterio de aceptación (R26) para wheel proxies generados desde cero

Antes de declarar un wheel proxy "ready", verificar con py3d:

```python
mem = next(l for l in p3d.lods if abs(l.resolution - 1e15) < 1e12)
required = {"ce_center", "ce_radius", "boundingbox_min", "boundingbox_max", "invview"}
missing = required - set(mem.selections.keys())
assert not missing, f"wheel proxy Memory incomplete: missing {missing}"
```

Esto debe ser parte del round-trip post-bake de cualquier wheel proxy y debe entrar
al `product-spec.md` del proyecto como criterio anatómico verificable, no como backlog
opcional (LL-057).

### El audit lo cubre (cross-ref)

`dayz-p3d-audit` Silent Killer #11 (added 2026-05-29) cubre el caso. Si auditas un wheel
proxy y devuelve PASS con solo `ce_center`, el chequeo no cubrió esta dimensión —
correr la skill actualizada.

> Origen: LFQuad bounce debug 2026-05-29; medición py3d directa en sesión Cowork;
> Croco v53 wheel JSON (`AI/10_Projects/LFQuad/research/2026-05-27-croco-geometry-extracted-v53.json:17207-17251`).
> Cross-ref: LL-057 (proceso, gap diferido sin gate), LL-055/056 (py3d 1.0.0 quirks),
> bug-ledger entry 2026-05-29 [process/anti-pattern].

---

## Addendum (2026-05-30) — Canonical car-build invariants (Landrover tutorial + Bohemia + PhysX) [VERIFICADO fuente primaria]

> Qué resuelve: el LFQuad shippeó botando/lanzándose al spawn pese a 4+ iteraciones. La pieza que
> faltaba NO era ride-height (eso era una divergencia real pero NO el mecanismo del lanzamiento). Es
> **cómo se construye la Geometry/masa**. Este addendum encodea el método canónico de construcción de
> un coche DayZ, cruzando el tutorial paso-a-paso **Tyson89/Landrover** (wiki + repo), la doc oficial
> de Bohemia y la doc de PhysX de NVIDIA. Provenance: subagentes que fetchearon y citaron VERBATIM las
> páginas/archivos reales (no memoria). Marcar [DOC] = documentado con fuente; [MEDIDO] = medido en
> referente; [CONSENSO] = comunidad sin doc oficial.

### Referencias externas autoritativas (citar SIEMPRE al construir un coche; añadidas a esta skill por petición)

- **Tutorial paso-a-paso (drivable car de cero):** `https://github.com/Tyson89/Landrover/wiki` — 4 páginas:
  [Home], [config.cpp](https://github.com/Tyson89/Landrover/wiki/config.cpp),
  [Object-Builder](https://github.com/Tyson89/Landrover/wiki/Object-Builder),
  [SimulationModule](https://github.com/Tyson89/Landrover/wiki/SimulationModule). Repo (config.cpp +
  Landrover.cfg model.cfg, branch `main`, licencia ADPL-SA): `https://github.com/Tyson89/Landrover`.
  Es el ejemplo concreto "cómo se hace bien" — referencia primaria para cualquier coche nuevo.
- **Bohemia oficial:** `https://community.bistudio.com/wiki/DayZ:Vehicle_Configuration` (Geometry LOD +
  masa por vértice → masa total + CoM; wheel hubs como componentes propios; wheel-proxy en FireGeo;
  Diag tool in-game). `https://community.bistudio.com/wiki/LOD` (grosor ≥0.5 m; "Mass distribution is
  critically important … Inertia/Moment of Inertia"; "flying tanks" por geometría que sobresale en el
  PhysX LOD). `https://community.bistudio.com/wiki/Validating_Geometries` (Find Non-Convexities /
  Convex Hull; cerrado+convexo o no funciona). `https://community.bistudio.com/wiki/Oxygen_2_-_Manual`
  (Find Components; "Geometry components must be closed convex objects"; <15 cm no colisiona a velocidad).
  `https://community.bistudio.com/wiki/Arma_3:_Cars_Config_Guidelines` (PhysX LOD 4e13 aparte; CoM
  centrado izq-der; `sprungMass` suma = peso).
- **Mecanismo del lanzamiento (PhysX):** `https://nvidia-omniverse.github.io/PhysX/physx/5.1.3/docs/BestPractices.html`
  — sección "Overlapping objects explode": cuerpos creados solapados "may explode, because the SDK tries
  to resolve the penetrations in a single time-step, which can lead to large velocities." Workaround del
  motor: `setMaxDepenetrationVelocity` (no expuesto a modders; la engine lo clampa internamente, pero la
  geometría mala lo dispara igual). Comunidad Arma "Anti-Bounce System" (Steam 2191542091): el bote al
  contacto lo causan "sharp edges in geometries which apparently impart a large moment to the vehicle,
  thus sending it up into the air" [CONSENSO, coincide con el mecanismo PhysX].

### La invariante de construcción de la Geometry LOD (lo que faltaba)

**La Geometry de un coche que funciona es un COMPUESTO de varios componentes convexos cerrados, NUNCA un
casco monolítico.** [DOC] Object-Builder checklist del Landrover (verbatim): "Convex Components / Property
Name 'autocenter' value '0' / Simple Shape - No unnecessary components / **Applied a Mass on ALL
components** / Wheel hubs present and selections assigned / Center of Mass". Bohemia: "convex components.
Every component's vertex should have weight assigned. From these weights the total mass of vehicle and its
center of mass is computed." (Croco quad = **23 componentes de chasis + 4 hubs**; LFQuad shippeó con **1**
`component01` que acaparaba ~90% de la masa — anti-patrón.)

Consecuencias de construirlo como monolito (las dos patas del bote del LFQuad, MISMA raíz):
1. **Trigger (forma):** un único casco convexo ajustado con bordes afilados, al despertar el rigid body en
   el spawn, solapa terreno/hubs → PhysX resuelve la penetración en un paso → impulso enorme → lanzamiento
   ([DOC] NVIDIA; [CONSENSO] ABS "sharp edges … large moment").
2. **Amplificador (inercia):** masa concentrada en 1 componente → tensor de inercia patológico/bajo
   (LFQuad Izz **128.5** = 37% del Croco **350.7** [MEDIDO]) → cualquier impulso lo hace girar/tumbar →
   re-penetra → gana energía → `Will delete object with !finite or outside world coords`. [DOC] LOD wiki:
   "the Mass distribution is critically important for the Objects physical behavior [Inertia / Moment of
   Inertia]".

### Checklist canónico (cada punto verificable offline; añadir al round-trip y al product-spec)

| # | Regla | Fuente | Check |
|---|---|---|---|
| 1 | Geometry = varios `componentNN` convexos **cerrados** (no monolito) | [DOC] Validating_Geometries / Oxygen2 / Landrover | `Find Non-Convexities` + `Find Non-Closed` limpios; contar componentes > 1 para el chasis |
| 2 | **Masa en TODOS los componentes** (incl. los 4 hubs), no concentrada en uno | [DOC] Landrover + Bohemia | sumar peso por componente; ninguno a 0; ninguno >~60% del total |
| 3 | `autocenter = 0` como named property en **cada** componente de Geometry | [DOC] Landrover Object-Builder | leer named properties por componente (extiende Killer #3 del audit a vehículos) |
| 4 | CoM **centrado en X** (izq-der); Y/Z razonables, no sesgo grande | [DOC] Landrover + Arma3 Cars | `CoM.x ≈ 0`; LFQuad CoM (0, 0.513, **+0.399**) vs Croco (0, 0.474, −0.011) [MEDIDO] → sesgo Z grande |
| 5 | Grosor de componente ≥ 0.5 m (un quad es estrecho: Croco chasis ±0.275 = 0.55 m) | [DOC] LOD wiki | ancho del componente de chasis ≥0.5 m (LFQuad post-D4H ±0.175 = 0.35 m ✗ — revertir) |
| 6 | Hubs `wheel_X_X_damper_land` = componentes convexos reales con masa, NO solo selecciones de cara | [DOC] Landrover + Bohemia | cada hub es un componente cerrado con peso (no parche del C.9) |
| 7 | Proxies (rueda/crew/puertas) **NO** en Geometry LOD (no animan, no colisionan allí) | [DOC] Landrover Object-Builder | Geometry sin proxies; wheel-proxies sí en Visual+ViewGeo+FireGeo |
| 8 | Fire Geometry obligatoria en vehículos | [DOC] Landrover Object-Builder | FireGeo presente |
| 9 | `drown_engine` memory point definido (si falta → 0 0 0 → motor se ahoga en el origen) | [DOC] Landrover Object-Builder | punto presente y posicionado en el motor |

### Suspensión: calibrada a la masa (fórmula documentada)

[DOC] Landrover SimulationModule: "Stiffness … needs to overcome the Kilogram that is going down by the
force of gravity"; punto de partida `compression = stiffness / 10`, `damping = compression * 3` (luego
ajustar). **Config de referencia VERBATIM del Landrover** (AWD, ~landrover; sólo como ancla de orden de
magnitud, no copiar a ciegas a un quad):

```cpp
class Suspension { stiffness=40000; compression=2100; damping=5400; travelMaxUp=0.10; travelMaxDown=0.06; };
wheelHubMass=15;      // KG, sólo aplica si NO hay rueda atachada
wheelHubRadius=0.284; // medido del componente hub (Shift+E, eje Y), nunca negativo
```

Comparativa [MEDIDO]: Croco stiffness 40000–41000; **LFQuad 20000** (la mitad), damping 9000, travelMaxUp
0.293/0.414. Trampa documentada: masa demasiado BAJA + stiffness copiada de un vehículo más pesado →
catapulta. (LFQuad NO está en esa trampa: su masa es correcta 1061.5 y su stiffness es más baja que el
referente — la suspensión NO es el trigger del bote; confirmado in-game D4H y por un caso comunitario
idéntico donde permutar suspensión/damping no curó el "floating/bouncing": *"both ways did not work … I'm
starting to think it's something else"*.)

### model.cfg — patrón del `suspension_damper` (resuelve la duda recurrente minValue/maxValue vs offsets)

[DOC] repo Landrover `Landrover.cfg` VERBATIM. **`minValue=0` / `maxValue=1` fijos; el recorrido real lo
llevan los offsets** (NO al revés):

```cpp
class suspension_damper_1_1 {
    type="translation"; source="damper_1_1"; selection="wheel_1_1_damper";
    axis="wheel_1_1_damper_axis";
    minValue=0.0; maxValue=1.0;        // FRONT (rear usa maxValue=0.6, sólo visual)
    offset0=0.05;  offset1=-0.35;      // recorrido: +0.05 (sobre reposo) a −0.35 (compresión)
};
// config.cpp AnimationSources: class damper_1_1 { source="user"; initPhase=0.4857; animPeriod=1; }
//   initPhase fija la posición visual del damper EN REPOSO (front ~0.486, rear ~0.400).
```

Esqueleto [DOC]: front = `damper → steering → wheel` (3 niveles, con bone de dirección); rear =
`damper → wheel` (sin bone de steering). El `source` del damper (`damper_1_1`…) casa con `animDamper` en
`Axles→Wheels` del config y con la clase de `AnimationSources`.

### config.cpp — masa NO va en el config

[DOC] El repo Landrover NO tiene `mass`/`sprungMass`/`centerOfMass`/`geometryClass` en config.cpp. La masa
se fija SÓLO por pesos de vértice en la Geometry LOD (Object Builder, Alt+M). No buscar setear masa por
config en DayZ CarScript.

### Lo que el Landrover NO cubre (gaps — seguir usando Bohemia/Croco)

- Sin sección de troubleshooting "el coche bota/vuela" (es guía de construcción, no de fallos).
- Sin cobertura del **PhysX LOD 4e13** separado del Geometry 1e13 (Arma sí lo exige —
  `[TBD-verify vs Croco/DayZ]` si los coches DayZ lo llevan). Resolution LOD y View Geometry = "TBD".
- Sin `sprungMass`; sin números de masa total. La Geometry-mass→CoM→inertia sigue siendo la fuente Bohemia.

> Origen: LFQuad bounce 2026-05-29/30; doc-research multi-agente (Bohemia + NVIDIA PhysX + ABS) y parse
> multi-agente del repo+wiki Tyson89/Landrover (citas verbatim de fuente primaria). Cross-ref: LL-062
> (operacionalizar invariantes en checks medibles), LL-030 (parity-first), `dayz-p3d-audit` Killers #3/#8/#9/#12/#13,
> Addendum 2026-05-26 (masa/CoM/suspensión escalan) y Addendum 2026-05-29 (ride-height triple).

---

## Addendum (2026-05-30b) — Per-LOD content map, memory-point catalog, proxy placement, LOD verbatim [VERIFICADO fuente primaria]

> Complemento de la "Required LOD set" de arriba y del Addendum 2026-05-30 (invariantes de Geometry/masa).
> Aquí: QUÉ contenido concreto va en cada LOD de un coche, el catálogo completo de memory points, dónde van
> los proxies por LOD, y las descripciones VERBATIM de Bohemia de cada LOD. La parte de **config.cpp +
> model.cfg** vive en `references/vehicle-config-and-modelcfg.md` (no duplicar). Fuentes: Bohemia LOD /
> Oxygen_2 / Validating_Geometries / Arma_3_Cars_Config_Guidelines (sub-agentes, citas verbatim) +
> `DayZ_Vehicle_Skill/skill-draft/references/extract-3d.md` (catálogo QuadBike real, vault) + Landrover.

### Qué va en cada LOD de un coche

| LOD | resolution | Contenido del coche | Cita Bohemia (verbatim) |
|---|---|---|---|
| Resolution 0–N | 0,1,4,8 | malla visual + proxies de rueda/crew/puerta en CADA visual LOD que deban verse | "Proxies need to be included in every resolution LOD that they should appear in." "should not contain any empty Named Selections … used in animations or by the game engine (wheels, etc), as this might cause the game to crash" |
| Geometry | 1.0e13 | `componentNN` convexos cerrados (chasis multi-componente) + hubs `wheel_X_Y_damper_land` como componentes propios; masa por vértice → masa+CoM | "convex components … From these weights the total mass of vehicle and its center of mass is computed. Wheel hubs should have their own components" (DayZ wiki) |
| Memory | 1.0e15 | TODOS los memory points (catálogo abajo): crew pos/dir, wheel axes, damper axes, light points, `drown_engine`, dials | "Named Selections used to define lights, vehicle entry points … control points for Animations" |
| LandContact | 2.0e15 | vértices de contacto con el suelo (OPCIONAL en coches DayZ — civiliansedan no la lleva) | "Contains only vertices that represent contact with land … mainly for vehicles. Wrong positioned points can cause 'levitation' or 'submerge'" |
| Roadway | 3.0e15 | superficie pisable (techo/capó si el jugador puede subirse) — no obligatoria | "If a unit is supposed to be able to stand on top of a model … Make sure that a RoadwayLOD doesn't overlap with a GeometryLOD, or the unit will start to wobble" |
| Hitpoints | 5.0e15 | una selección `dmgZone_*` por cada zona de daño del config | "define, via unconnected named vertexes, where certain destroyable parts of a model are (e.g. wheels, lights, etc.)" |
| ViewGeometry | 6.0e15 | CREW PROXIES (`crewdriver`/`crewcodriver`/`crewcargoN`) + componentes de oclusión + asientos | "If there is no component in view or fire geometry, players cursor will be not able to activate action menu" |
| FireGeometry | 7.0e15 | componentes de damage-zone + **wheel-proxies** (idénticos al Visual) + crew proxies | "Inside the fire geometry LOD there must be a proxy object placed with the correct name of the wheel slot so the simulation can attach a wheel and suspension to that position" (DayZ wiki) |
| Shadow Volume | 1.0e4 / 1.1e4 | sombra cerrada+triangulada, ligeramente encogida vs visual (opcional) | "Shadow LOD must be slightly shrinked compared to resolution LOD … otherwise the Model may look partly or completely shaded" |

Reglas de geometría reforzadas (verbatim): "Geometry objects should have a thickness of at least 0.5 meters
in order to work properly" (LOD wiki) · "Thinner parts than 15cm cannot collide in faster speeds" (Oxygen2) ·
"Geometry components must be closed convex objects" (Oxygen2) · validar con `Structure → Topology → Find
Non-Closed` + `Structure → Convexities → Find Non-Convexities` / `Component Convex Hull` (Validating_Geometries).

### PhysX LOD 4e13: Arma-3 sí, DayZ no (resuelve el [TBD-verify] previo)

El Addendum 2026-05-30 dejó `[TBD-verify vs Croco/DayZ]` si los coches DayZ llevan un PhysX LOD 4e13 aparte
del Geometry 1e13. Resuelto: es **Arma-3**. `Arma_3_Cars_Config_Guidelines` (verbatim): "There needs to be a
lod (4e13) consisting of convex components as simple as possible … Just the main body of car should be in
this lod, wheels are added by engine later." Los referentes **DayZ** (Landrover, QuadBike, Croco,
civiliansedan) usan **Geometry 1e13 sin un 4e13 separado**. → NO añadir un LOD 4e13 a un coche DayZ salvo
verificación in-game.

### Corrección de matiz: "flying tanks" ≠ el bote del spawn

El Addendum 2026-05-30 invocó el quote "flying tanks" del LOD wiki como apoyo del mecanismo de bote. Matiz
verificado: ese quote es específico de **barras de cañón/torreta que SOBRESALEN en el PhysX LOD** ("the
collision of a barrel with the environment will cause the tank … to move very violently … flying tanks"),
NO del bote por depenetración al spawn. El mecanismo del bote del spawn sigue siendo: PhysX resuelve la
interpenetración en un paso → impulso (NVIDIA "Overlapping objects explode") + bordes afilados (ABS,
comunidad). Ambos son reales pero distintos; no fusionarlos. (No se halló quote Bohemia explícito del
"spawn-bounce por geometría que sobresale bajo el origen" → ese eslabón sigue `[verify in-game]`.)

### Catálogo de memory points de un coche [VERIFICADO QuadBike vía extract-3d.md]

> Fuente: `AI/10_Projects/DayZ_Vehicle_Skill/skill-draft/references/extract-3d.md:106-191` (strings reales del
> QuadBike v53). ✓ = confirmado presente en QuadBike. Patrón rueda `wheel_<eje>_<lado>`, eje 1=front/2=rear,
> lado 1=left/2=right.

- **Crew/seats:** `pos_driver`(+`_dir`), `pos_codriver`(+`_dir`), `pos_cargo`(+`_dir`); proxies
  `crewdriver`,`crewcodriver`,`crewcargo1`,`crewcargo2`; selecciones `seat_driver`,`seat_codriver`,`seat_cargoN`;
  door-condition `seat_con_1_1`,`seat_con_2_1`.
- **Ruedas (×4):** `wheel_X_Y_axis` (2 pts, eje de rotación), `wheel_X_Y_damper` (selección de translación de
  suspensión), `wheel_X_Y_damper_axis` (2 pts), `wheel_X_Y_damper_land` (contacto suelo = el `wheelHub` del
  config), `wheel_X_Y_steering`+`_steering_axis` (solo front), `steering_hub_X_1` (front).
- **Steering/dashboard:** `steeringwheel`, `drivewheel`(+`_axis`), `mph`(+`_axis`), `rpm`(+`_axis`),
  `fuel_1`(+`_axis`), `dial_temp`(+`_axis`), `light_dashboard`.
- **Lights:** `light_1_1`,`light_2_1` (front), `light_1_2`,`light_2_2` (tail), `light_brake_1_2/2_2`,
  `light_reverse_1_2/2_2`, beam `light_left`(+`_dir`),`light_right`(+`_dir`), `reflector_1_1`,`reflector_2_1`.
- **Engine/particles:** `engine`(+`_axis`), `enginerun`,`engineshake`; `drown_engine` (¡crítico, §9 del 30-05!);
  `ptcexhaust_*`/`ptccoolantpos` `[TBD-verify — no salieron en strings del QuadBike]`.
- **Otros:** `pos center` (con espacio), `ce_center`/`ce_radius` (Central Economy loot), `fuelpoint`.

### Named selections por LOD (coche)

- **Visual LODs:** ruedas `wheel_X_Y`, suspensión `wheel_X_Y_damper`, steering `wheel_X_1_steering`,
  `steeringwheel`/`drivewheel`, puertas `doors_*`, asientos `seat_*`, luces `light_*` (hiddenSelections),
  `color`/`base`/`special` (hiddenSelections), catch-all del chasis (`zbytek`).
- **Geometry/Collision LODs:** `componentNN` (lowercase `component01` — vanilla vehicles use lowercase,
  measured via py3d on CivilianSedan and the extracted QuadBike MLOD; the uppercase `Component01` rule is
  Inventory_Base-only, see §validate() ERR_COMPONENT_NAMING. QuadBike Geometry has 27 components — ~30-50
  basta para sedan/hatch). Hubs `wheel_X_Y_damper_land` como componentes propios.
- **Hitpoints LOD:** una `dmgZone_*` por zona del config (`dmgZone_chassis/front/back/fender_*/engine/fuelTank/lights_*`).

### Proxies por LOD (coche)

- **Wheel proxies:** en CADA Visual LOD + ViewGeometry + FireGeometry (idénticos), masa 0. NO en Geometry
  (los hubs en Geometry son componentes, no proxies). Su `.p3d` necesita las 5 mem-points de Memory
  (Addendum 2026-05-29). Cara-proxy de 3 vértices + `proxy:path.NNN`.
- **Crew proxies:** ViewGeometry + FireGeometry; modelos vanilla `\dz\vehicles\wheeled\proxies\crew_driver.p3d`
  / `crew_cargo.p3d`. Sin ellos → `Proxy with bone name 'crewdriver' was not found in view geometry level`.
- **Door proxies:** la puerta es un `.p3d` aparte (item `CarDoor`) referenciado por `inventorySlot`; su
  apertura la anima el model.cfg del body, no el proxy. Oxygen2 (verbatim): "Proxy model must have geometry
  property `autocenter = 0` otherwise 0.0.0 axis of the inserted model will not be correct."

> Origen: LFQuad car-build skill consolidation 2026-05-30. Cross-ref `references/vehicle-config-and-modelcfg.md`,
> Addenda 2026-05-26/29/30, `dayz-p3d-audit` Killers #11/#12/#13, `dayz-pbo-build`.

---

## Correction (2026-05-30c) — Croco Geometry is extractable; the 2026-05-26 Object Builder note is stale

The Addendum 2026-05-26 note above says the Croco quadbike v53 is "NO full-debinarizable" and routes real geometry to Object Builder. That was true for the early parser state, but it is stale for the current LFQuad ROUND-2 workflow.

Verified current state:
- `AI/10_Projects/LFQuad/research/2026-05-27-croco-geometry-extracted-v53.md:76-82`: material v16 was resolved; all 12 LODs parse; a complete Croco MLOD was generated; Geometry LOD is OK with hubs + 27 convex components + `class=vehicle`.
- `AI/30_Sessions/2026-05-30-LFQuad-round2-spec-y-debinarizer-verdict.md:7`: `croco_extracted/quadbike_mlod.p3d` is usable, with round-trip OK since 2026-05-27; the residual debinarizer gap only affects visual LODs >16KB and has zero leverage for the bounce fix.
- `AI/30_Sessions/2026-05-30-LFQuad-round2-spec-y-debinarizer-verdict.md:13,16`: ROUND-2 should use py3d on the Geometry LOD, mirroring the extracted Croco; do not improve the debinarizer or fall back to Object Builder for this geometry task.

Operational rule: for car Geometry parity, use `croco_extracted\quadbike_mlod.p3d` / `croco_extracted\quadbike_mlod.p3d`-derived data as the quantitative reference. Treat the 2026-05-26 "Object Builder" sentence as historical context only, not current guidance.

---

## (added 2026-06-05) Geometry LOD named property `class=vehicle` -- required parity (SP-012b)

The Geometry LOD of every vanilla wheeled vehicle carries the named property `class = vehicle`
(alongside `autocenter = 0`). Verified universal -- civiliansedan, sedan_02, hatchback_02,
offroadhatchback, offroad_02, truck_01: 6/6 have `('class','vehicle')` on their Geometry LOD. It
flags the Geometry as a VEHICLE physics body. A procedurally-assembled Geometry that sets only
`autocenter=0` (the common py3d mistake -- assemble scripts set autocenter but never `class`) omits
it. Replicate it: `geo_lod.properties['class'] = 'vehicle'`, write back, confirm
`strings model.p3d | grep -c vehicle`.

Causation caveat (R31, verified in-game 2026-05-27): adding `class=vehicle` did NOT fix LFQuad's
`WheelCountPresent()==0` -- it was deployed, confirmed present in the binarized Geometry LOD, and the
in-game result was unchanged. So treat `class=vehicle` as REQUIRED PARITY (6/6 vanilla carry it; a
vehicle build must replicate it and it is cheap), NOT as the proven wheel-simulation gate. The
actual silent wheel-sim gate verified in-game is the `CfgSlots.selection` <-> FireGeometry proxy
selection consistency rule (see `enforce-script-reference`, wheel attachment / SP-017). Origin:
SP-012b, LFQuad bug-ledger UPDATE 8/10.

(Merged 2026-07-06 from the `dayz-model-pipeline` fork copy -- LL-110 dedup.)

## Correction (2026-06-01) — el spawn-launch es colisión-de-rueda + placement, NO masa/inercia [VERIFICADO probe + in-game]

> Refuta el marco de CAUSA del Addendum 2026-05-30 (que atribuía el bote a hull monolítico/bordes
> afilados como trigger + inercia baja como amplificador). El método de construcción multi-componente
> de ese addendum sigue siendo paridad válida; lo que se corrige es **qué causa el lanzamiento**.

- **Masa/CoM/inercia REFUTADO como trigger [VERIFICADO probe]:** un body con la masa re-sesgada al CoM
  autoritativo del Croco (Y 0.474) + roll inertia ~209 (≈ Croco 215) **botó idéntico** (spd 15.1 en t0.5,
  igual a 3 cifras). El impulso de spawn es ~vertical con masa total constante → por física `v~J/m` es
  independiente de la DISTRIBUCIÓN de masa. La descomposición convexa y el reparto de masa son palancas
  **ortogonales** (SP-019): partir el monolito no mueve CoM/inercia y no detiene el bote por sí solo.
- **El "Izz 350.7 del Croco" era artefacto de masa-uniforme del MLOD** (stripped); la roll inertia real
  del header ODOL es ~215 (SP-019). La comparación "37% del Croco" usaba el artefacto.
- **Causa #1 MEDIDA (FASE 2): la Geometry del chasis SOLAPA el volumen de rueda.** Cada centro de rueda
  (`*_damper_land`) tiene puntos de chasis a 0.16-0.19 m (radio neumático 0.34) vs Croco 0.43-0.46 m
  limpio. El collider de rueda del engine se auto-penetra con el chasis → PhysX eyecta (el mecanismo
  "overlapping objects explode" es real, pero el solape es chasis-vs-RUEDA, no monolito-vs-terreno).
  Arreglado: in-game las ruedas pasan a contactar (`wc` 0→1111 en t0.3).
- **Causa #2 MEDIDA (in-game, side-by-side): placement.** Incluso con #1 arreglado, el LFQuad nace a
  h=−0.264 (origen bajo la superficie) vs Croco +0.216 → ruedas enterradas → eyección. Mecanismo del
  trace **sin resolver** (research 2026-06-01); no afirmar "ECE traza sobre Geometry Y_min" como hecho
  general (matchea el LFQuad pero el Croco +0.216 no encaja).
- **Sigue válido del 2026-05-30:** Geometry = varios componentes convexos cerrados + masa en todos (Croco
  23 chasis + 4 hubs) es **paridad real**, pero es paridad, NO el trigger del bote.

---

## Addendum (2026-06-01) — wheel-well clearance vs radio, cilindro de rueda, diagnóstico de contacto, edit mass-safe [VERIFICADO]

### Check killer: holgura de wheel-well contra el RADIO de neumático (no la caja de hub)

El check viejo "hubs fuera del hull" validaba solo la caja de hub de 8 pts, NO el cilindro de rueda
completo → se le escapó el solape. Check correcto, medible: para cada centro de rueda (`*_damper_land`
centroid), **ningún punto de colisión de chasis (no-hub) puede caer dentro del radio de neumático**
(config `radius`, ~0.34, NO el `wheelHubRadius` pequeño). Target = holgura del referente (radio +
~0.07-0.09 m). [VERIFICADO: LFQuad 0.16-0.19 < 0.34 = solape → bote; Croco 0.43-0.46, 0 dentro;
script `wheel_overlap.py`]. A través del travel: despejar en X (lateral) → el well aguanta cuando la
rueda sube al comprimir.

### La Geometry del `.p3d` de RUEDA debe ser un cilindro ~radio, NO una caja

Una caja con semieje = radio tiene las **esquinas a radio·√2 (+42%)** → collider sobredimensionado y
cuadrado. [VERIFICADO: rueda LFQuad caja, esquinas 0.482 vs config 0.34; Croco cilindro 24-pts, radial
0.340-0.366 uniforme; check: `radial(Y-Z)` desde el centro ≈ radio y uniforme — caja ⇒ max=min·√2;
script `wheel_geo_inspect.py`]. Y el `.p3d` de rueda necesita **ViewGeo + FireGeo** (el Croco los tiene;
un from-scratch suele omitirlos). Construir el cilindro: N-gono en Y-Z (radio) extruido en X (width) →
`scipy.ConvexHull` da caras+normales outward; sel `component01` sobre todos pts/caras; añadir LODs
ViewGeo (6e15) y FireGeo (7e15, sels `component01`+`wheel`). [VERIFICADO: round-trip py3d + binariza
in-game]. La FireGeo de rueda debe llevar material de penetración en sus caras (rubber/metalplate como
el Croco); `material=""` degrada balística/surface (no bloquea spawn/contacto).

### La colisión del referente = descomposición en cajas convexas NO uniformes (no malla fina, no rejilla uniforme, no hull arbitrario)

[VERIFICADO: Croco Geometry = 23 cajas skewed de 8 pts dimensionadas al cuerpo (espina X±0.13, slabs
X±0.66) + 4 cilindros; LFQuad era 27 cajas uniformes axis-aligned; `check_croco_skew.py`]. "Seguir el
contorno" = cajas no-uniformes por región (ancho = ancho real del cuerpo ahí, estrechadas en las
ruedas para los wells) — NO un convex hull del cuerpo (lo engulle: el cuerpo VISUAL llega a X±0.472,
sobre la rueda) y NO descomposición en hulls arbitrarios (inflan/puentean en los guardabarros).
La inclinación (skew) de las cajas del referente es invisible in-game (la colisión no se renderiza) →
no invertir esfuerzo en replicarla; sí en funcional (holgura/radio/contacto).

### Edit de colisión mass-safe: mover puntos, no regenerar

Para abrir wheel-wells sin perturbar la física: **mover los puntos existentes de la Geometry**
(preserva el `#Mass#` per-punto → masa total + CoM EXACTOS); NO regenerar la geometría (regenerar
redistribuye masa → mueve el CoM). [VERIFICADO: reshape moviendo puntos ±X mantuvo masa 1061.5 + CoM
(0,0.627,0.260) exactos; una regeneración por convex-hull movió el CoM 0.260→0.348].

### Diagnóstico de contacto (aísla `contact=0` en UNA corrida)

Loguear `WheelHasContact(i)` por rueda + `WheelCountPresent()` del vehículo Y de un referente que
funciona (Croco) **lado a lado** en la misión de test. `wc=0000` vs `wc=1111` aísla "las ruedas nunca
contactan". Con `wp=0` (sin wheel-item adjunto) el engine igual simula los colliders desde el modelo →
`wc` refleja la salud de la colisión de rueda del modelo. El delta side-by-side (LFQuad −0.264 vs Croco
+0.216 al spawn) señaló el placement de inmediato; "vuela a 38 m" solo no lo señalaba. API: `Car.Cast(o)`,
`WheelHasContact(int)`, `WheelCount()`, `WheelCountPresent()` — `scripts/3_game/vehicles/car.c:297,349,352`.

### Tensión con el item #5 (grosor ≥0.5 m)

El item #5 del checklist 2026-05-30 ("componente de chasis ≥0.5 m de ancho") **choca con los wheel-wells**:
la colisión debe ser ESTRECHA junto a las ruedas para despejarlas. El ≥0.5 m es para colisión-a-velocidad
del cuerpo principal; en la zona de ruedas, estrecho es REQUERIDO. Aplicar #5 al cuerpo lejos de las
ruedas, no a las cajas del wheel-well.

> Origen: LFQuad spawn-bounce 2026-06-01 (bake reshape + cilindro + harness in-game); probes FASE 1/1b/2
> (`LFQuad_dev/_autotest/physics-reference-comparison.md`); handoff
> `30_Sessions/2026-06-01-LFQuad-wheelwell-bake-placement.md`. Cross-ref SP-019 (masa/Izz ortogonal),
> SP-023, Addendum 2026-05-30 (corregido arriba), 2026-05-29 (anatomía wheel proxy Memory).
## 2026-06-02 — Spawn-launch root cause CORRECTED (confirmed in-game, LFQuad)

The earlier "monolithic Geometry / low inertia -> spawn launch" hypothesis (2026-05-30, marked
[verify in-game]) is **refuted**. Confirmed cause of a vehicle that spawns underground and gets
ejected: a stray `#Mass#` tagg on a NON-Geometry LOD (typically FireGeometry 7e15).

- binarize bakes mass from whichever LOD carries `#Mass#`. A FireGeo `#Mass#` of all-zeros makes the
  ODOL ModelInfo `CoM=(0,0,0)`, inertia=0 -> `ECE_PLACE_ON_SURFACE` seats by CoM=0 -> spawns ~0.48 m low
  -> wheels buried -> PhysX depenetration -> ejection.
- The Geometry LOD (multi-component, convex, hubs) was correct the whole time. Proven by bisection:
  Croco-model + LFQuad-Geometry baked CoM 0.627; LFQuad-without-FireGeo baked 0.627. Material,
  mass-distribution, tris-vs-quads, skeleton and the py3d writer were all ruled out by experiment.
- `#Mass#` MUST live only on the Geometry LOD (1e13). py3d emits `#Mass#` on any LOD with a point whose
  `mass != None`. After every assemble, assert `lod.mass` per-LOD: only Geometry `!= None`, rest `None`.
  Fix: `point.mass=None` on non-Geometry LODs (see tools/fix_firegeo_mass.py).
- Placement depends on the baked CoM (`h ~= CoM.y - GeometryYmin`), NOT on Geometry-Ymin / LandContact /
  bbox. No geometry tweak fixes a CoM=0 spawn -- bake the mass first.
- Cross-refs preserved from the fork copy (LL-110 merge 2026-07-06): the Landrover/Bohemia build
  checklist (Addendum 2026-05-30) stays valid as BUILD invariants -- only the "monolith => spawn
  launch" diagnosis is invalidated. Mass-only-Geometry check: `dayz-p3d-audit` SKILL.md (#Mass# must
  live only on the Geometry LOD) + Killer #13. Cross-ref LL-079 (LOD bisection isolated the bug),
  LL-080, LL-081; handoff `30_Sessions/2026-06-02-LFQuad-placement-fix-firegeo-mass-CLOSED.md`.

## (added 2026-06-22) Auditar un vehículo HEREDADO / importado ANTES de planificar

Cuando recibes un vehículo de otro autor (config + model.cfg + p3d) o lo importas de otro juego, audítalo
host-direct ANTES de comprometer un plan — reframea el alcance y es barato. Origen: MercedesAMGLF
2026-06-22 (import de un Mercedes-AMG GT3, v1 de un amigo).

- **MLOD parse del p3d (host-direct, ~60 líneas Python)**: por LOD imprime resolución + nº puntos/caras +
  named selections. Confirma qué LODs / memory points / proxies YA existen. Un p3d "que parece completo"
  puede serlo de verdad (no rehagas la estructura) o tener huecos concretos (fíjalos uno a uno). Tell de
  parse correcto: offset final == tamaño del archivo, y las resoluciones casan con los valores mágicos DayZ
  (Geometry 1e13, Memory 1e15, ViewGeo 6e15, FireGeo 7e15). (Caso: el p3d del amigo tenía 9 LODs + 50
  memory points + proxies de rueda/crew → buen TEMPLATE, no un esbozo.)
- **Audit de vértices de la FUENTE (glTF accessors / FBX) por malla**: el split en proxys es un problema de
  AGRUPACIÓN de mallas bajo el techo (~32768 vértices-normales resueltos por LOD y por proxy), NO de
  decimación. Suma `accessors[POSITION].count` por mesh y agrúpalos. (Caso: 166 mallas / 236k verts; la
  mayor 26.7k —ninguna sola pasa— pero el agregado revienta el techo ×7.)
- **Verificar la SEMÁNTICA de las selections heredadas vs vanilla, no solo su presencia**: un config
  heredado "completo" puede traer bugs funcionales latentes. Contrasta cada selection con cómo la consume
  el engine vanilla:
  - `hiddenSelections`: vanilla usa índices de luz FIJOS (CivilianSedan `dz\vehicles\wheeled\config.cpp:5123-5142`:
    front 0/1, brake 2/3, reverse 4/5, tail 6/7, dashboard 8). Un config que mete `color/glass/interior` en
    0-2 y las luces detrás DESVÍA → riesgo de luces rotas.
  - repostaje: vanilla solo carga la posición si `MemoryPointExists("refill")` y `GetActionCompNameFuel()`
    devuelve `"refill"` (`scripts/3_game/vehicles/transport.c:75-76,313-315`). Un p3d con `fuelpoint` (no
    `refill`) deja la acción de combustible sin posición (cae a 0,0,0).

---

## Addendum (2026-06-24) — proxy-path format + DayZ vehicle axis convention [VERIFICADO vs CivilianSedan + kt_roadkill]

> Two vehicle-general facts pinned during the SUB_BRZ Phase-3 structural pass. Apply to ANY DayZ vehicle,
> not just source-game imports.

### MLOD proxy selections carry NO `.p3d` extension

A proxy selection is `proxy:<path>.<NNN>` (3-digit index) where `<path>` has **no `.p3d` suffix** — the
engine appends `.p3d` when it resolves. VERIFIED on vanilla (`proxy:\dz\vehicles\wheeled\civiliansedan\
proxy\sedanwheel.001`) and on the shipped kt_roadkill mod (`proxy:kt_roadkill_scum\proxy\..._wheel.001`).
Writing `...sedanwheel.p3d.001` makes the engine look for `...sedanwheel.p3d.p3d` → **proxy not found → that
attachment/geometry silently missing in-game** (wheels don't simulate, body proxy chunks invisible). It is a
silent failure: offline editor/py3d checks still "see" the proxy selection. ALWAYS author proxy paths
without the extension. py3d `add_proxy(path, index, ...)` → pass `path` without `.p3d`.

### Pure-geometry body-proxy TRIANGLE FRAME — py3d "identity" != engine identity [VERIFIED in-game 2026-06-24, MercedesAMGLF AC1.4 PASS]

A pure-geometry proxy (body chunk / engine / interior / dash — 1 visual LOD, no config class) renders its
referenced geometry transformed by the frame the engine derives from the proxy TRIANGLE. MODEL-SPACE geometry +
the right triangle = the chunk overlays the shell exactly. Two traps, both bit MercedesAMGLF:

- **Geometry MODEL-SPACE, not centered.** Author each chunk at its real car position (vanilla `prox_int`
  Y[0.36,1.56] cabin, `sedan_engine` Z[-2.30,-1.12] front — measured by debinarizing the vanilla proxy `.p3d`).
  Re-centering each chunk to the origin makes the engine pile them all AT the origin.
- **Triangle frame MUST be `R=((-1,0,0),(0,0,1),(0,1,0))`, NOT py3d's "identity".** That is the value
  `py3d.derive_proxy_frame` returns for vanilla `prox_int`/`sedan_engine` AND kt_roadkill `_body`/`drivewheel`.
  py3d's `canonical_proxy_triangle(rotation=None)` ("identity") produces a triangle the ENGINE RENDERS
  ROTATED ~90 deg — it passed every offline check yet failed in-game twice. Author with:
  `lod.add_proxy(path, index, origin=(0,0,0), rotation=((-1,0,0),(0,0,1),(0,1,0)), scale=0.1)` (path WITHOUT `.p3d`).

GATE: for proxies the offline frame/render is NOT a valid acceptance gate (false-green twice on MercedesAMGLF) —
the gate is the in-game spawn+render; offline only rules out gross errors (missing selection, duplicate `.p3d`).
Attachment proxies (wheel/crew/door) are placed by physics/config, not the triangle — their `pos` is NOT a
reference for pure-geometry placement.

### DayZ vehicle axis convention: front = −z, driver = +x

Measured on CivilianSedan v54 (the CONTROL): headlights/engine/`drown_engine` at **z ≈ −1.7..−2.4** (front),
reverse light/exhaust/`refill` at **z ≈ +2.2..+2.6** (rear), `seat_driver` at **x = +0.436** (driver on
+x). So a DayZ car FACES −z. Wheel naming `wheel_<side>_<axle>`: side 1 = +x, side 2 = −x; axle 1 = front
(−z), axle 2 = rear (+z) — front (steered) wheels are `_X_1`. When importing from a tool whose cars face +z
(source-game, most), the correct transform flips z; a car that "looks rotated 180°" relative to the source is
usually CORRECT — verify against CivilianSedan markers (a static render cannot show a front/back swap), do not
refactor on sight.

### `validate()` ERR_COMPONENT_NAMING is a false-positive for vehicles

Vanilla vehicle Geometry LODs use **lowercase `component01`** (CivilianSedan does, and it works) — the
py3d/audit "engine requires `Component01` uppercase" rule is for Inventory_Base items. Match vanilla
(lowercase) for vehicles; the resulting `ERR_COMPONENT_NAMING` from `P3D.validate()` is expected (the CONTROL
itself triggers it).

## Addendum (2026-06-24 s7) — componentNN DUAL-TAG: hub/seat selections must SHARE faces with a componentNN [VERIFIED in-game, was the SUB_BRZ spawn blocker]

The LOD tables above list `componentNN` + `wheel_X_Y_damper_land` + `seat_driver`/`seat_codriver` as if they were
independent selections. They are NOT independent: **the engine enumerates collision/action components ONLY by
`componentNN`**, so a hub/seat selection whose faces are in NO `componentNN` (a standalone island) is invisible to
the component pass and entity creation FAILS:
- `PHYSICS (E): Won't simulate, wheel wheel_1_1_damper_land has no proper selection in geometry`
- `PHYSICS (E): Action selection 'seat_driver' was not found in view or fire geometry level of model when parsing class Crew::Crew`

REQUIREMENT (Bohemia wiki "Object must be named ComponentXX"): each hub/seat box carries BOTH names on the SAME
faces — `wheel_X_Y_damper_land` AND a `componentNN` (Geometry); `seat_driver`/`seat_codriver` AND a `componentNN`
(ViewGeo, plus Geometry if seats live there). The hub IS component0N; the seat IS component0M. This is the SAME
dual-tag a FireGeo already does for `dmgzone_*` + `componentNN` on one box — extend it to the Geometry hubs and the
ViewGeo/Geometry seats.

THE DISCRIMINATOR (add to verify_<mod>.py): for each hub/seat selection, the % of its faces also covered by a
`componentNN` in the same LOD. Working cars = **100%** (CivilianSedan 15/15, kt_roadkill 15/15, LFQuad 60/60); the
SUB_BRZ that would NOT spawn = **0/12**. 100% = pass; anything else = the spawn blocker.
```python
def component_overlap(lod, sel_name):  # returns 1.0 when ok
    comp = {tuple(sorted(v.point_index for v in f.vertices))
            for n in lod.selections if n.lower().startswith("component")
            for f in lod.selections[n].faces}
    tf = [tuple(sorted(v.point_index for v in f.vertices)) for f in lod.selections[sel_name].faces]
    return sum(k in comp for k in tf) / len(tf)
```
Why it survives many "the selection is present and parity-correct" cycles: everyone checks PRESENCE; nobody checks
the componentNN face-OVERLAP. Offline parity ≠ drivable — this is one more thing only the in-game spawn gate (or
this overlap check) catches. The s2 candidate deltas (hub 16pt-vs-8pt-box, seats-in-Geometry) were RED HERRINGS:
a box hub is a valid component, seats-in-Geometry is fine (LFQuad does it) — once they are ALSO componentNN.

> Origen: SUB_BRZ spawn blocker resolved in-game 2026-06-24 s7. Builder fix `rip_p3_structural.py` (dual-tag) +
> deployed-p3d patch. Cross-ref `rip-import.md` "RESOLVED" addendum.

---

## Addendum (2026-06-25) — ATTACHMENT proxy needs a companion BONE-NAME selection (py3d add_proxy omits it) [VERIFIED vs CivilianSedan + kt_roadkill; in-game test PENDING]

An **attachment** proxy (crew / wheel / door — i.e. one the engine binds to a skeleton bone, NOT a pure-geometry
body chunk) needs TWO things in the LOD, not one:
1. the `proxy:<path>.<NNN>` selection + triangle (what `py3d LOD.add_proxy` creates), AND
2. a **companion NAMED SELECTION whose name IS the bone name** (`crewdriver`, `crewcodriver`, `wheel_1_1`,
   `wheel_2_1`, `wheel_1_2`, `wheel_2_2`, `doors_driver`, `doors_codriver`, `radiator`, …), carrying the **SAME
   3 points + 1 face** as the proxy. This is the proxy→bone binding Object Builder writes when you "name" a proxy.

`py3d add_proxy` creates only (1). Without (2) the engine reports, at `Load entity type`:
- `PHYSICS (E): Proxy with bone name 'crewdriver'/'crewcodriver' was not found in view geometry level of model`
  → crew not set up → `CrewPositionIndex` returns -1 → **get-in action never appears** (the cursor hits the seat
  component but the crew position isn't registered).
- `PHYSICS (W): Proxy with name 'CivSedanWheel_1_1'..'2_2' was not found in FireGeometry of the shape` (the wheel
  attachment can't find its hub proxy).

**Pure-geometry body-chunk proxies do NOT need (2)** (no bone) — that is why they resolve with zero error while the
crew/wheel proxies fail; do not be misled into thinking py3d proxies are universally broken.

VERIFIED — both working models bind every attachment proxy this way, in **ViewGeo AND FireGeo**:
```
# CivilianSedan & kt_roadkill ViewGeo+FireGeo non-proxy selections that share points with a proxy:
crewdriver   -> crew_driver.001    crewcodriver -> crew_cargo.001
wheel_1_1 -> sedanwheel.003  wheel_1_2 -> sedanwheel.004  wheel_2_1 -> sedanwheel.001  wheel_2_2 -> sedanwheel.002
doors_driver -> sedandoors_driver.001   doors_codriver -> sedandoors_codriver.001   radiator -> radiator_car.001
```
The wheel **bone name maps by POSITION** (`wheel_<side>_<axle>`, side1=+x/2=−x, axle1=front=−z/2=rear=+z), NOT by the
proxy index. The bone names must also exist in `model.cfg` `CfgSkeletons skeletonBones[]` (SUB_BRZ already declares
`crewdriver`/`crewcodriver`/`wheel_*`).

DISCRIMINATOR / verifier (add to `verify_<mod>.py`): for each attachment proxy, assert a same-points companion
selection named after its bone exists. SUB_BRZ had **0** bone selections (only the 4 occlusion components + 2 seats);
CivilianSedan/kt have the full set. Builder: `rip_p3_structural.py` must, after each crew/wheel `add_proxy`, create
the bone selection (see `VehicleImport\tools\patch_proxyframes_crew.py` `_ap`, 2026-06-25: `add_proxy(rotation=R,
scale=1.0)` + point-flags 63 + bone selection from the proxy's faces/points).

GATE: as with every proxy finding here, offline checks gave FALSE-GREEN 4 times on SUB_BRZ (occlusion / frame / scale
/ flags) — the only valid gate is the in-game RPT (the `bone name not found` line gone). This bone-selection fix is
**CONFIRMED in-game on SUB_BRZ (2026-06-25, s8)**: re-spawn via dayz-mcp → server RPT has ZERO `PHYSICS (E/W)` lines
(all `bone name not found` / `no proper selection` gone). BUT this only fixes get-in **gate-1** (`CrewPositionIndex`);
**gate-2 (`CrewCanGetThrough`) needs the car to run as an Enforce Script CLASS, not bare `CarScript`** — a ripped racing-game car
config `class <MOD>: CarScript` with no `.c` runs as bare CarScript whose `CrewCanGetThrough` returns false (base
`Transport` stub) → get-in still never appears. See `rip-import.md` s8 addendum "GET-IN ROOT CAUSE #2".

**Separate, do not conflate with get-in:** (a) the user insists DOORS must open/close first or get-in won't show —
investigate `CarScript.CrewCanGetThrough`/`IsAreaAtDoorFree` + whether get-in needs CarDoor **attachments** (SUB_BRZ
has none; doors are baked into body chunks). (b) get-in's `CanReachSeatFromDoors` (`carscript.c:2710`) uses the
`seat_con_X_Y` **memory point** + player within 1.0 m, NOT the physical door attachment.

> Origen: SUB_BRZ get-in/actions debug 2026-06-25 s8 (handoff `SUB_BRZ_dev\reviews\2026-06-25-prompt-next-session-proxys-actions-doors.md`). Cross-ref `rip-import.md`.


---

## Addendum (2026-06-25) — GET-IN ROOT CAUSE #2: a custom CarScript vehicle needs an Enforce Script CLASS, not just geometry [VERIFIED in-game on SUB_BRZ 2026-06-25 + vs vanilla/FC source]

> Project-agnostic. Applies to ANY DayZ ground vehicle declared `class <MOD>: CarScript` with no `.c` script
> class — source-game/OBJ/Blender imports, cars/trucks/quads authored from scratch. This is the get-in blocker that
> survives a perfectly parity-correct model (every LOD, every selection, every memory point present). The two
> proxy-side gotchas above (componentNN DUAL-TAG, ATTACHMENT proxy BONE-NAME) fix gate-1 of get-in; THIS fixes
> gate-2 and is independent of geometry. **MERCEDES_AMGLF will hit this same wall** — at this date its
> `MERCEDES_AMGLF_Base.c` overrides only vitals + `OnDebugSpawn` (0 of the 3 required overrides).

### Symptom

The vehicle spawns, renders and collides, but the "Get in" / Entrar action NEVER appears in the action menu.
No RPT error by itself (the action is silently filtered inside its `ActionCondition`). Telemetry tell: the
reported `class_name` stays at the base `"CarScript"` instead of your `"<MOD>_Base"` — the override class never
attached because there is no script module compiling it.

### Cause — the two-gate ActionCondition + the unoverridden base stub

`ActionGetInTransport.ActionCondition`
(`scripts/4_world/classes/useractionscomponent/actions/interact/actiongetintransport.c:51-66`) has TWO gates
that BOTH must pass:
1. gate-1 `CrewPositionIndex(componentIndex) >= 0` — needs the crew proxy bone selection (the "ATTACHMENT proxy
   BONE-NAME" addendum above); and
2. gate-2 `trans.CrewCanGetThrough(crew_index)` (~:63), then a reachability loop
   `CanReachSeatFromDoors(selections[i], player.GetPosition(), 1.0)` (:71-77).

`CrewCanGetThrough` is **NOT overridden by `CarScript` or `Car`** — only by the concrete vanilla car classes
(`CivilianSedan` etc.). A vehicle running as **bare `CarScript`** falls to the base stub
`Transport.CrewCanGetThrough` (`scripts/3_game/vehicles/transport.c:493-500`), which returns **false** in the
normal build (`#ifndef CFGMODS_DEFINE_TEST`) → gate-2 false → get-in never appears, no matter how perfect the
crew bone is. The same trap hits `GetSeatAnimationType` (`transport.c:475-479` → `Error("not implemented")`) and
`GetAnimInstance` (used in `ActionGetInTransport.Start`), both of which also `Error()`/false in the base.

### Fix — ship a thin `<MOD>_Base.c` script class (PIPELINE requirement; for an import pipeline add to the config/script phase)

Minimal M1 set (the three are mandatory; door mappers / `CanReach*` / `GetSeatIndexFromDoor` /
`GetAnimSourceFromSelection` are M2 — needed for openable doors and seat-switching, not for entering+driving).
Signatures verbatim from `CivilianSedan` (`scripts/4_world/.../civiliansedan.c:85,95`):

```c
class <PREFIX>_Base extends CarScript
{
    override int GetAnimInstance()                 { return VehicleAnimInstances.SEDAN; }       // civiliansedan.c:85
    override int GetSeatAnimationType(int posIdx)                                               // civiliansedan.c:95
    {
        switch (posIdx) { case 0: return DayZPlayerConstants.VEHICLESEAT_DRIVER;
                          case 1: return DayZPlayerConstants.VEHICLESEAT_CODRIVER; }            // add PASSENGER_* per seat
        return 0;
    }
    override bool CrewCanGetThrough(int posIdx)    { return posIdx == 0 || posIdx == 1; }       // M1 ungated; gate on door-state at M2
    // MODEL must carry memory points seat_con_1_1 / seat_con_2_1 + a crew config with seat_driver / seat_codriver.
    // M2 (openable doors / seat-switch): GetCarDoorsState, door-slot mappers, CanReach*, GetSeatIndexFromDoor, GetAnimSourceFromSelection.
}
```

The mod needs a `CfgMods` script module (`worldScriptModule files[]`) so the `.c` compiles. Pattern confirmed on
the shipped community mod **FC ("Frontera Cars")**: `FC_*_Base extends CarScript` directly (config
`class FC_Vaz_2101: CarScript`, FC_Options/.../FC_Vaz_2101/config.cpp:514) — FC cars do NOT re-parent to a vanilla
car; they override `CrewCanGetThrough`/`GetSeatAnimationType`/`GetAnimInstance` + the M2 door methods themselves.

### Geometry requirement (verified) — `seat_con_*` memory points

`CarScript.CanReachSeatFromDoors` (`scripts/.../carscript.c:2710-2731`) calls
`GetDoorConditionPointFromSelection` → `if (MemoryPointExists(conPointName))` and only then compares distance
≤ 1.0; if the memory point is absent it returns false → action filtered. The base maps `seat_driver`→`seat_con_1_1`,
`seat_codriver`→`seat_con_2_1` (`carscript.c:2674`), so NO override is needed for the mapping, but the model MUST
carry the memory points `seat_con_1_1`/`seat_con_2_1`, positioned so the player is ≤ 1.0 m away when facing the
door/seat. The `crew` config must expose `seat_driver`/`seat_codriver`.

### Doors are NOT required for get-in

`GetCarDoorsState` returns `DOORS_MISSING` when no `CarDoor` attachment exists (`civiliansedan.c:178-181`,
FC unknown_40493.c:982-985), and `DOORS_MISSING != DOORS_CLOSED` → `CrewCanGetThrough` passes. A script class with
NO door attachments gives WORKING get-in (baked doors stay static). Openable doors are a SEPARATE feature (`CarDoor`
classes + door proxies + door `.p3d` + `AnimationSources DoorsX` + model.cfg door bones), exactly as FC ships
(FC_Vaz_2101 `class FC_Vaz_2101_Door_Driver: CarDoor`, config.cpp:326; `AnimationSources class DoorsDriver` :843).

### In-game tell after the fix

Telemetry reports the custom class (`class_name:"<MOD>_Base"` instead of `"CarScript"`) AND "Get in" appears.
As with every finding here, offline checks cannot prove get-in — the gate is in-game.

> Origen: SUB_BRZ s8 2026-06-25 (in-game RPT grep + telemetry + Mercedes↔BRZ contrast subagent, verified against
> vanilla `actiongetintransport.c`/`transport.c`/`carscript.c`/`civiliansedan.c` + the shipped FC mod). Cross-ref
> the two proxy addenda above (componentNN DUAL-TAG = gate-1 component; ATTACHMENT proxy BONE-NAME = gate-1 crew
> bone) and `rip-import.md` s8 "GET-IN ROOT CAUSE #2". MERCEDES_AMGLF: same trap pending (its `_Base.c` has 0
> of the 3 required overrides).

## Addendum (2026-06-25) — verification = validate against the CONTROL, not assert blind; damper/steering are NOT universal [VERIFIED vs CivilianSedan MLOD]

A verifier whose expected values are hardcoded (even when comments cite "sedan") is a false-green
risk: it asserts the producer's internal consistency, not the engine contract. Fix = a **positive
control**: run the UNIVERSAL subset of checks against a known-good vanilla car (`CivilianSedan`
debinarized MLOD) and require it to PASS. If the sedan fails a "universal" check, the contract is
wrong, not the car. Tool: `VehicleImport\tools\verify_rip_car.py --positive-control <sedan_mlod.p3d>`.

What the positive control CAUGHT and corrected — both `verify_amglf.py` and `verify_brz.py` had it:
- They asserted `wheel_X_Y_damper` / `wheel_X_Y_damper_axis` and `wheel_X_1_steering` / `_steering_axis`
  as **Memory-LOD universal** selections. **The vanilla sedan has NONE of them in Memory.** It uses a
  `susp_arm_*` linkage (double-wishbone) with `susp_arm_steering_X_1_axis` for steering, and keeps
  `wheel_X_Y_damper_land` in the **Geometry** LOD (the hub), not Memory. The simple
  `wheel_X_Y_damper`/`wheel_X_1_steering` scheme is a friend/import convention, NOT vanilla contract.
- TRUE universal wheel contract (sedan-verified): `wheel_X_Y_axis` in Memory + `wheel_X_Y_damper_land`
  in Geometry, each 100% inside a `componentNN` (see the componentNN dual-tag addendum). Damper/steering
  selection NAMES are per-car/per-skeleton (model.cfg) → POLICY tier, not universal.
- ACTION for the Mercedes project: reclassify those two checks in `verify_amglf.py` (they pass today
  only because the friend body carries them, not because they are contract).

Run-before-closed gates (block, don't skip): `verify_rip_car.py --self-test` (non-tautology proof,
catches the 0/12-componentNN blocker), `--positive-control <sedan>` (contract satisfiable),
target hard-pass, `roundtrip_writer.py` (py3d write fidelity). Never close a phase on a metric that is
0.000/100% by construction (R22 tell).

---

## Addendum (2026-06-25b) — reusable verification harness for ANY car (generic vs source-game-specific split)

The rip→DayZ build grew a verification harness in `VehicleImport\tools\`. The GENERIC pieces apply to ANY DayZ
vehicle (procedural / OBJ / glTF too), the rest are PATTERNS to re-point. Use them as run-before-closed gates
that BLOCK, not optional steps — skippable verification is how the offline false-green happened. All green
offline 2026-06-25; build-time wiring is HELD until the SUB_BRZ script-class Cowork session closes.

GENERIC (wire these for any car, not just source-game):
- `verify_rip_car.py` — tier-**U** universal engine contract + per-car `POLICY` dict (dmgzone list,
  body-proxy naming, mod token). `--positive-control <CivilianSedan_mlod.p3d>` proves the contract is
  satisfiable; `--self-test` proves non-vacuity. Add a POLICY entry per new car instead of forking a
  `verify_<mod>.py` (the per-car `verify_amglf.py`/`verify_brz.py` are superseded).
- `visual_gate.py <p3d> <out_dir>` — Blender-headless N-angle render + `blender-visual-review` checklist +
  unresolved-proxy inventory. CAVEAT (s20 2026-07-02): it does NOT reproduce the engine cull — the engine
  renders the ANTI-cross side and shades with the STORED MLOD normals, while Blender no-normals + backface
  culling shows the +cross side (the exact opposite); and it does NOT resolve body-split proxy chunks
  (they are inventoried, not rendered). Use it only for geometry presence / silhouette / proxy inventory;
  winding and see-through verdicts are IN-GAME ONLY. Works on any `.p3d`. Needs Blender 5.1 (`BLENDER` env).
- `roundtrip_writer.py` — py3d read→save→read fidelity (the LFInfectedBig skinned-export corruption class).
- `_harness_util.py:clean_visual_shell` — reconstruct a runnable shell-only `.p3d` from a deployed full one.

PATTERN (bound to a builder/transform — re-point for a non-ripped racing-game car):
- STRUCTURAL BISECTION (`roundtrip_structural.py`): feed YOUR structural builder the CONTROL (CivilianSedan
  shell + locators from its own memory points) and require the regenerated LODs to pass the UNIVERSAL subset.
  Run a NEGATIVE control too (break the invariant — e.g. disable the hub/seat componentNN dual-tag) and require
  the bisection to CATCH it: that proves it tests the BUILDER and is non-tautological (would have caught the s7
  0/12 blocker offline). Requires the builder exposed as `build_structural(profile)` (parametrized shell /
  locators / mass / bbox-source / out), not a hardcoded script.
- TRANSFORM FIT (`fit_transform.py`): fit the source→DayZ transform from anchor pairs, confirm it is a pure
  sign-flip+offset, and PERTURB it (wrong sign / offset / scale) to prove the residual discriminates — a
  self-built pair gives residual 0.000 by construction (R22 tell), so the discrimination test is what makes it
  real, not the residual.

source-game-specific implementation + the MANDATORY-gates spec: `rip-import.md` §"Generalized harness".

> Origen: rip→DayZ verification-harness session 2026-06-25 (`VehicleImport\tools\`; HARNESS_HANDOFF.md). Closes
> the verifier-only gap: the harness now also bisects the BUILDER and rule-fits the transform, both proven
> non-tautological. Cross-ref the Addendum 2026-06-25 above (positive control) and rip-import.md s7/s8 lessons.


---

## Addendum (2026-06-27) — Crew get-in: dedicated seat components + canonical crew-proxy triangle [VERIFICADO in-game: LFQuad D34 + MercedesAMGLF]

The "Get in" radial and the seated player are governed by TWO ViewGeometry structures that procedural / regen body pipelines get wrong by default. Both blocked LFQuad (~7 days, resolved 2026-06-05 "Bloque A — Crew" D34) and MercedesAMGLF (2026-06-27). Symptom: the driver works but the **codriver radial never appears**, and the seated player sits sideways/backward or mis-placed.

### 1. Get-in appears for driver but NOT codriver (raycast "always driver")

DayZ resolves the seat with **`Transport.CrewPositionIndex(componentIdx)`** (proto native, `P:\scripts\3_game\vehicles\transport.c:116`) over the **collision component the cursor raycast HITS in the ViewGeometry LOD** (`ObjIntersectView`, `dayzphysics.c:88`; consumed at `actiongetintransport.c:50-51`) — NOT by memory-point proximity. So each seat needs its OWN dedicated, clean, closed-convex component:

- `seat_driver` = 1 dedicated `ComponentNN` (its own cube); `seat_codriver` = 1 dedicated `ComponentNN`. Dual-tag: the seat selection and its `ComponentNN` share the SAME faces (100% overlap).
- Seats painted across a multi-component grid -> the raycast never lands cleanly on the 2nd seat -> "always driver". (LFQuad N1.5: `seat_driver/codriver` spread over 88/112 points across ~23 components -> codriver never appeared.)
- References: vanilla CivilianSedan `seat_driver`=component31 / `seat_codriver`=component32 (one each); Croco one each.
- **FIX (LFQuad + Mercedes):** replace with 2 dedicated seat-cube components — each a clean closed box (8 verts, 12 tris, ALL faces outward) tagged `seat_X` + its own `ComponentNN` on the same faces.

Closed-car note (Mercedes): a closed car does NOT need the full body shell in ViewGeo — 2 dedicated seat cubes + wheel/crew proxies suffice. A solid body box (e.g. a central "spine") only OCCLUDES the seat cubes (cursor hits the spine first -> no seat hit) -> remove it. LFQuad/vanilla keep a shell only because they are open / have window openings.

### 2. Seated player sideways/backward/mis-placed, and proxy translations "don't move" him

Seated position AND orientation come from the **crew-proxy triangle** (`crewdriver`/`crewcodriver`, present in ViewGeo AND FireGeo), NOT from `pos_driver`/`pos_codriver` memory points. Two traps:

- **Triangle SHAPE must be CANONICAL = 3 distinct angles.** `origin + e1 + e2` with edge lengths ~1.0 and ~2.0 (angles 90 / 63.4 / 26.6). An isosceles 90/45/45 triangle = AMBIGUOUS frame (the proxy angle-sort rule ties -> orientation rotates differently per seat). A TINY triangle (py3d `add_proxy(scale=0.1)` -> edges ~0.05) is below the engine's frame-derivation threshold -> player mis-placed AND **translating the proxy has little/no visible effect** (the "I moved it and nothing happened" symptom on MercedesAMGLF). Make it canonical and translations respond.
- **FRAME (facing) depends on e1/e2 AND the model's base orientation.** Model facing -z (vanilla convention) -> SUB/vanilla use `e1=(0,0,1), e2=(0,2,0)` -> `R=((-1,0,0),(0,0,1),(0,1,0))`. A model yaw-rotated 180 deg (e.g. a source-game import reoriented in a later phase, like MercedesAMGLF) needs `e1=(0,0,-1)` -> `R=((1,0,0),(0,0,-1),(0,1,0))` to face forward. Replicate a KNOWN-GOOD same-orientation reference; do NOT copy a frame cross-model without recomputing. Practical tell: with the canonical triangle, +z moved the Mercedes player FORWARD (its forward is -z after the 180 deg yaw) — establish the sign empirically once, then it is exact.
- **The triangle ORIGIN (v0) anchor sets the seated HEIGHT + longitudinal position** — not the memory point. Translate all 3 verts together; use ~15 cm steps (small steps read as "no change"). A low sports-car roof may clip the standing pose regardless (inherent; not fixable from the .p3d).

### Builder fix (so future cars never hit this)
source-game/regen builders create crew proxies via `add_proxy(..., scale=0.1)` -> tiny ambiguous triangles, and may paint seats over the collision grid. Change crew-proxy creation to emit the **canonical triangle (edges ~1.0/2.0, 3 distinct angles)** with the model-correct frame, in BOTH ViewGeo and FireGeo, and build seats as **2 dedicated clean cubes** (one ComponentNN each) from the start.

> Origen: LFQuad "Bloque A — Crew" D34 (`30_Sessions/2026-06-05-LFQuad-crew-resuelto-postura.md`, in-game confirmed) + MercedesAMGLF get-in/seated-pose (2026-06-27). Cross-ref: `CrewPositionIndex` transport.c:116, `ActionGetInTransport.ActionCondition` actiongetintransport.c:50-73, `CanReachSeatFromDoors` carscript.c:2710. The earlier "codriver needs crew proxies in FireGeo" diagnosis was REFUTED — the cause is collision-component cleanliness + canonical proxy, not FireGeo presence.

### CRITICAL EXTENSION (2026-06-28, SUB_BRZ — in-game CONFIRMED): seat ComponentNN cubes must be INWARD-wound + point flags `0x02000000`, or they are NOT raycast-collidable

The "2 dedicated clean cubes, all faces outward" rule above is NECESSARY BUT NOT SUFFICIENT for a py3d-authored vehicle. A seat cube with **OUTWARD winding + point flags 0** is **invisible to `DayZPhysics.RaycastRV(..., ObjIntersectView)`** — the get-in action-target raycast never resolves it, so `CrewPositionIndex` falls back to component0 and the **codriver radial never appears** (the driver "works" only by that fallback; even the driver cube isn't truly hit). The crew mapping `CrewPositionIndex(comp)->crewIdx` is already correct (comp0→driver, comp1→codriver) — irrelevant while the geometry isn't raycast-collidable.

Measured (SUB_BRZ vs LFQuad positive control, headless probe): BRZ seat cubes were OUTWARD + flags 0 → `RaycastRV` `hit=0` from every direction at the exact cube center. The working LFQuad/Croco control seat ComponentNN are **INWARD-wound (every face) + every point flag = `0x02000000` (33554432)**. After rebuilding the BRZ ViewGeo seat ComponentNN with **inward winding + point flags 0x02000000 copied from the positive control** (not just shape/name), `RaycastRV` returns `hit=1 comp=1 crewIdx=1` and the codriver get-in works **in-game (confirmed 2026-06-28)**.

**Rule:** build ViewGeometry collision ComponentNN for vehicles (seats, and any cursor/action-targetable component) by COPYING the positive control's convention — **inward winding + point flags 0x02000000** — not py3d's default outward+flags0. Outward py3d boxes pass every offline shape/winding/dual-tag check yet are NOT raycast-collidable. The MercedesAMGLF (same sparse outward-box ViewGeo) has the SAME open codriver blocker → apply this fix there too.

**Diagnostic (reusable, no manual aim):** a headless mission probe that spawns the car + a known-good control, dumps `CrewPositionIndex(0..79)`, and casts `DayZPhysics.RaycastRV` (FIRE+VIEW) at each seat — localizes "mapping vs raycast vs collidability" in one run. Pattern files: `C:\tmp\brz_crew_probe_init.c` + `brz-crew-probe-run.ps1` (SUB_BRZ 2026-06-28). Parse the raw `hit=1 comp=N crewIdx=N` lines, NOT a boolean verdict — a regex `-match '1'` also matches `-1` (false-green observed this session).

> Origen: SUB_BRZ codriver get-in, root cause confirmed in-game 2026-06-28 (Claude diagnosis via headless crew-probe + Codex implementation). Applies to ALL source-game/py3d-built vehicle ViewGeo; same fix pending on MercedesAMGLF.

### MercedesAMGLF CONFIRMATION + refinements (2026-06-28 s12) — the seat winding+flags fix CONFIRMED on a 2nd car

The CRITICAL EXTENSION above is now CONFIRMED on MercedesAMGLF (headless crew-probe: codriver VIEW ray from its door side -> `hit=1 comp=6 crewIdx=1`; driver -> `hit=1 comp=5 crewIdx=0`). Three refinements from applying it to a CLOSED car (cite: MERCEDES s11/s12 + LFQuad D34 + SUB_BRZ s9):

- **Apply it MINIMALLY when the seat ComponentNN already map.** If the ViewGeo seats already enumerate as their own ComponentNN with the correct crew mapping (verify with the get-in diag PROBE / crew-probe `CrewPositionIndex(comp)`), do NOT rebuild the whole ViewGeo (SUB_BRZ rebuilt all ~23 components). Flip ONLY the seat ComponentNN faces in-place to inward winding + set their point flags to `0x02000000`, recomputing each face normal from the new (inward) order. This preserves the verified component indices/positions and the seat<->componentNN dual-tag. Mercedes: only `seat_driver`=Component06 / `seat_codriver`=Component07 changed; body components left untouched; `verify_amglf.py` stayed 35/35.

- **"Body shell in ViewGeo / high-index seats" is a RED HERRING for the codriver blocker.** MercedesAMGLF s11 added 5 body occlusion components + moved seats to high indices (idx 5/6) on the theory that the engine "could not discriminate 2 bare cubes" -> the codriver STILL failed. The real and ONLY cause was winding+flags (proven s12). Confirms + sharpens the 2026-06-27 closed-car note: a closed car needs NEITHER a body shell NOR high-index seat placement in ViewGeo -- just the 2 seat cubes, inward-wound + point-flagged. Leave any body occlusion components OUTWARD + flags 0 (inert, non-raycast-collidable -> cannot occlude the seat ray). Do not chase the "give the ViewGeo a body" lever; chase winding+flags.

- **Crew-probe seat anchor: aim at `pos_driver`/`pos_codriver` memory points (engine space) -- but ONLY if they sit inside the seat cube.** `c.GetMemoryPointPos("pos_driver")` returns ENGINE-space coords, sidestepping the py3d->engine sign flip (Mercedes engine driver = +x, py3d driver = -x). Mercedes pos_driver/codriver are y~0.78, INSIDE the seat cubes -> aim there directly (no height-raise). CAVEAT for the positive control: a VANILLA car's `pos_driver` is the door-sill ENTRY point (CivilianSedan: y~0.07, x~+-1.4), NOT the seat center -> a ray aimed there hits the body (comp=-1), giving a FALSE "control failed". For a positive control, anchor at the seat ComponentNN centroid, or use a car whose `pos_X` is at the seat (LFQuad). The target's result is self-validating when its rays hit the real seat comps.

- **Mercedes crew-probe tooling** (reusable, no manual aim): `mercedes_crew_probe_init.c` (spawns target + control near player; DumpTable `CrewPositionIndex` + RaycastRV VIEW+FIRE per seat from +-x/+-z) + `mercedes-crew-probe-run.ps1` (injects the probe into the PROJECT-LOCAL `<Mod>_dev\_server\mpmissions\...\init.c` -- NOT the shared DayZServer mission; launches detached, polls the server `script.log` for `[CREW-PROBE]`, restores the original init.c in `finally`). Parse the raw `hit=N comp=N crewIdx=N` integers, never a regex `-match '1'` (it also matches `-1`). Build-only PBO for the probe: `dayz-test.ps1 -Build` ALWAYS launches (no build-only flag) -> replicate its AddonBuilder call directly (`<src> <target> -prefix=<Mod> -temp=<FRESH_DIR> -packonly`); a FRESH `-temp` gives a clean sync AND dodges the sandbox `Remove-Item` guard (false-positives when `C:\Program` appears in the same command).

> Origen: MERCEDES_AMGLF s12 (2026-06-28, copiloto get-in confirmed headless via crew-probe). Applies the SUB_BRZ CRITICAL EXTENSION to a closed car; corrects the s11 "give the ViewGeo a body / high-index seats" theory (red herring). Cross-ref MERCEDES_AMGLF_dev\HANDOFF.md s12.

---

# Appendix — REGEN-FROM-glTF + GET-IN RADIAL / LOD ladder (sectioned from SKILL.md)

> Extracted from dayz-vehicles/SKILL.md 2026-07-07 (F3).
>
> These two blocks are structural parity for imported/regen bodies and belong with the parity method (this file is their declared source of truth). Moved verbatim from the core SKILL.md; the core now points here.

## REGEN-FROM-glTF BODY + PROXY-SPLIT (added 2026-06-24)

Regenerating a high-poly body from a glTF/FBX and splitting it into proxies to beat the 65535
resolved-vertex ceiling (the MercedesAMGLF GT3 path) has two traps that pass every offline gate and
only surface in-game. Origin: MercedesAMGLF Fase 2 smoke, 2026-06-24.

### glTF→DayZ winding: the offline check can be a tautology
The transform `DayZ=(-s·bx,+s·bz,-s·by)` has `det=-1` (a mirror) and flips face handedness. A winding
check that compares the post-transform geometric normal against the post-transform **declared glTF
normals** is **tautological** — the winding was reversed precisely to make them agree, so it reports
~0.00% flipped by construction (the R22 "0.000" tell). It proves internal consistency, not that DayZ
renders the texture outward. DayZ backface-culls by **winding**; the mirror-compensating reverse left
the front face pointing inward, so the body rendered see-through (texture on the interior) in-game.
Fix confirmed in-game: do NOT reverse — keep the glTF vertex order (`reverse_winding=False`). The
offline winding check must validate against the DayZ convention or against a reference model known to
render correctly, never against the normals you picked to match.

### proxy placement: an identity frame does not mean the geometry is aligned
A proxy `proxy:\...\X.p3d.NNN` is a tiny triangle whose engine-derived frame (angle-sort, computed by
`py3d.derive_proxy_frame` = the engine's rule per `dayz-proxy-align`) can be **identity-perfect**
(det +1, unambiguous, angles 90/63.4/26.6) and the referenced geometry still render ~2.5 m offset. The
frame is not the whole story: the engine places the referenced model by a **non-origin reference
point**, so a vanilla wheel (local geometry centered at its own origin, ~0.4 m, full LOD set) lands
right while a body region in **model-space** (car-sized, single visual LOD) is shifted by roughly its
own extent. Two fixes that FAILED on MercedesAMGLF: bumping the proxy-triangle scale (the engine
normalizes the triangle, so scale is moot) and the "wheel pattern" (re-center the geometry to its
bbox-center + anchor at that center — proves the engine does not use bbox-center either).

Practical guidance: **vanilla does not proxy the car body** — the body is direct geometry under the
65535 ceiling. Prefer fitting the body under 65535 (decimate with `blender-visual-review`, or split
into ≤2 sub-objects of direct geometry) over body-proxys of large model-space geometry. If you must
proxy large geometry, the referenced `.p3d` likely has to be LOCAL-centered with the same LOD set as a
vanilla wheel (Geometry/Memory/ViewGeo/FireGeo), and the placement reference must be reverse-engineered
with a controlled in-game anchor-sweep — never assume identity-frame == aligned. Status on
MercedesAMGLF: winding CLOSED, proxy placement OPEN (defect #2); see `MERCEDES_AMGLF_dev\HANDOFF.md`.
Same risk is live on SUB_BRZ (source-game import, all-proxy body) — this finding applies there too.

### proxy placement — s2 model-space convention NOT confirmed; in-game FAIL (s3 2026-06-24)
> **⚠️ CORRECTION (s3 2026-06-24, in-game smoke):** the "RESOLVED" claim below FAILED the in-game gate — body proxies
> rendered rotated/invisible (user's eye). The model-space + identity-frame convention IS identity in py3d
> (`derive_proxy_frame` = exact identity for all 6 `mb_`) but did NOT align in-game, and the offline gate (frame=identity
> + scatter render + verifier 33/33) gave **FALSE-GREEN twice**. **The leading root cause is orthogonal to the
> geometry-space convention:** the proxy SELECTION PATH carried a `.p3d` extension (`proxy:...\mb_chassis.p3d.001`) →
> the engine appends `.p3d` and looks for `mb_chassis.p3d.p3d` → proxy not found → geometry silently missing in-game
> (offline py3d still "sees" the selection). See the `.p3d`-extension rule in `references/vehicle-structural-parity.md`
> (VERIFIED vs vanilla CivilianSedan + kt_roadkill). **FIX THE PATH FIRST** (`add_proxy(path)` with NO `.p3d`); only
> then re-judge the geometry-space convention below. **RESOLVED + VERIFIED in-game 2026-06-24 (MercedesAMGLF AC1.4 PASS): the full confirmed convention is the block below.**
> Meta-lesson: for proxies, the offline frame/render is NOT a sufficient gate — the gate is the in-game render.

The session-1 guidance above ("vanilla doesn't proxy the body → prefer re-fit") is **superseded**: detailed
car mods DO proxy the body and it works. **CONVENTION CONFIRMED in-game 2026-06-24 (MercedesAMGLF AC1.4 PASS).**
A pure-geometry proxy (1 visual LOD, no config class — vanilla `prox_int`/`sedan_engine`, kt_roadkill `_body`,
Star_Audi_R8 `chassis1`/`eng`) needs ALL THREE of:

> 1. **Geometry in MODEL-SPACE** (real car position, NOT re-centered). Verified by debinarizing the vanilla
>    proxy `.p3d`: `prox_int` Y[0.36,1.56] (cabin), `sedan_engine` Z[-2.30,-1.12] (front).
> 2. **Proxy selection path WITHOUT `.p3d`** (`proxy:<path>.<NNN>`). The engine appends `.p3d`; a doubled
>    `.p3d.p3d` → proxy silently absent in-game (offline py3d still "sees" it). Vanilla + kt_roadkill confirm.
> 3. **Proxy-triangle FRAME = `R=((-1,0,0),(0,0,1),(0,1,0))`** — the value `py3d.derive_proxy_frame` returns
>    for vanilla `prox_int`/`sedan_engine` AND kt_roadkill `_body`/`drivewheel`. Author with
>    `add_proxy(path, origin=(0,0,0), rotation=((-1,0,0),(0,0,1),(0,1,0)), scale=0.1)`.
>    **CRITICAL TRAP:** py3d's `canonical_proxy_triangle(rotation=None)` ("identity") is NOT engine-identity —
>    the engine RENDERS IT ROTATED ~90°. That false "identity" passed every offline check yet failed in-game
>    twice (the green-in-false gate). Replicate the MEASURED vanilla/KT frame; never trust py3d's "identity".

Attachment proxies (wheel/crew/door) are NOT a placement reference: they are placed by physics/config (axles,
`proxyPos`) so their non-zero `pos` misleads. Re-fit/decimate is the WRONG default for a high-detail body
(MercedesAMGLF body ~167k resolved → ~60% decimation); proxies are correct and work when authored as above.
The transform-scale reference (`friend_visual_bbox`) must be a STABLE artifact (the donor `.p3d`), never the
deployed shell (pointing at your own output shrinks scale ~3%/rebuild). **Meta-lesson: for proxies the offline
frame/render is NOT a valid gate — the gate is the in-game render.** SUB_BRZ's "crew/wheel not found in
view/fire geometry" spawn blocker is very likely THIS bug (doubled-`.p3d` proxy paths) — apply rules 1-3 there.


## GET-IN RADIAL + LOD LADDER en coches proxy-body (added 2026-06-27, MERCEDES_AMGLF)

### Binding del script (precondición, falla silenciosa)
Un coche `class X: CarScript` cuyo `CfgMods.<Mod>.defs.worldScriptModule` no declara `dir = "<Mod>";` o usa
forward-slashes en `files[]` → el módulo NO carga → el script class nunca bindea → el trío de get-in (y todo
override) está MUERTO sin error (`script.log` 0-byte = falso-limpio; telemetría reporta la clase BASE `CarScript`).
Fix: `dir = "<Mod>";` + backslashes `files[] = {"<Mod>\scripts\4_World"}` (como SUB_BRZ/LFQuad). Confirmar con
telemetría `ClassName()` ≠ base. Para que la telemetría lea el nombre EXACTO del config-class hace falta la clase
hoja `class <Mod> extends <Mod>_Base {}`. Ver LL-163.

### La radial "Get in" — el blocker es GEOMÉTRICO (componente de colisión + crew proxy), NO `GetCrewIndex`
> Corrección 2026-06-27: una auditoría offline hipotetizó que a los coches source-game les faltaba el override
> `GetCrewIndex`. **REFUTADO in-game** — el MERCEDES s8 resolvió el get-in del CONDUCTOR sin tocar `GetCrewIndex`
> (telemetría `comp=0 crewIdx=0`, "el mapeo nativo funciona"). La fuente de verdad es el **Addendum 2026-06-27
> "Crew get-in" de `references/vehicle-structural-parity.md`** (VERIFICADO in-game LFQuad D34 + MercedesAMGLF). Resumen:

`CrewPositionIndex(componentIdx)` (native, transport.c:116) resuelve el asiento por el **componente de colisión que
el raycast del cursor golpea en la ViewGeo** (`ObjIntersectView`, actiongetintransport.c:50-51) — NO por
`GetCrewIndex` ni por memory points. Los dos blockers reales, ambos geométricos:
- una **caja sólida ocluyente** en la ViewGeo (p.ej. una "espina" central) → el cursor la golpea ANTES que el cubo
  de asiento → sin get-in. Fix = borrarla (MERCEDES conductor, in-game).
- cada asiento = su **propio ComponentNN dedicado y limpio** (cubo cerrado, dual-tag); pintados sobre una rejilla
  multi-componente → "siempre conductor", el codriver nunca se golpea (MERCEDES codriver = ABIERTO; LFQuad D34).
- la pose viene del **crew-proxy triángulo CANÓNICO** (edges ~1.0/2.0), no del diminuto `add_proxy(scale=0.1)`.

`GetCrewIndex` / `GetDoorConditionPointFromSelection` / el sistema de puertas NO son el camino del get-in básico (el
LFQuad y el MERCEDES conductor dan la radial sin ellos). Estado: MERCEDES conductor RESUELTO, codriver ABIERTO
(blocker geométrico, ver su HANDOFF); **SUB_BRZ get-in = VERDE-FALSO** — su HANDOFF lo reconoce: `vehicle_enter` del
MCP fuerza el asiento saltándose la ActionCondition; la radial nunca se observó → el SUB_BRZ debe aplicar/verificar
este Addendum (espina ocluyente + cubos de asiento limpios) ANTES de declararlo. Ver LL-164.

### ★ Blocker DECISIVO del codriver = ComponentNN de asiento INWARD-wound + point flags 0x02000000 (SUB_BRZ s9 in-game + MERCEDES s12 headless) — RESUELTO en ambos
**Supera lo de arriba (2026-06-27) y REFUTA LL-164 (NO necesita door system).** "Cubos de asiento limpios, todas las caras outward" es NECESARIO PERO NO SUFICIENTE: una caja py3d `outward winding + point flags 0` pasa todo gate offline (forma/winding/dual-tag) pero **NO es raycast-colisionable** → `DayZPhysics.RaycastRV(ObjIntersectView)` no la golpea → el cursor no resuelve ningún asiento → cae a component0 (el conductor "funciona" SOLO por ese fallback; el codriver NUNCA). El mapeo `CrewPositionIndex(comp)` SIEMPRE estuvo bien — irrelevante mientras la geometría no colisione. **FIX (copiar la convención del control positivo LFQuad/Croco, NO el default py3d): los ComponentNN de asiento = winding INWARD + cada point flag = `0x02000000` (33554432).** Aplicarlo MÍNIMO: si los asientos ya enumeran como su ComponentNN con el mapeo correcto (verifica con el crew-probe/PROBE), voltea SOLO las caras de asiento a inward + setea sus point flags + recomputa la normal — NO rebuildees toda la ViewGeo, NO toques el cuerpo. Closed-car: NO necesita shell ni asientos índice-alto en la ViewGeo (red herring en MERCEDES s11). Gate = in-game o el **crew-probe headless** (`RaycastRV` por asiento desde la puerta, sin apuntar; ancla en `pos_driver`/`pos_codriver` si caen dentro del cubo). Mecanismo + tooling + caveat de anclaje del control: `references/vehicle-structural-parity.md` "CRITICAL EXTENSION 2026-06-28" + "MercedesAMGLF CONFIRMATION 2026-06-28 s12". **Estado: codriver RESUELTO — SUB_BRZ (in-game) + MERCEDES (headless).** Para cualquier coche source-game/py3d nuevo: aplica esto de entrada (no descubras el blocker in-game).

### Ruedas al revés: medir el eje en el .p3d ANTES de fijar `angle1` (offline check, predice el bug sin in-game)
`model.cfg` wheel `angle1` debe ser coherente con el `dir` de cada `wheel_X_Y_axis` (2 puntos en el Memory LOD):
- ejes UNIFORMES (los 4 con el mismo signo X) → `angle1` UNIFORME en las 4 (LFQuad `(1,0,0)`; SUB_BRZ `(1,0,0)`→`-6.283`).
- ejes ESPEJADOS (L/R signo X opuesto) → `angle1` alternado L/R (convención Landrover).
Aplicar el flip-derecho del Landrover sobre ejes uniformes gira el lado derecho al revés.
**Audit 2026-06-27:** MERCEDES tiene ejes uniformes `(-1,0,0)` pero `angle1` alternado (model.cfg:84,97) → ruedas
al revés, OFFLINE-predicho. Fix = `angle1` uniforme. Check offline: `py3d` → `dir` de `wheel_X_Y_axis`, comparar
signos X entre L y R (script reusable: `references/audit_getin_wheels.py` — corre sobre los .p3d de ambos coches + LFQuad).

### LOD ladder para un coche shell+proxy (re-import de un diezmado)
El cuerpo va partido en shell-core (carpaint/glass/luces, directo en el LOD) + N proxys `mb_` (<65535 resueltos
c/u). Para una escalera de LODs visuales desde un modelo diezmado por el artista:
- Reutilizar el pipeline `phase2\build_proxies.py`/`build_shell.py` POR LOD con regiones decimadas y proxys con
  sufijo (`mb_chassis_lod1`, etc.). LODs cuyo cuerpo resuelve <65535 → geometría DIRECTA (sin proxys); los que
  exceden (LOD0/LOD1/LOD2 típicamente) → shell+proxys.
- Decimar con **Blender headless** (`--background --python`, modifier Decimate COLLAPSE, `use_collapse_triangulate`),
  per-objeto para conservar los grupos; re-split por grupo a regiones. Excluir las ruedas del cuerpo (van por wheel proxy).
- **Conservar los LODs de soporte (Geometry/Memory/ViewGeo/FireGeo) del .p3d DESPLEGADO**, no del friend control —
  así sobrevive cualquier edit posterior a esos LODs (p.ej. el parche del get-in en ViewGeo). El transform (escala)
  SÍ se mide contra el friend control estable (no contra la propia salida: encoge ~3%/rebuild).
- Verificar resolved<65535 POR LOD y POR proxy antes de escribir; `verify_amglf.py` debe seguir 35/35.
- El primer paso suave (p.ej. −20% LOD0→LOD1) preserva calidad cerca; acelerar después. Builder de referencia:
  `C:\Users\<you>\VehicleImport\scripts\build_ladder.py` (MERCEDES_AMGLF 2026-06-27; rescatado de %TEMP%
  2026-07-06, SHA256 verificado): 5 LODs 182k/145k/73k/23k/7k + shadow.

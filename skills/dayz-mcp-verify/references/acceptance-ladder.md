# Acceptance ladder — rip → coche conducible (Fase 5 drivability)

> Extracted from dayz-mcp-verify/SKILL.md 2026-07-07 (F3). The core SKILL.md keeps a summary + pointer here.


Escalera de aceptación completa de coches conducibles: los verbos de conducción owner-side, las rungs R1→R6, el mapeo fallo→fix de la taxonomía SUB_BRZ, y el detalle del orquestador `drive_ladder.py`. El núcleo de la skill resume esto en 5-8 líneas y apunta aquí.


## DRIVABILITY: verbos de conducción owner-side disponibles (added 2026-06-28)

Fase 5 del proyecto DayZ-MCP añadió y gateó in-game una surface de verbos componibles que SÍ conducen el coche
owner-side (el cliente toma ownership y maneja throttle/steer). Tools MCP (todas peer **cliente** salvo la última,
que es server):

| Tool MCP | Qué hace |
|---|---|
| `vehicle_get_in_client(pos)` | sienta al cliente en el coche cerca de `pos` (toma ownership + condiciona fuel/batería); devuelve `seated`/`is_owner`/`vehicle_fixture_ready` |
| `engine_set(mode)` | `"start"`/`"stop"` el motor del coche-owner |
| `vehicle_control(throttle, steer, brake, handbrake, hold_ttl_s)` | fija control SOSTENIDO (el coche sigue conduciendo sin re-llamar, hasta `vehicle_release` o el deadman `hold_ttl_s`); fail-closed (rango+NaN) |
| `vehicle_telemetry()` | speed/gear/engine/pos/`is_owner`/net_strategy del coche-owner |
| `vehicle_release()` | suelta el control sostenido |
| `query_get_in_condition(pos, component=-1)` (peer **server**) | diagnostica si el get-in NORMAL estaría disponible y CUÁL de los 7 gates de `ActionGetInTransport` bloquea; `component` = índice de un `scene_raycast` previo (OBLIGATORIO para un veredicto `available`; sin él → `partial`, nunca PASS) |

**Mecanismo (NO re-investigar, verificado in-game):** el cliente toma ownership con `StartCommand_Vehicle`
client-side (`OnVehicleSeatDriverEnter`→`Possess(car)`, bajo `FEATURE_NETWORK_RECONCILIATION`); conducir owner-side
exige aplicar `SetThrottle/SetSteering` DENTRO de `CarScript.OnInput` TRAS `super` (un `modded class CarScript` en el
PBO MCP — `Car.SetThrottle` desde el mission lo pisa `super.OnInput` con el input=0 del driver). El holder estático
`MCPCarDrive` + deadman lleva el estado. Ver `dayz-vehicles` (SP-032) + plan
`DayZ_MCP_dev/plans/2026-06-28-fase5-tramoA-redesign-delta.md`.

**Escalera de aceptación (§6 del plan, YA CABLEADA — ver §"ESCALERA DE ACEPTACIÓN" abajo):** con estos verbos las rungs que antes eran
"manual" ya son automatizables — R3 get-in disponible (`query_get_in_condition` con `component` de un raycast →
`available`/`first_block`), R4 sentado (`vehicle_get_in_client` → `seated`/`is_owner`), R5 conduce
(`engine_set`+`vehicle_control`+`vehicle_telemetry`+`vehicle_release` → `pos_delta` crece), R6 sentido de ruedas
(`vehicle_control{steer}` + visual). Caveats de gate verificados: (a) para MEDIR `pos_delta` de conducción, spawnea
el coche en zona DESPEJADA (offset; un obstáculo delante da pos_delta≈0 engañoso); (b) `query_get_in_condition` exige
el coche JUNTO al jugador (gate 7 reachability mide jugador↔puerta). Drivers de gate de referencia (raw enqueue):
`DayZ_MCP_dev/tools/{tramoA_verbs_gate.py,tramoB_getin_gate.py}`.

## ESCALERA DE ACEPTACIÓN: rip → coche conducible (added 2026-06-28)

El orquestador de Fase 5 (§6 del plan `DayZ_MCP_dev/plans/2026-06-28-fase5-drivability-autonoma.md`).
Recorre una escalera ordenada de **rungs**; cada rung lee **ground-truth in-game** con los verbos de
arriba (sección DRIVABILITY); cada fallo se mapea a un **fix conocido de la taxonomía SUB_BRZ** (en la
skill `dayz-vehicles`, `references/`). El objetivo: iterar un coche (rip source-game → conducible) sin humano
en el juego, **parando y escalando** en cuanto un fallo cae fuera de la taxonomía conocida.

**Cuándo**: tras el smoke visual (la receta de §"VEHÍCULO" de arriba ya dejó el juego lanzado, el bridge
verde y el coche cargando). La escalera es la extensión de **conducción** del smoke: empieza donde el
smoke acaba (entity spawnea + se ve) y llega hasta "conduce y gira al lado correcto".

### Precondiciones (heredadas — NO re-hacer aquí)
- **Launch + readiness + `bridge_status` verde**: receta §"VEHÍCULO" pasos 1-7 (misión stock, seed del
  bridge, `-PackOnly`, esperar CE, captura flaky). La escalera asume ambos peers `version_state=ok` y el
  player spawneado (`query_player_state` devuelve `pos`).
- **Box DayZ EXCLUSIVO** entre sesiones Cowork (precondición dura §"VEHÍCULO".8). Una sola sesión.
- **Surface de verbos construida y gateada in-game** (sección DRIVABILITY). La escalera NO construye
  bridge: lo conduce.

### Cómo se recorre (el lazo de iteración)
1. Posiciona el coche (ver "Colocación del spawn") y recorre **R1→R6 en orden**.
2. En cada rung FAIL, **clasifica**: ¿el síntoma está en la taxonomía SUB_BRZ (tabla "Mapeo fallo→fix")?
   - **Sí** → registra el rung + el fix mapeado en el journal y **sigue** recogiendo señal de los rungs
     que aún sean alcanzables (ver "hard-block vs soft" abajo). NO rebuild a mitad de pasada.
   - **No** (fallo fuera de la taxonomía) → **PARA y escala** (barandilla 1). No rebuild a ciegas.
3. Al final de la pasada: **batch** de todos los fixes registrados → el agente los aplica al `.p3d`/config
   (lazo humano/agente, NO scriptado: leer screenshots + editar geometría/config con los refs de
   `dayz-vehicles`) → **un solo** rebuild+deploy (`dayz-test-ingame` / `dayz-pbo-build`) → re-corre la
   escalera. Agrupar todos los fixes por rebuild es R5 (cada test in-game vale por TODOS los cambios).
4. **Presupuesto de iteraciones** por coche (default 6 pasadas; si no converge → escalar, no loop infinito).

**Hard-block vs soft (qué corta la pasada):**
- **R1 fail = hard** (sin entity no hay nada que probar) → para la pasada, fix, re-spawn.
- **R4 fail = hard para R5/R6** (sin sentarse no se conduce) → registra, salta R5/R6.
- **R2, R3, R6 = soft**: registra el fix y sigue. En particular **R3 (get-in diagnóstico) NO bloquea
  R4/R5**: `vehicle_get_in_client` (R4) **fuerza** el `StartCommand_Vehicle` y se salta los gates del
  radial → un coche con R3 FAIL (un humano no podría entrar) puede aun así conducirse por MCP. Eso es una
  señal valiosa: "conduce por MCP pero el get-in del jugador está roto" → el fix de get-in sigue siendo
  necesario para el producto. Recoge ambas señales en la misma pasada.

### Colocación del spawn (la tensión R3/R4 ↔ R5 — resolverla mal da verde/rojo falso)
- **R3 `query_get_in_condition` y R4 `vehicle_get_in_client` exigen el coche JUNTO al jugador** (gate 7
  reachability mide jugador↔puerta; el seat client-side busca transporte cercano).
- **R5 (conducir) exige pista DESPEJADA por delante** (un obstáculo da `pos_delta≈0` engañoso).
- **Resolución unificada**: spawnea el coche **en la posición del jugador, en terreno abierto**, orientado
  (`world_spawn` arg `rotation`) hacia espacio libre. Así R3/R4 tienen reachability Y R5 tiene pista.
- **Desambiguación obligatoria de `pos_delta≈0`** (es un rojo-falso candidato, NO concluir drivetrain a la
  primera): tras R4 OK (seated+is_owner) + R5 con throttle, si `pos_delta≈0`:
  - `vehicle_telemetry` con `speedo_max>0` / gear auto-subió / el motor revoluciona (log `[MCP-DRIVE]` RPM
    sube) → el powertrain FUNCIONA, el coche está **BLOQUEADO** (obstáculo) → **re-corre solo R5** con el
    coche reubicado a suelo despejado (offset tipo `tramoA_verbs_gate.py --dz 40`). Si entonces se mueve,
    era obstáculo (rojo-falso), no un fix de modelo.
  - `speedo_max≈0` + sin revoluciones + ruedas sin simular → **drivetrain/wheel-sim real** → fix de R5.
  El gate del primer spawn de SUB_BRZ (6063,1931) tenía obstáculo: `pos_delta` 0.15-0.25 con motor a tope;
  el offset +40m despejado dio 29 m. Ground-truth = el re-test en suelo despejado, no la primera lectura.

### La escalera

| Rung | Verbo(s) MCP | PASS (ground-truth) | FAIL → fix (taxonomía) |
|---|---|---|---|
| **R1 spawnea** | `world_spawn(type, pos, rotation)` | `ok=1`, `found=1`, entity con `pos` | `unknown_type`/`spawn_failed` → mod no montado / `CfgPatches`. Spawnea pero invisible / "action selection not found in geometry" → **componentNN** (islas sueltas) |
| **R2 render sólido+orientado** | `scene_raycast(from,to)` (N puntos) + `camera_set(cam_mode:"lookat")`+`capture_screenshot` (N ángulos) | rayos sólidos donde deben pegar + visual sin agujeros/caras invertidas, orientado, escala plausible | agujero desde un ángulo / sólido desde el opuesto → **winding por-pieza**. Coche rotado/espejado → **orient transform**. Tamaño mal → **escala**. Pieza flotando/rotada ~90° → **frame de proxy** |
| **R2.5 restore-gameplay** | (lookat NO desactiva la sim; ver abajo) | sim+controles vivos antes de conducir; **freecam PROHIBIDA en esta escalera** | si R4/R5 no responden con seated+owner+engine → sospechar freecam/sim, NO drivetrain |
| **R3 get-in disponible** | `scene_raycast` (anillo) → `component` → `query_get_in_condition(pos, component)` | el asiento de **CONDUCTOR** (`component_crew_index==0`) está `available=1` (`first_block=""`). Un coche con solo el PASAJERO available NO es conducible por un humano → R3 FAIL | el `first_block` del CONDUCTOR (tabla "Mapeo fallo→fix"). Soft: NO bloquea R4/R5 |
| **R4 sentado (MCP)** | `vehicle_get_in_client(pos)` | `seated=1`, `is_owner=1`, `vehicle_fixture_ready=1` | `not_seated`/`seat_failed` → reachability / seat anim / crew bone. Hard para R5/R6 |
| **R5 conduce** | `engine_set("start")` → `vehicle_control(throttle:1, hold_ttl_s:12)` → [no re-llamar] → `vehicle_telemetry` → `vehicle_release` | `pos_delta>1.0` m + `speedo_max>0` + `engine_on_server` + `is_owner` (movimiento por gravedad/inercia NO cuenta) | `pos_delta≈0` con engine+owner → AMBIGUO: **re-test OBLIGATORIO en suelo despejado** antes de mapear fix (`needs_clear_ground_retest`); si sigue ~0 con motor revolucionando → **wheel sim (FireGeo)** / drivetrain |
| **R6 ruedas/sentido** | `vehicle_control(steer:-1)` + muestreo `vehicle_telemetry` (+ `camera_set` lookat opcional) | el coche curva al lado COMANDADO — pero el signo izquierda/derecha está SIN CALIBRAR: el orquestador reporta `signed_cross`, confirma vs un coche vanilla de ref antes de concluir | curva al lado opuesto / ruedas espejadas → **model.cfg wheel `angle` sign** / **naming `wheel_X_Y`** |

`world_spawn` result: `pos_real`/`pos`. `vehicle_get_in_client`: `seated`/`is_owner`/`vehicle_fixture_ready`.
`vehicle_telemetry`: `speedo_max`/`gear`/`engine_on_server`/`pos`/`is_owner`/`net_strategy`.
`query_get_in_condition` → `get_in`: `available`/`partial`/`crew_size`/`component_crew_index`/`first_block`/
`per_seat[]{crew_index, crew_can_get_through, area_free, occupied, reachable}`. `scene_raycast` →
`raycast`: `hit`/`component`. (Firmas y campos verificados contra los schemas MCP + `tramoA_verbs_gate.py`/
`tramoB_getin_gate.py` que gatearon PASS in-game.)

### R2.5 — restore-gameplay (mecanismo VERIFICADO, no hand-wave)
La cámara y el get-in tocan la simulación del player; hacerlo en el orden malo deja el coche inerte con
todos los demás verbos en verde (rojo-falso clásico). Lo verificado en `MCPClientBridge.c`:
- **`camera_set` SIEMPRE suprime controles** (`SuppressGameplay()`, `:1333` → `PlayerControlDisable` +
  oculta HUD) pero **NO** desactiva la sim — salvo `cam_mode="free"`, que llama `DisableSimulation(true)`
  (`:1335-1400`, `CAMERA_MODE_FREE`). `lookat`/`orient`/`matrix` crean una `staticcamera`: **sim viva**.
- **El verbo `vehicle_get_in_client` (R4, `ProcessVehicleGetInClientPrep` `:919-1029`) NO restaura la sim**:
  hace seat (`StartCommand_Vehicle` `:955`) + conditioning (`OnDebugSpawn` `:1006`) + captura ownership, pero
  **no llama `RestoreGameplay()`**. El único PREP cliente que restaura es el del gate `drive_probe_client`
  (`ProcessDriveProbeClientPrep`, `RestoreGameplay()` `:1042`); la def `:1808-1832` → `DisableSimulation(false)`
  `:1813` + `PlayerControlEnable(true)` `:1825`. Consecuencia: una sim que una freecam deshabilitó **NO se cura
  sola al entrar en R4** — el get-in se colgaría en `not_seated` (la sim del player parada no completa el
  `HumanCommandVehicle`). La única protección es la regla de abajo.
- **Regla de la escalera**: para R2 y R6 usa **siempre `cam_mode="lookat"`** (staticcamera, sim viva,
  conducir sigue funcionando porque el throttle lo aplica el holder `MCPCarDrive.OnInput`, no el input del
  player). **NUNCA `cam_mode="free"` entre R2 y R5.** Si R5 no mueve con `seated=1`+`is_owner=1`+
  `engine_on`, el primer sospechoso es una sim freecam-deshabilitada (violación de R2.5), no el drivetrain.

### Barandillas anti-verde-falso (innegociables)
1. **Fallo fuera de la taxonomía conocida → PARA y escala.** No rebuild a ciegas. La escalera mapea
   síntomas conocidos; un síntoma nuevo es señal de que falta entender algo, no de iterar al azar.
2. **El gate es ground-truth in-game, nunca proxy offline.** Un audit offline (`rip_p5_gate.py --cull`,
   `audit_getin_wheels.py`) PRE-filtra antes del rebuild, pero el veredicto de un rung es la lectura
   in-game. Offline da verde-falso (probado 2× en MercedesAMGLF/SUB_BRZ).
3. **Presupuesto de iteraciones + journal por ciclo.** Cada pasada escribe `verdict.json` (rung alcanzado,
   `first_block`, `pos_delta`, fix mapeado) + los PNG de R2/R6 + la telemetría, en
   `<TargetMod>_dev\_ladder\run_<n>\`, para que cada verde sea **inspeccionable** y cada rojo trazable.

### Mapeo fallo → fix (taxonomía SUB_BRZ → `dayz-vehicles/references/`)

| Síntoma / señal | Rung | Fix (anchor) |
|---|---|---|
| `world_spawn` `unknown_type`/`spawn_failed` | R1 | mod no montado / `CfgPatches` no registra — `dayz-test-ingame` (paths `!Workshop`), no es bug de modelo |
| Spawnea pero invisible / "action selection X not found in view/fire geometry" | R1 | **componentNN dual-tag**: `vehicle-structural-parity.md` "componentNN DUAL-TAG" + `rip-import.md:385-388` (hubs/asientos = islas con 0% overlap → invisibles al enumerador de colisión; cada hub/asiento lleva TAMBIÉN un `componentNN` en las mismas caras) |
| Agujero desde un ángulo, sólido desde el opuesto | R2 | **winding por-pieza** (NO flip global — fue verde-falso): `rip-import.md:487-575`; fix permanente = orientar a la normal autorizada del source; gate offline = `rip_p5_gate.py --cull` |
| Coche rotado/espejado, o pieza flotando/rotada ~90° | R2 | **orient transform** del cuerpo / **frame de proxy** `R=((-1,0,0),(0,0,1),(0,1,0))` — `dayz-vehicles` §proxys (convención Mercedes; `rotation=None` de py3d renderiza ~90° rotado) |
| `first_block="componentNN"` (`component_crew_index<0`) | R3 | **componentNN** en los asientos (mismo fix que R1 invisible): el asiento no se enumera como componente de crew |
| `first_block="crew_can_get_through"` | R3 | **`class X: CarScript` pelado** hereda `Transport.CrewCanGetThrough()=false`: `rip-import.md:430-451`; fix = `extends CarScript` con override `CrewCanGetThrough`+`GetSeatAnimationType`+`GetAnimInstance` + `worldScriptModule` en `CfgMods` (puertas NO requeridas, `:449-451`) |
| `first_block="area_blocked"` (gate 6b) | R3 | `IsAreaAtDoorFree` false → obstrucción del área de la puerta / selección de puerta |
| `first_block="unreachable"` (gate 7) | R3 | `CanReachSeatFromDoors` false → geometría seat↔door, o **coche demasiado lejos del jugador** (mover adyacente antes de concluir fix de modelo) |
| `first_block="occupied"` / `"item_heavy"` / `"already_in_vehicle"` | R3 | estado del harness, NO bug de modelo: re-spawn limpio / soltar item pesado de las manos / salir del vehículo primero |
| `first_block="no_component"` (`partial=1`) | R3 | pasaste `component=-1`: saca un `component` real de un `scene_raycast`; sin él es diagnóstico PARCIAL, NUNCA PASS |
| `vehicle_get_in_client` `not_seated`/`seat_failed` | R4 | latencia get-in (subir `prep_deadline`) / crew bone-selection / seat anim type — `vehicle-config-and-modelcfg.md` (crew proxy = selección en geometría **Y** bone en `CfgSkeletons`, ambos o get-in rompe) |
| `pos_delta≈0` (tras descartar obstáculo) | R5 | **wheel sim (FireGeo)**: `rip-import.md:250-251` (cara de cada wheel proxy TAMBIÉN en visual `wheel_X_Y` + `wheel_X_Y_damper` + front `wheel_X_1_steering`) + `vehicle-structural-parity.md:23` (hubs como CARAS + componentNN en Geometry); o drivetrain en config.cpp |
| Curva al lado opuesto al `steer` comandado / ruedas espejadas | R6 | **model.cfg wheel `angle` sign** (`vehicle-config-and-modelcfg.md:484`) + **naming `wheel_X_Y`** (`rip-import.md:195`: 1er índice = lado 1=+x/2=−x, 2º = eje 1=front; ojo al espejado Mercedes vs sedan) |

### Orquestador de referencia
`references/drive_ladder.py` — conduce R1→R6 contra el daemon `:8765` (raw `/enqueue`+`/await`, mismo patrón
verificado de `tramoA_verbs_gate.py`/`tramoB_getin_gate.py`), para en el primer hard-fail o tras recoger los
soft-fails, y emite `verdict.json` nombrando el rung, el `first_block` y el fix mapeado. **NO** aplica fixes
ni rebuildea (eso es el lazo agente/humano, barandilla 1). Reporta `objective_PASS` (los rungs scriptables);
la **acceptance** real necesita además los rungs visuales del agente (R2_visual winding/orient/escala, R6
calibración de giro), que el script no cierra. Endurecido tras R21 (Codex 2026-06-28, DL-001..011): R3 gatea
el asiento de CONDUCTOR (no cualquiera), R4 fail-closed (seated+owner+fixture), un preflight aborta si el
player ya está en un coche (el re-run mediría el viejo), R5 exige engine_on+owner y emite
`needs_clear_ground_retest` en vez de adivinar obstáculo/drivetrain, cada verbo chequea timeout/ok (un fallo
de harness NO es fix de modelo). Fixtures offline `references/test_drive_ladder.py` (9 escenarios PASS).
Estado de verificación honesto: cada rung reusa una secuencia de verbos ya gateada in-game por separado; la
cadena R1→R6 en una sola corrida es el propio test in-game que la escalera existe para correr (no gateado
como unidad). `py_compile` + fixtures OK.

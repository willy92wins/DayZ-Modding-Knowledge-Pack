---
name: dayz-realistic-animation-director
description: Dirige de principio a fin la creación, corrección, pulido, exportación, integración y verificación de animaciones realistas para DayZ. Úsala cuando el resultado deba sentirse físicamente creíble en jugador, manos y armas, recargas, unstuck/unjam, locomoción, criaturas, ocupantes de vehículos, mecanismos, props o simulaciones; especialmente ante clipping, dedos cruzados, articulaciones sobreextendidas, contacto falso, objetos que no siguen la mano, stutter, loops defectuosos o discrepancias Blender-vs-in-game. Orquesta `blender-animation` para autoría y `dayz-animation-pipeline` para contratos del motor; no sustituye consultas puramente técnicas sobre config, ASI, skeletons o exportación.
---

# DayZ Realistic Animation Director

Produce una animación creíble y cierra su integración con evidencia honesta. Esta skill dirige el trabajo; las skills de Blender y DayZ conservan la autoridad técnica.

## Frontera de autoridad

Antes de actuar, lee [authority-and-routing.md](references/authority-and-routing.md).

- Invoca `blender-animation` antes de operar sobre Actions, rigs, constraints, curvas, renders o exportación desde Blender.
- Invoca `dayz-animation-pipeline` antes de decidir formato, skeleton, export mask, FPS/frame budget, notetracks, anim graph/ASI, compile, wiring o integración DayZ.
- Invoca la skill de dominio adicional indicada en [authority-and-routing.md](references/authority-and-routing.md) para personajes, criaturas, vehículos, P3D, retargeting o test in-game; aplica después los controles de [domain-gates.md](references/domain-gates.md).
- Ante conflicto, la autoridad especializada gana. Registra la divergencia y detén el gate afectado; no inventes una tercera regla.

Si la petición es sólo técnica —por ejemplo, elegir un `AnimationSource`, registrar una `.anm` o explicar un estado ASI— deja que `dayz-animation-pipeline` sea la skill primaria. Usa esta skill cuando haya que autorar, evaluar o mejorar el movimiento.

## Ruteo de dominio

| Animación | Skills que se añaden a la directora |
|---|---|
| Jugador, manos, humano custom o infectado | `dayz-characters`; para criaturas verifica primero su bind/skeleton real |
| Arma, recarga, unjam o mecanismo P3D | `dayz-weapons` si cambia el contrato de entidad + la skill P3D/model pertinente |
| Ocupante, entrada o controles de vehículo | `dayz-vehicles` |
| Mocap/donor externo | skill de retargeting aplicable; nunca sin mapa source→target |
| Prueba runtime | `dayz-test-ingame`/`dayz-mcp-verify` vigente, con lease y lifecycle |

`blender-animation` y `dayz-animation-pipeline` siguen siendo obligatorias para autoría e integración respectivamente; las skills de la tabla no las sustituyen.

## Tres controles que nunca se sustituyen entre sí

1. **Cadena completa:** medir nudillos y puntas no valida falanges intermedias. Muestrea todos los segmentos y articulaciones relevantes.
2. **Contacto positivo:** «sin penetración» no significa «agarrando». Exige una pareja de contacto, una superficie/landmark objetivo y una banda de distancia.
3. **Bloqueo relativo:** compartir keyframes o una curva escalar no demuestra que dos elementos se muevan juntos. Mide `T_actor^-1 * T_target` durante toda la ventana de agarre.

Un fallo visual reproducible del usuario o in-game invalida cualquier `PASS` offline. Conviértelo en fixture antes de volver a autorar.

## Flujo obligatorio por gates

### 0. Preserva y observa

- Inspecciona la escena, Actions, frame actual, selección, constraints y ventanas antes de mutar.
- Trabaja siempre desde una copia versionada; no sobrescribas el `.blend` fuente.
- Si corriges un defecto, reproduce primero el fallo con la escena actual y conserva esa evidencia RED.
- Lee el contrato del proyecto (`CLAUDE.md`, product spec, plan y handoff vigentes) cuando existan.

### 1. Captura el contrato técnico DayZ

Pide a `dayz-animation-pipeline` la ruta aplicable y registra:

- tipo de animación y skeleton/rig autoritativo;
- FPS, duración o frame budget y reglas de loop;
- notetracks/eventos y estados runtime;
- bones incluidos/excluidos y objetos/selecciones móviles completos;
- artefactos de exportación, compile, wiring, build y prueba in-game.

No hardcodees 291 frames, 30 FPS ni notetracks de la SR2M para otras animaciones. Cada tarea obtiene su contrato vigente.

### 2. Define aceptación antes de posar

Lee [motion-quality-contract.md](references/motion-quality-contract.md) y crea un contrato por tarea que declare sólo los módulos aplicables:

- poses y beats clave;
- articulaciones/cadenas y límites calibrados;
- contactos, superficies y ventanas `contact_on..release`;
- pares de colisión prohibidos y contactos permitidos;
- objetos que deben conservar transformación relativa;
- excepciones intencionales de impacto, snap o deslizamiento;
- pose real de entrada/salida y estados in-game a probar.

Las tolerancias deben venir de referencia, geometría o una decisión explícita. Nunca ajustes el umbral para hacer pasar el candidato actual.

Todo contrato declara exactamente `contract_mode: "diagnostic"` o `contract_mode: "production"`; valores ausentes o desconocidos son error. Un contrato capaz de conceder `OFFLINE_PASS` usa `production`. Cada check declara procedencia (`source_kind`, `source`, `verified_date`, `method`) y cualquier check `segment_clearance` exige procedencia geométrica compartida para los radios de cápsula. Un contrato `diagnostic` puede reproducir un fallo, pero `eligible_for_offline_pass` siempre será falso.

Para una ventana continua de contacto, colisión, bloqueo, orden, rango articular o continuidad usa `frame_range` consecutivo con `step: 1`; producción lo exige. Una lista dispersa de poses doradas no prueba lo que ocurre entre ellas.

### 3. Blocking

Con `blender-animation`, autora sólo poses doradas: inicio, anticipación, contacto, máximo esfuerzo, liberación, recuperación y final.

- Renderiza cada pose en vista on-axis y al menos una oblicua.
- Valida anatomía, silueta, contacto y colisión antes de interpolar.
- Para manos, lee [biomechanics-and-contact.md](references/biomechanics-and-contact.md) y evalúa los cinco dedos, muñeca, antebrazo, codo, hombro y clavícula cuando formen parte del gesto.
- No avances a spline si una pose clave ya clipea, está sobreextendida o no toca el objetivo.

### 4. Movimiento y esfuerzo

- Aplica blocking → spline → polish mediante `blender-animation`.
- Usa timing, spacing, arcos, anticipación, overlap, moving holds y settle según la intención física.
- Valida posición, rotación, velocidad, aceleración y jerk en los elementos relevantes.
- Distingue un snap/impacto intencional mediante una ventana declarada; fuera de ella, un pico es stutter.
- En mecanismos, mueve la jerarquía o selección funcional completa, no sólo la pieza visual que se ve desde una cámara.

### 5. Auditoría offline

Ejecuta el muestreador y el validador cuando exista Blender:

```powershell
& $env:BLENDER_EXE --background '<scene.blend>' --python '<skill>\scripts\sample_blender_motion.py' -- --contract '<contract.json>' --output '<report.json>'
python '<skill>\scripts\validate_motion_contract.py' --report '<report.json>' --contract '<contract.json>' --output '<audit.json>'
```

Interpreta los exit codes del validador:

- `0`: todos los checks requeridos pasan;
- `1`: input válido, uno o más checks requeridos fallan;
- `2`: contrato, muestra o ejecución inválidos; no hay veredicto de calidad.

Además del JSON:

- revisa vídeo completo a velocidad real;
- revisa renders multiángulo de contacto, extremos, transiciones y recuperación;
- busca clipping entre keyframes, no sólo en frames clave;
- comprueba inicio/final contra la pose real de entrada runtime.

### 6. Exporta e integra

- Entrega a `blender-animation` el export desde Blender siguiendo su contrato vigente.
- Entrega el artefacto a `dayz-animation-pipeline` para compile, ASI/config, build y deploy.
- Verifica el artefacto realmente desplegado, no sólo el source.
- No declares que Workbench, DayZATool, Blender MCP o DayZ se ejecutaron si no existe evidencia de esa ejecución en la sesión.

### 7. Gate in-game

Lee [evidence-and-integration.md](references/evidence-and-integration.md).

- Prueba las stances, cámaras y estados que puedan cambiar IK o blending.
- Revisa RPT y compara timing, contacto, clipping y estados mecánicos contra el contrato.
- Si in-game contradice Blender, in-game manda y el caso se convierte en regresión.
- Si el entorno no permite el test, termina en `MANUAL_REQUIRED`, no en PASS.

## Estados de salida

- `FAIL`: falla al menos un gate obligatorio.
- `OFFLINE_PASS`: contrato, escena, auditoría, renders y artefacto offline aprobados; falta juego.
- `MANUAL_REQUIRED`: el siguiente gate necesita una acción o herramienta no disponible.
- `IN_GAME_PASS`: el build desplegado y el comportamiento en DayZ están verificados con evidencia.

Reporta siempre qué gates se ejecutaron, qué evidencia existe, qué se omitió y por qué.

## Política de regresión

Cuando aparezca un defecto nuevo:

1. congela la escena fallida como input de sólo lectura;
2. escribe una fixture mínima que falle por ese motivo;
3. demuestra RED;
4. implementa o endurece el check;
5. demuestra GREEN con una muestra corregida para evitar un test tautológico;
6. sólo entonces modifica la animación productiva.

Ejecuta la suite reutilizable con:

```powershell
python '<skill>\scripts\run_regression_tests.py'
```

Para incluir la fixture real de SR2M, define `SR2M_V44_BLEND` y añade `--real-fixtures`. Si la variable falta, el resultado correcto es `SKIP_REAL_FIXTURE`, no PASS.

## Índice de recursos

- [authority-and-routing.md](references/authority-and-routing.md) — autoridad, precedencia y selección de skills.
- [motion-quality-contract.md](references/motion-quality-contract.md) — formato de muestra/contrato y catálogo de checks.
- [biomechanics-and-contact.md](references/biomechanics-and-contact.md) — anatomía, contacto, auto-colisión y sincronización.
- [domain-gates.md](references/domain-gates.md) — controles por dominio de animación.
- [evidence-and-integration.md](references/evidence-and-integration.md) — evidencia offline, export, deploy e in-game.
- `scripts/sample_blender_motion.py` — Blender → reporte neutral JSON.
- `scripts/validate_motion_contract.py` — reporte + contrato → auditoría determinista.
- `scripts/run_regression_tests.py` — fixtures sintéticas y reales opcionales.

## Stop conditions

Detén el avance y pide la decisión o evidencia que falta cuando:

- no existe referencia de entrada/salida y una elección cambiaría la coreografía;
- el pipeline vigente y una referencia discrepan sobre skeleton, export mask o estado runtime;
- no puede identificarse la pieza mecánica completa;
- una tolerancia sólo puede elegirse mirando el candidato que se desea aprobar;
- el gate offline pasa pero la revisión visual o in-game falla;
- el test de integración exige una herramienta o permiso no disponible.

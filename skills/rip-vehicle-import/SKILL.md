---
name: rip-vehicle-import
description: "Runbook canónico para convertir un rip de source-game (source-game 'Grub': .modelbin/.swatchbin/.carbin) en un vehículo DayZ CarScript conducible y texturizado — el pipeline repetible destilado del coche #1 (SUB_BRZ, ~30 sesiones → objetivo ≤5). Contiene SOLO las reglas finales verificadas in-game: pipeline de 12 pasos, checklist day-1 del coche nuevo, budgets de entrada, reglas de winding/glass/interior/materiales/estructura, reparto de lanes Claude/Codex y protocolo de test. Usar cuando: llega un zip/rip nuevo de source-game ('coche #2', 'nuevo coche del amigo', 'importar de source-game', 'empezar el siguiente coche'), se retoma el pipeline VehicleImport, o se duda de una regla del import (winding, cristales, LODs, budgets, transform). La historia/RCA de cada regla vive en dayz-vehicles/references/rip-import.md (changelog) — esta skill es el procedimiento operativo; ante conflicto entre ambas, manda ESTA."
---

# source-game → DayZ: runbook canónico (v1, 2026-07-11)

> Destilado del build SUB_BRZ s2..s32 + research dual consolidado
> (`VehicleImport\reviews\2026-07-11-research-metodo-import.md`). Reglas SOLO en su estado
> FINAL verificado; el porqué histórico (RCA, red herrings, supersedidos) está en
> `dayz-vehicles/references/rip-import.md` — consultarlo como historia, NO como
> procedimiento. Workspace: `C:\Users\<you>\VehicleImport` (NON-OneDrive). Orquestador:
> `scripts\import_car.py --car profiles\<car>.json`.

## Las 3 reglas de proceso que compran todo lo demás

1. **Ningún fix visual sin sonda de mecanismo medida + fixture negativa.** Los ~10
   rebuilds perdidos del coche #1 fueron hipótesis sin medición validadas in-game. Sonda
   primero (raycast/census/probe multiángulo), fix después, gate permanente al cerrar.
2. **Performance es requisito de ENTRADA, no fase de rescate.** Budgets e
   inventario de LODs autorados ANTES de ensamblar nada (paso 2). El BRZ a 231k caras =
   freeze de 10s; vanilla sedan = 14.6k.
3. **Offline nunca aprueba visuales**: el mejor veredicto offline es `NEEDS_INGAME`; el
   render del motor (smoke MCP → ojo del usuario SOLO al final) es el único juez visual.
   2 rebuilds sin progreso = STOP y re-diagnóstico (jamás un tercero a ciegas).

## Checklist DAY-1 (coche nuevo — todo offline, sin tocar geometría)

1. Unzip a `VehicleImport\rip\media\cars\<car>\` (junction si viene de otro lado). La
   `_library` de COCHES compartida ya está en `rip\media\cars\_library\` (verificar que
   los materialbins que el coche referencia resuelven — patrón 13/13 del BRZ).
2. `profiles\<car>.json` desde la plantilla (ver `references/profile-schema.md`): bloque
   `source` + budgets `intake` + policies. NO copiar las `exceptions` quirúrgicas del BRZ.
3. Step `manifest`: inventario (INCLUDE/EXCLUDE/SHADOW `__slod`/far-LOD-shells por bitmask
   `LODs=` /mirror-gaps RF `[ -f ]` probe) → `source_inventory.json`. Trampas fijas:
   parte custom solo-`__slod` (la visible es la estándar) · `*wide*` = flares bolt-on
   ENCIMA del shell (`body_a` SIEMPRE incluido — quitarlo borra el techo) ·
   `interior_a`-far-shell (LODs sin bits {0,1}) NUNCA como geometría close-view ·
   suspension/undercarriage SE INCLUYEN (re-posadas; las ruedas se apoyan visualmente) ·
   piezas MÓVILES (puertas/capó/maletero) = models PROPIOS ya cortados en el rip con eje
   en `Locators.xml` → clasificarlas como LANE PROPIA desde el day-1, NUNCA fundirlas al
   body ni planificar recorte manual (ver sección 2026-07-17 abajo).
4. Material map por-mesh (`rip_material_map.py`): TYPE por carpeta del materialbin
   (el NOMBRE de instancia miente — rollcage "leather_MGL" es METAL). Multi-material =
   normal (50/84 en BRZ) → por-mesh obligatorio, per-part es solo hint.
5. Color: `ManufacturerColors.bin` entry[0] (decoder `decode_color2.py`) — NUNCA a ojo.
6. Masa/drivetrain/reparto: stats públicos FH6 (game8/kudosprime/calculators.games) —
   el GameDB va cifrado (no minarlo, no subirlo a backends de terceros). Cross-check
   wheelbase de `Locators.xml` vs specs reales = valida ejes/unidades.
7. Dims/memoria: `Locators.xml` `SceneTransform _41/_42/_43` = x/y/z (y up, z long).
8. Gate intake: `lod_plan.json` (LOD autorado por pieza que cumpla el budget) — FAIL si
   ninguna combinación entra en presupuesto. Decisiones pendientes (variante
   stock/widebody, plazas, extras) → `pending_decisions[]` y SE PREGUNTAN, sin defaults.

## Pipeline canónico (12 pasos; steps de `import_car.py`)

| # | Paso | Regla dura | Gate |
|---|---|---|---|
| 1 | Intake + truth maps (day-1 arriba) | sin defaults silenciosos | inventory + NEEDS_DECISION |
| 2 | Budgets + lod_plan | visual ≤ ~120k caras · VP subset ≤16k resolved · shadow ≤5k · uniqUV>1 · dup_rate<2% | intake gate FAIL-loud |
| 3 | Import multi-LOD Blender headless | transform neto `(−Fx, Fy+Y0, −Fz)` det+1, verificado ≥3 anclas (G0 fail-stop) | G0 |
| 4 | Normalización topológica | dedup payload-aware PRIMERO → repair minoría flood-fill MAYORÍA (allowlist censada; conflicto nuevo = FAIL) → normales smooth(+cross) del winding FINAL. PROHIBIDO: flip global, orient-a-oráculo, fix desde fotos | Gb/Gb+ + winding_differential |
| 5 | Arquitectura visual | shell real LOD0 (paint hiddenSelections + luces) + chunks proxy <65535 resolved + `prox_int` dedicado (full res1.0 + subset 1100) + shadow dissolve 40° + ladder autorada por distancia | budgets + lod_semantics |
| 6 | Glass (subpipeline) | panes dobles del rip CONSERVADOS (par ext/int legítimo) · material clon vanilla `glass.rvmat` (α 0.22-0.32, noZwrite) · single-sided · twins/double-side = excepción MEDIDA · cierre estructural SOLO con gap demostrado por sonda multiángulo · knobs BRZ (E_flip/C1/sunk) = profile, no doctrina | glass_occ + probes |
| 7 | Estructural (`rip_p3_structural`) | componentNN DUAL-TAG (hubs/seats 100% overlap) · bone-companion por attachment proxy · ViewGeo seats INWARD + flags 0x02000000 · `#Mass#` SOLO Geometry · `refill` (no fuelpoint) · hitpoints==firegeo dmgzones==config | verify_rip_car U+P + roundtrip_structural + positive control sedan |
| 8 | Proxies | path SIN `.p3d` (default; hay contraejemplo registrado → ante duda, verificar contra control) · frame por lado: x<0 `((-1,0,0),(0,0,1),(0,1,0))`, x>0 `((1,0,0),(0,0,-1),(0,1,0))` · companions `wheel_X_Y` en visual+View+Fire · geometría MODEL-SPACE sin centrar · NUNCA `add_proxy` sobre uno existente (pierde frame) | proxy identity checks |
| 9 | Config/script (lane Codex) | `<MOD>_Base.c` extends CarScript SIEMPRE (CrewCanGetThrough/GetAnimInstance/GetSeatAnimationType; sin ella get-in JAMÁS aparece) · CfgMods `dir=` + backslashes · SimulationModule HEREDAR (no re-declarar) · slots vanilla `CivSedanWheel_*` · petrol = SparkPlug vital + GlowPlug→false · OnDebugSpawn COMPLETO (kits idénticos mod-vs-control) · matriz paridad PAR-001..017 | CfgConvert + parity diff |
| 10 | Texturas | TYPE→rvmat de tabla fleet · solo carpaint en selección paintable · PLASTIC NUNCA re-tipado (flares pintados) · `_co` solid UV-invariant + swatch por TEXCOORD2 · cabina de FUENTE REAL (materialbins `_library` + UI `TOY_*`; jamás paleta inventada) · specular alto amplifica artefactos del `_nohq` | TYPEMAT unknown=FAIL + surface_integrity |
| 11 | Deploy | TRANSPLANT (jamás pisar los struct LODs del desplegado) · staging atómico + build identity · `.bak` FUERA del árbol compilable · `-Build -PackOnly` (PackOnly solo = PBO stale) · `-include` REEMPLAZA la copy-list (dropea .paa/.rvmat = white car) | G7 0-missing + identity + perf_budget |
| 12 | Test | suite offline → `NEEDS_INGAME` → smoke MCP (spawn + capturas estándar + raycast + get-in probe) → drive ladder → **usuario: OK estético + feel, UNA pasada agrupada** | vehicle_smoke JSONL (INGAME_PASS real, nunca prompt-only) |

## Smoke MCP (paso 12) — gotchas de entorno fijos

- `world_spawn` espera vector MOTOR `[x, y_up, z]` (el connect-log imprime `[x,z,y_up]`).
- `camera_set` SUPRIME los controles del player → solo con box vacía; para 1PP:
  `vehicle_get_in_client` y capturar SIN camera_set.
- Captura con display dormido = frame negro → foreground + input wiggle antes.
- Launch server/cliente vía `.bat` con `start ""` (detached); poll UDP 2302 (no TCP).
- Box DayZ = EXCLUSIVA entre sesiones; verificar dueño del puerto por `@Mod` antes de
  matar nada (proceso ajeno = NO tocar). Misión STOCK del server, no la dev.
- RAM <2 GB libre con working sets bajos = zombies de kernel → pedir REINICIO antes de
  rebuild/launch.

## Reparto de lanes (modelo operativo)

- **Claude**: arquitectura y specs (con causa medida + fixture), orquestación del loop
  in-game (MCP host), juez visual de capturas, verificación independiente de CADA
  entrega (regenerar artefacto + gate real — jamás aceptar el exit 0), vault/memoria.
- **Codex** (end-to-end bajo spec): builders Python TDD, gates+fixtures, config/model/
  script con firmas verificadas, física numérica, cirugía `.p3d` determinista en work,
  Blender headless, reviews R21/R22, 2ª opinión sobre capturas (`codex exec -i`).
  Límites: sin veredicto engine, sin estética, sin deploy fuera del workspace, 1 exec
  concurrente, CUOTA COMPARTIDA entre sesiones (presupuestarla; muere fail-fast con
  "usage limit"), preflight fail-closed (P:\ montada antes de lanzar).
- **Usuario**: decisiones de gusto (stance/color/decimación visual — SIEMPRE gated),
  OK estético final sobre contact-sheet, feel de conducción.

**Prompt de handoff a Codex (7 puntos, siempre):** spec aprobada + archivos permitidos ·
inputs con hashes · firmas/APIs con path:line verificadas · fixtures pos/neg + exit
codes · comandos de gate + criterio de parada · prohibiciones (no deploy, no refactor
incidental, no tocar profile fuera del bloque) · output = diff+tests+JSONs+hashes+
unknowns + `NEEDS_INGAME` explícito. Skill `codex-handoff-template` para el armazón.

## Referencias

- `references/profile-schema.md` — el `profiles\<car>.json` campo a campo.
- `dayz-vehicles/references/rip-import.md` — historia/RCA (por qué cada regla).
- `dayz-vehicles/references/vehicle-structural-parity.md` — contrato estructural motor.
- `dayz-vehicles` SKILL.md preflight #1-#15 — checklist genérico de vehículo DayZ.
- `VehicleImport\reviews\2026-07-11-research-metodo-import.md` — el research consolidado
  que fija prioridades y este runbook.

## (added 2026-07-14 s34) Lift / traslacion de geometria: NO doble transformacion con chunks proxied

Al subir/trasladar geometria de un coche cuyos CHUNKS se instancian en el shell (sub_brz.p3d)
via PROXIES (proxy:\<MOD>\proxies\brz_chunk_*), el desplazamiento EFECTIVO de cada chunk =
delta del anchor del PROXY (en el shell) + delta de la GEOMETRIA local del chunk. Subir AMBOS
= doble (2x). Origen s34: un "subir el coche +7cm" subio +0.07 los proxies de chunk EN
sub_brz Y +0.07 la geometria de cada chunk = +0.14 efectivo -> carroceria descuadrada con
huecos, discos de freno flotando (proxy de chunk_03 +0.07, discos dentro en su Y original) y
coche flotando (Geometry del chasis subida). Diagnostico triple-confirmado (Claude + 2 Codex).

Reglas:
1. Subir la geometria del HIJO (chunk) O el anchor del PROXY, NUNCA ambos. Recomendado:
   geometria-only en los assets hoja; proxies de chunk en IDENTIDAD (anchor sin tocar).
2. Chunks MIXTOS (partes sprung + unsprung, p.ej. chunk_03 tunel+frenos, chunk_04
   trim+suspension): NO mover el proxy entero. PARTICIONAR por componente/seleccion
   (frenos/suspension/hubs FIJOS; body/trim +delta). Cero solape de puntos entre grupos.
3. Geometry LOD: subir el chasis (componentNN de body), NO los hubs (component de rueda +
   wheel_*_damper_land). #Mass# es escalar (no depende de Y): la masa no cambia, el CoM si.
4. Ruedas/frenos/suspension NO se mueven (tocan el suelo). OJO: drivewheel es el VOLANTE
   (steering), NO road-wheel -> se mueve con el body, no se deja fijo por error del clasificador.
5. GATE obligatorio = delta EFECTIVO (parent_delta + local_delta) por instancia, NO el delta
   local por archivo. Fixture negativa: parent +d + child +d (=+2d) DEBE fallar. En s34 el
   census verifico cada archivo a +0.07 pero NO el efectivo -> paso el gate y rompio el coche.
6. Ride-height por config (suspension stiffness/travel) NO da offset exacto verificable + cambia
   handling; para un lift exacto usar geometria. La flotacion post-lift = NEEDS_INGAME (medir
   root/contacto/suspension en Diag; NO parchear bajando la Geometry).

Ref: VehicleImport\work\s34_stance_audit_A.md (spec completa) + <notes>\AI\30_Sessions\2026-07-14-SUB_BRZ-s34.md.

## (added 2026-07-17 s36) Puertas y piezas móviles: el rip YA las trae cortadas — mirar Manifest ANTES de planificar recorte

source-game versiona cada pieza móvil como model INDEPENDIENTE (source-game las anima —
`MojoConfig.xml` `doorLF/RF`). En el Manifest: `scene\exterior\doors\door<lf>_a.modelbin`
(chapa, LODs autorados) + `doorhandle<lf>_a` + `doorjamb<lf>_a` +
`scene\interior\doors\doorcard<lf>_a` (panel interior). Solo lado L (R = espejo, patrón
RF estándar). Ejes de bisagra LISTOS en `Locators.xml`: `carLocator_door{LF,RF}` (+
`doorHandle{LF,RF}`, `entryDoorLF`) = el axis que `class Doors`/AnimationSources necesita,
con el MISMO transform que la geometría.

Reglas:
1. Day-1: clasificar doors/hood/trunk como lane propia (assets separados + axis de
   locator). El body se ensambla SIN ellas; la puerta entra como attachment/proxy con rig.
2. Si un ensamblado previo las fundió al body (chunks), el recorte se resuelve por MATCHING
   geométrico contra la pieza del rip transformada (tri_signature/centroides) — NUNCA
   marcado manual en Blender.
3. Al cerrar una fase que CONSTRUYE un artefacto (p.ej. puertas .p3d con su escalera de
   LODs), registrarlo en el LIVE-STATE con ruta + checkpoint: SUB_BRZ s34/s35 planificaron
   "marcado manual de doorcards" con las puertas YA construidas en
   `work\s33_f2_doors\` (C2b) — dos sesiones presupuestando un no-problema.

Origen: SUB_BRZ s36 (2026-07-17). RCA: dayz-vehicles/references/rip-import.md §"DOORS".

## (added 2026-07-18 s37) Attachment-render: frames de proxy + calibracion de locators

1. **El attachment se renderiza desde el proxy del LOD visual con su FRAME** (regla
   completa = dayz-vehicles preflight #21): frame por lado del paso 8 (ruedas) o el frame
   uniforme medido del control (puertas `((-1,0,0),(0,0,1),(0,1,0))`), en TODOS los LODs
   visuales + VG + FG, point flags 63, y clase `Proxy*` == basename del archivo
   (case-insensitive; `_ruined` vs `_destroyed` mato el cliente al swap — B5). Un frame
   identity (py3d `rotation=None`) = pieza rotada ~90 escondida con sim intacta (B1).
   Gate: `derive_proxy_frame` == esperado + fixture negativa identity. Diagnostico
   "attached pero invisible": medir FRAMES antes que LODs del item (la hipotesis
   LOD-0.0-del-item quedo refutada in-game s37).
2. **Locators.xml -> frame DayZ, calibracion EMPIRICA s37** (4 wheel locators vs anchors
   desplegados, match a 6 decimales): `dayz_x = -Fx`, `dayz_z = -Fz`; el datum Y del
   locator NO es fiable (los anchors se normalizaron; deriva mm entre ruedas) -> la Y se
   deriva de la geometria de la pieza. Eje de bisagra del BRZ = vertical puro (columna up
   del SceneTransform). Calibrar SIEMPRE contra un anchor desplegado conocido antes de
   consumir un locator nuevo.

## (added 2026-07-17 s38) Gate de RENDER headless por contenedor — los censos estructurales NO refutan defectos visuales

Un censo (counts/bbox/flags/selecciones/materiales) prueba estructura, NO pose ni render:
una barra de luces TUMBADA sobre el techo cabe en la misma bbox que una de pie, y dos
rondas de fixes (s37/s38) cerraron gates offline verdes con el coche roto in-game. El
render Blender headless del contenido CRUDO de cada contenedor (OBJ por LOD + workbench,
3 angulos) detecto a la primera lo que ningun censo vio: barra tumbada + paragolpes
duplicado flotante en chunk_00, rotos EN ARCHIVO desde s33 e identicos a la captura
in-game del usuario (equivalencia archivo=render=juego validada). Reglas:

1. GATE OBLIGATORIO pre-deploy de toda pieza visual nueva/editada: render antes/despues
   del contenedor COMPLETO (no solo la pieza tocada). Pipeline reusable:
   `VehicleImport\work\s39_f0_audit\render_all_chunks.py`.
2. Un diagnostico "archivos sanos" emitido solo con censos NO autoriza atribuir el
   defecto a runtime: renderiza antes de descartar datos.
3. Matching de cobertura NUNCA contra una referencia derivada del propio artefacto a
   validar (la "receta lod0" de puertas describia el item roto -> gate tautologico que
   costo una ronda entera: las caras "sin match" eran precisamente los huecos).
4. Materiales de panes/cristales: leer el ALPHA REAL del rvmat antes de portar caras a
   el (el `glass_i.rvmat` vanilla es alpha-0 en todos los canales = invisible por
   diseño; un "fix" que añade geometria con ese material añade cristal invisible).


## (added 2026-07-17 s39) El cristal del rip source-game nace SINGLE-SIDED cosido HACIA DENTRO -> invisible desde fuera; doble-cararlo

Dos premisas de un research pueden caer a la primera con el gate de render aplicado al
ARTEFACTO DEL QUE SE QUEJA EL USUARIO (no solo al fix). En SUB_BRZ s39, render directo
del desplegado falso: (a) la "barra de luces volcada" era `bodyfoglights_a` en su POSE
AUTORADA (barra de pods de techo del rip; match sub-mm) -> no-defecto; (b) los "boquetes
en la puerta" no eran huecos de chapa (la chapa renderiza solida con backface-cull ON) ->
eran las VENTANILLAS invisibles. Causa real unica de parabrisas + ventanillas + "boquetes":

1. **El cristal del rip source-game (glass.rvmat, *privacy*, *tint*) llega SINGLE-SIDED y cosido
   con el winding HACIA DENTRO** -> el motor lo descarta por backface culling desde el
   exterior -> invernadero invisible/hueco. Prueba definitiva y barata: render backface-cull
   ON vs OFF de solo las caras de cristal desde fuera; si con OFF ves el invernadero entero
   y con ON casi nada, es winding-inward. NO es alpha (subir alpha no hace aparecer una
   cara descartada por culling).
2. **Fix = doble-carar el cristal VISIBLE** (glass.rvmat/privacy/tint; NUNCA glass_i que es
   alpha-0 invisible por diseno): por cada cara de cristal, anadir una gemela con vertex
   order invertido + normal negada, en TODOS los LODs visuales (incl. la escalera de los
   items de puerta). Desde cada lado renderiza exactamente UNA de la pareja (la otra la
   descarta el culling) -> sin apilado de alpha, ventanilla visible por ambos lados.
   Patron reusable: `make_double_sided.py` FILTRADO por material de cristal (scoped);
   struct LODs intactos byte a byte (get-in de las puertas). Es la "excepcion MEDIDA" que
   la regla de glass (paso 6) contempla: aqui el rip NO trae pares ext/int legitimos, trae
   single-sided-inward -> doblar es correcto, no conservar.
3. **Gate del fix = DATO, no Blender.** El backface-cull de Blender sobre un OBJ importado
   NO refleja el winding DayZ (Blender recomputa normales; before/after salen identicos).
   Verifica por-pane que ahora hay winding en AMBOS sentidos (signo de cross.radial) +
   count de cristal x2 + no-cristal intacto + struct byte-parity. El gate VISUAL real es
   in-game (la skill ya lo dice: Blender no juzga winding DayZ).
4. **Metodo (extiende el gate de render de s38): renderiza primero el ARTEFACTO de la
   queja para confirmar el MECANISMO del defecto, ANTES de especificar el fix.** Ahorra
   reconstrucciones de no-problemas: aqui evito reconstruir la puerta (chapa ya solida) y
   subir alpha (defecto era winding), redirigiendo a doble-cara de cristal, todo offline
   antes de un solo build.

## Gate de linaje de winding

[EXACT][CLAIM-R21-RIP-WINDING-LINEAGE]
`VehicleImport/scripts/winding_lineage_gate.py` compara el winding por cara del
target contra el `source_face_id` sellado y deriva la relación esperada del
determinante: positivo = `PRESERVE`, negativo = `REVERSE`. Emite
`SOLID|INVERTED|MIXED` con exits `0|1|2`; manifiesto, linaje o determinante
ausente/no finito/cero falla cerrado como `MIXED`.

Este gate prueba **preservación de linaje**, no corrección visual o de colisión.
El A/B in-game y los controles de ViewGeometry siguen siendo el gate final. La
suite focal de linaje pasó 16/16 el 2026-07-24; no se congela un total global
de tests porque el árbol fuente sigue evolucionando.

## Override de tipo de material por identidad exacta

[EXACT][CLAIM-R21-RIP-MATERIAL-OVERRIDE] Una excepción de material puede
declararse en `source.material_type_overrides`, pero solo por identidad exacta
`part + mat_name + mat_path`. Debe coincidir con exactamente un mesh visible o
el mapa falla cerrado; conserva el tipo previo en `source_type` y registra
`override=source.material_type_overrides`.

El mecanismo está source-verificado y sus tests focales pasan. La validación
amplia del perfil BRZ conserva un fallo conocido independiente
(`builder.occ_struct` todavía presente); no usar ese fallo como evidencia
contra el override ni ocultarlo al declarar el estado del perfil.

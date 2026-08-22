---
name: grok-handoff-template
description: >
  Construye prompts para delegar en el CLI Grok Build (xAI) y parsea su salida
  JSON. Cinco roles: research ciego, autoría de plan a ciegas, reconciliación
  del consolidado (AGENTS-R22, en paralelo con Codex), revisión de código
  (AGENTS-R21) y peer/write-to-disk — Grok escribiendo archivos como suplente
  de Codex. Cubre las posturas de contención (consejo read-only, juez
  instrumentado con shell para MEDIR, escritor, peer), modelo y esfuerzo
  (grok-4.6), imágenes por bloques ACP, --json-schema para hallazgos
  estructurados, %TEMP% + hashes y los gotchas del CLI en Windows. Dispara con
  "pregúntale a grok", "tercera opinión", "que lo vea grok", "que lo
  escriba/implemente grok", "que grok escriba su plan", "que grok lo mida",
  "mándale la captura/render a grok", "handoff a grok", "grok review", "que
  opine el council"; o cuando el usuario pegue salida de Grok. Invócala ANTES
  de escribir cualquier prompt para Grok — un flag de permiso mal puesto mata
  la corrida en silencio.
---

# Grok Handoff Template

Builder + receptor para prompts Claude→Grok Build. Hermano de
`codex-handoff-template`; comparte esqueleto y vocabulario, pero Grok ocupa un
puesto distinto en el pipeline.

**El reparto vigente (2026-08-12, `workflow.md` §Reparto): Codex por defecto en
ejecución; Grok es lane de pleno derecho en planificación.** `G7` sigue mandando
la ejecución a Codex; Grok entra con cuatro roles de juicio (research ciego,
autoría de lane de plan, reconciliación del consolidado, R21 adversarial) y como
ejecutor peer cuando Codex está bloqueado. El rumbo declarado es ir supliendo
Codex por Grok **si no hay pérdida de calidad medida**; el árbitro es el
`council-scorecard.md` del vault, una fila por finding. Hasta que ese registro
diga que la calidad aguanta, la ejecución no se muda.

## Preflight del encargo — tres preguntas antes de escribir el prompt

Las tres se pagan ANTES de lanzar, no al recibir (origen: auditoría del
scorecard sobre ~67 corridas, SP-244).

1. **¿Algo de esto se decide MIDIENDO?** (un hash, correr un gate, contar
   líneas, ejecutar una suite). Un juez sin shell no ejecuta: todo lo que
   dependa de observar comportamiento real lo **supone**, y las dos mordidas de
   ForzaDayZ T5a fueron exactamente eso. Tres salidas, en orden de preferencia:
   lo mides tú y le das el dato · postura **C (juez instrumentado)**, que puede
   ejecutar sobre una copia · se lo delegas a Codex. Lo que no vale es pedirle
   el juicio y aceptar la medida supuesta.
2. **¿Grok implementó lo que Grok va a revisar?** Implementador y revisor de la
   misma familia comparten puntos ciegos; la convergencia vale menos (principio
   del usuario, GunRacks `D-09b`). Cuando el juicio importe, la segunda voz
   cambia de familia; si no se puede, la degradación se **declara en el
   artefacto**. Y el revisor va SIEMPRE en sesión nueva ciega — nunca un `-r`
   ni un `--fork-session` de la sesión que implementó.
3. **¿Dónde se vuelca el arbitraje?** La corrida que no se vuelca muere con la
   sesión: 67 corridas de dos días quedaron sin precisión recuperable. Regla
   del receptor: **el volcado al `council-scorecard.md` se hace en el mismo
   paso en que se arbitra cada hallazgo**, no al cerrar. `--json-schema` con el
   schema de hallazgos (`references/prompt-patterns.md` §Hallazgos
   estructurados) deja ese volcado casi gratis, y
   `grok export <sessionId> <ruta.md>` archiva el transcript en `reviews/`.

Y antes de delegar por esta skill: **grep `20_Knowledge/skill-patches-pending.md`
por su nombre.** Los `pending` son la lista de bugs conocidos de la skill. Ese
grep no se hizo dos veces seguidas con el bug de `acceptEdits` y el diagnóstico
se pagó dos veces. Corolario: grep antes, y re-mide si tu observación no encaja
con lo que dice el ledger.

## Routing gate — ¿esto va a Grok, y en qué postura?

1. **¿Es una tarea de EJECUCIÓN?** (escribir código, correr scripts, producir un
   artefacto) → Codex por defecto (`G7` / `AGENTS-R20`). Si Codex está bloqueado
   —cuota, filtro, runtime muerto— o el nicho es suyo, va a Grok en modo
   **peer**: `references/write-to-disk-handoff.md`. Ese archivo es de lectura
   obligatoria antes de la primera invocación de escritura.
2. **¿Es una tarea de JUICIO?** (investigar, escribir un plan a ciegas,
   reconciliar el consolidado, revisar código) → elige rol en la tabla de abajo
   y postura en §Posturas.
3. **¿Ya opinaron Claude y Codex y coinciden?** Una tercera lane sobre algo ya
   convergente rinde poco… salvo en reconciliación, donde Grok es
   estructuralmente la lane que menos solapa (0-3/24 frente a 6/12 de
   Claude↔Codex). Gasta la cuota donde hay desacuerdo real o donde el coste de
   un fallo es alto (integridad de datos, formato persistente, release).
4. **¿Es trivial?** → hazlo tú. Cada llamada cuesta cuota (§Coste).

**La bifurcación que más cuesta equivocar** es juicio vs. entregable-en-disco.
Pedir un documento con el allowlist de solo-lectura te obliga a copiar el cuerpo
desde stdout —caro y frágil—; pedir juicio sin allowlist deja a Grok editando el
árbol sin preguntar. No se mezclan en la misma sesión.

## Los cinco roles

| Rol | Cuándo | Forma | Postura | Reference |
|---|---|---|---|---|
| **Research ciego** | `AGENTS-R24` fase 0 | Paralelo y ciego: Claude ∥ Codex ∥ Grok, sin verse | Consejo (± web) | `prompt-patterns.md` §Research |
| **Autoría de plan** | Paso 1, solo si la fase 0 fue multi-lane | Escribe SU plan con el mismo briefing, sin ver el de nadie | **A** (escribe solo el plan) | `prompt-patterns.md` §Autoría |
| **Reconciliación de plan** | `AGENTS-R22`, sobre el consolidado v1 | **En paralelo con Codex**, no en cola; arbitra causa propia y se le declara | Consejo | `prompt-patterns.md` §Reconciliación |
| **Revisión de código** | `AGENTS-R21` | Paralelo: tercer revisor adversarial independiente | Consejo o **C** si hay que medir | `prompt-patterns.md` §R21 |
| **Peer / write-to-disk** | Codex bloqueado, o nicho suyo | Escribe el artefacto él; stdout es un recibo | **A** o **B** | **`write-to-disk-handoff.md`** |

Un rol por sesión. Mezclar («revisa y luego implementa») produce el
«hice todo a medias» que ya documenta `codex-handoff-template`.

### Por qué la reconciliación va en paralelo y no en cola

Hasta 2026-08-12 el patrón era secuencial («Grok audita el v2 tras la luz verde
de Codex»). Se cambió con dos datos del scorecard: **ir el segundo sobre un plan
ya limpiado le baja el disparo** (corrida 1), y el solape medido —Claude↔Codex
6/12, Grok 0-3/24— dice que Grok es la lane que aporta distinto: ponerla a votar
después asciende el punto ciego compartido a doctrina. Ahora Codex y Grok
arbitran el MISMO consolidado, a la vez y sin verse (`workflow.md` §Flujo 2).

Tres reglas del encargo que no se negocian (espejo de `AGENTS-R22.2`):

- **Adjuntar la tabla de procedencia** y declarar el conflicto de interés:
  «este consolidado incluye y descarta partes de tu plan».
- **Evidencia > mayoría**, dicho explícito: que dos lanes coincidan no es
  argumento; sin `path:line` no vence a una lane con cita verificada.
- **Bloque `DISENSO-FUERTE`**: llega al usuario **verbatim**, sin resumir ni
  añadir veredicto propio — Claude es lane y árbitro a la vez (`⚠ árbitro=lane`)
  y el transporte literal es lo único que impide que el árbitro entierre a una
  lane.

## Posturas de contención — elige antes de escribir el prompt

| | Consejo | **C — juez instrumentado** | A — escritor | B — peer completo |
|---|---|---|---|---|
| `--tools` | `read_file,grep,list_dir` | `+ run_terminal_cmd` | `+ search_replace` | omitido |
| Puede medir | no — **lo supone** | **sí** (shell) | no | sí |
| Puede escribir | no | vía shell (no deseado) | archivos | todo |
| Workspace | el del proyecto | **copia en `%TEMP%`** | acotado en el prompt | **`%TEMP%`** |
| Uso | R24, reconciliación, R21 puro | R21/R22 con gates que EJECUTAR | docs, specs, planes | código, PBO, medición |

Consejo, A y B están desarrolladas en `write-to-disk-handoff.md`. La C es nueva
(2026-08-15) y vive aquí:

### Postura C — juez instrumentado (verificada 2026-08-15, grok 1.0.4)

Para revisiones donde el veredicto depende de una medida: comprobar un hash
contra baseline, ejecutar el gate que el plan promete, contar símbolos, correr
`py3d validate`. Sonda de estreno: calculó por shell el SHA-256 de un blob y el
conteo de líneas de un fichero — ambos exactos contra la medición host-side
(`-eq` de 64 hex), con baseline intacto y salida validada por `--json-schema`.

```bash
# Desde Bash (el arg de --json-schema lleva JSON inline; PS 5.1 lo rompe)
"$USERPROFILE/.grok/bin/grok.exe" \
  --prompt-file "C:/ruta/brief.txt" \
  --cwd "C:/Users/<user>/AppData/Local/Temp/<workspace-copia>" \
  --tools "read_file,grep,list_dir,run_terminal_cmd" \
  --deny "Bash(rm *)" --deny "Bash(Remove-Item*)" --deny "Bash(git push*)" \
  --deny "MCPTool" \
  --json-schema "$SCHEMA_HALLAZGOS" \
  --output-format json --max-turns 24 --always-approve --no-memory \
  -m grok-4.6
```

Reglas que la hacen segura, porque `run_terminal_cmd` rompe el read-only (una
redirección de shell escribe archivos aunque no tenga `search_replace`):

1. **El workspace es una COPIA en `%TEMP%`**, nunca el árbol real. La copia ES
   la contención; el denylist solo recorta lo peor.
2. **Foto de hashes** de la copia antes de lanzar si el veredicto va a citar
   «no modifiqué nada» — con shell, eso hay que probarlo, no afirmarlo.
3. En el prompt: qué comandos puede usar (dale las invocaciones canónicas:
   `certutil -hashfile`, la línea exacta del gate) y la frontera **NO lances ni
   mates procesos DayZ** — el ciclo in-game es del orquestador (lease
   `dayz-mcp`).
4. Sus medidas entran al informe como las de cualquier lane: el receptor
   re-verifica las que deciden un veredicto (`G3`).

## Invocación canónica de juicio (re-verificada contra `grok 1.0.4`, 2026-08-15)

Los roles research / reconciliación / R21-puro van SIEMPRE en solo-lectura. Un
consejero no toca el árbol.

```powershell
& "$env:USERPROFILE\.grok\bin\grok.exe" `
  --prompt-file "<ruta absoluta del brief .txt>" `
  --cwd "<workspace>" `
  --tools "read_file,grep,list_dir" `
  --deny "MCPTool" `
  --output-format json `
  --max-turns 40 `
  --always-approve `
  --no-memory `
  -m grok-4.6
```

> **`--tools` es lo ÚNICO que separa a Grok de tu árbol.** El config del host
> (`~/.grok/config.toml:17`, leído 2026-08-22) está en `permission_mode =
> "auto"`, y bajo `auto` una corrida headless **escribe sin preguntar aunque no
> pases ningún flag de permiso**: A/B medido el 2026-08-22, mismo prompt y mismo
> allowlist con `search_replace`, sin flag → `end_turn` en 2 turnos con el
> fichero en disco; con `--always-approve` → idéntico. Las canónicas lo pasan
> igualmente para FIJAR el modo pase lo que pase en el config, no porque haga
> falta para escribir. El modo de permiso no es el cortafuegos; el toolset sí, y
> esta medida lo refuerza: sin flag alguno tampoco hubo prompt. Omitir el
> allowlist no es «puede que edite algo»: es «edita y ejecuta sin preguntar».
> Re-verificado en 1.0.4:
> con este allowlist informó de que no tiene herramienta de escritura y el
> archivo pedido no apareció en disco.

Qué hace cada pieza y por qué:

- **`$env:USERPROFILE\.grok\bin\grok.exe`**: ruta portable entre hosts (la
  forma `C:\Users\<user>\...` hardcodeada rompió en el portátil). `grok` puede
  no estar en el PATH de una shell abierta antes de instalarlo.
- **`--prompt-file`, y va SOLO.** `-p` y `--prompt-file` son excluyentes
  (combinarlos = exit 2, 0 bytes). `-p` inline está PROHIBIDO desde PowerShell
  5.1 para cualquier prompt real: PS re-tokeniza comillas y saltos de línea al
  pasar el argumento al exe nativo y el CLI aborta con
  `error: unexpected argument`. Brief a un `.txt`, siempre.
- **Shell de lanzamiento**: con `--prompt-file` y args ASCII vale PowerShell o
  Bash. En cuanto un argumento lleva JSON inline (`--json-schema`,
  `--prompt-json`) **se lanza desde Bash**; y la salida se lee SIEMPRE a
  fichero o con `[IO.File]::ReadAllText(path, [Text.Encoding]::UTF8)` —
  `Get-Content -Raw` en PS 5.1 mojibakea los acentos.
- **`--tools "read_file,grep,list_dir"`** es la garantía real (ver quote).
- **`--deny "MCPTool"`** no es opcional: **el allowlist NO elimina
  `search_tool`/`use_tool`** (la pasarela a MCP). Re-verificado en 1.0.4:

  | Operación | Herramienta | Con `--deny "MCPTool"` |
  |---|---|---|
  | Descubrir MCP | `search_tool` | **NO bloqueado** — enumera el inventario |
  | Invocar MCP | `use_tool` | **BLOQUEADO** — `Denied by permission policy: deny rule on mcp` |

  Grok ve que existe `dayz-mcp` y sus herramientas, pero no puede llamarlas.
  Se filtra el inventario; no hay riesgo de mutación. Sin el deny, sí lo hay.
- **`--always-approve`** evita que la corrida se cuelgue esperando una
  aprobación imposible en headless. Con el allowlist read-only no amplía nada.
- **`--no-memory`**: la memoria cross-session está apagada por defecto y
  verificada apagada en este host, pero si alguien la enciende las lanes
  ciegas dejan de serlo sin aviso. Cuesta cero y es a prueba de futuro.
  ⚠️ **Está OCULTO en `--help`, y funciona igual.** Medido 2026-08-22: de los
  cinco flags de la invocación canónica, `--no-memory` es el único que no sale
  en los 7.122 caracteres de `--help` (control negativo: un flag inventado
  tampoco sale, así que la comprobación discrimina). No lo quites porque un grep
  a la ayuda no lo encuentre — la ausencia ahí no es ausencia del flag.
- **`-m grok-4.6`**: pin explícito (§Modelo y esfuerzo). El default del host
  ya es 4.6, pero un default puede cambiar bajo tus pies — el pin hace las
  corridas comparables.
- **`--rules "<resumen>"`** (opcional): anexa texto al system prompt en un
  bloque `<human_rules>`. Es el sitio para el resumen de las `AGENTS-R` que
  Grok no carga, y deja el brief limpio. No confundir con
  `--system-prompt-override`, que reemplaza el system prompt entero y descarta
  `--rules`.
- **`--output-format json`** para parsear (§Receptor).

`--tools`, `--disallowed-tools` y `--max-turns` **solo existen en headless**;
en la TUI se ignoran con un warning.

### El sandbox NO te protege en Windows

No uses `--sandbox` como red de seguridad aquí. La documentación solo declara
backends de kernel para Linux (Landlock) y macOS (Seatbelt), y cuando no puede
aplicarse Grok «registra un warning y continúa sin enforcement». En este host
el confinamiento real lo da el allowlist de herramientas, nada más.

## Modelo y esfuerzo

- **Modelos en este host** (medido 2026-08-15, `grok models`): `grok-4.6`
  (**default**, 500k de contexto) y `grok-4.5`. El JSON reporta
  `modelUsage.grok-4.6-build`. Toda la tabla de costes histórica de esta skill
  es de la era 4.5; las sondas 4.6 salieron ~6× más baratas por corrida
  (§Coste). Pin siempre con `-m` para que las comparativas signifiquen algo.
- **`--reasoning-effort`** (alias `--effort`; documentados: `none, minimal,
  low, medium, high, xhigh, max`):
  - **Contratos one-shot** (constructor/juez de un disparo con `--json-schema`,
    con o sin tools): **`low` obligatorio**. En `high`/`xhigh` grok-4.6 entra
    en modo agéntico y devuelve una declaración de intenciones en el campo del
    schema en vez del artefacto — reproducido en 5 corridas, con `--max-turns`
    1/4/8 y con `--no-plan`. Parece pereza del modelo y es decapitación.
  - **Roles de juicio multi-turno** (R21/R22/research): sin flag (default del
    CLI) es lo verificado. Si un veredicto parece superficial, subir a `high`
    es un experimento pendiente de medir — no está demostrado que mejore un
    R21, solo que sube el coste.
- La suscripción actual ya cubre grok-4.6 con efforts hasta `xhigh`; el techo
  es cuota, no tier.

## Mandarle imágenes (headless multimodal)

Verificado en ambos hosts (portátil 1.0.3, sobremesa 1.0.4). Para DayZ esto
habilita lanes de revisión visual: renders del visor, capturas in-game,
referencias de Forza.

- Grok headless **no tiene `--image`**. Las imágenes van como bloques de
  contenido **ACP** dentro del prompt:
  `[{"type":"text","text":"..."},{"type":"image","data":"<base64>","mimeType":"image/png"}]`.
  El formato Anthropic (`source:{...}`) se rechaza con
  ``Invalid ACP content blocks: missing field `data` ``.
- **Los bloques van por `--prompt-file`** (el archivo se parsea como content
  blocks cuando contiene JSON), NO por `--prompt-json` inline: la línea de
  comandos de Windows tiene un techo de **32.767 chars** y un solo render en
  base64 lo revienta (medido: 29.826 pasa, 150.026 muere con
  `Argument list too long`).
- `--tools ""` acepta cadena vacía y produce la corrida de 1 turno sin
  herramientas que exigen los contratos «cero tool calls». Con
  `--reasoning-effort low` produce el artefacto; con `high`/`xhigh` lo decapita
  (§Modelo y esfuerzo).
- Lanzar desde Bash (el `--json-schema` acompañante lleva JSON inline).
- Adaptador de referencia que encapsula todo esto:
  `AI/10_Projects/AssetLab/tools/grok_arm.py`.

## Grok ya lee tu configuración de Claude Code

Esto no hay que montarlo — verificado con `grok inspect` sobre el proyecto:
carga tu `CLAUDE.md` global y los `Claude.md`/`Agents.md` del proyecto, tus
skills de `~/.claude/skills/`, tus plugins, tus MCP servers de `~/.claude.json`
y tus hooks (los hooks corren fuera del toolset del modelo — un allowlist
estricto no dice nada sobre lo que hagan ellos).

Dos consecuencias para el builder:

1. **No repitas las reglas en el prompt.** Cítalas por número igual que con
   Codex. Ojo con el namespace: las reglas que Grok lee de `CLAUDE.md` son
   `G-` y `DZ-R`; **`AGENTS-R21/R22/R24` viven en `~/.codex/AGENTS.md`, que
   Grok NO carga**. Resume su contenido en una línea, o pásalo por `--rules`.
2. **La independencia es de razonamiento, no de contexto.** Las tres lanes leen
   el mismo `CLAUDE.md`, así que comparten sus puntos ciegos. Vale para
   arquitectura y hechos medidos; no asumas que tres lanes convergentes
   garantizan ejecutabilidad (`LL-231`).

## Coste y cuota

Estás autenticado por suscripción (`grok.com`), sin `XAI_API_KEY`. El JSON
devuelve `total_cost_usd` (y `total_cost_usd_ticks` desde 1.0.4), que es
**contabilidad equivalente-API**, no un cargo aparte; lo que consume es cuota.

Era grok-4.5 (2026-08-03/07), medido en este host:

| Uso | Tokens | Coste | Tiempo | Turnos |
|---|---|---|---|---|
| Sonda trivial, directorio vacío | 30k | $0.064 | ~15 s | 2 |
| Pregunta de opinión con lectura de sus docs | 97k | $0.137 | ~40 s | 3 |
| **R22 completo sobre un plan grande** | **523k** | **$0.431** | **5,1 min** | **9** |
| **Follow-up con `-r <sessionId>`** | **107k** | **$0.051** | **38 s** | **1** |

Era grok-4.6 (sondas 2026-08-15, effort low):

| Uso | Tokens | Coste | Turnos |
|---|---|---|---|
| Juez read-only, 3 tareas | 55k | $0.010 | 3 |
| Postura C: SHA por shell + `--json-schema` | 36k | $0.008 | 2 |
| Imagen + schema, cero tools | 27k | $0.009 | 1 |

Consecuencias operativas:

- El precio por token de 4.6 es ~6× menor que lo que presupuestaba la tabla
  4.5. Re-presupuesta a la baja, pero mide tus primeras corridas serias antes
  de fiarte de la extrapolación.
- **Guarda el `sessionId` que devuelve el JSON.** Repreguntar con `-r` costó
  el **12%** de la revisión original (lee de caché, no vuelve a abrir
  ficheros). Las repreguntas son baratas: aprovéchalas en vez de abrir sesión
  nueva.
- El `--cwd` decide el contexto que carga. Apuntar a un proyecto con un
  `CLAUDE.md` de ~8k tokens lo paga en cada llamada nueva. Acota el alcance en
  el prompt (rutas concretas, no «revisa el mod»).
- `--max-turns` como backstop está bien, pero no lo aprietes: el R22 real usó
  9 turnos de los 60 permitidos; un peer real gasta 29-49.

## Presupuesto de invocación — dónde se va la cuota de verdad

Auditoría del 2026-08-15 sobre `~/.grok/logs/unified.jsonl` y las 314 sesiones
en disco (3→15 ago, sobremesa + portátil): **34,85M de tokens frescos** sobre
352M de contexto procesado. El 90,6% del contexto viaja cacheado, así que lo
que se paga es el fresco, y tres sumideros lo explican casi entero. Ninguno es
«Grok razona de más»: el reasoning es el 51% del output, pero el output entero
son 5,9M contra 34,85M de entrada.

| Sumidero | Peso | Qué es exactamente |
|---|---|---|
| **Abrir sesión** | **18,8%** | 21.377 frescos de media en el PRIMER turno (≈2,8 turnos normales), × 26 sesiones nuevas al día |
| **Qué se lee** | `read_file` = 69,9% del tool_result | El 80,8% de las lecturas YA usa rango: el problema no es leer sin rango, es *qué* fichero se abre |
| **Fan-out** | **14,3%** (4,99M) | 44 sesiones subagente |

### 1. Abrir sesión cuesta ~2,8 turnos antes de preguntar nada

El primer turno paga el `CLAUDE.md` del `--cwd`, el system prompt y la carga
inicial completa; sólo a partir del segundo entra el caché. Por eso el
follow-up con `-r` sale al 12% (§Coste): no es que sea barato, es que el resto
ya está pagado. **El default para seguir con el mismo material es `-r`; abrir
sesión nueva es la excepción y conviene saber por qué se abre.** El síntoma de
que se está pagando de más: `LFHeli_Base.c` se leyó 322 veces y
`LFPG_NetworkManager.c` 305 en el periodo — dentro de una sesión eso es caché,
repartido entre sesiones nuevas es fresco cada vez.

La excepción no se negocia y ya está en el preflight §2: **un revisor que debe
ser ciego va en sesión nueva**, nunca en `-r` ni en `--fork-session`. Ahí el
arranque no es desperdicio, es el precio de la independencia.

### 2. La carga inicial se cita por sección, no por ruta

Una lectura de skill pesa **6× una de código**: 24.904 chars de media frente a
4.044. Los reincidentes medidos son `dayz-vehicles/SKILL.md` a **151.362 chars
por lectura** (~48k tokens de un golpe), `codex-handoff-template/SKILL.md` a
66k ×7 y `LFHeli_dev/HANDOFF.md` a 66k ×7. En total 3,65 Mchars en ficheros de
skill ≈ 1,18M frescos.

Esto no se arregla leyendo menos, sino apuntando mejor: en §Estructura del
prompt punto 2, cuando la ruta es una skill grande o un HANDOFF, va **con la
sección y el rango de líneas** que aplica al ángulo del encargo. Un índice de
150k chars no aporta contexto al 90% que no toca la tarea — sólo desplaza al
brief del sitio donde el modelo mira.

### 3. El fan-out no es el problema; releer el sustrato sí

El batch del 2026-08-10 (33 subagentes sobre LFPowerGrid, pedidos explícitamente
por el usuario) salió **bien diseñado y conviene repetirlo**: Jaccard medio
**0,11** entre los 33 pares —prácticamente sin solape—, 196 ficheros distintos
cubiertos, un ángulo nominado por agente y un partial `.md` numerado por
informe. **El número de subagentes lo fija la cobertura, no una cuota**; poner
techo habría dejado ángulos reales sin cubrir.

Lo que sí se pagó dos veces: **56 ficheros los abrieron ≥5 subagentes**
(`LFPG_NetworkManager.c` ×26, `LFPG_Defines.c` ×21, `LFPG_RPCServerHandler.c`
×17), cada uno fresco. Para eso está `resume_from` (`~/.grok/docs/user-guide/
16-subagents.md:177-184`): el hijo «inherits the source's transcript, tool
state, and model», y el fuente debe estar completado, ser de la sesión actual y
del mismo tipo de agente. El caso de libro estaba en el propio batch —un
encargo de *«DEEP second-pass review of ONLY LFPG_NetworkManager.c (~279KB)»*
debería colgar del que ya lo leyó.

**Y el caveat que decide cuándo NO usarlo:** heredar el transcript **ancla**.
En una lane ciega o adversarial la independencia *es* el producto, así que ahí
se paga la relectura a conciencia. `resume_from` es para pasadas secuenciales
sobre el mismo material, no para ahorrar en lanes que debían ser ciegas.

Parámetros reales de `spawn_subagent` (medidos sobre 44 llamadas): `prompt`,
`description`, `subagent_type`, `capability_mode`, `background`, `isolation`,
`resume_from`, `cwd`. **No hay parámetro de herencia de contexto del padre** —
la única herencia disponible es `resume_from` entre hermanos.

> **En TUI los flags de contención no existen.** `--tools`,
> `--disallowed-tools` (incluido `Agent` / `Agent(tipo)`) y `--max-turns` son
> headless-only. El batch del 10-08 corrió en TUI, donde lo único que acota el
> fan-out es `[subagents]` en `~/.grok/config.toml` (`enabled`,
> `[subagents.toggle]` por tipo, `[subagents.models]` para fijar modelo). Si
> delegas un encargo grande por TUI, el presupuesto va en el encargo o no va.

## Receptor — parsear la salida

Con `--output-format json` la respuesta es un objeto único. Campos que
importan:

| Campo | Uso |
|---|---|
| `.text` | La respuesta en prosa. |
| `.structuredOutput` | **Con `--json-schema`, consume ESTE campo, nunca `.text`** — el text puede traer JSON espurio de turnos intermedios (visto en sonda: un «PENDING» antes del definitivo). |
| `.sessionId` | Para repreguntar sin re-pagar contexto (`-r <id>`) y para `grok export`. |
| `.total_cost_usd` | Contabilidad de la llamada. |
| `.usage.total_tokens` | Diagnóstico de por qué costó lo que costó. |
| `.stopReason` | `end_turn` = completó. Otro valor = se cortó, sospecha. |
| `.num_turns` | Turnos internos consumidos. |

Reglas duras del receptor (las mismas que con Codex, y por la misma razón):

1. **Verifica cada `path:line` que Grok cite, contra el archivo real.** Un
   hallazgo bien redactado con una cita inventada es el modo de fallo caro.
2. **Un hallazgo de una sola lane es candidato, no hecho.** No lo promuevas a
   memoria durable ni a una skill hasta que cierren las lanes (`LL-218`).
3. **Si Grok y Codex se contradicen en severidad, no votes.** Arbitra con
   evidencia: verifica cada hallazgo del más severo contra el código real Y
   contra el baseline previo, y clasifica en CONFIRMED-regresión / PREEXISTING
   / FALSE-POSITIVE. Patrón completo en `codex-handoff-template` §Arbitraje
   3-vías. **Evidencia > mayoría** — dos lanes de acuerdo sin cita no vencen a
   una con cita verificada.
4. **`stopReason != "end_turn"` invalida el análisis**: la respuesta está
   truncada aunque parezca completa. Con `text` cortísimo además = flag de
   permiso mal puesto, no falta de capacidad — no rediseñes el prompt.
5. **Follow-up de calibración SIEMPRE** (no solo ante sospecha): va 4/4 sin
   salir nunca en blanco, cuesta ~10-12% de la corrida y en 2 casos corrigió al
   orquestador. Plantilla en `prompt-patterns.md` §Follow-up.
6. **Si adjudicas NO-APLICAR un hallazgo, expón el arbitraje al revisor** en la
   repregunta e invita a rebatir con cita («si tienes evidencia fichero:línea,
   este es el momento; sin ella queda cerrado»). Convierte el desacuerdo en
   cierre explícito en 1 turno; imponerlo en silencio cría hallazgos zombie que
   reaparecen en la siguiente revisión.
7. **Volcado al scorecard en el mismo paso que el arbitraje** (preflight §3), y
   `grok export <sessionId> <reviews/...>.md` si la corrida merece archivo.

## Estructura del prompt

Mismo esqueleto que un prompt de Codex, con una diferencia: en los roles de
consejo Grok no escribe archivos, así que el output vuelve por stdout. En
autoría/peer se invierte: el bloque «ESCRITURA OBLIGATORIA» es lo primero, y lo
que vuelve por stdout es solo un recibo.

1. **Tarea en una línea**, con la frontera de alcance.
2. **Carga inicial** — rutas absolutas que debe leer, con el porqué de cada
   una. Máximo ~7; si necesitas más, el alcance es demasiado ancho.
3. **Fronteras** — `NO leas X`, `NO propongas Y`, `NO salgas de Z`.
4. **Reglas que aplican** — resumidas si son `AGENTS-R` (no las carga), o por
   `--rules`.
5. **Bloques de salida** — ver `references/prompt-patterns.md`. Pide siempre
   una sección explícita de «lo que NO pude verificar»: es la que separa un
   hallazgo de una conjetura, y sin pedirla no aparece.

## Anti-patrones

1. **Usar Grok donde tocaba Codex.** Ejecutar sigue siendo de Codex por defecto
   (`G7`); Grok entra cuando Codex está bloqueado.
2. **Pedirle un veredicto que depende de una medida a un juez sin shell.** La
   supone. Postura C, o mide tú.
3. **Prompt abierto** («¿qué opinas del plan?»). Devuelve un ensayo. Especifica
   dimensiones, formato y qué es un hallazgo válido.
4. **Lanzarlo sin `--tools`** en un rol de juicio. Aquí eso es escritura y shell
   auto-aprobadas, sin prompt que lo pare, y **no hace falta ningún flag de
   permiso para que lo sea** (A/B 2026-08-22).
5. **Pedirle un documento con el allowlist de solo-lectura.** Cambia de
   postura, no de prompt.
6. **`--permission-mode acceptEdits` para que escriba.** Pisa el
   `--always-approve` del comando —gana incluso pasando ambos— y la corrida
   muere en `cancelled` sin escribir nada, sin error y sin warning. Medido 3/3.
7. **`-p` inline (o `--prompt-json` inline) desde PowerShell 5.1.** Se trocea
   por comillas/saltos y aborta con exit 2; y el inline con imágenes revienta
   el techo argv de 32.767. `--prompt-file`, y JSON inline solo desde Bash.
8. **Consumir `.text` cuando hay `--json-schema`.** El artefacto validado está
   en `.structuredOutput`.
9. **Citar `AGENTS-R24` a secas** y suponer que sabe qué es. No carga
   `~/.codex/AGENTS.md`; resúmela, o pásala por `--rules`.
10. **Pasarle la salida de otra lane en una lane que debía ser ciega.**
    Contamina justo lo que la lane aportaba. En reconciliación el consolidado
    SÍ se comparte — eso es el encargo, no contaminación.
11. **Usar un `-r` o un `--fork-session` como revisor «independiente».** Ambos
    arrastran la conversación entera de la sesión que implementó.
12. **Aceptar sus `path:line` sin abrir el archivo** (`G2`), o aceptar sus
    medidas de Postura C sin re-verificar las que deciden un veredicto.
13. **Tratar `total_cost_usd` como factura.** Es cuota, no cargo.
14. **Cerrar la sesión sin volcar el arbitraje al scorecard.** La precisión de
    la corrida se pierde de forma definitiva.
15. **Abrir sesión nueva para seguir con el mismo material.** Se re-paga el
    arranque entero (~21k frescos) por algo que en `-r` cuesta el 12%. Distinto
    de la lane ciega, donde la sesión nueva es el encargo.
16. **Pasar la ruta de una skill o un HANDOFF grande a secas** en la carga
    inicial. `dayz-vehicles/SKILL.md` son ~48k tokens por lectura; cita la
    sección y el rango que aplican al ángulo.

## References

- **`references/write-to-disk-handoff.md`** — posturas A/B (y la comparativa
  completa con Consejo y C): por qué `acceptEdits` mata la corrida, la
  disciplina de `%TEMP%` + hashes, la tarjeta de entorno del host, el contrato
  de recibo y el bucle de visto bueno. **Obligatoria antes de la primera
  invocación de escritura.**
- `references/prompt-patterns.md` — esqueletos de prompt de los cinco roles,
  la ronda de conciliación post-ciega, el método adversarial (preguntas
  temporal y género-AC), el follow-up de calibración y el schema de hallazgos
  estructurados.
- `references/grok-cli-gotchas.md` — mecánica del CLI 1.0.4: tabla autoritativa
  de tool IDs, flags, permisos, memoria, sesiones, subcomandos (`export`,
  `update`, `sessions`), contradicciones entre las propias docs de Grok, y qué
  está verificado vs solo documentado.
- `references/track-record.md` — los estrenos reales de cada rol con sus
  lecciones operativas. El valor de esta skill está ahí: léelo antes de un
  encargo del rol que vas a usar.

## Estado de esta skill

v3, 2026-08-15. Revisada contra `grok 1.0.4 (d846eb93d9)` en el host WILLY con
tres sondas de re-verificación (juez read-only + deny MCP · Postura C con
shell y `--json-schema` · imagen por bloques ACP), las tres `end_turn` con
baseline intacto. Incorpora el rediseño de roles del 2026-08-12 (`workflow.md`
§Reparto: autoría de lane + reconciliación en paralelo) y el backlog SP-199 /
204 / 209 / 211 / 223 / 224 / 225 / 227 / 229 / 230 / 232 / 239 / 240 / 244
del ledger. Los cinco roles tienen estreno real documentado en
`track-record.md`. Sin re-medir tras el bump: si `--rules` sobrevive a un
`-r`, si los subagentes heredan los `--deny` del padre, y si `--effort high`
mejora un R21. Cuando una corrida falle de forma interesante, la lección va a
`track-record.md` — como en `codex-handoff-template`, cuyo valor está en sus
~15 casos reales.

v4, 2026-08-15 (tarde). Añade §Presupuesto de invocación con la auditoría de
gasto sobre 314 sesiones reales: el reparto medido del fresco, `-r` como default
del follow-up, la carga inicial citada por sección y el hallazgo de que el
fan-out grande estaba bien diseñado (Jaccard 0,11) pero releía el sustrato.
Sigue **sin medir** si los subagentes heredan los `--deny` del padre — lo que sí
quedó verificado es que no existe herencia de contexto padre→hijo, sólo
`resume_from` entre hermanos.

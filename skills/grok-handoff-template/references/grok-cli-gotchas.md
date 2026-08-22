# Grok Build CLI — mecánica y gotchas

Base 2026-08-03; revisado 2026-08-07 contra 1.0.0; revisado 2026-08-15 contra
**`grok 1.0.4 (d846eb93d9) [stable]`** en el sobremesa (hostname `WILLY`) con
tres sondas de ejecución. El portátil (`DESKTOP-L49Q27C`) corría 1.0.3 la
semana del 08-08→08-15; cuando una evidencia diga «DESKTOP-L49Q27C», es de esa
máquina.

Cada afirmación lleva su procedencia:

- **[V]** verificado ejecutándolo en un host propio (con fecha y máquina).
- **[D]** documentado en las docs locales, con cita; no ejecutado.
- **[?]** autoinforme del modelo o inferencia; trátalo como hipótesis.

Las docs viven en el disco y son la fuente autoritativa:
`~\.grok\README.md` (~2.680 líneas) y `~\.grok\docs\user-guide\*.md` (24 guías
por tema). Se escribieron para 1.0.0; el delta 1.0.0→1.0.4 no trae changelog
local — **si una corrida se comporta raro tras un bump, sospecha del bump antes
que del prompt**, y `grok update --check --json` te dice en qué versión estás.

## Instalación y modelos en este host

- **[V 2026-08-15, WILLY]** Binario: `$env:USERPROFILE\.grok\bin\grok.exe`,
  versión `1.0.4 (d846eb93d9) [stable]` (actualizado desde 1.0.0 con
  `grok update`; el updater es interno, canal `stable` semanal, `--alpha`
  existe). **La ruta se escribe con `$env:USERPROFILE`**, no hardcodeada — la
  forma `C:\Users\<user>\...` rompió en el portátil.
- **[V 2026-08-15, WILLY]** `grok models`: **`grok-4.6` (default)** y
  `grok-4.5`. El JSON de una corrida reporta `modelUsage.grok-4.6-build`.
  (El «solo lista grok-4.5» de la revisión del 08-07 era cierto en 1.0.0 y ya
  no lo es — otra razón para pinnear `-m`.)
- **[V]** El instalador añadió `~\.grok\bin` al PATH de usuario en el registro.
  Una shell abierta **antes** de instalar no lo ve: usa la ruta absoluta.
- **[V]** Autenticado por suscripción de `grok.com`. No hay `XAI_API_KEY` ni
  `GROK_API_KEY` en el entorno; `total_cost_usd` es contabilidad
  equivalente-API + cuota, no cargo.
- **[D]** grok-4.6: 500k de contexto y efforts `low/medium/high/xhigh` según
  `models_cache.json` (leído en el portátil, 2026-08-12).

## Lanzamiento — desde qué shell y cómo leer la salida

Consolidado de 4 incidentes medidos (2026-08-11 → 08-13) + sondas del 08-15:

| Forma | PowerShell 5.1 | Bash (Git Bash) |
|---|---|---|
| `--prompt-file` + args ASCII | **[V]** funciona (R22, GunRacks C5…) | **[V 08-15]** funciona (3 sondas) |
| `-p "<prompt>"` inline multilínea o con `"` | **ROTO** — PS re-tokeniza y el CLI aborta `error: unexpected argument`, exit 2, sin consumir cuota | funciona con `PROMPT="$(cat f.txt)"`, pero usa `--prompt-file` y te olvidas |
| `--json-schema '<json>'` / `--prompt-json '<json>'` inline | **ROTO** — se come las comillas (`Invalid JSON: key must be a string`) | **[V 08-15]** funciona |

- **[V]** `-p` y `--prompt-file` son **excluyentes**: combinarlos falla con
  exit 2 y 0 bytes.
- **[V DESKTOP-L49Q27C 2026-08-12]** Techo argv de Windows: **32.767 chars**.
  Medido: 29.826 pasan al parser, 150.026 mueren con `Argument list too long`.
  Por eso las imágenes en base64 NUNCA van inline (§Multimodal).
- **Lectura de la salida**: redirige stdout a fichero desde Bash (bytes
  limpios) o, en PowerShell, lee con
  `[IO.File]::ReadAllText($path, [Text.Encoding]::UTF8)`. `Get-Content -Raw`
  en PS 5.1 decodifica en la codepage ANSI y mojibakea los acentos del
  informe.
- **[V]** Prompts: mantén lo load-bearing en ASCII cuando puedas; en
  `--prompt-file` los acentos van bien (UTF-8 sin BOM).

## Multimodal headless (imágenes)

- **[V ambos hosts]** No hay `--image`. Bloques de contenido **ACP** dentro de
  un `--prompt-file` cuyo contenido es JSON:
  `[{"type":"text","text":"..."},{"type":"image","data":"<base64>","mimeType":"image/png"}]`.
  El formato Anthropic (`source:{...}`) se rechaza con
  ``Invalid ACP content blocks: missing field `data` ``.
- **[V WILLY 2026-08-15, 1.0.4]** Sonda: PNG sintética de 1.296 bytes por
  `--prompt-file` + `--json-schema` + `--tools ""` + effort `low` → leyó
  número y color exactos en 1 turno, $0.009.
- **[V]** `--tools ""` (cadena vacía) es válido: corrida sin herramientas, lo
  que exigen los contratos «cero tool calls».
- Adaptador de referencia: `AI/10_Projects/AssetLab/tools/grok_arm.py`.

## Esfuerzo de razonamiento

- **[D]** `--reasoning-effort` (alias `--effort`): `none, minimal, low,
  medium, high, xhigh, max`. Funciona en TUI y headless, a diferencia de
  `--tools` (`README.md:640`).
- **[V DESKTOP-L49Q27C 2026-08-12, 5 corridas]** En `high`/`xhigh`, grok-4.6
  ante un contrato de un solo disparo con `--json-schema` devuelve una
  **declaración de intenciones** en el campo del schema en vez del artefacto —
  con y sin tools, con `--max-turns` 1/4/8 y con `--no-plan`. Con
  `--max-turns 1` muere además en `cancelled`. Parece pereza y es
  decapitación. **One-shot → `low` siempre.**
- **[V WILLY 2026-08-15]** A `low`, multi-turno con tools + `--json-schema`
  produce bien (§Sondas). Si `high` mejora un R21 multi-turno: **sin medir**.

## Qué comparte con Claude Code (verificado con `grok inspect`)

Grok descubre la configuración de Claude Code sin ningún setup. En el
directorio del proyecto DayZ carga:

- **[V]** `~\.claude\Claude.md` (global) + `Claude.md`/`Agents.md` del
  proyecto.
- **[V]** Las skills de `~/.claude/skills/` (más las suyas bundled y las de
  `~/.grok/skills/`).
- **[V]** Los plugins con sus skills, agentes y hooks; los MCP servers de
  `~/.claude.json` (`answeroverflow`, `dayz-mcp`); 11 hooks.
  **[?]** Qué hooks disparan de verdad en una corrida headless no está
  auditado — los hooks corren fuera del toolset del modelo (`22:123`), así que
  el allowlist no los limita.
- **[D]** En cada hook define `CLAUDE_PROJECT_DIR` y `CLAUDE_PLUGIN_ROOT`/
  `CLAUDE_PLUGIN_DATA` como alias de sus `GROK_*` (`10-hooks.md:320`,
  `09-plugins.md:374`).

Lo que **NO** carga:

- **[V]** `~/.codex/AGENTS.md`. Las reglas `AGENTS-R*` le son invisibles:
  resúmelas o pásalas por `--rules`.
- **[V]** 36 de las 94 reglas de permiso de Claude Code se descartan por
  prefijo desconocido (todas las `PowerShell(...)` y `Skill(...)`). Grok
  reconoce `Bash`, `Read`, `Edit`/`Write`, `Grep`/`Glob`, `MCPTool`,
  `WebFetch`, `WebSearch`. Tus permisos **no se traducen enteros**.

`grok inspect` (o `--json`) es la forma de comprobar todo esto en vivo. Es
gratis: no llama al modelo.

## Tool IDs — la tabla que manda, y la trampa de los nombres

**[D]** La lista autoritativa de IDs válidos para `--tools` /
`--disallowed-tools` está en `README.md:599-609`:

| Display | ID para `--tools` |
|---|---|
| bash | `run_terminal_cmd` |
| grep | `grep` |
| read_file | `read_file` |
| search_replace | `search_replace` |
| list_dir | `list_dir` |
| web_search | `web_search` |
| web_fetch | `web_fetch` |
| todo_write | `todo_write` |
| task (subagentes) | `task` |

**La trampa**: otras cuatro páginas de las docs llaman al shell
`run_terminal_command` (`01-getting-started.md:141`, `08-skills.md:218`,
`10-hooks.md:162`, `20-background-tasks.md:9`). Para `--tools` el bueno es
`run_terminal_cmd` — **[V WILLY 2026-08-15]** confirmado por ejecución en la
sonda de postura C: con `--tools "read_file,grep,list_dir,run_terminal_cmd"`
ejecutó shell y midió un SHA-256 exacto. Lo mismo con el subagente:
`spawn_subagent` en `01-getting-started.md:144`, pero `task` en la tabla.

**[D]** `search_replace` es también el tool de **creación**: se llama con
`old_string` vacío (`~\.grok\bundled\skills\create-skill\SKILL.md:53`).
`Write` / `Edit` / `MultiEdit` **no son tool IDs** — son clases de regla de
permiso (`10-hooks.md:164`).

**[D]** Los dos flags componen: «when both flags are present,
`--disallowed-tools` wins» / «runs after `--tools`» (`14-headless-mode.md:82`,
`README.md:638`). Ojo al par confuso del `--help`: `--deny` es una REGLA de
permiso (alias compat `--disallowedTools`), y `--disallowed-tools` QUITA tools
built-in — nombres casi iguales, mecanismos distintos.

**[D]** Web: `web_search`/`web_fetch` existen como tools y `--disable-web-search`
las apaga en bloque. Un allowlist que no las incluye ya las excluye.

## Permisos y contención

### ★ Aquí no pregunta nada, y el flag de permiso no es lo que lo decide

**[V 2026-08-22]** `~\.grok\config.toml:12-17` NO trae always-approve: su
bloque `[ui]` termina en `permission_mode = "auto"` (leído ese día). Y bajo
`auto` **la escritura ocurre igual sin pasar ningún flag de permiso**: A/B
medido el 2026-08-22 con el mismo prompt y el mismo allowlist incluyendo
`search_replace` — sin flag, `end_turn` en 2 turnos y fichero en disco; con
`--always-approve`, idéntico. Así que el flag **no es load-bearing para
escribir**; se pasa para fijar el modo con independencia del config del host, y
porque la doc lo prescribe para scripts y CI (`22-permissions-and-safety.md:20-21`).
**[D]** «CLI overrides config for that process» (`22:59-63`).

Consecuencias, que son el hecho más importante de esta página:

1. **Ninguna invocación pregunta nada**, TUI o headless, con flag o sin él. El
   modo de permiso **no es el cortafuegos**.
2. **En los roles de juicio, lo único que separa a Grok del árbol es `--tools`**
   (más `--deny "MCPTool"`).
3. **Pasar `--permission-mode acceptEdits` DEGRADA la corrida** y la mata en
   headless. Detalle y medición en `write-to-disk-handoff.md` §Lo primero.

**[D]** Bajo always-approve siguen aplicando: reglas `deny`, hooks, y las `ask`
que matcheen segmentos de un comando de shell (`22:136`).

- **[V WILLY 2026-08-15, 1.0.4]** `--tools "read_file,grep,list_dir"` deja a
  Grok sin escritura. Sonda: leyó el valor pedido, informó de que no tiene
  herramienta de escritura y el archivo pedido **no existe en disco**.
- **[V WILLY 2026-08-15, 1.0.4]** El allowlist **NO elimina**
  `search_tool`/`use_tool` (pasarela MCP), y `--deny "MCPTool"` bloquea la
  invocación pero no el descubrimiento:

  | Operación | Herramienta | Resultado |
  |---|---|---|
  | Descubrir | `search_tool` | Ejecutó; encontró `dayz-mcp bridge_status` y su esquema |
  | Invocar | `use_tool` | `Denied by permission policy: deny rule on mcp` |

  **[D]** Y está escrito: «the final toolset retains requested tools **plus
  always-on MCP meta-tools**» (`14-headless-mode.md:82`; también `14:34`).
- **[D]** Las reglas MCP usan `MCPTool(server__tool)`. El estilo de Claude
  Code `mcp__server__tool` **nunca matchea** (`22:350-352`).

### La trampa de los `allow` de bash

**[D]** `22-permissions-and-safety.md:328`: los `deny` y `ask` se comprueban
contra **cada segmento** de un comando encadenado (`&&`, `||`, `;`, `|`), pero
los `allow` se comprueban **solo contra la cadena completa**. Consecuencia:
`--allow 'Bash(git *)'` autoaprueba `git status && rm -rf /`. Construye la
seguridad con `deny`, nunca con un allow amplio.

**[D]** Los checks por segmento pelan wrappers (`timeout`, `nice`, `env`) pero
**no** `sudo`, `xargs` ni `nohup` — hay que denegarlos explícitamente.

**[D]** Comandos siempre-preguntan aunque haya grant: `rm`, `chmod`, `chown`,
`chgrp`, `chattr`, `kill`, `killall`, `pkill`, `git push` (`22:334-336`).

### El sandbox no confina en Windows

**[D]** `README.md:2269-2272`: enforcement con Landlock (Linux ≥5.13) y
Seatbelt (macOS); si no puede aplicarse, «registra un warning y continúa sin
enforcement». Windows no aparece. **[?]** En este host `--sandbox` probablemente
no confina nada; comprobable en `~/.grok/sandbox-events.jsonl`
(`18-sandbox.md:235`). **La contención real aquí es el allowlist.**

## Modos de permiso

**[D]** `--permission-mode` acepta `default`, `acceptEdits`, `auto`, `dontAsk`,
`bypassPermissions`, `plan` (`22:33-40`).

> **Para headless con escritura hay dos valores que funcionan: `--always-approve`
> explícito, o no pasar el flag** y dejar el `auto` del config — los dos escriben
> (A/B 2026-08-22). Lo que NO vale es cualquier otro valor: **degrada** el modo, y
> `acceptEdits` en concreto mata la corrida, incluso pasando además
> `--always-approve`. El modo es uno, no capas que se suman. Pásalo explícito de
> todos modos: cuesta cero y te independiza del config del host.

- `bypassPermissions` es el nombre interno de always-approve (`--always-approve`,
  alias `--yolo`).
- **[D]** Gotcha de plan mode: los subagentes **no** heredan el gate de edición
  del padre (`19-plan-mode.md:127-137`) — un subagente con escritura puede
  editar mientras el padre sigue en plan mode.

## Flags y subcomandos útiles (inventario 1.0.4)

**[V 2026-08-15]** contra `grok --help` del host; uso verificado solo donde se
indica.

| Flag | Para qué sirve aquí |
|---|---|
| `--rules <TEXT>` (alias `--append-system-prompt`) | Anexa al system prompt en `<human_rules>` (`12-project-rules.md:163-171`) — el sitio para el resumen de `AGENTS-R`. Si sobrevive a un `-r`: no documentado. |
| `--system-prompt-override` | Reemplaza el system prompt entero **y descarta `--rules`**. Casi nunca es lo que quieres. |
| `--json-schema '<schema>'` | Salida estructurada validada; implica `--output-format json`. **[V 08-15]** multi-turno con tools a effort low → `.structuredOutput` validado. |
| `--prompt-json '<json>'` | Content blocks inline — inviable para imágenes por el techo argv; usa `--prompt-file` con JSON. |
| `-m grok-4.6` / `grok-4.5` | Pin de modelo. **[V 08-15]** default = 4.6. |
| `--reasoning-effort` | §Esfuerzo. One-shot → `low`. |
| `--no-memory` | Apaga memoria cross-session con prioridad absoluta (`13-memory.md:57`). En lanes ciegas, siempre. |
| `--disallowed-tools "task"` / `--no-subagents` | Corta el spawn de subagentes (`14-headless-mode.md:668`). Con allowlist ya están fuera. |
| `--agent <NAME>` / `--agents <JSON>` | Agente/subagentes custom por definición inline o fichero. **[?]** Sin explorar. |
| `--disable-web-search` | Apaga `web_search`+`web_fetch` en bloque. |
| `--fork-session` (+ `-s <uuid>`) | Forkea historia a un ID nuevo al reanudar. NO da independencia (§Sesiones). |
| `--verbatim` | Manda el prompt exactamente como está, sin envoltorio. |
| `-w, --worktree` | Git worktree para la sesión — **headless (`-p`) NO lo crea** (dixit `--help`); existe `grok worktree` para gestionarlos. **[?]** Sin explorar. |
| `--restore-code` | Al reanudar, restaura el snapshot del repo de la sesión original. **[?]** Sin explorar. |

Subcomandos: `inspect` (gratis, qué config ve) · `models` · `update`
(`--check --json` no instala) · **`export <SESSION_ID> [OUTPUT]`** — transcript
a Markdown, la vía para archivar una corrida de council en `reviews/`
(**[V 08-15]** sintaxis por `--help`; sin correr aún sobre una sesión real) ·
`sessions` (list/search/restore) · `trace` · `dashboard` · `doctor` · `mcp` ·
`plugin` · `agent` (headless sin TUI) · `wrap` · `completions` · `setup`.

## Memoria cross-session — apagada, pero compruébalo

**[D]** «Memory is experimental and disabled by default» (`13-memory.md:16`).
Se activa con `--experimental-memory`, `GROK_MEMORY=1` o `[memory] enabled`;
`--no-memory` gana a todo (`13-memory.md:43-57`).

**[V 2026-08-07]** En este host está apagada: sin `GROK_MEMORY`, sin sección
`[memory]`, sin `~/.grok/memory/`. Importa porque **rompería las lanes
ciegas**: con memoria activa, una sesión nueva puede reutilizar contexto de
sesiones previas del mismo workspace (`README.md:2160`, `13-memory.md:84-90`).
`--no-memory` en toda corrida de lane cuesta cero y es a prueba de futuro.

## Salida headless

**[V 1.0.4]** `--output-format json` devuelve un objeto único con: `text`,
`stopReason`, `sessionId`, `requestId`, `thought`, `usage{...}`, `num_turns`,
`total_cost_usd`, **`total_cost_usd_ticks`** (nuevo en 1.0.4), `modelUsage`, y
**`structuredOutput`** cuando hay `--json-schema`.

- **Con `--json-schema`, consume `structuredOutput`, no `text`** — el text
  puede traer JSON espurio de turnos intermedios (visto en sonda: un
  «PENDING» antes del definitivo).
- **[D]** Valores de `stopReason`: `end_turn`, `max_tokens`,
  `max_turn_requests`, `refusal`, `cancelled` (`14:240-243`). Solo `end_turn`
  es entrega válida. En la práctica, `cancelled` + `text` cortísimo = flag de
  permiso mal puesto.
- **[D]** Otros formatos: `plain` (default), `streaming-json` (NDJSON ACP),
  `streaming-messages-json` (formato Anthropic Messages;
  `--include-partial-messages` añade deltas).

## Sesiones — el resume es la palanca de coste

- **[D]** `-s <uuid>` nombra sesión **nueva**; `-r <id-o-título>` resume;
  `-c` continúa la más reciente del directorio.
- **[V]** `-r <sessionId>` reutiliza contexto cacheado: un follow-up de R22
  costó **107k tokens / $0.051 / 1 turno** frente a 523k/$0.431/9 de la
  revisión (12%). Guarda siempre el `sessionId`; el JSON devuelve el mismo id,
  así que se puede encadenar.
- **[D]** Persisten en `~/.grok/sessions/<cwd-codificado>/<session-id>/`, como
  JSON/JSONL inspeccionables.
- **[D]** **Un fork NO da independencia.** `--fork-session` «starts from a copy
  of the conversation» (`17-sessions.md:113-114, 210`) y deja
  `parent_session_id`. Para una lane de revisión ciega, sesión nueva que lea
  solo los paths en disco.

## Costes medidos

Era grok-4.5 (**[V]** 2026-08-03/07): sonda 30k/$0.064 · opinión 97k/$0.137 ·
R22 real 523k/$0.431/5,1 min/9 turnos · follow-up `-r` 107k/$0.051.

Era grok-4.6 (**[V]** 2026-08-15, effort low, 1.0.4):

| Sonda | Tokens | Coste | Turnos |
|---|---|---|---|
| Juez read-only, 3 tareas + MCP denegado | 55.502 | $0.0101 | 3 |
| Postura C: SHA por shell + `--json-schema` | 36.306 | $0.0080 | 2 |
| Imagen ACP + schema, `--tools ""` | 26.533 | $0.0090 | 1 |

~6× más barato por corrida equivalente que la tabla 4.5. El `--cwd` sigue
siendo la palanca: apuntar a un proyecto con `CLAUDE.md` grande se paga en
cada sesión nueva (no en los `-r`, que leen de caché).

## OneDrive: no reproduce el problema de Codex

**[V]** Codex se cuelga en la hidratación de OneDrive y obliga a copiar a un
scratchpad. **Grok no**: con `--cwd` sobre el árbol OneDrive leyó un `.md` de
271 líneas sin colgarse (33 s, 3 llamadas). No hace falta pre-copiar para que
LEA. La contrapartida es de coste (carga el `CLAUDE.md` del proyecto), y para
ESCRIBIR sigue mandando la disciplina `%TEMP%` de `write-to-disk-handoff.md`.

## Otras cosas que existen (punteros, no resumen)

- **Workflows en Rhai** — orquestación multi-agente determinista propia
  (`agent()`, `parallel()`, `phase()`, journal y resume), pareja conceptual del
  Workflow tool de Claude Code. Manual:
  `~\.grok\bundled\skills\create-workflow\SKILL.md`. Sin caso de uso en este
  pipeline mientras las lanes cross-provider las orqueste Claude.
- **Retomar sesiones ajenas** — `resume-claude`, `resume-codex`,
  `resume-cursor` leen el transcript nativo de esos CLIs y construyen un
  handoff (lógica en `~\.grok\bundled\skills\shared\resume-session\CORE.md`,
  con salvaguardas anti-inyección). Útil si una sesión de Codex muere.
- **`grok doctor`** — diagnóstico de terminal sin arrancar el agente.
- **`grok mcp` / `grok plugin`** — gestión de MCP y plugins, marketplace
  `xAI Official` ya configurado.

## Contradicciones dentro de las propias docs

Detectadas 2026-08-07 (docs de 1.0.0; siguen en disco). Cuando dos páginas
discrepan, la que habla específicamente del flag manda sobre la tabla
descriptiva.

| Tema | Una dice | La otra dice |
|---|---|---|
| ID del shell | `run_terminal_cmd` (`README.md:601`, `14:53`) — **[V]** el bueno | `run_terminal_command` (4 páginas) |
| ID del subagente | `task` (`README.md:609`) | `spawn_subagent` (`01:144`) |
| ID de grep | `grep` (`README.md:602`) | `grep_search` (`README.md:2351`) |
| Qué guarda la memoria | «does **not** record tool usage, file paths…» (`13:110`) | sí guarda ambos (`README.md:2125-2127`) |
| Subcomandos de `grok memory` | solo `clear` (`13:327`) | `edit`, `stats` (`README.md:2171-2177`) |
| `acceptEdits`/`dontAsk` | «no grok equivalent» en hooks (`10:284`) | existen como modes (`22:36-39`) |

## Sin verificar — pendiente

- Si `--rules`, `--permission-mode` y `--deny` sobreviven a un `-r` o hay que
  repetirlos en cada invocación. Y si `--rules` tiene límite de tamaño.
- Si los subagentes heredan los `--deny` del padre (solo está documentada la
  herencia del permission mode y del modelo). Mientras tanto: apágalos.
- Si `--effort high|xhigh` mejora de forma medible un R21 multi-turno, o solo
  sube el coste.
- `grok export` sobre una sesión real (sintaxis confirmada; ejecución no).
- `--agent`/`--agents`, `--worktree`+`--restore-code`: capacidades del harness
  sin explorar.
- Si `--sandbox` emite el warning «sin enforcement» en Windows
  (`~/.grok/sandbox-events.jsonl`).
- Qué hooks de los 11 cargados disparan de verdad en headless.
- Qué campos del frontmatter de skills honra (`README.md:1624-1629` solo
  documenta `name` y `description`).

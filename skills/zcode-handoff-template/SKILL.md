---
name: zcode-handoff-template
description: >
  Delegar trabajo a GLM-5.3 por la app ZCode (Z.ai) y recoger el resultado por
  disco, no por portapapeles. Hermana de codex-handoff-template,
  grok-handoff-template y qwen-handoff-template: GLM es la lane de VOLUMEN (1M
  de contexto, cuota de plan) para barridos de repo entero, research amplio,
  auditorias de corpus y segunda voz en revision. Clave medida: el agente de
  ZCode conecta los mismos servidores MCP del usuario, con filesystem sobre el
  vault y sobre DayZ Projects, asi que el brief va por rutas absolutas y el
  entregable lo escribe GLM en un archivo que Claude luego lee y verifica.
  Cubre que via funciona hoy, el protocolo en cinco pasos, la plantilla del
  brief, los caveats que GLM no hereda, las colisiones y el receptor. Dispara con "pasaselo a zcode", "que lo haga
  GLM", "delegar en GLM-5.3", "usa el plan de Z.ai", "handoff a zcode", "prompt
  para GLM", "que lo vea GLM", "tercera opinion con GLM"; o "send to zcode",
  "zcode handoff", "ask GLM". Invocala ANTES de escribir cualquier brief para
  GLM.
---

# ZCode / GLM-5.3 Handoff Template

Builder + receptor para encargos Claude→GLM-5.3 vía ZCode. Verificado contra
ZCode 3.8.1 / agente 0.16.3 el 2026-08-22 en este host.

## Estado de cada vía (no re-pagues este diagnóstico)

| superficie | estado | uso |
|---|---|---|
| **App ZCode** (GUI) | **operativa** — sesión OAuth viva, refresca su token en cada arranque | la vía real de trabajo |
| **CLI headless** (`zcode -p`) | **muerta con este plan** | solo diagnóstico offline (`skills list`, `plugins list`, `doctor`) |

Por qué el CLI no vale, medido y cerrado el 2026-08-22:

- `POST https://zcode.z.ai/api/v1/oauth/cli/init` → **404, body vacío**. El
  device-flow del CLI no está desplegado; por eso `zcode login` muere con
  `OAuth response is not valid JSON` (parsea cero bytes).
- Credencial del app copiada al CLI → **400 `captcha verify failed` (3007)**.
- Las cinco combinaciones credencial×endpoint del keystore → **401**, y
  `api.z.ai` concreta `token expired or incorrect`: la key que guarda el app
  **caduca**, el GUI la renueva sola y cualquier copia estática nace muerta.
- El propio `/login` del CLI solo ofrece *"Open browser login and create a
  Coding Plan API key"* o *"Paste a Coding Plan API key manually"*: **no existe
  modo sin key**, y este plan (ZCode Start Plan, OAuth desde el app) no emite
  ninguna.

Si algún día aparece una GLM Coding Plan API key, la vía CLI se abre entera y
está documentada en `references/cli-forensics.md`. Hasta entonces, el transporte
es otro.

## El hecho que hace esto útil: el transporte es el disco

El agente que corre dentro de la app **conecta los mismos servidores MCP del
usuario**. Medido en `~/.zcode/cli/log/zcode-2026-08-22.jsonl`
(`mcp.startup.completed` → `serverCount: 6, connected: 5, failed: 1,
toolCount: 70`):

| servidor | tools | qué le da a GLM |
|---|---|---|
| `ai-memory` | 14 | lectura/escritura sobre `%USERPROFILE%\ObsidianVault\AI` |
| `dayz-mods` | 14 | lectura/escritura sobre `OneDrive\Documentos\DayZ Projects` |
| `dayz-mcp` | 54 | el bridge de DayZ **entero** (ver §Colisiones) |
| `spline` | 35 | 3D/2D |
| `answeroverflow` | 4 | búsqueda en Discord archivado |
| `node_repl` | 3 | REPL |
| `fal-ai` | — | **falla al conectar** |

Consecuencia operativa, y es la regla central de esta skill: **no le pegues
contenido de archivos.** Dale rutas absolutas y deja que los lea. Y no le pidas
la respuesta por chat: **pídele que escriba el entregable en una ruta que tú
fijas**, y luego léela tú. El portapapeles transporta el encargo, no el
resultado.

Eso convierte un handoff manual en algo casi tan cerrado como el CLI: el único
paso humano es un ctrl+V.

## Routing gate — ¿esto va a GLM-5.3?

El reparto no cambia porque haya un modelo nuevo. `G7` sigue mandando la
EJECUCIÓN a Codex y el juicio a Grok. GLM entra por un hueco concreto: **1M de
contexto y cuota de plan que no se paga por llamada**.

1. **¿Es ejecución de código del pipeline?** → Codex (`G7` / `AGENTS-R20`). GLM
   entra si Codex y Grok están bloqueados.
2. **¿El trabajo cabe mal en 200k y bien en 1M?** — barrer un repo entero, leer
   40 notas antes de opinar, auditar un corpus, reconstruir el historial de una
   decisión — → **GLM**. Es su ventaja estructural, no una preferencia.
3. **¿Hace falta una segunda voz de familia distinta** para `AGENTS-R21`? → GLM
   sirve y es barato contra el plan. **Nunca GLM revisando a GLM**: implementador
   y revisor de la misma familia comparten puntos ciegos, y la convergencia vale
   menos.
4. **¿Lo decide una MEDIDA** (un hash, correr un gate, contar líneas)? GLM tiene
   shell y filesystem en la app, así que puede medir — pero solo si se lo pides
   explícitamente. Si no, lo supone.
5. **¿Trivial?** → hazlo tú.

Lo que GLM-5.3 **no** es: el nuevo ejecutor por defecto. Los públicos lo sitúan
por detrás de Fable 5 y GPT-5.6 Sol en Terminal-Bench 3.0 (28,3) y DeepSWE v1.1
(66,9). Su argumento es contexto y coste, no ganar la tarea difícil.

## Protocolo de handoff — cinco pasos

1. **Claude redacta el brief** con la plantilla de abajo. Rutas absolutas, nunca
   contenido pegado.
2. **El usuario abre el workspace correcto** en ZCode y pega el brief. El
   workspace importa: define el `workspaceKey` y qué scope de config aplica.
3. **GLM lee** por `ai-memory` / `dayz-mods` y trabaja.
4. **GLM escribe el entregable** en la ruta pactada — por defecto
   `AI/30_Sessions/YYYY-MM-DD-glm-<tema>.md` o un scratch acordado.
5. **Claude lee esa ruta**, verifica contra las fuentes y arbitra. Un hallazgo
   se vuelca al `council-scorecard.md` **en el mismo paso en que se arbitra**,
   no al cerrar.

El paso 4 es el que se olvida y el que hace que todo esto valga: sin ruta de
entrega pactada, el resultado se queda en una ventana de chat y muere ahí.

## Plantilla del brief

Bloque copiable. Mismo esqueleto que `codex-handoff-template` — un delegado
nuevo no justifica un formato nuevo.

```
## ROL
Eres [revisor ciego | barredor de repo | investigador]. [Puedes escribir
archivos SOLO en <ruta>] | [No escribas nada hasta el entregable final].

## FUENTES (léelas tú, no te las pego)
- %USERPROFILE%\ObsidianVault\AI\10_Projects\<PROY>\project-brief.md
- %USERPROFILE%\OneDrive\Documentos\DayZ Projects\<repo>\...
Tienes los servidores MCP ai-memory (vault) y dayz-mods (DayZ Projects).

## ENVIRONMENT CAVEATS (no heredas mi CLAUDE.md)
- Cite-then-verify: ninguna firma de API, path o constante sin grep + cita
  path:line. Sin verificar → etiqueta [ASSUMPTION] explícita.
- Escrituras en rutas OneDrive: inserción textual con Python. Nunca reformatear
  el JSON/YAML entero, nunca BOM.
- Severidad: crash / exception / corruption / degradation / cosmetic no son
  sinónimos. Usa el término exacto.
- NO toques dayz-mcp (world_*, session_*, vehicle_*) salvo que este brief te lo
  pida por su nombre.

## SCOPE DIFERENCIAL   (solo si comparas dos artefactos)
Restringido a: <A> vs <B>
Fijado como igual y VERIFICADO: [dim1 path:line], [dim2 path:line]
UNCHECKED: [dim3], [dim4] — si la causa vive aquí, este análisis no la ve.

## ENTREGABLE
Escribe el resultado en: <ruta absoluta>
Formato: bloques A) hallazgos  B) evidencia con path:line  C) lo que NO
verificaste  D) preguntas abiertas.

## STOP-RULES
- Si <hipótesis H> queda refutada por <observación>, aborta esa rama y dilo.
- Si una fuente no existe en la ruta dada, para y repórtalo. No la inventes.
```

## Lo que GLM no hereda

**Hereda**: los servidores MCP de arriba, las **60 skills** de
`~/.agents/skills/` (las mismas que Codex, `first match wins`, usuario sobre
workspace) y sus plugins oficiales (`browser-use`, `document-skills`,
`skill-creator`, `zcode-guide`).

**No hereda tu `CLAUDE.md`.** ZCode lee `~/.zcode/AGENTS.md` (usuario) y
`AGENTS.md` del repo, en ese orden. Ese archivo **no existe** en esta caja: GLM
arranca sin ninguna de tus reglas globales. Por eso el bloque de caveats va en
cada brief — mismo principio que `LL-184` para subagentes que no heredan
contexto.

Si vas a delegar en GLM más de una vez, la inversión correcta es **crear
`~/.zcode/AGENTS.md`** con ese bloque y dejar de repetirlo. Es la diferencia
entre pagar los caveats una vez o cada vez.

## Colisiones peligrosas (verificadas)

- **`dayz-mcp` se autoconecta con sus 54 tools** al abrir sesión en ZCode. Dos
  agentes conduciendo el mismo bridge es exactamente lo que el protocolo de
  sesión compartida existe para evitar. Antes de un handoff que toque DayZ:
  decide quién tiene el lease y **dilo en el brief**. Si el lease es tuyo, la
  línea "NO toques dayz-mcp" de la plantilla no es decorativa.
- **Los MCP se autoconectan en todos los scopes**, incluido el del workspace.
  Abrir en ZCode un repo ajeno conecta los servidores que ese repo declare, sin
  preguntar. Abre solo workspaces tuyos.
- **`fal-ai` falla** al conectar en el arranque. No cuentes con él desde GLM.
- **`~/.zcode/cli/config.json` guarda tus 7 servidores MCP.** Cualquier
  experimento sobre ese archivo toca la config viva del app: copia de seguridad
  antes, y compara por DATOS al revertir.

## Receptor

- El entregable se lee de la **ruta pactada**, no del chat. Si GLM no la
  escribió, el handoff falló: no lo remates tú copiando de la ventana.
- Verifica **las citas `path:line` antes de aceptarlas**. Un delegado sin tu
  CLAUDE.md confabula rutas con la misma soltura que cualquier otro; la
  convergencia con tu propia opinión no es verificación.
- Distingue *fallo de transporte* de *respuesta pobre* antes de juzgar la
  calidad del modelo.
- Cada hallazgo arbitrado → `council-scorecard.md`, una fila, en el momento.

## Anti-patrones

- **Pegarle el contenido de archivos que puede leer solo.** Quema contexto,
  introduce copias desincronizadas y desperdicia el 1M que justifica esta lane.
- **Pedir la respuesta por chat.** Sin ruta de entrega, el trabajo muere en una
  ventana.
- **Copiar credenciales del app a cualquier otro cliente.** Medido: caducan.
- **GLM revisando lo que escribió GLM.**
- **Pedirle juicio sobre algo que se decide midiendo** sin darle la medida ni
  pedirle explícitamente que la tome.
- **Delegar sin decir quién tiene el lease de `dayz-mcp`.**
- **Tratar el `--help` del CLI como documentación fiable** — ver
  `references/cli-forensics.md`: anuncia tres flags que el parser rechaza.

## Coste

La cuota es del plan y se consume por tokens; el argumento entero de esta lane
es que el contexto grande sale barato. Aun así, abrir sesión carga skills, MCP
y AGENTS.md antes de leer tu brief: para una pregunta de una línea esa carga es
la mayor parte del gasto. Preguntas cortas van a `glm-5-turbo` o no van.

## Estado de esta skill

**Verificado el 2026-08-22**: rutas del app y del bundle, esquema de config,
ids y límites de modelo (`glm-5.3`: 1.000.000 contexto / 128.000 salida,
esfuerzo `low|high|max`, default `max`), descubrimiento de las 60 skills,
conexión real de los 6 servidores MCP con sus conteos de tools, y las cinco
combinaciones de credencial del CLI.

**Sin verificar todavía**: la calidad de GLM-5.3 en tareas de este vault
(ninguna corrida real aún), la latencia, y si respeta el bloque de caveats sin
un `AGENTS.md` permanente. La primera delegación real debe medir esas tres
cosas y actualizar esta sección.

Detalle forense del CLI —endpoints, orden de resolución de credenciales, tabla
de flags que mienten, esquema exacto de `model.main`— en
`references/cli-forensics.md`. Léelo solo si aparece una API key o si algo no
cuadra con lo de arriba.

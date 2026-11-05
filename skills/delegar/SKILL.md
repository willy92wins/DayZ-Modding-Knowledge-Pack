---
name: delegar
description: Decide si delegar, elige modelo y ruta, y construye o recibe el handoff. Usa la matriz medida para Qwen/Ollama, OpenCode Zen y otras claves gratis (ejecución gratis primero), NVIDIA NIM/Nemotron/DeepSeek, OpenRouter/Venice, GX10 (LAN; congelado, solo lectura), Codex/OpenAI, Claude/Anthropic, Grok/xAI, Cursor, agy (Gemini/Argon) y Muse por CLI nativo (suscripción priorizada) y GLM/ZCode; luego carga solo la referencia de prime-agent, codex exec, claude -p, grok CLI, cursor-agent, agy (Antigravity), opencode/oc_run.py, Cline CLI, ZCode app o junior_agent.py y el rol de ejecucion, revision, research, plan o arbitraje. Dispara con «delega», «quien lo hace», «que modelo/ruta uso», «pasaselo a…», «handoff», «vigía acoplado», «watcher», «prime-agent», nombres de esas lanes/modelos/rutas (incluidos «gx10», «agy», «antigravity», «gemini», «gemini-3.8-flash», «cline», «muse», «wonder», «council»), o al recibir su salida. Invocala antes de cualquier brief o comando de delegacion.
---

# Delegar

Esta es la única skill cargable del catálogo. Decide el reparto y construye o recibe el
handoff. No contiene los manuales completos de cada CLI, el catálogo remoto ni el historial
de mediciones. Esos datos se cargan bajo demanda desde `references/`.

Invócala **antes** de escribir un brief o un comando. Si el usuario ya fijó modelo o ruta,
no omitas el gate: conserva su elección, comprueba la celda y aplica las restricciones de
riesgo y verificación.

## Ningún número de versión de este árbol es estado vivo (convención, 2026-09-26)

Un manual no puede saber por qué versión va el host hoy, así que aquí **la versión viva se
sonda, no se lee**. Cada ruta abre con un bloque `## Estado del host` que trae el comando de
sonda, lo que devolvió y **la fecha** en que se corrió. Ese bloque es lo único de la ruta que
habla del presente; si su fecha te parece vieja, vuelve a correr la sonda antes de decidir.

Por eso los ejemplos de invocación van **sin pin de modelo** allí donde el CLI tiene un
default usable: copiar un bloque usa entonces el default vivo y nunca selecciona por detrás de
él. Donde el CLI **no** tiene default usable —`agy` no declara ninguno, y el de `cline` está
roto— el ejemplo sí lleva el flag, y el bloque de estado dice de qué salida se copia el id.

Lo que **sí** conserva su versión, y no se toca:

- **cada medición** — un número pertenece a la versión con la que se midió, así que
  `references/evidence/` entero, las filas de la matriz y los sellos `[V fecha]` quedan como
  están; despincharlos convertiría la evidencia en folclore;
- **las fichas de `references/models/` y los catálogos de proveedor** — ahí la versión es el
  tema del documento, no una elección de redacción;
- **las decisiones fechadas del dueño** y las palabras gatillo del `description`.

Al editar: si escribes un slug concreto fuera de esos cuatro sitios, o lo fechas, o lo
cambias por la familia y un puntero a la sonda. Un slug suelto en prosa se lee como estado
vivo el día que caduca, y nadie avisa.

## Council habitual (decisión de Guillermo, 2026-10-26)

**5 miembros permanentes: Claude, ChatGPT, Grok, Muse y Argon** (`gemini-4-argon` por `agy`). **Mayoría = 3/5.** En los asientos Claude y ChatGPT, según la tarea:
**ChatGPT Astra + Claude Fable**, o **ChatGPT Sol + Claude Opus** (Sol vivo = `gpt-6.1-sol`).
Rutas: Claude CLI nativo · ChatGPT `codex exec`/sesión actual · Grok `grok-cli` · Muse [CLI nativo](references/routes/muse-cli.md) (`muse exec --model muse-wonder-1.0`) ·
Argon `agy -p -m gemini-4-argon-<esfuerzo>`. Detalle en [la composición base de routing.md](references/routing.md#council-base-del-usuario-2026-10-24).
Sondar identidad y esfuerzo de cada celda el día de la corrida. La composición explícita del encargo prevalece; este reparto no dispara un council para cada tarea.
**3/5 decide, salvo** una cita re-verificada contraria o un `DISENSO-FUERTE` (verbatim al usuario).
*(Sustituye a «Council habitual» = Muse, Grok, Claude y Codex, y a «las familias adicionales se suman».)*

## Resultado que debe producir

Una decisión completa tiene siete campos:

- **decisión**: hacerlo aquí o delegarlo;
- **rol**: ejecución, revisión, research, plan, arbitraje o continuidad;
- **modelo × ruta**: una celda concreta, no solo una marca o un proveedor;
- **estado**: disponibilidad medida y su fecha, o una incertidumbre declarada;
- **fronteras**: fuentes, workspace, permisos, riesgo y coste;
- **entregable**: artefacto y criterio observable de término;
- **revisión**: receptor y familia independiente que lo comprobará.

No lances nada mientras falte uno de esos campos.

## Gate breve

1. **¿Es trivial y reversible?** Hazlo en la sesión actual si es un cambio obvio y pequeño.
2. **¿Exige una herramienta viva de esta sesión?** Conserva aquí la interacción con el
   usuario, la orquestación de subagentes, un MCP interactivo exclusivo y la coordinación de
   recursos compartidos. Delega las partes separables.
3. **¿Es irreversible o de alto riesgo?** No delegues credenciales, destrucción, formatos
   persistentes ni una migración sin vuelta atrás. Puedes delegar una sonda o una parte segura.
4. **¿Es EJECUCIÓN o JUICIO?** La ejecución produce un artefacto. El juicio revisa,
   investiga, compara, reconcilia o arbitra. Esta separación decide la lane.
5. **Aplica la regla de reparto.** Carga `references/routing.md`. La ejecución baja por la
   escalera gratis primero. El juicio no baja por ella.
6. **Consulta la matriz.** Abre `references/reachability.md` y elige una celda
   `model_id × route_id` compatible con las restricciones del usuario.
7. **Carga solo lo necesario.** Una ruta, como máximo una ficha de proveedor, la ficha de
   modelo si aporta algo propio y un patrón de rol.
8. **Escribe el brief, ejecuta, supervisa y recibe.** Verifica identidad, término y
   artefactos. Encarga la revisión a otra familia. Corrida larga o bucle →
   §Supervisión de la corrida en marcha. **Al recibir, cuenta SIEMPRE los ficheros
   modificados FUERA del workspace**, no solo el `git status` del worktree: el `--cwd` no
   contiene (LL-451), y el entorno del host puede darle al worker una instrucción que su
   brief no le dio —el 2026-09-18 un stop hook le pidió a un worker de grok-cli promover
   una lección, editar una skill gobernada y commitear, con el brief prohibiéndole git
   (`fb-20260918-015158-51f6`; esa vez no lo hizo)—. Era regla solo de `cursor --mode ask`
   y ahora es general: el revisor mira dentro del workspace, así que fuera no mira nadie.

⚠ **¿El worker necesita una segunda opinión a mitad de trabajo?** No hace falta
devolverte el turno: el worker local puede lanzar un hijo `rlm()` en OTRA familia y seguir.
**Medido 2026-08-30: la admisión y la ejecución del hijo son verdes; el RETORNO tiene una carrera
de cierre sin resolver, y el catálogo de bocas de hijo se cae en silencio.** Lee `references/routes/prime-agent-bitacora.md`
§Subagentes RLM ANTES de diseñarlo, o el hijo entrega y su respuesta se pierde. No cambia la regla
de reparto: el revisor sigue siendo de otra familia por construcción.

Si ninguna celda tiene estado apto, detente. Explica qué está roto, no probado o no
disponible. No sustituyas modelo, proveedor o ruta en silencio.

**Antes de declarar una FAMILIA fuera** ("sin celda viva"), aplica la regla de `references/families.md`: sondea
el mismo dia, con un turno PONG, cada celda local, gratis y de suscripcion de su escalera. Un 402, "insufficient
funds" o una cuota agotada en una ruta de PAGO no demuestran nada sobre las gratis (lo que fallo con GLM, Kimi y
Qwen el 2026-09-28).


⚠ **Corrida larga o desatendida (overnight, varias horas, encargo de varios ítems):** el
gate de arriba NO basta y saltárselo costó una noche entera el 2026-08-28 (2 ítems de 5).
Antes de lanzarla, aplica el **Checklist antes de comprometer una noche** de
`references/routes/prime-agent.md` §Checklist antes de comprometer una noche: cronometrar acciones/hora de la boca, probar
que la suite colecciona EN el workspace elegido, techos inalcanzables (el juez es el gate
en disco, no el contador de tokens), reintento que REANUDA con `-r`, y vigía que cuente
artefactos en disco. Y cuando la corrida muera: mirar el árbol y relanzar, en ese orden.

## Experto Enfusion (Grok Bot) — cuándo acudir (Guillermo 2026-11-05)

- Toda PR o DIFF que toque **Enforce Script** (.c) o el **PBO**: revisión del Experto Enfusion (fbde1d58) **antes** del sello del Auditor. Sin esa revisión no se pide sello.
- **Hooks antihack**: los diseña Experto Enfusion **con** Responsable Proyectos. No se inventan en el hop de implementación.
- No sustituye al Auditor (LIMPIO/SOUND) ni a la revisión de otra familia (Sol/Codex). Orden: implementación → (revisión otra familia si aplica) → Experto Enfusion si Enforce/PBO → Auditor → merge. PBO: el dueño decide tras prueba en juego.
- Autoridad de Enfusion = Pack + skills vivas Claude + LLs del vault; no el extracto stale.

## Pase de oficio (Guillermo 2026-11-05)

Si recibes una tarea que según `registro-agentes.md` es de otro bot:
1. **No la ejecutas tú.** Se la pasas con `SendToAgent` al dueño. En el traspaso va el **texto literal** de Guillermo (para que cuente como su petición), más el contexto mínimo.
2. En el mismo turno le dices a Guillermo en **una frase** a quién la has pasado.
3. Prohibido: (a) hacer el oficio de otro; (b) devolverle «esto no es mío, pídeselo a X».
4. **Excepción:** bots que solo aceptan GO escrito en su propio chat (hoy: **Experto MCP**). Das a Guillermo el **texto exacto del GO** listo para pegar en ese chat; no finges el GO.
5. El dueño confirma recepción y cierra con un **POST** al que se la pasó.

## Clasificar el rol antes de escoger aparato

> **(rev. 2026-10-26, Guillermo) Normas de puerta vigentes.** Sustituyen a la nota rev. 2026-09-25 y a las frases antiguas que decían «la puerta por defecto a los
> modelos Grok es Cursor (rev. 2026-09-06)» y «`grok-cli` queda reservado para X pública», que ya no están en este fichero:
> - **Grok: primero `grok-cli`** (`grok.exe`; modelo por defecto `grok-4.7`). Cursor es contingencia y **no gasta Ultra en modelos no-Grok**. Antes de lanzar, sonda de
>   saldo de un turno: el `402 Payment Required: Grok Build usage balance exhausted` ya cortó antes del primer turno el 30-31 de agosto y el 2026-09-06 (detalle en
>   `references/reachability.md`). Medido el 2026-09-25: sonda de 34 s y 0,03 $, y dos rondas de implementación reales en postura B con `-r` (5,7 y 8,5 min; 0,14 y 0,51 $);
>   el 2026-10-26 `grok 1.0.70` contestó en 9,8 s.
> - **Codex nativo** por su cupo abundante. **Sol vivo = `gpt-6.1-sol`** (el slug lo manda el catálogo del CLI ese día).
> - Cursor Ultra sirve además Kimi K3, GLM y Composer (contingencia). `agy` (suscripción de Google; ver §Suscripción priorizada): la puerta es `agy`, **nunca el `gemini` de npm**
>   (`IneligibleTierError / UNSUPPORTED_CLIENT` con login válido).
> - **Cursor y `agy` nunca para modelos Anthropic ni OpenAI/ChatGPT** (regla de Guillermo, 2026-09-02): esos van por sus suscripciones (`claude -p`/subagente y `codex exec`).

**EJECUCIÓN** crea algo verificable en disco (fichero, test, JSON válido). Va por la escalera de abajo, **gratis primero** cuando el done-when es verificable.
**JUICIO** incluye revisión adversarial, investigación, autoría o reconciliación de planes y arbitraje. Es trabajo normal de Codex nativo; Anthropic es la otra familia para
revisión cruzada. **Nunca baja por la escalera gratis**, no se convierte en Qwen → Zen → Grok, y un modelo gratis no ocupa un puesto bloqueante sin repuesto de su familia.
Una excepción para Grok debe estar autorizada por la regla única de reparto.

Todo lo delegado se revisa. El revisor empieza en una sesión nueva y pertenece a **otra familia**. Cambiar de `codex exec` a `prime-agent` sin cambiar el modelo no aporta
independencia.

## Ejecución gratis (medida el 2026-10-26; **la lista rota: sondar antes de lanzar, no copiar**)

**Cuándo:** el done-when es mecánico y verificable, y el encargo no es JUICIO ni toca vault/credenciales (eso va a local).
**Cómo:** un turno de sonda → si contesta con contenido real, lanzar. Un 200 vacío, un 429 servido como contenido, un `-free` que cobra, una clave caducada o un timeout cuentan
como fallo y pasan a la **siguiente boca de la lista escrita antes**. El dispatcher es un script, no un modelo. Evidencia y comandos: [`references/evidence/probes-2026-10-26.md`](references/evidence/probes-2026-10-26.md).

| Pri | Puerta / modelo | Sirve para | Lanzamiento | Aviso |
|---|---|---|---|---|
| 1 | OpenCode Zen (`auth.json` renovado el 26-oct): `deepseek-v4.1-flash-free`, `glm-5.3-flash-free`, `mimo-v2.6-flash-free`, `big-pickle`, `beam-free`, `flint-40b-free`, `nemotron-3.5-lightning-free`, `nemotron-3.5-super-vl-free` | reescritura, tickets cortos, triage | `opencode run -m opencode/<id> "<brief>" < NUL` (verificado 13:35: glm-5.3-flash-free 6,8 s, deepseek-v4.1-flash-free 4,5 s, big-pickle 4,9 s) | **`auth.json` manda sobre `OPENCODE_API_KEY`**; si caduca (`API key has expired`) rompe también los `-free` → `opencode providers login` (lo hace Guillermo). **Solo vía `opencode run`**: HTTP crudo y `prime-agent --provider zen` dan `429 FreeUsageLimitError` (Retry-After ~11,6 h). `nemotron-3-ultra-free` colgó; `jev-1.13-free` UnknownError. Límite diario del CLI: no medido |
| 3 | tokenharbor `deepseek-v4.1-flash:free`; aihubmix `coding-glm-5.3-free` | lotes mecánicos | `prime-agent -p --provider <p> --model <id>` | 5 s entre reintentos |
| 4 | NVIDIA / OpenRouter `nemotron-3-ultra-550b-a55b(:free)` | corpus sweep, segunda familia | `prime-agent -p --provider nvidia --model nvidia/nemotron-3-ultra-550b-a55b` | otros modelos NIM cuelgan o dan 404 |
| 5 | Google API `gemini-3.5-flash` / `gemini-3.6-flash` | revisor cruzado de otra familia, triage | API OpenAI-compat, `GEMINI_API_KEY` | `gemini-3.8-flash` dio 503 en la propuesta del 26-oct |
| 6 | Ollama `qwen3.8:98k` | extracción, todo lo sensible | `prime-agent -p --provider ollama --model qwen3.8:98k` (`think:false`) | 60 s en frío; lease de la GPU |
| 8 | llm7 `codestral-latest`; bynara `nemotron-3.5-lightning-free` | snippets, relleno | API directa | el resto de sus modelos da 402; llm7 cachea |
| — | GX10 | solo lo que ya sirva su `/v1/models`; **FREEZE** | lectura | ver §GX10 |
| — | freebuff Desktop | manual-only (sin headless) | — | no es lane |
| — | Cline | bloqueada si pide reautenticación (login de Guillermo) | — | su lista `free` rota cada semana |

(La numeración salta del 1 al 3 y del 6 al 8 a propósito: conserva la de la propuesta del 2026-10-26; los puestos 2 y 7 no se asignaron.)

**Por tipo de trabajo:**
- *Triage:* `nemotron-3.5-lightning-free` o `mimo-v2.6-flash-free` → tokenharbor → `gemini-3.5-flash`.
- *Reescritura:* `glm-5.3-flash-free` → `deepseek-v4.1-flash-free` → *(suscripción)* `agy gemini-3.8-flash-low` / `gpt-oss-120b-medium`.
- *Corpus sweep:* `nemotron-3-ultra` (NVIDIA/OpenRouter) → `qwen3.8:98k` → `gemini-3.5-flash`.
- *Tickets cortos:* `big-pickle`, `beam-free` → aihubmix `coding-glm-5.3-free` → *(suscripción)* `agy gemini-4-argon-low`.
- ***Cyber:* `agy gemini-4-argon` (preferente, suscripción)** → Codex nativo → Claude.
- *JUICIO:* ninguno de los anteriores.

**Trampas del gratis:** una clave de pago caducada puede romper la lane gratis del mismo proveedor; sondea con un entorno limpio antes de culpar al modelo. Las lecciones de
calibración, fiabilidad por proveedor y bajas de agosto siguen en §Historial del escuadrón gratis, más abajo.

## Suscripción priorizada (NO gratis; se usa antes que el resto de suscripciones)

Orden (Guillermo, 2026-10-26, rev. 17:06 Madrid): **`agy`/Argon → Muse (Wonder; Spark: no medido) → `grok-cli` → Codex → Claude**; Cursor solo como contingencia de Grok. **Muse Wonder, Argon y Grok van ANTES que ChatGPT/Anthropic** en el trabajo general. **El JUICIO no cambia** (Codex nativo, Opus o Fable; §Clasificar el rol). Entra después de lo gratis (cuando el done-when es verificable) y antes de gastar Codex/Claude/Cursor en ejecución.
Muse Wonder: segundo modelo del Intelligence Index según Guillermo (dato suyo, no verificado aquí; sospecha que está «benchmaxed», pero «muy buena tool»). Orden entre `agy`/Argon y Muse Wonder dentro del grupo, y su calidad relativa: **no medido**.

| Pri | Puerta / modelo | Sirve para | Lanzamiento | Aviso |
|---|---|---|---|---|
| S1 | `agy` (suscripción Google): **`gemini-4-argon`** (low/medium/high), `gemini-3.8-flash-low`, `gpt-oss-120b-medium` | tickets con artefacto, reescritura. **Argon = preferente para cyber** | `agy -p -m <id> --add-dir <ws> "<brief>"` | `SUCCESS` no prueba trabajo: mirar `denied_actions` y disco; reconfirmar flags con `--help`; `claude-*` vetados |
| S2 | Muse (Wonder): `muse exec --model muse-wonder-1.0 --trust-workspace --prompt-file p.txt` | segunda voz / council / lane | idem | `-m` no vale; lane, no JUICIO; no sustituir por Spark/Glimmer sin avisar |
| S3 | Grok (`grok-cli`, `grok.exe`) | ejecución y council; puerta primaria de Grok | — | sonda de saldo de un turno antes (un `402` ya cortó antes del primer turno); consumo no llevado en el tablero (abajo) |
| S4 | Codex nativo (`codex exec -m <slug>`) | ejecución dura, todo el JUICIO | — | cupo abundante |
| S5 | Claude (CLI nativo) | JUICIO cruzado, implementación | — | no sondado el 26-oct (no medido) |
| — | Cursor (contingencia de Grok) | solo si `grok-cli` no sirve | — | no gastar Ultra/on-demand en OpenAI/Anthropic ni en modelos no-Grok |

**Tablero de cupos (pendiente, Guillermo 2026-10-26):** hay que llevar el consumo de **Argon (`agy`)** y de **Muse Wonder** junto al de Grok, Codex y Claude. **Fuente de datos: no identificada** (no medido); no inventar cifras ni fuente hasta tenerla.

## Escalera de EJECUCIÓN (orden de coste)

1. **Filtro previo:** vault / credenciales / código sin publicar → local (`ollama`; GX10 solo si ya sirve el modelo, sin cargar nada).
2. **Gratis** (§Ejecución gratis, en ese orden) cuando el done-when es verificable.
3. **Suscripción priorizada:** `agy`/Argon (`gemini-4-argon` para cyber) → Muse Wonder → `grok-cli`, antes que Codex/Claude (el JUICIO no cambia).
4. **Codex nativo por cuota** (abundante): ejecución que no cabe gratis y todo el JUICIO. `luna`/`astra` para lo ligero, `sol` para lo duro; el slug se lee del catálogo del CLI ese día.
5. **Claude**; **Cursor** solo como contingencia de Grok si nada anterior sirve (no gastar Cursor Ultra en modelos no-Grok).
6. **Puesto bloqueante** (gate que acepta, árbitro, revisor obligatorio): nunca gratis sin repuesto de la misma familia.

## Historial del escuadrón gratis: sillas medidas el 2026-08-28 (histórico, NO estado vivo)

> **rev. 2026-10-26.** Esta sección conserva la batería del 2026-08-27 y sus lecciones de calibración. Los modelos titulares, el GX10 como implementador y los
> proveedores de la tabla son de agosto-septiembre y **no** son el reparto vigente: el reparto vigente es §Ejecución gratis, §Suscripción priorizada y §Escalera de arriba.

19 proveedores, **163 modelos cableados**. Este reparto ya **no** es solo procedencia y
latencia: el 2026-08-27 se corrio una bateria de revision real -- 4 items x 8 celdas x 2
muestras, 64 corridas por el arnes -- con un item **sin defecto** como control negativo.

**El filtro que va ANTES de la escalera** (vigente; ahora es el peldaño 1 de §Escalera). Lo que toca el vault, credenciales o codigo sin publicar va a un local
—`ollama`, o `gx10` solo si ya sirve el modelo (FREEZE, decision de Guillermo 2026-10-26)— y no sale de casa. `empero` viaja por **HTTP en claro** y el resto son
terceros de los que solo se sabe que responden.

**La regla nueva, y la que mas ordena: separa puestos que BLOQUEAN de los que no.**
Un puesto no bloqueante -- generar un candidato, ampliar cobertura, una segunda opinion
que si no llega no pasa nada -- tolera una lane gratis: si cae, se pierde una llamada. Un
puesto bloqueante -- el gate que acepta, el arbitro, el revisor obligatorio de `G7` -- no.
Medido el 2026-08-27 en el unico momento del dia en que una lane gratis bloqueaba algo:
`gemini-3.7-flash` dio `503 high demand` y `kimi-k3` dio `429`, **las dos tras 3
reintentos**, y solo entregaron los modelos de repuesto. Saltarse un gate «porque el
gratis no contestaba» es como un control se convierte en adorno.

| silla | titular | evidencia |
|---|---|---|
| **Revisor / juicio gratis** | `bai/glm-5.3-flash` | **8/8 veredicto y 8/8 diagnostico, 0 falsos positivos, 0 mudas.** Unico gratis que aprueba los dos controles. **No** su gemelo de `empero`: mismo modelo, otro servidor, 2 mudas |
| **Segunda voz** | `bai/deepseek-v4-flash` | 8/8 veredicto, 7/8 diagnostico, 0 mudas. Misma casa, asi que **no** sirve como familia distinta |
| **Instrumento de medida** | `cerebras/gpt-oss-120b` | **1.667 tok/s** medidos (Artificial Analysis: 1.724), TTFT 0,28 s. A esa velocidad `n=5` por celda cuesta lo que `n=1`: es lo que desbloquea medir bien, mas que un puesto de trabajo |
| **Lote mecanico** (N llamadas cortas) | `bai/deepseek-v4-flash` y hermanos | 2,2-4,3 s, 4 de 4 |
| **Implementador** con fuentes en disco | *(histórico 2026-09; hoy el GX10 está en FREEZE y `/v1/models` manda)* `gx10` con el modelo de su lane (titular desde 2026-09-15): desde el 2026-09-26 `GLM-5.3-Flash-EXL3`, y con la lane FN `Qwen/Qwen3.8-Flash-Next`; respaldo `ollama/qwen3.8:65k` | Los dos no salen de casa. GLM: una PR real (`bearer_proxy.py`) aceptada en la ronda 1, 43 min, 129 líneas, coste 0 ([ficha](references/providers/gx10.md) §GLM). GX10: puerta real por el arnes el 2026-09-15 (fichero exacto en disco, `stopReason: stop`, 9,6 s), fuera de esta bateria y sin comparativa de calidad; compartido con Hermes. Ollama: **Pendiente**: en la bateria las 8 corridas dieron timeout a ~273 s, problema de lane, no de capacidad; WORKS de nuevo el 31-ago con la causa sin diagnosticar |
| **Revisor cruzado que ACREDITA familia** | `google/gemini-3.6-flash` o `nvidia/nemotron-3-ultra-550b-a55b` | Los dos entregaron arbitrajes largos y utiles. Sus hermanos «primera opcion» (`gemini-3.7-flash`, `kimi-k3`) fallaron: **lleva siempre modelo de repuesto en la misma familia** |

> (added 2026-09-13, SP-392) **`bai/glm-5.3-flash` ya no es gratis**: `400 credit insufficient balance` en la sonda. La silla de revisor gratis queda vacante hasta medir otro; GLM por Cursor (`glm-5.2-max`) funciona, pero es de pago.


**Bajas desde el 26-ago, para no recomendarlas por inercia:** `aihubmix` entero -- sus dos
modelos devuelven `Sorry, to prevent abuse of free resource` **como contenido con HTTP
200**, y esta descableado. `empero` en mantenimiento largo (24 sondas / 18 min, todas 503).
`z-ai/glm-5.2:free` saturado en origen.

**Que acredita una familia.** Solo `ollama` y `gx10` (pesos en tus maquinas), `nvidia` NIM y
`google` acreditan por credencial. En un rele, el nombre del modelo lo pone el rele: `llm7` anuncia
`claude-opus-5` y `gpt-5.6-sol` y **no acredita nada**.

**Como calibrar una silla, con lo que costo aprenderlo.** Un control de UNA muestra decide
*alcanzable / no alcanzable*, y nada mas:

- Tres modelos dieron **respuestas distintas a la misma pregunta determinista** segun la
  corrida (8 vs 11, 11 vs 10, 11 vs 12).
- El control de contar letras **no mide el tokenizador**: mide cuanta inferencia gasto esa
  llamada. `cohere/north-mini-code:free`, mismo modelo y mismo tokenizador, dijo 8 por API
  y 11 por el arnes gastando 131 tokens. Comparar lanes por acierto **sin igualar el
  presupuesto de razonamiento** es medir la configuracion de servicio, no el modelo.
- **`llm7` cachea**: 5 de 8 pares de muestras salieron byte a byte identicos. Su varianza
  no existe; sus numeros son `n~1`.
- Y un control negativo que todos aprueban -- como el de esta bateria -- descarta el modo
  de fallo «revisor que siempre encuentra algo» pero **no discrimina**. El siguiente
  necesita una trampa plausible dentro.

Detalle por lane, **trece** modos de fallo y el discriminador de credenciales:
`references/providers/relays-openai-compat.md`. Matriz por pareja: `references/reachability.md`.

**Fiabilidad por proveedor, corte 2026-08-31 (council LFHeli).** Lo que sostienen las medidas:
las bocas con credencial propia y plataforma estable — `nvidia` NIM, `opencode` Zen, `google`,
`cerebras`, `ollama` local — degradan MENOS que los relés third-party (`aihubmix` y `empero`
cayeron en 24-48 h; `llm7` cachea y raciona). PERO plataforma fiable ≠ modelo disponible ese día:
en la corrida de hoy `moonshotai/kimi-k3` (NIM) murió 4/4 por 429 en multi-turno,
`gemini-3.7-flash` dio 429 a mitad de respuesta, `z-ai/glm-5.3` (OpenRouter) quemó el tope entero
en reasoning con `content` vacío al primer intento (fix: tope ≥3x el contrato), y ZCode estaba KO
— mientras `codex exec` y `ollama` local por API directa entregaron a la primera. Dirección
acordada con el usuario: **ranking continuo por proveedor** con dos ejes por corrida — TRANSPORTE
(¿entregó?: los `STATUS` por lane del manifiesto de cada council) y CALIDAD (las filas del
`council-scorecard`). No promover «más fiable» a doctrina sin esas filas acumuladas.

## Elegir la celda modelo × ruta

Lee una fila de `references/reachability.md`; no deduzcas disponibilidad de un catálogo.
Comprueba:

1. identificador exacto del modelo;
2. identificador de la ruta y subruta;
3. proveedor, cuenta y host a los que se aplica;
4. estado `WORKS`, `BROKEN`, `UNTESTED` o `UNAVAILABLE`;
5. fecha y evidencia enlazada;
6. coste, privacidad, ventana, herramientas y restricciones del usuario.

Un resultado pertenece al par. Que `prime-agent` funcione con Ollama no prueba Zen. Que un
modelo aparezca en NVIDIA no prueba que esté servido. Que una app funcione no revive su CLI.
Si el estado ha caducado para una decisión costosa, ejecuta primero una sonda pequeña y
registra el resultado en la futura fase de contenido; no alteres la doctrina desde este
esqueleto.

## Mapa de referencias a cargar

### Decisión

- `references/routing.md`: regla única de reparto, riesgo, familia revisora y elección de
  puerta. Cárgala cuando haya que decidir quién o por dónde.
- `references/reachability.md`: autoridad modelo × ruta. Cárgala siempre que la celda no
  venga fijada y validada.
- `references/families.md`: indice por familia, orden de sondeo (local, gratis, suscripcion, pago) y regla
  para declarar una familia fuera. Cargala al elegir las lanes de un council o antes de escribir que una
  familia no tiene via viva.

### Ruta elegida

Carga **un** manual operativo:

- `references/routes/prime-agent.md` para el arnés común;
- `references/routes/codex-exec.md` para el CLI nativo de Codex;
- `references/routes/claude-p.md` para la puerta nativa de Anthropic (`claude -p`): el
  aislamiento del worker es **`--safe-mode`**, nunca `CLAUDE_CONFIG_DIR` a un directorio
  vacío, que relocaliza `~/.claude` con el login y mata la corrida en `Not logged in`.
  Peaje medido (2026-09-05, CLI 2.1.260): 66 skills propias y 7 servidores MCP a **cero**,
  sin `CLAUDE.md`, y aun así autentica por suscripción. Su celda sigue en
  `references/reachability.md` y la medición vieja en
  `references/evidence/prime-agent-puertas-2026-08-24.md`;
- `references/routes/grok-cli.md` para Grok, **puerta por defecto a los modelos Grok** (norma
  2026-09-25; `grok 1.0.70` sondada el 2026-10-26, que no es estado vivo) y, además, las herramientas de X. Si falla, **mira
  el saldo antes que el prompt**: un `402` que corta antes del primer turno y es idéntico en
  4.6 y 4.5 es cuenta, no receta (pasó el 30-31 de agosto y de nuevo el 2026-09-06);
- `references/routes/cursor-cli.md` para Cursor (`cursor-agent`), **contingencia para los
  modelos Grok** (tarifa plana Ultra; la puerta por defecto es `grok-cli` desde el 2026-09-25) y la única vía medida de Kimi K3 sin
  el racionamiento de NIM. **No es un proveedor de `prime-agent` y no puede serlo**: ver esa
  ruta §Qué es esta ruta, y qué NO es. ⚠ **`--mode ask` NO es «solo lectura»: frena la escritura
   dentro del `--workspace`, no en el resto del disco** (medido 2026-09-08: dejó 5 ficheros en
   `%TEMP%`). Una lane que deba ser estéril lo declara además en el brief, y al recibir se cuentan
   también los ficheros de fuera del workspace; **y es GENERADOR sin verificador (LL-451)**:
   sus llamadas de shell mueren en los pre-hooks PowerShell del host aunque lleve `--force`,
   asi que antes de delegarle un encargo con gate, sonda de un turno
   `python -c "print('ok')"`, y si bloquea se presupuesta la ronda 2 del receptor
   (ante un `402` de Grok, mirar el saldo antes que el prompt);
- `references/routes/agy-cli.md` para Antigravity (`agy`; sondada el 2026-10-26 con 1.4.7, versión que no es estado vivo), la lane de la suscripción de
  Google (**suscripción, no gratis; la primera de la priorizada**): sirve `gemini-4-argon` (preferente para cyber), `gemini-3.8-flash-low` y `gpt-oss-120b-medium`; la lista viva sale de `agy models`. Tres cosas antes de lanzar: `status:"SUCCESS"` con `rc=0` **no** prueba trabajo hecho
  —una herramienta denegada devuelve éxito con `response:""` y cero ficheros, se mira
  `denied_actions` y el disco—; **sin `--add-dir` el artefacto cae en
  `~/.gemini/antigravity-cli/scratch\`**, no en tu cwd; y el id lleva el esfuerzo dentro
  (`gemini-3.8-flash-low`, no `gemini-3.8-flash`). El `gemini` de npm es puerta MUERTA para
  esta cuenta —`IneligibleTierError / UNSUPPORTED_CLIENT` con el login válido: **LL-487**, una
  puerta puede morir por TIER, y eso no se arregla con flags ni esperando a que baje la cuota—;
- `references/routes/muse-cli.md` para Muse por su CLI nativo: miembro del council,
  con identidad y término verificados en los eventos JSONL; no inferir su login del de OpenCode/Cline.
  **Suscripción, no gratis (2026-10-26)**: `muse exec --model muse-wonder-1.0 --trust-workspace --prompt-file p.txt` (`-m` no vale);
- `references/routes/opencode-run.md` para OpenCode y la subruta `oc_run.py`. **rev. 2026-10-26:** `opencode run` funciona con el `auth.json` renovado; HTTP crudo y `prime-agent --provider zen` dan 429 (ver §Ejecución gratis);
- `references/routes/cline-cli.md` para Cline CLI — **lane gratis viva desde el 2026-09-21** para
  `z-ai/glm-5.3-flash` y `poolside/laguna-s-2.1:free` (artefacto exacto en 15-16 s, coste 0), que
  son justo las dos que por Zen están rotas. **El 2026-09-26 la lista gratis rotó**: esas dos ya
  no figuran (re-sonda y `totalCost` antes de contar con ellas) y entra `stealth/pixel-canary`,
  con artefacto exacto, latencia muy variable en su estreno (2-3 min por iteración entre las
  10:39 y las 10:53 UTC; 20 s una respuesta por el shim de Hermes a las 11:35) y familia
  desconocida: puesto no bloqueante y nunca revisor. La lista viva sale de `recommended-models`
  ([proveedor](references/providers/cline.md)). Sus celdas **locales** (ollama, openai-compatible)
  siguen BROKEN, y el modelo por defecto también: pasa `-m` explicito. **rev. 2026-10-26: pide reautenticación (login de Guillermo); bloqueada hasta entonces.**
  Dos trampas que no comparte con nadie: el **provider por defecto es estado en disco**
  (`lastUsedProvider` en `~/.cline/data/settings/providers.json` — pasa `-P` siempre, o la
  corrida hereda el de la anterior y se cuelga muda) y deja un **daemon hub** vivo tras la
  corrida (`cline hub stop`);
- `references/routes/zcode-app.md` para la app y el transporte por disco — **BROKEN 2026-08-31**
  (app KO, reporte del usuario; única vía GLM-5.3 no-flash viva hoy: `z-ai/glm-5.3` × API directa
  OpenRouter, de pago — ver `reachability.md`);
- `references/routes/qwen-junior-agent.md` cuando el wrapper cambie el control del bucle.

No copies mecánica de una ruta a otra. En especial, las mitigaciones de
`junior_agent.py` no aplican a Qwen por `prime-agent`, y el estado de Zen por `oc_run.py` no
se hereda a Zen por el arnés.

### Proveedor o cuenta

Carga una ficha de `references/providers/` solo si la celda necesita autenticación, cuota,
rate limits, plan o una política transversal. Los dueños son `openai.md`, `google.md`,
`nvidia.md`, `opencode-zen.md`, `ollama.md`, `gx10.md`, `xai.md`, `cursor.md`, `zai.md`, `openrouter.md`,
`venice.md`, `cline.md` y `relays-openai-compat.md` —la ficha común de los relés OpenAI-compatibles,
con sus **trece** modos de fallo—. No hay ficha de Anthropic.

Una excepción del proveedor no se copia en cada modelo ni en cada ruta. El manual enlaza a
su dueño.

### Modelo o familia

Carga una ficha de `references/models/` si hacen falta capacidades o fallos que sobreviven al
cambio de puerta: `qwen3.8.md`, `nvidia-catalog.md`, `zen-catalog.md`,
`codex-gpt-5.6.md`, `grok-4.6.md` o `glm-5.3.md`. No hay ficha de Claude ni de Gemini.

No abras una ficha solo porque el nombre aparece en la petición. La matriz puede bastar. No
crees una ficha vacía para cada modelo listado por un proveedor.

### Forma del encargo

Carga un solo patrón de `references/patterns/`:

- `common-handoff.md` para el esqueleto común;
- `implementation.md` para producir y recibir un artefacto;
- `review.md` para revisión ciega o adversarial;
- `research.md` para investigación independiente;
- `plan.md` para autoría, revisión o reconciliación de planes;
- `arbitration.md` para resolver dictámenes incompatibles;
- `next-session.md` para continuidad con carga mínima;
- `grupo-gratis.md` para el bucle de coste 0 en el que el dispatcher es un script y
  ningún modelo decide la siguiente boca;
- `closed-loop-mods.md` para mods DayZ/Enforce con el plan cerrado una vez y el bucle
  corriendo en disco.
- `coupled-watcher.md` se carga ADEMÁS del patrón del encargo cuando la corrida es desacoplada:
  runner + vigía en background, cuatro transiciones (EXIT, ORCHESTRATOR_NEEDED, ronda, DISPUTA), re-armado.

No mezcles varios roles en una sesión. Si el trabajo tiene fases, cierra y recibe una antes
de abrir la siguiente.

### Evidencia

Las referencias bajo `references/evidence/` justifican fechas, bancos, forense y track
record. No son instrucciones cargables por defecto. Ábrelas solo para auditar una regla,
resolver una contradicción o repetir una medición.

## Contrato mínimo del brief

Un brief de delegación debe ser autocontenido para la puerta elegida y declarar:

1. una tarea en una frase;
2. rol y criterio de éxito;
3. carga inicial enumerada, con rutas dentro del workspace;
4. alcance positivo y fronteras negativas;
5. permisos, riesgo y acciones prohibidas;
6. hechos verificados y supuestos etiquetados por separado;
7. entregable, ruta de escritura y formato;
8. pruebas o gate que el delegado debe ejecutar;
9. protocolo de cierre, incluida `LO QUE NO PUDE VERIFICAR`;
10. receptor que comprobará la salida.

- **El encargo nombra el PRODUCTO como una sola cosa observable (LL-442)**; el aparato
  (gate, ledger, instrumento) va a backlog aunque el revisor tenga razon, y justificar
  donde mirar con «donde salieron defectos antes» esta prohibido: es estadistica del proceso.
- **Los briefs de auditoria se escriben en lexico de ingenieria (LL-454)** con frase
  explicita de frontera local; grep previo de `adversarial|ataca|elevado|otro usuario|explota|bypass`.
  Un `rc=1` con log grande → buscar `flagged for possible cybersecurity` en el log antes
  de culpar a la cuota.
- **El punto 8 vuelve PEGADO, no resumido, o con su motivo (medido 2026-09-20).** De 165 entregas
  reales reconstruidas de los transcripts, solo 18 traían salida literal de una comprobación y
  **79 de 168 briefs le prohibían al worker correrla** (56 eran sandbox `read-only`). Si el brief
  pide un gate, el punto 7 exige el volcado literal —comando y lo que imprimió— dentro del
  entregable; y si el entorno se lo impide, una línea `GATE NO CORRIDO: <motivo>`. Sin eso, el
  receptor no puede distinguir «no lo corrió» de «no le dejaron», y el filtro de
  [`jev`](../jev/SKILL.md) se queda sin la única rama que ahorra revisor.

No pegues historiales enteros ni dependas de contexto implícito. Un hecho de relación no
medido se marca `[ASSUMPTION]`; no se presenta como axioma. Pide escritura por tramos cuando
la sesión pueda agotarse. El delegado produce el entregable: si falla, se relanza o se
reduce el alcance; no se completa a mano fingiendo que la delegación terminó.

## Restricciones comunes del aparato

Para `prime-agent`, decide siempre los tres diales `-nc`, `-ns` y `--cwd`; consulta el manual
antes de formar el comando. Especifica proveedor y modelo juntos. Contrasta ambos con el
stream para detectar un fallback silencioso.

El workspace contiene fuentes y salida. Los briefs, logs y streams de otras corridas quedan
fuera. Un `--cwd` no limita por sí solo lo que un intérprete general puede intentar; la
frontera también se expresa en el brief y se comprueba al recibir.

No copies aquí comandos completos de cada CLI. Los flags, permisos, sesiones, reintentos y
formas de salida pertenecen al manual de ruta.

## Supervisión de la corrida en marcha

Delegar transfiere la ejecución, no la responsabilidad de que la corrida avance hacia
el cometido. Y supervisar no es hacer de relay: el patrón caro de las primeras
delegaciones —cada worker contactando al orquestador en cada turno— es justo lo que
este reparto elimina. Quedan prohibidos los DOS extremos: el relay por turno y la
ceguera total. Medido el 2026-08-28 (gauntlet Grok→Codex sobre dayz-mcp): 2 h y 3
rondas ROJAS contra un gate imposible del orquestador sin que nadie mirase — el
bloqueo era arbitrable desde la ronda 1, y la disputa del implementador era una
pregunta dirigida al orquestador que no tenía canal para llegarle.

El protocolo, todo a coste ~cero en reposo (estado en disco, exits del harness, peeks
que decide el orquestador):

1. **Checkpoint tras la primera ronda, siempre.** Los errores del ENCUADRE (gate mal
   calibrado, spec imposible, allowlist sin censo) se manifiestan en la ronda 1 y
   solo el orquestador puede arbitrarlos. Leer veredicto + primer hallazgo cuesta
   ~200 tokens. Después, un peek por ronda o cada 30-45 min de corrida.
2. **Cada transición de estado produce una notificación del harness.** El driver de
   un bucle (o un watcher) SALE al cierre de cada ronda — cada exit re-invoca al
   orquestador gratis. Una única notificación terminal en una corrida de horas es
   diseño ciego. El estado vive en un fichero (LOOP-STATE) para que el peek sea una
   lectura, no un interrogatorio al worker.
   En `prime-agent`, ese estado es `~/.prime/agent/sessions/<session-id>.jsonl`: un log
   redirigido a cero bytes no demuestra que el worker esté parado.
3. **Señal ORCHESTRATOR_NEEDED.** Si el implementador escribe una sección DISPUTAS
   en su STATE, o el mismo BLOCKER sobrevive dos rondas con el mismo título, el
   driver PARA con ese estado en vez de quemar rondas contra una decisión que es del
   orquestador. Ambas condiciones se detectan con un grep del driver. La ronda N+1 del
   presupuesto tampoco existe: es ORCHESTRATOR_NEEDED. El criterio de parada (VERDE previo,
   repro-o-backlog, presupuesto N+1, procedencia por familia) tiene dueño único:
   `gates-ledger` §Cuándo para un bucle (rev. 2026-09-02).

El checkpoint es lectura de estado, no dirección: el bucle lo siguen dirigiendo el
driver y el delegado. Si el peek revela un error del encuadre propio, la corrección
viaja con el mea culpa explícito («el criterio era mío y estaba mal» —
`gauntlet-loop` §Los tres fallos): el constructor deja de defender su versión y
ataca el problema real. El pre-vuelo de la corrida nocturna (⚠ del gate) es
requisito aparte: aquel evita comprometer una noche mal; este evita que una corrida
bien lanzada muera sola.

## Un lanzamiento desacoplado NO esta completo sin su vigilante (added 2026-09-01)

Refuerzo duro de §Supervision de la corrida en marcha, que ya prohibe la ceguera total. Falta
el modo concreto por el que la ceguera se cuela: **lanzar el trabajo y lanzar el vigilante son
dos actos separados, y tras el primero la corrida PARECE lanzada** — proceso vivo, pid en
disco, artefactos apareciendo. Nada en esa foto grita que falta la mitad que despierta.

Medido el 2026-09-01: dos lanzamientos en la misma sesion (Grok implementando, Codex
revisando), los dos `Start-Process` desacoplados, los dos sin watcher, las dos veces prometi
«te aviso cuando entregue» y las dos veces **el usuario tuvo que venir a preguntar**. Su
veredicto: «problema grave de orquestacion, ha ocurrido mucho». La memoria del host ya decia
la receta correcta —trabajo DESACOPLADO, watcher ACOPLADO— y aun asi no disparo: el
conocimiento estaba, la funcion forzante no.

**El gate, de una linea, y va en el momento de prometer:** en cuanto escribas «te aviso» o
cualquier promesa de notificacion, **nombra el proceso concreto que te va a despertar**. Si no
puedes nombrarlo, no existe. Dos salidas honestas y ninguna mas:

1. lanzas el watcher acoplado (`run_in_background`) ahi mismo — su salida re-invoca al
   orquestador gratis; o
2. le dices al usuario que tendra que preguntar el.

Prometer un aviso que tu montaje no puede dar es peor que no prometerlo: el usuario deja de
vigilar porque cree que tu vigilas.

**Y la causa no es un descuido raro:** el `Start-Process` desacoplado ES la razon de que no
haya aviso, y es el mismo mecanismo que lo hace sobrevivir al /compact. Durabilidad y
notificacion se compran por separado. Por eso las dos mitades van siempre juntas.

**Receta medida y script del vigía (added 2026-09-02):** `references/patterns/coupled-watcher.md` —
runner y vigía como DOS tareas en background del harness, cuatro transiciones que despiertan (EXIT del
worker, `ORCHESTRATOR_NEEDED` nuevo por recuento, cierre de ronda, DISPUTA nueva en el STATE por
baseline de líneas), re-armado al despertar y las
trampas medidas (substring que dispara en falso, `[exited with code 0]` con el vigía vivo, muerte sin
recibo con `RC=127`).

## Protocolo común de verificación (rev. 2026-09-03)

Al terminar una delegación:

1. **Identidad.** Comprueba en la salida el proveedor y el modelo realmente usados.
2. **Término — y una lane cuenta como ENTREGADA solo con producto en la mano.** En el arnés
   normal, el `rc` no decide. Revisa `stopReason`, `errorMessage` y los eventos finales del
   stream. Un `rc=0` puede acompañar un 429 o cero bytes. El código de estado, el `rc` del
   proceso y un `ok:true` del arnés viven en el **transporte**; la entrega vive en el
   **contenido**. Antes de contar una lane: **contenido no vacío Y motivo de parada que no sea
   corte por longitud o por presupuesto** — típicamente `finish_reason` distinto de `length`,
   que significa que el presupuesto de salida se lo comió el razonamiento y **se factura
   igual**. Un **HTTP 200 con `content` vacío es una no-entrega PAGADA**, y ningún guard por
   código de retorno la ve. Medido tres veces: `qwen3.8-2.4t` (2026-08-28) y `laguna-s-2.1`
   (2026-08-27) salieron MUDOS con `content` vacío y `finish=length`; y el 2026-09-02
   `z-ai/glm-5.3` devolvió **200 con `content` vacío y `finish_reason=length` — 29.165 tokens de
   razonamiento de un presupuesto de 32.000 — y cobró 0,3022 USD por cero líneas** (su recambio
   `bai/glm-5.3-flash` falló además dos veces seguidas). Las dos primeras estaban escritas en
   `references/reachability.md` y aun así mordió la tercera: esa tabla se lee **al elegir celda**,
   y este fallo ocurre **al recibir**. Si la lane es bloqueante, el presupuesto de salida va
   holgado o no se lanza.
3. **Artefacto.** Abre cada fichero esperado. Comprueba ruta, tamaño, codificación y cambios.
4. **Citas.** Abre cada `path:line`; una cita plausible pero inventada invalida el hallazgo.
5. **Gate.** Repite las pruebas desde el receptor. No aceptes un gate rebaselinedo para pasar.
   Todo artefacto de medición lleva en cabecera el SHA contra el que midió (LL-444); al
   consumirlo se compara con HEAD, y si difiere es hipótesis: sin SHA se re-mide antes
   de repartir trabajo.
6. **Alcance.** Revisa el diff y confirma que no se tocaron rutas prohibidas.
7. **Incertidumbre.** Conserva de forma visible lo que el worker no pudo verificar.
8. **Revisión cruzada.** Entrega artefactos y fuentes a una familia distinta, en sesión ciega.
9. **Premisa del encargo (LL-401).** Todo contrato de revisión lleva, además de las
   comprobaciones enumeradas, una casilla libre y obligatoria: «¿qué puede estar mal en la
   premisa de este encargo?». Sin ella el revisor solo puede contestar «presente, colocado y
   bien formado», que no es «correcto». Un PASA en todos los gates acota lo que el contrato
   preguntó, nunca lo que el trabajo necesitaba. La distinción hechos / interpretaciones que
   `council-orchestration` exige (LL-286) se aplica a cualquier delegación de revisión, no
   solo a un council.
- **Al revisor de otra familia se le pregunta en NEGATIVO y por escrito (LL-431)**:
  «¿que defecto tendria este artefacto que este gate no veria?». Reproducir un verde
  solo prueba satisfacibilidad, no discriminacion.
- **El brief del revisor pide escenario de fallo EJECUTABLE (LL-475)**: `path:line` +
  entrada exacta + salida mala, y propuesta de mutacion para juntas; hallazgo sin repro
  → P3. Y el revisor debe PODER ejecutar: sonda `python -c` previa.

Una respuesta bien redactada no sustituye un efecto en disco. Una ausencia tampoco es un
dato hasta comprobar que la búsqueda tenía cobertura suficiente.

## Flujo receptor

Cuando el usuario pegue una salida o señale un artefacto:

- identifica la ruta y la celda que lo produjeron;
- separa hechos, cambios, pruebas, riesgos y puntos no verificados;
- verifica antes de incorporar afirmaciones a memoria o a un plan;
- registra fallos de transporte en la ruta, de cuenta en proveedor, cognitivos en modelo y
  exclusivos del par en la matriz;
- devuelve un veredicto claro: aceptar, corregir, relanzar, escalar o rechazar.
- **Antes de citar un dictamen como estado vivo, ordenalo por timestamp (LL-064)**:
  un dictamen anterior al brief de la ronda siguiente es historia, no estado; sin
  dictamen posterior a la ultima ronda, es «cerrado segun quien lo implemento», no cerrado.
- **Antes de pagar la revisión cruzada, pasa la entrega por `jev supervise` (skill `jev`, added
  2026-09-19)**, con la salida literal del gate en `evidence`. Está en **modo sombra**: registra su
  acción junto a la tuya y no la obedezcas hasta que la skill diga que salió de sombra (~100
  decisiones etiquetadas). Nunca acepta; su mejor salida es `REVISOR_CARO`.

No consolides automáticamente dos respuestas. Si discrepan, conserva el disenso y usa el
patrón de arbitraje con evidencia, no una votación por mayoría simple. **Excepción (rev. 2026-10-26, Guillermo):** en el council base de 5 miembros decide la mayoría 3/5 (§Council habitual), salvo una cita re-verificada contraria o un `DISENSO-FUERTE`.

## Fronteras de este fichero

Este `SKILL.md` posee el gate mínimo, el índice de carga y el protocolo común. No posee:

- comandos completos, flags o diagnóstico de una CLI;
- tablas largas de costes, latencia o catálogos;
- credenciales, cuotas o políticas de proveedor;
- capacidades detalladas de un modelo;
- casos históricos o bancos de medición;
- reglas repetidas de un manual vecino.

Cuando falte detalle, carga la referencia dueña. Si dos referencias afirman el mismo hecho,
no elijas la redacción que conviene: señala la contradicción y vuelve al dueño único fijado
por el mapa de migración.
## Al recibir: comprueba si lo «no verificado» lo bloqueaste tu (added 2026-08-29)

Refuerzo del §Protocolo comun de verificacion, punto 7, y del checkpoint de
§Supervision. Aquel dice **conservar** lo que el delegado no pudo verificar. Falta el
paso siguiente: **preguntar de quien es la culpa de que no pudiera**.

Origen (2026-08-28, DayZ-MCP): el brief prohibia usar el puerto 8765. Uno de los cinco
subtests del gate lanza `--client` sin `--port` y cae a ese puerto por defecto, asi que
el ejecutor **no pudo correrlo** y lo declaro en su seccion `LO QUE NO PUDE VERIFICAR`
en vez de fingir cobertura. La laguna era del encuadre, no del trabajo. El orquestador
la cerro en 11 segundos con el puerto libre — pero solo porque leyo esa seccion
preguntandose de quien era el hueco, no solo que decia.

Al recibir, para cada linea de `LO QUE NO PUDE VERIFICAR`, clasificala en tres:

- **Limite del delegado** (no supo, no cabia, no tenia evidencia) -> siguiente ronda.
- **Limite del entorno** (la caja no lo permite) -> se declara y se acepta.
- **Limite TUYO** (una frontera, un allowlist, un recurso que le vetaste) -> **lo cierras
  tu, ahora**, y el resultado viaja al brief de correccion con el mea culpa explicito.
  Un ejecutor que defiende su version contra un criterio mal puesto quema rondas; uno al
  que le dicen «el criterio era mio y estaba mal» ataca el problema real
  (`gauntlet-loop` §Los tres fallos).

Y al reves, como diseno del brief: si vas a vetar un recurso, mira antes si algun gate
que exiges lo necesita. Un veto que hace inejecutable un gate no protege nada — solo
convierte una comprobacion en una casilla vacia, y la casilla vacia se lee luego como
«cubierto» si nadie mira quien la dejo asi.

**Señal de que esto te esta pasando**: el delegado entrega con un gate «no ejecutado»
y su motivo cita una restriccion de TU brief, no una limitacion suya.

## (added 2026-08-29, LL-360) No transportar `$_` / `$var` / `$()` por shells anidadas

Un filtro PowerShell con `$_`, `$(...)` o `$var` no viaja inline dentro de bash con comillas dobles: bash expande antes y el filtro devuelve VACIO, que se lee como «no hay resultados». Usa la herramienta PowerShell nativa o un `.ps1` en disco. Un vacio inesperado se re-valida por otra via antes de construir encima.

## (added 2026-08-29, LL-366) Bloqueo de permisos: no rodearlo

Cuando el clasificador de permisos bloquea un lanzamiento agentico, no se rodea ni se trocea para colarlo. Se deja el trabajo completo y verificado (runner autocontenido que elige su venv, logs, teardown) y se entrega al humano UN comando. El humano aporta el consentimiento; nada mas.


## (added 2026-08-30, LL-391) El metodo es del ejecutor; los limites del entorno son tuyos

Al escribir el brief, separa las dos cosas. **Metodo** —como parsear, que formato, en que
orden, donde deja sus auxiliares, que lenguaje usa— es **del ejecutor**: imponerlo le
traslada tus puntos ciegos y le quita la via de escape cuando tu metodo falla. **Limites del
entorno que el no puede ver** —tope de tiempo de la corrida, cuota compartida, sandbox del
proveedor, un arbol con junctions que mata un recorrido recursivo, cuantas sesiones tocan esos
ficheros— son **tuyos, y hay que darselos**.

Medido el 2026-08-30 en la misma tanda: briefs cerrados **0 de 4** (dos muertos por el sandbox
al pedirles escribir fuera del cwd, dos parados a preguntar por falta de autoridad); briefs
abiertos **3 de 3**, dos por encima de lo especificado. Pero al abrirlos se cayo tambien
«escribe el esqueleto primero y amplia», y una lane produjo 1,8 MB de trabajo correcto y
murio de reloj (`rc=124`) **sin consolidar**: nadie le dijo que habia un tope de 50 minutos.

Prueba antes de soltar el brief: por cada frase que quites por «micromanagement», pregunta si
describe **COMO** hacerlo (fuera) o **BAJO QUE CONDICIONES** se ejecuta (dentro).

## (added 2026-08-31) La vía CLI hacia Codex/Grok está MUERTA desde dentro del worker

El worker de `prime-agent` corre en WSL, y ahí el interop de Windows está apagado:
`/proc/sys/fs/binfmt_misc/` solo tiene `register` y `status`, no existe `WSLInterop`, y `cmd.exe`
responde `cannot execute binary file: Exec format error`. Ningún `.exe`/`.cmd` es alcanzable →
`codex.cmd` y `grok.exe` quedan fuera. El shim npm de `codex` sí resuelve por `/mnt/c` pero muere
con `Missing optional dependency @openai/codex-linux-x64` (la instalación de Windows solo trae el
binario win32), y no hay codex nativo en WSL.

**No pierdas una sesión con el PATH.** Un `codex exec` lanzado desde una shell Windows va
perfectamente; el muerto es solo el camino desde DENTRO del worker. La única vía viva hacia otra
familia desde ahí es el hijo `rlm()` — estado medido y sus trampas en `references/routes/prime-agent-bitacora.md` §Subagentes RLM.
## (added 2026-09-01, LL-406) La senal de termino es un FICHERO, nunca el nombre de un proceso

> Par obligado con §Un lanzamiento desacoplado NO esta completo sin su vigilante, mas arriba en
> este mismo fichero: aquella dice que **tiene que haber** vigilante; esta, **por que senal**
> espera. Las dos se escribieron el mismo dia, en sesiones distintas, sobre el mismo agujero.

Refuerzo del §Protocolo comun de verificacion, punto 2. Aquel dice que el `rc` no decide si el
trabajo termino BIEN. Falta el escalon de antes: como sabes que la corrida **termino**, punto.

Medido el 2026-09-01 sobre `codex exec` y `grok.exe` lanzados desacoplados: tres veredictos
seguidos de «sigue corriendo» sobre una corrida acabada hacia una hora, cada uno por un
instrumento distinto y los tres fallando hacia el mismo lado.

**La regla, en una linea: el runner de cada lane escribe `EXIT` con `RC=<code>` DESPUES de que el
CLI retorne, y el vigia espera por ese fichero.**

> **Forma literal en `.cmd` (medido 2026-09-01, LL-409):** `echo RC=%ERRORLEVEL% > EXIT`, con ESPACIO antes de `>`.
> Sin el espacio cmd expande a `RC=0>` y lo lee como redirect del handle 0: crea el fichero VACIO y el
> vigia lo cuenta como terminado sin RC (paso en las 3 lanes del council del 2026-09-01). Comprobar una
> vez que aparece `RC=` antes de fiarse del lanzador.

Y las tres formas de equivocarse que sustituye:

- **`Get-Process <nombre>` no identifica una corrida.** En este host hubo a la vez dos `grok.exe`
  y dos procesos de Codex de sesiones distintas; el vigia caso con el ajeno —arrancado el dia
  anterior— y declaro vivo lo mio, que ya habia muerto. Si tienes que mirar el proceso, filtra por
  `CommandLine`, que contiene el directorio de la corrida, no por `Name`.
- **Un grep del log dispara falso.** El stream vuelca fragmentos de todo lo que el delegado LEE:
  buscar `tokens used` lo encontro porque Codex estaba leyendo un manual que habla de esa senal.
  Un marcador solo vale si el delegado no puede escribirlo por accidente.
- **`[IO.File]::ReadAllText` sobre un log vivo lanza IOException** (el proceso lo tiene abierto),
  el bucle del vigia revienta y **sale con codigo 0**: la notificacion de «completado» no prueba
  nada. Abrelo con `FileShare.ReadWrite`.

**Y la trampa que deja el marcador inalcanzable, que es la que hay que comprobar ANTES de lanzar:**
un `.cmd` invocado desde un `.bat` **sin `call`** transfiere el control y no vuelve, asi que todo
lo que escribas despues —incluido el `echo RC=`— no se ejecuta nunca. `codex.cmd` y los shims de
npm son `.cmd`. Antes de fiarte de un lanzador nuevo, corre una vez la ruta completa y comprueba
   que el `EXIT` aparece; si no aparece, el vigia se quedara sin su unica senal buena y caera al
   nombre del proceso, que es donde empieza este apartado.

## (added 2026-09-08, LL-486) Un gate resultado-AND-artefacto necesita codigos distintos

Un gate de cierre que exige resultado y artefacto colapsa dos preguntas en un bit («¿cumple
el criterio?» y «¿pudo contarmelo?»); la segunda depende del ENTORNO del worker, no de su
trabajo. Al recibir `entregado=False`: abrir el workdir antes de leer el veredicto,
reproducir el criterio, y clasificar con el trio (trabajo hecho / criterio medido /
artefacto escrito) antes de decidir nada — relanzar una lane cuyo trabajo esta en disco
paga una corrida para reproducir lo que ya existe.

## (LL-411, added 2026-09-02) Una fusion se delega como DECISIONES, no como transporte

Refuerzo del §Protocolo comun de verificacion, punto 3 (artefacto). Medido el 2026-09-01: la lane de
reconciliacion de 7 skills entrego la tabla de decisiones por hunk completa y correcta, y los ficheros
fusionados truncados (3 ausentes, 1 a medias, `out.json` a 0 B). El juicio cabe en una tabla; el transporte
de ficheros grandes por `search_replace` no cabe en los turnos. Regla: en fusiones y ediciones masivas el
entregable es `REPORT.md` con decision + evidencia por hunk; el orquestador ensambla con un script que
verifica que ninguna linea sea inventada y cuenta lo que pierde cada lado. Si la lane debe escribir ficheros
grandes, escritura por tramos y recibo de bytes por fichero, y contar los ficheros antes de leer contenido.


## (added 2026-09-02) Antes de lanzar `prime-agent` desde Windows, tres muros de transporte

Si la sesion orquestadora corre en Windows y el worker en WSL, hay tres formas medidas de perder
un arranque **sin que el modelo llegue a hablar**, y las tres dan un `RC` que miente:

1. **Una sola sesion de `prime-agent` a la vez**, aunque las lanes usen proveedores distintos: la
   segunda muere por el session worker del daemon, y `prime-agent doctor` dice `sessions 0`.
2. **`MSYS_NO_PATHCONV=1` delante de `wsl.exe`**, o Git Bash convierte tu `/mnt/c/...` en
   `C:/Program Files/Git/mnt/c/...` y sale `RC=127`.
3. **El typescript de `script` va a `/tmp`, no a drvfs**, y se copia al final.

Detalle medido, con las senales que los distinguen:
`references/routes/prime-agent.md` §Tres muros entre Git Bash y el worker.
## (added 2026-09-06, LL-459) Un `429` de limite de SESION mata a la vez TODOS los subagentes

Un `429` de limite de **sesion** (`resets HH:MM`, HTTP 429, `rate_limit`) no es el `429` de un
proveedor en una lane: mata a la vez **todos** los subagentes en vuelo. El limite es de cuenta y por
ventana, asi que la fan-out **no reparte el coste, adelanta la hora en que cae todo**.

No relances nada: anota la hora del reset y, pasada, un `SendMessage` por `agentId` los reanuda
**desde su transcripcion**, sin rehacer lecturas. A quien murio con el entregable ya escrito, pidele
un read-after-write antes de aceptar su resumen: el fichero puede haber quedado a medias.

Preventivo: **techo de ~6 subagentes Opus concurrentes**. Medido el 2026-09-04 (sesion Reserva de
DayZ-MCP): 13 subagentes lanzados en paralelo murieron juntos a las 17:05, y los 13 se reanudaron a
las 18:31 sin perder trabajo.

## (added 2026-09-19, LL-501) Subagentes del Agent tool: el informe vuelve como MENSAJE, no como fichero

En este harness un subagente `general-purpose` no puede escribir su fichero de informe («Subagents should return findings as text», 4 de 4 el 2026-09-19). Pide el informe como mensaje final autocontenido, con `path:line` y confirmado/plausible por hallazgo, y **persístelo tú** en cuanto llegue cada notificación: hasta entonces solo existe en tu contexto y una compactación se lo lleva.

## (added 2026-09-06, LL-461) Un campo que una tool valida es un CONTRATO, no una caja de texto

Antes de redactar un `EXPECT`, un `evidence_ref` o un texto de cierre que va a pasar por una tool:
abre su validador, con su `path:line`, y anota los tres datos que deciden la redaccion —**longitud
maxima, alfabeto permitido y forma exigida**. Si el campo es una **referencia** (ruta, id, url),
pruebala con control positivo y negativo ANTES de pegarla.

Escribir primero y descubrir el limite por rechazo cuesta la redaccion entera dos veces. Medido el
2026-09-06 en el buzon de DayZ-MCP: cuatro rechazos por titulo de mas de 120 caracteres y tres por
resolucion de mas de 2000, todos con el texto ya escrito.

## (added 2026-09-08) Antes de disenar el gate: SONDA el interop, no lo des por muerto

Refuerzo de §La via CLI hacia Codex/Grok esta MUERTA desde dentro del worker (2026-08-31), que
esta mas arriba en este mismo fichero. **La premisa de aquella seccion no se sostiene hoy en
este host**, y decide una cosa cara: si el worker puede correr su propio gate o si tienes que
correrselo tu.

**Lo que dice aquella seccion:** que en WSL el interop de Windows esta apagado,
`/proc/sys/fs/binfmt_misc/` solo tiene `register` y `status`, no existe `WSLInterop`, y
`cmd.exe` responde `cannot execute binary file: Exec format error`.

**Medido el 2026-09-08 (host WILLY), tres sondas:**

1. `ls /proc/sys/fs/binfmt_misc/` -> **`WSLInterop`**, `register`, `status`.
2. `/mnt/c/Windows/System32/cmd.exe /c echo INTEROP_OK` -> imprime `INTEROP_OK`.
3. `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\...\probe.ps1"` ->
   `5.1.22621.6133`, y lee bien un fichero del workspace.

**Lo que cambia en el diseno del brief, que es el motivo de escribir esto.** Con el interop
vivo, un encargo cuyo criterio de exito es un `.ps1` **se autoverifica**: el worker corre el
arnes, ve el rojo, itera, y entrega verde. Con el interop muerto, el worker entrega a ciegas y
el gate lo corres tu, que es una ronda mas por cada fallo.

Estrenado el 2026-09-08 en af59 ronda 2 (`gpt-6-astra` x `prime-agent` + `openai-codex`,
`--thinking ultra`): corrio el arnes de 9 escenarios **y las dos mutaciones de aislamiento**
el solo, y entrego `PASS=9 FAIL=0` con M1 cayendo solo en S8 y M2 solo en S9. El receptor
repitio el gate: identico, exit 0.

**Forma que hay que respetar, y fallo medido:** invocalo por `-File` con ruta **Windows**
(`C:\...`). Por `-Command` con comillas anidadas se rompe -- bash se come el `$` y PowerShell
contesta con un `ParserError` que **parece** un problema de alcance y no lo es. Perder la sonda
por ahi te hace concluir "no llego" cuando si llegas.

**La regla, en una linea: el estado del interop es una MEDIDA con fecha, no una propiedad del
host.** Cambia con actualizaciones de WSL y con reinicios. Antes de decidir quien corre el gate,
gasta los tres segundos de la sonda 2. Y no lo escribas como doctrina en ninguna direccion: esta
seccion y la del 31-ago se contradicen porque **las dos midieron bien en dias distintos**.

**Reserva declarada:** lo refutado es la PREMISA (binfmt_misc sin `WSLInterop`, `cmd.exe`
inejecutable). No he sondeado hoy `codex.cmd` ni `grok.exe` desde dentro del worker, que es lo
que aquella seccion citaba por su nombre; su conclusion sobre esas dos vias sigue sin
re-medir. Ficha del buzon: `fb-20260907-225728-b191`.

## (added 2026-09-08) Un gate mecanico sin control negativo acusa al delegado de lo tuyo

Refuerzo del §Protocolo comun de verificacion, punto 5 («repite las pruebas desde el receptor»).
Aquel dice que el receptor corre el gate. Falta lo de antes: **el gate tambien se calibra**, y
mientras no lo este sus fallos parecen fallos del trabajo delegado.

Medido en una tanda de 13 lanes: un script de ~40 lineas que comprobaba convenciones sobre las
lineas anadidas del diff dio **tres falsos positivos, cada uno de una familia distinta**, y los
tres marcaron ROJO trabajo correcto:

1. **Regex que casa con todo.** En BRE de `grep`, `\+` es «uno o mas», asi que buscar `\+\+`
   casa cualquier linea no vacia: 93 de 93 «violaciones». Para operadores, `grep -F` sobre el
   texto ya sin el `+` de columna 1 del diff.
2. **La regla tiene una excepcion legitima y el grep no la sabe.** `ref` en Enforce solo vale en
   miembros de clase — y las 9 «violaciones» eran `ref array<...> m_Wires;`, todas miembros, todas
   correctas. Cualquier regla con excepcion necesita la excepcion EN el gate.
3. **El gate mira donde ya no hay nada.** Comprobar finales de linea recorriendo
   `git diff --name-only` incluye los **borrados**, y `file` sobre una ruta que no existe no dice
   CRLF: ocho FAIL por ocho ficheros correctamente eliminados. Filtra con `--diff-filter=d`.

Y una cuarta, del mismo genero, fuera del script: **un fichero de estado rancio miente**. Un
`EXIT-REVIEW` de un intento anterior hizo declarar «terminada con RC=1» una revision que estaba
viva y escribiendo. Es LL-406 por la otra cara: el runner **borra su marca de termino al arrancar**,
y ante la duda se comparan mtimes.

**La regla, en una linea: antes de correr un gate sobre trabajo ajeno, pasalo por un control
negativo — codigo que SABES correcto.** Si lo marca ROJO, el roto es el gate. Cuesta un minuto y
evita devolver una ronda entera por un `\+` mal escapado; sin el, el coste sale en credibilidad,
porque el delegado no puede defenderse de una acusacion generada por tu propio script.

## (added 2026-09-19, LFDucati) `quemador.py` por RPC: un `rc=-9` NO es un tope de tiempo, es el primer `agent_end`

Medido en cuatro corridas `gx10 / Qwen/Qwen3.8-Flash-Next` del mismo día: `correr_con_rpc` (`scripts/prime-agent/quemador.py:113-131`) deja de leer en el PRIMER evento
`"type":"agent_end"`, cierra stdin, espera 15 s y hace `p.kill()` → `rc=-9`. Con `prime-agent` 0.9.4 ese `agent_end` llega también cuando el bucle del agente termina SIN que la puerta
haya pasado (p. ej. un turno que acaba en `stopReason: toolUse` sin llamada de herramienta válida), justo antes de la continuación autónoma. Resultado: tres corridas «cortadas» a los
1.696 s, 2.769 s y 372 s (esta última al 7.º turno), las tres con el trabajo a medias o hecho y el informe sin escribir. En los cuatro logs hay exactamente un `agent_end`, al final.

- **Diagnóstico en 10 s**: `grep -c '"type":"agent_end"' <log>` = 1 y último `stopReason` = `toolUse` → no fue el reloj ni la memoria (mirar `dmesg` no aporta nada): fue el corte del runner.
- **Al recibir `rc=-9` + `entregado=False`**: abre el workdir y repite la puerta ANTES de decidir (LL-486). Las tres veces el trabajo técnico estaba en disco; relanzarlo habría pagado otra corrida.
- **Mitigación medida a medias**: `"transporte": "pty"` en el manifiesto (la ruta vieja espera a que el proceso salga solo, así que las continuaciones corren). Arreglo de verdad pendiente:
  que `correr_con_rpc` siga leyendo tras `agent_end` mientras el proceso viva, o que espere al `EXIT` del proceso.
- **Y un patrón del worker que lo agrava**: deja el informe para el final aunque el brief pida escribirlo primero. Si la puerta muestra que solo falta el informe, encarga una lane corta de SOLO informe
  sobre el mismo workspace (con una copia `tools_orig/` para el diff) en vez de repetir el trabajo.

## (added 2026-09-19, LFDucati) `codex:codex-rescue`: corre en solo lectura y devuelve el control al LANZAR

El subagente `codex:codex-rescue` lanza la tarea de Codex en segundo plano y termina en ~100 s con «Codex Task started in the background»: su notificación de «completado» NO es el fin de la
revisión. Además la sesión de Codex sale con `sandbox_policy: read-only` y `approval_policy: never`: si el encargo pide dejar un fichero (`REVIEW.md`), Codex no puede escribirlo y lo dice
solo en su mensaje final. Un vigía atado a ese fichero se muere de hambre (45 min perdidos el 2026-09-19).

- **Señal de término**: el evento `task_complete` del rollout `~\.codex\sessions\YYYY\MM\DD\rollout-*.jsonl` de ESA corrida (se identifica por una cadena distintiva del prompt, no por la hora:
  había tres rollouts a minutos de distancia). El veredicto va en `last_agent_message`; los comandos y salidas del revisor, en los `function_call`/`function_call_output`.
- **Cosecha**: volcar `last_agent_message` a un fichero con cabecera «transcrito por el receptor, texto sin editar» + los tool calls como evidencia para el implementador. Es transporte, no autoría.
- **Si necesitas el fichero**: pide sandbox de escritura en el encargo o usa `codex exec` directo con la receta de `references/routes/codex-exec.md`; no des por hecho que la ruta del plugin escribe.
- **Cosecha sin rollouts (LL-208, 2026-09-19 TransferZ)**: `node <plugin>/scripts/codex-companion.mjs status|result <task-id>` lanzado DESDE el repo del job: el estado vive en `~/.claude/plugins/data/codex-openai-codex/state/<Repo>-<hash>/jobs/` y desde otro cwd `result` contesta «No job found» aunque el job siga vivo. El `<task-id>.log` de ese directorio trae el mensaje final entero (33 min de revisión el 2026-09-19).

## (added 2026-09-20, LL-502) Kanban `dir:` y la ruta que una tool valida: dos formas de entregar un brief roto

Dos medidas del mismo genero —el transporte rompe el encargo antes que el worker hable—:

1. **Kanban `--workspace dir:` contra un arbol con worktrees** — el worker del dispatcher puede morir en el parseo del **system prompt** (`json.decoder.jsondecodererror: expect ':' delimiting dict key and value`, dumps en `sessions/request_dump_*.json` de su perfil). Error de transporte con `rc=0`: los logs no muestran un turno del modelo, y la senal visible es solo `pid N not alive` en `kanban show`.
   - **Sonda obligatoria ANTES de encolar una tanda**: `hermes kanban show <id> | grep -c ui_meta`. Un brief que contenga `ui_meta` seguido de un salto de linea sin comas (p.ej. YAML pegado tal cual, `profile.yaml` inline) **rompe el system prompt** del worker.
   - **Frontera de alcance**: refutado solo el parseo del worker del dispatcher; la sesion `chat` interactiva del mismo perfil con el mismo texto puede vivir con el. La prueba es relanzar la misma task sin el fragmento y comparar `request_dump`/logs.
   - No culpar al BRIEF de contenido: el resto del texto puede estar intacto.
2. **La puerta normaliza URLs dentro de los briefs** — `github.com/...` salio del brief y del repositorio **con el dominio cambiado** en los artefactos de la sesion. Una URL que una tool valida es un CONTRATO (LL-461): canonizar antes al dominio de escritura; verificar con una sonda (curl o `gh`) ANTES de repartir. Un repo privado da `404` desde fuera: si el 404 viene con el dominio roto, `github.com` responde `200` y la ruta no existe — mirar el dominio.

Y del log, del dispatch del canal orquestador: tras cualquier crash, **abrir los dumps** (`hermes kanban log`, `sessions/request_dump_*.json`) antes de reencolar contra el mismo failure_limit.

## (added 2026-09-21, LL) El muro de approvals headless: `pid not alive` con `[BLOCKED: Command flagged as dangerous]`

Un executor de kanban (p.ej. @trabajador-opus) en una lane que tiene que **correr** gates/scripts (no solo leer) puede morir **x2 con el MESMO `worker_output`**: cada `powershell -NoProfile -File <script>.ps1`, todo `SCRATCH="$LOCALAPPDATA/Temp/…"` recursivo, y ciertos `for … git re…` salen `0.0s [BLOCKED: Command flagged as dangerous (script…)]` (el `0.0s`= el gate nunca se executó). El worker sobrevive con el workarround `powershell -NoProfile "& { & 'script.ps1' … }"` (esa via SÍ corre), pero si el BRIEF exige la via canonica no-vacua no puede cerrar y se suicida → `pid N not alive` a los ~15s o ~4min. Simultaneidad de lanes hermanas (ambas caen a la mesma ventana 01:10/01:13) NO implica reinicio del daemon: comprueba `tasklist` de los PIDs (todos dead) y `hermes kanban stats` (`running=0, blocked=N`) antes de culpar al dispatcher.

- **Diagnóstico determinista (0 LLM):** los dos crashes con el mesmo `worker_output` que contiene la cadena `[BLOCKED: Command flagged as dangerous` = **muro de capacidad/config del profile del executor**, no colgado. Difiere del `free tier … only be used from within` (capacidad de provider) y del `ui_meta` parseo-broke (LL-502). Los tres son muro, no colgado: **REANUDO prohibido** (quema `failure_limit` runs).
- **Sonda que no engaña:** `powershell -NoProfile -Command "Write-Output ok"` corre (exit 0). Que `-Command` viva y `-File` muera confirma que es el **policy de approvals** sobre `-File`/scripts, no powershell roto.
- **No es mi lane que cerrar:** no `unblock`/`promote` tu (privilegio del dueño), no `--yolo`/bypass (viola la política que Guillermo paga en suscripciones y el veto de "no matar nada"). Sella `hermes kanban block --kind capability` (va al flujo triage→humano) + postea evidencia en el task, retira la lane de `TASKS`/`BRANCHES` del watch (else wake fantasma). **Fix del dueño:** aprovar el patrn dangerous p/el profile executor via `hermes approvals` o pinear approvals en el dispatch, y despues `unblock`+`promote`; al reanudar re-registrar la lane en el watch.
- **Trampa del watch:** un `blocked` que el `default` no resucitó puede parecer "quieto"; el `default` reabre a los ~min (medido LL de la skill vigía). Re-leer `status` tras el `block` y **no soltar el turno hasta verlo en `blocked`**. El wake nombrado real son los **comments del propio task** (el feed que @hermes lee): `notify-list` estava vacío, así que el comentario-escalada ES la señal; nombra-lo en el cierre si no hay suscripción.

## GX10: rebajado a informativo — FREEZE (rev. 2026-10-26; reglas del dueño, 2026-09-19, 2026-09-26 y 2026-10-04)

**Congelado (Guillermo, 2026-10-26): no se carga ni se cambia ningún modelo; se lee `/v1/models` y se usa solo lo que ya sirva** (el 26-oct, `DeepSeek-V4.1-Flash-1017`: lectura fechada, no estado vivo). Ya no es el primer peldaño (ver §Escalera de EJECUCIÓN). Lo que sigue vale para lo que ya sirva: es local, gratis y no gasta cuota. **Máximo 4 lanes activas a la vez, en total,
contando las de todas las sesiones** (Guillermo, 2026-10-04; antes 3, desde el 2026-09-26). Antes de encolar, `python scripts/gx10_occupancy.py`:
- `FREE`, o `BUSY` con 1-3 en curso: se lanza.
- `FULL` (4 en curso, peticiones esperando por capacidad o caché KV ≥ 70 %) o `DOWN`: no se lanza ahí. Siguiente peldaño:
  §Ejecución gratis si el contenido puede salir de casa; si no, Ollama.

`prime-agent` sigue siendo una sesión a la vez por host (§tres muros de transporte). Las otras plazas son de Hermes, de la API
directa o de otros hosts.
`/v1/models` NO mide ocupación: respondió en 0,1 s durante ~7 h de generaciones caducadas porque Hermes llenaba el servidor.
Detalle: [ficha del GX10](references/providers/gx10.md) §Ocupación ANTES de lanzar.
- **(added 2026-09-25) Por API directa a `:8001`, pon `stream: true` siempre que la generación pueda pasar de 10 min.** Sin
  streaming, el proxy devuelve `502 timed out` a los ~600 s y se pierde todo (4/4 medido); con streaming pasaron peticiones de
  hasta 746 s. Con thinking, `max_tokens` ≥35-40k o sale muda. Contexto de hasta 200k por lane: presupuestado. Con más de ~100k,
  repite el encargo DESPUÉS del material: 2 de 5 peticiones de 145-170k degeneraron con el encargo solo al principio.
  Detalle en la [ficha](references/providers/gx10.md) §(added 2026-09-25).


## Officer Tokens / coste Cursor (2026-09-23)

Guillermo 2026-09-23 (correccion OT tras quemar Ultra):

1. **Siempre la lane mas barata que cumpla el done-when.** Escalera EJECUCION (rev. 2026-10-26): gratis (OpenCode Zen y claves gratis) -> suscripcion priorizada (agy/Argon -> Muse -> grok-cli -> Codex -> Claude; Cursor solo contingencia de Grok) -> solo entonces pago; ver §Escalera de EJECUCIÓN. El GX10 ya no es peldaño (FREEZE).
2. **Cursor es contingencia de Grok** (rev. 2026-10-26; la puerta por defecto es `grok-cli`, 2026-09-25) y no gasta Ultra en modelos no-Grok. Otros modelos en Cursor solo excepcionales con GO explicito de Guillermo; OT debe **NO-GO** si hay sub propia o gratis/barato equivalente.
3. **Cursor NUNCA** para Anthropic ni OpenAI/ChatGPT/gpt-*-sol/Astra/Luna (ningun rol, incluido Cloud Agent): Sol/JUICIO = `codex exec` (sub OpenAI); Claude = `claude -p` / sub Anthropic; **Luna = solo `codex exec -m gpt-6-luna`** (o orq-dispatch con esa celda; celda WORKS en reachability). Muse Spark = OpenCode Zen (rev. 2026-10-26: `muse-spark-1.2-contributor-free` ya no figura en `opencode models opencode`). Nunca Cloud Agent Cursor en masa para estos modelos.
4. **Officer Tokens** al congelar BRIEF: si Orq pide N Cloud Agents Cursor con modelo no-Grok, **frenar** aunque el techo de tokens quepa. Cupo Ultra agotado = senal, no reintentar en bucle.
5. Excepcion puntual (p.ej. prueba unica) no se convierte en politica; tras la prueba vuelve el default barato.

## JUICIO Codex Sol 6.0 (2026-09-23)

Guillermo 2026-09-23 (via Experto IA): revisor/JUICIO Codex en hops Sol/re-Sol **NUEVOS** = `gpt-6-sol` (Sol 6.0), no `gpt-5.6-sol`. Puerta `codex exec -m gpt-6-sol` (o orq-dispatch con esa celda). No mid-flight swap de un Sol ya LIVE. Cursor sigue vetado para OpenAI/Sol.
6. **Revisar model_id al sellar** (Guillermo 2026-09-23): no memorizar catalogo; consultar reachability/Experto IA y exigir el mas reciente de esa familia. Id viejo = NO-GO o corregir antes de YES.

Slugs canónicos 2026-09-23 ~02:02: `gpt-6-sol` / `gpt-6-luna` (CLI≥0.156). **NO** `gpt-6.0-sol` / `gpt-6.0-luna`.

(rev. 2026-10-26) **El Sol vivo es `gpt-6.1-sol`** (sondado con `codex-cli 0.160.0`; también responde `astra`). `gpt-6-sol` es el slug del 2026-09-23. El catálogo del CLI manda; un Sol ya LIVE no se cambia a mitad de vuelo.

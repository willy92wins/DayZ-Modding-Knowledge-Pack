# Prompt conventions

Why agent and skill files in this repo look the way they do. Read this before writing or editing anything in `.claude/agents/` or `.claude/skills/`.

## TL;DR

- **Uppercase section headers** (`## NAME`, `## ROLE`, `## CONSTRAINTS`) are structural — for tooling and scannability, not for the model.
- **Inline caps directives** (`MUST`, `NEVER`, `ALWAYS`, `DO NOT`, `CRITICAL`) are behavioral — they measurably increase model compliance, but only when used sparingly.
- **Lowercase prose for everything else.** Caps are a finite signal; spending them on decoration burns the budget you need for real rules.

## Why caps directives work

Capitalized directives like `MUST`, `MUST NOT`, `SHALL`, `SHOULD`, and `MAY` come from **RFC 2119**, the IETF's "Key words for use in RFCs to Indicate Requirement Levels." That convention is everywhere in the training data: protocol specs, security standards, API contracts, compliance docs. Whenever a document needed an unambiguous rule that a reader couldn't talk themselves out of, the author capitalized the verb.

LLMs have absorbed that pattern. Anthropic's own prompting guide explicitly recommends using caps for critical instructions, and in practice:

- *"you must not delete files"* — gets rationalized away ("the user clearly wants this resolved, deleting seems necessary…")
- *"you MUST NOT delete files"* — held to as a hard rule

Same words, measurably different compliance rates. This is real, not folklore.

## Why caps work *only when rare*

Caps function as a salience boost. The boost exists **because most surrounding text is lowercase** — caps stand out against the baseline. If a file is wall-to-wall `EVERY AGENT MUST ALWAYS DO X AND NEVER DO Y`, the model treats that as the author's normal voice and the emphasis evaporates. You end up with noisy prose AND no compliance lift — worst of both.

The signal is finite. Spend it on rules that, if violated, would mean the agent failed its job.

## How to decide whether to cap something

Apply this test to any directive you're tempted to capitalize:

> If I remove the caps and read the sentence aloud, does it still feel like an absolute rule?

- **Yes** → leave it lowercase. The grammar already carries the weight.
- **No, removing the caps would let the model rationalize an exception** → keep it capped.

Examples from the existing agents that pass the test:

- `DO NOT write fixes yourself` (mod-reviewer's whole identity is "audit, don't fix" — without caps the model would slip into fixing)
- `NEVER on params/returns/locals/typedefs` (a hard EnScript rule with no exceptions)
- `MUST conform to the style guide` (non-negotiable, blocks the work otherwise)

Examples that would *fail* the test (and should stay lowercase):

- `you must read the file before editing` — already enforced by tooling, no rationalization risk
- `you should always be helpful` — vague, not actionable, no specific failure mode
- `IMPORTANT: this is a tip about formatting` — decoration; the word "tip" already framed it

## Section headers — different rule

Section headers (`## NAME`, `## ROLE`, `## CAPABILITIES`, `## CONSTRAINTS`, `## EXAMPLES`) are uppercase by convention but for a different reason: the `agent-creator` skill validates the template structure, and consistent caps make sections greppable and visually distinct from inline content. Doesn't change model behavior — could be lowercase and nothing would break.

If you're authoring a new agent, follow the existing template exactly (uppercase headers, no trailing colons, blank line after each heading). The structural rules are enforced by `agent-creator`; deviating from them just makes the file fail validation.

## Quick checklist for writing a new agent or skill

1. Section headers: uppercase `## NAME`, `## ROLE`, etc. — match the existing template.
2. Inline caps: reserve `MUST` / `NEVER` / `ALWAYS` / `DO NOT` for actual hard rules. Apply the "remove the caps and re-read" test.
3. Default to lowercase prose. Trust the grammar.
4. If half the bullets in a section are capped, you've over-spent the signal — demote some to lowercase.

---

## CROSS-ENGINE / CROSS-LANGUAGE CONTAMINATION (added 2026-05-12)

Cuando una skill documenta un sistema que comparte familia con otro mejor documentado online — Arma 3 ↔ DayZ, SQF ↔ EnScript, Python 2 ↔ 3, Vue 2 ↔ 3, React class ↔ hooks — el riesgo dominante es **transferir conocimiento de la versión mejor documentada a la peor sin re-verificar**. El autor da por hecho que comparten valores cuando solo comparten parentesco.

Anti-patrones detectados en 2026-05-12 (verificados contra los archivos reales, NO contra el audit narrativo):

- En `dayz-p3d-audit/scripts/audit_p3d.py` y `dayz-p3d-inspector` hay rastro histórico de la contaminación: comentarios "Earlier versions used 2e13 / 3e13 / 7e13 — those values were wrong for modern DayZ" indican que rangos Arma 3 ESTUVIERON ahí y se corrigieron. El bug NO está en código actual.
- En `dayz-pbo-build/references/validation-scripts.md:226-228` el `known_bases` mezcla bases válidas de DayZ (`Inventory_Base`, `Container_Base`, `HouseNoDestruct`) con etiquetas Arma 3 puras (`Motorcycle`, `Helicopter`) — un usuario que herede de `Motorcycle` en DayZ no encuentra la clase. Verificación recomendada: filtrar contra `P:\dz\` vanilla.
- Caso paradójico (meta): el audit que pretendía detectar esta contaminación afirmó hallazgos concretos (ShadowVolume `9e9..1.1e10`, `dayz-p3d-audit:34`) que **NO EXISTEN en el código actual**. El bug que el audit citaba era de una versión previa ya corregida. Lección: incluso los audits confabulan — verificar contra fuente PRIMARIA (el archivo) antes de creer al audit.

Regla operativa antes de escribir un magic number, lista de clases base, o restricción de lenguaje en una skill de sistema poco documentado:

1. ¿Esta información viene de fuente nativa (P:\ vanilla, repo BI, docs Enfusion, scripts vanilla del propio juego)? Cita `path:line` o URL.
2. ¿O viene de un cousin engine (Arma3/SQF/legacy) que asumí aplicaba? Si sí, marcar `[NEEDS DAYZ VERIFICATION]` hasta confirmar.
3. Para lenguajes (EnScript, etc.): fuente autoritativa = binario o scripts vanilla del juego. Citarlo. No fiarse de blogs comunitarios sin cross-check contra el `.c` real.

Caso DEBUNKED-y-luego-corregido (audit 2026-05-12; actualizado 2026-07-06): el audit afirmó que `?:`, `++`, `foreach`, `+=` "son features válidas de EnScript". La verificación de 2026-05-12 contra las skills de entonces concluyó "los cuatro NO soportados". El veredicto final quedó partido:

- `?:` (ternario) — el desmentido SE SOSTIENE: no compila en EnScript. Sigue prohibido (enforce-script-reference, hard rules).
- `++`, `foreach`, `+=` — el audit TENÍA RAZÓN: verificado después en producción (LBmaster) y en los scripts vanilla del propio juego (`P:\scripts\3_game\billboardset.c:108` usa foreach, entre muchos). Las skills que los listaban como prohibidos estaban equivocadas y se corrigieron (enforce-script-reference reglas 2-4).

Lección meta REVISADA (más fuerte que la original): en 2026-05-12 el claim se "refutó" citando 4-5 skills coincidentes — pero N skills que repiten el mismo claim NO son N fuentes independientes si comparten linaje (todas heredaban la misma nota antigua). Consenso multi-skill ≠ verificación. La única fuente primaria para restricciones de lenguaje es el compilador / los scripts vanilla del juego; un solo `.c` vanilla usando `foreach` pesa más que 5 skills diciendo que no existe.

## DISCOVERABILITY THROUGH USER VOCABULARY (added 2026-05-12)

El `name:` y `description:` de una skill son lo que decide si Claude la autoinvoca cuando el usuario pregunta sobre el dominio. Si la skill se llama con jerga interna o nombre técnico que el usuario nunca diría, no se autoinvocará — existe pero nadie la encuentra.

Anti-patrón: skill `japm-pbo-recovery`. "JAPM" es el identificador del autor de la herramienta; el nombre comercial real es "PBO Tools". Un usuario que googlee "decompile PBO Tools" / "recover PBO source" / "obfuscated PBO" no encuentra la skill.

Regla: en `description:` incluir:

1. Nombre técnico del sistema (para precisión).
2. Nombre(s) comercial(es) o producto(s) público(s) asociados (lo que el usuario googlearía).
3. Verbos de usuario en imperativo presente: "decompile", "recover", "fix", "audit" — lo que el usuario teclea.
4. Síntomas del problema: "lost my source", "no source available", "obfuscated" — cómo lo describe el usuario antes de saber la solución.

Ejemplo correcto (parche aplicable a `japm-pbo-recovery`):

> Recover source code from DayZ PBO files obfuscated with JAPM **(also known as "PBO Tools")**. Use whenever: user mentions "PBO Tools", "JAPM", "obfuscated PBO", "lost my source", "recover PBO source", "decompile PBO", ...

## PROFUNDIDAD DE RESPUESTA (added 2026-05-12, recalibrada 2026-08-05)

El modelo ya tiende a ensanchar el alcance y a alargar la respuesta por su cuenta, y su
harness ya instruye "entregar lo pedido, al alcance pedido". La versión anterior de esta
sección mandaba lo contrario —subir por defecto **un nivel más profundo**— y empujaba justo
el fallo que hoy hay que frenar. El default correcto es **el alcance pedido**.

- Tarea acotada ("búscame sobre X", "qué te parece Y") → responder a ese nivel. Si el dominio
  es complejo y queda algo sustancial por decir, UNA frase al final ofreciéndolo: "puedo
  bajar a alternativas + criterios + riesgos si lo quieres".
- No inflar el primer turno con secciones que nadie pidió (matrices, 5+ opciones, auditorías
  laterales) salvo que el coste de no hacerlo sea irreversible (`G1`, formato persistente).
- Recomendar antes que enumerar sigue mandando (`G4`): máx 3 opciones y la recomendación
  primero, no un catálogo.

Palabras-clave con las que el usuario fija el nivel:

| Palabra-clave | Profundidad |
|---|---|
| "rápido" / "breve" | 2-4 frases máximo |
| (sin palabra) | el alcance pedido, sin subir de nivel |
| "profundo" / "a fondo" / "con math" / "audit" | exhaustivo |

Una vez establecido el nivel, mantenerlo en toda la sesión salvo que el usuario lo cambie.

Origen y matiz (sesión 2026-05-12 "Optimize legendary reanimation deck"): el caso que creó
esta regla fue un análisis demasiado superficial a "búscame sobre clive's hideaway", con el
usuario insistiendo en *"haz una búsqueda mayor... haz un análisis matemático"*. Ese fallo es
real, pero la respuesta correcta no es subir el default para todo: es **leer el contexto
acumulado de la sesión**. Dominio complejo + historia previa de iteración pide profundidad;
un prompt acotado en frío, no.

## PROTOCOLO DE ENTREGA — la sesión edita directo; el guardarraíl es el CENSO de raíces (reescrito 2026-09-01)

**Sustituye a la instrucción del 2026-07-30** («una edición de skill se empaqueta, no se aplica;
la instala él»). Desde el 2026-08-31 las skills **las actualizan las sesiones directamente**, sin
empaquetar y sin pedir permiso por cada edición. Lo que NO desaparece son los guardarraíles
mecánicos: cambian de sitio, del permiso al censo.

### El guardarraíl que sustituye al permiso: censa las raíces ANTES de editar

Escribir en UNA raíz deja **deriva invisible**: la copia que edita esta sesión y la que sirve al
agente pueden ser distintas, y nadie lo ve hasta que alguien lee la vieja. Antes de tocar una
skill, enumera dónde vive y **clasifica enlaces antes de contar** (regla de junctions):

```
~\.claude\skills\<name>                          <- lo lee Claude Code (CLI)
~\.agents\skills\<name>                          <- muchas entradas son junction a la de .claude
…\skills-plugin\<guid>\<guid>\skills\<name>      <- lo lee la app; hay N GUID y son plugins DISTINTOS
~\.grok\skills\<name>                            <- proyección; medido 2026-09-01: junction al plugin
```

Escribe en **todas las copias reales**; las que sean enlace ya quedan cubiertas. Verifica al
terminar por **sha256**, no por mtime. Ejemplo medido el 2026-09-01: `codex-handoff-template` y
`grok-handoff-template` existían en una sola copia real (plugin) y `~\.grok\skills` era junction a
ella, así que un solo write cubrió las dos vistas — pero eso **se comprueba, no se supone**.

### Lo que decide quién te gobierna: el manifiesto, no la carpeta

Una carpeta no dice qué la gobierna. `<plugin>\manifest.json` sí: trae por skill su `skillId`,
`enabled`, `creatorType` y `updatedAt`. Antes de concluir que una skill está huérfana, ábrelo.
El 2026-09-01 se dieron por huérfanas seis skills que estaban **registradas y habilitadas**, y el
«rescate» acabó dejando el arreglo en la copia sin gobierno mientras la servida seguía rota.

**Caveat medido:** editar la proyección del plugin **persiste** (host-direct, sha estable a los
minutos), pero **no** mueve el `updatedAt` del registro. La edición vive en local; si la app
re-sincroniza desde servidor, se pierde. Si el cambio tiene que sobrevivir a eso, dilo al usuario.

### Guardarraíles mecánicos que siguen en pie

1. **En el árbol del plugin, escribe host-direct con PowerShell**, nunca con Edit/Write del
   harness: allí van a una vista overlay que diverge del disco real. Leer para empaquetar, sí.
2. **Backup antes**, y **read-after-write** siempre.
3. **Barre con control positivo.** Si tu comprobación final da cero, pásala por la versión previa
   al arreglo: si allí también da cero, lo roto es tu detector, no el fichero que declaras limpio.

### Cuándo SÍ se empaqueta un `.skill`

Ya no es la vía de entrega por defecto. Queda para llevar una skill a una máquina o a un almacén
que no tiene copia. Si empaquetas:

1. `python C:\Users\<you>\.claude\skills\_shared\pack_skill.py <carpeta> <DIRECTORIO destino>` — el
   segundo argumento es un **directorio**; pasarle un `.skill` muere con `FileExistsError`.
   NO uses `skill-creator/scripts/package_skill.py`: lee `SKILL.md` sin `encoding`, cae a cp1252 en
   Windows y muere con `UnicodeDecodeError` ante cualquier em-dash, flecha o acento (3 de 8 skills
   murieron ahí el 2026-07-27).
2. **Instalar REEMPLAZA la carpeta entera, no fusiona.** Empaqueta desde la copia **más completa**
   —normalmente la del plugin, que puede vendorizar `scripts/` o `wheels/`— o instalar los borra.
   Con `dayz-3d-viewer` habría tirado 6 scripts que su propio `SKILL.md:51` invoca.
3. Empaqueta la skill **entera**: `SKILL.md` + `references/` + `scripts/` + `assets/`. Un
   `SKILL.md` suelto la instala mutilada, y un fragmento `.md` ni siquiera instala
   (`SKILL.md must start with YAML frontmatter (---)`).
4. El script excluye `__pycache__`, `.git`, `.pyc` y `.pyo` (`pack_skill.py:22-23`) pero **no** los
   `SKILL.md.bak*`: si la carpeta tiene backups, empaqueta desde una copia en scratchpad con el
   mismo nombre de carpeta y bórralos allí.

`pack_skill.py` ya valida que haya frontmatter y `name`, que el `description` no pase de 1024
caracteres (recortar sacando lo que no dispara al body, nunca truncando), y reabre el zip para
comprobar que las entradas usan `/` y no `\` — `CreateFromDirectory` de PowerShell 5.1 las escribe
con backslash y entonces el instalador no encuentra `<nombre>/SKILL.md`.

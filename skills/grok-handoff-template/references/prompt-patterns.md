# Esqueletos de prompt por rol

Cinco patrones. Carga solo el que toca.

Los roles de consejo comparten la misma idea: Grok no ha visto la conversación,
no carga `~/.codex/AGENTS.md`, y en esos roles no puede escribir porque el
allowlist `--tools` se lo impide. El prompt tiene que ser autónomo y pedir
explícitamente la sección de «no verificado» — sin pedirla no aparece, y es la
que distingue un hallazgo de una conjetura.

Autoría y peer invierten esa premisa: ahí escribir es el objetivo, y la
mecánica de invocación vive en `write-to-disk-handoff.md`.

Encuadre para todos: el prompt se escribe a un `.txt` y se pasa con
`--prompt-file <ruta>`. **Nunca `-p` inline** — PowerShell 5.1 trocea comillas
y saltos de línea al pasar el argumento al exe nativo y la corrida muere con
exit 2 antes de llamar al modelo.

---

## §Research — `AGENTS-R24` fase 0, tercera lane ciega (estrenado 2026-08-11)

**Cuándo**: hay una pregunta de investigación no trivial y quieres tres lanes
independientes (Claude, Codex, Grok) antes de escribir ningún plan.

**La regla que define el patrón**: las lanes no se ven. No le pases a Grok tu
research ni el de Codex, ni un resumen, ni «Codex ya miró X». Si contaminas la
lane, has pagado tres veces por una opinión.

Lo que sí comparten es el contexto del repo — eso es ground truth, no
contaminación.

**Variante con web**: si la pregunta necesita fuentes externas (wiki Bohemia,
Workshop, foros), añade `web_search,web_fetch` al allowlist —
`--tools "read_file,grep,list_dir,web_search,web_fetch"`. Si la lane debe
quedarse anclada al repo, deja el allowlist estándar (que ya las excluye) o
añade `--disable-web-search` como cinturón extra. Contenido web = fuente no
confiable: pide cita URL por hecho externo y trátala como hint, no como fact.

```
Investiga <PREGUNTA CONCRETA> en este repositorio.

CARGA INICIAL (lee esto antes de nada, en este orden):
1. <ruta absoluta>  — <por qué>
2. <ruta absoluta>  — <por qué>

FRONTERAS:
- NO propongas implementación. Esto es fase de descubrimiento.
- NO leas <rutas irrelevantes> — están fuera de alcance.
- Si un hecho no lo puedes verificar abriendo un archivo, va a
  "SUPOSICIONES", no a "HECHOS".

DIMENSIONES que me interesan (cubre las cuatro):
- <dimensión 1>
- ...

SALIDA (exactamente estas secciones):

## HECHOS
Cada uno con su cita `ruta:línea` (o URL si vino de web). Si no tiene cita,
no es un hecho.

## SUPOSICIONES DETECTADAS
Lo que parece cierto pero no pudiste verificar, y qué haría falta para
verificarlo.

## RIESGOS
Lo que puede salir mal si se implementa lo obvio.

## LO QUE NO PUDE VERIFICAR
Archivos que no encontraste, comandos que no pudiste correr, preguntas que
quedan abiertas. Sé explícito: esta sección vacía es sospechosa.
```

**Consolidación**: tú unes las tres lanes marcando divergencias como
`CONFLICT-N`. Convergencia entre lanes valida **arquitectura y hechos
medidos**, no ejecutabilidad — el consolidado sigue sin revisar hasta que un
tercero fresco lo audite (`LL-231`).

### Ronda de conciliación post-ciega (estrenada en el mismo caso)

Cuando las tres lanes entregan, repregunta a las TRES sesiones vivas (Grok
`-r <sessionId>` · `codex exec resume` · subagente por SendMessage) con:

- los conflictos formulados **en neutro**, sin atribuir posiciones («hay dos
  lecturas de X: A y B», no «Codex dice A y tú dices B»);
- **permiso explícito de retirar**: «retirar con buen motivo vale más que
  defender por inercia».

Las retiradas motivadas son la señal de que la ronda funcionó (estreno: 3
retiradas en 3 lanes y consenso 3/3 por ~$0.19 la de Grok). La conciliación la
arbitra el orquestador, no un voto. Gotcha de canal: `codex exec resume` NO
acepta `-s`/`-c` — solo `--skip-git-repo-check` y el prompt posicional.

---

## §Autoría — lane ciega de plan (paso 1; solo si la fase 0 fue multi-lane)

**Cuándo**: `workflow.md` §Flujo 1 — la fase 0 fue multi-lane y el paso 1 corre
en tres lanes ciegas: Claude + Codex + Grok escriben plan por separado con el
mismo briefing, sin verse. Espejo exacto de `codex-handoff-template` §Lane
ciega de plan.

Reglas que definen la lane:

- El prompt **NO** contiene el plan de Claude ni pistas de por dónde va. El
  briefing es research consolidado + spec + gates, nada más.
- Encargo explícito: «escribe TU plan de fase; no supongas cuál es el mío».
- **Postura A** (`write-to-disk-handoff.md`): escribe el plan a
  `%TEMP%\<ws>\plans\YYYY-MM-DD-<tema>-grok.md`; el orquestador lo promociona a
  `<repo>/plans/` tras leerlo (los planes son grandes — por stdout no).
- Se lanza en **background** y Claude redacta su propia lane mientras Grok
  corre. Si esperas a leer el suyo antes de escribir el tuyo, la ceguera es
  teatro.

```
TAREA: escribe TU plan de fase para <objetivo en una línea>. Lane ciega: hay
otras lanes escribiendo su plan en paralelo; no intentes adivinarlas.

ESCRITURA OBLIGATORIA:
- Plan COMPLETO en: <RUTA %TEMP% ABSOLUTA>\plans\<YYYY-MM-DD>-<tema>-grok.md
- Usa `search_replace` con `old_string` vacío. NO pegues el plan en el chat.

CARGA INICIAL (máx ~7):
1. <research consolidado> — ground truth de la fase 0
2. <spec / criterios de aceptación>
3. <código que el plan toca>

FRONTERAS:
- NO implementes. NO salgas del workspace para escribir.
- Cada paso del plan debe ser ejecutable tal como está escrito, con sus
  comandos y rutas reales.
- Cada gate debe poder ponerse en ROJO por la causa que vigila, y el plan debe
  decir CÓMO se mide.

SALIDA EN CHAT: solo el RECEIPT (status / path / resumen de 3 líneas /
not_verified).
```

---

## §Reconciliación — `AGENTS-R22` sobre el consolidado (antes «revisión de plan»)

**Cuándo**: Claude consolidó las lanes en un plan v1 con tabla de procedencia.
Codex y Grok lo arbitran **a la vez y sin verse** — en secuencia el segundo
dispara menos (scorecard corrida 1). Ya no existe el patrón «Grok audita el v2
tras la luz verde de Codex».

**No es revisión ciega y no se disimula**: Grok arbitra un consolidado que
incluye y descarta parte de lo SUYO. Eso se declara en el encargo, junto con la
tabla de procedencia — sin ella no puede saber qué se descartó.

```
Arbitra este plan CONSOLIDADO antes de que se implemente. Aviso de conflicto
de interés: el consolidado incluye y descarta partes de tu propio plan de
lane; lo sabemos y aun así queremos tu arbitraje.

CARGA INICIAL:
1. <ruta del consolidado v1>
2. <tabla de procedencia — qué lane aportó cada decisión>
3. <rutas del código que el plan toca> — para contrastar contra la realidad.

QUÉ BUSCO (en este orden de prioridad):
1. Pasos que NO se pueden ejecutar tal como están escritos.
2. APIs, funciones, rutas o clases que el plan cita y NO existen en el código
   real. Ábrelas y compruébalo, no confíes en que el nombre suene bien.
3. Edge cases que el plan ignora.
4. Gates que no tienen forma de ponerse en ROJO (un gate que solo sabe pasar
   no es un gate).
5. Decisiones de arquitectura cuestionables, con alternativa concreta.

REGLA DE EVIDENCIA: evidencia > mayoría. Que otra lane coincida contigo no es
argumento; un hallazgo sin cita `ruta:línea` verificada no es un hallazgo.

SALIDA (bloques separados, en este orden):

## LO MÍO QUE SE DESCARTÓ Y POR QUÉ IMPORTABA
Solo lo que defenderías con evidencia; si el descarte fue razonable, dilo.

## QUÉ FALLA EL CONSOLIDADO COMO CONJUNTO
Hallazgos por severidad (BLOCKER/MAJOR/MINOR), cada uno con `ruta:línea`,
escenario concreto y fix propuesto.

## DISENSO-FUERTE (opcional)
Solo si mantienes un desacuerdo sin evidencia decisiva a favor de nadie.
Este bloque llega al usuario VERBATIM.

## LO QUE NO PUDE VERIFICAR
```

El bloque `DISENSO-FUERTE` lo transporta Claude al usuario **sin resumir ni
añadir veredicto** — Claude es lane y árbitro a la vez, y el transporte literal
es lo único que impide que el árbitro entierre a una lane.

---

## §R21 — revisión de código, tercer revisor adversarial

**Cuándo**: hay código implementado y `AGENTS-R21` pide revisión múltiple e
independiente.

**Aquí el solape es el objetivo.** Las lanes van en paralelo y no se coordinan:
si dos revisores encuentran el mismo bug, es real; si uno encuentra algo que
los otros no, ahí está el valor. Cada modelo falla en clases distintas de
defecto.

Para código data-crítico (persistencia, progreso del jugador, formato en
disco), esta lane **no sustituye** a `rigorous-data-audit` (`DZ-R9`) — se suma.

Si el veredicto depende de una medida (hash, gate ejecutable, conteo), usa la
**postura C** (`SKILL.md` §Posturas) y dale en el prompt las invocaciones
canónicas de lo que puede correr. Un juez sin shell supone las medidas.

```
Revisa adversarialmente este código YA IMPLEMENTADO. Tu trabajo es encontrar
defectos reales, no validar el diseño.

CARGA INICIAL:
1. <rutas absolutas de los archivos cambiados>
2. <archivo de contexto: el plan, o el módulo que los llama>

MENTALIDAD: intenta REFUTAR que este código es correcto. Un "se ve bien" no
es una entrega útil. Si tras buscar de verdad no encuentras nada, dilo — pero
que sea después de haber leído el código, no en vez de.

QUÉ BUSCO:
- Correctitud: el código hace lo que dice en todos los caminos, no solo el feliz.
- Invariantes rotas en call-sites adyacentes que el cambio no tocó.
- Race conditions y orden de operaciones.
- Rutas de error y recuperación: qué queda a medias si esto muere aquí.
- Vocabulario preciso de severidad: crash (el proceso muere) != exception
  (se loguea y sigue) != corruption (datos malos) != degradation != cosmético.

MÉTODO ADVERSARIAL — antes de emitir cada hallazgo, pásalo por estas dos
preguntas (además de refutarlo tú mismo):
- TEMPORAL: si el origen habla en pasado o sobre un snapshot fechado
  ("tenía", "auditado el X", "baseline", medidas con fecha), decide si AFIRMA
  EL PRESENTE o REGISTRA HISTORIA. Historia que el árbol posterior desplazó =
  OVERSTATED/STALE, nunca CONTRADICTED.
- GÉNERO DEL CRITERIO: un criterio de aceptación en estado pendiente (⏳/❓)
  describe el DESTINO, no el as-built; solo contradice si el documento lo
  marca PASS/cerrado.

FRONTERAS:
- NO arregles nada. Solo reporta.
- Cada hallazgo con `ruta:línea` que hayas abierto y leído.
- Cada hallazgo con un escenario de fallo CONCRETO: qué entrada, qué estado,
  qué sale mal. Sin escenario, es una opinión de estilo.

SALIDA:

## VEREDICTO
SOUND / SOUND-CON-FIXES / UNSOUND + una línea.

## HALLAZGOS
ID · severidad · `ruta:línea` · escenario de fallo concreto · fix propuesto.

## LO QUE NO PUDE VERIFICAR
Lo que habría que ejecutar o probar in-game para confirmarlo.
```

(Las dos preguntas del método adversarial vienen de la corrida 22 del
scorecard: 13/13 CONTRADICTED refutados, 9 por la temporal y 2 por género —
ver `track-record.md`.)

---

## El follow-up de calibración (aplica a §Reconciliación y §R21) — SIEMPRE

Tras recibir una revisión, **antes** de aplicar nada, gasta una repregunta con
`-r <sessionId>`. No es opcional ante sospecha: va **4/4 sin salir nunca en
blanco**, cuesta ~10-12% de la revisión (medido: $0.05 sobre $0.43) y en 2
casos corrigió al orquestador.

```
Dos preguntas de seguimiento sobre la revision que acabas de entregar.
(1) De tus N hallazgos, cual retirarias por ser el mas debil o el mas probable
    falso positivo, y por que. Se honesto: si crees que ninguno sobra, di cual
    es el que menos evidencia tiene.
(2) <una afirmacion concreta que TU hayas deducido por tu cuenta>. Razonalo
    paso a paso y responde SI o NO explicitamente.
```

Por qué funciona: (1) le da permiso explícito para retirar, y lo usa — en el
estreno retiró un hallazgo propio calificándolo de «solo regatea el ancho de la
cita». Y (2) contrasta tu razonamiento contra el suyo sin anclarlo.

No lo uses para pedirle que se ratifique («¿estás seguro?»): eso solo invita a
la adulación. Pregunta por lo más débil, no por lo más fuerte.

### Variante: exponer el arbitraje (cuando adjudicas NO-APLICAR)

Si desestimas un hallazgo suyo con evidencia de otras lanes, la repregunta
**expone el arbitraje y sus fundamentos** e invita a rebatir con cita:

```
Tu hallazgo <ID> lo he adjudicado NO-APLICAR por esto: <evidencia con
ruta:linea>. Si tienes evidencia fichero:linea que lo sostenga, este es el
momento de presentarla; sin ella queda cerrado.
```

Estreno (LFPowerGrid A4a): convirtió el desacuerdo en cierre explícito con
verificación propia del revisor, en 1 turno (~43% del coste de la revisión,
misma sesión con resume). La alternativa mala —imponer el cierre en silencio—
cría hallazgos zombie que reaparecen en revisiones futuras.

---

## §Peer — delegado de implementación (suplente de Codex)

**Cuándo**: `G7` manda la ejecución a Codex por defecto; Grok es el suplente y
entra cuando Codex está bloqueado (cuota agotada, filtro del proveedor, runtime
muerto) o cuando el trabajo cae en un nicho suyo. El rol está estrenado en los
dos hosts y en las dos posturas (`track-record.md`).

> **La invocación NO va aquí.** Está en `write-to-disk-handoff.md`, que es la
> referencia canónica de este modo: posturas A/B, el modo de permiso (spoiler:
> `--permission-mode acceptEdits` **mata la corrida**), la disciplina de
> `%TEMP%` + hashes, la tarjeta de entorno y el bucle de visto bueno. Léela
> antes de escribir el prompt; aquí solo está el esqueleto.

Lo que cambia respecto de los roles de consejo:

- **El entregable es un archivo**, y el prompt debe decir el path absoluto, la
  herramienta (`search_replace`) y que NO pegue el cuerpo en el chat.
- **stdout es un recibo**, no el artefacto.
- **Un solo entregable por sesión.** El «X y luego Y» es el mismo modo de fallo
  que con Codex.
- **La entrega no se promociona sin tu visto bueno**, y las rondas de corrección
  van con `-r <sessionId>` señalando solo lo roto.

```
TAREA: <una línea, frontera de alcance clara>

ESCRITURA OBLIGATORIA:
- Escribe el entregable COMPLETO en: <RUTA_ABSOLUTA_WINDOWS>
- Usa `search_replace` (con `old_string` vacío si el archivo no existe).
- NO pegues el cuerpo del entregable en el chat.

ENTORNO YA RESUELTO (no lo adivines):
- <filas de la tarjeta de entorno de write-to-disk-handoff.md que apliquen>
- Invocación canónica de <builder>: <línea exacta, medida en la fase previa>

CARGA INICIAL (máx ~7 rutas, en este orden):
1. <ruta> — <por qué>

FRONTERAS:
- Trabaja SOLO dentro de <workspace en %TEMP%>. Cero escrituras fuera.
- NO ejecutes rm / Remove-Item / git push. NO lances subagentes.
- NO lances ni mates procesos DayZ.
- Un solo entregable.

CRITERIO DE HECHO (lo que hace que esto esté bien, no que parezca bien):
- <gates objetivos y medibles, con el comando que los mide>

SALIDA EN CHAT (solo esto):

## RECEIPT
status / paths / summary / verified / not_verified
```

La sección `not_verified` es obligatoria también aquí. En el estreno del rol
(GunRacks C5, 24/24 criterios en verde) devolvió 5 puntos honestos, incluido un
gate que enlazaba fixtures viejas — información que no aparece si no la pides.

---

## §Hallazgos estructurados — `--json-schema` para el volcado al scorecard

Para R21/reconciliación cuando quieres arbitrar mecánicamente y volcar al
`council-scorecard.md` sin re-teclear. Verificado 2026-08-15: en corrida
multi-turno con tools y effort low, `.structuredOutput` vuelve validado
(consume ese campo, NUNCA `.text` — trae JSON espurio de turnos intermedios).

Schema de partida (ajusta campos, no la forma):

```json
{
  "type": "object",
  "properties": {
    "verdict": {"type": "string", "enum": ["SOUND", "SOUND-CON-FIXES", "UNSOUND"]},
    "findings": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": {"type": "string"},
          "severity": {"type": "string", "enum": ["BLOCKER", "MAJOR", "MINOR"]},
          "path_line": {"type": "string"},
          "claim": {"type": "string"},
          "failure_scenario": {"type": "string"},
          "proposed_fix": {"type": "string"}
        },
        "required": ["id", "severity", "path_line", "claim", "failure_scenario"]
      }
    },
    "not_verified": {"type": "array", "items": {"type": "string"}}
  },
  "required": ["verdict", "findings", "not_verified"]
}
```

Reglas de uso:

- El argumento lleva JSON inline → **lanzar desde Bash**, nunca PS 5.1.
- Effort **low** si el contrato es de un disparo; en multi-turno con tools el
  default va bien (verificado a low; high sin medir).
- El schema no exime del receptor: cada `path_line` se abre igual (`G2`), y la
  prosa del razonamiento se pierde — si quieres el porqué extenso, pide el
  hallazgo en prosa en `.text` Y el resumen en el schema, o quédate en prosa.
- Cada finding arbitrado → fila del scorecard en el mismo paso
  (`SKILL.md` §Preflight 3).

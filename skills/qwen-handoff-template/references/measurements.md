# Mediciones — procedencia de cada cifra

Todas tomadas el **2026-08-15** en el sobremesa (RTX 3090 24 GB, Ollama 0.32.13,
`qwen3.8:27b` Q4 ~17 GB). Cada entrada dice cómo se obtuvo, para poder
re-medirla o desconfiar de ella con criterio.

Convención: **[M]** medido ejecutando · **[V]** verificado leyendo el fichero ·
**[?]** inferencia, trátalo como hipótesis.

## Rendimiento y contexto

| Cifra | Procedencia |
|---|---|
| Carga en frío 27,0 s | **[M]** `load_duration` nativo de Ollama tras `keep_alive:0` |
| 42,7 tok/s corto / 32,2 tok/s largo | **[M]** `eval_count / eval_duration`, no cronómetro externo |
| **7,7 tok/s con num_ctx 262144** | **[M]** 5 tareas de codegen, rango 7,4–8,4 |
| **37,7–38,7 tok/s con num_ctx 32768 / 8192** | **[M]** misma llamada, solo cambia `options.num_ctx` |
| 57% CPU / 43% GPU | **[M]** `ollama ps` con el modelo residente: `27 GB · 57%/43% CPU/GPU · 262144` |
| VRAM residente 22.169 MiB de 24.576 | **[M]** `nvidia-smi` durante la inferencia |

El salto de 7,7 → 38 tok/s es **5×** y viene solo de no reservar 256K de
contexto. Es la mejora más barata disponible.

## El harness (con y sin fuentes)

| Observación | Procedencia |
|---|---|
| Confabula firma: `vector GetBoneTransform(string)` con "I'm confident this is a real method" | **[M]** prompt sin herramientas |
| La firma real es `GetBoneTransform{LS,MS,WS}(int pivot, out vector transform[4])` | **[V]** `3_game/entities/object.c:252-254` |
| Con herramientas: 45 verificaciones, 0 citas falsas | **[M]** + **[V]** re-verifiqué las 10 de su tabla |
| Marca `NO VERIFICADO` lo que no encuentra, con motivo | **[M]** dos entradas en una misma entrega |
| Sin fuentes deriva a genérico plausible | **[M]** respuesta sobre cite-then-verify juzgada "desviada hacia contract-testing" por el senior |

## Modos de fallo

| Observación | Procedencia |
|---|---|
| Varianza 12 vs 50 llamadas, misma tarea, temp 0.1 | **[M]** dos corridas consecutivas |
| Corrida larga: 50 pasos sin entregar nada | **[M]** agotó `MAX_STEPS`; tenía la respuesta hacia el paso 15 |
| Escalado: **0 de 2** con la herramienta disponible | **[M]** una corrida atascada, otra con aviso de presupuesto |
| Verifica símbolos pero no efectos en cadena | **[M]** escribió `super.OnDebugSpawn()` con toda su tabla de firmas correcta |
| Rechaza un hallazgo **falso** citando el árbol | **[M]** se le inyectó uno falso junto a uno verdadero; aplicó el bueno, rechazó el malo |
| Detecta que una clase del mod no está en vanilla y lo declara | **[M]** `A6_Mag_SR2M_30Rnd`, con la consecuencia (`ErrorEx` si falta en `magazines[]`) |

## El bug de referencia (por qué la revisión es obligada)

El caso completo, porque es el mejor ejemplo de la frontera junior/senior:

- El junior escribió `super.OnDebugSpawn(); SpawnAttachedMagazine("A6_Mag_SR2M_30Rnd", CHAMBER);`
- **[V]** `weapon_base.c:2224-2227` — el padre hace `SpawnAmmo("", SAMF_DEFAULT)`
- **[V]** `weapon_base.c:41` — `SAMF_DEFAULT = CHAMBER | MAX_CAPACITY_MAG`
- **[V]** `weapon_base.c:783-786` — con `MAX_CAPACITY_MAG` coge `GetMaxMagazineTypeName(0)`
- **[V]** `weapon_base.c:789-793` — el segundo `CreateAttachment` sobre el slot ocupado falla, hace `ErrorEx` y `return null` **antes** de `FillChamber`
- **[V]** `automaticrifle/akm.c:55-56` — el propio vanilla lo documenta: `// Calling super for this one will just pick the 300 round mag`

Todas las firmas que el junior citó eran correctas. El defecto era la cadena.

Nota de método: el orquestador (yo) detectó el bug pero **con la causa
equivocada** — dije "cargador aleatorio" sin comprobar que `SAMF_DEFAULT` trae
`MAX_CAPACITY_MAG`. El senior lo corrigió. Un revisor que corrige al
orquestador no es un sello de goma.

## Coste

| Operación | Coste | Procedencia |
|---|---|---|
| Generar (local, con harness) | **$0** | no consume cuota |
| Revisión de un archivo completo | $0,127 | **[M]** `total_cost_usd`, 345 s, 0 findings |
| Revisión de un método pequeño | $0,060 | **[M]** 8 turnos, encontró 1 BLOCKER |
| Sonda senior→local por el puente | $0,009 | **[M]** 2 turnos |
| Referencia: revisión de plan grande | ~$0,43 | medido en sesiones previas (`grok-cli-gotchas`) |
| Re-preguntar con `-r <sessionId>` | ~12% de la original | medido en sesiones previas |

Tokens del orquestador consumidos por el bucle: **cero**. El script alterna los
dos procesos sin agente en medio, que es lo que hace que el ahorro sea real y
no un trasvase.

## Matriz de llamadas

| Dirección | Estado |
|---|---|
| `grok → local` | **[M]** verificada. $0,009, 2 turnos, tool ID `run_terminal_cmd` |
| `local → grok` | **[M]** mecánica implementada y funcional; **el modelo no la usa solo** (0/2) |
| `codex → local` | **no verificada** — Codex sin cuota hasta 2026-08-20 |
| `local → codex` | **no verificada** — misma razón |

## Backtest contra un hallazgo real (2026-08-15)

El experimento con más valor probatorio, porque tiene verdad conocida: se
reprodujo el código de una revisión pasada (LFHeli IV-4, corrida 19 del
`council-scorecard`) y se le dio el mismo encargo, sin pistas.

| | Grok (2026-08-14) | local (2026-08-15) |
|---|---|---|
| Encontró el cruce pitch↔roll | sí | **sí** |
| Coste | $1,765 + $0,463 re-review | **$0** |
| Esfuerzo | 23 turnos | 48 búsquedas / 39 min |
| Severidad | MINOR (la arbitrada) | BLOCKER (**sobreestimada**) |
| Signo del fix | no verificado | no verificado (igual) |

Contexto que da peso al resultado: el código lo escribió **Codex** (no vio el
defecto) y pasó una **pre-review de Claude** (tampoco). El scorecard registra
`solape-lane 0`.

Citas del local, re-verificadas por el orquestador:

- **[V]** `LFHeliFlightModel.c:141-144` — correcta, y es la mejor fuente: lleva
  un comentario literal `// Matrix [2] is the heli forward axis and [0] is the
  heli right axis` que fija el marco sin derivar geometría. El arbitraje
  original no la usó.
- **[V]** `LFHeliStabilizer.c:191,193` — correcta (índice 1→pitch, 2→roll).
- **[V]** `carscript.c:1142-1145` — **contenido correcto, ruta equivocada**
  (dijo `3_game/vehicles/`; vive en `4_world/entities/vehicles/`).

**Lo decisivo, y es sobre el harness**: la PRIMERA corrida devolvió `SOUND` con
cero hallazgos. Idéntico modelo, idéntico encargo, idéntico código. Solo cambió
que se arregló la poda de ventana y se subió `num_ctx` de 32768 a 49152. En la
corrida fallida el modelo repetía "no pude leer las líneas 3597-3598" — pero sí
las había leído: la poda le había borrado el resultado.

Caveat: el artefacto está **reconstruido** (el workspace original se limpió).
El arbitraje documenta la línea exacta, así que la reconstrucción es fiel, pero
no es el fichero original.

## Decodificado especulativo — MTP (2026-08-17)

RTX 3090, Ollama 0.32.13, `num_ctx` 32768, `think:false`, `temperature` 0, 600
tokens de salida, un solo stream, 66/66 capas en GPU en las seis corridas.

| modelo | `draft_num_predict` | acceptance | tok/s |
|---|---|---|---|
| qwen3.8:27b | 0 (off) | — | 29,19 |
| qwen3.8:27b | 4 (de fábrica) | 0,468 | 34,61 |
| **qwen3.8:27b** | **2** | 0,669 | **39,82** |
| qwen3.5:27b | off | — | 31,01 |
| qwen3.5:27b | 4 | 0,134 | 18,67 |
| qwen3.5:27b | 2 | 0,240 | 24,09 |

Tres cosas no obvias:

1. `draft_num_predict` es una opción **por request**, no solo un `PARAMETER` del
   Modelfile. Fuerza recarga del modelo, igual que `num_ctx`.
2. Ollama ya trae MTP encendido en `qwen3.8:27b` con el valor 4; lo que faltaba
   es la regla de que las tarjetas de 24 GB pican en 2.
3. Encenderlo en `qwen3.5:27b` es **pérdida neta**: su cabeza acepta el 13-24%
   frente al 47-67% de la 3.8, y el borrador desperdiciado cuesta más de lo que
   ahorra. Regla general: mira el `draft acceptance` del log antes de adoptar un
   flag de especulación, no el tok/s de una tirada corta.

Oráculo: `%LOCALAPPDATA%\Ollama\server.log` — `adding speculative implementation
'draft-mtp'` y `n_max=…` dicen si está puesto; `slot print_timing: … draft
acceptance = …` dice si compensa. `ollama ps` no lo muestra.

## Escalera de contexto y descarte de quants de terceros (2026-08-19)

Ollama 0.32.14, misma tarjeta. Oráculo: la columna `PROCESSOR` de `ollama ps`.

**Techo de contexto por fichero** (recarga del modelo en cada celda):

| num_ctx | fábrica `qwen3.8:27b` | AtomicChat AD-Q4_K_M | AtomicChat AD-IQ4_XS |
|---|---|---|---|
| 32.768 | 100% GPU · 66/66 | 100% GPU | 100% GPU |
| 49.152 | 100% GPU · 66/66 | 100% GPU | 100% GPU |
| 65.536 | **100% GPU · 66/66** | **6%/94% CPU** · 65/66 | 100% GPU · 66/66 |
| 98.304 | 19%/81% CPU · 58/66 | — | 16%/84% CPU · 59/66 |

**Confabulación de API, 8 tareas distintas** (`think:false`, temp 0,1, brief sin
firmas inline — la condición donde confabula). Oráculo mecánico: un símbolo
cuenta como inventado solo si el token no aparece en ninguno de los 2.805
ficheros `.c` vanilla, con cadenas y comentarios eliminados antes de extraer.

| modelo | símbolos | inventados | tasa |
|---|---|---|---|
| `qwen3.8:27b` | 85 | 20 | 23,5% |
| AD-Q4_K_M | 78 | 23 | 29,5% |
| AD-IQ4_XS | 89 | 15 | 16,9% |

Emparejado por tarea el mejor gana 4, pierde 3 y empata 1 → **no concluyente**.
Repetido antes con 5 semillas sobre UNA tarea: a temperatura 0,1 las semillas
dieron salidas casi idénticas (4 de 5 con los mismos símbolos), o sea ~1
observación disfrazada de 5. **La diversidad tiene que venir de la tarea, no de
la semilla.**

**Velocidad: no medible aquí.** Dentro de una misma carga el tok/s decae
monótonamente (50,93 → 46,24 → 45,43 → 44,34 → 42,20 en 5 repeticiones seguidas
sin recargar) y entre pasadas de una celda determinista la dispersión llegó al
44%. Con carga de escritorio de fondo y el reloj SM a 300 MHz, **por debajo del
~20% no hay medida**. Lo único perfectamente reproducible entre pasadas fue el
`draft acceptance`, idéntico a 5 decimales.

**Lo que sí quedó verificado del mecanismo de los quants calibrados** (leyendo
los tipos por tensor de la cabecera GGUF, no la etiqueta): suben `attn_k` y
`attn_v` de Q4_K a **Q8_0**, `attn_output` a Q6_K y la cabeza MTP `nextn` a
**Q8_0**; lo pagan bajando `token_embd` a IQ4_XS, `attn_q` a Q4_K y `ffn_down` a
Q5_K. La cabeza MTP **sobrevive** a su pipeline y Ollama la enciende
(`spec=draft-mtp`, acceptance 0,865-0,897). Y `ollama show` **no sirve** como
oráculo de quant: etiqueta `Q8_0` los dos ficheros AD porque lee
`general.file_type` del GGUF, un metadato, no los tensores.

**Trampa de instalación**: el CLI de Ollama 0.32.14 no importa GGUF en este host
— `ollama create -f Modelfile` con `FROM <ruta.gguf>` devuelve `400 invalid model
name` en 2 ms con ruta absoluta, relativa o con barras cambiadas, y falla
idéntico con un fichero que existe y con uno que no. La vía que funciona es la
API: `sha256` del GGUF → colocarlo en `OllamaModels\blobs\sha256-<digest>` →
`POST /api/create` con `{"model":…, "files":{"<n>.gguf":"sha256:<digest>"},
"template", "renderer", "parser", "parameters"}`. Acepta un segundo fichero en
el mapa para el **mmproj**, que es lo que conserva `vision`/`tools`/`thinking`.

## Auditoría real de un repo ajeno — ArmAToolbox (2026-08-19)

Primer encargo del junior sobre código **que no es DayZ y que nadie del pipeline
había leído**: `AlwarrenSidh/ArmAToolbox` en `016c9b8f` (addon de Blender para
`.p3d`/`.rtm`), 19 ficheros y 8.987 líneas de Python. `qwen3.8:27b`,
`--senior none`, `num_ctx` 65536, `draft_num_predict` 2.

**Coste**: 34 llamadas, **67 min**, $0,000, **0 escalados de 2** disponibles
(cuarta corrida seguida con 0 de N — el modelo no escala aunque pueda).

**Citas: 5 de 5 exactas, en la línea exacta, cero fabricadas.** Verificado con
`scripts/verify_citations.py` contra el árbol en disco. Es el resultado más
fuerte medido hasta ahora en el eje donde antes fallaba, y la variable que lo
cambió fue el campo **línea literal** en el formato de salida con el aviso de que
se iba a comparar contra el fichero.

**Razonamiento: 3 de 5 con la consecuencia bien.** Los 5 hechos eran ciertos al
leerlos:

| id | fichero:línea | hecho | consecuencia |
|---|---|---|---|
| B-01 | `MDLImporter.py:627` | 3 `return` antes del `close()` | **falsa** |
| B-02 | `MDLImporter.py:29` | `"i"` signado vs `"I"` del exportador | correcta |
| B-03 | `RTMExporter.py:110` | `open`/`close` sin `try/finally` | parcial |
| B-04 | `RTMExporter.py:161` | `keyframeList[0]` con lista vaciable en 122-127 | correcta |
| B-05 | `MDLExporter.py:446` | `except:` desnudo | correcta, expresión mal nombrada |

B-01 afirmaba que el handle se fuga y «bloquea el fichero en Windows hasta
reiniciar». En CPython el `return` suelta la última referencia y el fichero se
cierra ahí mismo. B-03 es defendible solo porque una excepción propagada retiene
el frame en su traceback — distinción que el informe no hace. Severidad inflada:
4 de 5 etiquetados MAYOR, incluidos los dos de consecuencia falsa.

**El control negativo, que es el dato más útil**: no encontró el bug conocido de
`MDLExporter.py:206` (`writeULong(filePtr, face.vertices[v]) # normal id` — las
normales se escriben por *loop* en 160-167 y la cara las indexa por *vértice*).
**Leyó ese tramo** en su llamada 12 (`156-300`) y no lo vio. No estaba sembrado en
el encargo a propósito. Confirma que el techo no es la atención sino el tipo de
inferencia: patrón local sí, relación entre dos sitios no.

**Reloj**: el 94% se va reprocesando el prompt, no generando —
`prompt eval 51.322 ms / 20.399 tokens` contra `eval 3.251 ms / 87 tokens`— porque
la poda de ventana invalida la caché de prefijo de llama.cpp y cada turno
reevalúa el historial entero. Lecturas de 78 líneas de media con picos de 175.

**Trampa de arnés cazada antes de lanzar**: `_vanilla_files()` indexaba solo
`*.c`; apuntado a un repo Python daba **0 ficheros**, cada `grep` respondía «sin
coincidencias» y el modelo lo habría leído como un hecho sobre el código. De ahí
`--ext` y el guard que aborta con índice vacío, probado en las dos direcciones
(0 ficheros → aborta; `--ext .py` → 19 ficheros, 8.987 líneas).

## Segunda pasada sobre el mismo repo, con el encargo corregido (2026-08-19)

Mismo modelo, mismo arnés, mismo repo; alcance = los ficheros que la primera
pasada declaró en su `## Sin mirar`. **45 llamadas, 61 min, $0,000, 0 escalados.**

**Citas: 6 de 6 exactas.** Acumulado de las dos auditorías: **11 de 11, cero
fabricadas**, verificadas con `verify_citations.py`.

**Consecuencias: 6 de 6 correctas**, contra 3 de 5 en la primera pasada. Las tres
cosas que cambiaron en el encargo:

1. exigir **la regla del lenguaje o de la API que produce la consecuencia**,
2. separar `confianza hecho` de `confianza consecuencia`,
3. darle el contraejemplo del refcount de CPython que había fallado.

Se ve en la salida: cada consecuencia cita ahora su regla (`range(a,b)` da `b-a`
elementos, `except:` captura `BaseException`, `open()` sin `encoding` usa
`locale.getpreferredencoding`). **Es consistente con que el arreglo funcione, no
es prueba**: ficheros distintos, ángulos distintos, n=6 contra n=5 y una sola
comparación. Para afirmarlo habría que repetir la primera pasada con el encargo
nuevo sobre los mismos tres ficheros.

**Y encontró un bug cruzado, que es lo que había fallado.** `ASCExporter.py:26`
escribe `ncols`/`nrows` como float (`sqrt(verts)` siempre lo es) y su bucle de
filas compara `row == 0` contra ese float: con rejilla no cuadrada nunca acierta
y el fichero sale entero en una línea. Comprobado ejecutándolo: 400 vértices → 20
saltos de línea, 200 vértices → **0**. El importador (`ASCImporter.py:72-75`) lee
una línea por fila tras `int()` sobre el float, así que **el `.asc` que exporta
ArmAToolbox no lo puede leer su propio importador**. Citó productor y consumidor,
como pedía el ángulo. La única imprecisión es con qué excepción muere.

**Lectura para el reparto**: el ángulo hay que nombrárselo. Con «busca bugs» se
quedó en patrón local; con «dos sitios que tienen que estar de acuerdo y no lo
están, cita las dos líneas» encontró uno de clase BLOCKER en el mismo repo.

**Poda y reloj — corregido**: la lentitud no era el número de llamadas sino que
`prune()` disparaba por número de mensajes y deslizaba la cola en cada turno,
invalidando la caché de prefijo. Ahora dispara por tamaño (75% de `num_ctx`) y
corta al 50%. Simulado sobre 60 turnos: **45 podas → 2**, prefijo estable en 57
turnos de 60 en vez de 14. Sin medir todavía en una corrida real.

## Cinco ficheros de quant comparados en los mismos tres ejes (2026-08-19)

Ampliación de la tanda de AtomicChat con los Dynamic V3 de Unsloth, publicados ese
mismo día. Todos montados con variable aislada (mismo renderer/parser/mmproj del
modelo de fábrica, solo cambian los pesos) y medidos con el mismo arnés.

| fichero | bytes | GiB | máx `num_ctx` 100% GPU | inventadas/8 tareas |
|---|---|---|---|---|
| Ollama `qwen3.8:27b` | 16.810.714.464 | 15,65 | 65.536 | 20/85 |
| AtomicChat AD-Q4_K_M | 17.120.781.792 | 15,94 | **49.152** | 23/78 |
| AtomicChat AD-IQ4_XS | 16.512.935.392 | 15,38 | 65.536 | 15/89 |
| Unsloth UD-Q4_K_M | 16.464.440.224 | 15,33 | 65.536 | 28/86 |
| **Unsloth UD-IQ4_XS** | 14.252.845.984 | **13,28** | **98.304** | 17/65 |

**El ganador y por qué**: el UD-IQ4_XS carga 98.304 con 66/66 capas y 14,3 GiB de
VRAM, donde el de fábrica y el UD-Q4_K_M ya derraman 7-8 capas a CPU. Son **+50%
de ventana** en la misma tarjeta. Con `draft_num_predict` 2 mantiene MTP vivo
(`spec=draft-mtp`) y su acceptance es **0,8951** contra 0,87385 del de fábrica —
número determinista, reproducido exacto en las cuatro tandas de la noche.

**Calidad, emparejada por tarea contra el de fábrica**: mejor en 4, peor en 1,
empate en 3, con un 15% menos de bits. Confound declarado: produjo **65 símbolos
contra 85**, o sea escribe más escueto, y "menos código" también puede ser
"solución menos completa" — la sonda no distingue.

**El 28/86 de UD-Q4_K_M es una sola tarea**: 19 símbolos inventados en `persist`,
donde se fabricó una API entera de JSON y de ficheros. Sin esa tarea queda 9/66,
el mejor de los cinco. La media agregada aquí no describe nada.

**Sonda de cabecera, 100 MB en vez de 30 GB**: la cabecera GGUF está al principio
del fichero, así que `curl -r 0-50000000` basta para leer los tipos por tensor.
Respondió gratis la pregunta que decidía si merecía la pena bajarlos — la cabeza
MTP (`nextn`) está **dentro** de los dos ficheros de Unsloth, pese a que el repo
publica además un `mtp-*.gguf` suelto. Ojo: 8 MB no llegan, la metadata del
tokenizador se los come.

**Estrategias distintas, visibles en los tensores**: AtomicChat reparte **por tipo
de tensor** (los 17 `attn_k` a Q8_0 en bloque, pagado bajando `token_embd` a
IQ4_XS); Unsloth reparte **por capa** (los mismos `attn_k` entre Q4_K, Q5_K, Q6_K
y Q8_0 según la capa, sin tocar `token_embd`). 9 tipos distintos en un fichero
contra 5 en el de Ollama. Y Unsloth declara bien el `general.file_type` (15 y 30),
mientras AtomicChat declara `Q8_0` en los dos suyos.

**Adoptado**: `qwen3.8:98k` (UD-IQ4_XS + `num_ctx` 98304 + `draft_num_predict` 2).

## Sin medir (pendiente)

Honestidad sobre los límites de este documento:

- **Las dos direcciones con Codex.** Repetir tras el 2026-08-20.
- **Trampa de contrato**: una spec que se contradice a sí misma. ¿Para y
  reporta, o elige una rama en silencio? Es el escenario donde un junior humano
  falla más.
- **Convergencia del bucle con findings.** Las dos revisiones reales cerraron en
  una ronda (una GREEN, otra con un BLOCKER aplicado). Nunca se han encadenado
  3 rondas: no sé si converge o si oscila.
- **Si el gate real del dominio pasa.** Ningún artefacto de estas pruebas se ha
  compilado ni probado in-game. Todo el "verde" de aquí es de revisión, no de
  ejecución.
- **Otros modelos locales.** `gemma4:26b`, `qwen3-coder:30b` y `qwen3-vl:30b`
  están instalados y no se han pasado por este harness. `qwen3-coder:30b` sí se
  midió sin harness: falló en la línea 20 de su primer script con un enum
  inexistente, contra un qwen3.8 que produjo geometría correcta.
- **n=1 por escenario.** Cada fila de arriba es una o dos corridas. Con una
  varianza medida de 4×, tratar cualquiera como "el comportamiento del modelo"
  sería exactamente el error que esta skill avisa de no cometer.

## Claude Code como harness del modelo local (2026-08-21)

Tarea trivial idéntica en las cuatro filas: leer un `.c` de 5 líneas y decir
clase y número de métodos. Todas respondieron correctamente.

### El aparato del orquestador, con `qwen3.8:27b`

| config | input | turnos | duración | TTFT | resultado |
|---|---|---|---|---|---|
| la del usuario (CLAUDE.md + hooks + skills + MCP) | **341.518** | 3 | 29,6 min | 7,6 min | **el stop hook sustituyó la respuesta** |
| aislada (`CLAUDE_CONFIG_DIR` vacío + `--strict-mcp-config`) | **47.603** | 2 | 5,8 min | 4,3 min | correcto |

293.915 tokens (86%) eran aparato. El `total_cost_usd` que devuelve Claude Code
contra Ollama es **nocional** —tarifas de Anthropic sobre un modelo local—; el
gasto real es 0.

### Showdown de modelos, config aislada, una sola variable

| modelo | input | duración | TTFT | GPU |
|---|---|---|---|---|
| `qwen3.8:27b` (262k nativo) | 47.603 | 5,8 min | 4,3 min | 43% |
| **`qwen3.8:65k`** | 47.604 | **1,5 min** | **1,4 min** | **100%** (17,2/17,2 GB) |
| `ornith-1.5:35b` | 43.356 | 2,4 min | 2,4 min | 81% (22,5/27,7 GB) |

**Esta tabla NO declara un modelo mejor que otro, y el motivo importa.** La
tarea era trivial y aun así consumió el **73% de la ventana de 65k**. Un lote
real se pasa de ahí, y entonces `qwen3.8:65k` trunca o se cae de la tarjeta
mientras Ornith (MoE A3B, 3B activos, 256k nativos) sigue. El ranking puede
invertirse justo donde empieza el trabajo de verdad.

### Índice de símbolos de Enforce

| | |
|---|---|
| Entrada | 2.805 ficheros, 11,6 MB (`P:\scripts`) |
| Construcción | **23 s** (1,7 s las sustituciones + 21 s ctags) |
| Índice | 53.065 símbolos; 29.561 métodos, 13.247 campos, 6.079 clases |
| `proto native` | las 3.612, con firma exacta |
| Validación | 300 clases al azar, nombre de ctags contra el token que sigue a `class` en el ORIGINAL → **300/300** |

La validación es así de específica por un motivo: comprobar solo que "el nombre
aparece en la línea" da 100% **incluso con el índice mal**, porque `Entity`
aparece igualmente en `class EntityAI extends Entity`. Un verificador que no
puede fallar no verifica nada.

### Reservas

- Todo son corridas únicas sobre una tarea trivial. No extrapolar a carga real.
- No se ha medido adherencia al protocolo de herramientas en **multi-turno
  largo**. Un `Read` correcto no predice 30 turnos.

## prime-agent como harness del local (2026-08-22)

Misma tarea trivial y mismo modelo que la tabla anterior, cambiando solo el
harness. `prime-agent` 0.8.0 en WSL, Ollama de Windows alcanzado en
`http://172.31.192.1:11434` (ya escuchaba en `0.0.0.0`, sin tocar nada).

| harness | input | output | turnos | tool calls | duración |
|---|---|---|---|---|---|
| Claude Code, config aislada | 47.603 | 209 | 2 | — | 5,8 min |
| **prime-agent** | **14.306** | 393 | 3 | 2 (`ipython`) | 7,2 min |

Las dos respondieron bien. La diferencia de contexto es estructural: **una sola
herramienta declarada contra una docena**.

### La cadena de instalación, por si hay que repetirla

Siete obstáculos, ninguno culpa del proyecto — es el precio de instalar desde una
sesión automatizada algo pensado para lanzarse a mano:

1. Windows/fuente: `canvas` no compila con node-gyp → `node_modules` vacío →
   `tsgo` ausente. Se salva con `npm install --ignore-scripts`.
2. Falta `uv` (lo necesita el kernel de IPython). `pip install uv` lo deja fuera
   del PATH, en el Scripts de usuario.
3. `uv python install 3.11` sale distinto de cero en Windows por el enlace de
   versión menor, **aunque el intérprete sí se instala**; el bootstrap mira el
   exit code y falla igual. Sin arreglo que no toque ajustes del sistema.
4. WSL: sudo pide contraseña. Se esquiva metiendo Node en `~/.local/node` para
   que el instalador no intente instalarlo él.
5. **El instalador abre `/dev/tty`** y espera una tecla: `< /dev/null` no le
   afecta y se queda colgado indefinidamente (50 min medidos, `S+`/`wait_woken`,
   cero red). **Lo tiene que lanzar una persona en su terminal.**
6. Primera invocación: timeout del daemon, por carrera de arranque en frío.
   `prime-agent doctor` lo levanta y a partir de ahí funciona.
7. Telemetría **activada por defecto** (opt-out): `PRIME_AGENT_TELEMETRY=0`,
   `DO_NOT_TRACK=1`.

### Gotcha de entorno: comillas anidadas a través de `wsl.exe`

Mordió tres veces. `$HOME` se expande en Git Bash **antes** de llegar a WSL, así
que apunta a la ruta de Windows; y el PATH de interop tapa el `node` de WSL con
el de Windows. Todo lo que vaya a WSL con variables o comillas dentro: escribirlo
a fichero y ejecutarlo allí.

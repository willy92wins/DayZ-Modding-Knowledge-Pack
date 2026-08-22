---
name: qwen-handoff-template
description: Delegar trabajo en el modelo LOCAL de Ollama (qwen3.8:27b y familia) como "empleado junior" de coste cero, y montar llamadas entre agentes en ambos sentidos — un senior de pago (Codex, Grok) descargando trabajo mecánico en el local, y el local escalando al senior cuando se atasca. Cubre el harness de verificación sin el cual el modelo confabula firmas de API, el ajuste de contexto que decide entre 38 tok/s y 7,7, el contrato de revisión obligada, los modos de fallo medidos (varianza 4x, no sabe parar, no escala solo) y el bucle generar-revisar-corregir con su coste real. Dispara con "pásaselo a qwen", "que lo haga el local", "delegar en el modelo local", "usa Ollama para esto", "sin gastar cuota", "el junior", "que lo revise el senior", o cuando Codex y Grok estén sin cuota y haya trabajo que no espera. Invócala ANTES de escribir cualquier prompt para el modelo local, porque el fallo típico es mandarle una tarea sin fuentes y recibir código con APIs inventadas que parecen correctas.
---

# Delegar en el modelo local (Qwen) como junior

Builder para encargos Claude→modelo local, y para las llamadas entre agentes en
ambas direcciones. Hermano de `codex-handoff-template` y `grok-handoff-template`;
el local ocupa un puesto distinto de los dos.

Todo lo cuantitativo de aquí está **medido en este host** (2026-08-15, ampliado
el 08-17 con el decodificado especulativo y el 08-19 con la escalera de contexto,
la comparativa de cinco ficheros de quant y dos auditorías reales sobre un repo
ajeno), no estimado. Las cifras están en `references/measurements.md` con su
procedencia y con lo que quedó sin medir.

## Por qué existe este puesto

El local no compite en calidad con un frontier: pierde. Compite en tres ejes
donde gana siempre, y por eso el puesto es real:

- **Coste marginal cero.** No consume cuota. Puedes lanzarle 50 iteraciones.
- **No tiene cuota que agotar.** El 2026-08-15 Codex devolvió `usage limit …
  try again at Aug 20th`: cinco días sin el ejecutor por defecto de `G7`. Un
  modelo local no tiene calendario.
- **Verifica sin cansarse.** Con las herramientas puestas hizo 45 comprobaciones
  contra el árbol vanilla en una tarea. Ninguna cita falló al re-verificarla.

La consecuencia práctica: **el local es para volumen con gates deterministas
detrás**, no para juicio.

### Lo que el "coste cero" no dice: lo que cuestas TÚ

Los tres ejes de arriba son ciertos y siguen siéndolo. Pero "el junior sale gratis"
es media contabilidad, y la otra media decide si delegar compensa. Medido en una
jornada real de 12 h (lane DayZ-MCP, 2026-08-20), con el local haciendo **toda** la
generación:

| | |
|---|---|
| generación (local) | **0 €** |
| orquestación (Opus 5) | **411,36 $** |

Y el reparto de esos 411 $ es lo que importa:

| concepto | $ | |
|---|---|---|
| cache read | 301,60 | **73%** |
| cache write | 85,58 | 21% |
| output — *lo que el orquestador escribió* | 24,16 | **6%** |

1.283 llamadas, **470k tokens de contexto releídos de media**, 0,32 $ por llamada.

**Léelo así: delegar ahorró la parte barata.** Lo que el senior *produce* son 24 $;
los otros 387 $ son el precio de **tener contexto vivo** durante la sesión, y eso se
paga igual escriba quien escriba. Si delegas esperando ahorrar mucho, vas a
decepcionarte: el ahorro está en el output, que es el 6%.

Delegar sigue mereciendo la pena por otras razones — no gasta cuota del senior, no
tiene calendario, y verifica sin cansarse — pero **no lo vendas como ahorro de coste
si el orquestador va a estar 12 h despierto**.

**Y el desperdicio concreto, que sí es tuyo:** de 651 llamadas a herramientas de esa
sesión, **268 (41%) fueron esperas y sondeos** — "¿ya terminó el background?", releer
un log, volver a mirar. Cada una pagó el contexto entero para no producir nada: ~85 $
de puro esperar. Con el local eso empeora, porque sus corridas tardan minutos y la
tentación de sondear es constante.

Tres reglas que salen de ese número:

- **bloquea una vez, no sondees diez.** Un `until <condición>; do sleep …; done` que
  espera al proceso cuesta una llamada; preguntar diez veces cuesta diez.
- **no encadenes verificaciones completas redundantes.** Una suite de 2 min corrida 15
  veces son 30 min y 15 contextos releídos.
- **trocea las sesiones largas.** El cache read crece con el trabajo acumulado: cuanto
  más larga la sesión, más caro cada turno siguiente.

## Routing gate — ¿esto va al local?

1. **¿El trabajo se puede verificar mecánicamente?** (un gate, un test, un grep,
   un compilador, un revisor) → candidato. Si el único juez sería tu criterio,
   no lo mandes: no ahorras nada porque tendrás que leerlo entero igual. Para
   Enforce ese gate ya está escrito: ver §El gate de firmas para Enforce.
2. **¿Las fuentes que necesita están en disco y se las puedes dar por
   herramienta?** → sí, mándalo. **Si no puede verificar, no lo mandes**: sin
   fuentes rellena los huecos con material plausible (§Sin fuentes deriva).
3. **¿Hay un senior disponible para revisar?** El contrato es que **todo lo que
   produce el junior se revisa**. Si no hay revisor, lo que entregue es un
   borrador tuyo por leer, no un entregable.
4. **¿Es trivial?** → hazlo tú. El ciclo completo son minutos de reloj.

## El contrato junior (esto es lo que hace que funcione)

El modelo mental correcto es un junior competente y literal recién llegado:
verifica lo que le mandas verificar, no inventa si le das dónde mirar, y **no
sabe cuándo ha terminado**. De ahí salen las tres reglas del contrato:

1. **Revisión obligada, siempre.** No entrega nada directamente. No es
   desconfianza: es que sus fallos y los del senior son de clases distintas y
   se cazan mutuamente (§La división del trabajo).
2. **Puede escalar, pero hay que empujarle.** Dale la vía y un presupuesto
   explícito. Medido: con la herramienta disponible y dos escalados en el
   bolsillo, **no la usó ninguna de las dos veces** — ni atascado ni tras un
   aviso. No se reconoce atascado, solo ocupado.
3. **Tiene una fecha de entrega.** Sin límite explícito, verifica hasta agotar
   el presupuesto sin entregar nada. Ver §No sabe parar.

## La división del trabajo (por qué la revisión no es burocracia)

Esto es lo más valioso que salió de las mediciones, porque no es opinión:

| | junior local | senior de pago |
|---|---|---|
| Existencia y firma de un símbolo | **fiable** — 100% de citas exactas | fiable |
| Localizar un bug de **patrón local** | **fiable** — 5/5 en una auditoría real | fiable |
| Acertar la **consecuencia en runtime** de lo que acaba de encontrar | **falla** | lo caza |
| Bug que exige **cruzar dos sitios** | **solo si le nombras el ángulo** | lo caza solo |
| Resistir un hallazgo falso del otro | **lo rechaza con evidencia** | — |

Las filas 2, 3 y 4 salen de la misma corrida y conviene leerlas juntas, porque
describen un perfil muy concreto: **encuentra el hecho y se equivoca en lo que
significa.** Auditando un addon de Blender de 9.000 líneas entregó 5 hallazgos
con las 5 citas exactas y verificables, 3 con su consecuencia bien razonada, y
**2 con una consecuencia que no ocurre** (§La consecuencia inventada). En la
misma corrida leyó el tramo que contenía un bug conocido de índices —el escritor
indexa por *loop* y el lector por *vértice*— y **no lo vio**: no está en una
línea, está en la relación entre dos.

**La fila 4 tiene truco, y es la más accionable de la tabla.** En una segunda
pasada sobre el mismo repo, con el ángulo escrito explícitamente en el encargo
(«dos sitios que tienen que estar de acuerdo y no lo están; cita las dos
líneas»), encontró uno de clase BLOCKER que nadie había visto: un exportador que
escribe un contador como float y un importador que lo trunca, con el fichero
resultante ilegible para su propio importador. Mismo modelo, mismo arnés, mismo
repo — cambió que se le nombrara el ángulo. **No es que no pueda razonar entre
dos sitios: es que no se le ocurre buscarlo.** Nombrar los ángulos es trabajo del
encargo, y es barato.

El caso real: el junior escribió `super.OnDebugSpawn()` habiendo verificado
correctamente la firma de todo lo que usaba. Lo que no hizo fue preguntarse qué
ejecuta la clase padre — que ya acopla un cargador y deja el slot ocupado, así
que su propia línea siguiente falla. El senior lo cazó en 8 turnos por $0,06,
citando el comentario del propio vanilla que documenta la trampa.

Y en la dirección contraria: al junior se le inyectó un hallazgo **falso** junto
a uno verdadero. Aplicó el verdadero y **rechazó el falso** citando la firma
real. No acata por autoridad; comprueba.

Por eso el bucle funciona: **cada uno verifica aquello en lo que el otro falla.**

## El reparto más productivo que ha salido: él localiza, tú mides

Es la forma concreta de la tabla de arriba, y encontró **tres agujeros de seguridad
reales** en un proyecto cuya suite de 1900 tests estaba verde sobre los tres.

El problema de partida: *"busca reglas que el código promete y ningún test defiende"*.
El local no puede ejecutar tests, así que no puede contestarlo solo. Y **"no encontré
un test" no es evidencia**: un test puede cubrir una regla sin nombrar el símbolo.

El reparto que sí funciona:

1. **Él localiza** un comentario **normativo** (no descriptivo) y enuncia la regla en
   una frase. Distinción que hay que darle explícitamente, porque es la que decide si
   el barrido sirve:
   - descriptivo, ignóralo: `# builds the response dict`
   - normativo, esto es lo que buscas: `# Caller holds self._lock`, `# never 0: 0 is
     reserved for "unknown"`, `# so that its enqueuer's /await resolves`
   Pistas de lenguaje: *must, never, always, cannot, only, otherwise, so that,
   guarantee, deliberately, on purpose* — y cualquier comentario que explique **por
   qué** algo está escrito de una forma concreta.
2. **Él propone la mutación mínima** que rompería la regla, en un bloque fijo:
   `fichero / línea / de / a / rompe / espero`.
3. **Tú la ejecutas** contra la suite y miras si algo se pone rojo.

**Una mutación que deja la suite verde ES la definición operativa de invariante sin
gate.** No hay que creerle nada.

Exigencias que hacen la mutación medible, y sin las cuales pierdes la corrida:

- **mínima**: invertir una condición, quitar una línea. No reescribir una función.
- **que rompa la regla, no la sintaxis**: un `SyntaxError` pone todo rojo y no mide nada.
- **plausible**: parecida al despiste de alguien editando ahí, no a un sabotaje.
- **con contexto único**: en una corrida de 20 mutaciones, **8 no se pudieron aplicar**
  porque la línea propuesta aparecía 2, 6, 8 o 15 veces en el fichero. Pídele contexto
  suficiente para que el ancla sea única, y trata los no aplicables como **sin medir**,
  nunca como defendidos.

Y dos lecturas del resultado que no son obvias:

- **"sobrevive" no siempre es un agujero.** Una guarda puede sobrevivir porque el estado
  que protege **es inalcanzable** — en el caso real, el ingreso ya rechazaba antes con un
  409. Eso es defensa en profundidad, no código muerto: documéntalo en el propio código
  para que nadie lo borre, y no escribas un test que fabrique un estado que el sistema no
  produce.
- **el detector barato**: si una función aparece en la suite **solo como punto de
  inyección** (`obj.metodo = doble`) y nunca como sujeto de una aserción, su
  comportamiento no lo comprueba nadie. Fue exactamente el caso de las dos primeras.

`scripts/run_mutations.py` implementa el bucle (aplica, corre, restaura, repite).
**Restaura bytes, no texto**: `write_text` normaliza CRLF→LF y "deshacer" un cambio
reescribiendo todos los finales de línea de un fichero es un estropicio silencioso en
cualquier repo con `.gitattributes`.

⚠ El bucle necesita la máquina para él solo: si corres otra suite en paralelo, su línea
base se cae por *flake* de carga y aborta la corrida entera.

## Configuración que no es opcional

> **Antes de cambiar de modelo, ajusta la ventana.** Medido 2026-08-21 dentro de
> Claude Code, misma tarea y una sola variable: `qwen3.8:27b` con su nativo de
> 262k tarda **5,8 min al 43% de GPU**; el mismo modelo con la ventana fijada a
> 65k tarda **1,5 min al 100% de GPU**. **3,9× por una línea de Modelfile**, más
> de lo que dio cambiar de modelo (Ornith: 2,4 min, 81%). Entrar entero en GPU
> gana a tener ventana grande. Tabla completa y su reserva en
> [`references/measurements.md`](references/measurements.md).

**`num_ctx` decide si el modelo es usable.** El servidor de Ollama de este host
arranca con `OLLAMA_CONTEXT_LENGTH=262144`. Con ese contexto un modelo de 27B
pide 27 GB, no cabe en una 3090 de 24 GB, y Ollama tira **el 57% a CPU**:

| num_ctx | tok/s | dónde corre |
|---|---|---|
| 262.144 (default del host) | **7,7** | 57% CPU / 43% GPU |
| 32.768 | 37,7 | GPU |
| 8.192 | 38,7 | GPU |

**Pasa `num_ctx` en cada llamada** (`options.num_ctx`), no toques la config
global: el ajuste del servidor lo gobierna la GUI de Ollama y vuelve solo.

**Dónde está exactamente el techo** (escalera completa, 2026-08-19, Ollama
0.32.14, `ollama ps` como oráculo — no `nvidia-smi`, que marca "casi lleno" y
sano mientras media red está en RAM):

| num_ctx | processor | capas |
|---|---|---|
| 32.768 / 49.152 / **65.536** | **100% GPU** | 66/66 |
| 98.304 | 19%/81% CPU/GPU | 58/66 |

Los scripts usan **65.536** por defecto, el último peldaño entero en GPU para el
fichero de fábrica. Antes ponían 49.152 por miedo a desbordar en una revisión de
código real; ese miedo tenía un peldaño de margen sin usar.

**Y el techo es del FICHERO, no del harness**, por eso es `--num-ctx` y no una
constante: con un quant más pequeño el peldaño sube. El Unsloth UD-IQ4_XS (13,28
GiB contra 15,65) aguanta **98.304 al 100% GPU con 66/66 capas**, un 50% más de
ventana en la misma tarjeta. Cómo se elige ese fichero, en §Elegir fichero de
quant. La regla al subirlo es siempre la misma: sube solo hasta donde `ollama ps`
siga diciendo `100% GPU`, porque derramar capas a CPU cuesta mucho más de lo que
vale el contexto extra.

**El segundo ajuste que tampoco es opcional: `draft_num_predict = 2`.** Enciende
el decodificado especulativo con la cabeza MTP que ya viene dentro del GGUF. El
modelo se publica con **4**, y en una tarjeta de 24 GB el óptimo es 2:

| draft_num_predict | acceptance | tok/s |
|---|---|---|
| 0 (apagado) | — | 29,19 |
| 4 (el de fábrica) | 0,468 | 34,61 |
| **2** | **0,669** | **39,82** |

Es **+15% sobre el default y +36% sobre apagado, gratis**, y ningún script lo
pasaba: heredaban el 4 del modelo. Ahora va en `options` de cada llamada, igual
que `num_ctx`. Antes de adoptar un flag de especulación en otro modelo, lee el
`draft acceptance` del log (`%LOCALAPPDATA%\Ollama\server.log`), no el tok/s de
una tirada corta: en `qwen3.5:27b` el mismo flag **resta** porque su cabeza
acepta el 13-24%.

**El tercer ajuste, y el que decide si la delegación entrega o no: `think: false`.**
El modelo razona en voz alta por defecto, y en un loop de herramientas ese canal se paga
en cada turno sin que nadie lo lea. Medido en este host, misma pregunta:

| `think` | tokens generados | reloj |
|---|---|---|
| por defecto (on) | 329 | 7,1 s |
| `false` | **73** | **2,2 s** |

El contenido de la respuesta fue equivalente. En una tarea real la diferencia deja de ser
un porcentaje: un encargo de tres defectos con el canal abierto estuvo **1h40 sin entregar
nada** —seguía razonando, turno tras turno— y el mismo encargo con `think: false` entregó
en **5,3 minutos**, con 35 verificaciones contra el árbol. Si una corrida parece colgada,
mira esto antes que nada.

Por qué se puede apagar sin perder: el puesto del local es **verificar y citar**, y eso lo
hace con las herramientas, no pensando. Y el modo de fallo que el razonamiento sí
arreglaría —la consecuencia mal calibrada (§La consecuencia inventada)— no es el que
tiene: falla igual con el canal abierto, porque no le falta deliberación, le falta aplicar
una regla que ya conoce.

**Y una salvaguarda que va con él: `num_predict`.** Sin techo, una sola respuesta se fue a
**16.000 tokens y seguía generando**, quemando el reloj sin entregar. 9.000-14.000 cubre un
informe con varios parches y sus tests. Una respuesta truncada en el tope se recupera
pidiendo el trozo que falta; una que no termina, no.

```json
"options": {"num_ctx": 65536, "draft_num_predict": 2, "num_predict": 12000},
"think": false
```

(`think` va en la raíz del cuerpo de `/api/chat`, no dentro de `options`.)

**Para uso interactivo, cuece los dos ajustes en una etiqueta** y olvídate de
recordarlos. `ollama run qwen3.8:27b` a pelo carga 27 GB al 57% en CPU:

```
curl -s -X POST http://127.0.0.1:11434/api/create -H "Content-Type: application/json" ^
  -d "{\"model\":\"qwen3.8:65k\",\"from\":\"qwen3.8:27b\",\"parameters\":{\"num_ctx\":65536,\"draft_num_predict\":2},\"stream\":false}"
```

Mismos pesos (comparte blobs, 0 bytes de disco), y a partir de ahí
`ollama run qwen3.8:65k` carga 17 GB · 100% GPU. El único compromiso es el que
dice el nombre: 65.536 de contexto máximo en vez de 262.144.

## Elegir fichero de quant: mide TU eje, no el del anuncio

Salen con regularidad quants "calibrados" de terceros para el mismo modelo, con
titulares del tipo "coincide con el modelo completo un 95,39% de las veces frente
al 94,73% del otro" o "10% mas de precision en KLD". Se probaron cuatro ficheros
contra el que sirve Ollama y el resultado reparte: **dos no aportan nada, uno
empeora, y uno es una mejora clara**. Lo que decide no es quien publica, es que
eje mires.

| fichero | tamano | max `num_ctx` 100% GPU | APIs inventadas (8 tareas) |
|---|---|---|---|
| Ollama `qwen3.8:27b` | 15,65 GiB | 65.536 | 20/85 |
| AtomicChat AD-Q4_K_M | 15,94 GiB | **49.152** (peor) | 23/78 |
| AtomicChat AD-IQ4_XS | 15,38 GiB | 65.536 (igual) | 15/89 |
| Unsloth UD-Q4_K_M | 15,33 GiB | 65.536 (igual) | 28/86 |
| **Unsloth UD-IQ4_XS** | **13,28 GiB** | **98.304 (+50%)** | 17/65 |

**El eje que decide en 10 minutos es el contexto**, porque es determinista y lo
lee `ollama ps`: o carga 66/66 capas o no. Los 2,4 GB que ahorra el UD-IQ4_XS
compran un peldano entero de ventana; los 0,3 GB del AD-IQ4_XS no compraban
ninguno, y AD-Q4_K_M **perdia** uno por pesar 310 MB de mas. Nada de eso aparece
en el titular de nadie, porque el titular mide acuerdo de token contra el BF16 y
tu limitacion es cuanta VRAM te deja libre el escritorio.

**Cuatro reglas que salieron de hacerlo:**

1. **Mide contra el fichero que TU corres.** Las comparaciones publicadas eran
   Unsloth contra AtomicChat; el de Ollama es un tercer publicador que no estaba
   en ninguna de las dos.
2. **Empieza por el eje determinista** (`num_ctx` maximo al 100% GPU). Decide en
   10 minutos; calidad y velocidad necesitan un diseno entero y a veces no
   resuelven nada.
3. **KLD y "% de acuerdo de token" no son tu tarea.** Miden divergencia de
   distribucion. Un 10% mejor en KLD no es un 10% mejor verificando `path:line`.
4. **Comprueba que la cabeza MTP sigue dentro, y sale gratis**: la cabecera GGUF
   esta al principio del fichero, asi que `curl -r 0-50000000` trae los tipos por
   tensor sin bajar 16 GB. Busca tensores `nextn`. Que el repo publique un
   `mtp-*.gguf` aparte no significa que la hayan sacado del principal: en Unsloth
   estan las dos cosas.

**Cuidado con la media en la sonda de calidad.** El 28/86 de Unsloth UD-Q4_K_M
son 19 inventados en UNA tarea (se invento una API entera de JSON y de ficheros);
sin ella queda en 9/66, el mejor de los cinco. Mira la distribucion por tarea,
nunca el agregado.

**Lo que los tipos por tensor revelan y la etiqueta esconde**: AtomicChat decide
**por tipo de tensor** (los 17 `attn_k` a Q8_0 en bloque, pagado bajando
`token_embd` a IQ4_XS); Unsloth decide **por capa** (los mismos `attn_k`
repartidos entre Q4_K, Q5_K, Q6_K y Q8_0 segun la capa, sin tocar `token_embd`).
Eso es lo que significa "Dynamic". Y `ollama show` no sirve de oraculo: etiqueta
`Q8_0` los dos ficheros de AtomicChat porque lee `general.file_type` del GGUF.

**Resultado adoptado**: `qwen3.8:98k` = Unsloth UD-IQ4_XS con `num_ctx` 98304 y
`draft_num_predict` 2 cocidos. MTP vivo (`draft-mtp`, acceptance 0,895 contra
0,874 del de fabrica) y 14,1 GiB de VRAM contra 16,3. Salvedad honesta: escribe
mas escueto (65 simbolos contra 85 en las mismas 8 tareas), y "menos codigo"
tambien puede ser "solucion menos completa", que la sonda no mide.

## El harness es el núcleo, no el modelo

Es el hallazgo que más cambia el resultado, y es barato de reproducir:

- **Sin herramientas**, ante una API que no recordaba, el modelo escribió
  `vector GetBoneTransform(string boneName)` con la nota "I'm confident this is
  a real method". La firma real toma un `int` y devuelve por parámetro `out`.
- **Con `grep` y `read` sobre el árbol**, misma familia de tarea: 45
  verificaciones, tabla de APIs con `path:línea`, y **dos entradas marcadas
  explícitamente `NO VERIFICADO`** con su motivo. Ninguna cita falló al
  comprobarla.

No cambió el modelo. Cambió que pudiera mirar.

**Corolario para el builder**: si te encuentras escribiendo en el prompt la
firma de la API para que no la invente, estás resolviendo el problema por el
lado caro. Dale la herramienta y la regla de citar; el resto sale solo.

### Formas de darle herramientas, y cuánto contexto cuesta cada una

`scripts/junior_agent.py` es la propia, mínima y controlada. Pero hay dos más, y
una es gratis porque ya la usas todos los días:

- **Claude Code apuntado a Ollama** — `ollama launch claude`, o a mano con
  `ANTHROPIC_BASE_URL=http://localhost:11434`, `ANTHROPIC_AUTH_TOKEN=ollama`,
  `ANTHROPIC_API_KEY=""` y `claude --model <modelo>`. Hereda el mejor tool-loop
  que tienes. **Medido 2026-08-21: el protocolo de herramientas aguanta** —
  `qwen3.8:27b` emitió un `tool_use` de `Read` bien formado y respondió correcto
  a la primera.
- **Qwen Code** — `qwen -p` headless, con `--output-format json` y techos
  (`--max-session-turns` sale con código 53, `--max-tool-calls` con 55), que es
  lo que permite a un script de fuera saber **por qué** murió una corrida.

- **prime-agent** — `PrimeIntellect-ai/prime-agent`, redistribución rebrandeada de
  `earendil-works/pi` con una capa propia de horizonte largo (memoria persistente
  refinable y presupuestos de turnos/tokens/tiempo, que upstream no tiene).
  Config local por `~/.prime/agent/models.json` apuntando al endpoint
  **OpenAI-compatible**, así que Ollama **y vLLM** entran sin proxy.

> **El hallazgo que más se transfiere: la superficie de herramientas ES el suelo
> de contexto.** Misma tarea trivial, mismo modelo (`qwen3.8:65k`), una sola
> variable:
>
> | harness | input tokens | duración | respuesta |
> |---|---|---|---|
> | Claude Code, config aislada | 47.603 | **5,8 min** | correcta |
> | **prime-agent** (una sola tool: un REPL de IPython) | **14.306** | 7,2 min | correcta |
>
> **3,3× menos**, y no es magia: Claude Code declara Read, Write, Edit, Bash,
> Glob, Grep, Task, WebFetch… y cada esquema ocupa system prompt. Un REPL donde
> las herramientas son funciones de Python paga un solo esquema. Sobre una ventana
> de 65k eso es la diferencia entre ~17k y ~50k libres para trabajo real:
> **triplica el presupuesto en la misma tarjeta**. Si vas justo de ventana, mira
> primero cuántas herramientas declara tu harness, no qué modelo usas.
>
> Reservas: una corrida, tarea trivial, y el reloj no es comparable del todo
> (prime-agent corría en WSL cruzando a la IP del host para hablar con Ollama).
> Los tokens sí son estructurales.

**La regla que hace que Claude Code sea viable: el worker no carga el aparato
del orquestador.** Misma tarea trivial, mismo modelo: con tu configuración
completa son **341.518 tokens** de entrada y 29,6 minutos; con
`CLAUDE_CONFIG_DIR` a un directorio vacío y
`--strict-mcp-config --mcp-config '{"mcpServers":{}}'`, son **47.603** y 5,8
minutos. **El 86% era CLAUDE.md, hooks, skills, plugins y MCP.** Y no es solo
coste: con la config completa un stop hook llegó a **sustituir la respuesta a la
tarea** por su respuesta al hook en el JSON de salida. Un worker quiere el
tool-loop, no tu doctrina.

Quedan ~47,6k de suelo irreducible (system prompt y definiciones de herramientas),
que ya son el 73% de una ventana de 65k. Presupuéstalo antes de elegir modelo.

### El gate de firmas para Enforce ya existe

`10_Projects/LocalVerifier/tools/enforce-index/enforce_index.py` en el vault.
Universal Ctags con el parser de C# forzado sobre los `.c`, más dos
sustituciones **de longitud constante** que hay que hacer o el índice sale mal:
`extends` → `:` y `modded class` → `class`. Sin ellas el parser toma el último
identificador como nombre de clase y **toda clase con herencia queda indexada
con el nombre de su padre** (`EntityAI` → `Entity`).

Indexa `P:\scripts` entero —53.065 símbolos, incluidas las 3.612 `proto native`
con firma exacta— en **23 segundos**, así que se puede reconstruir en cada
corrida. Devuelve `path`, línea, `kind`, `scope` y `signature`, y re-verifica
abriendo el fichero original en esa línea.

Probado contra la confabulación de arriba: `GetBoneTransform` → **0 resultados,
rechazado**; y el índice devuelve la real,
`GetBoneTransformWS(int pivot, out vector transform[4])` en `object.c:254`.

### Pídele la línea literal, y dile que la vas a diferenciar

Es la técnica de prompt con mejor relación resultado/esfuerzo que ha salido de
las mediciones, y cuesta tres líneas en el encargo. En el formato de salida,
además del `fichero:linea`, exige un campo **línea literal** con instrucción
explícita: *«copia y pega la línea EXACTA que te devolvió la herramienta; quien
reciba esto va a comparar ese texto contra el fichero en disco, y si no coincide
el hallazgo cae»*.

Por qué funciona: convierte una afirmación en algo **falsable mecánicamente**.
Ya no hace falta creerle ni releer el fichero entero — un script compara el texto
citado con esa línea y devuelve un veredicto. Y el modelo lo sabe mientras
escribe, que es cuando importa.

Medido en una auditoría real (9.000 líneas de Python, 34 llamadas): **5 de 5
citas exactas, en la línea exacta, cero fabricadas**. Es el mismo modelo que sin
esta regla se inventaba `path:line` y el cuerpo del código para respaldar un
veredicto.

El gate del receptor no es opcional y no es caro: por cada cita, lee la línea y
compárala normalizando espacios. Que los veredictos sean graduados ahorra
discusiones — «desfase de 2 líneas» y «este texto no existe en el repositorio»
no son el mismo problema, y solo uno invalida el informe:

```
OK / OK_OFFSET (±5 lineas) / OK_ELSEWHERE / WRONG_FILE / FABRICATED / BAD_RANGE / NO_FILE
```

Lo implementa `scripts/verify_citations.py`, y sale con código 1 si alguna cita
no resiste, para que sirva de gate y no de lectura. Está probado por mutación,
que es lo que hay que hacerle a cualquier gate antes de fiarse: con el informe
intacto pasa, con una línea fabricada falla, con el fichero cambiado falla, y con
un número de línea imposible **pasa si el texto está en el fichero** (ancla mala
sobre código real) y **falla si no está**. Esa última distinción no estaba: la
primera versión daba verde a una cita a la línea 99446 de un fichero de 973, y la
encontró la mutación, no la lectura.

Añade también un `## Sin mirar` obligatorio al final del informe. Lo entregó
honesto y con líneas concretas ya localizadas, y eso **sembró la segunda pasada
sin trabajo del orquestador**: saber dónde NO ha mirado vale casi tanto como lo
que encontró.

### Hasta dónde llega esto: un backtest contra un hallazgo real

Se le dio, sin pistas, el mismo código que un frontier había revisado en una
sesión pasada: un cruce de ejes pitch↔roll en la lectura de velocidad angular
de un helicóptero. Ese defecto **lo escribió Codex, no lo vio su autor, no lo vi
yo en la pre-review**, y lo encontró Grok por **$2,23** en 23 turnos.

El modelo local lo encontró, con cadena de evidencia propia y verificable, por
**$0**. Y llegó por una vía más corta que el arbitraje original (un comentario
del propio mod que fija el marco de ejes, en vez de derivar la geometría).

Con tres reservas que definen el puesto exactamente:

- **Calibró mal la severidad**: BLOCKER donde el arbitraje dejó MINOR.
- **El fix quedó incompleto**: acertó la permutación, no los signos — aunque lo
  declaró como no verificado, igual que había hecho el frontier.
- **La primera corrida devolvió SOUND.** El hallazgo apareció al arreglar la
  poda de ventana y subir `num_ctx`. Mismo modelo, mismo encargo, mismo código:
  **lo decidió el harness.** Si te devuelve "no encuentro nada", sospecha de tu
  ventana antes que de su capacidad.

`scripts/junior_agent.py` implementa ese loop (grep + read acotados a un árbol,
con guard de path). Cambia la constante `VANILLA` para apuntarlo a otro
proyecto.

## Sin fuentes deriva hacia lo genérico

Preguntado sin acceso a nada por qué es "cite-then-verify", el local devolvió
una respuesta coherente y bien escrita sobre verificar contratos de API en
runtime con tests de integración. Plausible, y **no es el patrón**. El senior
que la juzgó lo dijo así: "no es inútil, está desviada hacia contract-testing".

Es el modo de fallo peligroso, porque el resultado *parece* bueno. Si la tarea
no tiene fuentes que consultar, o no la mandes, o asume que necesitará revisión
de contenido y no solo de forma.

## Modos de fallo medidos

### La consecuencia inventada sobre un hecho verdadero

El más peligroso de todos, porque la parte verificable del hallazgo está bien y
eso te invita a aceptar el resto. Encuentra el hecho, lo cita exacto, y luego
**deduce mal qué pasa en ejecución**.

Caso medido: reportó, con la línea correcta, que un `open()` sin `close()` en un
camino de `return` «fuga el descriptor, bloquea el `.p3d` en Windows hasta
reiniciar y acumula un handle por cada import fallido». En CPython nada de eso
ocurre: al retornar la función, la variable local pierde su última referencia, el
contador llega a cero y el fichero se cierra ahí mismo. El hecho era cierto —
falta el `with`— y **la consecuencia era ficción**. Dos de cinco hallazgos de esa
corrida tenían el mismo defecto.

Es exactamente el eje de la tabla de división del trabajo: **verifica bien, razona
mal**. Y no lo arregla darle más contexto, porque no le falta información: le
falta aplicar una regla del lenguaje que sí conoce si se la preguntas suelta.

**Mitigación, y es barata: separa los dos veredictos en el formato de salida.**

```
- **hecho**: que dice el codigo, sin interpretarlo
- **consecuencia**: que pasa en ejecucion Y la regla del lenguaje que lo produce
- **confianza hecho**: VERIFICADO | NO VERIFICADO
- **confianza consecuencia**: RAZONADA (explico la regla) | SOSPECHA (no la justifico)
```

Pedir la **regla que produce la consecuencia** es lo que muerde: obliga a pasar
de «esto se fuga» a «esto se fuga *porque* la referencia sobrevive en X». Cuando
no hay regla que citar, el hallazgo se degrada solo a ESTILO en vez de colarse
como MAYOR. Y dile explícitamente que un hallazgo con hecho VERIFICADO y
consecuencia SOSPECHA es un buen hallazgo — si no, aparenta seguridad.

Relacionado: la severidad la calibra alta. En esa corrida etiquetó 4 de 5 como
MAYOR, incluidos los dos cuya consecuencia no ocurre.

### No sabe parar

Misma tarea, dos corridas, temperatura 0.1:

| | llamadas | tiempo | resultado |
|---|---|---|---|
| corrida A | 12 | 50 s | entregó, correcto |
| corrida B | **50** | ~15 min | **no entregó nada** |

En la corrida B tenía la respuesta hacia la llamada 15 y siguió 35 más,
alejándose del problema (de `SpawnAttachedMagazine` a `MagazineStorage`, a
`ak101.c`, a `FillSpecificChamber`). El disparador fue la parte ambigua del
requisito: sin criterio de "ya está", no cierra.

**Mitigación, ya implementada en `junior_agent.py`:**
- Aviso de presupuesto al 60% de los pasos: *"deja de explorar; si te falta UN
  dato usa `ask_senior` ahora, si no entrega con lo que tienes y declara el
  hueco. Entregar con un hueco declarado es correcto; no entregar es un fallo."*
- **Cierre forzado**: al agotar los pasos, una última llamada con las
  herramientas retiradas. Perder el trabajo porque no supo parar es el peor
  resultado disponible; peor que una respuesta con un hueco declarado.

### La varianza es el riesgo, no la calidad media

4× de diferencia en esfuerzo entre dos corridas idénticas. No diseñes el flujo
suponiendo que "normalmente va bien": diséñalo para que la corrida mala también
termine. Si necesitas fiabilidad en una tarea concreta, lánzala dos veces y
compara — sigue costando cero.

### No escala aunque pueda

0 de 2 con la herramienta disponible y presupuesto anunciado. Si el escalado
importa, **dispáralo desde el harness** (p. ej. detectar N búsquedas fallidas
del mismo símbolo y forzar la consulta), no confíes en su criterio.

## La matriz de llamadas entre agentes

Cuatro direcciones. Las invocaciones aquí están verificadas por ejecución.

### senior → local (descargar trabajo mecánico)

El senior invoca `scripts/ask_qwen.py` por shell. No necesita saber nada de
Ollama ni de puertos:

```
C:\Python314\python.exe <ruta>\ask_qwen.py --caller grok --prompt "..."
```

Con `--with-tools` el local responde a través del loop de verificación; sin él,
responde de memoria (vale para prosa, no para código).

**Grok**: necesita el shell en el allowlist. El tool ID es **`run_terminal_cmd`**
— sus propias docs lo llaman `run_terminal_command` en cuatro páginas y ese
nombre **no existe**. Verificado funcionando:

```
grok.exe --prompt-file <brief> --cwd <ws> \
  --tools "read_file,grep,list_dir,run_terminal_cmd" \
  --deny "MCPTool" --output-format json --max-turns 20 \
  --always-approve --no-memory
```

Coste medido de una sonda así: **$0,009 / 2 turnos**. Y corrige un límite que se
daba por del modelo: *Grok sí ejecuta* — lo que no ejecuta es lo que el
allowlist no le deja.

**Codex**: mismo puente, `-s workspace-write` para que pueda lanzarlo. No
verificado por ejecución (sin cuota el día de la medición).

### local → senior (escalar cuando se atasca)

Herramienta `ask_senior(question, what_you_tried)` en `junior_agent.py`. Abre
una sesión de juicio **read-only** del senior con la pregunta acotada. El
presupuesto se impone en el harness (`--max-escalations`), no en el prompt: cada
consulta gasta cuota del usuario y esa decisión no se delega en el modelo.

Pedirle `what_you_tried` no es burocracia: es lo que convierte "¿cómo hago X?"
en una pregunta que el senior puede responder sin repetir el trabajo.

## El bucle de revisión

`scripts/review_loop.py` alterna local ↔ senior **sin consumir tokens del
orquestador**, que es lo que hace que el ahorro sea real.

- Ronda 1 abre sesión del senior; las siguientes usan **`-r <sessionId>`**, que
  lee el contexto de caché y cuesta ~12% de la primera. Guarda el `sessionId`.
- Veredicto en JSON (`GREEN` / `CHANGES_REQUIRED`) para que el bucle decida solo.
- Al corregir, el local vuelve a entrar **con las herramientas puestas** y con
  instrucción explícita de rechazar hallazgos falsos citando el árbol. Sin eso,
  el bucle propaga los errores del senior con la autoridad del senior.
- Ledger con el coste de cada ronda. Sin él no puedes responder si compensa.

**Coste medido del ciclo completo** (generar + revisar, un archivo Enforce):
**$0,127**. Una pasada de revisión sobre un método pequeño: **$0,06**. Para
comparar: una revisión de plan grande del mismo senior cuesta ~$0,43.

**`GREEN` significa "tiene calidad frontier", no "funciona".** Sigue haciendo
falta el gate real del dominio (en DayZ, el test in-game: Enforce no compila
fuera del juego).

## Anti-patrones

1. **Mandarle una tarea sin fuentes y creerte el resultado.** Es el fallo que
   esta skill existe para evitar. Sin herramientas confabula con confianza.
2. **Dejar el `num_ctx` por defecto.** Estarás midiendo una config rota y
   concluyendo que el modelo es lento. Lo mismo con `draft_num_predict`: el 4
   de fábrica deja un 15% en la mesa en una tarjeta de 24 GB.
3. **Aceptar su entrega sin revisión** porque "esta vez se ve bien". Sus fallos
   son de razonamiento sobre efectos: se ven bien por construcción.
4. **Confiar en que escale solo.** No lo hace.
5. **Diseñar el flujo para la corrida buena.** La varianza es 4×.
6. **Darle al senior el shell sin `--deny`.** En este host el permission mode no
   pregunta nada; el allowlist es el único cortafuegos.
7. **Escribirle la firma de la API en el prompt** para que no la invente. Dale
   la herramienta.
8. **Tratar `GREEN` del revisor como "listo para producción"** saltándote el
   gate del dominio.
9. **Cambiar de fichero de quant buscando calidad.** Se midió el caso fuerte y
   no paga; el que sí paga es el harness (§No persigas ficheros de quant).
10. **Reportar una diferencia de tok/s de una sola pasada.** En esta máquina la
    velocidad decae dentro de la propia corrida; por debajo del ~20% no hay
    medida, hay ruido.
11. **Apuntar `--root` a un árbol que el índice no cubre.** El índice trae
    patrones por defecto (`*.c`); sobre un repo de otro lenguaje devolvía cero
    ficheros, cada `grep` contestaba «sin coincidencias», el modelo lo leía como
    un hecho sobre el código y **confabulaba el informe entero**. Ahora
    `junior_agent.py` cuenta lo indexado y **aborta con cero**, pero el hábito
    sigue siendo tuyo: pasa `--ext` y **mira la línea `[index]`** antes de
    aceptar ningún resultado. Un índice vacío no dice «no hay bugs», dice «no
    has buscado».
12. **Aceptar la consecuencia porque la cita es exacta.** Son dos veredictos
    distintos y el segundo falla más (§La consecuencia inventada).
13. **Aceptar un veredicto cuyo alcance es más ancho que su evidencia.** El modo de
    fallo, medido triando un buzón: una entrada agregaba tres incidencias, él citó
    correctamente la evidencia de **una** y dictaminó "RESUELTO" sobre las tres. La cita
    era exacta; la conclusión, no. Cuando un veredicto cierra N cosas, exige N
    evidencias.
14. **Cambiar un comportamiento sin mirar si hay un test que lo defiende.** Dos veces en
    una sesión, un "defecto" reportado resultó ser una **decisión consciente con test**:
    una tool deliberadamente ausente de un README (y el test lo exigía ausente), y un
    error opaco a propósito (el test comprobaba que el mensaje de la excepción NO
    saliera). En uno de los dos se rompió producción antes de darse cuenta. Grep del
    símbolo en los tests **antes** de tocar, no después.
15. **Vender la delegación como ahorro de coste sin contar la del orquestador.** El
    junior es gratis; tú no. En una jornada medida, el 94% del gasto fue contexto y solo
    el 6% output — o sea, la parte que el junior te ahorra (§Lo que el "coste cero" no
    dice).

## Scripts incluidos

| script | para qué |
|---|---|
| `scripts/junior_agent.py` | El loop de verificación + escalado + presupuesto y cierre forzado. `--root` fija el árbol y `--ext` sus patrones (`.py`, `.ts`, …; por defecto `.c`); imprime `[index] N ficheros` y aborta con cero |
| `scripts/ask_qwen.py` | Puente por shell para que un senior delegue en el local |
| `scripts/review_loop.py` | Bucle generar→revisar→corregir con ledger de coste |
| `scripts/verify_citations.py` | El gate del receptor: compara la línea literal de cada hallazgo contra el disco y sale con código 1 si alguna es fabricada |
| `scripts/run_mutations.py` | El otro gate del receptor: aplica cada mutación que el junior propone, corre la suite, restaura (byte a byte) y reporta cuáles sobreviven. Una superviviente es una invariante sin gate |

Los tres son stdlib puro y registran cada llamada en `agent_calls.jsonl`, que es
el scorecard: sin filas medidas, el reparto se decide por impresión.

## Referencias

- `references/measurements.md` — todas las cifras con su procedencia y qué
  quedó sin medir.

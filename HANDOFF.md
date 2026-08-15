# HANDOFF — DayZ Modding Knowledge Pack

<!-- LIVE-STATE:START -->
# DayZ Modding Knowledge Pack — Estado vivo · snapshot 2026-08-15 (backlog de adopción)

**Última verificación real, medida el 2026-08-15:** HEAD `de4fc9a` en
`r21/phase01-foundation`, árbol limpio. **`main` sigue en `f87a59e`** y NO se ha
adelantado: la Fase 02 no está cerrada. Sin remoto.

**El commit es del 2026-07-30: el repo lleva 16 días quieto** mientras las copias
instaladas seguían creciendo. Eso NO es estabilidad; es un backlog (§«Lo primero»).

Gates de hoy: suite **809 passed / 18 skipped / 305 subtests**, `validate` PASS con
cero findings, gate de corpus PASS exit 0 con `5 tracked .layout`, y
`promote --check` en **`FAIL` con 19 findings sobre 10 skills** — eran 2 findings
sobre 1 skill al cerrar julio.

`ciclos_en_este_objetivo: 1 (Backlog de adopción y cierre de Fase 02)`

> **Reiniciado a 1**: «Fase 02 — Tasks 3-5» se cerró y este es otro objetivo.

## Lo primero, antes de cualquier otra cosa

**El repo está 17 ficheros por detrás de las skills instaladas, +67.727 bytes**,
repartidos en 10 skills, más **21 backups del writer** (18 solo en
`dayz-vehicles`). Medido hoy, repo contra destino:

| skill | ficheros | delta |
|---|---:|---:|
| `dayz-vehicles` | 3 | **+41.220** |
| `dayz-aviation` | 2 | +10.874 |
| `dayz-test-ingame` | 2 | +8.554 |
| `dayz-basebuilding` | 1 | +4.422 |
| `dayz-mcp-verify` | 2 | +3.684 |
| `dayz-weapons` | 1 | +3.650 |
| `dayz-characters` | 2 | +2.781 |
| `_shared` | 1 | +2.207 |
| `rigorous-data-audit` | 1 | +1.395 |
| `rip-vehicle-import` | 2 | **−11.060** |

**`rip-vehicle-import` tiene delta NEGATIVO y no se adopta: se fusiona.** Un delta
negativo significa que o se quitó contenido, o el repo va por delante en parte del
fichero. Es exactamente lo que le pasó a `rigorous-data-audit` el 30 de julio, y
copiar encima habría borrado conocimiento verificado. Compara sección por sección
antes de escribir nada.

## Las dos reglas de adopción que costó descubrir

1. **NO adoptes payloads ejecutables** (`.py`, `.ps1`, `.bat`, `.cmd`). La
   promoción los **localiza** por diseño (`decision-log` 2026-07-26): sustituye
   `<dayz-projects>` por la ruta real de la máquina. Su diferencia con el repo suele
   ser **solo** esa sustitución —cero conocimiento— y adoptarlos mete una ruta
   privada en la fuente distribuible. La compuerta de privacidad lo caza, pero el
   arreglo es descartarlos, no despersonalizarlos.
2. **Un borrado en el diff exige merge, no copia.** Verifica grepeando la copia
   instalada por varias cadenas distintas de la sección que desaparecería. Si no
   están, el repo va por delante ahí y hay que fusionar partiendo del repo.

## Lo que cerró la sesión de julio

**`C2` y `C4` en `✓`, y `SC-006` cerrado: 28 de 54.** Quedan `C3`, `C6`, `C7` y
`C8` de la Fase 02. **Tasks 3, 4 y 5 del plan están cerradas**; de la Task 4 falta
el tramo raster/assets y de la Task 5 solo el gate de Sorter V4 (ver abajo).

## Bundle entregado al experto gráfico (2026-07-30)

`C:\Users\guill\DayZ-Knowledge-Bundle-20260730.zip` — 14,1 MB, 2.124 ficheros,
interno y no publicable. Pack completo + 6 skills propias fuera del pack + capa de
conocimiento del vault + `ROUTING-TABLE.md` con los 21 front-matters, que es el
formato de ingesta que prescribe el `README.md` §2 del propio pack. Diez chequeos
de verificación pasados.

**Está 16 días desactualizado.** Si hay que reenviarlo, adopta el backlog primero y
reconstruye; los scripts vivían en el scratchpad de aquella sesión y se han
perdido, pero el procedimiento está en
`30_Sessions/2026-08-15-DayZ-Modding-Knowledge-Pack-bundle-y-backlog-de-adopcion.md`.

El núcleo del pipeline 3D (`dayz-model-pipeline`, `dayz-texture-pipeline`,
`dayz-p3d-*`, `uv-clean-atlas`, `blender-assembly`, `enforce-script-reference`) es
del plugin `anthropic-skills` y **no es redistribuible**: el bundle lleva punteros
e instrucciones de instalación, no los bytes.

- **Task 3 / `C2`** — contrato `dayz-ui-scenario-v1` (schema + validador stdlib
  fail-closed + compositor). Medido sobre el árbol: los tres ids son idénticos a
  1920×1080 y 3440×1440 con `sibling_index` `0,1,2`, y la geometría **sí** cambia
  (ancho de card `497.664` → `891.648`). Esa segunda aserción es la que impide
  que pase una implementación que ignore el viewport. Seis fixtures negativos,
  exit 1 con su código exacto.
- **Task 4 / `SC-006`** — contrato `dayz-ui-render-v1`. `render.json`
  byte-idéntico entre **dos procesos del SO con cwd distinto**. Conserva
  literalmente los `id` del compositor, comprobado nodo a nodo: ese es el puente
  para que la Task 6 compare captura de engine contra composición sin traducir.
- **Task 5 / `C4`** — diff estructural + cinco overlays de defecto. La fixture
  negativa da **exactamente cuatro** hallazgos y el control positivo **cero**,
  medido. Empareja por `id`: invertir la lista de widgets da cero hallazgos. Cada
  detector tiene caso rojo **y** verde.
- **`BUG-023` cerrado** (`35943a3`) — la comparación estructural rechaza dos
  renders con viewports distintos (`DIFF-VIEWPORT-MISMATCH`) en vez de emitir 86
  cambios de geometría que son aritmética de resolución. **`analyze_document` NO
  se tocó a propósito**: analizar un render a un viewport que el escenario no
  declara es válido y `SC-005` lo exige; un `DIFF-OVERFLOW` que solo aparece a
  3440×1440 es un defecto responsive real, no un artefacto. La primera redacción
  del bug decía lo contrario y se corrigió al medirlo — el detalle está en el
  `bug-ledger.md`, con el error visible.
- **El escape inválido de `:91-92`** — cerrado el tercio que faltaba. Verificado
  en los dos sentidos: los subtests nuevos fallan contra el `parse.py` anterior y
  pasan contra el actual.

**`C3` NO cierra**, y no es por falta de trabajo: exige además `SC-007` (raster)
y `SC-008` (assets), y los dos siguen bloqueados por sus `ASSUMED`. Ver §Raster.

## Qué hacer a continuación

1. **Adopta el backlog de 17 ficheros** (§«Lo primero»), con las dos reglas de
   arriba: sin payloads ejecutables, y `rip-vehicle-import` por merge. Es lo único que
   protege 67 KB de conocimiento que hoy vive **solo** en el destino — la ventana
   entre escritura y adopción es donde `BUG-019` destruyó contenido.
2. **Re-mide `promote --check`.** Tras adoptar seguirá rojo: el finding mira el
   destino y adoptar cambia el repo. Solo una adjudicación lo explica, y se firma
   con quietud verificada y sin sesión de vehículos viva.
3. **Task 6 (`C6`)** — la sonda funciona y está desplegada en
   `P:\Mods\@LF_UIProbe`; falta el bundle `engine-capture-v1`. Requiere engine, no
   lo mezcles con el bloque offline. El puente ya está tendido: los `id` de widget
   del render son los del compositor y usan la misma derivación que el spec fija
   para `widget-tree.json`.
4. **`SC-008` (assets)** sigue bloqueado por el `ASSUMED` de licencia/procedencia
   del códec PAA/EDDS. El spec prohíbe meter código de códec antes de cerrarlo, así
   que eso es una decisión de licencia, no de implementación.
5. **El gate de Sorter V4** (último bullet de Task 5) sigue abierto **a propósito**:
   el plan pide «solo los defectos conocidos» y no los enumera en ningún sitio. Un
   gate contra una lista que nadie ha escrito pasa siempre o falla siempre. Enumera
   los defectos primero; eso es una decisión, no implementación.
6. **Promoción pendiente de `skill/rigorous-data-audit`**: las 36 líneas de
   `1312890` nunca llegaron a las raíces (la transacción se firmó sobre `8986bae`).
   Repo-ahead benigno, verificado por hash de blob. Agrúpalo con la promoción de
   Fase 02 para no gastar dos transacciones.

## Raster (`SC-007`): medido a medias, y esa es la respuesta

Spike ejecutado el 2026-07-28 **antes** de implementar el tramo, sobre una fixture
que ejercita el raster de verdad (texto en tres familias, alpha, degradado,
hairline) y con el render inspeccionado visualmente para que un lienzo en blanco
no fabricara un falso hallazgo.

- **Cinco ejecuciones limpias dan PNG y píxeles byte-idénticos**, y desplazar
  locale/timezone/cwd tampoco mueve un byte.
- **No se pudo medir el segundo entorno**: un solo host y **una sola build en
  caché**, así que la variable cabecera de cualquier perfil de raster —la build
  del navegador— no pudo mutarse.
- De seis variables mutadas una a una, **solo `--force-device-scale-factor` mueve
  píxeles**. Un perfil que nombre las otras cinco promete más de lo que entrega.
- **`chrome.exe` 150 ya no honra `--screenshot`** por línea de comandos: arranca y
  se cuelga. El binario que escribe el PNG y termina es `chrome-headless-shell`.
- **`--deterministic-mode` cuelga esa build.** Un perfil que lo nombrara no
  produciría artefacto ninguno.

Por eso el emisor marca `raster=false` y **no implementa raster**: un hueco
implementado se convierte en el perfil de facto sin que nadie lo haya medido.
Detalle en `10_Projects/DayZ_Modding_Knowledge_Pack/assumptions.md`.

## Corpus: montado, fijado y con gate propio

`C1` y `C5` están en **`✓`**. Los tres referentes públicos viven en
**`C:\Users\guill\DayZ-UI-Corpora\`** a los commits del research; TraderX se
extrae de las PBO del Workshop.

```
python tools\dayz-ui-lab\dayz_ui_lab\corpus.py --root .
→ 376/376 layouts, 0 diagnostics, 0 redistribuidos, verdict=PASS, exit 0
```

Cuatro cosas que conviene no romper:

- **Las rutas viven en `sources/local-roots.json`, que NO se rastrea.** Si el
  gate dice `CORPUS-ROOT-MISSING`, falta configurarlo, no está mal el corpus.
- **Un corpus sin raíz configurada FALLA el gate**, no se salta.
- **Nada de terceros entra en Git.** La auditoría compara **por contenido, no por
  ruta**, así que un layout ajeno renombrado también salta.
- **La allowlist de `.layout` tiene ahora DOS rutas nombradas** (la sonda y
  `tools/dayz-ui-lab/fixtures/scenarios`), porque el gate gobierna todos los
  `.layout` del repo y las fixtures de la Task 3 no cabían en ninguna. La
  garantía de C5 no la sostiene esa lista sino la comparación por contenido, que
  no se tocó. Una tercera ubicación sigue fallando, con test propio. **No la
  amplíes otra vez sin decidirlo**: `decision-log.md` §allowlist.

## Lo que te va a morder si no lo lees

1. **El destino muta solo, y ya no es una skill sino DIEZ.** Al cerrar julio el
   gate tenía 2 findings sobre `dayz-vehicles`; el 2026-08-15 tiene **19 sobre 10
   skills**, y `dayz-vehicles` acumula **18 backups del writer**. Esto no es una
   ráfaga: son 16 días de trabajo normal del usuario en otros proyectos, que
   aterriza en las skills instaladas.

   **Re-mide `promote --check` antes de tocar nada.** El ciclo es: adoptar →
   refrescar `output_hash` → `git add` → `validate` → suite → commit → re-medir →
   adjudicar **solo** con quietud verificada y sin sesión de vehículos viva.

   Cuatro cosas que ahorran tiempo: **adoptar NO puede poner verde ese finding**
   —mira el destino, y adoptar cambia el repo—; **la entrada de `dayz-vehicles` en
   el source-map NO espeja el output** (sus tres inputs son ancestría), así que su
   adopción es un cambio de **una línea**, `output_hash` sola; **mira el destino
   antes de sobrescribir**, porque trae backups `*.bak_*` del propio writer que no
   deben entrar en Git; y **el discriminador de qué input refrescar no es la ruta
   sino el hash**: si dos inputs comparten el `output_hash` saliente, el que se
   mueve es `pack-r21-authored` y `pack-baseline` es historia fijada a un commit.

2. **Un mtime viejo tampoco prueba que el fichero sea viejo.** Un `.bak` marcaba
   `20:55` habiéndose creado a las `23:20`: `Copy-Item` preserva el timestamp del
   origen. Es el reverso de la invariante que ya estaba escrita aquí.
3. **No delegues nunca un `--basetemp` relativo ni concatenado.** Una ruta Windows
   con los separadores comidos aterrizó como directorio literal con una ACL que
   negaba `Remove-Item`, `takeown`, `icacls` y `robocopy`, y **rompía la colección
   de `pytest`**. Resuelto; el aviso se queda por la causa.
4. **`B3b` sigue fuera de alcance por decisión del usuario, pero la RAZÓN que
   había escrita aquí era FALSA.** Decía que `--bare` es lo único que esconde las
   skills globales y que la sesión OAuth se niega a leerlo. El spike de
   aislamiento (2026-07-29, CLI `2.1.193`) lo refuta con el `--help` del propio
   binario: `--bare` salta hooks, LSP, plugin sync, atribución, auto-memory,
   prefetches, keychain y descubrimiento de `CLAUDE.md` — y dice, literal,
   «**Skills still resolve via `/skill-name`**». Es decir, **`--bare` nunca
   escondió las skills**, ni siquiera con API key. Y la restricción de auth que se
   creía bloqueante es de `--bare`, no del aislamiento.

   **Dos candidatos que no necesitan API de pago y que nadie había mirado:**
   `--disable-slash-commands`, cuya descripción íntegra es «**Disable all
   skills**», y `--setting-sources <user,project,local>`, que permitiría cargar
   `project`/`local` sin `user` y dejar fuera `~\.claude\skills`.

   **Lo que el spike NO puede decidir**, y por eso no lo decide: si esas flags
   impiden que el **contenido** de la skill llegue al modelo, o solo la invocación
   por `/nombre`. Una skill puede auto-dispararse por descripción sin que nadie
   escriba la barra. Distinguirlo exige una corrida viva con fixture
   discriminante, que es justo `B3b`. **La decisión de reabrir `B3b` es tuya**;
   lo que cambia es que su premisa técnica ya no se sostiene.
5. **El harness de evals vivos tiene un fail-open, y el spike lo acotó.**
   `_skills_tree_sha256` (`live_evals.py:201-211`) hashea `workspace/.claude/skills`,
   un árbol que **crea el propio harness** (`:221-222`) y en el que, para el brazo
   de control, no copia nada (`:223`). Los dos checks
   (`LIVE-EVAL-ARM-CONTAMINATED` en `:446` y `:464`) son reales pero **estrechos**:
   solo cazan contaminación *local al workspace* —una fixture que plante ficheros
   bajo `.claude/skills`, o el runner escribiéndolos durante la corrida—.

   **Medido:** `live_evals.py` no contiene **ni una** referencia a raíces de skills
   globales, a `--bare`, a setting sources ni al home del usuario. El aislamiento
   frente a las skills instaladas está delegado **al 100 %** a la línea de comandos
   del runner (`evals/live/runners/claude-code.py:28-43`), y el runner es
   enchufable: el harness nunca inspecciona, registra ni valida qué mecanismo usó.
   Por eso el finding no puede ponerse rojo para el modo de contaminación que su
   propio nombre promete.

   **Fix recomendado, sin implementar porque cambia un contrato:** que el runner
   declare su mecanismo de aislamiento en la salida y que el harness lo registre y
   falle cerrado si falta. Un veredicto `DISCRIMINATING` sin evidencia de
   aislamiento no debería poder emitirse.
6. **`@DayZ_MCP` no sirve como portador de test.** Su módulo `5_Mission` no
   compila: `CParser: quoted string not closed`, atribuido a
   `DayZ_MCP/scripts/5_Mission/mcpclientbridge.c`. Es del mod del usuario, no del
   pack, y no se ha tocado. Usa **`LFPowerGrid`**, que compila y está verificado.
7. **`Path.write_text` en Windows reescribe los finales de línea** de un repo que
   es LF por `.gitattributes`. Refrescar dos hashes convirtió 11.529 saltos. El
   blob queda bien, el árbol de trabajo no. Escribe con `write_bytes`.

## Método que ahorra sesiones

- **Adoptar tiene dos excepciones que no son opcionales.** Los **payloads
  ejecutables** (`.py`, `.ps1`, `.bat`) no se adoptan: la promoción los localiza y
  su única diferencia con el repo suele ser esa sustitución de ruta. Y un fichero
  con **borrados en el diff** se fusiona, no se copia: verifica grepeando el
  destino por varias cadenas de la sección que desaparecería.
- **Cuando midas bytes, mídelos en bytes.** Un commit entró con BOM en el asunto
  por `Set-Content -Encoding utf8` en PS 5.1, y el chequeo obvio —capturar
  `git log --format=%s` en una variable de PowerShell— decía que estaba limpio,
  porque PowerShell elimina el BOM al decodificar. `git cat-file commit HEAD` lo
  enseñó a la primera.
- **Lee el `--help` del binario antes de escribir en el handoff qué hace una
  flag.** La razón por la que `B3b` estaba cerrado —«`--bare` es lo único que
  esconde las skills»— era falsa, y bastaban treinta segundos de `--help` para
  verlo: esa misma flag dice «Skills still resolve via `/skill-name`». Una
  afirmación heredada sobre una herramienta se verifica igual que una API.
- **Verifica el GATE que gobierna un tipo de fichero antes de fijarle una ruta a
  Codex.** Esta sesión perdió una tanda entera de 36 minutos porque el prompt
  mandaba crear fixtures `.layout` en un sitio y, tres secciones más abajo,
  mantener verde el gate que gobierna **todos** los `.layout` del repo. Codex leyó
  ambas, paró sin escribir un byte y devolvió la contradicción — correctamente—,
  pero el chequeo costaba 30 segundos. Promovido a `codex-handoff-template`
  (`LL-221`).
- **Cuando Codex para y pregunta, verifica su hallazgo contra el código antes de
  aceptarlo, y también antes de rechazarlo.** Las dos veces que paró esta sesión
  tenía razón.
- **Re-ejecuta los gates que Codex declare verdes.** Reportó los dos de pytest
  como `No module named pytest` con el mismo intérprete con el que aquí corre la
  suite entera: era su sandbox, no el árbol. La cifra que vale es la tuya.
- **Para probar una sonda nueva no toques la allow-list sellada del launcher.**
  `extra_mods` acredita un `@Name` relativo bajo `P:\Mods`
  (`dayz_test_worker.py:183-197`) si el directorio es real y no un reparse point.
- **Para extraer layouts de una PBO de terceros: Mikero `ExtractPbo`** (instalado,
  en PATH). `PboViewer.exe` **no descomprime** las entradas `Cprs` y escribe los
  bytes comprimidos sin avisar.
- **`exit 0` de AddonBuilder no dice nada de los bytes.** Verifica la PBO entrada
  por entrada contra el fuente antes de creerte una fixture byte-sensible.
- **Para probar en rojo un cambio de parser sin inventar nada**: corre los tests
  nuevos contra `git show HEAD:<fichero>` en un árbol desechable. Treinta segundos,
  y convierte «pasa» en «pasa y antes no pasaba».

## Invariantes cerradas

- Git es la única fuente editable; las instaladas son despliegues. La adopción va
  del destino al repo, nunca al revés sin gate.
- **Adoptar protege el conocimiento y es barato; adjudicar caduca.**
- Un `mtime` que se mueve **no** prueba trabajo en curso; `git status --porcelain`
  sí. Un fichero commiteado conserva su mtime para siempre.
- Una adjudicación autoriza un digest concreto y **tapa, no arregla**.
- Un gate que no puede ponerse rojo no es un gate — y un gate que rechaza tu
  cambio puede tener razón.
- No declarar un criterio `✓` sin ejecutar su línea de evidencia.
- `validate` sobre ficheros sin rastrear no dice nada: `git add` y DESPUÉS validar.
- **Un mod que no compila pasa cualquier test que afirme sobre su texto.** Los tres
  tests de la sonda eran verdes con un `.c` que el motor rechazaba entero.
- **Una aserción de «no cambia» necesita su pareja «sí cambia».** `SC-005` pide que
  la identidad se conserve entre viewports; sin la aserción de que la geometría
  difiere, una implementación que ignorase la resolución pasaría el criterio.
- **Un gate nuevo se prueba en rojo y en verde**, y un gate que solo se ha visto en
  verde no está verificado.
- **Un repo quieto no es un repo estable** cuando su destino lo escriben otras
  sesiones. Dieciséis días sin tocar el árbol dejaron 17 ficheros de retraso.

**Gate de arranque:** declarar `Retomo DayZ Modding Knowledge Pack desde: de4fc9a
(commit del 2026-07-30, repo 16 días quieto) con Tasks 3-5 cerradas, C2 y C4 en ✓,
28 de 54, y un backlog de adopción de 17 ficheros sobre 10 skills · próxima acción:
adoptar ese backlog, con rip-vehicle-import por merge y sin payloads ejecutables`.
<!-- LIVE-STATE:END -->

---

## Log histórico

### 2026-07-25 — Fase 04 py3d y validación 3D

- Se implementaron y verificaron los cuatro workstreams aprobados.
- Se distribuyen todas las piezas legalmente redistribuibles desde el pack.
- El backend externo ODOL queda excluido por diseño; se fija por hash y se
  prueba desde su checkout local.
- La revisión independiente añadió límites estrictos para float32, números
  enormes, normales de proxy, rutas NUL, mapeos winding ambiguos y fallos I/O
  al preparar el payload temporal del backend.
- El rollout se probó solo sobre copias desechables.

### 2026-07-25 — Fase 02 slices 1–2

- B19 cerró por RED→GREEN y corpus.
- Se añadió `LF_UIProbe` con staging LF/CRLF reproducible.
- B20 quedó bloqueado honestamente por un cliente MCP con clave cacheada
  obsoleta; no hubo bypass.

### 2026-07-24 — Prior art aprobado y promovido

- Se aprobaron tres deltas: API index v2 no bloqueante, build/release
  transaccional y dayz-labs como companion sin autoridad de lifecycle.
- El commit `13af7f8b59962bca6fded981ad75cd77a37616ef` superó el gate integral.

### 2026-07-24 — Fase 01 cerrada

- Se cerraron A1–A9 y B1–B5 con gate reproducible y source map completo.
- La transacción `c7b5366cc761a8038e52f6a2` promovió el commit de contenido
  `7a25432febc112a957a7c1ef7a7d2c16c221b24f` a las tres superficies.

### 2026-07-24 — Bootstrap

- Se fijó el ZIP previo por SHA-256.
- Se extrajeron y verificaron 138 archivos sin diferencias.
- Se inicializó Git y se creó el commit raíz exacto.

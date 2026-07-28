# HANDOFF — DayZ Modding Knowledge Pack

<!-- LIVE-STATE:START -->
# DayZ Modding Knowledge Pack — Estado vivo · snapshot 2026-07-29 (C2, C4 y SC-006)

**Última verificación real:** HEAD `35943a3` en `r21/phase01-foundation`,
árbol limpio. **`main` sigue en `f87a59e`** y NO se ha adelantado: la Fase 02 no
está cerrada. Sin remoto. **Tres gates en verde y uno rojo a propósito**: suite
**809 passed / 18 skipped / 305 subtests**, `validate` PASS con cero findings,
gate de corpus PASS exit 0, y `promote --check` en **`FAIL`** por una **décima**
escritura host-direct en `dayz-vehicles` (ver «Lo que te va a morder» §1).

`ciclos_en_este_objetivo: 1 (Fase 02 — Tasks 3-5)`

> **Reiniciado a 1**: el objetivo anterior («B20, gate C1 y corpora») está
> cerrado y este es otro. No arrastra los dos ciclos de aquel. **Tasks 3-5 están
> hechas**, así que el próximo objetivo es otro y vuelve a reiniciarse.

## Lo que cerró esta sesión

**`C2` y `C4` en `✓`, y `SC-006` cerrado: 28 de 54.** Quedan `C3`, `C6`, `C7` y
`C8` de la Fase 02. **Tasks 3, 4 y 5 del plan están cerradas**; de la Task 4 falta
el tramo raster/assets y de la Task 5 solo el gate de Sorter V4 (ver abajo).

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

1. **Re-mide `promote --check` antes de tocar nada** (§«Lo que te va a morder»).
   Es lo único que separa el cuarto gate del verde, y se firma solo cuando la
   línea de vehículos esté quieta.
2. **Task 6 (`C6`)** — la sonda funciona y está desplegada en
   `P:\Mods\@LF_UIProbe`; falta el bundle `engine-capture-v1`. Requiere engine, no
   lo mezcles con el bloque offline. El puente ya está tendido: los `id` de widget
   del render son los del compositor y usan la misma derivación que el spec fija
   para `widget-tree.json`.
3. **`SC-008` (assets)** sigue bloqueado por el `ASSUMED` de licencia/procedencia
   del códec PAA/EDDS. El spec prohíbe meter código de códec antes de cerrarlo, así
   que eso es una decisión de licencia, no de implementación.
4. **El gate de Sorter V4** (último bullet de Task 5) sigue abierto **a propósito**:
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

1. **El destino muta solo: van DIEZ escrituras host-direct en `dayz-vehicles`.**
   La décima llegó a las **23:20 del 2026-07-28**, en mitad de esta sesión, y
   caducó la adjudicación de `b515776` —autorizaba `11722f3f`, el recibo explica
   `27037cfb`, el destino tiene `2337dd3b`—. **Adoptada sin firmar**: había
   `DayZDiag` ×2 y `AddonBuilder` corriendo, así que la línea de vehículos estaba
   viva. El gate queda rojo a propósito.

   **Re-mide `promote --check` antes de tocar nada.** Si vuelve
   `PROMOTION-TARGET-UNEXPLAINED`, el ciclo es: adoptar → refrescar `output_hash`
   → `git add` → `validate` → suite → commit → re-medir → adjudicar **solo** con
   quietud verificada y sin sesión de vehículos viva.

   Tres cosas que ahorran tiempo: **adoptar NO puede poner verde ese finding**
   —mira el destino, y adoptar cambia el repo—; **la entrada de `dayz-vehicles` en
   el source-map NO espeja el output** (sus tres inputs son ancestría), así que su
   adopción es un cambio de **una línea**, `output_hash` sola; y **mira el destino
   antes de sobrescribir**: trae un `SKILL.md.bak_pre_sp123_20260728` que es el
   backup del propio writer y no debe entrar en Git.

2. **Un mtime viejo tampoco prueba que el fichero sea viejo.** Ese `.bak` marca
   `20:55` y se creó a las `23:20`: `Copy-Item` preserva el timestamp del origen.
   Es el reverso de la invariante que ya estaba escrita aquí.
2. **No delegues nunca un `--basetemp` relativo ni concatenado.** Una ruta Windows
   con los separadores comidos aterrizó como directorio literal con una ACL que
   negaba `Remove-Item`, `takeown`, `icacls` y `robocopy`, y **rompía la colección
   de `pytest`**. Resuelto; el aviso se queda por la causa.
3. **`B3b` está fuera de alcance por decisión del usuario.** Sin API de pago no es
   alcanzable: `--bare` (`evals/live/runners/claude-code.py:28-43`) es lo único que
   esconde las skills globales del brazo de control, y es lo que se niega a leer la
   sesión OAuth. No lo reintentes.
4. **El harness de evals vivos tiene un fail-open, registrado y sin arreglar.**
   `_skills_tree_sha256` (`live_evals.py:201-211`) hashea `workspace/.claude/skills`
   (`:221`, `:233`), así que `LIVE-EVAL-ARM-CONTAMINATED` (`:446`, `:464`) prueba
   que ese árbol está vacío y **nada más**. Spike de aislamiento **sin empezar**.
5. **`@DayZ_MCP` no sirve como portador de test.** Su módulo `5_Mission` no
   compila: `CParser: quoted string not closed`, atribuido a
   `DayZ_MCP/scripts/5_Mission/mcpclientbridge.c`. Es del mod del usuario, no del
   pack, y no se ha tocado. Usa **`LFPowerGrid`**, que compila y está verificado.
6. **`Path.write_text` en Windows reescribe los finales de línea** de un repo que
   es LF por `.gitattributes`. Refrescar dos hashes convirtió 11.529 saltos. El
   blob queda bien, el árbol de trabajo no. Escribe con `write_bytes`.

## Método que ahorra sesiones

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

**Gate de arranque:** declarar `Retomo DayZ Modding Knowledge Pack desde: 35943a3
con Tasks 3-5 cerradas, C2 y C4 en ✓, 28 de 54, y el gate de promoción rojo por
la décima escritura en dayz-vehicles · próxima acción: re-medir promote --check y,
con el destino quieto, adjudicar; luego Task 6`.
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

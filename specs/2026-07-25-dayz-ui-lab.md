# Feature Spec: `dayz-ui-lab`

**Mod / PBO**: `dayz-ui-lab` offline tool + source-only probe fixture
**Date**: 2026-07-25
**Status**: Ready-to-implement
**Plan**: `plans/2026-07-24-02-dayz-ui-lab.md`
**DPF trace**: C1–C8; MCP handoff G4

## Context / Why

El visor existente parsea layouts aislados, pero no compone el estado runtime,
no rasteriza/difiere de forma canónica y contiene dos defectos medidos: B19
marca hojas válidas como incompletas y B20 rechaza continuaciones físicas que
DayZ carga. Esta feature crea un único laboratorio para implementar, observar,
comparar e iterar antes del golden final DayZDiag.

Aliases de evidencia: `UI_RESEARCH` = renderer local read-only fijado por source
map; `VANILLA` = scripts DayZ del build fijado; `VANILLA_GUI` = layouts vanilla
extraídos para research; `VAULT` = memoria privada no distribuible.

## Acceptance Scenarios

1. **Given** una fixture first-party con un `ButtonWidgetClass` hoja sin bloque
   hijo, **When** se parsea y se carga en DayZDiag, **Then** el parser devuelve
   cero `missing-child-block`, DayZ crea el botón y no aparece error de sintaxis
   del layout.
   - **Repro in-game**: lanzar DayZDiag con el probe, cargar
     `leaf-without-child-block.layout`, encontrar `LeafButton`, exportar su
     nombre/tipo y revisar RPT desde el sentinel begin hasta end.

2. **Given** dos fixtures first-party byte-equivalentes salvo EOL, una LF y otra
   CRLF, con dos cadenas unidas por continuación física explícita, **When**
   DayZDiag las carga y el parser offline las procesa, **Then** ambos lados
   devuelven exactamente el mismo texto lógico para las dos variantes.
   - **Repro in-game**: cargar primero `continuation-lf.layout` y después
     `continuation-crlf.layout`; leer el texto con
     `ButtonWidget.GetText(out string)` y comparar los dos registros de RPT y la
     salida offline. No implementar B20 hasta observar este resultado.

3. **Given** fixtures con llave desbalanceada, barra huérfana, continuación no
   observada y escape inválido, **When** se ejecuta el parser, **Then** cada una
   falla con código estable, source path, línea y columna; ninguna se normaliza
   silenciosamente.
   - **Repro in-game**: cargar la fixture de llave desbalanceada en un run
     aislado y confirmar error de layout en RPT; las otras negativas son gate
     offline para no gastar runs ni ampliar semántica del engine sin evidencia.

4. **Given** un escenario first-party con shell, subview y colección de tres
   cards, **When** se compone a 1920×1080 y 3440×1440, **Then** las tres cards
   conservan identidad, orden, estado y geometría calculada, y un path roto o un
   ciclo falla cerrado.
   - **Repro in-game**: cargar el escenario compuesto mediante el probe en ambas
     resoluciones, exportar el árbol y comparar ancestry, sibling index,
     visibilidad y geometría de las tres cards.

5. **Given** un escenario y un perfil de raster fijados, **When** dos ejecuciones
   limpias generan `render.json`, RGBA y PNG, **Then** los dos JSON son
   byte-idénticos; RGBA/PNG también lo son dentro del perfil y se marcan
   `non_canonical` fuera de él.
   - **Repro in-game**: capturar el mismo escenario/resolución en DayZDiag,
     importar ambos bundles y confirmar que el informe usa DayZDiag como golden,
     no el PNG offline.

6. **Given** una fixture negativa con referencia rota, clipping, overlap y
   estado ausente, **When** se ejecuta el diff, **Then** aparecen exactamente
   esos cuatro findings con scenario id, widget id, propiedad, esperado,
   observado y fuente editable; la fixture positiva devuelve cero.
   - **Repro in-game**: capturar la negativa y la positiva con el probe, importar
     ambos `engine-capture-v1` y comparar los findings estructurales por widget.

7. **Given** un escenario DayZDiag visible y una captura manual, **When** la
   sonda exporta el árbol y el importador recibe screenshot, snapshot, RPT y
   manifest, **Then** produce un `engine-capture-v1` coherente; capture ids,
   conteos, hashes, build o viewport mezclados fallan cerrados.
   - **Repro in-game**: abrir el escenario, esperar el estado settled, capturar
     PNG, conservar el tramo RPT delimitado y ejecutar el importador; repetir
     sustituyendo un artefacto por otro capture id y observar rechazo.

8. **Given** create/unlink y pooling sobre el mismo corpus, **When** se ejecuta
   el benchmark posterior a la calibración, **Then** ambos producen el mismo
   snapshot/render y pooling solo se promueve si no deja estado/callbacks y
   demuestra beneficio reproducible.
   - **Repro in-game**: ejecutar ambas estrategias en un único batch DayZDiag,
     abrir/cerrar/rebindear el escenario y comparar snapshot, callbacks y
     tiempos; «no adoptar» es un resultado válido.

9. **Given** una petición de implementar una UI visual, **When** un agente usa
   la skill `dayz-ui`, **Then** genera layout + escenario, itera mediante el
   mismo IR/render/diff y reserva DayZDiag para la aceptación final.
   - **Repro in-game**: ejecutar el eval de UI, cargar su fixture final con la
     sonda y confirmar que la skill no presenta preview offline como evidencia
     del engine.

## Success Criteria

- **SC-001 / C1-B19**: una hoja válida sin bloque hijo produce exactamente
  `0` diagnósticos `missing-child-block`; llave desbalanceada conserva source
  path, línea y columna.
- **SC-002 / C1-B20**: LF y CRLF producen exactamente el mismo valor lógico
  observado en DayZDiag; barra huérfana, forma no observada y escape inválido
  producen errores estables, no recuperación silenciosa.
- **SC-003 / C1 corpus**: VPP + Expansion + TraderPlus mantienen `319/319`,
  TraderX alcanza `46/46`, y LFPG fixtures pasan; el corpus válido devuelve
  exit `0` y cero falsos B19.
- **SC-004 / C2 schema**: `dayz-ui-scenario-v1` valida entrypoint, viewport,
  subviews, collections, bindings y estados nombrados; ciclo y path roto
  devuelven exit no-cero y código estable.
- **SC-005 / C2 composition**: shell→subview→3 cards conserva tres identidades
  distintas y su orden `0,1,2` en 1920×1080 y 3440×1440.
- **SC-006 / C3 semantic determinism**: dos ejecuciones limpias producen
  `render.json` byte-idéntico, sin timestamps ni rutas privadas.
- **SC-007 / C3 raster determinism**: dentro de un perfil que fija
  browser/rasterizador, codec, fuentes, SO y versiones, dos buffers RGBA y dos
  PNG son byte-idénticos; fuera del perfil, `canonical=false`.
- **SC-008 / C3 assets**: fixture first-party `.styles` + `.imageset` 9-slice +
  fuente propia resuelve todos sus assets; un asset ausente produce exactamente
  un finding estable y ningún fallback silencioso.
- **SC-009 / C4 diff**: la fixture negativa produce exactamente cuatro findings
  esperados —reference missing, clipping, overlap y missing state— y el control
  positivo produce `0`.
- **SC-010 / C5 corpus**: Git contiene manifests con commit/manifest/hash y
  licencia para VPP, Expansion, TraderPlus y TraderX, y contiene `0` layouts,
  capturas o assets de esos terceros.
- **SC-011 / C6 snapshot**: cada nodo exportado contiene id estable, parent id,
  sibling index, name, type, flags, sort, style, visibility, color, alpha,
  posición/tamaño local y posición/tamaño screen; begin/end repiten capture id y
  node count.
- **SC-012 / C6 bundle**: `engine-capture-v1` exige manifest, PNG, widget tree y
  RPT sanitizado con SHA-256; mismatch de capture id, count, hash, build,
  scenario o viewport devuelve exit no-cero.
- **SC-013 / C6 authority**: el import manual DayZDiag cierra el gate sin MCP;
  cada delta geométrico identifica un widget y no aplica un threshold pixel
  global inventado.
- **SC-014 / C7 pooling**: create/unlink y reuse producen snapshot/render
  equivalentes; `0` callbacks duplicados y `0` estados fantasma. Sin mejora
  reproducible registrada, el verdict es `do_not_adopt`.
- **SC-015 / C8 skill**: evals de UI vacía, style ausente, colección no
  compuesta, tooltip, fuente y offline≠engine pasan; solo una skill propia cubre
  los triggers UI.
- **SC-016 / A9 cierre**: `packctl validate` devuelve exit `0`,
  `PROMOTION-UNROUTED=0`, `PROMOTION-DRIFT=0`, y repo/Obsidian/skill activa
  coinciden con el recibo del commit promovido.
- **SC-017 / G4 handoff**: el schema no depende de MCP; el adapter posterior
  exige `run_id` + cliente único + PNG lossless y falla cerrado ante run
  inexistente, cliente ambiguo o bundle incompleto.

## Scope — Out of scope

- Modificar `py3d`, sus tests, rollout o plan de Fase 04.
- Modificar DayZ_MCP, su lifecycle, watch mode o captura pública en Fase 02.
- Hacer que MCP sea requisito para cerrar C6; el import manual es canónico.
- Copiar layouts, código, capturas, fuentes o assets de VPP, Expansion,
  TraderPlus o TraderX.
- Copiar `LF_UILab` como implementación probada o exigir Dabs a la sonda.
- Ejecutar Enforce Script en navegador o declarar el preview engine-faithful.
- Render 3D real de `ItemPreview`/`PlayerPreview` fuera del engine.
- Escribir ODOL o añadir codecs UI/asset a `py3d`.
- Adoptar pooling sin benchmark o tratar «no adoptar» como fallo.
- Inventar budgets de widgets, CPU, memoria, tiempos o tolerancias visuales sin
  medición reproducible.

## Assumptions

- ~~**ASSUMED — deferred before B20 GREEN**: DayZ concatena los fragmentos de la
  continuación sin insertar caracteres.~~ **REFUTADA por medición, 2026-07-28**
  (DayZDiag `1.29.163451`, sonda `LF_UIProbe`, `ButtonWidget.GetText`): el
  engine inserta **exactamente un salto de línea**. `Length()` devuelve `10` y
  `AlphaBeta` mide 9; el RPT lo escribe como CRLF, pero sus 49.768 bytes no
  contienen ni un LF suelto ni un CR suelto, así que un CR literal habría
  aparecido como CR suelto y un CRLF literal habría dado `11`. El valor lógico
  es `"Alpha\nBeta"`, idéntico para fuente LF y CRLF. El parser lo implementa
  así en `dba357e`. Haber diferido la decisión hasta medirla es lo que evitó
  codificar `"AlphaBeta"`.
- **ASSUMED — deferred before Task 4**: un perfil raster fijado puede producir
  RGBA/PNG byte-idénticos en dos entornos limpios. Se resuelve con spike antes
  de implementar el raster canónico; no afecta B19/B20 ni la IR semántica.
- **ASSUMED — deferred before Task 4 assets**: el codec elegido para PAA/EDDS
  será redistribuible o sustituible por una dependencia documentada. No entra
  código de codec hasta cerrar licencia/procedencia.
- **ASSUMED — deferred before Task 6**: la UI alcanza un estado settled
  observable después de actualización. La sonda probará convergencia en una
  fixture; no se fija un timeout universal sin medición.
- **ASSUMED — deferred to Phase 05**: el adapter MCP puede exponer selector
  run/client y PNG lossless sin alterar lifecycle. C6 no depende de ello.

## Forward Contract

| Consumer | Symbol it reads | Kind | Verify status |
|---|---|---|---|
| parser tests / viewer | `LayoutDoc.schemaVersion == 1` | existing IR field | `[EXACT] UI_RESEARCH/renderer/parse.py:22,71-105` |
| parser tests / viewer | `parse_text(...)`, `parse_file(...)` | existing Python API | `[EXACT] UI_RESEARCH/renderer/parse.py:379-412` |
| parser tests | `WidgetNode.has_child_block` | existing IR field | `[EXACT] UI_RESEARCH/renderer/parse.py:59-68,318-326` |
| B19 fixture | leaf `ButtonWidgetClass` without child block | vanilla syntax | `[EXACT] VANILLA_GUI/layouts/camera_tools/camera_tools.layout:298-310` |
| B20 engine probe | `WorkspaceWidget.CreateWidgets(string, Widget, bool)` | vanilla API | `[EXACT] VANILLA/1_core/proto/enwidgets.c:176-182` |
| B20 engine probe | `Widget.FindAnyWidget(string)` | vanilla API | `[EXACT] VANILLA/1_core/proto/enwidgets.c:168-170` |
| B20 engine probe | `ButtonWidget.GetText(out string)` | vanilla API | `[EXACT] VANILLA/1_core/proto/enwidgets.c:381-390` |
| probe cleanup | `Widget.Unlink()` | vanilla API | `[EXACT] VANILLA/1_core/proto/enwidgets.c:158-173` |
| engine snapshot | widget identity/state/geometry getters | vanilla API set | `[EXACT] VANILLA/1_core/proto/enwidgets.c:121-160` |
| scenario composer | `dayz-ui-scenario-v1` | new schema contract | `[DESIGN] this spec SC-004/SC-005; implementation must create and validate before Analyze Gate` |
| viewer/raster/diff | `dayz-ui-render-v1` | new normalized render contract | `[DESIGN] this spec SC-006–SC-009; implementation must create before consumers` |
| importer / Phase 05 MCP | `engine-capture-v1` | new bundle schema | `[DESIGN] this spec SC-011–SC-013/SC-017; implementation must create before importer/adapter` |
| Phase 05 MCP adapter | `transport=mcp`, non-empty `run_id`, unique client, PNG | new conditional contract | `[DESIGN] this spec SC-017; adapter remains out of Phase 02` |
| `dayz-ui` skill | `dayz-ui-lab` parse/render/diff CLI | new tool surface | `[DESIGN] this spec SC-015; promote only after tool gates` |

No engine API, classname, layout path, PBO prefix or stringtable key requerido
por la primera implementación permanece `[UNVERIFIED]`. Los tres contratos
nuevos están definidos aquí y su existencia se convierte en gate del Analyze
Gate antes de cualquier consumidor.

## `engine-capture-v1` Contract

`manifest.json` define:

- `schema_version`: literal `engine-capture-v1`;
- `capture_id`, `scenario_id` y `dayz_build`: strings no vacíos;
- `viewport.width` y `viewport.height`: enteros positivos en píxeles;
- `transport`: `manual` o `mcp`;
- `run_id`: prohibido para `manual` y obligatorio/no vacío para `mcp`;
- `artifacts.screenshot`, `artifacts.widget_tree`, `artifacts.rpt`: nombres de
  archivo relativos sin `..`, cada uno con SHA-256 hexadecimal;
- `widget_count`: entero no negativo, idéntico en manifest, begin/end y tree;
- ninguna ruta absoluta, timestamp requerido, key, profile o identidad privada.

`widget-tree.json` define un root document con el mismo `schema_version`,
`capture_id`, `scenario_id`, `viewport` y `widget_count`. Cada nodo tiene:

- `id` derivado de ancestry + sibling index + name + type;
- `parent_id` nullable y `sibling_index` no negativo;
- `name`, `type`, `flags`, `sort`, `style`, `visible`, `color`, `alpha`;
- `local.{x,y,width,height}` y `screen.{x,y,width,height}`;
- `children` como ids ordenados.

La sonda delimita la captura en RPT con begin/end que repiten capture id y
node count. El importador calcula hashes, valida la firma PNG, rechaza records
truncados/duplicados y produce el bundle; no confía en el nombre del proceso.

## Data / Lifecycle

- El parser y todos los renders son offline y no mutan el source layout.
- La sonda corre solo en cliente. No registra SyncVars, no envía RPC y no
  solicita estado server-only.
- Lifecycle de la sonda: create root → apply named state → settle gate →
  snapshot/sentinels → screenshot externo → `Unlink()` root.
- Un fallo antes del sentinel end invalida toda la captura.
- El importer nunca mezcla artefactos: valida ids, counts, viewport, build y
  hashes antes de calcular deltas.
- `preview.html` y `preview.png` son artefactos derivados; `scenario.json`,
  layout source e IR normalizada son las entradas versionables.

## Error Cases

| Caso | Resultado requerido |
|---|---|
| leaf sin child block | válido; cero warning B19 |
| llave desbalanceada | error con path/línea/columna |
| barra huérfana / continuación no observada | error estable, fail-closed |
| escape inválido | error estable, sin sustitución |
| path roto / ciclo de escenario | exit no-cero, código estable |
| binding/state/asset ausente | finding accionable; sin fallback silencioso |
| snapshot sin sentinel end o count mismatch | captura inválida |
| screenshot no PNG o hash incorrecto | captura inválida |
| capture/scenario/build/viewport mezclado | captura inválida |
| adapter MCP con run inexistente/cliente ambiguo | rechazo fail-closed |
| perfil raster no fijado | output `non_canonical`, nunca golden |

## Visual States

Cada escenario declara estados nombrados; no existe un mapa runtime global
implícito. El set mínimo de fixtures cubre:

- empty, populated, selected y hover;
- loading, ready, requesting y error;
- tab activa/inactiva;
- modal abierta/cerrada;
- tooltip visible/oculto;
- control enabled/disabled;
- raw layout frente a runtime-applied state.

La skill debe exigir un Forward Contract visual: qué crea el layout, qué
inserta el script, qué muta por estado y qué nunca puede validar el preview.

## Observability

- Parser: exit code, error code, source path, línea y columna.
- Scenario/render/diff: schema version, scenario id, viewport, canonical flag y
  widget ids estables.
- Probe: begin/end sentinels, capture id, node count y un record estructurado por
  widget; cualquier truncamiento invalida el batch.
- Bundle: SHA-256 por artefacto y manifest depersonalizado.
- Report: por finding, scenario, widget id, propiedad, esperado, observado,
  fuente editable y evidencia engine/offline.
- Severidad usa `crash`, `exception`, `corruption`, `degradation` o `cosmetic`
  de forma concreta; un error visual no se llama crash.

## Verification Plan

| Criterion | Verification | Where |
|---|---|---|
| SC-001 | unit tests leaf + brace error; grep corpus por diagnostics | offline |
| SC-002 | test first RED LF/CRLF/orphan/escape; compare RPT `GetText` | offline + one DayZDiag batch |
| SC-003 | corpus runner sobre roots allowlisted y manifests fijados | offline |
| SC-004–SC-005 | schema fixtures positive/negative + two viewports | offline; geometry calibrated in DayZDiag batch |
| SC-006 | compare SHA-256 of two clean `render.json` | offline |
| SC-007 | compare RGBA/PNG under pinned profile; mutate profile | offline, two clean environments |
| SC-008 | first-party assets positive + one missing asset negative | offline + DayZDiag visual batch |
| SC-009 | exact finding-set assertions | offline |
| SC-010 | provenance/privacy/license scan of Git payload | offline |
| SC-011 | schema assertions per node + sentinel count | offline + DayZDiag batch |
| SC-012 | JSON Schema tests and directed artifact mutations | offline |
| SC-013 | manual import of DayZDiag capture and per-widget delta report | one DayZDiag batch |
| SC-014 | create/unlink vs reuse snapshot/callback benchmark | offline where possible + final DayZDiag batch |
| SC-015 | eval harness current-vs-baseline + trigger overlap audit | offline |
| SC-016 | `packctl validate`, promotion dry-run/apply/readback | offline |
| SC-017 | schema conditional tests now; adapter tests in Phase 05 | offline |

## Implementation Slices

1. Contract amendments + this spec.
2. B19 tests RED → minimal GREEN.
3. B20 engine micro-fixture → tests RED → minimal GREEN; stop if engine
   semantics remain unobserved.
4. IR/scenario schemas and composition.
5. Semantic render and structural diff.
6. Pinned raster profile and first-party asset resolution.
7. Source-only probe, importer and DayZDiag calibration.
8. Pooling experiment.
9. Skill/evals/Obsidian/promotion/close.

Cada slice termina verde y revisado antes del siguiente. B19 puede cerrarse
aunque la identidad MCP actual bloquee el micro-fixture B20; ningún trabajo de
scenario/golden/diff empieza mientras C1 siga abierto.

**Checkpoint 2026-07-25**: slices 1–2 completados. B19 está en GREEN con
`10/10` tests offline del parser/probe; la fixture source-only B20 ya genera
variantes LF/CRLF byte-equivalentes. El parser B20 permanece deliberadamente
sin modificar porque `session_status` y `bridge_status` siguen devolviendo
`unauthorized` y aún no existe observación DayZDiag.

**Checkpoint 2026-07-28**: slice 3 completado. La observación DayZDiag existe y
`SC-002` está cerrado en sus dos mitades medibles offline: LF y CRLF producen el
mismo valor lógico, y ese valor —`"Alpha\nBeta"`— es el que devuelve el engine.
El parser pasa **46/46** en TraderX (antes 42/46), cerrando las cuatro
continuaciones de `BuyTooltip:80`, `CustomizeTooltip:79`, `SellTooltip:75` y
`testTooltip:74`. Barra huérfana y forma no observada fallan explícitamente; el
escape inválido queda pendiente de corpus (ver Open Questions).

`SC-003` **no** está cerrado: exige además `319/319` del corpus público, y VPP,
Expansion y TraderPlus no tienen checkout local en esta máquina. Lo medible aquí
se midió; el resto necesita los tres checkouts, no más trabajo de parser.

## Open Questions / NEEDS CLARIFICATION

No hay decisión de producto pendiente. El gate externo de MCP que bloqueaba B20
**está resuelto**: el 2026-07-28 el micro-fixture corrió por el lifecycle
gestionado (`dayz_test_run`), sin bypass del launcher, y B20 quedó medido.

Queda **una** pregunta abierta, y es de evidencia, no de producto: qué debe
hacer el parser con un **escape desconocido dentro de string**. La tabla de
Error Cases pide error estable; hoy se sustituye en silencio. No se ha cambiado
porque el corpus público de 319 layouts no tiene checkout en esta máquina y es
justo el que podría romperse, mientras que TraderX contiene **cero** backslashes
dentro de string (medido sobre los 46 extraídos con Mikero `ExtractPbo`). Se
decide cuando haya corpus con el que medirlo. Riesgo asimétrico registrado: un
backslash **fuera** de string sí es error duro hoy, luego el corpus público no
contiene ninguno y las reglas de continuación añadidas no pueden romperlo.

## Spec Quality Checklist

- [x] CHK001 Every Success Criterion is measurable.
- [x] CHK002 No vague adjectives are used as criteria.
- [x] CHK003 Numeric criteria include units/counts and thresholds.
- [x] CHK004 Every acceptance scenario uses Given/When/Then and concrete
  DayZDiag repro steps.
- [x] CHK005 Every criterion/scenario has a verification path.
- [x] CHK006 Offline-verifiable criteria are marked offline.
- [x] CHK007 Every guess is marked `ASSUMED`.
- [x] CHK008 Correctness-deciding assumptions are resolved before their slice
  or explicitly deferred with a hard stop.
- [x] CHK009 No template placeholders remain.
- [x] CHK010 Every existing Forward-Contract API has `path:line`; new contracts
  are explicitly `[DESIGN]` with a creation gate.
- [x] CHK011 Every existing classname/API/path used by the first slice was
  opened and verified.
- [x] CHK012 No `[UNVERIFIED]` ref is required by implementation.
- [x] CHK013 Out-of-scope is explicit.
- [x] CHK014 Canonical terms are stable: scenario, render, capture, probe,
  importer and adapter.
- [x] CHK015 Criteria and scenarios do not contradict.
- [x] CHK016 No persistence/progression/admin command is introduced; lifecycle
  recovery is covered by fail-closed capture/import and the existing MCP
  lifecycle guard.

**Result: 16/16 PASS.**

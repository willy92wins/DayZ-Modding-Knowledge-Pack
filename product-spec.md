# product-spec.md — DayZ Modding Knowledge Pack

> **Definición de Producto Final (DPF).** El progreso vivo está en
> `HANDOFF.md`; este documento fija el resultado aceptable.

## Qué es “terminado”

El siguiente release del pack será una fuente Git reproducible y un ZIP
depersonalizado que una persona o agente pueda usar para crear, verificar,
probar y publicar mods DayZ sin depender de rutas privadas ni convertir
afirmaciones no verificadas en doctrina.

El producto terminado incluye infraestructura de evidencia, UI iterativa,
persistencia segura, skills de dominio prioritarias, tooling py3d, metodología
MCP publicable y documentación de release/contribución. Todo conocimiento
aceptado queda además en Obsidian y, cuando es una invariante de dominio, en la
skill activa correspondiente.

**Alcance y orden confirmados con el usuario el 2026-07-24.**

## Cláusula de desafío

Cada criterio sirve al `Intent` de su grupo. Si una implementación más simple
protege mejor ese Intent, o una exigencia literal lo contradice, se plantea en
el Grill del plan antes de implementar. El criterio no cambia sin aprobación
y entrada en el changelog.

## A — Fuente, compatibilidad y release reproducible

> **Intent:** que exista una sola verdad distribuible y que Obsidian/skills
> reciban promociones verificables sin convertirse en fuentes paralelas ni
> filtrar datos privados.

| # | Criterio | Cómo se verifica | Estado |
|---|---|---|---|
| A1 | Git es fuente canónica del pack distribuible; Obsidian conserva memoria/evidencia completa y las skills instaladas son despliegues operativos | roles registrados en ADR 001/002; ninguna release se construye desde una copia instalada | ✓ |
| A2 | Inventario de procedencia cubre el 100% de archivos distribuibles y adjudica cada drift pack↔fuente | validador devuelve 0 `SOURCE-UNMAPPED`, 0 conflictos sin decisión | ✓ |
| A3 | Todas las skills cumplen la especificación Agent Skills y frontmatter ≤1024 caracteres | `skills-ref validate` con UTF-8: N/N válidas, exit 0 | ✓ |
| A4 | Dos builds limpios del mismo commit producen ZIP byte-idéntico y manifiestos iguales | dos SHA-256 iguales; orden, timestamps y encoding normalizados | ✓ |
| A5 | Manifest machine-readable declara release, commit, DayZ build, schema, licencias, hashes y convención de conteo | schema validation exit 0; número declarado = archivos reales según convención explícita | ✓ |
| A6 | Licencia MIT raíz, notices de terceros y política “no redistribuir rutas/inputs privados” | audit de licencias: 0 archivos distribuibles sin cobertura; py3d conserva MIT upstream | ✓ |
| A7 | Matriz por skill con build DayZ probado, fecha, dependencias y breaking changes | 100% de skills listadas; ninguna afirma compatibilidad sin evidencia | ✓ |
| A8 | Cero secretos, identidades, rutas privadas o links locales rotos no allowlisted | scanner y link audit exit 0 sobre el ZIP construido | ✓ |
| A9 | Todo conocimiento aceptado tiene routing repo↔Obsidian↔skill aplicable y recibo de promoción por commit/hash | `PROMOTION-UNROUTED=0`, `PROMOTION-DRIFT=0`; readback de todos los targets configurados; `not_applicable` exige motivo y se prohíbe para invariantes de dominio | ✓ |

## B — Evidencia, APIs, evaluaciones y preflight

> **Intent:** que el asistente aprenda contratos verificables y que una mejora
> de una skill pueda demostrarse frente a un baseline, no solo parecer mejor.

| # | Criterio | Cómo se verifica | Estado |
|---|---|---|---|
| B1 | Cada claim/snippet ejecutable nuevo registra fuente, build/commit, `path:line`, licencia, fecha, nivel de verificación y routing de promoción | provenance audit: 0 claims ejecutables sin registro o destino | ✓ |
| B2 | Índice `dayz-api-index` regenerable, vanilla-first, read-only, con allowed-roots y rechazo de build/schema incompatible | fixtures clase activa/comentada/inexistente/colisión; path escape y build mismatch fallan cerrados | ✓ |
| B3a | Harness mecánico de regresión del catálogo: cada caso de `evals/cases/` está bien formado y su veredicto fijado cuadra con sus aserciones | `packctl gate` recorre las variantes y falla con `EVAL-UNEXPECTED-VERDICT` si alguna se desvía; cada run emite `grading.json` y evidencia. **No compara contra baseline**: la respuesta puntuada está escrita en el propio caso | ✓ |
| B3b | Existe al menos un caso vivo `DISCRIMINATING`: mismo enunciado y fixture, N runs por brazo, la skill montada frente a ausente, y el brazo sin skill por debajo de su techo | `pass_rate(with_skill) >= min_pass_with_skill`, `pass_rate(without_skill) <= max_pass_without_skill` y diferencia `>= min_discrimination`, sobre un runner real y con el hash del árbol de skills registrado por brazo | ❓ |
| B4 | Errores StarDZ auditados existen como casos negativos | evals rechazan `autoptr` falso, overload falso, `Managed` falso, `JsonLoadFile`, `OnDrop` incompleto y Dabs inválido | ✓ |
| B5 | Pipeline CI-like ejecuta skill validation, provenance, links, privacy, Python, py3d y build reproducible | un comando local devuelve 0; mutaciones dirigidas producen códigos estables y exit no-cero | ✓ |
| B6 | Template mínimo `@MyMod` implementa la estructura, contratos de config, build y misión de test recomendados, consumiendo los mismos gates release-grade que `dayz-workshop-release` | scaffold se instancia sin rutas privadas; preflight y dry-run verifican artefacto nuevo/estructural y una publicación fallida conserva el PBO previo | ❓ |
| B7 | Simuladores offline reducen iteraciones sin presentarse como sustitutos del engine | parser de config y validadores loot/CE/physics tienen fixtures positivas, negativas y límites explícitos | ❓ |
| B8 | `dayz-api-index` v2 distingue liveness `active/commented/missing`, parent chain, guardas y namespace sin sustituir la lectura de fuente | fixtures estructurales cubren liveness, ciclos, `#ifdef`, overrides/config y comentarios; conserva allowed-roots/build/schema/tree digest | ❓ |

## C — `dayz-ui-lab` y skill `dayz-ui`

> **Intent:** que un agente pueda implementar una interfaz solicitada, observar
> un resultado determinista, comparar, corregir e iterar antes del gate real en
> DayZDiag, sin confundir preview offline con verdad del engine.

| # | Criterio | Cómo se verifica | Estado |
|---|---|---|---|
| C1 | Parser honesto cierra B19/B20 | 319/319 corpus público + 46/46 TraderX + LFPG, exit 0; 0 falso `missing-child-block`; CRLF/LF verificados en DayZDiag | ✓ |
| C2 | Escenarios versionables componen shell, subviews y colecciones, detectando ciclos y paths rotos | fixture shell→subview→3 cards conserva orden/identidad/geometría en 1920×1080 y 3440×1440 | ❓ |
| C3 | El render semántico es determinista entre ejecuciones limpias; RGBA/PNG solo son canónicos dentro de un perfil de raster fijado, y resuelven assets propios | dos `render.json` byte-idénticos sin timestamps/rutas privadas; dentro del perfil fijado, dos buffers RGBA y PNG byte-idénticos; fuera del perfil, artefacto `non_canonical`; fixture `.styles` + `.imageset` 9-slice + fuente sin fallback silencioso | ❓ |
| C4 | Diff accionable identifica referencia rota, clipping, solape y estado ausente por widget/escenario | fixture negativa produce exactamente los hallazgos esperados; control verde produce 0 | ❓ |
| C5 | Corpus positivo = VPP/Expansion/TraderPlus/TraderX; negativo = LFPG Sorter V4 TEST; terceros no se redistribuyen | manifests por commit/hash y auditoría de allowlist | ✓ |
| C6 | DayZDiag manda como golden; una sonda ingame first-party exporta geometría/estado runtime y calibra resoluciones/aspect ratios definidos | bundle `engine-capture-v1` coherente por escenario/run con screenshot PNG, snapshot estructurado completo, RPT sanitizado, build y resolución; import manual basta para cerrar el gate; deltas offline cuantificados por widget, sin umbral inventado | ❓ |
| C7 | Pooling solo se promueve con lifecycle completo y beneficio medido | create/unlink vs reuse: mismo output; 0 estado fantasma/callback duplicado; benchmark reproducible | ❓ |
| C8 | Skill UI incorpora arquitectura, Forward Contract visual y árboles de diagnóstico verificados | evals “vacío/estilo/colección/tooltip/fuente/offline≠engine” pasan | ❓ |

**Evidencia ejecutada el 2026-07-28** para `C1` y `C5`, medida sobre el árbol y
re-ejecutable desde el repo con
`python tools/dayz-ui-lab/dayz_ui_lab/corpus.py --root .`:

```
vpp-admin-tools   69/69    dayz-expansion 234/234    traderplus-v1 16/16
traderx           46/46    lfpowergrid     11/11
totals: 376/376 layouts parse across 5/5 corpora, 0 diagnostics emitted
provenance: 1 tracked .layout, 0 redistributed, 364 third-party layouts compared
verdict=PASS  (exit 0)
```

- **C1** — `319/319` público (VPP 69 + Expansion 234 + TraderPlus 16), `46/46`
  TraderX y `11/11` LFPG, exit `0`. El *0 falso `missing-child-block`* se **mide**,
  no se infiere de que B19 quitara la rama: el runner cuenta los diagnósticos que
  el parser emite de verdad y el total es `0`; si alguien reintrodujera uno,
  `CORPUS-DIAGNOSTICS-EMITTED` se pone rojo. El tramo CRLF/LF quedó verificado en
  DayZDiag `1.29.163451` con la sonda `LF_UIProbe` (`len=10`, LF y CRLF iguales,
  valor `"Alpha\nBeta"`); ver `plans/2026-07-24-02-dayz-ui-lab.md` §B20.
- **C5** — `tools/dayz-ui-lab/corpora/manifest.json` fija los cuatro referentes
  por commit (VPP `dc22e420`, Expansion `8d3a453b`, TraderPlus `d0cd39f1`) o por
  manifest de Workshop (TraderX `3069958660046119589`), cada uno con licencia y
  restricción de redistribución. **Los tres hashes de PBO de TraderX se
  recomputaron en local** y reproducen los del research, en vez de transcribirse.
  La auditoría de procedencia compara **por contenido, no por ruta**, los 364
  layouts de terceros contra lo rastreado en el repo: `0` redistribuidos, y el
  único `.layout` rastreado es la fixture first-party de la sonda. Un layout de
  tercero plantado con otro nombre lo detecta un test dedicado.

> Ninguno de los tres repos de referencia se redistribuye. El pack lleva solo
> URL, commit/manifest, hash y licencia; los bytes los aporta el operador vía
> `sources/local-roots.json`, que no se rastrea. Un corpus sin raíz configurada
> **falla el gate**, no se salta en silencio: «no medido» y «pasa» no pueden
> parecerse.

## D — `dayz-persistence`

> **Intent:** que actualizar, migrar, truncar o hacer rollback nunca convierta
> una incompatibilidad en corrupción silenciosa o pérdida evitable.

| # | Criterio | Cómo se verifica | Estado |
|---|---|---|---|
| D1 | Skill separa stream vanilla, CF ModStorage y archivos/sidecars | tres contratos y tres suites de fixtures independientes | ✓ |
| D2 | Versionado/migración cubre fresh, legacy, known, future, truncated, same-build upgrade y rollback | matriz completa produce verdict/acción esperados, sin lectura parcial aceptada | ✓ |
| D3 | Sidecars usan temp→verify→replace, backup y recuperación fail-closed | fault injection en cada frontera I/O conserva original o evidencia recuperable | ✓ |
| D4 | APIs deprecated y ejemplos incompletos no se recomiendan | evals rechazan `JsonLoadFile` como patrón nuevo y headers ligados solo al build DayZ | ✓ |
| D5 | Todo cambio persistente documenta legacy, datos post-cambio en rollback y alternativa sin cambio de formato | checklist y rigorous-data-audit sin hallazgos bloqueantes | ✓ |

**Evidencia ejecutada el 2026-07-28** (cada `✓` con la línea que lo cierra, medida sobre
`dcf0671`, no inferida). Spec: `specs/2026-07-28-dayz-persistence.md`, checklist 16/16.

- **D1** — tres referencias de contrato en `skills/dayz-persistence/references/` y tres
  simuladores que no comparten código: `test_persistence_router.py` parsea los tres módulos
  con `ast` y exige que sus imports sean disjuntos, así que factorizar un serializador común
  pone el gate en rojo. Router con `needs_clarification` para entrada ambigua.
- **D2** — `test_persistence_migration.py`: las 7 celdas con sus cuatro columnas (verdict,
  bytes consumidos, estado preservado, acción) y **mutation check por celda** —mutar un byte
  cambia el verdict en 7/7—. `truncated` nunca da `ok` y descarta el estado parcial entero;
  `future-version` deja el hash del fichero idéntico y emite una sola línea de log por
  ventana.
- **D3** — `test_persistence_sidecar.py`: las **9** fronteras I/O con fallo inyectado, cada
  una con la invariante «original intacto **o** evidencia recuperable». Incluye la ventana
  real del replace (fallo entre `delete_file` y `copy_file`, destino ausente y `.tmp`+`.bak`
  recuperables) y un test que exige que el FS exponga exactamente las nueve primitivas de
  DayZ, sin `rename` ni `move`.
- **D4** — `evals/cases/persistence-deprecated-api.json`, `persistence-mod-version.json` y
  `persistence-migration-rollback.json`, ejecutados por el harness (`evals/cases/*.json`, con
  inventario cerrado en `tests/packctl/test_evals.py`), cada uno con `current=PASS` /
  `absent=FAIL`. Verificado además que ningún `value` de assertion aparece en el `prompt` de
  su propio caso.
- **D5** — `test_persistence_checklist.py`: el checklist falla exactamente una vez por
  elemento ausente (legacy, rollback, alternativa sin cambio de formato), acumula sin
  cortocircuito y rechaza una alternativa presentada *después* del cambio. Más
  `rigorous-data-audit` **sin hallazgos bloqueantes**: 1 P2 y 2 P3, los tres corregidos en
  `dcf0671`.
  **Alcance declarado de esa auditoría:** se ejecutó **single-agent**, porque los subagentes
  exigen autorización explícita en este proyecto (`project-brief.md`) y la sesión no la
  tenía; hay precedente registrado en `compatibility-matrix.md`. Corrió el Step 1 completo
  —las comprobaciones mecánicas, que es donde la propia skill dice que el razonamiento
  falla— y la verificación 1-a-1 de cada hallazgo contra el fichero. **No** corrieron el
  Step 2 (ocho ángulos en paralelo) ni el Step 4 (implementer-grade con contexto fresco).
  Informe: `VAULT/10_Projects/DayZ_Modding_Knowledge_Pack/reviews/2026-07-28-phase03-rigorous-data-audit.md`.

## E — Skills y conocimiento de dominio

> **Intent:** cubrir las áreas que hoy obligan al asistente a improvisar,
> manteniendo módulos pequeños y research vanilla-first.

| # | Criterio | Cómo se verifica | Estado |
|---|---|---|---|
| E1 | `dayz-multiplayer-sync` cubre RPC, fiabilidad, ownership, predicción y diagnóstico de desync | fixtures cliente/servidor, auth fail-closed y dos clientes locales | ❓ |
| E2 | `dayz-sound-particles` cubre `.ptc`, soundsets, Effect systems y occlusion | ejemplos fuente-pineados + build/smoke por subsistema | ❓ |
| E3 | `dayz-terrain` cubre mapa básico, roadgraph y CE | proyecto mínimo reproducible y checks de roadgraph/CE | ❓ |
| E4 | `dayz-workshop-release` cubre mod.cpp, dependencias, signing/bisign, imágenes, changelog, preflight, cache invalidable y publicación transaccional | dry-run exige PBO nuevo, header/prefix/entries, firma cuando aplique y log sin fatal; cambios de inputs/toolchain invalidan cache y un fallo conserva bytes/manifest previos | ❓ |
| E5 | Vault incorpora RPT decision tree, arquitecturas mod y guía de performance medida | ramas deduplicadas con evidencia; budgets declaran build/hardware/corpus | ❓ |
| E6 | Disease/modifiers y plugin lifecycle se auditan vanilla-first antes de convertirse en skill/referencia | research con `path:line`, sides, lifecycle y fixtures; unknowns quedan marcados | ❓ |
| E7 | Compatibilidad se revisa contra la stable fijada y registra breaking changes | matriz actualizada desde fuentes locales/oficiales y fecha verificable | ❓ |

## F — py3d y validación de export

> **Intent:** que el tooling 3D reduzca iteraciones y bloquee corrupción o
> modelos no canónicos antes de binarize.

| # | Criterio | Cómo se verifica | Estado |
|---|---|---|---|
| F1 | Proxies soportan add/remove/align con rotación y round-trip | fixtures con matrices conocidas; save→reload conserva transform y selección | ✓ |
| F2 | Helpers de RTM/SEAnim/animación tienen contrato y límites explícitos | round-trip o export fixture comparado con referente aceptado | ✓ |
| F3 | Pre-export valida winding, huesos y escala | fixtures positivas/negativas y códigos estables; 0 reparación silenciosa | ✓ |
| F4 | Existe lectura ODOL read-only para anatomía/paridad, con cobertura y limitaciones declaradas, sin añadir writer ODOL | v53/v54/v55 fixtures legalmente distribuibles, self-diff y fallos boundary/oob fail-closed | ✓ |
| F5 | py3d mantiene toda su suite verde y una sola distribución canónica | baseline 130 pass/10 skip no retrocede; wheels/rollout hashes pineados | ✓ |

## G — MCP publicable y automatización

> **Intent:** hacer reproducible la metodología de prueba incluso sin el bridge
> privado y ampliar capacidades sin debilitar lifecycle/ownership.

| # | Criterio | Cómo se verifica | Estado |
|---|---|---|---|
| G1 | Protocolo del bridge documenta comandos, schemas, errores, versión y extensión | ejemplos request/response validados contra schema y bridge actual | ❓ |
| G2 | Modo lite funciona con DayZDiag + filePatching + scripts ingame, sin bridge privado | ladder mínima spawn→acción→RPT/verdict reproducible | ❓ |
| G3 | Un orquestador integra test-ingame + MCP y watch mode incremental | cambio de fixture dispara rebuild/retest exacto; lease y run_id permanecen fail-closed | ❓ |
| G4 | Secuencias, crash/RPT detection, screenshot diff, telemetry y dos clientes tienen gates separados | cada capability tiene fixture y verdict; el adapter de screenshot importa `engine-capture-v1`, selecciona un único cliente por `run_id` y conserva PNG lossless o falla cerrado; ningún número de performance sin medición | ❓ |
| G5 | Alternativas VPP/init.c y companions se documentan con límites; dayz-labs queda pineado, opcional y sin autoridad de lifecycle, y Cheat Engine no es dependencia recomendada | matriz capability/fiabilidad/riesgo/licencia/version verificada; gates excluyen installer y `start/stop/restart`; WPF no cuenta como evidencia `.layout` | ❓ |

## H — Ecosistema, contribución y pulido

> **Intent:** que el pack sea mantenible, enseñable y ampliable sin duplicación
> ni dependencia de la máquina original.

| # | Criterio | Cómo se verifica | Estado |
|---|---|---|---|
| H1 | Integración Workbench/Mikero/viewers documentada con versiones y licencia | comandos smokeados o marcados como companion no verificado | ❓ |
| H2 | Entorno limpio de server reproducible usa VM o alternativa viable, elegida tras spike | segunda máquina/VM ejecuta smoke sin junctions privados | ❓ |
| H3 | Guía de contribución define source map, evidencia, tests, licencia, promoción a Obsidian/skills y release | contribución fixture atraviesa validación y promoción end-to-end | ❓ |
| H4 | Notas duplicadas se consolidan sin perder claims/evidencia | mapa old→canonical; link audit y diff semántico revisados | ❓ |
| H5 | Diagramas mínimos cubren skeleton, proxy frame y lifecycle Construction quartet | assets first-party, links válidos y revisión humana | ❓ |
| H6 | Risk register/known engine bugs vive versionado y distingue crash/exception/corruption/degradation/cosmetic | cada entrada tiene evidencia, build y severidad concreta | ❓ |

## Fuera de alcance

- Importar StarDZ como skill monolítica o copiar snippets no verificados.
- Bundlear código/assets GPL, DPL-ND, CC-NC, vanilla DayZ o mods de terceros.
- Integrar lifecycle de dayz-labs/Lake como autoridad paralela a DayZ_MCP.
- Ejecutar Enforce en el navegador o prometer previews 3D fieles al engine.
- Escribir ODOL.
- Fijar budgets de CPU/red/widgets sin benchmark reproducible.
- Publicar repo, release o Workshop durante la fase de planificación.
- Tratar Obsidian o skills instaladas como fuentes paralelas de release; la
  promoción ocurre desde Git tras gates y conserva evidencia privada solo en
  Obsidian.

## Referencias de paridad

- Baseline ZIP SHA-256
  `E63C26C5C385E3037B4AFE9C918B3A9DE9E12CC0AF876316214518BF852735E5`;
  commit raíz `d48e2c1a02dacc97645a9e70d8bc1058e6dae9a5`.
- Agent Skills reference validator: snapshot oficial
  `38a2ff82958afee88dadf4831509e6f7e9d8ef4e`.
- DayZ inicial de compatibilidad: `1.29.0.163451`, verificado 2026-07-24.
- UI: VPP y Expansion fijados por commit; TraderX por manifest
  `3069958660046119589` y PBO hashes; LFPG Sorter V4 TEST como negativo.
- Prior art auditado: dayz-labs `dbd6ad3e...`, Lake `ac56f369...`,
  StarDZ `dbdcd23b...`.
- py3d upstream `7acd58b`/tag `v1.0` y fork release `1.4.0`; wheel
  reproducible SHA-256
  `8043b796dd18fe3d949fde03031d51afa3759021936760953c0e6ec0d74f86c2`,
  re-sellado el 2026-07-28 por decisión explícita del usuario: `4271ff0`
  endureció la fuente del wheel (`tools/py3d/py3d/__init__.py`), así que el
  sello anterior `c635bf7ec12c…` describía la fuente de `913192d` y el gate
  se puso rojo por el motivo correcto. Ese valor había sustituido a su vez a
  `cc014a4330e8…`, fijado antes de que `tools/py3d/pyproject.toml` existiera,
  cuando PEP 517 resolvía `setuptools` dinámicamente; ninguno de los dos se
  conserva como objetivo. La reproducibilidad es **toolchain-bound**: vale para
  `setuptools==83.0.0` y Python `3.14.3`, ambos declarados en
  `rollout/wheel-manifest.json`. La versión `1.4.0` ha designado dos contenidos
  distintos sin cambiar de nombre de fichero; lo que los distingue es el sello
  del manifiesto, no la versión.

Aliases de evidencia usados en los planes:

- `VANILLA/3_game/entities/entityai.c:2908-2925,2965-2989` — contrato
  `OnStoreSave`/`OnStoreLoad`.
- `VANILLA/3_game/tools/jsonfileloader.c:7-40,99-105` — `LoadFile` y
  deprecación de `JsonLoadFile`.
- `CF_ROOT/Entities/ItemBase.c:22-84` y
  `CF_ROOT/ModStorage/CF_ModStorageObject.c:25-76,80-156` — integración y
  framing de CF ModStorage.
- `VANILLA/3_game/gameplay.c:104-117` — firma de `ScriptRPC.Send`.
- `VAULT/AI/10_Projects/DayZ_UI_Research/project-brief.md:25-26` y
  `research/2026-07-24-ui-positive-reference-corpus-codex.md:64-105` —
  baseline B19/B20 y corpora UI.

La fase 01 fijará revisión, hash y root local de cada alias fuera de Git.

## Changelog de alcance

- 2026-07-24 — alcance inicial y orden aprobados por el usuario.
- 2026-07-24 — se añade source reconciliation como gate P0 tras medir drift en
  las 14 skills; no cambia el orden, lo hace seguro.
- 2026-07-24 — el usuario exige que todo conocimiento reunido permanezca también
  en Obsidian y en las skills aplicables; se añade A9 y ADR 002.
- 2026-07-24 — aprobados tres deltas post-Fase 01: B8 para
  `dayz-api-index` v2 sin bloquear UI, E4/B6 con postconditions/cache/publicación
  transaccional y G5 con dayz-labs solo como companion pineado sin lifecycle.
- 2026-07-25 — aprobadas las enmiendas de Fase 02: determinismo semántico
  cross-run y raster solo dentro de perfil fijado; snapshot ingame estructurado;
  sonda first-party vanilla-first sin Dabs obligatorio; schema
  `engine-capture-v1` ahora y adapter MCP run-bound/lossless en Fase 05.
  `py3d` queda fuera de esta ejecución y continúa en paralelo bajo Fase 04.
- 2026-07-26 — B3 se parte en B3a/B3b tras medir que el catálogo mecánico no
  compara contra baseline; aprobado por el usuario. Aplicado el 2026-07-27:
  `evals/schema.json:104-114,138-140` exige `response` como campo del propio caso
  y `packctl/gate.py:262-274` compara ese veredicto fijado contra las aserciones
  del mismo archivo, así que los 18/18 miden coherencia del catálogo, no eficacia
  de una skill. B3a conserva el texto original con esa reserva escrita; B3b queda
  en `❓` hasta que un run real lo demuestre.
- 2026-07-25 — cerrada Fase 04: F1–F5 pasan el gate limpio; py3d 1.4.0,
  RTM/SEAnim estricto, preflight MLOD y lector ODOL v53–v55 se distribuyen
  desde Git con fixtures y procedencia verificadas. El rollout a instalaciones
  activas queda separado y requiere autorización final.

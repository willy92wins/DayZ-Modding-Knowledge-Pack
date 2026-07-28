# Feature Spec: `dayz-persistence`

**Mod / PBO**: `dayz-persistence` skill + first-party simulators/fixtures (`tests/persistence/`)
**Date**: 2026-07-28
**Status**: Ready-to-implement
**Plan**: `plans/2026-07-24-03-dayz-persistence.md`
**DPF trace**: D1–D5 (`product-spec.md:87-91`)

## Context / Why

El pack no tiene hoy ninguna skill de persistencia, y las tres notas que la
rozan tratan «guardar estado» como un solo mecanismo. No lo es: el stream de
entidad vanilla, CF ModStorage y los archivos/sidecars tienen framing, unidad de
versión, modo de fallo y ruta de recuperación **distintos**, y presentar uno como
sustituto universal es el camino corto a la corrupción silenciosa. Esta feature
cierra D1–D5 con tres contratos separados, una matriz de migración de siete
celdas y fault injection en cada frontera I/O.

Fase **offline pura**: sin engine, sin MCP y sin login. Todo lo que aquí se
declara verde se mide con simuladores first-party y con lectura de fuente del
build fijado. Lo que solo un engine puede probar queda marcado como tal y se
delega al ciclo R5 del mod consumidor; no se declara cerrado aquí.

Aliases de evidencia: `VANILLA` = scripts DayZ del build fijado
`1.29.0.163451` (`compatibility-matrix.md:42-43`); `CF_ROOT` = árbol
`CommunityFramework` de Community Framework, idéntico byte a byte en los tres
checkouts locales (SHA-256 `4B37540E…` sobre `ModStorage/CF_ModStorageObject.c`);
`LFVS_SOURCE` = mod privado de almacenamiento virtual, usado solo como patrón
depersonalizado; `VAULT` = memoria privada no distribuible.

## Acceptance Scenarios

Cada escenario trae su repro **offline** (la que cierra el criterio en esta fase)
y, cuando la afirmación solo la puede probar el engine, la repro **in-game** que
el mod consumidor debe ejecutar en su batch R5. Las repros in-game se declaran
explícitamente **no ejecutadas en esta fase**.

1. **Given** un ejemplo que guarda estado de mod en el stream de entidad vanilla
   sin CF, **When** se pide a la skill el contrato aplicable, **Then** el router
   devuelve el contrato de stream vanilla, cita `OnStoreSave`/`OnStoreLoad` con
   `path:line`, y ningún ejemplo del pack presenta ese mecanismo como válido para
   datos de otro mod que pueda desinstalarse.
   - **Repro offline**: ejecutar el router sobre las tres entradas del corpus
     (dato propio en entidad propia / dato propio en entidad ajena / dato que
     sobrevive a la desinstalación) y comparar contra el verdict esperado.
   - **Repro in-game (consumidor, no ejecutada aquí)**: spawnear la entidad,
     escribir un valor, reiniciar el servidor y leerlo; confirmar en RPT que no
     hay `OnStoreLoad` fallido.

2. **Given** una entidad cuyo `super.OnStoreSave` escribe un número de campos
   **dependiente del estado runtime**, **When** una subclase lee tras `super` en
   `OnStoreLoad`, **Then** la skill exige que la subclase no asuma offset fijo y
   la fixture demuestra el desalineamiento cuando se asume.
   - **Repro offline**: simulador de stream con `m_EM` presente y ausente; la
     fixture «offset fijo» falla y la fixture «lectura secuencial tras super
     verdadero» pasa.
   - **Repro in-game (consumidor, no ejecutada aquí)**: colocar una entidad con
     y otra sin componente de energía, reiniciar y comparar los valores leídos.

3. **Given** un mod que guarda por CF ModStorage y luego se desinstala,
   **When** el servidor guarda de nuevo las entidades afectadas, **Then** los
   bytes del mod ausente se reemiten intactos y un reinstalar posterior los lee.
   - **Repro offline**: simulador CF con tres mods, desinstalar el segundo,
     ciclo save→load→save→load y comparar byte a byte el bloque del ausente.
   - **Repro in-game (consumidor, no ejecutada aquí)**: quitar el mod del
     `-mod=`, arrancar, guardar, volver a añadirlo y confirmar el dato.

4. **Given** las siete celdas de la matriz de migración, **When** el lector de
   referencia procesa cada fixture, **Then** cada celda produce verdict, bytes
   consumidos, estado preservado y acción **deterministas**, y ninguna acepta una
   lectura parcial como válida.
   - **Repro offline**: ejecutar la matriz completa; assert por celda sobre las
     cuatro columnas; mutar un byte de cada fixture y confirmar que el verdict
     cambia (mutation check, no tautología).

5. **Given** una versión de datos **futura** sin contrato explícito, **When** el
   lector la encuentra, **Then** rechaza fail-closed, conserva el archivo, emite
   un log rate-limited y no escribe nada encima.
   - **Repro offline**: fixture `future-version`; assert verdict `reject`,
     archivo intacto por hash antes/después, y exactamente una línea de log por
     ventana.

6. **Given** un sidecar y un fallo inyectado en **cada** frontera I/O
   (open/read/parse/backup/temp-write/temp-verify/replace), **When** el flujo
   corre, **Then** en toda frontera el original queda intacto **o** existe
   evidencia recuperable con nombre determinista; ninguna deja pérdida
   silenciosa.
   - **Repro offline**: simulador de FS con inyección por frontera; assert de la
     tabla de invariantes por punto de fallo, incluida la ventana en la que el
     destino no existe.

7. **Given** un `.tmp` huérfano de una ejecución anterior, **When** arranca el
   flujo, **Then** la política declarada (promover o descartar) se aplica de
   forma determinista y se justifica por su verificación, nunca por su mtime.
   - **Repro offline**: fixtures de huérfano válido y huérfano truncado; assert
     de que el truncado nunca se promueve.

8. **Given** un eval que pide «cargar un JSON de config de mi mod», **When** la
   respuesta propone `JsonLoadFile`, **Then** el eval **falla**, y solo pasa si
   propone `JsonFileLoader<T>.LoadFile` comprobando su `bool` y su
   `errorMessage`.
   - **Repro offline**: eval harness sobre el caso negativo y el positivo.

9. **Given** un eval que pide versionar el formato de guardado de un mod,
   **When** la respuesta usa el build de DayZ como única versión del mod,
   **Then** el eval falla; solo pasa si versiona el mod por su propio header o
   por `storageVersion` de `CfgMods`.
   - **Repro offline**: eval harness; el caso positivo debe citar la cadena
     `CfgMods … storageVersion` → `GetStorageVersion()` → `GetVersion()`.

10. **Given** una propuesta de cambio de formato persistente, **When** se aplica
    el checklist D5, **Then** exige lectura legacy, comportamiento declarado del
    lector viejo ante datos nuevos (rollback) y **una alternativa que no cambia
    el formato, presentada primero**; sin las tres, el checklist falla.
    - **Repro offline**: checklist ejecutado sobre una propuesta completa
      (pasa) y sobre tres propuestas cada una a la que le falta un elemento
      (fallan, una por elemento).

## Success Criteria

- **SC-001 / D1 separación**: existen tres documentos de contrato y **tres
  suites de fixtures que no comparten simulador**; ningún ejemplo del pack
  presenta un mecanismo como sustituto universal de otro.
- **SC-002 / D1 router**: el router devuelve un contrato único y determinista
  para cada una de las entradas del corpus de decisión; entrada ambigua devuelve
  `needs_clarification`, nunca un contrato por defecto.
- **SC-003 / D1 stream de anchura variable**: la fixture que asume offset fijo
  tras `super.OnStoreSave` falla y la que lee secuencialmente pasa; ambas sobre
  el mismo simulador.
- **SC-004 / D2 matriz**: `7/7` celdas —`fresh`, `legacy-no-header`,
  `known-version`, `future-version`, `truncated`, `same-dayz-build-new-mod-version`,
  `rollback-old-reader`— con verdict, bytes consumidos, estado preservado y
  acción declarados y asertados.
- **SC-005 / D2 no-tautología**: mutar un byte de cada fixture cambia su verdict
  en `7/7` casos; error exactamente `0` sin mutación no se acepta como prueba.
- **SC-006 / D2 future fail-closed**: `future-version` produce verdict `reject`,
  hash del archivo idéntico antes y después, y `≤1` línea de log por ventana.
- **SC-007 / D2 parcial**: `truncated` nunca produce verdict `ok`; el estado
  parcial leído se descarta entero, no se aplica a medias.
- **SC-008 / D3 fronteras**: `7/7` fronteras I/O tienen fixture de fallo
  inyectado y assert de «original intacto **o** evidencia recuperable».
- **SC-009 / D3 ventana de replace**: el contrato documenta explícitamente que
  DayZ **no expone rename/move** y que el replace es `DeleteFile` + `CopyFile`,
  con la ventana en la que el destino no existe, y la fixture la ejercita.
- **SC-010 / D3 verify post-copy**: la fixture de copia truncada es detectada
  por el verify posterior y **no** se borra el `.tmp` en ese camino.
- **SC-011 / D3 huérfanos**: `.tmp` huérfano válido y truncado producen acciones
  distintas y deterministas; el truncado nunca se promueve.
- **SC-012 / D4 deprecated**: el eval de `JsonLoadFile` falla el caso negativo y
  pasa el positivo, y ningún ejemplo del pack usa la API deprecated.
- **SC-013 / D4 versión de mod**: el eval rechaza versionar solo por build DayZ y
  exige la cadena `storageVersion` citada con `path:line`.
- **SC-014 / D4 grader honesto**: ningún token de `contains_all` aparece en el
  enunciado de su propio caso.
- **SC-015 / D5 checklist**: el checklist falla exactamente una vez por cada
  elemento ausente (legacy, rollback, alternativa sin cambio de formato) y pasa
  con los tres.
- **SC-016 / D5 auditoría**: `rigorous-data-audit` sobre ejemplos y simuladores
  cierra **sin hallazgos bloqueantes**; los no bloqueantes quedan registrados.
- **SC-017 / cierre de fase**: `packctl validate` exit `0` con `0` findings,
  `python -m pytest -q` sin retroceder desde `699 passed / 18 skipped`, y
  `promote --check` medido sobre el árbol en el momento del cierre.

## Scope — Out of scope

- Ejecutar DayZ, DayZDiag, MCP o cualquier eval vivo: la fase es offline pura.
- Declarar `runtime_verified` cualquier fila de la matriz de compatibilidad.
- Modificar `py3d`, el rollout de Fase 04, o cualquier cosa de Fase 02.
- Copiar código, rutas, ids o datos de `LFVS_SOURCE`/`LFPG_SOURCE` al pack: solo
  entra el patrón depersonalizado.
- Copiar código de Community Framework al pack; se cita, no se redistribuye.
- Escribir un motor de migración genérico: la skill entrega contratos, matriz y
  fixtures, no una librería de runtime.
- Cerrar `B3b` o cualquier criterio que exija runner autenticado.
- Prometer atomicidad real de reemplazo en disco: DayZ no la ofrece y el
  contrato debe decirlo, no simularla.

## Assumptions

- **ASSUMED — resuelta antes de escribir el contrato CF**: el árbol CF local es
  el que describe el contrato. Resuelta midiendo: los tres checkouts locales de
  `CF_ModStorageObject.c` son byte-idénticos (SHA-256 `4B37540E…`), así que no
  hay ambigüedad de qué CF se cita. **Sigue abierto** el commit upstream exacto:
  no hay `.git` en los checkouts, así que el contrato se ancla a
  `CF_ModStorage.VERSION = 5` (`CF_ROOT/ModStorage/CF_ModStorage.c:9`) y a los
  tres umbrales de `:11-14`, que son observables y falsables, en vez de a un SHA
  que no puedo probar.
- **ASSUMED — deferred, no decide código**: `CopyFile` puede truncar en
  silencio. El pack no lo demuestra desde su propio código; lo trata como
  **posible** y por eso exige verify post-copy. El patrón depersonalizado
  proviene de un mod de producción que añadió ese verify por esa razón. La
  fixture inyecta la truncación en el simulador, no la observa en el FS real.
- **ASSUMED — deferred al consumidor**: el orden en que el engine llama
  `OnStoreSave` sobre entidades anidadas. La skill no lo afirma; la matriz solo
  cubre el stream de **una** entidad.
- **ASSUMED — deferred**: que `ReadFile` con `READ_FILE_LENGTH = 100000000`
  (`VANILLA/3_game/tools/jsonfileloader.c:3`) sea suficiente para cualquier
  sidecar razonable. Se documenta el límite; no se propone superarlo.

## Forward Contract (R8-extended)

Cada símbolo que la skill, sus fixtures o el mod consumidor leen. Verificado
`path:line` contra el build fijado el 2026-07-28.

| Consumer | Symbol it reads | Kind | Verify status |
|---|---|---|---|
| contrato stream | `EntityAI.OnStoreSave(ParamsWriteContext)` | vanilla hook | `[EXACT] VANILLA/3_game/entities/entityai.c:2925` |
| contrato stream | `EntityAI.OnStoreLoad(ParamsReadContext, int)` → `bool` | vanilla hook | `[EXACT] VANILLA/3_game/entities/entityai.c:2989` |
| contrato stream | propagación `super` + `return false` ante `ctx.Read` fallido | vanilla doc contract | `[EXACT] VANILLA/3_game/entities/entityai.c:2969-2985` |
| fixture anchura variable | escritura condicional a `m_EM` (9 campos o ninguno) | vanilla behaviour | `[EXACT] VANILLA/3_game/entities/entityai.c:2928-2959` |
| contrato stream | `g_Game.SaveVersion()` | vanilla API | `[EXACT] VANILLA/3_game/global/game.c:434` |
| contrato stream | idiom `GetStorageVersion()` por subsistema | vanilla pattern | `[EXACT] VANILLA/4_world/classes/playerstomach.c:255`; `.../playermodifiers/modifiersmanager.c:170` |
| contrato CF | `CF_ModStorageObject.OnStoreSave` framing (`VERSION`, count, streams) | CF contract | `[EXACT] CF_ROOT/ModStorage/CF_ModStorageObject.c:46,62,64-71` |
| contrato CF | reemisión de mods descargados | CF contract | `[EXACT] CF_ROOT/ModStorage/CF_ModStorageObject.c:73-77` |
| contrato CF | corte por versión de juego `< 116` → `true` | CF contract | `[EXACT] CF_ROOT/ModStorage/CF_ModStorageObject.c:90-93` |
| contrato CF | corte por `cf_version < 2` → `true` | CF contract | `[EXACT] CF_ROOT/ModStorage/CF_ModStorageObject.c:121-124` |
| contrato CF | lectura fallida → `FormatError` + `false` | CF contract | `[EXACT] CF_ROOT/ModStorage/CF_ModStorageObject.c:109-113,127-131` |
| contrato CF | lectura parcial `modsRead < numMods` → `false` | CF contract | `[EXACT] CF_ROOT/ModStorage/CF_ModStorageObject.c:149-150` |
| contrato CF | `CF_ModStorage.VERSION = 5` | CF constant | `[EXACT] CF_ROOT/ModStorage/CF_ModStorage.c:9` |
| contrato CF | umbrales `116` / `141` / `2` | CF constants | `[EXACT] CF_ROOT/ModStorage/CF_ModStorage.c:11,12,14` |
| contrato CF | `CF_ModStorage.GetVersion()` → `m_Version` | CF API | `[EXACT] CF_ROOT/ModStorage/CF_ModStorage.c:41-44` |
| contrato CF | `m_Version = m_Mod.GetStorageVersion()` | CF wiring | `[EXACT] CF_ROOT/ModStorage/CF_ModStorage.c:274` |
| contrato CF | `CfgMods … storageVersion` → `SetStorageVersion` | config→código | `[EXACT] CF_ROOT/Mods/ModStructure.c:61-63,307` |
| contrato CF | hooks `CF_OnStoreSave` / `CF_OnStoreLoad` | CF hooks | `[EXACT] CF_ROOT/Entities/ItemBase.c:42-44,84-87` |
| contrato sidecar | `JsonFileLoader<T>.LoadFile(string, out T, out string)` → `bool` | vanilla API | `[EXACT] VANILLA/3_game/tools/jsonfileloader.c:7-40` |
| eval D4 negativo | `JsonLoadFile(string, out T)`, deprecated, sin retorno | vanilla API | `[EXACT] VANILLA/3_game/tools/jsonfileloader.c:99-131` |
| contrato sidecar | `FileExist` / `OpenFile` / `ReadFile` / `CloseFile` | vanilla API | `[EXACT] VANILLA/1_core/proto/ensystem.c:397,417,425,443` |
| contrato sidecar | `FPrint` / `FGets` / `MakeDirectory` | vanilla API | `[EXACT] VANILLA/1_core/proto/ensystem.c:462,501,525` |
| contrato sidecar | `DeleteFile` / `CopyFile` | vanilla API | `[EXACT] VANILLA/1_core/proto/ensystem.c:528,531` |
| contrato sidecar | **ausencia** de primitiva rename/move | vanilla negative | `[EXACT] VANILLA/1_core/proto/ensystem.c` — grep de `Rename\|MoveFile` sobre `1_core` devuelve `0` hits |
| contrato sidecar | secuencia depersonalizada temp→rotate→delete→copy→verify→sidecar→delete-tmp | patrón de producción | `[EXACT] LFVS_SOURCE/Scripts/4_World/LFV_FileStorage.c:28-45` |
| contrato sidecar | verify post-copy porque `CopyFile` puede truncar | patrón de producción | `[EXACT] LFVS_SOURCE/Scripts/4_World/LFV_FileStorage.c:998-1009,1281-1282` |
| skill `dayz-persistence` | `SKILL.md` frontmatter `description` ≤1024 | pack rule | `[DESIGN]` — gate en el check `skills` de `packctl validate` |
| `tests/persistence/` | simuladores stream / CF / sidecar | new first-party contract | `[DESIGN] este spec SC-001..SC-011; se crean antes que cualquier consumidor` |
| evals harness | `evals/evals.json` de la skill | existing contract | `[DESIGN] este spec SC-012..SC-014` |

Ningún símbolo requerido por la primera slice queda `[UNVERIFIED]`. Los
`[DESIGN]` son artefactos que esta fase **crea**; su existencia es gate del
Analyze Gate antes de que ningún consumidor los lea.

## Los tres contratos (resumen normativo)

**1. Stream de entidad vanilla.** Unidad de versión = build de DayZ
(`SaveVersion()`, `int version` del hook). Orden y anchura: lo que escribe
`OnStoreSave` en el orden exacto en que lo lee `OnStoreLoad`; **la anchura puede
depender del estado runtime** (`entityai.c:2928-2959`), así que leer por offset
fijo tras `super` es un bug latente. Fallo de lectura → `return false`
propagado, nunca estado parcial aceptado. Límite del mecanismo: los bytes viven
en la entidad; si el mod desaparece, nadie los reemite.

**2. CF ModStorage.** Unidad de versión = **el mod**, vía
`CfgMods … storageVersion` → `ModStructure.GetStorageVersion()` →
`CF_ModStorage.GetVersion()`. Framing propio: `CF_ModStorage.VERSION`, cuenta de
mods con datos, y un stream por mod. Su propiedad diferencial —la que ningún
otro mecanismo da— es que **reemite intactos los bytes de mods descargados**
(`:73-77`), de modo que desinstalar y reinstalar no pierde el dato. Tres cortes
de compatibilidad explícitos: `< 116`, `>= 141` y `< 2`.

**3. Archivos / sidecars.** Unidad de versión = header propio del archivo.
Primitivas disponibles: `FileExist`, `OpenFile`, `ReadFile`, `FGets`, `FPrint`,
`CloseFile`, `MakeDirectory`, `DeleteFile`, `CopyFile`. **No hay rename ni
move**, luego «temp→verify→replace» no es atómico: el replace real es
`DeleteFile(dest)` seguido de `CopyFile(tmp, dest)`, con una ventana en la que
el destino no existe. De ahí las tres exigencias del contrato: backup antes del
replace, verify **después** de la copia, y borrado del `.tmp` **solo** cuando el
verify pasa.

**Router.** Dato propio en entidad propia y que no debe sobrevivir a la
desinstalación → stream vanilla. Dato de mod que debe sobrevivir a la
desinstalación o vive en entidad de otro → CF ModStorage. Dato que no pertenece
a ninguna entidad, o que un admin debe poder inspeccionar/reparar fuera del
juego → sidecar. Entrada ambigua → `needs_clarification`.

## Matriz de migración (7 celdas)

| Caso | Verdict | Bytes consumidos | Estado preservado | Acción |
|---|---|---|---|---|
| `fresh` | `ok` | `0` | defaults | escribir header actual |
| `legacy-no-header` | `ok_legacy` | todos los del formato viejo | migrado completo | leer legacy, escribir nuevo tras backup |
| `known-version` | `ok` | los declarados por el header | completo | ninguna |
| `future-version` | `reject` | `0` | intacto | no escribir; log rate-limited |
| `truncated` | `reject` | `0` aplicados | intacto | no aplicar parcial; conservar evidencia |
| `same-dayz-build-new-mod-version` | `ok_migrate` | los del header viejo | migrado | migrar por versión de **mod**, no de build |
| `rollback-old-reader` | `reject_forward` | `0` | intacto | lector viejo declara y rechaza; no borra |

Regla transversal: `reject` nunca escribe. Un verdict de `0.000` de error sin
mutation check no se acepta como prueba (`G3`).

## Fronteras I/O y fault injection (D3)

| Frontera | Fallo inyectado | Invariante exigida |
|---|---|---|
| open (lectura) | handle `0` | original intacto; no se crea nada |
| read | corte a mitad | no se aplica estado parcial |
| parse | JSON inválido / schema ajeno | original intacto; evidencia conservada |
| backup / rotate | rotate falla | **no** continuar al replace |
| temp-write | `FPrint` falla / disco lleno | `.tmp` descartable; original intacto |
| temp-verify | header no reproduce | `.tmp` **conservado** como evidencia |
| replace | falla entre `DeleteFile` y `CopyFile` | destino ausente pero `.tmp` y backup presentes → recuperable |
| post-copy verify | copia truncada | destino borrado, `.tmp` **no** borrado |
| orphan `.tmp` | huérfano válido / truncado | promover solo si verifica; nunca por mtime |

## Observability

- Verdict, bytes consumidos, versión leída y versión esperada en cada resultado.
- Log rate-limited: `≤1` línea por ventana y caso, con la razón, no el volcado.
- Vocabulario de severidad exacto: `crash`, `exception`, `corruption`,
  `degradation`, `cosmetic`. Un rechazo fail-closed **no** es corruption.
- Ningún log incluye ruta privada, id de jugador ni nombre de archivo de usuario.

## Verification Plan

| Criterion | Verification | Where |
|---|---|---|
| SC-001 | inventario de contratos y suites; assert de no compartir simulador | offline |
| SC-002 | tabla de decisión del router sobre el corpus | offline |
| SC-003 | dos fixtures sobre el simulador de stream | offline |
| SC-004 | matriz completa, assert de las cuatro columnas por celda | offline |
| SC-005 | mutation check por celda | offline |
| SC-006 | hash del archivo antes/después + contador de log | offline |
| SC-007 | assert de que `truncated` no produce `ok` | offline |
| SC-008 | 7 fixtures de inyección, una por frontera | offline |
| SC-009 | grep negativo de rename/move + fixture de la ventana | offline |
| SC-010 | fixture de copia truncada; assert de `.tmp` conservado | offline |
| SC-011 | fixtures de huérfano válido/truncado | offline |
| SC-012 | eval harness negativo + positivo | offline |
| SC-013 | eval harness; assert de la cadena `storageVersion` | offline |
| SC-014 | test de solape token↔enunciado sobre todos los casos nuevos | offline |
| SC-015 | checklist sobre 1 propuesta completa + 3 incompletas | offline |
| SC-016 | `rigorous-data-audit` (`DZ-R9`) sobre ejemplos y simuladores | offline |
| SC-017 | `packctl validate`, `pytest -q`, `promote --check` | offline |

Ningún criterio de esta fase depende de un ciclo in-game. Las repros in-game de
los escenarios pertenecen al mod consumidor y quedan **no ejecutadas** aquí, por
diseño.

## Implementation Slices

1. Este spec + checklist (gate).
2. Tres contratos en `references/` + router, con las citas de la tabla.
3. Simuladores independientes: stream, CF, sidecar.
4. Matriz de migración + mutation check.
5. Fault injection por frontera.
6. `SKILL.md` + evals D4 + test anti-tautología de graders.
7. `rigorous-data-audit` y remediación hasta cero bloqueante.
8. Nota de vault, `product-spec` solo donde se midió, promoción y cierre.

Cada slice termina con `git add` → `packctl validate` → `pytest -q` verdes antes
de la siguiente. Ninguna slice posterior empieza con una anterior en rojo.

## Open Questions / NEEDS CLARIFICATION

Ninguna decisión de producto pendiente. Un dato que no pude probar y queda
declarado como límite, no como pregunta: **no existe checkout de CF con `.git`
en esta máquina**, así que el contrato CF se ancla a constantes observables
(`VERSION = 5` y los tres umbrales) en lugar de a un commit exacto. Si más
adelante aparece un checkout con historial, el ancla se endurece sin cambiar
ninguna afirmación.

## Spec Quality Checklist

- [x] CHK001 Cada Success Criterion es medible: todos expresan conteo, verdict,
  hash o exit code comprobable por una aserción.
- [x] CHK002 Ningún adjetivo vago actúa como criterio; «fail-closed» está
  definido por su invariante en la tabla de fronteras.
- [x] CHK003 Los criterios numéricos llevan unidad y umbral: `7/7` celdas, `7/7`
  fronteras, `≤1` línea de log, `0` findings, `699 passed / 18 skipped`, `≤1024`
  caracteres de `description`.
- [x] CHK004 Los diez escenarios son Given/When/Then con repro concreta; la
  repro offline es la que cierra el criterio y la in-game se declara del
  consumidor y no ejecutada.
- [x] CHK005 Cada criterio y escenario tiene ruta de verificación en la tabla
  Verification Plan.
- [x] CHK006 Los `17/17` criterios están marcados `offline`: la fase no gasta
  ningún ciclo in-game (`DZ-R5`).
- [x] CHK007 Las cuatro suposiciones están marcadas `ASSUMED`.
- [x] CHK008 La única que decidía corrección —qué árbol CF se cita— se resolvió
  midiendo (tres checkouts byte-idénticos) y su residuo (commit exacto) se
  sustituye por un ancla falsable; las otras tres se difieren con motivo.
- [x] CHK009 No quedan placeholders de plantilla.
- [x] CHK010 Los `26` símbolos existentes del Forward Contract llevan
  `path:line`; los `3` artefactos nuevos son `[DESIGN]` con gate de creación.
- [x] CHK011 Cada API, constante y ruta citada se abrió y se leyó hoy contra el
  build `1.29.0.163451`; la ausencia de rename/move se verificó por grep con
  resultado `0`, no por memoria.
- [x] CHK012 Ningún `[UNVERIFIED]` queda del que dependa la implementación.
- [x] CHK013 Out-of-scope explícito, con ocho no-objetivos.
- [x] CHK014 Términos canónicos estables: contrato, router, matriz, frontera,
  verdict, sidecar, huérfano.
- [x] CHK015 No hay contradicción entre criterios; `reject` significa lo mismo en
  la matriz, en las fronteras y en los criterios.
- [x] CHK016 La feature es data-crítica: hay escenarios de recuperación tras
  fallo (6, 7) y de intervención fuera del juego (router → sidecar), y
  `rigorous-data-audit` es SC-016, gate de la slice 7.

**Result: 16/16 PASS.**

# Plan de cierre r21 — Fase 03, Fase 02 y triaje de los 35 criterios abiertos

> **Modo de ejecución:** sesión nocturna autónoma de Claude, con delegación a
> Codex para la implementación cuando el tramo sea de código puro (`G7`).
> **Disciplina del plan:** `AGENTS-R2` (cite-then-verify). Ninguna afirmación
> entra sin `path:line` leído en el árbol, no recordado.
> **Fecha:** 2026-07-28. **Base:** HEAD `aa9a0d1`, árbol limpio.

## 1. Por qué existe este plan

La pregunta que lo dispara fue «¿está listo para publicar?». Medido contra el
criterio de cierre del propio programa —*todos* los criterios A–H en `✓` o con
exclusión de alcance aprobada y fechada
(`plans/2026-07-24-r21-master-roadmap.md:119-122`)— la respuesta es no:
**19 de 54 criterios están en `✓` y 35 siguen en `❓`**.

Este plan no inventa trabajo nuevo. Ordena el que ya está especificado, y
resuelve tres cosas que hoy no estaban escritas en ninguna parte:

1. Qué fase posee cada uno de los 35 criterios abiertos.
2. Que **la Fase 04 no está cerrada contra su propia fila del roadmap**.
3. Que **B20 ha dejado de estar bloqueado**, lo que cambia el orden de trabajo.

## 2. Decisiones del usuario, 2026-07-28 (madrugada)

Tomadas antes de la sesión nocturna, con el usuario delante:

| # | Decisión |
|---|---|
| D1 | Orden: **Fase 03 entera primero**, luego lo offline de la Fase 02. |
| D2 | Autonomía: commits en la rama, **promociones reales autorizadas** y **fast-forward de `main` autorizado** al cerrar una fase en verde. Sigue sin haber remoto ni push. |
| D3 | Alcance: **los 22 criterios fuera de las fases 02–03 entran en el plan sin recortar**. No se propone ninguna exclusión de alcance. |
| D4 | Desbloqueos de entorno: los tres, verificados en el momento (§3). |

D3 es la decisión de mayor coste y conviene que quede explícita: se descarta un
`v1` recortado, así que **publicar exige las seis fases completas**, no un
subconjunto.

## 3. Estado del entorno, medido el 2026-07-28 ~04:20

| Desbloqueo | Estado | Evidencia |
|---|---|---|
| Identidad DayZ MCP | **resuelta** | `bridge_status`: ambos peers `version=6~1.29.163451`, `version_state=ok`, *version accepted*, poll 66-67 s, `queue_depth=0`. `session_status`: `owner=null`, `queue=[]`, `claimable=true`, sin `audit_fault` |
| DayZDiag | **arriba** | binario `…\steamapps\common\DayZ\DayZDiag_x64.exe` (build 2026-07-15) y dos procesos vivos desde 04:15:34 y 04:15:48 |
| Login del CLI `claude` | pendiente al escribir esto | llamada real → `{"is_error":true,"result":"Not logged in · Please run /login"}` |

**Consecuencia que reordena la Fase 02:** el hard stop «B20 abierto»
(`plans/2026-07-24-02-dayz-ui-lab.md:173`) y los tres items que dependían de él
—la semántica CRLF/LF de continuación contra `ButtonWidget.GetText` en DayZDiag
(`:76`, `:87-90`)— **ya son ejecutables**. Lo que estaba bloqueado desde el
2026-07-25 no lo está.

Matiz que no se debe saltar: el puente vivo prueba autorización de protocolo,
**no** que la micro-fixture de B20 pase. Eso hay que ejecutarlo y medirlo.

## 4. Triaje de los 35 criterios abiertos

Cada criterio abierto, su dueño y qué evidencia exacta lo cierra. Las líneas
citadas son de `product-spec.md`, que es donde vive la evidencia exigida.

### 4.1 Residual de Fase 01 (1 criterio)

| Criterio | Qué lo cierra | Bloqueo |
|---|---|---|
| `B3b` (`:56`) | un caso vivo `DISCRIMINATING` sobre runner real | **solo el login del CLI**. Los cinco casos ya existen en `evals/live/cases/`; el harness se ejecutó y falló limpio por `Not logged in` |

### 4.2 Fase 02 — `dayz-ui-lab`, C1–C8 (8 criterios)

Plan vigente: `plans/2026-07-24-02-dayz-ui-lab.md`. Spec:
`specs/2026-07-25-dayz-ui-lab.md`. Estado real por tarea, leído del plan:

- Task 1 — 5 de 7 items cerrados; abiertos `:76` (micro-fixture CRLF/LF) y
  `:77` (builds/hashes y licencias de los corpora).
- Task 2 — 3 de 6 cerrados; abiertos `:87-90`, `:91-92` y el gate `:95`
  (LFPG + 319/319 público + 46/46 TraderX).
- Tasks 3 a 8 — íntegramente abiertas (`:97-169`).

| Criterio | Qué lo cierra | Engine |
|---|---|---|
| `C1` (`:71`) | 319/319 + 46/46 + LFPG, 0 falso `missing-child-block`, CRLF/LF verificado en DayZDiag | **sí** (micro-fixture) |
| `C2` (`:72`) | fixture shell→subview→3 cards conserva orden/identidad en 1920×1080 y 3440×1440 | no |
| `C3` (`:73`) | dos `render.json` byte-idénticos; RGBA/PNG idénticos dentro del perfil de raster fijado; fuera, `non_canonical` | no |
| `C4` (`:74`) | fixture negativa produce exactamente los hallazgos esperados; control verde 0 | no |
| `C5` (`:75`) | manifests por commit/hash de VPP/Expansion/TraderPlus/TraderX + LFPG Sorter V4 TEST como negativo | no |
| `C6` (`:76`) | bundle `engine-capture-v1` coherente; **el import manual con DayZDiag basta**, no exige MCP | **sí** |
| `C7` (`:77`) | benchmark create/unlink vs pool, 0 estado fantasma; se admite «no adoptar» documentado | no |
| `C8` (`:78`) | evals «vacío/estilo/colección/tooltip/fuente/offline≠engine» pasan | no |

### 4.3 Fase 03 — `dayz-persistence`, D1–D5 (5 criterios)

Plan vigente: `plans/2026-07-24-03-dayz-persistence.md`, cinco tareas, **todas
abiertas**, sin spec escrita todavía. Es data-crítica por declaración propia
(`:3-4`) y exige feature spec + checklist 16/16 antes de escribir la skill
(`:45`). **Cero dependencia de engine, de MCP y de login.**

| Criterio | Qué lo cierra |
|---|---|
| `D1` (`:87`) | tres contratos separados —stream vanilla, CF ModStorage, sidecars— con tres suites de fixtures independientes |
| `D2` (`:88`) | matriz `fresh`/`legacy`/`known`/`future`/`truncated`/`same-build upgrade`/`rollback` con verdict y acción deterministas |
| `D3` (`:89`) | temp→verify→replace con fault injection en cada frontera I/O: original intacto o evidencia recuperable |
| `D4` (`:90`) | evals rechazan `JsonLoadFile` como patrón nuevo y headers ligados solo al build DayZ |
| `D5` (`:91`) | checklist legacy + rollback + alternativa sin cambio de formato, y `rigorous-data-audit` sin hallazgos bloqueantes |

### 4.4 Fase 04 — **no está cerrada**: E1–E7, B7, B8 (9 criterios)

Hallazgo de este plan. El brief afirma «r21 Fase 04 cerrada con F1–F5 en verde»
(`project-brief.md:5`), pero la fila del roadmap asigna a la Fase 04
**`E`, `F` y `B7–B8`** (`plans/2026-07-24-r21-master-roadmap.md:41`). F1–F5 sí
están en `✓`; los otros nueve no. La fase está cerrada **en su tramo py3d**, no
contra su propia fila.

| Criterio | Qué lo cierra |
|---|---|
| `B7` (`:60`) | parser de config y validadores loot/CE/physics con fixtures positivas, negativas y límites |
| `B8` (`:61`) | `dayz-api-index` v2 con liveness `active/commented/missing`, parent chain, guardas y namespace |
| `E1` (`:100`) | `dayz-multiplayer-sync`: fixtures cliente/servidor, auth fail-closed, dos clientes locales |
| `E2` (`:101`) | `dayz-sound-particles`: ejemplos fuente-pineados + smoke por subsistema |
| `E3` (`:102`) | `dayz-terrain`: proyecto mínimo reproducible + checks de roadgraph/CE |
| `E4` (`:103`) | `dayz-workshop-release`: dry-run transaccional; un fallo conserva bytes y manifest previos |
| `E5` (`:104`) | vault con RPT decision tree, arquitecturas y performance con budgets que declaran build/hardware/corpus |
| `E6` (`:105`) | disease/modifiers y plugin lifecycle auditados vanilla-first con `path:line` |
| `E7` (`:106`) | matriz de compatibilidad contra la stable fijada, con fecha verificable |

Dependencia declarada: la Fase 04 depende de «01 y 03 cuando toque persistence»
(`roadmap:41`), así que **la Fase 03 desbloquea el tramo E**, lo que confirma D1.

### 4.5 Fase 05 — MCP publicable, G1–G5 (5 criterios)

Depende de «01; UI para visual diff» (`roadmap:42`), es decir **de la Fase 02**.

| Criterio | Qué lo cierra |
|---|---|
| `G1` (`:128`) | protocolo del bridge con ejemplos request/response validados contra schema |
| `G2` (`:129`) | modo lite sin bridge privado: ladder spawn→acción→RPT/verdict |
| `G3` (`:130`) | orquestador test-ingame + MCP con watch mode incremental, lease y `run_id` fail-closed |
| `G4` (`:131`) | gates separados por capability; el adapter de screenshot importa `engine-capture-v1` y conserva PNG lossless |
| `G5` (`:132`) | matriz capability/fiabilidad/riesgo/licencia; dayz-labs pineado y sin autoridad de lifecycle |

### 4.6 Fase 06 — ecosistema y release, H1–H6 y B6 (7 criterios)

Depende de 01–05 completas (`roadmap:43`). Es la fase que produce el release.

| Criterio | Qué lo cierra |
|---|---|
| `B6` (`:59`) | template `@MyMod` que consume los mismos gates release-grade |
| `H1` (`:141`) | integración Workbench/Mikero/viewers con versiones y licencia |
| `H2` (`:142`) | entorno limpio de server reproducible en VM, elegido tras spike |
| `H3` (`:143`) | guía de contribución con una contribución fixture end-to-end |
| `H4` (`:144`) | consolidación de notas duplicadas con mapa old→canonical |
| `H5` (`:145`) | diagramas first-party de skeleton, proxy frame y Construction quartet |
| `H6` (`:146`) | risk register versionado que distingue crash/exception/corruption/degradation/cosmetic |

### 4.7 Recuento

| Dueño | Criterios abiertos |
|---|---|
| Fase 01 residual | 1 (`B3b`) |
| Fase 02 | 8 |
| Fase 03 | 5 |
| Fase 04 (tramo no cerrado) | 9 |
| Fase 05 | 5 |
| Fase 06 | 7 |
| **Total** | **35** |

## 5. Secuencia de la sesión nocturna

### Bloque N1 — Fase 03 completa (prioridad, offline)

Ejecutar `plans/2026-07-24-03-dayz-persistence.md` en su orden, con dos gates
propios del pack antes de cada commit: `git add` y **después** `packctl validate`
(PASS, 0 findings) y `python -m pytest -q` (baseline **699 passed / 18 skipped**,
no retroceder).

1. **N1.1 — feature spec + checklist.** El plan exige cerrar spec y checklist
   16/16 antes de escribir la skill (`:45`). Destino: `specs/2026-07-28-dayz-persistence.md`.
   Skill a invocar: `dayz-feature-spec`.
2. **N1.2 — research source-first** (`:37-45`). Revalidar contra el build fijado
   las cuatro referencias de partida que el plan ya trae (`:28-35`):
   `EntityAI.OnStoreSave/OnStoreLoad`, `JsonFileLoader<T>.LoadFile`,
   `storageVersion`/`ctx.GetVersion()` y el framing de `CF_ModStorageObject`.
   **Son baseline, no un pase eterno** (`:39-40`): si una firma no se reproduce
   hoy, se corrige la cita, no se hereda.
3. **N1.3 — tres contratos** (`:47-55`) con router por tipo de dato/ownership.
4. **N1.4 — matriz de migración** (`:57-66`), siete fixtures, cada celda con
   verdict determinista.
5. **N1.5 — fault injection de sidecars** (`:68-74`) en cada frontera I/O.
6. **N1.6 — skill, evals y auditoría** (`:76-86`), incluido `rigorous-data-audit`
   (`DZ-R9`) sobre ejemplos y simuladores.
7. **N1.7 — promoción** de `dayz-persistence` con readback por hash. Autorizada
   por D2; el árbol debe estar limpio y el gate medido en el momento.

### Bloque N2 — Fase 02, tramo hoy ejecutable

Solo si N1 cierra o queda en un punto de parada limpio.

1. **N2.1 — B20**, que ya no está bloqueado: micro-fixture de continuación
   CRLF/LF observada con `ButtonWidget.GetText` en DayZDiag (`:76`, `:87-90`).
   Protocolo `dayz-mcp`: adquirir lease antes de mutar, liberarlo al terminar,
   nunca matar procesos DayZ a mano.
2. **N2.2 — gate C1** (`:95`): LFPG + 319/319 público + 46/46 TraderX, exit 0.
3. **N2.3 — corpora** (`:77`): fijar builds, hashes y licencias.
4. **N2.4 en adelante** — Tasks 3-5 del plan de fase (escenarios, render
   determinista, diff), todas offline.

### Fuera del alcance de la noche

Fases 04 (tramo E), 05 y 06. Entran en el plan por D3 y se calendarizan después
de que 02 y 03 estén en verde, respetando las dependencias del roadmap.

## 6. Envolvente de autonomía

**Autorizado** (D2): commitear en `r21/phase01-foundation` cuantas veces haga
falta; `promote --apply` con el gate verde, backup fuera del árbol gestionado y
readback independiente; fast-forward de `main` al cerrar una fase en verde.

**Sigue prohibido, sin cambio:** `push` (no hay remoto), tocar `P:\py3d`, copiar
el backend ODOL, añadir writer ODOL, y re-baselinar hashes sellados sin decisión
explícita.

**Regla de convivencia, aprendida hoy:** el destino lo escriben otras sesiones.
Adoptar protege el conocimiento y es barato; adjudicar caduca. Antes de firmar
una adjudicación, exigir quietud verificada del destino y igualdad byte a byte
con el repo (`LL-216`, refuerzo 2026-07-28).

## 7. Hard stops

Se heredan los de cada plan de fase (`03:88-97`, `02:171-185`) y se añaden dos:

- **No declarar un criterio `✓` sin ejecutar su línea de evidencia.** La tabla
  del §4 dice exactamente qué mide cada uno; el `✓` se escribe después de
  medirlo, no antes.
- **No declarar «Fase 04 cerrada» mientras E1–E7, B7 y B8 sigan abiertos.**
  Corregir esa afirmación en `project-brief.md:5` forma parte del cierre.

## 8. Definición de terminado de este plan

1. `D1–D5` en `✓` con su evidencia ejecutada.
2. El tramo hoy ejecutable de la Fase 02 avanzado, y B20 medido —pase o falle—
   en lugar de seguir bloqueado.
3. `product-spec.md` actualizado solo donde se haya medido.
4. `project-brief.md:5` corregido respecto al alcance real de la Fase 04.
5. Suite, `validate` y `promote --check` verdes al cerrar, medidos sobre el
   árbol y no leídos de un informe.

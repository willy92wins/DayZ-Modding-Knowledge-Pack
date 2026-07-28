# HANDOFF — DayZ Modding Knowledge Pack

<!-- LIVE-STATE:START -->
# DayZ Modding Knowledge Pack — Estado vivo · snapshot 2026-07-28 (madrugada)

**Última verificación real:** HEAD `b015972` en `r21/phase01-foundation`, árbol
limpio, `main` intacto en `994cb77`, sin remoto. Suite **698 passed / 18
skipped**, `packctl validate` PASS con cero findings, `packctl promote --check`
**`WARN` con exit 0** y finding único `PROMOTION-DRIFT operation_count=38`, plan
escrito. Todo medido sobre el árbol, no leído de informes.

**Promoción real ejecutada** (tx `6591ddab82a8162e1550f4c8` sobre `0e35ba9`, PASS,
54 operaciones, 141 eventos terminando en `COMMIT`), autorizada explícitamente.
Readback independiente: 162 ficheros antes y después, **0 perdidos**, 16 cambiados
—los 8 `SKILL.md` adoptados × 2 raíces— y los 162 proyectados coinciden con el repo.
El drift bajó de 46 a 38: las 38 restantes son **todas** de `obsidian_snapshots`
con `before_digest: absent`, que es estructural. Cero operaciones de skill con
drift; las dos raíces están sincronizadas y ya sin la asimetría CRLF/LF.

`ciclos_en_este_objetivo: 1 (deuda de promoción y hardening de Fase 04)`

## Cerrado en esta sesión (9 commits)

- **Quién escribe en las skills instaladas — RESUELTO. No es el harness.** Son
  dos sesiones concurrentes de Claude Code del propio usuario, promoviendo
  lecciones. Atribuido por tres vías: transcripciones de sesión con el texto
  literal, notas de memoria automática escritas 31 y 35 s después de cada
  escritura, y cada `LL-NNN` citado resuelve en el corpus del vault.
- **`7e437f0`** — adopción de los 8 artefactos que solo vivían en las instaladas
  (+227 líneas, 0 borrados). **`7556555`** — 22 adjudicaciones, digests releídos
  del check. **`f641c96`** — tercera tanda de `dayz-vehicles` adoptada y
  re-adjudicada.
- **`982dae6`** — BUG-021 y BUG-022 cerrados. **`4271ff0`** — MEN-1, MEN-5, MEN-6
  y el test de involución. **`98421b3`** — MEN-2, MEN-3, MEN-4 con round-trip por
  bytes sobre todo el corpus.
- **BUG-020 verificado de forma independiente**: `_latest_receipt_digests` sobre
  los 68 pares, con las 22 adjudicaciones y con el mapa vacío, da **0 findings en
  ambas pasadas** → **0 enmascarados**. Antes del fix eran 12. Y el guardarraíl
  sigue pudiendo ponerse rojo: las cuatro formas de fallo (fork, ciclo, múltiples
  preimágenes, transición duplicada) fallan cerradas **dentro** de una transacción
  y pasan **entre** dos. De los «cuatro tests invertidos» del mensaje de `ac21d13`,
  solo dos lo fueron; los otros dos siguen fallando cerrados.
- **`0e35ba9`** — el gate de preimagen comprueba **todos** los ids lógicos, no solo
  `[0]`. Y **retira la deuda que lo pedía**: la afirmación de que el gate indexa por
  un artefacto de ordenación y deja adjudicaciones inertes **es falsa**, medida
  instrumentando el gate real (68 operaciones, todas con 1 id). La cifra que la
  sostenía se había medido contra el plan deduplicado. `LL-217`.
- **`b015972`** — promoción real, receipt versionado con su propia entrada de
  procedencia, verificada contra el `receipt_hash` del evento `COMMIT` terminal.

## AVISO VIGENTE — el destino muta solo, y se ha medido dos veces

Escrituras host-direct en skills del pack **tres veces el 2026-07-27** (17:38:17,
19:39:59, 23:03:24). Coste medido: 8 findings a las 19:02 → **16** a las 19:48; y
gate limpio a las 20:10 → **FAIL** a las 23:12. El conocimiento es bueno y ya está
en Git; lo que se repite es el ciclo adoptar → re-medir → re-adjudicar.

**Frontera decidida y registrada** en `decisions/decision-log.md` (entrada
«Frontera de escritura», 2026-07-27): las **15 skills del `promotion-map`** se
escriben en el repo y llegan al destino por promoción con recibo; fuera de esas
15 no hay fricción. `promote --apply` solo desde la sesión que sostiene este
worktree y con autorización explícita del usuario.

**Antes de adjudicar cualquier cosa: re-medir.** Una adjudicación autoriza un
digest concreto y caduca sola.

## Deuda sin sesión asignada

- **Rollout py3d** a las 8 skills instaladas (siguen en `py3d-1.2.0`). Requiere
  autorización explícita. **NO cae dentro de la frontera de escritura**, al
  contrario de lo que dijeron las versiones previas de este bloque: las 8 son
  `dayz-3d-viewer`, `dayz-animation-pipeline`, `dayz-model-pipeline`,
  `dayz-p3d-audit`, `dayz-p3d-debinarizer`, `dayz-p3d-inspector`, `dayz-pbo-build`
  y `dayz-proxy-align` — todas en `~\.agents\skills` y **ninguna entre las 15 del
  `promotion-map`**. Intersección cero, medida listando los `wheels\py3d-*.whl`.
  Es host-direct y no toca este gate. Lo que sí sigue vigente es BUG-018: patch-only
  con preimagen por destino y backup fuera de la raíz de destino.
- **Eval vivo contra modelo real** para sacar B3b de `❓`.
- **`reports/` acumula basura** de sesiones anteriores (venvs de pytest, tmpdirs
  con ACLs read-only). Gitignored, no contamina commits; limpieza pendiente.

## Invariantes cerradas

- Git es la única fuente editable; las instaladas son despliegues. La adopción va
  del destino al repo, nunca al revés sin gate.
- Una adjudicación autoriza **un digest concreto**, caduca sola, y **tapa, no
  arregla** — por eso se adopta ANTES de adjudicar.
- Preimagen e historial causal son **dos gates distintos**. Firmar preimágenes no
  tapa historia (medido: 0 enmascarados).
- El gate de preimagen ve **una operación por destino lógico**, con un id cada
  una: 68 medidas instrumentando el gate real. No hay adjudicación inerte, y el
  layout de junctions no puede voltear su clave. La afirmación contraria, que este
  fichero y `verified-apis.md` sostuvieron hasta el 2026-07-28, salía de medir
  contra el plan deduplicado — que no es el índice del gate.
- **Instrumentar mutando dicts ajenos exige snapshot en el momento de la
  llamada**: el dedup muta las operaciones in place después
  (`promotion.py:1702`), así que guardar referencias mide el estado equivocado.
- Ningún writer ODOL; «aislado» ahí significa subproceso, no sandbox.
- Un gate que no puede ponerse rojo no es un gate.
- Ninguna promoción real sin autorización explícita del usuario.

**Gate de arranque:** declarar `Retomo DayZ Modding Knowledge Pack desde: 98421b3
con los seis MEN y BUG-021/022 cerrados · re-medir promote --check antes de tocar
nada, porque el destino muta solo`.
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

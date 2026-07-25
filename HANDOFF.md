# HANDOFF — DayZ Modding Knowledge Pack

<!-- LIVE-STATE:START -->
# DayZ Modding Knowledge Pack — Estado vivo · snapshot 2026-07-25

**Última verificación real:** el contenido de Fase 02 slices 1–2 quedó
versionado en `9cb9b9c70208b037de457715482d70c24b19a5b9`. La suite UI pasó
10/10, el corpus público 319/319, TraderX no-B20 42/42, LFPG 7/7 y los cuatro
B20 fallaron explícitamente como se esperaba. `py_compile`, preflight DayZ y
`packctl validate` pasaron; el validator informó cero findings en sus seis
familias.

## Estado actual

- Las cuatro enmiendas UI/MCP están aprobadas e incorporadas en DPF, roadmap,
  plan y feature spec.
- B19 está cerrado: una leaf válida no produce `missing-child-block`;
  `has_child_block` permanece informativo y `strict_child_blocks` ya no existe
  en parser, API ni CLI.
- La micro-fixture `LF_UIProbe` está preparada con source first-party,
  vanilla-first y sin Dabs obligatorio. El preparador genera LF/CRLF
  byte-equivalentes fuera del árbol versionado.
- B20 sigue abierto por diseño: no se ha modificado la semántica del parser ni
  se ha codificado un valor esperado sin observación DayZDiag.
- `session_status` y `bridge_status` devolvieron `unauthorized`; no se lanzó
  DayZ por un camino alternativo.
- C1 continúa abierto y bloquea scenario/render/diff. La skill `dayz-ui` no se
  crea/promueve antes de corpus + DayZDiag.
- MCP solo será adapter de `engine-capture-v1`; no duplica lifecycle. El delta
  run-bound/lossless queda en Fase 05.
- Py3d permanece intacto y fuera de esta ejecución.
- El commit raíz histórico sigue siendo
  `d48e2c1a02dacc97645a9e70d8bc1058e6dae9a5`; la rama activa es
  `r21/phase01-foundation` y no se ha mezclado a la rama principal.

## Issues abiertos

1. **[ALTA] B20 / C1** — falta observar en DayZDiag el texto exacto de las
   variantes LF/CRLF antes de escribir tests/implementación.
2. **[ALTA] Autorización MCP** — la identidad actual recibe `unauthorized`;
   puede resolverse con una sesión autorizada o ejecución manual DayZDiag.
3. **[MEDIA] Skill UI** — repo y Obsidian ya conservan el aprendizaje; la
   tercera superficie espera el gate C1 aprobado.
4. **[MEDIA] Integración pendiente** — la rama activa todavía no se ha
   mezclado a principal.

## Próxima acción

Restaurar autorización MCP o ejecutar manualmente `LF_UIProbe` con DayZDiag;
conservar los resultados RPT LF/CRLF; fijarlos como test RED y aplicar el GREEN
mínimo B20. Después ejecutar el gate 319/319 + TraderX 46/46 + LFPG. No empezar
scenario/render/diff ni tocar py3d antes.

## Invariantes cerradas

- El ZIP anterior es solo baseline; no se modifica.
- Este Git es la única fuente editable del pack distribuible.
- Obsidian conserva evidencia/memoria completa; las skills activas reciben
  promociones verificadas desde Git tras gates.
- Ninguna invariante de dominio puede quedar únicamente en una de las tres
  superficies.
- StarDZ, dayz-labs y Lake son prior art selectivo, no dependencias del pack.
- Un cero de `dayz-api-index` v1 no prueba ausencia; se abre la fuente y se
  inspeccionan guardas hasta que B8 esté cerrado.
- Un PBO existente tras exit 0 no es un release PASS sin postconditions y
  publicación transaccional.
- dayz-labs no ejecuta `start/stop/restart` sobre runs gobernados por DayZ_MCP.
- VPP, Expansion, TraderPlus y TraderX son corpus local opcional; no se
  redistribuyen.
- `dayz-ui-lab` no depende de py3d; PAA/EDDS permanece interno al lab hasta que
  exista un segundo consumidor real.
- Una leaf `.layout` puede omitir su bloque hijo; esa ausencia no es warning ni
  error.
- `ButtonWidget.GetText(out string)` devuelve `void`; el valor sale por el
  parámetro `out`.
- B20 no se implementa hasta que DayZDiag fije el valor lógico LF/CRLF.
- MCP no posee semántica UI ni crea una segunda autoridad de lifecycle.
- Ejecución y revisión por Codex, sin Claude/subagentes, mientras siga vigente
  la instrucción del usuario.
- Los cinco intentos fallidos de promoción permanecen como evidencia terminal
  `ABORT`; no se borran backups ni journals automáticamente.

## Punteros

- `product-spec.md`
- `plans/2026-07-24-r21-master-roadmap.md`
- `plans/2026-07-24-02-dayz-ui-lab.md`
- `plans/2026-07-24-02-dayz-ui-lab.codex-notes.md`
- `specs/2026-07-25-dayz-ui-lab.md`
- `tools/dayz-ui-lab/probe/README.md`
- `plans/2026-07-24-04-py3d-and-domain-skills.md`
- `decisions/001-canonical-source-and-baseline.md`
- `decisions/002-three-surface-promotion.md`

**Gate de arranque:** declarar `Retomo DayZ Modding Knowledge Pack desde:
Fase 02 slices 1–2 cerrados · B20 espera observación DayZDiag autorizada`.
<!-- LIVE-STATE:END -->

---

## Log histórico

### 2026-07-25 — Fase 02 slices 1–2

- Se aprobaron e incorporaron las cuatro enmiendas UI/MCP.
- B19 cerró por RED→GREEN y corpus; `strict_child_blocks` fue retirado.
- Se añadió `LF_UIProbe` con staging LF/CRLF reproducible y sin expectativa B20.
- El commit de contenido es `9cb9b9c70208b037de457715482d70c24b19a5b9`.
- B20 quedó bloqueado honestamente por MCP `unauthorized`; no hubo bypass.

### 2026-07-24 — Prior art aprobado y promovido

- Se aprobaron únicamente tres deltas: API index v2 no bloqueante, build/release
  transaccional y dayz-labs como companion sin lifecycle authority.
- El commit `13af7f8b59962bca6fded981ad75cd77a37616ef` superó el gate integral.
- La transacción `51a7024ef9a5e333e5fab7b8` promovió ese commit a Obsidian y
  skills activas con readback completo y cero residuos.

### 2026-07-24 — Fase 01 cerrada

- Se cerraron A1–A9 y B1–B5 con gate reproducible y source map completo.
- La transacción `c7b5366cc761a8038e52f6a2` promovió el commit de contenido
  `7a25432febc112a957a7c1ef7a7d2c16c221b24f` a las tres superficies.
- Cinco intentos previos fallaron cerrados y terminaron en `ABORT`; sus
  hallazgos quedaron convertidos en regresiones del motor de promoción.

### 2026-07-24 — Bootstrap

- Se fijó el ZIP previo por SHA-256.
- Se extrajeron y verificaron 138 archivos sin diferencias.
- Se inicializó Git y se creó el commit raíz exacto.
- Se midió el baseline antes de planificar.

# HANDOFF — DayZ Modding Knowledge Pack

<!-- LIVE-STATE:START -->
# DayZ Modding Knowledge Pack — Estado vivo · snapshot 2026-07-27 (noche)

**Última verificación real:** HEAD `8ac8993` en `r21/phase01-foundation`, árbol
limpio, `main` intacto en `994cb77`, sin remoto. Suite **660 passed / 18
skipped**, `packctl validate` PASS con cero findings, `promote --check` en `WARN`
con exit 0. Medidos sobre el árbol, no leídos de informes.

## Lo que cambió en esta sesión

- **Promoción real ejecutada** (tx `e2aa6cf9058070bb4fbf2a8c`, `verdict=PASS`, 54
  operaciones). Readback verificado a mano: cero ficheros perdidos en el destino;
  las seis diferencias de contenido son ejecutables bajo localización de alias y
  se reproducen byte a byte aplicando el mapa a los bytes del repo.
- **Wheel re-baselinado** a `c635bf7e…`, gate verde. La reproducibilidad es
  **toolchain-bound** (`setuptools==83.0.0`, Python `3.14.3`), no propiedad del
  código, y el `product-spec` ya lo dice así.
- **Eval vivo discriminante entregado** (`8ac8993`): schema que prohíbe
  `response`, runner agnóstico de proveedor, gate que declara `VACUOUS` el caso
  que pasa sin la skill, caso semilla del cap de 93 partes y adaptador para el
  CLI de Claude Code. **No enganchado a `gate` ni `validate`** a propósito.
- **B3 partido en B3a (✓) / B3b (❓)**. B3b sigue sin evidencia y así debe quedar
  hasta que un run real lo demuestre.

## Lo siguiente, y está aprobado

**Implementar BUG-020** siguiendo el plan aprobado por el usuario:
`VAULT/AI/10_Projects/DayZ_Modding_Knowledge_Pack/plans/2026-07-27-bug020-identidad-de-ocurrencia-sellada.md`
(mover a `<repo>/plans/` al retomarlo).

Orden del plan: (1) convertir el medidor fiel en test de regresión con los tres
receipts reales de fixture — hoy debe dar **12 rotos / 0 visibles**; (2)
sustituir el `sorted` por nombre de `promotion.py:1145` por orden de
`completed_at`; (3) reescribir `_causal_receipt_head` sobre ocurrencias
`(digest, transaction_id)`; (4) **cuatro fixtures negativas obligatorias** —
fork real, preimagen múltiple, ciclo real, transición duplicada; (5) re-medir con
las adjudicaciones vaciadas: los 12 deben resolver solos.

**Hallazgo que abarata el plan:** el `transaction_id` ya viaja en cada transición
(`_sealed_receipt_transitions:1039-1049`) y el receipt no cambia de forma, así
que la ocurrencia se **deriva** al recorrer. Si eso aguanta, no hay migración de
formato, ni lectura legacy v1, ni backup de receipts — al contrario de lo que
asumía la entrada del ledger. **Cláusula de parada vigente:** si al implementarlo
aparece algo que exija *persistir* la ocurrencia, parar y re-aprobar como
migración de formato.

## Lo que hay que saber antes de tocar nada

- **`validate` sobre un fichero sin rastrear no dice nada del estado
  post-commit.** Mordió dos veces en esta sesión: con `adjudications.json` y con
  el receipt de la promoción. Ejecutar `validate` **después** de `git add`.
- **Cada receipt necesita su propia entrada de procedencia**; el artefacto de
  árbol `repo/promotions` no los cubre.
- **La comparación viva↔repo caduca.** Re-medir siempre antes de adjudicar.
- **Las adjudicaciones tapan, no arreglan.** Los 12 pares adjudicados tienen el
  historial causal roto y el gate sale verde solo porque
  `_append_scoped_receipt_finding:974-977` suprime el finding mientras la
  adjudicación iguale al digest observado.
- **`logical_target_ids` es una lista en los tres receipts.** Si se inspecciona
  con `ConvertTo-Json` de PowerShell parece una cadena; no lo es.
- `promote --check` no escribe a stdout: el informe va a
  `<plan>.check-report.json`, y el fichero `--plan` no se crea si el check falla.

## Deuda sin sesión asignada

BUG-021, BUG-022, `MEN-1`…`MEN-6`, y el rollout py3d a las 8 skills instaladas
(que siguen en `py3d-1.2.0`, dos releases por detrás; ahora ya hay wheel con
identidad verde).

## Invariantes cerradas

- Git es la única fuente editable; las skills instaladas son despliegues. La
  adopción va del destino al repo, nunca al revés sin gate.
- Una adjudicación autoriza **un digest concreto** y caduca sola.
- Ningún writer ODOL. El backend externo se fija por hash y no se redistribuye;
  «aislado» ahí significa subproceso, no sandbox.
- Un gate que no puede ponerse rojo no es un gate.
- Ninguna promoción real sin autorización explícita del usuario.

**Gate de arranque:** declarar `Retomo DayZ Modding Knowledge Pack desde: eval
vivo entregado en 8ac8993 · implementar BUG-020 con el plan aprobado`.
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

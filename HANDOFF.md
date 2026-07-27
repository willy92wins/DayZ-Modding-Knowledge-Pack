# HANDOFF — DayZ Modding Knowledge Pack

<!-- LIVE-STATE:START -->
# DayZ Modding Knowledge Pack — Estado vivo · snapshot 2026-07-27 (cierre)

**Última verificación real:** HEAD `ac21d13` en `r21/phase01-foundation`, árbol
limpio, `main` intacto en `994cb77`, sin remoto. Suite **668 passed / 18
skipped**, `packctl validate` PASS con cero findings. Medidos sobre el árbol.

## Cerrado en esta sesión

- **Promoción real ejecutada** (tx `e2aa6cf9058070bb4fbf2a8c`, PASS, 54
  operaciones). Readback verificado a mano: 0 ficheros perdidos.
- **Wheel re-baselinado** a `c635bf7e…`. Reproducibilidad **toolchain-bound**
  (`setuptools==83.0.0`, Python 3.14.3).
- **Eval vivo discriminante** entregado (`8ac8993`). B3a ✓ / B3b ❓ sin evidencia
  fabricada.
- **BUG-020 implementado** (`ac21d13`): identidad de nodo = ocurrencia sellada.
  Medición independiente: **30 resuelven, 0 rotos, 0 enmascarados** (antes
  18/12/12). No hubo migración de formato: la ocurrencia se deriva al recorrer.

## BLOQUEO VIGENTE — resolver antes de tocar promoción

`promote --check` da **FAIL con 8 `PROMOTION-TARGET-UNEXPLAINED`**. No es
regresión de BUG-020: son 4 skills (`dayz-feature-spec`, `dayz-test-ingame`,
`dayz-vehicles`, `rigorous-data-audit`) × 2 targets cuyas copias instaladas
**cambiaron de contenido a las 17:38 y 18:30 del 2026-07-27**, durante el job de
Codex de BUG-020 — que tenía alcance limitado al worktree y no debería haberlas
tocado. Mismo número de ficheros, contenido distinto.

**Sospecha NO verificada:** el propio harness de Claude Code reescribe los árboles
de skills instalados (encaja con los avisos de skills que cambiaron toda la
sesión). Si es cierto, el gate de preimagen seguirá disparándose para siempre y
hay que decidir qué hacer con esos destinos.

**NO adjudicar esos 8** hasta saber quién escribe. Adjudicar es firmar sobre un
destino que muta solo.

## Trampas que esta sesión pagó

- **`validate` sobre un fichero sin rastrear no dice nada del estado
  post-commit.** Mordió tres veces. `git add` y **después** validar.
- **Cada receipt necesita su propia entrada de procedencia**; `repo/promotions`
  no los cubre.
- **La comparación viva↔repo caduca** (la de `4d594ae` duró 10 h). Re-medir
  siempre antes de adjudicar.
- **Las copias instaladas tienen EOL mixto**: originales CRLF, secciones nuevas
  LF. Adoptar solo el bloque añadido, normalizado, no el fichero entero.
- **`logical_target_ids` es una lista en los tres receipts**; `ConvertTo-Json` de
  PowerShell la muestra como cadena. Leer el JSON con Python.
- `promote --check` no escribe a stdout: informe en `<plan>.check-report.json`, y
  el `--plan` no se crea si falla.

## Deuda sin sesión asignada

BUG-021, BUG-022, `MEN-1`…`MEN-6`, y el rollout py3d a las 8 skills instaladas
(siguen en `py3d-1.2.0`; ya hay wheel con identidad verde).

## Invariantes cerradas

- Git es la única fuente editable; las instaladas son despliegues. La adopción va
  del destino al repo, nunca al revés sin gate.
- Una adjudicación autoriza **un digest concreto**, caduca sola, y **tapa, no
  arregla**.
- Ningún writer ODOL; «aislado» ahí significa subproceso, no sandbox.
- Un gate que no puede ponerse rojo no es un gate.
- Ninguna promoción real sin autorización explícita del usuario.

**Gate de arranque:** declarar `Retomo DayZ Modding Knowledge Pack desde: BUG-020
cerrado en ac21d13 · averiguar quién escribe en las skills instaladas antes de
tocar promoción`.
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

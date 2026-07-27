# HANDOFF — DayZ Modding Knowledge Pack

<!-- LIVE-STATE:START -->
# DayZ Modding Knowledge Pack — Estado vivo · snapshot 2026-07-27 (tarde)

**Última verificación real:** HEAD `78071a7` en `r21/phase01-foundation`, árbol
limpio, `main` intacto en `994cb77`, sin remoto. Suite 643 passed / 18 skipped,
`packctl validate` PASS con cero findings, y `packctl promote --check` en
`verdict=WARN` con **exit 0**. Los tres medidos sobre el árbol, no leídos de
informes.

## Estado actual

- **El gate de promoción está verde.** Ya no hay `PROMOTION-CONFIG-INVALID` ni
  `PROMOTION-TARGET-UNEXPLAINED`. El único finding es `PROMOTION-DRIFT
  operation_count=43`, que es el aviso de trabajo pendiente: el plan tiene 54
  operaciones y 43 con `before_digest != after_digest`.
- `<claude-appdata>` está mapeado en `local-targets.json` a la raíz
  **virtualizada** `C:\Users\guill\AppData\Roaming\Claude`, no a la física.
  La línea 14 de `fix-junctions.ps1` usa ese prefijo para *detectar* junctions
  rotas y las reconstruye contra una raíz que autodetecta en runtime, así que
  mapearlo a la física lo convertiría en no-op.
- Ese fichero está **gitignored**, luego la decisión no viaja con el repo. Queda
  documentada en `promotions/local-targets.example.json`, que además no tenía la
  clave `path_aliases` que el cargador exige.
- Las **12 adjudicaciones** están en `promotions/adjudications.json`, con los
  digests releídos del check en el momento. 7 se consumen; 5 quedan inertes
  porque el gate indexa por `logical_target_ids[0]`.
- El rollout py3d sigue patch-only con preimagen fijada (BUG-018 cerrado) y el
  gate de identidad del wheel sigue **rojo a propósito**.

## Lo que hay que saber antes de tocar nada

- **La comparación viva↔repo caduca.** La premisa «0 en riesgo» de `4d594ae`
  había caducado en 10 horas: `dayz-test-ingame` y `dayz-vehicles` ganaron
  SP-095 y SP-096 solo en las instaladas. Adjudicar sin re-medir habría repetido
  BUG-018/BUG-019 por tercera vía. Re-medir **siempre** antes de adjudicar.
- **Las instaladas ya no son uniformemente CRLF.** Las líneas originales son
  CRLF y las secciones nuevas LF puro. Copiar el fichero entero —el método de
  `4d594ae`— hoy reescribiría todas las líneas de un fichero LF del repo. Adoptar
  solo el bloque añadido, normalizado.
- **`promote --check` no escribe a stdout.** El informe va a
  `<plan>.check-report.json` y el fichero `--plan` no se crea si el check falla.
  Un exit 1 mudo en consola no significa que no haya diagnóstico.
- Quedan 4 ficheros `*.bak_pre_sp-09*` solo en las instaladas. Son backups cuyo
  contenido ya es subconjunto del repo; la promoción espejo los borrará y eso
  está escrito en las razones de las adjudicaciones, no dejado en silencio.

## Bloqueo vigente

**No ejecutar `promote --apply` hasta decidir BUG-020** (identidad de nodo del
historial causal = digest en vez de ocurrencia sellada). El gate ya no frena; el
guardarraíl es de decisión, no técnico.

## Próxima acción

1. Decidir BUG-020. Es lo único que separa de una promoción real.
2. Lanzar el eval vivo. El prompt está listo y actualizado a `05b092d`:
   `VAULT/AI/10_Projects/DayZ_Modding_Knowledge_Pack/reviews/2026-07-26-prompt-implementation-codex-live-eval.md`.
3. Deuda sin sesión asignada: BUG-021, BUG-022, `MEN-1`…`MEN-6`, y las 8 skills
   del rollout py3d aún en `py3d-1.2.0`.

## Invariantes cerradas

- Git es la única fuente editable; las skills instaladas son despliegues. La
  adopción va del destino al repo, nunca al revés sin gate.
- Una adjudicación autoriza **un digest concreto** y caduca sola si el destino se
  mueve. No se firma sobre una comparación heredada.
- Ningún writer ODOL entra en alcance. El backend externo se fija por hash y no
  se redistribuye. «Aislado» ahí significa subproceso, no sandbox.
- Los parsers y validadores fallan cerrados; un gate que no puede ponerse rojo no
  es un gate.
- No se ejecuta ninguna promoción real sin autorización explícita del usuario.

**Gate de arranque:** declarar `Retomo DayZ Modding Knowledge Pack desde: gate de
promoción verde en 78071a7 · decidir BUG-020 antes de cualquier --apply`.
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

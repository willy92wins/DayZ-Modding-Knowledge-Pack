# HANDOFF — DayZ Modding Knowledge Pack

<!-- LIVE-STATE:START -->
# DayZ Modding Knowledge Pack — Estado vivo · snapshot 2026-07-27

**Última verificación real:** la cola correctiva de BUG-018 está cerrada y
commiteada. HEAD `191df01` en `r21/phase01-foundation`, árbol limpio, `main`
intacto en `994cb77`. Suite 643 passed / 18 skipped y `packctl validate` PASS con
cero findings, medidos sobre el árbol y no leídos de informes.

## Estado actual

- El rollout py3d es **patch-only con preimagen fijada**: `patched/` eliminado,
  cero rutas de reemplazo completo, backup obligatorio fuera de la raíz destino y
  `preimage-manifest.json` con las 11 rutas (4 `patched`, 7 `not_applicable`,
  todas con hash para detectar drift). BUG-018 cerrado.
- La promoción tiene tres gates fail-closed: preimagen con historia **causal** de
  receipts (sin confiar en el reloj, con el receipt sellado contra su journal),
  placeholders en payloads ejecutables, y localización de alias al copiar.
- El wheel py3d tiene gate de identidad. Está **rojo a propósito**: al fijar el
  toolchain en `pyproject.toml` el artefacto cambió, así que `cc014a43…` ya no es
  reproducible y solo un re-baseline deliberado lo cierra.
- El conocimiento que solo existía en las skills instaladas está **adoptado** al
  repo (SP-091, SP-092, SP-093, una sección más de `dayz-vehicles` y el
  `evals.json` de `blender-animation`). La comparación viva↔repo da 0 ficheros y
  0 secciones en riesgo ante una promoción espejo.

## Bloqueo vigente

`promote --check` desde árbol limpio devuelve FAIL con **2
`PROMOTION-CONFIG-INVALID`** sobre `tools/py3d/rollout/fix-junctions.ps1`, líneas
3 y 14, ambas por `<claude-appdata>`. Es **deliberado**: el alias entró en la
lista cerrada sin valor en el mapa para que el gate deje de dar verde sobre un
fichero que se promovería roto.

Mientras eso siga así, el check retorna antes de llegar al gate de preimagen, y
los 12 `PROMOTION-TARGET-UNEXPLAINED` de los seis artefactos restaurados quedan
enmascarados.

## Próxima acción

1. Decidir `fix-junctions.ps1`: mapear `<claude-appdata>` o excluir el fichero de
   la promoción. Bloquea todo lo demás de promoción.
2. Escribir las 12 adjudicaciones (6 artefactos × 2 targets). Ya es seguro: la
   adopción cerró el riesgo de borrado.
3. Lanzar el eval vivo. Los evals actuales son tautológicos por schema y no
   miden eficacia de skill.
4. Poner al día la memoria durable, siete commits por detrás.

Prompt de arranque completo:
`VAULT/AI/10_Projects/DayZ_Modding_Knowledge_Pack/reviews/2026-07-27-prompt-siguiente-sesion.md`.

## Invariantes cerradas

- Git es la única fuente editable; las skills instaladas son despliegues. La
  adopción va del destino al repo, nunca al revés sin gate.
- Ningún writer ODOL entra en alcance. El backend externo se fija por hash y no
  se redistribuye.
- Los parsers y validadores fallan cerrados; un gate que no puede ponerse rojo no
  es un gate.
- No se ejecuta ninguna promoción real sin autorización explícita del usuario.

**Gate de arranque:** declarar `Retomo DayZ Modding Knowledge Pack desde:
BUG-018 cerrado · promoción bloqueada a propósito por <claude-appdata>`.
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

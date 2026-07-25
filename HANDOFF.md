# HANDOFF — DayZ Modding Knowledge Pack

<!-- LIVE-STATE:START -->
# DayZ Modding Knowledge Pack — Estado vivo · snapshot 2026-07-25

**Última verificación real:** la Fase 04 queda implementada en el commit de
contenido `aa0a101a44a3e4edf33a2679559628343c26e1c6`. Su gate limpio pasó
validación, 14/14 skills, 18 variantes de eval, compilación, suites packctl y
py3d, y dos builds reproducibles. F1–F5 están cerrados en `product-spec.md`.

## Estado actual

- La rama activa es `r21/phase04-py3d`.
- `tools/py3d` publica el fork 1.4.0 con ciclo completo de proxies MLOD:
  add, inspección estricta, align, remove y round-trip raw/engine.
- `tools/dayz-animation-formats` implementa lectura/escritura estricta de
  SEAnim v1 y RTM `RTM_MDAT`/`RTM_0101`.
- `tools/dayz-model-preflight` valida escala, huesos, winding y estructura
  MLOD sin reparación silenciosa.
- `tools/dayz-odol-strict` inspecciona y compara ODOL v53–v55 en modo
  read-only mediante un backend externo fijado por hash. El backend no se
  redistribuye; sí se distribuyen el adaptador, contrato, manifiesto y
  fixtures first-party.
- Todo el código de Fase 04 se distribuye desde el source pack. py3d añade un
  wheel reproducible generado desde esa fuente; su SHA-256 es
  `cc014a4330e8f4a0cb905b20c300ec726b62febddb0eb6d1c6426e41c563c8ff`.
  ODOL se distribuye como instalación desde fuente; no se afirma un wheel
  autónomo que omita su manifiesto externo al paquete Python.
- El rollout se verificó sobre una copia desechable: 19 cambios planeados,
  19 aplicados y 0 cambios en la segunda pasada.
- Las skills instaladas reales y `P:\py3d` permanecen intactos. Aplicar el
  rollout operativo requiere autorización final separada.
- La Fase 02 conserva su bloqueo B20/C1 por observación DayZDiag y no ha sido
  modificada por este trabajo.

## Validación de Fase 04

- Suite global: 582 passed, 18 skipped.
- py3d: 196 passed, 10 skipped.
- animación: 82 passed.
- preflight: 73 passed.
- ODOL: 69 passed, 5 skipped sin backend; 74 passed con el backend fijado.
- `packctl validate`: cero findings en claims, licencias, links, privacidad,
  skills y source map.
- `skills-ref` oficial en
  `38a2ff82958afee88dadf4831509e6f7e9d8ef4e`: 14/14.
- Wheel py3d: dos builds byte-idénticos y smoke aislado
  add→inspect→align→save/reload→remove.
- Fixtures binarias protegidas de normalización Git mediante
  `.gitattributes`; bytes de working tree e índice verificados.

## Issues abiertos

1. **[ALTA, fuera de Fase 04] B20 / C1** — falta observar en DayZDiag el texto
   exacto de las variantes LF/CRLF.
2. **[MEDIA] Integración de rama** — la rama Fase 04 queda lista para integrar;
   no se mezcla ni publica automáticamente.
3. **[MEDIA] Rollout operativo** — no actualizar skills instaladas ni
   `P:\py3d` sin aprobación explícita.

## Próxima acción

Elegir cómo integrar `r21/phase04-py3d` siguiendo el flujo de cierre de rama.
Tras integrarla, el rollout operativo puede ejecutarse por separado sobre una
raíz explícita, primero con `-NoWrite`, y solo después de aprobar el destino.

## Invariantes cerradas

- Git es la única fuente editable del pack distribuible.
- Ningún writer ODOL entra en alcance.
- Los parsers y validadores fallan cerrados en límites, valores no finitos,
  índices inválidos y anatomía ambigua.
- El backend ODOL se invoca aislado y debe coincidir con el manifiesto fijado.
- Fixtures de terceros no se redistribuyen; las incluidas tienen licencia y
  procedencia registradas.
- El wheel py3d deriva de la fuente versionada y el rollout verifica hash,
  versión, backup y readback.
- Obsidian conserva evidencia completa; las skills activas son despliegues,
  no fuentes paralelas.

## Punteros

- `product-spec.md`
- `plans/2026-07-25-04a-py3d-proxy-lifecycle.md`
- `plans/2026-07-25-04b-dayz-animation-formats.md`
- `plans/2026-07-25-04c-dayz-model-preflight.md`
- `plans/2026-07-25-04d-dayz-odol-strict.md`
- `specs/2026-07-25-py3d-proxy-lifecycle.md`
- `specs/2026-07-25-dayz-animation-formats.md`
- `specs/2026-07-25-dayz-model-preflight.md`
- `specs/2026-07-25-dayz-odol-strict.md`
- `tools/py3d/rollout/README.md`

**Gate de arranque:** declarar `Retomo DayZ Modding Knowledge Pack desde:
Fase 04 F1–F5 cerrada · rollout operativo pendiente de autorización`.
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

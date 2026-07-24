---
title: "Phase 01b — Crash-safe multi-root promotion"
date: 2026-07-24
status: implemented-awaiting-final-gate
approved_by: user
implements:
  - SC-015
  - SC-016
  - SC-017
  - A9
---

# Phase 01b — Crash-safe multi-root promotion

## Objetivo y alcance

Cerrar el hard stop de publicación parcial antes de la primera promoción real.
El alcance se limita a la transacción `packctl promote`: journal durable,
exclusión mutua, recovery, termination injection, recibo y fixtures. No cambia
el contenido de skills, knowledge, py3d ni el routing aprobado.

El backup local real usará
`%LOCALAPPDATA%\DayZ-Modding-Knowledge-Pack\promotion-backups`; la ruta expandida
solo vive en `promotions/local-targets.json`, ignorado por Git.

## Contrato de estado

### Journal

**[EXACT]** Cada transacción contiene un snapshot sellado de su plan y un
directorio de eventos JSON create-only. Los eventos tienen secuencia contigua,
`transaction_id`, `event_type`, `previous_event_hash`, payload y `event_hash`.
La cadena completa se revalida antes de aplicar, recuperar o añadir un evento.

Estados y decisión:

| Evidencia durable | Decisión única | Acción permitida |
|---|---|---|
| Sin transacción publicada | PRE | aplicar puede empezar |
| `PENDING`, sin terminal | PRE | solo recovery hacia PRE |
| `COMMIT`, todos los POST válidos, sin recibo | POST | recovery publica el recibo sellado |
| `COMMIT` + recibo válido | POST | terminal, readback solamente |
| `ABORT`, todos los PRE válidos | PRE | terminal, readback solamente |
| Cadena inválida, digest ajeno o terminal contradictorio | desconocida | exit 2, intervención |

`COMMIT` solo se añade tras verificar todos los destinos físicos y cada alias
lógico en POST. `ABORT` solo se añade tras verificar todos los PRE o ausencias.
No se añade ningún evento después de `COMMIT` o `ABORT`.

### Locks

**[EXACT]** Cada root físico usa un lock exclusivo no bloqueante mantenido por
el sistema operativo:

- Windows: `msvcrt.locking(fd, LK_NBLCK, 1)`;
- POSIX: `fcntl.flock(fd, LOCK_EX | LOCK_NB)`.

El fichero puede sobrevivir, pero el lock del kernel se libera al terminar el
proceso. Existencia no equivale a lock vivo. Apply y recovery adquieren todos
los roots en orden canónico y repiten CAS/readback bajo lock.

### Durabilidad

**[EXACT]** Todo evento, plan local, marker y recibo usa
write→flush→`os.fsync`→readback→rename durable. En POSIX se hace fsync del
directorio padre; en Windows la rename usa
`MoveFileExW(..., MOVEFILE_WRITE_THROUGH)` sin permitir copy cross-volume.
Staging, old y recovery sidecars permanecen en el mismo volumen que su target.

Evidencia de API:

- Python `os.fsync`: Windows usa `_commit()` y Unix `fsync()`:
  <https://docs.python.org/3/library/os.html#os.fsync>.
- Python `os.replace`: rename atómica en POSIX y puede fallar cross-filesystem:
  <https://docs.python.org/3/library/os.html#os.replace>.
- Python `msvcrt.locking` y `LK_NBLCK`:
  <https://docs.python.org/3/library/msvcrt.html#msvcrt.locking>.
- Python `fcntl.flock` y `LOCK_EX|LOCK_NB`:
  <https://docs.python.org/3/library/fcntl.html#fcntl.flock>.
- Microsoft `MOVEFILE_WRITE_THROUGH`:
  <https://learn.microsoft.com/windows/win32/api/winbase/nf-winbase-movefileexw>.

## Interfaces

- **[EXACT]** CLI:
  `python -m packctl promote --recover --transaction-root <local-path>`.
- **[EXACT]** Python:
  `recover_promotion(transaction_root: Path, *, terminate_at: str | None = None)
  -> dict[str, object]`.
- **[EXACT]** El fault de muerte solo se activa en tests mediante
  `PACKCTL_TERMINATE_AT` o `PACKCTL_RECOVER_TERMINATE_AT`; ejecuta
  `os._exit(97)` y no pasa por `except/finally`.

Recovery no depende de que el repo siga limpio ni de que la fuente siga
disponible para volver a PRE. Para completar POST después de `COMMIT`, exige
todos los POST y aliases válidos; nunca reconstruye contenido fuente faltante.

## Fronteras de termination injection

Apply:

1. `after_pending`
2. `after_stage:<index>`
3. `after_backup:<index>`
4. `after_old_move:<index>`
5. `after_publish:<index>`
6. `after_target_event:<index>`
7. `after_post_verified`
8. `after_commit`

Recovery/rollback:

1. `after_recovery_stage:<index>`
2. `after_recovery_old_move:<index>`
3. `after_pre_publish:<index>`
4. `after_pre_verified:<index>`
5. `after_abort`

## Viability tests obligatorios

1. Cada frontera apply anterior mata un subprocess con exit 97.
2. Sin `COMMIT`, uno o dos recovery posteriores terminan en todos los PRE,
   `ABORT`, cero recibo y cero mezcla.
3. Tras `COMMIT`, recovery exige todos los POST y crea exactamente el recibo
   sellado; repetir recovery es idempotente.
4. Cada frontera de recovery mata el primer intento; el segundo termina en
   todos los PRE.
5. Corrupción/truncado/reorden de evento, plan digest inválido o digest de
   target distinto de PRE/POST devuelve exit 2 y no escribe target.
6. Un lock vivo en otro subprocess devuelve
   `PROMOTION-LOCK-ACTIVE`, exit 2; un fichero de lock sin dueño no bloquea.
7. El recibo es create-only, no contiene paths físicos y su hash coincide con
   el sellado en `COMMIT`.
8. Apply normal y recovery leen de vuelta todos los aliases lógicos.
9. Suite anterior de excepciones capturables conserva su comportamiento.
10. Gate final: pytest combinado, validator, 14/14 skills, 12 eval variants y
    build reproducible ×2.

## Archivos esperados

- Modificar: `packctl/common.py`
- Modificar: `packctl/promotion.py`
- Modificar: `packctl/cli.py`
- Modificar: `tests/packctl/test_promotion.py`
- Modificar: `tests/packctl/test_cli.py`
- Modificar: feature spec, source map, handoff y memoria durable

## Hard stops

- Cualquier estado mixto tras recovery.
- `COMMIT` sin todos los POST o `ABORT` sin todos los PRE.
- Evento mutable, cadena no contigua o receipt overwrite.
- Recovery que borre un digest ajeno a PRE/POST.
- Lock basado solo en existencia/PID.
- Test de muerte que use excepción capturable en vez de terminar el proceso.
- Cualquier promoción real antes del gate completo desde commit limpio.

## Registro de implementación Codex

**[EXACT]** Implementado el 2026-07-24 en
`packctl/common.py:51-151`, `packctl/promotion.py:861-2443` y
`packctl/cli.py:63-76,155-160`. La auditoría se ejecutó localmente, sin Claude ni subagentes,
por decisión expresa del usuario.

Además del contrato inicial, la implementación cierra estos casos que el
primer diseño no hacía explícitos:

1. la raíz de transacción solo se publica después de que `plan.json` y
   `PENDING` existan y sean durables;
2. el digest de un artefacto `file` representa sus bytes y no el nombre que
   recibe el snapshot;
3. plan, contratos, aliases y CAS se vuelven a validar bajo los locks;
4. CAS se repite antes del backup, antes de mover el target y antes de
   `COMMIT`, preservando una mutación externa como evidencia ajena;
5. un `ABORT` limpio admite un nuevo intento con otro `transaction_id`;
6. el escaneo histórico valida cadena y recibo terminal, pero no exige que un
   target siga eternamente en el estado de una promoción ya superada;
7. recovery no escribe diagnósticos dentro de una transacción cuya evidencia
   todavía no ha validado;
8. symlinks o junctions anidados en payloads, backups o residuos se rechazan
   para no convertir un enlace en una copia al restaurar.

La matriz ejecutable está en
`tests/packctl/test_promotion.py:536-587,1043-1649`. Cubre las fronteras de
muerte forward/recovery, corrupción de evidencia, targets y recibos ajenos,
locks vivos y huérfanos, tres generaciones consecutivas, retry tras `ABORT`,
inicialización atómica y carreras bajo lock.

Verificación intermedia antes del gate final:

- `python -m pytest -q`: 271 passed, 13 skipped;
- los 13 skips son fixtures condicionadas por capacidades de enlaces del host;
- ninguna promoción sobre roots reales se ha ejecutado todavía.

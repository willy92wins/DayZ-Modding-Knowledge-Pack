---
title: "Codex audit — Phase 01 promotion transaction"
date: 2026-07-24
reviewer: codex
status: approved-for-implementation
reviewed_commit: 35bd072dc398b15cb8186129b910b73521f7fcf3
decision_date: 2026-07-24
---

# Codex audit — Phase 01 promotion transaction

## Alcance y método

Auditoría secuencial de `packctl promote` contra el feature spec de Fase 01 y
`rigorous-data-audit`. No se usaron Claude ni subagentes por decisión expresa
del usuario. Se revisaron CAS, confinamiento, aliases físicos/lógicos, staging,
backup, reemplazo, rollback, journal, locks, recibo y privacidad.

## Hallazgos corregidos

Todos los siguientes puntos están implementados y cubiertos por fixtures en el
commit revisado:

1. **[EXACT] Riesgo de escritura fuera de política.** `backup_root` no estaba
   sometido a allowlist/forbidden roots. Ahora falla cerrado tanto al crear el
   plan como al aplicarlo (`packctl/promotion.py:321-340,836-857`;
   `tests/packctl/test_promotion.py:299-328`).
2. **[EXACT] Riesgo de misrouting por alias.** La deduplicación física perdía la
   ruta de cada target lógico. El plan sella `logical_target_paths`, vuelve a
   resolverlas antes de escribir y hace readback por cada alias
   (`packctl/promotion.py:594-749,938-972,1380-1394`;
   `tests/packctl/test_promotion.py:597-629`).
3. **[EXACT] Degradación idempotente.** Una operación con PRE=POST seguía
   reemplazando. Ahora solo hace readback (`packctl/promotion.py:1318-1319`;
   `tests/packctl/test_promotion.py:632-667`).
4. **[EXACT] Riesgo destructivo sobre residuos ajenos.** Staging/old
   preexistentes se borraban. Ahora bloquean y se conservan; un staging parcial
   creado por la operación sí se limpia
   (`packctl/promotion.py:1320-1340`;
   `tests/packctl/test_promotion.py:410-460`).
5. **[EXACT] Riesgo de corrupción en excepción entre dos replaces.** Si fallaba
   después de mover el target a `.old` y antes de publicar staging, la operación
   aún no figuraba como tocada. La frontera `after_old_move` ya revierte y
   verifica PRE (`packctl/promotion.py:1360-1374`;
   `tests/packctl/test_promotion.py:670-693`).
6. **[EXACT] Evidencia PASS falsa.** El recibo se publicaba antes de la última
   escritura fallible del journal. Ahora el recibo es la última publicación y
   un fallo previo revierte sin recibo (`packctl/promotion.py:1415-1437`;
   `tests/packctl/test_promotion.py:696-722`).
7. **[EXACT] Locks no exclusivos.** El nombre incluía `transaction_id`, por lo
   que dos transacciones distintas podían adquirir locks diferentes sobre el
   mismo root. Ahora el lock es único por root, create-only y fsync; CAS se
   repite bajo lock (`packctl/promotion.py:1289-1312`).
8. **[EXACT] Recovery gate ausente.** Un lock no adjudicado, journal pendiente,
   rollback fallido o `complete` sin recibo válido bloquea con exit 2. Solo
   `rolled-back` verificado o `complete` con recibo coherente permiten continuar
   (`packctl/promotion.py:1005-1124`;
   `tests/packctl/test_promotion.py:463-572`).
9. **[EXACT] Hueco de privacidad.** Los contratos públicos `repo_only` no
   entraban en el scanner. `sources/*.json`, `promotions/*.json` y el schema del
   manifest ya se inspeccionan, incluyendo backslashes escapados en JSON
   (`packctl/validation.py:706-779`;
   `tests/packctl/test_validation.py:205-216`).

## Verificación

- `python -m pytest -q`: **223 passed, 13 skipped**.
- Tests dirigidos de promotion/privacy: **59 passed, 2 skipped**.
- Los skips corresponden a fixtures de symlink/junction no disponibles en el
  host; no son fallos.
- `python -m packctl validate --root .`: **PASS**, cero findings en los seis
  checks.
- `python -m compileall -q packctl tests/packctl`: **PASS**.
- `git diff --check`: **PASS**.

## Bloqueante residual

**[EXACT] Riesgo de corrupción por terminación abrupta.** El gate detecta y
bloquea estado interrumpido, pero no puede reconciliarlo. El journal sigue
reescribiendo un único JSON (`packctl/promotion.py:1306,1370,1378,1433`) mediante
temp→replace sin fsync de archivo/directorio (`packctl/common.py:27-37`).
`fault_at` lanza excepciones capturables (`packctl/promotion.py:824-826`), no
mata el proceso. Por tanto no hay evidencia de recuperación tras terminar el
proceso entre publicación de roots físicos.

Esto incumple todavía la invariante multi-root de
`skills/rigorous-data-audit/references/crash-safe-evidence-and-bundles.md:30-42`:
journal append-only `PENDING/COMMIT/ABORT`, rechazo mientras `PENDING`,
manifiestos PRE/POST y termination injection en cada frontera. También impide
superar honestamente el hard stop de promoción parcial
(`plans/2026-07-24-01-foundation-and-evidence.md:200-205`).

## Decisión

**[EXACT] Aprobado por el usuario el 2026-07-24**, incluido el backup root local
`%LOCALAPPDATA%\DayZ-Modding-Knowledge-Pack\promotion-backups`.

El contrato ejecutable y sus viability tests quedan en
`plans/2026-07-24-01b-crash-safe-promotion.md`.

## Propuesta aprobada

**[DESIGN] Mi recomendación es ampliar Task 7/8 antes de la primera promoción
real** con un subcontrato de crash recovery:

1. journal local append-only y duradero con eventos `PENDING`, `TOUCHED`,
   `COMMIT` y `ABORT`, más manifiestos PRE/POST exactos;
2. comando separado de recuperación/adjudicación que solo cierre `COMMIT` tras
   todos los POST hashes o `ABORT` tras restaurar todos los PRE/ausencias;
3. fsync de archivo y directorio en journal, locks y recibo;
4. harness subprocess que termina el proceso en cada frontera de stage, backup,
   old-move, publish, readback, rollback y receipt;
5. gate que demuestre estado totalmente PRE o totalmente POST tras cada
   reinicio; nunca mezcla silenciosa.

Hasta implementar y verificar este subcontrato, `promote --apply` no debe
ejecutarse sobre las raíces reales.

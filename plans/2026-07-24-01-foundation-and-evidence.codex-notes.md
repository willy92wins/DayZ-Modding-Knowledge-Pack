---
title: "Codex audit — Phase 01 promotion transaction"
date: 2026-07-24
reviewer: codex
status: implemented-awaiting-final-gate
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

## Addendum de implementación y segunda auditoría

**[EXACT] El bloqueante residual anterior está cerrado en código y fixtures.**
La implementación sustituyó el journal mutable por eventos create-only
hash-chained, locks del sistema operativo, plan sellado, inicialización atómica,
durabilidad explícita y recovery determinista
(`packctl/common.py:51-151`; `packctl/promotion.py:1131-1668,1832-2450`;
`tests/packctl/test_promotion.py:1092-1698`).

Durante la segunda auditoría y las promociones reales se localizaron y
corrigieron once fallos
adicionales:

1. **[EXACT] Corrupción lógica de snapshots de fichero.** El digest incluía el
   basename de la fuente, pero el target vault se llama con el commit. Los
   mismos bytes producían digests distintos. El digest de un fichero ahora es
   su SHA-256 binario (`packctl/common.py:307-314`;
   `tests/packctl/test_promotion.py:569-620`).
2. **[EXACT] Degradación tras promociones sucesivas.** El scanner terminal
   exigía que el target actual siguiera en el POST de cada transacción
   histórica, bloqueando una tercera generación legítima. Ahora valida cadena,
   semántica y recibo históricos, mientras el estado físico actual se adjudica
   solo para la transacción que se recupera
   (`packctl/promotion.py:2024-2114`;
   `tests/packctl/test_promotion.py:1480-1524`).
3. **[EXACT] Retry envenenado tras `ABORT`.** Un ID derivado solo del plan
   volvía a seleccionar una transacción terminal. Cada intento incorpora
   entropía del sistema y conserva el contrato sellado
   (`packctl/promotion.py:763-781`;
   `tests/packctl/test_promotion.py:1525-1548`).
4. **[EXACT] Escritura dentro de evidencia no confiable.** El CLI intentaba
   dejar `recover-report.json` en una transacción corrupta. Recovery ahora
   devuelve el informe por stdout sin mutar esa raíz
   (`packctl/cli.py:155-160`;
   `tests/packctl/test_promotion.py:1549-1582`).
5. **[EXACT] Ventana antes de `PENDING`.** Una terminación durante la creación
   de `plan.json` podía dejar una transacción visible pero inválida. La
   inicialización se materializa en un directorio oculto y se publica mediante
   rename durable solo tras sellar plan y primer evento
   (`packctl/promotion.py:1601-1638`;
   `tests/packctl/test_promotion.py:1583-1621`).
6. **[EXACT] TOCTOU de contrato tras preflight.** Apply no repetía la
   validación del contrato sellado después de adquirir locks. Ahora lo hace
   antes de publicar la transacción
   (`packctl/promotion.py:2202-2241`;
   `tests/packctl/test_promotion.py:1622-1660`).
7. **[EXACT] Riesgo destructivo entre backup y old-move.** Una mutación externa
   podía moverse a `.old` y ser eliminada como si fuera PRE. Un CAS adicional
   detiene la operación y preserva el digest ajeno
   (`packctl/promotion.py:2304-2350`;
   `tests/packctl/test_promotion.py:1661-1698`).
8. **[EXACT] Pérdida de semántica de enlaces anidados.** Copiar un symlink o
   junction dentro de un árbol podía restaurarlo como contenido materializado.
   Payloads y sidecars que los contienen ahora fallan cerrados
   (`packctl/promotion.py:886-897,1022-1033,1686-1693`).
9. **[EXACT] Degradación de reproducibilidad entre checkouts.** Con
   `core.autocrlf=true` y sin política versionada, un clon limpio del commit
   validado produjo 66 `SOURCE-HASH-MISMATCH`. El usuario aprobó fijar LF,
   registrar `.gitattributes` como artefacto gobernado y añadir una fixture que
   rechaza cualquier CRLF versionado
   (`.gitattributes:1`; `tests/packctl/test_validation.py:31-43`).
10. **[EXACT] El lock contaminaba un target exacto.** La primera promoción real
    falló cerrada antes de `PENDING`: el allowed root físico de
    `rigorous-data-audit` era también el target, por lo que
    `target/.packctl.lock` entraba en el digest y Windows denegaba leer su byte
    bloqueado. El lock ahora es un sidecar hermano determinista y la fixture
    prueba que el digest permanece estable
    (`packctl/promotion.py:1131-1144`;
    `tests/packctl/test_promotion.py:696-714`).
11. **[EXACT] Orden de digest distinto entre proyección y readback.** La segunda
    promoción real publicó tres destinos y falló cerrada al primer árbol que
    combinaba `SKILL.md` con `references/...`: la proyección recorría strings
    case-sensitive, mientras `tree_digest` recorría `Path` con la semántica del
    host. El rollback restauró los 53 estados PRE y cerró en `ABORT`. Ambos
    cálculos usan ahora el mismo orden de `Path`, con una fixture mixta que
    reproduce la divergencia de Windows
    (`packctl/promotion.py:93-106`;
    `tests/packctl/test_promotion.py:536-568`).

La ejecución intermedia posterior al undécimo fix fue
`python -m pytest -q tests/packctl`: **135 passed, 3 skipped**. La recuperación
idempotente de la transacción abortada también devolvió `PASS` y
`decision=ABORT`. Estos resultados demuestran el contrato focalizado en el
árbol de trabajo, pero no autorizan por sí solos otro intento real: primero se
repite el gate completo desde commit limpio, validator, 14/14 skills,
12 variantes de eval y build reproducible por duplicado.

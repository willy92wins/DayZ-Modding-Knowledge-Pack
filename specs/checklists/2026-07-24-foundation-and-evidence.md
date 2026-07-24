# Spec Quality Checklist — Foundation, evidence and promotion

**Spec**:
[`specs/2026-07-24-foundation-and-evidence.md`](../2026-07-24-foundation-and-evidence.md)
**Date**: 2026-07-24
**Reviewer**: Codex

## Measurability

- [x] **CHK001** — SC-001–SC-020 tienen conteos, hashes, exits, códigos o
  estados binarios verificables.
- [x] **CHK002** — no se usan «funciona», «robusto» o «correcto» como criterio;
  cada resultado tiene un observable o una fixture exacta.
- [x] **CHK003** — límites numéricos declaran unidad/umbral: 1024 caracteres,
  `duration_ms ≥ 0`, tokens enteros `≥ 0`, counts y exit codes.

## Testability / verification path

- [x] **CHK004** — los 13 escenarios usan Given/When/Then. El repro in-game
  está explícitamente marcado N/A porque esta
  feature no carga ni modifica DayZ runtime; cada uno ofrece su repro offline
  autoritativo en lugar de simular un gate de juego inexistente.
- [x] **CHK005** — SC-001–SC-020 y Scenarios 1–13 aparecen en la matriz de
  verificación.
- [x] **CHK006** — todos los checks son offline y están marcados así; no se
  consume un ciclo DayZDiag/servidor sin necesidad.

## Assumptions & clarity

- [x] **CHK007** — las dos incógnitas restantes están marcadas
  `ASSUMED, deferred` (`spec:209-215`).
- [x] **CHK008** — el root físico externo se difiere hasta antes de Task 8 y
  falla cerrado mientras tanto; la adjudicación de fuentes se resuelve en Tasks
  1–2 antes de editar contenido.
- [x] **CHK009** — no quedan marcadores de trabajo pendiente, guidance de
  plantilla ni líneas por fijar. Los valores `<...>` de CLI están declarados como metasyntaxis
  (`spec:377-390`).

## Cross-file references (G2/R2)

- [x] **CHK010** — cada símbolo del Forward Contract referencia su definición
  exacta `path:line` o el snapshot pineado (`spec:416-430`).
- [x] **CHK011** — esta fase no emite classnames, selections, bones, proxies ni
  stringtable keys de DayZ. Los únicos consumidores nuevos son contratos
  `[DESIGN]` definidos en el propio spec; el validador externo está verificado
  contra `AGENT_SKILLS_REF/.../validator.py:10-22,70-84,104-147`.
- [x] **CHK012** — no queda ninguna dependencia técnica sin verificar; las APIs
  nuevas son contratos de diseño, no afirmaciones de que ya existan.

## Scope & consistency

- [x] **CHK013** — `Scope — Out of scope` enumera diez no-objetivos
  (`spec:179-194`).
- [x] **CHK014** — `Fuente`, `Artefacto`, `Payload`, `Repo-only`, `Generado`,
  `Target lógico`, `Target físico`, `Operación física` y `Snapshot de vault`
  tienen una sola definición (`spec:16-30`).
- [x] **CHK015** — no hay contradicción: repo es fuente; vault recibe snapshot
  sin overwrite privado; skills reciben despliegue post-gate; aliases se
  deduplican pero todos tienen readback.

## Data-critical escalation

- [x] **CHK016** — la promoción persistente incluye target-changed,
  fault-injection, rollback fallido e intervención manual (Scenarios 8–12);
  `rigorous-data-audit` está obligado antes de Task 8
  (`spec:447-453`).
- [x] **CHK017** — los inputs descubiertos pero no adoptados tienen contrato
  explícito `excluded_inputs[]`, hash, razón tipada y fixture positiva/negativa;
  no se confunde «excluido del payload» con «ignorado sin decisión».

## Result

- **Pass count: 17 / 17**
- **Failing IDs**: ninguno.
- **Verdict**: Ready-to-implement para Tasks 1–7. Task 8 conserva el hard stop
  explícito sobre el root físico de `rigorous-data-audit`.

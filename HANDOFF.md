# HANDOFF — DayZ Modding Knowledge Pack

<!-- LIVE-STATE:START -->
# DayZ Modding Knowledge Pack — Estado vivo · snapshot 2026-07-24

**Última verificación real:** Fase 01 cerrada sobre el commit de contenido
`7a25432febc112a957a7c1ef7a7d2c16c221b24f`: `packctl` 143 passed/3 skipped,
py3d 130/10, pytest global 282/13, 14/14 skills válidas, 12/12 variantes de
eval, validator con cero findings y dos builds byte-idénticos con SHA-256
`e48bee5e53e943d687b5cc234e30fa14d3c4347340c6900c146a3ce0e9289fbf`.

## Estado actual

- A1–A9 y B1–B5 están cerrados en la DPF; source map, claims, API index,
  evals, licencias, privacidad, builder y gate reproducible quedan operativos.
- La promoción `c7b5366cc761a8038e52f6a2` terminó en `COMMIT`: 53/53 targets
  físicos y 67 aliases lógicos en POST, cero residuos y cero paths privados.
- El recibo create-only es
  `promotions/receipts/c7b5366cc761a8038e52f6a2.json`; su SHA-256
  `44533938582f194432ff18ff6a4d363c432858960e9ffe5fc7e5c8d14a14d0dd`
  coincide con el evento `COMMIT`.
- Dos recoveries posteriores devolvieron `PASS/COMMIT` sin modificar los 162
  eventos ni los targets.
- El commit raíz histórico sigue siendo
  `d48e2c1a02dacc97645a9e70d8bc1058e6dae9a5`; la rama activa es
  `r21/phase01-foundation` y no se ha mezclado a la rama principal.
- Orden de programa aprobado: foundation/evidence → UI lab → persistence →
  expansiones de dominio/tooling → MCP → release/polish.

## Issues abiertos

1. **[MEDIA] Integración pendiente** — la rama de Fase 01 todavía no se ha
   mezclado a principal; no re-promover el commit administrativo de cierre.
2. **[MEDIA] UI lab pendiente** — B19/B20, el Sorter V4 negativo y la
   fidelidad offline↔DayZDiag siguen perteneciendo a Fase 02.
3. **[MEDIA] Prior art posterior** — queda comentar con el usuario el valor
   incremental de dayz-labs, Lake-DayZ-MCP y StarDZ antes de asimilar nada
   adicional.

## Próxima acción

Presentar el cierre de Fase 01 y revisar con el usuario dayz-labs,
Lake-DayZ-MCP y StarDZ. Después, revisar el plan
`plans/2026-07-24-02-dayz-ui-lab.md` contra la DPF C y ejecutar primero su fase
de descubrimiento/corpus; no implementar el visor antes de ese gate.

## Invariantes cerradas

- El ZIP anterior es solo baseline; no se modifica.
- Este Git es la única fuente editable del pack distribuible.
- Obsidian conserva evidencia/memoria completa; las skills activas reciben
  promociones verificadas desde Git tras gates.
- Ninguna invariante de dominio puede quedar únicamente en una de las tres
  superficies.
- StarDZ, dayz-labs y Lake son prior art selectivo, no dependencias del pack.
- VPP, Expansion, TraderPlus y TraderX son corpus local opcional; no se
  redistribuyen.
- Ejecución y revisión por Codex, sin Claude/subagentes, mientras siga vigente
  la instrucción del usuario.
- Los cinco intentos fallidos de promoción permanecen como evidencia terminal
  `ABORT`; no se borran backups ni journals automáticamente.

## Punteros

- `product-spec.md`
- `plans/2026-07-24-r21-master-roadmap.md`
- `plans/2026-07-24-01-foundation-and-evidence.codex-notes.md`
- `promotions/receipts/c7b5366cc761a8038e52f6a2.json`
- `decisions/001-canonical-source-and-baseline.md`
- `decisions/002-three-surface-promotion.md`

**Gate de arranque:** declarar `Retomo DayZ Modding Knowledge Pack desde:
Fase 01 cerrada/promovida · próxima acción: review de prior art y plan 02 UI`.
<!-- LIVE-STATE:END -->

---

## Log histórico

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

# HANDOFF — DayZ Modding Knowledge Pack

<!-- LIVE-STATE:START -->
# DayZ Modding Knowledge Pack — Estado vivo · snapshot 2026-07-24

**Última verificación real:** los tres deltas de prior art aprobados quedaron
formalizados en el commit de contenido
`13af7f8b59962bca6fded981ad75cd77a37616ef`: `packctl` 143 passed/3 skipped,
py3d 130/10, 14/14 skills válidas, 18/18 variantes de eval, 43 archivos Python,
validator con cero findings y dos builds byte-idénticos con SHA-256
`4ff37fd213ff6e112f11066ec8e27c464e1b923536cb0f598838653afb7252d6`.

## Estado actual

- A1–A9 y B1–B5 están cerrados en la DPF; source map, claims, API index,
  evals, licencias, privacidad, builder y gate reproducible quedan operativos.
- B8 queda pendiente en Fase 04 sin reabrir B2 ni bloquear UI: el índice v2
  añadirá liveness estructurada, parent chain, guardas y namespace.
- E4/B6 quedan pendientes con contrato release-grade: exit 0/existencia no
  bastan; hacen falta postconditions, cache completa, staging y rollback.
- G5 fija dayz-labs v0.1.35 / `dbd6ad3e…` como companion opcional, sin
  installer en gates, sin lifecycle authority y sin usar WPF como evidencia
  `.layout`.
- La promoción `51a7024ef9a5e333e5fab7b8` terminó en `COMMIT`: 53/53 destinos
  físicos y 67 aliases lógicos en POST, 123 eventos y cero residuos.
- El recibo create-only es
  `promotions/receipts/51a7024ef9a5e333e5fab7b8.json`; su SHA-256
  `a3c0ccc8c92b92c6eeb105838becdf7d17649508904bdf945c3e9ddfb29cec59`
  coincide con el evento `COMMIT`.
- La promoción anterior `c7b5366cc761a8038e52f6a2` y sus dos recoveries
  idempotentes permanecen como evidencia histórica de Fase 01.
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
3. **[BAJA] Gate sensible a presión de memoria del host** — dos corridas
   prefinales sufrieron `0x800705AF`/`MemoryError` mientras coexistía otro gate;
   la corrida única posterior pasó completa sin cambio de código.

## Próxima acción

Revisar `plans/2026-07-24-02-dayz-ui-lab.md` contra la DPF C y ejecutar primero
su fase de descubrimiento/corpus. El visor `.layout` sigue siendo la prioridad:
iteración determinista offline, comparación y calibración final en DayZDiag.
`dayz-api-index` v2 no bloquea C1.

## Invariantes cerradas

- El ZIP anterior es solo baseline; no se modifica.
- Este Git es la única fuente editable del pack distribuible.
- Obsidian conserva evidencia/memoria completa; las skills activas reciben
  promociones verificadas desde Git tras gates.
- Ninguna invariante de dominio puede quedar únicamente en una de las tres
  superficies.
- StarDZ, dayz-labs y Lake son prior art selectivo, no dependencias del pack.
- Un cero de `dayz-api-index` v1 no prueba ausencia; se abre la fuente y se
  inspeccionan guardas hasta que B8 esté cerrado.
- Un PBO existente tras exit 0 no es un release PASS sin postconditions y
  publicación transaccional.
- dayz-labs no ejecuta `start/stop/restart` sobre runs gobernados por DayZ_MCP.
- VPP, Expansion, TraderPlus y TraderX son corpus local opcional; no se
  redistribuyen.
- Ejecución y revisión por Codex, sin Claude/subagentes, mientras siga vigente
  la instrucción del usuario.
- Los cinco intentos fallidos de promoción permanecen como evidencia terminal
  `ABORT`; no se borran backups ni journals automáticamente.

## Punteros

- `product-spec.md`
- `plans/2026-07-24-r21-master-roadmap.md`
- `plans/2026-07-24-prior-art-assimilation-proposal.md`
- `plans/2026-07-24-02-dayz-ui-lab.md`
- `plans/2026-07-24-04-py3d-and-domain-skills.md`
- `promotions/receipts/51a7024ef9a5e333e5fab7b8.json`
- `decisions/001-canonical-source-and-baseline.md`
- `decisions/002-three-surface-promotion.md`

**Gate de arranque:** declarar `Retomo DayZ Modding Knowledge Pack desde:
prior art aprobado/promovido · próxima acción: descubrimiento de Fase 02 UI`.
<!-- LIVE-STATE:END -->

---

## Log histórico

### 2026-07-24 — Prior art aprobado y promovido

- Se aprobaron únicamente tres deltas: API index v2 no bloqueante, build/release
  transaccional y dayz-labs como companion sin lifecycle authority.
- El commit `13af7f8b59962bca6fded981ad75cd77a37616ef` superó el gate integral.
- La transacción `51a7024ef9a5e333e5fab7b8` promovió ese commit a Obsidian y
  skills activas con readback completo y cero residuos.

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

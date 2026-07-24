# HANDOFF — DayZ Modding Knowledge Pack

<!-- LIVE-STATE:START -->
# DayZ Modding Knowledge Pack — Estado vivo · snapshot 2026-07-24

**Última verificación real:** la revisión de readiness de Fase 02 quedó
versionada en `32ac0ae64327d2dad3363c91d8e9d1f21067ca38`. `packctl validate`
pasó con claims/licencias/links/privacidad/skills/source map a cero. El
baseline externo del parser pasó 7/7 unit tests y aceptó
`LF_UILab_Main.layout` con `roots=1`, `widgets=48`, `nodes=48`.

## Estado actual

- A1–A9 y B1–B5 están cerrados en la DPF; source map, claims, API index,
  evals, licencias, privacidad, builder y gate reproducible quedan operativos.
- El Grill de Fase 02 conserva C1–C8, pero exige enmendar C3 y C6 antes de
  implementar: determinismo raster por perfil fijado y snapshot runtime
  estructurado por widget.
- `dayz-ui-lab` será un producto nuevo con una sola IR para visor, raster y
  diff; DayZDiag sigue siendo el golden final.
- `LF_UILab` queda como prior art para una sonda first-party; no se adopta como
  base probada ni se mantiene una dependencia obligatoria de Dabs.
- MCP solo será adapter de `engine-capture-v1`; no duplica lifecycle. El delta
  run-bound/lossless queda detrás del schema y de la Fase 05.
- El usuario aprobó dejar py3d totalmente fuera de esta ejecución y trabajarlo
  en paralelo. Fase 02 no modifica ni depende de py3d.
- No se ha implementado código UI de Fase 02.
- El commit raíz histórico sigue siendo
  `d48e2c1a02dacc97645a9e70d8bc1058e6dae9a5`; la rama activa es
  `r21/phase01-foundation` y no se ha mezclado a la rama principal.

## Issues abiertos

1. **[ALTA] Readiness C6** — screenshot + dump vanilla no contiene geometría;
   falta aprobar la sonda estructurada y su gate.
2. **[ALTA] Readiness C3** — «PNG byte-idéntico» carece de entorno fijado;
   falta aprobar la separación JSON cross-run / píxeles por perfil canónico.
3. **[MEDIA] Tooling UI/MCP** — falta aprobar sonda vanilla-first y schema MCP
   ahora/cambio run-bound después.
4. **[MEDIA] Integración pendiente** — la rama activa todavía no se ha
   mezclado a principal.

## Próxima acción

Adjudicar las cuatro enmiendas de
`plans/2026-07-24-02-dayz-ui-lab.codex-notes.md`. Si se aprueban, actualizar
DPF C3/C6 y el plan, fijar los viability gates y empezar por B19/B20. No tocar
py3d.

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
- `dayz-ui-lab` no depende de py3d; PAA/EDDS permanece interno al lab hasta que
  exista un segundo consumidor real.
- MCP no posee semántica UI ni crea una segunda autoridad de lifecycle.
- Ejecución y revisión por Codex, sin Claude/subagentes, mientras siga vigente
  la instrucción del usuario.
- Los cinco intentos fallidos de promoción permanecen como evidencia terminal
  `ABORT`; no se borran backups ni journals automáticamente.

## Punteros

- `product-spec.md`
- `plans/2026-07-24-r21-master-roadmap.md`
- `plans/2026-07-24-02-dayz-ui-lab.md`
- `plans/2026-07-24-02-dayz-ui-lab.codex-notes.md`
- `plans/2026-07-24-04-py3d-and-domain-skills.md`
- `decisions/001-canonical-source-and-baseline.md`
- `decisions/002-three-surface-promotion.md`

**Gate de arranque:** declarar `Retomo DayZ Modding Knowledge Pack desde:
Grill de Fase 02 UI pendiente · próxima acción: adjudicar cuatro enmiendas`.
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

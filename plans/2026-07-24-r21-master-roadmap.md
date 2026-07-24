# DayZ Modding Knowledge Pack — Roadmap maestro de mejora R21

> **Ejecución:** cada fase exige su plan hijo, revisión fría de Codex y gates
> de la DPF. El usuario pidió trabajo Codex-only; no despachar Claude ni
> subagentes.

**Goal:** completar el pack por capas verificables y promover cada conocimiento
aceptado a Obsidian y skills aplicables sin crear fuentes paralelas ni importar
prior art no trazable.

**Architecture:** Git es la fuente; un source map reconcilia inputs; validadores
y evals producen evidencia; el builder genera un ZIP reproducible mediante
allowlist. Obsidian conserva la memoria/evidencia completa y las skills activas
reciben snapshots post-gate; un promotion map y recibos por hash prueban la
sincronización de las tres superficies.

**Tech Stack:** Markdown, JSON/JSON Schema, Python 3 stdlib, pytest donde ya
existe, PowerShell solo para integración Windows/DayZ.

## Restricciones globales

- DPF autoritativa: [`../product-spec.md`](../product-spec.md).
- Baseline: commit `d48e2c1a02dacc97645a9e70d8bc1058e6dae9a5`.
- Cero writes al ZIP baseline.
- Cero edición independiente de skills instaladas; solo promoción desde un
  commit validado, con staging y readback.
- Toda invariante aceptada se enruta a repo + Obsidian + skill aplicable; un
  `not_applicable` requiere motivo y no vale para invariantes de dominio.
- Cero API/cifra nueva sin fuente, build/commit y `path:line`.
- Cero redistribución de vanilla, PBOs, DBs o assets de terceros.
- Cada fase termina en un deliverable testeable y un commit independiente.
- Una fase no empieza si su dependencia anterior está en rojo.

## Orden y dependencias

| Fase | Plan | DPF | Depende de | Gate de salida |
|---|---|---|---|---|
| 01 | Foundation + evidence | A1–A9, B1–B5 | baseline | source/promotion maps completos, 14/14 skills válidas, validator/build/promoción reproducibles |
| 02 | `dayz-ui-lab` | C | 01 | parser/corpus/determinismo/diff + calibración DayZDiag |
| 03 | `dayz-persistence` | D | 01 | matriz de compatibilidad/migración y fault injection |
| 04 | py3d + skills de dominio | E, F, B7 | 01 y 03 cuando toque persistence | research por dominio + planes ejecutables separados |
| 05 | MCP publicable | G | 01; UI para visual diff | protocolo/lite/orchestrator y capability gates |
| 06 | Ecosistema + release | H, B6 y cierre A | 01–05 | release candidate reproducible, auditada y documentada |

## Fase 01 — Foundation + evidence

- [ ] Ejecutar
  [`2026-07-24-01-foundation-and-evidence.md`](2026-07-24-01-foundation-and-evidence.md).
- [ ] Bloquear content edits mientras exista `SOURCE-UNMAPPED`.
- [ ] Registrar baseline de evals y compatibilidad DayZ.
- [ ] Producir el primer ZIP reproducible sin afirmar aún que el contenido está
  actualizado.
- [ ] Promover el snapshot reconciliado a Obsidian y targets de skills
  configurados solo después de todos los gates, con readback y recibo.

## Fase 02 — `dayz-ui-lab`

- [ ] Ejecutar
  [`2026-07-24-02-dayz-ui-lab.md`](2026-07-24-02-dayz-ui-lab.md).
- [ ] Cerrar B19/B20 antes de cualquier golden/diff.
- [ ] Promover patrones a `dayz-ui` solo después de corpus + DayZDiag.
- [ ] Cerrar con la nota Obsidian y la skill activa sincronizadas al commit.

## Fase 03 — `dayz-persistence`

- [ ] Ejecutar
  [`2026-07-24-03-dayz-persistence.md`](2026-07-24-03-dayz-persistence.md).
- [ ] Separar stream vanilla, CF y sidecars.
- [ ] Tratar todo cambio de formato con legacy + rollback + backup.
- [ ] Cerrar con conocimiento durable y skills aplicables sincronizados.

## Fase 04 — py3d y skills de dominio

- [ ] Ejecutar
  [`2026-07-24-04-py3d-and-domain-skills.md`](2026-07-24-04-py3d-and-domain-skills.md).
- [ ] Dividir la ejecución posterior en un plan por skill/herramienta.
- [ ] No mezclar ODOL writer ni cifras de performance sin benchmark.
- [ ] Cada workstream aceptado deja routing y recibo de promoción.

## Fase 05 — MCP publicable

- [ ] Ejecutar
  [`2026-07-24-05-dayz-mcp-public-and-automation.md`](2026-07-24-05-dayz-mcp-public-and-automation.md).
- [ ] Mantener lease/run-id y lifecycle request-bound.
- [ ] Separar protocolo público, modo lite y capacidades avanzadas.
- [ ] Promover los contratos MCP verificados a Obsidian y skills activas.

## Fase 06 — Ecosistema y release

- [ ] Ejecutar
  [`2026-07-24-06-release-ecosystem-and-polish.md`](2026-07-24-06-release-ecosystem-and-polish.md).
- [ ] Consolidar duplicados solo con mapa de procedencia.
- [ ] Cerrar licencias, contribución, companions y risk register.
- [ ] Repetir todos los gates desde un checkout limpio antes del release.
- [ ] Verificar `PROMOTION-UNROUTED=0` y `PROMOTION-DRIFT=0` en todos los
  targets configurados.

## Criterio de cierre del programa

Todos los criterios A–H de la DPF están `✓` o tienen una exclusión de alcance
aprobada y fechada. El ZIP final se reconstruye dos veces con el mismo SHA-256,
el repo queda limpio, Obsidian/skills aplicables coinciden con sus recibos y el
handoff identifica cualquier riesgo residual.

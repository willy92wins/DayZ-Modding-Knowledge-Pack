# Fase 05 — MCP publicable y automatización

> **Modo de ejecución:** Codex para código/docs; cualquier sesión viva DayZ
> requiere lease y lifecycle guard. No conectar MCP externos como autoridad.

## Objetivo y traza DPF

Cerrar G1–G5: publicar el contrato metodológico, ofrecer un modo lite y ampliar
el testing sin exponer infraestructura privada ni romper ownership.

## Destinos previstos

- Modificar: `skills/dayz-mcp-verify/**`
- Modificar: `skills/dayz-test-ingame/**`
- Crear: `knowledge/dayz-mcp-bridge-protocol.md`
- Crear: `knowledge/dayz-mcp-lite.md`
- Crear/actualizar:
  `VAULT/AI/20_Knowledge/dayz-mcp-bridge-protocol.md`.
- Crear/actualizar: `VAULT/AI/20_Knowledge/dayz-mcp-lite.md`.
- Promover: `dayz-mcp-verify` y `dayz-test-ingame` a los targets activos
  configurados.
- Crear: `tools/dayz-test-orchestrator/` si el research confirma extracción
  limpia y licenciable.
- Crear schemas y ladders first-party; no incluir keys, profiles o paths.

## Task 1 — Protocol inventory

- [ ] Enumerar comandos reales del bridge por grep, con sides, ownership,
  request/response, errores y version.
- [ ] Generar JSON Schemas y ejemplos validados contra el bridge actual.
- [ ] Documentar cómo extender sin colisiones y cómo negociar versión.
- [ ] Sanitizar toda ruta/config privada.
- [ ] Gate: ejemplo por comando y 0 schema drift contra implementación.

## Task 2 — Modo lite

- [ ] Definir subset viable con DayZDiag + filePatching + scripts ingame.
- [ ] Ladder mínima: spawn, ejecutar acción observable, leer RPT y emitir verdict.
- [ ] Ejemplos separados para vehicle, weapon, basebuilding e infected.
- [ ] Declarar lo que el modo lite no puede observar/controlar.
- [ ] Gate: host limpio sin bridge privado reproduce la ladder.

## Task 3 — Orchestrator único y watch mode

- [ ] Unificar preparación, build, server, client, bridge y cleanup bajo run_id.
- [ ] Mantener lease, token interno y stop request-bound.
- [ ] Watch identifica archivos afectados, ejecuta build incremental y solo la
  feature ladder correspondiente.
- [ ] Detectar loops y coalescer cambios.
- [ ] Gate: cambio de fixture dispara exactamente un rebuild/retest.

## Task 4 — Capacidades avanzadas separadas

- [ ] Secuencias declarativas de acciones con fixtures.
- [ ] Crash/exception/RPT detection con vocabulario preciso.
- [ ] Screenshot diff calibrado desde `dayz-ui-lab`.
- [ ] Telemetry con build/hardware/corpus y sin budgets heredados.
- [ ] Dos clientes locales con identidad/run exactos.
- [ ] Cada capability tiene flag, schema, test y verdict independiente.

## Task 5 — Companions y cierre

- [ ] VPP/init.c como alternativa básica documentada con límites.
- [ ] dayz-labs como companion opcional sin lifecycle authority.
- [ ] Lake/StarDZ como prior art, no dependencia.
- [ ] Cheat Engine queda fuera de la ruta recomendada por fragilidad/riesgo.
- [ ] Actualizar Obsidian con evidencia privada; promover skills desde el commit
  validado y verificar hashes/recibo.
- [ ] Validator/evals/ladders verdes; revisión fría Codex; DPF/HANDOFF actualizados.

## Hard stops

- Launch/kill fuera del lifecycle guard.
- Stop sin run_id exacto.
- Protocol example no verificado contra código.
- Key/path/profile privado en Git.
- Dos autoridades de lifecycle.
- Screenshot diff usado como prueba de gameplay sin gate DayZDiag.
- `PROMOTION-UNROUTED` o `PROMOTION-DRIFT`.

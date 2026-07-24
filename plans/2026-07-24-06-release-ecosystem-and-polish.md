# Fase 06 — Ecosistema, contribución, consolidación y release

## Objetivo y traza DPF

Cerrar H1–H6, B6 y los criterios A pendientes, produciendo el release candidate
auditable del programa.

## Task 1 — Integraciones y entorno limpio

- [ ] Documentar Workbench/Animation Editor, Mikero y viewers/debinarizers con
  versión, licencia, rol y smoke.
- [ ] Documentar dayz-labs como companion opcional pineado, con matriz de
  capacidades y límites: sin installer en gates, sin `start/stop/restart`
  cuando DayZ_MCP posee el run y sin equiparar WPF a evidencia `.layout`.
- [ ] Ejecutar spike Docker vs VM para server DayZ; escoger una única vía viable.
- [ ] Reproducir un smoke desde entorno limpio sin junctions privados.
- [ ] Documentar instalación y teardown.

## Task 2 — Contribución y extensión

- [ ] Guía de contribución: source map, research, provenance, fixtures, evals,
  licencias, routing repo↔Obsidian↔skills, review y changelog.
- [ ] Ejemplo de añadir una skill/reference y atravesar el pipeline.
- [ ] Template `@MyMod` con contratos de config/build/test que consume el
  preflight y los postconditions release-grade de Fase 04.
- [ ] El template no acepta exit 0/existencia como build pass: comprueba
  candidato fresco, header/prefix/entries, fatal log y firma cuando aplique.
- [ ] El ejemplo publica desde staging y demuestra con fault injection que un
  fallo conserva el PBO anterior y no avanza cache/manifest.
- [ ] Gate: una contribución fixture pasa end-to-end sin conocimiento tácito.

## Task 3 — Consolidación editorial

- [ ] Detectar duplicados exactos y semánticos en knowledge/references.
- [ ] Crear mapa old→canonical y preservar redirects cuando ayuden.
- [ ] No fusionar claims con diferente build/licencia/nivel de evidencia.
- [ ] Arreglar links o allowlistarlos como referencias externas deliberadas.
- [ ] Gate: 0 links rotos no allowlisted y 0 pérdida de claims verificados.

## Task 4 — Visual aids y risk register

- [ ] Diagramas first-party de skeleton, proxy frame y Construction quartet.
- [ ] Risk register/known engine bugs con build, evidencia y severidad precisa.
- [ ] Common RPT tree enlazado desde los runbooks.
- [ ] Gate: revisión humana y validator de assets/links.

## Task 5 — Release candidate

- [ ] Actualizar README, compatibilidad, changelog, licenses/notices y manifest.
- [ ] Ejecutar validator completo y todos los evals.
- [ ] Build reproducible ×2 en checkout limpio.
- [ ] Escanear ZIP por secrets, identidad, private paths, payloads de terceros
  y archivos fuera de allowlist.
- [ ] Verificar SHA, file count, source commit y DayZ build dentro del manifest.
- [ ] Verificar todos los recibos de promoción y readback de targets activos:
  `PROMOTION-UNROUTED=0`, `PROMOTION-DRIFT=0`.
- [ ] No publicar: entregar el RC local y su reporte para decisión del usuario.

## Task 6 — Revisión final

- [ ] Trazar A–H: cada criterio tiene evidencia o exclusión aprobada.
- [ ] Revisión fría Codex de contenido, tooling, licencias y release.
- [ ] Confirmar que ninguna invariante de dominio existe solo en repo, solo en
  Obsidian o solo en una skill instalada.
- [ ] Corregir findings y repetir gates proporcionales.
- [ ] Marcar DPF/HANDOFF y crear tag local solo si todos los gates están verdes.

## Hard stops

- Licencia o provenance desconocida.
- Public/private path leak.
- ZIP no reproducible.
- Claim de compatibilidad sin build.
- Link roto no allowlisted.
- Finding crítico de eval/audit.
- Build marcada PASS sin postconditions o publicación que no conserve rollback.
- Companion que asume lifecycle authority o se instala desde un gate.
- Routing incompleto o drift de promoción.
- Push, GitHub release o Workshop sin orden explícita separada.

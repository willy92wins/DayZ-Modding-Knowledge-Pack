# CLAUDE.md — DayZ Modding Knowledge Pack

## Resumen

Fuente canónica y versionada del pack público de conocimiento DayZ: skills
modulares, notas verificadas y tooling reutilizable. El ZIP publicado es un
artefacto generado; no es una fuente editable. Obsidian conserva la memoria
durable completa y las skills instaladas son destinos de promoción verificable.

## Definición de Producto Final

El contrato de aceptación está en [`product-spec.md`](product-spec.md).
Leerlo antes de planificar o ejecutar cualquier fase. Cada plan debe trazar
sus entregables a criterios concretos de esa DPF.

## Stack técnico

- Markdown y JSON para skills, conocimiento, contratos y manifiestos.
- Python 3, preferiblemente stdlib, para validación, evaluaciones y packaging.
- PowerShell únicamente para integración Windows/DayZ Tools cuando aporte
  una capacidad que Python no cubra de forma portable.
- Git como fuente de verdad y ZIP reproducible como artefacto de release.

## Estructura del repositorio

- `skills/`: skills propias distribuibles y sus referencias.
- `knowledge/`: notas públicas depersonalizadas.
- `tools/`: tooling DayZ distribuible, incluido el fork de py3d.
- `specs/`: contratos de features antes de implementar.
- `plans/`: roadmap y planes por subsistema.
- `decisions/`: ADRs del pack.
- `promotions/`: routing lógico y recibos repo↔Obsidian↔skills, sin rutas
  privadas.
- `HANDOFF.md`: estado vivo de la iniciativa.

## Convenciones del proyecto

- Autorar y revisar contenido canónico únicamente en este repositorio; nunca
  editar el ZIP publicado ni una copia instalada de forma independiente.
- Mantener tres roles distintos: Git = fuente distribuible; Obsidian = memoria
  durable/evidencia completa; skills instaladas = despliegue operativo.
- Toda invariante de dominio aceptada debe existir en el repo, en su nota
  Obsidian y en la skill activa correspondiente. Un artefacto sin consumidor de
  skill usa `not_applicable` con motivo; una invariante de dominio no puede
  hacerlo.
- Las copias instaladas solo cambian mediante promoción post-gate con staging,
  validación y readback por hash; nunca mediante edición independiente.
- Cada archivo distribuible debe declarar una fuente canónica en el inventario
  de procedencia de la fase 01.
- Cada API, firma o cifra técnica nueva necesita build/commit y evidencia
  `path:line`; una búsqueda es una pista, no una verificación.
- En planificación pública se usan aliases de procedencia (`VANILLA`,
  `CF_ROOT`, `VAULT`, `SKILL_SOURCE`); la fase 01 los resuelve mediante el
  source map sin versionar rutas privadas.
- No incluir rutas privadas, credenciales, vanilla/PBOs ni assets de terceros.
- Mantener las licencias de terceros y no copiar GPL, DPL-ND o CC-NC al pack MIT.
- El core de validación y packaging debe ser determinista y sin red.
- La petición vigente del usuario es ejecución y revisión por Codex, sin Claude
  ni subagentes, salvo autorización posterior explícita.

## Estado actual

El estado vivo se mantiene únicamente en [`HANDOFF.md`](HANDOFF.md).

## Decisiones clave

- [`decisions/001-canonical-source-and-baseline.md`](decisions/001-canonical-source-and-baseline.md)
  — este Git es la fuente; el ZIP anterior queda como baseline inmutable.
- [`decisions/002-three-surface-promotion.md`](decisions/002-three-surface-promotion.md)
  — todo conocimiento aceptado se enruta a repo, Obsidian y skills aplicables.

## Gotchas conocidos

- El baseline tiene 138 archivos; `MANIFEST.txt` declara 137 porque no se
  contabiliza a sí mismo, sin explicitar esa convención.
- Ocho de catorce skills incumplen el máximo oficial de 1024 caracteres del
  campo `description`.
- Las catorce skills del ZIP divergen de sus fuentes locales actuales.
- La promoción automatizada todavía no existe; no escribir copias instaladas
  hasta cerrar la fase 01.
- El validador oficial `skills-ref` necesita `PYTHONUTF8=1` en Windows PowerShell
  clásico para no intentar leer UTF-8 como cp1252.
- El audit preliminar detectó 53 links locales aparentemente rotos; el validador
  definitivo debe ignorar falsos enlaces dentro de fences de código.
- `check_dayz_winding.py` compila pero produce un `SyntaxWarning` por `\m` en
  el texto de ayuda.

## Enlaces

- DPF: [`product-spec.md`](product-spec.md)
- Roadmap: [`plans/2026-07-24-r21-master-roadmap.md`](plans/2026-07-24-r21-master-roadmap.md)
- Estado: [`HANDOFF.md`](HANDOFF.md)

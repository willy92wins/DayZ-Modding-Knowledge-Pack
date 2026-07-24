# Fase 01 — Foundation, procedencia y evaluaciones

> **Modo de ejecución:** Codex inline, sin Claude/subagentes. Este plan no
> autoriza publicar ni modificar copias instaladas.

## Objetivo y traza DPF

Cerrar A1–A8 y B1–B5. El resultado es una fuente reconciliada, validable y
reproducible sobre la que las fases de contenido puedan trabajar sin crear más
drift.

## Baseline verificado

- Commit raíz: `d48e2c1a02dacc97645a9e70d8bc1058e6dae9a5`.
- ZIP↔árbol: 138/138 hashes iguales.
- Skills: 14; `skills-ref`: 6 válidas, 8 con description >1024.
- Todas las 14 skills difieren de sus fuentes locales actuales.
- Vault notes: 8 idénticas y 7 distintas de la nota canónica homónima.
- py3d: 43 archivos idénticos, 2 rollout scripts distintos y 3 fixtures
  source-only.
- Tests: py3d 130 pass/10 skip; `compileall` OK con un SyntaxWarning.
- Licencia raíz ausente; scan preliminar de identidad/secretos limpio.

## Archivos previstos

- Crear: `sources/source-map.schema.json`
- Crear: `sources/source-map.json`
- Crear: `sources/local-roots.example.json`
- Crear local y excluir de Git: `sources/local-roots.json`
- Crear: `compatibility-matrix.md`
- Crear: `LICENSE`
- Crear: `THIRD_PARTY_NOTICES.md`
- Crear: `CONTRIBUTING.md`
- Crear: `CHANGELOG.md`
- Crear: `packctl/` y `tests/packctl/`
- Crear: `evals/schema.json`, `evals/cases/`, `evals/baselines/`
- Modificar: `.gitignore`, `README.md`, `MANIFEST.txt`
- Reconciliar: `skills/**`, `knowledge/**`, `tools/py3d/**`

## Task 0 — Contrato de implementación

- [ ] Crear `specs/2026-07-24-foundation-and-evidence.md`.
- [ ] Cerrar schema, severidades, exits, fixtures positivas/negativas y
  determinismo antes de escribir `packctl`.
- [ ] Etiquetar ejemplos ejecutables `[EXACT]` o `[DESIGN]`.
- [ ] Gate: checklist de feature spec completo y todos los criterios A/B de esta
  fase trazados a una fixture o revisión verificable.

## Task 1 — Source map y política de conflictos

- [ ] Definir schema v1 con `output_path`, `source_id`, `source_revision`,
  `source_hash`, `license`, `verification_level`, `decision` y
  `decision_evidence`.
- [ ] Separar IDs públicos de roots locales: el mapa versionado nunca guarda
  paths de usuario; `local-roots.json` no entra en Git ni en el ZIP.
- [ ] Inventariar los 138 archivos baseline.
- [ ] Emitir `SOURCE-UNMAPPED` si falta un archivo y
  `SOURCE-CONFLICT-UNDECIDED` si dos fuentes difieren sin adjudicación.
- [ ] Fijar explícitamente la convención del manifiesto: el count incluye o
  excluye el propio manifest, y validator/builder usan la misma.
- [ ] Gate: 138 entradas cubiertas y 0 conflictos silenciosos.

## Task 2 — Reconciliación de fuentes

- [ ] Comparar por contenido cada una de las 14 skills contra su fuente actual.
- [ ] Clasificar cada delta como `adopt`, `keep-pack`, `merge` o `reject`, con
  evidencia; nunca usar mtime como autoridad.
- [ ] Repetir para las 15 vault notes y el fork/rollout py3d.
- [ ] Mantener sanitización pública: una mejora válida con ruta privada se
  adapta, no se copia literalmente.
- [ ] Hacer un commit independiente por familia: skills, knowledge y py3d.
- [ ] Gate: `SOURCE-CONFLICT-UNDECIDED=0`.

## Task 3 — Validez y frontmatter de skills

- [ ] Acortar las ocho descriptions rechazadas sin perder triggers; mover
  detalle al cuerpo/references.
- [ ] Aplicar el test de caps y progressive disclosure a las 14 skills.
- [ ] Añadir por skill metadata durable de compatibilidad sin inventar
  frontmatter fuera de la especificación oficial.
- [ ] Ejecutar `skills-ref` con UTF-8 explícito en Windows.
- [ ] Añadir una fixture que excede 1024 y comprobar que el gate falla.
- [ ] Gate: 14/14 válidas; nuevas skills se descubren dinámicamente y también
  deben pasar.

## Task 4 — Licencias, privacidad y documentación

- [ ] Añadir MIT raíz únicamente sobre material propio.
- [ ] Mantener la licencia upstream de py3d y registrar atribuciones.
- [ ] Crear notices por componente; GPL/DPL-ND/CC-NC quedan como referencias,
  no payload.
- [ ] Documentar contribución, compatibilidad, breaking changes y update
  strategy.
- [ ] Añadir scanners por contenido para secretos, identidad, rutas absolutas
  y payloads de terceros.
- [ ] Gate: audit de release con 0 findings no allowlisted.

## Task 5 — `packctl`: validator y builder reproducible

- [ ] Implementar inventario, source-map validation, skill validation,
  Markdown-link validation con fences ignoradas, privacy/license checks,
  Python checks y py3d tests.
- [ ] Definir findings tipados con `code`, `severity`, `path`, `line`,
  `message` y `evidence`.
- [ ] Definir verdict JSON `PASS|WARN|FAIL` y exits estables:
  `0=sin findings bloqueantes`, `1=findings de validación`,
  `2=uso/configuración/error interno`.
- [ ] Builder por allowlist; orden, timestamps, permisos y encoding
  normalizados.
- [ ] Mutaciones dirigidas: private path, frontmatter largo, source unmapped,
  link roto, licencia ausente y archivo extra.
- [ ] Gate: dos builds del mismo commit tienen SHA-256 idéntico.

## Task 6 — Harness de evals piloto

- [ ] Definir schema para prompt, fixtures, assertions mecánicas, grader,
  evidence, tiempo, tokens, skill/baseline revision y verdict.
- [ ] Ejecutar en workspace temporal limpio.
- [ ] Pilotar tres familias: API/Enforce, UI y persistence.
- [ ] Añadir como negativos los contratos falsos detectados en StarDZ.
- [ ] Comparar skill actual contra snapshot anterior o ausencia de skill.
- [ ] Gate: cada run produce `grading.json`; un grader sin evidencia falla.

## Task 7 — Gates de cierre

- [ ] Checkout limpio y validator completo exit 0.
- [ ] Build reproducible ×2 con SHA idéntico.
- [ ] `git diff --check` limpio.
- [ ] Revisión fría Codex contra A/B.
- [ ] Actualizar `HANDOFF.md`, DPF y memoria durable.
- [ ] Commit de cierre de fase; no promover todavía a las instalaciones.

## Hard stops

- Cualquier `SOURCE-UNMAPPED` o conflicto sin decisión.
- Cualquier licencia desconocida en payload.
- Cualquier path/identidad privada en el ZIP.
- Cualquier skill inválida.
- Builder no determinista.
- Evals que solo puntúan narrativa sin evidencia.

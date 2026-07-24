# Fase 01 — Foundation, procedencia y evaluaciones

> **Modo de ejecución:** Codex inline, sin Claude/subagentes. Este plan no
> autoriza publicar. Las copias instaladas solo se modifican en Task 8, desde
> un commit validado y con readback.

> **Estado:** completado el 2026-07-24. Contenido promovido desde
> `7a25432febc112a957a7c1ef7a7d2c16c221b24f` mediante la transacción
> `c7b5366cc761a8038e52f6a2`; recibo create-only
> `promotions/receipts/c7b5366cc761a8038e52f6a2.json`. El cierre verificó
> 53/53 targets físicos, 67 aliases lógicos, cadena `COMMIT`, cero residuos,
> cero paths privados y recovery idempotente.

## Objetivo y traza DPF

Cerrar A1–A9 y B1–B5. El resultado es una fuente reconciliada, validable y
reproducible con promoción verificable a Obsidian y skills, sobre la que las
fases de contenido puedan trabajar sin crear más drift.

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
- Crear: `sources/claims.schema.json`
- Crear: `sources/claims.json`
- Crear: `sources/local-roots.example.json`
- Crear local y excluir de Git: `sources/local-roots.json`
- Crear: `compatibility-matrix.md`
- Crear: `LICENSE`
- Crear: `THIRD_PARTY_NOTICES.md`
- Crear: `CONTRIBUTING.md`
- Crear: `CHANGELOG.md`
- Crear: `packctl/` y `tests/packctl/`
- Crear: `tools/dayz-api-index/` o su módulo canónico dentro de `packctl/`
- Crear: `evals/schema.json`, `evals/cases/`, `evals/baselines/`
- Crear: `promotions/promotion-map.schema.json`
- Crear: `promotions/promotion-map.json`
- Crear: `promotions/local-targets.example.json`
- Crear local y excluir de Git: `promotions/local-targets.json`
- Crear: `promotions/receipts/`
- Crear: `.gitattributes`
- Modificar: `.gitignore`, `README.md`, `MANIFEST.txt`
- Reconciliar: `skills/**`, `knowledge/**`, `tools/py3d/**`
- Crear: `specs/checklists/2026-07-24-foundation-and-evidence.md`

## Task 0 — Contrato de implementación

- [x] Crear `specs/2026-07-24-foundation-and-evidence.md`.
- [x] Cerrar schema, severidades, exits, fixtures positivas/negativas y
  determinismo de build/promoción antes de escribir `packctl`.
- [x] Etiquetar ejemplos ejecutables `[EXACT]` o `[DESIGN]`.
- [x] Gate: checklist de feature spec completo y todos los criterios A/B de esta
  fase trazados a una fixture o revisión verificable.

## Task 1 — Source map y política de conflictos

- [x] Definir schema v1 con `output_path`, `distribution_role`
  (`payload|repo_only`), `output_hash`, inputs con `source_id`,
  `source_revision`, `source_hash`, `license`, `verification_level`,
  `decision` y `decision_evidence`.
- [x] Separar IDs públicos de roots locales: el mapa versionado nunca guarda
  paths de usuario; `local-roots.json` no entra en Git ni en el ZIP.
- [x] Inventariar los 138 archivos baseline y clasificar exactamente una vez
  todo archivo seguido por Git; solo `payload` alimenta el ZIP.
- [x] Declarar por separado miembros generados para evitar auto-hash del
  `manifest.json`.
- [x] Registrar caches, backups, fixtures regenerables, evidencia privada y
  otros inputs no adoptados en `excluded_inputs[]`, con hash y razón tipada;
  ningún input descubierto queda implícitamente descartado.
- [x] Crear claim registry para todo snippet/claim ejecutable introducido tras
  el baseline, con revisión, `path:line`, licencia, verificación y routing.
- [x] Emitir `SOURCE-UNMAPPED` si falta un archivo y
  `SOURCE-CONFLICT-UNDECIDED` si dos fuentes difieren sin adjudicación.
- [x] Fijar explícitamente la convención del manifiesto: el count incluye o
  excluye el propio manifest, y validator/builder usan la misma.
- [x] Gate: 138 entradas cubiertas y 0 conflictos silenciosos.

## Task 2 — Reconciliación de fuentes

- [x] Comparar por contenido cada una de las 14 skills contra su fuente actual.
- [x] Clasificar cada delta como `adopt`, `keep-pack`, `merge` o `reject`, con
  evidencia; nunca usar mtime como autoridad.
- [x] Repetir para las 15 vault notes y el fork/rollout py3d.
- [x] Mantener sanitización pública: una mejora válida con ruta privada se
  adapta, no se copia literalmente.
- [x] Hacer un commit independiente por familia: skills, knowledge y py3d.
- [x] Gate: `SOURCE-CONFLICT-UNDECIDED=0`.

## Task 3 — Validez y frontmatter de skills

- [x] Acortar las ocho descriptions rechazadas sin perder triggers; mover
  detalle al cuerpo/references.
- [x] Aplicar el test de caps y progressive disclosure a las 14 skills.
- [x] Añadir por skill metadata durable de compatibilidad sin inventar
  frontmatter fuera de la especificación oficial.
- [x] Ejecutar `skills-ref` con UTF-8 explícito en Windows.
- [x] Añadir una fixture que excede 1024 y comprobar que el gate falla.
- [x] Gate: 14/14 válidas; nuevas skills se descubren dinámicamente y también
  deben pasar.

## Task 4 — Licencias, privacidad y documentación

- [x] Añadir MIT raíz únicamente sobre material propio.
- [x] Mantener la licencia upstream de py3d y registrar atribuciones.
- [x] Crear notices por componente; GPL/DPL-ND/CC-NC quedan como referencias,
  no payload.
- [x] Documentar contribución, compatibilidad, breaking changes y update
  strategy.
- [x] Añadir scanners por contenido para secretos, identidad, rutas absolutas
  y payloads de terceros.
- [x] Gate: audit de release con 0 findings no allowlisted.

## Task 5 — `packctl`: validator y builder reproducible

- [x] Implementar inventario, source-map validation, skill validation,
  Markdown-link validation con fences ignoradas, privacy/license checks,
  Python checks y py3d tests.
- [x] Implementar `dayz-api-index` regenerable y read-only: allowed-roots,
  metadata de build/schema, scanner que excluye comentarios, query que conserva
  colisiones y rechazo fail-closed de escapes/mismatches.
- [x] Cubrir fixtures API clase activa/comentada/inexistente/colisión, escape,
  build mismatch y schema mismatch para cerrar B2 explícitamente.
- [x] Definir findings tipados con `code`, `severity`, `path`, `line`,
  `message` y `evidence`.
- [x] Definir verdict JSON `PASS|WARN|FAIL` y exits estables:
  `0=sin findings bloqueantes`, `1=findings de validación`,
  `2=uso/configuración/error interno`.
- [x] Builder por allowlist; orden, timestamps, permisos y encoding
  normalizados.
- [x] Fijar LF mediante `.gitattributes`, recalcular hashes sobre bytes
  canónicos y demostrar validator exit 0 desde un clon limpio aun con
  `core.autocrlf=true`.
- [x] Mutaciones dirigidas: private path, frontmatter largo, source unmapped,
  link roto, licencia ausente y archivo extra.
- [x] Gate: dos builds del mismo commit tienen SHA-256 idéntico.

## Task 6 — Harness de evals piloto

- [x] Definir schema para prompt, fixtures, assertions mecánicas, grader,
  evidence, tiempo, tokens, skill/baseline revision y verdict.
- [x] Ejecutar en workspace temporal limpio.
- [x] Pilotar tres familias: API/Enforce, UI y persistence.
- [x] Añadir como negativos los contratos falsos detectados en StarDZ.
- [x] Comparar skill actual contra snapshot anterior o ausencia de skill.
- [x] Gate: cada run produce `grading.json`; un grader sin evidencia falla.

## Task 7 — Routing y promoción de tres superficies

- [x] Definir por artefacto `artifact_id`, `repo_path`, `vault_target_id`,
  `skill_target_ids`, `applicability`, `not_applicable_reason`,
  `source_commit` y hashes esperados.
- [x] Mantener roots físicos únicamente en `promotions/local-targets.json`;
  mapa y recibos versionados usan IDs lógicos y nunca rutas privadas.
- [x] Requerir repo + Obsidian para todo conocimiento aceptado. Requerir skill
  para toda invariante de dominio; `not_applicable` solo vale para gobierno o
  tooling sin consumidor de skill y exige motivo.
- [x] `[DESIGN]` Separar `promote --check` read-only de `promote --apply`.
  `check` emite commit, hash previo y hash esperado; `apply` revalida por
  compare-and-swap bajo lock antes de escribir.
- [x] `[DESIGN]` `apply` usa staging en el mismo volumen, valida el árbol
  completo, crea y verifica backup, reemplaza solo targets allowlisted,
  verifica readback y revierte en orden inverso ante cualquier fallo.
- [x] Resolver junctions componente a componente, rechazar escapes/loops,
  preservar el enlace y deduplicar aliases físicos sin omitir readback de cada
  target lógico. Plugins/cachés nunca son roots gestionados.
- [x] Promover a Obsidian mediante snapshot exacto e inmutable por
  `{artifact_id}/{source_commit}`; no reemplazar notas privadas canónicas.
- [x] Cubrir fixtures: routing ausente, hash distinto, target no configurado,
  target read-only, copia parcial, skill legacy con triggers solapados y
  `not_applicable` inválido.
- [x] Gate: dry-run produce `PROMOTION-UNROUTED=0` y
  `PROMOTION-DRIFT=0`.

## Task 8 — Gates de cierre y primera promoción

- [x] Crear un commit limpio con el contenido reconciliado.
- [x] Checkout limpio y validator completo exit 0.
- [x] Build reproducible ×2 con SHA idéntico.
- [x] Ejecutar promoción desde ese commit a Obsidian y todos los targets
  de skills configurados y escribibles.
- [x] Resolver explícitamente si el target físico externo de
  `rigorous-data-audit` se añade a `allowed_physical_roots`; sin autorización,
  mantener fail-closed y no declarar la fase cerrada.
- [x] Leer de vuelta cada destino, verificar hashes y crear un recibo sin rutas
  privadas; un fallo deja verdict no-cero y no declara la fase cerrada.
- [x] `git diff --check` limpio.
- [x] Revisión fría Codex contra A/B.
- [x] Actualizar `HANDOFF.md`, DPF y memoria durable.
- [x] Commit separado para recibo/handoff de promoción.

## Hard stops

- Cualquier `SOURCE-UNMAPPED` o conflicto sin decisión.
- Cualquier licencia desconocida en payload.
- Cualquier path/identidad privada en el ZIP.
- Cualquier skill inválida.
- Builder no determinista.
- Evals que solo puntúan narrativa sin evidencia.
- Cualquier `PROMOTION-UNROUTED`, `PROMOTION-DRIFT`, destino no allowlisted o
  promoción parcial.
- Cualquier junction/reparse point que resuelva fuera de roots físicos
  allowlisted o dentro de plugin/cache.
- Cualquier rollback no verificado; queda exit `2`, journal/backup e intervención
  obligatoria.
- Invariante de dominio marcada `not_applicable` para skills.

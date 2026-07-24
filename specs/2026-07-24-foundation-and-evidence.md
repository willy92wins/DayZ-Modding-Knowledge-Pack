# Feature Spec: Foundation, evidence and three-surface promotion

**Mod / PBO**: N/A — tooling y contenido del DayZ Modding Knowledge Pack
**Date**: 2026-07-24
**Status**: Ready-to-implement
**Plan**: [`plans/2026-07-24-01-foundation-and-evidence.md`](../plans/2026-07-24-01-foundation-and-evidence.md)

## Context / Why

El baseline distribuido es íntegro, pero sus 14 skills, 15 notas y fork py3d ya
divergen de fuentes locales posteriores. Además, el repositorio contiene ahora
documentos internos que no deben entrar automáticamente en el ZIP. Esta fase
crea una única cadena verificable: reconciliar → validar → evaluar → construir
→ promocionar desde un commit limpio.

## Terminología canónica

- **Fuente**: input histórico o técnico fijado por ID, revisión y hash.
- **Artefacto**: archivo o árbol lógico gestionado por el pack.
- **Payload**: miembro público tomado del repositorio e incluido en el ZIP.
- **Repo-only**: archivo seguido por Git que queda fuera del ZIP.
- **Generado**: miembro del ZIP creado por el builder y ausente del árbol Git.
- **Target lógico**: ID público de destino; nunca contiene una ruta física.
- **Target físico**: root local no versionado que resuelve un target lógico.
- **Operación física**: una única escritura deduplicada tras resolver aliases y
  junctions.
- **Snapshot de vault**: copia exacta e inmutable de la proyección pública bajo
  un commit; no sustituye notas privadas existentes.
- **Invariante de dominio**: conocimiento reutilizable cuyo siguiente proyecto
  debe poder recuperar desde una skill activa.

## Acceptance Scenarios

La feature no modifica ni ejecuta DayZ runtime. En todos los escenarios,
**Repro in-game = N/A** y el comando offline indicado es el gate autoritativo.

1. **Given** un checkout limpio del commit reconciliado,
   **When** se ejecuta `python -m packctl gate --root . --report-dir <dir>`,
   **Then** valida fuentes, claims, skills, links, privacidad, licencias, Python,
   py3d, API index, evals y dos builds; devuelve exit `0` y verdict `PASS`.
   - **Repro in-game**: N/A — inspeccionar `gate.json`, los dos SHA-256 y el
     exit del comando offline.

2. **Given** una copia fixture con un archivo Git sin clasificación o un input
   divergente sin decisión,
   **When** se ejecuta `python -m packctl validate --root <fixture>`,
   **Then** devuelve exit `1` y exactamente `SOURCE-UNMAPPED` o
   `SOURCE-CONFLICT-UNDECIDED`, sin alterar la fixture.
   - **Repro in-game**: N/A — comparar hash de árbol antes/después.

3. **Given** fixtures con `description` de 1025 caracteres, link local roto,
   ruta privada y licencia ausente,
   **When** se ejecuta el validador,
   **Then** cada mutación produce su código estable, verdict `FAIL` y exit `1`;
   el control sin mutación no produce esos códigos.
   - **Repro in-game**: N/A — assertions exactas sobre el JSON.

4. **Given** un corpus Enforce con clase activa, clase comentada, símbolo
   inexistente y dos declaraciones homónimas,
   **When** se construye y consulta `dayz-api-index`,
   **Then** solo se indexan declaraciones activas, la inexistente devuelve cero
   resultados y la colisión devuelve ambos resultados ordenados.
   - **Repro in-game**: N/A — ejecutar fixtures `api_index_*`.

5. **Given** un índice con build o schema diferente del solicitado, o un include
   que escapa del root permitido,
   **When** se consulta o construye el índice,
   **Then** falla cerrado con exit `1` y un código `API-*`, sin leer fuera del
   root.
   - **Repro in-game**: N/A — fixture con canary externo que no aparece en la
     evidencia de lectura.

6. **Given** los casos piloto API, UI y persistence y sus variantes current y
   baseline/absent,
   **When** se ejecuta `python -m packctl eval run`,
   **Then** cada variante corre en un workspace temporal limpio y emite
   `grading.json`, evidencia, duración y tokens; un grader sin evidencia falla.
   - **Repro in-game**: N/A — validar los JSON contra schema y sus hashes.

7. **Given** un plan de promoción verde y dos targets lógicos de skill que
   resuelven al mismo destino físico,
   **When** se aplica el plan,
   **Then** se realiza una sola operación física, se verifican ambos IDs lógicos
   por readback y se crea un recibo sin rutas privadas.
   - **Repro in-game**: N/A — fixture de junction/alias y contador de operaciones.

8. **Given** un `promote --check` ya emitido,
   **When** el target cambia antes de `promote --apply`,
   **Then** el compare-and-swap detecta el hash distinto, devuelve exit `1` y no
   escribe ningún target.
   - **Repro in-game**: N/A — hashes pre/post de todos los targets idénticos al
     estado inmediatamente anterior a `apply`.

9. **Given** tres targets físicos y fault injection después del primer replace,
   **When** falla `promote --apply`,
   **Then** restaura en orden inverso todos los targets tocados, verifica sus
   hashes originales, conserva journal/backup y no emite recibo de éxito.
   - **Repro in-game**: N/A — assertions de fault injection en cada frontera I/O.

10. **Given** una nota privada existente en Obsidian y su ruta de snapshot,
    **When** se promociona la proyección pública,
    **Then** la nota privada conserva exactamente su hash y el snapshot
    `{artifact_id}/{source_commit}` coincide con el hash del repo.
    - **Repro in-game**: N/A — readback byte a byte de ambos archivos.

11. **Given** un junction cuyo destino resuelve fuera de todas las raíces
    físicas allowlisted o dentro de un root plugin/cache excluido,
    **When** se comprueba o aplica la promoción,
    **Then** falla cerrado antes de staging con `PROMOTION-TARGET-ESCAPE` o
    `PROMOTION-TARGET-FORBIDDEN`.
    - **Repro in-game**: N/A — canary externo y hashes de targets sin cambios.

12. **Given** una promoción interrumpida que no logra completar rollback,
    **When** el operador vuelve a ejecutar `promote --check`,
    **Then** recibe exit `2`, referencia al journal/backup local y pasos de
    intervención; nunca recibe verdict `PASS`.
    - **Repro in-game**: N/A — fixture de rollback fallido y recuperación manual.

13. **Given** una fuente comparada que contiene caches, backups, fixtures
    generadas o evidencia privada que no pertenece al payload,
    **When** se valida el source map,
    **Then** cada input excluido conserva ID de fuente, path relativo, hash y
    motivo tipado; no aparece como artefacto ni queda perdido sin adjudicación.
    - **Repro in-game**: N/A — fixture con un `.pyc`, un `.bak` y una fixture
      regenerable; los tres quedan excluidos de la allowlist y cubiertos una vez.

## Success Criteria

- **SC-001 / A1–A2**: 100% de archivos seguidos por Git tiene exactamente una
  clasificación `payload` o `repo_only`; 100% del payload tiene hash, licencia y
  procedencia; `SOURCE-UNMAPPED=0` y
  `SOURCE-CONFLICT-UNDECIDED=0`.
- **SC-002 / A3**: todas las carpetas descubiertas dinámicamente que contienen
  `SKILL.md` pasan el validador interno y el `skills-ref` pineado; en el baseline
  reconciliado son 14/14 y ningún `description` supera 1024 caracteres.
- **SC-003 / A4**: dos builds limpios del mismo commit producen ZIPs
  byte-idénticos y el mismo SHA-256.
- **SC-004 / A5**: `manifest.json` valida contra schema; `payload_file_count`
  coincide con los archivos source-backed, `archive_member_count` coincide con
  los miembros reales y se cumple
  `archive_member_count = payload_file_count + 1`.
- **SC-005 / A6**: cada payload tiene cobertura de licencia; MIT raíz y notices
  preservan la licencia upstream de py3d; payload GPL/DPL-ND/CC-NC = 0.
- **SC-006 / A7**: la matriz enumera 100% de skills con build, fecha,
  dependencias, breaking changes, nivel de verificación y evidencia o
  `unknown` explícito.
- **SC-007 / A8**: el ZIP construido produce 0 secretos, identidades, rutas
  privadas y links relativos rotos no allowlisted; el scanner no imprime el
  valor completo de un secreto.
- **SC-008 / A9**: cada artefacto de conocimiento tiene repo + al menos un
  destino vault; cada invariante de dominio tiene además los dos targets lógicos
  de skill; `PROMOTION-UNROUTED=0` y
  `PROMOTION-DRIFT=0`.
- **SC-009 / B1**: cada claim ejecutable introducido después del baseline lleva
  `claim_id` y registro con revisión, `path:line`, licencia, fecha, nivel de
  verificación y `promotion_artifact_id`; findings sin registro = 0.
- **SC-010 / B2**: las fixtures active/commented/missing/collision devuelven
  respectivamente `1/0/0/2` resultados; build mismatch, schema mismatch y path
  escape fallan cerrados con exit `1`.
- **SC-011 / B3**: cada run de eval emite un `grading.json` válido con
  `duration_ms ≥ 0`, tokens enteros `≥ 0`, revisión de skill/baseline, assertions
  y evidencia; tres familias piloto comparan current con baseline/absent.
- **SC-012 / B4**: los seis negativos StarDZ (`autoptr`, overload, `Managed`,
  `JsonLoadFile`, `OnDrop`, Dabs) son rechazados por assertions mecánicas; el
  control correcto de cada caso pasa.
- **SC-013 / B5**: un único `packctl gate` limpio devuelve exit `0`; cada mutación
  dirigida devuelve exit `1` y su código estable; uso/configuración/error interno
  devuelve exit `2`.
- **SC-014 / promoción**: `check` registra el hash anterior y esperado de cada
  target; `apply` vuelve a comprobarlos bajo lock antes de escribir.
- **SC-015 / recuperación**: fault injection en cada frontera
  stage→validate→backup→replace→readback→receipt conserva el estado anterior o,
  si la recuperación también falla, deja backup+journal verificables y exit `2`.
- **SC-016 / aliases**: N targets lógicos que resuelven al mismo path físico
  producen una operación física y N readbacks lógicos.
- **SC-017 / privacidad de routing**: source map, promotion map, schemas,
  ejemplos y recibos versionados contienen 0 roots físicos; los planes locales,
  journals y backups están ignorados por Git y excluidos del ZIP.
- **SC-018 / regresión py3d**: `python -m pytest -q -p no:cacheprovider
  tools/py3d/tests` mantiene al menos 130 pass y exactamente los skips
  adjudicados; cualquier test fallido bloquea el gate.
- **SC-019 / determinismo JSON**: findings, registros, manifests y grading se
  ordenan por claves canónicas; dos ejecuciones sobre los mismos bytes producen
  JSON byte-idéntico salvo campos de observación explícitamente excluidos del
  artefacto reproducible.
- **SC-020 / inputs excluidos**: todo archivo descubierto bajo una fuente
  reconciliada que no se adopta como artefacto tiene exactamente una entrada
  `excluded_inputs[]` con hash y razón tipada; caches, backups, fixtures
  regenerables y evidencia privada nunca entran en el ZIP.

## Scope — Out of scope

- No publicar, hacer push, crear release GitHub ni subir Workshop.
- No modificar ninguna skill instalada antes del gate y Task 8.
- No escribir en roots de plugins, caches o aplicaciones.
- No adjudicar por `mtime` ni copiar literalmente rutas privadas.
- No reemplazar ni «sanitizar» notas privadas existentes en Obsidian.
- No prometer transacción ACID frente a procesos externos que ignoren el lock;
  sí se exige CAS antes de escribir y readback después.
- No ejecutar Enforce, DayZDiag, servidor o cliente; esta fase indexa texto y
  valida artefactos offline.
- No convertir el índice lexical en autoridad semántica del engine.
- No crear todavía `dayz-ui`, `dayz-persistence` u otras nuevas skills.
- No resolver en Fase 01 la migración
  `dayz-ui-development` → `dayz-ui`.
- No introducir writer ODOL ni cambios de formato persistente DayZ.

## Assumptions

- **RESOLVED**: Git es fuente; Obsidian es memoria/snapshot; skills instaladas
  son despliegues. Evidencia: ADR 001/002.
- **RESOLVED**: los targets lógicos obligatorios son
  `claude_user_skills` y `agents_user_skills`; plugins/caches quedan excluidos.
  Evidencia: aprobación del usuario 2026-07-24.
- **RESOLVED**: `payload` y `repo_only` se clasifican por archivo; el source map
  es la allowlist del builder. Los generados se declaran aparte.
- **RESOLVED**: el source commit y hashes de una promoción viven en el plan
  local/recibo, no dentro del mapa autorreferente.
- **RESOLVED**: Obsidian recibe snapshots exactos e inmutables; la memoria
  privada se mantiene mediante el protocolo durable y no se sobreescribe.
- **ASSUMED, deferred**: el junction físico de `rigorous-data-audit` será
  autorizado explícitamente o la primera promoción lo bloqueará. Se resuelve
  antes de Task 8 porque afecta qué path puede escribirse, no el diseño del
  promotor.
- **ASSUMED, deferred**: la adjudicación `adopt|keep_pack|merge|reject` de cada
  delta se decide en Tasks 1–2; ninguna implementación depende de una autoridad
  aún no adjudicada.

## Contrato de datos

### 1. Source map v1

**[DESIGN]** `sources/source-map.json` tiene:

- `schema_version = 1`, `baseline_commit`, `claim_baseline_commit`,
  `release_id`, `dayz_build`;
- `sources[]` con `source_id`, `kind`, `revision`, `license` y, cuando aplica,
  `local_root_id`; ningún root físico;
- `artifacts[]` con `artifact_id`, `output_path`, `distribution_role`,
  `license`, `verification_level`, `routing_artifact_id`, `hash_policy`
  (`sha256|self_exempt`) e `inputs[]`;
- `excluded_inputs[]` con `source_id`, `source_revision`, `source_path`,
  `source_hash`, `reason` y `decision_evidence`;
- `generated_artifacts[]` para miembros no seguidos por Git.

Cada `input` contiene `source_id`, `source_revision`, `source_path`,
`source_hash`, `decision` (`adopt|keep_pack|merge|reject`) y
`decision_evidence`. Cada payload contiene además `output_hash`. Cada
`repo_only` exige `distribution_reason`; el propio source map no intenta
hashearse a sí mismo: es el único artefacto permitido con
`hash_policy=self_exempt`, no lleva `output_hash` y sus inputs apuntan al spec e
inventario que lo generan, nunca a sus propios bytes. Paths son relativos
POSIX, sin drive, raíz, `..`, NUL ni backslash.

**[EXACT]** Todos los archivos versionados son texto en Fase 01 y
`.gitattributes` fija `* text eol=lf`. Los SHA-256 de output se calculan sobre
esos bytes LF, de modo que un checkout limpio produce los mismos hashes aunque
la configuración global del host use `core.autocrlf=true`
(`.gitattributes:1`; `tests/packctl/test_validation.py:31-43`). Añadir formatos
binarios en fases posteriores exige declararlos `-text` antes de versionarlos.

Todo archivo seguido por Git aparece una vez en `artifacts`. Solo
`distribution_role=payload` entra en la allowlist. Un `generated_artifact` no
puede existir como archivo seguido por Git.

`excluded_inputs[].reason` pertenece al enum
`generated|cache|backup|project_evidence|superseded|license_restricted`.
Una exclusión registra el input comparado pero no crea un output; si contenía
conocimiento durable, `decision_evidence` identifica el artefacto que lo
asimiló o explica por qué quedó superseded. Un mismo par
`source_id + source_path` no puede aparecer a la vez como input de artefacto y
como excluido.

### 2. Claim registry v1

**[DESIGN]** `sources/claims.json` registra `claim_id`, `artifact_id`,
`line_start`, `line_end`, `source_id`, `source_revision`, `evidence_locator`,
`license`, `observed_at`, `verification_level` y `promotion_artifact_id`.

Desde `claim_baseline_commit`, cada fence ejecutable nuevo lleva inmediatamente
antes `<!-- claim: CLAIM-ID -->`; cada recomendación ejecutable en prosa usa
`[EXACT][CLAIM-ID]`. `[DESIGN]` no se presenta como API real y no requiere
fuente técnica, pero sí queda dentro del artefacto enrutado. Un claim puede
cubrir un bloque/rango continuo; no puede cubrir rangos disjuntos.

### 3. Finding, report y exits

**[DESIGN]** Todo finding contiene exactamente `code`, `severity`
(`error|warning|info`), `path`, `line`, `message` y `evidence`. La evidencia de
secretos se redacta. Orden canónico:
`severity_rank, code, path, line, message`.

El report contiene `schema_version`, `command`, `source_commit`, `verdict`,
`findings`, `checks` y `artifacts`. `FAIL` = al menos un `error`; `WARN` = cero
errores y al menos un `warning`; `PASS` = ninguno. Exits:

- `0`: ejecución válida sin findings bloqueantes (`PASS` o `WARN`);
- `1`: findings de validación o precondición fail-closed;
- `2`: uso, configuración, lock/journal irrecuperable o error interno.

Los comandos no escriben fuera de outputs declarados. `validate`, `gate`,
`api-index query` y `promote --check` son read-only respecto a fuentes/targets.

### 4. Manifest y ZIP

**[DESIGN]** El builder incluye todos los payloads ordenados y un único generado
`manifest.json`. El `MANIFEST.txt` versionado es payload normal.
`manifest.json` se excluye de su propia lista/hash:

- `payload_file_count` cuenta los source-backed, incluido `MANIFEST.txt`;
- `archive_member_count` cuenta todos los miembros, incluido `manifest.json`;
- por contrato, `archive_member_count = payload_file_count + 1`.

El manifest declara schema, release, commit, DayZ build, source-map schema,
licencias y SHA-256 de cada payload. JSON = UTF-8, LF, claves ordenadas,
separadores compactos y newline final.

ZIP usa paths POSIX ordenados, sin entradas de directorio, método `STORED`,
timestamp fijo `1980-01-01 00:00:00`, permisos file `0644`, `create_system=3`,
comentario vacío y nombres UTF-8. El builder rechaza repo sucio, hashes distintos
del source map, symlinks/reparse points en payload y output dentro del payload.

### 5. DayZ API index v1

**[DESIGN]** `python -m packctl api-index build` recibe IDs lógicos de source,
build y revisión, resueltos por `sources/local-roots.json`. Solo acepta includes
relativos contenidos en roots allowlisted y rechaza cualquier escape tras
resolver enlaces.

Produce `metadata.json` e `index.jsonl`. Metadata fija `schema_version`,
`dayz_build`, `source_id`, `source_revision` y tree digest. Cada record contiene
`symbol`, `kind`, `container`, `signature`, `relative_path`, `line`,
`source_revision` y `record_hash`. Orden:
`symbol, kind, container, relative_path, line`. `record_hash` es SHA-256 del
JSON canónico del record sin `record_hash`.

El scanner preserva líneas al retirar comentarios `//` y `/*…*/`, no indexa
declaraciones comentadas y devuelve todas las colisiones/overloads. `query`
requiere build y schema esperados; mismatch falla cerrado. El índice prueba
existencia lexical de una declaración, no side, runtime ni implementación
nativa.

### 6. Evals v1

**[DESIGN]** Cada case fija `case_id`, `family`, `prompt`, `fixtures`,
`assertions`, `grader`, `required_evidence` y variantes. Cada run fija
`skill_revision`, `baseline_revision|absent`, `runner_id`, response, hashes,
`duration_ms`, `tokens_input`, `tokens_output`, `tokens_total`, assertions,
evidence y verdict.

El runner es un ID lógico configurado localmente; no se versionan credenciales
ni comandos privados. La fixture runner permite validar el harness sin red.
Cada variante usa un directorio temporal nuevo con solo sus inputs declarados.
El grader falla si una assertion aprobada no referencia evidencia existente.

### 7. Promotion map y transacción v1

**[EXACT]** `promotions/promotion-map.json` contiene rutas, no estado de una
ejecución. Cada entrada fija `artifact_id`, `repo_path`, `artifact_kind`,
`applicability`, `vault_targets[]`, `skill_target_ids[]` y, cuando no aplica,
`not_applicable_reason`. `domain_invariant` exige ambos IDs de skills;
`governance|tooling` puede omitirlos con motivo. Repo y vault siempre son
obligatorios.

`promotions/local-targets.json` y los planes/journals/backups locales están
ignorados. La configuración local contiene roots físicos, ownership
`user_owned`, capacidad `writable`, roots físicos permitidos, roots prohibidos,
staging y backup. Ningún target descubierto automáticamente es escribible.

`promote --check`:

1. exige repo limpio y commit exacto;
2. valida routing y contenido fuente;
3. resuelve cada target componente a componente;
4. rechaza loops, escapes, plugins/caches, targets no configurados/read-only;
5. deduplica paths físicos case-insensitive sin perder IDs lógicos;
6. calcula `before_digest` y `after_digest`;
7. emite plan local con `transaction_id`, commit, digests y operaciones.

Para árboles, tree digest = SHA-256 de concatenar, por cada archivo ordenado,
`relative_path UTF-8`, byte NUL, SHA-256 lowercase del archivo y LF. Para un
artefacto `file`, digest = SHA-256 de sus bytes, independiente del basename del
snapshot. Un target ausente usa el sentinel `absent`
(`packctl/common.py:307-323`).

`promote --apply --plan <local-plan>`:

1. adquiere locks exclusivos del sistema operativo por root físico, en orden
   canónico;
2. vuelve a validar bajo lock plan sellado, contratos, commit, repo limpio,
   routing, aliases, source digests y todos los `before_digest`;
3. publica atómicamente una transacción que ya contiene `plan.json` y
   `PENDING` durables;
4. crea staging en el mismo volumen, valida el árbol completo y registra
   `STAGE_READY`;
5. crea backup durable, verifica `before_digest`, repite CAS y registra
   `BACKUP_READY`;
6. mueve PRE a `.old`, publica staging, verifica cada destino físico y registra
   `TARGET_PUBLISHED`;
7. verifica readback por operación física y por cada ID lógico;
8. escribe snapshot vault inmutable
   `{artifact_id}/{source_commit}` sin tocar notas privadas;
9. registra `POST_VERIFIED`, vuelve a comprobar todos los POST y aliases,
   sella `COMMIT` con el hash exacto del recibo y publica ese recibo
   create-only.

Ante excepción capturable antes de `COMMIT`, revierte en orden inverso, verifica
los hashes originales y solo entonces registra `ABORT`. Ante terminación del
proceso, `promote --recover` continúa la misma adjudicación: sin `COMMIT`
restaura todos los PRE; con `COMMIT` exige todos los POST y solo completa el
recibo sellado. Un digest ajeno a PRE/POST, una cadena inválida o un rollback
incompleto devuelve exit `2`, conserva la evidencia y exige intervención.
Nunca declara éxito parcial. Un plan cuyo target ya coincide es idempotente:
hace readback, no replace (`packctl/promotion.py:1825-2014,2078-2443`).

El recibo versionado contiene schema, transaction, source commit, artifact IDs,
target IDs lógicos, aliases físicos opacos, before/after digests, verdict y
fecha UTC; contiene cero rutas físicas. Los backups no se borran
automáticamente en esta fase.

## CLI pública

Todos los siguientes símbolos son **[EXACT]** y quedan congelados para Fase 01
(`packctl/cli.py:17-76,101-170`).
Los valores entre `<...>` son metasyntaxis de argumento, no placeholders de
diseño pendientes:

- `python -m packctl validate --root <repo> --report <json>`
- `python -m packctl build --root <repo> --output <zip> --report <json>`
- `python -m packctl gate --root <repo> --report-dir <dir>`
- `python -m packctl api-index build|query ...`
- `python -m packctl eval run --case <id> --variant <id> --out <dir>`
- `python -m packctl promote --check --plan <local-json>`
- `python -m packctl promote --apply --plan <local-json>`
- `python -m packctl promote --recover --transaction-root <local-path>`

Argumento ausente/inválido devuelve `2`. Finding de contenido devuelve `1`.
`--root` y outputs se resuelven antes de operar y se comprueba su contención.

## Fixtures obligatorias

- `source_clean`, `source_unmapped`, `source_conflict`, `source_private_root`.
- `skill_clean`, `skill_description_1025`, `skill_extra_frontmatter`.
- `links_clean`, `links_broken`, `links_in_fence`.
- `privacy_clean`, `privacy_private_path`, `privacy_secret_redacted`.
- `license_clean`, `license_missing`, `license_forbidden_payload`.
- `manifest_count`, `build_extra_file`, `build_dirty`, `build_reparse`.
- `api_index_active`, `api_index_commented`, `api_index_missing`,
  `api_index_collision`, `api_index_build_mismatch`,
  `api_index_schema_mismatch`, `api_index_escape`.
- `eval_api`, `eval_ui`, `eval_persistence`, `eval_missing_evidence` y los seis
  negativos StarDZ con controles correctos.
- `promotion_clean`, `promotion_unrouted`, `promotion_drift`,
  `promotion_target_changed`, `promotion_target_missing`,
  `promotion_target_readonly`, `promotion_alias`, `promotion_escape`,
  `promotion_forbidden`, `promotion_partial`, `promotion_rollback_failed`,
  `promotion_legacy_overlap`, `promotion_invalid_not_applicable`,
  `promotion_vault_preserves_private`.

Cada fixture negativa tiene un único defecto primario para que el código
esperado sea inequívoco. Las fixtures de fault injection iteran todas las
fronteras I/O, no solo una.

## Forward Contract

| Consumer | Symbol it reads | Kind | Verify status |
|---|---|---|---|
| `packctl source` | `sources/source-map.json` v1 | JSON contract | `[DESIGN]` `specs/2026-07-24-foundation-and-evidence.md:219-240` |
| `packctl claims` | `sources/claims.json` v1 | JSON contract | `[DESIGN]` `specs/2026-07-24-foundation-and-evidence.md:242-252` |
| `packctl validate` | finding/report/exits v1 | CLI + JSON | `[DESIGN]` `specs/2026-07-24-foundation-and-evidence.md:254-270` |
| `packctl build` | `manifest.json` + ZIP profile v1 | archive contract | `[DESIGN]` `specs/2026-07-24-foundation-and-evidence.md:272-289` |
| `packctl api-index` | metadata/index JSONL v1 | CLI + JSONL | `[DESIGN]` `specs/2026-07-24-foundation-and-evidence.md:291-309` |
| `packctl eval` | case/run/grading v1 | JSON contract | `[DESIGN]` `specs/2026-07-24-foundation-and-evidence.md:311-322` |
| `packctl promote` | promotion map/plan/receipt v1 | CLI + JSON | `[DESIGN]` `specs/2026-07-24-foundation-and-evidence.md:324-390` |
| external skill gate | allowed fields/caps | pinned reference | `AGENT_SKILLS_REF/skills-ref/src/skills_ref/validator.py:10-22,70-84,104-147` |
| py3d regression gate | current suite | pytest suite | `tools/py3d/tests` y DPF `product-spec.md:117` |

Ningún consumidor depende de una API DayZ sin verificar.

## Verification plan

| Criterion | Verification | Where |
|---|---|---|
| SC-001, SC-009 | source/claim schemas + cobertura Git + mutaciones | offline `pytest tests/packctl` |
| SC-002 | internal validator + pinned `skills-ref`, UTF-8 explícito | offline gate |
| SC-003, SC-004, SC-019 | build ×2 en directorios limpios + byte/hash diff | offline gate |
| SC-005–SC-007 | license/privacy/link fixtures y scan del ZIP final | offline gate |
| SC-008, SC-014–SC-017 | promotion fixtures, CAS, aliases, fault injection y readback | offline `pytest tests/packctl` + Task 8 |
| SC-010 | corpus API index positivo/negativo | offline `pytest tests/packctl` |
| SC-011, SC-012 | schema de grading + tres pilotos + StarDZ negatives | offline eval harness |
| SC-013 | clean gate y matriz de exits/códigos | offline subprocess tests |
| SC-018 | `python -m pytest -q -p no:cacheprovider tools/py3d/tests` | offline gate |
| SC-020 | fixture de inputs excluidos + unicidad contra inputs adoptados | offline `pytest tests/packctl` |
| Scenarios 1–13 | no runtime DayZ; comandos y fault injection descritos arriba | offline |

## Crash-recovery / intervención

Esta feature toca copias persistentes de skills y snapshots de Obsidian. Antes
de Task 8 se ejecutó `rigorous-data-audit` sobre CAS, backup, rollback,
idempotencia, termination injection y recibos. El operador nunca borra backups
automáticamente. Si existe journal incompleto, lock vivo, evidencia no
adjudicable o rollback fallido, `apply` se bloquea con exit `2` hasta ejecutar
recovery o intervenir fuera de la herramienta.

Amendment aprobado el 2026-07-24: la operación separada es `promote --recover`.
Usa journal append-only encadenado, locks del sistema operativo, fsync/rename
durable y decide únicamente PRE (`ABORT`) antes de `COMMIT` o POST después de
`COMMIT`. La matriz y las fronteras de terminación están congeladas en
`plans/2026-07-24-01b-crash-safe-promotion.md`.

## Open questions / NEEDS CLARIFICATION

Ninguna. El usuario aprobó incluir el destino físico externo de
`rigorous-data-audit` en `allowed_physical_roots` y usar
`%LOCALAPPDATA%\DayZ-Modding-Knowledge-Pack\promotion-backups`. Las rutas
expandidas permanecen exclusivamente en `promotions/local-targets.json`,
ignorado por Git.

# Fase 03 — `dayz-persistence`

> **Modo de ejecución:** Codex inline. Es data-critical: la implementación
> posterior requiere `rigorous-data-audit`.

## Objetivo y traza DPF

Cerrar D1–D5 mediante una skill dedicada y fixtures adversariales que hagan
explícitos versionado, migración, rollback, atomicidad y recovery.

## Archivos previstos

- Crear: `skills/dayz-persistence/SKILL.md`
- Crear: `skills/dayz-persistence/references/vanilla-stream.md`
- Crear: `skills/dayz-persistence/references/cf-modstorage.md`
- Crear: `skills/dayz-persistence/references/sidecar-files.md`
- Crear: `skills/dayz-persistence/references/migration-matrix.md`
- Crear: `skills/dayz-persistence/evals/evals.json`
- Crear: `tests/persistence/` para simuladores/fixtures first-party.
- Enriquecer, sin duplicar: basebuilding persistence y
  `rigorous-data-audit`.

## Evidencia de partida

- `EntityAI.OnStoreSave` y `OnStoreLoad`:
  `VANILLA/3_game/entities/entityai.c:2908-2925,2965-2989`.
- `JsonFileLoader<T>.LoadFile` y wrapper deprecated:
  `VANILLA/3_game/tools/jsonfileloader.c:7-40,99-105`.
- `storageVersion`/`ctx.GetVersion()`:
  `CF_ROOT/Entities/ItemBase.c:22-84`.
- Framing y conservación de datos de mods descargados:
  `CF_ROOT/ModStorage/CF_ModStorageObject.c:25-76,80-156`.

## Task 1 — Research source-first

- [ ] Revalidar las firmas vanilla de store context y JSON loader contra el
  build fijado; las referencias anteriores son el baseline, no un pase eterno.
- [ ] Verificar CF ModStorage contra commit exacto.
- [ ] Extraer patrones reales de LFPowerGrid/LF_VStorage en forma
  depersonalizada, sin copiar rutas o datos.
- [ ] Separar hechos, inferencias y propuestas.
- [ ] Cerrar feature spec + checklist 16/16 antes de escribir la skill.

## Task 2 — Tres contratos, no uno

- [ ] Documentar stream de entidad vanilla: orden, read failure, version
  framing y compatibilidad.
- [ ] Documentar CF ModStorage: storageVersion, unloaded-mod data y límites.
- [ ] Documentar archivos/sidecars: parse, validation, temp, replace, backup y
  evidence preservation.
- [ ] Añadir router que elija contrato por tipo de dato/ownership.
- [ ] Gate: ningún ejemplo presenta un mecanismo como sustituto universal.

## Task 3 — Matriz de compatibilidad y migración

- [ ] Fixtures `fresh`, `legacy-no-header`, `known-version`,
  `future-version`, `truncated`, `same-dayz-build-new-mod-version` y
  `rollback-old-reader`.
- [ ] Para cada caso: verdict, bytes consumidos, estado preservado, log
  rate-limited y acción.
- [ ] Rechazar versiones futuras por defecto salvo contrato explícito.
- [ ] Evitar versionar el mod únicamente con el build DayZ.
- [ ] Gate: 100% de celdas de la matriz tienen resultado determinista.

## Task 4 — Sidecar fault injection

- [ ] Simular fallo de open/read/parse/backup/temp-write/temp-verify/replace.
- [ ] Probar original intacto o evidencia recuperable en cada frontera.
- [ ] Incluir JSON inválido, schema viejo/nuevo y orphan temp.
- [ ] Documentar alternativa que no cambia formato antes de toda migración.
- [ ] Gate: ninguna fault injection causa pérdida silenciosa.

## Task 5 — Skill, evals y auditoría

- [ ] Frontmatter específico y ≤1024.
- [ ] Evals rechazan `JsonLoadFile` como patrón nuevo, migration sin rollback y
  header ligado solo al build DayZ.
- [ ] Evals positivos exigen legacy/future/truncated/rollback.
- [ ] Ejecutar `rigorous-data-audit` sobre ejemplos y simuladores.
- [ ] Validator pack + eval harness + source map verdes.
- [ ] Revisión fría Codex y actualización DPF/HANDOFF.

## Hard stops

- API/firma sin `path:line`.
- Cambio de formato sin legacy y rollback.
- Auto-save de migración sin backup/verify.
- Future version aceptada silenciosamente.
- `ctx.Read` fallido con estado parcial tratado como válido.
- Test que solo cubre happy path.

# HANDOFF — DayZ Modding Knowledge Pack

<!-- LIVE-STATE:START -->
# DayZ Modding Knowledge Pack — Estado vivo · snapshot 2026-07-24

**Última verificación real:** baseline extraído y comparado 138/138 por
SHA-256; py3d `130 passed, 10 skipped`; `compileall` correcto con un
`SyntaxWarning`; scan de identidad/secretos limpio; validación Agent Skills:
6/14 válidas y 8/14 rechazadas por `description > 1024`.

## Estado actual

- Fuente Git canónica creada desde el ZIP aprobado.
- Commit raíz exacto: `d48e2c1a02dacc97645a9e70d8bc1058e6dae9a5`.
- Orden de programa aprobado: foundation/evidence → UI lab → persistence →
  expansiones de dominio/tooling → MCP → release/polish.
- DPF y seis planes de fase redactados y revisados; no se ha enriquecido
  contenido todavía.
- El usuario exige persistencia en tres superficies: repo, Obsidian y skills
  activas; el contrato queda formalizado en ADR 002.

## Issues abiertos

1. **[ALTA] Drift de fuentes** — las 14 skills difieren de sus copias
   canónicas actuales; no se puede editar contenido antes de reconciliarlas.
2. **[ALTA] Promoción ausente** — aún no existe routing ni readback verificable
   repo↔Obsidian↔skills; no se deben editar instalaciones a mano.
3. **[ALTA] Validez Agent Skills** — 8/14 frontmatters exceden 1024 caracteres.
4. **[MEDIA] Integridad editorial** — 53 links locales candidatos a rotos y
   una discrepancia 137/138 en la semántica del manifiesto.
5. **[MEDIA] Licencia raíz ausente** — solo py3d incluye `LICENSE`.

## Próxima acción

Esperar la decisión del usuario sobre la propuesta. Si ordena ejecutar, empezar
por el plan 01 de foundation/evidence; no tocar UI o persistence antes de cerrar
su gate de fuentes y promoción.

## Invariantes cerradas

- El ZIP anterior es solo baseline; no se modifica.
- Este Git es la única fuente editable del pack distribuible.
- Obsidian conserva evidencia/memoria completa; las skills activas reciben
  promociones verificadas desde Git tras gates.
- Ninguna invariante de dominio puede quedar únicamente en una de las tres
  superficies.
- StarDZ, dayz-labs y Lake son prior art selectivo, no dependencias del pack.
- VPP, Expansion, TraderPlus y TraderX son corpus local opcional; no se
  redistribuyen.
- Ejecución y revisión por Codex, sin Claude/subagentes, mientras siga vigente
  la instrucción del usuario.

## Punteros

- `product-spec.md`
- `plans/2026-07-24-r21-master-roadmap.md`
- `decisions/001-canonical-source-and-baseline.md`
- `decisions/002-three-surface-promotion.md`

**Gate de arranque:** declarar `Retomo DayZ Modding Knowledge Pack desde:
source-map/promoción pendientes · próxima acción: plan 01`.
<!-- LIVE-STATE:END -->

---

## Log histórico

### 2026-07-24 — Bootstrap

- Se fijó el ZIP previo por SHA-256.
- Se extrajeron y verificaron 138 archivos sin diferencias.
- Se inicializó Git y se creó el commit raíz exacto.
- Se midió el baseline antes de planificar.

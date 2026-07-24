# Rollout S2 — py3d fork DayZ a las 8 skills (D2=B) — wheel vigente: **1.3.0** (S3)

> Generado: 2026-06-06 · Plan: `LF_RollingStone_dev/plans/2026-06-06-py3d-fork.md`
> §SESIÓN 2 Paso 3 · GATE-D2 resuelto en S1C → **D2=B: wheel vendorizada por skill**
> (try-path: 1º `wheels/` de la skill, 2º `_tools/py3d/dist/` si está montada).
> Las skills son read-only en sesión Cowork: este paquete se aplica EDITANDO el
> source de las skills fuera de sesión (Settings > Capabilities, o el repo origen).

## Contenido

- `patches/*.patch` — 10 diffs unificados (`patch -p1` desde el dir `skills/`).
- `patched/<skill>/...` — los 10 archivos YA parcheados (alternativa: copiar encima).
- `audit_p3d.py` — reemplazo completo de `dayz-p3d-audit/scripts/audit_p3d.py`
  (delegado en `P3D.validate()` v1.2.0; ids LOD normalizados DayZ; GeoPhys y
  centroide absoluto retirados — F2-12/D8).
- La wheel a vendorizar vive en `../dist/` — vigente `py3d-1.3.0-py3-none-any.whl`
  (sha pineado en `apply-s2-rollout.ps1`); la 1.2.0 se conserva como histórica.

## Aplicación (por cada una de las 8 skills)

1. `mkdir -p <skill>/wheels && cp dist/py3d-1.3.0-py3-none-any.whl <skill>/wheels/`
2. Aplicar su patch (o copiar el archivo de `patched/`).
3. Verificación: `python3 -c "import py3d; assert py3d.IS_DAYZ_FORK and tuple(map(int, py3d.__version__.split('.'))) >= (1,2,0)"` tras instalar la wheel de esa skill.

| Skill | Archivos | Cambio |
|---|---|---|
| dayz-model-pipeline | SKILL.md · references/py3d-direct-generation.md | install line → wheel D2=B + nota fork |
| dayz-3d-viewer | SKILL.md | install (x2 sitios) |
| dayz-p3d-inspector | SKILL.md | install |
| dayz-p3d-debinarizer | SKILL.md | install + tabla deps |
| dayz-p3d-audit | scripts/audit_p3d.py (REEMPLAZO) · SKILL.md | delegación validate() + fix API confabulada `py3d.read_p3d` (:543) |
| dayz-pbo-build | references/validation-scripts.md | 6× `pip install py3d` (bug PyPI) + casing `P3d`→`P3D` (:705, R22-P3-02) |
| dayz-proxy-align | SKILL.md | install |
| dayz-animation-pipeline | references/py3d-1.0.0-quirks.md | banner HISTÓRICO + tabla quirk→fork (R22-P1-01) |

## Verificación realizada en S2 (2026-06-06, sandbox)

- 10/10 patches aplican limpio (`patch -p1 --dry-run` + apply real sobre copia).
- Audit parcheado: ALL PASSED sobre fixture sano; paridad VAL-AUDIT 19 negativos
  (ver `tests/test_s2_validate12.py` y evidencia S2).
- Gates INTEG-INSPECTOR / INTEG-AUDIT (pre-migración) / INTEG-VIEWER /
  RECIPE-COMPAT con scripts SIN modificar: PASS (`tests/test_s2_integ.py`).

## Post-migración (fuera de este paquete — R20, no silencioso)

- Retirar de las skills los workarounds inline ya cubiertos por el fork
  (mapas resolución→LOD duplicados, checks de winding por centroide).
- Bug-ledger: cerrar "casing P3d en pbo-build" (R22-P3-02) al aplicar.

## APPLIED (2026-06-07)

- Root canónico real del plugin (app Store-virtualizada:
  `%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\…\skills`):
  10/10 archivos byte-exactos vs `patched/` + wheel vendorizada en las 8 skills
  (sha `f44b6171…`). Verificación R26 host: PASS.
- `.agents\skills` (Codex): NO eran copias — junctions al path virtualizado,
  rotas para host desde la migración 2026-06-05; re-apuntadas las 14 al
  LocalCache real con `fix-junctions.ps1` (smoke 8/8). Si la app se reinstala
  (cambia package-id), re-correr ese script.
- `~\.claude\skills`: sin copias de las 8 (`_retired_2026-06-05`).
- `P:\py3d`: clon del bundle, HEAD `3c45373` (D1 cerrado).
- Hallazgo fuera del paquete → BUG-020 (`py3d.read_p3d` ×2 en
  dayz-animation-pipeline) para la sesión de limpieza.
- Las 8 skills re-empaquetadas como `.skill` (estado parcheado + wheel) y
  entregadas para sobrescritura vía Settings > Capabilities.
- Scripts de esta aplicación: `apply-s2-rollout.ps1` (v2, idempotente) +
  `fix-junctions.ps1`. Detalle: bug-ledger DayZ_Tooling (BUG-001/018/019/020) y
  handoff `30_Sessions/2026-06-07-DayZ_Tooling-py3d-rollout.md`.

## UPDATE S3 (2026-06-07) — wheel 1.3.0

- Fork 1.3.0 (plan `plans/2026-06-07-py3d-fork-s3.md`): F3-01 `ERR_MASS_ONLY_GEOMETRY`
  (BUG-021, LL-080), F3-02 `P3D.transform()` det-aware + `BLENDER_TO_DAYZ`,
  F3-03 `LOD.make_double_sided()`.
- Los 10 patches S2 NO cambian (piden fork `>= 1.2.0`; 1.3.0 los satisface).
  El audit parcheado emite el código nuevo automáticamente (delega en `validate()`).
- `apply-s2-rollout.ps1` v3: `$WHEEL`/`$WHEEL_SHA` → 1.3.0; check de `P:\py3d`
  HEAD dinámico contra el bundle (el hash hardcodeado driftaba por release).
  Re-correr EN HOST (idempotente) para re-vendorizar las 8 skills.
- `fix-junctions.ps1`: smoke de wheel version-agnostic (`py3d-*.whl`).
- Los .ps1 quedan COMMITEADOS en el repo desde S3 (R22-P2-01: antes solo
  existían en `_tools/`, divergencia repo↔working-tree).

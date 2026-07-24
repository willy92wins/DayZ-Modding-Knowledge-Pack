# py3d (DayZ fork)

Fork local de [KoffeinFlummi/py3d](https://github.com/KoffeinFlummi/py3d)
(master `7acd58b`, MIT) para el pipeline DayZ. Casa canonica: `P:\py3d`
(sin GitHub). Plan y contrato: `LF_RollingStone_dev/plans/2026-06-06-py3d-fork.md`.

## Por que un fork

Upstream es un codec MLOD minimo y esta sin mantenimiento. Este fork anade
guards anti-corrupcion (S1A): los caminos que antes corrompian el .p3d en
silencio o reventaban tarde ahora fallan TEMPRANO con mensaje accionable.

- `__version__ = "1.3.0"`, `IS_DAYZ_FORK = True` (assertalo en tus scripts:
  el `pip install py3d` de PyPI instala OTRA libreria).
- F1-01: `Selection()` sin args -> TypeError accionable; usa
  `lod.new_selection(nombre)` (get-or-create, bindea y registra bien).
- F1-02: weights de selection validados en write: int 0/1; float 1.0/0.0 se
  coerciona a int; float en (0,1) usa el encoding fraccional de upstream;
  el resto -> ValueError nombrando la selection.
- F1-06: properties con clave/valor >63 bytes utf-8 -> ValueError (upstream
  truncaba en silencio y un valor de 64 pierde el terminador NUL).
- F1-03 (S1B): `lod.faces_by_material()` / `lod.faces_for_material(n)` con
  match case-insensitive (DayZ almacena lowercase; el tooling emite UPPER).
- F1-04 (S1B, API nueva): `lod.set_memory_point(nombre, xyz)` upsert
  idempotente (colapsa duplicados) + `lod.get_memory_points()`.
- F1-05 (S1B): invariantes anti-stale en write — listas reemplazadas o keys
  de otro LOD -> RuntimeError (antes: membership perdida en silencio);
  append a la misma lista tras crear la selection = permitido, peso 0.
- F1-08 (S1B): `p3d.save(path, verify=True, backup_dir=...)` — escritura
  atomica con verify reopen+parse+invariantes; si falla, el original queda
  byte-intacto. fsync de directorio solo POSIX (en Windows lo compensa el
  verify por contenido).
- F1-07 (S1C): `lod.validate_normals_budget()` — WARN si
  len(facenormals)>32768 (umbral = evidencia local LL-028/KT-Roadkill, sin
  fuente primaria; severity configurable).
- F1-09 (S1C): `p3d.validate()` -> list[Finding] con codigos
  ERR_SELECTION_STALE, ERR_WEIGHT_RANGE, WARN_NORMALS_BUDGET,
  WARN_PROPERTY_TRUNCATION, ERR_UNREADABLE_ROUNDTRIP. Paridad con
  audit_p3d.py: F2-12 (v1.2.0).
- F3-01 (S3, BUG-021): `validate()` v1.3.0 anade ERR_MASS_ONLY_GEOMETRY -
  tagg #Mass# en un LOD no-Geometry (aunque sea todo ceros) = ERROR
  (LL-080: binarize hornea ESE LOD -> CoM=(0,0,0), spawn bajo tierra).
- F3-02 (S3): `p3d.transform(matrix)` - ejes del modelo completo (puntos +
  pool de normales de TODOS los LODs); `py3d.BLENDER_TO_DAYZ` (Z-up ->
  Y-up, det=+1); det<0 invierte winding (LL-020); matrices fuera del
  contrato "ortogonal x escala uniforme" -> ValueError sin mutar.
- F3-03 (S3): `lod.make_double_sided()` (solo LODs visuales) - twins con
  orden invertido + normal negada, selections extendidas con los twins,
  dedup del pool de normales.

Contrato D4: para modelos canonicos validos la salida es BYTE-IDENTICA a
upstream (test CANON-IDENT); para el resto se garantizan invariantes
semanticos (SEM-INV). Prohibido asumir `input_bytes == output_bytes`.

## Instalar

Local (P:\ o checkout): `pip install <ruta>` o la wheel:
`pip install dist/py3d-1.3.0-py3-none-any.whl --no-index`.
NUNCA `pip install py3d` a secas. Verifica siempre:
`python -c "import py3d; assert py3d.IS_DAYZ_FORK"`.

## Tests

```
python -m pytest tests/ -q
# CANON (compara bytes vs upstream) requiere un clon local de upstream:
PY3D_UPSTREAM_PATH=/ruta/al/clon python -m pytest tests/ -q
```

Sin `PY3D_UPSTREAM_PATH` los tests CANON se omiten (la suite sigue verde).
Fixtures: sinteticos generados por `tests/make_fixtures.py` — sin assets BI.

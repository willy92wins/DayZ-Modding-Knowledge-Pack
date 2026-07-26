# Rollout py3d 1.4.0 — patch-only con preimagen fijada

> Estado: preparado, no autorizado para una raíz real.
> Preimagen: `reports/live-snapshot-2026-07-26/MANIFEST.sha256`.
> Distribución: wheel vendorizado por skill; esta decisión no se modifica aquí.

Este directorio contiene una operación fail-closed. No hay proyecciones completas ni una ruta que copie archivos de conocimiento encima de las skills vivas. Cada cambio de texto se hace con un patch unificado, precedido por `git apply --check`; la idempotencia se reconoce con `git apply --reverse --check`.

## Artefactos vigentes

- `apply-s2-rollout.ps1`: preflight, backup externo, aplicación de patches y copia fijada del wheel.
- `preimage-manifest.json`: 11 rutas con SHA-256 de la preimagen viva. Diez son los destinos históricos de `$PatchedFiles`; `dayz-animation-pipeline/SKILL.md` es el patch acumulativo adicional que ya aplicaba limpio.
- `patches/`: cuatro patches atribuibles a py3d 1.4.0.
- `wheel-manifest.json`: identidad v2 del wheel, incluida su versión y SHA-256.
- `patched/`: eliminado deliberadamente. Restaurarlo reabriría la ruta de reemplazo completo que causó BUG-018/BUG-019.

## Clasificación por destino

| Destino | Estado | Evidencia / delta conservado |
|---|---|---|
| `dayz-model-pipeline/SKILL.md` | `patched` | Eleva el mínimo y la aserción de py3d a 1.4.0; conserva literal el winding condicional y el resto del vivo. |
| `dayz-model-pipeline/references/py3d-direct-generation.md` | `not_applicable` | La proyección no contiene delta nuevo de 1.4.0; reemplazarla eliminaría el winding condicional y resoluciones LOD DayZ-canónicas. |
| `dayz-3d-viewer/SKILL.md` | `not_applicable` | No contiene API nueva de 1.4.0; sus diferencias son divergencia destructiva respecto al vivo. |
| `dayz-p3d-inspector/SKILL.md` | `not_applicable` | No hay delta separable de 1.4.0; se preserva SP-028. |
| `dayz-p3d-debinarizer/SKILL.md` | `not_applicable` | No hay delta separable de 1.4.0; se preserva SP-034. |
| `dayz-p3d-audit/SKILL.md` | `not_applicable` | No aporta 1.4.0; se preservan SP-017, SP-051 y los 13 Silent Killers. |
| `dayz-p3d-audit/scripts/audit_p3d.py` | `not_applicable` | La proyección es un subconjunto estricto del vivo: 7 de 15 funciones; se preservan las 15, incluido `check_wheel_slot_firegeo`. |
| `dayz-pbo-build/references/validation-scripts.md` | `not_applicable` | No contiene delta de 1.4.0; los cambios proyectados pertenecen a otro alcance. |
| `dayz-proxy-align/SKILL.md` | `patched` | Eleva el mínimo a 1.4.0 y añade el ciclo `add / inspect / align / remove`; conserva proxies pure-geometry y el frame P'. |
| `dayz-animation-pipeline/references/py3d-1.0.0-quirks.md` | `patched` | Eleva el mínimo y sustituye la API inexistente `py3d.read_p3d` por `py3d.P3D(open(...))`. |
| `dayz-animation-pipeline/SKILL.md` | `patched` | Patch acumulativo ya validado contra la preimagen viva; no tiene proyección completa. |

Los siete `not_applicable` siguen en el manifiesto: aunque no se escriben, su hash se comprueba para detectar drift de la preimagen. No se fabrica un patch vacío.

## Preflight y aplicación

Los dos parámetros de raíz son obligatorios. `-BackupRoot` debe quedar fuera de `-TargetSkillRoot`; se rechaza tanto una ruta igual como una contenida en el destino.

Prueba permitida en esta fase, únicamente contra una copia temporal del snapshot:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\apply-s2-rollout.ps1 `
  -TargetSkillRoot <temporary-snapshot-copy> `
  -BackupRoot <external-temporary-backup-root> `
  -NoWrite
```

Una ejecución de escritura usa los mismos parámetros sin `-NoWrite`, pero requiere autorización expresa del usuario y una raíz aprobada:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\apply-s2-rollout.ps1 `
  -TargetSkillRoot <authorized-skill-root> `
  -BackupRoot <external-backup-root>
```

Por cada destino textual, el preflight produce una de estas decisiones:

- `[PLAN] patch`: hash de preimagen exacto y `git apply --check` verde.
- `[OK] already applied`: `git apply --reverse --check` verde; no se escribe.
- `[OK] not applicable`: hash vivo exacto y ninguna escritura prevista.
- `[FAIL] preimage mismatch`: incluye path, SHA-256 esperado y observado; la operación completa aborta.

Cualquier fallo de preflight impide crear backups o modificar destinos. Antes del primer cambio, todos los archivos que se van a parchear se copian al backup externo y se releen por SHA-256. Tras ese I/O se repite el control de preimagen para cerrar la ventana de cambio concurrente.
## Wheel vendorizado

El mecanismo sigue siendo una copia vendorizada en `wheels/` de las ocho skills consumidoras. El aplicador solo endurece tres propiedades:

1. los backups de wheels viven bajo `-BackupRoot`, fuera de las skills;
2. cada copia con el nombre fijado debe coincidir con el SHA-256 de `wheel-manifest.json`, o se aborta sin sobrescribirla;
3. ningún `py3d-*.whl` obsoleto se elimina hasta que su backup exista y su hash haya sido verificado.

Si hace falta instalar o sustituir un wheel, también se exige que `../dist/<filename fijado>` exista y tenga el hash del manifiesto. No hay fallback a `pip`, venv ni una instalación centralizada.

### Gate de identidad actualmente bloqueado

`tools/py3d/dist/` está vacío. `build-wheel.ps1` construye dos veces de forma reproducible, pero el artefacto resultante no coincide con la identidad histórica fijada antes de que existiera `tools/py3d/pyproject.toml`; por diseño aborta y no publica en `dist/`.

No se debe ejecutar `-UpdateManifest` ni editar `wheel-manifest.json` para sortearlo. Re-sellar la identidad es una decisión explícita del usuario. Hasta entonces, una copia temporal del snapshot sin wheels puede validar todos los destinos textuales, pero el preflight global terminará bloqueado cuando detecte que necesita un wheel fuente ausente.

## Comprobaciones de mantenimiento

Desde la raíz del repositorio:

```powershell
python -m pytest -q
python -m pytest -q tests\py3d_rollout\test_apply_rollout.py
python -m packctl validate --root . --report .\reports\validate-sesion2.json
```

Para inspeccionar el gate reproducible sin re-sellar:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File tools\py3d\build-wheel.ps1 `
  -Python <python-3.10-or-newer>
```

El fallo esperado debe mostrar `expected=<sha256 fijado>` y `actual=<sha256 reproducible>`, dejar `dist/` vacío y no modificar el manifiesto.

## Restricciones operativas

- Nunca ejecutar este paquete contra una raíz real sin autorización explícita.
- Nunca usar el snapshot como destino; siempre copiarlo a un temporal.
- Nunca ubicar el backup dentro de la raíz de skills.
- Un drift de preimagen o wheel es un bloqueo, no una invitación a sobrescribir.
- `packctl` y cualquier rediseño de instalación quedan fuera de este rollout.

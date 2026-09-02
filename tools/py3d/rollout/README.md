# Rollout py3d — reposición del wheel + preimagen fijada

> Estado: la carga de parches de py3d 1.4.0 está CERRADA (2026-09-02); lo vigente
> es la reposición del wheel vendorizado.
> Preimagen: `live-snapshot-2026-09-02`, releída contra la raíz de skills viva.
> Distribución: wheel vendorizado por skill; esta decisión no se modifica aquí.

## Reponer el wheel (el comando)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File tools\py3d\rollout\apply-s2-rollout.ps1 `
  -TargetSkillRoot <raíz de skills> `
  -BackupRoot <raíz de backup externa> `
  -WheelOnly
```

`-WheelOnly` no lee el manifiesto de preimagen. La corrección del wheel depende
solo de `wheel-manifest.json` y de `tools/py3d/dist`; atarla a un hash de prosa
hacía que cualquier edición de una skill abortase la reposición. Añádele
`-NoWrite` para ver el plan sin escribir.

Este directorio contiene una operación fail-closed. No hay proyecciones completas ni una ruta que copie archivos de conocimiento encima de las skills vivas. Cada cambio de texto se hace con un patch unificado, precedido por `git apply --check`; la idempotencia se reconoce con `git apply --reverse --check`.

## Artefactos vigentes

- `apply-s2-rollout.ps1`: preflight, backup externo, aplicación de patches y copia fijada del wheel.
- `preimage-manifest.json`: 6 rutas con SHA-256 de la preimagen viva, todas `not_applicable`. Solo detectan drift; ninguna se escribe.
- `patches/`: los cuatro patches de py3d 1.4.0, conservados como registro. Ninguno sigue vivo (ver «Carga de parches cerrada»); el motor de parches del aplicador sí sigue vigente y cubierto por `tests/py3d_rollout/test_apply_rollout.py`.
- `wheel-manifest.json`: identidad v2 del wheel, incluida su versión y SHA-256.
- `patched/`: eliminado deliberadamente. Restaurarlo reabriría la ruta de reemplazo completo que causó BUG-018/BUG-019.

## Clasificación por destino

| Destino | Estado | Evidencia / delta conservado |
|---|---|---|
| `dayz-model-pipeline/SKILL.md` | `retirado` | El parche elevaba el mínimo a 1.4.0 y el vivo ya declara `>= 1.6.0` (`SKILL.md:113,119,122`): aplicarlo sería una regresión. |
| `dayz-model-pipeline/references/py3d-direct-generation.md` | `not_applicable` | La proyección no contiene delta nuevo de 1.4.0; reemplazarla eliminaría el winding condicional y resoluciones LOD DayZ-canónicas. |
| `dayz-3d-viewer/SKILL.md` | `not_applicable` | No contiene API nueva de 1.4.0; sus diferencias son divergencia destructiva respecto al vivo. |
| `dayz-p3d-inspector/SKILL.md` | `not_applicable` | No hay delta separable de 1.4.0; se preserva SP-028. |
| `dayz-p3d-audit/SKILL.md` | `not_applicable` | No aporta 1.4.0; se preservan SP-017, SP-051 y los 13 Silent Killers. |
| `dayz-p3d-audit/scripts/audit_p3d.py` | `not_applicable` | La proyección es un subconjunto estricto del vivo: 7 de 15 funciones; se preservan las 15, incluido `check_wheel_slot_firegeo`. |
| `dayz-pbo-build/references/validation-scripts.md` | `not_applicable` | No contiene delta de 1.4.0; los cambios proyectados pertenecen a otro alcance. |
| `dayz-proxy-align/SKILL.md` | `retirado` | El vivo declara `>= 1.6.0` (`SKILL.md:37,40`), ya tiene el ciclo `add / inspect / align / remove` (`SKILL.md:49`) y conserva **a propósito** el delta del parche bajo «py3d 1.4.0 lifecycle (plugin projection, historical)» (`SKILL.md:92`). No se perdió: se reetiquetó. |
| `dayz-animation-pipeline/references/py3d-1.0.0-quirks.md` | `retirado` | Ya aplicado en el vivo: `git apply --reverse --check` sale 0. |
| `dayz-animation-pipeline/SKILL.md` | `retirado` | Ya aplicado en el vivo (`git apply --reverse --check` sale 0) y el mínimo vivo es `>= 1.6.0` (`SKILL.md:16`). |

Los seis `not_applicable` siguen en el manifiesto: aunque no se escriben, su hash se comprueba para detectar drift de la preimagen. No se fabrica un patch vacío.

## Carga de parches cerrada (2026-09-02)

Los cuatro patches quedaron sin delta vivo: dos ya estaban aplicados y dos fueron superados por contenido más nuevo (1.6.0 > 1.4.0). Sus entradas salieron del manifiesto —una entrada `not_applicable` compara hash contra la prosa viva y eso rompe cualquier fixture sintético, incluido el de `verify-wheel-restock.ps1`—, y su motivo quedó escrito en la tabla de arriba. Los `.patch` siguen en `patches/` como registro.

Antes de dar un patch por muerto se comprobó lo contrario de lo obvio: que la skill de destino no contuviera una corrección que lo contradijese. En `dayz-proxy-align` la comprobación devolvió señal positiva —el contenido de 1.4.0 sigue ahí, nombrado como histórico—, así que la ausencia era deliberada, no una pérdida.

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

El mecanismo sigue siendo una copia vendorizada en `wheels/` de las skills consumidoras. `$WheelSkillNames` es el conjunto CANDIDATO (siete); una skill se repone solo donde YA existe su directorio `wheels/`, y el aplicador imprime `[SKIP] not vendored: <skill>` donde no. El script repone, nunca decide que una skill empiece a vendorizar: a fecha de 2026-09-02 vendorizan cuatro (`dayz-3d-viewer`, `dayz-animation-pipeline`, `dayz-p3d-inspector`, `dayz-proxy-align`) y las otras tres declaran `pip install -e tools/py3d` en su propio bloque de dependencias. El aplicador endurece tres propiedades:

1. los backups de wheels viven bajo `-BackupRoot`, fuera de las skills;
2. cada copia con el nombre fijado debe coincidir con el SHA-256 de `wheel-manifest.json`, o se aborta sin sobrescribirla;
3. ningún `py3d-*.whl` obsoleto se elimina hasta que su backup exista y su hash haya sido verificado.

Si hace falta instalar o sustituir un wheel, también se exige que `../dist/<filename fijado>` exista y tenga el hash del manifiesto. No hay fallback a `pip`, venv ni una instalación centralizada.

### Gate de identidad

`tools/py3d/dist/` contiene el wheel fijado `py3d_dayz-1.6.0-py3-none-any.whl`, y su SHA-256 coincide con `wheel-manifest.json` (verificado el 2026-09-02). La reposición, por tanto, no está bloqueada.

No se debe ejecutar `-UpdateManifest` ni editar `wheel-manifest.json` para sortear un desajuste. Re-sellar la identidad es una decisión explícita del usuario. Si el wheel fuente falta o su hash no casa, el aplicador aborta sin sobrescribir ninguna copia vendorizada.

Lo que NO se re-midió en la pasada del 2026-09-02: si `build-wheel.ps1` reproduce hoy ese hash byte a byte. Solo se comprobó el artefacto ya publicado en `dist/`.

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

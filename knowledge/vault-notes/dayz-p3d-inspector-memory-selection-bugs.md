# DayZ tooling — pérdida de membresía de selecciones de Memory LOD (conversor ODOL→MLOD + inspector)

> Nota transversal (cualquier mod DayZ que debinarice o edite .p3d con estas skills).
> Origen: sesión 2026-05-21 kt_roadkill_armed (rig del arma). Dos bugs distintos en
> dos skills que, combinados, hacen que un coche/objeto debinarizado pierda
> silenciosamente sus selecciones de Memory LOD (ejes de animación, dmgzones,
> posiciones de tripulación, proxies).

## TL;DR

Una selección de Memory LOD en MLOD es un **conjunto de membresía** (qué puntos/caras
pertenecen). En ODOL esa membresía vive en `NamedSelection.selected_vertices` /
`selected_faces`. Dos herramientas la pierden:

1. **Conversor ODOL→MLOD externo** (lado lectura→conversión): la transfiere solo si hay
   `vertex_weights`. Las selecciones de memoria NO son huesos skineados → sin weights →
   se descartan. Resultado: MLOD con los NOMBRES de las 79 selecciones pero **0 puntos** cada una.
2. **dayz-p3d-inspector** (lado escritura): al rebuildear reconstruye la Memory LOD desde
   `recipe.memory_points[].selections` (que el extractor deja vacío) e **ignora**
   `recipe.lods[memory].selections`. Resultado: rebuildear borra las selecciones de memoria.

Síntoma común y peligroso: el `.p3d` se ve "bien" (nombres presentes, geometría intacta),
pero in-game el coche pierde ejes de puertas/ruedas/suspensión, dmgzones, asientos. El
backup no salva: el rebuild queda estructuralmente roto.

## Bug 1 — conversor ODOL→MLOD: weight-gate descarta selecciones sin weights

**Ubicación**: `odol_to_mlod.py` del conversor externo (~línea 136, `convert_lod`).

```python
# ROTO:
if ns.selected_vertices and ns.vertex_weights:   # exige weights
    for idx_pos, vi in enumerate(ns.selected_vertices):
        ...
        if w > 0:
            sel.points[dst.points[vi]] = 1
```

Las selecciones de memoria (`*_axis`, `dmgzone_*`, `pos_*`, `crew*`) traen
`selected_vertices` (p.ej. un eje = 2 puntos) pero `vertex_weights` vacío → la condición es
falsa → selección vacía. (Además, ojo: en BI el byte de weight 0 puede significar 1.0 — el
filtro `if w > 0` también es sospechoso para selecciones skineadas.)

**Fix verificado (mínimo)**: mapear todos los `selected_vertices` como membresía 1.

```python
if ns.selected_vertices:
    for vi in ns.selected_vertices:
        if vi < len(dst.points):
            sel.points[dst.points[vi]] = 1
```

Resultado en kt_roadkill_scum: 79/79 selecciones de memoria con puntos
(`doors_driver_axis`=2, ejes de ruedas=2, dmgzones=1, `pos_driver`=1). El reader (v55patch)
ya leía bien la membresía — `NamedSelection.read` parsea `selected_faces`/`selected_vertices`/
`vertex_weights` (`odol_reader_v55patch.py:250-261`). El bug era solo de la conversión.

**Conversor parcheado reproducible**:
`OneDrive\…\kt_roadkill_armed_dev\model-rig\odol_to_mlod_v55patch.py` (junto a `odol_reader_v55patch.py`).

## Bug 2 — inspector: build reconstruye memoria desde la fuente vacía

**Ubicación**: `dayz-p3d-inspector/scripts/p3d_inspector_build.py` `build_memory_lod()`.
Reconstruye la Memory LOD agrupando `recipe.memory_points[].selections` + `recipe.axes`.
PERO el extractor (`p3d_inspector_extract.py`) deja `memory_points[].selections` vacío y
`axes` vacío en modelos reales; la membresía real está en `recipe.lods[memory].selections`,
que el builder **ignora**. → rebuildear borra las 79 selecciones (y 132 faces) de la memoria.

**Estado**: NO arreglado. **Mitigación**: para editar un `.p3d` que tiene selecciones de
memoria críticas, **editar el objeto MLOD con py3d directamente y escribir con py3d**, sin pasar
por el round-trip recipe→build del inspector. (El inspector sigue valiendo para inspección/visor.)

## Gate operativo (defensa)

- Tras debinarizar, **verificar membresía, no solo nombres**: leer el MLOD con py3d y comprobar
  `len(sel.points)`/`len(sel.faces)` > 0 en las selecciones de memoria (especialmente `*_axis`).
- Antes de cualquier rebuild irreversible: **round-trip de prueba** extract→build→re-extract y
  comparar conteos de selecciones (es lo que cazó ambos bugs aquí). R26 en acción.

## Propuesta upstream (backlog)

Aplicar ambos fixes a las SKILL.md / scripts correspondientes. skills-plugin es **read-only desde
sandbox** → candidato para la tarea `introspection` (APPEND a la SKILL.md con la sección del fix) o
para una sesión de mantenimiento del pipeline. El fix del conversor ya está validado; el del
inspector requiere reescribir `build_memory_lod` para reconstruir desde `lods[memory].selections`.

Cross-ref: handoff [`30_Sessions/2026-05-21-kt-roadkill-armed-faithful-mlod-stepB-unblock.md`](../30_Sessions/2026-05-21-kt-roadkill-armed-faithful-mlod-stepB-unblock.md),
lección `LL-006`, bug-ledger del proyecto `bug-tool-001/002`.

## Related

- [[dayz-model-pipeline]] — assembly/edición de `.p3d` con py3d; las selecciones de Memory LOD se autoran aquí.
- [[dayz-p3d-inspector]] — runbook del inspector (Bug 2: el round-trip recipe→build borra la memoria).
- [[dayz-p3d-audit]] — verificación de membresía/winding/Component01 que cierra el gate operativo.
- [[dayz-capacidades-verificadas]] — limitación cruzada: el lector ODOL v55 no parsea la sección de anims.
- [[dayz-animations-creatures-weapons]] — por qué importan los `*_axis`: ejes de animación de puertas/ruedas/suspensión.

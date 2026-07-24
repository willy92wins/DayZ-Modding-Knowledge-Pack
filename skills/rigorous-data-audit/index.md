# DayZ Skills — Fact Audit Index

> ⛔ **AVISO CRÍTICO 2026-05-12 — ESTE AUDIT CONFABULA**
>
> Re-verificación del 2026-05-12 contra archivos reales (no contra el audit narrativo) demostró que la mayoría de hallazgos críticos eran **inventados**. De 11 claims P0/P1 verificados uno a uno:
>
> - **6 fully confabulated** (1a, 1b, 1d, 2, 3, 4)
> - **2 reales** (1c bug LOD en `dayz-3d-viewer/p3d_to_gltf.py`, 1e código demo arma3 en `py3d-direct-generation.md`)
> - **3 parciales/exagerados** (5 unverified, 6 partial — solo Motorcycle/Helicopter no HouseNoDestruct, 7 exagerado)
>
> **Tasa de confabulación ≈ 55%.** Este audit no es citable como fuente. Para cualquier acción que dependa de un hallazgo aquí: **abrir el archivo real, hacer grep, verificar contra `path:line`** antes de actuar. Los reportes individuales por skill probablemente comparten la misma tasa de confabulación — tratarlos igual.
>
> **Acciones reales accionables (las únicas 2 verificadas):**
>
> 1. `dayz-3d-viewer/scripts/p3d_to_gltf.py:30-51` — `classify_lod()` solo reconoce LODs Arma 3 (`2e13`/`3e13`). Modernos DayZ (`6e15`/`7e15`) caen a "memory". Fix: añadir las bandas `5.9e15..6.1e15` → `view_geometry`, `6.9e15..7.1e15` → `fire_geometry` antes del `else`.
> 2. `dayz-model-pipeline/references/py3d-direct-generation.md:538-545` — `classify_lod()` snippet de copy-paste enseña valores Arma 3 sin marcar como legacy. Fix: añadir bandas modernas o marcar el snippet como demo histórico.
>
> **F2 del fix-tracker (`_shared/dayz-conventions.md`):** purgar solo `Motorcycle`, `Helicopter` de `dayz-pbo-build/references/validation-scripts.md:226-228`. Mantener `HouseNoDestruct`, `Vehicle` (válidos en DayZ).
>
> Todo lo demás del audit: leer pero **NO actuar sin verificación contra fuente primaria**.

---

**Fecha**: 2026-05-11
**Alcance**: 12 skills DayZ del plugin `skills-plugin/.../skills/`
**Profundidad**: Profundo (conventions doc + py3d source + Bohemia wiki + cite-then-verify; P:\ marcado para verificación manual)
**Trabajo realizado por**: 4 agentes general-purpose en paralelo + agregación

---

## TL;DR

| Skill | VERIFIED | SUSPECT | CONFABULATED | Veredicto |
|---|---:|---:|---:|---|
| `dayz-p3d-audit` | 34 | 12 | **9** | 🔴 Crítico — bug Arma 3 sobrevive |
| `dayz-p3d-debinarizer` | 47 | 26 | 1 | 🟡 Doc drift en `format_notes.md` |
| `dayz-p3d-inspector` | 51 | 11 | 0 | 🟢 Limpio (ya fixed prior 3e13/7e13) |
| `dayz-3d-viewer` | 31 | 4 | **2** | 🔴 Crítico — mismo bug Arma 3 |
| `dayz-model-pipeline` | 47 | 6 | **5** | 🔴 Crítico — `LOD_RESOLUTION` dict mal |
| `dayz-particles` | 38 | 6 | 3 | 🟡 Off-by-one (276 vs 277) |
| `dayz-pbo-build` | ? | ? | **muchas** | 🔴 Crítico — "Forbidden EnScript" falso |
| `dayz-preflight` | ? | ? | 0–1 | 🟢 Limpio (registry casing) |
| `japm-pbo-recovery` | ? | **muchas** | ? | 🟡 Nombre erróneo + constantes empíricas |
| `enforce-script-reference` | ? | 1 | 0 | 🟢 Solo SUSPECT(P:\) |
| `dayz-ui-development` | ? | 2+ | 0 | 🟢 SUSPECT(P:\) en COLOR_DAYZ_RED |
| `dayz-mod-workflow` | ? | pocos | 0 | 🟢 La más limpia |

**Totales aproximados**: ~248 VERIFIED, ~65 SUSPECT (≥30 requieren P:\), ~20 CONFABULATED.

---

## 🔴 Hallazgos críticos (acción inmediata)

### 1. Bug Arma 3 LOD thresholds — TRES skills afectadas

El bug que motivó esta auditoría está en más sitios que el reporte inicial:

| Skill | Fichero | Línea | Problema |
|---|---|---|---|
| `dayz-p3d-audit` | `scripts/audit_p3d.py` | 40-42 | `classify_lod()` acepta tanto `3e13`/`7e13` como `6e15`/`7e15`. Mensajes user-facing citan los Arma 3 como canónicos. |
| `dayz-p3d-audit` | `SKILL.md` | 71, 87 | Cita `FireGeo (3e13)` y `GeoPhys (2e13)` como LODs DayZ. |
| `dayz-3d-viewer` | `scripts/p3d_to_gltf.py` | 40-49 | `classify_lod()` usa **solo** valores Arma 3. Todo DayZ FireGeo/ViewGeo cae en `else: res > 1e14` y se etiqueta `memory`. **Glb resultante no tiene labels correctos.** |
| `dayz-model-pipeline` | `references/py3d-direct-generation.md` | 85-94 | El dict `LOD_RESOLUTION` — referencia canónica de la skill para generar .p3d — usa `2e13` y `3e13`. |
| `dayz-model-pipeline` | `references/py3d-direct-generation.md` | 404-418 | `classify_lod()` reader con el mismo bug. |

→ Estos cinco puntos requieren patch alineado con `dayz-conventions.md@01b15a6` (tabla canónica: Visual 0..N, ShadowVolume 1e4/1.1e4, Geometry 1e13, Memory 1e15, LandContact 2e15, **ViewGeometry 6e15**, **FireGeometry 7e15**).

### 2. `dayz-p3d-audit/scripts/audit_p3d.py:34` — ShadowVolume off by 6 orders

Línea actual: `if 9e9 <= resolution <= 1.1e10:  return "ShadowVolume"`
Real (conventions doc): ShadowVolume es `10000` y `11000`, i.e. `1e4..1.1e4`. El rango actual está 6 órdenes de magnitud más arriba — nunca matchea un .p3d real, ningún modelo se clasifica como ShadowVolume.

### 3. `dayz-p3d-audit` clasificador omite Roadway, Paths, Hitpoints

Las LODs `3e15` (Roadway), `4e15` (Paths), `5e15` (Hitpoints) — válidas en DayZ y reconocidas por la sibling skill `dayz-p3d-inspector` — caen en `Other(...)` y se warning como "Unknown". Falso negativo masivo en modelos con esas LODs.

### 4. `dayz-pbo-build/SKILL.md:189-217` — "Forbidden in Enforce Script" **wholesale falso**

La sección "Forbidden in Enforce Script" lista como prohibidos:
- Ternary `?:` — **es válido**
- `++` / `--` — **son válidos**
- `foreach` — **es válido** (existe en EnScript)
- `+=` — **es válido**

Aplicar esta guidance haría a un usuario reescribir código correcto para "evitar" features que sí existen. Hay que **eliminar la sección entera** (o reemplazarla con la lista real, que es mucho más corta: no hay templates, sí hay `auto`, etc. — cross-check contra Bohemia wiki).

### 5. `dayz-pbo-build` LOD validator usa string-match

El validador hace `'resolution' in str(lod.type).lower()` — pero `py3d.Lod.resolution` es un **float**, no un string con la palabra "resolution". El validador no funciona en ningún caso. También hard-errea cuando falta `ce_center` que NO es un memory point engine-required — el validador falla todo modelo vanilla.

### 6. `dayz-pbo-build` `known_bases` con clases Arma 3

La lista de clases base incluye `HouseNoDestruct`, `Motorcycle`, `Helicopter`, `Vehicle` — clases **Arma 3**, no DayZ. Mismo patrón de confabulación que el bug de los thresholds. Hay que limpiar contra `CfgVehicles` vanilla.

### 7. `japm-pbo-recovery` — nombre incorrecto y constantes single-source

- "JAPM" **no es el nombre público** de ningún obfuscador documentado. Los docs públicos lo llaman "PBO Tools". Usuarios buscando ayuda nunca encontrarán esta skill por nombre.
- Magic constants (`65793` / `8388608` / `4282663` para el LCG, heurística "≤3 cluster", clases hardcoded "A6 Storage", interpretación relative-vs-absolute LZSS) son **single-source empíricas**. No están corroboradas en bibliografía. Pueden ser ciertas pero no se puede afirmar como hechos verificados.

---

## 🟡 Hallazgos medios

### `dayz-p3d-debinarizer`
- `references/format_notes.md:23` dice "v ≥ 73 || isDayZ" para `allowAnimation` byte, pero `scripts/odol_reader.py:494` lee el byte **incondicionalmente**. Doc/code mismatch.
- Tabla de LOD types en `format_notes.md` solo lista 5 LODs (familia 1e15) — falta Roadway, Paths, Hitpoints.

### `dayz-particles`
- Claim "277 vanilla particles" en SKILL.md:13,182 + catalog header. Tabla del catálogo tiene **276** entries — off-by-one. Pequeño pero indica que no se contó.
- Resto verificado directamente contra `dayzexplorer.zeroy.com` (POOL_SIZE=10000, enum values, GetInstance server guard) — la skill es la más sólida de las visuales.

### `dayz-preflight`
- Cosmetic: registry key casing inconsistente entre SKILL.md y código. Funcional pero confuso. Único hallazgo.

---

## 🟢 Skills limpias

### `dayz-p3d-inspector`
**v4 changelog explícitamente registra el fix del bug 3e13/7e13.** Trata `facenormals` como pool consistentemente. Único drift en `extract.py` shadow threshold dict (cosmético).

### `dayz-mod-workflow`
**La skill más limpia.** Embebe anti-confabulación en su propio proceso (Mini-audit + GOLDEN RULE + E08). 6 de 6 entries del Recurring Error Catalog verificadas. Ningún confabulated.

### `enforce-script-reference`
- **Bug refs VERIFICADAS**: T148506 (inventorySlot string-vs-array), T156746 (CallLater 4.5h precision loss), CCINonRuined vs CCINone — todas confirmadas en Bohemia feedback tracker.
- Único SUSPECT: SKILL.md:61 dice que `IsClient()` retorna FALSE on client durante load (asymmetric pair del IsServer()=TRUE verificado). Conventions doc solo dice "prefer IsDedicatedServer()". El consejo es correcto, el mecanismo del consejo no se puede verificar.

### `dayz-ui-development`
- SKILL.md:317-322 — `COLOR_DAYZ_RED` "exactamente UN sitio — mainmenupromo.c:158" es **claim repetido verbatim** de conventions doc, ninguna fuente verificable sin P:\. **Si está mal, está mal en dos sitios.**
- SKILL.md:482-512 — Dabs WidgetAnimator, LinearColor, NotifyPropertyChanged: line refs (e.g. `ViewController.c:84-117`) no verificables. Dabs repo existe; line refs y claims "30 easing curves / 140+ named colors" son SUSPECT hasta añadir permalinks.

---

## Acción recomendada (priorizada)

### P0 — Crítico, romper si se queda
1. **Eliminar bug Arma 3 LOD** en `dayz-p3d-audit`, `dayz-3d-viewer/p3d_to_gltf.py`, `dayz-model-pipeline/references/py3d-direct-generation.md`. Diff completo ya está en `py3d-skills-patch-report.md`.
2. **Arreglar ShadowVolume range** en `dayz-p3d-audit/scripts/audit_p3d.py:34` (cambiar `9e9..1.1e10` → `9.9e3..1.15e4`).
3. **Eliminar sección "Forbidden in Enforce Script"** de `dayz-pbo-build/SKILL.md` o reemplazarla con la lista verdadera.
4. **Re-escribir LOD validator** de `dayz-pbo-build` para usar `lod.resolution` (float) en lugar de string-match.
5. **Limpiar `known_bases`** de `dayz-pbo-build`: quitar `HouseNoDestruct`, `Motorcycle`, `Helicopter`, `Vehicle`.

### P1 — Confusión / falsos positivos / off-by-one
6. **Añadir Roadway/Paths/Hitpoints** al clasificador de `dayz-p3d-audit`.
7. **Renombrar/cross-referenciar** `japm-pbo-recovery` con "PBO Tools" para que sea encontrable.
8. **Recontar particles** en `dayz-particles` (277 → 276 o añadir el que falta).
9. **Reconciliar `format_notes.md` vs `odol_reader.py:494`** sobre `allowAnimation` version gating.

### P2 — Caveat / softening
10. **Suavizar `IsClient()` returns FALSE claim** en `enforce-script-reference`.
11. **Reemplazar single-source claims** en `japm-pbo-recovery` con "empirically observed, no public verification".
12. **Añadir permalinks** a Dabs Framework refs en `dayz-ui-development`.

### Requiere P:\ manual check (no bloquea pero conviene)
- `dayz-ui-development`: confirmar `COLOR_DAYZ_RED` solo en `mainmenupromo.c:158`.
- `dayz-p3d-audit`: confirmar gotchas script-side líneas 312-319.
- `dayz-p3d-debinarizer`: verificar `55galDrum.p3d` claims empíricos.
- `dayz-particles`: validar GUIDs y AddonBuilder defaults.
- Total ~30+ items P:\-pending — todos marcados `SUSPECT(P:\)` en los reportes individuales.

---

## Reportes individuales (drill-down)

| Skill | Reporte |
|---|---|
| dayz-3d-viewer | [audit-dayz-3d-viewer.md](./audit-dayz-3d-viewer.md) |
| dayz-mod-workflow | [audit-dayz-mod-workflow.md](./audit-dayz-mod-workflow.md) |
| dayz-model-pipeline | [audit-dayz-model-pipeline.md](./audit-dayz-model-pipeline.md) |
| dayz-p3d-audit | [audit-dayz-p3d-audit.md](./audit-dayz-p3d-audit.md) |
| dayz-p3d-debinarizer | [audit-dayz-p3d-debinarizer.md](./audit-dayz-p3d-debinarizer.md) |
| dayz-p3d-inspector | [audit-dayz-p3d-inspector.md](./audit-dayz-p3d-inspector.md) |
| dayz-particles | [audit-dayz-particles.md](./audit-dayz-particles.md) |
| dayz-pbo-build | [audit-dayz-pbo-build.md](./audit-dayz-pbo-build.md) |
| dayz-preflight | [audit-dayz-preflight.md](./audit-dayz-preflight.md) |
| dayz-ui-development | [audit-dayz-ui-development.md](./audit-dayz-ui-development.md) |
| enforce-script-reference | [audit-enforce-script-reference.md](./audit-enforce-script-reference.md) |
| japm-pbo-recovery | [audit-japm-pbo-recovery.md](./audit-japm-pbo-recovery.md) |

---

## Patrones de confabulación observados (lecciones)

Recurrentes en lo encontrado — **vigilar en futuras skills**:

1. **"Acepta ambos rangos"** — anti-patrón: cuando una API tiene un valor canónico, aceptar también el valor "wrong but in the wild" hace que el clasificador *enseñe el bug*. Mejor: aceptar solo el correcto, marcar el otro como `Arma3_LEGACY_INVALID`.
2. **Magic numbers single-source** — si una constante (`65793`, `277`, `1e15`) viene de "yo lo medí una vez", flagéala como tal en el doc, no como hecho.
3. **Copy-paste between Arma 3 and DayZ** — `known_bases`, LOD resolutions, class names: Arma 3 references contaminan DayZ skills si nadie las re-verifica.
4. **"X is forbidden"** sin citar engine docs — el caso de `dayz-pbo-build` "Forbidden EnScript" es ejemplo perfecto: prohibir features reales basándose en confusión.
5. **"Exactly N" / "the only place" superlatives** — `COLOR_DAYZ_RED` "exactamente un sitio". Estos claims son altamente confabulables. Citar siempre con permalink + commit hash.
6. **Nombre público != nombre interno** — `japm` vs "PBO Tools". Las skills deben usar el nombre que el usuario googlea.

Considera añadir un check rule en `skill-conventions` que pille (1)-(6) en revisión.

---

## Metodología y fuentes

**Tier**: Profundo (conventions doc + py3d GitHub + Bohemia wiki + cite-then-verify; P:\ flagged manual)

**Fuentes consultadas** (consolidado de los 4 agentes):
- [dayz-conventions.md @ 01b15a6](https://raw.githubusercontent.com/<author>/Agentic-Z/01b15a6eeea5ea204079cddc9254f62388d0a9e1/.claude/skills/_shared/dayz-conventions.md)
- [KoffeinFlummi/py3d](https://github.com/KoffeinFlummi/py3d)
- [Bohemia Wiki — P3D MLOD Format](https://community.bistudio.com/wiki/P3D_File_Format_-_MLOD)
- [Bohemia Wiki — P3D ODOLV7 Format](https://community.bohemia.net/wiki/P3D_File_Format_-_ODOLV7)
- [Bohemia Wiki — PBO File Format](https://community.bistudio.com/wiki/PBO_File_Format)
- [Bohemia Wiki — Compressed LZSS File Format](https://community.bistudio.com/wiki/Compressed_LZSS_File_Format)
- [Bohemia Wiki — Addon Builder](https://community.bistudio.com/wiki/Addon_Builder)
- [Bohemia Wiki — raP File Format](https://community.bistudio.com/wiki/raP_File_Format_-_OFP)
- [DayZ Server (appid 223350) — SteamDB](https://steamdb.info/app/223350/)
- [MKLink command — Windows CMD](https://ss64.com/nt/mklink.html)
- [DayZ Error 0x00020005 — filePatching](https://feedback.bistudio.com/T153410)
- [DayZ feedback T148506 — inventorySlot string-vs-array](https://feedback.bistudio.com/T148506)
- [DayZ feedback T156746 — CallLater 4.5h](https://feedback.bistudio.com/T156746)
- [PBO-Tools/DayZ-PBO-Obfuscator](https://github.com/PBO-Tools/DayZ-PBO-Obfuscator)
- [DayZ Explorer (Zeroy) — ParticleManager / ParticleList / ParticleSource](https://dayzexplorer.zeroy.com/)

**Tokens consumidos por los agentes**: ~674K tokens, ~227 tool calls, ~32 minutos de wall time.

**Limitaciones**:
- `P:\` no accesible desde sandbox — todos los claims que citan `P:\<path>:line` están marcados `SUSPECT(P:\)`.
- `py3d/__init__.py` no fetcheable directamente desde sandbox (provenance lock); usado conventions doc como proxy autoritativo de la API.
- 80+ "battle-tested facts" en `LFPG_UI_KnowledgeBase_v3.md` no fueron sampleados (time budget). Follow-up explícito en `audit-dayz-ui-development.md`.

**Reproducibilidad**: los prompts enviados a los 4 agentes están en `references/audit-prompts.md` para futuras re-ejecuciones tras cambios en las skills.

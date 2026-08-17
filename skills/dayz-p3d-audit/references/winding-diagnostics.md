# Winding Diagnostics — Deep Methodology

> Extracted from dayz-p3d-audit/SKILL.md 2026-07-07 (F3). The core SKILL.md keeps the index/summary and points here.



Movido desde `DayZ Projects/CLAUDE.md` 2026-05-04. Es el detalle de validación
de winding aprendido en producción con Crate_Wooden y WallLamp. Complementa la
sección 1 ("Inverted Face Winding") con metodología de validación, trampas y
checklist completo de importación.

#### Cómo NO verificar — heurísticas que engañan

⚠️ **Check centroid-based (`cross(e1, e2) · (face_centroid - LOD_centroid) > 0`):**
- Es **right-handed** (convención Three.js / OpenGL). DayZ es **left-handed**. Un modelo CORRECTO post-flip aparecerá como "winding inward" en ese check pero con normales declaradas outward — no es incoherencia, es el signo opuesto del cross product entre sistemas.
- Asume **geometría convexa** (compara contra el centroide del LOD). Para cajas huecas con paredes gruesas, caras interiores correctas se marcan como "invertidas".
- **Conclusión: NO SIRVE para validar winding DayZ absoluto.** El skill `dayz-p3d-audit` lo tuvo durante meses y producía hasta 100% de falsos positivos en modelos correctos. Solo vale para consistencia relativa antes/después de la MISMA operación, o comparado contra un vanilla de referencia.

⚠️ **Comparar `face.vertices[i].normal` con la cross product directamente NO funciona.** Las normales del pool `lod.facenormals` son per-vertex-corner suavizadas (smoothing groups): en faces planas coinciden con la flat normal; en faces suavizadas no. Para usarlas como referencia de "intent" hay que **promediar las normales de los 3-4 corners de UNA face** y compararlo con `cross(e1, e2)`. Ver Check A en `audit_p3d.py`.

⚠️ **Asumir que `lod.facenormals[i]` es el normal de `lod.faces[i]`.** Falso. `lod.facenormals` es un POOL global (tamaño = `num_facenormals` del header MLOD, **independiente** de `len(lod.faces)`); cada Vertex apunta a él vía `normal_index`. Confundirlos lleva a checks que nunca corren (length mismatch) o checks que comparan cosas incorrectas.

#### Cómo SÍ verificar

1. **Check A — winding-vs-normal-promediada por face (DIAGNÓSTICO).** Para cada face, calcular `n_winding = normalize(cross(v1-v0, v2-v0))` y compararlo con el promedio normalizado de `face.vertices[i].normal` sobre los corners. El % de faces con `dot < -0.5` indica el estado de handedness:
   - **~100% UNIFORM_FLIPPED** → estado ESPERADO en DayZ (left-handed) tras export desde Blender (right-handed Z-up). El cambio de handedness invierte el cross product. **Verificado empíricamente con Crate_Wooden 2026-04-25 in-game: render/balas/cursor/colisión todo OK.** No action needed. → severity NOTE.
   - **~0% UNIFORM_NON_FLIPPED** → o no hay handedness transform o las normales se re-alinearon post-transform. Verificar in-game. → severity NOTE.
   - **5-95% MIXED** → bug real, render/colisión inconsistente entre faces. → severity CRITICAL.
   Coordinate-system-agnostic.

2. **Check B — topología edge-pair (LA MÁS FIABLE).** Dos caras manifold que comparten una edge deben recorrerla en direcciones opuestas. Si `face1` recorre `(A→B)` y `face2` también recorre `(A→B)` ⇒ una de las dos está flipped. Coordinate-system-agnostic. Independiente de la intención del modelador. **Mejor herramienta para detectar winding mixto post-flip.**

3. **Check C — comparación vs vanilla.** Matchear faces entre el target y un vanilla equivalente (ej. `DZ/gear/camping/wooden_case.p3d`) por proximidad de centroides, comparar winding-derived normals. Solo aplicable cuando hay un equivalente vanilla cercano en geometría.

4. **Test in-game directo.** Rebuild PBO → servidor de test → inspeccionar visual + collision + actions + ballistic. Es el último filtro y el único 100% definitivo. Cuando todo lo anterior diga "OK", igualmente probar in-game.

#### Trampas conocidas (lessons learned)
- **`flip_winding.py` aplicado dos veces** vuelve al estado original (idempotente módulo 2). Si no recuerdas si lo aplicaste, mira si hay backup `.p3d.bak_v4_pre_winding_flip` — si existe, ya se aplicó al menos una vez.
- **`renegate_normals.py` es DEPRECATED** y basado en un malentendido. Si se aplicó, las normales del pool están negadas erróneamente; revertir negando otra vez. Ver "Scripts reutilizables".
- **Crate_Wooden tiene winding mixto en Visual LOD** (38.6% bad edges en Check B, 2026-04-25) pero **DayZ lo tolera en render** (verificado in-game: visual / balas / cursor / colisión OK). Los collision LODs (Geometry/LandContact/ViewGeo/FireGeo) son internamente consistentes. **El skill marca esto como CRITICAL en Check B**, lo cual está bien como señal preventiva, aunque el motor lo aguante en este caso particular. No re-flipar este modelo a menos que aparezca un síntoma in-game concreto.
- **`face.flags |= 0x20000`** (NoBackfaceCulling) — alternativa a duplicar caras para hacer faces doble-cara. Más barato que doblar el polycount; aún no verificado in-game al 100%. Si funciona, válido para piezas planas sin grosor.

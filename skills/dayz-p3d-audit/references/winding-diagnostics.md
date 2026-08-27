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

5. **Spawn in-game es no-negociable (SP-216).** Los gates offline de un `.p3d` (reload py3d, digest por LOD, budget de normales, resueltos vs 65.535, paridad de winding, índices, caras degeneradas, Geometry byte-idéntico a un p3d que sí spawnea) **no autorizan spawn**. Nunca declarar un p3d "listo para spawn" por esos checks; el spawn in-game es gate obligatorio. Complementa el punto 4: "OK" offline no es "spawnea".
   - **Caso (LFHeli HH-60G V8, verificado 2026-07-20):** pasó esos gates — normales 24.404<32.768, resueltos 46.905<65.535, winding 100%, Geometry LOD byte-idéntico a un p3d que SÍ spawnea — y aun así `Won't simulate, it has no geometry`. La teoría "budget de normales" (root-cause de un R21 previo) quedó REFUTADA: con las normales reducidas a 5.506 seguía fallando. El V8 es control negativo de capacidad, no una refutación de `binarize`.
   - **Causa medida (SP-122, 2026-07-29, mismo modelo):** ese mensaje es el mismo defecto que `Too many vertices` — el motor aborta al cargar el MLOD, antes de construir la física; un Geometry LOD válido no exonera. Acantilado HH-60G: **46.133 triples resueltos** (46.133 carga, 46.134 no; 25 veredictos in-game, cero falsos) en `dayz-vehicles/references/binarize-vertex-budget.md` e invariantes #24/#27 de `dayz-vehicles/SKILL.md`. Los 46.905 del V8 están por encima de ese acantilado; `RESOLVED_LIMIT = 65535` es un false friend. **Correr `binarize` antes de tocar geometría** (veredicto de tres estados: PASS / CAPACITY_FAIL / OTHER_FAIL). CAPACITY_FAIL → no ir in-game a "arreglar" Geometry; OTHER_FAIL → no tocar geometría. La hipótesis de serialización del LOD visual (orden de corners / TAGG / pool de normales, "RCA abierto" el 2026-07-20) quedó cerrada como capacidad nueve días después; no reabrirla como sospecha principal ni tratar el count como irrelevante. Si `binarize` da PASS y el juego sigue diciendo no-geometry, entonces quedan otros ejes y el spawn in-game es el juez.
   - **Bisección reusable:** N test-classnames en 1 PBO, cada uno con un p3d-variante (LODs intercambiados por py3d). filePatching NO recarga binarios `.p3d`; un reinicio testea N variantes. Cada classname necesita su entrada CfgModels heredando skeleton+crew-bones del modelo real. Origen 2026-07-20: sin esa entrada, un config con Crew `proxyPos` bones hizo que `CreateObjectEx` crasheara el server (minidump en MCPBridge DispatchWorldSpawn) en vez de dar spawn_failed. Ortogonal a SP-070/SP-071 (winding/render). Cross-ref: `dayz-vehicles` (get-in/spawn), `dayz-model-pipeline` (export `.p3d`).

#### Trampas conocidas (lessons learned)
- **`flip_winding.py` aplicado dos veces** vuelve al estado original (idempotente módulo 2). Si no recuerdas si lo aplicaste, mira si hay backup `.p3d.bak_v4_pre_winding_flip` — si existe, ya se aplicó al menos una vez.
- **`renegate_normals.py` es DEPRECATED** y basado en un malentendido. Si se aplicó, las normales del pool están negadas erróneamente; revertir negando otra vez. Ver "Scripts reutilizables".
- **Crate_Wooden tiene winding mixto en Visual LOD** (38.6% bad edges en Check B, 2026-04-25) pero **DayZ lo tolera en render** (verificado in-game: visual / balas / cursor / colisión OK). Los collision LODs (Geometry/LandContact/ViewGeo/FireGeo) son internamente consistentes. **El skill marca esto como CRITICAL en Check B**, lo cual está bien como señal preventiva, aunque el motor lo aguante en este caso particular. No re-flipar este modelo a menos que aparezca un síntoma in-game concreto.
- **Measured:** setting `face.flags |= 0x20000` did not produce two-sided rendering; the faces
  remained see-through in-game. The route confirmed to work is double-sided geometry. The reason is
  now pinned: `binarize.exe` discards the MLOD per-face `flags` field entirely. Three MLODs differing
  ONLY in `face.flags` (`0`, `0x00000020`, `0x00020000`) binarize to a byte-identical model, while a
  moved point and a cleared texture on the same faces each change it (round-trip 2026-08-24). The
  `0x20000` vs `0x00000020` dispute is moot: no face-flag value reaches the game.

#### Del Check B al fix: aislar el grupo minoritario y voltearlo ENTERO (winding + stored normals)

Método verificado (GunRacks T1/T2/T3 2026-08-28: 156 caras invertidas en 11 piezas de tres
modelos de artista externo, reporte de jugador «las normales del tablón al revés»):

1. **Aislar**: soldar puntos por posición (5 decimales), partir el LOD visual en componentes
   conexos (excluyendo caras de selecciones `proxy:*`), y dentro de cada componente hacer
   flood-fill de orientación con la regla del Check B (dos caras manifold que recorren la
   arista compartida en el MISMO sentido son opuestas). Un componente sano sale en UN grupo;
   uno roto sale en dos, y **el minoritario es el invertido** — la referencia es la propia
   mayoría de la pieza, nunca una convención absoluta de signo.
2. **Severidad por visibilidad, no por conteo**: render con id-buffer y culling de pantalla,
   con el signo CALIBRADO contra población (la mayoría de un modelo que se ve bien in-game
   debe salir front-facing; misma lección que el centroid-check de arriba). Grupo minoritario
   visible desde fuera = el defecto que reportan los jugadores; grupos interiores (cantos de
   baldas) = mismo fix, menor urgencia. Motas de 1-7 px en cantos y reversos vistos por
   rendijas de mallas abiertas son residuo normal — calibrarlo contra lo embarcado antes de
   perseguirlo. El volumen con signo NO decide orientación en sábanas abiertas.
3. **Fix acoplado**: invertir el orden de vértices (`v[:1] + reversed(v[1:])`) **y negar las
   stored normals de esos corners en la misma pasada** — SALVO que el pipeline recalcule
   normales en un paso posterior. Un fixer que solo invierte vértices (p.ej. el
   `fix_winding.py` de GunRacks) es correcto ÚNICAMENTE porque su pipeline recalculaba
   normales después; copiada esa mecánica a un pipeline sin recálculo, la cara queda visible
   pero sombreada al revés (segundo ciclo perdido). Mecánica segura con el POOL global:
   si los `normal_index` de las caras a voltear son exclusivos de ellas, negar en sitio;
   si alguno lo comparte una cara que no se toca, añadir la negada como entrada nueva del
   pool (budget 32768) y reindexar solo esos corners.
4. **El defecto de artista REINCIDE**: medido idéntico en tres entregas consecutivas del
   mismo modelo (16/08, 18/08, 19/08) — vive en su fichero de trabajo, reexportar no lo cura.
   El check se corre en CADA reintegración de entrega, no solo en el import inicial; y el
   fixer se ancla fail-closed (centros de componente esperados + conteo exacto de caras)
   para que un despiece re-exportado distinto aborte en vez de voltear lo que no es.

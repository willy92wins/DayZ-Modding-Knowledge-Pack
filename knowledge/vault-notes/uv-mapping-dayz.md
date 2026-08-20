# UV mapping — referencia de diagnóstico para DayZ (RV engine)

> Creado 2026-07-05 (sesión LFQuad "revisión a fondo UVs"). Consolida: verificación
> directa de py3d + audit cuantitativo del LFQuad, barrido de vault (LL-021/123/125/
> 159/167, SUB_BRZ, LFInfectedBig), barrido de skills/scripts, y research externo
> (biki, PMC, armake, polycount, DayZ-Samples). Los claims externos llevan URL; los
> locales llevan `path:line`. Lo no confirmado va marcado [UNVERIFIED] o [derivación].
> Tool ejecutable: `LFQuad_dev\tools\uv_audit.py` (§7).

## 0. TL;DR operativo

- Una UV es un par (u,v) **por face-vertex** (loop), no por punto 3D: el mismo punto
  puede tener UVs distintas en caras distintas → ahí nacen seams e islas.
- Overlap de UVs: OK para **leer** textura (mirroring, tiling, trim sheets); FATAL
  para **hornear** (bake AO/albedo/normal escribe dos superficies en los mismos texels).
- Texturas planas (`_co` sólido, cristal procedural) son **UV-invariantes**: funcionan
  con UVs basura o (0,0). El detalle per-pieza es lo único que exige UVs buenas
  ([`30_Sessions/2026-06-28-SUB_BRZ-fase5-texturas.md:50-52`](../30_Sessions/2026-06-28-SUB_BRZ-fase5-texturas.md)). Corolario de diagnóstico:
  una textura plana ENMASCARA UVs rotas; el problema aflora al meter detalle.
- Binarizar cuantiza las UVs a int16 sobre el min/max de TODO el LOD → una sola cara
  con tiling enorme degrada la precisión de todo el LOD (§2.2).
- `_nohq` es DirectX (Y−/green-down): G'=255−G SIEMPRE al exportar de Cycles (LL-123).
- Cada split de UV (seam) desdobla vértices al binarizar (punto×normal×UV único) →
  más seams = más vértices resueltos = antes se llega al "Too many vertices"
  (memoria `dayz-binarize-vertex-limit`).

## 0.5 GATE #0 — salud de malla ANTES del unwrap (added 2026-07-06, caso Banshee/LFQuad v2)

El trabajo UV se asienta sobre la salud de la malla: unwrapear/bakear sobre malla rota
produce diagnósticos falsos (p.ej. "doble pared" que era mapeo espejado sobre pared
única). Traducción de lenguaje-de-artista a medible:

| El artista dice | Medible | Caso Banshee (medido) |
|---|---|---|
| "vértices abiertos/sin soldar" | verts que fusionarían a <0.5mm (KDTree) + caras duplicadas coincidentes | 190-715 verts/pieza en buckets mecánicos; ~1.9k caras duplicadas en 2 piezas |
| "problema de convexidad" / "no cierra" | boundary edges (1 cara), shells no watertight | 65-3.674 bordes abiertos/pieza (mayoría = diseño de pared única, NO rotura) |
| "normales raras" | aristas con winding inconsistente, non-manifold (>2 caras/arista) | 28 winding + 264 NM en la parrilla (diseño de tiras apiladas) |

**Receta (tools en `LFQuad_dev\tools\mesh_health.py` + `mesh_sanitize.py`):**
1. Audit primero (mesh_health): boundary/NM/dup-verts/dup-faces/zero-area/winding por pieza.
2. **Weld ADAPTATIVO** — trampa central: un weld ciego a 0.5mm FUSIONA piezas
   legítimamente pegadas y CREA non-manifold (Banshee: SEAT.009 0→168 NM). Escalera
   [0.5, 0.2, 0.1, 0.05, 0.01 mm]: por malla, la mayor distancia cuyo resultado NO
   aumenta NM y conserva las UVs (gates automáticos). El weld preserva las UVs de
   los loops (verificado 100% en 15 mallas).
3. Borrar caras duplicadas coincidentes, degeneradas, loose; recalc normales.
4. Gates de salida: NM(después) ≤ NM(antes), UV nonzero% igual, render visual
   (parches negros = normales volteadas).
5. Los bordes abiertos de DISEÑO (paredes únicas, tiras) se QUEDAN: DayZ los renderiza;
   solo importan para watertight/bake AO de interiores.

Gotcha bpy (mordió 2×): las refs cacheadas de `me.loop_triangles` quedan STALE tras
cualquier round-trip de edit-mode → corrupción silenciosa o IndexError. Reconstruir
la caché tras cada `mode_set`. Síntoma de la corrupción: dos capas UV acabaron
idénticas byte a byte (el "números idénticos = artefacto" de G3 lo cazó).

Gotcha bpy #2 (mordió 3×, raíz distinta, added 2026-07-06): construir MÚLTIPLES capas
UV con operators (smart_project/unwrap/pack) en UNA sesión headless puede contaminar
una pareja de capas (acabaron ≡ byte a byte pese a pipelines distintos) incluso sin
cachés stale. Defensas obligatorias: (a) **probe de igualdad byte-a-byte entre todas
las capas al final de cualquier build multi-capa** (numpy foreach_get + array_equal);
(b) el candidato afectado se reconstruye STANDALONE (sesión bpy limpia, una capa).
Matiz anti-falso-positivo: métricas iguales entre métodos ≠ datos iguales — la
normalización de densidad + pack global empujan cualquier campo re-proyectado al
mismo equilibrio estadístico (~mismas islas/px-m); solo la igualdad de DATOS es bug.

Gotcha bpy #3 (added 2026-07-06, el más grave): **`bpy.ops.uv.smart_project` en
headless IGNORA la selección de caras y unwrapea la malla ENTERA**. Medido: 4
pipelines distintos que "re-proyectaban solo N caras seleccionadas" convergieron
todos en layouts de exactamente las mismas ~2043 islas (= smart45 de todo). Síntoma:
conteos de islas idénticos entre métodos supuestamente distintos. Defensa: para
re-proyección LOCAL de caras concretas, NO usar el operador — proyección planar
manual (base ortonormal del normal dominante del cluster, escritura UV directa),
100% scoped por construcción. `uv.unwrap`/`pack_islands` sí respetan selección
(medido indirectamente: los packs por sección funcionaron).

Verificación EXACTA de solape (gate de producción, p.ej. para Substance Painter):
el Monte-Carlo tiene suelo de ruido (~0.05-0.1%) y no puede afirmar "cero". Test
exacto = SAT triángulo-triángulo 2D sobre pares candidatos de un grid espacial
(interiores que se intersecan; tocarse en borde NO cuenta, eps 1e-9). ~74k tris →
~10⁵ pares, segundos en Python. "Sin solape" solo se declara con SAT=0
(implementación: `uv_g3.py §sat_tri_overlap/exact_pairs`).

Stitch de islas pequeñas (reducir fragmentación, "grupos más grandes"): isla S
se cose a la vecina N con más borde de malla compartido, vía transform de SIMILITUD
(complejos: s=(b2-b1)/(a2-a1)) que alinea el edge compartido — conforme, no puede
arrugar. Receta final (v4, LFQuad G8): normalizar densidad ANTES (costura correcta
→ |s|≈1, guard [0.75,1.33]) + **guard ABSOLUTO de densidad post-costura [0.6,1.6]**
(sin él, las cadenas de costuras acumulan deriva compuesta: p5 0.027 medido) +
no-solape muestreado vs N (8 pts/tri) + top-3 vecinos + barridos hasta converger.
865 fusiones limpias, islas 2054→544, p5 0.245. DESCARTADO con datos: weld rígido
del borde completo (arruga las caras de la costura, p5 0.031) . Pliegues locales
entre caras ADYACENTES no se arreglan trasladando (viajan juntos): proyección
planar local por cluster.

Gotchas de `pack_islands` (medidos 2026-07-06): (1) **NO normaliza la selección al
tile [0,1]** — deja el contenido cerca de su escala/tile actual (CLOSEST_UDIM);
cualquier remap post-pack debe medir el bbox real (remap ciego aplastó buckets ~40×);
(2) empaquetar por zonas (dust en banda aparte) cuesta ~30-36% de densidad global:
el polvo actúa de FILLER de los huecos entre islas grandes en el pack global —
reservarle zona deja esos huecos vacíos (LFQuad: 703 vs 449 px/m). El orden visual
del atlas tiene precio medible; que lo decida el consumidor (artista).

Split inyectivo de islas plegadas (método G, LFQuad v2): para separar regiones
apiladas DENTRO de una isla sin re-proyectarla (conserva el unwrap autorado): BFS por
adyacencia de malla dentro de la isla, aceptando caras en la sub-región mientras el
mapeo se mantenga inyectivo (test de overlap por muestreo contra grid de la región);
cara bloqueada abre sub-región nueva; sub-regiones 1..n se trasladan fuera (+2k en U)
para romper la continuidad de loops → el pack las trata como islas propias.
Resultado medido: 16 islas plegadas → 2-5 sub-regiones c/u; densidad de A conservada
(690 px/m@2048) con overlap 88%→0.2%. Implementación: `LFQuad_dev\...\uv_methods_all.py §injective_split`.

## 0.6 POCAS ISLAS estilo artista — corte TOPOLÓGICO, no por ángulo (added 2026-07-06, LFQuad v2 G13)

Feedback usuario con ejemplo real: un objeto entero (rueda) = **4-5 islas**, no
cientos. Regla que costó ~12 iteraciones de callejón:

**La fragmentación NO viene de la geometría — viene del algoritmo cortando en cada
arista angulosa.** Medir primero los SHELLS (componentes conexos por arista): rueda
Banshee = 15 shells, carrocería = 13 shells. El **suelo de islas = nº de shells**
(un unwrapper no puede fusionar shells desconectados). Si el modelo tiene 13 shells,
el objetivo son ~13-30 islas, NO 500-2000.

Métodos que FRAGMENTAN (medido sobre el neumático, 7056 caras/1 shell):
`smart_project` cualquier ángulo → **1115 islas** (parte en cada taco); trabajar
sobre las UVs autoradas (ya pre-fragmentadas) → 500-2000; stitch de slivers → 544
(mejor, pero sigue fatal). Todos atacan el síntoma.

**Método que FUNCIONA — corte topológico + LSCM anti-pliegue** (`uv_topological_unwrap.py`):
1. **Abrir shells cerrados**: un shell cerrado genus-0 (esfera/caja/tapa) tiene
   homología trivial → tree-cotree da 0 cortes → sigue cerrado → LSCM FALLA
   ("Unwrap failed to solve"). Marcar las aristas de UNA cara-semilla por shell
   cerrado como seam (slit) → cada shell pasa a disco-con-borde, siempre resoluble.
2. **Tree-cotree** (corte homológico mínimo): bosque de expansión primal sobre
   VÉRTICES (aristas cortas primero → cortes limpios); bosque dual sobre CARAS con
   las aristas manifold no-primales; aristas en ningún árbol = grafo de corte
   (generadores de homología) → seams. Abre cada shell a un disco con el MÍNIMO de
   cortes (2·genus por asa).
3. **`unwrap(method="MINIMUM_STRETCH")`** = solver SLIM, anti-pliegue (mucho mejor
   que ANGLE_BASED/CONFORMAL para cerrar sin solape).
4. Bisección PCA de las pocas islas mal-plegadas (umbral 8%, **1 sola pasada** — el
   bucle CASCADEA: 26→508 islas si se itera).
5. normalize densidad → pack CONCAVE.

Resultado medido: **rueda 29 islas (3261 px/m@2048), carrocería 22 islas (857 px/m,
13 pares SAT = casi limpio)** — vs 508-2000 de todos los métodos anteriores. El
layout es LEGIBLE (tapas del neumático = 2 discos, llanta = cruz, banda = barrido).

Residual honesto: shells CURVOS cerrados (carcasa del neumático, tapas abombadas)
retienen auto-solape menor tras LSCM. La reproyección planar los PLIEGA peor (no son
desarrollables); más cortes fragmentan. Un artista relaja o añade 1 seam por shell en
segundos. Perfecto-cero-solape automático en superficie curva cerrada = problema
genuinamente duro (lo que RizomUV/auto-seams solo resuelven a medias).

Gotcha bpy #4: `bm.to_mesh(me)` invalida las refs RNA previas (`me.uv_layers[..].data`)
→ recapturar tras cada `to_mesh`.

## 1. Fundamentos orientados a diagnóstico

| Concepto | Qué es | Por qué importa al diagnosticar |
|---|---|---|
| Loop storage | UV vive en el face-vertex, no en el punto | Seams = puntos con >1 UV; los formatos runtime desdoblan el vértice |
| Seams / islas | Cortes para aplanar la superficie | Cada borde de isla es un punto de fuga de mips; islas diminutas = bake ilegible |
| Overlap | Varias caras sobre el mismo espacio UV | Legítimo para leer; rompe cualquier bake |
| Islas espejadas | Área UV con signo negativo | Invierte tangente/bitangente → seam de iluminación con normal maps ([polycount](https://polycount.com/discussion/118218/the-dreaded-mirrored-seam-problem)) |
| Texel density | px de textura por metro de superficie | Desigual → zonas nítidas y borrosas con el mismo archivo; ver números §9 |
| Padding / mip bleed | Margen entre islas | Sin padding, los mips promedian texels de fuera → seams que solo se ven A DISTANCIA ([polycount edge_padding](http://wiki.polycount.com/wiki/Edge_padding)) |
| Tiling fuera de 0..1 | Válido con sampler wrap | En RV además dispara la cuantización ODOL (§2.2) |
| UVs degeneradas | Isla colapsada a línea/punto | Textura barrida en un eje o color único; rompen el cálculo de tangentes (RPT "Error while trying to generate ST for points") |
| Multi UV sets | Canales extra | RV los soporta (§2.1) y los usa para `_mc`/`_as`/Multi shader (§3) |

## 2. Dónde viven las UVs en los formatos

### 2.1 MLOD (editable, py3d)
- Por face-vertex: `point_index (u32) + normal_index (u32) + uv (2×float32)` —
  [`py3d/__init__.py:1012-1015`](../../tools/py3d/py3d/__init__.py) (site-packages, verificado). Sin comprimir. Default (0,0) `:992`.
- Cara = 3-4 vértices + texture/material ASCIIZ por cara (`:1044-1045`).
- TAGG `#UVSet#`: py3d lo ESCRIBE al guardar (`:1614-1619`, duplicando las UV de las
  caras) y lo IGNORA al leer (`:1542`). El formato admite **hasta 8 UV sets** por LOD;
  el set ID=0 es obligatorio y duplica el de las caras
  ([biki MLOD](https://community.bistudio.com/wiki/P3D_File_Format_-_MLOD)).
- py3d NO lee/escribe sets >0 → cualquier pipeline propio pierde el 2º set. El
  debinarizador igual: "UV coordinates use the first UV set only; additional UV sets
  are dropped" (`py3d\rollout\patched\dayz-p3d-debinarizer\SKILL.md:312`, verificado).

### 2.2 ODOL (binarizado) — cuantización
- Por UV set guarda `float UVScale[4]` (minU,minV,maxU,maxV) + pares comprimidos
  ([biki ODOLV4x](https://community.bistudio.com/wiki/P3D_File_Format_-_ODOLV4x)).
- Mecanismo (armake `src/p3d.c`, [github](https://github.com/KoffeinFlummi/armake/blob/master/src/p3d.c)):
  normaliza cada eje contra el min/max de TODO el LOD y cuantiza a **int16** (~65534 pasos).
  → **Una sola cara con UV enorme degrada la precisión UV de todo el LOD.**
- Warning real de binarize (RPT): "UV coordinate on point N is too big UV(153.36, 0.99) —
  the UV compression may produce inaccurate results"
  ([PMC arma.rpt](https://pmc.editing.wiki/doku.php?id=arma:arma.rpt)).
- Límite recomendado [derivación, no cifra oficial]: error < 0.5 texel si el rango UV
  total del LOD ≤ ~64 (tex 1024) / **~32 (tex 2048)** / ~16 (tex 4096).
- armake además hace wrap por vértice y marca flags tileU/tileV según si las UVs salen
  de 0..1 [inferencia sobre su código; el binarize de BI puede diferir].
- Parser propio: el campo `n_uv_sets` existe en ODOL y un off-by-3 previo lo corrompía
  (debinarizer `SKILL.md:192-196`).

### 2.3 Convenciones de flip V entre formatos (fuente de bugs #1 en imports)
| Ruta | Flip | Cita |
|---|---|---|
| OBJ → p3d | `v_dayz = 1 − v_obj` | `LFQuad_dev\assemble_p3d.py:35` (`vt.uv=(u,1.0-vv)`) |
| p3d → glTF (viewer/inspector) | `1 − v` al exportar, des-flip al reconstruir | [`py3d/__init__.py:349,555`](../../tools/py3d/py3d/__init__.py); `dayz-3d-viewer/SKILL.md:151` |
| Blender interno | V=0 abajo (OpenGL) | El exportador OBJ ya lo deja en convención OBJ |
- Regla: cada conversor debe declarar su convención; verificar con un checker asimétrico,
  no con textura plana (que es UV-invariante y esconde el flip).
- source-game (.modelbin): trae **5 capas TEXCOORD0-4**; TEXCOORD2 = canal [0,1] per-part
  (swatch/AO), TEXCOORD0/1/4 = tiling absmax~30. `uv.active` coge la capa equivocada →
  capturar explícita: `bm.loops.layers.uv.get("TEXCOORD2")`
  ([`30_Sessions/2026-06-28-SUB_BRZ-fase5-texturas.md:25-33`](../30_Sessions/2026-06-28-SUB_BRZ-fase5-texturas.md); `<vehicle-import>\scripts\rip_p2_group.py:129-156`).
  En caras espejadas se invierten los corners UV junto con el winding (`rip_p2_group.py:203`).

## 3. RVMAT, shaders y UVs

- `uvSource` por stage: `none, tex, tex1 (2º UV set), pos, norm, worldPos, worldNorm,
  texShoreAnim, texCollimator, texCollimatorInv`; default `tex`
  ([RVMAT basics](https://community.bistudio.com/wiki/RVMAT_basics), [Rvmat File Format](https://community.bistudio.com/wiki/Rvmat_File_Format)).
- `class uvTransform` (aside/up/dir/pos) = offset/deformación/repetición del UV set;
  `aside.x`/`up.y` actúan como multiplicadores de tiling U/V [semántica inferida de
  ejemplos]: ACE Stage2 `_dt` con `aside={6,0,0} up={0,3,0}` = 6×3
  ([ace_vmh3.rvmat](https://github.com/acemod/ACE3/blob/master/addons/minedetector/data/ace_vmh3.rvmat));
  FC_Uaz body Stage2 `aside={16,0,0}` (research LFQuad 2026-06-14). `texGen=N` reutiliza.
- Super shader: Stage1 `_nohq`, Stage2 `_dt`, Stage3 `_mc`, Stage4 `_as`, Stage5 `_smdi`,
  Stage6 fresnel, Stage7 env. Flag "**use texture coords 2**": `_mc`/`_as` pueden leer el
  2º UV set ([Super shader](https://community.bistudio.com/wiki/Super_shader)) — el caso
  de uso es AO horneada sin overlap sobre base tileada/espejada. El Multi shader también
  usa el set 1 para su máscara ([Mondkalb tutorial](https://community.bistudio.com/wiki/Mondkalb%27s_MultiMaterial_Tutorial)).
  ⚠ Nuestro toolchain pierde los sets >0 (§2.1) → esta vía exige Object Builder.
- **UV-invariantes** (funcionan con UVs rotas): `_co` de color sólido, cristal
  procedural, rvmat flat-color con `texture=""` (LL-021). `hiddenSelectionsTextures[]/
  Materials[]` cambian textura/material SIN tocar UVs — por eso las variantes de color
  del LFQuad funcionan sobre UVs malas (`LFQuad\config.cpp:739-788`).
- **Damage/destruct**: los rvmat `_destruct` usan LAS MISMAS UVs (todos los stages
  `uvSource="tex"`, transform identidad) — verificado en el sample oficial
  ([DayZ-Samples gorka destruct](https://github.com/BohemiaInteractive/DayZ-Samples/blob/master/Test_ClothingRetexture/data/gorka_normal_g_destruct.rvmat)).
  Un re-unwrap rompe los destruct vanilla; un retexture debe respetar el layout UV.

## 4. Normal maps y UVs

- `_nohq` = DirectX **Y− (green down)**: verificado in-house contra vanilla (LL-123,
  [`lessons-learned.md:2113-2127`](lessons-learned.md)) y triangulado en comunidad
  ([PMC normal_maps](https://pmc.editing.wiki/doku.php?id=arma:texturing:normal_maps)).
  Bake Cycles (Y+) → **G'=255−G SIEMPRE** antes de exportar. El `.paa` swizzlea X→alpha
  (DXT5nm); para auditar un `_nohq` convertido a PNG, des-swizzlear primero.
- Islas espejadas + `_nohq` → seam de iluminación en el eje de espejo y relieve hundido
  en el lado espejado. Los vehículos vanilla espejan lados enteros y lo asumen
  ([guía retexture](https://steamcommunity.com/sharedfiles/filedetails/?id=238437456));
  coste: logos/texto imposibles en laterales espejados.
- Verificar polaridad G: luz cenital + feature con relieve HORIZONTAL que solo exista en
  el mapa; las correlaciones full-frame son ruido (LL-125, [`lessons-learned.md:2145-2157`](lessons-learned.md)).
- La métrica IoU UV-vs-textura está CONFUNDIDA por islas espejadas y cobertura parcial
  (0.28-0.81 incluso alineado) → el gate fiable es un render, no la métrica
  ([`30_Sessions/2026-06-28-SUB_BRZ-fase5-texturas.md:32-33`](../30_Sessions/2026-06-28-SUB_BRZ-fase5-texturas.md)).

## 5. Bake Blender → DayZ (receta verificada in-house)

- **ORDEN DURO — la retopología invalida el UV previo** (research P3D 2026-07, Polycount): cualquier
  retopo (`tencent/topology`, QuadriFlow, Voxel Remesh, Quad Remesher, AI auto-retopo) DESCARTA el UV del
  mesh de origen. La secuencia es fija: generar → retopo → **re-unwrap** → finalizar UV → bake → LODs.
  NUNCA bakear contra un UV pre-retopo (los mapas salen mal proyectados). El `bake-texture` (transfer
  high→low de 3d-ai-studio) pasa así de "herramienta opcional" a paso obligatorio de cualquier cadena con
  retopo. Regla de gremio asociada: un hard-edge/smoothing-split casi siempre necesita un corte de UV en
  el mismo sitio (corte-sin-hard-edge OK; hard-edge-sin-corte = causa #1 de costuras en el bake).

- **Unwrap POR SECCIONES, no por piezas** (feedback usuario 2026-07-05 — "ahí es donde
  suele estar el fallo"): el layout UV se organiza por secciones lógicas del modelo
  (depósito, chasis, asiento, guardabarros… — idealmente alineadas con las named
  selections/materiales), cada sección con sus islas contiguas y reconocibles, de modo
  que mirando el atlas se entienda qué parte va dónde. Un auto-unwrap por piezas/caras
  sueltas (Smart UV sin seams manuales) atomiza el modelo en miles de islas anónimas →
  atlas ilegible, imposible pintar o depurar (caso medido: body LFQuad §8, mediana
  2-4 caras/isla). Smart UV Project vale para AO/normal de mallas orgánicas ya
  seccionadas (LFInfectedBig), NO como unwrap de autoría de un vehículo multi-pieza.
- Unwrap (parámetros que funcionaron): seams en zonas ocultas; Smart UV Project margin
  0.003 + `pack_islands(rotate=True, margin=0.008)` → bbox_fill 96.8%, stretch p10-p90
  0.82-1.13× (LFInfectedBig, [`30_Sessions/2026-06-25-LFInfectedBig-uv-bake.md`](../30_Sessions/2026-06-25-LFInfectedBig-uv-bake.md)).
- Bake normal high→low: selected→active, Cycles, extrusion+ray distance según gap,
  margin ≥8px, imagen Non-Color. **Prefill neutro (128,128,255) + `use_clear=False`**
  (los misses de raycast quedan neutros, no negros/invertidos).
- Si el low fue re-posado tras el retopo: **BakeProxy** = topo+UV del low final con
  posiciones pre-conform; el tangent-space es invariante a pose (LL-159).
- AO: ocultar el high y todo excepto el low (auto-oclusión) — media 64→202 al hacerlo.
- Modelos monocromos SIN textura real: NO bakear atlas; rvmat flat-color por material
  con `diffuse[]` y `texture=""` (LL-021 — origen de este doc: el Banshee/LFQuad).
- Padding para atlas: 2048→16px, gutter ≥2× ([polycount](http://wiki.polycount.com/wiki/Edge_padding)).

## 6. Catálogo síntoma → causa → diagnóstico → fix

| Síntoma in-game | Causa probable | Diagnóstico | Fix |
|---|---|---|---|
| Cara de un solo color plano | UVs ausentes/(0,0) o isla colapsada | `uv_audit.py` zero-uv%; OB Structure→Check Faces | Mapear; OB "neighbour mapping" para caras sueltas |
| Textura "equivocada" repetida en piezas distintas; AO con manchas dobles | Bake sobre UVs con overlap | `uv_audit.py` OVERLAP MC por grupo y cross-group | Re-unwrap sin overlap para bake, o AO al 2º UV set ("use texture coords 2") |
| Seam de iluminación en el eje central; detalle hundido en un lado | Islas espejadas + `_nohq` | `uv_audit.py` mirrored% (área UV negativa) | Offset mirroring; re-bake con tangent basis del motor |
| Textura nítida en OB pero distorsionada/shimmer tras binarizar | Cuantización int16 con rango UV enorme en el LOD | RPT "UV coordinate on point N is too big"; bounds en `uv_audit.py` | Re-centrar tiling cerca de 0; mover el tiling al rvmat (`uvTransform`); partir materiales |
| Textura barrida/estirada en un eje | UVs degeneradas (planar map con vista mala, import roto) | `uv_audit.py` degenerate%; RPT "generate ST for points" | Re-unwrap de las caras afectadas |
| Borrosa pese a textura grande | Texel density baja o desigual | `uv_audit.py` px/m; checker grid in-game | Re-escalar islas a densidad uniforme |
| Seams que solo aparecen a distancia | Mip bleed por padding corto | Ver mips del `.paa`; padding de islas | Edge padding §5/§9; fondo del atlas similar a las islas |
| Bake sale negro / huecos / círculos | Islas diminutas sobre fondo negro + deriva UV | `uv_audit.py` islands (mediana caras/isla) + density | LL-021: flat-color rvmat si el modelo es monocromo; si no, re-unwrap con islas mayores |
| "Too many vertices" al binarizar | Exceso de splits UV/normal (vértices resueltos) | Contar seams; memoria `dayz-binarize-vertex-limit` | Compartir normales/UVs donde se pueda; menos islas |
| Todo correcto offline, mal in-game | Convención V-flip perdida en un conversor | Checker asimétrico por el pipeline completo | Aplicar/retirar `1−v` en el paso culpable (§2.3) |
| Atlas ilegible: no se sabe qué isla es qué parte; se pinta/bakea la parte equivocada | Unwrap automático por PIEZAS/caras sueltas (Smart UV atomiza) en vez de por SECCIONES lógicas | `uv_audit.py` islas: mediana de caras/isla baja (2-4) = atomizado; abrir el atlas y ver si un humano lo lee | Re-unwrap **por secciones** (§5): una zona UV contigua y reconocible por sección (depósito, chasis, asiento…), seams marcados a mano |

## 7. Tool: `uv_audit.py` (LFQuad_dev\tools\)

Auditor MLOD sobre py3d. Por LOD visual y grupo textura|material: zero-uv%, NaN,
bounds, degeneradas, espejadas (área UV con signo), **overlap Monte-Carlo** (robusto
con islas subpíxel), islas (union-find sobre UVs compartidas), texel density
(sqrt(uvA/3dA) → px/m a 2048), y overlap cross-group a nivel LOD.

Gotchas del propio tool (aprendidos construyéndolo):
- Raster clásico FALLA con islas subpíxel (tris de <1 texel no cubren ningún centro de
  muestra) → por eso Monte-Carlo con index grid.
- **Whitelistear caras proxy** (selección `proxy:...`): llevan UV degenerada por diseño.
- **Excluir tris "full-frame"** (área UV >0.2) del overlap cross-group: una sola cara
  mapeada a [0,1] entero (p.ej. lente de faro) solapa con todo y da 100% falso.
- Números "exactamente 100%/0.000" = sospecha de artefacto del tool, no del modelo (G3).

## 8. Caso LFQuad (medido 2026-07-05, p3d desplegados)

- **Ruedas (referencia sana, funcionan in-game con `_co` real)**: zero-uv 0%, bounds
  [0.01,0.99], overlap 0.2-0.4%, mirrored ≤0.6%, density p50 ≈ **292 px/m** (2048).
- **Body**: las UVs del Smart-UV-project de 2026-05-23 SÍ viajaron al p3d (0% zero-uv,
  0 NaN, bounds [0,1]) — "importado sin UVs" = sin textura que las use, no sin UVs.
  Problemas reales: **fragmentación** (b_black_1: 1859 islas/9732 caras, mediana 4;
  b_metal_2: 2154 islas, mediana 2), **density p50 ≈ 27 px/m** (10× peor que ruedas;
  pieza de 10cm ≈ 2.7px → causa cuantitativa de los artefactos del bake LL-021),
  overlap por grupo 0-2% con pico **b_white 18.7%** (la selección `color`), cross-group
  4.4%. La cara del faro (`b_lights_fc_nolight`) mapea [0,1] completo.
- El "87.5% overlap" del research 2026-06-14 **no era del p3d desplegado**: RESUELTO
  2026-07-06 — corresponde a las UVs ORIGINALES autoradas del modelo (FBX
  `YAMAHA_BANSHEE_1987_BLEND_DIEZMADO.fbx`: carrocería B_WHITE overlap MC 88.3%,
  buckets 57-88%). Las originales tienen buena densidad (349-1900 px/m@2048) pero
  solape masivo por stacking de piezas instanciadas → inservibles para bake, servibles
  para tiling/flat. Dos linajes de UV distintos: originales (densas+solapadas) vs
  smart-project del p3d (únicas+atomizadas+27 px/m). Ninguno sirve para textura con
  detalle.
- Si algún día se quiere textura con detalle en el body: las UVs actuales NO sirven
  (density+fragmentación); haría falta re-unwrap (§5) + re-bake, respetando que las
  variantes de color actuales (flat, UV-invariantes) seguirían funcionando.

## 9. Números de referencia

| Métrica | Valor | Fuente |
|---|---|---|
| Edge padding | 1024→8px, 2048→16px; gutter ≥2× | polycount edge_padding |
| Texel density props | ~512 px/m | [Beyond Extent](https://www.beyondextent.com/deep-dives/deepdive-texeldensity) |
| Texel density armas FP | ~1024 px/m o más | Beyond Extent + polycount |
| Referencia interna sana | ruedas LFQuad ≈ 292 px/m (2048) | audit 2026-07-05 |
| Rango UV máx por LOD (ODOL) | ~32 en tex 2048 [derivación] | armake p3d.c + PMC arma.rpt |
| Stretch aceptable (Blender) | p10-p90 dentro de 0.8-1.2× | LFInfectedBig 2026-06-25 |
| Smart UV / pack | margin 0.003 / pack margin 0.008, rotate=True | LFInfectedBig 2026-06-25 |

## 10. Fuentes principales

Biki P3D [MLOD](https://community.bistudio.com/wiki/P3D_File_Format_-_MLOD) /
[ODOLV4x](https://community.bistudio.com/wiki/P3D_File_Format_-_ODOLV4x) ·
[armake p3d.c](https://github.com/KoffeinFlummi/armake/blob/master/src/p3d.c) ·
[Super shader](https://community.bistudio.com/wiki/Super_shader) +
[RVMAT basics](https://community.bistudio.com/wiki/RVMAT_basics) ·
[PMC arma.rpt](https://pmc.editing.wiki/doku.php?id=arma:arma.rpt) ·
[DayZ-Samples](https://github.com/BohemiaInteractive/DayZ-Samples) ·
py3d site-packages (verificado en código) · vault: LL-021/123/125/159,
30_Sessions SUB_BRZ fase5 + LFInfectedBig uv-bake.

Pendientes UV abiertos en proyectos: MercedesAMGLF B5 (interior "UV scrambled");
A6_Mk47 V-flip cosmético sin confirmar in-game; source-game `--flip-green` si el `_nohq`
sale invertido in-game.

---
name: ai-3d-to-dayz
description: >
  Front-end para generar un prop, item o asset 3D de DayZ con IA: image/text-to-3D,
  limpieza y retopología low-poly manifold, UV, normal bake high→low, PBR y handoff
  a .p3d/.paa/.rvmat. Úsala para "generar un objeto/modelo 3D para DayZ", "crear un
  prop desde cero", "image to 3D", "convertir un GLB de IA en .p3d", Hunyuan,
  Tripo o Rodin, y low-poly realista. Decide el generador y los gates del front-end;
  alimenta dayz-model-pipeline, el pipeline de texturas y dayz-pbo-build, no los
  sustituye. Compón con blender-assembly, dayz-3d-viewer y 3d-generation-harness.
  hunyuan3d-local es opcional/externa (no va en este pack). No usar para humanoides ni animación.
---

# ai-3d-to-dayz

Front-end de generación asistida por IA para producir un asset 3D **game-ready para DayZ** desde una
idea. Scaffold de workflow: la estructura y los handoffs están verificados; los tool-picks concretos son
claims del canal @stefan_3d_ai marcados `❓ validar` hasta confirmarlos con tests propios.

> **Fuente y estado:** destilado de 33 vídeos del canal. KB con timestamps en
> `<knowledge-notes>\ai-3d-pipeline\` (`index.md` + 6 stages). Nombres de
> tools / versiones / settings = claims del creador, NO hechos. Verificar antes de fiarse (R2).

## WHEN TO USE

- El usuario quiere un objeto/prop/item para un mod DayZ y no quiere (o no puede) modelarlo a mano.
- Hay una imagen de referencia, o se puede generar una.
- Target = **props/items estáticos o con partes mecánicas** (armas, contenedores, equipo, props de mundo).
- NO usar para: personajes humanoides, o cuando la necesidad principal es animación esquelética (el
  pipeline del canal no cubre animación config-driven de DayZ — ver `stage-05-animation` de la KB).

## PIPELINE (scaffold idea → .p3d)

1. **Referencia.** Imagen limpia: fondo blanco, iluminada por todos lados, sin objetos extra. Tools
   `❓ validar`: Nano Banana / Krea / 3D AI Studio. **Quitar fondo SIEMPRE** antes de image-to-3D.
2. **Generar malla.** Geometría > textura (DayZ rehace la textura). Rutas verificadas como disponibles:
   - **Hunyuan 2.1 local** (RTX 3090) → skill externa opcional `hunyuan3d-local` si está instalada (no se distribuye en este pack). Controlar `target_face_number`.
   - **Tripo / 3D AI Studio** (acceso de pago) → vía de pago para generar malla; pedir low-poly con control de polígonos. No hay skill en este pack que lo automatice.
   - Controlar el poly count EN la generación; sin límite, toda tool saca millones de tris.
3. **Limpiar + retopo.** Importar GLB a Blender (invoca `blender-assembly`). Bajar a low-poly **manifold**:
   Retopoflow (manual) o Quad Remesher; o AI auto-retopo (Tripo/Rodin/Hunyuan) **+ cleanup obligatorio**.
4. **UV + normal bake (high→low).** Es el paso que genera el `_nohq`. Blender Cycles, selected→active
   (low primero, luego high), Bake Type Normal, Non-Color, margin 8px, tunear Extrusion/Max Ray Distance.
   Detalle de settings: `stage-01-mesh-retopo-uv-bake` de la KB. DayZ `_nohq` is DirectX-style (Y−):
   invert the green channel on export — verified fixture F7 in blender-assembly (Rule 11).
5. **Texturizar sobre la UV.** Tool: **Modddif** ❓ (pending validation, backlog #3: UV-respect and map
   usability unverified) (color → `_co`; normal → `_nohq`; NO saca roughness/metallic).
   El `_smdi` se hace aparte (PBR manual en Blender, o repackear un ORM de Tripo). NO re-mallar un retopo'd.
6. **Handoff DayZ.** Ensamblar `.p3d` MLOD — **opción recomendada: add-on Blender Arma 3 Object Builder**
   (lo que usa la comunidad DayZ; LODs/proxies/named selections nativos) o py3d. `_smdi`: repackear
   rough/metal con **preset SubstanceToArma** (R=white,G=metal,B=rough, invertir rough). Convertir a `.paa`
   (TexView/ImageToPAA), montar `.rvmat`, binarizar. → skills `dayz-texture-pipeline`, `dayz-model-pipeline`,
   `dayz-pbo-build`. Previsualizar con `dayz-3d-viewer`. Validar in-game con `dayz-test-ingame`.

## HARD RULES (las trampas que rompen DayZ)

- **La IA es solo BLOCKOUT high-poly, NO produce assets game-ready para DayZ** (confirmado por
  contrafactual independiente, 2026-06-23). El pipeline oficial Bohemia/Enfusion exige geometría
  manifold+cerrada+convexa y ships un Model Quality Assurance que marca non-manifold/ngon/non-convex
  como defectos — justo lo que la IA + auto-retopo generan. El output IA va SIEMPRE por retopo manual
  (Retopoflow/Quad Remesher) + UV + bake + validación Object Builder antes del `.p3d`. "AI auto-retopo
  suficiente" = REFUTADO. (liga con `dayz-binarize-vertex-limit`; detalle en `20_Knowledge/ai-3d-pipeline/counterfactual.md`).
- **NUNCA fiar la colocación / orientación / escala de un `.p3d` a la visión IA** — es el eslabón débil
  documentado (rota 90°, no reposiciona). Usar checks numéricos (verify_bounds) + diff contra imagen de
  referencia. (liga con `blender-visual-review`).
- Las tools de textura **DEBEN texturizar sobre la UV existente**, no re-mallar un modelo ya retopo'd.
  Verificar este punto en cualquier tool nueva antes de meterla en el pipeline.
- Vértices DayZ = punto×normal×uv por LOD. El budget no es "caras"; normales compartidas reducen el conteo.
- Nombres/versiones/settings de tools marcados `❓` son **claims sin verificar del creador** — confirmar
  contra la herramienta real antes de codificarlos como verdad.

## TOOL SHORTLIST (estado)

| Tool | Rol | Estado |
|---|---|---|
| Hunyuan 2.1 (local) | generar **blockout** high-poly, poly control | disponible ✅ (skill externa `hunyuan3d-local`, no en este pack) |
| Tripo / 3D AI Studio | generar malla low-poly, retopo, PBR | acceso ✅; **#1 en arena low-poly independiente (Top3D 71.8%)**; ⚠️ Smart Low-Poly tras paywall |
| Blender + Retopoflow/Quad Remesher (o ZRemesher/InstaLOD) | retopo manifold, UV, bake | núcleo ✅ — **insalvable** (la IA no lo reemplaza) |
| **Arma 3 Object Builder** (add-on Blender, MrClock8163) | `.p3d` MLOD nativo: LODs, proxies, named selections, RVMAT, RTM | ✅ **estándar de la comunidad DayZ** (Discord + dep. DayZ-LOD-Tools); **sustituto/complemento de py3d**. Ver [[arma3-object-builder]] |
| **Modddif** (ex-"Modif/Motif") | color (`_co`) + normal (`_nohq`) sobre UV existente | ✅ free; NO roughness/metallic |
| 3D AI Studio / Meshy Texture | PBR completo (albedo+normal+rough+metal) sobre UV existente | ✅ confirmado; repackear a `_smdi` |
| Sloyd (paramétrico) | props templados (barriles/cajas/armas) quad+UV+LOD out-of-box | ✅ menos cleanup que IA para props simples |
| Rodin (Hyper3D) | edición de malla, partes, PBR | acceso ✅; #3 arena low-poly |
| AI animación (Mixamo/AccuRig/Cascadeur/…) | rig/anim humanoide | BAJA para props DayZ |

## VALIDATION BACKLOG (endurecer este skill tras esto)

1. ~~Generación A/B: mismo prop DayZ vía Hunyuan 2.1 local vs Tripo → geometría + poly control.~~
   RESOLVED by the 2026-06-10 mk47 shootout (hunyuan3d-local §"Hard-surface → fal.ai") + the 2026-06-23
   full-body case: local 2.1 wins as default (free, organic, concept iteration); fal Hunyuan 3.1 Pro for
   fine hard-surface; fal Rodin 2.5 for organic full-body; Tripo 2.5 gave efficient direct low-poly
   (92k tris) but was not the pick.
2. Normal bake high→low (workflow Ep.3) → exportar → `_nohq.paa` → validar in-game.
3. Modif sobre una UV hecha → ¿respeta la UV? ¿maps sirven para `_co`/`_nohq`?
4. LOD batch vía Blender-MCP: un prompt que decime a N targets + downscale texturas → prototipo de LODs
   (any VISUAL decimation is user-gated — rule 2026-07-02: ask before, default is manual by the user).

Al confirmar cada punto: sustituir el `❓` correspondiente por el dato verificado + cita, aquí y en la KB.

## SOURCES

- KB: `20_Knowledge/ai-3d-pipeline/index.md` (+ stage-00/01/04/05/07/08).
- **Contrafactual + deep dives:** `counterfactual.md`, `arma3-object-builder.md`, `alternatives-deep-dive.md`.
- Externas clave: [Arma3 Object Builder](https://github.com/MrClock8163/Arma3ObjectBuilder) · [SubstanceToArma (preset `_smdi`)](https://github.com/MoonieFR/SubstanceToArma) · [Top3D low-poly arena](https://www.top3d.ai/leaderboard?type=low-poly).
- Transcripciones: `30_Research/youtube/stefan_3d_ai/` (33 vídeos) + `_counterfactual/` (5 independientes).
- Skill de extracción: `youtube-research`.

## (added 2026-06-23) Ruta personajes / infected (zombis)

Para un personaje o criatura humanoide (zombi / infected DayZ) NO autorar desde cero: reskin de un vanilla.
Recipe verificado en `20_Knowledge/dayz-custom-infected.md` -- heredar `ZombieMaleBase` reutiliza el esqueleto
`OFP2_ManSkeleton` + animaciones + IA vanilla (gratis por herencia del bloque `enfanimsys`); el coste real es
riguear la malla a los bones vanilla. Escalado runtime de DayZ roto (T140705) -> hornear el tamano en la
malla. La generacion de la malla full-body organica va por fal Rodin (ver hunyuan3d-local added 2026-06-23).

## Reglas promovidas del corpus de lecciones (added 2026-07-27)

Promovidas desde `AI/20_Knowledge/lessons-learned.md` para que lleguen por trigger en vez
de depender de que alguien recuerde buscarlas. Cada regla cita su `LL-NNN` de origen;
la entrada completa (síntoma, origen, evidencia) vive allí. No quites la cita: el índice
`lessons-index.md` detecta la promoción buscando esa referencia dentro de las skills.

- **LL-154** — Prepara la referencia con rembg, autocrop, fondo blanco, margen y agujeros transparentes rellenados; usa cuerpo completo cuando el output lo requiera. Tras generar, valida `trimesh.extents`: un eje casi cero es un fallo plano aunque el render parezca plausible.

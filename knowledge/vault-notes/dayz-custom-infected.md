---
title: Custom infected (zombi) en DayZ — recipe verificado
type: knowledge
created: 2026-06-23
status: verificado contra fuentes primarias (config vanilla del usuario, BI wiki, feedback tracker, DayZ Modders Discord)
tags: [dayz, infected, zombie, skeleton, rigging, scaling, p3d]
---

# Custom infected (zombi) en DayZ — recipe verificado

Cómo añadir un zombi custom **reutilizando esqueleto + animaciones + IA vanilla** (solo malla nueva).
Verificado 2026-06-23 (3 agentes, fuentes primarias). Origen: petición "un zombi un poco más grande con
agujero en el torso".

## 1. Config — herencia (trivial, well-trodden)
Jerarquía vanilla (verificada en `DZ\characters\zombies\config.cpp` del usuario):
`DZ_LightAI → DayZInfected → ZombieBase → ZombieMaleBase / ZombieFemaleBase → Zmb*_Base → variantes`.

**El esqueleto + anims + IA se heredan automáticamente** vía el bloque `enfanimsys` (en `ZombieBase`):
```cpp
class enfanimsys {
    meshObject="dz\characters\zombies\z_hermit_m.xob";
    graphname="dz\anims\workspaces\infected\infected_main\infected.agr";
    skeletonName="hermit_newbindpose.xob";
    ...
};
```
Un hijo lo hereda intacto → todas las animaciones de infected + el driver de IA, gratis. Config mínima
(patrón de `ZmbM_HermitSkinny_Base`):
```cpp
class CfgVehicles {
    class ZombieMaleBase;
    class MyZ_Base: ZombieMaleBase { scope=0; model="\MyMod\infected\myz.p3d"; hiddenSelectionsMaterials[]={...}; };
    class MyZ: MyZ_Base { scope=2; hiddenSelectionsTextures[]={"MyMod\data\myz_co.paa"}; };
};
```
Spawneo vía CE (`cfgspawnabletypes.xml` / territorios de zombis) como cualquier zed.
Requisito comunidad (PvZmoD): el custom **debe heredar de `ZombieBase`** (NO AnimalBase).

## 2. Rigging — el coste real
- Esqueleto humanoide DayZ = **`OFP2_ManSkeleton`** (lo comparten player + infected). La malla DEBE usar los
  nombres de bone/selección exactos; las anims están keyed a esos nombres ("not gonna work if you're not
  using dayz skeleton").
- En DayZ los "bones" del model.cfg = **selecciones de vértices nombradas**, no un armature; la deformación
  son weights por vértice a selecciones nombradas como los bones.
- **Rig oficial disponible:** [BI DayZ-Misc "Rig and Animations"](https://github.com/BohemiaInteractive/DayZ-Misc) (rig de player).
- Workflow Blender recomendado (Strykar, Discord 2026): crear el armature de zombi DESDE el player rig,
  parent con **automatic weights**, o renombrar vertex groups a los bones DayZ → import a Object Builder con
  weights + selecciones. Tools: **Arma 3 Object Builder** (comparte `OFP2_ManSkeleton`, importa RTM) +
  **DayZATool** (DTZxPorter).
- Bones a pesar (de `P3DAttachments` vanilla): Spine1/2/3, Head, Pelvis, LeftHand, RightHand_Dummy, piernas…
- Fallos típicos: selección sin weight → vértices pinchados/estirados; nombres que no cuadran con
  `skeletonBones[]` → malla explota.
- **La malla vanilla está BINARIZADA** (ODOL v54) → no se edita directa; autorar nueva + riguear (o debinarizar).

### Rigging verificado en práctica (LFInfectedBig S4, 2026-06-24)
- **Fuente del armature = `animation_rig_character.fbx`** de [BI DayZ-Misc](https://github.com/BohemiaInteractive/DayZ-Misc)
  (carpeta "Rig and Animations"). Es **Blender-native** (FBX): armature `Armature` con **114 bones cuyos
  nombres = OFP2_ManSkeleton exacto**, + un mesh **`Male_body` (7499 v) ya pesado en bind A-pose** (ref de
  proporciones/bind gratis). Unidades = **cm** (altura 172.5). Los helpers (`*_Dummy`, `Weapon_*`,
  `EntityPosition`) vienen como **EMPTIES**, no como bones del armature → se ignoran para el deform corporal.
- **GOTCHA crítico de auto-weights**: antes del bone-heat hay que **`transform_apply(scale=True)` sobre el
  ARMATURE** (bakear la escala en la bone data). Si solo escalas el objeto/padre, el bone-heat corre a la
  escala nativa del rig (172 u) contra tu malla (p.ej. 2.277 m) → **toda la malla se pesa a `Pelvis`** y el
  resto de bones quedan a 0 verts. Tras aplicar la escala, los pesos se reparten bien.
- **El `tail-head` de los bones tras importar FBX es basura** (el importador auto-genera los tails) → NO
  usarlo para detectar la pose (A vs T); fiarse de un render o del skinning real.
- **Bind pose**: la malla DEBE shippear en la **bind A-pose canónica** del rig (anims son relativas al rest).
  Conformar los brazos de la malla a los bones (rotación enmascarada por el peso de auto-weight = falloff
  suave en el hombro) si están más cerrados/abiertos que el canónico.
- **Cleanup**: `vertex_group_limit_total(4)` + `vertex_group_normalize_all` → máx 4 influences/vért, 0 verts
  sin peso (objetivo: cero pinching). Desactivar `use_deform` en cara/dedos/ojos reduce ruido de vgroups.
- Tools en disco (este PC): Object Builder en `…\DayZ Tools\Bin\ObjectBuilder\ObjectBuilder.exe`;
  DayZATool v1.3 en `Downloads\DayZATool_v1.3\` (solo para `.anm`, tiene un crash-dump previo).

### UV + normal/AO bake verificado en práctica (LFInfectedBig S5, 2026-06-25)
Detalle completo + patrones de script: `~/.claude/skills/dayz-characters/references/character-uv-bake.md`.
Gotchas que cada uno costó una iteración:
- **Bakear desde un proxy en pose PRE-conform**, no desde el low conformado. El conform del rig (S4) abre
  los miembros → el high (sin conformar) ya no coincide con el low → bake directo = ruido. Proxy =
  topología+UV del low que shippea con las posiciones del retopo (alineadas con el high); el normal
  tangent-space aplica al low conformado (invariante a la pose con misma topo+UV).
- **NO `normals_make_consistent` en el high AI no-watertight** (voltea shells → manchas negras). Originales + smooth.
- **Misses → pre-rellenar la imagen con neutro (128,128,255) + `use_clear=False`** (negro = normal hacia dentro = render negro).
- **AO**: ocultar todo menos el target (el high coincidente auto-ocluye → AO oscuro) + limpiar custom-split normals del low.
- `_nohq` = DirectX **Y-** → invertir canal verde del bake OpenGL. Triangular antes del bake y shippear triangulado.
- Geometría interna decorativa (costillas): bone-heat falla en mallas finas auto-intersectadas → pesos por
  altura al spine chain (o DATA_TRANSFER del cuerpo limpiando fuga de hombro/brazo).
- Gate = preview iluminado del low+normal vs el high + checks numéricos (spread de stretch UV, 0% pixeles negros, AO surface ~200).

## 3. Escalado ("más grande") — runtime ROTO, hornear en malla
- **`SetScale`/`GetScale` no funcionan en entidades** ([T140705](https://feedback.bistudio.com/T140705)); la
  collision box no escala con SetScale (Discord abr-2026); el `scale` del Object Spawner es **solo objetos
  estáticos**, no personajes/IA; no hay per-axis; no hay key `scale` de personaje en CfgVehicles.
- **Única vía: hornear el tamaño en la malla** sobre el mismo `OFP2_ManSkeleton`. Geometry + collision LODs
  escalan juntos (colisión cuadra). Coste: las anims vanilla asumen longitudes de hueso vanilla →
  **foot-sliding/IK drift**, peor cuanto más lejos de 1.0x.
- **~1.2x = sutil, probablemente aceptable**; 2x rompe feo. Sin ejemplos shipped de infected gigante limpio.
- ⚠️ Verificar in-game: contacto de pies, clipping en puertas, alcance de melee/hit, pathing IA.

## 4. El agujero pasante en el torso
- **Visual:** modelar el **túnel interior** (superficie cerrada, front-facing) = lo más robusto. Alternativa:
  flag de cara "both sides" `0x00000020` ([BI P3D flags](https://community.bohemia.net/wiki/P3D_Point_and_Face_Flags))
  o geometría double-sided (`make_double_sided.py`). ⚠️ **Discrepancia a verificar:** el wiki dice
  `0x00000020`; el `CLAUDE.md` del proyecto (Pendientes) dice `0x20000` para NoBackfaceCulling — confirmar cuál.
- **Colisión (Geometry LOD):** debe ser **"closed and convex"** (verbatim [BI Validating Geometries](https://community.bohemia.net/wiki/Validating_Geometries)).
  Un torso agujereado NO es convexo → o **convex decomposition** en `ComponentXX` numerados, o (lo simple)
  **dejar la colisión sólida** (ignorar el hueco). El collision LOD NO tiene que coincidir con el visual.
  Mass ≥10.
- **FireGeometry:** sólida salvo que quieras shots-through (poco payoff, más componentes). Con colisión
  sólida, **las balas por el agujero igual impactan** — decisión de diseño.
- **Damage zones:** config-driven (`componentNames[]`, [DayZ-Samples](https://github.com/BohemiaInteractive/DayZ-Samples/blob/master/Test_Building/config.cpp));
  sobreviven al torso remodelado si se preservan las selecciones/componentes nombrados que la config espera.

## Veredicto de esfuerzo/riesgo
| Parte | Dificultad |
|---|---|
| Config (heredar ZombieMaleBase) | ✅ trivial |
| Reusar esqueleto/anims/IA | ✅ gratis (herencia enfanimsys) |
| Agujero visual + colisión sólida | ✅ bajo riesgo |
| **Riguear malla custom a OFP2_ManSkeleton** | ⚠️ medio — el coste real (tier rigging de personaje) |
| **"Más grande"** | ⚠️ hornear ~1.2x en malla; runtime scale roto; verificar anims in-game |

## Plan (alto nivel)
1. Malla del zombi (AI desde la imagen ref / o editar base humanoide) conformada a proporciones del rig + el agujero (túnel).
2. Riguear a `OFP2_ManSkeleton` (rig oficial BI + auto-weights, cleanup).
3. Hornear ~1.2x en la malla. LODs: Visual (con hueco) / Geometry sólido convexo / Fire / Memory.
4. Textura → `_co/_nohq/_smdi` (ver [[alternatives-deep-dive]] §4, preset SubstanceToArma).
5. Config: `MyZ_Base: ZombieMaleBase` + variante; model.cfg con `OFP2_ManSkeleton`.
6. PBO (AddonBuilder) → binarize → test in-game (anims/foot-slide/colisión/hit/spawn).

## Fuentes
- Config vanilla local `DZ\characters\zombies\config.cpp`; [dayzexplorer ZombieBase](https://dayzexplorer.zeroy.com/zombiebase_8c_source.html)
- [OFP2_ManSkeleton model.cfg (Epoch)](https://github.com/EpochModTeam/DayZ-Epoch/blob/master/SQF/dayz_code/anim/model.cfg) · [BI Model Config](https://community.bistudio.com/wiki/Model_Config) · [BI DayZ-Misc rig](https://github.com/BohemiaInteractive/DayZ-Misc)
- [T140705 SetScale roto](https://feedback.bistudio.com/T140705) · [DayZ Object Spawner scale](https://community.bistudio.com/wiki/DayZ:Object_Spawner)
- [BI LOD](https://community.bohemia.net/wiki/LOD) · [Validating Geometries](https://community.bohemia.net/wiki/Validating_Geometries) · [P3D flags](https://community.bohemia.net/wiki/P3D_Point_and_Face_Flags)
- Ejemplos: [Skeleton Zombies (zisb)](https://steamcommunity.com/sharedfiles/filedetails/?id=1865458192) · [PvZmoD](https://steamcommunity.com/workshop/filedetails/discussion/2051775667/3880365909907863489/)
- DayZ Modders Discord (rigging, scaling, convex geo) vía Answer Overflow

## Related

- [[dayz-animations-creatures-weapons]] — anim graph, bones del esqueleto y commands `CMD_*` que el zombi hereda vía enfanimsys.
- [[dayz-model-pipeline]] — assembly del `.p3d`, LODs (Visual con hueco / Geometry convexo) y memory points.
- [[stage-01-mesh-retopo-uv-bake]] — retopo + UV + normal/AO bake de la malla AI antes de riguear.
- [[alternatives-deep-dive]] — texturizado `_co/_nohq/_smdi` (preset SubstanceToArma) referenciado en el plan.
- [[dayz-mod-implementation-checklists]] — checklist de config.cpp / herencia / persistence para la entidad final.
- [[30_Sessions/2026-06-25-LFInfectedBig-export-texture-lods|LFInfectedBig export]] — sesión real que aplicó este recipe end-to-end (rig→.p3d→PBO).

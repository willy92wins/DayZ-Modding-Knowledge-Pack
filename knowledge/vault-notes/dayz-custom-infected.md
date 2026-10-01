---
title: Custom infected (zombi) en DayZ — recipe verificado
type: knowledge
created: 2026-06-23
status: verificado contra fuentes primarias (config vanilla del usuario, BI wiki, feedback tracker, DayZ Modders Discord)
tags: [dayz, infected, zombie, skeleton, rigging, scaling, p3d]
---

# Custom infected (zombie) in DayZ — verified recipe

How to add a custom zombie **reusing vanilla skeleton + animations + AI** (new mesh only).
Verified 2026-06-23 (3 agents, primary sources). Origin: request "a slightly larger zombie with
a hole in the torso".

## 1. Config — herencia (trivial, well-trodden)
Vanilla hierarchy (verified in user's `DZ\characters\zombies\config.cpp`):
`DZ_LightAI → DayZInfected → ZombieBase → ZombieMaleBase / ZombieFemaleBase → Zmb*_Base → variants`.

**Skeleton + anims + AI are inherited automatically** via the `enfanimsys` block (in `ZombieBase`):
```cpp
class enfanimsys {
    meshObject="dz\characters\zombies\z_hermit_m.xob";
    graphname="dz\anims\workspaces\infected\infected_main\infected.agr";
    skeletonName="hermit_newbindpose.xob";
    ...
};
```
A child inherits it intact → all infected animations + AI driver, for free. Minimal config
(`ZmbM_HermitSkinny_Base` pattern):
```cpp
class CfgVehicles {
    class ZombieMaleBase;
    class MyZ_Base: ZombieMaleBase { scope=0; model="\MyMod\infected\myz.p3d"; hiddenSelectionsMaterials[]={...}; };
    class MyZ: MyZ_Base { scope=2; hiddenSelectionsTextures[]={"MyMod\data\myz_co.paa"}; };
};
```
Spawning via CE (`cfgspawnabletypes.xml` / zombie territories) like any zed.
Community requirement (PvZmoD): custom **must inherit from `ZombieBase`** (NOT AnimalBase).

## 2. Rigging — the real cost
- DayZ humanoid skeleton = **`OFP2_ManSkeleton`** (shared by player + infected). The mesh MUST use the
  exact bone/selection names; anims are keyed to those names ("not gonna work if you're not
  using dayz skeleton").
- In DayZ, model.cfg "bones" = **named vertex selections**, not an armature; deformation
  consists of per-vertex weights to selections named like the bones.
- **Official rig available:** [BI DayZ-Misc "Rig and Animations"](https://github.com/BohemiaInteractive/DayZ-Misc) (player rig).
- Recommended Blender workflow (Strykar, Discord 2026): create zombie armature FROM the player rig,
  parent with **automatic weights**, or rename vertex groups to DayZ bones → import into Object Builder with
  weights + selections. Tools: **Arma 3 Object Builder** (shares `OFP2_ManSkeleton`, imports RTM) +
  **DayZATool** (DTZxPorter).
- Bones to weight (from vanilla `P3DAttachments`): Spine1/2/3, Head, Pelvis, LeftHand, RightHand_Dummy, legs…
- Typical failures: unweighted selection → pinched/stretched vertices; names not matching
  `skeletonBones[]` → mesh explodes.
- **Vanilla mesh is BINARIZED** (ODOL v54) → not directly editable; author new + rig (or unbinarize).

### Rigging verified in practice (LFInfectedBig S4, 2026-06-24)
- **Armature source = `animation_rig_character.fbx`** from [BI DayZ-Misc](https://github.com/BohemiaInteractive/DayZ-Misc)
  ("Rig and Animations" folder). It is **Blender-native** (FBX): `Armature` armature with **114 bones whose
  names = exact OFP2_ManSkeleton**, + a **`Male_body` mesh (7499 v) already weighted in bind A-pose** (free
  proportion/bind ref). Units = **cm** (height 172.5). Helpers (`*_Dummy`, `Weapon_*`,
  `EntityPosition`) come as **EMPTIES**, not as armature bones → ignored for body deformation.
- **Critical auto-weights GOTCHA**: before bone-heat you must run **`transform_apply(scale=True)` on the
  ARMATURE** (bake scale into bone data). If you only scale the object/parent, bone-heat runs at the
  native rig scale (172 u) against your mesh (e.g. 2.277 m) → **entire mesh is weighted to `Pelvis`** and the
  remaining bones stay at 0 verts. After applying scale, weights distribute properly.
- **Bone `tail-head` after importing FBX is garbage** (importer auto-generates tails) → do NOT
  use it to detect pose (A vs T); rely on a render or actual skinning.
- **Bind pose**: mesh MUST ship in the **canonical bind A-pose** of the rig (anims are relative to rest).
  Conform mesh arms to bones (rotation masked by auto-weight weight = smooth
  shoulder falloff) if they are more closed/open than canonical.
- **Cleanup**: `vertex_group_limit_total(4)` + `vertex_group_normalize_all` → max 4 influences/vert, 0
  unweighted verts (goal: zero pinching). Disabling `use_deform` on face/fingers/eyes reduces vgroup noise.
- Tools on disk (this PC): Object Builder at `…\DayZ Tools\Bin\ObjectBuilder\ObjectBuilder.exe`;
  DayZATool v1.3 at `Downloads\DayZATool_v1.3\` (for `.anm` only, has a previous crash-dump).

### UV + normal/AO bake verified in practice (LFInfectedBig S5, 2026-06-25)
Full details + script patterns: `~/.claude/skills/dayz-characters/references/character-uv-bake.md`.
Gotchas where each cost an iteration:
- **Bake from a proxy in PRE-conform pose**, not from the conformed low. Rig conform (S4) opens
  limbs → unconformed high no longer matches low → direct bake = noise. Proxy =
  low topology+UV shipping with retopo positions (aligned with high); tangent-space
  normal applies to conformed low (pose-invariant with same topo+UV).
- **NO `normals_make_consistent` on non-watertight AI high** (flips shells → black spots). Originals + smooth.
- **Misses → pre-fill image with neutral (128,128,255) + `use_clear=False`** (black = inward normal = black render).
- **AO**: hide everything except target (coincident high self-occludes → dark AO) + clear low custom-split normals.
- `_nohq` = DirectX **Y-** → invert green channel from OpenGL bake. Triangulate before bake and ship triangulated.
- Decorative internal geometry (ribs): bone-heat fails on thin self-intersecting meshes → height-based
  weights to spine chain (or DATA_TRANSFER from body clearing shoulder/arm bleed).
- Gate = lit preview of low+normal vs high + numeric checks (UV stretch spread, 0% black pixels, AO surface ~200).

## 3. Scaling ("larger") — runtime BROKEN, bake into mesh
- **`SetScale`/`GetScale` do not work on entities** ([T140705](https://feedback.bistudio.com/T140705));
  collision box does not scale with SetScale (Discord Apr-2026); Object Spawner `scale` is **static objects
  only**, not characters/AI; no per-axis; no character `scale` key in CfgVehicles.
- **Only route: bake size into mesh** over the same `OFP2_ManSkeleton`. Geometry + collision LODs
  scale together (collision matches). Cost: vanilla anims assume vanilla bone lengths →
  **foot-sliding/IK drift**, worse the farther from 1.0x.
- **~1.2x = subtle, probably acceptable**; 2x breaks badly. No shipped examples of clean giant infected.
- ⚠️ Verify in-game: foot contact, door clipping, melee/hit range, AI pathing.

## 4. Through-hole in the torso
- **Visual:** model **interior tunnel** (closed, front-facing surface) = most robust. Alternative:
  "both sides" face flag `0x00000020` ([BI P3D flags](https://community.bohemia.net/wiki/P3D_Point_and_Face_Flags))
  or double-sided geometry (`make_double_sided.py`). ⚠️ **Discrepancy to verify:** wiki says
  `0x00000020`; project `CLAUDE.md` (Pending) says `0x20000` for NoBackfaceCulling — confirm which.
- **Collision (Geometry LOD):** must be **"closed and convex"** (verbatim [BI Validating Geometries](https://community.bohemia.net/wiki/Validating_Geometries)).
  A torso with a hole is NOT convex → either **convex decomposition** into numbered `ComponentXX`, or (the simple route)
  **leave collision solid** (ignore gap). Collision LOD does NOT have to match visual LOD.
  Mass ≥10.
- **FireGeometry:** solid unless you want shots-through (low payoff, more components). With solid
  collision, **bullets through the hole still impact** — design decision.
- **Damage zones:** config-driven (`componentNames[]`, [DayZ-Samples](https://github.com/BohemiaInteractive/DayZ-Samples/blob/master/Test_Building/config.cpp));
  survive remodeled torso if named selections/components expected by config are preserved.

## Effort/risk verdict
| Part | Difficulty |
|---|---|
| Config (inherit ZombieMaleBase) | ✅ trivial |
| Reuse skeleton/anims/AI | ✅ free (enfanimsys inheritance) |
| Visual hole + solid collision | ✅ low risk |
| **Rig custom mesh to OFP2_ManSkeleton** | ⚠️ medium — the real cost (character rigging tier) |
| **"Larger"** | ⚠️ bake ~1.2x into mesh; runtime scale broken; verify anims in-game |

## Plan (alto nivel)
1. Zombie mesh (AI from ref image / or edit humanoid base) conformed to rig proportions + hole (tunnel).
2. Rig to `OFP2_ManSkeleton` (official BI rig + auto-weights, cleanup).
3. Bake ~1.2x into mesh. LODs: Visual (with hole) / solid convex Geometry / Fire / Memory.
4. Texture → `_co/_nohq/_smdi` (see [[alternatives-deep-dive]] §4, SubstanceToArma preset).
5. Config: `MyZ_Base: ZombieMaleBase` + variant; model.cfg with `OFP2_ManSkeleton`.
6. PBO (AddonBuilder) → binarize → in-game test (anims/foot-slide/collision/hit/spawn).

## Fuentes
- Local vanilla config `DZ\characters\zombies\config.cpp`; [dayzexplorer ZombieBase](https://dayzexplorer.zeroy.com/zombiebase_8c_source.html)
- [OFP2_ManSkeleton model.cfg (Epoch)](https://github.com/EpochModTeam/DayZ-Epoch/blob/master/SQF/dayz_code/anim/model.cfg) · [BI Model Config](https://community.bistudio.com/wiki/Model_Config) · [BI DayZ-Misc rig](https://github.com/BohemiaInteractive/DayZ-Misc)
- [T140705 SetScale broken](https://feedback.bistudio.com/T140705) · [DayZ Object Spawner scale](https://community.bistudio.com/wiki/DayZ:Object_Spawner)
- [BI LOD](https://community.bohemia.net/wiki/LOD) · [Validating Geometries](https://community.bohemia.net/wiki/Validating_Geometries) · [P3D flags](https://community.bohemia.net/wiki/P3D_Point_and_Face_Flags)
- Examples: [Skeleton Zombies (zisb)](https://steamcommunity.com/sharedfiles/filedetails/?id=1865458192) · [PvZmoD](https://steamcommunity.com/workshop/filedetails/discussion/2051775667/3880365909907863489/)
- DayZ Modders Discord (rigging, scaling, convex geo) via Answer Overflow

## Related

- [[dayz-animations-creatures-weapons]] — anim graph, skeleton bones and `CMD_*` commands that zombie inherits via enfanimsys.
- [[dayz-model-pipeline]] — `.p3d` assembly, LODs (Visual with hole / convex Geometry) and memory points.
- [[stage-01-mesh-retopo-uv-bake]] — retopo + UV + normal/AO bake of AI mesh before rigging.
- [[alternatives-deep-dive]] — `_co/_nohq/_smdi` texturing (SubstanceToArma preset) referenced in plan.
- [[dayz-mod-implementation-checklists]] — config.cpp / inheritance / persistence checklist for final entity.
- [[30_Sessions/2026-06-25-LFInfectedBig-export-texture-lods|LFInfectedBig export]] — real session that applied this recipe end-to-end (rig→.p3d→PBO).

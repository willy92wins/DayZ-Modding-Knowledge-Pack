# LODs and Object Builder for DayZ doors

## Contents

- [Cross-LOD rule](#cross-lod-rule)
- [Resolution LOD](#resolution-lod)
- [Geometry LOD](#geometry-lod)
- [View Geometry LOD](#view-geometry-lod)
- [Fire Geometry LOD](#fire-geometry-lod)
- [Memory LOD](#memory-lod)
- [Pattern matrices](#pattern-matrices)
- [Object Builder validation](#object-builder-validation)
- [Pre-export checklist](#pre-export-checklist)
- [DayZ 1.30 Exp: Memory points and lock slots](#dayz-130-exp-memory-points-and-lock-slots)
- [Sources](#sources)

## Cross-LOD rule

Names are the contract. A moving or interactive part must use its intended name in each LOD where that role exists, then match model.cfg/config.cpp.

Not every visible component belongs in every physical LOD. Simple Door omits the handle from Geometry because it needs no real-world collision while retaining it in visible/interaction LODs (**Simple_Door Readme.txt:9-23**).

## Resolution LOD

Purpose: render the visible object.

- Name every visible logical component relevant to animation/materials.
- Simple: frame, door, handle (**Simple_Door Readme.txt:9-10**).
- Button: frame, door, handle, button (**Door_w_Button Readme.txt:9-10**).
- Expert: door, handle, lever (**Expert tutorial:8-9**).
- Animated names must match skeleton bones and animation selections.

Do not infer that every visible component needs collision. Assign later LODs by function.

## Geometry LOD

Purpose here: physical presence and collision.

- Include only components needing real-world space.
- Reuse the Resolution component name.
- Find components via **Structure > Topology > Find Components**.
- Shapes must be closed and convex.
- Simple: named door; handle omitted (**Simple_Door Readme.txt:12-14**).
- Button: **door1** and button (**Door_w_Button Readme.txt:12**).
- Expert: **door1** and lever (**Expert tutorial:11**).

If a tiny handle needs collision in a new design, ask before adding it instead of copying the omission blindly.

## View Geometry LOD

Purpose in tutorials:

- Interaction components/selections.
- View occlusion; units and AI should not see through a correct object.
- Geometry LOD fallback if View Geometry is absent (**Simple_Door Readme.txt:16-18**).

Requirements:

- Put the interactive named selection here.
- Match model.cfg **source** to that interaction selection.
- Source may differ from moving selection.
- For separate button/lever, use **door1_open** on the controller so Open appears there instead of at the door (**Door_w_Button Readme.txt:14-16**; **Expert tutorial:13-15**).
- A static button need not be a skeleton bone (**Door_w_Button Readme.txt:65**).

## Fire Geometry LOD

Purpose: penetration behavior/materials.

- Include components needing a penetration value.
- Assign material-appropriate penetration RVMATs.
- Keep names aligned with corresponding components.
- Simple includes relevant components for penetration (**Simple_Door Readme.txt:20-21**).
- Button/Expert describe a View Geometry copy with penetration RVMATs (**Button tutorial:18**; **Expert tutorial:17**).

A literal View Geometry copy is the supplied pattern, not a universal optimization rule. Validate ballistic needs for the new prop.

## Memory LOD

Purpose: non-rendered selections/points for rotations, actions, sounds, and prompts.

Provide:

- Named axis selection for each animated rotation: **door1_axis**, **handle_axis**, **lever_axis** as applicable.
- Axis points/selections referenced by **axis** with **memory = 1**.
- Named sound/action position such as **door1_action**, referenced by **soundPos**.
- Named interaction point at the intended door, button, or lever.

Simple lists door/handle axes, door action/sound position, and interaction point (**Simple_Door Readme.txt:23**). Button moves the interaction/component point to the button (**Door_w_Button Readme.txt:16**). Expert adds lever axis/action points (**Expert tutorial:15**).

The broader **dayz-animation-pipeline** skill describes a rotation axis as a pair of Memory points. Use it for general axis authoring; this skill stays on Doors mapping.

(since 1.30 Exp) If the door is one-sided or takes an inventory lock, also add the Memory names listed in [DayZ 1.30 Exp: Memory points and lock slots](#dayz-130-exp-memory-points-and-lock-slots).

## Pattern matrices

### Simple Door

| LOD | Supplied requirement |
|---|---|
| Resolution | Frame, named **door1**, named **handle**. |
| Geometry | Named **door1**; no handle geometry in this design. |
| View Geometry | Door and handle interaction/occlusion components. |
| Fire Geometry | Relevant components with penetration materials. |
| Memory | **door1_axis**, **handle_axis**, **door1_action**, interaction point. |

Mapping: handle child of door; both animations source **door1** (**assets/Door/Simple_Door.cfg:10-11,29-52**).

### Door with Button

| LOD | Supplied requirement |
|---|---|
| Resolution | Frame, door, handle, button. |
| Geometry | **door1** and button. |
| View Geometry | Button selection **door1_open**; occlusion as needed. |
| Fire Geometry | Named components with penetration RVMATs. |
| Memory | **door1_axis**, **door1_action**, interaction point at button. |

Mapping: only door is a bone; it rotates from source **door1_open** (**assets/Door_w_Button/Door_w_Button.cfg:7-10,27-38**).

### Expert Mode

| LOD | Supplied requirement |
|---|---|
| Resolution | Named **door1**, **handle**, **lever**. |
| Geometry | **door1** and lever. |
| View Geometry | Lever selection **door1_open**; occlusion as needed. |
| Fire Geometry | Named components with penetration RVMATs. |
| Memory | Door/handle/lever axes, action/sound point, interaction point. |

Mapping: handle follows door; lever follows nothing; all source **door1_open** (**assets/Expert_Mode/Expert_Mode.cfg:7-12,29-64**).

## Object Builder validation

Run on Geometry, View Geometry, Fire Geometry:

1. **Structure > Topology > Find Components**.
2. **Structure > Convexity > Find-NonConvexities**.
3. Inspect open/inside-out shapes using **Solid Fill Faces**.
4. Where appropriate, use **Structure > Triangulate Convex**, the tutorial author's preferred repair.
5. Re-run non-convexity checks.
6. Re-check named selections after topology changes.

Menu paths/tips: **Simple_Door Readme.txt:12-14**. The tutorial warns about non-convex and non-closed shapes; no in-game validation was run while creating this skill.

## Pre-export checklist

- [ ] Visible animated parts named in Resolution LOD.
- [ ] Only space-occupying parts in Geometry.
- [ ] Geometry components found and named.
- [ ] Geometry/View/Fire shapes closed and convex.
- [ ] View Geometry contains actual source interaction selection.
- [ ] View Geometry provides intended occlusion.
- [ ] Fire Geometry has appropriate penetration RVMATs.
- [ ] Every rotation has a named Memory axis.
- [ ] Action/sound point matches config **soundPos**.
- [ ] Interaction point is where action should appear.
- [ ] Static button omitted from skeleton; animated lever included.
- [ ] Cross-file names compared character for character.
- [ ] (since 1.30 Exp, lockable building door) Memory includes slot selections matching `CfgSlots` (`att_combinationlock`, `att_codelock`, or the numbered wood/metal variants).
- [ ] (since 1.30 Exp, one-sided door) Memory includes the pair named by `interactPositionPoint` / `interactDirPoint`.
- [ ] (since 1.30 Exp, bunker-style inside bypass) Memory includes `{DoorsSubclass}_action` and `{doorType}_inside` if you copy the `Bunker` pattern.

## DayZ 1.30 Exp: Memory points and lock slots

Tutorial Memory LOD (axes, `soundPos`, interaction) is unchanged. 1.30 adds extra named points consumed by script, not by `class Animations`.

| Role | Config / script name | Memory name(s) verified | Source |
|---|---|---|---|
| Lock attachment proxy | `CfgSlots` `selection` | `att_combinationlock`, `att_codelock` (and numbered `_wood` / `_metal` variants) | `exp/scripts/scripts/config.cpp:2325-2330,2777-2782` |
| One-sided open/close | `interactPositionPoint` + `interactDirPoint` on the Doors child | Whatever strings you put there; empty/missing → `MemPointDirectionalCheck` returns true | `AdditionalDoorsInfo.c:34-38`, `MiscGameplayFunctions.c:911-936` |
| Bunker inside vs outside | `Bunker.CanDoorBeOpened` formats `"%1_action"` and `"%1_inside"` from `doorInfo.m_DoorType` | Example: Doors subclass `Door1` → `Door1_action` and `Door1_inside` | `exp/scripts/scripts/4_World/Entities/Building/Bunker.c:47-54` |
| Code lock facing | `DigitalCodeLock.MEMPOINT_CENTER` / `MEMPOINT_INSIDE` on the **item** P3D | `ce_center`, `inside` | `exp/scripts/scripts/4_World/Entities/ItemBase/CodeLock.c:3-4,221` |
| Combination lock faces | item selections | `lock_attached_outside`, `lock_attached_inside` | `exp/scripts/scripts/4_World/Entities/ItemBase/CombinationLock.c:27-30` |
| Bunker crate spawn | `BroadcastedBunker` | `storagecratepos`, `storagecratedir` | `exp/scripts/scripts/4_World/Entities/Building/Bunker.c:174-176,264-274` |

**[DESIGN]** A custom building that should accept vanilla `CombinationLock` / `DigitalCodeLock` needs the slot selection in Memory (and usually a proxy in Resolution) whose name matches `CfgSlots.selection`. Fence already lists both slots at entity level (`exp/gear_camping/DZ/gear/camping/config.cpp:2683`).

Rebuildable doors: `doorConstructionPhysicsSource` is an **AnimationSource** name, not a Memory point. `Rebuilding` sets its phase to 1.0 on open start and 0.0 on close start (`Rebuilding.c:440-464`).

## Sources

Tutorial ranges read in full context:

- **Simple_Door Readme.txt:6-23**
- **Door_w_Button Readme.txt:6-18**
- **Welcome to novoGODs Expert_Mode Door mod.txt:5-17**
- **WELCOME TO novoGODS Shit Door Tutorial.txt:17-22**

Official LOD reference cited by tutorials, not fetched here:

- https://community.bistudio.com/wiki/LOD

---
name: dayz-doors
description: "Use when working on a DayZ door, animated door, class Doors, doors on buildings, a door with button, a door with lever, hatch/lid animation, model.cfg door, CfgSkeletons door, or diagnosing 'door won't open/animate' on buildings and static props."
---

# DayZ Doors

## Scope

Use this skill for the **class Doors** subsystem on DayZ buildings and static props: doors, hatches, lids, and the buttons or levers that drive them.

Do not use it as a general animation guide. For **AnimationSources**, **SetAnimationPhase**, character or creature animation graphs, vehicle-rider IK, weapons, RTM, ANM, or TXA work, use the **dayz-animation-pipeline** skill.

## Core contract

A door action crosses five name domains:

1. Visible and physical named selections in the P3D LODs.
2. Bones in **CfgSkeletons**.
3. Rotation classes in **CfgModels > class Animations**.
4. Each animation's **source**, normally the View Geometry interaction selection.
5. A **CfgVehicles > HouseNoDestruct child > class Doors** entry whose **component** matches that source.

The moving **selection** and interactive **source** may differ. This is the key to a door controlled by an adjacent button or lever.

Read [door-model-cfg-and-config.md](references/door-model-cfg-and-config.md) before editing model.cfg or config.cpp. Read [lods-and-object-builder.md](references/lods-and-object-builder.md) before editing the P3D. Read [worked-examples.md](references/worked-examples.md) when choosing a pattern. Exact source folders are in **assets/**.

## Workflow

1. **Model the object.** Decide what moves, what follows another bone, where the action appears, and where the sound originates.
2. **Build the LOD contract.** Name visible parts in Resolution LOD; add only space-occupying parts to Geometry; add interaction and occlusion shapes to View Geometry; add penetration-material components to Fire Geometry; add axes, action/sound, and interaction points to Memory.
3. **Write model.cfg.** Give the model a unique skeleton, list (child,parent) pairs, then add one rotation class per animated selection. Reuse a source when several parts move from one action.
4. **Write config.cpp.** Inherit from **HouseNoDestruct**, set **scope** and **model**, map the model source through **class Doors**, then define **DamageSystem**.
5. **Validate names.** Compare exact spelling and case across every LOD, skeleton bone, animation **selection**, **source**, **axis**, Doors **component**, **soundPos**, and DamageZone **componentNames**.
6. **Test in game.** Verify action location, closed/open motion, child motion, sub-ranges, collision, occlusion, penetration, sounds, world-spawn state, and server/client RPT logs.

Follow the debug order: config load -> entity spawn -> action location -> animation -> collision/occlusion -> audio/damage. Do not debug a later layer before the earlier layer is proven.

## Pick a worked pattern

| Need | Pattern | Defining mapping |
|---|---|---|
| Door plus moving handle | Simple Door | Door and handle share source **door1**; handle is a child of **door1** and finishes at phase **0.15**. |
| Door controlled by a static button | Door with Button | Only **door1** is a bone; animation source and Doors component are **door1_open** at the button. |
| Door plus moving handle and lever | Expert Mode | Door, handle, and lever share **door1_open**; handle follows door, lever follows nothing. |

## New door from scratch checklist

- [ ] P3D basename, CfgModels class, model path, and vehicle class are chosen.
- [ ] Skeleton name is unique to this P3D.
- [ ] Every animated selection is a skeleton bone.
- [ ] Every (child,parent) pair matches the intended transform hierarchy.
- [ ] Resolution LOD names every visible component.
- [ ] Geometry/View/Fire shapes are closed and convex.
- [ ] View Geometry contains the intended interaction selection/source.
- [ ] Memory contains each rotation axis, the sound/action point, and the interaction point.
- [ ] Every animation has verified type, selection, source, axis, memory, phase range, and angles.
- [ ] **CfgPatches.requiredAddons[]** includes **"DZ_Data"**.
- [ ] The object inherits from **HouseNoDestruct**.
- [ ] **class Doors** maps each intended source through **component**.
- [ ] Door sound names are verified in **DZ\sounds\hpp\config.cpp**. The 32 complete sound sets, and the nine that lack `Rattle` or `OpenABit`, are enumerated in [door-model-cfg-and-config.md](references/door-model-cfg-and-config.md) — `doorMetalSmall` is not the only option.
- [ ] **DamageSystem** has GlobalHealth, GlobalArmor, and appropriate DamageZones.
- [ ] In-game tests cover action position, motion, sounds, physical LODs, damage, spawn state, and RPT logs.

## Common gotchas

- A button can be the source without being animated or listed in the skeleton.
- A child handle must name the door bone as its parent or it will not follow the door transform.
- Only sources need a normal Doors mapping; animated selections sharing one source do not each need one.
- **DamageZones.componentNames[]** can target moving geometry (**door1**) even when the action source is **door1_open**.
- Use phase sub-ranges to sequence motion: Simple Door handle runs **0..0.15**, then the door runs **0.15..1**.
- **initOpened** is a spawn probability: `rand < initOpened` spawns the door opened (0 = always closed, 0.5 ~= half). Verified vs BI Doors_on_buildings wiki.
- Keep skeleton names unique. The tutorial warns that duplicate skeleton names can crash a server.
- The shipped Expert Mode example has a source-to-Doors anomaly; read its warning before copying it.

## Stop and ask

STOP and ask the user when a source, interaction selection, axis, component, LOD membership, or duplicate **class Doors** mapping cannot be proven from the real P3D/config files. Do not invent a plausible name. Prefix any unresolved technical claim with **?**.

## References

- [Model/config contract](references/door-model-cfg-and-config.md)
- [LODs and Object Builder](references/lods-and-object-builder.md)
- [Verified worked examples](references/worked-examples.md)
- [Official DayZ doors reference](https://community.bistudio.com/wiki/DayZ:Doors_on_buildings)
- [Official DayZ Samples](https://github.com/BohemiaInteractive/DayZ-Samples)
- [Official LOD reference](https://community.bistudio.com/wiki/LOD)

## Vehicle doors are out of scope (added 2026-08-31)

Vehicle doors do **not** use the building `class Doors` contract documented here.

- A detachable car door is a `CarDoor` attachment. `ActionCarDoorsOutside` resolves its target by
  raycast against the **item's ViewGeometry**.
- A door that stays part of the vehicle shell needs vehicle actions around
  `SetDoorOpen`/`IsDoorOpen` plus `model.cfg` `AnimationSources`.

Route vehicle work through `dayz-vehicles`: invariant #21 redirects to the public
`rip-vehicle-import/cookbooks/family-b/radial-puerta-ausente.md` **DOOR MECHANISM SELECTOR**, and
invariant #22 carries the attachment ViewGeometry rule. Applying building `class Doors` to a
vehicle will not produce a working radial, even though both mechanisms use names such as `source`,
`component`, and `axis`.

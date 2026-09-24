# Authority and routing

## Precedence

This skill is an orchestrator. It owns motion intent, realism contracts, quality gates, evidence states and the decision to advance. It does not own the implementation facts of Blender or DayZ.

1. `dayz-animation-pipeline` wins for engine routes, skeletons, graph/state names, formats, FPS/frame budgets, notetracks, export masks, Workbench/DayZATool, ASI/config, build and runtime integration.
2. `blender-animation` wins for live/headless Blender operation, `bpy`, Actions, constraints, interpolation, simulations, previews and the Blender-side export action.
3. A domain skill wins for its own model/character/vehicle/physics contract.
4. This director owns the cross-skill sequence and measurable quality contract.

If two authorities disagree, record both claims with their sources and stop the affected gate. Verify the current source or run the discriminating test. Never select the convenient claim merely because it lets an export proceed.

## Routing table

| Request | Primary route |
|---|---|
| Create, correct or polish realistic motion intended for DayZ | This director + `blender-animation` + `dayz-animation-pipeline` |
| Pure `model.cfg`, `AnimationSources`, ASI, skeleton or registration question | `dayz-animation-pipeline` |
| Generic Blender animation with no DayZ destination | `blender-animation` |
| Retarget external mocap into a DayZ source action | This director + retargeting skill + both authorities |
| Player/custom human asset or rig | Add `dayz-characters` (in 1.30: native surrender, dynamic ASI, stance speed/camera rotation limits) |
| Vehicle occupant/contact choreography | Add `dayz-vehicles` (in 1.30: 4-wheelers + motorcycles `MOTO1`/`MOTO2`, 2-bone handlebar IK, rider lean) |
| Creature locomotion, combat or terrain alignment | Add `dayz-characters` (in 1.30: `.agf` subgraphs, `AnimSrcNodeProcTransform` terrain rotation, unindexed skeletons) |
| P3D hierarchy, selection, proxy or mechanical axis | Add the relevant P3D/model skill |
| In-game verification | Add the current DayZ test/MCP skill and follow its lease/lifecycle rules |

## Non-duplication rules

- Link to current authority content instead of copying values or recipes.
- A task-local motion contract may snapshot the result returned by an authority. Label it with source and date; it is evidence for that animation, not a new universal rule.
- Do not promote one weapon's 291-frame duration, one creature's joint limit or one vehicle's seat offsets into defaults.
- Do not embed absolute local tool paths in reusable contracts. Supply them through CLI arguments or environment variables.
- Keep any unresolved export-mask conflict out of the quality checker. The checker validates the channels the current DayZ contract says should exist.

## Handoff contract

From the DayZ authority, request:

- route and target artifact (in 1.30: modular `.agf` subgraphs under `AnimSrcGraph` `.agr` master index; Enfusion Config syntax for `.asi`);
- authoritative rig/skeleton and bone/channel mask (in 1.30: global bone indices resolved by runtime name hash; 250-bone limit removed);
- timeline and event/notetrack constraints;
- runtime state(s), stance(s), handedness and camera modes (in 1.30: includes `DAYZCAMERA_3RD_VEHICLE_MOTORBIKE = 32`, speed limits per posture, and stance camera horizontal rotation lock);
- compile, wiring, build and deployment path (in 1.30: Workbench Enfusion 2021 Animation Editor with Live Editing, `-resolveFilePatchingUsingEnfusion=1`);
- exact in-game evidence required.

To the Blender authority, provide:

- source scene and immutable baseline;
- beat sheet and golden frames;
- landmarks, contacts, forbidden collision pairs and tolerances;
- channels allowed to change;
- preview and export requirements.

Back to the DayZ authority, provide:

- exported artifact and source scene;
- audit JSON and visual evidence;
- exact included/excluded channels;
- offline status and unresolved gates.

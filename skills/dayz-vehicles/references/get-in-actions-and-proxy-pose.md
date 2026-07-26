# Get-in actions and proxied-submodel pose

This reference isolates three commonly conflated layers: resolving a seat under
the cursor, registering a custom world action, and preserving the authored pose
of a `.p3d` instantiated by proxy.

## Get-in prompt: four ordered gates

[EXACT][CLAIM-R21-VEHICLE-GETIN-CHAIN] `ActionGetInTransport.ActionCondition`
accepts a seat only when all four links pass:

1. The cursor-hit ViewGeometry component maps through
   `Transport.CrewPositionIndex(componentIndex)` to a crew index. A single
   envelope component in front of the seat components can therefore make the
   mapping fail even when the seat cubes themselves are valid.
2. `CrewCanGetThrough(crewIndex)` returns true. The base `Transport`
   implementation returns false outside `CFGMODS_DEFINE_TEST`, so a custom car
   must provide the correct runtime override through its script class.
3. `IsAreaAtDoorFree(crewIndex)` passes its collision-box check around the
   `CrewEntry` transform.
4. At least one action selection passes `CanReachSeatFromDoors`. `CarScript`
   maps `seat_driver`, `seat_codriver`, `seat_cargo1` and `seat_cargo2` to
   `seat_con_1_1`, `seat_con_2_1`, `seat_con_1_2` and `seat_con_2_2`
   respectively, requires that memory point to exist, ignores vertical
   distance and applies a default 1 m horizontal limit.

Inspect and fix them in that order. Rebuilding `seat_con_*` cannot help while
the cursor resolves an envelope component, and script changes cannot help while
the model lacks the final memory point.

Source anchors (DayZ stable `1.29.0.163451`):

- `scripts/4_world/classes/useractionscomponent/actions/interact/actiongetintransport.c:26-80`
- `scripts/3_game/vehicles/transport.c:114-116,493-500,634-676`
- `scripts/4_world/entities/vehicles/carscript.c:2674-2693,2710-2732`

The envelope-component failure was cross-checked in a custom vehicle; vanilla
source establishes the component-to-seat and subsequent condition order.

## Cursor-targeted world action: two registrations, not the entity list

[EXACT][CLAIM-R21-VEHICLE-WORLD-ACTION] A custom `ActionInteractBase` offered
while the player looks at a vehicle needs both:

1. insertion of its typename from a `modded class ActionConstructor` override
   of `RegisterActions(TTypenameArray actions)`, after `super`;
2. addition from the existing `modded class PlayerBase` override of
   `SetActions(out TInputActionMap InputActionMap)`, after `super`.

Adding the action only to the vehicle/entity action list does not make the
player cursor evaluate it. In a measured failure, constructor registration was
present but `ActionCondition` was never called until the PlayerBase map also
registered the action.

Probe one boot with rate-limited log markers at: registration, action
construction, and `ActionCondition` after a successful target cast. Absence at
each marker identifies the dead link without changing the condition blindly.

Source anchors:

- `scripts/4_world/classes/useractionscomponent/actionconstructor.c:27-34,279-285`
- `scripts/4_world/entities/manbase/playerbase.c:1655-1658`

## Multi-LOD submodel instantiated by proxy

[EXACT][CLAIM-R21-VEHICLE-PROXY-AUTOCENTER] In the measured multi-LOD proxy
case, a visual-only submodel with no Geometry LOD was recentered during
binarization: the offset moved into ODOL `model_info.bounding_center` while the
shell proxy matrix remained authored, so the rendered part shifted.

The robust authoring gate is:

- add a Geometry LOD to the submodel, even an empty one;
- set its named property `autocenter=0`;
- after binarize, read the deployed ODOL and require
  `model_info.bounding_center == (0,0,0)` within the chosen numeric tolerance;
- compare the submodel MLOD/ODOL centroid and shell proxy transform against the
  expected world pose.

Treat a non-zero deployed bounding center as pose risk, not as proof of the
exact visual displacement. The evidence is cross-checked against one custom
vehicle plus working vanilla/community multi-LOD proxy controls; it is not a
claim that every single-LOD engine proxy follows the same path.

## Two caveats from the measured case (restored 2026-07-26)

- only ONE `modded class PlayerBase` per mod — put SetActions inside the existing one.
- prompt shown + hand animation playing + server state flipping (`[LFHELI-DBG] door open=true`) with NO visible door motion = the SCRIPT chain is fine; suspect the baked-anim side (selection content in the binarized ODOL, skeleton bone, axis) — the script/anim boundary is exactly SetAnimationPhase.

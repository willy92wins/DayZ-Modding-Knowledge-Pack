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

## The 1 m limit is a signature default, not what the caller passes (added 2026-09-07)

Gate 4 above says `CanReachSeatFromDoors` "applies a default 1 m horizontal limit". That number
is the **default in the signature** (`carscript.c:2710`), and it is not evidence about what runs:
**no vanilla script calls that method**. The engine invokes it natively, so neither `pDistance`
nor `pFromPos` are observable from script.

Measured cost of taking it at face value (LFQuad2, 2026-09-07): a quad whose
`GetDoorConditionPointFromSelection` returned the approach points `pos_driver`/`pos_codriver`
instead of centred ones was "corrected" to return the centred crew points. The change had three
true supports — two vanilla vehicles return centred points (`van_01.c:257`,
`offroadhatchback.c:358`), the sibling mod does the same, and the offline arithmetic gave 0.85 m
and 0.83 m against the 1 m limit. In game it broke two things at once: the driver entering from
the right ended up yawed 15-20 degrees, and the codriver became unreachable from **both** sides.
Reverted.

Before changing which memory point this method returns, **instrument it**: a logging override
that prints `pSeatSelection`, `pFromPos` and `pDistance` on every call costs one cycle and
settles what the engine actually passes. If it cannot be instrumented, the change is a bet:
ship it **alone**, never bundled with other changes, so the outcome is attributable.

## The occupant's pose comes from the ViewGeometry crew proxy, not the Memory point (added 2026-09-07)

Moving `crewdriver` in the **Memory LOD** does not move the occupant. Measured on LFQuad2 across
two runs differing only in that point (40 mm forward), with a probe printing player bone
positions in the vehicle frame:

    PEL   dX  -4.0   dY  -0.7   dZ  +1.4 mm      (143 and 1293 settled samples)
    LH    dX  +2.9   dY  +0.4   dZ  -0.9 mm
    RH    dX  -4.8   dY  +0.6   dZ  +3.3 mm

Nothing, and inside the noise (sd 0.05-0.08). The pelvis stayed at Z +0.2928 while the
ViewGeometry `crewdriver` proxy sat at +0.2948: 2 mm apart. Seventy millimetres of seat edits
applied before this was known moved the rider by nothing at all, across two review rounds.

**The anchors live in THREE places and must move together:**

    Memory LOD     crewdriver / crewcodriver                                   1 point
    ViewGeometry   crewdriver + proxy:\dz\vehicles\wheeled\proxies\crew_driver.001   3 points
    Geometry       only the proxy:\... name, NOT the crewdriver alias                3 points

Two traps when editing them. The two ViewGeometry names **share the same Point objects**, so a
script that iterates both selections shifts them twice unless it deduplicates by identity. And
the Geometry LOD carries only the `proxy:\...` names, so a verifier that looks up `crewdriver`
there raises `KeyError` instead of reporting a difference.

**Cheap offline check that catches a half-moved anchor**: the Memory-to-ViewGeometry offset must
match what the model shipped with, and in a healthy model it is **the same for every crew
position** — LFQuad measures 0.0 / 100.7 / 200.3 mm for driver and codriver alike. Two seats with
different offsets mean somebody moved one copy and not the others. On LFQuad2 that showed up as
18.9 mm of X disagreement on the codriver after a centring edit, and the user reported it as the
camera jumping for an instant on mounting: the engine seats you with one anchor and corrects to
the other.

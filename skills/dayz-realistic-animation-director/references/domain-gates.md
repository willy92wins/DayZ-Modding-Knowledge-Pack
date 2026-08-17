# Domain gates

Use only the sections relevant to the task, in addition to the common contract and the current `dayz-animation-pipeline` route.

## Player or humanoid action

- Verify the allowed body layer/export mask before authoring.
- Track centre-of-mass implication, shoulder/clavicle contribution and counter-motion.
- Preserve locomotion/root channels that the runtime layer owns.
- Test stance and camera variants that can change IK/blending.
- Review transitions into and out of the action, not only its central pose.

## Hand with weapon or object

- Apply every rule in `biomechanics-and-contact.md`.
- Identify the functional moving assembly before posing.
- Define jammed/closed/open or equivalent mechanical states from verified geometry/data.
- Keep contact lock until the declared release; after release enforce clearance.
- Validate regrip as approach → open hand → enclose target → close, rather than teleporting a closed fist.
- Compare start/end against the real runtime IK pose.

## Locomotion

- Define gait, stride, cadence, stance and root-motion ownership.
- Check foot locking, ground penetration, slip distance and support transitions.
- Track pelvis/COM arcs and upper-body counter-rotation.
- Match cycle pose and velocity at the seam.
- Test slopes/turning only if the DayZ graph or runtime consumer will exercise them.

## Creature

- Obtain the actual skeleton, rest pose and gait reference for that species/rig.
- Define contact sequence and support polygon per gait.
- Audit spine/tail/head phase relationships and foot sliding.
- Do not reuse human joint caps or timing tables.
- Verify how the creature graph blends navigation, terrain alignment, attack and hit states.

## Vehicle occupant

- Source seat, grip, pedal/footrest and steering anchors from actual model data.
- Keep hands/feet locked to moving controls through their travel.
- Audit elbow/knee solutions at steering extremes and animation transitions.
- Validate get-in/out approach side and clearance separately from the seated loop.
- Delegate anchor extraction and vehicle runtime behavior to their domain skills.

## Mechanical object or prop

- Identify selection/hierarchy, pivot/axis, limits and all attached sub-pieces.
- Use physically plausible acceleration, hard-stop, overshoot and damping for the mechanism.
- Check travel envelope and object-object collisions.
- Confirm whether DayZ drives it through `model.cfg`, script, weapon bones or skeletal animation; this decision belongs to `dayz-animation-pipeline`.

## Physics simulation

- Use `blender-animation` for simulation setup and bake discipline.
- Bake once before sampling; repeated unbaked evaluation is not deterministic evidence.
- Validate contacts and energy/settling after bake.
- Confirm the export route can carry the baked result into DayZ; do not assume Blender-only deformation survives.

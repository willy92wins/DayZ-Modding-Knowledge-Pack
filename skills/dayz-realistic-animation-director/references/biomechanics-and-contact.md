# Biomechanics and contact

## Whole-chain rule

A believable endpoint can hide an impossible chain. Sample every load-bearing joint and segment from the contact point back to the body. For a left-hand weapon interaction this normally includes all five digits, wrist, forearm/twist chain, elbow, upper arm, shoulder and clavicle/spine contribution allowed by the DayZ export mask.

Treat joint-limit tables as calibration aids, not universal truths. Rig rest axes, species, stylisation and retargeting change the numerical representation. A hard limit needs a reference or measured rig convention.

## Fingers

- Check MCP/PIP/DIP/tip positions, not only the fingertip.
- Build a per-frame hand-width axis from stable roots; a fixed world axis becomes wrong when the wrist rotates.
- Check ordered projection at multiple joint levels.
- Represent each phalanx with a capsule sized from the visible mesh or approved hand reference.
- Check explicit adjacent pairs: thumb-index, index-middle, middle-ring and ring-pinky.
- A finger may curl, but it must remain in its intended flexion plane unless abduction is explicitly authored.
- Never fix lateral crossing by forcing PIP/DIP twist. Correct the responsible metacarpal/MCP orientation and re-evaluate the complete chain.
- Review a close-up from palm, dorsal and end-on views; a full-body render cannot resolve distal phalanges.

## Wrist and arm

- Judge wrist flexion/extension, radial/ulnar deviation and twist separately when the rig permits it.
- Reject a wrist that reaches the target by compensating with overextension.
- Solve shoulder/clavicle placement before hiding reach error in the wrist.
- Audit elbow pole stability and shoulder continuity through the complete transition; three-frame position spikes are stutter even when key poses look correct.
- Preserve the runtime start/end pose supplied by the DayZ contract instead of eyeballing a close approximation.

## Positive contact

Every intended contact declares:

- actor and target landmarks/surfaces;
- `contact_on`, rigid/slip phases and `release`;
- allowed surface distance/penetration band;
- permitted target surface;
- relative-lock tolerances;
- release clearance path.

No collision and positive contact are separate checks. A hand 20 mm away can pass a collision audit while visibly missing the handle.

For a fist around a handle, define the cavity/heel surface—not the wrist origin or an arbitrary fingertip. If the landmark is derived from bones, subtract the measured flesh/capsule radius when calculating surface distance.

## Relative lock and sliding

During rigid contact, compare `T_actor^-1 * T_target` every sampled frame. This catches hierarchy, constraint and coordinate-frame errors that identical scalar curves miss.

For authored sliding:

- split the contact window;
- define the permitted translation axis and range;
- keep forbidden axes and rotation locked;
- start a new rigid baseline when the slide ends.

At release, stop enforcing lock and begin enforcing clearance. The hand should create space before crossing receiver/weapon geometry.

## Collision

- Separate allowed contact pairs from forbidden intersections.
- Sample the complete path; fast motion can tunnel between keyframes.
- Use adaptive subframes or denser sampling around fast transitions.
- For hands, include finger-finger, finger-weapon, palm-weapon and wrist/forearm-weapon pairs.
- For mechanisms, check the complete moving assembly and its travel envelope.

## Visual override

Numeric proxies approximate skin, clothing and perceived weight. If a clear multi-angle render or in-game capture shows overlap, miss, float or overextension, mark the gate failed even if the proxy says PASS. Preserve the case and improve the proxy before the next candidate.

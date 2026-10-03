# Player skeleton — bone catalog (sprint 2026-05-28)

Map of the DayZ player skeleton organized by zone. Use this to map Blender armatures → `OFP2_ManSkeleton`-compatible bones for `.txa`/`.anm`/`.rtm` authoring. Source: `DZ/anims/cfg/skeletons.anim.xml` (production skeleton + `player_testing.xob` for extra helpers).

**Critical rule, repeated from `skeletal-anm-enfusion.md`**: bone names must match exactly. A mismatch logs `Error: Bone X doesn't exist in skeleton OFP2_ManSkeleton` and that bone silently does not animate.

## Core / spine

- `Scene_Root` — outermost transform
- `EntityPosition` — engine-driven entity displacement bone (`movement="true"` in XML). Cross-ref `anim-graph.md` for the AI/graph side.
- `Pelvis`
- `Spine`, `Spine1`, `Spine2`, `Spine3`
- `Neck`, `Neck1`
- `Head`
- `LookAt` — head/look tracking target (not `Pin Look At`)

## Legs (symmetric L/R)

- `LeftUpLeg`, `LeftUpLegRoll`, `LeftKneeExtra`
- `LeftLeg`, `LeftLegRoll`
- `LeftFoot`, `LeftToeBase`
- + `Right*` mirror set
- Hip helpers: `LeftHipExtra`, `RightHipExtra`, `LeftHip_Helper`, `RightHip_Helper`

## Arms (symmetric L/R)

- `LeftShoulder`
- `LeftArm`, `LeftArmRoll`
- `LeftForeArm`, `LeftForeArmRoll`
- `LeftHand`
- + `Right*` mirror set (+ `RightArmExtra`)
- Hand-area helpers: `LeftHand_Dummy`, `LeftWristExtra`, `LeftForeArmExtra`, `LeftElbowExtra`, `LeftArmExtra` (+ `Right*` mirrors)

### Hands hang off the TWIST bones, not the forearm (SP-039)

The parent of `RightHand`/`LeftHand` is **`RightForeArmRoll`/`LeftForeArmRoll`** (twist/roll bone), NOT
`RightForeArm`/`LeftForeArm` (chain: ForeArm → ForeArmRoll → Hand → fingers). When fixing the wrist's
WORLD orientation via a LOCAL quat in a tool, divide by the REAL parent (`bone.parent`), not by `*ForeArm`:
skipping the roll bone leaks its rotation into the wrist and drops the fingers up to ~11 cm (the trigger
finger leaves the trigger). Bit the WeaponAnimPipeline viewer for 2 sessions, misdiagnosed as "mirrored
quat" — the fix was found by RENDERING the in-game bone positions as overlay points, not by theorizing
about quat conventions. Cross-ref `weapon-in-hands.md` §"READ it off the live skeleton".

### Twist bones sit at EVERY joint, and the parent table is measurable (added 2026-09-07)

SP-039 above covers the wrist only. The production rig has a roll bone inside every limb joint,
so any forward kinematics that walks `Arm -> ForeArm` or `UpLeg -> Leg` skips a bone and leaks
its rotation, exactly like skipping `ForeArmRoll` did:

```
Arm   -> ArmRoll   -> ForeArm -> ForeArmRoll -> Hand
UpLeg -> UpLegRoll -> Leg     -> LegRoll     -> Foot
```

Three more facts that a guessed hierarchy gets wrong (measured 2026-09-07 while fitting the
rider of a quad; 5 of 77 guessed parents were wrong, the worst put `Pelvis` under
`EntityPosition` and would have lifted the pelvis 0.95 m): **`Pelvis` hangs off `Scene_Root`**,
and `EntityPosition` (the movement bone) is its SIBLING, not its parent; `*ElbowExtra` hangs
off `*ArmRoll`; `*HipExtra` hangs off `Pelvis`.

Where the table comes from, because the obvious sources do not carry it: `DZ/anims/cfg/
skeletons.anim.xml` has **no `parent` attribute at all** (0 occurrences in 38,078 B; only
`index` and `lod`) although it names its source `hermit_newbindpose.xob`, and a SEAnim written
by DayZATool `--extract-anim` carries names and keys but no parents either. The bind pose model
does: `DayZATool.exe --extract-mdl DZ\characters\bodies\player_testing.xob` writes
`player_testing.semodel` (16,659 B, 148 bones, one root). SEModel header as read from the bytes:
`magic[7]="SEModel"`, `version` uint16 at 7, `headerSize` uint16 at 9 (=20), presence flags at
11..13, `boneCount` uint32 at 14 (=148), `meshCount` at 18, `matCount` at 22, 3 reserved, names
from offset 29 (`b.find(b"Scene_Root") == 29`); bone records are 73 B each with the parent index
as int32 right after one flags byte. The control that makes that read trustworthy: 73 is the
ONLY stride that yields in-range parents AND exactly one root. The full 148-bone table is
`references/ofp2-manskeleton-parents.txt` (measured by the LFQuad2 session with a bounded parser;
recipe and the roll-bone warning are in its header). DayZATool runs headless from a shell but
throws `InvalidOperationException` on `Console.ReadKey` when stdin is redirected — AFTER writing
the output file; ignore the exception and check the file exists.

### `RightHand_Dummy` / `LeftHand_Dummy` — what they are

- `RightHand_Dummy` is at `skeletons.anim.xml:100,115,525` (lod=2 helper). Distinct from `RightHand` (lod=1, the real hand bone).
- It's the helper that anchors weapons/items in the hand. Moving `RightHand_Dummy` moves the held item.
- Measured in game (DayZ 1.30.164014 Exp): the in-hand item sits on `RightHand_Dummy` within ~4 mm, and at rest the hands fall exactly on the IK pose. Two consequences. (1) The right grip is RIGID: if the animation rotates the right hand relative to the item, the item rotates with it and the other hand slips out of its grip — put any slack (a handle pivoting in the fist) on the LEFT hand. (2) `GetTransform` of the in-hand item is a trap: `mat[1]` is the dummy's Z, `mat[2]` its Y, and `mat[0]` points opposite to the model's +X as drawn — do not place item parts with that X. [EXACT]
- Tutorials call it "right hand dummy" (lowercase, with space) — **the real string is `RightHand_Dummy`** (PascalCase, underscore).
- `LeftHand_Dummy` (`skeletons.anim.xml:74`) is the symmetric helper. It's what the engine uses to track magazine position during reload — there are no dedicated magazine bones in the production skeleton (see §Legacy below).

## Fingers (lod 2)

Per hand: `[Left/Right]Hand[Ring/Pinky/Middle/Index/Thumb]1..4`. Lod 2, so only visible at close range; safe to ignore for first-pass weapon authoring, required for hand-pose detail work.

## IK helpers — critical for weapon authoring

- `RightHandOrigin`, `LeftHandOrigin` — IK origins.
- `LeftHandIKTarget`, `LeftHandIK`, `RightHandIK` — IK chain endpoints.
- `LeftForeArmDirection`, `RightForeArmDirection` (+ Origin variants) — forearm twist control.

These are what make the support-hand-on-foregrip pose work without ugly wrist twisting. When authoring a weapon `.anm`, you pose the IK helpers, not the raw forearm bones.

**[VERIFIED 2026-06-17] Position ≠ orientation — the IK helpers do NOT roll the wrist.** The IK helpers (`LeftHandIKTarget`/`LeftHandOrigin`/`LeftHand_Dummy`) POSITION the support hand, but rotating them does **not** change the hand/wrist ORIENTATION in-game — an in-game probe that rotated them 40° produced zero visible change. To change the support-hand grip orientation (e.g. horizontal handguard → vertical foregrip), vanilla rotates the **raw `LeftHand` (wrist) bone + the finger bones** (`LeftHand{Thumb,Index,Middle,Ring,Pinky}*`). Proof: diff the two vanilla OTS-14 ikposes for the same weapon — `ots14_normal` (handguard) vs `ots14_barrelhandle` (forward grip): `LeftHand` rotates 24.8°, fingers 20–55°, the IK helpers are absent/0°, positions 0 (pure rotation). **Reusable technique:** diffing two vanilla ikposes of the SAME weapon with DIFFERENT grips (extract both `.anm` via DayZATool → SEAnim → per-bone delta) reveals exactly which bones control the grip. **Caveat:** an extracted ikpose may not contain `LeftHand` at all — `aks74u.anm` keys the IK helpers, not `LeftHand` — so to author a wrist roll, base off an ikpose that HAS `LeftHand` (e.g. an OTS-14 pose). Origin: A6_SR2M vertical-grip authoring.

### The frame an ikpose keys its helpers in, and the axes of its SEAnim (added 2026-10-03)

[EXACT][CLAIM-ANIM-IKPOSE-OBJECT-FRAME] An ikpose keys `LeftHandIKTarget` in the held object's frame, the frame of `RightHand_Dummy`, whose key `(R, t)` (quaternion XYZW) takes the object to the hand. Measured offline on five vanilla two-handed ikposes, each extracted with DayZATool 1.3 (`--extract-anim <anm> 100`; 43 bones, one pose): the right wrist expressed in the object's frame, `p = -Rᵀt`, mirrors `LeftHandIKTarget` across the grip axis in the four symmetric grips (cm, SEAnim axes):

| ikpose | right wrist, `-Rᵀt` | `LeftHandIKTarget` | mirrored on | worst axis off |
|---|---|---|---|---|
| `ik/two_handed/cookingpot.anm` | (−9.1, +14.2, +1.5) | (−8.6, −15.7, +1.1) | Y | 1.5 |
| `ik/two_handed/cauldron.anm` | (−9.0, +12.5, +5.4) | (−8.5, −12.9, +4.9) | Y | 0.5 |
| `ik/vehicles/batterytruck.anm` | (+29.4, +7.7, +6.1) | (−28.0, +8.0, +9.1) | X | 3.0 |
| `ik/vehicles/radiator_car.anm` | (−30.9, −10.0, +17.6) | (+29.4, −7.7, +24.9) | X | 7.3 |

`ik/two_handed/batterycar.anm` holds its battery off-centre and mirrors nothing: (+16.2, −8.7, −0.5) against (−2.3, +19.5, +3.2). The truck battery and the radiator settle the quaternion convention: read as `-Rt` instead, their mirrors are 37 and 46 cm off. The pot's and cauldron's keys are close to a half turn, so there both readings agree within 2.3 cm and decide nothing.

- `RightHandOrigin` mirrors nothing in the five, and its frame is not known. In game (CocaLab, 2026-09-27, DayZDiag 1.29) an own ikpose that counter-rotated it along with the object broke the right arm: do not treat it as the object's frame.
- `LeftHandOrigin` equals `LeftHandIKTarget` in the pot's ikpose and sits 4 to 12 cm from it in the other four. Its frame was not tested on its own.
- These three helpers are not bones of the bind-pose model: `skeletons.anim.xml:149-151` declares them, and the parent table of `player_testing.xob` (`ofp2-manskeleton-parents.txt`, 148 bones) has none of them. It has `RightHandIK` and `LeftHandIK`, both under `RightHand_Dummy`. No table gives the three helpers' frame; the mirror above is the evidence.

**Axes.** In the object's frame SEAnim X is the model's X, SEAnim Y the model's Z (depth) and SEAnim Z the model's Y (up); the signs are not fixed. The truck battery's wrists sit at +29.4 and −28.0 cm on SEAnim X, just past the ends of its LOD0 (X ±26.0 cm, 24.0 cm tall, Z −11.1 to +12.0). The pot's sit at +14.2 and −15.7 cm on SEAnim Y, which cannot be the pot's vertical: its LOD0 is 25.6 × 24.2 × 26.5 cm with the base at the origin, so one wrist would sit 14 cm up its side and the other 16 cm under its base. `GetTransform` of an item in hand shows the same swap in game (`RightHand_Dummy` section above). In game (CocaLab, 2026-09-27), turning `RightHand_Dummy` 90° about SEAnim Y (`q·qy(90)`) tipped a tray over its long axis. Turning an object about its own vertical inside an ikpose is therefore a turn about SEAnim Z: inferred, not tried in game. When only the direction a held object points is wrong, turn the model instead (`item-ik-and-hide.md` §Turn the model, not the ikpose).

## Weapon attachment / interaction bones

- `Weapon_Root` — main anchor for the weapon (where the weapon's own `Weapon_Root` proxy attaches).
- `Weapon_Bullet`, `Weapon_Trigger`, `Weapon_Magazine`, `Weapon_Bolt` — weapon sub-parts the player skeleton can drive.
- `Weapon_Bone_01`..`Weapon_Bone_06` — configurable slots (for attachments / scope / muzzle device).
- `Weapon_Holster`, `Pistol_Holster`, `Weapon2hnd_Holster` — holstered weapon attachment points.
- `weapon` (lowercase) — legacy compatibility name.

## Face (lod 2)

- `Face_Hub`, `Face_Jawbone`, `Face_Chin`, `Face_Eyelids`, `Face_Forehead`
- `Face_Brow*`, `Face_Lip*`, `Face_Cheek*`, `Face_Tongue`
- `EyeLeft`, `EyeRight`

Lod 2 — mostly relevant for character mods and cutscenes, not gameplay animations.

## Misc / system

- `Opponent` — engine-driven, references the entity being interacted with (combat target, character being grabbed).
- `Camera3rd_Helper`, `Camera1st_lock_dummy` — camera anchors.
- `Marker` — generic marker helper.

## Legacy / to-be-removed [DO NOT USE]

These bones appear in `player_testing.xob` (test skeleton) marked literally `<!--To Be removed-->` (`skeletons.anim.xml:296-300`). They are not part of the production skeleton:

- `Bullet`, `Trigger`, `Magazine`, `Bolt`
- `Bullets_Magazine`, `Bullets_holder`, `Bullets_on_holder`
- `Universal1`, `Universal2`

If a tutorial or older guide references any of these as standard, treat the guide as stale.

## Mapping from this to Blender authoring

Workflow when bringing the skeleton into Blender to author a new `.txa` or `.anm`:

1. Extract `skeletons.anim.xml` from your vanilla unpack (or get the official rig from `BohemiaInteractive/DayZ-Misc`).
2. Build the armature in Blender with bone names matching this catalog exactly — PascalCase, underscores preserved.
3. For weapon authoring, weight the IK helpers and `RightHand_Dummy` properly so they drive what the engine expects; pose them in keyframes rather than the raw hand bones.
4. Verify on round-trip: export → re-read with `seanim_writer.py` or the SEAnim Blender plugin → confirm bone count and names match. RPT will tell you on first in-game test if anything is misnamed.

## Cross-references

- `references/anim-graph.md` — how these bones are referenced from state machines, ASIs, commands.
- `references/skeletal-anm-enfusion.md` — the `.anm` route from authoring to runtime.
- `references/blender-authoring.md` — bone-name discipline + headless Blender export pattern.

## DayZ 1.30 Exp: Bone Indexing & skeletons.anim.xml Deprecation [EXACT]

In DayZ 1.30 Exp (build 1.30.164014), the global skeleton architecture underwent fundamental changes:

1. **Removal of the 250 Bone Limit [CHANGELOG]**:
   The engine no longer enforces the legacy 250 global bone limit (`changelog:31`).
2. **Bone Index Resolution by String Hash [EXACT]**:
   Global bone indices are no longer sequential integers defined in `skeletons.anim.xml`. The engine derives the runtime bone index by hashing the bone name directly.
3. **Deprecation of `skeletons.anim.xml` Indices [EXACT]**:
   In `exp\anims_cfg\DZ\anims\cfg\skeletons.anim.xml`, all `index` attributes have been stripped across all human and animal skeletons, except for `EntityPosition`:
   ```xml
   <!-- [EXACT] exp\anims_cfg\DZ\anims\cfg\skeletons.anim.xml:986-989 -->
   	<skeleton name="ovis_gmelini_skeleton.xob">
   		<bone name="Scene_Root"/>
   		<bone name="EntityPosition"	index = "0" movement = "true" lod = "0" />
   		<bone name="Pelvis"/>
   ```
   `skeletons.anim.xml` is now primarily used for declaring Level-of-Detail (`lod="N"`) and auxiliary bones missing from the base `.xob`.

### Physical Ragdoll Bones in `human.ragdoll` [EXACT]

DayZ 1.30 Exp introduces data-driven ragdoll physics defined in `DZ/characters/bodies/human.ragdoll` (`exp\characters_bodies\DZ\characters\bodies\human.ragdoll:1-25`, 202 lines). The physical character model comprises 11 articulated rigid body bones, totaling 73.8 kg with collision capsules/spheres assigned to `"DZ/data/data/penetration/flesh.bisurf"`:

| Ragdoll Bone | Parent Bone | Mass (kg) | Collision Geometry | Joint Limits (Pitch / Roll / Yaw) | Stiffness / Damper |
|---|---|---|---|---|---|
| `pelvis` | *(Root)* | 17.0 | `Spine1` (capsule r=0.1, h=0.2), `Spine2` (capsule r=0.1, h=0.1) | N/A (Root) | N/A |
| `spine3` | `pelvis` | 15.0 | `Spine3` (capsule r=0.12, h=0.1) | Min `[-15, -20, -35]`, Max `[15, 20, 5]` | 0.8 / 0.4 |
| `head` | `spine3` | 6.1 | `Head` (sphere r=0.1) | Min `[-70, -35, -40]`, Max `[70, 35, 45]` | 0.8 / 0.3 |
| `leftarm` | `spine3` | 2.1 | `LeftArm` (capsule r=0.04, h=0.25) | Min `[-15, -45, -45]`, Max `[15, 130, 45]` | Default |
| `leftforearm` | `leftarm` | 1.7 | `LeftForeArm` (capsule r=0.04, h=0.2) | Min `[0, -45, -45]`, Max unconstrained | Default |
| `rightarm` | `spine3` | 2.1 | `RightArm` (capsule r=0.04, h=0.25) | Min `[-15, -45, -45]`, Max `[15, 130, 45]` | Default |
| `rightforearm` | `rightarm` | 1.7 | `RightForeArm` (capsule r=0.04, h=0.2) | Min `[0, -45, -45]`, Max unconstrained | Default |
| `leftupleg` | `pelvis` | 7.5 | `LeftUpLeg` (capsule r=0.05, h=0.425) | Min `[-5, -10, -120]`, Max `[5, 60, 70]` | - / 0.3 |
| `leftleg` | `leftupleg` | 6.6 | `LeftLeg` (capsule r=0.04, h=0.4), `LeftFoot` (capsule r=0.03, h=0.175) | Min `[-5, -2, -5]`, Max `[5, 2, 120]` | - / 0.3 |
| `rightupleg` | `pelvis` | 7.5 | `RightUpLeg` (capsule r=0.05, h=0.425) | Min `[-5, -10, -120]`, Max `[5, 60, 70]` | - / 0.3 |
| `rightleg` | `rightupleg` | 6.6 | `RightLeg` (capsule r=0.04, h=0.4), `RightFoot` (capsule r=0.03, h=0.175) | Min `[-5, -2, -5]`, Max `[5, 2, 120]` | - / 0.3 |

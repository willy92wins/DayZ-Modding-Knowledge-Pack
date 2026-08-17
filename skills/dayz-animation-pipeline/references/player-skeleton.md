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

### `RightHand_Dummy` / `LeftHand_Dummy` — what they are

- `RightHand_Dummy` is at `skeletons.anim.xml:100,115,525` (lod=2 helper). Distinct from `RightHand` (lod=1, the real hand bone).
- It's the helper that anchors weapons/items in the hand. Moving `RightHand_Dummy` moves the held item.
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

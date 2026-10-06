# Changelog

All notable changes to the DayZ Modding Knowledge Pack are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- `dayz-texture-pipeline` `scripts/normal_convention.py`: proposes whether a normal map is
  OpenGL (Y+) or DirectX (Y-) from two independent readings, and only when they agree; the
  candidate is confirmed another way before a channel is inverted. The albedo reading: the albedo's dark grooves mark the hollows; across a hollow
  d(nx)/dx and d(ny)/dy share their sign in DirectX and oppose it in OpenGL, and the red channel
  calibrates the sign. The curl reading needs no albedo: a height field's slopes have no curl
  under one convention only. Exit 0 with a verdict, 2 `INCONCLUSIVE`, 1 bad input; `--json`
  writes null for undefined numbers. The albedo reading is contributed from LFPowerGrid_dev
  `assets/heater/normal_convencion.py` (commit `a4c6e29`, the Pack owner's; pipeline ticket
  `fb-20260921-164248-a140`) and returns its numbers exactly on the heater maps (red −0.1296,
  green −0.0851, 491,775 pixels); a non-finite correlation is now `INCONCLUSIVE` (the original
  read NaN as DirectX). The cross-family review found the albedo reading wrong, with strong
  correlations, on a surface that curves one way along x and the other along y, and a missing
  weak-correlation test; the curl reading, the agreement rule and both fixtures followed. Its
  second round built known-DirectX maps both readings call OpenGL (a tangent-space bake on a
  sphere patch, undersampled tileable detail) and a weak-channel mutant the tests missed: the
  output became a candidate to confirm, and one-weak-channel tests followed. Its third round
  found that a raking light parallel to U renders a map and its inverted-green copy alike: the
  docs now say that the light must cross V and the inverted copy must read the known groove as a
  ridge, and that renders that look the same are inconclusive. A product test on vanilla maps
  (2026-10-04) found that an `OpenGL` candidate cannot tell an inverted green from a red inverted
  against the relief; the docs say to check red on a known joint first. The same test found a
  vanilla map whose curl residuals sat half a quantization step apart read OpenGL: the curl
  reading now abstains unless its two medians differ by more than one 8-bit step of the normal
  (2/255), a heuristic floor rather than a bound on rounding noise. A second product test found a flat brick decal and a cloth bag that read OpenGL with
  readings that agree on the whole map but not block by block: a candidate now also has to hold
  across a 6×6 grid of blocks, with at most 1 block in 10 against it for the curl reading and
  1 in 3 for the albedo reading. On 284 vanilla pairs never used to design that check it gave
  157 `DirectX`, 119 `INCONCLUSIVE` and 8 `OpenGL`, all 8 OpenGL-consistent by their own
  features; one design-sample map (`kancel_008_nohq`, DirectX by its glass panes) still reads
  OpenGL with stable blocks. Over the three samples that is 1 wrong candidate in 502, no N1 error
  and about 41 % `INCONCLUSIVE`; the Pack owner accepted that rate on 2026-10-04, and maps that mix
  the two conventions inside every block are documented as a known limit. The review of that
  version found that an inverted-green copy could break a tie only on one side: the normal is now
  decoded as (2c − 255)/255, which negates exactly, so the copy always gives the opposite verdict
  and the same block counts. On the heater both
  readings say DirectX (curl residuals 0.013 against 0.024), not confirmed another way; nothing
  was checked in game. SKILL.md rule 3, `map-conventions.md` and `validation-checklist.md` point at it.
  `tests/test_normal_convention.py` (40 tests) encodes synthetic height fields as DirectX and as
  OpenGL and reads them back; nine mutants of the detector, nine of the floor and twenty-nine of
  the block check, the decoding and the readers' masks each fail it. It skips where numpy
  or Pillow is missing, as on the CI runner. The ticket's second script (`uv_convencion.py`,
  V convention of a validated p3d) is not part of this change.
- `dayz-mcp-verify`: one section ported from the installed copy (added 2026-10-04, written by the
  orchestration session that ran a seed-and-prune strike scenario against an LFPowerGrid PR) and
  corrected in the review of PR #105: "A server HANG is bounded by log tails first" — read both log
  tails of the run and start from the one that carries the markers (in that run the RPT tail ended
  in world-streaming warnings and the markers were in `script*.log`); the interval between the last
  printed stage and the first missing one is a candidate until the source and the run's logs
  confirm the markers' order and obligation, that they belong to the same flow and to this run,
  and that their emission is visible (otherwise instrument the stages' entries and exits; a
  missing stage proves lack of observed progress, not where the server spins); verify the
  candidate region's loop structure in source before suspecting it; and a scenario bisect within
  one revision yields a candidate sub-path, while only a controlled comparison between revisions
  (same scenario, one variable) is evidence of a regression, so the attribution to the newest
  change stays unproven and the merge on hold until that comparison closes.
- `dayz-animation-pipeline` `SKILL.md` adds two measured write-ups from LFSkateboard test R1c
  (DayZDiag 1.30.164014 Exp, 2026-10-06, server and one client on one machine). A paragraph with claim
  `CLAIM-ANIM-VANILLA-GRAPH-INGAME-130` (`runtime_verified`): a ride `HumanCommandScript` on the vanilla
  player graph bound `MovementSpeed`, `MovementDirection` and `LookDirX` with `BindVariableFloat`,
  `Stance` with `BindVariableInt`, `Look` with `BindVariableBool`, `CMD_Jump` and `CMD_Land` with
  `BindCommand` and `TagFall` with `BindTag`; the 12 bind lines of six rides returned the same ids on
  server and owner client, none −1; `PreAnim_CallCommand(CMD_Jump)` took the graph into its jump states
  (`TagFall` seen in both landed flights on each side, and in a flight whose build left the body on the
  ground); and with `MovementSpeed` written every `PreAnimUpdate` (0-3) and the matching
  `GetCurrentMovement()` override, the walk, run and sprint sources played. R1c alone does not separate
  those two inputs; test R1 the night before, with the same override and no `MovementSpeed` write, stayed
  on the idle clip, which points at the write without isolating it. A subsection with claim
  `CLAIM-ANIM-SYNC-EVENTS-130` (`runtime_verified`): a clip that replaces a walk, run or sprint sync
  source needs the four foot events of its line, in the line's cyclic order — without them the whole
  pose froze (the pelvis read the same position on 50 of 53 state lines while rolling, pushing and
  turning at 0.5-6.5 m/s); with them it played. A clip with the events out of order was not tested.
- `dayz-physics-engine` `SKILL.md` adds to its Player CCT section "Lifting the player from a
  `HumanCommandScript` needs the controller's gravity off" (measured in game, DayZDiag 1.30.164014 Exp,
  LFSkateboard test R1c, 2026-10-06), claim `CLAIM-PHYS-SCRIPTCMD-GRAVITY-130` (`runtime_verified`). A
  ride command integrated its own ollie (vy 2.69 m/s at take-off) and passed `dy` as the y of
  `PrePhys_SetTranslation`, which is local space, with a `PostPhys_SetPosition` pin past 3 cm of error.
  With gravity on, the default, the body did not rise: the first air tick ended 0.088 m under the
  integrated height, and 0.2 s into the flight, pin already on, the server read the body 1 cm under its
  take-off height where the integration asked for about +0.34 m. With
  `Human.PhysicsEnableGravity(false)` from take-off to landing — the only code change — the body
  followed the translation; the server never needed the pin, and the owner client's root peaked at
  0.996 and 1.001 × vy²/2g in the two landed flights. The command switched the gravity back on at the
  landing and in `OnDeactivate`, and after the landing the rider rolled down a slope again. Not
  measured: a remote observer, flights longer than the 0.6 s these lasted, and fall damage after a
  flight with the gravity off.

### Changed

- `dayz-animation-pipeline` `SKILL.md`: the section heading now reads "Locomotion in scripted commands:
  driving the vanilla graph (added 2026-06-11, measured on 1.30 Exp 2026-10-06)". The 2026-06-11
  paragraph (LFSlidingFloor, `GetCurrentMovement()` override) ends with a dated qualification: on 1.30
  Exp that override alone did not take LFSkateboard's ride command off the idle clip, and writing
  `MovementSpeed` did. The paragraph corrected 2026-10-04 (LFSkateboard), claim
  `CLAIM-ANIM-VANILLA-VAR-BIND-130` (`source_verified`), replaces its closing [DESIGN] sentence: both
  routes are measured in game as of 2026-10-06 — the binds hold on the server and on the owner client,
  `PreAnim_CallCommand(CMD_Jump)` takes the graph into its jump states, and a `MovementSpeed` written
  every `PreAnimUpdate` moves the locomotion — and only the continuous `MovementDirection` blend stays
  [DESIGN]: it was bound and written (the lean × 85), but the test lap leaned only while pushing, so
  there were no rolling samples at full lean and its continuous blend was not isolated.

### Fixed

- `dayz-animation-pipeline` `SKILL.md` discarded two ways to drive the vanilla player graph from a
  `HumanCommandScript` (note of 2026-06-11): `PreAnim_SetFloat/SetInt` because "vanilla graph
  variable IDs are not exposed to script", and `PreAnim_CallCommand` for "0 call-sites in vanilla
  script, graph command IDs undocumented". The ID reasons rest on one false assumption: script gets
  the graph's IDs by name, on `Human.GetAnimInterface()` (`human.c:1420-1421`, DayZ 1.30.164014
  Exp), with `HumanAnimInterface.BindVariableFloat/Int/Bool(string)` (`human.c:313-315`),
  `BindCommand(string)` (`human.c:309-310`) and `BindTag(string)` (`human.c:318`). The vanilla
  `player_main.agr` declares `MovementDirection`, `Stance`, `TurnAmount` and `Lean` and a
  `Commands` block, and SIBNIC's shipped gunner binds `Stance` and forces it with `PreAnim_SetInt`
  in `OnActivate` (`dayz-vehicles` `references/gunner-shoot-from-vehicle.md`); the 0 call-sites
  only mean vanilla shows no example. A dated correction (LFSkateboard session, 2026-10-04)
  follows the original note, which is kept and now opens with a pointer to it, with claim
  `CLAIM-ANIM-VANILLA-VAR-BIND-130` (`source_verified`). Both routes are reopened, not proven:
  whether a value written every `PreAnimUpdate` survives the graph's own update of that variable
  (the `AnimSrcNodeVarUpdate` on `MovementDirection` in the player `Locomotion.agf`), and what a
  vanilla graph command does when `PreAnim_CallCommand` calls it, were not measured in game and
  are marked [DESIGN]. The pointer and the `PreAnim_CallCommand` half came from reviewing PR #106.

## [1.6.0] - 2026-10-04

Collision measured in game on 2 m boxes (DayZDiag 1.29.163709) and carried into the audit and model
skills and py3d: a box with no `ComponentNN` selection in its collision LODs, or left out of every
component beside a covered one, collided with nothing; winding is repaired per convex component or
closed shell, a collision LOD never reversed to match the Visual LOD; py3d 1.9.0, 1.10.0 and the
pinned 1.10.1; new FAIL rules in `dayz-script-validator`; `packctl validate` against merge-conflict
markers and a gate over every skill and tool test folder; collision probes in `dayz-mcp-verify`;
`types.xml` lifetimes in `dayz-persistence`; and `dayz-doors` without its third-party `assets/`.

### Added

- `dayz-persistence`: two sections from the LFPowerGrid mod (SP-459, SP-460; DayZDiag 1.29.163709). A class
  with no `types.xml` entry lives 30 to 60 minutes of server time (claim `CLAIM-PERS-CE-DEFAULT-LIFETIME`):
  `lifeMax` 1800, new entities at 1.03 to 1.98 times that, the lifetime falls with a player 10 m away, survives
  restarts and ignores server downtime, reads 0 in `EEInit` of a restored entity, and restored entities that ran
  out are deleted at startup before any player connects. Adding the entry later (`CLAIM-PERS-CE-ENTRY-LATE`)
  protects new objects only, rescues nothing that ran out, and `types.bin` keeps it after the XML is removed;
  the rule is an entry with an explicit lifetime for every class that persists, checked against `config.cpp`.
  An entry with `nominal` above 0 and without `category`, `usage` or `value` still spawns as loot
  (`CLAIM-PERS-CE-UNTAGGED-LOOT`: 202 placements on a fresh storage). `OnStoreLoad` returning false keeps the
  entity, with its script state at the defaults apart from what the load had assigned
  (`CLAIM-PERS-ONSTORELOAD-FALSE-KEEPS`: three batteries kept their wires and started with their energy at 0);
  the next save is not measured. The description names the symptom: placed objects that vanish after a restart.
- `dayz-pbo-build`: a manual release-package line in the folder-structure checks, an explicit-lifetime
  `types.xml` entry for every class that persists in the world (SP-459).
- `enforce-script-reference` `verified-api-catalog.md`: `ConfigIsExisting` with a trailing space after the class
  name still finds the class (`CLAIM-ENF-CONFIGISEXISTING-TRAILING-SPACE`; positive control only, and vanilla
  writes no space).
- `dayz-animation-pipeline`: the frame a vanilla ikpose keys its helpers in, and what to do when a
  held item points the wrong way (from CocaLab). `player-skeleton.md` (claim
  `CLAIM-ANIM-IKPOSE-OBJECT-FRAME`): `LeftHandIKTarget` is keyed in the held object's frame, the
  frame of `RightHand_Dummy`. Measured offline on five vanilla two-handed ikposes extracted with
  DayZATool 1.3: the right wrist in that frame (`-Rᵀt` of the `RightHand_Dummy` key) mirrors
  `LeftHandIKTarget` in the four symmetric grips, 0.47 to 7.31 cm off on the worst axis, and the
  truck battery and radiator rule out the opposite quaternion reading. `RightHandOrigin`'s frame is
  not known (in game, counter-rotating it with the object broke the right arm) and
  `LeftHandOrigin`'s was not tested; neither is in the bind-pose parent table. In that frame SEAnim
  Z is the object's vertical and SEAnim Y its depth, signs not fixed: read against the LOD0 of the
  vanilla pot and truck battery, and in game a 90-degree turn about SEAnim Y tipped a tray over.
  `item-ik-and-hide.md` (claim `CLAIM-ANIM-ITEM-TURN-MODEL`, confirmed in game 2026-09-27): when a
  vanilla ikpose gives a natural pose and only the item's direction is wrong, turn the model about
  its vertical, origin kept, rather than edit the ikpose; CocaLab's tray, turned 90 degrees, holds
  with the truck battery's ikpose and the pot's animation set. SKILL.md's routing rows name both.
- `dayz-mcp-verify` static-object playbook and tool table: two probes from the killer #2 run
  (2026-10-02, DayZDiag 1.29.163709). `scene_raycast(method="bullet")` queries the server's physics
  world on a fixed layer mask (`DayZPhysics.RayCastBullet`), next to the LOD rays; a hit counts only
  on the target at its face, and a miss alone is not proof. A `player_move` walk into the object
  reads player collision: blocked is `arrived:false` with the player stopped just before the face
  (about 0.36 m on that run's 2 m boxes), free is `arrived:true`, anything else inconclusive, with a
  same-distance open-ground walk as the free reference; a walk-through alone is not read as missing
  collision geometry (a low vanilla `WoodenCrate` took every ray and did not stop the player). For
  test fixtures, `rotation=64` spawned a box with its faces on the world axes where the default
  `rotation=0` (RF_DEFAULT) yawed it about 10 degrees; check the yaw with two parallel rays and the
  tilt with `bullet` normals on two faces that are not parallel before trusting face coordinates.
- `dayz-mcp-verify` static-object playbook: a standing-on-top reading of the physics body, next to
  the walk-into probe, from a later run (2026-10-02, DayZDiag 1.29.163709). A teleported player
  left idle does not fall: after `player_teleport` above a 2 m box's top or above open ground, the
  server kept the teleport height over 3-4 s, and above open ground the client still held it 15 s
  later. A short `player_move(angle_deg=0, speed="walk", hold_s=0.5)` before `query_player_state`
  applies it: above open ground the player dropped to the ground, and on two outward-wound boxes
  and an inward-wound one it stayed at the top's height (godmode on, the DayZ_MCP default). A
  reading counts only from the centre of an isolated top and with the endpoint still inside the
  top's footprint; anything else is inconclusive, and the move is kept short so the player does not
  walk off the top.

- `dayz-animation-pipeline` `scripts/extract_empties.py`, the rig step that writes
  `empties_armworld.json`. `build_rig_dayz.py` read that file, but no script of the skill wrote
  it: the extractor stayed in the `WeaponAnimPipeline_dev` project and printed its JSON between
  markers. A rig rebuilt with `{}` in its place kept its bones and lost every anchor, and
  `build_viewer.py` then put the weapon at a fixed `(0, 1.3, 0.2)` instead of on
  `RightHand_Dummy` `(-0.156, 1.368, 0.207)`. The script composes each helper's world through its
  parent chain and exits 1 without writing when the FBX has no `RightHand_Dummy`; it removes the
  previous run's file before the FBX import, read-only or not, so after a failed run
  `build_rig_dayz.py` stops instead of building on stale anchors (a file it cannot remove stops the
  extractor with that error). On the BI FBX (Blender 5.1.1), `fbx_extract.py`,
  `extract_empties.py` and `build_rig_dayz.py` rebuild the project's `data/rig_dayz.json` byte for
  byte except its `space` label. SKILL.md's scripts index and `weapon-anim-authoring-viewer.md`
  "Reusable tools" list the pipeline in the order it runs, with `--python-exit-code 1` for the
  Blender steps and a stop at the first non-zero exit (without the flag an uncaught Python
  exception exits 0).
  Regression test: `tests/test_extract_empties.py`, which skips itself where numpy is missing, as on
  the CI runner that now runs the skill test folders. Its FBX path placeholder adds it to the pinned
  census of payloads that only run once an operator edits a path (`tests/packctl/test_promotion.py`).
- `packctl validate` fails on git merge-conflict markers. The squash of #52 (`3e22429`) committed
  `<<<<<<< HEAD`, `=======` and `>>>>>>> 4de8b5a…` into this file's Unreleased → Fixed, and
  `validate` passed with 0 findings; the squash of #67 (`f27691e`) removed them. The new
  `conflict_markers` check reads every tracked file git would merge as text (no NUL byte in its
  first 8000 bytes, git's binary test), fenced code blocks included, splits it on line feeds so the
  line numbers are git's, and reports `MERGE-CONFLICT-MARKER` for each marker line: 7 `<`, `>`, `=`
  or `|` from column 0, then a space, a tab or the line end. `<<<<<<<` and `>>>>>>>` lines always
  count. `=======` and `|||||||` lines count only between a `<<<<<<<` line and the next `>>>>>>>`
  line, so the setext underline of a 7-letter heading passes, and a separator left behind once both
  side markers are gone is not reported. Git never indents a marker, so a document that shows one
  indents it. On `3e22429` the check reads 923 of the 932 tracked files (the 9 it skips are binary
  test fixtures) and reports those three lines only; a longer run, such as the 33 `=` at
  `skills/dayz-pbo-build/SKILL.md:337`, is not a marker. Tests in `tests/packctl/test_validation.py`.
- `dayz-mcp-verify`: two sections that a session testing a mod through the MCP wrote into the
  installed copy on 2026-10-03, ported in English without private names; the live copy is
  re-adjudicated in `promotions/adjudications.json`, so the next promotion replaces it with this one.
  "Check which mod a run loaded before reading its verdict": `dayz_test_run` boots the registered
  project its `project` argument names (an unregistered name is rejected with `bad_project`) and
  reports `succeeded` for it, intended or not; one run loaded another registered mod, and the missing
  compile errors of the mod under test were read as a fix, so the run's `-mod=` and `-mission=` are
  read in its RPT first, with `dayz-test-ingame`'s procedure. "`unapproved_debug_image` on a host
  with a non-English culture: check the server's code first": a build on a host with a Spanish
  culture was seen rejected for loading a localized .NET resource satellite; the MCP server's debug
  gate admits those since a fix of 2026-10-01, so the section sends the reader to the code the
  running server was started from and to its stderr log, instead of calling it a standing defect as
  the live text did.
  A third section it had written, a Mission-module lesson about a class holding a `static ref` to
  itself, was retracted by its author as measured on the wrong mod and is not ported; vanilla 1.29
  contradicts it as well (`VicinityItemManager` holds one and its module compiles).
- `dayz-mcp-verify`: the section the installed copy added on 2026-10-04 ("Audit the deployed PBO's
  file index, not just the source tree, before attributing compile failures"), ported in English
  without private names; the live copy is re-adjudicated in `promotions/adjudications.json`, so the
  next promotion replaces it with this one. Ported: the WHAT-is-packed versus WHY-it-failed limit,
  keeping experiments out of the packed tree (narrowed in review: a rebuild packs what is still in the
  tree and, without `-clear`, can pack stale source, so the index is read again after it), and the
  header-plaintext fact with the listing claim corrected (the source's grep form finds the names but
  prints whole newline-delimited chunks of binary, not one name per line, per a measurement on real
  PBOs; the section points at `dayz-aviation`'s index reader and `dayz-test-ingame`'s packed `.c`
  count check instead). Not ported: the lists-every-file reading of that grep (overstated per the
  measurement); the two-boot suspicion and its control outcome (an unnamed session, and the suspected
  construct is ordinary code, see `VicinityItemManager` above); the undescribed edit to the file under
  test; the multi-variable and one-variable-control morals, that static analysis is not a compiler,
  and the list-before-testing prescription, already in the Pack; the session narrative.
- `dayz-mcp-verify` static-object playbook, collision: the ray battery of `dayz-p3d-audit` rule 6 as
  a recipe with its two controls, and why picking an item up is not a collision test (SP-454;
  DayZDiag 1.29.163709, dayz-mcp run 606a5dbb, 2026-10-02). Nine rays per mode in `geom`, `view` and
  `fire`: one down the axis, which on a solid box rules out a LOD recentred by a missing
  `autocenter=0`; four through the middle from the sides and two more heights on one side; two from
  inside, which a sound object answers `entry 0, exit 1` at distance 0. The same battery goes at a
  control from the same PBO and load path and at a vanilla control of the same physics layer
  (`WoodenCrate` for `item_small`), and the winding is named as the cause only by a pair that
  changes the winding alone. The collision bullet no longer asks for rays "from ≥2 angles". Vanilla
  targeting adds a 30°, 3 m cone search, with no hit on the object needed, when the camera looks
  down at −45° or lower, and the target condition of `ActionTakeItemToHands` checks only distance;
  `action_use` builds its target without a ray, and in that run it put in the player's hands a kit
  box that all 27 rays of the battery missed. The item playbook points to the battery, and
  `dayz-p3d-audit` rule 6 to both. PREREQUISITES 4: when the mod under test does not compile, test a
  copy of its PBO without the offending entries, in a probe folder under `P:\Mods` written with the
  owner's OK, hosted by an approved project whose `default_base_mods` carry its dependencies (an
  absolute workshop path in `base_mods` fails with `bad_mod`).
- `dayz-physics-engine` truth #11, a sub-bullet: a Roadway face of another model across a lift's
  travel stops the ride down (SecretRock elevator, DayZDiag 1.29.163709, 2026-10-02/03). The cabin
  carried a player up through its stops, but going down it left them standing at the stop's floor
  height while it went on: the building's interior model had the shaft cut out of its collision
  slabs, not out of its Roadway LOD. With the shaft cut out of that Roadway too, the player rode
  down linked to the cabin. A character stands on Roadway where no Geometry is, and `RaycastRV`
  cannot target Roadway (`ObjIntersect`, `3_game/constants.c:31-38`), so the check is offline: no
  Roadway face of another model in the volume a moving piece's collision sweeps.
- `dayz-persistence`, after Contract 3: build what stored entities rest on inside
  `OnMissionStart` (same mod and build). A helicopter parked on a structure that the mod rebuilt
  from its sidecar 2 s after `OnMissionStart`, with parts 0.5 s after `EEInit`, came back before
  the structure after an orderly restart and fell 6.9 m; with the restore and the parts created
  inside `OnMissionStart` it stayed parked after two orderly restarts. It matches
  `enforce-script-reference` SP-LFS-3 (stored entities are created after `OnMissionStart` returns);
  the rule holds for a structure that needs nothing from the game's storage.
- `enforce-script-reference` Override Rules, rule 42, and a pointer from
  `references/vanilla-deep-dive.md`: a recipe's `CanDo` copies `ingredients[0]` and `[1]` to locals
  first and does not call `super.CanDo` (CocaLab, DayZDiag 1.29, 2026-09-27). With
  `super.CanDo(ingredients, player)` called first, the server's `CanDo` returned false while every
  part of its condition read true, and `ActionWorldCraft` cancelled the craft as it started; a probe
  that read the array after its `super` call found the tray in both slots. Copying to locals
  without `super` fixed it in game (the same commit also split the final `return` into a null
  guard, so which change mattered was not isolated). Vanilla: 1 of 206 `CanDo` overrides calls
  `super` (`craftlongtorch.c:61`, as its only statement). The mechanism is not established.
- `dayz-persistence` Hard stops item 9 and its section, and `rigorous-data-audit`
  `references/entry-point-audit.md`: an entry of a mod's own registry of world entities leaves by
  its id, never by proximity (SP-456, from a code audit of the SecretRock mod, 2026-10-03). An
  unregister that fell back to the nearest entry of the same class within 0.75 m deleted a
  neighbour's entry whenever an entity without an id was deleted: a placement refused after the
  entity was created, or an admin's console spawn. The rule: an unregister needs a matching id, and
  an entity without one never touches the file; in game (DayZDiag 1.29), with that rule, a console
  entity 0.3 m (horizontally) from a registered one was created and deleted, the registry kept its
  SHA-256 and the registered entity came back after the restart. Restore binds by id, since
  `GetObjectsAtPosition3D` promises no order and three traced cases show a position match taking
  the wrong entity or creating a second one (the [DESIGN] restore rule added with it is withdrawn,
  see Fixed); a restore pass still queued in
  `CALL_CATEGORY_SYSTEM` is removed (`ScriptCallQueue.Remove`) before the shutdown flag is set, so
  the shutdown's deletions cannot unregister entries; both were read in the code and not reproduced
  in game. The entry-point audit gains the worked example, the invariant's entry points and a search
  for proximity used as identity.
- `dayz-model-pipeline` `references/lods-and-geometry.md`: "Collision of a large building with an
  interior", from a rock-shaped building generated from Blender with a hangar, an attic and a lift
  inside (SecretRock RocaHeli R7.1-R7.3, 2026-10-01 to 2026-10-03; ledger SP-453, SP-457 and
  SP-458). An MLOD stores each named selection as one byte per point and per face of its LOD
  (py3d `Selection.write`), so collision pieces cost about the square of their count: 478 MB with
  1,150 pieces, 55-75 MB with 827-997 pieces of 6 points. Then: no room-membership test on open
  meshes; collision prisms that follow the visible face (geometric normal, neighbours by
  position, a room test with horizontal rays, every exterior triangle probed at 7 points), with
  the scope of each figure; the visual budget split into two models; and a `binarize` limit that
  prints nothing. With too many pieces in its collision LODs, `binarize.exe` wrote no ODOL and no
  capacity line (`OTHER_FAIL`). Over 9 variants, faces, named selections × points and selection
  bytes separate the passes from the failures equally, the piece and point counts alone do not,
  and the variable is not isolated; a truncated MLOD gives the same verdict. The fix, a second
  collision-only model with the same transform, took rays in game (0 holes in Geometry, Fire and
  View). Also: the pre-binarize check in `config-and-packing.md`, a pointer in `SKILL.md`'s Quick
  Reference and at `ComponentXX`, this cause of `OTHER_FAIL` with its two checks in `dayz-vehicles`
  `references/binarize-vertex-budget.md` and in `dayz-p3d-audit` SP-359, and a `dayz-p3d-audit`
  section on source meshes (zero-area faces and orphan points; faces against their normals read
  with Check A, not turned to them; `bmesh.ops.convex_hull` hulls recomputed with Qhull).
- `dayz-physics-engine` engine truth 11, the moving platform that is a separate entity: walking and
  jumping on it, from four trips played by hand (SP-452; DayZDiag 1.29.163709, one client on
  localhost, 2026-10-01). Walking during the travel kept the player linked, with no slide, and
  96.0-97.8 % of the server samples and 98.4-99.6 % of the client samples within 8 cm of the face. Two
  jumps on the way down kept the link, peaked 0.30-0.32 m above the face and landed on it, close to
  the vanilla jump on still ground (`StartCommand_Fall(2.6)`, 0.345 m by ballistics): the jump is
  relative to the platform, whether the link carries the player or the take-off inherits its
  velocity (the run cannot tell). A player who walked aboard was linked without the step a teleport
  needs, and no sample of either exit read a fall (the bottom one logged at 2 Hz). Short spikes of up to 22 cm (server) and
  12.6 cm (client) lasted one to three samples; on the client they follow long frames, and on the
  server the cause is open. A jump while the platform rises was not tried.
- `dayz-script-validator`: two FAIL rules from script modules that did not compile, each filed in
  the pipeline inbox with its log. `ES-RESERVED-WORD-IDENTIFIER` flags a variable, member or
  parameter named `sealed`, `local`, `owned` or `out`: `void Setup(vector rest, vector sealed)`
  stopped the World module on DayZDiag 1.29.163709 with `Expected name, not a keyword 'sealed'`,
  and `vector local;` stopped the Mission module on DayZDiag 1.30.164014 Exp with
  `Broken expression (missing ';'?)`, the error `owned` and `out` gave earlier
  (`enforce-script-reference`). Vanilla uses all four only as keywords; other modifiers it uses the
  same way wait for a failure on record. `ES-MODULO-FLOAT-CONTEXT` flags `%` in an arithmetic
  expression that also holds a float literal: `((g % 5) - 2) * 7.0` (DayZDiag 1.29) and
  `float ox = (n % 4) * 0.7 - 1.05;` (DayZ 1.30 Exp) failed with `Unknown operator '%'` although
  both operands of `%` are integers, and the `%` in an int local first compiles. A float variable
  is not seen, only the literal. Code under another mod's `#ifdef` is judged; `#if` blocks and the
  `#ifndef`/`#else` of a macro the same file `#define`s first are not, and an expression is never
  read through them, nor from the branch that holds the `%` into another branch of that block.
  Neither rule reports
  anything on vanilla 1.29.0.163451 (the vanilla control still matches its baseline) or on vanilla
  1.30.164014 Exp. Two errors filed with them get no rule yet: `Variable name 'X' already used as
  type name` needs the vanilla tree's class names, and `Formula too complex` has no measured limit
  (vanilla compiles a statement with 14 `+`; the one that failed had about 20 terms and its source
  is gone).
- `dayz-script-validator`: `ES-UNDEFINED-CLASS-REF` (FAIL), a third tree-level check, and
  `--vanilla-root DIR` (default `DAYZ_VANILLA_ROOT`, then `P:\scripts`). The public mod TransferZ,
  PR #12 at `11da911`, deleted a `4_World` class that `5_Mission` still called
  (`TransferZ_MaintenanceClient.c:59`, `TransferZExternalStagingSortPlanner.Sort(player, source)`).
  No module of the mod, of vanilla or of CF declared the type, so the Mission module could not
  compile, and the linter answered WARN with 0 errors. The rule flags a class-like name (first
  letter upper case) used where only a type fits (`Name.Method(`, `Name.Cast(`, `new Name`, a
  template argument, a typed declaration at the start of a line) when no `class`, `enum` or
  `typedef` of that name exists in the addon, the vanilla tree or an `--external-scripts` root.
  Not booted: the compile failure follows from the missing declaration. Where it cannot see every
  place the type could be declared, it lists what it could not judge under `info.skipped_checks`
  (and as a `SKIP` line in `--terse`) instead of a finding, and the status does not change: no
  usable vanilla tree (absent, or declaring no `class Managed`); a dependency, direct or required
  by a scanned dependency, that is not one of the 211 vanilla patch names
  (`scripts/shared/vanilla_patches.py`; mods use the `DZ_` prefix too) and that no scanned root
  declares in `CfgPatches`; a `requiredAddons[]` entry that is not a string literal; or no
  `requiredAddons[]` entry at all. Pass each dependency's root, the folder with its `config.cpp`,
  with `--external-scripts` to get verdicts. Variables declared after a comma
  (`string a, B;`) count as variables, while the commas of template arguments and of comparisons
  do not, and the `#ifndef`/`#else` branch of a macro that a scanned script `#define`s, or a
  scanned `CfgMods defines[]` lists, on a line the preprocessor always keeps is not judged.
  `vanilla_control.py` passes the tree as its own vanilla root, so the rule runs there instead of
  skipping, and the control still matches its baseline.
  On the TransferZ tree with CF passed, the first version of the rule reported one FAIL, on that
  line, and none on the mod's `main` at `2c7d5c1` (2026-09-19).

### Changed

- `dayz-p3d-audit` killer #8 (`SKILL.md` and `references/killers-detail.md` §8): a closed part
  left out of every `ComponentNN` collides with nothing also when the same LOD has other
  components, measured in game instead of expected (2026-10-02, DayZDiag 1.29.163709); a part left
  out only in part was not measured. A pair of 2 m boxes, A in
  `Component01` and B in `Component02` or in no component (byte-identical apart from those three
  tags), packed binarized and unbinarized, as `HouseNoDestruct` and as an `Inventory_Base` item:
  B in no component took 0 of 46 rays (`geom`, `view`, `fire` and the physics-world bullet ray)
  and the player walked through it as on open ground; as `Component02` it took 26 of 26 and
  stopped the player; no log line. Binarize keeps the left-out faces in the ODOL. The `dayz-doors`
  LOD reference (`references/lods-and-object-builder.md`) now says that the Expert tutorial's
  `Expert_Mode.p3d` leaves its lever out of every component in Geometry and Fire, although the
  tutorial's text puts it in Geometry: in game the lever took no Geometry, Fire or physics ray (0
  of 28) and a player walking into its knob stopped on the block behind it. In View Geometry the
  lever is `Component09`, one non-convex piece (knob and bar), and only the knob answered rays (3
  of 3, the bar 0 of 9). The reference gives the repair (the knob and the bar rebuilt as two
  closed, convex components in every collision LOD, each closed on the side they share, kept in
  `door1_open` and in `lever`, which the tutorial's View and Fire LODs lack; not tested in game)
  and a pre-export checklist line; the P3D is unchanged.
  py3d 1.10.0 raises that case as `ERR_COMPONENT_COVERAGE` (next entry); the pinned 1.9.0 wheel's
  `WARN_COMPONENT_COVERAGE` message still calls it not measured.
- py3d 1.10.0: `ERR_COMPONENT_COVERAGE`, an ERROR, for a closed part left out of every `ComponentNN`
  of a Geometry, View or Fire LOD, the case the in-game A/B of the previous entry measured (such
  parts took no ray in the LODs they were left out of, also beside covered parts, and no log line
  said so). `_check_component_coverage` groups the LOD's faces, proxy triangles aside, into pieces
  that share a corner position, read as the MLOD stores it (float32), and raises the ERROR for a
  piece that is a closed solid (each edge used by two of its faces, once each way, and thicker than
  16 float32 steps at its distance from the origin, so a flat double-sided sheet never is one) with
  no face and no point in any component. Each LOD is read on its own: the message counts the parts
  and their faces, gives each measured part its own readings (a box left out of all three LODs,
  which the player walked through; a lever left out of Geometry and Fire, whose knob did not stop a
  player) and says that a part left out of one LOD alone, component selections that hold nothing,
  and weapon fire were not measured. Every other face in no component stays
  `WARN_COMPONENT_COVERAGE` (a part left out only in part, an open piece such as a stray triangle, a
  flat double-sided sheet, a closed part too thin for the cutoff, which errs toward the WARN): its
  message says that was not measured, where 1.9.0's said "expect them to take no part in collision",
  and it no longer counts the ERROR's faces; the WARN for points alone is unchanged. A LOD whose
  component selections are all empty raises the ERROR for its closed parts (1.9.0: the WARN, every
  face counted). Owner's choice (2026-10-02): an ERROR only where measured. Downstream an ERROR
  fails `dayz-model-preflight` (`PREFLIGHT_PY3D_ERROR`), makes `dayz-vehicle-proxy-contract` refuse
  the MLOD and `python -m py3d validate` exit 1, and `validate()` skips its in-memory round trip.
  Measured offline on 414 unique MLODs (the owner's mod and vehicle projects and the three door
  models of the `dayz-doors` tutorial) with the 1.9.0 and 1.10.0 modules through
  `P3D._scan_v12_findings`: `Expert_Mode`'s lever, one closed 18-face piece in no component, becomes
  the ERROR in its Geometry and Fire LODs (its only ERROR); a vehicle's Fire LOD keeps the WARN for
  its two stray 1 mm triangles; no other finding changed. Version 1.10.0 because the pinned 1.9.0
  wheel (entry below) carries the 1.9.0 check; no new wheel. `dayz-p3d-audit` killer #8 (`SKILL.md`
  and `references/killers-detail.md` §8: the py3d text and, after review round 2, the opening
  sentence, which gave the lever the box's readings; the replaced text quoted in dated notes) and
  the `dayz-doors` LOD reference (the Expert lever paragraph and the checklist line) name both
  codes, and the py3d README the new finding. Tests: 52 new in
  `tools/py3d/tests/test_s2_validate12.py` (py3d suite 386 passed, 11 skipped; base 334 passed, 11
  skipped).

- `dayz-mcp-verify` "Axis-aligned test fixtures": a measured caveat. In one run (2026-10-02,
  DayZDiag 1.29.163709) a model with two 2 m boxes, one in `Component01` and the other in
  `Component02` or in no component, spawned with `rotation=64` came out as modelled on
  `HouseNoDestruct` and with the boxes' sides swapped on `Inventory_Base` (`item_large`), as a
  180-degree turn about Y leaves them (the boxes, symmetric in z, cannot tell it from a mirror in
  x), read from the component index of each hit and from which box took rays. Two parallel rays,
  face normals and a fixture symmetric about its origin cannot show the swap; the playbook now says
  to give the fixture sides a ray can tell apart (one component per side, read from the `component`
  of `rvproxy` hits) and check which answers where. Whether the swap is fixed or random, and its
  cause, were not measured.

- `dayz-p3d-audit` "Absolute winding check", rule 6: the kit box's missing collision is measured
  now, not a hypothesis. In a paired run (2026-10-02, DayZDiag 1.29.163709, the kit's own config on
  three classes, the MLODs packed unbinarized) the shipped `lf_kit_box.p3d` took 0 of 27
  `scene_raycast` rays in `geom`, `view` and `fire` again, and the same bytes with only the
  collision LODs' faces reversed took 27 of 27, with the collision normals negated or kept, at the
  same coordinates relative to the kit; a vanilla `WoodenCrate` took 27 of 27. Binarize writes the
  two fixed variants to the same ODOL. A server physics-world ray (`DayZPhysics.RayCastBullet`)
  finds the shipped kit where it finds the fixed ones, so the winding did not hide it from that
  static query (player contact was not measured). The misses were measured on the dayz-mcp
  bridge's `RaycastRVProxy` rays; the vanilla cursor and hologram rays in the same intersection
  modes are named as the reason to expect the defect in play, untested. The replaced sentence is
  quoted in a dated note. The first run's cursor-like ray is corrected too: the dayz-mcp bridge
  replaces a requested radius of 0 with its 0.05 m default, so it was a 0.05 m sphere, not radius 0.
- `dayz-animation-pipeline` Route C, the BI FBX rig's map `(−x,−z,−y,w)`: played in game, no longer
  offline only. In one run (2026-10-02, DayZDiag 1.29.163709) `LeftArm` alone was keyed on
  `animation_rig_character.fbx` straight ahead and 20° above horizontal, a turn about the bone's own
  X and Y where the FBX map and the JD map disagree, and spliced alone into the vanilla 1H idle.
  Through `scripts/seanim_export.py` (rig read as `fbx`) the arm came out forward of the chest; through
  the JD map it came out to the side; each matched the side offline FK gave it. The script's comment,
  `weapon-anim-authoring-viewer.md` (table status, new paragraph; claim
  `CLAIM-ANIM-ROUTEC-FBX-INGAME`), `blender-authoring.md` and `blender-animation`'s
  `dayz-handoff.md` now say so, scoped to one bone and rotations only (the offsets came from the
  vanilla clip).
- py3d wheel pinned at 1.9.0 (`tools/py3d/rollout/wheel-manifest.json`):
  `py3d_dayz-1.9.0-py3-none-any.whl`, SHA-256
  `33d8b5ba726c933d9bf1921f610e66de2e5395a7b38bee44fdebb4b49bcc635e`, built by
  `rollout/build-wheel.ps1 -UpdateManifest` from the source on main at `62c3dcc`, at the owner's
  request. Since the 1.8.0 pin it carries the winding messages of #37 and #40 and the component
  checks of #46 and #54. The toolchain was checked first: the same script rebuilt the 1.8.0 pin
  (`e7184429…`) byte for byte from the commit that sealed it (`053dc7f`), with Python 3.14.3 and
  setuptools 83.0.0; then 1.9.0 built six times to one hash, two of them in the seal. The wheel's
  `py3d/` files and `LICENSE` are byte-identical to the source, and `verify-wheel-restock.ps1`
  passed against it on synthetic skill roots. No installed skill tree vendors the wheel, so nothing
  was restocked; the user site-packages install follows the merge. The skill notes that called 1.8.0
  "the pinned wheel" now say it was pinned until 2026-10-02 (`dayz-p3d-audit` item 1 of "The three
  py3d gates", killers #2 and #8 and `references/killers-detail.md` §2 and §8; `dayz-vehicles`
  `rip-import.md` §3.5 and `vehicle-structural-parity.md`; `dayz-clothing`
  `autofit-from-official-rig.md`), and item 1 describes the 1.9.0 `ERR_WINDING_INVERTED` message
  next to the 1.8.0 one.
- py3d wheel pinned at 1.10.1 (`tools/py3d/rollout/wheel-manifest.json`):
  `py3d_dayz-1.10.1-py3-none-any.whl`, SHA-256
  `c9f000a51e6aca83104a8f021ef5e3eefe8d7f0a5b053623544b49dbdd5d1785`, built by
  `rollout/build-wheel.ps1 -UpdateManifest` from the source on main at `ea7b396` (`tools/py3d` as
  #78 left it), at the owner's request (2026-10-03). Since the 1.9.0 pin it carries
  `ERR_COMPONENT_COVERAGE` (#72, 1.10.0) and the part-by-part normals step of the two winding
  messages (#78, 1.10.1), whose entries (#72's above, #78's under Fixed) say no wheel carried them.
  The toolchain was checked first: the same script rebuilt the 1.9.0 pin (`33d8b5ba…`) byte for byte
  from the commit that sealed it (`4626f4b`), with Python 3.14.3 and setuptools 83.0.0; then 1.10.1
  built six times to one hash, two of them in the seal. The wheel's `py3d/` files and `LICENSE` are
  byte-identical to the source, `verify-wheel-restock.ps1` passed against it on synthetic skill
  roots, and the 7 CANON tests passed against upstream `7acd58b` (py3d suite with the upstream
  clone: 398 passed, 4 skipped). No installed skill tree vendors the wheel, so nothing was
  restocked; a dry run of the applicator on temporary copies of the build machine's skill roots
  planned 46 replacements, all in trees this rollout does not manage, and wrote nothing. The 1.9.0
  wheel is kept as the rollback, and the user site-packages install follows the merge. The skill
  notes that called 1.9.0 the pinned wheel, or said the pinned wheel's winding messages close with
  the per-corner normals step, now give 1.9.0 as the pin from 2026-10-02 to 2026-10-03 and name the
  1.10.1 pin (`dayz-p3d-audit` item 1 of "The three py3d gates", killer #8, "Absolute winding check"
  rule 5 and `references/killers-detail.md` §8; `dayz-doors`
  `references/lods-and-object-builder.md`, the Expert lever paragraph and the checklist line;
  `dayz-clothing` `autofit-from-official-rig.md`), and `TOOLS.md`, `README.md` and
  `GETTING-STARTED.md` give the current version, 1.10.1, and the pin, where they said 1.5.0, as do
  `dayz-model-pipeline` `references/py3d-direct-generation.md` (it said 1.7.0) and the docstring of
  `dayz-p3d-inspector` `scripts/p3d_inspector_extract.py` (it named the 1.5.0 wheel).
  `dayz-animation-pipeline` `SKILL.md` and `tools/dayz-3d-viewer/README.md`, which gave 1.6.0 as the
  pack fork's version, now give it as the minimum they need.

### Removed

- `dayz-doors` no longer ships `assets/` (nine files: three `.p3d` models, each with its
  `model.cfg` and `config.cpp`) or the six verbatim copies of those `model.cfg` and `config.cpp`
  files in `references/worked-examples.md`. They are not the Pack author's work: they are the
  examples of novoGOD's door tutorial `Doors_Buttons_Lesson` (a Discord attachment, files dated
  2025-04-23), whose archive holds no license or permission text. Their SHA-256 hashes equal the
  archive's members (the text files after LF normalisation), yet since v1.3.0 the source map
  labelled them, like the rest of the skill, "author-owned MIT", and the compatibility matrix and
  the 1.2.0 entry below called them the author's. `worked-examples.md` now describes the three
  patterns in tables (bones, animation windows, Doors entries) and, like the other two references,
  cites the tutorial's files by path and line. The source map registers the tutorial as an excluded
  source (no license or redistribution grant observed) and corrects the license of the old
  `worked-examples.md` input, which held the six copies; `THIRD_PARTY_NOTICES.md` lists the
  tutorial with the research-only sources. The files stay in the git history and in the v1.3.0 to
  v1.5.0 source archives.

### Fixed

- `dayz-persistence` Hard stops item 9 and point 2 of "A registry entry leaves by its id, never by
  proximity" (#97), and the matching search in `rigorous-data-audit`'s entry-point audit: point 2
  no longer gives a restore rule. The [DESIGN] rule merged in #97 created an entry's entity
  whenever the radius held none of its class, and a post-merge cross-family review traced that
  into a second entity. Three [DESIGN] rules written to replace it came out UNSOUND in review too:
  one kept a list of the restore's own creations per mission and bound each entity as it loaded (a
  second entity after a mission change; the wrong one when two loaded entities carry one id), one
  kept a list of every live entity through `EEInit` and `EEDelete` (a second entity from a pass
  started inside a creation), and one reserved the entry while its entity was created (a second
  entity from a pass that reloads the registry, and an entry reserved for good when its creation
  fails). Point 2 now keeps what the vanilla scripts and SecretRock's code show (only the id can
  bind; `GetObjectsAtPosition3D` promises no order, so a position match proves nothing) and lists
  the traced failures, the wrong entity and a second one, as an open problem with no rule reviewed
  sound. Item 9 stops a restore that gives an entry a new entity while one it already had may
  still live, and the audit search no longer calls a candidate without the id "a conflict to
  log". Traced through the code and the rules' text; none of it was reproduced in game.
- `dayz-pbo-build` SP-155 rule 1: a staged binarize looks for every file the p3d cite under the
  staging folder, which AddonBuilder passes as `-addon` (the source's parent), never under `P:\`,
  and embeds a face material it cannot find EMPTY in the ODOL (no shader, no stage texture, no
  `.bisurf`) while the build says "Build Successful". The rule called the "Material not loaded"
  messages of a staged build tolerable; the ArmorHneck ODOL it cited as working (deployed
  2026-08-04) carries its Fire Geometry material `armor_5mm_plate.rvmat` empty. The rule now
  stages the cited files beside the mod (copies, or a `DZ` junction to the extracted vanilla
  data). A new rule 5 checks, before the build, that every path the faces cite exists under the
  staging folder, and reads the ODOL afterwards as a control: an unresolved material has no
  shader, stage or surface and the engine's default colours, but bare vanilla `.rvmat`s
  (`half_lighted_default`, `streambed_leaves`, `default_2pass`) embed much the same, so a match
  is a lead to confirm against the text `.rvmat` (CfgConvert decoded a binarized `wood.rvmat`
  from `.bin` to `.cpp`). Measured: CocaLab
  (2026-09-27; gate control without the files: 6 failures) and the DayZ MCP v1.3.1 spike on
  SimpleGroup (2026-10-01, 11 builds): binarize parses every `config.cpp` under `-addon`, through
  junctions; AddonBuilder exits 0 with `[ResultCode]=1`; `-project=<source>` drops every `.paa`,
  `.rvmat` and `texHeaders.bin` from the PBO; with the mod alone under `-addon`, `T1_FlagKit.p3d`
  embeds its two `dz\` materials empty, and with a `DZ` junction beside it, it is byte-identical
  to the production build. `dayz-clothing` BUILD step 1 points at the rule. SP-069 rule 1 no
  longer says `-temp` "must stay under `P:\`": with the spike's nine binarized builds in a local
  `-temp` added to four earlier ones, `P:\` is the habit, not a measured requirement. The
  "Gate ordering" paragraph says AddonBuilder's own exit code is 0 on a failed build. Not
  measured: what an empty material does in game. The replaced sentences are quoted in dated
  notes.
- `dayz-ui-development`: exact units are 1/1080 of the screen height, and an unnumbered face
  with no size key follows its box. Rule 3 called `hexact*`/`vexact* 1` physical screen pixels and advised
  proportional units by default. Measured in game, exact units scale with the screen height on
  both axes: `ui_tree` rects at heights 461 to 1108 (2026-08-28/29), and on SimpleGroup's frames
  (2026-09-28) a 400-unit panel drew 400 px wide at 1920x1080 and at 2560x1080 and 267 px at
  1280x720. TEXT SIZING LAWS said the font-only default ignores the widget box, against
  `hot-iteration.md`'s "glyph height tracks the WIDGET height". SimpleGroup's shipped panel
  (unsized `Metron`/`MetronBook`, captures at 1080p and 720p) sides with the box, and the
  section now holds one law per face: an unnumbered bitmap face or an SDF face with no size key
  follows its box, a numbered bitmap face keeps its pixel size (the same ink at 1080p and 720p;
  text that must fit at 720p fills at most 2/3 of its box at 1080p), and an SDF face with
  `"exact text size"` N draws about N px per 1080 of height; the mockup calibration follows. Also from those captures:
  `WrapSpacer` + `"Size To Content V"` stacking, case-sensitive attribute keys (a GridSpacer's
  lowercase `columns`/`rows`), `rover_sim_colorable` honouring alpha, and a button with no style
  drawing no body. Aligned: the troubleshooting row, the offline preview step, S2 sorter rule 3,
  `layout-format.md` (unit comments, rect arithmetic, spacers), `layout-empirical-corpus.md`
  (the attribute table), `plan-to-implementation.md`
  (§0, §1.1, §2, the previewer note, §6.3), `widget-api.md`, `styles-format.md`,
  `advanced-patterns.md`, `admin-ui-patterns.md` (exact values need no script scaling),
  `hot-iteration.md`, the comments of the three templates, `TOOLS.md` and the layout viewer's README. The pack
  parser still lays exact units out as pixels (`tools/dayz-ui-lab/dayz_ui_lab/parse.py:772-775`);
  the docs now say so. Replaced passages are quoted in dated notes.
- `dayz-animation-pipeline` `scripts/seanim_writer.py` keeps SEAnim bone modifiers. `read_seanim`
  skipped them and `write_seanim` always wrote a count of 0, so a DayZATool extract read and
  written back lost them: `p_1hd_erc_idle_low` (65 bones, ABSOLUTE header) lost its 60 RELATIVE
  modifiers, and editing one track of a vanilla clip turned every bone ABSOLUTE. `read_seanim` now
  returns each bone's `modifier` (None when it has none) and refuses a modifier index out of range
  or repeated; `write_seanim` writes one entry per bone that carries one, in bone order, two bytes
  wide past 255 bones (four past 65,535), and refuses a value that is not a byte. That extract and
  four clips spliced from it read and write back byte for byte; bones without `modifier` write
  what they wrote before. Regression test `tests/test_seanim_writer.py`: fixtures built byte by
  byte from the SEAnim layout, 22 cases, all failing on the previous script; each mutant the
  review found surviving (modifier 0 dropped on read or write, the index width off by one at 255
  or 65,535 bones, only 0 to 3 accepted, 255 modifiers refused, `False` accepted, a repeated index
  of the same type accepted, a modifier equal to the header's type dropped) fails at least one of
  them. `skeletal-anm-enfusion.md` (claim `CLAIM-ANIM-DAYZATOOL-NO-MODIFIERS`): DayZATool's
  `--generate-anim` does not keep them either; the `.anm` built from that extract unchanged
  re-extracts with none. `weapon-anim-authoring-viewer.md` and a comment in `seanim_export.py` no
  longer say that `read_seanim` drops them.
- `dayz-model-pipeline` `references/animations.md`: a translation's `offset0`/`offset1` count
  lengths of its axis, not metres. Section 5's "Scale" rule said "Axis vector doesn't define
  scale; only direction matters" for every axis, and the examples read their offsets as metres.
  Read on 2026-10-03: Binarize stores a translation's offsets as `model.cfg` writes them and its
  axis at its own length (CocaLab's `offset1 = 1` on twelve 12.1 to 16.2 mm axes reads 1.0 in its
  binarized tray, each axis at its source length). If the older binarizer of the vanilla m249
  (ODOL v54) kept offsets the same way, the m249's compiled offsets are its authors' and only make
  sense in axis lengths (the belt runs from -1 to 0 on axes 1.11 to 1.15 cm long, the bolt from 0
  to +1 on 8.34 cm, the magazine from 0 to +1.45 on 10 cm); its rotation axes are stored as unit
  vectors. Inferred from that, not measured in game: the engine moves a selection by the offset
  times the axis. The rule now separates rotation (direction only) from translation (offset times
  axis length; on a 1 m axis the offset reads in metres, the axis `dayz-vehicles` recommends), the
  examples say their offsets assume a 1 m axis, and the troubleshooting table gains the symptom (a
  translation that barely moves or leaves the model). A dated note qualifies its "Multiple
  animations fight" row: the same m249 binds up to eight animations to one bone. Claim
  `CLAIM-MODEL-TRANSLATION-AXIS-LENGTH`; the replaced sentences are quoted in dated notes, and the
  example comments keep their text with "on a 1 m axis" added.
- `dayz-vehicles`: `references/gauge-needles.md` (twice) and
  `references/vehicle-config-and-modelcfg.md` named an unpublished skill as the tool that read the
  vanilla cars' animation classes from their ODOL, and `promotions/adjudications.json` named it in
  the reason of the `skill/ai-3d-to-dayz` adjudication. The three passages now name the capability,
  the ODOL reader of the external ODOL->MLOD converter, in the phrase the pack already uses for that
  converter. Where an installation sets the phrase alias for it (`packctl/promotion.py`,
  `promotions/local-targets.example.json`), a promotion writes the converter's local name in its
  place, so that installed copy still points at the tool; without the alias the public wording
  ships as it is. The adjudication's reason says "external converter -> the converter's local
  name"; its key and digest are unchanged, and `promote` uses only those (of a reason it checks that
  there is one). The measurements and what they cite are unchanged.
- `dayz-physics-engine` engine truth 2 said that a model with no View Geometry LOD gets no action.
  Read in the 1.29 source (not measured): at a camera pitch of −45° or lower, targeting also takes
  the objects of a 30°, 3 m cone and scores them by their distance to the cursor ray, with no hit on
  them needed, so an item on the ground can still become a target; the truth now says so and points
  to `dayz-mcp-verify`. In `dayz-mcp-verify` PREREQUISITES 4, the `extra_mods`/`base_mods` boundary
  was described as rejecting `:`, `\` and `/` in every project; it now also accepts an absolute path
  inside the project's `mod_roots`, and a workshop path, outside them, still fails with `bad_mod`
  (dated note; the old text is kept). Two more dated notes under WHAT IT DOES NOT COVER: the vanilla
  control's readings ("control HIT + mod MISS ... = reversed collision convex components") name a
  likely cause, which only a winding-only pair decides; and `entry=0` is not terrain by itself, since
  a ray that starts inside an object reads `entry 0, exit 1` at distance 0 (run 606a5dbb).
- `dayz-animation-pipeline` `weapon-anim-authoring-viewer.md`: why the helpers' world is composed
  by hand. It said plain `matrix_world` returns 0 before a depsgraph update, and even after for
  bone-parented empties. Measured on the BI FBX, `hide_viewport` decides: the 17 of 38 empties
  that import disabled in viewports, `RightHand_Dummy`, `LeftHand_Dummy` and the
  object-parented `Weapon_Root` among them, keep it at the origin before and after
  `view_layer.update()`; the 21 others, 16 of them parented to bones, agree with the formula.
  The SKILL.md entry of `fbx_extract.py` now says its `rig_raw.json` carries that
  `matrix_world` for the empties, and "Reusable tools" no longer calls `build_rig_dayz.py`'s
  output DayZ-space.
- `dayz-mcp-verify`: the pose check of "Axis-aligned test fixtures" and the `scene_raycast` entry
  of "What it does not cover" no longer read anything from the default `rvproxy` reply's `normal`.
  That field is the engine's `RaycastRVResult.dir`, for a ray the direction and size of the
  intersection: in two runs (2026-10-02) it lay along the ray in all 190 hits on an object, a box
  yawed about 10 degrees included, so its direction never showed a tilt or the side of the face.
  The face normal comes from `method="bullet"` (a unit vector in all 40 of its hits), read on two
  faces that are not parallel, since a tilt about one face's normal leaves that normal unchanged.
  The replaced sentences are quoted in dated notes.

- `dayz-p3d-audit` killer #1 and Check A's `MIXED` bullet. Killer #1 ("Inverted Face Winding")
  said a broken Geometry LOD has its normals pointing inward and fixed it by swapping
  `vertices[1]`/`[2]`; Rule 12 stores the cross product and the normals both inward, and the swap
  turns a quad into a crossed face. The killer is now a collision LOD wound opposite to the
  Visual LOD, the relative check `audit_p3d.py` runs through py3d `P3D.validate()`
  (`ERR_WINDING_INVERTED`), read as a trigger. Rule 18's per-component check decides: every face
  of every closed, convex component must point inward, and faces outside every component, or a
  face whose first three corners are collinear, leave it unresolved. `face.vertices.reverse()`
  fixes the faces that read outward, and a collision LOD is never reversed to match the Visual
  LOD ("Absolute winding check", rule 7). The decision tree's step 5a now reverses each outward
  face too (it reversed every face of the component, which turns its healthy faces outward), and
  `dayz-model-pipeline` Rule 18 gets a dated note saying the same: every face, not most, and only
  the outward faces reversed, since its whole-LOD fix moves the inversion onto the healthy
  component of a LOD with one healthy and one outward component. Measured offline
  with py3d 1.8.0 on synthetic boxes: the finding fires on an outward box and clears after
  `reverse()`, also fires on a healthy box under a Visual LOD whose cross product points outward,
  and on two boxes 4 m apart reads only `WARN_WINDING_MIXED`, healthy or not. The killer's offline
  pointer to `check_dayz_winding.py`, which then failed a correct export, and the "Z-up → Y-up flips
  collision winding but not visual" pitfall are corrected with it. Check A called any 5-95 %
  reading a CRITICAL real bug; the SUB_BRZ co-driver door, verified in game, reads `MIXED`
  (72.67 % of 11,921 faces flipped, 25.9 % agreeing) without an inverted face group (Check B: one
  stray edge in 17,542, and with it cut every welded component orients as one group), because its
  parts follow two conventions: exterior paint, black trim and mirror against their normals,
  cabin trim and glass with them. A mixed reading is now a WARNING to split by part, each part or
  group repaired from the Check A table, so a group's normals turn with its winding only when
  they agreed with it. Rule 2 of "Absolute winding check" keeps its sentence and gets the
  measurement in a dated note: on that door the twins (144 faces) do not explain the mix.
- py3d `ERR_WINDING_VS_NORMALS` message: it read every disagreement between winding and stored
  normals as faces wound backwards and prescribed `face.vertices.reverse()` on every face, and
  the py3d README called that fix always correct. The finding only says the two disagree. On the
  model of the Rule 12 in-game test, rebuilt byte for byte by the py3d tests, the correct export
  with its normals turned and the same export with its faces turned raise the same finding with
  the same text and need opposite fixes; either fix silences it, and the wrong one leaves the
  cross product and the normals both outward, the orientation of the variant that rendered
  inside-out in game. Reversing every face did exactly that to two Blender exports in DayZDiag
  (`dayz-p3d-audit`, "Absolute winding check: what 0 % means"). The message now says the two
  disagree and gives an order that works for both: settle the winding first, normals untouched
  (visual LOD: per closed shell, made coherent by turning the vertex order of the faces that
  disagree with their neighbours, then reversed whole if its signed volume by winding has the
  wrong sign; collision LOD: reverse the faces that point outward in each convex component),
  never with a `vertices[1]`/`[2]` swap; then negate each corner normal that still points
  against its face, with a negated copy for a pool entry that a kept corner also uses. Each
  part of that order answers a case measured on the same model with the steps it replaced: a
  shared entry negated in place turned a part whose normals were right (75 % agreement left);
  a closed shell with one reversed face kept its negative volume; turning that odd face with
  its normal, when the odd face was the right one, left one wrong normal that `validate()` no
  longer reports (47 of 48); and negating whole faces on a first-corner reading turned right
  corners (96 of 144 right before, 48 after, with 100 % agreement). On a synthetic ring-shaped
  FireGeometry, the centroid test read 264 of 336 correct faces as outward, hence "convex". The
  README says the same in three steps, adds that neither winding check sees faces and normals
  turned together (`transform(ROT_X_NEG90)` alone: 100 % agreement, `validate()` returns `[]`),
  and no longer gives a wrong normal sign the inside-out symptom of a wrong face order. Finding
  code and severity unchanged. No new wheel: the pinned and installed `py3d_dayz-1.8.0` still
  prints the old message.
- `dayz-p3d-audit` "Absolute winding check", rule 6: it pinned `ERR_WINDING_INVERTED` on the absolute
  check and, because that code flags the production `lf_kit_box.p3d`, called the fork's sign
  convention inverted. py3d raises that code in the relative check (`_check_winding_vs_visual`); the
  absolute check raises `ERR_WINDING_VS_NORMALS` and stays silent on the kit box. On the kit box the
  relative finding named the outward LODs: its Geometry, View and Fire components are wound outward
  (Rule 18), and in game (2026-10-02, DayZDiag 1.29.163709, the MLOD packed unbinarized) its
  collision took 0 of 27 `scene_raycast` rays in `geom`, `view` and `fire`, while `gate_and.p3d` from
  the same PBO (components wound inward) and a vanilla `WoodenCrate` on the kit's physics layer took
  21 of 21. That run did not change the kit's winding alone, so outward winding as the cause stays a
  hypothesis for this kit, supported by the paired test behind Rule 12 (which also turned the Visual
  LOD and the normals). Rule 6 now reads the finding as a trigger for Rule 18's
  per-component check and sends the fix to killer #1, and rule 7 no longer offers the kit box's
  outward sign, or a component Rule 18 cannot score, as one to keep. The old text is quoted in dated
  notes.
- `dayz-p3d-audit` killer #2 said the Geometry component MUST be `Component01` and that any other
  case silently loses all collision; `dayz-vehicles` limited that rule to `Inventory_Base` items.
  Measured in game (2026-10-02, DayZDiag 1.29.163709) with one 2 m box written three times,
  byte-identical except for the collision selection (`Component01`, `component01`, none), each
  packed unbinarized and binarized, as an `Inventory_Base` item and as a `HouseNoDestruct`: both
  names took every `scene_raycast` ray in `geom`, `view` and `fire` (6 of 6 per mode on the items),
  the physics ray, and stopped a walking player 0.36 m before the face; the box without a
  selection took none, and the player walked through it, with no log line. Binarize writes both
  names as the same ODOL, `component01`. Killer #2 is now that measured silent failure: no
  `ComponentNN` selection in the collision LODs (measured with all three unselected; other
  spellings untested). Decision-tree step 5b, the "case-sensitive" pitfall in PART 5 and the two
  `dayz-vehicles` notes are aligned; py3d `ERR_COMPONENT_NAMING` on `component01` is documented as
  a false positive (code unchanged). Killer #8 and step 5e asked for one `Component01` covering
  every face, which merges separate parts into one non-convex component; they now ask for one
  component per convex part, together covering the LOD, and note that py3d
  `WARN_COMPONENT_COVERAGE` counts `Component01` alone (it fires on the healthy six-component
  `gate_and.p3d`). The old text is quoted in dated notes.
- `dayz-p3d-audit` "From Check B to fix", step 3: it negated the stored normals of every minority
  group in the same pass as its winding, unless the pipeline recalculates normals afterwards. That
  fits a group whose normals turned along with its winding (the GunRacks case, the second row of
  the Check A table) and turns right normals wrong on a group whose winding alone was reversed,
  normals still matching its neighbours' (the fourth row). Measured offline on a Visual LOD made of
  one Rule 12 unit box with one face reversed and its normals untouched: the coupled fix left
  83.3 % agreement, reversing alone restored 100 % and the undamaged model; smoothed normals
  shared by three faces, and a two-face group with one face in each state, read the same way.
  Step 3 now reads the group with Check A before the fix and decides face by face: normals that
  agree with the inverted winding (reading at least +0.5) are negated with it, normals that
  disagree (at most −0.5) are kept, and a face that reads in between, or has a corner on the other
  side of it or within 0.1 of its plane (an average can hide one), is inspected. The reading goes
  through each face's vector area, because the first three corners of a non-planar or non-convex
  quad can read backwards once the face is reversed (measured on a planar dart quad and a twisted
  one: wrong branch in both states); Check A's definition and its `MIXED` bullet now read such
  quads the same way, and the door and Rule 12 MLODs measured there are all triangles, so their
  numbers stand. Its pool rule gives a negated copy to an entry that any kept corner also uses,
  and the fix closes on the whole LOD: Check B, plus every corner normal along its face by at
  least 0.1, a failing corner inspected rather than negated (a smoothed sharp fold fails it with
  every face wound right). py3d's absolute check reads one corner per face, and on a smoothed box
  whose shared entries had been negated in place it read 100 % with 8 corners still wrong. The
  section title and the `SKILL.md` index line said the same and are corrected with it; the
  GunRacks measurement and the recalculation caveat are kept verbatim, and the old text is quoted
  in dated notes. Item 1 of "The three py3d gates" said `ERR_WINDING_INVERTED` "suggests swapping
  vertices on every face"; the message of the pinned `py3d_dayz-1.8.0` names
  `face.vertices.reverse()` and warns against the swap. Following it on a healthy collision LOD
  still breaks the LOD: on the py3d multi-LOD fixture with its Visual LOD turned inside-out, it
  winds every face of each collision box outward and trades the finding for
  `ERR_WINDING_VS_NORMALS`, and `validate()` goes quiet only once those LODs' normals are negated
  too, with every LOD wound outward.
- `dayz-p3d-audit` killer #1 (`references/killers-detail.md`): the note on generating or editing a
  collision LOD quoted the text of py3d's relative-check message ("winding is INVERTED relative to
  the Visual LOD"), which can change with py3d; it now names the finding by its code,
  `ERR_WINDING_INVERTED`, as the automated-check note above it already does.
- py3d `ERR_WINDING_INVERTED` message: the relative check compares the share of faces wound
  outward from each LOD's centroid, files the finding on the collision LOD and told the reader to
  reverse every face of that LOD. On the clean multi-LOD model of the py3d tests, converted with
  `blender_to_dayz()`, a visual LOD turned inside-out (faces and normals together, which the
  absolute check passes) raised it on the three healthy collision LODs and nowhere else;
  reversing them traded it for `ERR_WINDING_VS_NORMALS` on each, and negating their normals as
  well left `validate()` at `[]` with every LOD wound outward, the collision LODs as
  `transform(ROT_X_NEG90)` alone leaves them, which registered no raycast in game. The pack
  already warned about this (`dayz-vehicles` `visual-gates-and-winding.md`; `dayz-p3d-audit`,
  item 1 of "The three py3d gates", "Absolute winding check" rule 7, and killer #1, which reads
  the finding as a trigger). The message now names the visual LOD it compares against, the one of
  lowest resolution, by index and resolution (`get_lod("visual")` returns the first in file
  order, which need not be it); says the collision LOD and that visual LOD disagree on which way
  is out, by a centroid test that assumes convex geometry, not which one is wrong; and gives for
  both LODs the order of `ERR_WINDING_VS_NORMALS`: the winding first, normals untouched (visual
  LOD per closed shell by its signed volume, collision LOD per convex component), steps that
  leave a part that reads right as it is, never a `vertices[1]`/`[2]` swap; then each corner
  normal still against its face. A part the steps cannot read (an open sheet, twins, a component
  that is not closed and convex) leaves it unresolved, to be checked in game or against a model
  that renders right; only with every part of both LODs reading right is there nothing to fix,
  as on a visual LOD meant to be seen from inside, which reads positive. Both messages take their
  winding steps from one helper, and every `ERR_WINDING_VS_NORMALS` text is unchanged. The README
  and KNOWN-ISSUES say the same. Finding code and severity unchanged: on that model it is the
  only finding that sees the inside-out visual LOD. No new wheel: the pinned and installed
  `py3d_dayz-1.8.0` still prints the old message.
- py3d `ERR_COMPONENT_NAMING` (py3d 1.9.0). It checked the Geometry LOD alone and also fired on a
  lowercase `component01` ("Engine requires 'Component01' (uppercase C); collision silently fails"),
  which in game collides exactly like `Component01` (the killer #2 entry above); vanilla vehicles
  name their components that way. It now flags a Geometry, View or Fire LOD that has faces outside
  its proxy triangles and no selection whose name starts with `component`, in any case; its message
  says that a model with no component in any collision LOD lost its collision silently in game, and
  that one LOD missing it alone was not measured. `WARN_COMPONENT_NAMING` now only flags a LOD whose
  component names are none of them `Component` and a number (e.g. only `Component_01`, a spelling
  never measured); `COMPONENT01` and `Component02` raise nothing. A collision LOD without faces of
  its own (a mass-only Geometry LOD, or one holding only proxy triangles) raises nothing; a
  selection under a proxy name counts as a proxy only with a proxy's shape (1 triangle, selected
  with its 3 corners). Each LOD is checked on its own. Measured offline with the old and the new
  module through `P3D._scan_v12_findings` on 414 unique MLODs (the owner's mod and vehicle projects
  and the Pack's door samples): the old check raised 94 errors, all on Geometry LODs, 88 of them
  with lowercase component names and 5 on Geometry LODs without faces (ruined wheels, one a
  debinarized vanilla `sedanwheel_destroyed`); the new one raises 1, a Geometry LOD with faces and
  no component, and nothing on View or Fire, where every LOD with faces has a component. The v2 test
  fixture's View and Fire LODs, which had no component, get `Component01`. The `dayz-p3d-audit`,
  `dayz-vehicles` and `dayz-clothing` notes on this finding now say which py3d version does what,
  and a knowledge note's claim that Object Builder is case-sensitive is marked as unmeasured. No new
  wheel: the pinned and installed `py3d_dayz-1.8.0` keeps the old check, and `apply-s2-rollout.ps1
  -WheelOnly` refuses to restock until a 1.9.0 wheel is built and pinned.
- The chiral in-game checks that #28 designed for the clothing and animation routes ran, and the
  character check got its attack (2026-10-02, DayZDiag 1.29.163709, one run driven by dayz-mcp).
  `dayz-clothing`: a test garment with an "F" on the left chest, exported with Rule 12, reads
  correctly on the wearer's left chest, opposite the item hand; the old `(x, z, −y)` + 180° + swap
  export reads mirrored on the right chest (worn by a spawned survivor with empty hands, since
  dayz-mcp cannot take a worn item off the player). `dayz-animation-pipeline`: `LeftArm` alone keyed
  in Blender on the official rig and exported through the calibrated Route C script rose on the side
  opposite the item hand; the skill's uncalibrated `scripts/seanim_export.py` left the arm at shoulder
  height. That shows the route keeps the track on `LeftArm` and raises it as keyed. It does not test
  the handedness of the frame change (the bone offsets came from the vanilla clip), nor whether Route
  C's formula, calibrated on the JD rig, fits the official FBX rig's bone frames (turned 90° about Z
  on 105 of 113 bones, within 0.5°): this raise turns mostly about the bone's own Z, so both maps
  raise the arm. `dayz-characters`: the Rule 12 LFInfectedBig build from #34 attacked the player with
  its limbs in place, like a vanilla `ZmbM_SoldierNormal`.
  The `[DESIGN, not yet run]` labels become run results with their scope. `dayz-mcp-verify` gets what the
  run taught: no verb takes a worn item off the player, so a second garment goes on a spawned survivor;
  an infected attacks only once it notices the player; in this run, infected spawned without AI later
  read health 0.
  Four claims registered.
- `dayz-characters` `check_dayz_winding.py`, the pre-PBO gate of the character pipeline, encoded the
  LFInfectedBig det +1 build: stored normals OUTWARD and `cross·normal < 0` (`NORMALS_OUTWARD_MIN =
  0.35`). It exited 1 on all three MLODs of the Rule 12 in-game test, the correct one included, with fix
  hints that would turn it inside-out, and it passed the outward-normal state. It now reads every visual
  LOD in the Rule 12 convention. The winding: the signed volume by winding of each closed shell (points
  welded, faces linked only through edges that exactly two faces share, `proxy:*` faces left out, an
  incoherent shell made coherent first); negative passes, positive is inside-out and gets
  `face.vertices.reverse()` on that shell, on the whole LOD only when every shell reads positive and
  nothing else is in it. The normals: corner by corner per shell, each corner normal against its face's
  vector area as that reversal leaves it, a normal within 5° of the face plane not read; a shell agrees
  above 90 % of its corners (a tolerance: smooth-shaded exports carry corners against their face), below
  10 % in every shell with the winding right means negate the normal pool and keep the faces (the gate
  counts the corners that agree now and that fix turns too, and withholds it when part of the LOD is not
  read), and anything else lists the shells to fix corner by corner. py3d `_pct_normal_agreement`'s
  first-corner count, over every face of the LOD, is printed alongside. Open and flat parts are reported
  as not scored, and a PASS that leaves faces unscored says so; a LOD with no closed shell, or a shell with
  no readable normal, is not measurable (exit 2). Visual LODs above resolution 10 are read too, a defect in
  one LOD now wins over another that is not measurable (exit 1; it was 2), and a missing or wrong py3d
  exits 2 instead of raising. Fixtures next to the script: the three in-game MLODs byte for byte,
  regenerated with py3d 1.8.0, plus the correct one with its normals negated; on them the exit codes go
  from 1, 1, 1, 0 (correct, mirrored, inside-out, outward normals) to 0, 0, 1, 1, and
  `test_check_dayz_winding.py` covers 39 cases. A cross-family review (gpt-6.1-sol, two rounds) showed that
  reading one corner per face passed normals wrong at the other corners, that a pool negation on a
  LOD-wide share turned a right part outward, that the first three corners of a non-convex quad point
  against the face, that the printed py3d count left proxies and incoherent shells out, and that a 0.1 mm
  flatness cut-off passed a thin inside-out part; each is a test now. Offline on the LFInfectedBig builds
  of the 2026-10-02 chiral check, the Rule 12 build passes (99.8 % of its corners agree, 99.5 % in the
  body; its open ribcage tubes, 63.5 % of the faces, not scored) and the two with outward normals fail on
  their normals. The OFFLINE GATE section of `dayz-characters`,
  `character-rigging.md` §6 and the `check_face_winding` docstring of `dayz-model-pipeline`
  `py3d-direct-generation.md` no longer say the gate fails a correct export or that characters use the
  opposite sign. The rewritten gate was not run in game; its verdicts are checked against the recorded
  in-game results of the probe and of the chiral check.
- `dayz-animation-pipeline` `scripts/seanim_export.py` wrote the viewer's bone-local quaternions and
  rest offsets as they are, in the viewer's right-handed frame. It now carries the Route C
  conversion calibrated 2026-06-29 on the JD Master Rig (rotation `(x,y,z,w) → (−y,−z,x,w)`, rest
  offset `(x,y,z) → (y,z,−x)` in cm, exact offline over 73 bone/frame pairs), one map per rig. The
  BI FBX rig that `build_rig_dayz.py` builds has the JD bone frames turned 90° about Z (113 of 114
  rest rotations within 1°, the root excepted): the literal map turns every one of its bone frames
  90° (rest offsets against DayZATool extracts of vanilla clips: 0 of 77 within 5°), so it gets
  `(−x,−z,−y,w)` / `(x,z,y)` instead, derived offline (77 of 77; rest rotations within 0.87° of the
  JD rig's against a vanilla idle). The rig is read from its rest offsets: the bone axis of its
  anatomical chains (helpers such as `RightHand_Dummy` and its child `Weapon_Root` skipped) and the
  roll of `Spine3` and both hands, within 2° of vanilla (both rigs read within 0.07°); any other rig,
  an anim bone missing from the rig and a missing `--rest-pose` file are refused, and an exported
  root bone and per-frame positions are flagged. `--rest-pose` loaded a
  vanilla SEAnim and ignored it; it now emits only that clip's bones, as the project copy does (the
  mask fixed a flop in game on 2026-06-30). Positions always come from the rig: the project copy
  also takes the reference's, but DayZATool marks most bones of vanilla action extracts RELATIVE
  (SEAnim bone modifiers, offsets from rest), so it writes their zeros as absolute offsets. On a
  real JD-rig clip without `--rest-pose` the output is byte-identical to the project copy's. The
  structural round-trip gate checks every bone's rotation and position keys.
  Docs: `blender-authoring.md` "Coordinate handling", `weapon-anim-authoring-viewer.md` (section
  "Route C bone-frame maps, per rig"), `SKILL.md` and `blender-animation`'s `dayz-handoff.md`. In
  game, the JD map played one full-body action wrong (A6_SR2M, 2026-06-30); in-game playback stays
  the gate. Regression test: `tests/test_seanim_export.py` (18 cases).
- py3d `WARN_COMPONENT_COVERAGE` (py3d 1.9.0). It read the Geometry LOD only when it held a
  selection named exactly `Component01`, and compared that selection alone with the whole LOD
  ("Component01 covers 8/48 vertices; uncovered vertices won't participate in collision" on the
  six-component `gate_and.p3d`): it fired whenever `Component01` held fewer points or faces than the
  LOD, as on a healthy LOD with several components (the killer #2 entry above), never read a LOD
  without an exact `Component01` (lowercase components included), counted proxy triangles and points
  that no face uses, and did not run on View or Fire. It now reads the union of every selection
  named `Component` and a number, in any case, on the Geometry, View and Fire LODs: one finding per
  LOD (it raised up to two) counts the faces, proxy triangles aside, that no component holds and the
  points those faces use that none holds; points that no face uses are not counted. A LOD with no
  component (`ERR_COMPONENT_NAMING`'s finding) or only proxy triangles raises nothing; one whose
  component selections are all empty is reported with every face counted. It stays a WARN: in game a
  box with no component collided with nothing (killer #2), but a face outside every component on a
  LOD that has others was not measured. Measured offline with the old and the new module through
  `P3D._scan_v12_findings` on 414 unique MLODs (the owner's mod and vehicle projects and the Pack's
  door samples): the old check raised 78 findings on 39 Geometry LODs, the new one raises 3, and no
  other finding changed. Two of the 3 are the door sample `Expert_Mode`, whose lever (18 faces) is
  in no component in its Geometry and Fire LODs, though `dayz-doors` lists the lever among its
  Geometry parts; the third is a vehicle's Fire LOD with two 1 mm triangles in no selection.
  `dayz-p3d-audit` killer #8 and `references/killers-detail.md` §8 say which py3d version does what,
  name the proxy triangles and points that no face uses as left out, and no longer state as measured
  that a face outside every component does not collide (measured only for a LOD with no component at
  all); the old text is quoted in their dated notes. No new wheel: the pinned and installed
  `py3d_dayz-1.8.0` keeps the old check.
- `dayz-p3d-audit` killer #1 no longer says that inverted collision winding lets the player walk
  through. Measured in game (2026-10-02, DayZDiag 1.29.163709): killer #2's 2 m box against the same
  bytes with every face of its Geometry, View and Fire LODs reversed and their normals negated,
  packed unbinarized and binarized, as an `item_large` `Inventory_Base` and as a `HouseNoDestruct`.
  The outward boxes took no `scene_raycast` ray in `geom`, `view` or `fire` (a cursor-like `view` ray
  went through too), while `DayZPhysics.RayCastBullet` hit them at the same faces as the inward ones,
  every probe box stopped a walking player about 0.36 m before its face, and a player stood on the
  two outward items' tops. A walk does not diagnose the winding either way. The sentence that a
  `dBodyCreateDynamicEx` body "masks inverted collision winding — the object rolls but the player
  walks through it" is replaced, and so are "no collision" in the killer's opening and "physically
  invisible" in its root cause; the old text is quoted in a dated note. `dayz-model-pipeline`'s
  SP-003 note no longer lists "walks through" among the symptoms of collision winding.
- `dayz-p3d-audit` "From Check B to fix" (`references/winding-diagnostics.md`), run on real
  models (2026-10-02). Step 1 said a healthy welded component yields one group: on the SUB_BRZ
  co-driver door (healthy, verified in game) the fill splits a 2,235-face component 2,121 + 114
  with 7 parity conflicts, and the minority follows the order of the fill (6 to 246 faces over
  41 other orders), and a real 30-face patch reversed inside that component came back mixed with
  those 114 (144 faces). Step 1 now counts conflicts: a component with one, or one that splits
  evenly, has no minority group and is inspected with item 2's visibility battery. Cutting the
  edges traversed the same way and filling again found the damaged faces in two constructed cases
  and four intact faces in a third (damage that took in a face of the door's seam), so no fill
  decides it.
  Step 3's branches were written for a part whose normals agree with its winding; on a part in
  the older convention (the door's paint) they pick the wrong side. The part's row is now decided
  first, from its faces outside the group, with the Check A table, never from its normals alone:
  brought to Rule 12, step 1 run again and the group read as written, or, kept in the older
  convention on purpose, read against it; no face outside the group, or MIXED, is inspected. One
  face with no reading stops the whole group, and the closing corner check reads a part kept in
  the older convention with `dot ≤ −0.1` (the healthy door's flags: 26,576 → 441 if all its 11
  such parts are kept). The three GunRacks MLODs of the step's own record go through it as
  before: their 156 faces read ≥ +0.99, and the result matches the files the 2026-08-28 fix saved
  byte for byte once py3d rewrites both.
  Check A's `MIXED` bullet aligned. Old text quoted in dated notes.
- `dayz-p3d-audit`: two passages still spoke of `check_dayz_winding.py` as before its Rule 12 rewrite
  (#53). Killer #1's dated note in `references/killers-detail.md` said the script "fails a correct
  export", and Check A's `UNIFORM_FLIPPED` bullet in `references/winding-diagnostics.md` named it with
  the LFInfectedBig outward-normal recipe. The gate now passes a correct export and fails the
  outward-normal state on its normals (`mirror_b_normals_out.p3d` and LFInfectedBig's outward-normal
  build, measured offline for #53); both passages say what it did then and what it does now.
- `packctl gate` ran only `tests/packctl` and `tools/py3d/tests`, and CI only `tests/packctl`, so
  the other twelve test folders the pack ships (`skills/<skill>/tests` in four skills, eight
  `tools/<tool>/tests`) could go red with both green. One pytest run over the skill folders runs
  nothing either: the four skills ship the same `test_install_py3d.py`, and the default import
  mode aborts the collection ("import file mismatch", exit 2). The gate now runs each
  `skills/<skill>/tests` and `tools/<tool>/tests` folder in its own pytest process (checks
  `skill_tests` and `tool_tests`, findings `SKILL-TESTS-FAILED` and `TOOL-TESTS-FAILED`, a log and
  a run record per folder in the report directory), and `packctl test-folders` runs those checks
  alone (its tools tree includes `tools/py3d/tests`, which the gate checks separately). The gate
  loads a pytest plugin, `packctl/pytest_observer.py`, into each run, and it records the run
  through pytest's hooks. A folder passes when pytest exits 0 or 5 ("no test collected") and that
  record shows no failure, no test deselected, dropped or added after collection, every
  collected test run to the end, and every `test_*.py` or `*_test.py` module of the folder
  either collected or skipping itself at import; exit 5 also needs that skip, which is what
  modules that skip themselves at import (`pytest.importorskip("bpy")` without Blender)
  produce. A failing or uncollectable folder, an empty one, script-style checks, a
  collection-only run, a module kept out of collection by configuration and a run ended early
  fail, and the gate's pytest runs ignore `PYTEST_ADDOPTS`. CI runs `packctl test-folders --tree
  skills`; the tool folders stay gate-only,
  since five of them import packages the runner does not install (jsonschema, numpy, Pillow,
  py3d). They add 4 to 8 minutes to the gate, almost all of it `dayz-vehicle-proxy-contract`.
  Measured on `26e76a4`, folder by folder: 24 skill tests and 629 tool tests pass,
  `dayz-odol-strict` skips 5 without `DAYZ_ODOL_BACKEND_ROOT`, and none of these twelve folders
  needs Blender, DayZ or the P: drive. Test files outside `skills/<skill>/tests` are not run:
  `dayz-realistic-animation-director/scripts/tests` (one of its modules imports `bpy`),
  `dayz-proxy-align/scripts/test_proxy_frame.py` and
  `dayz-mcp-verify/references/test_drive_ladder.py`.
- The four test files the entry above leaves out now sit in their skill's `tests/` folder, where
  the gate's `skill_tests` check and CI run them. `dayz-realistic-animation-director/scripts/tests`
  moved to `tests/` with its `fixtures/`, and `scripts/run_regression_tests.py` reads it there.
  `test_validate_motion_contract.py` stays a `unittest.TestCase` (40 tests and 8 subtests under
  pytest, the same 40 under the runner). `test_sample_blender_motion.py` was a collection error
  without Blender (`No module named 'bpy'`, exit 2), which also kept the 40 beside it from running;
  it now skips itself without `bpy` and has a `test_` entry for where `bpy` imports. It imports
  pytest only on the skip branch: Blender's bundled Python (Blender 5.1.1, Python 3.13.9) has no
  pytest, and the runner still launches the file inside Blender. `dayz-proxy-align`'s
  `test_proxy_frame.py`, module-level checks that collected no test (exit 5), is ten tests behind
  `pytest.importorskip("numpy")`, so the CI runner, which installs pytest only, skips it.
  `dayz-mcp-verify`'s `test_drive_ladder.py` asserts what its `check()` only recorded, so under
  pytest every test passed with a check failing: with R3 mutated to pass on the passenger seat it
  gave 9 passed, and now gives 1 failed. Both keep `python test_<name>.py`, exit 0 = pass, through
  `pytest.main`; `dayz-proxy-align/SKILL.md`, `dayz-mcp-verify/SKILL.md` and
  `acceptance-ladder.md` cite the new paths. Measured with `packctl test-folders --tree skills`:
  six folders pass, also with numpy hidden from the test processes, and the same two mutants fail
  `dayz-mcp-verify` and `dayz-proxy-align`.
- `dayz-characters`' `test_check_dayz_winding.py`, the 39 tests of its pre-PBO winding gate (#53),
  sat in `references/`, outside the `skills/<skill>/tests` folders the gate's `skill_tests` check
  and CI run, so a failing test there turned neither red. It now sits in `tests/` and reads
  `check_dayz_winding.py` and its fixtures where they stay, in `references/` and
  `references/winding_fixtures/`; `SKILL.md` and the gate's usage note cite the new path.
  Measured with `packctl test-folders --tree skills`: seven folders pass, `dayz-characters` with
  39 tests, on Python 3.14.3 and on 3.12.14 with pytest as the only package, as on the CI runner.
  With the gate's `DISAGREE_BELOW` mutated from 10 to 0, `dayz-characters` fails (6 of its 39
  tests), where `main` at `ea7b396` with the same mutant passes its six folders.
- py3d rollout applicator (`tools/py3d/rollout/apply-s2-rollout.ps1`): restocking a skill's
  `wheels/` counted the pinned name and legacy `py3d-*.whl` wheels but not an earlier
  `py3d_dayz-*.whl`, so a 1.8.0 → 1.9.0 restock would copy 1.9.0 beside 1.8.0, pass its own
  readback, and leave a directory the skills' `install_py3d.py` refuses (it wants exactly one
  `py3d_dayz-*-py3-none-any.whl`). Found by the cross-family review of the 1.9.0 pin; no installed
  tree vendors a wheel today, so nothing was affected. Earlier `py3d_dayz` wheels are now backed up
  and removed like legacy ones: a new case in `tests/py3d_rollout/test_apply_rollout.py` and test E
  of `verify-wheel-restock.ps1` fail on the previous applicator and pass now.
- `dayz-model-pipeline` SP-003 no longer tells you to match a collision LOD's winding to the Visual
  LOD. It said to compare the two "(centroid method) BEFORE deploying — they must agree in sign",
  and that `audit_p3d.py` does not validate this. `audit_p3d.py` does run that comparison, py3d's
  relative check (`ERR_WINDING_INVERTED`, through `P3D.validate()`), and since killer #1 was
  rewritten it is a trigger, not the verdict: it also fires on healthy collision LODs under an
  inside-out Visual LOD. Rule 18's per-component check decides (with its prerequisites met, every
  non-proxy face of every component reads inward), only the faces that read outward are reversed,
  their stored normals as killer #1's fix says, and a collision LOD is never reversed to match the
  Visual LOD. The section's title and body say so now, and so do the rule's two other copies: the
  collider recipe in `references/py3d-direct-generation.md`, which called the relative comparison
  "the operational gate", and `dayz-p3d-inspector`'s SP-003 section. The collider recipe also says
  to store the negated `hull.equations` normal on every face, reversed or not: scipy's `ConvexHull`
  returns its faces in no consistent order (measured offline, scipy 1.17.1: 22 of 44 faces of a
  12-gon cylinder wound outward), and the outward normals kept on the faces left alone read 50 %
  agreement in py3d. The old text is quoted in dated notes.
- `dayz-model-pipeline` Rule 18 no longer reverses whole collision LODs. Its body read the
  per-component check on "most faces" and fixed it with `face.vertices.reverse()` on every face of
  every collision LOD, though its own 2026-10-02 note had narrowed both: on a collision LOD holding
  one box wound inward and one wound outward, that loop swaps them (signed volumes by winding -8 and
  +8 become +8 and -8; measured offline, py3d 1.9.0, synthetic 2 m boxes), while reversing only the
  faces that read outward and negating their normals leaves both at -8. The body now carries killer
  #1's prerequisites and fix: every non-proxy face of every closed, convex component reads inward,
  only the faces that read outward are reversed, and a collision LOD is never reversed to match the
  Visual LOD. The two troubleshooting rows that reversed every face say the same; the
  symptom-triplet row also reversed Roadway, whose walkable faces it now sends to `dayz-p3d-audit`
  "Absolute winding check" rule 4, and the Check A row reversed whatever its direction check read
  outward, Visual LODs included: read literally on a closed Visual room seen from inside (signed
  volume +8, right for a room), it gave -8 with 100 % agreement and no py3d winding finding. That
  row now reads a Visual LOD shell by shell, never by the LOD-wide sum, after Check B has turned
  back any face wound against its neighbours (a face turned with its normal inside a closed solid
  left that solid at -5.33 instead of -8 with 100 % agreement, and only py3d's
  `WARN_WINDING_EDGE_INCOHERENT` saw it), and by the side meant to be seen: negative for a solid
  seen from outside, positive for a room seen from inside (rule 4); open or double-sided Visual
  parts stay unresolved by that sign. In `references/py3d-direct-generation.md`, the "Face Winding
  Order Fix" loop, which reverses every face of every LOD, proxy triangles included, is marked as
  the undo of a whole-model `P3D.transform()` reversal, its one use, and the section says how a
  collision LOD is repaired instead. Rule 18 also pointed at `check_face_winding` as its
  implementation: that function compares winding with stored normals on the first LOD only, and it
  returned no finding on a model whose first LOD is the Memory LOD over an outward collision box,
  nor with that box stored first (measured offline the same way). Rule 18 now says no function of
  the skill runs its check, and `check_face_winding`'s section says what it reads. The old text is
  quoted in dated notes.
- `dayz-model-pipeline` `references/lods-and-geometry.md`, the py3d fix for the GLB/glTF source
  case: the bullet above it reverses every face in every LOD except proxy triangles, but the loop
  under it reversed the proxy triangles too. The loop now keeps the order of each proxy triangle,
  the only face of a `proxy:<path>.<index>` selection (`py3d.PROXY_NAME_RE`) when it is a
  triangle, entries of weight 0 not counting, and reverses every other face once: a selection
  under a proxy name with more faces, or a quad, holds geometry and is reversed with the rest, and
  a vertex list that would be reversed twice (one `Face` listed twice, or two faces sharing one
  list) stops the loop before any face changes. A sentence says that `P3D.transform()` with the
  swap matrix (det<0) has already reversed every face, proxy triangles included, so after it only
  the proxy triangles go back; run after `transform()`, the loop would put every other face back
  in its original order and leave the proxies reversed. Measured offline with py3d 1.9.0 (the
  repository source and the installed wheel), running the documented block itself on synthetic
  models: the proxy triangles keep their order, one whose selection lists no points and one with a
  weight-0 entry beside it included, and every other face is reversed, a box and a quad under
  proxy names included, also after an MLOD write and read; a repeated `Face` or a shared vertex
  list raises with nothing changed; the old block, a loop that skips every face of a proxy-named
  selection and a no-op fail. On 411 MLODs of the owner's projects (13,688,834 faces, read only)
  the block raised on none, kept the 1,979 faces that are the single triangle of a proxy-named
  selection (191 of them in debinarized SUB_BRZ round trips whose proxy selections list no
  points) and reversed every other face once, the 108 faces of 18 six-face proxy-named selections
  in the LFPowerGrid logic gates' collision LODs included. The replaced block is quoted in a dated
  note. The GLB reversal itself is unchanged.
- `ai-3d-to-dayz` SP-071 no longer reverses every visual face of a Blender, OBJ, glTF or FBX
  import, and its census no longer reads a correct export as inverted. It said to reverse "every
  **visual** face" whenever the measured axis transform preserves winding, a det=+1 map: the recipe
  `dayz-model-pipeline` Rule 12 replaced after the in-game test of 2026-10-01, where that map with
  reversed faces rendered solid but mirrored. Every route of the skill reaches the MLOD as geometry
  authored in Blender, so it now takes Rule 12's FBX / Blender-authored recipe, whatever format the
  generator wrote (det=-1 map, faces in their order, normals negated); on that route LFInfectedBig,
  an AI-generated GLB retopologized in Blender, read correctly in game with Rule 12's map and
  mirrored with the det=+1 map and reversed faces (`dayz-characters`
  `references/character-rigging.md` §6, 2026-10-02). SP-071 had one calibration, the LFHeli OH-1 of
  2026-07-19: an artist's Blender model exported as OBJ, mapped with `x'=x, y'=z, z'=-y` (det=+1),
  every visual face reversed, and judged by its render side only. The reversal now needs a source
  lineage measured by an in-game A/B plus a chirality check. The census thresholds (at least 95 %
  negative `SOLID`, positive-dominant `INVERTED`) came from that pipeline's outward stored normals.
  Measured offline on the MLODs of the Rule 12 in-game test, which `tools/py3d/tests` rebuilds byte
  for byte, the export that rendered solid and read correctly reads 0 % negative, `INVERTED`, while
  the same export with every face reversed (inside-out) and SP-071's recipe (a mirror) read 100 %,
  `SOLID`. The section now sends a Rule 12 export to `dayz-p3d-audit`, whose signed volume is read
  per closed shell, never summed over the LOD, and says that the in-game A/B cannot see a mirror.
  `dayz-vehicles` invariant #10, whose generic-DCC case said "flip visual by default (SP-071;
  proxies exempt)", points to Rule 12 too. The old text is quoted in dated notes. Docs only;
  nothing re-measured in game for this change.
- `dayz-model-pipeline`: the GLB/glTF import path no longer reverses faces. `SKILL.md` (section
  "GLB/glTF imports — LL-020 refined", Rule 12's GLB bullet, the Rule 13 note, two troubleshooting
  rows and SP-071's glTF clause), `references/lods-and-geometry.md` (the rule, its py3d and Blender
  fixes and the all-LODs paragraph) and `knowledge/DAYZ_TECHNICAL_NOTES.md` (root cause, canonical
  fix, first rule) said that a GLB/glTF source mapped with the pure swap `(x,y,z)->(x,z,y)`
  (det=-1) needs every face reversed except proxy triangles. glTF front faces are CCW like
  Blender's, and Blender's glTF importer maps Y-up to Z-up with a rotation (det=+1, Blender 5.1
  `io_scene_gltf2/blender/imp/blender_gltf.py:70-72`), so after the det=-1 map the cross product
  already points inward, the MLOD convention Rule 12 measured in game on 2026-10-01; the reversal
  turned it outward, which renders inside-out. Two GLB/glTF-origin projects measured it in game:
  MercedesAMGLF (2026-06-24) rendered see-through with its faces reversed after a det=-1 map and
  solid with the glTF order kept (the case `dayz-vehicles` `references/vehicle-structural-parity.md`
  records), and A6_MK47 v12c (2026-06-11, binarized) rendered correctly with the pure swap,
  negated normals and no reversal, the rule `dayz-weapons` `references/import-rule-v4.md` already
  carried. The reversal dated from A6_MK47's v6-v7 stage (the Pack's v1.3.0 text still called its
  v7 in-game re-test pending), when that project's builds shipped a stray raw MLOD at the PBO root
  and the engine loaded that file. A GLB/glTF exported to spec and brought through
  Blender now takes Rule 12's recipe (`py3d.blender_to_dayz()`); a glTF read without Blender bakes
  its node transforms, reversing the faces of mirrored instances (glTF winds them clockwise, glTF
  2.0 §3.7.4), derives its own det=-1 map from the asset's frame and keeps that order (not tested
  in game), and ripped `.glb` assets stay with `dayz-vehicles`. A mirrored node brought through
  Blender arrives there as an object with negative scale; the text marks that case as not checked
  and points to `check_dayz_winding.py` to read the exported part. `lods-and-geometry.md` also drops
  "Flipped Geometry faces cause physics pass-through": `dayz-p3d-audit` killer #1 measured outward
  2 m collision boxes that the LOD raycasts miss while physics still stops a walking player, and a
  walk alone does not diagnose winding. The py3d block that the entry above had just made keep
  proxy triangles goes too: no face is reversed now, and after `P3D.transform()` every face goes
  back, proxy triangles included; that block is quoted in the dated note. `check_face_winding`
  could not catch the old recipe (it reads only whether the cross product and the normals
  agree), and the texts now say so.
  Documentation only: nothing was re-measured in game for this change. Every replaced passage is
  quoted in a dated note.
- py3d `ERR_WINDING_VS_NORMALS` and `ERR_WINDING_INVERTED` (py3d 1.10.1): both closed with "negate
  each corner normal that still points against its face", and the README's "Winding" step 3 said
  to go corner by corner. A corner normal smoothed across a sharp fold can point against a face
  wound right, so that step turns right normals, and `dayz-p3d-audit`'s
  `references/winding-diagnostics.md` ("From Check B to fix", item 3) rules it out. Measured
  offline in py3d's tests: a flat tetrahedron wound right, with one area-weighted normal per
  point, has 6 of its 12 corners against their faces and reads 75 %
  (`WARN_WINDING_NORMAL_MISMATCH`); the per-corner step turns those six normals through three pool
  copies and takes it to 100 % with no finding. Both messages now close with one normals step,
  part by part, never a corner on its own sign, and step 3 says how a face and a part read: a face
  by the average of its corner normals against its vector area (with its winding at ≥ 0.5, against
  it at ≤ −0.5, no reading in between, or with a corner normal that is zero or whose dot has the
  other sign or lies within 0.1 of zero); a part reads cleanly when every face of it has a reading and its larger group of faces
  wound alike reads all one way, and there the faces that read against their winding have their
  normals negated and the rest are kept; any other part is left as it is, to inspect. On the
  fixtures of every test that used the old step (the F of the Rule 12 in-game test with its
  normals turned, its faces turned, a shared pool, a plate face turned back and an odd face, and
  the multi-LOD model with its visual or geometry LOD inside-out) the new step gives back the clean
  model, and on the tetrahedron it changes nothing. Where it is more cautious it changes nothing
  and leaves the part to inspect, while the old step had fixed it: only each face's first corner
  turned, on flat normals, and a smoothed box whose shared entries were negated in place. Codes,
  severities and the checks are unchanged; the pinned 1.9.0 wheel still prints the old step.
  `dayz-characters` `check_dayz_winding.py` cited step 3 for its own per-corner fix: its fix for
  the shells between 10 % and 90 %, and the by-hand alternative to its pool fix, now read the
  shells part by part (its measurement, thresholds and exit codes are unchanged), and `SKILL.md`
  "OFFLINE GATE" says so, with the old text quoted in a dated note.
- `dayz-p3d-audit` "Absolute winding check", rule 5: when the winding was the wrong side, it
  reversed every face of every LOD, which on a model whose LODs are not all wrong moves the
  inversion onto the healthy ones, against killer #1 and rule 7. It now reverses only the faces
  the direction check of their kind reads wrong: Rule 18's per-component check on a collision
  component (prerequisites as killer #1 says), the signed volume of each closed Visual shell, read
  after Check B, against the side meant to be seen (an open or double-sided part has no sign), and
  rule 4's sign on walkable Roadway faces. The stored normals of those faces are read before the
  reversal with the Check A table, part by part (a group inside a part face by face, as "From
  Check B to fix" step 3 reads it), and a part with no clean reading keeps them; never by one
  corner's sign, which smoothed normals turn against faces that are right. Every face of every
  LOD only inside a whole-model operation, undoing the reversal `P3D.transform()` applies for a
  det<0 matrix or rule 8's reflection. The normals branch negates the whole pool only when every
  part of the LOD reads the table's third row, as on the LFSecure exports the rule was written
  for, and otherwise only those parts, through a negated copy of any entry a kept corner also
  uses. Measured offline (py3d 1.9.0, synthetic models): a correct exterior Visual LOD (signed
  volume −8) over a Geometry box wound outward (+8) ended at Visual +8 and Geometry −8 under the
  old rule, `ERR_WINDING_INVERTED` still raised, and at −8 and −8 with no winding finding under
  the new one; on an export with every face of every LOD reversed, the two write the same faces
  and normals; in a Visual LOD whose healthy and broken boxes share six pool entries, negating the
  whole pool left 24 of 48 corners agreeing and turned the healthy box's normals, where six
  negated copies for the broken box left 48 of 48; a flat tetrahedron with area-weighted normals
  has 6 of its 12 corners against their faces while healthy. The old sentence stays quoted in a
  dated note. Finding R21-ALIGN-01 of the cross-family review of #67; the normals rules answer
  this change's own review (two rounds).
- `dayz-model-pipeline` SP-071 ("Generic DCC visual-winding profile") no longer reverses every visual
  face of other raw OBJ imports, and its census no longer reads a correct export as inverted. The
  section said to reverse the vertices of every **visual** MLOD face of a raw OBJ whose measured axis
  transform preserves the source winding, a det=+1 map; from Blender's right-handed coordinates any
  det=+1 map mirrors the model, as Rule 12 measured in game on 2026-10-01. Every lineage the Pack
  records with that reversal started from Blender coordinates: SP-071's one calibration, the LFHeli
  OH-1 of 2026-07-19 (an artist's Blender model exported as OBJ, mapped with `x'=x, y'=z, z'=-y` and
  judged by which side rendered), LFInfectedBig, which read mirrored in game (`dayz-characters`
  `references/character-rigging.md` §6), and the SP-432 recipe. An OBJ exported from Blender with
  Forward Y / Up Z now follows Rule 12 as it stands, an OBJ in any other frame of a right-handed
  counter-clockwise source takes a det=-1 map derived from that frame with its faces in their order,
  and the reversal needs a source lineage measured by an in-game A/B plus a chirality check, as
  `ai-3d-to-dayz` SP-071 says. The census thresholds (at least 95 % negative `SOLID`,
  positive-dominant `INVERTED`) came from the OH-1 pipeline, which stored its normals outward against
  an inward winding: measured offline on the MLODs of the Rule 12 in-game test, which
  `tools/py3d/tests` rebuilds byte for byte, the export that rendered solid and read correctly reads
  0 % negative, `INVERTED`, while the same export with every face reversed (inside-out) and SP-071's
  recipe (a mirror) read 100 %, `SOLID`. The section now says the census reads stored normals against
  winding, sends a Rule 12 export to `dayz-p3d-audit` (agreement, then the signed volume per closed
  shell) and says the in-game A/B cannot see a mirror. The Path A note on imported vehicles no longer
  names a generic flip default, and in `dayz-characters` the LFInfectedBig case-log entry that gave
  "reverse every visual face" as the inside-out fix carries a dated note: the det=+1 map caused the
  inside-out render, and the reversal hid a mirror (`references/character-rigging.md` §6, in game
  2026-10-02). The old text is quoted in dated notes. Docs only; nothing re-measured in game for this
  change.
- packctl: in the middle of a merge, `git_tracked_files` (`packctl/common.py`) listed a path in
  conflict once per index stage, up to three times, as `git ls-files` prints it. It now lists each
  tracked path once, still sorted. None of its callers needed the repeats: `validate`'s link check
  reported a broken link in such a Markdown file three times, the gate passed such a Python file to
  `py_compile` three times and counted it three times, and `build`'s symlink check would repeat its
  finding; the source-map, privacy and conflict-marker checks read the list through a set, and
  `promote` refuses a dirty tree before it lists a route's files. Two tests in
  `tests/packctl/test_validation.py` leave a merge unresolved: the list and the link check fail on
  the old function and pass now.
- `tests/packctl/test_promotion.py`: on a Spanish-locale Windows host, the eight tests that create a
  directory link (nine runs, one test being parametrized) passed with a
  `PytestUnhandledThreadExceptionWarning` per link. Without Developer Mode `try_dir_link` falls back
  to `cmd /c mklink /J`, cmd writes its message in the console code page, the OEM one unless the
  console runs UTF-8 (cp850 here: `UnicodeDecodeError` on byte `0xa2`, the `ó` of `Unión`), and the
  helper decoded it as UTF-8 in subprocess's reader thread. It now keeps the output as bytes and
  reads only the return code. Under `-W error::pytest.PytestUnhandledThreadExceptionWarning` the nine
  runs go from failed to passed (in a console at code page 65001 both versions pass). CI never
  showed it: its `tests/packctl` step on `ea7b396` reports 359 passed and no warning.
- `dayz-test-ingame`, "Testing a mod that is not in the allow-list": project `DayZ_MCP` works as a
  carrier. The bullet said `@DayZ_MCP` could not carry other mods (its `5_Mission` failed with
  `CParser: quoted string not closed`, SP-128, 2026-07-28). On 2026-10-02 (DayZDiag 1.29.163709) it
  carried two extra mods in run `13cc2542` and four in run `1c289781`, and both peers compiled every
  script module (`Module: Mission; loaded 217x files; 540x classes`, no `CParser` line). Ten minutes
  before `13cc2542`, `LFPowerGrid`, the carrier the bullet recommended, carrying `@DayZ_MCP` and the
  same two mods, stopped at `Can't compile "Mission" script module!` on an error in its own
  `5_Mission` (run `f1afd2c3`). The bullet now says to check the carrier's `Module: Mission` line on
  the day, and quotes the replaced sentence in a dated note.
- `dayz-mcp-verify`: `telemetry_read(mode="object_at")` reads any classname, and
  `vehicle_prepare_fixture` any `CarScript`. SP-152 said object telemetry only took
  `type="MERCEDES_AMGLF"`. On 2026-10-02 `object_at` answered `telemetry.found=1` for `KP_CharAB_V1`, the
  vanilla `ZmbM_SoldierNormal` and `KP_CharAB_V3`, and the loopback checks `type` only for a non-empty
  string. The oldest copy of the tools on disk (2026-07-25) had the `MERCEDES_AMGLF` check only in the
  `vehicle_prepare_fixture` branch, and the tools' 2026-08-16 release has none: between 2026-08-18
  and 2026-10-01 that verb returned `vehicle_fixture_ready=1` on 15 other `CarScript` types, which
  the 2026-07-18 server-side conditioning section and `dayz-aviation`'s tooling note also denied.
  The zombie-command bullet now reconciles a lost spawn with `object_at` instead of logs and user
  inspection. The replaced sentences are quoted in dated notes.

## [1.5.0] - 2026-10-02

The Blender→DayZ map end to end: py3d 1.8.0 `blender_to_dayz()` and the deprecation of
`BLENDER_TO_DAYZ`; Rule 12 carried into the character route (measured in game), the clothing,
animation and model-pipeline routes; Check A labels aligned with it; and packctl promotion
unblocked for schema-1 receipts sealed in a checkout that no longer exists.

### Added

- `dayz-mcp-verify`: gating a PR through an external executor. A programmatic swap of Windows
  paths inside its TOML config edits TOML escapes, not path bytes (`TOMLDecodeError: Invalid hex
  value` in preflight); parse the rewritten TOML with `tomllib` and compare the decoded path with
  the intended one before handing it over. Check the deployed PBO against the sealed baseline
  before planning the gate. Measured in one aborted gate run; written first in an installed copy,
  ported here.

### Deprecated

- py3d `BLENDER_TO_DAYZ`: same value, now also published as `ROT_X_NEG90`, and every read
  raises a `FutureWarning` pointing at `blender_to_dayz()` (see Fixed).

### Fixed

- py3d 1.8.0: the documented Blender → DayZ path mirrored the model. `transform(BLENDER_TO_DAYZ)`
  applied the det=+1 rotation `(x, z, -y)`; Blender is right-handed and DayZ left-handed, so the
  model came out mirrored, and that call alone also inside-out. Measured in game on 2026-10-01
  (DayZDiag 1.29.163709) with one chiral model written three ways (the test behind Rule 12 in
  1.4.0). The new `blender_to_dayz(p3d)` applies the det=-1 swap `(x, z, y)`, keeps the face
  order and negates the normals; it writes, byte for byte, the MLOD that rendered solid and read
  correctly. A second probe the same day measured what the first left out: collision LODs
  converted with it register raycasts in `geom`, `view` and `fire` (the uncorrected det=+1 map:
  none), and static proxies drawn in Blender as py3d canonical triangles come out with the ODOL
  frames of `add_proxy(space="engine")` and render in the pose drawn. The binarized files with
  Blender-drawn and with engine-space proxies are byte-identical, so a crew or wheel proxy drawn
  that way with the identity frame gets the frame of the engine-space path a py3d-built motorbike
  was driven with: an equivalence of the proxy frame, not a drive through `blender_to_dayz`.
  Wheel `py3d_dayz-1.8.0-py3-none-any.whl`, SHA-256
  `e718442962df8f2d710fafd9ba9406d61f0c9a844b0f2ed40d5415862bcec304`; no installed skill tree
  vendors the wheel any more, and the site-packages install follows the merge.
- Rig handedness: the det=+1 Blender→DayZ maps that Rule 12 retired were still taught on the
  character, clothing and animation routes. `dayz-characters` (`character-rigging.md` §6): the
  official rig's `R⁻¹ = (x,z,-y)` lands in the FBX's own right-handed frame, not in the DayZ bind,
  so a rigged mesh exports with Rule 12's `(x,z,y)`, the map of `py3d.blender_to_dayz()`; this
  explains LFInfectedBig walking backward with `(x,z,-y)` and mirrored with `(-x,z,y)`.
  `check_dayz_winding.py` predates Rule 12 and fails a correct export (measured on the Rule 12
  probe); the gate to use instead is named. `dayz-clothing`: the "rotate 180° + swap L/R" worn
  fix keeps a mirror (ArmorHneck's p3d was a det=+1 export); the artist-handoff script
  `export_clothing_fbx.py` now uses the self-inverse `(x,z,y)` (offline round trip exact, faces
  outward in Blender); `autofit-from-official-rig.md` drops the face reversal and the
  mirrored-frame alternative. `dayz-animation-pipeline` and `blender-animation`: the viewer's
  `(x,z,-y)` is a rotation into a right-handed frame and is relabelled; geometry
  cross-references now point at Rule 12. Chiral in-game checks are designed for each route, not
  run. `check_dayz_winding.py` is scoped by the sign of the stored normals, not by the
  determinant: a det=+1 build with inward normals also fails it, and reversing its faces would
  turn it inside-out. Fixing a received worn p3d depends on its state: `z → −z` as received,
  `x → −x` with the L/R swap undone once it was rotated and swapped. `dayz-model-pipeline`: the
  headless OBJ export recipe exported Y-up (`(x,z,-y)`) before py3d applied Rule 12, and
  `blender-workflow.md` gave Forward -Y, a 180° turn; both now export Blender's own coordinates
  (Forward Y / Up Z, measured in Blender 5.1.1), and the four documented `wm.obj_export` calls,
  which Blender 5.1.1 rejected with `TypeError`, use its parameter names. Its troubleshooting
  row for Check A's `UNIFORM_NON_FLIPPED` reversed every face; a correct Rule 12 export reads
  exactly that, so the row now asks for a direction check (signed volume or the per-component
  check of Rule 18) first.
- `dayz-characters`: the chiral in-game check of the character route ran (2026-10-02, DayZDiag
  1.29.163709, LFInfectedBig rebuilt three ways from one dump with an "F" on the chest). The Rule 12
  build (`py3d.blender_to_dayz()`) is solid, reads the F correctly and is lit like a vanilla zombie.
  The state `check_dayz_winding.py` passes, MLOD winding with the normals stored OUTWARD, is solid
  but lit inverted (base shading, untextured client), and so is the shipped LFInfectedBig, which
  also reads the F mirrored. In the
  binarized files only the Rule 12 build keeps vanilla's relation between normals and winding. The
  docs now say to store normals inward on characters too, gate with dayz-p3d-audit's absolute check
  (it passes the Rule 12 build and fails both inverted ones), and read a PASS of
  `check_dayz_winding.py` on an outward-normal build as a lighting defect; a symptom row is added.
- packctl `promote`: schema-1 receipts sealed in a checkout that no longer exists stopped every
  `--check` (`PROMOTION-RECEIPT-JOURNAL-MISMATCH` on all nine receipts) and would have stopped
  the pre-apply journal sweep (`PROMOTION-RECOVERY-REQUIRED`). Such a receipt is now read from
  a checkout whose HEAD tracks it at `promotions/receipts/<id>.json` with the same raw bytes,
  only while its sealed path is gone, and it is still matched against the sealed plan and the
  COMMIT receipt hash. It explains only the concrete target paths it wrote that the check
  writes again, under this installation's roots. `promotions/adjudications.json` adjudicates
  the live `dayz-motorbikes` copy, which no receipt explains, for replacement by this version.
- `dayz-p3d-audit` Check A labels (`references/winding-diagnostics.md`): `UNIFORM_FLIPPED` was
  called the expected state after a Blender export and `UNIFORM_NON_FLIPPED` a skipped handedness
  step. Rule 12 writes the cross product and the stored normals both inward, so a correct export
  reads `UNIFORM_NON_FLIPPED`; `UNIFORM_FLIPPED` is the older outward-normal convention (it renders
  solid, and the 2026-04-25 Crate_Wooden in-game check stands) or a correct export with its faces
  reversed afterwards. Measured offline on the three MLODs of the Rule 12 in-game test, Check A
  reads `UNIFORM_NON_FLIPPED` on all three, the inside-out one included, so the item now maps
  agreement (counted on the same averaged normal), and the direction of the cross product relative
  to the side meant to be seen, to a state and a fix. The direction is decided per closed shell,
  faces linked only through edges that exactly two faces share (signed volume by winding on the
  visual LOD, where a LOD-wide sum hid one inverted box of four and a union through every welded
  edge moved the inversion onto a healthy box; Rule 18's per-component check on collision LODs),
  and `proxy:*` triangles stay out of the census and the fixes. The same file's
  centroid-check note no longer gives a correct model outward normals, and its pointer to Check A
  in `audit_p3d.py`, which has none, now names the check the script does run. Two other passages
  taught the old reading and are corrected: the `dayz-p3d-audit` decision tree asked for outward
  collision winding and swapped `verts[1]`/`verts[2]` when inward (it now reverses only the
  outward component), and `dayz-model-pipeline`
  `py3d-direct-generation.md` said any disagreement between winding and normals renders
  inside-out.

## [1.4.0] - 2026-10-01

DayZ 1.30 Experimental (1.30.164014) coverage across the pack, three new skills since 1.3.0
(`dayz-environment-hazards`, `dayz-underground`, `dayz-motorbikes`), the Blender→DayZ axis map
settled in game (`dayz-model-pipeline` Rule 12), the whole pack in English, the offline Enforce
linter at the source, Windows CI, and the author's pending skill-patch and lesson backlog
harvested into the governed skills.

### Added

- `dayz-motorbikes` (new skill), DayZ 1.30 Experimental (1.30.164014): single-track
  vehicles — `MotorbikeScript`, `simulation = "motorbike"`, two-wheel physics without
  `Axles`, kickstand and kickstart actions, the dedicated 3rd-person camera, the 1.30
  vehicle component refactor, rider animation and the vanilla P3D anatomy of
  `Motorbike_01`/`Motorbike_02`. Adopted from the author's live store; Spanish passages
  translated to English and machine-specific paths removed, with a mechanical gate that
  every code span, number (by value), link and heading survived (#16).
- Backlog harvest from the author's pending skill-patch ledger and lessons:
  - `enforce-script-reference` (#17): `%` only in integer context (hard rule 13);
    `Bottle_Base` liquid-action inheritance (rule 40); `ActionEmptyBottleBase` loop
    callbacks (rule 41); custom cookware, `Cooking.CookWithEquipment` and the
    cooling-fireplace double cook; client-local cable segments; field visibility when a body
    moves between script modules. Claims `CLAIM-ENF-MODULO-INT-ONLY`,
    `CLAIM-ENF-BOTTLE-LIQUID-ACTIONS`, `CLAIM-ENF-COOKWITHEQUIPMENT-HUB`,
    `CLAIM-ENF-EMPTYBOTTLE-LOOP-OVERRIDE`.
  - `dayz-model-pipeline` (#17): cookware model origin and heat-source anchor heights;
    the py3d `validate()` `_axis` heuristic; the client-local cable segment model.
  - `dayz-texture-pipeline` (#17): a config `hiddenSelectionsTextures[] = {""}` hides
    the selection.
  - `dayz-vehicles` and `rip-vehicle-import` (WP-VEH): the base seat→door table of
    `GetDoorConditionPointFromSelection` is the left-hand-drive mapping, so a
    right-hand-drive car needs the crossed override (claim `CLAIM-GETIN-LHD-BASE-TABLE`);
    a blank inventory preview when `invview` sits at the bounding-box centre (claim
    `CLAIM-INVVIEW-VIEW0-DEF`); the dashboard-light index has one writer
    (`UpdateLightsServer`, claim `CLAIM-DASHBOARD-LIGHT-RESYNC`) and coincident body/proxy
    faces with different materials flicker; a static proxy animates none of its pieces;
    sliding-plate tile margins, collapsed UVs in decimated LODs, the free-edge gate and
    the opening sense, and moving a whole wheel corner to change the track.
  - `dayz-motorbikes` (WP-VEH): shrink a lowered damper box around its own centre; log
    contacts server-side before tuning.
  - Models, textures and proxies (WP-VMOD): DayZ 1.30 vanilla P3Ds are ODOL v56 (1.29:
    v54) — read header bytes 4-7 before extracting (claim `CLAIM-ODOL-V56-130`, in
    `dayz-vehicles`, `dayz-model-pipeline`, `dayz-pbo-reverse-engineering`); crew-proxy
    frames beyond identity and the upright rider (`dayz-proxy-align`); satmap tile overlap,
    multi-atlas paint variants and `_as` encoding (`dayz-vehicles`,
    `dayz-texture-pipeline`); see-through triage from the real first-person camera, two-sided
    sheets, and control pieces for new ODOL gates (`dayz-p3d-audit`, `dayz-model-pipeline`).
  - Testing and building (WP-TEST): an unpacked `-mod` does not merge its `config.cpp`
    (world configs need a packed PBO); `class Missions` keeps a dedicated server alive
    without a client; registry views under a sandboxed (MSIX) launcher; which Steam account
    is logged in and whether it owns DayZ; a stage path that repeats the addon folder name
    packs a model-less PBO with exit 0; binarized ODOL judged by content; idle `cmd /K`
    windows from `cmd /c start`; a third-party graph mod crashing a 1.30 Exp server
    (`dayz-test-ingame`, `dayz-pbo-build`, `dayz-animation-pipeline`).
  - In-game bridge (WP-MCP): a locked Windows session fails `capture_screenshot` with
    `capture_backend_failed`; a `proto native` declaration does not prove the function is
    linked (`GetFPS` in DayZDiag 1.29); an adopted run's lease lasts 120 s and needs
    `session_heartbeat`; a native setter without a getter must not become a DTO field
    (claim `CLAIM-ENFORCE-NO-GET-TIMEMULTIPLIER`); archive a file-driver case directory and
    never re-run an answered command (`dayz-mcp-verify`, `dayz-test-ingame`,
    `enforce-script-reference`, `knowledge/dayz-mcp-bridge-protocol.md`).
  - Animation (WP-ANIM): measured authoring corrections (the vanilla aux-helper rule, the
    lossy Workbench compile, exporter constraints, no arm IK during continuous actions, the
    quaternion-sign split), syncing an object's pose to a continuous action, and the
    ~22 mm vanilla grip (`dayz-animation-pipeline`); physics truth 10 — config-driven
    animated building geometry is not a mover (`dayz-physics-engine`); `model.cfg` rotation
    sign and chained segments; raising a crop's `varStackMax` changes its harvest yield
    (claim `CLAIM-HARVEST-YIELD-STACKMAX-130`, `dayz-basebuilding`).
  - Models, persistence and QA (WP-MISC): LL-504's in-game measurement that a det=+1
    Blender→DayZ position map ships a mirrored model (claim `CLAIM-BLENDER-DAYZ-DET-NEG1`;
    Rule 12's det=+1 map is flagged for re-review); parts contained between LODs are
    recomputed per LOD; procedural face textures binarize to an undrawn section
    (`dayz-model-pipeline`); a storage copy without the CE anchor files loads nothing, and
    live cargo must not be walked by a frozen index (`dayz-persistence`); vanilla house
    furniture is proxy geometry, made interactive by replacing the model by path (claim
    `CLAIM-FURNITURE-FRIDGE-CLASS`, `dayz-doors`); `ExtractPbo -R` and friends
    (`dayz-pbo-reverse-engineering`); visibility by area sampling (`dayz-p3d-inspector`);
    inventory census before an audit (`rigorous-data-audit`); photo-resemblance scoring and
    animated-part clearance (`blender-visual-review`).
- Moving platforms and edited vanilla rocks (SP-450, SP-451, measured 2026-10-01):
  physics truth 11 — a platform that is a separate entity carries players and vehicles, with
  the vehicle mode that works, the frame hook that fires (`GetUpdateQueue(CALL_CATEGORY_GAMEPLAY)`)
  and the one that never reaches a `House` (`EOnFrame`) (`dayz-physics-engine`); three traps
  when driving a client by MCP (`dayz-mcp-verify`); editing imported vanilla rocks — double
  shell, triangle soup, a height field for inner faces (`dayz-model-pipeline`); checking moving
  mechanisms over their whole travel and sweeping sub-frame collisions (`blender-assembly`);
  absolute render paths under `blender -b` (`blender-visual-review`) (#26).

- `dayz-underground` (new skill), DayZ 1.30 Exp (1.30.164014).
  - Terrain holes: the `CfgWorlds >> <world> >> Holes >> <group> >> tiles[]`
    format taken from Livonia's config, the read-only `SurfaceIsHole(x, z)`,
    and why a tile is a heightmap cell (6.25 m on Livonia, cross-checked
    against the vanilla Dambog triggers).
  - Evidence that holes live in the world config: the `.wrp` of both
    Chernarus and Livonia moved from OPRW v29 to v32 and grew about 5 % on
    each, with or without holes.
  - Underground triggers: the JSON schema, the 256 to 4096 limit, and
    triggers tied to Object Spawner objects.
  - The underground presence the client now reports to the server.
  - The Badlands bunker-broadcast and irrigation-tunnel scripts.
  - Source-verified against the 1.30.164014 scripts; in-game behaviour is
    unverified and listed as such (claims `CLAIM-UG-*`).
- `dayz-basebuilding` §9 of the 1.30 reference.
  - The `Construction{}` activation check (`EntityAI.c:248-249`).
  - The per-part keys 1.30 reads: decay, `StaticsSupportData`, `EffectsData`,
    `custom_part_type`, `skipOnRepair`/`skipOnDismantle`.
  - Door locks on rebuilt buildings.
  - Rebuildable Nasdara buildings ship as scripts only in the Exp build.
  - `ECE_OBJECT_SPAWNER` (claims `CLAIM-BB-*`).
- `dayz-script-validator`: two tree-level checks, both derived from failures
  observed on a running server on 2026-09-17 rather than from review opinion.
  - `ES-PROTECTED-CROSS-MODULE` (FAIL). Enforce enforces `protected` across
    script modules: a class compiled into `5_Mission` cannot read a protected
    member declared by a `4_World` class, and the whole Mission module aborts.
    Verified at runtime with a disposable probe built into a PBO and booted
    (claim `CLAIM-ENFORCE-PROTECTED-CROSS-MODULE`). The check resolves the
    receiver's declared type before firing; a first version matched on the
    member name alone and produced 164 false positives on a tree that compiles
    clean, because one name was protected on an entity and public on an
    unrelated data class.
  - `ES-EXTERNAL-CONSUMER-MISSING` (FAIL), enabled by the new repeatable
    `--external-scripts DIR`. Script that lives outside the addon -- a mission
    `init.c`, another mod -- can call an addon class's methods, and no in-addon
    check sees it. A refactor removed 62 facade methods after proving no file
    under the addon's own `scripts/` called them; the offline linter, the
    implementer's gates and an independent review were all green, and the
    server then refused to compile the mission
    (claim `CLAIM-ENFORCE-EXTERNAL-CONSUMER-SURFACE`). The check only judges a
    receiver whose whole base chain is declared inside the addon, so
    vanilla-inherited and `modded class` methods stay silent. Measured against
    the real trees: 69 errors on the broken one, zero on the fixed one.
  - Paths are never hardcoded: external roots arrive by argument.
- `dayz-mcp-verify`: driving-bench traps measured on 2026-09-13 (SP-423): a
  `world_spawn` car outlives a dead run unless created with `flags=8389668`, get-in
  can seat a nearby car and still answer `ok`, the drive controller skipped gears before
  dayz-mcp `d065b0e`, and old trace dumps need the reader revision they were recorded with.
- `dayz-vehicles`: straight-line sensitivities of the vanilla sedan (SP-424): launch
  acceleration scales as torque^0.93-0.95, tyreGrip 0.70-1.00 leaves launch and braking
  unchanged, and the first upshift matches the gear-ratio formula within 1.4 %.
- Promotions that had stayed on side branches: `dayz-test-ingame` (an unfocused DayZDiag
  client runs at ~20 fps, SP-391), `dayz-pbo-build` (a content-gate string the base
  already contains cannot go red, SP-390), `dayz-mod-workflow` (tune a clock offset on
  the axis you are not investigating, SP-385), `enforce-script-reference` (a line break
  ends the statement inside a condition too, SP-386; looping `CombineItems` merges into
  pending-delete stacks) and `_shared/prompt-conventions` (single quotes in PowerShell).
- DayZ 1.30 Exp roboclients and server-side dummy bots, measured on build 1.30.164014:
  the 1.30 references of `dayz-mcp-verify`, `dayz-test-ingame` and `dayz-mod-workflow`
  record the public-Diag defines, the headless-client crash, the dummy-bot recipe, a
  server-load table and the launch/measurement traps, with three `runtime_verified`
  claims. `dayz-physics-engine` gains a section on what can and cannot be offloaded
  from the server.
- `dayz-animation-pipeline` `vehicle-rider-ik-pose.md`: a per-vehicle rider pose without a
  graph change, measured in game while the vehicle stands, for one player (DayZDiag
  1.30.164014, dedicated server and the owning client): a child `.asi` registered in
  `RegisterCustom` and swapped in with `SetAnimationInstanceByName`, as vanilla does for
  surrender. The page records the recipe, three traps (the frames after the get-out clip,
  bone names that do not resolve, the server's hand bones), the gates still open (riding,
  other riders, remote observers, weapon in hand, unconsciousness, ejection, death) and how
  the motorbike graph splits a rider pose into four pieces. Also the source-verified wiring
  of the steering-pose branch into the hand IK target nodes, and the inference that the
  steering clips set where the hands go (claims `CLAIM-ANIM-CHILD-ASI-SWAP-130`,
  `CLAIM-ANIM-HAND-IK-FROM-CLIP-130`, `CLAIM-ANIM-CHILD-ASI-RUNTIME-130`,
  `CLAIM-ANIM-POSE-PROBE-TRAPS-130`, `CLAIM-ANIM-MOTO-STOP-RIDE-SPLIT-130`).
- `dayz-animation-pipeline` `vehicle-rider-ik-pose.md` §Own clips on the rider: the same
  route with clips generated by DayZATool, measured in game riding and stopped (LFRider on
  the H2R, DayZDiag 1.30.164014, dedicated server and the owning client, one player). Our
  `ANIMSET5` clips play; the steering poses span +/-45 degrees of real wheel angle on every
  bike (`Vehicles.agf:50`, `:1466`), so frames authored over a bike's lock left the hands
  44 mm off at full lock, and with frames over 45 degrees the hands followed the frame of the
  bars' measured angle, stopped and at 24-27 km/h; DayZATool clips play as absolute poses, so
  difference-style transitions collapsed the rider's torso onto one point and whole-body
  absolute ones did not;
  a probe for the bars' real angle; a scripted get-out. Corrected: `GetBoneIndexByName`
  returns negative hash-like ids for `RightHand` and others, not -1 (claims
  `CLAIM-ANIM-OWN-ANM-PLAYS-130`, `CLAIM-ANIM-MOTO-STEER-SCALE-130`,
  `CLAIM-ANIM-TRANSITIONS-ABSOLUTE-130`, `CLAIM-ANIM-BARS-ANGLE-PROBE-130`,
  `CLAIM-ANIM-POSE-PROBE-TRAPS-130`). `skeletal-anm-enfusion.md`: the DayZATool round trip
  measured on two 1.30 player clips, and running it headless on a Windows host
  (`CLAIM-ANIM-DAYZATOOL-ROUNDTRIP-130`). `blender-animation`: DayZATool is not off limits on
  a Windows host. Scoped the one-graph-mod warnings and LL-052 against the child-`.asi`
  route and the 1.30 motorbike graph (review by Codex, one round).

### Changed

- README: the skill index lists all 42 skills (five rows were missing); the DayZ-MCP
  section reflects its 75 tools; §9 now states the editing direction of
  `CONTRIBUTING.md` item 7 (this repository is the editable source; installed trees are
  promotion targets) and the DayZ build coverage (#16).
- `AGENTS.md`, `GETTING-STARTED.md`: skill and tool counts measured on the tree (42
  skills, ten Python tools) (#16); the Copilot and Cursor agent files (`.github/copilot-instructions.md`,
  `.cursorrules`) still said 16 playbooks and five tools (#27).
- The remaining Spanish passages are now English: about 10,000 lines in 129 files (skills,
  `knowledge/`, `decisions/` and tool READMEs), translated line by line so no claim range
  moved, behind a mechanical gate (code spans, links, numbers by value, epistemic tags, claim
  markers and Markdown structure per line) and reviewed for meaning pair by pair. Left as they
  were on purpose: the sealed `MOVED-EXACT` history block, quoted game messages, section
  names of documents outside the Pack, file names, and skill front-matter descriptions
  (#25).

- Audit procedure: coverage angles no longer require eight agents or a fixed model.
  Review assignment and the bounded product-based stop rule belong to the orchestrator.
  The evidence checks and domain coverage remain; unavailable independent review must
  be declared. No game API, artifact format or runtime behavior changed.
- `dayz-model-pipeline` and `dayz-texture-pipeline`: the Option A edits made in the installed skills
  on 2026-09-26 (tickets 718f and abef) are now in the Pack. `dayz-model-pipeline` unifies Regla 12/13
  and GLB on the measured FBX/Blender recipe axis (x,z,-y) with inverted faces and negated normals
  (offline gates, no in-game proof), and its procedural-texture presets pack SMDI as R=255, G=old R,
  B=old G, as `map-conventions` does. `map-conventions` cites the measured SMDI PAAs instead of the
  stale procedural table.
- `dayz-mcp-verify` 1.30 reference: a confirmation run (run 3: 50 and 100 dummies on a
  10-wide grid, 45 s settles, back on the grid before moving) averaged 60 FPS over 45 s
  with 100 moving dummies at 0.008 server cores. Run 2 had averaged 54.7 FPS there, with
  the host at 34 % CPU from other load. The reading that 100 dummies show is withdrawn:
  the table shows both runs and the difference is not isolated. The headless roboclient
  crash is 3 of 3. `dayz-test-ingame` gains two traps measured that day (a stale script
  log in a reused `-profiles=` directory, a stalled CPU sampler) and no longer presents a
  two-minute warm-up or a 45 s settle as validated.

### Fixed

- `dayz-mcp-verify` no longer says `PrintWindow(PW_RENDERFULLCONTENT)` returns a black D3D
  area: with the session unlocked and the display on it captures the scene (measured
  2026-09-28, more than 20 captures) (#21).
- `dayz-animation-pipeline` cited `MotorBikeSTM` as `Vehicles.agf:1582-1750`; the node
  closes at `:1751` (claim `CLAIM-ANIM-MOTORBIKE-STM-RANGE`) (#22).
- `dayz-model-pipeline` `py3d-direct-generation.md` still taught the 2026-07-06 "det=+1,
  never reverse" rule that `SKILL.md` Rule 12 contradicts; it now defers to Rule 12 and to
  the LL-504 measurement (#23).
- `dayz-test-ingame` no longer presents restarting Steam as the remedy for a stale
  `ActiveProcess` pid; the deterministic fix (copy the live pid, from a shell outside any
  sandboxed app) is (#20).
- `dayz-basebuilding`: `Fence.OpenFence()` does not consult the combination lock (#16).
- `dayz-model-pipeline` Rule 12: the Blender→DayZ map is the det=-1 reflection
  `(x,y,z)→(x,z,y)` with the face order kept and the normals negated. The previous recipe
  (`(x,z,-y)` det=+1 + reversed faces + negated normals) renders solid but MIRRORED, which no
  winding gate can see: confirmed in game (DayZDiag 1.29.163709) with one chiral model exported
  three ways; `P3D.transform(py3d.BLENDER_TO_DAYZ)` on its own renders inside-out and mirrored.
  Propagated to `py3d-direct-generation.md`, `lods-and-geometry.md`, `blender-workflow.md` (its
  OBJ Forward -Y / Up Z settings are Blender's own axes, not a conversion), `blender-visual-review`
  and `knowledge/DAYZ_TECHNICAL_NOTES.md` (#26).
- A cross-family review of #16-#23 (Gemini over the 78 harvest hunks, GLM over the
  `dayz-motorbikes` translation) fixed: a wheel-proxy claim in
  `dayz-vehicles/references/rip-import.md` that generalised a door-proxy finding to vanilla
  wheels (whose frames are mirrored per side); the `dayz-mcp-verify` heartbeat rule that sat
  after the teardown, a 2026-09-07 "doors do not open by MCP" bullet that predates
  `door_index`, and a locked session read as a black frame (it fails with
  `capture_backend_failed`); the `dayz-pbo-build` "`-temp` under `P:\`" rule, which did not
  reproduce later; the inventory-preview failures filed under LIGHTS in `dayz-vehicles`; the
  cooling-fireplace double cook filed under the action-system rules; list and placement
  slips; three translation slips in `dayz-motorbikes`; and the README skill count (#24).
- `compatibility-matrix.md`: a "DayZ 1.30 Experimental" section that locates the 1.30
  content of each skill (without re-verifying it), and rows for the three 1.30-only
  skills (#16).

- `dayz-animation-pipeline` `item-ik-and-hide.md`: switching back to the base instance takes
  the `.asi` path, as vanilla does (`PlayerBase.c:2107`); the page said
  `SetAnimationInstanceByName("Empty", 0.2)`, which nobody has run. It also said 1.30
  dropped the surrender dummy item: the item no longer goes into the hands, but its profile
  is still registered so that the child `.asi` is preloaded.
- `dayz-basebuilding` cited `BaseBuildingBase.CreateConstructionComponent` at
  `basebuildingbase.c:872-876`. In 1.30.164014 the override is at `871-875`.
- `sources/source-map.json`: `validate` was red on bc042c2 with 28 errors and
  is now green. The 25 skill files and receipt 53bcac92 that 5ad3174 and
  5f6568e left unmapped are now mapped, and `adjudications.json` is resealed.
- Skill text mangled by shell escapes since 2026-09-07: PowerShell double quotes ate the
  backtick and first letter of `requiredAddons`, `nullptr`, `null`, `try`, `throw`, `for`, `break` and
  `array.Remove` in `dayz-mod-workflow`, `dayz-pbo-build` and `enforce-script-reference`, and a
  Python `\v` escape broke two `DZ\vehicles` paths in `dayz-vehicles`. The StarDZ block of
  `enforce-script-reference`, committed twice, keeps one copy.
- `dayz-animation-pipeline` said the 1.29 player graphs, the vehicle graph among them,
  were opaque binaries (`anim-graph.md`, `skeletal-anm-enfusion.md`, `tooling-and-walls.md`,
  `vehicle-rider-ik-pose.md`, `SKILL.md`). The 1.29.0.163709 extraction has nine text `.agr`
  files in the old `$AnimGraph 7` format, `Vehicles.agr` among them; 1.30 changed the
  syntax, not text versus binary (claim `CLAIM-ANIM-GRAPH-TEXT-129`). `SKILL.md` also
  called the 1.29 graph monolithic and said the master graph uses `include` directives
  (0 hits in the 1.30 `.agr` files). `dayz-realistic-animation-director` said the same of
  the creature graphs; all six 1.29 animal `.agr` files are text.
- `dayz-animation-pipeline` `tooling-and-walls.md` said 1.30 mods can patch individual
  sub-graphs. That is now marked unsupported and the one-graph-mod wall stays in force:
  adding a vehicle type touches `Vehicles.agf`, `player_main.ast`, `player_main.asi` and,
  above 12, `player_main.agr`, all at vanilla paths (claim
  `CLAIM-ANIM-VEHICLETYPE-PATHS-130`), and the official @DayZ post of 2026-09-16 tells
  graph mods to redo their changes from scratch.

## [1.3.0] - 2026-08-25

### Removed

- The ODOL→MLOD conversion skill and its scripts are no longer distributed
  with the pack. Reading-side tooling stays; every consumer that needs an
  ODOL→MLOD step now takes an external, locally supplied backend, following
  the pattern `tools/dayz-odol-strict` already used (`--odol-backend` /
  `DAYZ_ODOL_BACKEND_ROOT`). References across skills, notes and tooling now
  point at that external converter.

## [1.2.0] - 2026-08-24

The pack's own gates went looking at themselves. A winding rule that had been
corrected at its source but not at its call-sites, a face flag prescribed in
the same file that measures it inert, a far-LOD target its own census reads as
the failure, and a privacy check that passed over six physical roots because
they were spelled with dashes instead of separators. Contradictions were
adjudicated by which side carried a measurement; where neither did, the entry
says so rather than picking one.

### Added

- Three tools that reached the tree without a changelog line:
  `tools/dayz-script-validator` (pre-PBO linter for Enforce Script,
  `config.cpp`, `.layout` and `.rvmat` — the boot-time failures an editor's
  compile check does not see), `tools/dayz-layout-viewer` (one `.layout`
  rendered at four viewports in a single self-contained HTML, which is where
  exact-pixel-versus-proportional bugs become visible without a build) and
  `tools/dayz-vehicle-proxy-contract` (offline gate for proxy reachability,
  source-OBJ fit and required engine properties). The pack ships nine tools.
- Four more author-owned skills from the live store: `dayz-ai-patterns`,
  `dayz-realistic-animation-director`, `uv-clean-atlas`, `3d-generation-harness`.
  Image-to-3D generators named by the harness (`hunyuan3d-local` and kin) are
  optional/external and are not shipped. PartUV weights and Expansion eAI
  source are cited, not redistributed.
- Eight author-owned 3D/pipeline skills that the pack already cited but did not
  ship: `dayz-model-pipeline`, `dayz-p3d-audit`,
  `dayz-p3d-inspector`, `dayz-proxy-align`, `dayz-animation-pipeline`,
  `mixamo-retarget`, `blender-assembly`, `blender-visual-review`. The vendored
  py3d 1.4.0 wheel those p3d skills used to carry is not included; use
  pack `tools/py3d` 1.5.0 (`pip install -e tools/py3d`). Mixamo/Adobe assets
  are not redistributed.
- Ten author-owned skills that the pack already cited but did not ship:
  `enforce-script-reference`, `dayz-mod-workflow`, `dayz-texture-pipeline`,
  `dayz-particles`, `dayz-sound-system`, `dayz-ui-development`, `dayz-doors`
  (including the author's three worked-example `.p3d`s), `dayz-physics-engine`,
  `dayz-preflight`, `dayz-pbo-build`. The vendored py3d 1.4.0 wheel that
  `dayz-pbo-build` used to carry is not included; use pack `tools/py3d` 1.5.0.
- Routing instruction (AGENTS.md step 0 and README §0): before real
  multi-session work, ask which durable memory the human will use; recommend
  Obsidian or an equivalent plain-Markdown folder and do not proceed silently
  without one.
- `tools/dayz-3d-viewer` — sixth pack tool. Converts an MLOD `.p3d` (and
  optional PAA / RVMAT) to a deterministic `.glb` and a Three.js HTML
  viewer (`python -m dayz_3d_viewer`). Pillow and LZO are optional extras;
  three.js 0.160.0 is loaded from a CDN, not bundled.
- `skills/dayz-3d-viewer` — playbook for the viewer tool. Scripts and the
  old py3d 1.4.0 wheel stay out of the skill; invocations are
  `python -m dayz_3d_viewer`.
- `examples/end-to-end` — synthetic MLOD walked through py3d, model
  preflight and the 3D viewer. `run.py` executes steps 1–3. ODOL,
  animation and UI tools are named and skipped: they do not fit this
  asset.

### Changed

- Renamed the ripped-vehicle import skill from its previous directory to
  `skills/rip-vehicle-import/` and the companion reference
  `skills/dayz-vehicles/references/rip-import.md`. Public prose now uses
  neutral import terminology; measured geometry, hashes, LODs and gates are
  unchanged.
- Synced author working-copy updates into `dayz-feature-spec` (CHK017/CHK018),
  `dayz-vehicles` (extracted references plus day-0 viewer/signoff doctrine) and
  `rip-vehicle-import` (`B7_VISUAL_SIGNOFF`). Brand tokens stay neutralized.
- The DayZ-MCP bridge that `dayz-mcp-verify` drives is now public at
  https://github.com/willy92wins/dayz-mcp (MIT). The README, the bridge
  protocol note and `.mcp.example.json` point at it with the install one-liner
  instead of describing the skill as methodology for a private tool.

### Fixed

- README §4 said those ten skills (and the 3D playbooks still arriving) were
  first-party Anthropic content, not redistributable, and told readers to
  install the `anthropic-skills` plugin. That was false: they are the author's;
  `anthropic-skills` is only the local plugin folder name.
- `AGENTS.md` counted six tools while `TOOLS.md` counted nine, and the README's
  `tools/` row and structure diagram both named six of the nine. The canonical
  agent file was the one that was wrong.
- Eighteen tracked files had been edited without refreshing their `output_hash`
  in `sources/source-map.json`. The cost was not cosmetic: `gate` only runs the
  double build when no finding carries error severity, so the stale hashes made
  `build_reproducible` report `SKIPPED` — with no reason printed — and the
  pack's headline property went unmeasured. Gate is back to 7/7 with two
  byte-identical builds.
- The pack taught, in six places, that the Blender Z-up to DayZ Y-up rotation
  flips face handedness and that every face in every LOD must therefore be
  reversed. It does not. That rotation (`x'=x, y'=z, z'=-y`) has determinant
  +1, so it preserves winding; reversing anyway yields 100% flipped faces — a
  model visible only from inside. Only a reflection (determinant < 0, such as
  the pure swap a glTF import uses) requires the reversal. Rule 12 of
  `dayz-model-pipeline` already said so; the correction had not reached three
  stale cross-references inside that same file, two further files, or
  `references/py3d-direct-generation.md`, where the checklist at line 228 went
  as far as declaring `UNIFORM_FLIPPED` the correct post-fix state and
  `UNIFORM_NON_FLIPPED` the mark of a skipped step — the exact opposite of what
  line 263 of the same file says a correct assembly reports.
- `check_dayz_winding.py` printed its outward-normal fraction and then ignored
  it, so a model with inward normals still exited 0. The measurement is now the
  verdict, with a threshold placed where the metric can actually discriminate,
  and an unreadable model exits 2 instead of passing.
- `rip-import.md` prescribed the MLOD face flag `0x20000` for two-sided
  rendering in the same file that records, twenty lines later, the in-game test
  showing it does nothing. The prescription is withdrawn in the four places it
  appeared. What is established is bounded to what was measured: setting
  `0x20000` did not work, and double-siding the geometry does. Whether DayZ
  ignores a "both sides" face flag in general is still open, because
  `dayz-custom-infected.md` disputes the bit itself (`0x20000` against the
  Bohemia wiki's `0x00000020`) and the wiki value has never been tested.
- Invariant 13 of `dayz-vehicles` prescribed flipping a far LOD to 100%
  cross-outward, four lines above the census that measures ~98% cross-outward
  as the inverted state and lands the fix at ~2%, confirmed in-game on SUB_BRZ.
  Following the prescription delivered you into the state the measurement
  calls broken. The target is retired; the distinction the two draw — black is
  stored normals, transparent is vertex order — is kept, since it is the
  measurement's own.
- `killers-detail.md` explained that an inverted collision LOD hides behind a
  correct-looking model because "the renderer draws both sides". DayZ renders
  single-sided with backface culling, which the pack knows from two independent
  in-game cases. The same file also prescribed an absolute
  "cross-product must point AWAY from mesh center" detection fifteen lines
  above the block recording that this heuristic false-positived on every
  Blender export and was disabled — the disablement that let an inverted
  collision sphere pass a full audit as ALL PASSED. Both now name the relative
  comparison against the Visual LOD that `audit_p3d.py` actually runs.
- Six published files carried a physical system root, which `validate_privacy`
  is meant to prevent and reported zero findings on. Its two patterns require
  path separators and correctly exempt the `<you>` placeholder; neither can
  reach the same path flattened into one dash-joined name component sitting
  further along the very same line. Whoever scrubbed those files replaced the
  one occurrence the gate inspects, and the gate inspects only there. The
  roots are gone and a third pattern covers the flattened shape, with a test
  written to fail first — and which did.

### Removed

- `skills/grok-handoff-template`, `skills/qwen-handoff-template` and
  `skills/zcode-handoff-template`. They arrived under version control on
  2026-08-22 and are the process layer 1.1.0 deliberately stopped publishing:
  how to drive a paid CLI, a local Ollama model and a vendor app, not how to
  mod DayZ. They were also the only Spanish files left under `skills/`, they
  referenced a `codex-handoff-template` this pack does not ship, and one
  reference published a single machine's tool paths. They were never in
  `promotions/promotion-map.json` either, so they were never governed content.

## [1.1.0] - 2026-08-15

The first release shipped the author's project-management layer along with the
product. This one separates them, and gives agents other than Claude Code a way in.

### Added

- `AGENTS.md` — the canonical agent file, in English, covering routing, the four
  rules, layout, installation and the gates. `CLAUDE.md`, `GEMINI.md`,
  `.cursorrules` and `.github/copilot-instructions.md` are entry points that
  point at it, so the pack is discoverable from more than one host.
- `TOOLS.md` — an index of all five bundled tools with what each one does, how to
  run it and, deliberately, **what it refuses to do**. `tools/dayz-ui-lab` was
  absent from the README entirely and is now documented.
- `knowledge/dayz-mcp-bridge-protocol.md` — the in-game verification bridge that
  `dayz-mcp-verify` drives, previously present only as a one-line caveat saying
  it was not public. The note carries the tool surface, the design invariants
  worth copying, and the engine facts the bridge cost in-game cycles to learn:
  a server-side seat is not client ownership, `SetThrottle` sets *future* input
  that `CarScript.OnInput` then overwrites, `DEVELOPER` is not defined in
  DayZDiag while `DIAG_DEVELOPER` is, and freecam freezes the simulation you are
  trying to measure. Each cited to vanilla `path:line`.
- `.mcp.example.json` — example client wiring. Named `.example` on purpose:
  agents auto-start servers declared in `.mcp.json`, and a failed launch on every
  session is worse than no config.
- README §7 rule 7, **keep a durable memory outside the agent**, recommending a
  plain-Markdown vault (Obsidian) and saying what earns a note. The practice that
  produced this entire pack appeared nowhere in it: Obsidian was named only as an
  internal promotion target, and the `[[wikilink]]` syntax in `vault-notes/` was
  explained as a formatting quirk rather than as the mechanism it is.

### Removed

- `plans/`, `specs/`, `promotions/receipts/`, `promotions/adjudications.json`,
  `HANDOFF.md` and the old Spanish `CLAUDE.md`. These were the internal process
  layer: phase roadmaps, session state and promotion bookkeeping. They described
  how the work was run, not what the pack is, and one of them published a private
  workflow instruction and a set of gotchas that had been stale for weeks.

### Fixed

- The README structure diagram was missing two skills (`dayz-clothing`,
  `dayz-persistence`) and one whole tool (`dayz-ui-lab`), and still quoted py3d
  at `1.4.0` after the 1.5.0 sync.

## [1.0.0] - 2026-08-15

First public release. Everything below was accumulated across r21 phases 01-04
and is published together.

### Added

- `knowledge/vault-notes/dayz-world-arena-optimization.md`: what the Enforce
  compiler actually charges per script module, and why almost nothing that looks
  like a size proxy is one — a million source bytes removed bought 0 kB of arena.
  Includes the vanilla early-facade pattern that moves method bodies out of the
  World arena, with its four pieces re-verified in `P:\scripts` on 1.29.
- `rip-vehicle-import` cookbooks (`family-b/`), archived runbooks (`history/`) and the
  classify viewer, which reviews a Blender sitting without opening Blender. Its
  three Three.js libraries are **not** bundled; the viewer README says where to
  fetch them, matching the pack's existing policy on third-party tools.
- `dayz-vehicles` archived gate ladders (`history/`).
- `skills/_shared/pack_skill.py`: packages a skill folder into an installable
  `.skill` zip on Windows, where the upstream packager reads `SKILL.md` without
  an explicit encoding and dies on any em-dash or accent under cp1252.
- `dayz-clothing` skill: the worn-clothing pipeline verified in-game on DayZ
  1.29, covering the three silent failure modes that make a custom
  `ClothingTypes` item load as nothing, float, or come apart. Its helper
  scripts ship with placeholder paths and must be re-pointed before use.
- Compatibility-matrix rows for `dayz-clothing` and `dayz-persistence`. The
  latter closes a gap: the skill shipped without a row, so the matrix covered
  14 of 16 skills while claiming to cover all of them.
- py3d `KNOWN-ISSUES.md`: the published blind spots of the library, including
  three checks that cannot fail for the reason you would rely on them for —
  `save(verify=True)` compares no coordinates, `python -m py3d diff` calls
  materially different models equal, and `audit_p3d.py` can print `ALL PASSED`
  having checked nothing.
- py3d absolute winding check (`_check_winding_absolute` with normal-agreement
  and edge-coherence measures) and its council regression tests.
- In-game verified skill knowledge written between 2026-07-30 and 2026-08-13:
  worn clothing binds through `DayzTemporarySkeleton` rather than
  `OFP2_ManSkeleton`; starting CF on a mission whose persistence was written
  without it crashes the server hard while naming an unrelated vanilla entity;
  the diag RPT buffers about 52 KB.
- r21 Phase 04 strict 3D tooling: SEAnim v1 / `RTM_MDAT` / `RTM_0101`
  reader-writer-inspector, contract-driven MLOD pre-export validation and a
  read-only ODOL v53-v55 anatomy/diff adapter with authorized fixtures.
- py3d 1.4.0 proxy lifecycle with explicit raw/engine frames, strict anatomy,
  atomic align/remove operations and reproducible wheel manifest.
- Rollout projections for model preflight, animation formats, strict ODOL
  parity and proxy lifecycle, including an explicit-root, backup-preserving
  no-write/apply script.
- r21 Phase 01 evidence contracts: source map, executable-claim registry and
  local-root templates.
- Root MIT license, third-party notices, contribution policy and per-skill
  compatibility matrix.
- Source-verified guidance for injected-object Forward Contracts, historical
  PBO recovery, crash-safe evidence, authority and loopback boundaries,
  incremental rebuilds, vehicle get-in/action contracts, winding lineage and
  material overrides.

### Fixed

- **Two skill descriptions were not valid YAML** and no gate had said so.
  `dayz-clothing` carried `Use for: mod de ropa` and `dayz-persistence` carried
  `auditing DayZ persistence: OnStoreSave/...`; an unquoted `: ` inside a YAML
  scalar parses as a nested mapping. Found by re-pinning the external reference
  validator, which is the entire reason criterion A3 asks for a second
  implementation — the pack's own validator checks the caps and the field names
  and had passed both files.

### Changed

- **Agent Skills reference validator re-pinned to `skills-ref==0.1.1` from PyPI**,
  whose console script is `agentskills`. The previous pin was a git commit that is
  no longer reachable in `anthropics/skills`, and whose directory is gone from
  HEAD. `packctl gate` now looks for either command name, so an existing checkout
  keeps working. 16 of 16 skills validate.
- **py3d 1.4.0 → 1.5.0, distribution renamed `py3d` → `py3d-dayz`.** The pack
  now takes its py3d bytes from the published fork
  `willy92wins/py3d-dayz@c50321c`, which was ahead of the pack and already
  carried the release text. The importable module stays `py3d`; only the
  distribution name changes, because `py3d` on PyPI is an unrelated library.
  The version moved rather than being re-sealed again because `1.4.0` had come
  to designate three different contents distinguished only by a manifest seal.
  New reproducible wheel: `py3d_dayz-1.5.0-py3-none-any.whl`, SHA-256
  `16eac9218cddb02b52b533540c0259c33d5e5b2d6ad2cd28444ef049d608a73b`.
- `audit_p3d.py` moves from `tools/py3d/rollout/` to `tools/py3d/tools/`,
  matching the published layout.
- Distinguish fail-closed ODOL parity inspection from partial MLOD recovery;
  the compatible unknown-license backend remains external and SHA-256 pinned.
- Normalized all 14 skill descriptions to the official 1024-character limit.
- Coupled `dayz-test-ingame` and `dayz-mcp-verify` to the managed
  `dayz_test_run` / `dayz_test_stop` lifecycle.
- Hardened generated test launchers so credentials are scoped to child
  processes and no VPP password is packaged by default.
- Promoted the validated Phase 01 snapshot from commit
  `7a25432febc112a957a7c1ef7a7d2c16c221b24f` to Obsidian and all configured
  skill targets with create-only receipt `c7b5366cc761a8038e52f6a2`.

### Fixed

- Make the py3d wheel builder and rollout work under Windows PowerShell 5.1,
  including deferred `$PSScriptRoot` defaults and explicit native
  `git apply` exit-code capture.
- Replace a fabricated `py3d.read_p3d` reference with the verified
  `py3d.P3D(stream)` API in the animation projection.
- Promotion now durably synchronizes and safely removes verified Windows
  sidecars containing read-only files while preserving fail-closed behavior
  for unrelated permission errors.

### Security

- Explicitly exclude secrets, personal identities, private absolute paths,
  proprietary game data and incompatible third-party payloads from releases.

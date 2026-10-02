# Changelog

All notable changes to the DayZ Modding Knowledge Pack are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

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
- py3d `ERR_WINDING_VS_NORMALS` message: it read every disagreement between winding and stored
  normals as faces wound backwards and prescribed `face.vertices.reverse()` on every face, and
  the py3d README called that fix always correct. The finding only says the two disagree. On the
  model of the Rule 12 in-game test, rebuilt byte for byte by the py3d tests, the correct export
  with its normals turned and the same export with its faces turned raise the same finding with
  the same text and need opposite fixes; either fix silences it, and the wrong one leaves the
  cross product and the normals both outward, the orientation of the variant that rendered
  inside-out in game. Reversing every face did exactly that to two Blender exports in DayZDiag
  (`dayz-p3d-audit`, "Absolute winding check: what 0 % means"). The message now says the two
  disagree, asks for the direction first (visual LOD: signed volume by winding of each closed
  shell, read once its faces agree with their neighbours; collision LOD: the outward check in
  each convex component) and gives both fixes: normals wrong → negate the normals of the
  disagreeing faces, with a negated copy for a pool entry that a face left alone also uses;
  winding wrong → `face.vertices.reverse()` on every face of that part, never a
  `vertices[1]`/`[2]` swap. Those conditions come from measured cases. On the same model, a
  shared entry negated in place turned a part whose normals were right (75 % agreement left),
  and a closed shell with one reversed face kept its negative volume. On a synthetic
  ring-shaped FireGeometry, the centroid test read 264 of 336 correct faces as outward. The
  README says the same, adds that neither
  winding check sees faces and normals turned together (`transform(ROT_X_NEG90)` alone: 100 %
  agreement, `validate()` returns `[]`) and that the check reads each face's first corner only,
  and no longer gives a wrong normal sign the inside-out symptom of a wrong face order. Finding
  code and severity unchanged. No new wheel: the pinned and installed `py3d_dayz-1.8.0` still
  prints the old message.

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

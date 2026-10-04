---
name: dayz-mcp-verify
description: >
  Auto-test a DayZ mod in-game through dayz-mcp without keyboard or OCR:
  spawn a classname, orbit/capture, raycast collision, inspect
  placement/attachments/telemetry and emit PNG+JSON evidence. Compose with
  dayz-test-ingame; dayz_test_run/dayz_test_stop own the managed lifecycle,
  then this skill drives the bridge. Use for "auto-probar el mod", "verificar
  in-game con MCP", visual smoke/re-test, "comprobar que el .p3d carga/se
  ve/colisiona", automated spawn+capture+raycast, or the vehicle acceptance
  ladder (spawn→render→get-in→drive→wheel direction). Covers static objects,
  items/weapons, buildings without doors and vehicle placement/drivability.
  Player UI, door interaction, inventory use and firing remain manual.
  Also: ScriptConsoleTabRegistry, IsHeadless roboclient, UA_AM_INIT action inject.
---

# DayZ MCP verify — auto-test in-game vía tools MCP

## GATE 0 — ask WHO is driving, before touching anything (added 2026-08-07)
(until 1.29: managed `dayz_test_run` / `dayz_test_stop` and Mode=all capture still hold.) (since 1.30 Exp: Diag Script Console tabs register via `ScriptConsoleTabRegistry`; `IsHeadless()` names roboclients; SP `PerformActionStart` no-ops while pending. Details: [dayz-1-30-mcp-verify.md](references/dayz-1-30-mcp-verify.md) and ## DayZ 1.30 Exp.)

**Before the first `dayz-mcp` tool in a verification run, ask the user whether
they are driving or the MCP is.** Neither is assumed. A single question per run, not per
capture.

Why it is a gate and not a preference: **with the user present, their manual cycle is faster
and yields better results** — spawns with VPP in seconds and evaluates the whole scene at a glance,
while MCP loop needs to position camera, capture, and chain tools. MCP wins when
the user is NOT there: early morning, unattended run, or while attending another front. Furthermore,
changing mode is not free midway (clean manual test requires relaunching without
`@DayZ_MCP`), so the decision is made at the start of the cycle or paid twice.

| Situation | Who drives |
|---|---|
| User present and available | **Them** (VPP + direct judgment) — MCP only if they ask |
| User absent / unattended run | **MCP**, and report is left for them with evidence |
| Doubt | **Ask.** Never assume |

What does NOT change: MCP remains mandatory for what a human cannot measure by eye
(telemetry, numerical raycast, exact placement, repeatable series). There you do not ask, you use it.

Measurement that originated gate (2026-08-07, corpus of 276 sessions): 63% of wall-clock time in a full
cycle falls on user side, and 71% of their actual verifications are automatable with
today's tools. That it is automatable does not imply it should be automated: with them present,
their cycle rules.

## WHAT THIS DOES

Drives an already launched DayZDiag client, via `dayz-mcp` MCP server tools, to
verify a mod without human intervention: spawns object, views it from multiple angles
(camera + window-grab), checks collision via raycast, reads placement/telemetry, and
produces a report with pass/fail criteria and evidence. It is the automated **observation**
loop bridging the gap between "PBO compiles/deploys" and "looks and behaves properly
in-game", for the class of properties that DO NOT require keyboard input.

Server-authoritative + passive pixel capture. Control and data are engine-native
(spawn, raycast, telemetry, camera); sole non-native piece is visual capture
(window-grab of rendered client — `MakeScreenshot` is broken in diag, T165276).

## COMPOSITION — public lifecycle + MCP verification

Build/deploy/launch belongs to **`dayz-test-ingame`** (its environment preflight runs on its own:
`P:\` mounted, junction `P:\Mods`, AddonBuilder, `allowFilePatching`). This skill invokes it
with MCP mod added and then drives. Bridge verbs do not start or terminate
processes; public test tools do orchestrate managed lifecycle.

Before operational flow, read canonical protocol:
`<runbooks>\dayz-mcp-agent-session-protocol.md`.
[EXACT][CLAIM-R21-MCP-ORCHESTRATED-TEST] Execute lifecycle with
`dayz_test_run` and stop it with `dayz_test_stop` on exact `run_id`. Both
tools possess FIFO queue, lease, heartbeat, and release; do not wrap them in
a second `session_acquire`. Reserve `session_*` primitives for
low-level mutations not already encapsulated. Every lifecycle is
identified by `run_id`: sharing mod does not grant ownership. Under retail
quarantine only reads are allowed; if whoever opened retail cannot close it via
UI, declare `manual_cleanup_required`.

**Bridge startup sequence (rev. 2026-09-06): `dayz_test_run` → `session_acquire_wait` →
verbs. Never probe before adopting.** "Do not wrap launch in another lease" does not mean run
remains yours: upon completion, `dayz_test_run` RELEASES its owner lease (daemon audit:
`session_release_finished reason=owner_release` right after launch) and run transitions to `RUNNING_IDLE`
without owner (`release_owner`, `process_lifecycle.py:958-976`). From that instant the idle run fence
rejects ALL `/enqueue` on that run, **reads included**: `_enqueue_run_rejection` discards flag
`mutation` (`loopback.py:1293-1296`) and for `RUNNING_IDLE` returns `run_not_owned` (`:1317-1318`) with
hint "This run has no owner (RUNNING_IDLE). Adopt the existing run before dispatching." (`:99-102`,
`:1323-1329`). The counter-intuitive part: `bridge_status` counter is named
`fence.mutation_rejects_by_code` (`:2821-2822`) and counts reads as well. Every verb crossing
bridge falls there (`query_*`, telemetry, raycast, captures, `world_spawn`…) and also
`wait_for(players_at_least|players_at_most)`, which polls with `query_all_players` (`server.py:2645-2650`).
`wait_for(log_matches)` does NOT fall: reads log files without touching bridge (`server.py:2603-2637`,
`:2686-2697`).

1. `dayz_test_run(...)` → retain `run_id`.
2. Optional without adopting: `wait_for(log_matches, "…")` to wait for startup via RPT.
3. `session_acquire_wait(purpose=…)`: grant adopts the ONLY ownerless `RUNNING_IDLE` run and
   declares it in `adopted_run` (`_adopt_on_grant`, `loopback.py:3119-3120`, `:3193-3230`). Check
   `adopted_run.ok` before first verb. With multiple idle runs it answers
   `adopted_run.error = "multiple_idle_runs"` and adopts none (`:3202-3208`): `dayz_test_stop`
   surplus run and repeat.
4. `wait_for(players_at_least, 1)` and remaining verbs.
   - [EXACT] The adopted lease expires by itself (added 2026-09-27, LFPowerGrid, three runs): it lasts 120 s and is NOT renewed internally, fresh MCP client or not. Send `session_heartbeat` at least every ~90 s during the whole run, including while a human plays. Past the deadline the run goes ownerless again (`grace.remaining_s` counts down) and the daemon stops it (`lifecycle_stop_outcome: stopped`), even with the user in front of the game. (measured in game, DayZ 1.30.164014 Exp)
5. `session_release` → `dayz_test_stop(run_id)`.

With an MCP client prior to `8f5727f` of DayZ_MCP (2026-09-06) rejection arrived as a
BARE `remote_error`, without code or hint (ledger entry `fb-20260906-193626-f45d`, first attributed to a
client without polling); with current client it arrives as `run_not_owned: This run has no owner
(RUNNING_IDLE)…`. In both cases remedy is adopting, neither retrying nor relaunching. This rule corrects
step 1 of recipe SP-292 and clarifies first bullet of SP-152, below.

Two lease failures around long waits (measured in game sessions, 2026-09-28): (1) `wait_for` over the log does NOT renew the lease — a wait longer than ~2 min expired with `lease_expired`; interleave `session_heartbeat` between waits. (2) When a user message interrupts an in-flight call (a long `wait_for`), the next `session_heartbeat` answers `lease_invalid: token was never valid for this client`; if the run is still alive, `session_acquire_wait` readopts it. Also: `dayz_test_close` shuts the run down in order, with a termination line on both sides. [EXACT]

### Companion externo: dayz-labs

[EXACT][CLAIM-R21-MCP-COMPANION-AUTHORITY]
`external_companion_no_lifecycle_authority`. Release dayz-labs v0.1.35,
reviewed at pinned commit
`dbd6ad3e54e30c81a9aeb88fcb9f60f007804c2a`, can serve as reference or
optional companion. Its `start/stop/restart` verbs are excluded while
DayZ_MCP holds a run: only `dayz_test_run` / `dayz_test_stop` on exact
`run_id` govern that lifecycle. Do not install or update companion
as part of a gate; always document the examined `pinned_version`.

Its interface is WPF and captures its own application:
`wpf_not_layout_evidence`. A correct capture from dayz-labs does not validate the
parser, proportions, clipping, or semantics of a DayZ `.layout`; UI
viewer needs its own render and comparison against in-game evidence.

The `dayz_test_run` request must select `Mode=all`, build when PBO
changed, and `@DayZ_MCP` as additional dependency:

- `-Mode all` (server + client) is MANDATORY: visual capture reads from **rendered
  client**. A headless `-Mode server` has no window to grab.
- `@DayZ_MCP` is loaded alongside the mod under test; both peers (server + client bridge) poll the
  MCP server loopback.

## PREREQUISITES (gate before driving)

1. **`dayz-mcp` registered and connectable.** PRIMARY gate: are tools
   `mcp__dayz-mcp__*` available in session? (ToolSearch finds them → gate PASS). `claude mcp list` is
   SECONDARY and NOT reliable: gives false `× Failed to connect` with server operational — do not block
   on it if ToolSearch sees tools. Tools are only available in a session started
   WITH server already registered (broker registration `--client`, see TROUBLESHOOTING).
2. **Bridge config seeded.** In-game bridge reads `dayz_mcp.json` (url + key + pollHz) from
   its profiles; MCP server uses `<DayZ_MCP_dev>\tools\.dayz_mcp.key`. Seed the SAME key in
   launch profiles with `install-mcp.ps1` pointing to directories generated by `dayz-test.ps1`:

   ```powershell
   <DayZ_MCP_dev>\tools\install-mcp.ps1 `
     -ServerProfiles "<TargetMod>_dev\_server\profiles" `
     -ClientProfiles "<TargetMod>_dev\_client\profiles" `
     -MissionPath "<...>\mpmissions\dayzOffline.chernarusplus"
   ```

   `[verify on first run]` — generic seeding (arbitrary mod + `@DayZ_MCP` via
   `dayz-test.ps1`) was until now only exercised through `run-fase3.ps1`. The FIRST run
   of this skill validates that bridge finds config in these paths; if `bridge_status`
   reports `last_poll_age_s = null`, config is not where bridge looks for it — adjust
   path and declare it.
3. **`bridge_status` green.** ALWAYS first call: `bridge_status`. `server_peer` must
   have fresh `last_poll_age_s` (not null). For capture, `client_peer` as well. `never
   polled` → bridge did not start (config/key/startup) → abort and diagnose, do not keep
   driving blindly.
4. **Mods passed via `extra_mods`/`base_mods` must be REAL DIRECTORY under `P:\Mods`
   (→ `!Workshop`); Steam junctions ARE NOT valid.** Two layers, confusing them costs a session:
   - Public boundary `_valid_public_mod` (`DayZ_MCP_dev\tools\dayz_mcp\dayz_test_tool.py:75-85`)
     rejects `:`, `\` and `/` across **all** projects → absolute workshop path never passes
     through tool. That is by design, NOT a gap in your project's policy. *(Updated 2026-10-03: the
     boundary now also accepts an absolute path inside the selected project's `mod_roots`;
     `_valid_public_mod` calls `dayz_test_request._valid_mod_entry` (`dayz_test_tool.py:269-272`,
     `dayz_test_request.py:222-233`, DayZ_MCP_dev `506de5d`). A workshop path lies outside them and
     still fails, with `bad_mod`.)*
   - Subscribed mods exposed by Steam in `!Workshop` (`@CF`, `@Dabs Framework`,
     `@VPPAdminTools`) are **Junctions** to `steamapps\workshop\content\221100\<id>`, and path
     identity guard rejects them → `dayz_test_failed`, which is the generic catch-all of
     `server.py:1101` and **swallows the real cause**.

   **Operational consequence**: CF/Dabs/VPP are only loaded by declaring them with **absolute path** in
   project `default_base_mods` inside launcher `request-policy.json` — which is how
   SUB_BRZ and LFHeli declare them. Mods that are real directories (`@DayZ_MCP`, `@LFHeliCore`, mod
   under test) do go via `extra_mods` with relative name.

   Diagnosis in one command:
   `Get-Item '<!Workshop>\<@Mod>' -Force | Select-Object LinkType` → `Junction` = relative does not work.
   Measured 2026-08-02 with `preflight=true` (pure dry-check: `dayz_test_worker.py:533-534` returns
   before build and launching anything): without mods OK · `@DayZ_MCP` OK · `@A6_SR2M` OK · `@CF` FAIL ·
   `base_mods=["@CF"]` FAIL.

   **When the mod under test does not compile, test a probe copy of it** (added 2026-10-03,
   measured 2026-10-02, dayz-mcp run 606a5dbb) [EXACT][CLAIM-MCPV-PROBE-COPY], for example when
   its build packed another session's untracked test scripts:
   - copy the deployed PBO entry for entry without those entries (every other entry byte-identical,
     the same header properties, the SHA-1 trailer recomputed) into a probe folder of its own under
     `P:\Mods`;
   - host it in another approved project whose `default_base_mods` carry what the mod needs (CF and
     Dabs there): an absolute workshop path in `base_mods` fails with `bad_mod`, since each entry
     must be a folder name or an absolute path inside the project's `mod_roots`
     (`dayz_test_tool.py:399`, `dayz_test_request.py:222-233`);
   - writing under `P:\Mods` changes what every later run can load: ask the owner in chat first (in
     that session the agent harness's auto-mode permission check blocked the write until the owner
     agreed), and move the probe out of `P:\Mods` when done.

   In that run the copy (641 of the 645 entries) compiled the mission module, and its models were
   the deployed ones byte for byte.

   ⚠ **Before blaming the bridge for `version_blocked`/`last_poll_age_s=null`**: check that
   `key` of `dayz_mcp.json` in project profiles is the SAME as
   `DayZ_MCP_dev\tools\.dayz_mcp.key`. A stale key gives 401 and bridge never polls, with
   symptom identical to "mod is not loaded". Key rotations leave behind projects
   not exercised since then (2026-08-02: MERCEDES_AMGLF and LFPowerGrid with old key,
   SUB_BRZ/LFHeli/DayZ_MCP with current key).

   ⚠⚠ **The symptom is NOT always `version_blocked` / `last_poll_age_s=null`** — and believing so
   costs the session just the same (measured 2026-08-17 in LFPowerGrid, with this warning already written above and
   overlooked). With stale key the peer can read **`version_state: ok` with
   `last_poll_age_s` of 1.485 s**: it is data from LAST good poll, which may belong to another
   already dead run. A dead bridge reads like healthy this way. The telltale signature is in
   game script log: `[MCP-POC] poll error=5` (server) / `[MCP-CLIENT] client poll error=5`
   (client). That **5 is `EREST_ERROR_CLIENTERROR`** (`scripts\3_game\http\restapi.c:16-17`), meaning
   daemon returned 401 — 401 DOES NOT appear anywhere on game side.
   Two-command gate before blaming anything:
   - Compare key of **each** `dayz_mcp.json` the run will use against keyfile. These are two
     paths and `$profile:` wins over `$mission:` (`MCPBridge.c:145-149`, `MCPClientBridge.c:234-237`);
     if profiles key is missing, bridge falls back to mission key, which is usually the stale one.
     Same length (43) is NOT proof: compare the bytes.
   - `Invoke-WebRequest "http://127.0.0.1:8765/poll?key=<keyfile content>"` → 200
     `{"commands":[]}` proves daemon and live key are fine, isolating failure to run JSON.
   **And fixing it DOES NOT require server restart**: `ReloadKeyAfterFailure` (`MCPBridge.c:373-398`)
   rereads key when backoff hits ceiling. Fix JSON, wait ~20 s,
   `[MCP-POC] poll key reloaded` appears and peer returns to `last_poll_age_s` 0.2. That saves the boot.

   ⚠ **Player spawn needle cannot presuppose gender.** The example
   `Create entity type 'SurvivorM_` —suggested by `wait_for` description itself— **fails in
   silence** with a female character: 300 s timeout with player already in world and
   `Create entity type 'SurvivorF_Helga'` written to RPT. Use `Create entity type 'Survivor`.

## BRIDGE GOTCHAS THAT COST ONE RUN EACH (added 2026-08-18)

Verified in-game on 2026-08-18 during ATM cell test battery. All six cost at least
one run each, and **five of six produce a verdict accusing the mod without the mod
having any issue** (6 runs, 0 actual mod failures). Check them BEFORE writing first probe.

1. **`dayz_test_run` DOES NOT load `@DayZ_MCP` by default, and returns `succeeded` anyway.** Both
   processes launch alive, the game works, and the bridge stays silent. The symptom you receive
   (`server_poll_stale` / `client_not_polling` / `ready.reason=no_run`) points to bridge or
   key, not to mod set, so time is lost in the wrong place.
   **Gate**: pass `extra_mods=["@DayZ_MCP"]` and confirm in server log that define
   `DayZ_MCP` appears in all four modules, or look for `[MCP-POC]` lines.

2. **`logs_since` does not accept its own `marker`.** It RETURNS it as dict {path: [offsets]} and its
   parameter requires string: Pydantic ValidationError. Incremental draining is impossible.
   **Workaround**: read entire log at end of sequence and assign responses in order,
   verifying alignment with some field from event itself (a type, an id). If two probes
   share that field, mark `ambiguous_alignment` instead of guessing.

3. **`wait_for(log_matches)` does not work to wait for YOUR response.** With default
   `lookback_lines=200`, a line from previous probe satisfies pattern instantly. And with
   `lookback_lines=0` it has been seen timing out with line already present in client log,
   returning a line from another flow in `observed`. Use it as opportunistic wait; verdict
   comes from polling `logs_since`.

4. **Player inventory is NOT reset between runs.** Second run finds what
   first left behind, nothing fits anymore and dotation fails silently (`create_failed`, or endow of 0
   units). To chain: `dayz_test_stop`, delete
   `<mission>\storage_1\players.db` with backup, and relaunch (~3 min).
   **WARNING**: `clean=true` DOES NOT do this — forces `Build=true` and passes `-clear` to AddonBuilder, meaning
   **rebuilds the PBO** and breaks binary identity, which is precisely what an A/B test cannot
   afford. Balance/state that mod saves in server profile SURVIVES deletion.

5. **`inventory_give` returns `create_failed` whether classname does not exist or does not fit.**
   They are indistinguishable. Before blaming inventory, verify classname exists: grep in mission
   `types.xml` and test with a control vanilla item (`Apple` works). And do not
   presuppose mod config classnames exist: they can point to a mod not
   loaded, in which case exact classname count gives 0 forever and entire feature looks
   broken without being broken.

6. **Do not believe a verdict without looking at client log.** Many mod events are written by
   CLIENT, not server. In test battery originating this section, automatic verdict said
   FAIL or INCONCLUSIVE six times in a row while client log showed operations
   executing properly. Dangerous failure mode of a cell is not "does not measure": it is
   **"measures poorly and accuses the mod"**, and that propagates to project documents. If a verdict
   says FAIL, open client log before recording it.

- **`world_spawn` with `ok=1` DOES NOT prove object stays where you asked** (added 2026-08-21,
  DayZ-MCP council). `IsSpawnReady` (`MCPBridge.c:2729-2753`) takes ACTUAL position of object
  itself, searches objects at that position, and considers itself ready if it finds itself. An object
  is always where it is: gate is tautological and satisfied for any live object, even if physics
  is already ejecting it. Does not compare against REQUESTED position, does not measure drift, and does not require
  inter-tick stability. Real case: spawn at urban point with `ok=1` and vehicle ending up at
  **Y = -40 km**. Distinct from inverted coords failure above, which times out: this gives
  false PASS. **Rule: after any `world_spawn` that matters, confirm with `object_inspect` or
  `entities_query` that distance to requested position is as expected, and repeat reading a few
  seconds later to rule out drift.** A playbook verdict looking only at `ok` is invalid.

## THE LOOP

1. **Launch** via `dayz-test.ps1 … -ExtraMods "@DayZ_MCP"` (wait until client and server
   are in; BUG-009: client autoconnect is flaky — higher `-ServerWait` / retry).
2. **Gate** `bridge_status` (PREREQUISITES.3).
3. **Scene conditions** (comparable captures): `world_time_set` at noon
   (all 5 args `year/month/day/hour=12/minute=0` are mandatory) and `world_weather_set(overcast=1.0)`. Overcast sky = diffuse light: eliminates
   specular glint from direct sun that burns weapons/materials to white and hides detail
   (A6_SR2M finding 2026-06-17). DO NOT use `time_multiplier=0` before pending animations
   (freezes sim).
4. **Playbook** depending on mod type (below).
5. **Report** with evidence.

## PLAYBOOKS (pass/fail criteria by type)

All start from spawn. `world_spawn(type=<classname>, pos=[x,y,z])` → PASS if `ok` and without
`unknown_type`/`spawn_failed`; save actual `pos` for subsequent steps.

### Static object / container / building
- **Load**: spawn ok (above). FAIL → classname does not resolve (mod not mounted: absolute
  `!Workshop` paths, see dayz-test-ingame; or `CfgPatches` does not register).
- **Visible + textured + winding**: orbit camera (≥4 poses — front/side/back/overhead) with
  `camera_set` + `capture_screenshot`; inspect each PNG. PASS = object visible (not invisible), without
  missing textures (no solid magenta/white/black), plausible proportions, without inverted faces
  or holes (winding). Hole/missing-face from one angle and solid from opposite = inverted
  winding.
- **Collision**: `scene_raycast(from_pos, to)` (default `method="rvproxy"`: LOD intersection in the
  `intersect` mode) aimed at the object in each of `geom`, `view` and `fire`: the battery below for a
  small object or an item, multi-point for a building (walls, corners, floor). PASS = rays that
  should hit yield `hit=true` with `object_type`/`object_class` of object. No hit where it should
  hit = ViewGeo/FireGeo missing or improperly resolved (LODs). *(Changed 2026-10-03: this bullet
  asked for rays "from ≥2 angles", which do not tell the causes below apart.)*
- **Ray battery and its controls** (added 2026-10-03; the battery of `dayz-p3d-audit` "Absolute
  winding check" rule 6, fired on DayZDiag 1.29.163709 on 2026-10-02, dayz-mcp run 606a5dbb)
  [EXACT][CLAIM-MCPV-COLLISION-BATTERY]: nine rays per mode.
  - One vertical ray down the object's axis. On a solid box whose collision spans its own axis,
    like the measured kit box, a LOD recentred by a missing `autocenter=0` (`dayz-p3d-audit`
    killer #3) still sits on that ray, so a miss there is not the recentring. On an object with gaps
    or several separate parts the shifted collision can leave the axis: check that the ray crosses
    the collider both where it is modelled and where the recentring would put it.
  - Four horizontal rays through the middle, one from each side, and two more heights on one side.
  - Two rays from inside the object outward: a sound object answers `entry 0, exit 1` at distance 0.

  Fire the same battery, in the same run, at two controls: an object from the same PBO and load
  path, which separates the model from the build and the loading, and a vanilla object of the same
  physics layer (`physLayer`; `WoodenCrate` sets none and takes `item_small` from `Inventory_Base`,
  `DZ/data/config.cpp:3152`; for a static, the `Land_Container_1Aoh` control under WHAT IT DOES NOT
  COVER). In that run the LFPowerGrid kit box took 0 of 27, while the same PBO's logic-gate kit and
  `WoodenCrate` took 21 of 21 each (the battery without the two extra heights). The battery locates
  a miss; it does not name the cause. When the suspect is the winding, only a pair that changes the
  winding alone decides: the kit's paired run in rule 6 did; the Rule 12 pair, which also turned the
  Visual LOD and the normals, supports the cause without deciding it.
- **Picking an item up proves nothing about its collision** (added 2026-10-03; vanilla 1.29 and
  bridge source read, the pickup seen in the same run) [EXACT][CLAIM-MCPV-PICKUP-NO-RAY]. Vanilla
  targeting casts `RaycastRVProxy` from the camera, 5 m, with the default `ObjIntersectView`
  (`4_world/classes/useractionscomponent/actiontargets.c:211-219`, `3_game/global/dayzphysics.c:88`),
  and at a camera pitch of −45° or lower it also takes the objects of a 30°, 3 m cone and scores them
  by their distance to that ray, with no hit on them needed (`actiontargets.c:286-287`, `:444-445`,
  `:730-735`). The take action's target condition then checks only the distance to the object's
  position: `ActionTakeItemToHands` uses `CCTObject`
  (`4_world/classes/useractionscomponent/actions/interact/actiontakeitemtohands.c:13`,
  `4_world/classes/useractionscomponent/targetconditionscomponents/cctobject.c:10-22`), and its other
  conditions (takeable, not being placed or deleted, attachment state, room in the hands;
  `actiontakeitemtohands.c:31-41`)
  do not look at collision either. `action_use`
  builds its world target from the nearest object of the class, with `componentIndex -1` and the
  object's position as the cursor hit, and casts no ray (`MCPClientBridge.c:3769`, `:3783`,
  `:3861`). In that run `action_use(ActionTakeItemToHands)` put the kit box in the player's hands
  while all 27 rays of its battery missed it. Read collision from `scene_raycast` against a
  same-layer control. `intersect="view"` is the cursor's mode, but the bridge casts a 0.05 m sphere
  when the radius is 0 (`MCPBridge.c:2496`, `:2528-2531`), where the vanilla ray has none. The cone
  path is read in the source, not measured: no MCP verb sets the camera pitch.
- **Physics and player collision** (added 2026-10-02, measured on DayZDiag 1.29.163709)
  [EXACT][CLAIM-MCPV-COLLISION-PROBES]: `scene_raycast(method="bullet", radius=0)` casts
  `DayZPhysics.RayCastBullet` in the server's physics world, restricted to the layers BUILDING,
  DOOR, VEHICLE, ROADWAY, TERRAIN, ITEM_SMALL, ITEM_LARGE and FENCE (`MCPBridge.c:2983-3004`); the
  default `rvproxy` intersects the LODs instead. Count a hit only when `object_type` is the target
  and the position is where its face should be: a vertical ray through a box without collision
  returns `hit=1` on the terrain. A miss alone does not prove the object has no physics shape (its
  layer may be outside the mask), and a hit does not mean the player collides (the `WoodenCrate`
  below).
  For player collision the run teleported the player 4 m from the object's centre and called
  `player_move(to=<4 m past the centre, on the far side>, speed="walk", hold_s=10)`, then read the
  end position with `query_player_state` (server). Blocked means `arrived:false` AND the player
  stopped just before the face, after the full hold (about 0.36 m before it on that run's 2 m
  boxes); `released_by:"hold"` only says the hold expired, and `arrived:false` anywhere else is
  INCONCLUSIVE. Free means `arrived:true` (7.5 m in about 5 s); walk the same distance and bearing on
  open ground as the free reference. Every walk of that run went north nearly straight ahead
  (`applied_angle_deg` 0, and 0.04 on one walk), so it did not exercise a steering angle or its
  sign.
  A walk-through alone does not prove missing collision geometry: a vanilla `WoodenCrate`
  (`item_small`, low) took every ray and did not stop the player, while a `HescoBox` (`item_large`)
  stopped it; that run did not separate the crate's layer from its height.
- **Axis-aligned test fixtures: try `rotation=64`, then check the pose** (added 2026-10-02, same
  run): `rotation=0` leaves the bridge's `RF_DEFAULT` (512, the config's placement), which yawed an
  `Inventory_Base` probe about 10 degrees (a side-face reading moved 0.22 m across 1.2 m of the face);
  `rotation=64` spawned the same box with its faces on the world axes (equal readings at both
  offsets), on flat concrete. `scripts/3_game/ce/centraleconomy.c` gives 64 two names, `RF_IGNORE`
  ("object will spawn as model was created", :56) and `RF_RANDOMROT` (:62); the result agrees with
  the first comment and does not settle how the engine reads the value. Before trusting face
  coordinates, check the pose: two parallel rays at one height on a vertical face catch a yaw
  (unequal readings) but not a tilt, so also read `scene_raycast(method="bullet")` normals on two
  faces that are not parallel, such as a side and the top (a tilt about one face's normal leaves
  that normal unchanged), and check that each lies along its axis, allowing for the ground: the
  statics below read up to 0.31 degrees off the axis, the terrain about as much, the items on it.
  Read the fixture again a few seconds later. It may change an item's configured resting side;
  slopes and settling were not measured.
  The `normal` of a default `rvproxy` reply is not a face normal (added 2026-10-02, two runs)
  [EXACT][CLAIM-MCPV-RVPROXY-NORMAL]: the bridge copies the engine's `RaycastRVResult.dir`
  (`MCPBridge.c:2958`), for a ray the "direction and size of the intersection"
  (`scripts/3_game/global/dayzphysics.c:104`), as `enforce-script-reference` ("Surface normals")
  found on house walls. In this run and in run cf2d6bb3 it lay along the ray in all 190 `rvproxy`
  hits on an object, the box yawed about 10 degrees included ((-1.963, 0, 0) and (-1.966, 0, 0)),
  and its length is the ray's path through the object: (-2.1, 0, 0) across a 2 m box is its width
  plus the 0.05 m sphere at each side. `bullet` returns the hit face's normal (`MCPBridge.c:2998`):
  a unit vector in all 40 of its hits, up to 0.31 degrees off the axis on the `HouseNoDestruct`
  statics and on the axis on the items. *(Corrected 2026-10-02: this entry read the pose from the
  returned `normal` lying along the axis, citing (-2.1, 0, 0); with the default method it always
  does.)*
  An item can come out with its sides swapped, and none of these checks shows it (measured
  2026-10-02 on DayZDiag 1.29.163709, dayz-mcp run cf2d6bb3) [EXACT][CLAIM-MCPV-ITEM-YAW]: one MLOD
  held two 2 m boxes, A (x -3..-1) in `Component01` and B (x 1..3) in `Component02`, and a twin had
  B in no component; each model was spawned, binarized and as MLOD, with `flags=8389668` and
  `rotation=64` as `HouseNoDestruct` and as `Inventory_Base` (`item_large`). On the four statics the
  west box was A, as modelled: it answered as component 0 (`Component01`; `Component02` reads 1),
  and on the twins it was the only box that took rays. On the four items the boxes had swapped
  sides, as a turn of 180 degrees about Y leaves them: the west box answered as component 1, and on
  the twins every hit was component 0 on the east box while the west box took no ray. The boxes are
  symmetric in z, so these rays cannot tell that half-turn from a mirror in x. Parallel rays read
  equal on the items too, and the normals pointed the same way as on the statics, since the swap
  keeps every face on the axes; a fixture symmetric about its origin, like the single box above,
  cannot show it, and `object_inspect` returns memory points in model space (`GetMemoryPointPos`,
  `MCPBridge.c:2240`), not the pose. So give the fixture sides a ray can tell apart and check which
  answers where: one component per side, read from the `component` of `rvproxy` hits (`geom`,
  `view` or `fire`; the bridge leaves it 0 on `bullet` hits, `MCPBridge.c:2983-3004`), or a
  collider on one side only. Put the parts off-centre in z as well to tell a half-turn from a
  mirror, and probe along z too: a quarter-turn moves parts that lie along x onto the z axis.
  `telemetry_read(mode="object_at")` returns the object's `GetOrientation()` (`MCPBridge.c:3137`);
  that run did not read it. Not measured: whether the swap is fixed or random (all four items
  swapped; 64 is also `RF_RANDOMROT`), other `rotation` and `flags` values, base classes and layers,
  and the cause.
- **Standing on top: move the player before reading its height** (added 2026-10-02, measured on
  DayZDiag 1.29.163709 in a later run, on 2 m boxes) [EXACT][CLAIM-MCPV-STAND-PROBE]: a second
  reading of the object's physics body next to the walk-into probe above, on its top instead of a
  side face. An idle player is not a probe. After
  `player_teleport(pos=[x, <top + 0.07>, z], skip_clearance_check=true)` the player kept the
  teleport height (y 340.6000) and did not fall, on a box top and above open ground alike: the
  server read it twice over 3-4 s (`query_player_state`), and above open ground the client's
  physics position (the `start_pos` that `player_move` reports) still read it 15 s after the
  teleport (the worn-items section below saw the same after a teleport to y=160). Every
  `query_player_state` of these probes read godmode on, the DayZ_MCP default; the run did not
  separate the bridge, godmode and the engine as the cause. A short move applies the fall: the run
  teleported the player above the centre of each top, called
  `player_move(angle_deg=0, speed="walk", hold_s=0.5)`, then `query_player_state`. Above open
  ground the player dropped to the ground (y 340.6000 to 338.459); on the boxes, three
  `Inventory_Base` items at least 4 m from their neighbours (two outward-wound, MLOD and binarized,
  and one inward-wound), the server's y matched the top to within 0.0001 m (spawn y + 2.000 m,
  where `scene_raycast(method="bullet")` hit it) and its x, z lay 0.70-0.75 m from the centre,
  inside the 2 m top. Read the server's position after the move: with x, z still inside the top's
  footprint, y at the top's height there means the player stands on it and y at the ground means
  it fell through; an endpoint off the footprint, or any other height, is INCONCLUSIVE. Start above
  the centre of an isolated top (no other support at that height within the walk's reach, or the
  player can end on it), and run the same teleport and move above open ground as the falling
  reference. Keep the move short: 0.5 s took the player 0.70-0.75 m by the server's position read
  after the move, with the edge 1 m away; a top whose nearest edge is closer than that can be
  walked off in 0.5 s, and the endpoint check then reads INCONCLUSIVE.
- **Placement**: `telemetry_read(mode="object_at", type=<classname>, pos=<spawn_pos>, radius=2)`
  → `found=true`, `pos` ~ spawn, reasonable `orientation`. PASS = not buried or floating
  (cross-reference `pos.y` with visuals).

### Item / arma
- Load + visible/textured/winding as above, with **emphasis on proportions vs real-world
  reference** and on post-import geometry (orientation, winding) — where generated/imported
  meshes tend to fail.
- `telemetry_read object_at` → `attachment_count`, `health01`. Telemetry PASS = found + healthy
  stats.
- Collision: as for a static object, the ray battery with its two controls. Picking the item up, by
  hand or with `action_use`, does not test it (static-object playbook, "Picking an item up proves
  nothing about its collision").

### Vehicle (placement/structure only)
- Load + visible + collision + telemetry. `vehicle_enter(pos)` → `seated=true` confirms
  seat. `telemetry_read` → `engine_on_server`, `wheel_count`, `fuel_fraction`.
- `vehicle_enter` SEATS player (placement/seat). To DRIVE: drivability ladder
  (§DRIVABILITY + `references/acceptance-ladder.md`) covers autonomous driving via owner-side verbs
  (`vehicle_get_in_client`/`engine_set`/`vehicle_control`/`vehicle_telemetry`).

## CAPTURAR ARMA ALZADA / ADS (raise client-side) [VERIFIED-SR2M gate iter36→37]

To validate RAISED/aimed weapon pose (e.g. support hand grip) there is no player input
tool. Weapon raise is forced IN THE MOD, **client-side** — captured character is client's LOCAL
player, so server `init.c` override DOES NOT alter the pose client renders
(exact symptom: server log states `raised=1` but capture shows weapon LOWERED).

Drop-in: a `modded class MissionGameplay` in a gate mod (declares a `missionScriptModule` in its
`class defs`, `files[]={"Mod/Scripts/5_Mission"}`; build `-PackOnly` so `.c` survives packing):

```c
modded class MissionGameplay
{
    override void OnUpdate(float t)
    {
        super.OnUpdate(t);
        PlayerBase p = PlayerBase.Cast(GetGame().GetPlayer()); if (!p) return;
        HumanInputController h = p.GetInputController(); if (!h) return;
        h.OverrideRaise(HumanInputControllerOverrideType.ENABLED, true);  // ENABLED persiste; ONE_FRAME parpadea -> idle
    }
};
```

Key takeaways:
- 3rd-person aim pose depends SOLELY on `IsRaised()` (`dayzplayerimplement.c:1726`, AimingModel) →
  sustained raise is enough. DO NOT call `SetIronsights()`: forces ironsight camera which fights MCP
  free-cam, and server-side left weapon untextured.
- `WeaponADS()` (`human.c:86`) is INPUT flag without script override (`human.c:234-255`) → always 0
  even if ADS works. Success signal = `IsRaised()` / client log, NOT `WeaponADS()`.
- Keep `OverrideRaise(ENABLED)` server-side (init.c) as well so server agrees.
- Judge grip by hand at NATIVE resolution (crop orbit frame), never rescaled
  contact-sheet. Grip mechanism + geometric parity: skill `dayz-animation-pipeline`
  (`references/weapon-in-hands.md`).

## TOOL → WHAT IT VERIFIES

| Tool | Verifies | Failure signal |
|---|---|---|
| `world_spawn` | classname loads | `unknown_type` / `spawn_failed` → mod not mounted |
| `camera_set` + `capture_screenshot` | render: visible, textures, winding, proportions | invisible / magenta / holes |
| `scene_raycast` (default `rvproxy`) | LOD collision (Geometry/ViewGeo/FireGeo, by `intersect`) | no hit where it should hit |
| `scene_raycast(method="bullet")` | a physics shape on the masked layers (static-object playbook) | no hit on the target where it should hit; a miss alone is not proof |
| `player_move` walk + `query_player_state` | the player stopped by the object (static-object playbook) | `arrived:true` through it; a walk-through alone is not proof |
| `telemetry_read` (object_at) | placement, orientation, attachments, health | `found=false` / buried pos |
| `bridge_status` | peer liveness (gate) | `last_poll_age_s=null` → bridge down |
| `world_time_set` / `world_weather_set` | reproducible scene for captures | — |

## WHAT IT DOES NOT COVER (ALWAYS declare in report)

- **Player and UI actions**: open/close doors, interactive inventory, shooting, reloading,
  menus. There is no generic player input tool. (Driving IS covered — ladder
  §DRIVABILITY / `references/acceptance-ladder.md` with owner-side verbs.) For a building, geometry/collision YES;
  **doors NO** → manual test.
- **`exec_enforce`** does not execute on the headless diag server (GATE4B-LIM, engine limitation like
  MakeScreenshot) — do not rely on it to "execute arbitrary verification logic".
- **`telemetry_read`** is exposed as-is (BUG-010/011/012, hardening pending): does not certify
  large JSONL fixtures or extreme ranges.
- **CONTINUOUS actions (with progress bar): `action_use` STARTS them but does NOT COMPLETE them**
  (measured 2026-09-07, LFPowerGrid, ledger entry `fb-20260907-184749-3fc1`). Returns `ok=1, started=1` and the
  server effect **never arrives**: `OnFinishProgressServer` does not fire and the target remains in
  the world (`entities_query` at 0.003 m after two attempts with 60 s and 45 s waits). `key_press`
  is **not** the way out: it documents itself "not OS input, key-up, hold", and a continuous action
  needs SUSTAINED input. This immediately kills **dismantling, deploying/deploy, and crafting**, which
  is precisely how a mod moves money and persistent objects.
  - **What CAN be affirmed, and it is not little**: the CONDITION is evaluated for real, so
    `started=1` means "valid candidate" and serves as a measure that the mod **offers** the action
    on that target in that state. Always verify it with a negative control that must come out
    red (an excluded target returns `condition_failed`), or `started=1` proves nothing.
  - **Corollary that bites separately**: since deploying from a kit is a continuous action, **there is no
    way via MCP to create a truly persistent object** — `world_spawn` uses default flags
    and does not survive restart. Add that `dayz_test_stop` does not shut down gracefully (the
    next startup prints `... was not closed. Always shut down the server gracefully`) and
    **no test of `OnStoreSave`/`OnStoreLoad` between restarts is conclusive via MCP today**.
    If the result comes out "did not persist", that is the harness, NOT the mod: do not report it as a bug.

- **`class Doors` (`Building`) doors do NOT open by MCP without `door_index`** (measured 2026-09-07, LFSecure I-0/I-4, PBO L4):
  `action_use(ActionOpenDoors, classname=<door>)` returns `condition_failed` even with the player 1.4 m away,
  because the bridge builds the `ActionTarget` with `componentIndex=-1` and `Building.GetDoorIndex(-1)` (native,
  `3_game/entities/building.c:17`, "index of the door based on the view geometry component index") resolves no
  door. `object_anim(source=<door source>, phase=1.0)` answers `phase=1`, but the engine's door controller returns
  it to its "wanted" phase (re-read `phase=0`) and `IsDoorOpen(index)` stays false, so every action that needs an
  open door also returns `condition_failed`. Without `door_index`, opening/closing, sound and sync were a MANUAL
  test (the user's F) and MCP could only verify "starts closed" (`object_anim` reads `phase=0`); see the update below.
- Update (measured 2026-10-01, DayZDiag 1.29.163709, test building whose door component is a button on a moving piece) [EXACT]: `action_use` with `ActionOpenDoors`/`ActionCloseDoors` and `door_index` DOES open and close the door even there. `object_anim` (`SetAnimationPhaseNow`) on the door's source still cannot hold a static pose: the door settles at `ajar` with phase 0.07 instead of the requested phase — doors cannot be posed statically. For the verdict, use `object_doors` and rays.
- **`setup_failed` is a FALSE NEGATIVE for local instantaneous actions** (`IsLocal() && IsInstant()`:
  `ActionTogglePlaceObject`, `ActionDropItemSimple`; measured 2026-09-07): the bridge checks
  `GetRunningAction()==null` right after `PerformActionStart`, and an instantaneous action has already finished.
  The hologram appeared and the object fell to the ground in both cases. Rule: with `setup_failed` on an instantaneous
  action, verify the EFFECT (capture, `entities_query` of dropped object) before marking the action as failed.
- **`scene_raycast`: `entry=0` is TERRAIN and `normal` is NOT a unit normal** (measured 2026-09-07 with
  `intersect=fire` and `geom`): a vertical ray against the ground returns `hit=1`, `object_type=""`,
  `surface_type=cp_grass|cp_concrete2`, `entry=0`, `exit=0`; against an object it returns `entry=1`. The
  `normal` field is `RaycastRVResult.dir` as-is, which in line-object collision is "direction AND SIZE of the
  intersection" (`3_game/global/dayzphysics.c:104`): measured magnitudes 0.16-0.42. Its direction is the
  ray's own ("Axis-aligned test fixtures" above), so it says nothing about the face: never read it as a normal
  nor use it as a threshold (`dot >= 0.9` is never reached); a face normal comes from `method="bullet"`.
  *(Corrected 2026-10-02: this line said to use it only as direction (sign/axis).)* A mod that filters
  `!hit.entry` discards natural ground (hologram that never snaps to ground: LFSecure I-1).
  *(Qualified 2026-10-03: a ray that starts inside an object also reads `entry=0`: the inside rays of
  run 606a5dbb read `entry 0, exit 1` at distance 0 on the controls. Tell terrain by its empty
  `object_type`, not by `entry=0` alone; `entry=1` holds for hits from outside.)*
- **Collision probe with vanilla CONTROL before blaming the mesh** (measured 2026-09-07, LFSecure L3 -> L4):
  if `scene_raycast` does not hit a mod static, repeat the SAME ray (view, fire, and geom; from outside AND
  from inside) against a vanilla static spawned next to it (`world_spawn(type="Land_Container_1Aoh")`: flat
  walls, `House`, `IsBuilding()` true, also useful as a wall for holograms). Control HIT + mod MISS in all
  modes and from both sides = reversed collision convex components (inverted winding in Geometry/View/Fire:
  ODOL preserves them, engine does not see them); control HIT + mod HIT only from inside = reversed faces only in
  visuals. With the source winding restored (L4) the same ray gave the front face at +0.079 m and a wall
  of 0.42 m. The correction rule lives in `dayz-p3d-audit` (0% agreement = discrepancy, not direction).
  *(Qualified 2026-10-03: the two readings above name the likely cause, not a measured one; only a pair
  that changes the winding alone decides it, as "Ray battery and its controls" in the static-object
  playbook says.)*

## REPORTING

A report with: criteria table (criterion · PASS/FAIL/INFO · evidence), PNGs and telemetry/raycast
JSONs as evidence, global verdict, and a **"to manual test"** section with what is
not covered (doors, shooting, etc.). Context cost: each capture weighs ~25k tokens (~240-320
px) — **batch** orbit-pose captures and do NOT re-read a PNG except to verify something
concrete (images inflate context quickly). Hard budget ~25k tokens/image: do not request
higher resolution.

## TROUBLESHOOTING

| Symptom | Cause | Fix |
|---|---|---|
| `claude mcp list` → `× Failed to connect` | `claude mcp list` is NOT reliable: gives false `Failed` with the server operational. E4 contention on port 8765 (`ExclusiveThreadingHTTPServer` lock, fail-closed) was the PRE-broker failure mode | verify FIRST with ToolSearch (`mcp__dayz-mcp__*` tools available? → all OK, ignore `Failed`). Broker registration `--client` (since 2026-06-24) overcomes E4 contention: N sessions share the server without fighting for 8765, and orphan-guard releases orphans alone. If tools are truly missing: register in broker mode (`--client`) and open NEW session (tools load at startup) |
| tools do not appear in session | server was registered AFTER opening session | open a new session (MCPs load at startup) |
| `bridge_status.server_peer.last_poll_age_s = null` | server bridge does not poll | check `dayz_mcp.json` in server_profiles + key; confirm `@DayZ_MCP` mounted (absolute paths `!Workshop`) |
| `client_peer … null` (server ok) | client does not connect or `client_profiles\dayz_mcp.json` missing | BUG-009 (flaky autoconnection): larger `-ServerWait` / retry; seed client config |
| `version_state = legacy_blocked` | `--require-version` ON against a bridge not sending `ver=` | deploy 4B PBO (sends `ver=4~…`), or register server without `--require-version` for that run |
| byte-identical captures between poses | grab caught a stale desktop frame (not render) | [EXACT] `PrintWindow(hwnd, hdc, PW_RENDERFULLCONTENT=2)` on the client's main window DOES capture the D3D game area — full scene in >20 captures even with another window covering it and without taking focus, as long as the Windows session is unlocked and the display is on (measured in game, DayZDiag 1.29, 2026-09-28). A black game area means the display is off or the session is locked, not that the route cannot read D3D. `CopyFromScreen` only works with the window in front, and a covered DayZDiag also drops to ~20 FPS; validate on a crop of the game area, not whole-frame variance (corrects the LL-247 entry of 2026-08-12) |
| tool timeout and then "zombie" commands on reconnect | BUG-024: timeout leaves command queued; bridge executes it on return | after a timeout, reconcile with `bridge_status` before continuing |

## REFERENCES

- `dayz-test-ingame` — build/deploy/launch (this skill composes it with `-ExtraMods "@DayZ_MCP"`).
- `DayZ_MCP_dev\tools\README-mcp.md` — startup order + bridge troubleshooting.
- `DayZ_MCP_dev\HANDOFF.md` (LIVE-STATE) — server invariants, 11 tools, GATE4B-LIM, backlog.
- `_shared\dayz-conventions.md` — L2 (LODs, ViewGeo/FireGeo, DayZ response format).
- Precedent of camera+orbit capture: A6's `gate-mcp.ps1` (window-grab by orbit,
  dayz-test-ingame finding 2026-06-17) — alternative batch sweep to agent driving tools.


## VEHICLE: repeatable smoke recipe (added 2026-06-24)

Visual smoke of a CarScript vehicle driven by MCP, verified end-to-end on MercedesAMGLF
2026-06-24. Repeatable without re-deriving:

1. **Mission = stock `dayzOffline.chernarusplus`** (from DayZServer install), NOT a Phase 0
   mount-probe `void main()`: mount-probe spawns no player → client does not render the world and
   capture comes out black. Stock spawns player (`CreateCharacter`→`CreatePlayer`) → free-cam with rendered
   world. Pass it with `-Mission "<...>\dayzOffline.chernarusplus"`.
2. **Bridge seed in profiles generated by `dayz-test.ps1`**: `dayz_mcp.json`
   `{"url":"http://127.0.0.1:8765/","key":"<key>","pollHz":5}` (ASCII) in `<Mod>_dev\_server\profiles\`
   and `..\_client\profiles\`. The bridge reads it from `$profile:` (server `MCPBridge.c:125`, client
   `MCPClientBridge.c:211`); key = `DayZ_MCP_dev\tools\.dayz_mcp.key`. Seed BEFORE launch (the
   bridge reads config in its init, only once). Do not use `install-mcp.ps1 -Register` (re-registers
   broker mode `--client`).
3. **Launch**: `dayz-test.ps1 -Mod <Mod> -Mode all -Build -PackOnly -ExtraMods "@DayZ_MCP" -Mission
   "<...>\dayzOffline.chernarusplus" -ServerWait 240`. `-PackOnly` mandatory in mods with `.c`
   (binarize drops them → NO_IGNITER). Call the `.ps1` via absolute path (P:\ is subst).
4. **Readiness**: stock runs CE (`InitOffline`) ~1-3 min; during CE `bridge_status` comes out
   STALE (`last_poll_age_s` grows even though `version_state=ok`) — do NOT spawn there. Wait for `connected to
   server` in server's `script*.log` and for `bridge_status` to return fresh (<1 s). Poll
   log host-direct with PowerShell, NOT bash Monitor (inherits bindfs cache, LL-142).
5. **Smoke** (grouped, R5): `world_time_set(year,month,day,hour=12,minute=0)` (all 5 mandatory) + `world_weather_set overcast=1.0` → `world_spawn
   <Class> pos≈[player+~10]` → wait 30 s (survives without native crash = LL-099 ruled out) →
   `camera_set` (cam_mode **"lookat"**, `cam_pos`+`look_at`) + `capture_screenshot` + `scene_raycast` +
   `telemetry_read object_at`. Healthy telemetry = `found=1`, `health01=1`, `velocity 0`.
6. **Flaky capture**: grab sometimes catches loading screen or client's "Continue" menu overlay
   instead of render. If it happens: wait for settle (~30-40 s in background — foreground sleep is
   blocked in this environment) and recapture; use several angles. Top-down that clearly reveals proxy
   (mis)alignment: `cam_pos=[carX+3, 16, carZ+1]` `look_at=[carX, ground+0.1, carZ]`. ~25k
   tokens/image — batch captures, do not re-read a PNG except to verify something concrete.
7. **User's eye > capture** when render is ambiguous: in MercedesAMGLF grab was flaky and
   user reading was reliable diagnosis of winding and proxy alignment. If there is a human in
   the loop, cross-check with them. (Case s3 2026-06-24: I was about to sign PASS on faint renders; user's
   eye caught proxy misalignment I could not resolve → correct FAIL.)

8. **SHARED SESSION.** Port 2302 and Steam client remain single resources, but
   exclusion is coordinated with the runbook's FIFO lease, not attributing processes nor evicting
   other sessions. `dayz_test_run` acquires and maintains exclusion; retain `run_id` and
   terminate that same run with `dayz_test_stop`. NEVER kill a process to unlock the box:
   if state does not reconcile, retain the process and declare degraded shutdown.

9. **"Wheels = sheet/flat disk" is NOT a proxy bug.** A `world_spawn` of a CarScript without attachments leaves
   `wheel_count=0`/`attachment_count=0` → only hub/disk is visible, without tires. Expected in visual smoke; real
   wheels require attachments (physics phase), out of scope for smoke.

10. **`legacy_blocked` ("poll did not include ver=") is usually INCOMPLETE INIT, not version mismatch (added
    2026-06-28).** Refines the homonymous row in TROUBLESHOOTING: with 4B PBO deployed, right after launching server
    `bridge_status` can come out `legacy_blocked`/`last_poll_age_s=null` because the bridge has not yet completed the
    handshake; transitions to `ok` with `ver=4~…` when server mission LOADS completely (~1-2 min). Do NOT redeploy nor
    re-register for that — wait and re-check. It is only a real mismatch if it stays `legacy_blocked` with mission already
    loaded (client connected, world rendered). Origin: SUB_BRZ Phase 5 2026-06-28.

11. **Historical pattern superseded 2026-07-15.** `cmd start`/`.bat` avoided a background job
    losing its child, but created a process outside the registered lifecycle. For any current
    smoke, use exclusively `dayz_test_run`, retain its `run_id` and terminate only that run with
    `dayz_test_stop`. No unmanaged fallback exists to bypass the lifecycle guard.

## DRIVABILITY + ACCEPTANCE LADDER (summary — detail in reference)

Phase 5 of DayZ-MCP project added and gated in-game owner-side verbs that DO **drive** the
car (client takes ownership and handles throttle/steer): `vehicle_get_in_client(pos)` (seats +
ownership), `engine_set("start"/"stop")`, `vehicle_control(throttle, steer, brake, handbrake,
hold_ttl_s)` (SUSTAINED control, fail-closed), `vehicle_telemetry()`, `vehicle_release()`, and
`query_get_in_condition(pos, component)` (server peer, diagnoses which of the 7 gates of
`ActionGetInTransport` blocks). On top of them runs the **acceptance ladder** rip→drivable:
ordered rungs **R1 spawns → R2 render → R3 get-in available → R4 seated → R5 drives → R6
wheel direction**, each reading in-game ground-truth and mapping its failure to a known fix in the
SUB_BRZ taxonomy (`dayz-vehicles/references/`). Reference orchestrator `references/drive_ladder.py`
(drives R1→R6, outputs `verdict.json`; does NOT apply fixes nor rebuild) + fixtures `tests/test_drive_ladder.py`.

**Full detail** (verbs, verified owner-side mechanism, preconditions, spawn placement,
R2.5 restore-gameplay, anti-false-green guardrails, ladder table, and failure→fix mapping) →
`references/acceptance-ladder.md`.


## (added 2026-07-14) No restore-gameplay tool: for user MANUAL test, relaunch without @DayZ_MCP

`camera_set` ALWAYS suppresses player control (`SuppressGameplay()` -> `PlayerControlDisable`, see
§R2.5) and **there is NO MCP tool that fires `RestoreGameplay()`** — only internal gate `drive_probe_client`
does it, and it is not exposed as a verb/tool. Practical consequence: after an MCP smoke that used `camera_set`
(free-cam or static-cam lookat), the USER cannot take player control to test the car by hand
— their input remains suppressed and there is no verb to revert it on the fly.

Rule: when workflow passes from MCP smoke (automatic) to **user manual test** (driving, judging
feel/aesthetics), **relaunch the game WITHOUT `@DayZ_MCP`** (or at least with a client that never received
`camera_set` in that session). A clean client has normal control. If the client was already neutered:
reconnecting (Esc -> Disconnect -> Reconnect) recreates the player with clean camera/control; there is no tool
shortcut. Origin: SUB_BRZ s35 — time was lost looking for a non-existent restore tool and user had
to close the game and ask to relaunch normally.

## (added 2026-07-14) Autonomous smoke: world_spawn takes engine [x, y_up, z], and capture with sleeping display = black frame (SP-060)

Dos caveats de smoke MCP autonomo verificados in-vivo (SUB_BRZ s32):

1. **`world_spawn` takes vector in ENGINE order `[x, y_up, z_north]`** (`MCPBridge.c:1638` `Vector(x,y,z)`), but bridge connect-log prints player position as `<x, z_north, y_up>`. Passing the log triplet VERBATIM spawns the object at ~6 km altitude -> `IsSpawnReady` (2.0 m radius) is never satisfied -> job timeout + `found=0`, and engine auto-deletes the orphan (`NETWORK (E): Will delete object ... outside world coords`). Cost 3 timeouts in a row. Rule: convert `<x,z,y>` -> `[x,y,z]` before every `world_spawn`/`camera_set`; after a spawn timeout, grep RPT for `outside world coords` BEFORE retrying (distinguishes bad-coords from slow-spawn). Verifiable with `scene_raycast` to terrain (gives real y_up).
2. **Capturing with the display asleep = BLACK frame** even though the client runs (on 2026-07-11 a locked session with LockApp also gave black frames; since 2026-09-14 the capture backend fails outright on a locked session instead, see point 4). Fix: bring the client window to the foreground + input wiggle (mouse / F15) before EVERY `capture_screenshot`. Misleading symptom: it looks like "the mod's render is broken" and it is the compositor.
3. (minor) Spawn adjacent to player can fall INSIDE a building -> probe 3-4 `scene_raycast` to clear terrain before choosing pos.
4. [EXACT] A locked Windows session is a distinct capture failure (added 2026-09-14, SUB_BRZ s93): with `LogonUI` alive, `capture_screenshot` does not return a black frame — it fails outright with `capture_backend_failed` on every attempt while the game client stays alive and probing. Before budgeting captures in an unattended run, run `Get-Process LogonUI` first: with a locked session there is no host capture at all, for the MCP capture and for any window-grab script. (measured in game, DayZ 1.30.164014 Exp)

Origin: SUB_BRZ s32 MCP smoke (2026-07-11): 3 `world_spawn` timeouts with raw log pos + 2 black captures with LockApp; both resolved with the above.

## (added 2026-07-14) Telemetry numeric gates: calibrate against MEASURED PHYSICAL FLOOR, not ideal fixtures (SP-061)

Invariant for any acceptance-ladder / numeric gate on in-game telemetry (car drive_ladder, spikes, future harnesses):

1. **A threshold calibrated with ideal mathematical fixtures is a gate that no real physics passes.** The engine has a native noise floor (body dither between SetVelocity and reading; client network interpolator). Before setting a threshold: MEASURE the floor in a real run (metric p95 on real data), threshold = floor x margin (>=2x), and document the measured numbers next to the constant. Two convergent independent measurements (implementer + receiver, +-20%) validate the number. Case: LFHeli W0 batch1 - jitter gate at 0.5 m/s with real floor 4.3-5.1 m/s -> false NO-GO that cost an entire corrective pass; recalibrated gave GO with 2.2x margin.
2. **The perceptual smoothness metric is frame-to-frame zigzag in METERS (2nd difference, |delta v_implied|*dt)** - NOT |residual delta vs ideal| per frame (autocorrelated; measures 2x real zigzag) and NOT implied-velocity in m/s (scales 1/dt: same process gives different floors at 30 vs 60 FPS and breaks A/B FPS cells).
3. **Startup transients (setup teleport + interpolator chasing it) are excluded with bounded warm-up in client score window** (real transient 0.25 s -> warm-up 1.0 s = 4x margin), fail-closed everything else.
4. *(LFHeli X.5e/f extension)* **Relative STRUCTURAL checks also need an absolute floor, and frame-time mediaN is fallacious with bimodal distribution.** A run at 250 FPS with bimodal frame-time (4 ms bursts + ~50 ms population) broke three relative thresholds: max-gap 3x median, dt-tol 30%*dt, coverage span/median_dt. Fixes: absolute floors with physical basis (gap 0.150 s; dt-tol 0.015 s) and coverage by mean of dt column (mean of t DELTAS is TAUTOLOGICAL: span/(n-1) -> ratio ~1 always - vacuous check, G3 pitfall).

Cross-ref `dayz-vehicles` (drive_ladder) y `dayz-mod-workflow` ("primer run real -> retune, no NO-GO"). Origen: LFHeli X.5d (2026-07-11), doble medicion convergente + selftest 31/31.

## (added 2026-07-14) Telemetric gates (extends SP-061): float epsilon at boundaries + AGGREGATED temporal balance invariant (SP-063)

Two adversarial defects reproduced on an already double-sealed gate (Codex re-seal, confirmed by receiver):

1. **Temporal threshold comparators need float representation epsilon.** A "boundary precisely tolerates" contract (gap 150 ms / deviation 15 ms) is violated in binary: accumulated deltas give `0.15000000000000002 > 0.15` -> boundary false REJECT, and NOT deterministic. Fix: `> limit + EPS` (1e-6 s) in EACH temporal comparator, with N-1/N/N+1 boundary fixtures (149/150/151 and 14/15/16 ms).
2. **Coverage by count x mean is an evadable IDENTITY by biasing the denominator.** `rows >= K*span/mean(dt)` <=> `sum(dt) >= K*span`: a SUSTAINED +50% biased dt column (under per-row floor) compensates for 40% lost rows -> fail-open GO on incomplete trace. Fix: AGGREGATED two-sided balance invariant `|span - sum(dt[1:])| <= max(1%*span, 0.1 s)` - for honest producer it is ~0 by physical identity; measured <=0.0001% of span in 9 real CSVs vs 9.98% in adversarial fixture.
3. **(Meta) per-row floor + aggregated invariant are a mandatory PAIR**: per-row catches isolated outlier; aggregated catches small sustained bias. A single level leaves an open flank - and fixture demonstrating it is COUPLING of two checks "closed" separately.

Cross-ref `dayz-vehicles` (drive_ladder). Origen: re-sello LFHeli X5EF (2026-07-11), F-01/F-02 con outputs literales + fixture cruzada 40%-drops + dt-6ms -> GO fail-open.

## (added 2026-07-18 s37) Server-side conditioning of a custom car (real OnDebugSpawn)

`vehicle_get_in_client` executes OnDebugSpawn CLIENT-side = no-op under server authority
(symptom: misleading `vehicle_fixture_ready=1` with `wheel_count=0`/`fuel=0` in server
telemetry). To condition for real (authoritative wheels+fluids) without touching code:
`vehicle_enter(pos)` (server seat) and then raw enqueue
`vehicle_drive {throttle:0.01, duration:0.5}` — its PREP phase executes `car.OnDebugSpawn()`
SERVER-side (MCPBridge.c:2104-2112) and the 0.5 s micro-drive is negligible. NOTE:
`vehicle_drive` requires the SERVER-side seat (gives `not_seated` with owner-client seat).
`vehicle_prepare_fixture` takes any `CarScript` classname: an object of another class fails with
`fixture_not_vehicle` (`DayZ_MCP_dev/addon/scripts/5_Mission/MCPBridge.c:1214-1280`).
[EXACT][CLAIM-MCPV-PREPARE-FIXTURE-ANY-CARSCRIPT] Between 2026-08-18 and 2026-10-01 it returned
`vehicle_fixture_ready=1` with `wheel_count` 4 on 15 other `CarScript` types, among them `SUB_BRZ`,
`LFQuad2`, `Arma2Quad`, `Hatchback_02` and the vanilla `CivilianSedan`; three test variants of one
quad returned `fixture_not_ready`. *(Corrected 2026-10-03: this said "`vehicle_prepare_fixture` does
NOT work outside the Mercedes (`MERCEDES_AMGLF` hardcoded in MCPBridge.c:835 and loopback.py:113;
open issue to generalize it)". The loopback copy of 2026-07-25 still had that check; the tools'
2026-08-16 release does not.)* Raw `/enqueue`
requires `{identity, lease_token}` in body in addition to `?key=` (identity/token come from
`session_acquire`). gear idx of `vehicle_telemetry`: 0=R, 1=N, 2=1st ... 7=6th.
Verified in-game SUB_BRZ s37 (wheel_count 0->4, fuel 1.0, complete kit, run B3 to 6th).

## (added 2026-07-22) Bare spawn exposes undercarriage → looks like misalignment; condition before judging alignment

A `world_spawn` of a CarScript vehicle creates it WITHOUT attachments (`wheel_count=0`, `attachment_count=0`): wheels/tires are NOT there, so **brakes (rotor + caliper — caliper is usually RED), suspension and hubs remain EXPOSED** in the wheel arch and are seen "floating" with a gap. **That is NOT misalignment**: it is correct base geometry, symmetric and in place, contained within the volume the absent wheel would occupy.

Rules:
- A smoke with **bare spawn is MATERIALS-ONLY** — validates body paint/textures/winding, NOT undercarriage alignment nor "complete" look.
- To judge alignment/look WITH wheels: **CONDITION** the car (`wheel_count 0→4`) with `vehicle_enter(pos)` + server-side micro-drive (`OnDebugSpawn`; see note "Server-side conditioning (real OnDebugSpawn)" s37 above) and recapture with wheels on.
- Faced with a part that "looks displaced": **MEASURE before concluding** (bbox/centroid/left-right symmetry + bisection vs backup + containment in wheel volume) — do not sign "broken" or "OK" by opinion.

Verified: SUB_BRZ 2026-07-22 — a "misaligned parts" scare turned out to be exposed brakes/suspension from bare spawn; forensics (Codex, py3d) measured symmetry ≤0.003 m, 0-movement bisection across 6 shells, and containment in wheel volume (`<rip-import>\work\reviews\2026-07-22-SUB_BRZ-misalign-forensic.md`). Cost 30 min of avoidable forensics. Cross-ref LL-209.

## Rules promoted from lessons corpus (added 2026-07-27)

Promoted from `AI/20_Knowledge/lessons-learned.md` so they arrive via trigger instead
of depending on someone remembering to look them up. Each rule cites its originating `LL-NNN`;
the full entry (symptom, origin, evidence) lives there. Do not remove the citation: the
`lessons-index.md` index detects promotion by searching for that reference inside skills.

- **LL-181** — Before blaming the mod for an automated FAIL, verify the actuator/bridge source and confirm the stimulus reached the subject. Run an equivalent delta control or manual test to distinguish a harness defect.
- **LL-187** — If several defenses intercept the same failure, design a per-layer repro reaching its protection point. Demand each layer's specific signal; an aggregated PASS of “does not fail” does not prove all work.
- **LL-202** — At the first anomalous error of a client-side verb, verify the client's PID, its RPT tail, and `bridge_status` before continuing. If peer died, extract minidump/evidence and document degraded shutdown; do not diagnose subsequent errors as harness state.

## The daemon serves the code it loaded at STARTUP — a new verb does not exist until restarting it (LL-223, added 2026-07-29)

If you add a verb to the bridge (`SERVER_COMMANDS` / `CLIENT_COMMANDS` in `loopback.py`) and the tool
responds **`not_whitelisted`**, do not look for the bug in your diff: the **daemon** loaded that module
when it started and has not read it again. `loopback.py` and `server.py` are NOT sealed in
`app.pyz` —editing them takes effect without bundle rebuild— but that restarts nothing.

What deceives most: the tool **does appear registered** in your MCP client, because the client started
after the edit. The visible half of the system confirms the verb exists while the
deciding half remains with the old list.

**Command check** (source mtime vs startup of deciding process):

```powershell
(Get-Item '<...>\dayz_mcp\loopback.py').LastWriteTime
$pid_ = (Get-NetTCPConnection -LocalPort 8765 -State Listen).OwningProcess
(Get-CimInstance Win32_Process -Filter "ProcessId=$pid_").CreationDate
```

Source newer than process = that is the cause, stop looking at code. Measured 2026-07-29:
`loopback.py` 15:57:54 vs daemon started 14:18:42 (1 h 39 min offset).

**Restart**: `Stop-Process` on 8765 listener; client re-spawns it lazily on next
call and `daemon_generation` changes (thus confirming it is another process). Restarting the daemon
is declared safe (BUG-062b). **Warn beforehand**: momentarily disarms MCP tools of
other live sessions, so check `session_status` (owner/queue) first.

**After restart there is a re-handshake window**: first calls may return
`version_blocked` or `peer_reconnect_flush`. They are transients — retry, do not rediagnose.
Confirm with `bridge_status` that both peers have `version_state: ok` and low `last_poll_age_s`.

Sibling but distinct from sealed bundle trap: there `app.pyz` seals COPIES of modules
from the test lifecycle (`dayz_test_worker.py` et al.) and rebuild+CAS is needed; here there is no
sealing at all, it is enough for the process to be old.

Origen: DayZ_MCP, gate in-game de `query_all_players` (2026-07-29).

## "Open mod UI without keyboard" chain VERIFIED in-game + three pitfalls of use (SP-292, added 2026-08-18)

Cycle 1 gate of DayZ_MCP (2026-08-17, run `28f2e26f`, PBO `BCA758A1…`): full chain works end-to-end.
Measured recipe (LFPowerGrid + @DayZ_MCP; adapt names to mod):

1. `dayz_test_run(project="LFPowerGrid", mode="all", extra_mods=["@DayZ_MCP"])` → `wait_for(log_matches, "OnStoreLoad SUCCESS")`
   (77 s / 26 probes) → `session_acquire_wait(purpose=…)` (adopts run: check `adopted_run`) → `wait_for(players_at_least, 1)`.
   (rev. 2026-09-06: previous order in this recipe probed `players_at_least` BEFORE adopting; that probe crosses the
   bridge and idle run fence rejects it with `run_not_owned` — §COMPOSITION, "Bridge startup sequence".)
2. `world_spawn(type="LFPG_BTCAtmAdmin", pos=[x,0,z])` ~3 m from player → `action_use(action="LFPG_ActionOpenBTCAtm",
   classname="LFPG_BTCAtmAdmin", radius=5)` → `started:1` (lookup by `Type().ToString()` works at runtime).
3. `wait_for(log_matches, "[BTCOpenResponse]", lookback_lines=200)` — **with lookback**: response lands ~200 ms after
   trigger and with cursor "from now" it is ALWAYS lost (BUG-086, 2/2 timeouts with line already in log).
4. **`ui_tree(path="BTCAtmRoot")`** — with empty path returns `no_menu` even though UI is OPEN: a Dabs/ScriptView panel is
   a pre-created host, not a `UIScriptedMenu`. Pass root name of `.layout` (`grep -oE 'FrameWidgetClass \w+' gui/layouts/X.layout | head -1`).
5. `ui_set_text("EditBtcAmount", "1")` with INTEGER (`GetBtcInput()` is int: "0.001" → 0 → `ShowStatus` without RPC) →
   `ui_click("BtnBuyBtc")` → `clicked:1 handler=LFPG_BTCAtmView user_id=100` (`#ifdef DabsFramework` branch of `InvokeUiClick`
   fires with Dabs loaded by another mod) → `wait_for(log_matches, "[BTCTxResult]", lookback_lines=200)` and read `err=`.
6. `session_release` → `dayz_test_stop`.

Coexistence pitfall (measured 2026-08-18 00:01): `bridge_status` said box FREE (peers null, no lease, no runs) and 40 s
later a navprobe run started OUTSIDE lifecycle and WITHOUT lease; a probe executed `player_teleport` and moved ITS player.
Before any mutation on "the first human": `bridge_status.coordination.active`, `server_peer.last_poll_age_s`
and `Get-CimInstance Win32_Process -Filter "Name='DayZDiag_x64.exe'"`; if there is a server polling that is not yours, do NOT mutate.

## Verifier and bridge integrity: evidence, contract, and identity

The bridge measures and discriminates subjects; a green is only valid if the command received a response and the protocol preserves the identity it intends to isolate.

1. **Every negative criterion requires per-command liveness (LL-267).** Before resolving "X did not occur", require a response attributable to that command, for example `answered(tag)`, not a previous response from the run. Without it, the case is `INCONCLUSIVE`, never `PASS`. Publish the global response count and, if zero, abort early instead of printing a collection of verdicts. A denial case only passes after demonstrating that the subject could receive and execute the request.

2. **Census keys before closing the wire (LL-315).** Search each new top-level key in the serialized flat DTO and across all its consumers. Obvious names such as `state`, `status`, `error`, or `type` are usually taken; if they collide, nest the payload under a feature-specific object —the measured case ended up as `{ok, dialog:{state,…}}`— instead of overloading the field. The gate reads the real shared contract; the producer's suite does not accredit forward compatibility.

3. **A handshake mutation is global and authentication is not identity (LL-317, LL-319).** Before changing a version constant or deploying the PBO/daemon carrying it, inspect processes and sessions currently loading that mod. If an outside game is present, do not publish: coordinate or revert; holding your lease does not prove no one else consumes the protocol. Furthermore, maintain two fields with distinct contracts: instance identity remains stable over the process lifetime and is not hot-reloaded; the key only authenticates and can rotate. Knowing the instance does not grant authority, and a shared profile token does not identify a process. Never reuse the secret as identity.

4. **A cache must preserve the discriminator (LL-320).** Before caching fencing, authorization, rate-limit, or session resolution, write what property distinguishes the result and demonstrate that the key preserves that identity. Caching by instance allowed two processes to share a PID —the intruder received 100 out of 100 mutations and binding never switched to AMBIGUOUS—; caching the table for 50 ms hid the second polling peer —40/40 ticks without a single command—. Measure hits and cost under real pattern under load: in the measured case the useful rate was 0.0 and rest cost did not represent loaded regime. If the cache does not save measured work or merges distinct actors, it is eliminated.
## Vehicle ladder — session requirements (added 2026-08-24)

- **Verified canonical site**: ladder with drive requires a point with >=150 m clear in the driving direction (protocol requested in ledger entry fb-20260824-025758-2509). The historical G0 site froze the vehicle (positional drivability, LL-359) and the end of its line blocked get-out against statics. Do not reuse sites without evidence from the session itself (surface_query + entities_query; scene_raycast in `view` does NOT see statics that stop a car).
- **Single process lifetime**: the spawned daemon and its sequence die with the command tree that spawned them in this harness ("broke away" does not survive harvesting; adoption of an external daemon is also broken — fb-20260824-032050-9aed, LL-358). The entire run -> verbs -> teardown sequence goes INSIDE a single process (`AI/10_Projects/DayZ_MCP/lanes/2026-08-24/g0_full_abba.py` pattern: preventive stop, run, wait bridge-ready, wait player, teleport with lease, work, dayz_test_stop).

## Certified canonical site + instrumentation rules (added 2026-08-24 afternoon)
- **Canonical vehicle site: NWAF `[4200.0, 0.0, 10650.0]`** (certified 2026-08-24,
  PBO 28226C93B9B8, repo's `docs/VEHICLE_TESTING.md`): corridor 160 m x +-25 m north
  fully enumerated, drive delta_2s_xz 3.2 m, teardown verified. Re-certify with
  `python tools/g0_site_gate.py --pbo-sha256 <sha> --out <verdict.json>` (game already running,
  bridge ready; SHA is mandatory). Alternates and degradation causes in doc.
- **entities_query ONLY with player inside the area** (fb-20260824-123204-638e): far from
  any player answers 0 or cap-128 (bimodal) and is NOT a visible error. surface_query is
  globally reliable (static terrain). Corridors: 3 spheres r=65 with `count_total` as truncation
  indicator and distance check of the last row (nearest-first).
- **Canopy gate before ALL teleport to unverified coordinates**
  (fb-20260824-115220-1bc1): scene_raycast geom y+30 -> y-5 must hit at <=0.05 m from the
  surface at the PLAYER and VEHICLE point; detects roofs, tree crowns, and water (hits
  the surface sheet above seabed with negative y).
## Bridge v9 + certificado multi-agente (added 2026-08-24 noche)

- **Bridge v9** (commit d73da6c; version gate requires daemon-PBO pair): `object_anim`
  and `object_inspect` accept `object_id` (the one from world_spawn) and resolve against bridge
  registry - position-independent, reaches client-auth fixtures with replica at
  spawn. `player_teleport` rejects surface landings with covered column
  (`clearance_blocked`; `skip_clearance_check=true` for interiors). `entities_query`
  brings `nearest_player_m` + `reliability` (player_in_bubble | remote_unverified).
- **Measured caveat**: `object_anim` write APPLIES (SetAnimationPhaseNow) but
  `phase` of reply itself can lag by one tick (0 -> write 1.0 -> reply 0.0 ->
  next reading 0.599). Confirm with a subsequent reading, not with the reply.
- **Clearance probe ignores players** (ignore='player'): a survivor standing in the
  column gave dy=1.671 and rejected the point (this is how x4300 was demoted in r13 by mistake).
- **Long sessions**: diag client dies after ~6 min without commands (client_not_polling).
  Runner with keepalive (e.g. vehicle_telemetry every ~45 s) for the duration of the session.
- **Multi-agent certificate 3/3 (2026-08-24)**: Grok 4.6 (MCP-only), GPT-5.6 (codex), and
  Ox Alpha (opencode) drove spawn->fixture->seat->drive (100-163 m)->door by
  object_id->delete->release with minimal brief. The claim "agents from 3
  families drive it" has evidence in lanes/2026-08-24/ma/ in the vault.

## (added 2026-08-28) UI resolution sweep without reboot + window-grab<->engine calibration

Measured on flight F of sorter case (run dbca698d, ledger entry fb-20260828-160429-2899):

- **`dayz_test_run` width/height do NOT set client resolution** (requested 1280x720,
  real viewport 846x461). Do not waste a reboot changing resolution.
- **Validated technique**: SetWindowPos host-side (user32, SWP_NOZORDER) on live client
  window + `ui_reload_layout` -> viewport immediately re-measures, scenario and run
  are preserved. A sweep of N resolutions costs N reloads, not N boots.
- **Measured window frame (Win11)**: outer - client = 11 px left/right + 45 title + 11 bottom.
  Fullres `capture_screenshot` is 1:1 with viewport: engine_px = image_px - (11, 45).
- **The root of `ui_tree` with proportional `size 1 1` IS the real viewport** — use it as
  resolution oracle instead of trusting launcher requests.
- **Factor control**: widgets with exact flags render at declared x (height/1080),
  positions included — if reference panel does not give that exact factor, calibration
  is wrong, not layout.
- **TextWidget does not expose its text via `ui_tree`** (`text_readable=false` by contract): to
  measure GLYPHS the instrument is the frame (fullres + crop + per-pixel measurement), never the
  tree. Tag cases INSIDE strings to recognize them in capture.

## (added 2026-08-29, SP-350) THREE LAYERS that do not name each other: do not declare that a verb does NOT do something reading only Python side

The MCP server has **three layers** and none names the others in its own text:

    1. the tool in Python         `dayz_mcp/server.py`
    2. HTTP ingress               `loopback.py`, `session_coordination.py`
    3. the bridge in Enforce      `MCPBridge.c`, inside the game

Many tools are a thin wrapper ending in `runtime.call_bridge(...)`. **Real
semantics live downstream.** That is why a lane opening only one layer believes
it has the entire system before it, and signs off on behavior it has not seen.

**Measured on 2026-08-29: two independent reviewers made the SAME mistake the same
night, on the same system.**

- One reviewer declared the claim "`y=0` snaps to the ground" of `world_spawn` **FALSE**,
  reasoning that Python passes `pos` verbatim through `_require_vec3` without touching it. Premise
  was correct and conclusion false: snapping occurs in the bridge. `MCPBridge.c`:
  `ValidateSpawnArgs` sets `validation.flags = ECE_PLACE_ON_SURFACE` as default for
  `flags=0`, and `IsAllowedSpawnFlags` **demands that bit in every accepted combination except
  one**, `ECE_CREATEPHYSICS|ECE_TRACE`. Furthermore the vault already had the fact **measured four
  times** (`dayz-control-plane-gotchas.md`: `pos=[7500,0,7500]` -> `pos_real y=313.14`).
- Another reviewer declared that **"no file produces `box_claimed`"** by searching for it in
  `daemon.py`. The emitter lives two hops further, in `session_coordination.py` inside
  `box_wait_touch`, and is reached via `loopback.py`.

Both opened files and cited `path:line`. Verifying is not enough: one must verify in
**the layer where the behavior would live**.

### Reglas

1. **Before declaring that a verb does NOT do something**, check if its body ends in
   `call_bridge`. If it ends there, the only honest response is `not verifiable from Python
   side`, and stating that one would have to open `MCPBridge.c` to decide it.
2. **Before declaring that a field is not produced**, do not trust the module where assumed
   architecture would place it. Grep field name across ALL `tools/dayz_mcp/`.
3. **Before contradicting documented behavior**, grep the vault. It is memory of
   MEASUREMENTS: contradicting a measurement requires refuting the measurement, not reading code from another
   layer. Takes five seconds.
4. **Useful asymmetry**: to assert that something DOES happen, seeing it once is enough. To assert
   that it does NOT happen, one must have looked where it would happen.

### When writing a review brief

If the lane's workspace contains **only one layer**, say so in the brief and require that everything
relative to the others goes to `LO_NO_VERIFICADO`. In the run originating this section
the brief did not say so, and both lanes filled the gap with inference instead of with a
declaration of ignorance. **A well-placed "unverifiable" is worth more than a brilliant
and false finding**, because the false one travels: by the time the refutation arrived, another session had
already applied a fix to something that was not broken.

## (added 2026-08-29, SP-351) The box is shared: join the FIFO, do not wait for notice — and the oracle is the EFFECT

### `session_status`'s `blocked_on` is an ORDER, not decoration

With the box occupied, `session_status` returns literally:

    "blocked_on": "DayZ test box; next: call dayz_test_run(..., wait_for_box_s=<n>) to join the box FIFO"

Measured on 2026-08-29: an AUTONOMOUS NIGHT session read that line on each query for
**seven and three quarter hours** and kept waiting for another session to notify it that
it was releasing. The queue existed, was named in the response, and was not used.

When it was finally used: `wait_for_box_s=600` -> `active_run_exists` with
`hint: "stop it with dayz_test_stop(run_id=...)"`. Once again the next step served in the
response. And upon setting a 15 min deadline for the neighboring session, it released in two — it had spent hours
defending a fixture that **had never been used** (its own capture gave
`frame_client_all_black`, zero wiring activity on its server).

**Rules**:
1. If a tool tells you how to unblock yourself, do it before waiting for anyone.
2. **In an autonomous session there is no "wait for notice".** Either you join the resource queue or
   you put a deadline on whoever holds it. Waiting without a horizon is not courtesy: it is giving up the
   assignment. A horizon of type "when user finishes" **is not a horizon**: it is
   an open-ended dependency, and whoever offers it should release resource and request it
   again (relaunching takes minutes; a fixture is remade in two verbs).

### The oracle is the EFFECT, never the response

`ok` does NOT mean success, and there are at least four different encodings coexisting.
Measured in-game on 2026-08-29, same tool, same response, opposite effect:

    object_delete(999999999) -> ok:1, deleted:0     <- no borro nada
    object_delete(<id real>) -> ok:1, deleted:1     <- borro

Verified recipe, one oracle per verb:

| what you want to know | do NOT look at | look at |
|---|---|---|
| did it place where requested? | `ok` | `surface_query(x,z).y` against `pos_real` of `world_spawn` |
| did it delete anything? | `ok` | `deleted` |
| did it respawn? | `ok` / `requested` | `query_player_state.pos` BEFORE and AFTER |
| was the wait satisfied? | `ok` | `satisfied` |

### `player_respawn` works headless, and ONLY from the death screen

Verified 2026-08-29 (run `02524f97`): kill player with external damage
(`world_spawn` of live infected with `flags=3108` next to them; falling does NOT work with an open
panel), wait for capture to go through its three phases —normal, **desaturated with
blood** (unconscious), **completely black** (dead)— and then `player_respawn()`
triggers the vanilla sequence ("Spawning in 8 s"). Measured: position jumped ~1,878 m.

**Pitfall**: on a LIVE player it returns exactly the same (`ok:1, requested:1`) and does
NOTHING — byte-identical position. The response does not distinguish both cases; position does.

### `key_press` delivers a DIK to mission, is not operating system input

`key_press(dik=1)` returns `delivered:1` and does **not** open the vanilla menu (`ui_tree` ->
`no_menu`). It is not a failure: its description states "a mission callback, not OS input", and
vanilla menu does not hang from `OnKeyPress`. It works for modded UIs that DO hang from there. Do not
use it as a substitute for system ESC, and do not declare the verb broken from that test.

### Driving a client by MCP: three traps (SP-450, added 2026-10-01)

Measured on DayZDiag 1.29.163709 with one client on localhost [EXACT]:

- With the CF + Dabs Framework + VPPAdminTools stack loaded, a mod's `MissionGameplay.OnKeyPress` does not
  receive the keys sent by `input_trigger`; without that stack it does.
- The client can come up in the pause menu: ESC does not close it, `ui_click` on `continuebtn` does.
- `Print(variable)` prefixes the line with `string name = '…'`, and the CLIENT log cuts lines at 255
  characters (the server log does not): print short expressions.

## Visual smokes: bubble follows player, not camera (SP-082, added 2026-08-31)

- Before spawn, read `query_player_state.pos` and place the object next to the player. Free
  camera more than 1 km away does not force streaming: it may photograph terrain even if the server confirms
  the object by raycast.
- After several `camera_set`, treat as orphan camera any series of identical frames from
  different positions. There is no `camera_release`; restart or reconnect the client before
  diagnosing the asset.
- Some vanilla vehicles resist `object_delete`. Always check `deleted`; `deleted:0`
  means it was not cleaned up. If this occurs, cleanup is manual by the user via VPP.

## File-based driver embedded in the mission for server-side logic (SP-074, added 2026-08-31)

When the test needs mod APIs that have no MCP verb, use an Enforce driver in the `init.c`
of the workspace mission (`<dayz-projects>\<mod>_dev\_server\mpmissions\<mission>\`), not
`exec_enforce`. `Resolve-Mission` of `dayz-test.ps1` prefers that mission over the template.

Validated pattern:

1. Server-only driver class, started with `CallLater` at 250 ms.
2. File-based protocol **write-once per sequence**: `$profile:<caso>\cmd_<seq>.json` ->
   `res_<seq>.json`, read and written with `JsonFileLoader`. Never rewrite a `seq`.
3. A single boot per run: sequence lives in memory and resets to 1 on restart. Between runs,
   archive the entire directory via **rename**; do not move its contents with wildcard.
4. Print `MARK` in script log to delimit each window. Every operation failure is
   serialized inside its `res_<seq>.json`; driver poll does not die from a failed case.
5. Mission scripts see classes of all loaded mods and compile server-side with
   `#ifdef SERVER` visible. Host runner only writes commands, reads results, and trims log
   between marks. Cross this pattern with `dayz-test-ingame`.
6. [EXACT] Archive the case directory on completion — always, not only between runs — and never execute a command that already has its `res_<seq>.json`. Measured failure (2026-09-27, LFPowerGrid): a driver whose sequence reset to 1 on a stale `cmd_1.json` re-ran the bank-mounting command every ~1.5 s; half an hour later the world held thousands of duplicate objects and the user aborted the next session for performance. The log lines dismissed as harness noise were the signal: a repeated `OP seq=1` means the command IS running again, and duplicated live device ids mean two entities share one id. Before filing a repeated or `ERR` line as noise, write in one sentence what it would mean if true; if that sentence describes damage, it is signal. (measured in game, DayZ 1.30.164014 Exp)

## Lease preflight, object telemetry, and zombie commands (SP-152, added 2026-08-31; corrected 2026-10-03)

- `telemetry_read(mode="object_at")` reads any classname: the bridge matches it by exact
  `GetType()` inside the radius (`DayZ_MCP_dev/addon/scripts/5_Mission/MCPBridge.c:3007-3051`), and
  the loopback checks `type` only for a non-empty string (`DayZ_MCP_dev/tools/dayz_mcp/loopback.py:1349-1358`).
  [EXACT][CLAIM-MCPV-OBJECT-AT-ANY-TYPE] On 2026-10-02 (DayZDiag 1.29.163709, run `1c289781`) it
  answered `telemetry.found=1` with `pos`, `orientation`, `health01` and `declared_slots` (the reply's
  top-level `found` stays 0) for three types:
  `KP_CharAB_V1` (`health01` 0), the vanilla `ZmbM_SoldierNormal` (0) and `KP_CharAB_V3` (0.7525).
  `inventory_attach` returned the same telemetry block for `SurvivorM_Francis`. It reads only the
  fields the bridge fills, not a mod's script members or sync variables.
  *(Corrected 2026-10-03: this bullet said "On the frozen platform, `telemetry_read(mode="object_at")`
  only accepts `type="MERCEDES_AMGLF"`: the limit is in the Python loopback, even though the Enforce
  bridge is generic. For another classname, plan diagnosis with server logs and user tests; do not
  promise object telemetry." The oldest copy of the tools on disk (2026-07-25) has the
  `type != "MERCEDES_AMGLF"` check only in the loopback's `vehicle_prepare_fixture` branch, whose
  arguments also carry `mode="object_at"`, and its `telemetry_read` took any non-empty `type`; which
  verb returned the `bad_args` behind SP-152 on 2026-08-02 is not recorded. The tools' 2026-08-16
  release has no such check.)*
- `query_*`, telemetry, raycast, and captures cross the bridge and require
  `session_acquire`. Only `dayz_test_run`/`dayz_test_stop` manage their own lease; do not extrapolate
  that management to other verbs. (rev. 2026-09-06: "require `session_acquire`" includes ADOPTING the
  run that launch left `RUNNING_IDLE`; the grant of `session_acquire_wait` does so and declares it in
  `adopted_run` — §COMPOSITION, "Bridge startup sequence".)
- A `world_spawn` timeout leaves a zombie command: it may execute after losing the
  `object_id`. Before retrying, reconcile the effect with `telemetry_read(mode="object_at")` for that
  type at the spawn position: `telemetry.found` 0 means none of that type is inside the radius when the
  read runs (the zombie command can still run later), and two or more of that type inside the radius
  fail with `ambiguous_fixture` (`MCPBridge.c:3031-3045`; not exercised on a zombie spawn).
  Do not blindly duplicate spawn. *(Corrected 2026-10-03: this said "if the `object_at` cap prevents
  it, use logs plus user inspection"; there is no such cap, first bullet.)*

## `inventory_give`: one call does not equal one unit (SP-300, added 2026-08-31)

`inventory_give(classname)` uses `CreateInInventory`; a stackable item is spawned with its default
quantity, which may be the full stack. Never turn number of calls into units or into
nominal value. After provisioning, measure the actual `quantity` of the item with entity inspection or with
the aggregated field exposed by the mod, and calibrate against that measurement all thresholds for cost,
leftover, and cleanup.

## HUD with FPV camera gate: `camera_set` cannot photograph it (SP-327, added 2026-08-31)

`camera_set` installs a scripted camera. A HUD that gates with
`DayZPlayerCamera1stPersonVehicle.Cast(player.GetCurrentCamera())` hides under that camera; it is
correct HUD behavior, not a bug of the HUD nor of the MCP. Capture it via manual user freelook
or via a custom headless mode of the mod. Internal `RestoreGameplay()` restores
player camera, but there is no public `camera_release`: if the flow does not expose that restore,
reconnect or relaunch as indicated in the previous section.

## A negative of ONE sample is not a negative (LL-398, added 2026-09-01)

While closing a gate, a material override was rewritten on a worn garment and the garment did not
change. The garment was at health level 4. It was written as a scoped finding —"at health
level 4, a new override never gets rendered"—, with the mechanism declared as not
established and with **two captures separated by minutes**. It seemed prudent. It was false.

**The two captures ruled out the RENDERING artifact, not the sample size of one**, which
was what the entire claim depended on. Repeating the observation does not increase experiment
sample size; it only confirms that the observation was read correctly.

**And the variable was confounded.** Between the print that worked and the one that did not, TWO things
changed: the health level (0 -> 4) and the moment of writing (right after a state change,
versus an arbitrary instant). The result was blamed on the one being watched.

Before writing a negative in HANDOFF from this path:

1. **Count experiment samples, not captures.** A repeated capture is n=1.
2. **Enumerate everything that changed between the working and non-working cases**, and if there are two or more, the
   negative names neither until the matrix is crossed.
3. Scoping the finding to one axis **seems** cautious and is yet another claim: the chosen axis may
   be the wrong one, and then caution points in the opposite direction of the real mechanism.

### SP-124 — Free lease does NOT imply free box

`session_status` may return `owner: null`, empty queue, and `claimable: true` while a DayZ
server and client are alive, launched outside the managed lifecycle by another project
line and occupying port 2302. The lease speaks of the lease, not of the box.

Before considering the box free, read `-mod=` of living processes:

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'DayZ%'" |
  Select-Object ProcessId, CommandLine
```

The command line tells whose run it is and whether it loads your mod.

Corollary for build: the "no DayZ process" guard can be **narrowed** to the two
conditions it actually represents —no running process loads your mod, and the target PBO opens
exclusively— instead of skipping it or waiting for the other line to finish.

Cross-ref: `dayz-test-ingame` (same rule, launch side).

## Lesson LL-494 — widen closed allowlists in readers before writers (2026-09-10)

When a config is validated against a *closed* option set and long-lived readers re-validate every request, order is: (1) add the new token to the allowlist in code, (2) ship that code to every reader, (3) restart those readers, (4) only then write the value. Writing first invalidates the whole file for old readers (`daemon_provenance_conflict` / fail-closed). Not every resident process is a reader — measure which ones read the file and when. Cheap check: run the validator in a fresh process right after write and revert on failure.

## Driving bench through the MCP: the fixture outlives a dead run, get-in can seat the wrong car, old dumps need their reader (SP-423, added 2026-09-24)

Measured 2026-09-13 on a car-tuning bench (LFCarTune: 17 episodes, DayZDiag, NWAF concrete,
one `vehicle_trace` per episode) with the dayz-mcp build before `d065b0e`.

1. **A `world_spawn` car outlives its run.** Created with `flags=0`, a car whose run dies before
   `object_delete` is persisted by the server and comes back in every new run.
   `object_delete(object_id)` cannot reach it: the id belonged to the dead run. Create bench
   fixtures with `flags=8389668`:
   [EXACT][CLAIM-MCPV-FIXTURE-NOPERSIST] `ECE_PLACE_ON_SURFACE` (1060) | `ECE_NOPERSISTENCY_WORLD` (8388608), `scripts/3_game/ce/centraleconomy.c:30,37`.
2. **`vehicle_get_in_client(pos)` answered `ok` while seating the player in that orphan**, 2 m
   away, instead of the car just created at 0 m, in two episodes. Only the trace's `car_type`
   showed it. Two cars of the same class in range make `vehicle_prepare_fixture` return
   `ambiguous_fixture`. `d065b0e` makes get-in take the nearest vehicle; keep the check anyway.
3. After that, get-in returned `not_seated` for any car, also on a clean site and after
   `player_respawn`. Only a fresh client fixed it.
4. **The drive controller skipped gears.** Automatic `ShiftUp()` fired on every tick with rpm
   above 0.8 × redline: 1st to 4th within 100 ms at ~33 km/h, and no downshift. `d065b0e` waits
   0.3 s between automatic upshifts (`AUTO_SHIFT_SETTLE_S`, dayz-mcp
   `addon/scripts/4_World/MCP_CarScript.c`). Launch figures recorded before that build are only
   valid below ~33 km/h.
5. **`vehicle_trace` dumps of that build carry 0/1 booleans and lack fields added later.** The
   reader coerces them and requires those fields since dayz-mcp `1f71983`, so a current checkout
   rejects them as `dump_invalid`. Pinning the reader at `d2f9dad` reproduced all 16 episodes
   without a difference.
6. With that build, 7 cars in a row within one run, each deleted with the client seated, worked.
   What broke get-in was the orphan, not the car count.

Rules for a driving bench:

- Create the fixture with `flags=8389668`.
- Before the first episode, `entities_query(pos, radius=30)` shows no foreign vehicle.
- After `vehicle_get_in_client`, the returned `type` is the class you created; otherwise record
  `car_mismatch` and skip the episode.
- Before analysing an episode, cross-check the trace's `car_type` against the class you asked for.
- A `not_seated` that survives `player_respawn` needs a fresh client.
- An analysis of stored dumps pins the `vehicle_trace.py` revision they were recorded with.

Would close the gap: a get-in with a foreign vehicle 2 m away on a build with `d065b0e`, and a
5-car run with `flags=8389668` killed halfway, checking that nothing persists.

## Gating a PR through an external executor: rewrite TOML with its escaping, check baseline↔PBO drift first (added 2026-10-02)

Two defects, measured in one aborted attempt to gate an external PR by temporarily repointing the
source path in a gate executor's TOML config:

1. **A programmatic swap of Windows paths inside TOML edits TOML escapes, not path bytes.** In a
   basic (double-quoted) string every backslash is escaped (`\\`). Writing single backslashes turns
   `\U` into an invalid unicode escape, and the parser stops with `TOMLDecodeError: Invalid hex
   value` before anything is evaluated: the run died in preflight. A hash that matches the planned
   bytes does not prove the TOML parses. Load the result with `tomllib` in a fresh process and
   compare the decoded path with the intended one before handing it over: a single backslash before
   `t` or `n` parses fine, into a tab or a newline. Literal (single-quoted) strings take backslashes
   as they are.
2. **Check the deployed PBO against the sealed baseline before planning the gate.** The executor
   validated the deployed PBO against a sealed baseline hash. When they differ, the gate needs the
   owner's baseline, PBO and source aligned first; no repointing or rebuild resolves it. Abort path:
   preflight rejects → restore the TOML and the PBO byte for byte → freeze the evidence → escalate.

Source: one gate run aborted in preflight; the clean abort preserved the owner's PBO.

## Comparing worn items, and getting an infected to attack (added 2026-10-02)

Measured in one run (DayZDiag 1.29.163709, the chiral in-game checks of the character and clothing
routes) [EXACT][CLAIM-MCPV-WORN-MANNEQUIN]:

- **No verb takes a worn item off the player.** A second garment cannot go into an occupied slot,
  `player_respawn` on a living player does nothing even after `player_godmode(on=false)` (see the
  `player_respawn` section above), and `player_teleport` to y=160 left the player hanging in the air
  with no fall. To compare two garments, wear the second on a survivor spawned with
  `world_spawn(type="SurvivorM_<name>")`: `inventory_attach(object_id=<its id>, dest="attachment",
  slot=...)` works on it, and it stands facing north. It cannot be given an item to hold
  (`slot="Hands"` returns `attachment_create_failed`), so read its sides from its facing.
- **An infected attacks only once it notices the player.** One spawned with AI (`flags=8391716`, the
  living-infected 3108 plus `ECE_NOPERSISTENCY_WORLD`) behind a player standing still walked away.
  Spawned 2.4 m in front of the player, it attacked after a short `player_move` (jog, 1.2 s), wind-up
  and swings, again and again. Godmode does not hide the player from AI: in diag
  `m_CanBeTargetedDebug` starts true (`4_World/Entities/ManBase/PlayerBase.c:402`, 1.29).
- **In this run, infected spawned without AI did not stay healthy.** With `flags=8389668` three of
  them idled in place, but about 12 minutes later one custom and one vanilla `ZmbM_SoldierNormal` read
  `health01 = 0` in `telemetry_read(mode="object_at")` and lay on the ground, the third read 0.75. No
  log line explains it and the cause was not found; one observation, no AI/no-AI control. Capture
  static infected early, and re-read their health before a late capture.

## Check which mod a run loaded before reading its verdict (added 2026-10-03)

`dayz_test_run` boots the registered project its `project` argument names (a name with no launcher
policy is rejected with `bad_project`) and reports `succeeded` for that run, whether or not it is the
mod you meant to test. In one run the `project` argument named another registered mod by mistake: the
server loaded that mod and
`@DayZ_MCP` with another mission, never the mod under test, and the missing compile errors of the
mod under test were read as a fix. A "defect measured in the engine" was written from it and had to
be retracted. Before you attribute a compile result or any verdict to the mod under test, read the
`-mod=` and `-mission=` of that run in its RPT: the procedure is `dayz-test-ingame`'s "An in-game
observation is worth whatever the `-mod=` line of ITS run is worth" (SP-124 above reads the same
line to know whose box it is).

## `unapproved_debug_image` on a host with a non-English culture: check the server's code first (added 2026-10-03)

On a host with a Spanish (`es`) culture, `dayz_test_run(build=true)` on a project whose build runs
AddonBuilder was seen failing with `native_debug_gate_rejected:unapproved_debug_image` on
2026-10-03: the .NET helper loads localized resource satellites
(`C:\Windows\Microsoft.NET\assembly\GAC_MSIL\*.resources\v4.0_*_es_*`; seen:
`mscorlib.resources.dll`). The MCP server's debug gate admits structurally valid `GAC_MSIL` resource
satellites since a fix of 2026-10-01, so the rejection depends on the code the running server was
started from. The reply on the wire carries no detail (kind, pid, image): read the rejected image in
the MCP server's stderr log (search for `unapproved_debug_image`), and restart the server on current
code before treating the rejection as a defect of the gate. It is never a defect of the mod under
test.

Source: written into the installed copy on 2026-10-03 by a session testing a mod through the MCP;
ported here in English, without private names, and checked against the MCP server's code (its debug
gate's satellite rule dates from 2026-10-01).

## Audit the deployed PBO's file index, not just the source tree, before attributing compile failures (added 2026-10-04)

The build can pack untracked scratch files, so assuming the PBO holds exactly the source tree
misattributes a compile verdict read from the boot's log: know what the build actually packed
before a decisive boot. The PBO index is plaintext near the start of the binary. A
`grep -a "scripts\\\\" <mod>.pbo` finds the names, but it prints whole newline-delimited chunks
of binary, not one name per line, so it is not a file list. To read the index itself,
`dayz-aviation`'s "Read the PBO index before extracting" describes a reader over the header, and
`dayz-test-ingame` lists the PBO and compares the packed `.c` count with the source's.
Keep experiments out of the packed tree: a rebuild packs the scratch files still in it, and without
`-clear` its `-temp` sync can serve stale source (`dayz-pbo-build`, "Temp-stale trap"), so after a
rebuild read the deployed PBO's index again before the decisive boot.

Limits: the index audit establishes WHAT is packed, never WHY a compile failed.

Source: written into the installed copy on 2026-10-04 by a session that spent two days on a mod's
compile failures; ported here in English, without private names, with the listing claim corrected
against a measurement on real PBOs.

## A server HANG is bounded by log tails first: read script.log's tail, and attribute to a REGION, not to the branch you hypothesize (added 2026-10-04)

A boot that never finishes (1 of N driver snapshots, RPT frozen, process alive spinning at low
CPU) is a veredicto without a location. Before attributing the hang to a specific branch:

1. **The RPT tail is usually useless for a hang** (it ends in world-streaming warnings); the
   **`script*.log` tail is the datum** — mod `MARK` lines, `[VanillaPrune]`-style stage messages
   and init-completion lines live there, not in the RPT. One zero-cost read bounds the spin to the
   region between the last printed stage and the first missing one; a hang "after init, before the
   first prune-stage message" is a different fact from "inside the prune loop".
2. **Verify the region's loop structure in source before suspecting it** (descending loop with
   every branch decrementing; per-tick resolution capped; helper functions loop-free) — this
   eliminates the cheap suspects and moves the suspicion to the remaining ones (world-scan helpers,
   engine-side recursion/re-entry), without ever NAMING them as cause.
3. **Attribution to a revision requires the path to have run under both.** A code path that never
   executed in-engine under any revision (the instrument compiled for the first time the same day)
   cannot hang "because of" the newest change: the hang may be a regression, a pre-existing bug
   surfacing for the first time, or an instrument artifact. Only a single-variable A/B (same
   scenario, one revision's line reverted) — or a within-revision scenario bisect that toggles one
   sub-path (crossing the delete threshold vs marking strikes only) — closes it. Merge stays on
   HOLD meanwhile.

Source: written into the installed copy on 2026-10-04 by the same session as the lesson above,
after a seed-and-prune strike scenario hung the server between init and the first prune snapshot;
ported here in English, without private names.

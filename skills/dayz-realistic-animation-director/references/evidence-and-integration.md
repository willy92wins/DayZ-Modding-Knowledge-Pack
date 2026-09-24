# Evidence and integration

## Evidence ladder

1. **Contract evidence:** authoritative source, route, timeline, channels, events and acceptance criteria.
2. **Blocking evidence:** golden-pose renders in measured on-axis and oblique views.
3. **Motion evidence:** full-speed preview plus contact/extreme/recovery frames.
4. **Numeric evidence:** sampled report and audit JSON, including failed checks and worst frames.
5. **Artifact evidence:** exported file exists, is non-trivial and carries the intended channel/event mask. In DayZ 1.30, verify that animation graphs conform to Enfusion Config modular `.agf` subgraphs referenced by an `AnimSrcGraph` master index (`.agr`), and `.asi` instances conform to `AnimSetInstanceSource`.
6. **Build/deploy evidence:** compiled/packed artifact actually deployed, with hash/path when stale copies are possible. In DayZ 1.30, take advantage of named mod filesystems and `-resolveFilePatchingUsingEnfusion=1` (`work\changelog-1.30-exp-modding.md:10, 25`) to mount and verify unbinarized `.agf` subgraphs directly.
7. **In-game evidence:** target states exercised, RPT reviewed and visual behavior confirmed. In DayZ 1.30, Workbench Animation Editor (updated to Enfusion 2021) supports **Live Editing of running graphs** (`work\changelog-1.30-exp-modding.md:48, 62`), allowing live parameter tuning (`VehicleSteering`, `SlopeAngleX`, blend weights) on an active running client.

Never promote evidence upward. A clean script run is not a clean animation; an offline render is not an exported artifact; an exported artifact is not the deployed PBO; a deployed PBO is not an in-game PASS.

## Visual review set

At minimum capture:

- entry pose;
- first contact;
- maximum load/effort;
- mechanical extreme or locomotion support extreme;
- release;
- clearance/return;
- final pose;
- full-speed video.

Use an on-axis view for orientation claims. Add top/side/end-on close-ups for fingers, grips, feet or mechanical clearances.
In DayZ 1.30, when authoring vehicle interactions (such as motorcycles `MOTO1`/`MOTO2`), capture visual reviews during get-in, get-out, and seat-switching (`HumanCommandVehicle.IsTransitioning()` in `exp\scripts\scripts\3_Game\human.c:735-738`), verifying 2-bone IK hand lock on handlebars and foot placement on footpegs across the entire transition.

## Integration handoff

Send `dayz-animation-pipeline`:

- source scene/version and immutable donor;
- chosen route and target state name supplied by the pipeline;
- exported artifact path (including modular `.agf` files and `AnimSetInstanceSource` `.asi` mappings);
- FPS/frame range and events/notetracks;
- included/excluded channels;
- audit and render paths;
- current evidence state.

Then follow its current compile, wiring, build and test procedures. In DayZ 1.30, test workflows can leverage Workbench Enfusion 2021 Live Editing, the native Ragdoll Editor for `.ragdoll` files, and `-resolveFilePatchingUsingEnfusion=1`. Do not reproduce them here.

## Output states

### `FAIL`

At least one required gate failed or an input was invalid. Report check IDs, measured values, worst frames and whether the failure is numeric, visual, runtime or missing-data.

### `OFFLINE_PASS`

Blocking, motion, numeric audit, visual review and the relevant offline artifact pass. Explicitly state that DayZ runtime has not been confirmed.

### `MANUAL_REQUIRED`

The next gate requires unavailable GUI interaction, credentials, hardware, human judgment or an unsupported runtime harness. Give the exact action and evidence needed; do not present the previous state as final success.

### `IN_GAME_PASS`

The deployed build played correctly in required states/cameras/stances, RPT showed no relevant errors and the visual/mechanical contract passed. Record the build identity and evidence.

## Regression closeout

If the user or game refutes a prior PASS:

- mark the prior claim stale immediately;
- preserve the failing artifact;
- add a negative fixture;
- prove a corrected positive fixture can pass;
- update the project validation matrix/bug ledger/handoff;
- promote only the cross-project invariant, not project-specific coordinates or timing.

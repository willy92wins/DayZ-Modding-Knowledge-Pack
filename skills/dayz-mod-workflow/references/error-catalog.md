# Recurring error catalog (E01–E20)
# (until 1.29: index stopped at E20.) (since 1.30 Exp: also E21 CE rootclasses, E22 CanBeStarted / CCTLiquid — see table rows below and `dayz-1-30-mod-workflow.md`.) (measured on 1.30 Exp: E23, a `HumanCommandScript` subclass in `4_World` started twice crashes the exit — its row and the section below the table.)

> Extracted from dayz-mod-workflow/SKILL.md 2026-07-07 (F3).
>
> Full table of verified errors committed more than once. The core SKILL.md keeps a one-line index per error (`Ecode — title`) pointing here; this file is the detail (Correct + Source columns). The E11 / E20 corrected claims are preserved verbatim in both the index and this table.

Check ACTIVELY during implementation.


Verified errors committed more than once. Check ACTIVELY during implementation.

| ID  | Error | Correct | Source |
|-----|-------|---------|--------|
| E01 | `requiredAddons[]={"DabsFramework"}` | `{"DF_Scripts"}` or `{"DF_GUI"}` | UILab, config.cpp |
| E02 | `imageSets` in CfgSlots or root | Inside `CfgMods > Mod > defs > imageSets` | ArmorAddition |
| E03 | Same variable name in sibling scopes | Hoist variable before conditional | UILab crash |
| E04 | rvmat Stage4 with `AS` suffix | `color(0,1,1,1)` no suffix, R=0 | ArmorAddition |
| E05 | rvmat Stage2 DT alpha=1.0 | Alpha=0.5: `color(0.5,0.5,0.5,0.5,DT)` | ArmorAddition |
| E06 | rvmat fresnel values guessed | Copy from vanilla ref of same type | ArmorAddition |
| E07 | rvmat damage using procedural color | Use `generic_damage_mc.paa` / `generic_destruct_mc.paa` | ArmorAddition |
| E08 | Assuming function exists because "makes sense" | Verify in skill, vanilla, or internet | Multiple |
| E09 | Continuing past context saturation | Stop, checkpoint, handoff | Multiple |
| E10 | `forcedDiffuse` alpha 0 | Alpha 1: `0,0,0,1` | ArmorAddition |
| E11 | Using string in ActionCondition (client) | Strings not syncable. Use int ID via SyncVar (readable on both sides); a client-only cache passes the menu but fails the server-side Can() gate | SimpleGroup |
| E12 | IsTakeable=false to prevent pickup | RemoveAction(ActionTakeItem/ToHands). IsTakeable=false hides from vicinity but custom actions still work | SimpleGroup |
| E13 | Notify AFTER clearing collection | Loop on empty=0 notifications. Notify BEFORE clear | SimpleGroup |
| E14 | Debug downstream without verifying upstream | Follow hierarchy in 5.5. Check IsTakeable/AddAction BEFORE ActionCondition | SimpleGroup |
| E15 | Cache not cleaned on state transition | Every state change -> update cache (client + server) | SimpleGroup |
| E16 | Fix without mapping client/server boundary | Complete 2.5 data map BEFORE writing fix | SimpleGroup |
| E17 | SyncVar bitstream client/server mismatch | Same vars, same order, both sides | CF Issue #143 |
| E18 | `IsServer()`/`IsClient()` for server/client guard | Use `IsDedicatedServer()` / `!IsDedicatedServer()` | Expansion Pitfalls |
| E19 | Version field manually serialized in persistence | Engine manages version. Use `OnStoreLoad(ctx, version)` param | vanilla EntityAI.c |
| E20 | Modded vehicle won't drive + no RPT error + wheels mount but don't spin (`WheelCountPresent()=0` while `WheelCount()=N`); chassis bounces/sinks; steering animates without sim spin | `CfgSlots.<wheel-slot>.selection` must name a selection that exists in the **FireGeometry LOD of the body** and contains a wheel proxy (`proxy:\…`). If only in visual LODs → fix Y: alias the FireGeo proxy face into the slot's selection name (additive py3d, preserves visual hide). See `enforce-script-reference` §"Wheel attachment to simulation: `CfgSlots.selection` ↔ FireGeometry proxy selection" for mechanism + py3d fix. | LFQuad blocker `wheelPresent=0` |
| E21 | Custom-map `cfgeconomycore.xml` copied from 1.29 (no Motorbike / destructible-house rootclasses) | (since 1.30 Exp) Add `<rootclass name="MotorbikeScript" act="car" reportMemoryLOD="no" />` and `<rootclass name="HouseDestructible" reportMemoryLOD="no" />` next to `CarScript`/`BoatScript`. Verified `exp\worlds_chernarusplus_ce\DZ\worlds\chernarusplus\ce\cfgeconomycore.xml:17-18` (same pair on Enoch and Sakhal). | DayZ 1.30 Exp CE |
| E22 | Visible action widget but F does nothing / custom pond drink never lists | (since 1.30 Exp) After CCT/CCI vanilla can **show** actions with `CanBeStarted()==false` (`ActionManagerClient.c:336`); info actions override it to false (`ActionPartInfo.c:18-21`). Water/wash/fill vanilla uses `CCTLiquid` not `CCTWaterSurfaceEx` (`ActionWashHandsWater.c:28`). See `references/dayz-1-30-mod-workflow.md`. | DayZ 1.30 Exp actions |
| E23 | A `HumanCommandScript` subclass declared in `4_World` and started two or more times: every orderly exit crashes client and server | (measured on 1.30 Exp, open) Declare the class the engine starts in `3_Game`, as a thin shell that forwards its hooks to a `Managed` logic object in `4_World`: LFSkateboard's workaround, still being verified when reported. The measurements, and what is interpretation, in the E23 section below. | LFSkateboard, DayZDiag 1.30.164014 Exp |

## E23 — a `HumanCommandScript` subclass in `4_World`, started twice, crashes the orderly exit (open)

[EXACT][CLAIM-WF-HCS-4WORLD-EXIT-CRASH-130] Measured in game on 2026-10-07, DayZDiag 1.30.164014 Exp, server and client, by LFSkateboard (evidence crash-diag-1ride, crash-r5-2rides, R1d-run5-owner, exitexp2-nullcmd and exitexp-split-2rides):

- After two or more rides of the project's ride command, a `HumanCommandScript` subclass declared in `4_World`, the orderly exit crashed client and server with an ACCESS_VIOLATION during the cleanup of the `World` script module, right after `Leaked 'LFSK_RideCommand' script instance (-Nx)!` and before `Leaked 'HumanCommandScript' (+Nx)`, N being the number of rides. After one ride the exit was clean. A constructor and destructor probe counted exactly one of each per ride, and starting the command with `StartCommand_Script` on a new instance or with `StartCommand_ScriptInst` on its class made no difference.
- An empty class deriving from `HumanCommandScript`, declared in `scripts/4_World` and started twice with `StartCommand_ScriptInst`, ending itself after 1 s each time, crashed the orderly exit the same way: an ACCESS_VIOLATION in the `World` module's teardown right after `Leaked 'X' script instance (-2x)!`, where the bytes before the faulting address are a reference-count release.
- The same empty class declared in `scripts/3_Game` exited clean (`Termination successfully completed`), and still printed −2x for the class and +2x for `HumanCommandScript`, in the `Game` module.
- Started once, it exited clean from either module.

(claim: CLAIM-WF-HCS-EXIT-CRASH-WORKAROUND) The cause is not known. The project reads the leak counts as creation being counted under `HumanCommandScript` and destruction under the subclass: an interpretation, not a measurement. Its workaround (review 2026-10-08-crash-salida) keeps the class the engine starts in `3_Game`, a thin shell that forwards the command's hooks to a `Managed` logic object in `4_World`. When it was reported, on 2026-10-08, its verification in game on the real ride command was still running; no result is recorded here. Measured only on DayZDiag 1.30.164014 Exp.

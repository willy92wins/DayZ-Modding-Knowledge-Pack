# Recurring error catalog (E01–E20)

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

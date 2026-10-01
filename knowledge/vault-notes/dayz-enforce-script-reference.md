# DayZ Enforce Script Reference

Source skill: `C:\Users\<you>\.agents\skills\enforce-script-reference\SKILL.md:33-296`
Extraction date: 2026-05-14
Evidence level: skill-sourced summary. Before using an exact API/signature in code, verify in `P:\scripts\` or approved source and record it in project `verified-apis.md`.

## Hard Rules

Syntax restrictions to check before delivery:

- No ternary operators, increment/decrement operators, `foreach`, `+=` / `-=`, or multiline expressions.
- No string literal or inline concatenation directly as function parameter; build local strings first.
- Hoist variables before loops and conditionals; do not reuse the same local name in sibling branches.
- Use explicit typing and `m_` prefix for member fields.
- Do not allocate new arrays/maps/Param objects inside periodic ticks; reuse member fields and clear them.

Memory rules:

- `ref` matters primarily for class member fields on non-Managed types.
- Locals are strong references by default; `ref` on locals is usually redundant.
- Do not put `ref` on parameters or return types.
- Do not combine `ref` and `autoptr` on the same field.
- Do not use `delete` on live objects; clear references and let GC handle lifetime.
- Break circular references in destructors.

Networking/timer rules:

- SyncVar writes belong server-side and need dirty marking.
- Every RPC/read from context must check the read result and fail closed on failure.
- Side checks can lie during client load; prefer the dedicated-server split pattern already verified for the project.
- `CallLater` repeat timers and per-device periodic callbacks are risky over long uptime; centralize ticks.

Override/class rules:

- Keep `ScriptedWidgetEventHandler` override methods contiguous.
- `modded class` cannot add member variables.
- Multiple `modded class` declarations for the same class can coexist across files.

## Review Checklist

Before handoff, scan for:

- Forbidden syntax/patterns above.
- Cast results used without null checks.
- Destructors calling engine globals without null checks.
- SyncVar registration outside the constructor.
- RPC/context reads without return checks.
- Per-instance repeated timers.
- Circular references not cleared.
- Wrong entity identity comparison: config class vs script class.

## API Areas To Verify Per Project

These are common risk areas, not standalone verified APIs:

- Entity identity: config type vs script class name vs inheritance check.
- Entity lifecycle: constructor, init, action registration, persistence load/save, sync callbacks, delete/destructor.
- Object creation and inventory creation return values.
- Config lookup path format.
- Math/string helpers that are missing or version-dependent.
- Server-to-client RPC target routing.

## Common Failure Patterns

- UI/input stays locked because close/destructor did not release focus/input state.
- SyncVar never reaches client because registration happened too late.
- RPC executes on wrong side because server/client split was inferred from the wrong helper.
- Entity creation silently fails because object or cast result was not checked.
- Config lookup fails due to wrong path formatting.
- Timer-based degradation appears only after long server uptime.

## Related

- Project-level exact facts: `AI/10_Projects/<PROJECT>/verified-apis.md`
- [`AI/20_Knowledge/dayz-ui-development.md`](dayz-ui-development.md)
- [`AI/20_Knowledge/dayz-capacidades-verificadas.md`](dayz-capacidades-verificadas.md)
- [[dayz-mod-implementation-checklists]] — per-file checklists + catalog of recurring errors (E01–E31) that apply these rules.
- [[dayz-modded-class-server-stub-pattern]] — override bug-pattern without base stub (Rule 24, exact parameter names).

## IsKindOf config-vs-script semantics (added 2026-05-20)

`GetGame().IsKindOf(string entityType, string parentType)` queries the **CfgVehicles** chain, not the script chain. A class declared in script as `class X : Y` can have in CfgVehicles another parent (`class X : Z`) where `Y` and `Z` are siblings in config. The runtime uses the config version.

**Recurring failure pattern**: in compat-layer mods registering verified-base classnames (`LFV_StateProbe.RegisterVerifiedBase`, Expansion, similar frameworks), if registered base is the script parent but NOT the config parent, all descendants silently fail matching. The compat layer enters defensive no-op state and feature is not applied to that subclass. Typically silent at `m_LogLevel="ERROR"` (diagnostic WARNs are filtered).

**Canonical diagnostics**: when a class "does not catch" with a hook that should cover it by inheritance, unbinarize mod config.bin (`CfgConvert.exe -txt -dst out.cpp config.bin`) and `grep "class X:"` to rebuild config chain. Compare against script chain. Any intermediate `*_Placeable_Base`, `*_Coverable_Base`, `*_Static_Base` that is child in script but sibling in config is suspicious. 30 seconds of verification, eliminates 80% of search space.

**Documented case**: `A6_MilitaryStorageCrate` in LF_VStorage 2026-05-20. `A6_Openable_Placeable_Base` declares `: A6_Openable_Base` in script but `: A6_Storage_Base` in CfgVehicles. Fix: register all direct config-bases of concrete classes with cargo, not just the "logical" script base. See [`10_Projects/LF_VStorage/bug-ledger.md`](../10_Projects/LF_VStorage/bug-ledger.md) 2026-05-20 and [`10_Projects/LF_VStorage/verified-apis.md`](../10_Projects/LF_VStorage/verified-apis.md) (IsKindOf entry).

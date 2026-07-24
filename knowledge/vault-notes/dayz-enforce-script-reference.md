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
- [[dayz-mod-implementation-checklists]] — checklists por archivo + catálogo de errores recurrentes (E01–E31) que aplican estas reglas.
- [[dayz-modded-class-server-stub-pattern]] — bug-pattern de override sin stub base (Rule 24, nombres de parámetro exactos).

## IsKindOf semántica config-vs-script (added 2026-05-20)

`GetGame().IsKindOf(string entityType, string parentType)` consulta la cadena de **CfgVehicles**, no la cadena de scripts. Una clase declarada en script como `class X : Y` puede tener en CfgVehicles otro padre (`class X : Z`) donde `Y` y `Z` son hermanos en config. El runtime usa la versión de config.

**Patrón de fallo recurrente**: en mods de compat-layer que registran verified-base classnames (`LFV_StateProbe.RegisterVerifiedBase`, Expansion, frameworks similares), si la base registrada es el padre script pero NO el padre config, todos los descendientes silenciosamente fallan el match. La capa de compat entra en estado defensivo no-op y la feature no se aplica a esa subclase. Suele ser silencioso a `m_LogLevel="ERROR"` (los WARNs diagnósticos se filtran).

**Diagnóstico canónico**: cuando una clase "no engancha" con un hook que debería cubrirla por herencia, debinarizar el config.bin del mod (`CfgConvert.exe -txt -dst out.cpp config.bin`) y `grep "class X:"` para reconstruir la cadena de config. Comparar contra la cadena de script. Cualquier intermediate `*_Placeable_Base`, `*_Coverable_Base`, `*_Static_Base` que sea hijo en script pero hermano en config es sospechoso. 30 segundos de verificación, descarta 80% del espacio de búsqueda.

**Caso documentado**: `A6_MilitaryStorageCrate` en LF_VStorage 2026-05-20. `A6_Openable_Placeable_Base` declara `: A6_Openable_Base` en script pero `: A6_Storage_Base` en CfgVehicles. Fix: registrar todos los config-base directos de las clases concretas con cargo, no solo el script base "lógico". Ver [`10_Projects/LF_VStorage/bug-ledger.md`](../10_Projects/LF_VStorage/bug-ledger.md) 2026-05-20 y [`10_Projects/LF_VStorage/verified-apis.md`](../10_Projects/LF_VStorage/verified-apis.md) (entry IsKindOf).

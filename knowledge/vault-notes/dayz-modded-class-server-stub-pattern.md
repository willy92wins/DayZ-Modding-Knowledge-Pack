# DayZ — Patrón "stub server-only" en jerarquías modded class

> Cross-cutting bug-pattern. Applies to any DayZ mod that uses the
> separation `#ifdef SERVER modded class X` to put heavy logic
> server-only. Documented following compile error 2026-05-11 in
> LF_VStorage (`LFV_Module.ShouldBlockContainerInteractionWithReason`
> undefined on client with `mmg_storage` active).

## The architectural pattern (legitimate)

```
// Scripts/4_World/<MyMod>_Module.c  (client + server)
class <MyMod>_Module : CF_ModuleWorld
{
    // Empty stubs that the client can call without error.
    bool ShouldBlock(ItemBase x) { return false; }
    void Notify(PlayerBase p) {}
    void DoServerThing(EntityAI e) {}
}

// Scripts/4_World/<MyMod>_Module_Server.c  (solo server)
#ifdef SERVER
modded class <MyMod>_Module
{
    // Real override with heavy logic.
    override bool ShouldBlock(ItemBase x) { /* validación, IO, RPC, … */ }
    override void Notify(PlayerBase p) { /* mensajes admin … */ }
    override void DoServerThing(EntityAI e) { /* persistencia, … */ }

    // NEW methods added only here (NOT in base).
    bool NewServerMethod(...) { ... }   // <-- riesgo de bug
}
#endif
```

This is OK as long as discipline is maintained.

## The bug — adding server method without stub in base

When a dev adds a new method in `<MyMod>_Module_Server.c` and forgets
to add the corresponding stub in `<MyMod>_Module.c`:

1. The method exists ONLY under `#ifdef SERVER`.
2. On client the base class does not have the method.
3. Any code compiled on client calling the method fails with
   `Undefined function '<MyMod>_Module.NewServerMethod'`.

### When it manifests

The bug is **silent until some action / hook / UI loaded on
client calls the method**. Typical path:

```
// Scripts/4_World/Actions/<MyMod>_ModdedAction_X.c
#ifdef <some_external_mod>
modded class ActionX
{
    override void OnStartServer(ActionData ad)   // <-- compila en client+server
    {
        <MyMod>_Module m = <MyMod>_Module.GetModule();
        if (m.NewServerMethod(...)) { ... }       // <-- compile fail if client loads the #ifdef
    }
}
#endif
```

`OnStartServer` executes server-side, but the file is **compiled on
both**. The `#ifdef <some_external_mod>` activates when the external mod
is loaded (on client if the user has it installed).

Therefore the bug appears only on clients that have that external mod —
the others do not see it, which allows the bug to remain latent
for months.

## Detection

A cross `grep` pass closes the pattern:

```bash
# 1. Lista métodos server-only:
grep -nP '^\s*(bool|void|int|float|string)\s+\w+\s*\(' <MyMod>_Module_Server.c

# 2. For each one, verify whether a stub exists in base:
grep -n 'NewServerMethod\b' <MyMod>_Module.c
```

If (2) comes up empty for a method in (1) → stub is missing.

Another way: grep all callsites `<MyMod>_Module\.\w+\(` and cross-check
against what is defined in base.

## Fix

Add no-op stub in the base class. EXACT signature (including parameter
names — Enforce override rule):

```c
// In <MyMod>_Module.c, alongside other stubs:
bool NewServerMethod(/* mismos params + names que server */) { return false; }
void NewServerVoidMethod(/* mismos params */) {}
```

## Durable prevention

**Team convention**: any PR touching `<MyMod>_Module_Server.c`
adding a public method must add the corresponding stub in
`<MyMod>_Module.c` in the same commit.

Lightweight linter (offline script before each commit):

```python
# Pseudo-code: extract public signatures from Server.c, verify
# presence of each name in base .c. Fails CI if missing.
import re
server_methods = re.findall(r'^\s*(?:bool|void|int|float|string)\s+(\w+)\s*\(', server_src, re.M)
base_methods = re.findall(r'^\s*(?:bool|void|int|float|string)\s+(\w+)\s*\(', base_src, re.M)
missing = set(server_methods) - set(base_methods)
if missing:
    fail(f"Missing client stubs: {missing}")
```

(Not automated as of today; backlog if pattern recurs.)

## Casos verificados

| Project | Affected methods | Solution | Date |
|---|---|---|---|
| LF_VStorage | `ShouldBlockContainerInteractionWithReason`, `SendBlockReasonMessageToPlayer` | Stubs added in `LFV_Module.c:167-169` | 2026-05-11 |

## Relacionado

- `enforce-script-reference` Rule 24: override parameter names MUST match
  exactly. Applies when adding base stubs — use same names as server.
- DayZ engine compile lifecycle: client + server load the same
  `Scripts/4_World/` tree, divergence only via `#ifdef SERVER`.
- Skill `enforce-script-reference` covers the layer architecture (3_Game /
  4_World / 5_Mission) but NOT this specific pattern — candidate to
  add if bug recurs in another mod.
- [[dayz-enforce-script-reference]] — Rule 24 + `modded class` rules (do not add member vars, coexistence of declarations).
- [[dayz-mod-implementation-checklists]] — client/server data map (§1) that prevents this type of divergence.
- [[dayz-capacidades-verificadas]] — this note is linked from there as bug-pattern related to `#ifdef SERVER`.

## Aplica a

- LF_VStorage (verified).
- LF_PowerGrid (probable — uses same module architecture + #ifdef SERVER).
- Any DayZ mod separating heavy logic into `_Server.c` with
  `#ifdef SERVER modded class`.

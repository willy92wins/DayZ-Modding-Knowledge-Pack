# DayZ Enforce — the `4_World` arena and how it is truly measured

> Domain hub: what the Enforce compiler actually charges per module, and why
> almost everything that looks like a size proxy is not. It exists because measuring wrong
> here costs entire campaigns: reducing one million source bytes can yield
> **0 kB** of arena.
>
> Measured on DayZ `1.29.163451` in a production mod with ~1.2 MB of World
> module. The concrete numbers are from that mod; **the invariants and methods are
> from the engine**. Always separate engine fact, inference, and product constraint:
> do not turn an observed slope into a universal constant.

## The only capacity verdict

```
candidate.World - empty.World <= limit
```

A small causal saving is **not** equivalent to a capacity PASS. And a PASS names the
stack to which it belongs: an E/candidate pair where only the product PBO changes
measures the absolute contribution of the candidate **in that snapshot**, not that another stack
will fit. Use separate tags (`PROSPECTIVE_SNAPSHOT_CAPACITY_PASS|FAIL`,
`AFFECTED_STACK_NOT_RUN`) instead of an ambiguous PASS.

## Hierarchy of evidence

De mayor a menor autoridad:

1. **Module delta on adjacent engine pairs** — same build, stack, order,
   mission, config, and artifacts; full Game/World/Mission.
2. **Engine class counter, calibrated by family.**
3. **Semantic bytecode removed from the server preprocessed view** — valid for
   forecast only when the behavior truly disappears from the module.
4. **Declarations, methods, lines, source bytes, and PBO size** — they are
   inventories. By themselves they **do not predict arena**.

## What is NOT a proxy (measured)

| Transformation | Structural change | World kB |
|---|---|---:|
| `−16` files, same classes | none | `0/−1` |
| `−1,071,376` source bytes, same classes | none | `−2/0` |
| `−3` kit shell classes | 3 classes | `1/0` |
| `−1` large class, `−19,670` non-whitespace | 1 class | `44/45` |
| `−12` generic classes | 12 units | `79/77` |
| `−18` engine units | 18 units | `101/101` |
| `−3` source generic expressions, same classes | none | `−3` |
| same classes, real server bytecode removed | none | `28/29` |

**The compiler charges structure, bytecode, and materializations, not the physical text
that represents them.** One million source bytes was worth 0 kB; twelve generic
classes were worth ~78 kB.

## The invariants

| # | Invariant | Why it bites |
|---|---|---|
| 1 | **Classes are calibrated by family** | observed band ~`5.6..6.6 kB` per engine unit in generic specializations, but a small ordinary class can be worth **`0 kB`**. A global regression of "kB/class" selects the wrong work |
| 2 | **Generic expression removed ≠ materialization eliminated** | removing three `JsonFileLoader<T>` from the model did not lower the engine counter. The source scanner is a precondition, not a verdict |
| 3 | **Mass is counted net** | `removed body − exact replacement source − shared kernels added`. A refactor showed `277,983` gross characters and only `2,700` net |
| 4 | **The server preprocessor counts** | an entire class under `#ifndef SERVER` stopped being counted (`6141→6140`). Analyze with the exact defines of the run; a raw grep manufactures false inventories |
| 5 | **The `classes` counter includes generated types** | it is not a grep for `class`: `203 = 187 declarations + 14 novel generics + 2 residual`. Subtraction dimensions, does not name |
| 6 | **Anti-redistribution** | report Game, World, Mission **and total**. A reduction in World that grows equally or more in another module, another PBO, or at runtime does not resolve the pressure: it displaces it |
| 7 | **A PBO is not an arena** | `CfgMods.*ScriptModule.files[]` decides where a script compiles. Several PBOs declaring `worldScriptModule` still feed World: a packaging split with the same module saves **`0 kB`** |
| 8 | **Only five ScriptModule keys exist** | Engine, GameLib, Game, World, Mission. A scan of `1,238` `config.cpp` and `1,098` declarations of `class *ScriptModule` found no static custom key |

Engine references for 7: [Modding
Structure](https://community.bistudio.com/wiki/DayZ:Modding_Structure) and [Modding
Basics](https://community.bistudio.com/wiki/DayZ:Modding_Basics).

## The lever that does work: early World → Mission facade

**Measured, two reproducible pairs, synthetic probe of 200 methods.** A base class
declared in `4_World` whose **bodies** live in a subclass declared in
`5_Mission` keeps that mass out of the World arena.

**It is not a trick: it is the canonical vanilla pattern**, and its four pieces are
distributed between the two modules exactly as the pattern requires (verified in
`P:\scripts` on `1.29`):

- `4_world\classes\missionbaseworld.c:3` — the base, **in World**, declares
  `GetRainProcurementHandler()` returning `null`;
- `5_Mission\mission\missionserver.c:822` — the `override` with the real body,
  **in Mission**;
- `4_World\classes\rainprocurementcomponent.c:14` — the call-site calls through the
  base type: `MissionBaseWorld.Cast(g_Game.GetMission()).GetRainProcurementHandler()`;
- `5_Mission\mission\missionbase.c:1` — `class MissionBase extends MissionBaseWorld`
  inherits across modules.

| | control (bodies in World) | candidate (bodies in Mission) | moved |
|---|---|---|---|
| World − baseline | +116 / +118 kB | +53 / +54 kB | **+63 / +64 kB (54 %)** |

**Two nuances that decide whether it is useful to you:**

- **The shell is not free.** Signatures remain declared in World: 53 of the 116
  kB remained. The percentage moved depends on the body/signature ratio, so
  it **does not project linearly between classes**. The probe had 33 % signatures
  (200 tiny methods); a class of 49 fat methods has ~4 % and moves much more.
- **It is transport, not reduction.** Mission goes up +103 kB and duplicate signature
  overhead adds +39 kB. In two pairs with real classes: World `−139/−140 kB`,
  Mission `+142/+142 kB`, Game `0`, **total `+3/+2 kB`**.

When World is at 97 % and Mission at 39 %, the server fails **due to module
capacity** even if total memory is plenty. Rebalancing is a legitimate solution, but
call it **arena rebalance**: it does not fulfill an anti-redistribution contract.

**Mission is preferable to Game** for a World core: it compiles later and can
name World types; Game compiles earlier and cannot.

## The dynamic bridge, if you cannot use the facade

APIs verified in `P:\scripts\1_core\proto\enscript.c`, with doc from the header
itself:

- `Call` (`:139`) — *«The call creates new thread, so it's legal to use
  sleep/wait»*;
- `CallFunction` (`:146`) and `CallFunctionParams` (`:147`) — *«The call do not
  create new thread!!!!»*;
- `LoadScript` (`:160`) — creates a child, but does **not** demonstrate separate arena nor
  loading from VFS/PBO.

Mandatory pattern: one call per **coarse event** (never per getter), fixed function
name not derived from the client, checked result, **fail-closed before
any side effect**, rate-limited warning, and **zero dispatch in ticks, loops,
scans, timers, or periodic callbacks**.

Difference with the facade: the bridge only allows islands **without callers from
World**; the facade is normal virtual dispatch and does not touch call-sites.

**A child module can have its own arena, but that is not savings.** Mission
`init.c` appears as a separate module with `1 file`, `1 class`. If a change reduces
World and the cost reappears in a child you do not count, the three-module total
ceases to be complete: it is unaccounted relocation.

## Method: two rules that generalize outside DayZ

**A "cost-removal" experiment needs a positive control.** A probe of two
variants —without the thing and with the thing— produces an **ambiguous zero**: if the candidate
does not move the metric, you cannot distinguish "the mechanism works" from "the probe was measuring
nothing" (class discarded as unreferenced, file outside the module, build that did not
pick up the change). **Always three variants: baseline / positive control /
candidate.** The control injects mass through the conventional route and **must** move the
metric; if it does not, the experiment is `VOID` and the candidate is not read. And
**write the numerical prediction of the three rows before measuring**: an experiment
whose prediction is drafted afterward cannot fail.

**A minimal pilot must be able to falsify.** Typical gate: full modules, expected
counter, World savings `>=4 kB`, Game/Mission without growth, total savings `>=`
World savings, functional oracle, exact stop, and cleanup. And always separate the pilot's
two verdicts: **mechanism** (World drops, the rest adds up, behavior
passes) and **scale** (the measured density applied to the mass truly
transferable reaches the target with margin). A mechanism yielding `>=4 kB` does
not authorize scaling.

## STOP signals

- The upper depends on deleting behavior that must later reappear in another class.
- The proposal adds loops, scans, timers, callbacks, or dispatch to substitute
  static cost without an explicit Intent.
- The family mixes shell classes, templates, and large classes.
- The counter drops but World does not exceed quantization.
- Total savings is less than World savings.
- A hash drifts, or the measured candidate is not the normal build.

## Freezing the stack means freezing PBOs

A `-mod` line proves order and roots, **not** which PBOs existed inside each
root. For a fail-closed gate the minimum identity of each input is: mod path and
order; exact set of PBOs under that root; size and SHA-256 of each;
digest of its member listing; explicit zero-file manifest for empty
roots; and **the same manifest before and after each run**. If any is missing,
write `INVENTORY_INCOMPLETE` — never turn it into "zero consumers".

**With `-filePatching`, "empty mod" means empty recursive tree.** Checking
only `Addons\*.pbo` does not freeze a mod: a stray script, an unexpected
subdirectory, or a reparse point changes the effective input even if the PBO count is
zero.

**A positive control distinguishes "zero hits" from "broken search".** When auditing whether
anyone external references your classnames, run the detector against an artifact
that **does** contain them. If the control finds nothing, zero from the rest
means nothing.

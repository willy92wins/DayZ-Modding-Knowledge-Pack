# DayZ Mod — Implementation Checklists (Claude + Codex)

> Cross-cutting technical knowledge of DayZ modding. Readable by Claude (`dayz-mod-workflow` skill) and by Codex (must read this file before implementing DayZ features).
>
> Process (when and how) → [`00_System/workflow.md`](../00_System/workflow.md) + `dayz-mod-workflow` skill.
> This file is **what** to verify, not **when** to verify.
>
> Maintenance: add entries with `path:line` or concrete source (R2 cite-then-verify). If an entry is observed failing in production, log it in project `bug-ledger.md` + update catalog at the end.

---

## 1. Client/server data map (mandatory before any feature with state/action/UI)

Fill in table per feature before writing code:

```
| Dato                | CLIENT? | SERVER? | Bridge mechanism     |
|---------------------|---------|---------|----------------------|
| (rellenar)          |         |         | SyncVar / RPC / Cache|
```

Reglas duras (verificadas contra `vanilla EntityAI.c`):

- **SyncVar types**: Bool, BoolSignal, Int, Float, Object. **No** strings. `RegisterNetSyncVariableString` does not exist.
- **Bitstream alignment**: client and server register same SyncVars in same order. Mismatch corrupts ALL synchronized data without visible error.
- **`ActionCondition()`** runs **client-only** to display action in menu. Any data accessed there must be client-available.
- **Methods with `Server` suffix** (`OnStartServer`, `OnFinishServer`, `OnUpdateServer`) run on server. Server-only data here.
- Server does **not** re-execute `Can()` or `ActionCondition()`. It trusts client selection and validates via `SetupAction()`.
- If you need a string on client → ScriptRPC populating local cache, or encode as int hash via SyncVar.
- **If in doubt whether data is client-available → treat it as unavailable.**

---

## 2. Checklists by file type

### 2.1 config.cpp

- [ ] `CfgPatches` class name = addon folder name.
- [ ] `requiredAddons` uses CfgPatches class names:
  - CommunityFramework: `"JM_CF_Scripts"` (not `"CommunityFramework"`).
  - DabsFramework: `"DF_Scripts"` or `"DF_GUI"` (not `"DabsFramework"`).
  - Vanilla: `"DZ_Data"`, `"DZ_Scripts"`.
- [ ] `hiddenSelections[]` count = `hiddenSelectionsTextures[]` count.
- [ ] `scope = 2` spawnable, `1` reference, `0` abstract.
- [ ] Inheritance: parent exists or is in `requiredAddons`.
- [ ] **Vehicle nested class override (`class SimulationModule: SimulationModule`, `class Axles: Axles`, `class Front: Front`, `class Rear: Rear`, `class DamageZones: DamageZones`, etc.)**: base referenced with `: X` MUST be declared as forward-ref `class X;` in root of THIS `CfgVehicles`. Each `config.cpp` is parsed with its own scope — a child mod does NOT inherit forward-refs from parent PBO config. Without them → CfgConvert gives `Undefined base class 'X'` (compile-blocking, mod does not load). Nested classes WITHOUT `: parent` (Engine, Steering, Gearbox, Differential, Suspension…) merge implicitly and do NOT need forward-ref. See E24.
- [ ] **`ProcessDirectDamage` first argument = `DamageType.FIRE_ARM`** (enum, `damagesystem.c`), NOT `DT_FIRE_ARM` (non-existent alias in current vanilla, only in a comment). See E25.
- [ ] `inventorySlot` = string for one, `inventorySlot[]` = array for several. (Bug T148506: mixing forms silently breaks attachment.)
- [ ] `ghostIcon`: `"set:setname image:imagename"`. Verify imageset exists.
- [ ] `imageSets` inside `CfgMods > Mod > defs > imageSets` — **not** in root or CfgSlots.

### 2.2 Enforce Script — general

Full rules live in `enforce-script-reference` skill. Key verified restrictions:

- [ ] **No ternary operators** (`? :` does not compile).
- [ ] `ref` **only** on member fields, never on locals/params/returns/typedefs.
- [ ] **Never** use `delete` keyword (segfault if references remain).
- [ ] `foreach` works, but **never** directly on a getter return (NPE on 2nd iteration). Assign to local first.
- [ ] Prefix `m_` on all member fields.
- [ ] No `new` inside periodic ticks → use `m_` field + `.Clear()`.
- [ ] Complex expressions in array assignments can segfault → break into local var first.

### 2.3 Networking

- [ ] `RegisterNetSyncVariable*` is called in the **constructor**, not in `Init`.
- [ ] Types: Bool, Int, Float, Object. **No** strings.
- [ ] Same vars, same order on client and server (bitstream alignment).
- [ ] Override `OnVariablesSynchronized` for each registered SyncVar.
- [ ] Server guard: `GetGame().IsDedicatedServer()` (not `IsServer()` — returns true on client during load).
- [ ] Client guard: `!GetGame().IsDedicatedServer()` (not `IsClient()` — returns false on client during load).
- [ ] `SetSynchDirty()` after each SyncVar write on server.

### 2.4 UI / Layout

- [ ] `.layout` path matches `$PBOPREFIX$`.
- [ ] Widget names = script references, exact (case sensitive).
- [ ] Dabs MVC: widget names = ViewController property names, exact.
- [ ] `ScriptViewMenu` ghost-menu guard: `if (layoutRoot)` before operating.
- [ ] Input lock: `ChangeGameFocus(1)` on open, reverse on close.
- [ ] Cursor: `ShowUICursor(true)` on open, reverse on close.
- [ ] Cleanup in destructor / `OnHide`: remove handlers, null refs.

### 2.5 Actions

Pipeline `Can()` verificado contra `vanilla ActionBase.c`:

```
1. ConditionMask      — bitwise (vehicle, ladder, swimming, restrain, raised...)
2. Stance             — IsFullBody / IsPlayerInStance / IsRolling
3. Target owner       — si el target es de otro jugador → reject
4. CCT.Can()          — ConditionTarget (CCTObject=range, CCTCursor, CCTNone)
5. CCI.Can()          — ConditionItem (CCINone, CCIDummy)
6. ActionCondition()  — override custom, SOLO CLIENTE
7. FullBody stance    — verifica transición de stance si aplica
```

- [ ] `CreateConditionComponents` overridden with correct CCT/CCI.
- [ ] `ActionCondition` uses client-available data only (see §1).
- [ ] Target type: `GetType()` for exact, `IsKindOf()` for inheritance.
- [ ] **Non-pickup items**: use `RemoveAction(ActionTakeItem)` + `RemoveAction(ActionTakeItemToHands)`. **Keep** `IsTakeable=true`. (`IsTakeable=false` hides item from vicinity panel but does **not** block custom actions.)
- [ ] Overrides of `CanPutInCargo()` / `CanPutIntoHands()` if item should not be stored.
- [ ] Stringtable key exists, or use hardcoded string for testing.

### 2.6 .rvmat materials

- [ ] Stage2 DT: `color(0.5,0.5,0.5,0.5,DT)` — alpha 0.5, not 1.0.
- [ ] Stage4 AS: `color(0,1,1,1)` — **without** "AS" suffix, R=0.
- [ ] Stage6 fresnel: copy of vanilla ref of same shader type.
- [ ] Damage / destruct: uses vanilla `generic_damage_mc.paa` / `generic_destruct_mc.paa`.
- [ ] `forcedDiffuse` alpha: `0,0,0,1`, not `0,0,0,0`.
- [ ] **Compare each stage** against a working vanilla .rvmat of the same shader.

### 2.7 Persistence (OnStoreSave / OnStoreLoad)

- [ ] `version` field is managed by the **engine** — do not serialize it manually. `OnStoreLoad(ctx, version)` receives `version` as parameter.
- [ ] Save and Load in **exactly** the same order (sequential binary).
- [ ] Each `ctx.Write()` has its `ctx.Read()` at the same position.
- [ ] `super.OnStoreSave(ctx)` / `super.OnStoreLoad(ctx, version)` **first**.
- [ ] Check return of each `ctx.Read()` → `return false` on failure.
- [ ] `AfterStoreLoad` for post-load init (not in `OnStoreLoad`).
- [ ] Test: delete persistence files → verify clean start.

### 2.8 Edge cases — logical patterns

Applies to any feature with collections, state, or lifecycle:

- [ ] **Empty collection (count=0)**: loop body does not execute. Notify **before** clearing, not after.
- [ ] **Null/empty state**: no group, no flag, no items in slots. Guard nullcheck before each access.
- [ ] **State transitions**: `active→abandoned`, `raised→lowered`, `powered→unpowered`. Cache is updated on **each** transition and UI reflects new state.
- [ ] **Cache vs entity lifecycle**: if entity is destroyed, is cache cleared?
- [ ] **Player reconnection**: client cache is lost upon disconnect. How is it rebuilt? (RPC on connect, SyncVar re-sync.)
- [ ] **Concurrent operations**: two players acting on same entity simultaneously.

### 2.9 Refactor — state coherence (mandatory when consolidating logic around side-effects)

A refactor moving a guard / validation / rate-limit across an irreversible engine call (`super.OnStartServer`, `super.OnExecuteServer`, `ObjectDelete`, RPC send, `SetSynchDirty`, file write) can introduce **orphan state**: engine did half the work, guard rejects the rest, world remains incoherent.

**For each `return` / early-exit of the refactor**, list:

- What irreversible engine state has been mutated up to this point?
- If we return now, does the world remain in a coherent state?

If the 2nd answer is "no" → guard is in the wrong place. Move it **before** the irreversible call.

Patrones de orphan verificados:

- **ORPHAN-1**: rate-limit / validation **after** `super.OnStartServer` of an open/toggle action. The super already flipped `IsOpen()`; rejecting follow-up leaves container physically open with cargo virtualized in `.lfv`. Fix: pre-super rate-limit, gated on inferred intent. Ref: `LFV_ActionProbe.RateLimitAllowsOpen` in LF_VStorage Layer 6 v3.1.
- **ORPHAN-2**: SyncVar write across `SetSynchDirty()` uncoordinated with constructor registration order. Silent bitstream desync. Fix: register and write in same fixed order; one `SetSynchDirty()` per coherent batch.
- **ORPHAN-3**: entity destruction inside `foreach` over a registry, continuing loop. Stale ref → NPE/crash. Fix: collect entities-to-delete in temporary array, delete after foreach.

Reglas de proceso:

- **"Preserve original behavior" is a NON-goal** when original has bugs. Each "preserved" is a hypothesis to verify, not a fact to defend.
- **"Pre-existing / not introduced by refactor" is not an exemption.** For the audit, demand explicit signoff (fix-now / flag-for-later).
- **When an orphan is caught, run sibling-grep cross-codebase** — the bug rarely lives in a single place.

---

## 3. Debug / fix hierarchy (top-down, mandatory when something "does not work")

When something fails after implementing, diagnose top-down. **Never debug layer N+1 until confirming that layer N works.**

**Layer 1 — Config/Engine**
- [ ] Correct `scope` in `config.cpp`.
- [ ] Inherits from correct parent.
- [ ] Config compiles without errors.

**Layer 2 — Entity setup**
- [ ] Entity spawns in game.
- [ ] Correct `IsTakeable` (true for items with actions).
- [ ] Base class provides expected functionality.

**Layer 3 — Action registration**
- [ ] `AddAction(MyAction)` in entity `SetActions()` override.
- [ ] Action class compiles.
- [ ] `CreateConditionComponents` sets correct CCT/CCI.

**Layer 4 — Client conditions**
- [ ] `ActionCondition()` uses client-available data only (§1).
- [ ] Correct target type check.
- [ ] CCT range / component matches expected interaction distance.

**Layer 5 — Server execution**
- [ ] Server-side methods (`*Server()`) execute.
- [ ] Permissions / validation pass.
- [ ] Data writes succeed.

**Layer 6 — Response path**
- [ ] RPC returns to client.
- [ ] Client cache updates.
- [ ] UI refreshes.

Rules:
- Propose fix **and explain why** before implementing it.
- Confidence < 90% → ask before applying.
- After fix: re-run §2.8 (edge cases) in case fix introduced another problem.

---

## 4. Catalog of recurring errors

Errors made more than once. Check **actively** during implementation.

| ID  | Error | Correct | Source |
|-----|-------|----------|--------|
| E01 | `requiredAddons[]={"DabsFramework"}` | `{"DF_Scripts"}` or `{"DF_GUI"}` | UILab, config.cpp |
| E02 | `imageSets` in CfgSlots or root | Inside `CfgMods > Mod > defs > imageSets` | ArmorAddition |
| E03 | Same variable name in sibling scopes | Hoist before conditional | UILab crash |
| E04 | rvmat Stage4 with `AS` suffix | `color(0,1,1,1)` without suffix, R=0 | ArmorAddition |
| E05 | rvmat Stage2 DT alpha=1.0 | Alpha=0.5: `color(0.5,0.5,0.5,0.5,DT)` | ArmorAddition |
| E06 | rvmat fresnel guessed | Copy from vanilla ref of same shader | ArmorAddition |
| E07 | rvmat procedural damage | Use `generic_damage_mc.paa` / `generic_destruct_mc.paa` | ArmorAddition |
| E08 | Assuming a function exists because it "makes sense" | Verify in skill, vanilla, or internet | Multiple |
| E09 | Continuing beyond context saturation | Stop, checkpoint, handoff to `30_Sessions/` | Multiple |
| E10 | `forcedDiffuse` alpha 0 | Alpha 1: `0,0,0,1` | ArmorAddition |
| E11 | String in `ActionCondition` (client) | Strings not syncable. Client cache or int ID | SimpleGroup |
| E12 | `IsTakeable=false` to prevent pickup | `RemoveAction(ActionTakeItem/ToHands)`. `IsTakeable=false` only hides from vicinity, custom actions continue | SimpleGroup |
| E13 | Notify **after** clearing collection | Loop over 0 = 0 notifications. Notify before | SimpleGroup |
| E14 | Downstream debugging without upstream verification | Follow §3 hierarchy. Check IsTakeable/AddAction before ActionCondition | SimpleGroup |
| E15 | Cache not cleared on state transition | Each state change → update cache (client + server) | SimpleGroup |
| E16 | Fix without mapping client/server boundary | Complete §1 before writing fix | SimpleGroup |
| E17 | SyncVar bitstream client/server mismatch | Same vars, same order, both sides | CF Issue #143 |
| E18 | `IsServer()` / `IsClient()` for guard | Use `IsDedicatedServer()` / `!IsDedicatedServer()` | Expansion Pitfalls |
| E19 | `version` manually serialized | Engine manages it. Use `version` param of `OnStoreLoad` | vanilla EntityAI.c |
| E20 | Blaming p3d/config for placement bug when cause is in `Hologram.c` of another mod | Grep `modded class Hologram` across ALL loaded mods before touching p3d. A6_Base_Storage, BBP, etc. rewrite `GetProjectionEntityPosition`/`EvaluateCollision` | Chests stacking |
| E21 | Rate-limit / validation post-`super.OnXxxServer` → orphan state | Pre-super, gated on inferred intent. See §2.9 ORPHAN-1 | LF_VStorage Layer 6 v3.1 |
| E22 | "Preserves original behavior" treated as audit-pass when original has bugs | Non-goal. Each preserved is hypothesis. See §2.9 process rules | LF_VStorage Layer 6 v3→v3.1 |
| E23 | Sketchy pattern labeled "pre-existing" and silently dragged | Stop, explicit signoff, sibling-grep cross-codebase | LF_VStorage Layer 6 v3→v3.1 |
| E24 | Vehicle nested class override (`class SimulationModule: SimulationModule`, `Axles`, `Front`, `Rear`…) in a child mod WITHOUT declaring forward-ref `class X;` in root of child CfgVehicles → CfgConvert `Undefined base class 'X'` (compile-blocking) | Declare `class SimulationModule; class Axles; class Front; class Rear;` (whichever override uses) in root of child mod CfgVehicles. Each config.cpp has its own scope; does not inherit forward-refs from parent PBO | kt_roadkill_armed bug-003 |
| E25 | `ProcessDirectDamage(DT_FIRE_ARM, ...)` copied from a source (BRDM-2) → `DT_FIRE_ARM` is not a vanilla symbol (only comment in `object.c`) → compile fail | `DamageType.FIRE_ARM` (enum in `damagesystem.c`). Any `DT_*` seen in other mod sources may be custom non-portable aliases | kt_roadkill_armed bug-002 |
| E26 | `modded`/`extends` class re-declares member variable already declared by vanilla base (e.g. `m_NoiseSystem` in `CarScript`) → compile `Multiple declaration of variable 'X'` | Do NOT re-declare; reuse inherited one (CarScript already initializes `m_NoiseSystem`/`m_NoisePar`). Proactive check before compiling: grep each own `m_*` against base chain (carscript.c, car.c, transport.c, entityai.c, itembase.c) | kt_roadkill_armed bug-004 |
| E27 | Override with parameter name differing from base signature (e.g. `OnExecuteServer(ActionData actionData)` when base uses `action_data`) → compile `Can't find variable 'X'`. Enforce is NOT like C++/C#: param name in an `override` MUST match base | Copy signature with EXACT param names from base. Verify against base class vanilla file (grep method def) | kt_roadkill_armed bug-006 |
| E28 | `attachments[] += {...}` in CHILD mod (class inheriting vehicle in ANOTHER PBO) does NOT inherit base list — parsed config contains ONLY items from `+=`, breaking ALL slots (battery/wheels/doors). Verified with CfgConvert -xml | Materialize `attachments[] = {...}` with COMPLETE list from base + new ones at end. Do not rely on `+=` on parent from another PBO | kt_roadkill_armed bug-007 |
| E29 | Vehicle nested class override (`SimulationModule`/`Axles`/`Front`/`Rear`) with `: X` resolving to EMPTY forward-refs, omitting sub-blocks (`class wheels`) → malformed SimulationModule, half-broken vehicle (cannot enter, broken slots/wheels). NOT just "compiles": loads and breaks gameplay | Replicate pattern of original config: `class SimulationModule: SimulationModule` but inside `class Axles`/`Front`/`Rear` WITHOUT `: X` and WITH full `class wheels` (Left/Right). Or do not override if only changing minor physics | kt_roadkill_armed bug-007 (symptoms 1/3) |
| E30 | `GetInventory().CreateAttachment("<slot>")` / `CreateInInventory("<slot>")` passing SLOT name to mount part → API takes item **CLASS name**, not slot; if they differ it creates nothing (silent, no RPT error). Masked because in vanilla slot is usually named same as class (`CarBattery`, `SparkPlug`, `Reflector_1_1`) | Pass item **CLASS name** (e.g. `LFQuad_Wheel_Front`, NOT slot `LFQuad_wheel_1_1`); engine fills first compatible free slot per call. Cross-reference class (CfgVehicles) vs slot (CfgSlots/inventorySlot) before writing | LFQuad Sprint 0 R21 F1 (2026-05-26) |
| E31 | Vehicle (`: CarScript`) or custom wheel class (`: CarWheel`) without `class DamageSystem { class GlobalHealth ... }` → crash `[Object::GetMaxHealth] No DamageSystemData or not initialized` when accessing health (admin `SetHealth01`, damage, collision, possible sync). CarScript/CarWheel bases do NOT guarantee it | Declare `DamageSystem.GlobalHealth.Health { hitpoints; healthLevels[]; }` explicitly on vehicle AND on each custom wheel class (Croco sets it on its wheels, `croco_config.cpp:251/292`). Minimum viable = `GlobalHealth` only, without `DamageZones` | LFQuad Sprint 0 crash 2026-05-25 + R21 F2 (2026-05-26) |

---

## 5. Severity inflation in audits

Pattern observed in LFPowerGrid audits: labeling as `P1 — crash` findings that are actually `P2 — recoverable VM exception, server keeps running`. Cause: extrapolating from log message (`String CORRUPTED`) to actual behavior (process dies) without verifying.

Operational antidote before writing audit findings:

1. Reproduce bug on local server.
2. Log full cycle (load → execute → autosave → reload).
3. Distinguish:
   - **crash** — process dies, server goes down, requires restart.
   - **VM exception** — Enforce VM exception, log spam, execution continues.
   - **corruption** — bad data persists, code runs with it.
   - **degradation** — feature functions worse but runs.
   - **cosmetic** — visual only / without functional effect.
4. Finding label uses the concrete term from step 3, not "crash" as a generic.

Referencia cruzada: R4 + R30 del `CLAUDE.md` global.

---

## 6. Severity of ABSENCE + minimums required by engine (added 2026-05-25)

§5 classifies severity of an observed BUG. This section classifies severity of
something MISSING. "Incomplete feature" is not the same as "its absence crashes".

**Rule (LL-076):** in any gaps audit, label each finding by **severity
of absence**: does lacking it crash / break loading, or merely leave a feature
incomplete? An engine minimum deferred as a "high-level feature" can be a
masked P1 crash. LFQuad real case: `DamageSystem` filed as deferred "feature N3
(damage)" → its absence gives `[Object::GetMaxHealth] No DamageSystemData` (crash)
upon touching health (admin tools / damage / collision / sync).

**Checklist of engine minimums (anti-crash) — validate EARLY, separated from feature tiers:**

- **Vehicle (`CarScript`)**: `class DamageSystem { class GlobalHealth { class Health { hitpoints; healthLevels[]; }; }; }` — without this, any `GetMaxHealth`/`SetHealth` crashes. (Complete `DamageZones` ARE a feature; `GlobalHealth` is anti-crash baseline.) Also verify part classes (wheels) if their health is touched.
- **Vehicle**: constructor that sets engine sound strings (`m_EngineStart*`) — empty = broken audio / possible exception with SoundSet "".
- **Model `.p3d`**: Geometry LOD with convex components + mass (without this it does not simulate); action selections (`seat_*`, `refill`, doors) in the LOD that the cursor resolves (ViewGeometry for actions — verified LFQuad).
- **Generic**: if an engine baseline is "deferred", separate it in the plan as **P1 anti-crash** apart from the full feature, not in the late phase bucket.

Process antidote: parity audit (Phase 2 type) must include a pass of
"engine baselines per subsystem" in addition to the feature checklist, to avoid discovering
crashes one by one in-game.

Cross-ref: R4, R31, LL-076, §5.

---

## Mantenimiento

- When a session catches an error already in §4, do not add it again — use the existing ID as reference in the handoff.
- When a session catches a new recurring error (seen ≥ 2 times), add a new entry with sequential ID.
- If an entry becomes obsolete (engine changed, official patch), strike through with date + replacement, do not delete (historical memory).
- Last revision: 2026-05-17 (when refactoring skill `dayz-mod-workflow` for the 3-layer pipeline).

## Related

- [[dayz-enforce-script-reference]] — hard syntax/memory/networking rules that these checklists reference.
- [[dayz-capacidades-verificadas]] — build/config gotchas and feasibility verdicts complementary to the error catalog.
- [[dayz-modded-class-server-stub-pattern]] — E-pattern of server-only method without base stub (compile fail on client).
- [[dayz-model-pipeline]] — checklist 2.6/2.7 (rvmat, persistence) and engine baselines in `.p3d` (§6).
- [[workflow]] — the "when" of the process; this file is the "what" to verify.

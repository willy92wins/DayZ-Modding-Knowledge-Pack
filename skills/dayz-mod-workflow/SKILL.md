---
name: dayz-mod-workflow
description: >
  DayZ mod implementation and debugging protocol. Governs HOW to implement and
  fix, not WHAT. Client/server data mapping (mandatory before each feature),
  anti-confabulation (verify every API), debug hierarchy (top-down 6-layer
  diagnosis), edge case checklists, error catalog of verified recurring mistakes,
  checkpoint/handoff system for context degradation. Use ALONGSIDE domain skills
  (enforce-script-reference, dayz-ui-development, dayz-particles, etc.), not
  instead of them. Triggers: "implement", "write the code", "build the mod",
  "fix the bug", "debug this", "it doesn't work", "actions not showing",
  sprint execution, or any transition from plan to code/fix.
---

# DayZ Mod Implementation & Debug Protocol

Process skill for implementing and fixing DayZ mods. Does not contain domain
knowledge (that lives in domain skills). Ensures domain knowledge is correctly
applied and gaps are detected before they become bugs.

---

## 1. ACTIVATION CHECK

Pre-code ceremony routing (which gate applies when — Grill A → `dayz-feature-spec` → Grill B → this skill) is fixed by the single source: `<vault>\AI\00_System\workflow.md` §Árbol de decisión pre-código. Do not self-declare this skill mandatory without that context. (SP-050)

Before writing or fixing ANY code:

- [ ] Is there an approved plan/design? If NO -> plan first.
- [ ] Which domain skills apply? Load them NOW (not from memory):
  - Enforce Script -> `enforce-script-reference`
  - UI/layout -> `dayz-ui-development`
  - Particles -> `dayz-particles`
  - 3D models -> `dayz-model-pipeline`
  - PBO packaging -> `dayz-pbo-build`
  - Physics/collision/raycast -> `dayz-physics-engine`
  - Sound/CfgSoundSets -> `dayz-sound-system`
  - AI/infected/creature behavior -> `dayz-ai-patterns`
  - Build+deploy+launch loop -> `dayz-test-ingame`
- [ ] Is vanilla/mod reference code available for key patterns? If NO -> ask user.
- [ ] List all files to implement/fix, in dependency order.

---

## 2. PER-FILE PROTOCOL

For EACH file produced or modified:

### 2a. Write/edit the file

Follow all rules from `enforce-script-reference`. When in doubt about ANY
function, class, method, or parameter:

**GOLDEN RULE: If it's not in a loaded skill AND not in vanilla/mod code the
user has provided AND you haven't verified it -> STOP.**

Options when stopped:
1. Search the internet for the exact API/function
2. Check reference files in loaded skills
3. Ask user to provide a vanilla/mod example
4. Mark as ASSUMED in the mini-audit

NEVER use a function because "it makes sense that it would exist."

### 2b. Mini-audit

After each file, include:

```
## Mini-audit: [filename]
| API/Function         | Source                    | Status   |
|----------------------|---------------------------|----------|
| CreateObjectEx       | enforce-ref / vanilla     | VERIFIED |
| SomeWidget.SetColor  | dayz-ui-dev ref           | VERIFIED |
| entity.GetSomeMethod | not found                 | ASSUMED  |
```

**HARD RULE: If >2 items are ASSUMED -> do NOT advance. Resolve first.**

### 2b-linter. Offline Enforce/layout lint

Corre el **gate estructural obligatorio** (`script_validator.py`, y `ui_reconcile.py` si hay UI) — contrato completo, exit codes y limites en la seccion "Gates offline" mas abajo. Exit 1 bloquea. Es la capa OFFLINE; el comportamiento in-game lo cubre DayZ-MCP.

### 2c. Run type-specific checklist (Section 4)

---

## 2.5 CLIENT/SERVER DATA MAP

**MANDATORY before writing ANY feature involving entity state, actions, or UI.**

### Step 1: Fill this table

```
| Data needed       | CLIENT? | SERVER? | Bridge mechanism         |
|-------------------|---------|---------|--------------------------|
| (fill per feature)|         |         | SyncVar / RPC / Cache    |
```

### Hard rules (verified against vanilla EntityAI.c):

- **SyncVar types**: Bool, BoolSignal, Int, Float, Object ONLY.
  `RegisterNetSyncVariableString` DOES NOT EXIST.
- **Bitstream alignment**: Client and server MUST register same SyncVars in
  same order. Mismatch corrupts ALL synced data silently.
- **ActionCondition()** runs on BOTH sides: on the CLIENT for action menu
  display AND on the SERVER as the action-start gate
  (`actionmanagerserver.c:142` calls `pickedAction.Can(...)`; `Can()` calls
  `ActionCondition(player, target, item)` at `actionbase.c:898`).
  ActionCondition must only rely on data available on BOTH sides; a
  client-only cache passes the menu but the server rejects the action
  start silently.
- **OnStart/OnFinish/OnUpdate with "Server" suffix** runs on SERVER.
  Use server-only data here.
- Server DOES re-execute `Can()` (and therefore `ActionCondition()`) before
  starting the delivered action (`actionmanagerserver.c:142`) - it does NOT
  blindly trust client selection.
- If you need a string on client -> use ScriptRPC to populate a client
  cache, or encode as int hash via SyncVar. For data read inside
  ActionCondition, the SyncVar route is the only safe one (both sides).
- **If uncertain whether data is client-available -> treat as NOT available.**

---

## 3. CHECKPOINT PROTOCOL

### When to checkpoint:
- After every 2-3 files
- When generating code faster than thinking about it
- After >15 exchanges in implementation mode
- When uncertain about something written 5+ messages ago

### Format:

```
## CHECKPOINT
### Done:
  file1.c - status
  file2.c - status
### Pending:
  file3.c - what's needed
### New uncertainties:
  [things discovered not in the plan]
### Context: [low/medium/high/critical]
  Recommendation: [continue / finish current file / stop + handoff]
```

### Context rules:
- HIGH -> finish current file, checkpoint, recommend new session
- CRITICAL -> stop immediately, write handoff (Section 7)
- NEVER produce code past HIGH context. Quality WILL drop.

---

## 4. CHECKLISTS BY FILE TYPE

### 4.1 config.cpp

- [ ] `CfgPatches` class name matches addon folder name
- [ ] `requiredAddons` uses CfgPatches class names:
  - CommunityFramework: `"JM_CF_Scripts"` (NOT `"CommunityFramework"`)
  - DabsFramework: `"DF_Scripts"` or `"DF_GUI"` (NOT `"DabsFramework"`)
  - Vanilla: `"DZ_Data"`, `"DZ_Scripts"`
- [ ] `hiddenSelections[]` count matches `hiddenSelectionsTextures[]` count
- [ ] `scope = 2` spawnable, `1` reference, `0` abstract
- [ ] Inheritance: verify parent exists or is in requiredAddons
- [ ] `inventorySlot` = string for single, `inventorySlot[]` = array for multiple
- [ ] `ghostIcon`: `"set:setname image:imagename"` - verify imageset exists
- [ ] `imageSets` inside `CfgMods > Mod > defs > imageSets`, NOT in root/CfgSlots

### 4.2 Enforce Script - General

Defer to `enforce-script-reference` for full rules. Key verified restrictions:

- [ ] No ternary operators (`? :` does not compile)
- [ ] `ref` only on member fields, never on locals/params/returns
- [ ] Never use `delete` keyword (segfault if references still exist)
- [ ] `foreach`: works, but NEVER directly on getter returns (NPE on 2nd item).
      Assign to local variable first, then iterate.
- [ ] `m_` prefix on all member fields
- [ ] No `new` allocations inside periodic ticks - use m_ fields + `.Clear()`
- [ ] Complex expressions in array assignments can segfault - break into local var first

### 4.3 Networking

- [ ] `RegisterNetSyncVariable*` called in CONSTRUCTOR (not Init)
- [ ] Types: Bool, Int, Float, Object only. NO strings.
- [ ] Same vars, same order on client AND server (bitstream alignment)
- [ ] `OnVariablesSynchronized` override for every registered SyncVar
- [ ] Server guard: `GetGame().IsDedicatedServer()` (NOT `IsServer()` - returns true on client during load!)
- [ ] Client guard: `!GetGame().IsDedicatedServer()` (NOT `IsClient()` - returns false on client during load!)
- [ ] `SetSynchDirty()` after every SyncVar write on server

### 4.4 UI / Layout

- [ ] `.layout` path matches `$PBOPREFIX$`
- [ ] Widget names match script references exactly (case sensitive)
- [ ] Dabs MVC: widget names = ViewController property names exactly
- [ ] `ScriptViewMenu` ghost menu guard: check `if (layoutRoot)` before ops
- [ ] Input lock: `ChangeGameFocus(1)` on open, reverse on close
- [ ] Cursor: `ShowUICursor(true)` on open, reverse on close
- [ ] Cleanup in destructor/OnHide: remove handlers, null refs

### 4.5 Actions

**DayZ Action Pipeline** (verified against vanilla ActionBase.c `Can()` method):

```
1. ConditionMask  - bitwise (vehicle, ladder, swimming, restrain, raised...)
2. Stance         - IsFullBody / IsPlayerInStance / IsRolling
3. Target owner   - if target belongs to another player -> reject
4. CCT.Can()      - ConditionTarget (CCTObject=range, CCTCursor, CCTNone)
5. CCI.Can()      - ConditionItem (CCINone, CCIDummy)
6. ActionCondition()  - custom override, runs CLIENT (menu) AND SERVER (start gate, actionmanagerserver.c:142)
7. FullBody stance    - if full body, verify stance transition
```

- [ ] CreateConditionComponents overridden with correct CCT/CCI
- [ ] ActionCondition uses ONLY data available on BOTH client and server (see 2.5)
- [ ] Target type: `GetType()` for exact, `IsKindOf()` for inheritance
- [ ] **Non-pickupable items**: Use `RemoveAction(ActionTakeItem)` +
      `RemoveAction(ActionTakeItemToHands)`. Keep IsTakeable=true.
      (IsTakeable=false hides item from vicinity panel but does NOT block custom actions)
- [ ] `CanPutInCargo()` / `CanPutIntoHands()` overrides if item shouldn't be stored
- [ ] Verify stringtable key exists or use hardcoded string for testing

### 4.6 .rvmat Materials

- [ ] Stage2 DT: `color(0.5,0.5,0.5,0.5,DT)` - alpha 0.5, not 1.0
- [ ] Stage4 AS: `color(0,1,1,1)` - NO "AS" suffix, R=0
- [ ] Stage6 fresnel: copy from vanilla ref of same shader type
- [ ] Damage/destruct: use vanilla `generic_damage_mc.paa` / `generic_destruct_mc.paa`
- [ ] `forcedDiffuse` alpha: `0,0,0,1` not `0,0,0,0`
- [ ] Compare EVERY stage against known working vanilla .rvmat

### 4.7 Persistence (OnStoreSave / OnStoreLoad)

- [ ] Version field managed by ENGINE - do NOT serialize manually.
      `OnStoreLoad(ctx, version)` receives version as parameter.
- [ ] Save and Load in EXACTLY same order (raw sequential binary stream)
- [ ] Every `ctx.Write()` has matching `ctx.Read()` in same position
- [ ] Always call `super.OnStoreSave(ctx)` / `super.OnStoreLoad(ctx, version)` FIRST
- [ ] Check return value of every `ctx.Read()` -> return false on failure
- [ ] `AfterStoreLoad` for post-load init (not OnStoreLoad)
- [ ] Test: delete persistence files -> verify clean start works

### 4.8 Edge Cases - Logic Patterns

Run for ANY feature with collections, state, or lifecycle:

- [ ] **Empty collection (count=0)**: Loop body never executes.
      Send notifications BEFORE clearing, not after.
- [ ] **Null/empty state**: No group, no flag, no items in slots.
      Guard every access with null check.
- [ ] **State transitions**: active->abandoned, raised->lowered, powered->unpowered.
      Does cache update on EACH transition? Does UI reflect new state?
- [ ] **Cache vs entity lifecycle**: If entity destroyed, is cache cleaned up?
- [ ] **Player reconnection**: Client cache lost on disconnect.
      How is it rebuilt? (RPC on connect? SyncVar re-sync?)
- [ ] **Concurrent ops**: Two players acting on same entity simultaneously.

---

## 5. RECURRING ERROR CATALOG

Verified errors committed more than once. Check ACTIVELY during implementation. The full table (Error / Correct / Source) lives in **`references/error-catalog.md`**; the one-line index is here:

- **E01** — `requiredAddons[]={"DabsFramework"}`
- **E02** — `imageSets` in CfgSlots or root
- **E03** — Same variable name in sibling scopes
- **E04** — rvmat Stage4 with `AS` suffix
- **E05** — rvmat Stage2 DT alpha=1.0
- **E06** — rvmat fresnel values guessed
- **E07** — rvmat damage using procedural color
- **E08** — Assuming function exists because "makes sense"
- **E09** — Continuing past context saturation
- **E10** — `forcedDiffuse` alpha 0
- **E11** — string in ActionCondition — not syncable; use an int ID via SyncVar (readable on both sides), a client-only cache passes the menu but fails the server-side `Can()` gate
- **E12** — IsTakeable=false to prevent pickup
- **E13** — Notify AFTER clearing collection
- **E14** — Debug downstream without verifying upstream
- **E15** — Cache not cleaned on state transition
- **E16** — Fix without mapping client/server boundary
- **E17** — SyncVar bitstream client/server mismatch
- **E18** — `IsServer()`/`IsClient()` for server/client guard
- **E19** — Version field manually serialized in persistence
- **E20** — modded vehicle won't drive, `WheelCountPresent()=0` while `WheelCount()=N` — `CfgSlots.<wheel-slot>.selection` must exist in the body FireGeometry LOD with a wheel proxy

---

## 5.5 DEBUG/FIX PROTOCOL

When something "doesn't work" after implementation, diagnose TOP-DOWN.

### Diagnostic hierarchy (MANDATORY order):

**Layer 1 - Config/Engine:**
- [ ] `scope` value correct in config.cpp?
- [ ] Class inherits from correct parent?
- [ ] Config compiles without errors?

**Layer 2 - Entity setup:**
- [ ] Entity spawns in-game?
- [ ] IsTakeable setting correct? (true for items with actions)
- [ ] Base class provides expected functionality?

**Layer 3 - Action registration:**
- [ ] `AddAction(MyAction)` in entity's `SetActions()` override?
- [ ] Action class compiles?
- [ ] `CreateConditionComponents` sets correct CCT/CCI?

**Layer 4 - Client conditions:**
- [ ] `ActionCondition()` uses only data available on BOTH sides? (see 2.5 — the server re-runs it as the start gate)
- [ ] Target type check correct?
- [ ] CCT range/component matches expected interaction distance?

**Layer 5 - Server execution:**
- [ ] Server-side methods (`*Server()`) execute?
- [ ] Permissions/validation pass?
- [ ] Data writes succeed?

**Layer 6 - Response path:**
- [ ] RPC sent back to client?
- [ ] Client cache updated?
- [ ] UI refreshed?

### Rules:
- **Never debug layer N+1 until layer N is confirmed working.**
- **Propose fix + explain WHY before implementing.**
- **Confidence < 90% -> ask user before applying.**
- **After fix: re-run edge case checklist (4.8).**

### Disciplina de medición antes de otra hipótesis

Después de confirmar las capas estáticas, no saltes automáticamente a otra
lectura o a una bisección. Primero acredita qué midió el instrumento y si el
código sospechoso pudo ejecutar antes del síntoma:

1. **Acredita la pregunta y el instrumento (LL-287).** Antes de apoyar una
   decisión en una medida, escribe “este comando contesta X, no Y” y conserva
   tres salidas: `PASS`, `FAIL` e `INCONCLUSIVE/SETUP_FAIL`. Los barridos de
   privacidad son case-insensitive y buscan variantes; una muestra ordenada por
   ruta no permite estimar proporciones; un protocolo de reproducción no vale
   hasta producir al menos un rojo con el arreglo apagado; y un error de
   dependencias se repite en el entorno conocido-correcto antes de atribuirlo al
   repo. Si el primer instrumento concluye “está limpio”, confirma con otro
   instrumento independiente.

2. **Runtime mudo: sonda de recepción (LL-261).** Si el camino estático está
   verificado de extremo a extremo y el runtime sigue callado, detén el análisis
   por lectura y coloca una sonda mínima en la primera línea del receptor de cada
   lado pertinente. Todo guard fail-closed registra, con rate-limit, el motivo de
   `DROP` desde el diseño. Distingue primero “no llegó” de “llegó y fue rechazado”;
   solo después continúa por la jerarquía.

3. **Prueba alcanzabilidad temporal antes de bisecar (LL-304).** En una supuesta
   regresión, demuestra que el diff ejecutó antes del síntoma. Si no hay marcador
   previo, la correlación con el build no atribuye causalidad: instrumenta el
   callback que observa el efecto y captura la pila completa para nombrar al
   llamador. En cliente, emite la pila línea a línea porque el logger corta
   mensajes largos alrededor de 255 caracteres. Solo biseca el diff si su
   alcanzabilidad temporal está probada y la causa sigue abierta.

---

## 6. TESTING WITH FILEPATCHING (DayZDiag fast loop)

> Populated 2026-06-06 from source-verified deep-dive (vanilla v1.24; see
> LF_RollingStone_dev/research/deep-dive-2026-06-06/08-workbench-diagnostico.md). Line refs +-3.

### The fast loop (script-only iteration in seconds)

1. **DayZDiag_x64.exe** (ships with DayZ Tools) defines `DIAG_DEVELOPER`, has **no BattlEye** and
   does **not** require mod signatures (.bisign) — ideal dev runtime.
2. Launch: `-filePatching -dologs -noPause -mission=P:\<mission>` (+ `-connect/-port` for MP,
   `-profile` to boot with EnProfiler on).
3. Edit `.c` under `P:\<Mod>\scripts\...` -> **restart the mission** to reload. There is NO
   runtime hot-reload.
4. `config.cpp`/model/layout changes are NOT file-patched -> those still need the full PBO rebuild.
5. Logs: `%LOCALAPPDATA%\DayZ\*.RPT` (+ `.mdmp` crash dumps alongside; open with WinDbg/VS).

**When to use which cycle**: filePatching loop for script logic (fixes, prints, tuning);
full AddonBuilder+server cycle (R5 grouping still applies) for config.cpp, models, layouts and the
final validation gate.

**Hard stop — 2 ciclos sin convergencia**: dos ciclos in-game del MISMO tipo
(parche→rebuild→test) sin progreso medible → PARA, no lances un 3º. Antes del 3er
rebuild, haz (a) bisección pipeline-vs-data offline (Layer 7) o (b) cambio de estrategia
(instrumentación Print/Shape/DiagMenu, o preguntar al usuario). "Una variable por ciclo"
es el anti-patrón de Layer 7 trasladado al loop in-game: ilusión de progreso, O(N)
rebuilds. Caso real (SUB_BRZ s8, `30_Sessions/2026-06-25-introspeccion.md`): "4 parches
sin test limpio — debí parar tras 2". Endurece el "3+ rebuilds" de R5 a un tope de 2.


**Cliente atascado en la carga (~148 MB) — rotar `storage_1`**: el cliente diag
arranca, se queda en la pantalla de aviso de mods y no progresa. Su `script_*.log`
se congela tras `Module: World`, el proceso responde, y la memoria se queda en
**~148 MB** (un cliente que carga de verdad pasa de 2.000 MB). No es falta de
foco ni un cuelgue del proceso. Arreglo: rotar `storage_1` de la misión
(`...\DayZServer\mpmissions\dayzOffline.chernarusplus\storage_1` → renombrar,
nunca borrar) y relanzar; el servidor lo regenera limpio. Verificado 2026-08-22:
tras rotar, el mismo par arrancó entero y el jugador entró. El árbol ya acumula
decenas de backups con ese patrón (`storage_1_stuck-loading-*`,
`storage_1.bak_corrupt-modstorage-*`). Coste a declarar: rotar el storage borra
el estado persistente del mundo — los vehículos spawneados desaparecen y hay
que volver a crearlos.

### Debug tooling matrix

| Tool | Build | Use |
|---|---|---|
| `Shape.Create*` / `Debug.Draw*` | ALL builds (retail too) | 3D overlay: spheres/lines/bbox/matrix. `ShapeFlags.ONCE` auto-destroys — never keep that pointer (`endebug.c:133`) |
| `DbgUI.Begin/Text/Check/SliderFloat/Button/PlotLive` | all builds; call every frame in OnUpdate | live tuning panels (`1_core/proto/dbgui.c:59-126`) |
| `DiagMenu` (WIN+ALT in-game) | `DIAG_DEVELOPER` only | register via `modded class PluginDiagMenu` overriding `RegisterModdedDiagsIDs()` (ids via `GetModdedDiagID()`) + `RegisterModdedDiags()`; hard limit 512 IDs (`plugindiagmenumodding.c:52`); wrap mod code in `#ifdef DIAG_DEVELOPER` or it silently no-ops |
| `EnProfiler` | diag/developer builds | `SetModule(EnProfilerModule.WORLD)` -> `Enable(true)` -> `Dump()` to RPT (`1_core/proto/enprofiler.c`); proto natives are not tracked individually (:70) |
| `LogManager` CLI switches | all | `-doLogs -doSyncLog -doInvMoveLog -doActionLog -doWeaponLog -doWeatherLog ...` read at boot, zero recompile (`3_game/tools/debug.c:714-723`) |

### Logging discipline

- `Print/PrintFormat` -> RPT, cheap. `PrintToRPT` forces fflush per call — reserve for messages that
  must survive a crash (`endebug.c:98`).
- `ErrorEx(msg, severity)` auto-prefixes `[Class::Method] :: [SEVERITY]`.
- Server adminlog: `server.cfg` `adminLogPlayerHitsOnly/adminLogPlacement/adminLogBuildActions` +
  `g_Game.AdminLog(text)` (`game.c:668`).

### Known limits (verified)

- No script hot-reload; mission restart per change.
- Workbench ScriptEditor has **no verified breakpoint/step-debug API** — debugging is prints +
  shapes + DbgUI + DiagMenu.
- `GetDiagDrawMode` physics-view indices are engine-side enums, not exposed to script
  (`game.c:780-793`) — drive them from the native DiagMenu.

---

## Gates offline: estructurales vs de comportamiento (added 2026-06-29)

Un gate offline que pasa NO autoriza declarar "listo" si valida ESTRUCTURA pero el
criterio de éxito es COMPORTAMIENTO del engine.

- **Gate estructural** (offline, determinista): clase==filename, paths existen,
  topología/winding/UV, sumas de selección, braces, APIs citadas (2b), skeleton/bind
  comparado contra vanilla. Predice que el asset CARGA, no que se COMPORTA.
- **Gate de comportamiento** (solo el motor corriendo, o Buldozer): deform bajo
  animación, render/winding visible, masa/CoM/colisión, get-in, convención de proxy
  aplicada, IK codo/muñeca. NO derivable offline ni por un sandbox que no sea el
  propio engine.

### Gate estructural OBLIGATORIO antes de declarar nada listo

No es una recomendación ni un "ver también": **si no lo has corrido, no está listo.**

```
python tools/dayz-script-validator/scripts/script_validator.py <addon_root>
```

Exit `0` = PASS · `1` = FAIL · `2` = WARN. **Exit 1 bloquea**: se arregla o se
justifica por escrito en el handoff, con el rule id y el motivo. Un WARN se lee, no
se ignora en silencio.

Si el mod tiene UI, el gate incluye además:

```
python tools/dayz-script-validator/scripts/ui_reconcile.py <addon_root>
```

que cruza `FindAnyWidget`/`FindWidget` contra los widgets reales del `.layout` y las
claves `#STR_` contra el stringtable — dos fallos que compilan y solo aparecen al
abrir el menú.

Cuesta bajo un segundo sobre un addon completo, así que **no hay excusa de coste**:
corre en cada pasada, no solo al final. Caza la familia de errores que solo se
manifiesta al compilar el módulo en el boot (`Unknown type`, redeclaración de local,
override de método ausente, `delete`, `#ifdef` vacío, override de item en el `CfgXxx`
equivocado) y que de otro modo se paga con un ciclo in-game de minutos.

**Lo que este gate NO autoriza**, y es el punto entero de esta sección: verde aquí
predice que el módulo COMPILA y que el asset CARGA. No dice nada del comportamiento
del engine. El gate de comportamiento sigue siendo obligatorio aparte.

Cobertura conocida: las tablas de `scripts/shared/vanilla_reference.py` son
deliberadamente pequeñas (el linter no parsea `P:\scripts` en runtime), así que hay
falsos negativos por diseño y nunca falsos positivos por esa vía. Verde no es prueba
de ausencia.

**Regla**: antes de iterar sobre una métrica offline, pregunta "¿correlaciona con el
criterio de comportamiento, o es un proxy que el engine puede ignorar?". Proxy sin
correlación demostrada → UN test de comportamiento ANTES de seguir puliendo el proxy;
si no correlaciona, deja de pulirlo.

**Anti-patrón (casos reales, semana 2026-06-23)**:
- Deform de personaje: el deform-test en Blender bajó el edge-stretch 34×→6-9× en ~12
  iteraciones offline con CERO mejora in-game — el motor skinea contra el
  OFP2_ManSkeleton REAL del `model.cfg`, no contra el armature del FBX → gate falso
  (`30_Sessions/2026-06-24-LFInfectedBig-s8-offline-gate-false-green.md`).
- Proxy de vehículo: `derive_proxy_frame`=identidad dio "verde" offline 2 veces; el
  engine aplicó otra convención → body-proxy rotado ~90°
  (`30_Sessions/2026-06-24-MercedesAMGLF-fase2-smoke-FAIL-proxy-rotation.md`).

**Cross-ref**: G3 (verificación honesta: declarar QUÉ se verificó y qué NO), Layer 7
(bisección), R5 (no malgastar ciclos), SP-020 (gate real = tree compilable).

---

## 7. HANDOFF DOCUMENT TEMPLATE

When session ends mid-implementation:

```markdown
# Handoff: [Mod] - Session [N]

## Context
- Plan: [filename]
- Skills needed: [list]

## Done
1. path/file1.c - status, caveats
2. path/file2.c - status, caveats

## Pending
3. path/file3.c - what, dependencies, uncertainties
4. path/file4.c - what, dependencies, uncertainties

## Unresolved
- [ ] uncertainty 1
- [ ] uncertainty 2

## Errors found -> add to Error Catalog if recurring

## Notes for next session
```

## Pre-implementation grill — checklist obligatoria DayZ (added 2026-05-28, LL-043)

ANTES de escribir config.cpp / model.cfg / scripts de un mod DayZ, recorre esta
checklist con el usuario. **Es opt-out, no opt-in**: el Grill Modo A genérico
del `workflow.md` no captura los ejes propios de DayZ; saltarse esto regenera
LL-043 (presunciones silenciosas).

### Regla de presentación para usuarios no técnicos
Por cada eje: ofrecer **opciones cerradas con default recomendado** vía
`AskUserQuestion` (no preguntas abiertas). Si el usuario no entiende la pregunta,
explicarla con un ejemplo vanilla concreto, NO rellenar con un default silencioso.
Si una respuesta ramifica (lo siguiente cambia según), preguntar **una a una**
(excepción legítima a R18, como en el Grill Modo B del workflow).

### Ejes a cubrir (mínimo para CUALQUIER objeto colocable/usable)

1. **Crafteo (si aplica)** — cantidades exactas, herramienta requerida (sí/no
   y cuál), tiempo de animación, sonido. Default razonable: 2-6 unidades de
   material principal, sin herramienta, 1-3 s.
2. **Carga en manos** — peso (g), `itemSize` (slots — avisar si va a ser
   "solo en manos" por tamaño), pose de transporte (default vs específica).
3. **Deploy / colocación** — sonidos del holograma, superficies válidas
   (terreno / interior / agua), orientación inicial, snap horizontal vs sigue
   pendiente, rotación durante holograma.
4. **Estado colocado** — **pickup sí/no y cómo** (esto es crítico y se
   silencia muy fácilmente: aclarar que NO añadir acción de recoger ≠ que el
   motor no la tenga por defecto; si no se quiere pickup, hay que
   `RemoveAction(ActionTakeItem)` + `RemoveAction(ActionTakeItemToHands)` +
   `CanPutInCargo()=false` + `IsTakeable()=false`). Daño: hitpoints, fuentes
   (balas/melee/clima), comportamiento a 0 HP (ruin/destroy), drops al
   destruirse. `carveNavmesh`. Persistencia y tiempo de vida.
5. **Cargo interno** — ¿guarda items dentro? Si vestible: slots de attachment
   expuestos (subconjunto o todos).
6. **Visual / UX** — icono de inventario (`.paa`, generar o esperar al usuario),
   `displayName`/`descriptionShort` (idioma, tono, stringtable.xml con
   `#STR_<PREFIX>_*`).
7. **Spawn / distribución** — solo crafteo / loot / trader / admin /
   combinación. Compatibilidad TraderPlus / Expansion Market si aplica.
8. **Mod paraguas (si lo es)** — política: mismo PBO para todos los objetos
   futuros vs sub-mods. Naming convention de clases (`<PREFIX>_<Objeto>`).
9. **Compatibilidad con mods de terceros** — Expansion / CF / Dabs /
   TraderPlus / territorios (BBP, Expansion Territory). Preguntar qué corre el
   server.
10. **Fases avanzadas (si las hay)** — para personajes vestibles, vehículos,
    crafteo complejo: enumerar los ejes propios de esa fase (slots, cargo en
    prendas, decaimiento, límites…).

### Anti-patrón a evitar
"El usuario eligió X — por implicación también querrá Y / Z". NO. Cada decisión
se confirma. Si una etiqueta de opción contiene varios features ("se coloca, tiene
vida, se puede recoger"), tratar cada feature como confirmación INDEPENDIENTE
antes de implementarlo (en sesión "Mannequin Fase 1" la etiqueta "deployable
base-building" incluía "se puede recoger", el usuario tuvo que cortarlo a mano
durante la implementación).

### Plantilla reusable
Caso real con default + pregunta por punto, sirve de molde:
`<DayZ Projects>/Mannequin_dev/_grill-pendiente.md`.

### Cross-ref
LL-043, R18 (preguntar antes de presuponer), R25 (no añadir no pedido — extender
a "no presumir no pedido"), R26 (criterios verificables), workflow.md Grill
Modo A.

---

## Debug hierarchy — Layer 7: Bisección de componentes (added 2026-06-02)

**Cuándo activar**: cuando los 6 niveles top-down anteriores (logs/RPT/script.log → config → ScriptRPC → engine class hierarchy → datos client/server → race conditions) no han aislado la causa y el síntoma es **binario** (PASS/FAIL, visible/invisible, action sale/no sale, CoM=0/CoM≠0).

**Procedimiento** (caso `.p3d` multi-LOD; el patrón generaliza a mods multi-módulo y pipelines multi-fase):

1. **Lista de componentes separables** del sistema:
   - `.p3d`: cada LOD (Visual, Geometry, FireGeo, ViewGeo, LandContact, Memory, Shadow).
   - Mod: cada submódulo (clase modded, RPC, layout, animación, particle).
   - Pipeline: cada fase (extract → assemble → bake → binarize → PBO → deploy).

2. **Construye un híbrido control + test**: mitad-A del que funciona, mitad-B del que falla. Para `.p3d`: copia el .p3d-control, sustituye sus LODs FireGeo+ViewGeo por los del .p3d-test (preservando la mitad A = Visual+Geometry+resto). Para mods: en `config.cpp`, hereda del módulo control y sobrescribe solo los miembros del módulo test sospechoso.

3. **Reproduce el síntoma** en el híbrido:
   - Si **falla** → el bug está en la mitad B (LODs FireGeo+ViewGeo del test); recurse.
   - Si **pasa** → el bug está en la mitad A (Visual+Geometry+resto del test); recurse.

4. **Repite bisectando** hasta aislar el componente concreto. Converge en log₂(N) experimentos para N componentes (3 LODs = 2 bisecciones; 8 submódulos = 3 bisecciones).

5. **Solo entonces** lees el mecanismo (R31) dentro del componente aislado y nombras la causa raíz `path:line`. La bisección aísla el componente; R31 exige leer el código para nombrar la causa, no solo "está en el componente X".

**Anti-patrón a evitar**: variar parámetros del componente sospechoso ("¿y si la masa es no-uniforme?", "¿y si la topología es tris?", "¿y si el material es metalplate?") antes de bisecar componentes. Cada variación es un experimento concreto que da la **ilusión de progreso**, pero si la sospecha inicial es errónea, gastas O(N) variaciones sin llegar al bug. La bisección refuta o confirma la sospecha en log₂(N) experimentos.

**Caso real** (LFQuad N1.5 cerrado 2026-06-02): `.p3d` del LFQuad nacía con `CoM=(0,0,0)` en ODOL desplegado. Toda la evidencia inicial apuntaba al Geometry LOD (masa, topología, material). 5 binarizaciones de ensayo-error refutaron material/masa-distribución/topología/skeleton/writer; **2 binarizaciones de bisección** (híbrido Croco+LFQuad-Geo + LFQuad-sin-FireGeo) aislaron la causa al FireGeo LOD (un tagg `#Mass#` espurio con ceros que binarize priorizaba sobre el del Geometry). Handoff: `30_Sessions/2026-06-02-LFQuad-placement-fix-firegeo-mass-CLOSED.md`.

**Preventivo (no solo reactivo)**: para un PATH/PIPELINE NUEVO (primer export skinned,
primera convención de proxy, primer crew-selection, scope de modo de fuego en un
`CfgWeapons` nuevo) corre un CONTROL conocido-bueno por el mismo pipeline ANTES de la
1ª iteración sobre tu asset. ¿Hay un vanilla que ya lo hace? Léelo / round-tríppealo
primero: debinariza el `.p3d` vanilla, lee el `bin.pbo` de la config vanilla, o pasa un
modelo vanilla por tu exporter. Si el CONTROL tampoco pasa, el bug está en el PIPELINE,
no en tu asset. Casos de esta semana que esto atajaba: el scope de `Mode_FullAuto`
(eclipsaba a la vanilla — visible leyendo el `bin.pbo` vanilla, no teorizando sobre
modelo/anim; `30_Sessions/2026-06-28-A6_SR2M-bug10-fullauto-resolved.md`) y la malla
espejada L↔R (cazada al comparar el skeleton vanilla debinarizado, tras ~8 sesiones
iterando contra el rig FBX; `30_Sessions/2026-06-25-LFInfectedBig-mirror-fix-deform-solved.md`).

### Cross-ref
R35 (diagnóstico diferencial multi-dimensional), R35.1 (bisección antes de ensayo-error, added 2026-06-02 en `codex-briefing.md`), R31 (mecanismo `path:line` tras aislar). LL-079 (la lección durable de bisección), LL-080 (#Mass# espurio en FireGeo, el caso concreto).

## (added 2026-06-01) Dev tree vs compilable tree: cite-then-verify del tree antes del valor (SP-020)

Cuando un mod DayZ tiene dos árboles paralelos (`<MOD>/` compilable + `<MOD>_dev/`
de trabajo), TODO valor de `config.cpp`/`model.cfg`/script citado como ground truth
debe identificar el tree de origen. Antes de citar:

1. Confirmar qué tree es el COMPILABLE (el que el usuario buildea/firma/deploya).
   Heurística: el que tiene `$PBOPREFIX$` con el path canónico, NO el sufijado `_dev`.
2. Leer el config del tree compilable, no del `_dev`.
3. Si los dos divergen, REPORTAR la divergencia como hallazgo (puede ser desync del
   `_dev` que necesita rebase), NUNCA elegir uno como ground truth tácitamente.

Recidiva docs: LL-073, LL-025 (R8 extendido), handoff 2026-05-29/05-30 LFQuad.

<!-- [merged 2026-06-05 from <claude-home>\skills user copy during plugin-canonical migration] -->
### 4.9 Refactor - state coherence (MANDATORY when consolidating logic across side-effecting calls)

A refactor that moves a guard / validation / rate-limit across an irreversible
engine call (`super.OnStartServer`, `super.OnExecuteServer`, `ObjectDelete`,
RPC send, `SetSynchDirty`, file write) can introduce **orphan state**: the
engine has done half the work, the guard rejects the rest, and the world is
left incoherent.

**For every `return` / early-exit in the refactored function**, list:
- What irreversible engine state has been mutated up to this point?
- If we return now, is the world in a coherent state?

If the answer to the second question is "no" -> the guard is in the wrong
position. Move it BEFORE the irreversible call.

**Verified orphan patterns:**

- **ORPHAN-1: Rate-limit / validation AFTER `super.OnStartServer` of an
  open/toggle action.** Super already flipped `IsOpen()`; rejecting the
  follow-up LFV restore leaves the container physically open with cargo still
  virtualized in `.lfv`. Symptoms: empty open container in-game, `.lfv` file
  not consumed.
  **Fix**: rate-limit pre-super, gated on inferred intent (preState == CLOSED
  for toggles; asserted CLOSED for split-open hooks). See `LFV_ActionProbe.RateLimitAllowsOpen`
  in LF_VStorage Capa 6 v3.1.
- **ORPHAN-2: SyncVar write between irrelevant `SetSynchDirty()` calls** without
  matching the constructor registration order. Bitstream desync on client;
  values appear stale-but-correctly-typed. Fix: register and write in same
  fixed order; one `SetSynchDirty()` after a coherent batch of writes.
- **ORPHAN-3: Entity destruction inside `foreach` over a registry**, then
  continuing the loop. Stale ref at next iteration -> NPE or crash. Fix:
  collect entities-to-delete in a temporary array, delete after the foreach.

**Process rules:**

- **"Preserves original behavior" is a NON-GOAL** when the original is buggy.
  Treat each "preserved" semantic as a hypothesis to verify, not a fact to
  defend. For every "preserved" line in your audit, ask: "should this be
  preserved?"
- **"Pre-existing / not introduced by the refactor" is not exemption.** If the
  audit notes a sketchy pattern with that label, STOP and get explicit user
  signoff (fix-now / flag-for-later). Quietly continuing is the worst option.
- **When auditor or user catches one orphan-state bug, immediately grep
  cross-codebase for the same pattern in sibling files.** The bug rarely
  lives in just one place. Verified: in LF_VStorage Capa 6, after the
  auditor caught ORPHAN-1 in `RunToggleAfterSuper`, sibling-grep
  revealed `LFV_ModdedActionOpenRaGItem` and `LFV_ModdedActionFurnitureOpen`
  carried the same pre-existing orphan pattern that should have been fixed
  in the same pass.

---

## 8-9. AUDIT ESCALATION (severity discipline + multi-agent isolation) -> `references/audit-escalation.md`

Severity-inflation discipline (crash vs VM exception vs corruption vs degradation vs cosmetic — verify before labelling) and multi-agent audit context isolation (independent `path:line` per agent, ≥1 adversarial agent, ≥20% random re-check) are in **`references/audit-escalation.md`**.

> These OVERLAP the **`rigorous-data-audit`** skill — invoke that skill to RUN a data-critical audit (its 7-step, 8-parallel-auditor workflow); the reference here is only the severity-labelling + auditor-independence protocol note.

## (added 2026-07-23) Al cambiar una constante de intervalo de scheduler, actualizar los harness de verificación con counts hardcodeados

Origen: LFPowerGrid T4 W4-F02 cambió `LFPG_VANILLA_FLUSH_S` de 30s a 5s (write-behind).
El gate `verify_corrective` (16 checks sobre el mod) FALLÓ en `PERF_SCHEDULE_MAP` porque su
harness `verify_scheduler.py` tenía los counts ESPERADOS hardcodeados con el valor viejo
(`FlushVanillaIfDirty: 2` en la ventana de 60000ms = 30s; ahora `12` = 5s; y `10`→`60` en
300000ms). El único diff era ese callback; el fix fue actualizar los 2 EXPECTED maps del
harness, NO el mod.

Regla: cuando un cambio de código toca una constante `*_MS` / `*_S` que alimenta un
scheduler/timer periódico, ANTES de declarar el gate de build/verify PASS:
1. Grep los harness de verificación (`tools/verify_*.py`, `tests/`) por counts/intervalos
   hardcodeados de ESE callback (EXPECTED maps, snapshots congelados de la cadencia).
2. Recalcular el count esperado = `ventana_ms / intervalo_nuevo_ms` y actualizar el harness
   (APPEND-only o edición mínima, con comentario trazable citando el finding que lo motiva).
3. Confirmar que SOLO ese callback difiere — los demás counts del map deben coincidir exactos.
   Si difiere otro callback, es un cambio de cadencia NO-INTENCIONAL: investigar antes de tocar
   el harness.
4. Un FAIL de un gate de verify por un cambio LEGÍTIMO de intervalo NO es un fallo del código:
   es el harness desactualizado. Actualizarlo es parte de cerrar el batch. NO enmascarar: el
   único diff debe ser el intencional, verificado item-por-item contra el map esperado.

## Reglas promovidas del corpus de lecciones (added 2026-07-27)

Promovidas desde `AI/20_Knowledge/lessons-learned.md` para que lleguen por trigger en vez
de depender de que alguien recuerde buscarlas. Cada regla cita su `LL-NNN` de origen;
la entrada completa (síntoma, origen, evidencia) vive allí. No quites la cita: el índice
`lessons-index.md` detecta la promoción buscando esa referencia dentro de las skills.

- **LL-013** — Aísla cambios de física, herencia y `SimulationModule` de las features, y valida cada bloque estructural por separado. No apruebes clases `modded`/`extends` hasta que pasen CfgConvert, compilación real y gate in-game.
- **LL-061** — Antes de otro bake sobre el mismo `.p3d`/`.pbo`, cierra el gate pendiente del bake anterior o decláralo bloqueado con causa explícita. No acumules cambios que vuelvan ambiguo el siguiente veredicto.
- **LL-147** — Para cualquier fallo de estado sincronizado, instrumenta cliente y servidor desde el primer ciclo y confirma el valor en el lado donde se observa el síntoma. Trata toda discrepancia entre lados como dato de primera clase antes de proponer el fix.
- **LL-199** — En probes client-side, coloca primero `t`, posición y estado; deja raws y flags al final. Mantén cada payload útil por debajo de ~225 caracteres para absorber el wrapper del logger.
- **LL-200** — Emite `t=GetTickTime()` al principio de cada línea de diagnóstico. Estima el offset server↔client con la mediana de pares RPC REQUEST/ACK, interpola una serie sobre la otra y descarta muestras con gaps excesivos.

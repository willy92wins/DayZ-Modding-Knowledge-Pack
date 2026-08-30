# Networking & Persistence in Enforce Script

## Architecture Overview

DayZ uses a client-server model. Server is authoritative. Key mechanisms:

1. **SyncVars** — Automatic variable synchronization (server → clients)
2. **ScriptRPC** — Manual remote procedure calls (bidirectional)
3. **Persistence** — OnStoreSave/OnStoreLoad for server restart survival

---

## SyncVars (RegisterNetSyncVariable)

SyncVars automatically replicate member field changes from server to all clients.

### Registration — MUST be in Constructor

```
class LF_MyDevice extends ItemBase
{
    // Declare the synced field
    bool m_PoweredNet;
    int m_LoadPercent;
    float m_Temperature;

    void LF_MyDevice()
    {
        // Register in constructor — NOT in EEInit, NOT anywhere else
        string varPowered = "m_PoweredNet";
        RegisterNetSyncVariableBool(varPowered);

        string varLoad = "m_LoadPercent";
        RegisterNetSyncVariableInt(varLoad, 0, 100);  // min, max for compression

        string varTemp = "m_Temperature";
        RegisterNetSyncVariableFloat(varTemp, 0.0, 200.0, 2);  // min, max, precision bits
    }
}
```

**Registration variants:**
- `RegisterNetSyncVariableBool(string varName)` — 1 bit
- `RegisterNetSyncVariableInt(string varName, int min, int max)` — compressed int
- `RegisterNetSyncVariableFloat(string varName, float min, float max, int precision)` — compressed float

### Writing SyncVars — Server Only

```
void SetPowered(bool state)
{
    #ifdef SERVER
    m_PoweredNet = state;
    SetSynchDirty();  // Marks entity for sync on next network tick
    #endif
}
```

**Always**: `#ifdef SERVER` guard + `SetSynchDirty()`. Without `SetSynchDirty`,
clients never see the change.

### Reading SyncVars — Client Callback

```
override void OnVariablesSynchronized()
{
    super.OnVariablesSynchronized();

    // m_PoweredNet is now updated on client
    // React to state change (visual updates, sounds, etc.)
    if (m_PoweredNet)
    {
        // Turn on lights, play sound, swap rvmat
    }
    else
    {
        // Turn off lights, stop sound
    }
}
```

**Important**: `OnVariablesSynchronized` fires on the CLIENT when ANY registered
SyncVar changes. You cannot know which specific variable changed — check all
relevant fields.

---

## ScriptRPC — Manual Remote Calls

For complex data or client→server communication, use ScriptRPC.

### Sending (Client → Server or Server → Client)

```
// Client sends to server (target = the entity)
void SendMyRequest(int data1, string data2)
{
    ScriptRPC rpc = new ScriptRPC();
    rpc.Write(data1);
    rpc.Write(data2);

    Object target = m_Device;  // entity the RPC targets
    int rpcId = LFPG_RPC_MY_REQUEST;
    bool guaranteed = true;
    PlayerIdentity identity = null;  // null = server

    rpc.Send(target, rpcId, guaranteed, identity);
    // ScriptRPC is consumed on Send — no need to delete
}

// Server sends to specific client
void SendResponseToClient(PlayerBase player, PlayerIdentity who, int result)
{
    ScriptRPC rpc = new ScriptRPC();
    rpc.Write(result);

    Object target = player;  // ← target = player entity (NOT null, NOT m_Device)
    int rpcId = LFPG_RPC_MY_RESPONSE;
    bool guaranteed = true;

    rpc.Send(target, rpcId, guaranteed, who);
}
```

### ⚠ Server → Client response: `target` MUST be the receiving player entity

This is the single most common reason "the UI never opens, no error in logs."

When your dispatcher routes incoming RPCs through `modded class PlayerBase.OnRPC`
(the LFPG pattern), a server response only reaches that OnRPC handler if the
RPC's `target` is the player entity. Other targets silently drop the RPC on
the client side — no crash, no warning, just nothing happens.

| target arg | identity arg | Where it lands on the client |
|------------|--------------|------------------------------|
| `player` (PlayerBase) | `sender` (identity) | ✅ `player.OnRPC` fires — **use this for every server→client response** |
| `m_Device` (any entity) | `sender` | ⚠ `m_Device.OnRPC` fires — only use if the receiver is on the device, not PlayerBase |
| `null` | `sender` | ❌ Dispatched but rarely reaches PlayerBase.OnRPC — UI won't open. Works for simple "write chat line" RPCs in some builds, flaky for the rest. |
| `null` | `null` | Broadcast to all, no specific handler — avoid |

Real-world incident (LFPG BTC ATM, 2026-04):
- Server response used `rpc.Send(null, CHANNEL, true, sender)` — UI never opened.
- Working sibling handlers (CCTV `HandleLFPG_RequestCameraList`, Sorter
  `HandleSorterConfigRequest`) all use `rpc.Send(player, CHANNEL, true, sender)`.
- Fix: pass the `PlayerBase player` parameter (that the dispatcher already
  hands your server handler) as the `target` in the response `rpc.Send`.

Canonical server→client response pattern, for handlers that receive
`(PlayerBase player, PlayerIdentity sender, ...)`:

```
rpc.Send(player, LFPG_RPC_CHANNEL, true, sender);
```

- `player` (target) — routes the RPC to that player's `PlayerBase.OnRPC` on the client.
- `sender` (identity) — network-layer filter: only that one client receives the packet.

Using only `identity=sender` without `target=player` does restrict the
network delivery, but without a target the client-side handler chain
usually doesn't fire.

### Receiving — OnRPC Override

```
override void OnRPC(PlayerIdentity sender, int rpc_type, ParamsReadContext ctx)
{
    super.OnRPC(sender, rpc_type, ctx);

    if (rpc_type == LFPG_RPC_MY_REQUEST)
    {
        // Server receives from client
        #ifdef SERVER
        int data1;
        if (!ctx.Read(data1))
            return;  // ALWAYS check Read return

        string data2;
        if (!ctx.Read(data2))
            return;

        // Validate sender identity
        if (!sender)
            return;

        // Process request...
        HandleMyRequest(sender, data1, data2);
        #endif
        return;
    }

    if (rpc_type == LFPG_RPC_MY_RESPONSE)
    {
        // Client receives from server
        int result;
        if (!ctx.Read(result))
            return;

        // Update UI...
        return;
    }
}
```

### RPC Best Practices

- **Validate sender identity by stable ID, never by `PlayerIdentity` instance (LL-259).** Derive `GetId()` on both sides and compare values; a reference comparison silently rejects a valid sender and survives any transport change. If two or more transports reach the same receiver and fail identically — measured: three distinct transports failed the same way while the RX probe showed the RPC always arrived, because two shared guards compared instances (`sender != GetIdentity()` on the receiver and `GetIdentity() == stored identity` in the player lookup) — audit the shared guards/lookup before changing transport.

1. **Always check `ctx.Read()` return** — false means corrupted/truncated packet
2. **Always validate sender identity** on server side
3. **Use guaranteed=true for important state** changes, false for cosmetic updates
4. **ScriptRPC is consumed on Send** — `new ScriptRPC()` is fine, no delete needed
5. **RPC IDs must be unique** per mod — use a dedicated constant block (e.g., 20100-20199)
6. **Rate-limit client RPCs** — anti-spam cooldown on server side
7. **Resolve targets by NetworkID**, not by DeviceId or reference caching

### NetworkID Pattern

```
// Get NetworkID from entity
int netLow;
int netHigh;
m_Device.GetNetworkID(netLow, netHigh);

// Resolve entity from NetworkID
Object resolved = GetGame().GetObjectByNetworkId(netLow, netHigh);
EntityAI entity = EntityAI.Cast(resolved);
if (!entity)
    return;  // Entity no longer exists
```

---

### Single-ID string-dispatch RPC bus (RPCManager pattern)

An alternative to a growing `enum` of RPC IDs: register **one** high fixed RPC id on `DayZGame.Event_OnRPC`,
and dispatch by a **function-name string** written as the first param. Adding a networked verb = writing a
method whose name matches the string — no enum bookkeeping, no per-message ID. This is the classic
community "RPCManager" (Cj187-style); verified in the wild in SIBNIC's Gunner mod
(`vault 30_Research/sibnic-gunner`, `RPCManager_Gunner`).

```c
protected const int FRAMEWORK_RPC_ID = 1004258;   // one high, unlikely-to-collide id

class RPCManager_X
{
    protected Class m_InstanceClass;                       // the object holding the handler methods
    void RPCManager_X()  { GetDayZGame().Event_OnRPC.Insert(OnRPC); }
    void ~RPCManager_X() { GetDayZGame().Event_OnRPC.Remove(OnRPC); }
    void Reg_Class(Class instance) { m_InstanceClass = instance; }
    Class GetInstanceClass() { return m_InstanceClass; }

    void OnRPC(PlayerIdentity sender, Object target, int rpc_type, ParamsReadContext ctx)
    {
        if (rpc_type != FRAMEWORK_RPC_ID) return;
        Param1<string> fn = new Param1<string>("");
        if (!ctx.Read(fn)) return;
        auto callData = new Param3<ParamsReadContext,PlayerIdentity,Object>(ctx, sender, target);
        GetGame().GameScript.CallFunctionParams(GetRPCManager_X().GetInstanceClass(), fn.param1, NULL, callData);
    }

    void SendRPC(ref array<ref Param> params, bool guaranteed = false,
                 ref PlayerIdentity toIdentity = NULL, ref Object toTarget = NULL)
    {
        GetGame().RPC(toTarget, FRAMEWORK_RPC_ID, params, guaranteed, toIdentity);
    }
}
static ref RPCManager_X g_RPCManager_X;
static ref RPCManager_X GetRPCManager_X() { if (!g_RPCManager_X) g_RPCManager_X = new ref RPCManager_X; return g_RPCManager_X; }
```

Sender writes the function name as the leading param:
```c
ref array<ref Param> p = new array<ref Param>;
p.Insert(new Param1<string>("MyVerb_Client"));          // dispatch name
p.Insert(new Param2<PlayerBase,int>(player, seatIdx));  // payload the handler reads
GetRPCManager_X().SendRPC(p, true, identity);
```
Handler (a method on the registered instance, e.g. a `modded MissionGameplay` that called
`GetRPCManager_X().Reg_Class(this)` in its ctor):
```c
void MyVerb_Client(ref ParamsReadContext ctx, ref PlayerIdentity sender, ref Object target)
{
    Param2<PlayerBase,int> par = new Param2<PlayerBase,int>(NULL, 0);
    ctx.Read(par);
    // ... act on par.param1 / par.param2
}
```

**Trade-offs.** Pro: trivial to add verbs, one id, self-documenting names. Con: `CallFunctionParams` is a
string dispatch (typo = silent no-op — no compile check on the verb name), the single id can still collide
if two mods pick the same number (pick a random high one), and there's no side/authority gating baked in —
the handler must check `GetGame().IsServer()` / validate the sender itself (a `*_Server` verb must not
trust client-supplied entities). Fail-closed on unknown/invalid payloads (`G6`).

- **`Event_OnRPC` fires for ALL `rpc_type` on BOTH processes** (`3_game\dayzgame.c:970`; `Invoke` at `:3089` is before the `if (target)` at `:3093` and **outside** the `#ifndef SERVER` / `#ifndef NO_GUI` that guard the vanilla `switch` at `:3102-3103`). `Serializer.Read` **consumes the context even when the type does not match** — there is no rewind (`1_core\proto\serializer.c:56-64`). A subscriber that calls `ctx.Read` before checking its own `rpc_type` eats another handler's payload; the downstream handler (`CfgGameplayHandler.OnRPC`, `UndergroundAreaLoader.OnRPC`) then gets `false` and the symptom ("cfggameplay never arrives", stamina/lighting glitches) points away from the mod. [MEASURED IN-GAME 2026-08-17: `Read` with `Param1<int>` over a `Param1<T>` payload returned true (value 3); the subsequent correct-type `Read` returned false.] The correct pattern is vanilla's: filter **`rpc_type` AND side** before any read (`syncevents.c:13`). Vanilla can read unfiltered inside `UndergroundAreaLoader.OnRPC` only because it is called from the `case` that already filtered (`dayzgame.c:3109-3113`); a mod in `Event_OnRPC` has no such `case`.
- **Do NOT derive mod RPC IDs from `ERPCs.RPC_END`.** The enum contains **96 lines conditioned on `#ifdef DIAG_DEVELOPER`** (`3_game\enums\erpcs.c:110-205`) **before** `RPC_END` (`:207`), so its numeric value **differs between diag and retail builds**. A derived ID mismatches in a client-diag / server-retail pair and fails **silently**: the RPC is sent, nobody handles it, no error. Use fixed high literals (`const int` with hex is vanilla idiom: `1_core\constants.c:35`, `:63-70`). Supporting fact: the `switch` in `DayZGame.OnRPC` has **no `default:`**, so an unknown `rpc_type` produces no engine error.
- **Hooking `Event_OnRPC` does NOT require `modded class DayZGame`.** `Event_OnRPC` is `static` and accessed by class name — vanilla idiom: `DayZGame.MISSION_STATE_GAME` (`dayzplayerimplement.c:837`), `DayZGame.DeferredInit` (`ppemanager.c:83`) — which avoids collision with another mod that overrides `OnRPC`. The `Insert` must NOT copy vanilla's timing: `SyncEvents.RegisterEvents()` lives in the `MissionGameplay` constructor (`missiongameplay.c:76`), which is **client-side and late**; it can afford that because its RPCs fire in `ClientNew`. A document sent in `ClientPrepare` (`missionserver.c:307-313`) arrives **before** that mission exists and is lost without trace.

### `Event_OnRPC`: filter before the first context read (SP-338, added 2026-08-31)

The bus above is safe because it rejects the RPC id before `ctx.Read`. `ParamsReadContext` is a `Serializer` (`3_game\gameplay.c:15`), and a read consumes its stream even when the requested payload type is wrong; there is no seek or rewind (`1_core\proto\serializer.c:55-65`). `DayZGame.Event_OnRPC` receives every RPC on both processes (`3_game\dayzgame.c:3089-3103`), so the id and applicable side must be rejected before any read.

```c
// WRONG: this can consume another handler's payload.
Param1<string> payload = new Param1<string>("");
if (!ctx.Read(payload)) return;
if (rpc_type != MY_RPC_ID) return;

// RIGHT: filter id and side first, then touch ctx.
if (rpc_type != MY_RPC_ID) return;
if (GetGame().IsDedicatedServer()) return; // client-only handler; invert for server-only
Param1<string> safePayload = new Param1<string>("");
if (!ctx.Read(safePayload)) return;
```

Use `IsDedicatedServer()` / `!IsDedicatedServer()` for load-time side filters rather than relying on `IsClient()`. A wrong-order subscriber can break a different mod or a vanilla consumer with no warning; when multiple subscribers are wrong, load order decides which one consumes the stream first.

### Server mutations observed to replicate without custom NetSync (SP-338, added 2026-08-31)

The following results were measured from a dedicated server to an already connected client, with both peers alive for the mutation:

| Server call | Observed on connected client without custom NetSync | Verified declaration |
|---|---|---|
| `SetObjectMaterial(int, string)` | Yes | `3_game\entities\entityai.c:2899` |
| `SetObjectTexture(int, string)` | Yes | `3_game\entities\entityai.c:2896` |
| `SetAnimationPhase(string, float)` | Yes, including fractional phases | `3_game\entities\entity.c:15` |
| `SetPosition(vector)` | Yes | `3_game\entities\object.c:300` |
| `SetScale(float)` | **No** | `1_core\proto\enentity.c:448` |

Replicate scale explicitly, for example with `RegisterNetSyncVariableFloat` (`3_game\entities\entityai.c:2876`), then apply the synchronized value on the client. The earlier registration example labels `precision` as bits; that label is not the contract for this API. The argument is decimal digits and defaults to `1`. Raise it when values such as `1.25` must survive range quantization, or pass equal minimum and maximum values when the unbounded form is intended. Scale also affects collision: otherwise identical LFProbe boxes at scale `1` and `0.5` produced vertical ray distances of `0.2018 m` and `0.1018 m` (ratio `0.5045`).

Measured replication does not establish late-join reconstruction or behavior for map-placed objects; both remain unverified. Animation state is also model-specific: `Barrel_ColorBase` drives its two caps from the phase (`4_world\entities\itembase\barrel_colorbase.c:148-154`), and phase `0.5` exposed both in the LFProbe measurement. `GetAnimationPhase` immediately after a write also returned the previous value in that probe. Verify the target model and the required observation timing.

---

## Persistence (OnStoreSave / OnStoreLoad)

Entities with persistence enabled save/load data across server restarts.

### Saving

```
override void OnStoreSave(ParamsWriteContext ctx)
{
    super.OnStoreSave(ctx);

    // Write in EXACT same order as OnStoreLoad reads
    ctx.Write(m_PoweredNet);
    ctx.Write(m_FilterJSON);
    ctx.Write(m_LinkedContainerLow);
    ctx.Write(m_LinkedContainerHigh);
}
```

### Loading

```
override bool OnStoreLoad(ParamsReadContext ctx, int version)
{
    if (!super.OnStoreLoad(ctx, version))
        return false;

    // Read in EXACT same order as OnStoreSave writes
    if (!ctx.Read(m_PoweredNet))
        return false;

    if (!ctx.Read(m_FilterJSON))
        return false;

    if (!ctx.Read(m_LinkedContainerLow))
        return false;

    if (!ctx.Read(m_LinkedContainerHigh))
        return false;

    return true;
}
```

### Version Management

When you add new persisted fields, you MUST handle the version transition:

```
override bool OnStoreLoad(ParamsReadContext ctx, int version)
{
    if (!super.OnStoreLoad(ctx, version))
        return false;

    // Original fields (v1)
    if (!ctx.Read(m_PoweredNet))
        return false;

    // New field added in v2
    if (version >= 2)
    {
        if (!ctx.Read(m_NewField))
            return false;
    }
    else
    {
        m_NewField = DEFAULT_VALUE;  // sensible default for old saves
    }

    return true;
}
```

**Critical**: If you change the persist format without version handling,
all existing entities with old data will fail to load → entity corruption.
On LFPowerGrid we do save wipes for major schema changes (v3+, no migrators).

### Persistence Config

In config.cpp, entities must declare `storageCategory`:
```
class LF_MyDevice: Inventory_Base
{
    scope = 2;
    storageCategory = 1;  // enables persistence
};
```

---

## Side Detection During Load

DayZ has a loading phase where side-detection functions return unexpected values:

| Function | During load | After load |
|---|---|---|
| `GetGame().IsServer()` | **true** even on client | true on server |
| `GetGame().IsClient()` | **unreliable** on client (not guaranteed true during load; see rules 19-20) | true on client |
| `GetGame().IsDedicatedServer()` | false on client (correct!) | false on client |
| `GetGame().IsMultiplayer()` | true (correct) | true |

**Rule**: Always use `GetGame().IsDedicatedServer()` for server-side checks,
and `!GetGame().IsDedicatedServer()` for client-side checks.

Exception: If you need to support offline/singleplayer mode, `IsServer()` is
correct (it returns true in singleplayer where the client IS also the server).

---

## File I/O

Enforce Script provides limited file operations:

```
// JSON serialization (typed)
JsonFileLoader<MyClass>.JsonLoadFile(path, myInstance);
JsonFileLoader<MyClass>.JsonSaveFile(path, myInstance);

// File existence check
bool exists = FileExist(path);

// Copy and delete (no rename!)
CopyFile(srcPath, dstPath);
DeleteFile(path);

// Directory operations
MakeDirectory(dirPath);
```

**There is no `RenameFile`** in Enforce Script. Use CopyFile + DeleteFile.

**Atomic save pattern** (battle-tested):
1. Write to `.tmp`
2. Verify `.tmp` is readable (optional, controlled by setting)
3. Backup existing file to `.bak`
4. CopyFile `.tmp` → target
5. DeleteFile `.tmp`
6. On load: if target missing but `.bak` exists → restore from backup

# Timers, Performance & EnProfiler

## Timer Mechanisms in DayZ

DayZ offers several timing mechanisms, each with tradeoffs.

### CallLater (ScriptCallQueue)

The most common timer. Runs a callback after a delay, optionally repeating.

```
// One-shot: execute after 5 seconds
GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(MyCallback, 5000, false);

// Repeating: execute every 3 seconds
GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(MyCallback, 3000, true);

// With parameters (up to 9)
GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(MyCallback, 5000, false, param1, param2);

// Cancel a scheduled call
GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).Remove(MyCallback);
```

**CallQueue categories:**
- `CALL_CATEGORY_SYSTEM` — System-level, runs even during loading
- `CALL_CATEGORY_GAMEPLAY` — Standard gameplay, paused during loading
- `CALL_CATEGORY_GUI` — UI updates

21b. **`CallLater` re-queued from within its own callback never fires again** (chain pattern: `fn` re-enqueues itself) — zero RPT errors, chain dies silently after the first step; the same `CallLater` fired from OUTSIDE the queue works normally. Remedy: `Timer(CALL_CATEGORY_GAMEPLAY).Run(s, this, "fn", null, true)` + `Stop()` on completion. Measured 2026-08-19 (SUB_BRZ_NavSpike s71 CallLater dies after S1 vs s74 Timer S1–S5 complete, client diag 1.29)

#### THE CALLLATER BUG — 4.5 Hour Precision Loss

**Known engine bug** (BI tracker T156746, unfixed as of DayZ 1.28+):

After ~4.5 hours of server runtime, `CallLater` intervals become increasingly
inaccurate. Root cause: internal time is stored as 32-bit float. After 16,200
seconds (4.5h), integer values above 16,777,216 lose precision due to IEEE 754
mantissa limits.

**Symptoms:**
- Callbacks scheduled every 5s start firing every 7s, 10s, 15s...
- After 8+ hours, some callbacks never fire at all
- Affects ALL mods using `CallLater` with `repeat=true`

**Workarounds:**
1. **Server restart schedule** — restart every 3-4 hours
2. **Timer class** — uses different internal mechanism, not affected
3. **Manual tick counter** — count frames in OnUpdate, fire when threshold reached

### Timer Class (Alternative)

The `Timer` class is NOT affected by the CallLater bug but is heavier on resources.

```
class MyManager
{
    ref Timer m_Timer;

    void Start()
    {
        m_Timer = new Timer(CALL_CATEGORY_GAMEPLAY);
        m_Timer.Run(5.0, this, "OnTick", null, true);  // 5s repeat
    }

    void Stop()
    {
        if (m_Timer)
        {
            m_Timer.Stop();
        }
    }

    void OnTick()
    {
        // Called every 5s, reliable even after 4.5h+
    }
}
```

**Timer class uses more memory** than CallLater (creates internal objects).
For a few timers this is fine. For 100+ devices each with their own Timer,
use the centralized tick pattern instead.

### Centralized Tick Pattern (LFPowerGrid standard)

**The architecture we use for all periodic device ticks:**

```
class MyNetworkManager
{
    // Single timer for ALL devices
    ref Timer m_GlobalTimer;

    // Device registry
    ref array<MyDevice> m_RegisteredDevices;

    void MyNetworkManager()
    {
        m_RegisteredDevices = new array<MyDevice>;
    }

    void StartGlobalTick()
    {
        m_GlobalTimer = new Timer(CALL_CATEGORY_GAMEPLAY);
        m_GlobalTimer.Run(5.0, this, "OnGlobalTick", null, true);
    }

    void RegisterDevice(MyDevice dev)
    {
        if (m_RegisteredDevices.Find(dev) < 0)
        {
            m_RegisteredDevices.Insert(dev);
        }
    }

    void UnregisterDevice(MyDevice dev)
    {
        int idx = m_RegisteredDevices.Find(dev);
        if (idx >= 0)
        {
            m_RegisteredDevices.Remove(idx);
        }
    }

    void OnGlobalTick()
    {
        int i;
        int count = m_RegisteredDevices.Count();
        for (i = 0; i < count; i = i + 1)
        {
            MyDevice dev = m_RegisteredDevices[i];
            if (dev)
            {
                dev.OnDeviceTick();
            }
        }
    }
}
```

**Why not per-device CallLater:**
- Each `CallLater(repeat=true)` allocates internal queue entries
- 100 devices × repeating callbacks = heap fragmentation
- After hours → "Illegal write" crash (confirmed in production)
- Single Timer + array iteration = zero fragmentation, reliable indefinitely

**Exception**: `ScriptRPC` calls that create `new ScriptRPC()` are fine because
they're consumed on Send (no accumulation).

---

## EnProfiler API

Enforce Script has a built-in profiler for measuring script performance.

### Basic Usage

```
// Enable profiling
EnProfiler.Enable(true, true);  // (enable, immediate)

// Set what to track
int flags = EnProfilerFlags.FUNCTION_TIMES | EnProfilerFlags.FUNCTION_COUNT;
EnProfiler.SetFlags(flags);

// ... run code to profile ...

// Get results
array<ref EnProfilerTimeFuncPair> timePerFunc = new array<ref EnProfilerTimeFuncPair>;
EnProfiler.GetTimePerFunc(timePerFunc, 20);  // top 20

int i;
for (i = 0; i < timePerFunc.Count(); i = i + 1)
{
    EnProfilerTimeFuncPair pair = timePerFunc[i];
    string funcName = pair.GetName();
    float timeMs = pair.GetTime();
    string msg = funcName;
    msg = msg + ": ";
    msg = msg + timeMs.ToString();
    msg = msg + " ms";
    Print(msg);
}

// Disable when done
EnProfiler.Enable(false);
```

### Available Queries

| Method | Returns |
|---|---|
| `GetTimePerFunc(out, count)` | Top N functions by time consumed |
| `GetTimePerClass(out, count)` | Top N classes by time consumed |
| `GetCountPerFunc(out, count)` | Top N functions by call count |
| `GetInstancesPerClass(out, count)` | Top N classes by instance count |
| `GetAllocationsPerClass(out, count)` | Top N classes by allocation count |
| `GetCountOfFunc(name, type, global)` | Call count of specific function |
| `GetTimeOfFunc(name, type, global)` | Time consumed by specific function |

### Profiling Flags

```
EnProfilerFlags.FUNCTION_TIMES    // Track time per function
EnProfilerFlags.FUNCTION_COUNT    // Track call count per function
EnProfilerFlags.CLASS_TIMES       // Track time per class
EnProfilerFlags.CLASS_COUNT       // Track instance count per class
EnProfilerFlags.ALL               // Track everything (expensive)
```

### Practical Profiling Workflow

1. Add profiling around suspected bottleneck
2. Run for representative scenario (many devices, full grid)
3. Check `GetTimePerFunc` — top functions are your bottleneck
4. Check `GetAllocationsPerClass` — high alloc count = GC pressure
5. Optimize: cache lookups, reduce allocations, batch operations
6. Re-profile to verify improvement

---

## Performance Optimization Patterns

### String Concatenation — Pre-build, Don't Repeat

```
// WRONG — builds string every tick
void OnTick()
{
    string msg = "Device ";
    msg = msg + GetType();
    msg = msg + " at ";
    msg = msg + GetPosition().ToString();
    Print(msg);  // called every 5s for 50 devices = 250 string builds
}

// CORRECT — cache when data changes, print cached
class MyDevice
{
    protected string m_CachedLabel;

    void UpdateCachedLabel()
    {
        m_CachedLabel = "Device ";
        m_CachedLabel = m_CachedLabel + GetType();
        m_CachedLabel = m_CachedLabel + " at ";
        m_CachedLabel = m_CachedLabel + GetPosition().ToString();
    }
}
```

### IsKindOf Caching

`IsKindOf` walks the class hierarchy — expensive for hot paths.

```
// WRONG — checked every tick for every item
string cat = "";
string kWeapon = "Weapon_Base";
if (item.IsKindOf(kWeapon))
    cat = "weapon";

// CORRECT — cache per typeName
static ref map<string, string> s_CategoryCache;

static string GetCategory(EntityAI item)
{
    if (!s_CategoryCache)
    {
        s_CategoryCache = new map<string, string>;
    }

    string typeName = item.GetType();
    if (s_CategoryCache.Contains(typeName))
    {
        return s_CategoryCache.Get(typeName);
    }

    string result = ComputeCategory(item);
    s_CategoryCache.Set(typeName, result);
    return result;
}
```

### Distance Checks — DistanceSq First

```
// WRONG — sqrt every check
float dist = vector.Distance(posA, posB);
if (dist < 50.0)

// CORRECT — compare squared distances (no sqrt)
float distSq = vector.DistanceSq(posA, posB);
float thresholdSq = 2500.0;  // 50^2
if (distSq < thresholdSq)
```

### Batch Network Operations

```
// WRONG — separate RPC per device
int i;
for (i = 0; i < deviceCount; i = i + 1)
{
    ScriptRPC rpc = new ScriptRPC();
    rpc.Write(devices[i].GetState());
    rpc.Send(devices[i], RPC_STATE, true, identity);
}

// CORRECT — single RPC with batch data
ScriptRPC rpc = new ScriptRPC();
rpc.Write(deviceCount);
int j;
for (j = 0; j < deviceCount; j = j + 1)
{
    rpc.Write(devices[j].GetState());
}
rpc.Send(anchor, RPC_BATCH_STATE, true, identity);
```

### Config Reads — Cache Results

`GetGame().ConfigGetInt()` etc. read from binarized config every call.

```
// Cache config values on first access
static ref map<string, int> s_ItemSizeCache;

static int GetItemSlotSize(EntityAI item)
{
    if (!s_ItemSizeCache)
    {
        s_ItemSizeCache = new map<string, int>;
    }

    string typeName = item.GetType();
    if (s_ItemSizeCache.Contains(typeName))
    {
        return s_ItemSizeCache.Get(typeName);
    }

    // Read from config
    string cfgPath = "CfgVehicles ";
    cfgPath = cfgPath + typeName;
    cfgPath = cfgPath + " itemSize[]";
    TIntArray sizes = new TIntArray;
    GetGame().ConfigGetIntArray(cfgPath, sizes);

    int area = 1;
    if (sizes.Count() >= 2)
    {
        area = sizes[0] * sizes[1];
    }

    s_ItemSizeCache.Set(typeName, area);
    return area;
}
```

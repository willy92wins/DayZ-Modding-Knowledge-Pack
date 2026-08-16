# Memory Management in Enforce Script

## Reference Counting & Garbage Collection

Enforce Script uses automatic reference counting (ARC) for memory management.
Unlike traditional GC (mark-and-sweep), ARC is deterministic — objects are
destroyed immediately when their reference count hits zero.

### Two Class Families

**Managed classes** (inherit from `Managed`):
- Use strong references by default
- Most DayZ game objects inherit from Managed (EntityAI → Object → Managed)
- Instances survive as long as at least one strong reference exists

**Non-Managed classes** (plain classes, no Managed ancestor):
- **Class fields** default to **weak** pointers — must use `ref` to keep target alive; without `ref` the field dangles when the referenced object is destroyed. This is where ref bugs actually live.
- **Local variables** default to **strong** references (per Bohemia's official Enforce Script wiki). ARC keeps them alive to end of scope. `new X()` assigned to a plain local survives the enclosing scope without needing `ref`.
- Summary: the "weak by default" rule applies to CLASS FIELDS specifically, not to locals.

### The `ref` Keyword — Strong References

`ref` creates a strong reference that keeps the target alive.

**CORRECT — ref on class member fields:**
```
class MyManager
{
    // Strong ref keeps the map alive as long as MyManager lives
    ref map<string, ref array<string>> m_Data;

    void MyManager()
    {
        m_Data = new map<string, ref array<string>>;
    }
}
```

**WRONG — these are actual errors:**
```
// WRONG: ref on function parameter (lifetime is caller's responsibility)
void Process(ref array<int> data) { }

// WRONG: ref on return type
ref array<int> GetData() { }

// WRONG: double ref in instantiation — the `new ref` is the error
ref TIntArray arr = new ref TIntArray;
```

**Redundant but NOT wrong — `ref` on local variable:**
```
// Valid but redundant — locals are strong by default per Bohemia wiki
void DoStuff()
{
    ref array<int> local = new array<int>;    // works
    array<int> also_valid = new array<int>;   // also works (preferred, idiomatic)
}
```
Vanilla DayZ code mixes both patterns freely in the same files (`construction.c`
has both `ref InventoryLocation` and plain `InventoryLocation` locals).
The plain form is idiomatic and shorter; `ref` on local is legal but adds
no extra semantics.

**Rule summary**: `ref` is REQUIRED on non-Managed class member fields
(otherwise they dangle). NEVER on params/returns. On locals it's optional
style — don't mass-refactor existing code just to remove them.

### `autoptr` — Scoped Strong References

`autoptr` is an alternative to `ref` that destroys the target when the
containing scope ends. Useful for local variables that need to survive
the scope but auto-cleanup.

```
void ProcessFile()
{
    autoptr FileSerializer file = new FileSerializer;
    // file survives until end of this function
    // then auto-destroyed
}
```

**NEVER combine `ref` and `autoptr`** on the same field — undefined behavior.

### The `delete` Keyword — NEVER USE

Despite what the BI docs say, `delete` is **never necessary** in Enforce Script.
All instances are garbage collected when reference count reaches zero.

Using `delete` on an object that still has references elsewhere causes a **segfault**.

```
// WRONG — causes segfault if anything else references obj
delete obj;

// CORRECT — just let it go out of scope or set to null
obj = null;  // decrements refcount, GC handles the rest
```

### Circular Reference Prevention

ARC cannot collect reference cycles. If A→B→A, neither is ever freed.

**The problem:**
```
class Parent
{
    ref Child m_Child;  // strong ref to child
}

class Child
{
    Parent m_Parent;  // If this were ref, circular leak!
}
```

**The solution — break cycles in destructors:**
```
class LFPG_SorterTagView extends ScriptView
{
    void ~LFPG_SorterTagView()
    {
        // Break the cycle: Tag → Controller → OwnerController → ... → Tag
        LFPG_SorterTagController ctrl = LFPG_SorterTagController.Cast(GetController());
        if (ctrl)
        {
            ctrl.m_OwnerController = null;
        }
    }
}
```

**Pattern for ObservableCollections:**
When an ObservableCollection holds ScriptView items that reference back to
the parent controller, clearing the collection alone is NOT enough — the
views' destructors must break the back-reference first.

### Common GC Traps

**Trap 1: Local instance vanishes prematurely**
```
// WRONG — timer callback: by the time it fires, myHandler is GC'd
void Setup()
{
    MyHandler handler = new MyHandler;
    string cbName = "OnTimer";
    GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(handler.OnTimer, 5000, false);
    // handler goes out of scope → GC'd → CallLater fires on dead object → segfault
}

// CORRECT — store as member field
class MyClass
{
    ref MyHandler m_Handler;

    void Setup()
    {
        m_Handler = new MyHandler;
        string cbName = "OnTimer";
        GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(m_Handler.OnTimer, 5000, false);
    }
}
```

**Trap 2: foreach on getter return**
```
// WRONG — getter returns weak ref, GC collects between iterations
void Test()
{
    foreach (string t: GetMyArray())  // NPE on 2nd element!
    {
    }
}

// CORRECT — assign to local first
void Test()
{
    array<string> arr = GetMyArray();
    int i;
    for (i = 0; i < arr.Count(); i = i + 1)
    {
        string t = arr[i];
    }
}
```

**Trap 3: map<Widget, T> crashes at runtime**
```
// COMPILES but crashes — Widget is not a valid map key in Enforce
ref map<Widget, int> m_WidgetMap;  // CRASH

// Use parallel arrays or a wrapper instead
ref array<Widget> m_Widgets;
ref array<int> m_Values;
```

### Memory Allocation in Tick Callbacks

**NEVER allocate inside repeated callbacks:**
```
// WRONG — allocates every 5s, fragments heap, crash after hours
void OnTick()
{
    array<EntityAI> devices = new array<EntityAI>;  // BAD
    // ...
}

// CORRECT — allocate once as member, clear each tick
class MyManager
{
    ref array<EntityAI> m_TempDevices;

    void MyManager()
    {
        m_TempDevices = new array<EntityAI>;
    }

    void OnTick()
    {
        m_TempDevices.Clear();
        // reuse m_TempDevices
    }
}
```

### Summary Table

| Usage | `ref` | `autoptr` | plain |
|---|---|---|---|
| Class member field | YES — keeps alive | YES — auto-cleanup | Weak ref, may GC |
| Function parameter | NEVER | NEVER | Always plain |
| Local variable | NEVER | OK for scoped lifetime | Weak ref |
| Return type | NEVER | NEVER | Always plain |
| `new` expression | NEVER (`new ref X` is wrong) | NEVER | `new X` |

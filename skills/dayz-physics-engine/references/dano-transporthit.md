# Deep-Dive: Damage System, Hitzones and Armor — DayZ v1.24

> Investigation: 2026-06-06  
> Source of truth: `<dayz-projects>\scripts\` (vanilla v1.24)  
> Anti-confabulation: every cited API is verified with Grep/Read in the indicated files.

---

## Resumen ejecutivo

The DayZ damage system (MDF — Modular Damage Framework) operates primarily in C++ with an Enforce Script scripting layer. The flow is:  
**damage source → `ProcessDirectDamage` (proto native) → C++ calculation with CfgAmmo → EEHitBy (server script callback) → secondary effects (Shock, Blood, animation, bleeding)**

For LF_RollingStone the relevant path is **TransportHit**: the rock must register as `Transport` (or call `RegisterTransportHit` directly from `EOnContact`) for system to apply damage proportional to velocity without requiring any customized ammo in mod base configs.

---

## API verificada

### 1. TotalDamageResult

```c
// scripts/3_game/damagesystem.c:1-5
class TotalDamageResult: Managed
{
    proto native float GetDamage(string zoneName, string healthType);
    proto native float GetHighestDamage(string healthType);
};
```

- `GetDamage("", "Health")` → total damage to global hitzone in healthType "Health".
- `GetDamage("Head", "Shock")` → specific Shock damage to "Head" zone.
- `GetHighestDamage("Health")` → highest Health damage value among all hit hitzones.

### 2. DamageType enum

```c
// scripts/3_game/damagesystem.c:10-17
enum DamageType
{
    CLOSE_COMBAT,   // 0
    FIRE_ARM,       // 1
    EXPLOSION,
    STUN,
    CUSTOM
}
```

Aliases used internally: `DT_CUSTOM`, `DT_FIRE_ARM`, `DT_CLOSE_COMBAT` correspond to enum values (verified by usage in RegisterTransportHit).

### 3. ProcessDirectDamage

```c
// scripts/3_game/entities/object.c:1134
proto native void ProcessDirectDamage(
    int damageType,          // DamageType enum value
    EntityAI source,         // entity causing the damage
    string componentName,    // damage zone name (empty string = global zone)
    string ammoName,         // nombre de CfgAmmo a aplicar
    vector modelPos,         // model space position of impact
    float damageCoef = 1.0,  // multiplier applied to ammo damage
    int flags = 0            // ProcessDirectDamageFlags
);
```

**ProcessDirectDamageFlags** (`scripts/3_game/entities/object.c:1-7`):
- `ALL_TRANSFER` — transfers damage to attachments and global (default).
- `NO_ATTACHMENT_TRANSFER` — does not transfer to attachments.
- `NO_GLOBAL_TRANSFER` — does not transfer to global.
- `NO_TRANSFER` — combination of both `NO_*`.

> `ProcessIndirectDamage` does not exist in scripts — indirect damage (radius explosions) is handled via `DamageSystem.ExplosionDamage` (C++). [UNVERIFIED as script function directly accessible on EntityAI.]

### 4. DamageSystem (static class)

```c
// scripts/3_game/damagesystem.c:20-25
class DamageSystem
{
    static proto native void CloseCombatDamage(EntityAI source, Object targetObject,
        int targetComponentIndex, string ammoTypeName, vector worldPos,
        int directDamageFlags = ProcessDirectDamageFlags.ALL_TRANSFER);
    static proto native void CloseCombatDamageName(EntityAI source, Object targetObject,
        string targetComponentName, string ammoTypeName, vector worldPos,
        int directDamageFlags = ProcessDirectDamageFlags.ALL_TRANSFER);
    static proto native void ExplosionDamage(EntityAI source, Object directHitObject,
        string ammoTypeName, vector worldPos, int damageType);
    // + script helper methods: GetDamageZoneMap, GetDamageZoneFromComponentName, ResetAllZones
}
```

`ResetAllZones` sets Health, Shock, and Blood to maximum across all DamageSystem zones of an entity (`scripts/3_game/damagesystem.c:139-154`).

### 5. SetHealth / GetHealth / DecreaseHealth / AddHealth

All are `proto native` on `Object` (`scripts/3_game/entities/object.c`):

| Function | Signature | Notes |
|---------|-------|-------|
| `GetHealth(zone, type)` | `proto native float` | zone="" → global; type="" → main health |
| `GetHealth01(zone, type)` | `proto native float` | Normalized 0..1 |
| `GetMaxHealth(zone, type)` | `proto native float` | Configured maximum |
| `SetHealth(zone, type, value)` | `proto native void` | Direct setting |
| `AddHealth(zone, type, value)` | `proto native void` | Addition (negative value = subtraction) |
| `DecreaseHealth(zone, type, value)` | `proto native void` | Subtraction only |
| `SetHealthLevel(int level, zone)` | script helper | Uses `GetHealthLevelValue` |
| `SetHealth01(zone, type, coef)` | script helper | `SetHealth(..., max*coef)` |
| `SetHealthMax(zone, type)` | script helper | Calls `SetHealth(max)` |
| `GetHealthLevel(zone)` | `proto native int` | 0=pristine…4=ruined |
| `IsDamageDestroyed()` | `proto native bool` | True = health <= 0 |

Referencia: `scripts/3_game/entities/object.c:977-1121`

Known health types (used in scripts): `"Health"`, `"Blood"`, `"Shock"`.  
Special zone `"GlobalHealth"` used in PlayerBase for HUD (`scripts/4_world/entities/manbase/playerbase.c:5321-5322`).

### 6. EEHitBy — full signature and parameters

```c
// scripts/3_game/entities/entityai.c:1117
void EEHitBy(
    TotalDamageResult damageResult,  // result of C++ damage calculation
    int damageType,                  // DamageType enum
    EntityAI source,                 // who caused the damage
    int component,                   // hit geometric component index
    string dmgZone,                  // damage zone name (e.g. "Head", "Torso")
    string ammo,                     // nombre del CfgAmmo aplicado
    vector modelPos,                 // impact position in model space
    float speedCoef                  // velocity coef (for projectiles)
)
```

**Called**: server only. Fires AFTER C++ applies damage.  
**Inheritance chain**:
1. `EntityAI.EEHitBy` — invokes `m_OnHitByInvoker` (`entityai.c:1117-1124`)
2. `ItemBase.EEHitBy` — random damage to cargo/attachments for clothing (`itembase.c:1522-1560`)
3. `PlayerBase.EEHitBy` — bleeding, shock check, broken legs, unconRefill (`playerbase.c:1224-1347`)
4. `DayZPlayerImplement.EEHitBy` — reset `m_TransportHitRegistered`, damage/death animations (`dayzplayerimplement.c:1547-1600+`)

### 7. EEHitByRemote

```c
// scripts/3_game/entities/entityai.c:1127
void EEHitByRemote(int damageType, EntityAI source, int component,
    string dmgZone, string ammo, vector modelPos)
```

Called only on **client that caused the hit**. Without `TotalDamageResult`. Used for local feedback (e.g. melee block sound in PlayerBase `playerbase.c:1349-1358`).

### 8. EEKilled

```c
// scripts/3_game/entities/entityai.c:1078
void EEKilled(Object killer)
```

Called on server when entity is eliminated. Invokes `m_OnKilledInvoker` and analytics. If `ReplaceOnDeath()` → schedules `DeathUpdate()` via CallLater.

### 9. EEDelete

```c
// scripts/3_game/entities/entityai.c:934
void EEDelete(EntityAI parent)
```

Called when eliminating entity from world (also propagates to inventory).

### 10. EEHealthLevelChanged / OnDamageDestroyed

```c
// scripts/3_game/entities/entityai.c:1027
void EEHealthLevelChanged(int oldLevel, int newLevel, string zone)
```

Called when health level changes (0=pristine → 4=ruined). If `newLevel == GameConstants.STATE_RUINED` and `zone == ""` (global zone), calls `OnDamageDestroyed(oldLevel)` and `AttemptDestructionBehaviour(...)`.

```c
// scripts/3_game/entities/entityai.c:1047
void OnDamageDestroyed(int oldLevel);   // proto (override en clases concretas)
```

---

## Flujo TransportHit completo ⚠️ (relevante LF_RollingStone)

### Trigger: EOnContact in DayZPlayerImplement

```c
// scripts/4_world/entities/dayzplayerimplement.c:3814-3829
override protected void EOnContact(IEntity other, Contact extra)
{
    if (!IsAlive()) return;
    if (GetParent() == other) return;

    Transport transport = Transport.Cast(other);
    if (transport)
    {
        if (g_Game.IsServer())
        {
            RegisterTransportHit(transport);
        }
    }
}
```

**KEY**: `EOnContact` only reacts to `Transport.Cast(other)`. If the impacting entity is NOT a `Transport` (nor inherits from it), the TransportHit flow is NOT activated at all from the player. For LF_RollingStone as `ItemBase`, player does not automatically detect collision with the stone — it is the stone that must call `target.ProcessDirectDamage(...)` directly from its own `EOnContact`.
(from 1.30 Exp: same Transport-only filter at `exp/scripts/scripts/4_World/Entities/DayZPlayerImplement.c:3958-3973`.)

### RegisterTransportHit — análisis línea a línea

```c
// scripts/3_game/entities/entityai.c:4086-4157
void RegisterTransportHit(Transport transport)
{
    if (!m_TransportHitRegistered)
    {
        m_TransportHitRegistered = true;
        m_TransportHitVelocity = GetVelocity(transport);  // velocidad del Transport
```

**Step 1**: `m_TransportHitRegistered` acts as a single-shot guard per physics frame.  
**Step 2**: Captures Transport velocity (not player's).

#### Rama Car:
```c
        if (Car.CastTo(car, transport))
        {
            if (car.GetSpeedometerAbsolute() > 2)          // minimum threshold: 2 km/h
            {
                damage = m_TransportHitVelocity.Length();   // damage = velocity magnitude (m/s)
                ProcessDirectDamage(DT_CUSTOM, transport, "", "TransportHit", "0 0 0", damage);
            }
            else
                m_TransportHitRegistered = false;            // no damage if moving too slow

            // ragdoll impulse to corpses only
            if (IsDamageDestroyed() && car.GetSpeedometerAbsolute() > 3)
            {
                impulse = 40 * m_TransportHitVelocity;
                impulse[1] = 40 * 1.5;                      // componente Y exagerada
                dBodyApplyImpulse(this, impulse);
            }
        }
```

**Car damage** = `velocidad_transport.Length()` (meters/second) as `damageCoef` passed to `ProcessDirectDamage`. At 30 km/h (~8.3 m/s) the damageCoef is ~8.3.  
**Ragdoll impulse**: only if player is already dead (`IsDamageDestroyed()`). Magnitude scaled ×40 in XZ and ×60 in Y.

#### Rama Boat:
```c
        else if (Boat.CastTo(boat, transport))
        {
            // player standing on boat → ignore (not a real collision)
            if (player && player.PhysicsGetLinkedEntity() == boat)
            {
                m_TransportHitRegistered = false;
                return;
            }
            if (m_TransportHitVelocity.Normalize() > 5)     // umbral: >5 m/s (Normalize devuelve longitud original)
            {
                damage = m_TransportHitVelocity.Length() * 0.5;  // half damage vs Car
                ProcessDirectDamage(DT_CUSTOM, transport, "", "TransportHit", "0 0 0", damage);
            }
            else
                m_TransportHitRegistered = false;
        }
```

#### Generic branch (any other Transport):
```c
        else
        {
            if (m_TransportHitVelocity.Length() > 0.1)       // minimum threshold: 0.1 m/s
            {
                damage = m_TransportHitVelocity.Length();
                ProcessDirectDamage(DT_CUSTOM, transport, "", "TransportHit", "0 0 0", damage);
            }
            else
                m_TransportHitRegistered = false;

            if (IsDamageDestroyed() && m_TransportHitVelocity.Length() > 0.3)
            {
                impulse = 40 * m_TransportHitVelocity;
                impulse[1] = 40 * 1.5;
                dBodyApplyImpulse(this, impulse);
            }
        }
    }
}
```

The generic branch has the lowest threshold (0.1 m/s). Any object inheriting from `Transport` without being `Car` or `Boat` falls here.
(from 1.30 Exp: `RegisterTransportHit` starts at `exp/scripts/scripts/3_Game/Entities/EntityAI.c:4111`. A Motorbike branch sits between Car and Boat at `:4143-4160` — damage like Car when `GetSpeedometerAbsolute() > 2.0`; corpse impulse is `5.0 * velocity` with Y = 5.0, not 40/60. Generic is the last `else`. See section "DayZ 1.30 Exp" below.)

### Reset of m_TransportHitRegistered

The flag resets in `DayZPlayerImplement.EEHitBy` (`dayzplayerimplement.c:1551`):
```c
m_TransportHitRegistered = false;
```
This allows receiving multiple transport hits in different physics frames.

### What ProcessDirectDamage does with "TransportHit"

The function `ProcessDirectDamage(DT_CUSTOM, source, "", "TransportHit", "0 0 0", damage)` invokes the C++ system that:
1. Looks up `CfgAmmo TransportHit` in configuration.
2. Multiplies ammo damage values by `damageCoef` (= velocity in m/s).
3. Applies to zones according to entity DamageSystem.
4. Fires `EEHitBy` on target.

**Ammo "TransportHit" is NOT defined in `scripts/config.cpp`** — it is in base DayZ binary configs (data/). Its base damage + shock values are what C++ scales with velocity.

### Flow in DayZPlayerImplement.EEHitBy post-TransportHit

```c
// dayzplayerimplement.c:1547-1600
override void EEHitBy(..., string ammo, ...)
{
    super.EEHitBy(...);              // → PlayerBase.EEHitBy (bleeding, shock)
    m_TransportHitRegistered = false; // permite nuevo hit

    if (!IsAlive())
    {
        // animar muerte + ragdoll
        EvaluateDeathAnimation(...);
        SendDeathJuncture(...);
    }
    else
    {
        // impact animation:
        // DamageType.CUSTOM con hitAnimation==1 → fullbody anim
        EvaluateDamageHitAnimation(...);
        DayZPlayerSyncJunctures.SendDamageHitEx(...);
    }
}
```

For `DamageType.CUSTOM` + ammo `"TransportHit"`:  
- If `cfgAmmo TransportHit hitAnimation == 1` → `pAnimHitFullbody = true` → full-body hit animation.  
- The live player receives visual/audio impact feedback.

---

## Config dmgZones

Structure in `CfgVehicles`:
```
class MyCar : Transport
{
    class DamageSystem
    {
        class DamageZones
        {
            class Engine
            {
                componentNames[] = {"engine_comp"};
                transferToZonesNames[] = {"Body"};
                transferToZonesCoefs[] = {0.5};
                class Health
                {
                    hitpoints = 500;
                    transferToGlobalCoef = 0.08;
                };
            };
        };
    };
};
```

**Key components of a zone**:
- `componentNames[]`: names of p3d geo-components mapping to this zone.
- `transferToZonesNames[]` / `transferToZonesCoefs[]`: what percentage of damage transfers to other zones.
- `transferToGlobalCoef`: fraction going to global health.
- `fatalInjuryCoef`: if zone reaches 0 health and this coef > 0, object is destroyed [UNVERIFIED in scripts — appears in comments of `actionrepairtent.c:160`].

**GlobalHealth**: special player zone accessed as `GetHealth("GlobalHealth", "Blood")` used by HUD (playerbase.c:5321). Not a zone defined in player config — it is a C++ aggregate.

**Health states** (GameConstants, `scripts/3_game/constants.c:851-855`):
| Constant | Value | Description |
|-----------|-------|-------------|
| `STATE_PRISTINE` | 0 | Pristine |
| `STATE_WORN` | 1 | Worn |
| `STATE_DAMAGED` | 2 | Damaged |
| `STATE_BADLY_DAMAGED` | 3 | Badly damaged |
| `STATE_RUINED` | 4 | Destroyed / 0 HP |

---

## Armadura / Clothing

### GetProtectionLevel (verificado)

```c
// scripts/4_world/entities/itembase.c:4094
float GetProtectionLevel(int type, bool consider_filter = false, int system = 0)
```

This function in `ItemBase` returns **environmental** protection (biological/chemical) of masks and filters, NOT ballistic damage absorption. Types DEF_BIOLOGICAL / DEF_CHEMICAL. Reads `CfgVehicles item Protection { biological; chemical; }`.

### Ballistic absorption (how it actually works)

Clothing damage absorption is a **100% C++ mechanism** configured via `CfgAmmo`. Each ammo has damage multipliers reduced by victim's inventory. In scripts, post-damage events are:

1. `ItemBase.EEHitBy` (the EQUIPPED item receives the callback):
   ```c
   // scripts/4_world/entities/itembase.c:1522-1560
   override void EEHitBy(TotalDamageResult damageResult, ...)
   {
       super.EEHitBy(...);
       if (IsClothing() || IsContainer() || IsItemTent())
       {
           float dmg = damageResult.GetDamage("","Health") * -0.5;
           // randomly damages cargo or attachment (1/4 probability + another rand)
           DamageItemInCargo(dmg);    // o
           DamageItemAttachments(dmg);
       }
   }
   ```
   
   **Equipped clothing degrades** when player takes damage (50% of Health damage as negative HP to cargo/attachment). The actual reduction of damage to player does NOT occur in script — it occurs in C++ before EEHitBy arrives.

2. Ballistic helmets and vests have protection values in `CfgVehicles > armorLevels` (binary C++ data, not in decompiled scripts).

### BallisticHelmet — class wrapper only

```c
// scripts/4_world/entities/itembase/clothing/helmetbase/ballistichelmet_colorbase.c:1
class BallisticHelmet_ColorBase extends HelmetBase
```

There is no relevant script override — its entire protection logic is C++ config.

---

## Player hitzones (DamageZones)

Zone names used in scripts (verified by usage in playerbase.c, dayzplayerimplement.c):

| Zone | Observations |
|------|---------------|
| `"Head"` | Head zone (headshot shot) |
| `"Brain"` | Head sub-zone for headshot kill tracking (`dayzplayerimplement.c:1576`) |
| `"Torso"` | Torso, component used in fullbody animation (`dayzplayerimplement.c:1496`) |
| `"LeftArm"` | Bleeding source up (`playerbase.c:542`) |
| `"RightArm"` | Bleeding source up (`playerbase.c:538`) |
| `"LeftLeg"` | Legs (broken legs check) (`playerbase.c:1293`) |
| `"RightLeg"` | Legs (`playerbase.c:1293`) |
| `"LeftFoot"` | Feet (broken legs check) (`playerbase.c:1293`) |
| `"RightFoot"` | Feet |
| `""` (empty) | Global zone |
| `"GlobalHealth"` | C++ aggregate used only for HUD reading |

Physical zones with their `componentNames` are defined in binary DayZ data (`DayZCharacter` in CfgVehicles), not in decompiled scripts.

---

## Bleeding Sources Manager

```c
// scripts/4_world/entities/manbase/playerbase.c:85-86
ref BleedingSourcesManagerServer m_BleedingManagerServer;
ref BleedingSourcesManagerRemote m_BleedingManagerRemote;
```

**Bleeding flow** (`bleedingsourcesmanagerserver.c:167-198`):
1. In `PlayerBase.EEHitBy`, if there is "Blood" damage and bleeding manager exists: `GetBleedingManagerServer().ProcessHit(dmg, source, component, zone, ammo, modelPos)`.
2. `ProcessHit` reads `CfgAmmo ammo DamageApplied bleedThreshold` (float 0..1).
3. If damage exceeds threshold, creates a `BleedingSource` in corresponding zone.
4. Ammo may have `DamageApplied type` (string) to use `BleedChanceData.CalculateBleedChance`.

**Bleeding sources** have `eBleedingSourceType` type (NORMAL / CONTAMINATED) and are mapped to bones/positions of player skeleton.

---

## Shock and Unconsciousness

```c
// scripts/4_world/classes/shockhandler.c
class ShockHandler
{
    void SetShock(float dealtShock);    // acumula shock
    void CheckValue(bool forceUpdate);  // applies and syncs if exceeds threshold
    float GetCurrentShock();            // shock actual (= player.m_CurrentShock)
}
```

**Flow**:
1. "Shock" damage enters via `ProcessDirectDamage` (C++ applies to player Shock health).
2. In `PlayerBase.EEHitBy`: `m_ShockHandler.CheckValue(true)` — forces synchronization.
3. If `cfgAmmo ammo DamageApplied transferShockToDamage == 1`: Shock is converted into additional Health damage (non-lethal weapons).
4. `ShockHandler.Update()` on each tick; if shock < threshold, activates `ShouldBeUnconscious`.
5. Unconsciousness is managed in DayZPlayerImplement command handler (`m_ShouldBeUnconscious`, `m_IsUnconscious`).

`GiveShock(float shock)` → `AddHealth("","Shock", shock)` (valor negativo drena shock).

---

## Hit Animation Flow (DayZPlayerImplement)

```c
// dayzplayerimplement.c:1469
bool EvaluateDamageHitAnimation(TotalDamageResult, int pDamageType, ...)
{
    switch (pDamageType)
    {
        case DamageType.CLOSE_COMBAT:  // lee cfgAmmo hitAnimation
        case DamageType.FIRE_ARM:      // fullbody if Torso/Head + high damage
        case DamageType.EXPLOSION:     // no special animation
        case DamageType.CUSTOM:
            // hitAnimation==1 → fullbody
            // if ammo != "HeatDamage" and not falling → returns false (no anim)
    }
}
```

For `DamageType.CUSTOM` with ammo `"TransportHit"`:
- If `cfgAmmo TransportHit hitAnimation` returns 1 → fullbody animation.
- If returns 0 or does not exist → no impact animation (sound only).

---

## Patrones

### Script damage to an entity (without custom ammo)
```c
// Most direct method: uses DecreaseHealth bypassing ammo system
target.DecreaseHealth("", "", 50.0); // 50 HP damage to global zone

// Correct for specific zones:
target.DecreaseHealth("LeftLeg", "Health", 25.0);

// To respect full pipeline (triggers EEHitBy, animations, bleeding):
target.ProcessDirectDamage(DamageType.CUSTOM, sourceEntity, "", "TransportHit", "0 0 0", damageCoef);
```

### Area damage (trigger zones)
```c
// AreaDamageComponent (scripts/4_world/classes/areadamage/):
// Defaults to ammo "MeleeDamage" and type CUSTOM
object.ProcessDirectDamage(m_DamageType, m_Parent.GetParentObject(),
    data.Hitzone, m_AmmoName, data.Modelpos, damageCoef);
```

### ExplosionDamage
```c
// scripts/3_game/damagesystem.c:25
DamageSystem.ExplosionDamage(EntityAI source, Object directHitObject,
    string ammoTypeName, vector worldPos, int damageType);
```

Ejemplo de uso (`dayzgame.c:3651`):
```c
DamageSystem.ExplosionDamage(EntityAI.Cast(source), null,
    "Explosion_40mm_Ammo", pos, DamageType.EXPLOSION);
```

When `directHitObject == null`, system applies damage in radius defined in CfgAmmo. Destructibles use `DestructionEffectBase.DealExplosionDamage()` which internally calls this (`destructioneffectbase.c:50-52`).

### DealAbsoluteDmg (script helper)
```c
// scripts/4_world/static/miscgameplayfunctions.c:1597
static void DealAbsoluteDmg(ItemBase item, float dmg)
{
    item.DecreaseHealth(dmg, false);  // false = no auto-delete
}
```

Helper for tools that wear down upon use. Bypasses ammo system.

---

## Gotchas

1. **TransportHit requires Transport inheritance**: player's `EOnContact` only registers hit if impacting entity does `Transport.Cast(other)` successfully. `ItemBase` → `EntityAI` → not Transport. The rock needs to call `target.ProcessDirectDamage(...)` itself from its own `EOnContact`.

2. **m_TransportHitRegistered as frame guard**: flag only permits one hit per "contact episode". Resets in `EEHitBy`, not every frame. If the rock calls `ProcessDirectDamage` directly, there is no guard — can fire multiple times per tick if physical contact oscillates.

3. **damageCoef in ProcessDirectDamage IS the velocity**: In `RegisterTransportHit`, `damage = velocidad.Length()` is passed as `damageCoef`. Actual damage = `CfgAmmo TransportHit base_damage * damageCoef`. At 10 m/s with base damage 1 → 10 HP. Ammo "TransportHit" is not in scripts — it is in binary data.

4. **Ragdoll impulse only post-death**: `dBodyApplyImpulse` in RegisterTransportHit is only called if `IsDamageDestroyed()`. To push LIVE players, the PhysX physical solver system handles physical impulse automatically when there is rigid body contact — there is no explicit script call for that.

5. **GetProtectionLevel is for hazmat only**: Does not measure ballistic protection. Damage absorption values of vests/helmets are purely C++/config.

6. **DamageType.STUN** exists in the enum but has no visible usage in vanilla scripts — [usage unverified in current scripts].

7. **EEHitBy is SERVER ONLY**: Any logic placed in EEHitBy without `IsServer()` guard will execute server-side only anyway. `EEHitByRemote` is the shooter-client equivalent.

8. **`componentName` in ProcessDirectDamage is not the model component name**: it is the DamageZone name (e.g. "Head", "Engine"). Code comment explicitly clarifies it (`object.c:1128`).

9. **Boat has 0.5 damage factor** relative to Car at same speed (up to 1.29: `entityai.c:4129`; from 1.30 Exp: `exp/scripts/scripts/3_Game/Entities/EntityAI.c:4173` after the Motorbike branch). The generic branch applies the same factor as Car.

10. **"Brain" zone exists only in headshot death tracking**: It is not a config DamageZone, but a string shooter sends in `dmgZone` when bullet impacts head component. Verifying if configured as real zone is pending.

---

## What does NOT exist (anti-confabulation)

- **`ProcessIndirectDamage` in EntityAI/Object**: does NOT exist as a script function. Indirect explosion damage is C++ via `DamageSystem.ExplosionDamage`.
- **`DealDamage` as a global script function**: does NOT exist. The correct name is `ProcessDirectDamage` (on Object) or `DealAbsoluteDmg` (helper in MiscGameplayFunctions).
- **"TransportHit" in mod config.cpp**: NOT in DayZ scripts — it is in binary data. To replicate flow, mod must use that ammo name (which already exists in game base) or its own defined in config.cpp.
- **`GetProtectionLevel` for ballistic protection**: Function exists but only covers DEF_BIOLOGICAL and DEF_CHEMICAL. Does NOT absorb weapon damage.
- **Hitzones defined in scripts**: `componentNames` of player DamageZones are in binary CfgVehicles (DayZCharacter), not in decompiled scripts.
- **`BleedingSourcesManagerServer` / `ShockHandler` as classes accessible directly from exterior mods**: They are private `ref` on PlayerBase — accessible only via `GetBleedingManagerServer()` / (ShockHandler has no public getter).
- **`fatalInjuryCoef` in scripts**: Appears referenced in comment of `actionrepairtent.c:156` as "hack", but is not read via direct script — it is read by C++.

---

## Relevance for LF_RollingStone

### Problem S2: "Push + TransportHit damage"

Current path in LFRS S2 uses `ProcessDirectDamage(DT_CUSTOM, source, "", "TransportHit", ...)` from stone's `EOnContact`. This is **correct** in concept:
- `DamageType.CUSTOM` + ammo `"TransportHit"` → C++ looks up that ammo (exists in base DayZ).
- `damageCoef` = velocity → damage proportional to velocity.
- Player's `EEHitBy` fires normally → bleeding + shock + animation.

**Activation problem**: player does not detect the stone as Transport, so `EOnContact` of the stone (LFRS_RollingStone inheriting ItemBase, not Transport) fires, not the player's. From stone's `EOnContact`, target can be player. The code needs:
```c
// In EOnContact of LFRS_RollingStone:
override void EOnContact(IEntity other, Contact extra)
{
    if (!g_Game.IsServer()) return;
    EntityAI target = EntityAI.Cast(other);
    if (target && target.IsAlive())
    {
        float speed = GetVelocity(this).Length(); // velocity of the STONE
        if (speed > 0.5) // minimum threshold
        {
            target.ProcessDirectDamage(DamageType.CUSTOM, this, "",
                "TransportHit", "0 0 0", speed);
        }
    }
}
```

### Problema del impulso (empuje a jugadores vivos)

The ragdoll impulse of `RegisterTransportHit` applies only to corpses. For live players, PhysX solver applies physical impulse automatically if stone has `dBodySetMass` and player has `EnableDynamicSimulation`. But server-side `dBodyApplyImpulse` on the player DOES work for live players too — it is the same mechanism as falling ragdoll.

Para empujar vivos:
```c
if (target.IsAlive() && speed > 1.0)
{
    vector impulse = GetVelocity(this) * 20; // scale according to mass
    impulse[1] = Math.Max(impulse[1], 5.0);  // minimum Y component
    dBodyApplyImpulse(target, impulse);
}
```

### Guard against multiple hits

Without guard equivalent to `m_TransportHitRegistered`, EOnContact can fire multiple times in same physics frame if multiple contact points exist. Implement a bool + reset in EEHitBy or use a time cooldown.

### Hit animation

For player to show hit animation from TransportHit, ammo "TransportHit" in base data has `hitAnimation` configured. If custom ammo is used (e.g. "LFRS_StoneHit"), it must be defined in config.cpp:
```cpp
class CfgAmmo {
    class LFRS_StoneHit {
        hitAnimation = 1;  // fullbody
        // DamageApplied { Health { damage = 1; }; Shock { damage = 0.5; }; Blood { damage = 0.3; }; }
    };
};
```

---

## Fuentes verificadas

| Archivo | Contenido clave |
|---------|-----------------|
| `scripts/3_game/damagesystem.c` | `TotalDamageResult`, `DamageType`, `DamageSystem` (líneas 1-157) |
| `scripts/3_game/entities/object.c` | `ProcessDirectDamage`, `SetHealth`, `GetHealth`, `DecreaseHealth`, `IsDamageDestroyed`, `GetHealthLevel`, `ProcessDirectDamageFlags` (líneas 1-1275) |
| `scripts/3_game/entities/entityai.c` | `EEHitBy`, `EEHitByRemote`, `EEKilled`, `EEDelete`, `EEHealthLevelChanged`, `OnDamageDestroyed`, `RegisterTransportHit` (líneas 934-1157, 4086-4157) |
| `scripts/4_world/entities/dayzplayerimplement.c` | `EOnContact` (3814-3829), `EEHitBy` (1547-1600), `EvaluateDamageHitAnimation` (1469-1543) |
| `scripts/4_world/entities/manbase/playerbase.c` | `EEHitBy` (1224-1347), `BleedingManagerServer`, `ShockHandler`, `GiveShock`, hitzones de piernas |
| `scripts/4_world/entities/itembase.c` | `EEHitBy` ropa (1522-1560), `GetProtectionLevel` (4094-4128) |
| `scripts/4_world/classes/shockhandler.c` | `ShockHandler` completo (1-206) |
| `scripts/4_world/classes/bleedingsources/bleedingsourcesmanagerserver.c` | `ProcessHit` bleeding (167-198) |
| `scripts/4_world/entities/vehicles/carscript.c` | `OnContact`/`CheckContactCache` del coche (1454-1530), `m_dmgContactCoef` (197-198) |
| `scripts/3_game/effects/destructioneffects/destructioneffectbase.c` | `DealExplosionDamage`, `HasExplosionDamage` |
| `scripts/4_world/classes/areadamage/.../areadamagecomponent.c` | `AreaDamageComponent.EvaluateDamageInternal` |
| `scripts/3_game/constants.c:851-855` | `STATE_PRISTINE`..`STATE_RUINED` |
| `scripts/4_world/classes/useractionscomponent/actions/actionconstants.c:146-156` | `UADamageApplied` constantes |
| `scripts/4_world/static/miscgameplayfunctions.c:1597-1599` | `DealAbsoluteDmg` |

## DayZ 1.30 Exp (build 1.30.164014)

Digest H mapped "fall damage from 5 m health / 3 m shock, linear" onto this file via `SKILL.md:59-62`. That SKILL span is Transport-only `EOnContact`, not fall damage. This section **adds** the 1.30 facts.

(hasta 1.29: `HEALTH_HEIGHT_LOW = 5`, `HEALTH_HEIGHT_HIGH = 14`, `SHOCK_HEIGHT_LOW = 3`, `SHOCK_HEIGHT_HIGH = 12`, `BROKENLEGS_HEIGHT_LOW = 5`, `BROKENLEGS_HEIGHT_HIGH = 9`; `HandleFallDamage` used `Math.InverseLerp`. `stable-1.29/scripts/scripts/4_World/Entities/DayZPlayerImplementFallDamage.c:26-32,97`.)

(desde 1.30 Exp: health 2-12 m, shock 0-8 m, broken legs 3-8 m. `CurveExp` = `Pow(Clamp(InverseLerp(low, high, value),0,1), power)` — health/shock power 2.0, broken-legs 2.5. `Randomize` returns 1.0 unchanged if `pValue == 1`. `exp/scripts/scripts/4_World/Entities/DayZPlayerImplementFallDamage.c:26-33,92-140,160-163`.)

```c
// [EXACT] exp/scripts/scripts/3_Game/Entities/EntityAI.c:4143
			else if (Motorbike.CastTo(motorbike, transport))
			{
				float motorbikeSpeed = motorbike.GetSpeedometerAbsolute();
				if (motorbikeSpeed > 2.0)
				{
					damage = m_TransportHitVelocity.Length();
					ProcessDirectDamage(DT_CUSTOM, transport, "", "TransportHit", "0 0 0", damage);
				}
				else
					m_TransportHitRegistered = false;

				// compute impulse and apply only if the body dies
				if (IsDamageDestroyed() && motorbikeSpeed > 3.0)
				{
					impulse = 5.0 * m_TransportHitVelocity;
					impulse[1] = 5.0;
					dBodyApplyImpulse(this, impulse);
				}
			}
```

Vehicle authoring of that Motorbike type is `dayz-vehicles` / `dayz-motorbikes`. Full ragdoll / fall-damage deep-dive: `dayz-1-30-ragdoll-and-fall.md`.

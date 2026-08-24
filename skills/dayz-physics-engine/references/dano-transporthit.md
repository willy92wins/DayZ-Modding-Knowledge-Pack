# Deep-Dive: Sistema de Daño, Hitzones y Armadura — DayZ v1.24

> Investigación: 2026-06-06  
> Fuente de verdad: `<dayz-projects>\scripts\` (vanilla v1.24)  
> Anti-confabulación: toda API citada está verificada con Grep/Read en los archivos indicados.

---

## Resumen ejecutivo

El sistema de daño de DayZ (MDF — Modular Damage Framework) opera principalmente en C++ con una capa de scripting en Enforce Script. El flujo es:  
**fuente de daño → `ProcessDirectDamage` (proto native) → cálculo C++ con CfgAmmo → EEHitBy (callback script server) → efectos secundarios (Shock, Blood, animación, bleeding)**

Para LF_RollingStone el path relevante es **TransportHit**: la piedra debe registrarse como `Transport` (o llamar `RegisterTransportHit` directamente desde `EOnContact`) para que el sistema aplique daño proporcional a la velocidad sin necesidad de ninguna ammo customizada en los configs base del mod.

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

- `GetDamage("", "Health")` → daño total al hitzone global en healthType "Health".
- `GetDamage("Head", "Shock")` → daño de Shock específico a zona "Head".
- `GetHighestDamage("Health")` → mayor valor de daño Health entre todos los hitzones golpeados.

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

Alias usados internamente: `DT_CUSTOM`, `DT_FIRE_ARM`, `DT_CLOSE_COMBAT` corresponden a los valores del enum (verificado por uso en RegisterTransportHit).

### 3. ProcessDirectDamage

```c
// scripts/3_game/entities/object.c:1134
proto native void ProcessDirectDamage(
    int damageType,          // DamageType enum value
    EntityAI source,         // entidad que causa el daño
    string componentName,    // nombre de zona de daño (string vacío = zona global)
    string ammoName,         // nombre de CfgAmmo a aplicar
    vector modelPos,         // posición en model space del impacto
    float damageCoef = 1.0,  // multiplicador aplicado al daño del ammo
    int flags = 0            // ProcessDirectDamageFlags
);
```

**ProcessDirectDamageFlags** (`scripts/3_game/entities/object.c:1-7`):
- `ALL_TRANSFER` — transfiere daño a attachments y global (default).
- `NO_ATTACHMENT_TRANSFER` — no transfiere a attachments.
- `NO_GLOBAL_TRANSFER` — no transfiere al global.
- `NO_TRANSFER` — combinación de ambos `NO_*`.

> No existe `ProcessIndirectDamage` en scripts — el daño indirecto (explosiones en radio) se maneja vía `DamageSystem.ExplosionDamage` (C++). [NO VERIFICADO como función script accesible directamente en EntityAI.]

### 4. DamageSystem (clase estática)

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
    // + métodos helper en script: GetDamageZoneMap, GetDamageZoneFromComponentName, ResetAllZones
}
```

`ResetAllZones` setea Health, Shock y Blood al máximo en todas las zonas del DamageSystem de una entidad (`scripts/3_game/damagesystem.c:139-154`).

### 5. SetHealth / GetHealth / DecreaseHealth / AddHealth

Todos son `proto native` en `Object` (`scripts/3_game/entities/object.c`):

| Función | Firma | Notas |
|---------|-------|-------|
| `GetHealth(zone, type)` | `proto native float` | zone="" → global; type="" → main health |
| `GetHealth01(zone, type)` | `proto native float` | Normalizado 0..1 |
| `GetMaxHealth(zone, type)` | `proto native float` | Máximo configurado |
| `SetHealth(zone, type, value)` | `proto native void` | Setteo directo |
| `AddHealth(zone, type, value)` | `proto native void` | Suma (valor negativo = resta) |
| `DecreaseHealth(zone, type, value)` | `proto native void` | Sólo resta |
| `SetHealthLevel(int level, zone)` | script helper | Usa `GetHealthLevelValue` |
| `SetHealth01(zone, type, coef)` | script helper | `SetHealth(..., max*coef)` |
| `SetHealthMax(zone, type)` | script helper | Llama `SetHealth(max)` |
| `GetHealthLevel(zone)` | `proto native int` | 0=pristine…4=ruined |
| `IsDamageDestroyed()` | `proto native bool` | True = health <= 0 |

Referencia: `scripts/3_game/entities/object.c:977-1121`

Health types conocidos (usados en scripts): `"Health"`, `"Blood"`, `"Shock"`.  
Zona especial `"GlobalHealth"` usada en PlayerBase para HUD (`scripts/4_world/entities/manbase/playerbase.c:5321-5322`).

### 6. EEHitBy — firma completa y parámetros

```c
// scripts/3_game/entities/entityai.c:1117
void EEHitBy(
    TotalDamageResult damageResult,  // resultado del cálculo C++ de daño
    int damageType,                  // DamageType enum
    EntityAI source,                 // quién causó el daño
    int component,                   // índice de componente geométrico golpeado
    string dmgZone,                  // nombre de la damage zone (ej: "Head", "Torso")
    string ammo,                     // nombre del CfgAmmo aplicado
    vector modelPos,                 // posición de impacto en model space
    float speedCoef                  // coef de velocidad (para proyectiles)
)
```

**Llamado**: solo en servidor. Se dispara DESPUÉS de que C++ aplica el daño.  
**Cadena de herencia**:
1. `EntityAI.EEHitBy` — invoca `m_OnHitByInvoker` (`entityai.c:1117-1124`)
2. `ItemBase.EEHitBy` — daño random a cargo/attachments para ropa (`itembase.c:1522-1560`)
3. `PlayerBase.EEHitBy` — bleeding, shock check, broken legs, unconRefill (`playerbase.c:1224-1347`)
4. `DayZPlayerImplement.EEHitBy` — reset `m_TransportHitRegistered`, animaciones de daño/muerte (`dayzplayerimplement.c:1547-1600+`)

### 7. EEHitByRemote

```c
// scripts/3_game/entities/entityai.c:1127
void EEHitByRemote(int damageType, EntityAI source, int component,
    string dmgZone, string ammo, vector modelPos)
```

Llamado únicamente en el **cliente que causó el hit**. Sin `TotalDamageResult`. Usado para feedback local (ej: sound de bloqueo en melee en PlayerBase `playerbase.c:1349-1358`).

### 8. EEKilled

```c
// scripts/3_game/entities/entityai.c:1078
void EEKilled(Object killer)
```

Llamado en servidor cuando la entidad es eliminada. Invoca `m_OnKilledInvoker` y analytics. Si `ReplaceOnDeath()` → programa `DeathUpdate()` via CallLater.

### 9. EEDelete

```c
// scripts/3_game/entities/entityai.c:934
void EEDelete(EntityAI parent)
```

Llamado al eliminar la entidad del mundo (también propaga a inventario).

### 10. EEHealthLevelChanged / OnDamageDestroyed

```c
// scripts/3_game/entities/entityai.c:1027
void EEHealthLevelChanged(int oldLevel, int newLevel, string zone)
```

Se llama cuando el nivel de salud cambia (0=pristine → 4=ruined). Si `newLevel == GameConstants.STATE_RUINED` y `zone == ""` (zona global), llama `OnDamageDestroyed(oldLevel)` y `AttemptDestructionBehaviour(...)`.

```c
// scripts/3_game/entities/entityai.c:1047
void OnDamageDestroyed(int oldLevel);   // proto (override en clases concretas)
```

---

## Flujo TransportHit completo ⚠️ (relevante LF_RollingStone)

### Trigger: EOnContact en DayZPlayerImplement

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

**CLAVE**: `EOnContact` solo reacciona a `Transport.Cast(other)`. Si la entidad que impacta NO es un `Transport` (ni hereda de él), el flujo TransportHit NO se activa en absoluto desde el jugador. Para LF_RollingStone como `ItemBase`, el jugador no detecta la colisión con la piedra automáticamente — es la piedra quien debe llamar `target.ProcessDirectDamage(...)` directamente desde su propio `EOnContact`.

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

**Paso 1**: `m_TransportHitRegistered` actúa como guard de un solo disparo por frame de física.  
**Paso 2**: Captura la velocidad del Transport (no del jugador).

#### Rama Car:
```c
        if (Car.CastTo(car, transport))
        {
            if (car.GetSpeedometerAbsolute() > 2)          // umbral mínimo: 2 km/h
            {
                damage = m_TransportHitVelocity.Length();   // daño = magnitud velocidad (m/s)
                ProcessDirectDamage(DT_CUSTOM, transport, "", "TransportHit", "0 0 0", damage);
            }
            else
                m_TransportHitRegistered = false;            // sin daño si va muy lento

            // impulso ragdoll solo a cadáveres
            if (IsDamageDestroyed() && car.GetSpeedometerAbsolute() > 3)
            {
                impulse = 40 * m_TransportHitVelocity;
                impulse[1] = 40 * 1.5;                      // componente Y exagerada
                dBodyApplyImpulse(this, impulse);
            }
        }
```

**Daño Car** = `velocidad_transport.Length()` (metros/segundo) como `damageCoef` pasado a `ProcessDirectDamage`. A 30 km/h (~8.3 m/s) el damageCoef es ~8.3.  
**Impulso ragdoll**: solo si el jugador ya está muerto (`IsDamageDestroyed()`). Magnitud escalada ×40 en XZ y ×60 en Y.

#### Rama Boat:
```c
        else if (Boat.CastTo(boat, transport))
        {
            // jugador parado sobre el barco → ignorar (no es colisión real)
            if (player && player.PhysicsGetLinkedEntity() == boat)
            {
                m_TransportHitRegistered = false;
                return;
            }
            if (m_TransportHitVelocity.Normalize() > 5)     // umbral: >5 m/s (Normalize devuelve longitud original)
            {
                damage = m_TransportHitVelocity.Length() * 0.5;  // mitad de daño vs Car
                ProcessDirectDamage(DT_CUSTOM, transport, "", "TransportHit", "0 0 0", damage);
            }
            else
                m_TransportHitRegistered = false;
        }
```

#### Rama genérica (cualquier otro Transport):
```c
        else
        {
            if (m_TransportHitVelocity.Length() > 0.1)       // umbral mínimo: 0.1 m/s
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

La rama genérica tiene el umbral más bajo (0.1 m/s). Cualquier objeto que herede de `Transport` sin ser `Car` ni `Boat` cae aquí.

### Reset de m_TransportHitRegistered

El flag se resetea en `DayZPlayerImplement.EEHitBy` (`dayzplayerimplement.c:1551`):
```c
m_TransportHitRegistered = false;
```
Esto permite recibir múltiples hits de transport en diferentes frames de física.

### Qué hace ProcessDirectDamage con "TransportHit"

La función `ProcessDirectDamage(DT_CUSTOM, source, "", "TransportHit", "0 0 0", damage)` invoca el sistema C++ que:
1. Busca `CfgAmmo TransportHit` en la configuración.
2. Multiplica los valores de daño del ammo por `damageCoef` (= velocidad en m/s).
3. Aplica a zonas según el DamageSystem de la entidad.
4. Dispara `EEHitBy` en el objetivo.

**El ammo "TransportHit" NO está definido en `scripts/config.cpp`** — está en los configs binarios de DayZ base (data/). Sus valores de daño base + shock son los que el C++ escala con la velocidad.

### Flujo en DayZPlayerImplement.EEHitBy post-TransportHit

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
        // animación de impacto:
        // DamageType.CUSTOM con hitAnimation==1 → fullbody anim
        EvaluateDamageHitAnimation(...);
        DayZPlayerSyncJunctures.SendDamageHitEx(...);
    }
}
```

Para `DamageType.CUSTOM` + ammo `"TransportHit"`:  
- Si `cfgAmmo TransportHit hitAnimation == 1` → `pAnimHitFullbody = true` → animación de golpe de cuerpo completo.  
- El jugador vivo recibe feedback visual/sonoro del impacto.

---

## Config dmgZones

La estructura en `CfgVehicles`:
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

**Componentes clave de una zone**:
- `componentNames[]`: nombres de geo-components del p3d que mapean a esta zona.
- `transferToZonesNames[]` / `transferToZonesCoefs[]`: qué porcentaje del daño se transfiere a otras zonas.
- `transferToGlobalCoef`: fracción que va al health global.
- `fatalInjuryCoef`: si la zona llega a 0 health y este coef > 0, el objeto es destruido [NO verificado en scripts — aparece en comentarios de `actionrepairtent.c:160`].

**GlobalHealth**: zona especial del jugador accedida como `GetHealth("GlobalHealth", "Blood")` usada por el HUD (playerbase.c:5321). No es una zone definida en config del jugador — es un agregado C++.

**Estados de salud** (GameConstants, `scripts/3_game/constants.c:851-855`):
| Constante | Valor | Descripción |
|-----------|-------|-------------|
| `STATE_PRISTINE` | 0 | Nuevo |
| `STATE_WORN` | 1 | Desgastado |
| `STATE_DAMAGED` | 2 | Dañado |
| `STATE_BADLY_DAMAGED` | 3 | Muy dañado |
| `STATE_RUINED` | 4 | Destruido / 0 HP |

---

## Armadura / Clothing

### GetProtectionLevel (verificado)

```c
// scripts/4_world/entities/itembase.c:4094
float GetProtectionLevel(int type, bool consider_filter = false, int system = 0)
```

Esta función en `ItemBase` devuelve protección **ambiental** (biológica/química) de máscaras y filtros, NO absorción balística de daño. Tipos DEF_BIOLOGICAL / DEF_CHEMICAL. Lee `CfgVehicles item Protection { biological; chemical; }`.

### Absorción balística (cómo funciona realmente)

La absorción de daño de la ropa es un mecanismo **100% en C++** configurado vía `CfgAmmo`. Cada ammo tiene multiplicadores de daño que se reducen por el inventario de la víctima. En scripts, los eventos post-daño son:

1. `ItemBase.EEHitBy` (el item EQUIPADO recibe el callback):
   ```c
   // scripts/4_world/entities/itembase.c:1522-1560
   override void EEHitBy(TotalDamageResult damageResult, ...)
   {
       super.EEHitBy(...);
       if (IsClothing() || IsContainer() || IsItemTent())
       {
           float dmg = damageResult.GetDamage("","Health") * -0.5;
           // daña aleatoriamente cargo o attachment (1/4 probabilidad + otro rand)
           DamageItemInCargo(dmg);    // o
           DamageItemAttachments(dmg);
       }
   }
   ```
   
   La **ropa equipada se degrada** cuando el jugador recibe daño (50% del daño de Health como HP negativos al cargo/attachment). La reducción real del daño al jugador NO ocurre en script — ocurre en C++ antes de que llegue el EEHitBy.

2. Los cascos y chalecos balísticos tienen valores de protección en `CfgVehicles > armorLevels` (data C++ binaria, no en scripts descompilados).

### BallisticHelmet — solo wrapper de clase

```c
// scripts/4_world/entities/itembase/clothing/helmetbase/ballistichelmet_colorbase.c:1
class BallisticHelmet_ColorBase extends HelmetBase
```

No hay override de script relevante — toda su lógica de protección es config C++.

---

## Hitzones del jugador (DamageZones)

Los nombres de zona usados en scripts (verificados por uso en playerbase.c, dayzplayerimplement.c):

| Zona | Observaciones |
|------|---------------|
| `"Head"` | Zona de cabeza (disparo headshot) |
| `"Brain"` | Sub-zona de cabeza para headshot kill tracking (`dayzplayerimplement.c:1576`) |
| `"Torso"` | Torso, componente usado en animación fullbody (`dayzplayerimplement.c:1496`) |
| `"LeftArm"` | Bleeding source up (`playerbase.c:542`) |
| `"RightArm"` | Bleeding source up (`playerbase.c:538`) |
| `"LeftLeg"` | Legs (broken legs check) (`playerbase.c:1293`) |
| `"RightLeg"` | Legs (`playerbase.c:1293`) |
| `"LeftFoot"` | Feet (broken legs check) (`playerbase.c:1293`) |
| `"RightFoot"` | Feet |
| `""` (vacío) | Zona global |
| `"GlobalHealth"` | Agregado C++ usado solo para lectura HUD |

Las zonas físicas con sus `componentNames` están definidas en la data binaria de DayZ (`DayZCharacter` en CfgVehicles), no en los scripts descompilados.

---

## Bleeding Sources Manager

```c
// scripts/4_world/entities/manbase/playerbase.c:85-86
ref BleedingSourcesManagerServer m_BleedingManagerServer;
ref BleedingSourcesManagerRemote m_BleedingManagerRemote;
```

**Flujo de bleeding** (`bleedingsourcesmanagerserver.c:167-198`):
1. En `PlayerBase.EEHitBy`, si hay daño a "Blood" y hay bleeding manager: `GetBleedingManagerServer().ProcessHit(dmg, source, component, zone, ammo, modelPos)`.
2. `ProcessHit` lee `CfgAmmo ammo DamageApplied bleedThreshold` (float 0..1).
3. Si el daño supera el umbral, crea una `BleedingSource` en la zona correspondiente.
4. El ammo puede tener `DamageApplied type` (string) para usar `BleedChanceData.CalculateBleedChance`.

**Bleeding sources** tienen tipo `eBleedingSourceType` (NORMAL / CONTAMINATED) y están mapeadas a huesos/posiciones del skeleton del jugador.

---

## Shock y Unconsciousness

```c
// scripts/4_world/classes/shockhandler.c
class ShockHandler
{
    void SetShock(float dealtShock);    // acumula shock
    void CheckValue(bool forceUpdate);  // aplica y sincroniza si supera threshold
    float GetCurrentShock();            // shock actual (= player.m_CurrentShock)
}
```

**Flujo**:
1. Daño de "Shock" entra por `ProcessDirectDamage` (C++ aplica al health Shock del jugador).
2. En `PlayerBase.EEHitBy`: `m_ShockHandler.CheckValue(true)` — fuerza sincronización.
3. Si `cfgAmmo ammo DamageApplied transferShockToDamage == 1`: se convierte Shock en daño adicional de Health (armas no letales).
4. `ShockHandler.Update()` en cada tick; si shock < threshold, activa `ShouldBeUnconscious`.
5. La inconsciencia se gestiona en el command handler de DayZPlayerImplement (`m_ShouldBeUnconscious`, `m_IsUnconscious`).

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
        case DamageType.FIRE_ARM:      // fullbody si Torso/Head + daño alto
        case DamageType.EXPLOSION:     // sin animación especial
        case DamageType.CUSTOM:
            // hitAnimation==1 → fullbody
            // si ammo != "HeatDamage" y no está cayendo → devuelve false (sin anim)
    }
}
```

Para `DamageType.CUSTOM` con ammo `"TransportHit"`:
- Si `cfgAmmo TransportHit hitAnimation` retorna 1 → animación fullbody.
- Si devuelve 0 o no existe → sin animación de impacto (solo sound).

---

## Patrones

### Daño por script a una entidad (sin ammo custom)
```c
// Método más directo: usa DecreaseHealth bypaseando el sistema de ammo
target.DecreaseHealth("", "", 50.0); // 50 HP de daño a zona global

// Correcto para zonas específicas:
target.DecreaseHealth("LeftLeg", "Health", 25.0);

// Para respetar el pipeline completo (triggers EEHitBy, animations, bleeding):
target.ProcessDirectDamage(DamageType.CUSTOM, sourceEntity, "", "TransportHit", "0 0 0", damageCoef);
```

### Daño de área (trigger zones)
```c
// AreaDamageComponent (scripts/4_world/classes/areadamage/):
// Por defecto usa ammo "MeleeDamage" y type CUSTOM
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

Cuando `directHitObject == null`, el sistema aplica daño en radio definido en CfgAmmo. Los destructibles usan `DestructionEffectBase.DealExplosionDamage()` que internamente llama esto (`destructioneffectbase.c:50-52`).

### DealAbsoluteDmg (script helper)
```c
// scripts/4_world/static/miscgameplayfunctions.c:1597
static void DealAbsoluteDmg(ItemBase item, float dmg)
{
    item.DecreaseHealth(dmg, false);  // false = no auto-delete
}
```

Helper para herramientas que se desgastan al usarse. Bypasea el sistema de ammo.

---

## Gotchas

1. **TransportHit requiere herencia de Transport**: `EOnContact` del jugador solo registra hit si la entidad impactante hace `Transport.Cast(other)` con éxito. `ItemBase` → `EntityAI` → no es Transport. La piedra necesita llamar `target.ProcessDirectDamage(...)` ella misma desde su propio `EOnContact`.

2. **m_TransportHitRegistered como guard de frame**: el flag solo permite un hit por "episodio de contacto". Se resetea en `EEHitBy`, no en cada frame. Si la piedra llama `ProcessDirectDamage` directamente, no hay guard — puede disparar múltiples veces por tick si el contacto físico oscila.

3. **damageCoef en ProcessDirectDamage ES la velocidad**: En `RegisterTransportHit`, `damage = velocidad.Length()` se pasa como `damageCoef`. El daño real = `CfgAmmo TransportHit daño_base * damageCoef`. A 10 m/s con daño base 1 → 10 HP. El ammo "TransportHit" no está en scripts — está en datos binarios.

4. **Impulso ragdoll solo post-muerte**: `dBodyApplyImpulse` en RegisterTransportHit solo se llama si `IsDamageDestroyed()`. Para empujar jugadores VIVOS, el sistema de solver físico de PhysX maneja el impulso automáticamente cuando hay contacto de cuerpos rígidos — no hay llamada de script explícita para eso.

5. **GetProtectionLevel es solo para hazmat**: No mide protección balística. Los valores de absorción de daño de chalecos/cascos son puramente C++/config.

6. **DamageType.STUN** existe en el enum pero no tiene uso visible en scripts vanilla — [uso no verificado en scripts actuales].

7. **EEHitBy es SOLO servidor**: Cualquier lógica puesta en EEHitBy sin guard `IsServer()` se ejecutará solo en servidor de todas formas. `EEHitByRemote` es el equivalente en el cliente-shooter.

8. **`componentName` en ProcessDirectDamage no es el nombre de componente del modelo**: es el nombre de la DamageZone (ej: "Head", "Engine"). El comentario en el código lo aclara explícitamente (`object.c:1128`).

9. **Boat tiene factor 0.5 de daño** respecto a Car a la misma velocidad (`entityai.c:4129`). La rama genérica aplica el mismo factor que Car.

10. **Zona "Brain" solo existe en muerte headshot tracking**: No es una DamageZone de config, sino un string que el shooter envía en `dmgZone` cuando la bala impacta el componente de cabeza. Verificar si está configurada como zona real es pendiente.

---

## Qué NO existe (anti-confabulación)

- **`ProcessIndirectDamage` en EntityAI/Object**: NO existe como función script. El daño indirecto de explosiones es C++ vía `DamageSystem.ExplosionDamage`.
- **`DealDamage` como función global de script**: NO existe. El nombre correcto es `ProcessDirectDamage` (en Object) o `DealAbsoluteDmg` (helper en MiscGameplayFunctions).
- **"TransportHit" en config.cpp del mod**: NO está en los scripts de DayZ — está en datos binarios. Para replicar el flujo, el mod debe usar ese nombre de ammo (que ya existe en la base del juego) o uno propio definido en su config.cpp.
- **`GetProtectionLevel` para protección balística**: La función existe pero solo cubre DEF_BIOLOGICAL y DEF_CHEMICAL. NO absorbe daño de armas.
- **Hitzones definidas en scripts**: Los `componentNames` de las DamageZones del jugador están en CfgVehicles binario (DayZCharacter), no en los scripts descompilados.
- **`BleedingSourcesManagerServer` / `ShockHandler` como clases accesibles directamente desde mods exteriores**: Son `ref` privados en PlayerBase — accesibles solo via `GetBleedingManagerServer()` / (ShockHandler no tiene getter público).
- **`fatalInjuryCoef` en scripts**: Aparece referenciado en comentario de `actionrepairtent.c:156` como "hack", pero no se lee vía script directo — es leído por C++.

---

## Relevancia para LF_RollingStone

### Problema S2: "Empujar + daño TransportHit"

El path actual en LFRS S2 usa `ProcessDirectDamage(DT_CUSTOM, source, "", "TransportHit", ...)` desde el `EOnContact` de la piedra. Esto es **correcto** en concepto:
- `DamageType.CUSTOM` + ammo `"TransportHit"` → C++ busca ese ammo (existe en DayZ base).
- `damageCoef` = velocidad → daño proporcional a velocidad.
- `EEHitBy` del jugador se dispara normalmente → bleeding + shock + animación.

**Problema de activación**: el jugador no detecta la piedra como Transport, entonces `EOnContact` de la piedra (LFRS_RollingStone que hereda ItemBase, no Transport) se dispara, no el del jugador. Desde `EOnContact` de la piedra, el target puede ser el jugador. El código necesita:
```c
// En EOnContact de LFRS_RollingStone:
override void EOnContact(IEntity other, Contact extra)
{
    if (!g_Game.IsServer()) return;
    EntityAI target = EntityAI.Cast(other);
    if (target && target.IsAlive())
    {
        float speed = GetVelocity(this).Length(); // velocidad de la PIEDRA
        if (speed > 0.5) // umbral mínimo
        {
            target.ProcessDirectDamage(DamageType.CUSTOM, this, "",
                "TransportHit", "0 0 0", speed);
        }
    }
}
```

### Problema del impulso (empuje a jugadores vivos)

El impulso ragdoll de `RegisterTransportHit` solo aplica a cadáveres. Para vivos, el solver PhysX aplica impulso físico automáticamente si la piedra tiene `dBodySetMass` y el jugador tiene `EnableDynamicSimulation`. Pero `dBodyApplyImpulse` en el servidor sobre el jugador SÍ funciona para vivos también — es el mismo mecanismo que el ragdoll de caída.

Para empujar vivos:
```c
if (target.IsAlive() && speed > 1.0)
{
    vector impulse = GetVelocity(this) * 20; // escalar según masa
    impulse[1] = Math.Max(impulse[1], 5.0);  // componente Y mínima
    dBodyApplyImpulse(target, impulse);
}
```

### Guard contra hits múltiples

Sin guard equivalente a `m_TransportHitRegistered`, el EOnContact puede dispararse múltiples veces en el mismo frame de física si hay múltiples puntos de contacto. Implementar un bool + reset en EEHitBy o usar un cooldown de tiempo.

### Animación de hit

Para que el jugador muestre animación de golpe por TransportHit, el ammo "TransportHit" en la data base tiene `hitAnimation` configurado. Si se usa un ammo custom (ej: "LFRS_StoneHit"), se debe definir en config.cpp:
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

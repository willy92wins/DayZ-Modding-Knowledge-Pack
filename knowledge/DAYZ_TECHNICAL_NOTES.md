# Hechos técnicos — referencia DayZ

Notas técnicas verificadas por experiencia o source. Aplican a trabajo con
modelos `.p3d`, debris, configs, persistencia, integraciones LBmaster, loot.

Este archivo se extrajo de CLAUDE.md (2026-05-09) para mantener el archivo
principal por debajo del sweet spot. Cargar on-demand cuando una tarea toque
geometría / config / runtime DayZ.

## py3d (KoffeinFlummi MLOD reader)
- Constructor: `P3D(file)` — NO `P3D.read(file)`.
- `lod.resolution` → float. Tabla en sección "LODs DayZ".
- `lod.points[i].coords` → tupla `(x, y, z)`.
- `face.vertices[i].point.coords` → tupla `(x, y, z)`.
- `face.vertices[i].normal` → **tupla directa `(x, y, z)`**, NO `.coords`. Confundirlas resulta en fallback silencioso.
- `lod.facenormals` → **pool global de tuplas `(x, y, z)` indexado por `vertex.normal_index`**, NO un array per-face. Tamaño = `num_facenormals` del header MLOD, **independiente** de `len(lod.faces)`. Cada `Vertex` tiene `point_index` (→ pool `lod.points`) y `normal_index` (→ pool `lod.facenormals`). `face.vertices[i].normal` es property que resuelve `all_normals[normal_index]`.
- `face.vertices[i].uv` → tupla `(u, v)`.
- `lod.selections['Name'].points` / `.faces` → subconjuntos por nombre.

## LODs DayZ — resoluciones canónicas

| LOD | resolution | Notas |
|---|---|---|
| Visual | `0.0`, `1.0`, `2.0`, ... | LOD0 = base |
| ShadowVolume | `10000`, `11000` | |
| Geometry | `1e13` | colisión física |
| Memory | `1e15` | named points |
| LandContact | `2e15` | |
| ViewGeometry | **`6e15`** | raycast cursor/actions; sin esto fallan acciones |
| FireGeometry | **`7e15`** | balas/proyectiles; sin esto las balas atraviesan |

⚠️ **Bug conocido en `dayz-p3d-audit/scripts/audit_p3d.py`:** `classify_lod()` usa valores Arma 3 antiguos (FireGeo=`3e13`, ViewGeo=`7e13`), que NO son los valores DayZ modernos. Ver Pendientes en CLAUDE.md.

Verificación: `DZ/gear/camping/wooden_case.p3d` debinarizado → 9 LODs con Visual(1..4) + Geometry(`1e13`) + Memory(`1e15`) + LandContact(`2e15`) + ViewGeo(`6e15`) + FireGeo(`7e15`).

## Winding & normales (handedness Blender→DayZ) — TEMA CRÍTICO
Es la causa #1 de fallos al portar modelos de Blender a DayZ. Síntomas sutiles, diagnósticos engañosos. Ya nos lo hemos comido en WallLamp y Crate_Wooden — leer entera antes de tocar cualquier modelo importado.

### Síntomas in-game
- **La textura solo se ve desde DENTRO del objeto.** El objeto parece "vacío" desde fuera (caso clásico, Visual LOD mal).
- **Las balas atraviesan el objeto** (winding mal en FireGeo + Geometry → raycast desde fuera no encuentra superficie sólida).
- **Las acciones no aparecen** o el cursor no detecta el objeto (winding mal en ViewGeo o Geometry).
- **El jugador puede atravesar el objeto** (Geometry o GeoPhys mal).
- A veces solo UNO de estos síntomas: el winding puede estar bien en Visual y mal en Geometry, o viceversa. **Verificar cada LOD por separado.**

### Causa raíz
Blender usa Z-up, DayZ usa Y-up. Al exportar, el .p3d gira (Z→Y), cambiando la handedness del sistema de coordenadas. El **vertex order** que era counter-clockwise en Blender (visto desde fuera) queda effectivamente clockwise en DayZ — el motor lo trata como "interior" de la superficie y la cara no se renderiza/raycastea desde fuera.

Esto NO afecta a las normales del pool `lod.facenormals` — siguen apuntando hacia donde apuntaban en Blender. Por eso el modelo *parece* correcto al inspeccionar normales pero no funciona en juego: **lo que importa al motor de raycast/render es el winding, no la normal declarada**.

### Fix canónico
```python
import py3d
with open(p3d_path, 'rb') as f:
    p = py3d.P3D(f)
for lod in p.lods:                   # TODOS los LODs, no solo Visual
    for face in lod.faces:
        face.vertices.reverse()       # invierte el orden de los corners in-place
with open(p3d_path, 'wb') as f:
    p.write(f)
```

Reglas:
- Aplica a **todos** los LODs: Visual + ShadowVolume + Geometry + LandContact + ViewGeometry + FireGeometry. Dejar uno fuera produce inconsistencias entre render y colisión.
- `reverse()` opera in-place sobre la lista de Vertex objects. **NO toca el pool `lod.facenormals`** (es global, indexado por `vertex.normal_index`) ni los `normal_index` — las normales declaradas siguen apuntando al mismo sitio del pool, lo que es correcto.
- **NO uses el viejo "swap `vertices[1]` y `vertices[2]`"** — funciona solo para tris. Quads y polys mayores requieren `reverse()`.
- **Aplicación UNIFORME es esencial.** Si saltas algunas faces, el modelo queda con winding mixto, que es PEOR que el modelo flipped al revés: algunas zonas se ven desde fuera, otras desde dentro, render impredecible. **Verificar post-fix con Check B (topología edge-pair).**

Script: `outputs/flip_winding.py`.

### Verificación y trampas — ver skill `dayz-p3d-audit`

Para verificar winding (Check A diagnóstico, Check B topología edge-pair, Check C
vs vanilla), trampas conocidas (idempotencia de `flip_winding.py`, Crate_Wooden
mixed winding tolerado, `face.flags |= 0x20000` solo elude en Visual LOD,
interacción con `make_double_sided.py`), y checklist completo al importar un
modelo nuevo de Blender → ver `dayz-p3d-audit/SKILL.md` sección
**WINDING DIAGNOSTICS — Deep Methodology** (movido 2026-05-04 desde aquí).

## Debris spawn offsets — desde selection centroids del crate, NO bbox del debris
**Regla:** offset de spawn de cada debris desde el **centroide de la selección con ese nombre dentro del Visual LOD0 del crate principal**. NO usar el bbox del .p3d individual del debris.

**Razón:** ambos bboxes pueden diferir varios cm porque Object Builder recentra al exportar/importar el .p3d individual, mientras que la selección nombrada en el crate intacto mantiene la pose original. Usar el bbox individual produce offsets incrustados o desalineados en altura.

```python
with open(crate_main_p3d, 'rb') as f:
    model = py3d.P3D(f)
visual_lod = next(l for l in model.lods if l.resolution == 0.0)
sel = visual_lod.selections['plank_front']  # selection por nombre, no bbox
pts = [p.coords for p in sel.points]
centroid = (sum(p[0] for p in pts)/len(pts),
            sum(p[1] for p in pts)/len(pts),
            sum(p[2] for p in pts)/len(pts))
# centroid = offset de spawn del debris correspondiente
```

## Single-sided vs double-sided faces
.p3d exportados de Blender son single-sided por defecto (0 back-twin pairs, `face.flags = 0x0`). Es lo correcto para piezas solo visibles por fuera (laterales, suelo, corners de un crate cerrado).

**Excepción:** planks de los **extremos** (Front/Back) en un crate abierto se ven desde fuera (caja intacta) Y desde dentro (huecos entre planks una vez rota o cuando spawnean separados) → requieren back-twin.

`outputs/make_double_sided.py` duplica cada face del Visual LOD con vertex order invertido y normal negada, y extiende las selections para incluir los twins. NO toca Geo/Shadow/Memory (colisión y sombra siguen single-sided, como deben).

**Alternativa más barata (no probada):** poner `face.flags |= 0x20000` (bit `NoBackfaceCulling` del MLOD format) en cada face del Visual LOD. Mantiene polycount original. Ver Pendientes en CLAUDE.md.

## Container_Base custom — requisitos no obvios
Heredar de `Container_Base` NO basta con declarar `scope = 2; model = ...;`. El objeto resultante no recibe daño ni balas si el config.cpp carece de:

1. `class Cargo { itemsCargoSize; openable; allowOwnedCargoManipulation; }` — algunos builds no inicializan el objeto como contenedor sin esto.
2. `class GlobalArmor { class FragGrenade { ... } }` — sin esto el engine puede no registrar impactos de proyectiles.
3. `healthLevels[] = { {1.0, {"rvmat"}}, ... }` — formato moderno. **NO** usar `healthLevelValues[]` (legacy, rompe DamageSystem silenciosamente).

**Cajas cerradas sin Cargo del jugador (caso Crate_Wooden):** si el loot se spawnea world-space por `EEKilled` y no usa Cargo, poner `itemsCargoSize[] = {0, 0}`. Mantener `class Cargo` vacía porque Container_Base la necesita para inicializar. Si `{0,0}` da warning RPT, plan B: heredar de `Inventory_Base` y eliminar `class Cargo` entera. Ver Pendientes en CLAUDE.md.

Referencia: vanilla `WoodenCrate` en `DZ/gear/camping/config.cpp` líneas 10074–10210.

## Física dinámica de items (`ThrowPhysically`)
**Síntoma:** items spawneados con `CreateObjectEx(name, pos, ECE_CREATEPHYSICS|ECE_UPDATEPATHGRAPH)` + `dBodyApplyImpulse(ent, impulse)` aparecen **frozen en el aire** sin caer.

**Causa:** para items con `simulation = "inventoryItem"` + `physLayer = "item"`, `ECE_CREATEPHYSICS` crea la **shape de colisión** pero deja el rigid body **static/kinematic**. `dBodyApplyImpulse` sobre un body no-dinámico se descarta en silencio. Hay que activar dinámica + gravity + lifetime.

**Fix correcto — `ThrowPhysically`** (firma en `P:\scripts\3_game\entities\inventoryitem.c:26`):
```
proto native void ThrowPhysically(DayZPlayer player, vector force, bool collideWithCharacters = true);
```
Internamente hace `CreateDynamicPhysics(ITEM_LARGE)` + `SetDynamicPhysicsLifeTime(...)` + aplica force como impulso. Es el patrón vanilla (`miscgameplayfunctions.c:1188/1204/1212`, `plugindeveloper.c`).

```enforce
ItemBase debrisEnt = ItemBase.Cast(spawned);
debrisEnt.ThrowPhysically(null, impulse, false);
```

**APIs relacionadas verificadas en `P:\scripts`:**
- `1_core\proto\enphysics.c:141` → `proto void dBodyApplyImpulse(notnull IEntity body, vector impulse);` — válida pero SOLO sobre body ya dinámico.
- `1_core\proto\enphysics.c:64-69` → `dBodyActive`, `dBodyDynamic`, `dBodyIsDynamic`, `dBodyEnableGravity`.
- `3_game\entities\object.c:462-464` → `CreateDynamicPhysics(int interactionLayers)`, `EnableDynamicCCD(bool)`, `SetDynamicPhysicsLifeTime(float)` — miembros de `Object`, usables manualmente.
- `3_game\global\dayzphysics.c:1-29` → enum `PhxInteractionLayers { NOCOLLISION, DEFAULT, BUILDING, CHARACTER, VEHICLE, DYNAMICITEM, DYNAMICITEM_NOCHAR, ROADWAY, ... }`. Vanilla usa `DYNAMICITEM` para items inventariables.
- `4_world\entities\itembase.c:4530` → `StopItemDynamicPhysics()` ⇒ `SetDynamicPhysicsLifeTime(0.01)`. Confirma que el lifetime mantiene viva la dinámica.

**Patrón manual** (control fino sin `ThrowPhysically`):
```enforce
obj.CreateDynamicPhysics(PhxInteractionLayers.DYNAMICITEM);
obj.EnableDynamicCCD(true);
obj.SetDynamicPhysicsLifeTime(20.0);  // sin esto el motor lo duerme
dBodyEnableGravity(obj, true);
dBodyApplyImpulse(obj, impulse);
```

## Quantity en magazines (`ServerSetAmmoCount`)
**Bug silencioso:** `ItemBase.SetQuantity(N)` sobre un Magazine (mags reales `Mag_*` y ammo piles `Ammo_*` — ambos extienden `Magazine_Base`) NO rellena el ammo count interno. Admin pide `quantity=30` y el mag spawnea con 0 balas.

**Fix DWIM** para "quantity" en presets de loot:
```enforce
if (node.quantity >= 0.0)
{
    Magazine mag = Magazine.Cast(ent);
    if (mag)
    {
        mag.ServerSetAmmoCount(node.quantity);
    }
    else
    {
        ItemBase ib = ItemBase.Cast(ent);
        if (ib)
            ib.SetQuantity(node.quantity);
    }
}
```
Cast a `Magazine` primero (cubre mags + ammo piles), fallback a `ItemBase.SetQuantity` para stackables normales (Rag, PaperSheet, etc.).

**Firmas verificadas:**
- `4_world\entities\itembase\magazine\magazine.c:70` → `proto native void ServerSetAmmoCount(int ammoCount);`
- `3_game\entities\entityai.c:2242` → `bool SetQuantity(float value, bool destroy_config = true, bool destroy_forced = false, bool allow_client = false, bool clamp_to_stack_max = true);`

Vanilla usa `ServerSetAmmoCount` en 20+ sitios (`weapon_base.c:805`, `cfgplayerspawnhandler.c:330,340`, `recipebase.c:314,420`, etc.). Implementación viva: `Crate_Wooden.c::ApplyNodeAttributes`.

## Schema migration JSON — patrón ExpansionSettingBase
**Problema:** evoluciono el schema (añado campos), admin con JSON viejo no tiene esos campos. Si el constructor inyecta "ejemplos didácticos", al hacer Load esos ejemplos quedan intactos → admin ve loot apareciendo de la nada, sin saber por qué.

**Patrón canónico** (referencia: `salutesh/DayZ-Expansion-Scripts/ExpansionGarageSettings.c::OnLoad`):

1. `static const int SCHEMA_VERSION = N;` en la clase de config. Bumpear N al añadir campos.
2. **Constructor minimal:** solo defaults numéricos/escalares + `new array<T>` (vacíos para que el serializer no reciba null). `version = 0` como sentinel "no cargado aún".
3. **Método `Defaults()` separado:** puebla todos los campos con factory + ejemplos. Idempotente (`Clear()` antes de `Insert()` en arrays).
4. **`LoadOrCreate` pattern:**
   - JSON no existe → `cfg.Defaults(); SaveToDisk(cfg);`
   - JSON existe + load OK + `cfg.version < SCHEMA_VERSION` → `fresh = new Cfg; fresh.Defaults();`. Copiar campos NUEVOS por migración incremental (`if (cfg.version < 2) { ... }`, `if (cfg.version < 3) { ... }`). Luego `cfg.version = SCHEMA_VERSION; SaveToDisk(cfg);`.
   - JSON existe + load FALLA → `cfg.Defaults()` SOLO en memoria, NO sobreescribir fichero (admin puede estar editándolo con typo).

**Resultado:** server con JSON viejo hace auto-upgrade transparente → RPT muestra `Migrating CrateConfig v1 -> v3` + JSON se re-graba con campos nuevos + ejemplos didácticos. Cero sorpresas silenciosas.

Implementación viva: `Crate/scripts/4_World/Crate_Config.c::LoadOrCreate` + `Defaults` (historial de versiones ahí mismo).

## LBmaster preset integration — `#ifdef` opcional
**Contrato:** dependencia opcional en compile-time. NO añadir `LBmaster_Core` a `requiredAddons` del CfgPatches. Envolver TODO el código LB en `#ifdef LBmaster_Core`. Así el mod compila/corre en servers sin LBmaster (con fallback interno) y usa LB cuando está cargado.

**APIs verificadas en `LBmaster_Core/scripts/`:**
- `LB_PresetBase.c:92` → `static void SpawnPresets(PlayerBase player, array<LB_PresetBase> presets, EntityAI parent, vector altPos = vector.Zero, float radius = 0.0)`
- `LB_PresetBase.c:138` → `void SpawnPreset(PlayerBase player, EntityAI parent, vector altPos = vector.Zero, float radius = 0.0)`
- `LB_PresetLoader.c:146` → `LB_PresetBase GetPreset(string name)` — null si no encuentra.
- `LB_PresetLoader.c:189` → `array<LB_PresetBase> FindPresets(TStringArray arr)` — vacío si nada matchea.
- `LBConfigLoader.c:6` → `static ref T1 Get;` — **propiedad estática, sin paréntesis**. Acceso: `LB_PresetLoader.Get.GetPreset(...)`, NO `LB_PresetLoader.Get().GetPreset(...)`.

**Semántica crítica:**
- `SpawnPreset` (instance, 1 preset) → entra directo al loop `minSpawnTries/maxSpawnTries` e **ignora el root chance del preset** ⇒ spawn garantizado.
- `SpawnPresets` (static, N presets) → **aplica chance logic** (global weighted + individual) antes de spawnear. Con `individualChance = false` y chances < 1.0 puede no spawnear nada.

Precedente de uso de `#ifdef LBmaster_Core`: `LFPowerGrid/scripts/4_World/LFPG_NetworkManager.c:370`, `LFPG_BalanceProvider_LBmaster.c:8`. Implementación viva: `Crate_Wooden.c::TrySpawnLBPresets`.

## Cascada de loot resolution — patrón multi-tier
Para mods con múltiples fuentes de loot opcionales, orden recomendado en el dispatcher:

1. **Tier 1 (más complejo):** sistema externo (LBmaster presets). Condicionado por toggle admin (`useLBPresets`). Si framework no cargado o preset no resuelve → aviso RPT + caída a Tier 2.
2. **Tier 2 (medio):** tabla nativa del mod con attachments anidados recursivos. Si `lootTable.Count() == 0` → caída silenciosa a Tier 3.
3. **Tier 3 (simple):** lista plana de classnames. Legacy. Vacío → caída a Tier 4.
4. **Tier 4:** no-op + RPT `All loot tiers empty -> crate broke without spawning any loot` (admin nota que su config está vacía).

**Ventaja:** admin sube/baja en la escalera según lo que tenga en su server. Mods nuevos no rompen JSONs viejos (fallback natural). Admin sin framework externo sigue teniendo loot via Tier 2 o 3.

Implementación viva: `Crate_Wooden.c::DispatchLootSpawn`.

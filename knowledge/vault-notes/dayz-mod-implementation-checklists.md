# DayZ Mod — Implementation Checklists (Claude + Codex)

> Conocimiento técnico transversal del modding DayZ. Legible por Claude (skill `dayz-mod-workflow`) y por Codex (debe leer este archivo antes de implementar features de DayZ).
>
> Proceso (cuándo y cómo) → [`00_System/workflow.md`](../00_System/workflow.md) + skill `dayz-mod-workflow`.
> Este archivo es **qué** verificar, no **cuándo** verificar.
>
> Mantenimiento: añadir entradas con `path:line` o fuente concreta (R2 cite-then-verify). Si una entrada se observa fallar en producción, anotarla en `bug-ledger.md` del proyecto + actualizar el catálogo al final.

---

## 1. Client/server data map (obligatorio antes de cualquier feature con estado/acción/UI)

Rellena la tabla por feature antes de escribir código:

```
| Dato                | CLIENT? | SERVER? | Bridge mechanism     |
|---------------------|---------|---------|----------------------|
| (rellenar)          |         |         | SyncVar / RPC / Cache|
```

Reglas duras (verificadas contra `vanilla EntityAI.c`):

- **Tipos de SyncVar**: Bool, BoolSignal, Int, Float, Object. **No** strings. `RegisterNetSyncVariableString` no existe.
- **Alineamiento de bitstream**: cliente y servidor registran los mismos SyncVars en el mismo orden. El mismatch corrompe TODOS los datos sincronizados sin error visible.
- **`ActionCondition()`** corre **solo en cliente** para mostrar la acción en el menú. Todo dato accedido ahí debe estar disponible en cliente.
- **Métodos con sufijo `Server`** (`OnStartServer`, `OnFinishServer`, `OnUpdateServer`) corren en servidor. Datos server-only aquí.
- El servidor **no** re-ejecuta `Can()` ni `ActionCondition()`. Confía en la selección del cliente y valida vía `SetupAction()`.
- Si necesitas un string en cliente → ScriptRPC que rellena cache local, o codifica como hash int vía SyncVar.
- **Si dudas si un dato es client-available → trátalo como no disponible.**

---

## 2. Checklists por tipo de archivo

### 2.1 config.cpp

- [ ] `CfgPatches` nombre de clase = nombre de la carpeta del addon.
- [ ] `requiredAddons` usa nombres de clases de CfgPatches:
  - CommunityFramework: `"JM_CF_Scripts"` (no `"CommunityFramework"`).
  - DabsFramework: `"DF_Scripts"` o `"DF_GUI"` (no `"DabsFramework"`).
  - Vanilla: `"DZ_Data"`, `"DZ_Scripts"`.
- [ ] `hiddenSelections[]` cuenta = `hiddenSelectionsTextures[]` cuenta.
- [ ] `scope = 2` spawnable, `1` referencia, `0` abstracto.
- [ ] La herencia: padre existe o está en `requiredAddons`.
- [ ] **Override de clase anidada de vehículo (`class SimulationModule: SimulationModule`, `class Axles: Axles`, `class Front: Front`, `class Rear: Rear`, `class DamageZones: DamageZones`, etc.)**: la base referenciada con `: X` DEBE estar declarada como forward-ref `class X;` en el root de ESTE `CfgVehicles`. Cada `config.cpp` se parsea con su propio scope — un mod hijo NO hereda las forward-refs del config del PBO padre. Sin ellas → CfgConvert da `Undefined base class 'X'` (compile-blocking, el mod no carga). Las clases anidadas SIN `: parent` (Engine, Steering, Gearbox, Differential, Suspension…) mergean implícito y NO necesitan forward-ref. Ver E24.
- [ ] **`ProcessDirectDamage` primer argumento = `DamageType.FIRE_ARM`** (enum, `damagesystem.c`), NO `DT_FIRE_ARM` (alias inexistente en vanilla actual, solo en un comentario). Ver E25.
- [ ] `inventorySlot` = string para uno, `inventorySlot[]` = array para varios. (Bug T148506: mezclar formas rompe attachment silently.)
- [ ] `ghostIcon`: `"set:setname image:imagename"`. Verifica que el imageset existe.
- [ ] `imageSets` dentro de `CfgMods > Mod > defs > imageSets` — **no** en root ni en CfgSlots.

### 2.2 Enforce Script — general

Las reglas completas viven en la skill `enforce-script-reference`. Restricciones verificadas clave:

- [ ] **Sin operadores ternarios** (`? :` no compila).
- [ ] `ref` **solo** en member fields, nunca en locals/params/returns/typedefs.
- [ ] **Nunca** uses la keyword `delete` (segfault si quedan referencias).
- [ ] `foreach` funciona, pero **nunca** directamente sobre el return de un getter (NPE en la 2ª iteración). Asigna a local primero.
- [ ] Prefijo `m_` en todos los member fields.
- [ ] Sin `new` dentro de ticks periódicos → usa `m_` field + `.Clear()`.
- [ ] Expresiones complejas en asignaciones de array pueden segfault → romper en local var primero.

### 2.3 Networking

- [ ] `RegisterNetSyncVariable*` se llama en el **constructor**, no en `Init`.
- [ ] Tipos: Bool, Int, Float, Object. **No** strings.
- [ ] Mismas vars, mismo orden en cliente y servidor (bitstream alignment).
- [ ] Override de `OnVariablesSynchronized` para cada SyncVar registrada.
- [ ] Guard servidor: `GetGame().IsDedicatedServer()` (no `IsServer()` — devuelve true en cliente durante load).
- [ ] Guard cliente: `!GetGame().IsDedicatedServer()` (no `IsClient()` — devuelve false en cliente durante load).
- [ ] `SetSynchDirty()` tras cada escritura de SyncVar en servidor.

### 2.4 UI / Layout

- [ ] La ruta del `.layout` empareja con `$PBOPREFIX$`.
- [ ] Nombres de widget = referencias en script, exactos (case sensitive).
- [ ] Dabs MVC: widget names = ViewController property names, exactos.
- [ ] `ScriptViewMenu` ghost-menu guard: `if (layoutRoot)` antes de operar.
- [ ] Input lock: `ChangeGameFocus(1)` al abrir, reverso al cerrar.
- [ ] Cursor: `ShowUICursor(true)` al abrir, reverso al cerrar.
- [ ] Cleanup en destructor / `OnHide`: quita handlers, anula refs.

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

- [ ] `CreateConditionComponents` overrideado con CCT/CCI correcto.
- [ ] `ActionCondition` usa solo datos client-available (ver §1).
- [ ] Target type: `GetType()` para exacto, `IsKindOf()` para herencia.
- [ ] **Items no recogibles**: usa `RemoveAction(ActionTakeItem)` + `RemoveAction(ActionTakeItemToHands)`. **Mantén** `IsTakeable=true`. (`IsTakeable=false` esconde el item de la vicinity panel pero **no** bloquea custom actions.)
- [ ] Overrides de `CanPutInCargo()` / `CanPutIntoHands()` si el item no debe almacenarse.
- [ ] La clave de stringtable existe, o usa string hardcoded para testing.

### 2.6 .rvmat materials

- [ ] Stage2 DT: `color(0.5,0.5,0.5,0.5,DT)` — alpha 0.5, no 1.0.
- [ ] Stage4 AS: `color(0,1,1,1)` — **sin** sufijo "AS", R=0.
- [ ] Stage6 fresnel: copia de un vanilla ref del mismo tipo de shader.
- [ ] Damage / destruct: usa vanilla `generic_damage_mc.paa` / `generic_destruct_mc.paa`.
- [ ] `forcedDiffuse` alpha: `0,0,0,1`, no `0,0,0,0`.
- [ ] **Compara cada stage** contra un .rvmat vanilla que funciona del mismo shader.

### 2.7 Persistence (OnStoreSave / OnStoreLoad)

- [ ] El campo `version` lo gestiona el **engine** — no lo serialices manualmente. `OnStoreLoad(ctx, version)` recibe `version` como parámetro.
- [ ] Save y Load en **exactamente** el mismo orden (binario secuencial).
- [ ] Cada `ctx.Write()` tiene su `ctx.Read()` en la misma posición.
- [ ] `super.OnStoreSave(ctx)` / `super.OnStoreLoad(ctx, version)` **primero**.
- [ ] Comprueba el return de cada `ctx.Read()` → `return false` en fallo.
- [ ] `AfterStoreLoad` para post-load init (no en `OnStoreLoad`).
- [ ] Test: borra los archivos de persistencia → verifica arranque limpio.

### 2.8 Edge cases — patrones lógicos

Aplica para cualquier feature con colecciones, estado o lifecycle:

- [ ] **Colección vacía (count=0)**: el cuerpo del loop no se ejecuta. Notifica **antes** de limpiar, no después.
- [ ] **Estado null/vacío**: sin grupo, sin bandera, sin items en slots. Guard nullcheck antes de cada acceso.
- [ ] **Transiciones de estado**: `active→abandoned`, `raised→lowered`, `powered→unpowered`. La cache se actualiza en **cada** transición y la UI refleja el nuevo estado.
- [ ] **Cache vs lifecycle de entidad**: si la entidad se destruye, ¿la cache se limpia?
- [ ] **Reconexión de jugador**: el cache cliente se pierde al desconectar. ¿Cómo se reconstruye? (RPC al conectar, re-sync de SyncVar.)
- [ ] **Operaciones concurrentes**: dos jugadores actuando sobre la misma entidad simultáneamente.

### 2.9 Refactor — state coherence (obligatorio al consolidar lógica alrededor de side-effects)

Un refactor que mueve un guard / validación / rate-limit a través de una llamada engine irreversible (`super.OnStartServer`, `super.OnExecuteServer`, `ObjectDelete`, RPC send, `SetSynchDirty`, file write) puede introducir **orphan state**: el engine hizo medio trabajo, el guard rechaza el resto, el mundo queda incoherente.

**Para cada `return` / early-exit del refactor**, lista:

- ¿Qué estado engine irreversible se ha mutado hasta este punto?
- Si volvemos ahora, ¿el mundo queda en estado coherente?

Si la 2ª respuesta es "no" → el guard está en el sitio equivocado. Muévelo **antes** de la llamada irreversible.

Patrones de orphan verificados:

- **ORPHAN-1**: rate-limit / validación **después** de `super.OnStartServer` de una acción open/toggle. El super ya flipped `IsOpen()`; rechazar el follow-up deja contenedor físicamente abierto con cargo virtualizado en `.lfv`. Fix: rate-limit pre-super, gated en intent inferido. Ref: `LFV_ActionProbe.RateLimitAllowsOpen` en LF_VStorage Capa 6 v3.1.
- **ORPHAN-2**: escritura de SyncVar entre `SetSynchDirty()` no coordinados con el orden de registro del constructor. Bitstream desync silencioso. Fix: registra y escribe en el mismo orden fijo; un `SetSynchDirty()` por batch coherente.
- **ORPHAN-3**: destrucción de entidad dentro de `foreach` sobre un registry, continuando el loop. Stale ref → NPE/crash. Fix: recoger entities-a-borrar en array temporal, borrar tras el foreach.

Reglas de proceso:

- **"Preserva el comportamiento original" es un NO-objetivo** cuando el original tiene bugs. Cada "preserved" es una hipótesis a verificar, no un hecho a defender.
- **"Pre-existente / no introducido por el refactor" no es exención.** Para el audit, exige signoff explícito (fix-now / flag-for-later).
- **Cuando se cace un orphan, hacer sibling-grep cross-codebase** — el bug rara vez vive en un solo sitio.

---

## 3. Debug / fix hierarchy (top-down, obligatorio cuando algo "no funciona")

Cuando algo falla tras implementar, diagnostica de arriba abajo. **Nunca debuguees la capa N+1 hasta confirmar que la N funciona.**

**Capa 1 — Config/Engine**
- [ ] `scope` correcto en `config.cpp`.
- [ ] Hereda del padre correcto.
- [ ] Config compila sin errores.

**Capa 2 — Entity setup**
- [ ] La entidad spawnea en juego.
- [ ] `IsTakeable` correcto (true para items con actions).
- [ ] La clase base proporciona la funcionalidad esperada.

**Capa 3 — Action registration**
- [ ] `AddAction(MyAction)` en el override `SetActions()` de la entidad.
- [ ] La clase de la action compila.
- [ ] `CreateConditionComponents` setea el CCT/CCI correcto.

**Capa 4 — Client conditions**
- [ ] `ActionCondition()` usa solo datos client-available (§1).
- [ ] Target type check correcto.
- [ ] CCT range / component empareja con la distancia de interacción esperada.

**Capa 5 — Server execution**
- [ ] Los métodos server-side (`*Server()`) se ejecutan.
- [ ] Permisos / validación pasan.
- [ ] Las escrituras de datos tienen éxito.

**Capa 6 — Response path**
- [ ] El RPC vuelve al cliente.
- [ ] El client cache se actualiza.
- [ ] La UI refresca.

Reglas:
- Propón el fix **y explica por qué** antes de implementarlo.
- Confianza < 90% → pregunta antes de aplicar.
- Tras el fix: re-corre §2.8 (edge cases) por si el fix introdujo otro problema.

---

## 4. Catálogo de errores recurrentes

Errores cometidos más de una vez. Comprueba **activamente** durante la implementación.

| ID  | Error | Correcto | Fuente |
|-----|-------|----------|--------|
| E01 | `requiredAddons[]={"DabsFramework"}` | `{"DF_Scripts"}` o `{"DF_GUI"}` | UILab, config.cpp |
| E02 | `imageSets` en CfgSlots o root | Dentro de `CfgMods > Mod > defs > imageSets` | ArmorAddition |
| E03 | Mismo nombre de variable en scopes hermanos | Hoist antes del condicional | UILab crash |
| E04 | rvmat Stage4 con sufijo `AS` | `color(0,1,1,1)` sin sufijo, R=0 | ArmorAddition |
| E05 | rvmat Stage2 DT alpha=1.0 | Alpha=0.5: `color(0.5,0.5,0.5,0.5,DT)` | ArmorAddition |
| E06 | rvmat fresnel adivinado | Copia del vanilla ref del mismo shader | ArmorAddition |
| E07 | rvmat damage procedural | Usa `generic_damage_mc.paa` / `generic_destruct_mc.paa` | ArmorAddition |
| E08 | Asumir que una función existe porque "tiene sentido" | Verifica en skill, vanilla, o internet | Múltiples |
| E09 | Seguir más allá de la saturación de contexto | Para, checkpoint, handoff a `30_Sessions/` | Múltiples |
| E10 | `forcedDiffuse` alpha 0 | Alpha 1: `0,0,0,1` | ArmorAddition |
| E11 | String en `ActionCondition` (cliente) | Strings no syncables. Cache cliente o int ID | SimpleGroup |
| E12 | `IsTakeable=false` para evitar pickup | `RemoveAction(ActionTakeItem/ToHands)`. `IsTakeable=false` solo esconde de vicinity, custom actions siguen | SimpleGroup |
| E13 | Notificar **después** de limpiar colección | Loop sobre 0 = 0 notificaciones. Notifica antes | SimpleGroup |
| E14 | Debug downstream sin verificar upstream | Sigue jerarquía §3. Comprueba IsTakeable/AddAction antes de ActionCondition | SimpleGroup |
| E15 | Cache no se limpia en transición de estado | Cada cambio de estado → actualiza cache (cliente + servidor) | SimpleGroup |
| E16 | Fix sin mapear el boundary client/server | Completa §1 antes de escribir el fix | SimpleGroup |
| E17 | SyncVar bitstream cliente/servidor mismatch | Mismas vars, mismo orden, ambos lados | CF Issue #143 |
| E18 | `IsServer()` / `IsClient()` para guard | Usa `IsDedicatedServer()` / `!IsDedicatedServer()` | Expansion Pitfalls |
| E19 | `version` serializada manualmente | El engine la gestiona. Usa el param `version` de `OnStoreLoad` | vanilla EntityAI.c |
| E20 | Culpar p3d/config por un bug de placement cuando la causa está en `Hologram.c` de otro mod | Grep `modded class Hologram` en TODOS los mods cargados antes de tocar p3d. A6_Base_Storage, BBP, etc. reescriben `GetProjectionEntityPosition`/`EvaluateCollision` | Chests stacking |
| E21 | Rate-limit / validación post-`super.OnXxxServer` → orphan state | Pre-super, gated en intent inferido. Ver §2.9 ORPHAN-1 | LF_VStorage Capa 6 v3.1 |
| E22 | "Preserves original behavior" tratado como audit-pass cuando el original tiene bugs | No-objetivo. Cada preserved es hipótesis. Ver §2.9 reglas de proceso | LF_VStorage Capa 6 v3→v3.1 |
| E23 | Patrón sketchy etiquetado "pre-existing" y arrastrado en silencio | Stop, signoff explícito, sibling-grep cross-codebase | LF_VStorage Capa 6 v3→v3.1 |
| E24 | Override de clase anidada de vehículo (`class SimulationModule: SimulationModule`, `Axles`, `Front`, `Rear`…) en un mod hijo SIN declarar la forward-ref `class X;` en el root del propio CfgVehicles → CfgConvert `Undefined base class 'X'` (compile-blocking) | Declarar `class SimulationModule; class Axles; class Front; class Rear;` (las que use el override) en el root del CfgVehicles del mod hijo. Cada config.cpp tiene su propio scope; no hereda forward-refs del PBO padre | kt_roadkill_armed bug-003 |
| E25 | `ProcessDirectDamage(DT_FIRE_ARM, ...)` copiado de un source (BRDM-2) → `DT_FIRE_ARM` no es símbolo vanilla (solo comentario en `object.c`) → compile fail | `DamageType.FIRE_ARM` (enum en `damagesystem.c`). Los `DT_*` que veas en sources de otros mods pueden ser alias propios no portables | kt_roadkill_armed bug-002 |
| E26 | `modded`/`extends` class re-declara una variable miembro que la base vanilla ya declara (ej. `m_NoiseSystem` en `CarScript`) → compile `Multiple declaration of variable 'X'` | NO re-declarar; reusar la heredada (CarScript ya inicializa `m_NoiseSystem`/`m_NoisePar`). Check proactivo antes de compilar: grep cada `m_*` propia contra la cadena base (carscript.c, car.c, transport.c, entityai.c, itembase.c) | kt_roadkill_armed bug-004 |
| E27 | Override con nombre de parámetro distinto al de la firma base (ej. `OnExecuteServer(ActionData actionData)` cuando la base usa `action_data`) → compile `Can't find variable 'X'`. Enforce NO es como C++/C#: el nombre del param en un `override` DEBE coincidir con la base | Copiar la firma con los nombres de param EXACTOS de la base. Verificar contra el archivo vanilla de la clase base (grep la def del método) | kt_roadkill_armed bug-006 |
| E28 | `attachments[] += {...}` en un mod HIJO (clase que hereda de un vehículo en OTRO PBO) NO hereda la lista del base — el config parseado queda con SOLO los items del `+=`, rompiendo TODOS los slots (batería/ruedas/puertas). Verificado con CfgConvert -xml | Materializar `attachments[] = {...}` con la lista COMPLETA del base + los nuevos al final. No confiar en `+=` sobre un parent de otro PBO | kt_roadkill_armed bug-007 |
| E29 | Override de clase anidada de vehículo (`SimulationModule`/`Axles`/`Front`/`Rear`) con `: X` que resuelve a forward-refs VACÍAS, omitiendo sub-bloques (`class wheels`) → SimulationModule malformado, vehículo a medias (no entras, slots/ruedas rotos). NO es solo "compila": carga y rompe gameplay | Replicar el patrón del config original: `class SimulationModule: SimulationModule` pero dentro `class Axles`/`Front`/`Rear` SIN `: X` y CON `class wheels` completo (Left/Right). O no overridear si solo cambias física menor | kt_roadkill_armed bug-007 (síntomas 1/3) |
| E30 | `GetInventory().CreateAttachment("<slot>")` / `CreateInInventory("<slot>")` pasando el nombre de SLOT para montar una pieza → la API toma el **nombre de CLASE del ítem**, no el del slot; si difieren NO crea nada (silencioso, sin error RPT). Enmascarado porque en vanilla el slot suele llamarse igual que la clase (`CarBattery`, `SparkPlug`, `Reflector_1_1`) | Pasar el **nombre de CLASE** del ítem (p.ej. `LFQuad_Wheel_Front`, NO el slot `LFQuad_wheel_1_1`); el engine llena el primer slot compatible libre por llamada. Cruzar clase (CfgVehicles) vs slot (CfgSlots/inventorySlot) antes de escribir | LFQuad Sprint 0 R21 F1 (2026-05-26) |
| E31 | Vehículo (`: CarScript`) o clase de rueda custom (`: CarWheel`) sin `class DamageSystem { class GlobalHealth ... }` → crash `[Object::GetMaxHealth] No DamageSystemData or not initialized` al acceder a su salud (admin `SetHealth01`, daño, colisión, posible sync). Las bases CarScript/CarWheel NO lo garantizan | Declarar `DamageSystem.GlobalHealth.Health { hitpoints; healthLevels[]; }` explícito en el vehículo Y en cada clase de rueda custom (el Croco lo pone en sus ruedas, `croco_config.cpp:251/292`). Mínimo viable = solo `GlobalHealth`, sin `DamageZones` | LFQuad Sprint 0 crash 2026-05-25 + R21 F2 (2026-05-26) |

---

## 5. Inflación de severidad en audits

Patrón observado en audits de LFPowerGrid: etiquetar como `P1 — crash` hallazgos que en realidad son `P2 — VM exception recuperable, server sigue corriendo`. Causa: extrapolar desde mensaje de log (`String CORRUPTED`) hasta comportamiento real (proceso muere) sin verificar.

Antídoto operativo antes de redactar audit findings:

1. Reproducir el bug en server local.
2. Loggear el ciclo completo (carga → execute → autosave → reload).
3. Distinguir:
   - **crash** — proceso muere, server cae, requiere restart.
   - **VM exception** — excepción de Enforce VM, log spam, ejecución continúa.
   - **corruption** — datos malos persisten, código corre con ellos.
   - **degradation** — feature funciona peor pero corre.
   - **cosmetic** — solo visual / sin efecto funcional.
4. La etiqueta del finding usa el término concreto del paso 3, no "crash" como genérico.

Referencia cruzada: R4 + R30 del `CLAUDE.md` global.

---

## 6. Severidad de la AUSENCIA + mínimos que exige el engine (added 2026-05-25)

§5 clasifica la severidad de un BUG observado. Esta sección clasifica la severidad de
algo que FALTA. No es lo mismo "feature incompleta" que "su ausencia crashea".

**Regla (LL-076):** en cualquier audit de gaps, etiquetar cada hallazgo por **severidad
de la ausencia**: ¿no tenerlo crashea / rompe la carga, o solo deja una feature
incompleta? Un mínimo del engine diferido como "feature de nivel alto" puede ser un
crash P1 enmascarado. Caso real LFQuad: `DamageSystem` archivado como "feature N3
(daño)" diferida → su ausencia da `[Object::GetMaxHealth] No DamageSystemData` (crash)
al tocar la salud (admin tools / daño / colisión / sync).

**Checklist de mínimos del engine (anti-crash) — validar TEMPRANO, separado de los niveles de feature:**

- **Vehículo (`CarScript`)**: `class DamageSystem { class GlobalHealth { class Health { hitpoints; healthLevels[]; }; }; }` — sin esto, cualquier `GetMaxHealth`/`SetHealth` crashea. (Las `DamageZones` completas SÍ son feature; el `GlobalHealth` es mínimo anti-crash.) Verificar también las clases de pieza (ruedas) si su salud se toca.
- **Vehículo**: constructor que setee strings de sonido del motor (`m_EngineStart*`) — vacías = audio roto / posible exception con SoundSet "".
- **Modelo `.p3d`**: Geometry LOD con componentes convexos + masa (sin esto no simula); selecciones de acción (`seat_*`, `refill`, doors) en el LOD que el cursor resuelve (ViewGeometry para acciones — verificado LFQuad).
- **Genérico**: si un mínimo del engine se "difiere", separarlo en el plan como **P1 anti-crash** aparte de la feature completa, no en el bucket de la fase tardía.

Antídoto de proceso: la auditoría de paridad (tipo Fase 2) debe incluir una pasada de
"mínimos del engine por subsistema" además del checklist de features, para no descubrir
los crashes de uno en uno in-game.

Cross-ref: R4, R31, LL-076, §5.

---

## Mantenimiento

- Cuando una sesión cace un error que ya está en §4, no añadirlo otra vez — usar el ID existente como referencia en el handoff.
- Cuando una sesión cace un error nuevo recurrente (visto ≥ 2 veces), añadir entrada nueva con ID secuencial.
- Si una entrada se queda obsoleta (engine cambió, parche oficial), tachar con fecha + reemplazo, no borrar (memoria histórica).
- Última revisión: 2026-05-17 (al refactorizar la skill `dayz-mod-workflow` para el pipeline 3-capas).

## Related

- [[dayz-enforce-script-reference]] — reglas duras de sintaxis/memoria/networking que estos checklists referencian.
- [[dayz-capacidades-verificadas]] — gotchas de build/config y veredictos de feasibility complementarios al catálogo de errores.
- [[dayz-modded-class-server-stub-pattern]] — E-pattern de método server-only sin stub base (compile fail en cliente).
- [[dayz-model-pipeline]] — checklist 2.6/2.7 (rvmat, persistence) y los mínimos del engine en `.p3d` (§6).
- [[workflow]] — el "cuándo" del proceso; este archivo es el "qué" verificar.

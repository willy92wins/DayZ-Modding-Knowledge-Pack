---
status: durable-knowledge
created: 2026-05-28
last_verified: 2026-05-28
sources:
  - "video-transcripts/dayz-modding/index.md (4 videos: Tree + hunterz688 x3)"
  - "skills-plugin: dayz-animation-pipeline (SKILL.md + 6 references)"
  - "skills-plugin: dayz-model-pipeline (references/animations.md)"
  - "vault: lessons-learned LL-012"
  - "vanilla DayZ data unpacked at P:\\ (DZ/ + SurvivorAnims/ + 0_SurvivorAnimsDefines/)"
topic: DayZ animations — creatures, weapons/items, anim graphs
confidence_legend:
  "[VERIFIED-vanilla]": "confirmed against unpacked vanilla DayZ data (path:line snippet)"
  "[VERIFIED-vault]": "confirmed against an installed skill, real mod code, or vanilla asset already read"
  "[VERIFIED-source]": "stated by an experienced modder (hunterz688/Tree workshop) — credible but not vanilla-grounded; safe as a design pointer, not as a copy-pasteable identifier"
  "[REFUTED-vanilla]": "video claim contradicted by vanilla data"
  "[TBD-verify-vanilla]": "must grep P:\\ vanilla data before using any exact name/path/value in code"
---

# DayZ animations — creatures, weapons/items, anim graphs

Conocimiento transversal que **complementa** la skill `dayz-animation-pipeline`. La skill cubre Layer 1 (config-driven) y Layer 2/3 (skeletal `.anm`/RTM, tooling). Esta nota cubre las áreas que la skill apenas toca: pipeline de criaturas custom con anim graph + state machine, weapon/item animations con ASI/TXA y la disciplina de Workbench Animation Editor. Cada claim lleva etiqueta de verificación; nada con `[TBD-verify-vanilla]` debe entrar en `verified-apis.md` ni en un diff antes de greparlo en `P:\` real.

## Cuándo leer esta nota antes de la skill

- Vas a animar una **criatura/animal/infected custom** (cualquier cosa más allá de un door/lever rígido): empieza aquí, luego la skill para el seam sandbox/Windows.
- Vas a tocar **animaciones de jugador/armas/items** (reload, fire IK, mag remove, state IDs): empieza aquí, la skill confirma el wall "un solo mod de anim a la vez" y el OFP2_ManSkeleton.
- Vas a construir un **anim graph / state machine** propio: solo aquí. La skill no entra en este nivel.

Si el trabajo es un door/lever rígido, lever, gauge: usa directamente la skill ([`references/config-driven-animation.md`](skills-drafts/dayz-animation-pipeline/references/config-driven-animation.md)) — esta nota no aporta nada.

## Correcciones a los nombres que aparecen en los videos (sprint 2026-05-28)

Tabla maestra de spellings reales contra los que dicen los videos. **Usar siempre la columna de la derecha**.

| Video dice | Realidad VERIFIED | Fuente vanilla |
|---|---|---|
| `discrete = 1` / `discrete = 0` | `isDiscrete = 1` / `isDiscrete = 0` | `BuildingModels/model.cfg`, `Crate/model.cfg` |
| "rigid body vs deformación por weights" | Mecánico (sin interpolación) vs orgánico/suave | `dayz-model-pipeline/references/animations.md:16` |
| "Entity Position" (con espacio) | `EntityPosition` (PascalCase, una palabra) | `DZ/anims/cfg/skeletons.anim.xml:4` |
| "Pin Look At" / "Look At" | `LookAt` (PascalCase, una palabra). `Pin` no existe en vanilla | `DZ/anims/cfg/skeletons.anim.xml:18` |
| "right hand dummy" | `RightHand_Dummy` (con underscore, helper en lod=2) | `DZ/anims/cfg/skeletons.anim.xml:100,115,525` |
| "left hand mag tracking" bones | `LeftHand_Dummy` existe; NO hay magazine bones en skeleton de producción | `DZ/anims/cfg/skeletons.anim.xml:74` + ausencia en player skeleton |
| `cmd death` (minúsculas, con espacio) | `CMD_Death` (UPPER_SNAKE con prefijo `CMD_`) | `DZ/animals/animations/!graph_files/ambientlife/ambientlife_graph.agr` |
| `cmd look at` | `CMD_LookAt` | mismo |
| `cmd attack` | `CMD_Attack` | mismo |
| `cmd success` | `CMD_AttackSuccess` (NO existe `CMD_Success` solo) | mismo |
| `skeletonAnims.xml` / `skeletonanim.xml` | `skeletons.anim.xml` (literal, con puntos) | `DZ/anims/cfg/skeletons.anim.xml` |
| "weapon cocked" (state ID) | `FireCocked` (estado) — el state path es `WeaponOperations.<rig>.FireCocked` | `SurvivorAnims/animgraph/player_main/combat.agr:795` |
| "mag remove" (state ID) | `ReloadMagazineDetach` — state path `WeaponOperations.<rig>.ReloadMagazineDetach` | `.../weapons/player_main_1911.asi:21` |

**Cualquier identificador del video** que no aparezca confirmado en esta tabla o más abajo con `path:line` real, **debe gripearse en `P:\` antes de usarse**. Las videos son una fuente útil pero sistemáticamente imprecisa en casing y separadores.

---

## 1. Pipeline de criatura custom (animal / infected / predator)

### 1.1 Capas del pipeline

```
Blender (rig + skeleton + animaciones)
  → FBX (export con custom properties, sin leaf bones, sin cámara/lámpara, bake animation)
  → Workbench / Object Builder (import, weight painting, validación)
  → model.cfg (CfgSkeletons + bone-parent pairs)
  → anim graph (state machine, commands, variables, events)  ← núcleo del trabajo creativo
  → config.cpp (CfgVehicles entry tipo animal vanilla)
  → scripts mínimos (inventory visible, skinning, hit components)
  → skeleton XML registrado en metadata del mod
  → in-game con AI agent template vanilla (hen / herbívoro / predator)
```

[VERIFIED-source] El video repite: hay que **arrancar con animgraph mínimo (1 estado, 1 anim source)** y validarlo in-game **antes** de cablear estados/variables/eventos. Construir el graph entero offline y descubrir el fallo al final es el anti-patrón.

### 1.2 Bones especiales de criaturas — [VERIFIED-vanilla]

Las criaturas (y el player) usan dos bones del skeleton que el engine entiende nativamente:

- **`EntityPosition`** [VERIFIED-vanilla `DZ/anims/cfg/skeletons.anim.xml:4`]
  - `<bone name="EntityPosition" index="0" movement="true" lod="0" />`
  - Bone que el engine usa para predicción/desplazamiento del entity. Aparece en el skeleton del player y se referencia desde animgraphs de animales — wolf usa `"PredictionTurn" "EntityPosition"` (en `wolf_maingraph.agr`).
  - `movement="true"` es lo que marca el bone como conductor de movimiento real.
  - Para criaturas voladoras se usan trucos porque DayZ no soporta vuelo nativamente [VERIFIED-source, hunterz688 vol.1].

- **`LookAt`** [VERIFIED-vanilla `DZ/anims/cfg/skeletons.anim.xml:18`]
  - `<bone name="LookAt" index="18" lod="0" />`
  - **`Pin` NO existe en vanilla** — el video lo dice mal. El bone es solo `LookAt`.
  - Lo usa el AI / engine para orientar la mirada al target.

[VERIFIED-source] **Orientación de EntityPosition**: forward = +Y (verde en Blender), up = +Z (azul). Misorientación = animal camina de lado / atraviesa el suelo. El video no es vanilla-grounded en esto pero el principio es estándar de Bohemia.

[VERIFIED-source] **Workbench refresh**: cambiar bones/skeleton en `P:` puede requerir reiniciar Workbench para que detecte los cambios. No es bug, es caché de proyecto.

[VERIFIED-source] **Espacios en nombres de bones**: Workbench convierte espacios en underscores; Object Builder no necesariamente. **Recomendación dura: nombres de bones SIN espacios desde el principio** (PascalCase `EntityPosition` o snake como `entity_position`).

### 1.3 Skeleton XML y registro — [VERIFIED-vanilla]

- **Nombre real del archivo**: `skeletons.anim.xml` (literal, con los dos puntos). [VERIFIED-vanilla `DZ/anims/cfg/skeletons.anim.xml:1`: `<skeletons version="1.0">`]
- **Cómo lo encuentra el engine**: por **convención de path en el pbo**, no por una key explícita en `config.cpp`. El `config.cpp` del módulo vanilla `DZ/anims/cfg/config.cpp` contiene SOLO `CfgPatches { class DZ_Anims_Cfg {...} }`; no hay `skeletonFile = "..."` ni similar. [VERIFIED-vanilla]
- **Implicación para mods**: si añades una criatura custom con skeleton propio, el XML debe ir empaquetado en la ruta correcta dentro del pbo del mod (mismo layout `<mod>/anims/cfg/<algo>.anim.xml`) y depender de `DZ_Anims_Cfg` en `CfgPatches`. **No hay que apuntarlo desde config.cpp**.
- **Estructura del XML**: root `<skeletons version="1.0">`, hijos `<skeleton name="...xob">` que listan `<bone name="..." index="N" lod="N" />` (algunos con `movement="true"`).
- **Riesgo "crash al primer spawn"** que el video atribuía al XML faltante: el mecanismo real es que el `.xob` (skeleton binario) o sus bones no estén accesibles para el animgraph; el XML solo expone el catálogo. Verificar empaquetado del XML + del `.xob` referenciado.

### 1.4 FBX export desde Blender — checklist [VERIFIED-source]

Antes de exportar la criatura como FBX:

- **Export custom properties**: sí.
- **Leaf bones**: deshabilitar (DayZ no los necesita y son ruido en el skeleton).
- **Cámara/lámpara**: fuera del FBX.
- **Bake animation**: sí (necesario para que Workbench reciba clips correctos).
- **Rotación de criatura**: cuidar la orientación específica que DayZ espera; revisar tras importar en Workbench antes de seguir.
- Si añades el bone Entity Position / Look At después del rig inicial, **moverlo a su posición canónica antes de exportar** (centro/raíz para Entity Position, child de head para Look At).

### 1.5 model.cfg para criatura — referencias

La estructura del bloque `CfgSkeletons` + pares `"bone","parent"` está [VERIFIED-vault] en:
- [`dayz-animation-pipeline/references/config-driven-animation.md`](skills-drafts/dayz-animation-pipeline/references/config-driven-animation.md) (Layer 1 base)
- `dayz-model-pipeline/references/animations.md` (ejemplos completos)

Para criatura: hereda el `CfgSkeletons` de un animal vanilla (seagull, hen, herbívoro genérico) y añade los bones propios. El ejemplo del seagull en el video muestra que los pares `bone, parent` son la columna vertebral del config.

Nota anatómica: `isDiscrete = 0` para criaturas (movimiento orgánico con interpolación). `= 1` solo para mecánicos.

---

## 2. Anim graph y state machine (para criaturas)

El **anim graph** es la capa que el video llama "preview model / sheet master / state machine". Es donde defines:

- **Estados**: idle, walk, trot, run, attack, hit, death (uno o varios según side/zona de impacto), swim, turn.
- **Anim sources**: qué `.anm` reproduce cada estado.
- **Transitions**: condiciones para pasar entre estados (variable change, event, end-of-clip).
- **Variables**: valores numéricos que conducen blending/selección (`speed`, `swimming`, `state`).
- **Commands**: nombres engine-side que disparan estados desde el AI (death/attack/look at).
- **Events**: marcadores dentro de un clip que disparan sonido, daño, fin de simulación, etc.

### 2.1 Commands canónicos del anim graph — [VERIFIED-vanilla]

Casing real (UPPER_SNAKE con prefijo `CMD_`). El video los dice en minúsculas con espacios; **incorrecto** — usar siempre la columna real.

**Animales** (de `DZ/animals/animations/!graph_files/ambientlife/ambientlife_graph.agr`):

| Real | Video decía | Notas |
|---|---|---|
| `CMD_Death` | `cmd death` | death state trigger |
| `CMD_LookAt` | `cmd look at` | head/look tracking |
| `CMD_LookAtXChange` | (no mencionado) | sub-comando del look at |
| `CMD_Attack` | `cmd attack` | inicia attack state |
| `CMD_AttackSuccess` | `cmd success` | el attack conectó → aplica daño. **NO existe `CMD_Success` standalone** |
| `CMD_Hit` | (no mencionado) | recibe hit |
| `CMD_AnimCallBack` | (no mencionado) | event callback genérico |

**Player** (de `SurvivorAnims/animgraph/player_main/`):

| Real | Uso |
|---|---|
| `CMD_WeaponFire` | dispara arma |
| `CMD_Reload_Magazine` | reload de magazine completo |
| `CMD_Reload_BoltAction` | reload bolt-action |
| `CMD_Reload_Chambering` | chambering bullet |
| `CMD_Reload_ChamberingFast` | chambering rápido |
| `CMD_Reload_Clip` | reload de clip |
| `CMD_Modifier_Additive` | modifier (sickness/cough/sneeze) — **NO es para reload** (ver §3.1 refutación) |

### 2.2 Variables del anim graph — [VERIFIED-vanilla parcial]

- **`speed`** [VERIFIED-vanilla]: variable real en herbivores y ambientlife.
  `DZ/animals/animations/!graph_files/herbivores/herbivores_graph.agr`: `#Var speed float 0.0 0.0 5.0 ""`
- **`SlopeAngleX`** y **`SlopeAngleZ`** [VERIFIED-vanilla]: provistas por el engine, presentes en todos los animal graphs. `#Var SlopeAngleX float 0.0 -90.0 90.0 ""`. **Esta es la base del terrain alignment** (§2.4).
- **`swimming`** [REFUTED-vanilla como `#Var` standalone]: NO existe como variable en animal graphs. En el player graph aparece como **tag de estado** (`TagSwimming`, `SwimmingMaster` en `locomotion.agr`), no como variable float/bool expuesta. El video lo trataba como variable genérica — incorrecto para animales.

### 2.2 State machine mínima — método de validación [VERIFIED-source]

El video recomienda este orden estricto:

1. Crear graph + state machine con **un solo estado idle** y **un solo anim source** (una sola `.anm`).
2. Modelo en in-game con `model.cfg` mínimo (geometry, mass, FireGeo básico). [Cross-ref `dayz-p3d-audit` y `dayz-model-pipeline`.]
3. Verificar que la criatura no crashea, se ve, juega el idle.
4. **Recién entonces** añadir walk → run, blending por `speed`, terrain alignment, hit, death.

Construir todos los estados offline y descubrir bug en uno de ellos = horas/días de bisección.

### 2.3 BlendT (blend tree) por speed — [VERIFIED-source]

Para locomoción: nodo de blending entre walk / trot / run según el valor de la variable `speed`, con **duración de transición** explícita. Las animaciones de turn (giro) deben empezar y terminar en poses compatibles con los loops de walk/run; un turn que empieza/acaba en una pose arbitraria genera popping visible.

### 2.4 Terrain alignment — [VERIFIED-vanilla]

Mecanismo real: nodo `AnimNodeRot` que consume las variables `SlopeAngleX` / `SlopeAngleZ` (provistas por el engine) multiplicadas por **π/180 (= 0.01745329)** para convertir grados a radianes.

- Wolf: `DZ/animals/animations/!graph_files/wolf/wolf_maingraph.agr:3`
  `"AlignToTerrain_Rot" "" "Master_SM" "SlopeAngleX * 0.01745329..."`
- Herbívoros: nodos `TerrainRot_Deers`, `TerrainRot_CowAndBull`, `TerrainRot_BoarAndPig`, `TerrainRot_SheepAndGoat` con la misma fórmula. [VERIFIED-vanilla]

**No es un nodo "especial"** llamado "terrain alignment"; es un `AnimNodeRot` con nombre descriptivo. Para una criatura custom: copiar la fórmula desde el animal vanilla más parecido en proporciones (cuadrúpedo grande → cow, mediano → boar, pequeño → sheep).

### 2.5 Death states — [VERIFIED-source]

Death puede ser multi-state según parámetro/dirección del hit. La state machine vanilla de predators muestra varios estados de muerte (por lado de impacto, por zona del cuerpo). El video lo enseña como referencia copiable.

### 2.6 Hit states y attack — [VERIFIED-source]

- **Hit**: funciona como transition desde múltiples estados (idle, walk, run). Si el asset comprado solo tiene "hit estando quieto", hay que **recombinar en Blender** (non-linear editor) hits desde otras poses base para que la transition no se vea rota.
- **Attack**: requiere estado `attack` + estado `success` (el daño se aplica en `success`, no en `attack`). Eventos dentro de la animación de attack marcan el frame de impacto y el sonido.

### 2.7 Events en animaciones — [VERIFIED-source]

Animation events sirven para:
- Disparar sonido.
- Terminar simulación (death simulation finished → entity puede limpiarse).
- Aplicar damage en el frame correcto del attack.

**Gotcha del video**: añadir events puede romper el graph si el event table no concuerda. Si Workbench falla cargando un graph vanilla copiado, **ajustar el event table** antes que tocar la lógica del graph.

### 2.8 Animaciones de assets comprados — [VERIFIED-source]

Modelos comprados de stock raramente traen animaciones que encajen con las transitions de DayZ (poses de inicio/fin distintas). Hay que **recombinar en Blender** mezclando clips para que walk → run, idle → attack, etc., concuerden en pose.

---

## 3. Weapon / item animations (vol.3)

### 3.1 ASI y TXA — formato real [VERIFIED-vanilla]

- **`.txa`** = texto, fuente de keyframes que Workbench compila a `.anm` binario. [VERIFIED-vault]
- **`.asi`** = `$animsetinstance` con tabla `"StateName.SubName.Phase" → "{GUID}path.anm"`. [VERIFIED-vanilla]

**Estructura real** del `.asi` (de `DZ/anims/workspaces/player/player_main/player_main_rifle.asi:1-6`):

```
$animsetinstance {
  #template "{GUID}DZ/anims/workspaces/player/player_main/player_main.ast"
  #nparents 1
  #parent  "{GUID}DZ/anims/workspaces/player/player_main/player_main.asi"
  $animations {
    "ActionContinuous.BlowFireplaceCro.In" "{GUID}DZ/anims/anm/player/..."
    ...
  }
}
```

- `#template` apunta al `.ast` (animset template — define qué states pueden mapearse).
- `#parent` apunta a otro `.asi` del que se hereda (jerarquía: `player_main.asi` es la raíz, los específicos cuelgan de ella).
- `$animations` mapea `StateName.Sub.Phase` → `{GUID}path.anm`.

**Catálogo completo de ASI del player** [VERIFIED-vanilla `DZ/anims/workspaces/player/player_main/`]:

| ASI | Uso |
|---|---|
| `player_main.asi` | base / parent de todos |
| `player_main_1h.asi` | armas/items una mano |
| `player_main_1h_restrained.asi` | una mano + restrained |
| `player_main_2h.asi` | armas/items dos manos |
| `player_main_heavy.asi` | items pesados (wheel/door/barrel) — el de `AddItemInHandsProfileIK` |
| `player_main_pistol.asi` | pistolas |
| `player_main_rifle.asi` | rifles |
| `player_main_bow.asi` | arco (estado parcial — ver §3.8) |
| `player_main_surrender.asi` | manos arriba |
| `menu_rifle.asi` | rifle en menú/preview |
| `props/` | 30+ ASIs por prop |
| `weapons/` | uno por arma específica (`player_main_akm.asi`, `player_main_1911.asi`, etc.) |

**Implicación**: para una item/weapon custom, hereda del ASI vanilla más cercano y solo añade/override states. No reescribir el ASI completo (cross-ref §4).

### 3.2 Bones y workflow de Fire / Reload / IK

- **`RightHand_Dummy`** [VERIFIED-vanilla `DZ/anims/cfg/skeletons.anim.xml:100,115,525`]
  - Casing real: `RightHand_Dummy` (con underscore). El video lo decía "right hand dummy" — ese exacto string no existe.
  - Es un **helper bone en lod=2** (no es el bone principal `RightHand` que está en lod=1). Sirve como ancla auxiliar para el arma/item — mover este bone mueve el arma.
  - Alinear buttstock vs collarbone y ángulos del antebrazo es lo más sensible del rig [VERIFIED-source].

- **`LeftHand_Dummy`** [VERIFIED-vanilla `DZ/anims/cfg/skeletons.anim.xml:74`]
  - Simétrico al derecho, lod=2.

- **Magazine tracking — no hay bones de mag en skeleton de producción** [VERIFIED-vanilla]
  - Bones `Magazine`, `Bullets_Magazine`, `Bullets_holder`, `Bullets_on_holder` existen SOLO en el skeleton de testing `player_testing.xob` y están marcados literalmente `<!--To Be removed-->` (`skeletons.anim.xml:296-300`).
  - **En producción el engine trackea el magazine vía `LeftHand` / `LeftHand_Dummy` directamente** — no necesita un bone específico de mag.
  - El claim del video de "helper bones en Blender que NO se exportan al juego" es coherente con esto: los helpers viven solo en el `.blend` del autor para visualizar la trayectoria; el `.txa` exportado solo trackea la mano.

- **Fire IK**: puede verse "confuso" en Animation Editor; el rig en Blender (con weapon model presente) ayuda a entender lo que pasa [VERIFIED-source].

- **Blender vs juego**: constraints y números en Blender ayudan a posar, pero **no se exportan tal cual** al TXA. Toca exportar, cargar in-game/preview, mirar gaps de codo, hombro, agarre, e iterar [VERIFIED-source].

### 3.3 Weapon states — [VERIFIED-vanilla]

Los nombres reales (con paths). Patrón general: `WeaponOperations.<RigKey>.<StateName>` donde `<RigKey>` es la combinación pose/rig (p.ej. `ErcRas` = erected + rail accessory system, `Pst` = pistol, etc.).

| Video decía | Real | Ejemplo path | Fuente |
|---|---|---|---|
| "weapon cocked" / "Cocked" | `FireCocked` | `WeaponOperations.ErcRas.FireCocked` → `p_erc_empty_cocked_1911_ras.anm` | `.../weapons/player_main_1911.asi:10` |
| "mag remove" | `ReloadMagazineDetach` | `WeaponOperations.ErcRas.ReloadMagazineDetach` → `p_erc_reload_mag_remove_1911_ras.anm` | `.../weapons/player_main_1911.asi:21` |
| "bullet in chamber" | **NO existe como state name** | — | — |

**Chambering** se hace vía comandos (no state names): `CMD_Reload_Chambering`, `CMD_Reload_ChamberingFast`. El video confundía el comando con un state.

**Trigger del FireCocked state** desde el animgraph del player (`SurvivorAnims/animgraph/player_main/combat.agr`):
- Línea 795: `"FireCockedAnim" "" "WeaponOperations.FireCocked" "noloop"`
- Línea 850: transition condition `"GetCommandI(CMD_WeaponFire) == 2"` (fire con weapon cocked vacío)

**`mag remove` es solo la pose de retorno** [VERIFIED-vanilla por el nombre del `.anm`: `p_erc_reload_mag_remove_1911_ras.anm`]: el script de inventory decide cuándo el magazine sale realmente del slot; la animation solo dibuja la mano alejándose. El video tenía razón en este matiz.

### 3.4 Animation Editor (Workbench) — [VERIFIED-vanilla, mecanismo aclarado]

Mecanismo real: la línea `#eventtable` solo existe en el workspace **compilado** (`DZ/anims/workspaces/player/player_main/player_main.aw:136`):

```
#eventtable "{3037156104937B91}DZ/anims/workspaces/player/Player_EventTable.ae"
```

El workspace **fuente** que se edita en Workbench (`SurvivorAnims/animgraph/player_main/player_main.aw`) **no contiene** esa línea. Por eso el video dice "quitar la línea": para que Workbench abra el graph en el Animation Editor, el `.aw` fuente debe NO tener `#eventtable` (la asociación con el `.ae` se hace al compilar/exportar, no al editar).

**Acción práctica si vas a editar el player graph en Workbench**:
1. Si recibes un `.aw` compilado (extraído de `DZ/`), borra la línea `#eventtable`.
2. Edita el graph en Animation Editor.
3. Al re-exportar/empaquetar, Workbench/Workshop regenera la referencia al `.ae`.

Path del `.ae` de eventos: `DZ/anims/workspaces/player/Player_EventTable.ae`.

### 3.5 FPS — UNKNOWN (no detectable en archivos de texto)

[VERIFIED-vanilla negativo] Búsqueda exhaustiva en `SurvivorAnims/animgraph/` (todos los `.agr`, `.ast`, `.aw`) y en `DZ/anims/workspaces/` (todos los `.asi`, `.aw`, `.asy`) no encuentra ninguna key `fps`, `FPS`, `frameRate`, `framerate` ni el literal `30` en contexto relevante. El único `AnimFPS 30` que aparece está en `SurvivorAnims/Particle/MoneyPtc.ptc` — irrelevante (particle effect).

**Conclusión**: el framerate de las player animations no está declarado en archivos de texto del workspace o animgraph. O bien:
- (a) Está embebido en el binario `.anm` (probable — Bohemia bake del fps al compilar).
- (b) Es convención del exportador (plugin Blender / Workbench compiler).

El claim "30 fps default" del video sigue **sin confirmar ni refutar** sin un inspector de `.anm`. **Acción práctica**: si tu plugin de Blender expone fps, ponlo a 30 (consistente con la convención que el video reporta) y verifica round-trip con una animación corta antes de masivar el set.

### 3.5.bis Reload NO es additive en vanilla — [REFUTED-vanilla]

El video vol.3 afirma que "reload es additive animation: solo torso/hombros hacia abajo". **Vanilla no lo respalda.**

Lo que sí existe [VERIFIED-vanilla]:
- `CMD_Modifier_Additive` (en `player_main.agr:47` y usado en `locomotion.agr:3959-3976`) controla **modifiers de estado del personaje**: `SickSneezeStanceSTM`, `SickCoughStanceSTM`. Tos, estornudo, fiebre. Nada relacionado con reload.
- Los reloads vanilla usan **comandos dedicados sin flag additive**: `CMD_Reload_Magazine`, `CMD_Reload_BoltAction`, `CMD_Reload_Chambering`, `CMD_Reload_ChamberingFast`, `CMD_Reload_Clip`.
- No existe nodo `AnimNodeAdditive` ni tag `TagAdditive` para reloads en el animgraph del player.

**Interpretación**: el video puede estar describiendo cómo se *autora* en Blender (solo se anima torso/brazos, dejando piernas a otra capa por convención de production), pero el **sistema** no marca el reload como additive en runtime. Implementar tu propio reload custom asumiendo que es additive y se mezclará "automáticamente" → te puede romper la pose. **Verifica en el animgraph vanilla más cercano cómo entra/sale del state**.

### 3.6 Frames mínimos por state — [VERIFIED-source]

Cuidado con states de pocos frames (los videos mencionan "end on frame 2"). Si el state termina antes de tiempo, el engine se queda mostrando 2 frames únicos. Revisar duración del clip vs duración esperada del state.

### 3.7 Custom item animations sin re-autorizar todo el ASI [VERIFIED-source]

Para añadir animaciones a un **item custom** (encender/apagar, custom action):

- **Heredar/override una anim instance existente** en vez de crear ASI desde cero.
- Modificar solo el state nuevo y dejar el resto de la jerarquía intacto.
- Cuidado: locomoción y additive heredados de parent ASI son **delicados**; pueden romperse al sobreescribir.

### 3.8 Límites conocidos del sistema [VERIFIED-source]

A 2024-03-30 no estaban resueltos:
- **Dual wielding** (dos armas a la vez).
- **Bow** (la mecánica de arco completa).
- **Additive locomotion** customizada (modificar la capa additive del walk/run rompe visualmente al personaje fácilmente).

Si tu plan toca esto, marcar como riesgo alto en `assumptions.md` desde el día 1.

### 3.9 Versión de Blender — [VERIFIED-source no verificado]

El video recomienda **Blender 3.6.8** porque los sample `.blend` se hicieron ahí; otra persona reportó que **Blender 4.1** rompía con el plugin de DayZ animation. Vault no tiene confirmación independiente. **Si vas a empezar in serio**: arranca con 3.6.8, deja un test rápido en 4.x antes de cerrar.

### 3.10 Player skeleton — mapa de bones [VERIFIED-vanilla]

De `DZ/anims/cfg/skeletons.anim.xml` (skeleton de producción + `player_testing.xob`). Organizado por zona para usar como referencia al mapear armatures de Blender → DayZ.

**Core / spine**
- `Scene_Root`, `EntityPosition`, `Pelvis`, `Spine`, `Spine1`, `Spine2`, `Spine3`, `Neck`, `Neck1`, `Head`, `LookAt`

**Piernas** (simétrico izquierda/derecha)
- `LeftUpLeg`, `LeftUpLegRoll`, `LeftKneeExtra`, `LeftLeg`, `LeftLegRoll`, `LeftFoot`, `LeftToeBase`
- + `Right*` equivalentes
- Helpers de cadera: `LeftHipExtra`, `RightHipExtra`, `LeftHip_Helper`, `RightHip_Helper`

**Brazos** (simétrico)
- `LeftShoulder`, `LeftArm`, `LeftArmRoll`, `LeftForeArm`, `LeftForeArmRoll`, `LeftHand`
- + `Right*` equivalentes (+ `RightArmExtra`)
- Helpers de mano: `LeftHand_Dummy`, `LeftWristExtra`, `LeftForeArmExtra`, `LeftElbowExtra`, `LeftArmExtra` (+ `Right*`)

**Fingers** (lod 2)
- `[Left/Right]Hand[Ring/Pinky/Middle/Index/Thumb]1..4`

**IK helpers** (críticos para weapon authoring)
- `RightHandOrigin`, `LeftHandOrigin`, `LeftHandIKTarget`, `LeftHandIK`, `RightHandIK`
- `LeftForeArmDirection`, `RightForeArmDirection` (+ Origin variants)

**Weapon attachment / interaction**
- `Weapon_Root` (ancla principal del arma)
- `Weapon_Bullet`, `Weapon_Trigger`, `Weapon_Magazine`, `Weapon_Bolt`
- `Weapon_Bone_01..06` (slots configurables)
- `Weapon_Holster`, `Pistol_Holster`, `Weapon2hnd_Holster`
- `weapon` (lowercase, legacy compat)

**Face** (lod 2)
- `Face_Hub`, `Face_Jawbone`, `Face_Chin`, `Face_Eyelids`, `Face_Forehead`
- `Face_Brow*`, `Face_Lip*`, `Face_Cheek*`, `Face_Tongue`
- `EyeLeft`, `EyeRight`

**Misc / system**
- `Opponent`, `Camera3rd_Helper`, `Camera1st_lock_dummy`, `Marker`

**Legacy / to-be-removed** (NO usar — están marcados `<!--To Be removed-->` en `player_testing.xob`)
- `Bullet`, `Trigger`, `Magazine`, `Bolt`, `Bullets_Magazine`, `Bullets_holder`, `Bullets_on_holder`, `Universal1`, `Universal2`

---

## 4. Anim instances y el patrón de override

[VERIFIED-source] La forma idiomática de añadir o cambiar una animation en DayZ para un item custom es:

1. Encontrar el anim instance vanilla más cercano a lo que quieres.
2. **Heredar/sobreescribir** ese instance, no crear desde cero.
3. Cambiar solo lo necesario (state ID, anim file, transition).
4. Dejar el resto del ASI tocando lo mínimo.

Cross-ref Layer 1 de la skill ([`item-ik-and-hide.md`](skills-drafts/dayz-animation-pipeline/references/item-ik-and-hide.md)): el patrón A "carry IK reusando vanilla `.anm`" es la versión ya verificada de este mismo principio para items pesados (wheel/door/barrel).

---

## 5. AI behavior wiring (criatura ambient sin agresión)

[VERIFIED-source] Para un animal ambient tipo seagull (no agresivo, no malgasta CPU):

- Copia el AI agent template de hen o ambient life vanilla.
- Configura equipo / friendliness para que no pelee.
- Da inventory mínimo, skinning component, hit components.
- Si la criatura es predator (agresiva) copia desde wolf/bear vanilla, ajusta rango de ataque.

Mucho de esto está **poco documentado oficialmente**, según el video. La estrategia es: clonar vanilla más cercano, cambiar lo mínimo, iterar.

---

## 6. Eco de la skill: lo que NO repetimos aquí

Para evitar duplicar conocimiento (R20 anti-refactor incidental, R25 simplicidad), esto NO se duplica desde la skill — léelo allí:

- Wall "un solo mod de animation a la vez (player/creature)": skill `SKILL.md` § anchor 3, [`references/tooling-and-walls.md`](skills-drafts/dayz-animation-pipeline/references/tooling-and-walls.md) § "The walls".
- Bone names del player must match `OFP2_ManSkeleton` exact: skill [`references/skeletal-anm-enfusion.md`](skills-drafts/dayz-animation-pipeline/references/skeletal-anm-enfusion.md).
- Pipeline `.txa` → Workbench → `.anm`, `SEAnim` → DayZATool → `.anm`: skill mismas referencias.
- `AddItemInHandsProfileIK` API completo para items pesados con IK reusada: skill [`references/item-ik-and-hide.md`](skills-drafts/dayz-animation-pipeline/references/item-ik-and-hide.md).
- `model.cfg` structure (CfgSkeletons + CfgModels + class Animations + properties): skill [`references/config-driven-animation.md`](skills-drafts/dayz-animation-pipeline/references/config-driven-animation.md) y `dayz-model-pipeline/references/animations.md`.
- Hide-on-attach pattern (`type="hide"`, `hideValue`): skill mismo doc, con [TBD-verify] sobre el threshold exacto.
- LL-012: animar sub-pieza de proxy requiere separarla + mod derivado necesita su propio `.p3d` + `model.cfg`.

---

## 7. Estado de verificación y pendientes

**Sprint 2026-05-28** promovió la mayoría de claims de [TBD-verify-vanilla] a [VERIFIED-vanilla] usando `DZ/`, `SurvivorAnims/` y `0_SurvivorAnimsDefines/` desempaquetados.

**Verificado (path:line en vanilla)**:
- §1.2 bones de criatura (`EntityPosition`, `LookAt` — sin `Pin`)
- §1.3 skeleton XML (`skeletons.anim.xml`, sin entry explícita en config.cpp)
- §2.1 commands (`CMD_*` UPPER_SNAKE, casing real)
- §2.2 variables (`speed`, `SlopeAngle*` confirmados; `swimming` solo como tag de player, no var de animal)
- §2.4 terrain alignment (`AnimNodeRot` con `SlopeAngleX * 0.01745329`)
- §3.1 ASI estructura + catálogo completo
- §3.2 `RightHand_Dummy` / `LeftHand_Dummy` (sin mag bones en producción)
- §3.3 weapon states (`FireCocked`, `ReloadMagazineDetach` — sin `BulletChambered`)
- §3.4 Workbench Animation Editor (mecanismo `#eventtable`)
- §3.10 player skeleton (mapa completo de bones)

**Refutado por vanilla**:
- §3.5.bis reload NO es additive (los additive modifiers son para sickness, no reload)
- §2.2 `swimming` no es var standalone en animal graphs
- "Pin Look At" — `Pin` no existe en vanilla
- `cmd success` solo — el comando real es `CMD_AttackSuccess`
- `BulletChambered` — no existe como state, el chambering se hace por command

**Aún UNKNOWN (no detectable en archivos de texto vanilla)**:
- §3.5 30 fps default para player anims — embebido en binario `.anm` o convención del exportador. Asumir 30 + round-trip test.
- §3.9 Blender 3.6.8 vs 4.1 — vault no tiene confirmación independiente. Probar.

**Pendientes operativos**:
1. **Roadmap pipeline**: este conocimiento ya está sólido — considerar proponer APPEND a la skill `dayz-animation-pipeline` con un nuevo `references/anim-graph.md` (cubre commands `CMD_*`, variables del graph, terrain alignment, ASI structure). Pasar por R34 (propuesta al usuario, no auto-aplicar).
2. **Cola de patches**: registrar en [`20_Knowledge/skill-patches-pending.md`](skill-patches-pending.md) el patch propuesto a `dayz-animation-pipeline` si se decide hacerlo.

---

## 8. Procedencia y links

**Verificación contra vanilla (sprint 2026-05-28)** — fuente primaria de las promociones a [VERIFIED-vanilla]:
- `DZ/anims/cfg/skeletons.anim.xml` — todos los bones de §1.2, §3.2, §3.10
- `DZ/animals/animations/!graph_files/{ambientlife,herbivores,wolf}/*.agr` — commands §2.1, variables §2.2, terrain alignment §2.4
- `DZ/anims/workspaces/player/player_main/*.asi` + `weapons/*.asi` — ASI structure §3.1, weapon states §3.3
- `SurvivorAnims/animgraph/player_main/{combat,locomotion,player_main}.agr` — player commands §2.1, refutación additive §3.5.bis
- `DZ/anims/workspaces/player/player_main/player_main.aw` vs `SurvivorAnims/animgraph/player_main/player_main.aw` — diff `#eventtable` §3.4

**Procedencia original (videos procesados por Codex 2026-05-28)**

- Tree, "DayZ Basic Animations Tutorial", 2026-02-14, 22:31 — [`video-transcripts/dayz-modding/2026-02-14-tree-dayz-basic-animations-tutorial.md`](video-transcripts/dayz-modding/2026-02-14-tree-dayz-basic-animations-tutorial.md)
- hunterz688, "DayZ Custom Animations Introduction", 2023-06-02, 01:29:26 — [`video-transcripts/dayz-modding/2023-06-02-hunterz688-dayz-custom-animations-introduction.md`](video-transcripts/dayz-modding/2023-06-02-hunterz688-dayz-custom-animations-introduction.md)
- hunterz688, "DayZ Animation workshop vol.2", 2023-12-22, 01:46:07 — [`video-transcripts/dayz-modding/2023-12-22-hunterz688-dayz-animation-workshop-vol-2.md`](video-transcripts/dayz-modding/2023-12-22-hunterz688-dayz-animation-workshop-vol-2.md)
- hunterz688, "DayZ Animation Workshop vol.3", 2024-03-30, 01:34:18 — [`video-transcripts/dayz-modding/2024-03-30-hunterz688-dayz-animation-workshop-vol-3.md`](video-transcripts/dayz-modding/2024-03-30-hunterz688-dayz-animation-workshop-vol-3.md)
- handoff de la sesión que procesó los videos: [`30_Sessions/2026-05-28-dayz-animation-video-notes.md`](../30_Sessions/2026-05-28-dayz-animation-video-notes.md)
- skill `dayz-animation-pipeline` (instalada): cubre Layer 1/2/3, las dos walls, ASI heavy.
- skill `dayz-model-pipeline/references/animations.md`: estructura completa `model.cfg` con `isDiscrete`.
- lessons-learned LL-012 (proxy sub-piece animation).

---

## Orientación de la mano de apoyo: GEOMÉTRICA, no rotación de muñeca de la ikpose [VERIFIED-ingame 2026-06-17, A6_SR2M]

Probado in-game (A6_SR2M, SMG custom sin hand memory points, anims AKS74U; iter17–22 retail, captura por
órbita): **rotar el bone `LeftHand` (muñeca) en la ikpose NO reorienta la mano de apoyo.** El ASI/IK
realinea la mano al arma y absorbe la rotación de muñeca. 4 variantes con `LeftHand` a 90° en ejes
distintos (120–180° entre sí) renderizan IGUAL in-game; pixel-diff de la zona de la mano: 180° de roll =
RMS 7.8, MENOR que un cambio de curl de dedos (RMS 11). Lo único de la ikpose que se aplica visiblemente
es el **curl de dedos** (`LeftHand{Thumb,Index,Middle,Ring,Pinky}*`), no la orientación de la muñeca.

Mecanismo real (cf. `skills-plugin: dayz-animation-pipeline/references/weapon-in-hands.md` — el AKM
vanilla tiene 0 hand memory points): la mano de apoyo la posa el `.anm` de referencia anclado al origin
del arma (`Weapon_Root`/`RightHand_Dummy`); lo que decide dónde/cómo cae es la **parity geométrica**
arma↔anim-de-referencia, no la ikpose. `weapon_grip_viewer.py` cuantifica el gap (SR2M vs
`aks74u_vanilla_mlod`: bore alineado 0°, pero arma ~3 cm más baja + cañón más corto → mano alta/adelante,
palma horizontal de guardamanos, no vertical de foregrip).

**Corrige una sobre-generalización:** un diff de dos ikposes vanilla del MISMO arma (OTS-14 `normal` vs
`barrelhandle`) muestra un delta de `LeftHand` (24.8°), pero ese delta existe porque ambas poses se
autoraron contra un arma CON parity — NO implica que rotar `LeftHand` en un arma sin parity reproduzca
la orientación. Para palma vertical en un foregrip custom: parity geométrica con un anim cuya mano ya
caiga vertical (verificar con `weapon_grip_viewer.py`), o ajuste de geo/offset del arma — no rotar la ikpose.

---

## RESUELTO 2026-06-23: el grip se cierra SUBIENDO el arma (idle Y aim) [VERIFIED-ingame + gate]

Cierre de la línea de arriba. La palanca que funciona NO es rotar la ikpose ni la muñeca, sino **subir/
trasladar el ARMA hasta donde el anim posa la mano de apoyo**. RE empírica de un mod que funciona
(KarmaKrew, workshop 2864245850; armas Vikhr/SR-2M) confirmó: logran el grip con ikposes VANILLA IK-driven
(`vikhr.anm`, `pm73_ik.anm`) + behavior firearms + **parity de geometría**, sin anim mod de player, sin
override de pose base, sin huesos por script.

- **El número:** el bore del SR2M estaba 2.4 cm más bajo sobre el origen del arma que la referencia KK
  (Y0.066 vs 0.090) → la mano del anim caía ENCIMA del cañón. Trasladar TODO el modelo +Y0.024 (patrón
  global-offset; bore 0.066→0.090) sube el arma a la mano y cierra el agarre. Heurística: si las palancas
  de anim (ikpose pos/rot, behavior, LeftHand FK) salen inertes, **mueve el ARMA, no el anim**.
- **Cierra AMBAS stances.** El ikpose es compartido idle↔aim y se temía que cerrar el idle dejara el aim
  abierto (el aim-space additive abre la mano). Empíricamente no pasó: el mismo arma subida cerró el idle
  (validado in-game, shipped) Y el apuntado (gate iter37, 3ª persona, comparable a KK). El override
  per-stance del `.asi` queda como FALLBACK, no necesario aquí.
- **Capturar la pose de aim para validar (herramienta MCP):** forzar el raise **CLIENT-side** (`modded
  MissionGameplay` sobre `GetGame().GetPlayer()` → `OverrideRaise(ENABLED,true)`), NO en el `init.c` del
  servidor — el personaje capturado es el player local del cliente y los overrides del server no mueven su
  render (gate iter36: server `raised=1` pero arma bajada). `WeaponADS()` es flag de input (sin override de
  script) → métrica de éxito errónea; usar `IsRaised()` / log del cliente. No `SetIronsights()` (pelea con
  la free-cam). La pose de aim 3ª persona depende solo de `IsRaised()` (`dayzplayerimplement.c:1726`,
  AimingModel).
- **Juzgar por la mano a resolución NATIVA**, nunca el contact-sheet reescalado (la mano ~30px engaña; un
  grip bueno se declaró "inerte" por mirar la miniatura).

Detalle con citas: skill `dayz-animation-pipeline/references/weapon-in-hands.md` (§"Geometric parity IS the
grip fix") + skill `dayz-mcp-verify` (§"capturar arma alzada"). Proyecto A6_SR2M:
`research\2026-06-22-karmakrew-vikhr-RE-grip-mechanism.md`, `HANDOFF.md`.

## Related

- [[dayz-custom-infected]] — riguear una criatura/zombi al OFP2_ManSkeleton; usa los bones y el anim graph que esta nota detalla.
- [[dayz-capacidades-verificadas]] — veredicto de feasibility del pipeline de animación (dos sistemas, muros, herramientas Windows).
- [[dayz-model-pipeline]] — la named selection + memory points que se animan se autoran aquí (lado geometría `.p3d`).
- [[dayz-p3d-inspector-memory-selection-bugs]] — el lector ODOL pierde selecciones de Memory LOD (ejes de anim) al debinarizar.
- [[dayz-mod-implementation-checklists]] — checklist de model.cfg / config.cpp para entidades con animación.

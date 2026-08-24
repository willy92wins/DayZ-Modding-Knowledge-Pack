# DayZ — Capacidades verificadas y veredictos de feasibility

> Conocimiento transversal. Recoge **veredictos de viabilidad** que costaron
> sesiones enteras de investigación (revisar P:\, clonar CF/Dabs, búsqueda
> web, spikes) y un puñado de **gotchas verificados** que no están cubiertos
> por las skills de DayZ. El objetivo: no repetir investigaciones ya cerradas.

## Veredicto: NO se pueden capturar píxeles desde un mod puro de DayZ

Investigado a fondo en el proyecto **LF-COM** (mod de "red social de fotos
in-game"). Conclusión firme tras revisar todo `P:\`, clonar CF y Dabs
Framework (cero APIs de captura/bitmap/readback) y búsqueda web:

- **DayZ retail no permite leer el framebuffer desde script.** Es un
  bloqueo intencionado de Bohemia (anticheat / control de plataforma).
- **`CallExtension` (DLL nativa) fue eliminado del API público de DayZ.**
  Existe en Arma 3, no en DayZ. BattlEye bloquea extensions client-side y
  no hay proceso de whitelisting. Cero mods del Workshop han logrado
  shippear una DLL client-side. (Fuente: blog.lystic.dev, 2021-05-22.)
- **`MakeScreenshot` está roto desde la 1.19** y sigue roto en 1.29.
  Bohemia no lo va a arreglar.
- **`Workspace.SaveScreenshot()` NO existe** — fue una confabulación en una
  sesión; no asumirlo.
- **`SetObjectTexture` es local/client-only** en DayZ Enforce. No existe
  `SetObjectTextureGlobal` (eso es solo Arma 3). Las surfaces `r2t` son
  config-bound (declaradas estáticamente en `config.cpp`, atadas a memory
  points), **no creables en runtime** desde script, y requieren PiP activo.
  Verificado en `entityai.c v1.24.157551`.

**Decisión arquitectónica derivada (LF-COM)**: el camino viable es
**PBO + launcher companion `.exe` + backend web**. El launcher polea la
carpeta de screenshots de Steam y un archivo bandera en `$profile:\LFCOM\`,
convierte PNG→EDDS con `ImageToPAA.exe` de Bohemia, y el mod carga el EDDS
con `LoadImageFile`.

### APIs de cámara/preview que SÍ funcionan (verificadas)

- `PlayerPreviewWidget`: `GetDummyPlayer()` (desde 1.02), `SetModelOrientation`,
  `SetModelPosition`, `UpdateItemInHands`. **Solo sirve para humanos** — no
  hay widget vanilla equivalente para zombis/animales/IA.
- `FreeDebugCamera.GetInstance().SetFreezed(false)`.
- Patrón de skins replicadas que sí funciona: distribuir N `.paa` en el PBO
  vía `hiddenSelectionsTextures[]`, replicar solo el índice por SyncVar/RPC,
  cada cliente llama `SetObjectTexture(i, array[idx])` local.

## Veredicto: física de debris e items dinámicos

- **`ECE_CREATEPHYSICS` no basta** para debris con `simulation = "inventoryItem"`:
  crea el shape pero deja el body estático, `dBodyApplyImpulse` se descarta
  → debris congelado en el aire. **Fix**: `InventoryItem.ThrowPhysically(null, impulse, false)`
  (requiere castear `EntityAI → ItemBase`). Alternativa manual:
  `CreateDynamicPhysics` + `SetDynamicPhysicsLifeTime` + gravity + impulse.
- **PhysX ignora silenciosamente los componentes de Geometry LOD < 0.5 m.**
  Por eso un POC de pelota se hizo de 50 cm. Truco de producción: un
  Geometry LOD oversized invisible para mantener el visual al tamaño real.
- **Regla 0.5 m matizada**: aplica a colisión por Geometry LOD
  (`Container_Base`/`BuildingBase`), NO a `Inventory_Base` con
  `simulation=inventoryItem`. Y un `Container_Base` destructible **sin
  FireGeo no recibe balas** — el FireGeo es necesario para recibir disparos.
- **`StaticObj_Wreck_Train_Wagon_*` son cuerpos PhysX estáticos** —
  `dBodyApplyImpulse` se descarta sobre ellos. Vía viable: detectar colisión
  con `OnContact`, borrar el static y sustituir por entidad propia dinámica.
- **El plastic explosive vanilla NO detona al ser ruined** — safety feature
  intencional de Bohemia. Solo detona vía Remote Detonation Unit; `Detonate()`
  es privado. Alternativa: orquestar manualmente (partícula + soundset +
  `AreaDamageManager`) o llamar `Detonate()` por reflection.

## Gotchas verificados no cubiertos por skills

Estos causaron oleadas repetidas de errores de compilación o bugs en
proyectos reales. Si reaparecen en un tercer mod, candidatos a entrar en
`enforce-script-reference` / `dayz-pbo-build`.

**Config / build:**
- `requiredAddons` debe ser `"JM_CF_Scripts"`, **no** `"CF"`.
- `worldScriptModule files[]` lista solo la **carpeta raíz** (`4_World`), no
  las subcarpetas (`Actions`) por separado. Apuntar a una carpeta incluye
  automáticamente archivos nuevos → no hay que tocar `config.cpp` al añadir
  un `.c` a esa carpeta.
- Rutas de textura en `config.cpp` necesitan **doble backslash**
  (`\\dz\\gear\\…`); con uno solo el engine no resuelve.
- Clases proxy: deben heredar de `ProxyAttachment` y las rutas de modelo
  proxy llevan `\` inicial (`"\LFPowerGrid\data\…"`). `hiddenSelections[]`
  necesario para material swaps por script.
- `hiddenSelections[]={"camoGround"}` (p. ej. `Barrel_ColorBase`) **oculta
  la geometría** hasta que `hiddenSelectionsTextures[]` le asigna textura:
  sin textura el objeto es invisible, no gris.
- Falta `$PBOPREFIX$` en raíz = AddonBuilder falla.

**Enforce Script:**
- Sin `do...while`. Patrón estándar DayZ:
  `bool keep=true; while(keep){ …; keep=FindNextFile(...); }`.
- No permite expresiones partidas en varias líneas.
- Si la clase padre tiene constructor parametrizado, **todos** los hijos
  deben tener firma idéntica → solución: padre sin constructor
  parametrizado, cada hijo define el suyo.
- `ref` solo en class member fields, **nunca** en locales.
- `JsonKeyExists` debe incluir el `:` en el patrón (`"key":`) para no
  matchear substrings.
- `Print()` escribe en el **script log** (donde salen los `SCRIPT :`);
  `PrintToRPT()` escribe en el `.rpt`. Confundirlos = "no sale nada en el log".
- Para notificar al jugador: `player.MessageStatus()` — no `GetGame().Chat()`
  (no depende de mods de chat).
- Al consumir una tecla con un prompt custom visible: `return` SIN llamar a
  `super.OnKeyPress()`, si no hay doble activación (la F está ligada al
  ActionManager vanilla).
- `DZ_Weapons` siempre está cargado en runtime aunque no esté en
  `requiredAddons`.

**Otros:**
- Bug T148506: `inventorySlot` string-vs-array al portar clases.
- Damage rvmat que solo cambia tinte = el Stage3 usa proc `color()` en vez
  de la textura overlay vanilla (`weapons_damage_wood_mc.paa`, tiling 4×).
- DayZ 1.29 renombró SoundSets vanilla: `VSS_Vintorez_*` → `VSS_silencer_*`;
  `AmphibianS_InteriorTail` → `AmphibianS_silencerInteriorTail`. Los
  SoundSets custom de mods viven en sus propios PBOs y no necesitan alias.
- `OnStoreLoad` devolviendo `false` no crashea el server: la entidad no
  entra al mundo, `m_IsStoreLoad=false`, la entrada se purga al siguiente
  autosave (es una `Virtual Machine Exception` capturada, self-healing).
- Diagnóstico de minidump de server DayZ: la RPT trunca direcciones a 32
  bits ("Unknown module" engañoso); la dirección real es 64-bit. Sin PDBs
  de Bohemia no se puede ir más allá de "el AV cae dentro de
  `DayZServer_x64.exe`" = bug de engine.

## Veredicto: animación DayZ (fase 0 research, 2026-05-20)

Investigado para la skill `dayz-animation-pipeline` (draft en
`AI/20_Knowledge/skills-drafts/dayz-animation-pipeline/`). Dos sub-agentes web
con fuentes primarias (wiki Bohemia, PMC wiki, repos GitHub, `seanim.py`).

**Hay DOS sistemas de animación en paralelo — no confundirlos:**

- **Config-driven** (`model.cfg` + `config.cpp` + script): props/objetos —
  puertas, palancas, ruedas, hide-on-attach. Tipos `rotation(X/Y/Z)` y
  `translation(X/Y/Z)` [VERIFIED PMC wiki]. `SetAnimationPhase`. **100% texto,
  producible en sandbox.** El tipo `hide` está [VERIFIED contra mod real
  kt_roadkill] pero no en la PMC wiki — confirmar `hideValue` contra vanilla.
- **Skeletal**: personajes/armas usan el pipeline **Enfusion `.txa`→`.anm`**
  (NO RTM). RTM es legacy (Real Virtuality), para props/man legacy.

**Costura sandbox/GUI (lo crítico):** mi sandbox es Linux sin `P:\` ni DayZ
Tools. Capa 1 (config) la produzco entera. Capa 2 (intermediarios open:
**SEAnim** open-spec, keyframes Blender headless) la asisto. Capa 3 (Workbench,
FBXToRTMGui, firma PBO, test in-game) es solo Windows/GUI/computer-use.

**Muros [VERIFIED]:**
- **Un solo mod de animación de jugador a la vez** — dos crashean cliente/server
  (límite del engine Enfusion, no política). No afecta a animación de objetos.
- **RTM es ingeniería inversa** (aviso legal explícito de Bohemia). NO existe
  writer RTM open-source en Python puro; solo plugins de Blender escriben RTM.
- **`.anm` es propietario**; DayZATool lo escribe (binario cerrado). **SEAnim
  SÍ es formato abierto** → vía programática (writer verificado por round-trip
  en [`scripts/seanim_writer.py`](skills-drafts/dayz-animation-pipeline/scripts/seanim_writer.py), layout transcrito literal de `seanim.py`).
- Esqueleto `OFP2_ManSkeleton`, nombres de hueso exactos o RPT logea
  `Bone X doesn't exist`. No se puede reestructurar el esqueleto vanilla
  ([TBD-verify], consenso comunidad).

**Herramientas reales (todas Windows):** Arma3ObjectBuilder (Blender 4.2+,
export RTM), FBXToRTMGui.exe (DayZ Tools), DayZATool (DTZxPorter, `.anm`↔SEAnim),
DayZAnimationPluginDemo (Blender→`.txa`), SE2Dev/io_anim_seanim (SEAnim spec).

**Pendientes [TBD-verify] heredados** (confirmar contra `P:\` antes de fiarse):
tipos `translationModelX/Y/Z` y `direct`; fuentes engine DayZ `doors`/`damage`;
firma exacta de `SetAnimationPhase`; factor de escala Blender→DayZ; si los
plugins Blender DayZ/Arma corren headless en sandbox; catálogo de `.anm` IK
vanilla (paths Hatchback_02); si FBXToRTM viene con DayZ Tools o solo Arma 3.

**Clarificación de la costura (added 2026-05-20, evals + empaquetado):** el lado
geometría `.p3d` que necesita una animación —la named selection que se anima y el
par de memory points que define el `axis`— **es producible en sandbox**, NO es
Object Builder/Windows. Vía: `dayz-p3d-inspector` (extract → Recipe JSON → editar
memory points/axes/selections → rebuild `.p3d`) o `dayz-model-pipeline` (py3d
assembly); un conversor ODOL→MLOD externo primero si el `.p3d` es ODOL (binarizado, no
editable); `dayz-p3d-audit` para verificar winding/`Component01`. Caveats: py3d
edita MLOD; añadir memory points y el axis es trivial, pero **autoría de una named
selection nueva que agrupe geometría específica** se apoya en el contexto de
`dayz-model-pipeline`. Layer 3 real para trabajo Layer 1 = solo firma PBO + test
in-game. (El draft inicial empujaba esto a Object Builder por conservadurismo;
corregido en la skill tras eval.)

**Estado de la skill (2026-05-20):** `dayz-animation-pipeline` empaquetada a
`.skill` nativo en [`AI/20_Knowledge/skills-drafts/dayz-animation-pipeline.skill`](skills-drafts/dayz-animation-pipeline.skill).
Evals cerrados (con-skill 100% vs baseline 56% sobre 4 casos, n=1/brazo). Dos
mejoras validadas: `hideValue` como `[TBD-verify]` must-tag, y la clarificación de
costura de arriba. Handoff: [`30_Sessions/2026-05-20-dayz-animation-pipeline-evals-packaging.md`](../30_Sessions/2026-05-20-dayz-animation-pipeline-evals-packaging.md).

## Relacionado

- Skills: `enforce-script-reference`, `dayz-pbo-build`, `dayz-model-pipeline`,
  `dayz-p3d-audit` — cubren la mayoría del modding; esta nota es el
  complemento de lo que se verificó en proyectos y no está en ellas.
- Skill draft `dayz-animation-pipeline` — pipeline de animación completo
  (config-driven + skeletal), pendiente de evals + empaquetado.
- [`AI/20_Knowledge/dayz-modded-class-server-stub-pattern.md`](dayz-modded-class-server-stub-pattern.md) — patrón stub
  server-only (bug pattern relacionado con `#ifdef SERVER`).
- Proyectos donde se verificó: LF-COM, Crate, LF_VStorage, LF_PowerGrid,
  LF_Transfer (ver [`AI/10_Projects/_ESTADO-PROYECTOS.md`](../10_Projects/_ESTADO-PROYECTOS.md)).
- [[dayz-enforce-script-reference]] — reglas duras de Enforce que complementan los gotchas de build/script de aquí.
- [[dayz-mod-implementation-checklists]] — catálogo de errores recurrentes (E01–E31) y mínimos del engine anti-crash.
- [[dayz-animations-creatures-weapons]] — desarrolla el veredicto de animación con identificadores VERIFIED contra vanilla.
- [[dayz-p3d-inspector-memory-selection-bugs]] — detalle del agujero de RE en el lector ODOL v55 mencionado abajo.

## Limitación verificada — lector ODOL v55: la sección de anims no parsea (added 2026-05-25)

Confirmado 2 veces de forma independiente el 2026-05-24/25 (Claude en kt_roadkill_armed
+ Codex C1 en la misma sesión): el lector ODOL externo (conversor ODOL→MLOD, no distribuido en este pack) **no
parsea la sección de animaciones en formato v55**. El desync NO está en `AnimationClass`
(un parche ahí no lo resolvió). Consecuencia práctica:

- NO re-intentar recuperar offsets/sources exactos de dampers/anims desde un `.p3d`
  binarizado v55 hasta que el lector se arregle — es un agujero de reverse-engineering
  que ya costó tiempo dos veces.
- Vías alternativas: recuperar esas anims inspeccionando el binarizado **después** del
  rebuild propio, o tratarlas como cosméticas diferibles (R26: no fabricar a ojo).
- Dependencia del reader: `odol_reader.py` necesita sus módulos hermanos
  (`math_types.py`, `bis_reader.py`, `lzo_decompress.py`) en la misma carpeta
  de scripts del conversor externo. Copiar el script suelto falla (le pasó a Codex).

Propuesta pendiente (NO aplicada — el `SKILL.md` del conversor está en ruta
`skills-plugin` read-only desde sandbox): replicar esta limitación dentro del propio
SKILL.md vía una sesión con acceso de escritura al plugin (o draft en `skills-drafts/`).
Cross-ref introspección [`30_Sessions/2026-05-25-introspeccion.md`](../30_Sessions/2026-05-25-introspeccion.md) §2.5, PB-010.

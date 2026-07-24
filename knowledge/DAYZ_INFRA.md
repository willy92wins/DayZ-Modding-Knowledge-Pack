# DayZ environment & infra (L2)

Datos de infraestructura del workflow DayZ. Aplican a cualquier mod, no son
específicos de Crate ni LFPowerGrid. Adoptados de Agentic-Z 2026-05-04 y
verificados en el árbol vanilla local.

Este archivo se extrajo de CLAUDE.md (2026-05-09) para mantener el archivo
principal por debajo del sweet spot de ~300 líneas. Cargar on-demand cuando
una tarea toque infra DayZ (build, deploy, server config, terrain).

## Layout de drives y mods

- **`P:\` ES UN SYMLINK A `<dayz-projects>\`** (ya
  documentado en "Cheatsheet de paths"). DayZ Tools / AddonBuilder / Buldozer
  exigen el work drive como `P:\`.
- **`P:\Mods\` debe ser un directory junction al `!Workshop\` del DayZ instalado**
  (no una carpeta normal). El engine y el Launcher leen los mods desde
  `<DayZ install>\!Workshop\`. El junction permite desplegar PBOs como
  `P:\Mods\@<ModName>\Addons\<ModName>.pbo` y que aterricen donde el engine los
  busca:

  ```cmd
  cmd /c mklink /J P:\Mods "C:\Program Files (x86)\Steam\steamapps\common\DayZ\!Workshop"
  ```

  No requiere admin. Verificar antes de cada build PBO. Si `P:\Mods\` existe
  como carpeta normal, hay que borrarla primero (`rmdir /S /Q`).
- **Vanilla data candidates en `P:\`**: `P:\dz`, `P:\DZ`, `P:\dta` — el primero
  que exista es el bueno. Verificado: en este equipo `P:\dz` y `P:\DZ` existen.
- **Convención de mod source**: `P:\<ModName>\` como junction a la carpeta
  editable real (típicamente fuera de OneDrive si quieres evitar la regla
  OneDrive race). AddonBuilder lee de `P:\<ModName>\`, tú editas en la carpeta
  real, y el `$PBOPREFIX$` resuelve relativo a `P:\`.
- **Naming de mods**: `[A-Za-z][A-Za-z0-9_]{0,63}`. **Sin guiones** (el nombre
  dobla como identificador C-style en `CfgPatches`). `Mi-Mod` no parsea, usar
  `Mi_Mod` o `MiMod`.

## Diag binary obligatorio para iteración

- **Cliente y server tienen que ser `DayZDiag_x64.exe`**, NO los binarios retail.
  Razón: con `-filePatching` (necesario para que el engine lea `.cpp`/`.c` raw del
  source) los retail (`DayZ_x64.exe` cliente y `DayZServer_x64.exe`) bloquean
  past-loading-screen. El mismo `DayZDiag_x64.exe` corre en modo cliente o
  server según le pases o no `-server`.
- **DayZ Server install (Steam appid 223350) NO es necesario para iterar** — solo
  para el bootstrap inicial del mission template (ej. `dayzOffline.chernarusplus`).
  Tras copiarlo al workspace, se puede desinstalar.
- **Display flags del cliente**: `-window`, `-x=<width>`, `-y=<height>` — útil
  para iterar sin pelearse con fullscreen ultrawide. Default cómodo: 1920x1080
  windowed.

## `serverDZ.cfg` — `allowFilePatching = 1;` obligatorio

Si el cliente conecta con `-filePatching` y el server NO tiene
`allowFilePatching = 1;`, BattlEye rechaza con código `0x00020005`:
*"The server does not support the client's current filePatching setting"*.

```
// serverDZ.cfg
allowFilePatching = 1;
```

Sólo se baja a `0` cuando subes el server a producción real (sin iteración de
script live).

## VPP AdminTools — acceso admin en dev (`vppDisablePassword`)

Problema recurrente: VPP pide password al activar modo admin (tecla End) y lo
rechaza aunque el SteamID esté en `Permissions\SuperAdmins\SuperAdmins.txt`.
Verificado extrayendo el source de VPP (`PermissionManager.c`, `missionServer.c`,
2026-06-09):

- Superadmins se leen de `<profile>\VPPAdminTools\Permissions\SuperAdmins\SuperAdmins.txt`
  (uno por línea). El `SuperAdmins.json` root es de la versión vieja — no se usa.
- El **Steam API key NO es necesario** para superadmin (`SteamAPI.json` vacío es
  no-fatal; el log "Adding Super Admin" precede al error de SteamAPI).
- Login = `SHA256(password)` vs `Permissions\credentials.txt` (≤32 chars → VPP lo
  hashea y reescribe en boot; ==64 chars → lo usa como hash directo). Tras el match,
  `EnableToggles` usa `HasUserGroup`, que devuelve true para superadmins.

**Solución para dev (la buena — no pelear con credentials.txt):** en `serverDZ.cfg`:

```
vppDisablePassword = 1;
```

`missionServer.c:14` → `if (ServerConfigGetInt("vppDisablePassword")>0) DisablePasswordProtection(true)`
→ VPP no pide password; el superadmin (SteamID en SuperAdmins.txt) entra directo.
Keybinds VPP por defecto: `kHome`=Open Menu, `kEnd`=Toggle Admin (rebindeables en
Opciones→Controles si el perfil cliente se regeneró sin ellos).

## Comandos de invocación canónicos

**AddonBuilder** (build PBO):

```cmd
AddonBuilder.exe P:\<ModName> P:\Mods\@<ModName>\Addons ^
    -prefix=<ModName> -temp=P:\temp\<ModName> [-clear]
```

`-clear` wipea el target dir antes de buildear (útil en refactors grandes /
chasing stale assets).

**Gotchas de build verificados (added 2026-06-10, sesión LFGungame):**

- **AddonBuilder limpia su `-temp` ANTES de copiar** ("Clearing temp folder" en su log) y
  el default es `P:\temp\<mod>`. `P:\temp` y `P:\TEMP` son el MISMO path (Windows
  case-insensitive): un staging de fuentes bajo `P:\TEMP\<X>` con `-temp=P:\temp\<X>`
  hace que AddonBuilder BORRE el staging entero y falle con "Copy failed" (y exit 0 en
  algunos paths de error — el log es la verdad, no el exit code). NUNCA colocar staging
  ni fuentes bajo `P:\temp\*` / `P:\TEMP\*`.
- **Sin `-clear` el sync de `-temp` es INCREMENTAL y puede servir fuente STALE** (added
  2026-06-18, sesión LFPowerGrid perf-audit). Solo con `-clear` AddonBuilder loguea
  "Clearing temp folder"; sin él hace "Syncing folders" incremental y un `.c` cambiado
  puede NO re-copiarse. Caso real: `LFPG_DeviceInspector.c` quedó con copia de ~2 meses
  en `P:\temp\LFPowerGrid\` → cada build (packonly y binarize) empaquetó código viejo, el
  diag compiló la versión antigua, y un fix aplicado + verificado en disco "no tomaba"
  durante varios rebuilds. Filepatching NO salvó el caso (no sobreescribió los `.c` de la
  PBO con los sueltos del work drive). Síntoma canónico: un error de compilación que
  persiste idéntico tras editar + verificar la fuente. Mitigación: `dayz-test.ps1` ahora
  borra `P:\temp\<Mod>` antes de cada build; a mano, usar `-clear` o borrar la temp.
- **CfgConvert `-dst` falla SILENCIOSO (exit 0, sin output) con args quoteados** vía
  `Start-Process -ArgumentList` (comillas anidadas). Patrón fiable: `-WorkingDirectory`
  en la carpeta del config + paths RELATIVOS sin comillas
  (`-bin -dst config.bin config.cpp`). Validar SIEMPRE el output por
  timestamp+ubicación exacta, no por "existe un archivo con ese nombre" (LL-135: un
  config.bin de 2024 en el cwd casi acaba dentro del PBO del día).
- **Pipeline pack-only validado in-game (LFGungame, RPT 06-02)** para mods de scripts
  puros: (1) copia limpia de fuentes SIN `*.pbo`/`*.bisign` (robocopy `/XF`); (2)
  `CfgConvert -bin -dst config.bin config.cpp` y retirar `config.cpp` + `mod.cpp` del
  staging (el PBO desplegable NO los lleva; `mod.cpp` va suelto en `@Mod\`); (3)
  `FileBank.exe -property prefix=<Mod> -property "product=dayz ugc" <carpeta>` → genera
  `<carpeta>.pbo` al lado. Verificación: parse del header (properties + lista de
  archivos vs el PBO validado anterior) + grep binario de símbolos nuevos + firma
  `\0raP` del config.bin. FileBank NO compila los `.c` — el primer compile-check real
  es el RPT del arranque.

**Server diag**:

```cmd
DayZDiag_x64.exe -server ^
    -config=workspace\_server\maps\<map>\serverDZ.cfg ^
    -profiles=workspace\_server\maps\<map>\profiles ^
    -mission=<absolute-path-to-mission-template> ^
    -mod=@Mod1;@Mod2 ^
    -filePatching -port=2302
```

**Crítico**: `-mission=<absolute path>` debe ser absoluta. Si la omites el engine
busca en `mpmissions/` del binario (no existe en el DayZ install) y el server
arranca con mission vacía → log dice *"Mission script has no main function.
PlayerConnect will stay disabled"*.

**Cliente diag**:

```cmd
DayZDiag_x64.exe -profiles=workspace\_server\!ClientDiagLogs ^
    -mod=@Mod1;@Mod2 -connect=127.0.0.1 -port=2302 -filePatching
```

`-profiles=` apuntando a una carpeta dedicada contiene todos los artifacts diag
(Users/, DataCache/, BattlEye/, RPT, script.log) en un solo sitio.

## Mission templates — aliases canónicos

| Alias corto | Mission folder |
|---|---|
| `chernarus` | `dayzOffline.chernarusplus` |
| `livonia` | `dayzOffline.enoch` |
| `sakhal` | `dayzOffline.sakhal` |
| custom | el nombre real de la carpeta (ej. `dayzOffline.namalsk`) |

## Variables de entorno opcionales (resolvers)

Por si tu install vive fuera de los defaults Steam. Resolution order: env var
→ registry (Tools only) → fallback común.

| Variable | Apunta a | Usado por |
|---|---|---|
| `DAYZ_TOOLS_PATH` | DayZ Tools install root (parent de `Bin\AddonBuilder\AddonBuilder.exe`) | Build, preflight |
| `DAYZ_GAME_PATH` | DayZ game install (con `DayZ_x64.exe` y `DayZDiag_x64.exe`) | Launch-test |
| `DAYZ_DIAG_PATH` | Path directo a `DayZDiag_x64.exe` | Launch-test (override) |
| `DAYZ_VANILLA_DATA_PATH` | Folder con vanilla extraído (`P:\dz`, `P:\DZ`, `P:\dta`) | Preflight, lookup configs |
| `DAYZ_WORK_DRIVE` | Folder a montar como `P:\` | Mount script |

## Texturas — sufijos requeridos

Las texturas referenciadas en `.rvmat` y `config.cpp` deben usar los sufijos
canónicos. ImageToPAA valida esto al convertir desde PNG/TGA. Texturas en
**power-of-two dimensions** (1024x1024, 512x512, etc.).

| Sufijo | Para qué |
|---|---|
| `_co` | Color (diffuse) |
| `_nohq` | Normal map |
| `_smdi` | Spec/mask |

## `.p3d` named properties — los que importan

Set en Object Builder via *Edit → Named Properties*:

| Property | Valor típico | Para qué |
|---|---|---|
| `autocenter` | `0` | Items en mano: el grip point NO se recentra al cargar el modelo |
| `mass` | (kg) | Geometry LOD: physics weight |
| `mapType` | `building`, `vehicle`, etc. | Icono que aparece en mapa in-game |
| `class` | `house`, `car`, etc. | Categoría de comportamiento engine |
| `damage` | named selection | Define damage zone |

## Server / Central Economy — archivos relevantes

Layout estándar bajo `<mission>/`:

| Archivo | Función |
|---|---|
| `init.c` | Server-side mission entrypoint. `main()` obligatorio (si falta → "PlayerConnect will stay disabled" en RPT) |
| `cfgeconomycore.xml` | Estructura del CE (apunta a archivos de tipos) |
| `db/types.xml` | Spawn rates, lifetimes, locations |
| `db/events.xml` | Custom dynamic events (heli crashes, infected hordes, etc.) |
| `cfgeventspawns.xml` | Spawn positions de eventos |
| `cfgspawnabletypes.xml` | Items que aparecen como contenido de eventos |
| `cfggameplay.json` | Runtime tuning (movement, stamina, environment) |
| `cfgweather.xml` | Weather config (XML: `<weather reset= enable=>` + overcast/fog/rain/wind/storm). NO es `.json` (errata corregida 2026-07-06 contra wiki DayZ:Weather_Configuration) |
| `globals.xml` | Variables globales del CE |
| `mapgroupproto.xml` + `mapgrouppos.xml` | Loot tier locations (military, residential, etc.) |
| `storage_1/` | Persistencia activa. **Backup ANTES de tocar economía.** |

## BattlEye — códigos de kick más comunes

| Code | Causa típica | Fix |
|---|---|---|
| `0x00020005` | filePatching mismatch | `allowFilePatching = 1;` en serverDZ.cfg |
| `0x00010002` | Mismatched mod signatures | Reconstruir PBO con AddonBuilder, verificar `.bisign` |
| Public Variable Restriction | BattlEye filter detecta sync inesperado | Whitelist en `publicvariable.txt` |

## Cuándo cita el RPT que un script falla

- `script.log` → script side errors (compile + runtime)
- `<server>.RPT` / cliente RPT → engine-side errors (missing assets, malformed
  configs, access violations)
- `crash_<date>_<time>.log` → **excepciones manejadas, NO segfaults reales** (los
  crashes hard generan dump separado)

## Tooling realities

- **DayZ NO tiene runner de unit tests para Enforce Script.** La palanca de
  calidad es adherencia estricta a `enforce-script-reference` (style guide +
  pitfalls). Por eso R5 (agrupar tests in-game) — cada iteración es cara
  (rebuild PBO ~30s + connect ~30s + setup escenario 1-3 min).
- **`shutil.rmtree` en Windows recurre DENTRO de junction targets.** Si tienes
  `P:\<Mod>\` apuntando a fuente externa y haces `rmtree(P:\<Mod>)`, te lleva la
  fuente externa por delante. Para borrar junctions: `cmd /c rmdir <junction>`
  (no recurre, solo borra el link).

## Terrain / map (referencia rápida)

Pipeline básico:

| Archivo / paso | Función |
|---|---|
| Heightmap (`.png` / `.xyz`) | Terreno alturas |
| Satellite map | Color textura grande del terreno |
| Mask map | Asignación de surfaces por píxel |
| `layers.cfg` | Layer config — qué surface mappea a qué color del mask |

## Caveats de esta máquina (added 2026-06-11, sesión LFSlidingFloor)

- **DayZServer standalone (Steam, app 223350) NO completa la carga de misión en esta máquina NI EN VANILLA PURO**: cuelga tras cargar configs, sin error en logs, y muere ~6 min después con -freezecheck ("Termination successfully completed"). 4 runs verificados 2026-06-10. Para tests locales usar SIEMPRE la vía DayZDiag (skill dayz-test-ingame; tools por mod en `<Mod>_dev\tools\`). Su carpeta mpmissions sigue siendo útil como fuente de misiones para el -mission absoluto del diag.
- **Parsing de -mod del DayZServer standalone**: comillas embebidas en rutas con espacios PARTEN el valor (trata `"C:\Program` como nombre de mod; síntoma: `ANIMATION (E): Can't load "C:\Program...`). DayZDiag con el token -mod ENTERO entre comillas exteriores sí acepta rutas absolutas con espacios separadas por punto y coma. Solución general: junctions sin espacios (mklink /J) y rutas relativas al working dir.
- Junctions creados 2026-06-10 en la carpeta del DayZServer: `@CF` y `@VPPAdminTools` apuntando al !Workshop del cliente (para el .bat deprecated del server Steam; el flujo diag no los necesita).


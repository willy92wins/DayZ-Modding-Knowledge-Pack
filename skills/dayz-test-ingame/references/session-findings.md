# DayZ test-in-game — Session findings (dated appendices)

Extracted from dayz-test-ingame/SKILL.md 2026-07-07 (F3). Per-session in-game findings kept out of the core for length; each is verified and reusable across mods. The core skill links here from its "Session findings" index. Load on demand when a launch surfaces the matching symptom.

---

## Hallazgos sesión LFSlidingFloor (added 2026-06-11)

Origen: sesión 2026-06-10 (R21 + test in-game de 2 spikes). Cinco gotchas verificados del flujo diag:

- **Print() va a script_*.log, NO al RPT**: en DayZDiag los Print de script van SOLO al script log (retail server: RPT). Gates/monitores que digan "RPT" deben traducirse al runtime real. Sonda mínima: un Print en OnInit de un modded MissionServer confirma el sink Y el enganche del mod sin necesidad de cliente (ver LL-137).
- **-filePatching NO garantiza cargar los scripts del mod desde el work drive**: verificado 2026-06-10 — con -filePatching y un PBO vacío, los módulos compilaron SIN los archivos del mod y SIN error (World 2240 vs 2245 esperado). Detección: comparar los counts "Module: X; loaded Nx files" del script log contra un run de referencia (+N archivos del mod). Mitigación: -NoFilePatching (cargar SIEMPRE del PBO verificado por contenido).
- **VPPAdminTools REQUIERE @CF delante en -mod**: sin él, popup modal "Unknown type 'RPCManager'" (Can't compile Game module) que BLOQUEA el server esperando un click — sin traza útil si nadie mira el escritorio. Para leer diálogos invisibles: EnumWindows + GetWindowText vía PowerShell.
- **1 cuenta Steam = 1 cliente**: el segundo DayZDiag simultáneo (mismo SteamID, -name y -profiles distintos) recibe kick 179 "Ya se ha enviado una solicitud para esta SteamID". Tests de observador MP necesitan segunda cuenta o segundo PC.
- **El PBO desplegado queda LOCKED mientras el server corre**: AddonBuilder -clear y la copia final fallan ("Build failed" como última línea con el resto del log normal). Cerrar server y cliente ANTES de redeploy.

## Hallazgos sesión A6_SR2M grip — captura visual retail + Start-Process (added 2026-06-17)

Patrones reutilizables al testear in-game con **captura visual por cámara** (gate tipo `gate-mcp.ps1`:
retail server+client + camera bridge + window-grab por órbita). Independientes del mod.

**Captura visual (retail):**
- **Banda de brillo.** El mundo retail renderiza más brillante (~109–126) que la banda diag `[48,86]`,
  así que un gate de "in-world ready" por brillo da false-negative en retail y solo captura tras
  timeout. Usar una banda retail (p.ej. `[110,175]`) para que confirme rápido, o juzgar por contenido.
- **Glint especular.** Con sol directo (hora despejada) algunas armas/materiales se queman a blanco y
  tapan la mano/detalle. Fijar `overcast=1.0` (cielo cubierto → luz difusa, sin sol directo) lo elimina.
- **Deriva de exposición.** En runs largos la exposición deriva entre la primera captura y las últimas
  aunque la escena esté "congelada". Capturar todas las variantes RÁPIDO (ciclo corto) para exposición
  pareja entre ellas.
- **Desync en ciclos multi-config.** Si el timeout de "in-world ready" por config es MAYOR que el
  período con que el init cambia de config, la captura cae en la config SIGUIENTE (etiquetas corruptas
  — pasó en iter18). Mantener el timeout por config < período, y arrancar el ciclo solo tras el boot.
- **Check de RPT por errores.** NO incluir `"Can't load"` en el patrón de fallo: matchea el warning
  BENIGNO `Can't load @Mod/Anims/cfg/skeletons.anim.xml`, que sale para TODOS los mods (probe genérico
  per-mod). Buscar errores reales (`Unknown type`, `Cannot create`, `compile mission`) excluyendo
  `skeletons.anim.xml`.

- **Ventana del cliente DayZDiag se oculta sola (added 2026-08-22).** El proceso sigue vivo y
  respondiendo, pero la ventana pasa a `visible=False`; entonces `Get-Process().MainWindowHandle`
  devuelve **0** y cualquier script que dependa de él falla con "bad window rect 0 x 0". La
  ventana existe: hay que localizarla con `EnumWindows` filtrando por PID y descartar la del
  servidor por título (`*Console*`). En este host lo hace
  `ForzaDayZ\work\lfvui_spike\capture_loop.ps1`.
- **PrintWindow (PW_RENDERFULLCONTENT) dudoso para la capa de UI (added 2026-08-22).** Refresca
  la escena 3D, pero en una corrida de 49 fotogramas la región del HUD dio delta **exactamente
  0,00** mientras el usuario veía el elemento cambiar en la pantalla real. Un cero EXACTO en
  JPEG comprimido no es "casi igual", es el mismo pixel: sospechar del instrumento (`G3`).
  Para medir UI animada usar el ojo del usuario; PrintWindow queda para composición estática.
  No sustituir por `capture_screenshot` del MCP: es window-grab del host, no un comando del
  bridge (`dayz-mcp-verify/references/drive_ladder.py`). Origen: sonda LFVUI_Spike,
  `ForzaDayZ\work\lfvui_spike\caps\` (49 jpg) y `diff_frames.ps1` del mismo directorio.

**Start-Process en el PowerShell tool (`EPERM uv_spawn`).** Un comando inline con `Start-Process` dentro
de un `foreach` y `ArgumentList` con comillas-backtick (`` `"$x`" ``) dispara, de forma consistente,
`EPERM: operation not permitted, uv_spawn powershell.exe` (falla el spawn del shell, no el comando).
Fix: escribir el bucle a un `.ps1` de disco y ejecutarlo (`& script.ps1`), o usar
`Start-Process -ArgumentList @('a','b','c')` (array, sin backticks). Un solo `Start-Process` inline suele
ir; el `foreach` con backticks es el que rompe.

## Hallazgos sesión MercedesAMGLF Fase 0 (added 2026-06-22)

Dos patrones reutilizables al estrenar este harness en un mod nuevo. Origen: import MercedesAMGLF, R21 del harness.

### Patrón mount-probe — gate de Fase 0, más barato que el autotest de física

Para la primera validación build→deploy→mount de un mod nuevo, antes de que exista modelo o física, no uses el autotest de física (spawn + medición): usa una sonda de montaje mínima.

1. Stub solo-`CfgPatches` (`config.cpp` con `class CfgPatches { class <Mod> { requiredAddons[]={"DZ_Data"}; }; }` + `$PBOPREFIX$`), build con `-packonly`.
2. `dayz-test.ps1 -Mod <Mod> -Source <stub> -Mode server -Build -NoBaseMods` (aísla; el stub solo requiere vanilla).
3. Misión cuyo `init.c` es un `MissionServer` mínimo que en el primer `OnUpdate` (one-shot con flag) corre `GetGame().ConfigIsExisting("CfgPatches <Mod>")` e imprime `[<MOD>-MOUNT] CfgPatches.<Mod>=0|1`. Forma de la API verificada en vanilla: `g_Game.ConfigIsExisting(CFG_VEHICLESPATH+" "+type)` en `P:\scripts\4_world\systems\inventory\attachmentsoutofreach.c:89` (path con espacio).
4. Poll del `script*.log` por `[<MOD>-MOUNT]` + `BankRev -lf` del PBO desplegado para listar contenido.

Clave de velocidad: un `void main()` vacío en el `init.c` (reemplaza el vanilla) salta `CreateHive()`/CE, así el mission loop arranca en segundos en vez de minutos (no carga ~20k items de loot). La sonda no necesita cliente, a diferencia del spawn de un `CarScript`. Verificado: AC0.1 MercedesAMGLF 2026-06-22, probe a ~50s, server-only headless, runner `dayz-mount-probe.ps1`.

### Retargetar el autotest de física de LFQuad a un mod nuevo — trampas de acoplamiento

`dayz-autotest.ps1` / `autospawn_init.c` / `*_verdict.py` heredados de LFQuad traen acoplamiento que rompe en silencio al copiarlos a otro vehículo. Verificado por R21 en MercedesAMGLF; antes de fiarte del arnés retargetado, revisa los cuatro:

- **No spawnea en server-only.** `autospawn_init.c` gatea el spawn a `players >= 1` (un `CarScript` solo simula con jugador presente). En server-only por defecto nunca spawnea → timeout sin muestras. Haz `-WithClient` default/obligatorio para la corrida de física, o falla temprano si no hay cliente.
- **El dev build-gate exige un token de debug inexistente.** `Invoke-BuildGate` llama `Require-PboToken -Token '<MOD>-DBG'`; ese token venía de instrumentación in-vehicle de LFQuad. Un mod limpio no lo tiene, y no se mete debug a producción → el gate aborta un build válido. Sustituye por evidencia productiva (presencia de los `.c`/config esperados vía `BankRev -lf`).
- **El verdict inline de PowerShell no valida el vehículo de control.** El bloque de veredicto del `.ps1` calcula PASS solo con el subject; el `*_verdict.py` sí exige que el control settle (INVALID-RUN si no). Como el `.ps1` no invoca al `.py`, puede dar PASS con el control ausente/roto y perder el valor del control negativo. Que el `.ps1` invoque al `.py` y respete su exit code, o porta el gate del control al PowerShell.
- **`-replace` de PowerShell es case-insensitive por defecto.** Retargetar `'LFQuad'`→`'<Mod>'` también reescribe `LFQUAD-DBG`→`<Mod>-DBG` y `[LFQUAD-DBG]`→`[<Mod>-DBG]`. Verifica los tokens tras el retarget (o usa `-creplace` para los case-sensitive).


## RETARGETING THE HARNESS TO A NEW MOD (added 2026-06-23)

`dayz-test.ps1` is fully car-parametric (it takes `-Mod` and has zero hardcoded mod tokens) — copy it
verbatim into a new mod's `tools` folder. Only the per-mod helpers carry the old mod name and need a
case-sensitive token swap: `dayz-autotest.ps1`, the mount probe (`dayz-mount-probe.ps1` plus
`mount_probe_init.c`, including its bracketed `MOD-MOUNT` print token), `autospawn_init.c` (the classname
and the `MOD_Wheel` attachments), the verdict parser (`mod_verdict.py`), and the `server`/`client`/`offline`
.bat wrappers (`set MOD=`). Generic p3d utilities (`lfq_*.py`, `fix_firegeo_mass.py`,
`measure_wheel_geometry.py`) copy verbatim.

Retarget host-direct (PowerShell `-creplace` plus `[System.IO.File]::WriteAllText` with UTF8-no-BOM), NOT
the bash sandbox (bindfs cache) and NOT the Write/Edit tool on a OneDrive `.py` (null-byte risk). After the
swap, grep the destination for residual old-mod tokens — it MUST be zero — and confirm the new tokens
landed (wheel attachment, classname, probe token, `set MOD=`). The CONTROL (`CivilianSedan`) is shared
across mods and never changes. Origin: SUB_BRZ harness retargeted from MERCEDES_AMGLF with 0 residuals.

## THE DAYZ BOX IS A SINGLE EXCLUSIVE RESOURCE ACROSS SESSIONS (added 2026-06-24)

One Windows box runs one DayZ instance at a time: a server binds UDP **2302**, and one Steam account = one client
(a second client gets kick **179**, already noted under LFSlidingFloor findings). This bites hardest with multiple
concurrent Cowork sessions each testing a different mod: every `dayz-test.ps1` launch runs `-Kill` (kills ALL
`DayZDiag_x64`) before starting, so whichever session launches last EVICTS the others — their server+client die
mid-CE. The readiness window (build + CE boot, 2-4 min) does not fit inside the ~1-min eviction cadence, so a smoke
can never complete while a second session keeps relaunching. The dayz-mcp `--client`/broker registration lets several
sessions hold MCP tools at once, but it does NOT share the game — it does not solve this.

Rule before launching when other sessions may be open: ensure EXACTLY ONE Cowork session owns the box. Kill residual
`DayZDiag_x64`, then watch ~40 s host-direct (PowerShell) for any relaunch — a foreign `DayZDiag` reappearing means
another session is still alive (its cmdline shows the other `@Mod`/profiles; trace its parent). After your own launch
connects, confirm the live `DayZDiag` cmdlines reference YOUR mod before trusting anything you observe. Origin:
MERCEDES_AMGLF Fase 2 smoke 2026-06-24 (SUB_BRZ + LFInfectedBig sessions evicted the box repeatedly; PIDs/start-times
flipped every ~1 min).

**Pre-launch ownership check (added 2026-06-28, MANDATORY — origin: a SUB_BRZ session blind-killed A6_SR2M's
dedicated server, evicting an active session, then a foreign relaunch killed the SUB_BRZ server mid-test).**
NEVER `-Kill` / blind-kill before checking who holds the box. Before any kill or launch:
1. List holders host-direct: `Get-CimInstance Win32_Process -Filter "Name='DayZDiag_x64.exe' OR Name='DayZServer_x64.exe'"`
   and read each `.CommandLine` for its `@<Mod>` token and `-profiles=...<OtherMod>_dev` path. Also check
   `Get-NetUDPEndpoint -LocalPort 2302` for the actual binder.
2. If ANY holder references a DIFFERENT mod than the one you are testing → it is another live Cowork session.
   **Do NOT kill it.** Surface to the user ("2302 lo tiene @<OtherMod>; ¿lo mato o esa sesión está activa?") and
   wait for confirmation before evicting. Only auto-kill processes that are clearly YOURS (same `@<Mod>`) or
   confirmed stale by the user.
3. `DayZServer_x64.exe` (retail/dedicated binary) is a SEPARATE process from `DayZDiag_x64`: a DayZDiag-only kill
   misses it, and killing it evicts a retail-mode session. Cover both names when you legitimately clean up.
4. Killing a foreign DayZServer mid-write corrupts the shared `DayZServer\mpmissions\<mission>\storage_1` CE
   persistence → next boot dies on `!!! Serious stream damage detected during load` and exits before UDP bind.
   Remedy: rename `storage_1` (server regenerates a fresh one); better: don't kill foreign servers in the first place.
5. After your own launch binds, confirm the live cmdline references YOUR `@<Mod>` before trusting any in-game observation.


## (added 2026-06-26) Mods con dependencias en `@<Mod>_deps` separado: incluirlas en el modset

Si el mod tiene sus dependencias en un addon SEPARADO (`@<Mod>_deps`, no bundled en `@<Mod>`), el modset del launch DEBE incluirlas o el cliente falla a compilar scripts: `Can't compile "World": Unknown type '<BaseClass>'`. Las dependencias (clases base de config y de script) deben cargar ANTES del mod → ponerlas en `-BaseMods` (que va primero en el `-mod=`), no en `-ExtraMods` (que va después del mod).

Antes de relanzar un mod ya testeado, no asumas el `-BaseMods` por defecto: lee el `-mod=` del último RPT/output exitoso (`<Mod>_dev\_client\profiles\*.RPT`, línea "Launch CLIENT") y replica ESE modset.

Ejemplo real (A6_SR2M, 2026-06-26): lanzar sin `@A6_SR2M_deps` → `Unknown type 'A6_Optic_Mount_Base' (a6_sr2m.c:77)` / "Can't compile World". Correcto: `-BaseMods "@CF;@Dabs Framework;@VPPAdminTools;@A6_SR2M_deps"`. Nota Windows: `P:\` puede no estar montado en una sesión nueva → `subst P: "<ruta real del work drive>"` antes de build/launch.

## (added 2026-06-28) Deps de terceros con scripts "sloppy": usar `-Retail -NoFilePatching`

Si una dependencia de terceros (no tuya, p.ej. un pack A6) emite `SCRIPT (W)` (warnings) en
retail pero `SCRIPT (E)` FATALES en DayZDiag (llaves sin cerrar, "missing function scope",
"Opened scope at the end of file"), el path de test con filePatching NO sirve por DOS lados:

- **DayZDiag** es mas estricto: esos warnings de retail son errores fatales -> `Can't compile
  "World" script module!` -> el server Diag muere ("Server process exited before binding").
- **Cliente retail + `-filePatching`** -> crashea al CONECTAR: `Unhandled exception ... Access
  violation. Illegal read ... at 0x0` con callstack `CDPInitServer`/`CDPCreateClient`
  (minidump + `crash_*.log` en `_client\profiles`). El server queda sano (`is connected`
  seguido de `[Disconnect] -1`).

**Fix:** si tu cambio ya esta empaquetado en el PBO (no necesitas hot-reload de scripts),
lanza con **`-Retail -NoFilePatching`**. filePatching es innecesario con el PBO al dia, y
quitarlo evita ambos fallos. La replica de produccion (PBO + sin filePatching) es ademas la
config con la que el mod corre en un dedicado real.

```
dayz-test.ps1 -Mod <Mod> -Mode all -Retail -NoFilePatching -BaseMods "@CF;@Dabs Framework;@VPPAdminTools;@<Mod>_deps"
```

Verificar conexion sin OCR: `Select-String 'is connected'` en el RPT del server (señal
autoritativa) y `crash_*.log` nuevos en el profile del cliente para el fallo (PowerShell
host-direct, no Monitor bash -> bindfs cache, LL-142). Origen: A6_SR2M bug#10, 2026-06-28.

## (added 2026-06-28) Lanzar DayZDiag desde el agente: usar `cmd start`, NO una tarea background — y el bind-wait da falso-negativo

Tres gotchas verificados al conducir un smoke in-game DESDE el agente (tool calls), no a mano. Origen:
SUB_BRZ Fase 5 smoke 2026-06-28 (costó ~media sesión). Cross-ref LL-168.

- **Un `DayZDiag_x64.exe` arrancado con `Start-Process` desde una tarea `run_in_background` del agente
  (o desde el propio bind-wait de `dayz-test.ps1` corrido en background) MUERE cuando esa tarea/job
  termina.** El harness mata los procesos hijos del job al cerrarlo: el server cae a mitad del CE **SIN
  dejar RPT propio** (bindea 2302 y desaparece), y el cliente —si se lanzó en otra llamada— sobrevive
  (síntoma: `DayZDiag count = 1`, server muerto). Confirmado x3. La nota previa "Start-Process -PassThru
  sin -Wait" NO basta cuando la llamada corre en background. **Fix: lanzar server y cliente vía un `.bat`
  con `start ""`** (grupo de procesos independiente, fuera del árbol del agente) — sobreviven a través de
  las tool calls y escriben su RPT. Patrón: `srv.bat`+`cli.bat` con `start "" "DayZDiag.exe" -server ...`
  / `... -connect=127.0.0.1`, mismo modset (`-mod="...;@<Mod>;@DayZ_MCP"` con paths absolutos `!Workshop`).
  Pollear el bind uno mismo (`Get-NetUDPEndpoint -LocalPort 2302`); para esperar connect usar un poller
  **read-only** (sin `Start-Process` dentro, o al cerrar mataría el juego).
- **El bind-wait de `dayz-test.ps1` da FALSO-NEGATIVO** (visto a 240s): el server SÍ bindeó 2302
  (`Get-NetUDPEndpoint` lo confirma) pero el orchestrator "Timed out waiting for bind" → rehúsa lanzar el
  cliente Y mata el server que había lanzado. Workaround: dejar que `-Build` construya el PBO (eso sí
  funciona), ignorar el fallo de launch, y lanzar server+cliente a mano por `.bat`.
- **El bridge MCP `version_state=legacy_blocked` ("poll did not include ver=") es solo init incompleto**,
  NO un mismatch de versión: pasa a `ok` cuando el mission del server carga del todo (~1-2 min). No
  re-registres el server ni redepliegues por eso — espera y re-chequea `bridge_status` (refina la fila
  homónima de la skill `dayz-mcp-verify`).

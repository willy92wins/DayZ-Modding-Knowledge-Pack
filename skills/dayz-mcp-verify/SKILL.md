---
name: dayz-mcp-verify
description: >
  Auto-test a DayZ mod in-game through dayz-mcp without keyboard or OCR:
  spawn a classname, orbit/capture, raycast collision, inspect
  placement/attachments/telemetry and emit PNG+JSON evidence. Compose with
  dayz-test-ingame; dayz_test_run/dayz_test_stop own the managed lifecycle,
  then this skill drives the bridge. Use for "auto-probar el mod", "verificar
  in-game con MCP", visual smoke/re-test, "comprobar que el .p3d carga/se
  ve/colisiona", automated spawn+capture+raycast, or the vehicle acceptance
  ladder (spawn→render→get-in→drive→wheel direction). Covers static objects,
  items/weapons, buildings without doors and vehicle placement/drivability.
  Player UI, door interaction, inventory use and firing remain manual.
---

# DayZ MCP verify — auto-test in-game vía tools MCP

## GATE 0 — preguntar QUIÉN conduce, antes de tocar nada (added 2026-08-07)

**Antes de la primera tool de `dayz-mcp` en una tanda de verificación, preguntar al usuario si
conduce él o el MCP.** No se asume ninguno de los dos. Una sola pregunta por tanda, no por
captura.

Por qué es un gate y no una preferencia: **con el usuario delante, su ciclo manual es más rápido
y da mejor resultado** — spawnea con VPP en segundos y juzga la escena entera de un vistazo,
mientras que el lazo MCP necesita colocar cámara, capturar y encadenar tools. El MCP gana cuando
el usuario NO está: madrugada, tanda desatendida, o mientras atiende otro frente. Además el
cambio de modo no es gratis a mitad de camino (el test manual limpio pide relanzar sin
`@DayZ_MCP`), así que la decisión se toma al principio del ciclo o se paga dos veces.

| Situación | Quién conduce |
|---|---|
| Usuario presente y disponible | **Él** (VPP + juicio directo) — el MCP solo si él lo pide |
| Usuario ausente / tanda desatendida | **MCP**, y se le deja el reporte con evidencia |
| Duda | **Preguntar.** Nunca asumir |

Lo que NO cambia: el MCP sigue siendo obligatorio para lo que un humano no puede medir a ojo
(telemetría, raycast numérico, placement exacto, series repetibles). Ahí no se pregunta, se usa.

Medición que originó el gate (2026-08-07, corpus de 276 sesiones): el 63% del reloj de un ciclo
completo cae del lado del usuario, y el 71% de sus verificaciones reales son automatizables con
las tools de hoy. Que sea automatizable no implica que convenga automatizarlo: con él delante,
manda su ciclo.

## WHAT THIS DOES

Conduce un cliente DayZDiag ya lanzado, vía las tools del servidor MCP `dayz-mcp`, para
verificar un mod sin intervención humana: spawnea el objeto, lo mira desde varios ángulos
(cámara + window-grab), comprueba su colisión por raycast, lee su placement/telemetría, y
produce un reporte con criterios pass/fail y evidencia. Es el lazo de **observación**
automatizada que cierra el hueco entre "el PBO compila/despliega" y "se ve y se comporta bien
in-game", para la clase de propiedades que NO requieren input de teclado.

Server-authoritative + captura pasiva por píxeles. El control y los datos son engine-native
(spawn, raycast, telemetría, cámara); la única pieza no-native es la captura visual
(window-grab del cliente renderizado — `MakeScreenshot` está roto en diag, T165276).

## COMPOSICIÓN — lifecycle público + verificación MCP

El build/deploy/launch es de **`dayz-test-ingame`** (su preflight de entorno corre solito:
`P:\` montado, junction `P:\Mods`, AddonBuilder, `allowFilePatching`). Esta skill lo invoca
con el mod MCP añadido y luego conduce. Los verbos de bridge no arrancan ni terminan
procesos; las herramientas públicas de test sí orquestan el lifecycle gestionado.

Antes del flujo operativo, leer el protocolo canónico:
`<runbooks>\dayz-mcp-agent-session-protocol.md`.
[EXACT][CLAIM-R21-MCP-ORCHESTRATED-TEST] Ejecuta el lifecycle con
`dayz_test_run` y detenlo con `dayz_test_stop` sobre el `run_id` exacto. Ambas
herramientas poseen cola FIFO, lease, heartbeat y release; no las envuelvas en
un segundo `session_acquire`. Reserva las primitivas `session_*` para
mutaciones de bajo nivel que no estén ya encapsuladas. Todo lifecycle se
identifica por `run_id`: compartir mod no concede ownership. Con cuarentena
retail solo se permiten lecturas; si quien abrió retail no puede cerrarlo por
la UI, declarar `manual_cleanup_required`.

### Companion externo: dayz-labs

[EXACT][CLAIM-R21-MCP-COMPANION-AUTHORITY]
`external_companion_no_lifecycle_authority`. La release dayz-labs v0.1.35,
revisada en el commit fijado
`dbd6ad3e54e30c81a9aeb88fcb9f60f007804c2a`, puede servir como referencia o
companion opcional. Sus verbos `start/stop/restart` quedan excluidos mientras
DayZ_MCP posee un run: solo `dayz_test_run` / `dayz_test_stop` sobre el
`run_id` exacto gobiernan ese lifecycle. No instales ni actualices el companion
como parte de un gate; documenta siempre la `pinned_version` examinada.

Su interfaz es WPF y captura su propia aplicación:
`wpf_not_layout_evidence`. Una captura correcta de dayz-labs no valida el
parser, las proporciones, el clipping ni la semántica de un `.layout` DayZ; el
visor UI necesita su propio render y comparación contra evidencia del juego.

El request de `dayz_test_run` debe seleccionar `Mode=all`, build cuando cambió
el PBO y `@DayZ_MCP` como dependencia adicional:

- `-Mode all` (server + cliente) es OBLIGATORIO: la captura visual lee del **cliente
  renderizado**. Un `-Mode server` headless no tiene ventana que grabbear.
- `@DayZ_MCP` se carga junto al mod bajo test; ambos peers (server + client bridge) pollean al
  loopback del server MCP.

## PREREQUISITES (gate antes de conducir)

1. **`dayz-mcp` registrado y conectable.** Gate PRIMARIO: ¿están disponibles las tools
   `mcp__dayz-mcp__*` en la sesión? (ToolSearch las encuentra → gate PASS). `claude mcp list` es
   SECUNDARIO y NO fiable: da falsos `× Failed to connect` con el server operativo — no bloquear
   por él si ToolSearch ve las tools. Las tools solo están disponibles en una sesión que arrancó
   CON el server ya registrado (registro broker `--client`, ver TROUBLESHOOTING).
2. **Config del bridge sembrada.** El bridge in-game lee `dayz_mcp.json` (url + key + pollHz) de
   sus profiles; el server MCP usa `<DayZ_MCP_dev>\tools\.dayz_mcp.key`. Sembrar la MISMA key en
   los profiles del launch con `install-mcp.ps1` apuntando a los dirs que `dayz-test.ps1` genera:

   ```powershell
   <DayZ_MCP_dev>\tools\install-mcp.ps1 `
     -ServerProfiles "<TargetMod>_dev\_server\profiles" `
     -ClientProfiles "<TargetMod>_dev\_client\profiles" `
     -MissionPath "<...>\mpmissions\dayzOffline.chernarusplus"
   ```

   `[verify on first run]` — el seeding genérico (mod arbitrario + `@DayZ_MCP` vía
   `dayz-test.ps1`) hasta ahora solo se ejerció a través de `run-fase3.ps1`. La PRIMERA corrida
   de esta skill valida que el bridge encuentra la config en estos paths; si `bridge_status`
   reporta `last_poll_age_s = null`, la config no está donde el bridge la busca — ajustar el
   path y declararlo.
3. **`bridge_status` verde.** Primera llamada SIEMPRE: `bridge_status`. El `server_peer` debe
   tener `last_poll_age_s` fresco (no null). Para captura, el `client_peer` también. `never
   polled` → el bridge no arrancó (config/key/arranque) → abortar y diagnosticar, no seguir
   conduciendo a ciegas.
4. **Los mods que pases por `extra_mods`/`base_mods` deben ser DIRECTORIO REAL bajo `P:\Mods`
   (→ `!Workshop`); las junctions de Steam NO valen.** Dos capas, y confundirlas cuesta una sesión:
   - La frontera pública `_valid_public_mod` (`DayZ_MCP_dev\tools\dayz_mcp\dayz_test_tool.py:75-85`)
     rechaza `:`, `\` y `/` en **todos** los proyectos → una ruta absoluta de workshop no pasa nunca
     por la tool. Eso es diseño, NO una laguna de la policy de tu proyecto.
   - Los mods suscritos que Steam expone en `!Workshop` (`@CF`, `@Dabs Framework`,
     `@VPPAdminTools`) son **Junctions** a `steamapps\workshop\content\221100\<id>`, y el guard de
     identidad de rutas las rechaza → `dayz_test_failed`, que es el catch-all genérico de
     `server.py:1101` y **se traga la causa real**.

   **Consecuencia operativa**: CF/Dabs/VPP sólo se cargan declarándolos con **ruta absoluta** en el
   `default_base_mods` del proyecto dentro del `request-policy.json` del launcher — que es como los
   declaran SUB_BRZ y LFHeli. Los mods que son directorio real (`@DayZ_MCP`, `@LFHeliCore`, el mod
   bajo test) sí van por `extra_mods` con nombre relativo.

   Diagnóstico en un comando:
   `Get-Item '<!Workshop>\<@Mod>' -Force | Select-Object LinkType` → `Junction` = no sirve relativo.
   Medido 2026-08-02 con `preflight=true` (dry-check puro: `dayz_test_worker.py:533-534` retorna
   antes de build y de lanzar nada): sin mods OK · `@DayZ_MCP` OK · `@A6_SR2M` OK · `@CF` FAIL ·
   `base_mods=["@CF"]` FAIL.

   ⚠ **Antes de culpar al puente por `version_blocked`/`last_poll_age_s=null`**: comprueba que la
   `key` de `dayz_mcp.json` en los profiles del proyecto es la MISMA que
   `DayZ_MCP_dev\tools\.dayz_mcp.key`. Una key stale da 401 y el bridge no pollea nunca, con
   síntoma idéntico a "el mod no está cargado". Las rotaciones de key dejan atrás a los proyectos
   que no se ejercitaron desde entonces (2026-08-02: MERCEDES_AMGLF y LFPowerGrid con la vieja,
   SUB_BRZ/LFHeli/DayZ_MCP con la actual).

   ⚠⚠ **El síntoma NO siempre es `version_blocked` / `last_poll_age_s=null`** — y creer que sí
   cuesta la sesión igual (medido 2026-08-17 en LFPowerGrid, con este aviso ya escrito arriba y
   pasado por alto). Con la key stale el peer puede leerse **`version_state: ok` con
   `last_poll_age_s` de 1.485 s**: es el dato del ÚLTIMO sondeo bueno, que puede pertenecer a otra
   corrida ya muerta. Un puente muerto se lee así como sano. La firma que no engaña está en el
   script log del juego: `[MCP-POC] poll error=5` (server) / `[MCP-CLIENT] client poll error=5`
   (cliente). Ese **5 es `EREST_ERROR_CLIENTERROR`** (`scripts\3_game\http\restapi.c:16-17`), o sea
   el daemon devolvió 401 — el 401 NO aparece en ningún sitio del lado del juego.
   Gate de dos comandos antes de culpar a nada:
   - Comparar la key de **cada** `dayz_mcp.json` que el run vaya a usar contra el keyfile. Son dos
     rutas y `$profile:` gana a `$mission:` (`MCPBridge.c:145-149`, `MCPClientBridge.c:234-237`);
     si falta la de profiles, el bridge cae a la de la misión, que es la que suele quedar stale.
     Mismo largo (43) NO es prueba: comparar los bytes.
   - `Invoke-WebRequest "http://127.0.0.1:8765/poll?key=<contenido del keyfile>"` → 200
     `{"commands":[]}` demuestra que daemon y key viva están bien, y acota el fallo al JSON del run.
   **Y arreglarlo NO exige reiniciar el servidor**: `ReloadKeyAfterFailure` (`MCPBridge.c:373-398`)
   relee la key cuando el backoff toca techo. Corriges el JSON, esperas ~20 s, sale
   `[MCP-POC] poll key reloaded` y el peer vuelve a `last_poll_age_s` 0,2. Eso ahorra el boot.

   ⚠ **La aguja de spawn del jugador no puede presuponer el género.** El ejemplo
   `Create entity type 'SurvivorM_` —que sugiere la propia descripción de `wait_for`— **falla en
   silencio** con un personaje femenino: 300 s de timeout con el jugador ya dentro del mundo y
   `Create entity type 'SurvivorF_Helga'` escrito en el RPT. Usar `Create entity type 'Survivor`.

## GOTCHAS DEL PUENTE QUE CUESTAN UNA CORRIDA CADA UNO (added 2026-08-18)

Verificados in-game el 2026-08-18 durante una bateria de celdas de ATM. Los seis costaron al menos
una corrida cada uno, y **cinco de los seis producen un veredicto que acusa al mod sin que el mod
tenga nada** (6 corridas, 0 fallos reales del mod). Comprobalos ANTES de escribir la primera sonda.

1. **`dayz_test_run` NO carga `@DayZ_MCP` por defecto, y devuelve `succeeded` igual.** Los dos
   procesos arrancan vivos, el juego funciona, y el puente calla. El sintoma que recibes
   (`server_poll_stale` / `client_not_polling` / `ready.reason=no_run`) apunta al puente o a la
   clave, no al conjunto de mods, asi que se pierde el tiempo en el sitio equivocado.
   **Gate**: pasa `extra_mods=["@DayZ_MCP"]` y confirma en el log del servidor que el define
   `DayZ_MCP` aparece en los cuatro modulos, o busca lineas `[MCP-POC]`.

2. **`logs_since` no acepta su propio `marker`.** Lo DEVUELVE como dict {ruta: [offsets]} y su
   parametro lo exige string: ValidationError de Pydantic. El drenaje incremental es imposible.
   **Rodeo**: lee el log entero al final de la secuencia y asigna las respuestas por orden,
   verificando la alineacion con algun campo del propio evento (un tipo, un id). Si dos sondas
   comparten ese campo, marca `ambiguous_alignment` en vez de adivinar.

3. **`wait_for(log_matches)` no sirve para esperar TU respuesta.** Con el `lookback_lines=200` por
   defecto, una linea de la sonda anterior satisface el patron al instante. Y con
   `lookback_lines=0` se ha visto hacer timeout con la linea ya presente en el log del cliente,
   devolviendo en `observed` una linea de otro flujo. Usalo como espera oportunista; el veredicto
   sale del sondeo de `logs_since`.

4. **El inventario del jugador NO se resetea entre corridas.** La segunda corrida encuentra lo que
   dejo la primera, ya no cabe nada y el dotado falla en silencio (`create_failed`, o endow de 0
   unidades). Para encadenar: `dayz_test_stop`, borrar
   `<mision>\storage_1\players.db` con backup, y relanzar (~3 min).
   **OJO**: `clean=true` NO hace esto — fuerza `Build=true` y pasa `-clear` a AddonBuilder, o sea
   **reconstruye el PBO** y rompe la identidad de binario, que es justo lo que un A/B no puede
   permitirse. El saldo/estado que el mod guarde en el perfil del servidor SOBREVIVE al borrado.

5. **`inventory_give` devuelve `create_failed` tanto si el classname no existe como si no cabe.**
   Son indistinguibles. Antes de culpar al inventario, verifica que el classname existe: grep en el
   `types.xml` de la mision y una prueba con un item vanilla de control (`Apple` sirve). Y no
   presupongas que los classnames de la config del mod existen: pueden apuntar a un mod que no esta
   cargado, en cuyo caso el conteo por classname exacto da 0 para siempre y toda la feature parece
   rota sin estarlo.

6. **No te creas un veredicto sin mirar el log del cliente.** Muchos eventos de mod los escribe el
   CLIENTE, no el servidor. En la bateria que origino esta seccion, el veredicto automatico dijo
   FAIL o INCONCLUSIVE seis veces seguidas mientras el log del cliente mostraba las operaciones
   ejecutandose correctamente. El modo de fallo peligroso de una celda no es "no mide": es
   **"mide mal y acusa al mod"**, y eso se propaga a los documentos del proyecto. Si un veredicto
   dice FAIL, abre el log del cliente antes de registrarlo.

- **`world_spawn` con `ok=1` NO prueba que el objeto se quede donde lo pediste** (added 2026-08-21,
  council DayZ-MCP). `IsSpawnReady` (`MCPBridge.c:2729-2753`) toma la posicion ACTUAL del propio
  objeto, busca objetos en esa posicion y se da por listo si se encuentra a si mismo. Un objeto
  siempre esta donde esta: el gate es tautologico y se cumple para cualquier objeto vivo, aunque la
  fisica ya lo este expulsando. No compara contra la posicion PEDIDA, no mide deriva y no exige
  estabilidad entre ticks. Caso real: spawn en punto urbano con `ok=1` y el vehiculo terminando a
  **Y = -40 km**. Distinto del fallo por coords invertidas de mas arriba, que da timeout: este da
  PASS falso. **Regla: tras cualquier `world_spawn` que importe, confirmar con `object_inspect` o
  `entities_query` que la distancia a la posicion pedida es la esperada, y repetir la lectura unos
  segundos despues para descartar deriva.** Un veredicto de playbook que solo mire `ok` no vale.

## EL LAZO

1. **Lanzar** vía `dayz-test.ps1 … -ExtraMods "@DayZ_MCP"` (espera a que cliente y server
   estén dentro; BUG-009: la autoconexión del cliente es flaky — `-ServerWait` mayor / reintento).
2. **Gate** `bridge_status` (PREREQUISITES.3).
3. **Condiciones de escena** (capturas comparables): `world_time_set` a mediodía
   (los 5 args `year/month/day/hour=12/minute=0` son obligatorios) y `world_weather_set(overcast=1.0)`. Cielo cubierto = luz difusa: elimina el
   glint especular de sol directo que quema armas/materiales a blanco y tapa el detalle
   (hallazgo A6_SR2M 2026-06-17). NO uses `time_multiplier=0` antes de animaciones pendientes
   (congela la sim).
4. **Playbook** según tipo de mod (abajo).
5. **Reporte** con evidencia.

## PLAYBOOKS (criterios pass/fail por tipo)

Todos parten de spawn. `world_spawn(type=<classname>, pos=[x,y,z])` → PASS si `ok` y sin
`unknown_type`/`spawn_failed`; guarda el `pos` real para los pasos siguientes.

### Objeto estático / contenedor / edificio
- **Carga**: spawn ok (arriba). FAIL → el classname no resuelve (mod no montado: paths
  absolutos `!Workshop`, ver dayz-test-ingame; o `CfgPatches` no registra).
- **Visible + texturado + winding**: orbita la cámara (≥4 poses — frente/lado/atrás/picado) con
  `camera_set` + `capture_screenshot`; lee cada PNG. PASS = el objeto se ve (no invisible), sin
  texturas missing (no magenta/blanco/negro pleno), proporciones plausibles, sin caras invertidas
  ni agujeros (winding). El agujero/cara-faltante desde un ángulo y sólida desde el opuesto = winding
  invertido.
- **Colisión**: `scene_raycast(from_pos, to)` apuntando al objeto desde ≥2 ángulos (para
  edificios: multi-punto — paredes, esquinas, suelo). PASS = los rayos que deben pegar dan
  `hit=true` con `object_type`/`object_class` del objeto. Sin hit donde debería = ViewGeo/FireGeo
  ausente o mal resuelto (LODs).
- **Placement**: `telemetry_read(mode="object_at", type=<classname>, pos=<spawn_pos>, radius=2)`
  → `found=true`, `pos` ~ spawn, `orientation` razonable. PASS = no enterrado ni flotando
  (cruza `pos.y` con el visual).

### Item / arma
- Carga + visible/texturado/winding como arriba, con **énfasis en proporciones vs la referencia
  real** y en la geometría post-import (orientación, winding) — es donde fallan las mallas
  generadas/importadas.
- `telemetry_read object_at` → `attachment_count`, `health01`. PASS de telemetría = found + stats
  sanos.

### Vehículo (solo placement/estructura)
- Carga + visible + colisión + telemetría. `vehicle_enter(pos)` → `seated=true` confirma el
  asiento. `telemetry_read` → `engine_on_server`, `wheel_count`, `fuel_fraction`.
- `vehicle_enter` SIENTA al player (placement/asiento). Para CONDUCIR: la escalera de
  drivability (§DRIVABILITY + `references/acceptance-ladder.md`) cubre conducción autónoma vía los verbos owner-side
  (`vehicle_get_in_client`/`engine_set`/`vehicle_control`/`vehicle_telemetry`).

## CAPTURAR ARMA ALZADA / ADS (raise client-side) [VERIFIED-SR2M gate iter36→37]

Para validar la pose de arma ALZADA/apuntada (p.ej. el agarre de la mano de apoyo) no hay tool de input
de player. Se fuerza el raise EN EL MOD, **client-side** — el personaje capturado es el player LOCAL del
cliente, así que un override desde el `init.c` del servidor NO mueve la pose que el cliente renderiza
(síntoma exacto: el log del server dice `raised=1` pero la captura sale con el arma BAJADA).

Drop-in: un `modded class MissionGameplay` en un mod del gate (declara un `missionScriptModule` en su
`class defs`, `files[]={"Mod/Scripts/5_Mission"}`; build `-PackOnly` para que el `.c` sobreviva al pack):

```c
modded class MissionGameplay
{
    override void OnUpdate(float t)
    {
        super.OnUpdate(t);
        PlayerBase p = PlayerBase.Cast(GetGame().GetPlayer()); if (!p) return;
        HumanInputController h = p.GetInputController(); if (!h) return;
        h.OverrideRaise(HumanInputControllerOverrideType.ENABLED, true);  // ENABLED persiste; ONE_FRAME parpadea -> idle
    }
};
```

Claves:
- La pose de aim en 3ª persona depende SOLO de `IsRaised()` (`dayzplayerimplement.c:1726`, AimingModel) →
  un raise sostenido basta. NO llamar `SetIronsights()`: fuerza la cámara ironsight que pelea con la
  free-cam del MCP, y server-side dejó el arma sin textura.
- `WeaponADS()` (`human.c:86`) es flag de INPUT sin override de script (`human.c:234-255`) → siempre 0
  aunque el ADS funcione. La señal de éxito = `IsRaised()` / log del cliente, NO `WeaponADS()`.
- Mantener un `OverrideRaise(ENABLED)` también server-side (init.c) para que el servidor concuerde.
- Juzgar el agarre por la mano a resolución NATIVA (recortar el frame del orbit), nunca el contact-sheet
  reescalado. Mecanismo del grip + parity geométrica: skill `dayz-animation-pipeline`
  (`references/weapon-in-hands.md`).

## TOOL → QUÉ VERIFICA

| Tool | Verifica | Señal de fallo |
|---|---|---|
| `world_spawn` | el classname carga | `unknown_type` / `spawn_failed` → mod no montado |
| `camera_set` + `capture_screenshot` | render: visible, texturas, winding, proporciones | invisible / magenta / agujeros |
| `scene_raycast` | colisión (ViewGeo/FireGeo) | sin hit donde debería pegar |
| `telemetry_read` (object_at) | placement, orientación, attachments, health | `found=false` / pos enterrada |
| `bridge_status` | liveness de peers (gate) | `last_poll_age_s=null` → bridge caído |
| `world_time_set` / `world_weather_set` | escena reproducible para capturas | — |

## QUÉ NO CUBRE (declarar SIEMPRE en el reporte)

- **Acciones de player y UI**: abrir/cerrar puertas, inventario interactivo, disparar, recargar,
  menús. No hay tool de input de player genérico. (Conducir SÍ está cubierto — escalera
  §DRIVABILITY / `references/acceptance-ladder.md` con los verbos owner-side.) Para un edificio, la geometría/colisión SÍ;
  las **puertas NO** → test manual.
- **`exec_enforce`** no ejecuta en el server diag headless (GATE4B-LIM, limitación de engine tipo
  MakeScreenshot) — no apoyarse en él para "ejecutar lógica arbitraria de verificación".
- **`telemetry_read`** se expone tal cual (BUG-010/011/012, hardening pendiente): no certifica
  fixtures JSONL grandes ni rangos extremos.

## REPORTING

Un reporte con: tabla de criterios (criterio · PASS/FAIL/INFO · evidencia), los PNGs y los JSON
de telemetría/raycast como evidencia, veredicto global, y una sección **"a test manual"** con lo
no cubierto (puertas, disparo, etc.). Coste de contexto: cada captura pesa ~25k tokens (~240-320
px) — **batch** las capturas de una pose-órbita y NO re-leas un PNG salvo para verificar algo
concreto (las imágenes inflan el contexto rápido). Presupuesto duro ~25k tokens/imagen: no pedir
más resolución.

## TROUBLESHOOTING

| Síntoma | Causa | Fix |
|---|---|---|
| `claude mcp list` → `× Failed to connect` | `claude mcp list` NO es fiable: da falsos `Failed` con el server operativo. La contención E4 del puerto 8765 (lock `ExclusiveThreadingHTTPServer`, fail-closed) era el modo de fallo PRE-broker | verificar PRIMERO con ToolSearch (¿tools `mcp__dayz-mcp__*` disponibles? → todo OK, ignorar el `Failed`). El registro broker `--client` (desde 2026-06-24) supera la contención E4: N sesiones comparten el server sin pelear por 8765, y el orphan-guard suelta huérfanos solo. Si las tools faltan de verdad: registrar en modo broker (`--client`) y abrir sesión NUEVA (las tools cargan al arranque) |
| tools no aparecen en la sesión | el server se registró DESPUÉS de abrir la sesión | abrir una sesión nueva (los MCP se cargan al arranque) |
| `bridge_status.server_peer.last_poll_age_s = null` | el bridge server no pollea | revisar `dayz_mcp.json` en server_profiles + la key; confirmar `@DayZ_MCP` montado (paths absolutos `!Workshop`) |
| `client_peer … null` (server ok) | el cliente no conecta o `client_profiles\dayz_mcp.json` falta | BUG-009 (autoconexión flaky): `-ServerWait` mayor / reintento; sembrar la config del cliente |
| `version_state = legacy_blocked` | `--require-version` ON contra un bridge que no manda `ver=` | desplegar el PBO 4B (manda `ver=4~…`), o registrar el server sin `--require-version` para ese run |
| capturas byte-idénticas entre poses | grab cogió un frame stale del escritorio (no el render) | `PrintWindow(PW_RENDERFULLCONTENT)` devuelve marco real y área D3D NEGRA (LL-247, 2026-08-12): no arregla la captura del juego. Usar `CopyFromScreen` del rect interior, solo con sesión desbloqueada, y validar el recorte del área de juego |
| timeout de tool y luego comandos "zombie" al reconectar | BUG-024: un timeout deja el comando en cola; el bridge lo ejecuta al volver | tras un timeout, reconciliar con `bridge_status` antes de seguir |

## REFERENCES

- `dayz-test-ingame` — build/deploy/launch (esta skill lo compone con `-ExtraMods "@DayZ_MCP"`).
- `DayZ_MCP_dev\tools\README-mcp.md` — orden de arranque + troubleshooting del bridge.
- `DayZ_MCP_dev\HANDOFF.md` (LIVE-STATE) — invariantes del server, 11 tools, GATE4B-LIM, backlog.
- `_shared\dayz-conventions.md` — L2 (LODs, ViewGeo/FireGeo, formato de respuestas DayZ).
- Precedente de captura por cámara+órbita: el `gate-mcp.ps1` del A6 (window-grab por órbita,
  hallazgo dayz-test-ingame 2026-06-17) — barrido batch alternativo al agente conduciendo tools.


## VEHÍCULO: receta de smoke repetible (added 2026-06-24)

Smoke visual de un vehículo CarScript conducido por MCP, verificado end-to-end en MercedesAMGLF
2026-06-24. Repetible sin re-derivar:

1. **Misión = stock `dayzOffline.chernarusplus`** (la del DayZServer install), NO una mount-probe
   `void main()` de Fase 0: la mount-probe no spawnea player → el cliente no renderiza el mundo y la
   captura sale negra. La stock spawnea player (`CreateCharacter`→`CreatePlayer`) → free-cam con mundo
   renderizado. Pásala con `-Mission "<...>\dayzOffline.chernarusplus"`.
2. **Seed del bridge en los profiles que genera `dayz-test.ps1`**: `dayz_mcp.json`
   `{"url":"http://127.0.0.1:8765/","key":"<key>","pollHz":5}` (ASCII) en `<Mod>_dev\_server\profiles\`
   y `..\_client\profiles\`. El bridge lo lee de `$profile:` (server `MCPBridge.c:125`, client
   `MCPClientBridge.c:211`); key = `DayZ_MCP_dev\tools\.dayz_mcp.key`. Sembrar ANTES del launch (el
   bridge lee el config en su init, una sola vez). No uses `install-mcp.ps1 -Register` (re-registra el
   modo broker `--client`).
3. **Launch**: `dayz-test.ps1 -Mod <Mod> -Mode all -Build -PackOnly -ExtraMods "@DayZ_MCP" -Mission
   "<...>\dayzOffline.chernarusplus" -ServerWait 240`. `-PackOnly` obligatorio en mods con `.c`
   (binarize los dropea → NO_IGNITER). Llamar el `.ps1` por ruta absoluta (P:\ es subst).
4. **Readiness**: la stock corre el CE (`InitOffline`) ~1-3 min; durante el CE `bridge_status` sale
   STALE (`last_poll_age_s` crece aunque `version_state=ok`) — NO spawnees ahí. Espera a `connected to
   server` en el `script*.log` del server y a que `bridge_status` vuelva fresco (<1 s). Poll
   host-direct con PowerShell del log, NO Monitor bash (hereda el cache bindfs, LL-142).
5. **Smoke** (agrupado, R5): `world_time_set(year,month,day,hour=12,minute=0)` (los 5 obligatorios) + `world_weather_set overcast=1.0` → `world_spawn
   <Class> pos≈[player+~10]` → esperar 30 s (sobrevive sin crash nativo = LL-099 descartado) →
   `camera_set` (cam_mode **"lookat"**, `cam_pos`+`look_at`) + `capture_screenshot` + `scene_raycast` +
   `telemetry_read object_at`. Telemetría sana = `found=1`, `health01=1`, `velocity 0`.
6. **Captura flaky**: el grab a veces coge la pantalla de carga o el overlay del menú "Continuar" del
   cliente en vez del render. Si pasa: espera settle (~30-40 s en background — el foreground sleep está
   bloqueado en este entorno) y recaptura; usa varios ángulos. Cenital que delata bien la
   (des)alineación de proxys: `cam_pos=[carX+3, 16, carZ+1]` `look_at=[carX, suelo+0.1, carZ]`. ~25k
   tokens/imagen — batch las capturas, no re-leas un PNG salvo para verificar algo concreto.
7. **El ojo del usuario > la captura** cuando el render es ambiguo: en MercedesAMGLF el grab era flaky y
   la lectura del usuario fue el diagnóstico fiable de winding y alineación de proxys. Si hay humano en
   el bucle, contrástalo. (Caso s3 2026-06-24: yo iba a firmar PASS sobre renders tenues; el ojo del
   usuario cazó la desalineación de proxys que yo no resolvía → FAIL correcto.)

8. **SESIÓN COMPARTIDA.** El puerto 2302 y el cliente Steam siguen siendo recursos únicos, pero
   la exclusión se coordina con el lease FIFO del runbook, no atribuyendo procesos ni desalojando
   otras sesiones. `dayz_test_run` adquiere y mantiene la exclusión; conserva el `run_id` y
   termina ese mismo run con `dayz_test_stop`. NUNCA mates un proceso para desbloquear la caja:
   si el estado no reconcilia, conserva el proceso y declara cierre degradado.

9. **"Ruedas = lámina/disco plano" NO es bug de proxy.** Un `world_spawn` de un CarScript sin attachments deja
   `wheel_count=0`/`attachment_count=0` → solo se ve el hub/disco, sin neumáticos. Esperado en el smoke visual; las
   ruedas reales requieren attachments (fase de física), fuera de alcance del smoke.

10. **`legacy_blocked` ("poll did not include ver=") suele ser INIT INCOMPLETO, no mismatch de versión (added
    2026-06-28).** Refina la fila homónima de TROUBLESHOOTING: con el PBO 4B desplegado, justo tras lanzar el server
    el `bridge_status` puede salir `legacy_blocked`/`last_poll_age_s=null` porque el bridge aún no completó el
    handshake; pasa a `ok` con `ver=4~…` cuando el mission del server CARGA del todo (~1-2 min). NO redepliegues ni
    re-registres por eso — espera y re-chequea. Solo es mismatch real si sigue `legacy_blocked` con el mission ya
    cargado (cliente conectado, world renderizado). Origen: SUB_BRZ Fase 5 2026-06-28.

11. **Patrón histórico superseded 2026-07-15.** `cmd start`/`.bat` evitaba que un job background
    perdiera su hijo, pero creaba un proceso fuera del lifecycle registrado. Para cualquier smoke
    actual, usa exclusivamente `dayz_test_run`, conserva su `run_id` y termina solo ese run con
    `dayz_test_stop`. No existe fallback unmanaged para sortear el lifecycle guard.

## DRIVABILITY + ESCALERA DE ACEPTACIÓN (resumen — detalle en reference)

Fase 5 del proyecto DayZ-MCP añadió y gateó in-game verbos owner-side que SÍ **conducen** el
coche (el cliente toma ownership y maneja throttle/steer): `vehicle_get_in_client(pos)` (sienta +
ownership), `engine_set("start"/"stop")`, `vehicle_control(throttle, steer, brake, handbrake,
hold_ttl_s)` (control SOSTENIDO, fail-closed), `vehicle_telemetry()`, `vehicle_release()`, y
`query_get_in_condition(pos, component)` (peer server, diagnostica cuál de los 7 gates de
`ActionGetInTransport` bloquea). Sobre ellos corre la **escalera de aceptación** rip→conducible:
rungs ordenados **R1 spawnea → R2 render → R3 get-in disponible → R4 sentado → R5 conduce → R6
sentido de ruedas**, cada uno leyendo ground-truth in-game y mapeando su fallo a un fix conocido de
la taxonomía SUB_BRZ (`dayz-vehicles/references/`). Orquestador de referencia `references/drive_ladder.py`
(conduce R1→R6, emite `verdict.json`; NO aplica fixes ni rebuildea) + fixtures `references/test_drive_ladder.py`.

**Detalle completo** (verbos, mecanismo owner-side verificado, precondiciones, colocación del spawn,
R2.5 restore-gameplay, barandillas anti-verde-falso, la tabla de la escalera y el mapeo fallo→fix) →
`references/acceptance-ladder.md`.


## (added 2026-07-14) No hay tool de restore-gameplay: para test MANUAL del usuario, relanzar sin @DayZ_MCP

`camera_set` SIEMPRE suprime el control del player (`SuppressGameplay()` -> `PlayerControlDisable`, ver
§R2.5) y **NO hay tool MCP que dispare `RestoreGameplay()`** — solo el gate interno `drive_probe_client`
lo hace, y no está expuesto como verbo/tool. Consecuencia práctica: tras un smoke MCP que usó `camera_set`
(free-cam o static-cam lookat), el USUARIO no puede tomar el control del player para probar el coche a mano
— su input sigue suprimido y no hay verbo para revertirlo en caliente.

Regla: cuando el flujo pasa del smoke MCP (automático) al **test manual del usuario** (conducir, juzgar
feel/estética), **relanzar el juego SIN `@DayZ_MCP`** (o al menos con un cliente que nunca haya recibido
`camera_set` en esa sesión). Un cliente limpio tiene control normal. Si el cliente ya quedó "capado":
reconectar (Esc -> Disconnect -> Reconnect) recrea el player con cámara/control limpios; no hay atajo por
tool. Origen: SUB_BRZ s35 — se perdió tiempo buscando una tool de restore inexistente y el usuario tuvo
que cerrar el juego y pedir relanzar normal.

## (added 2026-07-14) Smoke autonomo: world_spawn toma [x, y_up, z] motor, y captura con display dormido = frame negro (SP-060)

Dos caveats de smoke MCP autonomo verificados in-vivo (SUB_BRZ s32):

1. **`world_spawn` toma el vector en orden MOTOR `[x, y_up, z_north]`** (`MCPBridge.c:1638` `Vector(x,y,z)`), pero el connect-log del bridge imprime la posicion del player como `<x, z_north, y_up>`. Pasar la tripleta del log VERBATIM spawnea el objeto a ~6 km de altura -> `IsSpawnReady` (radio 2.0 m) nunca se cumple -> job timeout + `found=0`, y el motor auto-borra el huerfano (`NETWORK (E): Will delete object ... outside world coords`). Costo 3 timeouts seguidos. Regla: convertir `<x,z,y>` -> `[x,y,z]` antes de todo `world_spawn`/`camera_set`; tras un timeout de spawn, grep del RPT por `outside world coords` ANTES de reintentar (distingue coords-malas de spawn-lento). Verificable con `scene_raycast` al terreno (da la y_up real).
2. **Captura con el display en reposo o la sesion bloqueada = frame NEGRO** aunque el client corra. Fix: traer la ventana del client a foreground + input wiggle (raton / F15) antes de CADA `capture_screenshot`. Sintoma enganoso: parece "render roto del mod" y es el compositor.
3. (menor) Spawn adyacente al player puede caer DENTRO de un edificio -> sondear 3-4 `scene_raycast` a terreno despejado antes de elegir la pos.

Origen: SUB_BRZ s32 smoke MCP (2026-07-11): 3 timeouts de `world_spawn` con la pos cruda del log + 2 capturas negras con LockApp; ambos resueltos con lo de arriba.

## (added 2026-07-14) Gates numericos de telemetria: calibrar contra el SUELO FISICO MEDIDO, no contra fixtures ideales (SP-061)

Invariante para cualquier acceptance-ladder / gate numerico sobre telemetria in-game (drive_ladder de coches, spikes, futuros harnesses):

1. **Un umbral calibrado con fixtures matematicas ideales es un gate que ninguna fisica real pasa.** El motor tiene suelo de ruido nativo (dither del body entre SetVelocity y lectura; interpolador de red del cliente). Antes de fijar un umbral: MEDIR el suelo en un run real (p95 de la metrica sobre datos reales), umbral = suelo x margen (>=2x), y documentar los numeros medidos junto a la constante. Dos mediciones independientes convergentes (implementador + receptor, +-20%) validan el numero. Caso: LFHeli W0 batch1 - jitter gate a 0.5 m/s con suelo real 4.3-5.1 m/s -> NO-GO falso que costo una correctiva entera; recalibrado dio GO con margen 2.2x.
2. **La metrica de suavidad perceptiva es el zigzag frame-a-frame en METROS (2a diferencia, |delta v_implied|*dt)** - NO |delta residual vs ideal| por frame (autocorrelacionado; media 2x el zigzag real) y NO implied-velocity en m/s (escala 1/dt: el mismo proceso da suelos distintos a 30 vs 60 FPS y rompe celdas A/B de FPS).
3. **Transitorios de arranque (teleport de setup + interpolador persiguiendolo) se excluyen con warm-up acotado en la ventana de score del cliente** (transitorio real 0.25 s -> warm-up 1.0 s = margen 4x), fail-closed todo lo demas.
4. *(extension LFHeli X.5e/f)* **Los checks ESTRUCTURALES relativos tambien necesitan piso absoluto, y la mediaNA del frame-time es falaz con distribucion bimodal.** Un run a 250 FPS con frame-time bimodal (rafagas 4 ms + poblacion ~50 ms) rompio tres umbrales relativos: max-gap 3x mediana, dt-tol 30%*dt, coverage span/mediana_dt. Fixes: pisos absolutos con base fisica (gap 0.150 s; dt-tol 0.015 s) y coverage por media de la columna dt (la media de los DELTAS de t es TAUTOLOGICA: span/(n-1) -> ratio ~1 siempre - check vacuo, trampa G3).

Cross-ref `dayz-vehicles` (drive_ladder) y `dayz-mod-workflow` ("primer run real -> retune, no NO-GO"). Origen: LFHeli X.5d (2026-07-11), doble medicion convergente + selftest 31/31.

## (added 2026-07-14) Gates telemetricos (extiende SP-061): epsilon float en bordes + invariante AGREGADA de balance temporal (SP-063)

Dos defectos adversariales reproducidos en un gate ya doblemente sellado (re-sello Codex, confirmados por el receptor):

1. **Comparadores de umbral temporal necesitan epsilon de representacion float.** Un contrato "el borde exacto tolera" (gap 150 ms / desviacion 15 ms) se viola en binario: deltas acumulados dan `0.15000000000000002 > 0.15` -> falso REJECT del borde, y NO determinista. Fix: `> limite + EPS` (1e-6 s) en CADA comparador temporal, con fixtures de borde N-1/N/N+1 (149/150/151 y 14/15/16 ms).
2. **Un coverage por conteo x media es una IDENTIDAD evadible sesgando el denominador.** `rows >= K*span/mean(dt)` <=> `sum(dt) >= K*span`: una columna dt sesgada +50% SOSTENIDA (bajo el floor por-fila) compensa un 40% de filas perdidas -> GO fail-open sobre traza incompleta. Fix: invariante AGREGADA de balance two-sided `|span - sum(dt[1:])| <= max(1%*span, 0.1 s)` - para productor honesto es ~0 por identidad fisica; medido <=0.0001% del span en 9 CSVs reales vs 9.98% en la fixture adversarial.
3. **(Meta) floor-por-fila + invariante agregada son PAREJA obligatoria**: el por-fila caza el outlier aislado; el agregado caza el sesgo sostenido pequeno. Un solo nivel deja un flanco abierto - y la fixture que lo demuestra es el ACOPLAMIENTO de dos checks "cerrados" por separado.

Cross-ref `dayz-vehicles` (drive_ladder). Origen: re-sello LFHeli X5EF (2026-07-11), F-01/F-02 con outputs literales + fixture cruzada 40%-drops + dt-6ms -> GO fail-open.

## (added 2026-07-18 s37) Conditioning server-side de un coche custom (OnDebugSpawn real)

`vehicle_get_in_client` ejecuta OnDebugSpawn CLIENT-side = no-op bajo autoridad del server
(sintoma: `vehicle_fixture_ready=1` enganoso con `wheel_count=0`/`fuel=0` en telemetria
server). Para condicionar de verdad (ruedas+fluidos autoritativos) sin tocar codigo:
`vehicle_enter(pos)` (asiento server) y despues raw enqueue
`vehicle_drive {throttle:0.01, duration:0.5}` — su fase PREP ejecuta `car.OnDebugSpawn()`
SERVER-side (MCPBridge.c:2104-2112) y el micro-drive de 0.5 s es despreciable. OJO:
`vehicle_drive` exige el asiento SERVER-side (da `not_seated` con el seat owner-client).
`vehicle_prepare_fixture` NO sirve fuera del Mercedes (hardcode `MERCEDES_AMGLF` en
MCPBridge.c:835 y loopback.py:113; chip abierto para generalizarlo). El raw `/enqueue`
exige `{identity, lease_token}` en el body ademas de `?key=` (la identity/token salen de
`session_acquire`). gear idx de `vehicle_telemetry`: 0=R, 1=N, 2=1a ... 7=6a.
Verificado in-game SUB_BRZ s37 (wheel_count 0->4, fuel 1.0, kit completo, run B3 a 6a).

## (added 2026-07-22) Spawn pelado expone el tren de rodaje → parece misalignment; condicionar antes de juzgar alineación

Un `world_spawn` de un vehículo CarScript lo crea SIN attachments (`wheel_count=0`, `attachment_count=0`): las ruedas/neumáticos NO están, así que los **frenos (rotor + caliper — el caliper suele ser ROJO), la suspensión y los hubs quedan AL DESCUBIERTO** en el paso de rueda y se ven "flotando" con un hueco. **Eso NO es misalignment**: es geometría base correcta, simétrica y en su sitio, contenida en el volumen que ocuparía la rueda ausente.

Reglas:
- Un smoke con **spawn pelado es MATERIALS-ONLY** — valida pintura/texturas/winding del cuerpo, NO la alineación del tren de rodaje ni el aspecto "completo".
- Para juzgar alineación/aspecto CON ruedas: **CONDICIONAR** el coche (`wheel_count 0→4`) con `vehicle_enter(pos)` + micro-drive server-side (`OnDebugSpawn`; ver nota "Conditioning server-side (OnDebugSpawn real)" s37 arriba) y recapturar con las ruedas puestas.
- Ante una pieza que "parece desplazada": **MEDIR antes de concluir** (bbox/centroide/simetría izq-der + bisección vs backup + containment en volumen de rueda) — no firmar "roto" ni "OK" por opinión.

Verificado: SUB_BRZ 2026-07-22 — un susto de "piezas desalineadas" resultó ser frenos/suspensión al descubierto por spawn pelado; el forense (Codex, py3d) midió simetría ≤0.003 m, bisección 0-movimiento en 6 shells y containment en el volumen de rueda (`<rip-import>\work\reviews\2026-07-22-SUB_BRZ-misalign-forensic.md`). Costó 30 min de forense evitable. Cross-ref LL-209.

## Reglas promovidas del corpus de lecciones (added 2026-07-27)

Promovidas desde `AI/20_Knowledge/lessons-learned.md` para que lleguen por trigger en vez
de depender de que alguien recuerde buscarlas. Cada regla cita su `LL-NNN` de origen;
la entrada completa (síntoma, origen, evidencia) vive allí. No quites la cita: el índice
`lessons-index.md` detecta la promoción buscando esa referencia dentro de las skills.

- **LL-181** — Antes de culpar al mod por un FAIL automatizado, verifica el source del actuador/bridge y confirma que el estímulo llegó al sujeto. Ejecuta un control delta equivalente o un test manual para discriminar un defecto del harness.
- **LL-187** — Si varias defensas interceptan el mismo fallo, diseña un repro por capa que alcance su punto de protección. Exige la señal específica de cada capa; un PASS agregado de “no falla” no demuestra que todas funcionen.
- **LL-202** — Ante el primer error anómalo de un verbo client-side, verifica el PID del cliente, el tail de su RPT y `bridge_status` antes de seguir. Si el peer murió, extrae minidump/evidencia y documenta el cierre degradado; no diagnostiques los errores posteriores como estado del harness.

## El daemon sirve el codigo que cargo al ARRANCAR — un verbo nuevo no existe hasta reiniciarlo (LL-223, added 2026-07-29)

Si anades un verbo al bridge (`SERVER_COMMANDS` / `CLIENT_COMMANDS` en `loopback.py`) y la tool
responde **`not_whitelisted`**, no busques el bug en tu diff: el **daemon** cargo ese modulo
cuando arranco y no lo ha vuelto a leer. `loopback.py` y `server.py` NO estan sellados en
`app.pyz` —editarlos surte efecto sin rebuild del bundle— pero eso no reinicia nada.

Lo que mas engana: la tool **si aparece registrada** en tu cliente MCP, porque el cliente arranco
despues de la edicion. La mitad visible del sistema confirma que el verbo existe mientras la
mitad que decide sigue con la lista vieja.

**Comprobacion de un comando** (mtime del fuente vs arranque del proceso que decide):

```powershell
(Get-Item '<...>\dayz_mcp\loopback.py').LastWriteTime
$pid_ = (Get-NetTCPConnection -LocalPort 8765 -State Listen).OwningProcess
(Get-CimInstance Win32_Process -Filter "ProcessId=$pid_").CreationDate
```

Fuente mas nuevo que el proceso = esa es la causa, deja de mirar el codigo. Medido 2026-07-29:
`loopback.py` 15:57:54 vs daemon arrancado 14:18:42 (1 h 39 min de desfase).

**Reinicio**: `Stop-Process` del listener del 8765; el cliente lo re-spawnea lazy en la siguiente
llamada y `daemon_generation` cambia (asi confirmas que es otro proceso). Reiniciar el daemon
esta declarado seguro (BUG-062b). **Avisa antes**: desarma momentaneamente las tools MCP de las
demas sesiones vivas, asi que mira `session_status` (owner/cola) primero.

**Tras el reinicio hay ventana de re-handshake**: las primeras llamadas pueden dar
`version_blocked` o `peer_reconnect_flush`. Son transitorios — reintenta, no rediagnostiques.
Confirma con `bridge_status` que ambos peers tienen `version_state: ok` y `last_poll_age_s` bajo.

Hermano pero distinto de la trampa del bundle sellado: alli `app.pyz` sella COPIAS de los modulos
del lifecycle de test (`dayz_test_worker.py` y cia) y hace falta rebuild+CAS; aqui no hay sellado
ninguno, basta con que el proceso sea viejo.

Origen: DayZ_MCP, gate in-game de `query_all_players` (2026-07-29).

## Cadena «abrir UI de mod sin teclado» VERIFICADA in-game + tres trampas de uso (SP-292, added 2026-08-18)

Gate del ciclo 1 de DayZ_MCP (2026-08-17, run `28f2e26f`, PBO `BCA758A1…`): la cadena completa funciona end-to-end.
Receta medida (LFPowerGrid + @DayZ_MCP; adaptar nombres al mod):

1. `dayz_test_run(project="LFPowerGrid", mode="all", extra_mods=["@DayZ_MCP"])` → `wait_for(log_matches, "OnStoreLoad SUCCESS")`
   (77 s / 26 sondeos) → `wait_for(players_at_least, 1)` → `session_acquire_wait(purpose=…)`.
2. `world_spawn(type="LFPG_BTCAtmAdmin", pos=[x,0,z])` a ~3 m del jugador → `action_use(action="LFPG_ActionOpenBTCAtm",
   classname="LFPG_BTCAtmAdmin", radius=5)` → `started:1` (el lookup por `Type().ToString()` funciona en runtime).
3. `wait_for(log_matches, "[BTCOpenResponse]", lookback_lines=200)` — **con lookback**: la respuesta aterriza ~200 ms tras el
   disparo y con el cursor «desde ahora» se pierde SIEMPRE (BUG-086, 2/2 timeouts con la linea ya en el log).
4. **`ui_tree(path="BTCAtmRoot")`** — con path vacio devuelve `no_menu` aunque la UI este ABIERTA: un panel Dabs/ScriptView es
   un host pre-creado, no un `UIScriptedMenu`. Pasar el nombre del root del `.layout` (`grep -oE 'FrameWidgetClass \w+' gui/layouts/X.layout | head -1`).
5. `ui_set_text("EditBtcAmount", "1")` con ENTERO (`GetBtcInput()` es int: "0.001" → 0 → `ShowStatus` sin RPC) →
   `ui_click("BtnBuyBtc")` → `clicked:1 handler=LFPG_BTCAtmView user_id=100` (la rama `#ifdef DabsFramework` de `InvokeUiClick`
   dispara con Dabs cargado por otro mod) → `wait_for(log_matches, "[BTCTxResult]", lookback_lines=200)` y leer `err=`.
6. `session_release` → `dayz_test_stop`.

Trampa de convivencia (medida 2026-08-18 00:01): `bridge_status` decia caja LIBRE (peers null, sin lease, sin runs) y 40 s
despues arranco un run navprobe FUERA del lifecycle y SIN lease; una sonda hizo `player_teleport` y movio a SU jugador.
Antes de cualquier mutacion sobre «el primer humano»: `bridge_status.coordination.active`, `server_peer.last_poll_age_s`
y `Get-CimInstance Win32_Process -Filter "Name='DayZDiag_x64.exe'"`; si hay un servidor sondeando que no es tuyo, NO mutes.

## Integridad del verificador y del bridge: evidencia, contrato e identidad

El bridge mide y discrimina sujetos; un verde solo vale si el comando obtuvo respuesta y el protocolo conserva la identidad que pretende aislar.

1. **Todo criterio negativo exige vida por comando (LL-267).** Antes de resolver "no ocurrió X", exige una respuesta atribuible a ese comando, por ejemplo `answered(tag)`, no una respuesta anterior de la corrida. Sin ella, el caso es `INCONCLUSIVE`, nunca `PASS`. Publica el recuento global de respuestas y, si es cero, aborta temprano en vez de imprimir una colección de veredictos. Un caso de denegación solo pasa después de demostrar que el sujeto podía recibir y ejecutar la petición.

2. **Censa las claves antes de cerrar el wire (LL-315).** Busca cada clave top-level nueva en el DTO plano serializado y en todos sus consumidores. Nombres obvios como `state`, `status`, `error` o `type` suelen estar ocupados; si colisionan, anida el payload bajo un objeto propio de la feature —el caso medido quedó como `{ok, dialog:{state,…}}`— en vez de sobrecargar el campo. El gate lee el contrato compartido real; la suite del productor no acredita compatibilidad hacia delante.

3. **Una mutación de handshake es global y autenticación no es identidad (LL-317, LL-319).** Antes de cambiar una constante de versión o desplegar el PBO/daemon que la porta, inspecciona los procesos y sesiones que cargan ese mod ahora. Si hay un juego ajeno, no publiques: coordina o revierte; poseer tu lease no demuestra que nadie más consuma el protocolo. Mantén además dos campos con contratos distintos: la identidad de instancia permanece estable durante la vida del proceso y no se recarga en caliente; la clave solo autentica y puede rotar. Conocer la instancia no concede autoridad, y un token de perfil compartido no identifica a un proceso. Nunca reutilices el secreto como identidad.

4. **Una caché debe preservar el discriminador (LL-320).** Antes de cachear fencing, autorización, rate-limit o resolución de sesión, escribe qué propiedad distingue el resultado y demuestra que la clave conserva esa identidad. Cachear por instancia permitió que dos procesos compartieran un PID —el intruso recibió 100 de 100 mutaciones y el binding nunca pasó a AMBIGUOUS—; cachear la tabla durante 50 ms ocultó al peer que sondeaba segundo —40/40 ticks sin un solo comando—. Mide hits y coste en el patrón real bajo carga: en el caso medido la tasa útil fue 0,0 y el coste en reposo no representaba el régimen cargado. Si la caché no ahorra trabajo medido o fusiona actores distintos, se elimina.
## Escalera de vehiculos — requisitos de sesion (added 2026-08-24)

- **Sitio canonico verificado**: la escalera con drive exige un punto con >=150 m despejados en la direccion de conduccion (protocolo pedido en ficha fb-20260824-025758-2509). El sitio historico del G0 congelaba el vehiculo (drivability posicional, LL-359) y el final de su linea bloqueaba el get-out contra estaticos. No reutilizar sitios sin evidencia de la propia sesion (surface_query + entities_query; el scene_raycast en `view` NO ve los estaticos que paran un coche).
- **Vida de proceso unica**: el daemon spawneado y su secuencia mueren con el arbol del comando que los pario en este harness ("broke away" no sobrevive a la cosecha; la adopcion de un daemon externo esta ademas rota — fb-20260824-032050-9aed, LL-358). Toda la secuencia run -> verbos -> teardown va DENTRO de un solo proceso (patron `AI/10_Projects/DayZ_MCP/lanes/2026-08-24/g0_full_abba.py`: stop-preventivo, run, espera bridge-ready, espera jugador, teleport con lease, trabajo, dayz_test_stop).

## Sitio canonico certificado + reglas de instrumentacion (added 2026-08-24 tarde)
- **Sitio canonico de vehiculos: NWAF `[4200.0, 0.0, 10650.0]`** (certificado 2026-08-24,
  PBO 28226C93B9B8, `docs/VEHICLE_TESTING.md` del repo): pasillo 160 m x +-25 m al norte
  enumerado completo, drive delta_2s_xz 3,2 m, teardown verificado. Re-certificar con
  `python tools/g0_site_gate.py --pbo-sha256 <sha> --out <verdict.json>` (juego ya corriendo,
  bridge ready; el SHA es obligatorio). Suplentes y causas de degradacion en el doc.
- **entities_query SOLO con el jugador dentro del area** (fb-20260824-123204-638e): lejos de
  todo jugador contesta 0 o cap-128 (bimodal) y NO es un error visible. surface_query si es
  global-fiable (terreno estatico). Pasillos: 3 esferas r=65 con `count_total` como indicador
  de truncado y prueba de distancia de la ultima fila (nearest-first).
- **Canopy gate antes de TODO teleport a coordenadas no verificadas**
  (fb-20260824-115220-1bc1): scene_raycast geom y+30 -> y-5 debe pegar a <=0,05 m de la
  superficie en el punto del JUGADOR y el del VEHICULO; detecta techos, copas y agua (pega
  en la lamina sobre lecho marino con y negativa).
## Bridge v9 + certificado multi-agente (added 2026-08-24 noche)

- **Bridge v9** (commit d73da6c; el gate de version exige pareja daemon-PBO): `object_anim`
  y `object_inspect` aceptan `object_id` (el de world_spawn) y resuelven contra el registro
  del bridge - independiente de posicion, alcanza fixtures client-auth con la replica en el
  spawn. `player_teleport` rechaza aterrizajes de superficie con columna cubierta
  (`clearance_blocked`; `skip_clearance_check=true` para interiores). `entities_query`
  trae `nearest_player_m` + `reliability` (player_in_bubble | remote_unverified).
- **Caveat medido**: el write de `object_anim` APLICA (SetAnimationPhaseNow) pero el
  `phase` del propio reply puede ir un tick por detras (0 -> write 1.0 -> reply 0.0 ->
  lectura siguiente 0.599). Confirmar con una lectura posterior, no con el reply.
- **La sonda de clearance ignora jugadores** (ignore='player'): un survivor plantado en la
  columna daba dy=1.671 y rechazaba el punto (asi se "demoto" x4300 en r13 por error).
- **Sesiones largas**: el cliente diag muere tras ~6 min sin comandos (client_not_polling).
  Runner con keepalive (p.ej. vehicle_telemetry cada ~45 s) mientras dure la sesion.
- **Certificado multi-agente 3/3 (2026-08-24)**: Grok 4.6 (solo-MCP), GPT-5.6 (codex) y
  Ox Alpha (opencode) condujeron spawn->fixture->asiento->drive (100-163 m)->puerta por
  object_id->delete->release con brief minimo. El claim "lo conducen agentes de 3
  familias" tiene evidencia en lanes/2026-08-24/ma/ del vault.

## (added 2026-08-28) Barrido de resoluciones UI sin reboot + calibracion window-grab<->engine

Medido en el vuelo F del caso sorter (run dbca698d, ficha fb-20260828-160429-2899):

- **`dayz_test_run` width/height NO fijan la resolucion del cliente** (pedidos 1280x720,
  viewport real 846x461). No gastes un reboot en cambiar de resolucion.
- **Tecnica validada**: SetWindowPos host-side (user32, SWP_NOZORDER) sobre la ventana viva
  del cliente + `ui_reload_layout` -> el viewport re-mide al instante, el escenario y el run
  se conservan. Un barrido de N resoluciones cuesta N reloads, no N boots.
- **Marco de ventana medido (Win11)**: outer - client = 11 px izq/der + 45 titulo + 11 abajo.
  El `capture_screenshot` fullres es 1:1 con el viewport: engine_px = imagen_px - (11, 45).
- **El root de `ui_tree` con `size 1 1` proporcional ES el viewport real** — usalo como
  oraculo de resolucion en vez de fiarte de lo pedido al launcher.
- **Control del factor**: los widgets con exact flags renderizan a declarado x (alto/1080),
  posiciones incluidas — si el panel de referencia no da ese factor exacto, la calibracion
  esta mal, no el layout.
- **TextWidget no expone su texto por `ui_tree`** (`text_readable=false` por contrato): para
  medir GLIFOS el instrumento es el frame (fullres + crop + medicion per-pixel), nunca el
  arbol. Etiqueta los casos DENTRO de las strings para reconocerlos en la captura.

## (added 2026-08-29, SP-350) TRES CAPAS que no se nombran entre si: no declares que un verbo NO hace algo leyendo solo el lado Python

El servidor MCP tiene **tres capas** y ninguna nombra a las otras en su propio texto:

    1. la tool en Python          `dayz_mcp/server.py`
    2. el ingress HTTP            `loopback.py`, `session_coordination.py`
    3. el puente en Enforce       `MCPBridge.c`, dentro del juego

Muchas tools son un envoltorio delgado que termina en `runtime.call_bridge(...)`. **La
semantica de verdad vive aguas abajo.** Por eso una lane que abre una sola capa cree
tener el sistema entero delante, y firma sobre comportamiento que no ha visto.

**Medido el 2026-08-29: dos revisores independientes cometieron el MISMO error la misma
noche, sobre el mismo sistema.**

- Un revisor declaro **FALSA** la afirmacion «`y=0` snaps to the ground» de `world_spawn`,
  razonando que el Python pasa `pos` verbatim por `_require_vec3` sin tocarlo. La premisa
  era correcta y la conclusion falsa: el snap ocurre en el puente. `MCPBridge.c`:
  `ValidateSpawnArgs` pone `validation.flags = ECE_PLACE_ON_SURFACE` como default de
  `flags=0`, y `IsAllowedSpawnFlags` **exige ese bit en toda combinacion aceptada salvo
  una**, `ECE_CREATEPHYSICS|ECE_TRACE`. Ademas el vault ya tenia el hecho **medido cuatro
  veces** (`dayz-control-plane-gotchas.md`: `pos=[7500,0,7500]` -> `pos_real y=313.14`).
- Otro revisor declaro que **«ningun fichero produce `box_claimed`»** buscandolo en
  `daemon.py`. El emisor vive dos saltos mas alla, en `session_coordination.py` dentro de
  `box_wait_touch`, y se llega por `loopback.py`.

Los dos abrieron ficheros y citaron `path:line`. Verificar no basta: hay que verificar en
**la capa donde viviria el comportamiento**.

### Reglas

1. **Antes de declarar que un verbo NO hace algo**, mira si su cuerpo termina en
   `call_bridge`. Si termina ahi, lo unico honesto es `no verificable desde el lado
   Python`, y decir que habria que abrir `MCPBridge.c` para decidirlo.
2. **Antes de declarar que un campo no se produce**, no te fies del modulo donde la
   arquitectura supuesta lo colocaria. Grep del nombre del campo en TODO `tools/dayz_mcp/`.
3. **Antes de contradecir un comportamiento documentado**, grep el vault. Es memoria de
   MEDICIONES: contradecir una medicion exige refutar la medicion, no leer codigo de otra
   capa. Cuesta cinco segundos.
4. **Asimetria util**: para afirmar que algo SI ocurre basta verlo una vez. Para afirmar
   que NO ocurre hay que haber mirado donde ocurriria.

### Al escribir un brief de revision

Si el workspace de la lane contiene **una sola capa**, dilo en el brief y exige que todo
lo relativo a las otras vaya a `LO_NO_VERIFICADO`. En la corrida que origina esta seccion
el brief no lo decia, y las dos lanes rellenaron el hueco con inferencia en vez de con una
declaracion de ignorancia. **Un «no verificable» bien puesto vale mas que un hallazgo
brillante y falso**, porque el falso viaja: cuando llego la refutacion, otra sesion ya
habia aplicado un arreglo a algo que no estaba roto.

## (added 2026-08-29, SP-351) La caja es compartida: entra en la FIFO, no esperes aviso — y el oraculo es el EFECTO

### El `blocked_on` de `session_status` es una ORDEN, no decoracion

Con la caja ocupada, `session_status` devuelve literalmente:

    "blocked_on": "DayZ test box; next: call dayz_test_run(..., wait_for_box_s=<n>) to join the box FIFO"

Medido el 2026-08-29: una sesion NOCTURNA AUTONOMA leyo esa linea en cada consulta durante
**siete horas y tres cuartos** y se quedo esperando a que otra sesion le avisara de que
soltaba. La cola existia, estaba nombrada en la respuesta, y no se uso.

Cuando por fin se uso: `wait_for_box_s=600` -> `active_run_exists` con
`hint: "stop it with dayz_test_stop(run_id=...)"`. Otra vez el siguiente paso servido en la
respuesta. Y al poner un plazo de 15 min a la sesion vecina, solto en dos — llevaba horas
defendiendo una fixture que **nunca se habia usado** (su propia captura daba
`frame_client_all_black`, cero actividad de cableado en su server).

**Reglas**:
1. Si una tool te dice como desbloquearte, hazlo antes de esperar a nadie.
2. **En una sesion autonoma no existe "esperar aviso".** O entras en la cola del recurso o
   le pones un plazo a quien lo tiene. Esperar sin horizonte no es cortesia: es ceder el
   encargo. Un horizonte del tipo «cuando el usuario termine» **no es un horizonte**: es
   una dependencia sin plazo, y quien lo ofrece deberia soltar el recurso y volver a
   pedirlo (relanzar cuesta minutos; una fixture se rehace en dos verbos).

### El oraculo es el EFECTO, nunca la respuesta

`ok` NO significa exito, y hay al menos cuatro codificaciones distintas conviviendo.
Medido in-game el 2026-08-29, misma tool, misma respuesta, efecto opuesto:

    object_delete(999999999) -> ok:1, deleted:0     <- no borro nada
    object_delete(<id real>) -> ok:1, deleted:1     <- borro

Receta verificada, un oraculo por verbo:

| lo que quieres saber | NO mires | mira |
|---|---|---|
| ¿coloco donde pedi? | `ok` | `surface_query(x,z).y` contra `pos_real` de `world_spawn` |
| ¿borro algo? | `ok` | `deleted` |
| ¿respawneo? | `ok` / `requested` | `query_player_state.pos` ANTES y DESPUES |
| ¿la espera se cumplio? | `ok` | `satisfied` |

### `player_respawn` funciona headless, y SOLO desde la death screen

Verificado 2026-08-29 (run `02524f97`): mata al jugador con dano externo
(`world_spawn` de infectado vivo con `flags=3108` al lado; la caida NO sirve con un panel
abierto), espera a que la captura pase por sus tres fases —normal, **desaturada con
sangre** (inconsciente), **completamente negra** (muerto)— y entonces `player_respawn()`
dispara la secuencia vanilla («Aparicion en 8 s»). Medido: la posicion salto ~1.878 m.

**Trampa**: sobre un jugador VIVO devuelve exactamente lo mismo (`ok:1, requested:1`) y no
hace NADA — posicion byte-identica. La respuesta no distingue los dos casos; la posicion si.

### `key_press` entrega un DIK a la mission, no es input del sistema operativo

`key_press(dik=1)` devuelve `delivered:1` y **no** abre el menu vanilla (`ui_tree` ->
`no_menu`). No es un fallo: su descripcion dice «a mission callback, not OS input», y el
menu vanilla no cuelga de `OnKeyPress`. Sirve para UIs modded que SI cuelgan de ahi. No lo
uses como sustituto de ESC del sistema, y no declares el verbo roto por ese test.

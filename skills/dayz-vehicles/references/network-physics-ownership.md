# Red, fisica y ownership: quien manda sobre la pose

Extraido de `SKILL.md` (corte 3, 2026-08-15). Aqui vive el DETALLE; el enunciado
corto y cuando leer esto estan en el indice `## ARCHIVO DE LECCIONES` del SKILL.md.
Nada de este fichero esta derogado: son lecciones vigentes, ordenadas por tema en
vez de por fecha.

---

## (added 2026-06-28) Ownership de red: seat forzado server-side != ownership del cliente; PHYSICS lo conduce el owner

Invariante verificada (source + in-game, DayZ-MCP Fase 5 S0). PREFLIGHT antes de cualquier intento de
conducir/automatizar un coche desde un peer cliente o de razonar sobre "quien conduce":

- El coche es un **Pawn** (`Transport extends Pawn` bajo `FEATURE_NETWORK_RECONCILIATION`,
  transport.c:53 -> Car car.c:98 -> CarScript carscript.c:170). El `IsOwner()` de `IsServerOrOwner()`
  (carscript.c:3222-3231) es el **ownership de red del COCHE**, no del player (glosario pawn.c:5-8:
  Owner = el cliente que controla el pawn).
- **`IsServerOrOwner()` NO gatea el throttle.** Sus unicos consumidores son teardown/fluidos
  (carscript.c:822/850/986). El throttle->fisica es **proto native** (`SetThrottle` car.c:202, "future
  throttle value") y lo aplica el **simulador del cuerpo = el OWNER**. El unico `SetThrottle` de script
  (carscript.c:1377) esta muerto en produccion (`#ifdef DIAG_DEVELOPER`).
- Un coche **sin cliente-dueno = `IsAuthorityOwner`** (autoridad sin owner, pawn.c:199-200) -> lo
  simula el server -> un `SetThrottle` server-side **SI lo mueve**. Esto es un **artefacto de
  single-box/SP**, NO prueba de que el server conduzca coches que un cliente posee. (DayZ-MCP S0 F2:
  server movio un PHYSICS car pos_delta=2.29 porque ningun cliente lo poseia.)
- Un **`StartCommand_Vehicle` server-side** (p.ej. el `vehicle_enter` del MCP) sienta al player SOLO
  server-side: el cliente **nunca obtiene `GetGame().GetPlayer().GetCommand_Vehicle()` ni el ownership
  del coche** (medido in-game x6, da `not_seated` en el peer cliente). El get-in real
  (`ActionGetInTransport.Start()`, metodo compartido cliente+server, actiongetintransport.c:82-98) corre
  `StartCommand_Vehicle` en el Human **DEL CLIENTE** + reserva asiento por juncture
  (`AddInventoryJunctureEx`/`SetVehicle`, :141-161). La transferencia de ownership es proto-native (no
  existe `SetNetworkOwner` en script).
- **Consecuencia practica:** para conducir/medir **owner-side** desde un cliente, el cliente debe
  **tomar ownership el mismo** (get-in client-side), no depender de un seat forzado server-side. Y un
  test de owner-authority en **single-box** esta **confundido** (el cliente nunca posee de verdad) ->
  el discriminador limpio es un dedicado 2-maquinas con un cliente remoto que hace el get-in.
- Lectura de diagnostico: `IsOwner()` (pawn.c:194), `IsAuthorityOwner()` (pawn.c:199-200),
  `GetOwnerIdentity()` (pawn.c:209), `GetNetworkID()` (object.c:815). Extiende el caso get-in/radial
  (LL-164) a la dimension de red. Origen: DayZ-MCP S0 (2026-06-28).
- **Conducir owner-side desde script (el actuador — verificado in-game 0→39 km/h):** `Car.SetThrottle/SetSteering/
  SetBrake` llamados desde el MISSION (`OnUpdate` / un job) NO mueven el owner-sim PHYSICS — **`super` de
  `CarScript.OnInput(dt)` (`carscript.c:1303`) los PISA cada frame** con el input=0 del driver local. Fix: aplicar
  el throttle DENTRO de un `modded class CarScript.OnInput`, **TRAS `super.OnInput(dt)`** (donde el autopiloto debug
  vanilla `carscript.c:1377` lo hace). NO hay inyección vía `HumanInputController` (el input de vehículo es nativo,
  sin API de override). Síntoma: "el coche es del owner pero `SetThrottle` no lo mueve". Origen: DayZ-MCP Fase 5 (SP-032).

## Angular velocity is NOT yaw/pitch/roll; derive omega from the pose delta (SP-170, origen LFHeli 2026-08-05)

`dBodySetAngularVelocity` takes angular velocity as rotation around x, y and z, **not
yaw/pitch/roll** — vanilla spells it at `enphysics.c:163`: *"Angular velocity,
rotation around x, y and z axis (not yaw/pitch/roll)"*. The Enfusion axis map is
yaw → Y, pitch → Z, roll → X (right-hand rule). Cross-checked on two independent
vanilla sources: `YawPitchRollMatrix("70 15 45", mat)` at `enmath3d.c:125-131`
matches the COLUMNS of `Rz(pitch) . Ry(yaw) . Rx(roll)` to 4e-7;
`dayzplayercameravehicles.c:137-139` reads `dBodyGetAngularVelocity(vehicle)` and
routes Y to yaw, Z to pitch, X to roll for camera lag. Corollary: `mat[i]` from
`GetTransform` (`enentity.c:288`) and from `YawPitchRollMatrix` are world-space
BASIS VECTORS (columns), not rows — mixing them up flips the sign of any rotation
derived from those matrices.

The trap that bites: if the solver keeps rate accumulators in deg/s (`m_PitchRate` /
`m_RollRate` / `m_YawRate`), those rates are NOT the derivative of the orientation
that gets written once a later step moves the pose without touching them (a
levelling stabilizer, a cosmetic pendulum adding a roll delta, a takeoff
level-assist). Feeding them as omega commands a rotation that the next
`SetOrientation` contradicts — that is the "body fighting the pose" judder.

Recipe: derive omega from the REAL pose delta, never from the accumulators.

    GetTransform(before);
    SetOrientation(target);
    GetTransform(after);
    // w*dt = 1/2 * sum_i (b_i x a_i) over the three basis vectors
    dBodySetAngularVelocity(this, sum * (0.5 / dt));

Exact to O(theta^3) (the per-tick delta does not reach 6 deg), immune to the
pendulum or stabilizer moving the pose on their own, and automatically ZERO at
call-sites that command the sampled pose (transition holds, ground clamp) with no
extra branch. Benign failure: if `SetOrientation` does not refresh the transform
on the same tick, `after == before`, omega = 0, behaviour identical to before.

## PHYSICS = prediccion del owner con reconciliacion: escribir pose pelea con ella (SP-180, added 2026-08-06, LFHeli F-01)

Extiende la seccion de ownership de arriba. Invariante verificada (runtime + fichero, LFHeli 2026-08-06).
PREFLIGHT ante CUALQUIER sintoma de "lag de input" / "rubberband" / "el cliente revierte transforms" en un
CarScript server-authoritative:

- **Mide la estrategia ANTES de teorizar** (1 linea, cualquier lado): `Print(GetNetworkMoveStrategy().ToString())`
  — NONE=0, LATEST=1, PHYSICS=2 (`pawn.c:138-148`; getter proto native `pawn.c:218` — SI esta expuesto a script;
  una nota previa que decia lo contrario costo 3 semanas de desvio en LFHeli). En DayZ 1.29 CarScript corre
  **PHYSICS de serie** (medido `str=2 own=true` en el cliente piloto); no existe flag de config que la seleccione
  (verificado vanilla + Expansion): la fija el motor por clase nativa. `FEATURE_NETWORK_RECONCILIATION` es
  incondicional (`defines.c:64`).
- **Bajo PHYSICS el owner YA simula predictivamente** (contrato Pawn completo en vanilla: `pawn.c:256-329`
  ObtainMove/ConsumeMove/ReplayMove/RewindState; `CarScriptMove/OwnerState` `carscript.c:3198-3218`;
  `IsServerOrOwner()` `carscript.c:3222-3231`). Consecuencias:
  1. Un server que escribe pose/velocidad por tick (`SetOrientation`/`SetVelocity`) NO coopera: genera
     correccion continua owner<-authority = **lag estructural de ida-y-vuelta + snap-backs**. El sintoma se
     siente incluso en loopback (el RTT no es la unica latencia: tick server + replicacion + rewind).
  2. Escribir TRANSFORM desde el cliente owner se REVIERTE en ~0,3 s (medido LFHeli D1). No es un bug que
     depurar: es la reconciliacion funcionando. No gastes ciclos ahi.
  3. La via compatible es la de Expansion 1.28+: **fuerzas simetricas owner/server** (`dBodyApplyForce`
     `enphysics.c:146`, world space; commit gated por `dBodyIsActive && dBodyIsDynamic`,
     `ExpansionPhysicsState.c:209-218`) + input dentro del `PawnMove` nativo (su RPC legacy se APAGA bajo
     PHYSICS, `DayZExpansion CarScript.c:1014-1051`) + contrato Move/OwnerState custom con `super` primero
     (`ExpansionHelicopterScript.c:164-213`). El motor integra; nadie escribe pose.
- **Spike barato antes de comprometerse a esa arquitectura** (patron ForceSpike E, LFHeli
  `plans/2026-08-06-forcespike-e.md`): flag de tuning default-off + ventana de 1,5 s en la que ambos lados
  aplican la MISMA fuerza (contra-gravedad + pulso lateral en un eje que nada del modelo toca) y el server
  suspende su actuador cinematico; trazas por tick ambos lados; parser offline dictamina SI/NO/INCONCLUSO
  (`LFHeli_dev/tools/spike_verdict.py`). Trampas del harness ya pagadas: el abort debe ser SIMETRICO
  (motor/asiento/salida del estado de vuelo), la supresion de la tecla secuestrada va AGUAS ARRIBA de todos
  los consumidores del canal, y toda salida del estado de vuelo limpia la ventana.
- Estado de la evidencia: TODO MEDIDO. Vuelo de veredicto 2026-08-06: **SI** — 3 pulsos limpios en el
  owner (pendiente local ~1,6 m/s2 vs 1,5 teorica, ganancia retenida, reversion puntual <=30% por el
  desfase owner->server); el snap-back al EXPIRAR la ventana es el actuador cinematico reabsorbiendo
  (la razon de retirar la escritura de pose en la via completa); un pulso owner-only cerca del suelo
  (server sin armar por AGL) se revirtio 91% = la limitacion F4 en vivo. Percepcion del piloto: nula
  (0,15 g lateral durante un ascenso a 7-11 m/s) — el gate es telemetrico, no de feel.

## Armazon Pawn custom (Move/OwnerState): la escalera de tipos y sus reglas duras (SP-188, added 2026-08-06, LFHeli D3-1)

Continuacion de SP-180: cuando la via es "fuerzas + owner prediction", el PRIMER paso de
construccion es un armazon Pawn INERTE (tipos custom + hooks solo-log, vuelo intacto) — valida el
wiring con el motor antes de migrar ningun solver (orden de menor riesgo verificado contra el
corpus Expansion). Receta verificada por fuente vanilla + compile gate (LFHeli 2026-08-06):

- **Escalera de tipos** (deriva del ultimo peldano, no de Pawn*): `PawnMove -> TransportMove ->
  CarMove -> CarScriptMove` y `PawnOwnerState -> TransportOwnerState -> CarOwnerState ->
  CarScriptOwnerState` (`transport.c:11-50`, `car.c:89-93`, `carscript.c:135-152`).
  `TransportOwnerState/TransportMove` llevan transform + velocidad lineal + angular NATIVOS
  (`transport.c:13-23,:35-42`): **NO los dupliques en el estado custom**.
- **Hooks** (`pawn.c:238-311`, todos `protected event`): `GetMoveType`/`GetOwnerStateType` (el
  motor instancia los tipos EN CONSTRUCCION, `pawn.c:235,:244` — los overrides deben existir en la
  clase, no activarse tarde), `ObtainMove`, `ConsumeMove`, `ReplayMove` (bool: respeta el rechazo
  del super antes de procesar), `ObtainState`, `RewindState(state, move, inout NetworkRewindType)`.
  CarScript ya implementa Get*Type/ObtainState/RewindState (`carscript.c:3198-3218`) — super
  SIEMPRE y exactamente una vez (ObtainState/RewindState del super llevan `m_fTime`).
- **Serializacion**: `Write/Read` con super PRIMERO; NUNCA serializar `vector` (expandir a
  floats); `EstimateMaximumSize()` = super + 4 bytes por escalar (bool cuenta 4, conservador).
  El Move lleva los ejes RAW pre-authority-scale (la atenuacion/FSM se recomputan por tick de
  solve; hornearlas rompe el determinismo del replay). El latch/estado con memoria del solver va
  en el OwnerState (server -> owner), no en el Move.
- **`ReadRawLocal` DENTRO de `ObtainMove`** (R22 que costo una ronda: el orden nativo
  ObtainMove<->EOnSimulate NO esta expuesto a script; fiarse de la ultima lectura del tick puede
  serializar ceros/stale y tus gates de round-trip validan un cableado VACIO). Exige ademas que el
  gate de payload rechace la corrida si todos los samples van en neutro.
- **Instrumentacion del armazon inerte**: match owner<->authority por `GetMoveId()` EXACTO
  (muestreo determinista `id % 64 == 0` en AMBOS lados), nunca por reloj; `rewind` se loguea
  siempre (raro), `replay` solo muestreado (un rewind storm re-corre todos los moves pendientes e
  inunda el log del cliente, truncado a ~255 chars/linea); contadores agregados a 1 Hz.
- **"Inerte" lo es para el VUELO, no para la RED**: los tipos custom anaden payload por
  move/correccion y una asimetria Write/Read desincroniza al owner — el gate de payload existe
  para eso.
- Estado de la evidencia: TODO CONFIRMADO EN RUNTIME (vuelo LFHeli D3-1, 2026-08-06): el motor
  instancia los tipos custom y los transporta (G1), 94 moves muestreados con los 5 ejes exactos en
  ambos lados y 48 con payload no-cero (G2), 477 rewinds + 47 replays visibles en el owner (G3).
  Trampa del receptor: el script log de DayZ envuelve cada Print en comillas simples — un parser
  de logs debe hacer strip de la comilla pegada al ULTIMO token de la linea o el gate de payload
  da un falso FAIL en ese campo.
- CAVEAT medido en el mismo vuelo: la cadena script de CONTACTO no recibio NI UN callback del
  asiento skid-suelo (0 OnContact en todo el vuelo, con touchdown real via AGL) — el override de
  Car.OnContact NO garantiza contactos suaves de asentado. Antes de construir logica sobre
  contactos de un vehiculo, mide primero que el callback dispare para TU caso (un print one-shot);
  la via robusta candidata es EntityEvent.CONTACT + EOnContact, pendiente de validar.

## Attack/release state must read raw input (SP-201, added 2026-08-31)

**[CODE-VERIFIED; in-game A/B pending]** A first-order command filter such as
`cmd += (raw - cmd) * k` decays asymptotically and does not reach exact zero. A
boolean derived from the filtered working value (`cmd != 0`) therefore remains
active after release: attack constants stay selected and idle-only levelling or
damping never starts. Capture `m_<axis>Raw` when the input is read, keep the
filtered command separate, and derive activity only from the raw field on every
simulation side. Owner and server must use the same source; mixing raw owner
state with filtered server state creates a second disagreement.

## Forced sleep needs registration warm-up and a settled-state gate (SP-153, added 2026-08-31)

- **[IN-GAME VERIFIED]** Do not call `dBodyActive(this,
  ActiveState.INACTIVE)` in the `EEInit` tick. The collider may not finish
  registration, leaving visual and physical position split. Keep the body active
  for a measured warm-up (about 3 s in the verified case) before the first sleep.
- **[DESIGN REVIEWED; partial in-game gate]** Sleep only when speed is near zero
  and AGL is at the local surface. Do not impose a lower AGL bound: a settled
  pivot measured `-0.02 m`. Explicitly request `ACTIVE` while the body is not
  settled; merely stopping the repeated `INACTIVE` call does not wake a body.
- `ClampMinValue(name, value, minimum, fallback)` does not impose an upper cap;
  the fourth argument handles non-finite input. Apply a safety maximum at the
  consumer with `Math.Min(tuned, cap)`.

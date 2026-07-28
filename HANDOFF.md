# HANDOFF — DayZ Modding Knowledge Pack

<!-- LIVE-STATE:START -->
# DayZ Modding Knowledge Pack — Estado vivo · snapshot 2026-07-28 (madrugada, 2ª sesión)

**Última verificación real:** HEAD `e892f45` en `r21/phase01-foundation`, árbol
limpio, `main` intacto en `994cb77` y 63 commits por detrás. Suite **699 passed /
18 skipped** (una más: el test nuevo de casos vivos), `packctl validate` PASS con
cero findings, `packctl promote --check` **`WARN` con exit 0** y finding único
`PROMOTION-DRIFT operation_count=38`. Las 38 llevan `logical_target_ids =
["obsidian_snapshots"]` y `before_digest: absent` —el destino es por commit—; las
16 operaciones de skill tienen **drift cero**. Todo medido sobre el árbol.

`ciclos_en_este_objetivo: 1 (rollout py3d y cierre de BUG-018)`

## Rollout py3d EJECUTADO — BUG-018 resuelto en la práctica

Autorizado explícitamente. Las 8 skills consumidoras pasan de `py3d-1.2.0` a
`1.4.0`. **Readback independiente**, no leído de la salida del script: 101
ficheros antes y después, **0 perdidos**, 8 wheels sustituidos, 4 documentos
parcheados. Los 8 wheels hashean al sello. Backup fuera del destino en
`%LOCALAPPDATA%\DayZ-Modding-Knowledge-Pack\rollout-backups\py3d-1.4.0-20260728-030119847`,
con las 4 preimágenes y los 8 wheels viejos.

El reemplazo completo que habría borrado conocimiento en 7 de 10 destinos **nunca
se ejecutó**. La vía patch-only entregó el delta sin perder una línea: las 4
líneas retiradas en `dayz-animation-pipeline` fueron reemplazadas por su versión
actualizada (net +20), y `py3d-1.0.0-quirks.md` ganó una corrección de API real
(`py3d.read_p3d` no existe; es `py3d.P3D(open(...))`).

**La sesión 2 ya estaba implementada** en `3ffecdf` desde el 2026-07-26: el
aplicador es patch-only, fail-closed, con backup obligatorio fuera del destino y
CAS repetido tras el backup. No había que construir nada, solo revalidar.

## Wheel re-sellado (`7ad464c`) — el gate estaba rojo con razón

`4271ff0` endureció **la fuente del wheel** (`tools/py3d/py3d/__init__.py`:
caracteres de control en rutas de proxy, contrato de nombre en `add_proxy`, y la
copia de `raw_frame` que quita el aliasing). El sello `c635bf7e…` describía la
fuente de `913192d`, no la de HEAD. Nuevo sello **`8043b796…`**, derivado dos
veces. Decisión del usuario: re-sellar 1.4.0 en vez de subir a 1.4.1, asumiendo
que `1.4.0` designa dos contenidos sin cambiar de nombre de fichero;
`product-spec.md` lo dice explícitamente.

## AVISO VIGENTE — el destino muta solo, y ya van CINCO escrituras

Tres el 2026-07-27 (17:38:17, 19:39:59, 23:03:24) y **dos durante esta sesión**:
02:43:33 (SP-098) y 03:23:51 (regla del censo de rips), ambas de la sesión
concurrente de LFHeli. Las dos adoptadas byte-exactas (`2c1df33`, `bbd6a49`) y
adjudicadas (`2d0c9b7`, `e892f45`).

**Lo aprendido, que ahorra la próxima vuelta:** adoptar es lo que protege el
conocimiento y es barato; adjudicar es lo que caduca. La primera adjudicación de
esta sesión expiró entre dos commits propios. **No persigas el digest mientras su
escritor sigue activo** — comprueba que el fichero instalado lleva un rato quieto
y que el repo lo iguala byte a byte antes de firmar.

Las 5 preimágenes del rollout también habían caducado (drift aditivo del
2026-07-27 19:44-19:46). Re-fijadas contra el fichero vivo, con snapshot nuevo
`live-snapshot-2026-07-28` fuera del repo; el del 26 se conserva como registro.
Los 4 parches se forward-checkearon contra el fichero vivo **antes** de re-fijar.

## Hechos estructurales medidos

- Las 8 skills del rollout viven en `~\.agents\skills` como **junctions al árbol
  gestionado del plugin de Cowork**; `~\.claude\skills` no contiene ninguna.
  Intersección con las 15 del `promotion-map` = **0**, verificada, y confirmada
  empíricamente: se modificaron 12 ficheros en esas 8 y el gate no dijo nada.
- El `manifest.json` del plugin registra **skills por nombre/id, no ficheros**
  (cero referencias a `py3d-1.2.0`), así que renombrar el wheel dentro de una
  skill registrada no deja un huérfano para el reconciliador.
- La premisa de `3ffecdf` de que «las skills vivas son LF-only» **es falsa desde
  el 2026-07-27**: 5 de 11 destinos llevan líneas CRLF y `dayz-p3d-inspector`
  está volcada entera (496 CRLF / 4 LF).

## Deuda sin sesión asignada

- **Eval vivo**: los 4 casos de `blender-animation` están portados a
  `evals/live/cases/` (`315517e`) y el test de casos vivos generalizado. Reserva
  escrita: el veredicto medido a mano («baseline also passed 7/7» = VACUOUS)
  **no viaja** con el port, porque medía la ejecución sin skill, no el
  conocimiento sin skill.

  **B3b sigue en ❓ por un bloqueo de entorno, medido el 2026-07-28, no por falta
  de casos.** Primera ejecución real intentada con `claude-sonnet-5` / `medium`
  sobre `txa-add-spine-up-export`: los 10 runs devolvieron
  `LIVE-EVAL-RUNNER-INVALID exit=2` y el veredicto fue `INCONCLUSIVE`. La causa
  no está en el harness —que se comportó bien: no inventó veredicto ni contó la
  tanda como evidencia— sino en que **el CLI `claude` no tiene sesión iniciada**:
  invocado a mano devuelve `{"is_error":true,"result":"Not logged in · Please run
  /login"}` con exit 1. Autenticar el CLI es del usuario. Con sesión, la
  ejecución es un comando:
  `python -m packctl eval live --root . --case evals/live/cases/<id>.json --runner evals/live/runners/claude-code.py --report <dir>`
  con `PACKCTL_LIVE_EVAL_MODEL` y `PACKCTL_LIVE_EVAL_EFFORT` puestos.

  **Deuda de diagnosticabilidad que esa ejecución destapó**: el adaptador colapsa
  cualquier fallo en `exit=2` escribiendo solo `type(error).__name__`
  (`runners/claude-code.py:110-112`), sin el mensaje ni la salida del CLI. El
  informe repitió `runner-invalid` diez veces y hubo que invocar el adaptador a
  mano para ver el motivo. Propagar el `result` del CLI al informe son ~5 líneas.

  Un aviso para quien lo ejecute: `citations_resolve` exige que **todas** las
  citas resuelvan, y las de raíz `pack` se resuelven contra la raíz del repo
  (`live_evals.py:266-270`), no contra el workspace que ve el modelo —que solo
  contiene `.claude/skills/<skill>` y los fixtures. Si el primer resultado real
  sale `INCONCLUSIVE` por citas no resueltas, mira ahí antes que al conocimiento.
- **Integración de la rama**: 63 commits, `main` es ancestro y el fast-forward es
  trivial. El usuario decidió **no tocarlo aún** y decidir al cerrar r21.
- **`reports/`**: 39,2 → 0,85 MB. Quedan 48 directorios vacíos que rechazan el
  borrado con `UnauthorizedAccessException` incluso para leer su ACL; hacen falta
  `takeown`/`icacls`.

## Invariantes cerradas

- Git es la única fuente editable; las instaladas son despliegues. La adopción va
  del destino al repo, nunca al revés sin gate.
- Una adjudicación autoriza **un digest concreto**, caduca sola, y **tapa, no
  arregla** — por eso se adopta ANTES de adjudicar.
- Preimagen e historial causal son dos gates distintos. Firmar preimágenes no
  tapa historia (medido: 0 enmascarados).
- El gate de preimagen ve una operación por destino lógico, con un id cada una.
- Instrumentar mutando dicts ajenos exige snapshot en el momento de la llamada.
- Un gate que no puede ponerse rojo no es un gate — el del wheel lo demostró.
- Ninguna promoción real ni rollout sin autorización explícita del usuario.

**Gate de arranque:** declarar `Retomo DayZ Modding Knowledge Pack desde: e892f45
con el rollout py3d aplicado y BUG-018 cerrado · re-medir promote --check antes
de tocar nada, porque el destino muta solo y ya van cinco`.
<!-- LIVE-STATE:END -->

---

## Log histórico

### 2026-07-25 — Fase 04 py3d y validación 3D

- Se implementaron y verificaron los cuatro workstreams aprobados.
- Se distribuyen todas las piezas legalmente redistribuibles desde el pack.
- El backend externo ODOL queda excluido por diseño; se fija por hash y se
  prueba desde su checkout local.
- La revisión independiente añadió límites estrictos para float32, números
  enormes, normales de proxy, rutas NUL, mapeos winding ambiguos y fallos I/O
  al preparar el payload temporal del backend.
- El rollout se probó solo sobre copias desechables.

### 2026-07-25 — Fase 02 slices 1–2

- B19 cerró por RED→GREEN y corpus.
- Se añadió `LF_UIProbe` con staging LF/CRLF reproducible.
- B20 quedó bloqueado honestamente por un cliente MCP con clave cacheada
  obsoleta; no hubo bypass.

### 2026-07-24 — Prior art aprobado y promovido

- Se aprobaron tres deltas: API index v2 no bloqueante, build/release
  transaccional y dayz-labs como companion sin autoridad de lifecycle.
- El commit `13af7f8b59962bca6fded981ad75cd77a37616ef` superó el gate integral.

### 2026-07-24 — Fase 01 cerrada

- Se cerraron A1–A9 y B1–B5 con gate reproducible y source map completo.
- La transacción `c7b5366cc761a8038e52f6a2` promovió el commit de contenido
  `7a25432febc112a957a7c1ef7a7d2c16c221b24f` a las tres superficies.

### 2026-07-24 — Bootstrap

- Se fijó el ZIP previo por SHA-256.
- Se extrajeron y verificaron 138 archivos sin diferencias.
- Se inicializó Git y se creó el commit raíz exacto.

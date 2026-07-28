# HANDOFF — DayZ Modding Knowledge Pack

<!-- LIVE-STATE:START -->
# DayZ Modding Knowledge Pack — Estado vivo · snapshot 2026-07-28 (B20 medido)

**Última verificación real:** HEAD `94fbc13` en `r21/phase01-foundation`, árbol
limpio. **`main` sigue en `f87a59e`** y NO se ha adelantado: la Fase 02 no está en
verde. Sin remoto. Suite **755 passed / 18 skipped / 5 subtests**, `validate` PASS
con cero findings, y **`promote --check` en ROJO** (ver aviso 1).

`ciclos_en_este_objetivo: 2 (Fase 02 — B20, gate C1 y corpora)`

> Sube a 2, no reinicia: el objetivo es el mismo y solo ha caído B20. **El motivo
> por el que iba a haber un ciclo 3 ya no existe**: los tres checkouts que
> bloqueaban C1 están en disco y el corpus mide verde (ver «Qué hacer» §2). Lo
> que queda es trabajo normal de repo, no un bloqueo.

## B20 — CERRADO por medición en el engine

`SC-002` tenía una observación pendiente desde el 2026-07-25. Ya existe. DayZDiag
`1.29.163451`, sonda `LF_UIProbe`, `ButtonWidget.GetText`: `len=10` en LF y en
CRLF, valor `"Alpha\nBeta"`. **El motor inserta exactamente un salto de línea; no
concatena**, y normaliza el fin de línea (LF y CRLF dan bytes iguales). Eso
**refuta** el `ASSUMED` del spec, que decía lo contrario.

El parser lo implementa (`dba357e`) y **TraderX pasa de 42/46 a 46/46**. Detalle y
cadena de medición en `plans/2026-07-24-02-dayz-ui-lab.md` §B20 y en
`30_Sessions/2026-07-28-DayZ-Modding-Knowledge-Pack-fase02-b20-medido.md`.

**Ningún criterio se ha movido a `✓`.** Siguen **24 de 54**.

## Qué hacer a continuación

1. **Adjudicar `skill/dayz-vehicles`** en cuanto haya 60 min de quietud — es lo
   único que pone verde el gate (aviso 1).
2. **Gate C1 (`:95`) — el corpus YA está en disco y ya da verde.** El usuario
   autorizó clonar, y los tres referentes están en **`C:\Users\guill\DayZ-UI-Corpora\`**
   a los commits fijados por el research, **pin verificado**:

   | Referente | Commit | Layouts |
   |---|---|---|
   | `VPP-Admin-Tools` | `dc22e420df3b54e821055f9764da1e48f4a31e71` | 69 |
   | `DayZ-Expansion-Scripts` | `8d3a453b2b6786a0bef728dbdfdc9a1ef0383a9b` | 234 |
   | `TraderPlusV1` | `d0cd39f105fba57104bf93798129626228a263e6` | 16 |

   Medido con el parser ya cambiado: **319/319 público**, **46/46 TraderX**,
   **11/11 LFPG**, cero fallos. **No hay regresión** por el cambio de B20.

   Lo que falta para poder **escribir el `✓`** no es medir, es hacerlo
   reproducible desde el repo: un **runner de corpus commiteado** (hoy la medida
   sale de un script de scratchpad) y los **manifests de `:77`/`SC-010`** con
   commit/hash/licencia. Sin eso se estaría marcando un criterio con evidencia
   que no se puede re-ejecutar. Los tres repos **no se redistribuyen**: solo
   entran URL, commit y hash.
3. **Corpora (`:77`)** — ahora se pueden **verificar**, no transcribir: los tres
   están en disco. Va emparejado con el runner del punto 2.
4. **Tasks 3-5** del plan de fase (escenarios, render determinista, diff), offline.
   Es el tramo natural para delegar a Codex: código puro, sin engine de por medio.
5. **El escape inválido de `:91-92` ya es decidible.** Se dejó abierto por falta
   de corpus; ahora está medido: en los **365 layouts** (319 público + 46 TraderX)
   hay **cero** backslashes dentro de string, y solo **4** en total, que son las
   cuatro continuaciones de B20. Convertir un escape desconocido en error es
   seguro sobre ambos corpora. Hazlo con test RED→GREEN y cierra el tercio que
   falta del item.
5. **Promoción pendiente de `skill/rigorous-data-audit`**: las 36 líneas de
   `1312890` nunca llegaron a las raíces (la transacción se firmó sobre `8986bae`).
   Es repo-ahead benigno, verificado por hash de blob. Agrúpalo con la promoción de
   Fase 02 para no gastar dos transacciones.

## Lo que te va a morder si no lo lees

1. **`promote --check` cierra en ROJO, a propósito.** Dos
   `PROMOTION-TARGET-UNEXPLAINED` sobre `skill/dayz-vehicles`
   (`expected=27037cfb… actual=11722f3f…`). Novena escritura host-direct, a las
   20:55, insert-only, **ya adoptada al repo en `94fbc13`** — repo y las dos raíces
   son byte-idénticos ahora. Falta **adjudicar**, y no se hizo porque solo había
   **14,6 min** de quietud frente a los 60 exigidos. **Adoptar NO puede poner verde
   este finding**: mira el destino, y adoptar cambia el repo. Solo una adjudicación
   —o una promoción nueva— lo explica. No re-midas esperando otra cosa.
2. **No delegues nunca un `--basetemp` relativo ni concatenado.** Una ruta Windows
   con los separadores comidos aterrizó como directorio literal con una ACL que
   negaba `Remove-Item`, `takeown`, `icacls` y `robocopy`, y **rompía la colección
   de `pytest`**. Resuelto; el aviso se queda por la causa.
3. **`B3b` está fuera de alcance por decisión del usuario.** Sin API de pago no es
   alcanzable: `--bare` (`evals/live/runners/claude-code.py:28-43`) es lo único que
   esconde las skills globales del brazo de control, y es lo que se niega a leer la
   sesión OAuth. No lo reintentes.
4. **El harness de evals vivos tiene un fail-open, registrado y sin arreglar.**
   `_skills_tree_sha256` (`live_evals.py:201-211`) hashea `workspace/.claude/skills`
   (`:221`, `:233`), así que `LIVE-EVAL-ARM-CONTAMINATED` (`:446`, `:464`) prueba
   que ese árbol está vacío y **nada más**. Spike de aislamiento **sin empezar**.
5. **`@DayZ_MCP` no sirve como portador de test.** Su módulo `5_Mission` no
   compila: `CParser: quoted string not closed`, atribuido a
   `DayZ_MCP/scripts/5_Mission/mcpclientbridge.c`. Es del mod del usuario, no del
   pack, y no se ha tocado. Usa **`LFPowerGrid`**, que compila y está verificado.
6. **`Path.write_text` en Windows reescribe los finales de línea** de un repo que
   es LF por `.gitattributes`. Refrescar dos hashes convirtió 11.529 saltos. El
   blob queda bien, el árbol de trabajo no. Escribe con `write_bytes`.

## Método que ahorra sesiones (verificado hoy)

- **Para probar una sonda nueva no toques la allow-list sellada del launcher.**
  `extra_mods` acredita un `@Name` relativo bajo `P:\Mods`
  (`dayz_test_worker.py:183-197`) si el directorio es real y no un reparse point.
  Montarla sobre un proyecto aprobado evita reconstruir el launcher nativo y su CAS.
- **Para extraer layouts de una PBO de terceros: Mikero `ExtractPbo`** (instalado,
  en PATH). `PboViewer.exe` **no descomprime** las entradas `Cprs` y escribe los
  bytes comprimidos sin avisar; un LZSS a mano da texto que empieza bien y
  degenera. La extracción buena se valida sola porque **reproduce la baseline
  publicada de 42/46**.
- **`exit 0` de AddonBuilder no dice nada de los bytes.** Verifica la PBO entrada
  por entrada contra el fuente antes de creerte una fixture byte-sensible.

## Invariantes cerradas

- Git es la única fuente editable; las instaladas son despliegues. La adopción va
  del destino al repo, nunca al revés sin gate.
- **Adoptar protege el conocimiento y es barato; adjudicar caduca.**
- Un `mtime` que se mueve **no** prueba trabajo en curso; `git status --porcelain`
  sí. Un fichero commiteado conserva su mtime para siempre.
- Una adjudicación autoriza un digest concreto y **tapa, no arregla**.
- Un gate que no puede ponerse rojo no es un gate — y un gate que rechaza tu
  cambio puede tener razón.
- No declarar un criterio `✓` sin ejecutar su línea de evidencia.
- `validate` sobre ficheros sin rastrear no dice nada: `git add` y DESPUÉS validar.
- **Un mod que no compila pasa cualquier test que afirme sobre su texto.** Los tres
  tests de la sonda eran verdes con un `.c` que el motor rechazaba entero.

**Gate de arranque:** declarar `Retomo DayZ Modding Knowledge Pack desde: 94fbc13
con B20 medido y el gate de promoción en rojo · adjudicar dayz-vehicles con 60 min
de quietud verificada antes de tocar nada más`.
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

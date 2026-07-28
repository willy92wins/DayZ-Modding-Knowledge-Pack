# HANDOFF — DayZ Modding Knowledge Pack

<!-- LIVE-STATE:START -->
# DayZ Modding Knowledge Pack — Estado vivo · snapshot 2026-07-28 (B20 medido)

**Última verificación real:** HEAD `94fbc13` en `r21/phase01-foundation`, árbol
limpio. **`main` sigue en `f87a59e`** y NO se ha adelantado: la Fase 02 no está en
verde. Sin remoto. Suite **755 passed / 18 skipped / 5 subtests**, `validate` PASS
con cero findings, y **`promote --check` en ROJO** (ver aviso 1).

`ciclos_en_este_objetivo: 2 (Fase 02 — B20, gate C1 y corpora)`

> Sube a 2, no reinicia: el objetivo es el mismo y solo ha caído B20. Si llega a 3
> con C1 todavía abierto, el gate de escalada tiene razón — porque lo que falta de
> C1 no es trabajo de parser sino tres checkouts (ver «Qué hacer»).

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
2. **Corpora (`:77`)**: fijar builds, hashes y licencias. Es lo más rentable que
   queda offline; los datos están en
   `10_Projects/DayZ_UI_Research/research/2026-07-24-ui-positive-reference-corpus-codex.md`.
   Para TraderX se verifican localmente; para VPP/Expansion/TraderPlus serían
   transcripción, y conviene marcarlo como tal.
3. **Gate C1 (`:95`) — decidir, no intentar.** Exige `319/319` del corpus público
   y **VPP, Expansion y TraderPlus no tienen checkout en esta máquina**. Lo que
   falta son tres checkouts, no más parser. O se clonan, o C1 se replantea con el
   usuario. No gastes sesión dándole vueltas al parser.
4. **Tasks 3-5** del plan de fase (escenarios, render determinista, diff), offline.
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

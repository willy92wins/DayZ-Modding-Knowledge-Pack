# HANDOFF — DayZ Modding Knowledge Pack

<!-- LIVE-STATE:START -->
# DayZ Modding Knowledge Pack — Estado vivo · snapshot 2026-08-15 (PUBLICADO)

## El pack es público

<https://github.com/willy92wins/DayZ-Modding-Knowledge-Pack> — **público**, rama
por defecto `main`, release **`v1.0.0`** con el ZIP reproducible adjunto.

> **Ya hay audiencia, y eso cambia las reglas.** Un `push` a `main` es visible al
> instante, y borrar no deshace un fork ni un caché. Las invariantes que antes
> protegían un árbol privado —cero rutas privadas, cero bytes de
> VPP/Expansion/TraderPlus/TraderX, ninguna afirmación sin su `path:line`— ahora
> protegen algo que lee gente de fuera. **Corre `packctl gate` antes de cada push.**

## Estado medido el 2026-08-15 (no recordado)

- **HEAD `0134e56` en `main`**, árbol limpio, remoto sincronizado (verificado con
  `git ls-remote`, no supuesto). **18 commits** en esta sesión.
- La rama de fase `r21/phase01-foundation` queda en `64ba73a`, un commit por
  detrás. La fase está cerrada; **`main` es el tronco a partir de ahora.**
- Worktree principal: `C:\Users\guill\DayZ-Modding-Knowledge-Pack`. El de fase
  (`.worktrees\r21-phase01`) ya no hace falta para trabajar.

| Gate | Resultado |
|---|---|
| `packctl gate` | **PASS en los 7 checks** — primera vez entero en verde |
| ├ `validate` | PASS, 0 findings (claims · licencias · links · privacidad · skills · source-map) |
| ├ `build_reproducible` | **PASS** (antes SKIPPED: exige árbol limpio) |
| ├ `skills_ref` | **PASS, 16/16** con el validador externo re-pineado |
| ├ `python_compile` | PASS, 121 ficheros trackeados |
| ├ `evals` | PASS, 24 variantes |
| └ `packctl_tests` / `py3d_tests` | PASS / PASS |
| Suite completa | **816 passed / 18 skipped / 305 subtests** |

**Inventario**: 16 playbooks + `_shared`, 5 `tools/`, 16 notas en
`knowledge/vault-notes/`, **372 ficheros trackeados**.

**Criterios: 28 de 54.** Abiertos: `B3b`, `B6`, `B7`, `B8`, `C3`, `C6`, `C7`,
`C8` y los grupos **`E` (7), `G` (5) y `H` (6) enteros**, que son fases futuras
sin empezar — no deuda de la fase cerrada.

## Cómo se verificó la publicación (y por qué así)

Construir dos veces en la misma máquina prueba determinismo **en esa máquina**. Lo
que acredita que lo publicado sirve es otra cadena, y se ejecutó entera:

1. `git ls-remote` → local y remoto en el mismo commit.
2. **Descargar el asset de vuelta de GitHub** y hashearlo → idéntico al build local:
   `c12e7ceb8e71333e62bb2274e7494f55763c356a4889a8ab16de1ae494c4e918`, 4.445.820 B.
3. **Clonar el repo publicado desde cero** → `validate` PASS, 0 findings.
4. **Reconstruir desde ese clon** → mismo hash que el asset, **bit a bit**.

**Y esa cadena cazó una trampa que apuntaba al revés.** Cuatro ficheros daban
`SOURCE-HASH-MISMATCH` en el worktree principal. La lectura fácil era «lo publicado
está roto»; la verdad era que el índice, el clon y GitHub los tienen en **LF** y
solo mi checkout local conservaba una copia **CRLF** anterior a que
`.gitattributes` (`* text eol=lf`) aplicara. **Lo publicado estaba bien; la copia
local era la anomalía.** Renormalizados. Si vuelve a pasar: `git ls-files --eol` lo
dice en una línea.

## Qué entró hoy

**Puesta al día tras 16 días de repo quieto.** Las skills instaladas habían crecido
y el repo no lo sabía:

- **24 ficheros adoptados o fusionados** de 10 skills. Conocimiento verificado
  in-game: `DayzTemporarySkeleton` para ropa, el crash duro de CF sobre
  persistencia escrita sin CF, el buffer de ~52 KB del RPT diag.
- **`dayz-clothing` dentro** (13 rutas privadas sustituidas por marcadores) y
  **`dayz-persistence` con fila en la matriz** — cerraba un hueco por el que `A7`
  afirmaba cubrir el 100% cubriendo 14 de 16.
- **py3d 1.5.0** sincronizado desde el fork publicado, distribución renombrada a
  `py3d-dayz`, wheel re-sellado y verificado «reproducible AND pinned».
- **Nota de la arena `4_World`** sintetizada de 30,6 KB a 10,3: era el último hueco
  real de dominio (cobertura del pack sobre ella: **2 %**).
- **4 parches SP** aplicados (correctiva como input no auditado, orden del
  teardown, mirror-gap por contenido, paso UV con `SAT=0`).

**Tres defectos reales que ningún gate estaba viendo:**

1. **Dos skills con frontmatter que no es YAML válido** (`Use for: mod de ropa`,
   `persistence: OnStoreSave/…`). El validador interno las daba por buenas porque
   comprueba campos y topes **sin parsear el documento como YAML**.
2. **El pack se contradecía a sí mismo**: `dayz-ui-development.md` afirmaba que
   toda hoja `.layout` necesita bloque hijo, mientras el propio pack incluye la
   fixture que lo refuta y un gate que parsea 376/376 layouts sin él. **Tachado, no
   borrado**, con la evidencia: esa frase ya generó un detector cuya suite de 83
   tests dio verde certificando una spec falsa.
3. **El gate compilaba `reports/`**, gitignored, y fallaba por un venv abandonado.
   Ahora compila lo que git trackea, que es lo que se publica.

**Y `MANIFEST.txt` era falso**: declaraba 222 ficheros contra 267 reales.
`validate` no podía cazarlo —prueba que cada fichero coincide con su hash, que es
justo lo que un documento caducado con bytes intactos pasa siempre—. No se
re-inventarió a mano; ahora apunta a `manifest.json`, que se genera del árbol.

## El validador externo: dónde está y por qué importa

**No había muerto: se había publicado.** `skills-ref==0.1.1` en PyPI
(<https://agentskills.io>), pero **su ejecutable se llama `agentskills`**, no
`skills-ref` — por eso el gate no lo encontraba y el pin viejo (un commit de rama
ya inalcanzable) parecía una herramienta muerta.

```
python -m venv <root>
<root>\Scripts\pip install skills-ref==0.1.1
$env:PACK_SKILLS_REF_ROOT = "<root>"
```

Se pagó solo en cinco minutos: encontró las dos skills con YAML inválido. **Es el
argumento entero del criterio `A3`**: cuando la segunda implementación deja de
ejecutarse, la primera sigue dando verde por encima del hueco.

## Drift contra las skills instaladas: 20 ficheros, TODOS deliberados

**No es deuda. No lo re-adoptes.** Al medir repo contra `~\.claude\skills` sigue
saliendo diferencia, y cada categoría es una decisión tomada:

| verdicto | ficheros | por qué |
|---|---:|---|
| `MERGE` | 9 | **el repo va por delante A PROPÓSITO**: secciones restauradas que el destino había perdido. La promoción las devuelve, no al revés |
| `NEW-IN-TARGET` | 3 | los 726 KB de Three.js, excluidos por política y documentados en `THIRD_PARTY_NOTICES.md` |
| `SKIP-EXECUTABLE` | 7 | solo la localización de rutas: cero conocimiento |
| `ADOPT` | 1 | `model.cfg.template`: su única diferencia es el CRLF que se normalizó. **Adoptarlo lo reintroduce** |

## Las reglas que costó descubrir

**Adopción:**

1. **No adoptes payloads ejecutables.** La promoción los **localiza** por diseño;
   sus diffs medidos fueron **+33, +33 y +99 bytes** — la sustitución de ruta y
   nada más. Excepción: un ejecutable **sin ninguna ruta** (como `pack_skill.py`)
   sí entra, porque el motivo de la regla no aplica.
2. **Un borrado exige merge, no copia** — pero *líneas solo-repo* NO prueban
   pérdida. Compara **secciones**: si un encabezado falta, grepea la cadena en
   **todo el árbol** antes de decidir. Si aparece en otro fichero es reubicación
   (adopta ambos); si no aparece, es pérdida (restaura).
3. **Una skill con writer vivo no se adopta**, aunque el fichero concreto lleve
   días quieto.

**La señal más barata y que no falla: un puntero colgante.** El destino había
borrado la §1 de `build-packaging-and-debug.md` **conservando la referencia cruzada
a ella**. Un puntero a algo que ya no existe es un accidente, no una edición.

**Método:**

- **`read_text` aplica universal newlines**: un read-after-write que compara
  *texto* falla sobre un fichero CRLF aunque la escritura sea correcta. Compara
  **bytes**.
- **Un gate se calibra contra lo que protege.** El de compilación recorría más
  árbol del que se publica; el del nombre del wheel llevaba la distribución como
  literal y rompió su propio test al renombrarla. Ahora la **deriva**.
- **Un resultado catastrófico también delata al medidor**: un chequeo dio «se
  pierde TODO» porque su variable de ruta estaba mal y el corpus estaba vacío. La
  sospecha vale en los dos extremos, no solo con el `0.000`.
- **PS 5.1 mete BOM** con `Out-File -Encoding utf8` (no existe `utf8NoBOM`). Los
  mensajes de commit se escriben con la herramienta Write, y el BOM se comprueba
  con `git cat-file`, **no** capturando `git log` en una variable de PowerShell.

## Lo que queda

**Nada obligatorio.** Candidatos, por orden de valor:

1. **El linter pre-PBO de `DayZ_Tooling` → `tools/dayz-script-lint/`** (§Candidato
   futuro más abajo). Sirve a `B7` en parte. Dos condiciones: **BUG-029 resuelto
   antes de entrar** y el cambio de destino asumido — está registrado como decisión
   009 en el decision-log de ese proyecto, allí **en revisión**.
2. **Reconstruir el bundle del experto gráfico**, que quedó viejo y ya no refleja
   el pack (le faltan las adopciones, py3d 1.5.0, `dayz-clothing` y la nota de arena).
3. **`C3`** necesita `SC-007` (segunda máquina o segunda build cacheada) y `SC-008`
   (decisión de licencia del códec PAA/EDDS). **`C6`** necesita engine.
4. **75 parches SP pendientes** en la cola, casi todos contra skills de plugin que
   el pack no gobierna.
5. El gate de **Sorter V4** sigue abierto a propósito: el plan pide «solo los
   defectos conocidos» y no los enumera.

## Auditoría de huecos: lo que se dejó FUERA a propósito

Se midió cobertura de todas las notas DayZ del vault contra los 2,9 MB del pack.
Tras añadir la de arena, **quedan tres con hueco y ninguna entra**:

| Nota | Cobertura | Por qué NO entra |
|---|---:|---|
| `dayz-enforce-deep-gotchas` | 12 % | **6 de 10 claims son `[WIKI]`** = hint sin verificar, y el `product-spec` prohíbe en «Fuera de alcance» copiar snippets no verificados |
| `dayz-server-admin-ops` | 16 % | la nota **se marca a sí misma «Uso privado»**; 12 de 21 claims son `[WIKI]` |
| `japm-pbo-recovery-patterns` | 8 % | 3 rutas privadas, y documenta ingeniería inversa sobre el mod de un tercero identificado |

Las dos primeras vienen del wiki StarDZ (CC BY-SA, hechos reescritos). **No las
metas sin resolver antes su etiquetado**: el pack vale por ser pequeño y verificado,
no por ser grande. Si algún día se verifican esos `[WIKI]` contra `P:\scripts`,
entonces sí. **Y ahora el repo es público**, así que meter material con licencia
share-alike o marcado de uso privado ya no es un descuido interno.

Las 7 skills instaladas que el pack no gobierna (`codex-handoff-template`,
`gauntlet-loop`, `introspection-workflow`, `pre-output-discipline`,
`secrets-handling`, `youtube-research`) son **método de trabajo, no dominio DayZ**.
Meterlas diluye la definición del producto y arrastra atribuciones de terceros.

## Candidato futuro: el linter pre-PBO de `DayZ_Tooling` → `tools/`

**Aprobado como dirección el 2026-08-15; el código todavía no existe aquí** (vive
en el sobremesa). `script_validator.py`, 8 detectores semánticos sobre Enforce y
`.rvmat`, **78 tests**, stdlib-only, smoke reproducido byte-idéntico por dos
ejecutores: **7 % FP en LFPowerGrid, 0 % en LF_VStorage**, y un bug real encontrado
(`#ifdef SERVER` vacío). Encaja por forma con `py3d` / `dayz-ui-lab` / los demás.

**Sirve al criterio `B7`, que sigue abierto** — «simuladores offline reducen
iteraciones… fixtures positivas, negativas y límites explícitos». Ojo: `B7` enumera
validadores de config/loot/CE y esto es Enforce + `.rvmat`, así que lo serviría
**en parte**; no lo cierra solo.

**Dos condiciones de entrada:**

1. **`BUG-029` resuelto ANTES de entrar, no dentro.** El detector
   `LAYOUT-LEAF-MISSING-BRACES` implementa una regla falsa —la misma que este pack
   tachó en `dayz-ui-development.md`— y su suite de 83 tests dio verde certificando
   fidelidad a esa spec falsa. **En cuarentena no viaja**: un pack cuya tesis es
   «verde ≠ verificado» no puede distribuir un detector conocido-falso, y ahora
   además lo distribuiría en público.
2. **Entra como `tools/dayz-script-lint/`, no como skill.** La decisión 001 de
   `DayZ_Tooling` lo enrutaba a `dayz-pbo-build`, que **no está en este pack**.
   Cambiar de destino lo convierte en herramienta distribuible con source-map,
   licencia y mantenimiento público. Registrado como decisión 009 en
   `DayZ_Tooling/decisions/decision-log.md`, allí marcada **en revisión**.

## Puerta de arranque

`Retomo DayZ Modding Knowledge Pack, PÚBLICO en
github.com/willy92wins/DayZ-Modding-Knowledge-Pack (main, release v1.0.0, asset
verificado por hash y reproducido desde un clon limpio) · HEAD 0134e56 en main,
árbol limpio, remoto sincronizado, packctl gate PASS en los 7 checks y suite
816/18/305 · el drift contra las skills instaladas (20 ficheros) es DELIBERADO, no
deuda: no lo re-adoptes · el repo tiene audiencia, así que gate antes de cada push
· próxima acción: nada obligatorio; candidatos son el linter de DayZ_Tooling hacia
tools/ con sus dos condiciones, reconstruir el bundle del experto gráfico y los
criterios abiertos B3b/B6/B7/B8 y C3/C6/C7/C8`
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

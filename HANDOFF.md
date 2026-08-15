# HANDOFF — DayZ Modding Knowledge Pack

<!-- LIVE-STATE:START -->
# DayZ Modding Knowledge Pack — Estado vivo · snapshot 2026-08-15 (listo para publicar, sin publicar)

**Medido el 2026-08-15, no recordado:** HEAD `d2bba60` en `r21/phase01-foundation`,
árbol limpio, 7 commits nuevos hoy. **`main` sigue en `f87a59e`.** Sin remoto
configurado, y así se queda: el usuario decidió **preparar todo y no publicar aún**.

**El backlog de adopción está cerrado** (§«El backlog está CERRADO»). El pack
gobierna **16 playbooks** más `_shared`; el ZIP son **267 entradas**.

Gates medidos sobre `d2bba60`, salvo el hash del ZIP (ver nota):

| Gate | Resultado |
|---|---|
| `validate` | **PASS**, 0 findings (claims · licencias · links · privacidad · skills · source-map) |
| Suite | **816 passed / 18 skipped / 305 subtests** |
| Build reproducible | **dos builds byte-idénticos**, 4.452.073 B, **267 entradas** (hash abajo) |
| py3d | 220 passed / 10 skipped; wheel «reproducible AND pinned» |
| `packctl gate` | **todos los checks en PASS** — `skills_ref` 16/16, `python_compile`, evals 24 variantes, tests packctl y py3d |
| `promote --check` | FAIL — mide el drift local repo↔instaladas, **no** afecta a publicar |

> **El hash del ZIP se mueve con cada commit, incluido este.** `HANDOFF.md` NO
> viaja en el archivo, pero `sources/source-map.json` sí, y ahí vive el hash de
> `HANDOFF.md`. Escribir un hash de ZIP dentro de este bloque lo invalida al
> commitearlo: es autorreferencial. Por eso el valor va **atado al commit en que se
> midió**, nunca presentado como «el hash del pack». Sobre `d2bba60` el ZIP es
> `815901EB3E2290AFCB65EBF507A36D5465078D45ADA81621B13D8F6959D9DB32`, reproducible
> en dos builds limpios. Lo que se verifica es la **propiedad** —construir dos veces
> da lo mismo—, no un número concreto: en cuanto commitees este bloque, cambia.

`ciclos_en_este_objetivo: 1 (Poner el pack al día y prepararlo para publicar)`

> **Reiniciado a 1**: el objetivo anterior era «Backlog de adopción y cierre de
> Fase 02». Este es otro: puesta al día + preparación de release.

## Publicación: se puede, y el bloqueador no es legal ni de privacidad

Verificado **ejecutando**, no leyendo los `✓` del spec:

- **Sin rutas privadas en el ZIP.** Todo lo que parece una ruta es el marcador
  `C:\Users\<you>\` documentado en `README.md:316`. Un grep crudo da 15 «hits» y
  los 15 son marcador; uno de ellos es un test que **asierta** que `OneDrive` no
  aparece. Si vuelves a mirarlo, mira las líneas antes de alarmarte.
- **Cero bytes de VPP / Expansion / TraderPlus / TraderX.** Las corpora se pinean
  por hash con `redistributed_in_pack`, `license` y `source_url`; los únicos
  `.layout` que viajan son first-party (fixtures + probe).
- **Las 3 fixtures ODOL** están declaradas first-party y **autorizadas por el
  usuario para redistribución pública el 2026-07-25** (`fixtures.json`).
- **Licencias**: MIT raíz + `THIRD_PARTY_NOTICES.md` con py3d (copyright upstream
  preservado), spec-kit como adaptación y SE2Dev solo como oráculo no empaquetado.

**`A3` vuelve a ser verificable, y el gate está entero en verde.** El validador
externo se había dado por muerto porque su commit pineado ya no es recuperable
(`upload-pack: not our ref`) y el HEAD de `anthropics/skills` no conserva el
directorio `skills-ref/`. **La herramienta no murió: se publicó.** Vive en PyPI
como `skills-ref==0.1.1` (<https://agentskills.io>) y su console script se llama
**`agentskills`**, no `skills-ref` — por eso el gate no lo encontraba. Un pin a
versión de PyPI es además **más estable** que a commit de rama: es un artefacto de
release inmutable, justo la propiedad que el pin viejo demostró no tener.

```
python -m venv <root>
<root>\Scripts\pip install skills-ref==0.1.1
$env:PACK_SKILLS_REF_ROOT = "<root>"
```

> **Se pagó solo en cinco minutos.** Nada más enchufarlo encontró **dos skills con
> frontmatter que NO es YAML válido**: `dayz-clothing` llevaba `Use for: mod de
> ropa` y `dayz-persistence` llevaba `persistence: OnStoreSave/…`. Un `: ` sin
> comillas dentro de un escalar YAML se parsea como mapping anidado, así que un
> loader conforme rechaza esos ficheros. **El validador interno las daba por
> buenas**, porque comprueba nombres de campo, patrón del nombre y el tope de 1024
> **sin llegar a parsear el documento como YAML**. Eso es exactamente lo que `A3`
> quería de una segunda implementación, y el pack llevaba dos skills rotas.
> Arregladas; 16/16 validan.

**Antes de publicar, dos cosas que no son técnicas:**

1. **Publicar tu nombre.** `tools/py3d/pyproject.toml:20` y `setup.py:14` llevan
   `Guillermo` y `willy92wins@gmail.com` como autoría del paquete. Es correcto y ya
   es público en el fork, pero conviene que sea una decisión y no un descubrimiento.
2. **Publicar los playbooks con los que produces mods por los que cobras.** El
   `README.md` lo dice explícitamente en su primera línea. Decisión de negocio.

**Si publicas**, quedan: pasar `[Unreleased]` del `CHANGELOG.md` a una versión,
crear el repo y empujar. Nada más está pendiente por el lado del release.

## Lo que se hizo hoy

**`09f1552` — adoptadas 6 skills** (+431 líneas, **0 borradas**): aviation,
basebuilding, characters, mcp-verify, test-ingame, weapons. La compuerta se
re-comprueba **en el momento de copiar**, no con una medición anterior, porque
estas skills tienen writers vivos y cambian entre medir y actuar.

**`3604047` — py3d sincronizado desde el fork publicado y subido a 1.5.0.**
La dirección importa: **GitHub iba por delante del pack**, no al revés, y su copia
ya venía despersonalizada para release. Distribución renombrada `py3d` →
`py3d-dayz` (el módulo importable sigue siendo `py3d`). Wheel
`py3d_dayz-1.5.0-py3-none-any.whl`, SHA-256
`16eac9218cddb02b52b533540c0259c33d5e5b2d6ad2cd28444ef049d608a73b`, verificado
«reproducible AND pinned». `audit_p3d.py` movido a `tools/`.

**`2c14416` — `dayz-clothing` dentro**, con sus 13 rutas privadas sustituidas por
`<dayz-projects>` / `<tmp>`. De paso se cerró un hueco viejo: **`dayz-persistence`
no tenía fila en la matriz de compatibilidad**, así que `A7` afirmaba cubrir el
100% cubriendo 14 de 16.

**`0aabdad` — el gate compila lo que se publica**, no lo que haya suelto. Recorría
el filesystem y barría `reports/`, que está gitignored; fallaba con un
`PermissionError` de un venv abandonado antes de compilar nada real.

**`38eb4c8` — la rama estable se movió a `1.29.0.163709`** (DayZ se actualizó el
2026-08-15 a las 04:37). **El pin NO se subió**: hacerlo habría convertido una
medición en una suposición para las 16 filas de golpe. La matriz dice que la build
se movió y que nada se ha re-verificado contra ella.

**`b244589` — nota de la arena `4_World`**, sintetizada de 30,6 KB a 10,3. Era el
último hueco real de dominio: cobertura medida del pack sobre ella, **2 %**. Fuera
la contabilidad de producto y los recibos internos; dentro las invariantes de
motor. Las 4 citas de vanilla del patrón de fachada se **re-verificaron en
`P:\scripts`** en vez de heredarlas — y el chequeo mejoró el texto, porque la clase
base vive en `4_world\classes\`, que es justo lo que hace funcionar el patrón.

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
entonces sí.

Las 7 skills instaladas que el pack no gobierna (`codex-handoff-template`,
`gauntlet-loop`, `introspection-workflow`, `pre-output-discipline`,
`secrets-handling`, `youtube-research`) son **método de trabajo, no dominio DayZ**.
Meterlas diluye la definición del producto y arrastra atribuciones de terceros.

## Candidato futuro: el linter pre-PBO de `DayZ_Tooling` → `tools/`

**Aprobado como dirección el 2026-08-15; el código todavía no existe aquí** (vive
en el sobremesa). `script_validator.py`, 8 detectores semánticos sobre Enforce y
`.rvmat`, **78 tests**, stdlib-only, smoke reproducido byte-idéntico por dos
ejecutores: **7% FP en LFPowerGrid, 0% en LF_VStorage**, y un bug real encontrado
(`#ifdef SERVER` vacío). Encaja por forma con `py3d` / `dayz-ui-lab` / los demás.

**Sirve al criterio `B7`, que sigue abierto** — «simuladores offline reducen
iteraciones… fixtures positivas, negativas y límites explícitos». Ojo: `B7`
enumera validadores de config/loot/CE y esto es Enforce + `.rvmat`, así que lo
serviría **en parte**; no lo cierra solo.

**Dos condiciones de entrada:**

1. **`BUG-029` resuelto ANTES de entrar, no dentro.** El detector
   `LAYOUT-LEAF-MISSING-BRACES` implementa una regla falsa —la misma que este pack
   acaba de tachar en `dayz-ui-development.md`— y su suite de 83 tests dio verde
   certificando fidelidad a esa spec falsa. **En cuarentena no viaja**: un pack
   cuya tesis es «verde ≠ verificado» no puede distribuir un detector
   conocido-falso.
2. **Entra como `tools/dayz-script-lint/`, no como skill.** La decisión 001 de
   `DayZ_Tooling` lo enrutaba a `dayz-pbo-build`, que **no está en este pack**.
   Cambiar de destino lo convierte en herramienta distribuible con source-map,
   licencia y mantenimiento público. Registrado como decisión 009 en
   `DayZ_Tooling/decisions/decision-log.md`, allí marcada **en revisión**.

## El backlog está CERRADO. Lo que queda es deliberado

No hay nada pendiente de adoptar. Lo que sigue apareciendo al medir repo contra
destino es, entero, decisión tomada — **no lo re-adoptes creyendo que es deuda**:

| verdicto | ficheros | por qué se queda así |
|---|---:|---|
| `MERGE` | 6 | **el repo va por delante A PROPÓSITO**: son las secciones restauradas. La promoción las devuelve al destino, no al revés |
| `NEW-IN-TARGET` | 3 | los 726 KB de Three.js, excluidos por política y documentados en `THIRD_PARTY_NOTICES.md` |
| `SKIP-EXECUTABLE` | 7 | solo la localización de rutas: cero conocimiento |
| `ADOPT` | 1 | `model.cfg.template`: su única diferencia es el CRLF que el repo normalizó. **Adoptarlo lo reintroduce** |

**Cuatro secciones se restauraron porque el destino las había perdido de verdad**,
verificado buscándolas en TODO el árbol instalado, no diffeando líneas:
`DOOR MECHANISM SELECTOR` y el guard de get-in `SP-141` (`dayz-vehicles/SKILL.md`),
la §1 de `build-packaging-and-debug.md`, y —por segunda vez— la sección de
persistencia de `rigorous-data-audit`.

**La §1 es el caso que mejor enseña la diferencia**: el destino la había borrado
**conservando la referencia cruzada a ella** («Catches §1 (config-only assets»).
Un puntero colgante es un accidente, no una edición.

**Y el clasificador por líneas se equivocó en los dos sentidos.** Cuatro ficheros
que marcó `MERGE` eran adopciones: `prompt-conventions.md` tenía la sección
**invertida a propósito** el 2026-08-05, y el `SKILL.md` de `rip-vehicle-import` no
perdió 11 KB sino que se **reestructuró**, archivando el contenido en `history/`.
Adoptarlo solo habría sido destructivo; adoptarlo **junto a** esos ficheros no.
La lección: *«el repo tiene líneas que el destino no»* no significa
«se pierde conocimiento». Hay que leer qué cambió.

## Las reglas de adopción, ya con tres confirmaciones

1. **No adoptes payloads ejecutables.** La promoción los **localiza** por diseño
   (`decision-log` 2026-07-26). Hoy se volvió a medir: sus diffs son **+33, +33 y
   +99 bytes** — la sustitución de ruta y nada más. Cero conocimiento, y adoptarlos
   devuelve una ruta privada a la fuente distribuible.
2. **Un borrado en el diff exige merge, no copia.** Señal barata: delta de tamaño
   negativo, o `repo_only_lines > 0`. Verifícalo grepeando el destino por varias
   cadenas distintas de la sección que desaparecería.
3. **Una skill con writer vivo no se adopta**, aunque el fichero concreto lleve
   días quieto.

## Método: lo que se volvió a pagar hoy

- **`read_text` aplica universal newlines.** Un read-after-write que compara texto
  falla sobre un fichero CRLF aunque la escritura sea correcta. **Compara bytes.**
- **Un gate se calibra contra lo que protege.** El de compilación recorría más
  árbol del que se publica; el de nombre de wheel llevaba la distribución como
  literal y rompió su propio test al renombrarla. Ahora la **deriva** de
  `pyproject.toml`.
- **Un resultado catastrófico también delata al medidor.** Un chequeo de pérdida de
  conocimiento dio «se pierde TODO»: la variable de ruta estaba mal y el corpus
  estaba vacío. La regla vale en los dos extremos, no solo con el 0.000.
- **Los ficheros son LF.** `.gitattributes` declara `* text eol=lf`; un fichero
  CRLF en el árbol se clona como LF y su hash registrado sale mal para todo el que
  clone.

## Estado de criterios

**28 de 54.** `C2` y `C4` en `✓`, `SC-006` cerrado. Abiertos de Fase 02: `C3`
(necesita `SC-007`, segunda máquina o segunda build cacheada, y `SC-008`, decisión
de licencia del códec PAA/EDDS), `C6` (necesita engine), `C7` y `C8`. El gate de
Sorter V4 sigue abierto a propósito: el plan pide «solo los defectos conocidos» y
no los enumera.

## Bundle del experto gráfico

`C:\Users\guill\DayZ-Knowledge-Bundle-20260730.zip` — 14,1 MB, 2.124 ficheros,
interno. **Está 16 días viejo y ya no refleja el pack**: le faltan las 6 skills
adoptadas, py3d 1.5.0 y `dayz-clothing`. Si hay que reenviarlo, se reconstruye
desde este HEAD. El procedimiento entero está en
`30_Sessions/2026-08-15-DayZ-Modding-Knowledge-Pack-bundle-y-backlog-de-adopcion.md`.

## Puerta de arranque

`Retomo DayZ Modding Knowledge Pack desde: b244589 (2026-08-15) con el backlog de
adopción CERRADO y la auditoría de huecos hecha —24 ficheros adoptados o
fusionados, py3d 1.5.0 desde el fork publicado, dayz-clothing dentro, la nota de
arena 4_World sintetizada, 16 playbooks— y verificado publicable: validate PASS,
ZIP reproducible, cero rutas privadas y cero bytes de terceros · lo que aún sale al
medir contra las skills instaladas es deliberado, NO deuda, y las 3 notas del vault
que quedan con hueco están fuera a propósito (§Auditoría de huecos) · **el gate
está entero en verde**: el validador externo se re-pineó a `skills-ref==0.1.1` de
PyPI (ejecutable `agentskills`) y encontró dos skills con frontmatter no-YAML, ya
arregladas · **no queda ningún bloqueador técnico para publicar** · próxima acción:
si publicamos, versionar el `CHANGELOG` y crear el repo; si no, la cola de parches
de skill tiene 79 pendientes, 6 de ellos contra skills que el pack gobierna`
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

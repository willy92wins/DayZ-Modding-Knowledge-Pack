# HANDOFF — DayZ Modding Knowledge Pack

<!-- LIVE-STATE:START -->
# DayZ Modding Knowledge Pack — Estado vivo · snapshot 2026-08-15 (listo para publicar, sin publicar)

**Medido el 2026-08-15, no recordado:** HEAD `0aabdad` en `r21/phase01-foundation`,
árbol limpio, 4 commits nuevos hoy. **`main` sigue en `f87a59e`.** Sin remoto
configurado, y así se queda: el usuario decidió **preparar todo y no publicar aún**.

Gates de hoy sobre `0aabdad`:

| Gate | Resultado |
|---|---|
| `validate` | **PASS**, 0 findings (claims · licencias · links · privacidad · skills · source-map) |
| Suite | **816 passed / 18 skipped / 305 subtests** |
| Build reproducible | **dos builds byte-idénticos** → `CC4C7BD6FD64C462ADCC72C2746AEC893612637239ED518D810904348800414D`, 4.308.996 B, 253 entradas |
| py3d | 220 passed / 10 skipped; wheel «reproducible AND pinned» |
| `packctl gate` | FAIL **solo** por `SKILLS-REF-NOT-CONFIGURED` (ver §Publicación) |
| `promote --check` | FAIL — mide el drift local repo↔instaladas, **no** afecta a publicar |

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

**Lo único rojo del gate es `SKILLS-REF-NOT-CONFIGURED`, y NO es un defecto del
pack.** El validador externo pineado (`38a2ff82958afee88dadf4831509e6f7e9d8ef4e`)
**ya no se puede traer**: ese commit no existe en `anthropics/skills`
(`upload-pack: not our ref`) y su HEAD ya no tiene el directorio `skills-ref/`.
Consecuencia honesta: **`A3` está en `✓` por una medición que hoy no es
reproducible.** Su *sustancia* sí la cubre el validador interno del pack, que
impone el mismo tope de 1024 caracteres, el shape del front-matter y las reglas de
nombre — `skills` PASS con 16 skills. Lo que falta es el **contraste** con una
segunda implementación. Es una decisión tuya: re-pinear a un validador disponible,
o registrar que el cross-check externo no existe y quedarte con el interno.

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

## Lo primero de la próxima sesión

Queda backlog, y **`dayz-vehicles` tiene un writer VIVO** (SKILL.md escrito a las
15:51 de hoy, `SP-247` y `SP-249` en el mismo rato). Mientras esté vivo no se toca:
adoptar a mitad de una secuencia mete en el repo un estado internamente incoherente.

| verdicto | ficheros | bytes | qué son |
|---|---:|---:|---|
| `MERGE` | 7 | +37.924 | el repo va por delante en parte del fichero |
| `NEW-IN-TARGET` | 17 | +814.423 | **de los cuales ~726 KB son Three.js vendorizado** |
| `ADOPT` | 2 | +2.514 | crecimiento puro |
| `SKIP-EXECUTABLE` | 7 | +569 | solo la localización de rutas: cero conocimiento |

Los dos `MERGE` peligrosos: **`rip-vehicle-import/SKILL.md` (−11.513, 225 líneas
solo-repo)** y **`dayz-vehicles/SKILL.md` (186 líneas solo-repo)**. Compara sección
por sección antes de escribir.

**`rip-vehicle-import/assets/classify-viewer/` trae Three.js, GLTFLoader y
OrbitControls vendorizados (~726 KB).** Son MIT, pero entrar en el pack exige
entrada propia en `THIRD_PARTY_NOTICES.md`. Decisión pendiente: entran con su
notice, o el visor se referencia sin empaquetar las libs.

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

`Retomo DayZ Modding Knowledge Pack desde: 0aabdad (2026-08-15) con el pack al día
—6 skills adoptadas, py3d 1.5.0 desde el fork publicado, dayz-clothing dentro— y
verificado publicable: validate PASS, ZIP reproducible CC4C7BD6…, cero rutas
privadas y cero bytes de terceros · el único rojo es el validador skills-ref
externo, cuyo commit pineado ya no existe upstream · próxima acción: fusionar los
7 ficheros MERGE (rip-vehicle-import y dayz-vehicles, ambos con líneas solo-repo) y
decidir si entran los 726 KB de Three.js vendorizado`
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

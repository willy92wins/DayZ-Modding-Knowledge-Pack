# Grok peer — escritura en disco (no por stdout)

Referencia canónica del modo **peer** (y de la autoría de plan, que usa la
misma postura A): cuando el entregable es un archivo, no un juicio. Para los
roles de consejo (research / reconciliación / R21) manda el `SKILL.md`,
incluida la postura C (juez instrumentado); aquí no hay nada que te sirva.

Estado: 2026-08-15, revisado contra `grok 1.0.4 (d846eb93d9)`. La mecánica del
CLI vive en `grok-cli-gotchas.md`; el esqueleto de prompt, en
`prompt-patterns.md` §Peer; los estrenos reales, en `track-record.md`. Si
divergen, manda este archivo para todo lo que sea invocación de escritura.

## Problema

El orquestador invoca a Grok con el patrón de **consejero** (solo lectura). Grok
no puede escribir, el artefacto sale por `.text`, y el orquestador acaba
capturando stdout, parseando JSON y copiando el cuerpo del documento a disco a
mano. Es caro en tokens, frágil con markdown y acentos, y escala mal cuanto más
largo es el entregable.

La causa es deliberada: `--tools "read_file,grep,list_dir"` deja a Grok sin
herramienta de escritura. Verificado — si se le pide crear un archivo, informa
de que no puede y el archivo no aparece en disco (re-verificado en 1.0.4,
2026-08-15).

## Regla de routing

| Intención del handoff | Patrón | Artefacto |
|---|---|---|
| Opinión, research, reconciliación, review | Consejo (read-only) o C (instrumentado) | Solo stdout |
| Documento, spec, plan en disco, código, mutación del entorno | **Peer (write-to-disk)** | Archivo en path absoluto; stdout = recibo corto |

**No mezclar.** Pedir un `.md` con allowlist read-only obliga al copiado por
stdout. Pedir solo juicio sin allowlist expone el árbol a edición accidental —
y en este host, sin ni siquiera preguntar — con flag de permiso o sin él
(§siguiente).

Reparto vigente: `G7` manda la ejecución a **Codex por defecto**; Grok es el
suplente y se usa cuando Codex está bloqueado (cuota, filtro, runtime muerto) o
cuando el orquestador lo elige a propósito. El criterio de promoción está en el
`SKILL.md` §Routing gate.

---

## Lo primero: aquí nada pregunta, y no es el flag lo que lo decide

```toml
# %USERPROFILE%\.grok\config.toml:12-17 — leído 2026-08-22
[ui]
permission_mode = "auto"
```

El config NO trae always-approve, y aun así **la escritura ocurre sin pasar
ningún flag de permiso**. A/B medido el 2026-08-22, mismo prompt y mismo
allowlist con `search_replace`: sin flag → `end_turn` en 2 turnos, fichero en
disco, $0,0085; con `--always-approve` → idéntico. La doc añade que «CLI
overrides config for that process» (`22-permissions-and-safety.md:59-63`). Tres
consecuencias que gobiernan todo lo demás:

1. **`--always-approve` no es load-bearing para escribir**, pero se pasa igual:
   fija el modo con independencia del config del host —que ya cambió una vez sin
   avisar— y la doc lo prescribe para scripts y CI (`22:20-21`). Lo que NO se
   hace es sustituirlo por otro valor.
2. **En las corridas de juicio, lo único que separa a Grok del árbol es
   `--tools`.** No el modo de permiso. Omitir el allowlist no es «puede que
   edite»: es «edita y ejecuta sin preguntar».
3. **`--permission-mode acceptEdits` es una DEGRADACIÓN, no una salvaguarda.**
   El modo es **uno**, no capas aditivas: pasar `acceptEdits` por CLI pisa
   incluso el `--always-approve` del propio comando (medido, tabla de abajo) y
   deja a Grok en un modo que solo auto-aprueba
   ediciones (`22-permissions-and-safety.md:36`). Cualquier tool que no sea una
   edición cae en la «prompt policy», cuyos resultados documentados son
   «prompt you, auto-approve, **or auto-deny the call**»
   (`22-permissions-and-safety.md:134`); y `search_replace` ni siquiera está en
   la lista de tools que nunca preguntan (`22:144-152`).

Medido en dos sesiones distintas, con foto de hashes antes y después:

| Modo de permiso | Resultado |
|---|---|
| `--permission-mode acceptEdits` | `cancelled`, 1-4 turnos, **disco intacto** |
| `acceptEdits` **+** `--always-approve` | `cancelled` igual. **Añadir el flag NO lo salva** |
| `--always-approve` (= `bypassPermissions`) a secas | `end_turn`, 11-49 turnos, ficheros escritos |

(LFHeli 2026-08-07, 3 corridas peer paralelas: las 3 `cancelled` con `acceptEdits`
y las 3 completas al relanzarlas cambiando **solo** ese flag. MercedesAMGLF F5-F7
2026-08-06: 4 workspaces, 11 rondas, cuatro entregables reales de hasta 28 KB con
`bypassPermissions`.)

Que `acceptEdits` + `--always-approve` tampoco funcione es la prueba de que **el
modo es uno, no capas que se suman**: el último valor gana y `acceptEdits`
auto-acepta ediciones pero no *ejecución*, así que el runtime cancela en cuanto el
agente va a ejecutar algo — incluso cuando lo que iba a ejecutar era escribir por
shell («escribo por shell en trozos» fue su último texto antes de morir).

Sin error, sin warning — parece que Grok «se quedó pensando».

> **Señal de diagnóstico**: `stopReason != "end_turn"` con `text` cortísimo = flag
> de permiso, no falta de capacidad. No rediseñes el prompt.

---

## Dos posturas de escritura. Elige antes de redactar el prompt

(La postura **C** —juez con shell sobre copia, para MEDIR sin entregar— es de
juicio y vive en `SKILL.md` §Posturas. La comparativa completa está al final.)

### Postura A — escritor de documentos (por defecto para .md / .json / specs / planes)

Escribe y lee. **Sin shell, sin web, sin subagentes.** Es la contención más
fuerte que sigue produciendo un archivo, y cubre el 80% de los handoffs de
escritura — incluida la lane de autoría de plan del paso 1.

```powershell
& "$env:USERPROFILE\.grok\bin\grok.exe" `
  --prompt-file "C:\path\to\prompt.txt" `
  --cwd "<workspace>" `
  --tools "read_file,grep,list_dir,search_replace" `
  --deny "MCPTool" `
  --output-format json `
  --max-turns 40 `
  --always-approve `
  --no-memory `
  -m grok-4.6
```

`search_replace` **sí crea archivos nuevos**: se invoca con `old_string` vacío
(`~\.grok\bundled\skills\create-skill\SKILL.md:53`). No hace falta darle shell
para que produzca un fichero que no existía.

### Postura B — peer completo (build, scripts, medición)

Cuando el encargo necesita ejecutar cosas: correr un builder, empaquetar un PBO,
medir. Aquí no hay allowlist que valga y la contención es el denylist más las
fronteras del prompt.

```powershell
& "$env:USERPROFILE\.grok\bin\grok.exe" `
  --prompt-file "C:\path\to\prompt.txt" `
  --cwd "<workspace en %TEMP%>" `
  --disallowed-tools "Agent" `
  --deny "Bash(rm *)" `
  --deny "Bash(Remove-Item*)" `
  --deny "Bash(git push*)" `
  --deny "MCPTool" `
  --output-format json `
  --max-turns 120 `
  --always-approve `
  --no-memory `
  -m grok-4.6
```

### Qué hace cada pieza

| Flag | Rol |
|---|---|
| **Sin `--tools`, o con `search_replace` dentro** | La diferencia que importa. Es lo que decide si puede escribir. |
| `--prompt-file` | Prompt largo en un `.txt`. Evita el infierno de comillas de PowerShell y el mojibake de acentos. **Va solo: `-p` y `--prompt-file` son excluyentes** y combinarlos falla con exit 2 y 0 bytes. |
| `--cwd` | Workspace y contexto cargado. En postura B, **siempre `%TEMP%`** (§Disciplina). |
| `--always-approve` | No es load-bearing: el config está en `permission_mode = "auto"` y bajo `auto` la escritura ocurre igual sin flag (A/B 2026-08-22). Se pasa para FIJAR el modo pase lo que pase en el config del host — que ya cambió una vez sin avisar. **Nunca lo sustituyas por `--permission-mode acceptEdits`.** |
| `--no-memory` | La memoria cross-session está apagada por defecto y verificada apagada aquí, pero cuesta cero y blinda las lanes si algún día se enciende. |
| `-m grok-4.6` | Pin de modelo: el default puede cambiar bajo tus pies y las comparativas de coste/calidad dejan de significar nada. |
| `--disallowed-tools "Agent"` | Corta el spawn de subagentes. Se puede combinar con `--tools`: el denylist corre DESPUÉS del allowlist (`README.md:638`). |
| `--deny "Bash(rm *)"` / `Remove-Item*` / `git push*` | Denylist de lo destructivo. En Windows el verbo peligroso es `Remove-Item`, no solo `rm`. |
| `--deny "MCPTool"` | Bloquea la **invocación** MCP. El descubrimiento (`search_tool`) puede seguir enumerando; la mutación no. |
| `--max-turns` | Backstop. Un peer real gasta 29-49 turnos; con 20 lo estrangulas. |
| `--output-format json` | Un objeto parseable al terminar. |
| `--json-schema '<schema>'` | Opcional: valida el RECIBO mecánicamente (implica `--output-format json`). El cuerpo del entregable sigue en el path; consume `.structuredOutput`, no `.text`. Con JSON inline en el argumento, lanzar desde Bash. |

### Lo que un allowlist NO cierra

- **Las meta-tools de MCP sobreviven al allowlist.** «The final toolset retains
  requested tools **plus always-on MCP meta-tools**» (`14-headless-mode.md:82`;
  también en la fila de `--tools` de `14:34`). Por eso `--deny "MCPTool"` no es
  opcional aunque hayas acotado `--tools`: es lo único que corta la invocación.
- **`--deny` sigue vigente bajo always-approve** — deny rules, hooks y las `ask`
  que matcheen segmentos de shell se aplican igual
  (`22-permissions-and-safety.md:136`). Esa es tu red, no el modo.
- **Los hooks corren antes que todo y fuera del toolset del modelo**
  (`22:123`). Un allowlist estricto no dice nada sobre lo que hagan tus hooks.
- **Los `--allow` de bash se evalúan contra la cadena COMPLETA**, no por
  segmento: `--allow 'Bash(git *)'` autoaprueba `git status && rm -rf /`. Los
  `deny` sí se comprueban por segmento. **Apóyate en deny, nunca en un allow
  amplio.**
- **Los subagentes heredan el permission mode del padre, incluido
  always-approve** (`19-plan-mode.md:137`). Que hereden tus `--deny` **no está
  documentado**. Si no los necesitas, apágalos.
- **El sandbox no confina en Windows.** Los backends documentados son Landlock
  (Linux) y Seatbelt (macOS); fuera de ahí Grok registra un warning y continúa
  sin enforcement. No uses `--sandbox` como red de seguridad aquí.

---

## Disciplina de workspace (postura B, no negociable)

Lo que convirtió la primera ejecución delegada real (GunRacks C5: 29 turnos,
2,66 M tokens, 24/24 criterios en verde) en algo *verificable* no fue el prompt:

1. **Todo el trabajo del delegado a `%TEMP%`. Cero escrituras suyas en OneDrive
   ni en el árbol real.** Le quita de encima los bugs del árbol OneDrive y deja
   la publicación en manos del orquestador. `P:\` es un symlink al árbol
   OneDrive: tampoco vale como workspace.
2. **Foto de hashes de lo intocable ANTES de lanzar.** Después se *demuestra* que
   no tocó nada en vez de afirmarlo. Y es lo único que delata **una ronda que
   devuelve texto plausible sin haber tocado un byte** — ha pasado dos veces.

```powershell
Get-ChildItem "<árbol intocable>" -Recurse -File |
  Get-FileHash -Algorithm SHA256 |
  Export-Csv "$env:TEMP\baseline.csv" -NoTypeInformation
```

3. **El prompt le da el entorno ya resuelto.** Un delegado que tiene que
   adivinar el entorno gasta turnos y acierta a medias. Tarjeta de este host
   (rutas verificadas por `Test-Path` 2026-08-15, host WILLY) — pega las filas
   que el encargo use:

   | Herramienta | Ruta verificada |
   |---|---|
   | Python 3.14.3 | `C:\Python314\python.exe` |
   | py3d (import) | 1.2.0 en `%APPDATA%\Python\Python314\site-packages\py3d` |
   | py3d fork (source of truth) | `P:\py3d` / GitHub `willy92wins/py3d-dayz` (1.4.x) |
   | AddonBuilder | `C:\Program Files (x86)\Steam\steamapps\common\DayZ Tools\Bin\AddonBuilder\AddonBuilder.exe` |
   | Mikero ExtractPbo | `C:\Program Files (x86)\Mikero\DePboTools\bin\ExtractPbo.exe` |
   | Blender | `C:\Program Files\Blender Foundation\Blender 5.1\blender.exe` (también 4.3) |
   | DayZDiag | `C:\Program Files (x86)\Steam\steamapps\common\DayZ\DayZDiag_x64.exe` — solo informativo, ver frontera |

   Con py3d, di en el prompt CUÁL de las dos copias usar (divergen: la
   instalada es 1.2.0, el fork va por 1.4.x), y recuerda que sus gates
   `validate`/`verify`/`diff` son ciegos a la geometría — no valen como prueba
   de winding.

4. **Frontera de procesos: Grok NUNCA lanza ni mata procesos DayZ** (ni
   DayZDiag ni DayZServer). El ciclo in-game pertenece al orquestador vía el
   lifecycle guard de `dayz-mcp`; un peer que «prueba el PBO arrancando el
   server» rompe el lease compartido. Escríbelo como frontera en el prompt de
   cualquier postura con shell.

---

## Contrato del prompt: write-to-disk + recibo

El orquestador **no** pide el cuerpo del documento en la respuesta. Pide:

1. **Path(s) de salida absolutos** donde Grok debe escribir.
2. **La herramienta de escritura del CLI** — que es `search_replace`. `write` y
   `Write` **no son tool IDs**: son clases de regla de permiso. Nombrar una tool
   que no existe le hace perder turnos.
3. **Recibo corto en stdout** (status + paths + una línea de resumen).

### Plantilla de prompt (copiar a `--prompt-file`)

````
TAREA: <una línea, frontera de alcance clara>

ESCRITURA OBLIGATORIA:
- Escribe el entregable COMPLETO en este path (absoluto Windows):
  <RUTA_ABSOLUTA_DEL_DOC>
- Usa `search_replace` (con `old_string` vacío si el archivo no existe).
- NO pegues el cuerpo del documento en el chat.
- Si el path ya existe y no debes sobrescribir, PARA y reporta failed.

CARGA INICIAL (lee en este orden, máx ~7 rutas):
1. <ruta> — <por qué>
2. ...

ENTORNO YA RESUELTO (no lo adivines):
- <filas de la tarjeta de entorno que apliquen, con la invocación canónica>

FRONTERAS:
- NO salgas de <directorio o glob permitido>.
- NO ejecutes rm / Remove-Item / git push, ni toques secrets.
- NO lances subagentes. NO lances ni mates procesos DayZ.
- Un solo entregable. No "y luego también X".

CRITERIO DE HECHO:
- El archivo existe en disco al terminar.
- <criterios de contenido medibles: secciones mínimas, idioma, etc.>

SALIDA EN CHAT (solo esto; sin el cuerpo del doc):

## RECEIPT
```json
{
  "status": "ok|failed",
  "paths": ["C:\\...\\archivo.md"],
  "summary": "una línea",
  "verified": ["qué comprobaste tú, p.ej. secciones escritas"],
  "not_verified": ["qué no pudiste comprobar"]
}
```
````

---

## Receptor

1. Lanzar Grok con la postura A o B.
2. Parsear el JSON: `.text` (o `.structuredOutput` si hubo `--json-schema`),
   `.sessionId`, `.stopReason`, `.total_cost_usd`, `.num_turns`.
3. **`stopReason != "end_turn"` → entrega inválida.** Los valores documentados son
   `end_turn`, `max_tokens`, `max_turn_requests`, `refusal`, `cancelled`
   (`14-headless-mode.md:240-243`).
4. Extraer `paths` del bloque RECEIPT.
5. **Verificar en disco, no por el reporte**: `Test-Path`, `Get-Item`, primeros
   bytes (anti-BOM), balance de llaves si es código, `Get-FileHash` contra el
   baseline para probar que no tocó lo intocable.
6. **Leer cada archivo entregado** y revisarlo contra el plan/spec.
7. Consumir el archivo **desde disco**. Nunca reconstruirlo desde `.text`.
8. Cerrar el rastro: arbitraje por hallazgo al `council-scorecard.md` en el
   mismo paso, y `grok export <sessionId> <reviews/...>.md` si la corrida
   merece archivo.

### El visto bueno es un gate, no un trámite

La entrega de Grok **nunca** se promociona al árbol real directamente. El bucle
fijado por el usuario (2026-08-06, F1 de LFVehicleUI): *«tú revisas y hasta que no
des visto bueno le obligas a seguir mejorando»*.

1. Defectos → ronda de corrección con `-r <sessionId>` señalando **solo** lo roto.
2. Repetir hasta visto bueno propio.
3. Solo entonces copiar al árbol real, con hashes.

Iterar es barato (un `-r` cuesta ~12% de la corrida original, porque lee de
caché; la ronda 3 quirúrgica de la spec B de LFPowerGrid costó 716K tokens
frente a los 3,0M de la ronda de edición — el patrón «resume para rondas de
corrección del MISMO implementador» escala bien). Promocionar defectos es caro.
Guarda siempre el `sessionId`.

```powershell
& "$env:USERPROFILE\.grok\bin\grok.exe" -r "<sessionId>" `
  --prompt-file "C:\path\to\followup.txt" `
  --deny "Bash(rm *)" --deny "Bash(Remove-Item*)" --deny "Bash(git push*)" `
  --deny "MCPTool" `
  --output-format json `
  --always-approve
```

**Un `-r` NO sirve como revisor.** Arrastra el historial completo de la sesión
que implementó (`17-sessions.md:113-114`), y `--fork-session` tampoco: forkea la
conversación, no la limpia (`17-sessions.md:210`). Para una lane de revisión
independiente, sesión **nueva** que lea solo los paths en disco. Y si el
revisor también es Grok, la pareja funciona pero comparte familia: se declara
la degradación en el artefacto (`SKILL.md` §Preflight 2).

---

## Anti-patrones

1. **Allowlist read-only + «genera un documento»** → solo stdout → copiar a mano.
2. **`--permission-mode acceptEdits`.** Pisa el `--always-approve` del comando y
   mata la corrida en silencio. Es el fallo más caro de esta página.
3. **Nombrar `write` como herramienta.** Es `search_replace`.
4. **Pedir el documento completo en la respuesta** aunque Grok pueda escribir.
5. **Montar el brief en `-p` con comillas anidadas** en PowerShell. Usar
   `--prompt-file`, y solo (`-p` y `--prompt-file` son excluyentes).
6. **Tratar stdout como el artefacto** en vez de como recibo de entrega.
7. **Confiar en el reporte sin `Test-Path`** ni hashes.
8. **Dejarle escribir en OneDrive, en `P:\` o en el árbol real.** Workspace en
   `%TEMP%`.
9. **`--allow 'Bash(git *)'` amplio** creyendo que acota git.
10. **Confiar en `--sandbox` en Windows** como aislamiento.
11. **Mezclar «revisa y luego escribe el plan final»** en una sola sesión: un rol
    por sesión, un entregable por sesión de escritura.
12. **Usar `-r` de la sesión que implementó como si fuera un revisor ciego.**
13. **Dejar que un peer con shell toque procesos DayZ.** El lease es del
    orquestador.
14. **Hardcodear `C:\Users\<user>\...` en la invocación.** `$env:USERPROFILE`
    funciona en cualquier host.

---

## Comparativa rápida

| | Consejo (juicio) | **C (juez instrumentado)** | Peer A (documento) | Peer B (build) |
|---|---|---|---|---|
| `--tools` | `read_file,grep,list_dir` | `+ run_terminal_cmd` | `+ search_replace` | omitido |
| Shell | no | **sí (medir)** | no | sí |
| Subagentes | no | no | no | `--disallowed-tools "Agent"` |
| Permiso | `--always-approve` | `--always-approve` | `--always-approve` | `--always-approve` |
| Workspace | el del proyecto | **copia en `%TEMP%`** | acotado en el prompt | **`%TEMP%`** |
| Artefacto | `.text` | medidas + veredicto | archivo en disco | archivos + medidas |
| stdout | ensayo / hallazgos | hallazgos (`--json-schema`) | RECEIPT JSON corto | RECEIPT JSON corto |
| Receptor | cite-then-verify | re-medir lo decisivo | `Test-Path` + Read | + hashes vs baseline |
| Uso | R24, reconciliación, R21 | R21/R22 con gates que correr | docs, specs, planes | código, PBO, medición |

(C está definida en `SKILL.md` §Posturas — es una postura de juicio, no de
entrega.)

---

## Checklist de orquestador (copiar)

- [ ] ¿Es juicio o es entregable en disco? Juicio → `SKILL.md` (Consejo o C), parar aquí.
- [ ] ¿Postura A (sin shell) o B (con shell)? A por defecto.
- [ ] Si es B: workspace en `%TEMP%` + foto de hashes de lo intocable, ANTES de lanzar.
- [ ] Prompt en fichero (`--prompt-file`, solo, sin `-p`).
- [ ] Paths de salida **absolutos Windows** en el prompt.
- [ ] Tarjeta de entorno pegada (filas que apliquen, con invocación canónica).
- [ ] Instrucción explícita: no pegar el cuerpo en el chat; usar `search_replace`.
- [ ] `--always-approve`. **NO** `--permission-mode acceptEdits`.
- [ ] `--deny` de `rm` / `Remove-Item` / `git push` / `MCPTool`.
- [ ] `--disallowed-tools "Agent"` salvo que necesites subagentes.
- [ ] Frontera en el prompt: NO procesos DayZ, NO salir del workspace.
- [ ] `--max-turns` holgado (40 doc / 120 build) + `-m grok-4.6` + `--no-memory`.
- [ ] Tras la corrida: `stopReason == "end_turn"`, `Test-Path` de cada path, hashes.
- [ ] Leer los archivos y dar (o no) el visto bueno antes de promocionar.
- [ ] Guardar `sessionId`; arbitraje al scorecard en el mismo paso; `grok export` si merece archivo.

---

## Referencias locales

- `SKILL.md` — routing, preflight, posturas (incluida C) y roles.
- `references/prompt-patterns.md` §Peer — el esqueleto de prompt.
- `references/grok-cli-gotchas.md` — flags, tool IDs, permisos, costes medidos.
- `references/track-record.md` — estrenos del rol peer (GunRacks C5, WRX T6.4,
  DayZ_MCP, LFPowerGrid portátil) con sus lecciones.
- `%USERPROFILE%\.grok\docs\user-guide\14-headless-mode.md` — headless, `--tools`,
  `--output-format`, `--prompt-file`, `stopReason`.
- `%USERPROFILE%\.grok\docs\user-guide\22-permissions-and-safety.md` — modos,
  allow/deny, qué nunca pregunta.
- `%USERPROFILE%\.grok\README.md:593-640` — tabla autoritativa de tool IDs.

Binario: `$env:USERPROFILE\.grok\bin\grok.exe`. Si `grok` no está en el PATH de
la shell (abierta antes de instalar), usar siempre la ruta absoluta.

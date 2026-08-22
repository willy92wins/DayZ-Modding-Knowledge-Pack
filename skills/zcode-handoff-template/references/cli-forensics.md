# ZCode CLI — forense

Todo lo medido el 2026-08-22 sobre el CLI headless de ZCode 3.8.1 / agente
0.16.3. Léelo si aparece una GLM Coding Plan API key (entonces la vía se abre
entera) o si algo del `SKILL.md` no cuadra.

## Índice

1. Dónde vive el CLI
2. Desbloqueo si aparece una API key
3. Esquema de config (el que acepta el parser, no el que parece)
4. Flags: los que existen y los que mienten
5. Modos de permiso
6. Peligro de credencial cruzada
7. Endpoints y códigos de error observados
8. Catálogo de modelos
9. Descubrimiento de skills, comandos, hooks y plugins

---

## 1. Dónde vive el CLI

No es un ejecutable propio: es un bundle Node incrustado en el app de escritorio.

```
%USERPROFILE%\AppData\Local\Programs\ZCode\resources\glm\zcode.cjs
```

`resources\glm\.node-bundle-meta.json` lo declara:

```json
{ "runtime": "electron-node", "entry": "zcode.cjs",
  "platform": "win32-x64", "source": "apps/zcode-cli/packages/cli/dist/zcode.cjs" }
```

Corre con `node` pelado — probado con v24.14.1, no necesita Electron. Hay un
shim instalado en `%APPDATA%\npm\zcode` y `zcode.cmd` para poder escribir
`zcode` a secas (ese directorio ya está en el PATH, es donde viven los shims de
`codex` y `gemini`).

`zcode doctor` responde sin credenciales:

```
version: 0.16.3   process: zcode-cli   node: v24.14.1
platform: win32/x64   sea: no (optional)   default artifact: node-bundle
```

Subcomandos que funcionan **offline**, útiles para diagnóstico aunque no haya
auth: `doctor`, `version`, `skills list`, `plugins list`, `commands list`.

## 2. Desbloqueo si aparece una API key

Con una GLM Coding Plan API key (`https://z.ai/manage-apikey/apikey-list`,
Individual Coding Plan → Plan Overview), la vía headless se abre en dos pasos:

1. Añadir a `~/.zcode/cli/config.json` el bloque `provider` + `model` de §3,
   con la key en `provider.zai.options.apiKey`. **Copia de seguridad primero**:
   ese archivo guarda los servidores MCP vivos del usuario.
2. Probar: `zcode --cwd "<repo>" --mode plan --no-color -p "di OK"`.

Alternativa oficial: `zcode login` — pero su endpoint está caído (§7). La
variante manual del slash command (`/login zai-coding-plan-api-key <key>`)
escribe la key en el config por ti.

## 3. Esquema de config

Archivo de usuario del CLI: `~/.zcode/cli/config.json`. Distinto del config del
app (`~/.zcode/v2/config.json`) — no los mezcles.

```json
{
  "provider": {
    "zai": {
      "name": "Z.ai",
      "kind": "anthropic",
      "options": {
        "baseURL": "https://api.z.ai/api/anthropic",
        "apiKey": "..."
      }
    }
  },
  "model": { "main": "zai/glm-5.3", "lite": "zai/glm-5-turbo" }
}
```

Tres trampas verificadas:

- **`model.main` es una CADENA `provider/model`.** El parser
  (`parseModelTarget`) solo acepta string; si le das `{provider, model}` lo
  descarta **en silencio** y el CLI sigue diciendo `Model config is missing`.
  El mensaje de error no menciona el formato.
- **El provider necesita `baseURL` explícito.** Los ids `builtin:*` no se
  autoprovisionan: sin `baseURL` da `Model provider builtin:zai-start-plan is
  missing baseURL`.
- **`apiKey: ""` gana sobre el entorno.** La cadena vacía no es nula, así que
  bloquea la resolución por env sin decir por qué. O pones una key real, o
  omites la clave entera.

Esfuerzo de razonamiento: el catálogo mapea los niveles a
`output_config.effort` del protocolo Anthropic. Fijarlo desde config sería
`provider.zai.models."glm-5.3".reasoning.defaultLevel` — **lectura del bundle,
sin corrida que lo confirme**.

## 4. Flags: los que existen y los que mienten

`--help` los anuncia todos; el parser rechaza tres. Probado flag a flag.

| flag | estado |
|---|---|
| `-p` / `--prompt` | funciona (con `-p`, el prompt va posicional **al final**) |
| `--cwd`, `--mode`, `--no-color`, `--json`, `--verbose` | funcionan |
| `--disallowed-tools` | funciona (ej. `"Bash(git *) Edit"`) |
| `--attach`, `--resume`, `-c`, `--locale` | funcionan |
| `--max-turns` | **`Unknown option`** |
| `--settings` | **`Unknown option`** |
| `--allowed-tools` | **`Unknown option`** (pero sí existe `--disallowed-tools`) |
| `--target` | incompatible con `--prompt`; usa `-p "/goal ..."` |

**El fallo silencioso número uno:** un flag desconocido **no da error visible**.
Imprime el `--help` completo y sale con código 0. Si ves el help donde esperabas
una respuesta del modelo, no es que el modelo callara — es un flag que no
existe.

Que `--settings` no funcione tiene consecuencia operativa: **no puedes probar
con una config alternativa**; toda prueba toca el archivo real, con los MCP del
usuario dentro.

## 5. Modos de permiso

`--mode` acepta `build`, `edit`, `plan`, `yolo`. **El default de `--prompt` es
`yolo`** — shell sin freno sobre el `--cwd` que le des.

- juicio / research / revisión → `--mode plan`
- escritura acotada → `--mode edit` + `--cwd` al subárbol mínimo
- denegar herramientas → `--disallowed-tools`, porque `--allowed-tools` no existe

Nunca lanzar con `--cwd` en la raíz del vault o de `DayZ Projects` para una
tarea que mira dos archivos.

## 6. Peligro de credencial cruzada

El CLI resuelve la API key por entorno y **gana la primera que encuentra**. Para
un provider `kind: anthropic` el orden de candidatos es:

```
ANTHROPIC_API_KEY  →  <PROVIDER>_API_KEY (ZAI_API_KEY)  →  ZCODE_API_KEY
```

Traducción: si tienes `ANTHROPIC_API_KEY` exportada y lanzas `zcode`, **tu key
de Anthropic viaja a los servidores de Z.ai**. No es hipotético, es el orden de
resolución del bundle.

Defensa: key explícita en `provider.zai.options.apiKey` — el valor del archivo
gana sobre el entorno. (En esta caja, ninguna de las tres variables estaba
puesta al comprobarlo, ni en la shell ni a nivel de usuario.)

## 7. Endpoints y códigos de error observados

| endpoint | qué es | observado |
|---|---|---|
| `https://zcode.z.ai/api/v1/oauth/cli/init` | device-flow del CLI | **404, `Content-Length: 0`** |
| `https://zcode.z.ai/api/v1/zcode-plan/anthropic/v1/messages` | plan del app | `400 captcha verify failed` (3007) desde el CLI; `401` a pelo |
| `https://api.z.ai/api/anthropic` | protocolo Anthropic estándar | `401 token expired or incorrect` con las credenciales del app |
| `https://api.z.ai/api/coding/paas/v4` | endpoint OpenAI del Coding Plan | no probado |

Errores del CLI que conviene saber leer:

- `OAuth response is not valid JSON` → el 404 de arriba: parsea cero bytes.
- `ProviderBusinessError` con `providerCode` numérico → error del proveedor;
  cita el código tal cual (3007 = captcha del edge).
- `Turn execution failed (traceId: ...)` → **fallo de transporte**, no respuesta
  vacía del modelo. No concluyas nada sobre calidad a partir de esto.
- El detalle de cada corrida queda en `~/.zcode/cli/log/zcode-YYYY-MM-DD.jsonl`
  (JSONL con `event`, `traceId`, `durationMs`, `context`). Ese log es la fuente
  buena cuando algo muere: también registra qué servidores MCP conectaron y con
  cuántas tools.

## 8. Catálogo de modelos

Fuente: `resources\model-providers\models_catalog_china_llm_zcode_2026-06-03.json`,
provider `zai`, baseURL `https://api.z.ai`, path anthropic
`/api/anthropic/v1/messages`.

| id | contexto | salida | razonamiento |
|---|---|---|---|
| `glm-5.3` | 1.000.000 | 128.000 | `low`, `high`, `max` (default `max`) |
| `glm-5-turbo` | 200.000 | 64.000 | `enabled`, `off` |
| `glm-5.1`, `glm-5` | 200.000 | 64.000 | `enabled`, `off` |
| `glm-4.7`, `glm-4.6` | 200.000 | 131.072 | `enabled`, `off` |

El plan del app expone `GLM-5.3` y `GLM-5-Turbo`. Los ids del catálogo van en
minúscula; los del config del app en mayúscula — usa los del catálogo para la
API.

Públicos de GLM-5.3 (lanzado 14-08-2026, base 743B): Terminal-Bench 3.0 28,3 ·
DeepSWE v1.1 66,9 · Agents' Last Exam 28,5 · CyberGym 84,5% · ExploitBench
54,4%. Por detrás de Fable 5 y GPT-5.6 Sol en las dos primeras.

## 9. Descubrimiento de skills, comandos, hooks y plugins

Orden de escaneo (antes gana):

1. roots configurados explícitamente
2. `~/.zcode/skills` (o `commands`)
3. `~/.agents/skills` ← **aquí viven las 60 skills de esta caja**
4. `<repo>/.zcode/skills` (del cwd hacia arriba hasta la raíz del proyecto)
5. `<repo>/.agents/skills`
6. roots de plugins habilitados (mínima precedencia)

Skills: la identidad es la ruta, así que las homónimas se descubren todas pero
**solo carga la primera**; el resto queda ensombrecida. Comandos: la clave es el
nombre normalizado, primera coincidencia gana, y los directorios anidados unen
con dos puntos (`review/code.md` → `/review:code`).

Instrucciones: `~/.zcode/AGENTS.md` primero, luego el `AGENTS.md` del repo — el
del repo puede estrechar al del usuario. **Ninguno de los dos existe hoy.**

Hooks: solo siete eventos (`SessionStart`, `UserPromptSubmit`, `PreToolUse`,
`PermissionRequest`, `PostToolUse`, `PostToolUseFailure`, `Stop`) y los del
archivo de config exigen `hooks.enabled: true`.

MCP: `~/.zcode/cli/config.json` → `mcp.servers` (fallback
`~/.agents/mcp.json` → `mcpServers`). **Todos los scopes se conectan
automáticamente** al abrir sesión, incluido el del workspace: abrir un repo
ajeno conecta los servidores que declare.

La documentación oficial cubre app, plugins, skills, MCP y hooks
(`https://zcode.z.ai/en/docs`) pero **no documenta el CLI en absoluto** — todo
lo de este archivo es ingeniería inversa del bundle y observación directa.

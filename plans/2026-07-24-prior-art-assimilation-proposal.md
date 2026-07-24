# Propuesta de asimilación post-Fase 01

> **Estado:** propuesta para discusión; no modifica todavía los planes 02–06.
> **Snapshots revisados:** dayz-labs `dbd6ad3e54e30c81a9aeb88fcb9f60f007804c2a`,
> Lake-Dayz-MCP `ac56f369c3b1d91ec602d63e2b2a003ffa1212bb` y
> StarDZ `dbdcd23b02eae0cb612110644f61fdd0d08a0d4b`.
> **Política:** extraer requisitos y fixtures; no importar implementaciones,
> bases de datos, assets ni una autoridad de lifecycle paralela.

## Resultado

Los tres repos siguen en los commits ya fijados por Fase 01. No hay delta
upstream que invalide el inventario. El valor incremental real después de
`7a25432` es:

| Proyecto | Valor residual | Decisión propuesta |
|---|---|---|
| dayz-labs | Alto para contratos de preflight, build, publicación y UX operativa | Extraer requisitos a Fase 04/06; companion opcional y no autoritativo |
| Lake-Dayz-MCP | Alto para una segunda versión del índice API/config | Reimplementar selectivamente con procedencia y confinamiento propios |
| StarDZ | Bajo: la mayor parte útil ya está asimilada o planificada | Mantener como fuente de casos adversariales; no importar el monolito |

Ninguno sustituye `DayZ_MCP`, `dayz-ui-lab`, el corpus UI directo ni las
skills especializadas.

## Evidencia adjudicada

### dayz-labs

- `[EXACT]` El MCP expone lifecycle, build/preflight, Git/GitHub, Workshop,
  mutaciones CE y gestión de servidores:
  [DzlMcpTools.cs:26-73](https://github.com/Borcioo/dayz-labs/blob/dbd6ad3e54e30c81a9aeb88fcb9f60f007804c2a/src/Dzl.Mcp/DzlMcpTools.cs#L26-L73),
  [DzlMcpTools.cs:99-124](https://github.com/Borcioo/dayz-labs/blob/dbd6ad3e54e30c81a9aeb88fcb9f60f007804c2a/src/Dzl.Mcp/DzlMcpTools.cs#L99-L124),
  [DzlMcpTools.cs:166-228](https://github.com/Borcioo/dayz-labs/blob/dbd6ad3e54e30c81a9aeb88fcb9f60f007804c2a/src/Dzl.Mcp/DzlMcpTools.cs#L166-L228) y
  [DzlMcpTools.cs:262-313](https://github.com/Borcioo/dayz-labs/blob/dbd6ad3e54e30c81a9aeb88fcb9f60f007804c2a/src/Dzl.Mcp/DzlMcpTools.cs#L262-L313).
- `[EXACT]` Una bandeja viva es la autoridad preferida, pero si el pipe falla
  el control plane ejecuta directamente la misma operación; no existe en este
  contrato un lease ni un `run_id`:
  [ControlPlane.cs:6-20](https://github.com/Borcioo/dayz-labs/blob/dbd6ad3e54e30c81a9aeb88fcb9f60f007804c2a/src/Dzl.Core/Ipc/ControlPlane.cs#L6-L20).
- `[EXACT]` La terminación revalida PID y basename del ejecutable antes de
  matar el árbol, pero no identidad fuerte de proceso:
  [ProcessManager.cs:60-73](https://github.com/Borcioo/dayz-labs/blob/dbd6ad3e54e30c81a9aeb88fcb9f60f007804c2a/src/Dzl.Core/Launch/ProcessManager.cs#L60-L73).
  Esto es incompatible con convertirlo en autoridad concurrente al lifecycle
  request-bound del pack.
- `[EXACT]` El cache mezcla contenido y ajustes, e invalida por ejecutable y
  clave:
  [BuildCache.cs:48-105](https://github.com/Borcioo/dayz-labs/blob/dbd6ad3e54e30c81a9aeb88fcb9f60f007804c2a/src/Dzl.Core/Build/BuildCache.cs#L48-L105) y
  [BuildService.cs:558-580](https://github.com/Borcioo/dayz-labs/blob/dbd6ad3e54e30c81a9aeb88fcb9f60f007804c2a/src/Dzl.Core/App/BuildService.cs#L558-L580).
- `[EXACT]` Publica desde staging con backup y rollback:
  [ModBuild.cs:42-100](https://github.com/Borcioo/dayz-labs/blob/dbd6ad3e54e30c81a9aeb88fcb9f60f007804c2a/src/Dzl.Core/Build/ModBuild.cs#L42-L100).
- `[EXACT]` El preflight cubre paths, case, ODOL y frescura de texturas:
  [FileSystemRules.cs:17-41](https://github.com/Borcioo/dayz-labs/blob/dbd6ad3e54e30c81a9aeb88fcb9f60f007804c2a/src/Dzl.Core/Build/Preflight/Rules/FileSystemRules.cs#L17-L41) y
  [FileSystemRules.cs:70-110](https://github.com/Borcioo/dayz-labs/blob/dbd6ad3e54e30c81a9aeb88fcb9f60f007804c2a/src/Dzl.Core/Build/Preflight/Rules/FileSystemRules.cs#L70-L110).
- `[EXACT]` Su documentación formula correctamente el postcondition de build:
  no confiar solo en exit `0`, sino comprobar output nuevo y diagnosticar el
  log:
  [building-mods.md:94-99](https://github.com/Borcioo/dayz-labs/blob/dbd6ad3e54e30c81a9aeb88fcb9f60f007804c2a/docs/guides/building-mods.md#L94-L99).
- `[EXACT]` No se encontró soporte de watch de fuentes, secuencias de acciones
  ingame, diff de screenshots de DayZ, telemetría de script/FPS ni dos
  clientes. Su captura de pantalla pertenece a la aplicación WPF, no al juego.

**Adjudicación:** su mayor aporte no es el MCP, sino cuatro requisitos:
preflight ampliado, cache correctamente invalidable, postconditions del
artefacto y publicación transaccional.

### Lake-Dayz-MCP

- `[EXACT]` Distingue símbolos activos de declaraciones comentadas y registra
  métodos, guards y usos heurísticos:
  [index_local.py:28-43](https://github.com/ZeripeDaniel/Lake-Dayz-MCP/blob/ac56f369c3b1d91ec602d63e2b2a003ffa1212bb/index_local.py#L28-L43),
  [index_local.py:51-77](https://github.com/ZeripeDaniel/Lake-Dayz-MCP/blob/ac56f369c3b1d91ec602d63e2b2a003ffa1212bb/index_local.py#L51-L77) y
  [index_local.py:162-213](https://github.com/ZeripeDaniel/Lake-Dayz-MCP/blob/ac56f369c3b1d91ec602d63e2b2a003ffa1212bb/index_local.py#L162-L213).
- `[EXACT]` Indexa por separado la pertenencia a `CfgXxx`:
  [index_config.py:30-65](https://github.com/ZeripeDaniel/Lake-Dayz-MCP/blob/ac56f369c3b1d91ec602d63e2b2a003ffa1212bb/index_config.py#L30-L65).
- `[EXACT]` El repo no incluye el importador Doxygen que produjo
  `members`/`refs`. La DB solo declara timestamps y conteos, sin build DayZ,
  schema version, hashes de fuentes ni commit del parser. Por tanto no es un
  artefacto reproducible o adjudicable para el pack.
- `[EXACT]` `enforce_lint` y `check_config` leen cualquier path accesible que
  les entregue el cliente, sin allowed-root:
  [server.py:467-512](https://github.com/ZeripeDaniel/Lake-Dayz-MCP/blob/ac56f369c3b1d91ec602d63e2b2a003ffa1212bb/server.py#L467-L512) y
  [server.py:554-593](https://github.com/ZeripeDaniel/Lake-Dayz-MCP/blob/ac56f369c3b1d91ec602d63e2b2a003ffa1212bb/server.py#L554-L593).
- `[EXACT]` El grep “live” del modset lee texto sin retirar comentarios:
  [server.py:186-214](https://github.com/ZeripeDaniel/Lake-Dayz-MCP/blob/ac56f369c3b1d91ec602d63e2b2a003ffa1212bb/server.py#L186-L214).
- `[EXACT]` `dayz-api-index` v1 ya supera sus contratos de procedencia y
  confinamiento: build/schema/revisión/tree digest en
  `packctl/api_index.py:287-355`, roots contenidos en
  `packctl/api_index.py:150-212` y rechazo de escapes/build mismatch en
  `tests/packctl/test_api_index.py:83-126`.
- `[EXACT]` v1 elimina comentarios y por diseño trata “comentado” y “ausente”
  como cero records:
  `packctl/api_index.py:32-76,87-147` y
  `tests/packctl/test_api_index.py:38-59`.

**Adjudicación:** no rehacer v1 ni importar la DB. El delta útil es un v2
acotado: estado `active|commented|missing`, parent chain, guards de
preprocesador, mapa config y usos opcionales con caveats.

### StarDZ

- `[EXACT]` Fase 01 ya convirtió seis errores en fixtures negativas:
  `product-spec.md:53-57` y `evals/cases/stardz-negatives.json`.
- `[EXACT]` La skill externa aún afirma contratos refutados sobre `autoptr`,
  overload, `Managed` y `JsonLoadFile`:
  [SKILL.md:83-151](https://github.com/StarDZ-Team/Dayz-Modding-Skills/blob/dbdcd23b02eae0cb612110644f61fdd0d08a0d4b/skills/dayz-modding/SKILL.md#L83-L151).
- `[EXACT]` Su tabla UI conserva una firma incompleta de `OnDrop` y no fija
  commits ni `path:line` de COT/VPP/Expansion:
  [gui-patterns.md:648-693](https://github.com/StarDZ-Team/Dayz-Modding-Skills/blob/dbdcd23b02eae0cb612110644f61fdd0d08a0d4b/skills/dayz-modding/references/gui-patterns.md#L648-L693).
- `[EXACT]` Sus cinco evals son prompts y assertions narrativas sin runner,
  baseline, resultados, grading ni CI:
  [evals.json:1-59](https://github.com/StarDZ-Team/Dayz-Modding-Skills/blob/dbdcd23b02eae0cb612110644f61fdd0d08a0d4b/skills/dayz-modding/evals/evals.json#L1-L59).
- `[EXACT]` El valor residual ya está en planes vigentes: pooling medido
  (`plans/2026-07-24-02-dayz-ui-lab.md:78-85`), disease/plugins y budgets
  (`plans/2026-07-24-04-py3d-and-domain-skills.md:76-83`).

**Adjudicación:** no queda una incorporación inmediata. Sus temas no auditados
siguen siendo un índice de preguntas, no conocimiento durable. Para UI mandan
los repos directos VPP/Expansion/TraderPlus/TraderX y DayZDiag.

## Deltas de plan propuestos

### P0 — no bloquear Fase 02

- `[DESIGN]` Ejecutar `dayz-ui-lab` con el plan actual.
- `[DESIGN]` Usar grep vanilla y el índice v1 para APIs UI durante research.
  Si aparece una declaración comentada o bajo `#ifdef`, adjudicarla contra el
  archivo fuente; no convertir el índice v2 en dependencia de C1.
- `[DESIGN]` Mantener VPP, Expansion, TraderPlus y TraderX como corpus positivo
  directo; StarDZ no se añade como quinto referente.

### P1 — `dayz-api-index` v2 en Fase 04

- `[DESIGN]` Añadir un workstream pequeño, antes de crear nuevas skills:
  liveness trivaluada, parent chain, method guards, config namespace y uso
  heurístico opt-in.
- `[DESIGN]` Conservar JSON tipado, allowed-roots, metadata de build/schema,
  tree digest y regeneración local. No usar SQLite ni redistribuir datos DayZ
  salvo que un benchmark demuestre que hace falta.
- `[DESIGN]` Fixtures mínimas: activa, comentada, ausente, misma clase
  activa+comentada, parent cycle, método solo consola, override PC válido,
  `CfgXxx` correcto/incorrecto y uso dentro de comentario.

### P1 — build/release y preflight en Fase 04/06

- `[DESIGN]` Añadir al dry-run de `dayz-workshop-release`:
  postcondition de PBO nuevo, header/prefix, firma correspondiente y log sin
  error fatal; exit code por sí solo nunca basta.
- `[DESIGN]` La cache debe invalidarse por contenido, opciones, prefix, build
  DayZ, versiones/hashes de todas las herramientas efectivas y clave de firma.
- `[DESIGN]` Publicar desde staging con rollback; una build fallida deja el
  artefacto anterior intacto y no actualiza cache/manifest.
- `[DESIGN]` Extender preflight con path case/conflicts, referencias excluidas,
  paths absolutos empaquetados, PAA stale/missing y ODOL antes de binarize.
- `[DESIGN]` Mantener la matriz CE 1.28/1.29, incluyendo random presets y nodos
  anidados, antes de aceptar editores/simuladores.

### P2 — companion dayz-labs en Fase 05/06

- `[DESIGN]` Documentarlo como companion opcional por versión exacta.
- `[DESIGN]` Cuando `DayZ_MCP` gobierna la sesión, las operaciones
  start/stop/restart del MCP dayz-labs quedan fuera de la ruta recomendada.
- `[DESIGN]` No instalarlo por defecto, no ejecutar su installer dentro de los
  gates del pack y no usar sus tests WPF como evidencia para `.layout`.

## Viability gates

1. Índice v2 distingue de forma estructurada activa/comentada/ausente y falla
   cerrado ante build/schema/path incompatibles.
2. El test de PBO viejo bloqueado demuestra que un exit engañoso no puede
   producir PASS ni refrescar cache.
3. Cambiar una herramienta, key, prefix u opción invalida la cache; tocar solo
   mtimes sin cambiar bytes no la invalida.
4. Un fallo en publicación restaura el artefacto anterior byte a byte.
5. La matriz CE conserva o rechaza explícitamente todos los campos vigentes;
   nunca los descarta silenciosamente.
6. Ningún companion puede convertirse accidentalmente en segunda autoridad de
   lifecycle.

## Decisión solicitada

Mi recomendación es aprobar estos tres deltas y nada más:

1. `dayz-api-index` v2 como workstream de Fase 04, sin bloquear UI.
2. Postconditions/cache/publicación transaccional dentro de
   `dayz-workshop-release` y el preflight CI.
3. dayz-labs solo como companion documentado sin lifecycle authority.

StarDZ queda cerrado como fuente ya explotada; Lake y dayz-labs siguen siendo
prior art sin dependencia ni payload.

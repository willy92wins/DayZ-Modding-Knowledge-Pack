# HANDOFF — DayZ Modding Knowledge Pack

<!-- LIVE-STATE:START -->
# DayZ Modding Knowledge Pack — Estado vivo · snapshot 2026-07-28 (Fase 03 cerrada)

**Última verificación real:** HEAD `1312890` en `r21/phase01-foundation`, árbol
limpio, **`main` fast-forwardeado a `1312890`** y 0 commits por detrás. Sin remoto.
Suite **748 passed / 18 skipped**, `packctl validate` PASS con cero findings,
`packctl promote --check` **`WARN` con exit 0** y finding único
`PROMOTION-DRIFT operation_count=39` — todas de `obsidian_snapshots` con
`before_digest: absent`, que es estructural (los snapshots se guardan por commit).

`ciclos_en_este_objetivo: 1 (Fase 02 — B20, gate C1 y corpora)`

> Contador reiniciado a 1 **porque cambia el objetivo**: el anterior era «cerrar
> Fase 03 y el tramo ejecutable de Fase 02», y la Fase 03 está cerrada. Lo que
> queda de Fase 02 es un cuerpo de trabajo distinto. Si prefieres tratarlo como el
> mismo objetivo a medias, súbelo a 2.

## Fase 03 `dayz-persistence` — CERRADA, D1–D5 en `✓`

Nueve commits de contenido, cada criterio con su línea de evidencia **ejecutada**.
Detalle en `product-spec.md` §D y en el handoff
`30_Sessions/2026-07-28-DayZ-Modding-Knowledge-Pack-fase03-dayz-persistence-cerrada.md`.

La skill `dayz-persistence` está **promovida y viva** en las dos raíces
(transacción `6e8cf995be627d7bf50cd147`, readback independiente: 0 perdidos,
0 cambiados, 5 añadidos por raíz).

## Qué hacer a continuación

**Fase 02, `plans/2026-07-24-02-dayz-ui-lab.md`.** Sigue siendo lo que dice el plan
maestro (`plans/2026-07-28-r21-completion-and-criteria-triage.md` §N2), sin
cambios:

1. **B20** — micro-fixture de continuación CRLF/LF observada con
   `ButtonWidget.GetText` en DayZDiag (`:76`, `:87-90`). Requiere `dayz-mcp`:
   lease antes de mutar, liberarlo al terminar, nunca matar procesos DayZ a mano,
   `session_status` antes del handoff.
2. **Gate C1** (`:95`): LFPG + 319/319 público + 46/46 TraderX, exit 0.
3. **Corpora** (`:77`): fijar builds, hashes y licencias.
4. Tasks 3-5 del plan de fase, todas offline.

## Lo que te va a morder si no lo lees

1. **Hay un directorio que rompe `pytest` y no se puede borrar.**
   `UsersguillAppDataLocalTempr21-sc015-basetemp`, en la raíz del repo. Una ruta
   Windows sin separadores que dejó una tanda de Codex como `--basetemp`. La
   colección muere con `PermissionError`. `Remove-Item`, `takeown`, `icacls` y
   `robocopy /MIR` fallan todos; `icacls` ni puede leer el DACL. **Los gates de
   esta sesión se corrieron con
   `--ignore=UsersguillAppDataLocalTempr21-sc015-basetemp` en línea de comandos**,
   deliberadamente NO en `pytest.ini`. Se arregla con consola elevada:
   `rmdir /S /Q "UsersguillAppDataLocalTempr21-sc015-basetemp"`.
2. **El destino sigue mutando solo.** Van ocho escrituras host-direct en
   `dayz-vehicles`. **Re-mide `promote --check` antes de tocar nada.** Si sale
   `PROMOTION-TARGET-UNEXPLAINED`: adoptar → refrescar `output_hash` → `git add` →
   `validate` → suite → commit → re-medir → adjudicar **solo con quietud
   verificada** (script en
   `scratchpad/adjudicate_vehicles.py`: exige 60 min de quietud e igualdad byte a
   byte asertadas al firmar).
3. **`B3b` está fuera de alcance por decisión del usuario.** Sin API de pago no es
   alcanzable: `--bare` (`evals/live/runners/claude-code.py:28-43`) es lo único que
   esconde las skills globales del brazo de control, y es lo que se niega a leer la
   sesión OAuth. No lo reintentes.
4. **El harness de evals vivos tiene un fail-open, registrado y sin arreglar.**
   `_skills_tree_sha256` (`live_evals.py:201-211`) hashea `workspace/.claude/skills`
   (`:221`, `:233`), así que `LIVE-EVAL-ARM-CONTAMINATED` (`:446`, `:464`) prueba
   que ese árbol está vacío y **nada más**. Quita `--bare` del runner y el brazo de
   control se contamina sin que ningún gate se ponga rojo. Spike de aislamiento
   pendiente, **estrictamente después** de lo que haya en curso.

## Estado de publicación

**24 de 54 criterios en `✓`** (eran 19). Cerrado: A1–A9, B1/B2/B3a/B4/B5, **D1–D5**
y F1–F5. Abierto: 30 — `B3b`, 8 de Fase 02, 9 de Fase 04 (tramo `E`+`B7`/`B8`),
5 de Fase 05 y 7 de Fase 06. La Fase 06 produce el release y depende de 01–05, así
que no hay publicación posible antes.

## Invariantes cerradas

- Git es la única fuente editable; las instaladas son despliegues. La adopción va
  del destino al repo, nunca al revés sin gate.
- **Adoptar protege el conocimiento y es barato; adjudicar caduca.** Reforzado con
  evidencia nueva: la adopción sin firma de `ce67494` evitó firmar una instrucción
  **técnicamente falsa** que el upstream corrigió ocho horas después.
- Un `mtime` que se mueve **no** prueba trabajo en curso; `git status --porcelain`
  sí. Un fichero commiteado conserva su mtime para siempre.
- Una adjudicación autoriza un digest concreto y **tapa, no arregla**.
- Un gate que no puede ponerse rojo no es un gate — y un gate que rechaza tu
  cambio puede tener razón: relájalo solo dejando constancia de qué se pierde.
- No declarar un criterio `✓` sin ejecutar su línea de evidencia.
- `validate` sobre ficheros sin rastrear no dice nada: `git add` y DESPUÉS validar.

**Gate de arranque:** declarar `Retomo DayZ Modding Knowledge Pack desde: 1312890
con la Fase 03 cerrada y main al día · re-medir promote --check antes de tocar
nada, y borrar el directorio basura con consola elevada antes de correr pytest`.
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

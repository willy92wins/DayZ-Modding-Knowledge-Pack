# HANDOFF — DayZ Modding Knowledge Pack

<!-- LIVE-STATE:START -->
# DayZ Modding Knowledge Pack — Estado vivo · snapshot 2026-07-28 (pre-sesión nocturna)

**Última verificación real:** HEAD `44a169b` en `r21/phase01-foundation`, árbol
limpio, `main` intacto en `994cb77` y 66 commits por detrás. Suite **699 passed /
18 skipped**, `packctl validate` PASS con cero findings, `packctl promote --check`
**`WARN` con exit 0** y finding único `PROMOTION-DRIFT operation_count=38` — todas
de `obsidian_snapshots` con `before_digest: absent`, que es estructural; las 16
operaciones de skill con drift cero.

`ciclos_en_este_objetivo: 1 (completar Fase 03 y el tramo ejecutable de Fase 02)`

## Qué se hace esta noche

**Plan maestro: `plans/2026-07-28-r21-completion-and-criteria-triage.md`** (commit
`44a169b`). Ahí está el triaje de los 35 criterios abiertos con dueño y evidencia,
y la secuencia. No re-planificar: ejecutar.

1. **Bloque N1 — Fase 03 `dayz-persistence` entera.** Offline puro, sin engine,
   sin MCP y sin login. Ejecutar `plans/2026-07-24-03-dayz-persistence.md` en
   orden. Es data-crítica por declaración propia (`:3-4`) → feature spec +
   checklist 16/16 ANTES de escribir la skill (`:45`), y `rigorous-data-audit`
   (`DZ-R9`) antes de declarar nada release-safe.
2. **Bloque N2 — Fase 02, solo si N1 cierra o para limpio.** Empezar por **B20**,
   que ya no está bloqueado.

## Decisiones del usuario, 2026-07-28 madrugada (no re-preguntar)

- **Orden**: Fase 03 entera primero, luego lo offline de la Fase 02.
- **Autonomía ampliada**: commits en la rama, **`promote --apply` autorizado** con
  el gate verde, y **fast-forward de `main` autorizado** al cerrar una fase en
  verde. Sigue sin haber remoto y sin `push`.
- **Sin recorte de alcance**: los 22 criterios fuera de las fases 02–03 entran en
  el plan. No se propone ninguna exclusión fechada; publicar exige las seis fases.
- **Desbloqueos**: los tres, hechos con el usuario delante.

## Entorno medido a las ~04:20, no supuesto

| Desbloqueo | Estado |
|---|---|
| **DayZ MCP** | **resuelto**. Ambos peers `version=6~1.29.163451`, `version_state=ok`, *version accepted*, poll 66-67 s. Lease libre: `owner=null`, `claimable=true`, sin `audit_fault` |
| **DayZDiag** | **arriba**, dos instancias desde 04:15:34 y 04:15:48 |
| **Auth del CLI `claude`** | **B3b sigue bloqueado, y NO por falta de `/login`** (ver abajo) |

**Corrección medida a las 04:45 — el bloqueo de B3b no es el `/login`.** El runner
invoca el CLI con `--bare` (`evals/live/runners/claude-code.py:29-43`), y la ayuda
del propio CLI dice de esa bandera: *«Anthropic auth is strictly
`ANTHROPIC_API_KEY` or apiKeyHelper via `--settings` (OAuth and keychain are never
read)»*. Medido: no existe `ANTHROPIC_API_KEY` ni en sesión, ni en `User`, ni en
`Machine`. Así que una sesión OAuth no desbloquea el eval; hace falta la variable
de entorno, que el adaptador hereda porque hace `subprocess.run` sin `env=`.

**Y quitar `--bare` no es el arreglo**: es lo que impide que el CLI auto-descubra
`CLAUDE.md` y las skills globales del usuario, o sea lo que mantiene honesto el
brazo `without_skill` —hay un test dedicado,
`test_without_skill_tree_contamination_rejects_case`. La bandera es load-bearing.

**Decisión del usuario (D5): no se usa API de pago.** El pack debe correr desde
Cowork con la auth que ya existe. Eso descarta la clave y el `apiKeyHelper`.

Es una pinza, no un descuido: el brazo `without_skill` solo es honesto si el
runner no ve las skills globales, y `blender-animation` está en `~\.claude\skills`;
lo único que hoy la esconde es `--bare`, que es justo lo que rechaza la auth de
Cowork. **B3b se queda en `❓` por diseño; no gastes tiempo de sesión en él.**
Las tres vías abiertas están en el §4.1.1 del plan, y la tercera —exclusión de
alcance fechada— exige decisión del usuario: no la tomes por tu cuenta.

**B20 ha dejado de estar bloqueado**, y eso reordena la Fase 02: el hard stop
«B20 abierto» (`plans/2026-07-24-02-dayz-ui-lab.md:173`) y los items que dependían
de él (`:76`, `:87-90` — semántica CRLF/LF de continuación observada con
`ButtonWidget.GetText` en DayZDiag) son ejecutables. Matiz: el puente vivo prueba
autorización de protocolo, **no** que la fixture de B20 pase. Hay que ejecutarla.

Protocolo `dayz-mcp`: adquirir lease antes de mutar, liberarlo al terminar, nunca
matar procesos DayZ a mano, `session_status` antes del handoff.

## Hallazgo que corrige el brief

**La Fase 04 NO está cerrada.** `project-brief.md:5` dice «Fase 04 cerrada con
F1–F5 en verde», pero la fila del roadmap le asigna **`E`, `F` y `B7–B8`**
(`plans/2026-07-24-r21-master-roadmap.md:41`). F1–F5 sí están; `E1–E7`, `B7` y
`B8` no. Corregir esa frase forma parte del cierre, y hay un hard stop que
prohíbe repetir la afirmación.

## Estado de publicación

**19 de 54 criterios en `✓`.** Cerrado: A1–A9 (fundamento, procedencia, build
reproducible, licencias, promoción), B1/B2/B3a/B4/B5 y F1–F5. Abierto: 35, con
dueño asignado en el plan. La Fase 06 se llama «Ecosistema + release» y depende de
01–05 (`roadmap:43`), así que no hay publicación posible antes.

## Deuda anotada, sin sesión asignada

- **Diagnosticabilidad del runner de evals**: el adaptador colapsa todo fallo en
  `exit=2` escribiendo solo `type(error).__name__`
  (`evals/live/runners/claude-code.py:110-112`). ~5 líneas propagar el `result`.
- **`reports/`**: 0,85 MB, pero quedan 48 directorios vacíos que rechazan el
  borrado por debajo del modelo de ACL (`takeown`, `icacls` y `Set-Acl` fallan los
  tres). Necesitan consola elevada.

## Invariantes cerradas

- Git es la única fuente editable; las instaladas son despliegues. La adopción va
  del destino al repo, nunca al revés sin gate.
- **Adoptar protege el conocimiento y es barato; adjudicar caduca.** Adopción sola
  es un punto de parada legítimo, con el gate rojo a propósito. Antes de firmar,
  exigir quietud verificada del destino e igualdad byte a byte con el repo
  (`LL-216`, refuerzo 2026-07-28).
- Una adjudicación autoriza un digest concreto y **tapa, no arregla**.
- Preimagen e historial causal son dos gates distintos.
- El sello del wheel es toolchain-bound y describe un commit fuente: endurecer la
  fuente pone el gate rojo con razón.
- Un gate que no puede ponerse rojo no es un gate.
- No declarar un criterio `✓` sin ejecutar su línea de evidencia.

**Gate de arranque:** declarar `Retomo DayZ Modding Knowledge Pack desde: 44a169b
con el plan de cierre commiteado · ejecutar Fase 03 entera antes de tocar Fase 02,
y re-medir promote --check antes de nada porque el destino muta solo`.
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

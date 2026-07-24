# Fase 04 — py3d y skills de dominio prioritarias

> Este es un plan de research y descomposición. Cada bloque que supere su
> viability gate obtiene una feature spec y un plan de implementación propio;
> no se implementan todos en un único diff.

## Objetivo y traza DPF

Cerrar E1–E7, F1–F5 y B7–B8 sin monolitos ni APIs inventadas.

## Orden interno

1. `dayz-api-index` v2, acotado y sin bloquear Fase 02.
2. py3d/export validation.
3. `dayz-multiplayer-sync`.
4. `dayz-sound-particles`.
5. `dayz-terrain`.
6. `dayz-workshop-release`.
7. disease/modifiers, plugin lifecycle, RPT y performance budgets.
8. simuladores offline.

## Evidencia de partida

- `ScriptRPC.Send(Object,int,bool,PlayerIdentity)`:
  `VANILLA/3_game/gameplay.c:104-117`.
- Entry points del lector ODOL:
  `SKILL_SOURCE/dayz-p3d-debinarizer/scripts/odol_reader.py:731`.
- El converter actual invierte el orden de índices al emitir MLOD:
  `SKILL_SOURCE/dayz-p3d-debinarizer/scripts/odol_to_mlod.py:120`.

## Workstream 0 — `dayz-api-index` v2

- [ ] Extender el índice v1 sin romper su JSON tipado, allowed-roots, metadata
  de build/schema, tree digest ni regeneración local.
- [ ] Emitir liveness estructurada `active|commented|missing`, parent chain,
  guardas de método/clase, namespace de config y uso heurístico solo opt-in.
- [ ] Fixtures mínimas: declaración activa, comentada, ausente,
  activa+comentada, parent cycle, método solo consola/guardado, override PC
  válido, `CfgXxx` correcto/incorrecto y uso dentro de comentario.
- [ ] Falla cerrada ante path escape, build/schema/tree incompatibles y ciclos.
- [ ] No introducir SQLite ni redistribuir una base DayZ salvo benchmark que
  demuestre necesidad; el índice sigue siendo evidencia auxiliar y nunca
  sustituye abrir la fuente citada.
- [ ] Gate: consulta devuelve estado, `path:line`, parent/guarda/namespace
  esperados para cada fixture y mantiene verdes los contratos v1.
- [ ] B8 no es dependencia de C1: `dayz-ui-lab` continúa con grep/fuente
  directa cuando v1 devuelve cero o una declaración ambigua.

## Workstream A — py3d

- [ ] Reconciliar los dos rollout scripts distintos y las tres fixtures
  source-only antes de nuevas features.
- [ ] Research de transform de proxies con matrices/rotación y referentes.
- [ ] Research de RTM/SEAnim: adjudicar si vive en py3d o en herramienta
  hermana según formatos/responsabilidad.
- [ ] Definir validaciones de winding, huesos y escala con fixtures.
- [ ] Mantener ODOL como read-only; comparar reutilizar el debinarizer contra
  integrarlo en py3d y escoger la vía más simple que cumpla F4.
- [ ] Plan hijo solo tras fijar interfaces y oráculos.

## Workstream B — multiplayer sync

- [ ] Grep vanilla de ScriptRPC, reliability, target/identity, SyncVars,
  ownership y callbacks.
- [ ] Corpus de desync real: LFHeli y otros casos ya verificados, depersonalizado.
- [ ] Amenazas: auth, replay/spam, invalid identity, oversized payload y wrong side.
- [ ] Ladder local con dos clientes antes de afirmar soporte multiplayer.
- [ ] Feature spec propia y evals positivas/negativas.

## Workstream C — sound + particles

- [ ] Separar `.ptc`/Effect de SoundShader/SoundSet.
- [ ] Verificar Workbench/config/runtime/occlusion por fuente.
- [ ] Proyecto fixture mínimo por subsistema.
- [ ] No copiar referencias StarDZ sin build/commit.
- [ ] Plan hijo después de build/smoke de los fixtures.

## Workstream D — terrain

- [ ] Fijar mapa mínimo, toolchain, roadgraph y CE para la stable actual.
- [ ] Auditar compatibilidad de los parsers CE con 1.28/1.29, incluidos random
  presets y nodos anidados; conservarlos o rechazarlos explícitamente, nunca
  descartarlos en silencio.
- [ ] Definir proyecto ejemplo y outputs verificables.
- [ ] Integrar el runbook roadgraph existente, sin duplicarlo.
- [ ] Plan hijo después de validar un round-trip mínimo.

## Workstream E — workshop release

- [ ] Extraer requisitos de dayz-labs y fuentes oficiales, no código GPL.
- [ ] Cubrir `mod.cpp`, requires/dependencies, PBO, signing/bisign, previews,
  changelog y update/rollback.
- [ ] Dry-run local sin publicar: `exit 0` o PBO preexistente nunca bastan.
- [ ] Postconditions: candidato creado por este run, digest/frescura coherente
  con inputs, header/prefix/entries esperados, `.bisign` cuando corresponda y
  log sin errores fatales.
- [ ] Cache key completa: bytes de inputs, opciones, prefix, build DayZ,
  versiones/hashes de todas las herramientas efectivas e identidad de clave
  de firma; un cambio en cualquiera invalida, tocar solo mtime no.
- [ ] Preflight fail-closed: conflictos de case/path,
  excluidos-pero-referenciados, paths absolutos empaquetados, `.paa`
  stale/missing y ODOL no soportado antes de binarize.
- [ ] Publicar desde staging solo tras validar. Ante cualquier fallo, el
  artefacto anterior queda byte-idéntico y cache/manifest no avanzan.
- [ ] Definir estrategia de secrets fuera del repo.
- [ ] Fixtures de viabilidad: PBO bloqueado/copy fallida, header/prefix
  incorrecto, firma ausente, fatal log, invalidación por cada componente de
  cache y fallo inyectado en publicación/rollback.
- [ ] Plan hijo después de fijar tool versions, artifacts y semántica exacta
  de commit/rollback.

## Workstream F — conocimiento y budgets

- [ ] Research vanilla-first de disease/modifiers y plugin lifecycle.
- [ ] Consolidar common RPT decision tree y arquitecturas mod.
- [ ] Medir batching/debounce/cache/ticks/CE queries en build/hardware/corpus
  declarados.
- [ ] Convertir números StarDZ en hipótesis, nunca en defaults.
- [ ] Promover solo patrones con dos referentes o soporte vanilla/engine.

## Workstream G — simuladores offline

- [ ] Priorizar parser de config y validadores de loot/CE; el preview físico
  entra solo si existe un oráculo que no finja equivalencia con el engine.
- [ ] Definir fixtures first-party positivas, negativas y de límites.
- [ ] Declarar por herramienta qué valida y qué requiere DayZDiag/Workbench.
- [ ] Plan hijo tras demostrar que el simulador evita una clase concreta de
  iteración sin introducir doctrina falsa.

## Gate de cierre de la fase

- Cada workstream tiene research con fuentes primarias, unknowns y referente.
- Cada feature aceptada tiene feature spec/checklist y plan hijo.
- `dayz-api-index` v2 supera su matriz completa y no se convierte en
  dependencia de UI.
- El release dry-run no puede producir PASS ni refrescar cache/manifest con un
  PBO viejo, inválido o no publicable; rollback conserva el anterior por hash.
- Cada invariante aceptada actualiza su nota Obsidian y la skill canónica;
  después se promueve a targets activos con recibo.
- No hay implementación huérfana de criterio DPF.
- py3d baseline no retrocede.
- Validator/evals/source-map verdes; `PROMOTION-UNROUTED=0` y
  `PROMOTION-DRIFT=0`.

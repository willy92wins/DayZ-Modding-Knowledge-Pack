# Fase 04 — py3d y skills de dominio prioritarias

> Este es un plan de research y descomposición. Cada bloque que supere su
> viability gate obtiene una feature spec y un plan de implementación propio;
> no se implementan todos en un único diff.

## Objetivo y traza DPF

Cerrar E1–E7, F1–F5 y B7 sin monolitos ni APIs inventadas.

## Orden interno

1. py3d/export validation.
2. `dayz-multiplayer-sync`.
3. `dayz-sound-particles`.
4. `dayz-terrain`.
5. `dayz-workshop-release`.
6. disease/modifiers, plugin lifecycle, RPT y performance budgets.
7. simuladores offline.

## Evidencia de partida

- `ScriptRPC.Send(Object,int,bool,PlayerIdentity)`:
  `VANILLA/3_game/gameplay.c:104-117`.
- Entry points del lector ODOL:
  `SKILL_SOURCE/dayz-p3d-debinarizer/scripts/odol_reader.py:731`.
- El converter actual invierte el orden de índices al emitir MLOD:
  `SKILL_SOURCE/dayz-p3d-debinarizer/scripts/odol_to_mlod.py:120`.

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
- [ ] Auditar compatibilidad de los parsers CE con 1.28/1.29.
- [ ] Definir proyecto ejemplo y outputs verificables.
- [ ] Integrar el runbook roadgraph existente, sin duplicarlo.
- [ ] Plan hijo después de validar un round-trip mínimo.

## Workstream E — workshop release

- [ ] Extraer requisitos de dayz-labs y fuentes oficiales, no código GPL.
- [ ] Cubrir `mod.cpp`, requires/dependencies, PBO, signing/bisign, previews,
  changelog y update/rollback.
- [ ] Dry-run local sin publicar.
- [ ] Definir estrategia de secrets fuera del repo.
- [ ] Plan hijo después de fijar tool versions y artifacts.

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
- No hay implementación huérfana de criterio DPF.
- py3d baseline no retrocede.
- Validator/evals/source-map verdes.

# Gates de proceso: fixtures negativas y reglas promovidas

Extraido de `SKILL.md` (corte 3, 2026-08-15). Aqui vive el DETALLE; el enunciado
corto y cuando leer esto estan en el indice `## ARCHIVO DE LECCIONES` del SKILL.md.
Nada de este fichero esta derogado: son lecciones vigentes, ordenadas por tema en
vez de por fecha.

---

## An import gate rule is not deliverable without a negative fixture (SP-096, added 2026-07-27)

SP-091 established the method rule: calibrate every gate rule against a model that WORKS. That is
necessary and NOT sufficient. The LFHeli OH-1 gates were calibrated against a good reference and
still shipped a gate that passed the broken model, failed the good one, and accepted absurd input.
An adversarial review with in-memory mutation took them apart in one pass:

- 12 proxies displaced by 100/200/300 m -> **PASS**. The distance rule existed and fired, but it
  emitted INFO, and the verdict counted only FAIL.
- 30.419 faces repointed to a texture that does not exist -> **PASS**, with zero findings naming it.
  The rule walked the inventory looking for unreferenced files, never the reverse direction.
- The "corrected" reference fixture itself carried `dot(geometric, stored) = -1.0` on 24 of its 48
  proxy vertices - the exact defect SP-093 is about - and the suite asserted it must PASS.
- The suite advertised as "11 tests green" was 7 tests with 4 red, and could not even start from the
  official layout because it pointed at a directory that did not exist there.

RULES for any model-import gate:

1. **Every rule ships with TWO fixtures, both executed by the suite**: a positive (the good
   reference AND the current clean model both pass) and a **negative mutant** built in memory from a
   good model with the exact defect the rule claims to detect, which the rule MUST fail. A rule
   without a mutant that makes it fail is not deliverable - that is the hole every false PASS above
   came through.
2. **No INFO, no WARN inside the verdict.** If it should block, it is a FAIL; if it should not, it
   is a diagnostic print and stays out of the verdict and the exit code. A severity that cannot
   change the outcome is a rule that does not exist.
3. **Regenerate the reference fixture and verify it against the rules it is supposed to certify.**
   A fixture is an artifact like any other; it rots, and a corrupt one converts the whole suite into
   theatre.
4. **Prefer few solid rules to many plausible ones.** The rebuild kept three - proxy-normal
   coherence, referenced-texture existence, finite UVs - each with its mutant, and that suite is
   worth more than the twelve rules it replaced.
5. **A rule whose threshold is a bare literal is a smell.** Derive it from measurement on the good
   case and leave the number and its derivation in the code.
6. **When a gate change makes a previously green tree go red, fix the RULE or accept the finding -
   never re-baseline the expected value to make it pass.** Deciding between the two is the user's
   call, not implementation.

Origin: LFHeli OH-1 2026-07-27, R21 dual (Codex + Claude subagent). The rebuilt gate lives at
`LFHeli_dev\tools\import_gates_v2\`; the retired one at `tools\import_gates_RETIRED_20260726\` as a
negative reference.

## Reglas promovidas del corpus de lecciones (added 2026-07-27)

Promovidas desde `AI/20_Knowledge/lessons-learned.md` para que lleguen por trigger en vez
de depender de que alguien recuerde buscarlas. Cada regla cita su `LL-NNN` de origen;
la entrada completa (síntoma, origen, evidencia) vive allí. No quites la cita: el índice
`lessons-index.md` detecta la promoción buscando esa referencia dentro de las skills.

- **LL-076** — Antes de diferir una feature, clasifica la severidad de su ausencia y valida los mínimos exigidos por el engine. Todo `CarScript` debe incluir al menos `DamageSystem.GlobalHealth`; su ausencia puede matar el proceso aunque el daño sea una feature posterior.
- **LL-172** — Ante paneles negros o see-through, decodifica primero el `_co` desplegado y mide píxeles oscuros. Si la textura está limpia, trata el síntoma como winding y exige captura in-game antes de voltear regiones.

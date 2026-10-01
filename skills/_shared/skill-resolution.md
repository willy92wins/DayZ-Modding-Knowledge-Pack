# Skill resolution policy (added 2026-05-12)

Operational policy when duplication already exists between user custom skills and plugin-installed skills (not the "pre-install" case — for that see "PLUGIN INSTALL CONFLICT CHECK" in `skill-conventions/SKILL.md`).

Typical case: `agentic-z@dayz-n-chill` plugin introduces `dayz-p3d-audit`, `dayz-p3d-debin`, `dayz-particles` when local versions already exist in `C:\Users\<you>\.claude\skills\`. Both remain resolvable via namespace (`agentic-z:dayz-p3d-audit` vs `dayz-p3d-audit`).

## Default operativo

Without explicit project policy: local custom skills (`C:\Users\<you>\.claude\skills\<name>`) win over plugin (`agentic-z:<name>`) because they typically carry user-specific patches.

## Per-skill policy (to decide upon detecting conflict)

1. **Local custom derives from plugin and patch is already upstreamed** → delete local custom, use plugin copy. Verify by inspecting diff before deleting (`diff plugin/skill.md user-local/skill.md`).
2. **Local custom diverges substantially** (own `P:\` paths, magic numbers tuned to setup, specific LFPG/LFV/SimpleGroup sections) → keep custom, disable plugin copy with `/plugin manage <plugin>` unchecking that specific skill.
3. **You are unsure** → keep both, declare conflict in `CLAUDE.md` of active project:

```markdown
## Skill resolution overrides
- Para dominio `dayz-p3d-audit`: usar `<namespace>:dayz-p3d-audit` porque <razón>. Última verificación YYYY-MM-DD.
```

## Document the decision where visible

Once decided, write override in:

- `00_System/codex-briefing.md` of vault (global pipeline rule).
- `workflow.md` of vault if affecting multiple projects.
- repo `CLAUDE.md` if project-specific.

This way Codex and Claude know which one to call and why, without having to re-evaluate conflict each session.

## Before installing a new plugin

List local skills (`ls ~/.claude/skills/`) and compare with plugin manifest. Decide per-skill policy BEFORE installing, not after noticing conflict. This is already covered in `skill-conventions/SKILL.md` section "PLUGIN INSTALL CONFLICT CHECK".

## Anti-pattern

Installing plugin without auditing conflicts, discovering duplication three sessions later, and leaving decision in limbo. Result: both versions coexist indefinitely, agents invoke the "wrong" one per internal search order, and user does not understand why skill behaves differently.

## Measured on 2026-08-24: "Operational default" is confirmed, and is missing two things (added 2026-08-24)

Default above —"local custom skills win over plugin"— **was measured and is true**,
but until that date it was written policy without measurement, and its example was `agentic-z:`, not the
plugin today serving most of the catalog. Measurement: SAME duplicated skill was invoked by
its two names and returned base directory was read.

| Invocation | Loads from |
|---|---|
| `mixamo-retarget` (bare) | `C:\Users\<you>\.claude\skills\mixamo-retarget` |
| `anthropic-skills:mixamo-retarget` (prefixed) | `%APPDATA%\Claude\local-agent-mode-sessions\skills-plugin\<uuid>\<uuid>\skills\mixamo-retarget` |

**The two missing nuances, and they are the ones causing damage:**

1. **"Wins" applies only to bare name.** Both copies remain **servable**: the
   prefixed name loads the plugin copy, and both names are in the catalog of each
   session. So fixing the local copy does NOT retire the other — an agent writing
   `anthropic-skills:<x>` gets the old version with no indication that it is. In the
   measurement, the served copy was **19 days behind** and lacked a doctrine fix that
   was in the local copy.
2. **There is a third tree, and it is neither of the two editable ones.** What namespace serves is not
   the folder from which it was packaged: it is a copy **materialized by the app** under
   `%APPDATA%\Claude\local-agent-mode-sessions\skills-plugin\`, with manifest and a
   reconciler deleting unregistered items within minutes (see memo
   `claude-skills-plugin-tree-managed`). There can be **more than one installation** there at once,
   with differing contents. Editing by hand does not survive; official registration is `.skill` +
   "Save skill" button.

**Consequence for item 1 of §Per-skill policy** ("delete local custom, use plugin
copy"): before deleting anything, check **which of the plugin trees is actually served**
and with what content. The `diff` against package source folder can come up clean
while what is served is something else.

**Cheap check, one minute**: invoke skill by its two names, compare base
directory and a witness line from the body. If they differ, you have servable duplication, not
resolved duplication.

Detail, map of five roots, and four measured simultaneous versions: [[LL-356]].

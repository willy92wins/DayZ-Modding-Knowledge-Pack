---
name: dayz
description: Use for ANY DayZ, Enfusion or Enforce Script modding work, even when the user does not say "skill". Mods, config.cpp, types.xml, model.cfg, .p3d/.paa/.rvmat models and textures, PBO build and signing, Steam Workshop, local DayZ server and in-game testing, vehicles, aircraft, weapons, clothing, base building, AI, UI layouts, animations, sound, particles, persistence, Blender and DayZ Tools pipelines, 1.30 porting. Routes to {{SKILL_COUNT}} specialised playbooks in the sibling folders; read the matching `<name>/SKILL.md` before acting. Start with `dayz-mod-dev` for mod work as a whole.
---

# DayZ Modding Knowledge Pack

This is the only entry point of the pack. It routes to {{SKILL_COUNT}} specialised playbooks
that sit in folders next to this file. They are not separately installed skills:
you reach them by reading their `SKILL.md`.

## How to use this router

1. **Pick the playbook(s).** Find the entry in the list below whose description
   matches the task (descriptions are trigger conditions: "invoke me when...").
   Read that `<name>/SKILL.md` **in full** before acting. The folder sits next
   to this file. Several playbooks may apply; read each.
2. **Mod work as a whole** (write, review or port a mod, build it, boot it,
   publish it): start with `dayz-mod-dev/SKILL.md`. It routes onward and carries
   the rules every mod task needs.
3. **Names.** Whenever a playbook says "invoke", "use", "compose with" or
   "delegate to" `dayz-x`, or writes `/dayz-x`, that means: read
   `dayz-x/SKILL.md` next to this file.
4. **Paths.** Repo-rooted paths in playbooks such as `skills/<x>/...` or
   `skills/_shared/...` mean `<x>/...` or `_shared/...` relative to this
   folder. Links like `../_shared/...` resolve as written. Open a playbook's
   `references/` files only when its procedure names them; they are large.
   Repo-only paths (`tools/`, `knowledge/`, `tests/`) are not installed here.

## The four rules

1. **Never invent an API.** Before writing any Enforce Script call, config
   class, `.p3d` selection or memory point, grep the vanilla source
   (`P:\scripts\` -> `1_core`, `3_game`, `4_world`) or a reference in the
   playbook, and cite `path:line`. Memory and semantic search are hints; open
   the file. DayZ fails silently on a wrong name.
2. **Respect the client/server split.** Decide which side owns each value before
   writing the feature. Most "it doesn't work" bugs are a read on the wrong side.
3. **In-game tests cost 3-10 minutes each.** Exhaust offline analysis, batch
   every pending change into one test, and have a plan B before asking for a
   rebuild. Two rebuilds with no progress mean the strategy is wrong.
4. **Be honest about verification.** Say what you checked, how (grep, checksum,
   repro, in-game) and what you did not. "It compiles" is not "it works".

## Playbooks

{{ROUTING_TABLE}}

# Copilot instructions

Canonical agent file: [`AGENTS.md`](../AGENTS.md). Summary below.

This repository is a **DayZ (Enfusion) modding knowledge pack**: 16 domain
playbooks in `skills/`, five Python tools in `tools/`, verified reference notes
in `knowledge/`.

## Routing

Do not load the pack wholesale — it is ~4 MB. Read every `skills/*/SKILL.md`
front-matter first (each `description` is a set of trigger conditions), load the
one whole `SKILL.md` that matches, and open files under its `references/` only
when the procedure names them.

## The four rules

1. **Never invent an API.** DayZ fails *silently* on confabulation. Grep the
   vanilla source (`P:\scripts\`) or a reference here and cite `path:line`
   before writing any Enforce Script call, config class or `.p3d` selection.
2. **Respect the client/server split.** Decide which side owns each value first.
3. **In-game tests cost 3–10 minutes.** Batch changes; have a plan B.
4. **Be honest about verification.** State what you checked, how, and what you
   did not. "It compiles" is not "it works".

## Editing this repository

Every executable claim needs a build/commit and a `path:line`. No private paths,
credentials, vanilla or third-party assets. The pack is MIT and takes no GPL,
DPL-ND or CC-NC material.

```bash
python -m packctl gate --root . --report-dir reports
```

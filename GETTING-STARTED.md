# Getting started

This pack is written for **coding agents**. They load one
`skills/<name>/SKILL.md` at a time from its `description:` and follow that
playbook. They are not meant to read the tree cover to cover.

This file is the exception. It is for the **human who just cloned** and needs
a map: what to install, which way the work flows, and which skill or tool to
open for a given job. It is an index, not a tutorial. If a paragraph starts
explaining how to write `config.cpp` or Enforce Script, it has gone too far —
that lives in `enforce-script-reference`.

Two jobs, two doors:

- **Make a DayZ mod** → §1 then §2. Hand the named skill to your agent.
- **Change this pack** → skip the mod cycle; go to [§4](#4-what-this-file-is-not).

---

## 1. Before you start

The pack does not vendor DayZ, DayZ Tools, Blender, or the game data.
[`README.md`](README.md) §4 is the install list. You need at least:

| Need | Why |
|---|---|
| **DayZ** plus **unpacked vanilla data** on `P:\` | Ground truth for scripts, models and configs. Agents grep `P:\scripts\` (`1_core`, `3_game`, `4_world`) instead of inventing APIs. |
| **DayZ Tools** | AddonBuilder packs PBOs. Object Builder / Workbench and TexView / ImageToPAA convert assets. |
| **`P:\` mounted** | Work-drive convention. It does not remount itself after a reboot — open DayZ Tools and mount it (Tools → Mount P drive). |
| **`P:\Mods`** as a junction to `<DayZ>\!Workshop` | Where a deployed PBO has to land for the engine to see it. |
| **`DayZDiag_x64.exe`** | Local filepatching launch. The retail exe is the wrong runtime for this loop. |
| **Python 3** | Pack tools. Model work also needs the pack py3d fork (below), not the unrelated PyPI package named `py3d`. |

Optional, only when the matching skill actually uses them: Blender, Community
Framework / Dabs / VPP, and [DayZ-MCP](https://github.com/willy92wins/dayz-mcp)
(the in-game drive loop; wiring is in `README.md` §8).

### Check the machine

Skill: [`skills/dayz-preflight/SKILL.md`](skills/dayz-preflight/SKILL.md).
Run it **before any other DayZ skill**. It is read-only: it never mounts
`P:\`, never creates junctions, never "fixes" the box.

From the pack root:

```text
python skills/dayz-preflight/preflight.py
```

`P:\` missing is a hard fail (exit 1). Missing Tools, vanilla data, the
workshop junction or DayZDiag are warnings — you decide whether to continue.
Override search with `DAYZ_TOOLS_PATH` and `DAYZ_VANILLA_DATA_PATH` if your
layout is not the Steam default (the skill lists the full resolution order).

For model work, install the pack py3d fork and assert you did not get the
PyPI namesake:

```text
pip install -e tools/py3d
python -c "import py3d; assert py3d.IS_DAYZ_FORK; print(py3d.__version__)"
```

Current fork version is **1.5.0**. Details and limits: [`TOOLS.md`](TOOLS.md).

### Give the pack to your agent

Copy `skills/*` **including** `skills/_shared/` into the agent's skills
directory (`<project>/.claude/skills/` or `~/.claude/skills/` on Claude Code;
any other host: follow [`AGENTS.md`](AGENTS.md)). Keep `_shared/` next to the
skills — several playbooks cite it.

Tell the agent to route from front-matter (`name` + `description`) and to
open a `references/` file only when the playbook names it. Dumping the whole
pack into context buries the answer.

### Write facts down outside the chat

A session's context dies when the session ends. Before multi-session work,
pick a durable store (the pack recommends [Obsidian](https://obsidian.md) or
any plain-Markdown folder) and keep verified APIs with `path:line`,
refuted assumptions, and decisions there. Layout and rules:
[`README.md`](README.md) §7. `knowledge/vault-notes/` is what that layer
looks like once it has grown.

---

## 2. The cycle, once

One pass, in this order. In-game time is expensive (minutes per boot). Exhaust
offline work, batch every pending change into one test, and have a plan B
before you ask for a rebuild. Two rebuilds with no progress means the
strategy is wrong, not the next tweak.

A green offline check predicts that a module **compiles** and an asset
**loads**. It does not predict that the engine **behaves**. Behaviour is the
in-game step.

### Understand

Skill: [`skills/dayz-feature-spec/SKILL.md`](skills/dayz-feature-spec/SKILL.md)
for anything non-trivial — success criteria, in-game Given/When/Then, and a
Forward Contract (classnames, `model.cfg` selections, proxies, stringtable
keys) the next phase will consume. Then load the **domain** skill from the
table in §3 (`dayz-vehicles`, `dayz-weapons`, …).

There is no pack command for this step. The agent greps vanilla under
`P:\scripts\` and cites `path:line`. Memory and semantic search are hints.

### Write

Skill: [`skills/dayz-mod-workflow/SKILL.md`](skills/dayz-mod-workflow/SKILL.md)
for *how* (client/server map before any feature, anti-confabulation,
checklists). Domain knowledge stays in the domain skill.
[`skills/enforce-script-reference/SKILL.md`](skills/enforce-script-reference/SKILL.md)
is the Enforce Script / `config.cpp` reference — load it before writing
script or config. That skill is where those languages are taught; this file
does not repeat them.

No pack command. If more than two APIs in a file are still assumed, the
workflow skill says to stop.

### Lint offline

Skill: [`skills/dayz-mod-workflow/SKILL.md`](skills/dayz-mod-workflow/SKILL.md)
(§ "Gates offline") plus
[`skills/dayz-pbo-build/SKILL.md`](skills/dayz-pbo-build/SKILL.md) for the
pre-pack structure review.

The shipped linter is `dayz-script-validator`. From the pack root, no
install required:

```text
python tools/dayz-script-validator/scripts/script_validator.py <addon_root>
```

Exit `0` PASS / `1` FAIL / `2` WARN. Exit 1 blocks packing. `--terse`
prints the verdict on line one. If the addon has UI, also run:

```text
python tools/dayz-script-validator/scripts/ui_reconcile.py <addon_root>
```

`dayz-pbo-build` walks seven further checks (folder layout, `config.cpp`,
`model.cfg`, textures, LODs, stringtable, scripts). Those checks are a
**playbook**, not a bundled CLI — the skill says there is no `validate.py`
in the pack. Have the agent follow the skill.

When the work is a model, a layout or an animation, reach for the matching
instrument **before** a build. Documented invocations live in
[`TOOLS.md`](TOOLS.md) and [`AGENTS.md`](AGENTS.md) ("Reaching for a tool").
On a clean clone the `python -m dayz_*` forms do **not** resolve until that
tool is installed (`python -m pip install -e tools/<name>` in that tool's
README) or its package is on `PYTHONPATH` (see
`examples/end-to-end/README.md`). Two script-path forms that live in the
tree:

```text
python skills/dayz-p3d-audit/scripts/audit_p3d.py --scan-dir P:\<Mod>
python tools/dayz-ui-lab/dayz_ui_lab/parse.py <layout> --check
```

`audit_p3d.py` imports `py3d` and refuses to start unless it is the pack
fork `>= 1.5.0` (`pip install -e tools/py3d` above). A wheeled vehicle
without `--scan-dir` (or `--config`) skips the FireGeometry wheel-slot
check and can print clean while the wheels never simulate.

Do **not** run `tools/dayz-script-validator/scripts/vanilla_control.py` as
part of making a mod. That control is a gate for people changing the
linter; it walks Bohemia's tree and takes on the order of 85 seconds.

### Pack

Skill: [`skills/dayz-pbo-build/SKILL.md`](skills/dayz-pbo-build/SKILL.md).
Canonical AddonBuilder line
([`knowledge/DAYZ_INFRA.md`](knowledge/DAYZ_INFRA.md) § "Comandos de
invocación canónicos"):

```text
AddonBuilder.exe P:\<ModName> P:\Mods\@<ModName>\Addons ^
    -prefix=<ModName> -temp=P:\temp\<ModName> [-clear]
```

AddonBuilder lives under DayZ Tools (`Bin\AddonBuilder\`). Pass `-clear`
unless you like stale `-temp` copies packing yesterday's `.c`. Never put
sources under `P:\temp\*`: AddonBuilder wipes that folder.

Scripts-only addons (no `.p3d` / `.paa`): default binarize can drop `.c`
and still print `Build Successful`. The skill's pack-only line is:

```text
AddonBuilder.exe P:\<ModName> P:\Mods\@<ModName>\Addons -prefix=<ModName> -temp=P:\temp\<ModName> -clear -packonly
```

Mixed addons (models + scripts) still need binarize; `-packonly` is the
wrong mode there. Confirm `.c` actually landed in the PBO — the skill's
post-build section is the check.

The generated `dayz-test.ps1` (next step) can drive AddonBuilder for you
(`-Build`). Use that once the template is copied into the mod.

### Deploy

There is no separate deploy CLI in the pack. AddonBuilder's destination
**is** the deploy (`P:\Mods\@<ModName>\Addons`), and `P:\Mods` must be the
workshop junction that `dayz-preflight` already checked.

Skill: [`skills/dayz-test-ingame/SKILL.md`](skills/dayz-test-ingame/SKILL.md)
owns the orchestrated build + deploy + launch path.

### Test in-game

Skill: [`skills/dayz-test-ingame/SKILL.md`](skills/dayz-test-ingame/SKILL.md).
It does **not** ship a launcher you run from this repo root. Copy
`skills/dayz-test-ingame/templates/dayz-test.ps1` verbatim into
`<Mod>_dev\tools\`, copy the three `.bat` wrappers, and replace
`__MODNAME__`. The template assumes a `P:\` work-drive layout; re-point
paths if yours differs (`README.md` §8).

From that `tools\` folder, the skill's documented invocations include:

```powershell
.\dayz-test.ps1 -Mod HiddenBase -Preflight
.\dayz-test.ps1 -Mod HiddenBase -Mode all -Build
```

`-Mod` is required (CfgPatches name, no dashes). `-Mode all` is
server-then-client on DayZDiag. Offline mode is marked `[DESIGN]` in the
skill — validate it in-game before trusting it.

Read the skill's filepatching section before expecting hot-reload. Script
and config edits are the general case; `.p3d` / `.paa` / `.rvmat` need
`-Build`. On some installs the PBO wins even for scripts — the skill
documents a `srcprobe` discriminator for that.

Optional auto-drive (spawn, orbit, screenshot, raycast) is
[`skills/dayz-mcp-verify/SKILL.md`](skills/dayz-mcp-verify/SKILL.md), which
talks to DayZ-MCP, published separately. Do not start that bridge from
this pack; see `README.md` §8 and
[`knowledge/dayz-mcp-bridge-protocol.md`](knowledge/dayz-mcp-bridge-protocol.md).

### Debug

Skill: [`skills/dayz-mod-workflow/SKILL.md`](skills/dayz-mod-workflow/SKILL.md)
§5.5 — six layers, top-down (config → entity → actions → client
conditions → server → response). Do not debug layer N+1 until layer N is
confirmed. Logs: `script.log` for script compile/runtime,
`*.RPT` for engine/assets, under the profiles the launcher created.
The workflow skill names the print / `Shape` / `DbgUI` / `DiagMenu` tools;
there is no pack command that "runs the debugger".

Two in-game cycles of the same kind with no measurable progress: stop.
Bisect (workflow Layer 7) or change strategy. A third rebuild is not a
plan.

---

## 3. I want X → look at Y

| I want… | Open |
|---|---|
| Check the box is ready | `dayz-preflight` → `python skills/dayz-preflight/preflight.py` |
| Spec a non-trivial feature first | `dayz-feature-spec` |
| Implement or debug *how* | `dayz-mod-workflow` |
| Write Enforce Script or `config.cpp` | `enforce-script-reference` |
| A car, truck, quad, bike or boat | `dayz-vehicles` |
| A racing-game rip into a drivable car | `rip-vehicle-import` (then `dayz-vehicles`) |
| A plane, seaplane or helicopter | `dayz-aviation` |
| A firearm (entity / `CfgWeapons`) | `dayz-weapons` |
| A zombie, survivor or human NPC | `dayz-characters` |
| Worn clothing | `dayz-clothing` |
| A fence, gate, tent or other buildable | `dayz-basebuilding` |
| Save/load, CF ModStorage, schema migration | `dayz-persistence` |
| HUD, `.layout`, widgets, Dabs MVC | `dayz-ui-development`; offline parse: `python tools/dayz-ui-lab/dayz_ui_lab/parse.py <layout> --check` |
| Rigid bodies, raycasts, "I walk through it" | `dayz-physics-engine` |
| `CfgSoundShaders` / sounds not playing on dedicated | `dayz-sound-system` |
| `.ptc` / particle script | `dayz-particles` |
| A door, hatch or lid | `dayz-doors` |
| Textures, `.paa`, `.rvmat`, PBR | `dayz-texture-pipeline` |
| Author a `.p3d` from Blender / py3d | `dayz-model-pipeline` + pack `tools/py3d` |
| Collision / winding / silent `.p3d` killers | `dayz-p3d-audit` → `audit_p3d.py` above |
| Model loads white, untextured or invisible | `dayz-model-preflight` (`TOOLS.md`; install that tool first) |
| Preview an MLOD `.p3d` without launching DayZ | `dayz-3d-viewer` (`TOOLS.md`; install that tool first) |
| Animation never plays / inspect an RTM | `dayz-animation-pipeline` + `dayz-animation-formats` (`TOOLS.md`) |
| Realistic motion gates | `dayz-realistic-animation-director` |
| Animate in Blender | `blender-animation` |
| Expansion eAI | `dayz-ai-patterns` |
| Learn from someone else's PBO | `dayz-pbo-reverse-engineering` |
| Pack / "is this addon ready" | `dayz-pbo-build` + the linter in §2 |
| Launch DayZDiag with the mod | `dayz-test-ingame` (template, not a pack-root CLI) |
| Auto-test in-game via MCP | `dayz-mcp-verify` + `README.md` §8 |
| Audit persistence / data-loss risk | `rigorous-data-audit` |
| Compare two binarized models | `dayz-odol-strict` (`TOOLS.md`; backend is external) |
| Vehicle proxy graph / fit | `dayz-vehicle-proxy-contract` (`TOOLS.md`) |
| AI-generated mesh into DayZ | `ai-3d-to-dayz` |
| See the pack tools on a synthetic `.p3d` | `examples/end-to-end/README.md` |
| What is true of a skill on which build | [`compatibility-matrix.md`](compatibility-matrix.md) |
| Change *this repository* | [§4](#4-what-this-file-is-not) |

Forty playbooks sit under `skills/`. The table above is the frequent
routes. The rest (`blender-assembly`, `uv-clean-atlas`, `mixamo-retarget`,
`ardy-motion-generation`, …) still apply when their `description:` matches —
read front-matter, then that `SKILL.md`.

---

## 4. What this file is not

- **Not the playbooks.** Procedures, checklists, API rules and worked
  failure modes live in `skills/*/SKILL.md` and the `references/` those
  files name.
- **Not a tool manual.** Coverage, refusals and full CLIs:
  [`TOOLS.md`](TOOLS.md).
- **Not an environment spec for every machine.** `dayz-test-ingame` and
  `dayz-mcp-verify` assume a particular Windows / `P:\` layout. The ideas
  transfer; generated scripts need re-pointing (`README.md` §8).
- **Not a DayZ install guide, Workshop signing guide, or production
  server guide.** Those are outside the pack.
- **Not current session state.** [`AGENTS.md`](AGENTS.md) carries none.
  Measure the tree if you need to know what is true of it.

### Changing the pack

That is a different job. Read [`CONTRIBUTING.md`](CONTRIBUTING.md) and the
Gates section of [`AGENTS.md`](AGENTS.md). Install the CLI once (without
it, `python -m packctl` only resolves while the shell is in the repo
root):

```text
pip install -e .
```

The gate that must be green before publishing:

```text
python -m packctl validate --root . --report reports/validate.json
python -m packctl gate --root . --report-dir ../pack-gate-reports
```

`gate` needs its report directory **outside** the repository
(`GATE-REPORT-IN-ROOT` is a silent exit 1) and the external Agent Skills
validator (`PACK_SKILLS_REF_ROOT` / PyPI `skills-ref`, console script
`agentskills`). `validate` is provenance, privacy, links and claim
ranges. `gate` adds skill validation, Python compilation, the layout
corpus and a reproducible build.

[`AGENTS.md`](AGENTS.md) also lists `python -m pytest -q`. **That does not
run from the repository root.** The suites here are per-tool by design —
each tool's README says to run its tests from that tool's directory — and
two of them share test-module basenames (`test_cli.py`, `_support.py`), so
a root-level collection aborts before a single test runs. Run each suite
from its own directory, and use `packctl gate` as the pack-wide check.

`python tools/dayz-script-validator/scripts/vanilla_control.py` is only
for commits that touch `tools/dayz-script-validator/` (a new rule, a
detector, or the parser). It is not a step in the mod cycle. Without a
local vanilla tree it SKIPs (exit 2). A green control only proves the
linter is silent on Bohemia's tree; it does not prove the new rule
catches anything.

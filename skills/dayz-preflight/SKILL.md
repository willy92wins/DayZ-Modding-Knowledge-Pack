---
name: dayz-preflight
description: "Use when: P:\\ not mounted, DayZ Tools missing, workshop folder, vanilla data unpacked, before building/packing, AddonBuilder path, DayZDiag locatable. Read-only env check. Not launch/test: dayz-test-ingame."
---

# /dayz-preflight

Verify the DayZ modding environment before doing any DayZ work. Halts with a clear error if `P:\` is not mounted (per `_shared/dayz-conventions.md`); warns on optional checks so the user can decide whether to proceed.

**Read-only.** Preflight inspects state and reports. It never mounts drives, creates junctions, or otherwise mutates the filesystem — fixes belong to dedicated setup skills.

**Non-redundancy note:** If the flow goes through dayz-test-ingame, its `dayz-test.ps1` preflight already checks AND auto-fixes these (junction creation etc.) — this skill is the read-only/warn variant.

Follow `_shared/dayz-conventions.md`.

## What it checks

| # | Check | Severity |
|---|---|---|
| 1 | `P:\` drive is mounted | **hard fail** — exit 1 |
| 2 | DayZ Tools installed (AddonBuilder.exe locatable) | warn |
| 3 | Vanilla DayZ data unpacked under `P:\` | warn |
| 4 | `P:\Mods\` is a directory junction to `<DayZ install>\!Workshop\` (not a regular folder, not missing, not dangling) | warn — build-pbo hard-fails on the same condition |
| 5 | `DayZDiag_x64.exe` locatable (required for `-filePatching` iteration; retail exes block past loading) | warn |

Exit code 0 = ready (or warnings only). Non-zero = hard environment issue, named in stderr.

## How paths are resolved

Paths are not blindly hard-coded. Resolution order, first hit wins:

| What | Order |
|---|---|
| **DayZ Tools install root** | 1. `DAYZ_TOOLS_PATH` env var → 2. Windows registry (`HKLM\SOFTWARE\WOW6432Node\Bohemia Interactive\DayZ Tools` → `Path` value, plus the `HKLM` non-WOW6432 and `HKCU` siblings) → 3. Common Steam paths (`C:\Program Files (x86)\Steam\steamapps\common\DayZ Tools`, then `C:\Program Files\…`). A candidate counts only if `Bin\AddonBuilder\AddonBuilder.exe` exists under it. |
| **Vanilla data root** | 1. `DAYZ_VANILLA_DATA_PATH` env var → 2. Canonical names on P:\: `P:\dz`, `P:\DZ`, `P:\dta`. A candidate counts only if it exists and is non-empty. |
| **`P:\` and `P:\Mods\`** | Fixed by DayZ engine convention — not configurable. |

To override either env var, set it in your shell or in the user/system environment before running any DayZ skill. Example (PowerShell): `$env:DAYZ_TOOLS_PATH = 'D:\Games\Steam\steamapps\common\DayZ Tools'`.

The `find_dayz_tools()` and `find_vanilla_data()` helper functions in `preflight.py` are reusable — future DayZ skills (e.g. `dayz-pbo-build`) should import them instead of re-implementing path discovery.

## How to run

This skill's directory is
`<skills>\dayz-preflight\`.

```cmd
python <this-skill's-dir>\preflight.py
```

## When to run

- Before invoking any other DayZ skill.
- After a fresh clone of the repo.
- After a fresh boot of the workstation — `P:\` does not auto-mount; you have to open DayZ Tools and mount it (or use the Tools "Mount P drive" command) at the start of each session.

## Output

Plain text, one line per check:

```
DayZ preflight

[OK]    P:\ is mounted
[OK]    DayZ Tools found: C:\Program Files (x86)\Steam\steamapps\common\DayZ Tools
[OK]    DayZDiag_x64.exe found: C:\Program Files (x86)\Steam\steamapps\common\DayZ\DayZDiag_x64.exe
[OK]    Vanilla data found: P:\dz
[OK]    Workshop deploy folder exists: P:\Mods

Preflight complete.
```

If `P:\` is not mounted:

```
DayZ preflight

[FAIL]  P:\ is NOT mounted
        Open DayZ Tools and mount the P drive (Tools menu > Mount P drive),
        or map it directly: subst P: "<dayz-projects>"
```

Exit 1, and downstream DayZ skills should refuse to run.

## Do not

- Don't try to mount `P:\` programmatically — it's a DayZ Tools function and assumes Tools is installed and configured. Surface a clear message and let the user mount it. (Manual alternative when Tools' mount is unavailable: `subst P: "<dayz-projects>"` — the operational route registered in dayz-test-ingame.)
- Don't gate on the DayZ Tools / vanilla data / Workshop folder checks — they're warnings, not errors. The user may have a custom layout.
- Don't reintroduce hard-coded paths in other DayZ skills. Import `find_dayz_tools` / `find_vanilla_data` from this skill so resolution stays consistent (env var → registry → fallback).

## SP-010 — Debug/diagnosis preflight extension

For DEBUG/diagnosis tasks (not just builds), also verify/request mounted: (1) unpacked vanilla scripts (`P:\scripts`) — the authoritative source for engine/action/CarScript behavior; (2) the deployed mod tree (`P:\<Mod>`) to confirm WHAT is actually in the build; (3) the working reference mod. Without these, diagnosis degrades to memory/diff. [LL-075, LFQuad 2026-05-25]

## SP-374 — Object Builder's external viewer points at a non-existent exe by default

Buldozer is the cheap answer to "how does it look?" — materials, alpha and animations previewed
without paying an in-game cycle. On a stock install the viewer is wired to a path that does not
exist, so it silently never gets used and the question goes in-game instead.

Check the registry value, and that the exe behind it is really there:

```powershell
$v = (Get-ItemProperty 'HKCU:\Software\Bohemia Interactive\Dayz Tools\Object Builder\CConfig').'%External Viewer'
$exe = ($v -split ' -buldozer')[0].Trim('"')
Test-Path $exe
```

FAIL with the real path as the suggestion: `<steamapps>\common\DayZ\DayZ_x64.exe`. The DayZ Tools
installer writes `<steamapps>\common\DayZ_x64.exe` — without the `DayZ\` directory — which is why
the default is broken out of the box.

Measured on this box: configured path `Test-Path` = False, real path = True, `P:\Buldozer` present.
Cost of not checking it: ~20 SUB_BRZ sessions paid in-game cycles for "does it show?" questions
(label alpha, needle size, quad behind the screen) with zero mentions of Buldozer in the project
handoff.

Not verified yet: that Buldozer opens a *custom* `.p3d` with its rvmats. Do not promote this to
`dayz-model-pipeline` / `dayz-vehicles` as a visual gate until that part is measured.

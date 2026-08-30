---
name: dayz-pbo-build
description: >
  Pre-build validation and packaging pipeline for DayZ mod addons. Validates config.cpp
  syntax and class inheritance, checks all texture/material paths exist, verifies .p3d
  LOD structure, validates model.cfg skeleton and animation references, checks stringtable.csv
  completeness, and generates correct $PBOPREFIX$ and folder structure for AddonBuilder.
  Use when user mentions: PBO, build, pack, addon, AddonBuilder, validate mod, pre-build check,
  deploy mod, release mod, config.cpp errors, missing textures, broken references, or
  any DayZ mod packaging workflow. Also trigger when user says "check my mod" or "is my mod ready".
---

# DayZ PBO Build Validator

Complete pre-build validation pipeline for DayZ mod addons. Catches configuration errors, missing assets, and structural problems BEFORE packing into PBOs—avoiding in-game crashes and deployment failures.

## Overview

This skill runs seven validation checks in sequence on a DayZ addon folder structure:

1. **Folder Structure** – Required files ($PBOPREFIX$, config.cpp), naming conventions, stale files
2. **config.cpp Syntax** – Brace balance, semicolons, class hierarchy, hiddenSelections matching
3. **model.cfg Validation** – Skeleton bones, named selections, animation references
4. **Texture/Material Paths** – Every .paa and .rvmat exists and is accessible
5. **.p3d LOD Structure** – LOD types, geometry mass, vertex budgets, named selections consistency
6. **Stringtable Completeness** – All #STR_ keys present and accounted for
7. **Script Validation** – Enforce Script syntax, #include paths, common pitfalls

Each check reports **PASS**, **WARN**, or **FAIL** status. The final summary shows all blockers before packing.

---

## Validation Checks (Detailed)

### 1. Folder Structure Validation

**Checks performed:**
- **REQUIRED:** `config.cpp` exists at addon root
- **REQUIRED:** `$PBOPREFIX$` file exists (single line: `mymod\myaddon` format)
- **RECOMMENDED:** `data/` folder (for textures, .rvmat, .p3d files)
- **RECOMMENDED:** `scripts/` folder (for .c, .cpp, .h files)
- **REQUIRED:** No spaces in folder names (DayZ tools reject these)
- **REQUIRED:** No uppercase file extensions (.PAA, .CPP are flagged)
- **FAIL:** Stale files found (.bak, .blend, .psd, .xcf, .tmp, .swp—these bloat PBOs)
- **WARN:** Large asset files > 10MB (texture atlases, unoptimized meshes)

**Example output:**
```
[PASS] config.cpp found at addon root
[PASS] $PBOPREFIX$ file present: mymod\myaddon
[WARN] .blend file found: data\model_source.blend (should not be packed)
[PASS] Folder names follow conventions (lowercase, no spaces)
```

---

### 2. config.cpp Syntax Validation

This check is critical—most DayZ mod failures start here.

**Checks performed:**
- **Brace balance:** Count `{` and `}` to detect unclosed classes
- **Semicolons:** Every class property and array must end with `;`
- **Required CfgPatches class:**
  - Must exist with at least one patch subclass
  - Each patch requires: `units[]`, `weapons[]`, `requiredVersion`, `requiredAddons[]`
- **Class inheritance verification:**
  - Validate parent classes exist (e.g., Inventory_Base, Container_Base, Land_Stone_*)
  - Warn if parent class is not a known DayZ base (may not exist in vanilla)
- **hiddenSelections matching:**
  - `hiddenSelectionsTextures[]` and `hiddenSelectionsMaterials[]` are each aligned index-by-index with `hiddenSelections[]` — each array (when present) must have the SAME length as `hiddenSelections[]`, not a combined total
  - Example: `hiddenSelections[] = {"skin1", "skin2", "metal"}` (3 items) → `hiddenSelectionsTextures[]` has 3 entries and `hiddenSelectionsMaterials[]` has 3 entries
- **AnimationSources reference check:**
  - Any AnimationSource defined here must be referenced in model.cfg (if model.cfg exists)
- **Duplicate class names:** Same class cannot be defined twice
- **No syntax helpers:** Reject obvious Python/macro syntax in .cpp (these get missed at compile time)

**Example output:**
```
[FAIL] config.cpp line 15: Unclosed brace (expected 0, found 1 extra {)
[FAIL] config.cpp line 42: Missing semicolon after property "units[]"
[PASS] CfgPatches structure valid (1 patch: MyMod_Item01)
[WARN] Class inheritance: parent "CustomBase_Broken" not recognized (may not exist)
[PASS] hiddenSelections arrays aligned (3 selections, 3 textures, 3 materials)
[FAIL] Duplicate class name "Item_Torch" defined at lines 28 and 105
```

---

### 3. model.cfg Validation

Only checked if `model.cfg` exists in the addon.

**Checks performed:**
- **CfgSkeletons section:**
  - Every bone listed in `skeletonBones[]` must exist
  - Check that bone names follow DayZ naming conventions (lowercase with underscores)
  - Verify no circular parent references
- **CfgModels section:**
  - Class name must match the .p3d filename (case-sensitive: `Item_Compass` class → `Item_Compass.p3d`). **Mismatch is silent and severe:** the engine falls back to `CfgModels.Default` (no skeleton/sections) for that model, so a WEAPON's attachment proxies stop rendering — attachments still attach (visible in slots) and the standalone item still renders in the world, but are INVISIBLE on the weapon (in-hands, inventory preview, ground), with NO RPT error. Common trigger: renaming a model `.p3d` (e.g. `body.p3d`→`body_raised.p3d` for a grip tweak) without updating CfgModels. Fix: `class <new>: <old> {};`. Re-run this check after ANY model rename. (Origin: A6_SR2M 2026-06-25.)
  - Type must be valid: `ArmaModel`, `BaseMiliHeliModel`, etc.
- **Animations within CfgModels:**
  - `selection` must exist as a named selection in the corresponding .p3d
  - `axis` must exist as a memory point pair in the p3d (e.g., `axis_lever`, `axis_lever_end`)
  - `source` must match an AnimationSource name from config.cpp
  - `speed` values should be reasonable (1.0 = 1 second)
- **Memory point pairs:** Any animation with `axis` requires matching memory points in p3d

**Example output:**
```
[PASS] Skeletons defined correctly (5 bones)
[FAIL] model.cfg class "Item_Watch" doesn't match .p3d filename (found: Item_WatchGold.p3d)
[WARN] Animation "door_open": selection "door_frame" not found in named selections
[FAIL] Animation "lever_rotate" references axis "lever_axis_end" (axis endpoint not found in p3d)
[PASS] Animation source "click_anim" matches config.cpp AnimationSources
```

---

### 4. Texture/Material Path Validation

Scans all texture references and verifies files exist.

**Checks performed:**
- **Scan sources:**
  - config.cpp: `hiddenSelectionsTextures[]`, `hiddenSelectionsMaterials[]`, any quoted `.paa` or `.rvmat`
  - .rvmat files: extract referenced texture paths
  - .p3d face textures (if py3d available)
- **Path existence:**
  - Every referenced `.paa` file MUST exist relative to addon root
  - Every referenced `.rvmat` file MUST exist
  - Paths are case-sensitive on Linux/server (always check capitalization)
- **File format checks:**
  - WARN if `.png` file referenced (should be `.paa` for DayZ)
  - WARN if `.dds` file referenced (use `.paa` instead)
  - .rvmat must reference valid texture paths within the addon or from common DayZ paths
- **Texture atlas validation:**
  - If multiple selections reference the same texture, verify texture has enough area for all UVs

**Example output:**
```
[FAIL] Texture not found: data\textures\body_co.paa (referenced in config.cpp line 45, class Item_Shirt)
[WARN] PNG file detected: data\textures\logo.png (convert to PAA for better compression)
[PASS] All 12 texture references validated and found
[WARN] Texture path capitalization: referenced as "Textures\Cloth_Co.paa" but file is "textures\cloth_co.paa"
[PASS] .rvmat materials reference valid texture paths
```

---

### 5. .p3d LOD Structure Validation

Only checked if py3d is available and .p3d files exist.

**Checks performed:**
- **LOD types present:**
  - REQUIRED: At least 1 Resolution LOD (LOD 0.0) for in-game appearance
  - REQUIRED: Geometry LOD for collision/physics
  - REQUIRED: Memory LOD (named selections + memory points)
- **Geometry LOD integrity:**
  - All components must have mass > 0 (0 mass = ignored by engine)
  - Faces must not be zero-area (degenerate triangles)
  - Warn if geometry LOD vertices > 3000 for small items (performance impact)
- **Memory LOD:**
  - Must have at least `ce_center` memory point (center of mass)
  - Warn if missing `ce_geom` or `ca_` collision points
- **Named selections:**
  - Consistent across LODs (if named_sel exists in LOD0, should exist in LOD2)
  - Warn if asymmetric (e.g., "Left_Arm" exists but no "Right_Arm")
- **Vertex count budgeting:**
  - LOD0: up to 5000 vertices (warn if higher for small objects)
  - LOD1: 40-60% of LOD0
  - LOD2 (far): 10-20% of LOD0

**Example output:**
```
[PASS] All required LOD types present (Resolution + Geometry + Memory)
[PASS] Geometry LOD mass valid (all components > 0)
[FAIL] Memory LOD missing ce_center point (required for physics)
[WARN] LOD0 vertex count: 4200 (high for small item, consider optimization)
[PASS] Named selections consistent across LODs (8 selections)
[WARN] No collision points (ce_geom) in Memory LOD—object may not collide properly
```

---

### 6. Stringtable Validation

DayZ uses **`stringtable.csv`**, not the `stringtable.xml` of Arma 3. Corrected
2026-08-21 after measuring this workspace: zero `stringtable.xml` anywhere in the DayZ
project tree, 38 `stringtable.csv`, and the two deployed PBOs checked (`LFPowerGrid`,
`LFGungame`) each carry `stringtable.csv` and no XML. Following the XML form produces a
file the engine never reads, and the engine does not complain — an unresolved key prints
its own name and logs **nothing** (measured: zero RPT lines for a missing key across a
49,340-byte client log), so this fails silently all the way to the player's screen.

**Format**, verified against two shipping mods (`AP_equipment_PUBLIC/stringtable.csv:1`,
`lfhelicore/stringtable.csv:1`): a header row `"Language","original","english",…` followed
by one row per key. The key sits in column 1 **without the leading `#`** — the `#` belongs
only to the reference in code, config or `.layout`. UTF-8, no BOM, LF.

**An unresolved stringtable is a CSV-header problem, not an addon-size problem.** Two
in-game bisection ladders (measured 2026-08-21) closed this: a three-file addon
(`$PBOPREFIX$` + minimal config.cpp + stringtable.csv) resolves its keys, and two data
rows are enough — provided the CSV carries the full 7-column reference header
(`"Language","original","english","spanish","german","russian","chinesesimp"`). With a
4-column header (no german/russian/chinesesimp) every key stays unresolved at any corpus
size, even though the PBO mounts and serves files and the client's own language column is
present with text. Fill untranslated columns with the english text. Earlier same-day probes
that blamed addon minimality were measuring a degenerate CSV. Full rule and evidence:
dayz-ui-development skill, LOCALIZATION section.

**Checks performed:**
- **Scan all script files (.c, .cpp) for `#STR_` references**
- **Scan config.cpp and every `.layout` for `#STR_` references** (displayName, description,
  and widget `text` alike)
- **`stringtable.csv` existence:**
  - If `#STR_` found but no `stringtable.csv` → FAIL
  - If it exists, check the header row and that every data row has the same column count
- **Key coverage:**
  - Every `#STR_KEY` referenced must appear in column 1 of some `stringtable.csv`, minus the `#`
  - WARN about orphaned keys (defined in stringtable but never used)
  - Prefer a mod-specific key prefix: names like `STR_UI_YES` invite collisions with other mods
- **Language completeness:**
  - Check that all languages (English, Russian, etc.) have values for each key
  - WARN if translation is missing or empty

**Example output:**
```
[FAIL] stringtable.csv not found, but 5 #STR_ references in config.cpp
[PASS] stringtable.csv header valid (4 columns, every row matches)
[FAIL] Missing key: #STR_MYMOD_DEVICE_NAME (used in config.cpp line 23)
[WARN] Orphaned key: #STR_OLD_DESCRIPTION (defined in stringtable but never referenced)
[WARN] Incomplete translation: Russian text missing for #STR_ITEM_DESC (only English present)
[PASS] All 12 #STR_ references have stringtable entries
```

---

### 7. Script Validation (Basic)

Checked if scripts exist in `scripts/` folder.

**Checks performed:**
- **Enforce Script (real gotchas — the language SUPPORTS ternary, `++`/`--`, `foreach`):**
  - Add to arrays with `.Insert()` / `.InsertAll()` (no array `+=` concatenation operator)
  - No bare function calls without assignment or statement context
- **#include path resolution:**
  - Every `#include "path/file.h"` must point to existing file
  - Check both relative and absolute paths
- **Common pitfalls:**
  - `GetGame()` used in destructors without null check
  - `Print()` left in debug code (warn, not fail)
  - Infinite loops detected (while true without break)
  - Missing return statements in non-void functions
- **Syntax basics:**
  - Unclosed strings, invalid escape sequences
  - Invalid class declarations or stray tokens

**Example output:**
```
[WARN] scripts/Item_Base.c line 42: array '+=' concatenation not supported - use .InsertAll()
[PASS] No #include path errors (5 includes resolved)
[PASS] No unsupported array '+=' concatenation
[WARN] scripts/Item_Base.c line 103: GetGame() called in destructor without null check
[FAIL] #include "scripts\missing.h" not found
[PASS] Script syntax valid (no orphaned braces or quotes)
```

---

### 8. Wheeled-vehicle wheel-slot <-> FireGeometry consistency (P1, release-blocking)

Vehicles only. For PhysX to seat a wheel (`WheelCountPresent() > 0`), the selection
named by `config.cpp > CfgSlots > <wheel-slot>.selection` MUST exist in the body's
**FireGeometry LOD**. A selection present only in visual LODs binds the slot as
inventory but the wheel never simulates: `WheelCountPresent()=0`, no traction, no
spin, NO RPT error - a silent killer (see `enforce-script-reference` wheel-attachment
rule, `dayz-model-pipeline` Rule 20).

This check lives in the `dayz-p3d-audit` validator (SP-017). Run it pre-build and
treat a CRITICAL as release-blocking:

```
python <dayz-p3d-audit>/scripts/audit_p3d.py --scan-dir P:\<Mod>
```

`--scan-dir` auto-discovers the mod's `config.cpp` and cross-checks every wheel
slot's selection against the body FireGeometry. Outcomes:
- `CRITICAL: SP-017: wheel-slot selection '<n>' ... ABSENT from the FireGeometry`
  -> the wheel will not simulate. **BLOCK the release**; apply the additive py3d fix
  (alias the FireGeo wheel-proxy face into selection `<n>`) before packing.
- `NOTE: SP-017 ... mapping unresolved (no CfgSlots ...)` -> verify manually
  (vanilla auto-registration configs that omit `CfgSlots`).

`audit_p3d.py` exits 1 on any CRITICAL, so wiring `--scan-dir` into the pre-build
gate (alongside the config/texture/LOD checks above) blocks a silently-broken
vehicle from being packed. PARITY note: `class=vehicle` on the Geometry LOD (SP-027)
is also reported, but it is parity only - NOT the wheel-sim gate.

---
## Output Format

After all checks complete, the skill generates a structured report:

```
=================================
DayZ Addon Validation Report
=================================

Addon: mymod\myaddon
Path: C:\Mods\mymod\myaddon
Date: 2026-03-28

--- VALIDATION RESULTS ---

[PASS] Folder structure valid
  └─ config.cpp found
  └─ $PBOPREFIX$ correct (mymod\myaddon)
  └─ No stale files detected

[PASS] config.cpp syntax OK
  └─ 12 classes, 3 patches (CfgPatches valid)
  └─ All braces balanced, semicolons correct
  └─ hiddenSelections count matches textures

[WARN] model.cfg: animation "lever_rotate" references axis "lever_axis"
  └─ Verify this axis exists as memory point pair in Item_Watch.p3d

[FAIL] Texture not found: data\textures\body_co.paa
  └─ Referenced in config.cpp line 45, class Item_Shirt
  └─ Expected at: C:\Mods\mymod\myaddon\data\textures\body_co.paa

[FAIL] stringtable.csv: missing key #STR_MYMOD_DEVICE_NAME
  └─ Used in config.cpp line 23, class Item_Device displayName
  └─ Add entry: <Key ID="STR_MYMOD_DEVICE_NAME"><Original>Device Name</Original>...

[PASS] All textures and materials found (8 references)

[PASS] .p3d LOD structure valid
  └─ Item_Watch.p3d: LOD0 (2104 verts), LOD1 (800 verts), Geometry, Memory
  └─ All named selections consistent across LODs
  └─ Memory LOD has ce_center

[PASS] Scripts: no Enforce violations found (3 files checked)

--- SUMMARY ---
✓ 5 PASS
⚠ 1 WARN
✗ 2 FAIL

Status: BLOCKED - Fix 2 critical errors before packing
  1. Add data\textures\body_co.paa
  2. Add STR_MYMOD_DEVICE_NAME to stringtable.csv (column 1, no leading #)

Next: Run AddonBuilder after corrections are complete
```

---

## Quick Commands

Use these prompts to trigger specific validation paths:

| User Says | Checks Run |
|-----------|-----------|
| "validate my mod" | All 7 checks |
| "check config.cpp" | Check 2 only |
| "check textures" | Check 4 only |
| "check my p3d" | Check 5 only |
| "is my mod ready for PBO?" | All checks, focused summary on blockers |
| "what's missing?" | All checks, emphasize FAILs |
| "validate for AddonBuilder" | All checks, suggest next steps |
| "I have config errors" | Check 2 with detailed line numbers |

---

## Understanding $PBOPREFIX$

The `$PBOPREFIX$` file is critical for DayZ's mod loading system.

**File location:** Addon root (same folder as config.cpp)
**File contents:** Single line, e.g.:
```
mymod\myaddon
```

**Rules:**
- Use backslashes `\` (not forward slashes)
- No trailing backslash
- No quotes or extra whitespace
- Must be unique across all addons (namespace collision = invisible mod)

**Example folder structure:**
```
DayZ_Addons\
  mymod\
    myaddon\
      config.cpp
      $PBOPREFIX$
      data\
        model.p3d
        texture.paa
      scripts\
        Item_Custom.c
```

With `$PBOPREFIX$` containing: `mymod\myaddon`

When packed, this becomes `mymod\myaddon.pbo` in the mod directory.

---

## AddonBuilder Workflow

After validation passes, use AddonBuilder to pack and binarize.

**Location:** DayZ Tools (included with game)
```
C:\Program Files (x86)\Steam\steamapps\common\DayZ Tools\Bin\AddonBuilder\
```

### Locate the authoritative build source before validation (SP-343)

Do not infer the source tree from the checkout that is easiest to find. Before basing a fix,
audit, or rebuild on a mod tree:

1. Read `build_*.ps1` and resolve the value assigned to `$source`; that is the tree the build
   script actually feeds to AddonBuilder.
2. Compare a known byte-stable payload artifact from that tree (for example, a `.c` entry),
   by content hash, with the corresponding entry in the deployed PBO. A matching path or
   timestamp is not evidence of identity.
3. Reject trees marked as display-only, archived, or not-for-build, even when their folder
   names look canonical.

A matching artifact locates the candidate source; it does not prove release closure. Before
release, apply the full-tree provenance gate in LL-367: canonical commit/source tree ->
complete build tree -> PBO.

**Command line (canonical invocation — see DAYZ_INFRA.md §Comandos de invocación canónicos):**
```batch
AddonBuilder.exe P:\<ModName> P:\Mods\@<ModName>\Addons -prefix=<ModName> -temp=P:\temp\<ModName> [-clear]
```

**Command line (pack only, skip binarization):**
```batch
AddonBuilder.exe P:\<ModName> P:\Mods\@<ModName>\Addons -prefix=<ModName> -temp=P:\temp\<ModName> -clear -packonly
```

**Temp-stale trap:** without `-clear` the `-temp` sync is INCREMENTAL and can serve stale
source — a changed `.c` may not be re-copied, so the PBO keeps packing old code while the
build reports success. If the PBO does not reflect your changes, wipe `P:\temp\<ModName>`
(or pass `-clear`) before rebuilding. Never place staging or sources under `P:\temp\*`:
AddonBuilder clears its `-temp` before copying.

**Binarized-build preflight rules (SP-155, verified 2026-08-03 ArmorHneck build):**

1. **Staging is mandatory for binarized builds.** The canonical `AddonBuilder P:\<Mod> …`
   invocation is fragile on a `P:\` with history: AddonBuilder derives `[Project]=P:\` and
   passes `-addon="P:"` to binarize, which parses configs across ALL of `P:\` and aborts on
   the first broken foreign config (e.g. `P:\temp\Utopia_PC\…\legacy_generic_attempt\config.cpp`).
   AddonBuilder reports "Build failed" with exit 0 and does not name the culprit (with
   `-noLogs -silent` the path never appears). **Rule:** stage a clean copy in
   `%TEMP%\<mod>_build_<stamp>\src\<Mod>` and run AddonBuilder against the staging directory
   (`[Project]` = staging → clean addon-space). "Material not loaded" / "Note: creating empty
   class" messages from the staging are tolerable (verified: HH-60G heli and ArmorHneck
   clothing both build and work). Validated end-to-end template: `ArmorHneck_dev\tools\build.ps1`.

2. **RVMATs referenced only from config.cpp do NOT enter the PBO.** The binarize whitelist
   (`*.p3d;*.paa`) + face-reference scan only pulls materials referenced by p3d FACES. An rvmat
   referenced solely from config.cpp (healthLevels damage/destruct, hiddenSelectionsMaterials
   on variants) is silently omitted, and the build still prints "Build Successful". Deferred
   in-game symptom: no visual damage swap / RPT "Material not loaded" when the item breaks.
   **Rule:** after the build, parse the PBO ENTRIES and compare against the full rvmat list
   from config.cpp (not just a classname grep). Copy any missing rvmat into
   `abtemp\<mod>\data\` and re-package with `-packonly` — use a SEPARATE `-temp` path
   (with `-clear`, the temp is wiped before the copy lands).

3. **Parallelism.** Binarize without high `-maxProcesses` is slow on dense skinned p3d
   (>5 min for 3 models at 18k pts in series). Use AddonBuilder's default parallelism and
   run in background; an apparent hang may just be serial + skinning.

4. **config.bin may silently fail to register in the engine (most severe).** The mod mounts
   (engine reads the dir, zero RPT errors) but `CreateObjectEx` returns `unknown_type` and the
   item does not exist for VPP. The SAME PBO re-packaged with config.cpp as TEXT registers and
   spawns (bisection with control vanilla Armband_Pink). Correlated symptom: `unRap` exit 255
   on that config.bin. **Rule:** (a) pack config.cpp as TEXT in local PBOs (the full-build
   binarize is only exploited for p3d ODOL); (b) the "it actually mounts" gate is an in-game
   spawn (world_spawn from the bridge or console), NEVER just strings/entries of the PBO —
   static analysis of config.bin reported "healthy" while the engine ignored it.

The orchestrated build path (temp wipe + deploy + launch) lives in dayz-test-ingame's
`dayz-test.ps1` template.


**Binarize via AddonBuilder CLI (SP-069, LFHeli OH-1 2026-07-19):**

1. **`-temp` for binarize must stay under `P:\`.** With `-temp` outside `P:\`, the
   "Binarizing" step dies in ~4 s with "Process ended with non-zero code. Exit code: 1",
   empty stderr and zero p3d produced — AddonBuilder still exits 0 ("Build failed" only
   in its log). Keep `-temp` on `P:\` (canonical: `-temp=P:\temp\<ModName>`).
   `-packonly` still accepts local folders outside `P:\`, so local staging remains valid.

2. **ODOL output is neither the source nor the target.** It lands in
   `<temp>\<prefix>\...` (e.g. `-temp=P:\x\temp -prefix=LFHeli` → ODOL in
   `P:\x\temp\LFHeli\models\`). The PBO AddonBuilder leaves in the target in binarize
   mode can be a tiny-PBO (~1 KB) that still prints "Build Successful".

3. **Verified release pattern** (binarized assets + scripts in a separate mod):
   binarize → collect ODOL from `<temp>\<prefix>\` → stage ODOL + raw `config.cpp` →
   `-packonly -prefix=<prefix>` → content gate (`config.cpp` present, no `config.bin`,
   N ODOL magics, prefix correct).

**What AddonBuilder does:**
1. Reads $PBOPREFIX$ → creates output filename (mymod\myaddon.pbo)
2. Binarizes config.cpp (text → binary, ~90% smaller, faster load)
3. Optimizes .p3d files (binary format, LOD structure intact)
4. Packs all files into .pbo container
5. Generates PBO header with prefix

**Output:** `mymod\myaddon.pbo` ready to place in `@YourMod/addons/`


**Comparison builds: match the mode to the reference artifact.** AddonBuilder has two modes and both produce a PBO that loads:
- **with `-packonly`**: packs raw, does not binarize `.p3d`. Large PBO.
- **without `-packonly`**: binarizes `.p3d` to ODOL. Much smaller PBO.

When the PBO is going to be used as a comparison term (compile gate, module measurement, A/B footprint, RED/GREEN of fixtures), **it must be built with the SAME mode as the artifact it is compared against**. Verify by size before deploying: a PBO that differs from the reference by a factor of 3–4× is not a variation of your code, it is a different build mode.

---

## Post-build check — confirm the PBO actually contains your scripts (binarize drops `.c`)

AddonBuilder's default binarize mode does **not** copy `.c` script files — they aren't in its
binarize/copy include-list. A scripts-heavy or scripts-only addon built with a plain
`AddonBuilder src dst -clear` can pack to a **config-only PBO** (`config.bin` + the CfgMods
path strings, nothing else) while still printing `Build Successful`. In-game the mod *mounts*
(its CfgPatches name appears in the server `script.log` `defines:` list) but **no script runs**:
no modded class merges, no hook fires. Verified 2026-06-03 — a scripts mod packed to 662 bytes
under binarize; `-packonly` produced the correct 124 KB PBO with all its `.c`.

Pack mode by addon type:
- **Scripts-only** (no `.p3d`/`.paa`): build with `-packonly` (copies everything as-is;
  `config.cpp` stays text, which DayZ loads fine).

`.c` is not the only casualty of the include-list: **`.csv` is dropped too**. Measured
2026-08-20 on a two-file addon — the binarizing pass produced a PBO with `config.bin` and
**no `stringtable.csv`**, while `-packonly` on the same source kept it. An addon whose only
job is to carry a stringtable therefore packs to something that mounts and translates
nothing. Same silent shape as the scripts case: `Build Successful`, mod mounts, feature
absent.
- **Mixed — models + scripts** (vehicles, items): you still need binarize for the `.p3d`, so
  `-packonly` is wrong. Confirm AddonBuilder's include-list copies `*.c`/`*.h`, or the scripts
  vanish silently — a CarScript vehicle would then load but never simulate.

### `-include` is not the final PBO manifest (SP-177)

AddonBuilder has two input paths. Its native binarization/discovery path handles `config.cpp`,
`.p3d`, and face-referenced `.rvmat`; these can enter the PBO even when their suffix is absent
from `-include`. The ordinary sync path carries `.c`, `.paa`, `.ogg`, `.layout`, and `.csv`;
with a fresh temp, an omitted suffix is silently dropped. This scopes LL-213's "exclusive
filter" rule to the ordinary sync pass, not the final PBO contents.

Measured case: an `.rvmat` omitted from `include.lst` still entered and was binarized because
three `.p3d` files referenced it. This does not override the config-only-rvmat rule above:
an `.rvmat` referenced only by `config.cpp` may still be absent.

Do not add material suffixes to `include.lst` as a precaution and treat that as proof.
List, count, and name the built PBO entries. Compare ordinary payload against the source tree,
and check the complete config-referenced rvmat set separately. Presence in the list does not
prove that an entry was packed; absence from the list does not prove that a native input was
dropped.

Always verify after packing (cheap; catches it instantly):
```powershell
$txt = [System.IO.File]::ReadAllText($pbo, [System.Text.Encoding]::GetEncoding('ISO-8859-1'))
$txt.Contains('YourKnownClassName')   # must be True; also sanity-check the PBO byte size
```
Debugging heuristic — when "the mod loads but no script runs", grep the deployed PBO for a
known class string **before** chasing the script logic, the mission class, or server checks.

**Script-footprint caveat:** PBO byte shrink is NOT evidence of script-arena reduction. When the goal is script memory footprint, do not adjudicate capacity from source bytes, line counts, or PBO container size — the container size is a sanity/identity check, not a proxy for compiled memory. Measure control and candidate with DayZDiag under frozen stack/order/mission/config; report Game, World, Mission, and total separately, along with files/classes and hashes. Only the repeated engine delta sustains a causality or capacity claim.

### Post-build check — deployed-artifact reconciliation and exception-safe gates

- **A portable return is a deployment boundary (LL-293).** A source pack does not bring Steam `!Workshop` or `_server\profiles`. Before the first in-game test, inventory those external dependencies and profiles, extract a census of the deployed PBO entries, and compare each expected entry with the current compilable tree by content hash. Whole-PBO byte equality is not a substitute for per-entry comparison; rebuild and deploy on any unresolved divergence. Run source-sync steps only in a mode that cannot overwrite restored sources with stale assembly output (`oh1-build-deploy.ps1` without `-SkipSourceSync` overwrites MLOD with stale `assemble_out`; `powershell -File x.ps1 -Array a,b` passes one string — gate FAIL without deploy, use `&`).

### Content gate: derived manifest, extras check, and negative control (SP-171)

A content gate built on a hand-maintained closed file list goes stale in both directions
simultaneously: it names files that have since been deleted (killing the build at
startup) and omits files the PBO actually ships (a PASS then proves nothing about half
the payload). The correct construction:

- **Manifest = enumerate the source tree.** The expected file set is derived from what
  exists in the addon source directory at build time, not from a static list. A derived
  manifest cannot omit what is present.
- **Extras check on the PBO.** After packing, list the PBO entries and flag any file
  that is NOT in the derived manifest. This is what a closed list was actually buying:
  catching files that should not be there.
- **Exclude AddonBuilder-generated metadata from the extras check.** `$PBOPREFIX$.txt`
  and `texHeaders.bin` (the .paa index) are produced by AddonBuilder and have no source
  counterpart by design; they are expected in the PBO and must not trigger a flag.

**Negative control (mandatory).** A gate that only asserts presences cannot detect that
you failed to remove something you thought you removed. For every line or file the build
is supposed to have eliminated, the gate must assert that it is ABSENT from the PBO.
Presence-only checks pass even when stale content remains.

**Payload anchors go stale just like the manifest.** Before treating an absent anchor
(e.g. a `CreateAttachment("…")` call) as a regression you introduced: extract the
DEPLOYED PBO and check whether it contains the anchor. If it is absent from the deployed
PBO as well, the anchor is stale — there is no regression. Only an anchor present in the
deployed PBO but missing from your new build is a true regression.


### AddonBuilder non-determinism: byte identity is valid within a build, invalid between builds (SP-194)

Measured 2026-08-07 (SUB_BRZ s48, LFPowerGrid F4-S3): with the same source MLOD and the same
`-include`, two AddonBuilder runs produce different `.p3d` bytes. The payload (vertices, normals,
UVs, named selections, textures, material set) hashes identically; only the ORDER of `faces`,
`sections`, and the material array changes. Of 10 byte-different entries in the first measurement,
8 were pure reordering and 2 were the real change.

**Within a build**, byte identity is valid and must be enforced: the binarized temp output must be
byte-exact against the PBO entry (both come from the same run). This is the gate already used by
`forza_build_identity.py` (stage↔PBO) and GATE A of `pbo_verify_s48.py`; SP-194 does not
invalidate it.

**Between builds**, comparing bytes or sizes gives false positives. A "only X should have changed"
gate against the deployed PBO will flag ~8 of 11 untouched entries. The correct between-builds gate
is an **unordered multiset** per LOD keyed on `(material, texture, vertex-index, lit_bit)`,
constructed by walking `sections` and mapping each face to its material. Vertex indices are
comparable because vertex order IS stable (its hash matches across runs). Reference implementation:
`pbo_verify_s48.py` GATE C (`canonical()`); diagnostic triple: `s48_diag_delta.py` /
`_content.py` / `_canonical.py` (counts → payload → canonical).

**Mandatory self-check:** if the sections do not cover ALL faces of the LOD, the multiset is
incomplete and the gate must declare itself **VOID** rather than pass.

**Addendum (LFPowerGrid F4-S3):** the non-determinism is in the ODOL binarization of `.p3d` only.
`.c` script entries are byte-stable between builds (measured: 1 of 147 `.c` entries changed size,
and it was exactly the file that was edited; all 50 `.p3d` sources were byte-identical between the
two trees). Therefore **comparing script entries between two PBOs IS a valid change detector** —
the "do not compare bytes between builds" rule applies to `.p3d` only; applying it to scripts
discards the cheapest gate available.

**SHA-pinned artifacts are irrepeatable.** If a qualification is pinned to a PBO SHA, rebuilding
"to regenerate it" produces a different hash from an identical tree and breaks the pin silently.
In a project with release or audit anchored to a hash, "do not rebuild the PBO" is a hard
invariant: the file is a unique artifact and must be backed up by hash.

- **Every expected difference needs a pinned base (LL-326).** Audit gate code for `continue`, `pass`, `ok += 1` and allowlists. A file known to differ because a delta/merge is not yet promoted cannot receive an unconditional OK: store the `SHA-256` of the exact source base at derivation time in an `enforce-base.json`, mark the artifact `STALE` if that base moved, and force the merge to be rebuilt. Separately, a proximity check for words such as "retired" or "obsolete" answers an adjacent question; require the live identifier beside each retired reference.

### Two silent no-load causes to check BEFORE blaming the engine (SP-347)

Both produce the same symptom as the binarize/`.c` case above — the mod mounts, nothing
runs, the log is empty — and both are decidable offline in seconds. Check them before
spending an in-game session interpreting silence, and before concluding "this API does not
work" from a log line that was never going to exist.

**1. The script-module name selects the compile stage. A wrong name loads nothing.**
`CfgMods.<Mod>.defs` must map each source folder to its own stage: `3_Game` ->
`gameScriptModule`, `4_World` -> `worldScriptModule`, `5_Mission` -> `missionScriptModule`.
Declaring `4_World` files under `gameScriptModule` is accepted by the packer and produces no
warning, but the code never reaches the stage where its base classes exist. Measured
2026-08-24: a bench mod declared `files[]={"<Mod>/scripts/4_world"}` under `gameScriptModule`
and emitted nothing at all; two mods that load on the same machine (`DayZ_MCP/config.cpp`,
`A6_MK47/config.cpp`) both use `worldScriptModule` for `4_World`. The correct shape already
appears in `dayz-aviation/SKILL.md:363-389` and `dayz-vehicles/references/rip-import.md:522`;
what none of them state is the failure mode, which is silence rather than an error.

Match the **case** of the folder too, on disk and in `config.cpp`. Working mods ship
`4_World`/`5_Mission` capitalized; a lowercase tree packs lowercase paths into the PBO while
`config.cpp` asks for the capitalized ones, and Windows will not tell you.

```powershell
# Declared modules vs. what is actually on disk
$cfg = Get-Content "$mod\config.cpp" -Raw
[regex]::Matches($cfg,'class\s+(\w+ScriptModule)') | % { $_.Groups[1].Value }
[regex]::Matches($cfg,'"([^"]*scripts/[^"]+)"') | % {
  $p = Join-Path $mod ($_.Groups[1].Value -replace '^[^/]+/','' -replace '/','\')
  "{0} -> on disk: {1}" -f $_.Groups[1].Value, (Test-Path $p) }
```

**2. Every vanilla PBO ends in a 21-byte trailer; hand-rolled packers omit it.** The trailer
is one `0x00` separator followed by the SHA-1 of everything before it:

```
trailer == b"\x00" + sha1(data[:-21]).digest()
```

Measured 2026-08-24 on 6 vanilla PBOs (`ai`, `ai_bliss`, `animals`, `animals_bliss`,
`anims_anm_infected`, `anims_anm_player`), 6/6 match, 10 KB to 350 MB. AddonBuilder writes it;
a custom Python/Node packer usually does not, because a PBO without it still parses correctly
with any reader you write yourself — the omission is invisible to a round-trip test, which
compares the packer against its own output.

Whether the engine *rejects* a PBO lacking the trailer is **not established**, and in the
measured case it was not the cause. Write it anyway: it is an idempotent append that removes
the variable instead of leaving it to be investigated later under time pressure.

```python
data = open(pbo, "rb").read()
if not (len(data) > 21 and data[-21] == 0
        and hashlib.sha1(data[:-21]).digest() == data[-20:]):
    open(pbo, "ab").write(b"\x00" + hashlib.sha1(data).digest())
```

**Gate ordering.** A build step that reports success without checking `$LASTEXITCODE` after
each AddonBuilder invocation, and a deploy step that accepts a PBO on `Test-Path` alone, will
both hand you a stale artifact and call it fresh. Check the return code after *every*
invocation, and print a `SHA-256` build-id at pack time that a boot sentinel inside the mod
can be checked against — otherwise an old PBO is indistinguishable from a new one that does
nothing.

---

## Common Validation Failures & Fixes

Symptom -> cause -> fix catalog moved to `references/common-validation-failures.md` (fire-mode stub, unclosed brace, missing semicolon, texture-not-found, #STR_ key missing, ce_center, hiddenSelections count mismatch).

---

## Advanced: Scripting Validation

Enforce Script **supports** ternary (`x ? a : b`), `++`/`--`, and `foreach (Type t : collection)` —
they appear throughout vanilla, so a validator must NOT flag them. The one real array caveat:

```enforce_script
// Arrays: no '+=' concatenation operator. Add elements with Insert()/InsertAll():
selections.Insert("newSelection");    // append one
selections.InsertAll(otherArray);     // append many

// Supported and idiomatic (do NOT flag):
int x = condition ? 1 : 0;            // ternary
i++;  --i;                            // increment / decrement
foreach (string s : selections) { }   // foreach over a collection
```

For the authoritative Enforce Script rule set, see the `enforce-script-reference` skill.

---

## Offline script linter (pre-PBO)

**Blocking gate — run before packing, not after.**

```
python tools/dayz-script-validator/scripts/script_validator.py <addon_root>
```

Exit `0` PASS / `1` FAIL / `2` WARN. **Do not build a PBO on exit 1**: the errors it catches (`Unknown type`, local redeclaration, override of an absent method, `delete`, empty `#ifdef`, item declared under the wrong `CfgXxx`) only surface when the script module compiles at boot, so packing first turns a one-second check into a full in-game cycle. Add `ui_reconcile.py <addon_root>` when the mod ships UI.

Green here means the module should COMPILE and the asset should LOAD. It says nothing about engine behaviour — see `dayz-mod-workflow` §"Gates offline" for the full contract and the known coverage limits.

## Integration with CI/CD

For automated builds, run validation before packing. Note: the validators are
reference code blocks in `references/validation-scripts.md` — adapt them to your
pipeline; there is no bundled `validate.py`.

**Example build script (after extracting a validator from the reference):**
```batch
@echo off
echo Validating addon...
python config_cpp_validator.py "P:\MyMod\config.cpp"
if %ERRORLEVEL% NEQ 0 (
    echo Validation failed, skipping pack
    exit /b 1
)
echo Validation passed, packing...
AddonBuilder.exe P:\MyMod P:\Mods\@MyMod\Addons -prefix=MyMod -temp=P:\temp\MyMod -clear
```

The reference validators return exit code 0 on PASS, 1 on FAIL, 2 on WARN (configurable).

---

## Reference Scripts

See `references/validation-scripts.md` for standalone Python validators that can be integrated into build pipelines.

- `config_cpp_validator.py` – Parse and check config.cpp syntax
- `texture_path_checker.py` – Verify texture existence
- `stringtable_validator.py` – Check string key coverage. **Broken for DayZ**: it
  parses `stringtable.xml`. Do not run as-is; see `references/validation-scripts.md` section 3.
- `p3d_lod_checker.py` – Validate .p3d LOD structure

Each outputs machine-readable JSON for CI/CD integration.
---

## Build appendices (session findings)

Dated 2026-06-11 session appendices moved to `references/build-appendices.md`: post-build PBO verification checklist (size/content/name/staging) and the model-path resolution gate (validate what the engine RESOLVES in the deployed PBO).

## Reglas promovidas del corpus de lecciones (added 2026-07-27)

Promovidas desde `AI/20_Knowledge/lessons-learned.md` para que lleguen por trigger en vez
de depender de que alguien recuerde buscarlas. Cada regla cita su `LL-NNN` de origen;
la entrada completa (síntoma, origen, evidencia) vive allí. No quites la cita: el índice
`lessons-index.md` detecta la promoción buscando esa referencia dentro de las skills.

- **LL-084** — Ante `quoted string not closed`, EOF o una línea señalada en vanilla, trata archivo y línea como posible cascada del módulo y revisa antes BOM/truncación upstream. Haz diagnóstico y corrección byte-level desde el host autoritativo, no desde un mount stale.
- **LL-213** — Trata `-include` como filtro exclusivo y valida siempre desde un temp vacío. Separa el sync de `.p3d` del paso que los binariza a ODOL; falla si faltan entries o si el tamaño indica MLOD copiado as-is.
- **LL-290** — Un pin por sha256 o por tamaño se rompe solo al pasar por git: con `core.autocrlf=true` (el default en Windows) `git add` normaliza a LF y `git checkout` reescribe con CRLF, así que el blob y el working tree dejan de coincidir con lo pineado (medido: LICENSE 1577 B pineado contra 1548 B en el blob, y 8 rojos en un clon Windows). Corre el gate sobre el **clon recién checked-out**, no sobre una copia exportada con robocopy: la copia conserva los bytes originales y da verde sobre un árbol que nadie recibe. Y pon `.gitattributes` con `* text=auto eol=lf` desde el primer commit, más `-text` en lo que se compare byte a byte. Es el mismo eje que la sección de identidad de bytes de AddonBuilder más arriba: antes de comparar hashes, asegura que comparas el árbol que se publica.
- **LL-367** — Un artefacto de release se traza al commit por hash de TODO su árbol fuente, no de los ficheros tocados. Gate de procedencia pre-release: commit/fuente canónica ↔ árbol completo de build ↔ PBO. Un sync incremental «verificado» solo verifica su propio delta.

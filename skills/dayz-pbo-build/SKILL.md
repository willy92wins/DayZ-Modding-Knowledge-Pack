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

**A stringtable alone is not enough to test with.** Measured 2026-08-21 on a disposable
addon: its PBO mounted and served a `.layout` loaded by addon prefix, and a key defined by
that same PBO still printed as its own name. Adding `prefix`, `dependencies[]`, or the full
`CfgMods` shape of a shipping mod changed nothing, with a vanilla key resolving in the same
frame as the positive control and every PBO re-extracted to confirm the csv was inside it.
Keys from real mods do resolve, so this is a caveat about minimal test addons, not about
stringtables in general — but it means a two-file addon is the wrong thing to debug with.

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

The orchestrated build path (temp wipe + deploy + launch) lives in dayz-test-ingame's
`dayz-test.ps1` template.

**What AddonBuilder does:**
1. Reads $PBOPREFIX$ → creates output filename (mymod\myaddon.pbo)
2. Binarizes config.cpp (text → binary, ~90% smaller, faster load)
3. Optimizes .p3d files (binary format, LOD structure intact)
4. Packs all files into .pbo container
5. Generates PBO header with prefix

**Output:** `mymod\myaddon.pbo` ready to place in `@YourMod/addons/`

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

Always verify after packing (cheap; catches it instantly):
```powershell
$txt = [System.IO.File]::ReadAllText($pbo, [System.Text.Encoding]::GetEncoding('ISO-8859-1'))
$txt.Contains('YourKnownClassName')   # must be True; also sanity-check the PBO byte size
```
Debugging heuristic — when "the mod loads but no script runs", grep the deployed PBO for a
known class string **before** chasing the script logic, the mission class, or server checks.

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

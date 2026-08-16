# DayZ PBO Build Validation Skill - Complete Documentation

## Quick Start

1. **Read this first:** [SKILL.md](SKILL.md) - Main skill documentation
2. **Run validators:** See [references/validation-scripts.md](references/validation-scripts.md)
3. **Use checklist:** [VALIDATION_CHECKLIST.txt](VALIDATION_CHECKLIST.txt) - Before packing

## File Structure

```
dayz-pbo-build/
├── SKILL.md                           # Main skill documentation
├── references/
│   ├── validation-scripts.md          # Python validators with source code (1071 lines)
│   ├── common-validation-failures.md  # Symptom -> cause -> fix catalog (F3 extract)
│   └── build-appendices.md            # Dated 2026-06-11 session appendices (F3 extract)
├── README.txt                         # Quick overview
├── VALIDATION_CHECKLIST.txt          # Pre-build checklist
└── INDEX.md                          # This file
```

## What This Skill Does

Complete pre-build validation pipeline for DayZ mod addons. Validates everything that would otherwise fail in-game or during AddonBuilder packing.

### 7-Step Validation Pipeline

1. **Folder Structure** - config.cpp, $PBOPREFIX$, naming conventions, stale files
2. **config.cpp Syntax** - Braces, semicolons, CfgPatches structure, inheritance
3. **model.cfg** - Skeleton bones, named selections, animation references
4. **Textures/Materials** - All .paa and .rvmat files exist and are accessible
5. **.p3d LOD Structure** - LOD types, geometry mass, vertex budgets, named selections
6. **Stringtable** - All #STR_ keys present and accounted for
7. **Scripts** - Enforce Script syntax restrictions, #include paths

## Key Features

- **Catches errors BEFORE packing** - No more in-game surprises
- **7 comprehensive checks** - From folder structure to script syntax
- **JSON output** - Machine-readable for CI/CD integration
- **Production-ready Python** - 4 standalone validators
- **Exit codes** - 0=PASS, 1=FAIL, 2=WARN for automation
- **No external deps** - Uses only Python standard library (py3d optional)

## Using the Validators

The validators are reference code blocks embedded in
[references/validation-scripts.md](references/validation-scripts.md) — extract and
adapt them; there is no bundled `validate.py` or standalone `.py` files.

### Individual Validators (after extracting from the reference)

```bash
# Check config.cpp syntax
python config_cpp_validator.py /path/to/config.cpp

# Check all textures exist
python texture_path_checker.py /path/to/addon

# Check stringtable keys
python stringtable_validator.py /path/to/addon

# Check .p3d LOD structure (requires py3d)
python p3d_lod_checker.py /path/to/addon
```

### Batch Validation

See "Combined Validator Script" in [references/validation-scripts.md](references/validation-scripts.md) for running all validators in one go.

### Pre-Build Workflow

1. Use [VALIDATION_CHECKLIST.txt](VALIDATION_CHECKLIST.txt) for manual review
2. Run validators: `python config_cpp_validator.py .`
3. Fix any FAIL or WARN messages
4. Run AddonBuilder: `AddonBuilder.exe P:\<ModName> P:\Mods\@<ModName>\Addons -prefix=<ModName> -temp=P:\temp\<ModName> -clear`
5. Your .pbo is ready!

## Common Errors & Fixes

**"Unclosed brace in config.cpp"**
- Count all `{` and `}` pairs
- Use code editor with brace matching

**"Missing semicolon after property"**
- Every config.cpp property must end with `;`
- Exception: Opening `{` doesn't need semicolon

**"Texture not found"**
- Check path capitalization (case-sensitive!)
- Verify file actually exists relative to addon root

**"hiddenSelections count mismatch"**
- hiddenSelectionsTextures[] and hiddenSelectionsMaterials[] must EACH match hiddenSelections[] length (index-aligned)
- Each selection needs one texture AND one material

**"Missing ce_center in Memory LOD"**
- Add memory point `ce_center` to .p3d Memory LOD
- Required for physics to work in-game

## $PBOPREFIX$ Reference

**File:** Addon root (same location as config.cpp)
**Format:** Single line, e.g., `mymod\myaddon`
**Rules:**
- Use backslashes `\` (not forward slashes)
- No trailing backslash
- No quotes or spaces
- Unique across all addons

**Example folder:**
```
MyMod/
└── myaddon/
    ├── config.cpp
    ├── $PBOPREFIX$         (contains: mymod\myaddon)
    └── data/
        └── textures/
```

## AddonBuilder Integration

After validation passes, pack with AddonBuilder (canonical invocation — DAYZ_INFRA.md §Comandos de invocación canónicos):

```batch
AddonBuilder.exe P:\<ModName> P:\Mods\@<ModName>\Addons -prefix=<ModName> -temp=P:\temp\<ModName> [-clear]
```

Temp-stale trap: without `-clear` the `-temp` sync is incremental and can pack stale
source. If the PBO does not reflect your changes, wipe `P:\temp\<ModName>` first.
The orchestrated build path lives in dayz-test-ingame's `dayz-test.ps1` template.

This:
1. Reads $PBOPREFIX$ → filename
2. Binarizes config.cpp
3. Optimizes .p3d files
4. Creates mymod\myaddon.pbo
5. Place in @YourMod/addons/

## CI/CD Integration

Example GitHub Actions workflow:

```yaml
- name: Validate DayZ addon
  run: |
    python config_cpp_validator.py . || exit 1
    python texture_path_checker.py . || exit 1
    echo "Validation passed, ready for build"
```

Exit code handling:
- `0` = PASS, safe to proceed
- `1` = FAIL, block build
- `2` = WARN, allow with review

## Reference Scripts

All 4 validators are in [references/validation-scripts.md](references/validation-scripts.md):

1. **config_cpp_validator.py** (520 lines)
   - Brace/semicolon balance
   - CfgPatches validation
   - Class inheritance checking
   - hiddenSelections matching

2. **texture_path_checker.py** (400 lines)
   - Scans all .paa references
   - Checks file existence
   - Capitalization mismatch detection
   - Format warnings (.png, .dds)

3. **stringtable_validator.py** (350 lines)
   - Scans #STR_ references
   - Checks stringtable.xml entries
   - XML syntax validation
   - Orphaned key detection

4. **p3d_lod_checker.py** (400 lines)
   - Verifies LOD types (Resolution, Geometry, Memory)
   - Checks geometry mass > 0
   - Validates vertex budgets
   - Named selection consistency

## Status Codes

Each validator returns:
- **PASS** - All checks passed, safe to pack
- **WARN** - Issues found but not blockers (review recommended)
- **FAIL** - Critical errors found, DO NOT PACK

## Advanced: Scripting Notes

DayZ Enforce Script **supports** ternary (`x ? a : b`), `++`/`--`, and `foreach` — do NOT flag them.
The only array caveat: there is no `+=` concatenation; add elements with `.Insert()` / `.InsertAll()`.
See the `enforce-script-reference` skill for the authoritative rules.

## Support

For errors or questions:
1. Check [SKILL.md](SKILL.md) detailed explanations
2. Review validator source code in [references/validation-scripts.md](references/validation-scripts.md)
3. Use [VALIDATION_CHECKLIST.txt](VALIDATION_CHECKLIST.txt) for manual review

---

**Version:** 1.0 (2026-03-28)
**Status:** Production Ready
**License:** Use freely for DayZ mod development

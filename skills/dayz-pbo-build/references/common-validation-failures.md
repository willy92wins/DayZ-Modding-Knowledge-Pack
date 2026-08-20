# DayZ PBO — Common Validation Failures & Fixes

Extracted from dayz-pbo-build/SKILL.md 2026-07-07 (F3). Symptom -> cause -> fix catalog for pre-build validation failures. The core skill links here from its "Common Validation Failures" pointer.

---

## Common Validation Failures & Fixes

### FAIL: Custom weapon stuck in single-mode (only fires semi; fire-mode key does nothing; no mode name in HUD) — binarize stays silent
**Cause:** `class Mode_SemiAuto;` / `class Mode_FullAuto;` forward-declared INSIDE `class CfgWeapons` creates an empty stub at `CfgWeapons.Mode_FullAuto` that eclipses the real one (`Mode_FullAuto: Mode_SemiAuto` with `autoFire=1` at root scope, vanilla `bin.pbo` config.cpp:307/310). Subclasses inherit the stub without `autoFire` → engine discards the mode. A forward-decl is a valid external, so CfgConvert/binarize never warns and the de-rapped .bin looks perfect.
**Fix:** Move `class Mode_SemiAuto;` / `class Mode_FullAuto;` to ROOT scope (above `class CfgWeapons`, alongside `class OpticsInfoRifle;`). Verify with `bin.pbo` decompilation. A diagnostic clone `WeaponName_ModeTest: VanillaWeapon_Base` (pure inherit, no `Mode_*` refs) that cycles isolates the cause to your `Mode_*` reference. Origin: A6_SR2M bug#10 (2026-06-28, ~12 cycles). Cross-ref: LL-174, SP-031, `dayz-weapon-config-crossproject.md` INV-W1.

### FAIL: "Unclosed brace in config.cpp"
**Cause:** Missing closing `}` in a class definition
**Fix:** Count all `{` and `}` pairs, especially in large classes. Use a code editor with brace matching (Sublime, VS Code).

### FAIL: "Missing semicolon after property"
**Cause:** Forgot `;` at end of property or array
**Fix:** Every line in config.cpp must end with `;` (except opening `{`)
```cpp
class MyClass {
    displayName = "My Item";  // <-- MUST have semicolon
    scope = 2;
};
```

### FAIL: "Texture not found: data\textures\..."
**Cause:** Referenced texture doesn't exist or path is wrong
**Fix:** Check capitalization (DayZ is case-sensitive on servers). Ensure .paa file is in exact path.

### FAIL: "#STR_KEY missing from stringtable.csv"
**Cause:** Used `#STR_MYKEY` in code, config or a `.layout` but didn't add it to the
stringtable. The engine says nothing about this: the key prints its own name on screen and
logs zero RPT lines (measured 2026-08-20 over a 49,340-byte client log).
**Fix:** Add a row to `stringtable.csv` at the addon root. DayZ uses CSV, not the
`stringtable.xml` of Arma 3 — verified 2026-08-21 across this workspace: zero XML
stringtables, 38 CSV ones, and the deployed PBOs carry only CSV. The key goes in column 1
**without** the leading `#`:
```csv
"Language","original","english","spanish"
"STR_MYKEY","My Item Name","My Item Name","Mi objeto"
```

### WARN: "Missing ce_center in Memory LOD"
**Cause:** .p3d missing center-of-mass memory point
**Fix:** Add `ce_center` as a memory point in the Memory LOD (use Object Builder or py3d).

### FAIL: "hiddenSelections count mismatch"
**Cause:** `hiddenSelectionsTextures[]` or `hiddenSelectionsMaterials[]` length differs from `hiddenSelections[]`
**Fix:** Ensure each array aligns index-by-index with `hiddenSelections[]`:
```cpp
hiddenSelections[] = {"skin1", "skin2"};                      // 2 selections
hiddenSelectionsTextures[] = {"tex1.paa", "tex2.paa"};        // 2 textures (one per selection)
hiddenSelectionsMaterials[] = {"mat1.rvmat", "mat2.rvmat"};   // 2 materials (one per selection)
// Total items in hiddenSelections (2) must match texture count (2) AND material count (2)
```

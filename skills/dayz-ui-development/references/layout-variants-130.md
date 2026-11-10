# Layout variants on DayZ 1.30 — change a vanilla `.layout` without replacing it

Measured on DayZ 1.30.164200 (stable, DayZDiag), 2026-10-27 and 2026-11-05, and on 1.30.164289 with variants
written by hand, 2026-11-10 (their evidence is in each claim of `sources/claims.json`). Target:
`VANILLA/gui/layouts/day_z_ingamemenu.layout`, the Esc menu, created by
`VANILLA/scripts/5_mission/GUI/InGameMenu.c:38`. Evidence: `VAULT/reviews/2026-10-26-dayz-130-variants-and-fsshadowing.md`
(sections "Results (2026-10-27)", "Workbench-generated variants (2026-11-05)", "Probe 4 results (2026-11-05)")
and `VAULT/plans/2026-11-05-ui-variant-probe-4.md`.

Not to be confused with the TEST/debug *copy* of your own layout in `SKILL.md` ("Two layouts with same
names make the second UNREACHABLE"): that is a second file under your own path. A 1.30 layout variant is a
file at the **vanilla** path, in a PBO that shadows the vanilla prefix, which the engine applies on top of
the vanilla layout.

## 1. Generate it in Workbench

[EXACT][CLAIM-UI-VARIANT-WORKBENCH-FORMAT-130] Recipe that produced a working variant:

1. Make an authoring root folder holding a `mod.cpp`. Start Workbench **from its own folder** (so it finds
   `dayz.gproj`) with `-filePatching` and `-mod=<authoring root>`; the resource browser then lists the
   addon beside `DZ`.
2. In the resource browser, right-click the vanilla layout (`DZ/gui/layouts/<name>.layout`) and create a
   resource variant for the selected addon. The log reads `Creating new resource variant for selected addon`.
3. Pick the variant in the editor's "Resource Variants" picker, make the edits, save.

Workbench writes `gui/layouts/<name>.layout` **plus a `<name>.layout.meta`** into the addon (vanilla
layouts have no `.meta`). The file mirrors the whole vanilla tree in vanilla order: the root has no ID, and
every other widget is `Class "{id}" { Prefab "{id}" }`. Only edited widgets carry properties. A widget you
add gets its own 64-bit ID, a `Name` and **no** `Prefab`. Excerpt of the generated file (Licensing
container: `version` recoloured, `copyright` hidden, one widget added):

```
FrameWidgetClass {
 {
  WrapSpacerWidgetClass "{00000000564F35E9}" {
   Prefab "{00000000564F35E9}"
   {
    TextWidgetClass "{00000000308B9F61}" {
     Prefab "{00000000308B9F61}"
     color 1 0 0 1
     "text color" 0.629 0 0 1
    }
    TextWidgetClass "{00000000BB186E8D}" {
     Prefab "{00000000BB186E8D}"
     visible 0
    }
    TextWidgetClass "{6ACB5888C22B23AC}" {
     Name "eoc_probe4_added"
     color 1 0 0 1
     text "TEST"
     "text color" 0.629 0 0 1
    }
   }
  }
```

The vanilla widgets behind those IDs are `Licensing`, `version` and `copyright`
(`VANILLA/gui/layouts/day_z_ingamemenu.layout:8`, `:25`, `:42`).

[EXACT][CLAIM-UI-VARIANT-IDS-NAME-HASH-CHECK] **How the IDs are derived.** Computed offline on 2026-11-09
over the vanilla layouts of 1.29, 1.30.164014, 1.30.164200 and 1.30.164289. An ID is `00000000` followed by a
CRC-32 of the widget's `Name` and then each ancestor's `Name`, up to but not including the layout root, with
no separators: `version` inside `Licensing` hashes `versionLicensing` to `308B9F61`, and the root-level
`dayz_logo` (`:540`) hashes to `9FF48118`. A named root hashes its own name. The CRC is polynomial
`0x04C11DB7`, MSB first, in a shift register that is not augmented (the message bits enter at the low end and
no 32 zero bits follow), with init and final XOR `0xFFFFFFFF`; `zlib.crc32` and CRC-32/BZIP2 give other
values. The earlier check hashed the bare name, which is why CRC32, FNV-1, FNV-1a and Adler-32 all failed.

`day_z_ingamemenu.layout` stores no widget IDs (its `{16-hex}` prefixes are texture references,
`imageTexture "{GUID}Gui/textures/..."`), but 10 of the 227 vanilla layouts store one per widget, 1,438 in all
(`VANILLA/gui/layouts/day_z_hud.layout:295`), and 1,395 of them equal the derived ID. The other 43 are nine
64-bit IDs of widgets added after 1.29 (`debug/day_z_debug_monitor.layout`,
`script_console/script_console.layout`) and 34 in
`underground_trigger_editor/day_z_underground_trigger_editor.layout` from `:71`: nine match the chain without
`triggers_section`, and 25 lie between `CC000001` and `CC000020`. Two siblings with one name share an ID
(`xbox/day_z_ingamemenu_xbox.layout:232` and `:667`, both `CDEFDF47`).

Outside `script_console.layout` and the `debug/` layouts, no widget changed its ID from 1.29 to 1.30.164289;
six were added in `new_ui/options/msstore/game_tab.layout`. The 878 IDs that seven layouts gained in
1.30.164014, and `day_z_hud.layout` in 1.30.164200, are the ones derived from the previous build's names. A
derived ID changes with the name of the widget or of any ancestor below the root, as it did for nine widgets
of `debug/day_z_hud_debug.layout` that moved between 1.29 and 1.30.164014.

[INFERRED] Where the vanilla widget stores an ID, a variant needs that ID rather than the derived one, and
one variant entry cannot tell two same-named siblings apart.

[EXACT][CLAIM-UI-VARIANT-HAND-WRITTEN-130] **A variant written by hand with the derived IDs applies.** On
DayZDiag 1.30.164289 (2026-11-10), a hand-written `day_z_ingamemenu.layout` in the format above, the whole
vanilla tree mirrored with derived IDs, packed with MakePbo (§3) and **without a `.meta`**, recoloured
`version`, hid `copyright`, `dayz_logo` and `vignette`, and added a widget inside `Licensing`:
`copyright_vis=0 version_color=-65536 licensing_children=3 logo_vis=0 vignette_vis=0 added_probe4=1@Licensing`.
The client log names the layout `{8648FA7C9D16ED7D}gui/layouts/day_z_ingamemenu.layout`, the GUID that
Workbench writes into the `.meta`, although the PBO had none. The IDs of any layout:
`tools/dayz-ui-lab/dayz_ui_lab/widget_ids.py` (`TOOLS.md`).

## 2. What a variant does in game

[EXACT][CLAIM-UI-VARIANT-PREFAB-MERGE-130] A variant generated as above **hides** (`visible 0`),
**modifies** (colour) and **adds** widgets of the vanilla layout **in place**, at the root and inside nested
containers, with no duplicates. Matching is by the `Prefab` ID, not by name. Vanilla script finds an added
widget with `FindAnyWidget`. Probe readout, from a `modded class InGameMenu` after vanilla `Init`:
`copyright_count=1 copyright_vis=0 licensing_count=1 logo_count=1 logo_vis=0 version_color=-65536 added_parent=Licensing`
(`dayz_logo`, `day_z_ingamemenu.layout:540`, is the root-level hide).

[EXACT][CLAIM-UI-VARIANT-NAME-KEYED-ADD-ONLY-130] **Hand-written, name-keyed files only add.** A full copy
of the vanilla layout with one changed text drew every widget twice; a delta file holding the root,
`Licensing` and a re-texted `copyright` left vanilla's `copyright` untouched and added a second one; a nested
container keyed by name (`Licensing`) became a second container, not a merge. Top-level widgets of such a
file do become children of the vanilla root and are reachable by the menu's own `FindAnyWidget`. The older
conclusion "variants can only add widgets" holds **only** for these files; for Workbench-generated files it is
superseded by the claim above.

[EXACT][CLAIM-UI-VARIANT-STALE-PREFAB-130] **An entry whose ID no widget has is dropped, with a warning.** On
1.30.164289 the entry `TextWidgetClass "{00000000DEADBEEF}" { Prefab "{00000000DEADBEEF}" Name "eoc_l5_stale" }`
inside `Licensing` added nothing (`licensing_children=3`, no `eoc_l5_stale`) and the rest of the variant
applied. The client log has `GUI (W): Overridden prefab member 'eoc_l5_stale' (GUID: '{DEADBEEF}' type:
TextWidgetClass) no longer exists in prefab`. After a DayZ update that renames or moves a widget, edits to it
stop applying with only that warning: recompute the IDs and diff.

[EXACT][CLAIM-UI-VARIANT-TWO-MODS-130] **Two mods varying one layout both apply.** On 1.30.164289, mod A
(`version` red, `copyright` hidden, one widget added) and mod B (`version` green, another widget added), each
with its own variant of `day_z_ingamemenu.layout`, loaded together in both orders: both added widgets sat in
`Licensing` (`licensing_children=4`) and `copyright` stayed hidden, while `version` took the colour of the mod
later in `-mod=` (A then B: `-16711936`, green; B then A: `-65536`, red). B's PBO also held a name-keyed
`day_z_hud.layout`, whose widget joined the HUD root in both orders: two `gui`-prefix shadow PBOs with
different files load together, and the vanilla `gui` files that neither PBO holds still load.

## 3. Packing

[EXACT][CLAIM-UI-VARIANT-GUI-PREFIX-PACKING-130] What worked: the variant's `gui/` folder packed as its own
PBO with prefix `gui` and the 1.30 header property `fsShadowing=1` (RaG PBO Builder `--fs-shadowing`; header
read back from the packed bytes), the `.meta` packed alongside the `.layout`, a `config.cpp` present, the
PBO unsigned, loaded on DayZDiag from a mod folder holding only the probe. Header and builder flags:
`skills/dayz-pbo-build/references/dayz-1-30-pbo-build.md` §"`fsShadowing`".

[EXACT][CLAIM-UI-VARIANT-MAKEPBO-PACKING-130] MakePbo works too (1.30.164289, 2026-11-10): the same `gui/`
folder, with `prefix=gui` and `fsShadowing=1` as two lines of `$PBOPREFIX$.txt`, packed by MakePbo 2.16
with `config.cpp` compiled to `config.bin`, **no `.meta`**, unsigned; the variants of §1 and §2 applied. The
variant's own `CfgPatches` class was not in the game config: `ConfigIsExisting` returned 0 for it, and 1 for
the probe mod's. Packing with a `config.cpp` is verified with RaG and MakePbo; without one, see §4.

## 4. Unknowns — do not promise these

- **A `gui`-prefix PBO without `config.cpp`.** claim: CLAIM-UI-VARIANT-NO-CONFIG-REPORT A community author
  reports packing each variant folder without one, through an `OVERRIDE` marker file in their own tool, and
  says pboProject refuses such folders. A report, not verified here.
- **Per-screen toggling.** No mechanism known: as measured, a loaded variant is always applied. Put
  conditional behaviour in script, not in the variant.
- **Variants of other resource types.** Not measured: only layout variants have been made and loaded.

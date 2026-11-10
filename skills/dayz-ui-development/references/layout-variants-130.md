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
The client log, in the lines of the warning of §2, names the layout
`{8648FA7C9D16ED7D}gui/layouts/day_z_ingamemenu.layout`, the GUID that Workbench writes into the `.meta`,
although the PBO had none. The IDs of any layout:
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
the probe mod's.

[EXACT][CLAIM-UI-VARIANT-NO-CONFIG-130] **`config.cpp` is not needed.** On 1.30.164289 (2026-11-10), a PBO
holding only `layouts/day_z_ingamemenu.layout`, a variant that hides `dayz_logo` and adds a widget inside
`Licensing`, with no `config.cpp`, no `.meta` and no signature, packed by FileBank with the header
`prefix=gui`, `fsShadowing=1`, loaded from its own mod folder and its variant applied:
`logo_vis=0 added_noconfig=1@Licensing licensing_children=3`. How to pack it:
`skills/dayz-pbo-build/references/dayz-1-30-pbo-build.md` §"`fsShadowing`".

claim: CLAIM-UI-VARIANT-NO-CONFIG-REPORT A community author reports packing each variant folder without
`config.cpp`, through an `OVERRIDE` marker file in their own tool, and says pboProject refuses such folders.
The measurement above agrees with the first part; the pboProject refusal is not verified here.

## 4. One screen only: inherit the vanilla layout in a layout of your own

[EXACT][CLAIM-UI-VARIANT-INHERIT-GUID-130] **A layout at your own path that inherits the vanilla layout by
its GUID gives the vanilla tree with your edits, and the vanilla layout stays as it was.** On DayZDiag
1.30.164289 (2026-11-10), a file in the mod's own folder whose root line is
`FrameWidgetClass : "{8648FA7C9D16ED7D}gui/layouts/day_z_ingamemenu.layout" {` and whose body is a variant in
the format of §1 (`dayz_logo` hidden, a widget `l5p3_added` added inside `Licensing`), created by script with
`CreateWidgets` on its own path, gave the whole vanilla tree with both edits:
`children=8 licensing_children=3 logo_vis=0 added_p3=1@Licensing`, where the vanilla path gives
`children=8 licensing_children=2 logo_vis=1`. The Esc menu, which creates the vanilla path, did not get those
edits: `logo_vis=1 added_p3=0` in the same runs, and `added_p3=0` in a run where it opened after that layout
had been created.

What did not work, in the same runs:

- The same root with the path and no GUID, `FrameWidgetClass : "gui/layouts/day_z_ingamemenu.layout" {`,
  gave what the body gives with no base: a root with no name and no children (`children=0`), and one
  `GUI (W): Overridden prefab member (GUID: '{…}' type: …) no longer exists in prefab` per entry of the body.
- `CreateWidgets("{8648FA7C9D16ED7D}gui/layouts/day_z_ingamemenu.layout")` returned null, with
  `SCRIPT (E): Cannot open layout '{8648FA7C9D16ED7D}gui/layouts/day_z_ingamemenu.layout'` and
  `Cannot load layout` for the same name. The GUID form names a base inside a layout; script does not open it.

[EXACT][CLAIM-UI-LAYOUT-GUID-CRC64-130] **A layout's GUID is a CRC-64 of its path, with or without a
`.meta`.** The client log of 1.30.164289 names layouts with their GUID in `GUI : Layout load @"{GUID}path"`
lines, also layouts packed without a `.meta`: `{D28473AC9D1FDDED}L5Probe3/gui/l5p3_noinherit.layout`,
`{BF87DB555BA864F7}L5Probe3/gui/l5p3_inherit_path.layout`,
`{D87638C86BF5A92A}DayZ_MCP/gui/layouts/mcp_dialog.layout`, and the Esc menu's
`{8648FA7C9D16ED7D}gui/layouts/day_z_ingamemenu.layout` (§1). Computed offline on 2026-11-10, each of the four
is the CRC-64/WE of the path in upper case with forward slashes (`GUI/LAYOUTS/DAY_Z_INGAMEMENU.LAYOUT` gives
`8648FA7C9D16ED7D`): polynomial `0x42F0E1EBA9EA3693`, MSB first, no reflection, init and final XOR
`0xFFFFFFFFFFFFFFFF` (check value of `123456789`: `62EC59E3F1A4F00A`), written as 16 upper-case hex digits.

[EXACT][CLAIM-UI-VARIANT-INHERIT-STACKS-130] **With a variant of the same layout loaded, the inherited base is
the varied layout.** With the PBO of `CLAIM-UI-VARIANT-NO-CONFIG-130` loaded, the layout above gave both its
own edits and the variant's: `licensing_children=4 logo_vis=0 added_variant=1@Licensing added_p3=1@Licensing`.
A variant at the vanilla path applies to every creation of that path, script included:
`CreateWidgets("gui/layouts/day_z_ingamemenu.layout")` gave `logo_vis=0 added_variant=1@Licensing`.

[INFERRED] To change one screen only, have that screen's script create a layout of your own that inherits
the vanilla one, and ship no variant at the vanilla path: a variant there reaches every screen that uses the
layout. The GUID of another vanilla layout is the same CRC of its path; only the Esc menu's has been used as
a base in game.

## 5. Shadows of an imageset or of the styles replace the whole file

[EXACT][CLAIM-UI-SHADOW-IMAGESET-REPLACES-130] **An imageset in a `gui` shadow PBO replaces the vanilla
imageset; it does not merge with it.** On DayZDiag 1.30.164289 (2026-11-10), a PBO with `prefix=gui` and
`fsShadowing=1`, packed like the one of `CLAIM-UI-VARIANT-NO-CONFIG-130`, held only
`imagesets/BleedingDrops.imageset`: the vanilla file cut to two images, `Bleeding2` resized from 128 x 128 to
100 x 100 and a new `l5p3_added` of 64 x 64. `ImageWidget.LoadImageFile(i, "set:BleedingDrops image:<name>")`
and `GetImageSize` gave `Bleeding2` 100 x 100 and `l5p3_added` 64 x 64, and `Bleeding1` failed. Without the PBO,
`Bleeding1` and `Bleeding2` gave 128 x 128 and `l5p3_added` failed. The images the file did not repeat were
gone for the game too: the log has
`GUI (E): ImageWidget::LoadImageFile can't set image 'set:BleedingDrops image:Bleeding3'` and the same line
for `Bleeding4` to `Bleeding16`, images the probe never loaded.

[EXACT][CLAIM-UI-SHADOW-STYLES-REPLACES-130] **The widget styles behave the same.** A PBO of the same kind
held only `looknfeel/dayzwidgets.styles`, with one `<Widget Name="TextWidget">` section of two styles:
`Normal` moved from `gui/fonts/MetronBook` to `gui/fonts/MetronLight`, and a new `L5Style` on
`gui/fonts/MetronLight`. `TextWidget.GetTextSize` gave the width of one 40-character text under four `style`
values. Without the PBO the widths were `Normal 680`, `Bold 690`, `Light 670` and `L5Style 680`; with it, all
four were `670`. So the file is read (`L5Style` draws like vanilla `Light`, which is on `MetronLight`),
`Normal` is replaced by name, and `Bold`, which the file does not repeat, draws like the new `Normal`. A style
name that does not exist draws like `Normal` too (`L5Style` without the PBO). No error line of that run names
`dayzwidgets`.

[INFERRED] A shadow of an imageset or of `dayzwidgets.styles` has to hold the whole vanilla file with your
changes, and it changes those images or styles on every screen. A full copy was not loaded in game.

## 6. Unknowns — do not promise these

- **Resource variants made in Workbench for other types.** The shadows of §5 were plain files. Whether a
  Workbench resource variant of an `.imageset` or of the styles merges like a layout variant is not measured.
- **A layout inherited by a widget inside another layout** (`Class "{id}" : "{GUID}path"` on a child) is not
  measured.

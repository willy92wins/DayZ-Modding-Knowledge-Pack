# DayZ UI — Plan → Implementation Fidelity Playbook

Added 2026-07-03. This file exists because of ONE recurring failure: **the UI never comes out
like it was planned.** It answers *why* that happens in DayZ/Enfusion specifically, and gives a
concrete author → preview → build → verify loop plus a plan/spec artifact and a parity gate.

Evidence discipline: every non-obvious claim carries a re-verifiable citation — a local
`path:line` under `<dayz-projects>\` (vanilla `scripts/`,
unpacked `gui/`) or an AnswerOverflow URL. If a citation is missing, treat the line as a hint.

---

## 0. TL;DR — the five moves that close most of the gap

1. **Author in proportional units (flags = 0) by default**, exact pixels (= 1) only for things that
   must be pixel-true. All-exact layouts look right at 1080p and wrong everywhere else (§1.1, §2).
2. **If you use the Workbench Layout Editor, register your imagesets/styles TWICE** — in
   `dayz.gproj` (so the editor previews them) AND in `config.cpp class defs` (so the game loads
   them). Missing either side is a direct mockup-vs-game divergence (§3).
3. **Keep the design mockup INSIDE the widget model.** No gradients, border-radius, web fonts,
   scanlines, CSS-only effects — none have a `.layout` equivalent, so a mockup that uses them is
   unimplementable as drawn and guarantees divergence (§1.6, §5).
4. **Run the offline gate before every in-game test**: linter → name/#STR reconciliation →
   approximate render. Cheap; catches the crashes and the "half my UI vanished" cases (§4, §6).
5. **Verify implemented-against-plan, not just syntax.** Every planned widget must exist with the
   planned name/mode; every `Binding_Name` must match a controller property; screenshot at the
   target resolution and diff against the calibrated mockup (§6).

---

## 1. WHY implemented UI diverges from the plan — the root-cause catalog

Six independent mechanisms. Each is a real, verified reason the in-game result differs from what
was drawn or specified. Knowing which one bit you is half the fix.

### 1.1 Exact flags mean PHYSICAL PIXELS, not "defined position"
`hexactpos/vexactpos/hexactsize/vexactsize 1` switches that axis to **physical screen resolution**
units, so a layout authored at 1920×1080 occupies a different fraction of the screen at 2560×1440,
ultrawide, or console.
- Evidence: `scripts/1_core/proto/enwidgets.c:68-71` — `EXACTPOS //< Uses physical resolution
  (g_iWidth, h_iHeight)`, `HEXACTSIZE //< Uses physical resolution (g_iWidth)`.
- `0` = **fraction of parent (0.0–1.0)**. Vanilla predominantly uses proportional: over
  `gui/layouts`, `hexactsize 0` appears 5851× vs `hexactsize 1` 2727×.
- Community corroboration: "It will only work on 1 resolution and 1 aspect ratio" —
  https://www.answeroverflow.com/m/535469900702154753
- **This is the single most common cause of "looked right in my mockup, wrong in-game."**

### 1.2 Colors are re-lit by the engine (global LV), and a script `SetColor` can override the layout
Two things move color away from what you authored:
- Global LV darkening — which is the PLAYER's HUD brightness, not an engine constant. There is
  no fix to apply: `SetLV`/`SetTextLV` are `proto static` (`enwidgets.c:114-117`) and vanilla
  drives them from `EDayZProfilesOptions.HUD_BRIGHTNESS` (`dayzgame.c:3778-3787`), so calling
  them from a mod overwrites the player's choice. Author honest ARGB, verify at a dimmed HUD,
  and do NOT pre-boost values either.
- Most mods set final colors in **script** via `SetColor(ARGB)` AFTER `CreateWidgets`, not in the
  `.layout`. So a static preview of the `.layout` alone cannot know the real colors — the plan
  must record intended colors separately, and the renderer's colors are best-effort only.
- `ImageWidget.SetColor()` **modulates/tints** the texture (multiplies), it does not repaint pixels
  — an already-colored image gets desaturated, not recolored. Author recolorable art white/greyscale
  and tint via `SetColor`. (community: https://www.answeroverflow.com/m/1379476089000300725)

### 1.3 3D-object brightness inside widgets is a separate knob
Item/player previews render dark unless you touch `Widget.SetObjectLighting(float [0,1], default 1)`
(`enwidgets.c:118-119`) — distinct from `SetLV`. If a planned inventory/preview panel "looks murky"
in-game but fine in the mockup, this is why.

### 1.4 Script-driven spacers overwrite authored child geometry at runtime
Any widget carrying a spacer `scriptclass` (e.g. `AutoHeightSpacer`, the vanilla spacer handlers)
force `EXACTPOS|EXACTSIZE` onto every child at init and on `OnChildAdd`, then reposition children in
screen pixels — so proportional pos/size you authored on those children is **silently discarded**
in-game while the editor preview still shows the authored values.
- Evidence: `scripts/3_game/gui/spacers/spacerbase.c:13-19,32-37`
  (`child.SetFlags(WidgetFlags.EXACTPOS | WidgetFlags.EXACTSIZE, false)` inside
  `OnWidgetScriptInit`/`OnChildAdd`).

### 1.5 Workbench editor preview ≠ game unless assets are registered on BOTH sides
Custom imagesets and `.styles` render in the Workbench **Layout Editor** only if listed in
`dayz.gproj`; the **game** only loads them if listed in `config.cpp class defs`. Register one side
and not the other and the mockup and the build disagree by construction. Full mechanism in §3.

### 1.6 The design mockup uses features with no `.layout` equivalent
When the "plan" is a freeform HTML/CSS mockup (Google-Fonts web font, radial-gradient, scanlines,
border-radius), none of those map to a widget attribute, so the implementation *cannot* match by
definition and the gap is judged by eye between two hand-made artifacts.
- Evidence (this project's own history): `LFGungame_dev\_review_flags\ui-mockup\lfgg-mockup.html`
  (CDN font + gradients) vs `lfgg-impl-mockup.html` ("posiciones y colores tomados de los `.layout`
  reales … No es el píxel exacto del engine").
- **Rule:** the design mockup must stay inside the widget model — every visual element maps to a
  widget class + a verified attribute, or it doesn't go in the plan.

### 1.7 Bonus divergence sources worth a glance
- `text_proportion` (text size as a fraction of widget height) drives most vanilla text scaling; an
  arbitrary mockup `font-size` px does not represent it — calibrate the mockup or label it
  "approximation" (see SKILL.md MOCKUP FIDELITY / LL-086).
- `UIManager.IsScaledMode()/SetScaledMode(bool)` is an engine-level UI scale toggle
  (`scripts/3_game/tools/uimanager.c:55-56`) — check it when "same layout, different size on a
  player's machine" before touching the layout.
- `EditBoxWidget` cannot center its text (no alignment API; `enwidgets.c:347-351`) — plan single-line
  inputs left-aligned or fake it with a `TextWidget` overlay.

---

## 2. Authoring resolution-independent layouts (the fix for §1.1)

- **Default to proportional (flags 0).** Position/size are then fractions of the parent, so the UI
  scales with resolution and aspect. Use `halign`/`valign` `*_ref` anchors to pin to an edge/center
  of the parent (`valign` 4518× + `halign` 4157× in the corpus — heavily used, not "rare").
- **Reach for exact (flags 1) only** for elements that must keep a pixel size (icon tiles, 1px
  borders, fixed-size buttons). Mixing pixel-pos + proportional-size on the SAME widget is fragile
  under resize — keep a widget all-exact or all-proportional.
- **Canonical resolution-independent full-screen 16:9 background:**
  ```
  ImageWidgetClass Background {
      size 0.16 0.09                 // 16% × 9%  (NOT 1.0 1.0)
      hexactpos 0 vexactpos 0 hexactsize 0 vexactsize 0
      halign center_ref
      valign center_ref
      fixaspect outside              // vanilla values seen: fixwidth (most common), inside, outside, none
      "stretch mode" stretch_w_h
      image0 "MyMod/gui/textures/bg_co.edds"   // 16:9 source, 2048×1024 recommended for large monitors
      { }
  }
  ```
  Evidence: `gui/layouts/loading.layout:36-55`; community consensus
  https://www.answeroverflow.com/m/1241899536742617208 and
  https://www.answeroverflow.com/m/1474596453661016238
- **Console/TV:** the `keepsafezone` attribute (163× in corpus) respects TV-safe margins. Gamepad/
  keyboard focus = the global `SetFocus(Widget)/GetFocus()` pair — *(corrected 2026-07-04:
  `SetActiveWindow` has ZERO vanilla call sites; do not design around it)*. Vanilla conventions:
  console menus `SetFocus(defaultButton)` in Init, hover and focus share one highlight path
  (OnMouseEnter/OnFocus → same ColorHighlight), device hot-swap via
  `GetOnInputDeviceChanged().Insert(fn)` + Remove in destructor. Full model:
  `vanilla-menus-map.md §7`.

---

## 3. The Workbench Layout Editor (the WYSIWYG tool) + dual registration

**Yes, DayZ Tools Workbench includes a WYSIWYG Layout Editor for `.layout` files** (the early
Enfusion editor; same workflow Arma Reforger documents as "Layout Creation" — create the
`UI/layouts` tree, right-click → new `.layout`, double-click to open in the Layout Editor). It is the
most direct way to make the plan and the implementation the same artifact instead of two.

Reality check: it exists, but it is not a silver bullet — modern DayZ-specific tutorials still
hand-author `.layout` files (e.g. the stardz DayZ Modding Wiki HUD chapter writes the widget tree by
hand). Use the editor for visual positioning/preview; keep the brace-format file as source of truth.

**The double-registration rule (verified mechanism of editor-vs-game divergence):**
- For the **Layout Editor to preview** your custom imagesets / `.styles`, register them in
  **`dayz.gproj`** (`GameProjectClass` `imageSets{}` / `widgetStyles{}` blocks), then restart
  Workbench. **Community-standard practice (2026-07-05): keep a PER-MOD dayz.gproj instead of
  hand-editing the global one next to `workbenchApp.exe`** — canonical copyable example: COT ships
  `JM/COT/Workbench/dayz.gproj` (complete GameProjectClass with `FileSystemPathClass Name "Game
  Root" Directory "P:"` + imageSets/widgetStyles/ScriptModules blocks); joetex's
  DayZ-BoutDangTimeTools generates the gproj from a template and copies it to the Workbench folder,
  after which Workbench auto-loads the mod's `.c`, `.layout` and `.styles` files.
  - Evidence: WoozyMasta "To make Workbench display new custom imagesets (in layout), add them to the
    dayz.gproj file next to workbenchApp.exe" https://www.answeroverflow.com/m/1467071719020953682 ;
    BRITTO (styles, both sides) https://www.answeroverflow.com/m/869608103442780342
- For the **game to load** the same assets, register them in **`config.cpp`**:
  ```cpp
  class CfgPatches { /* ... */ };
  class defs {
      class imageSets    { files[] = { "MyMod/gui/imagesets/my_set.imageset" }; };
      class widgetStyles { files[] = { "MyMod/gui/styles/my.styles" }; };
  };
  ```
- Missing `dayz.gproj` side → images/styles blank in the editor mockup. Missing `config.cpp` side →
  blank in-game. Keep both in sync or the plan and the build disagree.
- Workbench launch recipe (community-current): run `workbenchApp.exe` with cwd = DayZ install,
  `-mod=<relative;prefixes;to;each;mod>` (semicolon-separated, each pointing at the folder with the
  `CfgMods` config.cpp), `-newErrorsAreWarnings=1`, `-profiles=...`; kill any running instance first.
  https://www.answeroverflow.com/m/1516861595706327092
- Editor quirk: a `MapWidget` cannot be resized directly — change its type to another class, resize,
  switch back. https://www.answeroverflow.com/m/1506791557657788486

---

## 4. The offline → in-game iteration loop (what already exists in THIS environment)

The skill previously documented WHAT to write but never HOW to see it fast. Here is the loop
assembled from tools that already exist on this machine.

### 4.1 Iteration mechanics (verified)
- Client + server as `DayZDiag_x64.exe` + `-filePatching` + `serverDZ.cfg allowFilePatching=1` lets
  you edit raw `.c` without a PBO rebuild, and skips BattlEye + `.bisign` signing (harness mods are
  cheap to deploy). Source: `LF_RollingStone_dev\research\...\08-workbench-diagnostico.md:330,372` +
  `DAYZ_INFRA.md:38-64`.
- **There is NO script hot-reload**: a mission restart is required to pick up `.c` changes, and
  `config.cpp` changes always require a full PBO rebuild. `-clear` on AddonBuilder avoids stale
  `-temp` (see `DAYZ_INFRA.md`).
- **OPEN EXPERIMENT (highest-leverage unknown, ~5 min to settle):** does a raw `.layout` under
  filePatching get re-read from disk when a menu is closed and reopened (since `CreateWidgets` runs
  per-open)? If yes, UI iteration collapses from rebuild+reconnect (~3-10 min) to edit-file +
  reopen-menu (~seconds), no restart. No repo doc answers this — run it and record the result here.
  **Partial answer for Dabs UIs (2026-07-05): Dabs ships layout hot-reload under DIAG** —
  `static ScriptView.ReloadAll()` (`MVC/ScriptView.c:126-134`, `#ifdef DIAG_DEVELOPER`, comment
  literally "Hot reload all widgets layouts") Unlinks + rebuilds every live ScriptView's layout.
  Wire it to a keybind/DbgUI button under DayZDiag and Dabs-based UI gets edit→see in seconds; it
  also proves the engine re-reads the layout file on a fresh CreateWidgets call in a live session.

### 4.2 Tools on disk (use these; the skill never mentioned most of them)
- **Pre-PBO linter** — `tools/dayz-script-validator/scripts/script_validator.py <addon_root>` (JSON
  to stdout; exit 0 PASS / 1 FAIL / 2 WARN). Five UI detectors: layout leaf-brace, XML-format layout
  (crashes `CreateWidgets`), layout-file-missing (referenced from `.c` but absent → un-guardable CTD),
  `$PBOPREFIX$` path mismatch (→ crash + ghost menu), 3-param `OnMouseLeave` (compiles, never fires).
  Smoke on LFPG: 28 true positives, 0% FP. **Make this step 1 of the delivery checklist.**
- **Offline `.layout`→HTML renderer (v1)** — `<notes>\DayZ_UI_Research\renderer\dayz_layout_render.py <in.layout> [out.html]`. **Use ONLY as a labelled
  approximation** — its own bug ledger lists 15+ fidelity bugs: `visible 0` ignored, `text_proportion`
  never modelled (all text ~14px), `halign right_ref/bottom_ref` sign inverted, script-side centering
  not emulated, GridSpacer/WrapSpacer/Scroll layout not implemented, only the first root parsed,
  companion-`.c` color/text extraction by fragile regex that emits plausible-but-wrong output with no
  warning. Good for gross layout/text sanity; never trust its pixels or colors.
- **Renderer v2 (BUILT 2026-07-03) — the faithful offline previewer** —
  `python DayZ_UI_Research\renderer\build_viewer.py <in.layout> [-o out.preview.html] [--layout-root DIR]`.
  Uses the tested `parse.py` (tokenizer + parser + geometry resolver) and bundles the resolved geometry
  at 4 resolutions (1080p / 1440p / ultrawide 21:9 / 720p) into ONE self-contained `*.preview.html` that
  opens in any browser with no server. Improvements over v1 that matter for fidelity: **respects
  `visible 0`** (v1 rendered hidden widgets), **models `text_proportion`** (font-size = proportion ×
  widget-height; v1 pinned all text ~14px), renders ALL roots (v1 only the first), surfaces parser
  diagnostics (missing-child-block etc.), badges anchors the resolver marks `assumed` (center/right/
  bottom_ref phase-1), badges spacer containers (children auto-laid-out in-game), shows MVC
  `Binding_Name`/`Relay_Command`, and — the money feature — the **resolution switcher makes the
  exact-flag divergence VISIBLE**: exact-pixel widgets keep their px while proportional widgets scale, so
  you SEE which parts of the layout break off-1080p before ever launching the game. Still an
  approximation (real Metron fonts, PAA/EDDS textures shown hatched, and script-side `SetColor`/`SetPos`
  are NOT emulated — trust in-game for pixels/colors/fonts). Self-tested headless 2026-07-03 on
  `loading.layout` (vanilla, 25 widgets), `day_z_hud.layout` (292 widgets) and `LFPG_SorterTag.layout`
  (0 pageerrors, all toggles + resolution switch verified). Sample outputs shipped next to the tool
  (`loading.preview.html`, `LFPG_SorterTag.preview.html`).
- **In-game harnesses (keybind-toggled test menus):**
  - `LF_ColorTest` — F7 (scancode 65) panel of 10 known-ARGB swatches + SetLV(0) A/B protocol; a
    signed PBO exists in-tree → redeployable without rebuild.
  - `LFPG_UITest` — P key (scancode 25) panel: RichText markup, VideoWidget, widget-creation perf
    (300/500 items + live FPS). Header comment says "type uitest in chat" but the real opener is P.
  - `LF_UILab` — grave/º key (scancode 41) Dabs-MVC test-lab with TestRunner/TestCase, PASS/FAIL
    `[UILab]`-prefixed RPT lines, ExportToLog cheat-sheet. **~90% unbuilt** (only the V00 self-test is
    registered) and its `config.cpp` still carries error E01 (`requiredAddons[] { "DabsFramework" }` —
    must be `"DF_Scripts"`/`"DF_GUI"`). Fix E01 before reusing; then it is the ready scaffold for a
    keybind-toggled UI harness.
- **`DbgUI` (vanilla immediate-mode debug UI) — instant live tuning, no rebuild.** `scripts/1_core/
  proto/dbgui.c:59-126` exposes `SliderFloat/InputFloat/Button/Combo/Check/PlotLive/Begin/End` +
  `FloatOverride`. Call per-frame from `OnUpdate`; a DbgUI slider panel driving `SetPos/SetColor/
  SetTextExactSize` on a live menu gives real-time UI tweaking, then bake the final numbers into the
  `.layout`. (DiagMenu proper needs DayZDiag + WIN+ALT; DbgUI itself compiles in retail.)
- **Cheap post-test gate:** grep the RPT for `Cannot open layout <path>` — present when a layout fails
  to load (LFPowerGrid produced it at RPT l.505-506; a clean load produces zero). Also grep your
  harness `[UILab]`/LOG_TAG PASS/FAIL lines. Group all in-game checks per R5.

### 4.3 The loop, assembled
1. Author `.layout` in **brace** format (Layout Editor for visual placement, or by hand).
2. `python tools/dayz-script-validator/scripts/script_validator.py <addon_root>` → fix all findings.
3. Reconciliation gate (§6.2): `python tools/dayz-script-validator/scripts/ui_reconcile.py <addon>` — FindAnyWidget
   names + `#STR` keys cross-checked against layouts + stringtable.
4. Faithful-ish preview: `build_viewer.py <layout>` (v2 — respects `visible`, models `text_proportion`,
   resolution switcher exposes exact-flag breakage). Open the `*.preview.html`, flip through resolutions,
   diff the 1080p view against the design mockup for gross layout.
5. Deploy via `dayz-test-ingame` (DayZDiag + filePatching, no signing) with a keybind-toggled test menu
   (LF_ColorTest / LFPG_UITest pattern). Optionally add a DbgUI slider panel for live tuning.
6. Post-session: grep RPT for `Cannot open layout` + harness PASS/FAIL; screenshot at target
   resolution; diff vs the calibrated mockup (§6.3).

---

## 5. The UI plan/spec artifact (write this BEFORE any `.layout`)

The skill had no planning workflow. Produce this small artifact first; it is the forward contract for
the UI (mirrors the user's R8 forward-contract discipline and the `dayz-feature-spec` skill).

**5.1 Widget-tree spec table** — one row per widget the plan requires:

| Widget name | Class | Parent | Mode (prop/exact) | Pos | Size | Anchor (h/valign) | Text/#STR | Binding_Name / handler | Color source (layout vs script) |
|---|---|---|---|---|---|---|---|---|---|

Rules for filling it:
- Every visual element in the mockup MUST appear as a row with a real widget **class** (no element
  that only exists as a CSS effect). If it can't be expressed as a widget + verified attribute, it is
  not in the plan (§1.6).
- Choose **Mode** per widget up front: proportional unless it must be pixel-true (§2).
- Name every widget you will `FindAnyWidget`/bind — the name in this table is the contract §6 checks.
- Record where each color comes from (layout attribute vs script `SetColor`) so the preview's
  limitations are known and the in-game color is planned, not discovered.

**5.2 Acceptance criteria (forward contract):** derive them from what the CONSUMER needs, not from
internal consistency — "every row's widget exists in the built layout with the planned name and mode;
every `Binding_Name` resolves to a controller property; every `#STR` resolves in stringtable; the
build screenshots within tolerance of the calibrated mockup at 1080p AND one non-1080p resolution."

---

## 6. The plan → implementation parity gate (the closing check)

The existing DELIVERY CHECKLIST is all syntax (braces, flags, null-checks). Add this gate that ties
the build back to the plan. A crashing UI merge went GREEN through points 1/4/5 before an in-game
test (LFGungame BUG-004), so this is proven to catch real failures.

### 6.1 Offline load gate (automate where possible)
1. Every `CreateWidgets(path)` resolves to a file that EXISTS and is **brace** format (not XML).
   *(A missing file is an un-guardable native CTD — the `if(!root)` after `CreateWidgets` never runs.
   linter: layout-file-missing + XML-format.)*
2. Brace balance per layout (opens == closes); zero XML characters. *(linter: leaf-brace + XML.)*
3. `$PBOPREFIX$`/packaging: every layout path starts with the prefix, and `gui/` (plus
   `*.layout;*.imageset;*.fnt;*.styles;*.edds;*.paa;*.xml`) actually ships — AddonBuilder only packs
   extensions in its copy-list, so a working-locally / missing-for-others UI is usually a packaging
   filter miss. *(linter: PBOPREFIX path; filter list
   https://www.answeroverflow.com/m/1497956336799977484)*

### 6.2 Name / key reconciliation (AUTOMATED 2026-07-03)
Run `python tools/dayz-script-validator/scripts/ui_reconcile.py <addon_root>` (exit 0 clean / 1 FAIL
typo-likely / 2 WARN verify; `--json` for machine output). It cross-checks the whole addon at once:
4. Every string-literal `FindAnyWidget("X")` / `FindWidget("A/B/C")` in `.c` resolves to a widget
   present in some `.layout` of the addon (case-sensitive; a case-only diff is a FAIL — runtime lookup
   is case-sensitive). A close-but-unequal name is FAIL with a "did you mean" suggestion (typo/rename →
   silent null → crash on Cast); a name with no match is WARN (could be vanilla or dynamically created).
5. Every `#STR_...` used in layouts and `.c` string literals exists in the addon's `stringtable.xml`
   OR legacy `stringtable.csv` (case-insensitive; typo → FAIL with suggestion, else WARN).
   Verified 2026-07-03: clean on LFPG_UITest (28 refs, 0 findings) and LFPowerGrid (22 refs + 143 #STR
   over 261 CSV keys, 0 FAIL) — and it surfaced a real dangling `CreateWidgets` on a missing
   `LFPG_TankHUD.layout` in LFPowerGrid. Known false negative: names/keys built from variables or
   concatenation are not resolvable statically and are skipped by design.
6. Every `Binding_Name` / `Relay_Command` matches a controller property/method exactly (still manual —
   grep both sides).

### 6.3 Implemented-against-plan (the fidelity check the skill lacked)
7. Every widget in the §5 spec table exists in the built layout with the planned **name, class, and
   mode**; nothing planned is missing, nothing unplanned crept in.
8. Render the WRITTEN `.layout` (v1 renderer, labelled) and eyeball it against the mockup for gross
   layout — then trust ONLY the in-game screenshot for pixels/colors/fonts.
9. Screenshot in-game at 1080p **and** one non-1080p resolution; diff against the calibrated mockup.
   Resolution divergence here = an exact-flag issue (§1.1); asset-blank divergence = dual-registration
   (§3); color divergence = SetLV / script SetColor (§1.2).

---

## 7. Condensed verified facts that feed the above

Menu lifecycle (see also SKILL.md / expansion-mvc):
- Two opening APIs: `UIManager.EnterScriptedMenu(int id, parent)` creates+opens by **registered
  MenuID** (routes through `Mission.CreateScriptedMenu(id)` — a modded menu opened by ID must be added
  to a `modded ... CreateScriptedMenu(int id)` switch that calls `menu.SetID(id)` on the NEW instance;
  a common bug puts `SetID` in the wrong branch, leaving `MENU_UNKNOWN`); `ShowScriptedMenu(menu,
  parent)` shows an already-constructed instance. `scripts/3_game/tools/uimanager.c`,
  `dayzgame.c:1380-1386`, `missionbase.c:185-239`, `uiscriptedmenu.c:136-153`.
  Community: https://www.answeroverflow.com/m/1018294147649634408
- Vanilla MenuID range is 1..46 (`scripts/3_game/constants.c:170-215`, `MENU_ANY`..
  `MENU_CONNECTION_DIALOGUE`); pick an arbitrary high int for custom menus (e.g. 98765).
- `UIScriptedMenu.OnShow()` auto-calls `LockControls()` and `OnHide()` auto-`UnlockControls()` — per
  device `ChangeGameFocus(±1, INPUT_DEVICE_MOUSE/KEYBOARD/GAMEPAD)` + cursor. Overriding OnShow/OnHide
  without `super` skips input locking; adding your own `ChangeGameFocus` on top double-counts the
  stack. `IsHandlingPlayerDeathEvent()` returns true by default → the menu force-`Close()`s on player
  death; override to `false` to survive death. `scripts/3_game/tools/uiscriptedmenu.c:80-134,173-192,
  603-611`.
- Native modal (no custom layout): `GetUIManager().ShowDialog(caption, text, id, DBT_YESNO, DBB_YES,
  DMT_QUESTION, handler)` → result to `OnModalResult(w,x,y,code,result)` where `code==id`.
  `scripts/3_game/tools/uimanager.c:21-45`.
- HUD overlays extend `ScriptedWidgetEventHandler` (not `UIScriptedMenu`); MUST `Unlink()` the root in
  `OnMissionFinish` or widgets leak into the next session (stacked ghost HUDs after server hops).
  `inputs.xml` actions must be referenced in `config.cpp class inputs` or `GetInputByName` returns null
  and crashes. (stardz DayZ Modding Wiki HUD chapter; DayZ-CommunitySamples UISample.)

Widgets missing from the skill's table:
- `ItemPreviewWidget` (`SetItem(EntityAI)/SetView(idx)/SetModelPosition/Orientation`) and
  `PlayerPreviewWidget` (`SetPlayer/UpdateItemInHands/Refresh/...`). `scripts/3_game/gameplay.c:
  276-312`. Create via `GetWorkspace().CreateWidget(ItemPreviewWidgetTypeID, ...)`, then `SetItem` on
  a client-side object.
- `OnDraggingOver(Widget w, int x, int y, Widget reciever)` exists between OnDragging and OnDrop
  (`enwidgets.c:678`) — omitted from the SKILL.md event list.

Fonts (bitmap-atlas reality):
- Fonts are pre-baked bitmap atlases, one `.fnt`+`.edds` pair PER SIZE (`gui/fonts`: metron12/14/16/
  22/28/48/58, sdf_metronlight24/30/36/42/72, …; 118 `.fnt` files). Layouts reference a specific size
  file (`font "gui/fonts/sdf_MetronLight42"`). You cannot request an arbitrary point size at runtime;
  a custom TTF must be converted in Workbench to `.fnt/.edds` per needed size. `"exact text" 1` pins
  rendering to the registered bitmap sizes; with it off, the engine scales the bitmap to any size.
  Community: https://www.answeroverflow.com/m/1212857334620229632 ,
  https://www.answeroverflow.com/m/759968942113554452
- Workbench has no way to register a custom widget font FOR A MOD so its Layout Editor lists it —
  workaround: drop `.fnt` into `P:\gui\fonts` for preview, then hand-edit the mod's `.layout` font
  paths. `.fnt` files are not hand-editable atlas descriptors. (Strykar 2026-06:
  https://www.answeroverflow.com/m/1511090647824597053)

Imagesets:
- `.imageset` is plain-text, hand-editable — no Workbench needed to read/patch:
  `ImageSetClass { Name "<setname>" RefSize W H  Textures { ImageSetTextureClass { mpix N path
  "{GUID}Gui/imagesets/x.edds" } }  Images { ImageSetDefClass X { Name "X" Pos x y  Size w h
  Flags N } } }`. The `Name` on line 2 is what scripts use in `set:NAME image:IMG` — the filename is
  irrelevant. `gui/imagesets/ccgui_enforce.imageset:1-10` (+ `ProgressMenuTileFull … Flags 3` at
  :4181-4186, tiling flag for segmented progress bars).
- New standalone tool that bypasses Workbench for imagesets: Strykar's **DayZ Imageset Editor**
  (github.com/Strykar86/DayZ-Imageset-Editor, v1.4 2026-06) — drag-drop atlas editor + compiler,
  unpacks vanilla imagesets, exports element PNGs.
- `RichTextWidget` can embed imageset icons inline: `<image set="dayz_gui" name="icon_pin"/>` — mix
  text and icons (keybind hints) in one widget. https://www.answeroverflow.com/m/1019262760732868710

---

## 8. Sources

Local ground truth (verified this session): `scripts/1_core/proto/enwidgets.c`, `.../dbgui.c`,
`scripts/3_game/tools/uimanager.c` + `uiscriptedmenu.c`, `scripts/3_game/constants.c`,
`scripts/3_game/gameplay.c`, `scripts/3_game/gui/spacers/spacerbase.c`, `gui/layouts/day_z_hud.layout`
+ `loading.layout`, `gui/imagesets/ccgui_enforce.imageset`, `gui/fonts/`; project tooling under
`tools/dayz-script-validator/` and `<notes>\DayZ_UI_Research\`;
project ledgers under `<vault>\AI\10_Projects\{LFGungame,DayZ_UI_Research}`.

Web: DayZ Modders Discord via AnswerOverflow (URLs inline); DayZ-CommunitySamples (UISample);
stardz-team DayZ Modding Wiki (HUD overlay chapter) — **⚠️ WARNING (2026-07-05): its script-side
advice is sound, but its `.layout` snippets are XML format (`<?xml?>` + `<Widget>/<Attribute>` tags)
— the exact format verified to crash native CreateWidgets. NEVER copy its layout snippets**; Arma
Reforger "Layout Creation" wiki (same early-Enfusion Layout Editor workflow DayZ uses). Bohemia wiki
`Workbench` / `Game_Editor_(Workbench)` pages exist but block automated fetch (403) — confirm the
exact editor menu path in-app. Searchable proto mirror: **dayz-scripts.yadz.app** (Doxygen-style
PC-Stable script API with a "Widget UI system" group) — handy for quick signature lookups when the
local dump is not at hand. Ecosystem hygiene: GitHub searches for "DayZ mod menu" surface
cheat/malware template repos — never source UI code from them.

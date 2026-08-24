# AnswerOverflow community findings — UI (mined 2026-05-17)

Source: DayZ Modders Discord (serverId 452035973786632194), via AnswerOverflow MCP. All claims below were spot-checked against `P:\scripts\` vanilla source — `[VERIFIED vs P:...]` notes mark what was confirmed.

---

## UI-1. Loading-screen modding — full vanilla class hooks

**Pattern (community-reported, snippet-corrected after vanilla verify):**

Four hookable UIScriptedMenu-family vanilla classes live in `P:\scripts\3_game\dayzgame.c`:

```cs
// P:\scripts\3_game\dayzgame.c:63
class LoginScreenBase extends UIScriptedMenu { ... }
// P:\scripts\3_game\dayzgame.c:110
class LoginQueueBase extends LoginScreenBase { ... }
// P:\scripts\3_game\dayzgame.c:205
class LoginTimeBase extends LoginScreenBase { ... }
// P:\scripts\3_game\dayzgame.c:688
class LoadingScreen { ... }   // NOT a UIScriptedMenu — owns m_WidgetRoot directly
```

The Discord snippet (Deth297) wrote `modded class LoginQueueBase extends UIScriptedMenu` — **wrong syntax**. `modded class` does NOT take an `extends` clause; it just modifies the existing class. Correct form: `modded class LoginQueueBase { ... }`. Inheritance chain is already `LoginQueueBase → LoginScreenBase → UIScriptedMenu`.

**`LoadingScreen` widget bindings to override (verified at `dayzgame.c:693–707`):**

```cs
TextWidget   m_ModdedWarning;          // "ModdedWarning" — set in m_WidgetRoot.FindAnyWidget
ImageWidget  m_ImageWidgetBackground;  // "ImageBackground"
ImageWidget  m_ImageLogoMid;           // "ImageLogoMid"
ImageWidget  m_ImageLogoCorner;        // "ImageLogoCorner"
ImageWidget  m_ImageLoadingIcon;       // "ImageLoadingIcon"
ImageWidget  m_ImageBackground;        // also "ImageBackground" (alias cast)
ProgressBarWidget m_ProgressLoading;   // "LoadingBar"
TextWidget   m_TextWidgetTitle;        // "TextWidget"
TextWidget   m_TextWidgetStatus;       // "StatusText"
ref Timer    m_Timer;                  // exists, lazy-init pattern OK
```

**Override pattern (corrected — replaces the Discord version):**

```cs
modded class LoadingScreen
{
    protected ref TStringArray m_LoadingImageNames = {
        "MyMod/data/loading_01.edds",
        "MyMod/data/loading_02.edds"
    };
    protected int   m_CurrentImageIndex;
    protected const float CYCLE_INTERVAL = 15.0;

    override void Show()
    {
        if (m_LoadingImageNames.Count() == 0) {
            super.Show();
            return;
        }
        m_CurrentImageIndex = Math.RandomInt(0, m_LoadingImageNames.Count());
        ApplyCurrentImage();
        m_ImageLogoMid.Show(false);
        m_ImageLogoCorner.Show(false);
        m_ModdedWarning.Show(false);

        if (!m_Timer) m_Timer = new Timer();
        m_Timer.Run(CYCLE_INTERVAL, this, "CycleImage", NULL, true);
        super.Show();
    }

    void CycleImage()
    {
        if (!m_ImageWidgetBackground || m_LoadingImageNames.Count() == 0) return;
        m_CurrentImageIndex++;
        if (m_CurrentImageIndex >= m_LoadingImageNames.Count())
            m_CurrentImageIndex = 0;
        ApplyCurrentImage();
    }

    protected void ApplyCurrentImage()
    {
        string path = m_LoadingImageNames.Get(m_CurrentImageIndex);
        m_ImageWidgetBackground.LoadImageFile(0, path);
    }
}
```

`LoadImageFile(0, path)` accepts either a direct `.edds`/`.paa` path or imageset syntax `"set:NAME image:NAME"` (Don Alfredo confirmed both work; second is for imagesets, see UI-2 about the name pitfall).

`LoadMaskTexture(path)` is a separate hook for the alpha-mask layer that vanilla loading screens use; pass `""` to remove the vanilla mask.

**Sources:**
- Deth297 — https://www.answeroverflow.com/m/1499205167562887209
- Deth297 (image cycling) — https://www.answeroverflow.com/m/1499540557586764018
- Don Alfredo (Math.Randomize + mask) — https://www.answeroverflow.com/m/1499206814103769220
- Zasanta (open question: layout swap from Show()?) — https://www.answeroverflow.com/m/1500162785928024074

**[VERIFIED vs P:\scripts\3_game\dayzgame.c lines 63, 110, 205, 688, 693–707, 713–724]**

---

## UI-2. ImageSet filename ≠ internal Set name

In Workbench at `P:\gui\imagesets\` (confirmed exists), each `.imageset` file has two names:

1. **Filename** — e.g. `dayz_gui.imageset` on disk.
2. **Internal Set name** — visible in Workbench's right-panel `ImageSet` tab. This is what scripts must reference in `LoadImageFile(0, "set:NAME image:IMG")`.

These can differ. Silent-fail bug when scripts pass the filename instead of the Set name — the image just doesn't appear, no error.

**Workflow when adding a new imageset:**
1. Create `.imageset` in Workbench.
2. **Check the `ImageSet` tab** for the actual Set name.
3. Use THAT name in scripts.

**Source:** Strykar — https://www.answeroverflow.com/m/1504269524562874568

**[VERIFIED] Imagesets directory at `P:\gui\imagesets\` confirmed (ccgui_enforce.imageset, dayz_gui.imageset, etc.).**

---

## UI-3. `.layout` widget draw order is top-down — background must be first

Workbench draws widgets in the order they appear in the `.layout` file, top to bottom. If a background widget is placed below other widgets in the file, it will be drawn ON TOP of them in-game (covering them).

**Rule:** background image widget MUST be the first child in its parent block.

If Workbench reorders during edit (e.g. when adding new widgets), cut and paste the background widget back to the top via plain-text editor before saving.

**Source:** Strykar — https://www.answeroverflow.com/m/1504146173974286477

(Community-reported behavior; no vanilla code to cite.)

---

## UI-4. `.layout` typos break the entire file at the point of failure

The Workbench `.layout` parser is fail-loud-but-partial: it loads widgets sequentially until the first syntax error, then stops. Widgets defined AFTER the broken line silently never appear.

**Symptom you may see:** "all my widgets after the new <X> widget disappeared" → look for a typo or missing brace at the boundary.

**There is no external `.layout` linter today** (no equivalent of the `enscript` extension for `.c` in VS Code). Workbench is the only validator.

Already covered by the existing UI rule "Brace count MUST match — verify opens == closes."

**Source:** Strykar — https://www.answeroverflow.com/m/1503971202559901867

---

## UI-5. Image-based progress bars exist (via `DayZwidgets.styles`) — and tile-mode for Fallout-style segmented bars

DayZ DOES support image-based ProgressBar widgets, defined in `DayZwidgets.styles` (Strykar walked back an earlier "DayZ doesn't support" claim). Bohemia uses 0–255 alpha (8-bit). A 1×1 px sprite can be scaled to any size without blur.

**Segmented "Fallout-style" bar trick:**

Vanilla imageset `P:\gui\imagesets\ccgui_enforce.imageset` (confirmed exists) contains an image called `ProgressMenuTileFull` that has transparent left/right edges AND has its tile flag set. When a ProgressBar widget is wider than this image, the engine tiles it across the widget — the transparent edges become gaps between the repeated colored portion, producing a discrete segmented look without needing a custom sprite.

**Use case:** custom HUD bars (health, food, hydration) with a retro tick-mark style.

**Sources:**
- Strykar (DayZwidgets.styles + 1px sprite) — https://www.answeroverflow.com/m/1504239507233575104
- Strykar (Fallout tick bar via ProgressMenuTileFull) — https://www.answeroverflow.com/m/1504244290656927847

**[NOT VERIFIED in scripts]** — `ProgressMenuTileFull` is an imageset entry, not a script symbol; cannot grep in `P:\scripts\`. Open `P:\gui\imagesets\ccgui_enforce.imageset` in Workbench to confirm the entry name and tile flag before relying on this.

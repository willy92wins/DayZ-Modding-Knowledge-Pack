# Hot iteration — edit a `.layout` on disk and see it in the running game

Measured 2026-08-19 on DayZ 1.29 (runs `3b63168d`, `4320d1d6`, `08343f0c`, `fdf07db7`).
Every number below came from the engine, not from reading source.

The short version: **a `.layout` under `$profile:` is re-read from disk on every load, so a
UI can be iterated in seconds instead of one repack-and-boot per change.** Everything else
on this page is the rule that makes it work and the four traps that make it look like it
does not.

---

## 1. The rule that decides everything

**An addon-prefixed path is served by the PBO and only by the PBO.** Not the work drive,
not a loose file next to the PBO, not a loose file at a path the PBO does not even contain.
Three separate measurements collapse into that one sentence:

| What was tried | Result |
|---|---|
| A loose `.c` on the work drive (`P:\`) | PBO wins (SP-078, July) |
| A loose `.layout` at a path the PBO **also** contains | PBO wins |
| A loose `.layout` at a path the PBO **does not** contain | Not visible at all — `FileExist` returns 0 |

The third row is the one that closes it, and it carries its own positive control: in the
same probe, `FileExist` returned **1** for a file that exists *only inside the PBO*. So the
0 on the loose path is a real absence, not a blind guard (run `4320d1d6`).

**The corollary people usually want next:** adding assets to a mod "hot" — dropping a
texture or a model into the mod folder of a running game — is closed by the same mechanism.
The addon prefix is not a directory the engine watches.

**The exception, and it is the useful one:** `$profile:` resolves to the client's
`-profiles=` directory, which is an ordinary writable folder outside any PBO. The engine
reads it on demand. That is the whole loop.

---

## 2. What actually got measured

Run `08343f0c`, client 1920×1080:

| Question | Answer |
|---|---|
| Does a `.layout` written from outside the game load? | Yes, from `$profile:` |
| Do the engine rects match an offline prediction of the same file? | Worst delta **4,15e-05 px** across 3 widgets |
| Is the file re-read on **every** call, or parsed once and cached? | **Re-read every call**: same path, different bytes → different rects (5,37e-05 px against the new prediction) |
| Does a missing path kill the client? | No, when guarded — see §4 |
| Does unloading leave anything behind? | No: after `Unlink()`, lookup by name returns `widget_not_found` |

The re-read row is the one that separates a design loop from a one-shot. Test it with
**two files that predict different geometry**, never with the same file twice — otherwise a
cached parse passes the test.

Run `fdf07db7` added textures: a `.paa` copied into `$profile:` draws identically to the
same file served by a PBO — means within 1/255, standard deviations within 0,8, with both a
positive and a negative control in the same frame. **So hot UI can carry its own imagery**,
not just boxes and text.

---

## 3. The loop

1. Write the `.layout` into the client's profile directory from outside the game.
2. Reload it in the running client.
3. Capture a frame; read back the engine rects.
4. Compare against the offline prediction; look at the frame.
5. Edit and repeat — no repack, no reboot.

With DayZ-MCP the reload is one verb:

```
ui_reload_layout(path="$profile:my_panel.layout")   # loads, returns the engine rects
ui_reload_layout(mode="close")                      # unlinks the preview
```

It returns the same node shape as `ui_tree`, so an existing rect comparison keeps working.
It needs a lease and it is client-side.

**Without DayZ-MCP** the same two engine calls work from your own mod code:

```c
WorkspaceWidget workspace = GetGame().GetWorkspace();
if (m_Preview)                       // ALWAYS first — see trap 2
{
    m_Preview.Unlink();              // 1_core\proto\EnWidgets.c:173
    m_Preview = null;
}
if (!FileExist(path))                // 1_core\proto\ensystem.c:397 — see trap 1
    return;
m_Preview = workspace.CreateWidgets(path);   // 1_core\proto\EnWidgets.c:181
```

`CreateWidgets(string layout, Widget parentWidget = NULL, bool immedUpdate = true)` — leave
`immedUpdate` at its default: with it, the rects are already correct **in the same call**,
no frame of waiting. That was measured, not assumed.

---

## 4. The four traps

**Trap 1 — `CreateWidgets` on a missing file kills the client inside the native call.**
No exception, no null return: the process dies. `FileExist` is the only guard, and it
resolves VFS paths (proved by the positive control in §1), so it is a real guard and not a
disk-only check. Guard every runtime load, always.

**Trap 2 — a second `CreateWidgets` STACKS, it does not replace.** Two loads leave two
trees on screen, the second drawn over the first. Symptoms: clicks land on the invisible
older copy, and a rect snapshot stops describing what is on screen. `Unlink()` the previous
root before every load. Cheap way to prove there is only one: unload and check the name is
gone — if a copy had been stacked, one would survive.

**Trap 3 — a UI texture that does not resolve paints a flat WHITE box and logs NOTHING.**
Not a hole, not a magenta placeholder, not a warning: the slot fills with white
(255, 255, 255, standard deviation **0,0**) and the client RPT says nothing at all — zero
lines for the missing name in 46 KB of log. If a design comes out white, suspect the texture
path long before the color or the style.

**Trap 4 — perfect rects say nothing about whether anything is drawn.** A panel can report
exactly the right rectangle and paint nothing. It happened with a style name that exists, is
the right type, and whose `Normal` state has an empty `Center` image — every automated check
passed and the panel was invisible. **Always end the loop with a frame**, and if you need a
mechanical verdict, put a positive and a negative control in the same frame so the eye is
comparing rather than judging.

---

## 5. What this loop does NOT give you

The preview shows **appearance, not behaviour**. Nothing wires a script class to the root,
so its buttons have no handlers; a preview is for geometry, color, text fit and imagery. To
exercise handlers, focus and hit-testing you still need the real menu.

Two things remain unmeasured, both cheap to fold into a future run: whether a **custom font**
and whether an **imageset** resolve from `$profile:`. Vanilla fonts and imagesets work
because they come from the game's own PBOs.

---

## 6. Measured 2026-08-20: what a rendered frame settled

Six flights and four probes against DayZ 1.29.163709, client at 1280x720 and 1920x1080,
every claim below anchored to a capture.

### `#STR_` keys DO resolve in a `$profile:` preview

One frame, four widgets, three sources — the positive control is the whole point:

| Widget | Text set in the layout | On screen |
|---|---|---|
| Title | `#STR_LFPG_ACTION_ADD_WAYPOINT` (another **mod**'s key) | **Add waypoint** |
| Message | literal, no key | renders, and **wraps across two lines** |
| BtnNo | `#STR_CfgWheel0` (**vanilla**) | **Rueda** |
| BtnYes | a key defined by no stringtable | `STR_UI_YES`, verbatim |

So the preview path is not the problem when a key prints raw: the key is simply not
defined. A template that ships `#STR_` placeholders without a `stringtable.csv`
reads as broken on first run, which is why one now ships beside these layouts.

### `GetText()` cannot judge key resolution — only the frame can

In that same frame, `ui_tree` reported `BtnNo.text == "#STR_CfgWheel0"` while the screen
showed **Rueda**. The engine substitutes at draw time and hands back what was assigned.
Any check of the form "read the widget text, see if it still starts with `#`" reports a
failure that is not happening. Two of seven widgets were readable at all
(`text_readable` was false for every `MultilineTextWidgetClass`), so the channel is both
partial and misleading.

### An unresolved key logs nothing, and cannot wrap

Zero RPT lines matched `STR_UI_` across a 49,340-byte client log. And the classic
"the title is clipped at both ends" symptom was the key, not the wrap: `STR_UI_MODAL_MESSAGE`
is a single token with no spaces, and `wrap` breaks on spaces. The same widget with real
prose wrapped correctly.

### Glyph height tracks the WIDGET height

`form_row.layout` loaded standalone has root `size 1 1`, so its `RowLabel` box is the whole
screen (measured 435x720 px at 720p) and it renders a single screen-filling letter. The
**same file**, with only the root changed to `size 0.30 0.05` — `RowLabel` becomes 130x36 px
— renders readable text. Nothing else was touched, `text_proportion` included. That is the
mechanism behind an oversized body: the box, not the font.

### OPEN: `text_proportion` did not move it

Six variants of `modal_panel.layout` were flown with `text_proportion` inserted into
`Message` at 0.03 / 0.05 / 0.08 / 0.12 / 0.20 / 0.36. The glyph measured **104 px in all
six** (bright-pixel bounding box over the message band), with the Title in the same frames
constant at 21 px as a control. Either the attribute is inert on
`MultilineTextWidgetClass`, or the parser ignored it at the position used — it was inserted
immediately after `name`, whereas `Title` declares it after `wrap`. **This experiment does
not separate those two**, so no `text_proportion` value is recommended here. If a body
renders too large, change the box height, and treat any advice about this attribute as
unverified until someone flies the other insertion position.

### A preview draws on top but receives no input

`ui_click` on a preview button does nothing, and neither does a real mouse click with the
inventory open — the preview renders **above** the inventory and still never focuses.
Measured: zero reddish pixels in the button band across four frames (unfocused, two timed
bursts, post-click), while the same detector found 1,767 reddish pixels elsewhere in the
frame. Draw order and input routing are separate; `CreateWidgets` gives the first without
the second, because nothing calls `SetActiveWindow` on the new root
(`P:\scripts\1_core\proto\EnWidgets.c:695`). Focus states, hover states and wheel
scrolling are therefore **not observable** in this loop at all — not by an agent, and not
by a human at the keyboard.

### Name resolution is global — prefix your preview widgets

`ui_click` / `ui_set_text` / `ui_tree` resolve by name through `FindAnyWidget`, which does
not care which tree a name came from. A preview whose widgets are called `BtnYes` or
`Title` collides with whatever else is loaded. Give hot-iteration layouts a prefix of their
own.

### Packaging note for the stringtable

A stringtable is addon-level: read from the PBO at load, so unlike a `$profile:` layout it
does not hot-reload. Two traps when building one: AddonBuilder's binarizing pass applies a
file whitelist and **drops `.csv` from the PBO** (pack with `-packonly`, or add the
extension to an include list), and in this workspace a `config.bin` produced by that same
pass has been measured not to register at all, with the mod mounting silently broken.


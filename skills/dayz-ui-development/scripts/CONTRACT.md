# Contrato — paneles UI on demand

Layouts to load from `$profile:` with `ui_reload_layout` and populate on the fly with `ui_set_text` (FindAnyWidget by `name`). Authored texts empty (`text ""`). `#STR_` prohibited: a stringtable does not travel with a loose `.layout`.

`FindAnyWidget` is global: only one of these panels at a time (Unlink / `ui_reload_layout(mode="close")` before the next one).

## Names by type

All TextWidgets start at `text ""`. The orchestrator injects the string.

### `feed` (chat / log)

| name | class | `ui_set_text` |
|---|---|---|
| `FeedRoot` | FrameWidgetClass | no (host 1×1, `ignorepointer 1`, `priority 2000`) |
| `FeedPanel` | PanelWidgetClass | no (`style rover_sim_colorable`) |
| `TitleText` | TextWidgetClass | yes (always present) |
| `FeedLine0` … `FeedLine{N-1}` | TextWidgetClass | yes, one line per row |

### `info` (etiqueta / valor)

| name | class | `ui_set_text` |
|---|---|---|
| `InfoRoot` | FrameWidgetClass | no |
| `InfoPanel` | PanelWidgetClass | no |
| `TitleText` | TextWidgetClass | yes (always present) |
| `Label0` … `Label{N-1}` | TextWidgetClass | yes |
| `Value0` … `Value{N-1}` | TextWidgetClass | yes |

### `hud` (minimal HUD)

| name | class | `ui_set_text` |
|---|---|---|
| `HudRoot` | FrameWidgetClass | no (`priority 100`, tree `ignorepointer 1`) |
| `HudPanel` | PanelWidgetClass | no (`halign left` / `valign top`) |
| `TitleText` | TextWidgetClass | only if `--title` is passed |
| `FeedLine0` … `FeedLine{N-1}` | TextWidgetClass | yes |

`--title` does not write the literal into the widget (remains `text ""`); it goes into the file comment. The visible title is set with `ui_set_text` on `TitleText`.

## CLI

```
python gen_panel_layout.py <feed|info|hud> --rows N [--title TEXT] --out FILE
                           [--width W] [--height H] [--x X] [--y Y]
python gen_panel_layout.py --self-test
```

Units: screen fraction (flags `hexact*` / `vexact*` = 0). `--x`/`--y` anchor the top left corner of the panel.

| kind | --width | --height | --x | --y |
|---|---|---|---|---|
| feed | 0.32 | 0.45 | 0.02 | 0.50 |
| info | 0.28 | 0.40 | 0.02 | 0.04 |
| hud  | 0.22 | 0.10 | 0.76 | 0.04 |

Grammar and attributes: `stringtable_ladder.layout` (tested in-game with `ui_reload_layout`); extra HUD chrome from `hud_overlay.layout`. Encoding: UTF-8 without BOM, LF. No absolute paths inside `.layout`.

Ejemplos:

```
python gen_panel_layout.py feed --rows 10 --title "CHAT" --out chat_feed.layout
python gen_panel_layout.py info --rows 6 --title "STATUS" --out info_panel.layout
python gen_panel_layout.py hud --rows 2 --out mini_hud.layout
```

## Verificar

`python gen_panel_layout.py --self-test` — `{`/`}` balance per file, unique `name`s, each declared `FeedLineK`/`ValueK` appears exactly once; output `SELFTEST PASS` or `SELFTEST FAIL`.
Copy the `.layout` to `$profile:` and `ui_reload_layout(path="$profile:<file>.layout")` (Unlink beforehand); then `ui_set_text` by the `name`s above.

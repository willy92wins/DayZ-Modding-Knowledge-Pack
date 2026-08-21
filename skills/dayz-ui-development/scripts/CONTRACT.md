# Contrato — paneles UI on demand

Layouts para cargar desde `$profile:` con `ui_reload_layout` y rellenar en caliente con `ui_set_text` (FindAnyWidget por `name`). Textos autorados vacíos (`text ""`). Prohibido `#STR_`: un stringtable no viaja con un `.layout` suelto.

`FindAnyWidget` es global: un solo panel de estos a la vez (Unlink / `ui_reload_layout(mode="close")` antes del siguiente).

## Nombres por tipo

Todos los TextWidget arrancan en `text ""`. El orquestador inyecta el string.

### `feed` (chat / log)

| name | clase | `ui_set_text` |
|---|---|---|
| `FeedRoot` | FrameWidgetClass | no (host 1×1, `ignorepointer 1`, `priority 2000`) |
| `FeedPanel` | PanelWidgetClass | no (`style rover_sim_colorable`) |
| `TitleText` | TextWidgetClass | sí (siempre presente) |
| `FeedLine0` … `FeedLine{N-1}` | TextWidgetClass | sí, una línea por fila |

### `info` (etiqueta / valor)

| name | clase | `ui_set_text` |
|---|---|---|
| `InfoRoot` | FrameWidgetClass | no |
| `InfoPanel` | PanelWidgetClass | no |
| `TitleText` | TextWidgetClass | sí (siempre presente) |
| `Label0` … `Label{N-1}` | TextWidgetClass | sí |
| `Value0` … `Value{N-1}` | TextWidgetClass | sí |

### `hud` (HUD mínimo)

| name | clase | `ui_set_text` |
|---|---|---|
| `HudRoot` | FrameWidgetClass | no (`priority 100`, árbol `ignorepointer 1`) |
| `HudPanel` | PanelWidgetClass | no (`halign left` / `valign top`) |
| `TitleText` | TextWidgetClass | solo si se pasa `--title` |
| `FeedLine0` … `FeedLine{N-1}` | TextWidgetClass | sí |

`--title` no escribe el literal en el widget (sigue `text ""`); va al comentario del fichero. El título visible se pone con `ui_set_text` sobre `TitleText`.

## CLI

```
python gen_panel_layout.py <feed|info|hud> --rows N [--title TEXT] --out FILE
                           [--width W] [--height H] [--x X] [--y Y]
python gen_panel_layout.py --self-test
```

Unidades: fracción de pantalla (flags `hexact*` / `vexact*` = 0). `--x`/`--y` anclan la esquina superior izquierda del panel.

| kind | --width | --height | --x | --y |
|---|---|---|---|---|
| feed | 0.32 | 0.45 | 0.02 | 0.50 |
| info | 0.28 | 0.40 | 0.02 | 0.04 |
| hud  | 0.22 | 0.10 | 0.76 | 0.04 |

Gramática y atributos: `stringtable_ladder.layout` (probado in-game con `ui_reload_layout`); chrome HUD extra de `hud_overlay.layout`. Codificación: UTF-8 sin BOM, LF. Sin rutas absolutas dentro del `.layout`.

Ejemplos:

```
python gen_panel_layout.py feed --rows 10 --title "CHAT" --out chat_feed.layout
python gen_panel_layout.py info --rows 6 --title "STATUS" --out info_panel.layout
python gen_panel_layout.py hud --rows 2 --out mini_hud.layout
```

## Verificar

`python gen_panel_layout.py --self-test` — balance `{`/`}` por fichero, `name` únicos, cada `FeedLineK`/`ValueK` declarado aparece exactamente una vez; salida `SELFTEST PASS` o `SELFTEST FAIL`.
Copiar el `.layout` a `$profile:` y `ui_reload_layout(path="$profile:<file>.layout")` (Unlink previo); luego `ui_set_text` por los `name` de arriba.

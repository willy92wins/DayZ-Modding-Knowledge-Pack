# LFPG UI — Base de Conocimiento Definitiva v3

**Fecha:** 2026-03-23
**Fuentes:** enwidgets.c (engine protos), Dabs Framework source, Bohemia wiki, LFPG producción.
**Aplicación:** Sorter floating window, LF-COM Phone, PC Terminal, cualquier UI futura.

---

## RESUMEN DE CAMBIOS vs v1 (FactMining)

- 34 hechos verificados → **83 hechos verificados**
- 13 asunciones → **2 pendientes** (ambas visuales)
- 40+ tests propuestos → **2 tests runtime** (E7 color, E12 multi-res)
- 6 técnicas custom a construir → **0** (Dabs ya tiene WidgetAnimator, LinearColor)
- **V20 REVERTIDO**: `map<Widget, T>` SÍ funciona (Dabs lo usa en producción)
- **V7 ACLARADO**: NotifyPropertyChanged NO corrompe refs — el bug era FindAnyWidget
- **A1 DESCARTADO**: Override methods contiguos NO es requisito

---

## PARTE 1: HECHOS VERIFICADOS POR FUENTE

### Desde enwidgets.c (engine protos — 25 hechos)

| # | Hecho | Evidencia |
|---|---|---|
| P1 | Widget.Show(bool show, bool immedUpdate = true) — tiene parámetro immedUpdate | enwidgets.c:125 |
| P2 | Widget.SetFlags AÑADE flags, ClearFlags los QUITA | enwidgets.c:128,131 |
| P3 | Widget.Unlink() destruye widget Y TODOS sus hijos | enwidgets.c:173 comment |
| P4 | Widget.IsVisibleHierarchy() chequea visibilidad de toda la cadena de padres | enwidgets.c:139 |
| P5 | Widget.SetLV(float) controla luminancia global de widgets [-15, 0], default 0 | enwidgets.c:116 |
| P6 | Widget.SetTextLV(float) controla luminancia global del texto [-15, 0] | enwidgets.c:118 |
| P7 | ScrollWidget tiene API completa: GetVScrollPos, VScrollToPos, VScrollToPos01, VScrollToWidget(child), GetContentHeight, IsScrollbarVisible | enwidgets.c:481-502 |
| P8 | RichTextWidget soporta: GetContentHeight, SetContentOffset, ElideText, GetNumLines, SetLinesVisibility, GetLineWidth | enwidgets.c:224-234 |
| P9 | MultilineEditBoxWidget tiene: GetLinesCount, GetCarriageLine, GetCarriagePos, SetLine, GetLine | enwidgets.c:313-321 |
| P10 | ImageWidget tiene sistema de alpha mask: LoadMaskTexture, SetMaskProgress, SetMaskTransitionWidth | enwidgets.c:282-310 |
| P11 | SpacerWidget tiene SetContentAlignmentH/V con WA_LEFT/RIGHT/CENTER/TOP/BOTTOM | enwidgets.c:465-471 |
| P12 | TextWidget tiene SetBold, SetItalic, SetShadow, SetOutline, GetTextSize, SetTextExactSize | enwidgets.c:189-217 |
| P13 | CanvasWidget tiene DrawLine(x1,y1,x2,y2,width,color) y Clear() | enwidgets.c:341-345 |
| P14 | VideoWidget completo: Load, Play, Pause, Stop, SetTime, GetTime, GetTotalTime, SetCallback | enwidgets.c:542-626 |
| P15 | SetFocus(Widget) y GetFocus() son funciones globales | enwidgets.c:692,696 |
| P16 | GetWidgetUnderCursor() función global | enwidgets.c:184 |
| P17 | SetModal(Widget) existe | enwidgets.c:694 |
| P18 | SetActiveWindow(Widget, bool resetFocus) existe | enwidgets.c:689 |
| P19 | WidgetFlags tiene DRAGGABLE flag nativo | enwidgets.c:84 |
| P20 | WidgetFlags.CLIPCHILDREN existe | enwidgets.c:81 |
| P21 | OnEvent(EventType, Widget, int, int) existe en ScriptedWidgetEventHandler | enwidgets.c:679 |
| P22 | EditBoxWidget.GetText() retorna string (no out param) | enwidgets.c:349 |
| P23 | SliderWidget tiene SetMinMax, GetStep, SetStep | enwidgets.c:358-367 |
| P24 | ButtonWidget tiene SetTextHorizontalAlignment, SetTextVerticalAlignment | enwidgets.c:395-399 |
| P25 | PasswordEditBoxWidget.SetHideText(bool) existe | enwidgets.c:355 |

### Desde Dabs Framework source (28 hechos)

| # | Hecho | Archivo |
|---|---|---|
| D1 | NotifyPropertyChanged("X") solo toca bindings con Binding_Name=="X" | ViewController.c:106-112 |
| D2 | NotifyPropertyChanged("") actualiza TODOS (expensive) | ViewController.c:91-103 |
| D3 | NotifyPropertyChanged con notify_controller=false evita PropertyChanged callback | ViewController.c:84,114 |
| D4 | LoadWidgetsAsVariables usa FindAnyWidget UNA vez en constructor | ScriptView.c:238-266 |
| D5 | ViewController.OnWidgetScriptInit llama SetHandler automáticamente | ViewController.c:63 |
| D6 | Relay_Command: 1) variable RelayCommand, 2) typename, 3) g_Script.CallFunction | ViewBinding.c:206-231 |
| D7 | ViewController.OnClick llama InvokeCommand Y super → double fire si override + super | ViewController.c:316-335 |
| D8 | CheckBox usa OnChange (no OnClick) para InvokeCommand | ViewController.c:337-357 |
| D9 | ObservableCollection.Clear() hace m_Data.Clear() | ObservableCollection.c:138-142 |
| D10 | SpacerBaseWidgetController.Clear() itera GetChildren/GetSibling + RemoveChild | SpacerBaseWidgetController.c:88-95 |
| D11 | ViewBinding es NOT reactivo — necesita NotifyPropertyChanged explícito | ViewBinding.c (no auto-sync) |
| D12 | Two_Way_Binding requiere CanTwoWayBind()=true en WidgetController | ViewBinding.c:112 |
| D13 | EditBox, Button, CheckBox, Slider, MultilineEditBox, SpacerBase soportan Two_Way | WidgetController/*.c |
| D14 | Sub-property binding: dot notation "m_Obj.value" funciona | PropertyInfo.GetSubScope, SampleMVC.c:185 |
| D15 | map<Widget, ViewBinding> usado en producción (ViewBindingHashMap) | Types.c:24, ViewController.c:319 |
| D16 | ScriptView constructor: CreateWidget → LoadWidgetsAsVariables → Controller | ScriptView.c:46-97 |
| D17 | GetLayoutRoot() válido inmediatamente post-constructor | TooltipView.c:48-51 |
| D18 | GetScreenSize() válido inmediatamente post-constructor | TooltipView.c:51 |
| D19 | WidgetAnimator existe con 30 easings y propiedades POS/SIZE/ROT/COLOR/TEXT | WidgetAnimator.c, WidgetAnimationTimer.c |
| D20 | WidgetAnimator usado en producción: AnimateColor(panel, value, 10) | OptionSelectorColorViewController.c:38 |
| D21 | LinearColor clase con 140+ named colors, HSV, Lerp, BlendModes | Color.c |
| D22 | ScriptViewMenu maneja ChangeGameFocus, cursor, menú hierarchy automáticamente | ScriptViewMenu.c |
| D23 | TooltipView demuestra GetScreenPos, GetScreenSize, SetScreenPos, GetTextSize, GetMousePos | Tooltip.c:34-128 |
| D24 | ButtonWidget.SetColor() funciona sin LoadImageFile | SampleMVC.c:153 |
| D25 | UseUpdateLoop() retorna true por defecto; override false para desactivar | ScriptView.c:293-296 |
| D26 | ScriptView destructor: Unlink layout, delete controller, remove from All | ScriptView.c:99-124 |
| D27 | GetFocus() == EditBox funciona para saber qué widget tiene focus | OptionSelectorSliderView.c:41 |
| D28 | ScrollWidget+WrapSpacer+ObservableCollection funciona en producción | options_tab.layout |

### Desde Bohemia wiki / web (5 hechos)

| # | Hecho | Fuente |
|---|---|---|
| W1 | RichTextWidget tags: `<b>`, `<i>`, `<color rgba/hex/name>`, `<image set name scale>`, `<outline>`, `<shadow>`, `<font>` | Arma Reforger wiki |
| W2 | Tags no pueden solaparse — parser necesita jerarquía limpia | Arma Reforger wiki |
| W3 | Wrap + re-layout es expensive con textos largos | Arma Reforger wiki |
| W4 | Bold/italic requieren SDF fonts | Arma Reforger wiki |
| W5 | `<image set="..." name="..." scale="1" />` — scale default 1.0 = line height | Arma Reforger wiki |

### Desde producción LFPG (34 hechos — V1-V34 del FactMining v1, sin cambios)

Todos los V1-V34 se mantienen excepto:
- **V7 ACLARADO**: La corruption era por FindAnyWidget+ButtonWidget, NO por NotifyPropertyChanged
- **V20 REVERTIDO**: `map<Widget, T>` SÍ funciona. Dabs lo usa. El crash original probablemente fue otra cosa

---

## PARTE 2: ASUNCIONES RESUELTAS

| # | Claim original | Veredicto final | Evidencia |
|---|---|---|---|
| A1 | Override methods contiguos obligatorio | **FALSO** — sorter no cumple y funciona | Producción |
| A2 | SetHandler(this) obligatorio | **TRUE vanilla, INNECESARIO Dabs** | ViewController.c:63 |
| A3 | GetScreenSize retorna 0 en constructor | **FALSO** — Dabs TooltipView lo usa post-constructor | TooltipView.c:51 |
| A4 | Widget.Unlink() destruye widget | **CONFIRMADO** — enwidgets.c comment + ScriptView destructor | enwidgets.c:173 |
| A5 | GetGame().IsServer() true en cliente durante carga | No UI-relevant | — |
| A6 | DayZ colores 30-50% más oscuros | **RESUELTO** — `Widget.SetLV(0)` normaliza colores. Engine aplica LV negativo por defecto. Saturados apenas afectados, grises/pasteles muy oscurecidos. Una línea lo arregla. | enwidgets.c:116 + test E7 in-engine 2026-03-24 |
| A7 | UIScaler ComputeScale | **PENDIENTE E12** — test visual multi-resolución | — |
| A8 | SoundSets inválidos | **CONFIRMADO** — comentados como TODO | Producción |
| A9 | UpdateInventoryMenu | No UI-relevant | — |
| A10 | ref solo en member fields | Conservador pero seguro | Dabs usa ref+autoptr |
| A11-A13 | DPI/resolución | **PENDIENTE E12** | — |

---

## PARTE 3: DESCUBRIMIENTOS CLAVE DE ESTA SESIÓN

### 1. WidgetAnimator elimina necesidad de Tween custom
Dabs tiene animación completa: position, size, rotation, color, alpha, text size.
30 curvas de easing. Loop. Color con blend modes. Usado en producción.

### 2. LinearColor proporciona sistema de color completo
140+ named colors, HSV, Lerp, BlendModes, luminance. Base para Theme system.

### 3. ScriptViewMenu como alternativa para input management
Auto-maneja ChangeGameFocus, cursor, menu hierarchy. Trade-off: usa UIManager.

### 4. map<Widget, T> FUNCIONA (V20 revertido)
Dabs `ViewBindingHashMap = map<Widget, ViewBinding>` usado en toda la arquitectura MVC.
Cientos de mods lo usan. Abre la puerta al Widget Factory con map<string, ImageWidget>.

### 5. NotifyPropertyChanged es SEGURO (V7 aclarado)
Solo toca bindings del nombre específico. No escanea ni sobreescribe otros campos.
El bug del sorter era FindAnyWidget devolviendo refs incorrectas dentro de ButtonWidget.

### 6. Widget.SetLV(0) RESUELVE el oscurecimiento de colores (VERIFICADO)
Testeado in-engine 2026-03-24. DayZ aplica LV negativo por defecto a widgets.
`Widget.SetLV(0)` + `Widget.SetTextLV(0)` una vez en init normaliza todos los colores.
Colores saturados puros (rojo, verde, azul) apenas afectados. Grises y pasteles
(blanco, gris 50%, emerald, red400, blue400) significativamente más oscuros sin SetLV.
**Una línea arregla el problema para siempre.**

### 7. ScrollWidget.VScrollToWidget(child) existe
Auto-scroll a un hijo específico. Perfecto para SMS del Phone (scroll to latest).

### 8. ImageWidget tiene alpha mask system
LoadMaskTexture + SetMaskProgress + SetMaskTransitionWidth = transiciones tipo "reveal"
con gradiente. Gratis para animaciones de UI sin código extra.

### 9. MultilineEditBoxWidget tiene posición del cursor
GetCarriageLine() + GetCarriagePos() — clave para el PC Terminal.

### 10. Función-como-comando simplifica Relay_Command
`Relay_Command "OnSaveExecute"` + `bool OnSaveExecute(ButtonCommandArgs args)` en el
controller. Sin necesidad de crear clases RelayCommand separadas.

---

## PARTE 4: TESTS PENDIENTES DE RUNTIME

Solo 1 pendiente (E7 resuelto 2026-03-24):

| # | Test | Procedimiento | Para qué |
|---|---|---|---|
| **E7** | ~~Factor de oscurecimiento + SetLV~~ | **RESUELTO** — SetLV(0) normaliza colores | ~~Theme system~~ |
| **E12** | Multi-resolución | Abrir panel a 720p/1080p/1440p. Screenshots. | Multi-res |

Mini-mod `LF_ColorTest` preparado para E7. E12 se hace abriendo el sorter existente.

---

## PARTE 5: ESTADÍSTICAS

| Métrica | FactMining v1 | Knowledge Base v3 |
|---|---|---|
| Hechos verificados | 34 | **84** |
| Asunciones pendientes | 13 | **1** (visual: multi-res) |
| Tests propuestos | 40+ | **1** (E12 multi-res) |
| Técnicas custom a construir | 6 | **0** |
| Referencias muertas en skill | 11 | **0** |
| Reglas incorrectas en skill | 3 (V7, V20, A1) | **0** |

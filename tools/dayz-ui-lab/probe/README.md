# LF_UIProbe

Sonda source-only, first-party y sin Dabs para fijar B19/B20 en DayZDiag.

## Preparación

El repositorio normaliza texto a LF. Por eso la variante CRLF no se versiona
como supuesto: se genera byte a byte en un directorio nuevo.

```powershell
python tools/dayz-ui-lab/probe/prepare_probe.py `
  --out reports/dayz-ui-lab/probe/LF_UIProbe
```

El preparador falla si el destino ya existe. El resultado contiene:

- `leaf-without-child-block.layout`;
- `continuation-lf.layout`;
- `continuation-crlf.layout`;
- un mod cliente vanilla-first que carga las tres fixtures una sola vez.

## Evidencia requerida

Ejecutar mediante el lifecycle autorizado de DayZ MCP o manualmente con
DayZDiag. Conservar el tramo RPT entre:

- `[LF_UI_PROBE_BEGIN]`
- `[LF_UI_PROBE_END]`

Los registros `LF_UI_PROBE_RESULT` informan el texto que devuelve
`ButtonWidget.GetText(out string)`. No existe un valor esperado codificado:
B20 solo puede fijarse después de observar ambos casos LF/CRLF en el engine.
No usar el parser offline como sustituto de esa observación.

# LF_ColorTest — Mini test de colores DayZ

## Qué hace
- F7 abre un panel con 10 rectángulos de colores ARGB conocidos
- Muestra el valor hex de cada color al lado
- Prueba `Widget.SetLV(0)` al abrir para ver si normaliza colores
- Guillermo: screenshot del panel y comparar con los hex esperados
- Segundo test: comentar la línea SetLV(0), recargar, screenshot de nuevo
- Comparando ambos screenshots sabremos el factor de oscurecimiento exacto

## Archivos

### config.cpp
```cpp
class CfgPatches
{
    class LF_ColorTest
    {
        units[] = {};
        weapons[] = {};
        requiredAddons[] = { "DZ_Scripts", "DZ_Data" };
    };
};

class CfgMods
{
    class LF_ColorTest
    {
        type = "mod";
        name = "LF_ColorTest";
        dir = "LF_ColorTest";
        class defs
        {
            class missionScriptModule
            {
                value = "";
                files[] = { "LF_ColorTest/scripts/5_Mission" };
            };
        };
    };
};
```

### $PREFIX$
```
LF_ColorTest
```

### scripts/5_Mission/LF_ColorTest.c

```csharp
// LF_ColorTest — Diagnóstico de color DayZ
// F7 para abrir/cerrar

class LF_ColorTestPanel
{
    protected static ref LF_ColorTestPanel s_Instance;
    protected Widget m_Root;
    protected bool m_Open;

    static void Toggle()
    {
        if (!s_Instance)
        {
            s_Instance = new LF_ColorTestPanel();
        }

        if (s_Instance.m_Open)
        {
            s_Instance.Close();
        }
        else
        {
            s_Instance.Open();
        }
    }

    void LF_ColorTestPanel()
    {
        m_Open = false;
    }

    void ~LF_ColorTestPanel()
    {
        if (m_Root)
        {
            m_Root.Unlink();
        }
    }

    void Open()
    {
        if (!m_Root)
        {
            Build();
        }

        if (!m_Root)
        {
            return;
        }

        // ===== TEST: SetLV(0) para normalizar colores =====
        // Primer test: con esta línea activa. Screenshot.
        // Segundo test: comentar esta línea. Screenshot.
        Widget.SetLV(0);
        Widget.SetTextLV(0);
        // ==================================================

        m_Root.Show(true);
        m_Open = true;
        Print("[ColorTest] Panel abierto. SetLV(0) aplicado.");
    }

    void Close()
    {
        if (m_Root)
        {
            m_Root.Show(false);
        }
        m_Open = false;
        Print("[ColorTest] Panel cerrado.");
    }

    protected void Build()
    {
        WorkspaceWidget ws = GetGame().GetWorkspace();
        if (!ws)
        {
            Print("[ColorTest] ERROR: workspace null");
            return;
        }

        // Root frame
        int rootFlags = WidgetFlags.VISIBLE;
        rootFlags = rootFlags | WidgetFlags.EXACTPOS;
        rootFlags = rootFlags | WidgetFlags.EXACTSIZE;
        m_Root = ws.CreateWidget(FrameWidgetTypeID, 100, 100, 420, 520, rootFlags, 0, 50000);
        if (!m_Root)
        {
            Print("[ColorTest] ERROR: no pudo crear root");
            return;
        }

        // Background
        int bgFlags = WidgetFlags.VISIBLE;
        bgFlags = bgFlags | WidgetFlags.EXACTPOS;
        bgFlags = bgFlags | WidgetFlags.EXACTSIZE;
        bgFlags = bgFlags | WidgetFlags.IGNOREPOINTER;
        bgFlags = bgFlags | WidgetFlags.STRETCH;
        Widget bgW = ws.CreateWidget(ImageWidgetTypeID, 0, 0, 420, 520, bgFlags, ARGB(240, 20, 20, 20), 0, m_Root);
        ImageWidget bg = ImageWidget.Cast(bgW);
        if (bg)
        {
            string texPath = "#(argb,8,8,3)color(1,1,1,1,CO)";
            bg.LoadImageFile(0, texPath);
            bg.SetColor(ARGB(240, 20, 20, 20));
        }

        // Title
        int txtFlags = WidgetFlags.VISIBLE;
        txtFlags = txtFlags | WidgetFlags.EXACTPOS;
        txtFlags = txtFlags | WidgetFlags.EXACTSIZE;
        txtFlags = txtFlags | WidgetFlags.IGNOREPOINTER;
        Widget titleW = ws.CreateWidget(TextWidgetTypeID, 10, 10, 400, 30, txtFlags, ARGB(255, 255, 255, 255), 0, m_Root);
        TextWidget title = TextWidget.Cast(titleW);
        if (title)
        {
            string titleText = "LF ColorTest — F7 para cerrar";
            title.SetText(titleText);
        }

        // 10 color swatches
        // Each: known ARGB → ImageWidget + TextWidget with hex label
        ref array<int> colors = new array<int>();
        ref array<string> labels = new array<string>();

        colors.Insert(ARGB(255, 255, 0, 0));
        labels.Insert("FF FF0000 Rojo puro");

        colors.Insert(ARGB(255, 0, 255, 0));
        labels.Insert("FF 00FF00 Verde puro");

        colors.Insert(ARGB(255, 0, 0, 255));
        labels.Insert("FF 0000FF Azul puro");

        colors.Insert(ARGB(255, 255, 255, 255));
        labels.Insert("FF FFFFFF Blanco");

        colors.Insert(ARGB(255, 128, 128, 128));
        labels.Insert("FF 808080 Gris 50%");

        colors.Insert(ARGB(255, 64, 64, 64));
        labels.Insert("FF 404040 Gris 25%");

        colors.Insert(ARGB(255, 52, 211, 153));
        labels.Insert("FF 34D399 Emerald 400");

        colors.Insert(ARGB(255, 248, 113, 113));
        labels.Insert("FF F87171 Red 400");

        colors.Insert(ARGB(255, 96, 165, 250));
        labels.Insert("FF 60A5FA Blue 400");

        colors.Insert(ARGB(128, 255, 255, 255));
        labels.Insert("80 FFFFFF Blanco 50% alpha");

        int i = 0;
        int yOffset = 50;
        int swatchH = 40;
        int gap = 6;

        for (i = 0; i < colors.Count(); i = i + 1)
        {
            int cy = yOffset + (i * (swatchH + gap));
            int col = colors.Get(i);
            string lab = labels.Get(i);

            // Color swatch
            int swFlags = WidgetFlags.VISIBLE;
            swFlags = swFlags | WidgetFlags.EXACTPOS;
            swFlags = swFlags | WidgetFlags.EXACTSIZE;
            swFlags = swFlags | WidgetFlags.IGNOREPOINTER;
            swFlags = swFlags | WidgetFlags.STRETCH;
            Widget swW = ws.CreateWidget(ImageWidgetTypeID, 10, cy, 80, swatchH, swFlags, col, 0, m_Root);
            ImageWidget sw = ImageWidget.Cast(swW);
            if (sw)
            {
                string swTex = "#(argb,8,8,3)color(1,1,1,1,CO)";
                sw.LoadImageFile(0, swTex);
                sw.SetColor(col);
            }

            // Label
            int lbFlags = WidgetFlags.VISIBLE;
            lbFlags = lbFlags | WidgetFlags.EXACTPOS;
            lbFlags = lbFlags | WidgetFlags.EXACTSIZE;
            lbFlags = lbFlags | WidgetFlags.IGNOREPOINTER;
            Widget lbW = ws.CreateWidget(TextWidgetTypeID, 100, cy, 310, swatchH, lbFlags, ARGB(255, 220, 220, 220), 0, m_Root);
            TextWidget lb = TextWidget.Cast(lbW);
            if (lb)
            {
                lb.SetText(lab);
            }

            // Log
            string logMsg = "[ColorTest] Swatch ";
            logMsg = logMsg + i.ToString();
            logMsg = logMsg + ": ";
            logMsg = logMsg + lab;
            Print(logMsg);
        }

        Print("[ColorTest] Panel construido con 10 swatches.");
    }
}

modded class MissionGameplay
{
    override void OnKeyPress(int key)
    {
        super.OnKeyPress(key);

        // F7 = KeyCode 65 (KC_F7)
        if (key == 65)
        {
            LF_ColorTestPanel.Toggle();
        }
    }
}
```

## Instrucciones para Guillermo

1. Crear estructura `@LF_ColorTest/Addons/LF_ColorTest/` con los archivos
2. Cargar el mod en el servidor local
3. En juego: pulsar F7
4. **Test A**: Screenshot del panel (con SetLV(0) activo)
5. Cerrar juego
6. Comentar las líneas `Widget.SetLV(0)` y `Widget.SetTextLV(0)` en el script
7. Recargar
8. **Test B**: Screenshot del panel (sin SetLV)
9. Copiar ambos screenshots + el .RPT

## Qué buscamos

Comparando Test A vs Test B:
- Si Test A muestra colores idénticos a los hex → `SetLV(0)` es la cura
- Si Test A sigue oscuro → el darkening es del renderer, no de LV
- En ambos: medir cuánto más oscuro es cada swatch vs el hex esperado
  (especialmente gris 50% — si 808080 se ve como 5C5C5C, sabemos el factor)

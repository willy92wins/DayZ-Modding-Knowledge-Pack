# Effects & Lights

Seaplane water spray effects, custom navigation lights and per-aircraft headlights.

_Extracted from `dayz-aviation/SKILL.md` 2026-07-07 (F3)._

### Custom nav lights

```cpp
class LlamaPlaneScript_NavLightLeft  extends PointLightBase { /* red wing tip */ };
class LlamaPlaneScript_NavLightRight extends PointLightBase { /* green wing tip */ };
class LlamaPlaneScript_NavLightTail  extends PointLightBase { /* white tail */ };

// In LlamaPlaneScript:
protected void CreateNavLights()
{
    vector lightPos = m_CachedLightWingLeft;  // from memory point light_wing_left
    m_NavLightLeft = LlamaPlaneScript_NavLightLeft.Cast(ScriptedLightBase.CreateLight(LlamaPlaneScript_NavLightLeft, lightPos));
    m_NavLightLeft.AttachOnObject(this, lightPos);
    // ... right, tail
}

protected void SetNavLightsVisible(bool visible)
{
    if (m_NavLightLeft) m_NavLightLeft.SetEnabled(visible);
    // ...
}
```

Per-aircraft `CarLightBase` for headlights:

```cpp
class LM_TigermothFrontLight extends CarLightBase
{
    void LM_TigermothFrontLight()
    {
        m_SegregatedBrightness  = 6;  m_SegregatedRadius  = 60; m_SegregatedAngle  = 80;
        m_SegregatedColorRGB    = Vector(0.9, 0.9, 1);
        m_AggregatedBrightness  = 10; m_AggregatedRadius  = 85; m_AggregatedAngle  = 90;
        m_AggregatedColorRGB    = Vector(0.9, 0.9, 1);
        FadeIn(0.3); SetFadeOutTime(0.25); SegregateLight();
    }
}
```

## Effects

### Seaplane water effects

Three emitter classes per position (Front=9 max emitters, Back=5, Side=3) extending `EffectSeaplaneWaterBase : EffectParticle`. Speed states (Slow/Medium/Fast) via `enum ESeaplaneSpeed`. `UpdateSpeedState(speed)` enables/disables emitters dynamically. `Update()` lerps intensity between states. Memory point positions updated via `m_PosUpdateTimer` + `CoordToParent`. Reusable for boats, amphibious vehicles, hovercraft.

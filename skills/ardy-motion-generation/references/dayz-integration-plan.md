# Plan de integración ARDY → DayZ (NO VERIFICADO)

Todo este documento es `[DESIGN]` — plan/hipótesis, no un procedimiento probado. Ningún paso de
esta cadena se ha ejecutado. Antes de escribir código de retargeting, releer esto completo y
decidir con el usuario si cada tramo merece un gate propio (R3: cambios que tocan >1 archivo de
mod/skill piden aprobación previa) — no encadenar los 4 pasos en una sola sesión sin checkpoints.

## Por qué existe este plan sin estar verificado

El caso de uso elegido para ARDY es locomoción de cuerpo completo del survivor (correr, saltar,
vaultear). Para que eso llegue a jugarse en DayZ hace falta una cadena de conversión que hoy no
existe. Documentar el plan ahora evita que una sesión futura tenga que re-derivar desde cero qué
falta, pero **no adelantar el veredicto de que la cadena funciona** — cada flecha de abajo es un
punto de fallo plausible no explorado.

## La cadena completa

```
ARDY .npz (skeleton "core", world-space joints + rotaciones + root + foot contacts)
  │
  │  [DESIGN] Paso 1 — parseo
  ▼
Import a Blender (script Python custom, numpy → armature)
  │
  │  [DESIGN] Paso 2 — el paso de mayor riesgo
  ▼
Retarget al OFP2_ManSkeleton (skeleton del player DayZ)
  │
  │  [EXACT — pipeline ya existente y verificado, ver dayz-animation-pipeline]
  ▼
Export .txa → Workbench → .anm (SEAnim / DayZATool)
  │
  ▼
Gate in-game
```

Solo el tramo final (`.txa` → `.anm` → in-game) tiene pipeline verificado — es el que ya usa
`dayz-animation-pipeline` para cualquier animación skeletal del player. Los pasos 1 y 2 son
territorio nuevo.

## Paso 1 — Parsear el `.npz`

Bajo riesgo técnico: es un array de numpy con estructura documentada (`posed_joints [T,J,3]`,
rotaciones, root, foot contacts). Escribir un script que lo cargue e inspeccione la forma real
del primer output generado ANTES de asumir el layout — el README no da el dtype/orden de ejes
exacto (¿XYZ o XZY? ¿Y-up o Z-up?), y DayZ usa Z-up (ver caveats de winding Blender→DayZ ya
documentados en `outputs/flip_winding.py` de otros proyectos). Confirmar con un `.npz` real, no
asumir la convención de otro pipeline.

## Paso 2 — Retarget al OFP2_ManSkeleton (el paso que puede matar el plan)

Esto es estructuralmente el mismo problema que ya resuelve (parcialmente, EXPERIMENTAL) la skill
`mixamo-retarget`: mapear un esqueleto genérico externo a la jerarquía específica de huesos que
espera DayZ. Diferencias que pueden hacerlo MÁS difícil que el caso Mixamo:

- El skeleton "core" de ARDY no tiene mapping oficial documentado a ningún formato de videojuego
  (ni FBX, ni BVH, ni SMPL) — hay que derivar el mapping bone-por-bone a mano, comparando nombres
  y jerarquía contra el mapa completo de `OFP2_ManSkeleton` en
  `<knowledge-notes>/dayz-animations-creatures-weapons.md` §3.10 (Core/spine,
  piernas, brazos, IK helpers, fingers).
- No se sabe el bone count exacto de "core" contra fuente oficial (el vídeo decía 27, no
  confirmado en research.nvidia.com ni GitHub) — contar los joints reales del primer `.npz`
  generado antes de intentar mapear.
- DayZ espera fingers, `RightHand_Dummy`/`LeftHand_Dummy` (helpers lod=2), y varios IK helpers
  (`*HandOrigin`, `*HandIKTarget`) que un skeleton "core" genérico de 27 huesos probablemente NO
  cubre — la locomoción de piernas/torso puede mapear razonablemente bien, pero manos/dedos
  probablemente necesiten quedarse en su pose de bind (sin animar) o heredar de otra fuente.

**Pregunta abierta a resolver con el primer test**: ¿el retarget solo de piernas+torso+columna
(dejando brazos/manos intactos o en additive) es suficiente para el objetivo real ("correr,
saltar, vaultear")? Si sí, el alcance del retarget se reduce mucho y el riesgo baja. Decidirlo
ANTES de intentar mapear manos/dedos, que es donde este tipo de retarget suele fallar más.

## Paso 3-4 — Export y pipeline final

Una vez exista una pose FK en el armature de Blender con nombres de huesos DayZ correctos, el
resto de la cadena (`.txa` → Workbench → `.anm`) es el pipeline YA verificado de
`dayz-animation-pipeline` — no hay nada nuevo que diseñar ahí, solo ejecutar el proceso conocido
(ver esa skill para el detalle del export).

## Alternativas si el retarget directo no compensa

Si el paso 2 resulta demasiado costoso para el beneficio real:

- Usar ARDY solo como **referencia visual** (playblast) para animar a mano en Blender/Cascadeur,
  en vez de intentar un retarget automático 1:1. Pierde el "tiempo real" pero evita el problema
  de mapping de esqueleto.
- Revisar si `Cascadeur` (ya evaluado en `ai-3d-pipeline/stage-05-animation.md`, veredicto MED
  condicional, único con soporte custom-skeleton + IK/FK + física) cubre mejor el mismo objetivo
  de locomoción sin el problema de esqueleto no estándar de ARDY.

## Cross-refs

- `<knowledge-notes>/dayz-animations-creatures-weapons.md` §3.10 — mapa completo de
  bones del player DayZ, necesario para diseñar el mapping del paso 2.
- `<knowledge-notes>/ai-3d-pipeline/stage-05-animation.md` — veredicto de
  aplicabilidad de ARDY y comparación con las otras 6 herramientas evaluadas.
- skill `mixamo-retarget` — mismo tipo de problema (retarget externo → DayZ), ya EXPERIMENTAL;
  leer qué falló o quedó pendiente ahí antes de repetir el mismo camino.
- skill `dayz-animation-pipeline` — pipeline `.txa`/Workbench/`.anm` de destino final.

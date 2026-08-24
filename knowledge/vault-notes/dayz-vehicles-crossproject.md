# DayZ vehicles — invariantes cross-proyecto

> Hub de dominio: las invariantes que **todo** vehículo DayZ (coche/quad/camión/moto) va a
> encontrar, con qué proyecto las ganó cada una. Existe porque el coste real de NO tener esto
> fue re-derivar el get-in de tripulación decenas de iteraciones en tres proyectos seguidos.
>
> El detalle ejecutable vive en la skill `dayz-vehicles` (checklist "INVARIANTS YOU WILL HIT" al
> principio del `SKILL.md` + `references/vehicle-structural-parity.md`). Esta nota es el registro
> durable cross-proyecto + el grafo. Regla de promoción: `[[evidence-led-memory]]` §"Promoción
> cross-proyecto".

## Proyectos de vehículo (orden cronológico)

- `[[10_Projects/LFQuad/project-brief|LFQuad]]` — quad (Banshee + física Croco). **Primero** en resolver
  get-in, wheel-sim, paridad estructural. La fuente de las invariantes 1, 3, 4.
- **SUB_BRZ** (rip→DayZ pipeline; sin folder de vault, vive en `<vehicle-import>\` + auto-memory
  `rip-vehicle-import-pipeline`) — re-sufrió get-in + componentNN dual-tag + winding. Probó que la invariante 1
  es la MISMA en un coche importado, no algo del quad.
- `[[10_Projects/MercedesAMGLF/project-brief|MercedesAMGLF]]` — Mercedes-AMG GT3 por proxys. Cerró la
  convención de body-proxys del engine (invariante 5) y re-confirmó get-in in-game.

## Las invariantes (qué proyecto la ganó · dónde está el detalle)

| # | Invariante | Ganada en | Detalle en skill |
|---|---|---|---|
| 1 | Get-in radial necesita **clase de script** `extends CarScript` que override `CrewCanGetThrough` (un `class X: CarScript` pelado hereda `Transport.CrewCanGetThrough()=false`, `transport.c:493` → la acción se filtra y nunca aparece) | LFQuad D34 → re-sufrido SUB_BRZ + Mercedes | `vehicle-structural-parity.md` "Crew get-in" |
| 2 | El módulo de script tiene que **cargar** (`CfgMods files[]` sin back-slash / sin path `.p3d` que dé `*.p3d.p3d`) o la clase nunca bindea — fallo silencioso | SUB_BRZ / Mercedes | SKILL §"Binding del script" |
| 3 | Geometry LOD necesita named property **`class=vehicle`** o las ruedas no simulan (`WheelCountPresent()==0`, sin error RPT) | LFQuad 2026-05-27 (SP-027) | `vehicle-structural-parity.md` |
| 4 | Asientos y hubs deben llevar **`componentNN` (dual-tag)** o son islas de colisión invisibles → spawn blocker / sin asiento | SUB_BRZ s7 | "componentNN DUAL-TAG" |
| 5 | Crew/wheel proxies en **ViewGeo Y FireGeo**; triángulo del proxy = frame identidad del engine `R=((-1,0,0),(0,0,1),(0,1,0))` model-space (NO `rotation=None` de py3d) | Mercedes (body-proxys) | parity + `rip-import.md` |
| 6 | Signo de `angle1` de rueda: **medir el eje en el `.p3d` ANTES** de fijarlo (check offline predice el giro invertido sin in-game) | LFQuad shipping | `build-packaging-and-debug.md` §2-3 |
| 7 | **Una bujia vital por coche**: vanilla pone SparkPlug Y GlowPlug vital por defecto (un `CarScript` pelado exige las dos, `carscript.c:2004/2011`); petrol overridea `IsVitalGlowPlug()->false` (`civiliansedan.c:363`), diesel `IsVitalSparkPlug()->false` (`offroad_02.c:389`); declarar solo la vital en `attachments[]` + atacharla en `OnDebugSpawn`. "No arranca" con SparkPlug puesto = el GlowPlug sin overridear, NO un requisito eliminado | SUB_BRZ 2026-06-28 | SKILL #8 + `vehicle-config-and-modelcfg.md` sec 15 |

## Por qué existe esta nota (la lección de proceso)

El conocimiento del get-in **estaba capturado** en la skill (SP-007 pose, SP-017 wheelPresent), pero
llegó **tarde**: la victoria de LFQuad no se promovió a invariante de dominio cuando se ganó, así que cada
proyecto siguiente la re-derivó. El fix no era "más memoria" ni "más enlaces" — era **promover la
invariante el día que se gana** y ponerla donde el siguiente proyecto la lee **al arrancar** (checklist
preflight), no como triage tras el fallo. Regla codificada en `[[evidence-led-memory]]` §"Promoción
cross-proyecto"; cola de patches a skills read-only en `[[skill-patches-pending]]`.

## 2026-06-29 — Auditoría skills vs LFQuad/Mercedes/Subaru (consolidación)

Contraste del conocimiento de los 3 coches vs las skills. Confirmado: no fue fallo de captura sino de findability/timing + destino equivocado (promociones de mayo a `dayz-model-pipeline`, luego retirado). Acciones aplicadas a `dayz-vehicles/SKILL.md`: copiloto ViewGeo inward+flags `0x02000000` → **preflight #4**; bloque **METHOD** (parity-first / in-game-es-el-gate / crew-probe-FIRST); ownership completado con el actuador `OnInput`; +LL-103/LL-104/OnDebugSpawn/editor de encaje en `references/vehicle-config-and-modelcfg.md`. Vault: LL-166 + LL-175 escritas; `skill-patches-pending` reconciliado (SP-032/036 → applied; SP-041 closed no-issue; SP-040(b) `GetSteering` aplicado al plugin `dayz-animation-pipeline` vía Codex). Reafirmado (ya en §Relacionado): **`dayz-vehicles` es user-skill editable, NO plugin** — los SP-032/036 estaban mal aparcados como "plugin read-only". Detalle: [`30_Sessions/2026-06-29-dayz-vehicles-skill-audit-consolidation.md`](../30_Sessions/2026-06-29-dayz-vehicles-skill-audit-consolidation.md).

## Relacionado

- `[[dayz-capacidades-verificadas]]` — veredictos de feasibility DayZ + gotchas de Enforce/config.
- Skill `dayz-vehicles` (escribible directo en `~/.claude/skills/`, NO plugin read-only) — destino de
  promoción de toda invariante de vehículo nueva.
- [[dayz-model-pipeline]] — ensamblado de LODs/proxys/named-properties donde nacen las invariantes 3-5.
- [[evidence-led-memory]] — §"Promoción cross-proyecto", la regla de proceso que esta nota encarna.
- [[skill-patches-pending]] — cola de patches a skills read-only (SP-017/SP-027 son de vehículo).
- [[20_Knowledge/lessons-learned|lessons-learned]] — lecciones durables de los proyectos LFQuad/SUB_BRZ/Mercedes citados arriba.
- [[10_Projects/MercedesAMGLF/project-brief|MercedesAMGLF]] — proyecto que cerró la invariante 5 (body-proxys).

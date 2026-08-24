# Pre-CAMBIO-0 canonical path — archived snapshot

> Historical snapshot copied from `rip-vehicle-import/SKILL.md` on 2026-08-05. It is not the happy path for a new family B asset.

## Checklist DAY-1 (coche nuevo — todo offline, sin tocar geometría)

1. Unzip a `<vehicle-import>\rip\media\cars\<car>\` (junction si viene de otro lado). La
   `_library` de COCHES compartida ya está en `rip\media\cars\_library\` (verificar que
   los materialbins que el coche referencia resuelven — patrón 13/13 del BRZ).
2. `profiles\<car>.json` desde la plantilla (ver `references/profile-schema.md`): bloque
   `source` + budgets `intake` + policies. NO copiar las `exceptions` quirúrgicas del BRZ.
3. Step `manifest`: inventario (INCLUDE/EXCLUDE/SHADOW `__slod`/far-LOD-shells por bitmask
   `LODs=` /mirror-gaps RF `[ -f ]` probe) → `source_inventory.json`. Trampas fijas:
   parte custom solo-`__slod` (la visible es la estándar) · `*wide*` = flares bolt-on
   ENCIMA del shell (`body_a` SIEMPRE incluido — quitarlo borra el techo) ·
   `interior_a`-far-shell (LODs sin bits {0,1}) NUNCA como geometría close-view ·
   suspension/undercarriage SE INCLUYEN (re-posadas; las ruedas se apoyan visualmente) ·
   piezas MÓVILES (puertas/capó/maletero) = models PROPIOS ya cortados en el rip con eje
   en `Locators.xml` → clasificarlas como LANE PROPIA desde el day-1, NUNCA fundirlas al
   body ni planificar recorte manual (ver sección 2026-07-17 abajo).
4. Material map por-mesh (`rip_material_map.py`): TYPE por carpeta del materialbin
   (el NOMBRE de instancia miente — rollcage "leather_MGL" es METAL). Multi-material =
   normal (50/84 en BRZ) → por-mesh obligatorio, per-part es solo hint.
5. Color: `ManufacturerColors.bin` entry[0] (decoder `decode_color2.py`) — NUNCA a ojo.
6. Masa/drivetrain/reparto: stats públicos FH6 (game8/kudosprime/calculators.games) —
   el GameDB va cifrado (no minarlo, no subirlo a backends de terceros). Cross-check
   wheelbase de `Locators.xml` vs specs reales = valida ejes/unidades.
7. Dims/memoria: `Locators.xml` `SceneTransform _41/_42/_43` = x/y/z (y up, z long).
8. Gate intake: `lod_plan.json` (LOD autorado por pieza que cumpla el budget) — FAIL si
   ninguna combinación entra en presupuesto. Decisiones pendientes (variante
   stock/widebody, plazas, extras) → `pending_decisions[]` y SE PREGUNTAN, sin defaults.

## Pipeline canónico (12 pasos; steps de `import_car.py`)

| # | Paso | Regla dura | Gate |
|---|---|---|---|
| 1 | Intake + truth maps (day-1 arriba) | sin defaults silenciosos | inventory + NEEDS_DECISION |
| 2 | Budgets + lod_plan | visual ≤ ~120k caras · VP subset ≤16k resolved · shadow ≤5k · uniqUV>1 · dup_rate<2% | intake gate FAIL-loud |
| 3 | Import multi-LOD Blender headless | transform neto `(−Fx, Fy+Y0, −Fz)` det+1, verificado ≥3 anclas (G0 fail-stop) | G0 |
| 4 | Normalización topológica | dedup payload-aware PRIMERO → repair minoría flood-fill MAYORÍA (allowlist censada; conflicto nuevo = FAIL) → normales smooth(+cross) del winding FINAL. PROHIBIDO: flip global, orient-a-oráculo, fix desde fotos | Gb/Gb+ + winding_differential |
| 5 | Arquitectura visual | shell real LOD0 (paint hiddenSelections + luces) + chunks proxy <65535 resolved + `prox_int` dedicado (full res1.0 + subset 1100) + shadow dissolve 40° + ladder autorada por distancia | budgets + lod_semantics |
| 6 | Glass (subpipeline) | panes dobles del rip CONSERVADOS (par ext/int legítimo) · material clon vanilla `glass.rvmat` (α 0.22-0.32, noZwrite) · single-sided · twins/double-side = excepción MEDIDA · cierre estructural SOLO con gap demostrado por sonda multiángulo · knobs BRZ (E_flip/C1/sunk) = profile, no doctrina | glass_occ + probes |
| 7 | Estructural (`rip_p3_structural`) | componentNN DUAL-TAG (hubs/seats 100% overlap) · bone-companion por attachment proxy · ViewGeo seats INWARD + flags 0x02000000 · `#Mass#` SOLO Geometry · `refill` (no fuelpoint) · hitpoints==firegeo dmgzones==config | verify_rip_car U+P + roundtrip_structural + positive control sedan |
| 8 | Proxies | path SIN `.p3d` (default; hay contraejemplo registrado → ante duda, verificar contra control) · frame por lado: x<0 `((-1,0,0),(0,0,1),(0,1,0))`, x>0 `((1,0,0),(0,0,-1),(0,1,0))` · companions `wheel_X_Y` en visual+View+Fire · geometría MODEL-SPACE sin centrar · NUNCA `add_proxy` sobre uno existente (pierde frame) | proxy identity checks |
| 9 | Config/script (lane Codex) | `<MOD>_Base.c` extends CarScript SIEMPRE (CrewCanGetThrough/GetAnimInstance/GetSeatAnimationType; sin ella get-in JAMÁS aparece) · CfgMods `dir=` + backslashes · SimulationModule HEREDAR (no re-declarar) · slots vanilla `CivSedanWheel_*` · petrol = SparkPlug vital + GlowPlug→false · OnDebugSpawn COMPLETO (kits idénticos mod-vs-control) · matriz paridad PAR-001..017 | CfgConvert + parity diff |
| 10 | Texturas | TYPE→rvmat de tabla fleet · solo carpaint en selección paintable · PLASTIC NUNCA re-tipado (flares pintados) · `_co` solid UV-invariant + swatch por TEXCOORD2 · cabina de FUENTE REAL (materialbins `_library` + UI `TOY_*`; jamás paleta inventada) · specular alto amplifica artefactos del `_nohq` | TYPEMAT unknown=FAIL + surface_integrity |
| 11 | Deploy | TRANSPLANT (jamás pisar los struct LODs del desplegado) · staging atómico + build identity · `.bak` FUERA del árbol compilable · `-Build -PackOnly` (PackOnly solo = PBO stale) · `-include` REEMPLAZA la copy-list (dropea .paa/.rvmat = white car) | G7 0-missing + identity + perf_budget |
| 12 | Test | suite offline → `NEEDS_INGAME` → smoke MCP (spawn + capturas estándar + raycast + get-in probe) → drive ladder → **usuario: OK estético + feel, UNA pasada agrupada** | vehicle_smoke JSONL (INGAME_PASS real, nunca prompt-only) |

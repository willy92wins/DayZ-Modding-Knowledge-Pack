# Pre-CAMBIO-0 canonical path — archived snapshot

> Historical snapshot copied from `rip-vehicle-import/SKILL.md` on 2026-08-05. It is not the happy path for a new family B asset.

## DAY-1 Checklist (new car — all offline, without touching geometry)

1. Unzip to `<vehicle-import>\rip\media\cars\<car>\` (junction if coming from elsewhere). The
   shared CARS `_library` is already in `rip\media\cars\_library\` (verify that
   materialbins referenced by the car resolve — BRZ 13/13 pattern).
2. `profiles\<car>.json` from the template (see `references/profile-schema.md`): block
   `source` + budgets `intake` + policies. DO NOT copy surgical `exceptions` from the BRZ.
3. Step `manifest`: inventory (INCLUDE/EXCLUDE/SHADOW `__slod`/far-LOD-shells by bitmask
   `LODs=` /mirror-gaps RF `[ -f ]` probe) → `source_inventory.json`. Fixed traps:
   custom part only-`__slod` (visible one is standard) · `*wide*` = bolt-on flares
   ON TOP of shell (`body_a` ALWAYS included — removing it deletes the roof) ·
   `interior_a`-far-shell (LODs without bits {0,1}) NEVER as close-view geometry ·
   suspension/undercarriage ARE INCLUDED (re-posed; wheels rest visually) ·
   MOVABLE parts (doors/hood/trunk) = OWN models already cut in the rip with axis
   in `Locators.xml` → classify them into their OWN LANE from day-1, NEVER merge them into
   body or plan manual cut (see section 2026-07-17 below).
4. Per-mesh material map (`rip_material_map.py`): TYPE by materialbin folder
   (instance NAME lies — rollcage "leather_MGL" is METAL). Multi-material =
   normal (50/84 on BRZ) → per-mesh mandatory, per-part is only a hint.
5. Color: `ManufacturerColors.bin` entry[0] (decoder `decode_color2.py`) — NEVER by eye.
6. Mass/drivetrain/distribution: FH6 public stats (game8/kudosprime/calculators.games) —
   GameDB is encrypted (do not mine it, do not upload to third-party backends). Cross-check
   wheelbase from `Locators.xml` vs real specs = validates axes/units.
7. Dims/memory: `Locators.xml` `SceneTransform _41/_42/_43` = x/y/z (y up, z long).
8. Intake gate: `lod_plan.json` (authored LOD per part meeting budget) — FAIL if
   no combination fits budget. Pending decisions (stock/widebody
   variant, seats, extras) → `pending_decisions[]` and MUST BE ASKED, no defaults.

## Canonical pipeline (12 steps; `import_car.py` steps)

| # | Step | Hard rule | Gate |
|---|---|---|---|
| 1 | Intake + truth maps (day-1 above) | no silent defaults | inventory + NEEDS_DECISION |
| 2 | Budgets + lod_plan | visual ≤ ~120k faces · VP subset ≤16k resolved · shadow ≤5k · uniqUV>1 · dup_rate<2% | intake gate FAIL-loud |
| 3 | Import multi-LOD Blender headless | net transform `(−Fx, Fy+Y0, −Fz)` det+1, verified ≥3 anchors (G0 fail-stop) | G0 |
| 4 | Topological normalization | payload-aware dedup FIRST → MAJORITY flood-fill minority repair (censused allowlist; new conflict = FAIL) → smooth(+cross) normals from FINAL winding. FORBIDDEN: global flip, orient-to-oracle, fix from photos | Gb/Gb+ + winding_differential |
| 5 | Visual architecture | real shell LOD0 (paint hiddenSelections + lights) + proxy chunks <65535 resolved + dedicated `prox_int` (full res1.0 + subset 1100) + shadow dissolve 40° + distance-authored ladder | budgets + lod_semantics |
| 6 | Glass (subpipeline) | rip double panes PRESERVED (legitimate ext/int pair) · vanilla clone material `glass.rvmat` (α 0.22-0.32, noZwrite) · single-sided · twins/double-side = MEASURED exception · structural closure ONLY with gap demonstrated by multi-angle probe · BRZ knobs (E_flip/C1/sunk) = profile, not doctrine | glass_occ + probes |
| 7 | Structural (`rip_p3_structural`) | componentNN DUAL-TAG (hubs/seats 100% overlap) · bone-companion per attachment proxy · ViewGeo seats INWARD + flags 0x02000000 · `#Mass#` Geometry ONLY · `refill` (no fuelpoint) · hitpoints==firegeo dmgzones==config | verify_rip_car U+P + roundtrip_structural + positive control sedan |
| 8 | Proxies | path WITHOUT `.p3d` (default; registered counterexample exists → when in doubt, verify against control) · per-side frame: x<0 `((-1,0,0),(0,0,1),(0,1,0))`, x>0 `((1,0,0),(0,0,-1),(0,1,0))` · companions `wheel_X_Y` in visual+View+Fire · non-centered MODEL-SPACE geometry · NEVER `add_proxy` over an existing one (loses frame) | proxy identity checks |
| 9 | Config/script (lane Codex) | `<MOD>_Base.c` ALWAYS extends CarScript (CrewCanGetThrough/GetAnimInstance/GetSeatAnimationType; without it get-in NEVER appears) · CfgMods `dir=` + backslashes · INHERIT SimulationModule (do not re-declare) · vanilla slots `CivSedanWheel_*` · petrol = vital SparkPlug + GlowPlug→false · COMPLETE OnDebugSpawn (identical mod-vs-control kits) · parity matrix PAR-001..017 | CfgConvert + parity diff |
| 10 | Textures | TYPE→rvmat from fleet table · carpaint only on paintable selection · PLASTIC NEVER re-typed (painted flares) · `_co` solid UV-invariant + swatch via TEXCOORD2 · REAL SOURCE cabin (`_library` materialbins + `TOY_*` UI; never invented palette) · high specular amplifies `_nohq` artifacts | TYPEMAT unknown=FAIL + surface_integrity |
| 11 | Deploy | TRANSPLANT (never overwrite struct LODs of deployed) · atomic staging + build identity · `.bak` OUTSIDE compilable tree · `-Build -PackOnly` (PackOnly alone = stale PBO) · `-include` REPLACES copy-list (drops .paa/.rvmat = white car) | G7 0-missing + identity + perf_budget |
| 12 | Test | offline suite → `NEEDS_INGAME` → smoke MCP (spawn + standard captures + raycast + get-in probe) → drive ladder → **user: aesthetic + feel OK, ONE bundled pass** | vehicle_smoke JSONL (real INGAME_PASS, never prompt-only) |

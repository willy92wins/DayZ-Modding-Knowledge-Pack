# Auto-UV tool survey (researched 2026-07-16)

Question: best automatic/AI tool for livery-template UV atlases on hard-surface
vehicle meshes, local (RTX 3090) and scriptable. Full agent reports in the vault
session note (30_Sessions/2026-07-16-*uv*). Condensed verdicts:

| Tool | Verdict for this gate |
|---|---|
| **Blender 4.3+ SLIM (MINIMUM_STRETCH) + own seams** | WINNER as backbone. Solver is production-grade; the "intelligence" (seams) must be supplied — this skill's region-growing supplies it. Free, 100% bpy-scriptable. |
| **PartUV** (SIGGRAPH Asia 2025) | Only real UV AI with code+weights. Piloted and beaten 3–4× on island count here — see `partuv-pilot.md`. Keep as chart-source experiment. |
| **RizomUV VS** (€149.90 perpetual) | Best commercial fallback: true headless (`-cfi` Lua + RizomUVLink Python, Smithsonian pipeline). Livery look needs Size-Limiter tuning; test the 15-day trial before buying (historic script-mode regression bug). |
| Ministry of Flat | Discarded BY PHILOSOPHY: its author optimizes packing via MORE islands — opposite of this gate. Free-commercial, CLI, but wrong objective. |
| xatlas / UVAtlas | Chart-growers for lightmaps; confetti by design (this is what TRELLIS.2/Hunyuan3D call internally). UVAtlas in maintenance mode. |
| BFF / OptCuts / SLIM-paper | Solvers/cutters minimizing distortion or seam length — not semantic. BFF great flattener once seams exist (organic focus). |
| Houdini Labs AutoUV | Cluster method can cap island count, but Apprentice license can't export usefully — only worth it if already paying Houdini. |
| Nuvo / Flatten Anything / AUV-Net / SeamGPT / ArtUV / SeamGen | Papers without usable code+weights (as of 2026-07). Watch SeamGen/SATO. |
| PartField / P3-SAM (Hunyuan3D-Part) | AI mesh segmentation usable as seam source (P3-SAM shows vehicles). DIY route: segment labels → boundary edges → Mark Seam → SLIM. |
| Cloud (Tripo/Meshy/Rodin/fal.ai) | No cloud endpoint produces legible-island UVs; Tripo's own blog admits "exploded confetti". fal.ai has retopo (`hunyuan-3d/v3.1/smart-topology`, ~$0.75/gen) but no UV-unwrap endpoint. TRELLIS.2 retexture and Hunyuan3D-Paint both call bare xatlas — a hand-made UV is IGNORED by TRELLIS.2's pipeline. |
| Quad Remesher (€) | Retopo only (no UVs), quality edge flow helps seams; visual-destination retopo is user-gated. |

Bottom line: in 2026 there is still no mature "AI UV unwrapper" product. Production
answer = classic solver + smart seams, where "smart" is deterministic geometry
analysis (this skill) or an AI segmenter feeding the same solver.

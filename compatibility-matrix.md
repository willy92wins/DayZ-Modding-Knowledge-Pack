# Compatibility matrix

Reviewed: **2026-07-24**
Target stable build: **DayZ PC 1.29.0.163451** (released 2026-07-15)

This matrix records what was actually checked. It does not claim that every
workflow was run end-to-end on this build during r21 Phase 01.

## Verification levels

- `runtime_verified`: observed in a real DayZ run; the evidence may predate
  this matrix unless the row says otherwise.
- `source_verified`: exact contracts checked against local vanilla or project
  source for the target build.
- `offline_tested`: exercised with deterministic local tests, without DayZ.
- `cross_checked`: reconciled against more than one source or project corpus.
- `historical`: retained from dated project evidence and needs revalidation
  when reused.
- `unverified`: no sufficient evidence; never interpret as compatible.

## Skill coverage

| Skill | Level on 1.29.0.163451 | Required or recommended dependencies | Breaking changes / limits | Evidence |
|---|---|---|---|---|
| `ai-3d-to-dayz` | `cross_checked` | AI generator; Blender; `dayz-model-pipeline`; texture pipeline; `dayz-pbo-build` | No end-to-end runtime run in this phase. Generator APIs and Blender add-ons move independently of DayZ; recheck before use. | `skills/ai-3d-to-dayz/SKILL.md`; r21 source reconciliation |
| `ardy-motion-generation` | `historical` | WSL2; NVIDIA GPU/CUDA; Python; PyTorch 2.6.0; CMake ≥3.15; C++17; Blender/DayZ animation pipeline | ARDY environment was not rebuilt in this phase. Pin the documented ML stack; current compatibility beyond the cited project evidence is `unknown`. | `skills/ardy-motion-generation/SKILL.md:63-84` |
| `blender-animation` | `cross_checked` | Blender with `bpy`; optional Blender MCP; DayZ animation export tooling | DayZ 1.29 changed Animation Editor workflows: live debug, TXA re-import and save flow. Blender-to-DayZ export remains project-dependent and was not rerun here. | `skills/blender-animation/SKILL.md`; official 1.29 tool changelog |
| `dayz-aviation` | `source_verified` + historical runtime evidence | `enforce-script-reference`; `dayz-model-pipeline`; `dayz-vehicles`; `dayz-test-ingame` | Source contracts were checked on 1.29; each flight model still requires real-input runtime validation. No new universal aircraft API guarantee is asserted. | `skills/dayz-aviation/SKILL.md:26-31`; local `P:\scripts` build 1.29.0.163451 |
| `dayz-basebuilding` | `source_verified` | `enforce-script-reference`; `dayz-model-pipeline`; `rigorous-data-audit`; `dayz-pbo-build` | 1.29 known issue: navmesh does not update when fence gates open/close. Persistence and part-ID assumptions must be rechecked for each structure. | `skills/dayz-basebuilding/SKILL.md`; official 1.29 changelog |
| `dayz-characters` | `historical` | Blender; `OFP2_ManSkeleton`; `dayz-model-pipeline`; animation pipeline; `dayz-pbo-build` | No full humanoid import was rerun on 1.29. Skeleton, scale and deformation claims remain dated project evidence until revalidated. | `skills/dayz-characters/SKILL.md`; r21 source reconciliation |
| `dayz-feature-spec` | `offline_tested` | project spec, plan, task/handoff and source evidence | Engine-independent process skill. New injected-object Forward Contract is source-verified; it does not itself prove runtime behavior. | `skills/dayz-feature-spec/SKILL.md:46-59`; `GAMEMASTER_SOURCE/tools/gm/service.py:209-218` |
| `dayz-mcp-verify` | `source_verified` + historical runtime evidence | public `dayz_test_run` / `dayz_test_stop`; configured DayZ MCP bridge; `dayz-test-ingame` | The bridge is not bundled. Player UI, door interaction, inventory use and firing remain manual. This phase inspected lifecycle code but did not start DayZ. | `skills/dayz-mcp-verify/SKILL.md:33-64`; `DAYZ_MCP_SOURCE/server.py:915-995` |
| `dayz-pbo-reverse-engineering` | `offline_tested` | lawful PBO access; Mikero ExtractPbo or equivalent; optional p3d tooling | Tool output and legal permissions vary. Binarized/obfuscated content may limit recovery; no third-party payload may be redistributed automatically. | `skills/dayz-pbo-reverse-engineering/SKILL.md`; `THIRD_PARTY_NOTICES.md` |
| `dayz-test-ingame` | `source_verified` + `offline_tested` | DayZ Tools; AddonBuilder; DayZDiag; managed lifecycle; optional CF/VPP | Generated launcher parser and secret tests pass. Runtime launch was intentionally not run in this phase. 1.29 mod/tool changes require dependency checks before reuse. | `skills/dayz-test-ingame/SKILL.md`; `tests/packctl/test_dayz_test_template_contract.py` |
| `dayz-vehicles` | `source_verified` + historical runtime evidence | `enforce-script-reference`; `dayz-model-pipeline`; `dayz-pbo-build`; `dayz-test-ingame` | Several advanced proxy/winding rules are explicitly offline-only or pending in-game; preserve those labels. 1.29 vehicle fixes do not prove custom vehicle compatibility. | `skills/dayz-vehicles/SKILL.md:110-118,256-264`; local vanilla vehicle/action sources |
| `dayz-weapons` | `historical` + `source_verified` | `enforce-script-reference`; `dayz-model-pipeline`; `dayz-animation-pipeline`; `dayz-pbo-build` | 1.29 Animation Editor workflow changed; experimental notes reported some weapon animation playback issues. Entity contracts retain project evidence but must be tested on the target build. | `skills/dayz-weapons/SKILL.md:32-64`; official 1.29 tool changelog |
| `rip-vehicle-import` | `offline_tested` + historical runtime evidence | `dayz-vehicles`; VehicleImport scripts; Blender; py3d; build/test pipeline | Winding-lineage and material-override focused tests pass. Broader profile test still has a known unrelated `builder.occ_struct` failure; no new vehicle was run in-game in this phase. | `skills/rip-vehicle-import/SKILL.md:251-265`; focused tests under the local `VehicleImport` evidence root |
| `rigorous-data-audit` | `cross_checked` | real code/data paths; independent evidence; runtime validation for release | Audit can prove source invariants, not runtime safety by itself. Its multi-angle procedure references subagents, but r21 execution was explicitly single-agent. | `skills/rigorous-data-audit/SKILL.md:76-77,132-182`; new r21 references |

## Stable-build evidence and update policy

- The exact local game/scripts baseline used for source checks is
  `1.29.0.163451`.
- The [official stable changelog](https://forums.dayz.com/topic/266379-stable-update-129/)
  identifies Steam Stable `1.29.163451`, released 2026-07-15.
- Before a DayZ stable update is adopted, pin its build, diff relevant vanilla
  contracts, rerun offline gates, then batch representative in-game tests.
- A row only advances to `runtime_verified` with a dated, reproducible test
  artifact. Absence of a listed breaking change means `unknown`, not “none”.
- Dependencies with their own release cycles must be pinned per project. This
  pack does not promise compatibility with an unpinned VPP, Expansion,
  TraderPlus, TraderX, Blender or ML-tool version.

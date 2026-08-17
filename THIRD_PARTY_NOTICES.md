# Third-party notices

The repository-level [MIT license](LICENSE) covers original pack material.
Components listed below retain their own notices and licenses.

## Included component

### py3d

- Component: `tools/py3d/`
- Upstream: [KoffeinFlummi/py3d](https://github.com/KoffeinFlummi/py3d)
- License: MIT
- Copyright: © 2017 Felix Wiegand
- Local license: [`tools/py3d/LICENSE`](tools/py3d/LICENSE)

The pack contains a DayZ-specific fork. The upstream copyright and license
must remain with redistributions of that component.

## Adaptation attribution

### GitHub Spec Kit

`skills/dayz-feature-spec/` adapts the general idea of specification-driven
development from [github/spec-kit](https://github.com/github/spec-kit)
(MIT). The DayZ workflow, Forward Contract and verification gates in this
pack are original adaptations; no Spec Kit executable is bundled.

### BI PAA LZSS variant

`tools/dayz-3d-viewer` reimplements the Bohemia Interactive LZSS variant
used on non-DXT PAA mipmaps (ring buffer 4096, init 0x20), as documented
on the BI Community Wiki. No third-party C source is bundled.

### img2threejs

`skills/blender-visual-review/` and the detail-scan protocol in
`skills/blender-assembly/SKILL.md` adapt staged-review methodology from
[img2threejs/img2threejs](https://github.com/img2threejs/img2threejs) commit
`9a8ecf129a58c1b557a1f03f7727f6295672cd51` (v1.4.3, Apache-2.0).
`correction_loop.py` is a verbatim copy; `vr_delta.py` is an adaptation.
Per-file provenance is in
`skills/blender-visual-review/references/NOTICE-img2threejs.md`.

### Dev-GOM blender-toolkit

`skills/mixamo-retarget/scripts/retargeting.py` and `bone_matching.py` are
adapted from [Dev-GOM/claude-code-marketplace](https://github.com/Dev-GOM/claude-code-marketplace)
`plugins/blender-toolkit` (Apache-2.0). Relative imports were flattened and
the logger replaced with stdlib logging. The original WebSocket CLI and UI
panel are not included.

### SE2Dev io_anim_seanim

`tools/dayz-animation-formats/` implements a strict SEAnim v1 contract and
uses [SE2Dev/io_anim_seanim](https://github.com/SE2Dev/io_anim_seanim) at
commit `dffe313b635ce8940264201f25db9e68f4486d7e` as an independent
reader/writer oracle. That project is MIT-licensed. No SE2Dev source is bundled
in the tool.

## First-party binary fixtures

The animation fixtures and the three ODOL v53/v54/v55 fixtures under
`tools/` contain first-party semantic/asset data authorized by the user for
public redistribution on 2026-07-25. Their byte sizes, SHA-256 hashes and
origins are tracked beside the fixtures. They contain no DayZ game data or
external backend source.

## Validation-only dependency

The release process validates skills with the pinned `skills-ref` tool from
[agentskills/agentskills](https://github.com/agentskills/agentskills), commit
`38a2ff82958afee88dadf4831509e6f7e9d8ef4e` (Apache-2.0). It is a development
dependency and is not included in the release payload.

## Research-only sources excluded from the payload

The following projects were inspected as evidence or comparison corpora. No
source code, database, binary, asset or documentation payload from them is
redistributed by this pack:

| Project | Role | Observed license |
|---|---|---|
| [Borcioo/dayz-labs](https://github.com/Borcioo/dayz-labs) | MCP, build and CE tooling research | GPL-3.0 |
| [ZeripeDaniel/Lake-Dayz-MCP](https://github.com/ZeripeDaniel/Lake-Dayz-MCP) | public MCP protocol and API-database research | code: GPL-3.0; derived database: DPL-ND |
| [StarDZ-Team/Dayz-Modding-Skills](https://github.com/StarDZ-Team/Dayz-Modding-Skills) | skill-structure comparison and negative evaluation fixtures | MIT |
| [VanillaPlusPlus/VPP-Admin-Tools](https://github.com/VanillaPlusPlus/VPP-Admin-Tools) | UI/layout comparison corpus | MIT |
| [MrClock8163/Arma3ObjectBuilder](https://github.com/MrClock8163/Arma3ObjectBuilder) | proxy-frame and RTM external oracle | GPL-3.0-or-later |
| [ScripyZz/BisDLL-Arma-3](https://github.com/ScripyZz/BisDLL-Arma-3/tree/5600bad995c89154b4f6700ef087f86ef4c49315) | compatible ODOL parser backend; loaded externally through a pinned manifest | no license/redistribution grant observed |
| DayZ Expansion, TraderPlus and TraderX | UI/layout comparison corpora | not redistributed; license not asserted here |
| [mrdoob/three.js](https://github.com/mrdoob/three.js/tree/r128) | runtime dependency of the `rip-vehicle-import` classify viewer (`three.min.js`, `GLTFLoader.js`, `OrbitControls.js`, r128 UMD) | MIT; **not redistributed** — the viewer's README says where to fetch them |
| [mrdoob/three.js](https://github.com/mrdoob/three.js/tree/r160) | runtime dependency of `tools/dayz-3d-viewer` generated HTML (`three.module.js`, `GLTFLoader.js`, `OrbitControls.js`, r160 ESM via jsDelivr `three@0.160.0`) | MIT; **not redistributed** — the tool README names the CDN URL |
| [mrdoob/three.js](https://github.com/mrdoob/three.js/tree/r147) | runtime CDN of `dayz-p3d-inspector` and `dayz-proxy-align` generated HTML (UMD r0.147.0, last UMD examples build) | MIT; **not redistributed** |
| Mixamo / Adobe Mixamo | mocap / FBX / character assets referenced by `mixamo-retarget` | not redistributed; only the retargeting flow ships |
| Dabs Framework, LBmaster Groups | UI/script pattern research cited by `dayz-ui-development` | not redistributed; license not asserted here |
| LM_Planes (Steam workshop 3730564764) | Enforce/config pattern extraction in `enforce-script-reference` | not redistributed; workshop terms |
| DayZ Modders Discord via [AnswerOverflow](https://www.answeroverflow.com) | Community snippets in `dayz-ui-development` and `dayz-particles`, spot-checked against vanilla | Discord/AnswerOverflow terms; snippets rewritten against `P:\scripts` |
| IMPWMODPart2, DoorLockSystem | Audio prior-art citations in `dayz-sound-system` | not redistributed |
| DayZ game scripts, tools and data | API and runtime-contract evidence | Bohemia Interactive terms; not redistributed |

The source map records pinned revisions and decisions. A link or citation is
not permission to copy a source into the MIT payload.

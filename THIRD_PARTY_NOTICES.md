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
| DayZ game scripts, tools and data | API and runtime-contract evidence | Bohemia Interactive terms; not redistributed |

The source map records pinned revisions and decisions. A link or citation is
not permission to copy a source into the MIT payload.

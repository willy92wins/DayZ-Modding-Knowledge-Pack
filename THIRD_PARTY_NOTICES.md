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
| DayZ Expansion, TraderPlus and TraderX | UI/layout comparison corpora | not redistributed; license not asserted here |
| DayZ game scripts, tools and data | API and runtime-contract evidence | Bohemia Interactive terms; not redistributed |

The source map records pinned revisions and decisions. A link or citation is
not permission to copy a source into the MIT payload.

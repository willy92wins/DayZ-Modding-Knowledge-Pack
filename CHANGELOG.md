# Changelog

All notable changes to the DayZ Modding Knowledge Pack are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- r21 Phase 01 evidence contracts: source map, executable-claim registry and
  local-root templates.
- Root MIT license, third-party notices, contribution policy and per-skill
  compatibility matrix.
- Source-verified guidance for injected-object Forward Contracts, historical
  PBO recovery, crash-safe evidence, authority and loopback boundaries,
  incremental rebuilds, vehicle get-in/action contracts, winding lineage and
  material overrides.

### Changed

- Normalized all 14 skill descriptions to the official 1024-character limit.
- Coupled `dayz-test-ingame` and `dayz-mcp-verify` to the managed
  `dayz_test_run` / `dayz_test_stop` lifecycle.
- Hardened generated test launchers so credentials are scoped to child
  processes and no VPP password is packaged by default.
- Promoted the validated Phase 01 snapshot from commit
  `7a25432febc112a957a7c1ef7a7d2c16c221b24f` to Obsidian and all configured
  skill targets with create-only receipt `c7b5366cc761a8038e52f6a2`.

### Fixed

- Promotion now durably synchronizes and safely removes verified Windows
  sidecars containing read-only files while preserving fail-closed behavior
  for unrelated permission errors.

### Security

- Explicitly exclude secrets, personal identities, private absolute paths,
  proprietary game data and incompatible third-party payloads from releases.

# Changelog

All notable changes to the DayZ Modding Knowledge Pack are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- py3d `KNOWN-ISSUES.md`: the published blind spots of the library, including
  three checks that cannot fail for the reason you would rely on them for —
  `save(verify=True)` compares no coordinates, `python -m py3d diff` calls
  materially different models equal, and `audit_p3d.py` can print `ALL PASSED`
  having checked nothing.
- py3d absolute winding check (`_check_winding_absolute` with normal-agreement
  and edge-coherence measures) and its council regression tests.
- In-game verified skill knowledge written between 2026-07-30 and 2026-08-13:
  worn clothing binds through `DayzTemporarySkeleton` rather than
  `OFP2_ManSkeleton`; starting CF on a mission whose persistence was written
  without it crashes the server hard while naming an unrelated vanilla entity;
  the diag RPT buffers about 52 KB.
- r21 Phase 04 strict 3D tooling: SEAnim v1 / `RTM_MDAT` / `RTM_0101`
  reader-writer-inspector, contract-driven MLOD pre-export validation and a
  read-only ODOL v53-v55 anatomy/diff adapter with authorized fixtures.
- py3d 1.4.0 proxy lifecycle with explicit raw/engine frames, strict anatomy,
  atomic align/remove operations and reproducible wheel manifest.
- Rollout projections for model preflight, animation formats, strict ODOL
  parity and proxy lifecycle, including an explicit-root, backup-preserving
  no-write/apply script.
- r21 Phase 01 evidence contracts: source map, executable-claim registry and
  local-root templates.
- Root MIT license, third-party notices, contribution policy and per-skill
  compatibility matrix.
- Source-verified guidance for injected-object Forward Contracts, historical
  PBO recovery, crash-safe evidence, authority and loopback boundaries,
  incremental rebuilds, vehicle get-in/action contracts, winding lineage and
  material overrides.

### Changed

- **py3d 1.4.0 → 1.5.0, distribution renamed `py3d` → `py3d-dayz`.** The pack
  now takes its py3d bytes from the published fork
  `willy92wins/py3d-dayz@c50321c`, which was ahead of the pack and already
  carried the release text. The importable module stays `py3d`; only the
  distribution name changes, because `py3d` on PyPI is an unrelated library.
  The version moved rather than being re-sealed again because `1.4.0` had come
  to designate three different contents distinguished only by a manifest seal.
  New reproducible wheel: `py3d_dayz-1.5.0-py3-none-any.whl`, SHA-256
  `16eac9218cddb02b52b533540c0259c33d5e5b2d6ad2cd28444ef049d608a73b`.
- `audit_p3d.py` moves from `tools/py3d/rollout/` to `tools/py3d/tools/`,
  matching the published layout.
- Distinguish fail-closed ODOL parity inspection from partial MLOD recovery;
  the compatible unknown-license backend remains external and SHA-256 pinned.
- Normalized all 14 skill descriptions to the official 1024-character limit.
- Coupled `dayz-test-ingame` and `dayz-mcp-verify` to the managed
  `dayz_test_run` / `dayz_test_stop` lifecycle.
- Hardened generated test launchers so credentials are scoped to child
  processes and no VPP password is packaged by default.
- Promoted the validated Phase 01 snapshot from commit
  `7a25432febc112a957a7c1ef7a7d2c16c221b24f` to Obsidian and all configured
  skill targets with create-only receipt `c7b5366cc761a8038e52f6a2`.

### Fixed

- Make the py3d wheel builder and rollout work under Windows PowerShell 5.1,
  including deferred `$PSScriptRoot` defaults and explicit native
  `git apply` exit-code capture.
- Replace a fabricated `py3d.read_p3d` reference with the verified
  `py3d.P3D(stream)` API in the animation projection.
- Promotion now durably synchronizes and safely removes verified Windows
  sidecars containing read-only files while preserving fail-closed behavior
  for unrelated permission errors.

### Security

- Explicitly exclude secrets, personal identities, private absolute paths,
  proprietary game data and incompatible third-party payloads from releases.

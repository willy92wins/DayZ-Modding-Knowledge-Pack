# Third-party provenance — img2threejs

Source: https://github.com/img2threejs/img2threejs
Commit: `9a8ecf129a58c1b557a1f03f7727f6295672cd51` (v1.4.3, cloned 2026-07-30)
License: Apache-2.0 (see the repository's LICENSE file)

| File here | Relation to upstream |
|---|---|
| `correction_loop.py` | verbatim copy of `forge/stage4_review/correction_loop.py` (SHA-256 `c100a1c5c01b0a743afe7ddd41a7f9519a945321a4af3b6822ea235cf9d6a2df`) |
| `vr_delta.py` | adaptation for same-camera Blender render pairs; per-function origins listed in its module docstring (PNG codec + foreground mask from `forge/stage1_intake/extract_pbr_evidence.py`, mask geometry from `forge/stage4_review/diagnose_render.py`, luma signals from `forge/stage4_review/divine_eye.py`) |

The staged-review methodology sections added 2026-07-30 to this skill's `SKILL.md` (bounded loop, typed actions, per-feature gates) and to `blender-assembly/SKILL.md` (detail scan protocol, texture-side detail kinds) are adapted from the same repository's `SKILL.md` and `grimoire/` rubrics.

Windows console note: `correction_loop.py`'s plain-text output contains `Δ`, which crashes cp1252 consoles — always call it with `--json` (JSON escapes non-ASCII).

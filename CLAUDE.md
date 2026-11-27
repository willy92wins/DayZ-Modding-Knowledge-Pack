# CLAUDE.md

See [`AGENTS.md`](AGENTS.md) — it is the canonical agent file for this
repository and applies to Claude Code unchanged.

Skill installation for Claude Code specifically: `pip install -e .` once, then
`python3 -m packctl install --target ~/.claude/skills` (or
`<project>/.claude/skills`). The pack installs as one skill, `dayz`, invoked as
`/dayz`. See AGENTS.md, "Installing the skills for your agent".

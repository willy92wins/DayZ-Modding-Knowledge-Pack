# CLAUDE.md

See [`AGENTS.md`](AGENTS.md) — it is the canonical agent file for this
repository and applies to Claude Code unchanged.

Skill installation for Claude Code specifically: unzip the release's
`dayz-skill-<version>.zip` into `~/.claude/skills/`, or from a checkout run
`python3 -m packctl install --target ~/.claude/skills` (`--link` for
maintainers). The pack installs as one skill, `dayz`, invoked as `/dayz`. See
AGENTS.md, "Installing the skills for your agent".

---
name: tablero-cupos-sesiones
description: >-
  use this when the user asks for cupos, suscripciones, tablero, or sesiones
  vivas — refresh AI/_tablero.md; chat ping = live ∩ isStarred Claude titles
---
# Tablero cupos y sesiones

`VAULT` is your local Markdown vault root; `%APPDATA%`, `%LOCALAPPDATA%` and `%USERPROFILE%` are Windows placeholders. The existing vault runbook is optional: the bundled helper reads these three quotas without it. Keep physical roots in local configuration.

Refresh `VAULT\AI\_tablero.md` from live sources. Do not wait for the 8:13 recap. Do not invent numbers. No tokens, cookies, or org UUIDs in chat.

## Preferencia de lanes (2026-11-06)

Orden al despachar trabajo nuevo (hasta nuevo aviso): **1) Muse · 2) Antigravity (agy) · 3) DeepSeek en GB10/GX10 · 4) Claude A · 5) Grok solo si hace falta la puerta pública de X o no hay otra lane**. Nada de créditos extra de Codex hasta 2026-11-09 16:34 Madrid. El tablero no lanza trabajo; esta preferencia gobierna wiring/sesiones y el texto del hot-cupos.

## Cupos (local host)

1. Claude, two Max 20x orgs: `%APPDATA%\Claude\plan-usage-history.json`. Last sample per org. `u.fh` = 5h %, `u.sd` = weekly %, `t` = epoch ms. Weekly reset Sunday ~03:40 Madrid. Sample >12h = STALE. Do not force `claude usage` if OAuth is dead.
2. [EXACT][CLAIM-TABLERO-CODEX-CREDITS] Codex/OpenAI Pro: `python VAULT\AI\20_Runbooks\scripts\codex-usage.py --days 3`. Use CUOTA `rate_limits.primary` (used_percent, resets_at). Include credits balance: used >=100% with balance >0 = **NO bloqueado: tira de creditos**; without credits = **BLOQUEADO hasta reset**. If the dated row is >24h, say so. Do not `codex exec` just to read quota.
3. Grok grok.com (**20 €/mes** since 2026-08-31 14:31 Madrid): helper cache `%LOCALAPPDATA%\tablero-cupos\grok-usage.json`; call `%USERPROFILE%\.grok\bin\grok.exe --oauth --no-alt-screen --minimal /usage` (unset `XAI_API_KEY`) only if missing/unusable, >24h old, not from today Europe/Madrid, or `--refresh-grok`. Kill TUI if it hangs. Not `grok -p /usage`. 402 before first turn = pool empty. Unique public-X door; prefer Muse/agy/DS before spending this pool (norma 2026-11-06).
4. Cursor **Ultra (200 €/mes)** since 2026-08-31: `cursor-agent about` / `status` show tier, **not remaining quota**. Never invent a Cursor remaining figure. Point at Usage & Billing (`grokbot://app/v1/settings?id=plan`) for Grok Bot itself; Cursor Ultra saldo is not readable from CLI.
5. [EXACT][CLAIM-TABLERO-AGY-USAGE] Antigravity: TSV % = **remaining**; convert ISO UTC resets to Madrid. Helper cache: `%LOCALAPPDATA%\tablero-cupos\agy-usage.json` (raw TSV lines + epoch); call `agy -p "/usage"` only if missing/unusable, >24h old or not from today in Europe/Madrid; `--refresh-agy` forces a call. Reuse, including fallback after failure, = `STALE (lectura HH:MM Madrid)`; failed calls preserve good cache. Measured 2026-11-05 15:12–15:13 Madrid: three consecutive `/usage` calls, Gemini 5h 50%→50%→50%, weekly 76% constant: no measurable spend; cache avoids noise/latency, cost remains unproven.
6. [EXACT][CLAIM-TABLERO-MUSE-USAGE] Muse: `muse usage --json`; `allowance` has tier, window + weekly usedPercent/resetsAtMs and asOfMs. Show both resets in Madrid; include them in the chat hot-cupos line.

[EXACT][CLAIM-TABLERO-CUPOS-EXTRA] From this skill directory: `python scripts/cupos-extra.py` (or `--json`) reads Codex, Antigravity and Muse; each source fails soft. Antigravity JSON includes `stale` and `cached_at` (epoch seconds, null without a reading). Madrid uses zoneinfo, with the EU DST rule if tzdata is absent.

## Sesiones

1. **Grok Bot** roles table (not inboxes).
2. **Slugs** from `%USERPROFILE%\.local\orq-claude-channel\menu.json`.
3. **Vivas**: stream-json with Desktop **title** + **isStarred**, orq-dispatch INDEX, CLIs, dayz_mcp client count, MCP trees.

### Join + pin

- `~\.claude\sessions\<pid>.json` → `sessionId`
- `%APPDATA%\Claude\claude-code-sessions\*\*\local_*.json` where `cliSessionId == sessionId` → `title`, **`isStarred`**
- Fallback title: last `custom-title` in project jsonl; else derived `name`

### Chat alert = live ∩ starred (2026-09-07)

Ping **only** sessions that are process-alive **and** `isStarred: true`. Do not ping unstarred lives or starred offline sessions. `_tablero.md` may still list all lives (include a starred column).

Still omit from ping even if starred: Pantalla negra, DLSS5, Drift sweep, Skill/documentación búsqueda en X, Vaciado de buzón MCP.

## Deliver

Overwrite `_tablero.md`. Chat: filtered bullets `**<title>** · slug · model · since · one-liner` + hot cupos line. Quiet cron → silence. Hue: red ≥90%, blue ≥80% else, restore white; no Hue on quiet refresh.

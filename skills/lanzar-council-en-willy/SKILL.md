---
name: lanzar-council-en-willy
description: >-
  use this when launching a DayZ/Enfusion/MCP council or several Willy workers —
  one orq-dispatch hop; arm coupled watcher same turn; receive INDEX at close;
  never N Tasks; never go.cmd; never 15-min Grok Bot poll
---
# Launch council / Willy workers


> **Dueño (cambio aprobado 1-nov-2026, traspaso del Orq):** el dueño de esta skill es el **Experto MCP**. Regla: **un solo DayZDiag a la vez** (pruebas en juego en serie). Las menciones a Grok Bot / Orquestrador como lanzador o vigía de abajo quedan como histórico hasta que se reescriban por la vía canónica.

Use this when launching a planning council or several Willy workers on Willy.

Fan-out is **one** local-exec Shell that starts `orq-dispatch.ps1`. That script spawns N native processes and **dies**. Do not open N Grok Bot Tasks. Protocol lives in [council-orchestration](sand-workflow:council-orchestration). Do not change this dispatcher.

Night unattended work is **not** a council: [Sesiones nocturnas](sand-workflow:sesiones-nocturnas). Native Codex conducts; one hop Qwen/K3; Claude wrote `GATES.md` by day and is not in the tree. Do not spawn Sol to patch. Do not Claude → Codex-in-prime-agent → `rlm()`.

## Dispatcher (c3-20260829 in production)

- Script: `C:\Users\<you>\.local\bin\orq-dispatch.ps1`. Static runners: `run-prime-lane.sh`, `run-codex-lane.cmd`. Never generate runners from chat. Never `go.cmd`.
- `kind`: `ping` · `prime-agent` (Qwen/K3/Gemini only) · `grok` (repo `cwd`, `effort`/`max_turns`, stdout → `out.md`) · `codex` (sibling, same repo `cwd`) · `cmd` (escape).
- Cursor is **not** a dispatcher `kind` and **not** a prime-agent provider. If a hop needs Cursor/Kimi-K3/GLM-5.2, that is a separate `cursor-agent.cmd` invocation (absolute path; never `agent`) or a later lane — do not invent a `kind=cursor`.
- Done-when = host `lanes/<id>/out.md`. 0 bytes = ERROR. Hop that finishes with a red gate = ERROR, not COMPLETE.
- Mutating `cwd` under TEMP, not OneDrive. Kill `taskkill /T /F`; capture ExitCode before kill.
- Host tripwire: dispatcher writes `NOTIFY.json` and fail-soft POST to `C:\Users\<you>\.local\orq-dispatch\webhook.url`. Without that file there is disk only. That POST is not this chat waking up.

## One hop

1. `BRIEF.md` + `lanes.json`. Never blind: live `C:\Users\<you>\.claude\skills\gates-ledger` plus the job skills. Optional `MANIFEST.md`.
2. `powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Users\<you>\.local\bin\orq-dispatch.ps1 -JobDir %TEMP%\orq-dispatch\<job_id>`
3. **Same turn, coupled watcher.** Load live `C:\Users\<you>\.claude\skills\delegar\references\patterns\coupled-watcher.md` for the disk signals (INDEX.md / lanes/*/EXIT / NOTIFY.json). A decoupled hop is not launched until the vigía is armed in the **same turn** as dispatch. Name what will wake you before promising «te aviso». Do not use a Grok Bot 15-min cron. Do not poll GATES.md (LL-385).

### Grok Bot / Orquestrador — how the vigía must wake THIS chat (measured 2026-09-10 g7f)

- **Bug measured:** a Willy `Shell` with `block_until_ms: 0` that exits on INDEX **does not reliably re-open Orquestrador**. g7f INDEX finished 22:46 Madrid; the Shell watcher exited 22:47 with `WATCHER_EXIT`; Orq got no wake until Guillermo asked ~23:35. `NOTIFY.json` on disk + optional `webhook.url` POST also **do not** wake this chat (dispatcher docs already say that).
- **Required wake on Grok Bot:** arm **one** `Task` / `executor` vigía in the same turn as `orq-dispatch`. The executor polls the job dir on Willy (Shell+machineId) for INDEX/EXIT/NOTIFY, then returns a short INDEX report (ok/nok, job_id, out.md bytes/verdict head). Parent always gets a background-task completion wake — that is the named process.
- **Allowed:** an optional Willy Shell sensor in parallel for logs; it is **not** the promised wake.
- **Forbidden as sole vigía:** Shell-only on Willy, 15-min Grok Bot cron, polling GATES.md, relying on orq-dispatch webhook for this chat.
- «Never N Tasks» still means: do **not** fan out N worker Tasks for lanes. **One** watcher Task + one `orq-dispatch` Shell is the coupled pair.

4. **On INDEX:** receive ok/nok immediately (from the executor vigía result). Ping via Asistente/Hue. C12: trust artifact (out.md bytes, DECISOR/receipts) over INDEX. Prefer workspace `out.md` if `lanes/*/out.md` is a stub («REVIEW OK» only). Do not `--status` mid-hop. Do not `--approve` / `--attest` mid-hop.

## Do not

N **worker** Tasks for lanes · Shell-only vigía on Grok Bot · `go.cmd` · 3090 · `pkill -f prime-agent` · start Claude from prime-agent · nest Grok/Codex as `rlm()` · in-flight GATES peek (LL-385) · own the ledger · close a gate in red · reopen `routing.md` · spawn Sol to patch overnight · 15-min Grok Bot poll for INDEX

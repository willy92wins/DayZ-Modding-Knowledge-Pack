#!/usr/bin/env python3
"""Shell bridge so a paid agent (Codex, Grok) can delegate work to the local model.

This is the cheap direction of the matrix: an expensive agent offloads mechanical,
high-volume work to a model whose marginal cost is zero. The caller does not need
to know about Ollama, ports or JSON payloads - it runs one command and reads the
answer on stdout.

Every call appends a line to a JSONL ledger so the scorecard is built from
measured calls rather than impressions.

--with-tools gives the local model grep/read access to the vanilla DayZ tree via
enforce_agent.py, which is what turns it from "recalls an API" into "verifies an
API". Without it the model answers from memory - fine for prose, not for code.

Requires: Ollama on 127.0.0.1:11434. Pure stdlib, Python 3.10+.

Usage:
    python ask_qwen.py --prompt "Summarise what this function does: ..."
    python ask_qwen.py --prompt-file task.md --with-tools --json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen3.8:27b"
NUM_CTX = 65536          # the 262144 default spills 57% of a 27B model to CPU;
                         # 65536 still loads 100% GPU (66/66), 98304 does not
DRAFT_N_MAX = 2          # MTP speculative decoding; 24 GB cards peak at 2, and
                         # the model ships with 4, so it has to be passed here
LEDGER = Path(__file__).parent / "agent_calls.jsonl"


def log_call(record: dict) -> None:
    record["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    try:
        with open(LEDGER, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass


def ask_plain(model: str, prompt: str, system: str | None) -> dict:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model, "messages": messages, "stream": False,
        "options": {"temperature": 0.1, "num_ctx": NUM_CTX,
                    "draft_num_predict": DRAFT_N_MAX},
    }
    req = urllib.request.Request(
        f"{HOST}/api/chat", data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    t0 = time.monotonic()
    with urllib.request.urlopen(req, timeout=1800) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return {
        "text": body.get("message", {}).get("content", ""),
        "tokens": body.get("eval_count", 0),
        "wallS": round(time.monotonic() - t0, 1),
        "toolCalls": 0,
    }


def ask_with_tools(model: str, prompt: str) -> dict:
    """Delegate to junior_agent.py, which owns the grep/read tool loop.

    Escalation is off here: a senior that delegated INTO the local model should
    not have that call bounce back out to another paid model without saying so.
    """
    here = Path(__file__).parent
    task = here / "_bridge_task.md"
    out = here / "_bridge_out.md"
    task.write_text(prompt, encoding="utf-8")
    t0 = time.monotonic()
    proc = subprocess.run(
        [sys.executable, str(here / "junior_agent.py"), "--model", model,
         "--prompt", str(task), "--out", str(out),
         "--senior", "none", "--max-escalations", "0"],
        capture_output=True, text=True, timeout=3600,
    )
    if not out.exists():
        raise RuntimeError(f"local agent produced nothing: {proc.stderr[-500:]}")
    text = out.read_text(encoding="utf-8")
    calls = text.count("- `grep_vanilla(") + text.count("- `read_vanilla(")
    body = text.split("---", 2)[-1].strip()
    return {"text": body, "tokens": 0, "wallS": round(time.monotonic() - t0, 1),
            "toolCalls": calls}


def main(argv: list[str]) -> int:
    # Up front: NUM_CTX is read below as the argparse default, and Python
    # rejects a `global` that comes after the name has been used in scope.
    global NUM_CTX
    ap = argparse.ArgumentParser(description=__doc__)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--prompt")
    src.add_argument("--prompt-file", type=Path)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--system", help="optional system prompt (ignored with --with-tools)")
    ap.add_argument("--with-tools", action="store_true",
                    help="give the model grep/read access to the vanilla DayZ tree")
    ap.add_argument("--caller", default="unknown",
                    help="who is calling (codex, grok, claude) - recorded in the ledger")
    ap.add_argument("--num-ctx", type=int, default=NUM_CTX,
                    help="context window. The default is the ceiling of the "
                         "stock qwen3.8:27b on a 24 GB card; a smaller quant "
                         "buys a higher rung, so raise it only as far as "
                         "`ollama ps` still reports 100%% GPU.")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    NUM_CTX = args.num_ctx

    prompt = args.prompt if args.prompt else args.prompt_file.read_text(encoding="utf-8")

    try:
        r = ask_with_tools(args.model, prompt) if args.with_tools \
            else ask_plain(args.model, prompt, args.system)
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        print(f"ERROR: {exc}", file=sys.stderr)
        log_call({"caller": args.caller, "direction": f"{args.caller}->qwen",
                  "model": args.model, "ok": False, "error": str(exc)[:300]})
        return 2

    log_call({"caller": args.caller, "direction": f"{args.caller}->qwen",
              "model": args.model, "ok": True, "withTools": args.with_tools,
              "tokens": r["tokens"], "wallS": r["wallS"], "toolCalls": r["toolCalls"],
              "promptChars": len(prompt), "answerChars": len(r["text"])})

    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(r["text"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

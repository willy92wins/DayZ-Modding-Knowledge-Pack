#!/usr/bin/env python3
"""The local model as a junior: verifies against sources, escalates when stuck.

Two capabilities beyond the plain tool loop:

  grep_vanilla / read_vanilla  - verify an API instead of recalling it
  ask_senior                   - escalate a specific question to a paid model

The escalation tool exists because of a measured failure: on the first real task
the local model searched for SpawnAttachedMagazine five times, could not find it
(its patterns assumed `void`, the declaration returns `Magazine`), and shipped the
gap as NO VERIFICADO. A junior that can ask would have closed it in one question -
the reviewer later found it in seconds.

Escalation is CAPPED and logged. Each call spends the user's quota, so the budget
is enforced here rather than trusted to the model's judgement, and the remaining
budget is told to the model so it spends it on the hard question rather than the
first one.

Requires: Ollama on 127.0.0.1:11434, grok CLI. Pure stdlib, Python 3.10+.

Usage:
    python junior_agent.py --model qwen3.8:27b --prompt task.md --out ans.md \
        --senior grok --max-escalations 2
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

HOST = "http://127.0.0.1:11434"
GROK = str(Path.home() / ".grok" / "bin" / "grok.exe")
VANILLA = Path.home() / "OneDrive" / "Documentos" / "DayZ Projects" / "scripts"
SOURCE_GLOBS: tuple[str, ...] = ("*.c",)   # override with --ext for other trees
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv"}
NUM_CTX = 65536   # Default that is safe on the stock qwen3.8:27b: 32768 overflowed
                  # on a real code review, and 65536 is the last rung that still
                  # loads 66/66 layers on a 24 GB card - 98304 spills 8 of them to
                  # CPU. A smaller file buys a higher rung (the Unsloth UD-IQ4_XS
                  # holds 98304 at 100% GPU), so this is --num-ctx, not a constant:
                  # the ceiling belongs to the file, not to the harness.
DRAFT_N_MAX = 2   # MTP speculative decoding. The model ships draft_num_predict
                  # 4; 24 GB cards peak at 2, so it has to be passed per request.
MAX_STEPS = 50
LEDGER = Path(__file__).parent / "agent_calls.jsonl"

BASE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "grep_vanilla",
            "description": (
                "Regex search across the indexed source tree you were given. "
                "Returns path:line:text. Verify any class, method or constant here "
                "before using it - your memory is not a valid source."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "max_results": {"type": "integer"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_vanilla",
            "description": (
                "Read a line range from a file. Use the path EXACTLY as grep_vanilla "
                "printed it, including any leading tree prefix (e.g. 'mod/Foo.c' or "
                "'vanilla/3_game/entities/object.c') - do not add, strip or reorder "
                "prefixes, and do not start it with '/'. If a read fails, re-run "
                "grep_vanilla and copy the path from its output rather than guessing."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "start_line": {"type": "integer"},
                    "end_line": {"type": "integer"},
                },
                "required": ["path", "start_line", "end_line"],
            },
        },
    },
]

SENIOR_TOOL = {
    "type": "function",
    "function": {
        "name": "ask_senior",
        "description": (
            "Escalate ONE specific question to a senior engineer (a frontier model "
            "with the same access to the vanilla tree). Use it when you are stuck "
            "after genuinely trying: a symbol you cannot find, two readings of the "
            "spec that contradict each other, a signature you cannot confirm. "
            "It is expensive and capped, so do not use it for something a grep "
            "would answer, and ask the hardest question you have, not the first."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "the specific question, self-contained",
                },
                "what_you_tried": {
                    "type": "string",
                    "description": "which searches you already ran and what they returned",
                },
            },
            "required": ["question", "what_you_tried"],
        },
    },
}

_FILES: list[tuple[str, list[str]]] = []


def _vanilla_files() -> list[tuple[str, list[str]]]:
    if not _FILES:
        root = VANILLA.resolve()
        for pat in SOURCE_GLOBS:
            for p in sorted(root.rglob(pat)):
                if any(part in SKIP_DIRS for part in p.parts):
                    continue
                try:
                    _FILES.append((str(p.relative_to(root)).replace("\\", "/"),
                                   p.read_text(encoding="utf-8",
                                               errors="replace").splitlines()))
                except OSError:
                    continue
        _FILES.sort()
    return _FILES


def assert_index_not_empty() -> None:
    """Fail closed when the index is empty instead of letting the run confabulate.

    An empty index is the worst possible silent failure here: every grep returns
    "no match", the model reads that as a fact about the code, and it fills the
    gaps from memory. The output looks like an audit and is fiction. The default
    globs only match *.c, so pointing --root at any other kind of tree used to
    produce exactly that. Cheap positive control: count what got indexed, and
    refuse to start on zero.
    """
    files = _vanilla_files()
    lines = sum(len(l) for _, l in files)
    print(f"[index] {len(files)} ficheros, {lines} lineas, patrones={list(SOURCE_GLOBS)}",
          file=sys.stderr)
    if not files:
        raise SystemExit(
            f"ABORT: 0 ficheros indexados bajo {VANILLA} con {list(SOURCE_GLOBS)}.\n"
            f"El modelo recibiria un arbol vacio y confabularia el informe entero.\n"
            f"Usa --ext para los patrones del arbol (p.ej. --ext .py,.pyi)."
        )


def tool_grep(pattern: str, max_results: int = 40) -> str:
    try:
        rx = re.compile(pattern, re.IGNORECASE)
    except re.error as exc:
        return f"ERROR: invalid regex ({exc})"
    cap = max(1, min(max_results, 80))
    hits: list[str] = []
    for rel, lines in _vanilla_files():
        n = 0
        for i, line in enumerate(lines, 1):
            if rx.search(line):
                hits.append(f"{rel}:{i}:{line.strip()[:220]}")
                n += 1
                if n >= 8 or len(hits) >= cap:
                    break
        if len(hits) >= cap:
            break
    return "\n".join(hits) if hits else f"no matches for /{pattern}/ in the vanilla tree"


def tool_read(path: str, start_line: int, end_line: int) -> str:
    target = (VANILLA / path.replace("/", "\\")).resolve()
    try:
        target.relative_to(VANILLA.resolve())
    except ValueError:
        return "ERROR: path escapes the vanilla scripts root"
    if not target.is_file():
        return f"ERROR: no such file: {path}"
    lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    s = max(1, start_line)
    e = min(len(lines), max(s, end_line))
    if e - s > 400:
        e = s + 400
    body = "\n".join(f"{i}: {lines[i-1]}" for i in range(s, e + 1))
    return f"{path} lines {s}-{e} (file has {len(lines)}):\n{body}"


def log(record: dict) -> None:
    record["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    try:
        with open(LEDGER, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass


def ask_senior_grok(question: str, tried: str, workspace: Path) -> tuple[str, float]:
    brief = f"""Un ingeniero junior esta escribiendo codigo Enforce Script para un mod de DayZ y se
ha atascado. Tiene acceso al arbol vanilla en:
  {VANILLA}

Su pregunta:
{question}

Lo que ya intento:
{tried}

Responde SOLO a lo que pregunta, de forma directa y accionable. Verifica en el
arbol antes de afirmar una firma y cita `path:linea`. Si lo que busca no existe,
dilo claramente y di cual es la alternativa real. No escribas el archivo por el,
no revises codigo que no te ha ensenado, no pidas aprobacion.
"""
    bp = workspace / "_senior_q.txt"
    bp.write_text(brief, encoding="utf-8")
    cmd = [GROK, "--prompt-file", str(bp), "--cwd", str(workspace),
           "--tools", "read_file,grep,list_dir", "--deny", "MCPTool",
           "--output-format", "json", "--max-turns", "20",
           "--always-approve", "--no-memory"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
    if proc.returncode != 0:
        return f"ERROR: the senior could not be reached ({proc.stderr[-200:]})", 0.0
    try:
        body = json.loads(proc.stdout)
    except json.JSONDecodeError:
        s, e = proc.stdout.find("{"), proc.stdout.rfind("}")
        body = json.loads(proc.stdout[s:e + 1]) if s != -1 and e > s else {}
    return body.get("text", "(empty)"), float(body.get("total_cost_usd", 0.0))


MAX_TOOL_CHARS = 6000   # one search must not be able to flood the window
KEEP_RECENT = 30        # messages kept verbatim at the tail when pruning
PRUNE_AT_FRAC = 0.75    # prune only above this share of NUM_CTX ...
PRUNE_TO_FRAC = 0.50    # ... and then cut to here, so it stays quiet for many
                        # turns. Pruning changes the prefix and costs a full
                        # re-eval, so it has to be rare, not per-turn.


def est_tokens(messages: list[dict]) -> int:
    """Rough size of the conversation. 4 chars per token is close enough to
    decide whether we are near the window; it never needs to be exact."""
    n = 0
    for m in messages:
        n += len(m.get("content") or "") // 4 + 8
        for tc in (m.get("tool_calls") or []):
            n += len(json.dumps(tc, ensure_ascii=False)) // 4
    return n


def _marker(dropped: int) -> dict:
    return {"role": "user", "content": (
        f"[{dropped} mensajes intermedios de verificacion recortados para no desbordar "
        f"la ventana. Lo que ya comprobaste sigue siendo valido: no repitas esas "
        f"busquedas. Si necesitas un dato que ya viste y no recuerdas, vuelve a "
        f"consultarlo puntualmente.]")}


def prune(messages: list[dict]) -> list[dict]:
    """Keep the window under control WITHOUT ever dropping the original task.

    Measured failure this protects against: on a long review the history reached
    30k of a 32k window, Ollama truncated from the front, the only `user` message
    went with it, and the request died with HTTP 500 `no user query found in
    messages` - the run lost the assignment, not the argument. Server-side
    truncation cannot know which message is load-bearing, so it happens here.

    But WHEN it happens decides the wall clock, and the first version got that
    wrong. It pruned by message count, so past ~32 messages every single turn
    slid the tail by one. A changed prefix means llama.cpp cannot reuse its KV
    cache, so every turn re-evaluated the whole history: measured 51 s of prompt
    eval against 3 s of generation, 94% of a 67-minute audit spent reprocessing
    tokens it had already processed.

    So: prune on SIZE, not on message count, and when it does fire cut deep
    enough that it will not fire again for many turns. Between prunes the prefix
    is stable and the cache does its job; each prune costs one full re-eval, and
    the point is to pay that rarely instead of always.
    """
    limit = est_tokens(messages)
    if limit < int(NUM_CTX * PRUNE_AT_FRAC):
        return messages

    head = messages[0]                      # the task itself, never dropped
    target = int(NUM_CTX * PRUNE_TO_FRAC)
    keep = KEEP_RECENT
    while keep >= 4:
        tail = messages[-keep:]
        # A tail must not open on an orphan tool result: the API needs the
        # assistant message carrying the tool_calls that produced it.
        while tail and tail[0].get("role") == "tool":
            tail = tail[1:]
        cand = [head, _marker(len(messages) - 1 - len(tail))] + tail
        if est_tokens(cand) <= target or keep == 4:
            print(f"[prune] {limit} -> {est_tokens(cand)} tokens aprox "
                  f"(cola de {len(tail)} mensajes)", file=sys.stderr)
            return cand
        keep -= 4
    return messages


def chat(model: str, messages: list[dict], tools: list[dict]) -> dict:
    messages = prune(messages)
    payload = {"model": model, "messages": messages, "stream": False,
               "tools": tools,
               "options": {"temperature": 0.1, "num_ctx": NUM_CTX,
                           "draft_num_predict": DRAFT_N_MAX}}
    req = urllib.request.Request(
        f"{HOST}/api/chat", data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=1800) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main(argv: list[str]) -> int:
    # Declared up front: NUM_CTX is read below as the argparse default, and Python
    # rejects a `global` that comes after the name has been used in the scope.
    global VANILLA, SOURCE_GLOBS, NUM_CTX
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", required=True)
    ap.add_argument("--prompt", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--senior", choices=["grok", "none"], default="grok")
    ap.add_argument("--max-escalations", type=int, default=2)
    ap.add_argument("--root", type=Path,
                    help="tree the model may grep/read (default: the vanilla DayZ scripts). "
                         "Point it at a directory holding several trees to search across all "
                         "of them at once - reviewing code usually needs both the code under "
                         "review and the reference it must match.")
    ap.add_argument("--num-ctx", type=int, default=NUM_CTX,
                    help=f"context window (default {NUM_CTX}, the ceiling of the "
                         f"stock qwen3.8:27b on a 24 GB card). Raise it only as far "
                         f"as `ollama ps` still says 100%% GPU for the file you run: "
                         f"a smaller quant buys a higher rung, and spilling layers "
                         f"to CPU costs far more than the extra context is worth.")
    ap.add_argument("--ext", default="",
                    help="comma-separated source patterns to index (default: .c). "
                         "Use .py, .ts, .cpp ... for non-DayZ trees. The run aborts if "
                         "nothing matches: an empty index turns the audit into fiction.")
    args = ap.parse_args(argv)

    if args.root:
        VANILLA = args.root.resolve()
    if args.num_ctx != NUM_CTX:
        NUM_CTX = args.num_ctx
    if args.ext:
        SOURCE_GLOBS = tuple(
            e if e.startswith("*") else "*" + (e if e.startswith(".") else "." + e)
            for e in (x.strip() for x in args.ext.split(",")) if e
        )
    assert_index_not_empty()

    workspace = args.out.parent
    workspace.mkdir(parents=True, exist_ok=True)

    tools = list(BASE_TOOLS)
    if args.senior != "none" and args.max_escalations > 0:
        tools.append(SENIOR_TOOL)

    prompt = args.prompt.read_text(encoding="utf-8")
    if args.senior != "none":
        prompt += (f"\n\n## Escalado\n\nTienes {args.max_escalations} consulta(s) al "
                   f"senior disponibles en toda la sesion (`ask_senior`). Gastalas en "
                   f"lo que de verdad no puedas resolver con grep.\n")

    messages = [{"role": "user", "content": prompt}]
    calls: list[str] = []
    escalations: list[dict[str, Any]] = []
    spent = 0.0
    t0 = time.monotonic()
    warned = False

    # Measured failure this harness exists to prevent: given an ambiguous
    # requirement the model verified 50 times, never escalated, and delivered
    # nothing. It had the answer by call ~15. A junior does not stop on its own;
    # it needs a deadline and an explicit nudge to hand in what it has.
    budget = max(8, int(MAX_STEPS * 0.6))

    for step in range(MAX_STEPS):
        if step == budget and not warned:
            warned = True
            messages.append({"role": "user", "content": (
                f"AVISO DE PRESUPUESTO: llevas {len(calls)} verificaciones y te quedan "
                f"{MAX_STEPS - step} pasos. Deja de explorar. Si te falta UN dato "
                f"concreto para cerrar, usa `ask_senior` AHORA. Si no, entrega ya con "
                f"lo que tienes y declara explicitamente lo que no pudiste verificar. "
                f"Entregar con un hueco declarado es correcto; no entregar es un fallo.")})

        body = chat(args.model, messages, tools)
        msg = body.get("message", {})
        tcs = msg.get("tool_calls") or []
        messages.append(msg)

        if not tcs:
            elapsed = time.monotonic() - t0
            content = msg.get("content", "")
            head = (f"# {args.model} — junior run\n\n"
                    f"**{len(calls)} tool calls, {len(escalations)} escalations, "
                    f"{step} turns, {elapsed:.0f}s, senior cost ${spent:.3f}**\n\n")
            for c in calls:
                head += f"- `{c}`\n"
            for e in escalations:
                head += (f"\n> **ESCALADO**: {e['question']}\n>\n"
                         f"> _ya intentó_: {e['tried']}\n>\n"
                         f"> **senior**: {e['answer'][:1200]}\n")
            args.out.write_text(head + f"\n---\n\n{content}\n", encoding="utf-8")
            log({"direction": f"claude->{args.model}", "toolCalls": len(calls),
                 "escalations": len(escalations), "seniorCostUsd": round(spent, 3),
                 "wallS": round(elapsed, 1), "ok": True})
            print(f"\ndone: {len(calls)} calls, {len(escalations)} escalations, "
                  f"${spent:.3f} senior, {elapsed:.0f}s -> {args.out}")
            return 0

        for tc in tcs:
            fn = tc.get("function", {})
            name = fn.get("name", "")
            fargs = fn.get("arguments", {})
            if isinstance(fargs, str):
                try:
                    fargs = json.loads(fargs)
                except json.JSONDecodeError:
                    fargs = {}

            if name == "ask_senior":
                if len(escalations) >= args.max_escalations:
                    result = ("ERROR: escalation budget exhausted. Resolve it with the "
                              "tools you have and declare what you could not verify.")
                else:
                    q = str(fargs.get("question", ""))[:2000]
                    tried = str(fargs.get("what_you_tried", ""))[:1500]
                    print(f"  [{step}] ESCALATING: {q[:100]}", flush=True)
                    result, cost = ask_senior_grok(q, tried, workspace)
                    spent += cost
                    escalations.append({"question": q, "tried": tried,
                                        "answer": result, "costUsd": cost})
                    log({"direction": f"{args.model}->{args.senior}", "kind": "escalation",
                         "question": q[:300], "costUsd": round(cost, 4), "ok": True})
                calls.append(f"ask_senior({str(fargs.get('question',''))[:90]})")
            else:
                label = f"{name}({json.dumps(fargs, ensure_ascii=False)[:100]})"
                calls.append(label)
                print(f"  [{step}] {label}", flush=True)
                if name == "grep_vanilla":
                    result = tool_grep(fargs.get("pattern", ""), fargs.get("max_results", 40))
                elif name == "read_vanilla":
                    result = tool_read(fargs.get("path", ""),
                                       int(fargs.get("start_line", 1)),
                                       int(fargs.get("end_line", 60)))
                else:
                    result = f"ERROR: unknown tool {name}"

            if len(result) > MAX_TOOL_CHARS:
                result = (result[:MAX_TOOL_CHARS]
                          + f"\n\n[...recortado a {MAX_TOOL_CHARS} caracteres. "
                            f"Acota el patron o el rango en vez de barrer.]")
            messages.append({"role": "tool", "name": name, "content": result})

    # Last resort: one call with tools withdrawn, so the run cannot end empty.
    # Losing the work because the model would not stop searching is the worst
    # outcome available - worse than an answer with a declared gap.
    print("  step budget exhausted -> forcing a final answer without tools", flush=True)
    messages.append({"role": "user", "content": (
        "Se acabaron los pasos de verificacion. Entrega AHORA la respuesta con lo "
        "que ya has comprobado, y lista explicitamente lo que quedo sin verificar. "
        "No hagas mas busquedas.")})
    body = chat(args.model, messages, tools=[])
    content = body.get("message", {}).get("content", "")
    elapsed = time.monotonic() - t0

    args.out.write_text(
        f"# {args.model} — junior run (FORCED CLOSE)\n\n"
        f"**{len(calls)} tool calls, {len(escalations)} escalations, {elapsed:.0f}s, "
        f"senior cost ${spent:.3f}**\n\n"
        f"> Cerrado a la fuerza: agoto el presupuesto de pasos sin entregar por su "
        f"cuenta. Trata este resultado como degradado.\n\n"
        + "".join(f"- `{c}`\n" for c in calls)
        + f"\n---\n\n{content}\n", encoding="utf-8")
    log({"direction": f"claude->{args.model}", "toolCalls": len(calls),
         "escalations": len(escalations), "seniorCostUsd": round(spent, 3),
         "wallS": round(elapsed, 1), "ok": True, "forcedClose": True})
    print(f"\nforced close: {len(calls)} calls, {elapsed:.0f}s -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

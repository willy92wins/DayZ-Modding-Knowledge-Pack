#!/usr/bin/env python3
"""Local-model → Grok review loop, iterating until green light.

The question this answers: is a free local model plus a paid reviewer cheaper
than implementing it, once you count what the review actually costs? So the
loop runs with ZERO orchestrator tokens - no agent in the middle, just two
processes and a verdict parser.

Cost discipline: round 1 opens a Grok session (~$0.40 of quota on a real diff);
every later round resumes it with -r, which reads the context from cache and
costs ~12% of that. Rounds are capped, and every round's cost is recorded.

Grok runs READ-ONLY. --tools is the only thing separating it from the tree on
this host, so the allowlist is not optional.

Requires: Ollama on 127.0.0.1:11434, grok CLI. Pure stdlib, Python 3.10+.

Usage:
    python review_loop.py --model qwen3.8:27b --code v1.md --out loop/ --max-rounds 3
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
VANILLA = str(Path.home() / "OneDrive" / "Documentos" / "DayZ Projects" / "scripts")
NUM_CTX = 32768

REVIEW_BRIEF = """Tarea: revision adversarial de codigo (rol R21) de UN archivo Enforce Script para
DayZ, generado por otro modelo. Solo juicio: no escribes ni modificas nada.

El arbol de scripts VANILLA de DayZ esta en:
  {vanilla}
Usalo con grep/read_file para verificar cada API. Ese arbol es la unica fuente
de verdad sobre que existe en el engine.

## Contexto del encargo que se le dio al autor

Un SMG del pack A6. Requisitos funcionales:
- La clase base del arma hereda de `RifleBoltFree_Base`.
- Gating: el slot `weaponOptics` SOLO acepta optica si el slot
  `weaponSR2MOpticMount` ya tiene montada la montura de riel. Sin montura, se
  rechaza cualquier optica. Con montura, se acepta cualquiera (NO hay lista
  blanca).
- El arma usa el objeto de retroceso del PP19 vanilla.
- Un spawn de debug que deje el arma utilizable (montura, optica, compensador
  `A6_SR2M_Compensator`, cargador `A6_Mag_SR2M_30Rnd`).
- `A6_SR2M` hereda de la base sin logica extra.
- `A6_SR2M_RailMount` hereda de `A6_Optic_Mount_Base` (clase del pack A6, NO
  vanilla: no la busques, es correcto que no aparezca).
- Comentarios en ingles, tono cabecera vanilla.
- Toda condicion booleana en UNA linea (multi-linea rompe el parser de Enforce).

## Que es un hallazgo valido

- Una API que NO existe en el vanilla, o cuya FIRMA no coincide (numero/tipo de
  parametros, tipo de retorno). Cita `path:linea` del vanilla real.
- Logica que no cumple el requisito funcional (p.ej. el gating no bloquea, o
  bloquea de mas).
- Un `super.` omitido donde el contrato vanilla lo exige.
- Violacion de las restricciones de estilo/parser declaradas arriba.

NO son hallazgos validos: preferencias de estilo no pedidas, sugerencias de
refactor, o que falten config.cpp/model.cfg (estan fuera de alcance por diseno).

## Fronteras

- NO propongas reescribir el archivo entero; senala defectos concretos.
- NO inventes `path:linea`: si no lo verificaste en el arbol, dilo.
- NO pidas aprobacion: no hay operador. Emite tu veredicto y termina.

## Codigo a revisar

```c
{code}
```

## Salida obligatoria

Primero tu analisis en prosa. Y AL FINAL, un unico bloque ```json con esta forma
exacta (sin texto despues):

{{"verdict": "GREEN" | "CHANGES_REQUIRED",
  "findings": [
    {{"severity": "BLOCKER"|"MAJOR"|"MINOR",
      "what": "<defecto en una frase>",
      "where": "<simbolo o linea del codigo revisado>",
      "evidence": "<path:linea del vanilla que lo prueba, o 'no verificable'>",
      "fix": "<que cambiar, concreto>"}}
  ],
  "not_verified": ["<lo que no pudiste comprobar y por que>"]}}

`GREEN` significa: sin BLOCKER ni MAJOR. Si hay alguno, es CHANGES_REQUIRED.
"""

FIX_PROMPT = """Un revisor independiente ha auditado tu archivo Enforce contra el arbol vanilla
de DayZ y ha devuelto estos hallazgos:

{findings}

Corrige el archivo. Reglas:
- Usa tus herramientas `grep_vanilla` / `read_vanilla` para VERIFICAR cada
  correccion antes de aplicarla. Si un hallazgo del revisor te parece
  equivocado, compruebalo en el arbol: si el revisor se equivoca, NO apliques
  ese cambio y explica por que con su `path:linea`.
- No reescribas lo que ya estaba bien; cambia solo lo senalado.
- Mantén las restricciones originales: comentarios en ingles con tono cabecera
  vanilla, toda condicion booleana en UNA linea, un unico archivo.
- Canal headless: no pidas aprobacion, decide y aplica.

Devuelve el archivo COMPLETO corregido en un unico bloque de codigo, y despues
una lista breve de que cambiaste y que hallazgo rechazaste (con su evidencia).

Archivo actual:

```c
{code}
```
"""


def extract_code(md: str) -> str:
    blocks = re.findall(r"```(?:c|cpp|enforce)?\s*\n(.*?)```", md, re.DOTALL)
    return max(blocks, key=len).strip() if blocks else md.strip()


def call_grok(brief: str, workspace: Path, session_id: str | None) -> dict[str, Any]:
    brief_path = workspace / "_grok_brief.txt"
    brief_path.write_text(brief, encoding="utf-8")

    cmd = [GROK, "--prompt-file", str(brief_path), "--cwd", str(workspace),
           "--tools", "read_file,grep,list_dir", "--deny", "MCPTool",
           "--output-format", "json", "--max-turns", "40", "--always-approve"]
    if session_id:
        cmd += ["-r", session_id]

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if proc.returncode != 0:
        raise RuntimeError(f"grok exit {proc.returncode}: {proc.stderr[-600:]}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        start, end = proc.stdout.find("{"), proc.stdout.rfind("}")
        if start != -1 and end > start:
            return json.loads(proc.stdout[start:end + 1])
        raise


def parse_verdict(text: str) -> dict[str, Any]:
    blocks = re.findall(r"```json\s*\n(.*?)```", text, re.DOTALL)
    for b in reversed(blocks):
        try:
            return json.loads(b)
        except json.JSONDecodeError:
            continue
    start, end = text.rfind("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    return {"verdict": "UNPARSEABLE", "findings": [], "not_verified": []}


def ask_local(model: str, prompt: str, tools_script: Path) -> str:
    """Re-run the local model through the tool-enabled agent so it can verify fixes."""
    task = tools_script.parent / "_fix_task.md"
    task.write_text(prompt, encoding="utf-8")
    out = tools_script.parent / "_fix_out.md"
    proc = subprocess.run(
        [sys.executable, str(tools_script), "--model", model,
         "--prompt", str(task), "--out", str(out),
         "--senior", "none", "--max-escalations", "0"],
        capture_output=True, text=True, timeout=3600,
    )
    if not out.exists():
        raise RuntimeError(f"local agent produced nothing: {proc.stderr[-600:]}")
    return out.read_text(encoding="utf-8")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", required=True)
    ap.add_argument("--code", type=Path, required=True, help="v1 answer .md")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--max-rounds", type=int, default=3)
    ap.add_argument("--agent", type=Path,
                    default=Path(__file__).parent / "junior_agent.py")
    args = ap.parse_args(argv)

    args.out.mkdir(parents=True, exist_ok=True)
    code = extract_code(args.code.read_text(encoding="utf-8"))
    (args.out / "round0_code.c").write_text(code, encoding="utf-8")

    session_id: str | None = None
    ledger: list[dict[str, Any]] = []

    for rnd in range(1, args.max_rounds + 1):
        print(f"\n=== ronda {rnd}: grok revisa ===", flush=True)
        brief = REVIEW_BRIEF.format(vanilla=VANILLA, code=code)
        t0 = time.monotonic()
        body = call_grok(brief, args.out, session_id)
        text = body.get("text", "")
        session_id = body.get("sessionId") or session_id
        cost = body.get("total_cost_usd", 0.0)
        stop = body.get("stopReason", "?")
        verdict = parse_verdict(text)

        (args.out / f"round{rnd}_review.md").write_text(text, encoding="utf-8")
        n_block = sum(1 for f in verdict.get("findings", [])
                      if f.get("severity") in ("BLOCKER", "MAJOR"))
        print(f"  veredicto={verdict.get('verdict')} findings={len(verdict.get('findings', []))} "
              f"(blocker/major={n_block}) coste=${cost:.3f} stop={stop} "
              f"{time.monotonic()-t0:.0f}s", flush=True)
        ledger.append({"round": rnd, "stage": "review", "verdict": verdict.get("verdict"),
                       "findings": len(verdict.get("findings", [])), "blocking": n_block,
                       "costUsd": cost, "stopReason": stop})

        if stop != "end_turn":
            print("  stopReason != end_turn -> analisis truncado, no fiable", flush=True)

        if verdict.get("verdict") == "GREEN":
            print("  LUZ VERDE", flush=True)
            break
        if rnd == args.max_rounds:
            print("  tope de rondas alcanzado sin luz verde", flush=True)
            break

        print(f"=== ronda {rnd}: qwen corrige ===", flush=True)
        findings_txt = json.dumps(verdict.get("findings", []), indent=2, ensure_ascii=False)
        answer = ask_local(args.model, FIX_PROMPT.format(findings=findings_txt, code=code),
                           args.agent)
        code = extract_code(answer)
        (args.out / f"round{rnd}_fixed.c").write_text(code, encoding="utf-8")
        (args.out / f"round{rnd}_fix_notes.md").write_text(answer, encoding="utf-8")
        ledger.append({"round": rnd, "stage": "fix", "codeChars": len(code)})

    (args.out / "ledger.json").write_text(
        json.dumps({"sessionId": session_id, "ledger": ledger}, indent=2), encoding="utf-8")
    total = sum(e.get("costUsd", 0.0) for e in ledger)
    print(f"\ncoste total de cuota Grok: ${total:.3f}  ->  {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

"""Run the mutations a delivery proposes and report which ones nothing catches.

The junior can locate a rule and say no test seems to cover it, but "I found no
test" is not evidence: a test can cover a rule without naming the symbol. The
only thing that decides is breaking the rule on purpose and seeing whether the
suite goes red.

So: apply one mutation, run a bounded set of test modules, restore, repeat. A
mutation that leaves everything green is an undefended invariant -- and that is
the finding worth writing a test for.

    python run_mutations.py <delivery.md> --root <tree> [--modules m1,m2]

Parses the "### Mutación" blocks: fichero / línea / de / a.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

FIELD = {
    "fichero": "file",
    "línea": "line",
    "linea": "line",
    "de": "old",
    "a": "new",
    "rompe": "breaks",
    "espero": "expects",
}
# "- campo: value", tolerating bold and backticks around the value.
ROW = re.compile(r"^-\s*\*{0,2}([A-Za-zíé]+)\*{0,2}\s*:\s*(.*)$")


def parse(text: str) -> list[dict]:
    out: list[dict] = []
    current: dict | None = None
    for raw in text.splitlines():
        if raw.strip().startswith("### Mutaci"):
            if current and current.get("file"):
                out.append(current)
            current = {}
            continue
        if current is None:
            continue
        m = ROW.match(raw.strip())
        if not m:
            # A blank line after we have the four fields ends the block.
            if not raw.strip() and current.get("new") is not None:
                out.append(current)
                current = None
            continue
        key = FIELD.get(m.group(1).strip().lower())
        if key:
            current[key] = m.group(2).strip().strip("`")
    if current and current.get("file"):
        out.append(current)
    return [m for m in out if {"file", "old", "new"} <= set(m)]


def run_suite(py: Path, cwd: Path, modules: list[str]) -> tuple[bool, str]:
    proc = subprocess.run(
        [str(py), "-m", "unittest", *modules],
        cwd=cwd, capture_output=True, text=True, timeout=900,
    )
    tail = (proc.stderr or proc.stdout).strip().splitlines()
    summary = next((l for l in reversed(tail) if l.startswith(("OK", "FAILED"))), "?")
    return proc.returncode == 0, summary


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("delivery", type=Path)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--modules", default="")
    args = ap.parse_args(argv)

    tools = args.root / "tools"
    py = tools / ".venv-mcp/Scripts/python.exe"
    modules = [m for m in args.modules.split(",") if m.strip()] or [
        "tests.test_loopback",
        "tests.test_session_coordination",
        "tests.test_instance_fence",
        "tests.test_python_backlog_fixes",
        "tests.test_command_validation_coverage",
    ]

    mutations = parse(args.delivery.read_text(encoding="utf-8"))
    if not mutations:
        print("no mutation blocks found", file=sys.stderr)
        return 2

    ok, baseline = run_suite(py, tools, modules)
    print(f"baseline: {baseline}  (green={ok})\n")
    if not ok:
        print("baseline is not green; fix that before measuring mutations", file=sys.stderr)
        return 1

    undefended: list[int] = []
    for i, mut in enumerate(mutations):
        rel = mut["file"].replace("tools/", "", 1) if mut["file"].startswith("tools/") else mut["file"]
        target = (tools / rel).resolve()
        if not target.is_file():
            print(f"M{i}: NO_FILE {mut['file']}")
            continue
        raw = target.read_bytes()
        src = raw.decode("utf-8")
        if src.count(mut["old"]) != 1:
            print(f"M{i}: SKIP  ({src.count(mut['old'])} matches for the 'de' line)  {rel}")
            continue

        target.write_bytes(src.replace(mut["old"], mut["new"], 1).encode("utf-8"))
        try:
            still_green, summary = run_suite(py, tools, modules)
        finally:
            target.write_bytes(raw)   # always restore, byte for byte

        verdict = "UNDEFENDED" if still_green else "caught"
        if still_green:
            undefended.append(i)
        print(f"M{i}: {verdict:<11} {summary:<28} {rel}  -- {mut.get('breaks','')[:60]}")

    print(f"\n{len(undefended)} of {len(mutations)} mutations survive: {undefended}")
    print("Those are the invariants with no gate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

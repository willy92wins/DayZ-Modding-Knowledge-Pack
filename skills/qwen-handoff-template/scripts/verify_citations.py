#!/usr/bin/env python
"""Check every citation in a junior report against the tree on disk.

The measured failure mode of the local model is not being wrong about the
verdict -- it is fabricating the path:line and the code body that support a
verdict that may even be right. So make the report falsifiable: require a
**literal line** field per finding, then diff that text against the file.

Usage:
    python verify_citations.py <report.md> <root> [--ext .py,.c]

The report must contain blocks shaped like:

    ### B-01
    - **fichero**: pkg/mod.py:627
    - **linea literal**: filePtr = open(fileName, "rb")

Verdicts are graded on purpose, because "the anchor is two lines off" and "this
text exists nowhere in the repository" are different problems and only one of
them invalidates the report:

  OK            the quoted text is at the cited line
  OK_OFFSET     within +/-5 lines (sloppy anchor, real code)
  OK_ELSEWHERE  in the cited file but far away
  WRONG_FILE    in the tree, in a different file
  FABRICATED    nowhere in the tree            <- the report dies here
  BAD_RANGE     the cited line is past EOF
  NO_FILE       the cited file does not exist
  NO_LITERAL    the finding did not quote a line at all

Exit code is 1 if any finding is FABRICATED / WRONG_FILE / NO_FILE / NO_LITERAL,
so this can gate a pipeline instead of being read by eye.
"""
import argparse
import re
import sys
from pathlib import Path

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv"}
FATAL = {"FABRICATED", "WRONG_FILE", "NO_FILE", "NO_LITERAL", "BAD_RANGE"}


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().strip("`").strip()


def load_tree(root: Path, globs) -> dict:
    tree = {}
    for pat in globs:
        for p in sorted(root.rglob(pat)):
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            rel = str(p.relative_to(root)).replace("\\", "/")
            tree[rel] = p.read_text(encoding="utf-8", errors="replace").splitlines()
    return tree


def field(block: str, *names) -> str:
    """Read a report field, tolerating a decorated field name.

    The name only has to START with what we ask for: `**fichero**`,
    `**fichero:linea**` and `**fichero:línea**` are the same field. Demanding an
    exact match returned NO_FILE on all 8 citations of a report whose 8 citations
    were correct -- the brief said one name and the parser wanted another, and the
    gate reported it as fabrication (SP-313, measured 2026-08-22 on two models,
    neither of which had invented anything).
    """
    for name in names:
        m = re.search(r"^\s*[-*]?\s*\*\*%s[^*]*\*\*\s*:\s*(.+)$" % re.escape(name),
                      block, re.M | re.I)
        if m:
            return m.group(1).strip()
    return ""


def parse(report: str) -> list:
    out = []
    for b in re.split(r"^###\s+", report, flags=re.M)[1:]:
        loc = field(b, "fichero", "file")
        m = re.match(r"(.+?):(\d+)", loc)
        out.append({
            "id": b.splitlines()[0].strip(),
            "file": m.group(1).strip() if m else loc,
            "line": int(m.group(2)) if m else None,
            "literal": field(b, "linea literal", "línea literal", "literal line"),
            "sev": field(b, "severidad", "severity"),
            "claim": field(b, "hecho", "afirmacion", "afirmación", "claim"),
        })
    return out


def check(f: dict, tree: dict):
    want = norm(f["literal"])
    if not want:
        return "NO_LITERAL", ""
    lines = tree.get(f["file"])
    if lines is None:
        alt = [k for k in tree if k.endswith("/" + f["file"]) or k == f["file"]]
        if not alt:
            return "NO_FILE", ""
        f["file"] = alt[0]
        lines = tree[alt[0]]
    n = f["line"]
    if n is None or n < 1 or n > len(lines):
        # An anchor past EOF is a broken citation, but it is only fatal when the
        # text is not in the file either. Found-but-mislocated is a bad anchor;
        # not-found is a claim about code that is not there. A mutation test
        # (line 446 -> 99446) is what showed these two were being conflated and
        # the gate was letting the bad one through with exit 0.
        hits = [i + 1 for i, l in enumerate(lines) if want in norm(l)]
        if hits:
            return "OK_ELSEWHERE", "linea citada fuera de rango (fichero tiene %d); texto en %s" % (
                len(lines), hits[:3])
        return "BAD_RANGE", "fichero tiene %d lineas" % len(lines)
    if want in norm(lines[n - 1]):
        return "OK", ""
    for d in range(1, 6):
        for cand in (n - 1 - d, n - 1 + d):
            if 0 <= cand < len(lines) and want in norm(lines[cand]):
                return "OK_OFFSET", "linea real %d (delta %+d)" % (cand + 1, cand + 1 - n)
    hits = [i + 1 for i, l in enumerate(lines) if want in norm(l)]
    if hits:
        return "OK_ELSEWHERE", "en lineas %s" % hits[:3]
    for rel, ls in tree.items():
        for i, l in enumerate(ls):
            if want in norm(l):
                return "WRONG_FILE", "%s:%d" % (rel, i + 1)
    return "FABRICATED", ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report", type=Path)
    ap.add_argument("root", type=Path)
    ap.add_argument("--ext", default=".py,.c")
    a = ap.parse_args()

    globs = tuple(
        e if e.startswith("*") else "*" + (e if e.startswith(".") else "." + e)
        for e in (x.strip() for x in a.ext.split(",")) if e
    )
    tree = load_tree(a.root.resolve(), globs)
    findings = parse(a.report.read_text(encoding="utf-8", errors="replace"))
    print("arbol: %d ficheros %s" % (len(tree), list(globs)))
    print("hallazgos parseados: %d\n" % len(findings))
    if not tree:
        print("ABORT: arbol vacio, no se puede verificar nada.")
        return 1

    tally = {}
    for f in findings:
        v, extra = check(f, tree)
        tally[v] = tally.get(v, 0) + 1
        print("%-6s %-9s %-34s %s %s" % (
            f["id"], f["sev"][:9], "%s:%s" % (f["file"], f["line"]), v, extra))
        if f["claim"]:
            print("        %s" % f["claim"][:110])
        if v in FATAL or v == "BAD_RANGE":
            print("        citado: %s" % norm(f["literal"])[:110])
            ls = tree.get(f["file"])
            if ls and f["line"] and 0 < f["line"] <= len(ls):
                print("        real  : %s" % norm(ls[f["line"] - 1])[:110])

    print("\n=== veredicto de citas ===")
    for k, v in sorted(tally.items(), key=lambda x: -x[1]):
        print("  %-14s %d" % (k, v))
    solid = sum(v for k, v in tally.items() if k.startswith("OK"))
    print("  ---")
    print("  citas que resisten: %d de %d" % (solid, len(findings)))
    bad = sum(v for k, v in tally.items() if k in FATAL)
    if bad:
        print("\n  %d cita(s) no resisten: el informe NO se acepta tal cual." % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

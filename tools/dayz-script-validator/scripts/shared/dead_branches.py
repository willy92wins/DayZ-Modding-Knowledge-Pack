"""Lines of a script that the preprocessor provably never compiles.

Used by rules whose finding is wrong wherever the code compiles (a keyword
used as a name, `%` in a float expression). A branch under another mod's
#ifdef is still judged, because it compiles once that mod is loaded. What is
never compiled is not judged:

  - lines under `#if` / `#elif` (Enforce scripts use #ifdef / #ifndef; an
    `#if 0` block is how code is switched off);
  - the `#ifndef X` branch, or the `#else` of `#ifdef X`, when this file
    #defines X before that point on a line it always keeps (outside every
    block, or under an #ifdef of a macro it #defined the same way).
"""

import re

_OPEN_RE = re.compile(r"^\s*#\s*(?P<kind>ifdef|ifndef)\s+(?P<macro>\w+)")
_IF_RE = re.compile(r"^\s*#\s*if\b")
_ELIF_RE = re.compile(r"^\s*#\s*elif\b")
_ELSE_RE = re.compile(r"^\s*#\s*else\b")
_ENDIF_RE = re.compile(r"^\s*#\s*endif\b")
_DEFINE_RE = re.compile(r"^\s*#\s*define\s+(?P<name>\w+)")


def dead_lines(stripped):
    """Set of 1-based line numbers that never compile (directives included)."""
    dead = set()
    defined = set()
    # Each entry: (macro or None, branch taken when the macro is defined).
    stack = []
    for number, line in enumerate(stripped.split("\n"), start=1):
        opened = _OPEN_RE.match(line)
        if opened:
            stack.append((opened.group("macro"), opened.group("kind") == "ifdef"))
            dead.add(number)
            continue
        if _IF_RE.match(line):
            stack.append((None, True))
            dead.add(number)
            continue
        if _ELIF_RE.match(line):
            if stack:
                stack[-1] = (None, True)
            dead.add(number)
            continue
        if _ELSE_RE.match(line):
            if stack:
                macro, when_defined = stack[-1]
                stack[-1] = (macro, not when_defined)
            dead.add(number)
            continue
        if _ENDIF_RE.match(line):
            if stack:
                stack.pop()
            dead.add(number)
            continue
        if line.lstrip().startswith("#"):
            define = _DEFINE_RE.match(line)
            always = all(
                macro is not None and macro in defined and when_defined
                for macro, when_defined in stack
            )
            if define and always:
                defined.add(define.group("name"))
            dead.add(number)
            continue
        if any(
            macro is None or (macro in defined and not when_defined)
            for macro, when_defined in stack
        ):
            dead.add(number)
    return dead

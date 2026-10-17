import re

from shared.dead_branches import dead_lines


ES_MULTILINE_CONDITION_OPERATOR_RULE_ID = "ES-MULTILINE-CONDITION-OPERATOR"


# claim: CLAIM-ENFORCE-MULTILINE-CONDITION-OPERATOR
# WARN, not FAIL: one measurement, and the vanilla control has not run yet.
# Pipeline inbox fb-20261006-030019-e074, DayZ 1.30.164014 server: the
# condition
#
#   if ((t >= A && t < B) ||
#       (t >= C && t < D))
#       return -1.0;
#
# was refused with `Invalid statement ')'` and `Syntax error` at the
# continuation line. The same parser rule, with the operator leading the next
# line instead, is SP-386 (enforce-script-reference SKILL.md, "A newline
# terminates the statement ALSO in a condition": `Expected ')'` on
# LFHeli_Base.c); that form is not reported here. No `if` or `while` header
# ending in `&&` or `||` was found in the DayZ-MCP addon (compiles on 1.29
# and 1.30) or in any .c file of this pack.
#
# Reported: a line inside the parentheses of an `if (` or `while (` that ends
# in `&&` or `||` once comments are dropped, once per header. A header whose
# parenthesis never closes is left to ES-UNBALANCED-BRACKETS. Lines that
# never compile (shared/dead_branches.py) are not judged.

_HEADER_RE = re.compile(r"\b(?:if|while)\s*\(")
_TRAILING_RE = re.compile(r"(?:&&|\|\|)[ \t\r]*$")

ES_MULTILINE_CONDITION_OPERATOR_MESSAGE = (
    "[WARN] {rel_path} line {line}: this condition goes on to the next line "
    "after a trailing '{operator}'. DayZ 1.30.164014 refused such a condition "
    "with \"Invalid statement ')'\" and \"Syntax error\" at the continuation, "
    "and the script module did not compile. Keep the condition on one line, "
    "or compute its parts into bool locals first."
)


def check_es_multiline_condition_operator(stripped_source, rel_path):
    warnings = []
    dead = None
    for match in _HEADER_RE.finditer(stripped_source):
        depth = 1
        index = match.end()
        while index < len(stripped_source) and depth > 0:
            char = stripped_source[index]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            index += 1
        span = stripped_source[match.end():index]
        if depth > 0 or "\n" not in span:
            continue
        line = stripped_source.count("\n", 0, match.end()) + 1
        for offset, piece in enumerate(span.split("\n")[:-1]):
            trailing = _TRAILING_RE.search(piece)
            if trailing is None:
                continue
            if dead is None:
                dead = dead_lines(stripped_source)
            if line + offset in dead:
                continue
            warnings.append(
                {
                    "check": ES_MULTILINE_CONDITION_OPERATOR_RULE_ID,
                    "file": rel_path,
                    "line": line + offset,
                    "message": ES_MULTILINE_CONDITION_OPERATOR_MESSAGE.format(
                        rel_path=rel_path, line=line + offset,
                        operator=trailing.group(0).strip(),
                    ),
                    "severity": "WARN",
                    "rule_id": ES_MULTILINE_CONDITION_OPERATOR_RULE_ID,
                }
            )
            break
    return warnings

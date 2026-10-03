import re

from shared.dead_branches import dead_lines


ES_MODULO_FLOAT_CONTEXT_RULE_ID = "ES-MODULO-FLOAT-CONTEXT"


# claim: CLAIM-ENFORCE-MODULO-FLOAT-CONTEXT
# `%` compiles between integers, but not inside an arithmetic expression that
# also holds a float literal, even when both operands of `%` are integers:
#
#   `((g % 5) - 2) * 7.0`, DayZDiag 1.29, 2026-09-28:
#     SCRIPT (E): lfpg_probe3d.c,255: Unknown operator '%'
#     SCRIPT (E): Can't compile "Mission" script module!
#   `float ox = (n % 4) * 0.7 - 1.05;`, DayZ 1.30 (Exp), 2026-09-24: the
#     same error, and the mission did not compile.
#
# Both compiled once the `%` went into an int local first. Vanilla 1.29 holds
# 69 `%` operators and none shares an expression with a float literal.
#
# The expression around a `%` is walked out through grouping parentheses and
# stops at `;` `,` `{` `}`, an assignment, a comparison or logical operator,
# `?` `:`, `return`, an index bracket, and the parentheses of a call or of
# if/while/for/switch. A float literal counts only at that level or inside
# grouping parentheses: one inside a call's arguments or an index belongs to
# another expression. An expression that holds a string literal is not judged:
# there `+` concatenates, and no failure is on record for that case. A float
# VARIABLE is not seen (types are not tracked): only the literal case is found.
# What never compiles (shared/dead_branches.py) is not judged.

_TOKEN_RE = re.compile(
    r"(?P<float>(?<![\w.])(?:\d+\.\d*|\.\d+)(?:[eE][-+]?\d+)?f?(?![\w.]))"
    r"|(?P<num>(?<![\w.])\d+(?:[eE][-+]?\d+)?\w*)"
    r"|(?P<ident>[A-Za-z_]\w*)"
    r"|(?P<op>==|!=|<=|>=|&&|\|\||\+=|-=|\*=|/=|%=|\|=|&=|\^=|<<=|>>=|<<|>>"
    r"|\+\+|--|[-+*/%<>=!?:;,.{}()\[\]&|^~])"
)

_STOP_OPS = {
    ";", ",", "{", "}", "=", "+=", "-=", "*=", "/=", "%=", "|=", "&=", "^=",
    "<<=", ">>=", "==", "!=", "<", ">", "<=", ">=", "&&", "||", "?", ":",
}
_STOP_WORDS = {"return", "case", "new", "delete"}


def _tokens(stripped):
    """(kind, text, line, start, end) for every token of the stripped source."""
    tokens = []
    line = 1
    pos = 0
    for match in _TOKEN_RE.finditer(stripped):
        line += stripped.count("\n", pos, match.start())
        pos = match.start()
        tokens.append((match.lastgroup, match.group(), line, match.start(), match.end()))
    return tokens


def _matching(tokens):
    """Index of the partner of every bracket token; unbalanced ones map to None."""
    partner = {}
    stack = []
    pairs = {")": "(", "]": "["}
    for index, token in enumerate(tokens):
        text = token[1]
        if text in ("(", "["):
            stack.append(index)
        elif text in (")", "]"):
            while stack and tokens[stack[-1]][1] != pairs[text]:
                partner[stack.pop()] = None
            if stack:
                opener = stack.pop()
                partner[opener] = index
                partner[index] = opener
            else:
                partner[index] = None
        elif text in ("{", "}", ";"):
            while stack:
                partner[stack.pop()] = None
    while stack:
        partner[stack.pop()] = None
    return partner


def _is_call_or_control(tokens, open_index):
    """An opening parenthesis that belongs to a call or to if/while/for/switch."""
    if open_index == 0:
        return False
    kind, text = tokens[open_index - 1][:2]
    if kind == "ident":
        return text not in _STOP_WORDS
    return text in (")", "]")


def _is_stop(token):
    kind, text = token[:2]
    return text in _STOP_OPS or (kind == "ident" and text in _STOP_WORDS)


def _span(tokens, partner, index):
    """(first, last) token indexes of the arithmetic expression holding `index`."""
    first = index
    cursor = index - 1
    while cursor >= 0:
        text = tokens[cursor][1]
        if text in (")", "]"):
            opener = partner.get(cursor)
            if opener is None:
                break
            first = opener
            cursor = opener - 1
            continue
        if text == "(":
            if _is_call_or_control(tokens, cursor):
                break
            first = cursor
            cursor -= 1
            continue
        if text == "[" or _is_stop(tokens[cursor]):
            break
        first = cursor
        cursor -= 1
    last = index
    cursor = index + 1
    while cursor < len(tokens):
        text = tokens[cursor][1]
        if text in ("(", "["):
            closer = partner.get(cursor)
            if closer is None:
                break
            last = closer
            cursor = closer + 1
            continue
        if text == ")":
            opener = partner.get(cursor)
            if opener is None or _is_call_or_control(tokens, opener):
                break
            last = cursor
            cursor += 1
            continue
        if text == "]" or _is_stop(tokens[cursor]):
            break
        last = cursor
        cursor += 1
    return first, last


def _float_literal_at_level(tokens, partner, first, last):
    cursor = first
    while cursor <= last:
        kind, text = tokens[cursor][:2]
        if kind == "float":
            return text
        if text == "[" or (text == "(" and _is_call_or_control(tokens, cursor)):
            closer = partner.get(cursor)
            if closer is None:
                return None
            cursor = closer + 1
            continue
        cursor += 1
    return None


def _holds_string_literal(source, start, end):
    """The stripper blanks strings in place, so offsets match the source."""
    return '"' in source[start:end]


ES_MODULO_FLOAT_CONTEXT_MESSAGE = (
    "[FAIL] {rel_path} line {line}: '%' is used in an expression that also "
    "holds the float literal {literal}. Enforce types the whole expression as "
    "float and has no float '%': the compiler stops with \"Unknown operator "
    "'%'\" and the script module fails to load. Compute the '%' into an int "
    "local first, then use that local in the float expression."
)


def check_es_modulo_float_context(source, stripped_source, rel_path):
    if "%" not in stripped_source:
        return []
    tokens = _tokens(stripped_source)
    partner = _matching(tokens)
    dead = dead_lines(stripped_source)
    errors = []
    seen_lines = set()
    for index, token in enumerate(tokens):
        if token[1] != "%":
            continue
        line = token[2]
        if line in dead:
            continue
        first, last = _span(tokens, partner, index)
        literal = _float_literal_at_level(tokens, partner, first, last)
        if literal is None or line in seen_lines:
            continue
        if _holds_string_literal(source, tokens[first][3], tokens[last][4]):
            continue
        seen_lines.add(line)
        errors.append(
            {
                "check": ES_MODULO_FLOAT_CONTEXT_RULE_ID,
                "file": rel_path,
                "line": line,
                "message": ES_MODULO_FLOAT_CONTEXT_MESSAGE.format(
                    rel_path=rel_path, line=line, literal=literal
                ),
                "severity": "FAIL",
                "rule_id": ES_MODULO_FLOAT_CONTEXT_RULE_ID,
            }
        )
    return errors

import re

from detectors.pdrive_path import strip_comments_keep_strings


ES_STRING_PLUS_BOOL_RULE_ID = "ES-STRING-PLUS-BOOL"


# Concatenating a string with a bool does not compile. `string + int` and
# `string + float` do compile.
#
# The main stripper blanks string literals, so a stripped buffer never still
# contains `"x" + true`. This check therefore walks a comments-removed,
# strings-kept copy (strip_comments_keep_strings) instead of the stripped
# buffer.
#
# Scope is deliberately narrow: only a string literal joined with the tokens
# `true` or `false`, in either order. `prefix + myBool` is a known false
# negative -- without a type checker a variable on either side cannot be
# proven to be string-plus-bool, and a false positive is worse than a miss.
_STRING_LITERAL = r'"(?:[^"\\]|\\.)*"'

ES_STRING_PLUS_BOOL_RE = re.compile(
    r"(?:"
    + _STRING_LITERAL
    + r"\s*\+\s*(?:true|false)\b"
    + r"|(?:true|false)\b\s*\+\s*"
    + _STRING_LITERAL
    + r")"
)


ES_STRING_PLUS_BOOL_MESSAGE = (
    "[FAIL] {rel_path} line {line}: string literal concatenated with a bool. "
    "`string + bool` does not compile; `string + int` and `string + float` "
    "do. Convert the bool before concatenating."
)


def check_es_string_plus_bool(source, rel_path):
    cleaned = strip_comments_keep_strings(source)
    errors = []

    for match in ES_STRING_PLUS_BOOL_RE.finditer(cleaned):
        line_number = cleaned.count("\n", 0, match.start()) + 1
        message = ES_STRING_PLUS_BOOL_MESSAGE.format(
            rel_path=rel_path, line=line_number
        )
        errors.append(
            {
                "check": ES_STRING_PLUS_BOOL_RULE_ID,
                "file": rel_path,
                "line": line_number,
                "message": message,
                "severity": "FAIL",
                "rule_id": ES_STRING_PLUS_BOOL_RULE_ID,
            }
        )

    return errors

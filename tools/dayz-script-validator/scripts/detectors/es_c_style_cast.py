import re


ES_C_STYLE_CAST_RULE_ID = "ES-C-STYLE-CAST"


# Enforce Script has no C-style cast. Forms `(int)x`, `(float)y`, `(bool)z`
# and `(string)w` do not compile. Conversion is `Math.Floor` / `Math.Round` /
# `.ToInt()` or string concatenation (`"" + n`).
#
# Runs on source that already had comments and string literals stripped, so a
# cast mentioned inside a literal or comment is not flagged.
#
# Parameter lists such as `void Foo(int x)` are not casts: the closing `)`
# must sit immediately after the type token, and the next token must be an
# identifier or an opening parenthesis. That rejects `(int x)` while still
# matching `(int)x` and `(int)(expr)`.
ES_C_STYLE_CAST_RE = re.compile(
    r"\(\s*(?P<type>int|float|bool|string)\s*\)\s*(?:[A-Za-z_]\w*|\()"
)


ES_C_STYLE_CAST_MESSAGE = (
    "[FAIL] {rel_path} line {line}: C-style cast `({type})`. Enforce Script "
    "has no C-style casts; the construct does not compile. Convert with "
    "Math.Floor / Math.Round / .ToInt() or string concatenation (`\"\" + n`)."
)


def check_es_c_style_cast(stripped_source, rel_path):
    errors = []

    for match in ES_C_STYLE_CAST_RE.finditer(stripped_source):
        line_number = stripped_source.count("\n", 0, match.start()) + 1
        message = ES_C_STYLE_CAST_MESSAGE.format(
            rel_path=rel_path,
            line=line_number,
            type=match.group("type"),
        )
        errors.append(
            {
                "check": ES_C_STYLE_CAST_RULE_ID,
                "file": rel_path,
                "line": line_number,
                "message": message,
                "severity": "FAIL",
                "rule_id": ES_C_STYLE_CAST_RULE_ID,
            }
        )

    return errors

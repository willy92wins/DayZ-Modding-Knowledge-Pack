import re


ES_NO_DELETE_RULE_ID = "ES-NO-DELETE"


ES_NO_DELETE_RE = re.compile(r"\bdelete\s+\w")


ES_NO_DELETE_MESSAGE = (
    "[FAIL] {rel_path} line {line}: 'delete' keyword used. Enforce Script uses "
    "ARC garbage collection; 'delete' on live object causes segfault (SKILL.md "
    "rule 14, memory-management.md:82). Replace with 'obj = null;'."
)


def check_es_no_delete(stripped_source, rel_path):
    errors = []

    for match in ES_NO_DELETE_RE.finditer(stripped_source):
        line_number = stripped_source.count("\n", 0, match.start()) + 1
        message = ES_NO_DELETE_MESSAGE.format(rel_path=rel_path, line=line_number)
        errors.append(
            {
                "check": ES_NO_DELETE_RULE_ID,
                "file": rel_path,
                "line": line_number,
                "message": message,
                "severity": "FAIL",
                "rule_id": ES_NO_DELETE_RULE_ID,
            }
        )

    return errors

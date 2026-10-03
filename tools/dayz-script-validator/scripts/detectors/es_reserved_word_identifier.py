import re

from shared.dead_branches import dead_lines


ES_RESERVED_WORD_IDENTIFIER_RULE_ID = "ES-RESERVED-WORD-IDENTIFIER"


# claim: CLAIM-ENFORCE-RESERVED-WORD-NAME
# A variable, member or parameter named with an Enforce keyword stops the
# whole script module from compiling, and the error rarely names the word.
# Only words whose use as a name failed in a real compile are listed:
#
#   sealed  parameter `vector sealed`, DayZDiag 1.29.163709, 2026-10-02:
#           `Expected name, not a keyword 'sealed'`, then
#           `Can't compile "World" script module!`
#   local   local `vector local;`, DayZDiag 1.30.164014 (Exp), 2026-09-28:
#           `Broken expression (missing ';'?)`, then
#           `Can't compile "Mission" script module!`
#   owned   local `EntityAI owned;`, 2026-07-20: `Broken expression (missing
#           ';'?)` (enforce-script-reference SKILL.md, SP-073)
#   out     a local named `out`: `Broken expression (missing ';'?)`
#           (enforce-script-reference SKILL.md, "Three ways to break the
#           compiler that do not produce a readable error")
#
# Vanilla uses all four as keywords, never as names: `sealed class Contact`
# (1_core/physics/contact.c:9), `local array<string> overridden`
# (4_world/plugins/pluginbase/pluginconfigviewer.c:153), `proto owned string
# GetModule()` (1_core/proto/enconvert.c:536), `out array<Man> players`
# (3_game/global/game.c:947). Other modifiers vanilla uses the same way
# (notnull, inout, autoptr, reference, volatile, external, event...) are left
# out until a compile failure is on record for them.
#
# The name fails wherever it compiles, so code under another mod's #ifdef is
# judged too; what never compiles (shared/dead_branches.py) is not.
RESERVED_WORDS = ("sealed", "local", "owned", "out")

_NOT_A_TYPE = {
    "return", "new", "delete", "else", "case", "typedef", "class", "enum",
    "goto", "extends", "modded", "override", "proto", "native", "static",
    "const", "private", "protected", "ref", "autoptr", "notnull", "inout",
    "out", "owned", "local", "reference", "event", "external", "volatile",
    "thread", "sealed", "if", "while", "for", "foreach", "switch", "break",
    "continue", "default",
}

# `Type <word>` followed by what can only follow a declared name: `;`, `=`
# (not `==`), `[`, `,` or `)`. The leading `(` / `,` covers parameters; the
# leading `;`, `{`, `}` or start of line covers locals and members.
_DECL_RE = re.compile(
    r"(?:^|[;{}(,])[ \t]*"
    r"(?:(?:ref|autoptr|const|static|private|protected|owned|notnull|out|"
    r"inout|local|reference)[ \t]+)*"
    r"(?P<type>[A-Za-z_]\w*)(?:[ \t]*<[^;{}()\n]*?>)?(?:[ \t]*\[[^\]\n]*\])?"
    r"[ \t]+(?P<name>" + "|".join(RESERVED_WORDS) + r")\b"
    r"[ \t]*(?=;|=(?!=)|\[|,|\))",
    re.M,
)

ES_RESERVED_WORD_IDENTIFIER_MESSAGE = (
    "[FAIL] {rel_path} line {line}: '{name}' is an Enforce keyword and cannot "
    "name a variable, member or parameter. The compiler rejects the whole "
    "script module, often with an error that does not name the word "
    "(\"Broken expression (missing ';'?)\", or \"Expected name, not a keyword "
    "'{name}'\"). Rename it."
)


def check_es_reserved_word_identifier(stripped_source, rel_path):
    errors = []
    seen = set()
    dead = None
    for match in _DECL_RE.finditer(stripped_source):
        if match.group("type") in _NOT_A_TYPE:
            continue
        line = stripped_source.count("\n", 0, match.start("name")) + 1
        name = match.group("name")
        if dead is None:
            dead = dead_lines(stripped_source)
        if (line, name) in seen or line in dead:
            continue
        seen.add((line, name))
        errors.append(
            {
                "check": ES_RESERVED_WORD_IDENTIFIER_RULE_ID,
                "file": rel_path,
                "line": line,
                "message": ES_RESERVED_WORD_IDENTIFIER_MESSAGE.format(
                    rel_path=rel_path, line=line, name=name
                ),
                "severity": "FAIL",
                "rule_id": ES_RESERVED_WORD_IDENTIFIER_RULE_ID,
            }
        )
    return errors

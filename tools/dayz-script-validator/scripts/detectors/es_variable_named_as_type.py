import functools
import pathlib
import re

from detectors.es_reserved_word_identifier import (
    _FIRST_DECL_RE,
    _MODIFIERS,
    _NOT_A_TYPE,
    _TYPE,
)
from detectors.es_undefined_class_ref import (
    VANILLA_ANCHOR_CLASS,
    Definitions,
    vanilla_definitions,
)
from shared.dead_branches import dead_lines


ES_VARIABLE_NAMED_AS_TYPE_RULE_ID = "ES-VARIABLE-NAMED-AS-TYPE"


# claim: CLAIM-ENFORCE-VARIABLE-NAMED-AS-TYPE
# A variable, member or parameter whose name is already a type name stops the
# whole script module from compiling. Measured twice:
#
#   member  `bool Debug;` in a settings class (scripts/4_World), DayZDiag
#           1.29, 2026-09-28, pipeline inbox fb-20260928-025254-35c1
#           (corrected by 7ce1): the client refused the module with
#           `Variable name 'Debug' already used as type name`. Debug is a
#           vanilla class (3_game/tools/debug.c).
#   local   `Widget map = root.FindAnyWidget("mapWidget")`:
#           `Variable name 'map' already used as type name`, then
#           `Can't compile "Mission" script module!`
#           (enforce-script-reference pitfalls-advanced.md, SP-317).
#
# Parameters, and names that are an enum or a typedef rather than a class,
# have no failure on record; they are judged the same way because the error
# names a type, not a class. The match is exact case: Enforce identifiers are
# case-sensitive (enforce-script-reference SKILL.md, "A method named exactly
# like a vanilla class"), and no failure with a case-only match is on record,
# so a member `debug` is not reported.
#
# Type names come from the addon, every --external-scripts root and the
# vanilla tree. A module sees only the types of its own and lower modules, so
# a name is judged against the types declared in a module at or below the
# file's (a type whose module is unknown counts only for a file whose module
# is unknown). Without a usable vanilla tree only the addon and the external
# roots are judged, and the vanilla part is listed as skipped in the report.
# The name fails wherever it compiles, so code under another mod's #ifdef is
# judged too; what never compiles (shared/dead_branches.py) is not.

# `Type <name>` followed by what can only follow a declared name, as in
# ES-RESERVED-WORD-IDENTIFIER, with any name.
_DECL_RE = re.compile(
    r"(?:^|[;{}(,])[ \t]*" + _MODIFIERS + _TYPE
    + r"\s+(?P<name>[A-Za-z_]\w*)\s*(?=;|=(?!=)|\[|,|\)|:(?!:))",
    re.M,
)
_LATER_NAME_RE = re.compile(r",\s*(?P<name>[A-Za-z_]\w*)\s*(?=;|=(?!=)|\[|,)")

_MODULE_RE = re.compile(r"(?:^|[\\/])(?P<rank>[1-5])_[A-Za-z]+[\\/]")
_UNKNOWN_MODULE = 99

# Vanilla is read raw: comments are dropped (a block comment line that starts
# with `class X` would declare X), strings are kept so a `//` or `/*` inside
# one does not cut the text.
_RAW_TOKEN_RE = re.compile(r'"(?:\\.|[^"\\\n])*"|//[^\n]*|/\*.*?\*/', re.S)

ES_VARIABLE_NAMED_AS_TYPE_MESSAGE = (
    "[FAIL] {rel_path} line {line}: '{name}' names a variable, member or "
    "parameter, but '{name}' is already a type ({where}). The compiler "
    "refuses it with \"Variable name '{name}' already used as type name\" and "
    "the whole script module does not compile. Rename it."
)


def module_rank(rel_path):
    """1..5 for a file under N_Module/, _UNKNOWN_MODULE otherwise."""
    match = _MODULE_RE.search(str(rel_path).replace("\\", "/"))
    return int(match.group("rank")) if match else _UNKNOWN_MODULE


def _without_comments(text):
    return _RAW_TOKEN_RE.sub(
        lambda m: m.group(0) if m.group(0).startswith('"') else " ", text
    )


def declared_type_names(text):
    """Class, enum and typedef names declared in one text."""
    definitions = Definitions()
    definitions.add_source(text, variables=False)
    return definitions.types


@functools.lru_cache(maxsize=4)
def vanilla_sources(vanilla_key):
    """((relative path, text without comments), ...) of the vanilla tree."""
    root = pathlib.Path(vanilla_key)
    sources = []
    for path in sorted(root.rglob("*.c")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        sources.append((path.relative_to(root).as_posix(), _without_comments(text)))
    return tuple(sources)


@functools.lru_cache(maxsize=4)
def vanilla_type_ranks(vanilla_key):
    """{type name: lowest module rank that declares it} over the vanilla tree."""
    ranks = {}
    for rel_path, text in vanilla_sources(vanilla_key):
        rank = module_rank(rel_path)
        for name in declared_type_names(text):
            ranks[name] = min(rank, ranks.get(name, _UNKNOWN_MODULE))
    return ranks


def usable_vanilla_key(vanilla_root):
    """Resolved key of a vanilla tree that declares class Managed, or None."""
    if vanilla_root is None:
        return None
    key = str(pathlib.Path(vanilla_root).resolve())
    if VANILLA_ANCHOR_CLASS not in vanilla_definitions(key).classes:
        return None
    return key


def _inside_template_args(stripped, offset):
    """True when offset sits inside an unclosed `<` of its own statement.

    A comma between template arguments (`Param3<bool, vector, int>`,
    `typedef map<string, ref array<string>> Name;`) is not a declarator
    separator; vanilla control 2026-10-13 found 104 (1.29) and 109 (1.30)
    such false findings before this check.
    """
    start = max(stripped.rfind(c, 0, offset) for c in ";{}") + 1
    depth = 0
    for char in stripped[start:offset]:
        if char == "<":
            depth += 1
        elif char == ">" and depth:
            depth -= 1
    return depth > 0


def _declared_names(stripped):
    """(offset, name) of every name in a declared-name position."""
    for match in _DECL_RE.finditer(stripped):
        if match.group("type") in _NOT_A_TYPE:
            continue
        if stripped[match.start()] == "," and _inside_template_args(
            stripped, match.start()
        ):
            continue
        yield match.start("name"), match.group("name")
    for match in _FIRST_DECL_RE.finditer(stripped):
        if match.group("type") in _NOT_A_TYPE:
            continue
        depth = 0
        cursor = match.end()
        while cursor < len(stripped):
            char = stripped[cursor]
            if char in "([{":
                depth += 1
            elif char in ")]}":
                depth -= 1
                if depth < 0:
                    break
            elif char == ";" and depth == 0:
                break
            elif (
                char == ","
                and depth == 0
                and not _inside_template_args(stripped, cursor)
            ):
                later = _LATER_NAME_RE.match(stripped, cursor)
                if later:
                    yield later.start("name"), later.group("name")
            cursor += 1


def _visible(rank, file_rank):
    if rank == _UNKNOWN_MODULE:
        return file_rank == _UNKNOWN_MODULE
    return rank <= file_rank


def check_es_variable_named_as_type(
    addon_sources, external_sources, vanilla_root, vanilla_skip_reason=None
):
    """Return (errors, skipped).

    addon_sources / external_sources: lists of (rel_path, stripped_source).
    """
    if not addon_sources:
        return [], []
    # {name: [(rank, where)]}, the addon first so it names the declaration.
    types = {}
    for sources, where in (
        (addon_sources, "declared in the addon"),
        (external_sources or [], "declared in an --external-scripts root"),
    ):
        for rel_path, stripped in sources:
            rank = module_rank(rel_path)
            for name in declared_type_names(stripped):
                types.setdefault(name, []).append((rank, where))
    skipped = []
    vanilla_key = usable_vanilla_key(vanilla_root)
    if vanilla_key is None:
        if vanilla_root is None:
            reason = vanilla_skip_reason or "vanilla tree not available"
        else:
            reason = "the vanilla tree %s declares no class %s" % (
                vanilla_root, VANILLA_ANCHOR_CLASS
            )
        skipped.append(
            {
                "rule_id": ES_VARIABLE_NAMED_AS_TYPE_RULE_ID,
                "status": "SKIP",
                "reason": (
                    "%s. Names were judged only against the types the addon "
                    "and the --external-scripts roots declare; a name that is "
                    "a vanilla type (such as Debug) was not judged." % reason
                ),
            }
        )
    else:
        for name, rank in vanilla_type_ranks(vanilla_key).items():
            types.setdefault(name, []).append(
                (rank, "declared in the vanilla scripts tree")
            )

    errors = []
    for rel_path, stripped in addon_sources:
        file_rank = module_rank(rel_path)
        seen = set()
        dead = None
        for offset, name in sorted(_declared_names(stripped)):
            where = next(
                (w for rank, w in types.get(name, ()) if _visible(rank, file_rank)),
                None,
            )
            if where is None:
                continue
            line = stripped.count("\n", 0, offset) + 1
            if dead is None:
                dead = dead_lines(stripped)
            if (line, name) in seen or line in dead:
                continue
            seen.add((line, name))
            errors.append(
                {
                    "check": ES_VARIABLE_NAMED_AS_TYPE_RULE_ID,
                    "file": rel_path,
                    "line": line,
                    "message": ES_VARIABLE_NAMED_AS_TYPE_MESSAGE.format(
                        rel_path=rel_path, line=line, name=name, where=where
                    ),
                    "severity": "FAIL",
                    "rule_id": ES_VARIABLE_NAMED_AS_TYPE_RULE_ID,
                }
            )
    return errors, skipped

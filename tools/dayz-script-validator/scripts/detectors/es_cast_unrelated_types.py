import re

from detectors.es_reserved_word_identifier import _MODIFIERS, _NOT_A_TYPE
from detectors.es_undefined_class_ref import (
    _ENUM_DEF_RE,
    _LAST_IDENT_RE,
    _TYPEDEF_RE,
    Definitions,
)
from detectors.es_variable_named_as_type import usable_vanilla_key, vanilla_sources
from shared.dead_branches import dead_lines
from shared.method_recognition import find_method_for_line, find_method_regions


ES_CAST_UNRELATED_TYPES_RULE_ID = "ES-CAST-UNRELATED-TYPES"


# claim: CLAIM-ENFORCE-CAST-UNRELATED-TYPES
# `X.Cast(y)` where neither X nor the declared type of y derives from the
# other stops the whole script module from compiling. Pipeline inbox
# fb-20261009-122148-c852, DayZDiag 1.29:
#
#   Mission mission = GetGame().GetMission();
#   hud = IngameHud.Cast(mission);
#
# refused the Mission module with `Types 'IngameHud' and 'Mission' are not
# related`. The message is the evidence that neither class derives from the
# other; that IngameHud derives from Hud is the ticket's word, not re-read on
# a vanilla tree for this rule.
#
# Judged only when everything is known, otherwise skipped without a word:
#   - y is a plain name (not a call or a member access) declared in
#     the same function, as a local still open at the cast or a parameter,
#     or else as a member of the enclosing class itself, with one type and
#     no template arguments or array brackets; a later declarator
#     (`int a, y;`) in the function makes y unknown;
#   - X and that type are classes of the addon, the vanilla tree (comments
#     dropped) or an --external-scripts root, not a typedef, an enum, a
#     template or its parameter, nor a primitive;
#   - the whole `extends` chain of both resolves: each class has a
#     declaration that is not `modded` (a modded class does not change the
#     hierarchy) and one parent across all of them (a forward `class X;` is
#     no declaration); a class without a parent ends the chain. Class, the implicit root, is related to everything.
#     A header that a directive splits (`class D` / `#ifdef X` / `: B` /
#     `#endif`) has a parent _CLASS_RE cannot read, so its chain does not
#     resolve.
# Without a vanilla tree a chain that reaches a vanilla class does not
# resolve, so the cast is not judged. Lines that never compile
# (shared/dead_branches.py) are not judged.

_CLASS_RE = re.compile(
    r"^[ \t]*(?P<mods>(?:(?:modded|sealed|proto|native|inherited|static|"
    r"external)\s+)*)class\s+(?P<name>[A-Za-z_]\w*)(?P<params>\s*<[^;{}>]*>)?"
    r"(?:\s*(?::|\bextends\b)\s*(?P<parent>[A-Za-z_]\w*))?(?P<after>\s*;)?",
    re.M,
)
_CAST_RE = re.compile(
    r"(?<![\w.])(?P<target>[A-Za-z_]\w*)\s*\.\s*Cast\s*\(\s*"
    r"(?P<arg>[A-Za-z_]\w*)\s*\)"
)

IMPLICIT_ROOT = "Class"
# The parent of a class whose header a directive splits: no class has it.
UNREAD_PARENT = "#"
PRIMITIVES = {
    "int", "float", "bool", "string", "vector", "typename", "void", "auto",
    "func",
}

ES_CAST_UNRELATED_TYPES_MESSAGE = (
    "[FAIL] {rel_path} line {line}: '{target}.Cast({arg})': '{arg}' is "
    "declared as {arg_type}, and neither class derives from the other "
    "({target_chain}; {arg_chain}). The compiler refuses it with \"Types "
    "'{target}' and '{arg_type}' are not related\" and the whole script "
    "module does not compile. Get the object from an API that returns a "
    "related type (a HUD from the mission's GetHud(), not from the mission)."
)


def class_parent(text, match):
    """The parent of a _CLASS_RE match, None, or UNREAD_PARENT.

    The header runs from the match to the first `{` or `;`; a `#` in it is a
    directive (comments and strings are gone), and the parent behind it is
    not read.
    """
    ends = [
        i for i in (text.find("{", match.end()), text.find(";", match.end()))
        if i >= 0
    ]
    if "#" in text[match.end():min(ends, default=len(text))]:
        return UNREAD_PARENT
    return match.group("parent")


class Hierarchy:
    """Class declarations of every scanned tree, with their parents."""

    def __init__(self):
        self.declarations = {}
        self.definitions = Definitions()
        self.not_classes = set()

    def add_source(self, text):
        self.definitions.add_source(text, variables=False)
        for match in _ENUM_DEF_RE.finditer(text):
            self.not_classes.add(match.group("name"))
        for match in _TYPEDEF_RE.finditer(text):
            last = _LAST_IDENT_RE.search(match.group("body").split("//", 1)[0])
            if last:
                self.not_classes.add(last.group("name"))
        for match in _CLASS_RE.finditer(text):
            if match.group("after"):
                continue  # `class X;`: a forward declaration
            self.declarations.setdefault(match.group("name"), []).append(
                (
                    "modded" in match.group("mods").split(),
                    class_parent(text, match),
                    bool(match.group("params")),
                )
            )

    def is_plain_class(self, name):
        """A class and nothing else: no typedef, enum, template, primitive."""
        if name in PRIMITIVES or name in self.not_classes:
            return False
        if name in self.definitions.template_params:
            return False
        entries = self.declarations.get(name, ())
        return bool(entries) and not any(
            templated for _m, _p, templated in entries
        )

    def chain(self, name):
        """[name, parent, ...] up to a class without a parent, or None."""
        chain = []
        while name is not None:
            if name in chain or not self.is_plain_class(name):
                return None
            parents = {
                parent
                for modded, parent, _templated in self.declarations[name]
                if not modded
            }
            if len(parents) != 1:
                return None
            chain.append(name)
            name = parents.pop()
        return chain


def _declaration_re(name):
    return re.compile(
        r"(?:^|[;{}(,])[ \t]*" + _MODIFIERS
        + r"(?P<type>[A-Za-z_]\w*)(?P<targs>[ \t]*<[^;{}()\n]*?>)?"
        r"(?P<arr>[ \t]*\[[^\]\n]*\])?\s+" + re.escape(name)
        + r"\s*(?P<next>;|=(?!=)|\[|,|\)|:(?!:))",
        re.M,
    )


def _declared_type(match):
    """The plain type of a declaration match, or "" when not plain."""
    if match.group("type") in _NOT_A_TYPE:
        return None
    if match.group("targs") or match.group("arr") or match.group("next") == "[":
        return ""
    return match.group("type")


def _still_open(text, start, end):
    """True when no bracket open at `start` is closed before `end`."""
    depth = 0
    for char in text[start:end]:
        if char in "({":
            depth += 1
        elif char in ")}":
            depth -= 1
            if depth < 0:
                return False
    return True


def _line_offsets(stripped):
    offsets = [0]
    for index, char in enumerate(stripped):
        if char == "\n":
            offsets.append(index + 1)
    return offsets


def _class_regions(stripped):
    """(start, end) offsets of the body of each class of the file."""
    regions = []
    for match in _CLASS_RE.finditer(stripped):
        if match.group("after"):
            continue
        brace = stripped.find("{", match.end())
        if brace < 0:
            continue
        depth = 0
        for index in range(brace, len(stripped)):
            char = stripped[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    regions.append((brace, index))
                    break
    return regions


def _argument_type(stripped, offsets, dead, methods, regions, arg, cast_at):
    """The one plain declared type of `arg` at `cast_at`, or None."""
    line = stripped.count("\n", 0, cast_at) + 1
    declaration_re = _declaration_re(arg)
    method = find_method_for_line(methods, line)
    if method is not None:
        start = offsets[method["start_line"] - 1]
        body = stripped.find("{", offsets[method["brace_line"] - 1])
        scope = stripped[start:cast_at]
        if re.search(r",\s*" + re.escape(arg) + r"\s*(?=;|=(?!=)|\[)", scope):
            return None
        found = set()
        for match in declaration_re.finditer(stripped, start, cast_at):
            at = match.start("type")
            if stripped.count("\n", 0, at) + 1 in dead:
                continue
            declared = _declared_type(match)
            if declared is None:
                continue
            if at < body or _still_open(stripped, match.end(), cast_at):
                found.add(declared)
        if found:
            return found.pop() if len(found) == 1 and "" not in found else None
    enclosing = [r for r in regions if r[0] < cast_at < r[1]]
    if not enclosing:
        return None
    open_brace, close_brace = max(enclosing)
    found = set()
    for match in declaration_re.finditer(stripped, open_brace, close_brace):
        at = match.start("type")
        if stripped.count("\n", 0, at) + 1 in dead:
            continue
        inner = stripped[open_brace:at]
        if inner.count("{") - inner.count("}") != 1 or inner.count(
            "("
        ) != inner.count(")"):
            continue  # inside a method, or a parameter
        declared = _declared_type(match)
        if declared is not None:
            found.add(declared)
    if len(found) == 1 and "" not in found:
        return found.pop()
    return None


def check_es_cast_unrelated_types(addon_sources, external_sources, vanilla_root):
    """addon_sources / external_sources: lists of (rel_path, stripped_source)."""
    hierarchy = Hierarchy()
    for _rel_path, stripped in list(addon_sources) + list(external_sources or []):
        hierarchy.add_source(stripped)
    vanilla_key = usable_vanilla_key(vanilla_root)
    if vanilla_key is not None:
        for _rel_path, text in vanilla_sources(vanilla_key):
            hierarchy.add_source(text)

    errors = []
    for rel_path, stripped in addon_sources:
        dead = None
        methods = regions = offsets = None
        for match in _CAST_RE.finditer(stripped):
            target, arg = match.group("target"), match.group("arg")
            if target == IMPLICIT_ROOT:
                continue
            target_chain = hierarchy.chain(target)
            if target_chain is None:
                continue
            line = stripped.count("\n", 0, match.start()) + 1
            if dead is None:
                dead = dead_lines(stripped)
                methods = find_method_regions(stripped)
                regions = _class_regions(stripped)
                offsets = _line_offsets(stripped)
            if line in dead:
                continue
            arg_type = _argument_type(
                stripped, offsets, dead, methods, regions, arg, match.start()
            )
            if arg_type is None or arg_type == IMPLICIT_ROOT:
                continue
            arg_chain = hierarchy.chain(arg_type)
            if arg_chain is None:
                continue
            if target in arg_chain or arg_type in target_chain:
                continue
            errors.append(
                {
                    "check": ES_CAST_UNRELATED_TYPES_RULE_ID,
                    "file": rel_path,
                    "line": line,
                    "message": ES_CAST_UNRELATED_TYPES_MESSAGE.format(
                        rel_path=rel_path, line=line, target=target, arg=arg,
                        arg_type=arg_type,
                        target_chain=" > ".join(target_chain),
                        arg_chain=" > ".join(arg_chain),
                    ),
                    "severity": "FAIL",
                    "rule_id": ES_CAST_UNRELATED_TYPES_RULE_ID,
                }
            )
    return errors

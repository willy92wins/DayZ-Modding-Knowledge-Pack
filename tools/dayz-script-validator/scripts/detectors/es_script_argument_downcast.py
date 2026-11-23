import functools
import re

from detectors.es_cast_unrelated_types import (
    IMPLICIT_ROOT,
    FileScopes,
    Hierarchy,
    _argument_type,
    _class_regions,
    _line_offsets,
)
from detectors.es_protected_method_cross_class import _CALL_RE
from detectors.es_proto_argument_downcast import (
    ClassBodies,
    _NAME_RE,
    _STRING_RE,
    _WRITTEN,
    _arguments,
    _body_classes,
    _brackets,
    _inherited_member,
    _vanilla_index,
)
from detectors.es_variable_named_as_type import (
    module_rank,
    usable_vanilla_key,
    vanilla_sources,
)
from shared.dead_branches import line_branches
from shared.method_recognition import find_method_regions


ES_SCRIPT_ARGUMENT_DOWNCAST_RULE_ID = "ES-SCRIPT-ARGUMENT-DOWNCAST"


# claim: CLAIM-ENFORCE-SCRIPT-ARGUMENT-DOWNCAST
# A name, or a member through a name, passed to a parameter of a script
# method (not a `proto`), when the parameter's class derives from the
# class the argument is declared as. Pipeline inbox
# fb-20261122-205419-250d, DayZDiag 1.30.164289:
#
#   SubtreeBornInInventory(rec.m_RefEnt)
#
# with no receiver, `Object m_RefEnt` in the record class and
# `protected bool SubtreeBornInInventory(EntityAI root)` in the mod, was
# refused with "Unsafe down-casting, use 'EntityAI.Cast' for safe
# down-casting", "Types 'Object' and 'EntityAI' are unrelated" and
# "Cannot convert 'Object' to 'EntityAI' for argument '0' to method
# 'SubtreeBornInInventory'", and the Mission module did not compile. The
# compiler counts arguments from 0. With `EntityAI.Cast(rec.m_RefEnt)` in
# both calls and nothing else changed, the mod compiled.
# ES-PROTO-ARGUMENT-DOWNCAST judges only protos and said nothing. That
# Object derives from IEntity, and EntityAI from Object, is read from the
# vanilla tree when the rule runs. Only that pair is measured, so an
# Object where a script method takes an EntityAI is FAIL, and any other
# class above the parameter's is WARN.
#
# Judged only when everything is known, otherwise skipped without a word:
#   - the call is in a method that shared/method_recognition.py reads
#     (not one whose return type has template arguments, `array<T> F(`),
#     on a line that compiles (shared/dead_branches.py);
#   - it is `recv.Method(` with recv a class name, or a plain name with
#     one plain declared type read as ES-PROTO-ARGUMENT-DOWNCAST reads
#     it (`_argument_type` with `_inherited_member`), `this.Method(` with
#     the receiver the class of the class body around the call, or
#     `Method(` with no receiver inside a class body (a `modded class`
#     included), with that body as the receiver. A name preceded by a
#     dot, or by an identifier other than `return` or `else`, is no such
#     call, and a call outside every class body is a global function's
#     call. `super.Method(`, a receiver that is not a plain name and an
#     unknown receiver are skipped. With no receiver, a name that is
#     also a global function (declared outside every class body in the
#     addon, an --external-scripts root or the vanilla tree) is skipped;
#   - up the `extends` chain of the receiver's class, resolved as in
#     ES-CAST-UNRELATED-TYPES, the first class with a declaration of the
#     method on a line that compiles (modded included) decides, as
#     `ClassBodies.proto()` does, but every declaration there must be a
#     script method (no `proto`) with one parameter list. A proto there
#     is the proto rule's, and a proto beside a script method, or two
#     parameter lists, are skipped by both rules. A body that cannot be
#     read, or a declaration with a line from its start to its `(` under
#     an #if, #ifdef or #ifndef, leaves the method unknown;
#   - the argument is a plain name typed as the proto rule types it, or
#     `x.m`, exactly one dot between two plain names: the type of x (for
#     `this`, the class of the body around the call, never a local of
#     that name), then the member m up the chain of that type, the first
#     class that declares it. `super.m`, `x.y.z`, calls and anything
#     else are skipped;
#   - the parameter at the argument's index is neither `out` nor
#     `inout` and has a plain class type whose chain resolves, and that
#     chain holds the argument's class above the parameter's own.
#     Class, the implicit root, is never judged as the argument's class.
# A call whose arguments hold `<`, `>` or a directive is skipped, and so
# is one with more arguments than parameters. Script methods are read
# from the addon, every --external-scripts root and the vanilla tree, so
# without a vanilla tree no vanilla script method is judged. A down-cast
# in an assignment is not judged.

_BARE_CALL_RE = re.compile(r"(?<![\w.])(?P<method>[A-Za-z_]\w*)\s*\(")
_MEMBER_ARG_RE = re.compile(r"(?P<base>[A-Za-z_]\w*)\.(?P<member>[A-Za-z_]\w*)\Z")
_GLOBAL_DECL_RE = re.compile(
    r"^[ \t]*(?:[A-Za-z_]\w*[ \t]+)+(?P<name>[A-Za-z_]\w*)[ \t]*"
    r"\([^;{}]*\)[ \t]*;",
    re.M,
)
_WORD_TAIL_RE = re.compile(r"[A-Za-z0-9_]")

# (argument's class, parameter's class) of the refusal on record, and
# where it was refused, for the FAIL message.
_MEASURED = {
    ("Object", "EntityAI"): (
        "DayZDiag 1.30.164289, at the script method "
        "SubtreeBornInInventory of a mod, argument '0', where it also "
        "said \"Types 'Object' and 'EntityAI' are unrelated\""
    ),
}

ES_SCRIPT_ARGUMENT_DOWNCAST_MESSAGE = (
    "[FAIL] {rel_path} line {line}: '{call}(': argument {index} "
    "(counted from 0), '{arg}', is declared as {arg_type}, and the script "
    "method {owner}.{method} takes {param_type} there, which derives "
    "from it ({param_chain}). The compiler refuses the implicit "
    "down-cast with \"Cannot convert '{arg_type}' to '{param_type}' for "
    "argument '{index}' to method '{method}'\" and the whole script "
    "module does not compile ({measured}). Pass {param_type}.Cast({arg}), "
    "which is null when it is not one, or declare '{arg}' as {param_type}."
)
ES_SCRIPT_ARGUMENT_DOWNCAST_WARN_MESSAGE = (
    "[WARN] {rel_path} line {line}: '{call}(': argument {index} "
    "(counted from 0), '{arg}', is declared as {arg_type}, and the script "
    "method {owner}.{method} takes {param_type} there, which derives "
    "from it ({param_chain}): an implicit down-cast. DayZDiag 1.30 "
    "refused an Object where a mod's script method took an EntityAI, and "
    "the script module did not compile; whether it refuses {arg_type} "
    "where {param_type} is taken is not measured. Pass "
    "{param_type}.Cast({arg}), which is null when it is not one, or "
    "declare '{arg}' as {param_type}."
)


def _script_method(bodies, chain, method):
    """(class, parameters) of the script `method` that chain[0] reaches,
    or None, as ClassBodies.proto() reads it with the proto test turned
    round: the first class up the chain with a declaration on a line that
    compiles decides, and every declaration there must be a script method
    with one parameter list."""
    for cls in chain:
        bodies_of = bodies.bodies.get(cls)
        if not bodies_of or any(
            methods is None for _r, _l, _s, methods in bodies_of
        ):
            return None
        found = []
        for _rank, lines, _span, methods in bodies_of:
            for proto, parameters, start, at in methods.get(method, ()):
                if lines.blocks(at) is None:
                    continue
                if not lines.plain(start, at):
                    return None
                found.append((proto, parameters))
        if not found:
            continue
        signatures = {parameters for _proto, parameters in found}
        if any(proto for proto, _parameters in found) or len(signatures) != 1:
            return None
        return cls, signatures.pop()
    return None


def _global_names(text):
    """The names of the functions declared outside every class body of
    one text: a method region outside a class body, or a declaration
    that ends at `;` at the top level."""
    regions = _class_regions(text)
    methods = find_method_regions(text)
    offsets = _line_offsets(text)
    ranges = []
    names = set()
    for method in methods:
        start = offsets[method["start_line"] - 1]
        end = (
            offsets[method["end_line"]]
            if method["end_line"] < len(offsets) else len(text)
        )
        ranges.append((start, end))
        if not any(open_at < start < close_at for open_at, close_at in regions):
            names.add(method["name"])
    for match in _GLOBAL_DECL_RE.finditer(text):
        at = match.start()
        if any(open_at < at < close_at for open_at, close_at in regions):
            continue
        if any(start <= at < end for start, end in ranges):
            continue
        names.add(match.group("name"))
    return names


@functools.lru_cache(maxsize=4)
def _vanilla_global_names(vanilla_key):
    """The global function names of the vanilla tree, strings blanked.

    Built once per tree, as _vanilla_index() is: vanilla_sources() is
    cached, and this scan is the one other pass over its texts.
    """
    names = set()
    for _rel_path, text in vanilla_sources(vanilla_key):
        text = _STRING_RE.sub(lambda m: " " * len(m.group(0)), text)
        names.update(_global_names(text))
    return frozenset(names)


def _preceded_by_a_name(stripped, at):
    """True when the name at `at` is preceded, past whitespace, by a dot
    or by an identifier other than `return` or `else`: no bare call."""
    index = at - 1
    crossed_newline = False
    while index >= 0 and stripped[index] in " \t\r\n":
        if stripped[index] in "\r\n":
            crossed_newline = True
        index -= 1
    if index < 0:
        return False
    if crossed_newline:
        line_start = max(
            stripped.rfind("\n", 0, index + 1),
            stripped.rfind("\r", 0, index + 1),
        ) + 1
        first = line_start
        while first <= index and stripped[first] in " \t":
            first += 1
        if first <= index and stripped[first] == "#":
            return False
    if stripped[index] == ".":
        return True
    if not _WORD_TAIL_RE.match(stripped[index]):
        return False
    end = index + 1
    while index >= 0 and _WORD_TAIL_RE.match(stripped[index]):
        index -= 1
    return stripped[index + 1:end] not in ("return", "else")


def _member_type(
    base, member, stripped, scopes, at, hierarchy, bodies, body_classes,
    rank, inherited, around, line,
):
    """The declared type of `base.member` at the call at `at`, or None.

    For `this`, the class of the body around the call; a local of that
    name is never read. The member is read up the chain of the type of
    base, the first class that declares it, as _inherited_member() does.
    """
    if base == "super":
        return None
    if base == "this":
        enclosing = scopes.class_body(at)
        base_type = body_classes.get(enclosing[0]) if enclosing else None
    else:
        base_type = _argument_type(stripped, scopes, base, at, inherited, around)
    chain = hierarchy.chain(base_type) if base_type else None
    if not chain:
        return None
    blocks = around[line] if around else ()
    for owner in chain:
        declared = bodies.member(owner, member, rank, stripped, blocks)
        if declared is not None:
            return declared or None
    return None


def check_es_script_argument_downcast(addon_sources, external_sources, vanilla_root):
    """addon_sources / external_sources: lists of (rel_path, stripped_source).

    Returns (errors, warnings).
    """
    if not any(
        _CALL_RE.search(stripped) or _BARE_CALL_RE.search(stripped)
        for _rel_path, stripped in addon_sources
    ):
        return [], []
    hierarchy = Hierarchy()
    bodies = ClassBodies()
    vanilla_key = usable_vanilla_key(vanilla_root)
    if vanilla_key is not None:
        vanilla_hierarchy, vanilla_bodies = _vanilla_index(vanilla_key)
        hierarchy.declarations = {
            name: list(entries)
            for name, entries in vanilla_hierarchy.declarations.items()
        }
        hierarchy.definitions.merge(vanilla_hierarchy.definitions)
        hierarchy.not_classes |= vanilla_hierarchy.not_classes
        bodies.extend(vanilla_bodies)
    all_sources = list(addon_sources) + list(external_sources or [])
    for rel_path, stripped in all_sources:
        hierarchy.add_source(stripped)
        bodies.add_source(stripped, module_rank(rel_path))
    # The script method names of every tree, read once: a call to any
    # other name is no candidate, as bodies.names gates the proto rule.
    script_names = set()
    for bodies_of in bodies.bodies.values():
        for _rank, _lines, _span, methods in bodies_of:
            if methods is None:
                continue
            for name, declarations in methods.items():
                if any(not proto for proto, _p, _s, _a in declarations):
                    script_names.add(name)
    if not script_names:
        return [], []
    global_names = set()
    for _rel_path, stripped in all_sources:
        global_names.update(_global_names(stripped))
    if vanilla_key is not None:
        global_names.update(_vanilla_global_names(vanilla_key))

    errors = []
    warnings = []
    for rel_path, stripped in addon_sources:
        candidates = [
            (match.start(), match, match.group("recv"), match.group("method"))
            for match in _CALL_RE.finditer(stripped)
        ]
        candidates += [
            (match.start(), match, None, match.group("method"))
            for match in _BARE_CALL_RE.finditer(stripped)
        ]
        if not any(method in script_names for _at, _m, _r, method in candidates):
            continue
        candidates.sort(key=lambda candidate: candidate[0])
        rank = module_rank(rel_path)
        scopes = None
        for _at, match, recv, method in candidates:
            if method not in script_names:
                continue
            if scopes is None:
                scopes = FileScopes(stripped)
                closes, marks = _brackets(stripped)
                around = line_branches(stripped)
                body_classes = _body_classes(stripped)
                inherited = functools.partial(
                    _inherited_member, hierarchy, bodies, body_classes,
                    rank, stripped,
                )
            line = scopes.line(match.start())
            if line in scopes.dead or scopes.method(line) is None:
                continue
            if recv is None:
                if _preceded_by_a_name(stripped, match.start()):
                    continue
                if method in global_names:
                    continue
                enclosing = scopes.class_body(match.start())
                recv_type = body_classes.get(enclosing[0]) if enclosing else None
                if not recv_type:
                    continue
                call = method
            elif recv == "super":
                continue
            elif recv == "this":
                enclosing = scopes.class_body(match.start())
                recv_type = body_classes.get(enclosing[0]) if enclosing else None
                if not recv_type:
                    continue
                call = "this." + method
            else:
                recv_type = (
                    recv if hierarchy.is_plain_class(recv)
                    else _argument_type(
                        stripped, scopes, recv, match.start(), inherited, around
                    )
                )
                if not recv_type:
                    continue
                call = recv + "." + method
            chain = hierarchy.chain(recv_type)
            found = _script_method(bodies, chain, method) if chain else None
            if found is None:
                continue
            owner, parameters = found
            arguments = _arguments(stripped, match.end() - 1, closes, marks)
            if arguments is None or len(arguments) > len(parameters):
                continue
            for index, (arg, parameter) in enumerate(zip(arguments, parameters)):
                if parameter is None:
                    continue
                modifiers, param_type = parameter
                if modifiers & _WRITTEN or param_type is None:
                    continue
                param_chain = hierarchy.chain(param_type)
                if param_chain is None:
                    continue
                member = _MEMBER_ARG_RE.match(arg)
                if _NAME_RE.match(arg) is not None:
                    arg_type = _argument_type(
                        stripped, scopes, arg, match.start(), inherited, around
                    )
                elif member is not None:
                    arg_type = _member_type(
                        member.group("base"), member.group("member"),
                        stripped, scopes, match.start(), hierarchy, bodies,
                        body_classes, rank, inherited, around, line,
                    )
                else:
                    continue
                if arg_type == IMPLICIT_ROOT or arg_type not in param_chain[1:]:
                    continue
                measured = _MEASURED.get((arg_type, param_type))
                message = (
                    ES_SCRIPT_ARGUMENT_DOWNCAST_MESSAGE if measured
                    else ES_SCRIPT_ARGUMENT_DOWNCAST_WARN_MESSAGE
                )
                (errors if measured else warnings).append(
                    {
                        "check": ES_SCRIPT_ARGUMENT_DOWNCAST_RULE_ID,
                        "file": rel_path,
                        "line": line,
                        "message": message.format(
                            rel_path=rel_path, line=line, call=call,
                            method=method, index=index, arg=arg,
                            arg_type=arg_type, owner=owner,
                            param_type=param_type,
                            param_chain=" > ".join(param_chain),
                            measured=measured,
                        ),
                        "severity": "FAIL" if measured else "WARN",
                        "rule_id": ES_SCRIPT_ARGUMENT_DOWNCAST_RULE_ID,
                    }
                )
    return errors, warnings

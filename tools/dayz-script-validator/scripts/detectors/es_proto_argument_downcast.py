import re

from detectors.es_cast_unrelated_types import (
    IMPLICIT_ROOT,
    FileScopes,
    Hierarchy,
    _argument_type,
)
from detectors.es_protected_method_cross_class import _CALL_RE
from detectors.es_undeclared_static_member import class_bodies
from detectors.es_variable_named_as_type import usable_vanilla_key, vanilla_sources


ES_PROTO_ARGUMENT_DOWNCAST_RULE_ID = "ES-PROTO-ARGUMENT-DOWNCAST"


# claim: CLAIM-ENFORCE-PROTO-ARGUMENT-DOWNCAST
# A name passed to a parameter of a `proto` method, when the parameter's
# class derives from the class the name is declared as, stops the whole
# script module from compiling. Pipeline inbox fb-20261006-030019-e074, DayZ
# 1.30.164014 server:
#
#   DayZPhysics.RaycastRV(from, to, pos, dir, comp, hits, hitEntity,
#       m_Human, true, false, ObjIntersectGeom)
#
# with hitEntity an IEntity (the out argument of CollisionMoveTest) at the
# Object parameter 6 was refused with "Unsafe down-casting, use
# 'Object.Cast'", "Types 'IEntity' and 'Object' are unrelated" and "Cannot
# convert 'IEntity' to 'Object' for argument '6' to method 'RaycastRV'", and
# the World module did not compile. The compiler counts arguments from 0.
# That Object derives from IEntity is read from the vanilla tree when the
# rule runs. Only this shape is measured: an argument of a script method, an
# argument of an unrelated class and a down-cast in an assignment are not
# judged.
#
# Judged only when everything is known, otherwise skipped without a word:
#   - the call is `recv.Method(` with recv a class, or a plain name with one
#     plain declared type, as a local still open at the call, a parameter or
#     a member of the enclosing class (the lookup of ES-CAST-UNRELATED-TYPES);
#   - up the `extends` chain of that class, resolved as in
#     ES-CAST-UNRELATED-TYPES, the first class with a declaration (modded
#     included) whose body names Method before a `(` at its top level
#     declares it `proto` in every one of them, with one parameter list;
#   - the argument is a plain name with one plain declared type, looked up
#     as the receiver is, and the parameter at its index is neither `out`
#     nor `inout` and has a plain class type whose chain resolves;
#   - that chain holds the argument's class above the parameter's own.
#     Class, the implicit root, is not judged as the argument's class.
# A call whose arguments hold `<`, `>` or a directive is skipped, and so is
# one with more arguments than parameters. Proto methods are read from the
# addon, every --external-scripts root and the vanilla tree (comments
# dropped, strings blanked), so without a vanilla tree no vanilla proto is
# judged. Lines that never compile (shared/dead_branches.py) are not judged.

_IDENT_RE = re.compile(r"[A-Za-z_]\w*")
_NAME_RE = re.compile(r"[A-Za-z_]\w*\Z")
_STRING_RE = re.compile(r'"(?:\\.|[^"\\\n])*"')
_ATTRIBUTES_RE = re.compile(r"(?:\[[^\]]*\]\s*)*")
# What may stand before a parameter's type. The method writes an `out` or
# `inout` argument, and that direction is not judged.
_PARAMETER_MODIFIERS = frozenset({
    "out", "inout", "notnull", "const", "owned", "ref", "autoptr", "local",
})
_WRITTEN = frozenset({"out", "inout"})

ES_PROTO_ARGUMENT_DOWNCAST_MESSAGE = (
    "[FAIL] {rel_path} line {line}: '{recv}.{method}(': argument {index} "
    "(counted from 0), '{arg}', is declared as {arg_type}, and the proto "
    "{owner}.{method} takes {param_type} there, which derives from it "
    "({param_chain}). The compiler refuses the implicit down-cast with "
    "\"Cannot convert '{arg_type}' to '{param_type}' for argument '{index}' "
    "to method '{method}'\" and the whole script module does not compile. "
    "Pass {param_type}.Cast({arg}), which is null when it is not one, or "
    "declare '{arg}' as {param_type}."
)


def _closing(text, at, opener, closer):
    """Offset of the bracket that closes the `opener` at `at`, or None."""
    depth = 0
    for index in range(at, len(text)):
        if text[index] == opener:
            depth += 1
        elif text[index] == closer:
            depth -= 1
            if depth == 0:
                return index
    return None


def _heads(body):
    """The top-level statements of a class body, each up to `;` or a body.

    None when a bracket does not close: the body cannot be read.
    """
    heads = []
    head = []
    braces = parens = 0
    for char in body:
        if braces:
            if char == "{":
                braces += 1
            elif char == "}":
                braces -= 1
            continue
        if parens == 0 and char in "{;":
            heads.append("".join(head))
            head = []
            braces = 1 if char == "{" else 0
            continue
        if char == "(":
            parens += 1
        elif char == ")":
            parens -= 1
        head.append(char)
    if braces or parens:
        return None
    heads.append("".join(head))
    return heads


def _parameters(text):
    """((modifiers, type) or None, ...) of a parameter list.

    type is None for a type that is not a plain name (a template, an array);
    a parameter that does not read as modifiers, a type and a name is None.
    """
    pieces = []
    depth = 0
    start = 0
    for index, char in enumerate(text):
        if char in "(<[":
            depth += 1
        elif char in ")>]":
            depth -= 1
        elif char == "," and depth == 0:
            pieces.append(text[start:index])
            start = index + 1
    pieces.append(text[start:])
    parameters = []
    for piece in pieces:
        declaration = piece.split("=", 1)[0]
        words = _IDENT_RE.findall(declaration)
        if len(words) < 2 or not set(words[:-2]) <= _PARAMETER_MODIFIERS:
            parameters.append(None)
            continue
        # A template is no modifier, so only an array is left to refuse.
        plain = "[" not in declaration
        parameters.append((frozenset(words[:-2]), words[-2] if plain else None))
    return tuple(parameters)


def _method(head):
    """(name, is proto, parameters) of a method head, or None.

    Directives before the declaration are dropped. A parameter whose text
    holds one does not read as modifiers, a type and a name.
    """
    lines = head.split("\n")
    while lines and (not lines[0].strip() or lines[0].lstrip().startswith("#")):
        lines.pop(0)
    head = "\n".join(lines).strip()
    head = head[_ATTRIBUTES_RE.match(head).end():]
    open_at = head.find("(")
    if open_at < 0:
        return None
    before = head[:open_at]
    if "=" in before:
        return None  # a field set by a call
    words = _IDENT_RE.findall(before)
    if not words:
        return None
    close_at = _closing(head, open_at, "(", ")")
    return words[-1], "proto" in words, _parameters(head[open_at + 1:close_at])


class ProtoMethods:
    """The methods at the top level of every class body of the scanned trees."""

    def __init__(self):
        # {class: [None for a body that cannot be read, or
        #          {method: [(is proto, parameters), ...]}]}
        self.bodies = {}
        self.names = set()

    def add_source(self, text):
        for match, span in class_bodies(text):
            heads = None if span is None else _heads(text[span[0] + 1:span[1]])
            methods = None
            if heads is not None:
                methods = {}
                for head in heads:
                    found = _method(head)
                    if found is None:
                        continue
                    name, proto, parameters = found
                    methods.setdefault(name, []).append((proto, parameters))
                    if proto:
                        self.names.add(name)
            self.bodies.setdefault(match.group("name"), []).append(methods)

    def lookup(self, chain, method):
        """(class, parameters) of the proto `method` that chain[0] reaches, or None."""
        for cls in chain:
            bodies = self.bodies.get(cls)
            if not bodies or None in bodies:
                return None
            found = [entry for body in bodies for entry in body.get(method, ())]
            if not found:
                continue
            signatures = {parameters for _proto, parameters in found}
            if not all(proto for proto, _parameters in found) or len(signatures) != 1:
                return None
            return cls, signatures.pop()
        return None


def _arguments(stripped, open_at):
    """The arguments, stripped, of the call whose `(` is at open_at, or None.

    None when they hold `<` or `>` (template arguments and comparisons put
    commas the split cannot tell apart) or a directive, or never close.
    """
    pieces = []
    depth = 0
    start = open_at + 1
    for index in range(open_at, len(stripped)):
        char = stripped[index]
        if char in "<>#":
            return None
        if char in "([":
            depth += 1
        elif char in ")]":
            depth -= 1
            if depth == 0:
                pieces.append(stripped[start:index].strip())
                return pieces
        elif char == "," and depth == 1:
            pieces.append(stripped[start:index].strip())
            start = index + 1
    return None


def check_es_proto_argument_downcast(addon_sources, external_sources, vanilla_root):
    """addon_sources / external_sources: lists of (rel_path, stripped_source)."""
    texts = [
        stripped
        for _rel_path, stripped in list(addon_sources) + list(external_sources or [])
    ]
    vanilla_key = usable_vanilla_key(vanilla_root)
    if vanilla_key is not None:
        texts.extend(
            _STRING_RE.sub(lambda m: " " * len(m.group(0)), text)
            for _rel_path, text in vanilla_sources(vanilla_key)
        )
    hierarchy = Hierarchy()
    methods = ProtoMethods()
    for text in texts:
        hierarchy.add_source(text)
        methods.add_source(text)

    errors = []
    for rel_path, stripped in addon_sources:
        scopes = None
        for match in _CALL_RE.finditer(stripped):
            recv, method = match.group("recv"), match.group("method")
            if method not in methods.names:
                continue
            if scopes is None:
                scopes = FileScopes(stripped)
            line = scopes.line(match.start())
            if line in scopes.dead:
                continue
            recv_type = (
                recv if hierarchy.is_plain_class(recv)
                else _argument_type(stripped, scopes, recv, match.start())
            )
            chain = hierarchy.chain(recv_type) if recv_type else None
            found = methods.lookup(chain, method) if chain else None
            if found is None:
                continue
            owner, parameters = found
            arguments = _arguments(stripped, match.end() - 1)
            if arguments is None or len(arguments) > len(parameters):
                continue
            for index, (arg, parameter) in enumerate(zip(arguments, parameters)):
                if parameter is None or _NAME_RE.match(arg) is None:
                    continue
                modifiers, param_type = parameter
                if modifiers & _WRITTEN or param_type is None:
                    continue
                param_chain = hierarchy.chain(param_type)
                if param_chain is None:
                    continue
                arg_type = _argument_type(stripped, scopes, arg, match.start())
                if arg_type == IMPLICIT_ROOT or arg_type not in param_chain[1:]:
                    continue
                errors.append(
                    {
                        "check": ES_PROTO_ARGUMENT_DOWNCAST_RULE_ID,
                        "file": rel_path,
                        "line": line,
                        "message": ES_PROTO_ARGUMENT_DOWNCAST_MESSAGE.format(
                            rel_path=rel_path, line=line, recv=recv,
                            method=method, index=index, arg=arg,
                            arg_type=arg_type, owner=owner,
                            param_type=param_type,
                            param_chain=" > ".join(param_chain),
                        ),
                        "severity": "FAIL",
                        "rule_id": ES_PROTO_ARGUMENT_DOWNCAST_RULE_ID,
                    }
                )
    return errors

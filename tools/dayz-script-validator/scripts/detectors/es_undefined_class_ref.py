import functools
import pathlib
import re


ES_UNDEFINED_CLASS_REF_RULE_ID = "ES-UNDEFINED-CLASS-REF"


# claim: CLAIM-ENFORCE-UNDEFINED-TYPE-REF
# Observed on 2026-09-19 auditing netcopdev/TransferZ PR #12 (head 11da911): the
# PR deletes Scripts/4_World/TransferZ/TransferZ_ExternalStagingSortPlanner.c
# (class TransferZExternalStagingSortPlanner) while
# Scripts/5_Mission/TransferZ/TransferZ_MaintenanceClient.c:59 still calls
#
#   int sortResult = TransferZExternalStagingSortPlanner.Sort(player, source);
#
# The type exists in no module of the addon, of vanilla or of its one
# dependency (CF), so the Mission module cannot compile. The linter returned
# WARN with 0 errors on that tree: every rule read one file, and no rule asked
# whether a name used as a type is declared anywhere. The failure follows from
# the missing declaration; it was not booted.
#
# A reference is judged only where the identifier can only be a type:
#   - `Name.Method(`          static call, `Name.Cast(` included
#   - `new Name` / `new X<Name>`
#   - `Name var =|;|,|[`      typed declaration at the start of a line (locals,
#                             members, one-per-line parameters)
# and only for class-like names (first letter upper case). A static-call
# receiver can also be a variable, so a name declared as a variable, member or
# parameter anywhere in the scanned trees is not judged in that form.
#
# The universe of declarations is the addon, the vanilla scripts tree and every
# --external-scripts root. A verdict needs that universe to be complete, so the
# rule reports SKIP in the result's info block -- never a finding -- when:
#   - there is no vanilla tree: every vanilla type would look undefined;
#   - config.cpp requires a non-vanilla addon (not DZ_*) that no scanned root
#     declares in CfgPatches: the type may live there;
#   - no config.cpp in the tree declares requiredAddons[] at all: the
#     dependencies are unknown.
# The SKIP lists the unresolved names; passing the dependency's scripts with
# --external-scripts turns the list into verdicts.
# Code under #ifdef/#ifndef is judged only when the macro is known: tested by
# vanilla (engine and build flags), #define'd by the scanned scripts, or listed
# in a scanned CfgMods defines[]. Anything else is usually an optional mod's
# flag, and that code compiles only when the mod is loaded.

_CLASS_LIKE_RE = re.compile(r"^[A-Z]")

# Vanilla is read raw, and writes `/*sealed*/ class SurfaceDetectionParameters`
# (3_game/surfaceinfo.c:74): a block comment may precede the keyword.
_LEADING_COMMENTS = r"(?:/\*.*?\*/[ \t]*)*"
_CLASS_DEF_RE = re.compile(
    r"^[ \t]*" + _LEADING_COMMENTS
    + r"(?:(?:modded|sealed|proto|native|inherited|static|external)\s+)*"
    r"class\s+(?P<name>[A-Za-z_]\w*)(?:\s*<(?P<params>[^;{}>]*)>)?",
    re.M,
)
_TEMPLATE_PARAM_RE = re.compile(r"\bClass\s+(?P<name>[A-Za-z_]\w*)")
_ENUM_DEF_RE = re.compile(
    r"^[ \t]*" + _LEADING_COMMENTS + r"enum\s+(?P<name>[A-Za-z_]\w*)", re.M
)
# Vanilla writes typedefs with and without the trailing `;`
# (`typedef map<InventoryItem, vector> TItemsMap`), often with a `//` note.
_TYPEDEF_RE = re.compile(r"^[ \t]*typedef\b(?P<body>[^;\n]*)", re.M)
_LAST_IDENT_RE = re.compile(r"(?P<name>[A-Za-z_]\w*)\s*$")
# Vanilla's tested macros are engine/build flags (SERVER, DIAG_DEVELOPER...):
# code under them compiles in some real build, so it is judged. A mod only
# contributes the macros it DEFINES; the ones it merely tests are usually
# another mod's flag, and that code compiles only when that mod is loaded.
_MACRO_TEST_RE = re.compile(r"^[ \t]*#[ \t]*(?:ifdef|ifndef)[ \t]+(?P<name>\w+)", re.M)
_MACRO_DEFINE_RE = re.compile(r"^[ \t]*#[ \t]*define[ \t]+(?P<name>\w+)", re.M)
# `Type Name` followed by what can only follow a declared name. Collected for
# class-like names only: those are the ones a static-call receiver could be.
# Template spans are lazy here and below: a greedy `<...>` swallowed
# `Symptoms_primary` in `array<ref Param> Symptoms_primary, array<ref Param>
# Symptoms_secondary` (4_world/classes/playersymptoms/statemanager.c:827).
_DECLARED_NAME_RE = re.compile(
    r"\b[A-Za-z_]\w*(?:[ \t]*<[^;{}()\n]*?>)?(?:[ \t]*\[[^\]\n]*\])?"
    r"[ \t]+(?P<name>[A-Z]\w*)[ \t]*(?=[=;,)\[:])"
)

_STATIC_CALL_RE = re.compile(
    r"(?<![\w.])(?P<name>[A-Z]\w*)\s*\.\s*(?P<method>[A-Za-z_]\w*)\s*\("
)
_NEW_RE = re.compile(r"\bnew\s+(?P<name>[A-Za-z_]\w*)(?P<args>\s*<[^;{}()]*?>)?")
_DECL_RE = re.compile(
    r"^\s*(?:(?:ref|autoptr|const|static|private|protected|owned|notnull)\s+)*"
    r"(?P<name>[A-Za-z_]\w*)(?P<args>\s*<[^;{}()]*?>)?(?:\s*\[[^\]]*\])?"
    r"\s+[A-Za-z_]\w*\s*(?==|;|,|\[)"
)
_IDENT_RE = re.compile(r"[A-Za-z_]\w*")

_PP_OPEN_RE = re.compile(r"^\s*#\s*(?:ifdef|ifndef)\s+(?P<macro>\w+)")
_PP_OPEN_UNSUPPORTED_RE = re.compile(r"^\s*#\s*if\b")
_PP_ELIF_RE = re.compile(r"^\s*#\s*elif\b")
_PP_ENDIF_RE = re.compile(r"^\s*#\s*endif\b")

_MODULE_RE = re.compile(r"(?:^|[\\/])scripts[\\/](?P<module>[0-9]_[A-Za-z]+)[\\/]", re.I)

_REQUIRED_ADDONS_RE = re.compile(
    r"requiredAddons\s*\[\s*\]\s*=\s*\{(?P<body>[^}]*)\}", re.S
)
_DEFINES_RE = re.compile(r"\bdefines\s*\[\s*\]\s*=\s*\{(?P<body>[^}]*)\}", re.S)
_QUOTED_RE = re.compile(r'"(?P<value>[^"\n]*)"')
_CFGPATCHES_RE = re.compile(r"\bclass\s+CfgPatches\b")
_CLASS_NAME_RE = re.compile(r"\bclass\s+(?P<name>\w+)")
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)
_LINE_COMMENT_RE = re.compile(r"//[^\n]*")

# Measured 2026-09-19: 206 distinct CfgPatches names across the config.cpp files
# under P:\DZ, all prefixed DZ_. requiredAddons outside that prefix are mods.
VANILLA_ADDON_PREFIX = "DZ_"

ES_UNDEFINED_CLASS_REF_MESSAGE = (
    "[FAIL] {rel_path} line {line}: '{name}' is used as a type ({form}) but no "
    "class, enum or typedef named '{name}' is declared in the addon, in the "
    "vanilla scripts tree or in any --external-scripts root. A script module "
    "that names an unknown type does not compile, so {module} fails to load. "
    "Restore the declaration or update the reference; if the type comes from a "
    "dependency mod, list it in config.cpp requiredAddons[] and pass its "
    "scripts root with --external-scripts."
)


class Definitions:
    """Type names, template parameters, macros and class-like variable names."""

    def __init__(self):
        self.types = set()
        self.template_params = set()
        self.macros = set()
        self.variables = set()

    def add_source(self, text, tested_macros_are_known=False, variables=True):
        for match in _CLASS_DEF_RE.finditer(text):
            self.types.add(match.group("name"))
            params = match.group("params")
            if params:
                for param in _TEMPLATE_PARAM_RE.finditer(params):
                    self.template_params.add(param.group("name"))
        for match in _ENUM_DEF_RE.finditer(text):
            self.types.add(match.group("name"))
        for match in _TYPEDEF_RE.finditer(text):
            body = match.group("body").split("//", 1)[0]
            last = _LAST_IDENT_RE.search(body)
            if last:
                self.types.add(last.group("name"))
        for match in _MACRO_DEFINE_RE.finditer(text):
            self.macros.add(match.group("name"))
        if tested_macros_are_known:
            for match in _MACRO_TEST_RE.finditer(text):
                self.macros.add(match.group("name"))
        if variables:
            self.variables |= declared_variables(text)

    def merge(self, other):
        self.types |= other.types
        self.template_params |= other.template_params
        self.macros |= other.macros
        self.variables |= other.variables

    def is_type(self, name):
        return name in self.types or name in self.template_params


def declared_variables(text):
    return {match.group("name") for match in _DECLARED_NAME_RE.finditer(text)}


def _vanilla_texts(vanilla_root):
    for path in sorted(pathlib.Path(vanilla_root).rglob("*.c")):
        try:
            yield path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue


@functools.lru_cache(maxsize=4)
def vanilla_definitions(vanilla_root):
    """Types and macros of the vanilla tree, read once per process and root.

    Raw text, not stripped: a class named in a comment only makes the rule
    more lenient, and stripping 12 MB is a cost the quick-check hook would pay
    on every edit. Variable names are left to vanilla_variables().
    """
    definitions = Definitions()
    for text in _vanilla_texts(vanilla_root):
        definitions.add_source(text, tested_macros_are_known=True, variables=False)
    return definitions


@functools.lru_cache(maxsize=4)
def vanilla_variables(vanilla_root):
    """Class-like variable names declared in vanilla.

    Measured 2026-09-19: half of the vanilla scan (0.62 of ~1.3 s). Only an
    unresolved static-call receiver needs it, which is rare, so it is lazy.
    """
    names = set()
    for text in _vanilla_texts(vanilla_root):
        names |= declared_variables(text)
    return names


def _module_label(rel_path):
    match = _MODULE_RE.search(str(rel_path).replace("\\", "/"))
    if match:
        return "the %s script module" % match.group("module")
    return "the script module containing this file"


def _strip_config_comments(text):
    return _LINE_COMMENT_RE.sub("", _BLOCK_COMMENT_RE.sub("", text))


def _config_array_values(config_sources, array_re):
    values = set()
    for _rel_path, text in config_sources:
        for block in array_re.finditer(_strip_config_comments(text)):
            for item in _QUOTED_RE.finditer(block.group("body")):
                value = item.group("value").strip()
                if value:
                    values.add(value)
    return values


def required_addons(config_sources):
    """Every requiredAddons[] entry across the given raw config.cpp texts."""
    return _config_array_values(config_sources, _REQUIRED_ADDONS_RE)


def config_defines(config_sources):
    """Every CfgMods defines[] entry: macros a loaded mod turns on."""
    return _config_array_values(config_sources, _DEFINES_RE)


def declared_patches(config_sources):
    """Class names directly inside every `class CfgPatches { ... }` block."""
    patches = set()
    for _rel_path, text in config_sources:
        text = _strip_config_comments(text)
        for start in _CFGPATCHES_RE.finditer(text):
            open_brace = text.find("{", start.end())
            if open_brace < 0:
                continue
            depth = 1
            index = open_brace + 1
            while index < len(text) and depth > 0:
                char = text[index]
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                elif depth == 1 and char == "c":
                    match = _CLASS_NAME_RE.match(text, index)
                    if match and (index == 0 or not text[index - 1].isalnum()):
                        patches.add(match.group("name"))
                        index = match.end()
                        continue
                index += 1
    return patches


def _gated_by_unknown_macro(stack, known_macros):
    for macro in stack:
        if macro is None or macro not in known_macros:
            return True
    return False


def _update_pp_stack(stack, line):
    """True when `line` is a preprocessor directive (and has been applied)."""
    opened = _PP_OPEN_RE.match(line)
    if opened:
        stack.append(opened.group("macro"))
        return True
    if _PP_OPEN_UNSUPPORTED_RE.match(line):
        stack.append(None)
        return True
    if _PP_ELIF_RE.match(line):
        if stack:
            stack[-1] = None
        return True
    if _PP_ENDIF_RE.match(line):
        if stack:
            stack.pop()
        return True
    # `#else` keeps the macro: its branch is as knowable as the first one.
    return line.lstrip().startswith("#")


def _template_args(args):
    if not args:
        return []
    return [
        name for name in _IDENT_RE.findall(args) if _CLASS_LIKE_RE.match(name)
    ]


def find_type_references(stripped, known_macros):
    """Yield (line, name, form) for every class-like name used as a type."""
    stack = []
    for line_number, line in enumerate(stripped.split("\n"), start=1):
        if _update_pp_stack(stack, line):
            continue
        if _gated_by_unknown_macro(stack, known_macros):
            continue
        seen = set()

        def emit(name, form):
            if name not in seen and _CLASS_LIKE_RE.match(name):
                seen.add(name)
                return [(line_number, name, form)]
            return []

        for match in _STATIC_CALL_RE.finditer(line):
            name = match.group("name")
            if match.group("method") == "Cast":
                form = "%s.Cast" % name
            else:
                form = "static call %s.%s" % (name, match.group("method"))
            yield from emit(name, form)
        for match in _NEW_RE.finditer(line):
            yield from emit(match.group("name"), "new %s" % match.group("name"))
            for arg in _template_args(match.group("args")):
                yield from emit(arg, "template argument of new")
        decl = _DECL_RE.match(line)
        if decl:
            yield from emit(decl.group("name"), "typed declaration")
            for arg in _template_args(decl.group("args")):
                yield from emit(arg, "template argument of a declaration")


def check_es_undefined_class_ref(
    addon_sources,
    addon_configs,
    external_sources,
    external_configs,
    vanilla_root,
    vanilla_skip_reason=None,
    addon_is_vanilla=False,
):
    """Return (errors, skipped).

    addon_sources / external_sources: lists of (rel_path, stripped_source).
    addon_configs / external_configs: lists of (rel_path, raw config.cpp text).
    `addon_is_vanilla`: the addon IS the vanilla tree (the vanilla control). It
    has no mod dependencies, so its empty requiredAddons[] is not "unknown".
    `skipped` lists what the rule could not judge, for the report's info block;
    it never changes the status.
    """
    if not addon_sources:
        return [], []
    if vanilla_root is None:
        return [], [
            {
                "rule_id": ES_UNDEFINED_CLASS_REF_RULE_ID,
                "status": "SKIP",
                "reason": (
                    "%s. Without the vanilla tree every vanilla type would look "
                    "undefined, so the rule does not run."
                    % (vanilla_skip_reason or "vanilla tree not available")
                ),
            }
        ]

    vanilla_key = str(pathlib.Path(vanilla_root).resolve())
    definitions = Definitions()
    definitions.merge(vanilla_definitions(vanilla_key))
    for _rel_path, stripped in list(addon_sources) + list(external_sources or []):
        definitions.add_source(stripped)
    all_configs = list(addon_configs) + list(external_configs or [])
    definitions.macros |= config_defines(all_configs)

    unresolved = []
    for rel_path, stripped in addon_sources:
        for line, name, form in find_type_references(stripped, definitions.macros):
            if definitions.is_type(name):
                continue
            if form.startswith("static call") and (
                name in definitions.variables
                or name in vanilla_variables(vanilla_key)
            ):
                continue
            unresolved.append((rel_path, line, name, form))
    if not unresolved:
        return [], []

    names = sorted({name for _f, _l, name, _form in unresolved})
    shown = "%d type name(s) resolve nowhere (%s)" % (
        len(names), ", ".join(names[:10]) + (", ..." if len(names) > 10 else "")
    )
    required = required_addons(addon_configs)
    provided = declared_patches(all_configs)
    uncovered = sorted(
        dependency
        for dependency in required
        if not dependency.startswith(VANILLA_ADDON_PREFIX)
        and dependency not in provided
    )
    reason = None
    if uncovered:
        reason = (
            "config.cpp requires %s, and no scanned root declares %s in "
            "CfgPatches. %s and may come from there; pass the dependency's "
            "scripts root with --external-scripts to judge them."
            % (", ".join(uncovered), "it" if len(uncovered) == 1 else "them", shown)
        )
    elif not required and not addon_is_vanilla:
        # Observed on 2026-09-19 across 161 addon roots under P:\: three mods
        # (six trees) with `requiredAddons[]={};` use CF, Expansion or LBmaster
        # classes outside any #ifdef. They can only compile next to those mods,
        # and the empty list does not say which. Empty is "not declared", not
        # "vanilla only" (vanilla's own scripts/config.cpp is empty too, hence
        # the addon_is_vanilla exception).
        reason = (
            "no config.cpp in the tree lists any requiredAddons[] entry, so the "
            "addon's dependencies are unknown. %s; declare the dependencies in "
            "requiredAddons[] and pass their scripts roots with "
            "--external-scripts to judge them." % shown
        )
    if reason:
        return [], [
            {
                "rule_id": ES_UNDEFINED_CLASS_REF_RULE_ID,
                "status": "SKIP",
                "reason": reason,
                "unresolved": [
                    {"name": name, "file": rel_path, "line": line}
                    for rel_path, line, name, _form in unresolved
                ],
            }
        ]

    errors = []
    for rel_path, line, name, form in unresolved:
        errors.append(
            {
                "check": ES_UNDEFINED_CLASS_REF_RULE_ID,
                "file": rel_path,
                "line": line,
                "message": ES_UNDEFINED_CLASS_REF_MESSAGE.format(
                    rel_path=rel_path, line=line, name=name, form=form,
                    module=_module_label(rel_path),
                ),
                "severity": "FAIL",
                "rule_id": ES_UNDEFINED_CLASS_REF_RULE_ID,
            }
        )
    return errors, []

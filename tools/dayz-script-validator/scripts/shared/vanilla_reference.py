"""Curated, statically-verified slices of the vanilla DayZ script tree.

R2 cite-then-verify: every entry MUST carry a `path:line` citation. This is the
minimum-viable reference used by detectors that need to know vanilla member
names / base override signatures WITHOUT mounting and parsing P:\\scripts at
runtime. Coverage is intentionally partial — add entries only when verified
against the vanilla tree. Partial coverage means false negatives (a real
collision we don't yet know about), never false positives.

An optional generated index (`vanilla_index.json`, produced by
`scripts/build_vanilla_index.py`, not committed) extends these tables when
present. Missing, corrupt, or schema-mismatched index files fall back to the
curated tables with identical behaviour. On a key present in both, the curated
entry wins (it carries a human-verified fix message). The index holds the
members and signatures of the tree it was built from, so an index of another
tree than the one being read can report a false positive. A whole index of
that tree kept beside the default one, as `vanilla_index.json.<name>`, is
read instead (use_sibling_index); shared/vanilla_index_tree.py decides which
file is of the tree and warns when none is (VANILLA-INDEX-TREE-MISMATCH).
"""

from __future__ import annotations

import json
from pathlib import Path


INDEX_SCHEMA_VERSION = 1
INDEX_FILENAME = "vanilla_index.json"

_index_path_override = None
# A file beside the default index, read instead of it (use_sibling_index).
_index_path_sibling = None
_index_loaded = False
_index_data = None

# Member variables declared in a vanilla base class. Used by
# ES-MEMBER-REDECLARE-BASE (CANDIDATE-13): a mod class extending one of these
# (or `modded class <base>`) must not re-declare these names.
# Keyed by the base class name. Inheritance is NOT expanded — list the member
# under the class that actually declares it.
VANILLA_BASE_MEMBERS = {
    "CarScript": {
        "m_NoiseSystem",  # carscript.c:266 (protected NoiseSystem m_NoiseSystem;)
    },
}

# Positional parameter names of common override targets in the vanilla tree.
# Used by ES-OVERRIDE-PARAM-NAME-MISMATCH (CANDIDATE-15): Enforce requires an
# override's parameter NAMES to match the base signature exactly. Keyed by
# method name -> list of parameter names in order.
VANILLA_OVERRIDE_PARAMS = {
    "OnExecuteServer": ["action_data"],  # animatedactionbase.c:175
}


def default_index_path():
    return Path(__file__).resolve().parent / INDEX_FILENAME


def set_index_path_for_tests(path):
    """Point the loader at a specific index file (or a missing path).

    That file is then the only one read: use_sibling_index leaves it alone.
    """
    global _index_path_override
    _index_path_override = path
    reset_index_cache()


def index_path_is_pinned():
    """Whether set_index_path_for_tests names the only index file read."""
    return _index_path_override is not None


def reset_index_cache():
    """Forget the index read, and the file beside the default one it was.

    The next lookup reads the default index from disk again, or the pinned
    one.
    """
    global _index_loaded, _index_data, _index_path_sibling
    _index_loaded = False
    _index_data = None
    _index_path_sibling = None


def _index_path():
    if _index_path_override is not None:
        return Path(_index_path_override)
    if _index_path_sibling is not None:
        return _index_path_sibling
    return default_index_path()


def _read_index(path):
    """The index document in a file, or None when the file does not hold one."""
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    if data.get("schema_version") != INDEX_SCHEMA_VERSION:
        return None
    return data


def _load_index():
    global _index_loaded, _index_data
    if _index_loaded:
        return _index_data
    _index_loaded = True
    _index_data = _read_index(_index_path())
    return _index_data


def loaded_index_path():
    """Index file in use, or None when only the curated tables apply."""
    if _load_index() is None:
        return None
    return _index_path()


# The tables the lookups below read; build_vanilla_index.py writes each as an
# object. A file beside the default index without one of them is not whole.
_INDEX_TABLE_KEYS = (
    "base_members",
    "override_params",
    "global_class_names",
    "platform_gated_methods",
)


def _has_tables(index):
    return all(isinstance(index.get(key), dict) for key in _INDEX_TABLE_KEYS)


def use_sibling_index(built_from_tree):
    """Read an index kept beside the default one instead of the one in use.

    The files are `vanilla_index.json.<name>` in the default index's folder,
    taken in name order. The first that holds a whole index (an object of
    this schema_version with the four tables the lookups read) for which
    built_from_tree(tree) is true becomes the index in use, where tree is
    what that index records of the tree it was built from (the dict
    loaded_index_tree returns). Returns its path, or None when there is no
    such file: the index in use then stays. A path set with
    set_index_path_for_tests is never replaced.
    """
    global _index_path_sibling, _index_loaded, _index_data
    if _index_path_override is not None:
        return None
    default = default_index_path()
    try:
        siblings = sorted(default.parent.glob(INDEX_FILENAME + ".*"))
    except OSError:
        return None
    for path in siblings:
        data = _read_index(path)
        if data is None or not _has_tables(data):
            continue
        if built_from_tree(_tree_of(data)):
            _index_path_sibling = path
            _index_loaded = True
            _index_data = data
            return path
    return None


_INDEX_TREE_KEYS = (
    "vanilla_root",
    "file_count",
    "parsed_file_count",
    "total_bytes",
    "tree_digest",
)


def _tree_of(index):
    return {key: index.get(key) for key in _INDEX_TREE_KEYS}


def loaded_index_tree():
    """What the index in use says of the tree it was built from, or None.

    The values build_vanilla_index.py wrote, unchecked; a key the file lacks
    is None. shared/vanilla_index_tree.py compares them with the vanilla
    tree being read.
    """
    index = _load_index()
    if index is None:
        return None
    return _tree_of(index)


def base_member_set(base_name):
    curated = VANILLA_BASE_MEMBERS.get(base_name, set())
    index = _load_index()
    if not index:
        return curated
    indexed = index.get("base_members", {}).get(base_name)
    extra = set()
    if isinstance(indexed, dict):
        extra = set(indexed.keys())
    elif isinstance(indexed, (list, set, tuple)):
        extra = set(indexed)
    if not extra:
        return curated
    return set(curated) | extra


def override_param_names(method_name):
    if method_name in VANILLA_OVERRIDE_PARAMS:
        return VANILLA_OVERRIDE_PARAMS[method_name]
    index = _load_index()
    if not index:
        return None
    entry = index.get("override_params", {}).get(method_name)
    if entry is None:
        return None
    if isinstance(entry, dict):
        params = entry.get("params")
        if isinstance(params, list):
            return list(params)
        return None
    if isinstance(entry, list):
        return list(entry)
    return None


# Global class names from the vanilla tree that BREAK when reused as a method
# name: the compiler reads `Name(args)` as a cast/constructor (not a call) and
# fails "Too many parameters for 'Name' method". Used by
# ES-METHOD-NAME-COLLIDES-VANILLA-CLASS (CANDIDATE-38). Curated; partial
# coverage -> false negatives, never false positives. Keyed by class name.
VANILLA_GLOBAL_CLASS_NAMES = {
    "LogManager": "scripts/3_game/tools/debug.c:691",  # class LogManager
}


def is_vanilla_global_class_name(name):
    if name in VANILLA_GLOBAL_CLASS_NAMES:
        return True
    index = _load_index()
    if not index:
        return False
    names = index.get("global_class_names", {})
    return isinstance(names, dict) and name in names


def vanilla_global_class_citation(name):
    if name in VANILLA_GLOBAL_CLASS_NAMES:
        return VANILLA_GLOBAL_CLASS_NAMES[name]
    index = _load_index()
    if not index:
        return None
    names = index.get("global_class_names", {})
    if not isinstance(names, dict):
        return None
    citation = names.get(name)
    if isinstance(citation, str) and citation:
        return citation
    return None


# Method names verified ABSENT from the entire vanilla script tree (0
# occurrences each; host-side grep over P:\scripts, 2026-06-10). Calling one
# compile-fails with `Undefined function`. Used by ES-NONEXISTENT-METHOD
# (CANDIDATE-43). Value = fix message with the verified alternative.
# Source claims: enforce-script-reference SKILL.md:1599/:1605/:1630-1631
# ("Deep-dive verified additions", added 2026-06-06).
VANILLA_NONEXISTENT_METHODS = {
    # Real API: recipebase.c:159 `void InsertIngredient(int index, string ingredient, ...)`
    "AddIngredient": "use `InsertIngredient(index, classname)` (recipebase.c:159)",
    # No vanilla equivalent on RecipeBase (SKILL.md:1605)
    "SetIsCacheable": "remove the call; the method has no vanilla equivalent",
    # Radius damage goes through DamageSystem (damagesystem.c:25)
    "ProcessIndirectDamage": (
        "use `DamageSystem.ExplosionDamage(source, null, ammo, pos, "
        "DamageType.EXPLOSION)` (damagesystem.c:25)"
    ),
}


# Methods that vanilla declares only inside a preprocessor guard a PC+RELEASE
# compile does not define. An unguarded override then fails with
# `no function to override in base class`, the module is dropped, and the
# client freezes on the loading screen (no crash, no useful RPT line).
# Used by ES-OVERRIDE-OF-PLATFORM-GATED-METHOD. Curated; partial coverage
# -> false negatives, never false positives. Keyed by method name. `owner`
# is the vanilla class that declares the gated method.
VANILLA_PLATFORM_GATED_METHODS = {
    "GetConsoleToolbarText": {
        "owner": "Inventory",
        "macro": "PLATFORM_CONSOLE",
        # declaration at :1314; #ifdef PLATFORM_CONSOLE is the previous line
        "citation": "5_mission/gui/inventorynew/inventory.c:1314",
    },
}


def platform_gated_method(method_name):
    if method_name in VANILLA_PLATFORM_GATED_METHODS:
        return VANILLA_PLATFORM_GATED_METHODS[method_name]
    index = _load_index()
    if not index:
        return None
    entry = index.get("platform_gated_methods", {}).get(method_name)
    if not isinstance(entry, dict):
        return None
    owner = entry.get("owner")
    macro = entry.get("macro")
    citation = entry.get("citation")
    if not owner or not macro or not citation:
        return None
    return {
        "owner": owner,
        "macro": macro,
        "citation": citation,
    }


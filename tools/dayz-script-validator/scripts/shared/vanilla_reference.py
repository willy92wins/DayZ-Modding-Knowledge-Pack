"""Curated, statically-verified slices of the vanilla DayZ script tree.

R2 cite-then-verify: every entry MUST carry a `path:line` citation. This is the
minimum-viable reference used by detectors that need to know vanilla member
names / base override signatures WITHOUT mounting and parsing P:\\scripts at
runtime. Coverage is intentionally partial — add entries only when verified
against the vanilla tree. Partial coverage means false negatives (a real
collision we don't yet know about), never false positives.
"""

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


def base_member_set(base_name):
    return VANILLA_BASE_MEMBERS.get(base_name, set())


def override_param_names(method_name):
    return VANILLA_OVERRIDE_PARAMS.get(method_name)


# Global class names from the vanilla tree that BREAK when reused as a method
# name: the compiler reads `Name(args)` as a cast/constructor (not a call) and
# fails "Too many parameters for 'Name' method". Used by
# ES-METHOD-NAME-COLLIDES-VANILLA-CLASS (CANDIDATE-38). Curated; partial
# coverage -> false negatives, never false positives. Keyed by class name.
VANILLA_GLOBAL_CLASS_NAMES = {
    "LogManager": "scripts/3_game/tools/debug.c:691",  # class LogManager
}


def is_vanilla_global_class_name(name):
    return name in VANILLA_GLOBAL_CLASS_NAMES


def vanilla_global_class_citation(name):
    return VANILLA_GLOBAL_CLASS_NAMES.get(name)


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

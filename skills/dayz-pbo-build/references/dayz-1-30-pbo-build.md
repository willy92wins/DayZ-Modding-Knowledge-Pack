# DayZ 1.30 Exp — PBO / binarizer deltas (build 1.30.164014)

Companion to `SKILL.md` § DayZ 1.30 Exp. Folder structure, stringtable.csv,
include-list, and ODOL non-determinism still hold. This file is the 1.30
binarizer contract.

## Duplicate **members** abort binarize

(until 1.29: pre-build check "Duplicate class names: Same class cannot be
defined twice" — duplicate **properties** inside one class were a silent last-
write-wins.) (since 1.30 Exp [CHANGELOG], `work\changelog-1.30-exp-modding.md:19`):

> Changed: Binarizer will now stop binarising if a member is defined multiple
> times in a config file

This is a **build blocker**. AddonBuilder / CfgConvert that used to succeed on
a repeated `scope`, `displayName`, `weight`, `hiddenSelections[]`, or an inner
class name now **stops**. There is no Enforce example in `exp\` — the check is
engine-side.

[DESIGN] Audit every `config.cpp` (and inherited fragments) for a member
written twice in the **same class body**. Vanilla-style `class Foo; class Foo:
Bar {}` (forward + definition) is not the same bug; the changelog is
**multiple definitions of a member inside one block**.

Pre-build check 2 in `SKILL.md` now covers both class names **and** members.

## Unpacked mods do not retire the PBO gate

(since 1.30 Exp [CHANGELOG]: `-mod` can point at a folder and RV configs load
unpacked.) That is a **diag iteration** path (`dayz-test-ingame`). Workshop /
dedicated shipping still needs a PBO. Do not skip AddonBuilder for a release
because unpacked load exists.

Navmesh `.nm` regeneration (changelog `:21`) is a terrain/Workbench task, not
a PBO linter check. Flag it in the release notes of a custom map; this skill
does not validate `.nm` bytes (binaries are not in `exp\`).
